
# === NexusCore/tools\exports\export_20250803_114325\combined_195.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\utils\logging.py ===
import contextlib
import errno
import logging
import logging.handlers
import os
import sys
import threading
from dataclasses import dataclass
from io import TextIOWrapper
from logging import Filter
from typing import Any, ClassVar, Generator, List, Optional, TextIO, Type

from pip._vendor.rich.console import (
    Console,
    ConsoleOptions,
    ConsoleRenderable,
    RenderableType,
    RenderResult,
    RichCast,
)
from pip._vendor.rich.highlighter import NullHighlighter
from pip._vendor.rich.logging import RichHandler
from pip._vendor.rich.segment import Segment
from pip._vendor.rich.style import Style

from pip._internal.utils._log import VERBOSE, getLogger
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.deprecation import DEPRECATION_MSG_PREFIX
from pip._internal.utils.misc import ensure_dir

_log_state = threading.local()
subprocess_logger = getLogger("pip.subprocessor")


class BrokenStdoutLoggingError(Exception):
    """
    Raised if BrokenPipeError occurs for the stdout stream while logging.
    """


def _is_broken_pipe_error(exc_class: Type[BaseException], exc: BaseException) -> bool:
    if exc_class is BrokenPipeError:
        return True

    # On Windows, a broken pipe can show up as EINVAL rather than EPIPE:
    # https://bugs.python.org/issue19612
    # https://bugs.python.org/issue30418
    if not WINDOWS:
        return False

    return isinstance(exc, OSError) and exc.errno in (errno.EINVAL, errno.EPIPE)


@contextlib.contextmanager
def indent_log(num: int = 2) -> Generator[None, None, None]:
    """
    A context manager which will cause the log output to be indented for any
    log messages emitted inside it.
    """
    # For thread-safety
    _log_state.indentation = get_indentation()
    _log_state.indentation += num
    try:
        yield
    finally:
        _log_state.indentation -= num


def get_indentation() -> int:
    return getattr(_log_state, "indentation", 0)


class IndentingFormatter(logging.Formatter):
    default_time_format = "%Y-%m-%dT%H:%M:%S"

    def __init__(
        self,
        *args: Any,
        add_timestamp: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        A logging.Formatter that obeys the indent_log() context manager.

        :param add_timestamp: A bool indicating output lines should be prefixed
            with their record's timestamp.
        """
        self.add_timestamp = add_timestamp
        super().__init__(*args, **kwargs)

    def get_message_start(self, formatted: str, levelno: int) -> str:
        """
        Return the start of the formatted log message (not counting the
        prefix to add to each line).
        """
        if levelno < logging.WARNING:
            return ""
        if formatted.startswith(DEPRECATION_MSG_PREFIX):
            # Then the message already has a prefix.  We don't want it to
            # look like "WARNING: DEPRECATION: ...."
            return ""
        if levelno < logging.ERROR:
            return "WARNING: "

        return "ERROR: "

    def format(self, record: logging.LogRecord) -> str:
        """
        Calls the standard formatter, but will indent all of the log message
        lines by our current indentation level.
        """
        formatted = super().format(record)
        message_start = self.get_message_start(formatted, record.levelno)
        formatted = message_start + formatted

        prefix = ""
        if self.add_timestamp:
            prefix = f"{self.formatTime(record)} "
        prefix += " " * get_indentation()
        formatted = "".join([prefix + line for line in formatted.splitlines(True)])
        return formatted


@dataclass
class IndentedRenderable:
    renderable: RenderableType
    indent: int

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        segments = console.render(self.renderable, options)
        lines = Segment.split_lines(segments)
        for line in lines:
            yield Segment(" " * self.indent)
            yield from line
            yield Segment("\n")


class PipConsole(Console):
    def on_broken_pipe(self) -> None:
        # Reraise the original exception, rich 13.8.0+ exits by default
        # instead, preventing our handler from firing.
        raise BrokenPipeError() from None


class RichPipStreamHandler(RichHandler):
    KEYWORDS: ClassVar[Optional[List[str]]] = []

    def __init__(self, stream: Optional[TextIO], no_color: bool) -> None:
        super().__init__(
            console=PipConsole(file=stream, no_color=no_color, soft_wrap=True),
            show_time=False,
            show_level=False,
            show_path=False,
            highlighter=NullHighlighter(),
        )

    # Our custom override on Rich's logger, to make things work as we need them to.
    def emit(self, record: logging.LogRecord) -> None:
        style: Optional[Style] = None

        # If we are given a diagnostic error to present, present it with indentation.
        if getattr(record, "rich", False):
            assert isinstance(record.args, tuple)
            (rich_renderable,) = record.args
            assert isinstance(
                rich_renderable, (ConsoleRenderable, RichCast, str)
            ), f"{rich_renderable} is not rich-console-renderable"

            renderable: RenderableType = IndentedRenderable(
                rich_renderable, indent=get_indentation()
            )
        else:
            message = self.format(record)
            renderable = self.render_message(record, message)
            if record.levelno is not None:
                if record.levelno >= logging.ERROR:
                    style = Style(color="red")
                elif record.levelno >= logging.WARNING:
                    style = Style(color="yellow")

        try:
            self.console.print(renderable, overflow="ignore", crop=False, style=style)
        except Exception:
            self.handleError(record)

    def handleError(self, record: logging.LogRecord) -> None:
        """Called when logging is unable to log some output."""

        exc_class, exc = sys.exc_info()[:2]
        # If a broken pipe occurred while calling write() or flush() on the
        # stdout stream in logging's Handler.emit(), then raise our special
        # exception so we can handle it in main() instead of logging the
        # broken pipe error and continuing.
        if (
            exc_class
            and exc
            and self.console.file is sys.stdout
            and _is_broken_pipe_error(exc_class, exc)
        ):
            raise BrokenStdoutLoggingError()

        return super().handleError(record)


class BetterRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def _open(self) -> TextIOWrapper:
        ensure_dir(os.path.dirname(self.baseFilename))
        return super()._open()


class MaxLevelFilter(Filter):
    def __init__(self, level: int) -> None:
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < self.level


class ExcludeLoggerFilter(Filter):
    """
    A logging Filter that excludes records from a logger (or its children).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # The base Filter class allows only records from a logger (or its
        # children).
        return not super().filter(record)


def setup_logging(verbosity: int, no_color: bool, user_log_file: Optional[str]) -> int:
    """Configures and sets up all of the logging

    Returns the requested logging level, as its integer value.
    """

    # Determine the level to be logging at.
    if verbosity >= 2:
        level_number = logging.DEBUG
    elif verbosity == 1:
        level_number = VERBOSE
    elif verbosity == -1:
        level_number = logging.WARNING
    elif verbosity == -2:
        level_number = logging.ERROR
    elif verbosity <= -3:
        level_number = logging.CRITICAL
    else:
        level_number = logging.INFO

    level = logging.getLevelName(level_number)

    # The "root" logger should match the "console" level *unless* we also need
    # to log to a user log file.
    include_user_log = user_log_file is not None
    if include_user_log:
        additional_log_file = user_log_file
        root_level = "DEBUG"
    else:
        additional_log_file = "/dev/null"
        root_level = level

    # Disable any logging besides WARNING unless we have DEBUG level logging
    # enabled for vendored libraries.
    vendored_log_level = "WARNING" if level in ["INFO", "ERROR"] else "DEBUG"

    # Shorthands for clarity
    log_streams = {
        "stdout": "ext://sys.stdout",
        "stderr": "ext://sys.stderr",
    }
    handler_classes = {
        "stream": "pip._internal.utils.logging.RichPipStreamHandler",
        "file": "pip._internal.utils.logging.BetterRotatingFileHandler",
    }
    handlers = ["console", "console_errors", "console_subprocess"] + (
        ["user_log"] if include_user_log else []
    )

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "exclude_warnings": {
                    "()": "pip._internal.utils.logging.MaxLevelFilter",
                    "level": logging.WARNING,
                },
                "restrict_to_subprocess": {
                    "()": "logging.Filter",
                    "name": subprocess_logger.name,
                },
                "exclude_subprocess": {
                    "()": "pip._internal.utils.logging.ExcludeLoggerFilter",
                    "name": subprocess_logger.name,
                },
            },
            "formatters": {
                "indent": {
                    "()": IndentingFormatter,
                    "format": "%(message)s",
                },
                "indent_with_timestamp": {
                    "()": IndentingFormatter,
                    "format": "%(message)s",
                    "add_timestamp": True,
                },
            },
            "handlers": {
                "console": {
                    "level": level,
                    "class": handler_classes["stream"],
                    "no_color": no_color,
                    "stream": log_streams["stdout"],
                    "filters": ["exclude_subprocess", "exclude_warnings"],
                    "formatter": "indent",
                },
                "console_errors": {
                    "level": "WARNING",
                    "class": handler_classes["stream"],
                    "no_color": no_color,
                    "stream": log_streams["stderr"],
                    "filters": ["exclude_subprocess"],
                    "formatter": "indent",
                },
                # A handler responsible for logging to the console messages
                # from the "subprocessor" logger.
                "console_subprocess": {
                    "level": level,
                    "class": handler_classes["stream"],
                    "stream": log_streams["stderr"],
                    "no_color": no_color,
                    "filters": ["restrict_to_subprocess"],
                    "formatter": "indent",
                },
                "user_log": {
                    "level": "DEBUG",
                    "class": handler_classes["file"],
                    "filename": additional_log_file,
                    "encoding": "utf-8",
                    "delay": True,
                    "formatter": "indent_with_timestamp",
                },
            },
            "root": {
                "level": root_level,
                "handlers": handlers,
            },
            "loggers": {"pip._vendor": {"level": vendored_log_level}},
        }
    )

    return level_number

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\packaging\_parser.py ===
"""Handwritten parser of dependency specifiers.

The docstring for each __parse_* function contains EBNF-inspired grammar representing
the implementation.
"""

from __future__ import annotations

import ast
from typing import NamedTuple, Sequence, Tuple, Union

from ._tokenizer import DEFAULT_RULES, Tokenizer


class Node:
    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}('{self}')>"

    def serialize(self) -> str:
        raise NotImplementedError


class Variable(Node):
    def serialize(self) -> str:
        return str(self)


class Value(Node):
    def serialize(self) -> str:
        return f'"{self}"'


class Op(Node):
    def serialize(self) -> str:
        return str(self)


MarkerVar = Union[Variable, Value]
MarkerItem = Tuple[MarkerVar, Op, MarkerVar]
MarkerAtom = Union[MarkerItem, Sequence["MarkerAtom"]]
MarkerList = Sequence[Union["MarkerList", MarkerAtom, str]]


class ParsedRequirement(NamedTuple):
    name: str
    url: str
    extras: list[str]
    specifier: str
    marker: MarkerList | None


# --------------------------------------------------------------------------------------
# Recursive descent parser for dependency specifier
# --------------------------------------------------------------------------------------
def parse_requirement(source: str) -> ParsedRequirement:
    return _parse_requirement(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_requirement(tokenizer: Tokenizer) -> ParsedRequirement:
    """
    requirement = WS? IDENTIFIER WS? extras WS? requirement_details
    """
    tokenizer.consume("WS")

    name_token = tokenizer.expect(
        "IDENTIFIER", expected="package name at the start of dependency specifier"
    )
    name = name_token.text
    tokenizer.consume("WS")

    extras = _parse_extras(tokenizer)
    tokenizer.consume("WS")

    url, specifier, marker = _parse_requirement_details(tokenizer)
    tokenizer.expect("END", expected="end of dependency specifier")

    return ParsedRequirement(name, url, extras, specifier, marker)


def _parse_requirement_details(
    tokenizer: Tokenizer,
) -> tuple[str, str, MarkerList | None]:
    """
    requirement_details = AT URL (WS requirement_marker?)?
                        | specifier WS? (requirement_marker)?
    """

    specifier = ""
    url = ""
    marker = None

    if tokenizer.check("AT"):
        tokenizer.read()
        tokenizer.consume("WS")

        url_start = tokenizer.position
        url = tokenizer.expect("URL", expected="URL after @").text
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        tokenizer.expect("WS", expected="whitespace after URL")

        # The input might end after whitespace.
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer, span_start=url_start, after="URL and whitespace"
        )
    else:
        specifier_start = tokenizer.position
        specifier = _parse_specifier(tokenizer)
        tokenizer.consume("WS")

        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer,
            span_start=specifier_start,
            after=(
                "version specifier"
                if specifier
                else "name and no valid version specifier"
            ),
        )

    return (url, specifier, marker)


def _parse_requirement_marker(
    tokenizer: Tokenizer, *, span_start: int, after: str
) -> MarkerList:
    """
    requirement_marker = SEMICOLON marker WS?
    """

    if not tokenizer.check("SEMICOLON"):
        tokenizer.raise_syntax_error(
            f"Expected end or semicolon (after {after})",
            span_start=span_start,
        )
    tokenizer.read()

    marker = _parse_marker(tokenizer)
    tokenizer.consume("WS")

    return marker


def _parse_extras(tokenizer: Tokenizer) -> list[str]:
    """
    extras = (LEFT_BRACKET wsp* extras_list? wsp* RIGHT_BRACKET)?
    """
    if not tokenizer.check("LEFT_BRACKET", peek=True):
        return []

    with tokenizer.enclosing_tokens(
        "LEFT_BRACKET",
        "RIGHT_BRACKET",
        around="extras",
    ):
        tokenizer.consume("WS")
        extras = _parse_extras_list(tokenizer)
        tokenizer.consume("WS")

    return extras


def _parse_extras_list(tokenizer: Tokenizer) -> list[str]:
    """
    extras_list = identifier (wsp* ',' wsp* identifier)*
    """
    extras: list[str] = []

    if not tokenizer.check("IDENTIFIER"):
        return extras

    extras.append(tokenizer.read().text)

    while True:
        tokenizer.consume("WS")
        if tokenizer.check("IDENTIFIER", peek=True):
            tokenizer.raise_syntax_error("Expected comma between extra names")
        elif not tokenizer.check("COMMA"):
            break

        tokenizer.read()
        tokenizer.consume("WS")

        extra_token = tokenizer.expect("IDENTIFIER", expected="extra name after comma")
        extras.append(extra_token.text)

    return extras


def _parse_specifier(tokenizer: Tokenizer) -> str:
    """
    specifier = LEFT_PARENTHESIS WS? version_many WS? RIGHT_PARENTHESIS
              | WS? version_many WS?
    """
    with tokenizer.enclosing_tokens(
        "LEFT_PARENTHESIS",
        "RIGHT_PARENTHESIS",
        around="version specifier",
    ):
        tokenizer.consume("WS")
        parsed_specifiers = _parse_version_many(tokenizer)
        tokenizer.consume("WS")

    return parsed_specifiers


def _parse_version_many(tokenizer: Tokenizer) -> str:
    """
    version_many = (SPECIFIER (WS? COMMA WS? SPECIFIER)*)?
    """
    parsed_specifiers = ""
    while tokenizer.check("SPECIFIER"):
        span_start = tokenizer.position
        parsed_specifiers += tokenizer.read().text
        if tokenizer.check("VERSION_PREFIX_TRAIL", peek=True):
            tokenizer.raise_syntax_error(
                ".* suffix can only be used with `==` or `!=` operators",
                span_start=span_start,
                span_end=tokenizer.position + 1,
            )
        if tokenizer.check("VERSION_LOCAL_LABEL_TRAIL", peek=True):
            tokenizer.raise_syntax_error(
                "Local version label can only be used with `==` or `!=` operators",
                span_start=span_start,
                span_end=tokenizer.position,
            )
        tokenizer.consume("WS")
        if not tokenizer.check("COMMA"):
            break
        parsed_specifiers += tokenizer.read().text
        tokenizer.consume("WS")

    return parsed_specifiers


# --------------------------------------------------------------------------------------
# Recursive descent parser for marker expression
# --------------------------------------------------------------------------------------
def parse_marker(source: str) -> MarkerList:
    return _parse_full_marker(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_full_marker(tokenizer: Tokenizer) -> MarkerList:
    retval = _parse_marker(tokenizer)
    tokenizer.expect("END", expected="end of marker expression")
    return retval


def _parse_marker(tokenizer: Tokenizer) -> MarkerList:
    """
    marker = marker_atom (BOOLOP marker_atom)+
    """
    expression = [_parse_marker_atom(tokenizer)]
    while tokenizer.check("BOOLOP"):
        token = tokenizer.read()
        expr_right = _parse_marker_atom(tokenizer)
        expression.extend((token.text, expr_right))
    return expression


def _parse_marker_atom(tokenizer: Tokenizer) -> MarkerAtom:
    """
    marker_atom = WS? LEFT_PARENTHESIS WS? marker WS? RIGHT_PARENTHESIS WS?
                | WS? marker_item WS?
    """

    tokenizer.consume("WS")
    if tokenizer.check("LEFT_PARENTHESIS", peek=True):
        with tokenizer.enclosing_tokens(
            "LEFT_PARENTHESIS",
            "RIGHT_PARENTHESIS",
            around="marker expression",
        ):
            tokenizer.consume("WS")
            marker: MarkerAtom = _parse_marker(tokenizer)
            tokenizer.consume("WS")
    else:
        marker = _parse_marker_item(tokenizer)
    tokenizer.consume("WS")
    return marker


def _parse_marker_item(tokenizer: Tokenizer) -> MarkerItem:
    """
    marker_item = WS? marker_var WS? marker_op WS? marker_var WS?
    """
    tokenizer.consume("WS")
    marker_var_left = _parse_marker_var(tokenizer)
    tokenizer.consume("WS")
    marker_op = _parse_marker_op(tokenizer)
    tokenizer.consume("WS")
    marker_var_right = _parse_marker_var(tokenizer)
    tokenizer.consume("WS")
    return (marker_var_left, marker_op, marker_var_right)


def _parse_marker_var(tokenizer: Tokenizer) -> MarkerVar:
    """
    marker_var = VARIABLE | QUOTED_STRING
    """
    if tokenizer.check("VARIABLE"):
        return process_env_var(tokenizer.read().text.replace(".", "_"))
    elif tokenizer.check("QUOTED_STRING"):
        return process_python_str(tokenizer.read().text)
    else:
        tokenizer.raise_syntax_error(
            message="Expected a marker variable or quoted string"
        )


def process_env_var(env_var: str) -> Variable:
    if env_var in ("platform_python_implementation", "python_implementation"):
        return Variable("platform_python_implementation")
    else:
        return Variable(env_var)


def process_python_str(python_str: str) -> Value:
    value = ast.literal_eval(python_str)
    return Value(str(value))


def _parse_marker_op(tokenizer: Tokenizer) -> Op:
    """
    marker_op = IN | NOT IN | OP
    """
    if tokenizer.check("IN"):
        tokenizer.read()
        return Op("in")
    elif tokenizer.check("NOT"):
        tokenizer.read()
        tokenizer.expect("WS", expected="whitespace after 'not'")
        tokenizer.expect("IN", expected="'in' after 'not'")
        return Op("not in")
    elif tokenizer.check("OP"):
        return Op(tokenizer.read().text)
    else:
        return tokenizer.raise_syntax_error(
            "Expected marker operator, one of "
            "<=, <, !=, ==, >=, >, ~=, ===, in, not in"
        )

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\__init__.py ===
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
from google.ai.generativelanguage_v1beta import gapic_version as package_version

__version__ = package_version.__version__


from .services.cache_service import CacheServiceAsyncClient, CacheServiceClient
from .services.discuss_service import DiscussServiceAsyncClient, DiscussServiceClient
from .services.file_service import FileServiceAsyncClient, FileServiceClient
from .services.generative_service import (
    GenerativeServiceAsyncClient,
    GenerativeServiceClient,
)
from .services.model_service import ModelServiceAsyncClient, ModelServiceClient
from .services.permission_service import (
    PermissionServiceAsyncClient,
    PermissionServiceClient,
)
from .services.retriever_service import (
    RetrieverServiceAsyncClient,
    RetrieverServiceClient,
)
from .services.text_service import TextServiceAsyncClient, TextServiceClient
from .types.cache_service import (
    CreateCachedContentRequest,
    DeleteCachedContentRequest,
    GetCachedContentRequest,
    ListCachedContentsRequest,
    ListCachedContentsResponse,
    UpdateCachedContentRequest,
)
from .types.cached_content import CachedContent
from .types.citation import CitationMetadata, CitationSource
from .types.content import (
    Blob,
    CodeExecution,
    CodeExecutionResult,
    Content,
    ExecutableCode,
    FileData,
    FunctionCall,
    FunctionCallingConfig,
    FunctionDeclaration,
    FunctionResponse,
    GroundingPassage,
    GroundingPassages,
    Part,
    Schema,
    Tool,
    ToolConfig,
    Type,
)
from .types.discuss_service import (
    CountMessageTokensRequest,
    CountMessageTokensResponse,
    Example,
    GenerateMessageRequest,
    GenerateMessageResponse,
    Message,
    MessagePrompt,
)
from .types.file import File, VideoMetadata
from .types.file_service import (
    CreateFileRequest,
    CreateFileResponse,
    DeleteFileRequest,
    GetFileRequest,
    ListFilesRequest,
    ListFilesResponse,
)
from .types.generative_service import (
    AttributionSourceId,
    BatchEmbedContentsRequest,
    BatchEmbedContentsResponse,
    Candidate,
    ContentEmbedding,
    CountTokensRequest,
    CountTokensResponse,
    EmbedContentRequest,
    EmbedContentResponse,
    GenerateAnswerRequest,
    GenerateAnswerResponse,
    GenerateContentRequest,
    GenerateContentResponse,
    GenerationConfig,
    GroundingAttribution,
    SemanticRetrieverConfig,
    TaskType,
)
from .types.model import Model
from .types.model_service import (
    CreateTunedModelMetadata,
    CreateTunedModelRequest,
    DeleteTunedModelRequest,
    GetModelRequest,
    GetTunedModelRequest,
    ListModelsRequest,
    ListModelsResponse,
    ListTunedModelsRequest,
    ListTunedModelsResponse,
    UpdateTunedModelRequest,
)
from .types.permission import Permission
from .types.permission_service import (
    CreatePermissionRequest,
    DeletePermissionRequest,
    GetPermissionRequest,
    ListPermissionsRequest,
    ListPermissionsResponse,
    TransferOwnershipRequest,
    TransferOwnershipResponse,
    UpdatePermissionRequest,
)
from .types.retriever import (
    Chunk,
    ChunkData,
    Condition,
    Corpus,
    CustomMetadata,
    Document,
    MetadataFilter,
    StringList,
)
from .types.retriever_service import (
    BatchCreateChunksRequest,
    BatchCreateChunksResponse,
    BatchDeleteChunksRequest,
    BatchUpdateChunksRequest,
    BatchUpdateChunksResponse,
    CreateChunkRequest,
    CreateCorpusRequest,
    CreateDocumentRequest,
    DeleteChunkRequest,
    DeleteCorpusRequest,
    DeleteDocumentRequest,
    GetChunkRequest,
    GetCorpusRequest,
    GetDocumentRequest,
    ListChunksRequest,
    ListChunksResponse,
    ListCorporaRequest,
    ListCorporaResponse,
    ListDocumentsRequest,
    ListDocumentsResponse,
    QueryCorpusRequest,
    QueryCorpusResponse,
    QueryDocumentRequest,
    QueryDocumentResponse,
    RelevantChunk,
    UpdateChunkRequest,
    UpdateCorpusRequest,
    UpdateDocumentRequest,
)
from .types.safety import (
    ContentFilter,
    HarmCategory,
    SafetyFeedback,
    SafetyRating,
    SafetySetting,
)
from .types.text_service import (
    BatchEmbedTextRequest,
    BatchEmbedTextResponse,
    CountTextTokensRequest,
    CountTextTokensResponse,
    Embedding,
    EmbedTextRequest,
    EmbedTextResponse,
    GenerateTextRequest,
    GenerateTextResponse,
    TextCompletion,
    TextPrompt,
)
from .types.tuned_model import (
    Dataset,
    Hyperparameters,
    TunedModel,
    TunedModelSource,
    TuningExample,
    TuningExamples,
    TuningSnapshot,
    TuningTask,
)

__all__ = (
    "CacheServiceAsyncClient",
    "DiscussServiceAsyncClient",
    "FileServiceAsyncClient",
    "GenerativeServiceAsyncClient",
    "ModelServiceAsyncClient",
    "PermissionServiceAsyncClient",
    "RetrieverServiceAsyncClient",
    "TextServiceAsyncClient",
    "AttributionSourceId",
    "BatchCreateChunksRequest",
    "BatchCreateChunksResponse",
    "BatchDeleteChunksRequest",
    "BatchEmbedContentsRequest",
    "BatchEmbedContentsResponse",
    "BatchEmbedTextRequest",
    "BatchEmbedTextResponse",
    "BatchUpdateChunksRequest",
    "BatchUpdateChunksResponse",
    "Blob",
    "CacheServiceClient",
    "CachedContent",
    "Candidate",
    "Chunk",
    "ChunkData",
    "CitationMetadata",
    "CitationSource",
    "CodeExecution",
    "CodeExecutionResult",
    "Condition",
    "Content",
    "ContentEmbedding",
    "ContentFilter",
    "Corpus",
    "CountMessageTokensRequest",
    "CountMessageTokensResponse",
    "CountTextTokensRequest",
    "CountTextTokensResponse",
    "CountTokensRequest",
    "CountTokensResponse",
    "CreateCachedContentRequest",
    "CreateChunkRequest",
    "CreateCorpusRequest",
    "CreateDocumentRequest",
    "CreateFileRequest",
    "CreateFileResponse",
    "CreatePermissionRequest",
    "CreateTunedModelMetadata",
    "CreateTunedModelRequest",
    "CustomMetadata",
    "Dataset",
    "DeleteCachedContentRequest",
    "DeleteChunkRequest",
    "DeleteCorpusRequest",
    "DeleteDocumentRequest",
    "DeleteFileRequest",
    "DeletePermissionRequest",
    "DeleteTunedModelRequest",
    "DiscussServiceClient",
    "Document",
    "EmbedContentRequest",
    "EmbedContentResponse",
    "EmbedTextRequest",
    "EmbedTextResponse",
    "Embedding",
    "Example",
    "ExecutableCode",
    "File",
    "FileData",
    "FileServiceClient",
    "FunctionCall",
    "FunctionCallingConfig",
    "FunctionDeclaration",
    "FunctionResponse",
    "GenerateAnswerRequest",
    "GenerateAnswerResponse",
    "GenerateContentRequest",
    "GenerateContentResponse",
    "GenerateMessageRequest",
    "GenerateMessageResponse",
    "GenerateTextRequest",
    "GenerateTextResponse",
    "GenerationConfig",
    "GenerativeServiceClient",
    "GetCachedContentRequest",
    "GetChunkRequest",
    "GetCorpusRequest",
    "GetDocumentRequest",
    "GetFileRequest",
    "GetModelRequest",
    "GetPermissionRequest",
    "GetTunedModelRequest",
    "GroundingAttribution",
    "GroundingPassage",
    "GroundingPassages",
    "HarmCategory",
    "Hyperparameters",
    "ListCachedContentsRequest",
    "ListCachedContentsResponse",
    "ListChunksRequest",
    "ListChunksResponse",
    "ListCorporaRequest",
    "ListCorporaResponse",
    "ListDocumentsRequest",
    "ListDocumentsResponse",
    "ListFilesRequest",
    "ListFilesResponse",
    "ListModelsRequest",
    "ListModelsResponse",
    "ListPermissionsRequest",
    "ListPermissionsResponse",
    "ListTunedModelsRequest",
    "ListTunedModelsResponse",
    "Message",
    "MessagePrompt",
    "MetadataFilter",
    "Model",
    "ModelServiceClient",
    "Part",
    "Permission",
    "PermissionServiceClient",
    "QueryCorpusRequest",
    "QueryCorpusResponse",
    "QueryDocumentRequest",
    "QueryDocumentResponse",
    "RelevantChunk",
    "RetrieverServiceClient",
    "SafetyFeedback",
    "SafetyRating",
    "SafetySetting",
    "Schema",
    "SemanticRetrieverConfig",
    "StringList",
    "TaskType",
    "TextCompletion",
    "TextPrompt",
    "TextServiceClient",
    "Tool",
    "ToolConfig",
    "TransferOwnershipRequest",
    "TransferOwnershipResponse",
    "TunedModel",
    "TunedModelSource",
    "TuningExample",
    "TuningExamples",
    "TuningSnapshot",
    "TuningTask",
    "Type",
    "UpdateCachedContentRequest",
    "UpdateChunkRequest",
    "UpdateCorpusRequest",
    "UpdateDocumentRequest",
    "UpdatePermissionRequest",
    "UpdateTunedModelRequest",
    "VideoMetadata",
)

# === NexusCore/openenv\Lib\site-packages\IPython\utils\path.py ===
# encoding: utf-8
"""
Utilities for path handling.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import os
import sys
import errno
import shutil
import random
import glob
import warnings

from IPython.utils.process import system

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------
fs_encoding = sys.getfilesystemencoding()

def _writable_dir(path):
    """Whether `path` is a directory, to which the user has write access."""
    return os.path.isdir(path) and os.access(path, os.W_OK)

if sys.platform == 'win32':
    def _get_long_path_name(path):
        """Get a long path name (expand ~) on Windows using ctypes.

        Examples
        --------

        >>> get_long_path_name('c:\\\\docume~1')
        'c:\\\\Documents and Settings'

        """
        try:
            import ctypes
        except ImportError as e: 
            raise ImportError('you need to have ctypes installed for this to work') from e
        _GetLongPathName = ctypes.windll.kernel32.GetLongPathNameW
        _GetLongPathName.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p,
            ctypes.c_uint ]

        buf = ctypes.create_unicode_buffer(260)
        rv = _GetLongPathName(path, buf, 260)
        if rv == 0 or rv > 260:
            return path
        else:
            return buf.value
else:
    def _get_long_path_name(path):
        """Dummy no-op."""
        return path



def get_long_path_name(path):
    """Expand a path into its long form.

    On Windows this expands any ~ in the paths. On other platforms, it is
    a null operation.
    """
    return _get_long_path_name(path)


def compress_user(path: str) -> str:
    """Reverse of :func:`os.path.expanduser`"""
    home = os.path.expanduser("~")
    if path.startswith(home):
        path =  "~" + path[len(home):]
    return path

def get_py_filename(name):
    """Return a valid python filename in the current directory.

    If the given name is not a file, it adds '.py' and searches again.
    Raises IOError with an informative message if the file isn't found.
    """

    name = os.path.expanduser(name)
    if os.path.isfile(name):
        return name
    if not name.endswith(".py"):
        py_name = name + ".py"
        if os.path.isfile(py_name):
            return py_name
    raise IOError("File `%r` not found." % name)


def filefind(filename: str, path_dirs=None) -> str:
    """Find a file by looking through a sequence of paths.

    This iterates through a sequence of paths looking for a file and returns
    the full, absolute path of the first occurrence of the file.  If no set of
    path dirs is given, the filename is tested as is, after running through
    :func:`expandvars` and :func:`expanduser`.  Thus a simple call::

        filefind('myfile.txt')

    will find the file in the current working dir, but::

        filefind('~/myfile.txt')

    Will find the file in the users home directory.  This function does not
    automatically try any paths, such as the cwd or the user's home directory.

    Parameters
    ----------
    filename : str
        The filename to look for.
    path_dirs : str, None or sequence of str
        The sequence of paths to look for the file in.  If None, the filename
        need to be absolute or be in the cwd.  If a string, the string is
        put into a sequence and the searched.  If a sequence, walk through
        each element and join with ``filename``, calling :func:`expandvars`
        and :func:`expanduser` before testing for existence.

    Returns
    -------
    path : str
        returns absolute path to file.

    Raises
    ------
    IOError
    """

    # If paths are quoted, abspath gets confused, strip them...
    filename = filename.strip('"').strip("'")
    # If the input is an absolute path, just check it exists
    if os.path.isabs(filename) and os.path.isfile(filename):
        return filename

    if path_dirs is None:
        path_dirs = ("",)
    elif isinstance(path_dirs, str):
        path_dirs = (path_dirs,)

    for path in path_dirs:
        if path == '.': path = os.getcwd()
        testname = expand_path(os.path.join(path, filename))
        if os.path.isfile(testname):
            return os.path.abspath(testname)

    raise IOError("File %r does not exist in any of the search paths: %r" %
                  (filename, path_dirs) )


class HomeDirError(Exception):
    pass


def get_home_dir(require_writable=False) -> str:
    """Return the 'home' directory, as a unicode string.

    Uses os.path.expanduser('~'), and checks for writability.

    See stdlib docs for how this is determined.
    For Python <3.8, $HOME is first priority on *ALL* platforms.
    For Python >=3.8 on Windows, %HOME% is no longer considered.

    Parameters
    ----------
    require_writable : bool [default: False]
        if True:
            guarantees the return value is a writable directory, otherwise
            raises HomeDirError
        if False:
            The path is resolved, but it is not guaranteed to exist or be writable.
    """

    homedir = os.path.expanduser('~')
    # Next line will make things work even when /home/ is a symlink to
    # /usr/home as it is on FreeBSD, for example
    homedir = os.path.realpath(homedir)

    if not _writable_dir(homedir) and os.name == 'nt':
        # expanduser failed, use the registry to get the 'My Documents' folder.
        try:
            import winreg as wreg
            with wreg.OpenKey(
                wreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
            ) as key:
                homedir = wreg.QueryValueEx(key,'Personal')[0]
        except:
            pass

    if (not require_writable) or _writable_dir(homedir):
        assert isinstance(homedir, str), "Homedir should be unicode not bytes"
        return homedir
    else:
        raise HomeDirError('%s is not a writable dir, '
                'set $HOME environment variable to override' % homedir)

def get_xdg_dir():
    """Return the XDG_CONFIG_HOME, if it is defined and exists, else None.

    This is only for non-OS X posix (Linux,Unix,etc.) systems.
    """

    env = os.environ

    if os.name == "posix":
        # Linux, Unix, AIX, etc.
        # use ~/.config if empty OR not set
        xdg = env.get("XDG_CONFIG_HOME", None) or os.path.join(get_home_dir(), '.config')
        if xdg and _writable_dir(xdg):
            assert isinstance(xdg, str)
            return xdg

    return None


def get_xdg_cache_dir():
    """Return the XDG_CACHE_HOME, if it is defined and exists, else None.

    This is only for non-OS X posix (Linux,Unix,etc.) systems.
    """

    env = os.environ

    if os.name == "posix":
        # Linux, Unix, AIX, etc.
        # use ~/.cache if empty OR not set
        xdg = env.get("XDG_CACHE_HOME", None) or os.path.join(get_home_dir(), '.cache')
        if xdg and _writable_dir(xdg):
            assert isinstance(xdg, str)
            return xdg

    return None


def expand_path(s):
    """Expand $VARS and ~names in a string, like a shell

    :Examples:

       In [2]: os.environ['FOO']='test'

       In [3]: expand_path('variable FOO is $FOO')
       Out[3]: 'variable FOO is test'
    """
    # This is a pretty subtle hack. When expand user is given a UNC path
    # on Windows (\\server\share$\%username%), os.path.expandvars, removes
    # the $ to get (\\server\share\%username%). I think it considered $
    # alone an empty var. But, we need the $ to remains there (it indicates
    # a hidden share).
    if os.name=='nt':
        s = s.replace('$\\', 'IPYTHON_TEMP')
    s = os.path.expandvars(os.path.expanduser(s))
    if os.name=='nt':
        s = s.replace('IPYTHON_TEMP', '$\\')
    return s


def unescape_glob(string):
    """Unescape glob pattern in `string`."""
    def unescape(s):
        for pattern in '*[]!?':
            s = s.replace(r'\{0}'.format(pattern), pattern)
        return s
    return '\\'.join(map(unescape, string.split('\\\\')))


def shellglob(args):
    """
    Do glob expansion for each element in `args` and return a flattened list.

    Unmatched glob pattern will remain as-is in the returned list.

    """
    expanded = []
    # Do not unescape backslash in Windows as it is interpreted as
    # path separator:
    unescape = unescape_glob if sys.platform != 'win32' else lambda x: x
    for a in args:
        expanded.extend(glob.glob(a) or [unescape(a)])
    return expanded

ENOLINK = 1998

def link(src, dst):
    """Hard links ``src`` to ``dst``, returning 0 or errno.

    Note that the special errno ``ENOLINK`` will be returned if ``os.link`` isn't
    supported by the operating system.
    """

    if not hasattr(os, "link"):
        return ENOLINK
    link_errno = 0
    try:
        os.link(src, dst)
    except OSError as e:
        link_errno = e.errno
    return link_errno


def link_or_copy(src, dst):
    """Attempts to hardlink ``src`` to ``dst``, copying if the link fails.

    Attempts to maintain the semantics of ``shutil.copy``.

    Because ``os.link`` does not overwrite files, a unique temporary file
    will be used if the target already exists, then that file will be moved
    into place.
    """

    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))

    link_errno = link(src, dst)
    if link_errno == errno.EEXIST:
        if os.stat(src).st_ino == os.stat(dst).st_ino:
            # dst is already a hard link to the correct file, so we don't need
            # to do anything else. If we try to link and rename the file
            # anyway, we get duplicate files - see http://bugs.python.org/issue21876
            return

        new_dst = dst + "-temp-%04X" %(random.randint(1, 16**4), )
        try:
            link_or_copy(src, new_dst)
        except:
            try:
                os.remove(new_dst)
            except OSError:
                pass
            raise
        os.rename(new_dst, dst)
    elif link_errno != 0:
        # Either link isn't supported, or the filesystem doesn't support
        # linking, or 'src' and 'dst' are on different filesystems.
        shutil.copy(src, dst)

def ensure_dir_exists(path, mode=0o755):
    """ensure that a directory exists

    If it doesn't exist, try to create it and protect against a race condition
    if another process is doing the same.

    The default permissions are 755, which differ from os.makedirs default of 777.
    """
    if not os.path.exists(path):
        try:
            os.makedirs(path, mode=mode)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
    elif not os.path.isdir(path):
        raise IOError("%r exists but is not a directory" % path)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\common_utils\callback_utils.py ===
from typing import Any, Dict, List, Optional

import litellm
from litellm import get_secret
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import CommonProxyErrors, LiteLLMPromptInjectionParams
from litellm.proxy.types_utils.utils import get_instance_fn

blue_color_code = "\033[94m"
reset_color_code = "\033[0m"


def initialize_callbacks_on_proxy(  # noqa: PLR0915
    value: Any,
    premium_user: bool,
    config_file_path: str,
    litellm_settings: dict,
    callback_specific_params: dict = {},
):
    from litellm.proxy.proxy_server import prisma_client

    verbose_proxy_logger.debug(
        f"{blue_color_code}initializing callbacks={value} on proxy{reset_color_code}"
    )
    if isinstance(value, list):
        imported_list: List[Any] = []
        for callback in value:  # ["presidio", <my-custom-callback>]
            if (
                isinstance(callback, str)
                and callback in litellm._known_custom_logger_compatible_callbacks
            ):
                imported_list.append(callback)
            elif isinstance(callback, str) and callback == "presidio":
                from litellm.proxy.guardrails.guardrail_hooks.presidio import (
                    _OPTIONAL_PresidioPIIMasking,
                )

                presidio_logging_only: Optional[bool] = litellm_settings.get(
                    "presidio_logging_only", None
                )
                if presidio_logging_only is not None:
                    presidio_logging_only = bool(
                        presidio_logging_only
                    )  # validate boolean given

                _presidio_params = {}
                if "presidio" in callback_specific_params and isinstance(
                    callback_specific_params["presidio"], dict
                ):
                    _presidio_params = callback_specific_params["presidio"]

                params: Dict[str, Any] = {
                    "logging_only": presidio_logging_only,
                    **_presidio_params,
                }
                pii_masking_object = _OPTIONAL_PresidioPIIMasking(**params)
                imported_list.append(pii_masking_object)
            elif isinstance(callback, str) and callback == "llamaguard_moderations":
                try:
                    from litellm_enterprise.enterprise_callbacks.llama_guard import (
                        _ENTERPRISE_LlamaGuard,
                    )
                except ImportError:
                    raise Exception(
                        "MissingTrying to use Llama Guard"
                        + CommonProxyErrors.missing_enterprise_package.value
                    )

                if premium_user is not True:
                    raise Exception(
                        "Trying to use Llama Guard"
                        + CommonProxyErrors.not_premium_user.value
                    )

                llama_guard_object = _ENTERPRISE_LlamaGuard()
                imported_list.append(llama_guard_object)
            elif isinstance(callback, str) and callback == "hide_secrets":
                try:
                    from litellm_enterprise.enterprise_callbacks.secret_detection import (
                        _ENTERPRISE_SecretDetection,
                    )
                except ImportError:
                    raise Exception(
                        "Trying to use Secret Detection"
                        + CommonProxyErrors.missing_enterprise_package.value
                    )

                if premium_user is not True:
                    raise Exception(
                        "Trying to use secret hiding"
                        + CommonProxyErrors.not_premium_user.value
                    )

                _secret_detection_object = _ENTERPRISE_SecretDetection()
                imported_list.append(_secret_detection_object)
            elif isinstance(callback, str) and callback == "openai_moderations":
                try:
                    from enterprise.enterprise_hooks.openai_moderation import (
                        _ENTERPRISE_OpenAI_Moderation,
                    )
                except ImportError:
                    raise Exception(
                        "Trying to use OpenAI Moderations Check,"
                        + CommonProxyErrors.missing_enterprise_package_docker.value
                    )

                if premium_user is not True:
                    raise Exception(
                        "Trying to use OpenAI Moderations Check"
                        + CommonProxyErrors.not_premium_user.value
                    )

                openai_moderations_object = _ENTERPRISE_OpenAI_Moderation()
                imported_list.append(openai_moderations_object)
            elif isinstance(callback, str) and callback == "lakera_prompt_injection":
                from litellm.proxy.guardrails.guardrail_hooks.lakera_ai import (
                    lakeraAI_Moderation,
                )

                init_params = {}
                if "lakera_prompt_injection" in callback_specific_params:
                    init_params = callback_specific_params["lakera_prompt_injection"]
                lakera_moderations_object = lakeraAI_Moderation(**init_params)
                imported_list.append(lakera_moderations_object)
            elif isinstance(callback, str) and callback == "aporia_prompt_injection":
                from litellm.proxy.guardrails.guardrail_hooks.aporia_ai import (
                    AporiaGuardrail,
                )

                aporia_guardrail_object = AporiaGuardrail()
                imported_list.append(aporia_guardrail_object)
            elif isinstance(callback, str) and callback == "google_text_moderation":
                try:
                    from enterprise.enterprise_hooks.google_text_moderation import (
                        _ENTERPRISE_GoogleTextModeration,
                    )
                except ImportError:
                    raise Exception(
                        "Trying to use Google Text Moderation,"
                        + CommonProxyErrors.missing_enterprise_package_docker.value
                    )

                if premium_user is not True:
                    raise Exception(
                        "Trying to use Google Text Moderation"
                        + CommonProxyErrors.not_premium_user.value
                    )

                google_text_moderation_obj = _ENTERPRISE_GoogleTextModeration()
                imported_list.append(google_text_moderation_obj)
            elif isinstance(callback, str) and callback == "llmguard_moderations":
                try:
                    from litellm_enterprise.enterprise_callbacks.llm_guard import (
                        _ENTERPRISE_LLMGuard,
                    )
                except ImportError:
                    raise Exception(
                        "Trying to use Llm Guard"
                        + CommonProxyErrors.missing_enterprise_package.value
                    )

                if premium_user is not True:
                    raise Exception(
                        "Trying to use Llm Guard"
                        + CommonProxyErrors.not_premium_user.value
                    )

                llm_guard_moderation_obj = _ENTERPRISE_LLMGuard()
                imported_list.append(llm_guard_moderation_obj)
            elif isinstance(callback, str) and callback == "blocked_user_check":
                try:
                    from enterprise.enterprise_hooks.blocked_user_list import (
                        _ENTERPRISE_BlockedUserList,
                    )
                except ImportError:
                    raise Exception(
                        "Trying to use Blocked User List"
                        + CommonProxyErrors.missing_enterprise_package_docker.value
                    )

                if premium_user is not True:
                    raise Exception(
                        "Trying to use ENTERPRISE BlockedUser"
                        + CommonProxyErrors.not_premium_user.value
                    )

                blocked_user_list = _ENTERPRISE_BlockedUserList(
                    prisma_client=prisma_client
                )
                imported_list.append(blocked_user_list)
            elif isinstance(callback, str) and callback == "banned_keywords":
                try:
                    from enterprise.enterprise_hooks.banned_keywords import (
                        _ENTERPRISE_BannedKeywords,
                    )
                except ImportError:
                    raise Exception(
                        "Trying to use Banned Keywords"
                        + CommonProxyErrors.missing_enterprise_package_docker.value
                    )

                if premium_user is not True:
                    raise Exception(
                        "Trying to use ENTERPRISE BannedKeyword"
                        + CommonProxyErrors.not_premium_user.value
                    )

                banned_keywords_obj = _ENTERPRISE_BannedKeywords()
                imported_list.append(banned_keywords_obj)
            elif isinstance(callback, str) and callback == "detect_prompt_injection":
                from litellm.proxy.hooks.prompt_injection_detection import (
                    _OPTIONAL_PromptInjectionDetection,
                )

                prompt_injection_params = None
                if "prompt_injection_params" in litellm_settings:
                    prompt_injection_params_in_config = litellm_settings[
                        "prompt_injection_params"
                    ]
                    prompt_injection_params = LiteLLMPromptInjectionParams(
                        **prompt_injection_params_in_config
                    )

                prompt_injection_detection_obj = _OPTIONAL_PromptInjectionDetection(
                    prompt_injection_params=prompt_injection_params,
                )
                imported_list.append(prompt_injection_detection_obj)
            elif isinstance(callback, str) and callback == "batch_redis_requests":
                from litellm.proxy.hooks.batch_redis_get import (
                    _PROXY_BatchRedisRequests,
                )

                batch_redis_obj = _PROXY_BatchRedisRequests()
                imported_list.append(batch_redis_obj)
            elif isinstance(callback, str) and callback == "azure_content_safety":
                from litellm.proxy.hooks.azure_content_safety import (
                    _PROXY_AzureContentSafety,
                )

                azure_content_safety_params = litellm_settings[
                    "azure_content_safety_params"
                ]
                for k, v in azure_content_safety_params.items():
                    if (
                        v is not None
                        and isinstance(v, str)
                        and v.startswith("os.environ/")
                    ):
                        azure_content_safety_params[k] = get_secret(v)

                azure_content_safety_obj = _PROXY_AzureContentSafety(
                    **azure_content_safety_params,
                )
                imported_list.append(azure_content_safety_obj)
            else:
                verbose_proxy_logger.debug(
                    f"{blue_color_code} attempting to import custom calback={callback} {reset_color_code}"
                )
                imported_list.append(
                    get_instance_fn(
                        value=callback,
                        config_file_path=config_file_path,
                    )
                )
        if isinstance(litellm.callbacks, list):
            litellm.callbacks.extend(imported_list)
        else:
            litellm.callbacks = imported_list  # type: ignore

        if "prometheus" in value:
            from litellm.integrations.prometheus import PrometheusLogger

            PrometheusLogger._mount_metrics_endpoint(premium_user)
    else:
        litellm.callbacks = [
            get_instance_fn(
                value=value,
                config_file_path=config_file_path,
            )
        ]
    verbose_proxy_logger.debug(
        f"{blue_color_code} Initialized Callbacks - {litellm.callbacks} {reset_color_code}"
    )


def get_model_group_from_litellm_kwargs(kwargs: dict) -> Optional[str]:
    _litellm_params = kwargs.get("litellm_params", None) or {}
    _metadata = _litellm_params.get("metadata", None) or {}
    _model_group = _metadata.get("model_group", None)
    if _model_group is not None:
        return _model_group

    return None


def get_model_group_from_request_data(data: dict) -> Optional[str]:
    _metadata = data.get("metadata", None) or {}
    _model_group = _metadata.get("model_group", None)
    if _model_group is not None:
        return _model_group

    return None


def get_remaining_tokens_and_requests_from_request_data(data: Dict) -> Dict[str, str]:
    """
    Helper function to return x-litellm-key-remaining-tokens-{model_group} and x-litellm-key-remaining-requests-{model_group}

    Returns {} when api_key + model rpm/tpm limit is not set

    """
    headers = {}
    _metadata = data.get("metadata", None) or {}
    model_group = get_model_group_from_request_data(data)

    # Remaining Requests
    remaining_requests_variable_name = f"litellm-key-remaining-requests-{model_group}"
    remaining_requests = _metadata.get(remaining_requests_variable_name, None)
    if remaining_requests:
        headers[f"x-litellm-key-remaining-requests-{model_group}"] = remaining_requests

    # Remaining Tokens
    remaining_tokens_variable_name = f"litellm-key-remaining-tokens-{model_group}"
    remaining_tokens = _metadata.get(remaining_tokens_variable_name, None)
    if remaining_tokens:
        headers[f"x-litellm-key-remaining-tokens-{model_group}"] = remaining_tokens

    return headers


def get_logging_caching_headers(request_data: Dict) -> Optional[Dict]:
    _metadata = request_data.get("metadata", None) or {}
    headers = {}
    if "applied_guardrails" in _metadata:
        headers["x-litellm-applied-guardrails"] = ",".join(
            _metadata["applied_guardrails"]
        )

    if "semantic-similarity" in _metadata:
        headers["x-litellm-semantic-similarity"] = str(_metadata["semantic-similarity"])

    return headers


def add_guardrail_to_applied_guardrails_header(
    request_data: Dict, guardrail_name: Optional[str]
):
    if guardrail_name is None:
        return
    _metadata = request_data.get("metadata", None) or {}
    if "applied_guardrails" in _metadata:
        _metadata["applied_guardrails"].append(guardrail_name)
    else:
        _metadata["applied_guardrails"] = [guardrail_name]

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\ipipan.py ===
# Natural Language Toolkit: IPI PAN Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Konrad Goluchowski <kodie@mimuw.edu.pl>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import functools

from nltk.corpus.reader.api import CorpusReader
from nltk.corpus.reader.util import StreamBackedCorpusView, concat


def _parse_args(fun):
    @functools.wraps(fun)
    def decorator(self, fileids=None, **kwargs):
        kwargs.pop("tags", None)
        if not fileids:
            fileids = self.fileids()
        return fun(self, fileids, **kwargs)

    return decorator


class IPIPANCorpusReader(CorpusReader):
    """
    Corpus reader designed to work with corpus created by IPI PAN.
    See http://korpus.pl/en/ for more details about IPI PAN corpus.

    The corpus includes information about text domain, channel and categories.
    You can access possible values using ``domains()``, ``channels()`` and
    ``categories()``. You can use also this metadata to filter files, e.g.:
    ``fileids(channel='prasa')``, ``fileids(categories='publicystyczny')``.

    The reader supports methods: words, sents, paras and their tagged versions.
    You can get part of speech instead of full tag by giving "simplify_tags=True"
    parameter, e.g.: ``tagged_sents(simplify_tags=True)``.

    Also you can get all tags disambiguated tags specifying parameter
    "one_tag=False", e.g.: ``tagged_paras(one_tag=False)``.

    You can get all tags that were assigned by a morphological analyzer specifying
    parameter "disamb_only=False", e.g. ``tagged_words(disamb_only=False)``.

    The IPIPAN Corpus contains tags indicating if there is a space between two
    tokens. To add special "no space" markers, you should specify parameter
    "append_no_space=True", e.g. ``tagged_words(append_no_space=True)``.
    As a result in place where there should be no space between two tokens new
    pair ('', 'no-space') will be inserted (for tagged data) and just '' for
    methods without tags.

    The corpus reader can also try to append spaces between words. To enable this
    option, specify parameter "append_space=True", e.g. ``words(append_space=True)``.
    As a result either ' ' or (' ', 'space') will be inserted between tokens.

    By default, xml entities like &quot; and &amp; are replaced by corresponding
    characters. You can turn off this feature, specifying parameter
    "replace_xmlentities=False", e.g. ``words(replace_xmlentities=False)``.
    """

    def __init__(self, root, fileids):
        CorpusReader.__init__(self, root, fileids, None, None)

    def channels(self, fileids=None):
        if not fileids:
            fileids = self.fileids()
        return self._parse_header(fileids, "channel")

    def domains(self, fileids=None):
        if not fileids:
            fileids = self.fileids()
        return self._parse_header(fileids, "domain")

    def categories(self, fileids=None):
        if not fileids:
            fileids = self.fileids()
        return [
            self._map_category(cat) for cat in self._parse_header(fileids, "keyTerm")
        ]

    def fileids(self, channels=None, domains=None, categories=None):
        if channels is not None and domains is not None and categories is not None:
            raise ValueError(
                "You can specify only one of channels, domains "
                "and categories parameter at once"
            )
        if channels is None and domains is None and categories is None:
            return CorpusReader.fileids(self)
        if isinstance(channels, str):
            channels = [channels]
        if isinstance(domains, str):
            domains = [domains]
        if isinstance(categories, str):
            categories = [categories]
        if channels:
            return self._list_morph_files_by("channel", channels)
        elif domains:
            return self._list_morph_files_by("domain", domains)
        else:
            return self._list_morph_files_by(
                "keyTerm", categories, map=self._map_category
            )

    @_parse_args
    def sents(self, fileids=None, **kwargs):
        return concat(
            [
                self._view(
                    fileid, mode=IPIPANCorpusView.SENTS_MODE, tags=False, **kwargs
                )
                for fileid in self._list_morph_files(fileids)
            ]
        )

    @_parse_args
    def paras(self, fileids=None, **kwargs):
        return concat(
            [
                self._view(
                    fileid, mode=IPIPANCorpusView.PARAS_MODE, tags=False, **kwargs
                )
                for fileid in self._list_morph_files(fileids)
            ]
        )

    @_parse_args
    def words(self, fileids=None, **kwargs):
        return concat(
            [
                self._view(fileid, tags=False, **kwargs)
                for fileid in self._list_morph_files(fileids)
            ]
        )

    @_parse_args
    def tagged_sents(self, fileids=None, **kwargs):
        return concat(
            [
                self._view(fileid, mode=IPIPANCorpusView.SENTS_MODE, **kwargs)
                for fileid in self._list_morph_files(fileids)
            ]
        )

    @_parse_args
    def tagged_paras(self, fileids=None, **kwargs):
        return concat(
            [
                self._view(fileid, mode=IPIPANCorpusView.PARAS_MODE, **kwargs)
                for fileid in self._list_morph_files(fileids)
            ]
        )

    @_parse_args
    def tagged_words(self, fileids=None, **kwargs):
        return concat(
            [self._view(fileid, **kwargs) for fileid in self._list_morph_files(fileids)]
        )

    def _list_morph_files(self, fileids):
        return [f for f in self.abspaths(fileids)]

    def _list_header_files(self, fileids):
        return [
            f.replace("morph.xml", "header.xml")
            for f in self._list_morph_files(fileids)
        ]

    def _parse_header(self, fileids, tag):
        values = set()
        for f in self._list_header_files(fileids):
            values_list = self._get_tag(f, tag)
            for v in values_list:
                values.add(v)
        return list(values)

    def _list_morph_files_by(self, tag, values, map=None):
        fileids = self.fileids()
        ret_fileids = set()
        for f in fileids:
            fp = self.abspath(f).replace("morph.xml", "header.xml")
            values_list = self._get_tag(fp, tag)
            for value in values_list:
                if map is not None:
                    value = map(value)
                if value in values:
                    ret_fileids.add(f)
        return list(ret_fileids)

    def _get_tag(self, f, tag):
        tags = []
        with open(f) as infile:
            header = infile.read()
        tag_end = 0
        while True:
            tag_pos = header.find("<" + tag, tag_end)
            if tag_pos < 0:
                return tags
            tag_end = header.find("</" + tag + ">", tag_pos)
            tags.append(header[tag_pos + len(tag) + 2 : tag_end])

    def _map_category(self, cat):
        pos = cat.find(">")
        if pos == -1:
            return cat
        else:
            return cat[pos + 1 :]

    def _view(self, filename, **kwargs):
        tags = kwargs.pop("tags", True)
        mode = kwargs.pop("mode", 0)
        simplify_tags = kwargs.pop("simplify_tags", False)
        one_tag = kwargs.pop("one_tag", True)
        disamb_only = kwargs.pop("disamb_only", True)
        append_no_space = kwargs.pop("append_no_space", False)
        append_space = kwargs.pop("append_space", False)
        replace_xmlentities = kwargs.pop("replace_xmlentities", True)

        if len(kwargs) > 0:
            raise ValueError("Unexpected arguments: %s" % kwargs.keys())
        if not one_tag and not disamb_only:
            raise ValueError(
                "You cannot specify both one_tag=False and " "disamb_only=False"
            )
        if not tags and (simplify_tags or not one_tag or not disamb_only):
            raise ValueError(
                "You cannot specify simplify_tags, one_tag or "
                "disamb_only with functions other than tagged_*"
            )

        return IPIPANCorpusView(
            filename,
            tags=tags,
            mode=mode,
            simplify_tags=simplify_tags,
            one_tag=one_tag,
            disamb_only=disamb_only,
            append_no_space=append_no_space,
            append_space=append_space,
            replace_xmlentities=replace_xmlentities,
        )


class IPIPANCorpusView(StreamBackedCorpusView):
    WORDS_MODE = 0
    SENTS_MODE = 1
    PARAS_MODE = 2

    def __init__(self, filename, startpos=0, **kwargs):
        StreamBackedCorpusView.__init__(self, filename, None, startpos, None)
        self.in_sentence = False
        self.position = 0

        self.show_tags = kwargs.pop("tags", True)
        self.disamb_only = kwargs.pop("disamb_only", True)
        self.mode = kwargs.pop("mode", IPIPANCorpusView.WORDS_MODE)
        self.simplify_tags = kwargs.pop("simplify_tags", False)
        self.one_tag = kwargs.pop("one_tag", True)
        self.append_no_space = kwargs.pop("append_no_space", False)
        self.append_space = kwargs.pop("append_space", False)
        self.replace_xmlentities = kwargs.pop("replace_xmlentities", True)

    def read_block(self, stream):
        sentence = []
        sentences = []
        space = False
        no_space = False

        tags = set()

        lines = self._read_data(stream)

        while True:
            # we may have only part of last line
            if len(lines) <= 1:
                self._seek(stream)
                lines = self._read_data(stream)

            if lines == [""]:
                assert not sentences
                return []

            line = lines.pop()
            self.position += len(line) + 1

            if line.startswith('<chunk type="s"'):
                self.in_sentence = True
            elif line.startswith('<chunk type="p"'):
                pass
            elif line.startswith("<tok"):
                if self.append_space and space and not no_space:
                    self._append_space(sentence)
                space = True
                no_space = False
                orth = ""
                tags = set()
            elif line.startswith("</chunk"):
                if self.in_sentence:
                    self.in_sentence = False
                    self._seek(stream)
                    if self.mode == self.SENTS_MODE:
                        return [sentence]
                    elif self.mode == self.WORDS_MODE:
                        if self.append_space:
                            self._append_space(sentence)
                        return sentence
                    else:
                        sentences.append(sentence)
                elif self.mode == self.PARAS_MODE:
                    self._seek(stream)
                    return [sentences]
            elif line.startswith("<orth"):
                orth = line[6:-7]
                if self.replace_xmlentities:
                    orth = orth.replace("&quot;", '"').replace("&amp;", "&")
            elif line.startswith("<lex"):
                if not self.disamb_only or line.find("disamb=") != -1:
                    tag = line[line.index("<ctag") + 6 : line.index("</ctag")]
                    tags.add(tag)
            elif line.startswith("</tok"):
                if self.show_tags:
                    if self.simplify_tags:
                        tags = [t.split(":")[0] for t in tags]
                    if not self.one_tag or not self.disamb_only:
                        sentence.append((orth, tuple(tags)))
                    else:
                        sentence.append((orth, tags.pop()))
                else:
                    sentence.append(orth)
            elif line.startswith("<ns/>"):
                if self.append_space:
                    no_space = True
                if self.append_no_space:
                    if self.show_tags:
                        sentence.append(("", "no-space"))
                    else:
                        sentence.append("")
            elif line.startswith("</cesAna"):
                pass

    def _read_data(self, stream):
        self.position = stream.tell()
        buff = stream.read(4096)
        lines = buff.split("\n")
        lines.reverse()
        return lines

    def _seek(self, stream):
        stream.seek(self.position)

    def _append_space(self, sentence):
        if self.show_tags:
            sentence.append((" ", "space"))
        else:
            sentence.append(" ")

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\tagged.py ===
# Natural Language Toolkit: Tagged Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
#         Jacob Perkins <japerk@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A reader for corpora whose documents contain part-of-speech-tagged words.
"""

import os

from nltk.corpus.reader.api import *
from nltk.corpus.reader.timit import read_timit_block
from nltk.corpus.reader.util import *
from nltk.tag import map_tag, str2tuple
from nltk.tokenize import *


class TaggedCorpusReader(CorpusReader):
    """
    Reader for simple part-of-speech tagged corpora.  Paragraphs are
    assumed to be split using blank lines.  Sentences and words can be
    tokenized using the default tokenizers, or by custom tokenizers
    specified as parameters to the constructor.  Words are parsed
    using ``nltk.tag.str2tuple``.  By default, ``'/'`` is used as the
    separator.  I.e., words should have the form::

       word1/tag1 word2/tag2 word3/tag3 ...

    But custom separators may be specified as parameters to the
    constructor.  Part of speech tags are case-normalized to upper
    case.
    """

    def __init__(
        self,
        root,
        fileids,
        sep="/",
        word_tokenizer=WhitespaceTokenizer(),
        sent_tokenizer=RegexpTokenizer("\n", gaps=True),
        para_block_reader=read_blankline_block,
        encoding="utf8",
        tagset=None,
    ):
        """
        Construct a new Tagged Corpus reader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/...path to corpus.../'
            >>> reader = TaggedCorpusReader(root, '.*', '.txt') # doctest: +SKIP

        :param root: The root directory for this corpus.
        :param fileids: A list or regexp specifying the fileids in this corpus.
        """
        CorpusReader.__init__(self, root, fileids, encoding)
        self._sep = sep
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        self._para_block_reader = para_block_reader
        self._tagset = tagset

    def words(self, fileids=None):
        """
        :return: the given file(s) as a list of words
            and punctuation symbols.
        :rtype: list(str)
        """
        return concat(
            [
                TaggedCorpusView(
                    fileid,
                    enc,
                    False,
                    False,
                    False,
                    self._sep,
                    self._word_tokenizer,
                    self._sent_tokenizer,
                    self._para_block_reader,
                    None,
                )
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def sents(self, fileids=None):
        """
        :return: the given file(s) as a list of
            sentences or utterances, each encoded as a list of word
            strings.
        :rtype: list(list(str))
        """
        return concat(
            [
                TaggedCorpusView(
                    fileid,
                    enc,
                    False,
                    True,
                    False,
                    self._sep,
                    self._word_tokenizer,
                    self._sent_tokenizer,
                    self._para_block_reader,
                    None,
                )
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def paras(self, fileids=None):
        """
        :return: the given file(s) as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of word strings.
        :rtype: list(list(list(str)))
        """
        return concat(
            [
                TaggedCorpusView(
                    fileid,
                    enc,
                    False,
                    True,
                    True,
                    self._sep,
                    self._word_tokenizer,
                    self._sent_tokenizer,
                    self._para_block_reader,
                    None,
                )
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def tagged_words(self, fileids=None, tagset=None):
        """
        :return: the given file(s) as a list of tagged
            words and punctuation symbols, encoded as tuples
            ``(word,tag)``.
        :rtype: list(tuple(str,str))
        """
        if tagset and tagset != self._tagset:
            tag_mapping_function = lambda t: map_tag(self._tagset, tagset, t)
        else:
            tag_mapping_function = None
        return concat(
            [
                TaggedCorpusView(
                    fileid,
                    enc,
                    True,
                    False,
                    False,
                    self._sep,
                    self._word_tokenizer,
                    self._sent_tokenizer,
                    self._para_block_reader,
                    tag_mapping_function,
                )
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def tagged_sents(self, fileids=None, tagset=None):
        """
        :return: the given file(s) as a list of
            sentences, each encoded as a list of ``(word,tag)`` tuples.

        :rtype: list(list(tuple(str,str)))
        """
        if tagset and tagset != self._tagset:
            tag_mapping_function = lambda t: map_tag(self._tagset, tagset, t)
        else:
            tag_mapping_function = None
        return concat(
            [
                TaggedCorpusView(
                    fileid,
                    enc,
                    True,
                    True,
                    False,
                    self._sep,
                    self._word_tokenizer,
                    self._sent_tokenizer,
                    self._para_block_reader,
                    tag_mapping_function,
                )
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )

    def tagged_paras(self, fileids=None, tagset=None):
        """
        :return: the given file(s) as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of ``(word,tag)`` tuples.
        :rtype: list(list(list(tuple(str,str))))
        """
        if tagset and tagset != self._tagset:
            tag_mapping_function = lambda t: map_tag(self._tagset, tagset, t)
        else:
            tag_mapping_function = None
        return concat(
            [
                TaggedCorpusView(
                    fileid,
                    enc,
                    True,
                    True,
                    True,
                    self._sep,
                    self._word_tokenizer,
                    self._sent_tokenizer,
                    self._para_block_reader,
                    tag_mapping_function,
                )
                for (fileid, enc) in self.abspaths(fileids, True)
            ]
        )


class CategorizedTaggedCorpusReader(CategorizedCorpusReader, TaggedCorpusReader):
    """
    A reader for part-of-speech tagged corpora whose documents are
    divided into categories based on their file identifiers.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the corpus reader.  Categorization arguments
        (``cat_pattern``, ``cat_map``, and ``cat_file``) are passed to
        the ``CategorizedCorpusReader`` constructor.  The remaining arguments
        are passed to the ``TaggedCorpusReader``.
        """
        CategorizedCorpusReader.__init__(self, kwargs)
        TaggedCorpusReader.__init__(self, *args, **kwargs)

    def tagged_words(self, fileids=None, categories=None, tagset=None):
        return super().tagged_words(self._resolve(fileids, categories), tagset)

    def tagged_sents(self, fileids=None, categories=None, tagset=None):
        return super().tagged_sents(self._resolve(fileids, categories), tagset)

    def tagged_paras(self, fileids=None, categories=None, tagset=None):
        return super().tagged_paras(self._resolve(fileids, categories), tagset)


class TaggedCorpusView(StreamBackedCorpusView):
    """
    A specialized corpus view for tagged documents.  It can be
    customized via flags to divide the tagged corpus documents up by
    sentence or paragraph, and to include or omit part of speech tags.
    ``TaggedCorpusView`` objects are typically created by
    ``TaggedCorpusReader`` (not directly by nltk users).
    """

    def __init__(
        self,
        corpus_file,
        encoding,
        tagged,
        group_by_sent,
        group_by_para,
        sep,
        word_tokenizer,
        sent_tokenizer,
        para_block_reader,
        tag_mapping_function=None,
    ):
        self._tagged = tagged
        self._group_by_sent = group_by_sent
        self._group_by_para = group_by_para
        self._sep = sep
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        self._para_block_reader = para_block_reader
        self._tag_mapping_function = tag_mapping_function
        StreamBackedCorpusView.__init__(self, corpus_file, encoding=encoding)

    def read_block(self, stream):
        """Reads one paragraph at a time."""
        block = []
        for para_str in self._para_block_reader(stream):
            para = []
            for sent_str in self._sent_tokenizer.tokenize(para_str):
                sent = [
                    str2tuple(s, self._sep)
                    for s in self._word_tokenizer.tokenize(sent_str)
                ]
                if self._tag_mapping_function:
                    sent = [(w, self._tag_mapping_function(t)) for (w, t) in sent]
                if not self._tagged:
                    sent = [w for (w, t) in sent]
                if self._group_by_sent:
                    para.append(sent)
                else:
                    para.extend(sent)
            if self._group_by_para:
                block.append(para)
            else:
                block.extend(para)
        return block


# needs to implement simplified tags
class MacMorphoCorpusReader(TaggedCorpusReader):
    """
    A corpus reader for the MAC_MORPHO corpus.  Each line contains a
    single tagged word, using '_' as a separator.  Sentence boundaries
    are based on the end-sentence tag ('_.').  Paragraph information
    is not included in the corpus, so each paragraph returned by
    ``self.paras()`` and ``self.tagged_paras()`` contains a single
    sentence.
    """

    def __init__(self, root, fileids, encoding="utf8", tagset=None):
        TaggedCorpusReader.__init__(
            self,
            root,
            fileids,
            sep="_",
            word_tokenizer=LineTokenizer(),
            sent_tokenizer=RegexpTokenizer(".*\n"),
            para_block_reader=self._read_block,
            encoding=encoding,
            tagset=tagset,
        )

    def _read_block(self, stream):
        return read_regexp_block(stream, r".*", r".*_\.")


class TimitTaggedCorpusReader(TaggedCorpusReader):
    """
    A corpus reader for tagged sentences that are included in the TIMIT corpus.
    """

    def __init__(self, *args, **kwargs):
        TaggedCorpusReader.__init__(
            self, para_block_reader=read_timit_block, *args, **kwargs
        )

    def paras(self):
        raise NotImplementedError("use sents() instead")

    def tagged_paras(self):
        raise NotImplementedError("use tagged_sents() instead")

# === NexusCore/openenv\Lib\site-packages\pip\_internal\wheel_builder.py ===
"""Orchestrator for building wheels from InstallRequirements.
"""

import logging
import os.path
import re
import shutil
from typing import Iterable, List, Optional, Tuple

from pip._vendor.packaging.utils import canonicalize_name, canonicalize_version
from pip._vendor.packaging.version import InvalidVersion, Version

from pip._internal.cache import WheelCache
from pip._internal.exceptions import InvalidWheelFilename, UnsupportedWheel
from pip._internal.metadata import FilesystemWheel, get_wheel_distribution
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.operations.build.wheel import build_wheel_pep517
from pip._internal.operations.build.wheel_editable import build_wheel_editable
from pip._internal.operations.build.wheel_legacy import build_wheel_legacy
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.logging import indent_log
from pip._internal.utils.misc import ensure_dir, hash_file
from pip._internal.utils.setuptools_build import make_setuptools_clean_args
from pip._internal.utils.subprocess import call_subprocess
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.urls import path_to_url
from pip._internal.vcs import vcs

logger = logging.getLogger(__name__)

_egg_info_re = re.compile(r"([a-z0-9_.]+)-([a-z0-9_.!+-]+)", re.IGNORECASE)

BuildResult = Tuple[List[InstallRequirement], List[InstallRequirement]]


def _contains_egg_info(s: str) -> bool:
    """Determine whether the string looks like an egg_info.

    :param s: The string to parse. E.g. foo-2.1
    """
    return bool(_egg_info_re.search(s))


def _should_build(
    req: InstallRequirement,
    need_wheel: bool,
) -> bool:
    """Return whether an InstallRequirement should be built into a wheel."""
    if req.constraint:
        # never build requirements that are merely constraints
        return False
    if req.is_wheel:
        if need_wheel:
            logger.info(
                "Skipping %s, due to already being wheel.",
                req.name,
            )
        return False

    if need_wheel:
        # i.e. pip wheel, not pip install
        return True

    # From this point, this concerns the pip install command only
    # (need_wheel=False).

    if not req.source_dir:
        return False

    if req.editable:
        # we only build PEP 660 editable requirements
        return req.supports_pyproject_editable

    return True


def should_build_for_wheel_command(
    req: InstallRequirement,
) -> bool:
    return _should_build(req, need_wheel=True)


def should_build_for_install_command(
    req: InstallRequirement,
) -> bool:
    return _should_build(req, need_wheel=False)


def _should_cache(
    req: InstallRequirement,
) -> Optional[bool]:
    """
    Return whether a built InstallRequirement can be stored in the persistent
    wheel cache, assuming the wheel cache is available, and _should_build()
    has determined a wheel needs to be built.
    """
    if req.editable or not req.source_dir:
        # never cache editable requirements
        return False

    if req.link and req.link.is_vcs:
        # VCS checkout. Do not cache
        # unless it points to an immutable commit hash.
        assert not req.editable
        assert req.source_dir
        vcs_backend = vcs.get_backend_for_scheme(req.link.scheme)
        assert vcs_backend
        if vcs_backend.is_immutable_rev_checkout(req.link.url, req.source_dir):
            return True
        return False

    assert req.link
    base, ext = req.link.splitext()
    if _contains_egg_info(base):
        return True

    # Otherwise, do not cache.
    return False


def _get_cache_dir(
    req: InstallRequirement,
    wheel_cache: WheelCache,
) -> str:
    """Return the persistent or temporary cache directory where the built
    wheel need to be stored.
    """
    cache_available = bool(wheel_cache.cache_dir)
    assert req.link
    if cache_available and _should_cache(req):
        cache_dir = wheel_cache.get_path_for_link(req.link)
    else:
        cache_dir = wheel_cache.get_ephem_path_for_link(req.link)
    return cache_dir


def _verify_one(req: InstallRequirement, wheel_path: str) -> None:
    canonical_name = canonicalize_name(req.name or "")
    w = Wheel(os.path.basename(wheel_path))
    if canonicalize_name(w.name) != canonical_name:
        raise InvalidWheelFilename(
            f"Wheel has unexpected file name: expected {canonical_name!r}, "
            f"got {w.name!r}",
        )
    dist = get_wheel_distribution(FilesystemWheel(wheel_path), canonical_name)
    dist_verstr = str(dist.version)
    if canonicalize_version(dist_verstr) != canonicalize_version(w.version):
        raise InvalidWheelFilename(
            f"Wheel has unexpected file name: expected {dist_verstr!r}, "
            f"got {w.version!r}",
        )
    metadata_version_value = dist.metadata_version
    if metadata_version_value is None:
        raise UnsupportedWheel("Missing Metadata-Version")
    try:
        metadata_version = Version(metadata_version_value)
    except InvalidVersion:
        msg = f"Invalid Metadata-Version: {metadata_version_value}"
        raise UnsupportedWheel(msg)
    if metadata_version >= Version("1.2") and not isinstance(dist.version, Version):
        raise UnsupportedWheel(
            f"Metadata 1.2 mandates PEP 440 version, but {dist_verstr!r} is not"
        )


def _build_one(
    req: InstallRequirement,
    output_dir: str,
    verify: bool,
    build_options: List[str],
    global_options: List[str],
    editable: bool,
) -> Optional[str]:
    """Build one wheel.

    :return: The filename of the built wheel, or None if the build failed.
    """
    artifact = "editable" if editable else "wheel"
    try:
        ensure_dir(output_dir)
    except OSError as e:
        logger.warning(
            "Building %s for %s failed: %s",
            artifact,
            req.name,
            e,
        )
        return None

    # Install build deps into temporary directory (PEP 518)
    with req.build_env:
        wheel_path = _build_one_inside_env(
            req, output_dir, build_options, global_options, editable
        )
    if wheel_path and verify:
        try:
            _verify_one(req, wheel_path)
        except (InvalidWheelFilename, UnsupportedWheel) as e:
            logger.warning("Built %s for %s is invalid: %s", artifact, req.name, e)
            return None
    return wheel_path


def _build_one_inside_env(
    req: InstallRequirement,
    output_dir: str,
    build_options: List[str],
    global_options: List[str],
    editable: bool,
) -> Optional[str]:
    with TempDirectory(kind="wheel") as temp_dir:
        assert req.name
        if req.use_pep517:
            assert req.metadata_directory
            assert req.pep517_backend
            if global_options:
                logger.warning(
                    "Ignoring --global-option when building %s using PEP 517", req.name
                )
            if build_options:
                logger.warning(
                    "Ignoring --build-option when building %s using PEP 517", req.name
                )
            if editable:
                wheel_path = build_wheel_editable(
                    name=req.name,
                    backend=req.pep517_backend,
                    metadata_directory=req.metadata_directory,
                    tempd=temp_dir.path,
                )
            else:
                wheel_path = build_wheel_pep517(
                    name=req.name,
                    backend=req.pep517_backend,
                    metadata_directory=req.metadata_directory,
                    tempd=temp_dir.path,
                )
        else:
            wheel_path = build_wheel_legacy(
                name=req.name,
                setup_py_path=req.setup_py_path,
                source_dir=req.unpacked_source_directory,
                global_options=global_options,
                build_options=build_options,
                tempd=temp_dir.path,
            )

        if wheel_path is not None:
            wheel_name = os.path.basename(wheel_path)
            dest_path = os.path.join(output_dir, wheel_name)
            try:
                wheel_hash, length = hash_file(wheel_path)
                shutil.move(wheel_path, dest_path)
                logger.info(
                    "Created wheel for %s: filename=%s size=%d sha256=%s",
                    req.name,
                    wheel_name,
                    length,
                    wheel_hash.hexdigest(),
                )
                logger.info("Stored in directory: %s", output_dir)
                return dest_path
            except Exception as e:
                logger.warning(
                    "Building wheel for %s failed: %s",
                    req.name,
                    e,
                )
        # Ignore return, we can't do anything else useful.
        if not req.use_pep517:
            _clean_one_legacy(req, global_options)
        return None


def _clean_one_legacy(req: InstallRequirement, global_options: List[str]) -> bool:
    clean_args = make_setuptools_clean_args(
        req.setup_py_path,
        global_options=global_options,
    )

    logger.info("Running setup.py clean for %s", req.name)
    try:
        call_subprocess(
            clean_args, command_desc="python setup.py clean", cwd=req.source_dir
        )
        return True
    except Exception:
        logger.error("Failed cleaning build dir for %s", req.name)
        return False


def build(
    requirements: Iterable[InstallRequirement],
    wheel_cache: WheelCache,
    verify: bool,
    build_options: List[str],
    global_options: List[str],
) -> BuildResult:
    """Build wheels.

    :return: The list of InstallRequirement that succeeded to build and
        the list of InstallRequirement that failed to build.
    """
    if not requirements:
        return [], []

    # Build the wheels.
    logger.info(
        "Building wheels for collected packages: %s",
        ", ".join(req.name for req in requirements),  # type: ignore
    )

    with indent_log():
        build_successes, build_failures = [], []
        for req in requirements:
            assert req.name
            cache_dir = _get_cache_dir(req, wheel_cache)
            wheel_file = _build_one(
                req,
                cache_dir,
                verify,
                build_options,
                global_options,
                req.editable and req.permit_editable_wheels,
            )
            if wheel_file:
                # Record the download origin in the cache
                if req.download_info is not None:
                    # download_info is guaranteed to be set because when we build an
                    # InstallRequirement it has been through the preparer before, but
                    # let's be cautious.
                    wheel_cache.record_download_origin(cache_dir, req.download_info)
                # Update the link for this.
                req.link = Link(path_to_url(wheel_file))
                req.local_file_path = req.link.file_path
                assert req.link.is_wheel
                build_successes.append(req)
            else:
                build_failures.append(req)

    # notify success/failure
    if build_successes:
        logger.info(
            "Successfully built %s",
            " ".join([req.name for req in build_successes]),  # type: ignore
        )
    if build_failures:
        logger.info(
            "Failed to build %s",
            " ".join([req.name for req in build_failures]),  # type: ignore
        )
    # Return a list of requirements that failed to build
    return build_successes, build_failures

# === NexusCore/openenv\Lib\site-packages\pip\_internal\utils\logging.py ===
import contextlib
import errno
import logging
import logging.handlers
import os
import sys
import threading
from dataclasses import dataclass
from io import TextIOWrapper
from logging import Filter
from typing import Any, ClassVar, Generator, List, Optional, TextIO, Type

from pip._vendor.rich.console import (
    Console,
    ConsoleOptions,
    ConsoleRenderable,
    RenderableType,
    RenderResult,
    RichCast,
)
from pip._vendor.rich.highlighter import NullHighlighter
from pip._vendor.rich.logging import RichHandler
from pip._vendor.rich.segment import Segment
from pip._vendor.rich.style import Style

from pip._internal.utils._log import VERBOSE, getLogger
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.deprecation import DEPRECATION_MSG_PREFIX
from pip._internal.utils.misc import ensure_dir

_log_state = threading.local()
subprocess_logger = getLogger("pip.subprocessor")


class BrokenStdoutLoggingError(Exception):
    """
    Raised if BrokenPipeError occurs for the stdout stream while logging.
    """


def _is_broken_pipe_error(exc_class: Type[BaseException], exc: BaseException) -> bool:
    if exc_class is BrokenPipeError:
        return True

    # On Windows, a broken pipe can show up as EINVAL rather than EPIPE:
    # https://bugs.python.org/issue19612
    # https://bugs.python.org/issue30418
    if not WINDOWS:
        return False

    return isinstance(exc, OSError) and exc.errno in (errno.EINVAL, errno.EPIPE)


@contextlib.contextmanager
def indent_log(num: int = 2) -> Generator[None, None, None]:
    """
    A context manager which will cause the log output to be indented for any
    log messages emitted inside it.
    """
    # For thread-safety
    _log_state.indentation = get_indentation()
    _log_state.indentation += num
    try:
        yield
    finally:
        _log_state.indentation -= num


def get_indentation() -> int:
    return getattr(_log_state, "indentation", 0)


class IndentingFormatter(logging.Formatter):
    default_time_format = "%Y-%m-%dT%H:%M:%S"

    def __init__(
        self,
        *args: Any,
        add_timestamp: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        A logging.Formatter that obeys the indent_log() context manager.

        :param add_timestamp: A bool indicating output lines should be prefixed
            with their record's timestamp.
        """
        self.add_timestamp = add_timestamp
        super().__init__(*args, **kwargs)

    def get_message_start(self, formatted: str, levelno: int) -> str:
        """
        Return the start of the formatted log message (not counting the
        prefix to add to each line).
        """
        if levelno < logging.WARNING:
            return ""
        if formatted.startswith(DEPRECATION_MSG_PREFIX):
            # Then the message already has a prefix.  We don't want it to
            # look like "WARNING: DEPRECATION: ...."
            return ""
        if levelno < logging.ERROR:
            return "WARNING: "

        return "ERROR: "

    def format(self, record: logging.LogRecord) -> str:
        """
        Calls the standard formatter, but will indent all of the log message
        lines by our current indentation level.
        """
        formatted = super().format(record)
        message_start = self.get_message_start(formatted, record.levelno)
        formatted = message_start + formatted

        prefix = ""
        if self.add_timestamp:
            prefix = f"{self.formatTime(record)} "
        prefix += " " * get_indentation()
        formatted = "".join([prefix + line for line in formatted.splitlines(True)])
        return formatted


@dataclass
class IndentedRenderable:
    renderable: RenderableType
    indent: int

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        segments = console.render(self.renderable, options)
        lines = Segment.split_lines(segments)
        for line in lines:
            yield Segment(" " * self.indent)
            yield from line
            yield Segment("\n")


class PipConsole(Console):
    def on_broken_pipe(self) -> None:
        # Reraise the original exception, rich 13.8.0+ exits by default
        # instead, preventing our handler from firing.
        raise BrokenPipeError() from None


class RichPipStreamHandler(RichHandler):
    KEYWORDS: ClassVar[Optional[List[str]]] = []

    def __init__(self, stream: Optional[TextIO], no_color: bool) -> None:
        super().__init__(
            console=PipConsole(file=stream, no_color=no_color, soft_wrap=True),
            show_time=False,
            show_level=False,
            show_path=False,
            highlighter=NullHighlighter(),
        )

    # Our custom override on Rich's logger, to make things work as we need them to.
    def emit(self, record: logging.LogRecord) -> None:
        style: Optional[Style] = None

        # If we are given a diagnostic error to present, present it with indentation.
        if getattr(record, "rich", False):
            assert isinstance(record.args, tuple)
            (rich_renderable,) = record.args
            assert isinstance(
                rich_renderable, (ConsoleRenderable, RichCast, str)
            ), f"{rich_renderable} is not rich-console-renderable"

            renderable: RenderableType = IndentedRenderable(
                rich_renderable, indent=get_indentation()
            )
        else:
            message = self.format(record)
            renderable = self.render_message(record, message)
            if record.levelno is not None:
                if record.levelno >= logging.ERROR:
                    style = Style(color="red")
                elif record.levelno >= logging.WARNING:
                    style = Style(color="yellow")

        try:
            self.console.print(renderable, overflow="ignore", crop=False, style=style)
        except Exception:
            self.handleError(record)

    def handleError(self, record: logging.LogRecord) -> None:
        """Called when logging is unable to log some output."""

        exc_class, exc = sys.exc_info()[:2]
        # If a broken pipe occurred while calling write() or flush() on the
        # stdout stream in logging's Handler.emit(), then raise our special
        # exception so we can handle it in main() instead of logging the
        # broken pipe error and continuing.
        if (
            exc_class
            and exc
            and self.console.file is sys.stdout
            and _is_broken_pipe_error(exc_class, exc)
        ):
            raise BrokenStdoutLoggingError()

        return super().handleError(record)


class BetterRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def _open(self) -> TextIOWrapper:
        ensure_dir(os.path.dirname(self.baseFilename))
        return super()._open()


class MaxLevelFilter(Filter):
    def __init__(self, level: int) -> None:
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < self.level


class ExcludeLoggerFilter(Filter):
    """
    A logging Filter that excludes records from a logger (or its children).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # The base Filter class allows only records from a logger (or its
        # children).
        return not super().filter(record)


def setup_logging(verbosity: int, no_color: bool, user_log_file: Optional[str]) -> int:
    """Configures and sets up all of the logging

    Returns the requested logging level, as its integer value.
    """

    # Determine the level to be logging at.
    if verbosity >= 2:
        level_number = logging.DEBUG
    elif verbosity == 1:
        level_number = VERBOSE
    elif verbosity == -1:
        level_number = logging.WARNING
    elif verbosity == -2:
        level_number = logging.ERROR
    elif verbosity <= -3:
        level_number = logging.CRITICAL
    else:
        level_number = logging.INFO

    level = logging.getLevelName(level_number)

    # The "root" logger should match the "console" level *unless* we also need
    # to log to a user log file.
    include_user_log = user_log_file is not None
    if include_user_log:
        additional_log_file = user_log_file
        root_level = "DEBUG"
    else:
        additional_log_file = "/dev/null"
        root_level = level

    # Disable any logging besides WARNING unless we have DEBUG level logging
    # enabled for vendored libraries.
    vendored_log_level = "WARNING" if level in ["INFO", "ERROR"] else "DEBUG"

    # Shorthands for clarity
    log_streams = {
        "stdout": "ext://sys.stdout",
        "stderr": "ext://sys.stderr",
    }
    handler_classes = {
        "stream": "pip._internal.utils.logging.RichPipStreamHandler",
        "file": "pip._internal.utils.logging.BetterRotatingFileHandler",
    }
    handlers = ["console", "console_errors", "console_subprocess"] + (
        ["user_log"] if include_user_log else []
    )

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "exclude_warnings": {
                    "()": "pip._internal.utils.logging.MaxLevelFilter",
                    "level": logging.WARNING,
                },
                "restrict_to_subprocess": {
                    "()": "logging.Filter",
                    "name": subprocess_logger.name,
                },
                "exclude_subprocess": {
                    "()": "pip._internal.utils.logging.ExcludeLoggerFilter",
                    "name": subprocess_logger.name,
                },
            },
            "formatters": {
                "indent": {
                    "()": IndentingFormatter,
                    "format": "%(message)s",
                },
                "indent_with_timestamp": {
                    "()": IndentingFormatter,
                    "format": "%(message)s",
                    "add_timestamp": True,
                },
            },
            "handlers": {
                "console": {
                    "level": level,
                    "class": handler_classes["stream"],
                    "no_color": no_color,
                    "stream": log_streams["stdout"],
                    "filters": ["exclude_subprocess", "exclude_warnings"],
                    "formatter": "indent",
                },
                "console_errors": {
                    "level": "WARNING",
                    "class": handler_classes["stream"],
                    "no_color": no_color,
                    "stream": log_streams["stderr"],
                    "filters": ["exclude_subprocess"],
                    "formatter": "indent",
                },
                # A handler responsible for logging to the console messages
                # from the "subprocessor" logger.
                "console_subprocess": {
                    "level": level,
                    "class": handler_classes["stream"],
                    "stream": log_streams["stderr"],
                    "no_color": no_color,
                    "filters": ["restrict_to_subprocess"],
                    "formatter": "indent",
                },
                "user_log": {
                    "level": "DEBUG",
                    "class": handler_classes["file"],
                    "filename": additional_log_file,
                    "encoding": "utf-8",
                    "delay": True,
                    "formatter": "indent_with_timestamp",
                },
            },
            "root": {
                "level": root_level,
                "handlers": handlers,
            },
            "loggers": {"pip._vendor": {"level": vendored_log_level}},
        }
    )

    return level_number

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\packaging\_parser.py ===
"""Handwritten parser of dependency specifiers.

The docstring for each __parse_* function contains EBNF-inspired grammar representing
the implementation.
"""

from __future__ import annotations

import ast
from typing import NamedTuple, Sequence, Tuple, Union

from ._tokenizer import DEFAULT_RULES, Tokenizer


class Node:
    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}('{self}')>"

    def serialize(self) -> str:
        raise NotImplementedError


class Variable(Node):
    def serialize(self) -> str:
        return str(self)


class Value(Node):
    def serialize(self) -> str:
        return f'"{self}"'


class Op(Node):
    def serialize(self) -> str:
        return str(self)


MarkerVar = Union[Variable, Value]
MarkerItem = Tuple[MarkerVar, Op, MarkerVar]
MarkerAtom = Union[MarkerItem, Sequence["MarkerAtom"]]
MarkerList = Sequence[Union["MarkerList", MarkerAtom, str]]


class ParsedRequirement(NamedTuple):
    name: str
    url: str
    extras: list[str]
    specifier: str
    marker: MarkerList | None


# --------------------------------------------------------------------------------------
# Recursive descent parser for dependency specifier
# --------------------------------------------------------------------------------------
def parse_requirement(source: str) -> ParsedRequirement:
    return _parse_requirement(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_requirement(tokenizer: Tokenizer) -> ParsedRequirement:
    """
    requirement = WS? IDENTIFIER WS? extras WS? requirement_details
    """
    tokenizer.consume("WS")

    name_token = tokenizer.expect(
        "IDENTIFIER", expected="package name at the start of dependency specifier"
    )
    name = name_token.text
    tokenizer.consume("WS")

    extras = _parse_extras(tokenizer)
    tokenizer.consume("WS")

    url, specifier, marker = _parse_requirement_details(tokenizer)
    tokenizer.expect("END", expected="end of dependency specifier")

    return ParsedRequirement(name, url, extras, specifier, marker)


def _parse_requirement_details(
    tokenizer: Tokenizer,
) -> tuple[str, str, MarkerList | None]:
    """
    requirement_details = AT URL (WS requirement_marker?)?
                        | specifier WS? (requirement_marker)?
    """

    specifier = ""
    url = ""
    marker = None

    if tokenizer.check("AT"):
        tokenizer.read()
        tokenizer.consume("WS")

        url_start = tokenizer.position
        url = tokenizer.expect("URL", expected="URL after @").text
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        tokenizer.expect("WS", expected="whitespace after URL")

        # The input might end after whitespace.
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer, span_start=url_start, after="URL and whitespace"
        )
    else:
        specifier_start = tokenizer.position
        specifier = _parse_specifier(tokenizer)
        tokenizer.consume("WS")

        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer,
            span_start=specifier_start,
            after=(
                "version specifier"
                if specifier
                else "name and no valid version specifier"
            ),
        )

    return (url, specifier, marker)


def _parse_requirement_marker(
    tokenizer: Tokenizer, *, span_start: int, after: str
) -> MarkerList:
    """
    requirement_marker = SEMICOLON marker WS?
    """

    if not tokenizer.check("SEMICOLON"):
        tokenizer.raise_syntax_error(
            f"Expected end or semicolon (after {after})",
            span_start=span_start,
        )
    tokenizer.read()

    marker = _parse_marker(tokenizer)
    tokenizer.consume("WS")

    return marker


def _parse_extras(tokenizer: Tokenizer) -> list[str]:
    """
    extras = (LEFT_BRACKET wsp* extras_list? wsp* RIGHT_BRACKET)?
    """
    if not tokenizer.check("LEFT_BRACKET", peek=True):
        return []

    with tokenizer.enclosing_tokens(
        "LEFT_BRACKET",
        "RIGHT_BRACKET",
        around="extras",
    ):
        tokenizer.consume("WS")
        extras = _parse_extras_list(tokenizer)
        tokenizer.consume("WS")

    return extras


def _parse_extras_list(tokenizer: Tokenizer) -> list[str]:
    """
    extras_list = identifier (wsp* ',' wsp* identifier)*
    """
    extras: list[str] = []

    if not tokenizer.check("IDENTIFIER"):
        return extras

    extras.append(tokenizer.read().text)

    while True:
        tokenizer.consume("WS")
        if tokenizer.check("IDENTIFIER", peek=True):
            tokenizer.raise_syntax_error("Expected comma between extra names")
        elif not tokenizer.check("COMMA"):
            break

        tokenizer.read()
        tokenizer.consume("WS")

        extra_token = tokenizer.expect("IDENTIFIER", expected="extra name after comma")
        extras.append(extra_token.text)

    return extras


def _parse_specifier(tokenizer: Tokenizer) -> str:
    """
    specifier = LEFT_PARENTHESIS WS? version_many WS? RIGHT_PARENTHESIS
              | WS? version_many WS?
    """
    with tokenizer.enclosing_tokens(
        "LEFT_PARENTHESIS",
        "RIGHT_PARENTHESIS",
        around="version specifier",
    ):
        tokenizer.consume("WS")
        parsed_specifiers = _parse_version_many(tokenizer)
        tokenizer.consume("WS")

    return parsed_specifiers


def _parse_version_many(tokenizer: Tokenizer) -> str:
    """
    version_many = (SPECIFIER (WS? COMMA WS? SPECIFIER)*)?
    """
    parsed_specifiers = ""
    while tokenizer.check("SPECIFIER"):
        span_start = tokenizer.position
        parsed_specifiers += tokenizer.read().text
        if tokenizer.check("VERSION_PREFIX_TRAIL", peek=True):
            tokenizer.raise_syntax_error(
                ".* suffix can only be used with `==` or `!=` operators",
                span_start=span_start,
                span_end=tokenizer.position + 1,
            )
        if tokenizer.check("VERSION_LOCAL_LABEL_TRAIL", peek=True):
            tokenizer.raise_syntax_error(
                "Local version label can only be used with `==` or `!=` operators",
                span_start=span_start,
                span_end=tokenizer.position,
            )
        tokenizer.consume("WS")
        if not tokenizer.check("COMMA"):
            break
        parsed_specifiers += tokenizer.read().text
        tokenizer.consume("WS")

    return parsed_specifiers


# --------------------------------------------------------------------------------------
# Recursive descent parser for marker expression
# --------------------------------------------------------------------------------------
def parse_marker(source: str) -> MarkerList:
    return _parse_full_marker(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_full_marker(tokenizer: Tokenizer) -> MarkerList:
    retval = _parse_marker(tokenizer)
    tokenizer.expect("END", expected="end of marker expression")
    return retval


def _parse_marker(tokenizer: Tokenizer) -> MarkerList:
    """
    marker = marker_atom (BOOLOP marker_atom)+
    """
    expression = [_parse_marker_atom(tokenizer)]
    while tokenizer.check("BOOLOP"):
        token = tokenizer.read()
        expr_right = _parse_marker_atom(tokenizer)
        expression.extend((token.text, expr_right))
    return expression


def _parse_marker_atom(tokenizer: Tokenizer) -> MarkerAtom:
    """
    marker_atom = WS? LEFT_PARENTHESIS WS? marker WS? RIGHT_PARENTHESIS WS?
                | WS? marker_item WS?
    """

    tokenizer.consume("WS")
    if tokenizer.check("LEFT_PARENTHESIS", peek=True):
        with tokenizer.enclosing_tokens(
            "LEFT_PARENTHESIS",
            "RIGHT_PARENTHESIS",
            around="marker expression",
        ):
            tokenizer.consume("WS")
            marker: MarkerAtom = _parse_marker(tokenizer)
            tokenizer.consume("WS")
    else:
        marker = _parse_marker_item(tokenizer)
    tokenizer.consume("WS")
    return marker


def _parse_marker_item(tokenizer: Tokenizer) -> MarkerItem:
    """
    marker_item = WS? marker_var WS? marker_op WS? marker_var WS?
    """
    tokenizer.consume("WS")
    marker_var_left = _parse_marker_var(tokenizer)
    tokenizer.consume("WS")
    marker_op = _parse_marker_op(tokenizer)
    tokenizer.consume("WS")
    marker_var_right = _parse_marker_var(tokenizer)
    tokenizer.consume("WS")
    return (marker_var_left, marker_op, marker_var_right)


def _parse_marker_var(tokenizer: Tokenizer) -> MarkerVar:
    """
    marker_var = VARIABLE | QUOTED_STRING
    """
    if tokenizer.check("VARIABLE"):
        return process_env_var(tokenizer.read().text.replace(".", "_"))
    elif tokenizer.check("QUOTED_STRING"):
        return process_python_str(tokenizer.read().text)
    else:
        tokenizer.raise_syntax_error(
            message="Expected a marker variable or quoted string"
        )


def process_env_var(env_var: str) -> Variable:
    if env_var in ("platform_python_implementation", "python_implementation"):
        return Variable("platform_python_implementation")
    else:
        return Variable(env_var)


def process_python_str(python_str: str) -> Value:
    value = ast.literal_eval(python_str)
    return Value(str(value))


def _parse_marker_op(tokenizer: Tokenizer) -> Op:
    """
    marker_op = IN | NOT IN | OP
    """
    if tokenizer.check("IN"):
        tokenizer.read()
        return Op("in")
    elif tokenizer.check("NOT"):
        tokenizer.read()
        tokenizer.expect("WS", expected="whitespace after 'not'")
        tokenizer.expect("IN", expected="'in' after 'not'")
        return Op("not in")
    elif tokenizer.check("OP"):
        return Op(tokenizer.read().text)
    else:
        return tokenizer.raise_syntax_error(
            "Expected marker operator, one of "
            "<=, <, !=, ==, >=, >, ~=, ===, in, not in"
        )

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\packaging\_parser.py ===
"""Handwritten parser of dependency specifiers.

The docstring for each __parse_* function contains EBNF-inspired grammar representing
the implementation.
"""

from __future__ import annotations

import ast
from typing import NamedTuple, Sequence, Tuple, Union

from ._tokenizer import DEFAULT_RULES, Tokenizer


class Node:
    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}('{self}')>"

    def serialize(self) -> str:
        raise NotImplementedError


class Variable(Node):
    def serialize(self) -> str:
        return str(self)


class Value(Node):
    def serialize(self) -> str:
        return f'"{self}"'


class Op(Node):
    def serialize(self) -> str:
        return str(self)


MarkerVar = Union[Variable, Value]
MarkerItem = Tuple[MarkerVar, Op, MarkerVar]
MarkerAtom = Union[MarkerItem, Sequence["MarkerAtom"]]
MarkerList = Sequence[Union["MarkerList", MarkerAtom, str]]


class ParsedRequirement(NamedTuple):
    name: str
    url: str
    extras: list[str]
    specifier: str
    marker: MarkerList | None


# --------------------------------------------------------------------------------------
# Recursive descent parser for dependency specifier
# --------------------------------------------------------------------------------------
def parse_requirement(source: str) -> ParsedRequirement:
    return _parse_requirement(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_requirement(tokenizer: Tokenizer) -> ParsedRequirement:
    """
    requirement = WS? IDENTIFIER WS? extras WS? requirement_details
    """
    tokenizer.consume("WS")

    name_token = tokenizer.expect(
        "IDENTIFIER", expected="package name at the start of dependency specifier"
    )
    name = name_token.text
    tokenizer.consume("WS")

    extras = _parse_extras(tokenizer)
    tokenizer.consume("WS")

    url, specifier, marker = _parse_requirement_details(tokenizer)
    tokenizer.expect("END", expected="end of dependency specifier")

    return ParsedRequirement(name, url, extras, specifier, marker)


def _parse_requirement_details(
    tokenizer: Tokenizer,
) -> tuple[str, str, MarkerList | None]:
    """
    requirement_details = AT URL (WS requirement_marker?)?
                        | specifier WS? (requirement_marker)?
    """

    specifier = ""
    url = ""
    marker = None

    if tokenizer.check("AT"):
        tokenizer.read()
        tokenizer.consume("WS")

        url_start = tokenizer.position
        url = tokenizer.expect("URL", expected="URL after @").text
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        tokenizer.expect("WS", expected="whitespace after URL")

        # The input might end after whitespace.
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer, span_start=url_start, after="URL and whitespace"
        )
    else:
        specifier_start = tokenizer.position
        specifier = _parse_specifier(tokenizer)
        tokenizer.consume("WS")

        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer,
            span_start=specifier_start,
            after=(
                "version specifier"
                if specifier
                else "name and no valid version specifier"
            ),
        )

    return (url, specifier, marker)


def _parse_requirement_marker(
    tokenizer: Tokenizer, *, span_start: int, after: str
) -> MarkerList:
    """
    requirement_marker = SEMICOLON marker WS?
    """

    if not tokenizer.check("SEMICOLON"):
        tokenizer.raise_syntax_error(
            f"Expected end or semicolon (after {after})",
            span_start=span_start,
        )
    tokenizer.read()

    marker = _parse_marker(tokenizer)
    tokenizer.consume("WS")

    return marker


def _parse_extras(tokenizer: Tokenizer) -> list[str]:
    """
    extras = (LEFT_BRACKET wsp* extras_list? wsp* RIGHT_BRACKET)?
    """
    if not tokenizer.check("LEFT_BRACKET", peek=True):
        return []

    with tokenizer.enclosing_tokens(
        "LEFT_BRACKET",
        "RIGHT_BRACKET",
        around="extras",
    ):
        tokenizer.consume("WS")
        extras = _parse_extras_list(tokenizer)
        tokenizer.consume("WS")

    return extras


def _parse_extras_list(tokenizer: Tokenizer) -> list[str]:
    """
    extras_list = identifier (wsp* ',' wsp* identifier)*
    """
    extras: list[str] = []

    if not tokenizer.check("IDENTIFIER"):
        return extras

    extras.append(tokenizer.read().text)

    while True:
        tokenizer.consume("WS")
        if tokenizer.check("IDENTIFIER", peek=True):
            tokenizer.raise_syntax_error("Expected comma between extra names")
        elif not tokenizer.check("COMMA"):
            break

        tokenizer.read()
        tokenizer.consume("WS")

        extra_token = tokenizer.expect("IDENTIFIER", expected="extra name after comma")
        extras.append(extra_token.text)

    return extras


def _parse_specifier(tokenizer: Tokenizer) -> str:
    """
    specifier = LEFT_PARENTHESIS WS? version_many WS? RIGHT_PARENTHESIS
              | WS? version_many WS?
    """
    with tokenizer.enclosing_tokens(
        "LEFT_PARENTHESIS",
        "RIGHT_PARENTHESIS",
        around="version specifier",
    ):
        tokenizer.consume("WS")
        parsed_specifiers = _parse_version_many(tokenizer)
        tokenizer.consume("WS")

    return parsed_specifiers


def _parse_version_many(tokenizer: Tokenizer) -> str:
    """
    version_many = (SPECIFIER (WS? COMMA WS? SPECIFIER)*)?
    """
    parsed_specifiers = ""
    while tokenizer.check("SPECIFIER"):
        span_start = tokenizer.position
        parsed_specifiers += tokenizer.read().text
        if tokenizer.check("VERSION_PREFIX_TRAIL", peek=True):
            tokenizer.raise_syntax_error(
                ".* suffix can only be used with `==` or `!=` operators",
                span_start=span_start,
                span_end=tokenizer.position + 1,
            )
        if tokenizer.check("VERSION_LOCAL_LABEL_TRAIL", peek=True):
            tokenizer.raise_syntax_error(
                "Local version label can only be used with `==` or `!=` operators",
                span_start=span_start,
                span_end=tokenizer.position,
            )
        tokenizer.consume("WS")
        if not tokenizer.check("COMMA"):
            break
        parsed_specifiers += tokenizer.read().text
        tokenizer.consume("WS")

    return parsed_specifiers


# --------------------------------------------------------------------------------------
# Recursive descent parser for marker expression
# --------------------------------------------------------------------------------------
def parse_marker(source: str) -> MarkerList:
    return _parse_full_marker(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_full_marker(tokenizer: Tokenizer) -> MarkerList:
    retval = _parse_marker(tokenizer)
    tokenizer.expect("END", expected="end of marker expression")
    return retval


def _parse_marker(tokenizer: Tokenizer) -> MarkerList:
    """
    marker = marker_atom (BOOLOP marker_atom)+
    """
    expression = [_parse_marker_atom(tokenizer)]
    while tokenizer.check("BOOLOP"):
        token = tokenizer.read()
        expr_right = _parse_marker_atom(tokenizer)
        expression.extend((token.text, expr_right))
    return expression


def _parse_marker_atom(tokenizer: Tokenizer) -> MarkerAtom:
    """
    marker_atom = WS? LEFT_PARENTHESIS WS? marker WS? RIGHT_PARENTHESIS WS?
                | WS? marker_item WS?
    """

    tokenizer.consume("WS")
    if tokenizer.check("LEFT_PARENTHESIS", peek=True):
        with tokenizer.enclosing_tokens(
            "LEFT_PARENTHESIS",
            "RIGHT_PARENTHESIS",
            around="marker expression",
        ):
            tokenizer.consume("WS")
            marker: MarkerAtom = _parse_marker(tokenizer)
            tokenizer.consume("WS")
    else:
        marker = _parse_marker_item(tokenizer)
    tokenizer.consume("WS")
    return marker


def _parse_marker_item(tokenizer: Tokenizer) -> MarkerItem:
    """
    marker_item = WS? marker_var WS? marker_op WS? marker_var WS?
    """
    tokenizer.consume("WS")
    marker_var_left = _parse_marker_var(tokenizer)
    tokenizer.consume("WS")
    marker_op = _parse_marker_op(tokenizer)
    tokenizer.consume("WS")
    marker_var_right = _parse_marker_var(tokenizer)
    tokenizer.consume("WS")
    return (marker_var_left, marker_op, marker_var_right)


def _parse_marker_var(tokenizer: Tokenizer) -> MarkerVar:
    """
    marker_var = VARIABLE | QUOTED_STRING
    """
    if tokenizer.check("VARIABLE"):
        return process_env_var(tokenizer.read().text.replace(".", "_"))
    elif tokenizer.check("QUOTED_STRING"):
        return process_python_str(tokenizer.read().text)
    else:
        tokenizer.raise_syntax_error(
            message="Expected a marker variable or quoted string"
        )


def process_env_var(env_var: str) -> Variable:
    if env_var in ("platform_python_implementation", "python_implementation"):
        return Variable("platform_python_implementation")
    else:
        return Variable(env_var)


def process_python_str(python_str: str) -> Value:
    value = ast.literal_eval(python_str)
    return Value(str(value))


def _parse_marker_op(tokenizer: Tokenizer) -> Op:
    """
    marker_op = IN | NOT IN | OP
    """
    if tokenizer.check("IN"):
        tokenizer.read()
        return Op("in")
    elif tokenizer.check("NOT"):
        tokenizer.read()
        tokenizer.expect("WS", expected="whitespace after 'not'")
        tokenizer.expect("IN", expected="'in' after 'not'")
        return Op("not in")
    elif tokenizer.check("OP"):
        return Op(tokenizer.read().text)
    else:
        return tokenizer.raise_syntax_error(
            "Expected marker operator, one of "
            "<=, <, !=, ==, >=, >, ~=, ===, in, not in"
        )

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\_commit_scheduler.py ===
import atexit
import logging
import os
import time
from concurrent.futures import Future
from dataclasses import dataclass
from io import SEEK_END, SEEK_SET, BytesIO
from pathlib import Path
from threading import Lock, Thread
from typing import Dict, List, Optional, Union

from .hf_api import DEFAULT_IGNORE_PATTERNS, CommitInfo, CommitOperationAdd, HfApi
from .utils import filter_repo_objects


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _FileToUpload:
    """Temporary dataclass to store info about files to upload. Not meant to be used directly."""

    local_path: Path
    path_in_repo: str
    size_limit: int
    last_modified: float


class CommitScheduler:
    """
    Scheduler to upload a local folder to the Hub at regular intervals (e.g. push to hub every 5 minutes).

    The recommended way to use the scheduler is to use it as a context manager. This ensures that the scheduler is
    properly stopped and the last commit is triggered when the script ends. The scheduler can also be stopped manually
    with the `stop` method. Checkout the [upload guide](https://huggingface.co/docs/huggingface_hub/guides/upload#scheduled-uploads)
    to learn more about how to use it.

    Args:
        repo_id (`str`):
            The id of the repo to commit to.
        folder_path (`str` or `Path`):
            Path to the local folder to upload regularly.
        every (`int` or `float`, *optional*):
            The number of minutes between each commit. Defaults to 5 minutes.
        path_in_repo (`str`, *optional*):
            Relative path of the directory in the repo, for example: `"checkpoints/"`. Defaults to the root folder
            of the repository.
        repo_type (`str`, *optional*):
            The type of the repo to commit to. Defaults to `model`.
        revision (`str`, *optional*):
            The revision of the repo to commit to. Defaults to `main`.
        private (`bool`, *optional*):
            Whether to make the repo private. If `None` (default), the repo will be public unless the organization's default is private. This value is ignored if the repo already exists.
        token (`str`, *optional*):
            The token to use to commit to the repo. Defaults to the token saved on the machine.
        allow_patterns (`List[str]` or `str`, *optional*):
            If provided, only files matching at least one pattern are uploaded.
        ignore_patterns (`List[str]` or `str`, *optional*):
            If provided, files matching any of the patterns are not uploaded.
        squash_history (`bool`, *optional*):
            Whether to squash the history of the repo after each commit. Defaults to `False`. Squashing commits is
            useful to avoid degraded performances on the repo when it grows too large.
        hf_api (`HfApi`, *optional*):
            The [`HfApi`] client to use to commit to the Hub. Can be set with custom settings (user agent, token,...).

    Example:
    ```py
    >>> from pathlib import Path
    >>> from huggingface_hub import CommitScheduler

    # Scheduler uploads every 10 minutes
    >>> csv_path = Path("watched_folder/data.csv")
    >>> CommitScheduler(repo_id="test_scheduler", repo_type="dataset", folder_path=csv_path.parent, every=10)

    >>> with csv_path.open("a") as f:
    ...     f.write("first line")

    # Some time later (...)
    >>> with csv_path.open("a") as f:
    ...     f.write("second line")
    ```

    Example using a context manager:
    ```py
    >>> from pathlib import Path
    >>> from huggingface_hub import CommitScheduler

    >>> with CommitScheduler(repo_id="test_scheduler", repo_type="dataset", folder_path="watched_folder", every=10) as scheduler:
    ...     csv_path = Path("watched_folder/data.csv")
    ...     with csv_path.open("a") as f:
    ...         f.write("first line")
    ...     (...)
    ...     with csv_path.open("a") as f:
    ...         f.write("second line")

    # Scheduler is now stopped and last commit have been triggered
    ```
    """

    def __init__(
        self,
        *,
        repo_id: str,
        folder_path: Union[str, Path],
        every: Union[int, float] = 5,
        path_in_repo: Optional[str] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        private: Optional[bool] = None,
        token: Optional[str] = None,
        allow_patterns: Optional[Union[List[str], str]] = None,
        ignore_patterns: Optional[Union[List[str], str]] = None,
        squash_history: bool = False,
        hf_api: Optional["HfApi"] = None,
    ) -> None:
        self.api = hf_api or HfApi(token=token)

        # Folder
        self.folder_path = Path(folder_path).expanduser().resolve()
        self.path_in_repo = path_in_repo or ""
        self.allow_patterns = allow_patterns

        if ignore_patterns is None:
            ignore_patterns = []
        elif isinstance(ignore_patterns, str):
            ignore_patterns = [ignore_patterns]
        self.ignore_patterns = ignore_patterns + DEFAULT_IGNORE_PATTERNS

        if self.folder_path.is_file():
            raise ValueError(f"'folder_path' must be a directory, not a file: '{self.folder_path}'.")
        self.folder_path.mkdir(parents=True, exist_ok=True)

        # Repository
        repo_url = self.api.create_repo(repo_id=repo_id, private=private, repo_type=repo_type, exist_ok=True)
        self.repo_id = repo_url.repo_id
        self.repo_type = repo_type
        self.revision = revision
        self.token = token

        # Keep track of already uploaded files
        self.last_uploaded: Dict[Path, float] = {}  # key is local path, value is timestamp

        # Scheduler
        if not every > 0:
            raise ValueError(f"'every' must be a positive integer, not '{every}'.")
        self.lock = Lock()
        self.every = every
        self.squash_history = squash_history

        logger.info(f"Scheduled job to push '{self.folder_path}' to '{self.repo_id}' every {self.every} minutes.")
        self._scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()
        atexit.register(self._push_to_hub)

        self.__stopped = False

    def stop(self) -> None:
        """Stop the scheduler.

        A stopped scheduler cannot be restarted. Mostly for tests purposes.
        """
        self.__stopped = True

    def __enter__(self) -> "CommitScheduler":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        # Upload last changes before exiting
        self.trigger().result()
        self.stop()
        return

    def _run_scheduler(self) -> None:
        """Dumb thread waiting between each scheduled push to Hub."""
        while True:
            self.last_future = self.trigger()
            time.sleep(self.every * 60)
            if self.__stopped:
                break

    def trigger(self) -> Future:
        """Trigger a `push_to_hub` and return a future.

        This method is automatically called every `every` minutes. You can also call it manually to trigger a commit
        immediately, without waiting for the next scheduled commit.
        """
        return self.api.run_as_future(self._push_to_hub)

    def _push_to_hub(self) -> Optional[CommitInfo]:
        if self.__stopped:  # If stopped, already scheduled commits are ignored
            return None

        logger.info("(Background) scheduled commit triggered.")
        try:
            value = self.push_to_hub()
            if self.squash_history:
                logger.info("(Background) squashing repo history.")
                self.api.super_squash_history(repo_id=self.repo_id, repo_type=self.repo_type, branch=self.revision)
            return value
        except Exception as e:
            logger.error(f"Error while pushing to Hub: {e}")  # Depending on the setup, error might be silenced
            raise

    def push_to_hub(self) -> Optional[CommitInfo]:
        """
        Push folder to the Hub and return the commit info.

        <Tip warning={true}>

        This method is not meant to be called directly. It is run in the background by the scheduler, respecting a
        queue mechanism to avoid concurrent commits. Making a direct call to the method might lead to concurrency
        issues.

        </Tip>

        The default behavior of `push_to_hub` is to assume an append-only folder. It lists all files in the folder and
        uploads only changed files. If no changes are found, the method returns without committing anything. If you want
        to change this behavior, you can inherit from [`CommitScheduler`] and override this method. This can be useful
        for example to compress data together in a single file before committing. For more details and examples, check
        out our [integration guide](https://huggingface.co/docs/huggingface_hub/main/en/guides/upload#scheduled-uploads).
        """
        # Check files to upload (with lock)
        with self.lock:
            logger.debug("Listing files to upload for scheduled commit.")

            # List files from folder (taken from `_prepare_upload_folder_additions`)
            relpath_to_abspath = {
                path.relative_to(self.folder_path).as_posix(): path
                for path in sorted(self.folder_path.glob("**/*"))  # sorted to be deterministic
                if path.is_file()
            }
            prefix = f"{self.path_in_repo.strip('/')}/" if self.path_in_repo else ""

            # Filter with pattern + filter out unchanged files + retrieve current file size
            files_to_upload: List[_FileToUpload] = []
            for relpath in filter_repo_objects(
                relpath_to_abspath.keys(), allow_patterns=self.allow_patterns, ignore_patterns=self.ignore_patterns
            ):
                local_path = relpath_to_abspath[relpath]
                stat = local_path.stat()
                if self.last_uploaded.get(local_path) is None or self.last_uploaded[local_path] != stat.st_mtime:
                    files_to_upload.append(
                        _FileToUpload(
                            local_path=local_path,
                            path_in_repo=prefix + relpath,
                            size_limit=stat.st_size,
                            last_modified=stat.st_mtime,
                        )
                    )

        # Return if nothing to upload
        if len(files_to_upload) == 0:
            logger.debug("Dropping schedule commit: no changed file to upload.")
            return None

        # Convert `_FileToUpload` as `CommitOperationAdd` (=> compute file shas + limit to file size)
        logger.debug("Removing unchanged files since previous scheduled commit.")
        add_operations = [
            CommitOperationAdd(
                # Cap the file to its current size, even if the user append data to it while a scheduled commit is happening
                path_or_fileobj=PartialFileIO(file_to_upload.local_path, size_limit=file_to_upload.size_limit),
                path_in_repo=file_to_upload.path_in_repo,
            )
            for file_to_upload in files_to_upload
        ]

        # Upload files (append mode expected - no need for lock)
        logger.debug("Uploading files for scheduled commit.")
        commit_info = self.api.create_commit(
            repo_id=self.repo_id,
            repo_type=self.repo_type,
            operations=add_operations,
            commit_message="Scheduled Commit",
            revision=self.revision,
        )

        # Successful commit: keep track of the latest "last_modified" for each file
        for file in files_to_upload:
            self.last_uploaded[file.local_path] = file.last_modified
        return commit_info


class PartialFileIO(BytesIO):
    """A file-like object that reads only the first part of a file.

    Useful to upload a file to the Hub when the user might still be appending data to it. Only the first part of the
    file is uploaded (i.e. the part that was available when the filesystem was first scanned).

    In practice, only used internally by the CommitScheduler to regularly push a folder to the Hub with minimal
    disturbance for the user. The object is passed to `CommitOperationAdd`.

    Only supports `read`, `tell` and `seek` methods.

    Args:
        file_path (`str` or `Path`):
            Path to the file to read.
        size_limit (`int`):
            The maximum number of bytes to read from the file. If the file is larger than this, only the first part
            will be read (and uploaded).
    """

    def __init__(self, file_path: Union[str, Path], size_limit: int) -> None:
        self._file_path = Path(file_path)
        self._file = self._file_path.open("rb")
        self._size_limit = min(size_limit, os.fstat(self._file.fileno()).st_size)

    def __del__(self) -> None:
        self._file.close()
        return super().__del__()

    def __repr__(self) -> str:
        return f"<PartialFileIO file_path={self._file_path} size_limit={self._size_limit}>"

    def __len__(self) -> int:
        return self._size_limit

    def __getattribute__(self, name: str):
        if name.startswith("_") or name in ("read", "tell", "seek"):  # only 3 public methods supported
            return super().__getattribute__(name)
        raise NotImplementedError(f"PartialFileIO does not support '{name}'.")

    def tell(self) -> int:
        """Return the current file position."""
        return self._file.tell()

    def seek(self, __offset: int, __whence: int = SEEK_SET) -> int:
        """Change the stream position to the given offset.

        Behavior is the same as a regular file, except that the position is capped to the size limit.
        """
        if __whence == SEEK_END:
            # SEEK_END => set from the truncated end
            __offset = len(self) + __offset
            __whence = SEEK_SET

        pos = self._file.seek(__offset, __whence)
        if pos > self._size_limit:
            return self._file.seek(self._size_limit)
        return pos

    def read(self, __size: Optional[int] = -1) -> bytes:
        """Read at most `__size` bytes from the file.

        Behavior is the same as a regular file, except that it is capped to the size limit.
        """
        current = self._file.tell()
        if __size is None or __size < 0:
            # Read until file limit
            truncated_size = self._size_limit - current
        else:
            # Read until file limit or __size
            truncated_size = min(__size, self._size_limit - current)
        return self._file.read(truncated_size)

# === NexusCore/openenv\Lib\site-packages\packaging\_parser.py ===
"""Handwritten parser of dependency specifiers.

The docstring for each __parse_* function contains EBNF-inspired grammar representing
the implementation.
"""

from __future__ import annotations

import ast
from typing import NamedTuple, Sequence, Tuple, Union

from ._tokenizer import DEFAULT_RULES, Tokenizer


class Node:
    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}('{self}')>"

    def serialize(self) -> str:
        raise NotImplementedError


class Variable(Node):
    def serialize(self) -> str:
        return str(self)


class Value(Node):
    def serialize(self) -> str:
        return f'"{self}"'


class Op(Node):
    def serialize(self) -> str:
        return str(self)


MarkerVar = Union[Variable, Value]
MarkerItem = Tuple[MarkerVar, Op, MarkerVar]
MarkerAtom = Union[MarkerItem, Sequence["MarkerAtom"]]
MarkerList = Sequence[Union["MarkerList", MarkerAtom, str]]


class ParsedRequirement(NamedTuple):
    name: str
    url: str
    extras: list[str]
    specifier: str
    marker: MarkerList | None


# --------------------------------------------------------------------------------------
# Recursive descent parser for dependency specifier
# --------------------------------------------------------------------------------------
def parse_requirement(source: str) -> ParsedRequirement:
    return _parse_requirement(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_requirement(tokenizer: Tokenizer) -> ParsedRequirement:
    """
    requirement = WS? IDENTIFIER WS? extras WS? requirement_details
    """
    tokenizer.consume("WS")

    name_token = tokenizer.expect(
        "IDENTIFIER", expected="package name at the start of dependency specifier"
    )
    name = name_token.text
    tokenizer.consume("WS")

    extras = _parse_extras(tokenizer)
    tokenizer.consume("WS")

    url, specifier, marker = _parse_requirement_details(tokenizer)
    tokenizer.expect("END", expected="end of dependency specifier")

    return ParsedRequirement(name, url, extras, specifier, marker)


def _parse_requirement_details(
    tokenizer: Tokenizer,
) -> tuple[str, str, MarkerList | None]:
    """
    requirement_details = AT URL (WS requirement_marker?)?
                        | specifier WS? (requirement_marker)?
    """

    specifier = ""
    url = ""
    marker = None

    if tokenizer.check("AT"):
        tokenizer.read()
        tokenizer.consume("WS")

        url_start = tokenizer.position
        url = tokenizer.expect("URL", expected="URL after @").text
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        tokenizer.expect("WS", expected="whitespace after URL")

        # The input might end after whitespace.
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer, span_start=url_start, after="URL and whitespace"
        )
    else:
        specifier_start = tokenizer.position
        specifier = _parse_specifier(tokenizer)
        tokenizer.consume("WS")

        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer,
            span_start=specifier_start,
            after=(
                "version specifier"
                if specifier
                else "name and no valid version specifier"
            ),
        )

    return (url, specifier, marker)


def _parse_requirement_marker(
    tokenizer: Tokenizer, *, span_start: int, after: str
) -> MarkerList:
    """
    requirement_marker = SEMICOLON marker WS?
    """

    if not tokenizer.check("SEMICOLON"):
        tokenizer.raise_syntax_error(
            f"Expected end or semicolon (after {after})",
            span_start=span_start,
        )
    tokenizer.read()

    marker = _parse_marker(tokenizer)
    tokenizer.consume("WS")

    return marker


def _parse_extras(tokenizer: Tokenizer) -> list[str]:
    """
    extras = (LEFT_BRACKET wsp* extras_list? wsp* RIGHT_BRACKET)?
    """
    if not tokenizer.check("LEFT_BRACKET", peek=True):
        return []

    with tokenizer.enclosing_tokens(
        "LEFT_BRACKET",
        "RIGHT_BRACKET",
        around="extras",
    ):
        tokenizer.consume("WS")
        extras = _parse_extras_list(tokenizer)
        tokenizer.consume("WS")

    return extras


def _parse_extras_list(tokenizer: Tokenizer) -> list[str]:
    """
    extras_list = identifier (wsp* ',' wsp* identifier)*
    """
    extras: list[str] = []

    if not tokenizer.check("IDENTIFIER"):
        return extras

    extras.append(tokenizer.read().text)

    while True:
        tokenizer.consume("WS")
        if tokenizer.check("IDENTIFIER", peek=True):
            tokenizer.raise_syntax_error("Expected comma between extra names")
        elif not tokenizer.check("COMMA"):
            break

        tokenizer.read()
        tokenizer.consume("WS")

        extra_token = tokenizer.expect("IDENTIFIER", expected="extra name after comma")
        extras.append(extra_token.text)

    return extras


def _parse_specifier(tokenizer: Tokenizer) -> str:
    """
    specifier = LEFT_PARENTHESIS WS? version_many WS? RIGHT_PARENTHESIS
              | WS? version_many WS?
    """
    with tokenizer.enclosing_tokens(
        "LEFT_PARENTHESIS",
        "RIGHT_PARENTHESIS",
        around="version specifier",
    ):
        tokenizer.consume("WS")
        parsed_specifiers = _parse_version_many(tokenizer)
        tokenizer.consume("WS")

    return parsed_specifiers


def _parse_version_many(tokenizer: Tokenizer) -> str:
    """
    version_many = (SPECIFIER (WS? COMMA WS? SPECIFIER)*)?
    """
    parsed_specifiers = ""
    while tokenizer.check("SPECIFIER"):
        span_start = tokenizer.position
        parsed_specifiers += tokenizer.read().text
        if tokenizer.check("VERSION_PREFIX_TRAIL", peek=True):
            tokenizer.raise_syntax_error(
                ".* suffix can only be used with `==` or `!=` operators",
                span_start=span_start,
                span_end=tokenizer.position + 1,
            )
        if tokenizer.check("VERSION_LOCAL_LABEL_TRAIL", peek=True):
            tokenizer.raise_syntax_error(
                "Local version label can only be used with `==` or `!=` operators",
                span_start=span_start,
                span_end=tokenizer.position,
            )
        tokenizer.consume("WS")
        if not tokenizer.check("COMMA"):
            break
        parsed_specifiers += tokenizer.read().text
        tokenizer.consume("WS")

    return parsed_specifiers


# --------------------------------------------------------------------------------------
# Recursive descent parser for marker expression
# --------------------------------------------------------------------------------------
def parse_marker(source: str) -> MarkerList:
    return _parse_full_marker(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_full_marker(tokenizer: Tokenizer) -> MarkerList:
    retval = _parse_marker(tokenizer)
    tokenizer.expect("END", expected="end of marker expression")
    return retval


def _parse_marker(tokenizer: Tokenizer) -> MarkerList:
    """
    marker = marker_atom (BOOLOP marker_atom)+
    """
    expression = [_parse_marker_atom(tokenizer)]
    while tokenizer.check("BOOLOP"):
        token = tokenizer.read()
        expr_right = _parse_marker_atom(tokenizer)
        expression.extend((token.text, expr_right))
    return expression


def _parse_marker_atom(tokenizer: Tokenizer) -> MarkerAtom:
    """
    marker_atom = WS? LEFT_PARENTHESIS WS? marker WS? RIGHT_PARENTHESIS WS?
                | WS? marker_item WS?
    """

    tokenizer.consume("WS")
    if tokenizer.check("LEFT_PARENTHESIS", peek=True):
        with tokenizer.enclosing_tokens(
            "LEFT_PARENTHESIS",
            "RIGHT_PARENTHESIS",
            around="marker expression",
        ):
            tokenizer.consume("WS")
            marker: MarkerAtom = _parse_marker(tokenizer)
            tokenizer.consume("WS")
    else:
        marker = _parse_marker_item(tokenizer)
    tokenizer.consume("WS")
    return marker


def _parse_marker_item(tokenizer: Tokenizer) -> MarkerItem:
    """
    marker_item = WS? marker_var WS? marker_op WS? marker_var WS?
    """
    tokenizer.consume("WS")
    marker_var_left = _parse_marker_var(tokenizer)
    tokenizer.consume("WS")
    marker_op = _parse_marker_op(tokenizer)
    tokenizer.consume("WS")
    marker_var_right = _parse_marker_var(tokenizer)
    tokenizer.consume("WS")
    return (marker_var_left, marker_op, marker_var_right)


def _parse_marker_var(tokenizer: Tokenizer) -> MarkerVar:
    """
    marker_var = VARIABLE | QUOTED_STRING
    """
    if tokenizer.check("VARIABLE"):
        return process_env_var(tokenizer.read().text.replace(".", "_"))
    elif tokenizer.check("QUOTED_STRING"):
        return process_python_str(tokenizer.read().text)
    else:
        tokenizer.raise_syntax_error(
            message="Expected a marker variable or quoted string"
        )


def process_env_var(env_var: str) -> Variable:
    if env_var in ("platform_python_implementation", "python_implementation"):
        return Variable("platform_python_implementation")
    else:
        return Variable(env_var)


def process_python_str(python_str: str) -> Value:
    value = ast.literal_eval(python_str)
    return Value(str(value))


def _parse_marker_op(tokenizer: Tokenizer) -> Op:
    """
    marker_op = IN | NOT IN | OP
    """
    if tokenizer.check("IN"):
        tokenizer.read()
        return Op("in")
    elif tokenizer.check("NOT"):
        tokenizer.read()
        tokenizer.expect("WS", expected="whitespace after 'not'")
        tokenizer.expect("IN", expected="'in' after 'not'")
        return Op("not in")
    elif tokenizer.check("OP"):
        return Op(tokenizer.read().text)
    else:
        return tokenizer.raise_syntax_error(
            "Expected marker operator, one of <=, <, !=, ==, >=, >, ~=, ===, in, not in"
        )

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\tools\hierlist.py ===
# hierlist
#
# IMPORTANT - Please read before using.

# This module exposes an API for a Hierarchical Tree Control.
# Previously, a custom tree control was included in Pythonwin which
# has an API very similar to this.

# The current control used is the common "Tree Control".  This module exists now
# to provide an API similar to the old control, but for the new Tree control.

# If you need to use the Tree Control, you may still find this API a reasonable
# choice.  However, you should investigate using the tree control directly
# to provide maximum flexibility (but with extra work).
from __future__ import annotations

import commctrl
import win32api
import win32con
import win32ui
from pywin.mfc import dialog, object
from win32api import RGB


# helper to get the text of an arbitary item
def GetItemText(item):
    if isinstance(item, (tuple, list)):
        use = item[0]
    else:
        use = item
    if isinstance(use, str):
        return use
    else:
        return repr(item)


class HierDialog(dialog.Dialog):
    def __init__(
        self,
        title,
        hierList,
        bitmapID=win32ui.IDB_HIERFOLDERS,
        dlgID=win32ui.IDD_TREE,
        dll=None,
        childListBoxID=win32ui.IDC_LIST1,
    ):
        dialog.Dialog.__init__(self, dlgID, dll)  # reuse this dialog.
        self.hierList = hierList
        self.dlgID = dlgID
        self.title = title

    # 		self.childListBoxID = childListBoxID
    def OnInitDialog(self):
        self.SetWindowText(self.title)
        self.hierList.HierInit(self)
        return dialog.Dialog.OnInitDialog(self)


class HierList(object.Object):
    def __init__(
        self, root, bitmapID=win32ui.IDB_HIERFOLDERS, listBoxId=None, bitmapMask=None
    ):  # used to create object.
        self.listControl = None
        self.bitmapID = bitmapID
        self.root = root
        self.listBoxId = listBoxId
        self.itemHandleMap = {}
        self.filledItemHandlesMap = {}
        self.bitmapMask = bitmapMask

    def __getattr__(self, attr):
        try:
            return getattr(self.listControl, attr)
        except AttributeError:
            return object.Object.__getattr__(self, attr)

    def ItemFromHandle(self, handle):
        return self.itemHandleMap[handle]

    def SetStyle(self, newStyle):
        hwnd = self.listControl.GetSafeHwnd()
        style = win32api.GetWindowLong(hwnd, win32con.GWL_STYLE)
        win32api.SetWindowLong(hwnd, win32con.GWL_STYLE, (style | newStyle))

    def HierInit(self, parent, listControl=None):  # Used when window first exists.
        # this also calls "Create" on the listbox.
        # params - id of listbbox, ID of bitmap, size of bitmaps
        if self.bitmapMask is None:
            bitmapMask = RGB(0, 0, 255)
        else:
            bitmapMask = self.bitmapMask
        self.imageList = win32ui.CreateImageList(self.bitmapID, 16, 0, bitmapMask)
        if listControl is None:
            if self.listBoxId is None:
                self.listBoxId = win32ui.IDC_LIST1
            self.listControl = parent.GetDlgItem(self.listBoxId)
        else:
            self.listControl = listControl
            lbid = listControl.GetDlgCtrlID()
            assert (
                self.listBoxId is None or self.listBoxId == lbid
            ), "An invalid listbox control ID has been specified (specified as {}, but exists as {})".format(
                self.listBoxId, lbid
            )
            self.listBoxId = lbid
        self.listControl.SetImageList(self.imageList, commctrl.LVSIL_NORMAL)
        # 		self.list.AttachObject(self)

        parent.HookNotify(self.OnTreeItemExpanding, commctrl.TVN_ITEMEXPANDINGW)
        parent.HookNotify(self.OnTreeItemSelChanged, commctrl.TVN_SELCHANGEDW)
        parent.HookNotify(self.OnTreeItemDoubleClick, commctrl.NM_DBLCLK)
        self.notify_parent = parent

        if self.root:
            self.AcceptRoot(self.root)

    def DeleteAllItems(self):
        self.listControl.DeleteAllItems()
        self.root = None
        self.itemHandleMap = {}
        self.filledItemHandlesMap = {}

    def HierTerm(self):
        # Don't want notifies as we kill the list.
        parent = self.notify_parent  # GetParentFrame()
        parent.HookNotify(None, commctrl.TVN_ITEMEXPANDINGW)
        parent.HookNotify(None, commctrl.TVN_SELCHANGEDW)
        parent.HookNotify(None, commctrl.NM_DBLCLK)

        self.DeleteAllItems()
        self.listControl = None
        self.notify_parent = None  # Break a possible cycle

    def OnTreeItemDoubleClick(self, info, extra):
        (hwndFrom, idFrom, code) = info
        if idFrom != self.listBoxId:
            return None
        item = self.itemHandleMap[self.listControl.GetSelectedItem()]
        self.TakeDefaultAction(item)
        return 1

    def OnTreeItemExpanding(self, info, extra):
        (hwndFrom, idFrom, code) = info
        if idFrom != self.listBoxId:
            return None
        action, itemOld, itemNew, pt = extra
        itemHandle = itemNew[0]
        if itemHandle not in self.filledItemHandlesMap:
            item = self.itemHandleMap[itemHandle]
            self.AddSubList(itemHandle, self.GetSubList(item))
            self.filledItemHandlesMap[itemHandle] = None
        return 0

    def OnTreeItemSelChanged(self, info, extra):
        (hwndFrom, idFrom, code) = info
        if idFrom != self.listBoxId:
            return None
        action, itemOld, itemNew, pt = extra
        itemHandle = itemNew[0]
        item = self.itemHandleMap[itemHandle]
        self.PerformItemSelected(item)
        return 1

    def AddSubList(self, parentHandle, subItems):
        for item in subItems:
            self.AddItem(parentHandle, item)

    def AddItem(self, parentHandle, item, hInsertAfter=commctrl.TVI_LAST):
        text = self.GetText(item)
        if self.IsExpandable(item):
            cItems = 1  # Trick it !!
        else:
            cItems = 0
        bitmapCol = self.GetBitmapColumn(item)
        bitmapSel = self.GetSelectedBitmapColumn(item)
        if bitmapSel is None:
            bitmapSel = bitmapCol
        hitem = self.listControl.InsertItem(
            parentHandle,
            hInsertAfter,
            (None, None, None, text, bitmapCol, bitmapSel, cItems, 0),
        )
        self.itemHandleMap[hitem] = item
        return hitem

    def _GetChildHandles(self, handle):
        ret = []
        try:
            handle = self.listControl.GetChildItem(handle)
            while 1:
                ret.append(handle)
                handle = self.listControl.GetNextItem(handle, commctrl.TVGN_NEXT)
        except win32ui.error:
            # out of children
            pass
        return ret

    def Refresh(self, hparent=None):
        # Attempt to refresh the given item's sub-entries, but maintain the tree state
        # (ie, the selected item, expanded items, etc)
        if hparent is None:
            hparent = commctrl.TVI_ROOT
        if hparent not in self.filledItemHandlesMap:
            # This item has never been expanded, so no refresh can possibly be required.
            return
        root_item = self.itemHandleMap[hparent]
        old_handles = self._GetChildHandles(hparent)
        old_items = list(map(self.ItemFromHandle, old_handles))
        new_items = self.GetSubList(root_item)
        # Now an inefficient technique for synching the items.
        inew = 0
        hAfter = commctrl.TVI_FIRST
        for iold in range(len(old_items)):
            inewlook = inew
            matched = 0
            while inewlook < len(new_items):
                if old_items[iold] == new_items[inewlook]:
                    matched = 1
                    break
                inewlook += 1
            if matched:
                # Insert the new items.
                # print("Inserting after", old_items[iold], old_handles[iold])
                for i in range(inew, inewlook):
                    # print(f"Inserting index {i} ({new_items[i]})")
                    hAfter = self.AddItem(hparent, new_items[i], hAfter)

                inew = inewlook + 1
                # And recursively refresh iold
                hold = old_handles[iold]
                if hold in self.filledItemHandlesMap:
                    self.Refresh(hold)
            else:
                # Remove the deleted items.
                # print(f"Deleting {iold} ({old_items[iold]})")
                hdelete = old_handles[iold]
                # First recurse and remove the children from the map.
                for hchild in self._GetChildHandles(hdelete):
                    del self.itemHandleMap[hchild]
                    if hchild in self.filledItemHandlesMap:
                        del self.filledItemHandlesMap[hchild]
                self.listControl.DeleteItem(hdelete)
            hAfter = old_handles[iold]
        # Fill any remaining new items:
        for newItem in new_items[inew:]:
            # print("Inserting new item", newItem)
            self.AddItem(hparent, newItem)

    def AcceptRoot(self, root):
        self.listControl.DeleteAllItems()
        self.itemHandleMap = {commctrl.TVI_ROOT: root}
        self.filledItemHandlesMap = {commctrl.TVI_ROOT: root}
        subItems = self.GetSubList(root)
        self.AddSubList(0, subItems)

    def GetBitmapColumn(self, item):
        if self.IsExpandable(item):
            return 0
        else:
            return 4

    def GetSelectedBitmapColumn(self, item) -> int | None:
        return 0

    def CheckChangedChildren(self):
        return self.listControl.CheckChangedChildren()

    def GetText(self, item):
        return GetItemText(item)

    def PerformItemSelected(self, item):
        try:
            win32ui.SetStatusText("Selected " + self.GetText(item))
        except win32ui.error:  # No status bar!
            pass

    def TakeDefaultAction(self, item):
        win32ui.MessageBox("Got item " + self.GetText(item))


##########################################################################
#
# Classes for use with seperate HierListItems.
#
#
class HierListWithItems(HierList):
    def __init__(
        self, root, bitmapID=win32ui.IDB_HIERFOLDERS, listBoxID=None, bitmapMask=None
    ):  # used to create object.
        HierList.__init__(self, root, bitmapID, listBoxID, bitmapMask)

    def DelegateCall(self, fn):
        return fn()

    def GetBitmapColumn(self, item):
        rc = self.DelegateCall(item.GetBitmapColumn)
        if rc is None:
            rc = HierList.GetBitmapColumn(self, item)
        return rc

    def GetSelectedBitmapColumn(self, item):
        return self.DelegateCall(item.GetSelectedBitmapColumn)

    def IsExpandable(self, item):
        return self.DelegateCall(item.IsExpandable)

    def GetText(self, item):
        return self.DelegateCall(item.GetText)

    def GetSubList(self, item):
        return self.DelegateCall(item.GetSubList)

    def PerformItemSelected(self, item):
        func = getattr(item, "PerformItemSelected", None)
        if func is None:
            return HierList.PerformItemSelected(self, item)
        else:
            return self.DelegateCall(func)

    def TakeDefaultAction(self, item):
        func = getattr(item, "TakeDefaultAction", None)
        if func is None:
            return HierList.TakeDefaultAction(self, item)
        else:
            return self.DelegateCall(func)


# A hier list item - for use with a HierListWithItems
class HierListItem:
    def __init__(self):
        pass

    def GetText(self):
        pass

    def GetSubList(self):
        pass

    def IsExpandable(self):
        pass

    def GetBitmapColumn(self):
        return None  # indicate he should do it.

    def GetSelectedBitmapColumn(self):
        return None  # same as other

    def __lt__(self, other):
        # we want unrelated items to be sortable...
        return id(self) < id(other)

    def __eq__(self, other):
        return False

# === NexusCore/openenv\Lib\site-packages\anyio\streams\tls.py ===
from __future__ import annotations

import logging
import re
import ssl
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import wraps
from typing import Any, TypeVar

from .. import (
    BrokenResourceError,
    EndOfStream,
    aclose_forcefully,
    get_cancelled_exc_class,
    to_thread,
)
from .._core._typedattr import TypedAttributeSet, typed_attribute
from ..abc import AnyByteStream, ByteStream, Listener, TaskGroup

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack
else:
    from typing_extensions import TypeVarTuple, Unpack

T_Retval = TypeVar("T_Retval")
PosArgsT = TypeVarTuple("PosArgsT")
_PCTRTT = tuple[tuple[str, str], ...]
_PCTRTTT = tuple[_PCTRTT, ...]


class TLSAttribute(TypedAttributeSet):
    """Contains Transport Layer Security related attributes."""

    #: the selected ALPN protocol
    alpn_protocol: str | None = typed_attribute()
    #: the channel binding for type ``tls-unique``
    channel_binding_tls_unique: bytes = typed_attribute()
    #: the selected cipher
    cipher: tuple[str, str, int] = typed_attribute()
    #: the peer certificate in dictionary form (see :meth:`ssl.SSLSocket.getpeercert`
    # for more information)
    peer_certificate: None | (dict[str, str | _PCTRTTT | _PCTRTT]) = typed_attribute()
    #: the peer certificate in binary form
    peer_certificate_binary: bytes | None = typed_attribute()
    #: ``True`` if this is the server side of the connection
    server_side: bool = typed_attribute()
    #: ciphers shared by the client during the TLS handshake (``None`` if this is the
    #: client side)
    shared_ciphers: list[tuple[str, str, int]] | None = typed_attribute()
    #: the :class:`~ssl.SSLObject` used for encryption
    ssl_object: ssl.SSLObject = typed_attribute()
    #: ``True`` if this stream does (and expects) a closing TLS handshake when the
    #: stream is being closed
    standard_compatible: bool = typed_attribute()
    #: the TLS protocol version (e.g. ``TLSv1.2``)
    tls_version: str = typed_attribute()


@dataclass(eq=False)
class TLSStream(ByteStream):
    """
    A stream wrapper that encrypts all sent data and decrypts received data.

    This class has no public initializer; use :meth:`wrap` instead.
    All extra attributes from :class:`~TLSAttribute` are supported.

    :var AnyByteStream transport_stream: the wrapped stream

    """

    transport_stream: AnyByteStream
    standard_compatible: bool
    _ssl_object: ssl.SSLObject
    _read_bio: ssl.MemoryBIO
    _write_bio: ssl.MemoryBIO

    @classmethod
    async def wrap(
        cls,
        transport_stream: AnyByteStream,
        *,
        server_side: bool | None = None,
        hostname: str | None = None,
        ssl_context: ssl.SSLContext | None = None,
        standard_compatible: bool = True,
    ) -> TLSStream:
        """
        Wrap an existing stream with Transport Layer Security.

        This performs a TLS handshake with the peer.

        :param transport_stream: a bytes-transporting stream to wrap
        :param server_side: ``True`` if this is the server side of the connection,
            ``False`` if this is the client side (if omitted, will be set to ``False``
            if ``hostname`` has been provided, ``False`` otherwise). Used only to create
            a default context when an explicit context has not been provided.
        :param hostname: host name of the peer (if host name checking is desired)
        :param ssl_context: the SSLContext object to use (if not provided, a secure
            default will be created)
        :param standard_compatible: if ``False``, skip the closing handshake when
            closing the connection, and don't raise an exception if the peer does the
            same
        :raises ~ssl.SSLError: if the TLS handshake fails

        """
        if server_side is None:
            server_side = not hostname

        if not ssl_context:
            purpose = (
                ssl.Purpose.CLIENT_AUTH if server_side else ssl.Purpose.SERVER_AUTH
            )
            ssl_context = ssl.create_default_context(purpose)

            # Re-enable detection of unexpected EOFs if it was disabled by Python
            if hasattr(ssl, "OP_IGNORE_UNEXPECTED_EOF"):
                ssl_context.options &= ~ssl.OP_IGNORE_UNEXPECTED_EOF

        bio_in = ssl.MemoryBIO()
        bio_out = ssl.MemoryBIO()

        # External SSLContext implementations may do blocking I/O in wrap_bio(),
        # but the standard library implementation won't
        if type(ssl_context) is ssl.SSLContext:
            ssl_object = ssl_context.wrap_bio(
                bio_in, bio_out, server_side=server_side, server_hostname=hostname
            )
        else:
            ssl_object = await to_thread.run_sync(
                ssl_context.wrap_bio,
                bio_in,
                bio_out,
                server_side,
                hostname,
                None,
            )

        wrapper = cls(
            transport_stream=transport_stream,
            standard_compatible=standard_compatible,
            _ssl_object=ssl_object,
            _read_bio=bio_in,
            _write_bio=bio_out,
        )
        await wrapper._call_sslobject_method(ssl_object.do_handshake)
        return wrapper

    async def _call_sslobject_method(
        self, func: Callable[[Unpack[PosArgsT]], T_Retval], *args: Unpack[PosArgsT]
    ) -> T_Retval:
        while True:
            try:
                result = func(*args)
            except ssl.SSLWantReadError:
                try:
                    # Flush any pending writes first
                    if self._write_bio.pending:
                        await self.transport_stream.send(self._write_bio.read())

                    data = await self.transport_stream.receive()
                except EndOfStream:
                    self._read_bio.write_eof()
                except OSError as exc:
                    self._read_bio.write_eof()
                    self._write_bio.write_eof()
                    raise BrokenResourceError from exc
                else:
                    self._read_bio.write(data)
            except ssl.SSLWantWriteError:
                await self.transport_stream.send(self._write_bio.read())
            except ssl.SSLSyscallError as exc:
                self._read_bio.write_eof()
                self._write_bio.write_eof()
                raise BrokenResourceError from exc
            except ssl.SSLError as exc:
                self._read_bio.write_eof()
                self._write_bio.write_eof()
                if isinstance(exc, ssl.SSLEOFError) or (
                    exc.strerror and "UNEXPECTED_EOF_WHILE_READING" in exc.strerror
                ):
                    if self.standard_compatible:
                        raise BrokenResourceError from exc
                    else:
                        raise EndOfStream from None

                raise
            else:
                # Flush any pending writes first
                if self._write_bio.pending:
                    await self.transport_stream.send(self._write_bio.read())

                return result

    async def unwrap(self) -> tuple[AnyByteStream, bytes]:
        """
        Does the TLS closing handshake.

        :return: a tuple of (wrapped byte stream, bytes left in the read buffer)

        """
        await self._call_sslobject_method(self._ssl_object.unwrap)
        self._read_bio.write_eof()
        self._write_bio.write_eof()
        return self.transport_stream, self._read_bio.read()

    async def aclose(self) -> None:
        if self.standard_compatible:
            try:
                await self.unwrap()
            except BaseException:
                await aclose_forcefully(self.transport_stream)
                raise

        await self.transport_stream.aclose()

    async def receive(self, max_bytes: int = 65536) -> bytes:
        data = await self._call_sslobject_method(self._ssl_object.read, max_bytes)
        if not data:
            raise EndOfStream

        return data

    async def send(self, item: bytes) -> None:
        await self._call_sslobject_method(self._ssl_object.write, item)

    async def send_eof(self) -> None:
        tls_version = self.extra(TLSAttribute.tls_version)
        match = re.match(r"TLSv(\d+)(?:\.(\d+))?", tls_version)
        if match:
            major, minor = int(match.group(1)), int(match.group(2) or 0)
            if (major, minor) < (1, 3):
                raise NotImplementedError(
                    f"send_eof() requires at least TLSv1.3; current "
                    f"session uses {tls_version}"
                )

        raise NotImplementedError(
            "send_eof() has not yet been implemented for TLS streams"
        )

    @property
    def extra_attributes(self) -> Mapping[Any, Callable[[], Any]]:
        return {
            **self.transport_stream.extra_attributes,
            TLSAttribute.alpn_protocol: self._ssl_object.selected_alpn_protocol,
            TLSAttribute.channel_binding_tls_unique: (
                self._ssl_object.get_channel_binding
            ),
            TLSAttribute.cipher: self._ssl_object.cipher,
            TLSAttribute.peer_certificate: lambda: self._ssl_object.getpeercert(False),
            TLSAttribute.peer_certificate_binary: lambda: self._ssl_object.getpeercert(
                True
            ),
            TLSAttribute.server_side: lambda: self._ssl_object.server_side,
            TLSAttribute.shared_ciphers: lambda: self._ssl_object.shared_ciphers()
            if self._ssl_object.server_side
            else None,
            TLSAttribute.standard_compatible: lambda: self.standard_compatible,
            TLSAttribute.ssl_object: lambda: self._ssl_object,
            TLSAttribute.tls_version: self._ssl_object.version,
        }


@dataclass(eq=False)
class TLSListener(Listener[TLSStream]):
    """
    A convenience listener that wraps another listener and auto-negotiates a TLS session
    on every accepted connection.

    If the TLS handshake times out or raises an exception,
    :meth:`handle_handshake_error` is called to do whatever post-mortem processing is
    deemed necessary.

    Supports only the :attr:`~TLSAttribute.standard_compatible` extra attribute.

    :param Listener listener: the listener to wrap
    :param ssl_context: the SSL context object
    :param standard_compatible: a flag passed through to :meth:`TLSStream.wrap`
    :param handshake_timeout: time limit for the TLS handshake
        (passed to :func:`~anyio.fail_after`)
    """

    listener: Listener[Any]
    ssl_context: ssl.SSLContext
    standard_compatible: bool = True
    handshake_timeout: float = 30

    @staticmethod
    async def handle_handshake_error(exc: BaseException, stream: AnyByteStream) -> None:
        """
        Handle an exception raised during the TLS handshake.

        This method does 3 things:

        #. Forcefully closes the original stream
        #. Logs the exception (unless it was a cancellation exception) using the
           ``anyio.streams.tls`` logger
        #. Reraises the exception if it was a base exception or a cancellation exception

        :param exc: the exception
        :param stream: the original stream

        """
        await aclose_forcefully(stream)

        # Log all except cancellation exceptions
        if not isinstance(exc, get_cancelled_exc_class()):
            # CPython (as of 3.11.5) returns incorrect `sys.exc_info()` here when using
            # any asyncio implementation, so we explicitly pass the exception to log
            # (https://github.com/python/cpython/issues/108668). Trio does not have this
            # issue because it works around the CPython bug.
            logging.getLogger(__name__).exception(
                "Error during TLS handshake", exc_info=exc
            )

        # Only reraise base exceptions and cancellation exceptions
        if not isinstance(exc, Exception) or isinstance(exc, get_cancelled_exc_class()):
            raise

    async def serve(
        self,
        handler: Callable[[TLSStream], Any],
        task_group: TaskGroup | None = None,
    ) -> None:
        @wraps(handler)
        async def handler_wrapper(stream: AnyByteStream) -> None:
            from .. import fail_after

            try:
                with fail_after(self.handshake_timeout):
                    wrapped_stream = await TLSStream.wrap(
                        stream,
                        ssl_context=self.ssl_context,
                        standard_compatible=self.standard_compatible,
                    )
            except BaseException as exc:
                await self.handle_handshake_error(exc, stream)
            else:
                await handler(wrapped_stream)

        await self.listener.serve(handler_wrapper, task_group)

    async def aclose(self) -> None:
        await self.listener.aclose()

    @property
    def extra_attributes(self) -> Mapping[Any, Callable[[], Any]]:
        return {
            TLSAttribute.standard_compatible: lambda: self.standard_compatible,
        }

# === NexusCore/openenv\Lib\site-packages\fontTools\merge\tables.py ===
# Copyright 2013 Google, Inc. All Rights Reserved.
#
# Google Author(s): Behdad Esfahbod, Roozbeh Pournader

from fontTools import ttLib, cffLib
from fontTools.misc.psCharStrings import T2WidthExtractor
from fontTools.ttLib.tables.DefaultTable import DefaultTable
from fontTools.merge.base import add_method, mergeObjects
from fontTools.merge.cmap import computeMegaCmap
from fontTools.merge.util import *
import logging


log = logging.getLogger("fontTools.merge")


ttLib.getTableClass("maxp").mergeMap = {
    "*": max,
    "tableTag": equal,
    "tableVersion": equal,
    "numGlyphs": sum,
    "maxStorage": first,
    "maxFunctionDefs": first,
    "maxInstructionDefs": first,
    # TODO When we correctly merge hinting data, update these values:
    # maxFunctionDefs, maxInstructionDefs, maxSizeOfInstructions
}

headFlagsMergeBitMap = {
    "size": 16,
    "*": bitwise_or,
    1: bitwise_and,  # Baseline at y = 0
    2: bitwise_and,  # lsb at x = 0
    3: bitwise_and,  # Force ppem to integer values. FIXME?
    5: bitwise_and,  # Font is vertical
    6: lambda bit: 0,  # Always set to zero
    11: bitwise_and,  # Font data is 'lossless'
    13: bitwise_and,  # Optimized for ClearType
    14: bitwise_and,  # Last resort font. FIXME? equal or first may be better
    15: lambda bit: 0,  # Always set to zero
}

ttLib.getTableClass("head").mergeMap = {
    "tableTag": equal,
    "tableVersion": max,
    "fontRevision": max,
    "checkSumAdjustment": lambda lst: 0,  # We need *something* here
    "magicNumber": equal,
    "flags": mergeBits(headFlagsMergeBitMap),
    "unitsPerEm": equal,
    "created": current_time,
    "modified": current_time,
    "xMin": min,
    "yMin": min,
    "xMax": max,
    "yMax": max,
    "macStyle": first,
    "lowestRecPPEM": max,
    "fontDirectionHint": lambda lst: 2,
    "indexToLocFormat": first,
    "glyphDataFormat": equal,
}

ttLib.getTableClass("hhea").mergeMap = {
    "*": equal,
    "tableTag": equal,
    "tableVersion": max,
    "ascent": max,
    "descent": min,
    "lineGap": max,
    "advanceWidthMax": max,
    "minLeftSideBearing": min,
    "minRightSideBearing": min,
    "xMaxExtent": max,
    "caretSlopeRise": first,
    "caretSlopeRun": first,
    "caretOffset": first,
    "numberOfHMetrics": recalculate,
}

ttLib.getTableClass("vhea").mergeMap = {
    "*": equal,
    "tableTag": equal,
    "tableVersion": max,
    "ascent": max,
    "descent": min,
    "lineGap": max,
    "advanceHeightMax": max,
    "minTopSideBearing": min,
    "minBottomSideBearing": min,
    "yMaxExtent": max,
    "caretSlopeRise": first,
    "caretSlopeRun": first,
    "caretOffset": first,
    "numberOfVMetrics": recalculate,
}

os2FsTypeMergeBitMap = {
    "size": 16,
    "*": lambda bit: 0,
    1: bitwise_or,  # no embedding permitted
    2: bitwise_and,  # allow previewing and printing documents
    3: bitwise_and,  # allow editing documents
    8: bitwise_or,  # no subsetting permitted
    9: bitwise_or,  # no embedding of outlines permitted
}


def mergeOs2FsType(lst):
    lst = list(lst)
    if all(item == 0 for item in lst):
        return 0

    # Compute least restrictive logic for each fsType value
    for i in range(len(lst)):
        # unset bit 1 (no embedding permitted) if either bit 2 or 3 is set
        if lst[i] & 0x000C:
            lst[i] &= ~0x0002
        # set bit 2 (allow previewing) if bit 3 is set (allow editing)
        elif lst[i] & 0x0008:
            lst[i] |= 0x0004
        # set bits 2 and 3 if everything is allowed
        elif lst[i] == 0:
            lst[i] = 0x000C

    fsType = mergeBits(os2FsTypeMergeBitMap)(lst)
    # unset bits 2 and 3 if bit 1 is set (some font is "no embedding")
    if fsType & 0x0002:
        fsType &= ~0x000C
    return fsType


ttLib.getTableClass("OS/2").mergeMap = {
    "*": first,
    "tableTag": equal,
    "version": max,
    "xAvgCharWidth": first,  # Will be recalculated at the end on the merged font
    "fsType": mergeOs2FsType,  # Will be overwritten
    "panose": first,  # FIXME: should really be the first Latin font
    "ulUnicodeRange1": bitwise_or,
    "ulUnicodeRange2": bitwise_or,
    "ulUnicodeRange3": bitwise_or,
    "ulUnicodeRange4": bitwise_or,
    "fsFirstCharIndex": min,
    "fsLastCharIndex": max,
    "sTypoAscender": max,
    "sTypoDescender": min,
    "sTypoLineGap": max,
    "usWinAscent": max,
    "usWinDescent": max,
    # Version 1
    "ulCodePageRange1": onlyExisting(bitwise_or),
    "ulCodePageRange2": onlyExisting(bitwise_or),
    # Version 2, 3, 4
    "sxHeight": onlyExisting(max),
    "sCapHeight": onlyExisting(max),
    "usDefaultChar": onlyExisting(first),
    "usBreakChar": onlyExisting(first),
    "usMaxContext": onlyExisting(max),
    # version 5
    "usLowerOpticalPointSize": onlyExisting(min),
    "usUpperOpticalPointSize": onlyExisting(max),
}


@add_method(ttLib.getTableClass("OS/2"))
def merge(self, m, tables):
    DefaultTable.merge(self, m, tables)
    if self.version < 2:
        # bits 8 and 9 are reserved and should be set to zero
        self.fsType &= ~0x0300
    if self.version >= 3:
        # Only one of bits 1, 2, and 3 may be set. We already take
        # care of bit 1 implications in mergeOs2FsType. So unset
        # bit 2 if bit 3 is already set.
        if self.fsType & 0x0008:
            self.fsType &= ~0x0004
    return self


ttLib.getTableClass("post").mergeMap = {
    "*": first,
    "tableTag": equal,
    "formatType": max,
    "isFixedPitch": min,
    "minMemType42": max,
    "maxMemType42": lambda lst: 0,
    "minMemType1": max,
    "maxMemType1": lambda lst: 0,
    "mapping": onlyExisting(sumDicts),
    "extraNames": lambda lst: [],
}

ttLib.getTableClass("vmtx").mergeMap = ttLib.getTableClass("hmtx").mergeMap = {
    "tableTag": equal,
    "metrics": sumDicts,
}

ttLib.getTableClass("name").mergeMap = {
    "tableTag": equal,
    "names": first,  # FIXME? Does mixing name records make sense?
}

ttLib.getTableClass("loca").mergeMap = {
    "*": recalculate,
    "tableTag": equal,
}

ttLib.getTableClass("glyf").mergeMap = {
    "tableTag": equal,
    "glyphs": sumDicts,
    "glyphOrder": sumLists,
    "_reverseGlyphOrder": recalculate,
    "axisTags": equal,
}


@add_method(ttLib.getTableClass("glyf"))
def merge(self, m, tables):
    for i, table in enumerate(tables):
        for g in table.glyphs.values():
            if i:
                # Drop hints for all but first font, since
                # we don't map functions / CVT values.
                g.removeHinting()
            # Expand composite glyphs to load their
            # composite glyph names.
            if g.isComposite():
                g.expand(table)
    return DefaultTable.merge(self, m, tables)


ttLib.getTableClass("prep").mergeMap = lambda self, lst: first(lst)
ttLib.getTableClass("fpgm").mergeMap = lambda self, lst: first(lst)
ttLib.getTableClass("cvt ").mergeMap = lambda self, lst: first(lst)
ttLib.getTableClass("gasp").mergeMap = lambda self, lst: first(
    lst
)  # FIXME? Appears irreconcilable


@add_method(ttLib.getTableClass("CFF "))
def merge(self, m, tables):
    if any(hasattr(table.cff[0], "FDSelect") for table in tables):
        raise NotImplementedError("Merging CID-keyed CFF tables is not supported yet")

    for table in tables:
        table.cff.desubroutinize()

    newcff = tables[0]
    newfont = newcff.cff[0]
    private = newfont.Private
    newDefaultWidthX, newNominalWidthX = private.defaultWidthX, private.nominalWidthX
    storedNamesStrings = []
    glyphOrderStrings = []
    glyphOrder = set(newfont.getGlyphOrder())

    for name in newfont.strings.strings:
        if name not in glyphOrder:
            storedNamesStrings.append(name)
        else:
            glyphOrderStrings.append(name)

    chrset = list(newfont.charset)
    newcs = newfont.CharStrings
    log.debug("FONT 0 CharStrings: %d.", len(newcs))

    for i, table in enumerate(tables[1:], start=1):
        font = table.cff[0]
        defaultWidthX, nominalWidthX = (
            font.Private.defaultWidthX,
            font.Private.nominalWidthX,
        )
        widthsDiffer = (
            defaultWidthX != newDefaultWidthX or nominalWidthX != newNominalWidthX
        )
        font.Private = private
        fontGlyphOrder = set(font.getGlyphOrder())
        for name in font.strings.strings:
            if name in fontGlyphOrder:
                glyphOrderStrings.append(name)
        cs = font.CharStrings
        gs = table.cff.GlobalSubrs
        log.debug("Font %d CharStrings: %d.", i, len(cs))
        chrset.extend(font.charset)
        if newcs.charStringsAreIndexed:
            for i, name in enumerate(cs.charStrings, start=len(newcs)):
                newcs.charStrings[name] = i
                newcs.charStringsIndex.items.append(None)
        for name in cs.charStrings:
            if widthsDiffer:
                c = cs[name]
                defaultWidthXToken = object()
                extractor = T2WidthExtractor([], [], nominalWidthX, defaultWidthXToken)
                extractor.execute(c)
                width = extractor.width
                if width is not defaultWidthXToken:
                    # The following will be wrong if the width is added
                    # by a subroutine. Ouch!
                    c.program.pop(0)
                else:
                    width = defaultWidthX
                if width != newDefaultWidthX:
                    c.program.insert(0, width - newNominalWidthX)
            newcs[name] = cs[name]

    newfont.charset = chrset
    newfont.numGlyphs = len(chrset)
    newfont.strings.strings = glyphOrderStrings + storedNamesStrings

    return newcff


@add_method(ttLib.getTableClass("cmap"))
def merge(self, m, tables):
    if not hasattr(m, "cmap"):
        computeMegaCmap(m, tables)
    cmap = m.cmap

    cmapBmpOnly = {uni: gid for uni, gid in cmap.items() if uni <= 0xFFFF}
    self.tables = []
    module = ttLib.getTableModule("cmap")
    if len(cmapBmpOnly) != len(cmap):
        # format-12 required.
        cmapTable = module.cmap_classes[12](12)
        cmapTable.platformID = 3
        cmapTable.platEncID = 10
        cmapTable.language = 0
        cmapTable.cmap = cmap
        self.tables.append(cmapTable)
    # always create format-4
    cmapTable = module.cmap_classes[4](4)
    cmapTable.platformID = 3
    cmapTable.platEncID = 1
    cmapTable.language = 0
    cmapTable.cmap = cmapBmpOnly
    # ordered by platform then encoding
    self.tables.insert(0, cmapTable)

    uvsDict = m.uvsDict
    if uvsDict:
        # format-14
        uvsTable = module.cmap_classes[14](14)
        uvsTable.platformID = 0
        uvsTable.platEncID = 5
        uvsTable.language = 0
        uvsTable.cmap = {}
        uvsTable.uvsDict = uvsDict
        # ordered by platform then encoding
        self.tables.insert(0, uvsTable)
    self.tableVersion = 0
    self.numSubTables = len(self.tables)
    return self

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\M_E_T_A_.py ===
from fontTools.misc import sstruct
from fontTools.misc.textTools import byteord, safeEval
from . import DefaultTable
import pdb
import struct


METAHeaderFormat = """
		>	# big endian
		tableVersionMajor:			H
		tableVersionMinor:			H
		metaEntriesVersionMajor:	H
		metaEntriesVersionMinor:	H
		unicodeVersion:				L
		metaFlags:					H
		nMetaRecs:					H
"""
# This record is followed by nMetaRecs of METAGlyphRecordFormat.
# This in turn is followd by as many METAStringRecordFormat entries
# as specified by the METAGlyphRecordFormat entries
# this is followed by the strings specifried in the  METAStringRecordFormat
METAGlyphRecordFormat = """
		>	# big endian
		glyphID:			H
		nMetaEntry:			H
"""
# This record is followd by a variable data length field:
# 	USHORT or ULONG	hdrOffset
# Offset from start of META table to the beginning
# of this glyphs array of ns Metadata string entries.
# Size determined by metaFlags field
# METAGlyphRecordFormat entries must be sorted by glyph ID

METAStringRecordFormat = """
		>	# big endian
		labelID:			H
		stringLen:			H
"""
# This record is followd by a variable data length field:
# 	USHORT or ULONG	stringOffset
# METAStringRecordFormat entries must be sorted in order of labelID
# There may be more than one entry with the same labelID
# There may be more than one strign with the same content.

# Strings shall be Unicode UTF-8 encoded, and null-terminated.

METALabelDict = {
    0: "MojikumiX4051",  # An integer in the range 1-20
    1: "UNIUnifiedBaseChars",
    2: "BaseFontName",
    3: "Language",
    4: "CreationDate",
    5: "FoundryName",
    6: "FoundryCopyright",
    7: "OwnerURI",
    8: "WritingScript",
    10: "StrokeCount",
    11: "IndexingRadical",
}


def getLabelString(labelID):
    try:
        label = METALabelDict[labelID]
    except KeyError:
        label = "Unknown label"
    return str(label)


class table_M_E_T_A_(DefaultTable.DefaultTable):
    """Glyphlets META table

    The ``META`` table is used by Adobe's SING Glyphlets.

    See also https://web.archive.org/web/20080627183635/http://www.adobe.com/devnet/opentype/gdk/topic.html
    """

    dependencies = []

    def decompile(self, data, ttFont):
        dummy, newData = sstruct.unpack2(METAHeaderFormat, data, self)
        self.glyphRecords = []
        for i in range(self.nMetaRecs):
            glyphRecord, newData = sstruct.unpack2(
                METAGlyphRecordFormat, newData, GlyphRecord()
            )
            if self.metaFlags == 0:
                [glyphRecord.offset] = struct.unpack(">H", newData[:2])
                newData = newData[2:]
            elif self.metaFlags == 1:
                [glyphRecord.offset] = struct.unpack(">H", newData[:4])
                newData = newData[4:]
            else:
                assert 0, (
                    "The metaFlags field in the META table header has a value other than 0 or 1 :"
                    + str(self.metaFlags)
                )
            glyphRecord.stringRecs = []
            newData = data[glyphRecord.offset :]
            for j in range(glyphRecord.nMetaEntry):
                stringRec, newData = sstruct.unpack2(
                    METAStringRecordFormat, newData, StringRecord()
                )
                if self.metaFlags == 0:
                    [stringRec.offset] = struct.unpack(">H", newData[:2])
                    newData = newData[2:]
                else:
                    [stringRec.offset] = struct.unpack(">H", newData[:4])
                    newData = newData[4:]
                stringRec.string = data[
                    stringRec.offset : stringRec.offset + stringRec.stringLen
                ]
                glyphRecord.stringRecs.append(stringRec)
            self.glyphRecords.append(glyphRecord)

    def compile(self, ttFont):
        offsetOK = 0
        self.nMetaRecs = len(self.glyphRecords)
        count = 0
        while offsetOK != 1:
            count = count + 1
            if count > 4:
                pdb.set_trace()
            metaData = sstruct.pack(METAHeaderFormat, self)
            stringRecsOffset = len(metaData) + self.nMetaRecs * (
                6 + 2 * (self.metaFlags & 1)
            )
            stringRecSize = 6 + 2 * (self.metaFlags & 1)
            for glyphRec in self.glyphRecords:
                glyphRec.offset = stringRecsOffset
                if (glyphRec.offset > 65535) and ((self.metaFlags & 1) == 0):
                    self.metaFlags = self.metaFlags + 1
                    offsetOK = -1
                    break
                metaData = metaData + glyphRec.compile(self)
                stringRecsOffset = stringRecsOffset + (
                    glyphRec.nMetaEntry * stringRecSize
                )
                # this will be the String Record offset for the next GlyphRecord.
            if offsetOK == -1:
                offsetOK = 0
                continue

            # metaData now contains the header and all of the GlyphRecords. Its length should bw
            # the offset to the first StringRecord.
            stringOffset = stringRecsOffset
            for glyphRec in self.glyphRecords:
                assert glyphRec.offset == len(
                    metaData
                ), "Glyph record offset did not compile correctly! for rec:" + str(
                    glyphRec
                )
                for stringRec in glyphRec.stringRecs:
                    stringRec.offset = stringOffset
                    if (stringRec.offset > 65535) and ((self.metaFlags & 1) == 0):
                        self.metaFlags = self.metaFlags + 1
                        offsetOK = -1
                        break
                    metaData = metaData + stringRec.compile(self)
                    stringOffset = stringOffset + stringRec.stringLen
            if offsetOK == -1:
                offsetOK = 0
                continue

            if ((self.metaFlags & 1) == 1) and (stringOffset < 65536):
                self.metaFlags = self.metaFlags - 1
                continue
            else:
                offsetOK = 1

            # metaData now contains the header and all of the GlyphRecords and all of the String Records.
            # Its length should be the offset to the first string datum.
            for glyphRec in self.glyphRecords:
                for stringRec in glyphRec.stringRecs:
                    assert stringRec.offset == len(
                        metaData
                    ), "String offset did not compile correctly! for string:" + str(
                        stringRec.string
                    )
                    metaData = metaData + stringRec.string

        return metaData

    def toXML(self, writer, ttFont):
        writer.comment(
            "Lengths and number of entries in this table will be recalculated by the compiler"
        )
        writer.newline()
        formatstring, names, fixes = sstruct.getformat(METAHeaderFormat)
        for name in names:
            value = getattr(self, name)
            writer.simpletag(name, value=value)
            writer.newline()
        for glyphRec in self.glyphRecords:
            glyphRec.toXML(writer, ttFont)

    def fromXML(self, name, attrs, content, ttFont):
        if name == "GlyphRecord":
            if not hasattr(self, "glyphRecords"):
                self.glyphRecords = []
            glyphRec = GlyphRecord()
            self.glyphRecords.append(glyphRec)
            for element in content:
                if isinstance(element, str):
                    continue
                name, attrs, content = element
                glyphRec.fromXML(name, attrs, content, ttFont)
            glyphRec.offset = -1
            glyphRec.nMetaEntry = len(glyphRec.stringRecs)
        else:
            setattr(self, name, safeEval(attrs["value"]))


class GlyphRecord(object):
    def __init__(self):
        self.glyphID = -1
        self.nMetaEntry = -1
        self.offset = -1
        self.stringRecs = []

    def toXML(self, writer, ttFont):
        writer.begintag("GlyphRecord")
        writer.newline()
        writer.simpletag("glyphID", value=self.glyphID)
        writer.newline()
        writer.simpletag("nMetaEntry", value=self.nMetaEntry)
        writer.newline()
        for stringRec in self.stringRecs:
            stringRec.toXML(writer, ttFont)
        writer.endtag("GlyphRecord")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "StringRecord":
            stringRec = StringRecord()
            self.stringRecs.append(stringRec)
            for element in content:
                if isinstance(element, str):
                    continue
                stringRec.fromXML(name, attrs, content, ttFont)
            stringRec.stringLen = len(stringRec.string)
        else:
            setattr(self, name, safeEval(attrs["value"]))

    def compile(self, parentTable):
        data = sstruct.pack(METAGlyphRecordFormat, self)
        if parentTable.metaFlags == 0:
            datum = struct.pack(">H", self.offset)
        elif parentTable.metaFlags == 1:
            datum = struct.pack(">L", self.offset)
        data = data + datum
        return data

    def __repr__(self):
        return (
            "GlyphRecord[ glyphID: "
            + str(self.glyphID)
            + ", nMetaEntry: "
            + str(self.nMetaEntry)
            + ", offset: "
            + str(self.offset)
            + " ]"
        )


# XXX The following two functions are really broken around UTF-8 vs Unicode


def mapXMLToUTF8(string):
    uString = str()
    strLen = len(string)
    i = 0
    while i < strLen:
        prefixLen = 0
        if string[i : i + 3] == "&#x":
            prefixLen = 3
        elif string[i : i + 7] == "&amp;#x":
            prefixLen = 7
        if prefixLen:
            i = i + prefixLen
            j = i
            while string[i] != ";":
                i = i + 1
            valStr = string[j:i]

            uString = uString + chr(eval("0x" + valStr))
        else:
            uString = uString + chr(byteord(string[i]))
        i = i + 1

    return uString.encode("utf_8")


def mapUTF8toXML(string):
    uString = string.decode("utf_8")
    string = ""
    for uChar in uString:
        i = ord(uChar)
        if (i < 0x80) and (i > 0x1F):
            string = string + uChar
        else:
            string = string + "&#x" + hex(i)[2:] + ";"
    return string


class StringRecord(object):
    def toXML(self, writer, ttFont):
        writer.begintag("StringRecord")
        writer.newline()
        writer.simpletag("labelID", value=self.labelID)
        writer.comment(getLabelString(self.labelID))
        writer.newline()
        writer.newline()
        writer.simpletag("string", value=mapUTF8toXML(self.string))
        writer.newline()
        writer.endtag("StringRecord")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        for element in content:
            if isinstance(element, str):
                continue
            name, attrs, content = element
            value = attrs["value"]
            if name == "string":
                self.string = mapXMLToUTF8(value)
            else:
                setattr(self, name, safeEval(value))

    def compile(self, parentTable):
        data = sstruct.pack(METAStringRecordFormat, self)
        if parentTable.metaFlags == 0:
            datum = struct.pack(">H", self.offset)
        elif parentTable.metaFlags == 1:
            datum = struct.pack(">L", self.offset)
        data = data + datum
        return data

    def __repr__(self):
        return (
            "StringRecord [ labelID: "
            + str(self.labelID)
            + " aka "
            + getLabelString(self.labelID)
            + ", offset: "
            + str(self.offset)
            + ", length: "
            + str(self.stringLen)
            + ", string: "
            + self.string
            + " ]"
        )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\mistral\mistral_chat_transformation.py ===
"""
Transformation logic from OpenAI /v1/chat/completion format to Mistral's /chat/completion format.

Why separate file? Make it easy to see how transformation works

Docs - https://docs.mistral.ai/api/
"""

from typing import Any, Coroutine, List, Literal, Optional, Tuple, Union, overload, cast

from litellm.litellm_core_utils.prompt_templates.common_utils import (
    handle_messages_with_content_list_to_str_conversion,
    strip_none_values_from_message,
)
from litellm.llms.openai.chat.gpt_transformation import OpenAIGPTConfig
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.mistral import MistralToolCallMessage
from litellm.types.llms.openai import AllMessageValues


class MistralConfig(OpenAIGPTConfig):
    """
    Reference: https://docs.mistral.ai/api/

    The class `MistralConfig` provides configuration for the Mistral's Chat API interface. Below are the parameters:

    - `temperature` (number or null): Defines the sampling temperature to use, varying between 0 and 2. API Default - 0.7.

    - `top_p` (number or null): An alternative to sampling with temperature, used for nucleus sampling. API Default - 1.

    - `max_tokens` (integer or null): This optional parameter helps to set the maximum number of tokens to generate in the chat completion. API Default - null.

    - `tools` (list or null): A list of available tools for the model. Use this to specify functions for which the model can generate JSON inputs.

    - `tool_choice` (string - 'auto'/'any'/'none' or null): Specifies if/how functions are called. If set to none the model won't call a function and will generate a message instead. If set to auto the model can choose to either generate a message or call a function. If set to any the model is forced to call a function. Default - 'auto'.

    - `stop` (string or array of strings): Stop generation if this token is detected. Or if one of these tokens is detected when providing an array

    - `random_seed` (integer or null): The seed to use for random sampling. If set, different calls will generate deterministic results.

    - `safe_prompt` (boolean): Whether to inject a safety prompt before all conversations. API Default - 'false'.

    - `response_format` (object or null): An object specifying the format that the model must output. Setting to { "type": "json_object" } enables JSON mode, which guarantees the message the model generates is in JSON. When using JSON mode you MUST also instruct the model to produce JSON yourself with a system or a user message.
    """

    temperature: Optional[int] = None
    top_p: Optional[int] = None
    max_tokens: Optional[int] = None
    tools: Optional[list] = None
    tool_choice: Optional[Literal["auto", "any", "none"]] = None
    random_seed: Optional[int] = None
    safe_prompt: Optional[bool] = None
    response_format: Optional[dict] = None
    stop: Optional[Union[str, list]] = None

    def __init__(
        self,
        temperature: Optional[int] = None,
        top_p: Optional[int] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list] = None,
        tool_choice: Optional[Literal["auto", "any", "none"]] = None,
        random_seed: Optional[int] = None,
        safe_prompt: Optional[bool] = None,
        response_format: Optional[dict] = None,
        stop: Optional[Union[str, list]] = None,
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
            "stream",
            "temperature",
            "top_p",
            "max_tokens",
            "max_completion_tokens",
            "tools",
            "tool_choice",
            "seed",
            "stop",
            "response_format",
            "parallel_tool_calls",
        ]

        # Add reasoning support for magistral models
        if "magistral" in model.lower():
            supported_params.extend(["thinking", "reasoning_effort"])
            
        return supported_params

    def _map_tool_choice(self, tool_choice: str) -> str:
        if tool_choice == "auto" or tool_choice == "none":
            return tool_choice
        elif tool_choice == "required":
            return "any"
        else:  # openai 'tool_choice' object param not supported by Mistral API
            return "any"

    @staticmethod
    def _get_mistral_reasoning_system_prompt() -> str:
        """
        Returns the system prompt for Mistral reasoning models.
        Based on Mistral's documentation: https://docs.mistral.ai/capabilities/reasoning/
        """
        return """When solving problems, think step-by-step in <think> tags before providing your final answer. Use the following format:

<think>
Your step-by-step reasoning process. Be thorough and work through the problem carefully.
</think>

Then provide a clear, concise answer based on your reasoning."""

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        for param, value in non_default_params.items():
            if param == "max_tokens":
                optional_params["max_tokens"] = value
            if (
                param == "max_completion_tokens"
            ):  # max_completion_tokens should take priority
                optional_params["max_tokens"] = value
            if param == "tools":
                optional_params["tools"] = value
            if param == "stream" and value is True:
                optional_params["stream"] = value
            if param == "temperature":
                optional_params["temperature"] = value
            if param == "top_p":
                optional_params["top_p"] = value
            if param == "stop":
                optional_params["stop"] = value
            if param == "tool_choice" and isinstance(value, str):
                optional_params["tool_choice"] = self._map_tool_choice(
                    tool_choice=value
                )
            if param == "seed":
                optional_params["extra_body"] = {"random_seed": value}
            if param == "response_format":
                optional_params["response_format"] = value
            if param == "reasoning_effort" and "magistral" in model.lower():
                # Flag that we need to add reasoning system prompt
                optional_params["_add_reasoning_prompt"] = True
            if param == "thinking" and "magistral" in model.lower():
                # Flag that we need to add reasoning system prompt
                optional_params["_add_reasoning_prompt"] = True
            if param == "parallel_tool_calls":
                optional_params["parallel_tool_calls"] = value
        return optional_params

    def _get_openai_compatible_provider_info(
        self, api_base: Optional[str], api_key: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        # mistral is openai compatible, we just need to set this to custom_openai and have the api_base be https://api.mistral.ai
        api_base = (
            api_base
            or get_secret_str("MISTRAL_AZURE_API_BASE")  # for Azure AI Mistral
            or "https://api.mistral.ai/v1"
        )  # type: ignore

        # if api_base does not end with /v1 we add it
        if api_base is not None and not api_base.endswith(
            "/v1"
        ):  # Mistral always needs a /v1 at the end
            api_base = api_base + "/v1"
        dynamic_api_key = (
            api_key
            or get_secret_str("MISTRAL_AZURE_API_KEY")  # for Azure AI Mistral
            or get_secret_str("MISTRAL_API_KEY")
        )
        return api_base, dynamic_api_key

    @overload
    def _transform_messages(
        self, messages: List[AllMessageValues], model: str, is_async: Literal[True]
    ) -> Coroutine[Any, Any, List[AllMessageValues]]:
        ...

    @overload
    def _transform_messages(
        self,
        messages: List[AllMessageValues],
        model: str,
        is_async: Literal[False] = False,
    ) -> List[AllMessageValues]:
        ...

    def _transform_messages(
        self, messages: List[AllMessageValues], model: str, is_async: bool = False
    ) -> Union[List[AllMessageValues], Coroutine[Any, Any, List[AllMessageValues]]]:
        """
        - handles scenario where content is list and not string
        - content list is just text, and no images
        - if image passed in, then just return as is (user-intended)
        - if `name` is passed, then drop it for mistral API: https://github.com/BerriAI/litellm/issues/6696

        Motivation: mistral api doesn't support content as a list
        """
        ## 1. If 'image_url' in content, then return as is
        for m in messages:
            _content_block = m.get("content")
            if _content_block and isinstance(_content_block, list):
                for c in _content_block:
                    if c.get("type") == "image_url":
                        if is_async:
                            return super()._transform_messages(messages, model, True)
                        else:
                            return super()._transform_messages(messages, model, False)

        ## 2. If content is list, then convert to string
        messages = handle_messages_with_content_list_to_str_conversion(messages)

        ## 3. Handle name in message
        new_messages: List[AllMessageValues] = []
        for m in messages:
            m = MistralConfig._handle_name_in_message(m)
            m = MistralConfig._handle_tool_call_message(m)
            m = strip_none_values_from_message(m)  # prevents 'extra_forbidden' error
            new_messages.append(m)

        if is_async:
            return super()._transform_messages(new_messages, model, True)
        else:
            return super()._transform_messages(new_messages, model, False)

    def _add_reasoning_system_prompt_if_needed(
        self, 
        messages: List[AllMessageValues], 
        optional_params: dict
    ) -> List[AllMessageValues]:
        """
        Add reasoning system prompt for Mistral magistral models when reasoning_effort is specified.
        """
        if not optional_params.get("_add_reasoning_prompt", False):
            return messages
        
        # Check if there's already a system message
        has_system_message = any(msg.get("role") == "system" for msg in messages)
        
        if has_system_message:
            # Prepend reasoning instructions to existing system message
            for i, msg in enumerate(messages):
                if msg.get("role") == "system":
                    existing_content = msg.get("content", "")
                    reasoning_prompt = self._get_mistral_reasoning_system_prompt()
                    
                    # Handle both string and list content, preserving original format
                    if isinstance(existing_content, str):
                        # String content - prepend reasoning prompt
                        new_content: Union[str, list] = f"{reasoning_prompt}\n\n{existing_content}"
                    elif isinstance(existing_content, list):
                        # List content - prepend reasoning prompt as text block
                        new_content = [
                            {"type": "text", "text": reasoning_prompt + "\n\n"}
                        ] + existing_content
                    else:
                        # Fallback for any other type - convert to string
                        new_content = f"{reasoning_prompt}\n\n{str(existing_content)}"
                    
                    messages[i] = cast(AllMessageValues, {
                        **msg,
                        "content": new_content
                    })
                    break
        else:
            # Add new system message with reasoning instructions
            reasoning_message: AllMessageValues = cast(AllMessageValues, {
                "role": "system",
                "content": self._get_mistral_reasoning_system_prompt()
            })
            messages = [reasoning_message] + messages
        
        # Remove the internal flag
        optional_params.pop("_add_reasoning_prompt", None)
        return messages

    @classmethod
    def _handle_name_in_message(cls, message: AllMessageValues) -> AllMessageValues:
        """
        Mistral API only supports `name` in tool messages

        If role == tool, then we keep `name` if it's not an empty string
        Otherwise, we drop `name`
        """
        _name = message.get("name")  # type: ignore
        
        if _name is not None:
            # Remove name if not a tool message
            if message["role"] != "tool":
                message.pop("name", None)  # type: ignore
            # For tool messages, remove name if it's an empty string
            elif isinstance(_name, str) and len(_name.strip()) == 0:
                message.pop("name", None)  # type: ignore

        return message

    @classmethod
    def _handle_tool_call_message(cls, message: AllMessageValues) -> AllMessageValues:
        """
        Mistral API only supports tool_calls in Messages in `MistralToolCallMessage` spec
        """
        _tool_calls = message.get("tool_calls")
        mistral_tool_calls: List[MistralToolCallMessage] = []
        if _tool_calls is not None and isinstance(_tool_calls, list):
            for _tool in _tool_calls:
                _tool_call_message = MistralToolCallMessage(
                    id=_tool.get("id"),
                    type="function",
                    function=_tool.get("function"),  # type: ignore
                )
                mistral_tool_calls.append(_tool_call_message)
            message["tool_calls"] = mistral_tool_calls  # type: ignore
        return message

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        """
        Transform the overall request to be sent to the API.
        For magistral models, adds reasoning system prompt when reasoning_effort is specified.

        Returns:
            dict: The transformed request. Sent as the body of the API call.
        """
        # Add reasoning system prompt if needed (for magistral models)
        if "magistral" in model.lower() and optional_params.get("_add_reasoning_prompt", False):
            messages = self._add_reasoning_system_prompt_if_needed(messages, optional_params)
        
        # Call parent transform_request which handles _transform_messages
        return super().transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            headers=headers,
        )

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\installers.py ===
"""
    pygments.lexers.installers
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for installer/packager DSLs and formats.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, using, this, default
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Punctuation, Generic, Number, Whitespace

__all__ = ['NSISLexer', 'RPMSpecLexer',
           'DebianSourcesLexer', 'SourcesListLexer',
           'DebianControlLexer']


class NSISLexer(RegexLexer):
    """
    For NSIS scripts.
    """
    name = 'NSIS'
    url = 'http://nsis.sourceforge.net/'
    aliases = ['nsis', 'nsi', 'nsh']
    filenames = ['*.nsi', '*.nsh']
    mimetypes = ['text/x-nsis']
    version_added = '1.6'

    flags = re.IGNORECASE

    tokens = {
        'root': [
            (r'([;#].*)(\n)', bygroups(Comment, Whitespace)),
            (r"'.*?'", String.Single),
            (r'"', String.Double, 'str_double'),
            (r'`', String.Backtick, 'str_backtick'),
            include('macro'),
            include('interpol'),
            include('basic'),
            (r'\$\{[a-z_|][\w|]*\}', Keyword.Pseudo),
            (r'/[a-z_]\w*', Name.Attribute),
            (r'\s+', Whitespace),
            (r'[\w.]+', Text),
        ],
        'basic': [
            (r'(\n)(Function)(\s+)([._a-z][.\w]*)\b',
             bygroups(Whitespace, Keyword, Whitespace, Name.Function)),
            (r'\b([_a-z]\w*)(::)([a-z][a-z0-9]*)\b',
             bygroups(Keyword.Namespace, Punctuation, Name.Function)),
            (r'\b([_a-z]\w*)(:)', bygroups(Name.Label, Punctuation)),
            (r'(\b[ULS]|\B)([!<>=]?=|\<\>?|\>)\B', Operator),
            (r'[|+-]', Operator),
            (r'\\', Punctuation),
            (r'\b(Abort|Add(?:BrandingImage|Size)|'
             r'Allow(?:RootDirInstall|SkipFiles)|AutoCloseWindow|'
             r'BG(?:Font|Gradient)|BrandingText|BringToFront|Call(?:InstDLL)?|'
             r'(?:Sub)?Caption|ChangeUI|CheckBitmap|ClearErrors|CompletedText|'
             r'ComponentText|CopyFiles|CRCCheck|'
             r'Create(?:Directory|Font|Shortcut)|Delete(?:INI(?:Sec|Str)|'
             r'Reg(?:Key|Value))?|DetailPrint|DetailsButtonText|'
             r'Dir(?:Show|Text|Var|Verify)|(?:Disabled|Enabled)Bitmap|'
             r'EnableWindow|EnumReg(?:Key|Value)|Exch|Exec(?:Shell|Wait)?|'
             r'ExpandEnvStrings|File(?:BufSize|Close|ErrorText|Open|'
             r'Read(?:Byte)?|Seek|Write(?:Byte)?)?|'
             r'Find(?:Close|First|Next|Window)|FlushINI|Function(?:End)?|'
             r'Get(?:CurInstType|CurrentAddress|DlgItem|DLLVersion(?:Local)?|'
             r'ErrorLevel|FileTime(?:Local)?|FullPathName|FunctionAddress|'
             r'InstDirError|LabelAddress|TempFileName)|'
             r'Goto|HideWindow|Icon|'
             r'If(?:Abort|Errors|FileExists|RebootFlag|Silent)|'
             r'InitPluginsDir|Install(?:ButtonText|Colors|Dir(?:RegKey)?)|'
             r'Inst(?:ProgressFlags|Type(?:[GS]etText)?)|Int(?:CmpU?|Fmt|Op)|'
             r'IsWindow|LangString(?:UP)?|'
             r'License(?:BkColor|Data|ForceSelection|LangString|Text)|'
             r'LoadLanguageFile|LockWindow|Log(?:Set|Text)|MessageBox|'
             r'MiscButtonText|Name|Nop|OutFile|(?:Uninst)?Page(?:Ex(?:End)?)?|'
             r'PluginDir|Pop|Push|Quit|Read(?:(?:Env|INI|Reg)Str|RegDWORD)|'
             r'Reboot|(?:Un)?RegDLL|Rename|RequestExecutionLevel|ReserveFile|'
             r'Return|RMDir|SearchPath|Section(?:Divider|End|'
             r'(?:(?:Get|Set)(?:Flags|InstTypes|Size|Text))|Group(?:End)?|In)?|'
             r'SendMessage|Set(?:AutoClose|BrandingImage|Compress(?:ionLevel|'
             r'or(?:DictSize)?)?|CtlColors|CurInstType|DatablockOptimize|'
             r'DateSave|Details(?:Print|View)|Error(?:s|Level)|FileAttributes|'
             r'Font|OutPath|Overwrite|PluginUnload|RebootFlag|ShellVarContext|'
             r'Silent|StaticBkColor)|'
             r'Show(?:(?:I|Uni)nstDetails|Window)|Silent(?:Un)?Install|Sleep|'
             r'SpaceTexts|Str(?:CmpS?|Cpy|Len)|SubSection(?:End)?|'
             r'Uninstall(?:ButtonText|(?:Sub)?Caption|EXEName|Icon|Text)|'
             r'UninstPage|Var|VI(?:AddVersionKey|ProductVersion)|WindowIcon|'
             r'Write(?:INIStr|Reg(:?Bin|DWORD|(?:Expand)?Str)|Uninstaller)|'
             r'XPStyle)\b', Keyword),
            (r'\b(CUR|END|(?:FILE_ATTRIBUTE_)?'
             r'(?:ARCHIVE|HIDDEN|NORMAL|OFFLINE|READONLY|SYSTEM|TEMPORARY)|'
             r'HK(CC|CR|CU|DD|LM|PD|U)|'
             r'HKEY_(?:CLASSES_ROOT|CURRENT_(?:CONFIG|USER)|DYN_DATA|'
             r'LOCAL_MACHINE|PERFORMANCE_DATA|USERS)|'
             r'ID(?:ABORT|CANCEL|IGNORE|NO|OK|RETRY|YES)|'
             r'MB_(?:ABORTRETRYIGNORE|DEFBUTTON[1-4]|'
             r'ICON(?:EXCLAMATION|INFORMATION|QUESTION|STOP)|'
             r'OK(?:CANCEL)?|RETRYCANCEL|RIGHT|SETFOREGROUND|TOPMOST|USERICON|'
             r'YESNO(?:CANCEL)?)|SET|SHCTX|'
             r'SW_(?:HIDE|SHOW(?:MAXIMIZED|MINIMIZED|NORMAL))|'
             r'admin|all|auto|both|bottom|bzip2|checkbox|colored|current|false|'
             r'force|hide|highest|if(?:diff|newer)|lastused|leave|left|'
             r'listonly|lzma|nevershow|none|normal|off|on|pop|push|'
             r'radiobuttons|right|show|silent|silentlog|smooth|textonly|top|'
             r'true|try|user|zlib)\b', Name.Constant),
        ],
        'macro': [
            (r'\!(addincludedir(?:dir)?|addplugindir|appendfile|cd|define|'
             r'delfilefile|echo(?:message)?|else|endif|error|execute|'
             r'if(?:macro)?n?(?:def)?|include|insertmacro|macro(?:end)?|packhdr|'
             r'search(?:parse|replace)|system|tempfilesymbol|undef|verbose|'
             r'warning)\b', Comment.Preproc),
        ],
        'interpol': [
            (r'\$(R?[0-9])', Name.Builtin.Pseudo),    # registers
            (r'\$(ADMINTOOLS|APPDATA|CDBURN_AREA|COOKIES|COMMONFILES(?:32|64)|'
             r'DESKTOP|DOCUMENTS|EXE(?:DIR|FILE|PATH)|FAVORITES|FONTS|HISTORY|'
             r'HWNDPARENT|INTERNET_CACHE|LOCALAPPDATA|MUSIC|NETHOOD|PICTURES|'
             r'PLUGINSDIR|PRINTHOOD|PROFILE|PROGRAMFILES(?:32|64)|QUICKLAUNCH|'
             r'RECENT|RESOURCES(?:_LOCALIZED)?|SENDTO|SM(?:PROGRAMS|STARTUP)|'
             r'STARTMENU|SYSDIR|TEMP(?:LATES)?|VIDEOS|WINDIR|\{NSISDIR\})',
             Name.Builtin),
            (r'\$(CMDLINE|INSTDIR|OUTDIR|LANGUAGE)', Name.Variable.Global),
            (r'\$[a-z_]\w*', Name.Variable),
        ],
        'str_double': [
            (r'"', String.Double, '#pop'),
            (r'\$(\\[nrt"]|\$)', String.Escape),
            include('interpol'),
            (r'[^"]+', String.Double),
        ],
        'str_backtick': [
            (r'`', String.Double, '#pop'),
            (r'\$(\\[nrt"]|\$)', String.Escape),
            include('interpol'),
            (r'[^`]+', String.Double),
        ],
    }


class RPMSpecLexer(RegexLexer):
    """
    For RPM ``.spec`` files.
    """

    name = 'RPMSpec'
    aliases = ['spec']
    filenames = ['*.spec']
    mimetypes = ['text/x-rpm-spec']
    url = 'https://rpm-software-management.github.io/rpm/manual/spec.html'
    version_added = '1.6'

    _directives = ('(?:package|prep|build|install|clean|check|pre[a-z]*|'
                   'post[a-z]*|trigger[a-z]*|files)')

    tokens = {
        'root': [
            (r'#.*$', Comment),
            include('basic'),
        ],
        'description': [
            (r'^(%' + _directives + ')(.*)$',
             bygroups(Name.Decorator, Text), '#pop'),
            (r'\s+', Whitespace),
            (r'.', Text),
        ],
        'changelog': [
            (r'\*.*$', Generic.Subheading),
            (r'^(%' + _directives + ')(.*)$',
             bygroups(Name.Decorator, Text), '#pop'),
            (r'\s+', Whitespace),
            (r'.', Text),
        ],
        'string': [
            (r'"', String.Double, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|[0-7]{1,3})', String.Escape),
            include('interpol'),
            (r'.', String.Double),
        ],
        'basic': [
            include('macro'),
            (r'(?i)^(Name|Version|Release|Epoch|Summary|Group|License|Packager|'
             r'Vendor|Icon|URL|Distribution|Prefix|Patch[0-9]*|Source[0-9]*|'
             r'Requires\(?[a-z]*\)?|[a-z]+Req|Obsoletes|Suggests|Provides|Conflicts|'
             r'Build[a-z]+|[a-z]+Arch|Auto[a-z]+)(:)(.*)$',
             bygroups(Generic.Heading, Punctuation, using(this))),
            (r'^%description', Name.Decorator, 'description'),
            (r'^%changelog', Name.Decorator, 'changelog'),
            (r'^(%' + _directives + ')(.*)$', bygroups(Name.Decorator, Text)),
            (r'%(attr|defattr|dir|doc(?:dir)?|setup|config(?:ure)?|'
             r'make(?:install)|ghost|patch[0-9]+|find_lang|exclude|verify)',
             Keyword),
            include('interpol'),
            (r"'.*?'", String.Single),
            (r'"', String.Double, 'string'),
            (r'\s+', Whitespace),
            (r'.', Text),
        ],
        'macro': [
            (r'%define.*$', Comment.Preproc),
            (r'%\{\!\?.*%define.*\}', Comment.Preproc),
            (r'(%(?:if(?:n?arch)?|else(?:if)?|endif))(.*)$',
             bygroups(Comment.Preproc, Text)),
        ],
        'interpol': [
            (r'%\{?__[a-z_]+\}?', Name.Function),
            (r'%\{?_([a-z_]+dir|[a-z_]+path|prefix)\}?', Keyword.Pseudo),
            (r'%\{\?\w+\}', Name.Variable),
            (r'\$\{?RPM_[A-Z0-9_]+\}?', Name.Variable.Global),
            (r'%\{[a-zA-Z]\w+\}', Keyword.Constant),
        ]
    }


class DebianSourcesLexer(RegexLexer):
    """
    Lexer that highlights debian.sources files.
    """

    name = 'Debian Sources file'
    aliases = ['debian.sources']
    filenames = ['*.sources']
    version_added = '2.19'
    url = 'https://manpages.debian.org/bookworm/apt/sources.list.5.en.html#THE_DEB_AND_DEB-SRC_TYPES:_GENERAL_FORMAT'

    tokens = {
        'root': [
            (r'^(Signed-By)(:)(\s*)', bygroups(Keyword, Punctuation, Whitespace), 'signed-by'),
            (r'^([a-zA-Z\-0-9\.]*?)(:)(\s*)(.*?)$',
             bygroups(Keyword, Punctuation, Whitespace, String)),
        ],
        'signed-by': [
            (r' -----END PGP PUBLIC KEY BLOCK-----\n', Text, '#pop'),
            (r'.+\n', Text),
        ],        
    }


class SourcesListLexer(RegexLexer):
    """
    Lexer that highlights debian sources.list files.
    """

    name = 'Debian Sourcelist'
    aliases = ['debsources', 'sourceslist', 'sources.list']
    filenames = ['sources.list']
    version_added = '0.7'
    mimetype = ['application/x-debian-sourceslist']
    url = 'https://wiki.debian.org/SourcesList'

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'#.*?$', Comment),
            (r'^(deb(?:-src)?)(\s+)',
             bygroups(Keyword, Whitespace), 'distribution')
        ],
        'distribution': [
            (r'#.*?$', Comment, '#pop'),
            (r'\$\(ARCH\)', Name.Variable),
            (r'[^\s$[]+', String),
            (r'\[', String.Other, 'escaped-distribution'),
            (r'\$', String),
            (r'\s+', Whitespace, 'components')
        ],
        'escaped-distribution': [
            (r'\]', String.Other, '#pop'),
            (r'\$\(ARCH\)', Name.Variable),
            (r'[^\]$]+', String.Other),
            (r'\$', String.Other)
        ],
        'components': [
            (r'#.*?$', Comment, '#pop:2'),
            (r'$', Text, '#pop:2'),
            (r'\s+', Whitespace),
            (r'\S+', Keyword.Pseudo),
        ]
    }

    def analyse_text(text):
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('deb ') or line.startswith('deb-src '):
                return True


class DebianControlLexer(RegexLexer):
    """
    Lexer for Debian ``control`` files and ``apt-cache show <pkg>`` outputs.
    """
    name = 'Debian Control file'
    url = 'https://www.debian.org/doc/debian-policy/ch-controlfields.html'
    aliases = ['debcontrol', 'control']
    filenames = ['control']
    version_added = '0.9'

    tokens = {
        'root': [
            (r'^(Description)', Keyword, 'description'),
            (r'^(Maintainer|Uploaders|Changed-By)(:)(\s*)',
             bygroups(Keyword, Punctuation, Whitespace),
             'maintainer'),
            (r'^((?:Build-|Pre-)?Depends(?:-Indep|-Arch)?)(:)(\s*)',
             bygroups(Keyword, Punctuation, Whitespace), 'package_list'),
            (r'^(Recommends|Suggests|Enhances|Breaks|Replaces|Provides|Conflicts)(:)(\s*)',
             bygroups(Keyword, Punctuation, Whitespace), 'package_list'),
            (r'^((?:Python-)?Version)(:)(\s*)(\S+)$',
             bygroups(Keyword, Punctuation, Whitespace, Number)),
            (r'^((?:Installed-)?Size)(:)(\s*)(\S+)$',
             bygroups(Keyword, Punctuation, Whitespace, Number)),
            (r'^(MD5Sum|SHA1|SHA256)(:)(\s*)(\S+)$',
             bygroups(Keyword, Punctuation, Whitespace, Number)),
            (r'^([a-zA-Z\-0-9\.]*?)(:)(\s*)(.*?)$',
             bygroups(Keyword, Punctuation, Whitespace, String)),
        ],
        'maintainer': [
            (r'<[^>]+>$', Generic.Strong, '#pop'),
            (r'<[^>]+>', Generic.Strong),
            (r',\n?', Whitespace),
            (r'[^,<]+$', Text, '#pop'),
            (r'[^,<]+', Text),
        ],
        'description': [
            (r'(.*)(Homepage)(: )(\S+)',
             bygroups(Text, String, Name, Name.Class)),
            (r':.*\n', Generic.Strong),
            (r' .*\n', Text),
            default('#pop'),
        ],
        'package_list': [
            (r'(\$)(\{)(\w+)(\s*)(:)(\s*)(\w+)(\})',
             bygroups(Operator, Punctuation, Name.Entity, Whitespace,
                      Punctuation, Whitespace, Text, Punctuation)),
            (r'\(', Punctuation, 'package_list_vers'),
            (r'\|', Operator),
            (r'\n\s', Whitespace),
            (r'\n', Whitespace, '#pop'),
            (r'[,\s]', Text),
            (r'[+.a-zA-Z0-9-]+', Name.Function),
            (r'\[.*?\]', Name.Entity),
        ],
        'package_list_vers': [
            (r'\)', Punctuation, '#pop'),
            (r'([><=]+)(\s*)([^)]+)', bygroups(Operator, Whitespace, Number)),
        ]
    }

# === NexusCore/openenv\Lib\site-packages\jupyter_client\threaded.py ===
""" Defines a KernelClient that provides thread-safe sockets with async callbacks on message
replies.
"""
import asyncio
import atexit
import time
from concurrent.futures import Future
from functools import partial
from threading import Thread
from typing import Any, Dict, List, Optional

import zmq
from tornado.ioloop import IOLoop
from traitlets import Instance, Type
from traitlets.log import get_logger
from zmq.eventloop import zmqstream

from .channels import HBChannel
from .client import KernelClient
from .session import Session

# Local imports
# import ZMQError in top-level namespace, to avoid ugly attribute-error messages
# during garbage collection of threads at exit


class ThreadedZMQSocketChannel:
    """A ZMQ socket invoking a callback in the ioloop"""

    session = None
    socket = None
    ioloop = None
    stream = None
    _inspect = None

    def __init__(
        self,
        socket: Optional[zmq.Socket],
        session: Optional[Session],
        loop: Optional[IOLoop],
    ) -> None:
        """Create a channel.

        Parameters
        ----------
        socket : :class:`zmq.Socket`
            The ZMQ socket to use.
        session : :class:`session.Session`
            The session to use.
        loop
            A tornado ioloop to connect the socket to using a ZMQStream
        """
        super().__init__()

        self.socket = socket
        self.session = session
        self.ioloop = loop
        f: Future = Future()

        def setup_stream() -> None:
            try:
                assert self.socket is not None
                self.stream = zmqstream.ZMQStream(self.socket, self.ioloop)
                self.stream.on_recv(self._handle_recv)
            except Exception as e:
                f.set_exception(e)
            else:
                f.set_result(None)

        assert self.ioloop is not None
        self.ioloop.add_callback(setup_stream)
        # don't wait forever, raise any errors
        f.result(timeout=10)

    _is_alive = False

    def is_alive(self) -> bool:
        """Whether the channel is alive."""
        return self._is_alive

    def start(self) -> None:
        """Start the channel."""
        self._is_alive = True

    def stop(self) -> None:
        """Stop the channel."""
        self._is_alive = False

    def close(self) -> None:
        """Close the channel."""
        if self.stream is not None and self.ioloop is not None:
            # c.f.Future for threadsafe results
            f: Future = Future()

            def close_stream() -> None:
                try:
                    if self.stream is not None:
                        self.stream.close(linger=0)
                        self.stream = None
                except Exception as e:
                    f.set_exception(e)
                else:
                    f.set_result(None)

            self.ioloop.add_callback(close_stream)
            # wait for result
            try:
                f.result(timeout=5)
            except Exception as e:
                log = get_logger()
                msg = f"Error closing stream {self.stream}: {e}"
                log.warning(msg, RuntimeWarning, stacklevel=2)

        if self.socket is not None:
            try:
                self.socket.close(linger=0)
            except Exception:
                pass
            self.socket = None

    def send(self, msg: Dict[str, Any]) -> None:
        """Queue a message to be sent from the IOLoop's thread.

        Parameters
        ----------
        msg : message to send

        This is threadsafe, as it uses IOLoop.add_callback to give the loop's
        thread control of the action.
        """

        def thread_send() -> None:
            assert self.session is not None
            self.session.send(self.stream, msg)

        assert self.ioloop is not None
        self.ioloop.add_callback(thread_send)

    def _handle_recv(self, msg_list: List) -> None:
        """Callback for stream.on_recv.

        Unpacks message, and calls handlers with it.
        """
        assert self.ioloop is not None
        assert self.session is not None
        ident, smsg = self.session.feed_identities(msg_list)
        msg = self.session.deserialize(smsg)
        # let client inspect messages
        if self._inspect:
            self._inspect(msg)  # type:ignore[unreachable]
        self.call_handlers(msg)

    def call_handlers(self, msg: Dict[str, Any]) -> None:
        """This method is called in the ioloop thread when a message arrives.

        Subclasses should override this method to handle incoming messages.
        It is important to remember that this method is called in the thread
        so that some logic must be done to ensure that the application level
        handlers are called in the application thread.
        """
        pass

    def process_events(self) -> None:
        """Subclasses should override this with a method
        processing any pending GUI events.
        """
        pass

    def flush(self, timeout: float = 1.0) -> None:
        """Immediately processes all pending messages on this channel.

        This is only used for the IOPub channel.

        Callers should use this method to ensure that :meth:`call_handlers`
        has been called for all messages that have been received on the
        0MQ SUB socket of this channel.

        This method is thread safe.

        Parameters
        ----------
        timeout : float, optional
            The maximum amount of time to spend flushing, in seconds. The
            default is one second.
        """
        # We do the IOLoop callback process twice to ensure that the IOLoop
        # gets to perform at least one full poll.
        stop_time = time.monotonic() + timeout
        assert self.ioloop is not None
        if self.stream is None or self.stream.closed():
            # don't bother scheduling flush on a thread if we're closed
            _msg = "Attempt to flush closed stream"
            raise OSError(_msg)

        def flush(f: Any) -> None:
            try:
                self._flush()
            except Exception as e:
                f.set_exception(e)
            else:
                f.set_result(None)

        for _ in range(2):
            f: Future = Future()
            self.ioloop.add_callback(partial(flush, f))
            # wait for async flush, re-raise any errors
            timeout = max(stop_time - time.monotonic(), 0)
            try:
                f.result(max(stop_time - time.monotonic(), 0))
            except TimeoutError:
                # flush with a timeout means stop waiting, not raise
                return

    def _flush(self) -> None:
        """Callback for :method:`self.flush`."""
        assert self.stream is not None
        self.stream.flush()
        self._flushed = True


class IOLoopThread(Thread):
    """Run a pyzmq ioloop in a thread to send and receive messages"""

    _exiting = False
    ioloop = None

    def __init__(self) -> None:
        """Initialize an io loop thread."""
        super().__init__()
        self.daemon = True

    @staticmethod
    @atexit.register
    def _notice_exit() -> None:
        # Class definitions can be torn down during interpreter shutdown.
        # We only need to set _exiting flag if this hasn't happened.
        if IOLoopThread is not None:
            IOLoopThread._exiting = True

    def start(self) -> None:
        """Start the IOLoop thread

        Don't return until self.ioloop is defined,
        which is created in the thread
        """
        self._start_future: Future = Future()
        Thread.start(self)
        # wait for start, re-raise any errors
        self._start_future.result(timeout=10)

    def run(self) -> None:
        """Run my loop, ignoring EINTR events in the poller"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def assign_ioloop() -> None:
                self.ioloop = IOLoop.current()

            loop.run_until_complete(assign_ioloop())
        except Exception as e:
            self._start_future.set_exception(e)
        else:
            self._start_future.set_result(None)

        loop.run_until_complete(self._async_run())

    async def _async_run(self) -> None:
        """Run forever (until self._exiting is set)"""
        while not self._exiting:
            await asyncio.sleep(1)

    def stop(self) -> None:
        """Stop the channel's event loop and join its thread.

        This calls :meth:`~threading.Thread.join` and returns when the thread
        terminates. :class:`RuntimeError` will be raised if
        :meth:`~threading.Thread.start` is called again.
        """
        self._exiting = True
        self.join()
        self.close()
        self.ioloop = None

    def __del__(self) -> None:
        self.close()

    def close(self) -> None:
        """Close the io loop thread."""
        if self.ioloop is not None:
            try:
                self.ioloop.close(all_fds=True)
            except Exception:
                pass


class ThreadedKernelClient(KernelClient):
    """A KernelClient that provides thread-safe sockets with async callbacks on message replies."""

    @property
    def ioloop(self) -> Optional[IOLoop]:  # type:ignore[override]
        if self.ioloop_thread:
            return self.ioloop_thread.ioloop
        return None

    ioloop_thread = Instance(IOLoopThread, allow_none=True)

    def start_channels(
        self,
        shell: bool = True,
        iopub: bool = True,
        stdin: bool = True,
        hb: bool = True,
        control: bool = True,
    ) -> None:
        """Start the channels on the client."""
        self.ioloop_thread = IOLoopThread()
        self.ioloop_thread.start()

        if shell:
            self.shell_channel._inspect = self._check_kernel_info_reply

        super().start_channels(shell, iopub, stdin, hb, control)

    def _check_kernel_info_reply(self, msg: Dict[str, Any]) -> None:
        """This is run in the ioloop thread when the kernel info reply is received"""
        if msg["msg_type"] == "kernel_info_reply":
            self._handle_kernel_info_reply(msg)
            self.shell_channel._inspect = None

    def stop_channels(self) -> None:
        """Stop the channels on the client."""
        super().stop_channels()
        if self.ioloop_thread and self.ioloop_thread.is_alive():
            self.ioloop_thread.stop()

    iopub_channel_class = Type(ThreadedZMQSocketChannel)  # type:ignore[arg-type]
    shell_channel_class = Type(ThreadedZMQSocketChannel)  # type:ignore[arg-type]
    stdin_channel_class = Type(ThreadedZMQSocketChannel)  # type:ignore[arg-type]
    hb_channel_class = Type(HBChannel)  # type:ignore[arg-type]
    control_channel_class = Type(ThreadedZMQSocketChannel)  # type:ignore[arg-type]

    def is_alive(self) -> bool:
        """Is the kernel process still running?"""
        if self._hb_channel is not None:
            # We don't have access to the KernelManager,
            # so we use the heartbeat.
            return self._hb_channel.is_beating()
        # no heartbeat and not local, we can't tell if it's running,
        # so naively return True
        return True

# === NexusCore/openenv\Lib\site-packages\interpreter\terminal_interface\magic_commands.py ===
import json
import os
import subprocess
import sys
import time
from datetime import datetime

from ..core.utils.system_debug_info import system_info
from .utils.count_tokens import count_messages_tokens
from .utils.export_to_markdown import export_to_markdown


def handle_undo(self, arguments):
    # Removes all messages after the most recent user entry (and the entry itself).
    # Therefore user can jump back to the latest point of conversation.
    # Also gives a visual representation of the messages removed.

    if len(self.messages) == 0:
        return
    # Find the index of the last 'role': 'user' entry
    last_user_index = None
    for i, message in enumerate(self.messages):
        if message.get("role") == "user":
            last_user_index = i

    removed_messages = []

    # Remove all messages after the last 'role': 'user'
    if last_user_index is not None:
        removed_messages = self.messages[last_user_index:]
        self.messages = self.messages[:last_user_index]

    print("")  # Aesthetics.

    # Print out a preview of what messages were removed.
    for message in removed_messages:
        if "content" in message and message["content"] != None:
            self.display_message(
                f"**Removed message:** `\"{message['content'][:30]}...\"`"
            )
        elif "function_call" in message:
            self.display_message(
                f"**Removed codeblock**"
            )  # TODO: Could add preview of code removed here.

    print("")  # Aesthetics.


def handle_help(self, arguments):
    commands_description = {
        "%% [commands]": "Run commands in system shell",
        "%verbose [true/false]": "Toggle verbose mode. Without arguments or with 'true', it enters verbose mode. With 'false', it exits verbose mode.",
        "%reset": "Resets the current session.",
        "%undo": "Remove previous messages and its response from the message history.",
        "%save_message [path]": "Saves messages to a specified JSON path. If no path is provided, it defaults to 'messages.json'.",
        "%load_message [path]": "Loads messages from a specified JSON path. If no path is provided, it defaults to 'messages.json'.",
        "%tokens [prompt]": "EXPERIMENTAL: Calculate the tokens used by the next request based on the current conversation's messages and estimate the cost of that request; optionally provide a prompt to also calculate the tokens used by that prompt and the total amount of tokens that will be sent with the next request",
        "%help": "Show this help message.",
        "%info": "Show system and interpreter information",
        "%jupyter": "Export the conversation to a Jupyter notebook file",
        "%markdown [path]": "Export the conversation to a specified Markdown path. If no path is provided, it will be saved to the Downloads folder with a generated conversation name.",
    }

    base_message = ["> **Available Commands:**\n\n"]

    # Add each command and its description to the message
    for cmd, desc in commands_description.items():
        base_message.append(f"- `{cmd}`: {desc}\n")

    additional_info = [
        "\n\nFor further assistance, please join our community Discord or consider contributing to the project's development."
    ]

    # Combine the base message with the additional info
    full_message = base_message + additional_info

    self.display_message("".join(full_message))


def handle_verbose(self, arguments=None):
    if arguments == "" or arguments == "true":
        self.display_message("> Entered verbose mode")
        print("\n\nCurrent messages:\n")
        for message in self.messages:
            message = message.copy()
            if message["type"] == "image" and message.get("format") not in [
                "path",
                "description",
            ]:
                message["content"] = (
                    message["content"][:30] + "..." + message["content"][-30:]
                )
            print(message, "\n")
        print("\n")
        self.verbose = True
    elif arguments == "false":
        self.display_message("> Exited verbose mode")
        self.verbose = False
    else:
        self.display_message("> Unknown argument to verbose command.")


def handle_debug(self, arguments=None):
    if arguments == "" or arguments == "true":
        self.display_message("> Entered debug mode")
        print("\n\nCurrent messages:\n")
        for message in self.messages:
            message = message.copy()
            if message["type"] == "image" and message.get("format") not in [
                "path",
                "description",
            ]:
                message["content"] = (
                    message["content"][:30] + "..." + message["content"][-30:]
                )
            print(message, "\n")
        print("\n")
        self.debug = True
    elif arguments == "false":
        self.display_message("> Exited verbose mode")
        self.debug = False
    else:
        self.display_message("> Unknown argument to debug command.")


def handle_auto_run(self, arguments=None):
    if arguments == "" or arguments == "true":
        self.display_message("> Entered auto_run mode")
        self.auto_run = True
    elif arguments == "false":
        self.display_message("> Exited auto_run mode")
        self.auto_run = False
    else:
        self.display_message("> Unknown argument to auto_run command.")


def handle_info(self, arguments):
    system_info(self)


def handle_reset(self, arguments):
    self.reset()
    self.display_message("> Reset Done")


def default_handle(self, arguments):
    self.display_message("> Unknown command")
    handle_help(self, arguments)


def handle_save_message(self, json_path):
    if json_path == "":
        json_path = "messages.json"
    if not json_path.endswith(".json"):
        json_path += ".json"
    with open(json_path, "w") as f:
        json.dump(self.messages, f, indent=2)

    self.display_message(f"> messages json export to {os.path.abspath(json_path)}")


def handle_load_message(self, json_path):
    if json_path == "":
        json_path = "messages.json"
    if not json_path.endswith(".json"):
        json_path += ".json"
    with open(json_path, "r") as f:
        self.messages = json.load(f)

    self.display_message(f"> messages json loaded from {os.path.abspath(json_path)}")


def handle_count_tokens(self, prompt):
    messages = [{"role": "system", "message": self.system_message}] + self.messages

    outputs = []

    if len(self.messages) == 0:
        (conversation_tokens, conversation_cost) = count_messages_tokens(
            messages=messages, model=self.llm.model
        )
    else:
        (conversation_tokens, conversation_cost) = count_messages_tokens(
            messages=messages, model=self.llm.model
        )

    outputs.append(
        (
            f"> Tokens sent with next request as context: {conversation_tokens} (Estimated Cost: ${conversation_cost})"
        )
    )

    if prompt:
        (prompt_tokens, prompt_cost) = count_messages_tokens(
            messages=[prompt], model=self.llm.model
        )
        outputs.append(
            f"> Tokens used by this prompt: {prompt_tokens} (Estimated Cost: ${prompt_cost})"
        )

        total_tokens = conversation_tokens + prompt_tokens
        total_cost = conversation_cost + prompt_cost

        outputs.append(
            f"> Total tokens for next request with this prompt: {total_tokens} (Estimated Cost: ${total_cost})"
        )

    outputs.append(
        f"**Note**: This functionality is currently experimental and may not be accurate. Please report any issues you find to the [Open Interpreter GitHub repository](https://github.com/OpenInterpreter/open-interpreter)."
    )

    self.display_message("\n".join(outputs))


def get_downloads_path():
    if os.name == "nt":
        # For Windows
        downloads = os.path.join(os.environ["USERPROFILE"], "Downloads")
    else:
        # For MacOS and Linux
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        # For some GNU/Linux distros, there's no '~/Downloads' dir by default
        if not os.path.exists(downloads):
            os.makedirs(downloads)
    return downloads


def install_and_import(package):
    try:
        module = __import__(package)
    except ImportError:
        try:
            # Install the package silently with pip
            print("")
            print(f"Installing {package}...")
            print("")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            module = __import__(package)
        except subprocess.CalledProcessError:
            # If pip fails, try pip3
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip3", "install", package],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError:
                print(f"Failed to install package {package}.")
                return
    finally:
        globals()[package] = module
    return module


def jupyter(self, arguments):
    # Dynamically install nbformat if not already installed
    nbformat = install_and_import("nbformat")
    from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

    downloads = get_downloads_path()
    current_time = datetime.now()
    formatted_time = current_time.strftime("%m-%d-%y-%I%M%p")
    filename = f"open-interpreter-{formatted_time}.ipynb"
    notebook_path = os.path.join(downloads, filename)
    nb = new_notebook()
    cells = []

    for msg in self.messages:
        if msg["role"] == "user" and msg["type"] == "message":
            # Prefix user messages with '>' to render them as block quotes, so they stand out
            content = f"> {msg['content']}"
            cells.append(new_markdown_cell(content))
        elif msg["role"] == "assistant" and msg["type"] == "message":
            cells.append(new_markdown_cell(msg["content"]))
        elif msg["type"] == "code":
            # Handle the language of the code cell
            if "format" in msg and msg["format"]:
                language = msg["format"]
            else:
                language = "python"  # Default to Python if no format specified
            code_cell = new_code_cell(msg["content"])
            code_cell.metadata.update({"language": language})
            cells.append(code_cell)

    nb["cells"] = cells

    with open(notebook_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)

    print("")
    self.display_message(
        f"Jupyter notebook file exported to {os.path.abspath(notebook_path)}"
    )


def markdown(self, export_path: str):
    # If it's an empty conversations
    if len(self.messages) == 0:
        print("No messages to export.")
        return

    # If user doesn't specify the export path, then save the exported PDF in '~/Downloads'
    if not export_path:
        export_path = get_downloads_path() + f"/{self.conversation_filename[:-4]}md"

    export_to_markdown(self.messages, export_path)


def handle_magic_command(self, user_input):
    # Handle shell
    if user_input.startswith("%%"):
        code = user_input[2:].strip()
        self.computer.run("shell", code, stream=False, display=True)
        print("")
        return

    # split the command into the command and the arguments, by the first whitespace
    switch = {
        "help": handle_help,
        "verbose": handle_verbose,
        "debug": handle_debug,
        "auto_run": handle_auto_run,
        "reset": handle_reset,
        "save_message": handle_save_message,
        "load_message": handle_load_message,
        "undo": handle_undo,
        "tokens": handle_count_tokens,
        "info": handle_info,
        "jupyter": jupyter,
        "markdown": markdown,
    }

    user_input = user_input[1:].strip()  # Capture the part after the `%`
    command = user_input.split(" ")[0]
    arguments = user_input[len(command) :].strip()

    if command == "debug":
        print(
            "\n`%debug` / `--debug_mode` has been renamed to `%verbose` / `--verbose`.\n"
        )
        time.sleep(1.5)
        command = "verbose"

    action = switch.get(
        command, default_handle
    )  # Get the function from the dictionary, or default_handle if not found
    action(self, arguments)  # Execute the function

# === NexusCore/openenv\Lib\site-packages\joblib\externals\loky\backend\resource_tracker.py ===
###############################################################################
# Server process to keep track of unlinked resources, like folders and
# semaphores and clean them.
#
# author: Thomas Moreau
#
# Adapted from multiprocessing/resource_tracker.py
#  * add some VERBOSE logging,
#  * add support to track folders,
#  * add Windows support,
#  * refcounting scheme to avoid unlinking resources still in use.
#
# On Unix we run a server process which keeps track of unlinked
# resources. The server ignores SIGINT and SIGTERM and reads from a
# pipe. The resource_tracker implements a reference counting scheme: each time
# a Python process anticipates the shared usage of a resource by another
# process, it signals the resource_tracker of this shared usage, and in return,
# the resource_tracker increments the resource's reference count by 1.
# Similarly, when access to a resource is closed by a Python process, the
# process notifies the resource_tracker by asking it to decrement the
# resource's reference count by 1.  When the reference count drops to 0, the
# resource_tracker attempts to clean up the underlying resource.

# Finally, every other process connected to the resource tracker has a copy of
# the writable end of the pipe used to communicate with it, so the resource
# tracker gets EOF when all other processes have exited. Then the
# resource_tracker process unlinks any remaining leaked resources (with
# reference count above 0)

# For semaphores, this is important because the system only supports a limited
# number of named semaphores, and they will not be automatically removed till
# the next reboot.  Without this resource tracker process, "killall python"
# would probably leave unlinked semaphores.

# Note that this behavior differs from CPython's resource_tracker, which only
# implements list of shared resources, and not a proper refcounting scheme.
# Also, CPython's resource tracker will only attempt to cleanup those shared
# resources once all processes connected to the resource tracker have exited.


import os
import shutil
import sys
import signal
import warnings
from _multiprocessing import sem_unlink
from multiprocessing import util
from multiprocessing.resource_tracker import (
    ResourceTracker as _ResourceTracker,
)

from . import spawn

if sys.platform == "win32":
    import _winapi
    import msvcrt
    from multiprocessing.reduction import duplicate


__all__ = ["ensure_running", "register", "unregister"]

_HAVE_SIGMASK = hasattr(signal, "pthread_sigmask")
_IGNORED_SIGNALS = (signal.SIGINT, signal.SIGTERM)

_CLEANUP_FUNCS = {"folder": shutil.rmtree, "file": os.unlink}

if os.name == "posix":
    _CLEANUP_FUNCS["semlock"] = sem_unlink


VERBOSE = False


class ResourceTracker(_ResourceTracker):
    """Resource tracker with refcounting scheme.

    This class is an extension of the multiprocessing ResourceTracker class
    which implements a reference counting scheme to avoid unlinking shared
    resources still in use in other processes.

    This feature is notably used by `joblib.Parallel` to share temporary
    folders and memory mapped files between the main process and the worker
    processes.

    The actual implementation of the refcounting scheme is in the main
    function, which is run in a dedicated process.
    """

    def maybe_unlink(self, name, rtype):
        """Decrement the refcount of a resource, and delete it if it hits 0"""
        self.ensure_running()
        self._send("MAYBE_UNLINK", name, rtype)

    def ensure_running(self):
        """Make sure that resource tracker process is running.

        This can be run from any process.  Usually a child process will use
        the resource created by its parent."""
        with self._lock:
            if self._fd is not None:
                # resource tracker was launched before, is it still running?
                if self._check_alive():
                    # => still alive
                    return
                # => dead, launch it again
                os.close(self._fd)
                if os.name == "posix":
                    try:
                        # At this point, the resource_tracker process has been
                        # killed or crashed. Let's remove the process entry
                        # from the process table to avoid zombie processes.
                        os.waitpid(self._pid, 0)
                    except OSError:
                        # The process was terminated or is a child from an
                        # ancestor of the current process.
                        pass
                self._fd = None
                self._pid = None

                warnings.warn(
                    "resource_tracker: process died unexpectedly, "
                    "relaunching.  Some folders/sempahores might "
                    "leak."
                )

            fds_to_pass = []
            try:
                fds_to_pass.append(sys.stderr.fileno())
            except Exception:
                pass

            r, w = os.pipe()
            if sys.platform == "win32":
                _r = duplicate(msvcrt.get_osfhandle(r), inheritable=True)
                os.close(r)
                r = _r

            cmd = f"from {main.__module__} import main; main({r}, {VERBOSE})"
            try:
                fds_to_pass.append(r)
                # process will out live us, so no need to wait on pid
                exe = spawn.get_executable()
                args = [exe, *util._args_from_interpreter_flags(), "-c", cmd]
                util.debug(f"launching resource tracker: {args}")
                # bpo-33613: Register a signal mask that will block the
                # signals.  This signal mask will be inherited by the child
                # that is going to be spawned and will protect the child from a
                # race condition that can make the child die before it
                # registers signal handlers for SIGINT and SIGTERM. The mask is
                # unregistered after spawning the child.
                try:
                    if _HAVE_SIGMASK:
                        signal.pthread_sigmask(
                            signal.SIG_BLOCK, _IGNORED_SIGNALS
                        )
                    pid = spawnv_passfds(exe, args, fds_to_pass)
                finally:
                    if _HAVE_SIGMASK:
                        signal.pthread_sigmask(
                            signal.SIG_UNBLOCK, _IGNORED_SIGNALS
                        )
            except BaseException:
                os.close(w)
                raise
            else:
                self._fd = w
                self._pid = pid
            finally:
                if sys.platform == "win32":
                    _winapi.CloseHandle(r)
                else:
                    os.close(r)

    def __del__(self):
        # ignore error due to trying to clean up child process which has already been
        # shutdown on windows See https://github.com/joblib/loky/pull/450
        # This is only required if __del__ is defined
        if not hasattr(_ResourceTracker, "__del__"):
            return
        try:
            super().__del__()
        except ChildProcessError:
            pass


_resource_tracker = ResourceTracker()
ensure_running = _resource_tracker.ensure_running
register = _resource_tracker.register
maybe_unlink = _resource_tracker.maybe_unlink
unregister = _resource_tracker.unregister
getfd = _resource_tracker.getfd


def main(fd, verbose=0):
    """Run resource tracker."""
    # protect the process from ^C and "killall python" etc
    if verbose:
        util.log_to_stderr(level=util.DEBUG)

    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)

    if _HAVE_SIGMASK:
        signal.pthread_sigmask(signal.SIG_UNBLOCK, _IGNORED_SIGNALS)

    for f in (sys.stdin, sys.stdout):
        try:
            f.close()
        except Exception:
            pass

    if verbose:
        util.debug("Main resource tracker is running")

    registry = {rtype: {} for rtype in _CLEANUP_FUNCS.keys()}
    try:
        # keep track of registered/unregistered resources
        if sys.platform == "win32":
            fd = msvcrt.open_osfhandle(fd, os.O_RDONLY)
        with open(fd, "rb") as f:
            while True:
                line = f.readline()
                if line == b"":  # EOF
                    break
                try:
                    splitted = line.strip().decode("ascii").split(":")
                    # name can potentially contain separator symbols (for
                    # instance folders on Windows)
                    cmd, name, rtype = (
                        splitted[0],
                        ":".join(splitted[1:-1]),
                        splitted[-1],
                    )

                    if cmd == "PROBE":
                        continue

                    if rtype not in _CLEANUP_FUNCS:
                        raise ValueError(
                            f"Cannot register {name} for automatic cleanup: "
                            f"unknown resource type ({rtype}). Resource type "
                            "should be one of the following: "
                            f"{list(_CLEANUP_FUNCS.keys())}"
                        )

                    if cmd == "REGISTER":
                        if name not in registry[rtype]:
                            registry[rtype][name] = 1
                        else:
                            registry[rtype][name] += 1

                        if verbose:
                            util.debug(
                                "[ResourceTracker] incremented refcount of "
                                f"{rtype} {name} "
                                f"(current {registry[rtype][name]})"
                            )
                    elif cmd == "UNREGISTER":
                        del registry[rtype][name]
                        if verbose:
                            util.debug(
                                f"[ResourceTracker] unregister {name} {rtype}: "
                                f"registry({len(registry)})"
                            )
                    elif cmd == "MAYBE_UNLINK":
                        registry[rtype][name] -= 1
                        if verbose:
                            util.debug(
                                "[ResourceTracker] decremented refcount of "
                                f"{rtype} {name} "
                                f"(current {registry[rtype][name]})"
                            )

                        if registry[rtype][name] == 0:
                            del registry[rtype][name]
                            try:
                                if verbose:
                                    util.debug(
                                        f"[ResourceTracker] unlink {name}"
                                    )
                                _CLEANUP_FUNCS[rtype](name)
                            except Exception as e:
                                warnings.warn(
                                    f"resource_tracker: {name}: {e!r}"
                                )

                    else:
                        raise RuntimeError(f"unrecognized command {cmd!r}")
                except BaseException:
                    try:
                        sys.excepthook(*sys.exc_info())
                    except BaseException:
                        pass
    finally:
        # all processes have terminated; cleanup any remaining resources
        def _unlink_resources(rtype_registry, rtype):
            if rtype_registry:
                try:
                    warnings.warn(
                        "resource_tracker: There appear to be "
                        f"{len(rtype_registry)} leaked {rtype} objects to "
                        "clean up at shutdown"
                    )
                except Exception:
                    pass
            for name in rtype_registry:
                # For some reason the process which created and registered this
                # resource has failed to unregister it. Presumably it has
                # died.  We therefore clean it up.
                try:
                    _CLEANUP_FUNCS[rtype](name)
                    if verbose:
                        util.debug(f"[ResourceTracker] unlink {name}")
                except Exception as e:
                    warnings.warn(f"resource_tracker: {name}: {e!r}")

        for rtype, rtype_registry in registry.items():
            if rtype == "folder":
                continue
            else:
                _unlink_resources(rtype_registry, rtype)

        # The default cleanup routine for folders deletes everything inside
        # those folders recursively, which can include other resources tracked
        # by the resource tracker). To limit the risk of the resource tracker
        # attempting to delete twice a resource (once as part of a tracked
        # folder, and once as a resource), we delete the folders after all
        # other resource types.
        if "folder" in registry:
            _unlink_resources(registry["folder"], "folder")

    if verbose:
        util.debug("resource tracker shut down")


def spawnv_passfds(path, args, passfds):
    if sys.platform != "win32":
        args = [arg.encode("utf-8") for arg in args]
        path = path.encode("utf-8")
        return util.spawnv_passfds(path, args, passfds)
    else:
        passfds = sorted(passfds)
        cmd = " ".join(f'"{x}"' for x in args)
        try:
            _, ht, pid, _ = _winapi.CreateProcess(
                path, cmd, None, None, True, 0, None, None, None
            )
            _winapi.CloseHandle(ht)
        except BaseException:
            pass
        return pid

# === NexusCore/openenv\Lib\site-packages\nltk\metrics\confusionmatrix.py ===
# Natural Language Toolkit: Confusion Matrices
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
#         Tom Aarsen <>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.probability import FreqDist


class ConfusionMatrix:
    """
    The confusion matrix between a list of reference values and a
    corresponding list of test values.  Entry *[r,t]* of this
    matrix is a count of the number of times that the reference value
    *r* corresponds to the test value *t*.  E.g.:

        >>> from nltk.metrics import ConfusionMatrix
        >>> ref  = 'DET NN VB DET JJ NN NN IN DET NN'.split()
        >>> test = 'DET VB VB DET NN NN NN IN DET NN'.split()
        >>> cm = ConfusionMatrix(ref, test)
        >>> print(cm['NN', 'NN'])
        3

    Note that the diagonal entries *Ri=Tj* of this matrix
    corresponds to correct values; and the off-diagonal entries
    correspond to incorrect values.
    """

    def __init__(self, reference, test, sort_by_count=False):
        """
        Construct a new confusion matrix from a list of reference
        values and a corresponding list of test values.

        :type reference: list
        :param reference: An ordered list of reference values.
        :type test: list
        :param test: A list of values to compare against the
            corresponding reference values.
        :raise ValueError: If ``reference`` and ``length`` do not have
            the same length.
        """
        if len(reference) != len(test):
            raise ValueError("Lists must have the same length.")

        # Get a list of all values.
        if sort_by_count:
            ref_fdist = FreqDist(reference)
            test_fdist = FreqDist(test)

            def key(v):
                return -(ref_fdist[v] + test_fdist[v])

            values = sorted(set(reference + test), key=key)
        else:
            values = sorted(set(reference + test))

        # Construct a value->index dictionary
        indices = {val: i for (i, val) in enumerate(values)}

        # Make a confusion matrix table.
        confusion = [[0 for _ in values] for _ in values]
        max_conf = 0  # Maximum confusion
        for w, g in zip(reference, test):
            confusion[indices[w]][indices[g]] += 1
            max_conf = max(max_conf, confusion[indices[w]][indices[g]])

        #: A list of all values in ``reference`` or ``test``.
        self._values = values
        #: A dictionary mapping values in ``self._values`` to their indices.
        self._indices = indices
        #: The confusion matrix itself (as a list of lists of counts).
        self._confusion = confusion
        #: The greatest count in ``self._confusion`` (used for printing).
        self._max_conf = max_conf
        #: The total number of values in the confusion matrix.
        self._total = len(reference)
        #: The number of correct (on-diagonal) values in the matrix.
        self._correct = sum(confusion[i][i] for i in range(len(values)))

    def __getitem__(self, li_lj_tuple):
        """
        :return: The number of times that value ``li`` was expected and
        value ``lj`` was given.
        :rtype: int
        """
        (li, lj) = li_lj_tuple
        i = self._indices[li]
        j = self._indices[lj]
        return self._confusion[i][j]

    def __repr__(self):
        return f"<ConfusionMatrix: {self._correct}/{self._total} correct>"

    def __str__(self):
        return self.pretty_format()

    def pretty_format(
        self,
        show_percents=False,
        values_in_chart=True,
        truncate=None,
        sort_by_count=False,
    ):
        """
        :return: A multi-line string representation of this confusion matrix.
        :type truncate: int
        :param truncate: If specified, then only show the specified
            number of values.  Any sorting (e.g., sort_by_count)
            will be performed before truncation.
        :param sort_by_count: If true, then sort by the count of each
            label in the reference data.  I.e., labels that occur more
            frequently in the reference label will be towards the left
            edge of the matrix, and labels that occur less frequently
            will be towards the right edge.

        @todo: add marginals?
        """
        confusion = self._confusion

        values = self._values
        if sort_by_count:
            values = sorted(
                values, key=lambda v: -sum(self._confusion[self._indices[v]])
            )

        if truncate:
            values = values[:truncate]

        if values_in_chart:
            value_strings = ["%s" % val for val in values]
        else:
            value_strings = [str(n + 1) for n in range(len(values))]

        # Construct a format string for row values
        valuelen = max(len(val) for val in value_strings)
        value_format = "%" + repr(valuelen) + "s | "
        # Construct a format string for matrix entries
        if show_percents:
            entrylen = 6
            entry_format = "%5.1f%%"
            zerostr = "     ."
        else:
            entrylen = len(repr(self._max_conf))
            entry_format = "%" + repr(entrylen) + "d"
            zerostr = " " * (entrylen - 1) + "."

        # Write the column values.
        s = ""
        for i in range(valuelen):
            s += (" " * valuelen) + " |"
            for val in value_strings:
                if i >= valuelen - len(val):
                    s += val[i - valuelen + len(val)].rjust(entrylen + 1)
                else:
                    s += " " * (entrylen + 1)
            s += " |\n"

        # Write a dividing line
        s += "{}-+-{}+\n".format("-" * valuelen, "-" * ((entrylen + 1) * len(values)))

        # Write the entries.
        for val, li in zip(value_strings, values):
            i = self._indices[li]
            s += value_format % val
            for lj in values:
                j = self._indices[lj]
                if confusion[i][j] == 0:
                    s += zerostr
                elif show_percents:
                    s += entry_format % (100.0 * confusion[i][j] / self._total)
                else:
                    s += entry_format % confusion[i][j]
                if i == j:
                    prevspace = s.rfind(" ")
                    s = s[:prevspace] + "<" + s[prevspace + 1 :] + ">"
                else:
                    s += " "
            s += "|\n"

        # Write a dividing line
        s += "{}-+-{}+\n".format("-" * valuelen, "-" * ((entrylen + 1) * len(values)))

        # Write a key
        s += "(row = reference; col = test)\n"
        if not values_in_chart:
            s += "Value key:\n"
            for i, value in enumerate(values):
                s += "%6d: %s\n" % (i + 1, value)

        return s

    def key(self):
        values = self._values
        str = "Value key:\n"
        indexlen = len(repr(len(values) - 1))
        key_format = "  %" + repr(indexlen) + "d: %s\n"
        str += "".join([key_format % (i, values[i]) for i in range(len(values))])
        return str

    def recall(self, value):
        """Given a value in the confusion matrix, return the recall
        that corresponds to this value. The recall is defined as:

        - *r* = true positive / (true positive + false positive)

        and can loosely be considered the ratio of how often ``value``
        was predicted correctly relative to how often ``value`` was
        the true result.

        :param value: value used in the ConfusionMatrix
        :return: the recall corresponding to ``value``.
        :rtype: float
        """
        # Number of times `value` was correct, and also predicted
        TP = self[value, value]
        # Number of times `value` was correct
        TP_FN = sum(self[value, pred_value] for pred_value in self._values)
        if TP_FN == 0:
            return 0.0
        return TP / TP_FN

    def precision(self, value):
        """Given a value in the confusion matrix, return the precision
        that corresponds to this value. The precision is defined as:

        - *p* = true positive / (true positive + false negative)

        and can loosely be considered the ratio of how often ``value``
        was predicted correctly relative to the number of predictions
        for ``value``.

        :param value: value used in the ConfusionMatrix
        :return: the precision corresponding to ``value``.
        :rtype: float
        """
        # Number of times `value` was correct, and also predicted
        TP = self[value, value]
        # Number of times `value` was predicted
        TP_FP = sum(self[real_value, value] for real_value in self._values)
        if TP_FP == 0:
            return 0.0
        return TP / TP_FP

    def f_measure(self, value, alpha=0.5):
        """
        Given a value used in the confusion matrix, return the f-measure
        that corresponds to this value. The f-measure is the harmonic mean
        of the ``precision`` and ``recall``, weighted by ``alpha``.
        In particular, given the precision *p* and recall *r* defined by:

        - *p* = true positive / (true positive + false negative)
        - *r* = true positive / (true positive + false positive)

        The f-measure is:

        - *1/(alpha/p + (1-alpha)/r)*

        With ``alpha = 0.5``, this reduces to:

        - *2pr / (p + r)*

        :param value: value used in the ConfusionMatrix
        :param alpha: Ratio of the cost of false negative compared to false
            positives. Defaults to 0.5, where the costs are equal.
        :type alpha: float
        :return: the F-measure corresponding to ``value``.
        :rtype: float
        """
        p = self.precision(value)
        r = self.recall(value)
        if p == 0.0 or r == 0.0:
            return 0.0
        return 1.0 / (alpha / p + (1 - alpha) / r)

    def evaluate(self, alpha=0.5, truncate=None, sort_by_count=False):
        """
        Tabulate the **recall**, **precision** and **f-measure**
        for each value in this confusion matrix.

        >>> reference = "DET NN VB DET JJ NN NN IN DET NN".split()
        >>> test = "DET VB VB DET NN NN NN IN DET NN".split()
        >>> cm = ConfusionMatrix(reference, test)
        >>> print(cm.evaluate())
        Tag | Prec.  | Recall | F-measure
        ----+--------+--------+-----------
        DET | 1.0000 | 1.0000 | 1.0000
         IN | 1.0000 | 1.0000 | 1.0000
         JJ | 0.0000 | 0.0000 | 0.0000
         NN | 0.7500 | 0.7500 | 0.7500
         VB | 0.5000 | 1.0000 | 0.6667
        <BLANKLINE>

        :param alpha: Ratio of the cost of false negative compared to false
            positives, as used in the f-measure computation. Defaults to 0.5,
            where the costs are equal.
        :type alpha: float
        :param truncate: If specified, then only show the specified
            number of values. Any sorting (e.g., sort_by_count)
            will be performed before truncation. Defaults to None
        :type truncate: int, optional
        :param sort_by_count: Whether to sort the outputs on frequency
            in the reference label. Defaults to False.
        :type sort_by_count: bool, optional
        :return: A tabulated recall, precision and f-measure string
        :rtype: str
        """
        tags = self._values

        # Apply keyword parameters
        if sort_by_count:
            tags = sorted(tags, key=lambda v: -sum(self._confusion[self._indices[v]]))
        if truncate:
            tags = tags[:truncate]

        tag_column_len = max(max(len(tag) for tag in tags), 3)

        # Construct the header
        s = (
            f"{' ' * (tag_column_len - 3)}Tag | Prec.  | Recall | F-measure\n"
            f"{'-' * tag_column_len}-+--------+--------+-----------\n"
        )

        # Construct the body
        for tag in tags:
            s += (
                f"{tag:>{tag_column_len}} | "
                f"{self.precision(tag):<6.4f} | "
                f"{self.recall(tag):<6.4f} | "
                f"{self.f_measure(tag, alpha=alpha):.4f}\n"
            )

        return s


def demo():
    reference = "DET NN VB DET JJ NN NN IN DET NN".split()
    test = "DET VB VB DET NN NN NN IN DET NN".split()
    print("Reference =", reference)
    print("Test    =", test)
    print("Confusion matrix:")
    print(ConfusionMatrix(reference, test))
    print(ConfusionMatrix(reference, test).pretty_format(sort_by_count=True))

    print(ConfusionMatrix(reference, test).recall("VB"))


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\openai\lib\streaming\responses\_types.py ===
from __future__ import annotations

from typing_extensions import TypeAlias

from ....types.responses import ParsedResponse

ParsedResponseSnapshot: TypeAlias = ParsedResponse[object]
"""Snapshot type representing an in-progress accumulation of
a `ParsedResponse` object.
"""

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc4108.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
# Modified by Russ Housley to add items from the verified errata.
# Modified by Russ Housley to add maps for use with opentypes.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# CMS Firmware Wrapper
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc4108.txt
# https://www.rfc-editor.org/errata_search.php?rfc=4108
#


from pyasn1.type import univ, char, namedtype, namedval, tag, constraint, useful

from pyasn1_modules import rfc5280
from pyasn1_modules import rfc5652

MAX = float('inf')


class HardwareSerialEntry(univ.Choice):
    pass

HardwareSerialEntry.componentType = namedtype.NamedTypes(
    namedtype.NamedType('all', univ.Null()),
    namedtype.NamedType('single', univ.OctetString()),
    namedtype.NamedType('block', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('low', univ.OctetString()),
        namedtype.NamedType('high', univ.OctetString())
    ))
    )
)


class HardwareModules(univ.Sequence):
    pass

HardwareModules.componentType = namedtype.NamedTypes(
    namedtype.NamedType('hwType', univ.ObjectIdentifier()),
    namedtype.NamedType('hwSerialEntries', univ.SequenceOf(componentType=HardwareSerialEntry()))
)


class CommunityIdentifier(univ.Choice):
    pass

CommunityIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('communityOID', univ.ObjectIdentifier()),
    namedtype.NamedType('hwModuleList', HardwareModules())
)



class PreferredPackageIdentifier(univ.Sequence):
    pass

PreferredPackageIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('fwPkgID', univ.ObjectIdentifier()),
    namedtype.NamedType('verNum', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, MAX)))
)


class PreferredOrLegacyPackageIdentifier(univ.Choice):
    pass

PreferredOrLegacyPackageIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('preferred', PreferredPackageIdentifier()),
    namedtype.NamedType('legacy', univ.OctetString())
)


class CurrentFWConfig(univ.Sequence):
    pass

CurrentFWConfig.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('fwPkgType', univ.Integer()),
    namedtype.NamedType('fwPkgName', PreferredOrLegacyPackageIdentifier())
)


class PreferredOrLegacyStalePackageIdentifier(univ.Choice):
    pass

PreferredOrLegacyStalePackageIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('preferredStaleVerNum', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, MAX))),
    namedtype.NamedType('legacyStaleVersion', univ.OctetString())
)


class FirmwarePackageLoadErrorCode(univ.Enumerated):
    pass

FirmwarePackageLoadErrorCode.namedValues = namedval.NamedValues(
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
    ('signatureFailure', 15),
    ('contentTypeMismatch', 16),
    ('badEncryptedData', 17),
    ('unprotectedAttrsPresent', 18),
    ('badEncryptContent', 19),
    ('badEncryptAlgorithm', 20),
    ('missingCiphertext', 21),
    ('noDecryptKey', 22),
    ('decryptFailure', 23),
    ('badCompressAlgorithm', 24),
    ('missingCompressedContent', 25),
    ('decompressFailure', 26),
    ('wrongHardware', 27),
    ('stalePackage', 28),
    ('notInCommunity', 29),
    ('unsupportedPackageType', 30),
    ('missingDependency', 31),
    ('wrongDependencyVersion', 32),
    ('insufficientMemory', 33),
    ('badFirmware', 34),
    ('unsupportedParameters', 35),
    ('breaksDependency', 36),
    ('otherError', 99)
)


class VendorLoadErrorCode(univ.Integer):
    pass


# Wrapped Firmware Key Unsigned Attribute and Object Identifier

id_aa_wrappedFirmwareKey = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.39')

class WrappedFirmwareKey(rfc5652.EnvelopedData):
    pass


# Firmware Package Information Signed Attribute and Object Identifier

id_aa_firmwarePackageInfo = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.42')

class FirmwarePackageInfo(univ.Sequence):
    pass

FirmwarePackageInfo.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('fwPkgType', univ.Integer()),
    namedtype.OptionalNamedType('dependencies', univ.SequenceOf(componentType=PreferredOrLegacyPackageIdentifier()))
)

FirmwarePackageInfo.sizeSpec = univ.Sequence.sizeSpec + constraint.ValueSizeConstraint(1, 2)


# Community Identifiers Signed Attribute and Object Identifier

id_aa_communityIdentifiers = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.40')

class CommunityIdentifiers(univ.SequenceOf):
    pass

CommunityIdentifiers.componentType = CommunityIdentifier()


# Implemented Compression Algorithms Signed Attribute and Object Identifier

id_aa_implCompressAlgs = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.43')

class ImplementedCompressAlgorithms(univ.SequenceOf):
    pass

ImplementedCompressAlgorithms.componentType = univ.ObjectIdentifier()


# Implemented Cryptographic Algorithms Signed Attribute and Object Identifier

id_aa_implCryptoAlgs = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.38')

class ImplementedCryptoAlgorithms(univ.SequenceOf):
    pass

ImplementedCryptoAlgorithms.componentType = univ.ObjectIdentifier()


# Decrypt Key Identifier Signed Attribute and Object Identifier

id_aa_decryptKeyID = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.37')

class DecryptKeyIdentifier(univ.OctetString):
    pass


# Target Hardware Identifier Signed Attribute and Object Identifier

id_aa_targetHardwareIDs = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.36')

class TargetHardwareIdentifiers(univ.SequenceOf):
    pass

TargetHardwareIdentifiers.componentType = univ.ObjectIdentifier()


# Firmware Package Identifier Signed Attribute and Object Identifier

id_aa_firmwarePackageID = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.35')

class FirmwarePackageIdentifier(univ.Sequence):
    pass

FirmwarePackageIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('name', PreferredOrLegacyPackageIdentifier()),
    namedtype.OptionalNamedType('stale', PreferredOrLegacyStalePackageIdentifier())
)


# Firmware Package Message Digest Signed Attribute and Object Identifier

id_aa_fwPkgMessageDigest = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.41')

class FirmwarePackageMessageDigest(univ.Sequence):
    pass

FirmwarePackageMessageDigest.componentType = namedtype.NamedTypes(
    namedtype.NamedType('algorithm', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('msgDigest', univ.OctetString())
)


# Firmware Package Load Error Report Content Type and Object Identifier

class FWErrorVersion(univ.Integer):
    pass

FWErrorVersion.namedValues = namedval.NamedValues(
    ('v1', 1)
)


id_ct_firmwareLoadError = univ.ObjectIdentifier('1.2.840.113549.1.9.16.1.18')

class FirmwarePackageLoadError(univ.Sequence):
    pass

FirmwarePackageLoadError.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('version', FWErrorVersion().subtype(value='v1')),
    namedtype.NamedType('hwType', univ.ObjectIdentifier()),
    namedtype.NamedType('hwSerialNum', univ.OctetString()),
    namedtype.NamedType('errorCode', FirmwarePackageLoadErrorCode()),
    namedtype.OptionalNamedType('vendorErrorCode', VendorLoadErrorCode()),
    namedtype.OptionalNamedType('fwPkgName', PreferredOrLegacyPackageIdentifier()),
    namedtype.OptionalNamedType('config', univ.SequenceOf(componentType=CurrentFWConfig()).subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


# Firmware Package Load Receipt Content Type and Object Identifier

class FWReceiptVersion(univ.Integer):
    pass

FWReceiptVersion.namedValues = namedval.NamedValues(
    ('v1', 1)
)


id_ct_firmwareLoadReceipt = univ.ObjectIdentifier('1.2.840.113549.1.9.16.1.17')

class FirmwarePackageLoadReceipt(univ.Sequence):
    pass

FirmwarePackageLoadReceipt.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('version', FWReceiptVersion().subtype(value='v1')),
    namedtype.NamedType('hwType', univ.ObjectIdentifier()),
    namedtype.NamedType('hwSerialNum', univ.OctetString()),
    namedtype.NamedType('fwPkgName', PreferredOrLegacyPackageIdentifier()),
    namedtype.OptionalNamedType('trustAnchorKeyID', univ.OctetString()),
    namedtype.OptionalNamedType('decryptKeyID', univ.OctetString().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


# Firmware Package Content Type and Object Identifier

id_ct_firmwarePackage = univ.ObjectIdentifier('1.2.840.113549.1.9.16.1.16')

class FirmwarePkgData(univ.OctetString):
    pass


# Other Name syntax for Hardware Module Name

id_on_hardwareModuleName = univ.ObjectIdentifier('1.3.6.1.5.5.7.8.4')

class HardwareModuleName(univ.Sequence):
    pass

HardwareModuleName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('hwType', univ.ObjectIdentifier()),
    namedtype.NamedType('hwSerialNum', univ.OctetString())
)


# Map of Attribute Type OIDs to Attributes is added to the
# ones that are in rfc5652.py

_cmsAttributesMapUpdate = {
    id_aa_wrappedFirmwareKey: WrappedFirmwareKey(),
    id_aa_firmwarePackageInfo: FirmwarePackageInfo(),
    id_aa_communityIdentifiers: CommunityIdentifiers(),
    id_aa_implCompressAlgs: ImplementedCompressAlgorithms(),
    id_aa_implCryptoAlgs: ImplementedCryptoAlgorithms(),
    id_aa_decryptKeyID: DecryptKeyIdentifier(),
    id_aa_targetHardwareIDs: TargetHardwareIdentifiers(),
    id_aa_firmwarePackageID: FirmwarePackageIdentifier(),
    id_aa_fwPkgMessageDigest: FirmwarePackageMessageDigest(),
}

rfc5652.cmsAttributesMap.update(_cmsAttributesMapUpdate)


# Map of Content Type OIDs to Content Types is added to the
# ones that are in rfc5652.py

_cmsContentTypesMapUpdate = {
    id_ct_firmwareLoadError: FirmwarePackageLoadError(),
    id_ct_firmwareLoadReceipt: FirmwarePackageLoadReceipt(),
    id_ct_firmwarePackage: FirmwarePkgData(),
}

rfc5652.cmsContentTypesMap.update(_cmsContentTypesMapUpdate)


# Map of Other Name OIDs to Other Name is added to the
# ones that are in rfc5280.py

_anotherNameMapUpdate = {
    id_on_hardwareModuleName: HardwareModuleName(),
}

rfc5280.anotherNameMap.update(_anotherNameMapUpdate)

# === NexusCore/openenv\Lib\site-packages\tornado\autoreload.py ===
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

"""Automatically restart the server when a source file is modified.

Most applications should not access this module directly.  Instead,
pass the keyword argument ``autoreload=True`` to the
`tornado.web.Application` constructor (or ``debug=True``, which
enables this setting and several others).  This will enable autoreload
mode as well as checking for changes to templates and static
resources.  Note that restarting is a destructive operation and any
requests in progress will be aborted when the process restarts.  (If
you want to disable autoreload while using other debug-mode features,
pass both ``debug=True`` and ``autoreload=False``).

This module can also be used as a command-line wrapper around scripts
such as unit test runners.  See the `main` method for details.

The command-line wrapper and Application debug modes can be used together.
This combination is encouraged as the wrapper catches syntax errors and
other import-time failures, while debug mode catches changes once
the server has started.

This module will not work correctly when `.HTTPServer`'s multi-process
mode is used.

Reloading loses any Python interpreter command-line arguments (e.g. ``-u``)
because it re-executes Python using ``sys.executable`` and ``sys.argv``.
Additionally, modifying these variables will cause reloading to behave
incorrectly.

"""

import os
import sys

# sys.path handling
# -----------------
#
# If a module is run with "python -m", the current directory (i.e. "")
# is automatically prepended to sys.path, but not if it is run as
# "path/to/file.py".  The processing for "-m" rewrites the former to
# the latter, so subsequent executions won't have the same path as the
# original.
#
# Conversely, when run as path/to/file.py, the directory containing
# file.py gets added to the path, which can cause confusion as imports
# may become relative in spite of the future import.
#
# We address the former problem by reconstructing the original command
# line before re-execution so the new process will
# see the correct path.  We attempt to address the latter problem when
# tornado.autoreload is run as __main__.

if __name__ == "__main__":
    # This sys.path manipulation must come before our imports (as much
    # as possible - if we introduced a tornado.sys or tornado.os
    # module we'd be in trouble), or else our imports would become
    # relative again despite the future import.
    #
    # There is a separate __main__ block at the end of the file to call main().
    if sys.path[0] == os.path.dirname(__file__):
        del sys.path[0]

import functools
import importlib.abc
import os
import pkgutil
import sys
import traceback
import types
import subprocess
import weakref

from tornado import ioloop
from tornado.log import gen_log
from tornado import process

try:
    import signal
except ImportError:
    signal = None  # type: ignore

from typing import Callable, Dict, Optional, List, Union

# os.execv is broken on Windows and can't properly parse command line
# arguments and executable name if they contain whitespaces. subprocess
# fixes that behavior.
_has_execv = sys.platform != "win32"

_watched_files = set()
_reload_hooks = []
_reload_attempted = False
_io_loops: "weakref.WeakKeyDictionary[ioloop.IOLoop, bool]" = (
    weakref.WeakKeyDictionary()
)
_autoreload_is_main = False
_original_argv: Optional[List[str]] = None
_original_spec = None


def start(check_time: int = 500) -> None:
    """Begins watching source files for changes.

    .. versionchanged:: 5.0
       The ``io_loop`` argument (deprecated since version 4.1) has been removed.
    """
    io_loop = ioloop.IOLoop.current()
    if io_loop in _io_loops:
        return
    _io_loops[io_loop] = True
    if len(_io_loops) > 1:
        gen_log.warning("tornado.autoreload started more than once in the same process")
    modify_times: Dict[str, float] = {}
    callback = functools.partial(_reload_on_update, modify_times)
    scheduler = ioloop.PeriodicCallback(callback, check_time)
    scheduler.start()


def wait() -> None:
    """Wait for a watched file to change, then restart the process.

    Intended to be used at the end of scripts like unit test runners,
    to run the tests again after any source file changes (but see also
    the command-line interface in `main`)
    """
    io_loop = ioloop.IOLoop()
    io_loop.add_callback(start)
    io_loop.start()


def watch(filename: str) -> None:
    """Add a file to the watch list.

    All imported modules are watched by default.
    """
    _watched_files.add(filename)


def add_reload_hook(fn: Callable[[], None]) -> None:
    """Add a function to be called before reloading the process.

    Note that for open file and socket handles it is generally
    preferable to set the ``FD_CLOEXEC`` flag (using `fcntl` or
    `os.set_inheritable`) instead of using a reload hook to close them.
    """
    _reload_hooks.append(fn)


def _reload_on_update(modify_times: Dict[str, float]) -> None:
    if _reload_attempted:
        # We already tried to reload and it didn't work, so don't try again.
        return
    if process.task_id() is not None:
        # We're in a child process created by fork_processes.  If child
        # processes restarted themselves, they'd all restart and then
        # all call fork_processes again.
        return
    for module in list(sys.modules.values()):
        # Some modules play games with sys.modules (e.g. email/__init__.py
        # in the standard library), and occasionally this can cause strange
        # failures in getattr.  Just ignore anything that's not an ordinary
        # module.
        if not isinstance(module, types.ModuleType):
            continue
        path = getattr(module, "__file__", None)
        if not path:
            continue
        if path.endswith(".pyc") or path.endswith(".pyo"):
            path = path[:-1]
        _check_file(modify_times, path)
    for path in _watched_files:
        _check_file(modify_times, path)


def _check_file(modify_times: Dict[str, float], path: str) -> None:
    try:
        modified = os.stat(path).st_mtime
    except Exception:
        return
    if path not in modify_times:
        modify_times[path] = modified
        return
    if modify_times[path] != modified:
        gen_log.info("%s modified; restarting server", path)
        _reload()


def _reload() -> None:
    global _reload_attempted
    _reload_attempted = True
    for fn in _reload_hooks:
        fn()
    if sys.platform != "win32":
        # Clear the alarm signal set by
        # ioloop.set_blocking_log_threshold so it doesn't fire
        # after the exec.
        signal.setitimer(signal.ITIMER_REAL, 0, 0)
    # sys.path fixes: see comments at top of file.  If __main__.__spec__
    # exists, we were invoked with -m and the effective path is about to
    # change on re-exec.  Reconstruct the original command line to
    # ensure that the new process sees the same path we did.
    if _autoreload_is_main:
        assert _original_argv is not None
        spec = _original_spec
        argv = _original_argv
    else:
        spec = getattr(sys.modules["__main__"], "__spec__", None)
        argv = sys.argv
    if spec and spec.name != "__main__":
        # __spec__ is set in two cases: when running a module, and when running a directory. (when
        # running a file, there is no spec). In the former case, we must pass -m to maintain the
        # module-style behavior (setting sys.path), even though python stripped -m from its argv at
        # startup. If sys.path is exactly __main__, we're running a directory and should fall
        # through to the non-module behavior.
        #
        # Some of this, including the use of exactly __main__ as a spec for directory mode,
        # is documented at https://docs.python.org/3/library/runpy.html#runpy.run_path
        argv = ["-m", spec.name] + argv[1:]

    if not _has_execv:
        subprocess.Popen([sys.executable] + argv)
        os._exit(0)
    else:
        os.execv(sys.executable, [sys.executable] + argv)


_USAGE = """
  python -m tornado.autoreload -m module.to.run [args...]
  python -m tornado.autoreload path/to/script.py [args...]
"""


def main() -> None:
    """Command-line wrapper to re-run a script whenever its source changes.

    Scripts may be specified by filename or module name::

        python -m tornado.autoreload -m tornado.test.runtests
        python -m tornado.autoreload tornado/test/runtests.py

    Running a script with this wrapper is similar to calling
    `tornado.autoreload.wait` at the end of the script, but this wrapper
    can catch import-time problems like syntax errors that would otherwise
    prevent the script from reaching its call to `wait`.
    """
    # Remember that we were launched with autoreload as main.
    # The main module can be tricky; set the variables both in our globals
    # (which may be __main__) and the real importable version.
    #
    # We use optparse instead of the newer argparse because we want to
    # mimic the python command-line interface which requires stopping
    # parsing at the first positional argument. optparse supports
    # this but as far as I can tell argparse does not.
    import optparse
    import tornado.autoreload

    global _autoreload_is_main
    global _original_argv, _original_spec
    tornado.autoreload._autoreload_is_main = _autoreload_is_main = True
    original_argv = sys.argv
    tornado.autoreload._original_argv = _original_argv = original_argv
    original_spec = getattr(sys.modules["__main__"], "__spec__", None)
    tornado.autoreload._original_spec = _original_spec = original_spec

    parser = optparse.OptionParser(
        prog="python -m tornado.autoreload",
        usage=_USAGE,
        epilog="Either -m or a path must be specified, but not both",
    )
    parser.disable_interspersed_args()
    parser.add_option("-m", dest="module", metavar="module", help="module to run")
    parser.add_option(
        "--until-success",
        action="store_true",
        help="stop reloading after the program exist successfully (status code 0)",
    )
    opts, rest = parser.parse_args()
    if opts.module is None:
        if not rest:
            print("Either -m or a path must be specified", file=sys.stderr)
            sys.exit(1)
        path = rest[0]
        sys.argv = rest[:]
    else:
        path = None
        sys.argv = [sys.argv[0]] + rest

    # SystemExit.code is typed funny: https://github.com/python/typeshed/issues/8513
    # All we care about is truthiness
    exit_status: Union[int, str, None] = 1
    try:
        import runpy

        if opts.module is not None:
            runpy.run_module(opts.module, run_name="__main__", alter_sys=True)
        else:
            assert path is not None
            runpy.run_path(path, run_name="__main__")
    except SystemExit as e:
        exit_status = e.code
        gen_log.info("Script exited with status %s", e.code)
    except Exception as e:
        gen_log.warning("Script exited with uncaught exception", exc_info=True)
        # If an exception occurred at import time, the file with the error
        # never made it into sys.modules and so we won't know to watch it.
        # Just to make sure we've covered everything, walk the stack trace
        # from the exception and watch every file.
        for filename, lineno, name, line in traceback.extract_tb(sys.exc_info()[2]):
            watch(filename)
        if isinstance(e, SyntaxError):
            # SyntaxErrors are special:  their innermost stack frame is fake
            # so extract_tb won't see it and we have to get the filename
            # from the exception object.
            if e.filename is not None:
                watch(e.filename)
    else:
        exit_status = 0
        gen_log.info("Script exited normally")
    # restore sys.argv so subsequent executions will include autoreload
    sys.argv = original_argv

    if opts.module is not None:
        assert opts.module is not None
        # runpy did a fake import of the module as __main__, but now it's
        # no longer in sys.modules.  Figure out where it is and watch it.
        loader = pkgutil.get_loader(opts.module)
        if loader is not None and isinstance(loader, importlib.abc.FileLoader):
            watch(loader.get_filename())
    if opts.until_success and not exit_status:
        return
    wait()


if __name__ == "__main__":
    # See also the other __main__ block at the top of the file, which modifies
    # sys.path before our imports
    main()

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_mcp\mcp_client.py ===
import json
import logging
from contextlib import AsyncExitStack
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterable, Dict, List, Literal, Optional, Union, overload

from typing_extensions import NotRequired, TypeAlias, TypedDict, Unpack

from ...utils._runtime import get_hf_hub_version
from .._generated._async_client import AsyncInferenceClient
from .._generated.types import (
    ChatCompletionInputMessage,
    ChatCompletionInputTool,
    ChatCompletionStreamOutput,
    ChatCompletionStreamOutputDeltaToolCall,
)
from .._providers import PROVIDER_OR_POLICY_T
from .utils import format_result


if TYPE_CHECKING:
    from mcp import ClientSession

logger = logging.getLogger(__name__)

# Type alias for tool names
ToolName: TypeAlias = str

ServerType: TypeAlias = Literal["stdio", "sse", "http"]


class StdioServerParameters_T(TypedDict):
    command: str
    args: NotRequired[List[str]]
    env: NotRequired[Dict[str, str]]
    cwd: NotRequired[Union[str, Path, None]]


class SSEServerParameters_T(TypedDict):
    url: str
    headers: NotRequired[Dict[str, Any]]
    timeout: NotRequired[float]
    sse_read_timeout: NotRequired[float]


class StreamableHTTPParameters_T(TypedDict):
    url: str
    headers: NotRequired[dict[str, Any]]
    timeout: NotRequired[timedelta]
    sse_read_timeout: NotRequired[timedelta]
    terminate_on_close: NotRequired[bool]


class MCPClient:
    """
    Client for connecting to one or more MCP servers and processing chat completions with tools.

    <Tip warning={true}>

    This class is experimental and might be subject to breaking changes in the future without prior notice.

    </Tip>

    Args:
        model (`str`, `optional`):
            The model to run inference with. Can be a model id hosted on the Hugging Face Hub, e.g. `meta-llama/Meta-Llama-3-8B-Instruct`
            or a URL to a deployed Inference Endpoint or other local or remote endpoint.
        provider (`str`, *optional*):
            Name of the provider to use for inference. Defaults to "auto" i.e. the first of the providers available for the model, sorted by the user's order in https://hf.co/settings/inference-providers.
            If model is a URL or `base_url` is passed, then `provider` is not used.
        base_url (`str`, *optional*):
            The base URL to run inference. Defaults to None.
        api_key (`str`, `optional`):
            Token to use for authentication. Will default to the locally Hugging Face saved token if not provided. You can also use your own provider API key to interact directly with the provider's service.
    """

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        provider: Optional[PROVIDER_OR_POLICY_T] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        # Initialize MCP sessions as a dictionary of ClientSession objects
        self.sessions: Dict[ToolName, "ClientSession"] = {}
        self.exit_stack = AsyncExitStack()
        self.available_tools: List[ChatCompletionInputTool] = []
        # To be able to send the model in the payload if `base_url` is provided
        if model is None and base_url is None:
            raise ValueError("At least one of `model` or `base_url` should be set in `MCPClient`.")
        self.payload_model = model
        self.client = AsyncInferenceClient(
            model=None if base_url is not None else model,
            provider=provider,
            api_key=api_key,
            base_url=base_url,
        )

    async def __aenter__(self):
        """Enter the context manager"""
        await self.client.__aenter__()
        await self.exit_stack.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager"""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
        await self.cleanup()

    async def cleanup(self):
        """Clean up resources"""
        await self.client.close()
        await self.exit_stack.aclose()

    @overload
    async def add_mcp_server(self, type: Literal["stdio"], **params: Unpack[StdioServerParameters_T]): ...

    @overload
    async def add_mcp_server(self, type: Literal["sse"], **params: Unpack[SSEServerParameters_T]): ...

    @overload
    async def add_mcp_server(self, type: Literal["http"], **params: Unpack[StreamableHTTPParameters_T]): ...

    async def add_mcp_server(self, type: ServerType, **params: Any):
        """Connect to an MCP server

        Args:
            type (`str`):
                Type of the server to connect to. Can be one of:
                - "stdio": Standard input/output server (local)
                - "sse": Server-sent events (SSE) server
                - "http": StreamableHTTP server
            **params (`Dict[str, Any]`):
                Server parameters that can be either:
                    - For stdio servers:
                        - command (str): The command to run the MCP server
                        - args (List[str], optional): Arguments for the command
                        - env (Dict[str, str], optional): Environment variables for the command
                        - cwd (Union[str, Path, None], optional): Working directory for the command
                    - For SSE servers:
                        - url (str): The URL of the SSE server
                        - headers (Dict[str, Any], optional): Headers for the SSE connection
                        - timeout (float, optional): Connection timeout
                        - sse_read_timeout (float, optional): SSE read timeout
                    - For StreamableHTTP servers:
                        - url (str): The URL of the StreamableHTTP server
                        - headers (Dict[str, Any], optional): Headers for the StreamableHTTP connection
                        - timeout (timedelta, optional): Connection timeout
                        - sse_read_timeout (timedelta, optional): SSE read timeout
                        - terminate_on_close (bool, optional): Whether to terminate on close
        """
        from mcp import ClientSession, StdioServerParameters
        from mcp import types as mcp_types

        # Determine server type and create appropriate parameters
        if type == "stdio":
            # Handle stdio server
            from mcp.client.stdio import stdio_client

            logger.info(f"Connecting to stdio MCP server with command: {params['command']} {params.get('args', [])}")

            client_kwargs = {"command": params["command"]}
            for key in ["args", "env", "cwd"]:
                if params.get(key) is not None:
                    client_kwargs[key] = params[key]
            server_params = StdioServerParameters(**client_kwargs)
            read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
        elif type == "sse":
            # Handle SSE server
            from mcp.client.sse import sse_client

            logger.info(f"Connecting to SSE MCP server at: {params['url']}")

            client_kwargs = {"url": params["url"]}
            for key in ["headers", "timeout", "sse_read_timeout"]:
                if params.get(key) is not None:
                    client_kwargs[key] = params[key]
            read, write = await self.exit_stack.enter_async_context(sse_client(**client_kwargs))
        elif type == "http":
            # Handle StreamableHTTP server
            from mcp.client.streamable_http import streamablehttp_client

            logger.info(f"Connecting to StreamableHTTP MCP server at: {params['url']}")

            client_kwargs = {"url": params["url"]}
            for key in ["headers", "timeout", "sse_read_timeout", "terminate_on_close"]:
                if params.get(key) is not None:
                    client_kwargs[key] = params[key]
            read, write, _ = await self.exit_stack.enter_async_context(streamablehttp_client(**client_kwargs))
            # ^ TODO: should be handle `get_session_id_callback`? (function to retrieve the current session ID)
        else:
            raise ValueError(f"Unsupported server type: {type}")

        session = await self.exit_stack.enter_async_context(
            ClientSession(
                read_stream=read,
                write_stream=write,
                client_info=mcp_types.Implementation(
                    name="huggingface_hub.MCPClient",
                    version=get_hf_hub_version(),
                ),
            )
        )

        logger.debug("Initializing session...")
        await session.initialize()

        # List available tools
        response = await session.list_tools()
        logger.debug("Connected to server with tools:", [tool.name for tool in response.tools])

        for tool in response.tools:
            if tool.name in self.sessions:
                logger.warning(f"Tool '{tool.name}' already defined by another server. Skipping.")
                continue

            # Map tool names to their server for later lookup
            self.sessions[tool.name] = session

            # Add tool to the list of available tools (for use in chat completions)
            self.available_tools.append(
                ChatCompletionInputTool.parse_obj_as_instance(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                        },
                    }
                )
            )

    async def process_single_turn_with_tools(
        self,
        messages: List[Union[Dict, ChatCompletionInputMessage]],
        exit_loop_tools: Optional[List[ChatCompletionInputTool]] = None,
        exit_if_first_chunk_no_tool: bool = False,
    ) -> AsyncIterable[Union[ChatCompletionStreamOutput, ChatCompletionInputMessage]]:
        """Process a query using `self.model` and available tools, yielding chunks and tool outputs.

        Args:
            messages (`List[Dict]`):
                List of message objects representing the conversation history
            exit_loop_tools (`List[ChatCompletionInputTool]`, *optional*):
                List of tools that should exit the generator when called
            exit_if_first_chunk_no_tool (`bool`, *optional*):
                Exit if no tool is present in the first chunks. Default to False.

        Yields:
            [`ChatCompletionStreamOutput`] chunks or [`ChatCompletionInputMessage`] objects
        """
        # Prepare tools list based on options
        tools = self.available_tools
        if exit_loop_tools is not None:
            tools = [*exit_loop_tools, *self.available_tools]

        # Create the streaming request
        response = await self.client.chat.completions.create(
            model=self.payload_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=True,
        )

        message = {"role": "unknown", "content": ""}
        final_tool_calls: Dict[int, ChatCompletionStreamOutputDeltaToolCall] = {}
        num_of_chunks = 0

        # Read from stream
        async for chunk in response:
            num_of_chunks += 1
            delta = chunk.choices[0].delta if chunk.choices and len(chunk.choices) > 0 else None
            if not delta:
                continue

            # Process message
            if delta.role:
                message["role"] = delta.role
            if delta.content:
                message["content"] += delta.content

            # Process tool calls
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    # Aggregate chunks into tool calls
                    if tool_call.index not in final_tool_calls:
                        if (
                            tool_call.function.arguments is None or tool_call.function.arguments == "{}"
                        ):  # Corner case (depends on provider)
                            tool_call.function.arguments = ""
                        final_tool_calls[tool_call.index] = tool_call

                    elif tool_call.function.arguments:
                        final_tool_calls[tool_call.index].function.arguments += tool_call.function.arguments

            # Optionally exit early if no tools in first chunks
            if exit_if_first_chunk_no_tool and num_of_chunks <= 2 and len(final_tool_calls) == 0:
                return

            # Yield each chunk to caller
            yield chunk

        if message["content"]:
            messages.append(message)

        # Process tool calls one by one
        for tool_call in final_tool_calls.values():
            function_name = tool_call.function.name
            try:
                function_args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError as err:
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": f"Invalid JSON generated by the model: {err}",
                }
                tool_message_as_obj = ChatCompletionInputMessage.parse_obj_as_instance(tool_message)
                messages.append(tool_message_as_obj)
                yield tool_message_as_obj
                continue  # move to next tool call

            tool_message = {"role": "tool", "tool_call_id": tool_call.id, "content": "", "name": function_name}

            # Check if this is an exit loop tool
            if exit_loop_tools and function_name in [t.function.name for t in exit_loop_tools]:
                tool_message_as_obj = ChatCompletionInputMessage.parse_obj_as_instance(tool_message)
                messages.append(tool_message_as_obj)
                yield tool_message_as_obj
                return

            # Execute tool call with the appropriate session
            session = self.sessions.get(function_name)
            if session is not None:
                try:
                    result = await session.call_tool(function_name, function_args)
                    tool_message["content"] = format_result(result)
                except Exception as err:
                    tool_message["content"] = f"Error: MCP tool call failed with error message: {err}"
            else:
                tool_message["content"] = f"Error: No session found for tool: {function_name}"

            # Yield tool message
            tool_message_as_obj = ChatCompletionInputMessage.parse_obj_as_instance(tool_message)
            messages.append(tool_message_as_obj)
            yield tool_message_as_obj

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\env_settings.py ===
import os
import warnings
from pathlib import Path
from typing import AbstractSet, Any, Callable, ClassVar, Dict, List, Mapping, Optional, Tuple, Type, Union

from pydantic.v1.config import BaseConfig, Extra
from pydantic.v1.fields import ModelField
from pydantic.v1.main import BaseModel
from pydantic.v1.types import JsonWrapper
from pydantic.v1.typing import StrPath, display_as_type, get_origin, is_union
from pydantic.v1.utils import deep_update, lenient_issubclass, path_type, sequence_like

env_file_sentinel = str(object())

SettingsSourceCallable = Callable[['BaseSettings'], Dict[str, Any]]
DotenvType = Union[StrPath, List[StrPath], Tuple[StrPath, ...]]


class SettingsError(ValueError):
    pass


class BaseSettings(BaseModel):
    """
    Base class for settings, allowing values to be overridden by environment variables.

    This is useful in production for secrets you do not wish to save in code, it plays nicely with docker(-compose),
    Heroku and any 12 factor app design.
    """

    def __init__(
        __pydantic_self__,
        _env_file: Optional[DotenvType] = env_file_sentinel,
        _env_file_encoding: Optional[str] = None,
        _env_nested_delimiter: Optional[str] = None,
        _secrets_dir: Optional[StrPath] = None,
        **values: Any,
    ) -> None:
        # Uses something other than `self` the first arg to allow "self" as a settable attribute
        super().__init__(
            **__pydantic_self__._build_values(
                values,
                _env_file=_env_file,
                _env_file_encoding=_env_file_encoding,
                _env_nested_delimiter=_env_nested_delimiter,
                _secrets_dir=_secrets_dir,
            )
        )

    def _build_values(
        self,
        init_kwargs: Dict[str, Any],
        _env_file: Optional[DotenvType] = None,
        _env_file_encoding: Optional[str] = None,
        _env_nested_delimiter: Optional[str] = None,
        _secrets_dir: Optional[StrPath] = None,
    ) -> Dict[str, Any]:
        # Configure built-in sources
        init_settings = InitSettingsSource(init_kwargs=init_kwargs)
        env_settings = EnvSettingsSource(
            env_file=(_env_file if _env_file != env_file_sentinel else self.__config__.env_file),
            env_file_encoding=(
                _env_file_encoding if _env_file_encoding is not None else self.__config__.env_file_encoding
            ),
            env_nested_delimiter=(
                _env_nested_delimiter if _env_nested_delimiter is not None else self.__config__.env_nested_delimiter
            ),
            env_prefix_len=len(self.__config__.env_prefix),
        )
        file_secret_settings = SecretsSettingsSource(secrets_dir=_secrets_dir or self.__config__.secrets_dir)
        # Provide a hook to set built-in sources priority and add / remove sources
        sources = self.__config__.customise_sources(
            init_settings=init_settings, env_settings=env_settings, file_secret_settings=file_secret_settings
        )
        if sources:
            return deep_update(*reversed([source(self) for source in sources]))
        else:
            # no one should mean to do this, but I think returning an empty dict is marginally preferable
            # to an informative error and much better than a confusing error
            return {}

    class Config(BaseConfig):
        env_prefix: str = ''
        env_file: Optional[DotenvType] = None
        env_file_encoding: Optional[str] = None
        env_nested_delimiter: Optional[str] = None
        secrets_dir: Optional[StrPath] = None
        validate_all: bool = True
        extra: Extra = Extra.forbid
        arbitrary_types_allowed: bool = True
        case_sensitive: bool = False

        @classmethod
        def prepare_field(cls, field: ModelField) -> None:
            env_names: Union[List[str], AbstractSet[str]]
            field_info_from_config = cls.get_field_info(field.name)

            env = field_info_from_config.get('env') or field.field_info.extra.get('env')
            if env is None:
                if field.has_alias:
                    warnings.warn(
                        'aliases are no longer used by BaseSettings to define which environment variables to read. '
                        'Instead use the "env" field setting. '
                        'See https://pydantic-docs.helpmanual.io/usage/settings/#environment-variable-names',
                        FutureWarning,
                    )
                env_names = {cls.env_prefix + field.name}
            elif isinstance(env, str):
                env_names = {env}
            elif isinstance(env, (set, frozenset)):
                env_names = env
            elif sequence_like(env):
                env_names = list(env)
            else:
                raise TypeError(f'invalid field env: {env!r} ({display_as_type(env)}); should be string, list or set')

            if not cls.case_sensitive:
                env_names = env_names.__class__(n.lower() for n in env_names)
            field.field_info.extra['env_names'] = env_names

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> Tuple[SettingsSourceCallable, ...]:
            return init_settings, env_settings, file_secret_settings

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            return cls.json_loads(raw_val)

    # populated by the metaclass using the Config class defined above, annotated here to help IDEs only
    __config__: ClassVar[Type[Config]]


class InitSettingsSource:
    __slots__ = ('init_kwargs',)

    def __init__(self, init_kwargs: Dict[str, Any]):
        self.init_kwargs = init_kwargs

    def __call__(self, settings: BaseSettings) -> Dict[str, Any]:
        return self.init_kwargs

    def __repr__(self) -> str:
        return f'InitSettingsSource(init_kwargs={self.init_kwargs!r})'


class EnvSettingsSource:
    __slots__ = ('env_file', 'env_file_encoding', 'env_nested_delimiter', 'env_prefix_len')

    def __init__(
        self,
        env_file: Optional[DotenvType],
        env_file_encoding: Optional[str],
        env_nested_delimiter: Optional[str] = None,
        env_prefix_len: int = 0,
    ):
        self.env_file: Optional[DotenvType] = env_file
        self.env_file_encoding: Optional[str] = env_file_encoding
        self.env_nested_delimiter: Optional[str] = env_nested_delimiter
        self.env_prefix_len: int = env_prefix_len

    def __call__(self, settings: BaseSettings) -> Dict[str, Any]:  # noqa C901
        """
        Build environment variables suitable for passing to the Model.
        """
        d: Dict[str, Any] = {}

        if settings.__config__.case_sensitive:
            env_vars: Mapping[str, Optional[str]] = os.environ
        else:
            env_vars = {k.lower(): v for k, v in os.environ.items()}

        dotenv_vars = self._read_env_files(settings.__config__.case_sensitive)
        if dotenv_vars:
            env_vars = {**dotenv_vars, **env_vars}

        for field in settings.__fields__.values():
            env_val: Optional[str] = None
            for env_name in field.field_info.extra['env_names']:
                env_val = env_vars.get(env_name)
                if env_val is not None:
                    break

            is_complex, allow_parse_failure = self.field_is_complex(field)
            if is_complex:
                if env_val is None:
                    # field is complex but no value found so far, try explode_env_vars
                    env_val_built = self.explode_env_vars(field, env_vars)
                    if env_val_built:
                        d[field.alias] = env_val_built
                else:
                    # field is complex and there's a value, decode that as JSON, then add explode_env_vars
                    try:
                        env_val = settings.__config__.parse_env_var(field.name, env_val)
                    except ValueError as e:
                        if not allow_parse_failure:
                            raise SettingsError(f'error parsing env var "{env_name}"') from e

                    if isinstance(env_val, dict):
                        d[field.alias] = deep_update(env_val, self.explode_env_vars(field, env_vars))
                    else:
                        d[field.alias] = env_val
            elif env_val is not None:
                # simplest case, field is not complex, we only need to add the value if it was found
                d[field.alias] = env_val

        return d

    def _read_env_files(self, case_sensitive: bool) -> Dict[str, Optional[str]]:
        env_files = self.env_file
        if env_files is None:
            return {}

        if isinstance(env_files, (str, os.PathLike)):
            env_files = [env_files]

        dotenv_vars = {}
        for env_file in env_files:
            env_path = Path(env_file).expanduser()
            if env_path.is_file():
                dotenv_vars.update(
                    read_env_file(env_path, encoding=self.env_file_encoding, case_sensitive=case_sensitive)
                )

        return dotenv_vars

    def field_is_complex(self, field: ModelField) -> Tuple[bool, bool]:
        """
        Find out if a field is complex, and if so whether JSON errors should be ignored
        """
        if lenient_issubclass(field.annotation, JsonWrapper):
            return False, False

        if field.is_complex():
            allow_parse_failure = False
        elif is_union(get_origin(field.type_)) and field.sub_fields and any(f.is_complex() for f in field.sub_fields):
            allow_parse_failure = True
        else:
            return False, False

        return True, allow_parse_failure

    def explode_env_vars(self, field: ModelField, env_vars: Mapping[str, Optional[str]]) -> Dict[str, Any]:
        """
        Process env_vars and extract the values of keys containing env_nested_delimiter into nested dictionaries.

        This is applied to a single field, hence filtering by env_var prefix.
        """
        prefixes = [f'{env_name}{self.env_nested_delimiter}' for env_name in field.field_info.extra['env_names']]
        result: Dict[str, Any] = {}
        for env_name, env_val in env_vars.items():
            if not any(env_name.startswith(prefix) for prefix in prefixes):
                continue
            # we remove the prefix before splitting in case the prefix has characters in common with the delimiter
            env_name_without_prefix = env_name[self.env_prefix_len :]
            _, *keys, last_key = env_name_without_prefix.split(self.env_nested_delimiter)
            env_var = result
            for key in keys:
                env_var = env_var.setdefault(key, {})
            env_var[last_key] = env_val

        return result

    def __repr__(self) -> str:
        return (
            f'EnvSettingsSource(env_file={self.env_file!r}, env_file_encoding={self.env_file_encoding!r}, '
            f'env_nested_delimiter={self.env_nested_delimiter!r})'
        )


class SecretsSettingsSource:
    __slots__ = ('secrets_dir',)

    def __init__(self, secrets_dir: Optional[StrPath]):
        self.secrets_dir: Optional[StrPath] = secrets_dir

    def __call__(self, settings: BaseSettings) -> Dict[str, Any]:
        """
        Build fields from "secrets" files.
        """
        secrets: Dict[str, Optional[str]] = {}

        if self.secrets_dir is None:
            return secrets

        secrets_path = Path(self.secrets_dir).expanduser()

        if not secrets_path.exists():
            warnings.warn(f'directory "{secrets_path}" does not exist')
            return secrets

        if not secrets_path.is_dir():
            raise SettingsError(f'secrets_dir must reference a directory, not a {path_type(secrets_path)}')

        for field in settings.__fields__.values():
            for env_name in field.field_info.extra['env_names']:
                path = find_case_path(secrets_path, env_name, settings.__config__.case_sensitive)
                if not path:
                    # path does not exist, we currently don't return a warning for this
                    continue

                if path.is_file():
                    secret_value = path.read_text().strip()
                    if field.is_complex():
                        try:
                            secret_value = settings.__config__.parse_env_var(field.name, secret_value)
                        except ValueError as e:
                            raise SettingsError(f'error parsing env var "{env_name}"') from e

                    secrets[field.alias] = secret_value
                else:
                    warnings.warn(
                        f'attempted to load secret file "{path}" but found a {path_type(path)} instead.',
                        stacklevel=4,
                    )
        return secrets

    def __repr__(self) -> str:
        return f'SecretsSettingsSource(secrets_dir={self.secrets_dir!r})'


def read_env_file(
    file_path: StrPath, *, encoding: str = None, case_sensitive: bool = False
) -> Dict[str, Optional[str]]:
    try:
        from dotenv import dotenv_values
    except ImportError as e:
        raise ImportError('python-dotenv is not installed, run `pip install pydantic[dotenv]`') from e

    file_vars: Dict[str, Optional[str]] = dotenv_values(file_path, encoding=encoding or 'utf8')
    if not case_sensitive:
        return {k.lower(): v for k, v in file_vars.items()}
    else:
        return file_vars


def find_case_path(dir_path: Path, file_name: str, case_sensitive: bool) -> Optional[Path]:
    """
    Find a file within path's directory matching filename, optionally ignoring case.
    """
    for f in dir_path.iterdir():
        if f.name == file_name:
            return f
        elif not case_sensitive and f.name.lower() == file_name.lower():
            return f
    return None

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\formatters\rtf.py ===
"""
    pygments.formatters.rtf
    ~~~~~~~~~~~~~~~~~~~~~~~

    A formatter that generates RTF files.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from collections import OrderedDict
from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.style import _ansimap
from pip._vendor.pygments.util import get_bool_opt, get_int_opt, get_list_opt, surrogatepair


__all__ = ['RtfFormatter']


class RtfFormatter(Formatter):
    """
    Format tokens as RTF markup. This formatter automatically outputs full RTF
    documents with color information and other useful stuff. Perfect for Copy and
    Paste into Microsoft(R) Word(R) documents.

    Please note that ``encoding`` and ``outencoding`` options are ignored.
    The RTF format is ASCII natively, but handles unicode characters correctly
    thanks to escape sequences.

    .. versionadded:: 0.6

    Additional options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).

    `fontface`
        The used font family, for example ``Bitstream Vera Sans``. Defaults to
        some generic font which is supposed to have fixed width.

    `fontsize`
        Size of the font used. Size is specified in half points. The
        default is 24 half-points, giving a size 12 font.

        .. versionadded:: 2.0

    `linenos`
        Turn on line numbering (default: ``False``).

        .. versionadded:: 2.18

    `lineno_fontsize`
        Font size for line numbers. Size is specified in half points
        (default: `fontsize`). 

        .. versionadded:: 2.18

    `lineno_padding`
        Number of spaces between the (inline) line numbers and the
        source code (default: ``2``).

        .. versionadded:: 2.18

    `linenostart`
        The line number for the first line (default: ``1``).

        .. versionadded:: 2.18

    `linenostep`
        If set to a number n > 1, only every nth line number is printed.

        .. versionadded:: 2.18

    `lineno_color`
        Color for line numbers specified as a hex triplet, e.g. ``'5e5e5e'``. 
        Defaults to the style's line number color if it is a hex triplet, 
        otherwise ansi bright black.

        .. versionadded:: 2.18

    `hl_lines`
        Specify a list of lines to be highlighted, as line numbers separated by
        spaces, e.g. ``'3 7 8'``. The line numbers are relative to the input 
        (i.e. the first line is line 1) unless `hl_linenostart` is set.

        .. versionadded:: 2.18

    `hl_color`
        Color for highlighting the lines specified in `hl_lines`, specified as 
        a hex triplet (default: style's `highlight_color`).

        .. versionadded:: 2.18

    `hl_linenostart`
        If set to ``True`` line numbers in `hl_lines` are specified
        relative to `linenostart` (default ``False``).

        .. versionadded:: 2.18
    """
    name = 'RTF'
    aliases = ['rtf']
    filenames = ['*.rtf']

    def __init__(self, **options):
        r"""
        Additional options accepted:

        ``fontface``
            Name of the font used. Could for example be ``'Courier New'``
            to further specify the default which is ``'\fmodern'``. The RTF
            specification claims that ``\fmodern`` are "Fixed-pitch serif
            and sans serif fonts". Hope every RTF implementation thinks
            the same about modern...

        """
        Formatter.__init__(self, **options)
        self.fontface = options.get('fontface') or ''
        self.fontsize = get_int_opt(options, 'fontsize', 0)
        self.linenos = get_bool_opt(options, 'linenos', False)
        self.lineno_fontsize = get_int_opt(options, 'lineno_fontsize',
                                           self.fontsize)
        self.lineno_padding = get_int_opt(options, 'lineno_padding', 2)
        self.linenostart = abs(get_int_opt(options, 'linenostart', 1))
        self.linenostep = abs(get_int_opt(options, 'linenostep', 1))
        self.hl_linenostart = get_bool_opt(options, 'hl_linenostart', False)

        self.hl_color = options.get('hl_color', '')
        if not self.hl_color:
            self.hl_color = self.style.highlight_color

        self.hl_lines = []
        for lineno in get_list_opt(options, 'hl_lines', []):
            try:
                lineno = int(lineno)
                if self.hl_linenostart:
                    lineno = lineno - self.linenostart + 1
                self.hl_lines.append(lineno)
            except ValueError:
                pass

        self.lineno_color = options.get('lineno_color', '')
        if not self.lineno_color:
            if  self.style.line_number_color == 'inherit':
                # style color is the css value 'inherit'
                # default to ansi bright-black
                self.lineno_color = _ansimap['ansibrightblack']
            else:
                # style color is assumed to be a hex triplet as other
                # colors in pygments/style.py
                self.lineno_color = self.style.line_number_color

        self.color_mapping = self._create_color_mapping()

    def _escape(self, text):
        return text.replace('\\', '\\\\') \
                   .replace('{', '\\{') \
                   .replace('}', '\\}')

    def _escape_text(self, text):
        # empty strings, should give a small performance improvement
        if not text:
            return ''

        # escape text
        text = self._escape(text)

        buf = []
        for c in text:
            cn = ord(c)
            if cn < (2**7):
                # ASCII character
                buf.append(str(c))
            elif (2**7) <= cn < (2**16):
                # single unicode escape sequence
                buf.append('{\\u%d}' % cn)
            elif (2**16) <= cn:
                # RTF limits unicode to 16 bits.
                # Force surrogate pairs
                buf.append('{\\u%d}{\\u%d}' % surrogatepair(cn))

        return ''.join(buf).replace('\n', '\\par')

    @staticmethod
    def hex_to_rtf_color(hex_color):
        if hex_color[0] == "#":
            hex_color = hex_color[1:]

        return '\\red%d\\green%d\\blue%d;' % (
                        int(hex_color[0:2], 16),
                        int(hex_color[2:4], 16),
                        int(hex_color[4:6], 16)
                    )

    def _split_tokens_on_newlines(self, tokensource):
        """
        Split tokens containing newline characters into multiple token
        each representing a line of the input file. Needed for numbering
        lines of e.g. multiline comments.
        """
        for ttype, value in tokensource:
            if value == '\n':
                yield (ttype, value)
            elif "\n" in value:
                lines = value.split("\n")
                for line in lines[:-1]:
                    yield (ttype, line+"\n")
                if lines[-1]:
                    yield (ttype, lines[-1])
            else:
                yield (ttype, value)

    def _create_color_mapping(self):
        """
        Create a mapping of style hex colors to index/offset in
        the RTF color table.
        """
        color_mapping = OrderedDict()
        offset = 1

        if self.linenos:
            color_mapping[self.lineno_color] = offset
            offset += 1

        if self.hl_lines:
            color_mapping[self.hl_color] = offset
            offset += 1

        for _, style in self.style:
            for color in style['color'], style['bgcolor'], style['border']:
                if color and color not in color_mapping:
                    color_mapping[color] = offset
                    offset += 1

        return color_mapping

    @property
    def _lineno_template(self):
        if self.lineno_fontsize != self.fontsize:
            return '{{\\fs{} \\cf{} %s{}}}'.format(self.lineno_fontsize,
                          self.color_mapping[self.lineno_color],
                          " " * self.lineno_padding)

        return '{{\\cf{} %s{}}}'.format(self.color_mapping[self.lineno_color],
                      " " * self.lineno_padding)

    @property
    def _hl_open_str(self):
        return rf'{{\highlight{self.color_mapping[self.hl_color]} '

    @property
    def _rtf_header(self):
        lines = []
        # rtf 1.8 header
        lines.append('{\\rtf1\\ansi\\uc0\\deff0'
                     '{\\fonttbl{\\f0\\fmodern\\fprq1\\fcharset0%s;}}'
                     % (self.fontface and ' '
                        + self._escape(self.fontface) or ''))

        # color table
        lines.append('{\\colortbl;')
        for color, _ in self.color_mapping.items():
            lines.append(self.hex_to_rtf_color(color))
        lines.append('}')

        # font and fontsize
        lines.append('\\f0\\sa0')
        if self.fontsize:
            lines.append('\\fs%d' % self.fontsize)

        # ensure Libre Office Writer imports and renders consecutive
        # space characters the same width, needed for line numbering.
        # https://bugs.documentfoundation.org/show_bug.cgi?id=144050
        lines.append('\\dntblnsbdb')

        return lines

    def format_unencoded(self, tokensource, outfile):
        for line in self._rtf_header:
            outfile.write(line + "\n")

        tokensource = self._split_tokens_on_newlines(tokensource)

        # first pass of tokens to count lines, needed for line numbering
        if self.linenos:
            line_count = 0
            tokens = [] # for copying the token source generator
            for ttype, value in tokensource:
                tokens.append((ttype, value))
                if value.endswith("\n"):
                    line_count += 1

            # width of line number strings (for padding with spaces)
            linenos_width = len(str(line_count+self.linenostart-1))

            tokensource = tokens

        # highlight stream
        lineno = 1
        start_new_line = True
        for ttype, value in tokensource:
            if start_new_line and lineno in self.hl_lines:
                outfile.write(self._hl_open_str)

            if start_new_line and self.linenos:
                if (lineno-self.linenostart+1)%self.linenostep == 0:
                    current_lineno = lineno + self.linenostart - 1
                    lineno_str = str(current_lineno).rjust(linenos_width)
                else:
                    lineno_str = "".rjust(linenos_width)
                outfile.write(self._lineno_template % lineno_str)

            while not self.style.styles_token(ttype) and ttype.parent:
                ttype = ttype.parent
            style = self.style.style_for_token(ttype)
            buf = []
            if style['bgcolor']:
                buf.append('\\cb%d' % self.color_mapping[style['bgcolor']])
            if style['color']:
                buf.append('\\cf%d' % self.color_mapping[style['color']])
            if style['bold']:
                buf.append('\\b')
            if style['italic']:
                buf.append('\\i')
            if style['underline']:
                buf.append('\\ul')
            if style['border']:
                buf.append('\\chbrdr\\chcfpat%d' %
                           self.color_mapping[style['border']])
            start = ''.join(buf)
            if start:
                outfile.write(f'{{{start} ')
            outfile.write(self._escape_text(value))
            if start:
                outfile.write('}')
            start_new_line = False

            # complete line of input
            if value.endswith("\n"):
                # close line highlighting
                if lineno in self.hl_lines:
                    outfile.write('}')
                # newline in RTF file after closing }
                outfile.write("\n")

                start_new_line = True
                lineno += 1

        outfile.write('}\n')

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\fsnotify\__init__.py ===
"""
Sample usage to track changes in a thread.

    import threading
    import time
    watcher = fsnotify.Watcher()
    watcher.accepted_file_extensions = {'.py', '.pyw'}

    # Configure target values to compute throttling.
    # Note: internal sleep times will be updated based on
    # profiling the actual application runtime to match
    # those values.

    watcher.target_time_for_single_scan = 2.
    watcher.target_time_for_notification = 4.

    watcher.set_tracked_paths([target_dir])

    def start_watching():  # Called from thread
        for change_enum, change_path in watcher.iter_changes():
            if change_enum == fsnotify.Change.added:
                print('Added: ', change_path)
            elif change_enum == fsnotify.Change.modified:
                print('Modified: ', change_path)
            elif change_enum == fsnotify.Change.deleted:
                print('Deleted: ', change_path)

    t = threading.Thread(target=start_watching)
    t.daemon = True
    t.start()

    try:
        ...
    finally:
        watcher.dispose()


Note: changes are only reported for files (added/modified/deleted), not directories.
"""
import sys
from os.path import basename
from _pydev_bundle import pydev_log, _pydev_saved_modules
from os import scandir

try:
    from enum import IntEnum
except:

    class IntEnum(object):
        pass


import time

__author__ = "Fabio Zadrozny"
__email__ = "fabiofz@gmail.com"
__version__ = "0.1.5"  # Version here and in setup.py


class Change(IntEnum):
    added = 1
    modified = 2
    deleted = 3


class _SingleVisitInfo(object):
    def __init__(self):
        self.count = 0
        self.visited_dirs = set()
        self.file_to_mtime = {}
        self.last_sleep_time = time.time()


class _PathWatcher(object):
    """
    Helper to watch a single path.
    """

    def __init__(self, root_path, accept_directory, accept_file, single_visit_info, max_recursion_level, sleep_time=0.0):
        """
        :type root_path: str
        :type accept_directory: Callback[str, bool]
        :type accept_file: Callback[str, bool]
        :type max_recursion_level: int
        :type sleep_time: float
        """
        self.accept_directory = accept_directory
        self.accept_file = accept_file
        self._max_recursion_level = max_recursion_level

        self._root_path = root_path

        # Initial sleep value for throttling, it'll be auto-updated based on the
        # Watcher.target_time_for_single_scan.
        self.sleep_time = sleep_time

        self.sleep_at_elapsed = 1.0 / 30.0

        # When created, do the initial snapshot right away!
        old_file_to_mtime = {}
        self._check(single_visit_info, lambda _change: None, old_file_to_mtime)

    def __eq__(self, o):
        if isinstance(o, _PathWatcher):
            return self._root_path == o._root_path

        return False

    def __ne__(self, o):
        return not self == o

    def __hash__(self):
        return hash(self._root_path)

    def _check_dir(self, dir_path, single_visit_info, append_change, old_file_to_mtime, level):
        # This is the actual poll loop
        if dir_path in single_visit_info.visited_dirs or level > self._max_recursion_level:
            return
        single_visit_info.visited_dirs.add(dir_path)
        try:
            if isinstance(dir_path, bytes):
                try:
                    dir_path = dir_path.decode(sys.getfilesystemencoding())
                except UnicodeDecodeError:
                    try:
                        dir_path = dir_path.decode("utf-8")
                    except UnicodeDecodeError:
                        return  # Ignore if we can't deal with the path.

            new_files = single_visit_info.file_to_mtime

            for entry in scandir(dir_path):
                single_visit_info.count += 1

                # Throttle if needed inside the loop
                # to avoid consuming too much CPU.
                if single_visit_info.count % 300 == 0:
                    if self.sleep_time > 0:
                        t = time.time()
                        diff = t - single_visit_info.last_sleep_time
                        if diff > self.sleep_at_elapsed:
                            time.sleep(self.sleep_time)
                            single_visit_info.last_sleep_time = time.time()

                if entry.is_dir():
                    if self.accept_directory(entry.path):
                        self._check_dir(entry.path, single_visit_info, append_change, old_file_to_mtime, level + 1)

                elif self.accept_file(entry.path):
                    stat = entry.stat()
                    mtime = (stat.st_mtime_ns, stat.st_size)
                    path = entry.path
                    new_files[path] = mtime

                    old_mtime = old_file_to_mtime.pop(path, None)
                    if not old_mtime:
                        append_change((Change.added, path))
                    elif old_mtime != mtime:
                        append_change((Change.modified, path))

        except OSError:
            pass  # Directory was removed in the meanwhile.

    def _check(self, single_visit_info, append_change, old_file_to_mtime):
        self._check_dir(self._root_path, single_visit_info, append_change, old_file_to_mtime, 0)


class Watcher(object):
    # By default (if accept_directory is not specified), these will be the
    # ignored directories.
    ignored_dirs = {".git", "__pycache__", ".idea", "node_modules", ".metadata"}

    # By default (if accept_file is not specified), these will be the
    # accepted files.
    accepted_file_extensions = ()

    # Set to the target value for doing full scan of all files (adds a sleep inside the poll loop
    # which processes files to reach the target time).
    # Lower values will consume more CPU
    # Set to 0.0 to have no sleeps (which will result in a higher cpu load).
    target_time_for_single_scan = 2.0

    # Set the target value from the start of one scan to the start of another scan (adds a
    # sleep after a full poll is done to reach the target time).
    # Lower values will consume more CPU.
    # Set to 0.0 to have a new scan start right away without any sleeps.
    target_time_for_notification = 4.0

    # Set to True to print the time for a single poll through all the paths.
    print_poll_time = False

    # This is the maximum recursion level.
    max_recursion_level = 10

    def __init__(self, accept_directory=None, accept_file=None):
        """
        :param Callable[str, bool] accept_directory:
            Callable that returns whether a directory should be watched.
            Note: if passed it'll override the `ignored_dirs`

        :param Callable[str, bool] accept_file:
            Callable that returns whether a file should be watched.
            Note: if passed it'll override the `accepted_file_extensions`.
        """
        self._path_watchers = set()
        self._disposed = _pydev_saved_modules.ThreadingEvent()

        if accept_directory is None:
            accept_directory = lambda dir_path: basename(dir_path) not in self.ignored_dirs
        if accept_file is None:
            accept_file = lambda path_name: not self.accepted_file_extensions or path_name.endswith(self.accepted_file_extensions)
        self.accept_file = accept_file
        self.accept_directory = accept_directory
        self._single_visit_info = _SingleVisitInfo()

    @property
    def accept_directory(self):
        return self._accept_directory

    @accept_directory.setter
    def accept_directory(self, accept_directory):
        self._accept_directory = accept_directory
        for path_watcher in self._path_watchers:
            path_watcher.accept_directory = accept_directory

    @property
    def accept_file(self):
        return self._accept_file

    @accept_file.setter
    def accept_file(self, accept_file):
        self._accept_file = accept_file
        for path_watcher in self._path_watchers:
            path_watcher.accept_file = accept_file

    def dispose(self):
        self._disposed.set()

    @property
    def path_watchers(self):
        return tuple(self._path_watchers)

    def set_tracked_paths(self, paths):
        """
        Note: always resets all path trackers to track the passed paths.
        """
        if not isinstance(paths, (list, tuple, set)):
            paths = (paths,)

        # Sort by the path len so that the bigger paths come first (so,
        # if there's any nesting we want the nested paths to be visited
        # before the parent paths so that the max_recursion_level is correct).
        paths = sorted(set(paths), key=lambda path: -len(path))
        path_watchers = set()

        self._single_visit_info = _SingleVisitInfo()

        initial_time = time.time()
        for path in paths:
            sleep_time = 0.0  # When collecting the first time, sleep_time should be 0!
            path_watcher = _PathWatcher(
                path,
                self.accept_directory,
                self.accept_file,
                self._single_visit_info,
                max_recursion_level=self.max_recursion_level,
                sleep_time=sleep_time,
            )

            path_watchers.add(path_watcher)

        actual_time = time.time() - initial_time

        pydev_log.debug("Tracking the following paths for changes: %s", paths)
        pydev_log.debug("Time to track: %.2fs", actual_time)
        pydev_log.debug("Folders found: %s", len(self._single_visit_info.visited_dirs))
        pydev_log.debug("Files found: %s", len(self._single_visit_info.file_to_mtime))
        self._path_watchers = path_watchers

    def iter_changes(self):
        """
        Continuously provides changes (until dispose() is called).

        Changes provided are tuples with the Change enum and filesystem path.

        :rtype: Iterable[Tuple[Change, str]]
        """
        while not self._disposed.is_set():
            initial_time = time.time()

            old_visit_info = self._single_visit_info
            old_file_to_mtime = old_visit_info.file_to_mtime
            changes = []
            append_change = changes.append

            self._single_visit_info = single_visit_info = _SingleVisitInfo()
            for path_watcher in self._path_watchers:
                path_watcher._check(single_visit_info, append_change, old_file_to_mtime)

            # Note that we pop entries while visiting, so, what remained is what's deleted.
            for entry in old_file_to_mtime:
                append_change((Change.deleted, entry))

            for change in changes:
                yield change

            actual_time = time.time() - initial_time
            if self.print_poll_time:
                print("--- Total poll time: %.3fs" % actual_time)

            if actual_time > 0:
                if self.target_time_for_single_scan <= 0.0:
                    for path_watcher in self._path_watchers:
                        path_watcher.sleep_time = 0.0
                else:
                    perc = self.target_time_for_single_scan / actual_time

                    # Prevent from changing the values too much (go slowly into the right
                    # direction).
                    # (to prevent from cases where the user puts the machine on sleep and
                    # values become too skewed).
                    if perc > 2.0:
                        perc = 2.0
                    elif perc < 0.5:
                        perc = 0.5

                    for path_watcher in self._path_watchers:
                        if path_watcher.sleep_time <= 0.0:
                            path_watcher.sleep_time = 0.001
                        new_sleep_time = path_watcher.sleep_time * perc

                        # Prevent from changing the values too much (go slowly into the right
                        # direction).
                        # (to prevent from cases where the user puts the machine on sleep and
                        # values become too skewed).
                        diff_sleep_time = new_sleep_time - path_watcher.sleep_time
                        path_watcher.sleep_time += diff_sleep_time / (3.0 * len(self._path_watchers))

                        if actual_time > 0:
                            self._disposed.wait(actual_time)

                        if path_watcher.sleep_time < 0.001:
                            path_watcher.sleep_time = 0.001

            # print('new sleep time: %s' % path_watcher.sleep_time)

            diff = self.target_time_for_notification - actual_time
            if diff > 0.0:
                self._disposed.wait(diff)