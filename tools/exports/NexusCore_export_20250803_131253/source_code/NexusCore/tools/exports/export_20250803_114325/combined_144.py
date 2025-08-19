
# === NexusCore/openenv\Lib\site-packages\openai\resources\uploads\uploads.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import io
import os
import logging
import builtins
from typing import List, overload
from pathlib import Path

import anyio
import httpx

from ... import _legacy_response
from .parts import (
    Parts,
    AsyncParts,
    PartsWithRawResponse,
    AsyncPartsWithRawResponse,
    PartsWithStreamingResponse,
    AsyncPartsWithStreamingResponse,
)
from ...types import FilePurpose, upload_create_params, upload_complete_params
from ..._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ..._utils import maybe_transform, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ..._base_client import make_request_options
from ...types.upload import Upload
from ...types.file_purpose import FilePurpose

__all__ = ["Uploads", "AsyncUploads"]


# 64MB
DEFAULT_PART_SIZE = 64 * 1024 * 1024

log: logging.Logger = logging.getLogger(__name__)


class Uploads(SyncAPIResource):
    @cached_property
    def parts(self) -> Parts:
        return Parts(self._client)

    @cached_property
    def with_raw_response(self) -> UploadsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return UploadsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> UploadsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return UploadsWithStreamingResponse(self)

    @overload
    def upload_file_chunked(
        self,
        *,
        file: os.PathLike[str],
        mime_type: str,
        purpose: FilePurpose,
        bytes: int | None = None,
        part_size: int | None = None,
        md5: str | NotGiven = NOT_GIVEN,
    ) -> Upload:
        """Splits a file into multiple 64MB parts and uploads them sequentially."""

    @overload
    def upload_file_chunked(
        self,
        *,
        file: bytes,
        filename: str,
        bytes: int,
        mime_type: str,
        purpose: FilePurpose,
        part_size: int | None = None,
        md5: str | NotGiven = NOT_GIVEN,
    ) -> Upload:
        """Splits an in-memory file into multiple 64MB parts and uploads them sequentially."""

    def upload_file_chunked(
        self,
        *,
        file: os.PathLike[str] | bytes,
        mime_type: str,
        purpose: FilePurpose,
        filename: str | None = None,
        bytes: int | None = None,
        part_size: int | None = None,
        md5: str | NotGiven = NOT_GIVEN,
    ) -> Upload:
        """Splits the given file into multiple parts and uploads them sequentially.

        ```py
        from pathlib import Path

        client.uploads.upload_file(
            file=Path("my-paper.pdf"),
            mime_type="pdf",
            purpose="assistants",
        )
        ```
        """
        if isinstance(file, builtins.bytes):
            if filename is None:
                raise TypeError("The `filename` argument must be given for in-memory files")

            if bytes is None:
                raise TypeError("The `bytes` argument must be given for in-memory files")
        else:
            if not isinstance(file, Path):
                file = Path(file)

            if not filename:
                filename = file.name

            if bytes is None:
                bytes = file.stat().st_size

        upload = self.create(
            bytes=bytes,
            filename=filename,
            mime_type=mime_type,
            purpose=purpose,
        )

        part_ids: list[str] = []

        if part_size is None:
            part_size = DEFAULT_PART_SIZE

        if isinstance(file, builtins.bytes):
            buf: io.FileIO | io.BytesIO = io.BytesIO(file)
        else:
            buf = io.FileIO(file)

        try:
            while True:
                data = buf.read(part_size)
                if not data:
                    # EOF
                    break

                part = self.parts.create(upload_id=upload.id, data=data)
                log.info("Uploaded part %s for upload %s", part.id, upload.id)
                part_ids.append(part.id)
        except Exception:
            buf.close()
            raise

        return self.complete(upload_id=upload.id, part_ids=part_ids, md5=md5)

    def create(
        self,
        *,
        bytes: int,
        filename: str,
        mime_type: str,
        purpose: FilePurpose,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Upload:
        """
        Creates an intermediate
        [Upload](https://platform.openai.com/docs/api-reference/uploads/object) object
        that you can add
        [Parts](https://platform.openai.com/docs/api-reference/uploads/part-object) to.
        Currently, an Upload can accept at most 8 GB in total and expires after an hour
        after you create it.

        Once you complete the Upload, we will create a
        [File](https://platform.openai.com/docs/api-reference/files/object) object that
        contains all the parts you uploaded. This File is usable in the rest of our
        platform as a regular File object.

        For certain `purpose` values, the correct `mime_type` must be specified. Please
        refer to documentation for the
        [supported MIME types for your use case](https://platform.openai.com/docs/assistants/tools/file-search#supported-files).

        For guidance on the proper filename extensions for each purpose, please follow
        the documentation on
        [creating a File](https://platform.openai.com/docs/api-reference/files/create).

        Args:
          bytes: The number of bytes in the file you are uploading.

          filename: The name of the file to upload.

          mime_type: The MIME type of the file.

              This must fall within the supported MIME types for your file purpose. See the
              supported MIME types for assistants and vision.

          purpose: The intended purpose of the uploaded file.

              See the
              [documentation on File purposes](https://platform.openai.com/docs/api-reference/files/create#files-create-purpose).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/uploads",
            body=maybe_transform(
                {
                    "bytes": bytes,
                    "filename": filename,
                    "mime_type": mime_type,
                    "purpose": purpose,
                },
                upload_create_params.UploadCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Upload,
        )

    def cancel(
        self,
        upload_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Upload:
        """Cancels the Upload.

        No Parts may be added after an Upload is cancelled.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not upload_id:
            raise ValueError(f"Expected a non-empty value for `upload_id` but received {upload_id!r}")
        return self._post(
            f"/uploads/{upload_id}/cancel",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Upload,
        )

    def complete(
        self,
        upload_id: str,
        *,
        part_ids: List[str],
        md5: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Upload:
        """
        Completes the
        [Upload](https://platform.openai.com/docs/api-reference/uploads/object).

        Within the returned Upload object, there is a nested
        [File](https://platform.openai.com/docs/api-reference/files/object) object that
        is ready to use in the rest of the platform.

        You can specify the order of the Parts by passing in an ordered list of the Part
        IDs.

        The number of bytes uploaded upon completion must match the number of bytes
        initially specified when creating the Upload object. No Parts may be added after
        an Upload is completed.

        Args:
          part_ids: The ordered list of Part IDs.

          md5: The optional md5 checksum for the file contents to verify if the bytes uploaded
              matches what you expect.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not upload_id:
            raise ValueError(f"Expected a non-empty value for `upload_id` but received {upload_id!r}")
        return self._post(
            f"/uploads/{upload_id}/complete",
            body=maybe_transform(
                {
                    "part_ids": part_ids,
                    "md5": md5,
                },
                upload_complete_params.UploadCompleteParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Upload,
        )


class AsyncUploads(AsyncAPIResource):
    @cached_property
    def parts(self) -> AsyncParts:
        return AsyncParts(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncUploadsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncUploadsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncUploadsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncUploadsWithStreamingResponse(self)

    @overload
    async def upload_file_chunked(
        self,
        *,
        file: os.PathLike[str],
        mime_type: str,
        purpose: FilePurpose,
        bytes: int | None = None,
        part_size: int | None = None,
        md5: str | NotGiven = NOT_GIVEN,
    ) -> Upload:
        """Splits a file into multiple 64MB parts and uploads them sequentially."""

    @overload
    async def upload_file_chunked(
        self,
        *,
        file: bytes,
        filename: str,
        bytes: int,
        mime_type: str,
        purpose: FilePurpose,
        part_size: int | None = None,
        md5: str | NotGiven = NOT_GIVEN,
    ) -> Upload:
        """Splits an in-memory file into multiple 64MB parts and uploads them sequentially."""

    async def upload_file_chunked(
        self,
        *,
        file: os.PathLike[str] | bytes,
        mime_type: str,
        purpose: FilePurpose,
        filename: str | None = None,
        bytes: int | None = None,
        part_size: int | None = None,
        md5: str | NotGiven = NOT_GIVEN,
    ) -> Upload:
        """Splits the given file into multiple parts and uploads them sequentially.

        ```py
        from pathlib import Path

        client.uploads.upload_file(
            file=Path("my-paper.pdf"),
            mime_type="pdf",
            purpose="assistants",
        )
        ```
        """
        if isinstance(file, builtins.bytes):
            if filename is None:
                raise TypeError("The `filename` argument must be given for in-memory files")

            if bytes is None:
                raise TypeError("The `bytes` argument must be given for in-memory files")
        else:
            if not isinstance(file, anyio.Path):
                file = anyio.Path(file)

            if not filename:
                filename = file.name

            if bytes is None:
                stat = await file.stat()
                bytes = stat.st_size

        upload = await self.create(
            bytes=bytes,
            filename=filename,
            mime_type=mime_type,
            purpose=purpose,
        )

        part_ids: list[str] = []

        if part_size is None:
            part_size = DEFAULT_PART_SIZE

        if isinstance(file, anyio.Path):
            fd = await file.open("rb")
            async with fd:
                while True:
                    data = await fd.read(part_size)
                    if not data:
                        # EOF
                        break

                    part = await self.parts.create(upload_id=upload.id, data=data)
                    log.info("Uploaded part %s for upload %s", part.id, upload.id)
                    part_ids.append(part.id)
        else:
            buf = io.BytesIO(file)

            try:
                while True:
                    data = buf.read(part_size)
                    if not data:
                        # EOF
                        break

                    part = await self.parts.create(upload_id=upload.id, data=data)
                    log.info("Uploaded part %s for upload %s", part.id, upload.id)
                    part_ids.append(part.id)
            except Exception:
                buf.close()
                raise

        return await self.complete(upload_id=upload.id, part_ids=part_ids, md5=md5)

    async def create(
        self,
        *,
        bytes: int,
        filename: str,
        mime_type: str,
        purpose: FilePurpose,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Upload:
        """
        Creates an intermediate
        [Upload](https://platform.openai.com/docs/api-reference/uploads/object) object
        that you can add
        [Parts](https://platform.openai.com/docs/api-reference/uploads/part-object) to.
        Currently, an Upload can accept at most 8 GB in total and expires after an hour
        after you create it.

        Once you complete the Upload, we will create a
        [File](https://platform.openai.com/docs/api-reference/files/object) object that
        contains all the parts you uploaded. This File is usable in the rest of our
        platform as a regular File object.

        For certain `purpose` values, the correct `mime_type` must be specified. Please
        refer to documentation for the
        [supported MIME types for your use case](https://platform.openai.com/docs/assistants/tools/file-search#supported-files).

        For guidance on the proper filename extensions for each purpose, please follow
        the documentation on
        [creating a File](https://platform.openai.com/docs/api-reference/files/create).

        Args:
          bytes: The number of bytes in the file you are uploading.

          filename: The name of the file to upload.

          mime_type: The MIME type of the file.

              This must fall within the supported MIME types for your file purpose. See the
              supported MIME types for assistants and vision.

          purpose: The intended purpose of the uploaded file.

              See the
              [documentation on File purposes](https://platform.openai.com/docs/api-reference/files/create#files-create-purpose).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/uploads",
            body=await async_maybe_transform(
                {
                    "bytes": bytes,
                    "filename": filename,
                    "mime_type": mime_type,
                    "purpose": purpose,
                },
                upload_create_params.UploadCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Upload,
        )

    async def cancel(
        self,
        upload_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Upload:
        """Cancels the Upload.

        No Parts may be added after an Upload is cancelled.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not upload_id:
            raise ValueError(f"Expected a non-empty value for `upload_id` but received {upload_id!r}")
        return await self._post(
            f"/uploads/{upload_id}/cancel",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Upload,
        )

    async def complete(
        self,
        upload_id: str,
        *,
        part_ids: List[str],
        md5: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Upload:
        """
        Completes the
        [Upload](https://platform.openai.com/docs/api-reference/uploads/object).

        Within the returned Upload object, there is a nested
        [File](https://platform.openai.com/docs/api-reference/files/object) object that
        is ready to use in the rest of the platform.

        You can specify the order of the Parts by passing in an ordered list of the Part
        IDs.

        The number of bytes uploaded upon completion must match the number of bytes
        initially specified when creating the Upload object. No Parts may be added after
        an Upload is completed.

        Args:
          part_ids: The ordered list of Part IDs.

          md5: The optional md5 checksum for the file contents to verify if the bytes uploaded
              matches what you expect.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not upload_id:
            raise ValueError(f"Expected a non-empty value for `upload_id` but received {upload_id!r}")
        return await self._post(
            f"/uploads/{upload_id}/complete",
            body=await async_maybe_transform(
                {
                    "part_ids": part_ids,
                    "md5": md5,
                },
                upload_complete_params.UploadCompleteParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Upload,
        )


class UploadsWithRawResponse:
    def __init__(self, uploads: Uploads) -> None:
        self._uploads = uploads

        self.create = _legacy_response.to_raw_response_wrapper(
            uploads.create,
        )
        self.cancel = _legacy_response.to_raw_response_wrapper(
            uploads.cancel,
        )
        self.complete = _legacy_response.to_raw_response_wrapper(
            uploads.complete,
        )

    @cached_property
    def parts(self) -> PartsWithRawResponse:
        return PartsWithRawResponse(self._uploads.parts)


class AsyncUploadsWithRawResponse:
    def __init__(self, uploads: AsyncUploads) -> None:
        self._uploads = uploads

        self.create = _legacy_response.async_to_raw_response_wrapper(
            uploads.create,
        )
        self.cancel = _legacy_response.async_to_raw_response_wrapper(
            uploads.cancel,
        )
        self.complete = _legacy_response.async_to_raw_response_wrapper(
            uploads.complete,
        )

    @cached_property
    def parts(self) -> AsyncPartsWithRawResponse:
        return AsyncPartsWithRawResponse(self._uploads.parts)


class UploadsWithStreamingResponse:
    def __init__(self, uploads: Uploads) -> None:
        self._uploads = uploads

        self.create = to_streamed_response_wrapper(
            uploads.create,
        )
        self.cancel = to_streamed_response_wrapper(
            uploads.cancel,
        )
        self.complete = to_streamed_response_wrapper(
            uploads.complete,
        )

    @cached_property
    def parts(self) -> PartsWithStreamingResponse:
        return PartsWithStreamingResponse(self._uploads.parts)


class AsyncUploadsWithStreamingResponse:
    def __init__(self, uploads: AsyncUploads) -> None:
        self._uploads = uploads

        self.create = async_to_streamed_response_wrapper(
            uploads.create,
        )
        self.cancel = async_to_streamed_response_wrapper(
            uploads.cancel,
        )
        self.complete = async_to_streamed_response_wrapper(
            uploads.complete,
        )

    @cached_property
    def parts(self) -> AsyncPartsWithStreamingResponse:
        return AsyncPartsWithStreamingResponse(self._uploads.parts)

# === NexusCore/openenv\Lib\site-packages\attr\validators.py ===
# SPDX-License-Identifier: MIT

"""
Commonly useful validators.
"""

import operator
import re

from contextlib import contextmanager
from re import Pattern

from ._config import get_run_validators, set_run_validators
from ._make import _AndValidator, and_, attrib, attrs
from .converters import default_if_none
from .exceptions import NotCallableError


__all__ = [
    "and_",
    "deep_iterable",
    "deep_mapping",
    "disabled",
    "ge",
    "get_disabled",
    "gt",
    "in_",
    "instance_of",
    "is_callable",
    "le",
    "lt",
    "matches_re",
    "max_len",
    "min_len",
    "not_",
    "optional",
    "or_",
    "set_disabled",
]


def set_disabled(disabled):
    """
    Globally disable or enable running validators.

    By default, they are run.

    Args:
        disabled (bool): If `True`, disable running all validators.

    .. warning::

        This function is not thread-safe!

    .. versionadded:: 21.3.0
    """
    set_run_validators(not disabled)


def get_disabled():
    """
    Return a bool indicating whether validators are currently disabled or not.

    Returns:
        bool:`True` if validators are currently disabled.

    .. versionadded:: 21.3.0
    """
    return not get_run_validators()


@contextmanager
def disabled():
    """
    Context manager that disables running validators within its context.

    .. warning::

        This context manager is not thread-safe!

    .. versionadded:: 21.3.0
    """
    set_run_validators(False)
    try:
        yield
    finally:
        set_run_validators(True)


@attrs(repr=False, slots=True, unsafe_hash=True)
class _InstanceOfValidator:
    type = attrib()

    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if not isinstance(value, self.type):
            msg = f"'{attr.name}' must be {self.type!r} (got {value!r} that is a {value.__class__!r})."
            raise TypeError(
                msg,
                attr,
                self.type,
                value,
            )

    def __repr__(self):
        return f"<instance_of validator for type {self.type!r}>"


def instance_of(type):
    """
    A validator that raises a `TypeError` if the initializer is called with a
    wrong type for this particular attribute (checks are performed using
    `isinstance` therefore it's also valid to pass a tuple of types).

    Args:
        type (type | tuple[type]): The type to check for.

    Raises:
        TypeError:
            With a human readable error message, the attribute (of type
            `attrs.Attribute`), the expected type, and the value it got.
    """
    return _InstanceOfValidator(type)


@attrs(repr=False, frozen=True, slots=True)
class _MatchesReValidator:
    pattern = attrib()
    match_func = attrib()

    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if not self.match_func(value):
            msg = f"'{attr.name}' must match regex {self.pattern.pattern!r} ({value!r} doesn't)"
            raise ValueError(
                msg,
                attr,
                self.pattern,
                value,
            )

    def __repr__(self):
        return f"<matches_re validator for pattern {self.pattern!r}>"


def matches_re(regex, flags=0, func=None):
    r"""
    A validator that raises `ValueError` if the initializer is called with a
    string that doesn't match *regex*.

    Args:
        regex (str, re.Pattern):
            A regex string or precompiled pattern to match against

        flags (int):
            Flags that will be passed to the underlying re function (default 0)

        func (typing.Callable):
            Which underlying `re` function to call. Valid options are
            `re.fullmatch`, `re.search`, and `re.match`; the default `None`
            means `re.fullmatch`. For performance reasons, the pattern is
            always precompiled using `re.compile`.

    .. versionadded:: 19.2.0
    .. versionchanged:: 21.3.0 *regex* can be a pre-compiled pattern.
    """
    valid_funcs = (re.fullmatch, None, re.search, re.match)
    if func not in valid_funcs:
        msg = "'func' must be one of {}.".format(
            ", ".join(
                sorted((e and e.__name__) or "None" for e in set(valid_funcs))
            )
        )
        raise ValueError(msg)

    if isinstance(regex, Pattern):
        if flags:
            msg = "'flags' can only be used with a string pattern; pass flags to re.compile() instead"
            raise TypeError(msg)
        pattern = regex
    else:
        pattern = re.compile(regex, flags)

    if func is re.match:
        match_func = pattern.match
    elif func is re.search:
        match_func = pattern.search
    else:
        match_func = pattern.fullmatch

    return _MatchesReValidator(pattern, match_func)


@attrs(repr=False, slots=True, unsafe_hash=True)
class _OptionalValidator:
    validator = attrib()

    def __call__(self, inst, attr, value):
        if value is None:
            return

        self.validator(inst, attr, value)

    def __repr__(self):
        return f"<optional validator for {self.validator!r} or None>"


def optional(validator):
    """
    A validator that makes an attribute optional.  An optional attribute is one
    which can be set to `None` in addition to satisfying the requirements of
    the sub-validator.

    Args:
        validator
            (typing.Callable | tuple[typing.Callable] | list[typing.Callable]):
            A validator (or validators) that is used for non-`None` values.

    .. versionadded:: 15.1.0
    .. versionchanged:: 17.1.0 *validator* can be a list of validators.
    .. versionchanged:: 23.1.0 *validator* can also be a tuple of validators.
    """
    if isinstance(validator, (list, tuple)):
        return _OptionalValidator(_AndValidator(validator))

    return _OptionalValidator(validator)


@attrs(repr=False, slots=True, unsafe_hash=True)
class _InValidator:
    options = attrib()
    _original_options = attrib(hash=False)

    def __call__(self, inst, attr, value):
        try:
            in_options = value in self.options
        except TypeError:  # e.g. `1 in "abc"`
            in_options = False

        if not in_options:
            msg = f"'{attr.name}' must be in {self._original_options!r} (got {value!r})"
            raise ValueError(
                msg,
                attr,
                self._original_options,
                value,
            )

    def __repr__(self):
        return f"<in_ validator with options {self._original_options!r}>"


def in_(options):
    """
    A validator that raises a `ValueError` if the initializer is called with a
    value that does not belong in the *options* provided.

    The check is performed using ``value in options``, so *options* has to
    support that operation.

    To keep the validator hashable, dicts, lists, and sets are transparently
    transformed into a `tuple`.

    Args:
        options: Allowed options.

    Raises:
        ValueError:
            With a human readable error message, the attribute (of type
            `attrs.Attribute`), the expected options, and the value it got.

    .. versionadded:: 17.1.0
    .. versionchanged:: 22.1.0
       The ValueError was incomplete until now and only contained the human
       readable error message. Now it contains all the information that has
       been promised since 17.1.0.
    .. versionchanged:: 24.1.0
       *options* that are a list, dict, or a set are now transformed into a
       tuple to keep the validator hashable.
    """
    repr_options = options
    if isinstance(options, (list, dict, set)):
        options = tuple(options)

    return _InValidator(options, repr_options)


@attrs(repr=False, slots=False, unsafe_hash=True)
class _IsCallableValidator:
    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if not callable(value):
            message = (
                "'{name}' must be callable "
                "(got {value!r} that is a {actual!r})."
            )
            raise NotCallableError(
                msg=message.format(
                    name=attr.name, value=value, actual=value.__class__
                ),
                value=value,
            )

    def __repr__(self):
        return "<is_callable validator>"


def is_callable():
    """
    A validator that raises a `attrs.exceptions.NotCallableError` if the
    initializer is called with a value for this particular attribute that is
    not callable.

    .. versionadded:: 19.1.0

    Raises:
        attrs.exceptions.NotCallableError:
            With a human readable error message containing the attribute
            (`attrs.Attribute`) name, and the value it got.
    """
    return _IsCallableValidator()


@attrs(repr=False, slots=True, unsafe_hash=True)
class _DeepIterable:
    member_validator = attrib(validator=is_callable())
    iterable_validator = attrib(
        default=None, validator=optional(is_callable())
    )

    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if self.iterable_validator is not None:
            self.iterable_validator(inst, attr, value)

        for member in value:
            self.member_validator(inst, attr, member)

    def __repr__(self):
        iterable_identifier = (
            ""
            if self.iterable_validator is None
            else f" {self.iterable_validator!r}"
        )
        return (
            f"<deep_iterable validator for{iterable_identifier}"
            f" iterables of {self.member_validator!r}>"
        )


def deep_iterable(member_validator, iterable_validator=None):
    """
    A validator that performs deep validation of an iterable.

    Args:
        member_validator: Validator to apply to iterable members.

        iterable_validator:
            Validator to apply to iterable itself (optional).

    Raises
        TypeError: if any sub-validators fail

    .. versionadded:: 19.1.0
    """
    if isinstance(member_validator, (list, tuple)):
        member_validator = and_(*member_validator)
    return _DeepIterable(member_validator, iterable_validator)


@attrs(repr=False, slots=True, unsafe_hash=True)
class _DeepMapping:
    key_validator = attrib(validator=is_callable())
    value_validator = attrib(validator=is_callable())
    mapping_validator = attrib(default=None, validator=optional(is_callable()))

    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if self.mapping_validator is not None:
            self.mapping_validator(inst, attr, value)

        for key in value:
            self.key_validator(inst, attr, key)
            self.value_validator(inst, attr, value[key])

    def __repr__(self):
        return f"<deep_mapping validator for objects mapping {self.key_validator!r} to {self.value_validator!r}>"


def deep_mapping(key_validator, value_validator, mapping_validator=None):
    """
    A validator that performs deep validation of a dictionary.

    Args:
        key_validator: Validator to apply to dictionary keys.

        value_validator: Validator to apply to dictionary values.

        mapping_validator:
            Validator to apply to top-level mapping attribute (optional).

    .. versionadded:: 19.1.0

    Raises:
        TypeError: if any sub-validators fail
    """
    return _DeepMapping(key_validator, value_validator, mapping_validator)


@attrs(repr=False, frozen=True, slots=True)
class _NumberValidator:
    bound = attrib()
    compare_op = attrib()
    compare_func = attrib()

    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if not self.compare_func(value, self.bound):
            msg = f"'{attr.name}' must be {self.compare_op} {self.bound}: {value}"
            raise ValueError(msg)

    def __repr__(self):
        return f"<Validator for x {self.compare_op} {self.bound}>"


def lt(val):
    """
    A validator that raises `ValueError` if the initializer is called with a
    number larger or equal to *val*.

    The validator uses `operator.lt` to compare the values.

    Args:
        val: Exclusive upper bound for values.

    .. versionadded:: 21.3.0
    """
    return _NumberValidator(val, "<", operator.lt)


def le(val):
    """
    A validator that raises `ValueError` if the initializer is called with a
    number greater than *val*.

    The validator uses `operator.le` to compare the values.

    Args:
        val: Inclusive upper bound for values.

    .. versionadded:: 21.3.0
    """
    return _NumberValidator(val, "<=", operator.le)


def ge(val):
    """
    A validator that raises `ValueError` if the initializer is called with a
    number smaller than *val*.

    The validator uses `operator.ge` to compare the values.

    Args:
        val: Inclusive lower bound for values

    .. versionadded:: 21.3.0
    """
    return _NumberValidator(val, ">=", operator.ge)


def gt(val):
    """
    A validator that raises `ValueError` if the initializer is called with a
    number smaller or equal to *val*.

    The validator uses `operator.ge` to compare the values.

    Args:
       val: Exclusive lower bound for values

    .. versionadded:: 21.3.0
    """
    return _NumberValidator(val, ">", operator.gt)


@attrs(repr=False, frozen=True, slots=True)
class _MaxLengthValidator:
    max_length = attrib()

    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if len(value) > self.max_length:
            msg = f"Length of '{attr.name}' must be <= {self.max_length}: {len(value)}"
            raise ValueError(msg)

    def __repr__(self):
        return f"<max_len validator for {self.max_length}>"


def max_len(length):
    """
    A validator that raises `ValueError` if the initializer is called
    with a string or iterable that is longer than *length*.

    Args:
        length (int): Maximum length of the string or iterable

    .. versionadded:: 21.3.0
    """
    return _MaxLengthValidator(length)


@attrs(repr=False, frozen=True, slots=True)
class _MinLengthValidator:
    min_length = attrib()

    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if len(value) < self.min_length:
            msg = f"Length of '{attr.name}' must be >= {self.min_length}: {len(value)}"
            raise ValueError(msg)

    def __repr__(self):
        return f"<min_len validator for {self.min_length}>"


def min_len(length):
    """
    A validator that raises `ValueError` if the initializer is called
    with a string or iterable that is shorter than *length*.

    Args:
        length (int): Minimum length of the string or iterable

    .. versionadded:: 22.1.0
    """
    return _MinLengthValidator(length)


@attrs(repr=False, slots=True, unsafe_hash=True)
class _SubclassOfValidator:
    type = attrib()

    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if not issubclass(value, self.type):
            msg = f"'{attr.name}' must be a subclass of {self.type!r} (got {value!r})."
            raise TypeError(
                msg,
                attr,
                self.type,
                value,
            )

    def __repr__(self):
        return f"<subclass_of validator for type {self.type!r}>"


def _subclass_of(type):
    """
    A validator that raises a `TypeError` if the initializer is called with a
    wrong type for this particular attribute (checks are performed using
    `issubclass` therefore it's also valid to pass a tuple of types).

    Args:
        type (type | tuple[type, ...]): The type(s) to check for.

    Raises:
        TypeError:
            With a human readable error message, the attribute (of type
            `attrs.Attribute`), the expected type, and the value it got.
    """
    return _SubclassOfValidator(type)


@attrs(repr=False, slots=True, unsafe_hash=True)
class _NotValidator:
    validator = attrib()
    msg = attrib(
        converter=default_if_none(
            "not_ validator child '{validator!r}' "
            "did not raise a captured error"
        )
    )
    exc_types = attrib(
        validator=deep_iterable(
            member_validator=_subclass_of(Exception),
            iterable_validator=instance_of(tuple),
        ),
    )

    def __call__(self, inst, attr, value):
        try:
            self.validator(inst, attr, value)
        except self.exc_types:
            pass  # suppress error to invert validity
        else:
            raise ValueError(
                self.msg.format(
                    validator=self.validator,
                    exc_types=self.exc_types,
                ),
                attr,
                self.validator,
                value,
                self.exc_types,
            )

    def __repr__(self):
        return f"<not_ validator wrapping {self.validator!r}, capturing {self.exc_types!r}>"


def not_(validator, *, msg=None, exc_types=(ValueError, TypeError)):
    """
    A validator that wraps and logically 'inverts' the validator passed to it.
    It will raise a `ValueError` if the provided validator *doesn't* raise a
    `ValueError` or `TypeError` (by default), and will suppress the exception
    if the provided validator *does*.

    Intended to be used with existing validators to compose logic without
    needing to create inverted variants, for example, ``not_(in_(...))``.

    Args:
        validator: A validator to be logically inverted.

        msg (str):
            Message to raise if validator fails. Formatted with keys
            ``exc_types`` and ``validator``.

        exc_types (tuple[type, ...]):
            Exception type(s) to capture. Other types raised by child
            validators will not be intercepted and pass through.

    Raises:
        ValueError:
            With a human readable error message, the attribute (of type
            `attrs.Attribute`), the validator that failed to raise an
            exception, the value it got, and the expected exception types.

    .. versionadded:: 22.2.0
    """
    try:
        exc_types = tuple(exc_types)
    except TypeError:
        exc_types = (exc_types,)
    return _NotValidator(validator, msg, exc_types)


@attrs(repr=False, slots=True, unsafe_hash=True)
class _OrValidator:
    validators = attrib()

    def __call__(self, inst, attr, value):
        for v in self.validators:
            try:
                v(inst, attr, value)
            except Exception:  # noqa: BLE001, PERF203, S112
                continue
            else:
                return

        msg = f"None of {self.validators!r} satisfied for value {value!r}"
        raise ValueError(msg)

    def __repr__(self):
        return f"<or validator wrapping {self.validators!r}>"


def or_(*validators):
    """
    A validator that composes multiple validators into one.

    When called on a value, it runs all wrapped validators until one of them is
    satisfied.

    Args:
        validators (~collections.abc.Iterable[typing.Callable]):
            Arbitrary number of validators.

    Raises:
        ValueError:
            If no validator is satisfied. Raised with a human-readable error
            message listing all the wrapped validators and the value that
            failed all of them.

    .. versionadded:: 24.1.0
    """
    vals = []
    for v in validators:
        vals.extend(v.validators if isinstance(v, _OrValidator) else [v])

    return _OrValidator(tuple(vals))

# === NexusCore/openenv\Lib\site-packages\litellm\llms\sagemaker\completion\handler.py ===
import json
from copy import deepcopy
from typing import Any, Callable, List, Optional, Union, cast

import httpx

import litellm
from litellm._logging import verbose_logger
from litellm.litellm_core_utils.asyncify import asyncify
from litellm.llms.bedrock.base_aws_llm import BaseAWSLLM
from litellm.llms.custom_httpx.http_handler import (
    _get_httpx_client,
    get_async_httpx_client,
)
from litellm.types.llms.openai import AllMessageValues
from litellm.utils import (
    CustomStreamWrapper,
    EmbeddingResponse,
    ModelResponse,
    Usage,
    get_secret,
)

from ..common_utils import AWSEventStreamDecoder, SagemakerError
from .transformation import SagemakerConfig

sagemaker_config = SagemakerConfig()

"""
SAGEMAKER AUTH Keys/Vars
os.environ['AWS_ACCESS_KEY_ID'] = ""
os.environ['AWS_SECRET_ACCESS_KEY'] = ""
"""


# set os.environ['AWS_REGION_NAME'] = <your-region_name>
class SagemakerLLM(BaseAWSLLM):
    def _load_credentials(
        self,
        optional_params: dict,
    ):
        try:
            from botocore.credentials import Credentials
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")
        ## CREDENTIALS ##
        # pop aws_secret_access_key, aws_access_key_id, aws_session_token, aws_region_name from kwargs, since completion calls fail with them
        aws_secret_access_key = optional_params.pop("aws_secret_access_key", None)
        aws_access_key_id = optional_params.pop("aws_access_key_id", None)
        aws_session_token = optional_params.pop("aws_session_token", None)
        aws_region_name = optional_params.pop("aws_region_name", None)
        aws_role_name = optional_params.pop("aws_role_name", None)
        aws_session_name = optional_params.pop("aws_session_name", None)
        aws_profile_name = optional_params.pop("aws_profile_name", None)
        optional_params.pop(
            "aws_bedrock_runtime_endpoint", None
        )  # https://bedrock-runtime.{region_name}.amazonaws.com
        aws_web_identity_token = optional_params.pop("aws_web_identity_token", None)
        aws_sts_endpoint = optional_params.pop("aws_sts_endpoint", None)

        ### SET REGION NAME ###
        if aws_region_name is None:
            # check env #
            litellm_aws_region_name = get_secret("AWS_REGION_NAME", None)

            if litellm_aws_region_name is not None and isinstance(
                litellm_aws_region_name, str
            ):
                aws_region_name = litellm_aws_region_name

            standard_aws_region_name = get_secret("AWS_REGION", None)
            if standard_aws_region_name is not None and isinstance(
                standard_aws_region_name, str
            ):
                aws_region_name = standard_aws_region_name

            if aws_region_name is None:
                aws_region_name = "us-west-2"

        credentials: Credentials = self.get_credentials(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            aws_region_name=aws_region_name,
            aws_session_name=aws_session_name,
            aws_profile_name=aws_profile_name,
            aws_role_name=aws_role_name,
            aws_web_identity_token=aws_web_identity_token,
            aws_sts_endpoint=aws_sts_endpoint,
        )
        return credentials, aws_region_name

    def _prepare_request(
        self,
        credentials,
        model: str,
        data: dict,
        messages: List[AllMessageValues],
        litellm_params: dict,
        optional_params: dict,
        aws_region_name: str,
        extra_headers: Optional[dict] = None,
    ):
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")

        sigv4 = SigV4Auth(credentials, "sagemaker", aws_region_name)
        if optional_params.get("stream") is True:
            api_base = f"https://runtime.sagemaker.{aws_region_name}.amazonaws.com/endpoints/{model}/invocations-response-stream"
        else:
            api_base = f"https://runtime.sagemaker.{aws_region_name}.amazonaws.com/endpoints/{model}/invocations"

        sagemaker_base_url = optional_params.get("sagemaker_base_url", None)
        if sagemaker_base_url is not None:
            api_base = sagemaker_base_url

        encoded_data = json.dumps(data).encode("utf-8")
        headers = sagemaker_config.validate_environment(
            headers=extra_headers,
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )
        request = AWSRequest(
            method="POST", url=api_base, data=encoded_data, headers=headers
        )
        sigv4.add_auth(request)
        if (
            extra_headers is not None and "Authorization" in extra_headers
        ):  # prevent sigv4 from overwriting the auth header
            request.headers["Authorization"] = extra_headers["Authorization"]

        prepped_request = request.prepare()

        return prepped_request

    def completion(  # noqa: PLR0915
        self,
        model: str,
        messages: list,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding,
        logging_obj,
        optional_params: dict,
        litellm_params: dict,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        custom_prompt_dict={},
        hf_model_name=None,
        logger_fn=None,
        acompletion: bool = False,
        headers: dict = {},
    ):
        # pop streaming if it's in the optional params as 'stream' raises an error with sagemaker
        credentials, aws_region_name = self._load_credentials(optional_params)
        inference_params = deepcopy(optional_params)
        stream = inference_params.pop("stream", None)
        model_id = optional_params.get("model_id", None)

        ## Load Config
        config = litellm.SagemakerConfig.get_config()
        for k, v in config.items():
            if (
                k not in inference_params
            ):  # completion(top_k=3) > sagemaker_config(top_k=3) <- allows for dynamic variables to be passed in
                inference_params[k] = v

        if stream is True:
            if acompletion is True:
                response = self.async_streaming(
                    messages=messages,
                    model=model,
                    custom_prompt_dict=custom_prompt_dict,
                    hf_model_name=hf_model_name,
                    optional_params=optional_params,
                    encoding=encoding,
                    model_response=model_response,
                    logging_obj=logging_obj,
                    model_id=model_id,
                    aws_region_name=aws_region_name,
                    credentials=credentials,
                    headers=headers,
                    litellm_params=litellm_params,
                )
                return response
            else:
                data = sagemaker_config.transform_request(
                    model=model,
                    messages=messages,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    headers=headers,
                )
                prepared_request = self._prepare_request(
                    model=model,
                    data=data,
                    messages=messages,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    credentials=credentials,
                    aws_region_name=aws_region_name,
                )
                if model_id is not None:
                    # Add model_id as InferenceComponentName header
                    # boto3 doc: https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_runtime_InvokeEndpoint.html
                    prepared_request.headers.update(
                        {"X-Amzn-SageMaker-Inference-Component": model_id}
                    )
                sync_handler = _get_httpx_client()
                sync_response = sync_handler.post(
                    url=prepared_request.url,
                    headers=prepared_request.headers,  # type: ignore
                    data=prepared_request.body,
                    stream=stream,
                )

                if sync_response.status_code != 200:
                    raise SagemakerError(
                        status_code=sync_response.status_code,
                        message=str(sync_response.read()),
                    )

                decoder = AWSEventStreamDecoder(model="")

                completion_stream = decoder.iter_bytes(
                    sync_response.iter_bytes(chunk_size=1024)
                )
                streaming_response = CustomStreamWrapper(
                    completion_stream=completion_stream,
                    model=model,
                    custom_llm_provider="sagemaker",
                    logging_obj=logging_obj,
                )

            ## LOGGING
            logging_obj.post_call(
                input=messages,
                api_key="",
                original_response=streaming_response,
                additional_args={"complete_input_dict": data},
            )
            return streaming_response

        # Non-Streaming Requests

        # Async completion
        if acompletion is True:
            return self.async_completion(
                messages=messages,
                model=model,
                custom_prompt_dict=custom_prompt_dict,
                hf_model_name=hf_model_name,
                model_response=model_response,
                encoding=encoding,
                logging_obj=logging_obj,
                model_id=model_id,
                optional_params=optional_params,
                credentials=credentials,
                aws_region_name=aws_region_name,
                headers=headers,
                litellm_params=litellm_params,
            )

        ## Non-Streaming completion CALL
        _data = sagemaker_config.transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            headers=headers,
        )
        prepared_request_args = {
            "model": model,
            "data": _data,
            "optional_params": optional_params,
            "litellm_params": litellm_params,
            "credentials": credentials,
            "aws_region_name": aws_region_name,
            "messages": messages,
        }
        prepared_request = self._prepare_request(**prepared_request_args)
        try:
            if model_id is not None:
                # Add model_id as InferenceComponentName header
                # boto3 doc: https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_runtime_InvokeEndpoint.html
                prepared_request.headers.update(
                    {"X-Amzn-SageMaker-Inference-Component": model_id}
                )

            ## LOGGING
            timeout = 300.0
            sync_handler = _get_httpx_client()
            ## LOGGING
            logging_obj.pre_call(
                input=[],
                api_key="",
                additional_args={
                    "complete_input_dict": _data,
                    "api_base": prepared_request.url,
                    "headers": prepared_request.headers,
                },
            )

            # make sync httpx post request here
            try:
                sync_response = sync_handler.post(
                    url=prepared_request.url,
                    headers=prepared_request.headers,  # type: ignore
                    data=prepared_request.body,
                    timeout=timeout,
                )

                if sync_response.status_code != 200:
                    raise SagemakerError(
                        status_code=sync_response.status_code,
                        message=sync_response.text,
                    )
            except Exception as e:
                ## LOGGING
                logging_obj.post_call(
                    input=[],
                    api_key="",
                    original_response=str(e),
                    additional_args={"complete_input_dict": _data},
                )
                raise e
        except Exception as e:
            verbose_logger.error("Sagemaker error %s", str(e))
            status_code = (
                getattr(e, "response", {})
                .get("ResponseMetadata", {})
                .get("HTTPStatusCode", 500)
            )
            error_message = (
                getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
            )
            if "Inference Component Name header is required" in error_message:
                error_message += "\n pass in via `litellm.completion(..., model_id={InferenceComponentName})`"
            raise SagemakerError(status_code=status_code, message=error_message)

        return sagemaker_config.transform_response(
            model=model,
            raw_response=sync_response,
            model_response=model_response,
            logging_obj=logging_obj,
            request_data=_data,
            messages=messages,
            optional_params=optional_params,
            encoding=encoding,
            litellm_params=litellm_params,
        )

    async def make_async_call(
        self,
        api_base: str,
        headers: dict,
        data: str,
        logging_obj,
        client=None,
    ):
        try:
            if client is None:
                client = get_async_httpx_client(
                    llm_provider=litellm.LlmProviders.SAGEMAKER
                )  # Create a new client if none provided
            response = await client.post(
                api_base,
                headers=headers,
                data=data,
                stream=True,
            )

            if response.status_code != 200:
                raise SagemakerError(
                    status_code=response.status_code, message=response.text
                )

            decoder = AWSEventStreamDecoder(model="")
            completion_stream = decoder.aiter_bytes(
                response.aiter_bytes(chunk_size=1024)
            )

            return completion_stream

            # LOGGING
            logging_obj.post_call(
                input=[],
                api_key="",
                original_response="first stream response received",
                additional_args={"complete_input_dict": data},
            )

        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise SagemakerError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise SagemakerError(status_code=408, message="Timeout error occurred.")
        except Exception as e:
            raise SagemakerError(status_code=500, message=str(e))

    async def async_streaming(
        self,
        messages: List[AllMessageValues],
        model: str,
        custom_prompt_dict: dict,
        hf_model_name: Optional[str],
        credentials,
        aws_region_name: str,
        optional_params,
        encoding,
        model_response: ModelResponse,
        model_id: Optional[str],
        logging_obj: Any,
        litellm_params: dict,
        headers: dict,
    ):
        data = await sagemaker_config.async_transform_request(
            model=model,
            messages=messages,
            optional_params={**optional_params, "stream": True},
            litellm_params=litellm_params,
            headers=headers,
        )
        asyncified_prepare_request = asyncify(self._prepare_request)
        prepared_request_args = {
            "model": model,
            "data": data,
            "optional_params": optional_params,
            "litellm_params": litellm_params,
            "credentials": credentials,
            "aws_region_name": aws_region_name,
            "messages": messages,
        }
        prepared_request = await asyncified_prepare_request(**prepared_request_args)
        if model_id is not None:  # Fixes https://github.com/BerriAI/litellm/issues/8889
            prepared_request.headers.update(
                {"X-Amzn-SageMaker-Inference-Component": model_id}
            )

        if not prepared_request.body:
            raise ValueError("Prepared request body is empty")

        completion_stream = await self.make_async_call(
            api_base=prepared_request.url,
            headers=prepared_request.headers,  # type: ignore
            data=cast(str, prepared_request.body),
            logging_obj=logging_obj,
        )
        streaming_response = CustomStreamWrapper(
            completion_stream=completion_stream,
            model=model,
            custom_llm_provider="sagemaker",
            logging_obj=logging_obj,
        )

        # LOGGING
        logging_obj.post_call(
            input=[],
            api_key="",
            original_response="first stream response received",
            additional_args={"complete_input_dict": data},
        )

        return streaming_response

    async def async_completion(
        self,
        messages: List[AllMessageValues],
        model: str,
        custom_prompt_dict: dict,
        hf_model_name: Optional[str],
        credentials,
        aws_region_name: str,
        encoding,
        model_response: ModelResponse,
        optional_params: dict,
        logging_obj: Any,
        model_id: Optional[str],
        headers: dict,
        litellm_params: dict,
    ):
        timeout = 300.0
        async_handler = get_async_httpx_client(
            llm_provider=litellm.LlmProviders.SAGEMAKER
        )

        data = await sagemaker_config.async_transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            headers=headers,
        )

        asyncified_prepare_request = asyncify(self._prepare_request)
        prepared_request_args = {
            "model": model,
            "data": data,
            "optional_params": optional_params,
            "litellm_params": litellm_params,
            "credentials": credentials,
            "aws_region_name": aws_region_name,
            "messages": messages,
        }

        prepared_request = await asyncified_prepare_request(**prepared_request_args)
        ## LOGGING
        logging_obj.pre_call(
            input=[],
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": prepared_request.url,
                "headers": prepared_request.headers,
            },
        )
        try:
            if model_id is not None:
                # Add model_id as InferenceComponentName header
                # boto3 doc: https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_runtime_InvokeEndpoint.html
                prepared_request.headers.update(
                    {"X-Amzn-SageMaker-Inference-Component": model_id}
                )
            # make async httpx post request here
            try:
                response = await async_handler.post(
                    url=prepared_request.url,
                    headers=prepared_request.headers,  # type: ignore
                    data=prepared_request.body,
                    timeout=timeout,
                )

                if response.status_code != 200:
                    raise SagemakerError(
                        status_code=response.status_code, message=response.text
                    )
            except Exception as e:
                ## LOGGING
                logging_obj.post_call(
                    input=data["inputs"],
                    api_key="",
                    original_response=str(e),
                    additional_args={"complete_input_dict": data},
                )
                raise e
        except Exception as e:
            error_message = f"{str(e)}"
            if "Inference Component Name header is required" in error_message:
                error_message += "\n pass in via `litellm.completion(..., model_id={InferenceComponentName})`"
            raise SagemakerError(status_code=500, message=error_message)
        return sagemaker_config.transform_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            request_data=data,
            messages=messages,
            optional_params=optional_params,
            encoding=encoding,
            litellm_params=litellm_params,
        )

    def embedding(
        self,
        model: str,
        input: list,
        model_response: EmbeddingResponse,
        print_verbose: Callable,
        encoding,
        logging_obj,
        optional_params: dict,
        custom_prompt_dict={},
        litellm_params=None,
        logger_fn=None,
    ):
        """
        Supports Huggingface Jumpstart embeddings like GPT-6B
        """
        ### BOTO3 INIT
        import boto3

        # pop aws_secret_access_key, aws_access_key_id, aws_region_name from kwargs, since completion calls fail with them
        aws_secret_access_key = optional_params.pop("aws_secret_access_key", None)
        aws_access_key_id = optional_params.pop("aws_access_key_id", None)
        aws_region_name = optional_params.pop("aws_region_name", None)

        if aws_access_key_id is not None:
            # uses auth params passed to completion
            # aws_access_key_id is not None, assume user is trying to auth using litellm.completion
            client = boto3.client(
                service_name="sagemaker-runtime",
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region_name,
            )
        else:
            # aws_access_key_id is None, assume user is trying to auth using env variables
            # boto3 automaticaly reads env variables

            # we need to read region name from env
            # I assume majority of users use .env for auth
            region_name = (
                get_secret("AWS_REGION_NAME")
                or aws_region_name  # get region from config file if specified
                or "us-west-2"  # default to us-west-2 if region not specified
            )
            client = boto3.client(
                service_name="sagemaker-runtime",
                region_name=region_name,
            )

        # pop streaming if it's in the optional params as 'stream' raises an error with sagemaker
        inference_params = deepcopy(optional_params)
        inference_params.pop("stream", None)

        ## Load Config
        config = litellm.SagemakerConfig.get_config()
        for k, v in config.items():
            if (
                k not in inference_params
            ):  # completion(top_k=3) > sagemaker_config(top_k=3) <- allows for dynamic variables to be passed in
                inference_params[k] = v

        #### HF EMBEDDING LOGIC
        data = json.dumps({"inputs": input}).encode("utf-8")

        ## LOGGING
        request_str = f"""
        response = client.invoke_endpoint(
            EndpointName={model},
            ContentType="application/json",
            Body=f"{data!r}",  # Use !r for safe representation
            CustomAttributes="accept_eula=true",
        )"""  # type: ignore
        logging_obj.pre_call(
            input=input,
            api_key="",
            additional_args={"complete_input_dict": data, "request_str": request_str},
        )
        ## EMBEDDING CALL
        try:
            response = client.invoke_endpoint(
                EndpointName=model,
                ContentType="application/json",
                Body=data,
                CustomAttributes="accept_eula=true",
            )
        except Exception as e:
            status_code = (
                getattr(e, "response", {})
                .get("ResponseMetadata", {})
                .get("HTTPStatusCode", 500)
            )
            error_message = (
                getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
            )
            raise SagemakerError(status_code=status_code, message=error_message)

        response = json.loads(response["Body"].read().decode("utf8"))
        ## LOGGING
        logging_obj.post_call(
            input=input,
            api_key="",
            original_response=response,
            additional_args={"complete_input_dict": data},
        )

        print_verbose(f"raw model_response: {response}")
        if "embedding" not in response:
            raise SagemakerError(
                status_code=500, message="embedding not found in response"
            )
        embeddings = response["embedding"]

        if not isinstance(embeddings, list):
            raise SagemakerError(
                status_code=422,
                message=f"Response not in expected format - {embeddings}",
            )

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
            Usage(
                prompt_tokens=input_tokens,
                completion_tokens=0,
                total_tokens=input_tokens,
            ),
        )

        return model_response

# === NexusCore/openenv\Lib\site-packages\urllib3\contrib\emscripten\fetch.py ===
"""
Support for streaming http requests in emscripten.

A few caveats -

If your browser (or Node.js) has WebAssembly JavaScript Promise Integration enabled
https://github.com/WebAssembly/js-promise-integration/blob/main/proposals/js-promise-integration/Overview.md
*and* you launch pyodide using `pyodide.runPythonAsync`, this will fetch data using the
JavaScript asynchronous fetch api (wrapped via `pyodide.ffi.call_sync`). In this case
timeouts and streaming should just work.

Otherwise, it uses a combination of XMLHttpRequest and a web-worker for streaming.

This approach has several caveats:

Firstly, you can't do streaming http in the main UI thread, because atomics.wait isn't allowed.
Streaming only works if you're running pyodide in a web worker.

Secondly, this uses an extra web worker and SharedArrayBuffer to do the asynchronous fetch
operation, so it requires that you have crossOriginIsolation enabled, by serving over https
(or from localhost) with the two headers below set:

    Cross-Origin-Opener-Policy: same-origin
    Cross-Origin-Embedder-Policy: require-corp

You can tell if cross origin isolation is successfully enabled by looking at the global crossOriginIsolated variable in
JavaScript console. If it isn't, streaming requests will fallback to XMLHttpRequest, i.e. getting the whole
request into a buffer and then returning it. it shows a warning in the JavaScript console in this case.

Finally, the webworker which does the streaming fetch is created on initial import, but will only be started once
control is returned to javascript. Call `await wait_for_streaming_ready()` to wait for streaming fetch.

NB: in this code, there are a lot of JavaScript objects. They are named js_*
to make it clear what type of object they are.
"""

from __future__ import annotations

import io
import json
from email.parser import Parser
from importlib.resources import files
from typing import TYPE_CHECKING, Any

import js  # type: ignore[import-not-found]
from pyodide.ffi import (  # type: ignore[import-not-found]
    JsArray,
    JsException,
    JsProxy,
    to_js,
)

if TYPE_CHECKING:
    from typing_extensions import Buffer

from .request import EmscriptenRequest
from .response import EmscriptenResponse

"""
There are some headers that trigger unintended CORS preflight requests.
See also https://github.com/koenvo/pyodide-http/issues/22
"""
HEADERS_TO_IGNORE = ("user-agent",)

SUCCESS_HEADER = -1
SUCCESS_EOF = -2
ERROR_TIMEOUT = -3
ERROR_EXCEPTION = -4

_STREAMING_WORKER_CODE = (
    files(__package__)
    .joinpath("emscripten_fetch_worker.js")
    .read_text(encoding="utf-8")
)


class _RequestError(Exception):
    def __init__(
        self,
        message: str | None = None,
        *,
        request: EmscriptenRequest | None = None,
        response: EmscriptenResponse | None = None,
    ):
        self.request = request
        self.response = response
        self.message = message
        super().__init__(self.message)


class _StreamingError(_RequestError):
    pass


class _TimeoutError(_RequestError):
    pass


def _obj_from_dict(dict_val: dict[str, Any]) -> JsProxy:
    return to_js(dict_val, dict_converter=js.Object.fromEntries)


class _ReadStream(io.RawIOBase):
    def __init__(
        self,
        int_buffer: JsArray,
        byte_buffer: JsArray,
        timeout: float,
        worker: JsProxy,
        connection_id: int,
        request: EmscriptenRequest,
    ):
        self.int_buffer = int_buffer
        self.byte_buffer = byte_buffer
        self.read_pos = 0
        self.read_len = 0
        self.connection_id = connection_id
        self.worker = worker
        self.timeout = int(1000 * timeout) if timeout > 0 else None
        self.is_live = True
        self._is_closed = False
        self.request: EmscriptenRequest | None = request

    def __del__(self) -> None:
        self.close()

    # this is compatible with _base_connection
    def is_closed(self) -> bool:
        return self._is_closed

    # for compatibility with RawIOBase
    @property
    def closed(self) -> bool:
        return self.is_closed()

    def close(self) -> None:
        if self.is_closed():
            return
        self.read_len = 0
        self.read_pos = 0
        self.int_buffer = None
        self.byte_buffer = None
        self._is_closed = True
        self.request = None
        if self.is_live:
            self.worker.postMessage(_obj_from_dict({"close": self.connection_id}))
            self.is_live = False
        super().close()

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    def readinto(self, byte_obj: Buffer) -> int:
        if not self.int_buffer:
            raise _StreamingError(
                "No buffer for stream in _ReadStream.readinto",
                request=self.request,
                response=None,
            )
        if self.read_len == 0:
            # wait for the worker to send something
            js.Atomics.store(self.int_buffer, 0, ERROR_TIMEOUT)
            self.worker.postMessage(_obj_from_dict({"getMore": self.connection_id}))
            if (
                js.Atomics.wait(self.int_buffer, 0, ERROR_TIMEOUT, self.timeout)
                == "timed-out"
            ):
                raise _TimeoutError
            data_len = self.int_buffer[0]
            if data_len > 0:
                self.read_len = data_len
                self.read_pos = 0
            elif data_len == ERROR_EXCEPTION:
                string_len = self.int_buffer[1]
                # decode the error string
                js_decoder = js.TextDecoder.new()
                json_str = js_decoder.decode(self.byte_buffer.slice(0, string_len))
                raise _StreamingError(
                    f"Exception thrown in fetch: {json_str}",
                    request=self.request,
                    response=None,
                )
            else:
                # EOF, free the buffers and return zero
                # and free the request
                self.is_live = False
                self.close()
                return 0
        # copy from int32array to python bytes
        ret_length = min(self.read_len, len(memoryview(byte_obj)))
        subarray = self.byte_buffer.subarray(
            self.read_pos, self.read_pos + ret_length
        ).to_py()
        memoryview(byte_obj)[0:ret_length] = subarray
        self.read_len -= ret_length
        self.read_pos += ret_length
        return ret_length


class _StreamingFetcher:
    def __init__(self) -> None:
        # make web-worker and data buffer on startup
        self.streaming_ready = False

        js_data_blob = js.Blob.new(
            to_js([_STREAMING_WORKER_CODE], create_pyproxies=False),
            _obj_from_dict({"type": "application/javascript"}),
        )

        def promise_resolver(js_resolve_fn: JsProxy, js_reject_fn: JsProxy) -> None:
            def onMsg(e: JsProxy) -> None:
                self.streaming_ready = True
                js_resolve_fn(e)

            def onErr(e: JsProxy) -> None:
                js_reject_fn(e)  # Defensive: never happens in ci

            self.js_worker.onmessage = onMsg
            self.js_worker.onerror = onErr

        js_data_url = js.URL.createObjectURL(js_data_blob)
        self.js_worker = js.globalThis.Worker.new(js_data_url)
        self.js_worker_ready_promise = js.globalThis.Promise.new(promise_resolver)

    def send(self, request: EmscriptenRequest) -> EmscriptenResponse:
        headers = {
            k: v for k, v in request.headers.items() if k not in HEADERS_TO_IGNORE
        }

        body = request.body
        fetch_data = {"headers": headers, "body": to_js(body), "method": request.method}
        # start the request off in the worker
        timeout = int(1000 * request.timeout) if request.timeout > 0 else None
        js_shared_buffer = js.SharedArrayBuffer.new(1048576)
        js_int_buffer = js.Int32Array.new(js_shared_buffer)
        js_byte_buffer = js.Uint8Array.new(js_shared_buffer, 8)

        js.Atomics.store(js_int_buffer, 0, ERROR_TIMEOUT)
        js.Atomics.notify(js_int_buffer, 0)
        js_absolute_url = js.URL.new(request.url, js.location).href
        self.js_worker.postMessage(
            _obj_from_dict(
                {
                    "buffer": js_shared_buffer,
                    "url": js_absolute_url,
                    "fetchParams": fetch_data,
                }
            )
        )
        # wait for the worker to send something
        js.Atomics.wait(js_int_buffer, 0, ERROR_TIMEOUT, timeout)
        if js_int_buffer[0] == ERROR_TIMEOUT:
            raise _TimeoutError(
                "Timeout connecting to streaming request",
                request=request,
                response=None,
            )
        elif js_int_buffer[0] == SUCCESS_HEADER:
            # got response
            # header length is in second int of intBuffer
            string_len = js_int_buffer[1]
            # decode the rest to a JSON string
            js_decoder = js.TextDecoder.new()
            # this does a copy (the slice) because decode can't work on shared array
            # for some silly reason
            json_str = js_decoder.decode(js_byte_buffer.slice(0, string_len))
            # get it as an object
            response_obj = json.loads(json_str)
            return EmscriptenResponse(
                request=request,
                status_code=response_obj["status"],
                headers=response_obj["headers"],
                body=_ReadStream(
                    js_int_buffer,
                    js_byte_buffer,
                    request.timeout,
                    self.js_worker,
                    response_obj["connectionID"],
                    request,
                ),
            )
        elif js_int_buffer[0] == ERROR_EXCEPTION:
            string_len = js_int_buffer[1]
            # decode the error string
            js_decoder = js.TextDecoder.new()
            json_str = js_decoder.decode(js_byte_buffer.slice(0, string_len))
            raise _StreamingError(
                f"Exception thrown in fetch: {json_str}", request=request, response=None
            )
        else:
            raise _StreamingError(
                f"Unknown status from worker in fetch: {js_int_buffer[0]}",
                request=request,
                response=None,
            )


class _JSPIReadStream(io.RawIOBase):
    """
    A read stream that uses pyodide.ffi.run_sync to read from a JavaScript fetch
    response. This requires support for WebAssembly JavaScript Promise Integration
    in the containing browser, and for pyodide to be launched via runPythonAsync.

    :param js_read_stream:
        The JavaScript stream reader

    :param timeout:
        Timeout in seconds

    :param request:
        The request we're handling

    :param response:
        The response this stream relates to

    :param js_abort_controller:
        A JavaScript AbortController object, used for timeouts
    """

    def __init__(
        self,
        js_read_stream: Any,
        timeout: float,
        request: EmscriptenRequest,
        response: EmscriptenResponse,
        js_abort_controller: Any,  # JavaScript AbortController for timeouts
    ):
        self.js_read_stream = js_read_stream
        self.timeout = timeout
        self._is_closed = False
        self._is_done = False
        self.request: EmscriptenRequest | None = request
        self.response: EmscriptenResponse | None = response
        self.current_buffer = None
        self.current_buffer_pos = 0
        self.js_abort_controller = js_abort_controller

    def __del__(self) -> None:
        self.close()

    # this is compatible with _base_connection
    def is_closed(self) -> bool:
        return self._is_closed

    # for compatibility with RawIOBase
    @property
    def closed(self) -> bool:
        return self.is_closed()

    def close(self) -> None:
        if self.is_closed():
            return
        self.read_len = 0
        self.read_pos = 0
        self.js_read_stream.cancel()
        self.js_read_stream = None
        self._is_closed = True
        self._is_done = True
        self.request = None
        self.response = None
        super().close()

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    def _get_next_buffer(self) -> bool:
        result_js = _run_sync_with_timeout(
            self.js_read_stream.read(),
            self.timeout,
            self.js_abort_controller,
            request=self.request,
            response=self.response,
        )
        if result_js.done:
            self._is_done = True
            return False
        else:
            self.current_buffer = result_js.value.to_py()
            self.current_buffer_pos = 0
            return True

    def readinto(self, byte_obj: Buffer) -> int:
        if self.current_buffer is None:
            if not self._get_next_buffer() or self.current_buffer is None:
                self.close()
                return 0
        ret_length = min(
            len(byte_obj), len(self.current_buffer) - self.current_buffer_pos
        )
        byte_obj[0:ret_length] = self.current_buffer[
            self.current_buffer_pos : self.current_buffer_pos + ret_length
        ]
        self.current_buffer_pos += ret_length
        if self.current_buffer_pos == len(self.current_buffer):
            self.current_buffer = None
        return ret_length


# check if we are in a worker or not
def is_in_browser_main_thread() -> bool:
    return hasattr(js, "window") and hasattr(js, "self") and js.self == js.window


def is_cross_origin_isolated() -> bool:
    return hasattr(js, "crossOriginIsolated") and js.crossOriginIsolated


def is_in_node() -> bool:
    return (
        hasattr(js, "process")
        and hasattr(js.process, "release")
        and hasattr(js.process.release, "name")
        and js.process.release.name == "node"
    )


def is_worker_available() -> bool:
    return hasattr(js, "Worker") and hasattr(js, "Blob")


_fetcher: _StreamingFetcher | None = None

if is_worker_available() and (
    (is_cross_origin_isolated() and not is_in_browser_main_thread())
    and (not is_in_node())
):
    _fetcher = _StreamingFetcher()
else:
    _fetcher = None


NODE_JSPI_ERROR = (
    "urllib3 only works in Node.js with pyodide.runPythonAsync"
    " and requires the flag --experimental-wasm-stack-switching in "
    " versions of node <24."
)


def send_streaming_request(request: EmscriptenRequest) -> EmscriptenResponse | None:
    if has_jspi():
        return send_jspi_request(request, True)
    elif is_in_node():
        raise _RequestError(
            message=NODE_JSPI_ERROR,
            request=request,
            response=None,
        )

    if _fetcher and streaming_ready():
        return _fetcher.send(request)
    else:
        _show_streaming_warning()
        return None


_SHOWN_TIMEOUT_WARNING = False


def _show_timeout_warning() -> None:
    global _SHOWN_TIMEOUT_WARNING
    if not _SHOWN_TIMEOUT_WARNING:
        _SHOWN_TIMEOUT_WARNING = True
        message = "Warning: Timeout is not available on main browser thread"
        js.console.warn(message)


_SHOWN_STREAMING_WARNING = False


def _show_streaming_warning() -> None:
    global _SHOWN_STREAMING_WARNING
    if not _SHOWN_STREAMING_WARNING:
        _SHOWN_STREAMING_WARNING = True
        message = "Can't stream HTTP requests because: \n"
        if not is_cross_origin_isolated():
            message += "  Page is not cross-origin isolated\n"
        if is_in_browser_main_thread():
            message += "  Python is running in main browser thread\n"
        if not is_worker_available():
            message += " Worker or Blob classes are not available in this environment."  # Defensive: this is always False in browsers that we test in
        if streaming_ready() is False:
            message += """ Streaming fetch worker isn't ready. If you want to be sure that streaming fetch
is working, you need to call: 'await urllib3.contrib.emscripten.fetch.wait_for_streaming_ready()`"""
        from js import console

        console.warn(message)


def send_request(request: EmscriptenRequest) -> EmscriptenResponse:
    if has_jspi():
        return send_jspi_request(request, False)
    elif is_in_node():
        raise _RequestError(
            message=NODE_JSPI_ERROR,
            request=request,
            response=None,
        )
    try:
        js_xhr = js.XMLHttpRequest.new()

        if not is_in_browser_main_thread():
            js_xhr.responseType = "arraybuffer"
            if request.timeout:
                js_xhr.timeout = int(request.timeout * 1000)
        else:
            js_xhr.overrideMimeType("text/plain; charset=ISO-8859-15")
            if request.timeout:
                # timeout isn't available on the main thread - show a warning in console
                # if it is set
                _show_timeout_warning()

        js_xhr.open(request.method, request.url, False)
        for name, value in request.headers.items():
            if name.lower() not in HEADERS_TO_IGNORE:
                js_xhr.setRequestHeader(name, value)

        js_xhr.send(to_js(request.body))

        headers = dict(Parser().parsestr(js_xhr.getAllResponseHeaders()))

        if not is_in_browser_main_thread():
            body = js_xhr.response.to_py().tobytes()
        else:
            body = js_xhr.response.encode("ISO-8859-15")
        return EmscriptenResponse(
            status_code=js_xhr.status, headers=headers, body=body, request=request
        )
    except JsException as err:
        if err.name == "TimeoutError":
            raise _TimeoutError(err.message, request=request)
        elif err.name == "NetworkError":
            raise _RequestError(err.message, request=request)
        else:
            # general http error
            raise _RequestError(err.message, request=request)


def send_jspi_request(
    request: EmscriptenRequest, streaming: bool
) -> EmscriptenResponse:
    """
    Send a request using WebAssembly JavaScript Promise Integration
    to wrap the asynchronous JavaScript fetch api (experimental).

    :param request:
        Request to send

    :param streaming:
        Whether to stream the response

    :return: The response object
    :rtype: EmscriptenResponse
    """
    timeout = request.timeout
    js_abort_controller = js.AbortController.new()
    headers = {k: v for k, v in request.headers.items() if k not in HEADERS_TO_IGNORE}
    req_body = request.body
    fetch_data = {
        "headers": headers,
        "body": to_js(req_body),
        "method": request.method,
        "signal": js_abort_controller.signal,
    }
    # Call JavaScript fetch (async api, returns a promise)
    fetcher_promise_js = js.fetch(request.url, _obj_from_dict(fetch_data))
    # Now suspend WebAssembly until we resolve that promise
    # or time out.
    response_js = _run_sync_with_timeout(
        fetcher_promise_js,
        timeout,
        js_abort_controller,
        request=request,
        response=None,
    )
    headers = {}
    header_iter = response_js.headers.entries()
    while True:
        iter_value_js = header_iter.next()
        if getattr(iter_value_js, "done", False):
            break
        else:
            headers[str(iter_value_js.value[0])] = str(iter_value_js.value[1])
    status_code = response_js.status
    body: bytes | io.RawIOBase = b""

    response = EmscriptenResponse(
        status_code=status_code, headers=headers, body=b"", request=request
    )
    if streaming:
        # get via inputstream
        if response_js.body is not None:
            # get a reader from the fetch response
            body_stream_js = response_js.body.getReader()
            body = _JSPIReadStream(
                body_stream_js, timeout, request, response, js_abort_controller
            )
    else:
        # get directly via arraybuffer
        # n.b. this is another async JavaScript call.
        body = _run_sync_with_timeout(
            response_js.arrayBuffer(),
            timeout,
            js_abort_controller,
            request=request,
            response=response,
        ).to_py()
    response.body = body
    return response


def _run_sync_with_timeout(
    promise: Any,
    timeout: float,
    js_abort_controller: Any,
    request: EmscriptenRequest | None,
    response: EmscriptenResponse | None,
) -> Any:
    """
    Await a JavaScript promise synchronously with a timeout which is implemented
    via the AbortController

    :param promise:
        Javascript promise to await

    :param timeout:
        Timeout in seconds

    :param js_abort_controller:
        A JavaScript AbortController object, used on timeout

    :param request:
        The request being handled

    :param response:
        The response being handled (if it exists yet)

    :raises _TimeoutError: If the request times out
    :raises _RequestError: If the request raises a JavaScript exception

    :return: The result of awaiting the promise.
    """
    timer_id = None
    if timeout > 0:
        timer_id = js.setTimeout(
            js_abort_controller.abort.bind(js_abort_controller), int(timeout * 1000)
        )
    try:
        from pyodide.ffi import run_sync

        # run_sync here uses WebAssembly JavaScript Promise Integration to
        # suspend python until the JavaScript promise resolves.
        return run_sync(promise)
    except JsException as err:
        if err.name == "AbortError":
            raise _TimeoutError(
                message="Request timed out", request=request, response=response
            )
        else:
            raise _RequestError(message=err.message, request=request, response=response)
    finally:
        if timer_id is not None:
            js.clearTimeout(timer_id)


def has_jspi() -> bool:
    """
    Return true if jspi can be used.

    This requires both browser support and also WebAssembly
    to be in the correct state - i.e. that the javascript
    call into python was async not sync.

    :return: True if jspi can be used.
    :rtype: bool
    """
    try:
        from pyodide.ffi import can_run_sync, run_sync  # noqa: F401

        return bool(can_run_sync())
    except ImportError:
        return False


def streaming_ready() -> bool | None:
    if _fetcher:
        return _fetcher.streaming_ready
    else:
        return None  # no fetcher, return None to signify that


async def wait_for_streaming_ready() -> bool:
    if _fetcher:
        await _fetcher.js_worker_ready_promise
        return True
    else:
        return False

# === NexusCore/openenv\Lib\site-packages\IPython\core\prefilter.py ===
# encoding: utf-8
"""
Prefiltering components.

Prefilters transform user input before it is exec'd by Python.  These
transforms are used to implement additional syntax such as !ls and %magic.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from keyword import iskeyword
import re

from .autocall import IPyAutocall
from traitlets.config.configurable import Configurable
from .inputtransformer2 import (
    ESC_MAGIC,
    ESC_QUOTE,
    ESC_QUOTE2,
    ESC_PAREN,
)
from .macro import Macro
from .splitinput import LineInfo

from traitlets import (
    List, Integer, Unicode, Bool, Instance, CRegExp
)

#-----------------------------------------------------------------------------
# Global utilities, errors and constants
#-----------------------------------------------------------------------------


class PrefilterError(Exception):
    pass


# RegExp to identify potential function names
re_fun_name = re.compile(r'[^\W\d]([\w.]*) *$')

# RegExp to exclude strings with this start from autocalling.  In
# particular, all binary operators should be excluded, so that if foo is
# callable, foo OP bar doesn't become foo(OP bar), which is invalid.  The
# characters '!=()' don't need to be checked for, as the checkPythonChars
# routine explicitly does so, to catch direct calls and rebindings of
# existing names.

# Warning: the '-' HAS TO BE AT THE END of the first group, otherwise
# it affects the rest of the group in square brackets.
re_exclude_auto = re.compile(r'^[,&^\|\*/\+-]'
                             r'|^is |^not |^in |^and |^or ')

# try to catch also methods for stuff in lists/tuples/dicts: off
# (experimental). For this to work, the line_split regexp would need
# to be modified so it wouldn't break things at '['. That line is
# nasty enough that I shouldn't change it until I can test it _well_.
#self.re_fun_name = re.compile (r'[a-zA-Z_]([a-zA-Z0-9_.\[\]]*) ?$')


# Handler Check Utilities
def is_shadowed(identifier, ip):
    """Is the given identifier defined in one of the namespaces which shadow
    the alias and magic namespaces?  Note that an identifier is different
    than ifun, because it can not contain a '.' character."""
    # This is much safer than calling ofind, which can change state
    return (identifier in ip.user_ns \
            or identifier in ip.user_global_ns \
            or identifier in ip.ns_table['builtin']\
            or iskeyword(identifier))


#-----------------------------------------------------------------------------
# Main Prefilter manager
#-----------------------------------------------------------------------------


class PrefilterManager(Configurable):
    """Main prefilter component.

    The IPython prefilter is run on all user input before it is run.  The
    prefilter consumes lines of input and produces transformed lines of
    input.

    The implementation consists of two phases:

    1. Transformers
    2. Checkers and handlers

    Over time, we plan on deprecating the checkers and handlers and doing
    everything in the transformers.

    The transformers are instances of :class:`PrefilterTransformer` and have
    a single method :meth:`transform` that takes a line and returns a
    transformed line.  The transformation can be accomplished using any
    tool, but our current ones use regular expressions for speed.

    After all the transformers have been run, the line is fed to the checkers,
    which are instances of :class:`PrefilterChecker`.  The line is passed to
    the :meth:`check` method, which either returns `None` or a
    :class:`PrefilterHandler` instance.  If `None` is returned, the other
    checkers are tried.  If an :class:`PrefilterHandler` instance is returned,
    the line is passed to the :meth:`handle` method of the returned
    handler and no further checkers are tried.

    Both transformers and checkers have a `priority` attribute, that determines
    the order in which they are called.  Smaller priorities are tried first.

    Both transformers and checkers also have `enabled` attribute, which is
    a boolean that determines if the instance is used.

    Users or developers can change the priority or enabled attribute of
    transformers or checkers, but they must call the :meth:`sort_checkers`
    or :meth:`sort_transformers` method after changing the priority.
    """

    multi_line_specials = Bool(True).tag(config=True)
    shell = Instance('IPython.core.interactiveshell.InteractiveShellABC', allow_none=True)

    def __init__(self, shell=None, **kwargs):
        super(PrefilterManager, self).__init__(shell=shell, **kwargs)
        self.shell = shell
        self._transformers = []
        self.init_handlers()
        self.init_checkers()

    #-------------------------------------------------------------------------
    # API for managing transformers
    #-------------------------------------------------------------------------

    def sort_transformers(self):
        """Sort the transformers by priority.

        This must be called after the priority of a transformer is changed.
        The :meth:`register_transformer` method calls this automatically.
        """
        self._transformers.sort(key=lambda x: x.priority)

    @property
    def transformers(self):
        """Return a list of checkers, sorted by priority."""
        return self._transformers

    def register_transformer(self, transformer):
        """Register a transformer instance."""
        if transformer not in self._transformers:
            self._transformers.append(transformer)
            self.sort_transformers()

    def unregister_transformer(self, transformer):
        """Unregister a transformer instance."""
        if transformer in self._transformers:
            self._transformers.remove(transformer)

    #-------------------------------------------------------------------------
    # API for managing checkers
    #-------------------------------------------------------------------------

    def init_checkers(self):
        """Create the default checkers."""
        self._checkers = []
        for checker in _default_checkers:
            checker(
                shell=self.shell, prefilter_manager=self, parent=self
            )

    def sort_checkers(self):
        """Sort the checkers by priority.

        This must be called after the priority of a checker is changed.
        The :meth:`register_checker` method calls this automatically.
        """
        self._checkers.sort(key=lambda x: x.priority)

    @property
    def checkers(self):
        """Return a list of checkers, sorted by priority."""
        return self._checkers

    def register_checker(self, checker):
        """Register a checker instance."""
        if checker not in self._checkers:
            self._checkers.append(checker)
            self.sort_checkers()

    def unregister_checker(self, checker):
        """Unregister a checker instance."""
        if checker in self._checkers:
            self._checkers.remove(checker)

    #-------------------------------------------------------------------------
    # API for managing handlers
    #-------------------------------------------------------------------------

    def init_handlers(self):
        """Create the default handlers."""
        self._handlers = {}
        self._esc_handlers = {}
        for handler in _default_handlers:
            handler(
                shell=self.shell, prefilter_manager=self, parent=self
            )

    @property
    def handlers(self):
        """Return a dict of all the handlers."""
        return self._handlers

    def register_handler(self, name, handler, esc_strings):
        """Register a handler instance by name with esc_strings."""
        self._handlers[name] = handler
        for esc_str in esc_strings:
            self._esc_handlers[esc_str] = handler

    def unregister_handler(self, name, handler, esc_strings):
        """Unregister a handler instance by name with esc_strings."""
        try:
            del self._handlers[name]
        except KeyError:
            pass
        for esc_str in esc_strings:
            h = self._esc_handlers.get(esc_str)
            if h is handler:
                del self._esc_handlers[esc_str]

    def get_handler_by_name(self, name):
        """Get a handler by its name."""
        return self._handlers.get(name)

    def get_handler_by_esc(self, esc_str):
        """Get a handler by its escape string."""
        return self._esc_handlers.get(esc_str)

    #-------------------------------------------------------------------------
    # Main prefiltering API
    #-------------------------------------------------------------------------

    def prefilter_line_info(self, line_info):
        """Prefilter a line that has been converted to a LineInfo object.

        This implements the checker/handler part of the prefilter pipe.
        """
        # print("prefilter_line_info: ", line_info)
        handler = self.find_handler(line_info)
        return handler.handle(line_info)

    def find_handler(self, line_info):
        """Find a handler for the line_info by trying checkers."""
        for checker in self.checkers:
            if checker.enabled:
                handler = checker.check(line_info)
                if handler:
                    return handler
        return self.get_handler_by_name('normal')

    def transform_line(self, line, continue_prompt):
        """Calls the enabled transformers in order of increasing priority."""
        for transformer in self.transformers:
            if transformer.enabled:
                line = transformer.transform(line, continue_prompt)
        return line

    def prefilter_line(self, line, continue_prompt=False):
        """Prefilter a single input line as text.

        This method prefilters a single line of text by calling the
        transformers and then the checkers/handlers.
        """

        # print("prefilter_line: ", line, continue_prompt)
        # All handlers *must* return a value, even if it's blank ('').

        # save the line away in case we crash, so the post-mortem handler can
        # record it
        self.shell._last_input_line = line

        if not line:
            # Return immediately on purely empty lines, so that if the user
            # previously typed some whitespace that started a continuation
            # prompt, he can break out of that loop with just an empty line.
            # This is how the default python prompt works.
            return ''

        # At this point, we invoke our transformers.
        if not continue_prompt or (continue_prompt and self.multi_line_specials):
            line = self.transform_line(line, continue_prompt)

        # Now we compute line_info for the checkers and handlers
        line_info = LineInfo(line, continue_prompt)

        # the input history needs to track even empty lines
        stripped = line.strip()

        normal_handler = self.get_handler_by_name('normal')
        if not stripped:
            return normal_handler.handle(line_info)

        # special handlers are only allowed for single line statements
        if continue_prompt and not self.multi_line_specials:
            return normal_handler.handle(line_info)

        prefiltered = self.prefilter_line_info(line_info)
        # print("prefiltered line: %r" % prefiltered)
        return prefiltered

    def prefilter_lines(self, lines, continue_prompt=False):
        """Prefilter multiple input lines of text.

        This is the main entry point for prefiltering multiple lines of
        input.  This simply calls :meth:`prefilter_line` for each line of
        input.

        This covers cases where there are multiple lines in the user entry,
        which is the case when the user goes back to a multiline history
        entry and presses enter.
        """
        llines = lines.rstrip('\n').split('\n')
        # We can get multiple lines in one shot, where multiline input 'blends'
        # into one line, in cases like recalling from the readline history
        # buffer.  We need to make sure that in such cases, we correctly
        # communicate downstream which line is first and which are continuation
        # ones.
        if len(llines) > 1:
            out = '\n'.join([self.prefilter_line(line, lnum>0)
                             for lnum, line in enumerate(llines) ])
        else:
            out = self.prefilter_line(llines[0], continue_prompt)

        return out

#-----------------------------------------------------------------------------
# Prefilter transformers
#-----------------------------------------------------------------------------


class PrefilterTransformer(Configurable):
    """Transform a line of user input."""

    priority = Integer(100).tag(config=True)
    # Transformers don't currently use shell or prefilter_manager, but as we
    # move away from checkers and handlers, they will need them.
    shell = Instance('IPython.core.interactiveshell.InteractiveShellABC', allow_none=True)
    prefilter_manager = Instance('IPython.core.prefilter.PrefilterManager', allow_none=True)
    enabled = Bool(True).tag(config=True)

    def __init__(self, shell=None, prefilter_manager=None, **kwargs):
        super(PrefilterTransformer, self).__init__(
            shell=shell, prefilter_manager=prefilter_manager, **kwargs
        )
        self.prefilter_manager.register_transformer(self)

    def transform(self, line, continue_prompt):
        """Transform a line, returning the new one."""
        return None

    def __repr__(self):
        return "<%s(priority=%r, enabled=%r)>" % (
            self.__class__.__name__, self.priority, self.enabled)


#-----------------------------------------------------------------------------
# Prefilter checkers
#-----------------------------------------------------------------------------


class PrefilterChecker(Configurable):
    """Inspect an input line and return a handler for that line."""

    priority = Integer(100).tag(config=True)
    shell = Instance('IPython.core.interactiveshell.InteractiveShellABC', allow_none=True)
    prefilter_manager = Instance('IPython.core.prefilter.PrefilterManager', allow_none=True)
    enabled = Bool(True).tag(config=True)

    def __init__(self, shell=None, prefilter_manager=None, **kwargs):
        super(PrefilterChecker, self).__init__(
            shell=shell, prefilter_manager=prefilter_manager, **kwargs
        )
        self.prefilter_manager.register_checker(self)

    def check(self, line_info):
        """Inspect line_info and return a handler instance or None."""
        return None

    def __repr__(self):
        return "<%s(priority=%r, enabled=%r)>" % (
            self.__class__.__name__, self.priority, self.enabled)


class EmacsChecker(PrefilterChecker):

    priority = Integer(100).tag(config=True)
    enabled = Bool(False).tag(config=True)

    def check(self, line_info):
        "Emacs ipython-mode tags certain input lines."
        if line_info.line.endswith('# PYTHON-MODE'):
            return self.prefilter_manager.get_handler_by_name('emacs')
        else:
            return None


class MacroChecker(PrefilterChecker):

    priority = Integer(250).tag(config=True)

    def check(self, line_info):
        obj = self.shell.user_ns.get(line_info.ifun)
        if isinstance(obj, Macro):
            return self.prefilter_manager.get_handler_by_name('macro')
        else:
            return None


class IPyAutocallChecker(PrefilterChecker):

    priority = Integer(300).tag(config=True)

    def check(self, line_info):
        "Instances of IPyAutocall in user_ns get autocalled immediately"
        obj = self.shell.user_ns.get(line_info.ifun, None)
        if isinstance(obj, IPyAutocall):
            obj.set_ip(self.shell)
            return self.prefilter_manager.get_handler_by_name('auto')
        else:
            return None


class AssignmentChecker(PrefilterChecker):

    priority = Integer(600).tag(config=True)

    def check(self, line_info):
        """Check to see if user is assigning to a var for the first time, in
        which case we want to avoid any sort of automagic / autocall games.

        This allows users to assign to either alias or magic names true python
        variables (the magic/alias systems always take second seat to true
        python code).  E.g. ls='hi', or ls,that=1,2"""
        if line_info.the_rest:
            if line_info.the_rest[0] in '=,':
                return self.prefilter_manager.get_handler_by_name('normal')
        else:
            return None


class AutoMagicChecker(PrefilterChecker):

    priority = Integer(700).tag(config=True)

    def check(self, line_info):
        """If the ifun is magic, and automagic is on, run it.  Note: normal,
        non-auto magic would already have been triggered via '%' in
        check_esc_chars. This just checks for automagic.  Also, before
        triggering the magic handler, make sure that there is nothing in the
        user namespace which could shadow it."""
        if not self.shell.automagic or not self.shell.find_magic(line_info.ifun):
            return None

        # We have a likely magic method.  Make sure we should actually call it.
        if line_info.continue_prompt and not self.prefilter_manager.multi_line_specials:
            return None

        head = line_info.ifun.split('.',1)[0]
        if is_shadowed(head, self.shell):
            return None

        return self.prefilter_manager.get_handler_by_name('magic')


class PythonOpsChecker(PrefilterChecker):

    priority = Integer(900).tag(config=True)

    def check(self, line_info):
        """If the 'rest' of the line begins with a function call or pretty much
        any python operator, we should simply execute the line (regardless of
        whether or not there's a possible autocall expansion).  This avoids
        spurious (and very confusing) geattr() accesses."""
        if line_info.the_rest and line_info.the_rest[0] in "!=()<>,+*/%^&|":
            return self.prefilter_manager.get_handler_by_name("normal")
        else:
            return None


class AutocallChecker(PrefilterChecker):

    priority = Integer(1000).tag(config=True)

    function_name_regexp = CRegExp(re_fun_name,
        help="RegExp to identify potential function names."
        ).tag(config=True)
    exclude_regexp = CRegExp(re_exclude_auto,
        help="RegExp to exclude strings with this start from autocalling."
        ).tag(config=True)

    def check(self, line_info):
        "Check if the initial word/function is callable and autocall is on."
        if not self.shell.autocall:
            return None

        oinfo = line_info.ofind(self.shell) # This can mutate state via getattr
        if not oinfo.found:
            return None

        ignored_funs = ['b', 'f', 'r', 'u', 'br', 'rb', 'fr', 'rf']
        ifun = line_info.ifun
        line = line_info.line
        if ifun.lower() in ignored_funs and (line.startswith(ifun + "'") or line.startswith(ifun + '"')):
            return None

        if (
            callable(oinfo.obj)
            and (not self.exclude_regexp.match(line_info.the_rest))
            and self.function_name_regexp.match(line_info.ifun)
            and (
                line_info.raw_the_rest.startswith(" ")
                or not line_info.raw_the_rest.strip()
            )
        ):
            return self.prefilter_manager.get_handler_by_name("auto")
        else:
            return None


#-----------------------------------------------------------------------------
# Prefilter handlers
#-----------------------------------------------------------------------------


class PrefilterHandler(Configurable):
    handler_name = Unicode("normal")
    esc_strings: List = List([])
    shell = Instance(
        "IPython.core.interactiveshell.InteractiveShellABC", allow_none=True
    )
    prefilter_manager = Instance(
        "IPython.core.prefilter.PrefilterManager", allow_none=True
    )

    def __init__(self, shell=None, prefilter_manager=None, **kwargs):
        super(PrefilterHandler, self).__init__(
            shell=shell, prefilter_manager=prefilter_manager, **kwargs
        )
        self.prefilter_manager.register_handler(
            self.handler_name,
            self,
            self.esc_strings
        )

    def handle(self, line_info):
        # print("normal: ", line_info)
        """Handle normal input lines. Use as a template for handlers."""

        # With autoindent on, we need some way to exit the input loop, and I
        # don't want to force the user to have to backspace all the way to
        # clear the line.  The rule will be in this case, that either two
        # lines of pure whitespace in a row, or a line of pure whitespace but
        # of a size different to the indent level, will exit the input loop.
        line = line_info.line
        continue_prompt = line_info.continue_prompt

        if (continue_prompt and
            self.shell.autoindent and
            line.isspace() and
            0 < abs(len(line) - self.shell.indent_current_nsp) <= 2):
            line = ''

        return line

    def __str__(self):
        return "<%s(name=%s)>" % (self.__class__.__name__, self.handler_name)


class MacroHandler(PrefilterHandler):
    handler_name = Unicode("macro")

    def handle(self, line_info):
        obj = self.shell.user_ns.get(line_info.ifun)
        pre_space = line_info.pre_whitespace
        line_sep = "\n" + pre_space
        return pre_space + line_sep.join(obj.value.splitlines())


class MagicHandler(PrefilterHandler):

    handler_name = Unicode('magic')
    esc_strings = List([ESC_MAGIC])

    def handle(self, line_info):
        """Execute magic functions."""
        ifun    = line_info.ifun
        the_rest = line_info.the_rest
        #Prepare arguments for get_ipython().run_line_magic(magic_name, magic_args)
        t_arg_s = ifun + " " + the_rest
        t_magic_name, _, t_magic_arg_s = t_arg_s.partition(' ')
        t_magic_name = t_magic_name.lstrip(ESC_MAGIC)
        cmd = '%sget_ipython().run_line_magic(%r, %r)' % (line_info.pre_whitespace, t_magic_name, t_magic_arg_s)
        return cmd


class AutoHandler(PrefilterHandler):

    handler_name = Unicode('auto')
    esc_strings = List([ESC_PAREN, ESC_QUOTE, ESC_QUOTE2])

    def handle(self, line_info):
        """Handle lines which can be auto-executed, quoting if requested."""
        line    = line_info.line
        ifun    = line_info.ifun
        the_rest = line_info.the_rest
        esc     = line_info.esc
        continue_prompt = line_info.continue_prompt
        obj = line_info.ofind(self.shell).obj

        # This should only be active for single-line input!
        if continue_prompt:
            return line

        force_auto = isinstance(obj, IPyAutocall)

        # User objects sometimes raise exceptions on attribute access other
        # than AttributeError (we've seen it in the past), so it's safest to be
        # ultra-conservative here and catch all.
        try:
            auto_rewrite = obj.rewrite
        except Exception:
            auto_rewrite = True

        if esc == ESC_QUOTE:
            # Auto-quote splitting on whitespace
            newcmd = '%s("%s")' % (ifun,'", "'.join(the_rest.split()) )
        elif esc == ESC_QUOTE2:
            # Auto-quote whole string
            newcmd = '%s("%s")' % (ifun,the_rest)
        elif esc == ESC_PAREN:
            newcmd = '%s(%s)' % (ifun,",".join(the_rest.split()))
        else:
            # Auto-paren.
            if force_auto:
                # Don't rewrite if it is already a call.
                do_rewrite = not the_rest.startswith('(')
            else:
                if not the_rest:
                    # We only apply it to argument-less calls if the autocall
                    # parameter is set to 2.
                    do_rewrite = (self.shell.autocall >= 2)
                elif the_rest.startswith('[') and hasattr(obj, '__getitem__'):
                    # Don't autocall in this case: item access for an object
                    # which is BOTH callable and implements __getitem__.
                    do_rewrite = False
                else:
                    do_rewrite = True

            # Figure out the rewritten command
            if do_rewrite:
                if the_rest.endswith(';'):
                    newcmd = '%s(%s);' % (ifun.rstrip(),the_rest[:-1])
                else:
                    newcmd = '%s(%s)' % (ifun.rstrip(), the_rest)
            else:
                normal_handler = self.prefilter_manager.get_handler_by_name('normal')
                return normal_handler.handle(line_info)

        # Display the rewritten call
        if auto_rewrite:
            self.shell.auto_rewrite_input(newcmd)

        return newcmd


class EmacsHandler(PrefilterHandler):

    handler_name = Unicode('emacs')
    esc_strings = List([])

    def handle(self, line_info):
        """Handle input lines marked by python-mode."""

        # Currently, nothing is done.  Later more functionality can be added
        # here if needed.

        # The input cache shouldn't be updated
        return line_info.line


#-----------------------------------------------------------------------------
# Defaults
#-----------------------------------------------------------------------------


_default_checkers = [
    EmacsChecker,
    MacroChecker,
    IPyAutocallChecker,
    AssignmentChecker,
    AutoMagicChecker,
    PythonOpsChecker,
    AutocallChecker
]

_default_handlers = [
    PrefilterHandler,
    MacroHandler,
    MagicHandler,
    AutoHandler,
    EmacsHandler
]

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\mojo.py ===
"""
    pygments.lexers.mojo
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for Mojo and related languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import keyword

from pygments import unistring as uni
from pygments.lexer import (
    RegexLexer,
    bygroups,
    combined,
    default,
    include,
    this,
    using,
    words,
)
from pygments.token import (
    Comment,
    # Error,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Whitespace,
)
from pygments.util import shebang_matches

__all__ = ["MojoLexer"]


class MojoLexer(RegexLexer):
    """
    For Mojo source code (version 24.2.1).
    """

    name = "Mojo"
    url = "https://docs.modular.com/mojo/"
    aliases = ["mojo", "🔥"]
    filenames = [
        "*.mojo",
        "*.🔥",
    ]
    mimetypes = [
        "text/x-mojo",
        "application/x-mojo",
    ]
    version_added = "2.18"

    uni_name = f"[{uni.xid_start}][{uni.xid_continue}]*"

    def innerstring_rules(ttype):
        return [
            # the old style '%s' % (...) string formatting (still valid in Py3)
            (
                r"%(\(\w+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?"
                "[hlL]?[E-GXc-giorsaux%]",
                String.Interpol,
            ),
            # the new style '{}'.format(...) string formatting
            (
                r"\{"
                r"((\w+)((\.\w+)|(\[[^\]]+\]))*)?"  # field name
                r"(\![sra])?"  # conversion
                r"(\:(.?[<>=\^])?[-+ ]?#?0?(\d+)?,?(\.\d+)?[E-GXb-gnosx%]?)?"
                r"\}",
                String.Interpol,
            ),
            # backslashes, quotes and formatting signs must be parsed one at a time
            (r'[^\\\'"%{\n]+', ttype),
            (r'[\'"\\]', ttype),
            # unhandled string formatting sign
            (r"%|(\{{1,2})", ttype),
            # newlines are an error (use "nl" state)
        ]

    def fstring_rules(ttype):
        return [
            # Assuming that a '}' is the closing brace after format specifier.
            # Sadly, this means that we won't detect syntax error. But it's
            # more important to parse correct syntax correctly, than to
            # highlight invalid syntax.
            (r"\}", String.Interpol),
            (r"\{", String.Interpol, "expr-inside-fstring"),
            # backslashes, quotes and formatting signs must be parsed one at a time
            (r'[^\\\'"{}\n]+', ttype),
            (r'[\'"\\]', ttype),
            # newlines are an error (use "nl" state)
        ]

    tokens = {
        "root": [
            (r"\s+", Whitespace),
            (
                r'^(\s*)([rRuUbB]{,2})("""(?:.|\n)*?""")',
                bygroups(Whitespace, String.Affix, String.Doc),
            ),
            (
                r"^(\s*)([rRuUbB]{,2})('''(?:.|\n)*?''')",
                bygroups(Whitespace, String.Affix, String.Doc),
            ),
            (r"\A#!.+$", Comment.Hashbang),
            (r"#.*$", Comment.Single),
            (r"\\\n", Whitespace),
            (r"\\", Whitespace),
            include("keywords"),
            include("soft-keywords"),
            # In the original PR, all the below here used ((?:\s|\\\s)+) to
            # designate whitespace, but I can't find any example of this being
            # needed in the example file, so we're replacing it with `\s+`.
            (
                r"(alias)(\s+)",
                bygroups(Keyword, Whitespace),
                "varname",  # TODO varname the right fit?
            ),
            (r"(var)(\s+)", bygroups(Keyword, Whitespace), "varname"),
            (r"(def)(\s+)", bygroups(Keyword, Whitespace), "funcname"),
            (r"(fn)(\s+)", bygroups(Keyword, Whitespace), "funcname"),
            (
                r"(class)(\s+)",
                bygroups(Keyword, Whitespace),
                "classname",
            ),  # not implemented yet
            (r"(struct)(\s+)", bygroups(Keyword, Whitespace), "structname"),
            (r"(trait)(\s+)", bygroups(Keyword, Whitespace), "structname"),
            (r"(from)(\s+)", bygroups(Keyword.Namespace, Whitespace), "fromimport"),
            (r"(import)(\s+)", bygroups(Keyword.Namespace, Whitespace), "import"),
            include("expr"),
        ],
        "expr": [
            # raw f-strings
            (
                '(?i)(rf|fr)(""")',
                bygroups(String.Affix, String.Double),
                combined("rfstringescape", "tdqf"),
            ),
            (
                "(?i)(rf|fr)(''')",
                bygroups(String.Affix, String.Single),
                combined("rfstringescape", "tsqf"),
            ),
            (
                '(?i)(rf|fr)(")',
                bygroups(String.Affix, String.Double),
                combined("rfstringescape", "dqf"),
            ),
            (
                "(?i)(rf|fr)(')",
                bygroups(String.Affix, String.Single),
                combined("rfstringescape", "sqf"),
            ),
            # non-raw f-strings
            (
                '([fF])(""")',
                bygroups(String.Affix, String.Double),
                combined("fstringescape", "tdqf"),
            ),
            (
                "([fF])(''')",
                bygroups(String.Affix, String.Single),
                combined("fstringescape", "tsqf"),
            ),
            (
                '([fF])(")',
                bygroups(String.Affix, String.Double),
                combined("fstringescape", "dqf"),
            ),
            (
                "([fF])(')",
                bygroups(String.Affix, String.Single),
                combined("fstringescape", "sqf"),
            ),
            # raw bytes and strings
            ('(?i)(rb|br|r)(""")', bygroups(String.Affix, String.Double), "tdqs"),
            ("(?i)(rb|br|r)(''')", bygroups(String.Affix, String.Single), "tsqs"),
            ('(?i)(rb|br|r)(")', bygroups(String.Affix, String.Double), "dqs"),
            ("(?i)(rb|br|r)(')", bygroups(String.Affix, String.Single), "sqs"),
            # non-raw strings
            (
                '([uU]?)(""")',
                bygroups(String.Affix, String.Double),
                combined("stringescape", "tdqs"),
            ),
            (
                "([uU]?)(''')",
                bygroups(String.Affix, String.Single),
                combined("stringescape", "tsqs"),
            ),
            (
                '([uU]?)(")',
                bygroups(String.Affix, String.Double),
                combined("stringescape", "dqs"),
            ),
            (
                "([uU]?)(')",
                bygroups(String.Affix, String.Single),
                combined("stringescape", "sqs"),
            ),
            # non-raw bytes
            (
                '([bB])(""")',
                bygroups(String.Affix, String.Double),
                combined("bytesescape", "tdqs"),
            ),
            (
                "([bB])(''')",
                bygroups(String.Affix, String.Single),
                combined("bytesescape", "tsqs"),
            ),
            (
                '([bB])(")',
                bygroups(String.Affix, String.Double),
                combined("bytesescape", "dqs"),
            ),
            (
                "([bB])(')",
                bygroups(String.Affix, String.Single),
                combined("bytesescape", "sqs"),
            ),
            (r"[^\S\n]+", Text),
            include("numbers"),
            (r"!=|==|<<|>>|:=|[-~+/*%=<>&^|.]", Operator),
            (r"([]{}:\(\),;[])+", Punctuation),
            (r"(in|is|and|or|not)\b", Operator.Word),
            include("expr-keywords"),
            include("builtins"),
            include("magicfuncs"),
            include("magicvars"),
            include("name"),
        ],
        "expr-inside-fstring": [
            (r"[{([]", Punctuation, "expr-inside-fstring-inner"),
            # without format specifier
            (
                r"(=\s*)?"  # debug (https://bugs.python.org/issue36817)
                r"(\![sraf])?"  # conversion
                r"\}",
                String.Interpol,
                "#pop",
            ),
            # with format specifier
            # we'll catch the remaining '}' in the outer scope
            (
                r"(=\s*)?"  # debug (https://bugs.python.org/issue36817)
                r"(\![sraf])?"  # conversion
                r":",
                String.Interpol,
                "#pop",
            ),
            (r"\s+", Whitespace),  # allow new lines
            include("expr"),
        ],
        "expr-inside-fstring-inner": [
            (r"[{([]", Punctuation, "expr-inside-fstring-inner"),
            (r"[])}]", Punctuation, "#pop"),
            (r"\s+", Whitespace),  # allow new lines
            include("expr"),
        ],
        "expr-keywords": [
            # Based on https://docs.python.org/3/reference/expressions.html
            (
                words(
                    (
                        "async for",  # TODO https://docs.modular.com/mojo/roadmap#no-async-for-or-async-with
                        "async with",  # TODO https://docs.modular.com/mojo/roadmap#no-async-for-or-async-with
                        "await",
                        "else",
                        "for",
                        "if",
                        "lambda",
                        "yield",
                        "yield from",
                    ),
                    suffix=r"\b",
                ),
                Keyword,
            ),
            (words(("True", "False", "None"), suffix=r"\b"), Keyword.Constant),
        ],
        "keywords": [
            (
                words(
                    (
                        "assert",
                        "async",
                        "await",
                        "borrowed",
                        "break",
                        "continue",
                        "del",
                        "elif",
                        "else",
                        "except",
                        "finally",
                        "for",
                        "global",
                        "if",
                        "lambda",
                        "pass",
                        "raise",
                        "nonlocal",
                        "return",
                        "try",
                        "while",
                        "yield",
                        "yield from",
                        "as",
                        "with",
                    ),
                    suffix=r"\b",
                ),
                Keyword,
            ),
            (words(("True", "False", "None"), suffix=r"\b"), Keyword.Constant),
        ],
        "soft-keywords": [
            # `match`, `case` and `_` soft keywords
            (
                r"(^[ \t]*)"  # at beginning of line + possible indentation
                r"(match|case)\b"  # a possible keyword
                r"(?![ \t]*(?:"  # not followed by...
                r"[:,;=^&|@~)\]}]|(?:" +  # characters and keywords that mean this isn't
                # pattern matching (but None/True/False is ok)
                r"|".join(k for k in keyword.kwlist if k[0].islower())
                + r")\b))",
                bygroups(Whitespace, Keyword),
                "soft-keywords-inner",
            ),
        ],
        "soft-keywords-inner": [
            # optional `_` keyword
            (r"(\s+)([^\n_]*)(_\b)", bygroups(Whitespace, using(this), Keyword)),
            default("#pop"),
        ],
        "builtins": [
            (
                words(
                    (
                        "__import__",
                        "abs",
                        "aiter",
                        "all",
                        "any",
                        "bin",
                        "bool",
                        "bytearray",
                        "breakpoint",
                        "bytes",
                        "callable",
                        "chr",
                        "classmethod",
                        "compile",
                        "complex",
                        "delattr",
                        "dict",
                        "dir",
                        "divmod",
                        "enumerate",
                        "eval",
                        "filter",
                        "float",
                        "format",
                        "frozenset",
                        "getattr",
                        "globals",
                        "hasattr",
                        "hash",
                        "hex",
                        "id",
                        "input",
                        "int",
                        "isinstance",
                        "issubclass",
                        "iter",
                        "len",
                        "list",
                        "locals",
                        "map",
                        "max",
                        "memoryview",
                        "min",
                        "next",
                        "object",
                        "oct",
                        "open",
                        "ord",
                        "pow",
                        "print",
                        "property",
                        "range",
                        "repr",
                        "reversed",
                        "round",
                        "set",
                        "setattr",
                        "slice",
                        "sorted",
                        "staticmethod",
                        "str",
                        "sum",
                        "super",
                        "tuple",
                        "type",
                        "vars",
                        "zip",
                        # Mojo builtin types: https://docs.modular.com/mojo/stdlib/builtin/
                        "AnyType",
                        "Coroutine",
                        "DType",
                        "Error",
                        "Int",
                        "List",
                        "ListLiteral",
                        "Scalar",
                        "Int8",
                        "UInt8",
                        "Int16",
                        "UInt16",
                        "Int32",
                        "UInt32",
                        "Int64",
                        "UInt64",
                        "BFloat16",
                        "Float16",
                        "Float32",
                        "Float64",
                        "SIMD",
                        "String",
                        "Tensor",
                        "Tuple",
                        "Movable",
                        "Copyable",
                        "CollectionElement",
                    ),
                    prefix=r"(?<!\.)",
                    suffix=r"\b",
                ),
                Name.Builtin,
            ),
            (r"(?<!\.)(self|Ellipsis|NotImplemented|cls)\b", Name.Builtin.Pseudo),
            (
                words(
                    ("Error",),
                    prefix=r"(?<!\.)",
                    suffix=r"\b",
                ),
                Name.Exception,
            ),
        ],
        "magicfuncs": [
            (
                words(
                    (
                        "__abs__",
                        "__add__",
                        "__aenter__",
                        "__aexit__",
                        "__aiter__",
                        "__and__",
                        "__anext__",
                        "__await__",
                        "__bool__",
                        "__bytes__",
                        "__call__",
                        "__complex__",
                        "__contains__",
                        "__del__",
                        "__delattr__",
                        "__delete__",
                        "__delitem__",
                        "__dir__",
                        "__divmod__",
                        "__enter__",
                        "__eq__",
                        "__exit__",
                        "__float__",
                        "__floordiv__",
                        "__format__",
                        "__ge__",
                        "__get__",
                        "__getattr__",
                        "__getattribute__",
                        "__getitem__",
                        "__gt__",
                        "__hash__",
                        "__iadd__",
                        "__iand__",
                        "__ifloordiv__",
                        "__ilshift__",
                        "__imatmul__",
                        "__imod__",
                        "__imul__",
                        "__index__",
                        "__init__",
                        "__instancecheck__",
                        "__int__",
                        "__invert__",
                        "__ior__",
                        "__ipow__",
                        "__irshift__",
                        "__isub__",
                        "__iter__",
                        "__itruediv__",
                        "__ixor__",
                        "__le__",
                        "__len__",
                        "__length_hint__",
                        "__lshift__",
                        "__lt__",
                        "__matmul__",
                        "__missing__",
                        "__mod__",
                        "__mul__",
                        "__ne__",
                        "__neg__",
                        "__new__",
                        "__next__",
                        "__or__",
                        "__pos__",
                        "__pow__",
                        "__prepare__",
                        "__radd__",
                        "__rand__",
                        "__rdivmod__",
                        "__repr__",
                        "__reversed__",
                        "__rfloordiv__",
                        "__rlshift__",
                        "__rmatmul__",
                        "__rmod__",
                        "__rmul__",
                        "__ror__",
                        "__round__",
                        "__rpow__",
                        "__rrshift__",
                        "__rshift__",
                        "__rsub__",
                        "__rtruediv__",
                        "__rxor__",
                        "__set__",
                        "__setattr__",
                        "__setitem__",
                        "__str__",
                        "__sub__",
                        "__subclasscheck__",
                        "__truediv__",
                        "__xor__",
                    ),
                    suffix=r"\b",
                ),
                Name.Function.Magic,
            ),
        ],
        "magicvars": [
            (
                words(
                    (
                        "__annotations__",
                        "__bases__",
                        "__class__",
                        "__closure__",
                        "__code__",
                        "__defaults__",
                        "__dict__",
                        "__doc__",
                        "__file__",
                        "__func__",
                        "__globals__",
                        "__kwdefaults__",
                        "__module__",
                        "__mro__",
                        "__name__",
                        "__objclass__",
                        "__qualname__",
                        "__self__",
                        "__slots__",
                        "__weakref__",
                    ),
                    suffix=r"\b",
                ),
                Name.Variable.Magic,
            ),
        ],
        "numbers": [
            (
                r"(\d(?:_?\d)*\.(?:\d(?:_?\d)*)?|(?:\d(?:_?\d)*)?\.\d(?:_?\d)*)"
                r"([eE][+-]?\d(?:_?\d)*)?",
                Number.Float,
            ),
            (r"\d(?:_?\d)*[eE][+-]?\d(?:_?\d)*j?", Number.Float),
            (r"0[oO](?:_?[0-7])+", Number.Oct),
            (r"0[bB](?:_?[01])+", Number.Bin),
            (r"0[xX](?:_?[a-fA-F0-9])+", Number.Hex),
            (r"\d(?:_?\d)*", Number.Integer),
        ],
        "name": [
            (r"@" + uni_name, Name.Decorator),
            (r"@", Operator),  # new matrix multiplication operator
            (uni_name, Name),
        ],
        "varname": [
            (uni_name, Name.Variable, "#pop"),
        ],
        "funcname": [
            include("magicfuncs"),
            (uni_name, Name.Function, "#pop"),
            default("#pop"),
        ],
        "classname": [
            (uni_name, Name.Class, "#pop"),
        ],
        "structname": [
            (uni_name, Name.Struct, "#pop"),
        ],
        "import": [
            (r"(\s+)(as)(\s+)", bygroups(Whitespace, Keyword, Whitespace)),
            (r"\.", Name.Namespace),
            (uni_name, Name.Namespace),
            (r"(\s*)(,)(\s*)", bygroups(Whitespace, Operator, Whitespace)),
            default("#pop"),  # all else: go back
        ],
        "fromimport": [
            (r"(\s+)(import)\b", bygroups(Whitespace, Keyword.Namespace), "#pop"),
            (r"\.", Name.Namespace),
            # if None occurs here, it's "raise x from None", since None can
            # never be a module name
            (r"None\b", Keyword.Constant, "#pop"),
            (uni_name, Name.Namespace),
            default("#pop"),
        ],
        "rfstringescape": [
            (r"\{\{", String.Escape),
            (r"\}\}", String.Escape),
        ],
        "fstringescape": [
            include("rfstringescape"),
            include("stringescape"),
        ],
        "bytesescape": [
            (r'\\([\\abfnrtv"\']|\n|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        "stringescape": [
            (r"\\(N\{.*?\}|u[a-fA-F0-9]{4}|U[a-fA-F0-9]{8})", String.Escape),
            include("bytesescape"),
        ],
        "fstrings-single": fstring_rules(String.Single),
        "fstrings-double": fstring_rules(String.Double),
        "strings-single": innerstring_rules(String.Single),
        "strings-double": innerstring_rules(String.Double),
        "dqf": [
            (r'"', String.Double, "#pop"),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include("fstrings-double"),
        ],
        "sqf": [
            (r"'", String.Single, "#pop"),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include("fstrings-single"),
        ],
        "dqs": [
            (r'"', String.Double, "#pop"),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include("strings-double"),
        ],
        "sqs": [
            (r"'", String.Single, "#pop"),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include("strings-single"),
        ],
        "tdqf": [
            (r'"""', String.Double, "#pop"),
            include("fstrings-double"),
            (r"\n", String.Double),
        ],
        "tsqf": [
            (r"'''", String.Single, "#pop"),
            include("fstrings-single"),
            (r"\n", String.Single),
        ],
        "tdqs": [
            (r'"""', String.Double, "#pop"),
            include("strings-double"),
            (r"\n", String.Double),
        ],
        "tsqs": [
            (r"'''", String.Single, "#pop"),
            include("strings-single"),
            (r"\n", String.Single),
        ],
    }

    def analyse_text(text):
        # TODO supported?
        if shebang_matches(text, r"mojo?"):
            return 1.0
        if "import " in text[:1000]:
            return 0.9
        return 0

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc3852.py ===
# coding: utf-8
#
# This file is part of pyasn1-modules software.
#
# Created by Stanisław Pitucha with asn1ate tool.
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
# Cryptographic Message Syntax (CMS)
#
# ASN.1 source from:
# http://www.ietf.org/rfc/rfc3852.txt
#
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

from pyasn1_modules import rfc3280
from pyasn1_modules import rfc3281

MAX = float('inf')


def _buildOid(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))

    return univ.ObjectIdentifier(output)


class AttributeValue(univ.Any):
    pass


class Attribute(univ.Sequence):
    pass


Attribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('attrType', univ.ObjectIdentifier()),
    namedtype.NamedType('attrValues', univ.SetOf(componentType=AttributeValue()))
)


class SignedAttributes(univ.SetOf):
    pass


SignedAttributes.componentType = Attribute()
SignedAttributes.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class OtherRevocationInfoFormat(univ.Sequence):
    pass


OtherRevocationInfoFormat.componentType = namedtype.NamedTypes(
    namedtype.NamedType('otherRevInfoFormat', univ.ObjectIdentifier()),
    namedtype.NamedType('otherRevInfo', univ.Any())
)


class RevocationInfoChoice(univ.Choice):
    pass


RevocationInfoChoice.componentType = namedtype.NamedTypes(
    namedtype.NamedType('crl', rfc3280.CertificateList()),
    namedtype.NamedType('other', OtherRevocationInfoFormat().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
)


class RevocationInfoChoices(univ.SetOf):
    pass


RevocationInfoChoices.componentType = RevocationInfoChoice()


class OtherKeyAttribute(univ.Sequence):
    pass


OtherKeyAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('keyAttrId', univ.ObjectIdentifier()),
    namedtype.OptionalNamedType('keyAttr', univ.Any())
)

id_signedData = _buildOid(1, 2, 840, 113549, 1, 7, 2)


class KeyEncryptionAlgorithmIdentifier(rfc3280.AlgorithmIdentifier):
    pass


class EncryptedKey(univ.OctetString):
    pass


class CMSVersion(univ.Integer):
    pass


CMSVersion.namedValues = namedval.NamedValues(
    ('v0', 0),
    ('v1', 1),
    ('v2', 2),
    ('v3', 3),
    ('v4', 4),
    ('v5', 5)
)


class KEKIdentifier(univ.Sequence):
    pass


KEKIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('keyIdentifier', univ.OctetString()),
    namedtype.OptionalNamedType('date', useful.GeneralizedTime()),
    namedtype.OptionalNamedType('other', OtherKeyAttribute())
)


class KEKRecipientInfo(univ.Sequence):
    pass


KEKRecipientInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('kekid', KEKIdentifier()),
    namedtype.NamedType('keyEncryptionAlgorithm', KeyEncryptionAlgorithmIdentifier()),
    namedtype.NamedType('encryptedKey', EncryptedKey())
)


class KeyDerivationAlgorithmIdentifier(rfc3280.AlgorithmIdentifier):
    pass


class PasswordRecipientInfo(univ.Sequence):
    pass


PasswordRecipientInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.OptionalNamedType('keyDerivationAlgorithm', KeyDerivationAlgorithmIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('keyEncryptionAlgorithm', KeyEncryptionAlgorithmIdentifier()),
    namedtype.NamedType('encryptedKey', EncryptedKey())
)


class OtherRecipientInfo(univ.Sequence):
    pass


OtherRecipientInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('oriType', univ.ObjectIdentifier()),
    namedtype.NamedType('oriValue', univ.Any())
)


class IssuerAndSerialNumber(univ.Sequence):
    pass


IssuerAndSerialNumber.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuer', rfc3280.Name()),
    namedtype.NamedType('serialNumber', rfc3280.CertificateSerialNumber())
)


class SubjectKeyIdentifier(univ.OctetString):
    pass


class RecipientKeyIdentifier(univ.Sequence):
    pass


RecipientKeyIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('subjectKeyIdentifier', SubjectKeyIdentifier()),
    namedtype.OptionalNamedType('date', useful.GeneralizedTime()),
    namedtype.OptionalNamedType('other', OtherKeyAttribute())
)


class KeyAgreeRecipientIdentifier(univ.Choice):
    pass


KeyAgreeRecipientIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuerAndSerialNumber', IssuerAndSerialNumber()),
    namedtype.NamedType('rKeyId', RecipientKeyIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)))
)


class RecipientEncryptedKey(univ.Sequence):
    pass


RecipientEncryptedKey.componentType = namedtype.NamedTypes(
    namedtype.NamedType('rid', KeyAgreeRecipientIdentifier()),
    namedtype.NamedType('encryptedKey', EncryptedKey())
)


class RecipientEncryptedKeys(univ.SequenceOf):
    pass


RecipientEncryptedKeys.componentType = RecipientEncryptedKey()


class UserKeyingMaterial(univ.OctetString):
    pass


class OriginatorPublicKey(univ.Sequence):
    pass


OriginatorPublicKey.componentType = namedtype.NamedTypes(
    namedtype.NamedType('algorithm', rfc3280.AlgorithmIdentifier()),
    namedtype.NamedType('publicKey', univ.BitString())
)


class OriginatorIdentifierOrKey(univ.Choice):
    pass


OriginatorIdentifierOrKey.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuerAndSerialNumber', IssuerAndSerialNumber()),
    namedtype.NamedType('subjectKeyIdentifier', SubjectKeyIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('originatorKey', OriginatorPublicKey().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
)


class KeyAgreeRecipientInfo(univ.Sequence):
    pass


KeyAgreeRecipientInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('originator', OriginatorIdentifierOrKey().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.OptionalNamedType('ukm', UserKeyingMaterial().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('keyEncryptionAlgorithm', KeyEncryptionAlgorithmIdentifier()),
    namedtype.NamedType('recipientEncryptedKeys', RecipientEncryptedKeys())
)


class RecipientIdentifier(univ.Choice):
    pass


RecipientIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuerAndSerialNumber', IssuerAndSerialNumber()),
    namedtype.NamedType('subjectKeyIdentifier', SubjectKeyIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)


class KeyTransRecipientInfo(univ.Sequence):
    pass


KeyTransRecipientInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('rid', RecipientIdentifier()),
    namedtype.NamedType('keyEncryptionAlgorithm', KeyEncryptionAlgorithmIdentifier()),
    namedtype.NamedType('encryptedKey', EncryptedKey())
)


class RecipientInfo(univ.Choice):
    pass


RecipientInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('ktri', KeyTransRecipientInfo()),
    namedtype.NamedType('kari', KeyAgreeRecipientInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
    namedtype.NamedType('kekri', KEKRecipientInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),
    namedtype.NamedType('pwri', PasswordRecipientInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),
    namedtype.NamedType('ori', OtherRecipientInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4)))
)


class RecipientInfos(univ.SetOf):
    pass


RecipientInfos.componentType = RecipientInfo()
RecipientInfos.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class DigestAlgorithmIdentifier(rfc3280.AlgorithmIdentifier):
    pass


class Signature(univ.BitString):
    pass


class SignerIdentifier(univ.Choice):
    pass


SignerIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuerAndSerialNumber', IssuerAndSerialNumber()),
    namedtype.NamedType('subjectKeyIdentifier', SubjectKeyIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)


class UnprotectedAttributes(univ.SetOf):
    pass


UnprotectedAttributes.componentType = Attribute()
UnprotectedAttributes.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class ContentType(univ.ObjectIdentifier):
    pass


class EncryptedContent(univ.OctetString):
    pass


class ContentEncryptionAlgorithmIdentifier(rfc3280.AlgorithmIdentifier):
    pass


class EncryptedContentInfo(univ.Sequence):
    pass


EncryptedContentInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('contentType', ContentType()),
    namedtype.NamedType('contentEncryptionAlgorithm', ContentEncryptionAlgorithmIdentifier()),
    namedtype.OptionalNamedType('encryptedContent', EncryptedContent().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)


class EncryptedData(univ.Sequence):
    pass


EncryptedData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('encryptedContentInfo', EncryptedContentInfo()),
    namedtype.OptionalNamedType('unprotectedAttrs', UnprotectedAttributes().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)

id_contentType = _buildOid(1, 2, 840, 113549, 1, 9, 3)

id_data = _buildOid(1, 2, 840, 113549, 1, 7, 1)

id_messageDigest = _buildOid(1, 2, 840, 113549, 1, 9, 4)


class DigestAlgorithmIdentifiers(univ.SetOf):
    pass


DigestAlgorithmIdentifiers.componentType = DigestAlgorithmIdentifier()


class EncapsulatedContentInfo(univ.Sequence):
    pass


EncapsulatedContentInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('eContentType', ContentType()),
    namedtype.OptionalNamedType('eContent', univ.OctetString().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)


class Digest(univ.OctetString):
    pass


class DigestedData(univ.Sequence):
    pass


DigestedData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('digestAlgorithm', DigestAlgorithmIdentifier()),
    namedtype.NamedType('encapContentInfo', EncapsulatedContentInfo()),
    namedtype.NamedType('digest', Digest())
)


class ContentInfo(univ.Sequence):
    pass


ContentInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('contentType', ContentType()),
    namedtype.NamedType('content', univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)


class UnauthAttributes(univ.SetOf):
    pass


UnauthAttributes.componentType = Attribute()
UnauthAttributes.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class ExtendedCertificateInfo(univ.Sequence):
    pass


ExtendedCertificateInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('certificate', rfc3280.Certificate()),
    namedtype.NamedType('attributes', UnauthAttributes())
)


class SignatureAlgorithmIdentifier(rfc3280.AlgorithmIdentifier):
    pass


class ExtendedCertificate(univ.Sequence):
    pass


ExtendedCertificate.componentType = namedtype.NamedTypes(
    namedtype.NamedType('extendedCertificateInfo', ExtendedCertificateInfo()),
    namedtype.NamedType('signatureAlgorithm', SignatureAlgorithmIdentifier()),
    namedtype.NamedType('signature', Signature())
)


class OtherCertificateFormat(univ.Sequence):
    pass


OtherCertificateFormat.componentType = namedtype.NamedTypes(
    namedtype.NamedType('otherCertFormat', univ.ObjectIdentifier()),
    namedtype.NamedType('otherCert', univ.Any())
)


class AttributeCertificateV2(rfc3281.AttributeCertificate):
    pass


class AttCertVersionV1(univ.Integer):
    pass


AttCertVersionV1.namedValues = namedval.NamedValues(
    ('v1', 0)
)


class AttributeCertificateInfoV1(univ.Sequence):
    pass


AttributeCertificateInfoV1.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('version', AttCertVersionV1().subtype(value="v1")),
    namedtype.NamedType(
        'subject', univ.Choice(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('baseCertificateID', rfc3281.IssuerSerial().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
                namedtype.NamedType('subjectName', rfc3280.GeneralNames().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
            )
        )
    ),
    namedtype.NamedType('issuer', rfc3280.GeneralNames()),
    namedtype.NamedType('signature', rfc3280.AlgorithmIdentifier()),
    namedtype.NamedType('serialNumber', rfc3280.CertificateSerialNumber()),
    namedtype.NamedType('attCertValidityPeriod', rfc3281.AttCertValidityPeriod()),
    namedtype.NamedType('attributes', univ.SequenceOf(componentType=rfc3280.Attribute())),
    namedtype.OptionalNamedType('issuerUniqueID', rfc3280.UniqueIdentifier()),
    namedtype.OptionalNamedType('extensions', rfc3280.Extensions())
)


class AttributeCertificateV1(univ.Sequence):
    pass


AttributeCertificateV1.componentType = namedtype.NamedTypes(
    namedtype.NamedType('acInfo', AttributeCertificateInfoV1()),
    namedtype.NamedType('signatureAlgorithm', rfc3280.AlgorithmIdentifier()),
    namedtype.NamedType('signature', univ.BitString())
)


class CertificateChoices(univ.Choice):
    pass


CertificateChoices.componentType = namedtype.NamedTypes(
    namedtype.NamedType('certificate', rfc3280.Certificate()),
    namedtype.NamedType('extendedCertificate', ExtendedCertificate().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('v1AttrCert', AttributeCertificateV1().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('v2AttrCert', AttributeCertificateV2().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('other', OtherCertificateFormat().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3)))
)


class CertificateSet(univ.SetOf):
    pass


CertificateSet.componentType = CertificateChoices()


class MessageAuthenticationCode(univ.OctetString):
    pass


class UnsignedAttributes(univ.SetOf):
    pass


UnsignedAttributes.componentType = Attribute()
UnsignedAttributes.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class SignatureValue(univ.OctetString):
    pass


class SignerInfo(univ.Sequence):
    pass


SignerInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('sid', SignerIdentifier()),
    namedtype.NamedType('digestAlgorithm', DigestAlgorithmIdentifier()),
    namedtype.OptionalNamedType('signedAttrs', SignedAttributes().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('signatureAlgorithm', SignatureAlgorithmIdentifier()),
    namedtype.NamedType('signature', SignatureValue()),
    namedtype.OptionalNamedType('unsignedAttrs', UnsignedAttributes().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class SignerInfos(univ.SetOf):
    pass


SignerInfos.componentType = SignerInfo()


class SignedData(univ.Sequence):
    pass


SignedData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.NamedType('digestAlgorithms', DigestAlgorithmIdentifiers()),
    namedtype.NamedType('encapContentInfo', EncapsulatedContentInfo()),
    namedtype.OptionalNamedType('certificates', CertificateSet().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('crls', RevocationInfoChoices().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('signerInfos', SignerInfos())
)


class MessageAuthenticationCodeAlgorithm(rfc3280.AlgorithmIdentifier):
    pass


class MessageDigest(univ.OctetString):
    pass


class Time(univ.Choice):
    pass


Time.componentType = namedtype.NamedTypes(
    namedtype.NamedType('utcTime', useful.UTCTime()),
    namedtype.NamedType('generalTime', useful.GeneralizedTime())
)


class OriginatorInfo(univ.Sequence):
    pass


OriginatorInfo.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('certs', CertificateSet().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('crls', RevocationInfoChoices().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class AuthAttributes(univ.SetOf):
    pass


AuthAttributes.componentType = Attribute()
AuthAttributes.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class AuthenticatedData(univ.Sequence):
    pass


AuthenticatedData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.OptionalNamedType('originatorInfo', OriginatorInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('recipientInfos', RecipientInfos()),
    namedtype.NamedType('macAlgorithm', MessageAuthenticationCodeAlgorithm()),
    namedtype.OptionalNamedType('digestAlgorithm', DigestAlgorithmIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('encapContentInfo', EncapsulatedContentInfo()),
    namedtype.OptionalNamedType('authAttrs', AuthAttributes().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('mac', MessageAuthenticationCode()),
    namedtype.OptionalNamedType('unauthAttrs', UnauthAttributes().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)

id_ct_contentInfo = _buildOid(1, 2, 840, 113549, 1, 9, 16, 1, 6)

id_envelopedData = _buildOid(1, 2, 840, 113549, 1, 7, 3)


class EnvelopedData(univ.Sequence):
    pass


EnvelopedData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', CMSVersion()),
    namedtype.OptionalNamedType('originatorInfo', OriginatorInfo().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('recipientInfos', RecipientInfos()),
    namedtype.NamedType('encryptedContentInfo', EncryptedContentInfo()),
    namedtype.OptionalNamedType('unprotectedAttrs', UnprotectedAttributes().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class Countersignature(SignerInfo):
    pass


id_digestedData = _buildOid(1, 2, 840, 113549, 1, 7, 5)

id_signingTime = _buildOid(1, 2, 840, 113549, 1, 9, 5)


class ExtendedCertificateOrCertificate(univ.Choice):
    pass


ExtendedCertificateOrCertificate.componentType = namedtype.NamedTypes(
    namedtype.NamedType('certificate', rfc3280.Certificate()),
    namedtype.NamedType('extendedCertificate', ExtendedCertificate().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)))
)

id_encryptedData = _buildOid(1, 2, 840, 113549, 1, 7, 6)

id_ct_authData = _buildOid(1, 2, 840, 113549, 1, 9, 16, 1, 2)


class SigningTime(Time):
    pass


id_countersignature = _buildOid(1, 2, 840, 113549, 1, 9, 6)

# === NexusCore/openenv\Lib\site-packages\starlette\datastructures.py ===
from __future__ import annotations

import typing
from shlex import shlex
from urllib.parse import SplitResult, parse_qsl, urlencode, urlsplit

from starlette.concurrency import run_in_threadpool
from starlette.types import Scope


class Address(typing.NamedTuple):
    host: str
    port: int


_KeyType = typing.TypeVar("_KeyType")
# Mapping keys are invariant but their values are covariant since
# you can only read them
# that is, you can't do `Mapping[str, Animal]()["fido"] = Dog()`
_CovariantValueType = typing.TypeVar("_CovariantValueType", covariant=True)


class URL:
    def __init__(
        self,
        url: str = "",
        scope: Scope | None = None,
        **components: typing.Any,
    ) -> None:
        if scope is not None:
            assert not url, 'Cannot set both "url" and "scope".'
            assert not components, 'Cannot set both "scope" and "**components".'
            scheme = scope.get("scheme", "http")
            server = scope.get("server", None)
            path = scope["path"]
            query_string = scope.get("query_string", b"")

            host_header = None
            for key, value in scope["headers"]:
                if key == b"host":
                    host_header = value.decode("latin-1")
                    break

            if host_header is not None:
                url = f"{scheme}://{host_header}{path}"
            elif server is None:
                url = path
            else:
                host, port = server
                default_port = {"http": 80, "https": 443, "ws": 80, "wss": 443}[scheme]
                if port == default_port:
                    url = f"{scheme}://{host}{path}"
                else:
                    url = f"{scheme}://{host}:{port}{path}"

            if query_string:
                url += "?" + query_string.decode()
        elif components:
            assert not url, 'Cannot set both "url" and "**components".'
            url = URL("").replace(**components).components.geturl()

        self._url = url

    @property
    def components(self) -> SplitResult:
        if not hasattr(self, "_components"):
            self._components = urlsplit(self._url)
        return self._components

    @property
    def scheme(self) -> str:
        return self.components.scheme

    @property
    def netloc(self) -> str:
        return self.components.netloc

    @property
    def path(self) -> str:
        return self.components.path

    @property
    def query(self) -> str:
        return self.components.query

    @property
    def fragment(self) -> str:
        return self.components.fragment

    @property
    def username(self) -> None | str:
        return self.components.username

    @property
    def password(self) -> None | str:
        return self.components.password

    @property
    def hostname(self) -> None | str:
        return self.components.hostname

    @property
    def port(self) -> int | None:
        return self.components.port

    @property
    def is_secure(self) -> bool:
        return self.scheme in ("https", "wss")

    def replace(self, **kwargs: typing.Any) -> URL:
        if (
            "username" in kwargs
            or "password" in kwargs
            or "hostname" in kwargs
            or "port" in kwargs
        ):
            hostname = kwargs.pop("hostname", None)
            port = kwargs.pop("port", self.port)
            username = kwargs.pop("username", self.username)
            password = kwargs.pop("password", self.password)

            if hostname is None:
                netloc = self.netloc
                _, _, hostname = netloc.rpartition("@")

                if hostname[-1] != "]":
                    hostname = hostname.rsplit(":", 1)[0]

            netloc = hostname
            if port is not None:
                netloc += f":{port}"
            if username is not None:
                userpass = username
                if password is not None:
                    userpass += f":{password}"
                netloc = f"{userpass}@{netloc}"

            kwargs["netloc"] = netloc

        components = self.components._replace(**kwargs)
        return self.__class__(components.geturl())

    def include_query_params(self, **kwargs: typing.Any) -> URL:
        params = MultiDict(parse_qsl(self.query, keep_blank_values=True))
        params.update({str(key): str(value) for key, value in kwargs.items()})
        query = urlencode(params.multi_items())
        return self.replace(query=query)

    def replace_query_params(self, **kwargs: typing.Any) -> URL:
        query = urlencode([(str(key), str(value)) for key, value in kwargs.items()])
        return self.replace(query=query)

    def remove_query_params(self, keys: str | typing.Sequence[str]) -> URL:
        if isinstance(keys, str):
            keys = [keys]
        params = MultiDict(parse_qsl(self.query, keep_blank_values=True))
        for key in keys:
            params.pop(key, None)
        query = urlencode(params.multi_items())
        return self.replace(query=query)

    def __eq__(self, other: typing.Any) -> bool:
        return str(self) == str(other)

    def __str__(self) -> str:
        return self._url

    def __repr__(self) -> str:
        url = str(self)
        if self.password:
            url = str(self.replace(password="********"))
        return f"{self.__class__.__name__}({repr(url)})"


class URLPath(str):
    """
    A URL path string that may also hold an associated protocol and/or host.
    Used by the routing to return `url_path_for` matches.
    """

    def __new__(cls, path: str, protocol: str = "", host: str = "") -> URLPath:
        assert protocol in ("http", "websocket", "")
        return str.__new__(cls, path)

    def __init__(self, path: str, protocol: str = "", host: str = "") -> None:
        self.protocol = protocol
        self.host = host

    def make_absolute_url(self, base_url: str | URL) -> URL:
        if isinstance(base_url, str):
            base_url = URL(base_url)
        if self.protocol:
            scheme = {
                "http": {True: "https", False: "http"},
                "websocket": {True: "wss", False: "ws"},
            }[self.protocol][base_url.is_secure]
        else:
            scheme = base_url.scheme

        netloc = self.host or base_url.netloc
        path = base_url.path.rstrip("/") + str(self)
        return URL(scheme=scheme, netloc=netloc, path=path)


class Secret:
    """
    Holds a string value that should not be revealed in tracebacks etc.
    You should cast the value to `str` at the point it is required.
    """

    def __init__(self, value: str):
        self._value = value

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}('**********')"

    def __str__(self) -> str:
        return self._value

    def __bool__(self) -> bool:
        return bool(self._value)


class CommaSeparatedStrings(typing.Sequence[str]):
    def __init__(self, value: str | typing.Sequence[str]):
        if isinstance(value, str):
            splitter = shlex(value, posix=True)
            splitter.whitespace = ","
            splitter.whitespace_split = True
            self._items = [item.strip() for item in splitter]
        else:
            self._items = list(value)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int | slice) -> typing.Any:
        return self._items[index]

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._items)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        items = [item for item in self]
        return f"{class_name}({items!r})"

    def __str__(self) -> str:
        return ", ".join(repr(item) for item in self)


class ImmutableMultiDict(typing.Mapping[_KeyType, _CovariantValueType]):
    _dict: dict[_KeyType, _CovariantValueType]

    def __init__(
        self,
        *args: ImmutableMultiDict[_KeyType, _CovariantValueType]
        | typing.Mapping[_KeyType, _CovariantValueType]
        | typing.Iterable[tuple[_KeyType, _CovariantValueType]],
        **kwargs: typing.Any,
    ) -> None:
        assert len(args) < 2, "Too many arguments."

        value: typing.Any = args[0] if args else []
        if kwargs:
            value = (
                ImmutableMultiDict(value).multi_items()
                + ImmutableMultiDict(kwargs).multi_items()
            )

        if not value:
            _items: list[tuple[typing.Any, typing.Any]] = []
        elif hasattr(value, "multi_items"):
            value = typing.cast(
                ImmutableMultiDict[_KeyType, _CovariantValueType], value
            )
            _items = list(value.multi_items())
        elif hasattr(value, "items"):
            value = typing.cast(typing.Mapping[_KeyType, _CovariantValueType], value)
            _items = list(value.items())
        else:
            value = typing.cast("list[tuple[typing.Any, typing.Any]]", value)
            _items = list(value)

        self._dict = {k: v for k, v in _items}
        self._list = _items

    def getlist(self, key: typing.Any) -> list[_CovariantValueType]:
        return [item_value for item_key, item_value in self._list if item_key == key]

    def keys(self) -> typing.KeysView[_KeyType]:
        return self._dict.keys()

    def values(self) -> typing.ValuesView[_CovariantValueType]:
        return self._dict.values()

    def items(self) -> typing.ItemsView[_KeyType, _CovariantValueType]:
        return self._dict.items()

    def multi_items(self) -> list[tuple[_KeyType, _CovariantValueType]]:
        return list(self._list)

    def __getitem__(self, key: _KeyType) -> _CovariantValueType:
        return self._dict[key]

    def __contains__(self, key: typing.Any) -> bool:
        return key in self._dict

    def __iter__(self) -> typing.Iterator[_KeyType]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._dict)

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return sorted(self._list) == sorted(other._list)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        items = self.multi_items()
        return f"{class_name}({items!r})"


class MultiDict(ImmutableMultiDict[typing.Any, typing.Any]):
    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        self.setlist(key, [value])

    def __delitem__(self, key: typing.Any) -> None:
        self._list = [(k, v) for k, v in self._list if k != key]
        del self._dict[key]

    def pop(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        self._list = [(k, v) for k, v in self._list if k != key]
        return self._dict.pop(key, default)

    def popitem(self) -> tuple[typing.Any, typing.Any]:
        key, value = self._dict.popitem()
        self._list = [(k, v) for k, v in self._list if k != key]
        return key, value

    def poplist(self, key: typing.Any) -> list[typing.Any]:
        values = [v for k, v in self._list if k == key]
        self.pop(key)
        return values

    def clear(self) -> None:
        self._dict.clear()
        self._list.clear()

    def setdefault(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        if key not in self:
            self._dict[key] = default
            self._list.append((key, default))

        return self[key]

    def setlist(self, key: typing.Any, values: list[typing.Any]) -> None:
        if not values:
            self.pop(key, None)
        else:
            existing_items = [(k, v) for (k, v) in self._list if k != key]
            self._list = existing_items + [(key, value) for value in values]
            self._dict[key] = values[-1]

    def append(self, key: typing.Any, value: typing.Any) -> None:
        self._list.append((key, value))
        self._dict[key] = value

    def update(
        self,
        *args: MultiDict
        | typing.Mapping[typing.Any, typing.Any]
        | list[tuple[typing.Any, typing.Any]],
        **kwargs: typing.Any,
    ) -> None:
        value = MultiDict(*args, **kwargs)
        existing_items = [(k, v) for (k, v) in self._list if k not in value.keys()]
        self._list = existing_items + value.multi_items()
        self._dict.update(value)


class QueryParams(ImmutableMultiDict[str, str]):
    """
    An immutable multidict.
    """

    def __init__(
        self,
        *args: ImmutableMultiDict[typing.Any, typing.Any]
        | typing.Mapping[typing.Any, typing.Any]
        | list[tuple[typing.Any, typing.Any]]
        | str
        | bytes,
        **kwargs: typing.Any,
    ) -> None:
        assert len(args) < 2, "Too many arguments."

        value = args[0] if args else []

        if isinstance(value, str):
            super().__init__(parse_qsl(value, keep_blank_values=True), **kwargs)
        elif isinstance(value, bytes):
            super().__init__(
                parse_qsl(value.decode("latin-1"), keep_blank_values=True), **kwargs
            )
        else:
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._list = [(str(k), str(v)) for k, v in self._list]
        self._dict = {str(k): str(v) for k, v in self._dict.items()}

    def __str__(self) -> str:
        return urlencode(self._list)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        query_string = str(self)
        return f"{class_name}({query_string!r})"


class UploadFile:
    """
    An uploaded file included as part of the request data.
    """

    def __init__(
        self,
        file: typing.BinaryIO,
        *,
        size: int | None = None,
        filename: str | None = None,
        headers: Headers | None = None,
    ) -> None:
        self.filename = filename
        self.file = file
        self.size = size
        self.headers = headers or Headers()

    @property
    def content_type(self) -> str | None:
        return self.headers.get("content-type", None)

    @property
    def _in_memory(self) -> bool:
        # check for SpooledTemporaryFile._rolled
        rolled_to_disk = getattr(self.file, "_rolled", True)
        return not rolled_to_disk

    async def write(self, data: bytes) -> None:
        if self.size is not None:
            self.size += len(data)

        if self._in_memory:
            self.file.write(data)
        else:
            await run_in_threadpool(self.file.write, data)

    async def read(self, size: int = -1) -> bytes:
        if self._in_memory:
            return self.file.read(size)
        return await run_in_threadpool(self.file.read, size)

    async def seek(self, offset: int) -> None:
        if self._in_memory:
            self.file.seek(offset)
        else:
            await run_in_threadpool(self.file.seek, offset)

    async def close(self) -> None:
        if self._in_memory:
            self.file.close()
        else:
            await run_in_threadpool(self.file.close)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"filename={self.filename!r}, "
            f"size={self.size!r}, "
            f"headers={self.headers!r})"
        )


class FormData(ImmutableMultiDict[str, typing.Union[UploadFile, str]]):
    """
    An immutable multidict, containing both file uploads and text input.
    """

    def __init__(
        self,
        *args: FormData
        | typing.Mapping[str, str | UploadFile]
        | list[tuple[str, str | UploadFile]],
        **kwargs: str | UploadFile,
    ) -> None:
        super().__init__(*args, **kwargs)

    async def close(self) -> None:
        for key, value in self.multi_items():
            if isinstance(value, UploadFile):
                await value.close()


class Headers(typing.Mapping[str, str]):
    """
    An immutable, case-insensitive multidict.
    """

    def __init__(
        self,
        headers: typing.Mapping[str, str] | None = None,
        raw: list[tuple[bytes, bytes]] | None = None,
        scope: typing.MutableMapping[str, typing.Any] | None = None,
    ) -> None:
        self._list: list[tuple[bytes, bytes]] = []
        if headers is not None:
            assert raw is None, 'Cannot set both "headers" and "raw".'
            assert scope is None, 'Cannot set both "headers" and "scope".'
            self._list = [
                (key.lower().encode("latin-1"), value.encode("latin-1"))
                for key, value in headers.items()
            ]
        elif raw is not None:
            assert scope is None, 'Cannot set both "raw" and "scope".'
            self._list = raw
        elif scope is not None:
            # scope["headers"] isn't necessarily a list
            # it might be a tuple or other iterable
            self._list = scope["headers"] = list(scope["headers"])

    @property
    def raw(self) -> list[tuple[bytes, bytes]]:
        return list(self._list)

    def keys(self) -> list[str]:  # type: ignore[override]
        return [key.decode("latin-1") for key, value in self._list]

    def values(self) -> list[str]:  # type: ignore[override]
        return [value.decode("latin-1") for key, value in self._list]

    def items(self) -> list[tuple[str, str]]:  # type: ignore[override]
        return [
            (key.decode("latin-1"), value.decode("latin-1"))
            for key, value in self._list
        ]

    def getlist(self, key: str) -> list[str]:
        get_header_key = key.lower().encode("latin-1")
        return [
            item_value.decode("latin-1")
            for item_key, item_value in self._list
            if item_key == get_header_key
        ]

    def mutablecopy(self) -> MutableHeaders:
        return MutableHeaders(raw=self._list[:])

    def __getitem__(self, key: str) -> str:
        get_header_key = key.lower().encode("latin-1")
        for header_key, header_value in self._list:
            if header_key == get_header_key:
                return header_value.decode("latin-1")
        raise KeyError(key)

    def __contains__(self, key: typing.Any) -> bool:
        get_header_key = key.lower().encode("latin-1")
        for header_key, header_value in self._list:
            if header_key == get_header_key:
                return True
        return False

    def __iter__(self) -> typing.Iterator[typing.Any]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._list)

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, Headers):
            return False
        return sorted(self._list) == sorted(other._list)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        as_dict = dict(self.items())
        if len(as_dict) == len(self):
            return f"{class_name}({as_dict!r})"
        return f"{class_name}(raw={self.raw!r})"


class MutableHeaders(Headers):
    def __setitem__(self, key: str, value: str) -> None:
        """
        Set the header `key` to `value`, removing any duplicate entries.
        Retains insertion order.
        """
        set_key = key.lower().encode("latin-1")
        set_value = value.encode("latin-1")

        found_indexes: list[int] = []
        for idx, (item_key, item_value) in enumerate(self._list):
            if item_key == set_key:
                found_indexes.append(idx)

        for idx in reversed(found_indexes[1:]):
            del self._list[idx]

        if found_indexes:
            idx = found_indexes[0]
            self._list[idx] = (set_key, set_value)
        else:
            self._list.append((set_key, set_value))

    def __delitem__(self, key: str) -> None:
        """
        Remove the header `key`.
        """
        del_key = key.lower().encode("latin-1")

        pop_indexes: list[int] = []
        for idx, (item_key, item_value) in enumerate(self._list):
            if item_key == del_key:
                pop_indexes.append(idx)

        for idx in reversed(pop_indexes):
            del self._list[idx]

    def __ior__(self, other: typing.Mapping[str, str]) -> MutableHeaders:
        if not isinstance(other, typing.Mapping):
            raise TypeError(f"Expected a mapping but got {other.__class__.__name__}")
        self.update(other)
        return self

    def __or__(self, other: typing.Mapping[str, str]) -> MutableHeaders:
        if not isinstance(other, typing.Mapping):
            raise TypeError(f"Expected a mapping but got {other.__class__.__name__}")
        new = self.mutablecopy()
        new.update(other)
        return new

    @property
    def raw(self) -> list[tuple[bytes, bytes]]:
        return self._list

    def setdefault(self, key: str, value: str) -> str:
        """
        If the header `key` does not exist, then set it to `value`.
        Returns the header value.
        """
        set_key = key.lower().encode("latin-1")
        set_value = value.encode("latin-1")

        for idx, (item_key, item_value) in enumerate(self._list):
            if item_key == set_key:
                return item_value.decode("latin-1")
        self._list.append((set_key, set_value))
        return value

    def update(self, other: typing.Mapping[str, str]) -> None:
        for key, val in other.items():
            self[key] = val

    def append(self, key: str, value: str) -> None:
        """
        Append a header, preserving any duplicate entries.
        """
        append_key = key.lower().encode("latin-1")
        append_value = value.encode("latin-1")
        self._list.append((append_key, append_value))

    def add_vary_header(self, vary: str) -> None:
        existing = self.get("vary")
        if existing is not None:
            vary = ", ".join([existing, vary])
        self["vary"] = vary


class State:
    """
    An object that can be used to store arbitrary state.

    Used for `request.state` and `app.state`.
    """

    _state: dict[str, typing.Any]

    def __init__(self, state: dict[str, typing.Any] | None = None):
        if state is None:
            state = {}
        super().__setattr__("_state", state)

    def __setattr__(self, key: typing.Any, value: typing.Any) -> None:
        self._state[key] = value

    def __getattr__(self, key: typing.Any) -> typing.Any:
        try:
            return self._state[key]
        except KeyError:
            message = "'{}' object has no attribute '{}'"
            raise AttributeError(message.format(self.__class__.__name__, key))

    def __delattr__(self, key: typing.Any) -> None:
        del self._state[key]

# === NexusCore/openenv\Lib\site-packages\trio\_core\_tests\test_ki.py ===
from __future__ import annotations

import contextlib
import inspect
import signal
import sys
import threading
import weakref
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Callable, TypeVar

import outcome
import pytest

from trio.testing import RaisesGroup

from .tutil import gc_collect_harder

try:
    from async_generator import async_generator, yield_
except ImportError:  # pragma: no cover
    async_generator = yield_ = None

from ... import _core
from ..._abc import Instrument
from ..._core import _ki
from ..._timeouts import sleep
from ...testing import wait_all_tasks_blocked

if TYPE_CHECKING:
    from collections.abc import (
        AsyncGenerator,
        AsyncIterator,
        Callable,
        Generator,
        Iterator,
    )

    from ..._core import Abort, RaiseCancelT


def ki_self() -> None:
    signal.raise_signal(signal.SIGINT)


def test_ki_self() -> None:
    with pytest.raises(KeyboardInterrupt):
        ki_self()


async def test_ki_enabled() -> None:
    # Regular tasks aren't KI-protected
    assert not _core.currently_ki_protected()

    # Low-level call-soon callbacks are KI-protected
    token = _core.current_trio_token()
    record = []

    def check() -> None:
        record.append(_core.currently_ki_protected())

    token.run_sync_soon(check)
    await wait_all_tasks_blocked()
    assert record == [True]

    @_core.enable_ki_protection
    def protected() -> None:
        assert _core.currently_ki_protected()
        unprotected()

    @_core.disable_ki_protection
    def unprotected() -> None:
        assert not _core.currently_ki_protected()

    protected()

    @_core.enable_ki_protection
    async def aprotected() -> None:
        assert _core.currently_ki_protected()
        await aunprotected()

    @_core.disable_ki_protection
    async def aunprotected() -> None:
        assert not _core.currently_ki_protected()

    await aprotected()

    # make sure that the decorator here overrides the automatic manipulation
    # that start_soon() does:
    async with _core.open_nursery() as nursery:
        nursery.start_soon(aprotected)
        nursery.start_soon(aunprotected)

    @_core.enable_ki_protection
    def gen_protected() -> Iterator[None]:
        assert _core.currently_ki_protected()
        yield

    for _ in gen_protected():
        pass

    @_core.disable_ki_protection
    def gen_unprotected() -> Iterator[None]:
        assert not _core.currently_ki_protected()
        yield

    for _ in gen_unprotected():
        pass


# This used to be broken due to
#
#   https://bugs.python.org/issue29590
#
# Specifically, after a coroutine is resumed with .throw(), then the stack
# makes it look like the immediate caller is the function that called
# .throw(), not the actual caller. So child() here would have a caller deep in
# the guts of the run loop, and always be protected, even when it shouldn't
# have been. (Solution: we don't use .throw() anymore.)
async def test_ki_enabled_after_yield_briefly() -> None:
    @_core.enable_ki_protection
    async def protected() -> None:
        await child(True)

    @_core.disable_ki_protection
    async def unprotected() -> None:
        await child(False)

    async def child(expected: bool) -> None:
        import traceback

        traceback.print_stack()
        assert _core.currently_ki_protected() == expected
        await _core.checkpoint()
        traceback.print_stack()
        assert _core.currently_ki_protected() == expected

    await protected()
    await unprotected()


# This also used to be broken due to
#   https://bugs.python.org/issue29590
async def test_generator_based_context_manager_throw() -> None:
    @contextlib.contextmanager
    @_core.enable_ki_protection
    def protected_manager() -> Iterator[None]:
        assert _core.currently_ki_protected()
        try:
            yield
        finally:
            assert _core.currently_ki_protected()

    with protected_manager():
        assert not _core.currently_ki_protected()

    with pytest.raises(KeyError):
        # This is the one that used to fail
        with protected_manager():
            raise KeyError


# the async_generator package isn't typed, hence all the type: ignores
@pytest.mark.skipif(async_generator is None, reason="async_generator not installed")
async def test_async_generator_agen_protection() -> None:
    @_core.enable_ki_protection
    @async_generator  # type: ignore[misc] # untyped generator
    async def agen_protected1() -> None:  # type: ignore[misc] # untyped generator
        assert _core.currently_ki_protected()
        try:
            await yield_()
        finally:
            assert _core.currently_ki_protected()

    @_core.disable_ki_protection
    @async_generator  # type: ignore[misc] # untyped generator
    async def agen_unprotected1() -> None:  # type: ignore[misc] # untyped generator
        assert not _core.currently_ki_protected()
        try:
            await yield_()
        finally:
            assert not _core.currently_ki_protected()

    # Swap the order of the decorators:
    @async_generator  # type: ignore[misc] # untyped generator
    @_core.enable_ki_protection
    async def agen_protected2() -> None:  # type: ignore[misc] # untyped generator
        assert _core.currently_ki_protected()
        try:
            await yield_()
        finally:
            assert _core.currently_ki_protected()

    @async_generator  # type: ignore[misc] # untyped generator
    @_core.disable_ki_protection
    async def agen_unprotected2() -> None:  # type: ignore[misc] # untyped generator
        assert not _core.currently_ki_protected()
        try:
            await yield_()
        finally:
            assert not _core.currently_ki_protected()

    await _check_agen(agen_protected1)
    await _check_agen(agen_protected2)
    await _check_agen(agen_unprotected1)
    await _check_agen(agen_unprotected2)


async def test_native_agen_protection() -> None:
    # Native async generators
    @_core.enable_ki_protection
    async def agen_protected() -> AsyncIterator[None]:
        assert _core.currently_ki_protected()
        try:
            yield
        finally:
            assert _core.currently_ki_protected()

    @_core.disable_ki_protection
    async def agen_unprotected() -> AsyncIterator[None]:
        assert not _core.currently_ki_protected()
        try:
            yield
        finally:
            assert not _core.currently_ki_protected()

    await _check_agen(agen_protected)
    await _check_agen(agen_unprotected)


async def _check_agen(agen_fn: Callable[[], AsyncIterator[None]]) -> None:
    async for _ in agen_fn():
        assert not _core.currently_ki_protected()

    # asynccontextmanager insists that the function passed must itself be an
    # async gen function, not a wrapper around one
    if inspect.isasyncgenfunction(agen_fn):
        async with contextlib.asynccontextmanager(agen_fn)():
            assert not _core.currently_ki_protected()

        # Another case that's tricky due to:
        #   https://bugs.python.org/issue29590
        with pytest.raises(KeyError):
            async with contextlib.asynccontextmanager(agen_fn)():
                raise KeyError


# Test the case where there's no magic local anywhere in the call stack
def test_ki_disabled_out_of_context() -> None:
    assert _core.currently_ki_protected()


def test_ki_disabled_in_del() -> None:
    def nestedfunction() -> bool:
        return _core.currently_ki_protected()

    def __del__() -> None:
        assert _core.currently_ki_protected()
        assert nestedfunction()

    @_core.disable_ki_protection
    def outerfunction() -> None:
        assert not _core.currently_ki_protected()
        assert not nestedfunction()
        __del__()

    __del__()
    outerfunction()
    assert nestedfunction()


def test_ki_protection_works() -> None:
    async def sleeper(name: str, record: set[str]) -> None:
        try:
            while True:
                await _core.checkpoint()
        except _core.Cancelled:
            record.add(name + " ok")

    async def raiser(name: str, record: set[str]) -> None:
        try:
            # os.kill runs signal handlers before returning, so we don't need
            # to worry that the handler will be delayed
            print("killing, protection =", _core.currently_ki_protected())
            ki_self()
        except KeyboardInterrupt:
            print("raised!")
            # Make sure we aren't getting cancelled as well as siginted
            await _core.checkpoint()
            record.add(name + " raise ok")
            raise
        else:
            print("didn't raise!")
            # If we didn't raise (b/c protected), then we *should* get
            # cancelled at the next opportunity
            try:
                await _core.wait_task_rescheduled(lambda _: _core.Abort.SUCCEEDED)
            except _core.Cancelled:
                record.add(name + " cancel ok")

    # simulated control-C during raiser, which is *unprotected*
    print("check 1")
    record_set: set[str] = set()

    async def check_unprotected_kill() -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(sleeper, "s1", record_set)
            nursery.start_soon(sleeper, "s2", record_set)
            nursery.start_soon(raiser, "r1", record_set)

    # raises inside a nursery, so the KeyboardInterrupt is wrapped in an ExceptionGroup
    with RaisesGroup(KeyboardInterrupt):
        _core.run(check_unprotected_kill)
    assert record_set == {"s1 ok", "s2 ok", "r1 raise ok"}

    # simulated control-C during raiser, which is *protected*, so the KI gets
    # delivered to the main task instead
    print("check 2")
    record_set = set()

    async def check_protected_kill() -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(sleeper, "s1", record_set)
            nursery.start_soon(sleeper, "s2", record_set)
            nursery.start_soon(_core.enable_ki_protection(raiser), "r1", record_set)
            # __aexit__ blocks, and then receives the KI

    # raises inside a nursery, so the KeyboardInterrupt is wrapped in an ExceptionGroup
    with RaisesGroup(KeyboardInterrupt):
        _core.run(check_protected_kill)
    assert record_set == {"s1 ok", "s2 ok", "r1 cancel ok"}

    # kill at last moment still raises (run_sync_soon until it raises an
    # error, then kill)
    print("check 3")

    async def check_kill_during_shutdown() -> None:
        token = _core.current_trio_token()

        def kill_during_shutdown() -> None:
            assert _core.currently_ki_protected()
            try:
                token.run_sync_soon(kill_during_shutdown)
            except _core.RunFinishedError:
                # it's too late for regular handling! handle this!
                print("kill! kill!")
                ki_self()

        token.run_sync_soon(kill_during_shutdown)

    # no nurseries involved, so the KeyboardInterrupt isn't wrapped
    with pytest.raises(KeyboardInterrupt):
        _core.run(check_kill_during_shutdown)

    # KI arrives very early, before main is even spawned
    print("check 4")

    class InstrumentOfDeath(Instrument):
        def before_run(self) -> None:
            ki_self()

    async def main_1() -> None:
        await _core.checkpoint()

    # no nurseries involved, so the KeyboardInterrupt isn't wrapped
    with pytest.raises(KeyboardInterrupt):
        _core.run(main_1, instruments=[InstrumentOfDeath()])

    # checkpoint_if_cancelled notices pending KI
    print("check 5")

    @_core.enable_ki_protection
    async def main_2() -> None:
        assert _core.currently_ki_protected()
        ki_self()
        with pytest.raises(KeyboardInterrupt):
            await _core.checkpoint_if_cancelled()

    _core.run(main_2)

    # KI arrives while main task is not abortable, b/c already scheduled
    print("check 6")

    @_core.enable_ki_protection
    async def main_3() -> None:
        assert _core.currently_ki_protected()
        ki_self()
        await _core.cancel_shielded_checkpoint()
        await _core.cancel_shielded_checkpoint()
        await _core.cancel_shielded_checkpoint()
        with pytest.raises(KeyboardInterrupt):
            await _core.checkpoint()

    _core.run(main_3)

    # KI arrives while main task is not abortable, b/c refuses to be aborted
    print("check 7")

    @_core.enable_ki_protection
    async def main_4() -> None:
        assert _core.currently_ki_protected()
        ki_self()
        task = _core.current_task()

        def abort(_: RaiseCancelT) -> Abort:
            _core.reschedule(task, outcome.Value(1))
            return _core.Abort.FAILED

        assert await _core.wait_task_rescheduled(abort) == 1
        with pytest.raises(KeyboardInterrupt):
            await _core.checkpoint()

    _core.run(main_4)

    # KI delivered via slow abort
    print("check 8")

    @_core.enable_ki_protection
    async def main_5() -> None:
        assert _core.currently_ki_protected()
        ki_self()
        task = _core.current_task()

        def abort(raise_cancel: RaiseCancelT) -> Abort:
            result = outcome.capture(raise_cancel)
            _core.reschedule(task, result)
            return _core.Abort.FAILED

        with pytest.raises(KeyboardInterrupt):
            assert await _core.wait_task_rescheduled(abort)
        await _core.checkpoint()

    _core.run(main_5)

    # KI arrives just before main task exits, so the run_sync_soon machinery
    # is still functioning and will accept the callback to deliver the KI, but
    # by the time the callback is actually run, main has exited and can't be
    # aborted.
    print("check 9")

    @_core.enable_ki_protection
    async def main_6() -> None:
        ki_self()

    with pytest.raises(KeyboardInterrupt):
        _core.run(main_6)

    print("check 10")
    # KI in unprotected code, with
    # restrict_keyboard_interrupt_to_checkpoints=True
    record_list = []

    async def main_7() -> None:
        # We're not KI protected...
        assert not _core.currently_ki_protected()
        ki_self()
        # ...but even after the KI, we keep running uninterrupted...
        record_list.append("ok")
        # ...until we hit a checkpoint:
        with pytest.raises(KeyboardInterrupt):
            await sleep(10)

    _core.run(main_7, restrict_keyboard_interrupt_to_checkpoints=True)
    assert record_list == ["ok"]
    record_list = []
    # Exact same code raises KI early if we leave off the argument, doesn't
    # even reach the record.append call:
    with pytest.raises(KeyboardInterrupt):
        _core.run(main_7)
    assert record_list == []

    # KI arrives while main task is inside a cancelled cancellation scope
    # the KeyboardInterrupt should take priority
    print("check 11")

    @_core.enable_ki_protection
    async def main_8() -> None:
        assert _core.currently_ki_protected()
        with _core.CancelScope() as cancel_scope:
            cancel_scope.cancel()
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()
            ki_self()
            with pytest.raises(KeyboardInterrupt):
                await _core.checkpoint()
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()

    _core.run(main_8)


def test_ki_is_good_neighbor() -> None:
    # in the unlikely event someone overwrites our signal handler, we leave
    # the overwritten one be
    try:
        orig = signal.getsignal(signal.SIGINT)

        def my_handler(signum: object, frame: object) -> None:  # pragma: no cover
            pass

        async def main() -> None:
            signal.signal(signal.SIGINT, my_handler)

        _core.run(main)

        assert signal.getsignal(signal.SIGINT) is my_handler
    finally:
        signal.signal(signal.SIGINT, orig)


# Regression test for #461
# don't know if _active not being visible is a problem
def test_ki_with_broken_threads() -> None:
    thread = threading.main_thread()

    # scary!
    original = threading._active[thread.ident]  # type: ignore[attr-defined]

    # put this in a try finally so we don't have a chance of cascading a
    # breakage down to everything else
    try:
        del threading._active[thread.ident]  # type: ignore[attr-defined]

        @_core.enable_ki_protection
        async def inner() -> None:
            assert signal.getsignal(signal.SIGINT) != signal.default_int_handler

        _core.run(inner)
    finally:
        threading._active[thread.ident] = original  # type: ignore[attr-defined]


_T = TypeVar("_T")


def _identity(v: _T) -> _T:
    return v


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "it was decided not to protect against this case, see discussion in: "
        "https://github.com/python-trio/trio/pull/3110#discussion_r1802123644"
    ),
)
async def test_ki_does_not_leak_across_different_calls_to_inner_functions() -> None:
    assert not _core.currently_ki_protected()

    def factory(enabled: bool) -> Callable[[], bool]:
        @_core.enable_ki_protection if enabled else _identity
        def decorated() -> bool:
            return _core.currently_ki_protected()

        return decorated

    decorated_enabled = factory(True)
    decorated_disabled = factory(False)
    assert decorated_enabled()
    assert not decorated_disabled()


async def test_ki_protection_check_does_not_freeze_locals() -> None:
    class A:
        pass

    a = A()
    wr_a = weakref.ref(a)
    assert not _core.currently_ki_protected()
    del a
    if sys.implementation.name == "pypy":
        gc_collect_harder()
    assert wr_a() is None


def test_identity_weakref_internals() -> None:
    """To cover the parts WeakKeyIdentityDictionary won't ever reach."""

    class A:
        def __eq__(self, other: object) -> bool:
            return False

    a = A()
    assert a != a
    wr = _ki._IdRef(a)
    wr_other_is_self = wr

    # dict always checks identity before equality so we need to do it here
    # to cover `if self is other`
    assert wr == wr_other_is_self

    # we want to cover __ne__ and `return NotImplemented`
    assert wr != object()


def test_weak_key_identity_dict_remove_callback_keyerror() -> None:
    """We need to cover the KeyError in self._remove."""

    class A:
        def __eq__(self, other: object) -> bool:
            return False

    a = A()
    assert a != a
    d: _ki.WeakKeyIdentityDictionary[A, bool] = _ki.WeakKeyIdentityDictionary()

    d[a] = True

    data_copy = d._data.copy()
    d._data.clear()
    del a

    gc_collect_harder()  # would call sys.unraisablehook if there's a problem
    assert data_copy


def test_weak_key_identity_dict_remove_callback_selfref_expired() -> None:
    """We need to cover the KeyError in self._remove."""

    class A:
        def __eq__(self, other: object) -> bool:
            return False

    a = A()
    assert a != a
    d: _ki.WeakKeyIdentityDictionary[A, bool] = _ki.WeakKeyIdentityDictionary()

    d[a] = True

    data_copy = d._data.copy()
    wr_d = weakref.ref(d)
    del d
    gc_collect_harder()  # would call sys.unraisablehook if there's a problem
    assert wr_d() is None
    del a
    gc_collect_harder()
    assert data_copy


@_core.enable_ki_protection
async def _protected_async_gen_fn() -> AsyncGenerator[None, None]:
    yield


@_core.enable_ki_protection
async def _protected_async_fn() -> None:
    pass


@_core.enable_ki_protection
def _protected_gen_fn() -> Generator[None, None, None]:
    yield


@_core.disable_ki_protection
async def _unprotected_async_gen_fn() -> AsyncGenerator[None, None]:
    yield


@_core.disable_ki_protection
async def _unprotected_async_fn() -> None:
    pass


@_core.disable_ki_protection
def _unprotected_gen_fn() -> Generator[None, None, None]:
    yield


async def _consume_async_generator(agen: AsyncGenerator[None, None]) -> None:
    try:
        with pytest.raises(StopAsyncIteration):
            while True:
                await agen.asend(None)
    finally:
        await agen.aclose()


def _consume_function_for_coverage(
    fn: Callable[[], object],
) -> None:
    result = fn()
    if inspect.isasyncgen(result):
        result = _consume_async_generator(result)

    assert inspect.isgenerator(result) or inspect.iscoroutine(result)
    with pytest.raises(StopIteration):
        while True:
            result.send(None)


def test_enable_disable_ki_protection_passes_on_inspect_flags() -> None:
    assert inspect.isasyncgenfunction(_protected_async_gen_fn)
    _consume_function_for_coverage(_protected_async_gen_fn)
    assert inspect.iscoroutinefunction(_protected_async_fn)
    _consume_function_for_coverage(_protected_async_fn)
    assert inspect.isgeneratorfunction(_protected_gen_fn)
    _consume_function_for_coverage(_protected_gen_fn)
    assert inspect.isasyncgenfunction(_unprotected_async_gen_fn)
    _consume_function_for_coverage(_unprotected_async_gen_fn)
    assert inspect.iscoroutinefunction(_unprotected_async_fn)
    _consume_function_for_coverage(_unprotected_async_fn)
    assert inspect.isgeneratorfunction(_unprotected_gen_fn)
    _consume_function_for_coverage(_unprotected_gen_fn)

# === NexusCore/openenv\Lib\site-packages\gitdb\fun.py ===
# Copyright (C) 2010, 2011 Sebastian Thiel (byronimo@gmail.com) and contributors
#
# This module is part of GitDB and is released under
# the New BSD License: https://opensource.org/license/bsd-3-clause/
"""Contains basic c-functions which usually contain performance critical code
Keeping this code separate from the beginning makes it easier to out-source
it into c later, if required"""

import zlib
from gitdb.util import byte_ord
decompressobj = zlib.decompressobj

import mmap
from itertools import islice
from functools import reduce

from gitdb.const import NULL_BYTE, BYTE_SPACE
from gitdb.utils.encoding import force_text
from gitdb.typ import (
    str_blob_type,
    str_commit_type,
    str_tree_type,
    str_tag_type,
)

from io import StringIO

# INVARIANTS
OFS_DELTA = 6
REF_DELTA = 7
delta_types = (OFS_DELTA, REF_DELTA)

type_id_to_type_map = {
    0: b'',             # EXT 1
    1: str_commit_type,
    2: str_tree_type,
    3: str_blob_type,
    4: str_tag_type,
    5: b'',             # EXT 2
    OFS_DELTA: "OFS_DELTA",    # OFFSET DELTA
    REF_DELTA: "REF_DELTA"     # REFERENCE DELTA
}

type_to_type_id_map = {
    str_commit_type: 1,
    str_tree_type: 2,
    str_blob_type: 3,
    str_tag_type: 4,
    "OFS_DELTA": OFS_DELTA,
    "REF_DELTA": REF_DELTA,
}

# used when dealing with larger streams
chunk_size = 1000 * mmap.PAGESIZE

__all__ = ('is_loose_object', 'loose_object_header_info', 'msb_size', 'pack_object_header_info',
           'write_object', 'loose_object_header', 'stream_copy', 'apply_delta_data',
           'is_equal_canonical_sha', 'connect_deltas', 'DeltaChunkList', 'create_pack_object_header')


#{ Structures

def _set_delta_rbound(d, size):
    """Truncate the given delta to the given size
    :param size: size relative to our target offset, may not be 0, must be smaller or equal
        to our size
    :return: d"""
    d.ts = size

    # NOTE: data is truncated automatically when applying the delta
    # MUST NOT DO THIS HERE
    return d


def _move_delta_lbound(d, bytes):
    """Move the delta by the given amount of bytes, reducing its size so that its
    right bound stays static
    :param bytes: amount of bytes to move, must be smaller than delta size
    :return: d"""
    if bytes == 0:
        return

    d.to += bytes
    d.so += bytes
    d.ts -= bytes
    if d.data is not None:
        d.data = d.data[bytes:]
    # END handle data

    return d


def delta_duplicate(src):
    return DeltaChunk(src.to, src.ts, src.so, src.data)


def delta_chunk_apply(dc, bbuf, write):
    """Apply own data to the target buffer
    :param bbuf: buffer providing source bytes for copy operations
    :param write: write method to call with data to write"""
    if dc.data is None:
        # COPY DATA FROM SOURCE
        write(bbuf[dc.so:dc.so + dc.ts])
    else:
        # APPEND DATA
        # what's faster: if + 4 function calls or just a write with a slice ?
        # Considering data can be larger than 127 bytes now, it should be worth it
        if dc.ts < len(dc.data):
            write(dc.data[:dc.ts])
        else:
            write(dc.data)
        # END handle truncation
    # END handle chunk mode


class DeltaChunk:

    """Represents a piece of a delta, it can either add new data, or copy existing
    one from a source buffer"""
    __slots__ = (
        'to',       # start offset in the target buffer in bytes
                    'ts',       # size of this chunk in the target buffer in bytes
                    'so',       # start offset in the source buffer in bytes or None
                    'data',     # chunk of bytes to be added to the target buffer,
                                # DeltaChunkList to use as base, or None
    )

    def __init__(self, to, ts, so, data):
        self.to = to
        self.ts = ts
        self.so = so
        self.data = data

    def __repr__(self):
        return "DeltaChunk(%i, %i, %s, %s)" % (self.to, self.ts, self.so, self.data or "")

    #{ Interface

    def rbound(self):
        return self.to + self.ts

    def has_data(self):
        """:return: True if the instance has data to add to the target stream"""
        return self.data is not None

    #} END interface


def _closest_index(dcl, absofs):
    """:return: index at which the given absofs should be inserted. The index points
    to the DeltaChunk with a target buffer absofs that equals or is greater than
    absofs.
    **Note:** global method for performance only, it belongs to DeltaChunkList"""
    lo = 0
    hi = len(dcl)
    while lo < hi:
        mid = (lo + hi) / 2
        dc = dcl[mid]
        if dc.to > absofs:
            hi = mid
        elif dc.rbound() > absofs or dc.to == absofs:
            return mid
        else:
            lo = mid + 1
        # END handle bound
    # END for each delta absofs
    return len(dcl) - 1


def delta_list_apply(dcl, bbuf, write):
    """Apply the chain's changes and write the final result using the passed
    write function.
    :param bbuf: base buffer containing the base of all deltas contained in this
        list. It will only be used if the chunk in question does not have a base
        chain.
    :param write: function taking a string of bytes to write to the output"""
    for dc in dcl:
        delta_chunk_apply(dc, bbuf, write)
    # END for each dc


def delta_list_slice(dcl, absofs, size, ndcl):
    """:return: Subsection of this  list at the given absolute  offset, with the given
        size in bytes.
    :return: None"""
    cdi = _closest_index(dcl, absofs)   # delta start index
    cd = dcl[cdi]
    slen = len(dcl)
    lappend = ndcl.append

    if cd.to != absofs:
        tcd = DeltaChunk(cd.to, cd.ts, cd.so, cd.data)
        _move_delta_lbound(tcd, absofs - cd.to)
        tcd.ts = min(tcd.ts, size)
        lappend(tcd)
        size -= tcd.ts
        cdi += 1
    # END lbound overlap handling

    while cdi < slen and size:
        # are we larger than the current block
        cd = dcl[cdi]
        if cd.ts <= size:
            lappend(DeltaChunk(cd.to, cd.ts, cd.so, cd.data))
            size -= cd.ts
        else:
            tcd = DeltaChunk(cd.to, cd.ts, cd.so, cd.data)
            tcd.ts = size
            lappend(tcd)
            size -= tcd.ts
            break
        # END hadle size
        cdi += 1
    # END for each chunk


class DeltaChunkList(list):

    """List with special functionality to deal with DeltaChunks.
    There are two types of lists we represent. The one was created bottom-up, working
    towards the latest delta, the other kind was created top-down, working from the
    latest delta down to the earliest ancestor. This attribute is queryable
    after all processing with is_reversed."""

    __slots__ = tuple()

    def rbound(self):
        """:return: rightmost extend in bytes, absolute"""
        if len(self) == 0:
            return 0
        return self[-1].rbound()

    def lbound(self):
        """:return: leftmost byte at which this chunklist starts"""
        if len(self) == 0:
            return 0
        return self[0].to

    def size(self):
        """:return: size of bytes as measured by our delta chunks"""
        return self.rbound() - self.lbound()

    def apply(self, bbuf, write):
        """Only used by public clients, internally we only use the global routines
        for performance"""
        return delta_list_apply(self, bbuf, write)

    def compress(self):
        """Alter the list to reduce the amount of nodes. Currently we concatenate
        add-chunks
        :return: self"""
        slen = len(self)
        if slen < 2:
            return self
        i = 0

        first_data_index = None
        while i < slen:
            dc = self[i]
            i += 1
            if dc.data is None:
                if first_data_index is not None and i - 2 - first_data_index > 1:
                    # if first_data_index is not None:
                    nd = StringIO()                     # new data
                    so = self[first_data_index].to      # start offset in target buffer
                    for x in range(first_data_index, i - 1):
                        xdc = self[x]
                        nd.write(xdc.data[:xdc.ts])
                    # END collect data

                    del(self[first_data_index:i - 1])
                    buf = nd.getvalue()
                    self.insert(first_data_index, DeltaChunk(so, len(buf), 0, buf))

                    slen = len(self)
                    i = first_data_index + 1

                # END concatenate data
                first_data_index = None
                continue
            # END skip non-data chunks

            if first_data_index is None:
                first_data_index = i - 1
        # END iterate list

        # if slen_orig != len(self):
        #   print "INFO: Reduced delta list len to %f %% of former size" % ((float(len(self)) / slen_orig) * 100)
        return self

    def check_integrity(self, target_size=-1):
        """Verify the list has non-overlapping chunks only, and the total size matches
        target_size
        :param target_size: if not -1, the total size of the chain must be target_size
        :raise AssertionError: if the size doesn't match"""
        if target_size > -1:
            assert self[-1].rbound() == target_size
            assert reduce(lambda x, y: x + y, (d.ts for d in self), 0) == target_size
        # END target size verification

        if len(self) < 2:
            return

        # check data
        for dc in self:
            assert dc.ts > 0
            if dc.has_data():
                assert len(dc.data) >= dc.ts
        # END for each dc

        left = islice(self, 0, len(self) - 1)
        right = iter(self)
        right.next()
        # this is very pythonic - we might have just use index based access here,
        # but this could actually be faster
        for lft, rgt in zip(left, right):
            assert lft.rbound() == rgt.to
            assert lft.to + lft.ts == rgt.to
        # END for each pair


class TopdownDeltaChunkList(DeltaChunkList):

    """Represents a list which is generated by feeding its ancestor streams one by
    one"""
    __slots__ = tuple()

    def connect_with_next_base(self, bdcl):
        """Connect this chain with the next level of our base delta chunklist.
        The goal in this game is to mark as many of our chunks rigid, hence they
        cannot be changed by any of the upcoming bases anymore. Once all our
        chunks are marked like that, we can stop all processing
        :param bdcl: data chunk list being one of our bases. They must be fed in
            consecutively and in order, towards the earliest ancestor delta
        :return: True if processing was done. Use it to abort processing of
            remaining streams if False is returned"""
        nfc = 0                             # number of frozen chunks
        dci = 0                             # delta chunk index
        slen = len(self)                    # len of self
        ccl = list()                        # temporary list
        while dci < slen:
            dc = self[dci]
            dci += 1

            # all add-chunks which are already topmost don't need additional processing
            if dc.data is not None:
                nfc += 1
                continue
            # END skip add chunks

            # copy chunks
            # integrate the portion of the base list into ourselves. Lists
            # dont support efficient insertion ( just one at a time ), but for now
            # we live with it. Internally, its all just a 32/64bit pointer, and
            # the portions of moved memory should be smallish. Maybe we just rebuild
            # ourselves in order to reduce the amount of insertions ...
            del(ccl[:])
            delta_list_slice(bdcl, dc.so, dc.ts, ccl)

            # move the target bounds into place to match with our chunk
            ofs = dc.to - dc.so
            for cdc in ccl:
                cdc.to += ofs
            # END update target bounds

            if len(ccl) == 1:
                self[dci - 1] = ccl[0]
            else:
                # maybe try to compute the expenses here, and pick the right algorithm
                # It would normally be faster than copying everything physically though
                # TODO: Use a deque here, and decide by the index whether to extend
                # or extend left !
                post_dci = self[dci:]
                del(self[dci - 1:])           # include deletion of dc
                self.extend(ccl)
                self.extend(post_dci)

                slen = len(self)
                dci += len(ccl) - 1           # deleted dc, added rest

            # END handle chunk replacement
        # END for each chunk

        if nfc == slen:
            return False
        # END handle completeness
        return True


#} END structures

#{ Routines

def is_loose_object(m):
    """
    :return: True the file contained in memory map m appears to be a loose object.
        Only the first two bytes are needed"""
    b0, b1 = map(ord, m[:2])
    word = (b0 << 8) + b1
    return b0 == 0x78 and (word % 31) == 0


def loose_object_header_info(m):
    """
    :return: tuple(type_string, uncompressed_size_in_bytes) the type string of the
        object as well as its uncompressed size in bytes.
    :param m: memory map from which to read the compressed object data"""
    decompress_size = 8192      # is used in cgit as well
    hdr = decompressobj().decompress(m, decompress_size)
    type_name, size = hdr[:hdr.find(NULL_BYTE)].split(BYTE_SPACE)

    return type_name, int(size)


def pack_object_header_info(data):
    """
    :return: tuple(type_id, uncompressed_size_in_bytes, byte_offset)
        The type_id should be interpreted according to the ``type_id_to_type_map`` map
        The byte-offset specifies the start of the actual zlib compressed datastream
    :param m: random-access memory, like a string or memory map"""
    c = byte_ord(data[0])           # first byte
    i = 1                           # next char to read
    type_id = (c >> 4) & 7          # numeric type
    size = c & 15                   # starting size
    s = 4                           # starting bit-shift size
    while c & 0x80:
        c = byte_ord(data[i])
        i += 1
        size += (c & 0x7f) << s
        s += 7
    # END character loop
    # end performance at expense of maintenance ...
    return (type_id, size, i)


def create_pack_object_header(obj_type, obj_size):
    """
    :return: string defining the pack header comprised of the object type
        and its incompressed size in bytes

    :param obj_type: pack type_id of the object
    :param obj_size: uncompressed size in bytes of the following object stream"""
    c = 0       # 1 byte
    hdr = bytearray()  # output string

    c = (obj_type << 4) | (obj_size & 0xf)
    obj_size >>= 4
    while obj_size:
        hdr.append(c | 0x80)
        c = obj_size & 0x7f
        obj_size >>= 7
    # END until size is consumed
    hdr.append(c)
    # end handle interpreter
    return hdr


def msb_size(data, offset=0):
    """
    :return: tuple(read_bytes, size) read the msb size from the given random
        access data starting at the given byte offset"""
    size = 0
    i = 0
    l = len(data)
    hit_msb = False
    while i < l:
        c = data[i + offset]
        size |= (c & 0x7f) << i * 7
        i += 1
        if not c & 0x80:
            hit_msb = True
            break
        # END check msb bit
    # END while in range
    # end performance ...
    if not hit_msb:
        raise AssertionError("Could not find terminating MSB byte in data stream")
    return i + offset, size


def loose_object_header(type, size):
    """
    :return: bytes representing the loose object header, which is immediately
        followed by the content stream of size 'size'"""
    return ('%s %i\0' % (force_text(type), size)).encode('ascii')


def write_object(type, size, read, write, chunk_size=chunk_size):
    """
    Write the object as identified by type, size and source_stream into the
    target_stream

    :param type: type string of the object
    :param size: amount of bytes to write from source_stream
    :param read: read method of a stream providing the content data
    :param write: write method of the output stream
    :param close_target_stream: if True, the target stream will be closed when
        the routine exits, even if an error is thrown
    :return: The actual amount of bytes written to stream, which includes the header and a trailing newline"""
    tbw = 0                                             # total num bytes written

    # WRITE HEADER: type SP size NULL
    tbw += write(loose_object_header(type, size))
    tbw += stream_copy(read, write, size, chunk_size)

    return tbw


def stream_copy(read, write, size, chunk_size):
    """
    Copy a stream up to size bytes using the provided read and write methods,
    in chunks of chunk_size

    **Note:** its much like stream_copy utility, but operates just using methods"""
    dbw = 0                                             # num data bytes written

    # WRITE ALL DATA UP TO SIZE
    while True:
        cs = min(chunk_size, size - dbw)
        # NOTE: not all write methods return the amount of written bytes, like
        # mmap.write. Its bad, but we just deal with it ... perhaps its not
        # even less efficient
        # data_len = write(read(cs))
        # dbw += data_len
        data = read(cs)
        data_len = len(data)
        dbw += data_len
        write(data)
        if data_len < cs or dbw == size:
            break
        # END check for stream end
    # END duplicate data
    return dbw


def connect_deltas(dstreams):
    """
    Read the condensed delta chunk information from dstream and merge its information
        into a list of existing delta chunks

    :param dstreams: iterable of delta stream objects, the delta to be applied last
        comes first, then all its ancestors in order
    :return: DeltaChunkList, containing all operations to apply"""
    tdcl = None                         # topmost dcl

    dcl = tdcl = TopdownDeltaChunkList()
    for dsi, ds in enumerate(dstreams):
        # print "Stream", dsi
        db = ds.read()
        delta_buf_size = ds.size

        # read header
        i, base_size = msb_size(db)
        i, target_size = msb_size(db, i)

        # interpret opcodes
        tbw = 0                     # amount of target bytes written
        while i < delta_buf_size:
            c = ord(db[i])
            i += 1
            if c & 0x80:
                cp_off, cp_size = 0, 0
                if (c & 0x01):
                    cp_off = ord(db[i])
                    i += 1
                if (c & 0x02):
                    cp_off |= (ord(db[i]) << 8)
                    i += 1
                if (c & 0x04):
                    cp_off |= (ord(db[i]) << 16)
                    i += 1
                if (c & 0x08):
                    cp_off |= (ord(db[i]) << 24)
                    i += 1
                if (c & 0x10):
                    cp_size = ord(db[i])
                    i += 1
                if (c & 0x20):
                    cp_size |= (ord(db[i]) << 8)
                    i += 1
                if (c & 0x40):
                    cp_size |= (ord(db[i]) << 16)
                    i += 1

                if not cp_size:
                    cp_size = 0x10000

                rbound = cp_off + cp_size
                if (rbound < cp_size or
                        rbound > base_size):
                    break

                dcl.append(DeltaChunk(tbw, cp_size, cp_off, None))
                tbw += cp_size
            elif c:
                # NOTE: in C, the data chunks should probably be concatenated here.
                # In python, we do it as a post-process
                dcl.append(DeltaChunk(tbw, c, 0, db[i:i + c]))
                i += c
                tbw += c
            else:
                raise ValueError("unexpected delta opcode 0")
            # END handle command byte
        # END while processing delta data

        dcl.compress()

        # merge the lists !
        if dsi > 0:
            if not tdcl.connect_with_next_base(dcl):
                break
        # END handle merge

        # prepare next base
        dcl = DeltaChunkList()
    # END for each delta stream

    return tdcl


def apply_delta_data(src_buf, src_buf_size, delta_buf, delta_buf_size, write):
    """
    Apply data from a delta buffer using a source buffer to the target file

    :param src_buf: random access data from which the delta was created
    :param src_buf_size: size of the source buffer in bytes
    :param delta_buf_size: size for the delta buffer in bytes
    :param delta_buf: random access delta data
    :param write: write method taking a chunk of bytes

    **Note:** transcribed to python from the similar routine in patch-delta.c"""
    i = 0
    db = delta_buf
    while i < delta_buf_size:
        c = db[i]
        i += 1
        if c & 0x80:
            cp_off, cp_size = 0, 0
            if (c & 0x01):
                cp_off = db[i]
                i += 1
            if (c & 0x02):
                cp_off |= (db[i] << 8)
                i += 1
            if (c & 0x04):
                cp_off |= (db[i] << 16)
                i += 1
            if (c & 0x08):
                cp_off |= (db[i] << 24)
                i += 1
            if (c & 0x10):
                cp_size = db[i]
                i += 1
            if (c & 0x20):
                cp_size |= (db[i] << 8)
                i += 1
            if (c & 0x40):
                cp_size |= (db[i] << 16)
                i += 1

            if not cp_size:
                cp_size = 0x10000

            rbound = cp_off + cp_size
            if (rbound < cp_size or
                    rbound > src_buf_size):
                break
            write(src_buf[cp_off:cp_off + cp_size])
        elif c:
            write(db[i:i + c])
            i += c
        else:
            raise ValueError("unexpected delta opcode 0")
        # END handle command byte
    # END while processing delta data

    # yes, lets use the exact same error message that git uses :)
    assert i == delta_buf_size, "delta replay has gone wild"


def is_equal_canonical_sha(canonical_length, match, sha1):
    """
    :return: True if the given lhs and rhs 20 byte binary shas
        The comparison will take the canonical_length of the match sha into account,
        hence the comparison will only use the last 4 bytes for uneven canonical representations
    :param match: less than 20 byte sha
    :param sha1: 20 byte sha"""
    binary_length = canonical_length // 2
    if match[:binary_length] != sha1[:binary_length]:
        return False

    if canonical_length - binary_length and \
            (byte_ord(match[-1]) ^ byte_ord(sha1[len(match) - 1])) & 0xf0:
        return False
    # END handle uneven canonnical length
    return True

#} END routines


try:
    from gitdb_speedups._perf import connect_deltas
except ImportError:
    pass

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\scintilla\formatter.py ===
# Does Python source formatting for Scintilla controls.
import array
import string

import win32api
import win32con
import win32ui

from . import scintillacon

WM_KICKIDLE = 0x036A

# Used to indicate that style should use default color
from win32con import CLR_INVALID

debugging = 0
if debugging:
    # Output must go to another process else the result of
    # the printing itself will trigger again trigger a trace.

    import win32trace
    import win32traceutil

    def trace(*args):
        win32trace.write(" ".join(map(str, args)) + "\n")

else:
    trace = lambda *args: None


class Style:
    """Represents a single format"""

    def __init__(self, name, format, background=CLR_INVALID):
        self.name = name  # Name the format representes eg, "String", "Class"
        # Default background for each style is only used when there are no
        # saved settings (generally on first startup)
        self.background = self.default_background = background
        if isinstance(format, str):
            self.aliased = format
            self.format = None
        else:
            self.format = format
            self.aliased = None
        self.stylenum = None  # Not yet registered.

    def IsBasedOnDefault(self):
        return len(self.format) == 5

    # If the currently extended font defintion matches the
    # default format, restore the format to the "simple" format.
    def NormalizeAgainstDefault(self, defaultFormat):
        if self.IsBasedOnDefault():
            return 0  # No more to do, and not changed.
        bIsDefault = (
            self.format[7] == defaultFormat[7] and self.format[2] == defaultFormat[2]
        )
        if bIsDefault:
            self.ForceAgainstDefault()
        return bIsDefault

    def ForceAgainstDefault(self):
        self.format = self.format[:5]

    def GetCompleteFormat(self, defaultFormat):
        # Get the complete style after applying any relevant defaults.
        if len(self.format) == 5:  # It is a default one
            fmt = self.format + defaultFormat[5:]
        else:
            fmt = self.format
        flags = (
            win32con.CFM_BOLD
            | win32con.CFM_CHARSET
            | win32con.CFM_COLOR
            | win32con.CFM_FACE
            | win32con.CFM_ITALIC
            | win32con.CFM_SIZE
        )
        return (flags,) + fmt[1:]


# The Formatter interface
# used primarily when the actual formatting is done by Scintilla!
class FormatterBase:
    def __init__(self, scintilla):
        self.scintilla = scintilla
        self.baseFormatFixed = (-402653169, 0, 200, 0, 0, 0, 49, "Courier New")
        self.baseFormatProp = (-402653169, 0, 200, 0, 0, 0, 49, "Arial")
        self.bUseFixed = 1
        self.styles = {}  # Indexed by name
        self.styles_by_id = {}  # Indexed by allocated ID.
        self.SetStyles()

    def HookFormatter(self, parent=None):
        raise NotImplementedError

    # Used by the IDLE extensions to quickly determine if a character is a string.
    def GetStringStyle(self, pos):
        try:
            style = self.styles_by_id[self.scintilla.SCIGetStyleAt(pos)]
        except KeyError:
            # A style we don't know about - probably not even a .py file - can't be a string
            return None
        if style.name in self.string_style_names:
            return style
        return None

    def RegisterStyle(self, style, stylenum):
        assert stylenum is not None, "We must have a style number"
        assert style.stylenum is None, "Style has already been registered"
        assert stylenum not in self.styles, "We are reusing a style number!"
        style.stylenum = stylenum
        self.styles[style.name] = style
        self.styles_by_id[stylenum] = style

    def SetStyles(self):
        raise NotImplementedError

    def GetSampleText(self):
        return "Sample Text for the Format Dialog"

    def GetDefaultFormat(self):
        if self.bUseFixed:
            return self.baseFormatFixed
        return self.baseFormatProp

    # Update the control with the new style format.
    def _ReformatStyle(self, style):
        ## Selection (background only for now)
        ## Passing False for WPARAM to SCI_SETSELBACK is documented as resetting to scintilla default,
        ## but does not work - selection background is not visible at all.
        ## Default value in SPECIAL_STYLES taken from scintilla source.
        if style.name == STYLE_SELECTION:
            clr = style.background
            self.scintilla.SendScintilla(scintillacon.SCI_SETSELBACK, True, clr)

            ## Can't change font for selection, but could set color
            ## However, the font color dropbox has no option for default, and thus would
            ## always override syntax coloring
            ## clr = style.format[4]
            ## self.scintilla.SendScintilla(scintillacon.SCI_SETSELFORE, clr != CLR_INVALID, clr)
            return

        assert style.stylenum is not None, "Unregistered style."
        # print("Reformat style", style.name, style.stylenum)
        scintilla = self.scintilla
        stylenum = style.stylenum
        # Now we have the style number, indirect for the actual style.
        if style.aliased is not None:
            style = self.styles[style.aliased]
        f = style.format
        if style.IsBasedOnDefault():
            baseFormat = self.GetDefaultFormat()
        else:
            baseFormat = f
        scintilla.SCIStyleSetFore(stylenum, f[4])
        scintilla.SCIStyleSetFont(stylenum, baseFormat[7], baseFormat[5])
        if f[1] & 1:
            scintilla.SCIStyleSetBold(stylenum, 1)
        else:
            scintilla.SCIStyleSetBold(stylenum, 0)
        if f[1] & 2:
            scintilla.SCIStyleSetItalic(stylenum, 1)
        else:
            scintilla.SCIStyleSetItalic(stylenum, 0)
        scintilla.SCIStyleSetSize(stylenum, int(baseFormat[2] / 20))
        scintilla.SCIStyleSetEOLFilled(stylenum, 1)  # Only needed for unclosed strings.

        ## Default style background to whitespace background if set,
        ##	otherwise use system window color
        bg = style.background
        if bg == CLR_INVALID:
            bg = self.styles[STYLE_DEFAULT].background
        if bg == CLR_INVALID:
            bg = win32api.GetSysColor(win32con.COLOR_WINDOW)
        scintilla.SCIStyleSetBack(stylenum, bg)

    def GetStyleByNum(self, stylenum):
        return self.styles_by_id[stylenum]

    def ApplyFormattingStyles(self, bReload=1):
        if bReload:
            self.LoadPreferences()
        baseFormat = self.GetDefaultFormat()
        defaultStyle = Style("default", baseFormat)
        defaultStyle.stylenum = scintillacon.STYLE_DEFAULT
        self._ReformatStyle(defaultStyle)
        for style in self.styles.values():
            if style.aliased is None:
                style.NormalizeAgainstDefault(baseFormat)
            self._ReformatStyle(style)
        self.scintilla.InvalidateRect()

    # Some functions for loading and saving preferences.  By default
    # an INI file (well, MFC maps this to the registry) is used.
    def LoadPreferences(self):
        self.baseFormatFixed = eval(
            self.LoadPreference("Base Format Fixed", str(self.baseFormatFixed))
        )
        self.baseFormatProp = eval(
            self.LoadPreference("Base Format Proportional", str(self.baseFormatProp))
        )
        self.bUseFixed = int(self.LoadPreference("Use Fixed", 1))

        for style in self.styles.values():
            new = self.LoadPreference(style.name, str(style.format))
            try:
                style.format = eval(new)
            except:
                print("Error loading style data for", style.name)
            # Use "vanilla" background hardcoded in PYTHON_STYLES if no settings in registry
            style.background = int(
                self.LoadPreference(
                    style.name + " background", style.default_background
                )
            )

    def LoadPreference(self, name, default):
        return win32ui.GetProfileVal("Format", name, default)

    def SavePreferences(self):
        self.SavePreference("Base Format Fixed", str(self.baseFormatFixed))
        self.SavePreference("Base Format Proportional", str(self.baseFormatProp))
        self.SavePreference("Use Fixed", self.bUseFixed)
        for style in self.styles.values():
            if style.aliased is None:
                self.SavePreference(style.name, str(style.format))
                bg_name = style.name + " background"
                self.SavePreference(bg_name, style.background)

    def SavePreference(self, name, value):
        win32ui.WriteProfileVal("Format", name, value)


# An abstract formatter
# For all formatters we actually implement here.
# (as opposed to those formatters built in to Scintilla)
class Formatter(FormatterBase):
    def __init__(self, scintilla):
        self.bCompleteWhileIdle = 0
        self.bHaveIdleHandler = 0  # Don't currently have an idle handle
        self.nextstylenum = 0
        FormatterBase.__init__(self, scintilla)

    def HookFormatter(self, parent=None):
        if parent is None:
            parent = self.scintilla.GetParent()  # was GetParentFrame()!?
        parent.HookNotify(self.OnStyleNeeded, scintillacon.SCN_STYLENEEDED)

    def OnStyleNeeded(self, std, extra):
        notify = self.scintilla.SCIUnpackNotifyMessage(extra)
        endStyledChar = self.scintilla.SendScintilla(scintillacon.SCI_GETENDSTYLED)
        lineEndStyled = self.scintilla.LineFromChar(endStyledChar)
        endStyled = self.scintilla.LineIndex(lineEndStyled)
        # print(
        #     "endPosPaint",
        #     endPosPaint,
        #     "endStyledChar",
        #     endStyledChar,
        #     "lineEndStyled",
        #     lineEndStyled,
        #     "endStyled",
        #     endStyled,
        # )
        self.Colorize(endStyled, notify.position)

    def ColorSeg(self, start, end, styleName):
        end += 1
        # 		assert end-start>=0, "Can't have negative styling"
        stylenum = self.styles[styleName].stylenum
        while start < end:
            self.style_buffer[start] = stylenum
            start += 1
        # self.scintilla.SCISetStyling(end - start + 1, stylenum)

    def RegisterStyle(self, style, stylenum=None):
        if stylenum is None:
            stylenum = self.nextstylenum
            self.nextstylenum += 1
        FormatterBase.RegisterStyle(self, style, stylenum)

    def ColorizeString(self, str, styleStart):
        raise RuntimeError("You must override this method")

    def Colorize(self, start=0, end=-1):
        scintilla = self.scintilla
        # scintilla's formatting is all done in terms of utf, so
        # we work with utf8 bytes instead of unicode.  This magically
        # works as any extended chars found in the utf8 don't change
        # the semantics.
        stringVal = scintilla.GetTextRange(start, end, decode=False)
        if start > 0:
            stylenum = scintilla.SCIGetStyleAt(start - 1)
            styleStart = self.GetStyleByNum(stylenum).name
        else:
            styleStart = None
        # 		trace("Coloring", start, end, end-start, len(stringVal), styleStart, self.scintilla.SCIGetCharAt(start))
        scintilla.SCIStartStyling(start, 31)
        self.style_buffer = array.array("b", (0,) * len(stringVal))
        self.ColorizeString(stringVal, styleStart)
        scintilla.SCISetStylingEx(self.style_buffer)
        self.style_buffer = None
        # 		trace("After styling, end styled is", self.scintilla.SCIGetEndStyled())
        if (
            self.bCompleteWhileIdle
            and not self.bHaveIdleHandler
            and end != -1
            and end < scintilla.GetTextLength()
        ):
            self.bHaveIdleHandler = 1
            win32ui.GetApp().AddIdleHandler(self.DoMoreColoring)
            # Kicking idle makes the app seem slower when initially repainting!

    # 			win32ui.GetMainFrame().PostMessage(WM_KICKIDLE, 0, 0)

    def DoMoreColoring(self, handler, count):
        try:
            scintilla = self.scintilla
            endStyled = scintilla.SCIGetEndStyled()
            lineStartStyled = scintilla.LineFromChar(endStyled)
            start = scintilla.LineIndex(lineStartStyled)
            end = scintilla.LineIndex(lineStartStyled + 1)
            textlen = scintilla.GetTextLength()
            if end < 0:
                end = textlen

            finished = end >= textlen
            self.Colorize(start, end)
        except (win32ui.error, AttributeError):
            # Window may have closed before we finished - no big deal!
            finished = 1

        if finished:
            self.bHaveIdleHandler = 0
            win32ui.GetApp().DeleteIdleHandler(handler)
        return not finished


# A Formatter that knows how to format Python source
from keyword import iskeyword, kwlist

wordstarts = "_0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
wordchars = "._0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
operators = "%^&*()-+=|{}[]:;<>,/?!.~"

STYLE_DEFAULT = "Whitespace"
STYLE_COMMENT = "Comment"
STYLE_COMMENT_BLOCK = "Comment Blocks"
STYLE_NUMBER = "Number"
STYLE_STRING = "String"
STYLE_SQSTRING = "SQ String"
STYLE_TQSSTRING = "TQS String"
STYLE_TQDSTRING = "TQD String"
STYLE_KEYWORD = "Keyword"
STYLE_CLASS = "Class"
STYLE_METHOD = "Method"
STYLE_OPERATOR = "Operator"
STYLE_IDENTIFIER = "Identifier"
STYLE_BRACE = "Brace/Paren - matching"
STYLE_BRACEBAD = "Brace/Paren - unmatched"
STYLE_STRINGEOL = "String with no terminator"
STYLE_LINENUMBER = "Line numbers"
STYLE_INDENTGUIDE = "Indent guide"
STYLE_SELECTION = "Selection"

STRING_STYLES = [
    STYLE_STRING,
    STYLE_SQSTRING,
    STYLE_TQSSTRING,
    STYLE_TQDSTRING,
    STYLE_STRINGEOL,
]

# These styles can have any ID - they are not special to scintilla itself.
# However, if we use the built-in lexer, then we must use its style numbers
# so in that case, they _are_ special.
# (name, format, background, scintilla id)
PYTHON_STYLES = [
    (STYLE_DEFAULT, (0, 0, 200, 0, 0x808080), CLR_INVALID, scintillacon.SCE_P_DEFAULT),
    (
        STYLE_COMMENT,
        (0, 2, 200, 0, 0x008000),
        CLR_INVALID,
        scintillacon.SCE_P_COMMENTLINE,
    ),
    (
        STYLE_COMMENT_BLOCK,
        (0, 2, 200, 0, 0x808080),
        CLR_INVALID,
        scintillacon.SCE_P_COMMENTBLOCK,
    ),
    (STYLE_NUMBER, (0, 0, 200, 0, 0x808000), CLR_INVALID, scintillacon.SCE_P_NUMBER),
    (STYLE_STRING, (0, 0, 200, 0, 0x008080), CLR_INVALID, scintillacon.SCE_P_STRING),
    (STYLE_SQSTRING, STYLE_STRING, CLR_INVALID, scintillacon.SCE_P_CHARACTER),
    (STYLE_TQSSTRING, STYLE_STRING, CLR_INVALID, scintillacon.SCE_P_TRIPLE),
    (STYLE_TQDSTRING, STYLE_STRING, CLR_INVALID, scintillacon.SCE_P_TRIPLEDOUBLE),
    (STYLE_STRINGEOL, (0, 0, 200, 0, 0x000000), 0x008080, scintillacon.SCE_P_STRINGEOL),
    (STYLE_KEYWORD, (0, 1, 200, 0, 0x800000), CLR_INVALID, scintillacon.SCE_P_WORD),
    (STYLE_CLASS, (0, 1, 200, 0, 0xFF0000), CLR_INVALID, scintillacon.SCE_P_CLASSNAME),
    (STYLE_METHOD, (0, 1, 200, 0, 0x808000), CLR_INVALID, scintillacon.SCE_P_DEFNAME),
    (
        STYLE_OPERATOR,
        (0, 0, 200, 0, 0x000000),
        CLR_INVALID,
        scintillacon.SCE_P_OPERATOR,
    ),
    (
        STYLE_IDENTIFIER,
        (0, 0, 200, 0, 0x000000),
        CLR_INVALID,
        scintillacon.SCE_P_IDENTIFIER,
    ),
]

# These styles _always_ have this specific style number, regardless of
# internal or external formatter.
SPECIAL_STYLES = [
    (STYLE_BRACE, (0, 0, 200, 0, 0x000000), 0xFFFF80, scintillacon.STYLE_BRACELIGHT),
    (STYLE_BRACEBAD, (0, 0, 200, 0, 0x000000), 0x8EA5F2, scintillacon.STYLE_BRACEBAD),
    (
        STYLE_LINENUMBER,
        (0, 0, 200, 0, 0x000000),
        win32api.GetSysColor(win32con.COLOR_3DFACE),
        scintillacon.STYLE_LINENUMBER,
    ),
    (
        STYLE_INDENTGUIDE,
        (0, 0, 200, 0, 0x000000),
        CLR_INVALID,
        scintillacon.STYLE_INDENTGUIDE,
    ),
    ## Not actually a style; requires special handling to send appropriate messages to scintilla
    (
        STYLE_SELECTION,
        (0, 0, 200, 0, CLR_INVALID),
        win32api.RGB(0xC0, 0xC0, 0xC0),
        999999,
    ),
]

PythonSampleCode = """\
# Some Python
class Sample(Super):
  def Fn(self):
\tself.v = 1024
dest = 'dest.html'
x = func(a + 1)|)
s = "I forget...
## A large
## comment block"""


class PythonSourceFormatter(Formatter):
    string_style_names = STRING_STYLES

    def GetSampleText(self):
        return PythonSampleCode

    def LoadStyles(self):
        pass

    def SetStyles(self):
        for name, format, bg, ignore in PYTHON_STYLES:
            self.RegisterStyle(Style(name, format, bg))
        for name, format, bg, sc_id in SPECIAL_STYLES:
            self.RegisterStyle(Style(name, format, bg), sc_id)

    def ClassifyWord(self, cdoc, start, end, prevWord):
        word = cdoc[start : end + 1].decode("latin-1")
        attr = STYLE_IDENTIFIER
        if prevWord == "class":
            attr = STYLE_CLASS
        elif prevWord == "def":
            attr = STYLE_METHOD
        elif word[0] in string.digits:
            attr = STYLE_NUMBER
        elif iskeyword(word):
            attr = STYLE_KEYWORD
        self.ColorSeg(start, end, attr)
        return word

    def ColorizeString(self, str, styleStart):
        if styleStart is None:
            styleStart = STYLE_DEFAULT
        return self.ColorizePythonCode(str, 0, styleStart)

    def ColorizePythonCode(self, cdoc, charStart, styleStart):
        # Straight translation of C++, should do better
        lengthDoc = len(cdoc)
        if lengthDoc <= charStart:
            return
        prevWord = ""
        state = styleStart
        chPrev = chPrev2 = chPrev3 = " "
        chNext2 = chNext = cdoc[charStart : charStart + 1].decode("latin-1")
        startSeg = i = charStart
        while i < lengthDoc:
            ch = chNext
            chNext = " "
            if i + 1 < lengthDoc:
                chNext = cdoc[i + 1 : i + 2].decode("latin-1")
            chNext2 = " "
            if i + 2 < lengthDoc:
                chNext2 = cdoc[i + 2 : i + 3].decode("latin-1")
            if state == STYLE_DEFAULT:
                if ch in wordstarts:
                    self.ColorSeg(startSeg, i - 1, STYLE_DEFAULT)
                    state = STYLE_KEYWORD
                    startSeg = i
                elif ch == "#":
                    self.ColorSeg(startSeg, i - 1, STYLE_DEFAULT)
                    if chNext == "#":
                        state = STYLE_COMMENT_BLOCK
                    else:
                        state = STYLE_COMMENT
                    startSeg = i
                elif ch == '"':
                    self.ColorSeg(startSeg, i - 1, STYLE_DEFAULT)
                    startSeg = i
                    state = STYLE_COMMENT
                    if chNext == '"' and chNext2 == '"':
                        i += 2
                        state = STYLE_TQDSTRING
                        ch = " "
                        chPrev = " "
                        chNext = " "
                        if i + 1 < lengthDoc:
                            chNext = cdoc[i + 1]
                    else:
                        state = STYLE_STRING
                elif ch == "'":
                    self.ColorSeg(startSeg, i - 1, STYLE_DEFAULT)
                    startSeg = i
                    state = STYLE_COMMENT
                    if chNext == "'" and chNext2 == "'":
                        i += 2
                        state = STYLE_TQSSTRING
                        ch = " "
                        chPrev = " "
                        chNext = " "
                        if i + 1 < lengthDoc:
                            chNext = cdoc[i + 1]
                    else:
                        state = STYLE_SQSTRING
                elif ch in operators:
                    self.ColorSeg(startSeg, i - 1, STYLE_DEFAULT)
                    self.ColorSeg(i, i, STYLE_OPERATOR)
                    startSeg = i + 1
            elif state == STYLE_KEYWORD:
                if ch not in wordchars:
                    prevWord = self.ClassifyWord(cdoc, startSeg, i - 1, prevWord)
                    state = STYLE_DEFAULT
                    startSeg = i
                    if ch == "#":
                        if chNext == "#":
                            state = STYLE_COMMENT_BLOCK
                        else:
                            state = STYLE_COMMENT
                    elif ch == '"':
                        if chNext == '"' and chNext2 == '"':
                            i += 2
                            state = STYLE_TQDSTRING
                            ch = " "
                            chPrev = " "
                            chNext = " "
                            if i + 1 < lengthDoc:
                                chNext = cdoc[i + 1]
                        else:
                            state = STYLE_STRING
                    elif ch == "'":
                        if chNext == "'" and chNext2 == "'":
                            i += 2
                            state = STYLE_TQSSTRING
                            ch = " "
                            chPrev = " "
                            chNext = " "
                            if i + 1 < lengthDoc:
                                chNext = cdoc[i + 1]
                        else:
                            state = STYLE_SQSTRING
                    elif ch in operators:
                        self.ColorSeg(startSeg, i, STYLE_OPERATOR)
                        startSeg = i + 1
            elif state == STYLE_COMMENT or state == STYLE_COMMENT_BLOCK:
                if ch == "\r" or ch == "\n":
                    self.ColorSeg(startSeg, i - 1, state)
                    state = STYLE_DEFAULT
                    startSeg = i
            elif state == STYLE_STRING:
                if ch == "\\":
                    if chNext == '"' or chNext == "'" or chNext == "\\":
                        i += 1
                        ch = chNext
                        chNext = " "
                        if i + 1 < lengthDoc:
                            chNext = cdoc[i + 1]
                elif ch == '"':
                    self.ColorSeg(startSeg, i, STYLE_STRING)
                    state = STYLE_DEFAULT
                    startSeg = i + 1
            elif state == STYLE_SQSTRING:
                if ch == "\\":
                    if chNext == '"' or chNext == "'" or chNext == "\\":
                        i += 1
                        ch = chNext
                        chNext = " "
                        if i + 1 < lengthDoc:
                            chNext = cdoc[i + 1]
                elif ch == "'":
                    self.ColorSeg(startSeg, i, STYLE_SQSTRING)
                    state = STYLE_DEFAULT
                    startSeg = i + 1
            elif state == STYLE_TQSSTRING:
                if ch == "'" and chPrev == "'" and chPrev2 == "'" and chPrev3 != "\\":
                    self.ColorSeg(startSeg, i, STYLE_TQSSTRING)
                    state = STYLE_DEFAULT
                    startSeg = i + 1
            elif (
                state == STYLE_TQDSTRING
                and ch == '"'
                and chPrev == '"'
                and chPrev2 == '"'
                and chPrev3 != "\\"
            ):
                self.ColorSeg(startSeg, i, STYLE_TQDSTRING)
                state = STYLE_DEFAULT
                startSeg = i + 1
            chPrev3 = chPrev2
            chPrev2 = chPrev
            chPrev = ch
            i += 1
        if startSeg < lengthDoc:
            if state == STYLE_KEYWORD:
                self.ClassifyWord(cdoc, startSeg, lengthDoc - 1, prevWord)
            else:
                self.ColorSeg(startSeg, lengthDoc - 1, state)


# These taken from the SciTE properties file.
source_formatter_extensions = [
    (".py .pys .pyw".split(), scintillacon.SCLEX_PYTHON),
    (".html .htm .asp .shtml".split(), scintillacon.SCLEX_HTML),
    (
        "c .cc .cpp .cxx .h .hh .hpp .hxx .idl .odl .php3 .phtml .inc .js".split(),
        scintillacon.SCLEX_CPP,
    ),
    (".vbs .frm .ctl .cls".split(), scintillacon.SCLEX_VB),
    (".pl .pm .cgi .pod".split(), scintillacon.SCLEX_PERL),
    (".sql .spec .body .sps .spb .sf .sp".split(), scintillacon.SCLEX_SQL),
    (".tex .sty".split(), scintillacon.SCLEX_LATEX),
    (".xml .xul".split(), scintillacon.SCLEX_XML),
    (".err".split(), scintillacon.SCLEX_ERRORLIST),
    (".mak".split(), scintillacon.SCLEX_MAKEFILE),
    (".bat .cmd".split(), scintillacon.SCLEX_BATCH),
]


class BuiltinSourceFormatter(FormatterBase):
    # A class that represents a formatter built-in to Scintilla
    def __init__(self, scintilla, ext):
        self.ext = ext
        FormatterBase.__init__(self, scintilla)

    def Colorize(self, start=0, end=-1):
        self.scintilla.SendScintilla(scintillacon.SCI_COLOURISE, start, end)

    def RegisterStyle(self, style, stylenum=None):
        assert style.stylenum is None, "Style has already been registered"
        if stylenum is None:
            stylenum = self.nextstylenum
            self.nextstylenum += 1
        assert self.styles.get(stylenum) is None, "We are reusing a style number!"
        style.stylenum = stylenum
        self.styles[style.name] = style
        self.styles_by_id[stylenum] = style

    def HookFormatter(self, parent=None):
        sc = self.scintilla
        for exts, formatter in source_formatter_extensions:
            if self.ext in exts:
                formatter_use = formatter
                break
        else:
            formatter_use = scintillacon.SCLEX_PYTHON
        sc.SendScintilla(scintillacon.SCI_SETLEXER, formatter_use)
        keywords = " ".join(kwlist)
        sc.SCISetKeywords(keywords)


class BuiltinPythonSourceFormatter(BuiltinSourceFormatter):
    sci_lexer_name = scintillacon.SCLEX_PYTHON
    string_style_names = STRING_STYLES

    def __init__(self, sc, ext=".py"):
        BuiltinSourceFormatter.__init__(self, sc, ext)

    def SetStyles(self):
        for name, format, bg, sc_id in PYTHON_STYLES:
            self.RegisterStyle(Style(name, format, bg), sc_id)
        for name, format, bg, sc_id in SPECIAL_STYLES:
            self.RegisterStyle(Style(name, format, bg), sc_id)

    def GetSampleText(self):
        return PythonSampleCode

# === NexusCore/openenv\Lib\site-packages\matplotlib\colorizer.py ===
"""
The Colorizer class which handles the data to color pipeline via a
normalization and a colormap.

.. admonition:: Provisional status of colorizer

    The ``colorizer`` module and classes in this file are considered
    provisional and may change at any time without a deprecation period.

.. seealso::

  :doc:`/gallery/color/colormap_reference` for a list of builtin colormaps.

  :ref:`colormap-manipulation` for examples of how to make colormaps.

  :ref:`colormaps` for an in-depth discussion of choosing colormaps.

  :ref:`colormapnorms` for more details about data normalization.

"""

import functools

import numpy as np
from numpy import ma

from matplotlib import _api, colors, cbook, scale, artist
import matplotlib as mpl

mpl._docstring.interpd.register(
    colorizer_doc="""\
colorizer : `~matplotlib.colorizer.Colorizer` or None, default: None
    The Colorizer object used to map color to data. If None, a Colorizer
    object is created from a *norm* and *cmap*.""",
    )


class Colorizer:
    """
    Data to color pipeline.

    This pipeline is accessible via `.Colorizer.to_rgba` and executed via
    the `.Colorizer.norm` and `.Colorizer.cmap` attributes.

    Parameters
    ----------
    cmap: colorbar.Colorbar or str or None, default: None
        The colormap used to color data.

    norm: colors.Normalize or str or None, default: None
        The normalization used to normalize the data
    """
    def __init__(self, cmap=None, norm=None):

        self._cmap = None
        self._set_cmap(cmap)

        self._id_norm = None
        self._norm = None
        self.norm = norm

        self.callbacks = cbook.CallbackRegistry(signals=["changed"])
        self.colorbar = None

    def _scale_norm(self, norm, vmin, vmax, A):
        """
        Helper for initial scaling.

        Used by public functions that create a ScalarMappable and support
        parameters *vmin*, *vmax* and *norm*. This makes sure that a *norm*
        will take precedence over *vmin*, *vmax*.

        Note that this method does not set the norm.
        """
        if vmin is not None or vmax is not None:
            self.set_clim(vmin, vmax)
            if isinstance(norm, colors.Normalize):
                raise ValueError(
                    "Passing a Normalize instance simultaneously with "
                    "vmin/vmax is not supported.  Please pass vmin/vmax "
                    "directly to the norm when creating it.")

        # always resolve the autoscaling so we have concrete limits
        # rather than deferring to draw time.
        self.autoscale_None(A)

    @property
    def norm(self):
        return self._norm

    @norm.setter
    def norm(self, norm):
        _api.check_isinstance((colors.Normalize, str, None), norm=norm)
        if norm is None:
            norm = colors.Normalize()
        elif isinstance(norm, str):
            try:
                scale_cls = scale._scale_mapping[norm]
            except KeyError:
                raise ValueError(
                    "Invalid norm str name; the following values are "
                    f"supported: {', '.join(scale._scale_mapping)}"
                ) from None
            norm = _auto_norm_from_scale(scale_cls)()

        if norm is self.norm:
            # We aren't updating anything
            return

        in_init = self.norm is None
        # Remove the current callback and connect to the new one
        if not in_init:
            self.norm.callbacks.disconnect(self._id_norm)
        self._norm = norm
        self._id_norm = self.norm.callbacks.connect('changed',
                                                    self.changed)
        if not in_init:
            self.changed()

    def to_rgba(self, x, alpha=None, bytes=False, norm=True):
        """
        Return a normalized RGBA array corresponding to *x*.

        In the normal case, *x* is a 1D or 2D sequence of scalars, and
        the corresponding `~numpy.ndarray` of RGBA values will be returned,
        based on the norm and colormap set for this Colorizer.

        There is one special case, for handling images that are already
        RGB or RGBA, such as might have been read from an image file.
        If *x* is an `~numpy.ndarray` with 3 dimensions,
        and the last dimension is either 3 or 4, then it will be
        treated as an RGB or RGBA array, and no mapping will be done.
        The array can be `~numpy.uint8`, or it can be floats with
        values in the 0-1 range; otherwise a ValueError will be raised.
        Any NaNs or masked elements will be set to 0 alpha.
        If the last dimension is 3, the *alpha* kwarg (defaulting to 1)
        will be used to fill in the transparency.  If the last dimension
        is 4, the *alpha* kwarg is ignored; it does not
        replace the preexisting alpha.  A ValueError will be raised
        if the third dimension is other than 3 or 4.

        In either case, if *bytes* is *False* (default), the RGBA
        array will be floats in the 0-1 range; if it is *True*,
        the returned RGBA array will be `~numpy.uint8` in the 0 to 255 range.

        If norm is False, no normalization of the input data is
        performed, and it is assumed to be in the range (0-1).

        """
        # First check for special case, image input:
        if isinstance(x, np.ndarray) and x.ndim == 3:
            return self._pass_image_data(x, alpha, bytes, norm)

        # Otherwise run norm -> colormap pipeline
        x = ma.asarray(x)
        if norm:
            x = self.norm(x)
        rgba = self.cmap(x, alpha=alpha, bytes=bytes)
        return rgba

    @staticmethod
    def _pass_image_data(x, alpha=None, bytes=False, norm=True):
        """
        Helper function to pass ndarray of shape (...,3) or (..., 4)
        through `to_rgba()`, see `to_rgba()` for docstring.
        """
        if x.shape[2] == 3:
            if alpha is None:
                alpha = 1
            if x.dtype == np.uint8:
                alpha = np.uint8(alpha * 255)
            m, n = x.shape[:2]
            xx = np.empty(shape=(m, n, 4), dtype=x.dtype)
            xx[:, :, :3] = x
            xx[:, :, 3] = alpha
        elif x.shape[2] == 4:
            xx = x
        else:
            raise ValueError("Third dimension must be 3 or 4")
        if xx.dtype.kind == 'f':
            # If any of R, G, B, or A is nan, set to 0
            if np.any(nans := np.isnan(x)):
                if x.shape[2] == 4:
                    xx = xx.copy()
                xx[np.any(nans, axis=2), :] = 0

            if norm and (xx.max() > 1 or xx.min() < 0):
                raise ValueError("Floating point image RGB values "
                                 "must be in the 0..1 range.")
            if bytes:
                xx = (xx * 255).astype(np.uint8)
        elif xx.dtype == np.uint8:
            if not bytes:
                xx = xx.astype(np.float32) / 255
        else:
            raise ValueError("Image RGB array must be uint8 or "
                             "floating point; found %s" % xx.dtype)
        # Account for any masked entries in the original array
        # If any of R, G, B, or A are masked for an entry, we set alpha to 0
        if np.ma.is_masked(x):
            xx[np.any(np.ma.getmaskarray(x), axis=2), 3] = 0
        return xx

    def autoscale(self, A):
        """
        Autoscale the scalar limits on the norm instance using the
        current array
        """
        if A is None:
            raise TypeError('You must first set_array for mappable')
        # If the norm's limits are updated self.changed() will be called
        # through the callbacks attached to the norm
        self.norm.autoscale(A)

    def autoscale_None(self, A):
        """
        Autoscale the scalar limits on the norm instance using the
        current array, changing only limits that are None
        """
        if A is None:
            raise TypeError('You must first set_array for mappable')
        # If the norm's limits are updated self.changed() will be called
        # through the callbacks attached to the norm
        self.norm.autoscale_None(A)

    def _set_cmap(self, cmap):
        """
        Set the colormap for luminance data.

        Parameters
        ----------
        cmap : `.Colormap` or str or None
        """
        # bury import to avoid circular imports
        from matplotlib import cm
        in_init = self._cmap is None
        self._cmap = cm._ensure_cmap(cmap)
        if not in_init:
            self.changed()  # Things are not set up properly yet.

    @property
    def cmap(self):
        return self._cmap

    @cmap.setter
    def cmap(self, cmap):
        self._set_cmap(cmap)

    def set_clim(self, vmin=None, vmax=None):
        """
        Set the norm limits for image scaling.

        Parameters
        ----------
        vmin, vmax : float
             The limits.

             The limits may also be passed as a tuple (*vmin*, *vmax*) as a
             single positional argument.

             .. ACCEPTS: (vmin: float, vmax: float)
        """
        # If the norm's limits are updated self.changed() will be called
        # through the callbacks attached to the norm, this causes an inconsistent
        # state, to prevent this blocked context manager is used
        if vmax is None:
            try:
                vmin, vmax = vmin
            except (TypeError, ValueError):
                pass

        orig_vmin_vmax = self.norm.vmin, self.norm.vmax

        # Blocked context manager prevents callbacks from being triggered
        # until both vmin and vmax are updated
        with self.norm.callbacks.blocked(signal='changed'):
            if vmin is not None:
                self.norm.vmin = colors._sanitize_extrema(vmin)
            if vmax is not None:
                self.norm.vmax = colors._sanitize_extrema(vmax)

        # emit a update signal if the limits are changed
        if orig_vmin_vmax != (self.norm.vmin, self.norm.vmax):
            self.norm.callbacks.process('changed')

    def get_clim(self):
        """
        Return the values (min, max) that are mapped to the colormap limits.
        """
        return self.norm.vmin, self.norm.vmax

    def changed(self):
        """
        Call this whenever the mappable is changed to notify all the
        callbackSM listeners to the 'changed' signal.
        """
        self.callbacks.process('changed')
        self.stale = True

    @property
    def vmin(self):
        return self.get_clim()[0]

    @vmin.setter
    def vmin(self, vmin):
        self.set_clim(vmin=vmin)

    @property
    def vmax(self):
        return self.get_clim()[1]

    @vmax.setter
    def vmax(self, vmax):
        self.set_clim(vmax=vmax)

    @property
    def clip(self):
        return self.norm.clip

    @clip.setter
    def clip(self, clip):
        self.norm.clip = clip


class _ColorizerInterface:
    """
    Base class that contains the interface to `Colorizer` objects from
    a `ColorizingArtist` or `.cm.ScalarMappable`.

    Note: This class only contain functions that interface the .colorizer
    attribute. Other functions that as shared between `.ColorizingArtist`
    and `.cm.ScalarMappable` are not included.
    """
    def _scale_norm(self, norm, vmin, vmax):
        self._colorizer._scale_norm(norm, vmin, vmax, self._A)

    def to_rgba(self, x, alpha=None, bytes=False, norm=True):
        """
        Return a normalized RGBA array corresponding to *x*.

        In the normal case, *x* is a 1D or 2D sequence of scalars, and
        the corresponding `~numpy.ndarray` of RGBA values will be returned,
        based on the norm and colormap set for this Colorizer.

        There is one special case, for handling images that are already
        RGB or RGBA, such as might have been read from an image file.
        If *x* is an `~numpy.ndarray` with 3 dimensions,
        and the last dimension is either 3 or 4, then it will be
        treated as an RGB or RGBA array, and no mapping will be done.
        The array can be `~numpy.uint8`, or it can be floats with
        values in the 0-1 range; otherwise a ValueError will be raised.
        Any NaNs or masked elements will be set to 0 alpha.
        If the last dimension is 3, the *alpha* kwarg (defaulting to 1)
        will be used to fill in the transparency.  If the last dimension
        is 4, the *alpha* kwarg is ignored; it does not
        replace the preexisting alpha.  A ValueError will be raised
        if the third dimension is other than 3 or 4.

        In either case, if *bytes* is *False* (default), the RGBA
        array will be floats in the 0-1 range; if it is *True*,
        the returned RGBA array will be `~numpy.uint8` in the 0 to 255 range.

        If norm is False, no normalization of the input data is
        performed, and it is assumed to be in the range (0-1).

        """
        return self._colorizer.to_rgba(x, alpha=alpha, bytes=bytes, norm=norm)

    def get_clim(self):
        """
        Return the values (min, max) that are mapped to the colormap limits.
        """
        return self._colorizer.get_clim()

    def set_clim(self, vmin=None, vmax=None):
        """
        Set the norm limits for image scaling.

        Parameters
        ----------
        vmin, vmax : float
             The limits.

             For scalar data, the limits may also be passed as a
             tuple (*vmin*, *vmax*) as a single positional argument.

             .. ACCEPTS: (vmin: float, vmax: float)
        """
        # If the norm's limits are updated self.changed() will be called
        # through the callbacks attached to the norm
        self._colorizer.set_clim(vmin, vmax)

    def get_alpha(self):
        try:
            return super().get_alpha()
        except AttributeError:
            return 1

    @property
    def cmap(self):
        return self._colorizer.cmap

    @cmap.setter
    def cmap(self, cmap):
        self._colorizer.cmap = cmap

    def get_cmap(self):
        """Return the `.Colormap` instance."""
        return self._colorizer.cmap

    def set_cmap(self, cmap):
        """
        Set the colormap for luminance data.

        Parameters
        ----------
        cmap : `.Colormap` or str or None
        """
        self.cmap = cmap

    @property
    def norm(self):
        return self._colorizer.norm

    @norm.setter
    def norm(self, norm):
        self._colorizer.norm = norm

    def set_norm(self, norm):
        """
        Set the normalization instance.

        Parameters
        ----------
        norm : `.Normalize` or str or None

        Notes
        -----
        If there are any colorbars using the mappable for this norm, setting
        the norm of the mappable will reset the norm, locator, and formatters
        on the colorbar to default.
        """
        self.norm = norm

    def autoscale(self):
        """
        Autoscale the scalar limits on the norm instance using the
        current array
        """
        self._colorizer.autoscale(self._A)

    def autoscale_None(self):
        """
        Autoscale the scalar limits on the norm instance using the
        current array, changing only limits that are None
        """
        self._colorizer.autoscale_None(self._A)

    @property
    def colorbar(self):
        """
        The last colorbar associated with this object. May be None
        """
        return self._colorizer.colorbar

    @colorbar.setter
    def colorbar(self, colorbar):
        self._colorizer.colorbar = colorbar

    def _format_cursor_data_override(self, data):
        # This function overwrites Artist.format_cursor_data(). We cannot
        # implement cm.ScalarMappable.format_cursor_data() directly, because
        # most cm.ScalarMappable subclasses inherit from Artist first and from
        # cm.ScalarMappable second, so Artist.format_cursor_data would always
        # have precedence over cm.ScalarMappable.format_cursor_data.

        # Note if cm.ScalarMappable is depreciated, this functionality should be
        # implemented as format_cursor_data() on ColorizingArtist.
        n = self.cmap.N
        if np.ma.getmask(data):
            return "[]"
        normed = self.norm(data)
        if np.isfinite(normed):
            if isinstance(self.norm, colors.BoundaryNorm):
                # not an invertible normalization mapping
                cur_idx = np.argmin(np.abs(self.norm.boundaries - data))
                neigh_idx = max(0, cur_idx - 1)
                # use max diff to prevent delta == 0
                delta = np.diff(
                    self.norm.boundaries[neigh_idx:cur_idx + 2]
                ).max()
            elif self.norm.vmin == self.norm.vmax:
                # singular norms, use delta of 10% of only value
                delta = np.abs(self.norm.vmin * .1)
            else:
                # Midpoints of neighboring color intervals.
                neighbors = self.norm.inverse(
                    (int(normed * n) + np.array([0, 1])) / n)
                delta = abs(neighbors - data).max()
            g_sig_digits = cbook._g_sig_digits(data, delta)
        else:
            g_sig_digits = 3  # Consistent with default below.
        return f"[{data:-#.{g_sig_digits}g}]"


class _ScalarMappable(_ColorizerInterface):
    """
    A mixin class to map one or multiple sets of scalar data to RGBA.

    The ScalarMappable applies data normalization before returning RGBA colors from
    the given `~matplotlib.colors.Colormap`.
    """

    # _ScalarMappable exists for compatibility with
    # code written before the introduction of the Colorizer
    # and ColorizingArtist classes.

    # _ScalarMappable can be depreciated so that ColorizingArtist
    # inherits directly from _ColorizerInterface.
    # in this case, the following changes should occur:
    # __init__() has its functionality moved to ColorizingArtist.
    # set_array(), get_array(), _get_colorizer() and
    # _check_exclusionary_keywords() are moved to ColorizingArtist.
    # changed() can be removed so long as colorbar.Colorbar
    # is changed to connect to the colorizer instead of the
    # ScalarMappable/ColorizingArtist,
    # otherwise changed() can be moved to ColorizingArtist.
    def __init__(self, norm=None, cmap=None, *, colorizer=None, **kwargs):
        """
        Parameters
        ----------
        norm : `.Normalize` (or subclass thereof) or str or None
            The normalizing object which scales data, typically into the
            interval ``[0, 1]``.
            If a `str`, a `.Normalize` subclass is dynamically generated based
            on the scale with the corresponding name.
            If *None*, *norm* defaults to a *colors.Normalize* object which
            initializes its scaling based on the first data processed.
        cmap : str or `~matplotlib.colors.Colormap`
            The colormap used to map normalized data values to RGBA colors.
        """
        super().__init__(**kwargs)
        self._A = None
        self._colorizer = self._get_colorizer(colorizer=colorizer, norm=norm, cmap=cmap)

        self.colorbar = None
        self._id_colorizer = self._colorizer.callbacks.connect('changed', self.changed)
        self.callbacks = cbook.CallbackRegistry(signals=["changed"])

    def set_array(self, A):
        """
        Set the value array from array-like *A*.

        Parameters
        ----------
        A : array-like or None
            The values that are mapped to colors.

            The base class `.ScalarMappable` does not make any assumptions on
            the dimensionality and shape of the value array *A*.
        """
        if A is None:
            self._A = None
            return

        A = cbook.safe_masked_invalid(A, copy=True)
        if not np.can_cast(A.dtype, float, "same_kind"):
            raise TypeError(f"Image data of dtype {A.dtype} cannot be "
                            "converted to float")

        self._A = A
        if not self.norm.scaled():
            self._colorizer.autoscale_None(A)

    def get_array(self):
        """
        Return the array of values, that are mapped to colors.

        The base class `.ScalarMappable` does not make any assumptions on
        the dimensionality and shape of the array.
        """
        return self._A

    def changed(self):
        """
        Call this whenever the mappable is changed to notify all the
        callbackSM listeners to the 'changed' signal.
        """
        self.callbacks.process('changed', self)
        self.stale = True

    @staticmethod
    def _check_exclusionary_keywords(colorizer, **kwargs):
        """
        Raises a ValueError if any kwarg is not None while colorizer is not None
        """
        if colorizer is not None:
            if any([val is not None for val in kwargs.values()]):
                raise ValueError("The `colorizer` keyword cannot be used simultaneously"
                                 " with any of the following keywords: "
                                 + ", ".join(f'`{key}`' for key in kwargs.keys()))

    @staticmethod
    def _get_colorizer(cmap, norm, colorizer):
        if isinstance(colorizer, Colorizer):
            _ScalarMappable._check_exclusionary_keywords(
                Colorizer, cmap=cmap, norm=norm
            )
            return colorizer
        return Colorizer(cmap, norm)

# The docstrings here must be generic enough to apply to all relevant methods.
mpl._docstring.interpd.register(
    cmap_doc="""\
cmap : str or `~matplotlib.colors.Colormap`, default: :rc:`image.cmap`
    The Colormap instance or registered colormap name used to map scalar data
    to colors.""",
    norm_doc="""\
norm : str or `~matplotlib.colors.Normalize`, optional
    The normalization method used to scale scalar data to the [0, 1] range
    before mapping to colors using *cmap*. By default, a linear scaling is
    used, mapping the lowest value to 0 and the highest to 1.

    If given, this can be one of the following:

    - An instance of `.Normalize` or one of its subclasses
      (see :ref:`colormapnorms`).
    - A scale name, i.e. one of "linear", "log", "symlog", "logit", etc.  For a
      list of available scales, call `matplotlib.scale.get_scale_names()`.
      In that case, a suitable `.Normalize` subclass is dynamically generated
      and instantiated.""",
    vmin_vmax_doc="""\
vmin, vmax : float, optional
    When using scalar data and no explicit *norm*, *vmin* and *vmax* define
    the data range that the colormap covers. By default, the colormap covers
    the complete value range of the supplied data. It is an error to use
    *vmin*/*vmax* when a *norm* instance is given (but using a `str` *norm*
    name together with *vmin*/*vmax* is acceptable).""",
)


class ColorizingArtist(_ScalarMappable, artist.Artist):
    """
    Base class for artists that make map data to color using a `.colorizer.Colorizer`.

    The `.colorizer.Colorizer` applies data normalization before
    returning RGBA colors from a `~matplotlib.colors.Colormap`.

    """
    def __init__(self, colorizer, **kwargs):
        """
        Parameters
        ----------
        colorizer : `.colorizer.Colorizer`
        """
        _api.check_isinstance(Colorizer, colorizer=colorizer)
        super().__init__(colorizer=colorizer, **kwargs)

    @property
    def colorizer(self):
        return self._colorizer

    @colorizer.setter
    def colorizer(self, cl):
        _api.check_isinstance(Colorizer, colorizer=cl)
        self._colorizer.callbacks.disconnect(self._id_colorizer)
        self._colorizer = cl
        self._id_colorizer = cl.callbacks.connect('changed', self.changed)

    def _set_colorizer_check_keywords(self, colorizer, **kwargs):
        """
        Raises a ValueError if any kwarg is not None while colorizer is not None.
        """
        self._check_exclusionary_keywords(colorizer, **kwargs)
        self.colorizer = colorizer


def _auto_norm_from_scale(scale_cls):
    """
    Automatically generate a norm class from *scale_cls*.

    This differs from `.colors.make_norm_from_scale` in the following points:

    - This function is not a class decorator, but directly returns a norm class
      (as if decorating `.Normalize`).
    - The scale is automatically constructed with ``nonpositive="mask"``, if it
      supports such a parameter, to work around the difference in defaults
      between standard scales (which use "clip") and norms (which use "mask").

    Note that ``make_norm_from_scale`` caches the generated norm classes
    (not the instances) and reuses them for later calls.  For example,
    ``type(_auto_norm_from_scale("log")) == LogNorm``.
    """
    # Actually try to construct an instance, to verify whether
    # ``nonpositive="mask"`` is supported.
    try:
        norm = colors.make_norm_from_scale(
            functools.partial(scale_cls, nonpositive="mask"))(
            colors.Normalize)()
    except TypeError:
        norm = colors.make_norm_from_scale(scale_cls)(
            colors.Normalize)()
    return type(norm)

# === NexusCore/openenv\Lib\site-packages\win32\lib\pywin32_bootstrap.py ===
# Imported by pywin32.pth to bootstrap the pywin32 environment in "portable"
# environments or any other case where the post-install script isn't run.
#
# In short, there's a directory installed by pywin32 named 'pywin32_system32'
# with some important DLLs which need to be found by Python when some pywin32
# modules are imported.


try:
    import pywin32_system32
except ImportError:  # Python ≥3.6: replace ImportError with ModuleNotFoundError
    pass
else:
    import os

    # We're guaranteed only that __path__: Iterable[str]
    # https://docs.python.org/3/reference/import.html#path-attributes-on-modules
    for path in pywin32_system32.__path__:
        if os.path.isdir(path):
            os.add_dll_directory(path)
            break

# === NexusCore/openenv\Lib\site-packages\tornado\simple_httpclient.py ===
from tornado.escape import _unicode
from tornado import gen, version
from tornado.httpclient import (
    HTTPResponse,
    HTTPError,
    AsyncHTTPClient,
    main,
    _RequestProxy,
    HTTPRequest,
)
from tornado import httputil
from tornado.http1connection import HTTP1Connection, HTTP1ConnectionParameters
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError, IOStream
from tornado.netutil import (
    Resolver,
    OverrideResolver,
    _client_ssl_defaults,
    is_valid_ip,
)
from tornado.log import gen_log
from tornado.tcpclient import TCPClient

import base64
import collections
import copy
import functools
import re
import socket
import ssl
import sys
import time
from io import BytesIO
import urllib.parse

from typing import Dict, Any, Callable, Optional, Type, Union
from types import TracebackType
import typing

if typing.TYPE_CHECKING:
    from typing import Deque, Tuple, List  # noqa: F401


class HTTPTimeoutError(HTTPError):
    """Error raised by SimpleAsyncHTTPClient on timeout.

    For historical reasons, this is a subclass of `.HTTPClientError`
    which simulates a response code of 599.

    .. versionadded:: 5.1
    """

    def __init__(self, message: str) -> None:
        super().__init__(599, message=message)

    def __str__(self) -> str:
        return self.message or "Timeout"


class HTTPStreamClosedError(HTTPError):
    """Error raised by SimpleAsyncHTTPClient when the underlying stream is closed.

    When a more specific exception is available (such as `ConnectionResetError`),
    it may be raised instead of this one.

    For historical reasons, this is a subclass of `.HTTPClientError`
    which simulates a response code of 599.

    .. versionadded:: 5.1
    """

    def __init__(self, message: str) -> None:
        super().__init__(599, message=message)

    def __str__(self) -> str:
        return self.message or "Stream closed"


class SimpleAsyncHTTPClient(AsyncHTTPClient):
    """Non-blocking HTTP client with no external dependencies.

    This class implements an HTTP 1.1 client on top of Tornado's IOStreams.
    Some features found in the curl-based AsyncHTTPClient are not yet
    supported.  In particular, proxies are not supported, connections
    are not reused, and callers cannot select the network interface to be
    used.

    This implementation supports the following arguments, which can be passed
    to ``configure()`` to control the global singleton, or to the constructor
    when ``force_instance=True``.

    ``max_clients`` is the number of concurrent requests that can be
    in progress; when this limit is reached additional requests will be
    queued. Note that time spent waiting in this queue still counts
    against the ``request_timeout``.

    ``defaults`` is a dict of parameters that will be used as defaults on all
    `.HTTPRequest` objects submitted to this client.

    ``hostname_mapping`` is a dictionary mapping hostnames to IP addresses.
    It can be used to make local DNS changes when modifying system-wide
    settings like ``/etc/hosts`` is not possible or desirable (e.g. in
    unittests). ``resolver`` is similar, but using the `.Resolver` interface
    instead of a simple mapping.

    ``max_buffer_size`` (default 100MB) is the number of bytes
    that can be read into memory at once. ``max_body_size``
    (defaults to ``max_buffer_size``) is the largest response body
    that the client will accept.  Without a
    ``streaming_callback``, the smaller of these two limits
    applies; with a ``streaming_callback`` only ``max_body_size``
    does.

    .. versionchanged:: 4.2
        Added the ``max_body_size`` argument.
    """

    def initialize(  # type: ignore
        self,
        max_clients: int = 10,
        hostname_mapping: Optional[Dict[str, str]] = None,
        max_buffer_size: int = 104857600,
        resolver: Optional[Resolver] = None,
        defaults: Optional[Dict[str, Any]] = None,
        max_header_size: Optional[int] = None,
        max_body_size: Optional[int] = None,
    ) -> None:
        super().initialize(defaults=defaults)
        self.max_clients = max_clients
        self.queue = (
            collections.deque()
        )  # type: Deque[Tuple[object, HTTPRequest, Callable[[HTTPResponse], None]]]
        self.active = (
            {}
        )  # type: Dict[object, Tuple[HTTPRequest, Callable[[HTTPResponse], None]]]
        self.waiting = (
            {}
        )  # type: Dict[object, Tuple[HTTPRequest, Callable[[HTTPResponse], None], object]]
        self.max_buffer_size = max_buffer_size
        self.max_header_size = max_header_size
        self.max_body_size = max_body_size
        # TCPClient could create a Resolver for us, but we have to do it
        # ourselves to support hostname_mapping.
        if resolver:
            self.resolver = resolver
            self.own_resolver = False
        else:
            self.resolver = Resolver()
            self.own_resolver = True
        if hostname_mapping is not None:
            self.resolver = OverrideResolver(
                resolver=self.resolver, mapping=hostname_mapping
            )
        self.tcp_client = TCPClient(resolver=self.resolver)

    def close(self) -> None:
        super().close()
        if self.own_resolver:
            self.resolver.close()
        self.tcp_client.close()

    def fetch_impl(
        self, request: HTTPRequest, callback: Callable[[HTTPResponse], None]
    ) -> None:
        key = object()
        self.queue.append((key, request, callback))
        assert request.connect_timeout is not None
        assert request.request_timeout is not None
        timeout_handle = None
        if len(self.active) >= self.max_clients:
            timeout = (
                min(request.connect_timeout, request.request_timeout)
                or request.connect_timeout
                or request.request_timeout
            )  # min but skip zero
            if timeout:
                timeout_handle = self.io_loop.add_timeout(
                    self.io_loop.time() + timeout,
                    functools.partial(self._on_timeout, key, "in request queue"),
                )
        self.waiting[key] = (request, callback, timeout_handle)
        self._process_queue()
        if self.queue:
            gen_log.debug(
                "max_clients limit reached, request queued. "
                "%d active, %d queued requests." % (len(self.active), len(self.queue))
            )

    def _process_queue(self) -> None:
        while self.queue and len(self.active) < self.max_clients:
            key, request, callback = self.queue.popleft()
            if key not in self.waiting:
                continue
            self._remove_timeout(key)
            self.active[key] = (request, callback)
            release_callback = functools.partial(self._release_fetch, key)
            self._handle_request(request, release_callback, callback)

    def _connection_class(self) -> type:
        return _HTTPConnection

    def _handle_request(
        self,
        request: HTTPRequest,
        release_callback: Callable[[], None],
        final_callback: Callable[[HTTPResponse], None],
    ) -> None:
        self._connection_class()(
            self,
            request,
            release_callback,
            final_callback,
            self.max_buffer_size,
            self.tcp_client,
            self.max_header_size,
            self.max_body_size,
        )

    def _release_fetch(self, key: object) -> None:
        del self.active[key]
        self._process_queue()

    def _remove_timeout(self, key: object) -> None:
        if key in self.waiting:
            request, callback, timeout_handle = self.waiting[key]
            if timeout_handle is not None:
                self.io_loop.remove_timeout(timeout_handle)
            del self.waiting[key]

    def _on_timeout(self, key: object, info: Optional[str] = None) -> None:
        """Timeout callback of request.

        Construct a timeout HTTPResponse when a timeout occurs.

        :arg object key: A simple object to mark the request.
        :info string key: More detailed timeout information.
        """
        request, callback, timeout_handle = self.waiting[key]
        self.queue.remove((key, request, callback))

        error_message = f"Timeout {info}" if info else "Timeout"
        timeout_response = HTTPResponse(
            request,
            599,
            error=HTTPTimeoutError(error_message),
            request_time=self.io_loop.time() - request.start_time,
        )
        self.io_loop.add_callback(callback, timeout_response)
        del self.waiting[key]


class _HTTPConnection(httputil.HTTPMessageDelegate):
    _SUPPORTED_METHODS = {"GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"}

    def __init__(
        self,
        client: Optional[SimpleAsyncHTTPClient],
        request: HTTPRequest,
        release_callback: Callable[[], None],
        final_callback: Callable[[HTTPResponse], None],
        max_buffer_size: int,
        tcp_client: TCPClient,
        max_header_size: int,
        max_body_size: int,
    ) -> None:
        self.io_loop = IOLoop.current()
        self.start_time = self.io_loop.time()
        self.start_wall_time = time.time()
        self.client = client
        self.request = request
        self.release_callback = release_callback
        self.final_callback = final_callback
        self.max_buffer_size = max_buffer_size
        self.tcp_client = tcp_client
        self.max_header_size = max_header_size
        self.max_body_size = max_body_size
        self.code = None  # type: Optional[int]
        self.headers = None  # type: Optional[httputil.HTTPHeaders]
        self.chunks = []  # type: List[bytes]
        self._decompressor = None
        # Timeout handle returned by IOLoop.add_timeout
        self._timeout = None  # type: object
        self._sockaddr = None
        IOLoop.current().add_future(
            gen.convert_yielded(self.run()), lambda f: f.result()
        )

    async def run(self) -> None:
        try:
            self.parsed = urllib.parse.urlsplit(_unicode(self.request.url))
            if self.parsed.scheme not in ("http", "https"):
                raise ValueError("Unsupported url scheme: %s" % self.request.url)
            # urlsplit results have hostname and port results, but they
            # didn't support ipv6 literals until python 2.7.
            netloc = self.parsed.netloc
            if "@" in netloc:
                userpass, _, netloc = netloc.rpartition("@")
            host, port = httputil.split_host_and_port(netloc)
            if port is None:
                port = 443 if self.parsed.scheme == "https" else 80
            if re.match(r"^\[.*\]$", host):
                # raw ipv6 addresses in urls are enclosed in brackets
                host = host[1:-1]
            self.parsed_hostname = host  # save final host for _on_connect

            if self.request.allow_ipv6 is False:
                af = socket.AF_INET
            else:
                af = socket.AF_UNSPEC

            ssl_options = self._get_ssl_options(self.parsed.scheme)

            source_ip = None
            if self.request.network_interface:
                if is_valid_ip(self.request.network_interface):
                    source_ip = self.request.network_interface
                else:
                    raise ValueError(
                        "Unrecognized IPv4 or IPv6 address for network_interface, got %r"
                        % (self.request.network_interface,)
                    )

            if self.request.connect_timeout and self.request.request_timeout:
                timeout = min(
                    self.request.connect_timeout, self.request.request_timeout
                )
            elif self.request.connect_timeout:
                timeout = self.request.connect_timeout
            elif self.request.request_timeout:
                timeout = self.request.request_timeout
            else:
                timeout = 0
            if timeout:
                self._timeout = self.io_loop.add_timeout(
                    self.start_time + timeout,
                    functools.partial(self._on_timeout, "while connecting"),
                )
            stream = await self.tcp_client.connect(
                host,
                port,
                af=af,
                ssl_options=ssl_options,
                max_buffer_size=self.max_buffer_size,
                source_ip=source_ip,
            )

            if self.final_callback is None:
                # final_callback is cleared if we've hit our timeout.
                stream.close()
                return
            self.stream = stream
            self.stream.set_close_callback(self.on_connection_close)
            self._remove_timeout()
            if self.final_callback is None:
                return
            if self.request.request_timeout:
                self._timeout = self.io_loop.add_timeout(
                    self.start_time + self.request.request_timeout,
                    functools.partial(self._on_timeout, "during request"),
                )
            if (
                self.request.method not in self._SUPPORTED_METHODS
                and not self.request.allow_nonstandard_methods
            ):
                raise KeyError("unknown method %s" % self.request.method)
            for key in (
                "proxy_host",
                "proxy_port",
                "proxy_username",
                "proxy_password",
                "proxy_auth_mode",
            ):
                if getattr(self.request, key, None):
                    raise NotImplementedError("%s not supported" % key)
            if "Connection" not in self.request.headers:
                self.request.headers["Connection"] = "close"
            if "Host" not in self.request.headers:
                if "@" in self.parsed.netloc:
                    self.request.headers["Host"] = self.parsed.netloc.rpartition("@")[
                        -1
                    ]
                else:
                    self.request.headers["Host"] = self.parsed.netloc
            username, password = None, None
            if self.parsed.username is not None:
                username, password = self.parsed.username, self.parsed.password
            elif self.request.auth_username is not None:
                username = self.request.auth_username
                password = self.request.auth_password or ""
            if username is not None:
                assert password is not None
                if self.request.auth_mode not in (None, "basic"):
                    raise ValueError("unsupported auth_mode %s", self.request.auth_mode)
                self.request.headers["Authorization"] = "Basic " + _unicode(
                    base64.b64encode(
                        httputil.encode_username_password(username, password)
                    )
                )
            if self.request.user_agent:
                self.request.headers["User-Agent"] = self.request.user_agent
            elif self.request.headers.get("User-Agent") is None:
                self.request.headers["User-Agent"] = f"Tornado/{version}"
            if not self.request.allow_nonstandard_methods:
                # Some HTTP methods nearly always have bodies while others
                # almost never do. Fail in this case unless the user has
                # opted out of sanity checks with allow_nonstandard_methods.
                body_expected = self.request.method in ("POST", "PATCH", "PUT")
                body_present = (
                    self.request.body is not None
                    or self.request.body_producer is not None
                )
                if (body_expected and not body_present) or (
                    body_present and not body_expected
                ):
                    raise ValueError(
                        "Body must %sbe None for method %s (unless "
                        "allow_nonstandard_methods is true)"
                        % ("not " if body_expected else "", self.request.method)
                    )
            if self.request.expect_100_continue:
                self.request.headers["Expect"] = "100-continue"
            if self.request.body is not None:
                # When body_producer is used the caller is responsible for
                # setting Content-Length (or else chunked encoding will be used).
                self.request.headers["Content-Length"] = str(len(self.request.body))
            if (
                self.request.method == "POST"
                and "Content-Type" not in self.request.headers
            ):
                self.request.headers["Content-Type"] = (
                    "application/x-www-form-urlencoded"
                )
            if self.request.decompress_response:
                self.request.headers["Accept-Encoding"] = "gzip"
            req_path = (self.parsed.path or "/") + (
                ("?" + self.parsed.query) if self.parsed.query else ""
            )
            self.connection = self._create_connection(stream)
            start_line = httputil.RequestStartLine(self.request.method, req_path, "")
            self.connection.write_headers(start_line, self.request.headers)
            if self.request.expect_100_continue:
                await self.connection.read_response(self)
            else:
                await self._write_body(True)
        except Exception:
            if not self._handle_exception(*sys.exc_info()):
                raise

    def _get_ssl_options(
        self, scheme: str
    ) -> Union[None, Dict[str, Any], ssl.SSLContext]:
        if scheme == "https":
            if self.request.ssl_options is not None:
                return self.request.ssl_options
            # If we are using the defaults, don't construct a
            # new SSLContext.
            if (
                self.request.validate_cert
                and self.request.ca_certs is None
                and self.request.client_cert is None
                and self.request.client_key is None
            ):
                return _client_ssl_defaults
            ssl_ctx = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH, cafile=self.request.ca_certs
            )
            if not self.request.validate_cert:
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
            if self.request.client_cert is not None:
                ssl_ctx.load_cert_chain(
                    self.request.client_cert, self.request.client_key
                )
            if hasattr(ssl, "OP_NO_COMPRESSION"):
                # See netutil.ssl_options_to_context
                ssl_ctx.options |= ssl.OP_NO_COMPRESSION
            return ssl_ctx
        return None

    def _on_timeout(self, info: Optional[str] = None) -> None:
        """Timeout callback of _HTTPConnection instance.

        Raise a `HTTPTimeoutError` when a timeout occurs.

        :info string key: More detailed timeout information.
        """
        self._timeout = None
        error_message = f"Timeout {info}" if info else "Timeout"
        if self.final_callback is not None:
            self._handle_exception(
                HTTPTimeoutError, HTTPTimeoutError(error_message), None
            )

    def _remove_timeout(self) -> None:
        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
            self._timeout = None

    def _create_connection(self, stream: IOStream) -> HTTP1Connection:
        stream.set_nodelay(True)
        connection = HTTP1Connection(
            stream,
            True,
            HTTP1ConnectionParameters(
                no_keep_alive=True,
                max_header_size=self.max_header_size,
                max_body_size=self.max_body_size,
                decompress=bool(self.request.decompress_response),
            ),
            self._sockaddr,
        )
        return connection

    async def _write_body(self, start_read: bool) -> None:
        if self.request.body is not None:
            self.connection.write(self.request.body)
        elif self.request.body_producer is not None:
            fut = self.request.body_producer(self.connection.write)
            if fut is not None:
                await fut
        self.connection.finish()
        if start_read:
            try:
                await self.connection.read_response(self)
            except StreamClosedError:
                if not self._handle_exception(*sys.exc_info()):
                    raise

    def _release(self) -> None:
        if self.release_callback is not None:
            release_callback = self.release_callback
            self.release_callback = None  # type: ignore
            release_callback()

    def _run_callback(self, response: HTTPResponse) -> None:
        self._release()
        if self.final_callback is not None:
            final_callback = self.final_callback
            self.final_callback = None  # type: ignore
            self.io_loop.add_callback(final_callback, response)

    def _handle_exception(
        self,
        typ: "Optional[Type[BaseException]]",
        value: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> bool:
        if self.final_callback is not None:
            self._remove_timeout()
            if isinstance(value, StreamClosedError):
                if value.real_error is None:
                    value = HTTPStreamClosedError("Stream closed")
                else:
                    value = value.real_error
            self._run_callback(
                HTTPResponse(
                    self.request,
                    599,
                    error=value,
                    request_time=self.io_loop.time() - self.start_time,
                    start_time=self.start_wall_time,
                )
            )

            if hasattr(self, "stream"):
                # TODO: this may cause a StreamClosedError to be raised
                # by the connection's Future.  Should we cancel the
                # connection more gracefully?
                self.stream.close()
            return True
        else:
            # If our callback has already been called, we are probably
            # catching an exception that is not caused by us but rather
            # some child of our callback. Rather than drop it on the floor,
            # pass it along, unless it's just the stream being closed.
            return isinstance(value, StreamClosedError)

    def on_connection_close(self) -> None:
        if self.final_callback is not None:
            message = "Connection closed"
            if self.stream.error:
                raise self.stream.error
            try:
                raise HTTPStreamClosedError(message)
            except HTTPStreamClosedError:
                self._handle_exception(*sys.exc_info())

    async def headers_received(
        self,
        first_line: Union[httputil.ResponseStartLine, httputil.RequestStartLine],
        headers: httputil.HTTPHeaders,
    ) -> None:
        assert isinstance(first_line, httputil.ResponseStartLine)
        if self.request.expect_100_continue and first_line.code == 100:
            await self._write_body(False)
            return
        self.code = first_line.code
        self.reason = first_line.reason
        self.headers = headers

        if self._should_follow_redirect():
            return

        if self.request.header_callback is not None:
            # Reassemble the start line.
            self.request.header_callback("%s %s %s\r\n" % first_line)
            for k, v in self.headers.get_all():
                self.request.header_callback(f"{k}: {v}\r\n")
            self.request.header_callback("\r\n")

    def _should_follow_redirect(self) -> bool:
        if self.request.follow_redirects:
            assert self.request.max_redirects is not None
            return (
                self.code in (301, 302, 303, 307, 308)
                and self.request.max_redirects > 0
                and self.headers is not None
                and self.headers.get("Location") is not None
            )
        return False

    def finish(self) -> None:
        assert self.code is not None
        data = b"".join(self.chunks)
        self._remove_timeout()
        original_request = getattr(self.request, "original_request", self.request)
        if self._should_follow_redirect():
            assert isinstance(self.request, _RequestProxy)
            assert self.headers is not None
            new_request = copy.copy(self.request.request)
            new_request.url = urllib.parse.urljoin(
                self.request.url, self.headers["Location"]
            )
            assert self.request.max_redirects is not None
            new_request.max_redirects = self.request.max_redirects - 1
            del new_request.headers["Host"]
            # https://tools.ietf.org/html/rfc7231#section-6.4
            #
            # The original HTTP spec said that after a 301 or 302
            # redirect, the request method should be preserved.
            # However, browsers implemented this by changing the
            # method to GET, and the behavior stuck. 303 redirects
            # always specified this POST-to-GET behavior, arguably
            # for *all* methods, but libcurl < 7.70 only does this
            # for POST, while libcurl >= 7.70 does it for other methods.
            if (self.code == 303 and self.request.method != "HEAD") or (
                self.code in (301, 302) and self.request.method == "POST"
            ):
                new_request.method = "GET"
                new_request.body = None  # type: ignore
                for h in [
                    "Content-Length",
                    "Content-Type",
                    "Content-Encoding",
                    "Transfer-Encoding",
                ]:
                    try:
                        del self.request.headers[h]
                    except KeyError:
                        pass
            new_request.original_request = original_request  # type: ignore
            final_callback = self.final_callback
            self.final_callback = None  # type: ignore
            self._release()
            assert self.client is not None
            fut = self.client.fetch(new_request, raise_error=False)
            fut.add_done_callback(lambda f: final_callback(f.result()))
            self._on_end_request()
            return
        if self.request.streaming_callback:
            buffer = BytesIO()
        else:
            buffer = BytesIO(data)  # TODO: don't require one big string?
        response = HTTPResponse(
            original_request,
            self.code,
            reason=getattr(self, "reason", None),
            headers=self.headers,
            request_time=self.io_loop.time() - self.start_time,
            start_time=self.start_wall_time,
            buffer=buffer,
            effective_url=self.request.url,
        )
        self._run_callback(response)
        self._on_end_request()

    def _on_end_request(self) -> None:
        self.stream.close()

    def data_received(self, chunk: bytes) -> None:
        if self._should_follow_redirect():
            # We're going to follow a redirect so just discard the body.
            return
        if self.request.streaming_callback is not None:
            self.request.streaming_callback(chunk)
        else:
            self.chunks.append(chunk)


if __name__ == "__main__":
    AsyncHTTPClient.configure(SimpleAsyncHTTPClient)
    main()

# === NexusCore/openenv\Lib\site-packages\git\objects\util.py ===
# Copyright (C) 2008, 2009 Michael Trier (mtrier@gmail.com) and contributors
#
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

"""Utility functions for working with git objects."""

__all__ = [
    "get_object_type_by_name",
    "parse_date",
    "parse_actor_and_date",
    "ProcessStreamAdapter",
    "Traversable",
    "altz_to_utctz_str",
    "utctz_to_altz",
    "verify_utctz",
    "Actor",
    "tzoffset",
    "utc",
]

from abc import ABC, abstractmethod
import calendar
from collections import deque
from datetime import datetime, timedelta, tzinfo
import re
from string import digits
import time
import warnings

from git.util import Actor, IterableList, IterableObj

# typing ------------------------------------------------------------

from typing import (
    Any,
    Callable,
    Deque,
    Iterator,
    NamedTuple,
    Sequence,
    TYPE_CHECKING,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from git.types import Has_id_attribute, Literal

if TYPE_CHECKING:
    from io import BytesIO, StringIO
    from subprocess import Popen

    from git.types import Protocol, runtime_checkable

    from .blob import Blob
    from .commit import Commit
    from .submodule.base import Submodule
    from .tag import TagObject
    from .tree import TraversedTreeTup, Tree
else:
    Protocol = ABC

    def runtime_checkable(f):
        return f


class TraverseNT(NamedTuple):
    depth: int
    item: Union["Traversable", "Blob"]
    src: Union["Traversable", None]


T_TIobj = TypeVar("T_TIobj", bound="TraversableIterableObj")  # For TraversableIterableObj.traverse()

TraversedTup = Union[
    Tuple[Union["Traversable", None], "Traversable"],  # For Commit, Submodule.
    "TraversedTreeTup",  # For Tree.traverse().
]

# --------------------------------------------------------------------

ZERO = timedelta(0)

# { Functions


def mode_str_to_int(modestr: Union[bytes, str]) -> int:
    """Convert mode bits from an octal mode string to an integer mode for git.

    :param modestr:
        String like ``755`` or ``644`` or ``100644`` - only the last 6 chars will be
        used.

    :return:
        String identifying a mode compatible to the mode methods ids of the :mod:`stat`
        module regarding the rwx permissions for user, group and other, special flags
        and file system flags, such as whether it is a symlink.
    """
    mode = 0
    for iteration, char in enumerate(reversed(modestr[-6:])):
        char = cast(Union[str, int], char)
        mode += int(char) << iteration * 3
    # END for each char
    return mode


def get_object_type_by_name(
    object_type_name: bytes,
) -> Union[Type["Commit"], Type["TagObject"], Type["Tree"], Type["Blob"]]:
    """Retrieve the Python class GitPython uses to represent a kind of Git object.

    :return:
        A type suitable to handle the given as `object_type_name`.
        This type can be called create new instances.

    :param object_type_name:
        Member of :attr:`Object.TYPES <git.objects.base.Object.TYPES>`.

    :raise ValueError:
        If `object_type_name` is unknown.
    """
    if object_type_name == b"commit":
        from . import commit

        return commit.Commit
    elif object_type_name == b"tag":
        from . import tag

        return tag.TagObject
    elif object_type_name == b"blob":
        from . import blob

        return blob.Blob
    elif object_type_name == b"tree":
        from . import tree

        return tree.Tree
    else:
        raise ValueError("Cannot handle unknown object type: %s" % object_type_name.decode())


def utctz_to_altz(utctz: str) -> int:
    """Convert a git timezone offset into a timezone offset west of UTC in seconds
    (compatible with :attr:`time.altzone`).

    :param utctz:
        git utc timezone string, e.g. +0200
    """
    int_utctz = int(utctz)
    seconds = (abs(int_utctz) // 100) * 3600 + (abs(int_utctz) % 100) * 60
    return seconds if int_utctz < 0 else -seconds


def altz_to_utctz_str(altz: float) -> str:
    """Convert a timezone offset west of UTC in seconds into a Git timezone offset
    string.

    :param altz:
        Timezone offset in seconds west of UTC.
    """
    hours = abs(altz) // 3600
    minutes = (abs(altz) % 3600) // 60
    sign = "-" if altz >= 60 else "+"
    return "{}{:02}{:02}".format(sign, hours, minutes)


def verify_utctz(offset: str) -> str:
    """
    :raise ValueError:
        If `offset` is incorrect.

    :return:
        `offset`
    """
    fmt_exc = ValueError("Invalid timezone offset format: %s" % offset)
    if len(offset) != 5:
        raise fmt_exc
    if offset[0] not in "+-":
        raise fmt_exc
    if offset[1] not in digits or offset[2] not in digits or offset[3] not in digits or offset[4] not in digits:
        raise fmt_exc
    # END for each char
    return offset


class tzoffset(tzinfo):
    def __init__(self, secs_west_of_utc: float, name: Union[None, str] = None) -> None:
        self._offset = timedelta(seconds=-secs_west_of_utc)
        self._name = name or "fixed"

    def __reduce__(self) -> Tuple[Type["tzoffset"], Tuple[float, str]]:
        return tzoffset, (-self._offset.total_seconds(), self._name)

    def utcoffset(self, dt: Union[datetime, None]) -> timedelta:
        return self._offset

    def tzname(self, dt: Union[datetime, None]) -> str:
        return self._name

    def dst(self, dt: Union[datetime, None]) -> timedelta:
        return ZERO


utc = tzoffset(0, "UTC")


def from_timestamp(timestamp: float, tz_offset: float) -> datetime:
    """Convert a `timestamp` + `tz_offset` into an aware :class:`~datetime.datetime`
    instance."""
    utc_dt = datetime.fromtimestamp(timestamp, utc)
    try:
        local_dt = utc_dt.astimezone(tzoffset(tz_offset))
        return local_dt
    except ValueError:
        return utc_dt


def parse_date(string_date: Union[str, datetime]) -> Tuple[int, int]:
    """Parse the given date as one of the following:

        * Aware datetime instance
        * Git internal format: timestamp offset
        * :rfc:`2822`: ``Thu, 07 Apr 2005 22:13:13 +0200``
        * ISO 8601: ``2005-04-07T22:13:13`` - The ``T`` can be a space as well.

    :return:
        Tuple(int(timestamp_UTC), int(offset)), both in seconds since epoch

    :raise ValueError:
        If the format could not be understood.

    :note:
        Date can also be ``YYYY.MM.DD``, ``MM/DD/YYYY`` and ``DD.MM.YYYY``.
    """
    if isinstance(string_date, datetime):
        if string_date.tzinfo:
            utcoffset = cast(timedelta, string_date.utcoffset())  # typeguard, if tzinfoand is not None
            offset = -int(utcoffset.total_seconds())
            return int(string_date.astimezone(utc).timestamp()), offset
        else:
            raise ValueError(f"string_date datetime object without tzinfo, {string_date}")

    # Git time
    try:
        if string_date.count(" ") == 1 and string_date.rfind(":") == -1:
            timestamp, offset_str = string_date.split()
            if timestamp.startswith("@"):
                timestamp = timestamp[1:]
            timestamp_int = int(timestamp)
            return timestamp_int, utctz_to_altz(verify_utctz(offset_str))
        else:
            offset_str = "+0000"  # Local time by default.
            if string_date[-5] in "-+":
                offset_str = verify_utctz(string_date[-5:])
                string_date = string_date[:-6]  # skip space as well
            # END split timezone info
            offset = utctz_to_altz(offset_str)

            # Now figure out the date and time portion - split time.
            date_formats = []
            splitter = -1
            if "," in string_date:
                date_formats.append("%a, %d %b %Y")
                splitter = string_date.rfind(" ")
            else:
                # ISO plus additional
                date_formats.append("%Y-%m-%d")
                date_formats.append("%Y.%m.%d")
                date_formats.append("%m/%d/%Y")
                date_formats.append("%d.%m.%Y")

                splitter = string_date.rfind("T")
                if splitter == -1:
                    splitter = string_date.rfind(" ")
                # END handle 'T' and ' '
            # END handle RFC or ISO

            assert splitter > -1

            # Split date and time.
            time_part = string_date[splitter + 1 :]  # Skip space.
            date_part = string_date[:splitter]

            # Parse time.
            tstruct = time.strptime(time_part, "%H:%M:%S")

            for fmt in date_formats:
                try:
                    dtstruct = time.strptime(date_part, fmt)
                    utctime = calendar.timegm(
                        (
                            dtstruct.tm_year,
                            dtstruct.tm_mon,
                            dtstruct.tm_mday,
                            tstruct.tm_hour,
                            tstruct.tm_min,
                            tstruct.tm_sec,
                            dtstruct.tm_wday,
                            dtstruct.tm_yday,
                            tstruct.tm_isdst,
                        )
                    )
                    return int(utctime), offset
                except ValueError:
                    continue
                # END exception handling
            # END for each fmt

            # Still here ? fail.
            raise ValueError("no format matched")
        # END handle format
    except Exception as e:
        raise ValueError(f"Unsupported date format or type: {string_date}, type={type(string_date)}") from e
    # END handle exceptions


# Precompiled regexes
_re_actor_epoch = re.compile(r"^.+? (.*) (\d+) ([+-]\d+).*$")
_re_only_actor = re.compile(r"^.+? (.*)$")


def parse_actor_and_date(line: str) -> Tuple[Actor, int, int]:
    """Parse out the actor (author or committer) info from a line like::

        author Tom Preston-Werner <tom@mojombo.com> 1191999972 -0700

    :return:
        [Actor, int_seconds_since_epoch, int_timezone_offset]
    """
    actor, epoch, offset = "", "0", "0"
    m = _re_actor_epoch.search(line)
    if m:
        actor, epoch, offset = m.groups()
    else:
        m = _re_only_actor.search(line)
        actor = m.group(1) if m else line or ""
    return (Actor._from_string(actor), int(epoch), utctz_to_altz(offset))


# } END functions


# { Classes


class ProcessStreamAdapter:
    """Class wiring all calls to the contained Process instance.

    Use this type to hide the underlying process to provide access only to a specified
    stream. The process is usually wrapped into an :class:`~git.cmd.Git.AutoInterrupt`
    class to kill it if the instance goes out of scope.
    """

    __slots__ = ("_proc", "_stream")

    def __init__(self, process: "Popen", stream_name: str) -> None:
        self._proc = process
        self._stream: StringIO = getattr(process, stream_name)  # guessed type

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._stream, attr)


@runtime_checkable
class Traversable(Protocol):
    """Simple interface to perform depth-first or breadth-first traversals in one
    direction.

    Subclasses only need to implement one function.

    Instances of the subclass must be hashable.

    Defined subclasses:

    * :class:`Commit <git.objects.Commit>`
    * :class:`Tree <git.objects.tree.Tree>`
    * :class:`Submodule <git.objects.submodule.base.Submodule>`
    """

    __slots__ = ()

    @classmethod
    @abstractmethod
    def _get_intermediate_items(cls, item: Any) -> Sequence["Traversable"]:
        """
        :return:
            Tuple of items connected to the given item.
            Must be implemented in subclass.

        class Commit::     (cls, Commit) -> Tuple[Commit, ...]
        class Submodule::  (cls, Submodule) -> Iterablelist[Submodule]
        class Tree::       (cls, Tree) -> Tuple[Tree, ...]
        """
        raise NotImplementedError("To be implemented in subclass")

    @abstractmethod
    def list_traverse(self, *args: Any, **kwargs: Any) -> Any:
        """Traverse self and collect all items found.

        Calling this directly on the abstract base class, including via a ``super()``
        proxy, is deprecated. Only overridden implementations should be called.
        """
        warnings.warn(
            "list_traverse() method should only be called from subclasses."
            " Calling from Traversable abstract class will raise NotImplementedError in 4.0.0."
            " The concrete subclasses in GitPython itself are 'Commit', 'RootModule', 'Submodule', and 'Tree'.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._list_traverse(*args, **kwargs)

    def _list_traverse(
        self, as_edge: bool = False, *args: Any, **kwargs: Any
    ) -> IterableList[Union["Commit", "Submodule", "Tree", "Blob"]]:
        """Traverse self and collect all items found.

        :return:
            :class:`~git.util.IterableList` with the results of the traversal as
            produced by :meth:`traverse`::

                Commit -> IterableList[Commit]
                Submodule ->  IterableList[Submodule]
                Tree -> IterableList[Union[Submodule, Tree, Blob]]
        """
        # Commit and Submodule have id.__attribute__ as IterableObj.
        # Tree has id.__attribute__ inherited from IndexObject.
        if isinstance(self, Has_id_attribute):
            id = self._id_attribute_
        else:
            # Shouldn't reach here, unless Traversable subclass created with no
            # _id_attribute_.
            id = ""
            # Could add _id_attribute_ to Traversable, or make all Traversable also
            # Iterable?

        if not as_edge:
            out: IterableList[Union["Commit", "Submodule", "Tree", "Blob"]] = IterableList(id)
            out.extend(self.traverse(as_edge=as_edge, *args, **kwargs))  # noqa: B026
            return out
            # Overloads in subclasses (mypy doesn't allow typing self: subclass).
            # Union[IterableList['Commit'], IterableList['Submodule'], IterableList[Union['Submodule', 'Tree', 'Blob']]]
        else:
            # Raise DeprecationWarning, it doesn't make sense to use this.
            out_list: IterableList = IterableList(self.traverse(*args, **kwargs))
            return out_list

    @abstractmethod
    def traverse(self, *args: Any, **kwargs: Any) -> Any:
        """Iterator yielding items found when traversing self.

        Calling this directly on the abstract base class, including via a ``super()``
        proxy, is deprecated. Only overridden implementations should be called.
        """
        warnings.warn(
            "traverse() method should only be called from subclasses."
            " Calling from Traversable abstract class will raise NotImplementedError in 4.0.0."
            " The concrete subclasses in GitPython itself are 'Commit', 'RootModule', 'Submodule', and 'Tree'.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._traverse(*args, **kwargs)

    def _traverse(
        self,
        predicate: Callable[[Union["Traversable", "Blob", TraversedTup], int], bool] = lambda i, d: True,
        prune: Callable[[Union["Traversable", "Blob", TraversedTup], int], bool] = lambda i, d: False,
        depth: int = -1,
        branch_first: bool = True,
        visit_once: bool = True,
        ignore_self: int = 1,
        as_edge: bool = False,
    ) -> Union[Iterator[Union["Traversable", "Blob"]], Iterator[TraversedTup]]:
        """Iterator yielding items found when traversing `self`.

        :param predicate:
            A function ``f(i,d)`` that returns ``False`` if item i at depth ``d`` should
            not be included in the result.

        :param prune:
            A function ``f(i,d)`` that returns ``True`` if the search should stop at
            item ``i`` at depth ``d``. Item ``i`` will not be returned.

        :param depth:
            Defines at which level the iteration should not go deeper if -1. There is no
            limit if 0, you would effectively only get `self`, the root of the
            iteration. If 1, you would only get the first level of
            predecessors/successors.

        :param branch_first:
            If ``True``, items will be returned branch first, otherwise depth first.

        :param visit_once:
            If ``True``, items will only be returned once, although they might be
            encountered several times. Loops are prevented that way.

        :param ignore_self:
            If ``True``, `self` will be ignored and automatically pruned from the
            result. Otherwise it will be the first item to be returned. If `as_edge` is
            ``True``, the source of the first edge is ``None``.

        :param as_edge:
            If ``True``, return a pair of items, first being the source, second the
            destination, i.e. tuple(src, dest) with the edge spanning from source to
            destination.

        :return:
            Iterator yielding items found when traversing `self`::

                Commit -> Iterator[Union[Commit, Tuple[Commit, Commit]] Submodule ->
                Iterator[Submodule, Tuple[Submodule, Submodule]] Tree ->
                Iterator[Union[Blob, Tree, Submodule,
                                        Tuple[Union[Submodule, Tree], Union[Blob, Tree,
                                        Submodule]]]

                ignore_self=True is_edge=True -> Iterator[item] ignore_self=True
                is_edge=False --> Iterator[item] ignore_self=False is_edge=True ->
                Iterator[item] | Iterator[Tuple[src, item]] ignore_self=False
                is_edge=False -> Iterator[Tuple[src, item]]
        """

        visited = set()
        stack: Deque[TraverseNT] = deque()
        stack.append(TraverseNT(0, self, None))  # self is always depth level 0.

        def addToStack(
            stack: Deque[TraverseNT],
            src_item: "Traversable",
            branch_first: bool,
            depth: int,
        ) -> None:
            lst = self._get_intermediate_items(item)
            if not lst:  # Empty list
                return
            if branch_first:
                stack.extendleft(TraverseNT(depth, i, src_item) for i in lst)
            else:
                reviter = (TraverseNT(depth, lst[i], src_item) for i in range(len(lst) - 1, -1, -1))
                stack.extend(reviter)

        # END addToStack local method

        while stack:
            d, item, src = stack.pop()  # Depth of item, item, item_source

            if visit_once and item in visited:
                continue

            if visit_once:
                visited.add(item)

            rval: Union[TraversedTup, "Traversable", "Blob"]
            if as_edge:
                # If as_edge return (src, item) unless rrc is None
                # (e.g. for first item).
                rval = (src, item)
            else:
                rval = item

            if prune(rval, d):
                continue

            skipStartItem = ignore_self and (item is self)
            if not skipStartItem and predicate(rval, d):
                yield rval

            # Only continue to next level if this is appropriate!
            next_d = d + 1
            if depth > -1 and next_d > depth:
                continue

            addToStack(stack, item, branch_first, next_d)
        # END for each item on work stack


@runtime_checkable
class Serializable(Protocol):
    """Defines methods to serialize and deserialize objects from and into a data
    stream."""

    __slots__ = ()

    # @abstractmethod
    def _serialize(self, stream: "BytesIO") -> "Serializable":
        """Serialize the data of this object into the given data stream.

        :note:
            A serialized object would :meth:`_deserialize` into the same object.

        :param stream:
            A file-like object.

        :return:
            self
        """
        raise NotImplementedError("To be implemented in subclass")

    # @abstractmethod
    def _deserialize(self, stream: "BytesIO") -> "Serializable":
        """Deserialize all information regarding this object from the stream.

        :param stream:
            A file-like object.

        :return:
            self
        """
        raise NotImplementedError("To be implemented in subclass")


class TraversableIterableObj(IterableObj, Traversable):
    __slots__ = ()

    TIobj_tuple = Tuple[Union[T_TIobj, None], T_TIobj]

    def list_traverse(self: T_TIobj, *args: Any, **kwargs: Any) -> IterableList[T_TIobj]:
        return super()._list_traverse(*args, **kwargs)

    @overload
    def traverse(self: T_TIobj) -> Iterator[T_TIobj]: ...

    @overload
    def traverse(
        self: T_TIobj,
        predicate: Callable[[Union[T_TIobj, Tuple[Union[T_TIobj, None], T_TIobj]], int], bool],
        prune: Callable[[Union[T_TIobj, Tuple[Union[T_TIobj, None], T_TIobj]], int], bool],
        depth: int,
        branch_first: bool,
        visit_once: bool,
        ignore_self: Literal[True],
        as_edge: Literal[False],
    ) -> Iterator[T_TIobj]: ...

    @overload
    def traverse(
        self: T_TIobj,
        predicate: Callable[[Union[T_TIobj, Tuple[Union[T_TIobj, None], T_TIobj]], int], bool],
        prune: Callable[[Union[T_TIobj, Tuple[Union[T_TIobj, None], T_TIobj]], int], bool],
        depth: int,
        branch_first: bool,
        visit_once: bool,
        ignore_self: Literal[False],
        as_edge: Literal[True],
    ) -> Iterator[Tuple[Union[T_TIobj, None], T_TIobj]]: ...

    @overload
    def traverse(
        self: T_TIobj,
        predicate: Callable[[Union[T_TIobj, TIobj_tuple], int], bool],
        prune: Callable[[Union[T_TIobj, TIobj_tuple], int], bool],
        depth: int,
        branch_first: bool,
        visit_once: bool,
        ignore_self: Literal[True],
        as_edge: Literal[True],
    ) -> Iterator[Tuple[T_TIobj, T_TIobj]]: ...

    def traverse(
        self: T_TIobj,
        predicate: Callable[[Union[T_TIobj, TIobj_tuple], int], bool] = lambda i, d: True,
        prune: Callable[[Union[T_TIobj, TIobj_tuple], int], bool] = lambda i, d: False,
        depth: int = -1,
        branch_first: bool = True,
        visit_once: bool = True,
        ignore_self: int = 1,
        as_edge: bool = False,
    ) -> Union[Iterator[T_TIobj], Iterator[Tuple[T_TIobj, T_TIobj]], Iterator[TIobj_tuple]]:
        """For documentation, see :meth:`Traversable._traverse`."""

        ## To typecheck instead of using cast:
        #
        # import itertools
        # from git.types import TypeGuard
        # def is_commit_traversed(inp: Tuple) -> TypeGuard[Tuple[Iterator[Tuple['Commit', 'Commit']]]]:
        #     for x in inp[1]:
        #         if not isinstance(x, tuple) and len(x) != 2:
        #             if all(isinstance(inner, Commit) for inner in x):
        #                 continue
        #     return True
        #
        # ret = super(Commit, self).traverse(predicate, prune, depth, branch_first, visit_once, ignore_self, as_edge)
        # ret_tup = itertools.tee(ret, 2)
        # assert is_commit_traversed(ret_tup), f"{[type(x) for x in list(ret_tup[0])]}"
        # return ret_tup[0]

        return cast(
            Union[Iterator[T_TIobj], Iterator[Tuple[Union[None, T_TIobj], T_TIobj]]],
            super()._traverse(
                predicate,  # type: ignore[arg-type]
                prune,  # type: ignore[arg-type]
                depth,
                branch_first,
                visit_once,
                ignore_self,
                as_edge,
            ),
        )

# === NexusCore/openenv\Lib\site-packages\pyasn1\type\base.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import sys

from pyasn1 import error
from pyasn1.type import constraint
from pyasn1.type import tag
from pyasn1.type import tagmap

__all__ = ['Asn1Item', 'Asn1Type', 'SimpleAsn1Type',
           'ConstructedAsn1Type']


class Asn1Item(object):
    @classmethod
    def getTypeId(cls, increment=1):
        try:
            Asn1Item._typeCounter += increment
        except AttributeError:
            Asn1Item._typeCounter = increment
        return Asn1Item._typeCounter


class Asn1Type(Asn1Item):
    """Base class for all classes representing ASN.1 types.

    In the user code, |ASN.1| class is normally used only for telling
    ASN.1 objects from others.

    Note
    ----
    For as long as ASN.1 is concerned, a way to compare ASN.1 types
    is to use :meth:`isSameTypeWith` and :meth:`isSuperTypeOf` methods.
    """
    #: Set or return a :py:class:`~pyasn1.type.tag.TagSet` object representing
    #: ASN.1 tag(s) associated with |ASN.1| type.
    tagSet = tag.TagSet()

    #: Default :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
    #: object imposing constraints on initialization values.
    subtypeSpec = constraint.ConstraintsIntersection()

    # Disambiguation ASN.1 types identification
    typeId = None

    def __init__(self, **kwargs):
        readOnly = {
            'tagSet': self.tagSet,
            'subtypeSpec': self.subtypeSpec
        }

        readOnly.update(kwargs)

        self.__dict__.update(readOnly)

        self._readOnly = readOnly

    def __setattr__(self, name, value):
        if name[0] != '_' and name in self._readOnly:
            raise error.PyAsn1Error('read-only instance attribute "%s"' % name)

        self.__dict__[name] = value

    def __str__(self):
        return self.prettyPrint()

    @property
    def readOnly(self):
        return self._readOnly

    @property
    def effectiveTagSet(self):
        """For |ASN.1| type is equivalent to *tagSet*
        """
        return self.tagSet  # used by untagged types

    @property
    def tagMap(self):
        """Return a :class:`~pyasn1.type.tagmap.TagMap` object mapping ASN.1 tags to ASN.1 objects within callee object.
        """
        return tagmap.TagMap({self.tagSet: self})

    def isSameTypeWith(self, other, matchTags=True, matchConstraints=True):
        """Examine |ASN.1| type for equality with other ASN.1 type.

        ASN.1 tags (:py:mod:`~pyasn1.type.tag`) and constraints
        (:py:mod:`~pyasn1.type.constraint`) are examined when carrying
        out ASN.1 types comparison.

        Python class inheritance relationship is NOT considered.

        Parameters
        ----------
        other: a pyasn1 type object
            Class instance representing ASN.1 type.

        Returns
        -------
        : :class:`bool`
            :obj:`True` if *other* is |ASN.1| type,
            :obj:`False` otherwise.
        """
        return (self is other or
                (not matchTags or self.tagSet == other.tagSet) and
                (not matchConstraints or self.subtypeSpec == other.subtypeSpec))

    def isSuperTypeOf(self, other, matchTags=True, matchConstraints=True):
        """Examine |ASN.1| type for subtype relationship with other ASN.1 type.

        ASN.1 tags (:py:mod:`~pyasn1.type.tag`) and constraints
        (:py:mod:`~pyasn1.type.constraint`) are examined when carrying
        out ASN.1 types comparison.

        Python class inheritance relationship is NOT considered.

        Parameters
        ----------
            other: a pyasn1 type object
                Class instance representing ASN.1 type.

        Returns
        -------
            : :class:`bool`
                :obj:`True` if *other* is a subtype of |ASN.1| type,
                :obj:`False` otherwise.
        """
        return (not matchTags or
                (self.tagSet.isSuperTagSetOf(other.tagSet)) and
                 (not matchConstraints or self.subtypeSpec.isSuperTypeOf(other.subtypeSpec)))

    @staticmethod
    def isNoValue(*values):
        for value in values:
            if value is not noValue:
                return False
        return True

    def prettyPrint(self, scope=0):
        raise NotImplementedError

    # backward compatibility

    def getTagSet(self):
        return self.tagSet

    def getEffectiveTagSet(self):
        return self.effectiveTagSet

    def getTagMap(self):
        return self.tagMap

    def getSubtypeSpec(self):
        return self.subtypeSpec

    # backward compatibility
    def hasValue(self):
        return self.isValue

# Backward compatibility
Asn1ItemBase = Asn1Type


class NoValue(object):
    """Create a singleton instance of NoValue class.

    The *NoValue* sentinel object represents an instance of ASN.1 schema
    object as opposed to ASN.1 value object.

    Only ASN.1 schema-related operations can be performed on ASN.1
    schema objects.

    Warning
    -------
    Any operation attempted on the *noValue* object will raise the
    *PyAsn1Error* exception.
    """
    skipMethods = {
        '__slots__',
        # attributes
        '__getattribute__',
        '__getattr__',
        '__setattr__',
        '__delattr__',
        # class instance
        '__class__',
        '__init__',
        '__del__',
        '__new__',
        '__repr__',
        '__qualname__',
        '__objclass__',
        'im_class',
        '__sizeof__',
        # pickle protocol
        '__reduce__',
        '__reduce_ex__',
        '__getnewargs__',
        '__getinitargs__',
        '__getstate__',
        '__setstate__',
    }

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            def getPlug(name):
                def plug(self, *args, **kw):
                    raise error.PyAsn1Error('Attempted "%s" operation on ASN.1 schema object' % name)
                return plug

            op_names = [name
                        for typ in (str, int, list, dict)
                        for name in dir(typ)
                        if (name not in cls.skipMethods and
                            name.startswith('__') and
                            name.endswith('__') and
                            callable(getattr(typ, name)))]

            for name in set(op_names):
                setattr(cls, name, getPlug(name))

            cls._instance = object.__new__(cls)

        return cls._instance

    def __getattr__(self, attr):
        if attr in self.skipMethods:
            raise AttributeError('Attribute %s not present' % attr)

        raise error.PyAsn1Error('Attempted "%s" operation on ASN.1 schema object' % attr)

    def __repr__(self):
        return '<%s object>' % self.__class__.__name__


noValue = NoValue()


class SimpleAsn1Type(Asn1Type):
    """Base class for all simple classes representing ASN.1 types.

    ASN.1 distinguishes types by their ability to hold other objects.
    Scalar types are known as *simple* in ASN.1.

    In the user code, |ASN.1| class is normally used only for telling
    ASN.1 objects from others.

    Note
    ----
    For as long as ASN.1 is concerned, a way to compare ASN.1 types
    is to use :meth:`isSameTypeWith` and :meth:`isSuperTypeOf` methods.
    """
    #: Default payload value
    defaultValue = noValue

    def __init__(self, value=noValue, **kwargs):
        Asn1Type.__init__(self, **kwargs)
        if value is noValue:
            value = self.defaultValue
        else:
            value = self.prettyIn(value)
            try:
                self.subtypeSpec(value)

            except error.PyAsn1Error as exValue:
                raise type(exValue)('%s at %s' % (exValue, self.__class__.__name__))

        self._value = value

    def __repr__(self):
        representation = '%s %s object' % (
            self.__class__.__name__, self.isValue and 'value' or 'schema')

        for attr, value in self.readOnly.items():
            if value:
                representation += ', %s %s' % (attr, value)

        if self.isValue:
            value = self.prettyPrint()
            if len(value) > 32:
                value = value[:16] + '...' + value[-16:]
            representation += ', payload [%s]' % value

        return '<%s>' % representation

    def __eq__(self, other):
        if self is other:
            return True
        return self._value == other

    def __ne__(self, other):
        return self._value != other

    def __lt__(self, other):
        return self._value < other

    def __le__(self, other):
        return self._value <= other

    def __gt__(self, other):
        return self._value > other

    def __ge__(self, other):
        return self._value >= other

    def __bool__(self):
        return bool(self._value)

    def __hash__(self):
        return hash(self._value)

    @property
    def isValue(self):
        """Indicate that |ASN.1| object represents ASN.1 value.

        If *isValue* is :obj:`False` then this object represents just
        ASN.1 schema.

        If *isValue* is :obj:`True` then, in addition to its ASN.1 schema
        features, this object can also be used like a Python built-in object
        (e.g. :class:`int`, :class:`str`, :class:`dict` etc.).

        Returns
        -------
        : :class:`bool`
            :obj:`False` if object represents just ASN.1 schema.
            :obj:`True` if object represents ASN.1 schema and can be used as a normal value.

        Note
        ----
        There is an important distinction between PyASN1 schema and value objects.
        The PyASN1 schema objects can only participate in ASN.1 schema-related
        operations (e.g. defining or testing the structure of the data). Most
        obvious uses of ASN.1 schema is to guide serialisation codecs whilst
        encoding/decoding serialised ASN.1 contents.

        The PyASN1 value objects can **additionally** participate in many operations
        involving regular Python objects (e.g. arithmetic, comprehension etc).
        """
        return self._value is not noValue

    def clone(self, value=noValue, **kwargs):
        """Create a modified version of |ASN.1| schema or value object.

        The `clone()` method accepts the same set arguments as |ASN.1|
        class takes on instantiation except that all arguments
        of the `clone()` method are optional.

        Whatever arguments are supplied, they are used to create a copy
        of `self` taking precedence over the ones used to instantiate `self`.

        Note
        ----
        Due to the immutable nature of the |ASN.1| object, if no arguments
        are supplied, no new |ASN.1| object will be created and `self` will
        be returned instead.
        """
        if value is noValue:
            if not kwargs:
                return self

            value = self._value

        initializers = self.readOnly.copy()
        initializers.update(kwargs)

        return self.__class__(value, **initializers)

    def subtype(self, value=noValue, **kwargs):
        """Create a specialization of |ASN.1| schema or value object.

        The subtype relationship between ASN.1 types has no correlation with
        subtype relationship between Python types. ASN.1 type is mainly identified
        by its tag(s) (:py:class:`~pyasn1.type.tag.TagSet`) and value range
        constraints (:py:class:`~pyasn1.type.constraint.ConstraintsIntersection`).
        These ASN.1 type properties are implemented as |ASN.1| attributes.  

        The `subtype()` method accepts the same set arguments as |ASN.1|
        class takes on instantiation except that all parameters
        of the `subtype()` method are optional.

        With the exception of the arguments described below, the rest of
        supplied arguments they are used to create a copy of `self` taking
        precedence over the ones used to instantiate `self`.

        The following arguments to `subtype()` create a ASN.1 subtype out of
        |ASN.1| type:

        Other Parameters
        ----------------
        implicitTag: :py:class:`~pyasn1.type.tag.Tag`
            Implicitly apply given ASN.1 tag object to `self`'s
            :py:class:`~pyasn1.type.tag.TagSet`, then use the result as
            new object's ASN.1 tag(s).

        explicitTag: :py:class:`~pyasn1.type.tag.Tag`
            Explicitly apply given ASN.1 tag object to `self`'s
            :py:class:`~pyasn1.type.tag.TagSet`, then use the result as
            new object's ASN.1 tag(s).

        subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
            Add ASN.1 constraints object to one of the `self`'s, then
            use the result as new object's ASN.1 constraints.

        Returns
        -------
        :
            new instance of |ASN.1| schema or value object

        Note
        ----
        Due to the immutable nature of the |ASN.1| object, if no arguments
        are supplied, no new |ASN.1| object will be created and `self` will
        be returned instead.
        """
        if value is noValue:
            if not kwargs:
                return self

            value = self._value

        initializers = self.readOnly.copy()

        implicitTag = kwargs.pop('implicitTag', None)
        if implicitTag is not None:
            initializers['tagSet'] = self.tagSet.tagImplicitly(implicitTag)

        explicitTag = kwargs.pop('explicitTag', None)
        if explicitTag is not None:
            initializers['tagSet'] = self.tagSet.tagExplicitly(explicitTag)

        for arg, option in kwargs.items():
            initializers[arg] += option

        return self.__class__(value, **initializers)

    def prettyIn(self, value):
        return value

    def prettyOut(self, value):
        return str(value)

    def prettyPrint(self, scope=0):
        return self.prettyOut(self._value)

    def prettyPrintType(self, scope=0):
        return '%s -> %s' % (self.tagSet, self.__class__.__name__)

# Backward compatibility
AbstractSimpleAsn1Item = SimpleAsn1Type

#
# Constructed types:
# * There are five of them: Sequence, SequenceOf/SetOf, Set and Choice
# * ASN1 types and values are represened by Python class instances
# * Value initialization is made for defaulted components only
# * Primary method of component addressing is by-position. Data model for base
#   type is Python sequence. Additional type-specific addressing methods
#   may be implemented for particular types.
# * SequenceOf and SetOf types do not implement any additional methods
# * Sequence, Set and Choice types also implement by-identifier addressing
# * Sequence, Set and Choice types also implement by-asn1-type (tag) addressing
# * Sequence and Set types may include optional and defaulted
#   components
# * Constructed types hold a reference to component types used for value
#   verification and ordering.
# * Component type is a scalar type for SequenceOf/SetOf types and a list
#   of types for Sequence/Set/Choice.
#


class ConstructedAsn1Type(Asn1Type):
    """Base class for all constructed classes representing ASN.1 types.

    ASN.1 distinguishes types by their ability to hold other objects.
    Those "nesting" types are known as *constructed* in ASN.1.

    In the user code, |ASN.1| class is normally used only for telling
    ASN.1 objects from others.

    Note
    ----
    For as long as ASN.1 is concerned, a way to compare ASN.1 types
    is to use :meth:`isSameTypeWith` and :meth:`isSuperTypeOf` methods.
    """

    #: If :obj:`True`, requires exact component type matching,
    #: otherwise subtype relation is only enforced
    strictConstraints = False

    componentType = None

    # backward compatibility, unused
    sizeSpec = constraint.ConstraintsIntersection()

    def __init__(self, **kwargs):
        readOnly = {
            'componentType': self.componentType,
            # backward compatibility, unused
            'sizeSpec': self.sizeSpec
        }

        # backward compatibility: preserve legacy sizeSpec support
        kwargs = self._moveSizeSpec(**kwargs)

        readOnly.update(kwargs)

        Asn1Type.__init__(self, **readOnly)

    def _moveSizeSpec(self, **kwargs):
        # backward compatibility, unused
        sizeSpec = kwargs.pop('sizeSpec', self.sizeSpec)
        if sizeSpec:
            subtypeSpec = kwargs.pop('subtypeSpec', self.subtypeSpec)
            if subtypeSpec:
                subtypeSpec = sizeSpec

            else:
                subtypeSpec += sizeSpec

            kwargs['subtypeSpec'] = subtypeSpec

        return kwargs

    def __repr__(self):
        representation = '%s %s object' % (
            self.__class__.__name__, self.isValue and 'value' or 'schema'
        )

        for attr, value in self.readOnly.items():
            if value is not noValue:
                representation += ', %s=%r' % (attr, value)

        if self.isValue and self.components:
            representation += ', payload [%s]' % ', '.join(
                [repr(x) for x in self.components])

        return '<%s>' % representation

    def __eq__(self, other):
        return self is other or self.components == other

    def __ne__(self, other):
        return self.components != other

    def __lt__(self, other):
        return self.components < other

    def __le__(self, other):
        return self.components <= other

    def __gt__(self, other):
        return self.components > other

    def __ge__(self, other):
        return self.components >= other

    def __bool__(self):
        return bool(self.components)

    @property
    def components(self):
        raise error.PyAsn1Error('Method not implemented')

    def _cloneComponentValues(self, myClone, cloneValueFlag):
        pass

    def clone(self, **kwargs):
        """Create a modified version of |ASN.1| schema object.

        The `clone()` method accepts the same set arguments as |ASN.1|
        class takes on instantiation except that all arguments
        of the `clone()` method are optional.

        Whatever arguments are supplied, they are used to create a copy
        of `self` taking precedence over the ones used to instantiate `self`.

        Possible values of `self` are never copied over thus `clone()` can
        only create a new schema object.

        Returns
        -------
        :
            new instance of |ASN.1| type/value

        Note
        ----
        Due to the mutable nature of the |ASN.1| object, even if no arguments
        are supplied, a new |ASN.1| object will be created and returned.
        """
        cloneValueFlag = kwargs.pop('cloneValueFlag', False)

        initializers = self.readOnly.copy()
        initializers.update(kwargs)

        clone = self.__class__(**initializers)

        if cloneValueFlag:
            self._cloneComponentValues(clone, cloneValueFlag)

        return clone

    def subtype(self, **kwargs):
        """Create a specialization of |ASN.1| schema object.

        The `subtype()` method accepts the same set arguments as |ASN.1|
        class takes on instantiation except that all parameters
        of the `subtype()` method are optional.

        With the exception of the arguments described below, the rest of
        supplied arguments they are used to create a copy of `self` taking
        precedence over the ones used to instantiate `self`.

        The following arguments to `subtype()` create a ASN.1 subtype out of
        |ASN.1| type.

        Other Parameters
        ----------------
        implicitTag: :py:class:`~pyasn1.type.tag.Tag`
            Implicitly apply given ASN.1 tag object to `self`'s
            :py:class:`~pyasn1.type.tag.TagSet`, then use the result as
            new object's ASN.1 tag(s).

        explicitTag: :py:class:`~pyasn1.type.tag.Tag`
            Explicitly apply given ASN.1 tag object to `self`'s
            :py:class:`~pyasn1.type.tag.TagSet`, then use the result as
            new object's ASN.1 tag(s).

        subtypeSpec: :py:class:`~pyasn1.type.constraint.ConstraintsIntersection`
            Add ASN.1 constraints object to one of the `self`'s, then
            use the result as new object's ASN.1 constraints.


        Returns
        -------
        :
            new instance of |ASN.1| type/value

        Note
        ----
        Due to the mutable nature of the |ASN.1| object, even if no arguments
        are supplied, a new |ASN.1| object will be created and returned.
        """

        initializers = self.readOnly.copy()

        cloneValueFlag = kwargs.pop('cloneValueFlag', False)

        implicitTag = kwargs.pop('implicitTag', None)
        if implicitTag is not None:
            initializers['tagSet'] = self.tagSet.tagImplicitly(implicitTag)

        explicitTag = kwargs.pop('explicitTag', None)
        if explicitTag is not None:
            initializers['tagSet'] = self.tagSet.tagExplicitly(explicitTag)

        for arg, option in kwargs.items():
            initializers[arg] += option

        clone = self.__class__(**initializers)

        if cloneValueFlag:
            self._cloneComponentValues(clone, cloneValueFlag)

        return clone

    def getComponentByPosition(self, idx):
        raise error.PyAsn1Error('Method not implemented')

    def setComponentByPosition(self, idx, value, verifyConstraints=True):
        raise error.PyAsn1Error('Method not implemented')

    def setComponents(self, *args, **kwargs):
        for idx, value in enumerate(args):
            self[idx] = value
        for k in kwargs:
            self[k] = kwargs[k]
        return self

    # backward compatibility

    def setDefaultComponents(self):
        pass

    def getComponentType(self):
        return self.componentType

    # backward compatibility, unused
    def verifySizeSpec(self):
        self.subtypeSpec(self)


        # Backward compatibility
AbstractConstructedAsn1Item = ConstructedAsn1Type