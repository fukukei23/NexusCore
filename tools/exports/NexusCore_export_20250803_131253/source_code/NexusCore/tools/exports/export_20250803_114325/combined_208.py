
# === NexusCore/openenv\Lib\site-packages\litellm\integrations\langfuse\langfuse_prompt_management.py ===
"""
Call Hook for LiteLLM Proxy which allows Langfuse prompt management.
"""

import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Tuple, Union, cast

from packaging.version import Version
from typing_extensions import TypeAlias

from litellm.integrations.custom_logger import CustomLogger
from litellm.integrations.prompt_management_base import PromptManagementClient
from litellm.litellm_core_utils.asyncify import run_async_function
from litellm.types.llms.openai import AllMessageValues, ChatCompletionSystemMessage
from litellm.types.utils import StandardCallbackDynamicParams, StandardLoggingPayload

from ...litellm_core_utils.specialty_caches.dynamic_logging_cache import (
    DynamicLoggingCache,
)
from ..prompt_management_base import PromptManagementBase
from .langfuse import LangFuseLogger
from .langfuse_handler import LangFuseHandler

if TYPE_CHECKING:
    from langfuse import Langfuse
    from langfuse.client import ChatPromptClient, TextPromptClient

    from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj

    LangfuseClass: TypeAlias = Langfuse

    PROMPT_CLIENT = Union[TextPromptClient, ChatPromptClient]
else:
    PROMPT_CLIENT = Any
    LangfuseClass = Any
    LiteLLMLoggingObj = Any
in_memory_dynamic_logger_cache = DynamicLoggingCache()


@lru_cache(maxsize=10)
def langfuse_client_init(
    langfuse_public_key=None,
    langfuse_secret=None,
    langfuse_secret_key=None,
    langfuse_host=None,
    flush_interval=1,
) -> LangfuseClass:
    """
    Initialize Langfuse client with caching to prevent multiple initializations.

    Args:
        langfuse_public_key (str, optional): Public key for Langfuse. Defaults to None.
        langfuse_secret (str, optional): Secret key for Langfuse. Defaults to None.
        langfuse_host (str, optional): Host URL for Langfuse. Defaults to None.
        flush_interval (int, optional): Flush interval in seconds. Defaults to 1.

    Returns:
        Langfuse: Initialized Langfuse client instance

    Raises:
        Exception: If langfuse package is not installed
    """
    try:
        import langfuse
        from langfuse import Langfuse
    except Exception as e:
        raise Exception(
            f"\033[91mLangfuse not installed, try running 'pip install langfuse' to fix this error: {e}\n\033[0m"
        )

    # Instance variables

    secret_key = (
        langfuse_secret or langfuse_secret_key or os.getenv("LANGFUSE_SECRET_KEY")
    )
    public_key = langfuse_public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_host = langfuse_host or os.getenv(
        "LANGFUSE_HOST", "https://cloud.langfuse.com"
    )

    if not (
        langfuse_host.startswith("http://") or langfuse_host.startswith("https://")
    ):
        # add http:// if unset, assume communicating over private network - e.g. render
        langfuse_host = "http://" + langfuse_host

    langfuse_release = os.getenv("LANGFUSE_RELEASE")
    langfuse_debug = os.getenv("LANGFUSE_DEBUG")

    parameters = {
        "public_key": public_key,
        "secret_key": secret_key,
        "host": langfuse_host,
        "release": langfuse_release,
        "debug": langfuse_debug,
        "flush_interval": LangFuseLogger._get_langfuse_flush_interval(
            flush_interval
        ),  # flush interval in seconds
    }

    if Version(langfuse.version.__version__) >= Version("2.6.0"):
        parameters["sdk_integration"] = "litellm"

    client = Langfuse(**parameters)

    return client


class LangfusePromptManagement(LangFuseLogger, PromptManagementBase, CustomLogger):
    def __init__(
        self,
        langfuse_public_key=None,
        langfuse_secret=None,
        langfuse_host=None,
        flush_interval=1,
    ):
        import langfuse

        self.langfuse_sdk_version = langfuse.version.__version__
        self.Langfuse = langfuse_client_init(
            langfuse_public_key=langfuse_public_key,
            langfuse_secret=langfuse_secret,
            langfuse_host=langfuse_host,
            flush_interval=flush_interval,
        )

    @property
    def integration_name(self):
        return "langfuse"

    def _get_prompt_from_id(
        self,
        langfuse_prompt_id: str,
        langfuse_client: LangfuseClass,
        prompt_label: Optional[str] = None,
    ) -> PROMPT_CLIENT:
        return langfuse_client.get_prompt(langfuse_prompt_id, label=prompt_label)

    def _compile_prompt(
        self,
        langfuse_prompt_client: PROMPT_CLIENT,
        langfuse_prompt_variables: Optional[dict],
        call_type: Union[Literal["completion"], Literal["text_completion"]],
    ) -> List[AllMessageValues]:
        compiled_prompt: Optional[Union[str, list]] = None

        if langfuse_prompt_variables is None:
            langfuse_prompt_variables = {}

        compiled_prompt = langfuse_prompt_client.compile(**langfuse_prompt_variables)

        if isinstance(compiled_prompt, str):
            compiled_prompt = [
                ChatCompletionSystemMessage(role="system", content=compiled_prompt)
            ]
        else:
            compiled_prompt = cast(List[AllMessageValues], compiled_prompt)

        return compiled_prompt

    def _get_optional_params_from_langfuse(
        self, langfuse_prompt_client: PROMPT_CLIENT
    ) -> dict:
        config = langfuse_prompt_client.config
        optional_params = {}
        for k, v in config.items():
            if k != "model":
                optional_params[k] = v
        return optional_params

    async def async_get_chat_completion_prompt(
        self,
        model: str,
        messages: List[AllMessageValues],
        non_default_params: dict,
        prompt_id: Optional[str],
        prompt_variables: Optional[dict],
        dynamic_callback_params: StandardCallbackDynamicParams,
        litellm_logging_obj: LiteLLMLoggingObj,
        tools: Optional[List[Dict]] = None,
        prompt_label: Optional[str] = None,
    ) -> Tuple[str, List[AllMessageValues], dict,]:
        return self.get_chat_completion_prompt(
            model,
            messages,
            non_default_params,
            prompt_id,
            prompt_variables,
            dynamic_callback_params,
            prompt_label=prompt_label,
        )

    def should_run_prompt_management(
        self,
        prompt_id: str,
        dynamic_callback_params: StandardCallbackDynamicParams,
    ) -> bool:
        langfuse_client = langfuse_client_init(
            langfuse_public_key=dynamic_callback_params.get("langfuse_public_key"),
            langfuse_secret=dynamic_callback_params.get("langfuse_secret"),
            langfuse_secret_key=dynamic_callback_params.get("langfuse_secret_key"),
            langfuse_host=dynamic_callback_params.get("langfuse_host"),
        )
        langfuse_prompt_client = self._get_prompt_from_id(
            langfuse_prompt_id=prompt_id, langfuse_client=langfuse_client
        )
        return langfuse_prompt_client is not None

    def _compile_prompt_helper(
        self,
        prompt_id: str,
        prompt_variables: Optional[dict],
        dynamic_callback_params: StandardCallbackDynamicParams,
        prompt_label: Optional[str] = None,
    ) -> PromptManagementClient:
        langfuse_client = langfuse_client_init(
            langfuse_public_key=dynamic_callback_params.get("langfuse_public_key"),
            langfuse_secret=dynamic_callback_params.get("langfuse_secret"),
            langfuse_secret_key=dynamic_callback_params.get("langfuse_secret_key"),
            langfuse_host=dynamic_callback_params.get("langfuse_host"),
        )
        langfuse_prompt_client = self._get_prompt_from_id(
            langfuse_prompt_id=prompt_id,
            langfuse_client=langfuse_client,
            prompt_label=prompt_label,
        )

        ## SET PROMPT
        compiled_prompt = self._compile_prompt(
            langfuse_prompt_client=langfuse_prompt_client,
            langfuse_prompt_variables=prompt_variables,
            call_type="completion",
        )

        template_model = langfuse_prompt_client.config.get("model")

        template_optional_params = self._get_optional_params_from_langfuse(
            langfuse_prompt_client
        )

        return PromptManagementClient(
            prompt_id=prompt_id,
            prompt_template=compiled_prompt,
            prompt_template_model=template_model,
            prompt_template_optional_params=template_optional_params,
            completed_messages=None,
        )

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        return run_async_function(
            self.async_log_success_event, kwargs, response_obj, start_time, end_time
        )

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        standard_callback_dynamic_params = kwargs.get(
            "standard_callback_dynamic_params"
        )
        langfuse_logger_to_use = LangFuseHandler.get_langfuse_logger_for_request(
            globalLangfuseLogger=self,
            standard_callback_dynamic_params=standard_callback_dynamic_params,
            in_memory_dynamic_logger_cache=in_memory_dynamic_logger_cache,
        )
        langfuse_logger_to_use.log_event_on_langfuse(
            kwargs=kwargs,
            response_obj=response_obj,
            start_time=start_time,
            end_time=end_time,
            user_id=kwargs.get("user", None),
        )

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        standard_callback_dynamic_params = kwargs.get(
            "standard_callback_dynamic_params"
        )
        langfuse_logger_to_use = LangFuseHandler.get_langfuse_logger_for_request(
            globalLangfuseLogger=self,
            standard_callback_dynamic_params=standard_callback_dynamic_params,
            in_memory_dynamic_logger_cache=in_memory_dynamic_logger_cache,
        )
        standard_logging_object = cast(
            Optional[StandardLoggingPayload],
            kwargs.get("standard_logging_object", None),
        )
        if standard_logging_object is None:
            return
        langfuse_logger_to_use.log_event_on_langfuse(
            start_time=start_time,
            end_time=end_time,
            response_obj=None,
            user_id=kwargs.get("user", None),
            status_message=standard_logging_object["error_str"],
            level="ERROR",
            kwargs=kwargs,
        )

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\util.py ===
# Natural Language Toolkit: Tokenizer Utilities
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

from re import finditer
from xml.sax.saxutils import escape, unescape


def string_span_tokenize(s, sep):
    r"""
    Return the offsets of the tokens in *s*, as a sequence of ``(start, end)``
    tuples, by splitting the string at each occurrence of *sep*.

        >>> from nltk.tokenize.util import string_span_tokenize
        >>> s = '''Good muffins cost $3.88\nin New York.  Please buy me
        ... two of them.\n\nThanks.'''
        >>> list(string_span_tokenize(s, " ")) # doctest: +NORMALIZE_WHITESPACE
        [(0, 4), (5, 12), (13, 17), (18, 26), (27, 30), (31, 36), (37, 37),
        (38, 44), (45, 48), (49, 55), (56, 58), (59, 73)]

    :param s: the string to be tokenized
    :type s: str
    :param sep: the token separator
    :type sep: str
    :rtype: iter(tuple(int, int))
    """
    if len(sep) == 0:
        raise ValueError("Token delimiter must not be empty")
    left = 0
    while True:
        try:
            right = s.index(sep, left)
            if right != 0:
                yield left, right
        except ValueError:
            if left != len(s):
                yield left, len(s)
            break

        left = right + len(sep)


def regexp_span_tokenize(s, regexp):
    r"""
    Return the offsets of the tokens in *s*, as a sequence of ``(start, end)``
    tuples, by splitting the string at each successive match of *regexp*.

        >>> from nltk.tokenize.util import regexp_span_tokenize
        >>> s = '''Good muffins cost $3.88\nin New York.  Please buy me
        ... two of them.\n\nThanks.'''
        >>> list(regexp_span_tokenize(s, r'\s')) # doctest: +NORMALIZE_WHITESPACE
        [(0, 4), (5, 12), (13, 17), (18, 23), (24, 26), (27, 30), (31, 36),
        (38, 44), (45, 48), (49, 51), (52, 55), (56, 58), (59, 64), (66, 73)]

    :param s: the string to be tokenized
    :type s: str
    :param regexp: regular expression that matches token separators (must not be empty)
    :type regexp: str
    :rtype: iter(tuple(int, int))
    """
    left = 0
    for m in finditer(regexp, s):
        right, next = m.span()
        if right != left:
            yield left, right
        left = next
    yield left, len(s)


def spans_to_relative(spans):
    r"""
    Return a sequence of relative spans, given a sequence of spans.

        >>> from nltk.tokenize import WhitespaceTokenizer
        >>> from nltk.tokenize.util import spans_to_relative
        >>> s = '''Good muffins cost $3.88\nin New York.  Please buy me
        ... two of them.\n\nThanks.'''
        >>> list(spans_to_relative(WhitespaceTokenizer().span_tokenize(s))) # doctest: +NORMALIZE_WHITESPACE
        [(0, 4), (1, 7), (1, 4), (1, 5), (1, 2), (1, 3), (1, 5), (2, 6),
        (1, 3), (1, 2), (1, 3), (1, 2), (1, 5), (2, 7)]

    :param spans: a sequence of (start, end) offsets of the tokens
    :type spans: iter(tuple(int, int))
    :rtype: iter(tuple(int, int))
    """
    prev = 0
    for left, right in spans:
        yield left - prev, right - left
        prev = right


class CJKChars:
    """
    An object that enumerates the code points of the CJK characters as listed on
    https://en.wikipedia.org/wiki/Basic_Multilingual_Plane#Basic_Multilingual_Plane

    This is a Python port of the CJK code point enumerations of Moses tokenizer:
    https://github.com/moses-smt/mosesdecoder/blob/master/scripts/tokenizer/detokenizer.perl#L309
    """

    # Hangul Jamo (1100–11FF)
    Hangul_Jamo = (4352, 4607)  # (ord(u"\u1100"), ord(u"\u11ff"))

    # CJK Radicals Supplement (2E80–2EFF)
    # Kangxi Radicals (2F00–2FDF)
    # Ideographic Description Characters (2FF0–2FFF)
    # CJK Symbols and Punctuation (3000–303F)
    # Hiragana (3040–309F)
    # Katakana (30A0–30FF)
    # Bopomofo (3100–312F)
    # Hangul Compatibility Jamo (3130–318F)
    # Kanbun (3190–319F)
    # Bopomofo Extended (31A0–31BF)
    # CJK Strokes (31C0–31EF)
    # Katakana Phonetic Extensions (31F0–31FF)
    # Enclosed CJK Letters and Months (3200–32FF)
    # CJK Compatibility (3300–33FF)
    # CJK Unified Ideographs Extension A (3400–4DBF)
    # Yijing Hexagram Symbols (4DC0–4DFF)
    # CJK Unified Ideographs (4E00–9FFF)
    # Yi Syllables (A000–A48F)
    # Yi Radicals (A490–A4CF)
    CJK_Radicals = (11904, 42191)  # (ord(u"\u2e80"), ord(u"\ua4cf"))

    # Phags-pa (A840–A87F)
    Phags_Pa = (43072, 43135)  # (ord(u"\ua840"), ord(u"\ua87f"))

    # Hangul Syllables (AC00–D7AF)
    Hangul_Syllables = (44032, 55215)  # (ord(u"\uAC00"), ord(u"\uD7AF"))

    # CJK Compatibility Ideographs (F900–FAFF)
    CJK_Compatibility_Ideographs = (63744, 64255)  # (ord(u"\uF900"), ord(u"\uFAFF"))

    # CJK Compatibility Forms (FE30–FE4F)
    CJK_Compatibility_Forms = (65072, 65103)  # (ord(u"\uFE30"), ord(u"\uFE4F"))

    # Range U+FF65–FFDC encodes halfwidth forms, of Katakana and Hangul characters
    Katakana_Hangul_Halfwidth = (65381, 65500)  # (ord(u"\uFF65"), ord(u"\uFFDC"))

    # Supplementary Ideographic Plane 20000–2FFFF
    Supplementary_Ideographic_Plane = (
        131072,
        196607,
    )  # (ord(u"\U00020000"), ord(u"\U0002FFFF"))

    ranges = [
        Hangul_Jamo,
        CJK_Radicals,
        Phags_Pa,
        Hangul_Syllables,
        CJK_Compatibility_Ideographs,
        CJK_Compatibility_Forms,
        Katakana_Hangul_Halfwidth,
        Supplementary_Ideographic_Plane,
    ]


def is_cjk(character):
    """
    Python port of Moses' code to check for CJK character.

    >>> CJKChars().ranges
    [(4352, 4607), (11904, 42191), (43072, 43135), (44032, 55215), (63744, 64255), (65072, 65103), (65381, 65500), (131072, 196607)]
    >>> is_cjk(u'\u33fe')
    True
    >>> is_cjk(u'\uFE5F')
    False

    :param character: The character that needs to be checked.
    :type character: char
    :return: bool
    """
    return any(
        [
            start <= ord(character) <= end
            for start, end in [
                (4352, 4607),
                (11904, 42191),
                (43072, 43135),
                (44032, 55215),
                (63744, 64255),
                (65072, 65103),
                (65381, 65500),
                (131072, 196607),
            ]
        ]
    )


def xml_escape(text):
    """
    This function transforms the input text into an "escaped" version suitable
    for well-formed XML formatting.

    Note that the default xml.sax.saxutils.escape() function don't escape
    some characters that Moses does so we have to manually add them to the
    entities dictionary.

        >>> input_str = ''')| & < > ' " ] ['''
        >>> expected_output =  ''')| &amp; &lt; &gt; ' " ] ['''
        >>> escape(input_str) == expected_output
        True
        >>> xml_escape(input_str)
        ')&#124; &amp; &lt; &gt; &apos; &quot; &#93; &#91;'

    :param text: The text that needs to be escaped.
    :type text: str
    :rtype: str
    """
    return escape(
        text,
        entities={
            r"'": r"&apos;",
            r'"': r"&quot;",
            r"|": r"&#124;",
            r"[": r"&#91;",
            r"]": r"&#93;",
        },
    )


def xml_unescape(text):
    """
    This function transforms the "escaped" version suitable
    for well-formed XML formatting into humanly-readable string.

    Note that the default xml.sax.saxutils.unescape() function don't unescape
    some characters that Moses does so we have to manually add them to the
    entities dictionary.

        >>> from xml.sax.saxutils import unescape
        >>> s = ')&#124; &amp; &lt; &gt; &apos; &quot; &#93; &#91;'
        >>> expected = ''')| & < > \' " ] ['''
        >>> xml_unescape(s) == expected
        True

    :param text: The text that needs to be unescaped.
    :type text: str
    :rtype: str
    """
    return unescape(
        text,
        entities={
            r"&apos;": r"'",
            r"&quot;": r'"',
            r"&#124;": r"|",
            r"&#91;": r"[",
            r"&#93;": r"]",
        },
    )


def align_tokens(tokens, sentence):
    """
    This module attempt to find the offsets of the tokens in *s*, as a sequence
    of ``(start, end)`` tuples, given the tokens and also the source string.

        >>> from nltk.tokenize import TreebankWordTokenizer
        >>> from nltk.tokenize.util import align_tokens
        >>> s = str("The plane, bound for St Petersburg, crashed in Egypt's "
        ... "Sinai desert just 23 minutes after take-off from Sharm el-Sheikh "
        ... "on Saturday.")
        >>> tokens = TreebankWordTokenizer().tokenize(s)
        >>> expected = [(0, 3), (4, 9), (9, 10), (11, 16), (17, 20), (21, 23),
        ... (24, 34), (34, 35), (36, 43), (44, 46), (47, 52), (52, 54),
        ... (55, 60), (61, 67), (68, 72), (73, 75), (76, 83), (84, 89),
        ... (90, 98), (99, 103), (104, 109), (110, 119), (120, 122),
        ... (123, 131), (131, 132)]
        >>> output = list(align_tokens(tokens, s))
        >>> len(tokens) == len(expected) == len(output)  # Check that length of tokens and tuples are the same.
        True
        >>> expected == list(align_tokens(tokens, s))  # Check that the output is as expected.
        True
        >>> tokens == [s[start:end] for start, end in output]  # Check that the slices of the string corresponds to the tokens.
        True

    :param tokens: The list of strings that are the result of tokenization
    :type tokens: list(str)
    :param sentence: The original string
    :type sentence: str
    :rtype: list(tuple(int,int))
    """
    point = 0
    offsets = []
    for token in tokens:
        try:
            start = sentence.index(token, point)
        except ValueError as e:
            raise ValueError(f'substring "{token}" not found in "{sentence}"') from e
        point = start + len(token)
        offsets.append((start, point))
    return offsets

# === NexusCore/myenv\Lib\site-packages\pip\_internal\cli\parser.py ===
"""Base option parser setup"""

import logging
import optparse
import shutil
import sys
import textwrap
from contextlib import suppress
from typing import Any, Dict, Generator, List, NoReturn, Optional, Tuple

from pip._internal.cli.status_codes import UNKNOWN_ERROR
from pip._internal.configuration import Configuration, ConfigurationError
from pip._internal.utils.misc import redact_auth_from_url, strtobool

logger = logging.getLogger(__name__)


class PrettyHelpFormatter(optparse.IndentedHelpFormatter):
    """A prettier/less verbose help formatter for optparse."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # help position must be aligned with __init__.parseopts.description
        kwargs["max_help_position"] = 30
        kwargs["indent_increment"] = 1
        kwargs["width"] = shutil.get_terminal_size()[0] - 2
        super().__init__(*args, **kwargs)

    def format_option_strings(self, option: optparse.Option) -> str:
        return self._format_option_strings(option)

    def _format_option_strings(
        self, option: optparse.Option, mvarfmt: str = " <{}>", optsep: str = ", "
    ) -> str:
        """
        Return a comma-separated list of option strings and metavars.

        :param option:  tuple of (short opt, long opt), e.g: ('-f', '--format')
        :param mvarfmt: metavar format string
        :param optsep:  separator
        """
        opts = []

        if option._short_opts:
            opts.append(option._short_opts[0])
        if option._long_opts:
            opts.append(option._long_opts[0])
        if len(opts) > 1:
            opts.insert(1, optsep)

        if option.takes_value():
            assert option.dest is not None
            metavar = option.metavar or option.dest.lower()
            opts.append(mvarfmt.format(metavar.lower()))

        return "".join(opts)

    def format_heading(self, heading: str) -> str:
        if heading == "Options":
            return ""
        return heading + ":\n"

    def format_usage(self, usage: str) -> str:
        """
        Ensure there is only one newline between usage and the first heading
        if there is no description.
        """
        msg = "\nUsage: {}\n".format(self.indent_lines(textwrap.dedent(usage), "  "))
        return msg

    def format_description(self, description: Optional[str]) -> str:
        # leave full control over description to us
        if description:
            if hasattr(self.parser, "main"):
                label = "Commands"
            else:
                label = "Description"
            # some doc strings have initial newlines, some don't
            description = description.lstrip("\n")
            # some doc strings have final newlines and spaces, some don't
            description = description.rstrip()
            # dedent, then reindent
            description = self.indent_lines(textwrap.dedent(description), "  ")
            description = f"{label}:\n{description}\n"
            return description
        else:
            return ""

    def format_epilog(self, epilog: Optional[str]) -> str:
        # leave full control over epilog to us
        if epilog:
            return epilog
        else:
            return ""

    def indent_lines(self, text: str, indent: str) -> str:
        new_lines = [indent + line for line in text.split("\n")]
        return "\n".join(new_lines)


class UpdatingDefaultsHelpFormatter(PrettyHelpFormatter):
    """Custom help formatter for use in ConfigOptionParser.

    This is updates the defaults before expanding them, allowing
    them to show up correctly in the help listing.

    Also redact auth from url type options
    """

    def expand_default(self, option: optparse.Option) -> str:
        default_values = None
        if self.parser is not None:
            assert isinstance(self.parser, ConfigOptionParser)
            self.parser._update_defaults(self.parser.defaults)
            assert option.dest is not None
            default_values = self.parser.defaults.get(option.dest)
        help_text = super().expand_default(option)

        if default_values and option.metavar == "URL":
            if isinstance(default_values, str):
                default_values = [default_values]

            # If its not a list, we should abort and just return the help text
            if not isinstance(default_values, list):
                default_values = []

            for val in default_values:
                help_text = help_text.replace(val, redact_auth_from_url(val))

        return help_text


class CustomOptionParser(optparse.OptionParser):
    def insert_option_group(
        self, idx: int, *args: Any, **kwargs: Any
    ) -> optparse.OptionGroup:
        """Insert an OptionGroup at a given position."""
        group = self.add_option_group(*args, **kwargs)

        self.option_groups.pop()
        self.option_groups.insert(idx, group)

        return group

    @property
    def option_list_all(self) -> List[optparse.Option]:
        """Get a list of all options, including those in option groups."""
        res = self.option_list[:]
        for i in self.option_groups:
            res.extend(i.option_list)

        return res


class ConfigOptionParser(CustomOptionParser):
    """Custom option parser which updates its defaults by checking the
    configuration files and environmental variables"""

    def __init__(
        self,
        *args: Any,
        name: str,
        isolated: bool = False,
        **kwargs: Any,
    ) -> None:
        self.name = name
        self.config = Configuration(isolated)

        assert self.name
        super().__init__(*args, **kwargs)

    def check_default(self, option: optparse.Option, key: str, val: Any) -> Any:
        try:
            return option.check_value(key, val)
        except optparse.OptionValueError as exc:
            print(f"An error occurred during configuration: {exc}")
            sys.exit(3)

    def _get_ordered_configuration_items(
        self,
    ) -> Generator[Tuple[str, Any], None, None]:
        # Configuration gives keys in an unordered manner. Order them.
        override_order = ["global", self.name, ":env:"]

        # Pool the options into different groups
        section_items: Dict[str, List[Tuple[str, Any]]] = {
            name: [] for name in override_order
        }
        for section_key, val in self.config.items():
            # ignore empty values
            if not val:
                logger.debug(
                    "Ignoring configuration key '%s' as it's value is empty.",
                    section_key,
                )
                continue

            section, key = section_key.split(".", 1)
            if section in override_order:
                section_items[section].append((key, val))

        # Yield each group in their override order
        for section in override_order:
            for key, val in section_items[section]:
                yield key, val

    def _update_defaults(self, defaults: Dict[str, Any]) -> Dict[str, Any]:
        """Updates the given defaults with values from the config files and
        the environ. Does a little special handling for certain types of
        options (lists)."""

        # Accumulate complex default state.
        self.values = optparse.Values(self.defaults)
        late_eval = set()
        # Then set the options with those values
        for key, val in self._get_ordered_configuration_items():
            # '--' because configuration supports only long names
            option = self.get_option("--" + key)

            # Ignore options not present in this parser. E.g. non-globals put
            # in [global] by users that want them to apply to all applicable
            # commands.
            if option is None:
                continue

            assert option.dest is not None

            if option.action in ("store_true", "store_false"):
                try:
                    val = strtobool(val)
                except ValueError:
                    self.error(
                        f"{val} is not a valid value for {key} option, "
                        "please specify a boolean value like yes/no, "
                        "true/false or 1/0 instead."
                    )
            elif option.action == "count":
                with suppress(ValueError):
                    val = strtobool(val)
                with suppress(ValueError):
                    val = int(val)
                if not isinstance(val, int) or val < 0:
                    self.error(
                        f"{val} is not a valid value for {key} option, "
                        "please instead specify either a non-negative integer "
                        "or a boolean value like yes/no or false/true "
                        "which is equivalent to 1/0."
                    )
            elif option.action == "append":
                val = val.split()
                val = [self.check_default(option, key, v) for v in val]
            elif option.action == "callback":
                assert option.callback is not None
                late_eval.add(option.dest)
                opt_str = option.get_opt_string()
                val = option.convert_value(opt_str, val)
                # From take_action
                args = option.callback_args or ()
                kwargs = option.callback_kwargs or {}
                option.callback(option, opt_str, val, self, *args, **kwargs)
            else:
                val = self.check_default(option, key, val)

            defaults[option.dest] = val

        for key in late_eval:
            defaults[key] = getattr(self.values, key)
        self.values = None
        return defaults

    def get_default_values(self) -> optparse.Values:
        """Overriding to make updating the defaults after instantiation of
        the option parser possible, _update_defaults() does the dirty work."""
        if not self.process_default_values:
            # Old, pre-Optik 1.5 behaviour.
            return optparse.Values(self.defaults)

        # Load the configuration, or error out in case of an error
        try:
            self.config.load()
        except ConfigurationError as err:
            self.exit(UNKNOWN_ERROR, str(err))

        defaults = self._update_defaults(self.defaults.copy())  # ours
        for option in self._get_all_options():
            assert option.dest is not None
            default = defaults.get(option.dest)
            if isinstance(default, str):
                opt_str = option.get_opt_string()
                defaults[option.dest] = option.check_value(opt_str, default)
        return optparse.Values(defaults)

    def error(self, msg: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(UNKNOWN_ERROR, f"{msg}\n")

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc2315.py ===
#
# This file is part of pyasn1-modules software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
# PKCS#7 message syntax
#
# ASN.1 source from:
# https://opensource.apple.com/source/Security/Security-55179.1/libsecurity_asn1/asn1/pkcs7.asn.auto.html
#
# Sample captures from:
# openssl crl2pkcs7 -nocrl -certfile cert1.cer -out outfile.p7b
#
from pyasn1_modules.rfc2459 import *


class Attribute(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type', AttributeType()),
        namedtype.NamedType('values', univ.SetOf(componentType=AttributeValue()))
    )


class AttributeValueAssertion(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('attributeType', AttributeType()),
        namedtype.NamedType('attributeValue', AttributeValue(),
                            openType=opentype.OpenType('type', certificateAttributesMap))
    )


pkcs_7 = univ.ObjectIdentifier('1.2.840.113549.1.7')
data = univ.ObjectIdentifier('1.2.840.113549.1.7.1')
signedData = univ.ObjectIdentifier('1.2.840.113549.1.7.2')
envelopedData = univ.ObjectIdentifier('1.2.840.113549.1.7.3')
signedAndEnvelopedData = univ.ObjectIdentifier('1.2.840.113549.1.7.4')
digestedData = univ.ObjectIdentifier('1.2.840.113549.1.7.5')
encryptedData = univ.ObjectIdentifier('1.2.840.113549.1.7.6')


class ContentType(univ.ObjectIdentifier):
    pass


class ContentEncryptionAlgorithmIdentifier(AlgorithmIdentifier):
    pass


class EncryptedContent(univ.OctetString):
    pass


contentTypeMap = {}


class EncryptedContentInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('contentType', ContentType()),
        namedtype.NamedType('contentEncryptionAlgorithm', ContentEncryptionAlgorithmIdentifier()),
        namedtype.OptionalNamedType(
            'encryptedContent', EncryptedContent().subtype(
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)
            ),
            openType=opentype.OpenType('contentType', contentTypeMap)
        )
    )


class Version(univ.Integer):  # overrides x509.Version
    pass


class EncryptedData(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('version', Version()),
        namedtype.NamedType('encryptedContentInfo', EncryptedContentInfo())
    )


class DigestAlgorithmIdentifier(AlgorithmIdentifier):
    pass


class DigestAlgorithmIdentifiers(univ.SetOf):
    componentType = DigestAlgorithmIdentifier()


class Digest(univ.OctetString):
    pass


class ContentInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('contentType', ContentType()),
        namedtype.OptionalNamedType(
            'content',
            univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)),
            openType=opentype.OpenType('contentType', contentTypeMap)
        )
    )


class DigestedData(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('version', Version()),
        namedtype.NamedType('digestAlgorithm', DigestAlgorithmIdentifier()),
        namedtype.NamedType('contentInfo', ContentInfo()),
        namedtype.NamedType('digest', Digest())
    )


class IssuerAndSerialNumber(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('issuer', Name()),
        namedtype.NamedType('serialNumber', CertificateSerialNumber())
    )


class KeyEncryptionAlgorithmIdentifier(AlgorithmIdentifier):
    pass


class EncryptedKey(univ.OctetString):
    pass


class RecipientInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('version', Version()),
        namedtype.NamedType('issuerAndSerialNumber', IssuerAndSerialNumber()),
        namedtype.NamedType('keyEncryptionAlgorithm', KeyEncryptionAlgorithmIdentifier()),
        namedtype.NamedType('encryptedKey', EncryptedKey())
    )


class RecipientInfos(univ.SetOf):
    componentType = RecipientInfo()


class Attributes(univ.SetOf):
    componentType = Attribute()


class ExtendedCertificateInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('version', Version()),
        namedtype.NamedType('certificate', Certificate()),
        namedtype.NamedType('attributes', Attributes())
    )


class SignatureAlgorithmIdentifier(AlgorithmIdentifier):
    pass


class Signature(univ.BitString):
    pass


class ExtendedCertificate(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('extendedCertificateInfo', ExtendedCertificateInfo()),
        namedtype.NamedType('signatureAlgorithm', SignatureAlgorithmIdentifier()),
        namedtype.NamedType('signature', Signature())
    )


class ExtendedCertificateOrCertificate(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('certificate', Certificate()),
        namedtype.NamedType('extendedCertificate', ExtendedCertificate().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)))
    )


class ExtendedCertificatesAndCertificates(univ.SetOf):
    componentType = ExtendedCertificateOrCertificate()


class SerialNumber(univ.Integer):
    pass


class CRLEntry(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('userCertificate', SerialNumber()),
        namedtype.NamedType('revocationDate', useful.UTCTime())
    )


class TBSCertificateRevocationList(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('signature', AlgorithmIdentifier()),
        namedtype.NamedType('issuer', Name()),
        namedtype.NamedType('lastUpdate', useful.UTCTime()),
        namedtype.NamedType('nextUpdate', useful.UTCTime()),
        namedtype.OptionalNamedType('revokedCertificates', univ.SequenceOf(componentType=CRLEntry()))
    )


class CertificateRevocationList(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('tbsCertificateRevocationList', TBSCertificateRevocationList()),
        namedtype.NamedType('signatureAlgorithm', AlgorithmIdentifier()),
        namedtype.NamedType('signature', univ.BitString())
    )


class CertificateRevocationLists(univ.SetOf):
    componentType = CertificateRevocationList()


class DigestEncryptionAlgorithmIdentifier(AlgorithmIdentifier):
    pass


class EncryptedDigest(univ.OctetString):
    pass


class SignerInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('version', Version()),
        namedtype.NamedType('issuerAndSerialNumber', IssuerAndSerialNumber()),
        namedtype.NamedType('digestAlgorithm', DigestAlgorithmIdentifier()),
        namedtype.OptionalNamedType('authenticatedAttributes', Attributes().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.NamedType('digestEncryptionAlgorithm', DigestEncryptionAlgorithmIdentifier()),
        namedtype.NamedType('encryptedDigest', EncryptedDigest()),
        namedtype.OptionalNamedType('unauthenticatedAttributes', Attributes().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
    )


class SignerInfos(univ.SetOf):
    componentType = SignerInfo()


class SignedAndEnvelopedData(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('version', Version()),
        namedtype.NamedType('recipientInfos', RecipientInfos()),
        namedtype.NamedType('digestAlgorithms', DigestAlgorithmIdentifiers()),
        namedtype.NamedType('encryptedContentInfo', EncryptedContentInfo()),
        namedtype.OptionalNamedType('certificates', ExtendedCertificatesAndCertificates().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.OptionalNamedType('crls', CertificateRevocationLists().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
        namedtype.NamedType('signerInfos', SignerInfos())
    )


class EnvelopedData(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('version', Version()),
        namedtype.NamedType('recipientInfos', RecipientInfos()),
        namedtype.NamedType('encryptedContentInfo', EncryptedContentInfo())
    )


class DigestInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('digestAlgorithm', DigestAlgorithmIdentifier()),
        namedtype.NamedType('digest', Digest())
    )


class SignedData(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('version', Version()),
        namedtype.OptionalNamedType('digestAlgorithms', DigestAlgorithmIdentifiers()),
        namedtype.NamedType('contentInfo', ContentInfo()),
        namedtype.OptionalNamedType('certificates', ExtendedCertificatesAndCertificates().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.OptionalNamedType('crls', CertificateRevocationLists().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
        namedtype.OptionalNamedType('signerInfos', SignerInfos())
    )


class Data(univ.OctetString):
    pass

_contentTypeMapUpdate = {
    data: Data(),
    signedData: SignedData(),
    envelopedData: EnvelopedData(),
    signedAndEnvelopedData: SignedAndEnvelopedData(),
    digestedData: DigestedData(),
    encryptedData: EncryptedData()
}

contentTypeMap.update(_contentTypeMapUpdate)

# === NexusCore/openenv\Lib\site-packages\google\api_core\timeout.py ===
# Copyright 2017 Google LLC
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

"""Decorators for applying timeout arguments to functions.

These decorators are used to wrap API methods to apply either a
Deadline-dependent (recommended), constant (DEPRECATED) or exponential
(DEPRECATED) timeout argument.

For example, imagine an API method that can take a while to return results,
such as one that might block until a resource is ready:

.. code-block:: python

    def is_thing_ready(timeout=None):
        response = requests.get('https://example.com/is_thing_ready')
        response.raise_for_status()
        return response.json()

This module allows a function like this to be wrapped so that timeouts are
automatically determined, for example:

.. code-block:: python

    timeout_ = timeout.ExponentialTimeout()
    is_thing_ready_with_timeout = timeout_(is_thing_ready)

    for n in range(10):
        try:
            is_thing_ready_with_timeout({'example': 'data'})
        except:
            pass

In this example the first call to ``is_thing_ready`` will have a relatively
small timeout (like 1 second). If the resource is available and the request
completes quickly, the loop exits. But, if the resource isn't yet available
and the request times out, it'll be retried - this time with a larger timeout.

In the broader context these decorators are typically combined with
:mod:`google.api_core.retry` to implement API methods with a signature that
matches ``api_method(request, timeout=None, retry=None)``.
"""

from __future__ import unicode_literals

import datetime
import functools

from google.api_core import datetime_helpers

_DEFAULT_INITIAL_TIMEOUT = 5.0  # seconds
_DEFAULT_MAXIMUM_TIMEOUT = 30.0  # seconds
_DEFAULT_TIMEOUT_MULTIPLIER = 2.0
# If specified, must be in seconds. If none, deadline is not used in the
# timeout calculation.
_DEFAULT_DEADLINE = None


class TimeToDeadlineTimeout(object):
    """A decorator that decreases timeout set for an RPC based on how much time
    has left till its deadline. The deadline is calculated as
    ``now + initial_timeout`` when this decorator is first called for an rpc.

    In other words this decorator implements deadline semantics in terms of a
    sequence of decreasing timeouts t0 > t1 > t2 ... tn >= 0.

    Args:
        timeout (Optional[float]): the timeout (in seconds) to applied to the
            wrapped function. If `None`, the target function is expected to
            never timeout.
    """

    def __init__(self, timeout=None, clock=datetime_helpers.utcnow):
        self._timeout = timeout
        self._clock = clock

    def __call__(self, func):
        """Apply the timeout decorator.

        Args:
            func (Callable): The function to apply the timeout argument to.
                This function must accept a timeout keyword argument.

        Returns:
            Callable: The wrapped function.
        """

        first_attempt_timestamp = self._clock().timestamp()

        @functools.wraps(func)
        def func_with_timeout(*args, **kwargs):
            """Wrapped function that adds timeout."""

            if self._timeout is not None:
                # All calculations are in seconds
                now_timestamp = self._clock().timestamp()

                # To avoid usage of nonlocal but still have round timeout
                # numbers for first attempt (in most cases the only attempt made
                # for an RPC.
                if now_timestamp - first_attempt_timestamp < 0.001:
                    now_timestamp = first_attempt_timestamp

                time_since_first_attempt = now_timestamp - first_attempt_timestamp
                remaining_timeout = self._timeout - time_since_first_attempt

                # Although the `deadline` parameter in `google.api_core.retry.Retry`
                # is deprecated, and should be treated the same as the `timeout`,
                # it is still possible for the `deadline` argument in
                # `google.api_core.retry.Retry` to be larger than the `timeout`.
                # See https://github.com/googleapis/python-api-core/issues/654
                # Only positive non-zero timeouts are supported.
                # Revert back to the initial timeout for negative or 0 timeout values.
                if remaining_timeout < 1:
                    remaining_timeout = self._timeout

                kwargs["timeout"] = remaining_timeout

            return func(*args, **kwargs)

        return func_with_timeout

    def __str__(self):
        return "<TimeToDeadlineTimeout timeout={:.1f}>".format(self._timeout)


class ConstantTimeout(object):
    """A decorator that adds a constant timeout argument.

    DEPRECATED: use ``TimeToDeadlineTimeout`` instead.

    This is effectively equivalent to
    ``functools.partial(func, timeout=timeout)``.

    Args:
        timeout (Optional[float]): the timeout (in seconds) to applied to the
            wrapped function. If `None`, the target function is expected to
            never timeout.
    """

    def __init__(self, timeout=None):
        self._timeout = timeout

    def __call__(self, func):
        """Apply the timeout decorator.

        Args:
            func (Callable): The function to apply the timeout argument to.
                This function must accept a timeout keyword argument.

        Returns:
            Callable: The wrapped function.
        """

        @functools.wraps(func)
        def func_with_timeout(*args, **kwargs):
            """Wrapped function that adds timeout."""
            kwargs["timeout"] = self._timeout
            return func(*args, **kwargs)

        return func_with_timeout

    def __str__(self):
        return "<ConstantTimeout timeout={:.1f}>".format(self._timeout)


def _exponential_timeout_generator(initial, maximum, multiplier, deadline):
    """A generator that yields exponential timeout values.

    Args:
        initial (float): The initial timeout.
        maximum (float): The maximum timeout.
        multiplier (float): The multiplier applied to the timeout.
        deadline (float): The overall deadline across all invocations.

    Yields:
        float: A timeout value.
    """
    if deadline is not None:
        deadline_datetime = datetime_helpers.utcnow() + datetime.timedelta(
            seconds=deadline
        )
    else:
        deadline_datetime = datetime.datetime.max

    timeout = initial
    while True:
        now = datetime_helpers.utcnow()
        yield min(
            # The calculated timeout based on invocations.
            timeout,
            # The set maximum timeout.
            maximum,
            # The remaining time before the deadline is reached.
            float((deadline_datetime - now).seconds),
        )
        timeout = timeout * multiplier


class ExponentialTimeout(object):
    """A decorator that adds an exponentially increasing timeout argument.

    DEPRECATED: the concept of incrementing timeout exponentially has been
    deprecated. Use ``TimeToDeadlineTimeout`` instead.

    This is useful if a function is called multiple times. Each time the
    function is called this decorator will calculate a new timeout parameter
    based on the the number of times the function has been called.

    For example

    .. code-block:: python

    Args:
        initial (float): The initial timeout to pass.
        maximum (float): The maximum timeout for any one call.
        multiplier (float): The multiplier applied to the timeout for each
            invocation.
        deadline (Optional[float]): The overall deadline across all
            invocations. This is used to prevent a very large calculated
            timeout from pushing the overall execution time over the deadline.
            This is especially useful in conjunction with
            :mod:`google.api_core.retry`. If ``None``, the timeouts will not
            be adjusted to accommodate an overall deadline.
    """

    def __init__(
        self,
        initial=_DEFAULT_INITIAL_TIMEOUT,
        maximum=_DEFAULT_MAXIMUM_TIMEOUT,
        multiplier=_DEFAULT_TIMEOUT_MULTIPLIER,
        deadline=_DEFAULT_DEADLINE,
    ):
        self._initial = initial
        self._maximum = maximum
        self._multiplier = multiplier
        self._deadline = deadline

    def with_deadline(self, deadline):
        """Return a copy of this timeout with the given deadline.

        Args:
            deadline (float): The overall deadline across all invocations.

        Returns:
            ExponentialTimeout: A new instance with the given deadline.
        """
        return ExponentialTimeout(
            initial=self._initial,
            maximum=self._maximum,
            multiplier=self._multiplier,
            deadline=deadline,
        )

    def __call__(self, func):
        """Apply the timeout decorator.

        Args:
            func (Callable): The function to apply the timeout argument to.
                This function must accept a timeout keyword argument.

        Returns:
            Callable: The wrapped function.
        """
        timeouts = _exponential_timeout_generator(
            self._initial, self._maximum, self._multiplier, self._deadline
        )

        @functools.wraps(func)
        def func_with_timeout(*args, **kwargs):
            """Wrapped function that adds timeout."""
            kwargs["timeout"] = next(timeouts)
            return func(*args, **kwargs)

        return func_with_timeout

    def __str__(self):
        return (
            "<ExponentialTimeout initial={:.1f}, maximum={:.1f}, "
            "multiplier={:.1f}, deadline={:.1f}>".format(
                self._initial, self._maximum, self._multiplier, self._deadline
            )
        )

# === NexusCore/openenv\Lib\site-packages\google\api_core\operations_v1\transports\base.py ===
# -*- coding: utf-8 -*-
# Copyright 2020 Google LLC
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
import abc
import re
from typing import Awaitable, Callable, Optional, Sequence, Union

import google.api_core  # type: ignore
from google.api_core import exceptions as core_exceptions  # type: ignore
from google.api_core import gapic_v1  # type: ignore
from google.api_core import retry as retries  # type: ignore
from google.api_core import version
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.longrunning import operations_pb2
from google.oauth2 import service_account  # type: ignore
import google.protobuf
from google.protobuf import empty_pb2, json_format  # type: ignore
from grpc import Compression


PROTOBUF_VERSION = google.protobuf.__version__

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=version.__version__,
)


class OperationsTransport(abc.ABC):
    """Abstract transport class for Operations."""

    AUTH_SCOPES = ()

    DEFAULT_HOST: str = "longrunning.googleapis.com"

    def __init__(
        self,
        *,
        host: str = DEFAULT_HOST,
        # TODO(https://github.com/googleapis/python-api-core/issues/709): update type hint for credentials to include `google.auth.aio.Credentials`.
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        url_scheme="https",
        **kwargs,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to.
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.

                .. warning::
                    Important: If you accept a credential configuration (credential JSON/File/Stream)
                    from an external source for authentication to Google Cloud Platform, you must
                    validate it before providing it to any Google API or client library. Providing an
                    unvalidated credential configuration to Google APIs or libraries can compromise
                    the security of your systems and data. For more information, refer to
                    `Validate credential configurations from external sources`_.

                .. _Validate credential configurations from external sources:

                https://cloud.google.com/docs/authentication/external/externally-sourced-credentials
            scopes (Optional[Sequence[str]]): A list of scopes.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
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
        """
        maybe_url_match = re.match("^(?P<scheme>http(?:s)?://)?(?P<host>.*)$", host)
        if maybe_url_match is None:
            raise ValueError(
                f"Unexpected hostname structure: {host}"
            )  # pragma: NO COVER

        url_match_items = maybe_url_match.groupdict()

        host = f"{url_scheme}://{host}" if not url_match_items["scheme"] else host

        # Save the hostname. Default to port 443 (HTTPS) if none is specified.
        if ":" not in host:
            host += ":443"  # pragma: NO COVER
        self._host = host

        scopes_kwargs = {"scopes": scopes, "default_scopes": self.AUTH_SCOPES}

        # Save the scopes.
        self._scopes = scopes

        # If no credentials are provided, then determine the appropriate
        # defaults.
        if credentials and credentials_file:
            raise core_exceptions.DuplicateCredentialArgs(
                "'credentials_file' and 'credentials' are mutually exclusive"
            )

        if credentials_file is not None:
            credentials, _ = google.auth.load_credentials_from_file(
                credentials_file, **scopes_kwargs, quota_project_id=quota_project_id
            )

        elif credentials is None:
            credentials, _ = google.auth.default(
                **scopes_kwargs, quota_project_id=quota_project_id
            )

        # If the credentials are service account credentials, then always try to use self signed JWT.
        if (
            always_use_jwt_access
            and isinstance(credentials, service_account.Credentials)
            and hasattr(service_account.Credentials, "with_always_use_jwt_access")
        ):
            credentials = credentials.with_always_use_jwt_access(True)

        # Save the credentials.
        self._credentials = credentials

    def _prep_wrapped_messages(self, client_info):
        # Precompute the wrapped methods.
        self._wrapped_methods = {
            self.list_operations: gapic_v1.method.wrap_method(
                self.list_operations,
                default_retry=retries.Retry(
                    initial=0.5,
                    maximum=10.0,
                    multiplier=2.0,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=10.0,
                ),
                default_timeout=10.0,
                default_compression=Compression.NoCompression,
                client_info=client_info,
            ),
            self.get_operation: gapic_v1.method.wrap_method(
                self.get_operation,
                default_retry=retries.Retry(
                    initial=0.5,
                    maximum=10.0,
                    multiplier=2.0,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=10.0,
                ),
                default_timeout=10.0,
                default_compression=Compression.NoCompression,
                client_info=client_info,
            ),
            self.delete_operation: gapic_v1.method.wrap_method(
                self.delete_operation,
                default_retry=retries.Retry(
                    initial=0.5,
                    maximum=10.0,
                    multiplier=2.0,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=10.0,
                ),
                default_timeout=10.0,
                default_compression=Compression.NoCompression,
                client_info=client_info,
            ),
            self.cancel_operation: gapic_v1.method.wrap_method(
                self.cancel_operation,
                default_retry=retries.Retry(
                    initial=0.5,
                    maximum=10.0,
                    multiplier=2.0,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=10.0,
                ),
                default_timeout=10.0,
                default_compression=Compression.NoCompression,
                client_info=client_info,
            ),
        }

    def close(self):
        """Closes resources associated with the transport.

        .. warning::
             Only call this method if the transport is NOT shared
             with other clients - this may cause errors in other clients!
        """
        raise NotImplementedError()

    def _convert_protobuf_message_to_dict(
        self, message: google.protobuf.message.Message
    ):
        r"""Converts protobuf message to a dictionary.

        When the dictionary is encoded to JSON, it conforms to proto3 JSON spec.

        Args:
            message(google.protobuf.message.Message): The protocol buffers message
                instance to serialize.

        Returns:
            A dict representation of the protocol buffer message.
        """
        # TODO(https://github.com/googleapis/python-api-core/issues/643): For backwards compatibility
        # with protobuf 3.x 4.x, Remove once support for protobuf 3.x and 4.x is dropped.
        if PROTOBUF_VERSION[0:2] in ["3.", "4."]:
            result = json_format.MessageToDict(
                message,
                preserving_proto_field_name=True,
                including_default_value_fields=True,  # type: ignore # backward compatibility
            )
        else:
            result = json_format.MessageToDict(
                message,
                preserving_proto_field_name=True,
                always_print_fields_with_no_presence=True,
            )

        return result

    @property
    def list_operations(
        self,
    ) -> Callable[
        [operations_pb2.ListOperationsRequest],
        Union[
            operations_pb2.ListOperationsResponse,
            Awaitable[operations_pb2.ListOperationsResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def get_operation(
        self,
    ) -> Callable[
        [operations_pb2.GetOperationRequest],
        Union[operations_pb2.Operation, Awaitable[operations_pb2.Operation]],
    ]:
        raise NotImplementedError()

    @property
    def delete_operation(
        self,
    ) -> Callable[
        [operations_pb2.DeleteOperationRequest],
        Union[empty_pb2.Empty, Awaitable[empty_pb2.Empty]],
    ]:
        raise NotImplementedError()

    @property
    def cancel_operation(
        self,
    ) -> Callable[
        [operations_pb2.CancelOperationRequest],
        Union[empty_pb2.Empty, Awaitable[empty_pb2.Empty]],
    ]:
        raise NotImplementedError()


__all__ = ("OperationsTransport",)

# === NexusCore/openenv\Lib\site-packages\joblib\externals\loky\reusable_executor.py ===
###############################################################################
# Reusable ProcessPoolExecutor
#
# author: Thomas Moreau and Olivier Grisel
#
import time
import warnings
import threading
import multiprocessing as mp

from .process_executor import ProcessPoolExecutor, EXTRA_QUEUED_CALLS
from .backend.context import cpu_count
from .backend import get_context

__all__ = ["get_reusable_executor"]

# Singleton executor and id management
_executor_lock = threading.RLock()
_next_executor_id = 0
_executor = None
_executor_kwargs = None


def _get_next_executor_id():
    """Ensure that each successive executor instance has a unique, monotonic id.

    The purpose of this monotonic id is to help debug and test automated
    instance creation.
    """
    global _next_executor_id
    with _executor_lock:
        executor_id = _next_executor_id
        _next_executor_id += 1
        return executor_id


def get_reusable_executor(
    max_workers=None,
    context=None,
    timeout=10,
    kill_workers=False,
    reuse="auto",
    job_reducers=None,
    result_reducers=None,
    initializer=None,
    initargs=(),
    env=None,
):
    """Return the current ReusableExectutor instance.

    Start a new instance if it has not been started already or if the previous
    instance was left in a broken state.

    If the previous instance does not have the requested number of workers, the
    executor is dynamically resized to adjust the number of workers prior to
    returning.

    Reusing a singleton instance spares the overhead of starting new worker
    processes and importing common python packages each time.

    ``max_workers`` controls the maximum number of tasks that can be running in
    parallel in worker processes. By default this is set to the number of
    CPUs on the host.

    Setting ``timeout`` (in seconds) makes idle workers automatically shutdown
    so as to release system resources. New workers are respawn upon submission
    of new tasks so that ``max_workers`` are available to accept the newly
    submitted tasks. Setting ``timeout`` to around 100 times the time required
    to spawn new processes and import packages in them (on the order of 100ms)
    ensures that the overhead of spawning workers is negligible.

    Setting ``kill_workers=True`` makes it possible to forcibly interrupt
    previously spawned jobs to get a new instance of the reusable executor
    with new constructor argument values.

    The ``job_reducers`` and ``result_reducers`` are used to customize the
    pickling of tasks and results send to the executor.

    When provided, the ``initializer`` is run first in newly spawned
    processes with argument ``initargs``.

    The environment variable in the child process are a copy of the values in
    the main process. One can provide a dict ``{ENV: VAL}`` where ``ENV`` and
    ``VAL`` are string literals to overwrite the environment variable ``ENV``
    in the child processes to value ``VAL``. The environment variables are set
    in the children before any module is loaded. This only works with the
    ``loky`` context.
    """
    _executor, _ = _ReusablePoolExecutor.get_reusable_executor(
        max_workers=max_workers,
        context=context,
        timeout=timeout,
        kill_workers=kill_workers,
        reuse=reuse,
        job_reducers=job_reducers,
        result_reducers=result_reducers,
        initializer=initializer,
        initargs=initargs,
        env=env,
    )
    return _executor


class _ReusablePoolExecutor(ProcessPoolExecutor):
    def __init__(
        self,
        submit_resize_lock,
        max_workers=None,
        context=None,
        timeout=None,
        executor_id=0,
        job_reducers=None,
        result_reducers=None,
        initializer=None,
        initargs=(),
        env=None,
    ):
        super().__init__(
            max_workers=max_workers,
            context=context,
            timeout=timeout,
            job_reducers=job_reducers,
            result_reducers=result_reducers,
            initializer=initializer,
            initargs=initargs,
            env=env,
        )
        self.executor_id = executor_id
        self._submit_resize_lock = submit_resize_lock

    @classmethod
    def get_reusable_executor(
        cls,
        max_workers=None,
        context=None,
        timeout=10,
        kill_workers=False,
        reuse="auto",
        job_reducers=None,
        result_reducers=None,
        initializer=None,
        initargs=(),
        env=None,
    ):
        with _executor_lock:
            global _executor, _executor_kwargs
            executor = _executor

            if max_workers is None:
                if reuse is True and executor is not None:
                    max_workers = executor._max_workers
                else:
                    max_workers = cpu_count()
            elif max_workers <= 0:
                raise ValueError(
                    f"max_workers must be greater than 0, got {max_workers}."
                )

            if isinstance(context, str):
                context = get_context(context)
            if context is not None and context.get_start_method() == "fork":
                raise ValueError(
                    "Cannot use reusable executor with the 'fork' context"
                )

            kwargs = dict(
                context=context,
                timeout=timeout,
                job_reducers=job_reducers,
                result_reducers=result_reducers,
                initializer=initializer,
                initargs=initargs,
                env=env,
            )
            if executor is None:
                is_reused = False
                mp.util.debug(
                    f"Create a executor with max_workers={max_workers}."
                )
                executor_id = _get_next_executor_id()
                _executor_kwargs = kwargs
                _executor = executor = cls(
                    _executor_lock,
                    max_workers=max_workers,
                    executor_id=executor_id,
                    **kwargs,
                )
            else:
                if reuse == "auto":
                    reuse = kwargs == _executor_kwargs
                if (
                    executor._flags.broken
                    or executor._flags.shutdown
                    or not reuse
                    or executor.queue_size < max_workers
                ):
                    if executor._flags.broken:
                        reason = "broken"
                    elif executor._flags.shutdown:
                        reason = "shutdown"
                    elif executor.queue_size < max_workers:
                        # Do not reuse the executor if the queue size is too
                        # small as this would lead to limited parallelism.
                        reason = "queue size is too small"
                    else:
                        reason = "arguments have changed"
                    mp.util.debug(
                        "Creating a new executor with max_workers="
                        f"{max_workers} as the previous instance cannot be "
                        f"reused ({reason})."
                    )
                    executor.shutdown(wait=True, kill_workers=kill_workers)
                    _executor = executor = _executor_kwargs = None
                    # Recursive call to build a new instance
                    return cls.get_reusable_executor(
                        max_workers=max_workers, **kwargs
                    )
                else:
                    mp.util.debug(
                        "Reusing existing executor with "
                        f"max_workers={executor._max_workers}."
                    )
                    is_reused = True
                    executor._resize(max_workers)

        return executor, is_reused

    def submit(self, fn, *args, **kwargs):
        with self._submit_resize_lock:
            return super().submit(fn, *args, **kwargs)

    def _resize(self, max_workers):
        with self._submit_resize_lock:
            if max_workers is None:
                raise ValueError("Trying to resize with max_workers=None")
            elif max_workers == self._max_workers:
                return

            if self._executor_manager_thread is None:
                # If the executor_manager_thread has not been started
                # then no processes have been spawned and we can just
                # update _max_workers and return
                self._max_workers = max_workers
                return

            self._wait_job_completion()

            # Some process might have returned due to timeout so check how many
            # children are still alive. Use the _process_management_lock to
            # ensure that no process are spawned or timeout during the resize.
            with self._processes_management_lock:
                processes = list(self._processes.values())
                nb_children_alive = sum(p.is_alive() for p in processes)
                self._max_workers = max_workers
                for _ in range(max_workers, nb_children_alive):
                    self._call_queue.put(None)
            while (
                len(self._processes) > max_workers and not self._flags.broken
            ):
                time.sleep(1e-3)

            self._adjust_process_count()
            processes = list(self._processes.values())
            while not all(p.is_alive() for p in processes):
                time.sleep(1e-3)

    def _wait_job_completion(self):
        """Wait for the cache to be empty before resizing the pool."""
        # Issue a warning to the user about the bad effect of this usage.
        if self._pending_work_items:
            warnings.warn(
                "Trying to resize an executor with running jobs: "
                "waiting for jobs completion before resizing.",
                UserWarning,
            )
            mp.util.debug(
                f"Executor {self.executor_id} waiting for jobs completion "
                "before resizing"
            )
        # Wait for the completion of the jobs
        while self._pending_work_items:
            time.sleep(1e-3)

    def _setup_queues(self, job_reducers, result_reducers):
        # As this executor can be resized, use a large queue size to avoid
        # underestimating capacity and introducing overhead
        # Also handle the case where the user set max_workers to a value larger
        # than cpu_count(), to avoid limiting the number of parallel jobs.

        min_queue_size = max(cpu_count(), self._max_workers)
        self.queue_size = 2 * min_queue_size + EXTRA_QUEUED_CALLS
        super()._setup_queues(
            job_reducers, result_reducers, queue_size=self.queue_size
        )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\huggingface\rerank\transformation.py ===
import os
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, TypedDict, Union

import httpx

import litellm
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.llms.base_llm.rerank.transformation import BaseRerankConfig
from litellm.secret_managers.main import get_secret_str
from litellm.types.rerank import (
    OptionalRerankParams,
    RerankBilledUnits,
    RerankResponse,
    RerankResponseDocument,
    RerankResponseMeta,
    RerankResponseResult,
    RerankTokens,
)
from litellm.utils import token_counter

from ..common_utils import HuggingFaceError

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj

    LoggingClass = LiteLLMLoggingObj
else:
    LoggingClass = Any


class HuggingFaceRerankResponseItem(TypedDict):
    """Type definition for HuggingFace rerank API response items."""

    index: int
    score: float
    text: Optional[str]  # Optional, included when return_text=True


class HuggingFaceRerankResponse(TypedDict):
    """Type definition for HuggingFace rerank API complete response."""

    # The response is a list of HuggingFaceRerankResponseItem
    pass


# Type alias for the actual response structure
HuggingFaceRerankResponseList = List[HuggingFaceRerankResponseItem]


class HuggingFaceRerankConfig(BaseRerankConfig):
    def get_api_base(self, model: str, api_base: Optional[str]) -> str:
        if api_base is not None:
            return api_base
        elif os.getenv("HF_API_BASE") is not None:
            return os.getenv("HF_API_BASE", "")
        elif os.getenv("HUGGINGFACE_API_BASE") is not None:
            return os.getenv("HUGGINGFACE_API_BASE", "")
        else:
            return "https://api-inference.huggingface.co"

    def get_complete_url(self, api_base: Optional[str], model: str) -> str:
        """
        Get the complete URL for the API call, including the /rerank suffix if necessary.
        """
        # Get base URL from api_base or default
        base_url = self.get_api_base(model=model, api_base=api_base)

        # Remove trailing slashes and ensure we have the /rerank endpoint
        base_url = base_url.rstrip("/")
        if not base_url.endswith("/rerank"):
            base_url = f"{base_url}/rerank"

        return base_url

    def get_supported_cohere_rerank_params(self, model: str) -> list:
        return [
            "query",
            "documents",
            "top_n",
            "return_documents",
        ]

    def map_cohere_rerank_params(
        self,
        non_default_params: Optional[dict],
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
        optional_rerank_params = {}
        if non_default_params is not None:
            for k, v in non_default_params.items():
                if k == "documents" and v is not None:
                    optional_rerank_params["texts"] = v
                elif k == "return_documents" and v is not None and isinstance(v, bool):
                    optional_rerank_params["return_text"] = v
                elif k == "top_n" and v is not None:
                    optional_rerank_params["top_n"] = v
                elif k == "documents" and v is not None:
                    optional_rerank_params["texts"] = v
                elif k == "query" and v is not None:
                    optional_rerank_params["query"] = v

        return OptionalRerankParams(**optional_rerank_params)  # type: ignore

    def validate_environment(
        self,
        headers: dict,
        model: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        # Get API credentials
        api_key, api_base = self.get_api_credentials(api_key=api_key, api_base=api_base)

        default_headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }

        if api_key:
            default_headers["Authorization"] = f"Bearer {api_key}"

        if "Authorization" in headers:
            default_headers["Authorization"] = headers["Authorization"]

        return {**default_headers, **headers}

    def transform_rerank_request(
        self,
        model: str,
        optional_rerank_params: Union[OptionalRerankParams, dict],
        headers: dict,
    ) -> dict:
        if "query" not in optional_rerank_params:
            raise ValueError("query is required for HuggingFace rerank")
        if "texts" not in optional_rerank_params:
            raise ValueError(
                "Cohere 'documents' param is required for HuggingFace rerank"
            )
        # Ensure return_text is a boolean value
        # HuggingFace API expects return_text parameter, corresponding to our return_documents parameter
        request_body = {
            "raw_scores": False,
            "truncate": False,
            "truncation_direction": "Right",
        }

        request_body.update(optional_rerank_params)

        return request_body

    def transform_rerank_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: RerankResponse,
        logging_obj: LoggingClass,
        api_key: Optional[str] = None,
        request_data: dict = {},
        optional_params: dict = {},
        litellm_params: dict = {},
    ) -> RerankResponse:
        try:
            raw_response_json: HuggingFaceRerankResponseList = raw_response.json()
        except Exception:
            raise HuggingFaceError(
                message=getattr(raw_response, "text", str(raw_response)),
                status_code=getattr(raw_response, "status_code", 500),
            )

        # Use standard litellm token counter for proper token estimation
        input_text = request_data.get("query", "")
        try:
            # Calculate tokens for the raw response JSON string
            response_text = str(raw_response_json)
            estimated_output_tokens = token_counter(model=model, text=response_text)

            # Calculate input tokens from query and documents
            query = request_data.get("query", "")
            documents = request_data.get("texts", [])

            # Convert documents to string if they're not already
            documents_text = ""
            for doc in documents:
                if isinstance(doc, str):
                    documents_text += doc + " "
                elif isinstance(doc, dict) and "text" in doc:
                    documents_text += doc["text"] + " "

            # Calculate input tokens using the same model
            input_text = query + " " + documents_text
            estimated_input_tokens = token_counter(model=model, text=input_text)
        except Exception:
            # Fallback to reasonable estimates if token counting fails
            estimated_output_tokens = (
                len(raw_response_json) * 10 if raw_response_json else 10
            )
            estimated_input_tokens = (
                len(input_text) * 4 if "input_text" in locals() else 0
            )

        _billed_units = RerankBilledUnits(search_units=1)
        _tokens = RerankTokens(
            input_tokens=estimated_input_tokens, output_tokens=estimated_output_tokens
        )
        rerank_meta = RerankResponseMeta(
            api_version={"version": "1.0"}, billed_units=_billed_units, tokens=_tokens
        )

        # Check if documents should be returned based on request parameters
        should_return_documents = request_data.get(
            "return_text", False
        ) or request_data.get("return_documents", False)
        original_documents = request_data.get("texts", [])

        results = []
        for item in raw_response_json:
            # Extract required fields with defaults to handle None values
            index = item.get("index")
            score = item.get("score")

            # Skip items that don't have required fields
            if index is None or score is None:
                continue

            # Create RerankResponseResult with required fields
            result = RerankResponseResult(index=index, relevance_score=score)

            # Add optional document field if needed
            if should_return_documents:
                text_content = item.get("text", "")

                # 1. First try to use text returned directly from API if available
                if text_content:
                    result["document"] = RerankResponseDocument(text=text_content)
                # 2. If no text in API response but original documents are available, use those
                elif original_documents and 0 <= item.get("index", -1) < len(
                    original_documents
                ):
                    doc = original_documents[item.get("index")]
                    if isinstance(doc, str):
                        result["document"] = RerankResponseDocument(text=doc)
                    elif isinstance(doc, dict) and "text" in doc:
                        result["document"] = RerankResponseDocument(text=doc["text"])

            results.append(result)

        return RerankResponse(
            id=str(uuid.uuid4()),
            results=results,
            meta=rerank_meta,
        )

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return HuggingFaceError(message=error_message, status_code=status_code)

    def get_api_credentials(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Get API key and base URL from multiple sources.
        Returns tuple of (api_key, api_base).

        Parameters:
            api_key: API key provided directly to this function, takes precedence over all other sources
            api_base: API base provided directly to this function, takes precedence over all other sources
        """
        # Get API key from multiple sources
        final_api_key = (
            api_key or litellm.huggingface_key or get_secret_str("HUGGINGFACE_API_KEY")
        )

        # Get API base from multiple sources
        final_api_base = (
            api_base
            or litellm.api_base
            or get_secret_str("HF_API_BASE")
            or get_secret_str("HUGGINGFACE_API_BASE")
        )

        return final_api_key, final_api_base

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\translate\test_stack_decoder.py ===
# Natural Language Toolkit: Stack decoder
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Tah Wei Hoon <hoon.tw@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Tests for stack decoder
"""

import unittest
from collections import defaultdict
from math import log

from nltk.translate import PhraseTable, StackDecoder
from nltk.translate.stack_decoder import _Hypothesis, _Stack


class TestStackDecoder(unittest.TestCase):
    def test_find_all_src_phrases(self):
        # arrange
        phrase_table = TestStackDecoder.create_fake_phrase_table()
        stack_decoder = StackDecoder(phrase_table, None)
        sentence = ("my", "hovercraft", "is", "full", "of", "eels")

        # act
        src_phrase_spans = stack_decoder.find_all_src_phrases(sentence)

        # assert
        self.assertEqual(src_phrase_spans[0], [2])  # 'my hovercraft'
        self.assertEqual(src_phrase_spans[1], [2])  # 'hovercraft'
        self.assertEqual(src_phrase_spans[2], [3])  # 'is'
        self.assertEqual(src_phrase_spans[3], [5, 6])  # 'full of', 'full of eels'
        self.assertFalse(src_phrase_spans[4])  # no entry starting with 'of'
        self.assertEqual(src_phrase_spans[5], [6])  # 'eels'

    def test_distortion_score(self):
        # arrange
        stack_decoder = StackDecoder(None, None)
        stack_decoder.distortion_factor = 0.5
        hypothesis = _Hypothesis()
        hypothesis.src_phrase_span = (3, 5)

        # act
        score = stack_decoder.distortion_score(hypothesis, (8, 10))

        # assert
        expected_score = log(stack_decoder.distortion_factor) * (8 - 5)
        self.assertEqual(score, expected_score)

    def test_distortion_score_of_first_expansion(self):
        # arrange
        stack_decoder = StackDecoder(None, None)
        stack_decoder.distortion_factor = 0.5
        hypothesis = _Hypothesis()

        # act
        score = stack_decoder.distortion_score(hypothesis, (8, 10))

        # assert
        # expansion from empty hypothesis always has zero distortion cost
        self.assertEqual(score, 0.0)

    def test_compute_future_costs(self):
        # arrange
        phrase_table = TestStackDecoder.create_fake_phrase_table()
        language_model = TestStackDecoder.create_fake_language_model()
        stack_decoder = StackDecoder(phrase_table, language_model)
        sentence = ("my", "hovercraft", "is", "full", "of", "eels")

        # act
        future_scores = stack_decoder.compute_future_scores(sentence)

        # assert
        self.assertEqual(
            future_scores[1][2],
            (
                phrase_table.translations_for(("hovercraft",))[0].log_prob
                + language_model.probability(("hovercraft",))
            ),
        )
        self.assertEqual(
            future_scores[0][2],
            (
                phrase_table.translations_for(("my", "hovercraft"))[0].log_prob
                + language_model.probability(("my", "hovercraft"))
            ),
        )

    def test_compute_future_costs_for_phrases_not_in_phrase_table(self):
        # arrange
        phrase_table = TestStackDecoder.create_fake_phrase_table()
        language_model = TestStackDecoder.create_fake_language_model()
        stack_decoder = StackDecoder(phrase_table, language_model)
        sentence = ("my", "hovercraft", "is", "full", "of", "eels")

        # act
        future_scores = stack_decoder.compute_future_scores(sentence)

        # assert
        self.assertEqual(
            future_scores[1][3],  # 'hovercraft is' is not in phrase table
            future_scores[1][2] + future_scores[2][3],
        )  # backoff

    def test_future_score(self):
        # arrange: sentence with 8 words; words 2, 3, 4 already translated
        hypothesis = _Hypothesis()
        hypothesis.untranslated_spans = lambda _: [(0, 2), (5, 8)]  # mock
        future_score_table = defaultdict(lambda: defaultdict(float))
        future_score_table[0][2] = 0.4
        future_score_table[5][8] = 0.5
        stack_decoder = StackDecoder(None, None)

        # act
        future_score = stack_decoder.future_score(hypothesis, future_score_table, 8)

        # assert
        self.assertEqual(future_score, 0.4 + 0.5)

    def test_valid_phrases(self):
        # arrange
        hypothesis = _Hypothesis()
        # mock untranslated_spans method
        hypothesis.untranslated_spans = lambda _: [(0, 2), (3, 6)]
        all_phrases_from = [[1, 4], [2], [], [5], [5, 6, 7], [], [7]]

        # act
        phrase_spans = StackDecoder.valid_phrases(all_phrases_from, hypothesis)

        # assert
        self.assertEqual(phrase_spans, [(0, 1), (1, 2), (3, 5), (4, 5), (4, 6)])

    @staticmethod
    def create_fake_phrase_table():
        phrase_table = PhraseTable()
        phrase_table.add(("hovercraft",), ("",), 0.8)
        phrase_table.add(("my", "hovercraft"), ("", ""), 0.7)
        phrase_table.add(("my", "cheese"), ("", ""), 0.7)
        phrase_table.add(("is",), ("",), 0.8)
        phrase_table.add(("is",), ("",), 0.5)
        phrase_table.add(("full", "of"), ("", ""), 0.01)
        phrase_table.add(("full", "of", "eels"), ("", "", ""), 0.5)
        phrase_table.add(("full", "of", "spam"), ("", ""), 0.5)
        phrase_table.add(("eels",), ("",), 0.5)
        phrase_table.add(("spam",), ("",), 0.5)
        return phrase_table

    @staticmethod
    def create_fake_language_model():
        # nltk.model should be used here once it is implemented
        language_prob = defaultdict(lambda: -999.0)
        language_prob[("my",)] = log(0.1)
        language_prob[("hovercraft",)] = log(0.1)
        language_prob[("is",)] = log(0.1)
        language_prob[("full",)] = log(0.1)
        language_prob[("of",)] = log(0.1)
        language_prob[("eels",)] = log(0.1)
        language_prob[("my", "hovercraft")] = log(0.3)
        language_model = type(
            "", (object,), {"probability": lambda _, phrase: language_prob[phrase]}
        )()
        return language_model


class TestHypothesis(unittest.TestCase):
    def setUp(self):
        root = _Hypothesis()
        child = _Hypothesis(
            raw_score=0.5,
            src_phrase_span=(3, 7),
            trg_phrase=("hello", "world"),
            previous=root,
        )
        grandchild = _Hypothesis(
            raw_score=0.4,
            src_phrase_span=(1, 2),
            trg_phrase=("and", "goodbye"),
            previous=child,
        )
        self.hypothesis_chain = grandchild

    def test_translation_so_far(self):
        # act
        translation = self.hypothesis_chain.translation_so_far()

        # assert
        self.assertEqual(translation, ["hello", "world", "and", "goodbye"])

    def test_translation_so_far_for_empty_hypothesis(self):
        # arrange
        hypothesis = _Hypothesis()

        # act
        translation = hypothesis.translation_so_far()

        # assert
        self.assertEqual(translation, [])

    def test_total_translated_words(self):
        # act
        total_translated_words = self.hypothesis_chain.total_translated_words()

        # assert
        self.assertEqual(total_translated_words, 5)

    def test_translated_positions(self):
        # act
        translated_positions = self.hypothesis_chain.translated_positions()

        # assert
        translated_positions.sort()
        self.assertEqual(translated_positions, [1, 3, 4, 5, 6])

    def test_untranslated_spans(self):
        # act
        untranslated_spans = self.hypothesis_chain.untranslated_spans(10)

        # assert
        self.assertEqual(untranslated_spans, [(0, 1), (2, 3), (7, 10)])

    def test_untranslated_spans_for_empty_hypothesis(self):
        # arrange
        hypothesis = _Hypothesis()

        # act
        untranslated_spans = hypothesis.untranslated_spans(10)

        # assert
        self.assertEqual(untranslated_spans, [(0, 10)])


class TestStack(unittest.TestCase):
    def test_push_bumps_off_worst_hypothesis_when_stack_is_full(self):
        # arrange
        stack = _Stack(3)
        poor_hypothesis = _Hypothesis(0.01)

        # act
        stack.push(_Hypothesis(0.2))
        stack.push(poor_hypothesis)
        stack.push(_Hypothesis(0.1))
        stack.push(_Hypothesis(0.3))

        # assert
        self.assertFalse(poor_hypothesis in stack)

    def test_push_removes_hypotheses_that_fall_below_beam_threshold(self):
        # arrange
        stack = _Stack(3, 0.5)
        poor_hypothesis = _Hypothesis(0.01)
        worse_hypothesis = _Hypothesis(0.009)

        # act
        stack.push(poor_hypothesis)
        stack.push(worse_hypothesis)
        stack.push(_Hypothesis(0.9))  # greatly superior hypothesis

        # assert
        self.assertFalse(poor_hypothesis in stack)
        self.assertFalse(worse_hypothesis in stack)

    def test_push_does_not_add_hypothesis_that_falls_below_beam_threshold(self):
        # arrange
        stack = _Stack(3, 0.5)
        poor_hypothesis = _Hypothesis(0.01)

        # act
        stack.push(_Hypothesis(0.9))  # greatly superior hypothesis
        stack.push(poor_hypothesis)

        # assert
        self.assertFalse(poor_hypothesis in stack)

    def test_best_returns_the_best_hypothesis(self):
        # arrange
        stack = _Stack(3)
        best_hypothesis = _Hypothesis(0.99)

        # act
        stack.push(_Hypothesis(0.0))
        stack.push(best_hypothesis)
        stack.push(_Hypothesis(0.5))

        # assert
        self.assertEqual(stack.best(), best_hypothesis)

    def test_best_returns_none_when_stack_is_empty(self):
        # arrange
        stack = _Stack(3)

        # assert
        self.assertEqual(stack.best(), None)

# === NexusCore/openenv\Lib\site-packages\numpy\ma\testutils.py ===
"""Miscellaneous functions for testing masked arrays and subclasses

:author: Pierre Gerard-Marchant
:contact: pierregm_at_uga_dot_edu

"""
import operator

import numpy as np
import numpy._core.umath as umath
import numpy.testing
from numpy import ndarray
from numpy.testing import (  # noqa: F401
    assert_,
    assert_allclose,
    assert_array_almost_equal_nulp,
    assert_raises,
    build_err_msg,
)

from .core import filled, getmask, mask_or, masked, masked_array, nomask

__all__masked = [
    'almost', 'approx', 'assert_almost_equal', 'assert_array_almost_equal',
    'assert_array_approx_equal', 'assert_array_compare',
    'assert_array_equal', 'assert_array_less', 'assert_close',
    'assert_equal', 'assert_equal_records', 'assert_mask_equal',
    'assert_not_equal', 'fail_if_array_equal',
    ]

# Include some normal test functions to avoid breaking other projects who
# have mistakenly included them from this file. SciPy is one. That is
# unfortunate, as some of these functions are not intended to work with
# masked arrays. But there was no way to tell before.
from unittest import TestCase  # noqa: F401

__some__from_testing = [
    'TestCase', 'assert_', 'assert_allclose', 'assert_array_almost_equal_nulp',
    'assert_raises'
    ]

__all__ = __all__masked + __some__from_testing  # noqa: PLE0605


def approx(a, b, fill_value=True, rtol=1e-5, atol=1e-8):
    """
    Returns true if all components of a and b are equal to given tolerances.

    If fill_value is True, masked values considered equal. Otherwise,
    masked values are considered unequal.  The relative error rtol should
    be positive and << 1.0 The absolute error atol comes into play for
    those elements of b that are very small or zero; it says how small a
    must be also.

    """
    m = mask_or(getmask(a), getmask(b))
    d1 = filled(a)
    d2 = filled(b)
    if d1.dtype.char == "O" or d2.dtype.char == "O":
        return np.equal(d1, d2).ravel()
    x = filled(
        masked_array(d1, copy=False, mask=m), fill_value
    ).astype(np.float64)
    y = filled(masked_array(d2, copy=False, mask=m), 1).astype(np.float64)
    d = np.less_equal(umath.absolute(x - y), atol + rtol * umath.absolute(y))
    return d.ravel()


def almost(a, b, decimal=6, fill_value=True):
    """
    Returns True if a and b are equal up to decimal places.

    If fill_value is True, masked values considered equal. Otherwise,
    masked values are considered unequal.

    """
    m = mask_or(getmask(a), getmask(b))
    d1 = filled(a)
    d2 = filled(b)
    if d1.dtype.char == "O" or d2.dtype.char == "O":
        return np.equal(d1, d2).ravel()
    x = filled(
        masked_array(d1, copy=False, mask=m), fill_value
    ).astype(np.float64)
    y = filled(masked_array(d2, copy=False, mask=m), 1).astype(np.float64)
    d = np.around(np.abs(x - y), decimal) <= 10.0 ** (-decimal)
    return d.ravel()


def _assert_equal_on_sequences(actual, desired, err_msg=''):
    """
    Asserts the equality of two non-array sequences.

    """
    assert_equal(len(actual), len(desired), err_msg)
    for k in range(len(desired)):
        assert_equal(actual[k], desired[k], f'item={k!r}\n{err_msg}')


def assert_equal_records(a, b):
    """
    Asserts that two records are equal.

    Pretty crude for now.

    """
    assert_equal(a.dtype, b.dtype)
    for f in a.dtype.names:
        (af, bf) = (operator.getitem(a, f), operator.getitem(b, f))
        if not (af is masked) and not (bf is masked):
            assert_equal(operator.getitem(a, f), operator.getitem(b, f))


def assert_equal(actual, desired, err_msg=''):
    """
    Asserts that two items are equal.

    """
    # Case #1: dictionary .....
    if isinstance(desired, dict):
        if not isinstance(actual, dict):
            raise AssertionError(repr(type(actual)))
        assert_equal(len(actual), len(desired), err_msg)
        for k, i in desired.items():
            if k not in actual:
                raise AssertionError(f"{k} not in {actual}")
            assert_equal(actual[k], desired[k], f'key={k!r}\n{err_msg}')
        return
    # Case #2: lists .....
    if isinstance(desired, (list, tuple)) and isinstance(actual, (list, tuple)):
        return _assert_equal_on_sequences(actual, desired, err_msg='')
    if not (isinstance(actual, ndarray) or isinstance(desired, ndarray)):
        msg = build_err_msg([actual, desired], err_msg,)
        if not desired == actual:
            raise AssertionError(msg)
        return
    # Case #4. arrays or equivalent
    if ((actual is masked) and not (desired is masked)) or \
            ((desired is masked) and not (actual is masked)):
        msg = build_err_msg([actual, desired],
                            err_msg, header='', names=('x', 'y'))
        raise ValueError(msg)
    actual = np.asanyarray(actual)
    desired = np.asanyarray(desired)
    (actual_dtype, desired_dtype) = (actual.dtype, desired.dtype)
    if actual_dtype.char == "S" and desired_dtype.char == "S":
        return _assert_equal_on_sequences(actual.tolist(),
                                          desired.tolist(),
                                          err_msg='')
    return assert_array_equal(actual, desired, err_msg)


def fail_if_equal(actual, desired, err_msg='',):
    """
    Raises an assertion error if two items are equal.

    """
    if isinstance(desired, dict):
        if not isinstance(actual, dict):
            raise AssertionError(repr(type(actual)))
        fail_if_equal(len(actual), len(desired), err_msg)
        for k, i in desired.items():
            if k not in actual:
                raise AssertionError(repr(k))
            fail_if_equal(actual[k], desired[k], f'key={k!r}\n{err_msg}')
        return
    if isinstance(desired, (list, tuple)) and isinstance(actual, (list, tuple)):
        fail_if_equal(len(actual), len(desired), err_msg)
        for k in range(len(desired)):
            fail_if_equal(actual[k], desired[k], f'item={k!r}\n{err_msg}')
        return
    if isinstance(actual, np.ndarray) or isinstance(desired, np.ndarray):
        return fail_if_array_equal(actual, desired, err_msg)
    msg = build_err_msg([actual, desired], err_msg)
    if not desired != actual:
        raise AssertionError(msg)


assert_not_equal = fail_if_equal


def assert_almost_equal(actual, desired, decimal=7, err_msg='', verbose=True):
    """
    Asserts that two items are almost equal.

    The test is equivalent to abs(desired-actual) < 0.5 * 10**(-decimal).

    """
    if isinstance(actual, np.ndarray) or isinstance(desired, np.ndarray):
        return assert_array_almost_equal(actual, desired, decimal=decimal,
                                         err_msg=err_msg, verbose=verbose)
    msg = build_err_msg([actual, desired],
                        err_msg=err_msg, verbose=verbose)
    if not round(abs(desired - actual), decimal) == 0:
        raise AssertionError(msg)


assert_close = assert_almost_equal


def assert_array_compare(comparison, x, y, err_msg='', verbose=True, header='',
                         fill_value=True):
    """
    Asserts that comparison between two masked arrays is satisfied.

    The comparison is elementwise.

    """
    # Allocate a common mask and refill
    m = mask_or(getmask(x), getmask(y))
    x = masked_array(x, copy=False, mask=m, keep_mask=False, subok=False)
    y = masked_array(y, copy=False, mask=m, keep_mask=False, subok=False)
    if ((x is masked) and not (y is masked)) or \
            ((y is masked) and not (x is masked)):
        msg = build_err_msg([x, y], err_msg=err_msg, verbose=verbose,
                            header=header, names=('x', 'y'))
        raise ValueError(msg)
    # OK, now run the basic tests on filled versions
    return np.testing.assert_array_compare(comparison,
                                           x.filled(fill_value),
                                           y.filled(fill_value),
                                           err_msg=err_msg,
                                           verbose=verbose, header=header)


def assert_array_equal(x, y, err_msg='', verbose=True):
    """
    Checks the elementwise equality of two masked arrays.

    """
    assert_array_compare(operator.__eq__, x, y,
                         err_msg=err_msg, verbose=verbose,
                         header='Arrays are not equal')


def fail_if_array_equal(x, y, err_msg='', verbose=True):
    """
    Raises an assertion error if two masked arrays are not equal elementwise.

    """
    def compare(x, y):
        return (not np.all(approx(x, y)))
    assert_array_compare(compare, x, y, err_msg=err_msg, verbose=verbose,
                         header='Arrays are not equal')


def assert_array_approx_equal(x, y, decimal=6, err_msg='', verbose=True):
    """
    Checks the equality of two masked arrays, up to given number odecimals.

    The equality is checked elementwise.

    """
    def compare(x, y):
        "Returns the result of the loose comparison between x and y)."
        return approx(x, y, rtol=10. ** -decimal)
    assert_array_compare(compare, x, y, err_msg=err_msg, verbose=verbose,
                         header='Arrays are not almost equal')


def assert_array_almost_equal(x, y, decimal=6, err_msg='', verbose=True):
    """
    Checks the equality of two masked arrays, up to given number odecimals.

    The equality is checked elementwise.

    """
    def compare(x, y):
        "Returns the result of the loose comparison between x and y)."
        return almost(x, y, decimal)
    assert_array_compare(compare, x, y, err_msg=err_msg, verbose=verbose,
                         header='Arrays are not almost equal')


def assert_array_less(x, y, err_msg='', verbose=True):
    """
    Checks that x is smaller than y elementwise.

    """
    assert_array_compare(operator.__lt__, x, y,
                         err_msg=err_msg, verbose=verbose,
                         header='Arrays are not less-ordered')


def assert_mask_equal(m1, m2, err_msg=''):
    """
    Asserts the equality of two masks.

    """
    if m1 is nomask:
        assert_(m2 is nomask)
    if m2 is nomask:
        assert_(m1 is nomask)
    assert_array_equal(m1, m2, err_msg=err_msg)

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\assistant_stream_event.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import Union, Optional
from typing_extensions import Literal, Annotated, TypeAlias

from .thread import Thread
from ..._utils import PropertyInfo
from ..._models import BaseModel
from .threads.run import Run
from .threads.message import Message
from ..shared.error_object import ErrorObject
from .threads.runs.run_step import RunStep
from .threads.message_delta_event import MessageDeltaEvent
from .threads.runs.run_step_delta_event import RunStepDeltaEvent

__all__ = [
    "AssistantStreamEvent",
    "ThreadCreated",
    "ThreadRunCreated",
    "ThreadRunQueued",
    "ThreadRunInProgress",
    "ThreadRunRequiresAction",
    "ThreadRunCompleted",
    "ThreadRunIncomplete",
    "ThreadRunFailed",
    "ThreadRunCancelling",
    "ThreadRunCancelled",
    "ThreadRunExpired",
    "ThreadRunStepCreated",
    "ThreadRunStepInProgress",
    "ThreadRunStepDelta",
    "ThreadRunStepCompleted",
    "ThreadRunStepFailed",
    "ThreadRunStepCancelled",
    "ThreadRunStepExpired",
    "ThreadMessageCreated",
    "ThreadMessageInProgress",
    "ThreadMessageDelta",
    "ThreadMessageCompleted",
    "ThreadMessageIncomplete",
    "ErrorEvent",
]


class ThreadCreated(BaseModel):
    data: Thread
    """
    Represents a thread that contains
    [messages](https://platform.openai.com/docs/api-reference/messages).
    """

    event: Literal["thread.created"]

    enabled: Optional[bool] = None
    """Whether to enable input audio transcription."""


class ThreadRunCreated(BaseModel):
    data: Run
    """
    Represents an execution run on a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.run.created"]


class ThreadRunQueued(BaseModel):
    data: Run
    """
    Represents an execution run on a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.run.queued"]


class ThreadRunInProgress(BaseModel):
    data: Run
    """
    Represents an execution run on a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.run.in_progress"]


class ThreadRunRequiresAction(BaseModel):
    data: Run
    """
    Represents an execution run on a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.run.requires_action"]


class ThreadRunCompleted(BaseModel):
    data: Run
    """
    Represents an execution run on a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.run.completed"]


class ThreadRunIncomplete(BaseModel):
    data: Run
    """
    Represents an execution run on a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.run.incomplete"]


class ThreadRunFailed(BaseModel):
    data: Run
    """
    Represents an execution run on a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.run.failed"]


class ThreadRunCancelling(BaseModel):
    data: Run
    """
    Represents an execution run on a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.run.cancelling"]


class ThreadRunCancelled(BaseModel):
    data: Run
    """
    Represents an execution run on a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.run.cancelled"]


class ThreadRunExpired(BaseModel):
    data: Run
    """
    Represents an execution run on a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.run.expired"]


class ThreadRunStepCreated(BaseModel):
    data: RunStep
    """Represents a step in execution of a run."""

    event: Literal["thread.run.step.created"]


class ThreadRunStepInProgress(BaseModel):
    data: RunStep
    """Represents a step in execution of a run."""

    event: Literal["thread.run.step.in_progress"]


class ThreadRunStepDelta(BaseModel):
    data: RunStepDeltaEvent
    """Represents a run step delta i.e.

    any changed fields on a run step during streaming.
    """

    event: Literal["thread.run.step.delta"]


class ThreadRunStepCompleted(BaseModel):
    data: RunStep
    """Represents a step in execution of a run."""

    event: Literal["thread.run.step.completed"]


class ThreadRunStepFailed(BaseModel):
    data: RunStep
    """Represents a step in execution of a run."""

    event: Literal["thread.run.step.failed"]


class ThreadRunStepCancelled(BaseModel):
    data: RunStep
    """Represents a step in execution of a run."""

    event: Literal["thread.run.step.cancelled"]


class ThreadRunStepExpired(BaseModel):
    data: RunStep
    """Represents a step in execution of a run."""

    event: Literal["thread.run.step.expired"]


class ThreadMessageCreated(BaseModel):
    data: Message
    """
    Represents a message within a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.message.created"]


class ThreadMessageInProgress(BaseModel):
    data: Message
    """
    Represents a message within a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.message.in_progress"]


class ThreadMessageDelta(BaseModel):
    data: MessageDeltaEvent
    """Represents a message delta i.e.

    any changed fields on a message during streaming.
    """

    event: Literal["thread.message.delta"]


class ThreadMessageCompleted(BaseModel):
    data: Message
    """
    Represents a message within a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.message.completed"]


class ThreadMessageIncomplete(BaseModel):
    data: Message
    """
    Represents a message within a
    [thread](https://platform.openai.com/docs/api-reference/threads).
    """

    event: Literal["thread.message.incomplete"]


class ErrorEvent(BaseModel):
    data: ErrorObject

    event: Literal["error"]


AssistantStreamEvent: TypeAlias = Annotated[
    Union[
        ThreadCreated,
        ThreadRunCreated,
        ThreadRunQueued,
        ThreadRunInProgress,
        ThreadRunRequiresAction,
        ThreadRunCompleted,
        ThreadRunIncomplete,
        ThreadRunFailed,
        ThreadRunCancelling,
        ThreadRunCancelled,
        ThreadRunExpired,
        ThreadRunStepCreated,
        ThreadRunStepInProgress,
        ThreadRunStepDelta,
        ThreadRunStepCompleted,
        ThreadRunStepFailed,
        ThreadRunStepCancelled,
        ThreadRunStepExpired,
        ThreadMessageCreated,
        ThreadMessageInProgress,
        ThreadMessageDelta,
        ThreadMessageCompleted,
        ThreadMessageIncomplete,
        ErrorEvent,
    ],
    PropertyInfo(discriminator="event"),
]

# === NexusCore/openenv\Lib\site-packages\pip\_internal\cli\parser.py ===
"""Base option parser setup"""

import logging
import optparse
import shutil
import sys
import textwrap
from contextlib import suppress
from typing import Any, Dict, Generator, List, NoReturn, Optional, Tuple

from pip._internal.cli.status_codes import UNKNOWN_ERROR
from pip._internal.configuration import Configuration, ConfigurationError
from pip._internal.utils.misc import redact_auth_from_url, strtobool

logger = logging.getLogger(__name__)


class PrettyHelpFormatter(optparse.IndentedHelpFormatter):
    """A prettier/less verbose help formatter for optparse."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # help position must be aligned with __init__.parseopts.description
        kwargs["max_help_position"] = 30
        kwargs["indent_increment"] = 1
        kwargs["width"] = shutil.get_terminal_size()[0] - 2
        super().__init__(*args, **kwargs)

    def format_option_strings(self, option: optparse.Option) -> str:
        return self._format_option_strings(option)

    def _format_option_strings(
        self, option: optparse.Option, mvarfmt: str = " <{}>", optsep: str = ", "
    ) -> str:
        """
        Return a comma-separated list of option strings and metavars.

        :param option:  tuple of (short opt, long opt), e.g: ('-f', '--format')
        :param mvarfmt: metavar format string
        :param optsep:  separator
        """
        opts = []

        if option._short_opts:
            opts.append(option._short_opts[0])
        if option._long_opts:
            opts.append(option._long_opts[0])
        if len(opts) > 1:
            opts.insert(1, optsep)

        if option.takes_value():
            assert option.dest is not None
            metavar = option.metavar or option.dest.lower()
            opts.append(mvarfmt.format(metavar.lower()))

        return "".join(opts)

    def format_heading(self, heading: str) -> str:
        if heading == "Options":
            return ""
        return heading + ":\n"

    def format_usage(self, usage: str) -> str:
        """
        Ensure there is only one newline between usage and the first heading
        if there is no description.
        """
        msg = "\nUsage: {}\n".format(self.indent_lines(textwrap.dedent(usage), "  "))
        return msg

    def format_description(self, description: Optional[str]) -> str:
        # leave full control over description to us
        if description:
            if hasattr(self.parser, "main"):
                label = "Commands"
            else:
                label = "Description"
            # some doc strings have initial newlines, some don't
            description = description.lstrip("\n")
            # some doc strings have final newlines and spaces, some don't
            description = description.rstrip()
            # dedent, then reindent
            description = self.indent_lines(textwrap.dedent(description), "  ")
            description = f"{label}:\n{description}\n"
            return description
        else:
            return ""

    def format_epilog(self, epilog: Optional[str]) -> str:
        # leave full control over epilog to us
        if epilog:
            return epilog
        else:
            return ""

    def indent_lines(self, text: str, indent: str) -> str:
        new_lines = [indent + line for line in text.split("\n")]
        return "\n".join(new_lines)


class UpdatingDefaultsHelpFormatter(PrettyHelpFormatter):
    """Custom help formatter for use in ConfigOptionParser.

    This is updates the defaults before expanding them, allowing
    them to show up correctly in the help listing.

    Also redact auth from url type options
    """

    def expand_default(self, option: optparse.Option) -> str:
        default_values = None
        if self.parser is not None:
            assert isinstance(self.parser, ConfigOptionParser)
            self.parser._update_defaults(self.parser.defaults)
            assert option.dest is not None
            default_values = self.parser.defaults.get(option.dest)
        help_text = super().expand_default(option)

        if default_values and option.metavar == "URL":
            if isinstance(default_values, str):
                default_values = [default_values]

            # If its not a list, we should abort and just return the help text
            if not isinstance(default_values, list):
                default_values = []

            for val in default_values:
                help_text = help_text.replace(val, redact_auth_from_url(val))

        return help_text


class CustomOptionParser(optparse.OptionParser):
    def insert_option_group(
        self, idx: int, *args: Any, **kwargs: Any
    ) -> optparse.OptionGroup:
        """Insert an OptionGroup at a given position."""
        group = self.add_option_group(*args, **kwargs)

        self.option_groups.pop()
        self.option_groups.insert(idx, group)

        return group

    @property
    def option_list_all(self) -> List[optparse.Option]:
        """Get a list of all options, including those in option groups."""
        res = self.option_list[:]
        for i in self.option_groups:
            res.extend(i.option_list)

        return res


class ConfigOptionParser(CustomOptionParser):
    """Custom option parser which updates its defaults by checking the
    configuration files and environmental variables"""

    def __init__(
        self,
        *args: Any,
        name: str,
        isolated: bool = False,
        **kwargs: Any,
    ) -> None:
        self.name = name
        self.config = Configuration(isolated)

        assert self.name
        super().__init__(*args, **kwargs)

    def check_default(self, option: optparse.Option, key: str, val: Any) -> Any:
        try:
            return option.check_value(key, val)
        except optparse.OptionValueError as exc:
            print(f"An error occurred during configuration: {exc}")
            sys.exit(3)

    def _get_ordered_configuration_items(
        self,
    ) -> Generator[Tuple[str, Any], None, None]:
        # Configuration gives keys in an unordered manner. Order them.
        override_order = ["global", self.name, ":env:"]

        # Pool the options into different groups
        section_items: Dict[str, List[Tuple[str, Any]]] = {
            name: [] for name in override_order
        }
        for section_key, val in self.config.items():
            # ignore empty values
            if not val:
                logger.debug(
                    "Ignoring configuration key '%s' as it's value is empty.",
                    section_key,
                )
                continue

            section, key = section_key.split(".", 1)
            if section in override_order:
                section_items[section].append((key, val))

        # Yield each group in their override order
        for section in override_order:
            for key, val in section_items[section]:
                yield key, val

    def _update_defaults(self, defaults: Dict[str, Any]) -> Dict[str, Any]:
        """Updates the given defaults with values from the config files and
        the environ. Does a little special handling for certain types of
        options (lists)."""

        # Accumulate complex default state.
        self.values = optparse.Values(self.defaults)
        late_eval = set()
        # Then set the options with those values
        for key, val in self._get_ordered_configuration_items():
            # '--' because configuration supports only long names
            option = self.get_option("--" + key)

            # Ignore options not present in this parser. E.g. non-globals put
            # in [global] by users that want them to apply to all applicable
            # commands.
            if option is None:
                continue

            assert option.dest is not None

            if option.action in ("store_true", "store_false"):
                try:
                    val = strtobool(val)
                except ValueError:
                    self.error(
                        f"{val} is not a valid value for {key} option, "
                        "please specify a boolean value like yes/no, "
                        "true/false or 1/0 instead."
                    )
            elif option.action == "count":
                with suppress(ValueError):
                    val = strtobool(val)
                with suppress(ValueError):
                    val = int(val)
                if not isinstance(val, int) or val < 0:
                    self.error(
                        f"{val} is not a valid value for {key} option, "
                        "please instead specify either a non-negative integer "
                        "or a boolean value like yes/no or false/true "
                        "which is equivalent to 1/0."
                    )
            elif option.action == "append":
                val = val.split()
                val = [self.check_default(option, key, v) for v in val]
            elif option.action == "callback":
                assert option.callback is not None
                late_eval.add(option.dest)
                opt_str = option.get_opt_string()
                val = option.convert_value(opt_str, val)
                # From take_action
                args = option.callback_args or ()
                kwargs = option.callback_kwargs or {}
                option.callback(option, opt_str, val, self, *args, **kwargs)
            else:
                val = self.check_default(option, key, val)

            defaults[option.dest] = val

        for key in late_eval:
            defaults[key] = getattr(self.values, key)
        self.values = None
        return defaults

    def get_default_values(self) -> optparse.Values:
        """Overriding to make updating the defaults after instantiation of
        the option parser possible, _update_defaults() does the dirty work."""
        if not self.process_default_values:
            # Old, pre-Optik 1.5 behaviour.
            return optparse.Values(self.defaults)

        # Load the configuration, or error out in case of an error
        try:
            self.config.load()
        except ConfigurationError as err:
            self.exit(UNKNOWN_ERROR, str(err))

        defaults = self._update_defaults(self.defaults.copy())  # ours
        for option in self._get_all_options():
            assert option.dest is not None
            default = defaults.get(option.dest)
            if isinstance(default, str):
                opt_str = option.get_opt_string()
                defaults[option.dest] = option.check_value(opt_str, default)
        return optparse.Values(defaults)

    def error(self, msg: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(UNKNOWN_ERROR, f"{msg}\n")

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\julia.py ===
"""
    pygments.lexers.julia
    ~~~~~~~~~~~~~~~~~~~~~

    Lexers for the Julia language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import Lexer, RegexLexer, bygroups, do_insertions, \
    words, include
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic, Whitespace
from pygments.util import shebang_matches
from pygments.lexers._julia_builtins import OPERATORS_LIST, DOTTED_OPERATORS_LIST, \
    KEYWORD_LIST, BUILTIN_LIST, LITERAL_LIST

__all__ = ['JuliaLexer', 'JuliaConsoleLexer']

# see https://docs.julialang.org/en/v1/manual/variables/#Allowed-Variable-Names
allowed_variable = \
    '(?:[a-zA-Z_\u00A1-\U0010ffff][a-zA-Z_0-9!\u00A1-\U0010ffff]*)'
# see https://github.com/JuliaLang/julia/blob/master/src/flisp/julia_opsuffs.h
operator_suffixes = r'[²³¹ʰʲʳʷʸˡˢˣᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁᵂᵃᵇᵈᵉᵍᵏᵐᵒᵖᵗᵘᵛᵝᵞᵟᵠᵡᵢᵣᵤᵥᵦᵧᵨᵩᵪᶜᶠᶥᶦᶫᶰᶸᶻᶿ′″‴‵‶‷⁗⁰ⁱ⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜⱼⱽ]*'

class JuliaLexer(RegexLexer):
    """
    For Julia source code.
    """

    name = 'Julia'
    url = 'https://julialang.org/'
    aliases = ['julia', 'jl']
    filenames = ['*.jl']
    mimetypes = ['text/x-julia', 'application/x-julia']
    version_added = '1.6'

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'[^\S\n]+', Whitespace),
            (r'#=', Comment.Multiline, "blockcomment"),
            (r'#.*$', Comment),
            (r'[\[\](),;]', Punctuation),

            # symbols
            #   intercept range expressions first
            (r'(' + allowed_variable + r')(\s*)(:)(' + allowed_variable + ')',
                bygroups(Name, Whitespace, Operator, Name)),
            #   then match :name which does not follow closing brackets, digits, or the
            #   ::, <:, and :> operators
            (r'(?<![\]):<>\d.])(:' + allowed_variable + ')', String.Symbol),

            # type assertions - excludes expressions like ::typeof(sin) and ::avec[1]
            (r'(?<=::)(\s*)(' + allowed_variable + r')\b(?![(\[])',
             bygroups(Whitespace, Keyword.Type)),
            # type comparisons
            # - MyType <: A or MyType >: A
            ('(' + allowed_variable + r')(\s*)([<>]:)(\s*)(' + allowed_variable + r')\b(?![(\[])',
                bygroups(Keyword.Type, Whitespace, Operator, Whitespace, Keyword.Type)),
            # - <: B or >: B
            (r'([<>]:)(\s*)(' + allowed_variable + r')\b(?![(\[])',
                bygroups(Operator, Whitespace, Keyword.Type)),
            # - A <: or A >:
            (r'\b(' + allowed_variable + r')(\s*)([<>]:)',
                bygroups(Keyword.Type, Whitespace, Operator)),

            # operators
            # Suffixes aren't actually allowed on all operators, but we'll ignore that
            # since those cases are invalid Julia code.
            (words([*OPERATORS_LIST, *DOTTED_OPERATORS_LIST],
                   suffix=operator_suffixes), Operator),
            (words(['.' + o for o in DOTTED_OPERATORS_LIST],
                   suffix=operator_suffixes), Operator),
            (words(['...', '..']), Operator),

            # NOTE
            # Patterns below work only for definition sites and thus hardly reliable.
            #
            # functions
            # (r'(function)(\s+)(' + allowed_variable + ')',
            #  bygroups(Keyword, Text, Name.Function)),

            # chars
            (r"'(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,3}|\\u[a-fA-F0-9]{1,4}|"
             r"\\U[a-fA-F0-9]{1,6}|[^\\\'\n])'", String.Char),

            # try to match trailing transpose
            (r'(?<=[.\w)\]])(\'' + operator_suffixes + ')+', Operator),

            # raw strings
            (r'(raw)(""")', bygroups(String.Affix, String), 'tqrawstring'),
            (r'(raw)(")', bygroups(String.Affix, String), 'rawstring'),
            # regular expressions
            (r'(r)(""")', bygroups(String.Affix, String.Regex), 'tqregex'),
            (r'(r)(")', bygroups(String.Affix, String.Regex), 'regex'),
            # other strings
            (r'(' + allowed_variable + ')?(""")',
             bygroups(String.Affix, String), 'tqstring'),
            (r'(' + allowed_variable + ')?(")',
             bygroups(String.Affix, String), 'string'),

            # backticks
            (r'(' + allowed_variable + ')?(```)',
             bygroups(String.Affix, String.Backtick), 'tqcommand'),
            (r'(' + allowed_variable + ')?(`)',
             bygroups(String.Affix, String.Backtick), 'command'),

            # type names
            # - names that begin a curly expression
            ('(' + allowed_variable + r')(\{)',
                bygroups(Keyword.Type, Punctuation), 'curly'),
            # - names as part of bare 'where'
            (r'(where)(\s+)(' + allowed_variable + ')',
                bygroups(Keyword, Whitespace, Keyword.Type)),
            # - curly expressions in general
            (r'(\{)', Punctuation, 'curly'),
            # - names as part of type declaration
            (r'(abstract|primitive)([ \t]+)(type\b)([\s()]+)(' +
                allowed_variable + r')',
                bygroups(Keyword, Whitespace, Keyword, Text, Keyword.Type)),
            (r'(mutable(?=[ \t]))?([ \t]+)?(struct\b)([\s()]+)(' +
                allowed_variable + r')',
                bygroups(Keyword, Whitespace, Keyword, Text, Keyword.Type)),

            # macros
            (r'@' + allowed_variable, Name.Decorator),
            (words([*OPERATORS_LIST, '..', '.', *DOTTED_OPERATORS_LIST],
                prefix='@', suffix=operator_suffixes), Name.Decorator),

            # keywords
            (words(KEYWORD_LIST, suffix=r'\b'), Keyword),
            # builtin types
            (words(BUILTIN_LIST, suffix=r'\b'), Keyword.Type),
            # builtin literals
            (words(LITERAL_LIST, suffix=r'\b'), Name.Builtin),

            # names
            (allowed_variable, Name),

            # numbers
            (r'(\d+((_\d+)+)?\.(?!\.)(\d+((_\d+)+)?)?|\.\d+((_\d+)+)?)([eEf][+-]?[0-9]+)?', Number.Float),
            (r'\d+((_\d+)+)?[eEf][+-]?[0-9]+', Number.Float),
            (r'0x[a-fA-F0-9]+((_[a-fA-F0-9]+)+)?(\.([a-fA-F0-9]+((_[a-fA-F0-9]+)+)?)?)?p[+-]?\d+', Number.Float),
            (r'0b[01]+((_[01]+)+)?', Number.Bin),
            (r'0o[0-7]+((_[0-7]+)+)?', Number.Oct),
            (r'0x[a-fA-F0-9]+((_[a-fA-F0-9]+)+)?', Number.Hex),
            (r'\d+((_\d+)+)?', Number.Integer),

            # single dot operator matched last to permit e.g. ".1" as a float
            (words(['.']), Operator),
        ],

        "blockcomment": [
            (r'[^=#]', Comment.Multiline),
            (r'#=', Comment.Multiline, '#push'),
            (r'=#', Comment.Multiline, '#pop'),
            (r'[=#]', Comment.Multiline),
        ],

        'curly': [
            (r'\{', Punctuation, '#push'),
            (r'\}', Punctuation, '#pop'),
            (allowed_variable, Keyword.Type),
            include('root'),
        ],

        'tqrawstring': [
            (r'"""', String, '#pop'),
            (r'([^"]|"[^"][^"])+', String),
        ],
        'rawstring': [
            (r'"', String, '#pop'),
            (r'\\"', String.Escape),
            (r'([^"\\]|\\[^"])+', String),
        ],

        # Interpolation is defined as "$" followed by the shortest full
        # expression, which is something we can't parse.  Include the most
        # common cases here: $word, and $(paren'd expr).
        'interp': [
            (r'\$' + allowed_variable, String.Interpol),
            (r'(\$)(\()', bygroups(String.Interpol, Punctuation), 'in-intp'),
        ],
        'in-intp': [
            (r'\(', Punctuation, '#push'),
            (r'\)', Punctuation, '#pop'),
            include('root'),
        ],

        'string': [
            (r'(")(' + allowed_variable + r'|\d+)?',
             bygroups(String, String.Affix), '#pop'),
            # FIXME: This escape pattern is not perfect.
            (r'\\([\\"\'$nrbtfav]|(x|u|U)[a-fA-F0-9]+|\d+)', String.Escape),
            include('interp'),
            # @printf and @sprintf formats
            (r'%[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?[hlL]?[E-GXc-giorsux%]',
             String.Interpol),
            (r'[^"$%\\]+', String),
            (r'.', String),
        ],
        'tqstring': [
            (r'(""")(' + allowed_variable + r'|\d+)?',
             bygroups(String, String.Affix), '#pop'),
            (r'\\([\\"\'$nrbtfav]|(x|u|U)[a-fA-F0-9]+|\d+)', String.Escape),
            include('interp'),
            (r'[^"$%\\]+', String),
            (r'.', String),
        ],

        'regex': [
            (r'(")([imsxa]*)?', bygroups(String.Regex, String.Affix), '#pop'),
            (r'\\"', String.Regex),
            (r'[^\\"]+', String.Regex),
        ],

        'tqregex': [
            (r'(""")([imsxa]*)?', bygroups(String.Regex, String.Affix), '#pop'),
            (r'[^"]+', String.Regex),
        ],

        'command': [
            (r'(`)(' + allowed_variable + r'|\d+)?',
             bygroups(String.Backtick, String.Affix), '#pop'),
            (r'\\[`$]', String.Escape),
            include('interp'),
            (r'[^\\`$]+', String.Backtick),
            (r'.', String.Backtick),
        ],
        'tqcommand': [
            (r'(```)(' + allowed_variable + r'|\d+)?',
             bygroups(String.Backtick, String.Affix), '#pop'),
            (r'\\\$', String.Escape),
            include('interp'),
            (r'[^\\`$]+', String.Backtick),
            (r'.', String.Backtick),
        ],
    }

    def analyse_text(text):
        return shebang_matches(text, r'julia')


class JuliaConsoleLexer(Lexer):
    """
    For Julia console sessions. Modeled after MatlabSessionLexer.
    """
    name = 'Julia console'
    aliases = ['jlcon', 'julia-repl']
    url = 'https://julialang.org/'
    version_added = '1.6'
    _example = "jlcon/console"

    def get_tokens_unprocessed(self, text):
        jllexer = JuliaLexer(**self.options)
        start = 0
        curcode = ''
        insertions = []
        output = False
        error = False

        for line in text.splitlines(keepends=True):
            if line.startswith('julia>'):
                insertions.append((len(curcode), [(0, Generic.Prompt, line[:6])]))
                curcode += line[6:]
                output = False
                error = False
            elif line.startswith('help?>') or line.startswith('shell>'):
                yield start, Generic.Prompt, line[:6]
                yield start + 6, Text, line[6:]
                output = False
                error = False
            elif line.startswith('      ') and not output:
                insertions.append((len(curcode), [(0, Whitespace, line[:6])]))
                curcode += line[6:]
            else:
                if curcode:
                    yield from do_insertions(
                        insertions, jllexer.get_tokens_unprocessed(curcode))
                    curcode = ''
                    insertions = []
                if line.startswith('ERROR: ') or error:
                    yield start, Generic.Error, line
                    error = True
                else:
                    yield start, Generic.Output, line
                output = True
            start += len(line)

        if curcode:
            yield from do_insertions(
                insertions, jllexer.get_tokens_unprocessed(curcode))

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\archive_util.py ===
"""distutils.archive_util

Utility functions for creating archive files (tarballs, zip files,
that sort of thing)."""

from __future__ import annotations

import os
from typing import Literal, overload

try:
    import zipfile
except ImportError:
    zipfile = None


from ._log import log
from .dir_util import mkpath
from .errors import DistutilsExecError
from .spawn import spawn

try:
    from pwd import getpwnam
except ImportError:
    getpwnam = None

try:
    from grp import getgrnam
except ImportError:
    getgrnam = None


def _get_gid(name):
    """Returns a gid, given a group name."""
    if getgrnam is None or name is None:
        return None
    try:
        result = getgrnam(name)
    except KeyError:
        result = None
    if result is not None:
        return result[2]
    return None


def _get_uid(name):
    """Returns an uid, given a user name."""
    if getpwnam is None or name is None:
        return None
    try:
        result = getpwnam(name)
    except KeyError:
        result = None
    if result is not None:
        return result[2]
    return None


def make_tarball(
    base_name: str,
    base_dir: str | os.PathLike[str],
    compress: Literal["gzip", "bzip2", "xz"] | None = "gzip",
    verbose: bool = False,
    dry_run: bool = False,
    owner: str | None = None,
    group: str | None = None,
) -> str:
    """Create a (possibly compressed) tar file from all the files under
    'base_dir'.

    'compress' must be "gzip" (the default), "bzip2", "xz", or None.

    'owner' and 'group' can be used to define an owner and a group for the
    archive that is being built. If not provided, the current owner and group
    will be used.

    The output tar file will be named 'base_dir' +  ".tar", possibly plus
    the appropriate compression extension (".gz", ".bz2", ".xz" or ".Z").

    Returns the output filename.
    """
    tar_compression = {
        'gzip': 'gz',
        'bzip2': 'bz2',
        'xz': 'xz',
        None: '',
    }
    compress_ext = {'gzip': '.gz', 'bzip2': '.bz2', 'xz': '.xz'}

    # flags for compression program, each element of list will be an argument
    if compress is not None and compress not in compress_ext.keys():
        raise ValueError(
            "bad value for 'compress': must be None, 'gzip', 'bzip2', 'xz'"
        )

    archive_name = base_name + '.tar'
    archive_name += compress_ext.get(compress, '')

    mkpath(os.path.dirname(archive_name), dry_run=dry_run)

    # creating the tarball
    import tarfile  # late import so Python build itself doesn't break

    log.info('Creating tar archive')

    uid = _get_uid(owner)
    gid = _get_gid(group)

    def _set_uid_gid(tarinfo):
        if gid is not None:
            tarinfo.gid = gid
            tarinfo.gname = group
        if uid is not None:
            tarinfo.uid = uid
            tarinfo.uname = owner
        return tarinfo

    if not dry_run:
        tar = tarfile.open(archive_name, f'w|{tar_compression[compress]}')
        try:
            tar.add(base_dir, filter=_set_uid_gid)
        finally:
            tar.close()

    return archive_name


def make_zipfile(  # noqa: C901
    base_name: str,
    base_dir: str | os.PathLike[str],
    verbose: bool = False,
    dry_run: bool = False,
) -> str:
    """Create a zip file from all the files under 'base_dir'.

    The output zip file will be named 'base_name' + ".zip".  Uses either the
    "zipfile" Python module (if available) or the InfoZIP "zip" utility
    (if installed and found on the default search path).  If neither tool is
    available, raises DistutilsExecError.  Returns the name of the output zip
    file.
    """
    zip_filename = base_name + ".zip"
    mkpath(os.path.dirname(zip_filename), dry_run=dry_run)

    # If zipfile module is not available, try spawning an external
    # 'zip' command.
    if zipfile is None:
        if verbose:
            zipoptions = "-r"
        else:
            zipoptions = "-rq"

        try:
            spawn(["zip", zipoptions, zip_filename, base_dir], dry_run=dry_run)
        except DistutilsExecError:
            # XXX really should distinguish between "couldn't find
            # external 'zip' command" and "zip failed".
            raise DistutilsExecError(
                f"unable to create zip file '{zip_filename}': "
                "could neither import the 'zipfile' module nor "
                "find a standalone zip utility"
            )

    else:
        log.info("creating '%s' and adding '%s' to it", zip_filename, base_dir)

        if not dry_run:
            try:
                zip = zipfile.ZipFile(
                    zip_filename, "w", compression=zipfile.ZIP_DEFLATED
                )
            except RuntimeError:
                zip = zipfile.ZipFile(zip_filename, "w", compression=zipfile.ZIP_STORED)

            with zip:
                if base_dir != os.curdir:
                    path = os.path.normpath(os.path.join(base_dir, ''))
                    zip.write(path, path)
                    log.info("adding '%s'", path)
                for dirpath, dirnames, filenames in os.walk(base_dir):
                    for name in dirnames:
                        path = os.path.normpath(os.path.join(dirpath, name, ''))
                        zip.write(path, path)
                        log.info("adding '%s'", path)
                    for name in filenames:
                        path = os.path.normpath(os.path.join(dirpath, name))
                        if os.path.isfile(path):
                            zip.write(path, path)
                            log.info("adding '%s'", path)

    return zip_filename


ARCHIVE_FORMATS = {
    'gztar': (make_tarball, [('compress', 'gzip')], "gzip'ed tar-file"),
    'bztar': (make_tarball, [('compress', 'bzip2')], "bzip2'ed tar-file"),
    'xztar': (make_tarball, [('compress', 'xz')], "xz'ed tar-file"),
    'ztar': (make_tarball, [('compress', 'compress')], "compressed tar file"),
    'tar': (make_tarball, [('compress', None)], "uncompressed tar file"),
    'zip': (make_zipfile, [], "ZIP file"),
}


def check_archive_formats(formats):
    """Returns the first format from the 'format' list that is unknown.

    If all formats are known, returns None
    """
    for format in formats:
        if format not in ARCHIVE_FORMATS:
            return format
    return None


@overload
def make_archive(
    base_name: str,
    format: str,
    root_dir: str | os.PathLike[str] | bytes | os.PathLike[bytes] | None = None,
    base_dir: str | None = None,
    verbose: bool = False,
    dry_run: bool = False,
    owner: str | None = None,
    group: str | None = None,
) -> str: ...
@overload
def make_archive(
    base_name: str | os.PathLike[str],
    format: str,
    root_dir: str | os.PathLike[str] | bytes | os.PathLike[bytes],
    base_dir: str | None = None,
    verbose: bool = False,
    dry_run: bool = False,
    owner: str | None = None,
    group: str | None = None,
) -> str: ...
def make_archive(
    base_name: str | os.PathLike[str],
    format: str,
    root_dir: str | os.PathLike[str] | bytes | os.PathLike[bytes] | None = None,
    base_dir: str | None = None,
    verbose: bool = False,
    dry_run: bool = False,
    owner: str | None = None,
    group: str | None = None,
) -> str:
    """Create an archive file (eg. zip or tar).

    'base_name' is the name of the file to create, minus any format-specific
    extension; 'format' is the archive format: one of "zip", "tar", "gztar",
    "bztar", "xztar", or "ztar".

    'root_dir' is a directory that will be the root directory of the
    archive; ie. we typically chdir into 'root_dir' before creating the
    archive.  'base_dir' is the directory where we start archiving from;
    ie. 'base_dir' will be the common prefix of all files and
    directories in the archive.  'root_dir' and 'base_dir' both default
    to the current directory.  Returns the name of the archive file.

    'owner' and 'group' are used when creating a tar archive. By default,
    uses the current owner and group.
    """
    save_cwd = os.getcwd()
    if root_dir is not None:
        log.debug("changing into '%s'", root_dir)
        base_name = os.path.abspath(base_name)
        if not dry_run:
            os.chdir(root_dir)

    if base_dir is None:
        base_dir = os.curdir

    kwargs = {'dry_run': dry_run}

    try:
        format_info = ARCHIVE_FORMATS[format]
    except KeyError:
        raise ValueError(f"unknown archive format '{format}'")

    func = format_info[0]
    kwargs.update(format_info[1])

    if format != 'zip':
        kwargs['owner'] = owner
        kwargs['group'] = group

    try:
        filename = func(base_name, base_dir, **kwargs)
    finally:
        if root_dir is not None:
            log.debug("changing back to '%s'", save_cwd)
            os.chdir(save_cwd)

    return filename

# === NexusCore/openenv\Lib\site-packages\trio\_core\_io_kqueue.py ===
from __future__ import annotations

import errno
import select
import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, Literal

import attrs
import outcome

from .. import _core
from ._run import _public
from ._wakeup_socketpair import WakeupSocketpair

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from typing_extensions import TypeAlias

    from .._core import Abort, RaiseCancelT, Task, UnboundedQueue
    from .._file_io import _HasFileNo

assert not TYPE_CHECKING or (sys.platform != "linux" and sys.platform != "win32")

EventResult: TypeAlias = "list[select.kevent]"


@attrs.frozen(eq=False)
class _KqueueStatistics:
    tasks_waiting: int
    monitors: int
    backend: Literal["kqueue"] = attrs.field(init=False, default="kqueue")


@attrs.define(eq=False)
class KqueueIOManager:
    _kqueue: select.kqueue = attrs.Factory(select.kqueue)
    # {(ident, filter): Task or UnboundedQueue}
    _registered: dict[tuple[int, int], Task | UnboundedQueue[select.kevent]] = (
        attrs.Factory(dict)
    )
    _force_wakeup: WakeupSocketpair = attrs.Factory(WakeupSocketpair)
    _force_wakeup_fd: int | None = None

    def __attrs_post_init__(self) -> None:
        force_wakeup_event = select.kevent(
            self._force_wakeup.wakeup_sock,
            select.KQ_FILTER_READ,
            select.KQ_EV_ADD,
        )
        self._kqueue.control([force_wakeup_event], 0)
        self._force_wakeup_fd = self._force_wakeup.wakeup_sock.fileno()

    def statistics(self) -> _KqueueStatistics:
        tasks_waiting = 0
        monitors = 0
        for receiver in self._registered.values():
            if type(receiver) is _core.Task:
                tasks_waiting += 1
            else:
                monitors += 1
        return _KqueueStatistics(tasks_waiting=tasks_waiting, monitors=monitors)

    def close(self) -> None:
        self._kqueue.close()
        self._force_wakeup.close()

    def force_wakeup(self) -> None:
        self._force_wakeup.wakeup_thread_and_signal_safe()

    def get_events(self, timeout: float) -> EventResult:
        # max_events must be > 0 or kqueue gets cranky
        # and we generally want this to be strictly larger than the actual
        # number of events we get, so that we can tell that we've gotten
        # all the events in just 1 call.
        max_events = len(self._registered) + 1
        events = []
        while True:
            batch = self._kqueue.control([], max_events, timeout)
            events += batch
            if len(batch) < max_events:
                break
            else:  # TODO: test this line
                timeout = 0
                # and loop back to the start
        return events

    def process_events(self, events: EventResult) -> None:
        for event in events:
            key = (event.ident, event.filter)
            if event.ident == self._force_wakeup_fd:
                self._force_wakeup.drain()
                continue
            receiver = self._registered[key]
            if event.flags & select.KQ_EV_ONESHOT:  # TODO: test this branch
                del self._registered[key]
            if isinstance(receiver, _core.Task):
                _core.reschedule(receiver, outcome.Value(event))
            else:
                receiver.put_nowait(event)  # TODO: test this line

    # kevent registration is complicated -- e.g. aio submission can
    # implicitly perform a EV_ADD, and EVFILT_PROC with NOTE_TRACK will
    # automatically register filters for child processes. So our lowlevel
    # API is *very* low-level: we expose the kqueue itself for adding
    # events or sticking into AIO submission structs, and split waiting
    # off into separate methods. It's your responsibility to make sure
    # that handle_io never receives an event without a corresponding
    # registration! This may be challenging if you want to be careful
    # about e.g. KeyboardInterrupt. Possibly this API could be improved to
    # be more ergonomic...

    @_public
    def current_kqueue(self) -> select.kqueue:
        """TODO: these are implemented, but are currently more of a sketch than
        anything real. See `#26
        <https://github.com/python-trio/trio/issues/26>`__.
        """
        return self._kqueue

    @contextmanager
    @_public
    def monitor_kevent(
        self,
        ident: int,
        filter: int,
    ) -> Iterator[_core.UnboundedQueue[select.kevent]]:
        """TODO: these are implemented, but are currently more of a sketch than
        anything real. See `#26
        <https://github.com/python-trio/trio/issues/26>`__.
        """
        key = (ident, filter)
        if key in self._registered:
            raise _core.BusyResourceError(
                "attempt to register multiple listeners for same ident/filter pair",
            )
        q = _core.UnboundedQueue[select.kevent]()
        self._registered[key] = q
        try:
            yield q
        finally:
            del self._registered[key]

    @_public
    async def wait_kevent(
        self,
        ident: int,
        filter: int,
        abort_func: Callable[[RaiseCancelT], Abort],
    ) -> Abort:
        """TODO: these are implemented, but are currently more of a sketch than
        anything real. See `#26
        <https://github.com/python-trio/trio/issues/26>`__.
        """
        key = (ident, filter)
        if key in self._registered:
            raise _core.BusyResourceError(
                "attempt to register multiple listeners for same ident/filter pair",
            )
        self._registered[key] = _core.current_task()

        def abort(raise_cancel: RaiseCancelT) -> Abort:
            r = abort_func(raise_cancel)
            if r is _core.Abort.SUCCEEDED:  # TODO: test this branch
                del self._registered[key]
            return r

        # wait_task_rescheduled does not have its return type typed
        return await _core.wait_task_rescheduled(abort)  # type: ignore[no-any-return]

    async def _wait_common(
        self,
        fd: int | _HasFileNo,
        filter: int,
    ) -> None:
        if not isinstance(fd, int):
            fd = fd.fileno()
        flags = select.KQ_EV_ADD | select.KQ_EV_ONESHOT
        event = select.kevent(fd, filter, flags)
        self._kqueue.control([event], 0)

        def abort(_: RaiseCancelT) -> Abort:
            event = select.kevent(fd, filter, select.KQ_EV_DELETE)
            try:
                self._kqueue.control([event], 0)
            except OSError as exc:
                # kqueue tracks individual fds (*not* the underlying file
                # object, see _io_epoll.py for a long discussion of why this
                # distinction matters), and automatically deregisters an event
                # if the fd is closed. So if kqueue.control says that it
                # doesn't know about this event, then probably it's because
                # the fd was closed behind our backs. (Too bad we can't ask it
                # to wake us up when this happens, versus discovering it after
                # the fact... oh well, you can't have everything.)
                #
                # FreeBSD reports this using EBADF. macOS uses ENOENT.
                if exc.errno in (errno.EBADF, errno.ENOENT):  # pragma: no branch
                    pass
                else:  # pragma: no cover
                    # As far as we know, this branch can't happen.
                    raise
            return _core.Abort.SUCCEEDED

        await self.wait_kevent(fd, filter, abort)

    @_public
    async def wait_readable(self, fd: int | _HasFileNo) -> None:
        """Block until the kernel reports that the given object is readable.

        On Unix systems, ``fd`` must either be an integer file descriptor,
        or else an object with a ``.fileno()`` method which returns an
        integer file descriptor. Any kind of file descriptor can be passed,
        though the exact semantics will depend on your kernel. For example,
        this probably won't do anything useful for on-disk files.

        On Windows systems, ``fd`` must either be an integer ``SOCKET``
        handle, or else an object with a ``.fileno()`` method which returns
        an integer ``SOCKET`` handle. File descriptors aren't supported,
        and neither are handles that refer to anything besides a
        ``SOCKET``.

        :raises trio.BusyResourceError:
            if another task is already waiting for the given socket to
            become readable.
        :raises trio.ClosedResourceError:
            if another task calls :func:`notify_closing` while this
            function is still working.
        """
        await self._wait_common(fd, select.KQ_FILTER_READ)

    @_public
    async def wait_writable(self, fd: int | _HasFileNo) -> None:
        """Block until the kernel reports that the given object is writable.

        See `wait_readable` for the definition of ``fd``.

        :raises trio.BusyResourceError:
            if another task is already waiting for the given socket to
            become writable.
        :raises trio.ClosedResourceError:
            if another task calls :func:`notify_closing` while this
            function is still working.
        """
        await self._wait_common(fd, select.KQ_FILTER_WRITE)

    @_public
    def notify_closing(self, fd: int | _HasFileNo) -> None:
        """Notify waiters of the given object that it will be closed.

        Call this before closing a file descriptor (on Unix) or socket (on
        Windows). This will cause any `wait_readable` or `wait_writable`
        calls on the given object to immediately wake up and raise
        `~trio.ClosedResourceError`.

        This doesn't actually close the object – you still have to do that
        yourself afterwards. Also, you want to be careful to make sure no
        new tasks start waiting on the object in between when you call this
        and when it's actually closed. So to close something properly, you
        usually want to do these steps in order:

        1. Explicitly mark the object as closed, so that any new attempts
           to use it will abort before they start.
        2. Call `notify_closing` to wake up any already-existing users.
        3. Actually close the object.

        It's also possible to do them in a different order if that's more
        convenient, *but only if* you make sure not to have any checkpoints in
        between the steps. This way they all happen in a single atomic
        step, so other tasks won't be able to tell what order they happened
        in anyway.
        """
        if not isinstance(fd, int):
            fd = fd.fileno()

        for filter_ in [select.KQ_FILTER_READ, select.KQ_FILTER_WRITE]:
            key = (fd, filter_)
            receiver = self._registered.get(key)

            if receiver is None:
                continue

            if type(receiver) is _core.Task:
                event = select.kevent(fd, filter_, select.KQ_EV_DELETE)
                self._kqueue.control([event], 0)
                exc = _core.ClosedResourceError("another task closed this fd")
                _core.reschedule(receiver, outcome.Error(exc))
                del self._registered[key]
            else:
                # XX this is an interesting example of a case where being able
                # to close a queue would be useful...
                raise NotImplementedError(
                    "can't close an fd that monitor_kevent is using",
                )

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\constants.py ===
import os
import re
import typing
from typing import Literal, Optional, Tuple


# Possible values for env variables


ENV_VARS_TRUE_VALUES = {"1", "ON", "YES", "TRUE"}
ENV_VARS_TRUE_AND_AUTO_VALUES = ENV_VARS_TRUE_VALUES.union({"AUTO"})


def _is_true(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.upper() in ENV_VARS_TRUE_VALUES


def _as_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    return int(value)


# Constants for file downloads

PYTORCH_WEIGHTS_NAME = "pytorch_model.bin"
TF2_WEIGHTS_NAME = "tf_model.h5"
TF_WEIGHTS_NAME = "model.ckpt"
FLAX_WEIGHTS_NAME = "flax_model.msgpack"
CONFIG_NAME = "config.json"
REPOCARD_NAME = "README.md"
DEFAULT_ETAG_TIMEOUT = 10
DEFAULT_DOWNLOAD_TIMEOUT = 10
DEFAULT_REQUEST_TIMEOUT = 10
DOWNLOAD_CHUNK_SIZE = 10 * 1024 * 1024
HF_TRANSFER_CONCURRENCY = 100
MAX_HTTP_DOWNLOAD_SIZE = 50 * 1000 * 1000 * 1000  # 50 GB

# Constants for serialization

PYTORCH_WEIGHTS_FILE_PATTERN = "pytorch_model{suffix}.bin"  # Unsafe pickle: use safetensors instead
SAFETENSORS_WEIGHTS_FILE_PATTERN = "model{suffix}.safetensors"
TF2_WEIGHTS_FILE_PATTERN = "tf_model{suffix}.h5"

# Constants for safetensors repos

SAFETENSORS_SINGLE_FILE = "model.safetensors"
SAFETENSORS_INDEX_FILE = "model.safetensors.index.json"
SAFETENSORS_MAX_HEADER_LENGTH = 25_000_000

# Timeout of aquiring file lock and logging the attempt
FILELOCK_LOG_EVERY_SECONDS = 10

# Git-related constants

DEFAULT_REVISION = "main"
REGEX_COMMIT_OID = re.compile(r"[A-Fa-f0-9]{5,40}")

HUGGINGFACE_CO_URL_HOME = "https://huggingface.co/"

_staging_mode = _is_true(os.environ.get("HUGGINGFACE_CO_STAGING"))

_HF_DEFAULT_ENDPOINT = "https://huggingface.co"
_HF_DEFAULT_STAGING_ENDPOINT = "https://hub-ci.huggingface.co"
ENDPOINT = os.getenv("HF_ENDPOINT", _HF_DEFAULT_ENDPOINT).rstrip("/")
HUGGINGFACE_CO_URL_TEMPLATE = ENDPOINT + "/{repo_id}/resolve/{revision}/{filename}"

if _staging_mode:
    ENDPOINT = _HF_DEFAULT_STAGING_ENDPOINT
    HUGGINGFACE_CO_URL_TEMPLATE = _HF_DEFAULT_STAGING_ENDPOINT + "/{repo_id}/resolve/{revision}/{filename}"

HUGGINGFACE_HEADER_X_REPO_COMMIT = "X-Repo-Commit"
HUGGINGFACE_HEADER_X_LINKED_ETAG = "X-Linked-Etag"
HUGGINGFACE_HEADER_X_LINKED_SIZE = "X-Linked-Size"
HUGGINGFACE_HEADER_X_BILL_TO = "X-HF-Bill-To"

INFERENCE_ENDPOINT = os.environ.get("HF_INFERENCE_ENDPOINT", "https://api-inference.huggingface.co")

# See https://huggingface.co/docs/inference-endpoints/index
INFERENCE_ENDPOINTS_ENDPOINT = "https://api.endpoints.huggingface.cloud/v2"
INFERENCE_CATALOG_ENDPOINT = "https://endpoints.huggingface.co/api/catalog"

# See https://api.endpoints.huggingface.cloud/#post-/v2/endpoint/-namespace-
INFERENCE_ENDPOINT_IMAGE_KEYS = [
    "custom",
    "huggingface",
    "huggingfaceNeuron",
    "llamacpp",
    "tei",
    "tgi",
    "tgiNeuron",
]

# Proxy for third-party providers
INFERENCE_PROXY_TEMPLATE = "https://router.huggingface.co/{provider}"

REPO_ID_SEPARATOR = "--"
# ^ this substring is not allowed in repo_ids on hf.co
# and is the canonical one we use for serialization of repo ids elsewhere.


REPO_TYPE_DATASET = "dataset"
REPO_TYPE_SPACE = "space"
REPO_TYPE_MODEL = "model"
REPO_TYPES = [None, REPO_TYPE_MODEL, REPO_TYPE_DATASET, REPO_TYPE_SPACE]
SPACES_SDK_TYPES = ["gradio", "streamlit", "docker", "static"]

REPO_TYPES_URL_PREFIXES = {
    REPO_TYPE_DATASET: "datasets/",
    REPO_TYPE_SPACE: "spaces/",
}
REPO_TYPES_MAPPING = {
    "datasets": REPO_TYPE_DATASET,
    "spaces": REPO_TYPE_SPACE,
    "models": REPO_TYPE_MODEL,
}

DiscussionTypeFilter = Literal["all", "discussion", "pull_request"]
DISCUSSION_TYPES: Tuple[DiscussionTypeFilter, ...] = typing.get_args(DiscussionTypeFilter)
DiscussionStatusFilter = Literal["all", "open", "closed"]
DISCUSSION_STATUS: Tuple[DiscussionTypeFilter, ...] = typing.get_args(DiscussionStatusFilter)

# Webhook subscription types
WEBHOOK_DOMAIN_T = Literal["repo", "discussions"]

# default cache
default_home = os.path.join(os.path.expanduser("~"), ".cache")
HF_HOME = os.path.expandvars(
    os.path.expanduser(
        os.getenv(
            "HF_HOME",
            os.path.join(os.getenv("XDG_CACHE_HOME", default_home), "huggingface"),
        )
    )
)
hf_cache_home = HF_HOME  # for backward compatibility. TODO: remove this in 1.0.0

default_cache_path = os.path.join(HF_HOME, "hub")
default_assets_cache_path = os.path.join(HF_HOME, "assets")

# Legacy env variables
HUGGINGFACE_HUB_CACHE = os.getenv("HUGGINGFACE_HUB_CACHE", default_cache_path)
HUGGINGFACE_ASSETS_CACHE = os.getenv("HUGGINGFACE_ASSETS_CACHE", default_assets_cache_path)

# New env variables
HF_HUB_CACHE = os.path.expandvars(
    os.path.expanduser(
        os.getenv(
            "HF_HUB_CACHE",
            HUGGINGFACE_HUB_CACHE,
        )
    )
)
HF_ASSETS_CACHE = os.path.expandvars(
    os.path.expanduser(
        os.getenv(
            "HF_ASSETS_CACHE",
            HUGGINGFACE_ASSETS_CACHE,
        )
    )
)

HF_HUB_OFFLINE = _is_true(os.environ.get("HF_HUB_OFFLINE") or os.environ.get("TRANSFORMERS_OFFLINE"))

# If set, log level will be set to DEBUG and all requests made to the Hub will be logged
# as curl commands for reproducibility.
HF_DEBUG = _is_true(os.environ.get("HF_DEBUG"))

# Opt-out from telemetry requests
HF_HUB_DISABLE_TELEMETRY = (
    _is_true(os.environ.get("HF_HUB_DISABLE_TELEMETRY"))  # HF-specific env variable
    or _is_true(os.environ.get("DISABLE_TELEMETRY"))
    or _is_true(os.environ.get("DO_NOT_TRACK"))  # https://consoledonottrack.com/
)

HF_TOKEN_PATH = os.path.expandvars(
    os.path.expanduser(
        os.getenv(
            "HF_TOKEN_PATH",
            os.path.join(HF_HOME, "token"),
        )
    )
)
HF_STORED_TOKENS_PATH = os.path.join(os.path.dirname(HF_TOKEN_PATH), "stored_tokens")

if _staging_mode:
    # In staging mode, we use a different cache to ensure we don't mix up production and staging data or tokens
    # In practice in `huggingface_hub` tests, we monkeypatch these values with temporary directories. The following
    # lines are only used in third-party libraries tests (e.g. `transformers`, `diffusers`, etc.).
    _staging_home = os.path.join(os.path.expanduser("~"), ".cache", "huggingface_staging")
    HUGGINGFACE_HUB_CACHE = os.path.join(_staging_home, "hub")
    HF_TOKEN_PATH = os.path.join(_staging_home, "token")

# Here, `True` will disable progress bars globally without possibility of enabling it
# programmatically. `False` will enable them without possibility of disabling them.
# If environment variable is not set (None), then the user is free to enable/disable
# them programmatically.
# TL;DR: env variable has priority over code
__HF_HUB_DISABLE_PROGRESS_BARS = os.environ.get("HF_HUB_DISABLE_PROGRESS_BARS")
HF_HUB_DISABLE_PROGRESS_BARS: Optional[bool] = (
    _is_true(__HF_HUB_DISABLE_PROGRESS_BARS) if __HF_HUB_DISABLE_PROGRESS_BARS is not None else None
)

# Disable warning on machines that do not support symlinks (e.g. Windows non-developer)
HF_HUB_DISABLE_SYMLINKS_WARNING: bool = _is_true(os.environ.get("HF_HUB_DISABLE_SYMLINKS_WARNING"))

# Disable warning when using experimental features
HF_HUB_DISABLE_EXPERIMENTAL_WARNING: bool = _is_true(os.environ.get("HF_HUB_DISABLE_EXPERIMENTAL_WARNING"))

# Disable sending the cached token by default is all HTTP requests to the Hub
HF_HUB_DISABLE_IMPLICIT_TOKEN: bool = _is_true(os.environ.get("HF_HUB_DISABLE_IMPLICIT_TOKEN"))

# Enable fast-download using external dependency "hf_transfer"
# See:
# - https://pypi.org/project/hf-transfer/
# - https://github.com/huggingface/hf_transfer (private)
HF_HUB_ENABLE_HF_TRANSFER: bool = _is_true(os.environ.get("HF_HUB_ENABLE_HF_TRANSFER"))


# UNUSED
# We don't use symlinks in local dir anymore.
HF_HUB_LOCAL_DIR_AUTO_SYMLINK_THRESHOLD: int = (
    _as_int(os.environ.get("HF_HUB_LOCAL_DIR_AUTO_SYMLINK_THRESHOLD")) or 5 * 1024 * 1024
)

# Used to override the etag timeout on a system level
HF_HUB_ETAG_TIMEOUT: int = _as_int(os.environ.get("HF_HUB_ETAG_TIMEOUT")) or DEFAULT_ETAG_TIMEOUT

# Used to override the get request timeout on a system level
HF_HUB_DOWNLOAD_TIMEOUT: int = _as_int(os.environ.get("HF_HUB_DOWNLOAD_TIMEOUT")) or DEFAULT_DOWNLOAD_TIMEOUT

# Allows to add information about the requester in the user-agent (eg. partner name)
HF_HUB_USER_AGENT_ORIGIN: Optional[str] = os.environ.get("HF_HUB_USER_AGENT_ORIGIN")

# List frameworks that are handled by the InferenceAPI service. Useful to scan endpoints and check which models are
# deployed and running. Since 95% of the models are using the top 4 frameworks listed below, we scan only those by
# default. We still keep the full list of supported frameworks in case we want to scan all of them.
MAIN_INFERENCE_API_FRAMEWORKS = [
    "diffusers",
    "sentence-transformers",
    "text-generation-inference",
    "transformers",
]

ALL_INFERENCE_API_FRAMEWORKS = MAIN_INFERENCE_API_FRAMEWORKS + [
    "adapter-transformers",
    "allennlp",
    "asteroid",
    "bertopic",
    "doctr",
    "espnet",
    "fairseq",
    "fastai",
    "fasttext",
    "flair",
    "k2",
    "keras",
    "mindspore",
    "nemo",
    "open_clip",
    "paddlenlp",
    "peft",
    "pyannote-audio",
    "sklearn",
    "spacy",
    "span-marker",
    "speechbrain",
    "stanza",
    "timm",
]

# If OAuth didn't work after 2 redirects, there's likely a third-party cookie issue in the Space iframe view.
# In this case, we redirect the user to the non-iframe view.
OAUTH_MAX_REDIRECTS = 2

# OAuth-related environment variables injected by the Space
OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID")
OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET")
OAUTH_SCOPES = os.environ.get("OAUTH_SCOPES")
OPENID_PROVIDER_URL = os.environ.get("OPENID_PROVIDER_URL")

# Xet constants
HUGGINGFACE_HEADER_X_XET_ENDPOINT = "X-Xet-Cas-Url"
HUGGINGFACE_HEADER_X_XET_ACCESS_TOKEN = "X-Xet-Access-Token"
HUGGINGFACE_HEADER_X_XET_EXPIRATION = "X-Xet-Token-Expiration"
HUGGINGFACE_HEADER_X_XET_HASH = "X-Xet-Hash"
HUGGINGFACE_HEADER_X_XET_REFRESH_ROUTE = "X-Xet-Refresh-Route"
HUGGINGFACE_HEADER_LINK_XET_AUTH_KEY = "xet-auth"

default_xet_cache_path = os.path.join(HF_HOME, "xet")
HF_XET_CACHE = os.getenv("HF_XET_CACHE", default_xet_cache_path)

# === NexusCore/openenv\Lib\site-packages\ipykernel\kernelspec.py ===
"""The IPython kernel spec for Jupyter"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import errno
import json
import os
import platform
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

from jupyter_client.kernelspec import KernelSpecManager
from traitlets import Unicode
from traitlets.config import Application

pjoin = os.path.join

KERNEL_NAME = "python%i" % sys.version_info[0]

# path to kernelspec resources
RESOURCES = pjoin(Path(__file__).parent, "resources")


def make_ipkernel_cmd(
    mod: str = "ipykernel_launcher",
    executable: str | None = None,
    extra_arguments: list[str] | None = None,
    python_arguments: list[str] | None = None,
) -> list[str]:
    """Build Popen command list for launching an IPython kernel.

    Parameters
    ----------
    mod : str, optional (default 'ipykernel')
        A string of an IPython module whose __main__ starts an IPython kernel
    executable : str, optional (default sys.executable)
        The Python executable to use for the kernel process.
    extra_arguments : list, optional
        A list of extra arguments to pass when executing the launch code.

    Returns
    -------
    A Popen command list
    """
    if executable is None:
        executable = sys.executable
    extra_arguments = extra_arguments or []
    python_arguments = python_arguments or []
    return [executable, *python_arguments, "-m", mod, "-f", "{connection_file}", *extra_arguments]


def get_kernel_dict(
    extra_arguments: list[str] | None = None, python_arguments: list[str] | None = None
) -> dict[str, Any]:
    """Construct dict for kernel.json"""
    return {
        "argv": make_ipkernel_cmd(
            extra_arguments=extra_arguments, python_arguments=python_arguments
        ),
        "display_name": "Python %i (ipykernel)" % sys.version_info[0],
        "language": "python",
        "metadata": {"debugger": True},
    }


def write_kernel_spec(
    path: Path | str | None = None,
    overrides: dict[str, Any] | None = None,
    extra_arguments: list[str] | None = None,
    python_arguments: list[str] | None = None,
) -> str:
    """Write a kernel spec directory to `path`

    If `path` is not specified, a temporary directory is created.
    If `overrides` is given, the kernelspec JSON is updated before writing.

    The path to the kernelspec is always returned.
    """
    if path is None:
        path = Path(tempfile.mkdtemp(suffix="_kernels")) / KERNEL_NAME

    # stage resources
    shutil.copytree(RESOURCES, path)

    # ensure path is writable
    mask = Path(path).stat().st_mode
    if not mask & stat.S_IWUSR:
        Path(path).chmod(mask | stat.S_IWUSR)

    # write kernel.json
    kernel_dict = get_kernel_dict(extra_arguments, python_arguments)

    if overrides:
        kernel_dict.update(overrides)
    with open(pjoin(path, "kernel.json"), "w") as f:
        json.dump(kernel_dict, f, indent=1)

    return str(path)


def install(
    kernel_spec_manager: KernelSpecManager | None = None,
    user: bool = False,
    kernel_name: str = KERNEL_NAME,
    display_name: str | None = None,
    prefix: str | None = None,
    profile: str | None = None,
    env: dict[str, str] | None = None,
    frozen_modules: bool = False,
) -> str:
    """Install the IPython kernelspec for Jupyter

    Parameters
    ----------
    kernel_spec_manager : KernelSpecManager [optional]
        A KernelSpecManager to use for installation.
        If none provided, a default instance will be created.
    user : bool [default: False]
        Whether to do a user-only install, or system-wide.
    kernel_name : str, optional
        Specify a name for the kernelspec.
        This is needed for having multiple IPython kernels for different environments.
    display_name : str, optional
        Specify the display name for the kernelspec
    profile : str, optional
        Specify a custom profile to be loaded by the kernel.
    prefix : str, optional
        Specify an install prefix for the kernelspec.
        This is needed to install into a non-default location, such as a conda/virtual-env.
    env : dict, optional
        A dictionary of extra environment variables for the kernel.
        These will be added to the current environment variables before the
        kernel is started
    frozen_modules : bool, optional
        Whether to use frozen modules for potentially faster kernel startup.
        Using frozen modules prevents debugging inside of some built-in
        Python modules, such as io, abc, posixpath, ntpath, or stat.
        The frozen modules are used in CPython for faster interpreter startup.
        Ignored for cPython <3.11 and for other Python implementations.

    Returns
    -------
    The path where the kernelspec was installed.
    """
    if kernel_spec_manager is None:
        kernel_spec_manager = KernelSpecManager()

    if env is None:
        env = {}

    if (kernel_name != KERNEL_NAME) and (display_name is None):
        # kernel_name is specified and display_name is not
        # default display_name to kernel_name
        display_name = kernel_name
    overrides: dict[str, Any] = {}
    if display_name:
        overrides["display_name"] = display_name
    if profile:
        extra_arguments = ["--profile", profile]
        if not display_name:
            # add the profile to the default display name
            overrides["display_name"] = "Python %i [profile=%s]" % (sys.version_info[0], profile)
    else:
        extra_arguments = None

    python_arguments = None

    # addresses the debugger warning from debugpy about frozen modules
    if sys.version_info >= (3, 11) and platform.python_implementation() == "CPython":
        if not frozen_modules:
            # disable frozen modules
            python_arguments = ["-Xfrozen_modules=off"]
        elif "PYDEVD_DISABLE_FILE_VALIDATION" not in env:
            # user opted-in to have frozen modules, and we warned them about
            # consequences for the - disable the debugger warning
            env["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"

    if env:
        overrides["env"] = env
    path = write_kernel_spec(
        overrides=overrides, extra_arguments=extra_arguments, python_arguments=python_arguments
    )
    dest = kernel_spec_manager.install_kernel_spec(
        path, kernel_name=kernel_name, user=user, prefix=prefix
    )
    # cleanup afterward
    shutil.rmtree(path)
    return dest


# Entrypoint


class InstallIPythonKernelSpecApp(Application):
    """Dummy app wrapping argparse"""

    name = Unicode("ipython-kernel-install")

    def initialize(self, argv: list[str] | None = None) -> None:
        """Initialize the app."""
        if argv is None:
            argv = sys.argv[1:]
        self.argv = argv

    def start(self) -> None:
        """Start the app."""
        import argparse

        parser = argparse.ArgumentParser(
            prog=self.name, description="Install the IPython kernel spec."
        )
        parser.add_argument(
            "--user",
            action="store_true",
            help="Install for the current user instead of system-wide",
        )
        parser.add_argument(
            "--name",
            type=str,
            default=KERNEL_NAME,
            help="Specify a name for the kernelspec."
            " This is needed to have multiple IPython kernels at the same time.",
        )
        parser.add_argument(
            "--display-name",
            type=str,
            help="Specify the display name for the kernelspec."
            " This is helpful when you have multiple IPython kernels.",
        )
        parser.add_argument(
            "--profile",
            type=str,
            help="Specify an IPython profile to load. "
            "This can be used to create custom versions of the kernel.",
        )
        parser.add_argument(
            "--prefix",
            type=str,
            help="Specify an install prefix for the kernelspec."
            " This is needed to install into a non-default location, such as a conda/virtual-env.",
        )
        parser.add_argument(
            "--sys-prefix",
            action="store_const",
            const=sys.prefix,
            dest="prefix",
            help="Install to Python's sys.prefix."
            " Shorthand for --prefix='%s'. For use in conda/virtual-envs." % sys.prefix,
        )
        parser.add_argument(
            "--env",
            action="append",
            nargs=2,
            metavar=("ENV", "VALUE"),
            help="Set environment variables for the kernel.",
        )
        parser.add_argument(
            "--frozen_modules",
            action="store_true",
            help="Enable frozen modules for potentially faster startup."
            " This has a downside of preventing the debugger from navigating to certain built-in modules.",
        )
        opts = parser.parse_args(self.argv)
        if opts.env:
            opts.env = dict(opts.env)
        try:
            dest = install(
                user=opts.user,
                kernel_name=opts.name,
                profile=opts.profile,
                prefix=opts.prefix,
                display_name=opts.display_name,
                env=opts.env,
            )
        except OSError as e:
            if e.errno == errno.EACCES:
                print(e, file=sys.stderr)
                if opts.user:
                    print("Perhaps you want `sudo` or `--user`?", file=sys.stderr)
                self.exit(1)
            raise
        print(f"Installed kernelspec {opts.name} in {dest}")


if __name__ == "__main__":
    InstallIPythonKernelSpecApp.launch_instance()

# === NexusCore/openenv\Lib\site-packages\debugpy\adapter\sessions.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

import itertools
import os
import signal
import threading
import time

from debugpy import common
from debugpy.common import log, util
from debugpy.adapter import components, launchers, servers


_lock = threading.RLock()
_sessions = set()
_sessions_changed = threading.Event()


class Session(util.Observable):
    """A debug session involving a client, an adapter, a launcher, and a debug server.

    The client and the adapter are always present, and at least one of launcher and debug
    server is present, depending on the scenario.
    """

    _counter = itertools.count(1)

    def __init__(self):
        from debugpy.adapter import clients

        super().__init__()

        self.lock = threading.RLock()
        self.id = next(self._counter)
        self._changed_condition = threading.Condition(self.lock)

        self.client = components.missing(self, clients.Client)
        """The client component. Always present."""

        self.launcher = components.missing(self, launchers.Launcher)
        """The launcher componet. Always present in "launch" sessions, and never
        present in "attach" sessions.
        """

        self.server = components.missing(self, servers.Server)
        """The debug server component. Always present, unless this is a "launch"
        session with "noDebug".
        """

        self.no_debug = None
        """Whether this is a "noDebug" session."""

        self.pid = None
        """Process ID of the debuggee process."""

        self.debug_options = {}
        """Debug options as specified by "launch" or "attach" request."""

        self.is_finalizing = False
        """Whether finalize() has been invoked."""

        self.observers += [lambda *_: self.notify_changed()]

    def __str__(self):
        return f"Session[{self.id}]"

    def __enter__(self):
        """Lock the session for exclusive access."""
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Unlock the session."""
        self.lock.release()

    def register(self):
        with _lock:
            _sessions.add(self)
            _sessions_changed.set()

    def notify_changed(self):
        with self:
            self._changed_condition.notify_all()

        # A session is considered ended once all components disconnect, and there
        # are no further incoming messages from anything to handle.
        components = self.client, self.launcher, self.server
        if all(not com or not com.is_connected for com in components):
            with _lock:
                if self in _sessions:
                    log.info("{0} has ended.", self)
                    _sessions.remove(self)
                    _sessions_changed.set()

    def wait_for(self, predicate, timeout=None):
        """Waits until predicate() becomes true.

        The predicate is invoked with the session locked. If satisfied, the method
        returns immediately. Otherwise, the lock is released (even if it was held
        at entry), and the method blocks waiting for some attribute of either self,
        self.client, self.server, or self.launcher to change. On every change, session
        is re-locked and predicate is re-evaluated, until it is satisfied.

        While the session is unlocked, message handlers for components other than
        the one that is waiting can run, but message handlers for that one are still
        blocked.

        If timeout is not None, the method will unblock and return after that many
        seconds regardless of whether the predicate was satisfied. The method returns
        False if it timed out, and True otherwise.
        """

        def wait_for_timeout():
            time.sleep(timeout)
            wait_for_timeout.timed_out = True
            self.notify_changed()

        wait_for_timeout.timed_out = False
        if timeout is not None:
            thread = threading.Thread(
                target=wait_for_timeout, name="Session.wait_for() timeout"
            )
            thread.daemon = True
            thread.start()

        with self:
            while not predicate():
                if wait_for_timeout.timed_out:
                    return False
                self._changed_condition.wait()
            return True

    def finalize(self, why, terminate_debuggee=None):
        """Finalizes the debug session.

        If the server is present, sends "disconnect" request with "terminateDebuggee"
        set as specified request to it; waits for it to disconnect, allowing any
        remaining messages from it to be handled; and closes the server channel.

        If the launcher is present, sends "terminate" request to it, regardless of the
        value of terminate; waits for it to disconnect, allowing any remaining messages
        from it to be handled; and closes the launcher channel.

        If the client is present, sends "terminated" event to it.

        If terminate_debuggee=None, it is treated as True if the session has a Launcher
        component, and False otherwise.
        """

        if self.is_finalizing:
            return
        self.is_finalizing = True
        log.info("{0}; finalizing {1}.", why, self)

        if terminate_debuggee is None:
            terminate_debuggee = bool(self.launcher)

        try:
            self._finalize(why, terminate_debuggee)
        except Exception:
            # Finalization should never fail, and if it does, the session is in an
            # indeterminate and likely unrecoverable state, so just fail fast.
            log.swallow_exception("Fatal error while finalizing {0}", self)
            os._exit(1)

        log.info("{0} finalized.", self)

    def _finalize(self, why, terminate_debuggee):
        # If the client started a session, and then disconnected before issuing "launch"
        # or "attach", the main thread will be blocked waiting for the first server
        # connection to come in - unblock it, so that we can exit.
        servers.dont_wait_for_first_connection()

        if self.server:
            if self.server.is_connected:
                if terminate_debuggee and self.launcher and self.launcher.is_connected:
                    # If we were specifically asked to terminate the debuggee, and we
                    # can ask the launcher to kill it, do so instead of disconnecting
                    # from the server to prevent debuggee from running any more code.
                    self.launcher.terminate_debuggee()
                else:
                    # Otherwise, let the server handle it the best it can.
                    try:
                        self.server.channel.request(
                            "disconnect", {"terminateDebuggee": terminate_debuggee}
                        )
                    except Exception:
                        pass
            self.server.detach_from_session()

        if self.launcher and self.launcher.is_connected:
            # If there was a server, we just disconnected from it above, which should
            # cause the debuggee process to exit, unless it is being replaced in situ -
            # so let's wait for that first.
            if self.server and not self.server.connection.process_replaced:
                log.info('{0} waiting for "exited" event...', self)
                if not self.wait_for(
                    lambda: self.launcher.exit_code is not None,
                    timeout=common.PROCESS_EXIT_TIMEOUT,
                ):
                    log.warning('{0} timed out waiting for "exited" event.', self)

            # Terminate the debuggee process if it's still alive for any reason -
            # whether it's because there was no server to handle graceful shutdown,
            # or because the server couldn't handle it for some reason - unless the
            # process is being replaced in situ.
            if not (self.server and self.server.connection.process_replaced):
                self.launcher.terminate_debuggee()

            # Wait until the launcher message queue fully drains. There is no timeout
            # here, because the final "terminated" event will only come after reading
            # user input in wait-on-exit scenarios. In addition, if the process was
            # replaced in situ, the launcher might still have more output to capture
            # from its replacement.
            log.info("{0} waiting for {1} to disconnect...", self, self.launcher)
            self.wait_for(lambda: not self.launcher.is_connected)

            try:
                self.launcher.channel.close()
            except Exception:
                log.swallow_exception()

        if self.client:
            if self.client.is_connected:
                # Tell the client that debugging is over, but don't close the channel until it
                # tells us to, via the "disconnect" request.
                body = {}
                if self.client.restart_requested:
                    body["restart"] = True
                try:
                    self.client.channel.send_event("terminated", body)
                except Exception:
                    pass

            if (
                self.client.start_request is not None
                and self.client.start_request.command == "launch"
                and not (self.server and self.server.connection.process_replaced)
            ):
                servers.stop_serving()
                log.info(
                    '"launch" session ended - killing remaining debuggee processes.'
                )

                pids_killed = set()
                if self.launcher and self.launcher.pid is not None:
                    # Already killed above.
                    pids_killed.add(self.launcher.pid)

                while True:
                    conns = [
                        conn
                        for conn in servers.connections()
                        if conn.pid not in pids_killed
                    ]
                    if not len(conns):
                        break
                    for conn in conns:
                        log.info("Killing {0}", conn)
                        try:
                            os.kill(conn.pid, signal.SIGTERM)
                        except Exception:
                            log.swallow_exception("Failed to kill {0}", conn)
                        pids_killed.add(conn.pid)


def get(pid):
    with _lock:
        return next((session for session in _sessions if session.pid == pid), None)


def wait_until_ended():
    """Blocks until all sessions have ended.

    A session ends when all components that it manages disconnect from it.
    """
    while True:
        with _lock:
            if not len(_sessions):
                return
            _sessions_changed.clear()
        _sessions_changed.wait()


def report_sockets():
    if not _sessions:
        return
    session = sorted(_sessions, key=lambda session: session.id)[0]
    client = session.client
    if client is not None:
        client.report_sockets()

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_namespace_utils.py ===
from __future__ import annotations

import sys
from collections.abc import Generator, Iterator, Mapping
from contextlib import contextmanager
from functools import cached_property
from typing import Any, Callable, NamedTuple, TypeVar

from typing_extensions import ParamSpec, TypeAlias, TypeAliasType, TypeVarTuple

GlobalsNamespace: TypeAlias = 'dict[str, Any]'
"""A global namespace.

In most cases, this is a reference to the `__dict__` attribute of a module.
This namespace type is expected as the `globals` argument during annotations evaluation.
"""

MappingNamespace: TypeAlias = Mapping[str, Any]
"""Any kind of namespace.

In most cases, this is a local namespace (e.g. the `__dict__` attribute of a class,
the [`f_locals`][frame.f_locals] attribute of a frame object, when dealing with types
defined inside functions).
This namespace type is expected as the `locals` argument during annotations evaluation.
"""

_TypeVarLike: TypeAlias = 'TypeVar | ParamSpec | TypeVarTuple'


class NamespacesTuple(NamedTuple):
    """A tuple of globals and locals to be used during annotations evaluation.

    This datastructure is defined as a named tuple so that it can easily be unpacked:

    ```python {lint="skip" test="skip"}
    def eval_type(typ: type[Any], ns: NamespacesTuple) -> None:
        return eval(typ, *ns)
    ```
    """

    globals: GlobalsNamespace
    """The namespace to be used as the `globals` argument during annotations evaluation."""

    locals: MappingNamespace
    """The namespace to be used as the `locals` argument during annotations evaluation."""


def get_module_ns_of(obj: Any) -> dict[str, Any]:
    """Get the namespace of the module where the object is defined.

    Caution: this function does not return a copy of the module namespace, so the result
    should not be mutated. The burden of enforcing this is on the caller.
    """
    module_name = getattr(obj, '__module__', None)
    if module_name:
        try:
            return sys.modules[module_name].__dict__
        except KeyError:
            # happens occasionally, see https://github.com/pydantic/pydantic/issues/2363
            return {}
    return {}


# Note that this class is almost identical to `collections.ChainMap`, but need to enforce
# immutable mappings here:
class LazyLocalNamespace(Mapping[str, Any]):
    """A lazily evaluated mapping, to be used as the `locals` argument during annotations evaluation.

    While the [`eval`][eval] function expects a mapping as the `locals` argument, it only
    performs `__getitem__` calls. The [`Mapping`][collections.abc.Mapping] abstract base class
    is fully implemented only for type checking purposes.

    Args:
        *namespaces: The namespaces to consider, in ascending order of priority.

    Example:
        ```python {lint="skip" test="skip"}
        ns = LazyLocalNamespace({'a': 1, 'b': 2}, {'a': 3})
        ns['a']
        #> 3
        ns['b']
        #> 2
        ```
    """

    def __init__(self, *namespaces: MappingNamespace) -> None:
        self._namespaces = namespaces

    @cached_property
    def data(self) -> dict[str, Any]:
        return {k: v for ns in self._namespaces for k, v in ns.items()}

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __contains__(self, key: object) -> bool:
        return key in self.data

    def __iter__(self) -> Iterator[str]:
        return iter(self.data)


def ns_for_function(obj: Callable[..., Any], parent_namespace: MappingNamespace | None = None) -> NamespacesTuple:
    """Return the global and local namespaces to be used when evaluating annotations for the provided function.

    The global namespace will be the `__dict__` attribute of the module the function was defined in.
    The local namespace will contain the `__type_params__` introduced by PEP 695.

    Args:
        obj: The object to use when building namespaces.
        parent_namespace: Optional namespace to be added with the lowest priority in the local namespace.
            If the passed function is a method, the `parent_namespace` will be the namespace of the class
            the method is defined in. Thus, we also fetch type `__type_params__` from there (i.e. the
            class-scoped type variables).
    """
    locals_list: list[MappingNamespace] = []
    if parent_namespace is not None:
        locals_list.append(parent_namespace)

    # Get the `__type_params__` attribute introduced by PEP 695.
    # Note that the `typing._eval_type` function expects type params to be
    # passed as a separate argument. However, internally, `_eval_type` calls
    # `ForwardRef._evaluate` which will merge type params with the localns,
    # essentially mimicking what we do here.
    type_params: tuple[_TypeVarLike, ...] = getattr(obj, '__type_params__', ())
    if parent_namespace is not None:
        # We also fetch type params from the parent namespace. If present, it probably
        # means the function was defined in a class. This is to support the following:
        # https://github.com/python/cpython/issues/124089.
        type_params += parent_namespace.get('__type_params__', ())

    locals_list.append({t.__name__: t for t in type_params})

    # What about short-cirtuiting to `obj.__globals__`?
    globalns = get_module_ns_of(obj)

    return NamespacesTuple(globalns, LazyLocalNamespace(*locals_list))


class NsResolver:
    """A class responsible for the namespaces resolving logic for annotations evaluation.

    This class handles the namespace logic when evaluating annotations mainly for class objects.

    It holds a stack of classes that are being inspected during the core schema building,
    and the `types_namespace` property exposes the globals and locals to be used for
    type annotation evaluation. Additionally -- if no class is present in the stack -- a
    fallback globals and locals can be provided using the `namespaces_tuple` argument
    (this is useful when generating a schema for a simple annotation, e.g. when using
    `TypeAdapter`).

    The namespace creation logic is unfortunately flawed in some cases, for backwards
    compatibility reasons and to better support valid edge cases. See the description
    for the `parent_namespace` argument and the example for more details.

    Args:
        namespaces_tuple: The default globals and locals to use if no class is present
            on the stack. This can be useful when using the `GenerateSchema` class
            with `TypeAdapter`, where the "type" being analyzed is a simple annotation.
        parent_namespace: An optional parent namespace that will be added to the locals
            with the lowest priority. For a given class defined in a function, the locals
            of this function are usually used as the parent namespace:

            ```python {lint="skip" test="skip"}
            from pydantic import BaseModel

            def func() -> None:
                SomeType = int

                class Model(BaseModel):
                    f: 'SomeType'

                # when collecting fields, an namespace resolver instance will be created
                # this way:
                # ns_resolver = NsResolver(parent_namespace={'SomeType': SomeType})
            ```

            For backwards compatibility reasons and to support valid edge cases, this parent
            namespace will be used for *every* type being pushed to the stack. In the future,
            we might want to be smarter by only doing so when the type being pushed is defined
            in the same module as the parent namespace.

    Example:
        ```python {lint="skip" test="skip"}
        ns_resolver = NsResolver(
            parent_namespace={'fallback': 1},
        )

        class Sub:
            m: 'Model'

        class Model:
            some_local = 1
            sub: Sub

        ns_resolver = NsResolver()

        # This is roughly what happens when we build a core schema for `Model`:
        with ns_resolver.push(Model):
            ns_resolver.types_namespace
            #> NamespacesTuple({'Sub': Sub}, {'Model': Model, 'some_local': 1})
            # First thing to notice here, the model being pushed is added to the locals.
            # Because `NsResolver` is being used during the model definition, it is not
            # yet added to the globals. This is useful when resolving self-referencing annotations.

            with ns_resolver.push(Sub):
                ns_resolver.types_namespace
                #> NamespacesTuple({'Sub': Sub}, {'Sub': Sub, 'Model': Model})
                # Second thing to notice: `Sub` is present in both the globals and locals.
                # This is not an issue, just that as described above, the model being pushed
                # is added to the locals, but it happens to be present in the globals as well
                # because it is already defined.
                # Third thing to notice: `Model` is also added in locals. This is a backwards
                # compatibility workaround that allows for `Sub` to be able to resolve `'Model'`
                # correctly (as otherwise models would have to be rebuilt even though this
                # doesn't look necessary).
        ```
    """

    def __init__(
        self,
        namespaces_tuple: NamespacesTuple | None = None,
        parent_namespace: MappingNamespace | None = None,
    ) -> None:
        self._base_ns_tuple = namespaces_tuple or NamespacesTuple({}, {})
        self._parent_ns = parent_namespace
        self._types_stack: list[type[Any] | TypeAliasType] = []

    @cached_property
    def types_namespace(self) -> NamespacesTuple:
        """The current global and local namespaces to be used for annotations evaluation."""
        if not self._types_stack:
            # TODO: should we merge the parent namespace here?
            # This is relevant for TypeAdapter, where there are no types on the stack, and we might
            # need access to the parent_ns. Right now, we sidestep this in `type_adapter.py` by passing
            # locals to both parent_ns and the base_ns_tuple, but this is a bit hacky.
            # we might consider something like:
            # if self._parent_ns is not None:
            #     # Hacky workarounds, see class docstring:
            #     # An optional parent namespace that will be added to the locals with the lowest priority
            #     locals_list: list[MappingNamespace] = [self._parent_ns, self._base_ns_tuple.locals]
            #     return NamespacesTuple(self._base_ns_tuple.globals, LazyLocalNamespace(*locals_list))
            return self._base_ns_tuple

        typ = self._types_stack[-1]

        globalns = get_module_ns_of(typ)

        locals_list: list[MappingNamespace] = []
        # Hacky workarounds, see class docstring:
        # An optional parent namespace that will be added to the locals with the lowest priority
        if self._parent_ns is not None:
            locals_list.append(self._parent_ns)
        if len(self._types_stack) > 1:
            first_type = self._types_stack[0]
            locals_list.append({first_type.__name__: first_type})

        # Adding `__type_params__` *before* `vars(typ)`, as the latter takes priority
        # (see https://github.com/python/cpython/pull/120272).
        # TODO `typ.__type_params__` when we drop support for Python 3.11:
        type_params: tuple[_TypeVarLike, ...] = getattr(typ, '__type_params__', ())
        if type_params:
            # Adding `__type_params__` is mostly useful for generic classes defined using
            # PEP 695 syntax *and* using forward annotations (see the example in
            # https://github.com/python/cpython/issues/114053). For TypeAliasType instances,
            # it is way less common, but still required if using a string annotation in the alias
            # value, e.g. `type A[T] = 'T'` (which is not necessary in most cases).
            locals_list.append({t.__name__: t for t in type_params})

        # TypeAliasType instances don't have a `__dict__` attribute, so the check
        # is necessary:
        if hasattr(typ, '__dict__'):
            locals_list.append(vars(typ))

        # The `len(self._types_stack) > 1` check above prevents this from being added twice:
        locals_list.append({typ.__name__: typ})

        return NamespacesTuple(globalns, LazyLocalNamespace(*locals_list))

    @contextmanager
    def push(self, typ: type[Any] | TypeAliasType, /) -> Generator[None]:
        """Push a type to the stack."""
        self._types_stack.append(typ)
        # Reset the cached property:
        self.__dict__.pop('types_namespace', None)
        try:
            yield
        finally:
            self._types_stack.pop()
            self.__dict__.pop('types_namespace', None)

# === NexusCore/openenv\Lib\site-packages\PIL\AvifImagePlugin.py ===
from __future__ import annotations

import os
from io import BytesIO
from typing import IO

from . import ExifTags, Image, ImageFile

try:
    from . import _avif

    SUPPORTED = True
except ImportError:
    SUPPORTED = False

# Decoder options as module globals, until there is a way to pass parameters
# to Image.open (see https://github.com/python-pillow/Pillow/issues/569)
DECODE_CODEC_CHOICE = "auto"
# Decoding is only affected by this for libavif **0.8.4** or greater.
DEFAULT_MAX_THREADS = 0


def get_codec_version(codec_name: str) -> str | None:
    versions = _avif.codec_versions()
    for version in versions.split(", "):
        if version.split(" [")[0] == codec_name:
            return version.split(":")[-1].split(" ")[0]
    return None


def _accept(prefix: bytes) -> bool | str:
    if prefix[4:8] != b"ftyp":
        return False
    major_brand = prefix[8:12]
    if major_brand in (
        # coding brands
        b"avif",
        b"avis",
        # We accept files with AVIF container brands; we can't yet know if
        # the ftyp box has the correct compatible brands, but if it doesn't
        # then the plugin will raise a SyntaxError which Pillow will catch
        # before moving on to the next plugin that accepts the file.
        #
        # Also, because this file might not actually be an AVIF file, we
        # don't raise an error if AVIF support isn't properly compiled.
        b"mif1",
        b"msf1",
    ):
        if not SUPPORTED:
            return (
                "image file could not be identified because AVIF support not installed"
            )
        return True
    return False


def _get_default_max_threads() -> int:
    if DEFAULT_MAX_THREADS:
        return DEFAULT_MAX_THREADS
    if hasattr(os, "sched_getaffinity"):
        return len(os.sched_getaffinity(0))
    else:
        return os.cpu_count() or 1


class AvifImageFile(ImageFile.ImageFile):
    format = "AVIF"
    format_description = "AVIF image"
    __frame = -1

    def _open(self) -> None:
        if not SUPPORTED:
            msg = "image file could not be opened because AVIF support not installed"
            raise SyntaxError(msg)

        if DECODE_CODEC_CHOICE != "auto" and not _avif.decoder_codec_available(
            DECODE_CODEC_CHOICE
        ):
            msg = "Invalid opening codec"
            raise ValueError(msg)
        self._decoder = _avif.AvifDecoder(
            self.fp.read(),
            DECODE_CODEC_CHOICE,
            _get_default_max_threads(),
        )

        # Get info from decoder
        self._size, self.n_frames, self._mode, icc, exif, exif_orientation, xmp = (
            self._decoder.get_info()
        )
        self.is_animated = self.n_frames > 1

        if icc:
            self.info["icc_profile"] = icc
        if xmp:
            self.info["xmp"] = xmp

        if exif_orientation != 1 or exif:
            exif_data = Image.Exif()
            if exif:
                exif_data.load(exif)
                original_orientation = exif_data.get(ExifTags.Base.Orientation, 1)
            else:
                original_orientation = 1
            if exif_orientation != original_orientation:
                exif_data[ExifTags.Base.Orientation] = exif_orientation
                exif = exif_data.tobytes()
        if exif:
            self.info["exif"] = exif
        self.seek(0)

    def seek(self, frame: int) -> None:
        if not self._seek_check(frame):
            return

        # Set tile
        self.__frame = frame
        self.tile = [ImageFile._Tile("raw", (0, 0) + self.size, 0, self.mode)]

    def load(self) -> Image.core.PixelAccess | None:
        if self.tile:
            # We need to load the image data for this frame
            data, timescale, pts_in_timescales, duration_in_timescales = (
                self._decoder.get_frame(self.__frame)
            )
            self.info["timestamp"] = round(1000 * (pts_in_timescales / timescale))
            self.info["duration"] = round(1000 * (duration_in_timescales / timescale))

            if self.fp and self._exclusive_fp:
                self.fp.close()
            self.fp = BytesIO(data)

        return super().load()

    def load_seek(self, pos: int) -> None:
        pass

    def tell(self) -> int:
        return self.__frame


def _save_all(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    _save(im, fp, filename, save_all=True)


def _save(
    im: Image.Image, fp: IO[bytes], filename: str | bytes, save_all: bool = False
) -> None:
    info = im.encoderinfo.copy()
    if save_all:
        append_images = list(info.get("append_images", []))
    else:
        append_images = []

    total = 0
    for ims in [im] + append_images:
        total += getattr(ims, "n_frames", 1)

    quality = info.get("quality", 75)
    if not isinstance(quality, int) or quality < 0 or quality > 100:
        msg = "Invalid quality setting"
        raise ValueError(msg)

    duration = info.get("duration", 0)
    subsampling = info.get("subsampling", "4:2:0")
    speed = info.get("speed", 6)
    max_threads = info.get("max_threads", _get_default_max_threads())
    codec = info.get("codec", "auto")
    if codec != "auto" and not _avif.encoder_codec_available(codec):
        msg = "Invalid saving codec"
        raise ValueError(msg)
    range_ = info.get("range", "full")
    tile_rows_log2 = info.get("tile_rows", 0)
    tile_cols_log2 = info.get("tile_cols", 0)
    alpha_premultiplied = bool(info.get("alpha_premultiplied", False))
    autotiling = bool(info.get("autotiling", tile_rows_log2 == tile_cols_log2 == 0))

    icc_profile = info.get("icc_profile", im.info.get("icc_profile"))
    exif_orientation = 1
    if exif := info.get("exif"):
        if isinstance(exif, Image.Exif):
            exif_data = exif
        else:
            exif_data = Image.Exif()
            exif_data.load(exif)
        if ExifTags.Base.Orientation in exif_data:
            exif_orientation = exif_data.pop(ExifTags.Base.Orientation)
            exif = exif_data.tobytes() if exif_data else b""
        elif isinstance(exif, Image.Exif):
            exif = exif_data.tobytes()

    xmp = info.get("xmp")

    if isinstance(xmp, str):
        xmp = xmp.encode("utf-8")

    advanced = info.get("advanced")
    if advanced is not None:
        if isinstance(advanced, dict):
            advanced = advanced.items()
        try:
            advanced = tuple(advanced)
        except TypeError:
            invalid = True
        else:
            invalid = any(not isinstance(v, tuple) or len(v) != 2 for v in advanced)
        if invalid:
            msg = (
                "advanced codec options must be a dict of key-value string "
                "pairs or a series of key-value two-tuples"
            )
            raise ValueError(msg)

    # Setup the AVIF encoder
    enc = _avif.AvifEncoder(
        im.size,
        subsampling,
        quality,
        speed,
        max_threads,
        codec,
        range_,
        tile_rows_log2,
        tile_cols_log2,
        alpha_premultiplied,
        autotiling,
        icc_profile or b"",
        exif or b"",
        exif_orientation,
        xmp or b"",
        advanced,
    )

    # Add each frame
    frame_idx = 0
    frame_duration = 0
    cur_idx = im.tell()
    is_single_frame = total == 1
    try:
        for ims in [im] + append_images:
            # Get number of frames in this image
            nfr = getattr(ims, "n_frames", 1)

            for idx in range(nfr):
                ims.seek(idx)

                # Make sure image mode is supported
                frame = ims
                rawmode = ims.mode
                if ims.mode not in {"RGB", "RGBA"}:
                    rawmode = "RGBA" if ims.has_transparency_data else "RGB"
                    frame = ims.convert(rawmode)

                # Update frame duration
                if isinstance(duration, (list, tuple)):
                    frame_duration = duration[frame_idx]
                else:
                    frame_duration = duration

                # Append the frame to the animation encoder
                enc.add(
                    frame.tobytes("raw", rawmode),
                    frame_duration,
                    frame.size,
                    rawmode,
                    is_single_frame,
                )

                # Update frame index
                frame_idx += 1

                if not save_all:
                    break

    finally:
        im.seek(cur_idx)

    # Get the final output from the encoder
    data = enc.finish()
    if data is None:
        msg = "cannot write file as AVIF (encoder returned None)"
        raise OSError(msg)

    fp.write(data)


Image.register_open(AvifImageFile.format, AvifImageFile, _accept)
if SUPPORTED:
    Image.register_save(AvifImageFile.format, _save)
    Image.register_save_all(AvifImageFile.format, _save_all)
    Image.register_extensions(AvifImageFile.format, [".avif", ".avifs"])
    Image.register_mime(AvifImageFile.format, "image/avif")

# === NexusCore/openenv\Lib\site-packages\debugpy\common\json.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

"""Improved JSON serialization.
"""

import builtins
import json
import numbers
import operator


JsonDecoder = json.JSONDecoder


class JsonEncoder(json.JSONEncoder):
    """Customizable JSON encoder.

    If the object implements __getstate__, then that method is invoked, and its
    result is serialized instead of the object itself.
    """

    def default(self, value):
        try:
            get_state = value.__getstate__
        except AttributeError:
            pass
        else:
            return get_state()
        return super().default(value)


class JsonObject(object):
    """A wrapped Python object that formats itself as JSON when asked for a string
    representation via str() or format().
    """

    json_encoder_factory = JsonEncoder
    """Used by __format__ when format_spec is not empty."""

    json_encoder = json_encoder_factory(indent=4)
    """The default encoder used by __format__ when format_spec is empty."""

    def __init__(self, value):
        assert not isinstance(value, JsonObject)
        self.value = value

    def __getstate__(self):
        raise NotImplementedError

    def __repr__(self):
        return builtins.repr(self.value)

    def __str__(self):
        return format(self)

    def __format__(self, format_spec):
        """If format_spec is empty, uses self.json_encoder to serialize self.value
        as a string. Otherwise, format_spec is treated as an argument list to be
        passed to self.json_encoder_factory - which defaults to JSONEncoder - and
        then the resulting formatter is used to serialize self.value as a string.

        Example::

            format("{0} {0:indent=4,sort_keys=True}", json.repr(x))
        """
        if format_spec:
            # At this point, format_spec is a string that looks something like
            # "indent=4,sort_keys=True". What we want is to build a function call
            # from that which looks like:
            #
            #   json_encoder_factory(indent=4,sort_keys=True)
            #
            # which we can then eval() to create our encoder instance.
            make_encoder = "json_encoder_factory(" + format_spec + ")"
            encoder = eval(
                make_encoder, {"json_encoder_factory": self.json_encoder_factory}
            )
        else:
            encoder = self.json_encoder
        return encoder.encode(self.value)


# JSON property validators, for use with MessageDict.
#
# A validator is invoked with the actual value of the JSON property passed to it as
# the sole argument; or if the property is missing in JSON, then () is passed. Note
# that None represents an actual null in JSON, while () is a missing value.
#
# The validator must either raise TypeError or ValueError describing why the property
# value is invalid, or else return the value of the property, possibly after performing
# some substitutions - e.g. replacing () with some default value.


def _converter(value, classinfo):
    """Convert value (str) to number, otherwise return None if is not possible"""
    for one_info in classinfo:
        if issubclass(one_info, numbers.Number):
            try:
                return one_info(value)
            except ValueError:
                pass


def of_type(*classinfo, **kwargs):
    """Returns a validator for a JSON property that requires it to have a value of
    the specified type. If optional=True, () is also allowed.

    The meaning of classinfo is the same as for isinstance().
    """

    assert len(classinfo)
    optional = kwargs.pop("optional", False)
    assert not len(kwargs)

    def validate(value):
        if (optional and value == ()) or isinstance(value, classinfo):
            return value
        else:
            converted_value = _converter(value, classinfo)
            if converted_value:
                return converted_value

            if not optional and value == ():
                raise ValueError("must be specified")
            raise TypeError("must be " + " or ".join(t.__name__ for t in classinfo))

    return validate


def default(default):
    """Returns a validator for a JSON property with a default value.

    The validator will only allow property values that have the same type as the
    specified default value.
    """

    def validate(value):
        if value == ():
            return default
        elif isinstance(value, type(default)):
            return value
        else:
            raise TypeError("must be {0}".format(type(default).__name__))

    return validate


def enum(*values, **kwargs):
    """Returns a validator for a JSON enum.

    The validator will only allow the property to have one of the specified values.

    If optional=True, and the property is missing, the first value specified is used
    as the default.
    """

    assert len(values)
    optional = kwargs.pop("optional", False)
    assert not len(kwargs)

    def validate(value):
        if optional and value == ():
            return values[0]
        elif value in values:
            return value
        else:
            raise ValueError("must be one of: {0!r}".format(list(values)))

    return validate


def array(validate_item=False, vectorize=False, size=None):
    """Returns a validator for a JSON array.

    If the property is missing, it is treated as if it were []. Otherwise, it must
    be a list.

    If validate_item=False, it's treated as if it were (lambda x: x) - i.e. any item
    is considered valid, and is unchanged. If validate_item is a type or a tuple,
    it's treated as if it were json.of_type(validate).

    Every item in the list is replaced with validate_item(item) in-place, propagating
    any exceptions raised by the latter. If validate_item is a type or a tuple, it is
    treated as if it were json.of_type(validate_item).

    If vectorize=True, and the value is neither a list nor a dict, it is treated as
    if it were a single-element list containing that single value - e.g. "foo" is
    then the same as ["foo"]; but {} is an error, and not [{}].

    If size is not None, it can be an int, a tuple of one int, a tuple of two ints,
    or a set. If it's an int, the array must have exactly that many elements. If it's
    a tuple of one int, it's the minimum length. If it's a tuple of two ints, they
    are the minimum and the maximum lengths. If it's a set, it's the set of sizes that
    are valid - e.g. for {2, 4}, the array can be either 2 or 4 elements long.
    """

    if not validate_item:
        validate_item = lambda x: x
    elif isinstance(validate_item, type) or isinstance(validate_item, tuple):
        validate_item = of_type(validate_item)

    if size is None:
        validate_size = lambda _: True
    elif isinstance(size, set):
        size = {operator.index(n) for n in size}
        validate_size = lambda value: (
            len(value) in size
            or "must have {0} elements".format(
                " or ".join(str(n) for n in sorted(size))
            )
        )
    elif isinstance(size, tuple):
        assert 1 <= len(size) <= 2
        size = tuple(operator.index(n) for n in size)
        min_len, max_len = (size + (None,))[0:2]
        validate_size = lambda value: (
            "must have at least {0} elements".format(min_len)
            if len(value) < min_len
            else "must have at most {0} elements".format(max_len)
            if max_len is not None and len(value) < max_len
            else True
        )
    else:
        size = operator.index(size)
        validate_size = lambda value: (
            len(value) == size or "must have {0} elements".format(size)
        )

    def validate(value):
        if value == ():
            value = []
        elif vectorize and not isinstance(value, (list, dict)):
            value = [value]

        of_type(list)(value)

        size_err = validate_size(value)  # True if valid, str if error
        if size_err is not True:
            raise ValueError(size_err)

        for i, item in enumerate(value):
            try:
                value[i] = validate_item(item)
            except (TypeError, ValueError) as exc:
                raise type(exc)(f"[{repr(i)}] {exc}")
        return value

    return validate


def object(validate_value=False):
    """Returns a validator for a JSON object.

    If the property is missing, it is treated as if it were {}. Otherwise, it must
    be a dict.

    If validate_value=False, it's treated as if it were (lambda x: x) - i.e. any
    value is considered valid, and is unchanged. If validate_value is a type or a
    tuple, it's treated as if it were json.of_type(validate_value).

    Every value in the dict is replaced with validate_value(value) in-place, propagating
    any exceptions raised by the latter. If validate_value is a type or a tuple, it is
    treated as if it were json.of_type(validate_value). Keys are not affected.
    """

    if isinstance(validate_value, type) or isinstance(validate_value, tuple):
        validate_value = of_type(validate_value)

    def validate(value):
        if value == ():
            return {}

        of_type(dict)(value)
        if validate_value:
            for k, v in value.items():
                try:
                    value[k] = validate_value(v)
                except (TypeError, ValueError) as exc:
                    raise type(exc)(f"[{repr(k)}] {exc}")
        return value

    return validate


def repr(value):
    return JsonObject(value)


dumps = json.dumps
loads = json.loads

# === NexusCore/openenv\Lib\site-packages\litellm\llms\watsonx\common_utils.py ===
from typing import Dict, List, Optional, Union, cast

import httpx

import litellm
from litellm import verbose_logger
from litellm.caching import InMemoryCache
from litellm.litellm_core_utils.prompt_templates import factory as ptf
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import AllMessageValues
from litellm.types.llms.watsonx import WatsonXAPIParams, WatsonXCredentials


class WatsonXAIError(BaseLLMException):
    def __init__(
        self,
        status_code: int,
        message: str,
        headers: Optional[Union[Dict, httpx.Headers]] = None,
    ):
        super().__init__(status_code=status_code, message=message, headers=headers)


iam_token_cache = InMemoryCache()


def get_watsonx_iam_url():
    return (
        get_secret_str("WATSONX_IAM_URL") or "https://iam.cloud.ibm.com/identity/token"
    )


def generate_iam_token(api_key=None, **params) -> str:
    result: Optional[str] = iam_token_cache.get_cache(api_key)  # type: ignore

    if result is None:
        headers = {}
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        if api_key is None:
            api_key = (
                get_secret_str("WX_API_KEY")
                or get_secret_str("WATSONX_API_KEY")
                or get_secret_str("WATSONX_APIKEY")
            )
        if api_key is None:
            raise ValueError("API key is required")
        headers["Accept"] = "application/json"
        data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": api_key,
        }
        iam_token_url = get_watsonx_iam_url()
        verbose_logger.debug(
            "calling ibm `/identity/token` to retrieve IAM token.\nURL=%s\nheaders=%s\ndata=%s",
            iam_token_url,
            headers,
            data,
        )
        response = litellm.module_level_client.post(
            url=iam_token_url, data=data, headers=headers
        )
        response.raise_for_status()
        json_data = response.json()

        result = json_data["access_token"]
        iam_token_cache.set_cache(
            key=api_key,
            value=result,
            ttl=json_data["expires_in"] - 10,  # leave some buffer
        )

    return cast(str, result)


def _generate_watsonx_token(api_key: Optional[str], token: Optional[str]) -> str:
    if token is not None:
        return token
    token = generate_iam_token(api_key)
    return token


def _get_api_params(
    params: dict,
) -> WatsonXAPIParams:
    """
    Find watsonx.ai credentials in the params or environment variables and return the headers for authentication.
    """
    # Load auth variables from params
    project_id = params.pop(
        "project_id", params.pop("watsonx_project", None)
    )  # watsonx.ai project_id - allow 'watsonx_project' to be consistent with how vertex project implementation works -> reduce provider-specific params
    space_id = params.pop("space_id", None)  # watsonx.ai deployment space_id
    region_name = params.pop("region_name", params.pop("region", None))
    if region_name is None:
        region_name = params.pop(
            "watsonx_region_name", params.pop("watsonx_region", None)
        )  # consistent with how vertex ai + aws regions are accepted

    # Load auth variables from environment variables
    if project_id is None:
        project_id = (
            get_secret_str("WATSONX_PROJECT_ID")
            or get_secret_str("WX_PROJECT_ID")
            or get_secret_str("PROJECT_ID")
        )
    if region_name is None:
        region_name = (
            get_secret_str("WATSONX_REGION")
            or get_secret_str("WX_REGION")
            or get_secret_str("REGION")
        )
    if space_id is None:
        space_id = (
            get_secret_str("WATSONX_DEPLOYMENT_SPACE_ID")
            or get_secret_str("WATSONX_SPACE_ID")
            or get_secret_str("WX_SPACE_ID")
            or get_secret_str("SPACE_ID")
        )

    if project_id is None:
        raise WatsonXAIError(
            status_code=401,
            message="Error: Watsonx project_id not set. Set WX_PROJECT_ID in environment variables or pass in as a parameter.",
        )

    return WatsonXAPIParams(
        project_id=project_id,
        space_id=space_id,
        region_name=region_name,
    )


def convert_watsonx_messages_to_prompt(
    model: str,
    messages: List[AllMessageValues],
    provider: str,
    custom_prompt_dict: Dict,
) -> str:
    # handle anthropic prompts and amazon titan prompts
    if model in custom_prompt_dict:
        # check if the model has a registered custom prompt
        model_prompt_dict = custom_prompt_dict[model]
        prompt = ptf.custom_prompt(
            messages=messages,
            role_dict=model_prompt_dict.get(
                "role_dict", model_prompt_dict.get("roles")
            ),
            initial_prompt_value=model_prompt_dict.get("initial_prompt_value", ""),
            final_prompt_value=model_prompt_dict.get("final_prompt_value", ""),
            bos_token=model_prompt_dict.get("bos_token", ""),
            eos_token=model_prompt_dict.get("eos_token", ""),
        )
        return prompt
    elif provider == "ibm-mistralai":
        prompt = ptf.mistral_instruct_pt(messages=messages)
    else:
        prompt: str = ptf.prompt_factory(  # type: ignore
            model=model, messages=messages, custom_llm_provider="watsonx"
        )
    return prompt


# Mixin class for shared IBM Watson X functionality
class IBMWatsonXMixin:
    def validate_environment(
        self,
        headers: Dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> Dict:
        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if "Authorization" in headers:
            return {**default_headers, **headers}
        token = cast(
            Optional[str],
            optional_params.get("token") or get_secret_str("WATSONX_TOKEN"),
        )
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif zen_api_key := get_secret_str("WATSONX_ZENAPIKEY"):
            headers["Authorization"] = f"ZenApiKey {zen_api_key}"
        else:
            token = _generate_watsonx_token(api_key=api_key, token=token)
            # build auth headers
            headers["Authorization"] = f"Bearer {token}"
        return {**default_headers, **headers}

    def _get_base_url(self, api_base: Optional[str]) -> str:
        url = (
            api_base
            or get_secret_str("WATSONX_API_BASE")  # consistent with 'AZURE_API_BASE'
            or get_secret_str("WATSONX_URL")
            or get_secret_str("WX_URL")
            or get_secret_str("WML_URL")
        )

        if url is None:
            raise WatsonXAIError(
                status_code=401,
                message="Error: Watsonx URL not set. Set WATSONX_API_BASE in environment variables or pass in as parameter - 'api_base='.",
            )
        return url

    def _add_api_version_to_url(self, url: str, api_version: Optional[str]) -> str:
        api_version = api_version or litellm.WATSONX_DEFAULT_API_VERSION
        url = url + f"?version={api_version}"

        return url

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[Dict, httpx.Headers]
    ) -> BaseLLMException:
        return WatsonXAIError(
            status_code=status_code, message=error_message, headers=headers
        )

    @staticmethod
    def get_watsonx_credentials(
        optional_params: dict, api_key: Optional[str], api_base: Optional[str]
    ) -> WatsonXCredentials:
        api_key = (
            api_key
            or optional_params.pop("apikey", None)
            or get_secret_str("WATSONX_APIKEY")
            or get_secret_str("WATSONX_API_KEY")
            or get_secret_str("WX_API_KEY")
        )

        api_base = (
            api_base
            or optional_params.pop(
                "url",
                optional_params.pop("api_base", optional_params.pop("base_url", None)),
            )
            or get_secret_str("WATSONX_API_BASE")
            or get_secret_str("WATSONX_URL")
            or get_secret_str("WX_URL")
            or get_secret_str("WML_URL")
        )

        wx_credentials = optional_params.pop(
            "wx_credentials",
            optional_params.pop(
                "watsonx_credentials", None
            ),  # follow {provider}_credentials, same as vertex ai
        )

        token: Optional[str] = None

        if wx_credentials is not None:
            api_base = wx_credentials.get("url", api_base)
            api_key = wx_credentials.get(
                "apikey", wx_credentials.get("api_key", api_key)
            )
            token = wx_credentials.get(
                "token",
                wx_credentials.get(
                    "watsonx_token", None
                ),  # follow format of {provider}_token, same as azure - e.g. 'azure_ad_token=..'
            )
        if api_key is None or not isinstance(api_key, str):
            raise WatsonXAIError(
                status_code=401,
                message="Error: Watsonx API key not set. Set WATSONX_API_KEY in environment variables or pass in as parameter - 'api_key='.",
            )
        if api_base is None or not isinstance(api_base, str):
            raise WatsonXAIError(
                status_code=401,
                message="Error: Watsonx API base not set. Set WATSONX_API_BASE in environment variables or pass in as parameter - 'api_base='.",
            )
        return WatsonXCredentials(
            api_key=api_key, api_base=api_base, token=cast(Optional[str], token)
        )

    def _prepare_payload(self, model: str, api_params: WatsonXAPIParams) -> dict:
        payload: dict = {}
        if model.startswith("deployment/"):
            return (
                {}
            )  # Deployment models do not support 'space_id' or 'project_id' in their payload
        payload["model_id"] = model
        payload["project_id"] = api_params["project_id"]
        return payload

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\stanford_segmenter.py ===
#!/usr/bin/env python
# Natural Language Toolkit: Interface to the Stanford Segmenter
# for Chinese and Arabic
#
# Copyright (C) 2001-2024 NLTK Project
# Author: 52nlp <52nlpcn@gmail.com>
#         Casper Lehmann-Strøm <casperlehmann@gmail.com>
#         Alex Constantin <alex@keyworder.ch>
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import json
import os
import tempfile
import warnings
from subprocess import PIPE

from nltk.internals import (
    _java_options,
    config_java,
    find_dir,
    find_file,
    find_jar,
    java,
)
from nltk.tokenize.api import TokenizerI

_stanford_url = "https://nlp.stanford.edu/software"


class StanfordSegmenter(TokenizerI):
    """Interface to the Stanford Segmenter

    If stanford-segmenter version is older than 2016-10-31, then path_to_slf4j
    should be provieded, for example::

        seg = StanfordSegmenter(path_to_slf4j='/YOUR_PATH/slf4j-api.jar')

    >>> from nltk.tokenize.stanford_segmenter import StanfordSegmenter
    >>> seg = StanfordSegmenter() # doctest: +SKIP
    >>> seg.default_config('zh') # doctest: +SKIP
    >>> sent = u'这是斯坦福中文分词器测试'
    >>> print(seg.segment(sent)) # doctest: +SKIP
    \u8fd9 \u662f \u65af\u5766\u798f \u4e2d\u6587 \u5206\u8bcd\u5668 \u6d4b\u8bd5
    <BLANKLINE>
    >>> seg.default_config('ar') # doctest: +SKIP
    >>> sent = u'هذا هو تصنيف ستانفورد العربي للكلمات'
    >>> print(seg.segment(sent.split())) # doctest: +SKIP
    \u0647\u0630\u0627 \u0647\u0648 \u062a\u0635\u0646\u064a\u0641 \u0633\u062a\u0627\u0646\u0641\u0648\u0631\u062f \u0627\u0644\u0639\u0631\u0628\u064a \u0644 \u0627\u0644\u0643\u0644\u0645\u0627\u062a
    <BLANKLINE>
    """

    _JAR = "stanford-segmenter.jar"

    def __init__(
        self,
        path_to_jar=None,
        path_to_slf4j=None,
        java_class=None,
        path_to_model=None,
        path_to_dict=None,
        path_to_sihan_corpora_dict=None,
        sihan_post_processing="false",
        keep_whitespaces="false",
        encoding="UTF-8",
        options=None,
        verbose=False,
        java_options="-mx2g",
    ):
        # Raise deprecation warning.
        warnings.simplefilter("always", DeprecationWarning)
        warnings.warn(
            str(
                "\nThe StanfordTokenizer will "
                "be deprecated in version 3.2.5.\n"
                "Please use \033[91mnltk.parse.corenlp.CoreNLPTokenizer\033[0m instead.'"
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        warnings.simplefilter("ignore", DeprecationWarning)

        stanford_segmenter = find_jar(
            self._JAR,
            path_to_jar,
            env_vars=("STANFORD_SEGMENTER",),
            searchpath=(),
            url=_stanford_url,
            verbose=verbose,
        )
        if path_to_slf4j is not None:
            slf4j = find_jar(
                "slf4j-api.jar",
                path_to_slf4j,
                env_vars=("SLF4J", "STANFORD_SEGMENTER"),
                searchpath=(),
                url=_stanford_url,
                verbose=verbose,
            )
        else:
            slf4j = None

        # This is passed to java as the -cp option, the old version of segmenter needs slf4j.
        # The new version of stanford-segmenter-2016-10-31 doesn't need slf4j
        self._stanford_jar = os.pathsep.join(
            _ for _ in [stanford_segmenter, slf4j] if _ is not None
        )

        self._java_class = java_class
        self._model = path_to_model
        self._sihan_corpora_dict = path_to_sihan_corpora_dict
        self._sihan_post_processing = sihan_post_processing
        self._keep_whitespaces = keep_whitespaces
        self._dict = path_to_dict

        self._encoding = encoding
        self.java_options = java_options
        options = {} if options is None else options
        self._options_cmd = ",".join(
            f"{key}={json.dumps(val)}" for key, val in options.items()
        )

    def default_config(self, lang):
        """
        Attempt to initialize Stanford Word Segmenter for the specified language
        using the STANFORD_SEGMENTER and STANFORD_MODELS environment variables
        """

        search_path = ()
        if os.environ.get("STANFORD_SEGMENTER"):
            search_path = {os.path.join(os.environ.get("STANFORD_SEGMENTER"), "data")}

        # init for Chinese-specific files
        self._dict = None
        self._sihan_corpora_dict = None
        self._sihan_post_processing = "false"

        if lang == "ar":
            self._java_class = (
                "edu.stanford.nlp.international.arabic.process.ArabicSegmenter"
            )
            model = "arabic-segmenter-atb+bn+arztrain.ser.gz"

        elif lang == "zh":
            self._java_class = "edu.stanford.nlp.ie.crf.CRFClassifier"
            model = "pku.gz"
            self._sihan_post_processing = "true"

            path_to_dict = "dict-chris6.ser.gz"
            try:
                self._dict = find_file(
                    path_to_dict,
                    searchpath=search_path,
                    url=_stanford_url,
                    verbose=False,
                    env_vars=("STANFORD_MODELS",),
                )
            except LookupError as e:
                raise LookupError(
                    "Could not find '%s' (tried using env. "
                    "variables STANFORD_MODELS and <STANFORD_SEGMENTER>/data/)"
                    % path_to_dict
                ) from e

            sihan_dir = "./data/"
            try:
                path_to_sihan_dir = find_dir(
                    sihan_dir,
                    url=_stanford_url,
                    verbose=False,
                    env_vars=("STANFORD_SEGMENTER",),
                )
                self._sihan_corpora_dict = os.path.join(path_to_sihan_dir, sihan_dir)
            except LookupError as e:
                raise LookupError(
                    "Could not find '%s' (tried using the "
                    "STANFORD_SEGMENTER environment variable)" % sihan_dir
                ) from e
        else:
            raise LookupError(f"Unsupported language {lang}")

        try:
            self._model = find_file(
                model,
                searchpath=search_path,
                url=_stanford_url,
                verbose=False,
                env_vars=("STANFORD_MODELS", "STANFORD_SEGMENTER"),
            )
        except LookupError as e:
            raise LookupError(
                "Could not find '%s' (tried using env. "
                "variables STANFORD_MODELS and <STANFORD_SEGMENTER>/data/)" % model
            ) from e

    def tokenize(self, s):
        super().tokenize(s)

    def segment_file(self, input_file_path):
        """ """
        cmd = [
            self._java_class,
            "-loadClassifier",
            self._model,
            "-keepAllWhitespaces",
            self._keep_whitespaces,
            "-textFile",
            input_file_path,
        ]
        if self._sihan_corpora_dict is not None:
            cmd.extend(
                [
                    "-serDictionary",
                    self._dict,
                    "-sighanCorporaDict",
                    self._sihan_corpora_dict,
                    "-sighanPostProcessing",
                    self._sihan_post_processing,
                ]
            )

        stdout = self._execute(cmd)

        return stdout

    def segment(self, tokens):
        return self.segment_sents([tokens])

    def segment_sents(self, sentences):
        """ """
        encoding = self._encoding
        # Create a temporary input file
        _input_fh, self._input_file_path = tempfile.mkstemp(text=True)

        # Write the actural sentences to the temporary input file
        _input_fh = os.fdopen(_input_fh, "wb")
        _input = "\n".join(" ".join(x) for x in sentences)
        if isinstance(_input, str) and encoding:
            _input = _input.encode(encoding)
        _input_fh.write(_input)
        _input_fh.close()

        cmd = [
            self._java_class,
            "-loadClassifier",
            self._model,
            "-keepAllWhitespaces",
            self._keep_whitespaces,
            "-textFile",
            self._input_file_path,
        ]
        if self._sihan_corpora_dict is not None:
            cmd.extend(
                [
                    "-serDictionary",
                    self._dict,
                    "-sighanCorporaDict",
                    self._sihan_corpora_dict,
                    "-sighanPostProcessing",
                    self._sihan_post_processing,
                ]
            )

        stdout = self._execute(cmd)

        # Delete the temporary file
        os.unlink(self._input_file_path)

        return stdout

    def _execute(self, cmd, verbose=False):
        encoding = self._encoding
        cmd.extend(["-inputEncoding", encoding])
        _options_cmd = self._options_cmd
        if _options_cmd:
            cmd.extend(["-options", self._options_cmd])

        default_options = " ".join(_java_options)

        # Configure java.
        config_java(options=self.java_options, verbose=verbose)

        stdout, _stderr = java(
            cmd, classpath=self._stanford_jar, stdout=PIPE, stderr=PIPE
        )
        stdout = stdout.decode(encoding)

        # Return java configurations to their default values.
        config_java(options=default_options, verbose=False)

        return stdout

# === NexusCore/openenv\Lib\site-packages\openai\resources\embeddings.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import array
import base64
from typing import List, Union, Iterable, cast
from typing_extensions import Literal

import httpx

from .. import _legacy_response
from ..types import embedding_create_params
from .._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from .._utils import is_given, maybe_transform
from .._compat import cached_property
from .._extras import numpy as np, has_numpy
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from .._base_client import make_request_options
from ..types.embedding_model import EmbeddingModel
from ..types.create_embedding_response import CreateEmbeddingResponse

__all__ = ["Embeddings", "AsyncEmbeddings"]


class Embeddings(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> EmbeddingsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return EmbeddingsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> EmbeddingsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return EmbeddingsWithStreamingResponse(self)

    def create(
        self,
        *,
        input: Union[str, List[str], Iterable[int], Iterable[Iterable[int]]],
        model: Union[str, EmbeddingModel],
        dimensions: int | NotGiven = NOT_GIVEN,
        encoding_format: Literal["float", "base64"] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> CreateEmbeddingResponse:
        """
        Creates an embedding vector representing the input text.

        Args:
          input: Input text to embed, encoded as a string or array of tokens. To embed multiple
              inputs in a single request, pass an array of strings or array of token arrays.
              The input must not exceed the max input tokens for the model (8192 tokens for
              all embedding models), cannot be an empty string, and any array must be 2048
              dimensions or less.
              [Example Python code](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken)
              for counting tokens. In addition to the per-input token limit, all embedding
              models enforce a maximum of 300,000 tokens summed across all inputs in a single
              request.

          model: ID of the model to use. You can use the
              [List models](https://platform.openai.com/docs/api-reference/models/list) API to
              see all of your available models, or see our
              [Model overview](https://platform.openai.com/docs/models) for descriptions of
              them.

          dimensions: The number of dimensions the resulting output embeddings should have. Only
              supported in `text-embedding-3` and later models.

          encoding_format: The format to return the embeddings in. Can be either `float` or
              [`base64`](https://pypi.org/project/pybase64/).

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        params = {
            "input": input,
            "model": model,
            "user": user,
            "dimensions": dimensions,
            "encoding_format": encoding_format,
        }
        if not is_given(encoding_format):
            params["encoding_format"] = "base64"

        def parser(obj: CreateEmbeddingResponse) -> CreateEmbeddingResponse:
            if is_given(encoding_format):
                # don't modify the response object if a user explicitly asked for a format
                return obj

            for embedding in obj.data:
                data = cast(object, embedding.embedding)
                if not isinstance(data, str):
                    continue
                if not has_numpy():
                    # use array for base64 optimisation
                    embedding.embedding = array.array("f", base64.b64decode(data)).tolist()
                else:
                    embedding.embedding = np.frombuffer(  # type: ignore[no-untyped-call]
                        base64.b64decode(data), dtype="float32"
                    ).tolist()

            return obj

        return self._post(
            "/embeddings",
            body=maybe_transform(params, embedding_create_params.EmbeddingCreateParams),
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                post_parser=parser,
            ),
            cast_to=CreateEmbeddingResponse,
        )


class AsyncEmbeddings(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncEmbeddingsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncEmbeddingsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncEmbeddingsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncEmbeddingsWithStreamingResponse(self)

    async def create(
        self,
        *,
        input: Union[str, List[str], Iterable[int], Iterable[Iterable[int]]],
        model: Union[str, EmbeddingModel],
        dimensions: int | NotGiven = NOT_GIVEN,
        encoding_format: Literal["float", "base64"] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> CreateEmbeddingResponse:
        """
        Creates an embedding vector representing the input text.

        Args:
          input: Input text to embed, encoded as a string or array of tokens. To embed multiple
              inputs in a single request, pass an array of strings or array of token arrays.
              The input must not exceed the max input tokens for the model (8192 tokens for
              all embedding models), cannot be an empty string, and any array must be 2048
              dimensions or less.
              [Example Python code](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken)
              for counting tokens. In addition to the per-input token limit, all embedding
              models enforce a maximum of 300,000 tokens summed across all inputs in a single
              request.

          model: ID of the model to use. You can use the
              [List models](https://platform.openai.com/docs/api-reference/models/list) API to
              see all of your available models, or see our
              [Model overview](https://platform.openai.com/docs/models) for descriptions of
              them.

          dimensions: The number of dimensions the resulting output embeddings should have. Only
              supported in `text-embedding-3` and later models.

          encoding_format: The format to return the embeddings in. Can be either `float` or
              [`base64`](https://pypi.org/project/pybase64/).

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        params = {
            "input": input,
            "model": model,
            "user": user,
            "dimensions": dimensions,
            "encoding_format": encoding_format,
        }
        if not is_given(encoding_format):
            params["encoding_format"] = "base64"

        def parser(obj: CreateEmbeddingResponse) -> CreateEmbeddingResponse:
            if is_given(encoding_format):
                # don't modify the response object if a user explicitly asked for a format
                return obj

            for embedding in obj.data:
                data = cast(object, embedding.embedding)
                if not isinstance(data, str):
                    continue
                if not has_numpy():
                    # use array for base64 optimisation
                    embedding.embedding = array.array("f", base64.b64decode(data)).tolist()
                else:
                    embedding.embedding = np.frombuffer(  # type: ignore[no-untyped-call]
                        base64.b64decode(data), dtype="float32"
                    ).tolist()

            return obj

        return await self._post(
            "/embeddings",
            body=maybe_transform(params, embedding_create_params.EmbeddingCreateParams),
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                post_parser=parser,
            ),
            cast_to=CreateEmbeddingResponse,
        )


class EmbeddingsWithRawResponse:
    def __init__(self, embeddings: Embeddings) -> None:
        self._embeddings = embeddings

        self.create = _legacy_response.to_raw_response_wrapper(
            embeddings.create,
        )


class AsyncEmbeddingsWithRawResponse:
    def __init__(self, embeddings: AsyncEmbeddings) -> None:
        self._embeddings = embeddings

        self.create = _legacy_response.async_to_raw_response_wrapper(
            embeddings.create,
        )


class EmbeddingsWithStreamingResponse:
    def __init__(self, embeddings: Embeddings) -> None:
        self._embeddings = embeddings

        self.create = to_streamed_response_wrapper(
            embeddings.create,
        )


class AsyncEmbeddingsWithStreamingResponse:
    def __init__(self, embeddings: AsyncEmbeddings) -> None:
        self._embeddings = embeddings

        self.create = async_to_streamed_response_wrapper(
            embeddings.create,
        )

# === NexusCore/openenv\Lib\site-packages\openai\types\evals\run_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, List, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from ..responses.tool_param import ToolParam
from ..shared_params.metadata import Metadata
from ..shared.reasoning_effort import ReasoningEffort
from ..responses.response_input_text_param import ResponseInputTextParam
from .create_eval_jsonl_run_data_source_param import CreateEvalJSONLRunDataSourceParam
from ..responses.response_format_text_config_param import ResponseFormatTextConfigParam
from .create_eval_completions_run_data_source_param import CreateEvalCompletionsRunDataSourceParam

__all__ = [
    "RunCreateParams",
    "DataSource",
    "DataSourceCreateEvalResponsesRunDataSource",
    "DataSourceCreateEvalResponsesRunDataSourceSource",
    "DataSourceCreateEvalResponsesRunDataSourceSourceFileContent",
    "DataSourceCreateEvalResponsesRunDataSourceSourceFileContentContent",
    "DataSourceCreateEvalResponsesRunDataSourceSourceFileID",
    "DataSourceCreateEvalResponsesRunDataSourceSourceResponses",
    "DataSourceCreateEvalResponsesRunDataSourceInputMessages",
    "DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplate",
    "DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplate",
    "DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplateChatMessage",
    "DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplateEvalItem",
    "DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplateEvalItemContent",
    "DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplateEvalItemContentOutputText",
    "DataSourceCreateEvalResponsesRunDataSourceInputMessagesItemReference",
    "DataSourceCreateEvalResponsesRunDataSourceSamplingParams",
    "DataSourceCreateEvalResponsesRunDataSourceSamplingParamsText",
]


class RunCreateParams(TypedDict, total=False):
    data_source: Required[DataSource]
    """Details about the run's data source."""

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    name: str
    """The name of the run."""


class DataSourceCreateEvalResponsesRunDataSourceSourceFileContentContent(TypedDict, total=False):
    item: Required[Dict[str, object]]

    sample: Dict[str, object]


class DataSourceCreateEvalResponsesRunDataSourceSourceFileContent(TypedDict, total=False):
    content: Required[Iterable[DataSourceCreateEvalResponsesRunDataSourceSourceFileContentContent]]
    """The content of the jsonl file."""

    type: Required[Literal["file_content"]]
    """The type of jsonl source. Always `file_content`."""


class DataSourceCreateEvalResponsesRunDataSourceSourceFileID(TypedDict, total=False):
    id: Required[str]
    """The identifier of the file."""

    type: Required[Literal["file_id"]]
    """The type of jsonl source. Always `file_id`."""


class DataSourceCreateEvalResponsesRunDataSourceSourceResponses(TypedDict, total=False):
    type: Required[Literal["responses"]]
    """The type of run data source. Always `responses`."""

    created_after: Optional[int]
    """Only include items created after this timestamp (inclusive).

    This is a query parameter used to select responses.
    """

    created_before: Optional[int]
    """Only include items created before this timestamp (inclusive).

    This is a query parameter used to select responses.
    """

    instructions_search: Optional[str]
    """Optional string to search the 'instructions' field.

    This is a query parameter used to select responses.
    """

    metadata: Optional[object]
    """Metadata filter for the responses.

    This is a query parameter used to select responses.
    """

    model: Optional[str]
    """The name of the model to find responses for.

    This is a query parameter used to select responses.
    """

    reasoning_effort: Optional[ReasoningEffort]
    """Optional reasoning effort parameter.

    This is a query parameter used to select responses.
    """

    temperature: Optional[float]
    """Sampling temperature. This is a query parameter used to select responses."""

    tools: Optional[List[str]]
    """List of tool names. This is a query parameter used to select responses."""

    top_p: Optional[float]
    """Nucleus sampling parameter. This is a query parameter used to select responses."""

    users: Optional[List[str]]
    """List of user identifiers. This is a query parameter used to select responses."""


DataSourceCreateEvalResponsesRunDataSourceSource: TypeAlias = Union[
    DataSourceCreateEvalResponsesRunDataSourceSourceFileContent,
    DataSourceCreateEvalResponsesRunDataSourceSourceFileID,
    DataSourceCreateEvalResponsesRunDataSourceSourceResponses,
]


class DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplateChatMessage(TypedDict, total=False):
    content: Required[str]
    """The content of the message."""

    role: Required[str]
    """The role of the message (e.g. "system", "assistant", "user")."""


class DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplateEvalItemContentOutputText(
    TypedDict, total=False
):
    text: Required[str]
    """The text output from the model."""

    type: Required[Literal["output_text"]]
    """The type of the output text. Always `output_text`."""


DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplateEvalItemContent: TypeAlias = Union[
    str,
    ResponseInputTextParam,
    DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplateEvalItemContentOutputText,
]


class DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplateEvalItem(TypedDict, total=False):
    content: Required[DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplateEvalItemContent]
    """Text inputs to the model - can contain template strings."""

    role: Required[Literal["user", "assistant", "system", "developer"]]
    """The role of the message input.

    One of `user`, `assistant`, `system`, or `developer`.
    """

    type: Literal["message"]
    """The type of the message input. Always `message`."""


DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplate: TypeAlias = Union[
    DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplateChatMessage,
    DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplateEvalItem,
]


class DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplate(TypedDict, total=False):
    template: Required[Iterable[DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplateTemplate]]
    """A list of chat messages forming the prompt or context.

    May include variable references to the `item` namespace, ie {{item.name}}.
    """

    type: Required[Literal["template"]]
    """The type of input messages. Always `template`."""


class DataSourceCreateEvalResponsesRunDataSourceInputMessagesItemReference(TypedDict, total=False):
    item_reference: Required[str]
    """A reference to a variable in the `item` namespace. Ie, "item.name" """

    type: Required[Literal["item_reference"]]
    """The type of input messages. Always `item_reference`."""


DataSourceCreateEvalResponsesRunDataSourceInputMessages: TypeAlias = Union[
    DataSourceCreateEvalResponsesRunDataSourceInputMessagesTemplate,
    DataSourceCreateEvalResponsesRunDataSourceInputMessagesItemReference,
]


class DataSourceCreateEvalResponsesRunDataSourceSamplingParamsText(TypedDict, total=False):
    format: ResponseFormatTextConfigParam
    """An object specifying the format that the model must output.

    Configuring `{ "type": "json_schema" }` enables Structured Outputs, which
    ensures the model will match your supplied JSON schema. Learn more in the
    [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

    The default format is `{ "type": "text" }` with no additional options.

    **Not recommended for gpt-4o and newer models:**

    Setting to `{ "type": "json_object" }` enables the older JSON mode, which
    ensures the message the model generates is valid JSON. Using `json_schema` is
    preferred for models that support it.
    """


class DataSourceCreateEvalResponsesRunDataSourceSamplingParams(TypedDict, total=False):
    max_completion_tokens: int
    """The maximum number of tokens in the generated output."""

    seed: int
    """A seed value to initialize the randomness, during sampling."""

    temperature: float
    """A higher temperature increases randomness in the outputs."""

    text: DataSourceCreateEvalResponsesRunDataSourceSamplingParamsText
    """Configuration options for a text response from the model.

    Can be plain text or structured JSON data. Learn more:

    - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
    - [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
    """

    tools: Iterable[ToolParam]
    """An array of tools the model may call while generating a response.

    You can specify which tool to use by setting the `tool_choice` parameter.

    The two categories of tools you can provide the model are:

    - **Built-in tools**: Tools that are provided by OpenAI that extend the model's
      capabilities, like
      [web search](https://platform.openai.com/docs/guides/tools-web-search) or
      [file search](https://platform.openai.com/docs/guides/tools-file-search).
      Learn more about
      [built-in tools](https://platform.openai.com/docs/guides/tools).
    - **Function calls (custom tools)**: Functions that are defined by you, enabling
      the model to call your own code. Learn more about
      [function calling](https://platform.openai.com/docs/guides/function-calling).
    """

    top_p: float
    """An alternative to temperature for nucleus sampling; 1.0 includes all tokens."""


class DataSourceCreateEvalResponsesRunDataSource(TypedDict, total=False):
    source: Required[DataSourceCreateEvalResponsesRunDataSourceSource]
    """Determines what populates the `item` namespace in this run's data source."""

    type: Required[Literal["responses"]]
    """The type of run data source. Always `responses`."""

    input_messages: DataSourceCreateEvalResponsesRunDataSourceInputMessages
    """Used when sampling from a model.

    Dictates the structure of the messages passed into the model. Can either be a
    reference to a prebuilt trajectory (ie, `item.input_trajectory`), or a template
    with variable references to the `item` namespace.
    """

    model: str
    """The name of the model to use for generating completions (e.g. "o3-mini")."""

    sampling_params: DataSourceCreateEvalResponsesRunDataSourceSamplingParams


DataSource: TypeAlias = Union[
    CreateEvalJSONLRunDataSourceParam,
    CreateEvalCompletionsRunDataSourceParam,
    DataSourceCreateEvalResponsesRunDataSource,
]

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\platformdirs\api.py ===
"""Base API."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterator, Literal


class PlatformDirsABC(ABC):  # noqa: PLR0904
    """Abstract base class for platform directories."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        appname: str | None = None,
        appauthor: str | None | Literal[False] = None,
        version: str | None = None,
        roaming: bool = False,  # noqa: FBT001, FBT002
        multipath: bool = False,  # noqa: FBT001, FBT002
        opinion: bool = True,  # noqa: FBT001, FBT002
        ensure_exists: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """
        Create a new platform directory.

        :param appname: See `appname`.
        :param appauthor: See `appauthor`.
        :param version: See `version`.
        :param roaming: See `roaming`.
        :param multipath: See `multipath`.
        :param opinion: See `opinion`.
        :param ensure_exists: See `ensure_exists`.

        """
        self.appname = appname  #: The name of application.
        self.appauthor = appauthor
        """
        The name of the app author or distributing body for this application.

        Typically, it is the owning company name. Defaults to `appname`. You may pass ``False`` to disable it.

        """
        self.version = version
        """
        An optional version path element to append to the path.

        You might want to use this if you want multiple versions of your app to be able to run independently. If used,
        this would typically be ``<major>.<minor>``.

        """
        self.roaming = roaming
        """
        Whether to use the roaming appdata directory on Windows.

        That means that for users on a Windows network setup for roaming profiles, this user data will be synced on
        login (see
        `here <https://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx>`_).

        """
        self.multipath = multipath
        """
        An optional parameter which indicates that the entire list of data dirs should be returned.

        By default, the first item would only be returned.

        """
        self.opinion = opinion  #: A flag to indicating to use opinionated values.
        self.ensure_exists = ensure_exists
        """
        Optionally create the directory (and any missing parents) upon access if it does not exist.

        By default, no directories are created.

        """

    def _append_app_name_and_version(self, *base: str) -> str:
        params = list(base[1:])
        if self.appname:
            params.append(self.appname)
            if self.version:
                params.append(self.version)
        path = os.path.join(base[0], *params)  # noqa: PTH118
        self._optionally_create_directory(path)
        return path

    def _optionally_create_directory(self, path: str) -> None:
        if self.ensure_exists:
            Path(path).mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def user_data_dir(self) -> str:
        """:return: data directory tied to the user"""

    @property
    @abstractmethod
    def site_data_dir(self) -> str:
        """:return: data directory shared by users"""

    @property
    @abstractmethod
    def user_config_dir(self) -> str:
        """:return: config directory tied to the user"""

    @property
    @abstractmethod
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users"""

    @property
    @abstractmethod
    def user_cache_dir(self) -> str:
        """:return: cache directory tied to the user"""

    @property
    @abstractmethod
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users"""

    @property
    @abstractmethod
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user"""

    @property
    @abstractmethod
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user"""

    @property
    @abstractmethod
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user"""

    @property
    @abstractmethod
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user"""

    @property
    @abstractmethod
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user"""

    @property
    @abstractmethod
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user"""

    @property
    @abstractmethod
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user"""

    @property
    @abstractmethod
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user"""

    @property
    @abstractmethod
    def user_runtime_dir(self) -> str:
        """:return: runtime directory tied to the user"""

    @property
    @abstractmethod
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users"""

    @property
    def user_data_path(self) -> Path:
        """:return: data path tied to the user"""
        return Path(self.user_data_dir)

    @property
    def site_data_path(self) -> Path:
        """:return: data path shared by users"""
        return Path(self.site_data_dir)

    @property
    def user_config_path(self) -> Path:
        """:return: config path tied to the user"""
        return Path(self.user_config_dir)

    @property
    def site_config_path(self) -> Path:
        """:return: config path shared by the users"""
        return Path(self.site_config_dir)

    @property
    def user_cache_path(self) -> Path:
        """:return: cache path tied to the user"""
        return Path(self.user_cache_dir)

    @property
    def site_cache_path(self) -> Path:
        """:return: cache path shared by users"""
        return Path(self.site_cache_dir)

    @property
    def user_state_path(self) -> Path:
        """:return: state path tied to the user"""
        return Path(self.user_state_dir)

    @property
    def user_log_path(self) -> Path:
        """:return: log path tied to the user"""
        return Path(self.user_log_dir)

    @property
    def user_documents_path(self) -> Path:
        """:return: documents a path tied to the user"""
        return Path(self.user_documents_dir)

    @property
    def user_downloads_path(self) -> Path:
        """:return: downloads path tied to the user"""
        return Path(self.user_downloads_dir)

    @property
    def user_pictures_path(self) -> Path:
        """:return: pictures path tied to the user"""
        return Path(self.user_pictures_dir)

    @property
    def user_videos_path(self) -> Path:
        """:return: videos path tied to the user"""
        return Path(self.user_videos_dir)

    @property
    def user_music_path(self) -> Path:
        """:return: music path tied to the user"""
        return Path(self.user_music_dir)

    @property
    def user_desktop_path(self) -> Path:
        """:return: desktop path tied to the user"""
        return Path(self.user_desktop_dir)

    @property
    def user_runtime_path(self) -> Path:
        """:return: runtime path tied to the user"""
        return Path(self.user_runtime_dir)

    @property
    def site_runtime_path(self) -> Path:
        """:return: runtime path shared by users"""
        return Path(self.site_runtime_dir)

    def iter_config_dirs(self) -> Iterator[str]:
        """:yield: all user and site configuration directories."""
        yield self.user_config_dir
        yield self.site_config_dir

    def iter_data_dirs(self) -> Iterator[str]:
        """:yield: all user and site data directories."""
        yield self.user_data_dir
        yield self.site_data_dir

    def iter_cache_dirs(self) -> Iterator[str]:
        """:yield: all user and site cache directories."""
        yield self.user_cache_dir
        yield self.site_cache_dir

    def iter_runtime_dirs(self) -> Iterator[str]:
        """:yield: all user and site runtime directories."""
        yield self.user_runtime_dir
        yield self.site_runtime_dir

    def iter_config_paths(self) -> Iterator[Path]:
        """:yield: all user and site configuration paths."""
        for path in self.iter_config_dirs():
            yield Path(path)

    def iter_data_paths(self) -> Iterator[Path]:
        """:yield: all user and site data paths."""
        for path in self.iter_data_dirs():
            yield Path(path)

    def iter_cache_paths(self) -> Iterator[Path]:
        """:yield: all user and site cache paths."""
        for path in self.iter_cache_dirs():
            yield Path(path)

    def iter_runtime_paths(self) -> Iterator[Path]:
        """:yield: all user and site runtime paths."""
        for path in self.iter_runtime_dirs():
            yield Path(path)

# === NexusCore/openenv\Lib\site-packages\jinxed\_tparm.py ===
# -*- coding: utf-8 -*-
# Copyright 2019 - 2022 Avram Lubkin, All Rights Reserved

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
An pure Python implementation of tparm
Based on documentation in man(5) terminfo and comparing behavior of curses.tparm
"""

from collections import deque
import operator
import re


OPERATORS = {b'+': operator.add,
             b'-': operator.sub,
             b'*': operator.mul,
             b'/': operator.floordiv,
             b'm': operator.mod,
             b'&': operator.and_,
             b'|': operator.or_,
             b'^': operator.xor,
             b'=': operator.eq,
             b'>': operator.gt,
             b'<': operator.lt,
             b'~': operator.inv,
             b'!': operator.not_,
             b'A': lambda x, y: bool(x and y),
             b'O': lambda x, y: bool(x or y)}

FILTERS = (('_literal_percent', br'%%'),
           ('_pop_c', br'%c'),
           ('_increment_one_two', br'%i'),
           ('_binary_op', br'%([\+\-\*/m\&\|\^=><AO])'),
           ('_unary_op', br'%([\~!])'),
           ('_push_param', br'%p([1-9]\d*)'),
           ('_set_dynamic', br'%P([a-z])'),
           ('_get_dynamic', br'%g([a-z])'),
           ('_set_static', br'%P([A-Z])'),
           ('_get_static', br'%g([A-Z])'),
           ('_char_constant', br"%'(.)'"),
           ('_int_constant', br'%{(\d+)}'),
           ('_push_len', br'%l'),
           ('_cond_if', br'%\?(.+?)(?=%t)'),
           ('_cond_then_else', br'%t(.+?)(?=%e)'),
           ('_cond_then_fi', br'%t(.+?)(?=%;)'),
           ('_cond_else', br'%e(.+?)(?=%;|$)'),
           ('_cond_fi', br'%;'),
           ('_printf', br'%:?[^%]*?[doxXs]'),
           ('_unmatched', br'%.'),
           ('_literal', br'[^%]+'))

PATTERNS = tuple((re.compile(pattern), filter_) for filter_, pattern in FILTERS)
NULL = type('Null', (int,), {})(0)


class TParm(object):  # pylint: disable=useless-object-inheritance
    """
    Class to hold tparm methods and persist variables between calls
    """

    def __init__(self, *params, **kwargs):

        self.rtn = b''
        self.stack = deque()

        # The spec for tparm allows c string parameters, but most implementations don't
        # The reference code makes a best effort to determine which parameters require strings
        # We'll allow them without trying to predict
        for param in params:
            if not isinstance(param, (int, bytes)):
                raise TypeError('Parameters must be integers or bytes, not %s' %
                                type(param).__name__)
        self.params = list(params)

        static = kwargs.get('static')
        self.static = {} if static is None else static
        self.dynamic = {}

    def __call__(self, string, *params):
        self.dynamic = {}  # As of ncurses 6.3, dynamic variables do not persist between calls
        return self.child(*params).parse(string)

    def _literal_percent(self, group):  # pylint: disable=unused-argument
        """
        Literal percent sign
        """
        self.rtn += b'%'

    def _pop_c(self, group):  # pylint: disable=unused-argument
        """
        Return pop() like %c in printf
        """

        try:
            value = self.stack.pop()
        except IndexError:
            value = NULL

        # Treat null as 0x80
        if value is NULL:
            value = 0x80

        self.rtn += b'%c' % value

    def _increment_one_two(self, group):  # pylint: disable=unused-argument
        """
        Add 1 to first two parameters
        Missing parameters are treated as 0's
        """
        for index in (0, 1):
            try:
                self.params[index] += 1
            except IndexError:
                self.params.append(1)

    def _binary_op(self, group):
        """
        Perform a binary operation on the last two items on the stack
        The order of evaluation is the order the items were placed on the stack
        """
        second_val = self.stack.pop()
        self.stack.append(OPERATORS[group](self.stack.pop(), second_val))

    def _unary_op(self, group):
        """
        Perform a unary operation on the last item on the stack
        """
        self.stack.append(OPERATORS[group](self.stack.pop()))

    def _push_param(self, group):
        """
        Push a parameter onto the stack
        If the parameter is missing, push Null
        """
        try:
            self.stack.append(self.params[int(group) - 1])
        except IndexError:
            self.stack.append(NULL)

    def _set_dynamic(self, group):
        """
        Set the a dynamic variable to pop()
        """
        self.dynamic[group] = self.stack.pop()

    def _get_dynamic(self, group):
        """
        Push the value of a dynamic variable onto the stack
        """
        self.stack.append(self.dynamic.get(group, NULL))

    def _set_static(self, group):
        """
        Set the a static variable to pop()
        """
        self.static[group] = self.stack.pop()

    def _get_static(self, group):
        """
        Push the value of a static variable onto the stack
        """
        self.stack.append(self.static.get(group, NULL))

    def _char_constant(self, group):
        """
        Push an character constant onto the stack
        """
        self.stack.append(ord(group))

    def _int_constant(self, group):
        """
        Push an integer constant onto the stack
        """
        self.stack.append(int(group))

    def _push_len(self, group):  # pylint: disable=unused-argument
        """
        Replace the last item on the stack with its length
        """
        self.stack.append(len(self.stack.pop()))

    def _cond_if(self, group):
        """
        Recursively evaluate the body of the if statement
        """
        self.parse(group)

    def _cond_then_else(self, group):
        """
        If the last item on the stack is True,
        recursively evaluate then statement

        Do not consume last item on stack
        """
        if self.stack[-1]:
            self.parse(group)

    def _cond_then_fi(self, group):
        """
        If the last item on the stack is True,
        recursively evaluate then statement

        Always consume last item on stack
        """
        if self.stack.pop():
            self.parse(group)

    def _cond_else(self, group):
        """
        If the last item on the stack is False,
        recursively evaluate the both of the else statement

        Always consume last item on stack
        """
        if not self.stack.pop():
            self.parse(group)

    def _cond_fi(self, group):  # pylint: disable=unused-argument
        """
        End if statement
        """

    def _printf(self, group):
        """
        Subset of printf-like formatting
        """

        # : is an escape to prevent flags from being treated as % operators, ignore
        # Python 2 returns as ':', Python 3 returns as 58
        if group[1] in (b':', 58):
            group = b'%' + group[2:]

        try:
            value = self.stack.pop()
        except IndexError:
            value = NULL

        # Treat null as empty string when string formatting
        # Python 2 returns as 's', Python 3 returns as 115
        if value is NULL and group[-1] in (b's', 115):
            value = b''

        self.rtn += group % value

    def _unmatched(self, group):  # pylint: disable=unused-argument
        """
        Escape pattern with no spec is skipped
        """

    def _literal(self, group):
        """
        Anything not prefaced with a known pattern spec is treated literally
        """
        self.rtn += group

    def parse(self, string):
        """
        Parsing loop
        Evaluate regex patterns in order until a pattern is matched
        """

        if not isinstance(string, bytes):
            raise TypeError("A bytes-like object is required, not '%s'" % type(string).__name__)

        index = 0
        length = len(string)

        while index < length:
            for filt, meth in PATTERNS:  # pragma: no branch
                match = re.match(filt, string[index:])
                if match:
                    group = match.groups()[-1] if match.groups() else match.group(0)
                    getattr(self, meth)(group)
                    index += match.end()
                    break

        return self.rtn

    def child(self, *params):
        """
        Return a new instance with the same variables, but different parameters
        """
        return self.__class__(*params, static=self.static, dynamic=self.dynamic)


tparm = TParm()  # pylint: disable=invalid-name
"""Reimplementation of :py:func:`curses.tparm`"""

# === NexusCore/openenv\Lib\site-packages\joblib\numpy_pickle_utils.py ===
"""Utilities for fast persistence of big data, with optional compression."""

# Author: Gael Varoquaux <gael dot varoquaux at normalesup dot org>
# Copyright (c) 2009 Gael Varoquaux
# License: BSD Style, 3 clauses.

import contextlib
import io
import pickle
import sys
import warnings

from .compressor import _COMPRESSORS, _ZFILE_PREFIX

try:
    import numpy as np
except ImportError:
    np = None

Unpickler = pickle._Unpickler
Pickler = pickle._Pickler
xrange = range


try:
    # The python standard library can be built without bz2 so we make bz2
    # usage optional.
    # see https://github.com/scikit-learn/scikit-learn/issues/7526 for more
    # details.
    import bz2
except ImportError:
    bz2 = None

# Buffer size used in io.BufferedReader and io.BufferedWriter
_IO_BUFFER_SIZE = 1024**2


def _is_raw_file(fileobj):
    """Check if fileobj is a raw file object, e.g created with open."""
    fileobj = getattr(fileobj, "raw", fileobj)
    return isinstance(fileobj, io.FileIO)


def _get_prefixes_max_len():
    # Compute the max prefix len of registered compressors.
    prefixes = [len(compressor.prefix) for compressor in _COMPRESSORS.values()]
    prefixes += [len(_ZFILE_PREFIX)]
    return max(prefixes)


def _is_numpy_array_byte_order_mismatch(array):
    """Check if numpy array is having byte order mismatch"""
    return (
        sys.byteorder == "big"
        and (
            array.dtype.byteorder == "<"
            or (
                array.dtype.byteorder == "|"
                and array.dtype.fields
                and all(e[0].byteorder == "<" for e in array.dtype.fields.values())
            )
        )
    ) or (
        sys.byteorder == "little"
        and (
            array.dtype.byteorder == ">"
            or (
                array.dtype.byteorder == "|"
                and array.dtype.fields
                and all(e[0].byteorder == ">" for e in array.dtype.fields.values())
            )
        )
    )


def _ensure_native_byte_order(array):
    """Use the byte order of the host while preserving values

    Does nothing if array already uses the system byte order.
    """
    if _is_numpy_array_byte_order_mismatch(array):
        array = array.byteswap().view(array.dtype.newbyteorder("="))
    return array


###############################################################################
# Cache file utilities
def _detect_compressor(fileobj):
    """Return the compressor matching fileobj.

    Parameters
    ----------
    fileobj: file object

    Returns
    -------
    str in {'zlib', 'gzip', 'bz2', 'lzma', 'xz', 'compat', 'not-compressed'}
    """
    # Read the magic number in the first bytes of the file.
    max_prefix_len = _get_prefixes_max_len()
    if hasattr(fileobj, "peek"):
        # Peek allows to read those bytes without moving the cursor in the
        # file which.
        first_bytes = fileobj.peek(max_prefix_len)
    else:
        # Fallback to seek if the fileobject is not peekable.
        first_bytes = fileobj.read(max_prefix_len)
        fileobj.seek(0)

    if first_bytes.startswith(_ZFILE_PREFIX):
        return "compat"
    else:
        for name, compressor in _COMPRESSORS.items():
            if first_bytes.startswith(compressor.prefix):
                return name

    return "not-compressed"


def _buffered_read_file(fobj):
    """Return a buffered version of a read file object."""
    return io.BufferedReader(fobj, buffer_size=_IO_BUFFER_SIZE)


def _buffered_write_file(fobj):
    """Return a buffered version of a write file object."""
    return io.BufferedWriter(fobj, buffer_size=_IO_BUFFER_SIZE)


@contextlib.contextmanager
def _validate_fileobject_and_memmap(fileobj, filename, mmap_mode=None):
    """Utility function opening the right fileobject from a filename.

    The magic number is used to choose between the type of file object to open:
    * regular file object (default)
    * zlib file object
    * gzip file object
    * bz2 file object
    * lzma file object (for xz and lzma compressor)

    Parameters
    ----------
    fileobj: file object
    filename: str
        filename path corresponding to the fileobj parameter.
    mmap_mode: str
        memory map mode that should be used to open the pickle file. This
        parameter is useful to verify that the user is not trying to one with
        compression. Default: None.

    Returns
    -------
        a tuple with a file like object, and the validated mmap_mode.

    """
    # Detect if the fileobj contains compressed data.
    compressor = _detect_compressor(fileobj)
    validated_mmap_mode = mmap_mode

    if compressor == "compat":
        # Compatibility with old pickle mode: simply return the input
        # filename "as-is" and let the compatibility function be called by the
        # caller.
        warnings.warn(
            "The file '%s' has been generated with a joblib "
            "version less than 0.10. "
            "Please regenerate this pickle file." % filename,
            DeprecationWarning,
            stacklevel=2,
        )
        yield filename, validated_mmap_mode
    else:
        if compressor in _COMPRESSORS:
            # based on the compressor detected in the file, we open the
            # correct decompressor file object, wrapped in a buffer.
            compressor_wrapper = _COMPRESSORS[compressor]
            inst = compressor_wrapper.decompressor_file(fileobj)
            fileobj = _buffered_read_file(inst)

        # Checking if incompatible load parameters with the type of file:
        # mmap_mode cannot be used with compressed file or in memory buffers
        # such as io.BytesIO.
        if mmap_mode is not None:
            validated_mmap_mode = None
            if isinstance(fileobj, io.BytesIO):
                warnings.warn(
                    "In memory persistence is not compatible with "
                    'mmap_mode "%(mmap_mode)s" flag passed. '
                    "mmap_mode option will be ignored." % locals(),
                    stacklevel=2,
                )
            elif compressor != "not-compressed":
                warnings.warn(
                    'mmap_mode "%(mmap_mode)s" is not compatible '
                    "with compressed file %(filename)s. "
                    '"%(mmap_mode)s" flag will be ignored.' % locals(),
                    stacklevel=2,
                )
            elif not _is_raw_file(fileobj):
                warnings.warn(
                    '"%(fileobj)r" is not a raw file, mmap_mode '
                    '"%(mmap_mode)s" flag will be ignored.' % locals(),
                    stacklevel=2,
                )
            else:
                validated_mmap_mode = mmap_mode

        yield fileobj, validated_mmap_mode


def _write_fileobject(filename, compress=("zlib", 3)):
    """Return the right compressor file object in write mode."""
    compressmethod = compress[0]
    compresslevel = compress[1]

    if compressmethod in _COMPRESSORS.keys():
        file_instance = _COMPRESSORS[compressmethod].compressor_file(
            filename, compresslevel=compresslevel
        )
        return _buffered_write_file(file_instance)
    else:
        file_instance = _COMPRESSORS["zlib"].compressor_file(
            filename, compresslevel=compresslevel
        )
        return _buffered_write_file(file_instance)


# Utility functions/variables from numpy required for writing arrays.
# We need at least the functions introduced in version 1.9 of numpy. Here,
# we use the ones from numpy 1.10.2.
BUFFER_SIZE = 2**18  # size of buffer for reading npz files in bytes


def _read_bytes(fp, size, error_template="ran out of data"):
    """Read from file-like object until size bytes are read.

    TODO python2_drop: is it still needed? The docstring mentions python 2.6
    and it looks like this can be at least simplified ...

    Raises ValueError if not EOF is encountered before size bytes are read.
    Non-blocking objects only supported if they derive from io objects.

    Required as e.g. ZipExtFile in python 2.6 can return less data than
    requested.

    This function was taken from numpy/lib/format.py in version 1.10.2.

    Parameters
    ----------
    fp: file-like object
    size: int
    error_template: str

    Returns
    -------
    a bytes object
        The data read in bytes.

    """
    data = bytes()
    while True:
        # io files (default in python3) return None or raise on
        # would-block, python2 file will truncate, probably nothing can be
        # done about that.  note that regular files can't be non-blocking
        try:
            r = fp.read(size - len(data))
            data += r
            if len(r) == 0 or len(data) == size:
                break
        except io.BlockingIOError:
            pass
    if len(data) != size:
        msg = "EOF: reading %s, expected %d bytes got %d"
        raise ValueError(msg % (error_template, size, len(data)))
    else:
        return data


def _reconstruct(*args, **kwargs):
    # Wrapper for numpy._core.multiarray._reconstruct with backward compat
    # for numpy 1.X
    #
    # XXX: Remove this function when numpy 1.X is not supported anymore

    np_major_version = np.__version__[:2]
    if np_major_version == "1.":
        from numpy.core.multiarray import _reconstruct as np_reconstruct
    elif np_major_version == "2.":
        from numpy._core.multiarray import _reconstruct as np_reconstruct

    return np_reconstruct(*args, **kwargs)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\maple.py ===
"""
    pygments.lexers.maple
    ~~~~~~~~~~~~~~~~~~~~~

    Lexers for Maple.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import words, bygroups, ExtendedRegexLexer
from pygments.token import Comment, Name, String, Whitespace, Operator, Punctuation, Number, Keyword

__all__ = ['MapleLexer']


class MapleLexer(ExtendedRegexLexer):
    """
    Lexer for Maple.
    """

    name = 'Maple'
    aliases = ['maple']
    filenames = ['*.mpl', '*.mi', '*.mm']
    mimetypes = ['text/x-maple']
    url = 'https://www.maplesoft.com/products/Maple/'
    version_added = '2.19'

    keywords = ('and',
                'assuming',
                'break',
                'by',
                'catch',
                'description',
                'do',
                'done',
                'elif',
                'else',
                'end',
                'error',
                'export',
                'fi',
                'finally',
                'for',
                'from',
                'global',
                'if',
                'implies',
                'in',
                'intersect',
                'local',
                'minus',
                'mod',
                'module',
                'next',
                'not',
                'od',
                'option',
                'options',
                'or',
                'proc',
                'quit',
                'read',
                'return',
                'save',
                'stop',
                'subset',
                'then',
                'to',
                'try',
                'union',
                'use',
                'uses',
                'while',
                'xor')

    builtins = ('abs',
                'add',
                'addressof',
                'anames',
                'and',
                'andmap',
                'andseq',
                'appendto',
                'Array',
                'array',
                'ArrayOptions',
                'assemble',
                'ASSERT',
                'assign',
                'assigned',
                'attributes',
                'cat',
                'ceil',
                'coeff',
                'coeffs',
                'conjugate',
                'convert',
                'CopySign',
                'DEBUG',
                'debugopts',
                'Default0',
                'DefaultOverflow',
                'DefaultUnderflow',
                'degree',
                'denom',
                'diff',
                'disassemble',
                'divide',
                'done',
                'entries',
                'EqualEntries',
                'eval',
                'evalb',
                'evalf',
                'evalhf',
                'evalindets',
                'evaln',
                'expand',
                'exports',
                'factorial',
                'floor',
                'frac',
                'frem',
                'FromInert',
                'frontend',
                'gc',
                'genpoly',
                'has',
                'hastype',
                'hfarray',
                'icontent',
                'igcd',
                'ilcm',
                'ilog10',
                'Im',
                'implies',
                'indets',
                'indices',
                'intersect',
                'iolib',
                'iquo',
                'irem',
                'iroot',
                'iroot',
                'isqrt',
                'kernelopts',
                'lcoeff',
                'ldegree',
                'length',
                'lexorder',
                'lhs',
                'lowerbound',
                'lprint',
                'macro',
                'map',
                'max',
                'maxnorm',
                'member',
                'membertype',
                'min',
                'minus',
                'mod',
                'modp',
                'modp1',
                'modp2',
                'mods',
                'mul',
                'NextAfter',
                'nops',
                'normal',
                'not',
                'numboccur',
                'numelems',
                'numer',
                'NumericClass',
                'NumericEvent',
                'NumericEventHandler',
                'NumericStatus',
                'op',
                'or',
                'order',
                'OrderedNE',
                'ormap',
                'orseq',
                'parse',
                'piecewise',
                'pointto',
                'print',
                'quit',
                'Re',
                'readlib',
                'Record',
                'remove',
                'rhs',
                'round',
                'rtable',
                'rtable_elems',
                'rtable_eval',
                'rtable_indfns',
                'rtable_num_elems',
                'rtable_options',
                'rtable_redim',
                'rtable_scanblock',
                'rtable_set_indfn',
                'rtable_split_unit',
                'savelib',
                'Scale10',
                'Scale2',
                'SDMPolynom',
                'searchtext',
                'SearchText',
                'select',
                'selectremove',
                'seq',
                'series',
                'setattribute',
                'SFloatExponent',
                'SFloatMantissa',
                'sign',
                'sort',
                'ssystem',
                'stop',
                'String',
                'subs',
                'subset',
                'subsindets',
                'subsop',
                'substring',
                'system',
                'table',
                'taylor',
                'tcoeff',
                'time',
                'timelimit',
                'ToInert',
                'traperror',
                'trunc',
                'type',
                'typematch',
                'unames',
                'unassign',
                'union',
                'Unordered',
                'upperbound',
                'userinfo',
                'writeto',
                'xor',
                'xormap',
                'xorseq')

    def delayed_callback(self, match, ctx):
        yield match.start(1), Punctuation, match.group(1)  # quote

        ctx.pos = match.start(2)
        orig_end = ctx.end
        ctx.end = match.end(2)

        yield from self.get_tokens_unprocessed(context=ctx)
        yield match.end(2), Punctuation, match.group(1)  # quote

        ctx.pos = match.end()
        ctx.end = orig_end

    tokens = {
        'root': [
            (r'#.*\n', Comment.Single),
            (r'\(\*', Comment.Multiline, 'comment'),
            (r'"(\\.|.|\s)*?"', String),
            (r"('+)((.|\n)*?)\1", delayed_callback),
            (r'`(\\`|.)*?`', Name),
            (words(keywords, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(builtins, prefix=r'\b', suffix=r'\b'), Name.Builtin),
            (r'[a-zA-Z_][a-zA-Z0-9_]*', Name),
            (r'(:=|\*\*|@@|<=|>=|<>|->|::|\.\.|&\+|[\+\-\*\.\^\$/@&,:=<>%~])', Operator),
            (r'[;^!@$\(\)\[\]{}|_\\#?]+', Punctuation),
            (r'(\d+)(\.\.)', bygroups(Number.Integer, Punctuation)),
            (r'(\d*\.\d+|\d+\.\d*)([eE][+-]?\d+)?', Number.Float),
            (r'\d+', Number.Integer),
            (r'\s+', Whitespace),
        ],
        'comment': [
            (r'.*\(\*', Comment.Multiline, '#push'),
            (r'.*\*\)', Comment.Multiline, '#pop'),
            (r'.*\n', Comment.Multiline),
        ]
    }

    def analyse_text(text):
        if ':=' in text:
            return 0.1

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\scintilla\configui.py ===
import win32api
import win32con
import win32ui
from pywin.mfc import dialog

# Used to indicate that style should use default color
from win32con import CLR_INVALID

from . import scintillacon

######################################################
# Property Page for syntax formatting options

# The standard 16 color VGA palette should always be possible
paletteVGA = (
    ("Black", win32api.RGB(0, 0, 0)),
    ("Navy", win32api.RGB(0, 0, 128)),
    ("Green", win32api.RGB(0, 128, 0)),
    ("Cyan", win32api.RGB(0, 128, 128)),
    ("Maroon", win32api.RGB(128, 0, 0)),
    ("Purple", win32api.RGB(128, 0, 128)),
    ("Olive", win32api.RGB(128, 128, 0)),
    ("Gray", win32api.RGB(128, 128, 128)),
    ("Silver", win32api.RGB(192, 192, 192)),
    ("Blue", win32api.RGB(0, 0, 255)),
    ("Lime", win32api.RGB(0, 255, 0)),
    ("Aqua", win32api.RGB(0, 255, 255)),
    ("Red", win32api.RGB(255, 0, 0)),
    ("Fuchsia", win32api.RGB(255, 0, 255)),
    ("Yellow", win32api.RGB(255, 255, 0)),
    ("White", win32api.RGB(255, 255, 255)),
    # and a few others will generally be possible.
    ("DarkGrey", win32api.RGB(64, 64, 64)),
    ("PurpleBlue", win32api.RGB(64, 64, 192)),
    ("DarkGreen", win32api.RGB(0, 96, 0)),
    ("DarkOlive", win32api.RGB(128, 128, 64)),
    ("MediumBlue", win32api.RGB(0, 0, 192)),
    ("DarkNavy", win32api.RGB(0, 0, 96)),
    ("Magenta", win32api.RGB(96, 0, 96)),
    ("OffWhite", win32api.RGB(255, 255, 220)),
    ("LightPurple", win32api.RGB(220, 220, 255)),
    ("<Default>", win32con.CLR_INVALID),
)


class ScintillaFormatPropertyPage(dialog.PropertyPage):
    def __init__(self, scintillaClass=None, caption=0):
        self.scintillaClass = scintillaClass
        dialog.PropertyPage.__init__(self, win32ui.IDD_PP_FORMAT, caption=caption)

    def OnInitDialog(self):
        try:
            if self.scintillaClass is None:
                from . import control

                sc = control.CScintillaEdit
            else:
                sc = self.scintillaClass

            self.scintilla = sc()
            style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.ES_MULTILINE
            # Convert the rect size
            rect = self.MapDialogRect((5, 5, 120, 75))
            self.scintilla.CreateWindow(style, rect, self, 111)
            self.HookNotify(self.OnBraceMatch, scintillacon.SCN_UPDATEUI)
            self.scintilla.HookKeyStroke(self.OnEsc, 27)
            self.scintilla.SCISetViewWS(1)
            self.pos_bstart = self.pos_bend = self.pos_bbad = 0

            colorizer = self.scintilla._GetColorizer()
            text = colorizer.GetSampleText()
            items = text.split("|", 2)
            pos = len(items[0])
            self.scintilla.SCIAddText("".join(items))
            self.scintilla.SetSel(pos, pos)
            self.scintilla.ApplyFormattingStyles()
            self.styles = self.scintilla._GetColorizer().styles

            self.cbo = self.GetDlgItem(win32ui.IDC_COMBO1)
            for c in paletteVGA:
                self.cbo.AddString(c[0])

            self.cboBoldItalic = self.GetDlgItem(win32ui.IDC_COMBO2)
            for item in ("Bold Italic", "Bold", "Italic", "Regular"):
                self.cboBoldItalic.InsertString(0, item)

            self.butIsDefault = self.GetDlgItem(win32ui.IDC_CHECK1)
            self.butIsDefaultBackground = self.GetDlgItem(win32ui.IDC_CHECK2)
            self.listbox = self.GetDlgItem(win32ui.IDC_LIST1)
            self.HookCommand(self.OnListCommand, win32ui.IDC_LIST1)
            names = sorted(self.styles)
            for name in names:
                if self.styles[name].aliased is None:
                    self.listbox.AddString(name)
            self.listbox.SetCurSel(0)

            idc = win32ui.IDC_RADIO1
            if not self.scintilla._GetColorizer().bUseFixed:
                idc = win32ui.IDC_RADIO2
            self.GetDlgItem(idc).SetCheck(1)
            self.UpdateUIForStyle(self.styles[names[0]])

            self.scintilla.HookFormatter(self)
            self.HookCommand(self.OnButDefaultFixedFont, win32ui.IDC_BUTTON1)
            self.HookCommand(self.OnButDefaultPropFont, win32ui.IDC_BUTTON2)
            self.HookCommand(self.OnButThisFont, win32ui.IDC_BUTTON3)
            self.HookCommand(self.OnButUseDefaultFont, win32ui.IDC_CHECK1)
            self.HookCommand(self.OnButThisBackground, win32ui.IDC_BUTTON4)
            self.HookCommand(self.OnButUseDefaultBackground, win32ui.IDC_CHECK2)
            self.HookCommand(self.OnStyleUIChanged, win32ui.IDC_COMBO1)
            self.HookCommand(self.OnStyleUIChanged, win32ui.IDC_COMBO2)
            self.HookCommand(self.OnButFixedOrDefault, win32ui.IDC_RADIO1)
            self.HookCommand(self.OnButFixedOrDefault, win32ui.IDC_RADIO2)
        except:
            import traceback

            traceback.print_exc()

    def OnEsc(self, ch):
        self.GetParent().EndDialog(win32con.IDCANCEL)

    def OnBraceMatch(self, std, extra):
        import pywin.scintilla.view

        pywin.scintilla.view.DoBraceMatch(self.scintilla)

    def GetSelectedStyle(self):
        return self.styles[self.listbox.GetText(self.listbox.GetCurSel())]

    def _DoButDefaultFont(self, extra_flags, attr):
        baseFormat = getattr(self.scintilla._GetColorizer(), attr)
        flags = (
            extra_flags
            | win32con.CF_SCREENFONTS
            | win32con.CF_EFFECTS
            | win32con.CF_FORCEFONTEXIST
        )
        d = win32ui.CreateFontDialog(baseFormat, flags, None, self)
        if d.DoModal() == win32con.IDOK:
            setattr(self.scintilla._GetColorizer(), attr, d.GetCharFormat())
            self.OnStyleUIChanged(0, win32con.BN_CLICKED)

    def OnButDefaultFixedFont(self, id, code):
        if code == win32con.BN_CLICKED:
            self._DoButDefaultFont(win32con.CF_FIXEDPITCHONLY, "baseFormatFixed")
            return 1

    def OnButDefaultPropFont(self, id, code):
        if code == win32con.BN_CLICKED:
            self._DoButDefaultFont(win32con.CF_SCALABLEONLY, "baseFormatProp")
            return 1

    def OnButFixedOrDefault(self, id, code):
        if code == win32con.BN_CLICKED:
            bUseFixed = id == win32ui.IDC_RADIO1
            self.GetDlgItem(win32ui.IDC_RADIO1).GetCheck() != 0
            self.scintilla._GetColorizer().bUseFixed = bUseFixed
            self.scintilla.ApplyFormattingStyles(0)
            return 1

    def OnButThisFont(self, id, code):
        if code == win32con.BN_CLICKED:
            flags = (
                win32con.CF_SCREENFONTS
                | win32con.CF_EFFECTS
                | win32con.CF_FORCEFONTEXIST
            )
            style = self.GetSelectedStyle()
            # If the selected style is based on the default, we need to apply
            # the default to it.
            def_format = self.scintilla._GetColorizer().GetDefaultFormat()
            format = style.GetCompleteFormat(def_format)
            d = win32ui.CreateFontDialog(format, flags, None, self)
            if d.DoModal() == win32con.IDOK:
                style.format = d.GetCharFormat()
                self.scintilla.ApplyFormattingStyles(0)
            return 1

    def OnButUseDefaultFont(self, id, code):
        if code == win32con.BN_CLICKED:
            isDef = self.butIsDefault.GetCheck()
            self.GetDlgItem(win32ui.IDC_BUTTON3).EnableWindow(not isDef)
            if isDef:  # Being reset to the default font.
                style = self.GetSelectedStyle()
                style.ForceAgainstDefault()
                self.UpdateUIForStyle(style)
                self.scintilla.ApplyFormattingStyles(0)
            else:
                # User wants to override default -
                # do nothing!
                pass

    def OnButThisBackground(self, id, code):
        if code == win32con.BN_CLICKED:
            style = self.GetSelectedStyle()
            bg = win32api.RGB(0xFF, 0xFF, 0xFF)
            if style.background != CLR_INVALID:
                bg = style.background
            d = win32ui.CreateColorDialog(bg, 0, self)
            if d.DoModal() == win32con.IDOK:
                style.background = d.GetColor()
                self.scintilla.ApplyFormattingStyles(0)
            return 1

    def OnButUseDefaultBackground(self, id, code):
        if code == win32con.BN_CLICKED:
            isDef = self.butIsDefaultBackground.GetCheck()
            self.GetDlgItem(win32ui.IDC_BUTTON4).EnableWindow(not isDef)
            if isDef:  # Being reset to the default color
                style = self.GetSelectedStyle()
                style.background = style.default_background
                self.UpdateUIForStyle(style)
                self.scintilla.ApplyFormattingStyles(0)
            else:
                # User wants to override default -
                # do nothing!
                pass

    def OnListCommand(self, id, code):
        if code == win32con.LBN_SELCHANGE:
            style = self.GetSelectedStyle()
            self.UpdateUIForStyle(style)
        return 1

    def UpdateUIForStyle(self, style):
        format = style.format
        sel = 0
        for c in paletteVGA:
            if format[4] == c[1]:
                # print("Style", style.name, "is", c[0])
                break
            sel += 1
        else:
            sel = -1
        self.cbo.SetCurSel(sel)
        self.butIsDefault.SetCheck(style.IsBasedOnDefault())
        self.GetDlgItem(win32ui.IDC_BUTTON3).EnableWindow(not style.IsBasedOnDefault())

        self.butIsDefaultBackground.SetCheck(
            style.background == style.default_background
        )
        self.GetDlgItem(win32ui.IDC_BUTTON4).EnableWindow(
            style.background != style.default_background
        )

        bold = format[1] & win32con.CFE_BOLD != 0
        italic = format[1] & win32con.CFE_ITALIC != 0
        self.cboBoldItalic.SetCurSel(bold * 2 + italic)

    def OnStyleUIChanged(self, id, code):
        if code in [win32con.BN_CLICKED, win32con.CBN_SELCHANGE]:
            style = self.GetSelectedStyle()
            self.ApplyUIFormatToStyle(style)
            self.scintilla.ApplyFormattingStyles(0)
            return 0
        return 1

    def ApplyUIFormatToStyle(self, style):
        format = style.format
        color = paletteVGA[self.cbo.GetCurSel()]
        effect = 0
        sel = self.cboBoldItalic.GetCurSel()
        if sel == 0:
            effect = 0
        elif sel == 1:
            effect = win32con.CFE_ITALIC
        elif sel == 2:
            effect = win32con.CFE_BOLD
        else:
            effect = win32con.CFE_BOLD | win32con.CFE_ITALIC
        maskFlags = (
            format[0] | win32con.CFM_COLOR | win32con.CFM_BOLD | win32con.CFM_ITALIC
        )
        style.format = (
            maskFlags,
            effect,
            style.format[2],
            style.format[3],
            color[1],
        ) + style.format[5:]

    def OnOK(self):
        self.scintilla._GetColorizer().SavePreferences()
        return 1


def test():
    page = ScintillaFormatPropertyPage()
    sheet = dialog.PropertySheet("Test")
    sheet.AddPage(page)
    sheet.CreateWindow()

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_unix_pipes.py ===
from __future__ import annotations

import errno
import os
import select
import sys
from typing import TYPE_CHECKING

import pytest

from .. import _core
from .._core._tests.tutil import gc_collect_harder, skip_if_fbsd_pipes_broken
from ..testing import check_one_way_stream, wait_all_tasks_blocked

if TYPE_CHECKING:
    from .._file_io import _HasFileNo

posix = os.name == "posix"
pytestmark = pytest.mark.skipif(not posix, reason="posix only")

assert not TYPE_CHECKING or sys.platform == "unix"

if posix:
    from .._unix_pipes import FdStream
else:
    with pytest.raises(ImportError):
        from .._unix_pipes import FdStream


async def make_pipe() -> tuple[FdStream, FdStream]:
    """Makes a new pair of pipes."""
    (r, w) = os.pipe()
    return FdStream(w), FdStream(r)


async def make_clogged_pipe() -> tuple[FdStream, FdStream]:
    s, r = await make_pipe()
    try:
        while True:
            # We want to totally fill up the pipe buffer.
            # This requires working around a weird feature that POSIX pipes
            # have.
            # If you do a write of <= PIPE_BUF bytes, then it's guaranteed
            # to either complete entirely, or not at all. So if we tried to
            # write PIPE_BUF bytes, and the buffer's free space is only
            # PIPE_BUF/2, then the write will raise BlockingIOError... even
            # though a smaller write could still succeed! To avoid this,
            # make sure to write >PIPE_BUF bytes each time, which disables
            # the special behavior.
            # For details, search for PIPE_BUF here:
            #   http://pubs.opengroup.org/onlinepubs/9699919799/functions/write.html

            # for the getattr:
            # https://bitbucket.org/pypy/pypy/issues/2876/selectpipe_buf-is-missing-on-pypy3
            buf_size = getattr(select, "PIPE_BUF", 8192)
            os.write(s.fileno(), b"x" * buf_size * 2)
    except BlockingIOError:
        pass
    return s, r


async def test_send_pipe() -> None:
    r, w = os.pipe()
    async with FdStream(w) as send:
        assert send.fileno() == w
        await send.send_all(b"123")
        assert (os.read(r, 8)) == b"123"

        os.close(r)


async def test_receive_pipe() -> None:
    r, w = os.pipe()
    async with FdStream(r) as recv:
        assert (recv.fileno()) == r
        os.write(w, b"123")
        assert (await recv.receive_some(8)) == b"123"

        os.close(w)


async def test_pipes_combined() -> None:
    write, read = await make_pipe()
    count = 2**20

    async def sender() -> None:
        big = bytearray(count)
        await write.send_all(big)

    async def reader() -> None:
        await wait_all_tasks_blocked()
        received = 0
        while received < count:
            received += len(await read.receive_some(4096))

        assert received == count

    async with _core.open_nursery() as n:
        n.start_soon(sender)
        n.start_soon(reader)

    await read.aclose()
    await write.aclose()


async def test_pipe_errors() -> None:
    with pytest.raises(TypeError):
        FdStream(None)

    r, w = os.pipe()
    os.close(w)
    async with FdStream(r) as s:
        with pytest.raises(ValueError, match=r"^max_bytes must be integer >= 1$"):
            await s.receive_some(0)


async def test_del() -> None:
    w, r = await make_pipe()
    f1, f2 = w.fileno(), r.fileno()
    del w, r
    gc_collect_harder()

    with pytest.raises(OSError, match=r"Bad file descriptor$") as excinfo:
        os.close(f1)
    assert excinfo.value.errno == errno.EBADF

    with pytest.raises(OSError, match=r"Bad file descriptor$") as excinfo:
        os.close(f2)
    assert excinfo.value.errno == errno.EBADF


async def test_async_with() -> None:
    w, r = await make_pipe()
    async with w, r:
        pass

    assert w.fileno() == -1
    assert r.fileno() == -1

    with pytest.raises(OSError, match=r"Bad file descriptor$") as excinfo:
        os.close(w.fileno())
    assert excinfo.value.errno == errno.EBADF

    with pytest.raises(OSError, match=r"Bad file descriptor$") as excinfo:
        os.close(r.fileno())
    assert excinfo.value.errno == errno.EBADF


async def test_misdirected_aclose_regression() -> None:
    # https://github.com/python-trio/trio/issues/661#issuecomment-456582356
    w, r = await make_pipe()
    old_r_fd = r.fileno()

    # Close the original objects
    await w.aclose()
    await r.aclose()

    # Do a little dance to get a new pipe whose receive handle matches the old
    # receive handle.
    r2_fd, w2_fd = os.pipe()
    if r2_fd != old_r_fd:  # pragma: no cover
        os.dup2(r2_fd, old_r_fd)
        os.close(r2_fd)
    async with FdStream(old_r_fd) as r2:
        assert r2.fileno() == old_r_fd

        # And now set up a background task that's working on the new receive
        # handle
        async def expect_eof() -> None:
            assert await r2.receive_some(10) == b""

        async with _core.open_nursery() as nursery:
            nursery.start_soon(expect_eof)
            await wait_all_tasks_blocked()

            # Here's the key test: does calling aclose() again on the *old*
            # handle, cause the task blocked on the *new* handle to raise
            # ClosedResourceError?
            await r.aclose()
            await wait_all_tasks_blocked()

            # Guess we survived! Close the new write handle so that the task
            # gets an EOF and can exit cleanly.
            os.close(w2_fd)


async def test_close_at_bad_time_for_receive_some(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # We used to have race conditions where if one task was using the pipe,
    # and another closed it at *just* the wrong moment, it would give an
    # unexpected error instead of ClosedResourceError:
    # https://github.com/python-trio/trio/issues/661
    #
    # This tests what happens if the pipe gets closed in the moment *between*
    # when receive_some wakes up, and when it tries to call os.read
    async def expect_closedresourceerror() -> None:
        with pytest.raises(_core.ClosedResourceError):
            await r.receive_some(10)

    orig_wait_readable = _core._run.TheIOManager.wait_readable

    async def patched_wait_readable(
        self: _core._run.TheIOManager,
        fd: int | _HasFileNo,
    ) -> None:
        await orig_wait_readable(self, fd)
        await r.aclose()

    monkeypatch.setattr(_core._run.TheIOManager, "wait_readable", patched_wait_readable)
    s, r = await make_pipe()
    async with s, r:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(expect_closedresourceerror)
            await wait_all_tasks_blocked()
            # Trigger everything by waking up the receiver
            await s.send_all(b"x")


async def test_close_at_bad_time_for_send_all(monkeypatch: pytest.MonkeyPatch) -> None:
    # We used to have race conditions where if one task was using the pipe,
    # and another closed it at *just* the wrong moment, it would give an
    # unexpected error instead of ClosedResourceError:
    # https://github.com/python-trio/trio/issues/661
    #
    # This tests what happens if the pipe gets closed in the moment *between*
    # when send_all wakes up, and when it tries to call os.write
    async def expect_closedresourceerror() -> None:
        with pytest.raises(_core.ClosedResourceError):
            await s.send_all(b"x" * 100)

    orig_wait_writable = _core._run.TheIOManager.wait_writable

    async def patched_wait_writable(
        self: _core._run.TheIOManager,
        fd: int | _HasFileNo,
    ) -> None:
        await orig_wait_writable(self, fd)
        await s.aclose()

    monkeypatch.setattr(_core._run.TheIOManager, "wait_writable", patched_wait_writable)
    s, r = await make_clogged_pipe()
    async with s, r:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(expect_closedresourceerror)
            await wait_all_tasks_blocked()
            # Trigger everything by waking up the sender. On ppc64el, PIPE_BUF
            # is 8192 but make_clogged_pipe() ends up writing a total of
            # 1048576 bytes before the pipe is full, and then a subsequent
            # receive_some(10000) isn't sufficient for orig_wait_writable() to
            # return for our subsequent aclose() call. It's necessary to empty
            # the pipe further before this happens. So we loop here until the
            # pipe is empty to make sure that the sender wakes up even in this
            # case. Otherwise patched_wait_writable() never gets to the
            # aclose(), so expect_closedresourceerror() never returns, the
            # nursery never finishes all tasks and this test hangs.
            received_data = await r.receive_some(10000)
            while received_data:
                received_data = await r.receive_some(10000)


# On FreeBSD, directories are readable, and we haven't found any other trick
# for making an unreadable fd, so there's no way to run this test. Fortunately
# the logic this is testing doesn't depend on the platform, so testing on
# other platforms is probably good enough.
@pytest.mark.skipif(
    sys.platform.startswith("freebsd"),
    reason="no way to make read() return a bizarro error on FreeBSD",
)
async def test_bizarro_OSError_from_receive() -> None:
    # Make sure that if the read syscall returns some bizarro error, then we
    # get a BrokenResourceError. This is incredibly unlikely; there's almost
    # no way to trigger a failure here intentionally (except for EBADF, but we
    # exploit that to detect file closure, so it takes a different path). So
    # we set up a strange scenario where the pipe fd somehow transmutes into a
    # directory fd, causing os.read to raise IsADirectoryError (yes, that's a
    # real built-in exception type).
    s, r = await make_pipe()
    async with s, r:
        dir_fd = os.open("/", os.O_DIRECTORY, 0)
        try:
            os.dup2(dir_fd, r.fileno())
            with pytest.raises(_core.BrokenResourceError):
                await r.receive_some(10)
        finally:
            os.close(dir_fd)


@skip_if_fbsd_pipes_broken
async def test_pipe_fully() -> None:
    await check_one_way_stream(make_pipe, make_clogged_pipe)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\cache.py ===
"""Cache Management
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pip._vendor.packaging.tags import Tag, interpreter_name, interpreter_version
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.exceptions import InvalidWheelFilename
from pip._internal.models.direct_url import DirectUrl
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds
from pip._internal.utils.urls import path_to_url

logger = logging.getLogger(__name__)

ORIGIN_JSON_NAME = "origin.json"


def _hash_dict(d: Dict[str, str]) -> str:
    """Return a stable sha224 of a dictionary."""
    s = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha224(s.encode("ascii")).hexdigest()


class Cache:
    """An abstract class - provides cache directories for data from links

    :param cache_dir: The root of the cache.
    """

    def __init__(self, cache_dir: str) -> None:
        super().__init__()
        assert not cache_dir or os.path.isabs(cache_dir)
        self.cache_dir = cache_dir or None

    def _get_cache_path_parts(self, link: Link) -> List[str]:
        """Get parts of part that must be os.path.joined with cache_dir"""

        # We want to generate an url to use as our cache key, we don't want to
        # just reuse the URL because it might have other items in the fragment
        # and we don't care about those.
        key_parts = {"url": link.url_without_fragment}
        if link.hash_name is not None and link.hash is not None:
            key_parts[link.hash_name] = link.hash
        if link.subdirectory_fragment:
            key_parts["subdirectory"] = link.subdirectory_fragment

        # Include interpreter name, major and minor version in cache key
        # to cope with ill-behaved sdists that build a different wheel
        # depending on the python version their setup.py is being run on,
        # and don't encode the difference in compatibility tags.
        # https://github.com/pypa/pip/issues/7296
        key_parts["interpreter_name"] = interpreter_name()
        key_parts["interpreter_version"] = interpreter_version()

        # Encode our key url with sha224, we'll use this because it has similar
        # security properties to sha256, but with a shorter total output (and
        # thus less secure). However the differences don't make a lot of
        # difference for our use case here.
        hashed = _hash_dict(key_parts)

        # We want to nest the directories some to prevent having a ton of top
        # level directories where we might run out of sub directories on some
        # FS.
        parts = [hashed[:2], hashed[2:4], hashed[4:6], hashed[6:]]

        return parts

    def _get_candidates(self, link: Link, canonical_package_name: str) -> List[Any]:
        can_not_cache = not self.cache_dir or not canonical_package_name or not link
        if can_not_cache:
            return []

        path = self.get_path_for_link(link)
        if os.path.isdir(path):
            return [(candidate, path) for candidate in os.listdir(path)]
        return []

    def get_path_for_link(self, link: Link) -> str:
        """Return a directory to store cached items in for link."""
        raise NotImplementedError()

    def get(
        self,
        link: Link,
        package_name: Optional[str],
        supported_tags: List[Tag],
    ) -> Link:
        """Returns a link to a cached item if it exists, otherwise returns the
        passed link.
        """
        raise NotImplementedError()


class SimpleWheelCache(Cache):
    """A cache of wheels for future installs."""

    def __init__(self, cache_dir: str) -> None:
        super().__init__(cache_dir)

    def get_path_for_link(self, link: Link) -> str:
        """Return a directory to store cached wheels for link

        Because there are M wheels for any one sdist, we provide a directory
        to cache them in, and then consult that directory when looking up
        cache hits.

        We only insert things into the cache if they have plausible version
        numbers, so that we don't contaminate the cache with things that were
        not unique. E.g. ./package might have dozens of installs done for it
        and build a version of 0.0...and if we built and cached a wheel, we'd
        end up using the same wheel even if the source has been edited.

        :param link: The link of the sdist for which this will cache wheels.
        """
        parts = self._get_cache_path_parts(link)
        assert self.cache_dir
        # Store wheels within the root cache_dir
        return os.path.join(self.cache_dir, "wheels", *parts)

    def get(
        self,
        link: Link,
        package_name: Optional[str],
        supported_tags: List[Tag],
    ) -> Link:
        candidates = []

        if not package_name:
            return link

        canonical_package_name = canonicalize_name(package_name)
        for wheel_name, wheel_dir in self._get_candidates(link, canonical_package_name):
            try:
                wheel = Wheel(wheel_name)
            except InvalidWheelFilename:
                continue
            if canonicalize_name(wheel.name) != canonical_package_name:
                logger.debug(
                    "Ignoring cached wheel %s for %s as it "
                    "does not match the expected distribution name %s.",
                    wheel_name,
                    link,
                    package_name,
                )
                continue
            if not wheel.supported(supported_tags):
                # Built for a different python/arch/etc
                continue
            candidates.append(
                (
                    wheel.support_index_min(supported_tags),
                    wheel_name,
                    wheel_dir,
                )
            )

        if not candidates:
            return link

        _, wheel_name, wheel_dir = min(candidates)
        return Link(path_to_url(os.path.join(wheel_dir, wheel_name)))


class EphemWheelCache(SimpleWheelCache):
    """A SimpleWheelCache that creates it's own temporary cache directory"""

    def __init__(self) -> None:
        self._temp_dir = TempDirectory(
            kind=tempdir_kinds.EPHEM_WHEEL_CACHE,
            globally_managed=True,
        )

        super().__init__(self._temp_dir.path)


class CacheEntry:
    def __init__(
        self,
        link: Link,
        persistent: bool,
    ):
        self.link = link
        self.persistent = persistent
        self.origin: Optional[DirectUrl] = None
        origin_direct_url_path = Path(self.link.file_path).parent / ORIGIN_JSON_NAME
        if origin_direct_url_path.exists():
            try:
                self.origin = DirectUrl.from_json(
                    origin_direct_url_path.read_text(encoding="utf-8")
                )
            except Exception as e:
                logger.warning(
                    "Ignoring invalid cache entry origin file %s for %s (%s)",
                    origin_direct_url_path,
                    link.filename,
                    e,
                )


class WheelCache(Cache):
    """Wraps EphemWheelCache and SimpleWheelCache into a single Cache

    This Cache allows for gracefully degradation, using the ephem wheel cache
    when a certain link is not found in the simple wheel cache first.
    """

    def __init__(self, cache_dir: str) -> None:
        super().__init__(cache_dir)
        self._wheel_cache = SimpleWheelCache(cache_dir)
        self._ephem_cache = EphemWheelCache()

    def get_path_for_link(self, link: Link) -> str:
        return self._wheel_cache.get_path_for_link(link)

    def get_ephem_path_for_link(self, link: Link) -> str:
        return self._ephem_cache.get_path_for_link(link)

    def get(
        self,
        link: Link,
        package_name: Optional[str],
        supported_tags: List[Tag],
    ) -> Link:
        cache_entry = self.get_cache_entry(link, package_name, supported_tags)
        if cache_entry is None:
            return link
        return cache_entry.link

    def get_cache_entry(
        self,
        link: Link,
        package_name: Optional[str],
        supported_tags: List[Tag],
    ) -> Optional[CacheEntry]:
        """Returns a CacheEntry with a link to a cached item if it exists or
        None. The cache entry indicates if the item was found in the persistent
        or ephemeral cache.
        """
        retval = self._wheel_cache.get(
            link=link,
            package_name=package_name,
            supported_tags=supported_tags,
        )
        if retval is not link:
            return CacheEntry(retval, persistent=True)

        retval = self._ephem_cache.get(
            link=link,
            package_name=package_name,
            supported_tags=supported_tags,
        )
        if retval is not link:
            return CacheEntry(retval, persistent=False)

        return None

    @staticmethod
    def record_download_origin(cache_dir: str, download_info: DirectUrl) -> None:
        origin_path = Path(cache_dir) / ORIGIN_JSON_NAME
        if origin_path.exists():
            try:
                origin = DirectUrl.from_json(origin_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(
                    "Could not read origin file %s in cache entry (%s). "
                    "Will attempt to overwrite it.",
                    origin_path,
                    e,
                )
            else:
                # TODO: use DirectUrl.equivalent when
                # https://github.com/pypa/pip/pull/10564 is merged.
                if origin.url != download_info.url:
                    logger.warning(
                        "Origin URL %s in cache entry %s does not match download URL "
                        "%s. This is likely a pip bug or a cache corruption issue. "
                        "Will overwrite it with the new value.",
                        origin.url,
                        cache_dir,
                        download_info.url,
                    )
        origin_path.write_text(download_info.to_json(), encoding="utf-8")

# === NexusCore/openenv\Lib\site-packages\html2text\utils.py ===
import html.entities
from typing import Dict, List, Optional

from . import config

unifiable_n = {
    html.entities.name2codepoint[k]: v
    for k, v in config.UNIFIABLE.items()
    if k != "nbsp"
}


def hn(tag: str) -> int:
    if tag[0] == "h" and len(tag) == 2:
        n = tag[1]
        if "0" < n <= "9":
            return int(n)
    return 0


def dumb_property_dict(style: str) -> Dict[str, str]:
    """
    :returns: A hash of css attributes
    """
    return {
        x.strip().lower(): y.strip().lower()
        for x, y in [z.split(":", 1) for z in style.split(";") if ":" in z]
    }


def dumb_css_parser(data: str) -> Dict[str, Dict[str, str]]:
    """
    :type data: str

    :returns: A hash of css selectors, each of which contains a hash of
    css attributes.
    :rtype: dict
    """
    # remove @import sentences
    data += ";"
    importIndex = data.find("@import")
    while importIndex != -1:
        data = data[0:importIndex] + data[data.find(";", importIndex) + 1 :]
        importIndex = data.find("@import")

    # parse the css. reverted from dictionary comprehension in order to
    # support older pythons
    pairs = [x.split("{") for x in data.split("}") if "{" in x.strip()]
    try:
        elements = {a.strip(): dumb_property_dict(b) for a, b in pairs}
    except ValueError:
        elements = {}  # not that important

    return elements


def element_style(
    attrs: Dict[str, Optional[str]],
    style_def: Dict[str, Dict[str, str]],
    parent_style: Dict[str, str],
) -> Dict[str, str]:
    """
    :type attrs: dict
    :type style_def: dict
    :type style_def: dict

    :returns: A hash of the 'final' style attributes of the element
    :rtype: dict
    """
    style = parent_style.copy()
    if "class" in attrs:
        assert attrs["class"] is not None
        for css_class in attrs["class"].split():
            css_style = style_def.get("." + css_class, {})
            style.update(css_style)
    if "style" in attrs:
        assert attrs["style"] is not None
        immediate_style = dumb_property_dict(attrs["style"])
        style.update(immediate_style)

    return style


def google_list_style(style: Dict[str, str]) -> str:
    """
    Finds out whether this is an ordered or unordered list

    :type style: dict

    :rtype: str
    """
    if "list-style-type" in style:
        list_style = style["list-style-type"]
        if list_style in ["disc", "circle", "square", "none"]:
            return "ul"

    return "ol"


def google_has_height(style: Dict[str, str]) -> bool:
    """
    Check if the style of the element has the 'height' attribute
    explicitly defined

    :type style: dict

    :rtype: bool
    """
    return "height" in style


def google_text_emphasis(style: Dict[str, str]) -> List[str]:
    """
    :type style: dict

    :returns: A list of all emphasis modifiers of the element
    :rtype: list
    """
    emphasis = []
    if "text-decoration" in style:
        emphasis.append(style["text-decoration"])
    if "font-style" in style:
        emphasis.append(style["font-style"])
    if "font-weight" in style:
        emphasis.append(style["font-weight"])

    return emphasis


def google_fixed_width_font(style: Dict[str, str]) -> bool:
    """
    Check if the css of the current element defines a fixed width font

    :type style: dict

    :rtype: bool
    """
    font_family = ""
    if "font-family" in style:
        font_family = style["font-family"]
    return "courier new" == font_family or "consolas" == font_family


def list_numbering_start(attrs: Dict[str, Optional[str]]) -> int:
    """
    Extract numbering from list element attributes

    :type attrs: dict

    :rtype: int or None
    """
    if "start" in attrs:
        assert attrs["start"] is not None
        try:
            return int(attrs["start"]) - 1
        except ValueError:
            pass

    return 0


def skipwrap(
    para: str, wrap_links: bool, wrap_list_items: bool, wrap_tables: bool
) -> bool:
    # If it appears to contain a link
    # don't wrap
    if not wrap_links and config.RE_LINK.search(para):
        return True
    # If the text begins with four spaces or one tab, it's a code block;
    # don't wrap
    if para[0:4] == "    " or para[0] == "\t":
        return True

    # If the text begins with only two "--", possibly preceded by
    # whitespace, that's an emdash; so wrap.
    stripped = para.lstrip()
    if stripped[0:2] == "--" and len(stripped) > 2 and stripped[2] != "-":
        return False

    # I'm not sure what this is for; I thought it was to detect lists,
    # but there's a <br>-inside-<span> case in one of the tests that
    # also depends upon it.
    if stripped[0:1] in ("-", "*") and not stripped[0:2] == "**":
        return not wrap_list_items

    # If text contains a pipe character it is likely a table
    if not wrap_tables and config.RE_TABLE.search(para):
        return True

    # If the text begins with a single -, *, or +, followed by a space,
    # or an integer, followed by a ., followed by a space (in either
    # case optionally proceeded by whitespace), it's a list; don't wrap.
    return bool(
        config.RE_ORDERED_LIST_MATCHER.match(stripped)
        or config.RE_UNORDERED_LIST_MATCHER.match(stripped)
    )


def escape_md(text: str) -> str:
    """
    Escapes markdown-sensitive characters within other markdown
    constructs.
    """
    return config.RE_MD_CHARS_MATCHER.sub(r"\\\1", text)


def escape_md_section(text: str, snob: bool = False) -> str:
    """
    Escapes markdown-sensitive characters across whole document sections.
    """
    text = config.RE_MD_BACKSLASH_MATCHER.sub(r"\\\1", text)

    if snob:
        text = config.RE_MD_CHARS_MATCHER_ALL.sub(r"\\\1", text)

    text = config.RE_MD_DOT_MATCHER.sub(r"\1\\\2", text)
    text = config.RE_MD_PLUS_MATCHER.sub(r"\1\\\2", text)
    text = config.RE_MD_DASH_MATCHER.sub(r"\1\\\2", text)

    return text


def reformat_table(lines: List[str], right_margin: int) -> List[str]:
    """
    Given the lines of a table
    padds the cells and returns the new lines
    """
    # find the maximum width of the columns
    max_width = [len(x.rstrip()) + right_margin for x in lines[0].split("|")]
    max_cols = len(max_width)
    for line in lines:
        cols = [x.rstrip() for x in line.split("|")]
        num_cols = len(cols)

        # don't drop any data if colspan attributes result in unequal lengths
        if num_cols < max_cols:
            cols += [""] * (max_cols - num_cols)
        elif max_cols < num_cols:
            max_width += [len(x) + right_margin for x in cols[-(num_cols - max_cols) :]]
            max_cols = num_cols

        max_width = [
            max(len(x) + right_margin, old_len) for x, old_len in zip(cols, max_width)
        ]

    # reformat
    new_lines = []
    for line in lines:
        cols = [x.rstrip() for x in line.split("|")]
        if set(line.strip()) == set("-|"):
            filler = "-"
            new_cols = [
                x.rstrip() + (filler * (M - len(x.rstrip())))
                for x, M in zip(cols, max_width)
            ]
            new_lines.append("|-" + "|".join(new_cols) + "|")
        else:
            filler = " "
            new_cols = [
                x.rstrip() + (filler * (M - len(x.rstrip())))
                for x, M in zip(cols, max_width)
            ]
            new_lines.append("| " + "|".join(new_cols) + "|")
    return new_lines


def pad_tables_in_text(text: str, right_margin: int = 1) -> str:
    """
    Provide padding for tables in the text
    """
    lines = text.split("\n")
    table_buffer = []  # type: List[str]
    table_started = False
    new_lines = []
    for line in lines:
        # Toggle table started
        if config.TABLE_MARKER_FOR_PAD in line:
            table_started = not table_started
            if not table_started:
                table = reformat_table(table_buffer, right_margin)
                new_lines.extend(table)
                table_buffer = []
                new_lines.append("")
            continue
        # Process lines
        if table_started:
            table_buffer.append(line)
        else:
            new_lines.append(line)
    return "\n".join(new_lines)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\azure_ai\embed\handler.py ===
from typing import List, Optional, Union

from openai import OpenAI

import litellm
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    get_async_httpx_client,
)
from litellm.llms.openai.openai import OpenAIChatCompletion
from litellm.types.llms.azure_ai import ImageEmbeddingRequest
from litellm.types.utils import EmbeddingResponse
from litellm.utils import convert_to_model_response_object

from .cohere_transformation import AzureAICohereConfig


class AzureAIEmbedding(OpenAIChatCompletion):
    def _process_response(
        self,
        image_embedding_responses: Optional[List],
        text_embedding_responses: Optional[List],
        image_embeddings_idx: List[int],
        model_response: EmbeddingResponse,
        input: List,
    ):
        combined_responses = []
        if (
            image_embedding_responses is not None
            and text_embedding_responses is not None
        ):
            # Combine and order the results
            text_idx = 0
            image_idx = 0

            for idx in range(len(input)):
                if idx in image_embeddings_idx:
                    combined_responses.append(image_embedding_responses[image_idx])
                    image_idx += 1
                else:
                    combined_responses.append(text_embedding_responses[text_idx])
                    text_idx += 1

            model_response.data = combined_responses
        elif image_embedding_responses is not None:
            model_response.data = image_embedding_responses
        elif text_embedding_responses is not None:
            model_response.data = text_embedding_responses

        response = AzureAICohereConfig()._transform_response(response=model_response)  # type: ignore

        return response

    async def async_image_embedding(
        self,
        model: str,
        data: ImageEmbeddingRequest,
        timeout: float,
        logging_obj,
        model_response: litellm.EmbeddingResponse,
        optional_params: dict,
        api_key: Optional[str],
        api_base: Optional[str],
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
    ) -> EmbeddingResponse:
        if client is None or not isinstance(client, AsyncHTTPHandler):
            client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders.AZURE_AI,
                params={"timeout": timeout},
            )

        url = "{}/images/embeddings".format(api_base)

        response = await client.post(
            url=url,
            json=data,  # type: ignore
            headers={"Authorization": "Bearer {}".format(api_key)},
        )

        embedding_response = response.json()
        embedding_headers = dict(response.headers)
        returned_response: EmbeddingResponse = convert_to_model_response_object(  # type: ignore
            response_object=embedding_response,
            model_response_object=model_response,
            response_type="embedding",
            stream=False,
            _response_headers=embedding_headers,
        )
        return returned_response

    def image_embedding(
        self,
        model: str,
        data: ImageEmbeddingRequest,
        timeout: float,
        logging_obj,
        model_response: EmbeddingResponse,
        optional_params: dict,
        api_key: Optional[str],
        api_base: Optional[str],
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
    ):
        if api_base is None:
            raise ValueError(
                "api_base is None. Please set AZURE_AI_API_BASE or dynamically via `api_base` param, to make the request."
            )
        if api_key is None:
            raise ValueError(
                "api_key is None. Please set AZURE_AI_API_KEY or dynamically via `api_key` param, to make the request."
            )

        if client is None or not isinstance(client, HTTPHandler):
            client = HTTPHandler(timeout=timeout, concurrent_limit=1)

        url = "{}/images/embeddings".format(api_base)

        response = client.post(
            url=url,
            json=data,  # type: ignore
            headers={"Authorization": "Bearer {}".format(api_key)},
        )

        embedding_response = response.json()
        embedding_headers = dict(response.headers)
        returned_response: EmbeddingResponse = convert_to_model_response_object(  # type: ignore
            response_object=embedding_response,
            model_response_object=model_response,
            response_type="embedding",
            stream=False,
            _response_headers=embedding_headers,
        )
        return returned_response

    async def async_embedding(
        self,
        model: str,
        input: List,
        timeout: float,
        logging_obj,
        model_response: litellm.EmbeddingResponse,
        optional_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        client=None,
    ) -> EmbeddingResponse:
        (
            image_embeddings_request,
            v1_embeddings_request,
            image_embeddings_idx,
        ) = AzureAICohereConfig()._transform_request(
            input=input, optional_params=optional_params, model=model
        )

        image_embedding_responses: Optional[List] = None
        text_embedding_responses: Optional[List] = None

        if image_embeddings_request["input"]:
            image_response = await self.async_image_embedding(
                model=model,
                data=image_embeddings_request,
                timeout=timeout,
                logging_obj=logging_obj,
                model_response=model_response,
                optional_params=optional_params,
                api_key=api_key,
                api_base=api_base,
                client=client,
            )

            image_embedding_responses = image_response.data
            if image_embedding_responses is None:
                raise Exception("/image/embeddings route returned None Embeddings.")

        if v1_embeddings_request["input"]:
            response: EmbeddingResponse = await super().embedding(  # type: ignore
                model=model,
                input=input,
                timeout=timeout,
                logging_obj=logging_obj,
                model_response=model_response,
                optional_params=optional_params,
                api_key=api_key,
                api_base=api_base,
                client=client,
                aembedding=True,
            )
            text_embedding_responses = response.data
            if text_embedding_responses is None:
                raise Exception("/v1/embeddings route returned None Embeddings.")

        return self._process_response(
            image_embedding_responses=image_embedding_responses,
            text_embedding_responses=text_embedding_responses,
            image_embeddings_idx=image_embeddings_idx,
            model_response=model_response,
            input=input,
        )

    def embedding(
        self,
        model: str,
        input: List,
        timeout: float,
        logging_obj,
        model_response: EmbeddingResponse,
        optional_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        client=None,
        aembedding=None,
        max_retries: Optional[int] = None,
    ) -> EmbeddingResponse:
        """
        - Separate image url from text
        -> route image url call to `/image/embeddings`
        -> route text call to `/v1/embeddings` (OpenAI route)

        assemble result in-order, and return
        """
        if aembedding is True:
            return self.async_embedding(  # type: ignore
                model,
                input,
                timeout,
                logging_obj,
                model_response,
                optional_params,
                api_key,
                api_base,
                client,
            )

        (
            image_embeddings_request,
            v1_embeddings_request,
            image_embeddings_idx,
        ) = AzureAICohereConfig()._transform_request(
            input=input, optional_params=optional_params, model=model
        )

        image_embedding_responses: Optional[List] = None
        text_embedding_responses: Optional[List] = None

        if image_embeddings_request["input"]:
            image_response = self.image_embedding(
                model=model,
                data=image_embeddings_request,
                timeout=timeout,
                logging_obj=logging_obj,
                model_response=model_response,
                optional_params=optional_params,
                api_key=api_key,
                api_base=api_base,
                client=client,
            )

            image_embedding_responses = image_response.data
            if image_embedding_responses is None:
                raise Exception("/image/embeddings route returned None Embeddings.")

        if v1_embeddings_request["input"]:
            response: EmbeddingResponse = super().embedding(  # type: ignore
                model,
                input,
                timeout,
                logging_obj,
                model_response,
                optional_params,
                api_key,
                api_base,
                client=(
                    client
                    if client is not None and isinstance(client, OpenAI)
                    else None
                ),
                aembedding=aembedding,
            )

            text_embedding_responses = response.data
            if text_embedding_responses is None:
                raise Exception("/v1/embeddings route returned None Embeddings.")

        return self._process_response(
            image_embedding_responses=image_embedding_responses,
            text_embedding_responses=text_embedding_responses,
            image_embeddings_idx=image_embeddings_idx,
            model_response=model_response,
            input=input,
        )

# === NexusCore/openenv\Lib\site-packages\pip\_internal\cache.py ===
"""Cache Management
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pip._vendor.packaging.tags import Tag, interpreter_name, interpreter_version
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.exceptions import InvalidWheelFilename
from pip._internal.models.direct_url import DirectUrl
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.utils.temp_dir import TempDirectory, tempdir_kinds
from pip._internal.utils.urls import path_to_url

logger = logging.getLogger(__name__)

ORIGIN_JSON_NAME = "origin.json"


def _hash_dict(d: Dict[str, str]) -> str:
    """Return a stable sha224 of a dictionary."""
    s = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha224(s.encode("ascii")).hexdigest()


class Cache:
    """An abstract class - provides cache directories for data from links

    :param cache_dir: The root of the cache.
    """

    def __init__(self, cache_dir: str) -> None:
        super().__init__()
        assert not cache_dir or os.path.isabs(cache_dir)
        self.cache_dir = cache_dir or None

    def _get_cache_path_parts(self, link: Link) -> List[str]:
        """Get parts of part that must be os.path.joined with cache_dir"""

        # We want to generate an url to use as our cache key, we don't want to
        # just reuse the URL because it might have other items in the fragment
        # and we don't care about those.
        key_parts = {"url": link.url_without_fragment}
        if link.hash_name is not None and link.hash is not None:
            key_parts[link.hash_name] = link.hash
        if link.subdirectory_fragment:
            key_parts["subdirectory"] = link.subdirectory_fragment

        # Include interpreter name, major and minor version in cache key
        # to cope with ill-behaved sdists that build a different wheel
        # depending on the python version their setup.py is being run on,
        # and don't encode the difference in compatibility tags.
        # https://github.com/pypa/pip/issues/7296
        key_parts["interpreter_name"] = interpreter_name()
        key_parts["interpreter_version"] = interpreter_version()

        # Encode our key url with sha224, we'll use this because it has similar
        # security properties to sha256, but with a shorter total output (and
        # thus less secure). However the differences don't make a lot of
        # difference for our use case here.
        hashed = _hash_dict(key_parts)

        # We want to nest the directories some to prevent having a ton of top
        # level directories where we might run out of sub directories on some
        # FS.
        parts = [hashed[:2], hashed[2:4], hashed[4:6], hashed[6:]]

        return parts

    def _get_candidates(self, link: Link, canonical_package_name: str) -> List[Any]:
        can_not_cache = not self.cache_dir or not canonical_package_name or not link
        if can_not_cache:
            return []

        path = self.get_path_for_link(link)
        if os.path.isdir(path):
            return [(candidate, path) for candidate in os.listdir(path)]
        return []

    def get_path_for_link(self, link: Link) -> str:
        """Return a directory to store cached items in for link."""
        raise NotImplementedError()

    def get(
        self,
        link: Link,
        package_name: Optional[str],
        supported_tags: List[Tag],
    ) -> Link:
        """Returns a link to a cached item if it exists, otherwise returns the
        passed link.
        """
        raise NotImplementedError()


class SimpleWheelCache(Cache):
    """A cache of wheels for future installs."""

    def __init__(self, cache_dir: str) -> None:
        super().__init__(cache_dir)

    def get_path_for_link(self, link: Link) -> str:
        """Return a directory to store cached wheels for link

        Because there are M wheels for any one sdist, we provide a directory
        to cache them in, and then consult that directory when looking up
        cache hits.

        We only insert things into the cache if they have plausible version
        numbers, so that we don't contaminate the cache with things that were
        not unique. E.g. ./package might have dozens of installs done for it
        and build a version of 0.0...and if we built and cached a wheel, we'd
        end up using the same wheel even if the source has been edited.

        :param link: The link of the sdist for which this will cache wheels.
        """
        parts = self._get_cache_path_parts(link)
        assert self.cache_dir
        # Store wheels within the root cache_dir
        return os.path.join(self.cache_dir, "wheels", *parts)

    def get(
        self,
        link: Link,
        package_name: Optional[str],
        supported_tags: List[Tag],
    ) -> Link:
        candidates = []

        if not package_name:
            return link

        canonical_package_name = canonicalize_name(package_name)
        for wheel_name, wheel_dir in self._get_candidates(link, canonical_package_name):
            try:
                wheel = Wheel(wheel_name)
            except InvalidWheelFilename:
                continue
            if canonicalize_name(wheel.name) != canonical_package_name:
                logger.debug(
                    "Ignoring cached wheel %s for %s as it "
                    "does not match the expected distribution name %s.",
                    wheel_name,
                    link,
                    package_name,
                )
                continue
            if not wheel.supported(supported_tags):
                # Built for a different python/arch/etc
                continue
            candidates.append(
                (
                    wheel.support_index_min(supported_tags),
                    wheel_name,
                    wheel_dir,
                )
            )

        if not candidates:
            return link

        _, wheel_name, wheel_dir = min(candidates)
        return Link(path_to_url(os.path.join(wheel_dir, wheel_name)))


class EphemWheelCache(SimpleWheelCache):
    """A SimpleWheelCache that creates it's own temporary cache directory"""

    def __init__(self) -> None:
        self._temp_dir = TempDirectory(
            kind=tempdir_kinds.EPHEM_WHEEL_CACHE,
            globally_managed=True,
        )

        super().__init__(self._temp_dir.path)


class CacheEntry:
    def __init__(
        self,
        link: Link,
        persistent: bool,
    ):
        self.link = link
        self.persistent = persistent
        self.origin: Optional[DirectUrl] = None
        origin_direct_url_path = Path(self.link.file_path).parent / ORIGIN_JSON_NAME
        if origin_direct_url_path.exists():
            try:
                self.origin = DirectUrl.from_json(
                    origin_direct_url_path.read_text(encoding="utf-8")
                )
            except Exception as e:
                logger.warning(
                    "Ignoring invalid cache entry origin file %s for %s (%s)",
                    origin_direct_url_path,
                    link.filename,
                    e,
                )


class WheelCache(Cache):
    """Wraps EphemWheelCache and SimpleWheelCache into a single Cache

    This Cache allows for gracefully degradation, using the ephem wheel cache
    when a certain link is not found in the simple wheel cache first.
    """

    def __init__(self, cache_dir: str) -> None:
        super().__init__(cache_dir)
        self._wheel_cache = SimpleWheelCache(cache_dir)
        self._ephem_cache = EphemWheelCache()

    def get_path_for_link(self, link: Link) -> str:
        return self._wheel_cache.get_path_for_link(link)

    def get_ephem_path_for_link(self, link: Link) -> str:
        return self._ephem_cache.get_path_for_link(link)

    def get(
        self,
        link: Link,
        package_name: Optional[str],
        supported_tags: List[Tag],
    ) -> Link:
        cache_entry = self.get_cache_entry(link, package_name, supported_tags)
        if cache_entry is None:
            return link
        return cache_entry.link

    def get_cache_entry(
        self,
        link: Link,
        package_name: Optional[str],
        supported_tags: List[Tag],
    ) -> Optional[CacheEntry]:
        """Returns a CacheEntry with a link to a cached item if it exists or
        None. The cache entry indicates if the item was found in the persistent
        or ephemeral cache.
        """
        retval = self._wheel_cache.get(
            link=link,
            package_name=package_name,
            supported_tags=supported_tags,
        )
        if retval is not link:
            return CacheEntry(retval, persistent=True)

        retval = self._ephem_cache.get(
            link=link,
            package_name=package_name,
            supported_tags=supported_tags,
        )
        if retval is not link:
            return CacheEntry(retval, persistent=False)

        return None

    @staticmethod
    def record_download_origin(cache_dir: str, download_info: DirectUrl) -> None:
        origin_path = Path(cache_dir) / ORIGIN_JSON_NAME
        if origin_path.exists():
            try:
                origin = DirectUrl.from_json(origin_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(
                    "Could not read origin file %s in cache entry (%s). "
                    "Will attempt to overwrite it.",
                    origin_path,
                    e,
                )
            else:
                # TODO: use DirectUrl.equivalent when
                # https://github.com/pypa/pip/pull/10564 is merged.
                if origin.url != download_info.url:
                    logger.warning(
                        "Origin URL %s in cache entry %s does not match download URL "
                        "%s. This is likely a pip bug or a cache corruption issue. "
                        "Will overwrite it with the new value.",
                        origin.url,
                        cache_dir,
                        download_info.url,
                    )
        origin_path.write_text(download_info.to_json(), encoding="utf-8")