
# === NexusCore/tools\exports\export_20250803_114325\combined_187.py ===

# === NexusCore/openenv\Lib\site-packages\openai\resources\beta\threads\runs\steps.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import typing_extensions
from typing import List
from typing_extensions import Literal

import httpx

from ..... import _legacy_response
from ....._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ....._utils import maybe_transform, async_maybe_transform
from ....._compat import cached_property
from ....._resource import SyncAPIResource, AsyncAPIResource
from ....._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from .....pagination import SyncCursorPage, AsyncCursorPage
from ....._base_client import AsyncPaginator, make_request_options
from .....types.beta.threads.runs import step_list_params, step_retrieve_params
from .....types.beta.threads.runs.run_step import RunStep
from .....types.beta.threads.runs.run_step_include import RunStepInclude

__all__ = ["Steps", "AsyncSteps"]


class Steps(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> StepsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return StepsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> StepsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return StepsWithStreamingResponse(self)

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def retrieve(
        self,
        step_id: str,
        *,
        thread_id: str,
        run_id: str,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> RunStep:
        """
        Retrieves a run step.

        Args:
          include: A list of additional fields to include in the response. Currently the only
              supported value is `step_details.tool_calls[*].file_search.results[*].content`
              to fetch the file search result content.

              See the
              [file search tool documentation](https://platform.openai.com/docs/assistants/tools/file-search#customizing-file-search-settings)
              for more information.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        if not step_id:
            raise ValueError(f"Expected a non-empty value for `step_id` but received {step_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get(
            f"/threads/{thread_id}/runs/{run_id}/steps/{step_id}",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform({"include": include}, step_retrieve_params.StepRetrieveParams),
            ),
            cast_to=RunStep,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def list(
        self,
        run_id: str,
        *,
        thread_id: str,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[RunStep]:
        """
        Returns a list of run steps belonging to a run.

        Args:
          after: A cursor for use in pagination. `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          before: A cursor for use in pagination. `before` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              starting with obj_foo, your subsequent call can include before=obj_foo in order
              to fetch the previous page of the list.

          include: A list of additional fields to include in the response. Currently the only
              supported value is `step_details.tool_calls[*].file_search.results[*].content`
              to fetch the file search result content.

              See the
              [file search tool documentation](https://platform.openai.com/docs/assistants/tools/file-search#customizing-file-search-settings)
              for more information.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            f"/threads/{thread_id}/runs/{run_id}/steps",
            page=SyncCursorPage[RunStep],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "include": include,
                        "limit": limit,
                        "order": order,
                    },
                    step_list_params.StepListParams,
                ),
            ),
            model=RunStep,
        )


class AsyncSteps(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncStepsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncStepsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncStepsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncStepsWithStreamingResponse(self)

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def retrieve(
        self,
        step_id: str,
        *,
        thread_id: str,
        run_id: str,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> RunStep:
        """
        Retrieves a run step.

        Args:
          include: A list of additional fields to include in the response. Currently the only
              supported value is `step_details.tool_calls[*].file_search.results[*].content`
              to fetch the file search result content.

              See the
              [file search tool documentation](https://platform.openai.com/docs/assistants/tools/file-search#customizing-file-search-settings)
              for more information.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        if not step_id:
            raise ValueError(f"Expected a non-empty value for `step_id` but received {step_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._get(
            f"/threads/{thread_id}/runs/{run_id}/steps/{step_id}",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=await async_maybe_transform({"include": include}, step_retrieve_params.StepRetrieveParams),
            ),
            cast_to=RunStep,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def list(
        self,
        run_id: str,
        *,
        thread_id: str,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[RunStep, AsyncCursorPage[RunStep]]:
        """
        Returns a list of run steps belonging to a run.

        Args:
          after: A cursor for use in pagination. `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          before: A cursor for use in pagination. `before` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              starting with obj_foo, your subsequent call can include before=obj_foo in order
              to fetch the previous page of the list.

          include: A list of additional fields to include in the response. Currently the only
              supported value is `step_details.tool_calls[*].file_search.results[*].content`
              to fetch the file search result content.

              See the
              [file search tool documentation](https://platform.openai.com/docs/assistants/tools/file-search#customizing-file-search-settings)
              for more information.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            f"/threads/{thread_id}/runs/{run_id}/steps",
            page=AsyncCursorPage[RunStep],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "include": include,
                        "limit": limit,
                        "order": order,
                    },
                    step_list_params.StepListParams,
                ),
            ),
            model=RunStep,
        )


class StepsWithRawResponse:
    def __init__(self, steps: Steps) -> None:
        self._steps = steps

        self.retrieve = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                steps.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                steps.list  # pyright: ignore[reportDeprecated],
            )
        )


class AsyncStepsWithRawResponse:
    def __init__(self, steps: AsyncSteps) -> None:
        self._steps = steps

        self.retrieve = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                steps.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                steps.list  # pyright: ignore[reportDeprecated],
            )
        )


class StepsWithStreamingResponse:
    def __init__(self, steps: Steps) -> None:
        self._steps = steps

        self.retrieve = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                steps.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                steps.list  # pyright: ignore[reportDeprecated],
            )
        )


class AsyncStepsWithStreamingResponse:
    def __init__(self, steps: AsyncSteps) -> None:
        self._steps = steps

        self.retrieve = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                steps.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                steps.list  # pyright: ignore[reportDeprecated],
            )
        )

# === NexusCore/openenv\Lib\site-packages\dotenv\main.py ===
import io
import logging
import os
import pathlib
import shutil
import sys
import tempfile
from collections import OrderedDict
from contextlib import contextmanager
from typing import IO, Dict, Iterable, Iterator, Mapping, Optional, Tuple, Union

from .parser import Binding, parse_stream
from .variables import parse_variables

# A type alias for a string path to be used for the paths in this file.
# These paths may flow to `open()` and `shutil.move()`; `shutil.move()`
# only accepts string paths, not byte paths or file descriptors. See
# https://github.com/python/typeshed/pull/6832.
StrPath = Union[str, "os.PathLike[str]"]

logger = logging.getLogger(__name__)


def with_warn_for_invalid_lines(mappings: Iterator[Binding]) -> Iterator[Binding]:
    for mapping in mappings:
        if mapping.error:
            logger.warning(
                "python-dotenv could not parse statement starting at line %s",
                mapping.original.line,
            )
        yield mapping


class DotEnv:
    def __init__(
        self,
        dotenv_path: Optional[StrPath],
        stream: Optional[IO[str]] = None,
        verbose: bool = False,
        encoding: Optional[str] = None,
        interpolate: bool = True,
        override: bool = True,
    ) -> None:
        self.dotenv_path: Optional[StrPath] = dotenv_path
        self.stream: Optional[IO[str]] = stream
        self._dict: Optional[Dict[str, Optional[str]]] = None
        self.verbose: bool = verbose
        self.encoding: Optional[str] = encoding
        self.interpolate: bool = interpolate
        self.override: bool = override

    @contextmanager
    def _get_stream(self) -> Iterator[IO[str]]:
        if self.dotenv_path and os.path.isfile(self.dotenv_path):
            with open(self.dotenv_path, encoding=self.encoding) as stream:
                yield stream
        elif self.stream is not None:
            yield self.stream
        else:
            if self.verbose:
                logger.info(
                    "python-dotenv could not find configuration file %s.",
                    self.dotenv_path or ".env",
                )
            yield io.StringIO("")

    def dict(self) -> Dict[str, Optional[str]]:
        """Return dotenv as dict"""
        if self._dict:
            return self._dict

        raw_values = self.parse()

        if self.interpolate:
            self._dict = OrderedDict(
                resolve_variables(raw_values, override=self.override)
            )
        else:
            self._dict = OrderedDict(raw_values)

        return self._dict

    def parse(self) -> Iterator[Tuple[str, Optional[str]]]:
        with self._get_stream() as stream:
            for mapping in with_warn_for_invalid_lines(parse_stream(stream)):
                if mapping.key is not None:
                    yield mapping.key, mapping.value

    def set_as_environment_variables(self) -> bool:
        """
        Load the current dotenv as system environment variable.
        """
        if not self.dict():
            return False

        for k, v in self.dict().items():
            if k in os.environ and not self.override:
                continue
            if v is not None:
                os.environ[k] = v

        return True

    def get(self, key: str) -> Optional[str]:
        """ """
        data = self.dict()

        if key in data:
            return data[key]

        if self.verbose:
            logger.warning("Key %s not found in %s.", key, self.dotenv_path)

        return None


def get_key(
    dotenv_path: StrPath,
    key_to_get: str,
    encoding: Optional[str] = "utf-8",
) -> Optional[str]:
    """
    Get the value of a given key from the given .env.

    Returns `None` if the key isn't found or doesn't have a value.
    """
    return DotEnv(dotenv_path, verbose=True, encoding=encoding).get(key_to_get)


@contextmanager
def rewrite(
    path: StrPath,
    encoding: Optional[str],
) -> Iterator[Tuple[IO[str], IO[str]]]:
    pathlib.Path(path).touch()

    with tempfile.NamedTemporaryFile(mode="w", encoding=encoding, delete=False) as dest:
        error = None
        try:
            with open(path, encoding=encoding) as source:
                yield (source, dest)
        except BaseException as err:
            error = err

    if error is None:
        shutil.move(dest.name, path)
    else:
        os.unlink(dest.name)
        raise error from None


def set_key(
    dotenv_path: StrPath,
    key_to_set: str,
    value_to_set: str,
    quote_mode: str = "always",
    export: bool = False,
    encoding: Optional[str] = "utf-8",
) -> Tuple[Optional[bool], str, str]:
    """
    Adds or Updates a key/value to the given .env

    If the .env path given doesn't exist, fails instead of risking creating
    an orphan .env somewhere in the filesystem
    """
    if quote_mode not in ("always", "auto", "never"):
        raise ValueError(f"Unknown quote_mode: {quote_mode}")

    quote = quote_mode == "always" or (
        quote_mode == "auto" and not value_to_set.isalnum()
    )

    if quote:
        value_out = "'{}'".format(value_to_set.replace("'", "\\'"))
    else:
        value_out = value_to_set
    if export:
        line_out = f"export {key_to_set}={value_out}\n"
    else:
        line_out = f"{key_to_set}={value_out}\n"

    with rewrite(dotenv_path, encoding=encoding) as (source, dest):
        replaced = False
        missing_newline = False
        for mapping in with_warn_for_invalid_lines(parse_stream(source)):
            if mapping.key == key_to_set:
                dest.write(line_out)
                replaced = True
            else:
                dest.write(mapping.original.string)
                missing_newline = not mapping.original.string.endswith("\n")
        if not replaced:
            if missing_newline:
                dest.write("\n")
            dest.write(line_out)

    return True, key_to_set, value_to_set


def unset_key(
    dotenv_path: StrPath,
    key_to_unset: str,
    quote_mode: str = "always",
    encoding: Optional[str] = "utf-8",
) -> Tuple[Optional[bool], str]:
    """
    Removes a given key from the given `.env` file.

    If the .env path given doesn't exist, fails.
    If the given key doesn't exist in the .env, fails.
    """
    if not os.path.exists(dotenv_path):
        logger.warning("Can't delete from %s - it doesn't exist.", dotenv_path)
        return None, key_to_unset

    removed = False
    with rewrite(dotenv_path, encoding=encoding) as (source, dest):
        for mapping in with_warn_for_invalid_lines(parse_stream(source)):
            if mapping.key == key_to_unset:
                removed = True
            else:
                dest.write(mapping.original.string)

    if not removed:
        logger.warning(
            "Key %s not removed from %s - key doesn't exist.", key_to_unset, dotenv_path
        )
        return None, key_to_unset

    return removed, key_to_unset


def resolve_variables(
    values: Iterable[Tuple[str, Optional[str]]],
    override: bool,
) -> Mapping[str, Optional[str]]:
    new_values: Dict[str, Optional[str]] = {}

    for name, value in values:
        if value is None:
            result = None
        else:
            atoms = parse_variables(value)
            env: Dict[str, Optional[str]] = {}
            if override:
                env.update(os.environ)  # type: ignore
                env.update(new_values)
            else:
                env.update(new_values)
                env.update(os.environ)  # type: ignore
            result = "".join(atom.resolve(env) for atom in atoms)

        new_values[name] = result

    return new_values


def _walk_to_root(path: str) -> Iterator[str]:
    """
    Yield directories starting from the given directory up to the root
    """
    if not os.path.exists(path):
        raise IOError("Starting path not found")

    if os.path.isfile(path):
        path = os.path.dirname(path)

    last_dir = None
    current_dir = os.path.abspath(path)
    while last_dir != current_dir:
        yield current_dir
        parent_dir = os.path.abspath(os.path.join(current_dir, os.path.pardir))
        last_dir, current_dir = current_dir, parent_dir


def find_dotenv(
    filename: str = ".env",
    raise_error_if_not_found: bool = False,
    usecwd: bool = False,
) -> str:
    """
    Search in increasingly higher folders for the given file

    Returns path to the file if found, or an empty string otherwise
    """

    def _is_interactive():
        """Decide whether this is running in a REPL or IPython notebook"""
        try:
            main = __import__("__main__", None, None, fromlist=["__file__"])
        except ModuleNotFoundError:
            return False
        return not hasattr(main, "__file__")

    def _is_debugger():
        return sys.gettrace() is not None

    if usecwd or _is_interactive() or _is_debugger() or getattr(sys, "frozen", False):
        # Should work without __file__, e.g. in REPL or IPython notebook.
        path = os.getcwd()
    else:
        # will work for .py files
        frame = sys._getframe()
        current_file = __file__

        while frame.f_code.co_filename == current_file or not os.path.exists(
            frame.f_code.co_filename
        ):
            assert frame.f_back is not None
            frame = frame.f_back
        frame_filename = frame.f_code.co_filename
        path = os.path.dirname(os.path.abspath(frame_filename))

    for dirname in _walk_to_root(path):
        check_path = os.path.join(dirname, filename)
        if os.path.isfile(check_path):
            return check_path

    if raise_error_if_not_found:
        raise IOError("File not found")

    return ""


def load_dotenv(
    dotenv_path: Optional[StrPath] = None,
    stream: Optional[IO[str]] = None,
    verbose: bool = False,
    override: bool = False,
    interpolate: bool = True,
    encoding: Optional[str] = "utf-8",
) -> bool:
    """Parse a .env file and then load all the variables found as environment variables.

    Parameters:
        dotenv_path: Absolute or relative path to .env file.
        stream: Text stream (such as `io.StringIO`) with .env content, used if
            `dotenv_path` is `None`.
        verbose: Whether to output a warning the .env file is missing.
        override: Whether to override the system environment variables with the variables
            from the `.env` file.
        encoding: Encoding to be used to read the file.
    Returns:
        Bool: True if at least one environment variable is set else False

    If both `dotenv_path` and `stream` are `None`, `find_dotenv()` is used to find the
    .env file with it's default parameters. If you need to change the default parameters
    of `find_dotenv()`, you can explicitly call `find_dotenv()` and pass the result
    to this function as `dotenv_path`.
    """
    if dotenv_path is None and stream is None:
        dotenv_path = find_dotenv()

    dotenv = DotEnv(
        dotenv_path=dotenv_path,
        stream=stream,
        verbose=verbose,
        interpolate=interpolate,
        override=override,
        encoding=encoding,
    )
    return dotenv.set_as_environment_variables()


def dotenv_values(
    dotenv_path: Optional[StrPath] = None,
    stream: Optional[IO[str]] = None,
    verbose: bool = False,
    interpolate: bool = True,
    encoding: Optional[str] = "utf-8",
) -> Dict[str, Optional[str]]:
    """
    Parse a .env file and return its content as a dict.

    The returned dict will have `None` values for keys without values in the .env file.
    For example, `foo=bar` results in `{"foo": "bar"}` whereas `foo` alone results in
    `{"foo": None}`

    Parameters:
        dotenv_path: Absolute or relative path to the .env file.
        stream: `StringIO` object with .env content, used if `dotenv_path` is `None`.
        verbose: Whether to output a warning if the .env file is missing.
        encoding: Encoding to be used to read the file.

    If both `dotenv_path` and `stream` are `None`, `find_dotenv()` is used to find the
    .env file.
    """
    if dotenv_path is None and stream is None:
        dotenv_path = find_dotenv()

    return DotEnv(
        dotenv_path=dotenv_path,
        stream=stream,
        verbose=verbose,
        interpolate=interpolate,
        override=True,
        encoding=encoding,
    ).dict()

# === NexusCore/openenv\Lib\site-packages\gitdb\util.py ===
# Copyright (C) 2010, 2011 Sebastian Thiel (byronimo@gmail.com) and contributors
#
# This module is part of GitDB and is released under
# the New BSD License: https://opensource.org/license/bsd-3-clause/
import binascii
import os
import mmap
import sys
import time
import errno

from io import BytesIO

from smmap import (
    StaticWindowMapManager,
    SlidingWindowMapManager,
    SlidingWindowMapBuffer
)

# initialize our global memory manager instance
# Use it to free cached (and unused) resources.
mman = SlidingWindowMapManager()
# END handle mman

import hashlib

try:
    from struct import unpack_from
except ImportError:
    from struct import unpack, calcsize
    __calcsize_cache = dict()

    def unpack_from(fmt, data, offset=0):
        try:
            size = __calcsize_cache[fmt]
        except KeyError:
            size = calcsize(fmt)
            __calcsize_cache[fmt] = size
        # END exception handling
        return unpack(fmt, data[offset: offset + size])
    # END own unpack_from implementation


#{ Aliases

hex_to_bin = binascii.a2b_hex
bin_to_hex = binascii.b2a_hex

# errors
ENOENT = errno.ENOENT

# os shortcuts
exists = os.path.exists
mkdir = os.mkdir
chmod = os.chmod
isdir = os.path.isdir
isfile = os.path.isfile
rename = os.rename
dirname = os.path.dirname
basename = os.path.basename
join = os.path.join
read = os.read
write = os.write
close = os.close
fsync = os.fsync


def _retry(func, *args, **kwargs):
    # Wrapper around functions, that are problematic on "Windows". Sometimes
    # the OS or someone else has still a handle to the file
    if sys.platform == "win32":
        for _ in range(10):
            try:
                return func(*args, **kwargs)
            except Exception:
                time.sleep(0.1)
        return func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


def remove(*args, **kwargs):
    return _retry(os.remove, *args, **kwargs)


# Backwards compatibility imports
from gitdb.const import (
    NULL_BIN_SHA,
    NULL_HEX_SHA
)

#} END Aliases

#{ compatibility stuff ...


class _RandomAccessBytesIO:

    """Wrapper to provide required functionality in case memory maps cannot or may
    not be used. This is only really required in python 2.4"""
    __slots__ = '_sio'

    def __init__(self, buf=''):
        self._sio = BytesIO(buf)

    def __getattr__(self, attr):
        return getattr(self._sio, attr)

    def __len__(self):
        return len(self.getvalue())

    def __getitem__(self, i):
        return self.getvalue()[i]

    def __getslice__(self, start, end):
        return self.getvalue()[start:end]


def byte_ord(b):
    """
    Return the integer representation of the byte string.  This supports Python
    3 byte arrays as well as standard strings.
    """
    try:
        return ord(b)
    except TypeError:
        return b

#} END compatibility stuff ...

#{ Routines


def make_sha(source=b''):
    """A python2.4 workaround for the sha/hashlib module fiasco

    **Note** From the dulwich project """
    try:
        return hashlib.sha1(source)
    except NameError:
        import sha
        sha1 = sha.sha(source)
        return sha1


def allocate_memory(size):
    """:return: a file-protocol accessible memory block of the given size"""
    if size == 0:
        return _RandomAccessBytesIO(b'')
    # END handle empty chunks gracefully

    try:
        return mmap.mmap(-1, size)  # read-write by default
    except OSError:
        # setup real memory instead
        # this of course may fail if the amount of memory is not available in
        # one chunk - would only be the case in python 2.4, being more likely on
        # 32 bit systems.
        return _RandomAccessBytesIO(b"\0" * size)
    # END handle memory allocation


def file_contents_ro(fd, stream=False, allow_mmap=True):
    """:return: read-only contents of the file represented by the file descriptor fd

    :param fd: file descriptor opened for reading
    :param stream: if False, random access is provided, otherwise the stream interface
        is provided.
    :param allow_mmap: if True, its allowed to map the contents into memory, which
        allows large files to be handled and accessed efficiently. The file-descriptor
        will change its position if this is False"""
    try:
        if allow_mmap:
            # supports stream and random access
            try:
                return mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
            except OSError:
                # python 2.4 issue, 0 wants to be the actual size
                return mmap.mmap(fd, os.fstat(fd).st_size, access=mmap.ACCESS_READ)
            # END handle python 2.4
    except OSError:
        pass
    # END exception handling

    # read manually
    contents = os.read(fd, os.fstat(fd).st_size)
    if stream:
        return _RandomAccessBytesIO(contents)
    return contents


def file_contents_ro_filepath(filepath, stream=False, allow_mmap=True, flags=0):
    """Get the file contents at filepath as fast as possible

    :return: random access compatible memory of the given filepath
    :param stream: see ``file_contents_ro``
    :param allow_mmap: see ``file_contents_ro``
    :param flags: additional flags to pass to os.open
    :raise OSError: If the file could not be opened

    **Note** for now we don't try to use O_NOATIME directly as the right value needs to be
    shared per database in fact. It only makes a real difference for loose object
    databases anyway, and they use it with the help of the ``flags`` parameter"""
    fd = os.open(filepath, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | flags)
    try:
        return file_contents_ro(fd, stream, allow_mmap)
    finally:
        close(fd)
    # END assure file is closed


def sliding_ro_buffer(filepath, flags=0):
    """
    :return: a buffer compatible object which uses our mapped memory manager internally
        ready to read the whole given filepath"""
    return SlidingWindowMapBuffer(mman.make_cursor(filepath), flags=flags)


def to_hex_sha(sha):
    """:return: hexified version  of sha"""
    if len(sha) == 40:
        return sha
    return bin_to_hex(sha)


def to_bin_sha(sha):
    if len(sha) == 20:
        return sha
    return hex_to_bin(sha)


#} END routines


#{ Utilities

class LazyMixin:

    """
    Base class providing an interface to lazily retrieve attribute values upon
    first access. If slots are used, memory will only be reserved once the attribute
    is actually accessed and retrieved the first time. All future accesses will
    return the cached value as stored in the Instance's dict or slot.
    """

    __slots__ = tuple()

    def __getattr__(self, attr):
        """
        Whenever an attribute is requested that we do not know, we allow it
        to be created and set. Next time the same attribute is requested, it is simply
        returned from our dict/slots. """
        self._set_cache_(attr)
        # will raise in case the cache was not created
        return object.__getattribute__(self, attr)

    def _set_cache_(self, attr):
        """
        This method should be overridden in the derived class.
        It should check whether the attribute named by attr can be created
        and cached. Do nothing if you do not know the attribute or call your subclass

        The derived class may create as many additional attributes as it deems
        necessary in case a git command returns more information than represented
        in the single attribute."""
        pass


class LockedFD:

    """
    This class facilitates a safe read and write operation to a file on disk.
    If we write to 'file', we obtain a lock file at 'file.lock' and write to
    that instead. If we succeed, the lock file will be renamed to overwrite
    the original file.

    When reading, we obtain a lock file, but to prevent other writers from
    succeeding while we are reading the file.

    This type handles error correctly in that it will assure a consistent state
    on destruction.

    **note** with this setup, parallel reading is not possible"""
    __slots__ = ("_filepath", '_fd', '_write')

    def __init__(self, filepath):
        """Initialize an instance with the givne filepath"""
        self._filepath = filepath
        self._fd = None
        self._write = None          # if True, we write a file

    def __del__(self):
        # will do nothing if the file descriptor is already closed
        if self._fd is not None:
            self.rollback()

    def _lockfilepath(self):
        return "%s.lock" % self._filepath

    def open(self, write=False, stream=False):
        """
        Open the file descriptor for reading or writing, both in binary mode.

        :param write: if True, the file descriptor will be opened for writing. Other
            wise it will be opened read-only.
        :param stream: if True, the file descriptor will be wrapped into a simple stream
            object which supports only reading or writing
        :return: fd to read from or write to. It is still maintained by this instance
            and must not be closed directly
        :raise IOError: if the lock could not be retrieved
        :raise OSError: If the actual file could not be opened for reading

        **note** must only be called once"""
        if self._write is not None:
            raise AssertionError("Called %s multiple times" % self.open)

        self._write = write

        # try to open the lock file
        binary = getattr(os, 'O_BINARY', 0)
        lockmode = os.O_WRONLY | os.O_CREAT | os.O_EXCL | binary
        try:
            fd = os.open(self._lockfilepath(), lockmode, int("600", 8))
            if not write:
                os.close(fd)
            else:
                self._fd = fd
            # END handle file descriptor
        except OSError as e:
            raise OSError("Lock at %r could not be obtained" % self._lockfilepath()) from e
        # END handle lock retrieval

        # open actual file if required
        if self._fd is None:
            # we could specify exclusive here, as we obtained the lock anyway
            try:
                self._fd = os.open(self._filepath, os.O_RDONLY | binary)
            except:
                # assure we release our lockfile
                remove(self._lockfilepath())
                raise
            # END handle lockfile
        # END open descriptor for reading

        if stream:
            # need delayed import
            from gitdb.stream import FDStream
            return FDStream(self._fd)
        else:
            return self._fd
        # END handle stream

    def commit(self):
        """When done writing, call this function to commit your changes into the
        actual file.
        The file descriptor will be closed, and the lockfile handled.

        **Note** can be called multiple times"""
        self._end_writing(successful=True)

    def rollback(self):
        """Abort your operation without any changes. The file descriptor will be
        closed, and the lock released.

        **Note** can be called multiple times"""
        self._end_writing(successful=False)

    def _end_writing(self, successful=True):
        """Handle the lock according to the write mode """
        if self._write is None:
            raise AssertionError("Cannot end operation if it wasn't started yet")

        if self._fd is None:
            return

        os.close(self._fd)
        self._fd = None

        lockfile = self._lockfilepath()
        if self._write and successful:
            # on windows, rename does not silently overwrite the existing one
            if sys.platform == "win32":
                if isfile(self._filepath):
                    remove(self._filepath)
                # END remove if exists
            # END win32 special handling
            os.rename(lockfile, self._filepath)

            # assure others can at least read the file - the tmpfile left it at rw--
            # We may also write that file, on windows that boils down to a remove-
            # protection as well
            chmod(self._filepath, int("644", 8))
        else:
            # just delete the file so far, we failed
            remove(lockfile)
        # END successful handling

#} END utilities

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc5755.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# An Internet Attribute Certificate Profile for Authorization
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc5755.txt
# https://www.rfc-editor.org/rfc/rfc5912.txt (see Section 13)
#

from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import opentype
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

from pyasn1_modules import rfc5280
from pyasn1_modules import rfc5652

MAX = float('inf')

# Map for Security Category type to value

securityCategoryMap = { }


# Imports from RFC 5652

ContentInfo = rfc5652.ContentInfo


# Imports from RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier

Attribute = rfc5280.Attribute

AuthorityInfoAccessSyntax = rfc5280.AuthorityInfoAccessSyntax

AuthorityKeyIdentifier = rfc5280.AuthorityKeyIdentifier

CertificateSerialNumber = rfc5280.CertificateSerialNumber

CRLDistributionPoints = rfc5280.CRLDistributionPoints

Extensions = rfc5280.Extensions

Extension = rfc5280.Extension

GeneralNames = rfc5280.GeneralNames

GeneralName = rfc5280.GeneralName

UniqueIdentifier = rfc5280.UniqueIdentifier


# Object Identifier arcs

id_pkix = univ.ObjectIdentifier((1, 3, 6, 1, 5, 5, 7, ))

id_pe = id_pkix + (1, )

id_kp = id_pkix + (3, )

id_aca = id_pkix + (10, )

id_ad = id_pkix + (48, )

id_at = univ.ObjectIdentifier((2, 5, 4, ))

id_ce = univ.ObjectIdentifier((2, 5, 29, ))


# Attribute Certificate

class AttCertVersion(univ.Integer):
    namedValues = namedval.NamedValues(
        ('v2', 1)
    )


class IssuerSerial(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('issuer', GeneralNames()),
        namedtype.NamedType('serial', CertificateSerialNumber()),
        namedtype.OptionalNamedType('issuerUID', UniqueIdentifier())
    )


class ObjectDigestInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('digestedObjectType',
            univ.Enumerated(namedValues=namedval.NamedValues(
                ('publicKey', 0),
                ('publicKeyCert', 1),
                ('otherObjectTypes', 2)))),
        namedtype.OptionalNamedType('otherObjectTypeID',
            univ.ObjectIdentifier()),
        namedtype.NamedType('digestAlgorithm',
            AlgorithmIdentifier()),
        namedtype.NamedType('objectDigest',
            univ.BitString())
    )


class Holder(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('baseCertificateID',
            IssuerSerial().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.OptionalNamedType('entityName',
            GeneralNames().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('objectDigestInfo',
            ObjectDigestInfo().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 2)))
)


class V2Form(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('issuerName',
            GeneralNames()),
        namedtype.OptionalNamedType('baseCertificateID',
            IssuerSerial().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.OptionalNamedType('objectDigestInfo',
            ObjectDigestInfo().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 1)))
    )


class AttCertIssuer(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('v1Form', GeneralNames()),
        namedtype.NamedType('v2Form', V2Form().subtype(implicitTag=tag.Tag(
            tag.tagClassContext, tag.tagFormatConstructed, 0)))
    )


class AttCertValidityPeriod(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('notBeforeTime', useful.GeneralizedTime()),
        namedtype.NamedType('notAfterTime', useful.GeneralizedTime())
    )


class AttributeCertificateInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('version',
            AttCertVersion()),
        namedtype.NamedType('holder',
            Holder()),
        namedtype.NamedType('issuer',
            AttCertIssuer()),
        namedtype.NamedType('signature',
            AlgorithmIdentifier()),
        namedtype.NamedType('serialNumber',
            CertificateSerialNumber()),
        namedtype.NamedType('attrCertValidityPeriod',
            AttCertValidityPeriod()),
        namedtype.NamedType('attributes',
            univ.SequenceOf(componentType=Attribute())),
        namedtype.OptionalNamedType('issuerUniqueID',
            UniqueIdentifier()),
        namedtype.OptionalNamedType('extensions',
            Extensions())
    )


class AttributeCertificate(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('acinfo', AttributeCertificateInfo()),
        namedtype.NamedType('signatureAlgorithm', AlgorithmIdentifier()),
        namedtype.NamedType('signatureValue', univ.BitString())
    )


# Attribute Certificate Extensions

id_pe_ac_auditIdentity = id_pe + (4, )

id_ce_noRevAvail = id_ce + (56, )

id_ce_targetInformation = id_ce + (55, )


class TargetCert(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('targetCertificate', IssuerSerial()),
        namedtype.OptionalNamedType('targetName', GeneralName()),
        namedtype.OptionalNamedType('certDigestInfo', ObjectDigestInfo())
    )


class Target(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('targetName',
            GeneralName().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('targetGroup',
            GeneralName().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.NamedType('targetCert',
            TargetCert().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 2)))
    )


class Targets(univ.SequenceOf):
    componentType = Target()


id_pe_ac_proxying = id_pe + (10, )


class ProxyInfo(univ.SequenceOf):
    componentType = Targets()


id_pe_aaControls = id_pe + (6, )


class AttrSpec(univ.SequenceOf):
    componentType = univ.ObjectIdentifier()


class AAControls(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('pathLenConstraint',
            univ.Integer().subtype(
                subtypeSpec=constraint.ValueRangeConstraint(0, MAX))),
        namedtype.OptionalNamedType('permittedAttrs',
            AttrSpec().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('excludedAttrs',
            AttrSpec().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.DefaultedNamedType('permitUnSpecified',
            univ.Boolean().subtype(value=1))
    )


# Attribute Certificate Attributes

id_aca_authenticationInfo = id_aca + (1, )


id_aca_accessIdentity = id_aca + (2, )


class SvceAuthInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('service', GeneralName()),
        namedtype.NamedType('ident', GeneralName()),
        namedtype.OptionalNamedType('authInfo', univ.OctetString())
    )


id_aca_chargingIdentity = id_aca + (3, )


id_aca_group = id_aca + (4, )


class IetfAttrSyntax(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('policyAuthority',
            GeneralNames().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('values', univ.SequenceOf(
            componentType=univ.Choice(componentType=namedtype.NamedTypes(
                namedtype.NamedType('octets', univ.OctetString()),
                namedtype.NamedType('oid', univ.ObjectIdentifier()),
                namedtype.NamedType('string', char.UTF8String())
            ))
        ))
    )


id_at_role = id_at + (72,)


class RoleSyntax(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('roleAuthority',
            GeneralNames().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('roleName',
            GeneralName().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class ClassList(univ.BitString):
    namedValues = namedval.NamedValues(
        ('unmarked', 0),
        ('unclassified', 1),
        ('restricted', 2),
        ('confidential', 3),
        ('secret', 4),
        ('topSecret', 5)
    )


class SecurityCategory(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type',
            univ.ObjectIdentifier().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('value',
            univ.Any().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1)),
            openType=opentype.OpenType('type', securityCategoryMap))
    )


id_at_clearance = univ.ObjectIdentifier((2, 5, 4, 55, ))


class Clearance(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('policyId',
            univ.ObjectIdentifier()),
        namedtype.DefaultedNamedType('classList',
            ClassList().subtype(value='unclassified')),
        namedtype.OptionalNamedType('securityCategories',
            univ.SetOf(componentType=SecurityCategory()))
    )


id_at_clearance_rfc3281 = univ.ObjectIdentifier((2, 5, 1, 5, 55, ))


class Clearance_rfc3281(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('policyId',
            univ.ObjectIdentifier().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.DefaultedNamedType('classList',
            ClassList().subtype(implicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1)).subtype(
                    value='unclassified')),
        namedtype.OptionalNamedType('securityCategories',
            univ.SetOf(componentType=SecurityCategory()).subtype(
                implicitTag=tag.Tag(
                    tag.tagClassContext, tag.tagFormatSimple, 2)))
    )


id_aca_encAttrs = id_aca + (6, )


class ACClearAttrs(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('acIssuer', GeneralName()),
        namedtype.NamedType('acSerial', univ.Integer()),
        namedtype.NamedType('attrs', univ.SequenceOf(componentType=Attribute()))
    )


# Map of Certificate Extension OIDs to Extensions added to the
# ones that are in rfc5280.py

_certificateExtensionsMapUpdate = {
    id_pe_ac_auditIdentity: univ.OctetString(),
    id_ce_noRevAvail: univ.Null(),
    id_ce_targetInformation: Targets(),
    id_pe_ac_proxying: ProxyInfo(),
    id_pe_aaControls: AAControls(),
}

rfc5280.certificateExtensionsMap.update(_certificateExtensionsMapUpdate)


# Map of AttributeType OIDs to AttributeValue added to the
# ones that are in rfc5280.py

_certificateAttributesMapUpdate = {
    id_aca_authenticationInfo: SvceAuthInfo(),
    id_aca_accessIdentity: SvceAuthInfo(),
    id_aca_chargingIdentity: IetfAttrSyntax(),
    id_aca_group: IetfAttrSyntax(),
    id_at_role: RoleSyntax(),
    id_at_clearance: Clearance(),
    id_at_clearance_rfc3281: Clearance_rfc3281(),
    id_aca_encAttrs: ContentInfo(),
}

rfc5280.certificateAttributesMap.update(_certificateAttributesMapUpdate)

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\psLib.py ===
from fontTools.misc.textTools import bytechr, byteord, bytesjoin, tobytes, tostr
from fontTools.misc import eexec
from .psOperators import (
    PSOperators,
    ps_StandardEncoding,
    ps_array,
    ps_boolean,
    ps_dict,
    ps_integer,
    ps_literal,
    ps_mark,
    ps_name,
    ps_operator,
    ps_procedure,
    ps_procmark,
    ps_real,
    ps_string,
)
import re
from collections.abc import Callable
from string import whitespace
import logging


log = logging.getLogger(__name__)

ps_special = b"()<>[]{}%"  # / is one too, but we take care of that one differently

skipwhiteRE = re.compile(bytesjoin([b"[", whitespace, b"]*"]))
endofthingPat = bytesjoin([b"[^][(){}<>/%", whitespace, b"]*"])
endofthingRE = re.compile(endofthingPat)
commentRE = re.compile(b"%[^\n\r]*")

# XXX This not entirely correct as it doesn't allow *nested* embedded parens:
stringPat = rb"""
	\(
		(
			(
				[^()]*   \   [()]
			)
			|
			(
				[^()]*  \(   [^()]*  \)
			)
		)*
		[^()]*
	\)
"""
stringPat = b"".join(stringPat.split())
stringRE = re.compile(stringPat)

hexstringRE = re.compile(bytesjoin([b"<[", whitespace, b"0-9A-Fa-f]*>"]))


class PSTokenError(Exception):
    pass


class PSError(Exception):
    pass


class PSTokenizer(object):
    def __init__(self, buf=b"", encoding="ascii"):
        # Force self.buf to be a byte string
        buf = tobytes(buf)
        self.buf = buf
        self.len = len(buf)
        self.pos = 0
        self.closed = False
        self.encoding = encoding

    def read(self, n=-1):
        """Read at most 'n' bytes from the buffer, or less if the read
        hits EOF before obtaining 'n' bytes.
        If 'n' is negative or omitted, read all data until EOF is reached.
        """
        if self.closed:
            raise ValueError("I/O operation on closed file")
        if n is None or n < 0:
            newpos = self.len
        else:
            newpos = min(self.pos + n, self.len)
        r = self.buf[self.pos : newpos]
        self.pos = newpos
        return r

    def close(self):
        if not self.closed:
            self.closed = True
            del self.buf, self.pos

    def getnexttoken(
        self,
        # localize some stuff, for performance
        len=len,
        ps_special=ps_special,
        stringmatch=stringRE.match,
        hexstringmatch=hexstringRE.match,
        commentmatch=commentRE.match,
        endmatch=endofthingRE.match,
    ):
        self.skipwhite()
        if self.pos >= self.len:
            return None, None
        pos = self.pos
        buf = self.buf
        char = bytechr(byteord(buf[pos]))
        if char in ps_special:
            if char in b"{}[]":
                tokentype = "do_special"
                token = char
            elif char == b"%":
                tokentype = "do_comment"
                _, nextpos = commentmatch(buf, pos).span()
                token = buf[pos:nextpos]
            elif char == b"(":
                tokentype = "do_string"
                m = stringmatch(buf, pos)
                if m is None:
                    raise PSTokenError("bad string at character %d" % pos)
                _, nextpos = m.span()
                token = buf[pos:nextpos]
            elif char == b"<":
                tokentype = "do_hexstring"
                m = hexstringmatch(buf, pos)
                if m is None:
                    raise PSTokenError("bad hexstring at character %d" % pos)
                _, nextpos = m.span()
                token = buf[pos:nextpos]
            else:
                raise PSTokenError("bad token at character %d" % pos)
        else:
            if char == b"/":
                tokentype = "do_literal"
                m = endmatch(buf, pos + 1)
            else:
                tokentype = ""
                m = endmatch(buf, pos)
            if m is None:
                raise PSTokenError("bad token at character %d" % pos)
            _, nextpos = m.span()
            token = buf[pos:nextpos]
        self.pos = pos + len(token)
        token = tostr(token, encoding=self.encoding)
        return tokentype, token

    def skipwhite(self, whitematch=skipwhiteRE.match):
        _, nextpos = whitematch(self.buf, self.pos).span()
        self.pos = nextpos

    def starteexec(self):
        self.pos = self.pos + 1
        self.dirtybuf = self.buf[self.pos :]
        self.buf, R = eexec.decrypt(self.dirtybuf, 55665)
        self.len = len(self.buf)
        self.pos = 4

    def stopeexec(self):
        if not hasattr(self, "dirtybuf"):
            return
        self.buf = self.dirtybuf
        del self.dirtybuf


class PSInterpreter(PSOperators):
    def __init__(self, encoding="ascii"):
        systemdict = {}
        userdict = {}
        self.encoding = encoding
        self.dictstack = [systemdict, userdict]
        self.stack = []
        self.proclevel = 0
        self.procmark = ps_procmark()
        self.fillsystemdict()

    def fillsystemdict(self):
        systemdict = self.dictstack[0]
        systemdict["["] = systemdict["mark"] = self.mark = ps_mark()
        systemdict["]"] = ps_operator("]", self.do_makearray)
        systemdict["true"] = ps_boolean(1)
        systemdict["false"] = ps_boolean(0)
        systemdict["StandardEncoding"] = ps_array(ps_StandardEncoding)
        systemdict["FontDirectory"] = ps_dict({})
        self.suckoperators(systemdict, self.__class__)

    def suckoperators(self, systemdict, klass):
        for name in dir(klass):
            attr = getattr(self, name)
            if isinstance(attr, Callable) and name[:3] == "ps_":
                name = name[3:]
                systemdict[name] = ps_operator(name, attr)
        for baseclass in klass.__bases__:
            self.suckoperators(systemdict, baseclass)

    def interpret(self, data, getattr=getattr):
        tokenizer = self.tokenizer = PSTokenizer(data, self.encoding)
        getnexttoken = tokenizer.getnexttoken
        do_token = self.do_token
        handle_object = self.handle_object
        try:
            while 1:
                tokentype, token = getnexttoken()
                if not token:
                    break
                if tokentype:
                    handler = getattr(self, tokentype)
                    object = handler(token)
                else:
                    object = do_token(token)
                if object is not None:
                    handle_object(object)
            tokenizer.close()
            self.tokenizer = None
        except:
            if self.tokenizer is not None:
                log.debug(
                    "ps error:\n"
                    "- - - - - - -\n"
                    "%s\n"
                    ">>>\n"
                    "%s\n"
                    "- - - - - - -",
                    self.tokenizer.buf[self.tokenizer.pos - 50 : self.tokenizer.pos],
                    self.tokenizer.buf[self.tokenizer.pos : self.tokenizer.pos + 50],
                )
            raise

    def handle_object(self, object):
        if not (self.proclevel or object.literal or object.type == "proceduretype"):
            if object.type != "operatortype":
                object = self.resolve_name(object.value)
            if object.literal:
                self.push(object)
            else:
                if object.type == "proceduretype":
                    self.call_procedure(object)
                else:
                    object.function()
        else:
            self.push(object)

    def call_procedure(self, proc):
        handle_object = self.handle_object
        for item in proc.value:
            handle_object(item)

    def resolve_name(self, name):
        dictstack = self.dictstack
        for i in range(len(dictstack) - 1, -1, -1):
            if name in dictstack[i]:
                return dictstack[i][name]
        raise PSError("name error: " + str(name))

    def do_token(
        self,
        token,
        int=int,
        float=float,
        ps_name=ps_name,
        ps_integer=ps_integer,
        ps_real=ps_real,
    ):
        try:
            num = int(token)
        except (ValueError, OverflowError):
            try:
                num = float(token)
            except (ValueError, OverflowError):
                if "#" in token:
                    hashpos = token.find("#")
                    try:
                        base = int(token[:hashpos])
                        num = int(token[hashpos + 1 :], base)
                    except (ValueError, OverflowError):
                        return ps_name(token)
                    else:
                        return ps_integer(num)
                else:
                    return ps_name(token)
            else:
                return ps_real(num)
        else:
            return ps_integer(num)

    def do_comment(self, token):
        pass

    def do_literal(self, token):
        return ps_literal(token[1:])

    def do_string(self, token):
        return ps_string(token[1:-1])

    def do_hexstring(self, token):
        hexStr = "".join(token[1:-1].split())
        if len(hexStr) % 2:
            hexStr = hexStr + "0"
        cleanstr = []
        for i in range(0, len(hexStr), 2):
            cleanstr.append(chr(int(hexStr[i : i + 2], 16)))
        cleanstr = "".join(cleanstr)
        return ps_string(cleanstr)

    def do_special(self, token):
        if token == "{":
            self.proclevel = self.proclevel + 1
            return self.procmark
        elif token == "}":
            proc = []
            while 1:
                topobject = self.pop()
                if topobject == self.procmark:
                    break
                proc.append(topobject)
            self.proclevel = self.proclevel - 1
            proc.reverse()
            return ps_procedure(proc)
        elif token == "[":
            return self.mark
        elif token == "]":
            return ps_name("]")
        else:
            raise PSTokenError("huh?")

    def push(self, object):
        self.stack.append(object)

    def pop(self, *types):
        stack = self.stack
        if not stack:
            raise PSError("stack underflow")
        object = stack[-1]
        if types:
            if object.type not in types:
                raise PSError(
                    "typecheck, expected %s, found %s" % (repr(types), object.type)
                )
        del stack[-1]
        return object

    def do_makearray(self):
        array = []
        while 1:
            topobject = self.pop()
            if topobject == self.mark:
                break
            array.append(topobject)
        array.reverse()
        self.push(ps_array(array))

    def close(self):
        """Remove circular references."""
        del self.stack
        del self.dictstack


def unpack_item(item):
    tp = type(item.value)
    if tp == dict:
        newitem = {}
        for key, value in item.value.items():
            newitem[key] = unpack_item(value)
    elif tp == list:
        newitem = [None] * len(item.value)
        for i in range(len(item.value)):
            newitem[i] = unpack_item(item.value[i])
        if item.type == "proceduretype":
            newitem = tuple(newitem)
    else:
        newitem = item.value
    return newitem


def suckfont(data, encoding="ascii"):
    m = re.search(rb"/FontName\s+/([^ \t\n\r]+)\s+def", data)
    if m:
        fontName = m.group(1)
        fontName = fontName.decode()
    else:
        fontName = None
    interpreter = PSInterpreter(encoding=encoding)
    interpreter.interpret(
        b"/Helvetica 4 dict dup /Encoding StandardEncoding put definefont pop"
    )
    interpreter.interpret(data)
    fontdir = interpreter.dictstack[0]["FontDirectory"].value
    if fontName in fontdir:
        rawfont = fontdir[fontName]
    else:
        # fall back, in case fontName wasn't found
        fontNames = list(fontdir.keys())
        if len(fontNames) > 1:
            fontNames.remove("Helvetica")
        fontNames.sort()
        rawfont = fontdir[fontNames[0]]
    interpreter.close()
    return unpack_item(rawfont)

# === NexusCore/openenv\Lib\site-packages\fontTools\ufoLib\converters.py ===
"""
Functions for converting UFO1 or UFO2 files into UFO3 format.

Currently provides functionality for converting kerning rules
and kerning groups. Conversion is only supported _from_ UFO1
or UFO2, and _to_ UFO3.
"""

# adapted from the UFO spec


def convertUFO1OrUFO2KerningToUFO3Kerning(kerning, groups, glyphSet=()):
    """Convert kerning data in UFO1 or UFO2 syntax into UFO3 syntax.

    Args:
      kerning:
          A dictionary containing the kerning rules defined in
          the UFO font, as used in :class:`.UFOReader` objects.
      groups:
          A dictionary containing the groups defined in the UFO
          font, as used in :class:`.UFOReader` objects.
      glyphSet:
        Optional; a set of glyph objects to skip (default: None).

    Returns:
      1. A dictionary representing the converted kerning data.
      2. A copy of the groups dictionary, with all groups renamed to UFO3 syntax.
      3. A dictionary containing the mapping of old group names to new group names.

    """
    # gather known kerning groups based on the prefixes
    firstReferencedGroups, secondReferencedGroups = findKnownKerningGroups(groups)
    # Make lists of groups referenced in kerning pairs.
    for first, seconds in list(kerning.items()):
        if first in groups and first not in glyphSet:
            if not first.startswith("public.kern1."):
                firstReferencedGroups.add(first)
        for second in list(seconds.keys()):
            if second in groups and second not in glyphSet:
                if not second.startswith("public.kern2."):
                    secondReferencedGroups.add(second)
    # Create new names for these groups.
    firstRenamedGroups = {}
    for first in firstReferencedGroups:
        # Make a list of existing group names.
        existingGroupNames = list(groups.keys()) + list(firstRenamedGroups.keys())
        # Remove the old prefix from the name
        newName = first.replace("@MMK_L_", "")
        # Add the new prefix to the name.
        newName = "public.kern1." + newName
        # Make a unique group name.
        newName = makeUniqueGroupName(newName, existingGroupNames)
        # Store for use later.
        firstRenamedGroups[first] = newName
    secondRenamedGroups = {}
    for second in secondReferencedGroups:
        # Make a list of existing group names.
        existingGroupNames = list(groups.keys()) + list(secondRenamedGroups.keys())
        # Remove the old prefix from the name
        newName = second.replace("@MMK_R_", "")
        # Add the new prefix to the name.
        newName = "public.kern2." + newName
        # Make a unique group name.
        newName = makeUniqueGroupName(newName, existingGroupNames)
        # Store for use later.
        secondRenamedGroups[second] = newName
    # Populate the new group names into the kerning dictionary as needed.
    newKerning = {}
    for first, seconds in list(kerning.items()):
        first = firstRenamedGroups.get(first, first)
        newSeconds = {}
        for second, value in list(seconds.items()):
            second = secondRenamedGroups.get(second, second)
            newSeconds[second] = value
        newKerning[first] = newSeconds
    # Make copies of the referenced groups and store them
    # under the new names in the overall groups dictionary.
    allRenamedGroups = list(firstRenamedGroups.items())
    allRenamedGroups += list(secondRenamedGroups.items())
    for oldName, newName in allRenamedGroups:
        group = list(groups[oldName])
        groups[newName] = group
    # Return the kerning and the groups.
    return newKerning, groups, dict(side1=firstRenamedGroups, side2=secondRenamedGroups)


def findKnownKerningGroups(groups):
    """Find all kerning groups in a UFO1 or UFO2 font that use known prefixes.

    In some cases, not all kerning groups will be referenced
    by the kerning pairs in a UFO. The algorithm for locating
    groups in :func:`convertUFO1OrUFO2KerningToUFO3Kerning` will
    miss these unreferenced groups. By scanning for known prefixes,
    this function will catch all of the prefixed groups.

    The prefixes and sides by this function are:

    @MMK_L_ - side 1
    @MMK_R_ - side 2

    as defined in the UFO1 specification.

    Args:
        groups:
          A dictionary containing the groups defined in the UFO
          font, as read by :class:`.UFOReader`.

    Returns:
        Two sets; the first containing the names of all
        first-side kerning groups identified in the ``groups``
        dictionary, and the second containing the names of all
        second-side kerning groups identified.

        "First-side" and "second-side" are with respect to the
        writing direction of the script.

        Example::

          >>> testGroups = {
          ...     "@MMK_L_1" : None,
          ...     "@MMK_L_2" : None,
          ...     "@MMK_L_3" : None,
          ...     "@MMK_R_1" : None,
          ...     "@MMK_R_2" : None,
          ...     "@MMK_R_3" : None,
          ...     "@MMK_l_1" : None,
          ...     "@MMK_r_1" : None,
          ...     "@MMK_X_1" : None,
          ...     "foo" : None,
          ... }
          >>> first, second = findKnownKerningGroups(testGroups)
          >>> sorted(first) == ['@MMK_L_1', '@MMK_L_2', '@MMK_L_3']
          True
          >>> sorted(second) == ['@MMK_R_1', '@MMK_R_2', '@MMK_R_3']
          True
    """
    knownFirstGroupPrefixes = ["@MMK_L_"]
    knownSecondGroupPrefixes = ["@MMK_R_"]
    firstGroups = set()
    secondGroups = set()
    for groupName in list(groups.keys()):
        for firstPrefix in knownFirstGroupPrefixes:
            if groupName.startswith(firstPrefix):
                firstGroups.add(groupName)
                break
        for secondPrefix in knownSecondGroupPrefixes:
            if groupName.startswith(secondPrefix):
                secondGroups.add(groupName)
                break
    return firstGroups, secondGroups


def makeUniqueGroupName(name, groupNames, counter=0):
    """Make a kerning group name that will be unique within the set of group names.

    If the requested kerning group name already exists within the set, this
    will return a new name by adding an incremented counter to the end
    of the requested name.

    Args:
        name:
          The requested kerning group name.
        groupNames:
          A list of the existing kerning group names.
        counter:
          Optional; a counter of group names already seen (default: 0). If
          :attr:`.counter` is not provided, the function will recurse,
          incrementing the value of :attr:`.counter` until it finds the
          first unused ``name+counter`` combination, and return that result.

    Returns:
        A unique kerning group name composed of the requested name suffixed
        by the smallest available integer counter.
    """
    # Add a number to the name if the counter is higher than zero.
    newName = name
    if counter > 0:
        newName = "%s%d" % (newName, counter)
    # If the new name is in the existing group names, recurse.
    if newName in groupNames:
        return makeUniqueGroupName(name, groupNames, counter + 1)
    # Otherwise send back the new name.
    return newName


def test():
    """
    Tests for :func:`.convertUFO1OrUFO2KerningToUFO3Kerning`.

    No known prefixes.

    >>> testKerning = {
    ...     "A" : {
    ...         "A" : 1,
    ...         "B" : 2,
    ...         "CGroup" : 3,
    ...         "DGroup" : 4
    ...     },
    ...     "BGroup" : {
    ...         "A" : 5,
    ...         "B" : 6,
    ...         "CGroup" : 7,
    ...         "DGroup" : 8
    ...     },
    ...     "CGroup" : {
    ...         "A" : 9,
    ...         "B" : 10,
    ...         "CGroup" : 11,
    ...         "DGroup" : 12
    ...     },
    ... }
    >>> testGroups = {
    ...     "BGroup" : ["B"],
    ...     "CGroup" : ["C"],
    ...     "DGroup" : ["D"],
    ... }
    >>> kerning, groups, maps = convertUFO1OrUFO2KerningToUFO3Kerning(
    ...     testKerning, testGroups, [])
    >>> expected = {
    ...     "A" : {
    ...         "A": 1,
    ...         "B": 2,
    ...         "public.kern2.CGroup": 3,
    ...         "public.kern2.DGroup": 4
    ...     },
    ...     "public.kern1.BGroup": {
    ...         "A": 5,
    ...         "B": 6,
    ...         "public.kern2.CGroup": 7,
    ...         "public.kern2.DGroup": 8
    ...     },
    ...     "public.kern1.CGroup": {
    ...         "A": 9,
    ...         "B": 10,
    ...         "public.kern2.CGroup": 11,
    ...         "public.kern2.DGroup": 12
    ...     }
    ... }
    >>> kerning == expected
    True
    >>> expected = {
    ...     "BGroup": ["B"],
    ...     "CGroup": ["C"],
    ...     "DGroup": ["D"],
    ...     "public.kern1.BGroup": ["B"],
    ...     "public.kern1.CGroup": ["C"],
    ...     "public.kern2.CGroup": ["C"],
    ...     "public.kern2.DGroup": ["D"],
    ... }
    >>> groups == expected
    True

    Known prefixes.

    >>> testKerning = {
    ...     "A" : {
    ...         "A" : 1,
    ...         "B" : 2,
    ...         "@MMK_R_CGroup" : 3,
    ...         "@MMK_R_DGroup" : 4
    ...     },
    ...     "@MMK_L_BGroup" : {
    ...         "A" : 5,
    ...         "B" : 6,
    ...         "@MMK_R_CGroup" : 7,
    ...         "@MMK_R_DGroup" : 8
    ...     },
    ...     "@MMK_L_CGroup" : {
    ...         "A" : 9,
    ...         "B" : 10,
    ...         "@MMK_R_CGroup" : 11,
    ...         "@MMK_R_DGroup" : 12
    ...     },
    ... }
    >>> testGroups = {
    ...     "@MMK_L_BGroup" : ["B"],
    ...     "@MMK_L_CGroup" : ["C"],
    ...     "@MMK_L_XGroup" : ["X"],
    ...     "@MMK_R_CGroup" : ["C"],
    ...     "@MMK_R_DGroup" : ["D"],
    ...     "@MMK_R_XGroup" : ["X"],
    ... }
    >>> kerning, groups, maps = convertUFO1OrUFO2KerningToUFO3Kerning(
    ...     testKerning, testGroups, [])
    >>> expected = {
    ...     "A" : {
    ...         "A": 1,
    ...         "B": 2,
    ...         "public.kern2.CGroup": 3,
    ...         "public.kern2.DGroup": 4
    ...     },
    ...     "public.kern1.BGroup": {
    ...         "A": 5,
    ...         "B": 6,
    ...         "public.kern2.CGroup": 7,
    ...         "public.kern2.DGroup": 8
    ...     },
    ...     "public.kern1.CGroup": {
    ...         "A": 9,
    ...         "B": 10,
    ...         "public.kern2.CGroup": 11,
    ...         "public.kern2.DGroup": 12
    ...     }
    ... }
    >>> kerning == expected
    True
    >>> expected = {
    ...     "@MMK_L_BGroup": ["B"],
    ...     "@MMK_L_CGroup": ["C"],
    ...     "@MMK_L_XGroup": ["X"],
    ...     "@MMK_R_CGroup": ["C"],
    ...     "@MMK_R_DGroup": ["D"],
    ...     "@MMK_R_XGroup": ["X"],
    ...     "public.kern1.BGroup": ["B"],
    ...     "public.kern1.CGroup": ["C"],
    ...     "public.kern1.XGroup": ["X"],
    ...     "public.kern2.CGroup": ["C"],
    ...     "public.kern2.DGroup": ["D"],
    ...     "public.kern2.XGroup": ["X"],
    ... }
    >>> groups == expected
    True

    >>> from .validators import kerningValidator
    >>> kerningValidator(kerning)
    (True, None)

    Mixture of known prefixes and groups without prefixes.

    >>> testKerning = {
    ...     "A" : {
    ...         "A" : 1,
    ...         "B" : 2,
    ...         "@MMK_R_CGroup" : 3,
    ...         "DGroup" : 4
    ...     },
    ...     "BGroup" : {
    ...         "A" : 5,
    ...         "B" : 6,
    ...         "@MMK_R_CGroup" : 7,
    ...         "DGroup" : 8
    ...     },
    ...     "@MMK_L_CGroup" : {
    ...         "A" : 9,
    ...         "B" : 10,
    ...         "@MMK_R_CGroup" : 11,
    ...         "DGroup" : 12
    ...     },
    ... }
    >>> testGroups = {
    ...     "BGroup" : ["B"],
    ...     "@MMK_L_CGroup" : ["C"],
    ...     "@MMK_R_CGroup" : ["C"],
    ...     "DGroup" : ["D"],
    ... }
    >>> kerning, groups, maps = convertUFO1OrUFO2KerningToUFO3Kerning(
    ...     testKerning, testGroups, [])
    >>> expected = {
    ...     "A" : {
    ...         "A": 1,
    ...         "B": 2,
    ...         "public.kern2.CGroup": 3,
    ...         "public.kern2.DGroup": 4
    ...     },
    ...     "public.kern1.BGroup": {
    ...         "A": 5,
    ...         "B": 6,
    ...         "public.kern2.CGroup": 7,
    ...         "public.kern2.DGroup": 8
    ...     },
    ...     "public.kern1.CGroup": {
    ...         "A": 9,
    ...         "B": 10,
    ...         "public.kern2.CGroup": 11,
    ...         "public.kern2.DGroup": 12
    ...     }
    ... }
    >>> kerning == expected
    True
    >>> expected = {
    ...     "BGroup": ["B"],
    ...     "@MMK_L_CGroup": ["C"],
    ...     "@MMK_R_CGroup": ["C"],
    ...     "DGroup": ["D"],
    ...     "public.kern1.BGroup": ["B"],
    ...     "public.kern1.CGroup": ["C"],
    ...     "public.kern2.CGroup": ["C"],
    ...     "public.kern2.DGroup": ["D"],
    ... }
    >>> groups == expected
    True
    """


if __name__ == "__main__":
    import doctest

    doctest.testmod()

# === NexusCore/openenv\Lib\site-packages\google\auth\transport\_aiohttp_requests.py ===
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

"""Transport adapter for Async HTTP (aiohttp).

NOTE: This async support is experimental and marked internal. This surface may
change in minor releases.
"""

from __future__ import absolute_import

import asyncio
import functools
import logging

import aiohttp  # type: ignore
import urllib3  # type: ignore

from google.auth import _helpers
from google.auth import exceptions
from google.auth import transport
from google.auth.aio import _helpers as _helpers_async
from google.auth.transport import requests


_LOGGER = logging.getLogger(__name__)

# Timeout can be re-defined depending on async requirement. Currently made 60s more than
# sync timeout.
_DEFAULT_TIMEOUT = 180  # in seconds


class _CombinedResponse(transport.Response):
    """
    In order to more closely resemble the `requests` interface, where a raw
    and deflated content could be accessed at once, this class lazily reads the
    stream in `transport.Response` so both return forms can be used.

    The gzip and deflate transfer-encodings are automatically decoded for you
    because the default parameter for autodecompress into the ClientSession is set
    to False, and therefore we add this class to act as a wrapper for a user to be
    able to access both the raw and decoded response bodies - mirroring the sync
    implementation.
    """

    def __init__(self, response):
        self._response = response
        self._raw_content = None

    def _is_compressed(self):
        headers = self._response.headers
        return "Content-Encoding" in headers and (
            headers["Content-Encoding"] == "gzip"
            or headers["Content-Encoding"] == "deflate"
        )

    @property
    def status(self):
        return self._response.status

    @property
    def headers(self):
        return self._response.headers

    @property
    def data(self):
        return self._response.content

    async def raw_content(self):
        if self._raw_content is None:
            self._raw_content = await self._response.content.read()
        return self._raw_content

    async def content(self):
        # Load raw_content if necessary
        await self.raw_content()
        if self._is_compressed():
            decoder = urllib3.response.MultiDecoder(
                self._response.headers["Content-Encoding"]
            )
            decompressed = decoder.decompress(self._raw_content)
            return decompressed

        return self._raw_content


class _Response(transport.Response):
    """
    Requests transport response adapter.

    Args:
        response (requests.Response): The raw Requests response.
    """

    def __init__(self, response):
        self._response = response

    @property
    def status(self):
        return self._response.status

    @property
    def headers(self):
        return self._response.headers

    @property
    def data(self):
        return self._response.content


class Request(transport.Request):
    """Requests request adapter.

    This class is used internally for making requests using asyncio transports
    in a consistent way. If you use :class:`AuthorizedSession` you do not need
    to construct or use this class directly.

    This class can be useful if you want to manually refresh a
    :class:`~google.auth.credentials.Credentials` instance::

        import google.auth.transport.aiohttp_requests

        request = google.auth.transport.aiohttp_requests.Request()

        credentials.refresh(request)

    Args:
        session (aiohttp.ClientSession): An instance :class:`aiohttp.ClientSession` used
            to make HTTP requests. If not specified, a session will be created.

    .. automethod:: __call__
    """

    def __init__(self, session=None):
        # TODO: Use auto_decompress property for aiohttp 3.7+
        if session is not None and session._auto_decompress:
            raise exceptions.InvalidOperation(
                "Client sessions with auto_decompress=True are not supported."
            )
        self.session = session

    async def __call__(
        self,
        url,
        method="GET",
        body=None,
        headers=None,
        timeout=_DEFAULT_TIMEOUT,
        **kwargs,
    ):
        """
        Make an HTTP request using aiohttp.

        Args:
            url (str): The URL to be requested.
            method (Optional[str]):
                The HTTP method to use for the request. Defaults to 'GET'.
            body (Optional[bytes]):
                The payload or body in HTTP request.
            headers (Optional[Mapping[str, str]]):
                Request headers.
            timeout (Optional[int]): The number of seconds to wait for a
                response from the server. If not specified or if None, the
                requests default timeout will be used.
            kwargs: Additional arguments passed through to the underlying
                requests :meth:`requests.Session.request` method.

        Returns:
            google.auth.transport.Response: The HTTP response.

        Raises:
            google.auth.exceptions.TransportError: If any exception occurred.
        """

        try:
            if self.session is None:  # pragma: NO COVER
                self.session = aiohttp.ClientSession(
                    auto_decompress=False
                )  # pragma: NO COVER
            _helpers.request_log(_LOGGER, method, url, body, headers)
            response = await self.session.request(
                method, url, data=body, headers=headers, timeout=timeout, **kwargs
            )
            await _helpers_async.response_log_async(_LOGGER, response)
            return _CombinedResponse(response)

        except aiohttp.ClientError as caught_exc:
            new_exc = exceptions.TransportError(caught_exc)
            raise new_exc from caught_exc

        except asyncio.TimeoutError as caught_exc:
            new_exc = exceptions.TransportError(caught_exc)
            raise new_exc from caught_exc


class AuthorizedSession(aiohttp.ClientSession):
    """This is an async implementation of the Authorized Session class. We utilize an
    aiohttp transport instance, and the interface mirrors the google.auth.transport.requests
    Authorized Session class, except for the change in the transport used in the async use case.

    A Requests Session class with credentials.

    This class is used to perform requests to API endpoints that require
    authorization::

        from google.auth.transport import aiohttp_requests

        async with aiohttp_requests.AuthorizedSession(credentials) as authed_session:
            response = await authed_session.request(
                'GET', 'https://www.googleapis.com/storage/v1/b')

    The underlying :meth:`request` implementation handles adding the
    credentials' headers to the request and refreshing credentials as needed.

    Args:
        credentials (google.auth._credentials_async.Credentials):
            The credentials to add to the request.
        refresh_status_codes (Sequence[int]): Which HTTP status codes indicate
            that credentials should be refreshed and the request should be
            retried.
        max_refresh_attempts (int): The maximum number of times to attempt to
            refresh the credentials and retry the request.
        refresh_timeout (Optional[int]): The timeout value in seconds for
            credential refresh HTTP requests.
        auth_request (google.auth.transport.aiohttp_requests.Request):
            (Optional) An instance of
            :class:`~google.auth.transport.aiohttp_requests.Request` used when
            refreshing credentials. If not passed,
            an instance of :class:`~google.auth.transport.aiohttp_requests.Request`
            is created.
        kwargs: Additional arguments passed through to the underlying
            ClientSession :meth:`aiohttp.ClientSession` object.
    """

    def __init__(
        self,
        credentials,
        refresh_status_codes=transport.DEFAULT_REFRESH_STATUS_CODES,
        max_refresh_attempts=transport.DEFAULT_MAX_REFRESH_ATTEMPTS,
        refresh_timeout=None,
        auth_request=None,
        auto_decompress=False,
        **kwargs,
    ):
        super(AuthorizedSession, self).__init__(**kwargs)
        self.credentials = credentials
        self._refresh_status_codes = refresh_status_codes
        self._max_refresh_attempts = max_refresh_attempts
        self._refresh_timeout = refresh_timeout
        self._is_mtls = False
        self._auth_request = auth_request
        self._auth_request_session = None
        self._loop = asyncio.get_event_loop()
        self._refresh_lock = asyncio.Lock()
        self._auto_decompress = auto_decompress

    async def request(
        self,
        method,
        url,
        data=None,
        headers=None,
        max_allowed_time=None,
        timeout=_DEFAULT_TIMEOUT,
        auto_decompress=False,
        **kwargs,
    ):

        """Implementation of Authorized Session aiohttp request.

        Args:
            method (str):
                The http request method used (e.g. GET, PUT, DELETE)
            url (str):
                The url at which the http request is sent.
            data (Optional[dict]): Dictionary, list of tuples, bytes, or file-like
                object to send in the body of the Request.
            headers (Optional[dict]): Dictionary of HTTP Headers to send with the
                Request.
            timeout (Optional[Union[float, aiohttp.ClientTimeout]]):
                The amount of time in seconds to wait for the server response
                with each individual request. Can also be passed as an
                ``aiohttp.ClientTimeout`` object.
            max_allowed_time (Optional[float]):
                If the method runs longer than this, a ``Timeout`` exception is
                automatically raised. Unlike the ``timeout`` parameter, this
                value applies to the total method execution time, even if
                multiple requests are made under the hood.

                Mind that it is not guaranteed that the timeout error is raised
                at ``max_allowed_time``. It might take longer, for example, if
                an underlying request takes a lot of time, but the request
                itself does not timeout, e.g. if a large file is being
                transmitted. The timout error will be raised after such
                request completes.
        """
        # Headers come in as bytes which isn't expected behavior, the resumable
        # media libraries in some cases expect a str type for the header values,
        # but sometimes the operations return these in bytes types.
        if headers:
            for key in headers.keys():
                if type(headers[key]) is bytes:
                    headers[key] = headers[key].decode("utf-8")

        async with aiohttp.ClientSession(
            auto_decompress=self._auto_decompress,
            trust_env=kwargs.get("trust_env", False),
        ) as self._auth_request_session:
            auth_request = Request(self._auth_request_session)
            self._auth_request = auth_request

            # Use a kwarg for this instead of an attribute to maintain
            # thread-safety.
            _credential_refresh_attempt = kwargs.pop("_credential_refresh_attempt", 0)
            # Make a copy of the headers. They will be modified by the credentials
            # and we want to pass the original headers if we recurse.
            request_headers = headers.copy() if headers is not None else {}

            # Do not apply the timeout unconditionally in order to not override the
            # _auth_request's default timeout.
            auth_request = (
                self._auth_request
                if timeout is None
                else functools.partial(self._auth_request, timeout=timeout)
            )

            remaining_time = max_allowed_time

            with requests.TimeoutGuard(remaining_time, asyncio.TimeoutError) as guard:
                await self.credentials.before_request(
                    auth_request, method, url, request_headers
                )

            with requests.TimeoutGuard(remaining_time, asyncio.TimeoutError) as guard:
                response = await super(AuthorizedSession, self).request(
                    method,
                    url,
                    data=data,
                    headers=request_headers,
                    timeout=timeout,
                    **kwargs,
                )

            remaining_time = guard.remaining_timeout

            if (
                response.status in self._refresh_status_codes
                and _credential_refresh_attempt < self._max_refresh_attempts
            ):

                requests._LOGGER.info(
                    "Refreshing credentials due to a %s response. Attempt %s/%s.",
                    response.status,
                    _credential_refresh_attempt + 1,
                    self._max_refresh_attempts,
                )

                # Do not apply the timeout unconditionally in order to not override the
                # _auth_request's default timeout.
                auth_request = (
                    self._auth_request
                    if timeout is None
                    else functools.partial(self._auth_request, timeout=timeout)
                )

                with requests.TimeoutGuard(
                    remaining_time, asyncio.TimeoutError
                ) as guard:
                    async with self._refresh_lock:
                        await self._loop.run_in_executor(
                            None, self.credentials.refresh, auth_request
                        )

                remaining_time = guard.remaining_timeout

                return await self.request(
                    method,
                    url,
                    data=data,
                    headers=headers,
                    max_allowed_time=remaining_time,
                    timeout=timeout,
                    _credential_refresh_attempt=_credential_refresh_attempt + 1,
                    **kwargs,
                )

        return response

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\mte.py ===
"""
A reader for corpora whose documents are in MTE format.
"""

import os
import re
from functools import reduce

from nltk.corpus.reader import TaggedCorpusReader, concat
from nltk.corpus.reader.xmldocs import XMLCorpusView


def xpath(root, path, ns):
    return root.findall(path, ns)


class MTECorpusView(XMLCorpusView):
    """
    Class for lazy viewing the MTE Corpus.
    """

    def __init__(self, fileid, tagspec, elt_handler=None):
        XMLCorpusView.__init__(self, fileid, tagspec, elt_handler)

    def read_block(self, stream, tagspec=None, elt_handler=None):
        return list(
            filter(
                lambda x: x is not None,
                XMLCorpusView.read_block(self, stream, tagspec, elt_handler),
            )
        )


class MTEFileReader:
    """
    Class for loading the content of the multext-east corpus. It
    parses the xml files and does some tag-filtering depending on the
    given method parameters.
    """

    ns = {
        "tei": "https://www.tei-c.org/ns/1.0",
        "xml": "https://www.w3.org/XML/1998/namespace",
    }
    tag_ns = "{https://www.tei-c.org/ns/1.0}"
    xml_ns = "{https://www.w3.org/XML/1998/namespace}"
    word_path = "TEI/text/body/div/div/p/s/(w|c)"
    sent_path = "TEI/text/body/div/div/p/s"
    para_path = "TEI/text/body/div/div/p"

    def __init__(self, file_path):
        self.__file_path = file_path

    @classmethod
    def _word_elt(cls, elt, context):
        return elt.text

    @classmethod
    def _sent_elt(cls, elt, context):
        return [cls._word_elt(w, None) for w in xpath(elt, "*", cls.ns)]

    @classmethod
    def _para_elt(cls, elt, context):
        return [cls._sent_elt(s, None) for s in xpath(elt, "*", cls.ns)]

    @classmethod
    def _tagged_word_elt(cls, elt, context):
        if "ana" not in elt.attrib:
            return (elt.text, "")

        if cls.__tags == "" and cls.__tagset == "msd":
            return (elt.text, elt.attrib["ana"])
        elif cls.__tags == "" and cls.__tagset == "universal":
            return (elt.text, MTETagConverter.msd_to_universal(elt.attrib["ana"]))
        else:
            tags = re.compile("^" + re.sub("-", ".", cls.__tags) + ".*$")
            if tags.match(elt.attrib["ana"]):
                if cls.__tagset == "msd":
                    return (elt.text, elt.attrib["ana"])
                else:
                    return (
                        elt.text,
                        MTETagConverter.msd_to_universal(elt.attrib["ana"]),
                    )
            else:
                return None

    @classmethod
    def _tagged_sent_elt(cls, elt, context):
        return list(
            filter(
                lambda x: x is not None,
                [cls._tagged_word_elt(w, None) for w in xpath(elt, "*", cls.ns)],
            )
        )

    @classmethod
    def _tagged_para_elt(cls, elt, context):
        return list(
            filter(
                lambda x: x is not None,
                [cls._tagged_sent_elt(s, None) for s in xpath(elt, "*", cls.ns)],
            )
        )

    @classmethod
    def _lemma_word_elt(cls, elt, context):
        if "lemma" not in elt.attrib:
            return (elt.text, "")
        else:
            return (elt.text, elt.attrib["lemma"])

    @classmethod
    def _lemma_sent_elt(cls, elt, context):
        return [cls._lemma_word_elt(w, None) for w in xpath(elt, "*", cls.ns)]

    @classmethod
    def _lemma_para_elt(cls, elt, context):
        return [cls._lemma_sent_elt(s, None) for s in xpath(elt, "*", cls.ns)]

    def words(self):
        return MTECorpusView(
            self.__file_path, MTEFileReader.word_path, MTEFileReader._word_elt
        )

    def sents(self):
        return MTECorpusView(
            self.__file_path, MTEFileReader.sent_path, MTEFileReader._sent_elt
        )

    def paras(self):
        return MTECorpusView(
            self.__file_path, MTEFileReader.para_path, MTEFileReader._para_elt
        )

    def lemma_words(self):
        return MTECorpusView(
            self.__file_path, MTEFileReader.word_path, MTEFileReader._lemma_word_elt
        )

    def tagged_words(self, tagset, tags):
        MTEFileReader.__tagset = tagset
        MTEFileReader.__tags = tags
        return MTECorpusView(
            self.__file_path, MTEFileReader.word_path, MTEFileReader._tagged_word_elt
        )

    def lemma_sents(self):
        return MTECorpusView(
            self.__file_path, MTEFileReader.sent_path, MTEFileReader._lemma_sent_elt
        )

    def tagged_sents(self, tagset, tags):
        MTEFileReader.__tagset = tagset
        MTEFileReader.__tags = tags
        return MTECorpusView(
            self.__file_path, MTEFileReader.sent_path, MTEFileReader._tagged_sent_elt
        )

    def lemma_paras(self):
        return MTECorpusView(
            self.__file_path, MTEFileReader.para_path, MTEFileReader._lemma_para_elt
        )

    def tagged_paras(self, tagset, tags):
        MTEFileReader.__tagset = tagset
        MTEFileReader.__tags = tags
        return MTECorpusView(
            self.__file_path, MTEFileReader.para_path, MTEFileReader._tagged_para_elt
        )


class MTETagConverter:
    """
    Class for converting msd tags to universal tags, more conversion
    options are currently not implemented.
    """

    mapping_msd_universal = {
        "A": "ADJ",
        "S": "ADP",
        "R": "ADV",
        "C": "CONJ",
        "D": "DET",
        "N": "NOUN",
        "M": "NUM",
        "Q": "PRT",
        "P": "PRON",
        "V": "VERB",
        ".": ".",
        "-": "X",
    }

    @staticmethod
    def msd_to_universal(tag):
        """
        This function converts the annotation from the Multex-East to the universal tagset
        as described in Chapter 5 of the NLTK-Book

        Unknown Tags will be mapped to X. Punctuation marks are not supported in MSD tags, so
        """
        indicator = tag[0] if not tag[0] == "#" else tag[1]

        if not indicator in MTETagConverter.mapping_msd_universal:
            indicator = "-"

        return MTETagConverter.mapping_msd_universal[indicator]


class MTECorpusReader(TaggedCorpusReader):
    """
    Reader for corpora following the TEI-p5 xml scheme, such as MULTEXT-East.
    MULTEXT-East contains part-of-speech-tagged words with a quite precise tagging
    scheme. These tags can be converted to the Universal tagset
    """

    def __init__(self, root=None, fileids=None, encoding="utf8"):
        """
        Construct a new MTECorpusreader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/...path to corpus.../'
            >>> reader = MTECorpusReader(root, 'oana-*.xml', 'utf8') # doctest: +SKIP

        :param root: The root directory for this corpus. (default points to location in multext config file)
        :param fileids: A list or regexp specifying the fileids in this corpus. (default is oana-en.xml)
        :param encoding: The encoding of the given files (default is utf8)
        """
        TaggedCorpusReader.__init__(self, root, fileids, encoding)
        self._readme = "00README.txt"

    def __fileids(self, fileids):
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, str):
            fileids = [fileids]
        # filter wrong userinput
        fileids = filter(lambda x: x in self._fileids, fileids)
        # filter multext-east sourcefiles that are not compatible to the teip5 specification
        fileids = filter(lambda x: x not in ["oana-bg.xml", "oana-mk.xml"], fileids)
        if not fileids:
            print("No valid multext-east file specified")
        return fileids

    def words(self, fileids=None):
        """
        :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a list of words and punctuation symbols.
        :rtype: list(str)
        """
        return concat(
            [
                MTEFileReader(os.path.join(self._root, f)).words()
                for f in self.__fileids(fileids)
            ]
        )

    def sents(self, fileids=None):
        """
        :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a list of sentences or utterances,
                 each encoded as a list of word strings
        :rtype: list(list(str))
        """
        return concat(
            [
                MTEFileReader(os.path.join(self._root, f)).sents()
                for f in self.__fileids(fileids)
            ]
        )

    def paras(self, fileids=None):
        """
        :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a list of paragraphs, each encoded as a list
                 of sentences, which are in turn encoded as lists of word string
        :rtype: list(list(list(str)))
        """
        return concat(
            [
                MTEFileReader(os.path.join(self._root, f)).paras()
                for f in self.__fileids(fileids)
            ]
        )

    def lemma_words(self, fileids=None):
        """
        :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a list of words, the corresponding lemmas
                 and punctuation symbols, encoded as tuples (word, lemma)
        :rtype: list(tuple(str,str))
        """
        return concat(
            [
                MTEFileReader(os.path.join(self._root, f)).lemma_words()
                for f in self.__fileids(fileids)
            ]
        )

    def tagged_words(self, fileids=None, tagset="msd", tags=""):
        """
        :param fileids: A list specifying the fileids that should be used.
        :param tagset: The tagset that should be used in the returned object,
                       either "universal" or "msd", "msd" is the default
        :param tags: An MSD Tag that is used to filter all parts of the used corpus
                     that are not more precise or at least equal to the given tag
        :return: the given file(s) as a list of tagged words and punctuation symbols
                 encoded as tuples (word, tag)
        :rtype: list(tuple(str, str))
        """
        if tagset == "universal" or tagset == "msd":
            return concat(
                [
                    MTEFileReader(os.path.join(self._root, f)).tagged_words(
                        tagset, tags
                    )
                    for f in self.__fileids(fileids)
                ]
            )
        else:
            print("Unknown tagset specified.")

    def lemma_sents(self, fileids=None):
        """
        :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a list of sentences or utterances, each
                 encoded as a list of tuples of the word and the corresponding
                 lemma (word, lemma)
        :rtype: list(list(tuple(str, str)))
        """
        return concat(
            [
                MTEFileReader(os.path.join(self._root, f)).lemma_sents()
                for f in self.__fileids(fileids)
            ]
        )

    def tagged_sents(self, fileids=None, tagset="msd", tags=""):
        """
        :param fileids: A list specifying the fileids that should be used.
        :param tagset: The tagset that should be used in the returned object,
                       either "universal" or "msd", "msd" is the default
        :param tags: An MSD Tag that is used to filter all parts of the used corpus
                     that are not more precise or at least equal to the given tag
        :return: the given file(s) as a list of sentences or utterances, each
                 each encoded as a list of (word,tag) tuples
        :rtype: list(list(tuple(str, str)))
        """
        if tagset == "universal" or tagset == "msd":
            return concat(
                [
                    MTEFileReader(os.path.join(self._root, f)).tagged_sents(
                        tagset, tags
                    )
                    for f in self.__fileids(fileids)
                ]
            )
        else:
            print("Unknown tagset specified.")

    def lemma_paras(self, fileids=None):
        """
        :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a list of paragraphs, each encoded as a
                 list of sentences, which are in turn encoded as a list of
                 tuples of the word and the corresponding lemma (word, lemma)
        :rtype: list(List(List(tuple(str, str))))
        """
        return concat(
            [
                MTEFileReader(os.path.join(self._root, f)).lemma_paras()
                for f in self.__fileids(fileids)
            ]
        )

    def tagged_paras(self, fileids=None, tagset="msd", tags=""):
        """
        :param fileids: A list specifying the fileids that should be used.
        :param tagset: The tagset that should be used in the returned object,
                       either "universal" or "msd", "msd" is the default
        :param tags: An MSD Tag that is used to filter all parts of the used corpus
                     that are not more precise or at least equal to the given tag
        :return: the given file(s) as a list of paragraphs, each encoded as a
                 list of sentences, which are in turn encoded as a list
                 of (word,tag) tuples
        :rtype: list(list(list(tuple(str, str))))
        """
        if tagset == "universal" or tagset == "msd":
            return concat(
                [
                    MTEFileReader(os.path.join(self._root, f)).tagged_paras(
                        tagset, tags
                    )
                    for f in self.__fileids(fileids)
                ]
            )
        else:
            print("Unknown tagset specified.")

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\low_level.py ===
"""
Low-level helpers for the SecureTransport bindings.

These are Python functions that are not directly related to the high-level APIs
but are necessary to get them to work. They include a whole bunch of low-level
CoreFoundation messing about and memory management. The concerns in this module
are almost entirely about trying to avoid memory leaks and providing
appropriate and useful assistance to the higher-level code.
"""
import base64
import ctypes
import itertools
import os
import re
import ssl
import struct
import tempfile

from .bindings import CFConst, CoreFoundation, Security

# This regular expression is used to grab PEM data out of a PEM bundle.
_PEM_CERTS_RE = re.compile(
    b"-----BEGIN CERTIFICATE-----\n(.*?)\n-----END CERTIFICATE-----", re.DOTALL
)


def _cf_data_from_bytes(bytestring):
    """
    Given a bytestring, create a CFData object from it. This CFData object must
    be CFReleased by the caller.
    """
    return CoreFoundation.CFDataCreate(
        CoreFoundation.kCFAllocatorDefault, bytestring, len(bytestring)
    )


def _cf_dictionary_from_tuples(tuples):
    """
    Given a list of Python tuples, create an associated CFDictionary.
    """
    dictionary_size = len(tuples)

    # We need to get the dictionary keys and values out in the same order.
    keys = (t[0] for t in tuples)
    values = (t[1] for t in tuples)
    cf_keys = (CoreFoundation.CFTypeRef * dictionary_size)(*keys)
    cf_values = (CoreFoundation.CFTypeRef * dictionary_size)(*values)

    return CoreFoundation.CFDictionaryCreate(
        CoreFoundation.kCFAllocatorDefault,
        cf_keys,
        cf_values,
        dictionary_size,
        CoreFoundation.kCFTypeDictionaryKeyCallBacks,
        CoreFoundation.kCFTypeDictionaryValueCallBacks,
    )


def _cfstr(py_bstr):
    """
    Given a Python binary data, create a CFString.
    The string must be CFReleased by the caller.
    """
    c_str = ctypes.c_char_p(py_bstr)
    cf_str = CoreFoundation.CFStringCreateWithCString(
        CoreFoundation.kCFAllocatorDefault,
        c_str,
        CFConst.kCFStringEncodingUTF8,
    )
    return cf_str


def _create_cfstring_array(lst):
    """
    Given a list of Python binary data, create an associated CFMutableArray.
    The array must be CFReleased by the caller.

    Raises an ssl.SSLError on failure.
    """
    cf_arr = None
    try:
        cf_arr = CoreFoundation.CFArrayCreateMutable(
            CoreFoundation.kCFAllocatorDefault,
            0,
            ctypes.byref(CoreFoundation.kCFTypeArrayCallBacks),
        )
        if not cf_arr:
            raise MemoryError("Unable to allocate memory!")
        for item in lst:
            cf_str = _cfstr(item)
            if not cf_str:
                raise MemoryError("Unable to allocate memory!")
            try:
                CoreFoundation.CFArrayAppendValue(cf_arr, cf_str)
            finally:
                CoreFoundation.CFRelease(cf_str)
    except BaseException as e:
        if cf_arr:
            CoreFoundation.CFRelease(cf_arr)
        raise ssl.SSLError("Unable to allocate array: %s" % (e,))
    return cf_arr


def _cf_string_to_unicode(value):
    """
    Creates a Unicode string from a CFString object. Used entirely for error
    reporting.

    Yes, it annoys me quite a lot that this function is this complex.
    """
    value_as_void_p = ctypes.cast(value, ctypes.POINTER(ctypes.c_void_p))

    string = CoreFoundation.CFStringGetCStringPtr(
        value_as_void_p, CFConst.kCFStringEncodingUTF8
    )
    if string is None:
        buffer = ctypes.create_string_buffer(1024)
        result = CoreFoundation.CFStringGetCString(
            value_as_void_p, buffer, 1024, CFConst.kCFStringEncodingUTF8
        )
        if not result:
            raise OSError("Error copying C string from CFStringRef")
        string = buffer.value
    if string is not None:
        string = string.decode("utf-8")
    return string


def _assert_no_error(error, exception_class=None):
    """
    Checks the return code and throws an exception if there is an error to
    report
    """
    if error == 0:
        return

    cf_error_string = Security.SecCopyErrorMessageString(error, None)
    output = _cf_string_to_unicode(cf_error_string)
    CoreFoundation.CFRelease(cf_error_string)

    if output is None or output == u"":
        output = u"OSStatus %s" % error

    if exception_class is None:
        exception_class = ssl.SSLError

    raise exception_class(output)


def _cert_array_from_pem(pem_bundle):
    """
    Given a bundle of certs in PEM format, turns them into a CFArray of certs
    that can be used to validate a cert chain.
    """
    # Normalize the PEM bundle's line endings.
    pem_bundle = pem_bundle.replace(b"\r\n", b"\n")

    der_certs = [
        base64.b64decode(match.group(1)) for match in _PEM_CERTS_RE.finditer(pem_bundle)
    ]
    if not der_certs:
        raise ssl.SSLError("No root certificates specified")

    cert_array = CoreFoundation.CFArrayCreateMutable(
        CoreFoundation.kCFAllocatorDefault,
        0,
        ctypes.byref(CoreFoundation.kCFTypeArrayCallBacks),
    )
    if not cert_array:
        raise ssl.SSLError("Unable to allocate memory!")

    try:
        for der_bytes in der_certs:
            certdata = _cf_data_from_bytes(der_bytes)
            if not certdata:
                raise ssl.SSLError("Unable to allocate memory!")
            cert = Security.SecCertificateCreateWithData(
                CoreFoundation.kCFAllocatorDefault, certdata
            )
            CoreFoundation.CFRelease(certdata)
            if not cert:
                raise ssl.SSLError("Unable to build cert object!")

            CoreFoundation.CFArrayAppendValue(cert_array, cert)
            CoreFoundation.CFRelease(cert)
    except Exception:
        # We need to free the array before the exception bubbles further.
        # We only want to do that if an error occurs: otherwise, the caller
        # should free.
        CoreFoundation.CFRelease(cert_array)
        raise

    return cert_array


def _is_cert(item):
    """
    Returns True if a given CFTypeRef is a certificate.
    """
    expected = Security.SecCertificateGetTypeID()
    return CoreFoundation.CFGetTypeID(item) == expected


def _is_identity(item):
    """
    Returns True if a given CFTypeRef is an identity.
    """
    expected = Security.SecIdentityGetTypeID()
    return CoreFoundation.CFGetTypeID(item) == expected


def _temporary_keychain():
    """
    This function creates a temporary Mac keychain that we can use to work with
    credentials. This keychain uses a one-time password and a temporary file to
    store the data. We expect to have one keychain per socket. The returned
    SecKeychainRef must be freed by the caller, including calling
    SecKeychainDelete.

    Returns a tuple of the SecKeychainRef and the path to the temporary
    directory that contains it.
    """
    # Unfortunately, SecKeychainCreate requires a path to a keychain. This
    # means we cannot use mkstemp to use a generic temporary file. Instead,
    # we're going to create a temporary directory and a filename to use there.
    # This filename will be 8 random bytes expanded into base64. We also need
    # some random bytes to password-protect the keychain we're creating, so we
    # ask for 40 random bytes.
    random_bytes = os.urandom(40)
    filename = base64.b16encode(random_bytes[:8]).decode("utf-8")
    password = base64.b16encode(random_bytes[8:])  # Must be valid UTF-8
    tempdirectory = tempfile.mkdtemp()

    keychain_path = os.path.join(tempdirectory, filename).encode("utf-8")

    # We now want to create the keychain itself.
    keychain = Security.SecKeychainRef()
    status = Security.SecKeychainCreate(
        keychain_path, len(password), password, False, None, ctypes.byref(keychain)
    )
    _assert_no_error(status)

    # Having created the keychain, we want to pass it off to the caller.
    return keychain, tempdirectory


def _load_items_from_file(keychain, path):
    """
    Given a single file, loads all the trust objects from it into arrays and
    the keychain.
    Returns a tuple of lists: the first list is a list of identities, the
    second a list of certs.
    """
    certificates = []
    identities = []
    result_array = None

    with open(path, "rb") as f:
        raw_filedata = f.read()

    try:
        filedata = CoreFoundation.CFDataCreate(
            CoreFoundation.kCFAllocatorDefault, raw_filedata, len(raw_filedata)
        )
        result_array = CoreFoundation.CFArrayRef()
        result = Security.SecItemImport(
            filedata,  # cert data
            None,  # Filename, leaving it out for now
            None,  # What the type of the file is, we don't care
            None,  # what's in the file, we don't care
            0,  # import flags
            None,  # key params, can include passphrase in the future
            keychain,  # The keychain to insert into
            ctypes.byref(result_array),  # Results
        )
        _assert_no_error(result)

        # A CFArray is not very useful to us as an intermediary
        # representation, so we are going to extract the objects we want
        # and then free the array. We don't need to keep hold of keys: the
        # keychain already has them!
        result_count = CoreFoundation.CFArrayGetCount(result_array)
        for index in range(result_count):
            item = CoreFoundation.CFArrayGetValueAtIndex(result_array, index)
            item = ctypes.cast(item, CoreFoundation.CFTypeRef)

            if _is_cert(item):
                CoreFoundation.CFRetain(item)
                certificates.append(item)
            elif _is_identity(item):
                CoreFoundation.CFRetain(item)
                identities.append(item)
    finally:
        if result_array:
            CoreFoundation.CFRelease(result_array)

        CoreFoundation.CFRelease(filedata)

    return (identities, certificates)


def _load_client_cert_chain(keychain, *paths):
    """
    Load certificates and maybe keys from a number of files. Has the end goal
    of returning a CFArray containing one SecIdentityRef, and then zero or more
    SecCertificateRef objects, suitable for use as a client certificate trust
    chain.
    """
    # Ok, the strategy.
    #
    # This relies on knowing that macOS will not give you a SecIdentityRef
    # unless you have imported a key into a keychain. This is a somewhat
    # artificial limitation of macOS (for example, it doesn't necessarily
    # affect iOS), but there is nothing inside Security.framework that lets you
    # get a SecIdentityRef without having a key in a keychain.
    #
    # So the policy here is we take all the files and iterate them in order.
    # Each one will use SecItemImport to have one or more objects loaded from
    # it. We will also point at a keychain that macOS can use to work with the
    # private key.
    #
    # Once we have all the objects, we'll check what we actually have. If we
    # already have a SecIdentityRef in hand, fab: we'll use that. Otherwise,
    # we'll take the first certificate (which we assume to be our leaf) and
    # ask the keychain to give us a SecIdentityRef with that cert's associated
    # key.
    #
    # We'll then return a CFArray containing the trust chain: one
    # SecIdentityRef and then zero-or-more SecCertificateRef objects. The
    # responsibility for freeing this CFArray will be with the caller. This
    # CFArray must remain alive for the entire connection, so in practice it
    # will be stored with a single SSLSocket, along with the reference to the
    # keychain.
    certificates = []
    identities = []

    # Filter out bad paths.
    paths = (path for path in paths if path)

    try:
        for file_path in paths:
            new_identities, new_certs = _load_items_from_file(keychain, file_path)
            identities.extend(new_identities)
            certificates.extend(new_certs)

        # Ok, we have everything. The question is: do we have an identity? If
        # not, we want to grab one from the first cert we have.
        if not identities:
            new_identity = Security.SecIdentityRef()
            status = Security.SecIdentityCreateWithCertificate(
                keychain, certificates[0], ctypes.byref(new_identity)
            )
            _assert_no_error(status)
            identities.append(new_identity)

            # We now want to release the original certificate, as we no longer
            # need it.
            CoreFoundation.CFRelease(certificates.pop(0))

        # We now need to build a new CFArray that holds the trust chain.
        trust_chain = CoreFoundation.CFArrayCreateMutable(
            CoreFoundation.kCFAllocatorDefault,
            0,
            ctypes.byref(CoreFoundation.kCFTypeArrayCallBacks),
        )
        for item in itertools.chain(identities, certificates):
            # ArrayAppendValue does a CFRetain on the item. That's fine,
            # because the finally block will release our other refs to them.
            CoreFoundation.CFArrayAppendValue(trust_chain, item)

        return trust_chain
    finally:
        for obj in itertools.chain(identities, certificates):
            CoreFoundation.CFRelease(obj)


TLS_PROTOCOL_VERSIONS = {
    "SSLv2": (0, 2),
    "SSLv3": (3, 0),
    "TLSv1": (3, 1),
    "TLSv1.1": (3, 2),
    "TLSv1.2": (3, 3),
}


def _build_tls_unknown_ca_alert(version):
    """
    Builds a TLS alert record for an unknown CA.
    """
    ver_maj, ver_min = TLS_PROTOCOL_VERSIONS[version]
    severity_fatal = 0x02
    description_unknown_ca = 0x30
    msg = struct.pack(">BB", severity_fatal, description_unknown_ca)
    msg_len = len(msg)
    record_type_alert = 0x15
    record = struct.pack(">BBBH", record_type_alert, ver_maj, ver_min, msg_len) + msg
    return record

# === NexusCore/openenv\Lib\site-packages\matplotlib\textpath.py ===
from collections import OrderedDict
import logging
import urllib.parse

import numpy as np

from matplotlib import _text_helpers, dviread
from matplotlib.font_manager import (
    FontProperties, get_font, fontManager as _fontManager
)
from matplotlib.ft2font import LoadFlags
from matplotlib.mathtext import MathTextParser
from matplotlib.path import Path
from matplotlib.texmanager import TexManager
from matplotlib.transforms import Affine2D

_log = logging.getLogger(__name__)


class TextToPath:
    """A class that converts strings to paths."""

    FONT_SCALE = 100.
    DPI = 72

    def __init__(self):
        self.mathtext_parser = MathTextParser('path')
        self._texmanager = None

    def _get_font(self, prop):
        """
        Find the `FT2Font` matching font properties *prop*, with its size set.
        """
        filenames = _fontManager._find_fonts_by_props(prop)
        font = get_font(filenames)
        font.set_size(self.FONT_SCALE, self.DPI)
        return font

    def _get_hinting_flag(self):
        return LoadFlags.NO_HINTING

    def _get_char_id(self, font, ccode):
        """
        Return a unique id for the given font and character-code set.
        """
        return urllib.parse.quote(f"{font.postscript_name}-{ccode:x}")

    def get_text_width_height_descent(self, s, prop, ismath):
        fontsize = prop.get_size_in_points()

        if ismath == "TeX":
            return TexManager().get_text_width_height_descent(s, fontsize)

        scale = fontsize / self.FONT_SCALE

        if ismath:
            prop = prop.copy()
            prop.set_size(self.FONT_SCALE)
            width, height, descent, *_ = \
                self.mathtext_parser.parse(s, 72, prop)
            return width * scale, height * scale, descent * scale

        font = self._get_font(prop)
        font.set_text(s, 0.0, flags=LoadFlags.NO_HINTING)
        w, h = font.get_width_height()
        w /= 64.0  # convert from subpixels
        h /= 64.0
        d = font.get_descent()
        d /= 64.0
        return w * scale, h * scale, d * scale

    def get_text_path(self, prop, s, ismath=False):
        """
        Convert text *s* to path (a tuple of vertices and codes for
        matplotlib.path.Path).

        Parameters
        ----------
        prop : `~matplotlib.font_manager.FontProperties`
            The font properties for the text.
        s : str
            The text to be converted.
        ismath : {False, True, "TeX"}
            If True, use mathtext parser.  If "TeX", use tex for rendering.

        Returns
        -------
        verts : list
            A list of arrays containing the (x, y) coordinates of the vertices.
        codes : list
            A list of path codes.

        Examples
        --------
        Create a list of vertices and codes from a text, and create a `.Path`
        from those::

            from matplotlib.path import Path
            from matplotlib.text import TextToPath
            from matplotlib.font_manager import FontProperties

            fp = FontProperties(family="Comic Neue", style="italic")
            verts, codes = TextToPath().get_text_path(fp, "ABC")
            path = Path(verts, codes, closed=False)

        Also see `TextPath` for a more direct way to create a path from a text.
        """
        if ismath == "TeX":
            glyph_info, glyph_map, rects = self.get_glyphs_tex(prop, s)
        elif not ismath:
            font = self._get_font(prop)
            glyph_info, glyph_map, rects = self.get_glyphs_with_font(font, s)
        else:
            glyph_info, glyph_map, rects = self.get_glyphs_mathtext(prop, s)

        verts, codes = [], []
        for glyph_id, xposition, yposition, scale in glyph_info:
            verts1, codes1 = glyph_map[glyph_id]
            verts.extend(verts1 * scale + [xposition, yposition])
            codes.extend(codes1)
        for verts1, codes1 in rects:
            verts.extend(verts1)
            codes.extend(codes1)

        # Make sure an empty string or one with nothing to print
        # (e.g. only spaces & newlines) will be valid/empty path
        if not verts:
            verts = np.empty((0, 2))

        return verts, codes

    def get_glyphs_with_font(self, font, s, glyph_map=None,
                             return_new_glyphs_only=False):
        """
        Convert string *s* to vertices and codes using the provided ttf font.
        """

        if glyph_map is None:
            glyph_map = OrderedDict()

        if return_new_glyphs_only:
            glyph_map_new = OrderedDict()
        else:
            glyph_map_new = glyph_map

        xpositions = []
        glyph_ids = []
        for item in _text_helpers.layout(s, font):
            char_id = self._get_char_id(item.ft_object, ord(item.char))
            glyph_ids.append(char_id)
            xpositions.append(item.x)
            if char_id not in glyph_map:
                glyph_map_new[char_id] = item.ft_object.get_path()

        ypositions = [0] * len(xpositions)
        sizes = [1.] * len(xpositions)

        rects = []

        return (list(zip(glyph_ids, xpositions, ypositions, sizes)),
                glyph_map_new, rects)

    def get_glyphs_mathtext(self, prop, s, glyph_map=None,
                            return_new_glyphs_only=False):
        """
        Parse mathtext string *s* and convert it to a (vertices, codes) pair.
        """

        prop = prop.copy()
        prop.set_size(self.FONT_SCALE)

        width, height, descent, glyphs, rects = self.mathtext_parser.parse(
            s, self.DPI, prop)

        if not glyph_map:
            glyph_map = OrderedDict()

        if return_new_glyphs_only:
            glyph_map_new = OrderedDict()
        else:
            glyph_map_new = glyph_map

        xpositions = []
        ypositions = []
        glyph_ids = []
        sizes = []

        for font, fontsize, ccode, ox, oy in glyphs:
            char_id = self._get_char_id(font, ccode)
            if char_id not in glyph_map:
                font.clear()
                font.set_size(self.FONT_SCALE, self.DPI)
                font.load_char(ccode, flags=LoadFlags.NO_HINTING)
                glyph_map_new[char_id] = font.get_path()

            xpositions.append(ox)
            ypositions.append(oy)
            glyph_ids.append(char_id)
            size = fontsize / self.FONT_SCALE
            sizes.append(size)

        myrects = []
        for ox, oy, w, h in rects:
            vert1 = [(ox, oy), (ox, oy + h), (ox + w, oy + h),
                     (ox + w, oy), (ox, oy), (0, 0)]
            code1 = [Path.MOVETO,
                     Path.LINETO, Path.LINETO, Path.LINETO, Path.LINETO,
                     Path.CLOSEPOLY]
            myrects.append((vert1, code1))

        return (list(zip(glyph_ids, xpositions, ypositions, sizes)),
                glyph_map_new, myrects)

    def get_glyphs_tex(self, prop, s, glyph_map=None,
                       return_new_glyphs_only=False):
        """Convert the string *s* to vertices and codes using usetex mode."""
        # Mostly borrowed from pdf backend.

        dvifile = TexManager().make_dvi(s, self.FONT_SCALE)
        with dviread.Dvi(dvifile, self.DPI) as dvi:
            page, = dvi

        if glyph_map is None:
            glyph_map = OrderedDict()

        if return_new_glyphs_only:
            glyph_map_new = OrderedDict()
        else:
            glyph_map_new = glyph_map

        glyph_ids, xpositions, ypositions, sizes = [], [], [], []

        # Gather font information and do some setup for combining
        # characters into strings.
        for text in page.text:
            font = get_font(text.font_path)
            char_id = self._get_char_id(font, text.glyph)
            if char_id not in glyph_map:
                font.clear()
                font.set_size(self.FONT_SCALE, self.DPI)
                glyph_name_or_index = text.glyph_name_or_index
                if isinstance(glyph_name_or_index, str):
                    index = font.get_name_index(glyph_name_or_index)
                    font.load_glyph(index, flags=LoadFlags.TARGET_LIGHT)
                elif isinstance(glyph_name_or_index, int):
                    self._select_native_charmap(font)
                    font.load_char(
                        glyph_name_or_index, flags=LoadFlags.TARGET_LIGHT)
                else:  # Should not occur.
                    raise TypeError(f"Glyph spec of unexpected type: "
                                    f"{glyph_name_or_index!r}")
                glyph_map_new[char_id] = font.get_path()

            glyph_ids.append(char_id)
            xpositions.append(text.x)
            ypositions.append(text.y)
            sizes.append(text.font_size / self.FONT_SCALE)

        myrects = []

        for ox, oy, h, w in page.boxes:
            vert1 = [(ox, oy), (ox + w, oy), (ox + w, oy + h),
                     (ox, oy + h), (ox, oy), (0, 0)]
            code1 = [Path.MOVETO,
                     Path.LINETO, Path.LINETO, Path.LINETO, Path.LINETO,
                     Path.CLOSEPOLY]
            myrects.append((vert1, code1))

        return (list(zip(glyph_ids, xpositions, ypositions, sizes)),
                glyph_map_new, myrects)

    @staticmethod
    def _select_native_charmap(font):
        # Select the native charmap. (we can't directly identify it but it's
        # typically an Adobe charmap).
        for charmap_code in [
                1094992451,  # ADOBE_CUSTOM.
                1094995778,  # ADOBE_STANDARD.
        ]:
            try:
                font.select_charmap(charmap_code)
            except (ValueError, RuntimeError):
                pass
            else:
                break
        else:
            _log.warning("No supported encoding in font (%s).", font.fname)


text_to_path = TextToPath()


class TextPath(Path):
    """
    Create a path from the text.
    """

    def __init__(self, xy, s, size=None, prop=None,
                 _interpolation_steps=1, usetex=False):
        r"""
        Create a path from the text. Note that it simply is a path,
        not an artist. You need to use the `.PathPatch` (or other artists)
        to draw this path onto the canvas.

        Parameters
        ----------
        xy : tuple or array of two float values
            Position of the text. For no offset, use ``xy=(0, 0)``.

        s : str
            The text to convert to a path.

        size : float, optional
            Font size in points. Defaults to the size specified via the font
            properties *prop*.

        prop : `~matplotlib.font_manager.FontProperties`, optional
            Font property. If not provided, will use a default
            `.FontProperties` with parameters from the
            :ref:`rcParams<customizing-with-dynamic-rc-settings>`.

        _interpolation_steps : int, optional
            (Currently ignored)

        usetex : bool, default: False
            Whether to use tex rendering.

        Examples
        --------
        The following creates a path from the string "ABC" with Helvetica
        font face; and another path from the latex fraction 1/2::

            from matplotlib.text import TextPath
            from matplotlib.font_manager import FontProperties

            fp = FontProperties(family="Helvetica", style="italic")
            path1 = TextPath((12, 12), "ABC", size=12, prop=fp)
            path2 = TextPath((0, 0), r"$\frac{1}{2}$", size=12, usetex=True)

        Also see :doc:`/gallery/text_labels_and_annotations/demo_text_path`.
        """
        # Circular import.
        from matplotlib.text import Text

        prop = FontProperties._from_any(prop)
        if size is None:
            size = prop.get_size_in_points()

        self._xy = xy
        self.set_size(size)

        self._cached_vertices = None
        s, ismath = Text(usetex=usetex)._preprocess_math(s)
        super().__init__(
            *text_to_path.get_text_path(prop, s, ismath=ismath),
            _interpolation_steps=_interpolation_steps,
            readonly=True)
        self._should_simplify = False

    def set_size(self, size):
        """Set the text size."""
        self._size = size
        self._invalid = True

    def get_size(self):
        """Get the text size."""
        return self._size

    @property
    def vertices(self):
        """
        Return the cached path after updating it if necessary.
        """
        self._revalidate_path()
        return self._cached_vertices

    @property
    def codes(self):
        """
        Return the codes
        """
        return self._codes

    def _revalidate_path(self):
        """
        Update the path if necessary.

        The path for the text is initially create with the font size of
        `.FONT_SCALE`, and this path is rescaled to other size when necessary.
        """
        if self._invalid or self._cached_vertices is None:
            tr = (Affine2D()
                  .scale(self._size / text_to_path.FONT_SCALE)
                  .translate(*self._xy))
            self._cached_vertices = tr.transform(self._vertices)
            self._cached_vertices.flags.writeable = False
            self._invalid = False

# === NexusCore/openenv\Lib\site-packages\anthropic\_utils\_utils.py ===
from __future__ import annotations

import os
import re
import inspect
import functools
from typing import (
    Any,
    Tuple,
    Mapping,
    TypeVar,
    Callable,
    Iterable,
    Sequence,
    cast,
    overload,
)
from pathlib import Path
from typing_extensions import TypeGuard

import sniffio

from .._types import NotGiven, FileTypes, NotGivenOr, HeadersLike
from .._compat import parse_date as parse_date, parse_datetime as parse_datetime

_T = TypeVar("_T")
_TupleT = TypeVar("_TupleT", bound=Tuple[object, ...])
_MappingT = TypeVar("_MappingT", bound=Mapping[str, object])
_SequenceT = TypeVar("_SequenceT", bound=Sequence[object])
CallableT = TypeVar("CallableT", bound=Callable[..., Any])


def flatten(t: Iterable[Iterable[_T]]) -> list[_T]:
    return [item for sublist in t for item in sublist]


def extract_files(
    # TODO: this needs to take Dict but variance issues.....
    # create protocol type ?
    query: Mapping[str, object],
    *,
    paths: Sequence[Sequence[str]],
) -> list[tuple[str, FileTypes]]:
    """Recursively extract files from the given dictionary based on specified paths.

    A path may look like this ['foo', 'files', '<array>', 'data'].

    Note: this mutates the given dictionary.
    """
    files: list[tuple[str, FileTypes]] = []
    for path in paths:
        files.extend(_extract_items(query, path, index=0, flattened_key=None))
    return files


def _extract_items(
    obj: object,
    path: Sequence[str],
    *,
    index: int,
    flattened_key: str | None,
) -> list[tuple[str, FileTypes]]:
    try:
        key = path[index]
    except IndexError:
        if isinstance(obj, NotGiven):
            # no value was provided - we can safely ignore
            return []

        # cyclical import
        from .._files import assert_is_file_content

        # We have exhausted the path, return the entry we found.
        assert_is_file_content(obj, key=flattened_key)
        assert flattened_key is not None
        return [(flattened_key, cast(FileTypes, obj))]

    index += 1
    if is_dict(obj):
        try:
            # We are at the last entry in the path so we must remove the field
            if (len(path)) == index:
                item = obj.pop(key)
            else:
                item = obj[key]
        except KeyError:
            # Key was not present in the dictionary, this is not indicative of an error
            # as the given path may not point to a required field. We also do not want
            # to enforce required fields as the API may differ from the spec in some cases.
            return []
        if flattened_key is None:
            flattened_key = key
        else:
            flattened_key += f"[{key}]"
        return _extract_items(
            item,
            path,
            index=index,
            flattened_key=flattened_key,
        )
    elif is_list(obj):
        if key != "<array>":
            return []

        return flatten(
            [
                _extract_items(
                    item,
                    path,
                    index=index,
                    flattened_key=flattened_key + "[]" if flattened_key is not None else "[]",
                )
                for item in obj
            ]
        )

    # Something unexpected was passed, just ignore it.
    return []


def is_given(obj: NotGivenOr[_T]) -> TypeGuard[_T]:
    return not isinstance(obj, NotGiven)


# Type safe methods for narrowing types with TypeVars.
# The default narrowing for isinstance(obj, dict) is dict[unknown, unknown],
# however this cause Pyright to rightfully report errors. As we know we don't
# care about the contained types we can safely use `object` in it's place.
#
# There are two separate functions defined, `is_*` and `is_*_t` for different use cases.
# `is_*` is for when you're dealing with an unknown input
# `is_*_t` is for when you're narrowing a known union type to a specific subset


def is_tuple(obj: object) -> TypeGuard[tuple[object, ...]]:
    return isinstance(obj, tuple)


def is_tuple_t(obj: _TupleT | object) -> TypeGuard[_TupleT]:
    return isinstance(obj, tuple)


def is_sequence(obj: object) -> TypeGuard[Sequence[object]]:
    return isinstance(obj, Sequence)


def is_sequence_t(obj: _SequenceT | object) -> TypeGuard[_SequenceT]:
    return isinstance(obj, Sequence)


def is_mapping(obj: object) -> TypeGuard[Mapping[str, object]]:
    return isinstance(obj, Mapping)


def is_mapping_t(obj: _MappingT | object) -> TypeGuard[_MappingT]:
    return isinstance(obj, Mapping)


def is_dict(obj: object) -> TypeGuard[dict[object, object]]:
    return isinstance(obj, dict)


def is_list(obj: object) -> TypeGuard[list[object]]:
    return isinstance(obj, list)


def is_iterable(obj: object) -> TypeGuard[Iterable[object]]:
    return isinstance(obj, Iterable)


def deepcopy_minimal(item: _T) -> _T:
    """Minimal reimplementation of copy.deepcopy() that will only copy certain object types:

    - mappings, e.g. `dict`
    - list

    This is done for performance reasons.
    """
    if is_mapping(item):
        return cast(_T, {k: deepcopy_minimal(v) for k, v in item.items()})
    if is_list(item):
        return cast(_T, [deepcopy_minimal(entry) for entry in item])
    return item


# copied from https://github.com/Rapptz/RoboDanny
def human_join(seq: Sequence[str], *, delim: str = ", ", final: str = "or") -> str:
    size = len(seq)
    if size == 0:
        return ""

    if size == 1:
        return seq[0]

    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"

    return delim.join(seq[:-1]) + f" {final} {seq[-1]}"


def quote(string: str) -> str:
    """Add single quotation marks around the given string. Does *not* do any escaping."""
    return f"'{string}'"


def required_args(*variants: Sequence[str]) -> Callable[[CallableT], CallableT]:
    """Decorator to enforce a given set of arguments or variants of arguments are passed to the decorated function.

    Useful for enforcing runtime validation of overloaded functions.

    Example usage:
    ```py
    @overload
    def foo(*, a: str) -> str: ...


    @overload
    def foo(*, b: bool) -> str: ...


    # This enforces the same constraints that a static type checker would
    # i.e. that either a or b must be passed to the function
    @required_args(["a"], ["b"])
    def foo(*, a: str | None = None, b: bool | None = None) -> str: ...
    ```
    """

    def inner(func: CallableT) -> CallableT:
        params = inspect.signature(func).parameters
        positional = [
            name
            for name, param in params.items()
            if param.kind
            in {
                param.POSITIONAL_ONLY,
                param.POSITIONAL_OR_KEYWORD,
            }
        ]

        @functools.wraps(func)
        def wrapper(*args: object, **kwargs: object) -> object:
            given_params: set[str] = set()
            for i, _ in enumerate(args):
                try:
                    given_params.add(positional[i])
                except IndexError:
                    raise TypeError(
                        f"{func.__name__}() takes {len(positional)} argument(s) but {len(args)} were given"
                    ) from None

            for key in kwargs.keys():
                given_params.add(key)

            for variant in variants:
                matches = all((param in given_params for param in variant))
                if matches:
                    break
            else:  # no break
                if len(variants) > 1:
                    variations = human_join(
                        ["(" + human_join([quote(arg) for arg in variant], final="and") + ")" for variant in variants]
                    )
                    msg = f"Missing required arguments; Expected either {variations} arguments to be given"
                else:
                    assert len(variants) > 0

                    # TODO: this error message is not deterministic
                    missing = list(set(variants[0]) - given_params)
                    if len(missing) > 1:
                        msg = f"Missing required arguments: {human_join([quote(arg) for arg in missing])}"
                    else:
                        msg = f"Missing required argument: {quote(missing[0])}"
                raise TypeError(msg)
            return func(*args, **kwargs)

        return wrapper  # type: ignore

    return inner


_K = TypeVar("_K")
_V = TypeVar("_V")


@overload
def strip_not_given(obj: None) -> None: ...


@overload
def strip_not_given(obj: Mapping[_K, _V | NotGiven]) -> dict[_K, _V]: ...


@overload
def strip_not_given(obj: object) -> object: ...


def strip_not_given(obj: object | None) -> object:
    """Remove all top-level keys where their values are instances of `NotGiven`"""
    if obj is None:
        return None

    if not is_mapping(obj):
        return obj

    return {key: value for key, value in obj.items() if not isinstance(value, NotGiven)}


def coerce_integer(val: str) -> int:
    return int(val, base=10)


def coerce_float(val: str) -> float:
    return float(val)


def coerce_boolean(val: str) -> bool:
    return val == "true" or val == "1" or val == "on"


def maybe_coerce_integer(val: str | None) -> int | None:
    if val is None:
        return None
    return coerce_integer(val)


def maybe_coerce_float(val: str | None) -> float | None:
    if val is None:
        return None
    return coerce_float(val)


def maybe_coerce_boolean(val: str | None) -> bool | None:
    if val is None:
        return None
    return coerce_boolean(val)


def removeprefix(string: str, prefix: str) -> str:
    """Remove a prefix from a string.

    Backport of `str.removeprefix` for Python < 3.9
    """
    if string.startswith(prefix):
        return string[len(prefix) :]
    return string


def removesuffix(string: str, suffix: str) -> str:
    """Remove a suffix from a string.

    Backport of `str.removesuffix` for Python < 3.9
    """
    if string.endswith(suffix):
        return string[: -len(suffix)]
    return string


def file_from_path(path: str) -> FileTypes:
    contents = Path(path).read_bytes()
    file_name = os.path.basename(path)
    return (file_name, contents)


def get_required_header(headers: HeadersLike, header: str) -> str:
    lower_header = header.lower()
    if is_mapping_t(headers):
        # mypy doesn't understand the type narrowing here
        for k, v in headers.items():  # type: ignore
            if k.lower() == lower_header and isinstance(v, str):
                return v

    # to deal with the case where the header looks like Stainless-Event-Id
    intercaps_header = re.sub(r"([^\w])(\w)", lambda pat: pat.group(1) + pat.group(2).upper(), header.capitalize())

    for normalized_header in [header, lower_header, header.upper(), intercaps_header]:
        value = headers.get(normalized_header)
        if value:
            return value

    raise ValueError(f"Could not find {header} header")


def get_async_library() -> str:
    try:
        return sniffio.current_async_library()
    except Exception:
        return "false"


def lru_cache(*, maxsize: int | None = 128) -> Callable[[CallableT], CallableT]:
    """A version of functools.lru_cache that retains the type signature
    for the wrapped function arguments.
    """
    wrapper = functools.lru_cache(  # noqa: TID251
        maxsize=maxsize,
    )
    return cast(Any, wrapper)  # type: ignore[no-any-return]

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\xmldocs.py ===
# Natural Language Toolkit: XML Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Corpus reader for corpora whose documents are xml files.

(note -- not named 'xml' to avoid conflicting w/ standard xml package)
"""

import codecs
from xml.etree import ElementTree

from nltk.corpus.reader.api import CorpusReader
from nltk.corpus.reader.util import *
from nltk.data import SeekableUnicodeStreamReader
from nltk.internals import ElementWrapper
from nltk.tokenize import WordPunctTokenizer


class XMLCorpusReader(CorpusReader):
    """
    Corpus reader for corpora whose documents are xml files.

    Note that the ``XMLCorpusReader`` constructor does not take an
    ``encoding`` argument, because the unicode encoding is specified by
    the XML files themselves.  See the XML specs for more info.
    """

    def __init__(self, root, fileids, wrap_etree=False):
        self._wrap_etree = wrap_etree
        CorpusReader.__init__(self, root, fileids)

    def xml(self, fileid=None):
        # Make sure we have exactly one file -- no concatenating XML.
        if fileid is None and len(self._fileids) == 1:
            fileid = self._fileids[0]
        if not isinstance(fileid, str):
            raise TypeError("Expected a single file identifier string")
        # Read the XML in using ElementTree.
        with self.abspath(fileid).open() as fp:
            elt = ElementTree.parse(fp).getroot()
        # If requested, wrap it.
        if self._wrap_etree:
            elt = ElementWrapper(elt)
        # Return the ElementTree element.
        return elt

    def words(self, fileid=None):
        """
        Returns all of the words and punctuation symbols in the specified file
        that were in text nodes -- ie, tags are ignored. Like the xml() method,
        fileid can only specify one file.

        :return: the given file's text nodes as a list of words and punctuation symbols
        :rtype: list(str)
        """

        elt = self.xml(fileid)
        encoding = self.encoding(fileid)
        word_tokenizer = WordPunctTokenizer()
        try:
            iterator = elt.getiterator()
        except:
            iterator = elt.iter()
        out = []

        for node in iterator:
            text = node.text
            if text is not None:
                if isinstance(text, bytes):
                    text = text.decode(encoding)
                toks = word_tokenizer.tokenize(text)
                out.extend(toks)
        return out


class XMLCorpusView(StreamBackedCorpusView):
    """
    A corpus view that selects out specified elements from an XML
    file, and provides a flat list-like interface for accessing them.
    (Note: ``XMLCorpusView`` is not used by ``XMLCorpusReader`` itself,
    but may be used by subclasses of ``XMLCorpusReader``.)

    Every XML corpus view has a "tag specification", indicating what
    XML elements should be included in the view; and each (non-nested)
    element that matches this specification corresponds to one item in
    the view.  Tag specifications are regular expressions over tag
    paths, where a tag path is a list of element tag names, separated
    by '/', indicating the ancestry of the element.  Some examples:

      - ``'foo'``: A top-level element whose tag is ``foo``.
      - ``'foo/bar'``: An element whose tag is ``bar`` and whose parent
        is a top-level element whose tag is ``foo``.
      - ``'.*/foo'``: An element whose tag is ``foo``, appearing anywhere
        in the xml tree.
      - ``'.*/(foo|bar)'``: An wlement whose tag is ``foo`` or ``bar``,
        appearing anywhere in the xml tree.

    The view items are generated from the selected XML elements via
    the method ``handle_elt()``.  By default, this method returns the
    element as-is (i.e., as an ElementTree object); but it can be
    overridden, either via subclassing or via the ``elt_handler``
    constructor parameter.
    """

    #: If true, then display debugging output to stdout when reading
    #: blocks.
    _DEBUG = False

    #: The number of characters read at a time by this corpus reader.
    _BLOCK_SIZE = 1024

    def __init__(self, fileid, tagspec, elt_handler=None):
        """
        Create a new corpus view based on a specified XML file.

        Note that the ``XMLCorpusView`` constructor does not take an
        ``encoding`` argument, because the unicode encoding is
        specified by the XML files themselves.

        :type tagspec: str
        :param tagspec: A tag specification, indicating what XML
            elements should be included in the view.  Each non-nested
            element that matches this specification corresponds to one
            item in the view.

        :param elt_handler: A function used to transform each element
            to a value for the view.  If no handler is specified, then
            ``self.handle_elt()`` is called, which returns the element
            as an ElementTree object.  The signature of elt_handler is::

                elt_handler(elt, tagspec) -> value
        """
        if elt_handler:
            self.handle_elt = elt_handler

        self._tagspec = re.compile(tagspec + r"\Z")
        """The tag specification for this corpus view."""

        self._tag_context = {0: ()}
        """A dictionary mapping from file positions (as returned by
           ``stream.seek()`` to XML contexts.  An XML context is a
           tuple of XML tag names, indicating which tags have not yet
           been closed."""

        encoding = self._detect_encoding(fileid)
        StreamBackedCorpusView.__init__(self, fileid, encoding=encoding)

    def _detect_encoding(self, fileid):
        if isinstance(fileid, PathPointer):
            try:
                infile = fileid.open()
                s = infile.readline()
            finally:
                infile.close()
        else:
            with open(fileid, "rb") as infile:
                s = infile.readline()
        if s.startswith(codecs.BOM_UTF16_BE):
            return "utf-16-be"
        if s.startswith(codecs.BOM_UTF16_LE):
            return "utf-16-le"
        if s.startswith(codecs.BOM_UTF32_BE):
            return "utf-32-be"
        if s.startswith(codecs.BOM_UTF32_LE):
            return "utf-32-le"
        if s.startswith(codecs.BOM_UTF8):
            return "utf-8"
        m = re.match(rb'\s*<\?xml\b.*\bencoding="([^"]+)"', s)
        if m:
            return m.group(1).decode()
        m = re.match(rb"\s*<\?xml\b.*\bencoding='([^']+)'", s)
        if m:
            return m.group(1).decode()
        # No encoding found -- what should the default be?
        return "utf-8"

    def handle_elt(self, elt, context):
        """
        Convert an element into an appropriate value for inclusion in
        the view.  Unless overridden by a subclass or by the
        ``elt_handler`` constructor argument, this method simply
        returns ``elt``.

        :return: The view value corresponding to ``elt``.

        :type elt: ElementTree
        :param elt: The element that should be converted.

        :type context: str
        :param context: A string composed of element tags separated by
            forward slashes, indicating the XML context of the given
            element.  For example, the string ``'foo/bar/baz'``
            indicates that the element is a ``baz`` element whose
            parent is a ``bar`` element and whose grandparent is a
            top-level ``foo`` element.
        """
        return elt

    #: A regular expression that matches XML fragments that do not
    #: contain any un-closed tags.
    _VALID_XML_RE = re.compile(
        r"""
        [^<]*
        (
          ((<!--.*?-->)                         |  # comment
           (<![CDATA[.*?]])                     |  # raw character data
           (<!DOCTYPE\s+[^\[]*(\[[^\]]*])?\s*>) |  # doctype decl
           (<[^!>][^>]*>))                         # tag or PI
          [^<]*)*
        \Z""",
        re.DOTALL | re.VERBOSE,
    )

    #: A regular expression used to extract the tag name from a start tag,
    #: end tag, or empty-elt tag string.
    _XML_TAG_NAME = re.compile(r"<\s*(?:/\s*)?([^\s>]+)")

    #: A regular expression used to find all start-tags, end-tags, and
    #: empty-elt tags in an XML file.  This regexp is more lenient than
    #: the XML spec -- e.g., it allows spaces in some places where the
    #: spec does not.
    _XML_PIECE = re.compile(
        r"""
        # Include these so we can skip them:
        (?P<COMMENT>        <!--.*?-->                          )|
        (?P<CDATA>          <![CDATA[.*?]]>                     )|
        (?P<PI>             <\?.*?\?>                           )|
        (?P<DOCTYPE>        <!DOCTYPE\s+[^\[^>]*(\[[^\]]*])?\s*>)|
        # These are the ones we actually care about:
        (?P<EMPTY_ELT_TAG>  <\s*[^>/\?!\s][^>]*/\s*>            )|
        (?P<START_TAG>      <\s*[^>/\?!\s][^>]*>                )|
        (?P<END_TAG>        <\s*/[^>/\?!\s][^>]*>               )""",
        re.DOTALL | re.VERBOSE,
    )

    def _read_xml_fragment(self, stream):
        """
        Read a string from the given stream that does not contain any
        un-closed tags.  In particular, this function first reads a
        block from the stream of size ``self._BLOCK_SIZE``.  It then
        checks if that block contains an un-closed tag.  If it does,
        then this function either backtracks to the last '<', or reads
        another block.
        """
        fragment = ""

        if isinstance(stream, SeekableUnicodeStreamReader):
            startpos = stream.tell()
        while True:
            # Read a block and add it to the fragment.
            xml_block = stream.read(self._BLOCK_SIZE)
            fragment += xml_block

            # Do we have a well-formed xml fragment?
            if self._VALID_XML_RE.match(fragment):
                return fragment

            # Do we have a fragment that will never be well-formed?
            if re.search("[<>]", fragment).group(0) == ">":
                pos = stream.tell() - (
                    len(fragment) - re.search("[<>]", fragment).end()
                )
                raise ValueError('Unexpected ">" near char %s' % pos)

            # End of file?
            if not xml_block:
                raise ValueError("Unexpected end of file: tag not closed")

            # If not, then we must be in the middle of a <..tag..>.
            # If appropriate, backtrack to the most recent '<'
            # character.
            last_open_bracket = fragment.rfind("<")
            if last_open_bracket > 0:
                if self._VALID_XML_RE.match(fragment[:last_open_bracket]):
                    if isinstance(stream, SeekableUnicodeStreamReader):
                        stream.seek(startpos)
                        stream.char_seek_forward(last_open_bracket)
                    else:
                        stream.seek(-(len(fragment) - last_open_bracket), 1)
                    return fragment[:last_open_bracket]

            # Otherwise, read another block. (i.e., return to the
            # top of the loop.)

    def read_block(self, stream, tagspec=None, elt_handler=None):
        """
        Read from ``stream`` until we find at least one element that
        matches ``tagspec``, and return the result of applying
        ``elt_handler`` to each element found.
        """
        if tagspec is None:
            tagspec = self._tagspec
        if elt_handler is None:
            elt_handler = self.handle_elt

        # Use a stack of strings to keep track of our context:
        context = list(self._tag_context.get(stream.tell()))
        assert context is not None  # check this -- could it ever happen?

        elts = []

        elt_start = None  # where does the elt start
        elt_depth = None  # what context depth
        elt_text = ""

        while elts == [] or elt_start is not None:
            if isinstance(stream, SeekableUnicodeStreamReader):
                startpos = stream.tell()
            xml_fragment = self._read_xml_fragment(stream)

            # End of file.
            if not xml_fragment:
                if elt_start is None:
                    break
                else:
                    raise ValueError("Unexpected end of file")

            # Process each <tag> in the xml fragment.
            for piece in self._XML_PIECE.finditer(xml_fragment):
                if self._DEBUG:
                    print("{:>25} {}".format("/".join(context)[-20:], piece.group()))

                if piece.group("START_TAG"):
                    name = self._XML_TAG_NAME.match(piece.group()).group(1)
                    # Keep context up-to-date.
                    context.append(name)
                    # Is this one of the elts we're looking for?
                    if elt_start is None:
                        if re.match(tagspec, "/".join(context)):
                            elt_start = piece.start()
                            elt_depth = len(context)

                elif piece.group("END_TAG"):
                    name = self._XML_TAG_NAME.match(piece.group()).group(1)
                    # sanity checks:
                    if not context:
                        raise ValueError("Unmatched tag </%s>" % name)
                    if name != context[-1]:
                        raise ValueError(f"Unmatched tag <{context[-1]}>...</{name}>")
                    # Is this the end of an element?
                    if elt_start is not None and elt_depth == len(context):
                        elt_text += xml_fragment[elt_start : piece.end()]
                        elts.append((elt_text, "/".join(context)))
                        elt_start = elt_depth = None
                        elt_text = ""
                    # Keep context up-to-date
                    context.pop()

                elif piece.group("EMPTY_ELT_TAG"):
                    name = self._XML_TAG_NAME.match(piece.group()).group(1)
                    if elt_start is None:
                        if re.match(tagspec, "/".join(context) + "/" + name):
                            elts.append((piece.group(), "/".join(context) + "/" + name))

            if elt_start is not None:
                # If we haven't found any elements yet, then keep
                # looping until we do.
                if elts == []:
                    elt_text += xml_fragment[elt_start:]
                    elt_start = 0

                # If we've found at least one element, then try
                # backtracking to the start of the element that we're
                # inside of.
                else:
                    # take back the last start-tag, and return what
                    # we've gotten so far (elts is non-empty).
                    if self._DEBUG:
                        print(" " * 36 + "(backtrack)")
                    if isinstance(stream, SeekableUnicodeStreamReader):
                        stream.seek(startpos)
                        stream.char_seek_forward(elt_start)
                    else:
                        stream.seek(-(len(xml_fragment) - elt_start), 1)
                    context = context[: elt_depth - 1]
                    elt_start = elt_depth = None
                    elt_text = ""

        # Update the _tag_context dict.
        pos = stream.tell()
        if pos in self._tag_context:
            assert tuple(context) == self._tag_context[pos]
        else:
            self._tag_context[pos] = tuple(context)

        return [
            elt_handler(
                ElementTree.fromstring(elt.encode("ascii", "xmlcharrefreplace")),
                context,
            )
            for (elt, context) in elts
        ]

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\low_level.py ===
"""
Low-level helpers for the SecureTransport bindings.

These are Python functions that are not directly related to the high-level APIs
but are necessary to get them to work. They include a whole bunch of low-level
CoreFoundation messing about and memory management. The concerns in this module
are almost entirely about trying to avoid memory leaks and providing
appropriate and useful assistance to the higher-level code.
"""
import base64
import ctypes
import itertools
import os
import re
import ssl
import struct
import tempfile

from .bindings import CFConst, CoreFoundation, Security

# This regular expression is used to grab PEM data out of a PEM bundle.
_PEM_CERTS_RE = re.compile(
    b"-----BEGIN CERTIFICATE-----\n(.*?)\n-----END CERTIFICATE-----", re.DOTALL
)


def _cf_data_from_bytes(bytestring):
    """
    Given a bytestring, create a CFData object from it. This CFData object must
    be CFReleased by the caller.
    """
    return CoreFoundation.CFDataCreate(
        CoreFoundation.kCFAllocatorDefault, bytestring, len(bytestring)
    )


def _cf_dictionary_from_tuples(tuples):
    """
    Given a list of Python tuples, create an associated CFDictionary.
    """
    dictionary_size = len(tuples)

    # We need to get the dictionary keys and values out in the same order.
    keys = (t[0] for t in tuples)
    values = (t[1] for t in tuples)
    cf_keys = (CoreFoundation.CFTypeRef * dictionary_size)(*keys)
    cf_values = (CoreFoundation.CFTypeRef * dictionary_size)(*values)

    return CoreFoundation.CFDictionaryCreate(
        CoreFoundation.kCFAllocatorDefault,
        cf_keys,
        cf_values,
        dictionary_size,
        CoreFoundation.kCFTypeDictionaryKeyCallBacks,
        CoreFoundation.kCFTypeDictionaryValueCallBacks,
    )


def _cfstr(py_bstr):
    """
    Given a Python binary data, create a CFString.
    The string must be CFReleased by the caller.
    """
    c_str = ctypes.c_char_p(py_bstr)
    cf_str = CoreFoundation.CFStringCreateWithCString(
        CoreFoundation.kCFAllocatorDefault,
        c_str,
        CFConst.kCFStringEncodingUTF8,
    )
    return cf_str


def _create_cfstring_array(lst):
    """
    Given a list of Python binary data, create an associated CFMutableArray.
    The array must be CFReleased by the caller.

    Raises an ssl.SSLError on failure.
    """
    cf_arr = None
    try:
        cf_arr = CoreFoundation.CFArrayCreateMutable(
            CoreFoundation.kCFAllocatorDefault,
            0,
            ctypes.byref(CoreFoundation.kCFTypeArrayCallBacks),
        )
        if not cf_arr:
            raise MemoryError("Unable to allocate memory!")
        for item in lst:
            cf_str = _cfstr(item)
            if not cf_str:
                raise MemoryError("Unable to allocate memory!")
            try:
                CoreFoundation.CFArrayAppendValue(cf_arr, cf_str)
            finally:
                CoreFoundation.CFRelease(cf_str)
    except BaseException as e:
        if cf_arr:
            CoreFoundation.CFRelease(cf_arr)
        raise ssl.SSLError("Unable to allocate array: %s" % (e,))
    return cf_arr


def _cf_string_to_unicode(value):
    """
    Creates a Unicode string from a CFString object. Used entirely for error
    reporting.

    Yes, it annoys me quite a lot that this function is this complex.
    """
    value_as_void_p = ctypes.cast(value, ctypes.POINTER(ctypes.c_void_p))

    string = CoreFoundation.CFStringGetCStringPtr(
        value_as_void_p, CFConst.kCFStringEncodingUTF8
    )
    if string is None:
        buffer = ctypes.create_string_buffer(1024)
        result = CoreFoundation.CFStringGetCString(
            value_as_void_p, buffer, 1024, CFConst.kCFStringEncodingUTF8
        )
        if not result:
            raise OSError("Error copying C string from CFStringRef")
        string = buffer.value
    if string is not None:
        string = string.decode("utf-8")
    return string


def _assert_no_error(error, exception_class=None):
    """
    Checks the return code and throws an exception if there is an error to
    report
    """
    if error == 0:
        return

    cf_error_string = Security.SecCopyErrorMessageString(error, None)
    output = _cf_string_to_unicode(cf_error_string)
    CoreFoundation.CFRelease(cf_error_string)

    if output is None or output == u"":
        output = u"OSStatus %s" % error

    if exception_class is None:
        exception_class = ssl.SSLError

    raise exception_class(output)


def _cert_array_from_pem(pem_bundle):
    """
    Given a bundle of certs in PEM format, turns them into a CFArray of certs
    that can be used to validate a cert chain.
    """
    # Normalize the PEM bundle's line endings.
    pem_bundle = pem_bundle.replace(b"\r\n", b"\n")

    der_certs = [
        base64.b64decode(match.group(1)) for match in _PEM_CERTS_RE.finditer(pem_bundle)
    ]
    if not der_certs:
        raise ssl.SSLError("No root certificates specified")

    cert_array = CoreFoundation.CFArrayCreateMutable(
        CoreFoundation.kCFAllocatorDefault,
        0,
        ctypes.byref(CoreFoundation.kCFTypeArrayCallBacks),
    )
    if not cert_array:
        raise ssl.SSLError("Unable to allocate memory!")

    try:
        for der_bytes in der_certs:
            certdata = _cf_data_from_bytes(der_bytes)
            if not certdata:
                raise ssl.SSLError("Unable to allocate memory!")
            cert = Security.SecCertificateCreateWithData(
                CoreFoundation.kCFAllocatorDefault, certdata
            )
            CoreFoundation.CFRelease(certdata)
            if not cert:
                raise ssl.SSLError("Unable to build cert object!")

            CoreFoundation.CFArrayAppendValue(cert_array, cert)
            CoreFoundation.CFRelease(cert)
    except Exception:
        # We need to free the array before the exception bubbles further.
        # We only want to do that if an error occurs: otherwise, the caller
        # should free.
        CoreFoundation.CFRelease(cert_array)
        raise

    return cert_array


def _is_cert(item):
    """
    Returns True if a given CFTypeRef is a certificate.
    """
    expected = Security.SecCertificateGetTypeID()
    return CoreFoundation.CFGetTypeID(item) == expected


def _is_identity(item):
    """
    Returns True if a given CFTypeRef is an identity.
    """
    expected = Security.SecIdentityGetTypeID()
    return CoreFoundation.CFGetTypeID(item) == expected


def _temporary_keychain():
    """
    This function creates a temporary Mac keychain that we can use to work with
    credentials. This keychain uses a one-time password and a temporary file to
    store the data. We expect to have one keychain per socket. The returned
    SecKeychainRef must be freed by the caller, including calling
    SecKeychainDelete.

    Returns a tuple of the SecKeychainRef and the path to the temporary
    directory that contains it.
    """
    # Unfortunately, SecKeychainCreate requires a path to a keychain. This
    # means we cannot use mkstemp to use a generic temporary file. Instead,
    # we're going to create a temporary directory and a filename to use there.
    # This filename will be 8 random bytes expanded into base64. We also need
    # some random bytes to password-protect the keychain we're creating, so we
    # ask for 40 random bytes.
    random_bytes = os.urandom(40)
    filename = base64.b16encode(random_bytes[:8]).decode("utf-8")
    password = base64.b16encode(random_bytes[8:])  # Must be valid UTF-8
    tempdirectory = tempfile.mkdtemp()

    keychain_path = os.path.join(tempdirectory, filename).encode("utf-8")

    # We now want to create the keychain itself.
    keychain = Security.SecKeychainRef()
    status = Security.SecKeychainCreate(
        keychain_path, len(password), password, False, None, ctypes.byref(keychain)
    )
    _assert_no_error(status)

    # Having created the keychain, we want to pass it off to the caller.
    return keychain, tempdirectory


def _load_items_from_file(keychain, path):
    """
    Given a single file, loads all the trust objects from it into arrays and
    the keychain.
    Returns a tuple of lists: the first list is a list of identities, the
    second a list of certs.
    """
    certificates = []
    identities = []
    result_array = None

    with open(path, "rb") as f:
        raw_filedata = f.read()

    try:
        filedata = CoreFoundation.CFDataCreate(
            CoreFoundation.kCFAllocatorDefault, raw_filedata, len(raw_filedata)
        )
        result_array = CoreFoundation.CFArrayRef()
        result = Security.SecItemImport(
            filedata,  # cert data
            None,  # Filename, leaving it out for now
            None,  # What the type of the file is, we don't care
            None,  # what's in the file, we don't care
            0,  # import flags
            None,  # key params, can include passphrase in the future
            keychain,  # The keychain to insert into
            ctypes.byref(result_array),  # Results
        )
        _assert_no_error(result)

        # A CFArray is not very useful to us as an intermediary
        # representation, so we are going to extract the objects we want
        # and then free the array. We don't need to keep hold of keys: the
        # keychain already has them!
        result_count = CoreFoundation.CFArrayGetCount(result_array)
        for index in range(result_count):
            item = CoreFoundation.CFArrayGetValueAtIndex(result_array, index)
            item = ctypes.cast(item, CoreFoundation.CFTypeRef)

            if _is_cert(item):
                CoreFoundation.CFRetain(item)
                certificates.append(item)
            elif _is_identity(item):
                CoreFoundation.CFRetain(item)
                identities.append(item)
    finally:
        if result_array:
            CoreFoundation.CFRelease(result_array)

        CoreFoundation.CFRelease(filedata)

    return (identities, certificates)


def _load_client_cert_chain(keychain, *paths):
    """
    Load certificates and maybe keys from a number of files. Has the end goal
    of returning a CFArray containing one SecIdentityRef, and then zero or more
    SecCertificateRef objects, suitable for use as a client certificate trust
    chain.
    """
    # Ok, the strategy.
    #
    # This relies on knowing that macOS will not give you a SecIdentityRef
    # unless you have imported a key into a keychain. This is a somewhat
    # artificial limitation of macOS (for example, it doesn't necessarily
    # affect iOS), but there is nothing inside Security.framework that lets you
    # get a SecIdentityRef without having a key in a keychain.
    #
    # So the policy here is we take all the files and iterate them in order.
    # Each one will use SecItemImport to have one or more objects loaded from
    # it. We will also point at a keychain that macOS can use to work with the
    # private key.
    #
    # Once we have all the objects, we'll check what we actually have. If we
    # already have a SecIdentityRef in hand, fab: we'll use that. Otherwise,
    # we'll take the first certificate (which we assume to be our leaf) and
    # ask the keychain to give us a SecIdentityRef with that cert's associated
    # key.
    #
    # We'll then return a CFArray containing the trust chain: one
    # SecIdentityRef and then zero-or-more SecCertificateRef objects. The
    # responsibility for freeing this CFArray will be with the caller. This
    # CFArray must remain alive for the entire connection, so in practice it
    # will be stored with a single SSLSocket, along with the reference to the
    # keychain.
    certificates = []
    identities = []

    # Filter out bad paths.
    paths = (path for path in paths if path)

    try:
        for file_path in paths:
            new_identities, new_certs = _load_items_from_file(keychain, file_path)
            identities.extend(new_identities)
            certificates.extend(new_certs)

        # Ok, we have everything. The question is: do we have an identity? If
        # not, we want to grab one from the first cert we have.
        if not identities:
            new_identity = Security.SecIdentityRef()
            status = Security.SecIdentityCreateWithCertificate(
                keychain, certificates[0], ctypes.byref(new_identity)
            )
            _assert_no_error(status)
            identities.append(new_identity)

            # We now want to release the original certificate, as we no longer
            # need it.
            CoreFoundation.CFRelease(certificates.pop(0))

        # We now need to build a new CFArray that holds the trust chain.
        trust_chain = CoreFoundation.CFArrayCreateMutable(
            CoreFoundation.kCFAllocatorDefault,
            0,
            ctypes.byref(CoreFoundation.kCFTypeArrayCallBacks),
        )
        for item in itertools.chain(identities, certificates):
            # ArrayAppendValue does a CFRetain on the item. That's fine,
            # because the finally block will release our other refs to them.
            CoreFoundation.CFArrayAppendValue(trust_chain, item)

        return trust_chain
    finally:
        for obj in itertools.chain(identities, certificates):
            CoreFoundation.CFRelease(obj)


TLS_PROTOCOL_VERSIONS = {
    "SSLv2": (0, 2),
    "SSLv3": (3, 0),
    "TLSv1": (3, 1),
    "TLSv1.1": (3, 2),
    "TLSv1.2": (3, 3),
}


def _build_tls_unknown_ca_alert(version):
    """
    Builds a TLS alert record for an unknown CA.
    """
    ver_maj, ver_min = TLS_PROTOCOL_VERSIONS[version]
    severity_fatal = 0x02
    description_unknown_ca = 0x30
    msg = struct.pack(">BB", severity_fatal, description_unknown_ca)
    msg_len = len(msg)
    record_type_alert = 0x15
    record = struct.pack(">BBBH", record_type_alert, ver_maj, ver_min, msg_len) + msg
    return record

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc4211.py ===
# coding: utf-8
#
# This file is part of pyasn1-modules software.
#
# Created by Stanisław Pitucha with asn1ate tool.
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
# Internet X.509 Public Key Infrastructure Certificate Request
# Message Format (CRMF)
#
# ASN.1 source from:
# http://www.ietf.org/rfc/rfc4211.txt
#
from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import tag
from pyasn1.type import univ

from pyasn1_modules import rfc3280
from pyasn1_modules import rfc3852

MAX = float('inf')


def _buildOid(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))

    return univ.ObjectIdentifier(output)


id_pkix = _buildOid(1, 3, 6, 1, 5, 5, 7)

id_pkip = _buildOid(id_pkix, 5)

id_regCtrl = _buildOid(id_pkip, 1)


class SinglePubInfo(univ.Sequence):
    pass


SinglePubInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('pubMethod', univ.Integer(
        namedValues=namedval.NamedValues(('dontCare', 0), ('x500', 1), ('web', 2), ('ldap', 3)))),
    namedtype.OptionalNamedType('pubLocation', rfc3280.GeneralName())
)


class UTF8Pairs(char.UTF8String):
    pass


class PKMACValue(univ.Sequence):
    pass


PKMACValue.componentType = namedtype.NamedTypes(
    namedtype.NamedType('algId', rfc3280.AlgorithmIdentifier()),
    namedtype.NamedType('value', univ.BitString())
)


class POPOSigningKeyInput(univ.Sequence):
    pass


POPOSigningKeyInput.componentType = namedtype.NamedTypes(
    namedtype.NamedType(
        'authInfo', univ.Choice(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType(
                    'sender', rfc3280.GeneralName().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))
                ),
                namedtype.NamedType(
                    'publicKeyMAC', PKMACValue()
                )
            )
        )
    ),
    namedtype.NamedType('publicKey', rfc3280.SubjectPublicKeyInfo())
)


class POPOSigningKey(univ.Sequence):
    pass


POPOSigningKey.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('poposkInput', POPOSigningKeyInput().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('algorithmIdentifier', rfc3280.AlgorithmIdentifier()),
    namedtype.NamedType('signature', univ.BitString())
)


class Attributes(univ.SetOf):
    pass


Attributes.componentType = rfc3280.Attribute()


class PrivateKeyInfo(univ.Sequence):
    pass


PrivateKeyInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', univ.Integer()),
    namedtype.NamedType('privateKeyAlgorithm', rfc3280.AlgorithmIdentifier()),
    namedtype.NamedType('privateKey', univ.OctetString()),
    namedtype.OptionalNamedType('attributes',
                                Attributes().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)


class EncryptedValue(univ.Sequence):
    pass


EncryptedValue.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('intendedAlg', rfc3280.AlgorithmIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('symmAlg', rfc3280.AlgorithmIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('encSymmKey', univ.BitString().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.OptionalNamedType('keyAlg', rfc3280.AlgorithmIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
    namedtype.OptionalNamedType('valueHint', univ.OctetString().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))),
    namedtype.NamedType('encValue', univ.BitString())
)


class EncryptedKey(univ.Choice):
    pass


EncryptedKey.componentType = namedtype.NamedTypes(
    namedtype.NamedType('encryptedValue', EncryptedValue()),
    namedtype.NamedType('envelopedData', rfc3852.EnvelopedData().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)


class KeyGenParameters(univ.OctetString):
    pass


class PKIArchiveOptions(univ.Choice):
    pass


PKIArchiveOptions.componentType = namedtype.NamedTypes(
    namedtype.NamedType('encryptedPrivKey',
                        EncryptedKey().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('keyGenParameters',
                        KeyGenParameters().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('archiveRemGenPrivKey',
                        univ.Boolean().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
)

id_regCtrl_authenticator = _buildOid(id_regCtrl, 2)

id_regInfo = _buildOid(id_pkip, 2)

id_regInfo_certReq = _buildOid(id_regInfo, 2)


class ProtocolEncrKey(rfc3280.SubjectPublicKeyInfo):
    pass


class Authenticator(char.UTF8String):
    pass


class SubsequentMessage(univ.Integer):
    pass


SubsequentMessage.namedValues = namedval.NamedValues(
    ('encrCert', 0),
    ('challengeResp', 1)
)


class AttributeTypeAndValue(univ.Sequence):
    pass


AttributeTypeAndValue.componentType = namedtype.NamedTypes(
    namedtype.NamedType('type', univ.ObjectIdentifier()),
    namedtype.NamedType('value', univ.Any())
)


class POPOPrivKey(univ.Choice):
    pass


POPOPrivKey.componentType = namedtype.NamedTypes(
    namedtype.NamedType('thisMessage',
                        univ.BitString().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('subsequentMessage',
                        SubsequentMessage().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('dhMAC',
                        univ.BitString().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('agreeMAC',
                        PKMACValue().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),
    namedtype.NamedType('encryptedKey', rfc3852.EnvelopedData().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4)))
)


class ProofOfPossession(univ.Choice):
    pass


ProofOfPossession.componentType = namedtype.NamedTypes(
    namedtype.NamedType('raVerified',
                        univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('signature', POPOSigningKey().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
    namedtype.NamedType('keyEncipherment',
                        POPOPrivKey().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),
    namedtype.NamedType('keyAgreement',
                        POPOPrivKey().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3)))
)


class OptionalValidity(univ.Sequence):
    pass


OptionalValidity.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('notBefore', rfc3280.Time().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.OptionalNamedType('notAfter', rfc3280.Time().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
)


class CertTemplate(univ.Sequence):
    pass


CertTemplate.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('version', rfc3280.Version().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('serialNumber', univ.Integer().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('signingAlg', rfc3280.AlgorithmIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.OptionalNamedType('issuer', rfc3280.Name().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),
    namedtype.OptionalNamedType('validity', OptionalValidity().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4))),
    namedtype.OptionalNamedType('subject', rfc3280.Name().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),
    namedtype.OptionalNamedType('publicKey', rfc3280.SubjectPublicKeyInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 6))),
    namedtype.OptionalNamedType('issuerUID', rfc3280.UniqueIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 7))),
    namedtype.OptionalNamedType('subjectUID', rfc3280.UniqueIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 8))),
    namedtype.OptionalNamedType('extensions', rfc3280.Extensions().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 9)))
)


class Controls(univ.SequenceOf):
    pass


Controls.componentType = AttributeTypeAndValue()
Controls.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class CertRequest(univ.Sequence):
    pass


CertRequest.componentType = namedtype.NamedTypes(
    namedtype.NamedType('certReqId', univ.Integer()),
    namedtype.NamedType('certTemplate', CertTemplate()),
    namedtype.OptionalNamedType('controls', Controls())
)


class CertReqMsg(univ.Sequence):
    pass


CertReqMsg.componentType = namedtype.NamedTypes(
    namedtype.NamedType('certReq', CertRequest()),
    namedtype.OptionalNamedType('popo', ProofOfPossession()),
    namedtype.OptionalNamedType('regInfo', univ.SequenceOf(componentType=AttributeTypeAndValue()))
)


class CertReqMessages(univ.SequenceOf):
    pass


CertReqMessages.componentType = CertReqMsg()
CertReqMessages.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class CertReq(CertRequest):
    pass


id_regCtrl_pkiPublicationInfo = _buildOid(id_regCtrl, 3)


class CertId(univ.Sequence):
    pass


CertId.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuer', rfc3280.GeneralName()),
    namedtype.NamedType('serialNumber', univ.Integer())
)


class OldCertId(CertId):
    pass


class PKIPublicationInfo(univ.Sequence):
    pass


PKIPublicationInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('action',
                        univ.Integer(namedValues=namedval.NamedValues(('dontPublish', 0), ('pleasePublish', 1)))),
    namedtype.OptionalNamedType('pubInfos', univ.SequenceOf(componentType=SinglePubInfo()))
)


class EncKeyWithID(univ.Sequence):
    pass


EncKeyWithID.componentType = namedtype.NamedTypes(
    namedtype.NamedType('privateKey', PrivateKeyInfo()),
    namedtype.OptionalNamedType(
        'identifier', univ.Choice(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('string', char.UTF8String()),
                namedtype.NamedType('generalName', rfc3280.GeneralName())
            )
        )
    )
)

id_regCtrl_protocolEncrKey = _buildOid(id_regCtrl, 6)

id_regCtrl_oldCertID = _buildOid(id_regCtrl, 5)

id_smime = _buildOid(1, 2, 840, 113549, 1, 9, 16)


class PBMParameter(univ.Sequence):
    pass


PBMParameter.componentType = namedtype.NamedTypes(
    namedtype.NamedType('salt', univ.OctetString()),
    namedtype.NamedType('owf', rfc3280.AlgorithmIdentifier()),
    namedtype.NamedType('iterationCount', univ.Integer()),
    namedtype.NamedType('mac', rfc3280.AlgorithmIdentifier())
)

id_regCtrl_regToken = _buildOid(id_regCtrl, 1)

id_regCtrl_pkiArchiveOptions = _buildOid(id_regCtrl, 4)

id_regInfo_utf8Pairs = _buildOid(id_regInfo, 1)

id_ct = _buildOid(id_smime, 1)

id_ct_encKeyWithID = _buildOid(id_ct, 21)


class RegToken(char.UTF8String):
    pass

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\interpolatableHelpers.py ===
from fontTools.ttLib.ttGlyphSet import LerpGlyphSet
from fontTools.pens.basePen import AbstractPen, BasePen, DecomposingPen
from fontTools.pens.pointPen import AbstractPointPen, SegmentToPointPen
from fontTools.pens.recordingPen import RecordingPen, DecomposingRecordingPen
from fontTools.misc.transform import Transform
from collections import defaultdict, deque
from math import sqrt, copysign, atan2, pi
from enum import Enum
import itertools

import logging

log = logging.getLogger("fontTools.varLib.interpolatable")


class InterpolatableProblem:
    NOTHING = "nothing"
    MISSING = "missing"
    OPEN_PATH = "open_path"
    PATH_COUNT = "path_count"
    NODE_COUNT = "node_count"
    NODE_INCOMPATIBILITY = "node_incompatibility"
    CONTOUR_ORDER = "contour_order"
    WRONG_START_POINT = "wrong_start_point"
    KINK = "kink"
    UNDERWEIGHT = "underweight"
    OVERWEIGHT = "overweight"

    severity = {
        MISSING: 1,
        OPEN_PATH: 2,
        PATH_COUNT: 3,
        NODE_COUNT: 4,
        NODE_INCOMPATIBILITY: 5,
        CONTOUR_ORDER: 6,
        WRONG_START_POINT: 7,
        KINK: 8,
        UNDERWEIGHT: 9,
        OVERWEIGHT: 10,
        NOTHING: 11,
    }


def sort_problems(problems):
    """Sort problems by severity, then by glyph name, then by problem message."""
    return dict(
        sorted(
            problems.items(),
            key=lambda _: -min(
                (
                    (InterpolatableProblem.severity[p["type"]] + p.get("tolerance", 0))
                    for p in _[1]
                ),
            ),
            reverse=True,
        )
    )


def rot_list(l, k):
    """Rotate list by k items forward.  Ie. item at position 0 will be
    at position k in returned list.  Negative k is allowed."""
    return l[-k:] + l[:-k]


class PerContourPen(BasePen):
    def __init__(self, Pen, glyphset=None):
        BasePen.__init__(self, glyphset)
        self._glyphset = glyphset
        self._Pen = Pen
        self._pen = None
        self.value = []

    def _moveTo(self, p0):
        self._newItem()
        self._pen.moveTo(p0)

    def _lineTo(self, p1):
        self._pen.lineTo(p1)

    def _qCurveToOne(self, p1, p2):
        self._pen.qCurveTo(p1, p2)

    def _curveToOne(self, p1, p2, p3):
        self._pen.curveTo(p1, p2, p3)

    def _closePath(self):
        self._pen.closePath()
        self._pen = None

    def _endPath(self):
        self._pen.endPath()
        self._pen = None

    def _newItem(self):
        self._pen = pen = self._Pen()
        self.value.append(pen)


class PerContourOrComponentPen(PerContourPen):
    def addComponent(self, glyphName, transformation):
        self._newItem()
        self.value[-1].addComponent(glyphName, transformation)


class SimpleRecordingPointPen(AbstractPointPen):
    def __init__(self):
        self.value = []

    def beginPath(self, identifier=None, **kwargs):
        pass

    def endPath(self) -> None:
        pass

    def addPoint(self, pt, segmentType=None):
        self.value.append((pt, False if segmentType is None else True))


def vdiff_hypot2(v0, v1):
    s = 0
    for x0, x1 in zip(v0, v1):
        d = x1 - x0
        s += d * d
    return s


def vdiff_hypot2_complex(v0, v1):
    s = 0
    for x0, x1 in zip(v0, v1):
        d = x1 - x0
        s += d.real * d.real + d.imag * d.imag
        # This does the same but seems to be slower:
        # s += (d * d.conjugate()).real
    return s


def matching_cost(G, matching):
    return sum(G[i][j] for i, j in enumerate(matching))


def min_cost_perfect_bipartite_matching_scipy(G):
    n = len(G)
    rows, cols = linear_sum_assignment(G)
    assert (rows == list(range(n))).all()
    # Convert numpy array and integer to Python types,
    # to ensure that this is JSON-serializable.
    cols = list(int(e) for e in cols)
    return list(cols), matching_cost(G, cols)


def min_cost_perfect_bipartite_matching_munkres(G):
    n = len(G)
    cols = [None] * n
    for row, col in Munkres().compute(G):
        cols[row] = col
    return cols, matching_cost(G, cols)


def min_cost_perfect_bipartite_matching_bruteforce(G):
    n = len(G)

    if n > 6:
        raise Exception("Install Python module 'munkres' or 'scipy >= 0.17.0'")

    # Otherwise just brute-force
    permutations = itertools.permutations(range(n))
    best = list(next(permutations))
    best_cost = matching_cost(G, best)
    for p in permutations:
        cost = matching_cost(G, p)
        if cost < best_cost:
            best, best_cost = list(p), cost
    return best, best_cost


try:
    from scipy.optimize import linear_sum_assignment

    min_cost_perfect_bipartite_matching = min_cost_perfect_bipartite_matching_scipy
except ImportError:
    try:
        from munkres import Munkres

        min_cost_perfect_bipartite_matching = (
            min_cost_perfect_bipartite_matching_munkres
        )
    except ImportError:
        min_cost_perfect_bipartite_matching = (
            min_cost_perfect_bipartite_matching_bruteforce
        )


def contour_vector_from_stats(stats):
    # Don't change the order of items here.
    # It's okay to add to the end, but otherwise, other
    # code depends on it. Search for "covariance".
    size = sqrt(abs(stats.area))
    return (
        copysign((size), stats.area),
        stats.meanX,
        stats.meanY,
        stats.stddevX * 2,
        stats.stddevY * 2,
        stats.correlation * size,
    )


def matching_for_vectors(m0, m1):
    n = len(m0)

    identity_matching = list(range(n))

    costs = [[vdiff_hypot2(v0, v1) for v1 in m1] for v0 in m0]
    (
        matching,
        matching_cost,
    ) = min_cost_perfect_bipartite_matching(costs)
    identity_cost = sum(costs[i][i] for i in range(n))
    return matching, matching_cost, identity_cost


def points_characteristic_bits(points):
    bits = 0
    for pt, b in reversed(points):
        bits = (bits << 1) | b
    return bits


_NUM_ITEMS_PER_POINTS_COMPLEX_VECTOR = 4


def points_complex_vector(points):
    vector = []
    if not points:
        return vector
    points = [complex(*pt) for pt, _ in points]
    n = len(points)
    assert _NUM_ITEMS_PER_POINTS_COMPLEX_VECTOR == 4
    points.extend(points[: _NUM_ITEMS_PER_POINTS_COMPLEX_VECTOR - 1])
    while len(points) < _NUM_ITEMS_PER_POINTS_COMPLEX_VECTOR:
        points.extend(points[: _NUM_ITEMS_PER_POINTS_COMPLEX_VECTOR - 1])
    for i in range(n):
        # The weights are magic numbers.

        # The point itself
        p0 = points[i]
        vector.append(p0)

        # The vector to the next point
        p1 = points[i + 1]
        d0 = p1 - p0
        vector.append(d0 * 3)

        # The turn vector
        p2 = points[i + 2]
        d1 = p2 - p1
        vector.append(d1 - d0)

        # The angle to the next point, as a cross product;
        # Square root of, to match dimentionality of distance.
        cross = d0.real * d1.imag - d0.imag * d1.real
        cross = copysign(sqrt(abs(cross)), cross)
        vector.append(cross * 4)

    return vector


def add_isomorphisms(points, isomorphisms, reverse):
    reference_bits = points_characteristic_bits(points)
    n = len(points)

    # if points[0][0] == points[-1][0]:
    #   abort

    if reverse:
        points = points[::-1]
        bits = points_characteristic_bits(points)
    else:
        bits = reference_bits

    vector = points_complex_vector(points)

    assert len(vector) % n == 0
    mult = len(vector) // n
    mask = (1 << n) - 1

    for i in range(n):
        b = ((bits << (n - i)) & mask) | (bits >> i)
        if b == reference_bits:
            isomorphisms.append(
                (rot_list(vector, -i * mult), n - 1 - i if reverse else i, reverse)
            )


def find_parents_and_order(glyphsets, locations, *, discrete_axes=set()):
    parents = [None] + list(range(len(glyphsets) - 1))
    order = list(range(len(glyphsets)))
    if locations:
        # Order base master first
        bases = [
            i
            for i, l in enumerate(locations)
            if all(v == 0 for k, v in l.items() if k not in discrete_axes)
        ]
        if bases:
            logging.info("Found %s base masters: %s", len(bases), bases)
        else:
            logging.warning("No base master location found")

        # Form a minimum spanning tree of the locations
        try:
            from scipy.sparse.csgraph import minimum_spanning_tree

            graph = [[0] * len(locations) for _ in range(len(locations))]
            axes = set()
            for l in locations:
                axes.update(l.keys())
            axes = sorted(axes)
            vectors = [tuple(l.get(k, 0) for k in axes) for l in locations]
            for i, j in itertools.combinations(range(len(locations)), 2):
                i_discrete_location = {
                    k: v for k, v in zip(axes, vectors[i]) if k in discrete_axes
                }
                j_discrete_location = {
                    k: v for k, v in zip(axes, vectors[j]) if k in discrete_axes
                }
                if i_discrete_location != j_discrete_location:
                    continue
                graph[i][j] = vdiff_hypot2(vectors[i], vectors[j])

            tree = minimum_spanning_tree(graph, overwrite=True)
            rows, cols = tree.nonzero()
            graph = defaultdict(set)
            for row, col in zip(rows, cols):
                graph[row].add(col)
                graph[col].add(row)

            # Traverse graph from the base and assign parents
            parents = [None] * len(locations)
            order = []
            visited = set()
            queue = deque(bases)
            while queue:
                i = queue.popleft()
                visited.add(i)
                order.append(i)
                for j in sorted(graph[i]):
                    if j not in visited:
                        parents[j] = i
                        queue.append(j)
            assert len(order) == len(
                parents
            ), "Not all masters are reachable; report an issue"

        except ImportError:
            pass

        log.info("Parents: %s", parents)
        log.info("Order: %s", order)
    return parents, order


def transform_from_stats(stats, inverse=False):
    # https://cookierobotics.com/007/
    a = stats.varianceX
    b = stats.covariance
    c = stats.varianceY

    delta = (((a - c) * 0.5) ** 2 + b * b) ** 0.5
    lambda1 = (a + c) * 0.5 + delta  # Major eigenvalue
    lambda2 = (a + c) * 0.5 - delta  # Minor eigenvalue
    theta = atan2(lambda1 - a, b) if b != 0 else (pi * 0.5 if a < c else 0)
    trans = Transform()

    if lambda2 < 0:
        # XXX This is a hack.
        # The problem is that the covariance matrix is singular.
        # This happens when the contour is a line, or a circle.
        # In that case, the covariance matrix is not a good
        # representation of the contour.
        # We should probably detect this earlier and avoid
        # computing the covariance matrix in the first place.
        # But for now, we just avoid the division by zero.
        lambda2 = 0

    if inverse:
        trans = trans.translate(-stats.meanX, -stats.meanY)
        trans = trans.rotate(-theta)
        trans = trans.scale(1 / sqrt(lambda1), 1 / sqrt(lambda2))
    else:
        trans = trans.scale(sqrt(lambda1), sqrt(lambda2))
        trans = trans.rotate(theta)
        trans = trans.translate(stats.meanX, stats.meanY)

    return trans

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\thread_create_and_run_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from ..shared.chat_model import ChatModel
from .assistant_tool_param import AssistantToolParam
from ..shared_params.metadata import Metadata
from .code_interpreter_tool_param import CodeInterpreterToolParam
from .assistant_tool_choice_option_param import AssistantToolChoiceOptionParam
from .threads.message_content_part_param import MessageContentPartParam
from .assistant_response_format_option_param import AssistantResponseFormatOptionParam

__all__ = [
    "ThreadCreateAndRunParamsBase",
    "Thread",
    "ThreadMessage",
    "ThreadMessageAttachment",
    "ThreadMessageAttachmentTool",
    "ThreadMessageAttachmentToolFileSearch",
    "ThreadToolResources",
    "ThreadToolResourcesCodeInterpreter",
    "ThreadToolResourcesFileSearch",
    "ThreadToolResourcesFileSearchVectorStore",
    "ThreadToolResourcesFileSearchVectorStoreChunkingStrategy",
    "ThreadToolResourcesFileSearchVectorStoreChunkingStrategyAuto",
    "ThreadToolResourcesFileSearchVectorStoreChunkingStrategyStatic",
    "ThreadToolResourcesFileSearchVectorStoreChunkingStrategyStaticStatic",
    "ToolResources",
    "ToolResourcesCodeInterpreter",
    "ToolResourcesFileSearch",
    "TruncationStrategy",
    "ThreadCreateAndRunParamsNonStreaming",
    "ThreadCreateAndRunParamsStreaming",
]


class ThreadCreateAndRunParamsBase(TypedDict, total=False):
    assistant_id: Required[str]
    """
    The ID of the
    [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
    execute this run.
    """

    instructions: Optional[str]
    """Override the default system message of the assistant.

    This is useful for modifying the behavior on a per-run basis.
    """

    max_completion_tokens: Optional[int]
    """
    The maximum number of completion tokens that may be used over the course of the
    run. The run will make a best effort to use only the number of completion tokens
    specified, across multiple turns of the run. If the run exceeds the number of
    completion tokens specified, the run will end with status `incomplete`. See
    `incomplete_details` for more info.
    """

    max_prompt_tokens: Optional[int]
    """The maximum number of prompt tokens that may be used over the course of the run.

    The run will make a best effort to use only the number of prompt tokens
    specified, across multiple turns of the run. If the run exceeds the number of
    prompt tokens specified, the run will end with status `incomplete`. See
    `incomplete_details` for more info.
    """

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    model: Union[str, ChatModel, None]
    """
    The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
    be used to execute this run. If a value is provided here, it will override the
    model associated with the assistant. If not, the model associated with the
    assistant will be used.
    """

    parallel_tool_calls: bool
    """
    Whether to enable
    [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
    during tool use.
    """

    response_format: Optional[AssistantResponseFormatOptionParam]
    """Specifies the format that the model must output.

    Compatible with [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
    [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
    and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

    Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
    Outputs which ensures the model will match your supplied JSON schema. Learn more
    in the
    [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

    Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
    message the model generates is valid JSON.

    **Important:** when using JSON mode, you **must** also instruct the model to
    produce JSON yourself via a system or user message. Without this, the model may
    generate an unending stream of whitespace until the generation reaches the token
    limit, resulting in a long-running and seemingly "stuck" request. Also note that
    the message content may be partially cut off if `finish_reason="length"`, which
    indicates the generation exceeded `max_tokens` or the conversation exceeded the
    max context length.
    """

    temperature: Optional[float]
    """What sampling temperature to use, between 0 and 2.

    Higher values like 0.8 will make the output more random, while lower values like
    0.2 will make it more focused and deterministic.
    """

    thread: Thread
    """Options to create a new thread.

    If no thread is provided when running a request, an empty thread will be
    created.
    """

    tool_choice: Optional[AssistantToolChoiceOptionParam]
    """
    Controls which (if any) tool is called by the model. `none` means the model will
    not call any tools and instead generates a message. `auto` is the default value
    and means the model can pick between generating a message or calling one or more
    tools. `required` means the model must call one or more tools before responding
    to the user. Specifying a particular tool like `{"type": "file_search"}` or
    `{"type": "function", "function": {"name": "my_function"}}` forces the model to
    call that tool.
    """

    tool_resources: Optional[ToolResources]
    """A set of resources that are used by the assistant's tools.

    The resources are specific to the type of tool. For example, the
    `code_interpreter` tool requires a list of file IDs, while the `file_search`
    tool requires a list of vector store IDs.
    """

    tools: Optional[Iterable[AssistantToolParam]]
    """Override the tools the assistant can use for this run.

    This is useful for modifying the behavior on a per-run basis.
    """

    top_p: Optional[float]
    """
    An alternative to sampling with temperature, called nucleus sampling, where the
    model considers the results of the tokens with top_p probability mass. So 0.1
    means only the tokens comprising the top 10% probability mass are considered.

    We generally recommend altering this or temperature but not both.
    """

    truncation_strategy: Optional[TruncationStrategy]
    """Controls for how a thread will be truncated prior to the run.

    Use this to control the intial context window of the run.
    """


class ThreadMessageAttachmentToolFileSearch(TypedDict, total=False):
    type: Required[Literal["file_search"]]
    """The type of tool being defined: `file_search`"""


ThreadMessageAttachmentTool: TypeAlias = Union[CodeInterpreterToolParam, ThreadMessageAttachmentToolFileSearch]


class ThreadMessageAttachment(TypedDict, total=False):
    file_id: str
    """The ID of the file to attach to the message."""

    tools: Iterable[ThreadMessageAttachmentTool]
    """The tools to add this file to."""


class ThreadMessage(TypedDict, total=False):
    content: Required[Union[str, Iterable[MessageContentPartParam]]]
    """The text contents of the message."""

    role: Required[Literal["user", "assistant"]]
    """The role of the entity that is creating the message. Allowed values include:

    - `user`: Indicates the message is sent by an actual user and should be used in
      most cases to represent user-generated messages.
    - `assistant`: Indicates the message is generated by the assistant. Use this
      value to insert messages from the assistant into the conversation.
    """

    attachments: Optional[Iterable[ThreadMessageAttachment]]
    """A list of files attached to the message, and the tools they should be added to."""

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """


class ThreadToolResourcesCodeInterpreter(TypedDict, total=False):
    file_ids: List[str]
    """
    A list of [file](https://platform.openai.com/docs/api-reference/files) IDs made
    available to the `code_interpreter` tool. There can be a maximum of 20 files
    associated with the tool.
    """


class ThreadToolResourcesFileSearchVectorStoreChunkingStrategyAuto(TypedDict, total=False):
    type: Required[Literal["auto"]]
    """Always `auto`."""


class ThreadToolResourcesFileSearchVectorStoreChunkingStrategyStaticStatic(TypedDict, total=False):
    chunk_overlap_tokens: Required[int]
    """The number of tokens that overlap between chunks. The default value is `400`.

    Note that the overlap must not exceed half of `max_chunk_size_tokens`.
    """

    max_chunk_size_tokens: Required[int]
    """The maximum number of tokens in each chunk.

    The default value is `800`. The minimum value is `100` and the maximum value is
    `4096`.
    """


class ThreadToolResourcesFileSearchVectorStoreChunkingStrategyStatic(TypedDict, total=False):
    static: Required[ThreadToolResourcesFileSearchVectorStoreChunkingStrategyStaticStatic]

    type: Required[Literal["static"]]
    """Always `static`."""


ThreadToolResourcesFileSearchVectorStoreChunkingStrategy: TypeAlias = Union[
    ThreadToolResourcesFileSearchVectorStoreChunkingStrategyAuto,
    ThreadToolResourcesFileSearchVectorStoreChunkingStrategyStatic,
]


class ThreadToolResourcesFileSearchVectorStore(TypedDict, total=False):
    chunking_strategy: ThreadToolResourcesFileSearchVectorStoreChunkingStrategy
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


class ThreadToolResourcesFileSearch(TypedDict, total=False):
    vector_store_ids: List[str]
    """
    The
    [vector store](https://platform.openai.com/docs/api-reference/vector-stores/object)
    attached to this thread. There can be a maximum of 1 vector store attached to
    the thread.
    """

    vector_stores: Iterable[ThreadToolResourcesFileSearchVectorStore]
    """
    A helper to create a
    [vector store](https://platform.openai.com/docs/api-reference/vector-stores/object)
    with file_ids and attach it to this thread. There can be a maximum of 1 vector
    store attached to the thread.
    """


class ThreadToolResources(TypedDict, total=False):
    code_interpreter: ThreadToolResourcesCodeInterpreter

    file_search: ThreadToolResourcesFileSearch


class Thread(TypedDict, total=False):
    messages: Iterable[ThreadMessage]
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

    tool_resources: Optional[ThreadToolResources]
    """
    A set of resources that are made available to the assistant's tools in this
    thread. The resources are specific to the type of tool. For example, the
    `code_interpreter` tool requires a list of file IDs, while the `file_search`
    tool requires a list of vector store IDs.
    """


class ToolResourcesCodeInterpreter(TypedDict, total=False):
    file_ids: List[str]
    """
    A list of [file](https://platform.openai.com/docs/api-reference/files) IDs made
    available to the `code_interpreter` tool. There can be a maximum of 20 files
    associated with the tool.
    """


class ToolResourcesFileSearch(TypedDict, total=False):
    vector_store_ids: List[str]
    """
    The ID of the
    [vector store](https://platform.openai.com/docs/api-reference/vector-stores/object)
    attached to this assistant. There can be a maximum of 1 vector store attached to
    the assistant.
    """


class ToolResources(TypedDict, total=False):
    code_interpreter: ToolResourcesCodeInterpreter

    file_search: ToolResourcesFileSearch


class TruncationStrategy(TypedDict, total=False):
    type: Required[Literal["auto", "last_messages"]]
    """The truncation strategy to use for the thread.

    The default is `auto`. If set to `last_messages`, the thread will be truncated
    to the n most recent messages in the thread. When set to `auto`, messages in the
    middle of the thread will be dropped to fit the context length of the model,
    `max_prompt_tokens`.
    """

    last_messages: Optional[int]
    """
    The number of most recent messages from the thread when constructing the context
    for the run.
    """


class ThreadCreateAndRunParamsNonStreaming(ThreadCreateAndRunParamsBase, total=False):
    stream: Optional[Literal[False]]
    """
    If `true`, returns a stream of events that happen during the Run as server-sent
    events, terminating when the Run enters a terminal state with a `data: [DONE]`
    message.
    """


class ThreadCreateAndRunParamsStreaming(ThreadCreateAndRunParamsBase):
    stream: Required[Literal[True]]
    """
    If `true`, returns a stream of events that happen during the Run as server-sent
    events, terminating when the Run enters a terminal state with a `data: [DONE]`
    message.
    """


ThreadCreateAndRunParams = Union[ThreadCreateAndRunParamsNonStreaming, ThreadCreateAndRunParamsStreaming]

# === NexusCore/openenv\Lib\site-packages\charset_normalizer\cd.py ===
from __future__ import annotations

import importlib
from codecs import IncrementalDecoder
from collections import Counter
from functools import lru_cache
from typing import Counter as TypeCounter

from .constant import (
    FREQUENCIES,
    KO_NAMES,
    LANGUAGE_SUPPORTED_COUNT,
    TOO_SMALL_SEQUENCE,
    ZH_NAMES,
)
from .md import is_suspiciously_successive_range
from .models import CoherenceMatches
from .utils import (
    is_accentuated,
    is_latin,
    is_multi_byte_encoding,
    is_unicode_range_secondary,
    unicode_range,
)


def encoding_unicode_range(iana_name: str) -> list[str]:
    """
    Return associated unicode ranges in a single byte code page.
    """
    if is_multi_byte_encoding(iana_name):
        raise OSError("Function not supported on multi-byte code page")

    decoder = importlib.import_module(f"encodings.{iana_name}").IncrementalDecoder

    p: IncrementalDecoder = decoder(errors="ignore")
    seen_ranges: dict[str, int] = {}
    character_count: int = 0

    for i in range(0x40, 0xFF):
        chunk: str = p.decode(bytes([i]))

        if chunk:
            character_range: str | None = unicode_range(chunk)

            if character_range is None:
                continue

            if is_unicode_range_secondary(character_range) is False:
                if character_range not in seen_ranges:
                    seen_ranges[character_range] = 0
                seen_ranges[character_range] += 1
                character_count += 1

    return sorted(
        [
            character_range
            for character_range in seen_ranges
            if seen_ranges[character_range] / character_count >= 0.15
        ]
    )


def unicode_range_languages(primary_range: str) -> list[str]:
    """
    Return inferred languages used with a unicode range.
    """
    languages: list[str] = []

    for language, characters in FREQUENCIES.items():
        for character in characters:
            if unicode_range(character) == primary_range:
                languages.append(language)
                break

    return languages


@lru_cache()
def encoding_languages(iana_name: str) -> list[str]:
    """
    Single-byte encoding language association. Some code page are heavily linked to particular language(s).
    This function does the correspondence.
    """
    unicode_ranges: list[str] = encoding_unicode_range(iana_name)
    primary_range: str | None = None

    for specified_range in unicode_ranges:
        if "Latin" not in specified_range:
            primary_range = specified_range
            break

    if primary_range is None:
        return ["Latin Based"]

    return unicode_range_languages(primary_range)


@lru_cache()
def mb_encoding_languages(iana_name: str) -> list[str]:
    """
    Multi-byte encoding language association. Some code page are heavily linked to particular language(s).
    This function does the correspondence.
    """
    if (
        iana_name.startswith("shift_")
        or iana_name.startswith("iso2022_jp")
        or iana_name.startswith("euc_j")
        or iana_name == "cp932"
    ):
        return ["Japanese"]
    if iana_name.startswith("gb") or iana_name in ZH_NAMES:
        return ["Chinese"]
    if iana_name.startswith("iso2022_kr") or iana_name in KO_NAMES:
        return ["Korean"]

    return []


@lru_cache(maxsize=LANGUAGE_SUPPORTED_COUNT)
def get_target_features(language: str) -> tuple[bool, bool]:
    """
    Determine main aspects from a supported language if it contains accents and if is pure Latin.
    """
    target_have_accents: bool = False
    target_pure_latin: bool = True

    for character in FREQUENCIES[language]:
        if not target_have_accents and is_accentuated(character):
            target_have_accents = True
        if target_pure_latin and is_latin(character) is False:
            target_pure_latin = False

    return target_have_accents, target_pure_latin


def alphabet_languages(
    characters: list[str], ignore_non_latin: bool = False
) -> list[str]:
    """
    Return associated languages associated to given characters.
    """
    languages: list[tuple[str, float]] = []

    source_have_accents = any(is_accentuated(character) for character in characters)

    for language, language_characters in FREQUENCIES.items():
        target_have_accents, target_pure_latin = get_target_features(language)

        if ignore_non_latin and target_pure_latin is False:
            continue

        if target_have_accents is False and source_have_accents:
            continue

        character_count: int = len(language_characters)

        character_match_count: int = len(
            [c for c in language_characters if c in characters]
        )

        ratio: float = character_match_count / character_count

        if ratio >= 0.2:
            languages.append((language, ratio))

    languages = sorted(languages, key=lambda x: x[1], reverse=True)

    return [compatible_language[0] for compatible_language in languages]


def characters_popularity_compare(
    language: str, ordered_characters: list[str]
) -> float:
    """
    Determine if a ordered characters list (by occurrence from most appearance to rarest) match a particular language.
    The result is a ratio between 0. (absolutely no correspondence) and 1. (near perfect fit).
    Beware that is function is not strict on the match in order to ease the detection. (Meaning close match is 1.)
    """
    if language not in FREQUENCIES:
        raise ValueError(f"{language} not available")

    character_approved_count: int = 0
    FREQUENCIES_language_set = set(FREQUENCIES[language])

    ordered_characters_count: int = len(ordered_characters)
    target_language_characters_count: int = len(FREQUENCIES[language])

    large_alphabet: bool = target_language_characters_count > 26

    for character, character_rank in zip(
        ordered_characters, range(0, ordered_characters_count)
    ):
        if character not in FREQUENCIES_language_set:
            continue

        character_rank_in_language: int = FREQUENCIES[language].index(character)
        expected_projection_ratio: float = (
            target_language_characters_count / ordered_characters_count
        )
        character_rank_projection: int = int(character_rank * expected_projection_ratio)

        if (
            large_alphabet is False
            and abs(character_rank_projection - character_rank_in_language) > 4
        ):
            continue

        if (
            large_alphabet is True
            and abs(character_rank_projection - character_rank_in_language)
            < target_language_characters_count / 3
        ):
            character_approved_count += 1
            continue

        characters_before_source: list[str] = FREQUENCIES[language][
            0:character_rank_in_language
        ]
        characters_after_source: list[str] = FREQUENCIES[language][
            character_rank_in_language:
        ]
        characters_before: list[str] = ordered_characters[0:character_rank]
        characters_after: list[str] = ordered_characters[character_rank:]

        before_match_count: int = len(
            set(characters_before) & set(characters_before_source)
        )

        after_match_count: int = len(
            set(characters_after) & set(characters_after_source)
        )

        if len(characters_before_source) == 0 and before_match_count <= 4:
            character_approved_count += 1
            continue

        if len(characters_after_source) == 0 and after_match_count <= 4:
            character_approved_count += 1
            continue

        if (
            before_match_count / len(characters_before_source) >= 0.4
            or after_match_count / len(characters_after_source) >= 0.4
        ):
            character_approved_count += 1
            continue

    return character_approved_count / len(ordered_characters)


def alpha_unicode_split(decoded_sequence: str) -> list[str]:
    """
    Given a decoded text sequence, return a list of str. Unicode range / alphabet separation.
    Ex. a text containing English/Latin with a bit a Hebrew will return two items in the resulting list;
    One containing the latin letters and the other hebrew.
    """
    layers: dict[str, str] = {}

    for character in decoded_sequence:
        if character.isalpha() is False:
            continue

        character_range: str | None = unicode_range(character)

        if character_range is None:
            continue

        layer_target_range: str | None = None

        for discovered_range in layers:
            if (
                is_suspiciously_successive_range(discovered_range, character_range)
                is False
            ):
                layer_target_range = discovered_range
                break

        if layer_target_range is None:
            layer_target_range = character_range

        if layer_target_range not in layers:
            layers[layer_target_range] = character.lower()
            continue

        layers[layer_target_range] += character.lower()

    return list(layers.values())


def merge_coherence_ratios(results: list[CoherenceMatches]) -> CoherenceMatches:
    """
    This function merge results previously given by the function coherence_ratio.
    The return type is the same as coherence_ratio.
    """
    per_language_ratios: dict[str, list[float]] = {}
    for result in results:
        for sub_result in result:
            language, ratio = sub_result
            if language not in per_language_ratios:
                per_language_ratios[language] = [ratio]
                continue
            per_language_ratios[language].append(ratio)

    merge = [
        (
            language,
            round(
                sum(per_language_ratios[language]) / len(per_language_ratios[language]),
                4,
            ),
        )
        for language in per_language_ratios
    ]

    return sorted(merge, key=lambda x: x[1], reverse=True)


def filter_alt_coherence_matches(results: CoherenceMatches) -> CoherenceMatches:
    """
    We shall NOT return "English—" in CoherenceMatches because it is an alternative
    of "English". This function only keeps the best match and remove the em-dash in it.
    """
    index_results: dict[str, list[float]] = dict()

    for result in results:
        language, ratio = result
        no_em_name: str = language.replace("—", "")

        if no_em_name not in index_results:
            index_results[no_em_name] = []

        index_results[no_em_name].append(ratio)

    if any(len(index_results[e]) > 1 for e in index_results):
        filtered_results: CoherenceMatches = []

        for language in index_results:
            filtered_results.append((language, max(index_results[language])))

        return filtered_results

    return results


@lru_cache(maxsize=2048)
def coherence_ratio(
    decoded_sequence: str, threshold: float = 0.1, lg_inclusion: str | None = None
) -> CoherenceMatches:
    """
    Detect ANY language that can be identified in given sequence. The sequence will be analysed by layers.
    A layer = Character extraction by alphabets/ranges.
    """

    results: list[tuple[str, float]] = []
    ignore_non_latin: bool = False

    sufficient_match_count: int = 0

    lg_inclusion_list = lg_inclusion.split(",") if lg_inclusion is not None else []
    if "Latin Based" in lg_inclusion_list:
        ignore_non_latin = True
        lg_inclusion_list.remove("Latin Based")

    for layer in alpha_unicode_split(decoded_sequence):
        sequence_frequencies: TypeCounter[str] = Counter(layer)
        most_common = sequence_frequencies.most_common()

        character_count: int = sum(o for c, o in most_common)

        if character_count <= TOO_SMALL_SEQUENCE:
            continue

        popular_character_ordered: list[str] = [c for c, o in most_common]

        for language in lg_inclusion_list or alphabet_languages(
            popular_character_ordered, ignore_non_latin
        ):
            ratio: float = characters_popularity_compare(
                language, popular_character_ordered
            )

            if ratio < threshold:
                continue
            elif ratio >= 0.8:
                sufficient_match_count += 1

            results.append((language, round(ratio, 4)))

            if sufficient_match_count >= 3:
                break

    return sorted(
        filter_alt_coherence_matches(results), key=lambda x: x[1], reverse=True
    )

# === NexusCore/openenv\Lib\site-packages\fsspec\generic.py ===
from __future__ import annotations

import inspect
import logging
import os
import shutil
import uuid
from typing import Optional

from .asyn import AsyncFileSystem, _run_coros_in_chunks, sync_wrapper
from .callbacks import DEFAULT_CALLBACK
from .core import filesystem, get_filesystem_class, split_protocol, url_to_fs

_generic_fs = {}
logger = logging.getLogger("fsspec.generic")


def set_generic_fs(protocol, **storage_options):
    """Populate the dict used for method=="generic" lookups"""
    _generic_fs[protocol] = filesystem(protocol, **storage_options)


def _resolve_fs(url, method, protocol=None, storage_options=None):
    """Pick instance of backend FS"""
    url = url[0] if isinstance(url, (list, tuple)) else url
    protocol = protocol or split_protocol(url)[0]
    storage_options = storage_options or {}
    if method == "default":
        return filesystem(protocol)
    if method == "generic":
        return _generic_fs[protocol]
    if method == "current":
        cls = get_filesystem_class(protocol)
        return cls.current()
    if method == "options":
        fs, _ = url_to_fs(url, **storage_options.get(protocol, {}))
        return fs
    raise ValueError(f"Unknown FS resolution method: {method}")


def rsync(
    source,
    destination,
    delete_missing=False,
    source_field="size",
    dest_field="size",
    update_cond="different",
    inst_kwargs=None,
    fs=None,
    **kwargs,
):
    """Sync files between two directory trees

    (experimental)

    Parameters
    ----------
    source: str
        Root of the directory tree to take files from. This must be a directory, but
        do not include any terminating "/" character
    destination: str
        Root path to copy into. The contents of this location should be
        identical to the contents of ``source`` when done. This will be made a
        directory, and the terminal "/" should not be included.
    delete_missing: bool
        If there are paths in the destination that don't exist in the
        source and this is True, delete them. Otherwise, leave them alone.
    source_field: str | callable
        If ``update_field`` is "different", this is the key in the info
        of source files to consider for difference. Maybe a function of the
        info dict.
    dest_field: str | callable
        If ``update_field`` is "different", this is the key in the info
        of destination files to consider for difference. May be a function of
        the info dict.
    update_cond: "different"|"always"|"never"
        If "always", every file is copied, regardless of whether it exists in
        the destination. If "never", files that exist in the destination are
        not copied again. If "different" (default), only copy if the info
        fields given by ``source_field`` and ``dest_field`` (usually "size")
        are different. Other comparisons may be added in the future.
    inst_kwargs: dict|None
        If ``fs`` is None, use this set of keyword arguments to make a
        GenericFileSystem instance
    fs: GenericFileSystem|None
        Instance to use if explicitly given. The instance defines how to
        to make downstream file system instances from paths.

    Returns
    -------
    dict of the copy operations that were performed, {source: destination}
    """
    fs = fs or GenericFileSystem(**(inst_kwargs or {}))
    source = fs._strip_protocol(source)
    destination = fs._strip_protocol(destination)
    allfiles = fs.find(source, withdirs=True, detail=True)
    if not fs.isdir(source):
        raise ValueError("Can only rsync on a directory")
    otherfiles = fs.find(destination, withdirs=True, detail=True)
    dirs = [
        a
        for a, v in allfiles.items()
        if v["type"] == "directory" and a.replace(source, destination) not in otherfiles
    ]
    logger.debug(f"{len(dirs)} directories to create")
    if dirs:
        fs.make_many_dirs(
            [dirn.replace(source, destination) for dirn in dirs], exist_ok=True
        )
    allfiles = {a: v for a, v in allfiles.items() if v["type"] == "file"}
    logger.debug(f"{len(allfiles)} files to consider for copy")
    to_delete = [
        o
        for o, v in otherfiles.items()
        if o.replace(destination, source) not in allfiles and v["type"] == "file"
    ]
    for k, v in allfiles.copy().items():
        otherfile = k.replace(source, destination)
        if otherfile in otherfiles:
            if update_cond == "always":
                allfiles[k] = otherfile
            elif update_cond == "different":
                inf1 = source_field(v) if callable(source_field) else v[source_field]
                v2 = otherfiles[otherfile]
                inf2 = dest_field(v2) if callable(dest_field) else v2[dest_field]
                if inf1 != inf2:
                    # details mismatch, make copy
                    allfiles[k] = otherfile
                else:
                    # details match, don't copy
                    allfiles.pop(k)
        else:
            # file not in target yet
            allfiles[k] = otherfile
    logger.debug(f"{len(allfiles)} files to copy")
    if allfiles:
        source_files, target_files = zip(*allfiles.items())
        fs.cp(source_files, target_files, **kwargs)
    logger.debug(f"{len(to_delete)} files to delete")
    if delete_missing and to_delete:
        fs.rm(to_delete)
    return allfiles


class GenericFileSystem(AsyncFileSystem):
    """Wrapper over all other FS types

    <experimental!>

    This implementation is a single unified interface to be able to run FS operations
    over generic URLs, and dispatch to the specific implementations using the URL
    protocol prefix.

    Note: instances of this FS are always async, even if you never use it with any async
    backend.
    """

    protocol = "generic"  # there is no real reason to ever use a protocol with this FS

    def __init__(self, default_method="default", storage_options=None, **kwargs):
        """

        Parameters
        ----------
        default_method: str (optional)
            Defines how to configure backend FS instances. Options are:
            - "default": instantiate like FSClass(), with no
              extra arguments; this is the default instance of that FS, and can be
              configured via the config system
            - "generic": takes instances from the `_generic_fs` dict in this module,
              which you must populate before use. Keys are by protocol
            - "options": expects storage_options, a dict mapping protocol to
              kwargs to use when constructing the filesystem
            - "current": takes the most recently instantiated version of each FS
        """
        self.method = default_method
        self.st_opts = storage_options
        super().__init__(**kwargs)

    def _parent(self, path):
        fs = _resolve_fs(path, self.method, storage_options=self.st_opts)
        return fs.unstrip_protocol(fs._parent(path))

    def _strip_protocol(self, path):
        # normalization only
        fs = _resolve_fs(path, self.method, storage_options=self.st_opts)
        return fs.unstrip_protocol(fs._strip_protocol(path))

    async def _find(self, path, maxdepth=None, withdirs=False, detail=False, **kwargs):
        fs = _resolve_fs(path, self.method, storage_options=self.st_opts)
        if fs.async_impl:
            out = await fs._find(
                path, maxdepth=maxdepth, withdirs=withdirs, detail=True, **kwargs
            )
        else:
            out = fs.find(
                path, maxdepth=maxdepth, withdirs=withdirs, detail=True, **kwargs
            )
        result = {}
        for k, v in out.items():
            v = v.copy()  # don't corrupt target FS dircache
            name = fs.unstrip_protocol(k)
            v["name"] = name
            result[name] = v
        if detail:
            return result
        return list(result)

    async def _info(self, url, **kwargs):
        fs = _resolve_fs(url, self.method)
        if fs.async_impl:
            out = await fs._info(url, **kwargs)
        else:
            out = fs.info(url, **kwargs)
        out = out.copy()  # don't edit originals
        out["name"] = fs.unstrip_protocol(out["name"])
        return out

    async def _ls(
        self,
        url,
        detail=True,
        **kwargs,
    ):
        fs = _resolve_fs(url, self.method)
        if fs.async_impl:
            out = await fs._ls(url, detail=True, **kwargs)
        else:
            out = fs.ls(url, detail=True, **kwargs)
        out = [o.copy() for o in out]  # don't edit originals
        for o in out:
            o["name"] = fs.unstrip_protocol(o["name"])
        if detail:
            return out
        else:
            return [o["name"] for o in out]

    async def _cat_file(
        self,
        url,
        **kwargs,
    ):
        fs = _resolve_fs(url, self.method)
        if fs.async_impl:
            return await fs._cat_file(url, **kwargs)
        else:
            return fs.cat_file(url, **kwargs)

    async def _pipe_file(
        self,
        path,
        value,
        **kwargs,
    ):
        fs = _resolve_fs(path, self.method, storage_options=self.st_opts)
        if fs.async_impl:
            return await fs._pipe_file(path, value, **kwargs)
        else:
            return fs.pipe_file(path, value, **kwargs)

    async def _rm(self, url, **kwargs):
        urls = url
        if isinstance(urls, str):
            urls = [urls]
        fs = _resolve_fs(urls[0], self.method)
        if fs.async_impl:
            await fs._rm(urls, **kwargs)
        else:
            fs.rm(url, **kwargs)

    async def _makedirs(self, path, exist_ok=False):
        logger.debug("Make dir %s", path)
        fs = _resolve_fs(path, self.method, storage_options=self.st_opts)
        if fs.async_impl:
            await fs._makedirs(path, exist_ok=exist_ok)
        else:
            fs.makedirs(path, exist_ok=exist_ok)

    def rsync(self, source, destination, **kwargs):
        """Sync files between two directory trees

        See `func:rsync` for more details.
        """
        rsync(source, destination, fs=self, **kwargs)

    async def _cp_file(
        self,
        url,
        url2,
        blocksize=2**20,
        callback=DEFAULT_CALLBACK,
        tempdir: Optional[str] = None,
        **kwargs,
    ):
        fs = _resolve_fs(url, self.method)
        fs2 = _resolve_fs(url2, self.method)
        if fs is fs2:
            # pure remote
            if fs.async_impl:
                return await fs._copy(url, url2, **kwargs)
            else:
                return fs.copy(url, url2, **kwargs)
        await copy_file_op(fs, [url], fs2, [url2], tempdir, 1, on_error="raise")

    async def _make_many_dirs(self, urls, exist_ok=True):
        fs = _resolve_fs(urls[0], self.method)
        if fs.async_impl:
            coros = [fs._makedirs(u, exist_ok=exist_ok) for u in urls]
            await _run_coros_in_chunks(coros)
        else:
            for u in urls:
                fs.makedirs(u, exist_ok=exist_ok)

    make_many_dirs = sync_wrapper(_make_many_dirs)

    async def _copy(
        self,
        path1: list[str],
        path2: list[str],
        recursive: bool = False,
        on_error: str = "ignore",
        maxdepth: Optional[int] = None,
        batch_size: Optional[int] = None,
        tempdir: Optional[str] = None,
        **kwargs,
    ):
        # TODO: special case for one FS being local, which can use get/put
        # TODO: special case for one being memFS, which can use cat/pipe
        if recursive:
            raise NotImplementedError("Please use fsspec.generic.rsync")
        path1 = [path1] if isinstance(path1, str) else path1
        path2 = [path2] if isinstance(path2, str) else path2

        fs = _resolve_fs(path1, self.method)
        fs2 = _resolve_fs(path2, self.method)

        if fs is fs2:
            if fs.async_impl:
                return await fs._copy(path1, path2, **kwargs)
            else:
                return fs.copy(path1, path2, **kwargs)

        await copy_file_op(
            fs, path1, fs2, path2, tempdir, batch_size, on_error=on_error
        )


async def copy_file_op(
    fs1, url1, fs2, url2, tempdir=None, batch_size=20, on_error="ignore"
):
    import tempfile

    tempdir = tempdir or tempfile.mkdtemp()
    try:
        coros = [
            _copy_file_op(
                fs1,
                u1,
                fs2,
                u2,
                os.path.join(tempdir, uuid.uuid4().hex),
            )
            for u1, u2 in zip(url1, url2)
        ]
        out = await _run_coros_in_chunks(
            coros, batch_size=batch_size, return_exceptions=True
        )
    finally:
        shutil.rmtree(tempdir)
    if on_error == "return":
        return out
    elif on_error == "raise":
        for o in out:
            if isinstance(o, Exception):
                raise o


async def _copy_file_op(fs1, url1, fs2, url2, local, on_error="ignore"):
    if fs1.async_impl:
        await fs1._get_file(url1, local)
    else:
        fs1.get_file(url1, local)
    if fs2.async_impl:
        await fs2._put_file(local, url2)
    else:
        fs2.put_file(local, url2)
    os.unlink(local)
    logger.debug("Copy %s -> %s; done", url1, url2)


async def maybe_await(cor):
    if inspect.iscoroutine(cor):
        return await cor
    else:
        return cor

# === NexusCore/openenv\Lib\site-packages\markupsafe\__init__.py ===
from __future__ import annotations

import collections.abc as cabc
import string
import typing as t

try:
    from ._speedups import _escape_inner
except ImportError:
    from ._native import _escape_inner

if t.TYPE_CHECKING:
    import typing_extensions as te


class _HasHTML(t.Protocol):
    def __html__(self, /) -> str: ...


class _TPEscape(t.Protocol):
    def __call__(self, s: t.Any, /) -> Markup: ...


def escape(s: t.Any, /) -> Markup:
    """Replace the characters ``&``, ``<``, ``>``, ``'``, and ``"`` in
    the string with HTML-safe sequences. Use this if you need to display
    text that might contain such characters in HTML.

    If the object has an ``__html__`` method, it is called and the
    return value is assumed to already be safe for HTML.

    :param s: An object to be converted to a string and escaped.
    :return: A :class:`Markup` string with the escaped text.
    """
    # If the object is already a plain string, skip __html__ check and string
    # conversion. This is the most common use case.
    # Use type(s) instead of s.__class__ because a proxy object may be reporting
    # the __class__ of the proxied value.
    if type(s) is str:
        return Markup(_escape_inner(s))

    if hasattr(s, "__html__"):
        return Markup(s.__html__())

    return Markup(_escape_inner(str(s)))


def escape_silent(s: t.Any | None, /) -> Markup:
    """Like :func:`escape` but treats ``None`` as the empty string.
    Useful with optional values, as otherwise you get the string
    ``'None'`` when the value is ``None``.

    >>> escape(None)
    Markup('None')
    >>> escape_silent(None)
    Markup('')
    """
    if s is None:
        return Markup()

    return escape(s)


def soft_str(s: t.Any, /) -> str:
    """Convert an object to a string if it isn't already. This preserves
    a :class:`Markup` string rather than converting it back to a basic
    string, so it will still be marked as safe and won't be escaped
    again.

    >>> value = escape("<User 1>")
    >>> value
    Markup('&lt;User 1&gt;')
    >>> escape(str(value))
    Markup('&amp;lt;User 1&amp;gt;')
    >>> escape(soft_str(value))
    Markup('&lt;User 1&gt;')
    """
    if not isinstance(s, str):
        return str(s)

    return s


class Markup(str):
    """A string that is ready to be safely inserted into an HTML or XML
    document, either because it was escaped or because it was marked
    safe.

    Passing an object to the constructor converts it to text and wraps
    it to mark it safe without escaping. To escape the text, use the
    :meth:`escape` class method instead.

    >>> Markup("Hello, <em>World</em>!")
    Markup('Hello, <em>World</em>!')
    >>> Markup(42)
    Markup('42')
    >>> Markup.escape("Hello, <em>World</em>!")
    Markup('Hello &lt;em&gt;World&lt;/em&gt;!')

    This implements the ``__html__()`` interface that some frameworks
    use. Passing an object that implements ``__html__()`` will wrap the
    output of that method, marking it safe.

    >>> class Foo:
    ...     def __html__(self):
    ...         return '<a href="/foo">foo</a>'
    ...
    >>> Markup(Foo())
    Markup('<a href="/foo">foo</a>')

    This is a subclass of :class:`str`. It has the same methods, but
    escapes their arguments and returns a ``Markup`` instance.

    >>> Markup("<em>%s</em>") % ("foo & bar",)
    Markup('<em>foo &amp; bar</em>')
    >>> Markup("<em>Hello</em> ") + "<foo>"
    Markup('<em>Hello</em> &lt;foo&gt;')
    """

    __slots__ = ()

    def __new__(
        cls, object: t.Any = "", encoding: str | None = None, errors: str = "strict"
    ) -> te.Self:
        if hasattr(object, "__html__"):
            object = object.__html__()

        if encoding is None:
            return super().__new__(cls, object)

        return super().__new__(cls, object, encoding, errors)

    def __html__(self, /) -> te.Self:
        return self

    def __add__(self, value: str | _HasHTML, /) -> te.Self:
        if isinstance(value, str) or hasattr(value, "__html__"):
            return self.__class__(super().__add__(self.escape(value)))

        return NotImplemented

    def __radd__(self, value: str | _HasHTML, /) -> te.Self:
        if isinstance(value, str) or hasattr(value, "__html__"):
            return self.escape(value).__add__(self)

        return NotImplemented

    def __mul__(self, value: t.SupportsIndex, /) -> te.Self:
        return self.__class__(super().__mul__(value))

    def __rmul__(self, value: t.SupportsIndex, /) -> te.Self:
        return self.__class__(super().__mul__(value))

    def __mod__(self, value: t.Any, /) -> te.Self:
        if isinstance(value, tuple):
            # a tuple of arguments, each wrapped
            value = tuple(_MarkupEscapeHelper(x, self.escape) for x in value)
        elif hasattr(type(value), "__getitem__") and not isinstance(value, str):
            # a mapping of arguments, wrapped
            value = _MarkupEscapeHelper(value, self.escape)
        else:
            # a single argument, wrapped with the helper and a tuple
            value = (_MarkupEscapeHelper(value, self.escape),)

        return self.__class__(super().__mod__(value))

    def __repr__(self, /) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"

    def join(self, iterable: cabc.Iterable[str | _HasHTML], /) -> te.Self:
        return self.__class__(super().join(map(self.escape, iterable)))

    def split(  # type: ignore[override]
        self, /, sep: str | None = None, maxsplit: t.SupportsIndex = -1
    ) -> list[te.Self]:
        return [self.__class__(v) for v in super().split(sep, maxsplit)]

    def rsplit(  # type: ignore[override]
        self, /, sep: str | None = None, maxsplit: t.SupportsIndex = -1
    ) -> list[te.Self]:
        return [self.__class__(v) for v in super().rsplit(sep, maxsplit)]

    def splitlines(  # type: ignore[override]
        self, /, keepends: bool = False
    ) -> list[te.Self]:
        return [self.__class__(v) for v in super().splitlines(keepends)]

    def unescape(self, /) -> str:
        """Convert escaped markup back into a text string. This replaces
        HTML entities with the characters they represent.

        >>> Markup("Main &raquo; <em>About</em>").unescape()
        'Main » <em>About</em>'
        """
        from html import unescape

        return unescape(str(self))

    def striptags(self, /) -> str:
        """:meth:`unescape` the markup, remove tags, and normalize
        whitespace to single spaces.

        >>> Markup("Main &raquo;\t<em>About</em>").striptags()
        'Main » About'
        """
        value = str(self)

        # Look for comments then tags separately. Otherwise, a comment that
        # contains a tag would end early, leaving some of the comment behind.

        # keep finding comment start marks
        while (start := value.find("<!--")) != -1:
            # find a comment end mark beyond the start, otherwise stop
            if (end := value.find("-->", start)) == -1:
                break

            value = f"{value[:start]}{value[end + 3:]}"

        # remove tags using the same method
        while (start := value.find("<")) != -1:
            if (end := value.find(">", start)) == -1:
                break

            value = f"{value[:start]}{value[end + 1:]}"

        # collapse spaces
        value = " ".join(value.split())
        return self.__class__(value).unescape()

    @classmethod
    def escape(cls, s: t.Any, /) -> te.Self:
        """Escape a string. Calls :func:`escape` and ensures that for
        subclasses the correct type is returned.
        """
        rv = escape(s)

        if rv.__class__ is not cls:
            return cls(rv)

        return rv  # type: ignore[return-value]

    def __getitem__(self, key: t.SupportsIndex | slice, /) -> te.Self:
        return self.__class__(super().__getitem__(key))

    def capitalize(self, /) -> te.Self:
        return self.__class__(super().capitalize())

    def title(self, /) -> te.Self:
        return self.__class__(super().title())

    def lower(self, /) -> te.Self:
        return self.__class__(super().lower())

    def upper(self, /) -> te.Self:
        return self.__class__(super().upper())

    def replace(self, old: str, new: str, count: t.SupportsIndex = -1, /) -> te.Self:
        return self.__class__(super().replace(old, self.escape(new), count))

    def ljust(self, width: t.SupportsIndex, fillchar: str = " ", /) -> te.Self:
        return self.__class__(super().ljust(width, self.escape(fillchar)))

    def rjust(self, width: t.SupportsIndex, fillchar: str = " ", /) -> te.Self:
        return self.__class__(super().rjust(width, self.escape(fillchar)))

    def lstrip(self, chars: str | None = None, /) -> te.Self:
        return self.__class__(super().lstrip(chars))

    def rstrip(self, chars: str | None = None, /) -> te.Self:
        return self.__class__(super().rstrip(chars))

    def center(self, width: t.SupportsIndex, fillchar: str = " ", /) -> te.Self:
        return self.__class__(super().center(width, self.escape(fillchar)))

    def strip(self, chars: str | None = None, /) -> te.Self:
        return self.__class__(super().strip(chars))

    def translate(
        self,
        table: cabc.Mapping[int, str | int | None],  # type: ignore[override]
        /,
    ) -> str:
        return self.__class__(super().translate(table))

    def expandtabs(self, /, tabsize: t.SupportsIndex = 8) -> te.Self:
        return self.__class__(super().expandtabs(tabsize))

    def swapcase(self, /) -> te.Self:
        return self.__class__(super().swapcase())

    def zfill(self, width: t.SupportsIndex, /) -> te.Self:
        return self.__class__(super().zfill(width))

    def casefold(self, /) -> te.Self:
        return self.__class__(super().casefold())

    def removeprefix(self, prefix: str, /) -> te.Self:
        return self.__class__(super().removeprefix(prefix))

    def removesuffix(self, suffix: str) -> te.Self:
        return self.__class__(super().removesuffix(suffix))

    def partition(self, sep: str, /) -> tuple[te.Self, te.Self, te.Self]:
        left, sep, right = super().partition(sep)
        cls = self.__class__
        return cls(left), cls(sep), cls(right)

    def rpartition(self, sep: str, /) -> tuple[te.Self, te.Self, te.Self]:
        left, sep, right = super().rpartition(sep)
        cls = self.__class__
        return cls(left), cls(sep), cls(right)

    def format(self, *args: t.Any, **kwargs: t.Any) -> te.Self:
        formatter = EscapeFormatter(self.escape)
        return self.__class__(formatter.vformat(self, args, kwargs))

    def format_map(
        self,
        mapping: cabc.Mapping[str, t.Any],  # type: ignore[override]
        /,
    ) -> te.Self:
        formatter = EscapeFormatter(self.escape)
        return self.__class__(formatter.vformat(self, (), mapping))

    def __html_format__(self, format_spec: str, /) -> te.Self:
        if format_spec:
            raise ValueError("Unsupported format specification for Markup.")

        return self


class EscapeFormatter(string.Formatter):
    __slots__ = ("escape",)

    def __init__(self, escape: _TPEscape) -> None:
        self.escape: _TPEscape = escape
        super().__init__()

    def format_field(self, value: t.Any, format_spec: str) -> str:
        if hasattr(value, "__html_format__"):
            rv = value.__html_format__(format_spec)
        elif hasattr(value, "__html__"):
            if format_spec:
                raise ValueError(
                    f"Format specifier {format_spec} given, but {type(value)} does not"
                    " define __html_format__. A class that defines __html__ must define"
                    " __html_format__ to work with format specifiers."
                )
            rv = value.__html__()
        else:
            # We need to make sure the format spec is str here as
            # otherwise the wrong callback methods are invoked.
            rv = super().format_field(value, str(format_spec))
        return str(self.escape(rv))


class _MarkupEscapeHelper:
    """Helper for :meth:`Markup.__mod__`."""

    __slots__ = ("obj", "escape")

    def __init__(self, obj: t.Any, escape: _TPEscape) -> None:
        self.obj: t.Any = obj
        self.escape: _TPEscape = escape

    def __getitem__(self, key: t.Any, /) -> te.Self:
        return self.__class__(self.obj[key], self.escape)

    def __str__(self, /) -> str:
        return str(self.escape(self.obj))

    def __repr__(self, /) -> str:
        return str(self.escape(repr(self.obj)))

    def __int__(self, /) -> int:
        return int(self.obj)

    def __float__(self, /) -> float:
        return float(self.obj)


def __getattr__(name: str) -> t.Any:
    if name == "__version__":
        import importlib.metadata
        import warnings

        warnings.warn(
            "The '__version__' attribute is deprecated and will be removed in"
            " MarkupSafe 3.1. Use feature detection, or"
            ' `importlib.metadata.version("markupsafe")`, instead.',
            stacklevel=2,
        )
        return importlib.metadata.version("markupsafe")

    raise AttributeError(name)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_safe_repr.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

# Gotten from ptvsd for supporting the format expected there.
import sys
from _pydevd_bundle.pydevd_constants import IS_PY36_OR_GREATER
import locale
from _pydev_bundle import pydev_log


class SafeRepr(object):
    # Can be used to override the encoding from locale.getpreferredencoding()
    locale_preferred_encoding = None

    # Can be used to override the encoding used for sys.stdout.encoding
    sys_stdout_encoding = None

    # String types are truncated to maxstring_outer when at the outer-
    # most level, and truncated to maxstring_inner characters inside
    # collections.
    maxstring_outer = 2**16
    maxstring_inner = 128
    string_types = (str, bytes)
    bytes = bytes
    set_info = (set, "{", "}", False)
    frozenset_info = (frozenset, "frozenset({", "})", False)
    int_types = (int,)
    long_iter_types = (list, tuple, bytearray, range, dict, set, frozenset)

    # Collection types are recursively iterated for each limit in
    # maxcollection.
    maxcollection = (60, 20)

    # Specifies type, prefix string, suffix string, and whether to include a
    # comma if there is only one element. (Using a sequence rather than a
    # mapping because we use isinstance() to determine the matching type.)
    collection_types = [
        (tuple, "(", ")", True),
        (list, "[", "]", False),
        frozenset_info,
        set_info,
    ]
    try:
        from collections import deque

        collection_types.append((deque, "deque([", "])", False))
    except Exception:
        pass

    # type, prefix string, suffix string, item prefix string,
    # item key/value separator, item suffix string
    dict_types = [(dict, "{", "}", "", ": ", "")]
    try:
        from collections import OrderedDict

        dict_types.append((OrderedDict, "OrderedDict([", "])", "(", ", ", ")"))
    except Exception:
        pass

    # All other types are treated identically to strings, but using
    # different limits.
    maxother_outer = 2**16
    maxother_inner = 128

    convert_to_hex = False
    raw_value = False

    def __call__(self, obj):
        """
        :param object obj:
            The object for which we want a representation.

        :return str:
            Returns bytes encoded as utf-8 on py2 and str on py3.
        """
        try:
            return "".join(self._repr(obj, 0))
        except Exception:
            try:
                return "An exception was raised: %r" % sys.exc_info()[1]
            except Exception:
                return "An exception was raised"

    def _repr(self, obj, level):
        """Returns an iterable of the parts in the final repr string."""

        try:
            obj_repr = type(obj).__repr__
        except Exception:
            obj_repr = None

        def has_obj_repr(t):
            r = t.__repr__
            try:
                return obj_repr == r
            except Exception:
                return obj_repr is r

        for t, prefix, suffix, comma in self.collection_types:
            if isinstance(obj, t) and has_obj_repr(t):
                return self._repr_iter(obj, level, prefix, suffix, comma)

        for t, prefix, suffix, item_prefix, item_sep, item_suffix in self.dict_types:  # noqa
            if isinstance(obj, t) and has_obj_repr(t):
                return self._repr_dict(obj, level, prefix, suffix, item_prefix, item_sep, item_suffix)

        for t in self.string_types:
            if isinstance(obj, t) and has_obj_repr(t):
                return self._repr_str(obj, level)

        if self._is_long_iter(obj):
            return self._repr_long_iter(obj)

        return self._repr_other(obj, level)

    # Determines whether an iterable exceeds the limits set in
    # maxlimits, and is therefore unsafe to repr().
    def _is_long_iter(self, obj, level=0):
        try:
            # Strings have their own limits (and do not nest). Because
            # they don't have __iter__ in 2.x, this check goes before
            # the next one.
            if isinstance(obj, self.string_types):
                return len(obj) > self.maxstring_inner

            # If it's not an iterable (and not a string), it's fine.
            if not hasattr(obj, "__iter__"):
                return False

            # If it's not an instance of these collection types then it
            # is fine. Note: this is a fix for
            # https://github.com/Microsoft/ptvsd/issues/406
            if not isinstance(obj, self.long_iter_types):
                return False

            # Iterable is its own iterator - this is a one-off iterable
            # like generator or enumerate(). We can't really count that,
            # but repr() for these should not include any elements anyway,
            # so we can treat it the same as non-iterables.
            if obj is iter(obj):
                return False

            # range reprs fine regardless of length.
            if isinstance(obj, range):
                return False

            # numpy and scipy collections (ndarray etc) have
            # self-truncating repr, so they're always safe.
            try:
                module = type(obj).__module__.partition(".")[0]
                if module in ("numpy", "scipy"):
                    return False
            except Exception:
                pass

            # Iterables that nest too deep are considered long.
            if level >= len(self.maxcollection):
                return True

            # It is too long if the length exceeds the limit, or any
            # of its elements are long iterables.
            if hasattr(obj, "__len__"):
                try:
                    size = len(obj)
                except Exception:
                    size = None
                if size is not None and size > self.maxcollection[level]:
                    return True
                return any((self._is_long_iter(item, level + 1) for item in obj))  # noqa
            return any(i > self.maxcollection[level] or self._is_long_iter(item, level + 1) for i, item in enumerate(obj))  # noqa

        except Exception:
            # If anything breaks, assume the worst case.
            return True

    def _repr_iter(self, obj, level, prefix, suffix, comma_after_single_element=False):
        yield prefix

        if level >= len(self.maxcollection):
            yield "..."
        else:
            count = self.maxcollection[level]
            yield_comma = False
            for item in obj:
                if yield_comma:
                    yield ", "
                yield_comma = True

                count -= 1
                if count <= 0:
                    yield "..."
                    break

                for p in self._repr(item, 100 if item is obj else level + 1):
                    yield p
            else:
                if comma_after_single_element:
                    if count == self.maxcollection[level] - 1:
                        yield ","
        yield suffix

    def _repr_long_iter(self, obj):
        try:
            length = hex(len(obj)) if self.convert_to_hex else len(obj)
            obj_repr = "<%s, len() = %s>" % (type(obj).__name__, length)
        except Exception:
            try:
                obj_repr = "<" + type(obj).__name__ + ">"
            except Exception:
                obj_repr = "<no repr available for object>"
        yield obj_repr

    def _repr_dict(self, obj, level, prefix, suffix, item_prefix, item_sep, item_suffix):
        if not obj:
            yield prefix + suffix
            return
        if level >= len(self.maxcollection):
            yield prefix + "..." + suffix
            return

        yield prefix

        count = self.maxcollection[level]
        yield_comma = False

        if IS_PY36_OR_GREATER:
            # On Python 3.6 (onwards) dictionaries now keep
            # insertion order.
            sorted_keys = list(obj)
        else:
            try:
                sorted_keys = sorted(obj)
            except Exception:
                sorted_keys = list(obj)

        for key in sorted_keys:
            if yield_comma:
                yield ", "
            yield_comma = True

            count -= 1
            if count <= 0:
                yield "..."
                break

            yield item_prefix
            for p in self._repr(key, level + 1):
                yield p

            yield item_sep

            try:
                item = obj[key]
            except Exception:
                yield "<?>"
            else:
                for p in self._repr(item, 100 if item is obj else level + 1):
                    yield p
            yield item_suffix

        yield suffix

    def _repr_str(self, obj, level):
        try:
            if self.raw_value:
                # For raw value retrieval, ignore all limits.
                if isinstance(obj, bytes):
                    yield obj.decode("latin-1")
                else:
                    yield obj
                return

            limit_inner = self.maxother_inner
            limit_outer = self.maxother_outer
            limit = limit_inner if level > 0 else limit_outer
            if len(obj) <= limit:
                # Note that we check the limit before doing the repr (so, the final string
                # may actually be considerably bigger on some cases, as besides
                # the additional u, b, ' chars, some chars may be escaped in repr, so
                # even a single char such as \U0010ffff may end up adding more
                # chars than expected).
                yield self._convert_to_unicode_or_bytes_repr(repr(obj))
                return

            # Slightly imprecise calculations - we may end up with a string that is
            # up to 6 characters longer than limit. If you need precise formatting,
            # you are using the wrong class.
            left_count, right_count = max(1, int(2 * limit / 3)), max(1, int(limit / 3))  # noqa

            # Important: only do repr after slicing to avoid duplicating a byte array that could be
            # huge.

            # Note: we don't deal with high surrogates here because we're not dealing with the
            # repr() of a random object.
            # i.e.: A high surrogate unicode char may be splitted on Py2, but as we do a `repr`
            # afterwards, that's ok.

            # Also, we just show the unicode/string/bytes repr() directly to make clear what the
            # input type was (so, on py2 a unicode would start with u' and on py3 a bytes would
            # start with b').

            part1 = obj[:left_count]
            part1 = repr(part1)
            part1 = part1[: part1.rindex("'")]  # Remove the last '

            part2 = obj[-right_count:]
            part2 = repr(part2)
            part2 = part2[part2.index("'") + 1 :]  # Remove the first ' (and possibly u or b).

            yield part1
            yield "..."
            yield part2
        except:
            # This shouldn't really happen, but let's play it safe.
            pydev_log.exception("Error getting string representation to show.")
            for part in self._repr_obj(obj, level, self.maxother_inner, self.maxother_outer):
                yield part

    def _repr_other(self, obj, level):
        return self._repr_obj(obj, level, self.maxother_inner, self.maxother_outer)

    def _repr_obj(self, obj, level, limit_inner, limit_outer):
        try:
            if self.raw_value:
                # For raw value retrieval, ignore all limits.
                if isinstance(obj, bytes):
                    yield obj.decode("latin-1")
                    return

                try:
                    mv = memoryview(obj)
                except Exception:
                    yield self._convert_to_unicode_or_bytes_repr(repr(obj))
                    return
                else:
                    # Map bytes to Unicode codepoints with same values.
                    yield mv.tobytes().decode("latin-1")
                    return
            elif self.convert_to_hex and isinstance(obj, self.int_types):
                obj_repr = hex(obj)
            else:
                obj_repr = repr(obj)
        except Exception:
            try:
                obj_repr = object.__repr__(obj)
            except Exception:
                try:
                    obj_repr = "<no repr available for " + type(obj).__name__ + ">"  # noqa
                except Exception:
                    obj_repr = "<no repr available for object>"

        limit = limit_inner if level > 0 else limit_outer

        if limit >= len(obj_repr):
            yield self._convert_to_unicode_or_bytes_repr(obj_repr)
            return

        # Slightly imprecise calculations - we may end up with a string that is
        # up to 3 characters longer than limit. If you need precise formatting,
        # you are using the wrong class.
        left_count, right_count = max(1, int(2 * limit / 3)), max(1, int(limit / 3))  # noqa

        yield obj_repr[:left_count]
        yield "..."
        yield obj_repr[-right_count:]

    def _convert_to_unicode_or_bytes_repr(self, obj_repr):
        return obj_repr

    def _bytes_as_unicode_if_possible(self, obj_repr):
        # We try to decode with 3 possible encoding (sys.stdout.encoding,
        # locale.getpreferredencoding() and 'utf-8). If no encoding can decode
        # the input, we return the original bytes.
        try_encodings = []
        encoding = self.sys_stdout_encoding or getattr(sys.stdout, "encoding", "")
        if encoding:
            try_encodings.append(encoding.lower())

        preferred_encoding = self.locale_preferred_encoding or locale.getpreferredencoding()
        if preferred_encoding:
            preferred_encoding = preferred_encoding.lower()
            if preferred_encoding not in try_encodings:
                try_encodings.append(preferred_encoding)

        if "utf-8" not in try_encodings:
            try_encodings.append("utf-8")

        for encoding in try_encodings:
            try:
                return obj_repr.decode(encoding)
            except UnicodeDecodeError:
                pass

        return obj_repr  # Return the original version (in bytes)

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\ftp.py ===
import os
import sys
import uuid
import warnings
from ftplib import FTP, FTP_TLS, Error, error_perm
from typing import Any

from ..spec import AbstractBufferedFile, AbstractFileSystem
from ..utils import infer_storage_options, isfilelike


class FTPFileSystem(AbstractFileSystem):
    """A filesystem over classic FTP"""

    root_marker = "/"
    cachable = False
    protocol = "ftp"

    def __init__(
        self,
        host,
        port=21,
        username=None,
        password=None,
        acct=None,
        block_size=None,
        tempdir=None,
        timeout=30,
        encoding="utf-8",
        tls=False,
        **kwargs,
    ):
        """
        You can use _get_kwargs_from_urls to get some kwargs from
        a reasonable FTP url.

        Authentication will be anonymous if username/password are not
        given.

        Parameters
        ----------
        host: str
            The remote server name/ip to connect to
        port: int
            Port to connect with
        username: str or None
            If authenticating, the user's identifier
        password: str of None
            User's password on the server, if using
        acct: str or None
            Some servers also need an "account" string for auth
        block_size: int or None
            If given, the read-ahead or write buffer size.
        tempdir: str
            Directory on remote to put temporary files when in a transaction
        timeout: int
            Timeout of the ftp connection in seconds
        encoding: str
            Encoding to use for directories and filenames in FTP connection
        tls: bool
            Use FTP-TLS, by default False
        """
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.tempdir = tempdir or "/tmp"
        self.cred = username or "", password or "", acct or ""
        self.timeout = timeout
        self.encoding = encoding
        if block_size is not None:
            self.blocksize = block_size
        else:
            self.blocksize = 2**16
        self.tls = tls
        self._connect()
        if self.tls:
            self.ftp.prot_p()

    def _connect(self):
        if self.tls:
            ftp_cls = FTP_TLS
        else:
            ftp_cls = FTP
        if sys.version_info >= (3, 9):
            self.ftp = ftp_cls(timeout=self.timeout, encoding=self.encoding)
        elif self.encoding:
            warnings.warn("`encoding` not supported for python<3.9, ignoring")
            self.ftp = ftp_cls(timeout=self.timeout)
        else:
            self.ftp = ftp_cls(timeout=self.timeout)
        self.ftp.connect(self.host, self.port)
        self.ftp.login(*self.cred)

    @classmethod
    def _strip_protocol(cls, path):
        return "/" + infer_storage_options(path)["path"].lstrip("/").rstrip("/")

    @staticmethod
    def _get_kwargs_from_urls(urlpath):
        out = infer_storage_options(urlpath)
        out.pop("path", None)
        out.pop("protocol", None)
        return out

    def ls(self, path, detail=True, **kwargs):
        path = self._strip_protocol(path)
        out = []
        if path not in self.dircache:
            try:
                try:
                    out = [
                        (fn, details)
                        for (fn, details) in self.ftp.mlsd(path)
                        if fn not in [".", ".."]
                        and details["type"] not in ["pdir", "cdir"]
                    ]
                except error_perm:
                    out = _mlsd2(self.ftp, path)  # Not platform independent
                for fn, details in out:
                    details["name"] = "/".join(
                        ["" if path == "/" else path, fn.lstrip("/")]
                    )
                    if details["type"] == "file":
                        details["size"] = int(details["size"])
                    else:
                        details["size"] = 0
                    if details["type"] == "dir":
                        details["type"] = "directory"
                self.dircache[path] = out
            except Error:
                try:
                    info = self.info(path)
                    if info["type"] == "file":
                        out = [(path, info)]
                except (Error, IndexError) as exc:
                    raise FileNotFoundError(path) from exc
        files = self.dircache.get(path, out)
        if not detail:
            return sorted([fn for fn, details in files])
        return [details for fn, details in files]

    def info(self, path, **kwargs):
        # implement with direct method
        path = self._strip_protocol(path)
        if path == "/":
            # special case, since this dir has no real entry
            return {"name": "/", "size": 0, "type": "directory"}
        files = self.ls(self._parent(path).lstrip("/"), True)
        try:
            out = next(f for f in files if f["name"] == path)
        except StopIteration as exc:
            raise FileNotFoundError(path) from exc
        return out

    def get_file(self, rpath, lpath, **kwargs):
        if self.isdir(rpath):
            if not os.path.exists(lpath):
                os.mkdir(lpath)
            return
        if isfilelike(lpath):
            outfile = lpath
        else:
            outfile = open(lpath, "wb")

        def cb(x):
            outfile.write(x)

        self.ftp.retrbinary(
            f"RETR {rpath}",
            blocksize=self.blocksize,
            callback=cb,
        )
        if not isfilelike(lpath):
            outfile.close()

    def cat_file(self, path, start=None, end=None, **kwargs):
        if end is not None:
            return super().cat_file(path, start, end, **kwargs)
        out = []

        def cb(x):
            out.append(x)

        try:
            self.ftp.retrbinary(
                f"RETR {path}",
                blocksize=self.blocksize,
                rest=start,
                callback=cb,
            )
        except (Error, error_perm) as orig_exc:
            raise FileNotFoundError(path) from orig_exc
        return b"".join(out)

    def _open(
        self,
        path,
        mode="rb",
        block_size=None,
        cache_options=None,
        autocommit=True,
        **kwargs,
    ):
        path = self._strip_protocol(path)
        block_size = block_size or self.blocksize
        return FTPFile(
            self,
            path,
            mode=mode,
            block_size=block_size,
            tempdir=self.tempdir,
            autocommit=autocommit,
            cache_options=cache_options,
        )

    def _rm(self, path):
        path = self._strip_protocol(path)
        self.ftp.delete(path)
        self.invalidate_cache(self._parent(path))

    def rm(self, path, recursive=False, maxdepth=None):
        paths = self.expand_path(path, recursive=recursive, maxdepth=maxdepth)
        for p in reversed(paths):
            if self.isfile(p):
                self.rm_file(p)
            else:
                self.rmdir(p)

    def mkdir(self, path: str, create_parents: bool = True, **kwargs: Any) -> None:
        path = self._strip_protocol(path)
        parent = self._parent(path)
        if parent != self.root_marker and not self.exists(parent) and create_parents:
            self.mkdir(parent, create_parents=create_parents)

        self.ftp.mkd(path)
        self.invalidate_cache(self._parent(path))

    def makedirs(self, path: str, exist_ok: bool = False) -> None:
        path = self._strip_protocol(path)
        if self.exists(path):
            # NB: "/" does not "exist" as it has no directory entry
            if not exist_ok:
                raise FileExistsError(f"{path} exists without `exist_ok`")
            # exists_ok=True -> no-op
        else:
            self.mkdir(path, create_parents=True)

    def rmdir(self, path):
        path = self._strip_protocol(path)
        self.ftp.rmd(path)
        self.invalidate_cache(self._parent(path))

    def mv(self, path1, path2, **kwargs):
        path1 = self._strip_protocol(path1)
        path2 = self._strip_protocol(path2)
        self.ftp.rename(path1, path2)
        self.invalidate_cache(self._parent(path1))
        self.invalidate_cache(self._parent(path2))

    def __del__(self):
        self.ftp.close()

    def invalidate_cache(self, path=None):
        if path is None:
            self.dircache.clear()
        else:
            self.dircache.pop(path, None)
        super().invalidate_cache(path)


class TransferDone(Exception):
    """Internal exception to break out of transfer"""

    pass


class FTPFile(AbstractBufferedFile):
    """Interact with a remote FTP file with read/write buffering"""

    def __init__(
        self,
        fs,
        path,
        mode="rb",
        block_size="default",
        autocommit=True,
        cache_type="readahead",
        cache_options=None,
        **kwargs,
    ):
        super().__init__(
            fs,
            path,
            mode=mode,
            block_size=block_size,
            autocommit=autocommit,
            cache_type=cache_type,
            cache_options=cache_options,
            **kwargs,
        )
        if not autocommit:
            self.target = self.path
            self.path = "/".join([kwargs["tempdir"], str(uuid.uuid4())])

    def commit(self):
        self.fs.mv(self.path, self.target)

    def discard(self):
        self.fs.rm(self.path)

    def _fetch_range(self, start, end):
        """Get bytes between given byte limits

        Implemented by raising an exception in the fetch callback when the
        number of bytes received reaches the requested amount.

        Will fail if the server does not respect the REST command on
        retrieve requests.
        """
        out = []
        total = [0]

        def callback(x):
            total[0] += len(x)
            if total[0] > end - start:
                out.append(x[: (end - start) - total[0]])
                if end < self.size:
                    raise TransferDone
            else:
                out.append(x)

            if total[0] == end - start and end < self.size:
                raise TransferDone

        try:
            self.fs.ftp.retrbinary(
                f"RETR {self.path}",
                blocksize=self.blocksize,
                rest=start,
                callback=callback,
            )
        except TransferDone:
            try:
                # stop transfer, we got enough bytes for this block
                self.fs.ftp.abort()
                self.fs.ftp.getmultiline()
            except Error:
                self.fs._connect()

        return b"".join(out)

    def _upload_chunk(self, final=False):
        self.buffer.seek(0)
        self.fs.ftp.storbinary(
            f"STOR {self.path}", self.buffer, blocksize=self.blocksize, rest=self.offset
        )
        return True


def _mlsd2(ftp, path="."):
    """
    Fall back to using `dir` instead of `mlsd` if not supported.

    This parses a Linux style `ls -l` response to `dir`, but the response may
    be platform dependent.

    Parameters
    ----------
    ftp: ftplib.FTP
    path: str
        Expects to be given path, but defaults to ".".
    """
    lines = []
    minfo = []
    ftp.dir(path, lines.append)
    for line in lines:
        split_line = line.split()
        if len(split_line) < 9:
            continue
        this = (
            split_line[-1],
            {
                "modify": " ".join(split_line[5:8]),
                "unix.owner": split_line[2],
                "unix.group": split_line[3],
                "unix.mode": split_line[0],
                "size": split_line[4],
            },
        )
        if this[1]["unix.mode"][0] == "d":
            this[1]["type"] = "dir"
        else:
            this[1]["type"] = "file"
        minfo.append(this)
    return minfo

# === NexusCore/openenv\Lib\site-packages\nltk\sem\hole.py ===
# Natural Language Toolkit: Logic
#
# Author:     Peter Wang
# Updated by: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
An implementation of the Hole Semantics model, following Blackburn and Bos,
Representation and Inference for Natural Language (CSLI, 2005).

The semantic representations are built by the grammar hole.fcfg.
This module contains driver code to read in sentences and parse them
according to a hole semantics grammar.

After parsing, the semantic representation is in the form of an underspecified
representation that is not easy to read.  We use a "plugging" algorithm to
convert that representation into first-order logic formulas.
"""

from functools import reduce

from nltk.parse import load_parser
from nltk.sem.logic import (
    AllExpression,
    AndExpression,
    ApplicationExpression,
    ExistsExpression,
    IffExpression,
    ImpExpression,
    LambdaExpression,
    NegatedExpression,
    OrExpression,
)
from nltk.sem.skolemize import skolemize

# Note that in this code there may be multiple types of trees being referred to:
#
# 1. parse trees
# 2. the underspecified representation
# 3. first-order logic formula trees
# 4. the search space when plugging (search tree)
#


class Constants:
    ALL = "ALL"
    EXISTS = "EXISTS"
    NOT = "NOT"
    AND = "AND"
    OR = "OR"
    IMP = "IMP"
    IFF = "IFF"
    PRED = "PRED"
    LEQ = "LEQ"
    HOLE = "HOLE"
    LABEL = "LABEL"

    MAP = {
        ALL: lambda v, e: AllExpression(v.variable, e),
        EXISTS: lambda v, e: ExistsExpression(v.variable, e),
        NOT: NegatedExpression,
        AND: AndExpression,
        OR: OrExpression,
        IMP: ImpExpression,
        IFF: IffExpression,
        PRED: ApplicationExpression,
    }


class HoleSemantics:
    """
    This class holds the broken-down components of a hole semantics, i.e. it
    extracts the holes, labels, logic formula fragments and constraints out of
    a big conjunction of such as produced by the hole semantics grammar.  It
    then provides some operations on the semantics dealing with holes, labels
    and finding legal ways to plug holes with labels.
    """

    def __init__(self, usr):
        """
        Constructor.  `usr' is a ``sem.Expression`` representing an
        Underspecified Representation Structure (USR).  A USR has the following
        special predicates:
        ALL(l,v,n),
        EXISTS(l,v,n),
        AND(l,n,n),
        OR(l,n,n),
        IMP(l,n,n),
        IFF(l,n,n),
        PRED(l,v,n,v[,v]*) where the brackets and star indicate zero or more repetitions,
        LEQ(n,n),
        HOLE(n),
        LABEL(n)
        where l is the label of the node described by the predicate, n is either
        a label or a hole, and v is a variable.
        """
        self.holes = set()
        self.labels = set()
        self.fragments = {}  # mapping of label -> formula fragment
        self.constraints = set()  # set of Constraints
        self._break_down(usr)
        self.top_most_labels = self._find_top_most_labels()
        self.top_hole = self._find_top_hole()

    def is_node(self, x):
        """
        Return true if x is a node (label or hole) in this semantic
        representation.
        """
        return x in (self.labels | self.holes)

    def _break_down(self, usr):
        """
        Extract holes, labels, formula fragments and constraints from the hole
        semantics underspecified representation (USR).
        """
        if isinstance(usr, AndExpression):
            self._break_down(usr.first)
            self._break_down(usr.second)
        elif isinstance(usr, ApplicationExpression):
            func, args = usr.uncurry()
            if func.variable.name == Constants.LEQ:
                self.constraints.add(Constraint(args[0], args[1]))
            elif func.variable.name == Constants.HOLE:
                self.holes.add(args[0])
            elif func.variable.name == Constants.LABEL:
                self.labels.add(args[0])
            else:
                label = args[0]
                assert label not in self.fragments
                self.fragments[label] = (func, args[1:])
        else:
            raise ValueError(usr.label())

    def _find_top_nodes(self, node_list):
        top_nodes = node_list.copy()
        for f in self.fragments.values():
            # the label is the first argument of the predicate
            args = f[1]
            for arg in args:
                if arg in node_list:
                    top_nodes.discard(arg)
        return top_nodes

    def _find_top_most_labels(self):
        """
        Return the set of labels which are not referenced directly as part of
        another formula fragment.  These will be the top-most labels for the
        subtree that they are part of.
        """
        return self._find_top_nodes(self.labels)

    def _find_top_hole(self):
        """
        Return the hole that will be the top of the formula tree.
        """
        top_holes = self._find_top_nodes(self.holes)
        assert len(top_holes) == 1  # it must be unique
        return top_holes.pop()

    def pluggings(self):
        """
        Calculate and return all the legal pluggings (mappings of labels to
        holes) of this semantics given the constraints.
        """
        record = []
        self._plug_nodes([(self.top_hole, [])], self.top_most_labels, {}, record)
        return record

    def _plug_nodes(self, queue, potential_labels, plug_acc, record):
        """
        Plug the nodes in `queue' with the labels in `potential_labels'.

        Each element of `queue' is a tuple of the node to plug and the list of
        ancestor holes from the root of the graph to that node.

        `potential_labels' is a set of the labels which are still available for
        plugging.

        `plug_acc' is the incomplete mapping of holes to labels made on the
        current branch of the search tree so far.

        `record' is a list of all the complete pluggings that we have found in
        total so far.  It is the only parameter that is destructively updated.
        """
        if queue != []:
            (node, ancestors) = queue[0]
            if node in self.holes:
                # The node is a hole, try to plug it.
                self._plug_hole(
                    node, ancestors, queue[1:], potential_labels, plug_acc, record
                )
            else:
                assert node in self.labels
                # The node is a label.  Replace it in the queue by the holes and
                # labels in the formula fragment named by that label.
                args = self.fragments[node][1]
                head = [(a, ancestors) for a in args if self.is_node(a)]
                self._plug_nodes(head + queue[1:], potential_labels, plug_acc, record)
        else:
            raise Exception("queue empty")

    def _plug_hole(self, hole, ancestors0, queue, potential_labels0, plug_acc0, record):
        """
        Try all possible ways of plugging a single hole.
        See _plug_nodes for the meanings of the parameters.
        """
        # Add the current hole we're trying to plug into the list of ancestors.
        assert hole not in ancestors0
        ancestors = [hole] + ancestors0

        # Try each potential label in this hole in turn.
        for l in potential_labels0:
            # Is the label valid in this hole?
            if self._violates_constraints(l, ancestors):
                continue

            plug_acc = plug_acc0.copy()
            plug_acc[hole] = l
            potential_labels = potential_labels0.copy()
            potential_labels.remove(l)

            if len(potential_labels) == 0:
                # No more potential labels.  That must mean all the holes have
                # been filled so we have found a legal plugging so remember it.
                #
                # Note that the queue might not be empty because there might
                # be labels on there that point to formula fragments with
                # no holes in them.  _sanity_check_plugging will make sure
                # all holes are filled.
                self._sanity_check_plugging(plug_acc, self.top_hole, [])
                record.append(plug_acc)
            else:
                # Recursively try to fill in the rest of the holes in the
                # queue.  The label we just plugged into the hole could have
                # holes of its own so at the end of the queue.  Putting it on
                # the end of the queue gives us a breadth-first search, so that
                # all the holes at level i of the formula tree are filled
                # before filling level i+1.
                # A depth-first search would work as well since the trees must
                # be finite but the bookkeeping would be harder.
                self._plug_nodes(
                    queue + [(l, ancestors)], potential_labels, plug_acc, record
                )

    def _violates_constraints(self, label, ancestors):
        """
        Return True if the `label' cannot be placed underneath the holes given
        by the set `ancestors' because it would violate the constraints imposed
        on it.
        """
        for c in self.constraints:
            if c.lhs == label:
                if c.rhs not in ancestors:
                    return True
        return False

    def _sanity_check_plugging(self, plugging, node, ancestors):
        """
        Make sure that a given plugging is legal.  We recursively go through
        each node and make sure that no constraints are violated.
        We also check that all holes have been filled.
        """
        if node in self.holes:
            ancestors = [node] + ancestors
            label = plugging[node]
        else:
            label = node
        assert label in self.labels
        for c in self.constraints:
            if c.lhs == label:
                assert c.rhs in ancestors
        args = self.fragments[label][1]
        for arg in args:
            if self.is_node(arg):
                self._sanity_check_plugging(plugging, arg, [label] + ancestors)

    def formula_tree(self, plugging):
        """
        Return the first-order logic formula tree for this underspecified
        representation using the plugging given.
        """
        return self._formula_tree(plugging, self.top_hole)

    def _formula_tree(self, plugging, node):
        if node in plugging:
            return self._formula_tree(plugging, plugging[node])
        elif node in self.fragments:
            pred, args = self.fragments[node]
            children = [self._formula_tree(plugging, arg) for arg in args]
            return reduce(Constants.MAP[pred.variable.name], children)
        else:
            return node


class Constraint:
    """
    This class represents a constraint of the form (L =< N),
    where L is a label and N is a node (a label or a hole).
    """

    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __eq__(self, other):
        if self.__class__ == other.__class__:
            return self.lhs == other.lhs and self.rhs == other.rhs
        else:
            return False

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(repr(self))

    def __repr__(self):
        return f"({self.lhs} < {self.rhs})"


def hole_readings(sentence, grammar_filename=None, verbose=False):
    if not grammar_filename:
        grammar_filename = "grammars/sample_grammars/hole.fcfg"

    if verbose:
        print("Reading grammar file", grammar_filename)

    parser = load_parser(grammar_filename)

    # Parse the sentence.
    tokens = sentence.split()
    trees = list(parser.parse(tokens))
    if verbose:
        print("Got %d different parses" % len(trees))

    all_readings = []
    for tree in trees:
        # Get the semantic feature from the top of the parse tree.
        sem = tree.label()["SEM"].simplify()

        # Print the raw semantic representation.
        if verbose:
            print("Raw:       ", sem)

        # Skolemize away all quantifiers.  All variables become unique.
        while isinstance(sem, LambdaExpression):
            sem = sem.term
        skolemized = skolemize(sem)

        if verbose:
            print("Skolemized:", skolemized)

        # Break the hole semantics representation down into its components
        # i.e. holes, labels, formula fragments and constraints.
        hole_sem = HoleSemantics(skolemized)

        # Maybe show the details of the semantic representation.
        if verbose:
            print("Holes:       ", hole_sem.holes)
            print("Labels:      ", hole_sem.labels)
            print("Constraints: ", hole_sem.constraints)
            print("Top hole:    ", hole_sem.top_hole)
            print("Top labels:  ", hole_sem.top_most_labels)
            print("Fragments:")
            for l, f in hole_sem.fragments.items():
                print(f"\t{l}: {f}")

        # Find all the possible ways to plug the formulas together.
        pluggings = hole_sem.pluggings()

        # Build FOL formula trees using the pluggings.
        readings = list(map(hole_sem.formula_tree, pluggings))

        # Print out the formulas in a textual format.
        if verbose:
            for i, r in enumerate(readings):
                print()
                print("%d. %s" % (i, r))
            print()

        all_readings.extend(readings)

    return all_readings


if __name__ == "__main__":
    for r in hole_readings("a dog barks"):
        print(r)
    print()
    for r in hole_readings("every girl chases a dog"):
        print(r)

# === NexusCore/openenv\Lib\site-packages\nltk\stem\isri.py ===
#
# Natural Language Toolkit: The ISRI Arabic Stemmer
#
# Copyright (C) 2001-2024 NLTK Project
# Algorithm: Kazem Taghva, Rania Elkhoury, and Jeffrey Coombs (2005)
# Author: Hosam Algasaier <hosam_hme@yahoo.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
ISRI Arabic Stemmer

The algorithm for this stemmer is described in:

Taghva, K., Elkoury, R., and Coombs, J. 2005. Arabic Stemming without a root dictionary.
Information Science Research Institute. University of Nevada, Las Vegas, USA.

The Information Science Research Institute’s (ISRI) Arabic stemmer shares many features
with the Khoja stemmer. However, the main difference is that ISRI stemmer does not use root
dictionary. Also, if a root is not found, ISRI stemmer returned normalized form, rather than
returning the original unmodified word.

Additional adjustments were made to improve the algorithm:

1- Adding 60 stop words.
2- Adding the pattern (تفاعيل) to ISRI pattern set.
3- The step 2 in the original algorithm was normalizing all hamza. This step is discarded because it
increases the word ambiguities and changes the original root.

"""
import re

from nltk.stem.api import StemmerI


class ISRIStemmer(StemmerI):
    """
    ISRI Arabic stemmer based on algorithm: Arabic Stemming without a root dictionary.
    Information Science Research Institute. University of Nevada, Las Vegas, USA.

    A few minor modifications have been made to ISRI basic algorithm.
    See the source code of this module for more information.

    isri.stem(token) returns Arabic root for the given token.

    The ISRI Stemmer requires that all tokens have Unicode string types.
    If you use Python IDLE on Arabic Windows you have to decode text first
    using Arabic '1256' coding.
    """

    def __init__(self):
        # length three prefixes
        self.p3 = [
            "\u0643\u0627\u0644",
            "\u0628\u0627\u0644",
            "\u0648\u0644\u0644",
            "\u0648\u0627\u0644",
        ]

        # length two prefixes
        self.p2 = ["\u0627\u0644", "\u0644\u0644"]

        # length one prefixes
        self.p1 = [
            "\u0644",
            "\u0628",
            "\u0641",
            "\u0633",
            "\u0648",
            "\u064a",
            "\u062a",
            "\u0646",
            "\u0627",
        ]

        # length three suffixes
        self.s3 = [
            "\u062a\u0645\u0644",
            "\u0647\u0645\u0644",
            "\u062a\u0627\u0646",
            "\u062a\u064a\u0646",
            "\u0643\u0645\u0644",
        ]

        # length two suffixes
        self.s2 = [
            "\u0648\u0646",
            "\u0627\u062a",
            "\u0627\u0646",
            "\u064a\u0646",
            "\u062a\u0646",
            "\u0643\u0645",
            "\u0647\u0646",
            "\u0646\u0627",
            "\u064a\u0627",
            "\u0647\u0627",
            "\u062a\u0645",
            "\u0643\u0646",
            "\u0646\u064a",
            "\u0648\u0627",
            "\u0645\u0627",
            "\u0647\u0645",
        ]

        # length one suffixes
        self.s1 = ["\u0629", "\u0647", "\u064a", "\u0643", "\u062a", "\u0627", "\u0646"]

        # groups of length four patterns
        self.pr4 = {
            0: ["\u0645"],
            1: ["\u0627"],
            2: ["\u0627", "\u0648", "\u064A"],
            3: ["\u0629"],
        }

        # Groups of length five patterns and length three roots
        self.pr53 = {
            0: ["\u0627", "\u062a"],
            1: ["\u0627", "\u064a", "\u0648"],
            2: ["\u0627", "\u062a", "\u0645"],
            3: ["\u0645", "\u064a", "\u062a"],
            4: ["\u0645", "\u062a"],
            5: ["\u0627", "\u0648"],
            6: ["\u0627", "\u0645"],
        }

        self.re_short_vowels = re.compile(r"[\u064B-\u0652]")
        self.re_hamza = re.compile(r"[\u0621\u0624\u0626]")
        self.re_initial_hamza = re.compile(r"^[\u0622\u0623\u0625]")

        self.stop_words = [
            "\u064a\u0643\u0648\u0646",
            "\u0648\u0644\u064a\u0633",
            "\u0648\u0643\u0627\u0646",
            "\u0643\u0630\u0644\u0643",
            "\u0627\u0644\u062a\u064a",
            "\u0648\u0628\u064a\u0646",
            "\u0639\u0644\u064a\u0647\u0627",
            "\u0645\u0633\u0627\u0621",
            "\u0627\u0644\u0630\u064a",
            "\u0648\u0643\u0627\u0646\u062a",
            "\u0648\u0644\u0643\u0646",
            "\u0648\u0627\u0644\u062a\u064a",
            "\u062a\u0643\u0648\u0646",
            "\u0627\u0644\u064a\u0648\u0645",
            "\u0627\u0644\u0644\u0630\u064a\u0646",
            "\u0639\u0644\u064a\u0647",
            "\u0643\u0627\u0646\u062a",
            "\u0644\u0630\u0644\u0643",
            "\u0623\u0645\u0627\u0645",
            "\u0647\u0646\u0627\u0643",
            "\u0645\u0646\u0647\u0627",
            "\u0645\u0627\u0632\u0627\u0644",
            "\u0644\u0627\u0632\u0627\u0644",
            "\u0644\u0627\u064a\u0632\u0627\u0644",
            "\u0645\u0627\u064a\u0632\u0627\u0644",
            "\u0627\u0635\u0628\u062d",
            "\u0623\u0635\u0628\u062d",
            "\u0623\u0645\u0633\u0649",
            "\u0627\u0645\u0633\u0649",
            "\u0623\u0636\u062d\u0649",
            "\u0627\u0636\u062d\u0649",
            "\u0645\u0627\u0628\u0631\u062d",
            "\u0645\u0627\u0641\u062a\u0626",
            "\u0645\u0627\u0627\u0646\u0641\u0643",
            "\u0644\u0627\u0633\u064a\u0645\u0627",
            "\u0648\u0644\u0627\u064a\u0632\u0627\u0644",
            "\u0627\u0644\u062d\u0627\u0644\u064a",
            "\u0627\u0644\u064a\u0647\u0627",
            "\u0627\u0644\u0630\u064a\u0646",
            "\u0641\u0627\u0646\u0647",
            "\u0648\u0627\u0644\u0630\u064a",
            "\u0648\u0647\u0630\u0627",
            "\u0644\u0647\u0630\u0627",
            "\u0641\u0643\u0627\u0646",
            "\u0633\u062a\u0643\u0648\u0646",
            "\u0627\u0644\u064a\u0647",
            "\u064a\u0645\u0643\u0646",
            "\u0628\u0647\u0630\u0627",
            "\u0627\u0644\u0630\u0649",
        ]

    def stem(self, token):
        """
        Stemming a word token using the ISRI stemmer.
        """
        token = self.norm(
            token, 1
        )  # remove diacritics which representing Arabic short vowels
        if token in self.stop_words:
            return token  # exclude stop words from being processed
        token = self.pre32(
            token
        )  # remove length three and length two prefixes in this order
        token = self.suf32(
            token
        )  # remove length three and length two suffixes in this order
        token = self.waw(
            token
        )  # remove connective ‘و’ if it precedes a word beginning with ‘و’
        token = self.norm(token, 2)  # normalize initial hamza to bare alif
        # if 4 <= word length <= 7, then stem; otherwise, no stemming
        if len(token) == 4:  # length 4 word
            token = self.pro_w4(token)
        elif len(token) == 5:  # length 5 word
            token = self.pro_w53(token)
            token = self.end_w5(token)
        elif len(token) == 6:  # length 6 word
            token = self.pro_w6(token)
            token = self.end_w6(token)
        elif len(token) == 7:  # length 7 word
            token = self.suf1(token)
            if len(token) == 7:
                token = self.pre1(token)
            if len(token) == 6:
                token = self.pro_w6(token)
                token = self.end_w6(token)
        return token

    def norm(self, word, num=3):
        """
        normalization:
        num=1  normalize diacritics
        num=2  normalize initial hamza
        num=3  both 1&2
        """
        if num == 1:
            word = self.re_short_vowels.sub("", word)
        elif num == 2:
            word = self.re_initial_hamza.sub("\u0627", word)
        elif num == 3:
            word = self.re_short_vowels.sub("", word)
            word = self.re_initial_hamza.sub("\u0627", word)
        return word

    def pre32(self, word):
        """remove length three and length two prefixes in this order"""
        if len(word) >= 6:
            for pre3 in self.p3:
                if word.startswith(pre3):
                    return word[3:]
        if len(word) >= 5:
            for pre2 in self.p2:
                if word.startswith(pre2):
                    return word[2:]
        return word

    def suf32(self, word):
        """remove length three and length two suffixes in this order"""
        if len(word) >= 6:
            for suf3 in self.s3:
                if word.endswith(suf3):
                    return word[:-3]
        if len(word) >= 5:
            for suf2 in self.s2:
                if word.endswith(suf2):
                    return word[:-2]
        return word

    def waw(self, word):
        """remove connective ‘و’ if it precedes a word beginning with ‘و’"""
        if len(word) >= 4 and word[:2] == "\u0648\u0648":
            word = word[1:]
        return word

    def pro_w4(self, word):
        """process length four patterns and extract length three roots"""
        if word[0] in self.pr4[0]:  # مفعل
            word = word[1:]
        elif word[1] in self.pr4[1]:  # فاعل
            word = word[:1] + word[2:]
        elif word[2] in self.pr4[2]:  # فعال - فعول - فعيل
            word = word[:2] + word[3]
        elif word[3] in self.pr4[3]:  # فعلة
            word = word[:-1]
        else:
            word = self.suf1(word)  # do - normalize short sufix
            if len(word) == 4:
                word = self.pre1(word)  # do - normalize short prefix
        return word

    def pro_w53(self, word):
        """process length five patterns and extract length three roots"""
        if word[2] in self.pr53[0] and word[0] == "\u0627":  # افتعل - افاعل
            word = word[1] + word[3:]
        elif word[3] in self.pr53[1] and word[0] == "\u0645":  # مفعول - مفعال - مفعيل
            word = word[1:3] + word[4]
        elif word[0] in self.pr53[2] and word[4] == "\u0629":  # مفعلة - تفعلة - افعلة
            word = word[1:4]
        elif word[0] in self.pr53[3] and word[2] == "\u062a":  # مفتعل - يفتعل - تفتعل
            word = word[1] + word[3:]
        elif word[0] in self.pr53[4] and word[2] == "\u0627":  # مفاعل - تفاعل
            word = word[1] + word[3:]
        elif word[2] in self.pr53[5] and word[4] == "\u0629":  # فعولة - فعالة
            word = word[:2] + word[3]
        elif word[0] in self.pr53[6] and word[1] == "\u0646":  # انفعل - منفعل
            word = word[2:]
        elif word[3] == "\u0627" and word[0] == "\u0627":  # افعال
            word = word[1:3] + word[4]
        elif word[4] == "\u0646" and word[3] == "\u0627":  # فعلان
            word = word[:3]
        elif word[3] == "\u064a" and word[0] == "\u062a":  # تفعيل
            word = word[1:3] + word[4]
        elif word[3] == "\u0648" and word[1] == "\u0627":  # فاعول
            word = word[0] + word[2] + word[4]
        elif word[2] == "\u0627" and word[1] == "\u0648":  # فواعل
            word = word[0] + word[3:]
        elif word[3] == "\u0626" and word[2] == "\u0627":  # فعائل
            word = word[:2] + word[4]
        elif word[4] == "\u0629" and word[1] == "\u0627":  # فاعلة
            word = word[0] + word[2:4]
        elif word[4] == "\u064a" and word[2] == "\u0627":  # فعالي
            word = word[:2] + word[3]
        else:
            word = self.suf1(word)  # do - normalize short sufix
            if len(word) == 5:
                word = self.pre1(word)  # do - normalize short prefix
        return word

    def pro_w54(self, word):
        """process length five patterns and extract length four roots"""
        if word[0] in self.pr53[2]:  # تفعلل - افعلل - مفعلل
            word = word[1:]
        elif word[4] == "\u0629":  # فعللة
            word = word[:4]
        elif word[2] == "\u0627":  # فعالل
            word = word[:2] + word[3:]
        return word

    def end_w5(self, word):
        """ending step (word of length five)"""
        if len(word) == 4:
            word = self.pro_w4(word)
        elif len(word) == 5:
            word = self.pro_w54(word)
        return word

    def pro_w6(self, word):
        """process length six patterns and extract length three roots"""
        if word.startswith("\u0627\u0633\u062a") or word.startswith(
            "\u0645\u0633\u062a"
        ):  # مستفعل - استفعل
            word = word[3:]
        elif (
            word[0] == "\u0645" and word[3] == "\u0627" and word[5] == "\u0629"
        ):  # مفعالة
            word = word[1:3] + word[4]
        elif (
            word[0] == "\u0627" and word[2] == "\u062a" and word[4] == "\u0627"
        ):  # افتعال
            word = word[1] + word[3] + word[5]
        elif (
            word[0] == "\u0627" and word[3] == "\u0648" and word[2] == word[4]
        ):  # افعوعل
            word = word[1] + word[4:]
        elif (
            word[0] == "\u062a" and word[2] == "\u0627" and word[4] == "\u064a"
        ):  # تفاعيل   new pattern
            word = word[1] + word[3] + word[5]
        else:
            word = self.suf1(word)  # do - normalize short sufix
            if len(word) == 6:
                word = self.pre1(word)  # do - normalize short prefix
        return word

    def pro_w64(self, word):
        """process length six patterns and extract length four roots"""
        if word[0] == "\u0627" and word[4] == "\u0627":  # افعلال
            word = word[1:4] + word[5]
        elif word.startswith("\u0645\u062a"):  # متفعلل
            word = word[2:]
        return word

    def end_w6(self, word):
        """ending step (word of length six)"""
        if len(word) == 5:
            word = self.pro_w53(word)
            word = self.end_w5(word)
        elif len(word) == 6:
            word = self.pro_w64(word)
        return word

    def suf1(self, word):
        """normalize short sufix"""
        for sf1 in self.s1:
            if word.endswith(sf1):
                return word[:-1]
        return word

    def pre1(self, word):
        """normalize short prefix"""
        for sp1 in self.p1:
            if word.startswith(sp1):
                return word[1:]
        return word

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\heap_profiler.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: HeapProfiler (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import runtime


class HeapSnapshotObjectId(str):
    '''
    Heap snapshot object id.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> HeapSnapshotObjectId:
        return cls(json)

    def __repr__(self):
        return 'HeapSnapshotObjectId({})'.format(super().__repr__())


@dataclass
class SamplingHeapProfileNode:
    '''
    Sampling Heap Profile node. Holds callsite information, allocation statistics and child nodes.
    '''
    #: Function location.
    call_frame: runtime.CallFrame

    #: Allocations size in bytes for the node excluding children.
    self_size: float

    #: Node id. Ids are unique across all profiles collected between startSampling and stopSampling.
    id_: int

    #: Child nodes.
    children: typing.List[SamplingHeapProfileNode]

    def to_json(self):
        json = dict()
        json['callFrame'] = self.call_frame.to_json()
        json['selfSize'] = self.self_size
        json['id'] = self.id_
        json['children'] = [i.to_json() for i in self.children]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            call_frame=runtime.CallFrame.from_json(json['callFrame']),
            self_size=float(json['selfSize']),
            id_=int(json['id']),
            children=[SamplingHeapProfileNode.from_json(i) for i in json['children']],
        )


@dataclass
class SamplingHeapProfileSample:
    '''
    A single sample from a sampling profile.
    '''
    #: Allocation size in bytes attributed to the sample.
    size: float

    #: Id of the corresponding profile tree node.
    node_id: int

    #: Time-ordered sample ordinal number. It is unique across all profiles retrieved
    #: between startSampling and stopSampling.
    ordinal: float

    def to_json(self):
        json = dict()
        json['size'] = self.size
        json['nodeId'] = self.node_id
        json['ordinal'] = self.ordinal
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            size=float(json['size']),
            node_id=int(json['nodeId']),
            ordinal=float(json['ordinal']),
        )


@dataclass
class SamplingHeapProfile:
    '''
    Sampling profile.
    '''
    head: SamplingHeapProfileNode

    samples: typing.List[SamplingHeapProfileSample]

    def to_json(self):
        json = dict()
        json['head'] = self.head.to_json()
        json['samples'] = [i.to_json() for i in self.samples]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            head=SamplingHeapProfileNode.from_json(json['head']),
            samples=[SamplingHeapProfileSample.from_json(i) for i in json['samples']],
        )


def add_inspected_heap_object(
        heap_object_id: HeapSnapshotObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables console to refer to the node with given id via $x (see Command Line API for more details
    $x functions).

    :param heap_object_id: Heap snapshot object id to be accessible by means of $x command line API.
    '''
    params: T_JSON_DICT = dict()
    params['heapObjectId'] = heap_object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.addInspectedHeapObject',
        'params': params,
    }
    json = yield cmd_dict


def collect_garbage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.collectGarbage',
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.enable',
    }
    json = yield cmd_dict


def get_heap_object_id(
        object_id: runtime.RemoteObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,HeapSnapshotObjectId]:
    '''
    :param object_id: Identifier of the object to get heap object id for.
    :returns: Id of the heap snapshot object corresponding to the passed remote object id.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.getHeapObjectId',
        'params': params,
    }
    json = yield cmd_dict
    return HeapSnapshotObjectId.from_json(json['heapSnapshotObjectId'])


def get_object_by_heap_object_id(
        object_id: HeapSnapshotObjectId,
        object_group: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.RemoteObject]:
    '''
    :param object_id:
    :param object_group: *(Optional)* Symbolic group name that can be used to release multiple objects.
    :returns: Evaluation result.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    if object_group is not None:
        params['objectGroup'] = object_group
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.getObjectByHeapObjectId',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.RemoteObject.from_json(json['result'])


def get_sampling_profile() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SamplingHeapProfile]:
    '''


    :returns: Return the sampling profile being collected.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.getSamplingProfile',
    }
    json = yield cmd_dict
    return SamplingHeapProfile.from_json(json['profile'])


def start_sampling(
        sampling_interval: typing.Optional[float] = None,
        include_objects_collected_by_major_gc: typing.Optional[bool] = None,
        include_objects_collected_by_minor_gc: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param sampling_interval: *(Optional)* Average sample interval in bytes. Poisson distribution is used for the intervals. The default value is 32768 bytes.
    :param include_objects_collected_by_major_gc: *(Optional)* By default, the sampling heap profiler reports only objects which are still alive when the profile is returned via getSamplingProfile or stopSampling, which is useful for determining what functions contribute the most to steady-state memory usage. This flag instructs the sampling heap profiler to also include information about objects discarded by major GC, which will show which functions cause large temporary memory usage or long GC pauses.
    :param include_objects_collected_by_minor_gc: *(Optional)* By default, the sampling heap profiler reports only objects which are still alive when the profile is returned via getSamplingProfile or stopSampling, which is useful for determining what functions contribute the most to steady-state memory usage. This flag instructs the sampling heap profiler to also include information about objects discarded by minor GC, which is useful when tuning a latency-sensitive application for minimal GC activity.
    '''
    params: T_JSON_DICT = dict()
    if sampling_interval is not None:
        params['samplingInterval'] = sampling_interval
    if include_objects_collected_by_major_gc is not None:
        params['includeObjectsCollectedByMajorGC'] = include_objects_collected_by_major_gc
    if include_objects_collected_by_minor_gc is not None:
        params['includeObjectsCollectedByMinorGC'] = include_objects_collected_by_minor_gc
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.startSampling',
        'params': params,
    }
    json = yield cmd_dict


def start_tracking_heap_objects(
        track_allocations: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param track_allocations: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    if track_allocations is not None:
        params['trackAllocations'] = track_allocations
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.startTrackingHeapObjects',
        'params': params,
    }
    json = yield cmd_dict


def stop_sampling() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SamplingHeapProfile]:
    '''


    :returns: Recorded sampling heap profile.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.stopSampling',
    }
    json = yield cmd_dict
    return SamplingHeapProfile.from_json(json['profile'])


def stop_tracking_heap_objects(
        report_progress: typing.Optional[bool] = None,
        treat_global_objects_as_roots: typing.Optional[bool] = None,
        capture_numeric_value: typing.Optional[bool] = None,
        expose_internals: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param report_progress: *(Optional)* If true 'reportHeapSnapshotProgress' events will be generated while snapshot is being taken when the tracking is stopped.
    :param treat_global_objects_as_roots: *(Optional)* Deprecated in favor of ```exposeInternals```.
    :param capture_numeric_value: *(Optional)* If true, numerical values are included in the snapshot
    :param expose_internals: **(EXPERIMENTAL)** *(Optional)* If true, exposes internals of the snapshot.
    '''
    params: T_JSON_DICT = dict()
    if report_progress is not None:
        params['reportProgress'] = report_progress
    if treat_global_objects_as_roots is not None:
        params['treatGlobalObjectsAsRoots'] = treat_global_objects_as_roots
    if capture_numeric_value is not None:
        params['captureNumericValue'] = capture_numeric_value
    if expose_internals is not None:
        params['exposeInternals'] = expose_internals
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.stopTrackingHeapObjects',
        'params': params,
    }
    json = yield cmd_dict


def take_heap_snapshot(
        report_progress: typing.Optional[bool] = None,
        treat_global_objects_as_roots: typing.Optional[bool] = None,
        capture_numeric_value: typing.Optional[bool] = None,
        expose_internals: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param report_progress: *(Optional)* If true 'reportHeapSnapshotProgress' events will be generated while snapshot is being taken.
    :param treat_global_objects_as_roots: *(Optional)* If true, a raw snapshot without artificial roots will be generated. Deprecated in favor of ```exposeInternals```.
    :param capture_numeric_value: *(Optional)* If true, numerical values are included in the snapshot
    :param expose_internals: **(EXPERIMENTAL)** *(Optional)* If true, exposes internals of the snapshot.
    '''
    params: T_JSON_DICT = dict()
    if report_progress is not None:
        params['reportProgress'] = report_progress
    if treat_global_objects_as_roots is not None:
        params['treatGlobalObjectsAsRoots'] = treat_global_objects_as_roots
    if capture_numeric_value is not None:
        params['captureNumericValue'] = capture_numeric_value
    if expose_internals is not None:
        params['exposeInternals'] = expose_internals
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.takeHeapSnapshot',
        'params': params,
    }
    json = yield cmd_dict


@event_class('HeapProfiler.addHeapSnapshotChunk')
@dataclass
class AddHeapSnapshotChunk:
    chunk: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AddHeapSnapshotChunk:
        return cls(
            chunk=str(json['chunk'])
        )


@event_class('HeapProfiler.heapStatsUpdate')
@dataclass
class HeapStatsUpdate:
    '''
    If heap objects tracking has been started then backend may send update for one or more fragments
    '''
    #: An array of triplets. Each triplet describes a fragment. The first integer is the fragment
    #: index, the second integer is a total count of objects for the fragment, the third integer is
    #: a total size of the objects for the fragment.
    stats_update: typing.List[int]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> HeapStatsUpdate:
        return cls(
            stats_update=[int(i) for i in json['statsUpdate']]
        )


@event_class('HeapProfiler.lastSeenObjectId')
@dataclass
class LastSeenObjectId:
    '''
    If heap objects tracking has been started then backend regularly sends a current value for last
    seen object id and corresponding timestamp. If the were changes in the heap since last event
    then one or more heapStatsUpdate events will be sent before a new lastSeenObjectId event.
    '''
    last_seen_object_id: int
    timestamp: float

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LastSeenObjectId:
        return cls(
            last_seen_object_id=int(json['lastSeenObjectId']),
            timestamp=float(json['timestamp'])
        )


@event_class('HeapProfiler.reportHeapSnapshotProgress')
@dataclass
class ReportHeapSnapshotProgress:
    done: int
    total: int
    finished: typing.Optional[bool]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ReportHeapSnapshotProgress:
        return cls(
            done=int(json['done']),
            total=int(json['total']),
            finished=bool(json['finished']) if 'finished' in json else None
        )


@event_class('HeapProfiler.resetProfiles')
@dataclass
class ResetProfiles:


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ResetProfiles:
        return cls(

        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\heap_profiler.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: HeapProfiler (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import runtime


class HeapSnapshotObjectId(str):
    '''
    Heap snapshot object id.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> HeapSnapshotObjectId:
        return cls(json)

    def __repr__(self):
        return 'HeapSnapshotObjectId({})'.format(super().__repr__())


@dataclass
class SamplingHeapProfileNode:
    '''
    Sampling Heap Profile node. Holds callsite information, allocation statistics and child nodes.
    '''
    #: Function location.
    call_frame: runtime.CallFrame

    #: Allocations size in bytes for the node excluding children.
    self_size: float

    #: Node id. Ids are unique across all profiles collected between startSampling and stopSampling.
    id_: int

    #: Child nodes.
    children: typing.List[SamplingHeapProfileNode]

    def to_json(self):
        json = dict()
        json['callFrame'] = self.call_frame.to_json()
        json['selfSize'] = self.self_size
        json['id'] = self.id_
        json['children'] = [i.to_json() for i in self.children]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            call_frame=runtime.CallFrame.from_json(json['callFrame']),
            self_size=float(json['selfSize']),
            id_=int(json['id']),
            children=[SamplingHeapProfileNode.from_json(i) for i in json['children']],
        )


@dataclass
class SamplingHeapProfileSample:
    '''
    A single sample from a sampling profile.
    '''
    #: Allocation size in bytes attributed to the sample.
    size: float

    #: Id of the corresponding profile tree node.
    node_id: int

    #: Time-ordered sample ordinal number. It is unique across all profiles retrieved
    #: between startSampling and stopSampling.
    ordinal: float

    def to_json(self):
        json = dict()
        json['size'] = self.size
        json['nodeId'] = self.node_id
        json['ordinal'] = self.ordinal
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            size=float(json['size']),
            node_id=int(json['nodeId']),
            ordinal=float(json['ordinal']),
        )


@dataclass
class SamplingHeapProfile:
    '''
    Sampling profile.
    '''
    head: SamplingHeapProfileNode

    samples: typing.List[SamplingHeapProfileSample]

    def to_json(self):
        json = dict()
        json['head'] = self.head.to_json()
        json['samples'] = [i.to_json() for i in self.samples]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            head=SamplingHeapProfileNode.from_json(json['head']),
            samples=[SamplingHeapProfileSample.from_json(i) for i in json['samples']],
        )


def add_inspected_heap_object(
        heap_object_id: HeapSnapshotObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables console to refer to the node with given id via $x (see Command Line API for more details
    $x functions).

    :param heap_object_id: Heap snapshot object id to be accessible by means of $x command line API.
    '''
    params: T_JSON_DICT = dict()
    params['heapObjectId'] = heap_object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.addInspectedHeapObject',
        'params': params,
    }
    json = yield cmd_dict


def collect_garbage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.collectGarbage',
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.enable',
    }
    json = yield cmd_dict


def get_heap_object_id(
        object_id: runtime.RemoteObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,HeapSnapshotObjectId]:
    '''
    :param object_id: Identifier of the object to get heap object id for.
    :returns: Id of the heap snapshot object corresponding to the passed remote object id.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.getHeapObjectId',
        'params': params,
    }
    json = yield cmd_dict
    return HeapSnapshotObjectId.from_json(json['heapSnapshotObjectId'])


def get_object_by_heap_object_id(
        object_id: HeapSnapshotObjectId,
        object_group: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.RemoteObject]:
    '''
    :param object_id:
    :param object_group: *(Optional)* Symbolic group name that can be used to release multiple objects.
    :returns: Evaluation result.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    if object_group is not None:
        params['objectGroup'] = object_group
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.getObjectByHeapObjectId',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.RemoteObject.from_json(json['result'])


def get_sampling_profile() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SamplingHeapProfile]:
    '''


    :returns: Return the sampling profile being collected.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.getSamplingProfile',
    }
    json = yield cmd_dict
    return SamplingHeapProfile.from_json(json['profile'])


def start_sampling(
        sampling_interval: typing.Optional[float] = None,
        include_objects_collected_by_major_gc: typing.Optional[bool] = None,
        include_objects_collected_by_minor_gc: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param sampling_interval: *(Optional)* Average sample interval in bytes. Poisson distribution is used for the intervals. The default value is 32768 bytes.
    :param include_objects_collected_by_major_gc: *(Optional)* By default, the sampling heap profiler reports only objects which are still alive when the profile is returned via getSamplingProfile or stopSampling, which is useful for determining what functions contribute the most to steady-state memory usage. This flag instructs the sampling heap profiler to also include information about objects discarded by major GC, which will show which functions cause large temporary memory usage or long GC pauses.
    :param include_objects_collected_by_minor_gc: *(Optional)* By default, the sampling heap profiler reports only objects which are still alive when the profile is returned via getSamplingProfile or stopSampling, which is useful for determining what functions contribute the most to steady-state memory usage. This flag instructs the sampling heap profiler to also include information about objects discarded by minor GC, which is useful when tuning a latency-sensitive application for minimal GC activity.
    '''
    params: T_JSON_DICT = dict()
    if sampling_interval is not None:
        params['samplingInterval'] = sampling_interval
    if include_objects_collected_by_major_gc is not None:
        params['includeObjectsCollectedByMajorGC'] = include_objects_collected_by_major_gc
    if include_objects_collected_by_minor_gc is not None:
        params['includeObjectsCollectedByMinorGC'] = include_objects_collected_by_minor_gc
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.startSampling',
        'params': params,
    }
    json = yield cmd_dict


def start_tracking_heap_objects(
        track_allocations: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param track_allocations: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    if track_allocations is not None:
        params['trackAllocations'] = track_allocations
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.startTrackingHeapObjects',
        'params': params,
    }
    json = yield cmd_dict


def stop_sampling() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SamplingHeapProfile]:
    '''


    :returns: Recorded sampling heap profile.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.stopSampling',
    }
    json = yield cmd_dict
    return SamplingHeapProfile.from_json(json['profile'])


def stop_tracking_heap_objects(
        report_progress: typing.Optional[bool] = None,
        treat_global_objects_as_roots: typing.Optional[bool] = None,
        capture_numeric_value: typing.Optional[bool] = None,
        expose_internals: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param report_progress: *(Optional)* If true 'reportHeapSnapshotProgress' events will be generated while snapshot is being taken when the tracking is stopped.
    :param treat_global_objects_as_roots: *(Optional)* Deprecated in favor of ```exposeInternals```.
    :param capture_numeric_value: *(Optional)* If true, numerical values are included in the snapshot
    :param expose_internals: **(EXPERIMENTAL)** *(Optional)* If true, exposes internals of the snapshot.
    '''
    params: T_JSON_DICT = dict()
    if report_progress is not None:
        params['reportProgress'] = report_progress
    if treat_global_objects_as_roots is not None:
        params['treatGlobalObjectsAsRoots'] = treat_global_objects_as_roots
    if capture_numeric_value is not None:
        params['captureNumericValue'] = capture_numeric_value
    if expose_internals is not None:
        params['exposeInternals'] = expose_internals
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.stopTrackingHeapObjects',
        'params': params,
    }
    json = yield cmd_dict


def take_heap_snapshot(
        report_progress: typing.Optional[bool] = None,
        treat_global_objects_as_roots: typing.Optional[bool] = None,
        capture_numeric_value: typing.Optional[bool] = None,
        expose_internals: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param report_progress: *(Optional)* If true 'reportHeapSnapshotProgress' events will be generated while snapshot is being taken.
    :param treat_global_objects_as_roots: *(Optional)* If true, a raw snapshot without artificial roots will be generated. Deprecated in favor of ```exposeInternals```.
    :param capture_numeric_value: *(Optional)* If true, numerical values are included in the snapshot
    :param expose_internals: **(EXPERIMENTAL)** *(Optional)* If true, exposes internals of the snapshot.
    '''
    params: T_JSON_DICT = dict()
    if report_progress is not None:
        params['reportProgress'] = report_progress
    if treat_global_objects_as_roots is not None:
        params['treatGlobalObjectsAsRoots'] = treat_global_objects_as_roots
    if capture_numeric_value is not None:
        params['captureNumericValue'] = capture_numeric_value
    if expose_internals is not None:
        params['exposeInternals'] = expose_internals
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.takeHeapSnapshot',
        'params': params,
    }
    json = yield cmd_dict


@event_class('HeapProfiler.addHeapSnapshotChunk')
@dataclass
class AddHeapSnapshotChunk:
    chunk: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AddHeapSnapshotChunk:
        return cls(
            chunk=str(json['chunk'])
        )


@event_class('HeapProfiler.heapStatsUpdate')
@dataclass
class HeapStatsUpdate:
    '''
    If heap objects tracking has been started then backend may send update for one or more fragments
    '''
    #: An array of triplets. Each triplet describes a fragment. The first integer is the fragment
    #: index, the second integer is a total count of objects for the fragment, the third integer is
    #: a total size of the objects for the fragment.
    stats_update: typing.List[int]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> HeapStatsUpdate:
        return cls(
            stats_update=[int(i) for i in json['statsUpdate']]
        )


@event_class('HeapProfiler.lastSeenObjectId')
@dataclass
class LastSeenObjectId:
    '''
    If heap objects tracking has been started then backend regularly sends a current value for last
    seen object id and corresponding timestamp. If the were changes in the heap since last event
    then one or more heapStatsUpdate events will be sent before a new lastSeenObjectId event.
    '''
    last_seen_object_id: int
    timestamp: float

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LastSeenObjectId:
        return cls(
            last_seen_object_id=int(json['lastSeenObjectId']),
            timestamp=float(json['timestamp'])
        )


@event_class('HeapProfiler.reportHeapSnapshotProgress')
@dataclass
class ReportHeapSnapshotProgress:
    done: int
    total: int
    finished: typing.Optional[bool]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ReportHeapSnapshotProgress:
        return cls(
            done=int(json['done']),
            total=int(json['total']),
            finished=bool(json['finished']) if 'finished' in json else None
        )


@event_class('HeapProfiler.resetProfiles')
@dataclass
class ResetProfiles:


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ResetProfiles:
        return cls(

        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\heap_profiler.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: HeapProfiler (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import runtime


class HeapSnapshotObjectId(str):
    '''
    Heap snapshot object id.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> HeapSnapshotObjectId:
        return cls(json)

    def __repr__(self):
        return 'HeapSnapshotObjectId({})'.format(super().__repr__())


@dataclass
class SamplingHeapProfileNode:
    '''
    Sampling Heap Profile node. Holds callsite information, allocation statistics and child nodes.
    '''
    #: Function location.
    call_frame: runtime.CallFrame

    #: Allocations size in bytes for the node excluding children.
    self_size: float

    #: Node id. Ids are unique across all profiles collected between startSampling and stopSampling.
    id_: int

    #: Child nodes.
    children: typing.List[SamplingHeapProfileNode]

    def to_json(self):
        json = dict()
        json['callFrame'] = self.call_frame.to_json()
        json['selfSize'] = self.self_size
        json['id'] = self.id_
        json['children'] = [i.to_json() for i in self.children]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            call_frame=runtime.CallFrame.from_json(json['callFrame']),
            self_size=float(json['selfSize']),
            id_=int(json['id']),
            children=[SamplingHeapProfileNode.from_json(i) for i in json['children']],
        )


@dataclass
class SamplingHeapProfileSample:
    '''
    A single sample from a sampling profile.
    '''
    #: Allocation size in bytes attributed to the sample.
    size: float

    #: Id of the corresponding profile tree node.
    node_id: int

    #: Time-ordered sample ordinal number. It is unique across all profiles retrieved
    #: between startSampling and stopSampling.
    ordinal: float

    def to_json(self):
        json = dict()
        json['size'] = self.size
        json['nodeId'] = self.node_id
        json['ordinal'] = self.ordinal
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            size=float(json['size']),
            node_id=int(json['nodeId']),
            ordinal=float(json['ordinal']),
        )


@dataclass
class SamplingHeapProfile:
    '''
    Sampling profile.
    '''
    head: SamplingHeapProfileNode

    samples: typing.List[SamplingHeapProfileSample]

    def to_json(self):
        json = dict()
        json['head'] = self.head.to_json()
        json['samples'] = [i.to_json() for i in self.samples]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            head=SamplingHeapProfileNode.from_json(json['head']),
            samples=[SamplingHeapProfileSample.from_json(i) for i in json['samples']],
        )


def add_inspected_heap_object(
        heap_object_id: HeapSnapshotObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables console to refer to the node with given id via $x (see Command Line API for more details
    $x functions).

    :param heap_object_id: Heap snapshot object id to be accessible by means of $x command line API.
    '''
    params: T_JSON_DICT = dict()
    params['heapObjectId'] = heap_object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.addInspectedHeapObject',
        'params': params,
    }
    json = yield cmd_dict


def collect_garbage() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.collectGarbage',
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.enable',
    }
    json = yield cmd_dict


def get_heap_object_id(
        object_id: runtime.RemoteObjectId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,HeapSnapshotObjectId]:
    '''
    :param object_id: Identifier of the object to get heap object id for.
    :returns: Id of the heap snapshot object corresponding to the passed remote object id.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.getHeapObjectId',
        'params': params,
    }
    json = yield cmd_dict
    return HeapSnapshotObjectId.from_json(json['heapSnapshotObjectId'])


def get_object_by_heap_object_id(
        object_id: HeapSnapshotObjectId,
        object_group: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.RemoteObject]:
    '''
    :param object_id:
    :param object_group: *(Optional)* Symbolic group name that can be used to release multiple objects.
    :returns: Evaluation result.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    if object_group is not None:
        params['objectGroup'] = object_group
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.getObjectByHeapObjectId',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.RemoteObject.from_json(json['result'])


def get_sampling_profile() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SamplingHeapProfile]:
    '''


    :returns: Return the sampling profile being collected.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.getSamplingProfile',
    }
    json = yield cmd_dict
    return SamplingHeapProfile.from_json(json['profile'])


def start_sampling(
        sampling_interval: typing.Optional[float] = None,
        include_objects_collected_by_major_gc: typing.Optional[bool] = None,
        include_objects_collected_by_minor_gc: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param sampling_interval: *(Optional)* Average sample interval in bytes. Poisson distribution is used for the intervals. The default value is 32768 bytes.
    :param include_objects_collected_by_major_gc: *(Optional)* By default, the sampling heap profiler reports only objects which are still alive when the profile is returned via getSamplingProfile or stopSampling, which is useful for determining what functions contribute the most to steady-state memory usage. This flag instructs the sampling heap profiler to also include information about objects discarded by major GC, which will show which functions cause large temporary memory usage or long GC pauses.
    :param include_objects_collected_by_minor_gc: *(Optional)* By default, the sampling heap profiler reports only objects which are still alive when the profile is returned via getSamplingProfile or stopSampling, which is useful for determining what functions contribute the most to steady-state memory usage. This flag instructs the sampling heap profiler to also include information about objects discarded by minor GC, which is useful when tuning a latency-sensitive application for minimal GC activity.
    '''
    params: T_JSON_DICT = dict()
    if sampling_interval is not None:
        params['samplingInterval'] = sampling_interval
    if include_objects_collected_by_major_gc is not None:
        params['includeObjectsCollectedByMajorGC'] = include_objects_collected_by_major_gc
    if include_objects_collected_by_minor_gc is not None:
        params['includeObjectsCollectedByMinorGC'] = include_objects_collected_by_minor_gc
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.startSampling',
        'params': params,
    }
    json = yield cmd_dict


def start_tracking_heap_objects(
        track_allocations: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param track_allocations: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    if track_allocations is not None:
        params['trackAllocations'] = track_allocations
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.startTrackingHeapObjects',
        'params': params,
    }
    json = yield cmd_dict


def stop_sampling() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SamplingHeapProfile]:
    '''


    :returns: Recorded sampling heap profile.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.stopSampling',
    }
    json = yield cmd_dict
    return SamplingHeapProfile.from_json(json['profile'])


def stop_tracking_heap_objects(
        report_progress: typing.Optional[bool] = None,
        treat_global_objects_as_roots: typing.Optional[bool] = None,
        capture_numeric_value: typing.Optional[bool] = None,
        expose_internals: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param report_progress: *(Optional)* If true 'reportHeapSnapshotProgress' events will be generated while snapshot is being taken when the tracking is stopped.
    :param treat_global_objects_as_roots: *(Optional)* Deprecated in favor of ```exposeInternals```.
    :param capture_numeric_value: *(Optional)* If true, numerical values are included in the snapshot
    :param expose_internals: **(EXPERIMENTAL)** *(Optional)* If true, exposes internals of the snapshot.
    '''
    params: T_JSON_DICT = dict()
    if report_progress is not None:
        params['reportProgress'] = report_progress
    if treat_global_objects_as_roots is not None:
        params['treatGlobalObjectsAsRoots'] = treat_global_objects_as_roots
    if capture_numeric_value is not None:
        params['captureNumericValue'] = capture_numeric_value
    if expose_internals is not None:
        params['exposeInternals'] = expose_internals
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.stopTrackingHeapObjects',
        'params': params,
    }
    json = yield cmd_dict


def take_heap_snapshot(
        report_progress: typing.Optional[bool] = None,
        treat_global_objects_as_roots: typing.Optional[bool] = None,
        capture_numeric_value: typing.Optional[bool] = None,
        expose_internals: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param report_progress: *(Optional)* If true 'reportHeapSnapshotProgress' events will be generated while snapshot is being taken.
    :param treat_global_objects_as_roots: *(Optional)* If true, a raw snapshot without artificial roots will be generated. Deprecated in favor of ```exposeInternals```.
    :param capture_numeric_value: *(Optional)* If true, numerical values are included in the snapshot
    :param expose_internals: **(EXPERIMENTAL)** *(Optional)* If true, exposes internals of the snapshot.
    '''
    params: T_JSON_DICT = dict()
    if report_progress is not None:
        params['reportProgress'] = report_progress
    if treat_global_objects_as_roots is not None:
        params['treatGlobalObjectsAsRoots'] = treat_global_objects_as_roots
    if capture_numeric_value is not None:
        params['captureNumericValue'] = capture_numeric_value
    if expose_internals is not None:
        params['exposeInternals'] = expose_internals
    cmd_dict: T_JSON_DICT = {
        'method': 'HeapProfiler.takeHeapSnapshot',
        'params': params,
    }
    json = yield cmd_dict


@event_class('HeapProfiler.addHeapSnapshotChunk')
@dataclass
class AddHeapSnapshotChunk:
    chunk: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AddHeapSnapshotChunk:
        return cls(
            chunk=str(json['chunk'])
        )


@event_class('HeapProfiler.heapStatsUpdate')
@dataclass
class HeapStatsUpdate:
    '''
    If heap objects tracking has been started then backend may send update for one or more fragments
    '''
    #: An array of triplets. Each triplet describes a fragment. The first integer is the fragment
    #: index, the second integer is a total count of objects for the fragment, the third integer is
    #: a total size of the objects for the fragment.
    stats_update: typing.List[int]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> HeapStatsUpdate:
        return cls(
            stats_update=[int(i) for i in json['statsUpdate']]
        )


@event_class('HeapProfiler.lastSeenObjectId')
@dataclass
class LastSeenObjectId:
    '''
    If heap objects tracking has been started then backend regularly sends a current value for last
    seen object id and corresponding timestamp. If the were changes in the heap since last event
    then one or more heapStatsUpdate events will be sent before a new lastSeenObjectId event.
    '''
    last_seen_object_id: int
    timestamp: float

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LastSeenObjectId:
        return cls(
            last_seen_object_id=int(json['lastSeenObjectId']),
            timestamp=float(json['timestamp'])
        )


@event_class('HeapProfiler.reportHeapSnapshotProgress')
@dataclass
class ReportHeapSnapshotProgress:
    done: int
    total: int
    finished: typing.Optional[bool]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ReportHeapSnapshotProgress:
        return cls(
            done=int(json['done']),
            total=int(json['total']),
            finished=bool(json['finished']) if 'finished' in json else None
        )


@event_class('HeapProfiler.resetProfiles')
@dataclass
class ResetProfiles:


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ResetProfiles:
        return cls(

        )