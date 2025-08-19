
# === NexusCore/openenv\Lib\site-packages\fontTools\misc\xmlReader.py ===
from fontTools import ttLib
from fontTools.misc.textTools import safeEval
from fontTools.ttLib.tables.DefaultTable import DefaultTable
import sys
import os
import logging


log = logging.getLogger(__name__)


class TTXParseError(Exception):
    pass


BUFSIZE = 0x4000


class XMLReader(object):
    def __init__(
        self, fileOrPath, ttFont, progress=None, quiet=None, contentOnly=False
    ):
        if fileOrPath == "-":
            fileOrPath = sys.stdin
        if not hasattr(fileOrPath, "read"):
            self.file = open(fileOrPath, "rb")
            self._closeStream = True
        else:
            # assume readable file object
            self.file = fileOrPath
            self._closeStream = False
        self.ttFont = ttFont
        self.progress = progress
        if quiet is not None:
            from fontTools.misc.loggingTools import deprecateArgument

            deprecateArgument("quiet", "configure logging instead")
            self.quiet = quiet
        self.root = None
        self.contentStack = []
        self.contentOnly = contentOnly
        self.stackSize = 0

    def read(self, rootless=False):
        if rootless:
            self.stackSize += 1
        if self.progress:
            self.file.seek(0, 2)
            fileSize = self.file.tell()
            self.progress.set(0, fileSize // 100 or 1)
            self.file.seek(0)
        self._parseFile(self.file)
        if self._closeStream:
            self.close()
        if rootless:
            self.stackSize -= 1

    def close(self):
        self.file.close()

    def _parseFile(self, file):
        from xml.parsers.expat import ParserCreate

        parser = ParserCreate()
        parser.StartElementHandler = self._startElementHandler
        parser.EndElementHandler = self._endElementHandler
        parser.CharacterDataHandler = self._characterDataHandler

        pos = 0
        while True:
            chunk = file.read(BUFSIZE)
            if not chunk:
                parser.Parse(chunk, 1)
                break
            pos = pos + len(chunk)
            if self.progress:
                self.progress.set(pos // 100)
            parser.Parse(chunk, 0)

    def _startElementHandler(self, name, attrs):
        if self.stackSize == 1 and self.contentOnly:
            # We already know the table we're parsing, skip
            # parsing the table tag and continue to
            # stack '2' which begins parsing content
            self.contentStack.append([])
            self.stackSize = 2
            return
        stackSize = self.stackSize
        self.stackSize = stackSize + 1
        subFile = attrs.get("src")
        if subFile is not None:
            if hasattr(self.file, "name"):
                # if file has a name, get its parent directory
                dirname = os.path.dirname(self.file.name)
            else:
                # else fall back to using the current working directory
                dirname = os.getcwd()
            subFile = os.path.join(dirname, subFile)
        if not stackSize:
            if name != "ttFont":
                raise TTXParseError("illegal root tag: %s" % name)
            if self.ttFont.reader is None and not self.ttFont.tables:
                sfntVersion = attrs.get("sfntVersion")
                if sfntVersion is not None:
                    if len(sfntVersion) != 4:
                        sfntVersion = safeEval('"' + sfntVersion + '"')
                    self.ttFont.sfntVersion = sfntVersion
            self.contentStack.append([])
        elif stackSize == 1:
            if subFile is not None:
                subReader = XMLReader(subFile, self.ttFont, self.progress)
                subReader.read()
                self.contentStack.append([])
                return
            tag = ttLib.xmlToTag(name)
            msg = "Parsing '%s' table..." % tag
            if self.progress:
                self.progress.setLabel(msg)
            log.info(msg)
            if tag == "GlyphOrder":
                tableClass = ttLib.GlyphOrder
            elif "ERROR" in attrs or ("raw" in attrs and safeEval(attrs["raw"])):
                tableClass = DefaultTable
            else:
                tableClass = ttLib.getTableClass(tag)
                if tableClass is None:
                    tableClass = DefaultTable
            if tag == "loca" and tag in self.ttFont:
                # Special-case the 'loca' table as we need the
                #    original if the 'glyf' table isn't recompiled.
                self.currentTable = self.ttFont[tag]
            else:
                self.currentTable = tableClass(tag)
                self.ttFont[tag] = self.currentTable
            self.contentStack.append([])
        elif stackSize == 2 and subFile is not None:
            subReader = XMLReader(subFile, self.ttFont, self.progress, contentOnly=True)
            subReader.read()
            self.contentStack.append([])
            self.root = subReader.root
        elif stackSize == 2:
            self.contentStack.append([])
            self.root = (name, attrs, self.contentStack[-1])
        else:
            l = []
            self.contentStack[-1].append((name, attrs, l))
            self.contentStack.append(l)

    def _characterDataHandler(self, data):
        if self.stackSize > 1:
            # parser parses in chunks, so we may get multiple calls
            # for the same text node; thus we need to append the data
            # to the last item in the content stack:
            # https://github.com/fonttools/fonttools/issues/2614
            if (
                data != "\n"
                and self.contentStack[-1]
                and isinstance(self.contentStack[-1][-1], str)
                and self.contentStack[-1][-1] != "\n"
            ):
                self.contentStack[-1][-1] += data
            else:
                self.contentStack[-1].append(data)

    def _endElementHandler(self, name):
        self.stackSize = self.stackSize - 1
        del self.contentStack[-1]
        if not self.contentOnly:
            if self.stackSize == 1:
                self.root = None
            elif self.stackSize == 2:
                name, attrs, content = self.root
                self.currentTable.fromXML(name, attrs, content, self.ttFont)
                self.root = None


class ProgressPrinter(object):
    def __init__(self, title, maxval=100):
        print(title)

    def set(self, val, maxval=None):
        pass

    def increment(self, val=1):
        pass

    def setLabel(self, text):
        print(text)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\utils\logging.py ===
# coding=utf-8
# Copyright 2020 Optuna, Hugging Face
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
"""Logging utilities."""

import logging
import os
from logging import (
    CRITICAL,  # NOQA
    DEBUG,  # NOQA
    ERROR,  # NOQA
    FATAL,  # NOQA
    INFO,  # NOQA
    NOTSET,  # NOQA
    WARN,  # NOQA
    WARNING,  # NOQA
)
from typing import Optional

from .. import constants


log_levels = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

_default_log_level = logging.WARNING


def _get_library_name() -> str:
    return __name__.split(".")[0]


def _get_library_root_logger() -> logging.Logger:
    return logging.getLogger(_get_library_name())


def _get_default_logging_level():
    """
    If `HF_HUB_VERBOSITY` env var is set to one of the valid choices return that as the new default level. If it is not
    - fall back to `_default_log_level`
    """
    env_level_str = os.getenv("HF_HUB_VERBOSITY", None)
    if env_level_str:
        if env_level_str in log_levels:
            return log_levels[env_level_str]
        else:
            logging.getLogger().warning(
                f"Unknown option HF_HUB_VERBOSITY={env_level_str}, has to be one of: {', '.join(log_levels.keys())}"
            )
    return _default_log_level


def _configure_library_root_logger() -> None:
    library_root_logger = _get_library_root_logger()
    library_root_logger.addHandler(logging.StreamHandler())
    library_root_logger.setLevel(_get_default_logging_level())


def _reset_library_root_logger() -> None:
    library_root_logger = _get_library_root_logger()
    library_root_logger.setLevel(logging.NOTSET)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
        Returns a logger with the specified name. This function is not supposed
        to be directly accessed by library users.

        Args:
            name (`str`, *optional*):
                The name of the logger to get, usually the filename

        Example:

    ```python
    >>> from huggingface_hub import get_logger

    >>> logger = get_logger(__file__)
    >>> logger.set_verbosity_info()
    ```
    """

    if name is None:
        name = _get_library_name()

    return logging.getLogger(name)


def get_verbosity() -> int:
    """Return the current level for the HuggingFace Hub's root logger.

    Returns:
        Logging level, e.g., `huggingface_hub.logging.DEBUG` and
        `huggingface_hub.logging.INFO`.

    <Tip>

    HuggingFace Hub has following logging levels:

    - `huggingface_hub.logging.CRITICAL`, `huggingface_hub.logging.FATAL`
    - `huggingface_hub.logging.ERROR`
    - `huggingface_hub.logging.WARNING`, `huggingface_hub.logging.WARN`
    - `huggingface_hub.logging.INFO`
    - `huggingface_hub.logging.DEBUG`

    </Tip>
    """
    return _get_library_root_logger().getEffectiveLevel()


def set_verbosity(verbosity: int) -> None:
    """
    Sets the level for the HuggingFace Hub's root logger.

    Args:
        verbosity (`int`):
            Logging level, e.g., `huggingface_hub.logging.DEBUG` and
            `huggingface_hub.logging.INFO`.
    """
    _get_library_root_logger().setLevel(verbosity)


def set_verbosity_info():
    """
    Sets the verbosity to `logging.INFO`.
    """
    return set_verbosity(INFO)


def set_verbosity_warning():
    """
    Sets the verbosity to `logging.WARNING`.
    """
    return set_verbosity(WARNING)


def set_verbosity_debug():
    """
    Sets the verbosity to `logging.DEBUG`.
    """
    return set_verbosity(DEBUG)


def set_verbosity_error():
    """
    Sets the verbosity to `logging.ERROR`.
    """
    return set_verbosity(ERROR)


def disable_propagation() -> None:
    """
    Disable propagation of the library log outputs. Note that log propagation is
    disabled by default.
    """
    _get_library_root_logger().propagate = False


def enable_propagation() -> None:
    """
    Enable propagation of the library log outputs. Please disable the
    HuggingFace Hub's default handler to prevent double logging if the root
    logger has been configured.
    """
    _get_library_root_logger().propagate = True


_configure_library_root_logger()

if constants.HF_DEBUG:
    # If `HF_DEBUG` environment variable is set, set the verbosity of `huggingface_hub` logger to `DEBUG`.
    set_verbosity_debug()

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\utils\_xet.py ===
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

import requests

from .. import constants
from . import get_session, hf_raise_for_status, validate_hf_hub_args


class XetTokenType(str, Enum):
    READ = "read"
    WRITE = "write"


@dataclass(frozen=True)
class XetFileData:
    file_hash: str
    refresh_route: str


@dataclass(frozen=True)
class XetConnectionInfo:
    access_token: str
    expiration_unix_epoch: int
    endpoint: str


def parse_xet_file_data_from_response(response: requests.Response) -> Optional[XetFileData]:
    """
    Parse XET file metadata from an HTTP response.

    This function extracts XET file metadata from the HTTP headers or HTTP links
    of a given response object. If the required metadata is not found, it returns `None`.

    Args:
        response (`requests.Response`):
            The HTTP response object containing headers dict and links dict to extract the XET metadata from.
    Returns:
        `Optional[XetFileData]`:
            An instance of `XetFileData` containing the file hash and refresh route if the metadata
            is found. Returns `None` if the required metadata is missing.
    """
    if response is None:
        return None
    try:
        file_hash = response.headers[constants.HUGGINGFACE_HEADER_X_XET_HASH]

        if constants.HUGGINGFACE_HEADER_LINK_XET_AUTH_KEY in response.links:
            refresh_route = response.links[constants.HUGGINGFACE_HEADER_LINK_XET_AUTH_KEY]["url"]
        else:
            refresh_route = response.headers[constants.HUGGINGFACE_HEADER_X_XET_REFRESH_ROUTE]
    except KeyError:
        return None

    return XetFileData(
        file_hash=file_hash,
        refresh_route=refresh_route,
    )


def parse_xet_connection_info_from_headers(headers: Dict[str, str]) -> Optional[XetConnectionInfo]:
    """
    Parse XET connection info from the HTTP headers or return None if not found.
    Args:
        headers (`Dict`):
           HTTP headers to extract the XET metadata from.
    Returns:
        `XetConnectionInfo` or `None`:
            The information needed to connect to the XET storage service.
            Returns `None` if the headers do not contain the XET connection info.
    """
    try:
        endpoint = headers[constants.HUGGINGFACE_HEADER_X_XET_ENDPOINT]
        access_token = headers[constants.HUGGINGFACE_HEADER_X_XET_ACCESS_TOKEN]
        expiration_unix_epoch = int(headers[constants.HUGGINGFACE_HEADER_X_XET_EXPIRATION])
    except (KeyError, ValueError, TypeError):
        return None

    return XetConnectionInfo(
        endpoint=endpoint,
        access_token=access_token,
        expiration_unix_epoch=expiration_unix_epoch,
    )


@validate_hf_hub_args
def refresh_xet_connection_info(
    *,
    file_data: XetFileData,
    headers: Dict[str, str],
) -> XetConnectionInfo:
    """
    Utilizes the information in the parsed metadata to request the Hub xet connection information.
    This includes the access token, expiration, and XET service URL.
    Args:
        file_data: (`XetFileData`):
            The file data needed to refresh the xet connection information.
        headers (`Dict[str, str]`):
            Headers to use for the request, including authorization headers and user agent.
    Returns:
        `XetConnectionInfo`:
            The connection information needed to make the request to the xet storage service.
    Raises:
        [`~utils.HfHubHTTPError`]
            If the Hub API returned an error.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If the Hub API response is improperly formatted.
    """
    if file_data.refresh_route is None:
        raise ValueError("The provided xet metadata does not contain a refresh endpoint.")
    return _fetch_xet_connection_info_with_url(file_data.refresh_route, headers)


@validate_hf_hub_args
def fetch_xet_connection_info_from_repo_info(
    *,
    token_type: XetTokenType,
    repo_id: str,
    repo_type: str,
    revision: Optional[str] = None,
    headers: Dict[str, str],
    endpoint: Optional[str] = None,
    params: Optional[Dict[str, str]] = None,
) -> XetConnectionInfo:
    """
    Uses the repo info to request a xet access token from Hub.
    Args:
        token_type (`XetTokenType`):
            Type of the token to request: `"read"` or `"write"`.
        repo_id (`str`):
            A namespace (user or an organization) and a repo name separated by a `/`.
        repo_type (`str`):
            Type of the repo to upload to: `"model"`, `"dataset"` or `"space"`.
        revision (`str`, `optional`):
            The revision of the repo to get the token for.
        headers (`Dict[str, str]`):
            Headers to use for the request, including authorization headers and user agent.
        endpoint (`str`, `optional`):
            The endpoint to use for the request. Defaults to the Hub endpoint.
        params (`Dict[str, str]`, `optional`):
            Additional parameters to pass with the request.
    Returns:
        `XetConnectionInfo`:
            The connection information needed to make the request to the xet storage service.
    Raises:
        [`~utils.HfHubHTTPError`]
            If the Hub API returned an error.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If the Hub API response is improperly formatted.
    """
    endpoint = endpoint if endpoint is not None else constants.ENDPOINT
    url = f"{endpoint}/api/{repo_type}s/{repo_id}/xet-{token_type.value}-token/{revision}"
    return _fetch_xet_connection_info_with_url(url, headers, params)


@validate_hf_hub_args
def _fetch_xet_connection_info_with_url(
    url: str,
    headers: Dict[str, str],
    params: Optional[Dict[str, str]] = None,
) -> XetConnectionInfo:
    """
    Requests the xet connection info from the supplied URL. This includes the
    access token, expiration time, and endpoint to use for the xet storage service.
    Args:
        url: (`str`):
            The access token endpoint URL.
        headers (`Dict[str, str]`):
            Headers to use for the request, including authorization headers and user agent.
        params (`Dict[str, str]`, `optional`):
            Additional parameters to pass with the request.
    Returns:
        `XetConnectionInfo`:
            The connection information needed to make the request to the xet storage service.
    Raises:
        [`~utils.HfHubHTTPError`]
            If the Hub API returned an error.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If the Hub API response is improperly formatted.
    """
    resp = get_session().get(headers=headers, url=url, params=params)
    hf_raise_for_status(resp)

    metadata = parse_xet_connection_info_from_headers(resp.headers)  # type: ignore
    if metadata is None:
        raise ValueError("Xet headers have not been correctly set by the server.")
    return metadata

# === NexusCore/openenv\Lib\site-packages\inquirer\render\console\__init__.py ===
import sys

from blessed import Terminal

from inquirer import errors
from inquirer import events
from inquirer import themes
from inquirer.render.console._checkbox import Checkbox
from inquirer.render.console._confirm import Confirm
from inquirer.render.console._editor import Editor
from inquirer.render.console._list import List
from inquirer.render.console._password import Password
from inquirer.render.console._path import Path
from inquirer.render.console._text import Text


class ConsoleRender:
    def __init__(self, event_generator=None, theme=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._event_gen = event_generator or events.KeyEventGenerator()
        self.terminal = Terminal()
        self._previous_error = None
        self._position = 0
        self._theme = theme or themes.Default()

    def render(self, question, answers=None):
        question.answers = answers or {}

        if question.ignore:
            return question.default

        clazz = self.render_factory(question.kind)
        render = clazz(question, terminal=self.terminal, theme=self._theme, show_default=question.show_default)

        self.clear_eos()

        try:
            return self._event_loop(render)
        finally:
            print("")

    def _event_loop(self, render):
        try:
            while True:
                self._relocate()
                self._print_status_bar(render)

                self._print_header(render)
                self._print_hint(render)
                self._print_options(render)

                self._process_input(render)
                self._force_initial_column()
        except errors.EndOfInput as e:
            self._go_to_end(render)
            return e.selection

    def _print_status_bar(self, render):
        if self._previous_error is None:
            self.clear_bottombar()
            return

        self.render_error(self._previous_error)
        self._previous_error = None

    def _print_options(self, render):
        for message, symbol, color in render.get_options():
            if hasattr(message, "decode"):  # python 2
                message = message.decode("utf-8")
            self.print_line(" {color}{s} {m}{t.normal}", m=message, color=color, s=symbol)

    def _print_header(self, render):
        base = render.get_header()

        header = base[: self.width - 9] + "..." if len(base) > self.width - 6 else base
        default_value = " ({color}{default}{normal})".format(
            default=render.question.default, color=self._theme.Question.default_color, normal=self.terminal.normal
        )
        show_default = render.question.default and render.show_default
        header += default_value if show_default else ""
        msg_template = (
            "{t.move_up}{t.clear_eol}{tq.brackets_color}[" "{tq.mark_color}?{tq.brackets_color}]{t.normal} {msg}"
        )

        # ensure any user input with { or } will not cause a formatting error
        escaped_current_value = str(render.get_current_value()).replace("{", "{{").replace("}", "}}")
        self.print_str(
            f"\n{msg_template}: {escaped_current_value}",
            msg=header,
            lf=not render.title_inline,
            tq=self._theme.Question,
        )

    def _print_hint(self, render):
        msg_template = "{t.move_up}{t.clear_eol}{color}{msg}"
        hint = ""
        if render.question.hints is not None:
            hint = render.get_hint()
        color = self._theme.Question.mark_color
        if hint:
            self.print_str(
                f"\n{msg_template}", msg=hint, color=color, lf=not render.title_inline, tq=self._theme.Question
            )

    def _process_input(self, render):
        try:
            ev = self._event_gen.next()
            if isinstance(ev, events.KeyPressed):
                render.process_input(ev.value)
        except errors.ValidationError as e:
            self._previous_error = e.value
        except errors.EndOfInput as e:
            try:
                render.question.validate(e.selection)
                raise
            except errors.ValidationError as e:
                self._previous_error = render.handle_validation_error(e)

    def _relocate(self):
        print(self._position * self.terminal.move_up, end="")
        self._force_initial_column()
        self._position = 0

    def _go_to_end(self, render):
        positions = len(list(render.get_options())) - self._position
        if positions > 0:
            print(self._position * self.terminal.move_down, end="")
        self._position = 0

    def _force_initial_column(self):
        self.print_str("\r")

    def render_error(self, message):
        if message:
            symbol = ">> "
            size = len(symbol) + 1
            length = len(message)
            message = message.rstrip()
            message = message if length + size < self.width else message[: self.width - (size + 3)] + "..."

            self.render_in_bottombar(
                "{t.red}{s}{t.normal}{t.bold}{msg}{t.normal} ".format(msg=message, s=symbol, t=self.terminal)
            )

    def render_in_bottombar(self, message):
        with self.terminal.location(0, self.height - 2):
            self.clear_eos()
            self.print_str(message)

    def clear_bottombar(self):
        with self.terminal.location(0, self.height - 2):
            self.clear_eos()

    def render_factory(self, question_type):
        matrix = {
            "text": Text,
            "editor": Editor,
            "password": Password,
            "confirm": Confirm,
            "list": List,
            "checkbox": Checkbox,
            "path": Path,
        }

        if question_type not in matrix:
            raise errors.UnknownQuestionTypeError()
        return matrix.get(question_type)

    def print_line(self, base, lf=True, **kwargs):
        self.print_str(base + self.terminal.clear_eol(), lf=lf, **kwargs)

    def print_str(self, base, lf=False, **kwargs):
        if lf:
            self._position += 1

        print(base.format(t=self.terminal, **kwargs), end="\n" if lf else "")
        sys.stdout.flush()

    def clear_eos(self):
        print(self.terminal.clear_eos(), end="")

    @property
    def width(self):
        return self.terminal.width or 80

    @property
    def height(self):
        return self.terminal.width or 24

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\multimodal_embeddings\embedding_handler.py ===
import json
from typing import Literal, Optional, Union

import httpx

import litellm
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    get_async_httpx_client,
)
from litellm.llms.vertex_ai.gemini.vertex_and_google_ai_studio_gemini import (
    VertexAIError,
    VertexLLM,
)
from litellm.types.utils import EmbeddingResponse

from .transformation import VertexAIMultimodalEmbeddingConfig

vertex_multimodal_embedding_handler = VertexAIMultimodalEmbeddingConfig()


class VertexMultimodalEmbedding(VertexLLM):
    def __init__(self) -> None:
        super().__init__()
        self.SUPPORTED_MULTIMODAL_EMBEDDING_MODELS = [
            "multimodalembedding",
            "multimodalembedding@001",
        ]

    def multimodal_embedding(
        self,
        model: str,
        input: Union[list, str],
        print_verbose,
        model_response: EmbeddingResponse,
        custom_llm_provider: Literal["gemini", "vertex_ai"],
        optional_params: dict,
        litellm_params: dict,
        logging_obj: LiteLLMLoggingObj,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        headers: dict = {},
        encoding=None,
        vertex_project=None,
        vertex_location=None,
        vertex_credentials=None,
        aembedding=False,
        timeout=300,
        client=None,
    ) -> EmbeddingResponse:
        _auth_header, vertex_project = self._ensure_access_token(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider=custom_llm_provider,
        )

        auth_header, url = self._get_token_and_url(
            model=model,
            auth_header=_auth_header,
            gemini_api_key=api_key,
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            vertex_credentials=vertex_credentials,
            stream=None,
            custom_llm_provider=custom_llm_provider,
            api_base=api_base,
            should_use_v1beta1_features=False,
            mode="embedding",
        )

        if client is None:
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    _httpx_timeout = httpx.Timeout(timeout)
                    _params["timeout"] = _httpx_timeout
            else:
                _params["timeout"] = httpx.Timeout(timeout=600.0, connect=5.0)

            sync_handler: HTTPHandler = HTTPHandler(**_params)  # type: ignore
        else:
            sync_handler = client  # type: ignore

        request_data = vertex_multimodal_embedding_handler.transform_embedding_request(
            model, input, optional_params, headers
        )

        headers = vertex_multimodal_embedding_handler.validate_environment(
            headers=headers,
            model=model,
            messages=[],
            optional_params=optional_params,
            api_key=auth_header,
            api_base=api_base,
            litellm_params=litellm_params,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=input,
            api_key="",
            additional_args={
                "complete_input_dict": request_data,
                "api_base": url,
                "headers": headers,
            },
        )

        if aembedding is True:
            return self.async_multimodal_embedding(  # type: ignore
                model=model,
                api_base=url,
                data=request_data,
                timeout=timeout,
                headers=headers,
                client=client,
                model_response=model_response,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logging_obj=logging_obj,
                api_key=api_key,
            )

        response = sync_handler.post(
            url=url,
            headers=headers,
            data=json.dumps(request_data),
        )

        return vertex_multimodal_embedding_handler.transform_embedding_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            api_key=api_key,
            request_data=request_data,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )

    async def async_multimodal_embedding(
        self,
        model: str,
        api_base: str,
        optional_params: dict,
        litellm_params: dict,
        data: dict,
        model_response: litellm.EmbeddingResponse,
        timeout: Optional[Union[float, httpx.Timeout]],
        logging_obj: LiteLLMLoggingObj,
        headers={},
        client: Optional[AsyncHTTPHandler] = None,
        api_key: Optional[str] = None,
    ) -> litellm.EmbeddingResponse:
        if client is None:
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    timeout = httpx.Timeout(timeout)
                _params["timeout"] = timeout
            client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders.VERTEX_AI,
                params={"timeout": timeout},
            )
        else:
            client = client  # type: ignore

        try:
            response = await client.post(api_base, headers=headers, json=data)  # type: ignore
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise VertexAIError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise VertexAIError(status_code=408, message="Timeout error occurred.")

        return vertex_multimodal_embedding_handler.transform_embedding_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            api_key=api_key,
            request_data=data,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )

# === NexusCore/openenv\Lib\site-packages\openai\types\completion_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, List, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypedDict

from .chat.chat_completion_stream_options_param import ChatCompletionStreamOptionsParam

__all__ = ["CompletionCreateParamsBase", "CompletionCreateParamsNonStreaming", "CompletionCreateParamsStreaming"]


class CompletionCreateParamsBase(TypedDict, total=False):
    model: Required[Union[str, Literal["gpt-3.5-turbo-instruct", "davinci-002", "babbage-002"]]]
    """ID of the model to use.

    You can use the
    [List models](https://platform.openai.com/docs/api-reference/models/list) API to
    see all of your available models, or see our
    [Model overview](https://platform.openai.com/docs/models) for descriptions of
    them.
    """

    prompt: Required[Union[str, List[str], Iterable[int], Iterable[Iterable[int]], None]]
    """
    The prompt(s) to generate completions for, encoded as a string, array of
    strings, array of tokens, or array of token arrays.

    Note that <|endoftext|> is the document separator that the model sees during
    training, so if a prompt is not specified the model will generate as if from the
    beginning of a new document.
    """

    best_of: Optional[int]
    """
    Generates `best_of` completions server-side and returns the "best" (the one with
    the highest log probability per token). Results cannot be streamed.

    When used with `n`, `best_of` controls the number of candidate completions and
    `n` specifies how many to return – `best_of` must be greater than `n`.

    **Note:** Because this parameter generates many completions, it can quickly
    consume your token quota. Use carefully and ensure that you have reasonable
    settings for `max_tokens` and `stop`.
    """

    echo: Optional[bool]
    """Echo back the prompt in addition to the completion"""

    frequency_penalty: Optional[float]
    """Number between -2.0 and 2.0.

    Positive values penalize new tokens based on their existing frequency in the
    text so far, decreasing the model's likelihood to repeat the same line verbatim.

    [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)
    """

    logit_bias: Optional[Dict[str, int]]
    """Modify the likelihood of specified tokens appearing in the completion.

    Accepts a JSON object that maps tokens (specified by their token ID in the GPT
    tokenizer) to an associated bias value from -100 to 100. You can use this
    [tokenizer tool](/tokenizer?view=bpe) to convert text to token IDs.
    Mathematically, the bias is added to the logits generated by the model prior to
    sampling. The exact effect will vary per model, but values between -1 and 1
    should decrease or increase likelihood of selection; values like -100 or 100
    should result in a ban or exclusive selection of the relevant token.

    As an example, you can pass `{"50256": -100}` to prevent the <|endoftext|> token
    from being generated.
    """

    logprobs: Optional[int]
    """
    Include the log probabilities on the `logprobs` most likely output tokens, as
    well the chosen tokens. For example, if `logprobs` is 5, the API will return a
    list of the 5 most likely tokens. The API will always return the `logprob` of
    the sampled token, so there may be up to `logprobs+1` elements in the response.

    The maximum value for `logprobs` is 5.
    """

    max_tokens: Optional[int]
    """
    The maximum number of [tokens](/tokenizer) that can be generated in the
    completion.

    The token count of your prompt plus `max_tokens` cannot exceed the model's
    context length.
    [Example Python code](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken)
    for counting tokens.
    """

    n: Optional[int]
    """How many completions to generate for each prompt.

    **Note:** Because this parameter generates many completions, it can quickly
    consume your token quota. Use carefully and ensure that you have reasonable
    settings for `max_tokens` and `stop`.
    """

    presence_penalty: Optional[float]
    """Number between -2.0 and 2.0.

    Positive values penalize new tokens based on whether they appear in the text so
    far, increasing the model's likelihood to talk about new topics.

    [See more information about frequency and presence penalties.](https://platform.openai.com/docs/guides/text-generation)
    """

    seed: Optional[int]
    """
    If specified, our system will make a best effort to sample deterministically,
    such that repeated requests with the same `seed` and parameters should return
    the same result.

    Determinism is not guaranteed, and you should refer to the `system_fingerprint`
    response parameter to monitor changes in the backend.
    """

    stop: Union[Optional[str], List[str], None]
    """Not supported with latest reasoning models `o3` and `o4-mini`.

    Up to 4 sequences where the API will stop generating further tokens. The
    returned text will not contain the stop sequence.
    """

    stream_options: Optional[ChatCompletionStreamOptionsParam]
    """Options for streaming response. Only set this when you set `stream: true`."""

    suffix: Optional[str]
    """The suffix that comes after a completion of inserted text.

    This parameter is only supported for `gpt-3.5-turbo-instruct`.
    """

    temperature: Optional[float]
    """What sampling temperature to use, between 0 and 2.

    Higher values like 0.8 will make the output more random, while lower values like
    0.2 will make it more focused and deterministic.

    We generally recommend altering this or `top_p` but not both.
    """

    top_p: Optional[float]
    """
    An alternative to sampling with temperature, called nucleus sampling, where the
    model considers the results of the tokens with top_p probability mass. So 0.1
    means only the tokens comprising the top 10% probability mass are considered.

    We generally recommend altering this or `temperature` but not both.
    """

    user: str
    """
    A unique identifier representing your end-user, which can help OpenAI to monitor
    and detect abuse.
    [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).
    """


class CompletionCreateParamsNonStreaming(CompletionCreateParamsBase, total=False):
    stream: Optional[Literal[False]]
    """Whether to stream back partial progress.

    If set, tokens will be sent as data-only
    [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format)
    as they become available, with the stream terminated by a `data: [DONE]`
    message.
    [Example Python code](https://cookbook.openai.com/examples/how_to_stream_completions).
    """


class CompletionCreateParamsStreaming(CompletionCreateParamsBase):
    stream: Required[Literal[True]]
    """Whether to stream back partial progress.

    If set, tokens will be sent as data-only
    [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format)
    as they become available, with the stream terminated by a `data: [DONE]`
    message.
    [Example Python code](https://cookbook.openai.com/examples/how_to_stream_completions).
    """


CompletionCreateParams = Union[CompletionCreateParamsNonStreaming, CompletionCreateParamsStreaming]

# === NexusCore/openenv\Lib\site-packages\pip\_internal\utils\compatibility_tags.py ===
"""Generate and work with PEP 425 Compatibility Tags.
"""

import re
from typing import List, Optional, Tuple

from pip._vendor.packaging.tags import (
    PythonVersion,
    Tag,
    compatible_tags,
    cpython_tags,
    generic_tags,
    interpreter_name,
    interpreter_version,
    ios_platforms,
    mac_platforms,
)

_apple_arch_pat = re.compile(r"(.+)_(\d+)_(\d+)_(.+)")


def version_info_to_nodot(version_info: Tuple[int, ...]) -> str:
    # Only use up to the first two numbers.
    return "".join(map(str, version_info[:2]))


def _mac_platforms(arch: str) -> List[str]:
    match = _apple_arch_pat.match(arch)
    if match:
        name, major, minor, actual_arch = match.groups()
        mac_version = (int(major), int(minor))
        arches = [
            # Since we have always only checked that the platform starts
            # with "macosx", for backwards-compatibility we extract the
            # actual prefix provided by the user in case they provided
            # something like "macosxcustom_". It may be good to remove
            # this as undocumented or deprecate it in the future.
            "{}_{}".format(name, arch[len("macosx_") :])
            for arch in mac_platforms(mac_version, actual_arch)
        ]
    else:
        # arch pattern didn't match (?!)
        arches = [arch]
    return arches


def _ios_platforms(arch: str) -> List[str]:
    match = _apple_arch_pat.match(arch)
    if match:
        name, major, minor, actual_multiarch = match.groups()
        ios_version = (int(major), int(minor))
        arches = [
            # Since we have always only checked that the platform starts
            # with "ios", for backwards-compatibility we extract the
            # actual prefix provided by the user in case they provided
            # something like "ioscustom_". It may be good to remove
            # this as undocumented or deprecate it in the future.
            "{}_{}".format(name, arch[len("ios_") :])
            for arch in ios_platforms(ios_version, actual_multiarch)
        ]
    else:
        # arch pattern didn't match (?!)
        arches = [arch]
    return arches


def _custom_manylinux_platforms(arch: str) -> List[str]:
    arches = [arch]
    arch_prefix, arch_sep, arch_suffix = arch.partition("_")
    if arch_prefix == "manylinux2014":
        # manylinux1/manylinux2010 wheels run on most manylinux2014 systems
        # with the exception of wheels depending on ncurses. PEP 599 states
        # manylinux1/manylinux2010 wheels should be considered
        # manylinux2014 wheels:
        # https://www.python.org/dev/peps/pep-0599/#backwards-compatibility-with-manylinux2010-wheels
        if arch_suffix in {"i686", "x86_64"}:
            arches.append("manylinux2010" + arch_sep + arch_suffix)
            arches.append("manylinux1" + arch_sep + arch_suffix)
    elif arch_prefix == "manylinux2010":
        # manylinux1 wheels run on most manylinux2010 systems with the
        # exception of wheels depending on ncurses. PEP 571 states
        # manylinux1 wheels should be considered manylinux2010 wheels:
        # https://www.python.org/dev/peps/pep-0571/#backwards-compatibility-with-manylinux1-wheels
        arches.append("manylinux1" + arch_sep + arch_suffix)
    return arches


def _get_custom_platforms(arch: str) -> List[str]:
    arch_prefix, arch_sep, arch_suffix = arch.partition("_")
    if arch.startswith("macosx"):
        arches = _mac_platforms(arch)
    elif arch.startswith("ios"):
        arches = _ios_platforms(arch)
    elif arch_prefix in ["manylinux2014", "manylinux2010"]:
        arches = _custom_manylinux_platforms(arch)
    else:
        arches = [arch]
    return arches


def _expand_allowed_platforms(platforms: Optional[List[str]]) -> Optional[List[str]]:
    if not platforms:
        return None

    seen = set()
    result = []

    for p in platforms:
        if p in seen:
            continue
        additions = [c for c in _get_custom_platforms(p) if c not in seen]
        seen.update(additions)
        result.extend(additions)

    return result


def _get_python_version(version: str) -> PythonVersion:
    if len(version) > 1:
        return int(version[0]), int(version[1:])
    else:
        return (int(version[0]),)


def _get_custom_interpreter(
    implementation: Optional[str] = None, version: Optional[str] = None
) -> str:
    if implementation is None:
        implementation = interpreter_name()
    if version is None:
        version = interpreter_version()
    return f"{implementation}{version}"


def get_supported(
    version: Optional[str] = None,
    platforms: Optional[List[str]] = None,
    impl: Optional[str] = None,
    abis: Optional[List[str]] = None,
) -> List[Tag]:
    """Return a list of supported tags for each version specified in
    `versions`.

    :param version: a string version, of the form "33" or "32",
        or None. The version will be assumed to support our ABI.
    :param platform: specify a list of platforms you want valid
        tags for, or None. If None, use the local system platform.
    :param impl: specify the exact implementation you want valid
        tags for, or None. If None, use the local interpreter impl.
    :param abis: specify a list of abis you want valid
        tags for, or None. If None, use the local interpreter abi.
    """
    supported: List[Tag] = []

    python_version: Optional[PythonVersion] = None
    if version is not None:
        python_version = _get_python_version(version)

    interpreter = _get_custom_interpreter(impl, version)

    platforms = _expand_allowed_platforms(platforms)

    is_cpython = (impl or interpreter_name()) == "cp"
    if is_cpython:
        supported.extend(
            cpython_tags(
                python_version=python_version,
                abis=abis,
                platforms=platforms,
            )
        )
    else:
        supported.extend(
            generic_tags(
                interpreter=interpreter,
                abis=abis,
                platforms=platforms,
            )
        )
    supported.extend(
        compatible_tags(
            python_version=python_version,
            interpreter=interpreter,
            platforms=platforms,
        )
    )

    return supported

# === NexusCore/openenv\Lib\site-packages\pydantic\plugin\__init__.py ===
"""!!! abstract "Usage Documentation"
    [Build a Plugin](../concepts/plugins.md#build-a-plugin)

Plugin interface for Pydantic plugins, and related types.
"""

from __future__ import annotations

from typing import Any, Callable, Literal, NamedTuple

from pydantic_core import CoreConfig, CoreSchema, ValidationError
from typing_extensions import Protocol, TypeAlias

__all__ = (
    'PydanticPluginProtocol',
    'BaseValidateHandlerProtocol',
    'ValidatePythonHandlerProtocol',
    'ValidateJsonHandlerProtocol',
    'ValidateStringsHandlerProtocol',
    'NewSchemaReturns',
    'SchemaTypePath',
    'SchemaKind',
)

NewSchemaReturns: TypeAlias = 'tuple[ValidatePythonHandlerProtocol | None, ValidateJsonHandlerProtocol | None, ValidateStringsHandlerProtocol | None]'


class SchemaTypePath(NamedTuple):
    """Path defining where `schema_type` was defined, or where `TypeAdapter` was called."""

    module: str
    name: str


SchemaKind: TypeAlias = Literal['BaseModel', 'TypeAdapter', 'dataclass', 'create_model', 'validate_call']


class PydanticPluginProtocol(Protocol):
    """Protocol defining the interface for Pydantic plugins."""

    def new_schema_validator(
        self,
        schema: CoreSchema,
        schema_type: Any,
        schema_type_path: SchemaTypePath,
        schema_kind: SchemaKind,
        config: CoreConfig | None,
        plugin_settings: dict[str, object],
    ) -> tuple[
        ValidatePythonHandlerProtocol | None, ValidateJsonHandlerProtocol | None, ValidateStringsHandlerProtocol | None
    ]:
        """This method is called for each plugin every time a new [`SchemaValidator`][pydantic_core.SchemaValidator]
        is created.

        It should return an event handler for each of the three validation methods, or `None` if the plugin does not
        implement that method.

        Args:
            schema: The schema to validate against.
            schema_type: The original type which the schema was created from, e.g. the model class.
            schema_type_path: Path defining where `schema_type` was defined, or where `TypeAdapter` was called.
            schema_kind: The kind of schema to validate against.
            config: The config to use for validation.
            plugin_settings: Any plugin settings.

        Returns:
            A tuple of optional event handlers for each of the three validation methods -
                `validate_python`, `validate_json`, `validate_strings`.
        """
        raise NotImplementedError('Pydantic plugins should implement `new_schema_validator`.')


class BaseValidateHandlerProtocol(Protocol):
    """Base class for plugin callbacks protocols.

    You shouldn't implement this protocol directly, instead use one of the subclasses with adds the correctly
    typed `on_error` method.
    """

    on_enter: Callable[..., None]
    """`on_enter` is changed to be more specific on all subclasses"""

    def on_success(self, result: Any) -> None:
        """Callback to be notified of successful validation.

        Args:
            result: The result of the validation.
        """
        return

    def on_error(self, error: ValidationError) -> None:
        """Callback to be notified of validation errors.

        Args:
            error: The validation error.
        """
        return

    def on_exception(self, exception: Exception) -> None:
        """Callback to be notified of validation exceptions.

        Args:
            exception: The exception raised during validation.
        """
        return


class ValidatePythonHandlerProtocol(BaseValidateHandlerProtocol, Protocol):
    """Event handler for `SchemaValidator.validate_python`."""

    def on_enter(
        self,
        input: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: dict[str, Any] | None = None,
        self_instance: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> None:
        """Callback to be notified of validation start, and create an instance of the event handler.

        Args:
            input: The input to be validated.
            strict: Whether to validate the object in strict mode.
            from_attributes: Whether to validate objects as inputs by extracting attributes.
            context: The context to use for validation, this is passed to functional validators.
            self_instance: An instance of a model to set attributes on from validation, this is used when running
                validation from the `__init__` method of a model.
            by_alias: Whether to use the field's alias to match the input data to an attribute.
            by_name: Whether to use the field's name to match the input data to an attribute.
        """
        pass


class ValidateJsonHandlerProtocol(BaseValidateHandlerProtocol, Protocol):
    """Event handler for `SchemaValidator.validate_json`."""

    def on_enter(
        self,
        input: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        context: dict[str, Any] | None = None,
        self_instance: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> None:
        """Callback to be notified of validation start, and create an instance of the event handler.

        Args:
            input: The JSON data to be validated.
            strict: Whether to validate the object in strict mode.
            context: The context to use for validation, this is passed to functional validators.
            self_instance: An instance of a model to set attributes on from validation, this is used when running
                validation from the `__init__` method of a model.
            by_alias: Whether to use the field's alias to match the input data to an attribute.
            by_name: Whether to use the field's name to match the input data to an attribute.
        """
        pass


StringInput: TypeAlias = 'dict[str, StringInput]'


class ValidateStringsHandlerProtocol(BaseValidateHandlerProtocol, Protocol):
    """Event handler for `SchemaValidator.validate_strings`."""

    def on_enter(
        self,
        input: StringInput,
        *,
        strict: bool | None = None,
        context: dict[str, Any] | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> None:
        """Callback to be notified of validation start, and create an instance of the event handler.

        Args:
            input: The string data to be validated.
            strict: Whether to validate the object in strict mode.
            context: The context to use for validation, this is passed to functional validators.
            by_alias: Whether to use the field's alias to match the input data to an attribute.
            by_name: Whether to use the field's name to match the input data to an attribute.
        """
        pass

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_signature.py ===
from __future__ import annotations

import dataclasses
from inspect import Parameter, Signature, signature
from typing import TYPE_CHECKING, Any, Callable

from pydantic_core import PydanticUndefined

from ._utils import is_valid_identifier

if TYPE_CHECKING:
    from ..config import ExtraValues
    from ..fields import FieldInfo


# Copied over from stdlib dataclasses
class _HAS_DEFAULT_FACTORY_CLASS:
    def __repr__(self):
        return '<factory>'


_HAS_DEFAULT_FACTORY = _HAS_DEFAULT_FACTORY_CLASS()


def _field_name_for_signature(field_name: str, field_info: FieldInfo) -> str:
    """Extract the correct name to use for the field when generating a signature.

    Assuming the field has a valid alias, this will return the alias. Otherwise, it will return the field name.
    First priority is given to the alias, then the validation_alias, then the field name.

    Args:
        field_name: The name of the field
        field_info: The corresponding FieldInfo object.

    Returns:
        The correct name to use when generating a signature.
    """
    if isinstance(field_info.alias, str) and is_valid_identifier(field_info.alias):
        return field_info.alias
    if isinstance(field_info.validation_alias, str) and is_valid_identifier(field_info.validation_alias):
        return field_info.validation_alias

    return field_name


def _process_param_defaults(param: Parameter) -> Parameter:
    """Modify the signature for a parameter in a dataclass where the default value is a FieldInfo instance.

    Args:
        param (Parameter): The parameter

    Returns:
        Parameter: The custom processed parameter
    """
    from ..fields import FieldInfo

    param_default = param.default
    if isinstance(param_default, FieldInfo):
        annotation = param.annotation
        # Replace the annotation if appropriate
        # inspect does "clever" things to show annotations as strings because we have
        # `from __future__ import annotations` in main, we don't want that
        if annotation == 'Any':
            annotation = Any

        # Replace the field default
        default = param_default.default
        if default is PydanticUndefined:
            if param_default.default_factory is PydanticUndefined:
                default = Signature.empty
            else:
                # this is used by dataclasses to indicate a factory exists:
                default = dataclasses._HAS_DEFAULT_FACTORY  # type: ignore
        return param.replace(
            annotation=annotation, name=_field_name_for_signature(param.name, param_default), default=default
        )
    return param


def _generate_signature_parameters(  # noqa: C901 (ignore complexity, could use a refactor)
    init: Callable[..., None],
    fields: dict[str, FieldInfo],
    validate_by_name: bool,
    extra: ExtraValues | None,
) -> dict[str, Parameter]:
    """Generate a mapping of parameter names to Parameter objects for a pydantic BaseModel or dataclass."""
    from itertools import islice

    present_params = signature(init).parameters.values()
    merged_params: dict[str, Parameter] = {}
    var_kw = None
    use_var_kw = False

    for param in islice(present_params, 1, None):  # skip self arg
        # inspect does "clever" things to show annotations as strings because we have
        # `from __future__ import annotations` in main, we don't want that
        if fields.get(param.name):
            # exclude params with init=False
            if getattr(fields[param.name], 'init', True) is False:
                continue
            param = param.replace(name=_field_name_for_signature(param.name, fields[param.name]))
        if param.annotation == 'Any':
            param = param.replace(annotation=Any)
        if param.kind is param.VAR_KEYWORD:
            var_kw = param
            continue
        merged_params[param.name] = param

    if var_kw:  # if custom init has no var_kw, fields which are not declared in it cannot be passed through
        allow_names = validate_by_name
        for field_name, field in fields.items():
            # when alias is a str it should be used for signature generation
            param_name = _field_name_for_signature(field_name, field)

            if field_name in merged_params or param_name in merged_params:
                continue

            if not is_valid_identifier(param_name):
                if allow_names:
                    param_name = field_name
                else:
                    use_var_kw = True
                    continue

            if field.is_required():
                default = Parameter.empty
            elif field.default_factory is not None:
                # Mimics stdlib dataclasses:
                default = _HAS_DEFAULT_FACTORY
            else:
                default = field.default
            merged_params[param_name] = Parameter(
                param_name,
                Parameter.KEYWORD_ONLY,
                annotation=field.rebuild_annotation(),
                default=default,
            )

    if extra == 'allow':
        use_var_kw = True

    if var_kw and use_var_kw:
        # Make sure the parameter for extra kwargs
        # does not have the same name as a field
        default_model_signature = [
            ('self', Parameter.POSITIONAL_ONLY),
            ('data', Parameter.VAR_KEYWORD),
        ]
        if [(p.name, p.kind) for p in present_params] == default_model_signature:
            # if this is the standard model signature, use extra_data as the extra args name
            var_kw_name = 'extra_data'
        else:
            # else start from var_kw
            var_kw_name = var_kw.name

        # generate a name that's definitely unique
        while var_kw_name in fields:
            var_kw_name += '_'
        merged_params[var_kw_name] = var_kw.replace(name=var_kw_name)

    return merged_params


def generate_pydantic_signature(
    init: Callable[..., None],
    fields: dict[str, FieldInfo],
    validate_by_name: bool,
    extra: ExtraValues | None,
    is_dataclass: bool = False,
) -> Signature:
    """Generate signature for a pydantic BaseModel or dataclass.

    Args:
        init: The class init.
        fields: The model fields.
        validate_by_name: The `validate_by_name` value of the config.
        extra: The `extra` value of the config.
        is_dataclass: Whether the model is a dataclass.

    Returns:
        The dataclass/BaseModel subclass signature.
    """
    merged_params = _generate_signature_parameters(init, fields, validate_by_name, extra)

    if is_dataclass:
        merged_params = {k: _process_param_defaults(v) for k, v in merged_params.items()}

    return Signature(parameters=list(merged_params.values()), return_annotation=None)

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\dbgcommands.py ===
# Command Handlers for the debugger.

# Not in the debugger package, as I always want these interfaces to be
# available, even if the debugger has not yet been (or can not be)
# imported
import warnings

import win32ui
from pywin.scintilla.control import CScintillaEditInterface

from . import scriptutils

IdToBarNames = {
    win32ui.IDC_DBG_STACK: ("Stack", 0),
    win32ui.IDC_DBG_BREAKPOINTS: ("Breakpoints", 0),
    win32ui.IDC_DBG_WATCH: ("Watch", 1),
}


class DebuggerCommandHandler:
    def HookCommands(self):
        commands = (
            (self.OnStep, None, win32ui.IDC_DBG_STEP),
            (self.OnStepOut, self.OnUpdateOnlyBreak, win32ui.IDC_DBG_STEPOUT),
            (self.OnStepOver, None, win32ui.IDC_DBG_STEPOVER),
            (self.OnGo, None, win32ui.IDC_DBG_GO),
            (self.OnClose, self.OnUpdateClose, win32ui.IDC_DBG_CLOSE),
            (self.OnAdd, self.OnUpdateAddBreakpoints, win32ui.IDC_DBG_ADD),
            (self.OnClearAll, self.OnUpdateClearAllBreakpoints, win32ui.IDC_DBG_CLEAR),
            # 		                  (self.OnDebuggerToolbar, self.OnUpdateDebuggerToolbar, win32ui.ID_DEBUGGER_TOOLBAR),
        )

        frame = win32ui.GetMainFrame()

        for methHandler, methUpdate, id in commands:
            frame.HookCommand(methHandler, id)
            if not methUpdate is None:
                frame.HookCommandUpdate(methUpdate, id)

        for id in IdToBarNames:
            frame.HookCommand(self.OnDebuggerBar, id)
            frame.HookCommandUpdate(self.OnUpdateDebuggerBar, id)

    def OnDebuggerToolbar(self, id, code):
        if code == 0:
            return not win32ui.GetMainFrame().OnBarCheck(id)

    def OnUpdateDebuggerToolbar(self, cmdui):
        win32ui.GetMainFrame().OnUpdateControlBarMenu(cmdui)
        cmdui.Enable(1)

    def _GetDebugger(self):
        try:
            import pywin.debugger

            return pywin.debugger.currentDebugger
        except ImportError:
            return None

    def _DoOrStart(self, doMethod, startFlag):
        d = self._GetDebugger()
        if d is not None and d.IsDebugging():
            method = getattr(d, doMethod)
            method()
        else:
            scriptutils.RunScript(
                defName=None, defArgs=None, bShowDialog=0, debuggingType=startFlag
            )

    def OnStep(self, msg, code):
        self._DoOrStart("do_set_step", scriptutils.RS_DEBUGGER_STEP)

    def OnStepOver(self, msg, code):
        self._DoOrStart("do_set_next", scriptutils.RS_DEBUGGER_STEP)

    def OnStepOut(self, msg, code):
        d = self._GetDebugger()
        if d is not None and d.IsDebugging():
            d.do_set_return()

    def OnGo(self, msg, code):
        self._DoOrStart("do_set_continue", scriptutils.RS_DEBUGGER_GO)

    def OnClose(self, msg, code):
        d = self._GetDebugger()
        if d is not None:
            if d.IsDebugging():
                d.set_quit()
            else:
                d.close()

    def OnUpdateClose(self, cmdui):
        d = self._GetDebugger()
        if d is not None and d.inited:
            cmdui.Enable(1)
        else:
            cmdui.Enable(0)

    def OnAdd(self, msg, code):
        doc, view = scriptutils.GetActiveEditorDocument()
        if doc is None:
            ## Don't do a messagebox, as this could be triggered from the app's
            ## idle loop whenever the debug toolbar is visible, giving a never-ending
            ## series of dialogs.  This can happen when the OnUpdate handler
            ## for the toolbar button IDC_DBG_ADD fails, since MFC falls back to
            ## sending a normal command if the UI update command fails.
            ## win32ui.MessageBox('There is no active window - no breakpoint can be added')
            warnings.warn("There is no active window - no breakpoint can be added")
            return None
        pathName = doc.GetPathName()
        lineNo = view.LineFromChar(view.GetSel()[0]) + 1
        # If I have a debugger, then tell it, otherwise just add a marker
        d = self._GetDebugger()
        if d is None:
            import pywin.framework.editor.color.coloreditor

            doc.MarkerToggle(
                lineNo, pywin.framework.editor.color.coloreditor.MARKER_BREAKPOINT
            )
        else:
            if d.get_break(pathName, lineNo):
                win32ui.SetStatusText("Clearing breakpoint", 1)
                rc = d.clear_break(pathName, lineNo)
            else:
                win32ui.SetStatusText("Setting breakpoint", 1)
                rc = d.set_break(pathName, lineNo)
            if rc:
                win32ui.MessageBox(rc)
            d.GUIRespondDebuggerData()

    def OnClearAll(self, msg, code):
        win32ui.SetStatusText("Clearing all breakpoints")
        d = self._GetDebugger()
        if d is None:
            import pywin.framework.editor
            import pywin.framework.editor.color.coloreditor

            for doc in pywin.framework.editor.editorTemplate.GetDocumentList():
                doc.MarkerDeleteAll(
                    pywin.framework.editor.color.coloreditor.MARKER_BREAKPOINT
                )
        else:
            d.clear_all_breaks()
            d.UpdateAllLineStates()
            d.GUIRespondDebuggerData()

    def OnUpdateOnlyBreak(self, cmdui):
        d = self._GetDebugger()
        ok = d is not None and d.IsBreak()
        cmdui.Enable(ok)

    def OnUpdateAddBreakpoints(self, cmdui):
        doc, view = scriptutils.GetActiveEditorDocument()
        if doc is None or not isinstance(view, CScintillaEditInterface):
            enabled = 0
        else:
            enabled = 1
            lineNo = view.LineFromChar(view.GetSel()[0]) + 1
            import pywin.framework.editor.color.coloreditor

            cmdui.SetCheck(
                doc.MarkerAtLine(
                    lineNo, pywin.framework.editor.color.coloreditor.MARKER_BREAKPOINT
                )
                != 0
            )
        cmdui.Enable(enabled)

    def OnUpdateClearAllBreakpoints(self, cmdui):
        d = self._GetDebugger()
        cmdui.Enable(d is None or len(d.breaks) != 0)

    def OnUpdateDebuggerBar(self, cmdui):
        name, enabled = IdToBarNames.get(cmdui.m_nID, (None, 0))
        d = self._GetDebugger()
        if d is not None and d.IsDebugging() and name is not None:
            enabled = 1
            bar = d.GetDebuggerBar(name)
            cmdui.SetCheck(bar.IsWindowVisible())
        cmdui.Enable(enabled)

    def OnDebuggerBar(self, id, code):
        name = IdToBarNames.get(id)[0]
        d = self._GetDebugger()
        if d is not None and name is not None:
            bar = d.GetDebuggerBar(name)
            newState = not bar.IsWindowVisible()
            win32ui.GetMainFrame().ShowControlBar(bar, newState, 1)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\log.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Log
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import network
from . import runtime


@dataclass
class LogEntry:
    '''
    Log entry.
    '''
    #: Log entry source.
    source: str

    #: Log entry severity.
    level: str

    #: Logged text.
    text: str

    #: Timestamp when this entry was added.
    timestamp: runtime.Timestamp

    category: typing.Optional[str] = None

    #: URL of the resource if known.
    url: typing.Optional[str] = None

    #: Line number in the resource.
    line_number: typing.Optional[int] = None

    #: JavaScript stack trace.
    stack_trace: typing.Optional[runtime.StackTrace] = None

    #: Identifier of the network request associated with this entry.
    network_request_id: typing.Optional[network.RequestId] = None

    #: Identifier of the worker associated with this entry.
    worker_id: typing.Optional[str] = None

    #: Call arguments.
    args: typing.Optional[typing.List[runtime.RemoteObject]] = None

    def to_json(self):
        json = dict()
        json['source'] = self.source
        json['level'] = self.level
        json['text'] = self.text
        json['timestamp'] = self.timestamp.to_json()
        if self.category is not None:
            json['category'] = self.category
        if self.url is not None:
            json['url'] = self.url
        if self.line_number is not None:
            json['lineNumber'] = self.line_number
        if self.stack_trace is not None:
            json['stackTrace'] = self.stack_trace.to_json()
        if self.network_request_id is not None:
            json['networkRequestId'] = self.network_request_id.to_json()
        if self.worker_id is not None:
            json['workerId'] = self.worker_id
        if self.args is not None:
            json['args'] = [i.to_json() for i in self.args]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source=str(json['source']),
            level=str(json['level']),
            text=str(json['text']),
            timestamp=runtime.Timestamp.from_json(json['timestamp']),
            category=str(json['category']) if 'category' in json else None,
            url=str(json['url']) if 'url' in json else None,
            line_number=int(json['lineNumber']) if 'lineNumber' in json else None,
            stack_trace=runtime.StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            network_request_id=network.RequestId.from_json(json['networkRequestId']) if 'networkRequestId' in json else None,
            worker_id=str(json['workerId']) if 'workerId' in json else None,
            args=[runtime.RemoteObject.from_json(i) for i in json['args']] if 'args' in json else None,
        )


@dataclass
class ViolationSetting:
    '''
    Violation configuration setting.
    '''
    #: Violation type.
    name: str

    #: Time threshold to trigger upon.
    threshold: float

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['threshold'] = self.threshold
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            threshold=float(json['threshold']),
        )


def clear() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears the log.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.clear',
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables log domain, prevents further log entries from being reported to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables log domain, sends the entries collected so far to the client by means of the
    ``entryAdded`` notification.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.enable',
    }
    json = yield cmd_dict


def start_violations_report(
        config: typing.List[ViolationSetting]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    start violation reporting.

    :param config: Configuration for violations.
    '''
    params: T_JSON_DICT = dict()
    params['config'] = [i.to_json() for i in config]
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.startViolationsReport',
        'params': params,
    }
    json = yield cmd_dict


def stop_violations_report() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stop violation reporting.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.stopViolationsReport',
    }
    json = yield cmd_dict


@event_class('Log.entryAdded')
@dataclass
class EntryAdded:
    '''
    Issued when new message was logged.
    '''
    #: The entry.
    entry: LogEntry

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> EntryAdded:
        return cls(
            entry=LogEntry.from_json(json['entry'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\log.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Log
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import network
from . import runtime


@dataclass
class LogEntry:
    '''
    Log entry.
    '''
    #: Log entry source.
    source: str

    #: Log entry severity.
    level: str

    #: Logged text.
    text: str

    #: Timestamp when this entry was added.
    timestamp: runtime.Timestamp

    category: typing.Optional[str] = None

    #: URL of the resource if known.
    url: typing.Optional[str] = None

    #: Line number in the resource.
    line_number: typing.Optional[int] = None

    #: JavaScript stack trace.
    stack_trace: typing.Optional[runtime.StackTrace] = None

    #: Identifier of the network request associated with this entry.
    network_request_id: typing.Optional[network.RequestId] = None

    #: Identifier of the worker associated with this entry.
    worker_id: typing.Optional[str] = None

    #: Call arguments.
    args: typing.Optional[typing.List[runtime.RemoteObject]] = None

    def to_json(self):
        json = dict()
        json['source'] = self.source
        json['level'] = self.level
        json['text'] = self.text
        json['timestamp'] = self.timestamp.to_json()
        if self.category is not None:
            json['category'] = self.category
        if self.url is not None:
            json['url'] = self.url
        if self.line_number is not None:
            json['lineNumber'] = self.line_number
        if self.stack_trace is not None:
            json['stackTrace'] = self.stack_trace.to_json()
        if self.network_request_id is not None:
            json['networkRequestId'] = self.network_request_id.to_json()
        if self.worker_id is not None:
            json['workerId'] = self.worker_id
        if self.args is not None:
            json['args'] = [i.to_json() for i in self.args]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source=str(json['source']),
            level=str(json['level']),
            text=str(json['text']),
            timestamp=runtime.Timestamp.from_json(json['timestamp']),
            category=str(json['category']) if 'category' in json else None,
            url=str(json['url']) if 'url' in json else None,
            line_number=int(json['lineNumber']) if 'lineNumber' in json else None,
            stack_trace=runtime.StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            network_request_id=network.RequestId.from_json(json['networkRequestId']) if 'networkRequestId' in json else None,
            worker_id=str(json['workerId']) if 'workerId' in json else None,
            args=[runtime.RemoteObject.from_json(i) for i in json['args']] if 'args' in json else None,
        )


@dataclass
class ViolationSetting:
    '''
    Violation configuration setting.
    '''
    #: Violation type.
    name: str

    #: Time threshold to trigger upon.
    threshold: float

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['threshold'] = self.threshold
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            threshold=float(json['threshold']),
        )


def clear() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears the log.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.clear',
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables log domain, prevents further log entries from being reported to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables log domain, sends the entries collected so far to the client by means of the
    ``entryAdded`` notification.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.enable',
    }
    json = yield cmd_dict


def start_violations_report(
        config: typing.List[ViolationSetting]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    start violation reporting.

    :param config: Configuration for violations.
    '''
    params: T_JSON_DICT = dict()
    params['config'] = [i.to_json() for i in config]
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.startViolationsReport',
        'params': params,
    }
    json = yield cmd_dict


def stop_violations_report() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stop violation reporting.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.stopViolationsReport',
    }
    json = yield cmd_dict


@event_class('Log.entryAdded')
@dataclass
class EntryAdded:
    '''
    Issued when new message was logged.
    '''
    #: The entry.
    entry: LogEntry

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> EntryAdded:
        return cls(
            entry=LogEntry.from_json(json['entry'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\log.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Log
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import network
from . import runtime


@dataclass
class LogEntry:
    '''
    Log entry.
    '''
    #: Log entry source.
    source: str

    #: Log entry severity.
    level: str

    #: Logged text.
    text: str

    #: Timestamp when this entry was added.
    timestamp: runtime.Timestamp

    category: typing.Optional[str] = None

    #: URL of the resource if known.
    url: typing.Optional[str] = None

    #: Line number in the resource.
    line_number: typing.Optional[int] = None

    #: JavaScript stack trace.
    stack_trace: typing.Optional[runtime.StackTrace] = None

    #: Identifier of the network request associated with this entry.
    network_request_id: typing.Optional[network.RequestId] = None

    #: Identifier of the worker associated with this entry.
    worker_id: typing.Optional[str] = None

    #: Call arguments.
    args: typing.Optional[typing.List[runtime.RemoteObject]] = None

    def to_json(self):
        json = dict()
        json['source'] = self.source
        json['level'] = self.level
        json['text'] = self.text
        json['timestamp'] = self.timestamp.to_json()
        if self.category is not None:
            json['category'] = self.category
        if self.url is not None:
            json['url'] = self.url
        if self.line_number is not None:
            json['lineNumber'] = self.line_number
        if self.stack_trace is not None:
            json['stackTrace'] = self.stack_trace.to_json()
        if self.network_request_id is not None:
            json['networkRequestId'] = self.network_request_id.to_json()
        if self.worker_id is not None:
            json['workerId'] = self.worker_id
        if self.args is not None:
            json['args'] = [i.to_json() for i in self.args]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source=str(json['source']),
            level=str(json['level']),
            text=str(json['text']),
            timestamp=runtime.Timestamp.from_json(json['timestamp']),
            category=str(json['category']) if 'category' in json else None,
            url=str(json['url']) if 'url' in json else None,
            line_number=int(json['lineNumber']) if 'lineNumber' in json else None,
            stack_trace=runtime.StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            network_request_id=network.RequestId.from_json(json['networkRequestId']) if 'networkRequestId' in json else None,
            worker_id=str(json['workerId']) if 'workerId' in json else None,
            args=[runtime.RemoteObject.from_json(i) for i in json['args']] if 'args' in json else None,
        )


@dataclass
class ViolationSetting:
    '''
    Violation configuration setting.
    '''
    #: Violation type.
    name: str

    #: Time threshold to trigger upon.
    threshold: float

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['threshold'] = self.threshold
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            threshold=float(json['threshold']),
        )


def clear() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears the log.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.clear',
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables log domain, prevents further log entries from being reported to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables log domain, sends the entries collected so far to the client by means of the
    ``entryAdded`` notification.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.enable',
    }
    json = yield cmd_dict


def start_violations_report(
        config: typing.List[ViolationSetting]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    start violation reporting.

    :param config: Configuration for violations.
    '''
    params: T_JSON_DICT = dict()
    params['config'] = [i.to_json() for i in config]
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.startViolationsReport',
        'params': params,
    }
    json = yield cmd_dict


def stop_violations_report() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stop violation reporting.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Log.stopViolationsReport',
    }
    json = yield cmd_dict


@event_class('Log.entryAdded')
@dataclass
class EntryAdded:
    '''
    Issued when new message was logged.
    '''
    #: The entry.
    entry: LogEntry

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> EntryAdded:
        return cls(
            entry=LogEntry.from_json(json['entry'])
        )

# === NexusCore/openenv\Lib\site-packages\win32comext\shell\demos\servers\empty_volume_cache.py ===
# A sample implementation of IEmptyVolumeCache - see
# https://learn.microsoft.com/en-ca/windows/win32/lwef/disk-cleanup for an overview.
#
# * Execute this script to register the handler
# * Start the "disk cleanup" tool - look for "pywin32 compiled files"
import os
import stat
import sys

import pythoncom
import win32gui
import winerror
from win32com.server.exception import COMException
from win32com.shell import shell, shellcon

# Our shell extension.
IEmptyVolumeCache_Methods = (
    "Initialize GetSpaceUsed Purge ShowProperties Deactivate".split()
)
IEmptyVolumeCache2_Methods = "InitializeEx".split()

ico = os.path.join(sys.prefix, "py.ico")
if not os.path.isfile(ico):
    ico = os.path.join(sys.prefix, "PC", "py.ico")
if not os.path.isfile(ico):
    ico = None
    print("Can't find python.ico - no icon will be installed")


class EmptyVolumeCache:
    _reg_progid_ = "Python.ShellExtension.EmptyVolumeCache"
    _reg_desc_ = "Python Sample Shell Extension (disk cleanup)"
    _reg_clsid_ = "{EADD0777-2968-4c72-A999-2BF5F756259C}"
    _reg_icon_ = ico
    _com_interfaces_ = [shell.IID_IEmptyVolumeCache, shell.IID_IEmptyVolumeCache2]
    _public_methods_ = IEmptyVolumeCache_Methods + IEmptyVolumeCache2_Methods

    def Initialize(self, hkey, volume, flags):
        # This should never be called, except on win98.
        print("Unless we are on 98, Initialize call is unexpected!")
        raise COMException(hresult=winerror.E_NOTIMPL)

    def InitializeEx(self, hkey, volume, key_name, flags):
        # Must return a tuple of:
        # (display_name, description, button_name, flags)
        print("InitializeEx called with", hkey, volume, key_name, flags)
        self.volume = volume
        if flags & shellcon.EVCF_SETTINGSMODE:
            print("We are being run on a schedule")
            # In this case, "because there is no opportunity for user
            # feedback, only those files that are extremely safe to clean up
            # should be touched. You should ignore the initialization
            # method's pcwszVolume parameter and clean unneeded files
            # regardless of what drive they are on."
            self.volume = None  # flag as 'any disk will do'
        elif flags & shellcon.EVCF_OUTOFDISKSPACE:
            # In this case, "the handler should be aggressive about deleting
            # files, even if it results in a performance loss. However, the
            # handler obviously should not delete files that would cause an
            # application to fail or the user to lose data."
            print("We are being run as we are out of disk-space")
        else:
            # This case is not documented - we are guessing :)
            print("We are being run because the user asked")

        # For the sake of demo etc, we tell the shell to only show us when
        # there are > 0 bytes available.  Our GetSpaceUsed will check the
        # volume, so will return 0 when we are on a different disk
        flags = shellcon.EVCF_DONTSHOWIFZERO | shellcon.EVCF_ENABLEBYDEFAULT

        return (
            "pywin32 compiled files",
            "Removes all .pyc and .pyo files in the pywin32 directories",
            "click me!",
            flags,
        )

    def _GetDirectories(self):
        root_dir = os.path.abspath(os.path.dirname(os.path.dirname(win32gui.__file__)))
        if self.volume is not None and not root_dir.lower().startswith(
            self.volume.lower()
        ):
            return []
        return [
            os.path.join(root_dir, p)
            for p in ("win32", "win32com", "win32comext", "isapi")
        ]

    def _WalkCallback(self, arg, directory, files):
        # callback function for os.path.walk - no need to be member, but it's
        # close to the callers :)
        callback, total_list = arg
        for file in files:
            fqn = os.path.join(directory, file).lower()
            if file.endswith(".pyc") or file.endswith(".pyo"):
                # See below - total_list is None means delete files,
                # otherwise it is a list where the result is stored. It's a
                # list simply due to the way os.walk works - only [0] is
                # referenced
                if total_list is None:
                    print("Deleting file", fqn)
                    # Should do callback.PurgeProcess - left as an exercise :)
                    os.remove(fqn)
                else:
                    total_list[0] += os.stat(fqn)[stat.ST_SIZE]
                    # and callback to the tool
                    if callback:
                        # for the sake of seeing the progress bar do its thing,
                        # we take longer than we need to...
                        # ACK - for some bizarre reason this screws up the XP
                        # cleanup manager - clues welcome!! :)
                        # # print("Looking in", directory, ", but waiting a while...")
                        # # time.sleep(3)
                        # now do it
                        used = total_list[0]
                        callback.ScanProgress(used, 0, "Looking at " + fqn)

    def GetSpaceUsed(self, callback):
        total = [0]  # See _WalkCallback above
        try:
            for d in self._GetDirectories():
                os.path.walk(d, self._WalkCallback, (callback, total))
                print("After looking in", d, "we have", total[0], "bytes")
        except pythoncom.error as exc:
            # This will be raised by the callback when the user selects 'cancel'.
            if exc.hresult != winerror.E_ABORT:
                raise  # that's the documented error code!
            print("User cancelled the operation")
        return total[0]

    def Purge(self, amt_to_free, callback):
        print("Purging", amt_to_free, "bytes...")
        # we ignore amt_to_free - it is generally what we returned for
        # GetSpaceUsed
        try:
            for d in self._GetDirectories():
                os.path.walk(d, self._WalkCallback, (callback, None))
        except pythoncom.error as exc:
            # This will be raised by the callback when the user selects 'cancel'.
            if exc.hresult != winerror.E_ABORT:
                raise  # that's the documented error code!
            print("User cancelled the operation")

    def ShowProperties(self, hwnd):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def Deactivate(self):
        print("Deactivate called")
        return 0


def DllRegisterServer():
    # Also need to register specially in:
    # HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches
    # See link at top of file.
    import winreg

    kn = r"Software\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches\{}".format(
        EmptyVolumeCache._reg_desc_,
    )
    key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, kn)
    winreg.SetValueEx(key, None, 0, winreg.REG_SZ, EmptyVolumeCache._reg_clsid_)


def DllUnregisterServer():
    import winreg

    kn = r"Software\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches\{}".format(
        EmptyVolumeCache._reg_desc_,
    )
    try:
        key = winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, kn)
    except OSError as details:
        import errno

        if details.errno != errno.ENOENT:
            raise
    print(EmptyVolumeCache._reg_desc_, "unregistration complete.")


if __name__ == "__main__":
    from win32com.server import register

    register.UseCommandLine(
        EmptyVolumeCache,
        finalize_register=DllRegisterServer,
        finalize_unregister=DllUnregisterServer,
    )

# === NexusCore/evaluation\evalplus\evalplus\eval\utils.py ===
# The MIT License
#
# Copyright (c) OpenAI (https://openai.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import contextlib
import faulthandler
import io
import os
import platform
import signal
import tempfile
from typing import Optional


@contextlib.contextmanager
def swallow_io():
    stream = WriteOnlyStringIO()
    with contextlib.redirect_stdout(stream):
        with contextlib.redirect_stderr(stream):
            with redirect_stdin(stream):
                yield


@contextlib.contextmanager
def time_limit(seconds: float):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")

    signal.setitimer(signal.ITIMER_REAL, seconds)
    signal.signal(signal.SIGALRM, signal_handler)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


@contextlib.contextmanager
def create_tempdir():
    with tempfile.TemporaryDirectory() as dirname:
        with chdir(dirname):
            yield dirname


@contextlib.contextmanager
def chdir(root):
    if root == ".":
        yield
        return
    cwd = os.getcwd()
    os.chdir(root)
    try:
        yield
    except BaseException as exc:
        raise exc
    finally:
        os.chdir(cwd)


class TimeoutException(Exception):
    pass


class WriteOnlyStringIO(io.StringIO):
    """StringIO that throws an exception when it's read from"""

    def read(self, *args, **kwargs):
        raise IOError

    def readline(self, *args, **kwargs):
        raise IOError

    def readlines(self, *args, **kwargs):
        raise IOError

    def readable(self, *args, **kwargs):
        """Returns True if the IO object can be read."""
        return False


class redirect_stdin(contextlib._RedirectStream):  # type: ignore
    _stream = "stdin"


def reliability_guard(maximum_memory_bytes: Optional[int] = None):
    """
    This disables various destructive functions and prevents the generated code
    from interfering with the test (e.g. fork bomb, killing other processes,
    removing filesystem files, etc.)

    WARNING
    This function is NOT a security sandbox. Untrusted code, including, model-
    generated code, should not be blindly executed outside of one. See the
    Codex paper for more information about OpenAI's code sandbox, and proceed
    with caution.
    """

    if maximum_memory_bytes is not None:
        import resource

        resource.setrlimit(
            resource.RLIMIT_AS, (maximum_memory_bytes, maximum_memory_bytes)
        )
        resource.setrlimit(
            resource.RLIMIT_DATA, (maximum_memory_bytes, maximum_memory_bytes)
        )
        if not platform.uname().system == "Darwin":
            resource.setrlimit(
                resource.RLIMIT_STACK, (maximum_memory_bytes, maximum_memory_bytes)
            )

    faulthandler.disable()

    import builtins

    builtins.exit = None
    builtins.quit = None

    import os

    os.environ["OMP_NUM_THREADS"] = "1"

    os.kill = None
    os.system = None
    os.putenv = None
    os.remove = None
    os.removedirs = None
    os.rmdir = None
    os.fchdir = None
    os.setuid = None
    os.fork = None
    os.forkpty = None
    os.killpg = None
    os.rename = None
    os.renames = None
    os.truncate = None
    os.replace = None
    os.unlink = None
    os.fchmod = None
    os.fchown = None
    os.chmod = None
    os.chown = None
    os.chroot = None
    os.fchdir = None
    os.lchflags = None
    os.lchmod = None
    os.lchown = None
    os.getcwd = None
    os.chdir = None
    builtins.open = None

    import shutil

    shutil.rmtree = None
    shutil.move = None
    shutil.chown = None

    import subprocess

    subprocess.Popen = None  # type: ignore

    __builtins__["help"] = None

    import sys

    sys.modules["ipdb"] = None
    sys.modules["joblib"] = None
    sys.modules["resource"] = None
    sys.modules["psutil"] = None
    sys.modules["tkinter"] = None

# === NexusCore/myenv\Lib\site-packages\pip\_internal\network\download.py ===
"""Download files with progress indicators.
"""

import email.message
import logging
import mimetypes
import os
from typing import Iterable, Optional, Tuple

from pip._vendor.requests.models import Response

from pip._internal.cli.progress_bars import get_download_progress_renderer
from pip._internal.exceptions import NetworkConnectionError
from pip._internal.models.index import PyPI
from pip._internal.models.link import Link
from pip._internal.network.cache import is_from_cache
from pip._internal.network.session import PipSession
from pip._internal.network.utils import HEADERS, raise_for_status, response_chunks
from pip._internal.utils.misc import format_size, redact_auth_from_url, splitext

logger = logging.getLogger(__name__)


def _get_http_response_size(resp: Response) -> Optional[int]:
    try:
        return int(resp.headers["content-length"])
    except (ValueError, KeyError, TypeError):
        return None


def _prepare_download(
    resp: Response,
    link: Link,
    progress_bar: str,
) -> Iterable[bytes]:
    total_length = _get_http_response_size(resp)

    if link.netloc == PyPI.file_storage_domain:
        url = link.show_url
    else:
        url = link.url_without_fragment

    logged_url = redact_auth_from_url(url)

    if total_length:
        logged_url = f"{logged_url} ({format_size(total_length)})"

    if is_from_cache(resp):
        logger.info("Using cached %s", logged_url)
    else:
        logger.info("Downloading %s", logged_url)

    if logger.getEffectiveLevel() > logging.INFO:
        show_progress = False
    elif is_from_cache(resp):
        show_progress = False
    elif not total_length:
        show_progress = True
    elif total_length > (512 * 1024):
        show_progress = True
    else:
        show_progress = False

    chunks = response_chunks(resp)

    if not show_progress:
        return chunks

    renderer = get_download_progress_renderer(bar_type=progress_bar, size=total_length)
    return renderer(chunks)


def sanitize_content_filename(filename: str) -> str:
    """
    Sanitize the "filename" value from a Content-Disposition header.
    """
    return os.path.basename(filename)


def parse_content_disposition(content_disposition: str, default_filename: str) -> str:
    """
    Parse the "filename" value from a Content-Disposition header, and
    return the default filename if the result is empty.
    """
    m = email.message.Message()
    m["content-type"] = content_disposition
    filename = m.get_param("filename")
    if filename:
        # We need to sanitize the filename to prevent directory traversal
        # in case the filename contains ".." path parts.
        filename = sanitize_content_filename(str(filename))
    return filename or default_filename


def _get_http_response_filename(resp: Response, link: Link) -> str:
    """Get an ideal filename from the given HTTP response, falling back to
    the link filename if not provided.
    """
    filename = link.filename  # fallback
    # Have a look at the Content-Disposition header for a better guess
    content_disposition = resp.headers.get("content-disposition")
    if content_disposition:
        filename = parse_content_disposition(content_disposition, filename)
    ext: Optional[str] = splitext(filename)[1]
    if not ext:
        ext = mimetypes.guess_extension(resp.headers.get("content-type", ""))
        if ext:
            filename += ext
    if not ext and link.url != resp.url:
        ext = os.path.splitext(resp.url)[1]
        if ext:
            filename += ext
    return filename


def _http_get_download(session: PipSession, link: Link) -> Response:
    target_url = link.url.split("#", 1)[0]
    resp = session.get(target_url, headers=HEADERS, stream=True)
    raise_for_status(resp)
    return resp


class Downloader:
    def __init__(
        self,
        session: PipSession,
        progress_bar: str,
    ) -> None:
        self._session = session
        self._progress_bar = progress_bar

    def __call__(self, link: Link, location: str) -> Tuple[str, str]:
        """Download the file given by link into location."""
        try:
            resp = _http_get_download(self._session, link)
        except NetworkConnectionError as e:
            assert e.response is not None
            logger.critical(
                "HTTP error %s while getting %s", e.response.status_code, link
            )
            raise

        filename = _get_http_response_filename(resp, link)
        filepath = os.path.join(location, filename)

        chunks = _prepare_download(resp, link, self._progress_bar)
        with open(filepath, "wb") as content_file:
            for chunk in chunks:
                content_file.write(chunk)
        content_type = resp.headers.get("Content-Type", "")
        return filepath, content_type


class BatchDownloader:
    def __init__(
        self,
        session: PipSession,
        progress_bar: str,
    ) -> None:
        self._session = session
        self._progress_bar = progress_bar

    def __call__(
        self, links: Iterable[Link], location: str
    ) -> Iterable[Tuple[Link, Tuple[str, str]]]:
        """Download the files given by links into location."""
        for link in links:
            try:
                resp = _http_get_download(self._session, link)
            except NetworkConnectionError as e:
                assert e.response is not None
                logger.critical(
                    "HTTP error %s while getting %s",
                    e.response.status_code,
                    link,
                )
                raise

            filename = _get_http_response_filename(resp, link)
            filepath = os.path.join(location, filename)

            chunks = _prepare_download(resp, link, self._progress_bar)
            with open(filepath, "wb") as content_file:
                for chunk in chunks:
                    content_file.write(chunk)
            content_type = resp.headers.get("Content-Type", "")
            yield link, (filepath, content_type)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\columns.py ===
from collections import defaultdict
from itertools import chain
from operator import itemgetter
from typing import Dict, Iterable, List, Optional, Tuple

from .align import Align, AlignMethod
from .console import Console, ConsoleOptions, RenderableType, RenderResult
from .constrain import Constrain
from .measure import Measurement
from .padding import Padding, PaddingDimensions
from .table import Table
from .text import TextType
from .jupyter import JupyterMixin


class Columns(JupyterMixin):
    """Display renderables in neat columns.

    Args:
        renderables (Iterable[RenderableType]): Any number of Rich renderables (including str).
        width (int, optional): The desired width of the columns, or None to auto detect. Defaults to None.
        padding (PaddingDimensions, optional): Optional padding around cells. Defaults to (0, 1).
        expand (bool, optional): Expand columns to full width. Defaults to False.
        equal (bool, optional): Arrange in to equal sized columns. Defaults to False.
        column_first (bool, optional): Align items from top to bottom (rather than left to right). Defaults to False.
        right_to_left (bool, optional): Start column from right hand side. Defaults to False.
        align (str, optional): Align value ("left", "right", or "center") or None for default. Defaults to None.
        title (TextType, optional): Optional title for Columns.
    """

    def __init__(
        self,
        renderables: Optional[Iterable[RenderableType]] = None,
        padding: PaddingDimensions = (0, 1),
        *,
        width: Optional[int] = None,
        expand: bool = False,
        equal: bool = False,
        column_first: bool = False,
        right_to_left: bool = False,
        align: Optional[AlignMethod] = None,
        title: Optional[TextType] = None,
    ) -> None:
        self.renderables = list(renderables or [])
        self.width = width
        self.padding = padding
        self.expand = expand
        self.equal = equal
        self.column_first = column_first
        self.right_to_left = right_to_left
        self.align: Optional[AlignMethod] = align
        self.title = title

    def add_renderable(self, renderable: RenderableType) -> None:
        """Add a renderable to the columns.

        Args:
            renderable (RenderableType): Any renderable object.
        """
        self.renderables.append(renderable)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        render_str = console.render_str
        renderables = [
            render_str(renderable) if isinstance(renderable, str) else renderable
            for renderable in self.renderables
        ]
        if not renderables:
            return
        _top, right, _bottom, left = Padding.unpack(self.padding)
        width_padding = max(left, right)
        max_width = options.max_width
        widths: Dict[int, int] = defaultdict(int)
        column_count = len(renderables)

        get_measurement = Measurement.get
        renderable_widths = [
            get_measurement(console, options, renderable).maximum
            for renderable in renderables
        ]
        if self.equal:
            renderable_widths = [max(renderable_widths)] * len(renderable_widths)

        def iter_renderables(
            column_count: int,
        ) -> Iterable[Tuple[int, Optional[RenderableType]]]:
            item_count = len(renderables)
            if self.column_first:
                width_renderables = list(zip(renderable_widths, renderables))

                column_lengths: List[int] = [item_count // column_count] * column_count
                for col_no in range(item_count % column_count):
                    column_lengths[col_no] += 1

                row_count = (item_count + column_count - 1) // column_count
                cells = [[-1] * column_count for _ in range(row_count)]
                row = col = 0
                for index in range(item_count):
                    cells[row][col] = index
                    column_lengths[col] -= 1
                    if column_lengths[col]:
                        row += 1
                    else:
                        col += 1
                        row = 0
                for index in chain.from_iterable(cells):
                    if index == -1:
                        break
                    yield width_renderables[index]
            else:
                yield from zip(renderable_widths, renderables)
            # Pad odd elements with spaces
            if item_count % column_count:
                for _ in range(column_count - (item_count % column_count)):
                    yield 0, None

        table = Table.grid(padding=self.padding, collapse_padding=True, pad_edge=False)
        table.expand = self.expand
        table.title = self.title

        if self.width is not None:
            column_count = (max_width) // (self.width + width_padding)
            for _ in range(column_count):
                table.add_column(width=self.width)
        else:
            while column_count > 1:
                widths.clear()
                column_no = 0
                for renderable_width, _ in iter_renderables(column_count):
                    widths[column_no] = max(widths[column_no], renderable_width)
                    total_width = sum(widths.values()) + width_padding * (
                        len(widths) - 1
                    )
                    if total_width > max_width:
                        column_count = len(widths) - 1
                        break
                    else:
                        column_no = (column_no + 1) % column_count
                else:
                    break

        get_renderable = itemgetter(1)
        _renderables = [
            get_renderable(_renderable)
            for _renderable in iter_renderables(column_count)
        ]
        if self.equal:
            _renderables = [
                None
                if renderable is None
                else Constrain(renderable, renderable_widths[0])
                for renderable in _renderables
            ]
        if self.align:
            align = self.align
            _Align = Align
            _renderables = [
                None if renderable is None else _Align(renderable, align)
                for renderable in _renderables
            ]

        right_to_left = self.right_to_left
        add_row = table.add_row
        for start in range(0, len(_renderables), column_count):
            row = _renderables[start : start + column_count]
            if right_to_left:
                row = row[::-1]
            add_row(*row)
        yield table


if __name__ == "__main__":  # pragma: no cover
    import os

    console = Console()

    files = [f"{i} {s}" for i, s in enumerate(sorted(os.listdir()))]
    columns = Columns(files, padding=(0, 1), expand=False, equal=False)
    console.print(columns)
    console.rule()
    columns.column_first = True
    console.print(columns)
    columns.right_to_left = True
    console.rule()
    console.print(columns)

# === NexusCore/openenv\Lib\site-packages\cffi\cffi_opcode.py ===
from .error import VerificationError

class CffiOp(object):
    def __init__(self, op, arg):
        self.op = op
        self.arg = arg

    def as_c_expr(self):
        if self.op is None:
            assert isinstance(self.arg, str)
            return '(_cffi_opcode_t)(%s)' % (self.arg,)
        classname = CLASS_NAME[self.op]
        return '_CFFI_OP(_CFFI_OP_%s, %s)' % (classname, self.arg)

    def as_python_bytes(self):
        if self.op is None and self.arg.isdigit():
            value = int(self.arg)     # non-negative: '-' not in self.arg
            if value >= 2**31:
                raise OverflowError("cannot emit %r: limited to 2**31-1"
                                    % (self.arg,))
            return format_four_bytes(value)
        if isinstance(self.arg, str):
            raise VerificationError("cannot emit to Python: %r" % (self.arg,))
        return format_four_bytes((self.arg << 8) | self.op)

    def __str__(self):
        classname = CLASS_NAME.get(self.op, self.op)
        return '(%s %s)' % (classname, self.arg)

def format_four_bytes(num):
    return '\\x%02X\\x%02X\\x%02X\\x%02X' % (
        (num >> 24) & 0xFF,
        (num >> 16) & 0xFF,
        (num >>  8) & 0xFF,
        (num      ) & 0xFF)

OP_PRIMITIVE       = 1
OP_POINTER         = 3
OP_ARRAY           = 5
OP_OPEN_ARRAY      = 7
OP_STRUCT_UNION    = 9
OP_ENUM            = 11
OP_FUNCTION        = 13
OP_FUNCTION_END    = 15
OP_NOOP            = 17
OP_BITFIELD        = 19
OP_TYPENAME        = 21
OP_CPYTHON_BLTN_V  = 23   # varargs
OP_CPYTHON_BLTN_N  = 25   # noargs
OP_CPYTHON_BLTN_O  = 27   # O  (i.e. a single arg)
OP_CONSTANT        = 29
OP_CONSTANT_INT    = 31
OP_GLOBAL_VAR      = 33
OP_DLOPEN_FUNC     = 35
OP_DLOPEN_CONST    = 37
OP_GLOBAL_VAR_F    = 39
OP_EXTERN_PYTHON   = 41

PRIM_VOID          = 0
PRIM_BOOL          = 1
PRIM_CHAR          = 2
PRIM_SCHAR         = 3
PRIM_UCHAR         = 4
PRIM_SHORT         = 5
PRIM_USHORT        = 6
PRIM_INT           = 7
PRIM_UINT          = 8
PRIM_LONG          = 9
PRIM_ULONG         = 10
PRIM_LONGLONG      = 11
PRIM_ULONGLONG     = 12
PRIM_FLOAT         = 13
PRIM_DOUBLE        = 14
PRIM_LONGDOUBLE    = 15

PRIM_WCHAR         = 16
PRIM_INT8          = 17
PRIM_UINT8         = 18
PRIM_INT16         = 19
PRIM_UINT16        = 20
PRIM_INT32         = 21
PRIM_UINT32        = 22
PRIM_INT64         = 23
PRIM_UINT64        = 24
PRIM_INTPTR        = 25
PRIM_UINTPTR       = 26
PRIM_PTRDIFF       = 27
PRIM_SIZE          = 28
PRIM_SSIZE         = 29
PRIM_INT_LEAST8    = 30
PRIM_UINT_LEAST8   = 31
PRIM_INT_LEAST16   = 32
PRIM_UINT_LEAST16  = 33
PRIM_INT_LEAST32   = 34
PRIM_UINT_LEAST32  = 35
PRIM_INT_LEAST64   = 36
PRIM_UINT_LEAST64  = 37
PRIM_INT_FAST8     = 38
PRIM_UINT_FAST8    = 39
PRIM_INT_FAST16    = 40
PRIM_UINT_FAST16   = 41
PRIM_INT_FAST32    = 42
PRIM_UINT_FAST32   = 43
PRIM_INT_FAST64    = 44
PRIM_UINT_FAST64   = 45
PRIM_INTMAX        = 46
PRIM_UINTMAX       = 47
PRIM_FLOATCOMPLEX  = 48
PRIM_DOUBLECOMPLEX = 49
PRIM_CHAR16        = 50
PRIM_CHAR32        = 51

_NUM_PRIM          = 52
_UNKNOWN_PRIM          = -1
_UNKNOWN_FLOAT_PRIM    = -2
_UNKNOWN_LONG_DOUBLE   = -3

_IO_FILE_STRUCT        = -1

PRIMITIVE_TO_INDEX = {
    'char':               PRIM_CHAR,
    'short':              PRIM_SHORT,
    'int':                PRIM_INT,
    'long':               PRIM_LONG,
    'long long':          PRIM_LONGLONG,
    'signed char':        PRIM_SCHAR,
    'unsigned char':      PRIM_UCHAR,
    'unsigned short':     PRIM_USHORT,
    'unsigned int':       PRIM_UINT,
    'unsigned long':      PRIM_ULONG,
    'unsigned long long': PRIM_ULONGLONG,
    'float':              PRIM_FLOAT,
    'double':             PRIM_DOUBLE,
    'long double':        PRIM_LONGDOUBLE,
    '_cffi_float_complex_t': PRIM_FLOATCOMPLEX,
    '_cffi_double_complex_t': PRIM_DOUBLECOMPLEX,
    '_Bool':              PRIM_BOOL,
    'wchar_t':            PRIM_WCHAR,
    'char16_t':           PRIM_CHAR16,
    'char32_t':           PRIM_CHAR32,
    'int8_t':             PRIM_INT8,
    'uint8_t':            PRIM_UINT8,
    'int16_t':            PRIM_INT16,
    'uint16_t':           PRIM_UINT16,
    'int32_t':            PRIM_INT32,
    'uint32_t':           PRIM_UINT32,
    'int64_t':            PRIM_INT64,
    'uint64_t':           PRIM_UINT64,
    'intptr_t':           PRIM_INTPTR,
    'uintptr_t':          PRIM_UINTPTR,
    'ptrdiff_t':          PRIM_PTRDIFF,
    'size_t':             PRIM_SIZE,
    'ssize_t':            PRIM_SSIZE,
    'int_least8_t':       PRIM_INT_LEAST8,
    'uint_least8_t':      PRIM_UINT_LEAST8,
    'int_least16_t':      PRIM_INT_LEAST16,
    'uint_least16_t':     PRIM_UINT_LEAST16,
    'int_least32_t':      PRIM_INT_LEAST32,
    'uint_least32_t':     PRIM_UINT_LEAST32,
    'int_least64_t':      PRIM_INT_LEAST64,
    'uint_least64_t':     PRIM_UINT_LEAST64,
    'int_fast8_t':        PRIM_INT_FAST8,
    'uint_fast8_t':       PRIM_UINT_FAST8,
    'int_fast16_t':       PRIM_INT_FAST16,
    'uint_fast16_t':      PRIM_UINT_FAST16,
    'int_fast32_t':       PRIM_INT_FAST32,
    'uint_fast32_t':      PRIM_UINT_FAST32,
    'int_fast64_t':       PRIM_INT_FAST64,
    'uint_fast64_t':      PRIM_UINT_FAST64,
    'intmax_t':           PRIM_INTMAX,
    'uintmax_t':          PRIM_UINTMAX,
    }

F_UNION         = 0x01
F_CHECK_FIELDS  = 0x02
F_PACKED        = 0x04
F_EXTERNAL      = 0x08
F_OPAQUE        = 0x10

G_FLAGS = dict([('_CFFI_' + _key, globals()[_key])
                for _key in ['F_UNION', 'F_CHECK_FIELDS', 'F_PACKED',
                             'F_EXTERNAL', 'F_OPAQUE']])

CLASS_NAME = {}
for _name, _value in list(globals().items()):
    if _name.startswith('OP_') and isinstance(_value, int):
        CLASS_NAME[_value] = _name[3:]

# === NexusCore/openenv\Lib\site-packages\rich\columns.py ===
from collections import defaultdict
from itertools import chain
from operator import itemgetter
from typing import Dict, Iterable, List, Optional, Tuple

from .align import Align, AlignMethod
from .console import Console, ConsoleOptions, RenderableType, RenderResult
from .constrain import Constrain
from .measure import Measurement
from .padding import Padding, PaddingDimensions
from .table import Table
from .text import TextType
from .jupyter import JupyterMixin


class Columns(JupyterMixin):
    """Display renderables in neat columns.

    Args:
        renderables (Iterable[RenderableType]): Any number of Rich renderables (including str).
        width (int, optional): The desired width of the columns, or None to auto detect. Defaults to None.
        padding (PaddingDimensions, optional): Optional padding around cells. Defaults to (0, 1).
        expand (bool, optional): Expand columns to full width. Defaults to False.
        equal (bool, optional): Arrange in to equal sized columns. Defaults to False.
        column_first (bool, optional): Align items from top to bottom (rather than left to right). Defaults to False.
        right_to_left (bool, optional): Start column from right hand side. Defaults to False.
        align (str, optional): Align value ("left", "right", or "center") or None for default. Defaults to None.
        title (TextType, optional): Optional title for Columns.
    """

    def __init__(
        self,
        renderables: Optional[Iterable[RenderableType]] = None,
        padding: PaddingDimensions = (0, 1),
        *,
        width: Optional[int] = None,
        expand: bool = False,
        equal: bool = False,
        column_first: bool = False,
        right_to_left: bool = False,
        align: Optional[AlignMethod] = None,
        title: Optional[TextType] = None,
    ) -> None:
        self.renderables = list(renderables or [])
        self.width = width
        self.padding = padding
        self.expand = expand
        self.equal = equal
        self.column_first = column_first
        self.right_to_left = right_to_left
        self.align: Optional[AlignMethod] = align
        self.title = title

    def add_renderable(self, renderable: RenderableType) -> None:
        """Add a renderable to the columns.

        Args:
            renderable (RenderableType): Any renderable object.
        """
        self.renderables.append(renderable)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        render_str = console.render_str
        renderables = [
            render_str(renderable) if isinstance(renderable, str) else renderable
            for renderable in self.renderables
        ]
        if not renderables:
            return
        _top, right, _bottom, left = Padding.unpack(self.padding)
        width_padding = max(left, right)
        max_width = options.max_width
        widths: Dict[int, int] = defaultdict(int)
        column_count = len(renderables)

        get_measurement = Measurement.get
        renderable_widths = [
            get_measurement(console, options, renderable).maximum
            for renderable in renderables
        ]
        if self.equal:
            renderable_widths = [max(renderable_widths)] * len(renderable_widths)

        def iter_renderables(
            column_count: int,
        ) -> Iterable[Tuple[int, Optional[RenderableType]]]:
            item_count = len(renderables)
            if self.column_first:
                width_renderables = list(zip(renderable_widths, renderables))

                column_lengths: List[int] = [item_count // column_count] * column_count
                for col_no in range(item_count % column_count):
                    column_lengths[col_no] += 1

                row_count = (item_count + column_count - 1) // column_count
                cells = [[-1] * column_count for _ in range(row_count)]
                row = col = 0
                for index in range(item_count):
                    cells[row][col] = index
                    column_lengths[col] -= 1
                    if column_lengths[col]:
                        row += 1
                    else:
                        col += 1
                        row = 0
                for index in chain.from_iterable(cells):
                    if index == -1:
                        break
                    yield width_renderables[index]
            else:
                yield from zip(renderable_widths, renderables)
            # Pad odd elements with spaces
            if item_count % column_count:
                for _ in range(column_count - (item_count % column_count)):
                    yield 0, None

        table = Table.grid(padding=self.padding, collapse_padding=True, pad_edge=False)
        table.expand = self.expand
        table.title = self.title

        if self.width is not None:
            column_count = (max_width) // (self.width + width_padding)
            for _ in range(column_count):
                table.add_column(width=self.width)
        else:
            while column_count > 1:
                widths.clear()
                column_no = 0
                for renderable_width, _ in iter_renderables(column_count):
                    widths[column_no] = max(widths[column_no], renderable_width)
                    total_width = sum(widths.values()) + width_padding * (
                        len(widths) - 1
                    )
                    if total_width > max_width:
                        column_count = len(widths) - 1
                        break
                    else:
                        column_no = (column_no + 1) % column_count
                else:
                    break

        get_renderable = itemgetter(1)
        _renderables = [
            get_renderable(_renderable)
            for _renderable in iter_renderables(column_count)
        ]
        if self.equal:
            _renderables = [
                None
                if renderable is None
                else Constrain(renderable, renderable_widths[0])
                for renderable in _renderables
            ]
        if self.align:
            align = self.align
            _Align = Align
            _renderables = [
                None if renderable is None else _Align(renderable, align)
                for renderable in _renderables
            ]

        right_to_left = self.right_to_left
        add_row = table.add_row
        for start in range(0, len(_renderables), column_count):
            row = _renderables[start : start + column_count]
            if right_to_left:
                row = row[::-1]
            add_row(*row)
        yield table


if __name__ == "__main__":  # pragma: no cover
    import os

    console = Console()

    files = [f"{i} {s}" for i, s in enumerate(sorted(os.listdir()))]
    columns = Columns(files, padding=(0, 1), expand=False, equal=False)
    console.print(columns)
    console.rule()
    columns.column_first = True
    console.print(columns)
    columns.right_to_left = True
    console.rule()
    console.print(columns)

# === NexusCore/openenv\Lib\site-packages\httpx\_transports\asgi.py ===
from __future__ import annotations

import typing

from .._models import Request, Response
from .._types import AsyncByteStream
from .base import AsyncBaseTransport

if typing.TYPE_CHECKING:  # pragma: no cover
    import asyncio

    import trio

    Event = typing.Union[asyncio.Event, trio.Event]


_Message = typing.MutableMapping[str, typing.Any]
_Receive = typing.Callable[[], typing.Awaitable[_Message]]
_Send = typing.Callable[
    [typing.MutableMapping[str, typing.Any]], typing.Awaitable[None]
]
_ASGIApp = typing.Callable[
    [typing.MutableMapping[str, typing.Any], _Receive, _Send], typing.Awaitable[None]
]

__all__ = ["ASGITransport"]


def is_running_trio() -> bool:
    try:
        # sniffio is a dependency of trio.

        # See https://github.com/python-trio/trio/issues/2802
        import sniffio

        if sniffio.current_async_library() == "trio":
            return True
    except ImportError:  # pragma: nocover
        pass

    return False


def create_event() -> Event:
    if is_running_trio():
        import trio

        return trio.Event()

    import asyncio

    return asyncio.Event()


class ASGIResponseStream(AsyncByteStream):
    def __init__(self, body: list[bytes]) -> None:
        self._body = body

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield b"".join(self._body)


class ASGITransport(AsyncBaseTransport):
    """
    A custom AsyncTransport that handles sending requests directly to an ASGI app.

    ```python
    transport = httpx.ASGITransport(
        app=app,
        root_path="/submount",
        client=("1.2.3.4", 123)
    )
    client = httpx.AsyncClient(transport=transport)
    ```

    Arguments:

    * `app` - The ASGI application.
    * `raise_app_exceptions` - Boolean indicating if exceptions in the application
       should be raised. Default to `True`. Can be set to `False` for use cases
       such as testing the content of a client 500 response.
    * `root_path` - The root path on which the ASGI application should be mounted.
    * `client` - A two-tuple indicating the client IP and port of incoming requests.
    ```
    """

    def __init__(
        self,
        app: _ASGIApp,
        raise_app_exceptions: bool = True,
        root_path: str = "",
        client: tuple[str, int] = ("127.0.0.1", 123),
    ) -> None:
        self.app = app
        self.raise_app_exceptions = raise_app_exceptions
        self.root_path = root_path
        self.client = client

    async def handle_async_request(
        self,
        request: Request,
    ) -> Response:
        assert isinstance(request.stream, AsyncByteStream)

        # ASGI scope.
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": request.method,
            "headers": [(k.lower(), v) for (k, v) in request.headers.raw],
            "scheme": request.url.scheme,
            "path": request.url.path,
            "raw_path": request.url.raw_path.split(b"?")[0],
            "query_string": request.url.query,
            "server": (request.url.host, request.url.port),
            "client": self.client,
            "root_path": self.root_path,
        }

        # Request.
        request_body_chunks = request.stream.__aiter__()
        request_complete = False

        # Response.
        status_code = None
        response_headers = None
        body_parts = []
        response_started = False
        response_complete = create_event()

        # ASGI callables.

        async def receive() -> dict[str, typing.Any]:
            nonlocal request_complete

            if request_complete:
                await response_complete.wait()
                return {"type": "http.disconnect"}

            try:
                body = await request_body_chunks.__anext__()
            except StopAsyncIteration:
                request_complete = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.request", "body": body, "more_body": True}

        async def send(message: typing.MutableMapping[str, typing.Any]) -> None:
            nonlocal status_code, response_headers, response_started

            if message["type"] == "http.response.start":
                assert not response_started

                status_code = message["status"]
                response_headers = message.get("headers", [])
                response_started = True

            elif message["type"] == "http.response.body":
                assert not response_complete.is_set()
                body = message.get("body", b"")
                more_body = message.get("more_body", False)

                if body and request.method != "HEAD":
                    body_parts.append(body)

                if not more_body:
                    response_complete.set()

        try:
            await self.app(scope, receive, send)
        except Exception:  # noqa: PIE-786
            if self.raise_app_exceptions:
                raise

            response_complete.set()
            if status_code is None:
                status_code = 500
            if response_headers is None:
                response_headers = {}

        assert response_complete.is_set()
        assert status_code is not None
        assert response_headers is not None

        stream = ASGIResponseStream(body_parts)

        return Response(status_code, headers=response_headers, stream=stream)

# === NexusCore/openenv\Lib\site-packages\IPython\testing\ipunittest.py ===
"""Experimental code for cleaner support of IPython syntax with unittest.

In IPython up until 0.10, we've used very hacked up nose machinery for running
tests with IPython special syntax, and this has proved to be extremely slow.
This module provides decorators to try a different approach, stemming from a
conversation Brian and I (FP) had about this problem Sept/09.

The goal is to be able to easily write simple functions that can be seen by
unittest as tests, and ultimately for these to support doctests with full
IPython syntax.  Nose already offers this based on naming conventions and our
hackish plugins, but we are seeking to move away from nose dependencies if
possible.

This module follows a different approach, based on decorators.

- A decorator called @ipdoctest can mark any function as having a docstring
  that should be viewed as a doctest, but after syntax conversion.

Authors
-------

- Fernando Perez <Fernando.Perez@berkeley.edu>
"""


#-----------------------------------------------------------------------------
#  Copyright (C) 2009-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib
import re
import sys
import unittest
import builtins
from doctest import DocTestFinder, DocTestRunner, TestResults
from IPython.terminal.interactiveshell import InteractiveShell

#-----------------------------------------------------------------------------
# Classes and functions
#-----------------------------------------------------------------------------

def count_failures(runner):
    """Count number of failures in a doctest runner.

    Code modeled after the summarize() method in doctest.
    """
    if sys.version_info < (3, 13):
        return [TestResults(f, t) for f, t in runner._name2ft.values() if f > 0]
    else:
        return [
            TestResults(failure, try_)
            for failure, try_, skip in runner._stats.values()
            if failure > 0
        ]


class IPython2PythonConverter:
    """Convert IPython 'syntax' to valid Python.

    Eventually this code may grow to be the full IPython syntax conversion
    implementation, but for now it only does prompt conversion."""
    
    def __init__(self):
        self.rps1 = re.compile(r'In\ \[\d+\]: ')
        self.rps2 = re.compile(r'\ \ \ \.\.\.+: ')
        self.rout = re.compile(r'Out\[\d+\]: \s*?\n?')
        self.pyps1 = '>>> '
        self.pyps2 = '... '
        self.rpyps1 = re.compile (r'(\s*%s)(.*)$' % self.pyps1)
        self.rpyps2 = re.compile (r'(\s*%s)(.*)$' % self.pyps2)

    def __call__(self, ds):
        """Convert IPython prompts to python ones in a string."""
        from . import globalipapp

        pyps1 = '>>> '
        pyps2 = '... '
        pyout = ''

        dnew = ds
        dnew = self.rps1.sub(pyps1, dnew)
        dnew = self.rps2.sub(pyps2, dnew)
        dnew = self.rout.sub(pyout, dnew)
        ip = InteractiveShell.instance()

        # Convert input IPython source into valid Python.
        out = []
        newline = out.append
        for line in dnew.splitlines():

            mps1 = self.rpyps1.match(line)
            if mps1 is not None:
                prompt, text = mps1.groups()
                newline(prompt+ip.prefilter(text, False))
                continue

            mps2 = self.rpyps2.match(line)
            if mps2 is not None:
                prompt, text = mps2.groups()
                newline(prompt+ip.prefilter(text, True))
                continue
            
            newline(line)
        newline('')  # ensure a closing newline, needed by doctest
        # print("PYSRC:", '\n'.join(out))  # dbg
        return '\n'.join(out)

    #return dnew


class Doc2UnitTester:
    """Class whose instances act as a decorator for docstring testing.

    In practice we're only likely to need one instance ever, made below (though
    no attempt is made at turning it into a singleton, there is no need for
    that).
    """
    def __init__(self, verbose=False):
        """New decorator.

        Parameters
        ----------

        verbose : boolean, optional (False)
          Passed to the doctest finder and runner to control verbosity.
        """
        self.verbose = verbose
        # We can reuse the same finder for all instances
        self.finder = DocTestFinder(verbose=verbose, recurse=False)

    def __call__(self, func):
        """Use as a decorator: doctest a function's docstring as a unittest.
        
        This version runs normal doctests, but the idea is to make it later run
        ipython syntax instead."""

        # Capture the enclosing instance with a different name, so the new
        # class below can see it without confusion regarding its own 'self'
        # that will point to the test instance at runtime
        d2u = self

        # Rewrite the function's docstring to have python syntax
        if func.__doc__ is not None:
            func.__doc__ = ip2py(func.__doc__)

        # Now, create a tester object that is a real unittest instance, so
        # normal unittest machinery (or Nose, or Trial) can find it.
        class Tester(unittest.TestCase):
            def test(self):
                # Make a new runner per function to be tested
                runner = DocTestRunner(verbose=d2u.verbose)
                for the_test in d2u.finder.find(func, func.__name__):
                    runner.run(the_test)
                failed = count_failures(runner)
                if failed:
                    # Since we only looked at a single function's docstring,
                    # failed should contain at most one item.  More than that
                    # is a case we can't handle and should error out on
                    if len(failed) > 1:
                        err = "Invalid number of test results: %s" % failed
                        raise ValueError(err)
                    # Report a normal failure.
                    self.fail('failed doctests: %s' % str(failed[0]))
                    
        # Rename it so test reports have the original signature.
        Tester.__name__ = func.__name__
        return Tester


def ipdocstring(func):
    """Change the function docstring via ip2py.
    """
    if func.__doc__ is not None:
        func.__doc__ = ip2py(func.__doc__)
    return func

        
# Make an instance of the classes for public use
ipdoctest = Doc2UnitTester()
ip2py = IPython2PythonConverter()

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\auth\rds_iam_token.py ===
import os
from typing import Any, Optional, Union

import httpx


def init_rds_client(
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    aws_region_name: Optional[str] = None,
    aws_session_name: Optional[str] = None,
    aws_profile_name: Optional[str] = None,
    aws_role_name: Optional[str] = None,
    aws_web_identity_token: Optional[str] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
):
    from litellm.secret_managers.main import get_secret

    # check for custom AWS_REGION_NAME and use it if not passed to init_bedrock_client
    litellm_aws_region_name = get_secret("AWS_REGION_NAME", None)
    standard_aws_region_name = get_secret("AWS_REGION", None)
    ## CHECK IS  'os.environ/' passed in
    # Define the list of parameters to check
    params_to_check = [
        aws_access_key_id,
        aws_secret_access_key,
        aws_region_name,
        aws_session_name,
        aws_profile_name,
        aws_role_name,
        aws_web_identity_token,
    ]

    # Iterate over parameters and update if needed
    for i, param in enumerate(params_to_check):
        if param and param.startswith("os.environ/"):
            params_to_check[i] = get_secret(param)  # type: ignore
    # Assign updated values back to parameters
    (
        aws_access_key_id,
        aws_secret_access_key,
        aws_region_name,
        aws_session_name,
        aws_profile_name,
        aws_role_name,
        aws_web_identity_token,
    ) = params_to_check

    ### SET REGION NAME
    region_name = aws_region_name
    if aws_region_name:
        region_name = aws_region_name
    elif litellm_aws_region_name:
        region_name = litellm_aws_region_name
    elif standard_aws_region_name:
        region_name = standard_aws_region_name
    else:
        raise Exception(
            "AWS region not set: set AWS_REGION_NAME or AWS_REGION env variable or in .env file",
        )

    import boto3

    if isinstance(timeout, float):
        config = boto3.session.Config(connect_timeout=timeout, read_timeout=timeout)  # type: ignore
    elif isinstance(timeout, httpx.Timeout):
        config = boto3.session.Config(  # type: ignore
            connect_timeout=timeout.connect, read_timeout=timeout.read
        )
    else:
        config = boto3.session.Config()  # type: ignore

    ### CHECK STS ###
    if (
        aws_web_identity_token is not None
        and aws_role_name is not None
        and aws_session_name is not None
    ):
        try:
            oidc_token = open(aws_web_identity_token).read()  # check if filepath
        except Exception:
            oidc_token = get_secret(aws_web_identity_token)

        if oidc_token is None:
            raise Exception(
                "OIDC token could not be retrieved from secret manager.",
            )

        sts_client = boto3.client("sts")

        # https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRoleWithWebIdentity.html
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts/client/assume_role_with_web_identity.html
        sts_response = sts_client.assume_role_with_web_identity(
            RoleArn=aws_role_name,
            RoleSessionName=aws_session_name,
            WebIdentityToken=oidc_token,
            DurationSeconds=3600,
        )

        client = boto3.client(
            service_name="rds",
            aws_access_key_id=sts_response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=sts_response["Credentials"]["SecretAccessKey"],
            aws_session_token=sts_response["Credentials"]["SessionToken"],
            region_name=region_name,
            config=config,
        )

    elif aws_role_name is not None and aws_session_name is not None:
        # use sts if role name passed in
        sts_client = boto3.client(
            "sts",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

        sts_response = sts_client.assume_role(
            RoleArn=aws_role_name, RoleSessionName=aws_session_name
        )

        client = boto3.client(
            service_name="rds",
            aws_access_key_id=sts_response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=sts_response["Credentials"]["SecretAccessKey"],
            aws_session_token=sts_response["Credentials"]["SessionToken"],
            region_name=region_name,
            config=config,
        )
    elif aws_access_key_id is not None:
        # uses auth params passed to completion
        # aws_access_key_id is not None, assume user is trying to auth using litellm.completion

        client = boto3.client(
            service_name="rds",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
            config=config,
        )
    elif aws_profile_name is not None:
        # uses auth values from AWS profile usually stored in ~/.aws/credentials

        client = boto3.Session(profile_name=aws_profile_name).client(
            service_name="rds",
            region_name=region_name,
            config=config,
        )

    else:
        # aws_access_key_id is None, assume user is trying to auth using env variables
        # boto3 automatically reads env variables

        client = boto3.client(
            service_name="rds",
            region_name=region_name,
            config=config,
        )

    return client


def generate_iam_auth_token(
    db_host, db_port, db_user, client: Optional[Any] = None
) -> str:
    from urllib.parse import quote

    if client is None:
        boto_client = init_rds_client(
            aws_region_name=os.getenv("AWS_REGION_NAME"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_name=os.getenv("AWS_SESSION_NAME"),
            aws_profile_name=os.getenv("AWS_PROFILE_NAME"),
            aws_role_name=os.getenv("AWS_ROLE_NAME", os.getenv("AWS_ROLE_ARN")),
            aws_web_identity_token=os.getenv(
                "AWS_WEB_IDENTITY_TOKEN", os.getenv("AWS_WEB_IDENTITY_TOKEN_FILE")
            ),
        )
    else:
        boto_client = client

    token = boto_client.generate_db_auth_token(
        DBHostname=db_host, Port=db_port, DBUsername=db_user
    )
    cleaned_token = quote(token, safe="")

    return cleaned_token

# === NexusCore/openenv\Lib\site-packages\nltk\tag\__init__.py ===
# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com> (minor additions)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
NLTK Taggers

This package contains classes and interfaces for part-of-speech
tagging, or simply "tagging".

A "tag" is a case-sensitive string that specifies some property of a token,
such as its part of speech.  Tagged tokens are encoded as tuples
``(tag, token)``.  For example, the following tagged token combines
the word ``'fly'`` with a noun part of speech tag (``'NN'``):

    >>> tagged_tok = ('fly', 'NN')

An off-the-shelf tagger is available for English. It uses the Penn Treebank tagset:

    >>> from nltk import pos_tag, word_tokenize
    >>> pos_tag(word_tokenize("John's big idea isn't all that bad.")) # doctest: +NORMALIZE_WHITESPACE
    [('John', 'NNP'), ("'s", 'POS'), ('big', 'JJ'), ('idea', 'NN'), ('is', 'VBZ'),
    ("n't", 'RB'), ('all', 'PDT'), ('that', 'DT'), ('bad', 'JJ'), ('.', '.')]

A Russian tagger is also available if you specify lang="rus". It uses
the Russian National Corpus tagset:

    >>> pos_tag(word_tokenize("Илья оторопел и дважды перечитал бумажку."), lang='rus')    # doctest: +SKIP
    [('Илья', 'S'), ('оторопел', 'V'), ('и', 'CONJ'), ('дважды', 'ADV'), ('перечитал', 'V'),
    ('бумажку', 'S'), ('.', 'NONLEX')]

This package defines several taggers, which take a list of tokens,
assign a tag to each one, and return the resulting list of tagged tokens.
Most of the taggers are built automatically based on a training corpus.
For example, the unigram tagger tags each word *w* by checking what
the most frequent tag for *w* was in a training corpus:

    >>> from nltk.corpus import brown
    >>> from nltk.tag import UnigramTagger
    >>> tagger = UnigramTagger(brown.tagged_sents(categories='news')[:500])
    >>> sent = ['Mitchell', 'decried', 'the', 'high', 'rate', 'of', 'unemployment']
    >>> for word, tag in tagger.tag(sent):
    ...     print(word, '->', tag)
    Mitchell -> NP
    decried -> None
    the -> AT
    high -> JJ
    rate -> NN
    of -> IN
    unemployment -> None

Note that words that the tagger has not seen during training receive a tag
of ``None``.

We evaluate a tagger on data that was not seen during training:

    >>> round(tagger.accuracy(brown.tagged_sents(categories='news')[500:600]), 3)
    0.735

For more information, please consult chapter 5 of the NLTK Book.

isort:skip_file
"""

import functools

from nltk.tag.api import TaggerI
from nltk.tag.util import str2tuple, tuple2str, untag
from nltk.tag.sequential import (
    SequentialBackoffTagger,
    ContextTagger,
    DefaultTagger,
    NgramTagger,
    UnigramTagger,
    BigramTagger,
    TrigramTagger,
    AffixTagger,
    RegexpTagger,
    ClassifierBasedTagger,
    ClassifierBasedPOSTagger,
)
from nltk.tag.brill import BrillTagger
from nltk.tag.brill_trainer import BrillTaggerTrainer
from nltk.tag.tnt import TnT
from nltk.tag.hunpos import HunposTagger
from nltk.tag.stanford import StanfordTagger, StanfordPOSTagger, StanfordNERTagger
from nltk.tag.hmm import HiddenMarkovModelTagger, HiddenMarkovModelTrainer
from nltk.tag.senna import SennaTagger, SennaChunkTagger, SennaNERTagger
from nltk.tag.mapping import tagset_mapping, map_tag
from nltk.tag.crf import CRFTagger
from nltk.tag.perceptron import PerceptronTagger

from nltk.data import load, find


PRETRAINED_TAGGERS = {
    "rus": "taggers/averaged_perceptron_tagger_rus/",
    "eng": "taggers/averaged_perceptron_tagger_eng/",
}


@functools.lru_cache
def _get_tagger(lang=None):
    if lang == "rus":
        tagger = PerceptronTagger(lang=lang)
    else:
        tagger = PerceptronTagger()
    return tagger


def _pos_tag(tokens, tagset=None, tagger=None, lang=None):
    # Currently only supports English and Russian.
    if lang not in ["eng", "rus"]:
        raise NotImplementedError(
            "Currently, NLTK pos_tag only supports English and Russian "
            "(i.e. lang='eng' or lang='rus')"
        )
    # Throws Error if tokens is of string type
    elif isinstance(tokens, str):
        raise TypeError("tokens: expected a list of strings, got a string")

    else:
        tagged_tokens = tagger.tag(tokens)
        if tagset:  # Maps to the specified tagset.
            if lang == "eng":
                tagged_tokens = [
                    (token, map_tag("en-ptb", tagset, tag))
                    for (token, tag) in tagged_tokens
                ]
            elif lang == "rus":
                # Note that the new Russian pos tags from the model contains suffixes,
                # see https://github.com/nltk/nltk/issues/2151#issuecomment-430709018
                tagged_tokens = [
                    (token, map_tag("ru-rnc-new", tagset, tag.partition("=")[0]))
                    for (token, tag) in tagged_tokens
                ]
        return tagged_tokens


def pos_tag(tokens, tagset=None, lang="eng"):
    """
    Use NLTK's currently recommended part of speech tagger to
    tag the given list of tokens.

        >>> from nltk.tag import pos_tag
        >>> from nltk.tokenize import word_tokenize
        >>> pos_tag(word_tokenize("John's big idea isn't all that bad.")) # doctest: +NORMALIZE_WHITESPACE
        [('John', 'NNP'), ("'s", 'POS'), ('big', 'JJ'), ('idea', 'NN'), ('is', 'VBZ'),
        ("n't", 'RB'), ('all', 'PDT'), ('that', 'DT'), ('bad', 'JJ'), ('.', '.')]
        >>> pos_tag(word_tokenize("John's big idea isn't all that bad."), tagset='universal') # doctest: +NORMALIZE_WHITESPACE
        [('John', 'NOUN'), ("'s", 'PRT'), ('big', 'ADJ'), ('idea', 'NOUN'), ('is', 'VERB'),
        ("n't", 'ADV'), ('all', 'DET'), ('that', 'DET'), ('bad', 'ADJ'), ('.', '.')]

    NB. Use `pos_tag_sents()` for efficient tagging of more than one sentence.

    :param tokens: Sequence of tokens to be tagged
    :type tokens: list(str)
    :param tagset: the tagset to be used, e.g. universal, wsj, brown
    :type tagset: str
    :param lang: the ISO 639 code of the language, e.g. 'eng' for English, 'rus' for Russian
    :type lang: str
    :return: The tagged tokens
    :rtype: list(tuple(str, str))
    """
    tagger = _get_tagger(lang)
    return _pos_tag(tokens, tagset, tagger, lang)


def pos_tag_sents(sentences, tagset=None, lang="eng"):
    """
    Use NLTK's currently recommended part of speech tagger to tag the
    given list of sentences, each consisting of a list of tokens.

    :param sentences: List of sentences to be tagged
    :type sentences: list(list(str))
    :param tagset: the tagset to be used, e.g. universal, wsj, brown
    :type tagset: str
    :param lang: the ISO 639 code of the language, e.g. 'eng' for English, 'rus' for Russian
    :type lang: str
    :return: The list of tagged sentences
    :rtype: list(list(tuple(str, str)))
    """
    tagger = _get_tagger(lang)
    return [_pos_tag(sent, tagset, tagger, lang) for sent in sentences]

# === NexusCore/openenv\Lib\site-packages\numpy\polynomial\__init__.py ===
"""
A sub-package for efficiently dealing with polynomials.

Within the documentation for this sub-package, a "finite power series,"
i.e., a polynomial (also referred to simply as a "series") is represented
by a 1-D numpy array of the polynomial's coefficients, ordered from lowest
order term to highest.  For example, array([1,2,3]) represents
``P_0 + 2*P_1 + 3*P_2``, where P_n is the n-th order basis polynomial
applicable to the specific module in question, e.g., `polynomial` (which
"wraps" the "standard" basis) or `chebyshev`.  For optimal performance,
all operations on polynomials, including evaluation at an argument, are
implemented as operations on the coefficients.  Additional (module-specific)
information can be found in the docstring for the module of interest.

This package provides *convenience classes* for each of six different kinds
of polynomials:

========================    ================
**Name**                    **Provides**
========================    ================
`~polynomial.Polynomial`    Power series
`~chebyshev.Chebyshev`      Chebyshev series
`~legendre.Legendre`        Legendre series
`~laguerre.Laguerre`        Laguerre series
`~hermite.Hermite`          Hermite series
`~hermite_e.HermiteE`       HermiteE series
========================    ================

These *convenience classes* provide a consistent interface for creating,
manipulating, and fitting data with polynomials of different bases.
The convenience classes are the preferred interface for the `~numpy.polynomial`
package, and are available from the ``numpy.polynomial`` namespace.
This eliminates the need to navigate to the corresponding submodules, e.g.
``np.polynomial.Polynomial`` or ``np.polynomial.Chebyshev`` instead of
``np.polynomial.polynomial.Polynomial`` or
``np.polynomial.chebyshev.Chebyshev``, respectively.
The classes provide a more consistent and concise interface than the
type-specific functions defined in the submodules for each type of polynomial.
For example, to fit a Chebyshev polynomial with degree ``1`` to data given
by arrays ``xdata`` and ``ydata``, the
`~chebyshev.Chebyshev.fit` class method::

    >>> from numpy.polynomial import Chebyshev
    >>> xdata = [1, 2, 3, 4]
    >>> ydata = [1, 4, 9, 16]
    >>> c = Chebyshev.fit(xdata, ydata, deg=1)

is preferred over the `chebyshev.chebfit` function from the
``np.polynomial.chebyshev`` module::

    >>> from numpy.polynomial.chebyshev import chebfit
    >>> c = chebfit(xdata, ydata, deg=1)

See :doc:`routines.polynomials.classes` for more details.

Convenience Classes
===================

The following lists the various constants and methods common to all of
the classes representing the various kinds of polynomials. In the following,
the term ``Poly`` represents any one of the convenience classes (e.g.
`~polynomial.Polynomial`, `~chebyshev.Chebyshev`, `~hermite.Hermite`, etc.)
while the lowercase ``p`` represents an **instance** of a polynomial class.

Constants
---------

- ``Poly.domain``     -- Default domain
- ``Poly.window``     -- Default window
- ``Poly.basis_name`` -- String used to represent the basis
- ``Poly.maxpower``   -- Maximum value ``n`` such that ``p**n`` is allowed

Creation
--------

Methods for creating polynomial instances.

- ``Poly.basis(degree)``    -- Basis polynomial of given degree
- ``Poly.identity()``       -- ``p`` where ``p(x) = x`` for all ``x``
- ``Poly.fit(x, y, deg)``   -- ``p`` of degree ``deg`` with coefficients
  determined by the least-squares fit to the data ``x``, ``y``
- ``Poly.fromroots(roots)`` -- ``p`` with specified roots
- ``p.copy()``              -- Create a copy of ``p``

Conversion
----------

Methods for converting a polynomial instance of one kind to another.

- ``p.cast(Poly)``    -- Convert ``p`` to instance of kind ``Poly``
- ``p.convert(Poly)`` -- Convert ``p`` to instance of kind ``Poly`` or map
  between ``domain`` and ``window``

Calculus
--------
- ``p.deriv()`` -- Take the derivative of ``p``
- ``p.integ()`` -- Integrate ``p``

Validation
----------
- ``Poly.has_samecoef(p1, p2)``   -- Check if coefficients match
- ``Poly.has_samedomain(p1, p2)`` -- Check if domains match
- ``Poly.has_sametype(p1, p2)``   -- Check if types match
- ``Poly.has_samewindow(p1, p2)`` -- Check if windows match

Misc
----
- ``p.linspace()`` -- Return ``x, p(x)`` at equally-spaced points in ``domain``
- ``p.mapparms()`` -- Return the parameters for the linear mapping between
  ``domain`` and ``window``.
- ``p.roots()``    -- Return the roots of ``p``.
- ``p.trim()``     -- Remove trailing coefficients.
- ``p.cutdeg(degree)`` -- Truncate ``p`` to given degree
- ``p.truncate(size)`` -- Truncate ``p`` to given size

"""
from .chebyshev import Chebyshev
from .hermite import Hermite
from .hermite_e import HermiteE
from .laguerre import Laguerre
from .legendre import Legendre
from .polynomial import Polynomial

__all__ = [  # noqa: F822
    "set_default_printstyle",
    "polynomial", "Polynomial",
    "chebyshev", "Chebyshev",
    "legendre", "Legendre",
    "hermite", "Hermite",
    "hermite_e", "HermiteE",
    "laguerre", "Laguerre",
]


def set_default_printstyle(style):
    """
    Set the default format for the string representation of polynomials.

    Values for ``style`` must be valid inputs to ``__format__``, i.e. 'ascii'
    or 'unicode'.

    Parameters
    ----------
    style : str
        Format string for default printing style. Must be either 'ascii' or
        'unicode'.

    Notes
    -----
    The default format depends on the platform: 'unicode' is used on
    Unix-based systems and 'ascii' on Windows. This determination is based on
    default font support for the unicode superscript and subscript ranges.

    Examples
    --------
    >>> p = np.polynomial.Polynomial([1, 2, 3])
    >>> c = np.polynomial.Chebyshev([1, 2, 3])
    >>> np.polynomial.set_default_printstyle('unicode')
    >>> print(p)
    1.0 + 2.0·x + 3.0·x²
    >>> print(c)
    1.0 + 2.0·T₁(x) + 3.0·T₂(x)
    >>> np.polynomial.set_default_printstyle('ascii')
    >>> print(p)
    1.0 + 2.0 x + 3.0 x**2
    >>> print(c)
    1.0 + 2.0 T_1(x) + 3.0 T_2(x)
    >>> # Formatting supersedes all class/package-level defaults
    >>> print(f"{p:unicode}")
    1.0 + 2.0·x + 3.0·x²
    """
    if style not in ('unicode', 'ascii'):
        raise ValueError(
            f"Unsupported format string '{style}'. Valid options are 'ascii' "
            f"and 'unicode'"
        )
    _use_unicode = True
    if style == 'ascii':
        _use_unicode = False
    from ._polybase import ABCPolyBase
    ABCPolyBase._use_unicode = _use_unicode


from numpy._pytesttester import PytestTester

test = PytestTester(__name__)
del PytestTester

# === NexusCore/openenv\Lib\site-packages\pip\_internal\network\download.py ===
"""Download files with progress indicators.
"""

import email.message
import logging
import mimetypes
import os
from typing import Iterable, Optional, Tuple

from pip._vendor.requests.models import Response

from pip._internal.cli.progress_bars import get_download_progress_renderer
from pip._internal.exceptions import NetworkConnectionError
from pip._internal.models.index import PyPI
from pip._internal.models.link import Link
from pip._internal.network.cache import is_from_cache
from pip._internal.network.session import PipSession
from pip._internal.network.utils import HEADERS, raise_for_status, response_chunks
from pip._internal.utils.misc import format_size, redact_auth_from_url, splitext

logger = logging.getLogger(__name__)


def _get_http_response_size(resp: Response) -> Optional[int]:
    try:
        return int(resp.headers["content-length"])
    except (ValueError, KeyError, TypeError):
        return None


def _prepare_download(
    resp: Response,
    link: Link,
    progress_bar: str,
) -> Iterable[bytes]:
    total_length = _get_http_response_size(resp)

    if link.netloc == PyPI.file_storage_domain:
        url = link.show_url
    else:
        url = link.url_without_fragment

    logged_url = redact_auth_from_url(url)

    if total_length:
        logged_url = f"{logged_url} ({format_size(total_length)})"

    if is_from_cache(resp):
        logger.info("Using cached %s", logged_url)
    else:
        logger.info("Downloading %s", logged_url)

    if logger.getEffectiveLevel() > logging.INFO:
        show_progress = False
    elif is_from_cache(resp):
        show_progress = False
    elif not total_length:
        show_progress = True
    elif total_length > (512 * 1024):
        show_progress = True
    else:
        show_progress = False

    chunks = response_chunks(resp)

    if not show_progress:
        return chunks

    renderer = get_download_progress_renderer(bar_type=progress_bar, size=total_length)
    return renderer(chunks)


def sanitize_content_filename(filename: str) -> str:
    """
    Sanitize the "filename" value from a Content-Disposition header.
    """
    return os.path.basename(filename)


def parse_content_disposition(content_disposition: str, default_filename: str) -> str:
    """
    Parse the "filename" value from a Content-Disposition header, and
    return the default filename if the result is empty.
    """
    m = email.message.Message()
    m["content-type"] = content_disposition
    filename = m.get_param("filename")
    if filename:
        # We need to sanitize the filename to prevent directory traversal
        # in case the filename contains ".." path parts.
        filename = sanitize_content_filename(str(filename))
    return filename or default_filename


def _get_http_response_filename(resp: Response, link: Link) -> str:
    """Get an ideal filename from the given HTTP response, falling back to
    the link filename if not provided.
    """
    filename = link.filename  # fallback
    # Have a look at the Content-Disposition header for a better guess
    content_disposition = resp.headers.get("content-disposition")
    if content_disposition:
        filename = parse_content_disposition(content_disposition, filename)
    ext: Optional[str] = splitext(filename)[1]
    if not ext:
        ext = mimetypes.guess_extension(resp.headers.get("content-type", ""))
        if ext:
            filename += ext
    if not ext and link.url != resp.url:
        ext = os.path.splitext(resp.url)[1]
        if ext:
            filename += ext
    return filename


def _http_get_download(session: PipSession, link: Link) -> Response:
    target_url = link.url.split("#", 1)[0]
    resp = session.get(target_url, headers=HEADERS, stream=True)
    raise_for_status(resp)
    return resp


class Downloader:
    def __init__(
        self,
        session: PipSession,
        progress_bar: str,
    ) -> None:
        self._session = session
        self._progress_bar = progress_bar

    def __call__(self, link: Link, location: str) -> Tuple[str, str]:
        """Download the file given by link into location."""
        try:
            resp = _http_get_download(self._session, link)
        except NetworkConnectionError as e:
            assert e.response is not None
            logger.critical(
                "HTTP error %s while getting %s", e.response.status_code, link
            )
            raise

        filename = _get_http_response_filename(resp, link)
        filepath = os.path.join(location, filename)

        chunks = _prepare_download(resp, link, self._progress_bar)
        with open(filepath, "wb") as content_file:
            for chunk in chunks:
                content_file.write(chunk)
        content_type = resp.headers.get("Content-Type", "")
        return filepath, content_type


class BatchDownloader:
    def __init__(
        self,
        session: PipSession,
        progress_bar: str,
    ) -> None:
        self._session = session
        self._progress_bar = progress_bar

    def __call__(
        self, links: Iterable[Link], location: str
    ) -> Iterable[Tuple[Link, Tuple[str, str]]]:
        """Download the files given by links into location."""
        for link in links:
            try:
                resp = _http_get_download(self._session, link)
            except NetworkConnectionError as e:
                assert e.response is not None
                logger.critical(
                    "HTTP error %s while getting %s",
                    e.response.status_code,
                    link,
                )
                raise

            filename = _get_http_response_filename(resp, link)
            filepath = os.path.join(location, filename)

            chunks = _prepare_download(resp, link, self._progress_bar)
            with open(filepath, "wb") as content_file:
                for chunk in chunks:
                    content_file.write(chunk)
            content_type = resp.headers.get("Content-Type", "")
            yield link, (filepath, content_type)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\columns.py ===
from collections import defaultdict
from itertools import chain
from operator import itemgetter
from typing import Dict, Iterable, List, Optional, Tuple

from .align import Align, AlignMethod
from .console import Console, ConsoleOptions, RenderableType, RenderResult
from .constrain import Constrain
from .measure import Measurement
from .padding import Padding, PaddingDimensions
from .table import Table
from .text import TextType
from .jupyter import JupyterMixin


class Columns(JupyterMixin):
    """Display renderables in neat columns.

    Args:
        renderables (Iterable[RenderableType]): Any number of Rich renderables (including str).
        width (int, optional): The desired width of the columns, or None to auto detect. Defaults to None.
        padding (PaddingDimensions, optional): Optional padding around cells. Defaults to (0, 1).
        expand (bool, optional): Expand columns to full width. Defaults to False.
        equal (bool, optional): Arrange in to equal sized columns. Defaults to False.
        column_first (bool, optional): Align items from top to bottom (rather than left to right). Defaults to False.
        right_to_left (bool, optional): Start column from right hand side. Defaults to False.
        align (str, optional): Align value ("left", "right", or "center") or None for default. Defaults to None.
        title (TextType, optional): Optional title for Columns.
    """

    def __init__(
        self,
        renderables: Optional[Iterable[RenderableType]] = None,
        padding: PaddingDimensions = (0, 1),
        *,
        width: Optional[int] = None,
        expand: bool = False,
        equal: bool = False,
        column_first: bool = False,
        right_to_left: bool = False,
        align: Optional[AlignMethod] = None,
        title: Optional[TextType] = None,
    ) -> None:
        self.renderables = list(renderables or [])
        self.width = width
        self.padding = padding
        self.expand = expand
        self.equal = equal
        self.column_first = column_first
        self.right_to_left = right_to_left
        self.align: Optional[AlignMethod] = align
        self.title = title

    def add_renderable(self, renderable: RenderableType) -> None:
        """Add a renderable to the columns.

        Args:
            renderable (RenderableType): Any renderable object.
        """
        self.renderables.append(renderable)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        render_str = console.render_str
        renderables = [
            render_str(renderable) if isinstance(renderable, str) else renderable
            for renderable in self.renderables
        ]
        if not renderables:
            return
        _top, right, _bottom, left = Padding.unpack(self.padding)
        width_padding = max(left, right)
        max_width = options.max_width
        widths: Dict[int, int] = defaultdict(int)
        column_count = len(renderables)

        get_measurement = Measurement.get
        renderable_widths = [
            get_measurement(console, options, renderable).maximum
            for renderable in renderables
        ]
        if self.equal:
            renderable_widths = [max(renderable_widths)] * len(renderable_widths)

        def iter_renderables(
            column_count: int,
        ) -> Iterable[Tuple[int, Optional[RenderableType]]]:
            item_count = len(renderables)
            if self.column_first:
                width_renderables = list(zip(renderable_widths, renderables))

                column_lengths: List[int] = [item_count // column_count] * column_count
                for col_no in range(item_count % column_count):
                    column_lengths[col_no] += 1

                row_count = (item_count + column_count - 1) // column_count
                cells = [[-1] * column_count for _ in range(row_count)]
                row = col = 0
                for index in range(item_count):
                    cells[row][col] = index
                    column_lengths[col] -= 1
                    if column_lengths[col]:
                        row += 1
                    else:
                        col += 1
                        row = 0
                for index in chain.from_iterable(cells):
                    if index == -1:
                        break
                    yield width_renderables[index]
            else:
                yield from zip(renderable_widths, renderables)
            # Pad odd elements with spaces
            if item_count % column_count:
                for _ in range(column_count - (item_count % column_count)):
                    yield 0, None

        table = Table.grid(padding=self.padding, collapse_padding=True, pad_edge=False)
        table.expand = self.expand
        table.title = self.title

        if self.width is not None:
            column_count = (max_width) // (self.width + width_padding)
            for _ in range(column_count):
                table.add_column(width=self.width)
        else:
            while column_count > 1:
                widths.clear()
                column_no = 0
                for renderable_width, _ in iter_renderables(column_count):
                    widths[column_no] = max(widths[column_no], renderable_width)
                    total_width = sum(widths.values()) + width_padding * (
                        len(widths) - 1
                    )
                    if total_width > max_width:
                        column_count = len(widths) - 1
                        break
                    else:
                        column_no = (column_no + 1) % column_count
                else:
                    break

        get_renderable = itemgetter(1)
        _renderables = [
            get_renderable(_renderable)
            for _renderable in iter_renderables(column_count)
        ]
        if self.equal:
            _renderables = [
                None
                if renderable is None
                else Constrain(renderable, renderable_widths[0])
                for renderable in _renderables
            ]
        if self.align:
            align = self.align
            _Align = Align
            _renderables = [
                None if renderable is None else _Align(renderable, align)
                for renderable in _renderables
            ]

        right_to_left = self.right_to_left
        add_row = table.add_row
        for start in range(0, len(_renderables), column_count):
            row = _renderables[start : start + column_count]
            if right_to_left:
                row = row[::-1]
            add_row(*row)
        yield table


if __name__ == "__main__":  # pragma: no cover
    import os

    console = Console()

    files = [f"{i} {s}" for i, s in enumerate(sorted(os.listdir()))]
    columns = Columns(files, padding=(0, 1), expand=False, equal=False)
    console.print(columns)
    console.rule()
    columns.column_first = True
    console.print(columns)
    columns.right_to_left = True
    console.rule()
    console.print(columns)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\q.py ===
"""
    pygments.lexers.q
    ~~~~~~~~~~~~~~~~~

    Lexer for the Q programming language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, words, include, bygroups, inherit
from pygments.token import Comment, Name, Number, Operator, Punctuation, \
    String, Whitespace, Literal, Generic

__all__ = ["KLexer", "QLexer"]


class KLexer(RegexLexer):
    """
    For K source code.
    """

    name = "K"
    aliases = ["k"]
    filenames = ["*.k"]
    url = "https://code.kx.com"
    version_added = '2.12'

    tokens = {
        "whitespace": [
            # hashbang script
            (r"^#!.*", Comment.Hashbang),
            # Comments
            (r"^/\s*\n", Comment.Multiline, "comments"),
            (r"(?<!\S)/.*", Comment.Single),
            # Whitespace
            (r"\s+", Whitespace),
            # Strings
            (r"\"", String.Double, "strings"),
        ],
        "root": [
            include("whitespace"),
            include("keywords"),
            include("declarations"),
        ],
        "keywords": [
            (words(("abs", "acos", "asin", "atan", "avg", "bin",
                    "binr", "by", "cor", "cos", "cov", "dev",
                    "delete", "div", "do", "enlist", "exec", "exit",
                    "exp", "from", "getenv", "hopen", "if", "in",
                    "insert", "last", "like", "log", "max", "min",
                    "prd", "select", "setenv", "sin", "sqrt", "ss",
                    "sum", "tan", "update", "var", "wavg", "while",
                    "within", "wsum", "xexp"),
                   suffix=r"\b"), Operator.Word),
        ],
        "declarations": [
            # Timing
            (r"^\\ts?", Comment.Preproc),
            (r"^(\\\w\s+[^/\n]*?)(/.*)",
             bygroups(Comment.Preproc, Comment.Single)),
            # Generic System Commands
            (r"^\\\w.*", Comment.Preproc),
            # Prompt
            (r"^[a-zA-Z]\)", Generic.Prompt),
            # Function Names
            (r"([.]?[a-zA-Z][\w.]*)(\s*)([-.~=!@#$%^&*_+|,<>?/\\:']?:)(\s*)(\{)",
             bygroups(Name.Function, Whitespace, Operator, Whitespace, Punctuation),
             "functions"),
            # Variable Names
            (r"([.]?[a-zA-Z][\w.]*)(\s*)([-.~=!@#$%^&*_+|,<>?/\\:']?:)",
             bygroups(Name.Variable, Whitespace, Operator)),
            # Functions
            (r"\{", Punctuation, "functions"),
            # Parentheses
            (r"\(", Punctuation, "parentheses"),
            # Brackets
            (r"\[", Punctuation, "brackets"),
            # Errors
            (r"'`([a-zA-Z][\w.]*)?", Name.Exception),
            # File Symbols
            (r"`:([a-zA-Z/][\w./]*)?", String.Symbol),
            # Symbols
            (r"`([a-zA-Z][\w.]*)?", String.Symbol),
            # Numbers
            include("numbers"),
            # Variable Names
            (r"[a-zA-Z][\w.]*", Name),
            # Operators
            (r"[-=+*#$%@!~^&:.,<>'\\|/?_]", Operator),
            # Punctuation
            (r";", Punctuation),
        ],
        "functions": [
            include("root"),
            (r"\}", Punctuation, "#pop"),
        ],
        "parentheses": [
            include("root"),
            (r"\)", Punctuation, "#pop"),
        ],
        "brackets": [
            include("root"),
            (r"\]", Punctuation, "#pop"),
        ],
        "numbers": [
            # Binary Values
            (r"[01]+b", Number.Bin),
            # Nulls/Infinities
            (r"0[nNwW][cefghijmndzuvtp]?", Number),
            # Timestamps
            ((r"(?:[0-9]{4}[.][0-9]{2}[.][0-9]{2}|[0-9]+)"
              "D(?:[0-9](?:[0-9](?::[0-9]{2}"
              "(?::[0-9]{2}(?:[.][0-9]*)?)?)?)?)?"), Literal.Date),
            # Datetimes
            ((r"[0-9]{4}[.][0-9]{2}"
              "(?:m|[.][0-9]{2}(?:T(?:[0-9]{2}:[0-9]{2}"
              "(?::[0-9]{2}(?:[.][0-9]*)?)?)?)?)"), Literal.Date),
            # Times
            (r"[0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:[.][0-9]{1,3})?)?",
             Literal.Date),
            # GUIDs
            (r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
             Number.Hex),
            # Byte Vectors
            (r"0x[0-9a-fA-F]+", Number.Hex),
            # Floats
            (r"([0-9]*[.]?[0-9]+|[0-9]+[.]?[0-9]*)[eE][+-]?[0-9]+[ef]?",
             Number.Float),
            (r"([0-9]*[.][0-9]+|[0-9]+[.][0-9]*)[ef]?", Number.Float),
            (r"[0-9]+[ef]", Number.Float),
            # Characters
            (r"[0-9]+c", Number),
            # Integers
            (r"[0-9]+[ihtuv]", Number.Integer),
            # Long Integers
            (r"[0-9]+[jnp]?", Number.Integer.Long),
        ],
        "comments": [
            (r"[^\\]+", Comment.Multiline),
            (r"^\\", Comment.Multiline, "#pop"),
            (r"\\", Comment.Multiline),
        ],
        "strings": [
            (r'[^"\\]+', String.Double),
            (r"\\.", String.Escape),
            (r'"', String.Double, "#pop"),
        ],
    }


class QLexer(KLexer):
    """
    For `Q <https://code.kx.com/>`_ source code.
    """

    name = "Q"
    aliases = ["q"]
    filenames = ["*.q"]
    version_added = '2.12'

    tokens = {
        "root": [
            (words(("aj", "aj0", "ajf", "ajf0", "all", "and", "any", "asc",
                    "asof", "attr", "avgs", "ceiling", "cols", "count", "cross",
                    "csv", "cut", "deltas", "desc", "differ", "distinct", "dsave",
                    "each", "ej", "ema", "eval", "except", "fby", "fills", "first",
                    "fkeys", "flip", "floor", "get", "group", "gtime", "hclose",
                    "hcount", "hdel", "hsym", "iasc", "idesc", "ij", "ijf",
                    "inter", "inv", "key", "keys", "lj", "ljf", "load", "lower",
                    "lsq", "ltime", "ltrim", "mavg", "maxs", "mcount", "md5",
                    "mdev", "med", "meta", "mins", "mmax", "mmin", "mmu", "mod",
                    "msum", "neg", "next", "not", "null", "or", "over", "parse",
                    "peach", "pj", "prds", "prior", "prev", "rand", "rank", "ratios",
                    "raze", "read0", "read1", "reciprocal", "reval", "reverse",
                    "rload", "rotate", "rsave", "rtrim", "save", "scan", "scov",
                    "sdev", "set", "show", "signum", "ssr", "string", "sublist",
                    "sums", "sv", "svar", "system", "tables", "til", "trim", "txf",
                    "type", "uj", "ujf", "ungroup", "union", "upper", "upsert",
                    "value", "view", "views", "vs", "where", "wj", "wj1", "ww",
                    "xasc", "xbar", "xcol", "xcols", "xdesc", "xgroup", "xkey",
                    "xlog", "xprev", "xrank"),
                    suffix=r"\b"), Name.Builtin,
            ),
            inherit,
        ],
    }

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_signals.py ===
from __future__ import annotations

import signal
from typing import TYPE_CHECKING, NoReturn

import pytest

import trio
from trio.testing import RaisesGroup

from .. import _core
from .._signals import _signal_handler, get_pending_signal_count, open_signal_receiver

if TYPE_CHECKING:
    from types import FrameType


async def test_open_signal_receiver() -> None:
    orig = signal.getsignal(signal.SIGILL)
    with open_signal_receiver(signal.SIGILL) as receiver:
        # Raise it a few times, to exercise signal coalescing, both at the
        # call_soon level and at the SignalQueue level
        signal.raise_signal(signal.SIGILL)
        signal.raise_signal(signal.SIGILL)
        await _core.wait_all_tasks_blocked()
        signal.raise_signal(signal.SIGILL)
        await _core.wait_all_tasks_blocked()
        async for signum in receiver:  # pragma: no branch
            assert signum == signal.SIGILL
            break
        assert get_pending_signal_count(receiver) == 0
        signal.raise_signal(signal.SIGILL)
        async for signum in receiver:  # pragma: no branch
            assert signum == signal.SIGILL
            break
        assert get_pending_signal_count(receiver) == 0
    with pytest.raises(RuntimeError):
        await receiver.__anext__()
    assert signal.getsignal(signal.SIGILL) is orig


async def test_open_signal_receiver_restore_handler_after_one_bad_signal() -> None:
    orig = signal.getsignal(signal.SIGILL)
    with pytest.raises(
        ValueError,
        match=r"(signal number out of range|invalid signal value)$",
    ):
        with open_signal_receiver(signal.SIGILL, 1234567):
            pass  # pragma: no cover
    # Still restored even if we errored out
    assert signal.getsignal(signal.SIGILL) is orig


def test_open_signal_receiver_empty_fail() -> None:
    with pytest.raises(TypeError, match="No signals were provided"):
        with open_signal_receiver():
            pass


async def test_open_signal_receiver_restore_handler_after_duplicate_signal() -> None:
    orig = signal.getsignal(signal.SIGILL)
    with open_signal_receiver(signal.SIGILL, signal.SIGILL):
        pass
    # Still restored correctly
    assert signal.getsignal(signal.SIGILL) is orig


async def test_catch_signals_wrong_thread() -> None:
    async def naughty() -> None:
        with open_signal_receiver(signal.SIGINT):
            pass  # pragma: no cover

    with pytest.raises(RuntimeError):
        await trio.to_thread.run_sync(trio.run, naughty)


async def test_open_signal_receiver_conflict() -> None:
    with RaisesGroup(trio.BusyResourceError):
        with open_signal_receiver(signal.SIGILL) as receiver:
            async with trio.open_nursery() as nursery:
                nursery.start_soon(receiver.__anext__)
                nursery.start_soon(receiver.__anext__)


# Blocks until all previous calls to run_sync_soon(idempotent=True) have been
# processed.
async def wait_run_sync_soon_idempotent_queue_barrier() -> None:
    ev = trio.Event()
    token = _core.current_trio_token()
    token.run_sync_soon(ev.set, idempotent=True)
    await ev.wait()


async def test_open_signal_receiver_no_starvation() -> None:
    # Set up a situation where there are always 2 pending signals available to
    # report, and make sure that instead of getting the same signal reported
    # over and over, it alternates between reporting both of them.
    with open_signal_receiver(signal.SIGILL, signal.SIGFPE) as receiver:
        try:
            print(signal.getsignal(signal.SIGILL))
            previous = None
            for _ in range(10):
                signal.raise_signal(signal.SIGILL)
                signal.raise_signal(signal.SIGFPE)
                await wait_run_sync_soon_idempotent_queue_barrier()
                if previous is None:
                    previous = await receiver.__anext__()
                else:
                    got = await receiver.__anext__()
                    assert got in [signal.SIGILL, signal.SIGFPE]
                    assert got != previous
                    previous = got
            # Clear out the last signal so that it doesn't get redelivered
            while get_pending_signal_count(receiver) != 0:
                await receiver.__anext__()
        except BaseException:  # pragma: no cover
            # If there's an unhandled exception above, then exiting the
            # open_signal_receiver block might cause the signal to be
            # redelivered and give us a core dump instead of a traceback...
            import traceback

            traceback.print_exc()


async def test_catch_signals_race_condition_on_exit() -> None:
    delivered_directly: set[int] = set()

    def direct_handler(signo: int, frame: FrameType | None) -> None:
        delivered_directly.add(signo)

    print(1)
    # Test the version where the call_soon *doesn't* have a chance to run
    # before we exit the with block:
    with _signal_handler({signal.SIGILL, signal.SIGFPE}, direct_handler):
        with open_signal_receiver(signal.SIGILL, signal.SIGFPE) as receiver:
            signal.raise_signal(signal.SIGILL)
            signal.raise_signal(signal.SIGFPE)
        await wait_run_sync_soon_idempotent_queue_barrier()
    assert delivered_directly == {signal.SIGILL, signal.SIGFPE}
    delivered_directly.clear()

    print(2)
    # Test the version where the call_soon *does* have a chance to run before
    # we exit the with block:
    with _signal_handler({signal.SIGILL, signal.SIGFPE}, direct_handler):
        with open_signal_receiver(signal.SIGILL, signal.SIGFPE) as receiver:
            signal.raise_signal(signal.SIGILL)
            signal.raise_signal(signal.SIGFPE)
            await wait_run_sync_soon_idempotent_queue_barrier()
            assert get_pending_signal_count(receiver) == 2
    assert delivered_directly == {signal.SIGILL, signal.SIGFPE}
    delivered_directly.clear()

    # Again, but with a SIG_IGN signal:

    print(3)
    with _signal_handler({signal.SIGILL}, signal.SIG_IGN):
        with open_signal_receiver(signal.SIGILL) as receiver:
            signal.raise_signal(signal.SIGILL)
        await wait_run_sync_soon_idempotent_queue_barrier()
    # test passes if the process reaches this point without dying

    print(4)
    with _signal_handler({signal.SIGILL}, signal.SIG_IGN):
        with open_signal_receiver(signal.SIGILL) as receiver:
            signal.raise_signal(signal.SIGILL)
            await wait_run_sync_soon_idempotent_queue_barrier()
            assert get_pending_signal_count(receiver) == 1
    # test passes if the process reaches this point without dying

    # Check exception chaining if there are multiple exception-raising
    # handlers
    def raise_handler(signum: int, frame: FrameType | None) -> NoReturn:
        raise RuntimeError(signum)

    with _signal_handler({signal.SIGILL, signal.SIGFPE}, raise_handler):
        with pytest.raises(RuntimeError) as excinfo:
            with open_signal_receiver(signal.SIGILL, signal.SIGFPE) as receiver:
                signal.raise_signal(signal.SIGILL)
                signal.raise_signal(signal.SIGFPE)
                await wait_run_sync_soon_idempotent_queue_barrier()
                assert get_pending_signal_count(receiver) == 2
        exc = excinfo.value
        signums = {exc.args[0]}
        assert isinstance(exc.__context__, RuntimeError)
        signums.add(exc.__context__.args[0])
        assert signums == {signal.SIGILL, signal.SIGFPE}

# === NexusCore/openenv\Lib\site-packages\jupyter_client\launcher.py ===
"""Utilities for launching kernels"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import os
import sys
import warnings
from subprocess import PIPE, Popen
from typing import Any, Dict, List, Optional

from traitlets.log import get_logger


def launch_kernel(
    cmd: List[str],
    stdin: Optional[int] = None,
    stdout: Optional[int] = None,
    stderr: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
    independent: bool = False,
    cwd: Optional[str] = None,
    **kw: Any,
) -> Popen:
    """Launches a localhost kernel, binding to the specified ports.

    Parameters
    ----------
    cmd : Popen list,
        A string of Python code that imports and executes a kernel entry point.

    stdin, stdout, stderr : optional (default None)
        Standards streams, as defined in subprocess.Popen.

    env: dict, optional
        Environment variables passed to the kernel

    independent : bool, optional (default False)
        If set, the kernel process is guaranteed to survive if this process
        dies. If not set, an effort is made to ensure that the kernel is killed
        when this process dies. Note that in this case it is still good practice
        to kill kernels manually before exiting.

    cwd : path, optional
        The working dir of the kernel process (default: cwd of this process).

    **kw: optional
        Additional arguments for Popen

    Returns
    -------

    Popen instance for the kernel subprocess
    """

    # Popen will fail (sometimes with a deadlock) if stdin, stdout, and stderr
    # are invalid. Unfortunately, there is in general no way to detect whether
    # they are valid.  The following two blocks redirect them to (temporary)
    # pipes in certain important cases.

    # If this process has been backgrounded, our stdin is invalid. Since there
    # is no compelling reason for the kernel to inherit our stdin anyway, we'll
    # place this one safe and always redirect.
    redirect_in = True
    _stdin = PIPE if stdin is None else stdin

    # If this process in running on pythonw, we know that stdin, stdout, and
    # stderr are all invalid.
    redirect_out = sys.executable.endswith("pythonw.exe")
    if redirect_out:
        blackhole = open(os.devnull, "w")  # noqa
        _stdout = blackhole if stdout is None else stdout
        _stderr = blackhole if stderr is None else stderr
    else:
        _stdout, _stderr = stdout, stderr

    env = env if (env is not None) else os.environ.copy()

    kwargs = kw.copy()
    main_args = {
        "stdin": _stdin,
        "stdout": _stdout,
        "stderr": _stderr,
        "cwd": cwd,
        "env": env,
    }
    kwargs.update(main_args)

    # Spawn a kernel.
    if sys.platform == "win32":
        if cwd:
            kwargs["cwd"] = cwd

        from .win_interrupt import create_interrupt_event

        # Create a Win32 event for interrupting the kernel
        # and store it in an environment variable.
        interrupt_event = create_interrupt_event()
        env["JPY_INTERRUPT_EVENT"] = str(interrupt_event)
        # deprecated old env name:
        env["IPY_INTERRUPT_EVENT"] = env["JPY_INTERRUPT_EVENT"]

        try:
            from _winapi import (
                CREATE_NEW_PROCESS_GROUP,
                DUPLICATE_SAME_ACCESS,
                DuplicateHandle,
                GetCurrentProcess,
            )
        except:  # noqa
            from _subprocess import (
                CREATE_NEW_PROCESS_GROUP,
                DUPLICATE_SAME_ACCESS,
                DuplicateHandle,
                GetCurrentProcess,
            )

        # create a handle on the parent to be inherited
        if independent:
            kwargs["creationflags"] = CREATE_NEW_PROCESS_GROUP
        else:
            pid = GetCurrentProcess()
            handle = DuplicateHandle(
                pid,
                pid,
                pid,
                0,
                True,
                DUPLICATE_SAME_ACCESS,  # Inheritable by new processes.
            )
            env["JPY_PARENT_PID"] = str(int(handle))

        # Prevent creating new console window on pythonw
        if redirect_out:
            kwargs["creationflags"] = (
                kwargs.setdefault("creationflags", 0) | 0x08000000
            )  # CREATE_NO_WINDOW

        # Avoid closing the above parent and interrupt handles.
        # close_fds is True by default on Python >=3.7
        # or when no stream is captured on Python <3.7
        # (we always capture stdin, so this is already False by default on <3.7)
        kwargs["close_fds"] = False
    else:
        # Create a new session.
        # This makes it easier to interrupt the kernel,
        # because we want to interrupt the whole process group.
        # We don't use setpgrp, which is known to cause problems for kernels starting
        # certain interactive subprocesses, such as bash -i.
        kwargs["start_new_session"] = True
        if not independent:
            env["JPY_PARENT_PID"] = str(os.getpid())

    try:
        # Allow to use ~/ in the command or its arguments
        cmd = [os.path.expanduser(s) for s in cmd]
        proc = Popen(cmd, **kwargs)  # noqa
    except Exception as ex:
        try:
            msg = "Failed to run command:\n{}\n    PATH={!r}\n    with kwargs:\n{!r}\n"
            # exclude environment variables,
            # which may contain access tokens and the like.
            without_env = {key: value for key, value in kwargs.items() if key != "env"}
            msg = msg.format(cmd, env.get("PATH", os.defpath), without_env)
            get_logger().error(msg)
        except Exception as ex2:  # Don't let a formatting/logger issue lead to the wrong exception
            warnings.warn(f"Failed to run command: '{cmd}' due to exception: {ex}", stacklevel=2)
            warnings.warn(
                f"The following exception occurred handling the previous failure: {ex2}",
                stacklevel=2,
            )
        raise ex

    if sys.platform == "win32":
        # Attach the interrupt event to the Popen object so it can be used later.
        proc.win32_interrupt_event = interrupt_event

    # Clean up pipes created to work around Popen bug.
    if redirect_in and stdin is None:
        assert proc.stdin is not None
        proc.stdin.close()

    return proc


__all__ = [
    "launch_kernel",
]

# === NexusCore/openenv\Lib\site-packages\PIL\WmfImagePlugin.py ===
#
# The Python Imaging Library
# $Id$
#
# WMF stub codec
#
# history:
# 1996-12-14 fl   Created
# 2004-02-22 fl   Turned into a stub driver
# 2004-02-23 fl   Added EMF support
#
# Copyright (c) Secret Labs AB 1997-2004.  All rights reserved.
# Copyright (c) Fredrik Lundh 1996.
#
# See the README file for information on usage and redistribution.
#
# WMF/EMF reference documentation:
# https://winprotocoldoc.blob.core.windows.net/productionwindowsarchives/MS-WMF/[MS-WMF].pdf
# http://wvware.sourceforge.net/caolan/index.html
# http://wvware.sourceforge.net/caolan/ora-wmf.html
from __future__ import annotations

from typing import IO

from . import Image, ImageFile
from ._binary import i16le as word
from ._binary import si16le as short
from ._binary import si32le as _long

_handler = None


def register_handler(handler: ImageFile.StubHandler | None) -> None:
    """
    Install application-specific WMF image handler.

    :param handler: Handler object.
    """
    global _handler
    _handler = handler


if hasattr(Image.core, "drawwmf"):
    # install default handler (windows only)

    class WmfHandler(ImageFile.StubHandler):
        def open(self, im: ImageFile.StubImageFile) -> None:
            im._mode = "RGB"
            self.bbox = im.info["wmf_bbox"]

        def load(self, im: ImageFile.StubImageFile) -> Image.Image:
            im.fp.seek(0)  # rewind
            return Image.frombytes(
                "RGB",
                im.size,
                Image.core.drawwmf(im.fp.read(), im.size, self.bbox),
                "raw",
                "BGR",
                (im.size[0] * 3 + 3) & -4,
                -1,
            )

    register_handler(WmfHandler())

#
# --------------------------------------------------------------------
# Read WMF file


def _accept(prefix: bytes) -> bool:
    return prefix.startswith((b"\xd7\xcd\xc6\x9a\x00\x00", b"\x01\x00\x00\x00"))


##
# Image plugin for Windows metafiles.


class WmfStubImageFile(ImageFile.StubImageFile):
    format = "WMF"
    format_description = "Windows Metafile"

    def _open(self) -> None:
        # check placable header
        s = self.fp.read(80)

        if s.startswith(b"\xd7\xcd\xc6\x9a\x00\x00"):
            # placeable windows metafile

            # get units per inch
            inch = word(s, 14)
            if inch == 0:
                msg = "Invalid inch"
                raise ValueError(msg)
            self._inch: tuple[float, float] = inch, inch

            # get bounding box
            x0 = short(s, 6)
            y0 = short(s, 8)
            x1 = short(s, 10)
            y1 = short(s, 12)

            # normalize size to 72 dots per inch
            self.info["dpi"] = 72
            size = (
                (x1 - x0) * self.info["dpi"] // inch,
                (y1 - y0) * self.info["dpi"] // inch,
            )

            self.info["wmf_bbox"] = x0, y0, x1, y1

            # sanity check (standard metafile header)
            if s[22:26] != b"\x01\x00\t\x00":
                msg = "Unsupported WMF file format"
                raise SyntaxError(msg)

        elif s.startswith(b"\x01\x00\x00\x00") and s[40:44] == b" EMF":
            # enhanced metafile

            # get bounding box
            x0 = _long(s, 8)
            y0 = _long(s, 12)
            x1 = _long(s, 16)
            y1 = _long(s, 20)

            # get frame (in 0.01 millimeter units)
            frame = _long(s, 24), _long(s, 28), _long(s, 32), _long(s, 36)

            size = x1 - x0, y1 - y0

            # calculate dots per inch from bbox and frame
            xdpi = 2540.0 * (x1 - x0) / (frame[2] - frame[0])
            ydpi = 2540.0 * (y1 - y0) / (frame[3] - frame[1])

            self.info["wmf_bbox"] = x0, y0, x1, y1

            if xdpi == ydpi:
                self.info["dpi"] = xdpi
            else:
                self.info["dpi"] = xdpi, ydpi
            self._inch = xdpi, ydpi

        else:
            msg = "Unsupported file format"
            raise SyntaxError(msg)

        self._mode = "RGB"
        self._size = size

        loader = self._load()
        if loader:
            loader.open(self)

    def _load(self) -> ImageFile.StubHandler | None:
        return _handler

    def load(
        self, dpi: float | tuple[float, float] | None = None
    ) -> Image.core.PixelAccess | None:
        if dpi is not None:
            self.info["dpi"] = dpi
            x0, y0, x1, y1 = self.info["wmf_bbox"]
            if not isinstance(dpi, tuple):
                dpi = dpi, dpi
            self._size = (
                int((x1 - x0) * dpi[0] / self._inch[0]),
                int((y1 - y0) * dpi[1] / self._inch[1]),
            )
        return super().load()


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    if _handler is None or not hasattr(_handler, "save"):
        msg = "WMF save handler not installed"
        raise OSError(msg)
    _handler.save(im, fp, filename)


#
# --------------------------------------------------------------------
# Registry stuff


Image.register_open(WmfStubImageFile.format, WmfStubImageFile, _accept)
Image.register_save(WmfStubImageFile.format, _save)

Image.register_extensions(WmfStubImageFile.format, [".wmf", ".emf"])

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\knbc.py ===
#! /usr/bin/env python
# KNB Corpus reader
# Copyright (C) 2001-2024 NLTK Project
# Author: Masato Hagiwara <hagisan@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

# For more information, see http://lilyx.net/pages/nltkjapanesecorpus.html

import re

from nltk.corpus.reader.api import CorpusReader, SyntaxCorpusReader
from nltk.corpus.reader.util import (
    FileSystemPathPointer,
    find_corpus_fileids,
    read_blankline_block,
)
from nltk.parse import DependencyGraph

# default function to convert morphlist to str for tree representation
_morphs2str_default = lambda morphs: "/".join(m[0] for m in morphs if m[0] != "EOS")


class KNBCorpusReader(SyntaxCorpusReader):
    """
    This class implements:
      - ``__init__``, which specifies the location of the corpus
        and a method for detecting the sentence blocks in corpus files.
      - ``_read_block``, which reads a block from the input stream.
      - ``_word``, which takes a block and returns a list of list of words.
      - ``_tag``, which takes a block and returns a list of list of tagged
        words.
      - ``_parse``, which takes a block and returns a list of parsed
        sentences.

    The structure of tagged words:
      tagged_word = (word(str), tags(tuple))
      tags = (surface, reading, lemma, pos1, posid1, pos2, posid2, pos3, posid3, others ...)

    Usage example

    >>> from nltk.corpus.util import LazyCorpusLoader
    >>> knbc = LazyCorpusLoader(
    ...     'knbc/corpus1',
    ...     KNBCorpusReader,
    ...     r'.*/KN.*',
    ...     encoding='euc-jp',
    ... )

    >>> len(knbc.sents()[0])
    9

    """

    def __init__(self, root, fileids, encoding="utf8", morphs2str=_morphs2str_default):
        """
        Initialize KNBCorpusReader
        morphs2str is a function to convert morphlist to str for tree representation
        for _parse()
        """
        SyntaxCorpusReader.__init__(self, root, fileids, encoding)
        self.morphs2str = morphs2str

    def _read_block(self, stream):
        # blocks are split by blankline (or EOF) - default
        return read_blankline_block(stream)

    def _word(self, t):
        res = []
        for line in t.splitlines():
            # ignore the Bunsets headers
            if not re.match(r"EOS|\*|\#|\+", line):
                cells = line.strip().split(" ")
                res.append(cells[0])

        return res

    # ignores tagset argument
    def _tag(self, t, tagset=None):
        res = []
        for line in t.splitlines():
            # ignore the Bunsets headers
            if not re.match(r"EOS|\*|\#|\+", line):
                cells = line.strip().split(" ")
                # convert cells to morph tuples
                res.append((cells[0], " ".join(cells[1:])))

        return res

    def _parse(self, t):
        dg = DependencyGraph()
        i = 0
        for line in t.splitlines():
            if line[0] in "*+":
                # start of bunsetsu or tag

                cells = line.strip().split(" ", 3)
                m = re.match(r"([\-0-9]*)([ADIP])", cells[1])

                assert m is not None

                node = dg.nodes[i]
                node.update({"address": i, "rel": m.group(2), "word": []})

                dep_parent = int(m.group(1))

                if dep_parent == -1:
                    dg.root = node
                else:
                    dg.nodes[dep_parent]["deps"].append(i)

                i += 1
            elif line[0] != "#":
                # normal morph
                cells = line.strip().split(" ")
                # convert cells to morph tuples
                morph = cells[0], " ".join(cells[1:])
                dg.nodes[i - 1]["word"].append(morph)

        if self.morphs2str:
            for node in dg.nodes.values():
                node["word"] = self.morphs2str(node["word"])

        return dg.tree()


######################################################################
# Demo
######################################################################


def demo():
    import nltk
    from nltk.corpus.util import LazyCorpusLoader

    root = nltk.data.find("corpora/knbc/corpus1")
    fileids = [
        f
        for f in find_corpus_fileids(FileSystemPathPointer(root), ".*")
        if re.search(r"\d\-\d\-[\d]+\-[\d]+", f)
    ]

    def _knbc_fileids_sort(x):
        cells = x.split("-")
        return (cells[0], int(cells[1]), int(cells[2]), int(cells[3]))

    knbc = LazyCorpusLoader(
        "knbc/corpus1",
        KNBCorpusReader,
        sorted(fileids, key=_knbc_fileids_sort),
        encoding="euc-jp",
    )

    print(knbc.fileids()[:10])
    print("".join(knbc.words()[:100]))

    print("\n\n".join(str(tree) for tree in knbc.parsed_sents()[:2]))

    knbc.morphs2str = lambda morphs: "/".join(
        "{}({})".format(m[0], m[1].split(" ")[2]) for m in morphs if m[0] != "EOS"
    ).encode("utf-8")

    print("\n\n".join("%s" % tree for tree in knbc.parsed_sents()[:2]))

    print(
        "\n".join(
            " ".join("{}/{}".format(w[0], w[1].split(" ")[2]) for w in sent)
            for sent in knbc.tagged_sents()[0:2]
        )
    )


def test():
    from nltk.corpus.util import LazyCorpusLoader

    knbc = LazyCorpusLoader(
        "knbc/corpus1", KNBCorpusReader, r".*/KN.*", encoding="euc-jp"
    )
    assert isinstance(knbc.words()[0], str)
    assert isinstance(knbc.sents()[0][0], str)
    assert isinstance(knbc.tagged_words()[0], tuple)
    assert isinstance(knbc.tagged_sents()[0][0], tuple)


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\__init__.py ===
# Natural Language Toolkit: Corpus Readers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK corpus readers.  The modules in this package provide functions
that can be used to read corpus fileids in a variety of formats.  These
functions can be used to read both the corpus fileids that are
distributed in the NLTK corpus package, and corpus fileids that are part
of external corpora.

Corpus Reader Functions
=======================
Each corpus module defines one or more "corpus reader functions",
which can be used to read documents from that corpus.  These functions
take an argument, ``item``, which is used to indicate which document
should be read from the corpus:

- If ``item`` is one of the unique identifiers listed in the corpus
  module's ``items`` variable, then the corresponding document will
  be loaded from the NLTK corpus package.
- If ``item`` is a fileid, then that file will be read.

Additionally, corpus reader functions can be given lists of item
names; in which case, they will return a concatenation of the
corresponding documents.

Corpus reader functions are named based on the type of information
they return.  Some common examples, and their return types, are:

- words(): list of str
- sents(): list of (list of str)
- paras(): list of (list of (list of str))
- tagged_words(): list of (str,str) tuple
- tagged_sents(): list of (list of (str,str))
- tagged_paras(): list of (list of (list of (str,str)))
- chunked_sents(): list of (Tree w/ (str,str) leaves)
- parsed_sents(): list of (Tree with str leaves)
- parsed_paras(): list of (list of (Tree with str leaves))
- xml(): A single xml ElementTree
- raw(): unprocessed corpus contents

For example, to read a list of the words in the Brown Corpus, use
``nltk.corpus.brown.words()``:

    >>> from nltk.corpus import brown
    >>> print(", ".join(brown.words()[:6])) # only first 6 words
    The, Fulton, County, Grand, Jury, said

isort:skip_file
"""

from nltk.corpus.reader.plaintext import *
from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.corpus.reader.tagged import *
from nltk.corpus.reader.cmudict import *
from nltk.corpus.reader.conll import *
from nltk.corpus.reader.chunked import *
from nltk.corpus.reader.wordlist import *
from nltk.corpus.reader.xmldocs import *
from nltk.corpus.reader.ppattach import *
from nltk.corpus.reader.senseval import *
from nltk.corpus.reader.ieer import *
from nltk.corpus.reader.sinica_treebank import *
from nltk.corpus.reader.bracket_parse import *
from nltk.corpus.reader.indian import *
from nltk.corpus.reader.toolbox import *
from nltk.corpus.reader.timit import *
from nltk.corpus.reader.ycoe import *
from nltk.corpus.reader.rte import *
from nltk.corpus.reader.string_category import *
from nltk.corpus.reader.propbank import *
from nltk.corpus.reader.verbnet import *
from nltk.corpus.reader.bnc import *
from nltk.corpus.reader.nps_chat import *
from nltk.corpus.reader.wordnet import *
from nltk.corpus.reader.switchboard import *
from nltk.corpus.reader.dependency import *
from nltk.corpus.reader.nombank import *
from nltk.corpus.reader.ipipan import *
from nltk.corpus.reader.pl196x import *
from nltk.corpus.reader.knbc import *
from nltk.corpus.reader.chasen import *
from nltk.corpus.reader.childes import *
from nltk.corpus.reader.aligned import *
from nltk.corpus.reader.lin import *
from nltk.corpus.reader.semcor import *
from nltk.corpus.reader.framenet import *
from nltk.corpus.reader.udhr import *
from nltk.corpus.reader.bnc import *
from nltk.corpus.reader.sentiwordnet import *
from nltk.corpus.reader.twitter import *
from nltk.corpus.reader.nkjp import *
from nltk.corpus.reader.crubadan import *
from nltk.corpus.reader.mte import *
from nltk.corpus.reader.reviews import *
from nltk.corpus.reader.opinion_lexicon import *
from nltk.corpus.reader.pros_cons import *
from nltk.corpus.reader.categorized_sents import *
from nltk.corpus.reader.comparative_sents import *
from nltk.corpus.reader.panlex_lite import *
from nltk.corpus.reader.panlex_swadesh import *
from nltk.corpus.reader.bcp47 import *

# Make sure that nltk.corpus.reader.bracket_parse gives the module, not
# the function bracket_parse() defined in nltk.tree:
from nltk.corpus.reader import bracket_parse

__all__ = [
    "CorpusReader",
    "CategorizedCorpusReader",
    "PlaintextCorpusReader",
    "find_corpus_fileids",
    "TaggedCorpusReader",
    "CMUDictCorpusReader",
    "ConllChunkCorpusReader",
    "WordListCorpusReader",
    "PPAttachmentCorpusReader",
    "SensevalCorpusReader",
    "IEERCorpusReader",
    "ChunkedCorpusReader",
    "SinicaTreebankCorpusReader",
    "BracketParseCorpusReader",
    "IndianCorpusReader",
    "ToolboxCorpusReader",
    "TimitCorpusReader",
    "YCOECorpusReader",
    "MacMorphoCorpusReader",
    "SyntaxCorpusReader",
    "AlpinoCorpusReader",
    "RTECorpusReader",
    "StringCategoryCorpusReader",
    "EuroparlCorpusReader",
    "CategorizedBracketParseCorpusReader",
    "CategorizedTaggedCorpusReader",
    "CategorizedPlaintextCorpusReader",
    "PortugueseCategorizedPlaintextCorpusReader",
    "tagged_treebank_para_block_reader",
    "PropbankCorpusReader",
    "VerbnetCorpusReader",
    "BNCCorpusReader",
    "ConllCorpusReader",
    "XMLCorpusReader",
    "NPSChatCorpusReader",
    "SwadeshCorpusReader",
    "WordNetCorpusReader",
    "WordNetICCorpusReader",
    "SwitchboardCorpusReader",
    "DependencyCorpusReader",
    "NombankCorpusReader",
    "IPIPANCorpusReader",
    "Pl196xCorpusReader",
    "TEICorpusView",
    "KNBCorpusReader",
    "ChasenCorpusReader",
    "CHILDESCorpusReader",
    "AlignedCorpusReader",
    "TimitTaggedCorpusReader",
    "LinThesaurusCorpusReader",
    "SemcorCorpusReader",
    "FramenetCorpusReader",
    "UdhrCorpusReader",
    "BNCCorpusReader",
    "SentiWordNetCorpusReader",
    "SentiSynset",
    "TwitterCorpusReader",
    "NKJPCorpusReader",
    "CrubadanCorpusReader",
    "MTECorpusReader",
    "ReviewsCorpusReader",
    "OpinionLexiconCorpusReader",
    "ProsConsCorpusReader",
    "CategorizedSentencesCorpusReader",
    "ComparativeSentencesCorpusReader",
    "PanLexLiteCorpusReader",
    "NonbreakingPrefixesCorpusReader",
    "UnicharsCorpusReader",
    "MWAPPDBCorpusReader",
    "PanlexSwadeshCorpusReader",
    "BCP47CorpusReader",
]

# === NexusCore/openenv\Lib\site-packages\numpy\_core\__init__.py ===
"""
Contains the core of NumPy: ndarray, ufuncs, dtypes, etc.

Please note that this module is private.  All functions and objects
are available in the main ``numpy`` namespace - use that instead.

"""

import os

from numpy.version import version as __version__

# disables OpenBLAS affinity setting of the main thread that limits
# python threads or processes to one core
env_added = []
for envkey in ['OPENBLAS_MAIN_FREE', 'GOTOBLAS_MAIN_FREE']:
    if envkey not in os.environ:
        os.environ[envkey] = '1'
        env_added.append(envkey)

try:
    from . import multiarray
except ImportError as exc:
    import sys
    msg = """

IMPORTANT: PLEASE READ THIS FOR ADVICE ON HOW TO SOLVE THIS ISSUE!

Importing the numpy C-extensions failed. This error can happen for
many reasons, often due to issues with your setup or how NumPy was
installed.

We have compiled some common reasons and troubleshooting tips at:

    https://numpy.org/devdocs/user/troubleshooting-importerror.html

Please note and check the following:

  * The Python version is: Python%d.%d from "%s"
  * The NumPy version is: "%s"

and make sure that they are the versions you expect.
Please carefully study the documentation linked above for further help.

Original error was: %s
""" % (sys.version_info[0], sys.version_info[1], sys.executable,
        __version__, exc)
    raise ImportError(msg) from exc
finally:
    for envkey in env_added:
        del os.environ[envkey]
del envkey
del env_added
del os

from . import umath

# Check that multiarray,umath are pure python modules wrapping
# _multiarray_umath and not either of the old c-extension modules
if not (hasattr(multiarray, '_multiarray_umath') and
        hasattr(umath, '_multiarray_umath')):
    import sys
    path = sys.modules['numpy'].__path__
    msg = ("Something is wrong with the numpy installation. "
        "While importing we detected an older version of "
        "numpy in {}. One method of fixing this is to repeatedly uninstall "
        "numpy until none is found, then reinstall this version.")
    raise ImportError(msg.format(path))

from . import numerictypes as nt
from .numerictypes import sctypeDict, sctypes

multiarray.set_typeDict(nt.sctypeDict)
from . import (
    _machar,
    einsumfunc,
    fromnumeric,
    function_base,
    getlimits,
    numeric,
    shape_base,
)
from .einsumfunc import *
from .fromnumeric import *
from .function_base import *
from .getlimits import *

# Note: module name memmap is overwritten by a class with same name
from .memmap import *
from .numeric import *
from .records import recarray, record
from .shape_base import *

del nt

# do this after everything else, to minimize the chance of this misleadingly
# appearing in an import-time traceback
# add these for module-freeze analysis (like PyInstaller)
from . import (
    _add_newdocs,
    _add_newdocs_scalars,
    _dtype,
    _dtype_ctypes,
    _internal,
    _methods,
)
from .numeric import absolute as abs

acos = numeric.arccos
acosh = numeric.arccosh
asin = numeric.arcsin
asinh = numeric.arcsinh
atan = numeric.arctan
atanh = numeric.arctanh
atan2 = numeric.arctan2
concat = numeric.concatenate
bitwise_left_shift = numeric.left_shift
bitwise_invert = numeric.invert
bitwise_right_shift = numeric.right_shift
permute_dims = numeric.transpose
pow = numeric.power

__all__ = [
    "abs", "acos", "acosh", "asin", "asinh", "atan", "atanh", "atan2",
    "bitwise_invert", "bitwise_left_shift", "bitwise_right_shift", "concat",
    "pow", "permute_dims", "memmap", "sctypeDict", "record", "recarray"
]
__all__ += numeric.__all__
__all__ += function_base.__all__
__all__ += getlimits.__all__
__all__ += shape_base.__all__
__all__ += einsumfunc.__all__


def _ufunc_reduce(func):
    # Report the `__name__`. pickle will try to find the module. Note that
    # pickle supports for this `__name__` to be a `__qualname__`. It may
    # make sense to add a `__qualname__` to ufuncs, to allow this more
    # explicitly (Numba has ufuncs as attributes).
    # See also: https://github.com/dask/distributed/issues/3450
    return func.__name__


def _DType_reconstruct(scalar_type):
    # This is a work-around to pickle type(np.dtype(np.float64)), etc.
    # and it should eventually be replaced with a better solution, e.g. when
    # DTypes become HeapTypes.
    return type(dtype(scalar_type))


def _DType_reduce(DType):
    # As types/classes, most DTypes can simply be pickled by their name:
    if not DType._legacy or DType.__module__ == "numpy.dtypes":
        return DType.__name__

    # However, user defined legacy dtypes (like rational) do not end up in
    # `numpy.dtypes` as module and do not have a public class at all.
    # For these, we pickle them by reconstructing them from the scalar type:
    scalar_type = DType.type
    return _DType_reconstruct, (scalar_type,)


def __getattr__(name):
    # Deprecated 2022-11-22, NumPy 1.25.
    if name == "MachAr":
        import warnings
        warnings.warn(
            "The `np._core.MachAr` is considered private API (NumPy 1.24)",
            DeprecationWarning, stacklevel=2,
        )
        return _machar.MachAr
    raise AttributeError(f"Module {__name__!r} has no attribute {name!r}")


import copyreg

copyreg.pickle(ufunc, _ufunc_reduce)
copyreg.pickle(type(dtype), _DType_reduce, _DType_reconstruct)

# Unclutter namespace (must keep _*_reconstruct for unpickling)
del copyreg, _ufunc_reduce, _DType_reduce

from numpy._pytesttester import PytestTester

test = PytestTester(__name__)
del PytestTester

# === NexusCore/openenv\Lib\site-packages\openai\types\moderation.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Optional
from typing_extensions import Literal

from pydantic import Field as FieldInfo

from .._models import BaseModel

__all__ = ["Moderation", "Categories", "CategoryAppliedInputTypes", "CategoryScores"]


class Categories(BaseModel):
    harassment: bool
    """
    Content that expresses, incites, or promotes harassing language towards any
    target.
    """

    harassment_threatening: bool = FieldInfo(alias="harassment/threatening")
    """
    Harassment content that also includes violence or serious harm towards any
    target.
    """

    hate: bool
    """
    Content that expresses, incites, or promotes hate based on race, gender,
    ethnicity, religion, nationality, sexual orientation, disability status, or
    caste. Hateful content aimed at non-protected groups (e.g., chess players) is
    harassment.
    """

    hate_threatening: bool = FieldInfo(alias="hate/threatening")
    """
    Hateful content that also includes violence or serious harm towards the targeted
    group based on race, gender, ethnicity, religion, nationality, sexual
    orientation, disability status, or caste.
    """

    illicit: Optional[bool] = None
    """
    Content that includes instructions or advice that facilitate the planning or
    execution of wrongdoing, or that gives advice or instruction on how to commit
    illicit acts. For example, "how to shoplift" would fit this category.
    """

    illicit_violent: Optional[bool] = FieldInfo(alias="illicit/violent", default=None)
    """
    Content that includes instructions or advice that facilitate the planning or
    execution of wrongdoing that also includes violence, or that gives advice or
    instruction on the procurement of any weapon.
    """

    self_harm: bool = FieldInfo(alias="self-harm")
    """
    Content that promotes, encourages, or depicts acts of self-harm, such as
    suicide, cutting, and eating disorders.
    """

    self_harm_instructions: bool = FieldInfo(alias="self-harm/instructions")
    """
    Content that encourages performing acts of self-harm, such as suicide, cutting,
    and eating disorders, or that gives instructions or advice on how to commit such
    acts.
    """

    self_harm_intent: bool = FieldInfo(alias="self-harm/intent")
    """
    Content where the speaker expresses that they are engaging or intend to engage
    in acts of self-harm, such as suicide, cutting, and eating disorders.
    """

    sexual: bool
    """
    Content meant to arouse sexual excitement, such as the description of sexual
    activity, or that promotes sexual services (excluding sex education and
    wellness).
    """

    sexual_minors: bool = FieldInfo(alias="sexual/minors")
    """Sexual content that includes an individual who is under 18 years old."""

    violence: bool
    """Content that depicts death, violence, or physical injury."""

    violence_graphic: bool = FieldInfo(alias="violence/graphic")
    """Content that depicts death, violence, or physical injury in graphic detail."""


class CategoryAppliedInputTypes(BaseModel):
    harassment: List[Literal["text"]]
    """The applied input type(s) for the category 'harassment'."""

    harassment_threatening: List[Literal["text"]] = FieldInfo(alias="harassment/threatening")
    """The applied input type(s) for the category 'harassment/threatening'."""

    hate: List[Literal["text"]]
    """The applied input type(s) for the category 'hate'."""

    hate_threatening: List[Literal["text"]] = FieldInfo(alias="hate/threatening")
    """The applied input type(s) for the category 'hate/threatening'."""

    illicit: List[Literal["text"]]
    """The applied input type(s) for the category 'illicit'."""

    illicit_violent: List[Literal["text"]] = FieldInfo(alias="illicit/violent")
    """The applied input type(s) for the category 'illicit/violent'."""

    self_harm: List[Literal["text", "image"]] = FieldInfo(alias="self-harm")
    """The applied input type(s) for the category 'self-harm'."""

    self_harm_instructions: List[Literal["text", "image"]] = FieldInfo(alias="self-harm/instructions")
    """The applied input type(s) for the category 'self-harm/instructions'."""

    self_harm_intent: List[Literal["text", "image"]] = FieldInfo(alias="self-harm/intent")
    """The applied input type(s) for the category 'self-harm/intent'."""

    sexual: List[Literal["text", "image"]]
    """The applied input type(s) for the category 'sexual'."""

    sexual_minors: List[Literal["text"]] = FieldInfo(alias="sexual/minors")
    """The applied input type(s) for the category 'sexual/minors'."""

    violence: List[Literal["text", "image"]]
    """The applied input type(s) for the category 'violence'."""

    violence_graphic: List[Literal["text", "image"]] = FieldInfo(alias="violence/graphic")
    """The applied input type(s) for the category 'violence/graphic'."""


class CategoryScores(BaseModel):
    harassment: float
    """The score for the category 'harassment'."""

    harassment_threatening: float = FieldInfo(alias="harassment/threatening")
    """The score for the category 'harassment/threatening'."""

    hate: float
    """The score for the category 'hate'."""

    hate_threatening: float = FieldInfo(alias="hate/threatening")
    """The score for the category 'hate/threatening'."""

    illicit: float
    """The score for the category 'illicit'."""

    illicit_violent: float = FieldInfo(alias="illicit/violent")
    """The score for the category 'illicit/violent'."""

    self_harm: float = FieldInfo(alias="self-harm")
    """The score for the category 'self-harm'."""

    self_harm_instructions: float = FieldInfo(alias="self-harm/instructions")
    """The score for the category 'self-harm/instructions'."""

    self_harm_intent: float = FieldInfo(alias="self-harm/intent")
    """The score for the category 'self-harm/intent'."""

    sexual: float
    """The score for the category 'sexual'."""

    sexual_minors: float = FieldInfo(alias="sexual/minors")
    """The score for the category 'sexual/minors'."""

    violence: float
    """The score for the category 'violence'."""

    violence_graphic: float = FieldInfo(alias="violence/graphic")
    """The score for the category 'violence/graphic'."""


class Moderation(BaseModel):
    categories: Categories
    """A list of the categories, and whether they are flagged or not."""

    category_applied_input_types: CategoryAppliedInputTypes
    """
    A list of the categories along with the input type(s) that the score applies to.
    """

    category_scores: CategoryScores
    """A list of the categories along with their scores as predicted by model."""

    flagged: bool
    """Whether any of the below categories are flagged."""

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\support\wait.py ===
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

import time
from typing import Callable, Generic, Literal, Optional, Tuple, Type, TypeVar, Union

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.types import WaitExcTypes
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

POLL_FREQUENCY: float = 0.5  # How long to sleep in between calls to the method
IGNORED_EXCEPTIONS: Tuple[Type[Exception]] = (NoSuchElementException,)  # default to be ignored.

D = TypeVar("D", bound=Union[WebDriver, WebElement])
T = TypeVar("T")


class WebDriverWait(Generic[D]):
    def __init__(
        self,
        driver: D,
        timeout: float,
        poll_frequency: float = POLL_FREQUENCY,
        ignored_exceptions: Optional[WaitExcTypes] = None,
    ):
        """Constructor, takes a WebDriver instance and timeout in seconds.

        Attributes:
        -----------
        driver
            - Instance of WebDriver (Ie, Firefox, Chrome or Remote) or
            a WebElement

        timeout
            - Number of seconds before timing out

        poll_frequency
            - Sleep interval between calls
            - By default, it is 0.5 second.

        ignored_exceptions
            - Iterable structure of exception classes ignored during calls.
            - By default, it contains NoSuchElementException only.

        Example:
        --------
        >>> from selenium.webdriver.common.by import By
        >>> from selenium.webdriver.support.wait import WebDriverWait
        >>> from selenium.common.exceptions import ElementNotVisibleException
        >>>
        >>> # Wait until the element is no longer visible
        >>> is_disappeared = WebDriverWait(driver, 30, 1, (ElementNotVisibleException))
        ...     .until_not(lambda x: x.find_element(By.ID, "someId").is_displayed())
        """
        self._driver = driver
        self._timeout = float(timeout)
        self._poll = poll_frequency
        # avoid the divide by zero
        if self._poll == 0:
            self._poll = POLL_FREQUENCY
        exceptions: list = list(IGNORED_EXCEPTIONS)
        if ignored_exceptions:
            try:
                exceptions.extend(iter(ignored_exceptions))
            except TypeError:  # ignored_exceptions is not iterable
                exceptions.append(ignored_exceptions)
        self._ignored_exceptions = tuple(exceptions)

    def __repr__(self) -> str:
        return f'<{type(self).__module__}.{type(self).__name__} (session="{self._driver.session_id}")>'

    def until(self, method: Callable[[D], Union[Literal[False], T]], message: str = "") -> T:
        """Wait until the method returns a value that is not False.

        Calls the method provided with the driver as an argument until the
        return value does not evaluate to ``False``.

        Parameters:
        -----------
        method: callable(WebDriver)
            - A callable object that takes a WebDriver instance as an argument.

        message: str
            - Optional message for :exc:`TimeoutException`

        Return:
        -------
        object: T
            - The result of the last call to `method`

        Raises:
        -------
        TimeoutException
            - If 'method' does not return a truthy value within the WebDriverWait
            object's timeout

        Example:
        --------
        >>> from selenium.webdriver.common.by import By
        >>> from selenium.webdriver.support.ui import WebDriverWait
        >>> from selenium.webdriver.support import expected_conditions as EC

        # Wait until an element is visible on the page
        >>> wait = WebDriverWait(driver, 10)
        >>> element = wait.until(EC.visibility_of_element_located((By.ID, "exampleId")))
        >>> print(element.text)
        """
        screen = None
        stacktrace = None

        end_time = time.monotonic() + self._timeout
        while True:
            try:
                value = method(self._driver)
                if value:
                    return value
            except self._ignored_exceptions as exc:
                screen = getattr(exc, "screen", None)
                stacktrace = getattr(exc, "stacktrace", None)
            if time.monotonic() > end_time:
                break
            time.sleep(self._poll)
        raise TimeoutException(message, screen, stacktrace)

    def until_not(self, method: Callable[[D], T], message: str = "") -> Union[T, Literal[True]]:
        """Wait until the method returns a value that is not False.

        Calls the method provided with the driver as an argument until the
        return value does not evaluate to ``False``.

        Parameters:
        -----------
        method: callable(WebDriver)
            - A callable object that takes a WebDriver instance as an argument.

        message: str
            - Optional message for :exc:`TimeoutException`

        Return:
        -------
        object: T
            - The result of the last call to `method`

        Raises:
        -------
        TimeoutException
            - If 'method' does not return False within the WebDriverWait
            object's timeout

        Example:
        --------
        >>> from selenium.webdriver.common.by import By
        >>> from selenium.webdriver.support.ui import WebDriverWait
        >>> from selenium.webdriver.support import expected_conditions as EC

        # Wait until an element is visible on the page
        >>> wait = WebDriverWait(driver, 10)
        >>> is_disappeared = wait.until_not(EC.visibility_of_element_located((By.ID, "exampleId")))
        """
        end_time = time.monotonic() + self._timeout
        while True:
            try:
                value = method(self._driver)
                if not value:
                    return value
            except self._ignored_exceptions:
                return True
            if time.monotonic() > end_time:
                break
            time.sleep(self._poll)
        raise TimeoutException(message)

# === NexusCore/evaluation\evalplus\evalplus\_experimental\evaluate_coverage.py ===
import argparse
import importlib
import inspect
import multiprocessing
import os
import sys
from io import StringIO
from typing import Any, Callable, List, Union

import coverage

from evalplus.data import get_human_eval_plus
from evalplus.data.utils import to_raw
from evalplus.eval.utils import reliability_guard, swallow_io, time_limit


def construct_inputs_sig(inputs: list) -> str:
    str_builder = ""
    for x in inputs:
        if type(x) == str:
            str_builder += f"'{to_raw(x)}',"
        else:
            str_builder += f"{x},"
    return str_builder[:-1]


class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio
        sys.stdout = self._stdout


def parse_lcov(outputs: List[str], func: Callable, mode: str = "branch"):
    switch, extracted_outputs = False, []
    for line in outputs:
        if switch == False and "tmp_src" in line:
            switch = True
        if switch == True and "end_of_record" in line:
            switch = False
        if switch:
            extracted_outputs.append(line)

    src, start_lineno = inspect.getsourcelines(func)
    end_lineno = start_lineno + len(src) - 1

    if mode == "branch":
        branch, branch_covered = [], []
        for line in extracted_outputs:
            if line.startswith("BRDA"):
                # BRDA format: BR:<lineno>,<blockno>,<branchno>,<taken>
                lineno, blockno, branchno, taken = line[5:].split(",")
                branch_sig = f"BR:{lineno},{blockno},{branchno}"
                branch.append(branch_sig)
                if taken not in ["0", "-"]:
                    branch_covered.append(branch_sig)
        per = 1.0 if len(branch) == 0 else len(branch_covered) / len(branch)
        return per, branch, branch_covered
    else:
        not_covered_lines = []
        for line in extracted_outputs:
            if line.startswith("DA"):
                # DA format: DA:<lineno>,<exec_count>[,...]
                lineno, exec_count = line[3:].split(",")[:2]
                if start_lineno <= int(lineno) <= end_lineno:
                    if exec_count == "0":
                        not_covered_lines.append(int(lineno))
        for lineno in not_covered_lines:
            line = src[lineno - start_lineno]
            if line.strip() != "" and "def" not in line:
                src[lineno - start_lineno] = line[:-1] + "  # Not executed\n"
        return "".join(src)


def test_code_coverage(
    code: str, inputs: List[List[Any]], entry_point: str, mode="branch"
):
    def safety_test(code: str, inputs: List[List[Any]], entry_point: str):
        for input_list in inputs:
            code += f"{entry_point}({construct_inputs_sig(input_list)})\n"
        reliability_guard()
        try:
            with swallow_io():
                with time_limit(1):
                    exec(code, {})
        except:
            sys.exit(1)

    p = multiprocessing.Process(target=safety_test, args=(code, inputs, entry_point))
    p.start()
    p.join()
    safe = p.exitcode == 0
    if p.is_alive():
        p.terminate()
        p.kill()
    if not safe:
        print("Potentially dangerous code, refuse coverage test.")
        return None

    with open("tmp_src.py", "w") as f:
        f.write(code)
    import tmp_src

    importlib.reload(tmp_src)
    func = getattr(tmp_src, f"{entry_point}", None)
    assert func != None, f"{entry_point = } not exist"

    cov = coverage.Coverage(branch=True)
    cov.start()
    with swallow_io():
        for input_list in inputs:
            func(*input_list)
    cov.stop()
    with Capturing() as outputs:
        cov.lcov_report(outfile="-")

    ret = parse_lcov(outputs, func, mode)

    os.remove("tmp_src.py")
    return ret


def test_solution_coverage(
    dataset: str = "HumanEvalPlus",
    task_id: str = "HumanEval/0",
    impl: str = "canonical",
    inputs: Union[str, List[List[Any]]] = "base_input",
    mode: str = "branch",
):
    """
    Parameters:
    * dataset: {None, "HumanEval", "HumanEvalPlus"}
    * task_id: ralated to dataset
    * impl: {"canonical", source code}
    * inputs: {"base_inputs", list}
    * mode: {"branch"}, will support "line" for coverage-guided LLM test generation
    """
    if "HumanEval" in dataset:
        problems, problem = get_human_eval_plus(), None
        for p in problems:
            if p["task_id"] == task_id:
                problem = p
        assert problem != None, f"invalid {task_id = }"
        entry_point = problem["entry_point"]
        code = problem["prompt"] + (
            impl if impl != "canonical" else problem["canonical_solution"]
        )
        if inputs == "base_input":
            inputs = problem["base_input"]
    else:
        raise NotImplementedError

    return test_code_coverage(code, inputs, entry_point, mode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", type=str, default="branch", choices=["line", "branch"]
    )
    args = parser.parse_args()

    if args.mode == "branch":
        for i in range(0, 164):
            task_id = f"HumanEval/{i}"
            branch, branch_covered = test_solution_coverage(
                dataset="HumanEval", task_id=task_id, mode="branch"
            )
            per = 1.0 if len(branch) == 0 else len(branch_covered) / len(branch)
            if per != 1.0:
                print(i, per, len(branch_covered), len(branch))
    else:
        for i in range(0, 164):
            task_id = f"HumanEval/{i}"
            annotated_code = test_solution_coverage(
                dataset="HumanEval", task_id=task_id, mode="line"
            )
            if "Not executed" in annotated_code:
                print(f"{task_id = }")
                print(annotated_code)

# === NexusCore/evaluation\evalplus\tools\_experimental\evaluate_coverage.py ===
import argparse
import importlib
import inspect
import multiprocessing
import os
import sys
from io import StringIO
from typing import Any, Callable, List, Union

import coverage

from evalplus.data import get_human_eval_plus
from evalplus.data.utils import to_raw
from evalplus.eval.utils import reliability_guard, swallow_io, time_limit


def construct_inputs_sig(inputs: list) -> str:
    str_builder = ""
    for x in inputs:
        if type(x) == str:
            str_builder += f"'{to_raw(x)}',"
        else:
            str_builder += f"{x},"
    return str_builder[:-1]


class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio
        sys.stdout = self._stdout


def parse_lcov(outputs: List[str], func: Callable, mode: str = "branch"):
    switch, extracted_outputs = False, []
    for line in outputs:
        if switch == False and "tmp_src" in line:
            switch = True
        if switch == True and "end_of_record" in line:
            switch = False
        if switch:
            extracted_outputs.append(line)

    src, start_lineno = inspect.getsourcelines(func)
    end_lineno = start_lineno + len(src) - 1

    if mode == "branch":
        branch, branch_covered = [], []
        for line in extracted_outputs:
            if line.startswith("BRDA"):
                # BRDA format: BR:<lineno>,<blockno>,<branchno>,<taken>
                lineno, blockno, branchno, taken = line[5:].split(",")
                branch_sig = f"BR:{lineno},{blockno},{branchno}"
                branch.append(branch_sig)
                if taken not in ["0", "-"]:
                    branch_covered.append(branch_sig)
        per = 1.0 if len(branch) == 0 else len(branch_covered) / len(branch)
        return per, branch, branch_covered
    else:
        not_covered_lines = []
        for line in extracted_outputs:
            if line.startswith("DA"):
                # DA format: DA:<lineno>,<exec_count>[,...]
                lineno, exec_count = line[3:].split(",")[:2]
                if start_lineno <= int(lineno) <= end_lineno:
                    if exec_count == "0":
                        not_covered_lines.append(int(lineno))
        for lineno in not_covered_lines:
            line = src[lineno - start_lineno]
            if line.strip() != "" and "def" not in line:
                src[lineno - start_lineno] = line[:-1] + "  # Not executed\n"
        return "".join(src)


def test_code_coverage(
    code: str, inputs: List[List[Any]], entry_point: str, mode="branch"
):
    def safety_test(code: str, inputs: List[List[Any]], entry_point: str):
        for input_list in inputs:
            code += f"{entry_point}({construct_inputs_sig(input_list)})\n"
        reliability_guard()
        try:
            with swallow_io():
                with time_limit(1):
                    exec(code, {})
        except:
            sys.exit(1)

    p = multiprocessing.Process(target=safety_test, args=(code, inputs, entry_point))
    p.start()
    p.join()
    safe = p.exitcode == 0
    if p.is_alive():
        p.terminate()
        p.kill()
    if not safe:
        print("Potentially dangerous code, refuse coverage test.")
        return None

    with open("tmp_src.py", "w") as f:
        f.write(code)
    import tmp_src

    importlib.reload(tmp_src)
    func = getattr(tmp_src, f"{entry_point}", None)
    assert func != None, f"{entry_point = } not exist"

    cov = coverage.Coverage(branch=True)
    cov.start()
    with swallow_io():
        for input_list in inputs:
            func(*input_list)
    cov.stop()
    with Capturing() as outputs:
        cov.lcov_report(outfile="-")

    ret = parse_lcov(outputs, func, mode)

    os.remove("tmp_src.py")
    return ret


def test_solution_coverage(
    dataset: str = "HumanEvalPlus",
    task_id: str = "HumanEval/0",
    impl: str = "canonical",
    inputs: Union[str, List[List[Any]]] = "base_input",
    mode: str = "branch",
):
    """
    Parameters:
    * dataset: {None, "HumanEval", "HumanEvalPlus"}
    * task_id: ralated to dataset
    * impl: {"canonical", source code}
    * inputs: {"base_inputs", list}
    * mode: {"branch"}, will support "line" for coverage-guided LLM test generation
    """
    if "HumanEval" in dataset:
        problems, problem = get_human_eval_plus(), None
        for p in problems:
            if p["task_id"] == task_id:
                problem = p
        assert problem != None, f"invalid {task_id = }"
        entry_point = problem["entry_point"]
        code = problem["prompt"] + (
            impl if impl != "canonical" else problem["canonical_solution"]
        )
        if inputs == "base_input":
            inputs = problem["base_input"]
    else:
        raise NotImplementedError

    return test_code_coverage(code, inputs, entry_point, mode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", type=str, default="branch", choices=["line", "branch"]
    )
    args = parser.parse_args()

    if args.mode == "branch":
        for i in range(0, 164):
            task_id = f"HumanEval/{i}"
            branch, branch_covered = test_solution_coverage(
                dataset="HumanEval", task_id=task_id, mode="branch"
            )
            per = 1.0 if len(branch) == 0 else len(branch_covered) / len(branch)
            if per != 1.0:
                print(i, per, len(branch_covered), len(branch))
    else:
        for i in range(0, 164):
            task_id = f"HumanEval/{i}"
            annotated_code = test_solution_coverage(
                dataset="HumanEval", task_id=task_id, mode="line"
            )
            if "Not executed" in annotated_code:
                print(f"{task_id = }")
                print(annotated_code)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\pyproject.py ===
import importlib.util
import os
import sys
from collections import namedtuple
from typing import Any, List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    from pip._vendor import tomli as tomllib

from pip._vendor.packaging.requirements import InvalidRequirement

from pip._internal.exceptions import (
    InstallationError,
    InvalidPyProjectBuildRequires,
    MissingPyProjectBuildRequires,
)
from pip._internal.utils.packaging import get_requirement


def _is_list_of_str(obj: Any) -> bool:
    return isinstance(obj, list) and all(isinstance(item, str) for item in obj)


def make_pyproject_path(unpacked_source_directory: str) -> str:
    return os.path.join(unpacked_source_directory, "pyproject.toml")


BuildSystemDetails = namedtuple(
    "BuildSystemDetails", ["requires", "backend", "check", "backend_path"]
)


def load_pyproject_toml(
    use_pep517: Optional[bool], pyproject_toml: str, setup_py: str, req_name: str
) -> Optional[BuildSystemDetails]:
    """Load the pyproject.toml file.

    Parameters:
        use_pep517 - Has the user requested PEP 517 processing? None
                     means the user hasn't explicitly specified.
        pyproject_toml - Location of the project's pyproject.toml file
        setup_py - Location of the project's setup.py file
        req_name - The name of the requirement we're processing (for
                   error reporting)

    Returns:
        None if we should use the legacy code path, otherwise a tuple
        (
            requirements from pyproject.toml,
            name of PEP 517 backend,
            requirements we should check are installed after setting
                up the build environment
            directory paths to import the backend from (backend-path),
                relative to the project root.
        )
    """
    has_pyproject = os.path.isfile(pyproject_toml)
    has_setup = os.path.isfile(setup_py)

    if not has_pyproject and not has_setup:
        raise InstallationError(
            f"{req_name} does not appear to be a Python project: "
            f"neither 'setup.py' nor 'pyproject.toml' found."
        )

    if has_pyproject:
        with open(pyproject_toml, encoding="utf-8") as f:
            pp_toml = tomllib.loads(f.read())
        build_system = pp_toml.get("build-system")
    else:
        build_system = None

    # The following cases must use PEP 517
    # We check for use_pep517 being non-None and falsy because that means
    # the user explicitly requested --no-use-pep517.  The value 0 as
    # opposed to False can occur when the value is provided via an
    # environment variable or config file option (due to the quirk of
    # strtobool() returning an integer in pip's configuration code).
    if has_pyproject and not has_setup:
        if use_pep517 is not None and not use_pep517:
            raise InstallationError(
                "Disabling PEP 517 processing is invalid: "
                "project does not have a setup.py"
            )
        use_pep517 = True
    elif build_system and "build-backend" in build_system:
        if use_pep517 is not None and not use_pep517:
            raise InstallationError(
                "Disabling PEP 517 processing is invalid: "
                "project specifies a build backend of {} "
                "in pyproject.toml".format(build_system["build-backend"])
            )
        use_pep517 = True

    # If we haven't worked out whether to use PEP 517 yet,
    # and the user hasn't explicitly stated a preference,
    # we do so if the project has a pyproject.toml file
    # or if we cannot import setuptools or wheels.

    # We fallback to PEP 517 when without setuptools or without the wheel package,
    # so setuptools can be installed as a default build backend.
    # For more info see:
    # https://discuss.python.org/t/pip-without-setuptools-could-the-experience-be-improved/11810/9
    # https://github.com/pypa/pip/issues/8559
    elif use_pep517 is None:
        use_pep517 = (
            has_pyproject
            or not importlib.util.find_spec("setuptools")
            or not importlib.util.find_spec("wheel")
        )

    # At this point, we know whether we're going to use PEP 517.
    assert use_pep517 is not None

    # If we're using the legacy code path, there is nothing further
    # for us to do here.
    if not use_pep517:
        return None

    if build_system is None:
        # Either the user has a pyproject.toml with no build-system
        # section, or the user has no pyproject.toml, but has opted in
        # explicitly via --use-pep517.
        # In the absence of any explicit backend specification, we
        # assume the setuptools backend that most closely emulates the
        # traditional direct setup.py execution, and require wheel and
        # a version of setuptools that supports that backend.

        build_system = {
            "requires": ["setuptools>=40.8.0"],
            "build-backend": "setuptools.build_meta:__legacy__",
        }

    # If we're using PEP 517, we have build system information (either
    # from pyproject.toml, or defaulted by the code above).
    # Note that at this point, we do not know if the user has actually
    # specified a backend, though.
    assert build_system is not None

    # Ensure that the build-system section in pyproject.toml conforms
    # to PEP 518.

    # Specifying the build-system table but not the requires key is invalid
    if "requires" not in build_system:
        raise MissingPyProjectBuildRequires(package=req_name)

    # Error out if requires is not a list of strings
    requires = build_system["requires"]
    if not _is_list_of_str(requires):
        raise InvalidPyProjectBuildRequires(
            package=req_name,
            reason="It is not a list of strings.",
        )

    # Each requirement must be valid as per PEP 508
    for requirement in requires:
        try:
            get_requirement(requirement)
        except InvalidRequirement as error:
            raise InvalidPyProjectBuildRequires(
                package=req_name,
                reason=f"It contains an invalid requirement: {requirement!r}",
            ) from error

    backend = build_system.get("build-backend")
    backend_path = build_system.get("backend-path", [])
    check: List[str] = []
    if backend is None:
        # If the user didn't specify a backend, we assume they want to use
        # the setuptools backend. But we can't be sure they have included
        # a version of setuptools which supplies the backend. So we
        # make a note to check that this requirement is present once
        # we have set up the environment.
        # This is quite a lot of work to check for a very specific case. But
        # the problem is, that case is potentially quite common - projects that
        # adopted PEP 518 early for the ability to specify requirements to
        # execute setup.py, but never considered needing to mention the build
        # tools themselves. The original PEP 518 code had a similar check (but
        # implemented in a different way).
        backend = "setuptools.build_meta:__legacy__"
        check = ["setuptools>=40.8.0"]

    return BuildSystemDetails(requires, backend, check, backend_path)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\formatters\svg.py ===
"""
    pygments.formatters.svg
    ~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for SVG output.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.token import Comment
from pip._vendor.pygments.util import get_bool_opt, get_int_opt

__all__ = ['SvgFormatter']


def escape_html(text):
    """Escape &, <, > as well as single and double quotes for HTML."""
    return text.replace('&', '&amp;').  \
                replace('<', '&lt;').   \
                replace('>', '&gt;').   \
                replace('"', '&quot;'). \
                replace("'", '&#39;')


class2style = {}

class SvgFormatter(Formatter):
    """
    Format tokens as an SVG graphics file.  This formatter is still experimental.
    Each line of code is a ``<text>`` element with explicit ``x`` and ``y``
    coordinates containing ``<tspan>`` elements with the individual token styles.

    By default, this formatter outputs a full SVG document including doctype
    declaration and the ``<svg>`` root element.

    .. versionadded:: 0.9

    Additional options accepted:

    `nowrap`
        Don't wrap the SVG ``<text>`` elements in ``<svg><g>`` elements and
        don't add a XML declaration and a doctype.  If true, the `fontfamily`
        and `fontsize` options are ignored.  Defaults to ``False``.

    `fontfamily`
        The value to give the wrapping ``<g>`` element's ``font-family``
        attribute, defaults to ``"monospace"``.

    `fontsize`
        The value to give the wrapping ``<g>`` element's ``font-size``
        attribute, defaults to ``"14px"``.

    `linenos`
        If ``True``, add line numbers (default: ``False``).

    `linenostart`
        The line number for the first line (default: ``1``).

    `linenostep`
        If set to a number n > 1, only every nth line number is printed.

    `linenowidth`
        Maximum width devoted to line numbers (default: ``3*ystep``, sufficient
        for up to 4-digit line numbers. Increase width for longer code blocks).

    `xoffset`
        Starting offset in X direction, defaults to ``0``.

    `yoffset`
        Starting offset in Y direction, defaults to the font size if it is given
        in pixels, or ``20`` else.  (This is necessary since text coordinates
        refer to the text baseline, not the top edge.)

    `ystep`
        Offset to add to the Y coordinate for each subsequent line.  This should
        roughly be the text size plus 5.  It defaults to that value if the text
        size is given in pixels, or ``25`` else.

    `spacehack`
        Convert spaces in the source to ``&#160;``, which are non-breaking
        spaces.  SVG provides the ``xml:space`` attribute to control how
        whitespace inside tags is handled, in theory, the ``preserve`` value
        could be used to keep all whitespace as-is.  However, many current SVG
        viewers don't obey that rule, so this option is provided as a workaround
        and defaults to ``True``.
    """
    name = 'SVG'
    aliases = ['svg']
    filenames = ['*.svg']

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.nowrap = get_bool_opt(options, 'nowrap', False)
        self.fontfamily = options.get('fontfamily', 'monospace')
        self.fontsize = options.get('fontsize', '14px')
        self.xoffset = get_int_opt(options, 'xoffset', 0)
        fs = self.fontsize.strip()
        if fs.endswith('px'):
            fs = fs[:-2].strip()
        try:
            int_fs = int(fs)
        except ValueError:
            int_fs = 20
        self.yoffset = get_int_opt(options, 'yoffset', int_fs)
        self.ystep = get_int_opt(options, 'ystep', int_fs + 5)
        self.spacehack = get_bool_opt(options, 'spacehack', True)
        self.linenos = get_bool_opt(options,'linenos',False)
        self.linenostart = get_int_opt(options,'linenostart',1)
        self.linenostep = get_int_opt(options,'linenostep',1)
        self.linenowidth = get_int_opt(options,'linenowidth', 3*self.ystep)
        self._stylecache = {}

    def format_unencoded(self, tokensource, outfile):
        """
        Format ``tokensource``, an iterable of ``(tokentype, tokenstring)``
        tuples and write it into ``outfile``.

        For our implementation we put all lines in their own 'line group'.
        """
        x = self.xoffset
        y = self.yoffset
        if not self.nowrap:
            if self.encoding:
                outfile.write(f'<?xml version="1.0" encoding="{self.encoding}"?>\n')
            else:
                outfile.write('<?xml version="1.0"?>\n')
            outfile.write('<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.0//EN" '
                          '"http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/'
                          'svg10.dtd">\n')
            outfile.write('<svg xmlns="http://www.w3.org/2000/svg">\n')
            outfile.write(f'<g font-family="{self.fontfamily}" font-size="{self.fontsize}">\n')

        counter = self.linenostart
        counter_step = self.linenostep
        counter_style = self._get_style(Comment)
        line_x = x

        if self.linenos:
            if counter % counter_step == 0:
                outfile.write(f'<text x="{x+self.linenowidth}" y="{y}" {counter_style} text-anchor="end">{counter}</text>')
            line_x += self.linenowidth + self.ystep
            counter += 1

        outfile.write(f'<text x="{line_x}" y="{y}" xml:space="preserve">')
        for ttype, value in tokensource:
            style = self._get_style(ttype)
            tspan = style and '<tspan' + style + '>' or ''
            tspanend = tspan and '</tspan>' or ''
            value = escape_html(value)
            if self.spacehack:
                value = value.expandtabs().replace(' ', '&#160;')
            parts = value.split('\n')
            for part in parts[:-1]:
                outfile.write(tspan + part + tspanend)
                y += self.ystep
                outfile.write('</text>\n')
                if self.linenos and counter % counter_step == 0:
                    outfile.write(f'<text x="{x+self.linenowidth}" y="{y}" text-anchor="end" {counter_style}>{counter}</text>')

                counter += 1
                outfile.write(f'<text x="{line_x}" y="{y}" ' 'xml:space="preserve">')
            outfile.write(tspan + parts[-1] + tspanend)
        outfile.write('</text>')

        if not self.nowrap:
            outfile.write('</g></svg>\n')

    def _get_style(self, tokentype):
        if tokentype in self._stylecache:
            return self._stylecache[tokentype]
        otokentype = tokentype
        while not self.style.styles_token(tokentype):
            tokentype = tokentype.parent
        value = self.style.style_for_token(tokentype)
        result = ''
        if value['color']:
            result = ' fill="#' + value['color'] + '"'
        if value['bold']:
            result += ' font-weight="bold"'
        if value['italic']:
            result += ' font-style="italic"'
        self._stylecache[otokentype] = result
        return result

# === NexusCore/openenv\Lib\site-packages\setuptools\depends.py ===
from __future__ import annotations

import contextlib
import dis
import marshal
import sys
from types import CodeType
from typing import Any, Literal, TypeVar

from packaging.version import Version

from . import _imp
from ._imp import PY_COMPILED, PY_FROZEN, PY_SOURCE, find_module

_T = TypeVar("_T")

__all__ = ['Require', 'find_module']


class Require:
    """A prerequisite to building or installing a distribution"""

    def __init__(
        self,
        name,
        requested_version,
        module,
        homepage: str = '',
        attribute=None,
        format=None,
    ) -> None:
        if format is None and requested_version is not None:
            format = Version

        if format is not None:
            requested_version = format(requested_version)
            if attribute is None:
                attribute = '__version__'

        self.__dict__.update(locals())
        del self.self

    def full_name(self):
        """Return full package/distribution name, w/version"""
        if self.requested_version is not None:
            return f'{self.name}-{self.requested_version}'
        return self.name

    def version_ok(self, version):
        """Is 'version' sufficiently up-to-date?"""
        return (
            self.attribute is None
            or self.format is None
            or str(version) != "unknown"
            and self.format(version) >= self.requested_version
        )

    def get_version(
        self, paths=None, default: _T | Literal["unknown"] = "unknown"
    ) -> _T | Literal["unknown"] | None | Any:
        """Get version number of installed module, 'None', or 'default'

        Search 'paths' for module.  If not found, return 'None'.  If found,
        return the extracted version attribute, or 'default' if no version
        attribute was specified, or the value cannot be determined without
        importing the module.  The version is formatted according to the
        requirement's version format (if any), unless it is 'None' or the
        supplied 'default'.
        """

        if self.attribute is None:
            try:
                f, _p, _i = find_module(self.module, paths)
            except ImportError:
                return None
            if f:
                f.close()
            return default

        v = get_module_constant(self.module, self.attribute, default, paths)

        if v is not None and v is not default and self.format is not None:
            return self.format(v)

        return v

    def is_present(self, paths=None):
        """Return true if dependency is present on 'paths'"""
        return self.get_version(paths) is not None

    def is_current(self, paths=None):
        """Return true if dependency is present and up-to-date on 'paths'"""
        version = self.get_version(paths)
        if version is None:
            return False
        return self.version_ok(str(version))


def maybe_close(f):
    @contextlib.contextmanager
    def empty():
        yield
        return

    if not f:
        return empty()

    return contextlib.closing(f)


# Some objects are not available on some platforms.
# XXX it'd be better to test assertions about bytecode instead.
if not sys.platform.startswith('java') and sys.platform != 'cli':

    def get_module_constant(
        module, symbol, default: _T | int = -1, paths=None
    ) -> _T | int | None | Any:
        """Find 'module' by searching 'paths', and extract 'symbol'

        Return 'None' if 'module' does not exist on 'paths', or it does not define
        'symbol'.  If the module defines 'symbol' as a constant, return the
        constant.  Otherwise, return 'default'."""

        try:
            f, path, (_suffix, _mode, kind) = info = find_module(module, paths)
        except ImportError:
            # Module doesn't exist
            return None

        with maybe_close(f):
            if kind == PY_COMPILED:
                f.read(8)  # skip magic & date
                code = marshal.load(f)
            elif kind == PY_FROZEN:
                code = _imp.get_frozen_object(module, paths)
            elif kind == PY_SOURCE:
                code = compile(f.read(), path, 'exec')
            else:
                # Not something we can parse; we'll have to import it.  :(
                imported = _imp.get_module(module, paths, info)
                return getattr(imported, symbol, None)

        return extract_constant(code, symbol, default)

    def extract_constant(
        code: CodeType, symbol: str, default: _T | int = -1
    ) -> _T | int | None | Any:
        """Extract the constant value of 'symbol' from 'code'

        If the name 'symbol' is bound to a constant value by the Python code
        object 'code', return that value.  If 'symbol' is bound to an expression,
        return 'default'.  Otherwise, return 'None'.

        Return value is based on the first assignment to 'symbol'.  'symbol' must
        be a global, or at least a non-"fast" local in the code block.  That is,
        only 'STORE_NAME' and 'STORE_GLOBAL' opcodes are checked, and 'symbol'
        must be present in 'code.co_names'.
        """
        if symbol not in code.co_names:
            # name's not there, can't possibly be an assignment
            return None

        name_idx = list(code.co_names).index(symbol)

        STORE_NAME = dis.opmap['STORE_NAME']
        STORE_GLOBAL = dis.opmap['STORE_GLOBAL']
        LOAD_CONST = dis.opmap['LOAD_CONST']

        const = default

        for byte_code in dis.Bytecode(code):
            op = byte_code.opcode
            arg = byte_code.arg

            if op == LOAD_CONST:
                assert arg is not None
                const = code.co_consts[arg]
            elif arg == name_idx and (op == STORE_NAME or op == STORE_GLOBAL):
                return const
            else:
                const = default

        return None

    __all__ += ['get_module_constant', 'extract_constant']

# === NexusCore/openenv\Lib\site-packages\setuptools\glob.py ===
"""
Filename globbing utility. Mostly a copy of `glob` from Python 3.5.

Changes include:
 * `yield from` and PEP3102 `*` removed.
 * Hidden files are not ignored.
"""

from __future__ import annotations

import fnmatch
import os
import re
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, AnyStr, overload

if TYPE_CHECKING:
    from _typeshed import BytesPath, StrOrBytesPath, StrPath

__all__ = ["glob", "iglob", "escape"]


def glob(pathname: AnyStr, recursive: bool = False) -> list[AnyStr]:
    """Return a list of paths matching a pathname pattern.

    The pattern may contain simple shell-style wildcards a la
    fnmatch. However, unlike fnmatch, filenames starting with a
    dot are special cases that are not matched by '*' and '?'
    patterns.

    If recursive is true, the pattern '**' will match any files and
    zero or more directories and subdirectories.
    """
    return list(iglob(pathname, recursive=recursive))


def iglob(pathname: AnyStr, recursive: bool = False) -> Iterator[AnyStr]:
    """Return an iterator which yields the paths matching a pathname pattern.

    The pattern may contain simple shell-style wildcards a la
    fnmatch. However, unlike fnmatch, filenames starting with a
    dot are special cases that are not matched by '*' and '?'
    patterns.

    If recursive is true, the pattern '**' will match any files and
    zero or more directories and subdirectories.
    """
    it = _iglob(pathname, recursive)
    if recursive and _isrecursive(pathname):
        s = next(it)  # skip empty string
        assert not s
    return it


def _iglob(pathname: AnyStr, recursive: bool) -> Iterator[AnyStr]:
    dirname, basename = os.path.split(pathname)
    glob_in_dir = glob2 if recursive and _isrecursive(basename) else glob1

    if not has_magic(pathname):
        if basename:
            if os.path.lexists(pathname):
                yield pathname
        else:
            # Patterns ending with a slash should match only directories
            if os.path.isdir(dirname):
                yield pathname
        return

    if not dirname:
        yield from glob_in_dir(dirname, basename)
        return
    # `os.path.split()` returns the argument itself as a dirname if it is a
    # drive or UNC path.  Prevent an infinite recursion if a drive or UNC path
    # contains magic characters (i.e. r'\\?\C:').
    if dirname != pathname and has_magic(dirname):
        dirs: Iterable[AnyStr] = _iglob(dirname, recursive)
    else:
        dirs = [dirname]
    if not has_magic(basename):
        glob_in_dir = glob0
    for dirname in dirs:
        for name in glob_in_dir(dirname, basename):
            yield os.path.join(dirname, name)


# These 2 helper functions non-recursively glob inside a literal directory.
# They return a list of basenames. `glob1` accepts a pattern while `glob0`
# takes a literal basename (so it only has to check for its existence).


@overload
def glob1(dirname: StrPath, pattern: str) -> list[str]: ...
@overload
def glob1(dirname: BytesPath, pattern: bytes) -> list[bytes]: ...
def glob1(dirname: StrOrBytesPath, pattern: str | bytes) -> list[str] | list[bytes]:
    if not dirname:
        if isinstance(pattern, bytes):
            dirname = os.curdir.encode('ASCII')
        else:
            dirname = os.curdir
    try:
        names = os.listdir(dirname)
    except OSError:
        return []
    # mypy false-positives: str or bytes type possibility is always kept in sync
    return fnmatch.filter(names, pattern)  # type: ignore[type-var, return-value]


def glob0(dirname, basename):
    if not basename:
        # `os.path.split()` returns an empty basename for paths ending with a
        # directory separator.  'q*x/' should match only directories.
        if os.path.isdir(dirname):
            return [basename]
    else:
        if os.path.lexists(os.path.join(dirname, basename)):
            return [basename]
    return []


# This helper function recursively yields relative pathnames inside a literal
# directory.


@overload
def glob2(dirname: StrPath, pattern: str) -> Iterator[str]: ...
@overload
def glob2(dirname: BytesPath, pattern: bytes) -> Iterator[bytes]: ...
def glob2(dirname: StrOrBytesPath, pattern: str | bytes) -> Iterator[str | bytes]:
    assert _isrecursive(pattern)
    yield pattern[:0]
    yield from _rlistdir(dirname)


# Recursively yields relative pathnames inside a literal directory.
@overload
def _rlistdir(dirname: StrPath) -> Iterator[str]: ...
@overload
def _rlistdir(dirname: BytesPath) -> Iterator[bytes]: ...
def _rlistdir(dirname: StrOrBytesPath) -> Iterator[str | bytes]:
    if not dirname:
        if isinstance(dirname, bytes):
            dirname = os.curdir.encode('ASCII')
        else:
            dirname = os.curdir
    try:
        names = os.listdir(dirname)
    except OSError:
        return
    for x in names:
        yield x
        # mypy false-positives: str or bytes type possibility is always kept in sync
        path = os.path.join(dirname, x) if dirname else x  # type: ignore[arg-type]
        for y in _rlistdir(path):
            yield os.path.join(x, y)  # type: ignore[arg-type]


magic_check = re.compile('([*?[])')
magic_check_bytes = re.compile(b'([*?[])')


def has_magic(s: str | bytes) -> bool:
    if isinstance(s, bytes):
        return magic_check_bytes.search(s) is not None
    else:
        return magic_check.search(s) is not None


def _isrecursive(pattern: str | bytes) -> bool:
    if isinstance(pattern, bytes):
        return pattern == b'**'
    else:
        return pattern == '**'


def escape(pathname):
    """Escape all special characters."""
    # Escaping is done by wrapping any of "*?[" between square brackets.
    # Metacharacters do not work in the drive part and shouldn't be escaped.
    drive, pathname = os.path.splitdrive(pathname)
    if isinstance(pathname, bytes):
        pathname = magic_check_bytes.sub(rb'[\1]', pathname)
    else:
        pathname = magic_check.sub(r'[\1]', pathname)
    return drive + pathname

# === NexusCore/openenv\Lib\site-packages\stack_data\utils.py ===
import ast
import itertools
import types
from collections import OrderedDict, Counter, defaultdict
from types import FrameType, TracebackType
from typing import (
    Iterator, List, Tuple, Iterable, Callable, Union,
    TypeVar, Mapping,
)

from asttokens import ASTText

T = TypeVar('T')
R = TypeVar('R')


def truncate(seq, max_length: int, middle):
    if len(seq) > max_length:
        right = (max_length - len(middle)) // 2
        left = max_length - len(middle) - right
        seq = seq[:left] + middle + seq[-right:]
    return seq


def unique_in_order(it: Iterable[T]) -> List[T]:
    return list(OrderedDict.fromkeys(it))


def line_range(atok: ASTText, node: ast.AST) -> Tuple[int, int]:
    """
    Returns a pair of numbers representing a half open range
    (i.e. suitable as arguments to the `range()` builtin)
    of line numbers of the given AST nodes.
    """
    if isinstance(node, getattr(ast, "match_case", ())):
        start, _end = line_range(atok, node.pattern)
        _start, end = line_range(atok, node.body[-1])
        return start, end
    else:
        (start, _), (end, _) = atok.get_text_positions(node, padded=False)
        return start, end + 1


def highlight_unique(lst: List[T]) -> Iterator[Tuple[T, bool]]:
    counts = Counter(lst)

    for is_common, group in itertools.groupby(lst, key=lambda x: counts[x] > 3):
        if is_common:
            group = list(group)
            highlighted = [False] * len(group)

            def highlight_index(f):
                try:
                    i = f()
                except ValueError:
                    return None
                highlighted[i] = True
                return i

            for item in set(group):
                first = highlight_index(lambda: group.index(item))
                if first is not None:
                    highlight_index(lambda: group.index(item, first + 1))
                highlight_index(lambda: -1 - group[::-1].index(item))
        else:
            highlighted = itertools.repeat(True)

        yield from zip(group, highlighted)


def identity(x: T) -> T:
    return x


def collapse_repeated(lst, *, collapser, mapper=identity, key=identity):
    keyed = list(map(key, lst))
    for is_highlighted, group in itertools.groupby(
            zip(lst, highlight_unique(keyed)),
            key=lambda t: t[1][1],
    ):
        original_group, highlighted_group = zip(*group)
        if is_highlighted:
            yield from map(mapper, original_group)
        else:
            keyed_group, _ = zip(*highlighted_group)
            yield collapser(list(original_group), list(keyed_group))


def is_frame(frame_or_tb: Union[FrameType, TracebackType]) -> bool:
    assert_(isinstance(frame_or_tb, (types.FrameType, types.TracebackType)))
    return isinstance(frame_or_tb, (types.FrameType,))


def iter_stack(frame_or_tb: Union[FrameType, TracebackType]) -> Iterator[Union[FrameType, TracebackType]]:
    current: Union[FrameType, TracebackType, None] = frame_or_tb
    while current:
        yield current
        if is_frame(current):
            current = current.f_back
        else:
            current = current.tb_next


def frame_and_lineno(frame_or_tb: Union[FrameType, TracebackType]) -> Tuple[FrameType, int]:
    if is_frame(frame_or_tb):
        return frame_or_tb, frame_or_tb.f_lineno
    else:
        return frame_or_tb.tb_frame, frame_or_tb.tb_lineno


def group_by_key_func(iterable: Iterable[T], key_func: Callable[[T], R]) -> Mapping[R, List[T]]:
    # noinspection PyUnresolvedReferences
    """
    Create a dictionary from an iterable such that the keys are the result of evaluating a key function on elements
    of the iterable and the values are lists of elements all of which correspond to the key.

    >>> def si(d): return sorted(d.items())
    >>> si(group_by_key_func("a bb ccc d ee fff".split(), len))
    [(1, ['a', 'd']), (2, ['bb', 'ee']), (3, ['ccc', 'fff'])]
    >>> si(group_by_key_func([-1, 0, 1, 3, 6, 8, 9, 2], lambda x: x % 2))
    [(0, [0, 6, 8, 2]), (1, [-1, 1, 3, 9])]
    """
    result = defaultdict(list)
    for item in iterable:
        result[key_func(item)].append(item)
    return result


class cached_property(object):
    """
    A property that is only computed once per instance and then replaces itself
    with an ordinary attribute. Deleting the attribute resets the property.

    Based on https://github.com/pydanny/cached-property/blob/master/cached_property.py
    """

    def __init__(self, func):
        self.__doc__ = func.__doc__
        self.func = func

    def cached_property_wrapper(self, obj, _cls):
        if obj is None:
            return self

        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value

    __get__ = cached_property_wrapper


def _pygmented_with_ranges(formatter, code, ranges):
    import pygments
    from pygments.lexers import get_lexer_by_name

    class MyLexer(type(get_lexer_by_name("python3"))):
        def get_tokens(self, text):
            length = 0
            for ttype, value in super().get_tokens(text):
                if any(start <= length < end for start, end in ranges):
                    ttype = ttype.ExecutingNode
                length += len(value)
                yield ttype, value

    lexer = MyLexer(stripnl=False)
    try:
        highlighted = pygments.highlight(code, lexer, formatter)
    except Exception:
        # When pygments fails, prefer code without highlighting over crashing
        highlighted = code
    return highlighted.splitlines()


def assert_(condition, error=""):
    if not condition:
        if isinstance(error, str):
            error = AssertionError(error)
        raise error


# Copied from the standard traceback module pre-3.11
def some_str(value):
    try:
        return str(value)
    except:
        return '<unprintable %s object>' % type(value).__name__

# === NexusCore/openenv\Lib\site-packages\trio\_signals.py ===
from __future__ import annotations

import signal
from collections import OrderedDict
from contextlib import contextmanager
from typing import TYPE_CHECKING

import trio

from ._util import ConflictDetector, is_main_thread

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Generator, Iterable
    from types import FrameType

    from typing_extensions import Self

# Discussion of signal handling strategies:
#
# - On Windows signals barely exist. There are no options; signal handlers are
#   the only available API.
#
# - On Linux signalfd is arguably the natural way. Semantics: signalfd acts as
#   an *alternative* signal delivery mechanism. The way you use it is to mask
#   out the relevant signals process-wide (so that they don't get delivered
#   the normal way), and then when you read from signalfd that actually counts
#   as delivering it (despite the mask). The problem with this is that we
#   don't have any reliable way to mask out signals process-wide -- the only
#   way to do that in Python is to call pthread_sigmask from the main thread
#   *before starting any other threads*, and as a library we can't really
#   impose that, and the failure mode is annoying (signals get delivered via
#   signal handlers whether we want them to or not).
#
# - on macOS/*BSD, kqueue is the natural way. Semantics: kqueue acts as an
#   *extra* signal delivery mechanism. Signals are delivered the normal
#   way, *and* are delivered to kqueue. So you want to set them to SIG_IGN so
#   that they don't end up pending forever (I guess?). I can't find any actual
#   docs on how masking and EVFILT_SIGNAL interact. I did see someone note
#   that if a signal is pending when the kqueue filter is added then you
#   *don't* get notified of that, which makes sense. But still, we have to
#   manipulate signal state (e.g. setting SIG_IGN) which as far as Python is
#   concerned means we have to do this from the main thread.
#
# So in summary, there don't seem to be any compelling advantages to using the
# platform-native signal notification systems; they're kinda nice, but it's
# simpler to implement the naive signal-handler-based system once and be
# done. (The big advantage would be if there were a reliable way to monitor
# for SIGCHLD from outside the main thread and without interfering with other
# libraries that also want to monitor for SIGCHLD. But there isn't. I guess
# kqueue might give us that, but in kqueue we don't need it, because kqueue
# can directly monitor for child process state changes.)


@contextmanager
def _signal_handler(
    signals: Iterable[int],
    handler: Callable[[int, FrameType | None], object] | int | signal.Handlers | None,
) -> Generator[None, None, None]:
    original_handlers = {}
    try:
        for signum in set(signals):
            original_handlers[signum] = signal.signal(signum, handler)
        yield
    finally:
        for signum, original_handler in original_handlers.items():
            signal.signal(signum, original_handler)


class SignalReceiver:
    def __init__(self) -> None:
        # {signal num: None}
        self._pending: OrderedDict[int, None] = OrderedDict()
        self._lot = trio.lowlevel.ParkingLot()
        self._conflict_detector = ConflictDetector(
            "only one task can iterate on a signal receiver at a time",
        )
        self._closed = False

    def _add(self, signum: int) -> None:
        if self._closed:
            signal.raise_signal(signum)
        else:
            self._pending[signum] = None
            self._lot.unpark()

    def _redeliver_remaining(self) -> None:
        # First make sure that any signals still in the delivery pipeline will
        # get redelivered
        self._closed = True

        # And then redeliver any that are sitting in pending. This is done
        # using a weird recursive construct to make sure we process everything
        # even if some of the handlers raise exceptions.
        def deliver_next() -> None:
            if self._pending:
                signum, _ = self._pending.popitem(last=False)
                try:
                    signal.raise_signal(signum)
                finally:
                    deliver_next()

        deliver_next()

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> int:
        if self._closed:
            raise RuntimeError("open_signal_receiver block already exited")
        # In principle it would be possible to support multiple concurrent
        # calls to __anext__, but doing it without race conditions is quite
        # tricky, and there doesn't seem to be any point in trying.
        with self._conflict_detector:
            if not self._pending:
                await self._lot.park()
            else:
                await trio.lowlevel.checkpoint()
            signum, _ = self._pending.popitem(last=False)
            return signum


def get_pending_signal_count(rec: AsyncIterator[int]) -> int:
    """Helper for tests, not public or otherwise used."""
    # open_signal_receiver() always produces SignalReceiver, this should not fail.
    assert isinstance(rec, SignalReceiver)
    return len(rec._pending)


@contextmanager
def open_signal_receiver(
    *signals: signal.Signals | int,
) -> Generator[AsyncIterator[int], None, None]:
    """A context manager for catching signals.

    Entering this context manager starts listening for the given signals and
    returns an async iterator; exiting the context manager stops listening.

    The async iterator blocks until a signal arrives, and then yields it.

    Note that if you leave the ``with`` block while the iterator has
    unextracted signals still pending inside it, then they will be
    re-delivered using Python's regular signal handling logic. This avoids a
    race condition when signals arrives just before we exit the ``with``
    block.

    Args:
      signals: the signals to listen for.

    Raises:
      TypeError: if no signals were provided.

      RuntimeError: if you try to use this anywhere except Python's main
          thread. (This is a Python limitation.)

    Example:

      A common convention for Unix daemons is that they should reload their
      configuration when they receive a ``SIGHUP``. Here's a sketch of what
      that might look like using :func:`open_signal_receiver`::

         with trio.open_signal_receiver(signal.SIGHUP) as signal_aiter:
             async for signum in signal_aiter:
                 assert signum == signal.SIGHUP
                 reload_configuration()

    """
    if not signals:
        raise TypeError("No signals were provided")

    if not is_main_thread():
        raise RuntimeError(
            "Sorry, open_signal_receiver is only possible when running in "
            "Python interpreter's main thread",
        )
    token = trio.lowlevel.current_trio_token()
    queue = SignalReceiver()

    def handler(signum: int, frame: FrameType | None) -> None:
        token.run_sync_soon(queue._add, signum, idempotent=True)

    try:
        with _signal_handler(signals, handler):
            yield queue
    finally:
        queue._redeliver_remaining()

# === NexusCore/openenv\Lib\site-packages\yaml\reader.py ===
# This module contains abstractions for the input stream. You don't have to
# looks further, there are no pretty code.
#
# We define two classes here.
#
#   Mark(source, line, column)
# It's just a record and its only use is producing nice error messages.
# Parser does not use it for any other purposes.
#
#   Reader(source, data)
# Reader determines the encoding of `data` and converts it to unicode.
# Reader provides the following methods and attributes:
#   reader.peek(length=1) - return the next `length` characters
#   reader.forward(length=1) - move the current position to `length` characters.
#   reader.index - the number of the current character.
#   reader.line, stream.column - the line and the column of the current character.

__all__ = ['Reader', 'ReaderError']

from .error import YAMLError, Mark

import codecs, re

class ReaderError(YAMLError):

    def __init__(self, name, position, character, encoding, reason):
        self.name = name
        self.character = character
        self.position = position
        self.encoding = encoding
        self.reason = reason

    def __str__(self):
        if isinstance(self.character, bytes):
            return "'%s' codec can't decode byte #x%02x: %s\n"  \
                    "  in \"%s\", position %d"    \
                    % (self.encoding, ord(self.character), self.reason,
                            self.name, self.position)
        else:
            return "unacceptable character #x%04x: %s\n"    \
                    "  in \"%s\", position %d"    \
                    % (self.character, self.reason,
                            self.name, self.position)

class Reader(object):
    # Reader:
    # - determines the data encoding and converts it to a unicode string,
    # - checks if characters are in allowed range,
    # - adds '\0' to the end.

    # Reader accepts
    #  - a `bytes` object,
    #  - a `str` object,
    #  - a file-like object with its `read` method returning `str`,
    #  - a file-like object with its `read` method returning `unicode`.

    # Yeah, it's ugly and slow.

    def __init__(self, stream):
        self.name = None
        self.stream = None
        self.stream_pointer = 0
        self.eof = True
        self.buffer = ''
        self.pointer = 0
        self.raw_buffer = None
        self.raw_decode = None
        self.encoding = None
        self.index = 0
        self.line = 0
        self.column = 0
        if isinstance(stream, str):
            self.name = "<unicode string>"
            self.check_printable(stream)
            self.buffer = stream+'\0'
        elif isinstance(stream, bytes):
            self.name = "<byte string>"
            self.raw_buffer = stream
            self.determine_encoding()
        else:
            self.stream = stream
            self.name = getattr(stream, 'name', "<file>")
            self.eof = False
            self.raw_buffer = None
            self.determine_encoding()

    def peek(self, index=0):
        try:
            return self.buffer[self.pointer+index]
        except IndexError:
            self.update(index+1)
            return self.buffer[self.pointer+index]

    def prefix(self, length=1):
        if self.pointer+length >= len(self.buffer):
            self.update(length)
        return self.buffer[self.pointer:self.pointer+length]

    def forward(self, length=1):
        if self.pointer+length+1 >= len(self.buffer):
            self.update(length+1)
        while length:
            ch = self.buffer[self.pointer]
            self.pointer += 1
            self.index += 1
            if ch in '\n\x85\u2028\u2029'  \
                    or (ch == '\r' and self.buffer[self.pointer] != '\n'):
                self.line += 1
                self.column = 0
            elif ch != '\uFEFF':
                self.column += 1
            length -= 1

    def get_mark(self):
        if self.stream is None:
            return Mark(self.name, self.index, self.line, self.column,
                    self.buffer, self.pointer)
        else:
            return Mark(self.name, self.index, self.line, self.column,
                    None, None)

    def determine_encoding(self):
        while not self.eof and (self.raw_buffer is None or len(self.raw_buffer) < 2):
            self.update_raw()
        if isinstance(self.raw_buffer, bytes):
            if self.raw_buffer.startswith(codecs.BOM_UTF16_LE):
                self.raw_decode = codecs.utf_16_le_decode
                self.encoding = 'utf-16-le'
            elif self.raw_buffer.startswith(codecs.BOM_UTF16_BE):
                self.raw_decode = codecs.utf_16_be_decode
                self.encoding = 'utf-16-be'
            else:
                self.raw_decode = codecs.utf_8_decode
                self.encoding = 'utf-8'
        self.update(1)

    NON_PRINTABLE = re.compile('[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\uD7FF\uE000-\uFFFD\U00010000-\U0010ffff]')
    def check_printable(self, data):
        match = self.NON_PRINTABLE.search(data)
        if match:
            character = match.group()
            position = self.index+(len(self.buffer)-self.pointer)+match.start()
            raise ReaderError(self.name, position, ord(character),
                    'unicode', "special characters are not allowed")

    def update(self, length):
        if self.raw_buffer is None:
            return
        self.buffer = self.buffer[self.pointer:]
        self.pointer = 0
        while len(self.buffer) < length:
            if not self.eof:
                self.update_raw()
            if self.raw_decode is not None:
                try:
                    data, converted = self.raw_decode(self.raw_buffer,
                            'strict', self.eof)
                except UnicodeDecodeError as exc:
                    character = self.raw_buffer[exc.start]
                    if self.stream is not None:
                        position = self.stream_pointer-len(self.raw_buffer)+exc.start
                    else:
                        position = exc.start
                    raise ReaderError(self.name, position, character,
                            exc.encoding, exc.reason)
            else:
                data = self.raw_buffer
                converted = len(data)
            self.check_printable(data)
            self.buffer += data
            self.raw_buffer = self.raw_buffer[converted:]
            if self.eof:
                self.buffer += '\0'
                self.raw_buffer = None
                break

    def update_raw(self, size=4096):
        data = self.stream.read(size)
        if self.raw_buffer is None:
            self.raw_buffer = data
        else:
            self.raw_buffer += data
        self.stream_pointer += len(data)
        if not data:
            self.eof = True

# === NexusCore/openenv\Lib\site-packages\debugpy\common\singleton.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

import functools
import threading


class Singleton(object):
    """A base class for a class of a singleton object.

    For any derived class T, the first invocation of T() will create the instance,
    and any future invocations of T() will return that instance.

    Concurrent invocations of T() from different threads are safe.
    """

    # A dual-lock scheme is necessary to be thread safe while avoiding deadlocks.
    # _lock_lock is shared by all singleton types, and is used to construct their
    # respective _lock instances when invoked for a new type. Then _lock is used
    # to synchronize all further access for that type, including __init__. This way,
    # __init__ for any given singleton can access another singleton, and not get
    # deadlocked if that other singleton is trying to access it.
    _lock_lock = threading.RLock()
    _lock = None

    # Specific subclasses will get their own _instance set in __new__.
    _instance = None

    _is_shared = None  # True if shared, False if exclusive

    def __new__(cls, *args, **kwargs):
        # Allow arbitrary args and kwargs if shared=False, because that is guaranteed
        # to construct a new singleton if it succeeds. Otherwise, this call might end
        # up returning an existing instance, which might have been constructed with
        # different arguments, so allowing them is misleading.
        assert not kwargs.get("shared", False) or (len(args) + len(kwargs)) == 0, (
            "Cannot use constructor arguments when accessing a Singleton without "
            "specifying shared=False."
        )

        # Avoid locking as much as possible with repeated double-checks - the most
        # common path is when everything is already allocated.
        if not cls._instance:
            # If there's no per-type lock, allocate it.
            if cls._lock is None:
                with cls._lock_lock:
                    if cls._lock is None:
                        cls._lock = threading.RLock()

            # Now that we have a per-type lock, we can synchronize construction.
            if not cls._instance:
                with cls._lock:
                    if not cls._instance:
                        cls._instance = object.__new__(cls)
                        # To prevent having __init__ invoked multiple times, call
                        # it here directly, and then replace it with a stub that
                        # does nothing - that stub will get auto-invoked on return,
                        # and on all future singleton accesses.
                        cls._instance.__init__()
                        cls.__init__ = lambda *args, **kwargs: None

        return cls._instance

    def __init__(self, *args, **kwargs):
        """Initializes the singleton instance. Guaranteed to only be invoked once for
        any given type derived from Singleton.

        If shared=False, the caller is requesting a singleton instance for their own
        exclusive use. This is only allowed if the singleton has not been created yet;
        if so, it is created and marked as being in exclusive use. While it is marked
        as such, all attempts to obtain an existing instance of it immediately raise
        an exception. The singleton can eventually be promoted to shared use by calling
        share() on it.
        """

        shared = kwargs.pop("shared", True)
        with self:
            if shared:
                assert (
                    type(self)._is_shared is not False
                ), "Cannot access a non-shared Singleton."
                type(self)._is_shared = True
            else:
                assert type(self)._is_shared is None, "Singleton is already created."

    def __enter__(self):
        """Lock this singleton to prevent concurrent access."""
        type(self)._lock.acquire()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Unlock this singleton to allow concurrent access."""
        type(self)._lock.release()

    def share(self):
        """Share this singleton, if it was originally created with shared=False."""
        type(self)._is_shared = True


class ThreadSafeSingleton(Singleton):
    """A singleton that incorporates a lock for thread-safe access to its members.

    The lock can be acquired using the context manager protocol, and thus idiomatic
    use is in conjunction with a with-statement. For example, given derived class T::

        with T() as t:
            t.x = t.frob(t.y)

    All access to the singleton from the outside should follow this pattern for both
    attributes and method calls. Singleton members can assume that self is locked by
    the caller while they're executing, but recursive locking of the same singleton
    on the same thread is also permitted.
    """

    threadsafe_attrs = frozenset()
    """Names of attributes that are guaranteed to be used in a thread-safe manner.

    This is typically used in conjunction with share() to simplify synchronization.
    """

    readonly_attrs = frozenset()
    """Names of attributes that are readonly. These can be read without locking, but
    cannot be written at all.

    Every derived class gets its own separate set. Thus, for any given singleton type
    T, an attribute can be made readonly after setting it, with T.readonly_attrs.add().
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make sure each derived class gets a separate copy.
        type(self).readonly_attrs = set(type(self).readonly_attrs)

    # Prevent callers from reading or writing attributes without locking, except for
    # reading attributes listed in threadsafe_attrs, and methods specifically marked
    # with @threadsafe_method. Such methods should perform the necessary locking to
    # ensure thread safety for the callers.

    @staticmethod
    def assert_locked(self):
        lock = type(self)._lock
        assert lock.acquire(blocking=False), (
            "ThreadSafeSingleton accessed without locking. Either use with-statement, "
            "or if it is a method or property, mark it as @threadsafe_method or with "
            "@autolocked_method, as appropriate."
        )
        lock.release()

    def __getattribute__(self, name):
        value = object.__getattribute__(self, name)
        if name not in (type(self).threadsafe_attrs | type(self).readonly_attrs):
            if not getattr(value, "is_threadsafe_method", False):
                ThreadSafeSingleton.assert_locked(self)
        return value

    def __setattr__(self, name, value):
        assert name not in type(self).readonly_attrs, "This attribute is read-only."
        if name not in type(self).threadsafe_attrs:
            ThreadSafeSingleton.assert_locked(self)
        return object.__setattr__(self, name, value)


def threadsafe_method(func):
    """Marks a method of a ThreadSafeSingleton-derived class as inherently thread-safe.

    A method so marked must either not use any singleton state, or lock it appropriately.
    """

    func.is_threadsafe_method = True
    return func


def autolocked_method(func):
    """Automatically synchronizes all calls of a method of a ThreadSafeSingleton-derived
    class by locking the singleton for the duration of each call.
    """

    @functools.wraps(func)
    @threadsafe_method
    def lock_and_call(self, *args, **kwargs):
        with self:
            return func(self, *args, **kwargs)

    return lock_and_call

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\client\credentials.py ===
import requests
from typing import Dict, Any, Optional, Union

from .exceptions import UnauthorizedError


class CredentialsManagementClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """
        Initialize the CredentialsManagementClient.

        Args:
            base_url (str): The base URL of the LiteLLM proxy server (e.g., "http://localhost:8000")
            api_key (Optional[str]): API key for authentication. If provided, it will be sent as a Bearer token.
        """
        self._base_url = base_url.rstrip("/")  # Remove trailing slash if present
        self._api_key = api_key

    def _get_headers(self) -> Dict[str, str]:
        """
        Get the headers for API requests, including authorization if api_key is set.

        Returns:
            Dict[str, str]: Headers to use for API requests
        """
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def list(
        self,
        return_request: bool = False,
    ) -> Union[Dict[str, Any], requests.Request]:
        """
        List all credentials.

        Args:
            return_request (bool): If True, returns the prepared request object instead of executing it

        Returns:
            Union[Dict[str, Any], requests.Request]: Either the response from the server or
            a prepared request object if return_request is True

        Raises:
            UnauthorizedError: If the request fails with a 401 status code
            requests.exceptions.RequestException: If the request fails with any other error
        """
        url = f"{self._base_url}/credentials"

        request = requests.Request("GET", url, headers=self._get_headers())

        if return_request:
            return request

        session = requests.Session()
        try:
            response = session.send(request.prepare())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError(e)
            raise

    def create(
        self,
        credential_name: str,
        credential_info: Dict[str, Any],
        credential_values: Dict[str, Any],
        return_request: bool = False,
    ) -> Union[Dict[str, Any], requests.Request]:
        """
        Create a new credential.

        Args:
            credential_name (str): Name of the credential
            credential_info (Dict[str, Any]): Additional information about the credential
            credential_values (Dict[str, Any]): Values for the credential
            return_request (bool): If True, returns the prepared request object instead of executing it

        Returns:
            Union[Dict[str, Any], requests.Request]: Either the response from the server or
            a prepared request object if return_request is True

        Raises:
            UnauthorizedError: If the request fails with a 401 status code
            requests.exceptions.RequestException: If the request fails with any other error
        """
        url = f"{self._base_url}/credentials"

        data = {
            "credential_name": credential_name,
            "credential_info": credential_info,
            "credential_values": credential_values,
        }

        request = requests.Request("POST", url, headers=self._get_headers(), json=data)

        if return_request:
            return request

        session = requests.Session()
        try:
            response = session.send(request.prepare())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError(e)
            raise

    def delete(
        self,
        credential_name: str,
        return_request: bool = False,
    ) -> Union[Dict[str, Any], requests.Request]:
        """
        Delete a credential by name.

        Args:
            credential_name (str): Name of the credential to delete
            return_request (bool): If True, returns the prepared request object instead of executing it

        Returns:
            Union[Dict[str, Any], requests.Request]: Either the response from the server or
            a prepared request object if return_request is True

        Raises:
            UnauthorizedError: If the request fails with a 401 status code
            requests.exceptions.RequestException: If the request fails with any other error
        """
        url = f"{self._base_url}/credentials/{credential_name}"

        request = requests.Request("DELETE", url, headers=self._get_headers())

        if return_request:
            return request

        session = requests.Session()
        try:
            response = session.send(request.prepare())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError(e)
            raise

    def get(
        self,
        credential_name: str,
        return_request: bool = False,
    ) -> Union[Dict[str, Any], requests.Request]:
        """
        Get a credential by name.

        Args:
            credential_name (str): Name of the credential to retrieve
            return_request (bool): If True, returns the prepared request object instead of executing it

        Returns:
            Union[Dict[str, Any], requests.Request]: Either the response from the server or
            a prepared request object if return_request is True

        Raises:
            UnauthorizedError: If the request fails with a 401 status code
            requests.exceptions.RequestException: If the request fails with any other error
        """
        url = f"{self._base_url}/credentials/by_name/{credential_name}"

        request = requests.Request("GET", url, headers=self._get_headers())

        if return_request:
            return request

        session = requests.Session()
        try:
            response = session.send(request.prepare())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError(e)
            raise

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\thread_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from ..shared_params.metadata import Metadata
from .code_interpreter_tool_param import CodeInterpreterToolParam
from .threads.message_content_part_param import MessageContentPartParam

__all__ = [
    "ThreadCreateParams",
    "Message",
    "MessageAttachment",
    "MessageAttachmentTool",
    "MessageAttachmentToolFileSearch",
    "ToolResources",
    "ToolResourcesCodeInterpreter",
    "ToolResourcesFileSearch",
    "ToolResourcesFileSearchVectorStore",
    "ToolResourcesFileSearchVectorStoreChunkingStrategy",
    "ToolResourcesFileSearchVectorStoreChunkingStrategyAuto",
    "ToolResourcesFileSearchVectorStoreChunkingStrategyStatic",
    "ToolResourcesFileSearchVectorStoreChunkingStrategyStaticStatic",
]


class ThreadCreateParams(TypedDict, total=False):
    messages: Iterable[Message]
    """
    A list of [messages](https://platform.openai.com/docs/api-reference/messages) to
    start the thread with.
    """

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    tool_resources: Optional[ToolResources]
    """
    A set of resources that are made available to the assistant's tools in this
    thread. The resources are specific to the type of tool. For example, the
    `code_interpreter` tool requires a list of file IDs, while the `file_search`
    tool requires a list of vector store IDs.
    """


class MessageAttachmentToolFileSearch(TypedDict, total=False):
    type: Required[Literal["file_search"]]
    """The type of tool being defined: `file_search`"""


MessageAttachmentTool: TypeAlias = Union[CodeInterpreterToolParam, MessageAttachmentToolFileSearch]


class MessageAttachment(TypedDict, total=False):
    file_id: str
    """The ID of the file to attach to the message."""

    tools: Iterable[MessageAttachmentTool]
    """The tools to add this file to."""


class Message(TypedDict, total=False):
    content: Required[Union[str, Iterable[MessageContentPartParam]]]
    """The text contents of the message."""

    role: Required[Literal["user", "assistant"]]
    """The role of the entity that is creating the message. Allowed values include:

    - `user`: Indicates the message is sent by an actual user and should be used in
      most cases to represent user-generated messages.
    - `assistant`: Indicates the message is generated by the assistant. Use this
      value to insert messages from the assistant into the conversation.
    """

    attachments: Optional[Iterable[MessageAttachment]]
    """A list of files attached to the message, and the tools they should be added to."""

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """


class ToolResourcesCodeInterpreter(TypedDict, total=False):
    file_ids: List[str]
    """
    A list of [file](https://platform.openai.com/docs/api-reference/files) IDs made
    available to the `code_interpreter` tool. There can be a maximum of 20 files
    associated with the tool.
    """


class ToolResourcesFileSearchVectorStoreChunkingStrategyAuto(TypedDict, total=False):
    type: Required[Literal["auto"]]
    """Always `auto`."""


class ToolResourcesFileSearchVectorStoreChunkingStrategyStaticStatic(TypedDict, total=False):
    chunk_overlap_tokens: Required[int]
    """The number of tokens that overlap between chunks. The default value is `400`.

    Note that the overlap must not exceed half of `max_chunk_size_tokens`.
    """

    max_chunk_size_tokens: Required[int]
    """The maximum number of tokens in each chunk.

    The default value is `800`. The minimum value is `100` and the maximum value is
    `4096`.
    """


class ToolResourcesFileSearchVectorStoreChunkingStrategyStatic(TypedDict, total=False):
    static: Required[ToolResourcesFileSearchVectorStoreChunkingStrategyStaticStatic]

    type: Required[Literal["static"]]
    """Always `static`."""


ToolResourcesFileSearchVectorStoreChunkingStrategy: TypeAlias = Union[
    ToolResourcesFileSearchVectorStoreChunkingStrategyAuto, ToolResourcesFileSearchVectorStoreChunkingStrategyStatic
]


class ToolResourcesFileSearchVectorStore(TypedDict, total=False):
    chunking_strategy: ToolResourcesFileSearchVectorStoreChunkingStrategy
    """The chunking strategy used to chunk the file(s).

    If not set, will use the `auto` strategy.
    """

    file_ids: List[str]
    """
    A list of [file](https://platform.openai.com/docs/api-reference/files) IDs to
    add to the vector store. There can be a maximum of 10000 files in a vector
    store.
    """

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """


class ToolResourcesFileSearch(TypedDict, total=False):
    vector_store_ids: List[str]
    """
    The
    [vector store](https://platform.openai.com/docs/api-reference/vector-stores/object)
    attached to this thread. There can be a maximum of 1 vector store attached to
    the thread.
    """

    vector_stores: Iterable[ToolResourcesFileSearchVectorStore]
    """
    A helper to create a
    [vector store](https://platform.openai.com/docs/api-reference/vector-stores/object)
    with file_ids and attach it to this thread. There can be a maximum of 1 vector
    store attached to the thread.
    """


class ToolResources(TypedDict, total=False):
    code_interpreter: ToolResourcesCodeInterpreter

    file_search: ToolResourcesFileSearch

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\realtime\transcription_session_update.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Optional
from typing_extensions import Literal

from ...._models import BaseModel

__all__ = [
    "TranscriptionSessionUpdate",
    "Session",
    "SessionClientSecret",
    "SessionClientSecretExpiresAt",
    "SessionInputAudioNoiseReduction",
    "SessionInputAudioTranscription",
    "SessionTurnDetection",
]


class SessionClientSecretExpiresAt(BaseModel):
    anchor: Optional[Literal["created_at"]] = None
    """The anchor point for the ephemeral token expiration.

    Only `created_at` is currently supported.
    """

    seconds: Optional[int] = None
    """The number of seconds from the anchor point to the expiration.

    Select a value between `10` and `7200`.
    """


class SessionClientSecret(BaseModel):
    expires_at: Optional[SessionClientSecretExpiresAt] = None
    """Configuration for the ephemeral token expiration."""


class SessionInputAudioNoiseReduction(BaseModel):
    type: Optional[Literal["near_field", "far_field"]] = None
    """Type of noise reduction.

    `near_field` is for close-talking microphones such as headphones, `far_field` is
    for far-field microphones such as laptop or conference room microphones.
    """


class SessionInputAudioTranscription(BaseModel):
    language: Optional[str] = None
    """The language of the input audio.

    Supplying the input language in
    [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `en`)
    format will improve accuracy and latency.
    """

    model: Optional[Literal["gpt-4o-transcribe", "gpt-4o-mini-transcribe", "whisper-1"]] = None
    """
    The model to use for transcription, current options are `gpt-4o-transcribe`,
    `gpt-4o-mini-transcribe`, and `whisper-1`.
    """

    prompt: Optional[str] = None
    """
    An optional text to guide the model's style or continue a previous audio
    segment. For `whisper-1`, the
    [prompt is a list of keywords](https://platform.openai.com/docs/guides/speech-to-text#prompting).
    For `gpt-4o-transcribe` models, the prompt is a free text string, for example
    "expect words related to technology".
    """


class SessionTurnDetection(BaseModel):
    create_response: Optional[bool] = None
    """Whether or not to automatically generate a response when a VAD stop event
    occurs.

    Not available for transcription sessions.
    """

    eagerness: Optional[Literal["low", "medium", "high", "auto"]] = None
    """Used only for `semantic_vad` mode.

    The eagerness of the model to respond. `low` will wait longer for the user to
    continue speaking, `high` will respond more quickly. `auto` is the default and
    is equivalent to `medium`.
    """

    interrupt_response: Optional[bool] = None
    """
    Whether or not to automatically interrupt any ongoing response with output to
    the default conversation (i.e. `conversation` of `auto`) when a VAD start event
    occurs. Not available for transcription sessions.
    """

    prefix_padding_ms: Optional[int] = None
    """Used only for `server_vad` mode.

    Amount of audio to include before the VAD detected speech (in milliseconds).
    Defaults to 300ms.
    """

    silence_duration_ms: Optional[int] = None
    """Used only for `server_vad` mode.

    Duration of silence to detect speech stop (in milliseconds). Defaults to 500ms.
    With shorter values the model will respond more quickly, but may jump in on
    short pauses from the user.
    """

    threshold: Optional[float] = None
    """Used only for `server_vad` mode.

    Activation threshold for VAD (0.0 to 1.0), this defaults to 0.5. A higher
    threshold will require louder audio to activate the model, and thus might
    perform better in noisy environments.
    """

    type: Optional[Literal["server_vad", "semantic_vad"]] = None
    """Type of turn detection."""


class Session(BaseModel):
    client_secret: Optional[SessionClientSecret] = None
    """Configuration options for the generated client secret."""

    include: Optional[List[str]] = None
    """The set of items to include in the transcription. Current available items are:

    - `item.input_audio_transcription.logprobs`
    """

    input_audio_format: Optional[Literal["pcm16", "g711_ulaw", "g711_alaw"]] = None
    """The format of input audio.

    Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For `pcm16`, input audio must
    be 16-bit PCM at a 24kHz sample rate, single channel (mono), and little-endian
    byte order.
    """

    input_audio_noise_reduction: Optional[SessionInputAudioNoiseReduction] = None
    """Configuration for input audio noise reduction.

    This can be set to `null` to turn off. Noise reduction filters audio added to
    the input audio buffer before it is sent to VAD and the model. Filtering the
    audio can improve VAD and turn detection accuracy (reducing false positives) and
    model performance by improving perception of the input audio.
    """

    input_audio_transcription: Optional[SessionInputAudioTranscription] = None
    """Configuration for input audio transcription.

    The client can optionally set the language and prompt for transcription, these
    offer additional guidance to the transcription service.
    """

    modalities: Optional[List[Literal["text", "audio"]]] = None
    """The set of modalities the model can respond with.

    To disable audio, set this to ["text"].
    """

    turn_detection: Optional[SessionTurnDetection] = None
    """Configuration for turn detection, ether Server VAD or Semantic VAD.

    This can be set to `null` to turn off, in which case the client must manually
    trigger model response. Server VAD means that the model will detect the start
    and end of speech based on audio volume and respond at the end of user speech.
    Semantic VAD is more advanced and uses a turn detection model (in conjuction
    with VAD) to semantically estimate whether the user has finished speaking, then
    dynamically sets a timeout based on this probability. For example, if user audio
    trails off with "uhhm", the model will score a low probability of turn end and
    wait longer for the user to continue speaking. This can be useful for more
    natural conversations, but may have a higher latency.
    """


class TranscriptionSessionUpdate(BaseModel):
    session: Session
    """Realtime transcription session object configuration."""

    type: Literal["transcription_session.update"]
    """The event type, must be `transcription_session.update`."""

    event_id: Optional[str] = None
    """Optional client-generated ID used to identify this event."""

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\realtime\transcription_session_update_param.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List
from typing_extensions import Literal, Required, TypedDict

__all__ = [
    "TranscriptionSessionUpdateParam",
    "Session",
    "SessionClientSecret",
    "SessionClientSecretExpiresAt",
    "SessionInputAudioNoiseReduction",
    "SessionInputAudioTranscription",
    "SessionTurnDetection",
]


class SessionClientSecretExpiresAt(TypedDict, total=False):
    anchor: Literal["created_at"]
    """The anchor point for the ephemeral token expiration.

    Only `created_at` is currently supported.
    """

    seconds: int
    """The number of seconds from the anchor point to the expiration.

    Select a value between `10` and `7200`.
    """


class SessionClientSecret(TypedDict, total=False):
    expires_at: SessionClientSecretExpiresAt
    """Configuration for the ephemeral token expiration."""


class SessionInputAudioNoiseReduction(TypedDict, total=False):
    type: Literal["near_field", "far_field"]
    """Type of noise reduction.

    `near_field` is for close-talking microphones such as headphones, `far_field` is
    for far-field microphones such as laptop or conference room microphones.
    """


class SessionInputAudioTranscription(TypedDict, total=False):
    language: str
    """The language of the input audio.

    Supplying the input language in
    [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `en`)
    format will improve accuracy and latency.
    """

    model: Literal["gpt-4o-transcribe", "gpt-4o-mini-transcribe", "whisper-1"]
    """
    The model to use for transcription, current options are `gpt-4o-transcribe`,
    `gpt-4o-mini-transcribe`, and `whisper-1`.
    """

    prompt: str
    """
    An optional text to guide the model's style or continue a previous audio
    segment. For `whisper-1`, the
    [prompt is a list of keywords](https://platform.openai.com/docs/guides/speech-to-text#prompting).
    For `gpt-4o-transcribe` models, the prompt is a free text string, for example
    "expect words related to technology".
    """


class SessionTurnDetection(TypedDict, total=False):
    create_response: bool
    """Whether or not to automatically generate a response when a VAD stop event
    occurs.

    Not available for transcription sessions.
    """

    eagerness: Literal["low", "medium", "high", "auto"]
    """Used only for `semantic_vad` mode.

    The eagerness of the model to respond. `low` will wait longer for the user to
    continue speaking, `high` will respond more quickly. `auto` is the default and
    is equivalent to `medium`.
    """

    interrupt_response: bool
    """
    Whether or not to automatically interrupt any ongoing response with output to
    the default conversation (i.e. `conversation` of `auto`) when a VAD start event
    occurs. Not available for transcription sessions.
    """

    prefix_padding_ms: int
    """Used only for `server_vad` mode.

    Amount of audio to include before the VAD detected speech (in milliseconds).
    Defaults to 300ms.
    """

    silence_duration_ms: int
    """Used only for `server_vad` mode.

    Duration of silence to detect speech stop (in milliseconds). Defaults to 500ms.
    With shorter values the model will respond more quickly, but may jump in on
    short pauses from the user.
    """

    threshold: float
    """Used only for `server_vad` mode.

    Activation threshold for VAD (0.0 to 1.0), this defaults to 0.5. A higher
    threshold will require louder audio to activate the model, and thus might
    perform better in noisy environments.
    """

    type: Literal["server_vad", "semantic_vad"]
    """Type of turn detection."""


class Session(TypedDict, total=False):
    client_secret: SessionClientSecret
    """Configuration options for the generated client secret."""

    include: List[str]
    """The set of items to include in the transcription. Current available items are:

    - `item.input_audio_transcription.logprobs`
    """

    input_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"]
    """The format of input audio.

    Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For `pcm16`, input audio must
    be 16-bit PCM at a 24kHz sample rate, single channel (mono), and little-endian
    byte order.
    """

    input_audio_noise_reduction: SessionInputAudioNoiseReduction
    """Configuration for input audio noise reduction.

    This can be set to `null` to turn off. Noise reduction filters audio added to
    the input audio buffer before it is sent to VAD and the model. Filtering the
    audio can improve VAD and turn detection accuracy (reducing false positives) and
    model performance by improving perception of the input audio.
    """

    input_audio_transcription: SessionInputAudioTranscription
    """Configuration for input audio transcription.

    The client can optionally set the language and prompt for transcription, these
    offer additional guidance to the transcription service.
    """

    modalities: List[Literal["text", "audio"]]
    """The set of modalities the model can respond with.

    To disable audio, set this to ["text"].
    """

    turn_detection: SessionTurnDetection
    """Configuration for turn detection, ether Server VAD or Semantic VAD.

    This can be set to `null` to turn off, in which case the client must manually
    trigger model response. Server VAD means that the model will detect the start
    and end of speech based on audio volume and respond at the end of user speech.
    Semantic VAD is more advanced and uses a turn detection model (in conjuction
    with VAD) to semantically estimate whether the user has finished speaking, then
    dynamically sets a timeout based on this probability. For example, if user audio
    trails off with "uhhm", the model will score a low probability of turn end and
    wait longer for the user to continue speaking. This can be useful for more
    natural conversations, but may have a higher latency.
    """


class TranscriptionSessionUpdateParam(TypedDict, total=False):
    session: Required[Session]
    """Realtime transcription session object configuration."""

    type: Required[Literal["transcription_session.update"]]
    """The event type, must be `transcription_session.update`."""

    event_id: str
    """Optional client-generated ID used to identify this event."""

# === NexusCore/openenv\Lib\site-packages\pip\_internal\pyproject.py ===
import importlib.util
import os
import sys
from collections import namedtuple
from typing import Any, List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    from pip._vendor import tomli as tomllib

from pip._vendor.packaging.requirements import InvalidRequirement

from pip._internal.exceptions import (
    InstallationError,
    InvalidPyProjectBuildRequires,
    MissingPyProjectBuildRequires,
)
from pip._internal.utils.packaging import get_requirement


def _is_list_of_str(obj: Any) -> bool:
    return isinstance(obj, list) and all(isinstance(item, str) for item in obj)


def make_pyproject_path(unpacked_source_directory: str) -> str:
    return os.path.join(unpacked_source_directory, "pyproject.toml")


BuildSystemDetails = namedtuple(
    "BuildSystemDetails", ["requires", "backend", "check", "backend_path"]
)


def load_pyproject_toml(
    use_pep517: Optional[bool], pyproject_toml: str, setup_py: str, req_name: str
) -> Optional[BuildSystemDetails]:
    """Load the pyproject.toml file.

    Parameters:
        use_pep517 - Has the user requested PEP 517 processing? None
                     means the user hasn't explicitly specified.
        pyproject_toml - Location of the project's pyproject.toml file
        setup_py - Location of the project's setup.py file
        req_name - The name of the requirement we're processing (for
                   error reporting)

    Returns:
        None if we should use the legacy code path, otherwise a tuple
        (
            requirements from pyproject.toml,
            name of PEP 517 backend,
            requirements we should check are installed after setting
                up the build environment
            directory paths to import the backend from (backend-path),
                relative to the project root.
        )
    """
    has_pyproject = os.path.isfile(pyproject_toml)
    has_setup = os.path.isfile(setup_py)

    if not has_pyproject and not has_setup:
        raise InstallationError(
            f"{req_name} does not appear to be a Python project: "
            f"neither 'setup.py' nor 'pyproject.toml' found."
        )

    if has_pyproject:
        with open(pyproject_toml, encoding="utf-8") as f:
            pp_toml = tomllib.loads(f.read())
        build_system = pp_toml.get("build-system")
    else:
        build_system = None

    # The following cases must use PEP 517
    # We check for use_pep517 being non-None and falsy because that means
    # the user explicitly requested --no-use-pep517.  The value 0 as
    # opposed to False can occur when the value is provided via an
    # environment variable or config file option (due to the quirk of
    # strtobool() returning an integer in pip's configuration code).
    if has_pyproject and not has_setup:
        if use_pep517 is not None and not use_pep517:
            raise InstallationError(
                "Disabling PEP 517 processing is invalid: "
                "project does not have a setup.py"
            )
        use_pep517 = True
    elif build_system and "build-backend" in build_system:
        if use_pep517 is not None and not use_pep517:
            raise InstallationError(
                "Disabling PEP 517 processing is invalid: "
                "project specifies a build backend of {} "
                "in pyproject.toml".format(build_system["build-backend"])
            )
        use_pep517 = True

    # If we haven't worked out whether to use PEP 517 yet,
    # and the user hasn't explicitly stated a preference,
    # we do so if the project has a pyproject.toml file
    # or if we cannot import setuptools or wheels.

    # We fallback to PEP 517 when without setuptools or without the wheel package,
    # so setuptools can be installed as a default build backend.
    # For more info see:
    # https://discuss.python.org/t/pip-without-setuptools-could-the-experience-be-improved/11810/9
    # https://github.com/pypa/pip/issues/8559
    elif use_pep517 is None:
        use_pep517 = (
            has_pyproject
            or not importlib.util.find_spec("setuptools")
            or not importlib.util.find_spec("wheel")
        )

    # At this point, we know whether we're going to use PEP 517.
    assert use_pep517 is not None

    # If we're using the legacy code path, there is nothing further
    # for us to do here.
    if not use_pep517:
        return None

    if build_system is None:
        # Either the user has a pyproject.toml with no build-system
        # section, or the user has no pyproject.toml, but has opted in
        # explicitly via --use-pep517.
        # In the absence of any explicit backend specification, we
        # assume the setuptools backend that most closely emulates the
        # traditional direct setup.py execution, and require wheel and
        # a version of setuptools that supports that backend.

        build_system = {
            "requires": ["setuptools>=40.8.0"],
            "build-backend": "setuptools.build_meta:__legacy__",
        }

    # If we're using PEP 517, we have build system information (either
    # from pyproject.toml, or defaulted by the code above).
    # Note that at this point, we do not know if the user has actually
    # specified a backend, though.
    assert build_system is not None

    # Ensure that the build-system section in pyproject.toml conforms
    # to PEP 518.

    # Specifying the build-system table but not the requires key is invalid
    if "requires" not in build_system:
        raise MissingPyProjectBuildRequires(package=req_name)

    # Error out if requires is not a list of strings
    requires = build_system["requires"]
    if not _is_list_of_str(requires):
        raise InvalidPyProjectBuildRequires(
            package=req_name,
            reason="It is not a list of strings.",
        )

    # Each requirement must be valid as per PEP 508
    for requirement in requires:
        try:
            get_requirement(requirement)
        except InvalidRequirement as error:
            raise InvalidPyProjectBuildRequires(
                package=req_name,
                reason=f"It contains an invalid requirement: {requirement!r}",
            ) from error

    backend = build_system.get("build-backend")
    backend_path = build_system.get("backend-path", [])
    check: List[str] = []
    if backend is None:
        # If the user didn't specify a backend, we assume they want to use
        # the setuptools backend. But we can't be sure they have included
        # a version of setuptools which supplies the backend. So we
        # make a note to check that this requirement is present once
        # we have set up the environment.
        # This is quite a lot of work to check for a very specific case. But
        # the problem is, that case is potentially quite common - projects that
        # adopted PEP 518 early for the ability to specify requirements to
        # execute setup.py, but never considered needing to mention the build
        # tools themselves. The original PEP 518 code had a similar check (but
        # implemented in a different way).
        backend = "setuptools.build_meta:__legacy__"
        check = ["setuptools>=40.8.0"]

    return BuildSystemDetails(requires, backend, check, backend_path)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\formatters\svg.py ===
"""
    pygments.formatters.svg
    ~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for SVG output.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.token import Comment
from pip._vendor.pygments.util import get_bool_opt, get_int_opt

__all__ = ['SvgFormatter']


def escape_html(text):
    """Escape &, <, > as well as single and double quotes for HTML."""
    return text.replace('&', '&amp;').  \
                replace('<', '&lt;').   \
                replace('>', '&gt;').   \
                replace('"', '&quot;'). \
                replace("'", '&#39;')


class2style = {}

class SvgFormatter(Formatter):
    """
    Format tokens as an SVG graphics file.  This formatter is still experimental.
    Each line of code is a ``<text>`` element with explicit ``x`` and ``y``
    coordinates containing ``<tspan>`` elements with the individual token styles.

    By default, this formatter outputs a full SVG document including doctype
    declaration and the ``<svg>`` root element.

    .. versionadded:: 0.9

    Additional options accepted:

    `nowrap`
        Don't wrap the SVG ``<text>`` elements in ``<svg><g>`` elements and
        don't add a XML declaration and a doctype.  If true, the `fontfamily`
        and `fontsize` options are ignored.  Defaults to ``False``.

    `fontfamily`
        The value to give the wrapping ``<g>`` element's ``font-family``
        attribute, defaults to ``"monospace"``.

    `fontsize`
        The value to give the wrapping ``<g>`` element's ``font-size``
        attribute, defaults to ``"14px"``.

    `linenos`
        If ``True``, add line numbers (default: ``False``).

    `linenostart`
        The line number for the first line (default: ``1``).

    `linenostep`
        If set to a number n > 1, only every nth line number is printed.

    `linenowidth`
        Maximum width devoted to line numbers (default: ``3*ystep``, sufficient
        for up to 4-digit line numbers. Increase width for longer code blocks).

    `xoffset`
        Starting offset in X direction, defaults to ``0``.

    `yoffset`
        Starting offset in Y direction, defaults to the font size if it is given
        in pixels, or ``20`` else.  (This is necessary since text coordinates
        refer to the text baseline, not the top edge.)

    `ystep`
        Offset to add to the Y coordinate for each subsequent line.  This should
        roughly be the text size plus 5.  It defaults to that value if the text
        size is given in pixels, or ``25`` else.

    `spacehack`
        Convert spaces in the source to ``&#160;``, which are non-breaking
        spaces.  SVG provides the ``xml:space`` attribute to control how
        whitespace inside tags is handled, in theory, the ``preserve`` value
        could be used to keep all whitespace as-is.  However, many current SVG
        viewers don't obey that rule, so this option is provided as a workaround
        and defaults to ``True``.
    """
    name = 'SVG'
    aliases = ['svg']
    filenames = ['*.svg']

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.nowrap = get_bool_opt(options, 'nowrap', False)
        self.fontfamily = options.get('fontfamily', 'monospace')
        self.fontsize = options.get('fontsize', '14px')
        self.xoffset = get_int_opt(options, 'xoffset', 0)
        fs = self.fontsize.strip()
        if fs.endswith('px'):
            fs = fs[:-2].strip()
        try:
            int_fs = int(fs)
        except ValueError:
            int_fs = 20
        self.yoffset = get_int_opt(options, 'yoffset', int_fs)
        self.ystep = get_int_opt(options, 'ystep', int_fs + 5)
        self.spacehack = get_bool_opt(options, 'spacehack', True)
        self.linenos = get_bool_opt(options,'linenos',False)
        self.linenostart = get_int_opt(options,'linenostart',1)
        self.linenostep = get_int_opt(options,'linenostep',1)
        self.linenowidth = get_int_opt(options,'linenowidth', 3*self.ystep)
        self._stylecache = {}

    def format_unencoded(self, tokensource, outfile):
        """
        Format ``tokensource``, an iterable of ``(tokentype, tokenstring)``
        tuples and write it into ``outfile``.

        For our implementation we put all lines in their own 'line group'.
        """
        x = self.xoffset
        y = self.yoffset
        if not self.nowrap:
            if self.encoding:
                outfile.write(f'<?xml version="1.0" encoding="{self.encoding}"?>\n')
            else:
                outfile.write('<?xml version="1.0"?>\n')
            outfile.write('<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.0//EN" '
                          '"http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/'
                          'svg10.dtd">\n')
            outfile.write('<svg xmlns="http://www.w3.org/2000/svg">\n')
            outfile.write(f'<g font-family="{self.fontfamily}" font-size="{self.fontsize}">\n')

        counter = self.linenostart
        counter_step = self.linenostep
        counter_style = self._get_style(Comment)
        line_x = x

        if self.linenos:
            if counter % counter_step == 0:
                outfile.write(f'<text x="{x+self.linenowidth}" y="{y}" {counter_style} text-anchor="end">{counter}</text>')
            line_x += self.linenowidth + self.ystep
            counter += 1

        outfile.write(f'<text x="{line_x}" y="{y}" xml:space="preserve">')
        for ttype, value in tokensource:
            style = self._get_style(ttype)
            tspan = style and '<tspan' + style + '>' or ''
            tspanend = tspan and '</tspan>' or ''
            value = escape_html(value)
            if self.spacehack:
                value = value.expandtabs().replace(' ', '&#160;')
            parts = value.split('\n')
            for part in parts[:-1]:
                outfile.write(tspan + part + tspanend)
                y += self.ystep
                outfile.write('</text>\n')
                if self.linenos and counter % counter_step == 0:
                    outfile.write(f'<text x="{x+self.linenowidth}" y="{y}" text-anchor="end" {counter_style}>{counter}</text>')

                counter += 1
                outfile.write(f'<text x="{line_x}" y="{y}" ' 'xml:space="preserve">')
            outfile.write(tspan + parts[-1] + tspanend)
        outfile.write('</text>')

        if not self.nowrap:
            outfile.write('</g></svg>\n')

    def _get_style(self, tokentype):
        if tokentype in self._stylecache:
            return self._stylecache[tokentype]
        otokentype = tokentype
        while not self.style.styles_token(tokentype):
            tokentype = tokentype.parent
        value = self.style.style_for_token(tokentype)
        result = ''
        if value['color']:
            result = ' fill="#' + value['color'] + '"'
        if value['bold']:
            result += ' font-weight="bold"'
        if value['italic']:
            result += ' font-style="italic"'
        self._stylecache[otokentype] = result
        return result

# === NexusCore/openenv\Lib\site-packages\pygments\formatters\svg.py ===
"""
    pygments.formatters.svg
    ~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for SVG output.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.formatter import Formatter
from pygments.token import Comment
from pygments.util import get_bool_opt, get_int_opt

__all__ = ['SvgFormatter']


def escape_html(text):
    """Escape &, <, > as well as single and double quotes for HTML."""
    return text.replace('&', '&amp;').  \
                replace('<', '&lt;').   \
                replace('>', '&gt;').   \
                replace('"', '&quot;'). \
                replace("'", '&#39;')


class2style = {}

class SvgFormatter(Formatter):
    """
    Format tokens as an SVG graphics file.  This formatter is still experimental.
    Each line of code is a ``<text>`` element with explicit ``x`` and ``y``
    coordinates containing ``<tspan>`` elements with the individual token styles.

    By default, this formatter outputs a full SVG document including doctype
    declaration and the ``<svg>`` root element.

    .. versionadded:: 0.9

    Additional options accepted:

    `nowrap`
        Don't wrap the SVG ``<text>`` elements in ``<svg><g>`` elements and
        don't add a XML declaration and a doctype.  If true, the `fontfamily`
        and `fontsize` options are ignored.  Defaults to ``False``.

    `fontfamily`
        The value to give the wrapping ``<g>`` element's ``font-family``
        attribute, defaults to ``"monospace"``.

    `fontsize`
        The value to give the wrapping ``<g>`` element's ``font-size``
        attribute, defaults to ``"14px"``.

    `linenos`
        If ``True``, add line numbers (default: ``False``).

    `linenostart`
        The line number for the first line (default: ``1``).

    `linenostep`
        If set to a number n > 1, only every nth line number is printed.

    `linenowidth`
        Maximum width devoted to line numbers (default: ``3*ystep``, sufficient
        for up to 4-digit line numbers. Increase width for longer code blocks).

    `xoffset`
        Starting offset in X direction, defaults to ``0``.

    `yoffset`
        Starting offset in Y direction, defaults to the font size if it is given
        in pixels, or ``20`` else.  (This is necessary since text coordinates
        refer to the text baseline, not the top edge.)

    `ystep`
        Offset to add to the Y coordinate for each subsequent line.  This should
        roughly be the text size plus 5.  It defaults to that value if the text
        size is given in pixels, or ``25`` else.

    `spacehack`
        Convert spaces in the source to ``&#160;``, which are non-breaking
        spaces.  SVG provides the ``xml:space`` attribute to control how
        whitespace inside tags is handled, in theory, the ``preserve`` value
        could be used to keep all whitespace as-is.  However, many current SVG
        viewers don't obey that rule, so this option is provided as a workaround
        and defaults to ``True``.
    """
    name = 'SVG'
    aliases = ['svg']
    filenames = ['*.svg']

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.nowrap = get_bool_opt(options, 'nowrap', False)
        self.fontfamily = options.get('fontfamily', 'monospace')
        self.fontsize = options.get('fontsize', '14px')
        self.xoffset = get_int_opt(options, 'xoffset', 0)
        fs = self.fontsize.strip()
        if fs.endswith('px'):
            fs = fs[:-2].strip()
        try:
            int_fs = int(fs)
        except ValueError:
            int_fs = 20
        self.yoffset = get_int_opt(options, 'yoffset', int_fs)
        self.ystep = get_int_opt(options, 'ystep', int_fs + 5)
        self.spacehack = get_bool_opt(options, 'spacehack', True)
        self.linenos = get_bool_opt(options,'linenos',False)
        self.linenostart = get_int_opt(options,'linenostart',1)
        self.linenostep = get_int_opt(options,'linenostep',1)
        self.linenowidth = get_int_opt(options,'linenowidth', 3*self.ystep)
        self._stylecache = {}

    def format_unencoded(self, tokensource, outfile):
        """
        Format ``tokensource``, an iterable of ``(tokentype, tokenstring)``
        tuples and write it into ``outfile``.

        For our implementation we put all lines in their own 'line group'.
        """
        x = self.xoffset
        y = self.yoffset
        if not self.nowrap:
            if self.encoding:
                outfile.write(f'<?xml version="1.0" encoding="{self.encoding}"?>\n')
            else:
                outfile.write('<?xml version="1.0"?>\n')
            outfile.write('<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.0//EN" '
                          '"http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/'
                          'svg10.dtd">\n')
            outfile.write('<svg xmlns="http://www.w3.org/2000/svg">\n')
            outfile.write(f'<g font-family="{self.fontfamily}" font-size="{self.fontsize}">\n')

        counter = self.linenostart
        counter_step = self.linenostep
        counter_style = self._get_style(Comment)
        line_x = x

        if self.linenos:
            if counter % counter_step == 0:
                outfile.write(f'<text x="{x+self.linenowidth}" y="{y}" {counter_style} text-anchor="end">{counter}</text>')
            line_x += self.linenowidth + self.ystep
            counter += 1

        outfile.write(f'<text x="{line_x}" y="{y}" xml:space="preserve">')
        for ttype, value in tokensource:
            style = self._get_style(ttype)
            tspan = style and '<tspan' + style + '>' or ''
            tspanend = tspan and '</tspan>' or ''
            value = escape_html(value)
            if self.spacehack:
                value = value.expandtabs().replace(' ', '&#160;')
            parts = value.split('\n')
            for part in parts[:-1]:
                outfile.write(tspan + part + tspanend)
                y += self.ystep
                outfile.write('</text>\n')
                if self.linenos and counter % counter_step == 0:
                    outfile.write(f'<text x="{x+self.linenowidth}" y="{y}" text-anchor="end" {counter_style}>{counter}</text>')

                counter += 1
                outfile.write(f'<text x="{line_x}" y="{y}" ' 'xml:space="preserve">')
            outfile.write(tspan + parts[-1] + tspanend)
        outfile.write('</text>')

        if not self.nowrap:
            outfile.write('</g></svg>\n')

    def _get_style(self, tokentype):
        if tokentype in self._stylecache:
            return self._stylecache[tokentype]
        otokentype = tokentype
        while not self.style.styles_token(tokentype):
            tokentype = tokentype.parent
        value = self.style.style_for_token(tokentype)
        result = ''
        if value['color']:
            result = ' fill="#' + value['color'] + '"'
        if value['bold']:
            result += ' font-weight="bold"'
        if value['italic']:
            result += ' font-style="italic"'
        self._stylecache[otokentype] = result
        return result

# === NexusCore/openenv\Lib\site-packages\win32\Demos\service\pipeTestService.py ===
# A Demo of services and named pipes.

# A multi-threaded service that simply echos back its input.

# * Install as a service using "pipeTestService.py install"
# * Use Control Panel to change the user name of the service
#   to a real user name (ie, NOT the SystemAccount)
# * Start the service.
# * Run the "pipeTestServiceClient.py" program as the client pipe side.

import _thread
import traceback

import pywintypes

# Old versions of the service framework would not let you import this
# module at the top-level.  Now you can, and can check 'servicemanager.Debugging()'
# and 'servicemanager.RunningAsService()' to check your context.
import servicemanager
import win32con
import win32service
import win32serviceutil
import winerror

# # Use "import *" to keep this looking as much as a "normal" service
# as possible.  Real code shouldn't do this.
from ntsecuritycon import *  # nopycln: import
from win32api import *  # nopycln: import
from win32event import *  # nopycln: import
from win32file import *  # nopycln: import
from win32pipe import *  # nopycln: import


def ApplyIgnoreError(fn, args):
    try:
        return fn(*args)
    except error:  # Ignore win32api errors.
        return None


class TestPipeService(win32serviceutil.ServiceFramework):
    _svc_name_ = "PyPipeTestService"
    _svc_display_name_ = "Python Pipe Test Service"
    _svc_description_ = "Tests Python service framework by receiving and echoing messages over a named pipe"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = CreateEvent(None, 0, 0, None)
        self.overlapped = pywintypes.OVERLAPPED()
        self.overlapped.hEvent = CreateEvent(None, 0, 0, None)
        self.thread_handles = []

    def CreatePipeSecurityObject(self):
        # Create a security object giving World read/write access,
        # but only "Owner" modify access.
        sa = pywintypes.SECURITY_ATTRIBUTES()
        sidEveryone = pywintypes.SID()
        sidEveryone.Initialize(SECURITY_WORLD_SID_AUTHORITY, 1)
        sidEveryone.SetSubAuthority(0, SECURITY_WORLD_RID)
        sidCreator = pywintypes.SID()
        sidCreator.Initialize(SECURITY_CREATOR_SID_AUTHORITY, 1)
        sidCreator.SetSubAuthority(0, SECURITY_CREATOR_OWNER_RID)

        acl = pywintypes.ACL()
        acl.AddAccessAllowedAce(FILE_GENERIC_READ | FILE_GENERIC_WRITE, sidEveryone)
        acl.AddAccessAllowedAce(FILE_ALL_ACCESS, sidCreator)

        sa.SetSecurityDescriptorDacl(1, acl, 0)
        return sa

    # The functions executed in their own thread to process a client request.
    def DoProcessClient(self, pipeHandle, tid):
        try:
            try:
                # Create a loop, reading large data.  If we knew the data stream was
                # was small, a simple ReadFile would do.
                d = b""
                hr = winerror.ERROR_MORE_DATA
                while hr == winerror.ERROR_MORE_DATA:
                    hr, thisd = ReadFile(pipeHandle, 256)
                    d += thisd
                print("Read", d)
                ok = 1
            except error:
                # Client disconnection - do nothing
                ok = 0

            # A secure service would handle (and ignore!) errors writing to the
            # pipe, but for the sake of this demo we don't (if only to see what errors
            # we can get when our clients break at strange times :-)
            if ok:
                msg = (
                    "%s (on thread %d) sent me %s"
                    % (GetNamedPipeHandleState(pipeHandle, False, True)[4], tid, d)
                ).encode("ascii")
                WriteFile(pipeHandle, msg)
        finally:
            ApplyIgnoreError(DisconnectNamedPipe, (pipeHandle,))
            ApplyIgnoreError(CloseHandle, (pipeHandle,))

    def ProcessClient(self, pipeHandle):
        try:
            procHandle = GetCurrentProcess()
            th = DuplicateHandle(
                procHandle,
                GetCurrentThread(),
                procHandle,
                0,
                0,
                win32con.DUPLICATE_SAME_ACCESS,
            )
            try:
                self.thread_handles.append(th)
                try:
                    return self.DoProcessClient(pipeHandle, th)
                except:
                    traceback.print_exc()
            finally:
                self.thread_handles.remove(th)
        except:
            traceback.print_exc()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        # Write an event log record - in debug mode we will also
        # see this message printed.
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )

        num_connections = 0
        while 1:
            pipeHandle = CreateNamedPipe(
                "\\\\.\\pipe\\PyPipeTest",
                PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED,
                PIPE_TYPE_MESSAGE | PIPE_READMODE_BYTE,
                PIPE_UNLIMITED_INSTANCES,  # max instances
                0,
                0,
                6000,
                self.CreatePipeSecurityObject(),
            )
            try:
                hr = ConnectNamedPipe(pipeHandle, self.overlapped)
            except error as details:
                print("Error connecting pipe!", details)
                CloseHandle(pipeHandle)
                break
            if hr == winerror.ERROR_PIPE_CONNECTED:
                # Client is already connected - signal event
                SetEvent(self.overlapped.hEvent)
            rc = WaitForMultipleObjects(
                (self.hWaitStop, self.overlapped.hEvent), 0, INFINITE
            )
            if rc == WAIT_OBJECT_0:
                # Stop event
                break
            else:
                # Pipe event - spawn thread to deal with it.
                _thread.start_new_thread(self.ProcessClient, (pipeHandle,))
                num_connections += 1

        # Sleep to ensure that any new threads are in the list, and then
        # wait for all current threads to finish.
        # What is a better way?
        Sleep(500)
        while self.thread_handles:
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING, 5000)
            print("Waiting for %d threads to finish..." % (len(self.thread_handles)))
            WaitForMultipleObjects(self.thread_handles, 1, 3000)
        # Write another event log record.
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPED,
            (self._svc_name_, " after processing %d connections" % (num_connections,)),
        )


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(TestPipeService)

# === NexusCore/openenv\Lib\site-packages\win32com\test\testAccess.py ===
#
# This assumes that you have MSAccess and DAO installed.
#  You need to run makepy.py over "msaccess.tlb" and
#  "dao3032.dll", and ensure the generated files are on the
#  path.

# You can run this with no args, and a test database will be generated.
# You can optionally pass a dbname on the command line, in which case it will be dumped.

import os
import sys

import pythoncom
import win32api
from win32com.client import Dispatch, constants, gencache


def CreateTestAccessDatabase(dbname=None):
    # Creates a test access database - returns the filename.
    if dbname is None:
        dbname = os.path.join(win32api.GetTempPath(), "COMTestSuiteTempDatabase.mdb")

    access = Dispatch("Access.Application")
    dbEngine = access.DBEngine
    workspace = dbEngine.Workspaces(0)

    try:
        os.unlink(dbname)
    except OSError:
        print(
            "WARNING - Unable to delete old test database - expect a COM exception RSN!"
        )

    newdb = workspace.CreateDatabase(
        dbname, constants.dbLangGeneral, constants.dbEncrypt
    )

    # Create one test table.
    table = newdb.CreateTableDef("Test Table 1")
    table.Fields.Append(table.CreateField("First Name", constants.dbText))
    table.Fields.Append(table.CreateField("Last Name", constants.dbText))

    index = table.CreateIndex("UniqueIndex")
    index.Fields.Append(index.CreateField("First Name"))
    index.Fields.Append(index.CreateField("Last Name"))
    index.Unique = -1
    table.Indexes.Append(index)

    newdb.TableDefs.Append(table)

    # Create a second test table.
    table = newdb.CreateTableDef("Test Table 2")
    table.Fields.Append(table.CreateField("First Name", constants.dbText))
    table.Fields.Append(table.CreateField("Last Name", constants.dbText))

    newdb.TableDefs.Append(table)

    # Create a relationship between them
    relation = newdb.CreateRelation("TestRelationship")
    relation.Table = "Test Table 1"
    relation.ForeignTable = "Test Table 2"

    field = relation.CreateField("First Name")
    field.ForeignName = "First Name"
    relation.Fields.Append(field)

    field = relation.CreateField("Last Name")
    field.ForeignName = "Last Name"
    relation.Fields.Append(field)

    relation.Attributes = (
        constants.dbRelationDeleteCascade + constants.dbRelationUpdateCascade
    )

    newdb.Relations.Append(relation)

    # Finally we can add some data to the table.
    tab1 = newdb.OpenRecordset("Test Table 1")
    tab1.AddNew()
    tab1.Fields("First Name").Value = "Mark"
    tab1.Fields("Last Name").Value = "Hammond"
    tab1.Update()

    tab1.MoveFirst()
    # We do a simple bookmark test which tests our optimized VT_SAFEARRAY|VT_UI1 support.
    # The bookmark will be a buffer object - remember it for later.
    bk = tab1.Bookmark

    # Add a second record.
    tab1.AddNew()
    tab1.Fields("First Name").Value = "Second"
    tab1.Fields("Last Name").Value = "Person"
    tab1.Update()

    # Reset the bookmark to the one we saved.
    # But first check the test is actually doing something!
    tab1.MoveLast()
    assert (
        tab1.Fields("First Name").Value == "Second"
    ), "Unexpected record is last - makes bookmark test pointless!"

    tab1.Bookmark = bk
    assert tab1.Bookmark == bk, "The bookmark data is not the same"
    assert (
        tab1.Fields("First Name").Value == "Mark"
    ), "The bookmark did not reset the record pointer correctly"

    return dbname


def DoDumpAccessInfo(dbname):
    from . import daodump

    a = forms = None
    try:
        sys.stderr.write("Creating Access Application...\n")
        a = Dispatch("Access.Application")
        print("Opening database %s" % dbname)
        a.OpenCurrentDatabase(dbname)
        db = a.CurrentDb()
        daodump.DumpDB(db, 1)
        forms = a.Forms
        print("There are %d forms open." % (len(forms)))
        # Uncommenting these lines means Access remains open.
        # for form in forms:
        #     print(f" {form.Name}")
        reports = a.Reports
        print("There are %d reports open" % (len(reports)))
    finally:
        if not a is None:
            sys.stderr.write("Closing database\n")
            try:
                a.CloseCurrentDatabase()
            except pythoncom.com_error:
                pass


# Generate all the support we can.
def GenerateSupport():
    # dao
    gencache.EnsureModule("{00025E01-0000-0000-C000-000000000046}", 0, 4, 0)
    # Access
    #       gencache.EnsureModule("{4AFFC9A0-5F99-101B-AF4E-00AA003F0F07}", 0, 8, 0)
    gencache.EnsureDispatch("Access.Application")


def DumpAccessInfo(dbname):
    amod = gencache.GetModuleForProgID("Access.Application")
    dmod = gencache.GetModuleForProgID("DAO.DBEngine.35")
    if amod is None and dmod is None:
        DoDumpAccessInfo(dbname)
        # Now generate all the support we can.
        GenerateSupport()
    else:
        sys.stderr.write(
            "testAccess not doing dynamic test, as generated code already exists\n"
        )
    # Now a generated version.
    DoDumpAccessInfo(dbname)


def test(dbname=None):
    if dbname is None:
        # We need makepy support to create a database (just for the constants!)
        try:
            GenerateSupport()
        except pythoncom.com_error:
            print("*** Can not import the MSAccess type libraries - tests skipped")
            return
        dbname = CreateTestAccessDatabase()
        print("A test database at '%s' was created" % dbname)

    DumpAccessInfo(dbname)


if __name__ == "__main__":
    from .util import CheckClean

    dbname = None
    if len(sys.argv) > 1:
        dbname = sys.argv[1]

    test(dbname)

    CheckClean()