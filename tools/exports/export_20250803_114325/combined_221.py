
# === NexusCore/openenv\Lib\site-packages\google\api_core\extended_operation.py ===
# Copyright 2022 Google LLC
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

"""Futures for extended long-running operations returned from Google Cloud APIs.

These futures can be used to synchronously wait for the result of a
long-running operations using :meth:`ExtendedOperation.result`:

.. code-block:: python

    extended_operation = my_api_client.long_running_method()

    extended_operation.result()

Or asynchronously using callbacks and :meth:`Operation.add_done_callback`:

.. code-block:: python

    extended_operation = my_api_client.long_running_method()

    def my_callback(ex_op):
        print(f"Operation {ex_op.name} completed")

    extended_operation.add_done_callback(my_callback)

"""

import threading

from google.api_core import exceptions
from google.api_core.future import polling


class ExtendedOperation(polling.PollingFuture):
    """An ExtendedOperation future for interacting with a Google API Long-Running Operation.

    Args:
        extended_operation (proto.Message): The initial operation.
        refresh (Callable[[], type(extended_operation)]): A callable that returns
            the latest state of the operation.
        cancel (Callable[[], None]): A callable that tries to cancel the operation.
        polling Optional(google.api_core.retry.Retry): The configuration used
            for polling. This can be used to control how often :meth:`done`
            is polled. If the ``timeout`` argument to :meth:`result` is
            specified it will override the ``polling.timeout`` property.
        retry Optional(google.api_core.retry.Retry): DEPRECATED use ``polling``
            instead. If specified it will override ``polling`` parameter to
            maintain backward compatibility.

    Note: Most long-running API methods use google.api_core.operation.Operation
    This class is a wrapper for a subset of methods that use alternative
    Long-Running Operation (LRO) semantics.

    Note: there is not a concrete type the extended operation must be.
    It MUST have fields that correspond to the following, POSSIBLY WITH DIFFERENT NAMES:
    * name: str
    * status: Union[str, bool, enum.Enum]
    * error_code: int
    * error_message: str
    """

    def __init__(
        self,
        extended_operation,
        refresh,
        cancel,
        polling=polling.DEFAULT_POLLING,
        **kwargs,
    ):
        super().__init__(polling=polling, **kwargs)
        self._extended_operation = extended_operation
        self._refresh = refresh
        self._cancel = cancel
        # Note: the extended operation does not give a good way to indicate cancellation.
        # We make do with manually tracking cancellation and checking for doneness.
        self._cancelled = False
        self._completion_lock = threading.Lock()
        # Invoke in case the operation came back already complete.
        self._handle_refreshed_operation()

    # Note: the following four properties MUST be overridden in a subclass
    # if, and only if, the fields in the corresponding extended operation message
    # have different names.
    #
    # E.g. we have an extended operation class that looks like
    #
    # class MyOperation(proto.Message):
    #     moniker = proto.Field(proto.STRING, number=1)
    #     status_msg = proto.Field(proto.STRING, number=2)
    #     optional http_error_code = proto.Field(proto.INT32, number=3)
    #     optional http_error_msg = proto.Field(proto.STRING, number=4)
    #
    # the ExtendedOperation subclass would provide property overrides that map
    # to these (poorly named) fields.
    @property
    def name(self):
        return self._extended_operation.name

    @property
    def status(self):
        return self._extended_operation.status

    @property
    def error_code(self):
        return self._extended_operation.error_code

    @property
    def error_message(self):
        return self._extended_operation.error_message

    def __getattr__(self, name):
        return getattr(self._extended_operation, name)

    def done(self, retry=None):
        self._refresh_and_update(retry)
        return self._extended_operation.done

    def cancel(self):
        if self.done():
            return False

        self._cancel()
        self._cancelled = True
        return True

    def cancelled(self):
        # TODO(dovs): there is not currently a good way to determine whether the
        # operation has been cancelled.
        # The best we can do is manually keep track of cancellation
        # and check for doneness.
        if not self._cancelled:
            return False

        self._refresh_and_update()
        return self._extended_operation.done

    def _refresh_and_update(self, retry=None):
        if not self._extended_operation.done:
            self._extended_operation = (
                self._refresh(retry=retry) if retry else self._refresh()
            )
            self._handle_refreshed_operation()

    def _handle_refreshed_operation(self):
        with self._completion_lock:
            if not self._extended_operation.done:
                return

            if self.error_code and self.error_message:
                # Note: `errors` can be removed once proposal A from
                # b/284179390 is implemented.
                errors = []
                if hasattr(self, "error") and hasattr(self.error, "errors"):
                    errors = self.error.errors
                exception = exceptions.from_http_status(
                    status_code=self.error_code,
                    message=self.error_message,
                    response=self._extended_operation,
                    errors=errors,
                )
                self.set_exception(exception)
            elif self.error_code or self.error_message:
                exception = exceptions.GoogleAPICallError(
                    f"Unexpected error {self.error_code}: {self.error_message}"
                )
                self.set_exception(exception)
            else:
                # Extended operations have no payload.
                self.set_result(None)

    @classmethod
    def make(cls, refresh, cancel, extended_operation, **kwargs):
        """
        Return an instantiated ExtendedOperation (or child) that wraps
        * a refresh callable
        * a cancel callable (can be a no-op)
        * an initial result

        .. note::
            It is the caller's responsibility to set up refresh and cancel
            with their correct request argument.
            The reason for this is that the services that use Extended Operations
            have rpcs that look something like the following:

            // service.proto
            service MyLongService {
                rpc StartLongTask(StartLongTaskRequest) returns (ExtendedOperation) {
                    option (google.cloud.operation_service) = "CustomOperationService";
                }
            }

            service CustomOperationService {
                rpc Get(GetOperationRequest) returns (ExtendedOperation) {
                    option (google.cloud.operation_polling_method) = true;
                }
            }

            Any info needed for the poll, e.g. a name, path params, etc.
            is held in the request, which the initial client method is in a much
            better position to make made because the caller made the initial request.

            TL;DR: the caller sets up closures for refresh and cancel that carry
            the properly configured requests.

        Args:
            refresh (Callable[Optional[Retry]][type(extended_operation)]): A callable that
                returns the latest state of the operation.
            cancel (Callable[][Any]): A callable that tries to cancel the operation
                on a best effort basis.
            extended_operation (Any): The initial response of the long running method.
                See the docstring for ExtendedOperation.__init__ for requirements on
                the type and fields of extended_operation
        """
        return cls(extended_operation, refresh, cancel, **kwargs)

# === NexusCore/openenv\Lib\site-packages\google\api_core\operation_async.py ===
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

"""AsyncIO futures for long-running operations returned from Google Cloud APIs.

These futures can be used to await for the result of a long-running operation
using :meth:`AsyncOperation.result`:


.. code-block:: python

    operation = my_api_client.long_running_method()
    result = await operation.result()

Or asynchronously using callbacks and :meth:`Operation.add_done_callback`:

.. code-block:: python

    operation = my_api_client.long_running_method()

    def my_callback(future):
        result = await future.result()

    operation.add_done_callback(my_callback)

"""

import functools
import threading

from google.api_core import exceptions
from google.api_core import protobuf_helpers
from google.api_core.future import async_future
from google.longrunning import operations_pb2
from google.rpc import code_pb2


class AsyncOperation(async_future.AsyncFuture):
    """A Future for interacting with a Google API Long-Running Operation.

    Args:
        operation (google.longrunning.operations_pb2.Operation): The
            initial operation.
        refresh (Callable[[], ~.api_core.operation.Operation]): A callable that
            returns the latest state of the operation.
        cancel (Callable[[], None]): A callable that tries to cancel
            the operation.
        result_type (func:`type`): The protobuf type for the operation's
            result.
        metadata_type (func:`type`): The protobuf type for the operation's
            metadata.
        retry (google.api_core.retry.Retry): The retry configuration used
            when polling. This can be used to control how often :meth:`done`
            is polled. Regardless of the retry's ``deadline``, it will be
            overridden by the ``timeout`` argument to :meth:`result`.
    """

    def __init__(
        self,
        operation,
        refresh,
        cancel,
        result_type,
        metadata_type=None,
        retry=async_future.DEFAULT_RETRY,
    ):
        super().__init__(retry=retry)
        self._operation = operation
        self._refresh = refresh
        self._cancel = cancel
        self._result_type = result_type
        self._metadata_type = metadata_type
        self._completion_lock = threading.Lock()
        # Invoke this in case the operation came back already complete.
        self._set_result_from_operation()

    @property
    def operation(self):
        """google.longrunning.Operation: The current long-running operation."""
        return self._operation

    @property
    def metadata(self):
        """google.protobuf.Message: the current operation metadata."""
        if not self._operation.HasField("metadata"):
            return None

        return protobuf_helpers.from_any_pb(
            self._metadata_type, self._operation.metadata
        )

    @classmethod
    def deserialize(cls, payload):
        """Deserialize a ``google.longrunning.Operation`` protocol buffer.

        Args:
            payload (bytes): A serialized operation protocol buffer.

        Returns:
            ~.operations_pb2.Operation: An Operation protobuf object.
        """
        return operations_pb2.Operation.FromString(payload)

    def _set_result_from_operation(self):
        """Set the result or exception from the operation if it is complete."""
        # This must be done in a lock to prevent the async_future thread
        # and main thread from both executing the completion logic
        # at the same time.
        with self._completion_lock:
            # If the operation isn't complete or if the result has already been
            # set, do not call set_result/set_exception again.
            if not self._operation.done or self._future.done():
                return

            if self._operation.HasField("response"):
                response = protobuf_helpers.from_any_pb(
                    self._result_type, self._operation.response
                )
                self.set_result(response)
            elif self._operation.HasField("error"):
                exception = exceptions.GoogleAPICallError(
                    self._operation.error.message,
                    errors=(self._operation.error,),
                    response=self._operation,
                )
                self.set_exception(exception)
            else:
                exception = exceptions.GoogleAPICallError(
                    "Unexpected state: Long-running operation had neither "
                    "response nor error set."
                )
                self.set_exception(exception)

    async def _refresh_and_update(self, retry=async_future.DEFAULT_RETRY):
        """Refresh the operation and update the result if needed.

        Args:
            retry (google.api_core.retry.Retry): (Optional) How to retry the RPC.
        """
        # If the currently cached operation is done, no need to make another
        # RPC as it will not change once done.
        if not self._operation.done:
            self._operation = await self._refresh(retry=retry)
            self._set_result_from_operation()

    async def done(self, retry=async_future.DEFAULT_RETRY):
        """Checks to see if the operation is complete.

        Args:
            retry (google.api_core.retry.Retry): (Optional) How to retry the RPC.

        Returns:
            bool: True if the operation is complete, False otherwise.
        """
        await self._refresh_and_update(retry)
        return self._operation.done

    async def cancel(self):
        """Attempt to cancel the operation.

        Returns:
            bool: True if the cancel RPC was made, False if the operation is
                already complete.
        """
        result = await self.done()
        if result:
            return False
        else:
            await self._cancel()
            return True

    async def cancelled(self):
        """True if the operation was cancelled."""
        await self._refresh_and_update()
        return (
            self._operation.HasField("error")
            and self._operation.error.code == code_pb2.CANCELLED
        )


def from_gapic(operation, operations_client, result_type, grpc_metadata=None, **kwargs):
    """Create an operation future from a gapic client.

    This interacts with the long-running operations `service`_ (specific
    to a given API) via a gapic client.

    .. _service: https://github.com/googleapis/googleapis/blob/\
                 050400df0fdb16f63b63e9dee53819044bffc857/\
                 google/longrunning/operations.proto#L38

    Args:
        operation (google.longrunning.operations_pb2.Operation): The operation.
        operations_client (google.api_core.operations_v1.OperationsClient):
            The operations client.
        result_type (:func:`type`): The protobuf result type.
        grpc_metadata (Optional[List[Tuple[str, str]]]): Additional metadata to pass
            to the rpc.
        kwargs: Keyword args passed into the :class:`Operation` constructor.

    Returns:
        ~.api_core.operation.Operation: The operation future to track the given
            operation.
    """
    refresh = functools.partial(
        operations_client.get_operation,
        operation.name,
        metadata=grpc_metadata,
    )
    cancel = functools.partial(
        operations_client.cancel_operation,
        operation.name,
        metadata=grpc_metadata,
    )
    return AsyncOperation(operation, refresh, cancel, result_type, **kwargs)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\db\db_transaction_queue\spend_update_queue.py ===
import asyncio
from typing import Dict, List, Optional

from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import (
    DBSpendUpdateTransactions,
    Litellm_EntityType,
    SpendUpdateQueueItem,
)
from litellm.proxy.db.db_transaction_queue.base_update_queue import (
    BaseUpdateQueue,
    service_logger_obj,
)
from litellm.types.services import ServiceTypes


class SpendUpdateQueue(BaseUpdateQueue):
    """
    In memory buffer for spend updates that should be committed to the database
    """

    def __init__(self):
        super().__init__()
        self.update_queue: asyncio.Queue[SpendUpdateQueueItem] = asyncio.Queue()

    async def flush_and_get_aggregated_db_spend_update_transactions(
        self,
    ) -> DBSpendUpdateTransactions:
        """Flush all updates from the queue and return all updates aggregated by entity type."""
        updates = await self.flush_all_updates_from_in_memory_queue()
        verbose_proxy_logger.debug("Aggregating updates by entity type: %s", updates)
        return self.get_aggregated_db_spend_update_transactions(updates)

    async def add_update(self, update: SpendUpdateQueueItem):
        """Enqueue an update to the spend update queue"""
        verbose_proxy_logger.debug("Adding update to queue: %s", update)
        await self.update_queue.put(update)

        # if the queue is full, aggregate the updates
        if self.update_queue.qsize() >= self.MAX_SIZE_IN_MEMORY_QUEUE:
            verbose_proxy_logger.warning(
                "Spend update queue is full. Aggregating all entries in queue to concatenate entries."
            )
            await self.aggregate_queue_updates()

    async def aggregate_queue_updates(self):
        """Concatenate all updates in the queue to reduce the size of in-memory queue"""
        updates: List[
            SpendUpdateQueueItem
        ] = await self.flush_all_updates_from_in_memory_queue()
        aggregated_updates = self._get_aggregated_spend_update_queue_item(updates)
        for update in aggregated_updates:
            await self.update_queue.put(update)
        return

    def _get_aggregated_spend_update_queue_item(
        self, updates: List[SpendUpdateQueueItem]
    ) -> List[SpendUpdateQueueItem]:
        """
        This is used to reduce the size of the in-memory queue by aggregating updates by entity type + id


        Aggregate updates by entity type + id

        eg.

        ```
        [
            {
                "entity_type": "user",
                "entity_id": "123",
                "response_cost": 100
            },
            {
                "entity_type": "user",
                "entity_id": "123",
                "response_cost": 200
            }
        ]

        ```

        becomes

        ```

        [
            {
                "entity_type": "user",
                "entity_id": "123",
                "response_cost": 300
            }
        ]

        ```
        """
        verbose_proxy_logger.debug(
            "Aggregating spend updates, current queue size: %s",
            self.update_queue.qsize(),
        )
        aggregated_spend_updates: List[SpendUpdateQueueItem] = []

        _in_memory_map: Dict[str, SpendUpdateQueueItem] = {}
        """
        Used for combining several updates into a single update
        Key=entity_type:entity_id
        Value=SpendUpdateQueueItem
        """
        for update in updates:
            _key = f"{update.get('entity_type')}:{update.get('entity_id')}"
            if _key not in _in_memory_map:
                _in_memory_map[_key] = update
            else:
                current_cost = _in_memory_map[_key].get("response_cost", 0) or 0
                update_cost = update.get("response_cost", 0) or 0
                _in_memory_map[_key]["response_cost"] = current_cost + update_cost

        for _key, update in _in_memory_map.items():
            aggregated_spend_updates.append(update)

        verbose_proxy_logger.debug(
            "Aggregated spend updates: %s", aggregated_spend_updates
        )
        return aggregated_spend_updates

    def get_aggregated_db_spend_update_transactions(
        self, updates: List[SpendUpdateQueueItem]
    ) -> DBSpendUpdateTransactions:
        """Aggregate updates by entity type."""
        # Initialize all transaction lists as empty dicts
        db_spend_update_transactions = DBSpendUpdateTransactions(
            user_list_transactions={},
            end_user_list_transactions={},
            key_list_transactions={},
            team_list_transactions={},
            team_member_list_transactions={},
            org_list_transactions={},
        )

        # Map entity types to their corresponding transaction dictionary keys
        entity_type_to_dict_key = {
            Litellm_EntityType.USER: "user_list_transactions",
            Litellm_EntityType.END_USER: "end_user_list_transactions",
            Litellm_EntityType.KEY: "key_list_transactions",
            Litellm_EntityType.TEAM: "team_list_transactions",
            Litellm_EntityType.TEAM_MEMBER: "team_member_list_transactions",
            Litellm_EntityType.ORGANIZATION: "org_list_transactions",
        }

        for update in updates:
            entity_type = update.get("entity_type")
            entity_id = update.get("entity_id") or ""
            response_cost = update.get("response_cost") or 0

            if entity_type is None:
                verbose_proxy_logger.debug(
                    "Skipping update spend for update: %s, because entity_type is None",
                    update,
                )
                continue

            dict_key = entity_type_to_dict_key.get(entity_type)
            if dict_key is None:
                verbose_proxy_logger.debug(
                    "Skipping update spend for update: %s, because entity_type is not in entity_type_to_dict_key",
                    update,
                )
                continue  # Skip unknown entity types

            # Type-safe access using if/elif statements
            if dict_key == "user_list_transactions":
                transactions_dict = db_spend_update_transactions[
                    "user_list_transactions"
                ]
            elif dict_key == "end_user_list_transactions":
                transactions_dict = db_spend_update_transactions[
                    "end_user_list_transactions"
                ]
            elif dict_key == "key_list_transactions":
                transactions_dict = db_spend_update_transactions[
                    "key_list_transactions"
                ]
            elif dict_key == "team_list_transactions":
                transactions_dict = db_spend_update_transactions[
                    "team_list_transactions"
                ]
            elif dict_key == "team_member_list_transactions":
                transactions_dict = db_spend_update_transactions[
                    "team_member_list_transactions"
                ]
            elif dict_key == "org_list_transactions":
                transactions_dict = db_spend_update_transactions[
                    "org_list_transactions"
                ]
            else:
                continue

            if transactions_dict is None:
                transactions_dict = {}

                # type ignore: dict_key is guaranteed to be one of "one of ("user_list_transactions", "end_user_list_transactions", "key_list_transactions", "team_list_transactions", "team_member_list_transactions", "org_list_transactions")"
                db_spend_update_transactions[dict_key] = transactions_dict  # type: ignore

            if entity_id not in transactions_dict:
                transactions_dict[entity_id] = 0

            transactions_dict[entity_id] += response_cost or 0

        return db_spend_update_transactions

    async def _emit_new_item_added_to_queue_event(
        self,
        queue_size: Optional[int] = None,
    ):
        asyncio.create_task(
            service_logger_obj.async_service_success_hook(
                service=ServiceTypes.IN_MEMORY_SPEND_UPDATE_QUEUE,
                duration=0,
                call_type="_emit_new_item_added_to_queue_event",
                event_metadata={
                    "gauge_labels": ServiceTypes.IN_MEMORY_SPEND_UPDATE_QUEUE,
                    "gauge_value": queue_size,
                },
            )
        )

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\control.py ===
import sys
import time
from typing import TYPE_CHECKING, Callable, Dict, Iterable, List, Union

if sys.version_info >= (3, 8):
    from typing import Final
else:
    from pip._vendor.typing_extensions import Final  # pragma: no cover

from .segment import ControlCode, ControlType, Segment

if TYPE_CHECKING:
    from .console import Console, ConsoleOptions, RenderResult

STRIP_CONTROL_CODES: Final = [
    7,  # Bell
    8,  # Backspace
    11,  # Vertical tab
    12,  # Form feed
    13,  # Carriage return
]
_CONTROL_STRIP_TRANSLATE: Final = {
    _codepoint: None for _codepoint in STRIP_CONTROL_CODES
}

CONTROL_ESCAPE: Final = {
    7: "\\a",
    8: "\\b",
    11: "\\v",
    12: "\\f",
    13: "\\r",
}

CONTROL_CODES_FORMAT: Dict[int, Callable[..., str]] = {
    ControlType.BELL: lambda: "\x07",
    ControlType.CARRIAGE_RETURN: lambda: "\r",
    ControlType.HOME: lambda: "\x1b[H",
    ControlType.CLEAR: lambda: "\x1b[2J",
    ControlType.ENABLE_ALT_SCREEN: lambda: "\x1b[?1049h",
    ControlType.DISABLE_ALT_SCREEN: lambda: "\x1b[?1049l",
    ControlType.SHOW_CURSOR: lambda: "\x1b[?25h",
    ControlType.HIDE_CURSOR: lambda: "\x1b[?25l",
    ControlType.CURSOR_UP: lambda param: f"\x1b[{param}A",
    ControlType.CURSOR_DOWN: lambda param: f"\x1b[{param}B",
    ControlType.CURSOR_FORWARD: lambda param: f"\x1b[{param}C",
    ControlType.CURSOR_BACKWARD: lambda param: f"\x1b[{param}D",
    ControlType.CURSOR_MOVE_TO_COLUMN: lambda param: f"\x1b[{param+1}G",
    ControlType.ERASE_IN_LINE: lambda param: f"\x1b[{param}K",
    ControlType.CURSOR_MOVE_TO: lambda x, y: f"\x1b[{y+1};{x+1}H",
    ControlType.SET_WINDOW_TITLE: lambda title: f"\x1b]0;{title}\x07",
}


class Control:
    """A renderable that inserts a control code (non printable but may move cursor).

    Args:
        *codes (str): Positional arguments are either a :class:`~rich.segment.ControlType` enum or a
            tuple of ControlType and an integer parameter
    """

    __slots__ = ["segment"]

    def __init__(self, *codes: Union[ControlType, ControlCode]) -> None:
        control_codes: List[ControlCode] = [
            (code,) if isinstance(code, ControlType) else code for code in codes
        ]
        _format_map = CONTROL_CODES_FORMAT
        rendered_codes = "".join(
            _format_map[code](*parameters) for code, *parameters in control_codes
        )
        self.segment = Segment(rendered_codes, None, control_codes)

    @classmethod
    def bell(cls) -> "Control":
        """Ring the 'bell'."""
        return cls(ControlType.BELL)

    @classmethod
    def home(cls) -> "Control":
        """Move cursor to 'home' position."""
        return cls(ControlType.HOME)

    @classmethod
    def move(cls, x: int = 0, y: int = 0) -> "Control":
        """Move cursor relative to current position.

        Args:
            x (int): X offset.
            y (int): Y offset.

        Returns:
            ~Control: Control object.

        """

        def get_codes() -> Iterable[ControlCode]:
            control = ControlType
            if x:
                yield (
                    control.CURSOR_FORWARD if x > 0 else control.CURSOR_BACKWARD,
                    abs(x),
                )
            if y:
                yield (
                    control.CURSOR_DOWN if y > 0 else control.CURSOR_UP,
                    abs(y),
                )

        control = cls(*get_codes())
        return control

    @classmethod
    def move_to_column(cls, x: int, y: int = 0) -> "Control":
        """Move to the given column, optionally add offset to row.

        Returns:
            x (int): absolute x (column)
            y (int): optional y offset (row)

        Returns:
            ~Control: Control object.
        """

        return (
            cls(
                (ControlType.CURSOR_MOVE_TO_COLUMN, x),
                (
                    ControlType.CURSOR_DOWN if y > 0 else ControlType.CURSOR_UP,
                    abs(y),
                ),
            )
            if y
            else cls((ControlType.CURSOR_MOVE_TO_COLUMN, x))
        )

    @classmethod
    def move_to(cls, x: int, y: int) -> "Control":
        """Move cursor to absolute position.

        Args:
            x (int): x offset (column)
            y (int): y offset (row)

        Returns:
            ~Control: Control object.
        """
        return cls((ControlType.CURSOR_MOVE_TO, x, y))

    @classmethod
    def clear(cls) -> "Control":
        """Clear the screen."""
        return cls(ControlType.CLEAR)

    @classmethod
    def show_cursor(cls, show: bool) -> "Control":
        """Show or hide the cursor."""
        return cls(ControlType.SHOW_CURSOR if show else ControlType.HIDE_CURSOR)

    @classmethod
    def alt_screen(cls, enable: bool) -> "Control":
        """Enable or disable alt screen."""
        if enable:
            return cls(ControlType.ENABLE_ALT_SCREEN, ControlType.HOME)
        else:
            return cls(ControlType.DISABLE_ALT_SCREEN)

    @classmethod
    def title(cls, title: str) -> "Control":
        """Set the terminal window title

        Args:
            title (str): The new terminal window title
        """
        return cls((ControlType.SET_WINDOW_TITLE, title))

    def __str__(self) -> str:
        return self.segment.text

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        if self.segment.text:
            yield self.segment


def strip_control_codes(
    text: str, _translate_table: Dict[int, None] = _CONTROL_STRIP_TRANSLATE
) -> str:
    """Remove control codes from text.

    Args:
        text (str): A string possibly contain control codes.

    Returns:
        str: String with control codes removed.
    """
    return text.translate(_translate_table)


def escape_control_codes(
    text: str,
    _translate_table: Dict[int, str] = CONTROL_ESCAPE,
) -> str:
    """Replace control codes with their "escaped" equivalent in the given text.
    (e.g. "\b" becomes "\\b")

    Args:
        text (str): A string possibly containing control codes.

    Returns:
        str: String with control codes replaced with their escaped version.
    """
    return text.translate(_translate_table)


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich.console import Console

    console = Console()
    console.print("Look at the title of your terminal window ^")
    # console.print(Control((ControlType.SET_WINDOW_TITLE, "Hello, world!")))
    for i in range(10):
        console.set_window_title("🚀 Loading" + "." * i)
        time.sleep(0.5)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\lilypond.py ===
"""
    pygments.lexers.lilypond
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for LilyPond.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import bygroups, default, inherit, words
from pygments.lexers.lisp import SchemeLexer
from pygments.lexers._lilypond_builtins import (
    keywords, pitch_language_names, clefs, scales, repeat_types, units,
    chord_modifiers, pitches, music_functions, dynamics, articulations,
    music_commands, markup_commands, grobs, translators, contexts,
    context_properties, grob_properties, scheme_functions, paper_variables,
    header_variables
)
from pygments.token import Token

__all__ = ["LilyPondLexer"]

# In LilyPond, (unquoted) name tokens only contain letters, hyphens,
# and underscores, where hyphens and underscores must not start or end
# a name token.
#
# Note that many of the entities listed as LilyPond built-in keywords
# (in file `_lilypond_builtins.py`) are only valid if surrounded by
# double quotes, for example, 'hufnagel-fa1'. This means that
# `NAME_END_RE` doesn't apply to such entities in valid LilyPond code.
NAME_END_RE = r"(?=\d|[^\w\-]|[\-_][\W\d])"

def builtin_words(names, backslash, suffix=NAME_END_RE):
    prefix = r"[\-_^]?"
    if backslash == "mandatory":
        prefix += r"\\"
    elif backslash == "optional":
        prefix += r"\\?"
    else:
        assert backslash == "disallowed"
    return words(names, prefix, suffix)


class LilyPondLexer(SchemeLexer):
    """
    Lexer for input to LilyPond, a text-based music typesetter.

    .. important::

       This lexer is meant to be used in conjunction with the ``lilypond`` style.
    """
    name = 'LilyPond'
    url = 'https://lilypond.org'
    aliases = ['lilypond']
    filenames = ['*.ly']
    mimetypes = []
    version_added = '2.11'

    flags = re.DOTALL | re.MULTILINE

    # Because parsing LilyPond input is very tricky (and in fact
    # impossible without executing LilyPond when there is Scheme
    # code in the file), this lexer does not try to recognize
    # lexical modes. Instead, it catches the most frequent pieces
    # of syntax, and, above all, knows about many kinds of builtins.

    # In order to parse embedded Scheme, this lexer subclasses the SchemeLexer.
    # It redefines the 'root' state entirely, and adds a rule for #{ #}
    # to the 'value' state. The latter is used to parse a Scheme expression
    # after #.

    def get_tokens_unprocessed(self, text):
        """Highlight Scheme variables as LilyPond builtins when applicable."""
        for index, token, value in super().get_tokens_unprocessed(text):
            if token is Token.Name.Function or token is Token.Name.Variable:
                if value in scheme_functions:
                    token = Token.Name.Builtin.SchemeFunction
            elif token is Token.Name.Builtin:
                token = Token.Name.Builtin.SchemeBuiltin
            yield index, token, value

    tokens = {
        "root": [
            # Whitespace.
            (r"\s+", Token.Text.Whitespace),

            # Multi-line comments. These are non-nestable.
            (r"%\{.*?%\}", Token.Comment.Multiline),

            # Simple comments.
            (r"%.*?$", Token.Comment.Single),

            # End of embedded LilyPond in Scheme.
            (r"#\}", Token.Punctuation, "#pop"),

            # Embedded Scheme, starting with # ("delayed"),
            # or $ (immediate). #@ and and $@ are the lesser known
            # "list splicing operators".
            (r"[#$]@?", Token.Punctuation, "value"),

            # Any kind of punctuation:
            # - sequential music: { },
            # - parallel music: << >>,
            # - voice separator: << \\ >>,
            # - chord: < >,
            # - bar check: |,
            # - dot in nested properties: \revert NoteHead.color,
            # - equals sign in assignments and lists for various commands:
            #   \override Stem.color = red,
            # - comma as alternative syntax for lists: \time 3,3,2 4/4,
            # - colon in tremolos: c:32,
            # - double hyphen and underscore in lyrics: li -- ly -- pond __
            #   (which must be preceded by ASCII whitespace)
            (r"""(?x)
               \\\\
               | (?<= \s ) (?: -- | __ )
               | [{}<>=.,:|]
              """, Token.Punctuation),

            # Pitches, with optional octavation marks, octave check,
            # and forced or cautionary accidental.
            (words(pitches, suffix=r"=?[',]*!?\??" + NAME_END_RE), Token.Pitch),

            # Strings, optionally with direction specifier.
            (r'[\-_^]?"', Token.String, "string"),

            # Numbers.
            (r"-?\d+\.\d+", Token.Number.Float), # 5. and .5 are not allowed
            (r"-?\d+/\d+", Token.Number.Fraction),
            # Integers, or durations with optional augmentation dots.
            # We have no way to distinguish these, so we highlight
            # them all as numbers.
            #
            # Normally, there is a space before the integer (being an
            # argument to a music function), which we check here.  The
            # case without a space is handled below (as a fingering
            # number).
            (r"""(?x)
               (?<= \s ) -\d+
               | (?: (?: \d+ | \\breve | \\longa | \\maxima )
                     \.* )
              """, Token.Number),
            # Separates duration and duration multiplier highlighted as fraction.
            (r"\*", Token.Number),

            # Ties, slurs, manual beams.
            (r"[~()[\]]", Token.Name.Builtin.Articulation),

            # Predefined articulation shortcuts. A direction specifier is
            # required here.
            (r"[\-_^][>^_!.\-+]", Token.Name.Builtin.Articulation),

            # Fingering numbers, string numbers.
            (r"[\-_^]?\\?\d+", Token.Name.Builtin.Articulation),

            # Builtins.
            (builtin_words(keywords, "mandatory"), Token.Keyword),
            (builtin_words(pitch_language_names, "disallowed"), Token.Name.PitchLanguage),
            (builtin_words(clefs, "disallowed"), Token.Name.Builtin.Clef),
            (builtin_words(scales, "mandatory"), Token.Name.Builtin.Scale),
            (builtin_words(repeat_types, "disallowed"), Token.Name.Builtin.RepeatType),
            (builtin_words(units, "mandatory"), Token.Number),
            (builtin_words(chord_modifiers, "disallowed"), Token.ChordModifier),
            (builtin_words(music_functions, "mandatory"), Token.Name.Builtin.MusicFunction),
            (builtin_words(dynamics, "mandatory"), Token.Name.Builtin.Dynamic),
            # Those like slurs that don't take a backslash are covered above.
            (builtin_words(articulations, "mandatory"), Token.Name.Builtin.Articulation),
            (builtin_words(music_commands, "mandatory"), Token.Name.Builtin.MusicCommand),
            (builtin_words(markup_commands, "mandatory"), Token.Name.Builtin.MarkupCommand),
            (builtin_words(grobs, "disallowed"), Token.Name.Builtin.Grob),
            (builtin_words(translators, "disallowed"), Token.Name.Builtin.Translator),
            # Optional backslash because of \layout { \context { \Score ... } }.
            (builtin_words(contexts, "optional"), Token.Name.Builtin.Context),
            (builtin_words(context_properties, "disallowed"), Token.Name.Builtin.ContextProperty),
            (builtin_words(grob_properties, "disallowed"),
             Token.Name.Builtin.GrobProperty,
             "maybe-subproperties"),
            # Optional backslashes here because output definitions are wrappers
            # around modules.  Concretely, you can do, e.g.,
            # \paper { oddHeaderMarkup = \evenHeaderMarkup }
            (builtin_words(paper_variables, "optional"), Token.Name.Builtin.PaperVariable),
            (builtin_words(header_variables, "optional"), Token.Name.Builtin.HeaderVariable),

            # Other backslashed-escaped names (like dereferencing a
            # music variable), possibly with a direction specifier.
            (r"[\-_^]?\\.+?" + NAME_END_RE, Token.Name.BackslashReference),

            # Definition of a variable. Support assignments to alist keys
            # (myAlist.my-key.my-nested-key = \markup \spam \eggs).
            (r"""(?x)
               (?: [^\W\d] | - )+
               (?= (?: [^\W\d] | [\-.] )* \s* = )
              """, Token.Name.Lvalue),

            # Virtually everything can appear in markup mode, so we highlight
            # as text.  Try to get a complete word, or we might wrongly lex
            # a suffix that happens to be a builtin as a builtin (e.g., "myStaff").
            (r"([^\W\d]|-)+?" + NAME_END_RE, Token.Text),
            (r".", Token.Text),
        ],
        "string": [
            (r'"', Token.String, "#pop"),
            (r'\\.', Token.String.Escape),
            (r'[^\\"]+', Token.String),
        ],
        "value": [
            # Scan a LilyPond value, then pop back since we had a
            # complete expression.
            (r"#\{", Token.Punctuation, ("#pop", "root")),
            inherit,
        ],
        # Grob subproperties are undeclared and it would be tedious
        # to maintain them by hand. Instead, this state allows recognizing
        # everything that looks like a-known-property.foo.bar-baz as
        # one single property name.
        "maybe-subproperties": [
            (r"\s+", Token.Text.Whitespace),
            (r"(\.)((?:[^\W\d]|-)+?)" + NAME_END_RE,
             bygroups(Token.Punctuation, Token.Name.Builtin.GrobProperty)),
            default("#pop"),
        ]
    }

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_wait_for_object.py ===
import os

import pytest

on_windows = os.name == "nt"
# Mark all the tests in this file as being windows-only
pytestmark = pytest.mark.skipif(not on_windows, reason="windows only")

import trio

from .. import _core, _timeouts
from .._core._tests.tutil import slow

if on_windows:
    from .._core._windows_cffi import Handle, ffi, kernel32
    from .._wait_for_object import WaitForMultipleObjects_sync, WaitForSingleObject


def test_WaitForMultipleObjects_sync() -> None:
    # This does a series of tests where we set/close the handle before
    # initiating the waiting for it.
    #
    # Note that closing the handle (not signaling) will cause the
    # *initiation* of a wait to return immediately. But closing a handle
    # that is already being waited on will not stop whatever is waiting
    # for it.

    # One handle
    handle1 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    kernel32.SetEvent(handle1)
    WaitForMultipleObjects_sync(handle1)
    kernel32.CloseHandle(handle1)
    print("test_WaitForMultipleObjects_sync one OK")

    # Two handles, signal first
    handle1 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    handle2 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    kernel32.SetEvent(handle1)
    WaitForMultipleObjects_sync(handle1, handle2)
    kernel32.CloseHandle(handle1)
    kernel32.CloseHandle(handle2)
    print("test_WaitForMultipleObjects_sync set first OK")

    # Two handles, signal second
    handle1 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    handle2 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    kernel32.SetEvent(handle2)
    WaitForMultipleObjects_sync(handle1, handle2)
    kernel32.CloseHandle(handle1)
    kernel32.CloseHandle(handle2)
    print("test_WaitForMultipleObjects_sync set second OK")

    # Two handles, close first
    handle1 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    handle2 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    kernel32.CloseHandle(handle1)
    with pytest.raises(OSError, match=r"^\[WinError 6\] The handle is invalid$"):
        WaitForMultipleObjects_sync(handle1, handle2)
    kernel32.CloseHandle(handle2)
    print("test_WaitForMultipleObjects_sync close first OK")

    # Two handles, close second
    handle1 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    handle2 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    kernel32.CloseHandle(handle2)
    with pytest.raises(OSError, match=r"^\[WinError 6\] The handle is invalid$"):
        WaitForMultipleObjects_sync(handle1, handle2)
    kernel32.CloseHandle(handle1)
    print("test_WaitForMultipleObjects_sync close second OK")


@slow
async def test_WaitForMultipleObjects_sync_slow() -> None:
    # This does a series of test in which the main thread sync-waits for
    # handles, while we spawn a thread to set the handles after a short while.

    TIMEOUT = 0.3

    # One handle
    handle1 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    t0 = _core.current_time()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(
            trio.to_thread.run_sync,
            WaitForMultipleObjects_sync,
            handle1,
        )
        await _timeouts.sleep(TIMEOUT)
        # If we would comment the line below, the above thread will be stuck,
        # and Trio won't exit this scope
        kernel32.SetEvent(handle1)
    t1 = _core.current_time()
    assert TIMEOUT <= (t1 - t0) < 2.0 * TIMEOUT
    kernel32.CloseHandle(handle1)
    print("test_WaitForMultipleObjects_sync_slow one OK")

    # Two handles, signal first
    handle1 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    handle2 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    t0 = _core.current_time()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(
            trio.to_thread.run_sync,
            WaitForMultipleObjects_sync,
            handle1,
            handle2,
        )
        await _timeouts.sleep(TIMEOUT)
        kernel32.SetEvent(handle1)
    t1 = _core.current_time()
    assert TIMEOUT <= (t1 - t0) < 2.0 * TIMEOUT
    kernel32.CloseHandle(handle1)
    kernel32.CloseHandle(handle2)
    print("test_WaitForMultipleObjects_sync_slow thread-set first OK")

    # Two handles, signal second
    handle1 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    handle2 = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    t0 = _core.current_time()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(
            trio.to_thread.run_sync,
            WaitForMultipleObjects_sync,
            handle1,
            handle2,
        )
        await _timeouts.sleep(TIMEOUT)
        kernel32.SetEvent(handle2)
    t1 = _core.current_time()
    assert TIMEOUT <= (t1 - t0) < 2.0 * TIMEOUT
    kernel32.CloseHandle(handle1)
    kernel32.CloseHandle(handle2)
    print("test_WaitForMultipleObjects_sync_slow thread-set second OK")


async def test_WaitForSingleObject() -> None:
    # This does a series of test for setting/closing the handle before
    # initiating the wait.

    # Test already set
    handle = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    kernel32.SetEvent(handle)
    await WaitForSingleObject(handle)  # should return at once
    kernel32.CloseHandle(handle)
    print("test_WaitForSingleObject already set OK")

    # Test already set, as int
    handle = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    handle_int = int(ffi.cast("intptr_t", handle))
    kernel32.SetEvent(handle)
    await WaitForSingleObject(handle_int)  # should return at once
    kernel32.CloseHandle(handle)
    print("test_WaitForSingleObject already set OK")

    # Test already closed
    handle = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    kernel32.CloseHandle(handle)
    with pytest.raises(OSError, match=r"^\[WinError 6\] The handle is invalid$"):
        await WaitForSingleObject(handle)  # should return at once
    print("test_WaitForSingleObject already closed OK")

    # Not a handle
    with pytest.raises(TypeError):
        await WaitForSingleObject("not a handle")  # type: ignore[arg-type] # Wrong type
    # with pytest.raises(OSError):
    #     await WaitForSingleObject(99)  # If you're unlucky, it actually IS a handle :(
    print("test_WaitForSingleObject not a handle OK")


@slow
async def test_WaitForSingleObject_slow() -> None:
    # This does a series of test for setting the handle in another task,
    # and cancelling the wait task.

    # Set the timeout used in the tests. We test the waiting time against
    # the timeout with a certain margin.
    TIMEOUT = 0.3

    async def signal_soon_async(handle: Handle) -> None:
        await _timeouts.sleep(TIMEOUT)
        kernel32.SetEvent(handle)

    # Test handle is SET after TIMEOUT in separate coroutine

    handle = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    t0 = _core.current_time()

    async with _core.open_nursery() as nursery:
        nursery.start_soon(WaitForSingleObject, handle)
        nursery.start_soon(signal_soon_async, handle)

    kernel32.CloseHandle(handle)
    t1 = _core.current_time()
    assert TIMEOUT <= (t1 - t0) < 2.0 * TIMEOUT
    print("test_WaitForSingleObject_slow set from task OK")

    # Test handle is SET after TIMEOUT in separate coroutine, as int

    handle = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    handle_int = int(ffi.cast("intptr_t", handle))
    t0 = _core.current_time()

    async with _core.open_nursery() as nursery:
        nursery.start_soon(WaitForSingleObject, handle_int)
        nursery.start_soon(signal_soon_async, handle)

    kernel32.CloseHandle(handle)
    t1 = _core.current_time()
    assert TIMEOUT <= (t1 - t0) < 2.0 * TIMEOUT
    print("test_WaitForSingleObject_slow set from task as int OK")

    # Test handle is CLOSED after 1 sec - NOPE see comment above

    # Test cancellation

    handle = kernel32.CreateEventA(ffi.NULL, True, False, ffi.NULL)
    t0 = _core.current_time()

    with _timeouts.move_on_after(TIMEOUT):
        await WaitForSingleObject(handle)

    kernel32.CloseHandle(handle)
    t1 = _core.current_time()
    assert TIMEOUT <= (t1 - t0) < 2.0 * TIMEOUT
    print("test_WaitForSingleObject_slow cancellation OK")

# === NexusCore/openenv\Lib\site-packages\zmq\backend\cffi\message.py ===
"""Dummy Frame object"""

# Copyright (C) PyZMQ Developers
# Distributed under the terms of the Modified BSD License.

import errno
from threading import Event

import zmq
import zmq.error
from zmq.constants import ETERM

from ._cffi import ffi
from ._cffi import lib as C

zmq_gc = None

try:
    from __pypy__.bufferable import bufferable as maybe_bufferable
except ImportError:
    maybe_bufferable = object


def _content(obj):
    """Return content of obj as bytes"""
    if type(obj) is bytes:
        return obj
    if not isinstance(obj, memoryview):
        obj = memoryview(obj)
    return obj.tobytes()


def _check_rc(rc):
    err = C.zmq_errno()
    if rc == -1:
        if err == errno.EINTR:
            raise zmq.error.InterrruptedSystemCall(err)
        elif err == errno.EAGAIN:
            raise zmq.error.Again(errno)
        elif err == ETERM:
            raise zmq.error.ContextTerminated(err)
        else:
            raise zmq.error.ZMQError(err)
    return 0


class Frame(maybe_bufferable):
    _data = None
    tracker = None
    closed = False
    more = False
    _buffer = None
    _bytes = None
    _failed_init = False
    tracker_event = None
    zmq_msg = None

    def __init__(self, data=None, track=False, copy=None, copy_threshold=None):
        self._failed_init = True

        self.zmq_msg = ffi.cast('zmq_msg_t[1]', C.malloc(ffi.sizeof("zmq_msg_t")))

        # self.tracker should start finished
        # except in the case where we are sharing memory with libzmq
        if track:
            self.tracker = zmq._FINISHED_TRACKER

        if isinstance(data, str):
            raise TypeError(
                "Unicode strings are not allowed. Only: bytes, buffer interfaces."
            )

        if data is None:
            rc = C.zmq_msg_init(self.zmq_msg)
            _check_rc(rc)
            self._failed_init = False
            return

        self._data = data
        if type(data) is bytes:
            # avoid unnecessary copy on .bytes access
            self._bytes = data

        self._buffer = memoryview(data)
        if not self._buffer.contiguous:
            raise BufferError("memoryview: underlying buffer is not contiguous")
        # from_buffer silently copies if memory is not contiguous
        c_data = ffi.from_buffer(self._buffer)
        data_len_c = self._buffer.nbytes

        if copy is None:
            if copy_threshold and data_len_c < copy_threshold:
                copy = True
            else:
                copy = False

        if copy:
            # copy message data instead of sharing memory
            rc = C.zmq_msg_init_size(self.zmq_msg, data_len_c)
            _check_rc(rc)
            ffi.buffer(C.zmq_msg_data(self.zmq_msg), data_len_c)[:] = self._buffer
            self._failed_init = False
            return

        # Getting here means that we are doing a true zero-copy Frame,
        # where libzmq and Python are sharing memory.
        # Hook up garbage collection with MessageTracker and zmq_free_fn

        # Event and MessageTracker for monitoring when zmq is done with data:
        if track:
            evt = Event()
            self.tracker_event = evt
            self.tracker = zmq.MessageTracker(evt)
        # create the hint for zmq_free_fn
        # two pointers: the zmq_gc context and a message to be sent to the zmq_gc PULL socket
        # allows libzmq to signal to Python when it is done with Python-owned memory.
        global zmq_gc
        if zmq_gc is None:
            from zmq.utils.garbage import gc as zmq_gc
        # can't use ffi.new because it will be freed at the wrong time!
        hint = ffi.cast("zhint[1]", C.malloc(ffi.sizeof("zhint")))
        hint[0].id = zmq_gc.store(data, self.tracker_event)
        if not zmq_gc._push_mutex:
            zmq_gc._push_mutex = C.mutex_allocate()

        hint[0].mutex = ffi.cast("mutex_t*", zmq_gc._push_mutex)
        hint[0].sock = ffi.cast("void*", zmq_gc._push_socket.underlying)

        # calls zmq_wrap_msg_init_data with the C.free_python_msg callback
        rc = C.zmq_wrap_msg_init_data(
            self.zmq_msg,
            c_data,
            data_len_c,
            hint,
        )
        if rc != 0:
            C.free(hint)
            C.free(self.zmq_msg)
            _check_rc(rc)
        self._failed_init = False

    def __del__(self):
        if not self.closed and not self._failed_init:
            self.close()

    def close(self):
        if self.closed or self._failed_init or self.zmq_msg is None:
            return
        self.closed = True
        rc = C.zmq_msg_close(self.zmq_msg)
        C.free(self.zmq_msg)
        self.zmq_msg = None
        if rc != 0:
            _check_rc(rc)

    def _buffer_from_zmq_msg(self):
        """one-time extract buffer from zmq_msg

        for Frames created by recv
        """
        if self._data is None:
            self._data = ffi.buffer(
                C.zmq_msg_data(self.zmq_msg), C.zmq_msg_size(self.zmq_msg)
            )
        if self._buffer is None:
            self._buffer = memoryview(self._data)

    @property
    def buffer(self):
        if self._buffer is None:
            self._buffer_from_zmq_msg()
        return self._buffer

    @property
    def bytes(self):
        if self._bytes is None:
            self._bytes = self.buffer.tobytes()
        return self._bytes

    def __len__(self):
        return self.buffer.nbytes

    def __eq__(self, other):
        return self.bytes == _content(other)

    @property
    def done(self):
        return self.tracker.done()

    def __buffer__(self, flags):
        return self.buffer

    def __copy__(self):
        """Create a shallow copy of the message.

        This does not copy the contents of the Frame, just the pointer.
        This will increment the 0MQ ref count of the message, but not
        the ref count of the Python object. That is only done once when
        the Python is first turned into a 0MQ message.
        """
        return self.fast_copy()

    def fast_copy(self):
        """Fast shallow copy of the Frame.

        Does not copy underlying data.
        """
        new_msg = Frame()
        # This does not copy the contents, but just increases the ref-count
        # of the zmq_msg by one.
        C.zmq_msg_copy(new_msg.zmq_msg, self.zmq_msg)
        # Copy the ref to underlying data
        new_msg._data = self._data
        new_msg._buffer = self._buffer

        # Frame copies share the tracker and tracker_event
        new_msg.tracker_event = self.tracker_event
        new_msg.tracker = self.tracker

        return new_msg


Message = Frame

__all__ = ['Frame', 'Message']

# === NexusCore/myenv\Lib\site-packages\pip\_internal\commands\show.py ===
import logging
from optparse import Values
from typing import Generator, Iterable, Iterator, List, NamedTuple, Optional

from pip._vendor.packaging.requirements import InvalidRequirement
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.metadata import BaseDistribution, get_default_environment
from pip._internal.utils.misc import write_output

logger = logging.getLogger(__name__)


class ShowCommand(Command):
    """
    Show information about one or more installed packages.

    The output is in RFC-compliant mail header format.
    """

    usage = """
      %prog [options] <package> ..."""
    ignore_require_venv = True

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "-f",
            "--files",
            dest="files",
            action="store_true",
            default=False,
            help="Show the full list of installed files for each package.",
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: List[str]) -> int:
        if not args:
            logger.warning("ERROR: Please provide a package name or names.")
            return ERROR
        query = args

        results = search_packages_info(query)
        if not print_results(
            results, list_files=options.files, verbose=options.verbose
        ):
            return ERROR
        return SUCCESS


class _PackageInfo(NamedTuple):
    name: str
    version: str
    location: str
    editable_project_location: Optional[str]
    requires: List[str]
    required_by: List[str]
    installer: str
    metadata_version: str
    classifiers: List[str]
    summary: str
    homepage: str
    project_urls: List[str]
    author: str
    author_email: str
    license: str
    license_expression: str
    entry_points: List[str]
    files: Optional[List[str]]


def search_packages_info(query: List[str]) -> Generator[_PackageInfo, None, None]:
    """
    Gather details from installed distributions. Print distribution name,
    version, location, and installed files. Installed files requires a
    pip generated 'installed-files.txt' in the distributions '.egg-info'
    directory.
    """
    env = get_default_environment()

    installed = {dist.canonical_name: dist for dist in env.iter_all_distributions()}
    query_names = [canonicalize_name(name) for name in query]
    missing = sorted(
        [name for name, pkg in zip(query, query_names) if pkg not in installed]
    )
    if missing:
        logger.warning("Package(s) not found: %s", ", ".join(missing))

    def _get_requiring_packages(current_dist: BaseDistribution) -> Iterator[str]:
        return (
            dist.metadata["Name"] or "UNKNOWN"
            for dist in installed.values()
            if current_dist.canonical_name
            in {canonicalize_name(d.name) for d in dist.iter_dependencies()}
        )

    for query_name in query_names:
        try:
            dist = installed[query_name]
        except KeyError:
            continue

        try:
            requires = sorted(
                # Avoid duplicates in requirements (e.g. due to environment markers).
                {req.name for req in dist.iter_dependencies()},
                key=str.lower,
            )
        except InvalidRequirement:
            requires = sorted(dist.iter_raw_dependencies(), key=str.lower)

        try:
            required_by = sorted(_get_requiring_packages(dist), key=str.lower)
        except InvalidRequirement:
            required_by = ["#N/A"]

        try:
            entry_points_text = dist.read_text("entry_points.txt")
            entry_points = entry_points_text.splitlines(keepends=False)
        except FileNotFoundError:
            entry_points = []

        files_iter = dist.iter_declared_entries()
        if files_iter is None:
            files: Optional[List[str]] = None
        else:
            files = sorted(files_iter)

        metadata = dist.metadata

        project_urls = metadata.get_all("Project-URL", [])
        homepage = metadata.get("Home-page", "")
        if not homepage:
            # It's common that there is a "homepage" Project-URL, but Home-page
            # remains unset (especially as PEP 621 doesn't surface the field).
            #
            # This logic was taken from PyPI's codebase.
            for url in project_urls:
                url_label, url = url.split(",", maxsplit=1)
                normalized_label = (
                    url_label.casefold().replace("-", "").replace("_", "").strip()
                )
                if normalized_label == "homepage":
                    homepage = url.strip()
                    break

        yield _PackageInfo(
            name=dist.raw_name,
            version=dist.raw_version,
            location=dist.location or "",
            editable_project_location=dist.editable_project_location,
            requires=requires,
            required_by=required_by,
            installer=dist.installer,
            metadata_version=dist.metadata_version or "",
            classifiers=metadata.get_all("Classifier", []),
            summary=metadata.get("Summary", ""),
            homepage=homepage,
            project_urls=project_urls,
            author=metadata.get("Author", ""),
            author_email=metadata.get("Author-email", ""),
            license=metadata.get("License", ""),
            license_expression=metadata.get("License-Expression", ""),
            entry_points=entry_points,
            files=files,
        )


def print_results(
    distributions: Iterable[_PackageInfo],
    list_files: bool,
    verbose: bool,
) -> bool:
    """
    Print the information from installed distributions found.
    """
    results_printed = False
    for i, dist in enumerate(distributions):
        results_printed = True
        if i > 0:
            write_output("---")

        metadata_version_tuple = tuple(map(int, dist.metadata_version.split(".")))

        write_output("Name: %s", dist.name)
        write_output("Version: %s", dist.version)
        write_output("Summary: %s", dist.summary)
        write_output("Home-page: %s", dist.homepage)
        write_output("Author: %s", dist.author)
        write_output("Author-email: %s", dist.author_email)
        if metadata_version_tuple >= (2, 4) and dist.license_expression:
            write_output("License-Expression: %s", dist.license_expression)
        else:
            write_output("License: %s", dist.license)
        write_output("Location: %s", dist.location)
        if dist.editable_project_location is not None:
            write_output(
                "Editable project location: %s", dist.editable_project_location
            )
        write_output("Requires: %s", ", ".join(dist.requires))
        write_output("Required-by: %s", ", ".join(dist.required_by))

        if verbose:
            write_output("Metadata-Version: %s", dist.metadata_version)
            write_output("Installer: %s", dist.installer)
            write_output("Classifiers:")
            for classifier in dist.classifiers:
                write_output("  %s", classifier)
            write_output("Entry-points:")
            for entry in dist.entry_points:
                write_output("  %s", entry.strip())
            write_output("Project-URLs:")
            for project_url in dist.project_urls:
                write_output("  %s", project_url)
        if list_files:
            write_output("Files:")
            if dist.files is None:
                write_output("Cannot locate RECORD or installed-files.txt")
            else:
                for line in dist.files:
                    write_output("  %s", line.strip())
    return results_printed

# === NexusCore/myenv\Lib\site-packages\pip\_internal\models\direct_url.py ===
""" PEP 610 """

import json
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Iterable, Optional, Type, TypeVar, Union

__all__ = [
    "DirectUrl",
    "DirectUrlValidationError",
    "DirInfo",
    "ArchiveInfo",
    "VcsInfo",
]

T = TypeVar("T")

DIRECT_URL_METADATA_NAME = "direct_url.json"
ENV_VAR_RE = re.compile(r"^\$\{[A-Za-z0-9-_]+\}(:\$\{[A-Za-z0-9-_]+\})?$")


class DirectUrlValidationError(Exception):
    pass


def _get(
    d: Dict[str, Any], expected_type: Type[T], key: str, default: Optional[T] = None
) -> Optional[T]:
    """Get value from dictionary and verify expected type."""
    if key not in d:
        return default
    value = d[key]
    if not isinstance(value, expected_type):
        raise DirectUrlValidationError(
            f"{value!r} has unexpected type for {key} (expected {expected_type})"
        )
    return value


def _get_required(
    d: Dict[str, Any], expected_type: Type[T], key: str, default: Optional[T] = None
) -> T:
    value = _get(d, expected_type, key, default)
    if value is None:
        raise DirectUrlValidationError(f"{key} must have a value")
    return value


def _exactly_one_of(infos: Iterable[Optional["InfoType"]]) -> "InfoType":
    infos = [info for info in infos if info is not None]
    if not infos:
        raise DirectUrlValidationError(
            "missing one of archive_info, dir_info, vcs_info"
        )
    if len(infos) > 1:
        raise DirectUrlValidationError(
            "more than one of archive_info, dir_info, vcs_info"
        )
    assert infos[0] is not None
    return infos[0]


def _filter_none(**kwargs: Any) -> Dict[str, Any]:
    """Make dict excluding None values."""
    return {k: v for k, v in kwargs.items() if v is not None}


@dataclass
class VcsInfo:
    name: ClassVar = "vcs_info"

    vcs: str
    commit_id: str
    requested_revision: Optional[str] = None

    @classmethod
    def _from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["VcsInfo"]:
        if d is None:
            return None
        return cls(
            vcs=_get_required(d, str, "vcs"),
            commit_id=_get_required(d, str, "commit_id"),
            requested_revision=_get(d, str, "requested_revision"),
        )

    def _to_dict(self) -> Dict[str, Any]:
        return _filter_none(
            vcs=self.vcs,
            requested_revision=self.requested_revision,
            commit_id=self.commit_id,
        )


class ArchiveInfo:
    name = "archive_info"

    def __init__(
        self,
        hash: Optional[str] = None,
        hashes: Optional[Dict[str, str]] = None,
    ) -> None:
        # set hashes before hash, since the hash setter will further populate hashes
        self.hashes = hashes
        self.hash = hash

    @property
    def hash(self) -> Optional[str]:
        return self._hash

    @hash.setter
    def hash(self, value: Optional[str]) -> None:
        if value is not None:
            # Auto-populate the hashes key to upgrade to the new format automatically.
            # We don't back-populate the legacy hash key from hashes.
            try:
                hash_name, hash_value = value.split("=", 1)
            except ValueError:
                raise DirectUrlValidationError(
                    f"invalid archive_info.hash format: {value!r}"
                )
            if self.hashes is None:
                self.hashes = {hash_name: hash_value}
            elif hash_name not in self.hashes:
                self.hashes = self.hashes.copy()
                self.hashes[hash_name] = hash_value
        self._hash = value

    @classmethod
    def _from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["ArchiveInfo"]:
        if d is None:
            return None
        return cls(hash=_get(d, str, "hash"), hashes=_get(d, dict, "hashes"))

    def _to_dict(self) -> Dict[str, Any]:
        return _filter_none(hash=self.hash, hashes=self.hashes)


@dataclass
class DirInfo:
    name: ClassVar = "dir_info"

    editable: bool = False

    @classmethod
    def _from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["DirInfo"]:
        if d is None:
            return None
        return cls(editable=_get_required(d, bool, "editable", default=False))

    def _to_dict(self) -> Dict[str, Any]:
        return _filter_none(editable=self.editable or None)


InfoType = Union[ArchiveInfo, DirInfo, VcsInfo]


@dataclass
class DirectUrl:
    url: str
    info: InfoType
    subdirectory: Optional[str] = None

    def _remove_auth_from_netloc(self, netloc: str) -> str:
        if "@" not in netloc:
            return netloc
        user_pass, netloc_no_user_pass = netloc.split("@", 1)
        if (
            isinstance(self.info, VcsInfo)
            and self.info.vcs == "git"
            and user_pass == "git"
        ):
            return netloc
        if ENV_VAR_RE.match(user_pass):
            return netloc
        return netloc_no_user_pass

    @property
    def redacted_url(self) -> str:
        """url with user:password part removed unless it is formed with
        environment variables as specified in PEP 610, or it is ``git``
        in the case of a git URL.
        """
        purl = urllib.parse.urlsplit(self.url)
        netloc = self._remove_auth_from_netloc(purl.netloc)
        surl = urllib.parse.urlunsplit(
            (purl.scheme, netloc, purl.path, purl.query, purl.fragment)
        )
        return surl

    def validate(self) -> None:
        self.from_dict(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DirectUrl":
        return DirectUrl(
            url=_get_required(d, str, "url"),
            subdirectory=_get(d, str, "subdirectory"),
            info=_exactly_one_of(
                [
                    ArchiveInfo._from_dict(_get(d, dict, "archive_info")),
                    DirInfo._from_dict(_get(d, dict, "dir_info")),
                    VcsInfo._from_dict(_get(d, dict, "vcs_info")),
                ]
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        res = _filter_none(
            url=self.redacted_url,
            subdirectory=self.subdirectory,
        )
        res[self.info.name] = self.info._to_dict()
        return res

    @classmethod
    def from_json(cls, s: str) -> "DirectUrl":
        return cls.from_dict(json.loads(s))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    def is_local_editable(self) -> bool:
        return isinstance(self.info, DirInfo) and self.info.editable

# === NexusCore/openenv\Lib\site-packages\shortuuid\test_shortuuid.py ===
import os
import string
import sys
import unittest
from collections import defaultdict
from unittest.mock import patch
from uuid import UUID
from uuid import uuid4

from shortuuid.cli import cli
from shortuuid.main import decode
from shortuuid.main import encode
from shortuuid.main import get_alphabet
from shortuuid.main import random
from shortuuid.main import set_alphabet
from shortuuid.main import ShortUUID
from shortuuid.main import uuid

sys.path.insert(0, os.path.abspath(__file__ + "/../.."))


class LegacyShortUUIDTest(unittest.TestCase):
    def test_generation(self):
        self.assertTrue(20 < len(uuid()) < 24)
        self.assertTrue(20 < len(uuid("http://www.example.com/")) < 24)
        self.assertTrue(20 < len(uuid("HTTP://www.example.com/")) < 24)
        self.assertTrue(20 < len(uuid("example.com/")) < 24)

    def test_encoding(self):
        u = UUID("{3b1f8b40-222c-4a6e-b77e-779d5a94e21c}")
        self.assertEqual(encode(u), "CXc85b4rqinB7s5J52TRYb")

    def test_decoding(self):
        u = UUID("{3b1f8b40-222c-4a6e-b77e-779d5a94e21c}")
        self.assertEqual(decode("CXc85b4rqinB7s5J52TRYb"), u)

    def test_alphabet(self):
        backup_alphabet = get_alphabet()

        alphabet = "01"
        set_alphabet(alphabet)
        self.assertEqual(alphabet, get_alphabet())

        set_alphabet("01010101010101")
        self.assertEqual(alphabet, get_alphabet())

        self.assertEqual(set(uuid()), set("01"))
        self.assertTrue(116 < len(uuid()) < 140)

        u = uuid4()
        self.assertEqual(u, decode(encode(u)))

        u = uuid()
        self.assertEqual(u, encode(decode(u)))

        self.assertRaises(ValueError, set_alphabet, "1")
        self.assertRaises(ValueError, set_alphabet, "1111111")

        set_alphabet(backup_alphabet)

        self.assertRaises(ValueError, lambda x: ShortUUID(x), "0")

    def test_random(self):
        self.assertEqual(len(random()), 22)
        for i in range(1, 100):
            self.assertEqual(len(random(i)), i)


class ClassShortUUIDTest(unittest.TestCase):
    def test_generation(self):
        su = ShortUUID()
        self.assertTrue(20 < len(su.uuid()) < 24)
        self.assertTrue(20 < len(su.uuid("http://www.example.com/")) < 24)
        self.assertTrue(20 < len(su.uuid("HTTP://www.example.com/")) < 24)
        self.assertTrue(20 < len(su.uuid("example.com/")) < 24)

    def test_encoding(self):
        su = ShortUUID()
        u = UUID("{3b1f8b40-222c-4a6e-b77e-779d5a94e21c}")
        self.assertEqual(su.encode(u), "CXc85b4rqinB7s5J52TRYb")

    def test_decoding(self):
        su = ShortUUID()
        u = UUID("{3b1f8b40-222c-4a6e-b77e-779d5a94e21c}")
        self.assertEqual(su.decode("CXc85b4rqinB7s5J52TRYb"), u)

    def test_random(self):
        su = ShortUUID()
        for i in range(1000):
            self.assertEqual(len(su.random()), 22)

        for i in range(1, 100):
            self.assertEqual(len(su.random(i)), i)

    def test_alphabet(self):
        alphabet = "01"
        su1 = ShortUUID(alphabet)
        su2 = ShortUUID()

        self.assertEqual(alphabet, su1.get_alphabet())

        su1.set_alphabet("01010101010101")
        self.assertEqual(alphabet, su1.get_alphabet())

        self.assertEqual(set(su1.uuid()), set("01"))
        self.assertTrue(116 < len(su1.uuid()) < 140)
        self.assertTrue(20 < len(su2.uuid()) < 24)

        u = uuid4()
        self.assertEqual(u, su1.decode(su1.encode(u)))

        u = su1.uuid()
        self.assertEqual(u, su1.encode(su1.decode(u)))

        self.assertRaises(ValueError, su1.set_alphabet, "1")
        self.assertRaises(ValueError, su1.set_alphabet, "1111111")

    def test_encoded_length(self):
        su1 = ShortUUID()
        self.assertEqual(su1.encoded_length(), 22)

        base64_alphabet = (
            string.ascii_uppercase + string.ascii_lowercase + string.digits + "+/"
        )

        su2 = ShortUUID(base64_alphabet)
        self.assertEqual(su2.encoded_length(), 22)

        binary_alphabet = "01"
        su3 = ShortUUID(binary_alphabet)
        self.assertEqual(su3.encoded_length(), 128)

        su4 = ShortUUID()
        self.assertEqual(su4.encoded_length(num_bytes=8), 11)


class ShortUUIDPaddingTest(unittest.TestCase):
    def test_padding(self):
        su = ShortUUID()
        random_uid = uuid4()
        smallest_uid = UUID(int=0)

        encoded_random = su.encode(random_uid)
        encoded_small = su.encode(smallest_uid)

        self.assertEqual(len(encoded_random), len(encoded_small))

    def test_decoding(self):
        su = ShortUUID()
        random_uid = uuid4()
        smallest_uid = UUID(int=0)

        encoded_random = su.encode(random_uid)
        encoded_small = su.encode(smallest_uid)

        self.assertEqual(su.decode(encoded_small), smallest_uid)
        self.assertEqual(su.decode(encoded_random), random_uid)

    def test_consistency(self):
        su = ShortUUID()
        num_iterations = 1000
        uid_lengths = defaultdict(int)

        for count in range(num_iterations):
            random_uid = uuid4()
            encoded_random = su.encode(random_uid)
            uid_lengths[len(encoded_random)] += 1
            decoded_random = su.decode(encoded_random)

            self.assertEqual(random_uid, decoded_random)

        self.assertEqual(len(uid_lengths), 1)
        uid_length = next(iter(uid_lengths.keys()))  # Get the 1 value

        self.assertEqual(uid_lengths[uid_length], num_iterations)


class EncodingEdgeCasesTest(unittest.TestCase):
    def test_decode_dict(self):
        su = ShortUUID()
        self.assertRaises(ValueError, su.encode, [])
        self.assertRaises(ValueError, su.encode, {})
        self.assertRaises(ValueError, su.decode, (2,))
        self.assertRaises(ValueError, su.encode, 42)
        self.assertRaises(ValueError, su.encode, 42.0)


class DecodingEdgeCasesTest(unittest.TestCase):
    def test_decode_dict(self):
        su = ShortUUID()
        self.assertRaises(ValueError, su.decode, [])
        self.assertRaises(ValueError, su.decode, {})
        self.assertRaises(ValueError, su.decode, (2,))
        self.assertRaises(ValueError, su.decode, 42)
        self.assertRaises(ValueError, su.decode, 42.0)


class CliTest(unittest.TestCase):
    @patch("shortuuid.cli.print")
    def test_shortuuid_command_produces_uuid(self, mock_print):
        # When we call the main cli function
        cli([])
        # Then a shortuuid is printed out
        mock_print.assert_called()
        terminal_output = mock_print.call_args[0][0]
        self.assertEqual(len(terminal_output), 22)

    @patch("shortuuid.cli.print")
    def test_encode_command(self, mock_print):
        cli(["encode", "3b1f8b40-222c-4a6e-b77e-779d5a94e21c"])

        terminal_output = mock_print.call_args[0][0]
        self.assertEqual(terminal_output, "CXc85b4rqinB7s5J52TRYb")

    @patch("shortuuid.cli.print")
    def test_decode_command(self, mock_print):
        cli(["decode", "CXc85b4rqinB7s5J52TRYb"])

        terminal_output = mock_print.call_args[0][0]
        self.assertEqual(terminal_output, "3b1f8b40-222c-4a6e-b77e-779d5a94e21c")


if __name__ == "__main__":
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\starlette\websockets.py ===
from __future__ import annotations

import enum
import json
import typing

from starlette.requests import HTTPConnection
from starlette.responses import Response
from starlette.types import Message, Receive, Scope, Send


class WebSocketState(enum.Enum):
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2
    RESPONSE = 3


class WebSocketDisconnect(Exception):
    def __init__(self, code: int = 1000, reason: str | None = None) -> None:
        self.code = code
        self.reason = reason or ""


class WebSocket(HTTPConnection):
    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        super().__init__(scope)
        assert scope["type"] == "websocket"
        self._receive = receive
        self._send = send
        self.client_state = WebSocketState.CONNECTING
        self.application_state = WebSocketState.CONNECTING

    async def receive(self) -> Message:
        """
        Receive ASGI websocket messages, ensuring valid state transitions.
        """
        if self.client_state == WebSocketState.CONNECTING:
            message = await self._receive()
            message_type = message["type"]
            if message_type != "websocket.connect":
                raise RuntimeError(
                    'Expected ASGI message "websocket.connect", '
                    f"but got {message_type!r}"
                )
            self.client_state = WebSocketState.CONNECTED
            return message
        elif self.client_state == WebSocketState.CONNECTED:
            message = await self._receive()
            message_type = message["type"]
            if message_type not in {"websocket.receive", "websocket.disconnect"}:
                raise RuntimeError(
                    'Expected ASGI message "websocket.receive" or '
                    f'"websocket.disconnect", but got {message_type!r}'
                )
            if message_type == "websocket.disconnect":
                self.client_state = WebSocketState.DISCONNECTED
            return message
        else:
            raise RuntimeError(
                'Cannot call "receive" once a disconnect message has been received.'
            )

    async def send(self, message: Message) -> None:
        """
        Send ASGI websocket messages, ensuring valid state transitions.
        """
        if self.application_state == WebSocketState.CONNECTING:
            message_type = message["type"]
            if message_type not in {
                "websocket.accept",
                "websocket.close",
                "websocket.http.response.start",
            }:
                raise RuntimeError(
                    'Expected ASGI message "websocket.accept",'
                    '"websocket.close" or "websocket.http.response.start",'
                    f"but got {message_type!r}"
                )
            if message_type == "websocket.close":
                self.application_state = WebSocketState.DISCONNECTED
            elif message_type == "websocket.http.response.start":
                self.application_state = WebSocketState.RESPONSE
            else:
                self.application_state = WebSocketState.CONNECTED
            await self._send(message)
        elif self.application_state == WebSocketState.CONNECTED:
            message_type = message["type"]
            if message_type not in {"websocket.send", "websocket.close"}:
                raise RuntimeError(
                    'Expected ASGI message "websocket.send" or "websocket.close", '
                    f"but got {message_type!r}"
                )
            if message_type == "websocket.close":
                self.application_state = WebSocketState.DISCONNECTED
            try:
                await self._send(message)
            except OSError:
                self.application_state = WebSocketState.DISCONNECTED
                raise WebSocketDisconnect(code=1006)
        elif self.application_state == WebSocketState.RESPONSE:
            message_type = message["type"]
            if message_type != "websocket.http.response.body":
                raise RuntimeError(
                    'Expected ASGI message "websocket.http.response.body", '
                    f"but got {message_type!r}"
                )
            if not message.get("more_body", False):
                self.application_state = WebSocketState.DISCONNECTED
            await self._send(message)
        else:
            raise RuntimeError('Cannot call "send" once a close message has been sent.')

    async def accept(
        self,
        subprotocol: str | None = None,
        headers: typing.Iterable[tuple[bytes, bytes]] | None = None,
    ) -> None:
        headers = headers or []

        if self.client_state == WebSocketState.CONNECTING:
            # If we haven't yet seen the 'connect' message, then wait for it first.
            await self.receive()
        await self.send(
            {"type": "websocket.accept", "subprotocol": subprotocol, "headers": headers}
        )

    def _raise_on_disconnect(self, message: Message) -> None:
        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message["code"], message.get("reason"))

    async def receive_text(self) -> str:
        if self.application_state != WebSocketState.CONNECTED:
            raise RuntimeError(
                'WebSocket is not connected. Need to call "accept" first.'
            )
        message = await self.receive()
        self._raise_on_disconnect(message)
        return typing.cast(str, message["text"])

    async def receive_bytes(self) -> bytes:
        if self.application_state != WebSocketState.CONNECTED:
            raise RuntimeError(
                'WebSocket is not connected. Need to call "accept" first.'
            )
        message = await self.receive()
        self._raise_on_disconnect(message)
        return typing.cast(bytes, message["bytes"])

    async def receive_json(self, mode: str = "text") -> typing.Any:
        if mode not in {"text", "binary"}:
            raise RuntimeError('The "mode" argument should be "text" or "binary".')
        if self.application_state != WebSocketState.CONNECTED:
            raise RuntimeError(
                'WebSocket is not connected. Need to call "accept" first.'
            )
        message = await self.receive()
        self._raise_on_disconnect(message)

        if mode == "text":
            text = message["text"]
        else:
            text = message["bytes"].decode("utf-8")
        return json.loads(text)

    async def iter_text(self) -> typing.AsyncIterator[str]:
        try:
            while True:
                yield await self.receive_text()
        except WebSocketDisconnect:
            pass

    async def iter_bytes(self) -> typing.AsyncIterator[bytes]:
        try:
            while True:
                yield await self.receive_bytes()
        except WebSocketDisconnect:
            pass

    async def iter_json(self) -> typing.AsyncIterator[typing.Any]:
        try:
            while True:
                yield await self.receive_json()
        except WebSocketDisconnect:
            pass

    async def send_text(self, data: str) -> None:
        await self.send({"type": "websocket.send", "text": data})

    async def send_bytes(self, data: bytes) -> None:
        await self.send({"type": "websocket.send", "bytes": data})

    async def send_json(self, data: typing.Any, mode: str = "text") -> None:
        if mode not in {"text", "binary"}:
            raise RuntimeError('The "mode" argument should be "text" or "binary".')
        text = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        if mode == "text":
            await self.send({"type": "websocket.send", "text": text})
        else:
            await self.send({"type": "websocket.send", "bytes": text.encode("utf-8")})

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        await self.send(
            {"type": "websocket.close", "code": code, "reason": reason or ""}
        )

    async def send_denial_response(self, response: Response) -> None:
        if "websocket.http.response" in self.scope.get("extensions", {}):
            await response(self.scope, self.receive, self.send)
        else:
            raise RuntimeError(
                "The server doesn't support the Websocket Denial Response extension."
            )


class WebSocketClose:
    def __init__(self, code: int = 1000, reason: str | None = None) -> None:
        self.code = code
        self.reason = reason or ""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {"type": "websocket.close", "code": self.code, "reason": self.reason}
        )

# === NexusCore/openenv\Lib\site-packages\win32com\universal.py ===
# Code that packs and unpacks the Univgw structures.

# See if we have a special directory for the binaries (for developers)

import pythoncom
from win32com.client import gencache

com_error = pythoncom.com_error  # Re-exported alias


def RegisterInterfaces(typelibGUID, lcid, major, minor, interface_names=None):
    ret = []  # return a list of (dispid, funcname for our policy's benefit
    # First see if we have makepy support.  If so, we can probably satisfy the request without loading the typelib.
    try:
        mod = gencache.GetModuleForTypelib(typelibGUID, lcid, major, minor)
    except ImportError:
        mod = None
    if mod is None:
        import win32com.client.build

        # Load up the typelib and build (but don't cache) it now
        tlb = pythoncom.LoadRegTypeLib(typelibGUID, major, minor, lcid)
        typecomp_lib = tlb.GetTypeComp()
        if interface_names is None:
            interface_names = []
            for i in range(tlb.GetTypeInfoCount()):
                info = tlb.GetTypeInfo(i)
                doc = tlb.GetDocumentation(i)
                attr = info.GetTypeAttr()
                if attr.typekind == pythoncom.TKIND_INTERFACE or (
                    attr.typekind == pythoncom.TKIND_DISPATCH
                    and attr.wTypeFlags & pythoncom.TYPEFLAG_FDUAL
                ):
                    interface_names.append(doc[0])
        for name in interface_names:
            type_info, type_comp = typecomp_lib.BindType(
                name,
            )
            # Not sure why we don't get an exception here - BindType's C
            # impl looks correct..
            if type_info is None:
                raise ValueError(f"The interface '{name}' can not be located")
            # If we got back a Dispatch interface, convert to the real interface.
            attr = type_info.GetTypeAttr()
            if attr.typekind == pythoncom.TKIND_DISPATCH:
                refhtype = type_info.GetRefTypeOfImplType(-1)
                type_info = type_info.GetRefTypeInfo(refhtype)
                attr = type_info.GetTypeAttr()
            item = win32com.client.build.VTableItem(
                type_info, attr, type_info.GetDocumentation(-1)
            )
            _doCreateVTable(
                item.clsid, item.python_name, item.bIsDispatch, item.vtableFuncs
            )
            for info in item.vtableFuncs:
                names, dispid, desc = info
                invkind = desc[4]
                ret.append((dispid, invkind, names[0]))
    else:
        # Cool - can used cached info.
        for name in interface_names or mod.VTablesToClassMap.values():
            try:
                iid = mod.NamesToIIDMap[name]
            except KeyError:
                raise ValueError(
                    f"Interface '{name}' does not exist in this cached typelib"
                )
            # print("Processing interface", name)
            sub_mod = gencache.GetModuleForCLSID(iid)
            is_dispatch = getattr(sub_mod, name + "_vtables_dispatch_", None)
            method_defs = getattr(sub_mod, name + "_vtables_", None)
            if is_dispatch is None or method_defs is None:
                raise ValueError(f"Interface '{name}' is IDispatch only")

            # And create the univgw defn
            _doCreateVTable(iid, name, is_dispatch, method_defs)
            for info in method_defs:
                names, dispid, desc = info
                invkind = desc[4]
                ret.append((dispid, invkind, names[0]))
    return ret


def _doCreateVTable(iid, interface_name, is_dispatch, method_defs):
    defn = Definition(iid, is_dispatch, method_defs)
    vtbl = pythoncom._univgw.CreateVTable(defn, is_dispatch)
    pythoncom._univgw.RegisterVTable(vtbl, iid, interface_name)


def _CalcTypeSize(typeTuple):
    t = typeTuple[0]
    if t & (pythoncom.VT_BYREF | pythoncom.VT_ARRAY):
        # It's a pointer.
        cb = pythoncom._univgw.SizeOfVT(pythoncom.VT_PTR)[1]
    elif t == pythoncom.VT_RECORD:
        # Just because a type library uses records doesn't mean the user
        # is trying to.  We need to better place to warn about this, but it
        # isn't here.
        # try:
        #     import warnings
        #     warnings.warn("warning: records are known to not work for vtable interfaces")
        # except ImportError:
        #     print("warning: records are known to not work for vtable interfaces")
        cb = pythoncom._univgw.SizeOfVT(pythoncom.VT_PTR)[1]
        # cb = typeInfo.GetTypeAttr().cbSizeInstance
    else:
        cb = pythoncom._univgw.SizeOfVT(t)[1]
    return cb


class Arg:
    def __init__(self, arg_info, name=None):
        self.name = name
        self.vt, self.inOut, self.default, self.clsid = arg_info
        self.size = _CalcTypeSize(arg_info)
        # Offset from the beginning of the arguments of the stack.
        self.offset = 0


class Method:
    def __init__(self, method_info, isEventSink=0):
        all_names, dispid, desc = method_info
        name = all_names[0]
        names = all_names[1:]
        invkind = desc[4]
        arg_defs = desc[2]
        ret_def = desc[8]

        self.dispid = dispid
        self.invkind = invkind
        # We don't use this ATM.
        #        self.ret = Arg(ret_def)
        if isEventSink and name[:2] != "On":
            name = "On%s" % name
        self.name = name
        cbArgs = 0
        self.args = []
        for argDesc in arg_defs:
            arg = Arg(argDesc)
            arg.offset = cbArgs
            cbArgs += arg.size
            self.args.append(arg)
        self.cbArgs = cbArgs
        self._gw_in_args = self._GenerateInArgTuple()
        self._gw_out_args = self._GenerateOutArgTuple()

    def _GenerateInArgTuple(self):
        # Given a method, generate the in argument tuple
        l = []
        for arg in self.args:
            if arg.inOut & pythoncom.PARAMFLAG_FIN or arg.inOut == 0:
                l.append((arg.vt, arg.offset, arg.size))
        return tuple(l)

    def _GenerateOutArgTuple(self):
        # Given a method, generate the out argument tuple
        l = []
        for arg in self.args:
            if (
                arg.inOut & pythoncom.PARAMFLAG_FOUT
                or arg.inOut & pythoncom.PARAMFLAG_FRETVAL
                or arg.inOut == 0
            ):
                l.append((arg.vt, arg.offset, arg.size, arg.clsid))
        return tuple(l)


class Definition:
    def __init__(self, iid, is_dispatch, method_defs):
        self._iid = iid
        self._methods = []
        self._is_dispatch = is_dispatch
        for info in method_defs:
            entry = Method(info)
            self._methods.append(entry)

    def iid(self):
        return self._iid

    def vtbl_argsizes(self):
        return [m.cbArgs for m in self._methods]

    def vtbl_argcounts(self):
        return [len(m.args) for m in self._methods]

    def dispatch(
        self,
        ob,
        index,
        argPtr,
        ReadFromInTuple=pythoncom._univgw.ReadFromInTuple,
        WriteFromOutTuple=pythoncom._univgw.WriteFromOutTuple,
    ):
        "Dispatch a call to an interface method."
        meth = self._methods[index]
        # Infer S_OK if they don't return anything bizarre.
        hr = 0
        args = ReadFromInTuple(meth._gw_in_args, argPtr)
        # If ob is a dispatcher, ensure a policy
        ob = getattr(ob, "policy", ob)
        # Ensure the correct dispid is setup
        ob._dispid_to_func_[meth.dispid] = meth.name
        retVal = ob._InvokeEx_(meth.dispid, 0, meth.invkind, args, None, None)
        # None is an allowed return value stating that
        # the code doesn't want to touch any output arguments.
        if isinstance(retVal, tuple):  # Like pythoncom, we special case a tuple.
            # However, if they want to return a specific HRESULT,
            # then they have to return all of the out arguments
            # AND the HRESULT.
            if len(retVal) == len(meth._gw_out_args) + 1:
                hr = retVal[0]
                retVal = retVal[1:]
            else:
                raise TypeError(
                    "Expected {} return values, got: {}".format(
                        len(meth._gw_out_args) + 1, len(retVal)
                    )
                )
        else:
            retVal = [retVal]
            retVal.extend([None] * (len(meth._gw_out_args) - 1))
            retVal = tuple(retVal)
        WriteFromOutTuple(retVal, meth._gw_out_args, argPtr)
        return hr

# === NexusCore/openenv\Lib\site-packages\zmq\asyncio.py ===
"""AsyncIO support for zmq

Requires asyncio and Python 3.
"""

# Copyright (c) PyZMQ Developers.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import selectors
import sys
import warnings
from asyncio import Future, SelectorEventLoop
from weakref import WeakKeyDictionary

import zmq as _zmq
from zmq import _future

# registry of asyncio loop : selector thread
_selectors: WeakKeyDictionary = WeakKeyDictionary()


class ProactorSelectorThreadWarning(RuntimeWarning):
    """Warning class for notifying about the extra thread spawned by tornado

    We automatically support proactor via tornado's AddThreadSelectorEventLoop"""


def _get_selector_windows(
    asyncio_loop,
) -> asyncio.AbstractEventLoop:
    """Get selector-compatible loop

    Returns an object with ``add_reader`` family of methods,
    either the loop itself or a SelectorThread instance.

    Workaround Windows proactor removal of
    *reader methods, which we need for zmq sockets.
    """

    if asyncio_loop in _selectors:
        return _selectors[asyncio_loop]

    # detect add_reader instead of checking for proactor?
    if hasattr(asyncio, "ProactorEventLoop") and isinstance(
        asyncio_loop,
        asyncio.ProactorEventLoop,  # type: ignore
    ):
        try:
            from tornado.platform.asyncio import AddThreadSelectorEventLoop
        except ImportError:
            raise RuntimeError(
                "Proactor event loop does not implement add_reader family of methods required for zmq."
                " zmq will work with proactor if tornado >= 6.1 can be found."
                " Use `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())`"
                " or install 'tornado>=6.1' to avoid this error."
            )

        warnings.warn(
            "Proactor event loop does not implement add_reader family of methods required for zmq."
            " Registering an additional selector thread for add_reader support via tornado."
            " Use `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())`"
            " to avoid this warning.",
            RuntimeWarning,
            # stacklevel 5 matches most likely zmq.asyncio.Context().socket()
            stacklevel=5,
        )

        selector_loop = _selectors[asyncio_loop] = AddThreadSelectorEventLoop(
            asyncio_loop
        )  # type: ignore

        # patch loop.close to also close the selector thread
        loop_close = asyncio_loop.close

        def _close_selector_and_loop():
            # restore original before calling selector.close,
            # which in turn calls eventloop.close!
            asyncio_loop.close = loop_close
            _selectors.pop(asyncio_loop, None)
            selector_loop.close()

        asyncio_loop.close = _close_selector_and_loop  # type: ignore # mypy bug - assign a function to method
        return selector_loop
    else:
        return asyncio_loop


def _get_selector_noop(loop) -> asyncio.AbstractEventLoop:
    """no-op on non-Windows"""
    return loop


if sys.platform == "win32":
    _get_selector = _get_selector_windows
else:
    _get_selector = _get_selector_noop


class _AsyncIO:
    _Future = Future
    _WRITE = selectors.EVENT_WRITE
    _READ = selectors.EVENT_READ

    def _default_loop(self):
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            warnings.warn(
                "No running event loop. zmq.asyncio should be used from within an asyncio loop.",
                RuntimeWarning,
                stacklevel=4,
            )
        # get_event_loop deprecated in 3.10:
        return asyncio.get_event_loop()


class Poller(_AsyncIO, _future._AsyncPoller):
    """Poller returning asyncio.Future for poll results."""

    def _watch_raw_socket(self, loop, socket, evt, f):
        """Schedule callback for a raw socket"""
        selector = _get_selector(loop)
        if evt & self._READ:
            selector.add_reader(socket, lambda *args: f())
        if evt & self._WRITE:
            selector.add_writer(socket, lambda *args: f())

    def _unwatch_raw_sockets(self, loop, *sockets):
        """Unschedule callback for a raw socket"""
        selector = _get_selector(loop)
        for socket in sockets:
            selector.remove_reader(socket)
            selector.remove_writer(socket)


class Socket(_AsyncIO, _future._AsyncSocket):
    """Socket returning asyncio Futures for send/recv/poll methods."""

    _poller_class = Poller

    def _get_selector(self, io_loop=None):
        if io_loop is None:
            io_loop = self._get_loop()
        return _get_selector(io_loop)

    def _init_io_state(self, io_loop=None):
        """initialize the ioloop event handler"""
        self._get_selector(io_loop).add_reader(
            self._fd, lambda: self._handle_events(0, 0)
        )

    def _clear_io_state(self):
        """clear any ioloop event handler

        called once at close
        """
        loop = self._current_loop
        if loop and not loop.is_closed() and self._fd != -1:
            self._get_selector(loop).remove_reader(self._fd)


Poller._socket_class = Socket


class Context(_zmq.Context[Socket]):
    """Context for creating asyncio-compatible Sockets"""

    _socket_class = Socket

    # avoid sharing instance with base Context class
    _instance = None

    # overload with no changes to satisfy pyright
    def __init__(
        self: Context,
        io_threads: int | _zmq.Context = 1,
        shadow: _zmq.Context | int = 0,
    ) -> None:
        super().__init__(io_threads, shadow)  # type: ignore


class ZMQEventLoop(SelectorEventLoop):
    """DEPRECATED: AsyncIO eventloop using zmq_poll.

    pyzmq sockets should work with any asyncio event loop as of pyzmq 17.
    """

    def __init__(self, selector=None):
        _deprecated()
        return super().__init__(selector)


_loop = None


def _deprecated():
    if _deprecated.called:  # type: ignore
        return
    _deprecated.called = True  # type: ignore

    warnings.warn(
        "ZMQEventLoop and zmq.asyncio.install are deprecated in pyzmq 17. Special eventloop integration is no longer needed.",
        DeprecationWarning,
        stacklevel=3,
    )


_deprecated.called = False  # type: ignore


def install():
    """DEPRECATED: No longer needed in pyzmq 17"""
    _deprecated()


__all__ = [
    "Context",
    "Socket",
    "Poller",
    "ZMQEventLoop",
    "install",
]

# === NexusCore/openenv\Lib\site-packages\jedi\inference\dynamic_params.py ===
"""
One of the really important features of |jedi| is to have an option to
understand code like this::

    def foo(bar):
        bar. # completion here
    foo(1)

There's no doubt wheter bar is an ``int`` or not, but if there's also a call
like ``foo('str')``, what would happen? Well, we'll just show both. Because
that's what a human would expect.

It works as follows:

- |Jedi| sees a param
- search for function calls named ``foo``
- execute these calls and check the input.
"""

from jedi import settings
from jedi import debug
from jedi.parser_utils import get_parent_scope
from jedi.inference.cache import inference_state_method_cache
from jedi.inference.arguments import TreeArguments
from jedi.inference.param import get_executed_param_names
from jedi.inference.helpers import is_stdlib_path
from jedi.inference.utils import to_list
from jedi.inference.value import instance
from jedi.inference.base_value import ValueSet, NO_VALUES
from jedi.inference.references import get_module_contexts_containing_name
from jedi.inference import recursion


MAX_PARAM_SEARCHES = 20


def _avoid_recursions(func):
    def wrapper(function_value, param_index):
        inf = function_value.inference_state
        with recursion.execution_allowed(inf, function_value.tree_node) as allowed:
            # We need to catch recursions that may occur, because an
            # anonymous functions can create an anonymous parameter that is
            # more or less self referencing.
            if allowed:
                inf.dynamic_params_depth += 1
                try:
                    return func(function_value, param_index)
                finally:
                    inf.dynamic_params_depth -= 1
            return NO_VALUES
    return wrapper


@debug.increase_indent
@_avoid_recursions
def dynamic_param_lookup(function_value, param_index):
    """
    A dynamic search for param values. If you try to complete a type:

    >>> def func(foo):
    ...     foo
    >>> func(1)
    >>> func("")

    It is not known what the type ``foo`` without analysing the whole code. You
    have to look for all calls to ``func`` to find out what ``foo`` possibly
    is.
    """
    if not function_value.inference_state.do_dynamic_params_search:
        return NO_VALUES

    funcdef = function_value.tree_node

    path = function_value.get_root_context().py__file__()
    if path is not None and is_stdlib_path(path):
        # We don't want to search for references in the stdlib. Usually people
        # don't work with it (except if you are a core maintainer, sorry).
        # This makes everything slower. Just disable it and run the tests,
        # you will see the slowdown, especially in 3.6.
        return NO_VALUES

    if funcdef.type == 'lambdef':
        string_name = _get_lambda_name(funcdef)
        if string_name is None:
            return NO_VALUES
    else:
        string_name = funcdef.name.value
    debug.dbg('Dynamic param search in %s.', string_name, color='MAGENTA')

    module_context = function_value.get_root_context()
    arguments_list = _search_function_arguments(module_context, funcdef, string_name)
    values = ValueSet.from_sets(
        get_executed_param_names(
            function_value, arguments
        )[param_index].infer()
        for arguments in arguments_list
    )
    debug.dbg('Dynamic param result finished', color='MAGENTA')
    return values


@inference_state_method_cache(default=None)
@to_list
def _search_function_arguments(module_context, funcdef, string_name):
    """
    Returns a list of param names.
    """
    compare_node = funcdef
    if string_name == '__init__':
        cls = get_parent_scope(funcdef)
        if cls.type == 'classdef':
            string_name = cls.name.value
            compare_node = cls

    found_arguments = False
    i = 0
    inference_state = module_context.inference_state

    if settings.dynamic_params_for_other_modules:
        module_contexts = get_module_contexts_containing_name(
            inference_state, [module_context], string_name,
            # Limit the amounts of files to be opened massively.
            limit_reduction=5,
        )
    else:
        module_contexts = [module_context]

    for for_mod_context in module_contexts:
        for name, trailer in _get_potential_nodes(for_mod_context, string_name):
            i += 1

            # This is a simple way to stop Jedi's dynamic param recursion
            # from going wild: The deeper Jedi's in the recursion, the less
            # code should be inferred.
            if i * inference_state.dynamic_params_depth > MAX_PARAM_SEARCHES:
                return

            random_context = for_mod_context.create_context(name)
            for arguments in _check_name_for_execution(
                    inference_state, random_context, compare_node, name, trailer):
                found_arguments = True
                yield arguments

        # If there are results after processing a module, we're probably
        # good to process. This is a speed optimization.
        if found_arguments:
            return


def _get_lambda_name(node):
    stmt = node.parent
    if stmt.type == 'expr_stmt':
        first_operator = next(stmt.yield_operators(), None)
        if first_operator == '=':
            first = stmt.children[0]
            if first.type == 'name':
                return first.value

    return None


def _get_potential_nodes(module_value, func_string_name):
    try:
        names = module_value.tree_node.get_used_names()[func_string_name]
    except KeyError:
        return

    for name in names:
        bracket = name.get_next_leaf()
        trailer = bracket.parent
        if trailer.type == 'trailer' and bracket == '(':
            yield name, trailer


def _check_name_for_execution(inference_state, context, compare_node, name, trailer):
    from jedi.inference.value.function import BaseFunctionExecutionContext

    def create_args(value):
        arglist = trailer.children[1]
        if arglist == ')':
            arglist = None
        args = TreeArguments(inference_state, context, arglist, trailer)
        from jedi.inference.value.instance import InstanceArguments
        if value.tree_node.type == 'classdef':
            created_instance = instance.TreeInstance(
                inference_state,
                value.parent_context,
                value,
                args
            )
            return InstanceArguments(created_instance, args)
        else:
            if value.is_bound_method():
                args = InstanceArguments(value.instance, args)
            return args

    for value in inference_state.infer(context, name):
        value_node = value.tree_node
        if compare_node == value_node:
            yield create_args(value)
        elif isinstance(value.parent_context, BaseFunctionExecutionContext) \
                and compare_node.type == 'funcdef':
            # Here we're trying to find decorators by checking the first
            # parameter. It's not very generic though. Should find a better
            # solution that also applies to nested decorators.
            param_names = value.parent_context.get_param_names()
            if len(param_names) != 1:
                continue
            values = param_names[0].infer()
            if [v.tree_node for v in values] == [compare_node]:
                # Found a decorator.
                module_context = context.get_root_context()
                execution_context = value.as_context(create_args(value))
                potential_nodes = _get_potential_nodes(module_context, param_names[0].string_name)
                for name, trailer in potential_nodes:
                    if value_node.start_pos < name.start_pos < value_node.end_pos:
                        random_context = execution_context.create_context(name)
                        yield from _check_name_for_execution(
                            inference_state,
                            random_context,
                            compare_node,
                            name,
                            trailer
                        )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\openai\transcriptions\handler.py ===
from typing import Optional, Union

import httpx
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel

import litellm
from litellm.litellm_core_utils.audio_utils.utils import get_audio_file_name
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.llms.base_llm.audio_transcription.transformation import (
    BaseAudioTranscriptionConfig,
)
from litellm.types.utils import FileTypes
from litellm.utils import (
    TranscriptionResponse,
    convert_to_model_response_object,
    extract_duration_from_srt_or_vtt,
)

from ..openai import OpenAIChatCompletion


class OpenAIAudioTranscription(OpenAIChatCompletion):
    # Audio Transcriptions
    async def make_openai_audio_transcriptions_request(
        self,
        openai_aclient: AsyncOpenAI,
        data: dict,
        timeout: Union[float, httpx.Timeout],
    ):
        """
        Helper to:
        - call openai_aclient.audio.transcriptions.with_raw_response when litellm.return_response_headers is True
        - call openai_aclient.audio.transcriptions.create by default
        """
        try:
            raw_response = (
                await openai_aclient.audio.transcriptions.with_raw_response.create(
                    **data, timeout=timeout
                )
            )  # type: ignore
            headers = dict(raw_response.headers)
            response = raw_response.parse()

            return headers, response
        except Exception as e:
            raise e

    def make_sync_openai_audio_transcriptions_request(
        self,
        openai_client: OpenAI,
        data: dict,
        timeout: Union[float, httpx.Timeout],
    ):
        """
        Helper to:
        - call openai_aclient.audio.transcriptions.with_raw_response when litellm.return_response_headers is True
        - call openai_aclient.audio.transcriptions.create by default
        """
        try:
            if litellm.return_response_headers is True:
                raw_response = (
                    openai_client.audio.transcriptions.with_raw_response.create(
                        **data, timeout=timeout
                    )
                )  # type: ignore
                headers = dict(raw_response.headers)
                response = raw_response.parse()
                return headers, response
            else:
                response = openai_client.audio.transcriptions.create(**data, timeout=timeout)  # type: ignore
                return None, response
        except Exception as e:
            raise e

    def audio_transcriptions(
        self,
        model: str,
        audio_file: FileTypes,
        optional_params: dict,
        litellm_params: dict,
        model_response: TranscriptionResponse,
        timeout: float,
        max_retries: int,
        logging_obj: LiteLLMLoggingObj,
        api_key: Optional[str],
        api_base: Optional[str],
        client=None,
        atranscription: bool = False,
        provider_config: Optional[BaseAudioTranscriptionConfig] = None,
    ) -> TranscriptionResponse:
        """
        Handle audio transcription request
        """
        if provider_config is not None:
            data = provider_config.transform_audio_transcription_request(
                model=model,
                audio_file=audio_file,
                optional_params=optional_params,
                litellm_params=litellm_params,
            )

            if isinstance(data, bytes):
                raise ValueError("OpenAI transformation route requires a dict")
        else:
            data = {"model": model, "file": audio_file, **optional_params}

        if atranscription is True:
            return self.async_audio_transcriptions(  # type: ignore
                audio_file=audio_file,
                data=data,
                model_response=model_response,
                timeout=timeout,
                api_key=api_key,
                api_base=api_base,
                client=client,
                max_retries=max_retries,
                logging_obj=logging_obj,
            )

        openai_client: OpenAI = self._get_openai_client(  # type: ignore
            is_async=False,
            api_key=api_key,
            api_base=api_base,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=None,
            api_key=openai_client.api_key,
            additional_args={
                "api_base": openai_client._base_url._uri_reference,
                "atranscription": True,
                "complete_input_dict": data,
            },
        )
        _, response = self.make_sync_openai_audio_transcriptions_request(
            openai_client=openai_client,
            data=data,
            timeout=timeout,
        )

        if isinstance(response, BaseModel):
            stringified_response = response.model_dump()
        else:
            stringified_response = TranscriptionResponse(text=response).model_dump()

        ## LOGGING
        logging_obj.post_call(
            input=get_audio_file_name(audio_file),
            api_key=api_key,
            additional_args={"complete_input_dict": data},
            original_response=stringified_response,
        )
        hidden_params = {"model": model, "custom_llm_provider": "openai"}
        final_response: TranscriptionResponse = convert_to_model_response_object(response_object=stringified_response, model_response_object=model_response, hidden_params=hidden_params, response_type="audio_transcription")  # type: ignore
        return final_response

    async def async_audio_transcriptions(
        self,
        audio_file: FileTypes,
        data: dict,
        model_response: TranscriptionResponse,
        timeout: float,
        logging_obj: LiteLLMLoggingObj,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        client=None,
        max_retries=None,
    ):
        try:
            openai_aclient: AsyncOpenAI = self._get_openai_client(  # type: ignore
                is_async=True,
                api_key=api_key,
                api_base=api_base,
                timeout=timeout,
                max_retries=max_retries,
                client=client,
            )

            ## LOGGING
            logging_obj.pre_call(
                input=None,
                api_key=openai_aclient.api_key,
                additional_args={
                    "api_base": openai_aclient._base_url._uri_reference,
                    "atranscription": True,
                    "complete_input_dict": data,
                },
            )
            headers, response = await self.make_openai_audio_transcriptions_request(
                openai_aclient=openai_aclient,
                data=data,
                timeout=timeout,
            )
            logging_obj.model_call_details["response_headers"] = headers
            if isinstance(response, BaseModel):
                stringified_response = response.model_dump()
            else:
                duration = extract_duration_from_srt_or_vtt(response)
                stringified_response = TranscriptionResponse(text=response).model_dump()
                stringified_response["duration"] = duration
            ## LOGGING
            logging_obj.post_call(
                input=get_audio_file_name(audio_file),
                api_key=api_key,
                additional_args={"complete_input_dict": data},
                original_response=stringified_response,
            )
            # Extract the actual model from data instead of hardcoding "whisper-1"
            actual_model = data.get("model", "whisper-1")
            hidden_params = {"model": actual_model, "custom_llm_provider": "openai"}
            return convert_to_model_response_object(response_object=stringified_response, model_response_object=model_response, hidden_params=hidden_params, response_type="audio_transcription")  # type: ignore
        except Exception as e:
            ## LOGGING
            logging_obj.post_call(
                input=input,
                api_key=api_key,
                original_response=str(e),
            )
            raise e

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\vertex_embeddings\embedding_handler.py ===
from typing import Literal, Optional, Union

import httpx

import litellm
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObject
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    _get_httpx_client,
    get_async_httpx_client,
)
from litellm.llms.vertex_ai.vertex_ai_non_gemini import VertexAIError
from litellm.llms.vertex_ai.vertex_llm_base import VertexBase
from litellm.types.llms.vertex_ai import *
from litellm.types.utils import EmbeddingResponse

from .types import *


class VertexEmbedding(VertexBase):
    def __init__(self) -> None:
        super().__init__()

    def embedding(
        self,
        model: str,
        input: Union[list, str],
        print_verbose,
        model_response: EmbeddingResponse,
        optional_params: dict,
        logging_obj: LiteLLMLoggingObject,
        custom_llm_provider: Literal[
            "vertex_ai", "vertex_ai_beta", "gemini"
        ],  # if it's vertex_ai or gemini (google ai studio)
        timeout: Optional[Union[float, httpx.Timeout]],
        api_key: Optional[str] = None,
        encoding=None,
        aembedding=False,
        api_base: Optional[str] = None,
        client: Optional[Union[AsyncHTTPHandler, HTTPHandler]] = None,
        vertex_project: Optional[str] = None,
        vertex_location: Optional[str] = None,
        vertex_credentials: Optional[VERTEX_CREDENTIALS_TYPES] = None,
        gemini_api_key: Optional[str] = None,
        extra_headers: Optional[dict] = None,
    ) -> EmbeddingResponse:
        if aembedding is True:
            return self.async_embedding(  # type: ignore
                model=model,
                input=input,
                logging_obj=logging_obj,
                model_response=model_response,
                optional_params=optional_params,
                encoding=encoding,
                custom_llm_provider=custom_llm_provider,
                timeout=timeout,
                api_base=api_base,
                vertex_project=vertex_project,
                vertex_location=vertex_location,
                vertex_credentials=vertex_credentials,
                gemini_api_key=gemini_api_key,
                extra_headers=extra_headers,
            )

        should_use_v1beta1_features = self.is_using_v1beta1_features(
            optional_params=optional_params
        )

        _auth_header, vertex_project = self._ensure_access_token(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider=custom_llm_provider,
        )
        auth_header, api_base = self._get_token_and_url(
            model=model,
            gemini_api_key=gemini_api_key,
            auth_header=_auth_header,
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            vertex_credentials=vertex_credentials,
            stream=False,
            custom_llm_provider=custom_llm_provider,
            api_base=api_base,
            should_use_v1beta1_features=should_use_v1beta1_features,
            mode="embedding",
        )
        headers = self.set_headers(auth_header=auth_header, extra_headers=extra_headers)
        vertex_request: VertexEmbeddingRequest = litellm.vertexAITextEmbeddingConfig.transform_openai_request_to_vertex_embedding_request(
            input=input, optional_params=optional_params, model=model
        )

        _client_params = {}
        if timeout:
            _client_params["timeout"] = timeout
        if client is None or not isinstance(client, HTTPHandler):
            client = _get_httpx_client(params=_client_params)
        else:
            client = client  # type: ignore
        ## LOGGING
        logging_obj.pre_call(
            input=vertex_request,
            api_key="",
            additional_args={
                "complete_input_dict": vertex_request,
                "api_base": api_base,
                "headers": headers,
            },
        )

        try:
            response = client.post(url=api_base, headers=headers, json=vertex_request)  # type: ignore
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise VertexAIError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise VertexAIError(status_code=408, message="Timeout error occurred.")

        _json_response = response.json()
        ## LOGGING POST-CALL
        logging_obj.post_call(
            input=input, api_key=None, original_response=_json_response
        )

        model_response = (
            litellm.vertexAITextEmbeddingConfig.transform_vertex_response_to_openai(
                response=_json_response, model=model, model_response=model_response
            )
        )

        return model_response

    async def async_embedding(
        self,
        model: str,
        input: Union[list, str],
        model_response: litellm.EmbeddingResponse,
        logging_obj: LiteLLMLoggingObject,
        optional_params: dict,
        custom_llm_provider: Literal[
            "vertex_ai", "vertex_ai_beta", "gemini"
        ],  # if it's vertex_ai or gemini (google ai studio)
        timeout: Optional[Union[float, httpx.Timeout]],
        api_base: Optional[str] = None,
        client: Optional[AsyncHTTPHandler] = None,
        vertex_project: Optional[str] = None,
        vertex_location: Optional[str] = None,
        vertex_credentials: Optional[VERTEX_CREDENTIALS_TYPES] = None,
        gemini_api_key: Optional[str] = None,
        extra_headers: Optional[dict] = None,
        encoding=None,
    ) -> litellm.EmbeddingResponse:
        """
        Async embedding implementation
        """
        should_use_v1beta1_features = self.is_using_v1beta1_features(
            optional_params=optional_params
        )
        _auth_header, vertex_project = await self._ensure_access_token_async(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider=custom_llm_provider,
        )
        auth_header, api_base = self._get_token_and_url(
            model=model,
            gemini_api_key=gemini_api_key,
            auth_header=_auth_header,
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            vertex_credentials=vertex_credentials,
            stream=False,
            custom_llm_provider=custom_llm_provider,
            api_base=api_base,
            should_use_v1beta1_features=should_use_v1beta1_features,
            mode="embedding",
        )
        headers = self.set_headers(auth_header=auth_header, extra_headers=extra_headers)
        vertex_request: VertexEmbeddingRequest = litellm.vertexAITextEmbeddingConfig.transform_openai_request_to_vertex_embedding_request(
            input=input, optional_params=optional_params, model=model
        )

        _async_client_params = {}
        if timeout:
            _async_client_params["timeout"] = timeout
        if client is None or not isinstance(client, AsyncHTTPHandler):
            client = get_async_httpx_client(
                params=_async_client_params, llm_provider=litellm.LlmProviders.VERTEX_AI
            )
        else:
            client = client  # type: ignore
        ## LOGGING
        logging_obj.pre_call(
            input=vertex_request,
            api_key="",
            additional_args={
                "complete_input_dict": vertex_request,
                "api_base": api_base,
                "headers": headers,
            },
        )

        try:
            response = await client.post(api_base, headers=headers, json=vertex_request)  # type: ignore
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise VertexAIError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise VertexAIError(status_code=408, message="Timeout error occurred.")

        _json_response = response.json()
        ## LOGGING POST-CALL
        logging_obj.post_call(
            input=input, api_key=None, original_response=_json_response
        )

        model_response = (
            litellm.vertexAITextEmbeddingConfig.transform_vertex_response_to_openai(
                response=_json_response, model=model, model_response=model_response
            )
        )

        return model_response

# === NexusCore/openenv\Lib\site-packages\pip\_internal\commands\show.py ===
import logging
from optparse import Values
from typing import Generator, Iterable, Iterator, List, NamedTuple, Optional

from pip._vendor.packaging.requirements import InvalidRequirement
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.metadata import BaseDistribution, get_default_environment
from pip._internal.utils.misc import write_output

logger = logging.getLogger(__name__)


class ShowCommand(Command):
    """
    Show information about one or more installed packages.

    The output is in RFC-compliant mail header format.
    """

    usage = """
      %prog [options] <package> ..."""
    ignore_require_venv = True

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "-f",
            "--files",
            dest="files",
            action="store_true",
            default=False,
            help="Show the full list of installed files for each package.",
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: List[str]) -> int:
        if not args:
            logger.warning("ERROR: Please provide a package name or names.")
            return ERROR
        query = args

        results = search_packages_info(query)
        if not print_results(
            results, list_files=options.files, verbose=options.verbose
        ):
            return ERROR
        return SUCCESS


class _PackageInfo(NamedTuple):
    name: str
    version: str
    location: str
    editable_project_location: Optional[str]
    requires: List[str]
    required_by: List[str]
    installer: str
    metadata_version: str
    classifiers: List[str]
    summary: str
    homepage: str
    project_urls: List[str]
    author: str
    author_email: str
    license: str
    license_expression: str
    entry_points: List[str]
    files: Optional[List[str]]


def search_packages_info(query: List[str]) -> Generator[_PackageInfo, None, None]:
    """
    Gather details from installed distributions. Print distribution name,
    version, location, and installed files. Installed files requires a
    pip generated 'installed-files.txt' in the distributions '.egg-info'
    directory.
    """
    env = get_default_environment()

    installed = {dist.canonical_name: dist for dist in env.iter_all_distributions()}
    query_names = [canonicalize_name(name) for name in query]
    missing = sorted(
        [name for name, pkg in zip(query, query_names) if pkg not in installed]
    )
    if missing:
        logger.warning("Package(s) not found: %s", ", ".join(missing))

    def _get_requiring_packages(current_dist: BaseDistribution) -> Iterator[str]:
        return (
            dist.metadata["Name"] or "UNKNOWN"
            for dist in installed.values()
            if current_dist.canonical_name
            in {canonicalize_name(d.name) for d in dist.iter_dependencies()}
        )

    for query_name in query_names:
        try:
            dist = installed[query_name]
        except KeyError:
            continue

        try:
            requires = sorted(
                # Avoid duplicates in requirements (e.g. due to environment markers).
                {req.name for req in dist.iter_dependencies()},
                key=str.lower,
            )
        except InvalidRequirement:
            requires = sorted(dist.iter_raw_dependencies(), key=str.lower)

        try:
            required_by = sorted(_get_requiring_packages(dist), key=str.lower)
        except InvalidRequirement:
            required_by = ["#N/A"]

        try:
            entry_points_text = dist.read_text("entry_points.txt")
            entry_points = entry_points_text.splitlines(keepends=False)
        except FileNotFoundError:
            entry_points = []

        files_iter = dist.iter_declared_entries()
        if files_iter is None:
            files: Optional[List[str]] = None
        else:
            files = sorted(files_iter)

        metadata = dist.metadata

        project_urls = metadata.get_all("Project-URL", [])
        homepage = metadata.get("Home-page", "")
        if not homepage:
            # It's common that there is a "homepage" Project-URL, but Home-page
            # remains unset (especially as PEP 621 doesn't surface the field).
            #
            # This logic was taken from PyPI's codebase.
            for url in project_urls:
                url_label, url = url.split(",", maxsplit=1)
                normalized_label = (
                    url_label.casefold().replace("-", "").replace("_", "").strip()
                )
                if normalized_label == "homepage":
                    homepage = url.strip()
                    break

        yield _PackageInfo(
            name=dist.raw_name,
            version=dist.raw_version,
            location=dist.location or "",
            editable_project_location=dist.editable_project_location,
            requires=requires,
            required_by=required_by,
            installer=dist.installer,
            metadata_version=dist.metadata_version or "",
            classifiers=metadata.get_all("Classifier", []),
            summary=metadata.get("Summary", ""),
            homepage=homepage,
            project_urls=project_urls,
            author=metadata.get("Author", ""),
            author_email=metadata.get("Author-email", ""),
            license=metadata.get("License", ""),
            license_expression=metadata.get("License-Expression", ""),
            entry_points=entry_points,
            files=files,
        )


def print_results(
    distributions: Iterable[_PackageInfo],
    list_files: bool,
    verbose: bool,
) -> bool:
    """
    Print the information from installed distributions found.
    """
    results_printed = False
    for i, dist in enumerate(distributions):
        results_printed = True
        if i > 0:
            write_output("---")

        metadata_version_tuple = tuple(map(int, dist.metadata_version.split(".")))

        write_output("Name: %s", dist.name)
        write_output("Version: %s", dist.version)
        write_output("Summary: %s", dist.summary)
        write_output("Home-page: %s", dist.homepage)
        write_output("Author: %s", dist.author)
        write_output("Author-email: %s", dist.author_email)
        if metadata_version_tuple >= (2, 4) and dist.license_expression:
            write_output("License-Expression: %s", dist.license_expression)
        else:
            write_output("License: %s", dist.license)
        write_output("Location: %s", dist.location)
        if dist.editable_project_location is not None:
            write_output(
                "Editable project location: %s", dist.editable_project_location
            )
        write_output("Requires: %s", ", ".join(dist.requires))
        write_output("Required-by: %s", ", ".join(dist.required_by))

        if verbose:
            write_output("Metadata-Version: %s", dist.metadata_version)
            write_output("Installer: %s", dist.installer)
            write_output("Classifiers:")
            for classifier in dist.classifiers:
                write_output("  %s", classifier)
            write_output("Entry-points:")
            for entry in dist.entry_points:
                write_output("  %s", entry.strip())
            write_output("Project-URLs:")
            for project_url in dist.project_urls:
                write_output("  %s", project_url)
        if list_files:
            write_output("Files:")
            if dist.files is None:
                write_output("Cannot locate RECORD or installed-files.txt")
            else:
                for line in dist.files:
                    write_output("  %s", line.strip())
    return results_printed

# === NexusCore/openenv\Lib\site-packages\pip\_internal\models\direct_url.py ===
""" PEP 610 """

import json
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Iterable, Optional, Type, TypeVar, Union

__all__ = [
    "DirectUrl",
    "DirectUrlValidationError",
    "DirInfo",
    "ArchiveInfo",
    "VcsInfo",
]

T = TypeVar("T")

DIRECT_URL_METADATA_NAME = "direct_url.json"
ENV_VAR_RE = re.compile(r"^\$\{[A-Za-z0-9-_]+\}(:\$\{[A-Za-z0-9-_]+\})?$")


class DirectUrlValidationError(Exception):
    pass


def _get(
    d: Dict[str, Any], expected_type: Type[T], key: str, default: Optional[T] = None
) -> Optional[T]:
    """Get value from dictionary and verify expected type."""
    if key not in d:
        return default
    value = d[key]
    if not isinstance(value, expected_type):
        raise DirectUrlValidationError(
            f"{value!r} has unexpected type for {key} (expected {expected_type})"
        )
    return value


def _get_required(
    d: Dict[str, Any], expected_type: Type[T], key: str, default: Optional[T] = None
) -> T:
    value = _get(d, expected_type, key, default)
    if value is None:
        raise DirectUrlValidationError(f"{key} must have a value")
    return value


def _exactly_one_of(infos: Iterable[Optional["InfoType"]]) -> "InfoType":
    infos = [info for info in infos if info is not None]
    if not infos:
        raise DirectUrlValidationError(
            "missing one of archive_info, dir_info, vcs_info"
        )
    if len(infos) > 1:
        raise DirectUrlValidationError(
            "more than one of archive_info, dir_info, vcs_info"
        )
    assert infos[0] is not None
    return infos[0]


def _filter_none(**kwargs: Any) -> Dict[str, Any]:
    """Make dict excluding None values."""
    return {k: v for k, v in kwargs.items() if v is not None}


@dataclass
class VcsInfo:
    name: ClassVar = "vcs_info"

    vcs: str
    commit_id: str
    requested_revision: Optional[str] = None

    @classmethod
    def _from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["VcsInfo"]:
        if d is None:
            return None
        return cls(
            vcs=_get_required(d, str, "vcs"),
            commit_id=_get_required(d, str, "commit_id"),
            requested_revision=_get(d, str, "requested_revision"),
        )

    def _to_dict(self) -> Dict[str, Any]:
        return _filter_none(
            vcs=self.vcs,
            requested_revision=self.requested_revision,
            commit_id=self.commit_id,
        )


class ArchiveInfo:
    name = "archive_info"

    def __init__(
        self,
        hash: Optional[str] = None,
        hashes: Optional[Dict[str, str]] = None,
    ) -> None:
        # set hashes before hash, since the hash setter will further populate hashes
        self.hashes = hashes
        self.hash = hash

    @property
    def hash(self) -> Optional[str]:
        return self._hash

    @hash.setter
    def hash(self, value: Optional[str]) -> None:
        if value is not None:
            # Auto-populate the hashes key to upgrade to the new format automatically.
            # We don't back-populate the legacy hash key from hashes.
            try:
                hash_name, hash_value = value.split("=", 1)
            except ValueError:
                raise DirectUrlValidationError(
                    f"invalid archive_info.hash format: {value!r}"
                )
            if self.hashes is None:
                self.hashes = {hash_name: hash_value}
            elif hash_name not in self.hashes:
                self.hashes = self.hashes.copy()
                self.hashes[hash_name] = hash_value
        self._hash = value

    @classmethod
    def _from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["ArchiveInfo"]:
        if d is None:
            return None
        return cls(hash=_get(d, str, "hash"), hashes=_get(d, dict, "hashes"))

    def _to_dict(self) -> Dict[str, Any]:
        return _filter_none(hash=self.hash, hashes=self.hashes)


@dataclass
class DirInfo:
    name: ClassVar = "dir_info"

    editable: bool = False

    @classmethod
    def _from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["DirInfo"]:
        if d is None:
            return None
        return cls(editable=_get_required(d, bool, "editable", default=False))

    def _to_dict(self) -> Dict[str, Any]:
        return _filter_none(editable=self.editable or None)


InfoType = Union[ArchiveInfo, DirInfo, VcsInfo]


@dataclass
class DirectUrl:
    url: str
    info: InfoType
    subdirectory: Optional[str] = None

    def _remove_auth_from_netloc(self, netloc: str) -> str:
        if "@" not in netloc:
            return netloc
        user_pass, netloc_no_user_pass = netloc.split("@", 1)
        if (
            isinstance(self.info, VcsInfo)
            and self.info.vcs == "git"
            and user_pass == "git"
        ):
            return netloc
        if ENV_VAR_RE.match(user_pass):
            return netloc
        return netloc_no_user_pass

    @property
    def redacted_url(self) -> str:
        """url with user:password part removed unless it is formed with
        environment variables as specified in PEP 610, or it is ``git``
        in the case of a git URL.
        """
        purl = urllib.parse.urlsplit(self.url)
        netloc = self._remove_auth_from_netloc(purl.netloc)
        surl = urllib.parse.urlunsplit(
            (purl.scheme, netloc, purl.path, purl.query, purl.fragment)
        )
        return surl

    def validate(self) -> None:
        self.from_dict(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DirectUrl":
        return DirectUrl(
            url=_get_required(d, str, "url"),
            subdirectory=_get(d, str, "subdirectory"),
            info=_exactly_one_of(
                [
                    ArchiveInfo._from_dict(_get(d, dict, "archive_info")),
                    DirInfo._from_dict(_get(d, dict, "dir_info")),
                    VcsInfo._from_dict(_get(d, dict, "vcs_info")),
                ]
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        res = _filter_none(
            url=self.redacted_url,
            subdirectory=self.subdirectory,
        )
        res[self.info.name] = self.info._to_dict()
        return res

    @classmethod
    def from_json(cls, s: str) -> "DirectUrl":
        return cls.from_dict(json.loads(s))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    def is_local_editable(self) -> bool:
        return isinstance(self.info, DirInfo) and self.info.editable

# === NexusCore/openenv\Lib\site-packages\pydantic\deprecated\copy_internals.py ===
from __future__ import annotations as _annotations

import typing
from copy import deepcopy
from enum import Enum
from typing import Any

import typing_extensions

from .._internal import (
    _model_construction,
    _typing_extra,
    _utils,
)

if typing.TYPE_CHECKING:
    from .. import BaseModel
    from .._internal._utils import AbstractSetIntStr, MappingIntStrAny

    AnyClassMethod = classmethod[Any, Any, Any]
    TupleGenerator = typing.Generator[tuple[str, Any], None, None]
    Model = typing.TypeVar('Model', bound='BaseModel')
    # should be `set[int] | set[str] | dict[int, IncEx] | dict[str, IncEx] | None`, but mypy can't cope
    IncEx: typing_extensions.TypeAlias = 'set[int] | set[str] | dict[int, Any] | dict[str, Any] | None'

_object_setattr = _model_construction.object_setattr


def _iter(
    self: BaseModel,
    to_dict: bool = False,
    by_alias: bool = False,
    include: AbstractSetIntStr | MappingIntStrAny | None = None,
    exclude: AbstractSetIntStr | MappingIntStrAny | None = None,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
) -> TupleGenerator:
    # Merge field set excludes with explicit exclude parameter with explicit overriding field set options.
    # The extra "is not None" guards are not logically necessary but optimizes performance for the simple case.
    if exclude is not None:
        exclude = _utils.ValueItems.merge(
            {k: v.exclude for k, v in self.__pydantic_fields__.items() if v.exclude is not None}, exclude
        )

    if include is not None:
        include = _utils.ValueItems.merge({k: True for k in self.__pydantic_fields__}, include, intersect=True)

    allowed_keys = _calculate_keys(self, include=include, exclude=exclude, exclude_unset=exclude_unset)  # type: ignore
    if allowed_keys is None and not (to_dict or by_alias or exclude_unset or exclude_defaults or exclude_none):
        # huge boost for plain _iter()
        yield from self.__dict__.items()
        if self.__pydantic_extra__:
            yield from self.__pydantic_extra__.items()
        return

    value_exclude = _utils.ValueItems(self, exclude) if exclude is not None else None
    value_include = _utils.ValueItems(self, include) if include is not None else None

    if self.__pydantic_extra__ is None:
        items = self.__dict__.items()
    else:
        items = list(self.__dict__.items()) + list(self.__pydantic_extra__.items())

    for field_key, v in items:
        if (allowed_keys is not None and field_key not in allowed_keys) or (exclude_none and v is None):
            continue

        if exclude_defaults:
            try:
                field = self.__pydantic_fields__[field_key]
            except KeyError:
                pass
            else:
                if not field.is_required() and field.default == v:
                    continue

        if by_alias and field_key in self.__pydantic_fields__:
            dict_key = self.__pydantic_fields__[field_key].alias or field_key
        else:
            dict_key = field_key

        if to_dict or value_include or value_exclude:
            v = _get_value(
                type(self),
                v,
                to_dict=to_dict,
                by_alias=by_alias,
                include=value_include and value_include.for_element(field_key),
                exclude=value_exclude and value_exclude.for_element(field_key),
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )
        yield dict_key, v


def _copy_and_set_values(
    self: Model,
    values: dict[str, Any],
    fields_set: set[str],
    extra: dict[str, Any] | None = None,
    private: dict[str, Any] | None = None,
    *,
    deep: bool,  # UP006
) -> Model:
    if deep:
        # chances of having empty dict here are quite low for using smart_deepcopy
        values = deepcopy(values)
        extra = deepcopy(extra)
        private = deepcopy(private)

    cls = self.__class__
    m = cls.__new__(cls)
    _object_setattr(m, '__dict__', values)
    _object_setattr(m, '__pydantic_extra__', extra)
    _object_setattr(m, '__pydantic_fields_set__', fields_set)
    _object_setattr(m, '__pydantic_private__', private)

    return m


@typing.no_type_check
def _get_value(
    cls: type[BaseModel],
    v: Any,
    to_dict: bool,
    by_alias: bool,
    include: AbstractSetIntStr | MappingIntStrAny | None,
    exclude: AbstractSetIntStr | MappingIntStrAny | None,
    exclude_unset: bool,
    exclude_defaults: bool,
    exclude_none: bool,
) -> Any:
    from .. import BaseModel

    if isinstance(v, BaseModel):
        if to_dict:
            return v.model_dump(
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                include=include,  # type: ignore
                exclude=exclude,  # type: ignore
                exclude_none=exclude_none,
            )
        else:
            return v.copy(include=include, exclude=exclude)

    value_exclude = _utils.ValueItems(v, exclude) if exclude else None
    value_include = _utils.ValueItems(v, include) if include else None

    if isinstance(v, dict):
        return {
            k_: _get_value(
                cls,
                v_,
                to_dict=to_dict,
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                include=value_include and value_include.for_element(k_),
                exclude=value_exclude and value_exclude.for_element(k_),
                exclude_none=exclude_none,
            )
            for k_, v_ in v.items()
            if (not value_exclude or not value_exclude.is_excluded(k_))
            and (not value_include or value_include.is_included(k_))
        }

    elif _utils.sequence_like(v):
        seq_args = (
            _get_value(
                cls,
                v_,
                to_dict=to_dict,
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                include=value_include and value_include.for_element(i),
                exclude=value_exclude and value_exclude.for_element(i),
                exclude_none=exclude_none,
            )
            for i, v_ in enumerate(v)
            if (not value_exclude or not value_exclude.is_excluded(i))
            and (not value_include or value_include.is_included(i))
        )

        return v.__class__(*seq_args) if _typing_extra.is_namedtuple(v.__class__) else v.__class__(seq_args)

    elif isinstance(v, Enum) and getattr(cls.model_config, 'use_enum_values', False):
        return v.value

    else:
        return v


def _calculate_keys(
    self: BaseModel,
    include: MappingIntStrAny | None,
    exclude: MappingIntStrAny | None,
    exclude_unset: bool,
    update: dict[str, Any] | None = None,  # noqa UP006
) -> typing.AbstractSet[str] | None:
    if include is None and exclude is None and exclude_unset is False:
        return None

    keys: typing.AbstractSet[str]
    if exclude_unset:
        keys = self.__pydantic_fields_set__.copy()
    else:
        keys = set(self.__dict__.keys())
        keys = keys | (self.__pydantic_extra__ or {}).keys()

    if include is not None:
        keys &= include.keys()

    if update:
        keys -= update.keys()

    if exclude:
        keys -= {k for k, v in exclude.items() if _utils.ValueItems.is_true(v)}

    return keys

# === NexusCore/openenv\Lib\site-packages\smmap\test\test_mman.py ===
from .lib import TestBase, FileCreator

from smmap.mman import (
    WindowCursor,
    SlidingWindowMapManager,
    StaticWindowMapManager
)
from smmap.util import align_to_mmap

from random import randint
from time import time
import os
import sys
from copy import copy


class TestMMan(TestBase):

    def test_cursor(self):
        with FileCreator(self.k_window_test_size, "cursor_test") as fc:
            man = SlidingWindowMapManager()
            ci = WindowCursor(man)  # invalid cursor
            assert not ci.is_valid()
            assert not ci.is_associated()
            assert ci.size() == 0       # this is cached, so we can query it in invalid state

            cv = man.make_cursor(fc.path)
            assert not cv.is_valid()    # no region mapped yet
            assert cv.is_associated()  # but it know where to map it from
            assert cv.file_size() == fc.size
            assert cv.path() == fc.path

        # copy module
        cio = copy(cv)
        assert not cio.is_valid() and cio.is_associated()

        # assign method
        assert not ci.is_associated()
        ci.assign(cv)
        assert not ci.is_valid() and ci.is_associated()

        # unuse non-existing region is fine
        cv.unuse_region()
        cv.unuse_region()

        # destruction is fine (even multiple times)
        cv._destroy()
        WindowCursor(man)._destroy()

    def test_memory_manager(self):
        slide_man = SlidingWindowMapManager()
        static_man = StaticWindowMapManager()

        for man in (static_man, slide_man):
            assert man.num_file_handles() == 0
            assert man.num_open_files() == 0
            winsize_cmp_val = 0
            if isinstance(man, StaticWindowMapManager):
                winsize_cmp_val = -1
            # END handle window size
            assert man.window_size() > winsize_cmp_val
            assert man.mapped_memory_size() == 0
            assert man.max_mapped_memory_size() > 0

            # collection doesn't raise in 'any' mode
            man._collect_lru_region(0)
            # doesn't raise if we are within the limit
            man._collect_lru_region(10)

            # doesn't fail if we over-allocate
            assert man._collect_lru_region(sys.maxsize) == 0

            # use a region, verify most basic functionality
            with FileCreator(self.k_window_test_size, "manager_test") as fc:
                fd = os.open(fc.path, os.O_RDONLY)
                try:
                    for item in (fc.path, fd):
                        c = man.make_cursor(item)
                        assert c.path_or_fd() is item
                        assert c.use_region(10, 10).is_valid()
                        assert c.ofs_begin() == 10
                        assert c.size() == 10
                        with open(fc.path, 'rb') as fp:
                            assert c.buffer()[:] == fp.read(20)[10:]

                    if isinstance(item, int):
                        self.assertRaises(ValueError, c.path)
                    else:
                        self.assertRaises(ValueError, c.fd)
                    # END handle value error
                # END for each input
                finally:
                    os.close(fd)
        # END for each manasger type

    def test_memman_operation(self):
        # test more access, force it to actually unmap regions
        with FileCreator(self.k_window_test_size, "manager_operation_test") as fc:
            with open(fc.path, 'rb') as fp:
                data = fp.read()
            fd = os.open(fc.path, os.O_RDONLY)
            try:
                max_num_handles = 15
                # small_size =
                for mtype, args in ((StaticWindowMapManager, (0, fc.size // 3, max_num_handles)),
                                    (SlidingWindowMapManager, (fc.size // 100, fc.size // 3, max_num_handles)),):
                    for item in (fc.path, fd):
                        assert len(data) == fc.size

                        # small windows, a reasonable max memory. Not too many regions at once
                        man = mtype(window_size=args[0], max_memory_size=args[1], max_open_handles=args[2])
                        c = man.make_cursor(item)

                        # still empty (more about that is tested in test_memory_manager()
                        assert man.num_open_files() == 0
                        assert man.mapped_memory_size() == 0

                        base_offset = 5000
                        # window size is 0 for static managers, hence size will be 0. We take that into consideration
                        size = man.window_size() // 2
                        assert c.use_region(base_offset, size).is_valid()
                        rr = c.region()
                        assert rr.client_count() == 2  # the manager and the cursor and us

                        assert man.num_open_files() == 1
                        assert man.num_file_handles() == 1
                        assert man.mapped_memory_size() == rr.size()

                        # assert c.size() == size        # the cursor may overallocate in its static version
                        assert c.ofs_begin() == base_offset
                        assert rr.ofs_begin() == 0        # it was aligned and expanded
                        if man.window_size():
                            # but isn't larger than the max window (aligned)
                            assert rr.size() == align_to_mmap(man.window_size(), True)
                        else:
                            assert rr.size() == fc.size
                        # END ignore static managers which dont use windows and are aligned to file boundaries

                        assert c.buffer()[:] == data[base_offset:base_offset + (size or c.size())]

                        # obtain second window, which spans the first part of the file - it is a still the same window
                        nsize = (size or fc.size) - 10
                        assert c.use_region(0, nsize).is_valid()
                        assert c.region() == rr
                        assert man.num_file_handles() == 1
                        assert c.size() == nsize
                        assert c.ofs_begin() == 0
                        assert c.buffer()[:] == data[:nsize]

                        # map some part at the end, our requested size cannot be kept
                        overshoot = 4000
                        base_offset = fc.size - (size or c.size()) + overshoot
                        assert c.use_region(base_offset, size).is_valid()
                        if man.window_size():
                            assert man.num_file_handles() == 2
                            assert c.size() < size
                            assert c.region() is not rr  # old region is still available, but has not cursor ref anymore
                            assert rr.client_count() == 1  # only held by manager
                        else:
                            assert c.size() < fc.size
                        # END ignore static managers which only have one handle per file
                        rr = c.region()
                        assert rr.client_count() == 2  # manager + cursor
                        assert rr.ofs_begin() < c.ofs_begin()  # it should have extended itself to the left
                        assert rr.ofs_end() <= fc.size  # it cannot be larger than the file
                        assert c.buffer()[:] == data[base_offset:base_offset + (size or c.size())]

                        # unising a region makes the cursor invalid
                        c.unuse_region()
                        assert not c.is_valid()
                        if man.window_size():
                            # but doesn't change anything regarding the handle count - we cache it and only
                            # remove mapped regions if we have to
                            assert man.num_file_handles() == 2
                        # END ignore this for static managers

                        # iterate through the windows, verify data contents
                        # this will trigger map collection after a while
                        max_random_accesses = 5000
                        num_random_accesses = max_random_accesses
                        memory_read = 0
                        st = time()

                        # cache everything to get some more performance
                        includes_ofs = c.includes_ofs
                        max_mapped_memory_size = man.max_mapped_memory_size()
                        max_file_handles = man.max_file_handles()
                        mapped_memory_size = man.mapped_memory_size
                        num_file_handles = man.num_file_handles
                        while num_random_accesses:
                            num_random_accesses -= 1
                            base_offset = randint(0, fc.size - 1)

                            # precondition
                            if man.window_size():
                                assert max_mapped_memory_size >= mapped_memory_size()
                            # END statistics will overshoot, which is fine
                            assert max_file_handles >= num_file_handles()
                            assert c.use_region(base_offset, (size or c.size())).is_valid()
                            csize = c.size()
                            assert c.buffer()[:] == data[base_offset:base_offset + csize]
                            memory_read += csize

                            assert includes_ofs(base_offset)
                            assert includes_ofs(base_offset + csize - 1)
                            assert not includes_ofs(base_offset + csize)
                        # END while we should do an access
                        elapsed = max(time() - st, 0.001)  # prevent zero division errors on windows
                        mb = float(1000 * 1000)
                        print("%s: Read %i mb of memory with %i random on cursor initialized with %s accesses in %fs (%f mb/s)\n"
                              % (mtype, memory_read / mb, max_random_accesses, type(item), elapsed, (memory_read / mb) / elapsed),
                              file=sys.stderr)

                        # an offset as large as the size doesn't work !
                        assert not c.use_region(fc.size, size).is_valid()

                        # collection - it should be able to collect all
                        assert man.num_file_handles()
                        assert man.collect()
                        assert man.num_file_handles() == 0
                    # END for each item
                # END for each manager type
            finally:
                os.close(fd)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\progress_bar.py ===
import math
from functools import lru_cache
from time import monotonic
from typing import Iterable, List, Optional

from .color import Color, blend_rgb
from .color_triplet import ColorTriplet
from .console import Console, ConsoleOptions, RenderResult
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import Style, StyleType

# Number of characters before 'pulse' animation repeats
PULSE_SIZE = 20


class ProgressBar(JupyterMixin):
    """Renders a (progress) bar. Used by rich.progress.

    Args:
        total (float, optional): Number of steps in the bar. Defaults to 100. Set to None to render a pulsing animation.
        completed (float, optional): Number of steps completed. Defaults to 0.
        width (int, optional): Width of the bar, or ``None`` for maximum width. Defaults to None.
        pulse (bool, optional): Enable pulse effect. Defaults to False. Will pulse if a None total was passed.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
        animation_time (Optional[float], optional): Time in seconds to use for animation, or None to use system time.
    """

    def __init__(
        self,
        total: Optional[float] = 100.0,
        completed: float = 0,
        width: Optional[int] = None,
        pulse: bool = False,
        style: StyleType = "bar.back",
        complete_style: StyleType = "bar.complete",
        finished_style: StyleType = "bar.finished",
        pulse_style: StyleType = "bar.pulse",
        animation_time: Optional[float] = None,
    ):
        self.total = total
        self.completed = completed
        self.width = width
        self.pulse = pulse
        self.style = style
        self.complete_style = complete_style
        self.finished_style = finished_style
        self.pulse_style = pulse_style
        self.animation_time = animation_time

        self._pulse_segments: Optional[List[Segment]] = None

    def __repr__(self) -> str:
        return f"<Bar {self.completed!r} of {self.total!r}>"

    @property
    def percentage_completed(self) -> Optional[float]:
        """Calculate percentage complete."""
        if self.total is None:
            return None
        completed = (self.completed / self.total) * 100.0
        completed = min(100, max(0.0, completed))
        return completed

    @lru_cache(maxsize=16)
    def _get_pulse_segments(
        self,
        fore_style: Style,
        back_style: Style,
        color_system: str,
        no_color: bool,
        ascii: bool = False,
    ) -> List[Segment]:
        """Get a list of segments to render a pulse animation.

        Returns:
            List[Segment]: A list of segments, one segment per character.
        """
        bar = "-" if ascii else "━"
        segments: List[Segment] = []
        if color_system not in ("standard", "eight_bit", "truecolor") or no_color:
            segments += [Segment(bar, fore_style)] * (PULSE_SIZE // 2)
            segments += [Segment(" " if no_color else bar, back_style)] * (
                PULSE_SIZE - (PULSE_SIZE // 2)
            )
            return segments

        append = segments.append
        fore_color = (
            fore_style.color.get_truecolor()
            if fore_style.color
            else ColorTriplet(255, 0, 255)
        )
        back_color = (
            back_style.color.get_truecolor()
            if back_style.color
            else ColorTriplet(0, 0, 0)
        )
        cos = math.cos
        pi = math.pi
        _Segment = Segment
        _Style = Style
        from_triplet = Color.from_triplet

        for index in range(PULSE_SIZE):
            position = index / PULSE_SIZE
            fade = 0.5 + cos(position * pi * 2) / 2.0
            color = blend_rgb(fore_color, back_color, cross_fade=fade)
            append(_Segment(bar, _Style(color=from_triplet(color))))
        return segments

    def update(self, completed: float, total: Optional[float] = None) -> None:
        """Update progress with new values.

        Args:
            completed (float): Number of steps completed.
            total (float, optional): Total number of steps, or ``None`` to not change. Defaults to None.
        """
        self.completed = completed
        self.total = total if total is not None else self.total

    def _render_pulse(
        self, console: Console, width: int, ascii: bool = False
    ) -> Iterable[Segment]:
        """Renders the pulse animation.

        Args:
            console (Console): Console instance.
            width (int): Width in characters of pulse animation.

        Returns:
            RenderResult: [description]

        Yields:
            Iterator[Segment]: Segments to render pulse
        """
        fore_style = console.get_style(self.pulse_style, default="white")
        back_style = console.get_style(self.style, default="black")

        pulse_segments = self._get_pulse_segments(
            fore_style, back_style, console.color_system, console.no_color, ascii=ascii
        )
        segment_count = len(pulse_segments)
        current_time = (
            monotonic() if self.animation_time is None else self.animation_time
        )
        segments = pulse_segments * (int(width / segment_count) + 2)
        offset = int(-current_time * 15) % segment_count
        segments = segments[offset : offset + width]
        yield from segments

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        width = min(self.width or options.max_width, options.max_width)
        ascii = options.legacy_windows or options.ascii_only
        should_pulse = self.pulse or self.total is None
        if should_pulse:
            yield from self._render_pulse(console, width, ascii=ascii)
            return

        completed: Optional[float] = (
            min(self.total, max(0, self.completed)) if self.total is not None else None
        )

        bar = "-" if ascii else "━"
        half_bar_right = " " if ascii else "╸"
        half_bar_left = " " if ascii else "╺"
        complete_halves = (
            int(width * 2 * completed / self.total)
            if self.total and completed is not None
            else width * 2
        )
        bar_count = complete_halves // 2
        half_bar_count = complete_halves % 2
        style = console.get_style(self.style)
        is_finished = self.total is None or self.completed >= self.total
        complete_style = console.get_style(
            self.finished_style if is_finished else self.complete_style
        )
        _Segment = Segment
        if bar_count:
            yield _Segment(bar * bar_count, complete_style)
        if half_bar_count:
            yield _Segment(half_bar_right * half_bar_count, complete_style)

        if not console.no_color:
            remaining_bars = width - bar_count - half_bar_count
            if remaining_bars and console.color_system is not None:
                if not half_bar_count and bar_count:
                    yield _Segment(half_bar_left, style)
                    remaining_bars -= 1
                if remaining_bars:
                    yield _Segment(bar * remaining_bars, style)

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        return (
            Measurement(self.width, self.width)
            if self.width is not None
            else Measurement(4, options.max_width)
        )


if __name__ == "__main__":  # pragma: no cover
    console = Console()
    bar = ProgressBar(width=50, total=100)

    import time

    console.show_cursor(False)
    for n in range(0, 101, 1):
        bar.update(n)
        console.print(bar)
        console.file.write("\r")
        time.sleep(0.05)
    console.show_cursor(True)
    console.print()

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc6960.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# Online Certificate Status Protocol (OCSP)
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc6960.txt
#

from pyasn1.type import univ, char, namedtype, namedval, tag, constraint, useful

from pyasn1_modules import rfc2560
from pyasn1_modules import rfc5280

MAX = float('inf')


# Imports from RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier
AuthorityInfoAccessSyntax = rfc5280.AuthorityInfoAccessSyntax
Certificate = rfc5280.Certificate
CertificateSerialNumber = rfc5280.CertificateSerialNumber
CRLReason = rfc5280.CRLReason
Extensions = rfc5280.Extensions
GeneralName = rfc5280.GeneralName
Name = rfc5280.Name

id_kp = rfc5280.id_kp

id_ad_ocsp = rfc5280.id_ad_ocsp


# Imports from the original OCSP module in RFC 2560

AcceptableResponses = rfc2560.AcceptableResponses
ArchiveCutoff = rfc2560.ArchiveCutoff
CertStatus = rfc2560.CertStatus
KeyHash = rfc2560.KeyHash
OCSPResponse = rfc2560.OCSPResponse
OCSPResponseStatus = rfc2560.OCSPResponseStatus
ResponseBytes = rfc2560.ResponseBytes
RevokedInfo = rfc2560.RevokedInfo
UnknownInfo = rfc2560.UnknownInfo
Version = rfc2560.Version

id_kp_OCSPSigning = rfc2560.id_kp_OCSPSigning

id_pkix_ocsp = rfc2560.id_pkix_ocsp
id_pkix_ocsp_archive_cutoff = rfc2560.id_pkix_ocsp_archive_cutoff
id_pkix_ocsp_basic = rfc2560.id_pkix_ocsp_basic
id_pkix_ocsp_crl = rfc2560.id_pkix_ocsp_crl
id_pkix_ocsp_nocheck = rfc2560.id_pkix_ocsp_nocheck
id_pkix_ocsp_nonce = rfc2560.id_pkix_ocsp_nonce
id_pkix_ocsp_response = rfc2560.id_pkix_ocsp_response
id_pkix_ocsp_service_locator = rfc2560.id_pkix_ocsp_service_locator


# Additional object identifiers

id_pkix_ocsp_pref_sig_algs = id_pkix_ocsp + (8, )
id_pkix_ocsp_extended_revoke = id_pkix_ocsp + (9, )


# Updated structures (mostly to improve openTypes support)

class CertID(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('hashAlgorithm', AlgorithmIdentifier()),
        namedtype.NamedType('issuerNameHash', univ.OctetString()),
        namedtype.NamedType('issuerKeyHash', univ.OctetString()),
        namedtype.NamedType('serialNumber', CertificateSerialNumber())
    )


class SingleResponse(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('certID', CertID()),
        namedtype.NamedType('certStatus', CertStatus()),
        namedtype.NamedType('thisUpdate', useful.GeneralizedTime()),
        namedtype.OptionalNamedType('nextUpdate', useful.GeneralizedTime().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('singleExtensions', Extensions().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class ResponderID(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('byName', Name().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.NamedType('byKey', KeyHash().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
    )


class ResponseData(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.DefaultedNamedType('version', Version('v1').subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('responderID', ResponderID()),
        namedtype.NamedType('producedAt', useful.GeneralizedTime()),
        namedtype.NamedType('responses', univ.SequenceOf(
            componentType=SingleResponse())),
        namedtype.OptionalNamedType('responseExtensions', Extensions().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class BasicOCSPResponse(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('tbsResponseData', ResponseData()),
        namedtype.NamedType('signatureAlgorithm', AlgorithmIdentifier()),
        namedtype.NamedType('signature', univ.BitString()),
        namedtype.OptionalNamedType('certs', univ.SequenceOf(
            componentType=Certificate()).subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0)))
    )


class Request(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('reqCert', CertID()),
        namedtype.OptionalNamedType('singleRequestExtensions', Extensions().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
    )


class Signature(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('signatureAlgorithm', AlgorithmIdentifier()),
        namedtype.NamedType('signature', univ.BitString()),
        namedtype.OptionalNamedType('certs', univ.SequenceOf(
            componentType=Certificate()).subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0)))
    )


class TBSRequest(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.DefaultedNamedType('version', Version('v1').subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('requestorName', GeneralName().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.NamedType('requestList', univ.SequenceOf(
            componentType=Request())),
        namedtype.OptionalNamedType('requestExtensions', Extensions().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
    )


class OCSPRequest(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('tbsRequest', TBSRequest()),
        namedtype.OptionalNamedType('optionalSignature', Signature().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
    )


# Previously omitted structure

class ServiceLocator(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('issuer', Name()),
        namedtype.NamedType('locator', AuthorityInfoAccessSyntax())
    )


# Additional structures

class CrlID(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('crlUrl', char.IA5String().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('crlNum', univ.Integer().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('crlTime', useful.GeneralizedTime().subtype(
            explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
    )


class PreferredSignatureAlgorithm(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('sigIdentifier', AlgorithmIdentifier()),
        namedtype.OptionalNamedType('certIdentifier', AlgorithmIdentifier())
    )


class PreferredSignatureAlgorithms(univ.SequenceOf):
    componentType = PreferredSignatureAlgorithm()



# Response Type OID to Response Map

ocspResponseMap = {
    id_pkix_ocsp_basic: BasicOCSPResponse(),
}


# Map of Extension OIDs to Extensions added to the ones
# that are in rfc5280.py

_certificateExtensionsMapUpdate = {
    # Certificate Extension
    id_pkix_ocsp_nocheck: univ.Null(""),
    # OCSP Request Extensions
    id_pkix_ocsp_nonce: univ.OctetString(),
    id_pkix_ocsp_response: AcceptableResponses(),
    id_pkix_ocsp_service_locator: ServiceLocator(),
    id_pkix_ocsp_pref_sig_algs: PreferredSignatureAlgorithms(),
    # OCSP Response Extensions
    id_pkix_ocsp_crl: CrlID(),
    id_pkix_ocsp_archive_cutoff: ArchiveCutoff(),
    id_pkix_ocsp_extended_revoke: univ.Null(""),
}

rfc5280.certificateExtensionsMap.update(_certificateExtensionsMapUpdate)

# === NexusCore/openenv\Lib\site-packages\rich\progress_bar.py ===
import math
from functools import lru_cache
from time import monotonic
from typing import Iterable, List, Optional

from .color import Color, blend_rgb
from .color_triplet import ColorTriplet
from .console import Console, ConsoleOptions, RenderResult
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import Style, StyleType

# Number of characters before 'pulse' animation repeats
PULSE_SIZE = 20


class ProgressBar(JupyterMixin):
    """Renders a (progress) bar. Used by rich.progress.

    Args:
        total (float, optional): Number of steps in the bar. Defaults to 100. Set to None to render a pulsing animation.
        completed (float, optional): Number of steps completed. Defaults to 0.
        width (int, optional): Width of the bar, or ``None`` for maximum width. Defaults to None.
        pulse (bool, optional): Enable pulse effect. Defaults to False. Will pulse if a None total was passed.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
        animation_time (Optional[float], optional): Time in seconds to use for animation, or None to use system time.
    """

    def __init__(
        self,
        total: Optional[float] = 100.0,
        completed: float = 0,
        width: Optional[int] = None,
        pulse: bool = False,
        style: StyleType = "bar.back",
        complete_style: StyleType = "bar.complete",
        finished_style: StyleType = "bar.finished",
        pulse_style: StyleType = "bar.pulse",
        animation_time: Optional[float] = None,
    ):
        self.total = total
        self.completed = completed
        self.width = width
        self.pulse = pulse
        self.style = style
        self.complete_style = complete_style
        self.finished_style = finished_style
        self.pulse_style = pulse_style
        self.animation_time = animation_time

        self._pulse_segments: Optional[List[Segment]] = None

    def __repr__(self) -> str:
        return f"<Bar {self.completed!r} of {self.total!r}>"

    @property
    def percentage_completed(self) -> Optional[float]:
        """Calculate percentage complete."""
        if self.total is None:
            return None
        completed = (self.completed / self.total) * 100.0
        completed = min(100, max(0.0, completed))
        return completed

    @lru_cache(maxsize=16)
    def _get_pulse_segments(
        self,
        fore_style: Style,
        back_style: Style,
        color_system: str,
        no_color: bool,
        ascii: bool = False,
    ) -> List[Segment]:
        """Get a list of segments to render a pulse animation.

        Returns:
            List[Segment]: A list of segments, one segment per character.
        """
        bar = "-" if ascii else "━"
        segments: List[Segment] = []
        if color_system not in ("standard", "eight_bit", "truecolor") or no_color:
            segments += [Segment(bar, fore_style)] * (PULSE_SIZE // 2)
            segments += [Segment(" " if no_color else bar, back_style)] * (
                PULSE_SIZE - (PULSE_SIZE // 2)
            )
            return segments

        append = segments.append
        fore_color = (
            fore_style.color.get_truecolor()
            if fore_style.color
            else ColorTriplet(255, 0, 255)
        )
        back_color = (
            back_style.color.get_truecolor()
            if back_style.color
            else ColorTriplet(0, 0, 0)
        )
        cos = math.cos
        pi = math.pi
        _Segment = Segment
        _Style = Style
        from_triplet = Color.from_triplet

        for index in range(PULSE_SIZE):
            position = index / PULSE_SIZE
            fade = 0.5 + cos(position * pi * 2) / 2.0
            color = blend_rgb(fore_color, back_color, cross_fade=fade)
            append(_Segment(bar, _Style(color=from_triplet(color))))
        return segments

    def update(self, completed: float, total: Optional[float] = None) -> None:
        """Update progress with new values.

        Args:
            completed (float): Number of steps completed.
            total (float, optional): Total number of steps, or ``None`` to not change. Defaults to None.
        """
        self.completed = completed
        self.total = total if total is not None else self.total

    def _render_pulse(
        self, console: Console, width: int, ascii: bool = False
    ) -> Iterable[Segment]:
        """Renders the pulse animation.

        Args:
            console (Console): Console instance.
            width (int): Width in characters of pulse animation.

        Returns:
            RenderResult: [description]

        Yields:
            Iterator[Segment]: Segments to render pulse
        """
        fore_style = console.get_style(self.pulse_style, default="white")
        back_style = console.get_style(self.style, default="black")

        pulse_segments = self._get_pulse_segments(
            fore_style, back_style, console.color_system, console.no_color, ascii=ascii
        )
        segment_count = len(pulse_segments)
        current_time = (
            monotonic() if self.animation_time is None else self.animation_time
        )
        segments = pulse_segments * (int(width / segment_count) + 2)
        offset = int(-current_time * 15) % segment_count
        segments = segments[offset : offset + width]
        yield from segments

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        width = min(self.width or options.max_width, options.max_width)
        ascii = options.legacy_windows or options.ascii_only
        should_pulse = self.pulse or self.total is None
        if should_pulse:
            yield from self._render_pulse(console, width, ascii=ascii)
            return

        completed: Optional[float] = (
            min(self.total, max(0, self.completed)) if self.total is not None else None
        )

        bar = "-" if ascii else "━"
        half_bar_right = " " if ascii else "╸"
        half_bar_left = " " if ascii else "╺"
        complete_halves = (
            int(width * 2 * completed / self.total)
            if self.total and completed is not None
            else width * 2
        )
        bar_count = complete_halves // 2
        half_bar_count = complete_halves % 2
        style = console.get_style(self.style)
        is_finished = self.total is None or self.completed >= self.total
        complete_style = console.get_style(
            self.finished_style if is_finished else self.complete_style
        )
        _Segment = Segment
        if bar_count:
            yield _Segment(bar * bar_count, complete_style)
        if half_bar_count:
            yield _Segment(half_bar_right * half_bar_count, complete_style)

        if not console.no_color:
            remaining_bars = width - bar_count - half_bar_count
            if remaining_bars and console.color_system is not None:
                if not half_bar_count and bar_count:
                    yield _Segment(half_bar_left, style)
                    remaining_bars -= 1
                if remaining_bars:
                    yield _Segment(bar * remaining_bars, style)

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        return (
            Measurement(self.width, self.width)
            if self.width is not None
            else Measurement(4, options.max_width)
        )


if __name__ == "__main__":  # pragma: no cover
    console = Console()
    bar = ProgressBar(width=50, total=100)

    import time

    console.show_cursor(False)
    for n in range(0, 101, 1):
        bar.update(n)
        console.print(bar)
        console.file.write("\r")
        time.sleep(0.05)
    console.show_cursor(True)
    console.print()

# === NexusCore/openenv\Lib\site-packages\fontTools\colorLib\table_builder.py ===
"""
colorLib.table_builder: Generic helper for filling in BaseTable derivatives from tuples and maps and such.

"""

import collections
import enum
from fontTools.ttLib.tables.otBase import (
    BaseTable,
    FormatSwitchingBaseTable,
    UInt8FormatSwitchingBaseTable,
)
from fontTools.ttLib.tables.otConverters import (
    ComputedInt,
    SimpleValue,
    Struct,
    Short,
    UInt8,
    UShort,
    IntValue,
    FloatValue,
    OptionalValue,
)
from fontTools.misc.roundTools import otRound


class BuildCallback(enum.Enum):
    """Keyed on (BEFORE_BUILD, class[, Format if available]).
    Receives (dest, source).
    Should return (dest, source), which can be new objects.
    """

    BEFORE_BUILD = enum.auto()

    """Keyed on (AFTER_BUILD, class[, Format if available]).
    Receives (dest).
    Should return dest, which can be a new object.
    """
    AFTER_BUILD = enum.auto()

    """Keyed on (CREATE_DEFAULT, class[, Format if available]).
    Receives no arguments.
    Should return a new instance of class.
    """
    CREATE_DEFAULT = enum.auto()


def _assignable(convertersByName):
    return {k: v for k, v in convertersByName.items() if not isinstance(v, ComputedInt)}


def _isNonStrSequence(value):
    return isinstance(value, collections.abc.Sequence) and not isinstance(value, str)


def _split_format(cls, source):
    if _isNonStrSequence(source):
        assert len(source) > 0, f"{cls} needs at least format from {source}"
        fmt, remainder = source[0], source[1:]
    elif isinstance(source, collections.abc.Mapping):
        assert "Format" in source, f"{cls} needs at least Format from {source}"
        remainder = source.copy()
        fmt = remainder.pop("Format")
    else:
        raise ValueError(f"Not sure how to populate {cls} from {source}")

    assert isinstance(
        fmt, collections.abc.Hashable
    ), f"{cls} Format is not hashable: {fmt!r}"
    assert fmt in cls.convertersByName, f"{cls} invalid Format: {fmt!r}"

    return fmt, remainder


class TableBuilder:
    """
    Helps to populate things derived from BaseTable from maps, tuples, etc.

    A table of lifecycle callbacks may be provided to add logic beyond what is possible
    based on otData info for the target class. See BuildCallbacks.
    """

    def __init__(self, callbackTable=None):
        if callbackTable is None:
            callbackTable = {}
        self._callbackTable = callbackTable

    def _convert(self, dest, field, converter, value):
        enumClass = getattr(converter, "enumClass", None)

        if enumClass:
            if isinstance(value, enumClass):
                pass
            elif isinstance(value, str):
                try:
                    value = getattr(enumClass, value.upper())
                except AttributeError:
                    raise ValueError(f"{value} is not a valid {enumClass}")
            else:
                value = enumClass(value)

        elif isinstance(converter, IntValue):
            value = otRound(value)
        elif isinstance(converter, FloatValue):
            value = float(value)

        elif isinstance(converter, Struct):
            if converter.repeat:
                if _isNonStrSequence(value):
                    value = [self.build(converter.tableClass, v) for v in value]
                else:
                    value = [self.build(converter.tableClass, value)]
                setattr(dest, converter.repeat, len(value))
            else:
                value = self.build(converter.tableClass, value)
        elif callable(converter):
            value = converter(value)

        setattr(dest, field, value)

    def build(self, cls, source):
        assert issubclass(cls, BaseTable)

        if isinstance(source, cls):
            return source

        callbackKey = (cls,)
        fmt = None
        if issubclass(cls, FormatSwitchingBaseTable):
            fmt, source = _split_format(cls, source)
            callbackKey = (cls, fmt)

        dest = self._callbackTable.get(
            (BuildCallback.CREATE_DEFAULT,) + callbackKey, lambda: cls()
        )()
        assert isinstance(dest, cls)

        convByName = _assignable(cls.convertersByName)
        skippedFields = set()

        # For format switchers we need to resolve converters based on format
        if issubclass(cls, FormatSwitchingBaseTable):
            dest.Format = fmt
            convByName = _assignable(convByName[dest.Format])
            skippedFields.add("Format")

        # Convert sequence => mapping so before thunk only has to handle one format
        if _isNonStrSequence(source):
            # Sequence (typically list or tuple) assumed to match fields in declaration order
            assert len(source) <= len(
                convByName
            ), f"Sequence of {len(source)} too long for {cls}; expected <= {len(convByName)} values"
            source = dict(zip(convByName.keys(), source))

        dest, source = self._callbackTable.get(
            (BuildCallback.BEFORE_BUILD,) + callbackKey, lambda d, s: (d, s)
        )(dest, source)

        if isinstance(source, collections.abc.Mapping):
            for field, value in source.items():
                if field in skippedFields:
                    continue
                converter = convByName.get(field, None)
                if not converter:
                    raise ValueError(
                        f"Unrecognized field {field} for {cls}; expected one of {sorted(convByName.keys())}"
                    )
                self._convert(dest, field, converter, value)
        else:
            # let's try as a 1-tuple
            dest = self.build(cls, (source,))

        for field, conv in convByName.items():
            if not hasattr(dest, field) and isinstance(conv, OptionalValue):
                setattr(dest, field, conv.DEFAULT)

        dest = self._callbackTable.get(
            (BuildCallback.AFTER_BUILD,) + callbackKey, lambda d: d
        )(dest)

        return dest


class TableUnbuilder:
    def __init__(self, callbackTable=None):
        if callbackTable is None:
            callbackTable = {}
        self._callbackTable = callbackTable

    def unbuild(self, table):
        assert isinstance(table, BaseTable)

        source = {}

        callbackKey = (type(table),)
        if isinstance(table, FormatSwitchingBaseTable):
            source["Format"] = int(table.Format)
            callbackKey += (table.Format,)

        for converter in table.getConverters():
            if isinstance(converter, ComputedInt):
                continue
            value = getattr(table, converter.name)

            enumClass = getattr(converter, "enumClass", None)
            if enumClass:
                source[converter.name] = value.name.lower()
            elif isinstance(converter, Struct):
                if converter.repeat:
                    source[converter.name] = [self.unbuild(v) for v in value]
                else:
                    source[converter.name] = self.unbuild(value)
            elif isinstance(converter, SimpleValue):
                # "simple" values (e.g. int, float, str) need no further un-building
                source[converter.name] = value
            else:
                raise NotImplementedError(
                    "Don't know how unbuild {value!r} with {converter!r}"
                )

        source = self._callbackTable.get(callbackKey, lambda s: s)(source)

        return source

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\S_V_G_.py ===
"""Compiles/decompiles SVG table.

https://docs.microsoft.com/en-us/typography/opentype/spec/svg

The XML format is:

.. code-block:: xml

	<SVG>
		<svgDoc endGlyphID="1" startGlyphID="1">
			<![CDATA[ <complete SVG doc> ]]
		</svgDoc>
	...
		<svgDoc endGlyphID="n" startGlyphID="m">
			<![CDATA[ <complete SVG doc> ]]
		</svgDoc>
	</SVG>
"""

from fontTools.misc.textTools import bytesjoin, safeEval, strjoin, tobytes, tostr
from fontTools.misc import sstruct
from . import DefaultTable
from collections.abc import Sequence
from dataclasses import dataclass, astuple
from io import BytesIO
import struct
import logging


log = logging.getLogger(__name__)


SVG_format_0 = """
	>   # big endian
	version:                  H
	offsetToSVGDocIndex:      L
	reserved:                 L
"""

SVG_format_0Size = sstruct.calcsize(SVG_format_0)

doc_index_entry_format_0 = """
	>   # big endian
	startGlyphID:             H
	endGlyphID:               H
	svgDocOffset:             L
	svgDocLength:             L
"""

doc_index_entry_format_0Size = sstruct.calcsize(doc_index_entry_format_0)


class table_S_V_G_(DefaultTable.DefaultTable):
    """Scalable Vector Graphics table

    The ``SVG`` table contains representations for glyphs in the SVG
    image format.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/stat
    """

    def decompile(self, data, ttFont):
        self.docList = []
        # Version 0 is the standardized version of the table; and current.
        # https://www.microsoft.com/typography/otspec/svg.htm
        sstruct.unpack(SVG_format_0, data[:SVG_format_0Size], self)
        if self.version != 0:
            log.warning(
                "Unknown SVG table version '%s'. Decompiling as version 0.",
                self.version,
            )
        # read in SVG Documents Index
        # data starts with the first entry of the entry list.
        pos = subTableStart = self.offsetToSVGDocIndex
        self.numEntries = struct.unpack(">H", data[pos : pos + 2])[0]
        pos += 2
        if self.numEntries > 0:
            data2 = data[pos:]
            entries = []
            for i in range(self.numEntries):
                record_data = data2[
                    i
                    * doc_index_entry_format_0Size : (i + 1)
                    * doc_index_entry_format_0Size
                ]
                docIndexEntry = sstruct.unpack(
                    doc_index_entry_format_0, record_data, DocumentIndexEntry()
                )
                entries.append(docIndexEntry)

            for entry in entries:
                start = entry.svgDocOffset + subTableStart
                end = start + entry.svgDocLength
                doc = data[start:end]
                compressed = False
                if doc.startswith(b"\x1f\x8b"):
                    import gzip

                    bytesIO = BytesIO(doc)
                    with gzip.GzipFile(None, "r", fileobj=bytesIO) as gunzipper:
                        doc = gunzipper.read()
                    del bytesIO
                    compressed = True
                doc = tostr(doc, "utf_8")
                self.docList.append(
                    SVGDocument(doc, entry.startGlyphID, entry.endGlyphID, compressed)
                )

    def compile(self, ttFont):
        version = 0
        offsetToSVGDocIndex = (
            SVG_format_0Size  # I start the SVGDocIndex right after the header.
        )
        # get SGVDoc info.
        docList = []
        entryList = []
        numEntries = len(self.docList)
        datum = struct.pack(">H", numEntries)
        entryList.append(datum)
        curOffset = len(datum) + doc_index_entry_format_0Size * numEntries
        seenDocs = {}
        allCompressed = getattr(self, "compressed", False)
        for i, doc in enumerate(self.docList):
            if isinstance(doc, (list, tuple)):
                doc = SVGDocument(*doc)
                self.docList[i] = doc
            docBytes = tobytes(doc.data, encoding="utf_8")
            if (allCompressed or doc.compressed) and not docBytes.startswith(
                b"\x1f\x8b"
            ):
                import gzip

                bytesIO = BytesIO()
                # mtime=0 strips the useless timestamp and makes gzip output reproducible;
                # equivalent to `gzip -n`
                with gzip.GzipFile(None, "w", fileobj=bytesIO, mtime=0) as gzipper:
                    gzipper.write(docBytes)
                gzipped = bytesIO.getvalue()
                if len(gzipped) < len(docBytes):
                    docBytes = gzipped
                del gzipped, bytesIO
            docLength = len(docBytes)
            if docBytes in seenDocs:
                docOffset = seenDocs[docBytes]
            else:
                docOffset = curOffset
                curOffset += docLength
                seenDocs[docBytes] = docOffset
                docList.append(docBytes)
            entry = struct.pack(
                ">HHLL", doc.startGlyphID, doc.endGlyphID, docOffset, docLength
            )
            entryList.append(entry)
        entryList.extend(docList)
        svgDocData = bytesjoin(entryList)

        reserved = 0
        header = struct.pack(">HLL", version, offsetToSVGDocIndex, reserved)
        data = [header, svgDocData]
        data = bytesjoin(data)
        return data

    def toXML(self, writer, ttFont):
        for i, doc in enumerate(self.docList):
            if isinstance(doc, (list, tuple)):
                doc = SVGDocument(*doc)
                self.docList[i] = doc
            attrs = {"startGlyphID": doc.startGlyphID, "endGlyphID": doc.endGlyphID}
            if doc.compressed:
                attrs["compressed"] = 1
            writer.begintag("svgDoc", **attrs)
            writer.newline()
            writer.writecdata(doc.data)
            writer.newline()
            writer.endtag("svgDoc")
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "svgDoc":
            if not hasattr(self, "docList"):
                self.docList = []
            doc = strjoin(content)
            doc = doc.strip()
            startGID = int(attrs["startGlyphID"])
            endGID = int(attrs["endGlyphID"])
            compressed = bool(safeEval(attrs.get("compressed", "0")))
            self.docList.append(SVGDocument(doc, startGID, endGID, compressed))
        else:
            log.warning("Unknown %s %s", name, content)


class DocumentIndexEntry(object):
    def __init__(self):
        self.startGlyphID = None  # USHORT
        self.endGlyphID = None  # USHORT
        self.svgDocOffset = None  # ULONG
        self.svgDocLength = None  # ULONG

    def __repr__(self):
        return (
            "startGlyphID: %s, endGlyphID: %s, svgDocOffset: %s, svgDocLength: %s"
            % (self.startGlyphID, self.endGlyphID, self.svgDocOffset, self.svgDocLength)
        )


@dataclass
class SVGDocument(Sequence):
    data: str
    startGlyphID: int
    endGlyphID: int
    compressed: bool = False

    # Previously, the SVG table's docList attribute contained a lists of 3 items:
    # [doc, startGlyphID, endGlyphID]; later, we added a `compressed` attribute.
    # For backward compatibility with code that depends of them being sequences of
    # fixed length=3, we subclass the Sequence abstract base class and pretend only
    # the first three items are present. 'compressed' is only accessible via named
    # attribute lookup like regular dataclasses: i.e. `doc.compressed`, not `doc[3]`
    def __getitem__(self, index):
        return astuple(self)[:3][index]

    def __len__(self):
        return 3

# === NexusCore/openenv\Lib\site-packages\ipykernel\inprocess\client.py ===
"""A client for in-process kernels."""

# -----------------------------------------------------------------------------
#  Copyright (C) 2012  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file LICENSE, distributed as part of this software.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import asyncio

from jupyter_client.client import KernelClient
from jupyter_client.clientabc import KernelClientABC
from jupyter_core.utils import run_sync

# IPython imports
from traitlets import Instance, Type, default

# Local imports
from .channels import InProcessChannel, InProcessHBChannel

# -----------------------------------------------------------------------------
# Main kernel Client class
# -----------------------------------------------------------------------------


class InProcessKernelClient(KernelClient):
    """A client for an in-process kernel.

    This class implements the interface of
    `jupyter_client.clientabc.KernelClientABC` and allows
    (asynchronous) frontends to be used seamlessly with an in-process kernel.

    See `jupyter_client.client.KernelClient` for docstrings.
    """

    # The classes to use for the various channels.
    shell_channel_class = Type(InProcessChannel)  # type:ignore[arg-type]
    iopub_channel_class = Type(InProcessChannel)  # type:ignore[arg-type]
    stdin_channel_class = Type(InProcessChannel)  # type:ignore[arg-type]
    control_channel_class = Type(InProcessChannel)  # type:ignore[arg-type]
    hb_channel_class = Type(InProcessHBChannel)  # type:ignore[arg-type]

    kernel = Instance("ipykernel.inprocess.ipkernel.InProcessKernel", allow_none=True)

    # --------------------------------------------------------------------------
    # Channel management methods
    # --------------------------------------------------------------------------

    @default("blocking_class")
    def _default_blocking_class(self):
        from .blocking import BlockingInProcessKernelClient

        return BlockingInProcessKernelClient

    def get_connection_info(self):
        """Get the connection info for the client."""
        d = super().get_connection_info()
        d["kernel"] = self.kernel  # type:ignore[assignment]
        return d

    def start_channels(self, *args, **kwargs):
        """Start the channels on the client."""
        super().start_channels()
        if self.kernel:
            self.kernel.frontends.append(self)

    @property
    def shell_channel(self):
        if self._shell_channel is None:
            self._shell_channel = self.shell_channel_class(self)  # type:ignore[abstract,call-arg]
        return self._shell_channel

    @property
    def iopub_channel(self):
        if self._iopub_channel is None:
            self._iopub_channel = self.iopub_channel_class(self)  # type:ignore[abstract,call-arg]
        return self._iopub_channel

    @property
    def stdin_channel(self):
        if self._stdin_channel is None:
            self._stdin_channel = self.stdin_channel_class(self)  # type:ignore[abstract,call-arg]
        return self._stdin_channel

    @property
    def control_channel(self):
        if self._control_channel is None:
            self._control_channel = self.control_channel_class(self)  # type:ignore[abstract,call-arg]
        return self._control_channel

    @property
    def hb_channel(self):
        if self._hb_channel is None:
            self._hb_channel = self.hb_channel_class(self)  # type:ignore[abstract,call-arg]
        return self._hb_channel

    # Methods for sending specific messages
    # -------------------------------------

    def execute(
        self, code, silent=False, store_history=True, user_expressions=None, allow_stdin=None
    ):
        """Execute code on the client."""
        if allow_stdin is None:
            allow_stdin = self.allow_stdin
        content = dict(
            code=code,
            silent=silent,
            store_history=store_history,
            user_expressions=user_expressions or {},
            allow_stdin=allow_stdin,
        )
        msg = self.session.msg("execute_request", content)
        self._dispatch_to_kernel(msg)
        return msg["header"]["msg_id"]

    def complete(self, code, cursor_pos=None):
        """Get code completion."""
        if cursor_pos is None:
            cursor_pos = len(code)
        content = dict(code=code, cursor_pos=cursor_pos)
        msg = self.session.msg("complete_request", content)
        self._dispatch_to_kernel(msg)
        return msg["header"]["msg_id"]

    def inspect(self, code, cursor_pos=None, detail_level=0):
        """Get code inspection."""
        if cursor_pos is None:
            cursor_pos = len(code)
        content = dict(
            code=code,
            cursor_pos=cursor_pos,
            detail_level=detail_level,
        )
        msg = self.session.msg("inspect_request", content)
        self._dispatch_to_kernel(msg)
        return msg["header"]["msg_id"]

    def history(self, raw=True, output=False, hist_access_type="range", **kwds):
        """Get code history."""
        content = dict(raw=raw, output=output, hist_access_type=hist_access_type, **kwds)
        msg = self.session.msg("history_request", content)
        self._dispatch_to_kernel(msg)
        return msg["header"]["msg_id"]

    def shutdown(self, restart=False):
        """Handle shutdown."""
        # FIXME: What to do here?
        msg = "Cannot shutdown in-process kernel"
        raise NotImplementedError(msg)

    def kernel_info(self):
        """Request kernel info."""
        msg = self.session.msg("kernel_info_request")
        self._dispatch_to_kernel(msg)
        return msg["header"]["msg_id"]

    def comm_info(self, target_name=None):
        """Request a dictionary of valid comms and their targets."""
        content = {} if target_name is None else dict(target_name=target_name)
        msg = self.session.msg("comm_info_request", content)
        self._dispatch_to_kernel(msg)
        return msg["header"]["msg_id"]

    def input(self, string):
        """Handle kernel input."""
        if self.kernel is None:
            msg = "Cannot send input reply. No kernel exists."
            raise RuntimeError(msg)
        self.kernel.raw_input_str = string

    def is_complete(self, code):
        """Handle an is_complete request."""
        msg = self.session.msg("is_complete_request", {"code": code})
        self._dispatch_to_kernel(msg)
        return msg["header"]["msg_id"]

    def _dispatch_to_kernel(self, msg):
        """Send a message to the kernel and handle a reply."""
        kernel = self.kernel
        if kernel is None:
            msg = "Cannot send request. No kernel exists."
            raise RuntimeError(msg)

        stream = kernel.shell_stream
        self.session.send(stream, msg)
        msg_parts = stream.recv_multipart()
        if run_sync is not None:
            dispatch_shell = run_sync(kernel.dispatch_shell)
            dispatch_shell(msg_parts)
        else:
            loop = asyncio.get_event_loop()  # type:ignore[unreachable]
            loop.run_until_complete(kernel.dispatch_shell(msg_parts))
        idents, reply_msg = self.session.recv(stream, copy=False)
        self.shell_channel.call_handlers_later(reply_msg)

    def get_shell_msg(self, block=True, timeout=None):
        """Get a shell message."""
        return self.shell_channel.get_msg(block, timeout)

    def get_iopub_msg(self, block=True, timeout=None):
        """Get an iopub message."""
        return self.iopub_channel.get_msg(block, timeout)

    def get_stdin_msg(self, block=True, timeout=None):
        """Get a stdin message."""
        return self.stdin_channel.get_msg(block, timeout)

    def get_control_msg(self, block=True, timeout=None):
        """Get a control message."""
        return self.control_channel.get_msg(block, timeout)


# -----------------------------------------------------------------------------
# ABC Registration
# -----------------------------------------------------------------------------

KernelClientABC.register(InProcessKernelClient)

# === NexusCore/openenv\Lib\site-packages\joblib\externals\loky\backend\reduction.py ===
###############################################################################
# Customizable Pickler with some basic reducers
#
# author: Thomas Moreau
#
# adapted from multiprocessing/reduction.py (17/02/2017)
#  * Replace the ForkingPickler with a similar _LokyPickler,
#  * Add CustomizableLokyPickler to allow customizing pickling process
#    on the fly.
#
import copyreg
import io
import functools
import types
import sys
import os

from multiprocessing import util
from pickle import loads, HIGHEST_PROTOCOL

###############################################################################
# Enable custom pickling in Loky.

_dispatch_table = {}


def register(type_, reduce_function):
    _dispatch_table[type_] = reduce_function


###############################################################################
# Registers extra pickling routines to improve picklization  for loky


# make methods picklable
def _reduce_method(m):
    if m.__self__ is None:
        return getattr, (m.__class__, m.__func__.__name__)
    else:
        return getattr, (m.__self__, m.__func__.__name__)


class _C:
    def f(self):
        pass

    @classmethod
    def h(cls):
        pass


register(type(_C().f), _reduce_method)
register(type(_C.h), _reduce_method)


def _reduce_method_descriptor(m):
    return getattr, (m.__objclass__, m.__name__)


register(type(list.append), _reduce_method_descriptor)
register(type(int.__add__), _reduce_method_descriptor)


# Make partial func pickable
def _reduce_partial(p):
    return _rebuild_partial, (p.func, p.args, p.keywords or {})


def _rebuild_partial(func, args, keywords):
    return functools.partial(func, *args, **keywords)


register(functools.partial, _reduce_partial)

if sys.platform != "win32":
    from ._posix_reduction import _mk_inheritable  # noqa: F401
else:
    from . import _win_reduction  # noqa: F401

# global variable to change the pickler behavior
try:
    from joblib.externals import cloudpickle  # noqa: F401

    DEFAULT_ENV = "cloudpickle"
except ImportError:
    # If cloudpickle is not present, fallback to pickle
    DEFAULT_ENV = "pickle"

ENV_LOKY_PICKLER = os.environ.get("LOKY_PICKLER", DEFAULT_ENV)
_LokyPickler = None
_loky_pickler_name = None


def set_loky_pickler(loky_pickler=None):
    global _LokyPickler, _loky_pickler_name

    if loky_pickler is None:
        loky_pickler = ENV_LOKY_PICKLER

    loky_pickler_cls = None

    # The default loky_pickler is cloudpickle
    if loky_pickler in ["", None]:
        loky_pickler = "cloudpickle"

    if loky_pickler == _loky_pickler_name:
        return

    if loky_pickler == "cloudpickle":
        from joblib.externals.cloudpickle import CloudPickler as loky_pickler_cls
    else:
        try:
            from importlib import import_module

            module_pickle = import_module(loky_pickler)
            loky_pickler_cls = module_pickle.Pickler
        except (ImportError, AttributeError) as e:
            extra_info = (
                "\nThis error occurred while setting loky_pickler to"
                f" '{loky_pickler}', as required by the env variable "
                "LOKY_PICKLER or the function set_loky_pickler."
            )
            e.args = (e.args[0] + extra_info,) + e.args[1:]
            e.msg = e.args[0]
            raise e

    util.debug(
        f"Using '{loky_pickler if loky_pickler else 'cloudpickle'}' for "
        "serialization."
    )

    class CustomizablePickler(loky_pickler_cls):
        _loky_pickler_cls = loky_pickler_cls

        def _set_dispatch_table(self, dispatch_table):
            for ancestor_class in self._loky_pickler_cls.mro():
                dt_attribute = getattr(ancestor_class, "dispatch_table", None)
                if isinstance(dt_attribute, types.MemberDescriptorType):
                    # Ancestor class (typically _pickle.Pickler) has a
                    # member_descriptor for its "dispatch_table" attribute. Use
                    # it to set the dispatch_table as a member instead of a
                    # dynamic attribute in the __dict__ of the instance,
                    # otherwise it will not be taken into account by the C
                    # implementation of the dump method if a subclass defines a
                    # class-level dispatch_table attribute as was done in
                    # cloudpickle 1.6.0:
                    # https://github.com/joblib/loky/pull/260
                    dt_attribute.__set__(self, dispatch_table)
                    break

            # On top of member descriptor set, also use setattr such that code
            # that directly access self.dispatch_table gets a consistent view
            # of the same table.
            self.dispatch_table = dispatch_table

        def __init__(self, writer, reducers=None, protocol=HIGHEST_PROTOCOL):
            loky_pickler_cls.__init__(self, writer, protocol=protocol)
            if reducers is None:
                reducers = {}

            if hasattr(self, "dispatch_table"):
                # Force a copy that we will update without mutating the
                # any class level defined dispatch_table.
                loky_dt = dict(self.dispatch_table)
            else:
                # Use standard reducers as bases
                loky_dt = copyreg.dispatch_table.copy()

            # Register loky specific reducers
            loky_dt.update(_dispatch_table)

            # Set the new dispatch table, taking care of the fact that we
            # need to use the member_descriptor when we inherit from a
            # subclass of the C implementation of the Pickler base class
            # with an class level dispatch_table attribute.
            self._set_dispatch_table(loky_dt)

            # Register the reducers
            for type, reduce_func in reducers.items():
                self.register(type, reduce_func)

        def register(self, type, reduce_func):
            """Attach a reducer function to a given type in the dispatch table."""
            self.dispatch_table[type] = reduce_func

    _LokyPickler = CustomizablePickler
    _loky_pickler_name = loky_pickler


def get_loky_pickler_name():
    global _loky_pickler_name
    return _loky_pickler_name


def get_loky_pickler():
    global _LokyPickler
    return _LokyPickler


# Set it to its default value
set_loky_pickler()


def dump(obj, file, reducers=None, protocol=None):
    """Replacement for pickle.dump() using _LokyPickler."""
    global _LokyPickler
    _LokyPickler(file, reducers=reducers, protocol=protocol).dump(obj)


def dumps(obj, reducers=None, protocol=None):
    global _LokyPickler

    buf = io.BytesIO()
    dump(obj, buf, reducers=reducers, protocol=protocol)
    return buf.getbuffer()


__all__ = ["dump", "dumps", "loads", "register", "set_loky_pickler"]

if sys.platform == "win32":
    from multiprocessing.reduction import duplicate

    __all__ += ["duplicate"]

# === NexusCore/openenv\Lib\site-packages\litellm\llms\sagemaker\common_utils.py ===
import json
from typing import AsyncIterator, Iterator, List, Optional, Union

import httpx

import litellm
from litellm import verbose_logger
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.types.utils import GenericStreamingChunk as GChunk
from litellm.types.utils import StreamingChatCompletionChunk

_response_stream_shape_cache = None


class SagemakerError(BaseLLMException):
    def __init__(
        self,
        status_code: int,
        message: str,
        headers: Optional[Union[dict, httpx.Headers]] = None,
    ):
        super().__init__(status_code=status_code, message=message, headers=headers)


class AWSEventStreamDecoder:
    def __init__(self, model: str, is_messages_api: Optional[bool] = None) -> None:
        from botocore.parsers import EventStreamJSONParser

        self.model = model
        self.parser = EventStreamJSONParser()
        self.content_blocks: List = []
        self.is_messages_api = is_messages_api

    def _chunk_parser_messages_api(
        self, chunk_data: dict
    ) -> StreamingChatCompletionChunk:
        openai_chunk = StreamingChatCompletionChunk(
            **{"model": self.model, **chunk_data}
        )

        return openai_chunk

    def _chunk_parser(self, chunk_data: dict) -> GChunk:
        verbose_logger.debug("in sagemaker chunk parser, chunk_data %s", chunk_data)
        _token = chunk_data.get("token", {}) or {}
        _index = chunk_data.get("index", None) or 0
        is_finished = False
        finish_reason = ""

        _text = _token.get("text", "")
        if _text == "<|endoftext|>":
            return GChunk(
                text="",
                index=_index,
                is_finished=True,
                finish_reason="stop",
                usage=None,
            )

        return GChunk(
            text=_text,
            index=_index,
            is_finished=is_finished,
            finish_reason=finish_reason,
            usage=None,
        )

    def iter_bytes(
        self, iterator: Iterator[bytes]
    ) -> Iterator[Optional[Union[GChunk, StreamingChatCompletionChunk]]]:
        """Given an iterator that yields lines, iterate over it & yield every event encountered"""
        from botocore.eventstream import EventStreamBuffer

        event_stream_buffer = EventStreamBuffer()
        accumulated_json = ""

        for chunk in iterator:
            event_stream_buffer.add_data(chunk)
            for event in event_stream_buffer:
                message = self._parse_message_from_event(event)
                if message:
                    # remove data: prefix and "\n\n" at the end
                    message = (
                        litellm.CustomStreamWrapper._strip_sse_data_from_chunk(message)
                        or ""
                    )
                    message = message.replace("\n\n", "")

                    # Accumulate JSON data
                    accumulated_json += message

                    # Try to parse the accumulated JSON
                    try:
                        _data = json.loads(accumulated_json)
                        if self.is_messages_api:
                            yield self._chunk_parser_messages_api(chunk_data=_data)
                        else:
                            yield self._chunk_parser(chunk_data=_data)
                        # Reset accumulated_json after successful parsing
                        accumulated_json = ""
                    except json.JSONDecodeError:
                        # If it's not valid JSON yet, continue to the next event
                        continue

        # Handle any remaining data after the iterator is exhausted
        if accumulated_json:
            try:
                _data = json.loads(accumulated_json)
                if self.is_messages_api:
                    yield self._chunk_parser_messages_api(chunk_data=_data)
                else:
                    yield self._chunk_parser(chunk_data=_data)
            except json.JSONDecodeError:
                # Handle or log any unparseable data at the end
                verbose_logger.error(
                    f"Warning: Unparseable JSON data remained: {accumulated_json}"
                )
                yield None

    async def aiter_bytes(
        self, iterator: AsyncIterator[bytes]
    ) -> AsyncIterator[Optional[Union[GChunk, StreamingChatCompletionChunk]]]:
        """Given an async iterator that yields lines, iterate over it & yield every event encountered"""
        from botocore.eventstream import EventStreamBuffer

        event_stream_buffer = EventStreamBuffer()
        accumulated_json = ""

        async for chunk in iterator:
            event_stream_buffer.add_data(chunk)
            for event in event_stream_buffer:
                try:
                    message = self._parse_message_from_event(event)
                    if message:
                        verbose_logger.debug(
                            "sagemaker  parsed chunk bytes %s", message
                        )
                        # remove data: prefix and "\n\n" at the end
                        message = (
                            litellm.CustomStreamWrapper._strip_sse_data_from_chunk(
                                message
                            )
                            or ""
                        )
                        message = message.replace("\n\n", "")

                        # Accumulate JSON data
                        accumulated_json += message

                        # Try to parse the accumulated JSON
                        _data = json.loads(accumulated_json)
                        if self.is_messages_api:
                            yield self._chunk_parser_messages_api(chunk_data=_data)
                        else:
                            yield self._chunk_parser(chunk_data=_data)
                        # Reset accumulated_json after successful parsing
                        accumulated_json = ""
                except json.JSONDecodeError:
                    # If it's not valid JSON yet, continue to the next event
                    continue
                except UnicodeDecodeError as e:
                    verbose_logger.warning(
                        f"UnicodeDecodeError: {e}. Attempting to combine with next event."
                    )
                    continue
                except Exception as e:
                    verbose_logger.error(
                        f"Error parsing message: {e}. Attempting to combine with next event."
                    )
                    continue

        # Handle any remaining data after the iterator is exhausted
        if accumulated_json:
            try:
                _data = json.loads(accumulated_json)
                if self.is_messages_api:
                    yield self._chunk_parser_messages_api(chunk_data=_data)
                else:
                    yield self._chunk_parser(chunk_data=_data)
            except json.JSONDecodeError:
                # Handle or log any unparseable data at the end
                verbose_logger.error(
                    f"Warning: Unparseable JSON data remained: {accumulated_json}"
                )
                yield None
            except Exception as e:
                verbose_logger.error(f"Final error parsing accumulated JSON: {e}")

    def _parse_message_from_event(self, event) -> Optional[str]:
        response_dict = event.to_response_dict()
        parsed_response = self.parser.parse(response_dict, get_response_stream_shape())

        if response_dict["status_code"] != 200:
            raise ValueError(f"Bad response code, expected 200: {response_dict}")

        if "chunk" in parsed_response:
            chunk = parsed_response.get("chunk")
            if not chunk:
                return None
            return chunk.get("bytes").decode()  # type: ignore[no-any-return]
        else:
            chunk = response_dict.get("body")
            if not chunk:
                return None

            return chunk.decode()  # type: ignore[no-any-return]


def get_response_stream_shape():
    global _response_stream_shape_cache
    if _response_stream_shape_cache is None:
        from botocore.loaders import Loader
        from botocore.model import ServiceModel

        loader = Loader()
        sagemaker_service_dict = loader.load_service_model(
            "sagemaker-runtime", "service-2"
        )
        sagemaker_service_model = ServiceModel(sagemaker_service_dict)
        _response_stream_shape_cache = sagemaker_service_model.shape_for(
            "InvokeEndpointWithResponseStreamOutput"
        )
    return _response_stream_shape_cache

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\common_utils\http_parsing_utils.py ===
import json
from typing import Any, Dict, List, Optional

import orjson
from fastapi import Request, UploadFile, status

from litellm._logging import verbose_proxy_logger
from litellm.types.router import Deployment


async def _read_request_body(request: Optional[Request]) -> Dict:
    """
    Safely read the request body and parse it as JSON.

    Parameters:
    - request: The request object to read the body from

    Returns:
    - dict: Parsed request data as a dictionary or an empty dictionary if parsing fails
    """
    try:
        if request is None:
            return {}

        # Check if we already read and parsed the body
        _cached_request_body: Optional[dict] = _safe_get_request_parsed_body(
            request=request
        )
        if _cached_request_body is not None:
            return _cached_request_body

        _request_headers: dict = _safe_get_request_headers(request=request)
        content_type = _request_headers.get("content-type", "")

        if "form" in content_type:
            parsed_body = dict(await request.form())
        else:
            # Read the request body
            body = await request.body()

            # Return empty dict if body is empty or None
            if not body:
                parsed_body = {}
            else:
                try:
                    parsed_body = orjson.loads(body)
                except orjson.JSONDecodeError:
                    # Fall back to the standard json module which is more forgiving
                    # First decode bytes to string if needed
                    body_str = body.decode("utf-8") if isinstance(body, bytes) else body

                    # Replace invalid surrogate pairs
                    import re

                    # This regex finds incomplete surrogate pairs
                    body_str = re.sub(
                        r"[\uD800-\uDBFF](?![\uDC00-\uDFFF])", "", body_str
                    )
                    # This regex finds low surrogates without high surrogates
                    body_str = re.sub(
                        r"(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]", "", body_str
                    )

                    parsed_body = json.loads(body_str)

        # Cache the parsed result
        _safe_set_request_parsed_body(request=request, parsed_body=parsed_body)
        return parsed_body

    except (json.JSONDecodeError, orjson.JSONDecodeError):
        verbose_proxy_logger.exception("Invalid JSON payload received.")
        return {}
    except Exception as e:
        # Catch unexpected errors to avoid crashes
        verbose_proxy_logger.exception(
            "Unexpected error reading request body - {}".format(e)
        )
        return {}


def _safe_get_request_parsed_body(request: Optional[Request]) -> Optional[dict]:
    if request is None:
        return None
    if (
        hasattr(request, "scope")
        and "parsed_body" in request.scope
        and isinstance(request.scope["parsed_body"], tuple)
    ):
        accepted_keys, parsed_body = request.scope["parsed_body"]
        return {key: parsed_body[key] for key in accepted_keys}
    return None


def _safe_set_request_parsed_body(
    request: Optional[Request],
    parsed_body: dict,
) -> None:
    try:
        if request is None:
            return
        request.scope["parsed_body"] = (tuple(parsed_body.keys()), parsed_body)
    except Exception as e:
        verbose_proxy_logger.debug(
            "Unexpected error setting request parsed body - {}".format(e)
        )


def _safe_get_request_headers(request: Optional[Request]) -> dict:
    """
    [Non-Blocking] Safely get the request headers
    """
    try:
        if request is None:
            return {}
        return dict(request.headers)
    except Exception as e:
        verbose_proxy_logger.debug(
            "Unexpected error reading request headers - {}".format(e)
        )
        return {}


def check_file_size_under_limit(
    request_data: dict,
    file: UploadFile,
    router_model_names: List[str],
) -> bool:
    """
    Check if any files passed in request are under max_file_size_mb

    Returns True -> when file size is under max_file_size_mb limit
    Raises ProxyException -> when file size is over max_file_size_mb limit or not a premium_user
    """
    from litellm.proxy.proxy_server import (
        CommonProxyErrors,
        ProxyException,
        llm_router,
        premium_user,
    )

    file_contents_size = file.size or 0
    file_content_size_in_mb = file_contents_size / (1024 * 1024)
    if "metadata" not in request_data:
        request_data["metadata"] = {}
    request_data["metadata"]["file_size_in_mb"] = file_content_size_in_mb
    max_file_size_mb = None

    if llm_router is not None and request_data["model"] in router_model_names:
        try:
            deployment: Optional[
                Deployment
            ] = llm_router.get_deployment_by_model_group_name(
                model_group_name=request_data["model"]
            )
            if (
                deployment
                and deployment.litellm_params is not None
                and deployment.litellm_params.max_file_size_mb is not None
            ):
                max_file_size_mb = deployment.litellm_params.max_file_size_mb
        except Exception as e:
            verbose_proxy_logger.error(
                "Got error when checking file size: %s", (str(e))
            )

    if max_file_size_mb is not None:
        verbose_proxy_logger.debug(
            "Checking file size, file content size=%s, max_file_size_mb=%s",
            file_content_size_in_mb,
            max_file_size_mb,
        )
        if not premium_user:
            raise ProxyException(
                message=f"Tried setting max_file_size_mb for /audio/transcriptions. {CommonProxyErrors.not_premium_user.value}",
                code=status.HTTP_400_BAD_REQUEST,
                type="bad_request",
                param="file",
            )
        if file_content_size_in_mb > max_file_size_mb:
            raise ProxyException(
                message=f"File size is too large. Please check your file size. Passed file size: {file_content_size_in_mb} MB. Max file size: {max_file_size_mb} MB",
                code=status.HTTP_400_BAD_REQUEST,
                type="bad_request",
                param="file",
            )

    return True


async def get_form_data(request: Request) -> Dict[str, Any]:
    """
    Read form data from request

    Handles when OpenAI SDKs pass form keys as `timestamp_granularities[]="word"` instead of `timestamp_granularities=["word", "sentence"]`
    """
    form = await request.form()
    form_data = dict(form)
    parsed_form_data: dict[str, Any] = {}
    for key, value in form_data.items():
        # OpenAI SDKs pass form keys as `timestamp_granularities[]="word"` instead of `timestamp_granularities=["word", "sentence"]`
        if key.endswith("[]"):
            clean_key = key[:-2]
            parsed_form_data.setdefault(clean_key, []).append(value)
        else:
            parsed_form_data[key] = value
    return parsed_form_data


async def get_request_body(request: Request) -> Dict[str, Any]:
    """
    Read the request body and parse it as JSON.
    """
    if request.headers.get("content-type") == "application/json":
        return await _read_request_body(request)
    elif (
        request.headers.get("content-type") == "multipart/form-data"
        or request.headers.get("content-type") == "application/x-www-form-urlencoded"
    ):
        return await get_form_data(request)
    else:
        raise ValueError(
            f"Unsupported content type: {request.headers.get('content-type')}"
        )

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\progress_bar.py ===
import math
from functools import lru_cache
from time import monotonic
from typing import Iterable, List, Optional

from .color import Color, blend_rgb
from .color_triplet import ColorTriplet
from .console import Console, ConsoleOptions, RenderResult
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import Style, StyleType

# Number of characters before 'pulse' animation repeats
PULSE_SIZE = 20


class ProgressBar(JupyterMixin):
    """Renders a (progress) bar. Used by rich.progress.

    Args:
        total (float, optional): Number of steps in the bar. Defaults to 100. Set to None to render a pulsing animation.
        completed (float, optional): Number of steps completed. Defaults to 0.
        width (int, optional): Width of the bar, or ``None`` for maximum width. Defaults to None.
        pulse (bool, optional): Enable pulse effect. Defaults to False. Will pulse if a None total was passed.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
        animation_time (Optional[float], optional): Time in seconds to use for animation, or None to use system time.
    """

    def __init__(
        self,
        total: Optional[float] = 100.0,
        completed: float = 0,
        width: Optional[int] = None,
        pulse: bool = False,
        style: StyleType = "bar.back",
        complete_style: StyleType = "bar.complete",
        finished_style: StyleType = "bar.finished",
        pulse_style: StyleType = "bar.pulse",
        animation_time: Optional[float] = None,
    ):
        self.total = total
        self.completed = completed
        self.width = width
        self.pulse = pulse
        self.style = style
        self.complete_style = complete_style
        self.finished_style = finished_style
        self.pulse_style = pulse_style
        self.animation_time = animation_time

        self._pulse_segments: Optional[List[Segment]] = None

    def __repr__(self) -> str:
        return f"<Bar {self.completed!r} of {self.total!r}>"

    @property
    def percentage_completed(self) -> Optional[float]:
        """Calculate percentage complete."""
        if self.total is None:
            return None
        completed = (self.completed / self.total) * 100.0
        completed = min(100, max(0.0, completed))
        return completed

    @lru_cache(maxsize=16)
    def _get_pulse_segments(
        self,
        fore_style: Style,
        back_style: Style,
        color_system: str,
        no_color: bool,
        ascii: bool = False,
    ) -> List[Segment]:
        """Get a list of segments to render a pulse animation.

        Returns:
            List[Segment]: A list of segments, one segment per character.
        """
        bar = "-" if ascii else "━"
        segments: List[Segment] = []
        if color_system not in ("standard", "eight_bit", "truecolor") or no_color:
            segments += [Segment(bar, fore_style)] * (PULSE_SIZE // 2)
            segments += [Segment(" " if no_color else bar, back_style)] * (
                PULSE_SIZE - (PULSE_SIZE // 2)
            )
            return segments

        append = segments.append
        fore_color = (
            fore_style.color.get_truecolor()
            if fore_style.color
            else ColorTriplet(255, 0, 255)
        )
        back_color = (
            back_style.color.get_truecolor()
            if back_style.color
            else ColorTriplet(0, 0, 0)
        )
        cos = math.cos
        pi = math.pi
        _Segment = Segment
        _Style = Style
        from_triplet = Color.from_triplet

        for index in range(PULSE_SIZE):
            position = index / PULSE_SIZE
            fade = 0.5 + cos(position * pi * 2) / 2.0
            color = blend_rgb(fore_color, back_color, cross_fade=fade)
            append(_Segment(bar, _Style(color=from_triplet(color))))
        return segments

    def update(self, completed: float, total: Optional[float] = None) -> None:
        """Update progress with new values.

        Args:
            completed (float): Number of steps completed.
            total (float, optional): Total number of steps, or ``None`` to not change. Defaults to None.
        """
        self.completed = completed
        self.total = total if total is not None else self.total

    def _render_pulse(
        self, console: Console, width: int, ascii: bool = False
    ) -> Iterable[Segment]:
        """Renders the pulse animation.

        Args:
            console (Console): Console instance.
            width (int): Width in characters of pulse animation.

        Returns:
            RenderResult: [description]

        Yields:
            Iterator[Segment]: Segments to render pulse
        """
        fore_style = console.get_style(self.pulse_style, default="white")
        back_style = console.get_style(self.style, default="black")

        pulse_segments = self._get_pulse_segments(
            fore_style, back_style, console.color_system, console.no_color, ascii=ascii
        )
        segment_count = len(pulse_segments)
        current_time = (
            monotonic() if self.animation_time is None else self.animation_time
        )
        segments = pulse_segments * (int(width / segment_count) + 2)
        offset = int(-current_time * 15) % segment_count
        segments = segments[offset : offset + width]
        yield from segments

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        width = min(self.width or options.max_width, options.max_width)
        ascii = options.legacy_windows or options.ascii_only
        should_pulse = self.pulse or self.total is None
        if should_pulse:
            yield from self._render_pulse(console, width, ascii=ascii)
            return

        completed: Optional[float] = (
            min(self.total, max(0, self.completed)) if self.total is not None else None
        )

        bar = "-" if ascii else "━"
        half_bar_right = " " if ascii else "╸"
        half_bar_left = " " if ascii else "╺"
        complete_halves = (
            int(width * 2 * completed / self.total)
            if self.total and completed is not None
            else width * 2
        )
        bar_count = complete_halves // 2
        half_bar_count = complete_halves % 2
        style = console.get_style(self.style)
        is_finished = self.total is None or self.completed >= self.total
        complete_style = console.get_style(
            self.finished_style if is_finished else self.complete_style
        )
        _Segment = Segment
        if bar_count:
            yield _Segment(bar * bar_count, complete_style)
        if half_bar_count:
            yield _Segment(half_bar_right * half_bar_count, complete_style)

        if not console.no_color:
            remaining_bars = width - bar_count - half_bar_count
            if remaining_bars and console.color_system is not None:
                if not half_bar_count and bar_count:
                    yield _Segment(half_bar_left, style)
                    remaining_bars -= 1
                if remaining_bars:
                    yield _Segment(bar * remaining_bars, style)

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        return (
            Measurement(self.width, self.width)
            if self.width is not None
            else Measurement(4, options.max_width)
        )


if __name__ == "__main__":  # pragma: no cover
    console = Console()
    bar = ProgressBar(width=50, total=100)

    import time

    console.show_cursor(False)
    for n in range(0, 101, 1):
        bar.update(n)
        console.print(bar)
        console.file.write("\r")
        time.sleep(0.05)
    console.show_cursor(True)
    console.print()

# === NexusCore/openenv\Lib\site-packages\tornado\test\runtests.py ===
from functools import reduce
import gc
import io
import locale  # system locale module, not tornado.locale
import logging
import operator
import textwrap
import sys
import unittest
import warnings

from tornado.httpclient import AsyncHTTPClient
from tornado.httpserver import HTTPServer
from tornado.netutil import Resolver
from tornado.options import define, add_parse_callback, options
from tornado.test.util import ABT_SKIP_MESSAGE


TEST_MODULES = [
    "tornado.httputil.doctests",
    "tornado.iostream.doctests",
    "tornado.util.doctests",
    "tornado.test.asyncio_test",
    "tornado.test.auth_test",
    "tornado.test.autoreload_test",
    "tornado.test.circlerefs_test",
    "tornado.test.concurrent_test",
    "tornado.test.curl_httpclient_test",
    "tornado.test.escape_test",
    "tornado.test.gen_test",
    "tornado.test.http1connection_test",
    "tornado.test.httpclient_test",
    "tornado.test.httpserver_test",
    "tornado.test.httputil_test",
    "tornado.test.import_test",
    "tornado.test.ioloop_test",
    "tornado.test.iostream_test",
    "tornado.test.locale_test",
    "tornado.test.locks_test",
    "tornado.test.netutil_test",
    "tornado.test.log_test",
    "tornado.test.options_test",
    "tornado.test.process_test",
    "tornado.test.queues_test",
    "tornado.test.routing_test",
    "tornado.test.simple_httpclient_test",
    "tornado.test.tcpclient_test",
    "tornado.test.tcpserver_test",
    "tornado.test.template_test",
    "tornado.test.testing_test",
    "tornado.test.twisted_test",
    "tornado.test.util_test",
    "tornado.test.web_test",
    "tornado.test.websocket_test",
    "tornado.test.wsgi_test",
]


def all():
    return unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)


def test_runner_factory(stderr):

    class TornadoTextTestResult(unittest.TextTestResult):
        def addSkip(self, test, reason):
            if reason == ABT_SKIP_MESSAGE:
                # Don't report abstract base tests as skips in our own tooling.
                #
                # See tornado.test.util.abstract_base_test.
                return
            super().addSkip(test, reason)

    class TornadoTextTestRunner(unittest.TextTestRunner):
        def __init__(self, *args, **kwargs):
            kwargs["stream"] = stderr
            kwargs["resultclass"] = TornadoTextTestResult
            super().__init__(*args, **kwargs)

        def run(self, test):
            result = super().run(test)
            if result.skipped:
                skip_reasons = {reason for (test, reason) in result.skipped}
                self.stream.write(  # type: ignore
                    textwrap.fill(
                        "Some tests were skipped because: %s"
                        % ", ".join(sorted(skip_reasons))
                    )
                )
                self.stream.write("\n")  # type: ignore
            return result

    return TornadoTextTestRunner


class LogCounter(logging.Filter):
    """Counts the number of WARNING or higher log records."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.info_count = self.warning_count = self.error_count = 0

    def filter(self, record):
        if record.levelno >= logging.ERROR:
            self.error_count += 1
        elif record.levelno >= logging.WARNING:
            self.warning_count += 1
        elif record.levelno >= logging.INFO:
            self.info_count += 1
        return True


class CountingStderr(io.IOBase):
    def __init__(self, real):
        self.real = real
        self.byte_count = 0

    def write(self, data):
        self.byte_count += len(data)
        return self.real.write(data)

    def flush(self):
        return self.real.flush()


def main():
    # Be strict about most warnings (This is set in our test running
    # scripts to catch import-time warnings, but set it again here to
    # be sure). This also turns on warnings that are ignored by
    # default, including DeprecationWarnings and python 3.2's
    # ResourceWarnings.
    warnings.filterwarnings("error")
    # setuptools sometimes gives ImportWarnings about things that are on
    # sys.path even if they're not being used.
    warnings.filterwarnings("ignore", category=ImportWarning)
    # Tornado generally shouldn't use anything deprecated, but some of
    # our dependencies do (last match wins).
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("error", category=DeprecationWarning, module=r"tornado\..*")
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
    warnings.filterwarnings(
        "error", category=PendingDeprecationWarning, module=r"tornado\..*"
    )

    logging.getLogger("tornado.access").setLevel(logging.CRITICAL)

    define(
        "httpclient",
        type=str,
        default=None,
        callback=lambda s: AsyncHTTPClient.configure(
            s, defaults=dict(allow_ipv6=False)
        ),
    )
    define("httpserver", type=str, default=None, callback=HTTPServer.configure)
    define("resolver", type=str, default=None, callback=Resolver.configure)
    define(
        "debug_gc",
        type=str,
        multiple=True,
        help="A comma-separated list of gc module debug constants, "
        "e.g. DEBUG_STATS or DEBUG_COLLECTABLE,DEBUG_OBJECTS",
        callback=lambda values: gc.set_debug(
            reduce(operator.or_, (getattr(gc, v) for v in values))
        ),
    )
    define(
        "fail-if-logs",
        default=True,
        help="If true, fail the tests if any log output is produced (unless captured by ExpectLog)",
    )

    def set_locale(x):
        locale.setlocale(locale.LC_ALL, x)

    define("locale", type=str, default=None, callback=set_locale)

    log_counter = LogCounter()
    add_parse_callback(lambda: logging.getLogger().handlers[0].addFilter(log_counter))

    # Certain errors (especially "unclosed resource" errors raised in
    # destructors) go directly to stderr instead of logging. Count
    # anything written by anything but the test runner as an error.
    orig_stderr = sys.stderr
    counting_stderr = CountingStderr(orig_stderr)
    sys.stderr = counting_stderr  # type: ignore

    import tornado.testing

    kwargs = {}

    # HACK:  unittest.main will make its own changes to the warning
    # configuration, which may conflict with the settings above
    # or command-line flags like -bb.  Passing warnings=False
    # suppresses this behavior, although this looks like an implementation
    # detail.  http://bugs.python.org/issue15626
    kwargs["warnings"] = False

    kwargs["testRunner"] = test_runner_factory(orig_stderr)
    try:
        tornado.testing.main(**kwargs)
    finally:
        # The tests should run clean; consider it a failure if they
        # logged anything at info level or above.
        if (
            log_counter.info_count > 0
            or log_counter.warning_count > 0
            or log_counter.error_count > 0
            or counting_stderr.byte_count > 0
        ):
            logging.error(
                "logged %d infos, %d warnings, %d errors, and %d bytes to stderr",
                log_counter.info_count,
                log_counter.warning_count,
                log_counter.error_count,
                counting_stderr.byte_count,
            )
            if options.fail_if_logs:
                sys.exit(1)


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\trio\_core\_entry_queue.py ===
from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable
from typing import TYPE_CHECKING, NoReturn

import attrs

from .. import _core
from .._util import NoPublicConstructor, final
from ._wakeup_socketpair import WakeupSocketpair

if TYPE_CHECKING:
    from typing_extensions import TypeVarTuple, Unpack

    PosArgsT = TypeVarTuple("PosArgsT")

Function = Callable[..., object]  # type: ignore[explicit-any]
Job = tuple[Function, tuple[object, ...]]


@attrs.define
class EntryQueue:
    # This used to use a queue.Queue. but that was broken, because Queues are
    # implemented in Python, and not reentrant -- so it was thread-safe, but
    # not signal-safe. deque is implemented in C, so each operation is atomic
    # WRT threads (and this is guaranteed in the docs), AND each operation is
    # atomic WRT signal delivery (signal handlers can run on either side, but
    # not *during* a deque operation). dict makes similar guarantees - and
    # it's even ordered!
    queue: deque[Job] = attrs.Factory(deque)
    idempotent_queue: dict[Job, None] = attrs.Factory(dict)

    wakeup: WakeupSocketpair = attrs.Factory(WakeupSocketpair)
    done: bool = False
    # Must be a reentrant lock, because it's acquired from signal handlers.
    # RLock is signal-safe as of cpython 3.2. NB that this does mean that the
    # lock is effectively *disabled* when we enter from signal context. The
    # way we use the lock this is OK though, because when
    # run_sync_soon is called from a signal it's atomic WRT the
    # main thread -- it just might happen at some inconvenient place. But if
    # you look at the one place where the main thread holds the lock, it's
    # just to make 1 assignment, so that's atomic WRT a signal anyway.
    lock: threading.RLock = attrs.Factory(threading.RLock)

    async def task(self) -> None:
        assert _core.currently_ki_protected()
        # RLock has two implementations: a signal-safe version in _thread, and
        # and signal-UNsafe version in threading. We need the signal safe
        # version. Python 3.2 and later should always use this anyway, but,
        # since the symptoms if this goes wrong are just "weird rare
        # deadlocks", then let's make a little check.
        # See:
        #     https://bugs.python.org/issue13697#msg237140
        assert self.lock.__class__.__module__ == "_thread"

        def run_cb(job: Job) -> None:
            # We run this with KI protection enabled; it's the callback's
            # job to disable it if it wants it disabled. Exceptions are
            # treated like system task exceptions (i.e., converted into
            # TrioInternalError and cause everything to shut down).
            sync_fn, args = job
            try:
                sync_fn(*args)
            except BaseException as exc:

                async def kill_everything(  # noqa: RUF029  # await not used
                    exc: BaseException,
                ) -> NoReturn:
                    raise exc

                try:
                    _core.spawn_system_task(kill_everything, exc)
                except RuntimeError:
                    # We're quite late in the shutdown process and the
                    # system nursery is already closed.
                    # TODO(2020-06): this is a gross hack and should
                    # be fixed soon when we address #1607.
                    parent_nursery = _core.current_task().parent_nursery
                    if parent_nursery is None:
                        raise AssertionError(
                            "Internal error: `parent_nursery` should never be `None`",
                        ) from exc  # pragma: no cover
                    parent_nursery.start_soon(kill_everything, exc)

        # This has to be carefully written to be safe in the face of new items
        # being queued while we iterate, and to do a bounded amount of work on
        # each pass:
        def run_all_bounded() -> None:
            for _ in range(len(self.queue)):
                run_cb(self.queue.popleft())
            for job in list(self.idempotent_queue):
                del self.idempotent_queue[job]
                run_cb(job)

        try:
            while True:
                run_all_bounded()
                if not self.queue and not self.idempotent_queue:
                    await self.wakeup.wait_woken()
                else:
                    await _core.checkpoint()
        except _core.Cancelled:
            # Keep the work done with this lock held as minimal as possible,
            # because it doesn't protect us against concurrent signal delivery
            # (see the comment above). Notice that this code would still be
            # correct if written like:
            #   self.done = True
            #   with self.lock:
            #       pass
            # because all we want is to force run_sync_soon
            # to either be completely before or completely after the write to
            # done. That's why we don't need the lock to protect
            # against signal handlers.
            with self.lock:
                self.done = True
            # No more jobs will be submitted, so just clear out any residual
            # ones:
            run_all_bounded()
            assert not self.queue
            assert not self.idempotent_queue

    def close(self) -> None:
        self.wakeup.close()

    def size(self) -> int:
        return len(self.queue) + len(self.idempotent_queue)

    def run_sync_soon(
        self,
        sync_fn: Callable[[Unpack[PosArgsT]], object],
        *args: Unpack[PosArgsT],
        idempotent: bool = False,
    ) -> None:
        with self.lock:
            if self.done:
                raise _core.RunFinishedError("run() has exited")
            # We have to hold the lock all the way through here, because
            # otherwise the main thread might exit *while* we're doing these
            # calls, and then our queue item might not be processed, or the
            # wakeup call might trigger an OSError b/c the IO manager has
            # already been shut down.
            if idempotent:
                self.idempotent_queue[sync_fn, args] = None
            else:
                self.queue.append((sync_fn, args))
            self.wakeup.wakeup_thread_and_signal_safe()


@final
@attrs.define(eq=False)
class TrioToken(metaclass=NoPublicConstructor):
    """An opaque object representing a single call to :func:`trio.run`.

    It has no public constructor; instead, see :func:`current_trio_token`.

    This object has two uses:

    1. It lets you re-enter the Trio run loop from external threads or signal
       handlers. This is the low-level primitive that :func:`trio.to_thread`
       and `trio.from_thread` use to communicate with worker threads, that
       `trio.open_signal_receiver` uses to receive notifications about
       signals, and so forth.

    2. Each call to :func:`trio.run` has exactly one associated
       :class:`TrioToken` object, so you can use it to identify a particular
       call.

    """

    _reentry_queue: EntryQueue

    def run_sync_soon(
        self,
        sync_fn: Callable[[Unpack[PosArgsT]], object],
        *args: Unpack[PosArgsT],
        idempotent: bool = False,
    ) -> None:
        """Schedule a call to ``sync_fn(*args)`` to occur in the context of a
        Trio task.

        This is safe to call from the main thread, from other threads, and
        from signal handlers. This is the fundamental primitive used to
        re-enter the Trio run loop from outside of it.

        The call will happen "soon", but there's no guarantee about exactly
        when, and no mechanism provided for finding out when it's happened.
        If you need this, you'll have to build your own.

        The call is effectively run as part of a system task (see
        :func:`~trio.lowlevel.spawn_system_task`). In particular this means
        that:

        * :exc:`KeyboardInterrupt` protection is *enabled* by default; if
          you want ``sync_fn`` to be interruptible by control-C, then you
          need to use :func:`~trio.lowlevel.disable_ki_protection`
          explicitly.

        * If ``sync_fn`` raises an exception, then it's converted into a
          :exc:`~trio.TrioInternalError` and *all* tasks are cancelled. You
          should be careful that ``sync_fn`` doesn't crash.

        All calls with ``idempotent=False`` are processed in strict
        first-in first-out order.

        If ``idempotent=True``, then ``sync_fn`` and ``args`` must be
        hashable, and Trio will make a best-effort attempt to discard any
        call submission which is equal to an already-pending call. Trio
        will process these in first-in first-out order.

        Any ordering guarantees apply separately to ``idempotent=False``
        and ``idempotent=True`` calls; there's no rule for how calls in the
        different categories are ordered with respect to each other.

        :raises trio.RunFinishedError:
              if the associated call to :func:`trio.run`
              has already exited. (Any call that *doesn't* raise this error
              is guaranteed to be fully processed before :func:`trio.run`
              exits.)

        """
        self._reentry_queue.run_sync_soon(sync_fn, *args, idempotent=idempotent)

# === NexusCore/openenv\Lib\site-packages\win32\test\testall.py ===
import os
import re
import sys
import traceback
import unittest

import pywin32_testutil

# A list of demos that depend on user-interface of *any* kind.  Tests listed
# here are not suitable for unattended testing.
ui_demos = """GetSaveFileName print_desktop win32cred_demo win32gui_demo
              win32gui_dialog win32gui_menu win32gui_taskbar
              win32rcparser_demo winprocess win32console_demo
              win32clipboard_bitmapdemo
              win32gui_devicenotify
              NetValidatePasswordPolicy""".split()
# Other demos known as 'bad' (or at least highly unlikely to work)
# desktopmanager: hangs (well, hangs for 60secs or so...)
# EvtSubscribe_*: must be run together:
# SystemParametersInfo: a couple of the params cause markh to hang, and there's
# no great reason to adjust (twice!) all those system settings!
bad_demos = """desktopmanager win32comport_demo
               EvtSubscribe_pull EvtSubscribe_push
               SystemParametersInfo
            """.split()

argvs = {
    "rastest": ("-l",),
}

no_user_interaction = True

# re to pull apart an exception line into the exception type and the args.
re_exception = re.compile(r"([a-zA-Z0-9_.]*): (.*)$")


def find_exception_in_output(data):
    have_traceback = False
    for line in data.splitlines():
        line = line.decode("ascii")  # not sure what the correct encoding is...
        if line.startswith("Traceback ("):
            have_traceback = True
            continue
        if line.startswith(" "):
            continue
        if have_traceback:
            # first line not starting with a space since the traceback.
            # must be the exception!
            m = re_exception.match(line)
            if m:
                exc_type, args = m.groups()
                # get hacky - get the *real* exception object from the name.
                bits = exc_type.split(".", 1)
                if len(bits) > 1:
                    mod = __import__(bits[0])
                    exc = getattr(mod, bits[1])
                else:
                    # probably builtin
                    exc = eval(bits[0])
            else:
                # hrm - probably just an exception with no args
                try:
                    exc = eval(line.strip())
                    args = "()"
                except:
                    return None
            # try and turn the args into real args.
            try:
                args = eval(args)
            except:
                pass
            if not isinstance(args, tuple):
                args = (args,)
            # try and instantiate the exception.
            try:
                ret = exc(*args)
            except:
                ret = None
            return ret
        # apparently not - keep looking...
        have_traceback = False


class TestRunner:
    def __init__(self, argv):
        self.argv = argv
        self.__name__ = f"Test Runner for cmdline {argv}"

    def __call__(self):
        import subprocess

        p = subprocess.Popen(
            self.argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        output, _ = p.communicate()
        rc = p.returncode

        if rc:
            base = os.path.basename(self.argv[1])
            # See if we can detect and reconstruct an exception in the output.
            reconstituted = find_exception_in_output(output)
            assert (
                reconstituted is not None
            ), f"{base} failed with exit code {rc}.  Output is:\n{output}"
            raise reconstituted


def get_demo_tests():
    import win32api

    ret = []
    demo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Demos"))
    assert os.path.isdir(demo_dir), demo_dir
    for name in os.listdir(demo_dir):
        base, ext = os.path.splitext(name)
        if base in ui_demos and no_user_interaction:
            continue
        # Skip any other files than .py and bad tests in any case
        if ext != ".py" or base in bad_demos:
            continue
        argv = (sys.executable, os.path.join(demo_dir, base + ".py")) + argvs.get(
            base, ()
        )
        ret.append(
            unittest.FunctionTestCase(
                TestRunner(argv), description="win32/demos/" + name
            )
        )
    return ret


def import_all():
    # Some hacks for import order - dde depends on win32ui
    try:
        import win32ui
    except ImportError:
        pass  # 'what-ev-a....'

    import win32api

    dir = os.path.dirname(win32api.__file__)
    num = 0
    is_debug = os.path.splitext(os.path.basename(win32api.__file__))[0].endswith("_d")
    for name in os.listdir(dir):
        base, ext = os.path.splitext(name)
        # handle `modname.cp310-win_amd64.pyd` etc
        base = base.split(".")[0]
        if (
            (ext == ".pyd")
            and name != "_winxptheme.pyd"
            and is_debug == base.endswith("_d")
        ):
            try:
                __import__(base)
            except:
                print("FAILED to import", name)
                raise
            num += 1


def suite():
    # Loop over all .py files here, except me :)
    try:
        me = __file__
    except NameError:
        me = sys.argv[0]
    me = os.path.abspath(me)
    files = os.listdir(os.path.dirname(me))
    suite = unittest.TestSuite()
    suite.addTest(unittest.FunctionTestCase(import_all))
    for file in files:
        base, ext = os.path.splitext(file)
        if ext == ".py" and os.path.basename(me) != file:
            try:
                mod = __import__(base)
            except:
                print("FAILED to import test module %r" % base)
                traceback.print_exc()
                continue
            if hasattr(mod, "suite"):
                test = mod.suite()
            else:
                test = unittest.defaultTestLoader.loadTestsFromModule(mod)
            suite.addTest(test)
    for test in get_demo_tests():
        suite.addTest(test)
    return suite


class CustomLoader(pywin32_testutil.TestLoader):
    def loadTestsFromModule(self, module):
        return self.fixupTestsForLeakTests(suite())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test runner for PyWin32/win32")
    parser.add_argument(
        "-no-user-interaction",
        default=False,
        action="store_true",
        help="(This is now the default - use `-user-interaction` to include them)",
    )

    parser.add_argument(
        "-user-interaction",
        action="store_true",
        help="Include tests which require user interaction",
    )

    parsed_args, remains = parser.parse_known_args()

    if parsed_args.no_user_interaction:
        print(
            "Note: -no-user-interaction is now the default, run with `-user-interaction` to include them."
        )

    no_user_interaction = not parsed_args.user_interaction

    sys.argv = [sys.argv[0]] + remains

    pywin32_testutil.testmain(testLoader=CustomLoader())

# === NexusCore/openenv\Lib\site-packages\win32comext\axscript\client\debug.py ===
import os
import sys

import pythoncom
import win32api
import winerror
from win32com.axdebug import adb, axdebug, documents, gateways
from win32com.axdebug.codecontainer import SourceCodeContainer
from win32com.axdebug.util import _wrap
from win32com.server.exception import COMException

debuggingTrace = "DEBUG_AXDEBUG" in os.environ  # Should we print "trace" output?


def trace(*args):
    """A function used instead of "print" for debugging output."""
    if not debuggingTrace:
        return
    print(win32api.GetCurrentThreadId(), end=" ")
    for arg in args:
        print(arg, end=" ")
    print()


# Note that the DebugManager is not a COM gateway class for the
# debugger - but it does create and manage them.
class DebugManager:
    _debugger_interfaces_ = [axdebug.IID_IActiveScriptDebug]

    def __init__(self, scriptEngine):
        self.scriptEngine = scriptEngine
        self.adb = adb.Debugger()
        self.rootNode = None
        self.debugApplication = None
        self.ccProvider = documents.CodeContainerProvider()
        try:
            self.scriptSiteDebug = scriptEngine.GetScriptSite(
                axdebug.IID_IActiveScriptSiteDebug
            )
        except pythoncom.com_error:
            # No debugger interface (ie, dumb host).  Do the extra work.
            trace("Scripting site has no debugger interface")
            self.scriptSiteDebug = None
        # Get the debug application object.
        self.debugApplication = None
        if self.scriptSiteDebug is not None:
            # Spec says that we should test for this, and if it fails revert to
            # PDM application.
            try:
                self.debugApplication = self.scriptSiteDebug.GetApplication()
                self.rootNode = self.scriptSiteDebug.GetRootApplicationNode()
            except pythoncom.com_error:
                self.debugApplication = None

        if self.debugApplication is None:
            # Try to get/create the default one
            # NOTE - Don't catch exceptions here - let the parent do it,
            # so it knows debug support is available.
            pdm = pythoncom.CoCreateInstance(
                axdebug.CLSID_ProcessDebugManager,
                None,
                pythoncom.CLSCTX_ALL,
                axdebug.IID_IProcessDebugManager,
            )
            self.debugApplication = pdm.GetDefaultApplication()
            self.rootNode = self.debugApplication.GetRootNode()

        assert (
            self.debugApplication is not None
        ), "Need to have a DebugApplication object by now!"
        self.activeScriptDebug = None

        if self.debugApplication is not None:
            self.adb.AttachApp(self.debugApplication, self.ccProvider)
        self.codeContainers = {}
        self.activeScriptDebug = _wrap(
            ActiveScriptDebug(self, self.codeContainers), axdebug.IID_IActiveScriptDebug
        )

    def Close(self):
        # Called by the language engine when it receives a close request
        self.activeScriptDebug = None
        self.scriptEngine = None
        self.rootNode = None
        self.debugApplication = None
        self.scriptSiteDebug = None
        if self.ccProvider is not None:
            self.ccProvider.Close()
            self.ccProvider = None
        self.codeContainers = {}
        if self.adb:
            self.adb.CloseApp()
            self.adb = None

    # print("Close complete")

    def IsAnyHost(self):
        "Do we have _any_ debugging interfaces installed?"
        return self.debugApplication is not None

    def IsSimpleHost(self):
        return self.scriptSiteDebug is None

    def HandleRuntimeError(self):
        """Called by the engine when a runtime error occurs.  If we have a debugger,
        we let it know.

        The result is a boolean which indicates if the error handler should call
        IActiveScriptSite::OnScriptError()
        """
        # 		if self.IsAnyHost:
        # 			site = _wrap(self, axdebug.IID_IActiveScriptSite)
        # 			breakResume, errorResume, fCallOnError = self.debugApplication(activeScriptErrorDebug, site)
        # Do something with these!
        # 		else:
        trace("HandleRuntimeError")
        fCallOnError = 1
        return fCallOnError

    def _query_interface_for_debugger_(self, iid):
        if iid in self._debugger_interfaces_:
            return self.activeScriptDebug
        trace("DebugManager QI - unknown IID", iid)
        return 0

    def OnEnterScript(self):
        trace("OnEnterScript")
        self.adb.SetupAXDebugging(sys._getframe().f_back)

    def OnLeaveScript(self):
        trace("OnLeaveScript")
        self.adb.ResetAXDebugging()

    def AddScriptBlock(self, codeBlock):
        # If we don't have debugging support, don't bother.
        cc = DebugCodeBlockContainer(codeBlock, self.scriptSiteDebug)
        if self.IsSimpleHost():
            document = documents.DebugDocumentText(cc)
            document = _wrap(document, axdebug.IID_IDebugDocument)
            provider = documents.DebugDocumentProvider(document)
            provider = _wrap(provider, axdebug.IID_IDebugDocumentProvider)
            cc.debugDocument = document
            newNode = self.debugApplication.CreateApplicationNode()
            newNode.SetDocumentProvider(provider)
            newNode.Attach(self.rootNode)
        else:
            newNode = None  # Managed by smart host.
            self.codeContainers[cc.sourceContext] = cc
        self.ccProvider.AddCodeContainer(cc, newNode)


class DebugCodeBlockContainer(SourceCodeContainer):
    def __init__(self, codeBlock, site):
        self.codeBlock = codeBlock
        SourceCodeContainer.__init__(
            self,
            codeBlock.codeText,
            codeBlock.GetFileName(),
            codeBlock.sourceContextCookie,
            codeBlock.startLineNumber,
            site,
        )

    def GetName(self, dnt):
        if dnt == axdebug.DOCUMENTNAMETYPE_APPNODE:
            return self.codeBlock.GetDisplayName()
        elif dnt == axdebug.DOCUMENTNAMETYPE_TITLE:
            return self.codeBlock.GetDisplayName()
        # 		elif dnt==axdebug.DOCUMENTNAMETYPE_FILE_TAIL:
        # 		elif dnt==axdebug.DOCUMENTNAMETYPE_URL:
        else:
            raise COMException(scode=winerror.S_FALSE)


class EnumDebugCodeContexts(gateways.EnumDebugCodeContexts):
    def _wrap(self, ob):
        return ob


class ActiveScriptDebug:
    """The class which implements the IActiveScriptDebug interface for the Active Script engine.

    Only ever used by smart hosts.
    """

    _public_methods_ = [
        "GetScriptTextAttributes",
        "GetScriptletTextAttributes",
        "EnumCodeContextsOfPosition",
    ]
    _com_interfaces_ = [axdebug.IID_IActiveScriptDebug]

    def __init__(self, debugMgr, codeContainers):
        self.debugMgr = debugMgr
        self.scriptSiteDebug = debugMgr.scriptSiteDebug
        self.codeContainers = codeContainers

    def _Close(self):
        self.debugMgr = None
        self.scriptSiteDebug = None
        self.codeContainers = {}

    def _query_interface_(self, iid):
        trace("DebuggerQI with", iid)
        return _wrap(self.debugMgr.scriptEngine, iid)

    def GetScriptTextAttributes(self, code, delim, flags):
        container = SourceCodeContainer(code, "<Temp Code Block>")
        return container.GetSyntaxColorAttributes()

    def GetScriptletTextAttributes(self, code, delim, flags):
        trace("GetScriptletTextAttributes", code, delim, flags)
        container = SourceCodeContainer(code, "<Temp Code Block>")
        return container.GetSyntaxColorAttributes()

    def EnumCodeContextsOfPosition(self, context, charOffset, numChars):
        trace("EnumCodeContextsOfPosition", context, charOffset, numChars)
        try:
            context = self.codeContainers[context].GetCodeContextAtPosition(charOffset)
        except KeyError:
            raise COMException(scode=winerror.E_UNEXPECTED)
        enum = EnumDebugCodeContexts([context])
        return _wrap(enum, axdebug.IID_IEnumDebugCodeContexts)

# === NexusCore/openenv\Lib\site-packages\grpc\_utilities.py ===
# Copyright 2015 gRPC authors.
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
"""Internal utilities for gRPC Python."""

import collections
import logging
import threading
import time
from typing import Callable, Dict, Optional, Sequence

import grpc  # pytype: disable=pyi-error
from grpc import _common  # pytype: disable=pyi-error
from grpc._typing import DoneCallbackType

_LOGGER = logging.getLogger(__name__)

_DONE_CALLBACK_EXCEPTION_LOG_MESSAGE = (
    'Exception calling connectivity future "done" callback!'
)


class RpcMethodHandler(
    collections.namedtuple(
        "_RpcMethodHandler",
        (
            "request_streaming",
            "response_streaming",
            "request_deserializer",
            "response_serializer",
            "unary_unary",
            "unary_stream",
            "stream_unary",
            "stream_stream",
        ),
    ),
    grpc.RpcMethodHandler,
):
    pass


class DictionaryGenericHandler(grpc.ServiceRpcHandler):
    _name: str
    _method_handlers: Dict[str, grpc.RpcMethodHandler]

    def __init__(
        self, service: str, method_handlers: Dict[str, grpc.RpcMethodHandler]
    ):
        self._name = service
        self._method_handlers = {
            _common.fully_qualified_method(service, method): method_handler
            for method, method_handler in method_handlers.items()
        }

    def service_name(self) -> str:
        return self._name

    def service(
        self, handler_call_details: grpc.HandlerCallDetails
    ) -> Optional[grpc.RpcMethodHandler]:
        details_method = handler_call_details.method
        return self._method_handlers.get(
            details_method
        )  # pytype: disable=attribute-error


class _ChannelReadyFuture(grpc.Future):
    _condition: threading.Condition
    _channel: grpc.Channel
    _matured: bool
    _cancelled: bool
    _done_callbacks: Sequence[Callable]

    def __init__(self, channel: grpc.Channel):
        self._condition = threading.Condition()
        self._channel = channel

        self._matured = False
        self._cancelled = False
        self._done_callbacks = []

    def _block(self, timeout: Optional[float]) -> None:
        until = None if timeout is None else time.time() + timeout
        with self._condition:
            while True:
                if self._cancelled:
                    raise grpc.FutureCancelledError()
                elif self._matured:
                    return
                else:
                    if until is None:
                        self._condition.wait()
                    else:
                        remaining = until - time.time()
                        if remaining < 0:
                            raise grpc.FutureTimeoutError()
                        else:
                            self._condition.wait(timeout=remaining)

    def _update(self, connectivity: Optional[grpc.ChannelConnectivity]) -> None:
        with self._condition:
            if (
                not self._cancelled
                and connectivity is grpc.ChannelConnectivity.READY
            ):
                self._matured = True
                self._channel.unsubscribe(self._update)
                self._condition.notify_all()
                done_callbacks = tuple(self._done_callbacks)
                self._done_callbacks = None
            else:
                return

        for done_callback in done_callbacks:
            try:
                done_callback(self)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception(_DONE_CALLBACK_EXCEPTION_LOG_MESSAGE)

    def cancel(self) -> bool:
        with self._condition:
            if not self._matured:
                self._cancelled = True
                self._channel.unsubscribe(self._update)
                self._condition.notify_all()
                done_callbacks = tuple(self._done_callbacks)
                self._done_callbacks = None
            else:
                return False

        for done_callback in done_callbacks:
            try:
                done_callback(self)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception(_DONE_CALLBACK_EXCEPTION_LOG_MESSAGE)

        return True

    def cancelled(self) -> bool:
        with self._condition:
            return self._cancelled

    def running(self) -> bool:
        with self._condition:
            return not self._cancelled and not self._matured

    def done(self) -> bool:
        with self._condition:
            return self._cancelled or self._matured

    def result(self, timeout: Optional[float] = None) -> None:
        self._block(timeout)

    def exception(self, timeout: Optional[float] = None) -> None:
        self._block(timeout)

    def traceback(self, timeout: Optional[float] = None) -> None:
        self._block(timeout)

    def add_done_callback(self, fn: DoneCallbackType):
        with self._condition:
            if not self._cancelled and not self._matured:
                self._done_callbacks.append(fn)
                return

        fn(self)

    def start(self):
        with self._condition:
            self._channel.subscribe(self._update, try_to_connect=True)

    def __del__(self):
        with self._condition:
            if not self._cancelled and not self._matured:
                self._channel.unsubscribe(self._update)


def channel_ready_future(channel: grpc.Channel) -> _ChannelReadyFuture:
    ready_future = _ChannelReadyFuture(channel)
    ready_future.start()
    return ready_future


def first_version_is_lower(version1: str, version2: str) -> bool:
    """
    Compares two versions in the format '1.60.1' or '1.60.1.dev0'.

    This method will be used in all stubs generated by grpcio-tools to check whether
    the stub version is compatible with the runtime grpcio.

    Args:
        version1: The first version string.
        version2: The second version string.

    Returns:
        True if version1 is lower, False otherwise.
    """
    version1_list = version1.split(".")
    version2_list = version2.split(".")

    try:
        for i in range(3):
            if int(version1_list[i]) < int(version2_list[i]):
                return True
            elif int(version1_list[i]) > int(version2_list[i]):
                return False
    except ValueError:
        # Return false in case we can't convert version to int.
        return False

    # The version without dev0 will be considered lower.
    return len(version1_list) < len(version2_list)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\keys.py ===
from __future__ import annotations

from enum import Enum

__all__ = [
    "Keys",
    "ALL_KEYS",
]


class Keys(str, Enum):
    """
    List of keys for use in key bindings.

    Note that this is an "StrEnum", all values can be compared against
    strings.
    """

    value: str

    Escape = "escape"  # Also Control-[
    ShiftEscape = "s-escape"

    ControlAt = "c-@"  # Also Control-Space.

    ControlA = "c-a"
    ControlB = "c-b"
    ControlC = "c-c"
    ControlD = "c-d"
    ControlE = "c-e"
    ControlF = "c-f"
    ControlG = "c-g"
    ControlH = "c-h"
    ControlI = "c-i"  # Tab
    ControlJ = "c-j"  # Newline
    ControlK = "c-k"
    ControlL = "c-l"
    ControlM = "c-m"  # Carriage return
    ControlN = "c-n"
    ControlO = "c-o"
    ControlP = "c-p"
    ControlQ = "c-q"
    ControlR = "c-r"
    ControlS = "c-s"
    ControlT = "c-t"
    ControlU = "c-u"
    ControlV = "c-v"
    ControlW = "c-w"
    ControlX = "c-x"
    ControlY = "c-y"
    ControlZ = "c-z"

    Control1 = "c-1"
    Control2 = "c-2"
    Control3 = "c-3"
    Control4 = "c-4"
    Control5 = "c-5"
    Control6 = "c-6"
    Control7 = "c-7"
    Control8 = "c-8"
    Control9 = "c-9"
    Control0 = "c-0"

    ControlShift1 = "c-s-1"
    ControlShift2 = "c-s-2"
    ControlShift3 = "c-s-3"
    ControlShift4 = "c-s-4"
    ControlShift5 = "c-s-5"
    ControlShift6 = "c-s-6"
    ControlShift7 = "c-s-7"
    ControlShift8 = "c-s-8"
    ControlShift9 = "c-s-9"
    ControlShift0 = "c-s-0"

    ControlBackslash = "c-\\"
    ControlSquareClose = "c-]"
    ControlCircumflex = "c-^"
    ControlUnderscore = "c-_"

    Left = "left"
    Right = "right"
    Up = "up"
    Down = "down"
    Home = "home"
    End = "end"
    Insert = "insert"
    Delete = "delete"
    PageUp = "pageup"
    PageDown = "pagedown"

    ControlLeft = "c-left"
    ControlRight = "c-right"
    ControlUp = "c-up"
    ControlDown = "c-down"
    ControlHome = "c-home"
    ControlEnd = "c-end"
    ControlInsert = "c-insert"
    ControlDelete = "c-delete"
    ControlPageUp = "c-pageup"
    ControlPageDown = "c-pagedown"

    ShiftLeft = "s-left"
    ShiftRight = "s-right"
    ShiftUp = "s-up"
    ShiftDown = "s-down"
    ShiftHome = "s-home"
    ShiftEnd = "s-end"
    ShiftInsert = "s-insert"
    ShiftDelete = "s-delete"
    ShiftPageUp = "s-pageup"
    ShiftPageDown = "s-pagedown"

    ControlShiftLeft = "c-s-left"
    ControlShiftRight = "c-s-right"
    ControlShiftUp = "c-s-up"
    ControlShiftDown = "c-s-down"
    ControlShiftHome = "c-s-home"
    ControlShiftEnd = "c-s-end"
    ControlShiftInsert = "c-s-insert"
    ControlShiftDelete = "c-s-delete"
    ControlShiftPageUp = "c-s-pageup"
    ControlShiftPageDown = "c-s-pagedown"

    BackTab = "s-tab"  # shift + tab

    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    F7 = "f7"
    F8 = "f8"
    F9 = "f9"
    F10 = "f10"
    F11 = "f11"
    F12 = "f12"
    F13 = "f13"
    F14 = "f14"
    F15 = "f15"
    F16 = "f16"
    F17 = "f17"
    F18 = "f18"
    F19 = "f19"
    F20 = "f20"
    F21 = "f21"
    F22 = "f22"
    F23 = "f23"
    F24 = "f24"

    ControlF1 = "c-f1"
    ControlF2 = "c-f2"
    ControlF3 = "c-f3"
    ControlF4 = "c-f4"
    ControlF5 = "c-f5"
    ControlF6 = "c-f6"
    ControlF7 = "c-f7"
    ControlF8 = "c-f8"
    ControlF9 = "c-f9"
    ControlF10 = "c-f10"
    ControlF11 = "c-f11"
    ControlF12 = "c-f12"
    ControlF13 = "c-f13"
    ControlF14 = "c-f14"
    ControlF15 = "c-f15"
    ControlF16 = "c-f16"
    ControlF17 = "c-f17"
    ControlF18 = "c-f18"
    ControlF19 = "c-f19"
    ControlF20 = "c-f20"
    ControlF21 = "c-f21"
    ControlF22 = "c-f22"
    ControlF23 = "c-f23"
    ControlF24 = "c-f24"

    # Matches any key.
    Any = "<any>"

    # Special.
    ScrollUp = "<scroll-up>"
    ScrollDown = "<scroll-down>"

    CPRResponse = "<cursor-position-response>"
    Vt100MouseEvent = "<vt100-mouse-event>"
    WindowsMouseEvent = "<windows-mouse-event>"
    BracketedPaste = "<bracketed-paste>"

    SIGINT = "<sigint>"

    # For internal use: key which is ignored.
    # (The key binding for this key should not do anything.)
    Ignore = "<ignore>"

    # Some 'Key' aliases (for backwards-compatibility).
    ControlSpace = ControlAt
    Tab = ControlI
    Enter = ControlM
    Backspace = ControlH

    # ShiftControl was renamed to ControlShift in
    # 888fcb6fa4efea0de8333177e1bbc792f3ff3c24 (20 Feb 2020).
    ShiftControlLeft = ControlShiftLeft
    ShiftControlRight = ControlShiftRight
    ShiftControlHome = ControlShiftHome
    ShiftControlEnd = ControlShiftEnd


ALL_KEYS: list[str] = [k.value for k in Keys]


# Aliases.
KEY_ALIASES: dict[str, str] = {
    "backspace": "c-h",
    "c-space": "c-@",
    "enter": "c-m",
    "tab": "c-i",
    # ShiftControl was renamed to ControlShift.
    "s-c-left": "c-s-left",
    "s-c-right": "c-s-right",
    "s-c-home": "c-s-home",
    "s-c-end": "c-s-end",
}

# === NexusCore/openenv\Lib\site-packages\smmap\util.py ===
"""Module containing a memory memory manager which provides a sliding window on a number of memory mapped files"""
import os
import sys

from mmap import mmap, ACCESS_READ
from mmap import ALLOCATIONGRANULARITY

__all__ = ["align_to_mmap", "is_64_bit",
           "MapWindow", "MapRegion", "MapRegionList", "ALLOCATIONGRANULARITY"]

#{ Utilities


def align_to_mmap(num, round_up):
    """
    Align the given integer number to the closest page offset, which usually is 4096 bytes.

    :param round_up: if True, the next higher multiple of page size is used, otherwise
        the lower page_size will be used (i.e. if True, 1 becomes 4096, otherwise it becomes 0)
    :return: num rounded to closest page"""
    res = (num // ALLOCATIONGRANULARITY) * ALLOCATIONGRANULARITY
    if round_up and (res != num):
        res += ALLOCATIONGRANULARITY
    # END handle size
    return res


def is_64_bit():
    """:return: True if the system is 64 bit. Otherwise it can be assumed to be 32 bit"""
    return sys.maxsize > (1 << 32) - 1

#}END utilities


#{ Utility Classes

class MapWindow:

    """Utility type which is used to snap windows towards each other, and to adjust their size"""
    __slots__ = (
        'ofs',      # offset into the file in bytes
        'size'              # size of the window in bytes
    )

    def __init__(self, offset, size):
        self.ofs = offset
        self.size = size

    def __repr__(self):
        return "MapWindow(%i, %i)" % (self.ofs, self.size)

    @classmethod
    def from_region(cls, region):
        """:return: new window from a region"""
        return cls(region._b, region.size())

    def ofs_end(self):
        return self.ofs + self.size

    def align(self):
        """Assures the previous window area is contained in the new one"""
        nofs = align_to_mmap(self.ofs, 0)
        self.size += self.ofs - nofs    # keep size constant
        self.ofs = nofs
        self.size = align_to_mmap(self.size, 1)

    def extend_left_to(self, window, max_size):
        """Adjust the offset to start where the given window on our left ends if possible,
        but don't make yourself larger than max_size.
        The resize will assure that the new window still contains the old window area"""
        rofs = self.ofs - window.ofs_end()
        nsize = rofs + self.size
        rofs -= nsize - min(nsize, max_size)
        self.ofs -= rofs
        self.size += rofs

    def extend_right_to(self, window, max_size):
        """Adjust the size to make our window end where the right window begins, but don't
        get larger than max_size"""
        self.size = min(self.size + (window.ofs - self.ofs_end()), max_size)


class MapRegion:

    """Defines a mapped region of memory, aligned to pagesizes

    **Note:** deallocates used region automatically on destruction"""
    __slots__ = [
        '_b',   # beginning of mapping
        '_mf',  # mapped memory chunk (as returned by mmap)
        '_uc',  # total amount of usages
        '_size',  # cached size of our memory map
        '__weakref__'
    ]

    #{ Configuration
    #} END configuration

    def __init__(self, path_or_fd, ofs, size, flags=0):
        """Initialize a region, allocate the memory map
        :param path_or_fd: path to the file to map, or the opened file descriptor
        :param ofs: **aligned** offset into the file to be mapped
        :param size: if size is larger then the file on disk, the whole file will be
            allocated the the size automatically adjusted
        :param flags: additional flags to be given when opening the file.
        :raise Exception: if no memory can be allocated"""
        self._b = ofs
        self._size = 0
        self._uc = 0

        if isinstance(path_or_fd, int):
            fd = path_or_fd
        else:
            fd = os.open(path_or_fd, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | flags)
        # END handle fd

        try:
            kwargs = dict(access=ACCESS_READ, offset=ofs)
            corrected_size = size
            sizeofs = ofs

            # have to correct size, otherwise (instead of the c version) it will
            # bark that the size is too large ... many extra file accesses because
            # if this ... argh !
            actual_size = min(os.fstat(fd).st_size - sizeofs, corrected_size)
            self._mf = mmap(fd, actual_size, **kwargs)
            # END handle memory mode

            self._size = len(self._mf)
        finally:
            if isinstance(path_or_fd, str):
                os.close(fd)
            # END only close it if we opened it
        # END close file handle
        # We assume the first one to use us keeps us around
        self.increment_client_count()

    def __repr__(self):
        return "MapRegion<%i, %i>" % (self._b, self.size())

    #{ Interface

    def buffer(self):
        """:return: a buffer containing the memory"""
        return self._mf

    def map(self):
        """:return: a memory map containing the memory"""
        return self._mf

    def ofs_begin(self):
        """:return: absolute byte offset to the first byte of the mapping"""
        return self._b

    def size(self):
        """:return: total size of the mapped region in bytes"""
        return self._size

    def ofs_end(self):
        """:return: Absolute offset to one byte beyond the mapping into the file"""
        return self._b + self._size

    def includes_ofs(self, ofs):
        """:return: True if the given offset can be read in our mapped region"""
        return self._b <= ofs < self._b + self._size

    def client_count(self):
        """:return: number of clients currently using this region"""
        return self._uc

    def increment_client_count(self, ofs = 1):
        """Adjust the usage count by the given positive or negative offset.
        If usage count equals 0, we will auto-release our resources
        :return: True if we released resources, False otherwise. In the latter case, we can still be used"""
        self._uc += ofs
        assert self._uc > -1, "Increments must match decrements, usage counter negative: %i" % self._uc

        if self.client_count() == 0:
            self.release()
            return True
        else:
            return False
        # end handle release

    def release(self):
        """Release all resources this instance might hold. Must only be called if there usage_count() is zero"""
        self._mf.close()

    #} END interface


class MapRegionList(list):

    """List of MapRegion instances associating a path with a list of regions."""
    __slots__ = (
        '_path_or_fd',  # path or file descriptor which is mapped by all our regions
        '_file_size'    # total size of the file we map
    )

    def __new__(cls, path):
        return super().__new__(cls)

    def __init__(self, path_or_fd):
        self._path_or_fd = path_or_fd
        self._file_size = None

    def path_or_fd(self):
        """:return: path or file descriptor we are attached to"""
        return self._path_or_fd

    def file_size(self):
        """:return: size of file we manager"""
        if self._file_size is None:
            if isinstance(self._path_or_fd, str):
                self._file_size = os.stat(self._path_or_fd).st_size
            else:
                self._file_size = os.fstat(self._path_or_fd).st_size
            # END handle path type
        # END update file size
        return self._file_size

#} END utility classes

# === NexusCore/openenv\Lib\site-packages\httpcore\_async\connection.py ===
from __future__ import annotations

import itertools
import logging
import ssl
import types
import typing

from .._backends.auto import AutoBackend
from .._backends.base import SOCKET_OPTION, AsyncNetworkBackend, AsyncNetworkStream
from .._exceptions import ConnectError, ConnectTimeout
from .._models import Origin, Request, Response
from .._ssl import default_ssl_context
from .._synchronization import AsyncLock
from .._trace import Trace
from .http11 import AsyncHTTP11Connection
from .interfaces import AsyncConnectionInterface

RETRIES_BACKOFF_FACTOR = 0.5  # 0s, 0.5s, 1s, 2s, 4s, etc.


logger = logging.getLogger("httpcore.connection")


def exponential_backoff(factor: float) -> typing.Iterator[float]:
    """
    Generate a geometric sequence that has a ratio of 2 and starts with 0.

    For example:
    - `factor = 2`: `0, 2, 4, 8, 16, 32, 64, ...`
    - `factor = 3`: `0, 3, 6, 12, 24, 48, 96, ...`
    """
    yield 0
    for n in itertools.count():
        yield factor * 2**n


class AsyncHTTPConnection(AsyncConnectionInterface):
    def __init__(
        self,
        origin: Origin,
        ssl_context: ssl.SSLContext | None = None,
        keepalive_expiry: float | None = None,
        http1: bool = True,
        http2: bool = False,
        retries: int = 0,
        local_address: str | None = None,
        uds: str | None = None,
        network_backend: AsyncNetworkBackend | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> None:
        self._origin = origin
        self._ssl_context = ssl_context
        self._keepalive_expiry = keepalive_expiry
        self._http1 = http1
        self._http2 = http2
        self._retries = retries
        self._local_address = local_address
        self._uds = uds

        self._network_backend: AsyncNetworkBackend = (
            AutoBackend() if network_backend is None else network_backend
        )
        self._connection: AsyncConnectionInterface | None = None
        self._connect_failed: bool = False
        self._request_lock = AsyncLock()
        self._socket_options = socket_options

    async def handle_async_request(self, request: Request) -> Response:
        if not self.can_handle_request(request.url.origin):
            raise RuntimeError(
                f"Attempted to send request to {request.url.origin} on connection to {self._origin}"
            )

        try:
            async with self._request_lock:
                if self._connection is None:
                    stream = await self._connect(request)

                    ssl_object = stream.get_extra_info("ssl_object")
                    http2_negotiated = (
                        ssl_object is not None
                        and ssl_object.selected_alpn_protocol() == "h2"
                    )
                    if http2_negotiated or (self._http2 and not self._http1):
                        from .http2 import AsyncHTTP2Connection

                        self._connection = AsyncHTTP2Connection(
                            origin=self._origin,
                            stream=stream,
                            keepalive_expiry=self._keepalive_expiry,
                        )
                    else:
                        self._connection = AsyncHTTP11Connection(
                            origin=self._origin,
                            stream=stream,
                            keepalive_expiry=self._keepalive_expiry,
                        )
        except BaseException as exc:
            self._connect_failed = True
            raise exc

        return await self._connection.handle_async_request(request)

    async def _connect(self, request: Request) -> AsyncNetworkStream:
        timeouts = request.extensions.get("timeout", {})
        sni_hostname = request.extensions.get("sni_hostname", None)
        timeout = timeouts.get("connect", None)

        retries_left = self._retries
        delays = exponential_backoff(factor=RETRIES_BACKOFF_FACTOR)

        while True:
            try:
                if self._uds is None:
                    kwargs = {
                        "host": self._origin.host.decode("ascii"),
                        "port": self._origin.port,
                        "local_address": self._local_address,
                        "timeout": timeout,
                        "socket_options": self._socket_options,
                    }
                    async with Trace("connect_tcp", logger, request, kwargs) as trace:
                        stream = await self._network_backend.connect_tcp(**kwargs)
                        trace.return_value = stream
                else:
                    kwargs = {
                        "path": self._uds,
                        "timeout": timeout,
                        "socket_options": self._socket_options,
                    }
                    async with Trace(
                        "connect_unix_socket", logger, request, kwargs
                    ) as trace:
                        stream = await self._network_backend.connect_unix_socket(
                            **kwargs
                        )
                        trace.return_value = stream

                if self._origin.scheme in (b"https", b"wss"):
                    ssl_context = (
                        default_ssl_context()
                        if self._ssl_context is None
                        else self._ssl_context
                    )
                    alpn_protocols = ["http/1.1", "h2"] if self._http2 else ["http/1.1"]
                    ssl_context.set_alpn_protocols(alpn_protocols)

                    kwargs = {
                        "ssl_context": ssl_context,
                        "server_hostname": sni_hostname
                        or self._origin.host.decode("ascii"),
                        "timeout": timeout,
                    }
                    async with Trace("start_tls", logger, request, kwargs) as trace:
                        stream = await stream.start_tls(**kwargs)
                        trace.return_value = stream
                return stream
            except (ConnectError, ConnectTimeout):
                if retries_left <= 0:
                    raise
                retries_left -= 1
                delay = next(delays)
                async with Trace("retry", logger, request, kwargs) as trace:
                    await self._network_backend.sleep(delay)

    def can_handle_request(self, origin: Origin) -> bool:
        return origin == self._origin

    async def aclose(self) -> None:
        if self._connection is not None:
            async with Trace("close", logger, None, {}):
                await self._connection.aclose()

    def is_available(self) -> bool:
        if self._connection is None:
            # If HTTP/2 support is enabled, and the resulting connection could
            # end up as HTTP/2 then we should indicate the connection as being
            # available to service multiple requests.
            return (
                self._http2
                and (self._origin.scheme == b"https" or not self._http1)
                and not self._connect_failed
            )
        return self._connection.is_available()

    def has_expired(self) -> bool:
        if self._connection is None:
            return self._connect_failed
        return self._connection.has_expired()

    def is_idle(self) -> bool:
        if self._connection is None:
            return self._connect_failed
        return self._connection.is_idle()

    def is_closed(self) -> bool:
        if self._connection is None:
            return self._connect_failed
        return self._connection.is_closed()

    def info(self) -> str:
        if self._connection is None:
            return "CONNECTION FAILED" if self._connect_failed else "CONNECTING"
        return self._connection.info()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} [{self.info()}]>"

    # These context managers are not used in the standard flow, but are
    # useful for testing or working with connection instances directly.

    async def __aenter__(self) -> AsyncHTTPConnection:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        await self.aclose()

# === NexusCore/openenv\Lib\site-packages\httpcore\_sync\connection.py ===
from __future__ import annotations

import itertools
import logging
import ssl
import types
import typing

from .._backends.sync import SyncBackend
from .._backends.base import SOCKET_OPTION, NetworkBackend, NetworkStream
from .._exceptions import ConnectError, ConnectTimeout
from .._models import Origin, Request, Response
from .._ssl import default_ssl_context
from .._synchronization import Lock
from .._trace import Trace
from .http11 import HTTP11Connection
from .interfaces import ConnectionInterface

RETRIES_BACKOFF_FACTOR = 0.5  # 0s, 0.5s, 1s, 2s, 4s, etc.


logger = logging.getLogger("httpcore.connection")


def exponential_backoff(factor: float) -> typing.Iterator[float]:
    """
    Generate a geometric sequence that has a ratio of 2 and starts with 0.

    For example:
    - `factor = 2`: `0, 2, 4, 8, 16, 32, 64, ...`
    - `factor = 3`: `0, 3, 6, 12, 24, 48, 96, ...`
    """
    yield 0
    for n in itertools.count():
        yield factor * 2**n


class HTTPConnection(ConnectionInterface):
    def __init__(
        self,
        origin: Origin,
        ssl_context: ssl.SSLContext | None = None,
        keepalive_expiry: float | None = None,
        http1: bool = True,
        http2: bool = False,
        retries: int = 0,
        local_address: str | None = None,
        uds: str | None = None,
        network_backend: NetworkBackend | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> None:
        self._origin = origin
        self._ssl_context = ssl_context
        self._keepalive_expiry = keepalive_expiry
        self._http1 = http1
        self._http2 = http2
        self._retries = retries
        self._local_address = local_address
        self._uds = uds

        self._network_backend: NetworkBackend = (
            SyncBackend() if network_backend is None else network_backend
        )
        self._connection: ConnectionInterface | None = None
        self._connect_failed: bool = False
        self._request_lock = Lock()
        self._socket_options = socket_options

    def handle_request(self, request: Request) -> Response:
        if not self.can_handle_request(request.url.origin):
            raise RuntimeError(
                f"Attempted to send request to {request.url.origin} on connection to {self._origin}"
            )

        try:
            with self._request_lock:
                if self._connection is None:
                    stream = self._connect(request)

                    ssl_object = stream.get_extra_info("ssl_object")
                    http2_negotiated = (
                        ssl_object is not None
                        and ssl_object.selected_alpn_protocol() == "h2"
                    )
                    if http2_negotiated or (self._http2 and not self._http1):
                        from .http2 import HTTP2Connection

                        self._connection = HTTP2Connection(
                            origin=self._origin,
                            stream=stream,
                            keepalive_expiry=self._keepalive_expiry,
                        )
                    else:
                        self._connection = HTTP11Connection(
                            origin=self._origin,
                            stream=stream,
                            keepalive_expiry=self._keepalive_expiry,
                        )
        except BaseException as exc:
            self._connect_failed = True
            raise exc

        return self._connection.handle_request(request)

    def _connect(self, request: Request) -> NetworkStream:
        timeouts = request.extensions.get("timeout", {})
        sni_hostname = request.extensions.get("sni_hostname", None)
        timeout = timeouts.get("connect", None)

        retries_left = self._retries
        delays = exponential_backoff(factor=RETRIES_BACKOFF_FACTOR)

        while True:
            try:
                if self._uds is None:
                    kwargs = {
                        "host": self._origin.host.decode("ascii"),
                        "port": self._origin.port,
                        "local_address": self._local_address,
                        "timeout": timeout,
                        "socket_options": self._socket_options,
                    }
                    with Trace("connect_tcp", logger, request, kwargs) as trace:
                        stream = self._network_backend.connect_tcp(**kwargs)
                        trace.return_value = stream
                else:
                    kwargs = {
                        "path": self._uds,
                        "timeout": timeout,
                        "socket_options": self._socket_options,
                    }
                    with Trace(
                        "connect_unix_socket", logger, request, kwargs
                    ) as trace:
                        stream = self._network_backend.connect_unix_socket(
                            **kwargs
                        )
                        trace.return_value = stream

                if self._origin.scheme in (b"https", b"wss"):
                    ssl_context = (
                        default_ssl_context()
                        if self._ssl_context is None
                        else self._ssl_context
                    )
                    alpn_protocols = ["http/1.1", "h2"] if self._http2 else ["http/1.1"]
                    ssl_context.set_alpn_protocols(alpn_protocols)

                    kwargs = {
                        "ssl_context": ssl_context,
                        "server_hostname": sni_hostname
                        or self._origin.host.decode("ascii"),
                        "timeout": timeout,
                    }
                    with Trace("start_tls", logger, request, kwargs) as trace:
                        stream = stream.start_tls(**kwargs)
                        trace.return_value = stream
                return stream
            except (ConnectError, ConnectTimeout):
                if retries_left <= 0:
                    raise
                retries_left -= 1
                delay = next(delays)
                with Trace("retry", logger, request, kwargs) as trace:
                    self._network_backend.sleep(delay)

    def can_handle_request(self, origin: Origin) -> bool:
        return origin == self._origin

    def close(self) -> None:
        if self._connection is not None:
            with Trace("close", logger, None, {}):
                self._connection.close()

    def is_available(self) -> bool:
        if self._connection is None:
            # If HTTP/2 support is enabled, and the resulting connection could
            # end up as HTTP/2 then we should indicate the connection as being
            # available to service multiple requests.
            return (
                self._http2
                and (self._origin.scheme == b"https" or not self._http1)
                and not self._connect_failed
            )
        return self._connection.is_available()

    def has_expired(self) -> bool:
        if self._connection is None:
            return self._connect_failed
        return self._connection.has_expired()

    def is_idle(self) -> bool:
        if self._connection is None:
            return self._connect_failed
        return self._connection.is_idle()

    def is_closed(self) -> bool:
        if self._connection is None:
            return self._connect_failed
        return self._connection.is_closed()

    def info(self) -> str:
        if self._connection is None:
            return "CONNECTION FAILED" if self._connect_failed else "CONNECTING"
        return self._connection.info()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} [{self.info()}]>"

    # These context managers are not used in the standard flow, but are
    # useful for testing or working with connection instances directly.

    def __enter__(self) -> HTTPConnection:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        self.close()

# === NexusCore/openenv\Lib\site-packages\nltk\metrics\segmentation.py ===
# Natural Language Toolkit: Text Segmentation Metrics
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
#         David Doukhan <david.doukhan@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT


"""
Text Segmentation Metrics

1. Windowdiff

Pevzner, L., and Hearst, M., A Critique and Improvement of
  an Evaluation Metric for Text Segmentation,
  Computational Linguistics 28, 19-36


2. Generalized Hamming Distance

Bookstein A., Kulyukin V.A., Raita T.
Generalized Hamming Distance
Information Retrieval 5, 2002, pp 353-375

Baseline implementation in C++
http://digital.cs.usu.edu/~vkulyukin/vkweb/software/ghd/ghd.html

Study describing benefits of Generalized Hamming Distance Versus
WindowDiff for evaluating text segmentation tasks
Begsten, Y.  Quel indice pour mesurer l'efficacite en segmentation de textes ?
TALN 2009


3. Pk text segmentation metric

Beeferman D., Berger A., Lafferty J. (1999)
Statistical Models for Text Segmentation
Machine Learning, 34, 177-210
"""

try:
    import numpy as np
except ImportError:
    pass


def windowdiff(seg1, seg2, k, boundary="1", weighted=False):
    """
    Compute the windowdiff score for a pair of segmentations.  A
    segmentation is any sequence over a vocabulary of two items
    (e.g. "0", "1"), where the specified boundary value is used to
    mark the edge of a segmentation.

        >>> s1 = "000100000010"
        >>> s2 = "000010000100"
        >>> s3 = "100000010000"
        >>> '%.2f' % windowdiff(s1, s1, 3)
        '0.00'
        >>> '%.2f' % windowdiff(s1, s2, 3)
        '0.30'
        >>> '%.2f' % windowdiff(s2, s3, 3)
        '0.80'

    :param seg1: a segmentation
    :type seg1: str or list
    :param seg2: a segmentation
    :type seg2: str or list
    :param k: window width
    :type k: int
    :param boundary: boundary value
    :type boundary: str or int or bool
    :param weighted: use the weighted variant of windowdiff
    :type weighted: boolean
    :rtype: float
    """

    if len(seg1) != len(seg2):
        raise ValueError("Segmentations have unequal length")
    if k > len(seg1):
        raise ValueError(
            "Window width k should be smaller or equal than segmentation lengths"
        )
    wd = 0
    for i in range(len(seg1) - k + 1):
        ndiff = abs(seg1[i : i + k].count(boundary) - seg2[i : i + k].count(boundary))
        if weighted:
            wd += ndiff
        else:
            wd += min(1, ndiff)
    return wd / (len(seg1) - k + 1.0)


# Generalized Hamming Distance


def _init_mat(nrows, ncols, ins_cost, del_cost):
    mat = np.empty((nrows, ncols))
    mat[0, :] = ins_cost * np.arange(ncols)
    mat[:, 0] = del_cost * np.arange(nrows)
    return mat


def _ghd_aux(mat, rowv, colv, ins_cost, del_cost, shift_cost_coeff):
    for i, rowi in enumerate(rowv):
        for j, colj in enumerate(colv):
            shift_cost = shift_cost_coeff * abs(rowi - colj) + mat[i, j]
            if rowi == colj:
                # boundaries are at the same location, no transformation required
                tcost = mat[i, j]
            elif rowi > colj:
                # boundary match through a deletion
                tcost = del_cost + mat[i, j + 1]
            else:
                # boundary match through an insertion
                tcost = ins_cost + mat[i + 1, j]
            mat[i + 1, j + 1] = min(tcost, shift_cost)


def ghd(ref, hyp, ins_cost=2.0, del_cost=2.0, shift_cost_coeff=1.0, boundary="1"):
    """
    Compute the Generalized Hamming Distance for a reference and a hypothetical
    segmentation, corresponding to the cost related to the transformation
    of the hypothetical segmentation into the reference segmentation
    through boundary insertion, deletion and shift operations.

    A segmentation is any sequence over a vocabulary of two items
    (e.g. "0", "1"), where the specified boundary value is used to
    mark the edge of a segmentation.

    Recommended parameter values are a shift_cost_coeff of 2.
    Associated with a ins_cost, and del_cost equal to the mean segment
    length in the reference segmentation.

        >>> # Same examples as Kulyukin C++ implementation
        >>> ghd('1100100000', '1100010000', 1.0, 1.0, 0.5)
        0.5
        >>> ghd('1100100000', '1100000001', 1.0, 1.0, 0.5)
        2.0
        >>> ghd('011', '110', 1.0, 1.0, 0.5)
        1.0
        >>> ghd('1', '0', 1.0, 1.0, 0.5)
        1.0
        >>> ghd('111', '000', 1.0, 1.0, 0.5)
        3.0
        >>> ghd('000', '111', 1.0, 2.0, 0.5)
        6.0

    :param ref: the reference segmentation
    :type ref: str or list
    :param hyp: the hypothetical segmentation
    :type hyp: str or list
    :param ins_cost: insertion cost
    :type ins_cost: float
    :param del_cost: deletion cost
    :type del_cost: float
    :param shift_cost_coeff: constant used to compute the cost of a shift.
        ``shift cost = shift_cost_coeff * |i - j|`` where ``i`` and ``j``
        are the positions indicating the shift
    :type shift_cost_coeff: float
    :param boundary: boundary value
    :type boundary: str or int or bool
    :rtype: float
    """

    ref_idx = [i for (i, val) in enumerate(ref) if val == boundary]
    hyp_idx = [i for (i, val) in enumerate(hyp) if val == boundary]

    nref_bound = len(ref_idx)
    nhyp_bound = len(hyp_idx)

    if nref_bound == 0 and nhyp_bound == 0:
        return 0.0
    elif nref_bound > 0 and nhyp_bound == 0:
        return nref_bound * ins_cost
    elif nref_bound == 0 and nhyp_bound > 0:
        return nhyp_bound * del_cost

    mat = _init_mat(nhyp_bound + 1, nref_bound + 1, ins_cost, del_cost)
    _ghd_aux(mat, hyp_idx, ref_idx, ins_cost, del_cost, shift_cost_coeff)
    return float(mat[-1, -1])


# Beeferman's Pk text segmentation evaluation metric


def pk(ref, hyp, k=None, boundary="1"):
    """
    Compute the Pk metric for a pair of segmentations A segmentation
    is any sequence over a vocabulary of two items (e.g. "0", "1"),
    where the specified boundary value is used to mark the edge of a
    segmentation.

    >>> '%.2f' % pk('0100'*100, '1'*400, 2)
    '0.50'
    >>> '%.2f' % pk('0100'*100, '0'*400, 2)
    '0.50'
    >>> '%.2f' % pk('0100'*100, '0100'*100, 2)
    '0.00'

    :param ref: the reference segmentation
    :type ref: str or list
    :param hyp: the segmentation to evaluate
    :type hyp: str or list
    :param k: window size, if None, set to half of the average reference segment length
    :type boundary: str or int or bool
    :param boundary: boundary value
    :type boundary: str or int or bool
    :rtype: float
    """

    if k is None:
        k = int(round(len(ref) / (ref.count(boundary) * 2.0)))

    err = 0
    for i in range(len(ref) - k + 1):
        r = ref[i : i + k].count(boundary) > 0
        h = hyp[i : i + k].count(boundary) > 0
        if r != h:
            err += 1
    return err / (len(ref) - k + 1.0)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\rust.py ===
"""
    pygments.lexers.rust
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for the Rust language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, bygroups, words, default
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace

__all__ = ['RustLexer']


class RustLexer(RegexLexer):
    """
    Lexer for the Rust programming language (version 1.47).
    """
    name = 'Rust'
    url = 'https://www.rust-lang.org/'
    filenames = ['*.rs', '*.rs.in']
    aliases = ['rust', 'rs']
    mimetypes = ['text/rust', 'text/x-rust']
    version_added = '1.6'

    keyword_types = (words((
        'u8', 'u16', 'u32', 'u64', 'u128', 'i8', 'i16', 'i32', 'i64', 'i128',
        'usize', 'isize', 'f32', 'f64', 'char', 'str', 'bool',
    ), suffix=r'\b'), Keyword.Type)

    builtin_funcs_types = (words((
        'Copy', 'Send', 'Sized', 'Sync', 'Unpin',
        'Drop', 'Fn', 'FnMut', 'FnOnce', 'drop',
        'Box', 'ToOwned', 'Clone',
        'PartialEq', 'PartialOrd', 'Eq', 'Ord',
        'AsRef', 'AsMut', 'Into', 'From', 'Default',
        'Iterator', 'Extend', 'IntoIterator', 'DoubleEndedIterator',
        'ExactSizeIterator',
        'Option', 'Some', 'None',
        'Result', 'Ok', 'Err',
        'String', 'ToString', 'Vec',
    ), suffix=r'\b'), Name.Builtin)

    builtin_macros = (words((
        'asm', 'assert', 'assert_eq', 'assert_ne', 'cfg', 'column',
        'compile_error', 'concat', 'concat_idents', 'dbg', 'debug_assert',
        'debug_assert_eq', 'debug_assert_ne', 'env', 'eprint', 'eprintln',
        'file', 'format', 'format_args', 'format_args_nl', 'global_asm',
        'include', 'include_bytes', 'include_str',
        'is_aarch64_feature_detected',
        'is_arm_feature_detected',
        'is_mips64_feature_detected',
        'is_mips_feature_detected',
        'is_powerpc64_feature_detected',
        'is_powerpc_feature_detected',
        'is_x86_feature_detected',
        'line', 'llvm_asm', 'log_syntax', 'macro_rules', 'matches',
        'module_path', 'option_env', 'panic', 'print', 'println', 'stringify',
        'thread_local', 'todo', 'trace_macros', 'unimplemented', 'unreachable',
        'vec', 'write', 'writeln',
    ), suffix=r'!'), Name.Function.Magic)

    tokens = {
        'root': [
            # rust allows a file to start with a shebang, but if the first line
            # starts with #![ then it's not a shebang but a crate attribute.
            (r'#![^[\r\n].*$', Comment.Preproc),
            default('base'),
        ],
        'base': [
            # Whitespace and Comments
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
            (r'//!.*?\n', String.Doc),
            (r'///(\n|[^/].*?\n)', String.Doc),
            (r'//(.*?)\n', Comment.Single),
            (r'/\*\*(\n|[^/*])', String.Doc, 'doccomment'),
            (r'/\*!', String.Doc, 'doccomment'),
            (r'/\*', Comment.Multiline, 'comment'),

            # Macro parameters
            (r"""\$([a-zA-Z_]\w*|\(,?|\),?|,?)""", Comment.Preproc),
            # Keywords
            (words(('as', 'async', 'await', 'box', 'const', 'crate', 'dyn',
                    'else', 'extern', 'for', 'if', 'impl', 'in', 'loop',
                    'match', 'move', 'mut', 'pub', 'ref', 'return', 'static',
                    'super', 'trait', 'unsafe', 'use', 'where', 'while'),
                   suffix=r'\b'), Keyword),
            (words(('abstract', 'become', 'do', 'final', 'macro', 'override',
                    'priv', 'typeof', 'try', 'unsized', 'virtual', 'yield'),
                   suffix=r'\b'), Keyword.Reserved),
            (r'(true|false)\b', Keyword.Constant),
            (r'self\b', Name.Builtin.Pseudo),
            (r'mod\b', Keyword, 'modname'),
            (r'let\b', Keyword.Declaration),
            (r'fn\b', Keyword, 'funcname'),
            (r'(struct|enum|type|union)\b', Keyword, 'typename'),
            (r'(default)(\s+)(type|fn)\b', bygroups(Keyword, Whitespace, Keyword)),
            keyword_types,
            (r'[sS]elf\b', Name.Builtin.Pseudo),
            # Prelude (taken from Rust's src/libstd/prelude.rs)
            builtin_funcs_types,
            builtin_macros,
            # Path separators, so types don't catch them.
            (r'::\b', Punctuation),
            # Types in positions.
            (r'(?::|->)', Punctuation, 'typename'),
            # Labels
            (r'(break|continue)(\b\s*)(\'[A-Za-z_]\w*)?',
             bygroups(Keyword, Text.Whitespace, Name.Label)),

            # Character literals
            (r"""'(\\['"\\nrt]|\\x[0-7][0-9a-fA-F]|\\0"""
             r"""|\\u\{[0-9a-fA-F]{1,6}\}|.)'""",
             String.Char),
            (r"""b'(\\['"\\nrt]|\\x[0-9a-fA-F]{2}|\\0"""
             r"""|\\u\{[0-9a-fA-F]{1,6}\}|.)'""",
             String.Char),

            # Binary literals
            (r'0b[01_]+', Number.Bin, 'number_lit'),
            # Octal literals
            (r'0o[0-7_]+', Number.Oct, 'number_lit'),
            # Hexadecimal literals
            (r'0[xX][0-9a-fA-F_]+', Number.Hex, 'number_lit'),
            # Decimal literals
            (r'[0-9][0-9_]*(\.[0-9_]+[eE][+\-]?[0-9_]+|'
             r'\.[0-9_]*(?!\.)|[eE][+\-]?[0-9_]+)', Number.Float,
             'number_lit'),
            (r'[0-9][0-9_]*', Number.Integer, 'number_lit'),

            # String literals
            (r'b"', String, 'bytestring'),
            (r'"', String, 'string'),
            (r'(?s)b?r(#*)".*?"\1', String),

            # Lifetime names
            (r"'", Operator, 'lifetime'),

            # Operators and Punctuation
            (r'\.\.=?', Operator),
            (r'[{}()\[\],.;]', Punctuation),
            (r'[+\-*/%&|<>^!~@=:?]', Operator),

            # Identifiers
            (r'[a-zA-Z_]\w*', Name),
            # Raw identifiers
            (r'r#[a-zA-Z_]\w*', Name),

            # Attributes
            (r'#!?\[', Comment.Preproc, 'attribute['),

            # Misc
            # Lone hashes: not used in Rust syntax, but allowed in macro
            # arguments, most famously for quote::quote!()
            (r'#', Punctuation),
        ],
        'comment': [
            (r'[^*/]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline),
        ],
        'doccomment': [
            (r'[^*/]+', String.Doc),
            (r'/\*', String.Doc, '#push'),
            (r'\*/', String.Doc, '#pop'),
            (r'[*/]', String.Doc),
        ],
        'modname': [
            (r'\s+', Whitespace),
            (r'[a-zA-Z_]\w*', Name.Namespace, '#pop'),
            default('#pop'),
        ],
        'funcname': [
            (r'\s+', Whitespace),
            (r'[a-zA-Z_]\w*', Name.Function, '#pop'),
            default('#pop'),
        ],
        'typename': [
            (r'\s+', Whitespace),
            (r'&', Keyword.Pseudo),
            (r"'", Operator, 'lifetime'),
            builtin_funcs_types,
            keyword_types,
            (r'[a-zA-Z_]\w*', Name.Class, '#pop'),
            default('#pop'),
        ],
        'lifetime': [
            (r"(static|_)", Name.Builtin),
            (r"[a-zA-Z_]+\w*", Name.Attribute),
            default('#pop'),
        ],
        'number_lit': [
            (r'[ui](8|16|32|64|size)', Keyword, '#pop'),
            (r'f(32|64)', Keyword, '#pop'),
            default('#pop'),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r"""\\['"\\nrt]|\\x[0-7][0-9a-fA-F]|\\0"""
             r"""|\\u\{[0-9a-fA-F]{1,6}\}""", String.Escape),
            (r'[^\\"]+', String),
            (r'\\', String),
        ],
        'bytestring': [
            (r"""\\x[89a-fA-F][0-9a-fA-F]""", String.Escape),
            include('string'),
        ],
        'attribute_common': [
            (r'"', String, 'string'),
            (r'\[', Comment.Preproc, 'attribute['),
        ],
        'attribute[': [
            include('attribute_common'),
            (r'\]', Comment.Preproc, '#pop'),
            (r'[^"\]\[]+', Comment.Preproc),
        ],
    }

# === NexusCore/evaluation\evalplus\tools\mbpp\fix_v010.py ===
def check_id(data, n, task_id):
    assert data[n]["task_id"] == task_id


def fix(data):
    # fix: https://github.com/evalplus/evalplus/issues/156

    check_id(data, 334, "Mbpp/734")
    data[334]["prompt"] = data[334]["prompt"].replace(
        "https://www.geeksforgeeks.org/sum-of-products-of-all-possible-subarrays/", ""
    )

    check_id(data, 335, "Mbpp/735")
    data[335]["prompt"] = data[335]["prompt"].replace(
        "https://www.geeksforgeeks.org/toggle-bits-number-expect-first-last-bits/", ""
    )

    check_id(data, 336, "Mbpp/736")
    data[336]["prompt"] = data[336]["prompt"].replace(
        "https://www.w3resource.com/python-exercises/data-structures-and-algorithms/python-data-structure-exercise-24.php",
        "",
    )

    check_id(data, 338, "Mbpp/739")
    data[338]["prompt"] = data[338]["prompt"].replace(
        "https://www.geeksforgeeks.org/index-of-smallest-triangular-number-with-n-digits/",
        "",
    )

    check_id(data, 339, "Mbpp/740")
    data[339]["prompt"] = data[339]["prompt"].replace(
        "https://www.geeksforgeeks.org/python-convert-tuple-to-adjacent-pair-dictionary/",
        "",
    )

    check_id(data, 342, "Mbpp/743")
    data[342]["prompt"] = data[342]["prompt"].replace(
        "https://www.geeksforgeeks.org/python-program-right-rotate-list-n/", ""
    )

    check_id(data, 344, "Mbpp/745")
    data[344]["prompt"] = data[344]["prompt"].replace(
        "https://www.w3resource.com/python-exercises/lambda/python-lambda-exercise-24.php",
        "",
    )

    check_id(data, 347, "Mbpp/749")
    data[347]["prompt"] = data[347]["prompt"].replace(
        "https://www.geeksforgeeks.org/python-sort-numeric-strings-in-a-list/", ""
    )

    check_id(data, 349, "Mbpp/751")
    data[349]["prompt"] = data[349]["prompt"].replace(
        "https://www.geeksforgeeks.org/how-to-check-if-a-given-array-represents-a-binary-heap/",
        "",
    )

    check_id(data, 350, "Mbpp/752")
    data[350]["prompt"] = data[350]["prompt"].replace(
        "https://www.geeksforgeeks.org/jacobsthal-and-jacobsthal-lucas-numbers/", ""
    )

    check_id(data, 351, "Mbpp/753")
    data[351]["prompt"] = data[351]["prompt"].replace(
        "https://www.geeksforgeeks.org/python-find-minimum-k-records-from-tuple-list/",
        "",
    )

    check_id(data, 354, "Mbpp/757")
    data[354]["prompt"] = data[354]["prompt"].replace(
        "https://www.geeksforgeeks.org/python-program-to-count-the-pairs-of-reverse-strings/",
        "",
    )

    check_id(data, 359, "Mbpp/763")
    data[359]["prompt"] = data[359]["prompt"].replace(
        "https://www.geeksforgeeks.org/find-minimum-difference-pair/", ""
    )

    check_id(data, 366, "Mbpp/771")
    data[366]["prompt"] = data[366]["prompt"].replace(
        "https://www.geeksforgeeks.org/check-for-balanced-parentheses-in-an-expression/",
        "",
    )

    check_id(data, 372, "Mbpp/780")
    data[372]["prompt"] = data[372]["prompt"].replace(
        "https://www.geeksforgeeks.org/python-combinations-of-sum-with-tuples-in-tuple-list/",
        "",
    )

    check_id(data, 373, "Mbpp/781")
    data[373]["prompt"] = data[373]["prompt"].replace(
        "https://www.w3resource.com/python-exercises/basic/python-basic-1-exercise-24.php",
        "",
    )

    check_id(data, 374, "Mbpp/782")
    data[374]["prompt"] = data[374]["prompt"].replace(
        "https://www.geeksforgeeks.org/sum-of-all-odd-length-subarrays/", ""
    )

    check_id(data, 392, "Mbpp/803")
    data[392]["prompt"] = data[392]["prompt"].replace(
        "https://www.geeksforgeeks.org/check-if-given-number-is-perfect-square-in-cpp/",
        "",
    )

    # fix: https://github.com/evalplus/evalplus/issues/147

    check_id(data, 375, "Mbpp/783")
    del data[375]

    check_id(data, 345, "Mbpp/746")
    del data[345]

    check_id(data, 318, "Mbpp/640")
    del data[318]

    check_id(data, 282, "Mbpp/595")
    del data[282]

    check_id(data, 270, "Mbpp/582")
    del data[270]

    check_id(data, 263, "Mbpp/574")
    del data[263]

    check_id(data, 231, "Mbpp/461")
    del data[231]

    check_id(data, 216, "Mbpp/442")
    del data[216]

    check_id(data, 212, "Mbpp/438")
    del data[212]

    check_id(data, 206, "Mbpp/431")
    del data[206]

    check_id(data, 187, "Mbpp/407")
    del data[187]

    check_id(data, 183, "Mbpp/400")
    del data[183]

    check_id(data, 180, "Mbpp/396")
    del data[180]

    check_id(data, 160, "Mbpp/295")
    del data[160]

    check_id(data, 121, "Mbpp/249")
    del data[121]

    check_id(data, 107, "Mbpp/229")
    del data[107]

    check_id(data, 94, "Mbpp/164")
    del data[94]

    check_id(data, 89, "Mbpp/143")
    del data[89]

    check_id(data, 67, "Mbpp/117")
    del data[67]

    check_id(data, 65, "Mbpp/115")
    del data[65]

    check_id(data, 37, "Mbpp/83")
    del data[37]

    return data


if __name__ == "__main__":
    import json

    TASK_INSPECT = [
        "Mbpp/734",
        "Mbpp/735",
        "Mbpp/736",
        "Mbpp/739",
        "Mbpp/740",
        "Mbpp/743",
        "Mbpp/745",
        "Mbpp/749",
        "Mbpp/751",
        "Mbpp/752",
        "Mbpp/753",
        "Mbpp/757",
        "Mbpp/763",
        "Mbpp/771",
        "Mbpp/780",
        "Mbpp/781",
        "Mbpp/782",
        "Mbpp/803",
    ]
    SOURCE_VERSION = "v0.1.0"
    TARGET_VERSION = "v0.2.0"

    def evolve(src_file, tgt_file):
        with open(src_file) as f:
            data = [json.loads(line) for line in f.readlines() if line]

        data = fix(data)
        with open(tgt_file, "wb") as f:
            for x in data:
                f.write((json.dumps(x) + "\n").encode("utf-8"))

    evolve(f"MbppPlus-{SOURCE_VERSION}.jsonl", f"MbppPlus-{TARGET_VERSION}.jsonl")

    # Inspect the output of jsonl
    with open(f"MbppPlus-{TARGET_VERSION}.jsonl") as f:
        data = [json.loads(line) for line in f.readlines() if line]

    data = {x["task_id"]: x for x in data}
    for task_id in TASK_INSPECT:
        print(data[task_id]["prompt"])
        print("====================================")

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\util\ssltransport.py ===
import io
import socket
import ssl

from ..exceptions import ProxySchemeUnsupported
from ..packages import six

SSL_BLOCKSIZE = 16384


class SSLTransport:
    """
    The SSLTransport wraps an existing socket and establishes an SSL connection.

    Contrary to Python's implementation of SSLSocket, it allows you to chain
    multiple TLS connections together. It's particularly useful if you need to
    implement TLS within TLS.

    The class supports most of the socket API operations.
    """

    @staticmethod
    def _validate_ssl_context_for_tls_in_tls(ssl_context):
        """
        Raises a ProxySchemeUnsupported if the provided ssl_context can't be used
        for TLS in TLS.

        The only requirement is that the ssl_context provides the 'wrap_bio'
        methods.
        """

        if not hasattr(ssl_context, "wrap_bio"):
            if six.PY2:
                raise ProxySchemeUnsupported(
                    "TLS in TLS requires SSLContext.wrap_bio() which isn't "
                    "supported on Python 2"
                )
            else:
                raise ProxySchemeUnsupported(
                    "TLS in TLS requires SSLContext.wrap_bio() which isn't "
                    "available on non-native SSLContext"
                )

    def __init__(
        self, socket, ssl_context, server_hostname=None, suppress_ragged_eofs=True
    ):
        """
        Create an SSLTransport around socket using the provided ssl_context.
        """
        self.incoming = ssl.MemoryBIO()
        self.outgoing = ssl.MemoryBIO()

        self.suppress_ragged_eofs = suppress_ragged_eofs
        self.socket = socket

        self.sslobj = ssl_context.wrap_bio(
            self.incoming, self.outgoing, server_hostname=server_hostname
        )

        # Perform initial handshake.
        self._ssl_io_loop(self.sslobj.do_handshake)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def fileno(self):
        return self.socket.fileno()

    def read(self, len=1024, buffer=None):
        return self._wrap_ssl_read(len, buffer)

    def recv(self, len=1024, flags=0):
        if flags != 0:
            raise ValueError("non-zero flags not allowed in calls to recv")
        return self._wrap_ssl_read(len)

    def recv_into(self, buffer, nbytes=None, flags=0):
        if flags != 0:
            raise ValueError("non-zero flags not allowed in calls to recv_into")
        if buffer and (nbytes is None):
            nbytes = len(buffer)
        elif nbytes is None:
            nbytes = 1024
        return self.read(nbytes, buffer)

    def sendall(self, data, flags=0):
        if flags != 0:
            raise ValueError("non-zero flags not allowed in calls to sendall")
        count = 0
        with memoryview(data) as view, view.cast("B") as byte_view:
            amount = len(byte_view)
            while count < amount:
                v = self.send(byte_view[count:])
                count += v

    def send(self, data, flags=0):
        if flags != 0:
            raise ValueError("non-zero flags not allowed in calls to send")
        response = self._ssl_io_loop(self.sslobj.write, data)
        return response

    def makefile(
        self, mode="r", buffering=None, encoding=None, errors=None, newline=None
    ):
        """
        Python's httpclient uses makefile and buffered io when reading HTTP
        messages and we need to support it.

        This is unfortunately a copy and paste of socket.py makefile with small
        changes to point to the socket directly.
        """
        if not set(mode) <= {"r", "w", "b"}:
            raise ValueError("invalid mode %r (only r, w, b allowed)" % (mode,))

        writing = "w" in mode
        reading = "r" in mode or not writing
        assert reading or writing
        binary = "b" in mode
        rawmode = ""
        if reading:
            rawmode += "r"
        if writing:
            rawmode += "w"
        raw = socket.SocketIO(self, rawmode)
        self.socket._io_refs += 1
        if buffering is None:
            buffering = -1
        if buffering < 0:
            buffering = io.DEFAULT_BUFFER_SIZE
        if buffering == 0:
            if not binary:
                raise ValueError("unbuffered streams must be binary")
            return raw
        if reading and writing:
            buffer = io.BufferedRWPair(raw, raw, buffering)
        elif reading:
            buffer = io.BufferedReader(raw, buffering)
        else:
            assert writing
            buffer = io.BufferedWriter(raw, buffering)
        if binary:
            return buffer
        text = io.TextIOWrapper(buffer, encoding, errors, newline)
        text.mode = mode
        return text

    def unwrap(self):
        self._ssl_io_loop(self.sslobj.unwrap)

    def close(self):
        self.socket.close()

    def getpeercert(self, binary_form=False):
        return self.sslobj.getpeercert(binary_form)

    def version(self):
        return self.sslobj.version()

    def cipher(self):
        return self.sslobj.cipher()

    def selected_alpn_protocol(self):
        return self.sslobj.selected_alpn_protocol()

    def selected_npn_protocol(self):
        return self.sslobj.selected_npn_protocol()

    def shared_ciphers(self):
        return self.sslobj.shared_ciphers()

    def compression(self):
        return self.sslobj.compression()

    def settimeout(self, value):
        self.socket.settimeout(value)

    def gettimeout(self):
        return self.socket.gettimeout()

    def _decref_socketios(self):
        self.socket._decref_socketios()

    def _wrap_ssl_read(self, len, buffer=None):
        try:
            return self._ssl_io_loop(self.sslobj.read, len, buffer)
        except ssl.SSLError as e:
            if e.errno == ssl.SSL_ERROR_EOF and self.suppress_ragged_eofs:
                return 0  # eof, return 0.
            else:
                raise

    def _ssl_io_loop(self, func, *args):
        """Performs an I/O loop between incoming/outgoing and the socket."""
        should_loop = True
        ret = None

        while should_loop:
            errno = None
            try:
                ret = func(*args)
            except ssl.SSLError as e:
                if e.errno not in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):
                    # WANT_READ, and WANT_WRITE are expected, others are not.
                    raise e
                errno = e.errno

            buf = self.outgoing.read()
            self.socket.sendall(buf)

            if errno is None:
                should_loop = False
            elif errno == ssl.SSL_ERROR_WANT_READ:
                buf = self.socket.recv(SSL_BLOCKSIZE)
                if buf:
                    self.incoming.write(buf)
                else:
                    self.incoming.write_eof()
        return ret

# === NexusCore/openenv\Lib\site-packages\openai\_types.py ===
from __future__ import annotations

from os import PathLike
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Type,
    Tuple,
    Union,
    Mapping,
    TypeVar,
    Callable,
    Optional,
    Sequence,
)
from typing_extensions import Set, Literal, Protocol, TypeAlias, TypedDict, override, runtime_checkable

import httpx
import pydantic
from httpx import URL, Proxy, Timeout, Response, BaseTransport, AsyncBaseTransport

if TYPE_CHECKING:
    from ._models import BaseModel
    from ._response import APIResponse, AsyncAPIResponse
    from ._legacy_response import HttpxBinaryResponseContent

Transport = BaseTransport
AsyncTransport = AsyncBaseTransport
Query = Mapping[str, object]
Body = object
AnyMapping = Mapping[str, object]
ModelT = TypeVar("ModelT", bound=pydantic.BaseModel)
_T = TypeVar("_T")


# Approximates httpx internal ProxiesTypes and RequestFiles types
# while adding support for `PathLike` instances
ProxiesDict = Dict["str | URL", Union[None, str, URL, Proxy]]
ProxiesTypes = Union[str, Proxy, ProxiesDict]
if TYPE_CHECKING:
    Base64FileInput = Union[IO[bytes], PathLike[str]]
    FileContent = Union[IO[bytes], bytes, PathLike[str]]
else:
    Base64FileInput = Union[IO[bytes], PathLike]
    FileContent = Union[IO[bytes], bytes, PathLike]  # PathLike is not subscriptable in Python 3.8.
FileTypes = Union[
    # file (or bytes)
    FileContent,
    # (filename, file (or bytes))
    Tuple[Optional[str], FileContent],
    # (filename, file (or bytes), content_type)
    Tuple[Optional[str], FileContent, Optional[str]],
    # (filename, file (or bytes), content_type, headers)
    Tuple[Optional[str], FileContent, Optional[str], Mapping[str, str]],
]
RequestFiles = Union[Mapping[str, FileTypes], Sequence[Tuple[str, FileTypes]]]

# duplicate of the above but without our custom file support
HttpxFileContent = Union[IO[bytes], bytes]
HttpxFileTypes = Union[
    # file (or bytes)
    HttpxFileContent,
    # (filename, file (or bytes))
    Tuple[Optional[str], HttpxFileContent],
    # (filename, file (or bytes), content_type)
    Tuple[Optional[str], HttpxFileContent, Optional[str]],
    # (filename, file (or bytes), content_type, headers)
    Tuple[Optional[str], HttpxFileContent, Optional[str], Mapping[str, str]],
]
HttpxRequestFiles = Union[Mapping[str, HttpxFileTypes], Sequence[Tuple[str, HttpxFileTypes]]]

# Workaround to support (cast_to: Type[ResponseT]) -> ResponseT
# where ResponseT includes `None`. In order to support directly
# passing `None`, overloads would have to be defined for every
# method that uses `ResponseT` which would lead to an unacceptable
# amount of code duplication and make it unreadable. See _base_client.py
# for example usage.
#
# This unfortunately means that you will either have
# to import this type and pass it explicitly:
#
# from openai import NoneType
# client.get('/foo', cast_to=NoneType)
#
# or build it yourself:
#
# client.get('/foo', cast_to=type(None))
if TYPE_CHECKING:
    NoneType: Type[None]
else:
    NoneType = type(None)


class RequestOptions(TypedDict, total=False):
    headers: Headers
    max_retries: int
    timeout: float | Timeout | None
    params: Query
    extra_json: AnyMapping
    idempotency_key: str
    follow_redirects: bool


# Sentinel class used until PEP 0661 is accepted
class NotGiven:
    """
    A sentinel singleton class used to distinguish omitted keyword arguments
    from those passed in with the value None (which may have different behavior).

    For example:

    ```py
    def get(timeout: Union[int, NotGiven, None] = NotGiven()) -> Response: ...


    get(timeout=1)  # 1s timeout
    get(timeout=None)  # No timeout
    get()  # Default timeout behavior, which may not be statically known at the method definition.
    ```
    """

    def __bool__(self) -> Literal[False]:
        return False

    @override
    def __repr__(self) -> str:
        return "NOT_GIVEN"


NotGivenOr = Union[_T, NotGiven]
NOT_GIVEN = NotGiven()


class Omit:
    """In certain situations you need to be able to represent a case where a default value has
    to be explicitly removed and `None` is not an appropriate substitute, for example:

    ```py
    # as the default `Content-Type` header is `application/json` that will be sent
    client.post("/upload/files", files={"file": b"my raw file content"})

    # you can't explicitly override the header as it has to be dynamically generated
    # to look something like: 'multipart/form-data; boundary=0d8382fcf5f8c3be01ca2e11002d2983'
    client.post(..., headers={"Content-Type": "multipart/form-data"})

    # instead you can remove the default `application/json` header by passing Omit
    client.post(..., headers={"Content-Type": Omit()})
    ```
    """

    def __bool__(self) -> Literal[False]:
        return False


@runtime_checkable
class ModelBuilderProtocol(Protocol):
    @classmethod
    def build(
        cls: type[_T],
        *,
        response: Response,
        data: object,
    ) -> _T: ...


Headers = Mapping[str, Union[str, Omit]]


class HeadersLikeProtocol(Protocol):
    def get(self, __key: str) -> str | None: ...


HeadersLike = Union[Headers, HeadersLikeProtocol]

ResponseT = TypeVar(
    "ResponseT",
    bound=Union[
        object,
        str,
        None,
        "BaseModel",
        List[Any],
        Dict[str, Any],
        Response,
        ModelBuilderProtocol,
        "APIResponse[Any]",
        "AsyncAPIResponse[Any]",
        "HttpxBinaryResponseContent",
    ],
)

StrBytesIntFloat = Union[str, bytes, int, float]

# Note: copied from Pydantic
# https://github.com/pydantic/pydantic/blob/6f31f8f68ef011f84357330186f603ff295312fd/pydantic/main.py#L79
IncEx: TypeAlias = Union[Set[int], Set[str], Mapping[int, Union["IncEx", bool]], Mapping[str, Union["IncEx", bool]]]

PostParser = Callable[[Any], Any]


@runtime_checkable
class InheritsGeneric(Protocol):
    """Represents a type that has inherited from `Generic`

    The `__orig_bases__` property can be used to determine the resolved
    type variable for a given base class.
    """

    __orig_bases__: tuple[_GenericAlias]


class _GenericAlias(Protocol):
    __origin__: type[object]


class HttpxSendArgs(TypedDict, total=False):
    auth: httpx.Auth
    follow_redirects: bool

# === NexusCore/openenv\Lib\site-packages\tiktoken\_educational.py ===
"""This is an educational implementation of the byte pair encoding algorithm."""
import collections
from typing import Optional

import regex

import tiktoken


class SimpleBytePairEncoding:
    def __init__(self, *, pat_str: str, mergeable_ranks: dict[bytes, int]) -> None:
        """Creates an Encoding object."""
        # A regex pattern string that is used to split the input text
        self.pat_str = pat_str
        # A dictionary mapping token bytes to their ranks. The ranks correspond to merge priority
        self.mergeable_ranks = mergeable_ranks

        self._decoder = {token: token_bytes for token_bytes, token in mergeable_ranks.items()}
        self._pat = regex.compile(pat_str)

    def encode(self, text: str, visualise: Optional[str] = "colour") -> list[int]:
        """Encodes a string into tokens.

        >>> enc.encode("hello world")
        [388, 372]
        """
        # Use the regex to split the text into (approximately) words
        words = self._pat.findall(text)
        tokens = []
        for word in words:
            # Turn each word into tokens, using the byte pair encoding algorithm
            word_bytes = word.encode("utf-8")
            word_tokens = bpe_encode(self.mergeable_ranks, word_bytes, visualise=visualise)
            tokens.extend(word_tokens)
        return tokens

    def decode_bytes(self, tokens: list[int]) -> bytes:
        """Decodes a list of tokens into bytes.

        >>> enc.decode_bytes([388, 372])
        b'hello world'
        """
        return b"".join(self._decoder[token] for token in tokens)

    def decode(self, tokens: list[int]) -> str:
        """Decodes a list of tokens into a string.

        Decoded bytes are not guaranteed to be valid UTF-8. In that case, we replace
        the invalid bytes with the replacement character "�".

        >>> enc.decode([388, 372])
        'hello world'
        """
        return self.decode_bytes(tokens).decode("utf-8", errors="replace")

    def decode_tokens_bytes(self, tokens: list[int]) -> list[bytes]:
        """Decodes a list of tokens into a list of bytes.

        Useful for visualising how a string is tokenised.

        >>> enc.decode_tokens_bytes([388, 372])
        [b'hello', b' world']
        """
        return [self._decoder[token] for token in tokens]

    @staticmethod
    def train(training_data: str, vocab_size: int, pat_str: str):
        """Train a BPE tokeniser on some data!"""
        mergeable_ranks = bpe_train(data=training_data, vocab_size=vocab_size, pat_str=pat_str)
        return SimpleBytePairEncoding(pat_str=pat_str, mergeable_ranks=mergeable_ranks)

    @staticmethod
    def from_tiktoken(encoding):
        if isinstance(encoding, str):
            encoding = tiktoken.get_encoding(encoding)
        return SimpleBytePairEncoding(
            pat_str=encoding._pat_str, mergeable_ranks=encoding._mergeable_ranks
        )


def bpe_encode(
    mergeable_ranks: dict[bytes, int], input: bytes, visualise: Optional[str] = "colour"
) -> list[int]:
    parts = [bytes([b]) for b in input]
    while True:
        # See the intermediate merges play out!
        if visualise:
            if visualise in ["colour", "color"]:
                visualise_tokens(parts)
            elif visualise == "simple":
                print(parts)

        # Iterate over all pairs and find the pair we want to merge the most
        min_idx = None
        min_rank = None
        for i, pair in enumerate(zip(parts[:-1], parts[1:])):
            rank = mergeable_ranks.get(pair[0] + pair[1])
            if rank is not None and (min_rank is None or rank < min_rank):
                min_idx = i
                min_rank = rank

        # If there were no pairs we could merge, we're done!
        if min_rank is None:
            break
        assert min_idx is not None

        # Otherwise, merge that pair and leave the rest unchanged. Then repeat.
        parts = parts[:min_idx] + [parts[min_idx] + parts[min_idx + 1]] + parts[min_idx + 2 :]

    if visualise:
        print()

    tokens = [mergeable_ranks[part] for part in parts]
    return tokens


def bpe_train(
    data: str, vocab_size: int, pat_str: str, visualise: Optional[str] = "colour"
) -> dict[bytes, int]:
    # First, add tokens for each individual byte value
    if vocab_size < 2**8:
        raise ValueError("vocab_size must be at least 256, so we can encode all bytes")
    ranks = {}
    for i in range(2**8):
        ranks[bytes([i])] = i

    # Splinter up our data into lists of bytes
    # data = "Hello world"
    # words = [
    #     [b'H', b'e', b'l', b'l', b'o'],
    #     [b' ', b'w', b'o', b'r', b'l', b'd']
    # ]
    words: list[list[bytes]] = [
        [bytes([b]) for b in word.encode("utf-8")] for word in regex.findall(pat_str, data)
    ]

    # Now, use our data to figure out which merges we should make
    while len(ranks) < vocab_size:
        # Find the most common pair. This will become our next token
        stats = collections.Counter()
        for piece in words:
            for pair in zip(piece[:-1], piece[1:]):
                stats[pair] += 1

        most_common_pair = max(stats, key=lambda x: stats[x])
        token_bytes = most_common_pair[0] + most_common_pair[1]
        token = len(ranks)
        # Add the new token!
        ranks[token_bytes] = token

        # Now merge that most common pair in all the words. That is, update our training data
        # to reflect our decision to make that pair into a new token.
        new_words = []
        for word in words:
            new_word = []
            i = 0
            while i < len(word) - 1:
                if (word[i], word[i + 1]) == most_common_pair:
                    # We found our pair! Merge it
                    new_word.append(token_bytes)
                    i += 2
                else:
                    new_word.append(word[i])
                    i += 1
            if i == len(word) - 1:
                new_word.append(word[i])
            new_words.append(new_word)
        words = new_words

        # See the intermediate merges play out!
        if visualise:
            print(f"The current most common pair is {most_common_pair[0]} + {most_common_pair[1]}")
            print(f"So we made {token_bytes} our {len(ranks)}th token")
            if visualise in ["colour", "color"]:
                print("Now the first fifty words in our training data look like:")
                visualise_tokens([token for word in words[:50] for token in word])
            elif visualise == "simple":
                print("Now the first twenty words in our training data look like:")
                for word in words[:20]:
                    print(word)
            print("\n")

    return ranks


def visualise_tokens(token_values: list[bytes]) -> None:
    background = [f"\u001b[48;5;{i}m" for i in [167, 179, 185, 77, 80, 68, 134]]
    # If token boundaries do not occur at unicode character boundaries, it's unclear how best to
    # visualise the token. Here, we'll just use the unicode replacement character to represent some
    # fraction of a character.
    unicode_token_values = [x.decode("utf-8", errors="replace") for x in token_values]

    running_length = 0
    last_color = None
    for token in unicode_token_values:
        color = background[running_length % len(background)]
        if color == last_color:
            color = background[(running_length + 1) % len(background)]
            assert color != last_color
        last_color = color
        running_length += len(token)
        print(color + token, end="")
    print("\u001b[0m")


def train_simple_encoding():
    gpt2_pattern = (
        r"""'s|'t|'re|'ve|'m|'ll|'d| ?[\p{L}]+| ?[\p{N}]+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
    )
    with open(__file__, "r") as f:
        data = f.read()

    enc = SimpleBytePairEncoding.train(data, vocab_size=600, pat_str=gpt2_pattern)

    print("This is the sequence of merges performed in order to encode 'hello world':")
    tokens = enc.encode("hello world")
    assert enc.decode(tokens) == "hello world"
    assert enc.decode_bytes(tokens) == b"hello world"
    assert enc.decode_tokens_bytes(tokens) == [b"hello", b" world"]

    return enc