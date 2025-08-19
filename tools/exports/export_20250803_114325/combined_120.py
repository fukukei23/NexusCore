
# === NexusCore/openenv\Lib\site-packages\openai\resources\vector_stores\files.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Union, Optional
from typing_extensions import Literal, assert_never

import httpx

from ... import _legacy_response
from ...types import FileChunkingStrategyParam
from ..._types import NOT_GIVEN, Body, Query, Headers, NotGiven, FileTypes
from ..._utils import is_given, maybe_transform, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...pagination import SyncPage, AsyncPage, SyncCursorPage, AsyncCursorPage
from ..._base_client import AsyncPaginator, make_request_options
from ...types.vector_stores import file_list_params, file_create_params, file_update_params
from ...types.file_chunking_strategy_param import FileChunkingStrategyParam
from ...types.vector_stores.vector_store_file import VectorStoreFile
from ...types.vector_stores.file_content_response import FileContentResponse
from ...types.vector_stores.vector_store_file_deleted import VectorStoreFileDeleted

__all__ = ["Files", "AsyncFiles"]


class Files(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> FilesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return FilesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> FilesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return FilesWithStreamingResponse(self)

    def create(
        self,
        vector_store_id: str,
        *,
        file_id: str,
        attributes: Optional[Dict[str, Union[str, float, bool]]] | NotGiven = NOT_GIVEN,
        chunking_strategy: FileChunkingStrategyParam | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """
        Create a vector store file by attaching a
        [File](https://platform.openai.com/docs/api-reference/files) to a
        [vector store](https://platform.openai.com/docs/api-reference/vector-stores/object).

        Args:
          file_id: A [File](https://platform.openai.com/docs/api-reference/files) ID that the
              vector store should use. Useful for tools like `file_search` that can access
              files.

          attributes: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard. Keys are strings with a maximum
              length of 64 characters. Values are strings with a maximum length of 512
              characters, booleans, or numbers.

          chunking_strategy: The chunking strategy used to chunk the file(s). If not set, will use the `auto`
              strategy. Only applicable if `file_ids` is non-empty.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            f"/vector_stores/{vector_store_id}/files",
            body=maybe_transform(
                {
                    "file_id": file_id,
                    "attributes": attributes,
                    "chunking_strategy": chunking_strategy,
                },
                file_create_params.FileCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStoreFile,
        )

    def retrieve(
        self,
        file_id: str,
        *,
        vector_store_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """
        Retrieves a vector store file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get(
            f"/vector_stores/{vector_store_id}/files/{file_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStoreFile,
        )

    def update(
        self,
        file_id: str,
        *,
        vector_store_id: str,
        attributes: Optional[Dict[str, Union[str, float, bool]]],
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """
        Update attributes on a vector store file.

        Args:
          attributes: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard. Keys are strings with a maximum
              length of 64 characters. Values are strings with a maximum length of 512
              characters, booleans, or numbers.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            f"/vector_stores/{vector_store_id}/files/{file_id}",
            body=maybe_transform({"attributes": attributes}, file_update_params.FileUpdateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStoreFile,
        )

    def list(
        self,
        vector_store_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        filter: Literal["in_progress", "completed", "failed", "cancelled"] | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[VectorStoreFile]:
        """
        Returns a list of vector store files.

        Args:
          after: A cursor for use in pagination. `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          before: A cursor for use in pagination. `before` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              starting with obj_foo, your subsequent call can include before=obj_foo in order
              to fetch the previous page of the list.

          filter: Filter by file status. One of `in_progress`, `completed`, `failed`, `cancelled`.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            f"/vector_stores/{vector_store_id}/files",
            page=SyncCursorPage[VectorStoreFile],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "filter": filter,
                        "limit": limit,
                        "order": order,
                    },
                    file_list_params.FileListParams,
                ),
            ),
            model=VectorStoreFile,
        )

    def delete(
        self,
        file_id: str,
        *,
        vector_store_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFileDeleted:
        """Delete a vector store file.

        This will remove the file from the vector store but
        the file itself will not be deleted. To delete the file, use the
        [delete file](https://platform.openai.com/docs/api-reference/files/delete)
        endpoint.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._delete(
            f"/vector_stores/{vector_store_id}/files/{file_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStoreFileDeleted,
        )

    def create_and_poll(
        self,
        file_id: str,
        *,
        vector_store_id: str,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
        chunking_strategy: FileChunkingStrategyParam | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """Attach a file to the given vector store and wait for it to be processed."""
        self.create(vector_store_id=vector_store_id, file_id=file_id, chunking_strategy=chunking_strategy)

        return self.poll(
            file_id,
            vector_store_id=vector_store_id,
            poll_interval_ms=poll_interval_ms,
        )

    def poll(
        self,
        file_id: str,
        *,
        vector_store_id: str,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """Wait for the vector store file to finish processing.

        Note: this will return even if the file failed to process, you need to check
        file.last_error and file.status to handle these cases
        """
        headers: dict[str, str] = {"X-Stainless-Poll-Helper": "true"}
        if is_given(poll_interval_ms):
            headers["X-Stainless-Custom-Poll-Interval"] = str(poll_interval_ms)

        while True:
            response = self.with_raw_response.retrieve(
                file_id,
                vector_store_id=vector_store_id,
                extra_headers=headers,
            )

            file = response.parse()
            if file.status == "in_progress":
                if not is_given(poll_interval_ms):
                    from_header = response.headers.get("openai-poll-after-ms")
                    if from_header is not None:
                        poll_interval_ms = int(from_header)
                    else:
                        poll_interval_ms = 1000

                self._sleep(poll_interval_ms / 1000)
            elif file.status == "cancelled" or file.status == "completed" or file.status == "failed":
                return file
            else:
                if TYPE_CHECKING:  # type: ignore[unreachable]
                    assert_never(file.status)
                else:
                    return file

    def upload(
        self,
        *,
        vector_store_id: str,
        file: FileTypes,
        chunking_strategy: FileChunkingStrategyParam | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """Upload a file to the `files` API and then attach it to the given vector store.

        Note the file will be asynchronously processed (you can use the alternative
        polling helper method to wait for processing to complete).
        """
        file_obj = self._client.files.create(file=file, purpose="assistants")
        return self.create(vector_store_id=vector_store_id, file_id=file_obj.id, chunking_strategy=chunking_strategy)

    def upload_and_poll(
        self,
        *,
        vector_store_id: str,
        file: FileTypes,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
        chunking_strategy: FileChunkingStrategyParam | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """Add a file to a vector store and poll until processing is complete."""
        file_obj = self._client.files.create(file=file, purpose="assistants")
        return self.create_and_poll(
            vector_store_id=vector_store_id,
            file_id=file_obj.id,
            chunking_strategy=chunking_strategy,
            poll_interval_ms=poll_interval_ms,
        )

    def content(
        self,
        file_id: str,
        *,
        vector_store_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncPage[FileContentResponse]:
        """
        Retrieve the parsed contents of a vector store file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            f"/vector_stores/{vector_store_id}/files/{file_id}/content",
            page=SyncPage[FileContentResponse],
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            model=FileContentResponse,
        )


class AsyncFiles(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncFilesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncFilesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncFilesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncFilesWithStreamingResponse(self)

    async def create(
        self,
        vector_store_id: str,
        *,
        file_id: str,
        attributes: Optional[Dict[str, Union[str, float, bool]]] | NotGiven = NOT_GIVEN,
        chunking_strategy: FileChunkingStrategyParam | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """
        Create a vector store file by attaching a
        [File](https://platform.openai.com/docs/api-reference/files) to a
        [vector store](https://platform.openai.com/docs/api-reference/vector-stores/object).

        Args:
          file_id: A [File](https://platform.openai.com/docs/api-reference/files) ID that the
              vector store should use. Useful for tools like `file_search` that can access
              files.

          attributes: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard. Keys are strings with a maximum
              length of 64 characters. Values are strings with a maximum length of 512
              characters, booleans, or numbers.

          chunking_strategy: The chunking strategy used to chunk the file(s). If not set, will use the `auto`
              strategy. Only applicable if `file_ids` is non-empty.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            f"/vector_stores/{vector_store_id}/files",
            body=await async_maybe_transform(
                {
                    "file_id": file_id,
                    "attributes": attributes,
                    "chunking_strategy": chunking_strategy,
                },
                file_create_params.FileCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStoreFile,
        )

    async def retrieve(
        self,
        file_id: str,
        *,
        vector_store_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """
        Retrieves a vector store file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._get(
            f"/vector_stores/{vector_store_id}/files/{file_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStoreFile,
        )

    async def update(
        self,
        file_id: str,
        *,
        vector_store_id: str,
        attributes: Optional[Dict[str, Union[str, float, bool]]],
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """
        Update attributes on a vector store file.

        Args:
          attributes: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard. Keys are strings with a maximum
              length of 64 characters. Values are strings with a maximum length of 512
              characters, booleans, or numbers.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            f"/vector_stores/{vector_store_id}/files/{file_id}",
            body=await async_maybe_transform({"attributes": attributes}, file_update_params.FileUpdateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStoreFile,
        )

    def list(
        self,
        vector_store_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        filter: Literal["in_progress", "completed", "failed", "cancelled"] | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[VectorStoreFile, AsyncCursorPage[VectorStoreFile]]:
        """
        Returns a list of vector store files.

        Args:
          after: A cursor for use in pagination. `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          before: A cursor for use in pagination. `before` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              starting with obj_foo, your subsequent call can include before=obj_foo in order
              to fetch the previous page of the list.

          filter: Filter by file status. One of `in_progress`, `completed`, `failed`, `cancelled`.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            f"/vector_stores/{vector_store_id}/files",
            page=AsyncCursorPage[VectorStoreFile],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "filter": filter,
                        "limit": limit,
                        "order": order,
                    },
                    file_list_params.FileListParams,
                ),
            ),
            model=VectorStoreFile,
        )

    async def delete(
        self,
        file_id: str,
        *,
        vector_store_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFileDeleted:
        """Delete a vector store file.

        This will remove the file from the vector store but
        the file itself will not be deleted. To delete the file, use the
        [delete file](https://platform.openai.com/docs/api-reference/files/delete)
        endpoint.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._delete(
            f"/vector_stores/{vector_store_id}/files/{file_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStoreFileDeleted,
        )

    async def create_and_poll(
        self,
        file_id: str,
        *,
        vector_store_id: str,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
        chunking_strategy: FileChunkingStrategyParam | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """Attach a file to the given vector store and wait for it to be processed."""
        await self.create(vector_store_id=vector_store_id, file_id=file_id, chunking_strategy=chunking_strategy)

        return await self.poll(
            file_id,
            vector_store_id=vector_store_id,
            poll_interval_ms=poll_interval_ms,
        )

    async def poll(
        self,
        file_id: str,
        *,
        vector_store_id: str,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """Wait for the vector store file to finish processing.

        Note: this will return even if the file failed to process, you need to check
        file.last_error and file.status to handle these cases
        """
        headers: dict[str, str] = {"X-Stainless-Poll-Helper": "true"}
        if is_given(poll_interval_ms):
            headers["X-Stainless-Custom-Poll-Interval"] = str(poll_interval_ms)

        while True:
            response = await self.with_raw_response.retrieve(
                file_id,
                vector_store_id=vector_store_id,
                extra_headers=headers,
            )

            file = response.parse()
            if file.status == "in_progress":
                if not is_given(poll_interval_ms):
                    from_header = response.headers.get("openai-poll-after-ms")
                    if from_header is not None:
                        poll_interval_ms = int(from_header)
                    else:
                        poll_interval_ms = 1000

                await self._sleep(poll_interval_ms / 1000)
            elif file.status == "cancelled" or file.status == "completed" or file.status == "failed":
                return file
            else:
                if TYPE_CHECKING:  # type: ignore[unreachable]
                    assert_never(file.status)
                else:
                    return file

    async def upload(
        self,
        *,
        vector_store_id: str,
        file: FileTypes,
        chunking_strategy: FileChunkingStrategyParam | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """Upload a file to the `files` API and then attach it to the given vector store.

        Note the file will be asynchronously processed (you can use the alternative
        polling helper method to wait for processing to complete).
        """
        file_obj = await self._client.files.create(file=file, purpose="assistants")
        return await self.create(
            vector_store_id=vector_store_id, file_id=file_obj.id, chunking_strategy=chunking_strategy
        )

    async def upload_and_poll(
        self,
        *,
        vector_store_id: str,
        file: FileTypes,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
        chunking_strategy: FileChunkingStrategyParam | NotGiven = NOT_GIVEN,
    ) -> VectorStoreFile:
        """Add a file to a vector store and poll until processing is complete."""
        file_obj = await self._client.files.create(file=file, purpose="assistants")
        return await self.create_and_poll(
            vector_store_id=vector_store_id,
            file_id=file_obj.id,
            poll_interval_ms=poll_interval_ms,
            chunking_strategy=chunking_strategy,
        )

    def content(
        self,
        file_id: str,
        *,
        vector_store_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[FileContentResponse, AsyncPage[FileContentResponse]]:
        """
        Retrieve the parsed contents of a vector store file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        if not file_id:
            raise ValueError(f"Expected a non-empty value for `file_id` but received {file_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            f"/vector_stores/{vector_store_id}/files/{file_id}/content",
            page=AsyncPage[FileContentResponse],
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            model=FileContentResponse,
        )


class FilesWithRawResponse:
    def __init__(self, files: Files) -> None:
        self._files = files

        self.create = _legacy_response.to_raw_response_wrapper(
            files.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            files.retrieve,
        )
        self.update = _legacy_response.to_raw_response_wrapper(
            files.update,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            files.list,
        )
        self.delete = _legacy_response.to_raw_response_wrapper(
            files.delete,
        )
        self.content = _legacy_response.to_raw_response_wrapper(
            files.content,
        )


class AsyncFilesWithRawResponse:
    def __init__(self, files: AsyncFiles) -> None:
        self._files = files

        self.create = _legacy_response.async_to_raw_response_wrapper(
            files.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            files.retrieve,
        )
        self.update = _legacy_response.async_to_raw_response_wrapper(
            files.update,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            files.list,
        )
        self.delete = _legacy_response.async_to_raw_response_wrapper(
            files.delete,
        )
        self.content = _legacy_response.async_to_raw_response_wrapper(
            files.content,
        )


class FilesWithStreamingResponse:
    def __init__(self, files: Files) -> None:
        self._files = files

        self.create = to_streamed_response_wrapper(
            files.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            files.retrieve,
        )
        self.update = to_streamed_response_wrapper(
            files.update,
        )
        self.list = to_streamed_response_wrapper(
            files.list,
        )
        self.delete = to_streamed_response_wrapper(
            files.delete,
        )
        self.content = to_streamed_response_wrapper(
            files.content,
        )


class AsyncFilesWithStreamingResponse:
    def __init__(self, files: AsyncFiles) -> None:
        self._files = files

        self.create = async_to_streamed_response_wrapper(
            files.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            files.retrieve,
        )
        self.update = async_to_streamed_response_wrapper(
            files.update,
        )
        self.list = async_to_streamed_response_wrapper(
            files.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            files.delete,
        )
        self.content = async_to_streamed_response_wrapper(
            files.content,
        )

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\msgpack\fallback.py ===
"""Fallback pure Python implementation of msgpack"""

import struct
import sys
from datetime import datetime as _DateTime

if hasattr(sys, "pypy_version_info"):
    from __pypy__ import newlist_hint
    from __pypy__.builders import BytesBuilder

    _USING_STRINGBUILDER = True

    class BytesIO:
        def __init__(self, s=b""):
            if s:
                self.builder = BytesBuilder(len(s))
                self.builder.append(s)
            else:
                self.builder = BytesBuilder()

        def write(self, s):
            if isinstance(s, memoryview):
                s = s.tobytes()
            elif isinstance(s, bytearray):
                s = bytes(s)
            self.builder.append(s)

        def getvalue(self):
            return self.builder.build()

else:
    from io import BytesIO

    _USING_STRINGBUILDER = False

    def newlist_hint(size):
        return []


from .exceptions import BufferFull, ExtraData, FormatError, OutOfData, StackError
from .ext import ExtType, Timestamp

EX_SKIP = 0
EX_CONSTRUCT = 1
EX_READ_ARRAY_HEADER = 2
EX_READ_MAP_HEADER = 3

TYPE_IMMEDIATE = 0
TYPE_ARRAY = 1
TYPE_MAP = 2
TYPE_RAW = 3
TYPE_BIN = 4
TYPE_EXT = 5

DEFAULT_RECURSE_LIMIT = 511


def _check_type_strict(obj, t, type=type, tuple=tuple):
    if type(t) is tuple:
        return type(obj) in t
    else:
        return type(obj) is t


def _get_data_from_buffer(obj):
    view = memoryview(obj)
    if view.itemsize != 1:
        raise ValueError("cannot unpack from multi-byte object")
    return view


def unpackb(packed, **kwargs):
    """
    Unpack an object from `packed`.

    Raises ``ExtraData`` when *packed* contains extra bytes.
    Raises ``ValueError`` when *packed* is incomplete.
    Raises ``FormatError`` when *packed* is not valid msgpack.
    Raises ``StackError`` when *packed* contains too nested.
    Other exceptions can be raised during unpacking.

    See :class:`Unpacker` for options.
    """
    unpacker = Unpacker(None, max_buffer_size=len(packed), **kwargs)
    unpacker.feed(packed)
    try:
        ret = unpacker._unpack()
    except OutOfData:
        raise ValueError("Unpack failed: incomplete input")
    except RecursionError:
        raise StackError
    if unpacker._got_extradata():
        raise ExtraData(ret, unpacker._get_extradata())
    return ret


_NO_FORMAT_USED = ""
_MSGPACK_HEADERS = {
    0xC4: (1, _NO_FORMAT_USED, TYPE_BIN),
    0xC5: (2, ">H", TYPE_BIN),
    0xC6: (4, ">I", TYPE_BIN),
    0xC7: (2, "Bb", TYPE_EXT),
    0xC8: (3, ">Hb", TYPE_EXT),
    0xC9: (5, ">Ib", TYPE_EXT),
    0xCA: (4, ">f"),
    0xCB: (8, ">d"),
    0xCC: (1, _NO_FORMAT_USED),
    0xCD: (2, ">H"),
    0xCE: (4, ">I"),
    0xCF: (8, ">Q"),
    0xD0: (1, "b"),
    0xD1: (2, ">h"),
    0xD2: (4, ">i"),
    0xD3: (8, ">q"),
    0xD4: (1, "b1s", TYPE_EXT),
    0xD5: (2, "b2s", TYPE_EXT),
    0xD6: (4, "b4s", TYPE_EXT),
    0xD7: (8, "b8s", TYPE_EXT),
    0xD8: (16, "b16s", TYPE_EXT),
    0xD9: (1, _NO_FORMAT_USED, TYPE_RAW),
    0xDA: (2, ">H", TYPE_RAW),
    0xDB: (4, ">I", TYPE_RAW),
    0xDC: (2, ">H", TYPE_ARRAY),
    0xDD: (4, ">I", TYPE_ARRAY),
    0xDE: (2, ">H", TYPE_MAP),
    0xDF: (4, ">I", TYPE_MAP),
}


class Unpacker:
    """Streaming unpacker.

    Arguments:

    :param file_like:
        File-like object having `.read(n)` method.
        If specified, unpacker reads serialized data from it and `.feed()` is not usable.

    :param int read_size:
        Used as `file_like.read(read_size)`. (default: `min(16*1024, max_buffer_size)`)

    :param bool use_list:
        If true, unpack msgpack array to Python list.
        Otherwise, unpack to Python tuple. (default: True)

    :param bool raw:
        If true, unpack msgpack raw to Python bytes.
        Otherwise, unpack to Python str by decoding with UTF-8 encoding (default).

    :param int timestamp:
        Control how timestamp type is unpacked:

            0 - Timestamp
            1 - float  (Seconds from the EPOCH)
            2 - int  (Nanoseconds from the EPOCH)
            3 - datetime.datetime  (UTC).

    :param bool strict_map_key:
        If true (default), only str or bytes are accepted for map (dict) keys.

    :param object_hook:
        When specified, it should be callable.
        Unpacker calls it with a dict argument after unpacking msgpack map.
        (See also simplejson)

    :param object_pairs_hook:
        When specified, it should be callable.
        Unpacker calls it with a list of key-value pairs after unpacking msgpack map.
        (See also simplejson)

    :param str unicode_errors:
        The error handler for decoding unicode. (default: 'strict')
        This option should be used only when you have msgpack data which
        contains invalid UTF-8 string.

    :param int max_buffer_size:
        Limits size of data waiting unpacked.  0 means 2**32-1.
        The default value is 100*1024*1024 (100MiB).
        Raises `BufferFull` exception when it is insufficient.
        You should set this parameter when unpacking data from untrusted source.

    :param int max_str_len:
        Deprecated, use *max_buffer_size* instead.
        Limits max length of str. (default: max_buffer_size)

    :param int max_bin_len:
        Deprecated, use *max_buffer_size* instead.
        Limits max length of bin. (default: max_buffer_size)

    :param int max_array_len:
        Limits max length of array.
        (default: max_buffer_size)

    :param int max_map_len:
        Limits max length of map.
        (default: max_buffer_size//2)

    :param int max_ext_len:
        Deprecated, use *max_buffer_size* instead.
        Limits max size of ext type.  (default: max_buffer_size)

    Example of streaming deserialize from file-like object::

        unpacker = Unpacker(file_like)
        for o in unpacker:
            process(o)

    Example of streaming deserialize from socket::

        unpacker = Unpacker()
        while True:
            buf = sock.recv(1024**2)
            if not buf:
                break
            unpacker.feed(buf)
            for o in unpacker:
                process(o)

    Raises ``ExtraData`` when *packed* contains extra bytes.
    Raises ``OutOfData`` when *packed* is incomplete.
    Raises ``FormatError`` when *packed* is not valid msgpack.
    Raises ``StackError`` when *packed* contains too nested.
    Other exceptions can be raised during unpacking.
    """

    def __init__(
        self,
        file_like=None,
        *,
        read_size=0,
        use_list=True,
        raw=False,
        timestamp=0,
        strict_map_key=True,
        object_hook=None,
        object_pairs_hook=None,
        list_hook=None,
        unicode_errors=None,
        max_buffer_size=100 * 1024 * 1024,
        ext_hook=ExtType,
        max_str_len=-1,
        max_bin_len=-1,
        max_array_len=-1,
        max_map_len=-1,
        max_ext_len=-1,
    ):
        if unicode_errors is None:
            unicode_errors = "strict"

        if file_like is None:
            self._feeding = True
        else:
            if not callable(file_like.read):
                raise TypeError("`file_like.read` must be callable")
            self.file_like = file_like
            self._feeding = False

        #: array of bytes fed.
        self._buffer = bytearray()
        #: Which position we currently reads
        self._buff_i = 0

        # When Unpacker is used as an iterable, between the calls to next(),
        # the buffer is not "consumed" completely, for efficiency sake.
        # Instead, it is done sloppily.  To make sure we raise BufferFull at
        # the correct moments, we have to keep track of how sloppy we were.
        # Furthermore, when the buffer is incomplete (that is: in the case
        # we raise an OutOfData) we need to rollback the buffer to the correct
        # state, which _buf_checkpoint records.
        self._buf_checkpoint = 0

        if not max_buffer_size:
            max_buffer_size = 2**31 - 1
        if max_str_len == -1:
            max_str_len = max_buffer_size
        if max_bin_len == -1:
            max_bin_len = max_buffer_size
        if max_array_len == -1:
            max_array_len = max_buffer_size
        if max_map_len == -1:
            max_map_len = max_buffer_size // 2
        if max_ext_len == -1:
            max_ext_len = max_buffer_size

        self._max_buffer_size = max_buffer_size
        if read_size > self._max_buffer_size:
            raise ValueError("read_size must be smaller than max_buffer_size")
        self._read_size = read_size or min(self._max_buffer_size, 16 * 1024)
        self._raw = bool(raw)
        self._strict_map_key = bool(strict_map_key)
        self._unicode_errors = unicode_errors
        self._use_list = use_list
        if not (0 <= timestamp <= 3):
            raise ValueError("timestamp must be 0..3")
        self._timestamp = timestamp
        self._list_hook = list_hook
        self._object_hook = object_hook
        self._object_pairs_hook = object_pairs_hook
        self._ext_hook = ext_hook
        self._max_str_len = max_str_len
        self._max_bin_len = max_bin_len
        self._max_array_len = max_array_len
        self._max_map_len = max_map_len
        self._max_ext_len = max_ext_len
        self._stream_offset = 0

        if list_hook is not None and not callable(list_hook):
            raise TypeError("`list_hook` is not callable")
        if object_hook is not None and not callable(object_hook):
            raise TypeError("`object_hook` is not callable")
        if object_pairs_hook is not None and not callable(object_pairs_hook):
            raise TypeError("`object_pairs_hook` is not callable")
        if object_hook is not None and object_pairs_hook is not None:
            raise TypeError("object_pairs_hook and object_hook are mutually exclusive")
        if not callable(ext_hook):
            raise TypeError("`ext_hook` is not callable")

    def feed(self, next_bytes):
        assert self._feeding
        view = _get_data_from_buffer(next_bytes)
        if len(self._buffer) - self._buff_i + len(view) > self._max_buffer_size:
            raise BufferFull

        # Strip buffer before checkpoint before reading file.
        if self._buf_checkpoint > 0:
            del self._buffer[: self._buf_checkpoint]
            self._buff_i -= self._buf_checkpoint
            self._buf_checkpoint = 0

        # Use extend here: INPLACE_ADD += doesn't reliably typecast memoryview in jython
        self._buffer.extend(view)
        view.release()

    def _consume(self):
        """Gets rid of the used parts of the buffer."""
        self._stream_offset += self._buff_i - self._buf_checkpoint
        self._buf_checkpoint = self._buff_i

    def _got_extradata(self):
        return self._buff_i < len(self._buffer)

    def _get_extradata(self):
        return self._buffer[self._buff_i :]

    def read_bytes(self, n):
        ret = self._read(n, raise_outofdata=False)
        self._consume()
        return ret

    def _read(self, n, raise_outofdata=True):
        # (int) -> bytearray
        self._reserve(n, raise_outofdata=raise_outofdata)
        i = self._buff_i
        ret = self._buffer[i : i + n]
        self._buff_i = i + len(ret)
        return ret

    def _reserve(self, n, raise_outofdata=True):
        remain_bytes = len(self._buffer) - self._buff_i - n

        # Fast path: buffer has n bytes already
        if remain_bytes >= 0:
            return

        if self._feeding:
            self._buff_i = self._buf_checkpoint
            raise OutOfData

        # Strip buffer before checkpoint before reading file.
        if self._buf_checkpoint > 0:
            del self._buffer[: self._buf_checkpoint]
            self._buff_i -= self._buf_checkpoint
            self._buf_checkpoint = 0

        # Read from file
        remain_bytes = -remain_bytes
        if remain_bytes + len(self._buffer) > self._max_buffer_size:
            raise BufferFull
        while remain_bytes > 0:
            to_read_bytes = max(self._read_size, remain_bytes)
            read_data = self.file_like.read(to_read_bytes)
            if not read_data:
                break
            assert isinstance(read_data, bytes)
            self._buffer += read_data
            remain_bytes -= len(read_data)

        if len(self._buffer) < n + self._buff_i and raise_outofdata:
            self._buff_i = 0  # rollback
            raise OutOfData

    def _read_header(self):
        typ = TYPE_IMMEDIATE
        n = 0
        obj = None
        self._reserve(1)
        b = self._buffer[self._buff_i]
        self._buff_i += 1
        if b & 0b10000000 == 0:
            obj = b
        elif b & 0b11100000 == 0b11100000:
            obj = -1 - (b ^ 0xFF)
        elif b & 0b11100000 == 0b10100000:
            n = b & 0b00011111
            typ = TYPE_RAW
            if n > self._max_str_len:
                raise ValueError(f"{n} exceeds max_str_len({self._max_str_len})")
            obj = self._read(n)
        elif b & 0b11110000 == 0b10010000:
            n = b & 0b00001111
            typ = TYPE_ARRAY
            if n > self._max_array_len:
                raise ValueError(f"{n} exceeds max_array_len({self._max_array_len})")
        elif b & 0b11110000 == 0b10000000:
            n = b & 0b00001111
            typ = TYPE_MAP
            if n > self._max_map_len:
                raise ValueError(f"{n} exceeds max_map_len({self._max_map_len})")
        elif b == 0xC0:
            obj = None
        elif b == 0xC2:
            obj = False
        elif b == 0xC3:
            obj = True
        elif 0xC4 <= b <= 0xC6:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            if len(fmt) > 0:
                n = struct.unpack_from(fmt, self._buffer, self._buff_i)[0]
            else:
                n = self._buffer[self._buff_i]
            self._buff_i += size
            if n > self._max_bin_len:
                raise ValueError(f"{n} exceeds max_bin_len({self._max_bin_len})")
            obj = self._read(n)
        elif 0xC7 <= b <= 0xC9:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            L, n = struct.unpack_from(fmt, self._buffer, self._buff_i)
            self._buff_i += size
            if L > self._max_ext_len:
                raise ValueError(f"{L} exceeds max_ext_len({self._max_ext_len})")
            obj = self._read(L)
        elif 0xCA <= b <= 0xD3:
            size, fmt = _MSGPACK_HEADERS[b]
            self._reserve(size)
            if len(fmt) > 0:
                obj = struct.unpack_from(fmt, self._buffer, self._buff_i)[0]
            else:
                obj = self._buffer[self._buff_i]
            self._buff_i += size
        elif 0xD4 <= b <= 0xD8:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            if self._max_ext_len < size:
                raise ValueError(f"{size} exceeds max_ext_len({self._max_ext_len})")
            self._reserve(size + 1)
            n, obj = struct.unpack_from(fmt, self._buffer, self._buff_i)
            self._buff_i += size + 1
        elif 0xD9 <= b <= 0xDB:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            if len(fmt) > 0:
                (n,) = struct.unpack_from(fmt, self._buffer, self._buff_i)
            else:
                n = self._buffer[self._buff_i]
            self._buff_i += size
            if n > self._max_str_len:
                raise ValueError(f"{n} exceeds max_str_len({self._max_str_len})")
            obj = self._read(n)
        elif 0xDC <= b <= 0xDD:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            (n,) = struct.unpack_from(fmt, self._buffer, self._buff_i)
            self._buff_i += size
            if n > self._max_array_len:
                raise ValueError(f"{n} exceeds max_array_len({self._max_array_len})")
        elif 0xDE <= b <= 0xDF:
            size, fmt, typ = _MSGPACK_HEADERS[b]
            self._reserve(size)
            (n,) = struct.unpack_from(fmt, self._buffer, self._buff_i)
            self._buff_i += size
            if n > self._max_map_len:
                raise ValueError(f"{n} exceeds max_map_len({self._max_map_len})")
        else:
            raise FormatError("Unknown header: 0x%x" % b)
        return typ, n, obj

    def _unpack(self, execute=EX_CONSTRUCT):
        typ, n, obj = self._read_header()

        if execute == EX_READ_ARRAY_HEADER:
            if typ != TYPE_ARRAY:
                raise ValueError("Expected array")
            return n
        if execute == EX_READ_MAP_HEADER:
            if typ != TYPE_MAP:
                raise ValueError("Expected map")
            return n
        # TODO should we eliminate the recursion?
        if typ == TYPE_ARRAY:
            if execute == EX_SKIP:
                for i in range(n):
                    # TODO check whether we need to call `list_hook`
                    self._unpack(EX_SKIP)
                return
            ret = newlist_hint(n)
            for i in range(n):
                ret.append(self._unpack(EX_CONSTRUCT))
            if self._list_hook is not None:
                ret = self._list_hook(ret)
            # TODO is the interaction between `list_hook` and `use_list` ok?
            return ret if self._use_list else tuple(ret)
        if typ == TYPE_MAP:
            if execute == EX_SKIP:
                for i in range(n):
                    # TODO check whether we need to call hooks
                    self._unpack(EX_SKIP)
                    self._unpack(EX_SKIP)
                return
            if self._object_pairs_hook is not None:
                ret = self._object_pairs_hook(
                    (self._unpack(EX_CONSTRUCT), self._unpack(EX_CONSTRUCT)) for _ in range(n)
                )
            else:
                ret = {}
                for _ in range(n):
                    key = self._unpack(EX_CONSTRUCT)
                    if self._strict_map_key and type(key) not in (str, bytes):
                        raise ValueError("%s is not allowed for map key" % str(type(key)))
                    if isinstance(key, str):
                        key = sys.intern(key)
                    ret[key] = self._unpack(EX_CONSTRUCT)
                if self._object_hook is not None:
                    ret = self._object_hook(ret)
            return ret
        if execute == EX_SKIP:
            return
        if typ == TYPE_RAW:
            if self._raw:
                obj = bytes(obj)
            else:
                obj = obj.decode("utf_8", self._unicode_errors)
            return obj
        if typ == TYPE_BIN:
            return bytes(obj)
        if typ == TYPE_EXT:
            if n == -1:  # timestamp
                ts = Timestamp.from_bytes(bytes(obj))
                if self._timestamp == 1:
                    return ts.to_unix()
                elif self._timestamp == 2:
                    return ts.to_unix_nano()
                elif self._timestamp == 3:
                    return ts.to_datetime()
                else:
                    return ts
            else:
                return self._ext_hook(n, bytes(obj))
        assert typ == TYPE_IMMEDIATE
        return obj

    def __iter__(self):
        return self

    def __next__(self):
        try:
            ret = self._unpack(EX_CONSTRUCT)
            self._consume()
            return ret
        except OutOfData:
            self._consume()
            raise StopIteration
        except RecursionError:
            raise StackError

    next = __next__

    def skip(self):
        self._unpack(EX_SKIP)
        self._consume()

    def unpack(self):
        try:
            ret = self._unpack(EX_CONSTRUCT)
        except RecursionError:
            raise StackError
        self._consume()
        return ret

    def read_array_header(self):
        ret = self._unpack(EX_READ_ARRAY_HEADER)
        self._consume()
        return ret

    def read_map_header(self):
        ret = self._unpack(EX_READ_MAP_HEADER)
        self._consume()
        return ret

    def tell(self):
        return self._stream_offset


class Packer:
    """
    MessagePack Packer

    Usage::

        packer = Packer()
        astream.write(packer.pack(a))
        astream.write(packer.pack(b))

    Packer's constructor has some keyword arguments:

    :param default:
        When specified, it should be callable.
        Convert user type to builtin type that Packer supports.
        See also simplejson's document.

    :param bool use_single_float:
        Use single precision float type for float. (default: False)

    :param bool autoreset:
        Reset buffer after each pack and return its content as `bytes`. (default: True).
        If set this to false, use `bytes()` to get content and `.reset()` to clear buffer.

    :param bool use_bin_type:
        Use bin type introduced in msgpack spec 2.0 for bytes.
        It also enables str8 type for unicode. (default: True)

    :param bool strict_types:
        If set to true, types will be checked to be exact. Derived classes
        from serializable types will not be serialized and will be
        treated as unsupported type and forwarded to default.
        Additionally tuples will not be serialized as lists.
        This is useful when trying to implement accurate serialization
        for python types.

    :param bool datetime:
        If set to true, datetime with tzinfo is packed into Timestamp type.
        Note that the tzinfo is stripped in the timestamp.
        You can get UTC datetime with `timestamp=3` option of the Unpacker.

    :param str unicode_errors:
        The error handler for encoding unicode. (default: 'strict')
        DO NOT USE THIS!!  This option is kept for very specific usage.

    :param int buf_size:
        Internal buffer size. This option is used only for C implementation.
    """

    def __init__(
        self,
        *,
        default=None,
        use_single_float=False,
        autoreset=True,
        use_bin_type=True,
        strict_types=False,
        datetime=False,
        unicode_errors=None,
        buf_size=None,
    ):
        self._strict_types = strict_types
        self._use_float = use_single_float
        self._autoreset = autoreset
        self._use_bin_type = use_bin_type
        self._buffer = BytesIO()
        self._datetime = bool(datetime)
        self._unicode_errors = unicode_errors or "strict"
        if default is not None and not callable(default):
            raise TypeError("default must be callable")
        self._default = default

    def _pack(
        self,
        obj,
        nest_limit=DEFAULT_RECURSE_LIMIT,
        check=isinstance,
        check_type_strict=_check_type_strict,
    ):
        default_used = False
        if self._strict_types:
            check = check_type_strict
            list_types = list
        else:
            list_types = (list, tuple)
        while True:
            if nest_limit < 0:
                raise ValueError("recursion limit exceeded")
            if obj is None:
                return self._buffer.write(b"\xc0")
            if check(obj, bool):
                if obj:
                    return self._buffer.write(b"\xc3")
                return self._buffer.write(b"\xc2")
            if check(obj, int):
                if 0 <= obj < 0x80:
                    return self._buffer.write(struct.pack("B", obj))
                if -0x20 <= obj < 0:
                    return self._buffer.write(struct.pack("b", obj))
                if 0x80 <= obj <= 0xFF:
                    return self._buffer.write(struct.pack("BB", 0xCC, obj))
                if -0x80 <= obj < 0:
                    return self._buffer.write(struct.pack(">Bb", 0xD0, obj))
                if 0xFF < obj <= 0xFFFF:
                    return self._buffer.write(struct.pack(">BH", 0xCD, obj))
                if -0x8000 <= obj < -0x80:
                    return self._buffer.write(struct.pack(">Bh", 0xD1, obj))
                if 0xFFFF < obj <= 0xFFFFFFFF:
                    return self._buffer.write(struct.pack(">BI", 0xCE, obj))
                if -0x80000000 <= obj < -0x8000:
                    return self._buffer.write(struct.pack(">Bi", 0xD2, obj))
                if 0xFFFFFFFF < obj <= 0xFFFFFFFFFFFFFFFF:
                    return self._buffer.write(struct.pack(">BQ", 0xCF, obj))
                if -0x8000000000000000 <= obj < -0x80000000:
                    return self._buffer.write(struct.pack(">Bq", 0xD3, obj))
                if not default_used and self._default is not None:
                    obj = self._default(obj)
                    default_used = True
                    continue
                raise OverflowError("Integer value out of range")
            if check(obj, (bytes, bytearray)):
                n = len(obj)
                if n >= 2**32:
                    raise ValueError("%s is too large" % type(obj).__name__)
                self._pack_bin_header(n)
                return self._buffer.write(obj)
            if check(obj, str):
                obj = obj.encode("utf-8", self._unicode_errors)
                n = len(obj)
                if n >= 2**32:
                    raise ValueError("String is too large")
                self._pack_raw_header(n)
                return self._buffer.write(obj)
            if check(obj, memoryview):
                n = obj.nbytes
                if n >= 2**32:
                    raise ValueError("Memoryview is too large")
                self._pack_bin_header(n)
                return self._buffer.write(obj)
            if check(obj, float):
                if self._use_float:
                    return self._buffer.write(struct.pack(">Bf", 0xCA, obj))
                return self._buffer.write(struct.pack(">Bd", 0xCB, obj))
            if check(obj, (ExtType, Timestamp)):
                if check(obj, Timestamp):
                    code = -1
                    data = obj.to_bytes()
                else:
                    code = obj.code
                    data = obj.data
                assert isinstance(code, int)
                assert isinstance(data, bytes)
                L = len(data)
                if L == 1:
                    self._buffer.write(b"\xd4")
                elif L == 2:
                    self._buffer.write(b"\xd5")
                elif L == 4:
                    self._buffer.write(b"\xd6")
                elif L == 8:
                    self._buffer.write(b"\xd7")
                elif L == 16:
                    self._buffer.write(b"\xd8")
                elif L <= 0xFF:
                    self._buffer.write(struct.pack(">BB", 0xC7, L))
                elif L <= 0xFFFF:
                    self._buffer.write(struct.pack(">BH", 0xC8, L))
                else:
                    self._buffer.write(struct.pack(">BI", 0xC9, L))
                self._buffer.write(struct.pack("b", code))
                self._buffer.write(data)
                return
            if check(obj, list_types):
                n = len(obj)
                self._pack_array_header(n)
                for i in range(n):
                    self._pack(obj[i], nest_limit - 1)
                return
            if check(obj, dict):
                return self._pack_map_pairs(len(obj), obj.items(), nest_limit - 1)

            if self._datetime and check(obj, _DateTime) and obj.tzinfo is not None:
                obj = Timestamp.from_datetime(obj)
                default_used = 1
                continue

            if not default_used and self._default is not None:
                obj = self._default(obj)
                default_used = 1
                continue

            if self._datetime and check(obj, _DateTime):
                raise ValueError(f"Cannot serialize {obj!r} where tzinfo=None")

            raise TypeError(f"Cannot serialize {obj!r}")

    def pack(self, obj):
        try:
            self._pack(obj)
        except:
            self._buffer = BytesIO()  # force reset
            raise
        if self._autoreset:
            ret = self._buffer.getvalue()
            self._buffer = BytesIO()
            return ret

    def pack_map_pairs(self, pairs):
        self._pack_map_pairs(len(pairs), pairs)
        if self._autoreset:
            ret = self._buffer.getvalue()
            self._buffer = BytesIO()
            return ret

    def pack_array_header(self, n):
        if n >= 2**32:
            raise ValueError
        self._pack_array_header(n)
        if self._autoreset:
            ret = self._buffer.getvalue()
            self._buffer = BytesIO()
            return ret

    def pack_map_header(self, n):
        if n >= 2**32:
            raise ValueError
        self._pack_map_header(n)
        if self._autoreset:
            ret = self._buffer.getvalue()
            self._buffer = BytesIO()
            return ret

    def pack_ext_type(self, typecode, data):
        if not isinstance(typecode, int):
            raise TypeError("typecode must have int type.")
        if not 0 <= typecode <= 127:
            raise ValueError("typecode should be 0-127")
        if not isinstance(data, bytes):
            raise TypeError("data must have bytes type")
        L = len(data)
        if L > 0xFFFFFFFF:
            raise ValueError("Too large data")
        if L == 1:
            self._buffer.write(b"\xd4")
        elif L == 2:
            self._buffer.write(b"\xd5")
        elif L == 4:
            self._buffer.write(b"\xd6")
        elif L == 8:
            self._buffer.write(b"\xd7")
        elif L == 16:
            self._buffer.write(b"\xd8")
        elif L <= 0xFF:
            self._buffer.write(b"\xc7" + struct.pack("B", L))
        elif L <= 0xFFFF:
            self._buffer.write(b"\xc8" + struct.pack(">H", L))
        else:
            self._buffer.write(b"\xc9" + struct.pack(">I", L))
        self._buffer.write(struct.pack("B", typecode))
        self._buffer.write(data)

    def _pack_array_header(self, n):
        if n <= 0x0F:
            return self._buffer.write(struct.pack("B", 0x90 + n))
        if n <= 0xFFFF:
            return self._buffer.write(struct.pack(">BH", 0xDC, n))
        if n <= 0xFFFFFFFF:
            return self._buffer.write(struct.pack(">BI", 0xDD, n))
        raise ValueError("Array is too large")

    def _pack_map_header(self, n):
        if n <= 0x0F:
            return self._buffer.write(struct.pack("B", 0x80 + n))
        if n <= 0xFFFF:
            return self._buffer.write(struct.pack(">BH", 0xDE, n))
        if n <= 0xFFFFFFFF:
            return self._buffer.write(struct.pack(">BI", 0xDF, n))
        raise ValueError("Dict is too large")

    def _pack_map_pairs(self, n, pairs, nest_limit=DEFAULT_RECURSE_LIMIT):
        self._pack_map_header(n)
        for k, v in pairs:
            self._pack(k, nest_limit - 1)
            self._pack(v, nest_limit - 1)

    def _pack_raw_header(self, n):
        if n <= 0x1F:
            self._buffer.write(struct.pack("B", 0xA0 + n))
        elif self._use_bin_type and n <= 0xFF:
            self._buffer.write(struct.pack(">BB", 0xD9, n))
        elif n <= 0xFFFF:
            self._buffer.write(struct.pack(">BH", 0xDA, n))
        elif n <= 0xFFFFFFFF:
            self._buffer.write(struct.pack(">BI", 0xDB, n))
        else:
            raise ValueError("Raw is too large")

    def _pack_bin_header(self, n):
        if not self._use_bin_type:
            return self._pack_raw_header(n)
        elif n <= 0xFF:
            return self._buffer.write(struct.pack(">BB", 0xC4, n))
        elif n <= 0xFFFF:
            return self._buffer.write(struct.pack(">BH", 0xC5, n))
        elif n <= 0xFFFFFFFF:
            return self._buffer.write(struct.pack(">BI", 0xC6, n))
        else:
            raise ValueError("Bin is too large")

    def bytes(self):
        """Return internal buffer contents as bytes object"""
        return self._buffer.getvalue()

    def reset(self):
        """Reset internal buffer.

        This method is useful only when autoreset=False.
        """
        self._buffer = BytesIO()

    def getbuffer(self):
        """Return view of internal buffer."""
        if _USING_STRINGBUILDER:
            return memoryview(self.bytes())
        else:
            return self._buffer.getbuffer()

# === NexusCore/openenv\Lib\site-packages\fontTools\cffLib\specializer.py ===
# -*- coding: utf-8 -*-

"""T2CharString operator specializer and generalizer.

PostScript glyph drawing operations can be expressed in multiple different
ways. For example, as well as the ``lineto`` operator, there is also a
``hlineto`` operator which draws a horizontal line, removing the need to
specify a ``dx`` coordinate, and a ``vlineto`` operator which draws a
vertical line, removing the need to specify a ``dy`` coordinate. As well
as decompiling :class:`fontTools.misc.psCharStrings.T2CharString` objects
into lists of operations, this module allows for conversion between general
and specific forms of the operation.

"""

from fontTools.cffLib import maxStackLimit


def stringToProgram(string):
    if isinstance(string, str):
        string = string.split()
    program = []
    for token in string:
        try:
            token = int(token)
        except ValueError:
            try:
                token = float(token)
            except ValueError:
                pass
        program.append(token)
    return program


def programToString(program):
    return " ".join(str(x) for x in program)


def programToCommands(program, getNumRegions=None):
    """Takes a T2CharString program list and returns list of commands.
    Each command is a two-tuple of commandname,arg-list.  The commandname might
    be empty string if no commandname shall be emitted (used for glyph width,
    hintmask/cntrmask argument, as well as stray arguments at the end of the
    program (🤷).
    'getNumRegions' may be None, or a callable object. It must return the
    number of regions. 'getNumRegions' takes a single argument, vsindex. It
    returns the numRegions for the vsindex.
    The Charstring may or may not start with a width value. If the first
    non-blend operator has an odd number of arguments, then the first argument is
    a width, and is popped off. This is complicated with blend operators, as
    there may be more than one before the first hint or moveto operator, and each
    one reduces several arguments to just one list argument. We have to sum the
    number of arguments that are not part of the blend arguments, and all the
    'numBlends' values. We could instead have said that by definition, if there
    is a blend operator, there is no width value, since CFF2 Charstrings don't
    have width values. I discussed this with Behdad, and we are allowing for an
    initial width value in this case because developers may assemble a CFF2
    charstring from CFF Charstrings, which could have width values.
    """

    seenWidthOp = False
    vsIndex = 0
    lenBlendStack = 0
    lastBlendIndex = 0
    commands = []
    stack = []
    it = iter(program)

    for token in it:
        if not isinstance(token, str):
            stack.append(token)
            continue

        if token == "blend":
            assert getNumRegions is not None
            numSourceFonts = 1 + getNumRegions(vsIndex)
            # replace the blend op args on the stack with a single list
            # containing all the blend op args.
            numBlends = stack[-1]
            numBlendArgs = numBlends * numSourceFonts + 1
            # replace first blend op by a list of the blend ops.
            stack[-numBlendArgs:] = [stack[-numBlendArgs:]]
            lenStack = len(stack)
            lenBlendStack += numBlends + lenStack - 1
            lastBlendIndex = lenStack
            # if a blend op exists, this is or will be a CFF2 charstring.
            continue

        elif token == "vsindex":
            vsIndex = stack[-1]
            assert type(vsIndex) is int

        elif (not seenWidthOp) and token in {
            "hstem",
            "hstemhm",
            "vstem",
            "vstemhm",
            "cntrmask",
            "hintmask",
            "hmoveto",
            "vmoveto",
            "rmoveto",
            "endchar",
        }:
            seenWidthOp = True
            parity = token in {"hmoveto", "vmoveto"}
            if lenBlendStack:
                # lenBlendStack has the number of args represented by the last blend
                # arg and all the preceding args. We need to now add the number of
                # args following the last blend arg.
                numArgs = lenBlendStack + len(stack[lastBlendIndex:])
            else:
                numArgs = len(stack)
            if numArgs and (numArgs % 2) ^ parity:
                width = stack.pop(0)
                commands.append(("", [width]))

        if token in {"hintmask", "cntrmask"}:
            if stack:
                commands.append(("", stack))
            commands.append((token, []))
            commands.append(("", [next(it)]))
        else:
            commands.append((token, stack))
        stack = []
    if stack:
        commands.append(("", stack))
    return commands


def _flattenBlendArgs(args):
    token_list = []
    for arg in args:
        if isinstance(arg, list):
            token_list.extend(arg)
            token_list.append("blend")
        else:
            token_list.append(arg)
    return token_list


def commandsToProgram(commands):
    """Takes a commands list as returned by programToCommands() and converts
    it back to a T2CharString program list."""
    program = []
    for op, args in commands:
        if any(isinstance(arg, list) for arg in args):
            args = _flattenBlendArgs(args)
        program.extend(args)
        if op:
            program.append(op)
    return program


def _everyN(el, n):
    """Group the list el into groups of size n"""
    l = len(el)
    if l % n != 0:
        raise ValueError(el)
    for i in range(0, l, n):
        yield el[i : i + n]


class _GeneralizerDecombinerCommandsMap(object):
    @staticmethod
    def rmoveto(args):
        if len(args) != 2:
            raise ValueError(args)
        yield ("rmoveto", args)

    @staticmethod
    def hmoveto(args):
        if len(args) != 1:
            raise ValueError(args)
        yield ("rmoveto", [args[0], 0])

    @staticmethod
    def vmoveto(args):
        if len(args) != 1:
            raise ValueError(args)
        yield ("rmoveto", [0, args[0]])

    @staticmethod
    def rlineto(args):
        if not args:
            raise ValueError(args)
        for args in _everyN(args, 2):
            yield ("rlineto", args)

    @staticmethod
    def hlineto(args):
        if not args:
            raise ValueError(args)
        it = iter(args)
        try:
            while True:
                yield ("rlineto", [next(it), 0])
                yield ("rlineto", [0, next(it)])
        except StopIteration:
            pass

    @staticmethod
    def vlineto(args):
        if not args:
            raise ValueError(args)
        it = iter(args)
        try:
            while True:
                yield ("rlineto", [0, next(it)])
                yield ("rlineto", [next(it), 0])
        except StopIteration:
            pass

    @staticmethod
    def rrcurveto(args):
        if not args:
            raise ValueError(args)
        for args in _everyN(args, 6):
            yield ("rrcurveto", args)

    @staticmethod
    def hhcurveto(args):
        l = len(args)
        if l < 4 or l % 4 > 1:
            raise ValueError(args)
        if l % 2 == 1:
            yield ("rrcurveto", [args[1], args[0], args[2], args[3], args[4], 0])
            args = args[5:]
        for args in _everyN(args, 4):
            yield ("rrcurveto", [args[0], 0, args[1], args[2], args[3], 0])

    @staticmethod
    def vvcurveto(args):
        l = len(args)
        if l < 4 or l % 4 > 1:
            raise ValueError(args)
        if l % 2 == 1:
            yield ("rrcurveto", [args[0], args[1], args[2], args[3], 0, args[4]])
            args = args[5:]
        for args in _everyN(args, 4):
            yield ("rrcurveto", [0, args[0], args[1], args[2], 0, args[3]])

    @staticmethod
    def hvcurveto(args):
        l = len(args)
        if l < 4 or l % 8 not in {0, 1, 4, 5}:
            raise ValueError(args)
        last_args = None
        if l % 2 == 1:
            lastStraight = l % 8 == 5
            args, last_args = args[:-5], args[-5:]
        it = _everyN(args, 4)
        try:
            while True:
                args = next(it)
                yield ("rrcurveto", [args[0], 0, args[1], args[2], 0, args[3]])
                args = next(it)
                yield ("rrcurveto", [0, args[0], args[1], args[2], args[3], 0])
        except StopIteration:
            pass
        if last_args:
            args = last_args
            if lastStraight:
                yield ("rrcurveto", [args[0], 0, args[1], args[2], args[4], args[3]])
            else:
                yield ("rrcurveto", [0, args[0], args[1], args[2], args[3], args[4]])

    @staticmethod
    def vhcurveto(args):
        l = len(args)
        if l < 4 or l % 8 not in {0, 1, 4, 5}:
            raise ValueError(args)
        last_args = None
        if l % 2 == 1:
            lastStraight = l % 8 == 5
            args, last_args = args[:-5], args[-5:]
        it = _everyN(args, 4)
        try:
            while True:
                args = next(it)
                yield ("rrcurveto", [0, args[0], args[1], args[2], args[3], 0])
                args = next(it)
                yield ("rrcurveto", [args[0], 0, args[1], args[2], 0, args[3]])
        except StopIteration:
            pass
        if last_args:
            args = last_args
            if lastStraight:
                yield ("rrcurveto", [0, args[0], args[1], args[2], args[3], args[4]])
            else:
                yield ("rrcurveto", [args[0], 0, args[1], args[2], args[4], args[3]])

    @staticmethod
    def rcurveline(args):
        l = len(args)
        if l < 8 or l % 6 != 2:
            raise ValueError(args)
        args, last_args = args[:-2], args[-2:]
        for args in _everyN(args, 6):
            yield ("rrcurveto", args)
        yield ("rlineto", last_args)

    @staticmethod
    def rlinecurve(args):
        l = len(args)
        if l < 8 or l % 2 != 0:
            raise ValueError(args)
        args, last_args = args[:-6], args[-6:]
        for args in _everyN(args, 2):
            yield ("rlineto", args)
        yield ("rrcurveto", last_args)


def _convertBlendOpToArgs(blendList):
    # args is list of blend op args. Since we are supporting
    # recursive blend op calls, some of these args may also
    # be a list of blend op args, and need to be converted before
    # we convert the current list.
    if any([isinstance(arg, list) for arg in blendList]):
        args = [
            i
            for e in blendList
            for i in (_convertBlendOpToArgs(e) if isinstance(e, list) else [e])
        ]
    else:
        args = blendList

    # We now know that blendList contains a blend op argument list, even if
    # some of the args are lists that each contain a blend op argument list.
    # 	Convert from:
    # 		[default font arg sequence x0,...,xn] + [delta tuple for x0] + ... + [delta tuple for xn]
    # 	to:
    # 		[ [x0] + [delta tuple for x0],
    #                 ...,
    #          [xn] + [delta tuple for xn] ]
    numBlends = args[-1]
    # Can't use args.pop() when the args are being used in a nested list
    # comprehension. See calling context
    args = args[:-1]

    l = len(args)
    numRegions = l // numBlends - 1
    if not (numBlends * (numRegions + 1) == l):
        raise ValueError(blendList)

    defaultArgs = [[arg] for arg in args[:numBlends]]
    deltaArgs = args[numBlends:]
    numDeltaValues = len(deltaArgs)
    deltaList = [
        deltaArgs[i : i + numRegions] for i in range(0, numDeltaValues, numRegions)
    ]
    blend_args = [a + b + [1] for a, b in zip(defaultArgs, deltaList)]
    return blend_args


def generalizeCommands(commands, ignoreErrors=False):
    result = []
    mapping = _GeneralizerDecombinerCommandsMap
    for op, args in commands:
        # First, generalize any blend args in the arg list.
        if any([isinstance(arg, list) for arg in args]):
            try:
                args = [
                    n
                    for arg in args
                    for n in (
                        _convertBlendOpToArgs(arg) if isinstance(arg, list) else [arg]
                    )
                ]
            except ValueError:
                if ignoreErrors:
                    # Store op as data, such that consumers of commands do not have to
                    # deal with incorrect number of arguments.
                    result.append(("", args))
                    result.append(("", [op]))
                else:
                    raise

        func = getattr(mapping, op, None)
        if func is None:
            result.append((op, args))
            continue
        try:
            for command in func(args):
                result.append(command)
        except ValueError:
            if ignoreErrors:
                # Store op as data, such that consumers of commands do not have to
                # deal with incorrect number of arguments.
                result.append(("", args))
                result.append(("", [op]))
            else:
                raise
    return result


def generalizeProgram(program, getNumRegions=None, **kwargs):
    return commandsToProgram(
        generalizeCommands(programToCommands(program, getNumRegions), **kwargs)
    )


def _categorizeVector(v):
    """
    Takes X,Y vector v and returns one of r, h, v, or 0 depending on which
    of X and/or Y are zero, plus tuple of nonzero ones.  If both are zero,
    it returns a single zero still.

    >>> _categorizeVector((0,0))
    ('0', (0,))
    >>> _categorizeVector((1,0))
    ('h', (1,))
    >>> _categorizeVector((0,2))
    ('v', (2,))
    >>> _categorizeVector((1,2))
    ('r', (1, 2))
    """
    if not v[0]:
        if not v[1]:
            return "0", v[:1]
        else:
            return "v", v[1:]
    else:
        if not v[1]:
            return "h", v[:1]
        else:
            return "r", v


def _mergeCategories(a, b):
    if a == "0":
        return b
    if b == "0":
        return a
    if a == b:
        return a
    return None


def _negateCategory(a):
    if a == "h":
        return "v"
    if a == "v":
        return "h"
    assert a in "0r"
    return a


def _convertToBlendCmds(args):
    # return a list of blend commands, and
    # the remaining non-blended args, if any.
    num_args = len(args)
    stack_use = 0
    new_args = []
    i = 0
    while i < num_args:
        arg = args[i]
        i += 1
        if not isinstance(arg, list):
            new_args.append(arg)
            stack_use += 1
        else:
            prev_stack_use = stack_use
            # The arg is a tuple of blend values.
            # These are each (master 0,delta 1..delta n, 1)
            # Combine as many successive tuples as we can,
            # up to the max stack limit.
            num_sources = len(arg) - 1
            blendlist = [arg]
            stack_use += 1 + num_sources  # 1 for the num_blends arg

            # if we are here, max stack is the CFF2 max stack.
            # I use the CFF2 max stack limit here rather than
            # the 'maxstack' chosen by the client, as the default
            # maxstack may have been used unintentionally. For all
            # the other operators, this just produces a little less
            # optimization, but here it puts a hard (and low) limit
            # on the number of source fonts that can be used.
            #
            # Make sure the stack depth does not exceed (maxstack - 1), so
            # that subroutinizer can insert subroutine calls at any point.
            while (
                (i < num_args)
                and isinstance(args[i], list)
                and stack_use + num_sources < maxStackLimit
            ):
                blendlist.append(args[i])
                i += 1
                stack_use += num_sources
            # blendList now contains as many single blend tuples as can be
            # combined without exceeding the CFF2 stack limit.
            num_blends = len(blendlist)
            # append the 'num_blends' default font values
            blend_args = []
            for arg in blendlist:
                blend_args.append(arg[0])
            for arg in blendlist:
                assert arg[-1] == 1
                blend_args.extend(arg[1:-1])
            blend_args.append(num_blends)
            new_args.append(blend_args)
            stack_use = prev_stack_use + num_blends

    return new_args


def _addArgs(a, b):
    if isinstance(b, list):
        if isinstance(a, list):
            if len(a) != len(b) or a[-1] != b[-1]:
                raise ValueError()
            return [_addArgs(va, vb) for va, vb in zip(a[:-1], b[:-1])] + [a[-1]]
        else:
            a, b = b, a
    if isinstance(a, list):
        assert a[-1] == 1
        return [_addArgs(a[0], b)] + a[1:]
    return a + b


def _argsStackUse(args):
    stackLen = 0
    maxLen = 0
    for arg in args:
        if type(arg) is list:
            # Blended arg
            maxLen = max(maxLen, stackLen + _argsStackUse(arg))
            stackLen += arg[-1]
        else:
            stackLen += 1
    return max(stackLen, maxLen)


def specializeCommands(
    commands,
    ignoreErrors=False,
    generalizeFirst=True,
    preserveTopology=False,
    maxstack=48,
):
    # We perform several rounds of optimizations.  They are carefully ordered and are:
    #
    # 0. Generalize commands.
    #    This ensures that they are in our expected simple form, with each line/curve only
    #    having arguments for one segment, and using the generic form (rlineto/rrcurveto).
    #    If caller is sure the input is in this form, they can turn off generalization to
    #    save time.
    #
    # 1. Combine successive rmoveto operations.
    #
    # 2. Specialize rmoveto/rlineto/rrcurveto operators into horizontal/vertical variants.
    #    We specialize into some, made-up, variants as well, which simplifies following
    #    passes.
    #
    # 3. Merge or delete redundant operations, to the extent requested.
    #    OpenType spec declares point numbers in CFF undefined.  As such, we happily
    #    change topology.  If client relies on point numbers (in GPOS anchors, or for
    #    hinting purposes(what?)) they can turn this off.
    #
    # 4. Peephole optimization to revert back some of the h/v variants back into their
    #    original "relative" operator (rline/rrcurveto) if that saves a byte.
    #
    # 5. Combine adjacent operators when possible, minding not to go over max stack size.
    #
    # 6. Resolve any remaining made-up operators into real operators.
    #
    # I have convinced myself that this produces optimal bytecode (except for, possibly
    # one byte each time maxstack size prohibits combining.)  YMMV, but you'd be wrong. :-)
    # A dynamic-programming approach can do the same but would be significantly slower.
    #
    # 7. For any args which are blend lists, convert them to a blend command.

    # 0. Generalize commands.
    if generalizeFirst:
        commands = generalizeCommands(commands, ignoreErrors=ignoreErrors)
    else:
        commands = list(commands)  # Make copy since we modify in-place later.

    # 1. Combine successive rmoveto operations.
    for i in range(len(commands) - 1, 0, -1):
        if "rmoveto" == commands[i][0] == commands[i - 1][0]:
            v1, v2 = commands[i - 1][1], commands[i][1]
            commands[i - 1] = (
                "rmoveto",
                [_addArgs(v1[0], v2[0]), _addArgs(v1[1], v2[1])],
            )
            del commands[i]

    # 2. Specialize rmoveto/rlineto/rrcurveto operators into horizontal/vertical variants.
    #
    # We, in fact, specialize into more, made-up, variants that special-case when both
    # X and Y components are zero.  This simplifies the following optimization passes.
    # This case is rare, but OCD does not let me skip it.
    #
    # After this round, we will have four variants that use the following mnemonics:
    #
    #  - 'r' for relative,   ie. non-zero X and non-zero Y,
    #  - 'h' for horizontal, ie. zero X and non-zero Y,
    #  - 'v' for vertical,   ie. non-zero X and zero Y,
    #  - '0' for zeros,      ie. zero X and zero Y.
    #
    # The '0' pseudo-operators are not part of the spec, but help simplify the following
    # optimization rounds.  We resolve them at the end.  So, after this, we will have four
    # moveto and four lineto variants:
    #
    #  - 0moveto, 0lineto
    #  - hmoveto, hlineto
    #  - vmoveto, vlineto
    #  - rmoveto, rlineto
    #
    # and sixteen curveto variants.  For example, a '0hcurveto' operator means a curve
    # dx0,dy0,dx1,dy1,dx2,dy2,dx3,dy3 where dx0, dx1, and dy3 are zero but not dx3.
    # An 'rvcurveto' means dx3 is zero but not dx0,dy0,dy3.
    #
    # There are nine different variants of curves without the '0'.  Those nine map exactly
    # to the existing curve variants in the spec: rrcurveto, and the four variants hhcurveto,
    # vvcurveto, hvcurveto, and vhcurveto each cover two cases, one with an odd number of
    # arguments and one without.  Eg. an hhcurveto with an extra argument (odd number of
    # arguments) is in fact an rhcurveto.  The operators in the spec are designed such that
    # all four of rhcurveto, rvcurveto, hrcurveto, and vrcurveto are encodable for one curve.
    #
    # Of the curve types with '0', the 00curveto is equivalent to a lineto variant.  The rest
    # of the curve types with a 0 need to be encoded as a h or v variant.  Ie. a '0' can be
    # thought of a "don't care" and can be used as either an 'h' or a 'v'.  As such, we always
    # encode a number 0 as argument when we use a '0' variant.  Later on, we can just substitute
    # the '0' with either 'h' or 'v' and it works.
    #
    # When we get to curve splines however, things become more complicated...  XXX finish this.
    # There's one more complexity with splines.  If one side of the spline is not horizontal or
    # vertical (or zero), ie. if it's 'r', then it limits which spline types we can encode.
    # Only hhcurveto and vvcurveto operators can encode a spline starting with 'r', and
    # only hvcurveto and vhcurveto operators can encode a spline ending with 'r'.
    # This limits our merge opportunities later.
    #
    for i in range(len(commands)):
        op, args = commands[i]

        if op in {"rmoveto", "rlineto"}:
            c, args = _categorizeVector(args)
            commands[i] = c + op[1:], args
            continue

        if op == "rrcurveto":
            c1, args1 = _categorizeVector(args[:2])
            c2, args2 = _categorizeVector(args[-2:])
            commands[i] = c1 + c2 + "curveto", args1 + args[2:4] + args2
            continue

    # 3. Merge or delete redundant operations, to the extent requested.
    #
    # TODO
    # A 0moveto that comes before all other path operations can be removed.
    # though I find conflicting evidence for this.
    #
    # TODO
    # "If hstem and vstem hints are both declared at the beginning of a
    # CharString, and this sequence is followed directly by the hintmask or
    # cntrmask operators, then the vstem hint operator (or, if applicable,
    # the vstemhm operator) need not be included."
    #
    # "The sequence and form of a CFF2 CharString program may be represented as:
    # {hs* vs* cm* hm* mt subpath}? {mt subpath}*"
    #
    # https://www.microsoft.com/typography/otspec/cff2charstr.htm#section3.1
    #
    # For Type2 CharStrings the sequence is:
    # w? {hs* vs* cm* hm* mt subpath}? {mt subpath}* endchar"

    # Some other redundancies change topology (point numbers).
    if not preserveTopology:
        for i in range(len(commands) - 1, -1, -1):
            op, args = commands[i]

            # A 00curveto is demoted to a (specialized) lineto.
            if op == "00curveto":
                assert len(args) == 4
                c, args = _categorizeVector(args[1:3])
                op = c + "lineto"
                commands[i] = op, args
                # and then...

            # A 0lineto can be deleted.
            if op == "0lineto":
                del commands[i]
                continue

            # Merge adjacent hlineto's and vlineto's.
            # In CFF2 charstrings from variable fonts, each
            # arg item may be a list of blendable values, one from
            # each source font.
            if i and op in {"hlineto", "vlineto"} and (op == commands[i - 1][0]):
                _, other_args = commands[i - 1]
                assert len(args) == 1 and len(other_args) == 1
                try:
                    new_args = [_addArgs(args[0], other_args[0])]
                except ValueError:
                    continue
                commands[i - 1] = (op, new_args)
                del commands[i]
                continue

    # 4. Peephole optimization to revert back some of the h/v variants back into their
    #    original "relative" operator (rline/rrcurveto) if that saves a byte.
    for i in range(1, len(commands) - 1):
        op, args = commands[i]
        prv, nxt = commands[i - 1][0], commands[i + 1][0]

        if op in {"0lineto", "hlineto", "vlineto"} and prv == nxt == "rlineto":
            assert len(args) == 1
            args = [0, args[0]] if op[0] == "v" else [args[0], 0]
            commands[i] = ("rlineto", args)
            continue

        if op[2:] == "curveto" and len(args) == 5 and prv == nxt == "rrcurveto":
            assert (op[0] == "r") ^ (op[1] == "r")
            if op[0] == "v":
                pos = 0
            elif op[0] != "r":
                pos = 1
            elif op[1] == "v":
                pos = 4
            else:
                pos = 5
            # Insert, while maintaining the type of args (can be tuple or list).
            args = args[:pos] + type(args)((0,)) + args[pos:]
            commands[i] = ("rrcurveto", args)
            continue

    # 5. Combine adjacent operators when possible, minding not to go over max stack size.
    stackUse = _argsStackUse(commands[-1][1]) if commands else 0
    for i in range(len(commands) - 1, 0, -1):
        op1, args1 = commands[i - 1]
        op2, args2 = commands[i]
        new_op = None

        # Merge logic...
        if {op1, op2} <= {"rlineto", "rrcurveto"}:
            if op1 == op2:
                new_op = op1
            else:
                l = len(args2)
                if op2 == "rrcurveto" and l == 6:
                    new_op = "rlinecurve"
                elif l == 2:
                    new_op = "rcurveline"

        elif (op1, op2) in {("rlineto", "rlinecurve"), ("rrcurveto", "rcurveline")}:
            new_op = op2

        elif {op1, op2} == {"vlineto", "hlineto"}:
            new_op = op1

        elif "curveto" == op1[2:] == op2[2:]:
            d0, d1 = op1[:2]
            d2, d3 = op2[:2]

            if d1 == "r" or d2 == "r" or d0 == d3 == "r":
                continue

            d = _mergeCategories(d1, d2)
            if d is None:
                continue
            if d0 == "r":
                d = _mergeCategories(d, d3)
                if d is None:
                    continue
                new_op = "r" + d + "curveto"
            elif d3 == "r":
                d0 = _mergeCategories(d0, _negateCategory(d))
                if d0 is None:
                    continue
                new_op = d0 + "r" + "curveto"
            else:
                d0 = _mergeCategories(d0, d3)
                if d0 is None:
                    continue
                new_op = d0 + d + "curveto"

        # Make sure the stack depth does not exceed (maxstack - 1), so
        # that subroutinizer can insert subroutine calls at any point.
        args1StackUse = _argsStackUse(args1)
        combinedStackUse = max(args1StackUse, len(args1) + stackUse)
        if new_op and combinedStackUse < maxstack:
            commands[i - 1] = (new_op, args1 + args2)
            del commands[i]
            stackUse = combinedStackUse
        else:
            stackUse = args1StackUse

    # 6. Resolve any remaining made-up operators into real operators.
    for i in range(len(commands)):
        op, args = commands[i]

        if op in {"0moveto", "0lineto"}:
            commands[i] = "h" + op[1:], args
            continue

        if op[2:] == "curveto" and op[:2] not in {"rr", "hh", "vv", "vh", "hv"}:
            l = len(args)

            op0, op1 = op[:2]
            if (op0 == "r") ^ (op1 == "r"):
                assert l % 2 == 1
            if op0 == "0":
                op0 = "h"
            if op1 == "0":
                op1 = "h"
            if op0 == "r":
                op0 = op1
            if op1 == "r":
                op1 = _negateCategory(op0)
            assert {op0, op1} <= {"h", "v"}, (op0, op1)

            if l % 2:
                if op0 != op1:  # vhcurveto / hvcurveto
                    if (op0 == "h") ^ (l % 8 == 1):
                        # Swap last two args order
                        args = args[:-2] + args[-1:] + args[-2:-1]
                else:  # hhcurveto / vvcurveto
                    if op0 == "h":  # hhcurveto
                        # Swap first two args order
                        args = args[1:2] + args[:1] + args[2:]

            commands[i] = op0 + op1 + "curveto", args
            continue

    # 7. For any series of args which are blend lists, convert the series to a single blend arg.
    for i in range(len(commands)):
        op, args = commands[i]
        if any(isinstance(arg, list) for arg in args):
            commands[i] = op, _convertToBlendCmds(args)

    return commands


def specializeProgram(program, getNumRegions=None, **kwargs):
    return commandsToProgram(
        specializeCommands(programToCommands(program, getNumRegions), **kwargs)
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        import doctest

        sys.exit(doctest.testmod().failed)

    import argparse

    parser = argparse.ArgumentParser(
        "fonttools cffLib.specializer",
        description="CFF CharString generalizer/specializer",
    )
    parser.add_argument("program", metavar="command", nargs="*", help="Commands.")
    parser.add_argument(
        "--num-regions",
        metavar="NumRegions",
        nargs="*",
        default=None,
        help="Number of variable-font regions for blend opertaions.",
    )
    parser.add_argument(
        "--font",
        metavar="FONTFILE",
        default=None,
        help="CFF2 font to specialize.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=str,
        help="Output font file name.",
    )

    options = parser.parse_args(sys.argv[1:])

    if options.program:
        getNumRegions = (
            None
            if options.num_regions is None
            else lambda vsIndex: int(
                options.num_regions[0 if vsIndex is None else vsIndex]
            )
        )

        program = stringToProgram(options.program)
        print("Program:")
        print(programToString(program))
        commands = programToCommands(program, getNumRegions)
        print("Commands:")
        print(commands)
        program2 = commandsToProgram(commands)
        print("Program from commands:")
        print(programToString(program2))
        assert program == program2
        print("Generalized program:")
        print(programToString(generalizeProgram(program, getNumRegions)))
        print("Specialized program:")
        print(programToString(specializeProgram(program, getNumRegions)))

    if options.font:
        from fontTools.ttLib import TTFont

        font = TTFont(options.font)
        cff2 = font["CFF2"].cff.topDictIndex[0]
        charstrings = cff2.CharStrings
        for glyphName in charstrings.keys():
            charstring = charstrings[glyphName]
            charstring.decompile()
            getNumRegions = charstring.private.getNumRegions
            charstring.program = specializeProgram(
                charstring.program, getNumRegions, maxstack=maxStackLimit
            )

        if options.output_file is None:
            from fontTools.misc.cliTools import makeOutputFileName

            outfile = makeOutputFileName(
                options.font, overWrite=True, suffix=".specialized"
            )
        else:
            outfile = options.output_file
        if outfile:
            print("Saving", outfile)
            font.save(outfile)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\health_endpoints\_health_endpoints.py ===
import asyncio
import copy
import os
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Literal, Optional, Union

import fastapi
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.constants import HEALTH_CHECK_TIMEOUT_SECONDS
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler
from litellm.proxy._types import (
    AlertType,
    CallInfo,
    Litellm_EntityType,
    ProxyErrorTypes,
    ProxyException,
    UserAPIKeyAuth,
    WebhookEvent,
)
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.db.exception_handler import PrismaDBExceptionHandler
from litellm.proxy.health_check import (
    _clean_endpoint_data,
    _update_litellm_params_for_health_check,
    perform_health_check,
    run_with_timeout,
)

#### Health ENDPOINTS ####

router = APIRouter()


@router.get(
    "/test",
    tags=["health"],
    dependencies=[Depends(user_api_key_auth)],
)
async def test_endpoint(request: Request):
    """
    [DEPRECATED] use `/health/liveliness` instead.

    A test endpoint that pings the proxy server to check if it's healthy.

    Parameters:
        request (Request): The incoming request.

    Returns:
        dict: A dictionary containing the route of the request URL.
    """
    # ping the proxy server to check if its healthy
    return {"route": request.url.path}


@router.get(
    "/health/services",
    tags=["health"],
    dependencies=[Depends(user_api_key_auth)],
)
async def health_services_endpoint(  # noqa: PLR0915
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    service: Union[
        Literal[
            "slack_budget_alerts",
            "langfuse",
            "slack",
            "openmeter",
            "webhook",
            "email",
            "braintrust",
            "datadog",
            "generic_api",
        ],
        str,
    ] = fastapi.Query(description="Specify the service being hit."),
):
    """
    Use this admin-only endpoint to check if the service is healthy.

    Example:
    ```
    curl -L -X GET 'http://0.0.0.0:4000/health/services?service=datadog' \
    -H 'Authorization: Bearer sk-1234'
    ```
    """
    try:
        from litellm.proxy.proxy_server import (
            general_settings,
            prisma_client,
            proxy_logging_obj,
        )

        if service is None:
            raise HTTPException(
                status_code=400, detail={"error": "Service must be specified."}
            )

        if service not in [
            "slack_budget_alerts",
            "email",
            "langfuse",
            "slack",
            "openmeter",
            "webhook",
            "braintrust",
            "otel",
            "custom_callback_api",
            "langsmith",
            "datadog",
            "generic_api",
        ]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Service must be in list. Service={service}. List={['slack_budget_alerts']}"
                },
            )

        if (
            service == "openmeter"
            or service == "braintrust"
            or service == "generic_api"
            or (service in litellm.success_callback and service != "langfuse")
        ):
            _ = await litellm.acompletion(
                model="openai/litellm-mock-response-model",
                messages=[{"role": "user", "content": "Hey, how's it going?"}],
                user="litellm:/health/services",
                mock_response="This is a mock response",
            )
            return {
                "status": "success",
                "message": "Mock LLM request made - check {}.".format(service),
            }
        elif service == "datadog":
            from litellm.integrations.datadog.datadog import DataDogLogger

            datadog_logger = DataDogLogger()
            response = await datadog_logger.async_health_check()
            return {
                "status": response["status"],
                "message": (
                    response["error_message"]
                    if response["status"] == "unhealthy"
                    else "Datadog is healthy"
                ),
            }
        elif service == "langfuse":
            from litellm.integrations.langfuse.langfuse import LangFuseLogger

            langfuse_logger = LangFuseLogger()
            langfuse_logger.Langfuse.auth_check()
            _ = litellm.completion(
                model="openai/litellm-mock-response-model",
                messages=[{"role": "user", "content": "Hey, how's it going?"}],
                user="litellm:/health/services",
                mock_response="This is a mock response",
            )
            return {
                "status": "success",
                "message": "Mock LLM request made - check langfuse.",
            }

        if service == "webhook":
            user_info = CallInfo(
                token=user_api_key_dict.token or "",
                spend=1,
                max_budget=0,
                user_id=user_api_key_dict.user_id,
                key_alias=user_api_key_dict.key_alias,
                team_id=user_api_key_dict.team_id,
                event_group=Litellm_EntityType.KEY,
            )
            await proxy_logging_obj.budget_alerts(
                type="user_budget",
                user_info=user_info,
            )

        if service == "slack" or service == "slack_budget_alerts":
            if "slack" in general_settings.get("alerting", []):
                # test_message = f"""\n🚨 `ProjectedLimitExceededError` 💸\n\n`Key Alias:` litellm-ui-test-alert \n`Expected Day of Error`: 28th March \n`Current Spend`: $100.00 \n`Projected Spend at end of month`: $1000.00 \n`Soft Limit`: $700"""
                # check if user has opted into unique_alert_webhooks
                if (
                    proxy_logging_obj.slack_alerting_instance.alert_to_webhook_url
                    is not None
                ):
                    for (
                        alert_type
                    ) in proxy_logging_obj.slack_alerting_instance.alert_to_webhook_url:
                        # only test alert if it's in active alert types
                        if (
                            proxy_logging_obj.slack_alerting_instance.alert_types
                            is not None
                            and alert_type
                            not in proxy_logging_obj.slack_alerting_instance.alert_types
                        ):
                            continue

                        test_message = "default test message"
                        if alert_type == AlertType.llm_exceptions:
                            test_message = "LLM Exception test alert"
                        elif alert_type == AlertType.llm_too_slow:
                            test_message = "LLM Too Slow test alert"
                        elif alert_type == AlertType.llm_requests_hanging:
                            test_message = "LLM Requests Hanging test alert"
                        elif alert_type == AlertType.budget_alerts:
                            test_message = "Budget Alert test alert"
                        elif alert_type == AlertType.db_exceptions:
                            test_message = "DB Exception test alert"
                        elif alert_type == AlertType.outage_alerts:
                            test_message = "Outage Alert Exception test alert"
                        elif alert_type == AlertType.daily_reports:
                            test_message = "Daily Reports test alert"
                        else:
                            test_message = "Budget Alert test alert"

                        await proxy_logging_obj.alerting_handler(
                            message=test_message, level="Low", alert_type=alert_type
                        )
                else:
                    await proxy_logging_obj.alerting_handler(
                        message="This is a test slack alert message",
                        level="Low",
                        alert_type=AlertType.budget_alerts,
                    )

                if prisma_client is not None:
                    asyncio.create_task(
                        proxy_logging_obj.slack_alerting_instance.send_monthly_spend_report()
                    )
                    asyncio.create_task(
                        proxy_logging_obj.slack_alerting_instance.send_weekly_spend_report()
                    )

                alert_types = (
                    proxy_logging_obj.slack_alerting_instance.alert_types or []
                )
                alert_types = list(alert_types)
                return {
                    "status": "success",
                    "alert_types": alert_types,
                    "message": "Mock Slack Alert sent, verify Slack Alert Received on your channel",
                }
            else:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": '"{}" not in proxy config: general_settings. Unable to test this.'.format(
                            service
                        )
                    },
                )
        if service == "email":
            webhook_event = WebhookEvent(
                event="key_created",
                event_group=Litellm_EntityType.KEY,
                event_message="Test Email Alert",
                token=user_api_key_dict.token or "",
                key_alias="Email Test key (This is only a test alert key. DO NOT USE THIS IN PRODUCTION.)",
                spend=0,
                max_budget=0,
                user_id=user_api_key_dict.user_id,
                user_email=os.getenv("TEST_EMAIL_ADDRESS"),
                team_id=user_api_key_dict.team_id,
            )

            # use create task - this can take 10 seconds. don't keep ui users waiting for notification to check their email
            await proxy_logging_obj.slack_alerting_instance.send_key_created_or_user_invited_email(
                webhook_event=webhook_event
            )

            return {
                "status": "success",
                "message": "Mock Email Alert sent, verify Email Alert Received",
            }

    except Exception as e:
        verbose_proxy_logger.error(
            "litellm.proxy.proxy_server.health_services_endpoint(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Authentication Error({str(e)})"),
                type=ProxyErrorTypes.auth_error,
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Authentication Error, " + str(e),
            type=ProxyErrorTypes.auth_error,
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _convert_health_check_to_dict(check) -> dict:
    """Convert health check database record to dictionary format"""
    return {
        "health_check_id": check.health_check_id,
        "model_name": check.model_name,
        "model_id": check.model_id,
        "status": check.status,
        "healthy_count": check.healthy_count,
        "unhealthy_count": check.unhealthy_count,
        "error_message": check.error_message,
        "response_time_ms": check.response_time_ms,
        "details": check.details,
        "checked_by": check.checked_by,
        "checked_at": check.checked_at.isoformat() if check.checked_at else None,
        "created_at": check.created_at.isoformat() if check.created_at else None,
    }


def _check_prisma_client():
    """Helper to check if prisma_client is available and raise appropriate error"""
    from litellm.proxy.proxy_server import prisma_client
    
    if prisma_client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Database not initialized"},
        )
    return prisma_client


async def _save_health_check_to_db(
    prisma_client, 
    model_name: str, 
    healthy_endpoints: list, 
    unhealthy_endpoints: list, 
    start_time: float, 
    user_id: Optional[str],
    model_id: Optional[str] = None
):
    """Helper function to save health check results to database"""
    try:
        # Extract error message from first unhealthy endpoint if available
        error_message = (
            str(unhealthy_endpoints[0]["error"])[:500] 
            if unhealthy_endpoints and unhealthy_endpoints[0].get("error") 
            else None
        )
        
        await prisma_client.save_health_check_result(
            model_name=model_name,
            model_id=model_id,
            status="healthy" if healthy_endpoints else "unhealthy",
            healthy_count=len(healthy_endpoints),
            unhealthy_count=len(unhealthy_endpoints),
            error_message=error_message,
            response_time_ms=(time.time() - start_time) * 1000,
            details=None,  # Skip details for now to avoid JSON serialization issues
            checked_by=user_id,
        )
    except Exception as db_error:
        verbose_proxy_logger.warning(f"Failed to save health check to database for model {model_name}: {db_error}")
        # Continue execution - don't let database save failure break health checks


async def _perform_health_check_and_save(
    model_list,
    target_model,
    cli_model,
    details,
    prisma_client,
    start_time,
    user_id,
    model_id=None
):
    """Helper function to perform health check and save results to database"""
    healthy_endpoints, unhealthy_endpoints = await perform_health_check(
        model_list=model_list, 
        cli_model=cli_model, 
        model=target_model,
        details=details
    )
    
    # Optionally save health check result to database (non-blocking)
    if prisma_client is not None:
        # For CLI model, use cli_model name; for router models, use target_model
        model_name_for_db = cli_model if cli_model is not None else target_model
        if model_name_for_db is not None:
            asyncio.create_task(_save_health_check_to_db(
                prisma_client,
                model_name_for_db,
                healthy_endpoints,
                unhealthy_endpoints,
                start_time,
                user_id,
                model_id=model_id
            ))
    
    return {
        "healthy_endpoints": healthy_endpoints,
        "unhealthy_endpoints": unhealthy_endpoints,
        "healthy_count": len(healthy_endpoints),
        "unhealthy_count": len(unhealthy_endpoints),
    }


@router.get("/health", tags=["health"], dependencies=[Depends(user_api_key_auth)])
async def health_endpoint(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    model: Optional[str] = fastapi.Query(
        None, description="Specify the model name (optional)"
    ),
    model_id: Optional[str] = fastapi.Query(
        None, description="Specify the model ID (optional)"
    ),
):
    """
    🚨 USE `/health/liveliness` to health check the proxy 🚨

    See more 👉 https://docs.litellm.ai/docs/proxy/health


    Check the health of all the endpoints in config.yaml

    To run health checks in the background, add this to config.yaml:
    ```
    general_settings:
        # ... other settings
        background_health_checks: True
    ```
    else, the health checks will be run on models when /health is called.
    """
    from litellm.proxy.proxy_server import (
        health_check_details,
        health_check_results,
        llm_model_list,
        llm_router,
        use_background_health_checks,
        user_model,
        prisma_client,
    )
    import time

    start_time = time.time()
    
    # Handle model_id parameter - convert to model name for health check
    target_model = model
    if model_id and not model:
        # Use get_deployment from router to find the model name
        if llm_router is not None:
            try:
                deployment = llm_router.get_deployment(model_id=model_id)
                if deployment is not None:
                    target_model = deployment.model_name
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail={"error": f"Model with ID {model_id} not found"},
                    )
            except Exception as e:
                verbose_proxy_logger.error(f"Error getting deployment for model_id {model_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error": f"Model with ID {model_id} not found"},
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": f"Model with ID {model_id} not found"},
            )
    
    try:
        if llm_model_list is None:
            # if no router set, check if user set a model using litellm --model ollama/llama2
            if user_model is not None:
                return await _perform_health_check_and_save(
                    model_list=[],
                    target_model=None,
                    cli_model=user_model,
                    details=health_check_details,
                    prisma_client=prisma_client,
                    start_time=start_time,
                    user_id=user_api_key_dict.user_id,
                    model_id=None  # CLI model doesn't have model_id
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "Model list not initialized"},
            )
        _llm_model_list = copy.deepcopy(llm_model_list)
        ### FILTER MODELS FOR ONLY THOSE USER HAS ACCESS TO ###
        if len(user_api_key_dict.models) > 0:
            pass
        else:
            pass  #
        if use_background_health_checks:
            return health_check_results
        else:
            return await _perform_health_check_and_save(
                model_list=_llm_model_list,
                target_model=target_model,
                cli_model=None,
                details=health_check_details,
                prisma_client=prisma_client,
                start_time=start_time,
                user_id=user_api_key_dict.user_id,
                model_id=model_id
            )
    except Exception as e:
        verbose_proxy_logger.error(
            "litellm.proxy.proxy_server.py::health_endpoint(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        raise e


@router.get("/health/history", tags=["health"], dependencies=[Depends(user_api_key_auth)])
async def health_check_history_endpoint(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    model: Optional[str] = fastapi.Query(
        None, description="Filter by specific model name"
    ),
    status_filter: Optional[str] = fastapi.Query(
        None, description="Filter by status (healthy/unhealthy)"
    ),
    limit: int = fastapi.Query(
        100, description="Number of records to return", ge=1, le=1000
    ),
    offset: int = fastapi.Query(
        0, description="Number of records to skip", ge=0
    ),
):
    """
    Get health check history for models
    
    Returns historical health check data with optional filtering.
    """
    prisma_client = _check_prisma_client()
    
    try:
        history = await prisma_client.get_health_check_history(
            model_name=model,
            limit=limit,
            offset=offset,
            status_filter=status_filter,
        )
        
        # Convert to dict format for JSON response using helper function
        history_data = [_convert_health_check_to_dict(check) for check in history]
        
        return {
            "health_checks": history_data,
            "total_records": len(history_data),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        verbose_proxy_logger.error(f"Error getting health check history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to retrieve health check history: {str(e)}"},
        )


@router.get("/health/latest", tags=["health"], dependencies=[Depends(user_api_key_auth)])
async def latest_health_checks_endpoint(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get the latest health check status for all models
    
    Returns the most recent health check result for each model.
    """
    prisma_client = _check_prisma_client()
    
    try:
        latest_checks = await prisma_client.get_all_latest_health_checks()
        
        # Convert to dict format for JSON response using helper function
        checks_data = {
            (check.model_id if check.model_id else check.model_name): _convert_health_check_to_dict(check)
            for check in latest_checks
        }
        
        return {
            "latest_health_checks": checks_data,
            "total_models": len(checks_data),
        }
    except Exception as e:
        verbose_proxy_logger.error(f"Error getting latest health checks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to retrieve latest health checks: {str(e)}"},
        )


db_health_cache = {"status": "unknown", "last_updated": datetime.now()}


async def _db_health_readiness_check():
    from litellm.proxy.proxy_server import prisma_client

    global db_health_cache

    # Note - Intentionally don't try/except this so it raises an exception when it fails
    try:
        # if timedelta is less than 2 minutes return DB Status
        time_diff = datetime.now() - db_health_cache["last_updated"]
        if db_health_cache["status"] != "unknown" and time_diff < timedelta(minutes=2):
            return db_health_cache

        if prisma_client is None:
            db_health_cache = {"status": "disconnected", "last_updated": datetime.now()}
            return db_health_cache

        await prisma_client.health_check()
        db_health_cache = {"status": "connected", "last_updated": datetime.now()}
        return db_health_cache
    except Exception as e:
        PrismaDBExceptionHandler.handle_db_exception(e)
        return db_health_cache


@router.get(
    "/settings",
    tags=["health"],
    dependencies=[Depends(user_api_key_auth)],
)
@router.get(
    "/active/callbacks",
    tags=["health"],
    dependencies=[Depends(user_api_key_auth)],
)
async def active_callbacks():
    """
    Returns a list of litellm level settings

    This is useful for debugging and ensuring the proxy server is configured correctly.

    Response schema:
    ```
    {
        "alerting": _alerting,
        "litellm.callbacks": litellm_callbacks,
        "litellm.input_callback": litellm_input_callbacks,
        "litellm.failure_callback": litellm_failure_callbacks,
        "litellm.success_callback": litellm_success_callbacks,
        "litellm._async_success_callback": litellm_async_success_callbacks,
        "litellm._async_failure_callback": litellm_async_failure_callbacks,
        "litellm._async_input_callback": litellm_async_input_callbacks,
        "all_litellm_callbacks": all_litellm_callbacks,
        "num_callbacks": len(all_litellm_callbacks),
        "num_alerting": _num_alerting,
        "litellm.request_timeout": litellm.request_timeout,
    }
    ```
    """

    from litellm.proxy.proxy_server import general_settings, proxy_logging_obj

    _alerting = str(general_settings.get("alerting"))
    # get success callbacks

    litellm_callbacks = [str(x) for x in litellm.callbacks]
    litellm_input_callbacks = [str(x) for x in litellm.input_callback]
    litellm_failure_callbacks = [str(x) for x in litellm.failure_callback]
    litellm_success_callbacks = [str(x) for x in litellm.success_callback]
    litellm_async_success_callbacks = [str(x) for x in litellm._async_success_callback]
    litellm_async_failure_callbacks = [str(x) for x in litellm._async_failure_callback]
    litellm_async_input_callbacks = [str(x) for x in litellm._async_input_callback]

    all_litellm_callbacks = (
        litellm_callbacks
        + litellm_input_callbacks
        + litellm_failure_callbacks
        + litellm_success_callbacks
        + litellm_async_success_callbacks
        + litellm_async_failure_callbacks
        + litellm_async_input_callbacks
    )

    alerting = proxy_logging_obj.alerting
    _num_alerting = 0
    if alerting and isinstance(alerting, list):
        _num_alerting = len(alerting)

    return {
        "alerting": _alerting,
        "litellm.callbacks": litellm_callbacks,
        "litellm.input_callback": litellm_input_callbacks,
        "litellm.failure_callback": litellm_failure_callbacks,
        "litellm.success_callback": litellm_success_callbacks,
        "litellm._async_success_callback": litellm_async_success_callbacks,
        "litellm._async_failure_callback": litellm_async_failure_callbacks,
        "litellm._async_input_callback": litellm_async_input_callbacks,
        "all_litellm_callbacks": all_litellm_callbacks,
        "num_callbacks": len(all_litellm_callbacks),
        "num_alerting": _num_alerting,
        "litellm.request_timeout": litellm.request_timeout,
    }


def callback_name(callback):
    if isinstance(callback, str):
        return callback

    try:
        return callback.__name__
    except AttributeError:
        try:
            return callback.__class__.__name__
        except AttributeError:
            return str(callback)


@router.get(
    "/health/readiness",
    tags=["health"],
    dependencies=[Depends(user_api_key_auth)],
)
async def health_readiness():
    """
    Unprotected endpoint for checking if worker can receive requests
    """
    from litellm.proxy.proxy_server import prisma_client, version

    try:
        # get success callback
        success_callback_names = []

        try:
            # this was returning a JSON of the values in some of the callbacks
            # all we need is the callback name, hence we do str(callback)
            success_callback_names = [
                callback_name(x) for x in litellm.success_callback
            ]
        except AttributeError:
            # don't let this block the /health/readiness response, if we can't convert to str -> return litellm.success_callback
            success_callback_names = litellm.success_callback

        # check Cache
        cache_type = None
        if litellm.cache is not None:
            from litellm.caching.caching import RedisSemanticCache

            cache_type = litellm.cache.type

            if isinstance(litellm.cache.cache, RedisSemanticCache):
                # ping the cache
                # TODO: @ishaan-jaff - we should probably not ping the cache on every /health/readiness check
                try:
                    index_info = await litellm.cache.cache._index_info()
                except Exception as e:
                    index_info = "index does not exist - error: " + str(e)
                cache_type = {"type": cache_type, "index_info": index_info}

        # check DB
        if prisma_client is not None:  # if db passed in, check if it's connected
            db_health_status = await _db_health_readiness_check()
            return {
                "status": "healthy",
                "db": "connected",
                "cache": cache_type,
                "litellm_version": version,
                "success_callbacks": success_callback_names,
                "use_aiohttp_transport": AsyncHTTPHandler._should_use_aiohttp_transport(),
                **db_health_status,
            }
        else:
            return {
                "status": "healthy",
                "db": "Not connected",
                "cache": cache_type,
                "litellm_version": version,
                "success_callbacks": success_callback_names,
                "use_aiohttp_transport": AsyncHTTPHandler._should_use_aiohttp_transport(),
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service Unhealthy ({str(e)})")


@router.get(
    "/health/liveliness",  # Historical LiteLLM name; doesn't match k8s terminology but kept for backwards compatibility
    tags=["health"],
)
@router.get(
    "/health/liveness",  # Kubernetes has "liveness" probes (https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/#define-a-liveness-command)
    tags=["health"],
)
async def health_liveliness():
    """
    Unprotected endpoint for checking if worker is alive
    """
    return "I'm alive!"


@router.options(
    "/health/readiness",
    tags=["health"],
    dependencies=[Depends(user_api_key_auth)],
)
async def health_readiness_options():
    """
    Options endpoint for health/readiness check.
    """
    response_headers = {
        "Allow": "GET, OPTIONS",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    return Response(headers=response_headers, status_code=200)


@router.options(
    "/health/liveliness",
    tags=["health"],
)
@router.options(
    "/health/liveness",  # Kubernetes has "liveness" probes (https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/#define-a-liveness-command)
    tags=["health"],
)
async def health_liveliness_options():
    """
    Options endpoint for health/liveliness check.
    """
    response_headers = {
        "Allow": "GET, OPTIONS",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    return Response(headers=response_headers, status_code=200)


@router.post(
    "/health/test_connection",
    tags=["health"],
    dependencies=[Depends(user_api_key_auth)],
)
async def test_model_connection(
    request: Request,
    mode: Optional[
        Literal[
            "chat",
            "completion",
            "embedding",
            "audio_speech",
            "audio_transcription",
            "image_generation",
            "batch",
            "rerank",
            "realtime",
        ]
    ] = fastapi.Body("chat", description="The mode to test the model with"),
    litellm_params: Dict = fastapi.Body(
        None,
        description="Parameters for litellm.completion, litellm.embedding for the health check",
    ),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Test a direct connection to a specific model.
    
    This endpoint allows you to verify if your proxy can successfully connect to a specific model.
    It's useful for troubleshooting model connectivity issues without going through the full proxy routing.
    
    Example:
    ```bash
    curl -X POST 'http://localhost:4000/health/test_connection' \\
      -H 'Authorization: Bearer sk-1234' \\
      -H 'Content-Type: application/json' \\
      -d '{
        "litellm_params": {
            "model": "gpt-4",
            "custom_llm_provider": "azure_ai",
            "litellm_credential_name": null,
            "api_key": "6xxxxxxx",
            "api_base": "https://litellm8397336933.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-10-21",
        },
        "mode": "chat"
      }'
    ```
    
    Returns:
        dict: A dictionary containing the health check result with either success information or error details.
    """
    try:
        # Include health_check_params if provided
        litellm_params = _update_litellm_params_for_health_check(
            model_info={},
            litellm_params=litellm_params,
        )
        mode = mode or litellm_params.pop("mode", None)
        result = await run_with_timeout(
            litellm.ahealth_check(
                model_params=litellm_params,
                mode=mode,
                prompt="test from litellm",
                input=["test from litellm"],
            ),
            HEALTH_CHECK_TIMEOUT_SECONDS,
        )

        # Clean the result for display
        cleaned_result = _clean_endpoint_data(
            {**litellm_params, **result}, details=True
        )

        return {
            "status": "error" if "error" in result else "success",
            "result": cleaned_result,
        }

    except Exception as e:
        verbose_proxy_logger.error(
            f"litellm.proxy.health_endpoints.test_model_connection(): Exception occurred - {str(e)}"
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to test connection: {str(e)}"},
        )

# === NexusCore/openenv\Lib\site-packages\stack_data\core.py ===
import ast
import html
import os
import sys
from collections import defaultdict, Counter
from enum import Enum
from textwrap import dedent
from types import FrameType, CodeType, TracebackType
from typing import (
    Iterator, List, Tuple, Optional, NamedTuple,
    Any, Iterable, Callable, Union,
    Sequence)
from typing import Mapping

import executing
from asttokens.util import Token
from executing import only
from pure_eval import Evaluator, is_expression_interesting
from stack_data.utils import (
    truncate, unique_in_order, line_range,
    frame_and_lineno, iter_stack, collapse_repeated, group_by_key_func,
    cached_property, is_frame, _pygmented_with_ranges, assert_)

RangeInLine = NamedTuple('RangeInLine',
                         [('start', int),
                          ('end', int),
                          ('data', Any)])
RangeInLine.__doc__ = """
Represents a range of characters within one line of source code,
and some associated data.

Typically this will be converted to a pair of markers by markers_from_ranges.
"""

MarkerInLine = NamedTuple('MarkerInLine',
                          [('position', int),
                           ('is_start', bool),
                           ('string', str)])
MarkerInLine.__doc__ = """
A string that is meant to be inserted at a given position in a line of source code.
For example, this could be an ANSI code or the opening or closing of an HTML tag.
is_start should be True if this is the first of a pair such as the opening of an HTML tag.
This will help to sort and insert markers correctly.

Typically this would be created from a RangeInLine by markers_from_ranges.
Then use Line.render to insert the markers correctly.
"""


class BlankLines(Enum):
    """The values are intended to correspond to the following behaviour:
    HIDDEN: blank lines are not shown in the output
    VISIBLE: blank lines are visible in the output
    SINGLE: any consecutive blank lines are shown as a single blank line
            in the output. This option requires the line number to be shown.
            For a single blank line, the corresponding line number is shown.
            Two or more consecutive blank lines are shown as a single blank
            line in the output with a custom string shown instead of a
            specific line number.
    """
    HIDDEN = 1
    VISIBLE = 2
    SINGLE=3

class Variable(
    NamedTuple('_Variable',
               [('name', str),
                ('nodes', Sequence[ast.AST]),
                ('value', Any)])
):
    """
    An expression that appears one or more times in source code and its associated value.
    This will usually be a variable but it can be any expression evaluated by pure_eval.
    - name is the source text of the expression.
    - nodes is a list of equivalent nodes representing the same expression.
    - value is the safely evaluated value of the expression.
    """
    __hash__ = object.__hash__
    __eq__ = object.__eq__


class Source(executing.Source):
    """
    The source code of a single file and associated metadata.

    In addition to the attributes from the base class executing.Source,
    if .tree is not None, meaning this is valid Python code, objects have:
        - pieces: a list of Piece objects
        - tokens_by_lineno: a defaultdict(list) mapping line numbers to lists of tokens.

    Don't construct this class. Get an instance from frame_info.source.
    """

    @cached_property
    def pieces(self) -> List[range]:
        if not self.tree:
            return [
                range(i, i + 1)
                for i in range(1, len(self.lines) + 1)
            ]
        return list(self._clean_pieces())

    @cached_property
    def tokens_by_lineno(self) -> Mapping[int, List[Token]]:
        if not self.tree:
            raise AttributeError("This file doesn't contain valid Python, so .tokens_by_lineno doesn't exist")
        return group_by_key_func(
            self.asttokens().tokens,
            lambda tok: tok.start[0],
        )

    def _clean_pieces(self) -> Iterator[range]:
        pieces = self._raw_split_into_pieces(self.tree, 1, len(self.lines) + 1)
        pieces = [
            (start, end)
            for (start, end) in pieces
            if end > start
        ]

        # Combine overlapping pieces, i.e. consecutive pieces where the end of the first
        # is greater than the start of the second.
        # This can happen when two statements are on the same line separated by a semicolon.
        new_pieces = pieces[:1]
        for (start, end) in pieces[1:]:
            (last_start, last_end) = new_pieces[-1]
            if start < last_end:
                assert start == last_end - 1
                assert ';' in self.lines[start - 1]
                new_pieces[-1] = (last_start, end)
            else:
                new_pieces.append((start, end))
        pieces = new_pieces

        starts = [start for start, end in pieces[1:]]
        ends = [end for start, end in pieces[:-1]]
        if starts != ends:
            joins = list(map(set, zip(starts, ends)))
            mismatches = [s for s in joins if len(s) > 1]
            raise AssertionError("Pieces mismatches: %s" % mismatches)

        def is_blank(i):
            try:
                return not self.lines[i - 1].strip()
            except IndexError:
                return False

        for start, end in pieces:
            while is_blank(start):
                start += 1
            while is_blank(end - 1):
                end -= 1
            if start < end:
                yield range(start, end)

    def _raw_split_into_pieces(
            self,
            stmt: ast.AST,
            start: int,
            end: int,
    ) -> Iterator[Tuple[int, int]]:
        for name, body in ast.iter_fields(stmt):
            if (
                    isinstance(body, list) and body and
                    isinstance(body[0], (ast.stmt, ast.ExceptHandler, getattr(ast, 'match_case', ())))
            ):
                for rang, group in sorted(group_by_key_func(body, self.line_range).items()):
                    sub_stmt = group[0]
                    for inner_start, inner_end in self._raw_split_into_pieces(sub_stmt, *rang):
                        if start < inner_start:
                            yield start, inner_start
                        if inner_start < inner_end:
                            yield inner_start, inner_end
                        start = inner_end

        yield start, end

    def line_range(self, node: ast.AST) -> Tuple[int, int]:
        return line_range(self.asttext(), node)


class Options:
    """
    Configuration for FrameInfo, either in the constructor or the .stack_data classmethod.
    These all determine which Lines and gaps are produced by FrameInfo.lines. 

    before and after are the number of pieces of context to include in a frame
    in addition to the executing piece.

    include_signature is whether to include the function signature as a piece in a frame.

    If a piece (other than the executing piece) has more than max_lines_per_piece lines,
    it will be truncated with a gap in the middle. 
    """
    def __init__(
            self, *,
            before: int = 3,
            after: int = 1,
            include_signature: bool = False,
            max_lines_per_piece: int = 6,
            pygments_formatter=None,
            blank_lines = BlankLines.HIDDEN
    ):
        self.before = before
        self.after = after
        self.include_signature = include_signature
        self.max_lines_per_piece = max_lines_per_piece
        self.pygments_formatter = pygments_formatter
        self.blank_lines = blank_lines

    def __repr__(self):
        keys = sorted(self.__dict__)
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class LineGap(object):
    """
    A singleton representing one or more lines of source code that were skipped
    in FrameInfo.lines.

    LINE_GAP can be created in two ways:
    - by truncating a piece of context that's too long.
    - immediately after the signature piece if Options.include_signature is true
      and the following piece isn't already part of the included pieces. 
    """
    def __repr__(self):
        return "LINE_GAP"


LINE_GAP = LineGap()


class BlankLineRange:
    """
    Records the line number range for blank lines gaps between pieces.
    For a single blank line, begin_lineno == end_lineno.
    """
    def __init__(self, begin_lineno: int, end_lineno: int):
        self.begin_lineno = begin_lineno
        self.end_lineno = end_lineno


class Line(object):
    """
    A single line of source code for a particular stack frame.

    Typically this is obtained from FrameInfo.lines.
    Since that list may also contain LINE_GAP, you should first check
    that this is really a Line before using it.

    Attributes:
        - frame_info
        - lineno: the 1-based line number within the file
        - text: the raw source of this line. For displaying text, see .render() instead.
        - leading_indent: the number of leading spaces that should probably be stripped.
            This attribute is set within FrameInfo.lines. If you construct this class
            directly you should probably set it manually (at least to 0).
        - is_current: whether this is the line currently being executed by the interpreter
            within this frame.
        - tokens: a list of source tokens in this line

    There are several helpers for constructing RangeInLines which can be converted to markers
    using markers_from_ranges which can be passed to .render():
        - token_ranges
        - variable_ranges
        - executing_node_ranges
        - range_from_node
    """
    def __init__(
            self,
            frame_info: 'FrameInfo',
            lineno: int,
    ):
        self.frame_info = frame_info
        self.lineno = lineno
        self.text = frame_info.source.lines[lineno - 1]  # type: str
        self.leading_indent = None  # type: Optional[int]

    def __repr__(self):
        return "<{self.__class__.__name__} {self.lineno} (current={self.is_current}) " \
               "{self.text!r} of {self.frame_info.filename}>".format(self=self)

    @property
    def is_current(self) -> bool:
        """
        Whether this is the line currently being executed by the interpreter
        within this frame.
        """
        return self.lineno == self.frame_info.lineno

    @property
    def tokens(self) -> List[Token]:
        """
        A list of source tokens in this line.
        The tokens are Token objects from asttokens:
        https://asttokens.readthedocs.io/en/latest/api-index.html#asttokens.util.Token
        """
        return self.frame_info.source.tokens_by_lineno[self.lineno]

    @cached_property
    def token_ranges(self) -> List[RangeInLine]:
        """
        A list of RangeInLines for each token in .tokens,
        where range.data is a Token object from asttokens:
        https://asttokens.readthedocs.io/en/latest/api-index.html#asttokens.util.Token
        """
        return [
            RangeInLine(
                token.start[1],
                token.end[1],
                token,
            )
            for token in self.tokens
        ]

    @cached_property
    def variable_ranges(self) -> List[RangeInLine]:
        """
        A list of RangeInLines for each Variable that appears at least partially in this line.
        The data attribute of the range is a pair (variable, node) where node is the particular
        AST node from the list variable.nodes that corresponds to this range.
        """
        return [
            self.range_from_node(node, (variable, node))
            for variable, node in self.frame_info.variables_by_lineno[self.lineno]
        ]

    @cached_property
    def executing_node_ranges(self) -> List[RangeInLine]:
        """
        A list of one or zero RangeInLines for the executing node of this frame.
        The list will have one element if the node can be found and it overlaps this line.
        """
        return self._raw_executing_node_ranges(
            self.frame_info._executing_node_common_indent
        )

    def _raw_executing_node_ranges(self, common_indent=0) -> List[RangeInLine]:
        ex = self.frame_info.executing
        node = ex.node
        if node:
            rang = self.range_from_node(node, ex, common_indent)
            if rang:
                return [rang]
        return []

    def range_from_node(
        self, node: ast.AST, data: Any, common_indent: int = 0
    ) -> Optional[RangeInLine]:
        """
        If the given node overlaps with this line, return a RangeInLine
        with the correct start and end and the given data.
        Otherwise, return None.
        """
        atext = self.frame_info.source.asttext()
        (start, range_start), (end, range_end) = atext.get_text_positions(node, padded=False)

        if not (start <= self.lineno <= end):
            return None

        if start != self.lineno:
            range_start = common_indent

        if end != self.lineno:
            range_end = len(self.text)

        if range_start == range_end == 0:
            # This is an empty line. If it were included, it would result
            # in a value of zero for the common indentation assigned to
            # a block of code.
            return None

        return RangeInLine(range_start, range_end, data)

    def render(
            self,
            markers: Iterable[MarkerInLine] = (),
            *,
            strip_leading_indent: bool = True,
            pygmented: bool = False,
            escape_html: bool = False
    ) -> str:
        """
        Produces a string for display consisting of .text
        with the .strings of each marker inserted at the correct positions.
        If strip_leading_indent is true (the default) then leading spaces
        common to all lines in this frame will be excluded.
        """
        if pygmented and self.frame_info.scope:
            assert_(not markers, ValueError("Cannot use pygmented with markers"))
            start_line, lines = self.frame_info._pygmented_scope_lines
            result = lines[self.lineno - start_line]
            if strip_leading_indent:
                result = result.replace(self.text[:self.leading_indent], "", 1)
            return result

        text = self.text

        # This just makes the loop below simpler
        markers = list(markers) + [MarkerInLine(position=len(text), is_start=False, string='')]

        markers.sort(key=lambda t: t[:2])

        parts = []
        if strip_leading_indent:
            start = self.leading_indent
        else:
            start = 0
        original_start = start

        for marker in markers:
            text_part = text[start:marker.position]
            if escape_html:
                text_part = html.escape(text_part)
            parts.append(text_part)
            parts.append(marker.string)

            # Ensure that start >= leading_indent
            start = max(marker.position, original_start)
        return ''.join(parts)


def markers_from_ranges(
        ranges: Iterable[RangeInLine],
        converter: Callable[[RangeInLine], Optional[Tuple[str, str]]],
) -> List[MarkerInLine]:
    """
    Helper to create MarkerInLines given some RangeInLines.
    converter should be a function accepting a RangeInLine returning
    either None (which is ignored) or a pair of strings which
    are used to create two markers included in the returned list.
    """
    markers = []
    for rang in ranges:
        converted = converter(rang)
        if converted is None:
            continue

        start_string, end_string = converted
        if not (isinstance(start_string, str) and isinstance(end_string, str)):
            raise TypeError("converter should return None or a pair of strings")

        markers += [
            MarkerInLine(position=rang.start, is_start=True, string=start_string),
            MarkerInLine(position=rang.end, is_start=False, string=end_string),
        ]
    return markers


def style_with_executing_node(style, modifier):
    from pygments.styles import get_style_by_name
    if isinstance(style, str):
        style = get_style_by_name(style)

    class NewStyle(style):
        for_executing_node = True

        styles = {
            **style.styles,
            **{
                k.ExecutingNode: v + " " + modifier
                for k, v in style.styles.items()
            }
        }

    return NewStyle


class RepeatedFrames:
    """
    A sequence of consecutive stack frames which shouldn't be displayed because
    the same code and line number were repeated many times in the stack, e.g.
    because of deep recursion.

    Attributes:
        - frames: list of raw frame or traceback objects
        - frame_keys: list of tuples (frame.f_code, lineno) extracted from the frame objects.
                        It's this information from the frames that is used to determine
                        whether two frames should be considered similar (i.e. repeating).
        - description: A string briefly describing frame_keys
    """
    def __init__(
            self,
            frames: List[Union[FrameType, TracebackType]],
            frame_keys: List[Tuple[CodeType, int]],
    ):
        self.frames = frames
        self.frame_keys = frame_keys

    @cached_property
    def description(self) -> str:
        """
        A string briefly describing the repeated frames, e.g.
            my_function at line 10 (100 times)
        """
        counts = sorted(Counter(self.frame_keys).items(),
                        key=lambda item: (-item[1], item[0][0].co_name))
        return ', '.join(
            '{name} at line {lineno} ({count} times)'.format(
                name=Source.for_filename(code.co_filename).code_qualname(code),
                lineno=lineno,
                count=count,
            )
            for (code, lineno), count in counts
        )

    def __repr__(self):
        return '<{self.__class__.__name__} {self.description}>'.format(self=self)


class FrameInfo(object):
    """
    Information about a frame!
    Pass either a frame object or a traceback object,
    and optionally an Options object to configure.

    Or use the classmethod FrameInfo.stack_data() for an iterator of FrameInfo and
    RepeatedFrames objects. 

    Attributes:
        - frame: an actual stack frame object, either frame_or_tb or frame_or_tb.tb_frame
        - options
        - code: frame.f_code
        - source: a Source object
        - filename: a hopefully absolute file path derived from code.co_filename
        - scope: the AST node of the innermost function, class or module being executed
        - lines: a list of Line/LineGap objects to display, determined by options
        - executing: an Executing object from the `executing` library, which has:
            - .node: the AST node being executed in this frame, or None if it's unknown
            - .statements: a set of one or more candidate statements (AST nodes, probably just one)
                currently being executed in this frame.
            - .code_qualname(): the __qualname__ of the function or class being executed,
                or just the code name.

    Properties returning one or more pieces of source code (ranges of lines):
        - scope_pieces: all the pieces in the scope
        - included_pieces: a subset of scope_pieces determined by options
        - executing_piece: the piece currently being executed in this frame

    Properties returning lists of Variable objects:
        - variables: all variables in the scope
        - variables_by_lineno: variables organised into lines
        - variables_in_lines: variables contained within FrameInfo.lines
        - variables_in_executing_piece: variables contained within FrameInfo.executing_piece
    """
    def __init__(
            self,
            frame_or_tb: Union[FrameType, TracebackType],
            options: Optional[Options] = None,
    ):
        self.executing = Source.executing(frame_or_tb)
        frame, self.lineno = frame_and_lineno(frame_or_tb)
        self.frame = frame
        self.code = frame.f_code
        self.options = options or Options()  # type: Options
        self.source = self.executing.source  # type: Source


    def __repr__(self):
        return "{self.__class__.__name__}({self.frame})".format(self=self)

    @classmethod
    def stack_data(
            cls,
            frame_or_tb: Union[FrameType, TracebackType],
            options: Optional[Options] = None,
            *,
            collapse_repeated_frames: bool = True
    ) -> Iterator[Union['FrameInfo', RepeatedFrames]]:
        """
        An iterator of FrameInfo and RepeatedFrames objects representing
        a full traceback or stack. Similar consecutive frames are collapsed into RepeatedFrames
        objects, so always check what type of object has been yielded.

        Pass either a frame object or a traceback object,
        and optionally an Options object to configure.
        """
        stack = list(iter_stack(frame_or_tb))

        # Reverse the stack from a frame so that it's in the same order
        # as the order from a traceback, which is the order of a printed
        # traceback when read top to bottom (most recent call last)
        if is_frame(frame_or_tb):
            stack = stack[::-1]

        def mapper(f):
            return cls(f, options)

        if not collapse_repeated_frames:
            yield from map(mapper, stack)
            return

        def _frame_key(x):
            frame, lineno = frame_and_lineno(x)
            return frame.f_code, lineno

        yield from collapse_repeated(
            stack,
            mapper=mapper,
            collapser=RepeatedFrames,
            key=_frame_key,
        )

    @cached_property
    def scope_pieces(self) -> List[range]:
        """
        All the pieces (ranges of lines) contained in this object's .scope,
        unless there is no .scope (because the source isn't valid Python syntax)
        in which case it returns all the pieces in the source file, each containing one line.
        """
        if not self.scope:
            return self.source.pieces

        scope_start, scope_end = self.source.line_range(self.scope)
        return [
            piece
            for piece in self.source.pieces
            if scope_start <= piece.start and piece.stop <= scope_end
        ]

    @cached_property
    def filename(self) -> str:
        """
        A hopefully absolute file path derived from .code.co_filename,
        the current working directory, and sys.path.
        Code based on ipython.
        """
        result = self.code.co_filename

        if (
                os.path.isabs(result) or
                (
                        result.startswith("<") and
                        result.endswith(">")
                )
        ):
            return result

        # Try to make the filename absolute by trying all
        # sys.path entries (which is also what linecache does)
        # as well as the current working directory
        for dirname in ["."] + list(sys.path):
            try:
                fullname = os.path.join(dirname, result)
                if os.path.isfile(fullname):
                    return os.path.abspath(fullname)
            except Exception:
                # Just in case that sys.path contains very
                # strange entries...
                pass

        return result

    @cached_property
    def executing_piece(self) -> range:
        """
        The piece (range of lines) containing the line currently being executed
        by the interpreter in this frame.
        """
        return only(
            piece
            for piece in self.scope_pieces
            if self.lineno in piece
        )

    @cached_property
    def included_pieces(self) -> List[range]:
        """
        The list of pieces (ranges of lines) to display for this frame.
        Consists of .executing_piece, surrounding context pieces
        determined by .options.before and .options.after,
        and the function signature if a function is being executed and
        .options.include_signature is True (in which case this might not
        be a contiguous range of pieces).
        Always a subset of .scope_pieces.
        """
        scope_pieces = self.scope_pieces
        if not self.scope_pieces:
            return []

        pos = scope_pieces.index(self.executing_piece)
        pieces_start = max(0, pos - self.options.before)
        pieces_end = pos + 1 + self.options.after
        pieces = scope_pieces[pieces_start:pieces_end]

        if (
                self.options.include_signature
                and not self.code.co_name.startswith('<')
                and isinstance(self.scope, (ast.FunctionDef, ast.AsyncFunctionDef))
                and pieces_start > 0
        ):
            pieces.insert(0, scope_pieces[0])

        return pieces

    @cached_property
    def _executing_node_common_indent(self) -> int:
        """
        The common minimal indentation shared by the markers intended
        for an exception node that spans multiple lines.

        Intended to be used only internally.
        """
        indents = []
        lines = [line for line in self.lines if isinstance(line, Line)]

        for line in lines:
            for rang in line._raw_executing_node_ranges():
                begin_text = len(line.text) - len(line.text.lstrip())
                indent = max(rang.start, begin_text)
                indents.append(indent)

        if len(indents) <= 1:
            return 0

        return min(indents[1:])

    @cached_property
    def lines(self) -> List[Union[Line, LineGap, BlankLineRange]]:
        """
        A list of lines to display, determined by options.
        The objects yielded either have type Line, BlankLineRange
        or are the singleton LINE_GAP.
        Always check the type that you're dealing with when iterating.

        LINE_GAP can be created in two ways:
            - by truncating a piece of context that's too long, determined by
                .options.max_lines_per_piece
            - immediately after the signature piece if Options.include_signature is true
              and the following piece isn't already part of the included pieces.

        The Line objects are all within the ranges from .included_pieces.
        """
        pieces = self.included_pieces
        if not pieces:
            return []

        add_empty_lines = self.options.blank_lines in (BlankLines.VISIBLE, BlankLines.SINGLE)
        prev_piece = None
        result = []
        for i, piece in enumerate(pieces):
            if (
                    i == 1
                    and self.scope
                    and pieces[0] == self.scope_pieces[0]
                    and pieces[1] != self.scope_pieces[1]
            ):
                result.append(LINE_GAP)
            elif prev_piece and add_empty_lines and piece.start > prev_piece.stop:
                if self.options.blank_lines == BlankLines.SINGLE:
                    result.append(BlankLineRange(prev_piece.stop, piece.start-1))
                else:  # BlankLines.VISIBLE
                    for lineno in range(prev_piece.stop, piece.start):
                        result.append(Line(self, lineno))

            lines = [Line(self, i) for i in piece]  # type: List[Line]
            if piece != self.executing_piece:
                lines = truncate(
                    lines,
                    max_length=self.options.max_lines_per_piece,
                    middle=[LINE_GAP],
                )
            result.extend(lines)
            prev_piece = piece

        real_lines = [
            line
            for line in result
            if isinstance(line, Line)
        ]

        text = "\n".join(
            line.text
            for line in real_lines
        )
        dedented_lines = dedent(text).splitlines()
        leading_indent = len(real_lines[0].text) - len(dedented_lines[0])
        for line in real_lines:
            line.leading_indent = leading_indent
        return result

    @cached_property
    def scope(self) -> Optional[ast.AST]:
        """
        The AST node of the innermost function, class or module being executed.
        """
        if not self.source.tree or not self.executing.statements:
            return None

        stmt = list(self.executing.statements)[0]
        while True:
            # Get the parent first in case the original statement is already
            # a function definition, e.g. if we're calling a decorator
            # In that case we still want the surrounding scope, not that function
            stmt = stmt.parent
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                return stmt

    @cached_property
    def _pygmented_scope_lines(self) -> Optional[Tuple[int, List[str]]]:
        # noinspection PyUnresolvedReferences
        from pygments.formatters import HtmlFormatter

        formatter = self.options.pygments_formatter
        scope = self.scope
        assert_(formatter, ValueError("Must set a pygments formatter in Options"))
        assert_(scope)

        if isinstance(formatter, HtmlFormatter):
            formatter.nowrap = True

        atext = self.source.asttext()
        node = self.executing.node
        if node and getattr(formatter.style, "for_executing_node", False):
            scope_start = atext.get_text_range(scope)[0]
            start, end = atext.get_text_range(node)
            start -= scope_start
            end -= scope_start
            ranges = [(start, end)]
        else:
            ranges = []

        code = atext.get_text(scope)
        lines = _pygmented_with_ranges(formatter, code, ranges)

        start_line = self.source.line_range(scope)[0]

        return start_line, lines

    @cached_property
    def variables(self) -> List[Variable]:
        """
        All Variable objects whose nodes are contained within .scope
        and whose values could be safely evaluated by pure_eval.
        """
        if not self.scope:
            return []

        evaluator = Evaluator.from_frame(self.frame)
        scope = self.scope
        node_values = [
            pair
            for pair in evaluator.find_expressions(scope)
            if is_expression_interesting(*pair)
        ]  # type: List[Tuple[ast.AST, Any]]

        if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for node in ast.walk(scope.args):
                if not isinstance(node, ast.arg):
                    continue
                name = node.arg
                try:
                    value = evaluator.names[name]
                except KeyError:
                    pass
                else:
                    node_values.append((node, value))

        # Group equivalent nodes together
        def get_text(n):
            if isinstance(n, ast.arg):
                return n.arg
            else:
                return self.source.asttext().get_text(n)

        def normalise_node(n):
            try:
                # Add parens to avoid syntax errors for multiline expressions
                return ast.parse('(' + get_text(n) + ')')
            except Exception:
                return n

        grouped = group_by_key_func(
            node_values,
            lambda nv: ast.dump(normalise_node(nv[0])),
        )

        result = []
        for group in grouped.values():
            nodes, values = zip(*group)
            value = values[0]
            text = get_text(nodes[0])
            if not text:
                continue
            result.append(Variable(text, nodes, value))

        return result

    @cached_property
    def variables_by_lineno(self) -> Mapping[int, List[Tuple[Variable, ast.AST]]]:
        """
        A mapping from 1-based line numbers to lists of pairs:
            - A Variable object
            - A specific AST node from the variable's .nodes list that's
                in the line at that line number.
        """
        result = defaultdict(list)
        for var in self.variables:
            for node in var.nodes:
                for lineno in range(*self.source.line_range(node)):
                    result[lineno].append((var, node))
        return result

    @cached_property
    def variables_in_lines(self) -> List[Variable]:
        """
        A list of Variable objects contained within the lines returned by .lines.
        """
        return unique_in_order(
            var
            for line in self.lines
            if isinstance(line, Line)
            for var, node in self.variables_by_lineno[line.lineno]
        )

    @cached_property
    def variables_in_executing_piece(self) -> List[Variable]:
        """
        A list of Variable objects contained within the lines
        in the range returned by .executing_piece.
        """
        return unique_in_order(
            var
            for lineno in self.executing_piece
            for var, node in self.variables_by_lineno[lineno]
        )

# === NexusCore/openenv\Lib\site-packages\git\refs\symbolic.py ===
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

__all__ = ["SymbolicReference"]

import os

from gitdb.exc import BadName, BadObject

from git.compat import defenc
from git.objects.base import Object
from git.objects.commit import Commit
from git.refs.log import RefLog
from git.util import (
    LockedFD,
    assure_directory_exists,
    hex_to_bin,
    join_path,
    join_path_native,
    to_native_path_linux,
)

# typing ------------------------------------------------------------------

from typing import (
    Any,
    Iterator,
    List,
    TYPE_CHECKING,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from git.types import AnyGitObject, PathLike

if TYPE_CHECKING:
    from git.config import GitConfigParser
    from git.objects.commit import Actor
    from git.refs import Head, TagReference, RemoteReference, Reference
    from git.refs.log import RefLogEntry
    from git.repo import Repo


T_References = TypeVar("T_References", bound="SymbolicReference")

# ------------------------------------------------------------------------------


def _git_dir(repo: "Repo", path: Union[PathLike, None]) -> PathLike:
    """Find the git dir that is appropriate for the path."""
    name = f"{path}"
    if name in ["HEAD", "ORIG_HEAD", "FETCH_HEAD", "index", "logs"]:
        return repo.git_dir
    return repo.common_dir


class SymbolicReference:
    """Special case of a reference that is symbolic.

    This does not point to a specific commit, but to another
    :class:`~git.refs.head.Head`, which itself specifies a commit.

    A typical example for a symbolic reference is :class:`~git.refs.head.HEAD`.
    """

    __slots__ = ("repo", "path")

    _resolve_ref_on_create = False
    _points_to_commits_only = True
    _common_path_default = ""
    _remote_common_path_default = "refs/remotes"
    _id_attribute_ = "name"

    def __init__(self, repo: "Repo", path: PathLike, check_path: bool = False) -> None:
        self.repo = repo
        self.path = path

    def __str__(self) -> str:
        return str(self.path)

    def __repr__(self) -> str:
        return '<git.%s "%s">' % (self.__class__.__name__, self.path)

    def __eq__(self, other: object) -> bool:
        if hasattr(other, "path"):
            other = cast(SymbolicReference, other)
            return self.path == other.path
        return False

    def __ne__(self, other: object) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        return hash(self.path)

    @property
    def name(self) -> str:
        """
        :return:
            In case of symbolic references, the shortest assumable name is the path
            itself.
        """
        return str(self.path)

    @property
    def abspath(self) -> PathLike:
        return join_path_native(_git_dir(self.repo, self.path), self.path)

    @classmethod
    def _get_packed_refs_path(cls, repo: "Repo") -> str:
        return os.path.join(repo.common_dir, "packed-refs")

    @classmethod
    def _iter_packed_refs(cls, repo: "Repo") -> Iterator[Tuple[str, str]]:
        """Return an iterator yielding pairs of sha1/path pairs (as strings) for the
        corresponding refs.

        :note:
            The packed refs file will be kept open as long as we iterate.
        """
        try:
            with open(cls._get_packed_refs_path(repo), "rt", encoding="UTF-8") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("#"):
                        # "# pack-refs with: peeled fully-peeled sorted"
                        # the git source code shows "peeled",
                        # "fully-peeled" and "sorted" as the keywords
                        # that can go on this line, as per comments in git file
                        # refs/packed-backend.c
                        # I looked at master on 2017-10-11,
                        # commit 111ef79afe, after tag v2.15.0-rc1
                        # from repo https://github.com/git/git.git
                        if line.startswith("# pack-refs with:") and "peeled" not in line:
                            raise TypeError("PackingType of packed-Refs not understood: %r" % line)
                        # END abort if we do not understand the packing scheme
                        continue
                    # END parse comment

                    # Skip dereferenced tag object entries - previous line was actual
                    # tag reference for it.
                    if line[0] == "^":
                        continue

                    yield cast(Tuple[str, str], tuple(line.split(" ", 1)))
                # END for each line
        except OSError:
            return None
        # END no packed-refs file handling

    @classmethod
    def dereference_recursive(cls, repo: "Repo", ref_path: Union[PathLike, None]) -> str:
        """
        :return:
            hexsha stored in the reference at the given `ref_path`, recursively
            dereferencing all intermediate references as required

        :param repo:
            The repository containing the reference at `ref_path`.
        """

        while True:
            hexsha, ref_path = cls._get_ref_info(repo, ref_path)
            if hexsha is not None:
                return hexsha
        # END recursive dereferencing

    @staticmethod
    def _check_ref_name_valid(ref_path: PathLike) -> None:
        """Check a ref name for validity.

        This is based on the rules described in :manpage:`git-check-ref-format(1)`.
        """
        previous: Union[str, None] = None
        one_before_previous: Union[str, None] = None
        for c in str(ref_path):
            if c in " ~^:?*[\\":
                raise ValueError(
                    f"Invalid reference '{ref_path}': references cannot contain spaces, tildes (~), carets (^),"
                    f" colons (:), question marks (?), asterisks (*), open brackets ([) or backslashes (\\)"
                )
            elif c == ".":
                if previous is None or previous == "/":
                    raise ValueError(
                        f"Invalid reference '{ref_path}': references cannot start with a period (.) or contain '/.'"
                    )
                elif previous == ".":
                    raise ValueError(f"Invalid reference '{ref_path}': references cannot contain '..'")
            elif c == "/":
                if previous == "/":
                    raise ValueError(f"Invalid reference '{ref_path}': references cannot contain '//'")
                elif previous is None:
                    raise ValueError(
                        f"Invalid reference '{ref_path}': references cannot start with forward slashes '/'"
                    )
            elif c == "{" and previous == "@":
                raise ValueError(f"Invalid reference '{ref_path}': references cannot contain '@{{'")
            elif ord(c) < 32 or ord(c) == 127:
                raise ValueError(f"Invalid reference '{ref_path}': references cannot contain ASCII control characters")

            one_before_previous = previous
            previous = c

        if previous == ".":
            raise ValueError(f"Invalid reference '{ref_path}': references cannot end with a period (.)")
        elif previous == "/":
            raise ValueError(f"Invalid reference '{ref_path}': references cannot end with a forward slash (/)")
        elif previous == "@" and one_before_previous is None:
            raise ValueError(f"Invalid reference '{ref_path}': references cannot be '@'")
        elif any(component.endswith(".lock") for component in str(ref_path).split("/")):
            raise ValueError(
                f"Invalid reference '{ref_path}': references cannot have slash-separated components that end with"
                " '.lock'"
            )

    @classmethod
    def _get_ref_info_helper(
        cls, repo: "Repo", ref_path: Union[PathLike, None]
    ) -> Union[Tuple[str, None], Tuple[None, str]]:
        """
        :return:
            *(str(sha), str(target_ref_path))*, where:

            * *sha* is of the file at rela_path points to if available, or ``None``.
            * *target_ref_path* is the reference we point to, or ``None``.
        """
        if ref_path:
            cls._check_ref_name_valid(ref_path)

        tokens: Union[None, List[str], Tuple[str, str]] = None
        repodir = _git_dir(repo, ref_path)
        try:
            with open(os.path.join(repodir, str(ref_path)), "rt", encoding="UTF-8") as fp:
                value = fp.read().rstrip()
            # Don't only split on spaces, but on whitespace, which allows to parse lines like:
            # 60b64ef992065e2600bfef6187a97f92398a9144                branch 'master' of git-server:/path/to/repo
            tokens = value.split()
            assert len(tokens) != 0
        except OSError:
            # Probably we are just packed. Find our entry in the packed refs file.
            # NOTE: We are not a symbolic ref if we are in a packed file, as these
            # are excluded explicitly.
            for sha, path in cls._iter_packed_refs(repo):
                if path != ref_path:
                    continue
                # sha will be used.
                tokens = sha, path
                break
            # END for each packed ref
        # END handle packed refs
        if tokens is None:
            raise ValueError("Reference at %r does not exist" % ref_path)

        # Is it a reference?
        if tokens[0] == "ref:":
            return (None, tokens[1])

        # It's a commit.
        if repo.re_hexsha_only.match(tokens[0]):
            return (tokens[0], None)

        raise ValueError("Failed to parse reference information from %r" % ref_path)

    @classmethod
    def _get_ref_info(cls, repo: "Repo", ref_path: Union[PathLike, None]) -> Union[Tuple[str, None], Tuple[None, str]]:
        """
        :return:
            *(str(sha), str(target_ref_path))*, where:

            * *sha* is of the file at rela_path points to if available, or ``None``.
            * *target_ref_path* is the reference we point to, or ``None``.
        """
        return cls._get_ref_info_helper(repo, ref_path)

    def _get_object(self) -> AnyGitObject:
        """
        :return:
            The object our ref currently refers to. Refs can be cached, they will always
            point to the actual object as it gets re-created on each query.
        """
        # We have to be dynamic here as we may be a tag which can point to anything.
        # Our path will be resolved to the hexsha which will be used accordingly.
        return Object.new_from_sha(self.repo, hex_to_bin(self.dereference_recursive(self.repo, self.path)))

    def _get_commit(self) -> "Commit":
        """
        :return:
            :class:`~git.objects.commit.Commit` object we point to. This works for
            detached and non-detached :class:`SymbolicReference` instances. The symbolic
            reference will be dereferenced recursively.
        """
        obj = self._get_object()
        if obj.type == "tag":
            obj = obj.object
        # END dereference tag

        if obj.type != Commit.type:
            raise TypeError("Symbolic Reference pointed to object %r, commit was required" % obj)
        # END handle type
        return obj

    def set_commit(
        self,
        commit: Union[Commit, "SymbolicReference", str],
        logmsg: Union[str, None] = None,
    ) -> "SymbolicReference":
        """Like :meth:`set_object`, but restricts the type of object to be a
        :class:`~git.objects.commit.Commit`.

        :raise ValueError:
            If `commit` is not a :class:`~git.objects.commit.Commit` object, nor does it
            point to a commit.

        :return:
            self
        """
        # Check the type - assume the best if it is a base-string.
        invalid_type = False
        if isinstance(commit, Object):
            invalid_type = commit.type != Commit.type
        elif isinstance(commit, SymbolicReference):
            invalid_type = commit.object.type != Commit.type
        else:
            try:
                invalid_type = self.repo.rev_parse(commit).type != Commit.type
            except (BadObject, BadName) as e:
                raise ValueError("Invalid object: %s" % commit) from e
            # END handle exception
        # END verify type

        if invalid_type:
            raise ValueError("Need commit, got %r" % commit)
        # END handle raise

        # We leave strings to the rev-parse method below.
        self.set_object(commit, logmsg)

        return self

    def set_object(
        self,
        object: Union[AnyGitObject, "SymbolicReference", str],
        logmsg: Union[str, None] = None,
    ) -> "SymbolicReference":
        """Set the object we point to, possibly dereference our symbolic reference
        first. If the reference does not exist, it will be created.

        :param object:
            A refspec, a :class:`SymbolicReference` or an
            :class:`~git.objects.base.Object` instance.

            * :class:`SymbolicReference` instances will be dereferenced beforehand to
              obtain the git object they point to.
            * :class:`~git.objects.base.Object` instances must represent git objects
              (:class:`~git.types.AnyGitObject`).

        :param logmsg:
            If not ``None``, the message will be used in the reflog entry to be written.
            Otherwise the reflog is not altered.

        :note:
            Plain :class:`SymbolicReference` instances may not actually point to objects
            by convention.

        :return:
            self
        """
        if isinstance(object, SymbolicReference):
            object = object.object  # @ReservedAssignment
        # END resolve references

        is_detached = True
        try:
            is_detached = self.is_detached
        except ValueError:
            pass
        # END handle non-existing ones

        if is_detached:
            return self.set_reference(object, logmsg)

        # set the commit on our reference
        return self._get_reference().set_object(object, logmsg)

    commit = property(
        _get_commit,
        set_commit,  # type: ignore[arg-type]
        doc="Query or set commits directly",
    )

    object = property(
        _get_object,
        set_object,  # type: ignore[arg-type]
        doc="Return the object our ref currently refers to",
    )

    def _get_reference(self) -> "SymbolicReference":
        """
        :return:
            :class:`~git.refs.reference.Reference` object we point to

        :raise TypeError:
            If this symbolic reference is detached, hence it doesn't point to a
            reference, but to a commit.
        """
        sha, target_ref_path = self._get_ref_info(self.repo, self.path)
        if target_ref_path is None:
            raise TypeError("%s is a detached symbolic reference as it points to %r" % (self, sha))
        return self.from_path(self.repo, target_ref_path)

    def set_reference(
        self,
        ref: Union[AnyGitObject, "SymbolicReference", str],
        logmsg: Union[str, None] = None,
    ) -> "SymbolicReference":
        """Set ourselves to the given `ref`.

        It will stay a symbol if the `ref` is a :class:`~git.refs.reference.Reference`.

        Otherwise a git object, specified as a :class:`~git.objects.base.Object`
        instance or refspec, is assumed. If it is valid, this reference will be set to
        it, which effectively detaches the reference if it was a purely symbolic one.

        :param ref:
            A :class:`SymbolicReference` instance, an :class:`~git.objects.base.Object`
            instance (specifically an :class:`~git.types.AnyGitObject`), or a refspec
            string. Only if the ref is a :class:`SymbolicReference` instance, we will
            point to it. Everything else is dereferenced to obtain the actual object.

        :param logmsg:
            If set to a string, the message will be used in the reflog.
            Otherwise, a reflog entry is not written for the changed reference.
            The previous commit of the entry will be the commit we point to now.

            See also: :meth:`log_append`

        :return:
            self

        :note:
            This symbolic reference will not be dereferenced. For that, see
            :meth:`set_object`.
        """
        write_value = None
        obj = None
        if isinstance(ref, SymbolicReference):
            write_value = "ref: %s" % ref.path
        elif isinstance(ref, Object):
            obj = ref
            write_value = ref.hexsha
        elif isinstance(ref, str):
            try:
                obj = self.repo.rev_parse(ref + "^{}")  # Optionally dereference tags.
                write_value = obj.hexsha
            except (BadObject, BadName) as e:
                raise ValueError("Could not extract object from %s" % ref) from e
            # END end try string
        else:
            raise ValueError("Unrecognized Value: %r" % ref)
        # END try commit attribute

        # typecheck
        if obj is not None and self._points_to_commits_only and obj.type != Commit.type:
            raise TypeError("Require commit, got %r" % obj)
        # END verify type

        oldbinsha: bytes = b""
        if logmsg is not None:
            try:
                oldbinsha = self.commit.binsha
            except ValueError:
                oldbinsha = Commit.NULL_BIN_SHA
            # END handle non-existing
        # END retrieve old hexsha

        fpath = self.abspath
        assure_directory_exists(fpath, is_file=True)

        lfd = LockedFD(fpath)
        fd = lfd.open(write=True, stream=True)
        try:
            fd.write(write_value.encode("utf-8") + b"\n")
            lfd.commit()
        except BaseException:
            lfd.rollback()
            raise
        # Adjust the reflog
        if logmsg is not None:
            self.log_append(oldbinsha, logmsg)

        return self

    # Aliased reference
    reference: Union["Head", "TagReference", "RemoteReference", "Reference"]
    reference = property(  # type: ignore[assignment]
        _get_reference,
        set_reference,  # type: ignore[arg-type]
        doc="Returns the Reference we point to",
    )
    ref = reference

    def is_valid(self) -> bool:
        """
        :return:
            ``True`` if the reference is valid, hence it can be read and points to a
            valid object or reference.
        """
        try:
            self.object  # noqa: B018
        except (OSError, ValueError):
            return False
        else:
            return True

    @property
    def is_detached(self) -> bool:
        """
        :return:
            ``True`` if we are a detached reference, hence we point to a specific commit
            instead to another reference.
        """
        try:
            self.ref  # noqa: B018
            return False
        except TypeError:
            return True

    def log(self) -> "RefLog":
        """
        :return:
            :class:`~git.refs.log.RefLog` for this reference.
            Its last entry reflects the latest change applied to this reference.

        :note:
            As the log is parsed every time, its recommended to cache it for use instead
            of calling this method repeatedly. It should be considered read-only.
        """
        return RefLog.from_file(RefLog.path(self))

    def log_append(
        self,
        oldbinsha: bytes,
        message: Union[str, None],
        newbinsha: Union[bytes, None] = None,
    ) -> "RefLogEntry":
        """Append a logentry to the logfile of this ref.

        :param oldbinsha:
            Binary sha this ref used to point to.

        :param message:
            A message describing the change.

        :param newbinsha:
            The sha the ref points to now. If None, our current commit sha will be used.

        :return:
            The added :class:`~git.refs.log.RefLogEntry` instance.
        """
        # NOTE: We use the committer of the currently active commit - this should be
        # correct to allow overriding the committer on a per-commit level.
        # See https://github.com/gitpython-developers/GitPython/pull/146.
        try:
            committer_or_reader: Union["Actor", "GitConfigParser"] = self.commit.committer
        except ValueError:
            committer_or_reader = self.repo.config_reader()
        # END handle newly cloned repositories
        if newbinsha is None:
            newbinsha = self.commit.binsha

        if message is None:
            message = ""

        return RefLog.append_entry(committer_or_reader, RefLog.path(self), oldbinsha, newbinsha, message)

    def log_entry(self, index: int) -> "RefLogEntry":
        """
        :return:
            :class:`~git.refs.log.RefLogEntry` at the given index

        :param index:
            Python list compatible positive or negative index.

        :note:
            This method must read part of the reflog during execution, hence it should
            be used sparingly, or only if you need just one index. In that case, it will
            be faster than the :meth:`log` method.
        """
        return RefLog.entry_at(RefLog.path(self), index)

    @classmethod
    def to_full_path(cls, path: Union[PathLike, "SymbolicReference"]) -> PathLike:
        """
        :return:
            String with a full repository-relative path which can be used to initialize
            a :class:`~git.refs.reference.Reference` instance, for instance by using
            :meth:`Reference.from_path <git.refs.reference.Reference.from_path>`.
        """
        if isinstance(path, SymbolicReference):
            path = path.path
        full_ref_path = path
        if not cls._common_path_default:
            return full_ref_path
        if not str(path).startswith(cls._common_path_default + "/"):
            full_ref_path = "%s/%s" % (cls._common_path_default, path)
        return full_ref_path

    @classmethod
    def delete(cls, repo: "Repo", path: PathLike) -> None:
        """Delete the reference at the given path.

        :param repo:
            Repository to delete the reference from.

        :param path:
            Short or full path pointing to the reference, e.g. ``refs/myreference`` or
            just ``myreference``, hence ``refs/`` is implied.
            Alternatively the symbolic reference to be deleted.
        """
        full_ref_path = cls.to_full_path(path)
        abs_path = os.path.join(repo.common_dir, full_ref_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)
        else:
            # Check packed refs.
            pack_file_path = cls._get_packed_refs_path(repo)
            try:
                with open(pack_file_path, "rb") as reader:
                    new_lines = []
                    made_change = False
                    dropped_last_line = False
                    for line_bytes in reader:
                        line = line_bytes.decode(defenc)
                        _, _, line_ref = line.partition(" ")
                        line_ref = line_ref.strip()
                        # Keep line if it is a comment or if the ref to delete is not in
                        # the line.
                        # If we deleted the last line and this one is a tag-reference
                        # object, we drop it as well.
                        if (line.startswith("#") or full_ref_path != line_ref) and (
                            not dropped_last_line or dropped_last_line and not line.startswith("^")
                        ):
                            new_lines.append(line)
                            dropped_last_line = False
                            continue
                        # END skip comments and lines without our path

                        # Drop this line.
                        made_change = True
                        dropped_last_line = True

                # Write the new lines.
                if made_change:
                    # Binary writing is required, otherwise Windows will open the file
                    # in text mode and change LF to CRLF!
                    with open(pack_file_path, "wb") as fd:
                        fd.writelines(line.encode(defenc) for line in new_lines)

            except OSError:
                pass  # It didn't exist at all.

        # Delete the reflog.
        reflog_path = RefLog.path(cls(repo, full_ref_path))
        if os.path.isfile(reflog_path):
            os.remove(reflog_path)
        # END remove reflog

    @classmethod
    def _create(
        cls: Type[T_References],
        repo: "Repo",
        path: PathLike,
        resolve: bool,
        reference: Union["SymbolicReference", str],
        force: bool,
        logmsg: Union[str, None] = None,
    ) -> T_References:
        """Internal method used to create a new symbolic reference.

        If `resolve` is ``False``, the reference will be taken as is, creating a proper
        symbolic reference. Otherwise it will be resolved to the corresponding object
        and a detached symbolic reference will be created instead.
        """
        git_dir = _git_dir(repo, path)
        full_ref_path = cls.to_full_path(path)
        abs_ref_path = os.path.join(git_dir, full_ref_path)

        # Figure out target data.
        target = reference
        if resolve:
            target = repo.rev_parse(str(reference))

        if not force and os.path.isfile(abs_ref_path):
            target_data = str(target)
            if isinstance(target, SymbolicReference):
                target_data = str(target.path)
            if not resolve:
                target_data = "ref: " + target_data
            with open(abs_ref_path, "rb") as fd:
                existing_data = fd.read().decode(defenc).strip()
            if existing_data != target_data:
                raise OSError(
                    "Reference at %r does already exist, pointing to %r, requested was %r"
                    % (full_ref_path, existing_data, target_data)
                )
        # END no force handling

        ref = cls(repo, full_ref_path)
        ref.set_reference(target, logmsg)
        return ref

    @classmethod
    def create(
        cls: Type[T_References],
        repo: "Repo",
        path: PathLike,
        reference: Union["SymbolicReference", str] = "HEAD",
        logmsg: Union[str, None] = None,
        force: bool = False,
        **kwargs: Any,
    ) -> T_References:
        """Create a new symbolic reference: a reference pointing to another reference.

        :param repo:
            Repository to create the reference in.

        :param path:
            Full path at which the new symbolic reference is supposed to be created at,
            e.g. ``NEW_HEAD`` or ``symrefs/my_new_symref``.

        :param reference:
            The reference which the new symbolic reference should point to.
            If it is a commit-ish, the symbolic ref will be detached.

        :param force:
            If ``True``, force creation even if a symbolic reference with that name
            already exists. Raise :exc:`OSError` otherwise.

        :param logmsg:
            If not ``None``, the message to append to the reflog.
            If ``None``, no reflog entry is written.

        :return:
            Newly created symbolic reference

        :raise OSError:
            If a (Symbolic)Reference with the same name but different contents already
            exists.

        :note:
            This does not alter the current HEAD, index or working tree.
        """
        return cls._create(repo, path, cls._resolve_ref_on_create, reference, force, logmsg)

    def rename(self, new_path: PathLike, force: bool = False) -> "SymbolicReference":
        """Rename self to a new path.

        :param new_path:
            Either a simple name or a full path, e.g. ``new_name`` or
            ``features/new_name``.
            The prefix ``refs/`` is implied for references and will be set as needed.
            In case this is a symbolic ref, there is no implied prefix.

        :param force:
            If ``True``, the rename will succeed even if a head with the target name
            already exists. It will be overwritten in that case.

        :return:
            self

        :raise OSError:
            If a file at path but with different contents already exists.
        """
        new_path = self.to_full_path(new_path)
        if self.path == new_path:
            return self

        new_abs_path = os.path.join(_git_dir(self.repo, new_path), new_path)
        cur_abs_path = os.path.join(_git_dir(self.repo, self.path), self.path)
        if os.path.isfile(new_abs_path):
            if not force:
                # If they point to the same file, it's not an error.
                with open(new_abs_path, "rb") as fd1:
                    f1 = fd1.read().strip()
                with open(cur_abs_path, "rb") as fd2:
                    f2 = fd2.read().strip()
                if f1 != f2:
                    raise OSError("File at path %r already exists" % new_abs_path)
                # else: We could remove ourselves and use the other one, but...
                # ...for clarity, we just continue as usual.
            # END not force handling
            os.remove(new_abs_path)
        # END handle existing target file

        dname = os.path.dirname(new_abs_path)
        if not os.path.isdir(dname):
            os.makedirs(dname)
        # END create directory

        os.rename(cur_abs_path, new_abs_path)
        self.path = new_path

        return self

    @classmethod
    def _iter_items(
        cls: Type[T_References], repo: "Repo", common_path: Union[PathLike, None] = None
    ) -> Iterator[T_References]:
        if common_path is None:
            common_path = cls._common_path_default
        rela_paths = set()

        # Walk loose refs.
        # Currently we do not follow links.
        for root, dirs, files in os.walk(join_path_native(repo.common_dir, common_path)):
            if "refs" not in root.split(os.sep):  # Skip non-refs subfolders.
                refs_id = [d for d in dirs if d == "refs"]
                if refs_id:
                    dirs[0:] = ["refs"]
            # END prune non-refs folders

            for f in files:
                if f == "packed-refs":
                    continue
                abs_path = to_native_path_linux(join_path(root, f))
                rela_paths.add(abs_path.replace(to_native_path_linux(repo.common_dir) + "/", ""))
            # END for each file in root directory
        # END for each directory to walk

        # Read packed refs.
        for _sha, rela_path in cls._iter_packed_refs(repo):
            if rela_path.startswith(str(common_path)):
                rela_paths.add(rela_path)
            # END relative path matches common path
        # END packed refs reading

        # Yield paths in sorted order.
        for path in sorted(rela_paths):
            try:
                yield cls.from_path(repo, path)
            except ValueError:
                continue
        # END for each sorted relative refpath

    @classmethod
    def iter_items(
        cls: Type[T_References],
        repo: "Repo",
        common_path: Union[PathLike, None] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Iterator[T_References]:
        """Find all refs in the repository.

        :param repo:
            The :class:`~git.repo.base.Repo`.

        :param common_path:
            Optional keyword argument to the path which is to be shared by all returned
            Ref objects.
            Defaults to class specific portion if ``None``, ensuring that only refs
            suitable for the actual class are returned.

        :return:
            A list of :class:`SymbolicReference`, each guaranteed to be a symbolic ref
            which is not detached and pointing to a valid ref.

            The list is lexicographically sorted. The returned objects are instances of
            concrete subclasses, such as :class:`~git.refs.head.Head` or
            :class:`~git.refs.tag.TagReference`.
        """
        return (r for r in cls._iter_items(repo, common_path) if r.__class__ is SymbolicReference or not r.is_detached)

    @classmethod
    def from_path(cls: Type[T_References], repo: "Repo", path: PathLike) -> T_References:
        """Make a symbolic reference from a path.

        :param path:
            Full ``.git``-directory-relative path name to the Reference to instantiate.

        :note:
            Use :meth:`to_full_path` if you only have a partial path of a known
            Reference type.

        :return:
            Instance of type :class:`~git.refs.reference.Reference`,
            :class:`~git.refs.head.Head`, or :class:`~git.refs.tag.Tag`, depending on
            the given path.
        """
        if not path:
            raise ValueError("Cannot create Reference from %r" % path)

        # Names like HEAD are inserted after the refs module is imported - we have an
        # import dependency cycle and don't want to import these names in-function.
        from . import HEAD, Head, RemoteReference, TagReference, Reference

        for ref_type in (
            HEAD,
            Head,
            RemoteReference,
            TagReference,
            Reference,
            SymbolicReference,
        ):
            try:
                instance: T_References
                instance = ref_type(repo, path)
                if instance.__class__ is SymbolicReference and instance.is_detached:
                    raise ValueError("SymbolicRef was detached, we drop it")
                else:
                    return instance

            except ValueError:
                pass
            # END exception handling
        # END for each type to try
        raise ValueError("Could not find reference type suitable to handle path %r" % path)

    def is_remote(self) -> bool:
        """:return: True if this symbolic reference points to a remote branch"""
        return str(self.path).startswith(self._remote_common_path_default + "/")

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\services\model_service\client.py ===
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
from collections import OrderedDict
import os
import re
from typing import (
    Callable,
    Dict,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
)
import warnings

from google.api_core import client_options as client_options_lib
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.exceptions import MutualTLSChannelError  # type: ignore
from google.auth.transport import mtls  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta2 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore

from google.ai.generativelanguage_v1beta2.services.model_service import pagers
from google.ai.generativelanguage_v1beta2.types import model, model_service

from .transports.base import DEFAULT_CLIENT_INFO, ModelServiceTransport
from .transports.grpc import ModelServiceGrpcTransport
from .transports.grpc_asyncio import ModelServiceGrpcAsyncIOTransport
from .transports.rest import ModelServiceRestTransport


class ModelServiceClientMeta(type):
    """Metaclass for the ModelService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = OrderedDict()  # type: Dict[str, Type[ModelServiceTransport]]
    _transport_registry["grpc"] = ModelServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = ModelServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = ModelServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[ModelServiceTransport]:
        """Returns an appropriate transport class.

        Args:
            label: The name of the desired transport. If none is
                provided, then the first transport in the registry is used.

        Returns:
            The transport class to use.
        """
        # If a specific transport is requested, return that one.
        if label:
            return cls._transport_registry[label]

        # No transport is requested; return the default (that is, the first one
        # in the dictionary).
        return next(iter(cls._transport_registry.values()))


class ModelServiceClient(metaclass=ModelServiceClientMeta):
    """Provides methods for getting metadata information about
    Generative Models.
    """

    @staticmethod
    def _get_default_mtls_endpoint(api_endpoint):
        """Converts api endpoint to mTLS endpoint.

        Convert "*.sandbox.googleapis.com" and "*.googleapis.com" to
        "*.mtls.sandbox.googleapis.com" and "*.mtls.googleapis.com" respectively.
        Args:
            api_endpoint (Optional[str]): the api endpoint to convert.
        Returns:
            str: converted mTLS api endpoint.
        """
        if not api_endpoint:
            return api_endpoint

        mtls_endpoint_re = re.compile(
            r"(?P<name>[^.]+)(?P<mtls>\.mtls)?(?P<sandbox>\.sandbox)?(?P<googledomain>\.googleapis\.com)?"
        )

        m = mtls_endpoint_re.match(api_endpoint)
        name, mtls, sandbox, googledomain = m.groups()
        if mtls or not googledomain:
            return api_endpoint

        if sandbox:
            return api_endpoint.replace(
                "sandbox.googleapis.com", "mtls.sandbox.googleapis.com"
            )

        return api_endpoint.replace(".googleapis.com", ".mtls.googleapis.com")

    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = "generativelanguage.googleapis.com"
    DEFAULT_MTLS_ENDPOINT = _get_default_mtls_endpoint.__func__(  # type: ignore
        DEFAULT_ENDPOINT
    )

    _DEFAULT_ENDPOINT_TEMPLATE = "generativelanguage.{UNIVERSE_DOMAIN}"
    _DEFAULT_UNIVERSE = "googleapis.com"

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            ModelServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_info(info)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    @classmethod
    def from_service_account_file(cls, filename: str, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            file.

        Args:
            filename (str): The path to the service account private key json
                file.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            ModelServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> ModelServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            ModelServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def model_path(
        model: str,
    ) -> str:
        """Returns a fully-qualified model string."""
        return "models/{model}".format(
            model=model,
        )

    @staticmethod
    def parse_model_path(path: str) -> Dict[str, str]:
        """Parses a model path into its component segments."""
        m = re.match(r"^models/(?P<model>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_billing_account_path(
        billing_account: str,
    ) -> str:
        """Returns a fully-qualified billing_account string."""
        return "billingAccounts/{billing_account}".format(
            billing_account=billing_account,
        )

    @staticmethod
    def parse_common_billing_account_path(path: str) -> Dict[str, str]:
        """Parse a billing_account path into its component segments."""
        m = re.match(r"^billingAccounts/(?P<billing_account>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_folder_path(
        folder: str,
    ) -> str:
        """Returns a fully-qualified folder string."""
        return "folders/{folder}".format(
            folder=folder,
        )

    @staticmethod
    def parse_common_folder_path(path: str) -> Dict[str, str]:
        """Parse a folder path into its component segments."""
        m = re.match(r"^folders/(?P<folder>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_organization_path(
        organization: str,
    ) -> str:
        """Returns a fully-qualified organization string."""
        return "organizations/{organization}".format(
            organization=organization,
        )

    @staticmethod
    def parse_common_organization_path(path: str) -> Dict[str, str]:
        """Parse a organization path into its component segments."""
        m = re.match(r"^organizations/(?P<organization>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_project_path(
        project: str,
    ) -> str:
        """Returns a fully-qualified project string."""
        return "projects/{project}".format(
            project=project,
        )

    @staticmethod
    def parse_common_project_path(path: str) -> Dict[str, str]:
        """Parse a project path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_location_path(
        project: str,
        location: str,
    ) -> str:
        """Returns a fully-qualified location string."""
        return "projects/{project}/locations/{location}".format(
            project=project,
            location=location,
        )

    @staticmethod
    def parse_common_location_path(path: str) -> Dict[str, str]:
        """Parse a location path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)/locations/(?P<location>.+?)$", path)
        return m.groupdict() if m else {}

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[client_options_lib.ClientOptions] = None
    ):
        """Deprecated. Return the API endpoint and client cert source for mutual TLS.

        The client cert source is determined in the following order:
        (1) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is not "true", the
        client cert source is None.
        (2) if `client_options.client_cert_source` is provided, use the provided one; if the
        default client cert source exists, use the default one; otherwise the client cert
        source is None.

        The API endpoint is determined in the following order:
        (1) if `client_options.api_endpoint` if provided, use the provided one.
        (2) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is "always", use the
        default mTLS endpoint; if the environment variable is "never", use the default API
        endpoint; otherwise if client cert source exists, use the default mTLS endpoint, otherwise
        use the default API endpoint.

        More details can be found at https://google.aip.dev/auth/4114.

        Args:
            client_options (google.api_core.client_options.ClientOptions): Custom options for the
                client. Only the `api_endpoint` and `client_cert_source` properties may be used
                in this method.

        Returns:
            Tuple[str, Callable[[], Tuple[bytes, bytes]]]: returns the API endpoint and the
                client cert source to use.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If any errors happen.
        """

        warnings.warn(
            "get_mtls_endpoint_and_cert_source is deprecated. Use the api_endpoint property instead.",
            DeprecationWarning,
        )
        if client_options is None:
            client_options = client_options_lib.ClientOptions()
        use_client_cert = os.getenv("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )

        # Figure out the client cert source to use.
        client_cert_source = None
        if use_client_cert == "true":
            if client_options.client_cert_source:
                client_cert_source = client_options.client_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()

        # Figure out which api endpoint to use.
        if client_options.api_endpoint is not None:
            api_endpoint = client_options.api_endpoint
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            api_endpoint = cls.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = cls.DEFAULT_ENDPOINT

        return api_endpoint, client_cert_source

    @staticmethod
    def _read_environment_variables():
        """Returns the environment variables used by the client.

        Returns:
            Tuple[bool, str, str]: returns the GOOGLE_API_USE_CLIENT_CERTIFICATE,
            GOOGLE_API_USE_MTLS_ENDPOINT, and GOOGLE_CLOUD_UNIVERSE_DOMAIN environment variables.

        Raises:
            ValueError: If GOOGLE_API_USE_CLIENT_CERTIFICATE is not
                any of ["true", "false"].
            google.auth.exceptions.MutualTLSChannelError: If GOOGLE_API_USE_MTLS_ENDPOINT
                is not any of ["auto", "never", "always"].
        """
        use_client_cert = os.getenv(
            "GOOGLE_API_USE_CLIENT_CERTIFICATE", "false"
        ).lower()
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto").lower()
        universe_domain_env = os.getenv("GOOGLE_CLOUD_UNIVERSE_DOMAIN")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )
        return use_client_cert == "true", use_mtls_endpoint, universe_domain_env

    @staticmethod
    def _get_client_cert_source(provided_cert_source, use_cert_flag):
        """Return the client cert source to be used by the client.

        Args:
            provided_cert_source (bytes): The client certificate source provided.
            use_cert_flag (bool): A flag indicating whether to use the client certificate.

        Returns:
            bytes or None: The client cert source to be used by the client.
        """
        client_cert_source = None
        if use_cert_flag:
            if provided_cert_source:
                client_cert_source = provided_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()
        return client_cert_source

    @staticmethod
    def _get_api_endpoint(
        api_override, client_cert_source, universe_domain, use_mtls_endpoint
    ):
        """Return the API endpoint used by the client.

        Args:
            api_override (str): The API endpoint override. If specified, this is always
                the return value of this function and the other arguments are not used.
            client_cert_source (bytes): The client certificate source used by the client.
            universe_domain (str): The universe domain used by the client.
            use_mtls_endpoint (str): How to use the mTLS endpoint, which depends also on the other parameters.
                Possible values are "always", "auto", or "never".

        Returns:
            str: The API endpoint to be used by the client.
        """
        if api_override is not None:
            api_endpoint = api_override
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            _default_universe = ModelServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = ModelServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = ModelServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
                UNIVERSE_DOMAIN=universe_domain
            )
        return api_endpoint

    @staticmethod
    def _get_universe_domain(
        client_universe_domain: Optional[str], universe_domain_env: Optional[str]
    ) -> str:
        """Return the universe domain used by the client.

        Args:
            client_universe_domain (Optional[str]): The universe domain configured via the client options.
            universe_domain_env (Optional[str]): The universe domain configured via the "GOOGLE_CLOUD_UNIVERSE_DOMAIN" environment variable.

        Returns:
            str: The universe domain to be used by the client.

        Raises:
            ValueError: If the universe domain is an empty string.
        """
        universe_domain = ModelServiceClient._DEFAULT_UNIVERSE
        if client_universe_domain is not None:
            universe_domain = client_universe_domain
        elif universe_domain_env is not None:
            universe_domain = universe_domain_env
        if len(universe_domain.strip()) == 0:
            raise ValueError("Universe Domain cannot be an empty string.")
        return universe_domain

    @staticmethod
    def _compare_universes(
        client_universe: str, credentials: ga_credentials.Credentials
    ) -> bool:
        """Returns True iff the universe domains used by the client and credentials match.

        Args:
            client_universe (str): The universe domain configured via the client options.
            credentials (ga_credentials.Credentials): The credentials being used in the client.

        Returns:
            bool: True iff client_universe matches the universe in credentials.

        Raises:
            ValueError: when client_universe does not match the universe in credentials.
        """

        default_universe = ModelServiceClient._DEFAULT_UNIVERSE
        credentials_universe = getattr(credentials, "universe_domain", default_universe)

        if client_universe != credentials_universe:
            raise ValueError(
                "The configured universe domain "
                f"({client_universe}) does not match the universe domain "
                f"found in the credentials ({credentials_universe}). "
                "If you haven't configured the universe domain explicitly, "
                f"`{default_universe}` is the default."
            )
        return True

    def _validate_universe_domain(self):
        """Validates client's and credentials' universe domains are consistent.

        Returns:
            bool: True iff the configured universe domain is valid.

        Raises:
            ValueError: If the configured universe domain is not valid.
        """
        self._is_universe_domain_valid = (
            self._is_universe_domain_valid
            or ModelServiceClient._compare_universes(
                self.universe_domain, self.transport._credentials
            )
        )
        return self._is_universe_domain_valid

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used by the client instance.
        """
        return self._universe_domain

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, ModelServiceTransport, Callable[..., ModelServiceTransport]]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the model service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,ModelServiceTransport,Callable[..., ModelServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the ModelServiceTransport constructor.
                If set to None, a transport is chosen automatically.
            client_options (Optional[Union[google.api_core.client_options.ClientOptions, dict]]):
                Custom options for the client.

                1. The ``api_endpoint`` property can be used to override the
                default endpoint provided by the client when ``transport`` is
                not explicitly provided. Only if this property is not set and
                ``transport`` was not explicitly provided, the endpoint is
                determined by the GOOGLE_API_USE_MTLS_ENDPOINT environment
                variable, which have one of the following values:
                "always" (always use the default mTLS endpoint), "never" (always
                use the default regular endpoint) and "auto" (auto-switch to the
                default mTLS endpoint if client certificate is present; this is
                the default value).

                2. If the GOOGLE_API_USE_CLIENT_CERTIFICATE environment variable
                is "true", then the ``client_cert_source`` property can be used
                to provide a client certificate for mTLS transport. If
                not provided, the default SSL client certificate will be used if
                present. If GOOGLE_API_USE_CLIENT_CERTIFICATE is "false" or not
                set, no client certificate will be used.

                3. The ``universe_domain`` property can be used to override the
                default "googleapis.com" universe. Note that the ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client_options = client_options
        if isinstance(self._client_options, dict):
            self._client_options = client_options_lib.from_dict(self._client_options)
        if self._client_options is None:
            self._client_options = client_options_lib.ClientOptions()
        self._client_options = cast(
            client_options_lib.ClientOptions, self._client_options
        )

        universe_domain_opt = getattr(self._client_options, "universe_domain", None)

        (
            self._use_client_cert,
            self._use_mtls_endpoint,
            self._universe_domain_env,
        ) = ModelServiceClient._read_environment_variables()
        self._client_cert_source = ModelServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = ModelServiceClient._get_universe_domain(
            universe_domain_opt, self._universe_domain_env
        )
        self._api_endpoint = None  # updated below, depending on `transport`

        # Initialize the universe domain validation.
        self._is_universe_domain_valid = False

        api_key_value = getattr(self._client_options, "api_key", None)
        if api_key_value and credentials:
            raise ValueError(
                "client_options.api_key and credentials are mutually exclusive"
            )

        # Save or instantiate the transport.
        # Ordinarily, we provide the transport, but allowing a custom transport
        # instance provides an extensibility point for unusual situations.
        transport_provided = isinstance(transport, ModelServiceTransport)
        if transport_provided:
            # transport is a ModelServiceTransport instance.
            if credentials or self._client_options.credentials_file or api_key_value:
                raise ValueError(
                    "When providing a transport instance, "
                    "provide its credentials directly."
                )
            if self._client_options.scopes:
                raise ValueError(
                    "When providing a transport instance, provide its scopes "
                    "directly."
                )
            self._transport = cast(ModelServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = self._api_endpoint or ModelServiceClient._get_api_endpoint(
            self._client_options.api_endpoint,
            self._client_cert_source,
            self._universe_domain,
            self._use_mtls_endpoint,
        )

        if not transport_provided:
            import google.auth._default  # type: ignore

            if api_key_value and hasattr(
                google.auth._default, "get_api_key_credentials"
            ):
                credentials = google.auth._default.get_api_key_credentials(
                    api_key_value
                )

            transport_init: Union[
                Type[ModelServiceTransport], Callable[..., ModelServiceTransport]
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., ModelServiceTransport], transport)
            )
            # initialize with the provided callable or the passed in class
            self._transport = transport_init(
                credentials=credentials,
                credentials_file=self._client_options.credentials_file,
                host=self._api_endpoint,
                scopes=self._client_options.scopes,
                client_cert_source_for_mtls=self._client_cert_source,
                quota_project_id=self._client_options.quota_project_id,
                client_info=client_info,
                always_use_jwt_access=True,
                api_audience=self._client_options.api_audience,
            )

    def get_model(
        self,
        request: Optional[Union[model_service.GetModelRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> model.Model:
        r"""Gets information about a specific Model.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta2

            def sample_get_model():
                # Create a client
                client = generativelanguage_v1beta2.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta2.GetModelRequest(
                    name="name_value",
                )

                # Make the request
                response = client.get_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta2.types.GetModelRequest, dict]):
                The request object. Request for getting information about
                a specific Model.
            name (str):
                Required. The resource name of the model.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta2.types.Model:
                Information about a Generative
                Language Model.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.GetModelRequest):
            request = model_service.GetModelRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.get_model]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def list_models(
        self,
        request: Optional[Union[model_service.ListModelsRequest, dict]] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListModelsPager:
        r"""Lists models available through the API.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta2

            def sample_list_models():
                # Create a client
                client = generativelanguage_v1beta2.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta2.ListModelsRequest(
                )

                # Make the request
                page_result = client.list_models(request=request)

                # Handle the response
                for response in page_result:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta2.types.ListModelsRequest, dict]):
                The request object. Request for listing all Models.
            page_size (int):
                The maximum number of ``Models`` to return (per page).

                The service may return fewer models. If unspecified, at
                most 50 models will be returned per page. This method
                returns at most 1000 models per page, even if you pass a
                larger page_size.

                This corresponds to the ``page_size`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            page_token (str):
                A page token, received from a previous ``ListModels``
                call.

                Provide the ``page_token`` returned by one request as an
                argument to the next request to retrieve the next page.

                When paginating, all other parameters provided to
                ``ListModels`` must match the call that provided the
                page token.

                This corresponds to the ``page_token`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta2.services.model_service.pagers.ListModelsPager:
                Response from ListModel containing a paginated list of
                Models.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([page_size, page_token])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.ListModelsRequest):
            request = model_service.ListModelsRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if page_size is not None:
                request.page_size = page_size
            if page_token is not None:
                request.page_token = page_token

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.list_models]

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__iter__` convenience method.
        response = pagers.ListModelsPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def __enter__(self) -> "ModelServiceClient":
        return self

    def __exit__(self, type, value, traceback):
        """Releases underlying transport's resources.

        .. warning::
            ONLY use as a context manager if the transport is NOT shared
            with other clients! Exiting the with block will CLOSE the transport
            and may cause errors in other clients!
        """
        self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("ModelServiceClient",)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\organization_endpoints.py ===
"""
Endpoints for /organization operations

/organization/new
/organization/update
/organization/delete
/organization/member_add
/organization/info
/organization/list
"""

#### ORGANIZATION MANAGEMENT ####

import uuid
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, status

from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import *
from litellm.proxy.auth.auth_checks import can_user_call_model
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.management_endpoints.budget_management_endpoints import (
    new_budget,
    update_budget,
)
from litellm.proxy.management_helpers.object_permission_utils import (
    handle_update_object_permission_common,
)
from litellm.proxy.management_helpers.utils import (
    get_new_internal_user_defaults,
    management_endpoint_wrapper,
)
from litellm.proxy.utils import PrismaClient

router = APIRouter()


@router.post(
    "/organization/new",
    tags=["organization management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=NewOrganizationResponse,
)
async def new_organization(
    data: NewOrganizationRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Allow orgs to own teams

    Set org level budgets + model access.

    Only admins can create orgs.

    # Parameters

    - organization_alias: *str* - The name of the organization.
    - models: *List* - The models the organization has access to.
    - budget_id: *Optional[str]* - The id for a budget (tpm/rpm/max budget) for the organization.
    ### IF NO BUDGET ID - CREATE ONE WITH THESE PARAMS ###
    - max_budget: *Optional[float]* - Max budget for org
    - tpm_limit: *Optional[int]* - Max tpm limit for org
    - rpm_limit: *Optional[int]* - Max rpm limit for org
    - max_parallel_requests: *Optional[int]* - [Not Implemented Yet] Max parallel requests for org
    - soft_budget: *Optional[float]* - [Not Implemented Yet] Get a slack alert when this soft budget is reached. Don't block requests.
    - model_max_budget: *Optional[dict]* - Max budget for a specific model
    - budget_duration: *Optional[str]* - Frequency of reseting org budget
    - metadata: *Optional[dict]* - Metadata for organization, store information for organization. Example metadata - {"extra_info": "some info"}
    - blocked: *bool* - Flag indicating if the org is blocked or not - will stop all calls from keys with this org_id.
    - tags: *Optional[List[str]]* - Tags for [tracking spend](https://litellm.vercel.app/docs/proxy/enterprise#tracking-spend-for-custom-tags) and/or doing [tag-based routing](https://litellm.vercel.app/docs/proxy/tag_routing).
    - organization_id: *Optional[str]* - The organization id of the team. Default is None. Create via `/organization/new`.
    - model_aliases: Optional[dict] - Model aliases for the team. [Docs](https://docs.litellm.ai/docs/proxy/team_based_routing#create-team-with-model-alias)
    - object_permission: Optional[LiteLLM_ObjectPermissionBase] - organization-specific object permission. Example - {"vector_stores": ["vector_store_1", "vector_store_2"]}. IF null or {} then no object permission.
    Case 1: Create new org **without** a budget_id

    ```bash
    curl --location 'http://0.0.0.0:4000/organization/new' \

    --header 'Authorization: Bearer sk-1234' \

    --header 'Content-Type: application/json' \

    --data '{
        "organization_alias": "my-secret-org",
        "models": ["model1", "model2"],
        "max_budget": 100
    }'


    ```

    Case 2: Create new org **with** a budget_id

    ```bash
    curl --location 'http://0.0.0.0:4000/organization/new' \

    --header 'Authorization: Bearer sk-1234' \

    --header 'Content-Type: application/json' \

    --data '{
        "organization_alias": "my-secret-org",
        "models": ["model1", "model2"],
        "budget_id": "428eeaa8-f3ac-4e85-a8fb-7dc8d7aa8689"
    }'
    ```
    """

    from litellm.proxy.proxy_server import (
        litellm_proxy_admin_name,
        llm_router,
        prisma_client,
    )

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if (
        user_api_key_dict.user_role is None
        or user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN
    ):
        raise HTTPException(
            status_code=401,
            detail={
                "error": f"Only admins can create orgs. Your role is = {user_api_key_dict.user_role}"
            },
        )

    if llm_router is None:
        raise HTTPException(
            status_code=500, detail={"error": CommonProxyErrors.no_llm_router.value}
        )

    user_object_correct_type: Optional[LiteLLM_UserTable] = None

    if user_api_key_dict.user_id is not None:
        try:
            user_object = await prisma_client.db.litellm_usertable.find_unique(
                where={"user_id": user_api_key_dict.user_id}
            )
            user_object_correct_type = LiteLLM_UserTable(**user_object.model_dump())
        except Exception:
            pass

    if data.budget_id is None:
        """
        Every organization needs a budget attached.

        If none provided, create one based on provided values
        """
        budget_params = LiteLLM_BudgetTable.model_fields.keys()

        # Only include Budget Params when creating an entry in litellm_budgettable
        _json_data = data.json(exclude_none=True)
        _budget_data = {k: v for k, v in _json_data.items() if k in budget_params}
        budget_row = LiteLLM_BudgetTable(**_budget_data)

        new_budget = prisma_client.jsonify_object(budget_row.json(exclude_none=True))

        _budget = await prisma_client.db.litellm_budgettable.create(
            data={
                **new_budget,  # type: ignore
                "created_by": user_api_key_dict.user_id or litellm_proxy_admin_name,
                "updated_by": user_api_key_dict.user_id or litellm_proxy_admin_name,
            }
        )  # type: ignore

        data.budget_id = _budget.budget_id

    ## Handle Object Permission - MCP, Vector Stores etc.
    object_permission_id = await _set_object_permission(
        data=data,
        prisma_client=prisma_client,
    )

    """
    Ensure only models that user has access to, are given to org
    """
    if len(user_api_key_dict.models) == 0:  # user has access to all models
        pass
    else:
        if len(data.models) == 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "User not allowed to give access to all models. Select models you want org to have access to."
                },
            )

        for m in data.models:
            await can_user_call_model(
                m, llm_router=llm_router, user_object=user_object_correct_type
            )

    organization_row = LiteLLM_OrganizationTable(
        **data.json(exclude_none=True),
        object_permission_id=object_permission_id,
        created_by=user_api_key_dict.user_id or litellm_proxy_admin_name,
        updated_by=user_api_key_dict.user_id or litellm_proxy_admin_name,
    )
    new_organization_row = prisma_client.jsonify_object(
        organization_row.json(exclude_none=True)
    )
    verbose_proxy_logger.info(
        f"new_organization_row: {json.dumps(new_organization_row, indent=2)}"
    )
    response = await prisma_client.db.litellm_organizationtable.create(
        data={
            **new_organization_row,  # type: ignore
        }
    )

    return response


async def _set_object_permission(
    data: NewOrganizationRequest,
    prisma_client: Optional[PrismaClient],
) -> Optional[str]:
    """
    Creates the LiteLLM_ObjectPermissionTable record for the organization.
    - Handles permissions for vector stores and mcp servers.

    Returns the object_permission_id if created, otherwise None.
    """
    if prisma_client is None:
        return None

    if data.object_permission is not None:
        created_object_permission = (
            await prisma_client.db.litellm_objectpermissiontable.create(
                data=data.object_permission.model_dump(exclude_none=True),
            )
        )
        del data.object_permission
        return created_object_permission.object_permission_id
    return None


@router.patch(
    "/organization/update",
    tags=["organization management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=LiteLLM_OrganizationTableWithMembers,
)
async def update_organization(
    data: LiteLLM_OrganizationTableUpdate,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Update an organization
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_id is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Cannot associate a user_id to this action. Check `/key/info` to validate if 'user_id' is set."
            },
        )

    if data.updated_by is None:
        data.updated_by = user_api_key_dict.user_id

    updated_organization_row = prisma_client.jsonify_object(
        data.model_dump(exclude_none=True)
    )
    existing_organization_row = (
        await prisma_client.db.litellm_organizationtable.find_unique(
            where={"organization_id": data.organization_id},
        )
    )

    if existing_organization_row is None:
        raise ValueError(
            f"Organization not found for organization_id={data.organization_id}"
        )

    if data.object_permission is not None:
        updated_organization_row = await handle_update_object_permission(
            data_json=updated_organization_row,
            existing_organization_row=existing_organization_row,
        )

    response = await prisma_client.db.litellm_organizationtable.update(
        where={"organization_id": data.organization_id},
        data=updated_organization_row,
        include={"members": True, "teams": True, "litellm_budget_table": True},
    )

    return response


async def handle_update_object_permission(
    data_json: dict,
    existing_organization_row: LiteLLM_OrganizationTable,
) -> dict:
    """
    Handle the update of object permission for an organization.

    - Upserts the new object permission into the LiteLLM_ObjectPermissionTable
    - Adds object_permission_id to data_json (this gets added in the DB)
    - Pops the object_permission from data_json
    """
    from litellm.proxy.proxy_server import prisma_client

    # Use the common helper to handle the object permission update
    object_permission_id = await handle_update_object_permission_common(
        data_json=data_json,
        existing_object_permission_id=existing_organization_row.object_permission_id,
        prisma_client=prisma_client,
    )

    # Add the object_permission_id to data_json if one was created/updated
    if object_permission_id is not None:
        data_json["object_permission_id"] = object_permission_id

    return data_json


@router.delete(
    "/organization/delete",
    tags=["organization management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=List[LiteLLM_OrganizationTableWithMembers],
)
async def delete_organization(
    data: DeleteOrganizationRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Delete an organization

    # Parameters:

    - organization_ids: List[str] - The organization ids to delete.
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=401,
            detail={"error": "Only proxy admins can delete organizations"},
        )

    deleted_orgs = []
    for organization_id in data.organization_ids:
        # delete all teams in the organization
        await prisma_client.db.litellm_teamtable.delete_many(
            where={"organization_id": organization_id}
        )
        # delete all members in the organization
        await prisma_client.db.litellm_organizationmembership.delete_many(
            where={"organization_id": organization_id}
        )
        # delete all keys in the organization
        await prisma_client.db.litellm_verificationtoken.delete_many(
            where={"organization_id": organization_id}
        )
        # delete the organization
        deleted_org = await prisma_client.db.litellm_organizationtable.delete(
            where={"organization_id": organization_id},
            include={"members": True, "teams": True, "litellm_budget_table": True},
        )
        if deleted_org is None:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Organization={organization_id} not found"},
            )
        deleted_orgs.append(deleted_org)

    return deleted_orgs


@router.get(
    "/organization/list",
    tags=["organization management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=List[LiteLLM_OrganizationTableWithMembers],
)
async def list_organization(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    ```
    curl --location --request GET 'http://0.0.0.0:4000/organization/list' \
        --header 'Authorization: Bearer sk-1234'
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    if prisma_client is None:
        raise HTTPException(
            status_code=400,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    # if proxy admin - get all orgs
    if user_api_key_dict.user_role == LitellmUserRoles.PROXY_ADMIN:
        response = await prisma_client.db.litellm_organizationtable.find_many(
            include={"litellm_budget_table": True, "members": True, "teams": True}
        )
    # if internal user - get orgs they are a member of
    else:
        org_memberships = (
            await prisma_client.db.litellm_organizationmembership.find_many(
                where={"user_id": user_api_key_dict.user_id}
            )
        )
        org_objects = await prisma_client.db.litellm_organizationtable.find_many(
            where={
                "organization_id": {
                    "in": [membership.organization_id for membership in org_memberships]
                }
            },
            include={"litellm_budget_table": True, "members": True, "teams": True},
        )

        response = org_objects

    return response


@router.get(
    "/organization/info",
    tags=["organization management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=LiteLLM_OrganizationTableWithMembers,
)
async def info_organization(organization_id: str):
    """
    Get the org specific information
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    response: Optional[
        LiteLLM_OrganizationTableWithMembers
    ] = await prisma_client.db.litellm_organizationtable.find_unique(
        where={"organization_id": organization_id},
        include={
            "litellm_budget_table": True,
            "members": True,
            "teams": True,
            "object_permission": True,
        },
    )

    if response is None:
        raise HTTPException(status_code=404, detail={"error": "Organization not found"})

    response_pydantic_obj = LiteLLM_OrganizationTableWithMembers(
        **response.model_dump()
    )

    return response_pydantic_obj


@router.post(
    "/organization/info",
    tags=["organization management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def deprecated_info_organization(data: OrganizationRequest):
    """
    DEPRECATED: Use GET /organization/info instead
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail={"error": "No db connected"})

    if len(data.organizations) == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Specify list of organization id's to query. Passed in={data.organizations}"
            },
        )
    response = await prisma_client.db.litellm_organizationtable.find_many(
        where={"organization_id": {"in": data.organizations}},
        include={"litellm_budget_table": True},
    )

    return response


@router.post(
    "/organization/member_add",
    tags=["organization management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=OrganizationAddMemberResponse,
)
@management_endpoint_wrapper
async def organization_member_add(
    data: OrganizationMemberAddRequest,
    http_request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
) -> OrganizationAddMemberResponse:
    """
    [BETA]

    Add new members (either via user_email or user_id) to an organization

    If user doesn't exist, new user row will also be added to User Table

    Only proxy_admin or org_admin of organization, allowed to access this endpoint.

    # Parameters:

    - organization_id: str (required)
    - member: Union[List[Member], Member] (required)
        - role: Literal[LitellmUserRoles] (required)
        - user_id: Optional[str]
        - user_email: Optional[str]

    Note: Either user_id or user_email must be provided for each member.

    Example:
    ```
    curl -X POST 'http://0.0.0.0:4000/organization/member_add' \
    -H 'Authorization: Bearer sk-1234' \
    -H 'Content-Type: application/json' \
    -d '{
        "organization_id": "45e3e396-ee08-4a61-a88e-16b3ce7e0849",
        "member": {
            "role": "internal_user",
            "user_id": "krrish247652@berri.ai"
        },
        "max_budget_in_organization": 100.0
    }'
    ```

    The following is executed in this function:

    1. Check if organization exists
    2. Creates a new Internal User if the user_id or user_email is not found in LiteLLM_UserTable
    3. Add Internal User to the `LiteLLM_OrganizationMembership` table
    """
    try:
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            raise HTTPException(status_code=500, detail={"error": "No db connected"})

        # Check if organization exists
        existing_organization_row = (
            await prisma_client.db.litellm_organizationtable.find_unique(
                where={"organization_id": data.organization_id}
            )
        )
        if existing_organization_row is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": f"Organization not found for organization_id={getattr(data, 'organization_id', None)}"
                },
            )

        members: List[OrgMember]
        if isinstance(data.member, List):
            members = data.member
        else:
            members = [data.member]

        updated_users: List[LiteLLM_UserTable] = []
        updated_organization_memberships: List[LiteLLM_OrganizationMembershipTable] = []

        for member in members:
            (
                updated_user,
                updated_organization_membership,
            ) = await add_member_to_organization(
                member=member,
                organization_id=data.organization_id,
                prisma_client=prisma_client,
            )

            updated_users.append(updated_user)
            updated_organization_memberships.append(updated_organization_membership)

        return OrganizationAddMemberResponse(
            organization_id=data.organization_id,
            updated_users=updated_users,
            updated_organization_memberships=updated_organization_memberships,
        )
    except Exception as e:
        verbose_proxy_logger.exception(f"Error adding member to organization: {e}")
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "detail", f"Authentication Error({str(e)})"),
                type=ProxyErrorTypes.auth_error,
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        elif isinstance(e, ProxyException):
            raise e
        raise ProxyException(
            message="Authentication Error, " + str(e),
            type=ProxyErrorTypes.auth_error,
            param=getattr(e, "param", "None"),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def find_member_if_email(
    user_email: str, prisma_client: PrismaClient
) -> LiteLLM_UserTable:
    """
    Find a member if the user_email is in LiteLLM_UserTable
    """

    try:
        existing_user_email_row: BaseModel = (
            await prisma_client.db.litellm_usertable.find_unique(
                where={"user_email": user_email}
            )
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Unique user not found for user_email={user_email}. Potential duplicate OR non-existent user_email in LiteLLM_UserTable. Use 'user_id' instead."
            },
        )
    existing_user_email_row_pydantic = LiteLLM_UserTable(
        **existing_user_email_row.model_dump()
    )
    return existing_user_email_row_pydantic


@router.patch(
    "/organization/member_update",
    tags=["organization management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=LiteLLM_OrganizationMembershipTable,
)
@management_endpoint_wrapper
async def organization_member_update(
    data: OrganizationMemberUpdateRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Update a member's role in an organization
    """
    try:
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            raise HTTPException(
                status_code=500,
                detail={"error": CommonProxyErrors.db_not_connected_error.value},
            )

        # Check if organization exists
        existing_organization_row = (
            await prisma_client.db.litellm_organizationtable.find_unique(
                where={"organization_id": data.organization_id}
            )
        )
        if existing_organization_row is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Organization not found for organization_id={getattr(data, 'organization_id', None)}"
                },
            )

        # Check if member exists in organization
        if data.user_email is not None and data.user_id is None:
            existing_user_email_row = await find_member_if_email(
                data.user_email, prisma_client
            )
            data.user_id = existing_user_email_row.user_id

        try:
            existing_organization_membership = (
                await prisma_client.db.litellm_organizationmembership.find_unique(
                    where={
                        "user_id_organization_id": {
                            "user_id": data.user_id,
                            "organization_id": data.organization_id,
                        }
                    }
                )
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Error finding organization membership for user_id={data.user_id} in organization={data.organization_id}: {e}"
                },
            )
        if existing_organization_membership is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": f"Member not found in organization for user_id={data.user_id}"
                },
            )

        # Update member role
        if data.role is not None:
            await prisma_client.db.litellm_organizationmembership.update(
                where={
                    "user_id_organization_id": {
                        "user_id": data.user_id,
                        "organization_id": data.organization_id,
                    }
                },
                data={"user_role": data.role},
            )
        if data.max_budget_in_organization is not None:
            # if budget_id is None, create a new budget
            budget_id = existing_organization_membership.budget_id or str(uuid.uuid4())
            if existing_organization_membership.budget_id is None:
                new_budget_obj = BudgetNewRequest(
                    budget_id=budget_id, max_budget=data.max_budget_in_organization
                )
                await new_budget(
                    budget_obj=new_budget_obj, user_api_key_dict=user_api_key_dict
                )
            else:
                # update budget table with new max_budget
                await update_budget(
                    budget_obj=BudgetNewRequest(
                        budget_id=budget_id, max_budget=data.max_budget_in_organization
                    ),
                    user_api_key_dict=user_api_key_dict,
                )

            # update organization membership with new budget_id
            await prisma_client.db.litellm_organizationmembership.update(
                where={
                    "user_id_organization_id": {
                        "user_id": data.user_id,
                        "organization_id": data.organization_id,
                    }
                },
                data={"budget_id": budget_id},
            )
        final_organization_membership: Optional[
            BaseModel
        ] = await prisma_client.db.litellm_organizationmembership.find_unique(
            where={
                "user_id_organization_id": {
                    "user_id": data.user_id,
                    "organization_id": data.organization_id,
                }
            },
            include={"litellm_budget_table": True},
        )

        if final_organization_membership is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Member not found in organization={data.organization_id} for user_id={data.user_id}"
                },
            )

        final_organization_membership_pydantic = LiteLLM_OrganizationMembershipTable(
            **final_organization_membership.model_dump(exclude_none=True)
        )
        return final_organization_membership_pydantic
    except Exception as e:
        verbose_proxy_logger.exception(f"Error updating member in organization: {e}")
        raise e


@router.delete(
    "/organization/member_delete",
    tags=["organization management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def organization_member_delete(
    data: OrganizationMemberDeleteRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Delete a member from an organization
    """
    try:
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            raise HTTPException(
                status_code=500,
                detail={"error": CommonProxyErrors.db_not_connected_error.value},
            )

        if data.user_email is not None and data.user_id is None:
            existing_user_email_row = await find_member_if_email(
                data.user_email, prisma_client
            )
            data.user_id = existing_user_email_row.user_id

        member_to_delete = await prisma_client.db.litellm_organizationmembership.delete(
            where={
                "user_id_organization_id": {
                    "user_id": data.user_id,
                    "organization_id": data.organization_id,
                }
            }
        )
        return member_to_delete

    except Exception as e:
        verbose_proxy_logger.exception(f"Error deleting member from organization: {e}")
        raise e


async def add_member_to_organization(
    member: OrgMember,
    organization_id: str,
    prisma_client: PrismaClient,
) -> Tuple[LiteLLM_UserTable, LiteLLM_OrganizationMembershipTable]:
    """
    Add a member to an organization

    - Checks if member.user_id or member.user_email is in LiteLLM_UserTable
    - If not found, create a new user in LiteLLM_UserTable
    - Add user to organization in LiteLLM_OrganizationMembership
    """

    try:
        user_object: Optional[LiteLLM_UserTable] = None
        existing_user_id_row = None
        existing_user_email_row = None
        ## Check if user exists in LiteLLM_UserTable - user exists - either the user_id or user_email is in LiteLLM_UserTable
        if member.user_id is not None:
            existing_user_id_row = await prisma_client.db.litellm_usertable.find_unique(
                where={"user_id": member.user_id}
            )

        if existing_user_id_row is None and member.user_email is not None:
            try:
                existing_user_email_row = (
                    await prisma_client.db.litellm_usertable.find_unique(
                        where={"user_email": member.user_email}
                    )
                )
            except Exception as e:
                raise ValueError(
                    f"Potential NON-Existent or Duplicate user email in DB: Error finding a unique instance of user_email={member.user_email} in LiteLLM_UserTable.: {e}"
                )

        ## If user does not exist, create a new user
        if existing_user_id_row is None and existing_user_email_row is None:
            # Create a new user - since user does not exist
            user_id: str = member.user_id or str(uuid.uuid4())
            new_user_defaults = get_new_internal_user_defaults(
                user_id=user_id,
                user_email=member.user_email,
            )

            _returned_user = await prisma_client.insert_data(data=new_user_defaults, table_name="user")  # type: ignore
            if _returned_user is not None:
                user_object = LiteLLM_UserTable(**_returned_user.model_dump())
        elif existing_user_email_row is not None and len(existing_user_email_row) > 1:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Multiple users with this email found in db. Please use 'user_id' instead."
                },
            )
        elif existing_user_email_row is not None:
            user_object = LiteLLM_UserTable(**existing_user_email_row.model_dump())
        elif existing_user_id_row is not None:
            user_object = LiteLLM_UserTable(**existing_user_id_row.model_dump())
        else:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": f"User not found for user_id={member.user_id} and user_email={member.user_email}"
                },
            )

        if user_object is None:
            raise ValueError(
                f"User does not exist in LiteLLM_UserTable. user_id={member.user_id} and user_email={member.user_email}"
            )

        # Add user to organization
        _organization_membership = (
            await prisma_client.db.litellm_organizationmembership.create(
                data={
                    "organization_id": organization_id,
                    "user_id": user_object.user_id,
                    "user_role": member.role,
                }
            )
        )
        organization_membership = LiteLLM_OrganizationMembershipTable(
            **_organization_membership.model_dump()
        )
        return user_object, organization_membership

    except Exception as e:
        raise ValueError(
            f"Error adding member={member} to organization={organization_id}: {e}"
        )

# === NexusCore/openenv\Lib\site-packages\starlette\routing.py ===
from __future__ import annotations

import contextlib
import functools
import inspect
import re
import traceback
import types
import typing
import warnings
from contextlib import asynccontextmanager
from enum import Enum

from starlette._exception_handler import wrap_app_handling_exceptions
from starlette._utils import get_route_path, is_async_callable
from starlette.concurrency import run_in_threadpool
from starlette.convertors import CONVERTOR_TYPES, Convertor
from starlette.datastructures import URL, Headers, URLPath
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse, Response
from starlette.types import ASGIApp, Lifespan, Receive, Scope, Send
from starlette.websockets import WebSocket, WebSocketClose


class NoMatchFound(Exception):
    """
    Raised by `.url_for(name, **path_params)` and `.url_path_for(name, **path_params)`
    if no matching route exists.
    """

    def __init__(self, name: str, path_params: dict[str, typing.Any]) -> None:
        params = ", ".join(list(path_params.keys()))
        super().__init__(f'No route exists for name "{name}" and params "{params}".')


class Match(Enum):
    NONE = 0
    PARTIAL = 1
    FULL = 2


def iscoroutinefunction_or_partial(obj: typing.Any) -> bool:  # pragma: no cover
    """
    Correctly determines if an object is a coroutine function,
    including those wrapped in functools.partial objects.
    """
    warnings.warn(
        "iscoroutinefunction_or_partial is deprecated, "
        "and will be removed in a future release.",
        DeprecationWarning,
    )
    while isinstance(obj, functools.partial):
        obj = obj.func
    return inspect.iscoroutinefunction(obj)


def request_response(
    func: typing.Callable[[Request], typing.Awaitable[Response] | Response],
) -> ASGIApp:
    """
    Takes a function or coroutine `func(request) -> response`,
    and returns an ASGI application.
    """

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive, send)

        async def app(scope: Scope, receive: Receive, send: Send) -> None:
            if is_async_callable(func):
                response = await func(request)
            else:
                response = await run_in_threadpool(func, request)
            await response(scope, receive, send)

        await wrap_app_handling_exceptions(app, request)(scope, receive, send)

    return app


def websocket_session(
    func: typing.Callable[[WebSocket], typing.Awaitable[None]],
) -> ASGIApp:
    """
    Takes a coroutine `func(session)`, and returns an ASGI application.
    """
    # assert asyncio.iscoroutinefunction(func), "WebSocket endpoints must be async"

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        session = WebSocket(scope, receive=receive, send=send)

        async def app(scope: Scope, receive: Receive, send: Send) -> None:
            await func(session)

        await wrap_app_handling_exceptions(app, session)(scope, receive, send)

    return app


def get_name(endpoint: typing.Callable[..., typing.Any]) -> str:
    if inspect.isroutine(endpoint) or inspect.isclass(endpoint):
        return endpoint.__name__
    return endpoint.__class__.__name__


def replace_params(
    path: str,
    param_convertors: dict[str, Convertor[typing.Any]],
    path_params: dict[str, str],
) -> tuple[str, dict[str, str]]:
    for key, value in list(path_params.items()):
        if "{" + key + "}" in path:
            convertor = param_convertors[key]
            value = convertor.to_string(value)
            path = path.replace("{" + key + "}", value)
            path_params.pop(key)
    return path, path_params


# Match parameters in URL paths, eg. '{param}', and '{param:int}'
PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")


def compile_path(
    path: str,
) -> tuple[typing.Pattern[str], str, dict[str, Convertor[typing.Any]]]:
    """
    Given a path string, like: "/{username:str}",
    or a host string, like: "{subdomain}.mydomain.org", return a three-tuple
    of (regex, format, {param_name:convertor}).

    regex:      "/(?P<username>[^/]+)"
    format:     "/{username}"
    convertors: {"username": StringConvertor()}
    """
    is_host = not path.startswith("/")

    path_regex = "^"
    path_format = ""
    duplicated_params = set()

    idx = 0
    param_convertors = {}
    for match in PARAM_REGEX.finditer(path):
        param_name, convertor_type = match.groups("str")
        convertor_type = convertor_type.lstrip(":")
        assert (
            convertor_type in CONVERTOR_TYPES
        ), f"Unknown path convertor '{convertor_type}'"
        convertor = CONVERTOR_TYPES[convertor_type]

        path_regex += re.escape(path[idx : match.start()])
        path_regex += f"(?P<{param_name}>{convertor.regex})"

        path_format += path[idx : match.start()]
        path_format += "{%s}" % param_name

        if param_name in param_convertors:
            duplicated_params.add(param_name)

        param_convertors[param_name] = convertor

        idx = match.end()

    if duplicated_params:
        names = ", ".join(sorted(duplicated_params))
        ending = "s" if len(duplicated_params) > 1 else ""
        raise ValueError(f"Duplicated param name{ending} {names} at path {path}")

    if is_host:
        # Align with `Host.matches()` behavior, which ignores port.
        hostname = path[idx:].split(":")[0]
        path_regex += re.escape(hostname) + "$"
    else:
        path_regex += re.escape(path[idx:]) + "$"

    path_format += path[idx:]

    return re.compile(path_regex), path_format, param_convertors


class BaseRoute:
    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        raise NotImplementedError()  # pragma: no cover

    def url_path_for(self, name: str, /, **path_params: typing.Any) -> URLPath:
        raise NotImplementedError()  # pragma: no cover

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        A route may be used in isolation as a stand-alone ASGI app.
        This is a somewhat contrived case, as they'll almost always be used
        within a Router, but could be useful for some tooling and minimal apps.
        """
        match, child_scope = self.matches(scope)
        if match == Match.NONE:
            if scope["type"] == "http":
                response = PlainTextResponse("Not Found", status_code=404)
                await response(scope, receive, send)
            elif scope["type"] == "websocket":
                websocket_close = WebSocketClose()
                await websocket_close(scope, receive, send)
            return

        scope.update(child_scope)
        await self.handle(scope, receive, send)


class Route(BaseRoute):
    def __init__(
        self,
        path: str,
        endpoint: typing.Callable[..., typing.Any],
        *,
        methods: list[str] | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
        middleware: typing.Sequence[Middleware] | None = None,
    ) -> None:
        assert path.startswith("/"), "Routed paths must start with '/'"
        self.path = path
        self.endpoint = endpoint
        self.name = get_name(endpoint) if name is None else name
        self.include_in_schema = include_in_schema

        endpoint_handler = endpoint
        while isinstance(endpoint_handler, functools.partial):
            endpoint_handler = endpoint_handler.func
        if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
            # Endpoint is function or method. Treat it as `func(request) -> response`.
            self.app = request_response(endpoint)
            if methods is None:
                methods = ["GET"]
        else:
            # Endpoint is a class. Treat it as ASGI.
            self.app = endpoint

        if middleware is not None:
            for cls, args, kwargs in reversed(middleware):
                self.app = cls(app=self.app, *args, **kwargs)

        if methods is None:
            self.methods = None
        else:
            self.methods = {method.upper() for method in methods}
            if "GET" in self.methods:
                self.methods.add("HEAD")

        self.path_regex, self.path_format, self.param_convertors = compile_path(path)

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        path_params: dict[str, typing.Any]
        if scope["type"] == "http":
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                path_params = dict(scope.get("path_params", {}))
                path_params.update(matched_params)
                child_scope = {"endpoint": self.endpoint, "path_params": path_params}
                if self.methods and scope["method"] not in self.methods:
                    return Match.PARTIAL, child_scope
                else:
                    return Match.FULL, child_scope
        return Match.NONE, {}

    def url_path_for(self, name: str, /, **path_params: typing.Any) -> URLPath:
        seen_params = set(path_params.keys())
        expected_params = set(self.param_convertors.keys())

        if name != self.name or seen_params != expected_params:
            raise NoMatchFound(name, path_params)

        path, remaining_params = replace_params(
            self.path_format, self.param_convertors, path_params
        )
        assert not remaining_params
        return URLPath(path=path, protocol="http")

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.methods and scope["method"] not in self.methods:
            headers = {"Allow": ", ".join(self.methods)}
            if "app" in scope:
                raise HTTPException(status_code=405, headers=headers)
            else:
                response = PlainTextResponse(
                    "Method Not Allowed", status_code=405, headers=headers
                )
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, Route)
            and self.path == other.path
            and self.endpoint == other.endpoint
            and self.methods == other.methods
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        methods = sorted(self.methods or [])
        path, name = self.path, self.name
        return f"{class_name}(path={path!r}, name={name!r}, methods={methods!r})"


class WebSocketRoute(BaseRoute):
    def __init__(
        self,
        path: str,
        endpoint: typing.Callable[..., typing.Any],
        *,
        name: str | None = None,
        middleware: typing.Sequence[Middleware] | None = None,
    ) -> None:
        assert path.startswith("/"), "Routed paths must start with '/'"
        self.path = path
        self.endpoint = endpoint
        self.name = get_name(endpoint) if name is None else name

        endpoint_handler = endpoint
        while isinstance(endpoint_handler, functools.partial):
            endpoint_handler = endpoint_handler.func
        if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
            # Endpoint is function or method. Treat it as `func(websocket)`.
            self.app = websocket_session(endpoint)
        else:
            # Endpoint is a class. Treat it as ASGI.
            self.app = endpoint

        if middleware is not None:
            for cls, args, kwargs in reversed(middleware):
                self.app = cls(app=self.app, *args, **kwargs)

        self.path_regex, self.path_format, self.param_convertors = compile_path(path)

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        path_params: dict[str, typing.Any]
        if scope["type"] == "websocket":
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                path_params = dict(scope.get("path_params", {}))
                path_params.update(matched_params)
                child_scope = {"endpoint": self.endpoint, "path_params": path_params}
                return Match.FULL, child_scope
        return Match.NONE, {}

    def url_path_for(self, name: str, /, **path_params: typing.Any) -> URLPath:
        seen_params = set(path_params.keys())
        expected_params = set(self.param_convertors.keys())

        if name != self.name or seen_params != expected_params:
            raise NoMatchFound(name, path_params)

        path, remaining_params = replace_params(
            self.path_format, self.param_convertors, path_params
        )
        assert not remaining_params
        return URLPath(path=path, protocol="websocket")

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, WebSocketRoute)
            and self.path == other.path
            and self.endpoint == other.endpoint
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self.path!r}, name={self.name!r})"


class Mount(BaseRoute):
    def __init__(
        self,
        path: str,
        app: ASGIApp | None = None,
        routes: typing.Sequence[BaseRoute] | None = None,
        name: str | None = None,
        *,
        middleware: typing.Sequence[Middleware] | None = None,
    ) -> None:
        assert path == "" or path.startswith("/"), "Routed paths must start with '/'"
        assert (
            app is not None or routes is not None
        ), "Either 'app=...', or 'routes=' must be specified"
        self.path = path.rstrip("/")
        if app is not None:
            self._base_app: ASGIApp = app
        else:
            self._base_app = Router(routes=routes)
        self.app = self._base_app
        if middleware is not None:
            for cls, args, kwargs in reversed(middleware):
                self.app = cls(app=self.app, *args, **kwargs)
        self.name = name
        self.path_regex, self.path_format, self.param_convertors = compile_path(
            self.path + "/{path:path}"
        )

    @property
    def routes(self) -> list[BaseRoute]:
        return getattr(self._base_app, "routes", [])

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        path_params: dict[str, typing.Any]
        if scope["type"] in ("http", "websocket"):
            root_path = scope.get("root_path", "")
            route_path = get_route_path(scope)
            match = self.path_regex.match(route_path)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                remaining_path = "/" + matched_params.pop("path")
                matched_path = route_path[: -len(remaining_path)]
                path_params = dict(scope.get("path_params", {}))
                path_params.update(matched_params)
                child_scope = {
                    "path_params": path_params,
                    # app_root_path will only be set at the top level scope,
                    # initialized with the (optional) value of a root_path
                    # set above/before Starlette. And even though any
                    # mount will have its own child scope with its own respective
                    # root_path, the app_root_path will always be available in all
                    # the child scopes with the same top level value because it's
                    # set only once here with a default, any other child scope will
                    # just inherit that app_root_path default value stored in the
                    # scope. All this is needed to support Request.url_for(), as it
                    # uses the app_root_path to build the URL path.
                    "app_root_path": scope.get("app_root_path", root_path),
                    "root_path": root_path + matched_path,
                    "endpoint": self.app,
                }
                return Match.FULL, child_scope
        return Match.NONE, {}

    def url_path_for(self, name: str, /, **path_params: typing.Any) -> URLPath:
        if self.name is not None and name == self.name and "path" in path_params:
            # 'name' matches "<mount_name>".
            path_params["path"] = path_params["path"].lstrip("/")
            path, remaining_params = replace_params(
                self.path_format, self.param_convertors, path_params
            )
            if not remaining_params:
                return URLPath(path=path)
        elif self.name is None or name.startswith(self.name + ":"):
            if self.name is None:
                # No mount name.
                remaining_name = name
            else:
                # 'name' matches "<mount_name>:<child_name>".
                remaining_name = name[len(self.name) + 1 :]
            path_kwarg = path_params.get("path")
            path_params["path"] = ""
            path_prefix, remaining_params = replace_params(
                self.path_format, self.param_convertors, path_params
            )
            if path_kwarg is not None:
                remaining_params["path"] = path_kwarg
            for route in self.routes or []:
                try:
                    url = route.url_path_for(remaining_name, **remaining_params)
                    return URLPath(
                        path=path_prefix.rstrip("/") + str(url), protocol=url.protocol
                    )
                except NoMatchFound:
                    pass
        raise NoMatchFound(name, path_params)

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, Mount)
            and self.path == other.path
            and self.app == other.app
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        name = self.name or ""
        return f"{class_name}(path={self.path!r}, name={name!r}, app={self.app!r})"


class Host(BaseRoute):
    def __init__(self, host: str, app: ASGIApp, name: str | None = None) -> None:
        assert not host.startswith("/"), "Host must not start with '/'"
        self.host = host
        self.app = app
        self.name = name
        self.host_regex, self.host_format, self.param_convertors = compile_path(host)

    @property
    def routes(self) -> list[BaseRoute]:
        return getattr(self.app, "routes", [])

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        if scope["type"] in ("http", "websocket"):
            headers = Headers(scope=scope)
            host = headers.get("host", "").split(":")[0]
            match = self.host_regex.match(host)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                path_params = dict(scope.get("path_params", {}))
                path_params.update(matched_params)
                child_scope = {"path_params": path_params, "endpoint": self.app}
                return Match.FULL, child_scope
        return Match.NONE, {}

    def url_path_for(self, name: str, /, **path_params: typing.Any) -> URLPath:
        if self.name is not None and name == self.name and "path" in path_params:
            # 'name' matches "<mount_name>".
            path = path_params.pop("path")
            host, remaining_params = replace_params(
                self.host_format, self.param_convertors, path_params
            )
            if not remaining_params:
                return URLPath(path=path, host=host)
        elif self.name is None or name.startswith(self.name + ":"):
            if self.name is None:
                # No mount name.
                remaining_name = name
            else:
                # 'name' matches "<mount_name>:<child_name>".
                remaining_name = name[len(self.name) + 1 :]
            host, remaining_params = replace_params(
                self.host_format, self.param_convertors, path_params
            )
            for route in self.routes or []:
                try:
                    url = route.url_path_for(remaining_name, **remaining_params)
                    return URLPath(path=str(url), protocol=url.protocol, host=host)
                except NoMatchFound:
                    pass
        raise NoMatchFound(name, path_params)

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, Host)
            and self.host == other.host
            and self.app == other.app
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        name = self.name or ""
        return f"{class_name}(host={self.host!r}, name={name!r}, app={self.app!r})"


_T = typing.TypeVar("_T")


class _AsyncLiftContextManager(typing.AsyncContextManager[_T]):
    def __init__(self, cm: typing.ContextManager[_T]):
        self._cm = cm

    async def __aenter__(self) -> _T:
        return self._cm.__enter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> bool | None:
        return self._cm.__exit__(exc_type, exc_value, traceback)


def _wrap_gen_lifespan_context(
    lifespan_context: typing.Callable[
        [typing.Any], typing.Generator[typing.Any, typing.Any, typing.Any]
    ],
) -> typing.Callable[[typing.Any], typing.AsyncContextManager[typing.Any]]:
    cmgr = contextlib.contextmanager(lifespan_context)

    @functools.wraps(cmgr)
    def wrapper(app: typing.Any) -> _AsyncLiftContextManager[typing.Any]:
        return _AsyncLiftContextManager(cmgr(app))

    return wrapper


class _DefaultLifespan:
    def __init__(self, router: Router):
        self._router = router

    async def __aenter__(self) -> None:
        await self._router.startup()

    async def __aexit__(self, *exc_info: object) -> None:
        await self._router.shutdown()

    def __call__(self: _T, app: object) -> _T:
        return self


class Router:
    def __init__(
        self,
        routes: typing.Sequence[BaseRoute] | None = None,
        redirect_slashes: bool = True,
        default: ASGIApp | None = None,
        on_startup: typing.Sequence[typing.Callable[[], typing.Any]] | None = None,
        on_shutdown: typing.Sequence[typing.Callable[[], typing.Any]] | None = None,
        # the generic to Lifespan[AppType] is the type of the top level application
        # which the router cannot know statically, so we use typing.Any
        lifespan: Lifespan[typing.Any] | None = None,
        *,
        middleware: typing.Sequence[Middleware] | None = None,
    ) -> None:
        self.routes = [] if routes is None else list(routes)
        self.redirect_slashes = redirect_slashes
        self.default = self.not_found if default is None else default
        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)

        if on_startup or on_shutdown:
            warnings.warn(
                "The on_startup and on_shutdown parameters are deprecated, and they "
                "will be removed on version 1.0. Use the lifespan parameter instead. "
                "See more about it on https://www.starlette.io/lifespan/.",
                DeprecationWarning,
            )
            if lifespan:
                warnings.warn(
                    "The `lifespan` parameter cannot be used with `on_startup` or "
                    "`on_shutdown`. Both `on_startup` and `on_shutdown` will be "
                    "ignored."
                )

        if lifespan is None:
            self.lifespan_context: Lifespan[typing.Any] = _DefaultLifespan(self)

        elif inspect.isasyncgenfunction(lifespan):
            warnings.warn(
                "async generator function lifespans are deprecated, "
                "use an @contextlib.asynccontextmanager function instead",
                DeprecationWarning,
            )
            self.lifespan_context = asynccontextmanager(
                lifespan,
            )
        elif inspect.isgeneratorfunction(lifespan):
            warnings.warn(
                "generator function lifespans are deprecated, "
                "use an @contextlib.asynccontextmanager function instead",
                DeprecationWarning,
            )
            self.lifespan_context = _wrap_gen_lifespan_context(
                lifespan,
            )
        else:
            self.lifespan_context = lifespan

        self.middleware_stack = self.app
        if middleware:
            for cls, args, kwargs in reversed(middleware):
                self.middleware_stack = cls(self.middleware_stack, *args, **kwargs)

    async def not_found(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            websocket_close = WebSocketClose()
            await websocket_close(scope, receive, send)
            return

        # If we're running inside a starlette application then raise an
        # exception, so that the configurable exception handler can deal with
        # returning the response. For plain ASGI apps, just return the response.
        if "app" in scope:
            raise HTTPException(status_code=404)
        else:
            response = PlainTextResponse("Not Found", status_code=404)
        await response(scope, receive, send)

    def url_path_for(self, name: str, /, **path_params: typing.Any) -> URLPath:
        for route in self.routes:
            try:
                return route.url_path_for(name, **path_params)
            except NoMatchFound:
                pass
        raise NoMatchFound(name, path_params)

    async def startup(self) -> None:
        """
        Run any `.on_startup` event handlers.
        """
        for handler in self.on_startup:
            if is_async_callable(handler):
                await handler()
            else:
                handler()

    async def shutdown(self) -> None:
        """
        Run any `.on_shutdown` event handlers.
        """
        for handler in self.on_shutdown:
            if is_async_callable(handler):
                await handler()
            else:
                handler()

    async def lifespan(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handle ASGI lifespan messages, which allows us to manage application
        startup and shutdown events.
        """
        started = False
        app: typing.Any = scope.get("app")
        await receive()
        try:
            async with self.lifespan_context(app) as maybe_state:
                if maybe_state is not None:
                    if "state" not in scope:
                        raise RuntimeError(
                            'The server does not support "state" in the lifespan scope.'
                        )
                    scope["state"].update(maybe_state)
                await send({"type": "lifespan.startup.complete"})
                started = True
                await receive()
        except BaseException:
            exc_text = traceback.format_exc()
            if started:
                await send({"type": "lifespan.shutdown.failed", "message": exc_text})
            else:
                await send({"type": "lifespan.startup.failed", "message": exc_text})
            raise
        else:
            await send({"type": "lifespan.shutdown.complete"})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        The main entry point to the Router class.
        """
        await self.middleware_stack(scope, receive, send)

    async def app(self, scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["type"] in ("http", "websocket", "lifespan")

        if "router" not in scope:
            scope["router"] = self

        if scope["type"] == "lifespan":
            await self.lifespan(scope, receive, send)
            return

        partial = None

        for route in self.routes:
            # Determine if any route matches the incoming scope,
            # and hand over to the matching route if found.
            match, child_scope = route.matches(scope)
            if match == Match.FULL:
                scope.update(child_scope)
                await route.handle(scope, receive, send)
                return
            elif match == Match.PARTIAL and partial is None:
                partial = route
                partial_scope = child_scope

        if partial is not None:
            #  Handle partial matches. These are cases where an endpoint is
            # able to handle the request, but is not a preferred option.
            # We use this in particular to deal with "405 Method Not Allowed".
            scope.update(partial_scope)
            await partial.handle(scope, receive, send)
            return

        route_path = get_route_path(scope)
        if scope["type"] == "http" and self.redirect_slashes and route_path != "/":
            redirect_scope = dict(scope)
            if route_path.endswith("/"):
                redirect_scope["path"] = redirect_scope["path"].rstrip("/")
            else:
                redirect_scope["path"] = redirect_scope["path"] + "/"

            for route in self.routes:
                match, child_scope = route.matches(redirect_scope)
                if match != Match.NONE:
                    redirect_url = URL(scope=redirect_scope)
                    response = RedirectResponse(url=str(redirect_url))
                    await response(scope, receive, send)
                    return

        await self.default(scope, receive, send)

    def __eq__(self, other: typing.Any) -> bool:
        return isinstance(other, Router) and self.routes == other.routes

    def mount(
        self, path: str, app: ASGIApp, name: str | None = None
    ) -> None:  # pragma: nocover
        route = Mount(path, app=app, name=name)
        self.routes.append(route)

    def host(
        self, host: str, app: ASGIApp, name: str | None = None
    ) -> None:  # pragma: no cover
        route = Host(host, app=app, name=name)
        self.routes.append(route)

    def add_route(
        self,
        path: str,
        endpoint: typing.Callable[[Request], typing.Awaitable[Response] | Response],
        methods: list[str] | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
    ) -> None:  # pragma: nocover
        route = Route(
            path,
            endpoint=endpoint,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
        )
        self.routes.append(route)

    def add_websocket_route(
        self,
        path: str,
        endpoint: typing.Callable[[WebSocket], typing.Awaitable[None]],
        name: str | None = None,
    ) -> None:  # pragma: no cover
        route = WebSocketRoute(path, endpoint=endpoint, name=name)
        self.routes.append(route)

    def route(
        self,
        path: str,
        methods: list[str] | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
    ) -> typing.Callable:  # type: ignore[type-arg]
        """
        We no longer document this decorator style API, and its usage is discouraged.
        Instead you should use the following approach:

        >>> routes = [Route(path, endpoint=...), ...]
        >>> app = Starlette(routes=routes)
        """
        warnings.warn(
            "The `route` decorator is deprecated, and will be removed in version 1.0.0."
            "Refer to https://www.starlette.io/routing/#http-routing for the recommended approach.",  # noqa: E501
            DeprecationWarning,
        )

        def decorator(func: typing.Callable) -> typing.Callable:  # type: ignore[type-arg]  # noqa: E501
            self.add_route(
                path,
                func,
                methods=methods,
                name=name,
                include_in_schema=include_in_schema,
            )
            return func

        return decorator

    def websocket_route(self, path: str, name: str | None = None) -> typing.Callable:  # type: ignore[type-arg]
        """
        We no longer document this decorator style API, and its usage is discouraged.
        Instead you should use the following approach:

        >>> routes = [WebSocketRoute(path, endpoint=...), ...]
        >>> app = Starlette(routes=routes)
        """
        warnings.warn(
            "The `websocket_route` decorator is deprecated, and will be removed in version 1.0.0. Refer to "  # noqa: E501
            "https://www.starlette.io/routing/#websocket-routing for the recommended approach.",  # noqa: E501
            DeprecationWarning,
        )

        def decorator(func: typing.Callable) -> typing.Callable:  # type: ignore[type-arg]  # noqa: E501
            self.add_websocket_route(path, func, name=name)
            return func

        return decorator

    def add_event_handler(
        self, event_type: str, func: typing.Callable[[], typing.Any]
    ) -> None:  # pragma: no cover
        assert event_type in ("startup", "shutdown")

        if event_type == "startup":
            self.on_startup.append(func)
        else:
            self.on_shutdown.append(func)

    def on_event(self, event_type: str) -> typing.Callable:  # type: ignore[type-arg]
        warnings.warn(
            "The `on_event` decorator is deprecated, and will be removed in version 1.0.0. "  # noqa: E501
            "Refer to https://www.starlette.io/lifespan/ for recommended approach.",
            DeprecationWarning,
        )

        def decorator(func: typing.Callable) -> typing.Callable:  # type: ignore[type-arg]  # noqa: E501
            self.add_event_handler(event_type, func)
            return func

        return decorator

# === NexusCore/openenv\Lib\site-packages\PIL\ImageFile.py ===
#
# The Python Imaging Library.
# $Id$
#
# base class for image file handlers
#
# history:
# 1995-09-09 fl   Created
# 1996-03-11 fl   Fixed load mechanism.
# 1996-04-15 fl   Added pcx/xbm decoders.
# 1996-04-30 fl   Added encoders.
# 1996-12-14 fl   Added load helpers
# 1997-01-11 fl   Use encode_to_file where possible
# 1997-08-27 fl   Flush output in _save
# 1998-03-05 fl   Use memory mapping for some modes
# 1999-02-04 fl   Use memory mapping also for "I;16" and "I;16B"
# 1999-05-31 fl   Added image parser
# 2000-10-12 fl   Set readonly flag on memory-mapped images
# 2002-03-20 fl   Use better messages for common decoder errors
# 2003-04-21 fl   Fall back on mmap/map_buffer if map is not available
# 2003-10-30 fl   Added StubImageFile class
# 2004-02-25 fl   Made incremental parser more robust
#
# Copyright (c) 1997-2004 by Secret Labs AB
# Copyright (c) 1995-2004 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import abc
import io
import itertools
import logging
import os
import struct
from typing import IO, Any, NamedTuple, cast

from . import ExifTags, Image
from ._deprecate import deprecate
from ._util import DeferredError, is_path

TYPE_CHECKING = False
if TYPE_CHECKING:
    from ._typing import StrOrBytesPath

logger = logging.getLogger(__name__)

MAXBLOCK = 65536

SAFEBLOCK = 1024 * 1024

LOAD_TRUNCATED_IMAGES = False
"""Whether or not to load truncated image files. User code may change this."""

ERRORS = {
    -1: "image buffer overrun error",
    -2: "decoding error",
    -3: "unknown error",
    -8: "bad configuration",
    -9: "out of memory error",
}
"""
Dict of known error codes returned from :meth:`.PyDecoder.decode`,
:meth:`.PyEncoder.encode` :meth:`.PyEncoder.encode_to_pyfd` and
:meth:`.PyEncoder.encode_to_file`.
"""


#
# --------------------------------------------------------------------
# Helpers


def _get_oserror(error: int, *, encoder: bool) -> OSError:
    try:
        msg = Image.core.getcodecstatus(error)
    except AttributeError:
        msg = ERRORS.get(error)
    if not msg:
        msg = f"{'encoder' if encoder else 'decoder'} error {error}"
    msg += f" when {'writing' if encoder else 'reading'} image file"
    return OSError(msg)


def raise_oserror(error: int) -> OSError:
    deprecate(
        "raise_oserror",
        12,
        action="It is only useful for translating error codes returned by a codec's "
        "decode() method, which ImageFile already does automatically.",
    )
    raise _get_oserror(error, encoder=False)


def _tilesort(t: _Tile) -> int:
    # sort on offset
    return t[2]


class _Tile(NamedTuple):
    codec_name: str
    extents: tuple[int, int, int, int] | None
    offset: int = 0
    args: tuple[Any, ...] | str | None = None


#
# --------------------------------------------------------------------
# ImageFile base class


class ImageFile(Image.Image):
    """Base class for image file format handlers."""

    def __init__(
        self, fp: StrOrBytesPath | IO[bytes], filename: str | bytes | None = None
    ) -> None:
        super().__init__()

        self._min_frame = 0

        self.custom_mimetype: str | None = None

        self.tile: list[_Tile] = []
        """ A list of tile descriptors """

        self.readonly = 1  # until we know better

        self.decoderconfig: tuple[Any, ...] = ()
        self.decodermaxblock = MAXBLOCK

        if is_path(fp):
            # filename
            self.fp = open(fp, "rb")
            self.filename = os.fspath(fp)
            self._exclusive_fp = True
        else:
            # stream
            self.fp = cast(IO[bytes], fp)
            self.filename = filename if filename is not None else ""
            # can be overridden
            self._exclusive_fp = False

        try:
            try:
                self._open()
            except (
                IndexError,  # end of data
                TypeError,  # end of data (ord)
                KeyError,  # unsupported mode
                EOFError,  # got header but not the first frame
                struct.error,
            ) as v:
                raise SyntaxError(v) from v

            if not self.mode or self.size[0] <= 0 or self.size[1] <= 0:
                msg = "not identified by this driver"
                raise SyntaxError(msg)
        except BaseException:
            # close the file only if we have opened it this constructor
            if self._exclusive_fp:
                self.fp.close()
            raise

    def _open(self) -> None:
        pass

    def _close_fp(self):
        if getattr(self, "_fp", False) and not isinstance(self._fp, DeferredError):
            if self._fp != self.fp:
                self._fp.close()
            self._fp = DeferredError(ValueError("Operation on closed image"))
        if self.fp:
            self.fp.close()

    def close(self) -> None:
        """
        Closes the file pointer, if possible.

        This operation will destroy the image core and release its memory.
        The image data will be unusable afterward.

        This function is required to close images that have multiple frames or
        have not had their file read and closed by the
        :py:meth:`~PIL.Image.Image.load` method. See :ref:`file-handling` for
        more information.
        """
        try:
            self._close_fp()
            self.fp = None
        except Exception as msg:
            logger.debug("Error closing: %s", msg)

        super().close()

    def get_child_images(self) -> list[ImageFile]:
        child_images = []
        exif = self.getexif()
        ifds = []
        if ExifTags.Base.SubIFDs in exif:
            subifd_offsets = exif[ExifTags.Base.SubIFDs]
            if subifd_offsets:
                if not isinstance(subifd_offsets, tuple):
                    subifd_offsets = (subifd_offsets,)
                for subifd_offset in subifd_offsets:
                    ifds.append((exif._get_ifd_dict(subifd_offset), subifd_offset))
        ifd1 = exif.get_ifd(ExifTags.IFD.IFD1)
        if ifd1 and ifd1.get(ExifTags.Base.JpegIFOffset):
            assert exif._info is not None
            ifds.append((ifd1, exif._info.next))

        offset = None
        for ifd, ifd_offset in ifds:
            assert self.fp is not None
            current_offset = self.fp.tell()
            if offset is None:
                offset = current_offset

            fp = self.fp
            if ifd is not None:
                thumbnail_offset = ifd.get(ExifTags.Base.JpegIFOffset)
                if thumbnail_offset is not None:
                    thumbnail_offset += getattr(self, "_exif_offset", 0)
                    self.fp.seek(thumbnail_offset)

                    length = ifd.get(ExifTags.Base.JpegIFByteCount)
                    assert isinstance(length, int)
                    data = self.fp.read(length)
                    fp = io.BytesIO(data)

            with Image.open(fp) as im:
                from . import TiffImagePlugin

                if thumbnail_offset is None and isinstance(
                    im, TiffImagePlugin.TiffImageFile
                ):
                    im._frame_pos = [ifd_offset]
                    im._seek(0)
                im.load()
                child_images.append(im)

        if offset is not None:
            assert self.fp is not None
            self.fp.seek(offset)
        return child_images

    def get_format_mimetype(self) -> str | None:
        if self.custom_mimetype:
            return self.custom_mimetype
        if self.format is not None:
            return Image.MIME.get(self.format.upper())
        return None

    def __getstate__(self) -> list[Any]:
        return super().__getstate__() + [self.filename]

    def __setstate__(self, state: list[Any]) -> None:
        self.tile = []
        self.filename = state[5]
        super().__setstate__(state)

    def verify(self) -> None:
        """Check file integrity"""

        # raise exception if something's wrong.  must be called
        # directly after open, and closes file when finished.
        if self._exclusive_fp:
            self.fp.close()
        self.fp = None

    def load(self) -> Image.core.PixelAccess | None:
        """Load image data based on tile list"""

        if not self.tile and self._im is None:
            msg = "cannot load this image"
            raise OSError(msg)

        pixel = Image.Image.load(self)
        if not self.tile:
            return pixel

        self.map: mmap.mmap | None = None
        use_mmap = self.filename and len(self.tile) == 1

        readonly = 0

        # look for read/seek overrides
        if hasattr(self, "load_read"):
            read = self.load_read
            # don't use mmap if there are custom read/seek functions
            use_mmap = False
        else:
            read = self.fp.read

        if hasattr(self, "load_seek"):
            seek = self.load_seek
            use_mmap = False
        else:
            seek = self.fp.seek

        if use_mmap:
            # try memory mapping
            decoder_name, extents, offset, args = self.tile[0]
            if isinstance(args, str):
                args = (args, 0, 1)
            if (
                decoder_name == "raw"
                and isinstance(args, tuple)
                and len(args) >= 3
                and args[0] == self.mode
                and args[0] in Image._MAPMODES
            ):
                try:
                    # use mmap, if possible
                    import mmap

                    with open(self.filename) as fp:
                        self.map = mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ)
                    if offset + self.size[1] * args[1] > self.map.size():
                        msg = "buffer is not large enough"
                        raise OSError(msg)
                    self.im = Image.core.map_buffer(
                        self.map, self.size, decoder_name, offset, args
                    )
                    readonly = 1
                    # After trashing self.im,
                    # we might need to reload the palette data.
                    if self.palette:
                        self.palette.dirty = 1
                except (AttributeError, OSError, ImportError):
                    self.map = None

        self.load_prepare()
        err_code = -3  # initialize to unknown error
        if not self.map:
            # sort tiles in file order
            self.tile.sort(key=_tilesort)

            # FIXME: This is a hack to handle TIFF's JpegTables tag.
            prefix = getattr(self, "tile_prefix", b"")

            # Remove consecutive duplicates that only differ by their offset
            self.tile = [
                list(tiles)[-1]
                for _, tiles in itertools.groupby(
                    self.tile, lambda tile: (tile[0], tile[1], tile[3])
                )
            ]
            for i, (decoder_name, extents, offset, args) in enumerate(self.tile):
                seek(offset)
                decoder = Image._getdecoder(
                    self.mode, decoder_name, args, self.decoderconfig
                )
                try:
                    decoder.setimage(self.im, extents)
                    if decoder.pulls_fd:
                        decoder.setfd(self.fp)
                        err_code = decoder.decode(b"")[1]
                    else:
                        b = prefix
                        while True:
                            read_bytes = self.decodermaxblock
                            if i + 1 < len(self.tile):
                                next_offset = self.tile[i + 1].offset
                                if next_offset > offset:
                                    read_bytes = next_offset - offset
                            try:
                                s = read(read_bytes)
                            except (IndexError, struct.error) as e:
                                # truncated png/gif
                                if LOAD_TRUNCATED_IMAGES:
                                    break
                                else:
                                    msg = "image file is truncated"
                                    raise OSError(msg) from e

                            if not s:  # truncated jpeg
                                if LOAD_TRUNCATED_IMAGES:
                                    break
                                else:
                                    msg = (
                                        "image file is truncated "
                                        f"({len(b)} bytes not processed)"
                                    )
                                    raise OSError(msg)

                            b = b + s
                            n, err_code = decoder.decode(b)
                            if n < 0:
                                break
                            b = b[n:]
                finally:
                    # Need to cleanup here to prevent leaks
                    decoder.cleanup()

        self.tile = []
        self.readonly = readonly

        self.load_end()

        if self._exclusive_fp and self._close_exclusive_fp_after_loading:
            self.fp.close()
        self.fp = None

        if not self.map and not LOAD_TRUNCATED_IMAGES and err_code < 0:
            # still raised if decoder fails to return anything
            raise _get_oserror(err_code, encoder=False)

        return Image.Image.load(self)

    def load_prepare(self) -> None:
        # create image memory if necessary
        if self._im is None:
            self.im = Image.core.new(self.mode, self.size)
        # create palette (optional)
        if self.mode == "P":
            Image.Image.load(self)

    def load_end(self) -> None:
        # may be overridden
        pass

    # may be defined for contained formats
    # def load_seek(self, pos: int) -> None:
    #     pass

    # may be defined for blocked formats (e.g. PNG)
    # def load_read(self, read_bytes: int) -> bytes:
    #     pass

    def _seek_check(self, frame: int) -> bool:
        if (
            frame < self._min_frame
            # Only check upper limit on frames if additional seek operations
            # are not required to do so
            or (
                not (hasattr(self, "_n_frames") and self._n_frames is None)
                and frame >= getattr(self, "n_frames") + self._min_frame
            )
        ):
            msg = "attempt to seek outside sequence"
            raise EOFError(msg)

        return self.tell() != frame


class StubHandler(abc.ABC):
    def open(self, im: StubImageFile) -> None:
        pass

    @abc.abstractmethod
    def load(self, im: StubImageFile) -> Image.Image:
        pass


class StubImageFile(ImageFile, metaclass=abc.ABCMeta):
    """
    Base class for stub image loaders.

    A stub loader is an image loader that can identify files of a
    certain format, but relies on external code to load the file.
    """

    @abc.abstractmethod
    def _open(self) -> None:
        pass

    def load(self) -> Image.core.PixelAccess | None:
        loader = self._load()
        if loader is None:
            msg = f"cannot find loader for this {self.format} file"
            raise OSError(msg)
        image = loader.load(self)
        assert image is not None
        # become the other object (!)
        self.__class__ = image.__class__  # type: ignore[assignment]
        self.__dict__ = image.__dict__
        return image.load()

    @abc.abstractmethod
    def _load(self) -> StubHandler | None:
        """(Hook) Find actual image loader."""
        pass


class Parser:
    """
    Incremental image parser.  This class implements the standard
    feed/close consumer interface.
    """

    incremental = None
    image: Image.Image | None = None
    data: bytes | None = None
    decoder: Image.core.ImagingDecoder | PyDecoder | None = None
    offset = 0
    finished = 0

    def reset(self) -> None:
        """
        (Consumer) Reset the parser.  Note that you can only call this
        method immediately after you've created a parser; parser
        instances cannot be reused.
        """
        assert self.data is None, "cannot reuse parsers"

    def feed(self, data: bytes) -> None:
        """
        (Consumer) Feed data to the parser.

        :param data: A string buffer.
        :exception OSError: If the parser failed to parse the image file.
        """
        # collect data

        if self.finished:
            return

        if self.data is None:
            self.data = data
        else:
            self.data = self.data + data

        # parse what we have
        if self.decoder:
            if self.offset > 0:
                # skip header
                skip = min(len(self.data), self.offset)
                self.data = self.data[skip:]
                self.offset = self.offset - skip
                if self.offset > 0 or not self.data:
                    return

            n, e = self.decoder.decode(self.data)

            if n < 0:
                # end of stream
                self.data = None
                self.finished = 1
                if e < 0:
                    # decoding error
                    self.image = None
                    raise _get_oserror(e, encoder=False)
                else:
                    # end of image
                    return
            self.data = self.data[n:]

        elif self.image:
            # if we end up here with no decoder, this file cannot
            # be incrementally parsed.  wait until we've gotten all
            # available data
            pass

        else:
            # attempt to open this file
            try:
                with io.BytesIO(self.data) as fp:
                    im = Image.open(fp)
            except OSError:
                pass  # not enough data
            else:
                flag = hasattr(im, "load_seek") or hasattr(im, "load_read")
                if flag or len(im.tile) != 1:
                    # custom load code, or multiple tiles
                    self.decode = None
                else:
                    # initialize decoder
                    im.load_prepare()
                    d, e, o, a = im.tile[0]
                    im.tile = []
                    self.decoder = Image._getdecoder(im.mode, d, a, im.decoderconfig)
                    self.decoder.setimage(im.im, e)

                    # calculate decoder offset
                    self.offset = o
                    if self.offset <= len(self.data):
                        self.data = self.data[self.offset :]
                        self.offset = 0

                self.image = im

    def __enter__(self) -> Parser:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> Image.Image:
        """
        (Consumer) Close the stream.

        :returns: An image object.
        :exception OSError: If the parser failed to parse the image file either
                            because it cannot be identified or cannot be
                            decoded.
        """
        # finish decoding
        if self.decoder:
            # get rid of what's left in the buffers
            self.feed(b"")
            self.data = self.decoder = None
            if not self.finished:
                msg = "image was incomplete"
                raise OSError(msg)
        if not self.image:
            msg = "cannot parse this image"
            raise OSError(msg)
        if self.data:
            # incremental parsing not possible; reopen the file
            # not that we have all data
            with io.BytesIO(self.data) as fp:
                try:
                    self.image = Image.open(fp)
                finally:
                    self.image.load()
        return self.image


# --------------------------------------------------------------------


def _save(im: Image.Image, fp: IO[bytes], tile: list[_Tile], bufsize: int = 0) -> None:
    """Helper to save image based on tile list

    :param im: Image object.
    :param fp: File object.
    :param tile: Tile list.
    :param bufsize: Optional buffer size
    """

    im.load()
    if not hasattr(im, "encoderconfig"):
        im.encoderconfig = ()
    tile.sort(key=_tilesort)
    # FIXME: make MAXBLOCK a configuration parameter
    # It would be great if we could have the encoder specify what it needs
    # But, it would need at least the image size in most cases. RawEncode is
    # a tricky case.
    bufsize = max(MAXBLOCK, bufsize, im.size[0] * 4)  # see RawEncode.c
    try:
        fh = fp.fileno()
        fp.flush()
        _encode_tile(im, fp, tile, bufsize, fh)
    except (AttributeError, io.UnsupportedOperation) as exc:
        _encode_tile(im, fp, tile, bufsize, None, exc)
    if hasattr(fp, "flush"):
        fp.flush()


def _encode_tile(
    im: Image.Image,
    fp: IO[bytes],
    tile: list[_Tile],
    bufsize: int,
    fh: int | None,
    exc: BaseException | None = None,
) -> None:
    for encoder_name, extents, offset, args in tile:
        if offset > 0:
            fp.seek(offset)
        encoder = Image._getencoder(im.mode, encoder_name, args, im.encoderconfig)
        try:
            encoder.setimage(im.im, extents)
            if encoder.pushes_fd:
                encoder.setfd(fp)
                errcode = encoder.encode_to_pyfd()[1]
            else:
                if exc:
                    # compress to Python file-compatible object
                    while True:
                        errcode, data = encoder.encode(bufsize)[1:]
                        fp.write(data)
                        if errcode:
                            break
                else:
                    # slight speedup: compress to real file object
                    assert fh is not None
                    errcode = encoder.encode_to_file(fh, bufsize)
            if errcode < 0:
                raise _get_oserror(errcode, encoder=True) from exc
        finally:
            encoder.cleanup()


def _safe_read(fp: IO[bytes], size: int) -> bytes:
    """
    Reads large blocks in a safe way.  Unlike fp.read(n), this function
    doesn't trust the user.  If the requested size is larger than
    SAFEBLOCK, the file is read block by block.

    :param fp: File handle.  Must implement a <b>read</b> method.
    :param size: Number of bytes to read.
    :returns: A string containing <i>size</i> bytes of data.

    Raises an OSError if the file is truncated and the read cannot be completed

    """
    if size <= 0:
        return b""
    if size <= SAFEBLOCK:
        data = fp.read(size)
        if len(data) < size:
            msg = "Truncated File Read"
            raise OSError(msg)
        return data
    blocks: list[bytes] = []
    remaining_size = size
    while remaining_size > 0:
        block = fp.read(min(remaining_size, SAFEBLOCK))
        if not block:
            break
        blocks.append(block)
        remaining_size -= len(block)
    if sum(len(block) for block in blocks) < size:
        msg = "Truncated File Read"
        raise OSError(msg)
    return b"".join(blocks)


class PyCodecState:
    def __init__(self) -> None:
        self.xsize = 0
        self.ysize = 0
        self.xoff = 0
        self.yoff = 0

    def extents(self) -> tuple[int, int, int, int]:
        return self.xoff, self.yoff, self.xoff + self.xsize, self.yoff + self.ysize


class PyCodec:
    fd: IO[bytes] | None

    def __init__(self, mode: str, *args: Any) -> None:
        self.im: Image.core.ImagingCore | None = None
        self.state = PyCodecState()
        self.fd = None
        self.mode = mode
        self.init(args)

    def init(self, args: tuple[Any, ...]) -> None:
        """
        Override to perform codec specific initialization

        :param args: Tuple of arg items from the tile entry
        :returns: None
        """
        self.args = args

    def cleanup(self) -> None:
        """
        Override to perform codec specific cleanup

        :returns: None
        """
        pass

    def setfd(self, fd: IO[bytes]) -> None:
        """
        Called from ImageFile to set the Python file-like object

        :param fd: A Python file-like object
        :returns: None
        """
        self.fd = fd

    def setimage(
        self,
        im: Image.core.ImagingCore,
        extents: tuple[int, int, int, int] | None = None,
    ) -> None:
        """
        Called from ImageFile to set the core output image for the codec

        :param im: A core image object
        :param extents: a 4 tuple of (x0, y0, x1, y1) defining the rectangle
            for this tile
        :returns: None
        """

        # following c code
        self.im = im

        if extents:
            (x0, y0, x1, y1) = extents
        else:
            (x0, y0, x1, y1) = (0, 0, 0, 0)

        if x0 == 0 and x1 == 0:
            self.state.xsize, self.state.ysize = self.im.size
        else:
            self.state.xoff = x0
            self.state.yoff = y0
            self.state.xsize = x1 - x0
            self.state.ysize = y1 - y0

        if self.state.xsize <= 0 or self.state.ysize <= 0:
            msg = "Size cannot be negative"
            raise ValueError(msg)

        if (
            self.state.xsize + self.state.xoff > self.im.size[0]
            or self.state.ysize + self.state.yoff > self.im.size[1]
        ):
            msg = "Tile cannot extend outside image"
            raise ValueError(msg)


class PyDecoder(PyCodec):
    """
    Python implementation of a format decoder. Override this class and
    add the decoding logic in the :meth:`decode` method.

    See :ref:`Writing Your Own File Codec in Python<file-codecs-py>`
    """

    _pulls_fd = False

    @property
    def pulls_fd(self) -> bool:
        return self._pulls_fd

    def decode(self, buffer: bytes | Image.SupportsArrayInterface) -> tuple[int, int]:
        """
        Override to perform the decoding process.

        :param buffer: A bytes object with the data to be decoded.
        :returns: A tuple of ``(bytes consumed, errcode)``.
            If finished with decoding return -1 for the bytes consumed.
            Err codes are from :data:`.ImageFile.ERRORS`.
        """
        msg = "unavailable in base decoder"
        raise NotImplementedError(msg)

    def set_as_raw(
        self, data: bytes, rawmode: str | None = None, extra: tuple[Any, ...] = ()
    ) -> None:
        """
        Convenience method to set the internal image from a stream of raw data

        :param data: Bytes to be set
        :param rawmode: The rawmode to be used for the decoder.
            If not specified, it will default to the mode of the image
        :param extra: Extra arguments for the decoder.
        :returns: None
        """

        if not rawmode:
            rawmode = self.mode
        d = Image._getdecoder(self.mode, "raw", rawmode, extra)
        assert self.im is not None
        d.setimage(self.im, self.state.extents())
        s = d.decode(data)

        if s[0] >= 0:
            msg = "not enough image data"
            raise ValueError(msg)
        if s[1] != 0:
            msg = "cannot decode image data"
            raise ValueError(msg)


class PyEncoder(PyCodec):
    """
    Python implementation of a format encoder. Override this class and
    add the decoding logic in the :meth:`encode` method.

    See :ref:`Writing Your Own File Codec in Python<file-codecs-py>`
    """

    _pushes_fd = False

    @property
    def pushes_fd(self) -> bool:
        return self._pushes_fd

    def encode(self, bufsize: int) -> tuple[int, int, bytes]:
        """
        Override to perform the encoding process.

        :param bufsize: Buffer size.
        :returns: A tuple of ``(bytes encoded, errcode, bytes)``.
            If finished with encoding return 1 for the error code.
            Err codes are from :data:`.ImageFile.ERRORS`.
        """
        msg = "unavailable in base encoder"
        raise NotImplementedError(msg)

    def encode_to_pyfd(self) -> tuple[int, int]:
        """
        If ``pushes_fd`` is ``True``, then this method will be used,
        and ``encode()`` will only be called once.

        :returns: A tuple of ``(bytes consumed, errcode)``.
            Err codes are from :data:`.ImageFile.ERRORS`.
        """
        if not self.pushes_fd:
            return 0, -8  # bad configuration
        bytes_consumed, errcode, data = self.encode(0)
        if data:
            assert self.fd is not None
            self.fd.write(data)
        return bytes_consumed, errcode

    def encode_to_file(self, fh: int, bufsize: int) -> int:
        """
        :param fh: File handle.
        :param bufsize: Buffer size.

        :returns: If finished successfully, return 0.
            Otherwise, return an error code. Err codes are from
            :data:`.ImageFile.ERRORS`.
        """
        errcode = 0
        while errcode == 0:
            status, errcode, buf = self.encode(bufsize)
            if status > 0:
                os.write(fh, buf[status:])
        return errcode

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\securetransport.py ===
"""
SecureTranport support for urllib3 via ctypes.

This makes platform-native TLS available to urllib3 users on macOS without the
use of a compiler. This is an important feature because the Python Package
Index is moving to become a TLSv1.2-or-higher server, and the default OpenSSL
that ships with macOS is not capable of doing TLSv1.2. The only way to resolve
this is to give macOS users an alternative solution to the problem, and that
solution is to use SecureTransport.

We use ctypes here because this solution must not require a compiler. That's
because pip is not allowed to require a compiler either.

This is not intended to be a seriously long-term solution to this problem.
The hope is that PEP 543 will eventually solve this issue for us, at which
point we can retire this contrib module. But in the short term, we need to
solve the impending tire fire that is Python on Mac without this kind of
contrib module. So...here we are.

To use this module, simply import and inject it::

    import pip._vendor.urllib3.contrib.securetransport as securetransport
    securetransport.inject_into_urllib3()

Happy TLSing!

This code is a bastardised version of the code found in Will Bond's oscrypto
library. An enormous debt is owed to him for blazing this trail for us. For
that reason, this code should be considered to be covered both by urllib3's
license and by oscrypto's:

.. code-block::

    Copyright (c) 2015-2016 Will Bond <will@wbond.net>

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.
"""
from __future__ import absolute_import

import contextlib
import ctypes
import errno
import os.path
import shutil
import socket
import ssl
import struct
import threading
import weakref

from .. import util
from ..packages import six
from ..util.ssl_ import PROTOCOL_TLS_CLIENT
from ._securetransport.bindings import CoreFoundation, Security, SecurityConst
from ._securetransport.low_level import (
    _assert_no_error,
    _build_tls_unknown_ca_alert,
    _cert_array_from_pem,
    _create_cfstring_array,
    _load_client_cert_chain,
    _temporary_keychain,
)

try:  # Platform-specific: Python 2
    from socket import _fileobject
except ImportError:  # Platform-specific: Python 3
    _fileobject = None
    from ..packages.backports.makefile import backport_makefile

__all__ = ["inject_into_urllib3", "extract_from_urllib3"]

# SNI always works
HAS_SNI = True

orig_util_HAS_SNI = util.HAS_SNI
orig_util_SSLContext = util.ssl_.SSLContext

# This dictionary is used by the read callback to obtain a handle to the
# calling wrapped socket. This is a pretty silly approach, but for now it'll
# do. I feel like I should be able to smuggle a handle to the wrapped socket
# directly in the SSLConnectionRef, but for now this approach will work I
# guess.
#
# We need to lock around this structure for inserts, but we don't do it for
# reads/writes in the callbacks. The reasoning here goes as follows:
#
#    1. It is not possible to call into the callbacks before the dictionary is
#       populated, so once in the callback the id must be in the dictionary.
#    2. The callbacks don't mutate the dictionary, they only read from it, and
#       so cannot conflict with any of the insertions.
#
# This is good: if we had to lock in the callbacks we'd drastically slow down
# the performance of this code.
_connection_refs = weakref.WeakValueDictionary()
_connection_ref_lock = threading.Lock()

# Limit writes to 16kB. This is OpenSSL's limit, but we'll cargo-cult it over
# for no better reason than we need *a* limit, and this one is right there.
SSL_WRITE_BLOCKSIZE = 16384

# This is our equivalent of util.ssl_.DEFAULT_CIPHERS, but expanded out to
# individual cipher suites. We need to do this because this is how
# SecureTransport wants them.
CIPHER_SUITES = [
    SecurityConst.TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,
    SecurityConst.TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,
    SecurityConst.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
    SecurityConst.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
    SecurityConst.TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256,
    SecurityConst.TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256,
    SecurityConst.TLS_DHE_RSA_WITH_AES_256_GCM_SHA384,
    SecurityConst.TLS_DHE_RSA_WITH_AES_128_GCM_SHA256,
    SecurityConst.TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA384,
    SecurityConst.TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA,
    SecurityConst.TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256,
    SecurityConst.TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA,
    SecurityConst.TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA384,
    SecurityConst.TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA,
    SecurityConst.TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256,
    SecurityConst.TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA,
    SecurityConst.TLS_DHE_RSA_WITH_AES_256_CBC_SHA256,
    SecurityConst.TLS_DHE_RSA_WITH_AES_256_CBC_SHA,
    SecurityConst.TLS_DHE_RSA_WITH_AES_128_CBC_SHA256,
    SecurityConst.TLS_DHE_RSA_WITH_AES_128_CBC_SHA,
    SecurityConst.TLS_AES_256_GCM_SHA384,
    SecurityConst.TLS_AES_128_GCM_SHA256,
    SecurityConst.TLS_RSA_WITH_AES_256_GCM_SHA384,
    SecurityConst.TLS_RSA_WITH_AES_128_GCM_SHA256,
    SecurityConst.TLS_AES_128_CCM_8_SHA256,
    SecurityConst.TLS_AES_128_CCM_SHA256,
    SecurityConst.TLS_RSA_WITH_AES_256_CBC_SHA256,
    SecurityConst.TLS_RSA_WITH_AES_128_CBC_SHA256,
    SecurityConst.TLS_RSA_WITH_AES_256_CBC_SHA,
    SecurityConst.TLS_RSA_WITH_AES_128_CBC_SHA,
]

# Basically this is simple: for PROTOCOL_SSLv23 we turn it into a low of
# TLSv1 and a high of TLSv1.2. For everything else, we pin to that version.
# TLSv1 to 1.2 are supported on macOS 10.8+
_protocol_to_min_max = {
    util.PROTOCOL_TLS: (SecurityConst.kTLSProtocol1, SecurityConst.kTLSProtocol12),
    PROTOCOL_TLS_CLIENT: (SecurityConst.kTLSProtocol1, SecurityConst.kTLSProtocol12),
}

if hasattr(ssl, "PROTOCOL_SSLv2"):
    _protocol_to_min_max[ssl.PROTOCOL_SSLv2] = (
        SecurityConst.kSSLProtocol2,
        SecurityConst.kSSLProtocol2,
    )
if hasattr(ssl, "PROTOCOL_SSLv3"):
    _protocol_to_min_max[ssl.PROTOCOL_SSLv3] = (
        SecurityConst.kSSLProtocol3,
        SecurityConst.kSSLProtocol3,
    )
if hasattr(ssl, "PROTOCOL_TLSv1"):
    _protocol_to_min_max[ssl.PROTOCOL_TLSv1] = (
        SecurityConst.kTLSProtocol1,
        SecurityConst.kTLSProtocol1,
    )
if hasattr(ssl, "PROTOCOL_TLSv1_1"):
    _protocol_to_min_max[ssl.PROTOCOL_TLSv1_1] = (
        SecurityConst.kTLSProtocol11,
        SecurityConst.kTLSProtocol11,
    )
if hasattr(ssl, "PROTOCOL_TLSv1_2"):
    _protocol_to_min_max[ssl.PROTOCOL_TLSv1_2] = (
        SecurityConst.kTLSProtocol12,
        SecurityConst.kTLSProtocol12,
    )


def inject_into_urllib3():
    """
    Monkey-patch urllib3 with SecureTransport-backed SSL-support.
    """
    util.SSLContext = SecureTransportContext
    util.ssl_.SSLContext = SecureTransportContext
    util.HAS_SNI = HAS_SNI
    util.ssl_.HAS_SNI = HAS_SNI
    util.IS_SECURETRANSPORT = True
    util.ssl_.IS_SECURETRANSPORT = True


def extract_from_urllib3():
    """
    Undo monkey-patching by :func:`inject_into_urllib3`.
    """
    util.SSLContext = orig_util_SSLContext
    util.ssl_.SSLContext = orig_util_SSLContext
    util.HAS_SNI = orig_util_HAS_SNI
    util.ssl_.HAS_SNI = orig_util_HAS_SNI
    util.IS_SECURETRANSPORT = False
    util.ssl_.IS_SECURETRANSPORT = False


def _read_callback(connection_id, data_buffer, data_length_pointer):
    """
    SecureTransport read callback. This is called by ST to request that data
    be returned from the socket.
    """
    wrapped_socket = None
    try:
        wrapped_socket = _connection_refs.get(connection_id)
        if wrapped_socket is None:
            return SecurityConst.errSSLInternal
        base_socket = wrapped_socket.socket

        requested_length = data_length_pointer[0]

        timeout = wrapped_socket.gettimeout()
        error = None
        read_count = 0

        try:
            while read_count < requested_length:
                if timeout is None or timeout >= 0:
                    if not util.wait_for_read(base_socket, timeout):
                        raise socket.error(errno.EAGAIN, "timed out")

                remaining = requested_length - read_count
                buffer = (ctypes.c_char * remaining).from_address(
                    data_buffer + read_count
                )
                chunk_size = base_socket.recv_into(buffer, remaining)
                read_count += chunk_size
                if not chunk_size:
                    if not read_count:
                        return SecurityConst.errSSLClosedGraceful
                    break
        except (socket.error) as e:
            error = e.errno

            if error is not None and error != errno.EAGAIN:
                data_length_pointer[0] = read_count
                if error == errno.ECONNRESET or error == errno.EPIPE:
                    return SecurityConst.errSSLClosedAbort
                raise

        data_length_pointer[0] = read_count

        if read_count != requested_length:
            return SecurityConst.errSSLWouldBlock

        return 0
    except Exception as e:
        if wrapped_socket is not None:
            wrapped_socket._exception = e
        return SecurityConst.errSSLInternal


def _write_callback(connection_id, data_buffer, data_length_pointer):
    """
    SecureTransport write callback. This is called by ST to request that data
    actually be sent on the network.
    """
    wrapped_socket = None
    try:
        wrapped_socket = _connection_refs.get(connection_id)
        if wrapped_socket is None:
            return SecurityConst.errSSLInternal
        base_socket = wrapped_socket.socket

        bytes_to_write = data_length_pointer[0]
        data = ctypes.string_at(data_buffer, bytes_to_write)

        timeout = wrapped_socket.gettimeout()
        error = None
        sent = 0

        try:
            while sent < bytes_to_write:
                if timeout is None or timeout >= 0:
                    if not util.wait_for_write(base_socket, timeout):
                        raise socket.error(errno.EAGAIN, "timed out")
                chunk_sent = base_socket.send(data)
                sent += chunk_sent

                # This has some needless copying here, but I'm not sure there's
                # much value in optimising this data path.
                data = data[chunk_sent:]
        except (socket.error) as e:
            error = e.errno

            if error is not None and error != errno.EAGAIN:
                data_length_pointer[0] = sent
                if error == errno.ECONNRESET or error == errno.EPIPE:
                    return SecurityConst.errSSLClosedAbort
                raise

        data_length_pointer[0] = sent

        if sent != bytes_to_write:
            return SecurityConst.errSSLWouldBlock

        return 0
    except Exception as e:
        if wrapped_socket is not None:
            wrapped_socket._exception = e
        return SecurityConst.errSSLInternal


# We need to keep these two objects references alive: if they get GC'd while
# in use then SecureTransport could attempt to call a function that is in freed
# memory. That would be...uh...bad. Yeah, that's the word. Bad.
_read_callback_pointer = Security.SSLReadFunc(_read_callback)
_write_callback_pointer = Security.SSLWriteFunc(_write_callback)


class WrappedSocket(object):
    """
    API-compatibility wrapper for Python's OpenSSL wrapped socket object.

    Note: _makefile_refs, _drop(), and _reuse() are needed for the garbage
    collector of PyPy.
    """

    def __init__(self, socket):
        self.socket = socket
        self.context = None
        self._makefile_refs = 0
        self._closed = False
        self._exception = None
        self._keychain = None
        self._keychain_dir = None
        self._client_cert_chain = None

        # We save off the previously-configured timeout and then set it to
        # zero. This is done because we use select and friends to handle the
        # timeouts, but if we leave the timeout set on the lower socket then
        # Python will "kindly" call select on that socket again for us. Avoid
        # that by forcing the timeout to zero.
        self._timeout = self.socket.gettimeout()
        self.socket.settimeout(0)

    @contextlib.contextmanager
    def _raise_on_error(self):
        """
        A context manager that can be used to wrap calls that do I/O from
        SecureTransport. If any of the I/O callbacks hit an exception, this
        context manager will correctly propagate the exception after the fact.
        This avoids silently swallowing those exceptions.

        It also correctly forces the socket closed.
        """
        self._exception = None

        # We explicitly don't catch around this yield because in the unlikely
        # event that an exception was hit in the block we don't want to swallow
        # it.
        yield
        if self._exception is not None:
            exception, self._exception = self._exception, None
            self.close()
            raise exception

    def _set_ciphers(self):
        """
        Sets up the allowed ciphers. By default this matches the set in
        util.ssl_.DEFAULT_CIPHERS, at least as supported by macOS. This is done
        custom and doesn't allow changing at this time, mostly because parsing
        OpenSSL cipher strings is going to be a freaking nightmare.
        """
        ciphers = (Security.SSLCipherSuite * len(CIPHER_SUITES))(*CIPHER_SUITES)
        result = Security.SSLSetEnabledCiphers(
            self.context, ciphers, len(CIPHER_SUITES)
        )
        _assert_no_error(result)

    def _set_alpn_protocols(self, protocols):
        """
        Sets up the ALPN protocols on the context.
        """
        if not protocols:
            return
        protocols_arr = _create_cfstring_array(protocols)
        try:
            result = Security.SSLSetALPNProtocols(self.context, protocols_arr)
            _assert_no_error(result)
        finally:
            CoreFoundation.CFRelease(protocols_arr)

    def _custom_validate(self, verify, trust_bundle):
        """
        Called when we have set custom validation. We do this in two cases:
        first, when cert validation is entirely disabled; and second, when
        using a custom trust DB.
        Raises an SSLError if the connection is not trusted.
        """
        # If we disabled cert validation, just say: cool.
        if not verify:
            return

        successes = (
            SecurityConst.kSecTrustResultUnspecified,
            SecurityConst.kSecTrustResultProceed,
        )
        try:
            trust_result = self._evaluate_trust(trust_bundle)
            if trust_result in successes:
                return
            reason = "error code: %d" % (trust_result,)
        except Exception as e:
            # Do not trust on error
            reason = "exception: %r" % (e,)

        # SecureTransport does not send an alert nor shuts down the connection.
        rec = _build_tls_unknown_ca_alert(self.version())
        self.socket.sendall(rec)
        # close the connection immediately
        # l_onoff = 1, activate linger
        # l_linger = 0, linger for 0 seoncds
        opts = struct.pack("ii", 1, 0)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, opts)
        self.close()
        raise ssl.SSLError("certificate verify failed, %s" % reason)

    def _evaluate_trust(self, trust_bundle):
        # We want data in memory, so load it up.
        if os.path.isfile(trust_bundle):
            with open(trust_bundle, "rb") as f:
                trust_bundle = f.read()

        cert_array = None
        trust = Security.SecTrustRef()

        try:
            # Get a CFArray that contains the certs we want.
            cert_array = _cert_array_from_pem(trust_bundle)

            # Ok, now the hard part. We want to get the SecTrustRef that ST has
            # created for this connection, shove our CAs into it, tell ST to
            # ignore everything else it knows, and then ask if it can build a
            # chain. This is a buuuunch of code.
            result = Security.SSLCopyPeerTrust(self.context, ctypes.byref(trust))
            _assert_no_error(result)
            if not trust:
                raise ssl.SSLError("Failed to copy trust reference")

            result = Security.SecTrustSetAnchorCertificates(trust, cert_array)
            _assert_no_error(result)

            result = Security.SecTrustSetAnchorCertificatesOnly(trust, True)
            _assert_no_error(result)

            trust_result = Security.SecTrustResultType()
            result = Security.SecTrustEvaluate(trust, ctypes.byref(trust_result))
            _assert_no_error(result)
        finally:
            if trust:
                CoreFoundation.CFRelease(trust)

            if cert_array is not None:
                CoreFoundation.CFRelease(cert_array)

        return trust_result.value

    def handshake(
        self,
        server_hostname,
        verify,
        trust_bundle,
        min_version,
        max_version,
        client_cert,
        client_key,
        client_key_passphrase,
        alpn_protocols,
    ):
        """
        Actually performs the TLS handshake. This is run automatically by
        wrapped socket, and shouldn't be needed in user code.
        """
        # First, we do the initial bits of connection setup. We need to create
        # a context, set its I/O funcs, and set the connection reference.
        self.context = Security.SSLCreateContext(
            None, SecurityConst.kSSLClientSide, SecurityConst.kSSLStreamType
        )
        result = Security.SSLSetIOFuncs(
            self.context, _read_callback_pointer, _write_callback_pointer
        )
        _assert_no_error(result)

        # Here we need to compute the handle to use. We do this by taking the
        # id of self modulo 2**31 - 1. If this is already in the dictionary, we
        # just keep incrementing by one until we find a free space.
        with _connection_ref_lock:
            handle = id(self) % 2147483647
            while handle in _connection_refs:
                handle = (handle + 1) % 2147483647
            _connection_refs[handle] = self

        result = Security.SSLSetConnection(self.context, handle)
        _assert_no_error(result)

        # If we have a server hostname, we should set that too.
        if server_hostname:
            if not isinstance(server_hostname, bytes):
                server_hostname = server_hostname.encode("utf-8")

            result = Security.SSLSetPeerDomainName(
                self.context, server_hostname, len(server_hostname)
            )
            _assert_no_error(result)

        # Setup the ciphers.
        self._set_ciphers()

        # Setup the ALPN protocols.
        self._set_alpn_protocols(alpn_protocols)

        # Set the minimum and maximum TLS versions.
        result = Security.SSLSetProtocolVersionMin(self.context, min_version)
        _assert_no_error(result)

        result = Security.SSLSetProtocolVersionMax(self.context, max_version)
        _assert_no_error(result)

        # If there's a trust DB, we need to use it. We do that by telling
        # SecureTransport to break on server auth. We also do that if we don't
        # want to validate the certs at all: we just won't actually do any
        # authing in that case.
        if not verify or trust_bundle is not None:
            result = Security.SSLSetSessionOption(
                self.context, SecurityConst.kSSLSessionOptionBreakOnServerAuth, True
            )
            _assert_no_error(result)

        # If there's a client cert, we need to use it.
        if client_cert:
            self._keychain, self._keychain_dir = _temporary_keychain()
            self._client_cert_chain = _load_client_cert_chain(
                self._keychain, client_cert, client_key
            )
            result = Security.SSLSetCertificate(self.context, self._client_cert_chain)
            _assert_no_error(result)

        while True:
            with self._raise_on_error():
                result = Security.SSLHandshake(self.context)

                if result == SecurityConst.errSSLWouldBlock:
                    raise socket.timeout("handshake timed out")
                elif result == SecurityConst.errSSLServerAuthCompleted:
                    self._custom_validate(verify, trust_bundle)
                    continue
                else:
                    _assert_no_error(result)
                    break

    def fileno(self):
        return self.socket.fileno()

    # Copy-pasted from Python 3.5 source code
    def _decref_socketios(self):
        if self._makefile_refs > 0:
            self._makefile_refs -= 1
        if self._closed:
            self.close()

    def recv(self, bufsiz):
        buffer = ctypes.create_string_buffer(bufsiz)
        bytes_read = self.recv_into(buffer, bufsiz)
        data = buffer[:bytes_read]
        return data

    def recv_into(self, buffer, nbytes=None):
        # Read short on EOF.
        if self._closed:
            return 0

        if nbytes is None:
            nbytes = len(buffer)

        buffer = (ctypes.c_char * nbytes).from_buffer(buffer)
        processed_bytes = ctypes.c_size_t(0)

        with self._raise_on_error():
            result = Security.SSLRead(
                self.context, buffer, nbytes, ctypes.byref(processed_bytes)
            )

        # There are some result codes that we want to treat as "not always
        # errors". Specifically, those are errSSLWouldBlock,
        # errSSLClosedGraceful, and errSSLClosedNoNotify.
        if result == SecurityConst.errSSLWouldBlock:
            # If we didn't process any bytes, then this was just a time out.
            # However, we can get errSSLWouldBlock in situations when we *did*
            # read some data, and in those cases we should just read "short"
            # and return.
            if processed_bytes.value == 0:
                # Timed out, no data read.
                raise socket.timeout("recv timed out")
        elif result in (
            SecurityConst.errSSLClosedGraceful,
            SecurityConst.errSSLClosedNoNotify,
        ):
            # The remote peer has closed this connection. We should do so as
            # well. Note that we don't actually return here because in
            # principle this could actually be fired along with return data.
            # It's unlikely though.
            self.close()
        else:
            _assert_no_error(result)

        # Ok, we read and probably succeeded. We should return whatever data
        # was actually read.
        return processed_bytes.value

    def settimeout(self, timeout):
        self._timeout = timeout

    def gettimeout(self):
        return self._timeout

    def send(self, data):
        processed_bytes = ctypes.c_size_t(0)

        with self._raise_on_error():
            result = Security.SSLWrite(
                self.context, data, len(data), ctypes.byref(processed_bytes)
            )

        if result == SecurityConst.errSSLWouldBlock and processed_bytes.value == 0:
            # Timed out
            raise socket.timeout("send timed out")
        else:
            _assert_no_error(result)

        # We sent, and probably succeeded. Tell them how much we sent.
        return processed_bytes.value

    def sendall(self, data):
        total_sent = 0
        while total_sent < len(data):
            sent = self.send(data[total_sent : total_sent + SSL_WRITE_BLOCKSIZE])
            total_sent += sent

    def shutdown(self):
        with self._raise_on_error():
            Security.SSLClose(self.context)

    def close(self):
        # TODO: should I do clean shutdown here? Do I have to?
        if self._makefile_refs < 1:
            self._closed = True
            if self.context:
                CoreFoundation.CFRelease(self.context)
                self.context = None
            if self._client_cert_chain:
                CoreFoundation.CFRelease(self._client_cert_chain)
                self._client_cert_chain = None
            if self._keychain:
                Security.SecKeychainDelete(self._keychain)
                CoreFoundation.CFRelease(self._keychain)
                shutil.rmtree(self._keychain_dir)
                self._keychain = self._keychain_dir = None
            return self.socket.close()
        else:
            self._makefile_refs -= 1

    def getpeercert(self, binary_form=False):
        # Urgh, annoying.
        #
        # Here's how we do this:
        #
        # 1. Call SSLCopyPeerTrust to get hold of the trust object for this
        #    connection.
        # 2. Call SecTrustGetCertificateAtIndex for index 0 to get the leaf.
        # 3. To get the CN, call SecCertificateCopyCommonName and process that
        #    string so that it's of the appropriate type.
        # 4. To get the SAN, we need to do something a bit more complex:
        #    a. Call SecCertificateCopyValues to get the data, requesting
        #       kSecOIDSubjectAltName.
        #    b. Mess about with this dictionary to try to get the SANs out.
        #
        # This is gross. Really gross. It's going to be a few hundred LoC extra
        # just to repeat something that SecureTransport can *already do*. So my
        # operating assumption at this time is that what we want to do is
        # instead to just flag to urllib3 that it shouldn't do its own hostname
        # validation when using SecureTransport.
        if not binary_form:
            raise ValueError("SecureTransport only supports dumping binary certs")
        trust = Security.SecTrustRef()
        certdata = None
        der_bytes = None

        try:
            # Grab the trust store.
            result = Security.SSLCopyPeerTrust(self.context, ctypes.byref(trust))
            _assert_no_error(result)
            if not trust:
                # Probably we haven't done the handshake yet. No biggie.
                return None

            cert_count = Security.SecTrustGetCertificateCount(trust)
            if not cert_count:
                # Also a case that might happen if we haven't handshaked.
                # Handshook? Handshaken?
                return None

            leaf = Security.SecTrustGetCertificateAtIndex(trust, 0)
            assert leaf

            # Ok, now we want the DER bytes.
            certdata = Security.SecCertificateCopyData(leaf)
            assert certdata

            data_length = CoreFoundation.CFDataGetLength(certdata)
            data_buffer = CoreFoundation.CFDataGetBytePtr(certdata)
            der_bytes = ctypes.string_at(data_buffer, data_length)
        finally:
            if certdata:
                CoreFoundation.CFRelease(certdata)
            if trust:
                CoreFoundation.CFRelease(trust)

        return der_bytes

    def version(self):
        protocol = Security.SSLProtocol()
        result = Security.SSLGetNegotiatedProtocolVersion(
            self.context, ctypes.byref(protocol)
        )
        _assert_no_error(result)
        if protocol.value == SecurityConst.kTLSProtocol13:
            raise ssl.SSLError("SecureTransport does not support TLS 1.3")
        elif protocol.value == SecurityConst.kTLSProtocol12:
            return "TLSv1.2"
        elif protocol.value == SecurityConst.kTLSProtocol11:
            return "TLSv1.1"
        elif protocol.value == SecurityConst.kTLSProtocol1:
            return "TLSv1"
        elif protocol.value == SecurityConst.kSSLProtocol3:
            return "SSLv3"
        elif protocol.value == SecurityConst.kSSLProtocol2:
            return "SSLv2"
        else:
            raise ssl.SSLError("Unknown TLS version: %r" % protocol)

    def _reuse(self):
        self._makefile_refs += 1

    def _drop(self):
        if self._makefile_refs < 1:
            self.close()
        else:
            self._makefile_refs -= 1


if _fileobject:  # Platform-specific: Python 2

    def makefile(self, mode, bufsize=-1):
        self._makefile_refs += 1
        return _fileobject(self, mode, bufsize, close=True)

else:  # Platform-specific: Python 3

    def makefile(self, mode="r", buffering=None, *args, **kwargs):
        # We disable buffering with SecureTransport because it conflicts with
        # the buffering that ST does internally (see issue #1153 for more).
        buffering = 0
        return backport_makefile(self, mode, buffering, *args, **kwargs)


WrappedSocket.makefile = makefile


class SecureTransportContext(object):
    """
    I am a wrapper class for the SecureTransport library, to translate the
    interface of the standard library ``SSLContext`` object to calls into
    SecureTransport.
    """

    def __init__(self, protocol):
        self._min_version, self._max_version = _protocol_to_min_max[protocol]
        self._options = 0
        self._verify = False
        self._trust_bundle = None
        self._client_cert = None
        self._client_key = None
        self._client_key_passphrase = None
        self._alpn_protocols = None

    @property
    def check_hostname(self):
        """
        SecureTransport cannot have its hostname checking disabled. For more,
        see the comment on getpeercert() in this file.
        """
        return True

    @check_hostname.setter
    def check_hostname(self, value):
        """
        SecureTransport cannot have its hostname checking disabled. For more,
        see the comment on getpeercert() in this file.
        """
        pass

    @property
    def options(self):
        # TODO: Well, crap.
        #
        # So this is the bit of the code that is the most likely to cause us
        # trouble. Essentially we need to enumerate all of the SSL options that
        # users might want to use and try to see if we can sensibly translate
        # them, or whether we should just ignore them.
        return self._options

    @options.setter
    def options(self, value):
        # TODO: Update in line with above.
        self._options = value

    @property
    def verify_mode(self):
        return ssl.CERT_REQUIRED if self._verify else ssl.CERT_NONE

    @verify_mode.setter
    def verify_mode(self, value):
        self._verify = True if value == ssl.CERT_REQUIRED else False

    def set_default_verify_paths(self):
        # So, this has to do something a bit weird. Specifically, what it does
        # is nothing.
        #
        # This means that, if we had previously had load_verify_locations
        # called, this does not undo that. We need to do that because it turns
        # out that the rest of the urllib3 code will attempt to load the
        # default verify paths if it hasn't been told about any paths, even if
        # the context itself was sometime earlier. We resolve that by just
        # ignoring it.
        pass

    def load_default_certs(self):
        return self.set_default_verify_paths()

    def set_ciphers(self, ciphers):
        # For now, we just require the default cipher string.
        if ciphers != util.ssl_.DEFAULT_CIPHERS:
            raise ValueError("SecureTransport doesn't support custom cipher strings")

    def load_verify_locations(self, cafile=None, capath=None, cadata=None):
        # OK, we only really support cadata and cafile.
        if capath is not None:
            raise ValueError("SecureTransport does not support cert directories")

        # Raise if cafile does not exist.
        if cafile is not None:
            with open(cafile):
                pass

        self._trust_bundle = cafile or cadata

    def load_cert_chain(self, certfile, keyfile=None, password=None):
        self._client_cert = certfile
        self._client_key = keyfile
        self._client_cert_passphrase = password

    def set_alpn_protocols(self, protocols):
        """
        Sets the ALPN protocols that will later be set on the context.

        Raises a NotImplementedError if ALPN is not supported.
        """
        if not hasattr(Security, "SSLSetALPNProtocols"):
            raise NotImplementedError(
                "SecureTransport supports ALPN only in macOS 10.12+"
            )
        self._alpn_protocols = [six.ensure_binary(p) for p in protocols]

    def wrap_socket(
        self,
        sock,
        server_side=False,
        do_handshake_on_connect=True,
        suppress_ragged_eofs=True,
        server_hostname=None,
    ):
        # So, what do we do here? Firstly, we assert some properties. This is a
        # stripped down shim, so there is some functionality we don't support.
        # See PEP 543 for the real deal.
        assert not server_side
        assert do_handshake_on_connect
        assert suppress_ragged_eofs

        # Ok, we're good to go. Now we want to create the wrapped socket object
        # and store it in the appropriate place.
        wrapped_socket = WrappedSocket(sock)

        # Now we can handshake
        wrapped_socket.handshake(
            server_hostname,
            self._verify,
            self._trust_bundle,
            self._min_version,
            self._max_version,
            self._client_cert,
            self._client_key,
            self._client_key_passphrase,
            self._alpn_protocols,
        )
        return wrapped_socket