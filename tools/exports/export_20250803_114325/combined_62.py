
# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\buffer.py ===
"""
Data structures for the Buffer.
It holds the text, cursor position, history, etc...
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from collections import deque
from enum import Enum
from functools import wraps
from typing import Any, Callable, Coroutine, Iterable, TypeVar, cast

from .application.current import get_app
from .application.run_in_terminal import run_in_terminal
from .auto_suggest import AutoSuggest, Suggestion
from .cache import FastDictCache
from .clipboard import ClipboardData
from .completion import (
    CompleteEvent,
    Completer,
    Completion,
    DummyCompleter,
    get_common_complete_suffix,
)
from .document import Document
from .eventloop import aclosing
from .filters import FilterOrBool, to_filter
from .history import History, InMemoryHistory
from .search import SearchDirection, SearchState
from .selection import PasteMode, SelectionState, SelectionType
from .utils import Event, to_str
from .validation import ValidationError, Validator

__all__ = [
    "EditReadOnlyBuffer",
    "Buffer",
    "CompletionState",
    "indent",
    "unindent",
    "reshape_text",
]

logger = logging.getLogger(__name__)


class EditReadOnlyBuffer(Exception):
    "Attempt editing of read-only :class:`.Buffer`."


class ValidationState(Enum):
    "The validation state of a buffer. This is set after the validation."

    VALID = "VALID"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class CompletionState:
    """
    Immutable class that contains a completion state.
    """

    def __init__(
        self,
        original_document: Document,
        completions: list[Completion] | None = None,
        complete_index: int | None = None,
    ) -> None:
        #: Document as it was when the completion started.
        self.original_document = original_document

        #: List of all the current Completion instances which are possible at
        #: this point.
        self.completions = completions or []

        #: Position in the `completions` array.
        #: This can be `None` to indicate "no completion", the original text.
        self.complete_index = complete_index  # Position in the `_completions` array.

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.original_document!r}, <{len(self.completions)!r}> completions, index={self.complete_index!r})"

    def go_to_index(self, index: int | None) -> None:
        """
        Create a new :class:`.CompletionState` object with the new index.

        When `index` is `None` deselect the completion.
        """
        if self.completions:
            assert index is None or 0 <= index < len(self.completions)
            self.complete_index = index

    def new_text_and_position(self) -> tuple[str, int]:
        """
        Return (new_text, new_cursor_position) for this completion.
        """
        if self.complete_index is None:
            return self.original_document.text, self.original_document.cursor_position
        else:
            original_text_before_cursor = self.original_document.text_before_cursor
            original_text_after_cursor = self.original_document.text_after_cursor

            c = self.completions[self.complete_index]
            if c.start_position == 0:
                before = original_text_before_cursor
            else:
                before = original_text_before_cursor[: c.start_position]

            new_text = before + c.text + original_text_after_cursor
            new_cursor_position = len(before) + len(c.text)
            return new_text, new_cursor_position

    @property
    def current_completion(self) -> Completion | None:
        """
        Return the current completion, or return `None` when no completion is
        selected.
        """
        if self.complete_index is not None:
            return self.completions[self.complete_index]
        return None


_QUOTED_WORDS_RE = re.compile(r"""(\s+|".*?"|'.*?')""")


class YankNthArgState:
    """
    For yank-last-arg/yank-nth-arg: Keep track of where we are in the history.
    """

    def __init__(
        self, history_position: int = 0, n: int = -1, previous_inserted_word: str = ""
    ) -> None:
        self.history_position = history_position
        self.previous_inserted_word = previous_inserted_word
        self.n = n

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(history_position={self.history_position!r}, n={self.n!r}, previous_inserted_word={self.previous_inserted_word!r})"


BufferEventHandler = Callable[["Buffer"], None]
BufferAcceptHandler = Callable[["Buffer"], bool]


class Buffer:
    """
    The core data structure that holds the text and cursor position of the
    current input line and implements all text manipulations on top of it. It
    also implements the history, undo stack and the completion state.

    :param completer: :class:`~prompt_toolkit.completion.Completer` instance.
    :param history: :class:`~prompt_toolkit.history.History` instance.
    :param tempfile_suffix: The tempfile suffix (extension) to be used for the
        "open in editor" function. For a Python REPL, this would be ".py", so
        that the editor knows the syntax highlighting to use. This can also be
        a callable that returns a string.
    :param tempfile: For more advanced tempfile situations where you need
        control over the subdirectories and filename. For a Git Commit Message,
        this would be ".git/COMMIT_EDITMSG", so that the editor knows the syntax
        highlighting to use. This can also be a callable that returns a string.
    :param name: Name for this buffer. E.g. DEFAULT_BUFFER. This is mostly
        useful for key bindings where we sometimes prefer to refer to a buffer
        by their name instead of by reference.
    :param accept_handler: Called when the buffer input is accepted. (Usually
        when the user presses `enter`.) The accept handler receives this
        `Buffer` as input and should return True when the buffer text should be
        kept instead of calling reset.

        In case of a `PromptSession` for instance, we want to keep the text,
        because we will exit the application, and only reset it during the next
        run.
    :param max_number_of_completions: Never display more than this number of
        completions, even when the completer can produce more (limited by
        default to 10k for performance).

    Events:

    :param on_text_changed: When the buffer text changes. (Callable or None.)
    :param on_text_insert: When new text is inserted. (Callable or None.)
    :param on_cursor_position_changed: When the cursor moves. (Callable or None.)
    :param on_completions_changed: When the completions were changed. (Callable or None.)
    :param on_suggestion_set: When an auto-suggestion text has been set. (Callable or None.)

    Filters:

    :param complete_while_typing: :class:`~prompt_toolkit.filters.Filter`
        or `bool`. Decide whether or not to do asynchronous autocompleting while
        typing.
    :param validate_while_typing: :class:`~prompt_toolkit.filters.Filter`
        or `bool`. Decide whether or not to do asynchronous validation while
        typing.
    :param enable_history_search: :class:`~prompt_toolkit.filters.Filter` or
        `bool` to indicate when up-arrow partial string matching is enabled. It
        is advised to not enable this at the same time as
        `complete_while_typing`, because when there is an autocompletion found,
        the up arrows usually browse through the completions, rather than
        through the history.
    :param read_only: :class:`~prompt_toolkit.filters.Filter`. When True,
        changes will not be allowed.
    :param multiline: :class:`~prompt_toolkit.filters.Filter` or `bool`. When
        not set, pressing `Enter` will call the `accept_handler`.  Otherwise,
        pressing `Esc-Enter` is required.
    """

    def __init__(
        self,
        completer: Completer | None = None,
        auto_suggest: AutoSuggest | None = None,
        history: History | None = None,
        validator: Validator | None = None,
        tempfile_suffix: str | Callable[[], str] = "",
        tempfile: str | Callable[[], str] = "",
        name: str = "",
        complete_while_typing: FilterOrBool = False,
        validate_while_typing: FilterOrBool = False,
        enable_history_search: FilterOrBool = False,
        document: Document | None = None,
        accept_handler: BufferAcceptHandler | None = None,
        read_only: FilterOrBool = False,
        multiline: FilterOrBool = True,
        max_number_of_completions: int = 10000,
        on_text_changed: BufferEventHandler | None = None,
        on_text_insert: BufferEventHandler | None = None,
        on_cursor_position_changed: BufferEventHandler | None = None,
        on_completions_changed: BufferEventHandler | None = None,
        on_suggestion_set: BufferEventHandler | None = None,
    ) -> None:
        # Accept both filters and booleans as input.
        enable_history_search = to_filter(enable_history_search)
        complete_while_typing = to_filter(complete_while_typing)
        validate_while_typing = to_filter(validate_while_typing)
        read_only = to_filter(read_only)
        multiline = to_filter(multiline)

        self.completer = completer or DummyCompleter()
        self.auto_suggest = auto_suggest
        self.validator = validator
        self.tempfile_suffix = tempfile_suffix
        self.tempfile = tempfile
        self.name = name
        self.accept_handler = accept_handler

        # Filters. (Usually, used by the key bindings to drive the buffer.)
        self.complete_while_typing = complete_while_typing
        self.validate_while_typing = validate_while_typing
        self.enable_history_search = enable_history_search
        self.read_only = read_only
        self.multiline = multiline
        self.max_number_of_completions = max_number_of_completions

        # Text width. (For wrapping, used by the Vi 'gq' operator.)
        self.text_width = 0

        #: The command buffer history.
        # Note that we shouldn't use a lazy 'or' here. bool(history) could be
        # False when empty.
        self.history = InMemoryHistory() if history is None else history

        self.__cursor_position = 0

        # Events
        self.on_text_changed: Event[Buffer] = Event(self, on_text_changed)
        self.on_text_insert: Event[Buffer] = Event(self, on_text_insert)
        self.on_cursor_position_changed: Event[Buffer] = Event(
            self, on_cursor_position_changed
        )
        self.on_completions_changed: Event[Buffer] = Event(self, on_completions_changed)
        self.on_suggestion_set: Event[Buffer] = Event(self, on_suggestion_set)

        # Document cache. (Avoid creating new Document instances.)
        self._document_cache: FastDictCache[
            tuple[str, int, SelectionState | None], Document
        ] = FastDictCache(Document, size=10)

        # Create completer / auto suggestion / validation coroutines.
        self._async_suggester = self._create_auto_suggest_coroutine()
        self._async_completer = self._create_completer_coroutine()
        self._async_validator = self._create_auto_validate_coroutine()

        # Asyncio task for populating the history.
        self._load_history_task: asyncio.Future[None] | None = None

        # Reset other attributes.
        self.reset(document=document)

    def __repr__(self) -> str:
        if len(self.text) < 15:
            text = self.text
        else:
            text = self.text[:12] + "..."

        return f"<Buffer(name={self.name!r}, text={text!r}) at {id(self)!r}>"

    def reset(
        self, document: Document | None = None, append_to_history: bool = False
    ) -> None:
        """
        :param append_to_history: Append current input to history first.
        """
        if append_to_history:
            self.append_to_history()

        document = document or Document()

        self.__cursor_position = document.cursor_position

        # `ValidationError` instance. (Will be set when the input is wrong.)
        self.validation_error: ValidationError | None = None
        self.validation_state: ValidationState | None = ValidationState.UNKNOWN

        # State of the selection.
        self.selection_state: SelectionState | None = None

        # Multiple cursor mode. (When we press 'I' or 'A' in visual-block mode,
        # we can insert text on multiple lines at once. This is implemented by
        # using multiple cursors.)
        self.multiple_cursor_positions: list[int] = []

        # When doing consecutive up/down movements, prefer to stay at this column.
        self.preferred_column: int | None = None

        # State of complete browser
        # For interactive completion through Ctrl-N/Ctrl-P.
        self.complete_state: CompletionState | None = None

        # State of Emacs yank-nth-arg completion.
        self.yank_nth_arg_state: YankNthArgState | None = None  # for yank-nth-arg.

        # Remember the document that we had *right before* the last paste
        # operation. This is used for rotating through the kill ring.
        self.document_before_paste: Document | None = None

        # Current suggestion.
        self.suggestion: Suggestion | None = None

        # The history search text. (Used for filtering the history when we
        # browse through it.)
        self.history_search_text: str | None = None

        # Undo/redo stacks (stack of `(text, cursor_position)`).
        self._undo_stack: list[tuple[str, int]] = []
        self._redo_stack: list[tuple[str, int]] = []

        # Cancel history loader. If history loading was still ongoing.
        # Cancel the `_load_history_task`, so that next repaint of the
        # `BufferControl` we will repopulate it.
        if self._load_history_task is not None:
            self._load_history_task.cancel()
        self._load_history_task = None

        #: The working lines. Similar to history, except that this can be
        #: modified. The user can press arrow_up and edit previous entries.
        #: Ctrl-C should reset this, and copy the whole history back in here.
        #: Enter should process the current command and append to the real
        #: history.
        self._working_lines: deque[str] = deque([document.text])
        self.__working_index = 0

    def load_history_if_not_yet_loaded(self) -> None:
        """
        Create task for populating the buffer history (if not yet done).

        Note::

            This needs to be called from within the event loop of the
            application, because history loading is async, and we need to be
            sure the right event loop is active. Therefor, we call this method
            in the `BufferControl.create_content`.

            There are situations where prompt_toolkit applications are created
            in one thread, but will later run in a different thread (Ptpython
            is one example. The REPL runs in a separate thread, in order to
            prevent interfering with a potential different event loop in the
            main thread. The REPL UI however is still created in the main
            thread.) We could decide to not support creating prompt_toolkit
            objects in one thread and running the application in a different
            thread, but history loading is the only place where it matters, and
            this solves it.
        """
        if self._load_history_task is None:

            async def load_history() -> None:
                async for item in self.history.load():
                    self._working_lines.appendleft(item)
                    self.__working_index += 1

            self._load_history_task = get_app().create_background_task(load_history())

            def load_history_done(f: asyncio.Future[None]) -> None:
                """
                Handle `load_history` result when either done, cancelled, or
                when an exception was raised.
                """
                try:
                    f.result()
                except asyncio.CancelledError:
                    # Ignore cancellation. But handle it, so that we don't get
                    # this traceback.
                    pass
                except GeneratorExit:
                    # Probably not needed, but we had situations where
                    # `GeneratorExit` was raised in `load_history` during
                    # cancellation.
                    pass
                except BaseException:
                    # Log error if something goes wrong. (We don't have a
                    # caller to which we can propagate this exception.)
                    logger.exception("Loading history failed")

            self._load_history_task.add_done_callback(load_history_done)

    # <getters/setters>

    def _set_text(self, value: str) -> bool:
        """set text at current working_index. Return whether it changed."""
        working_index = self.working_index
        working_lines = self._working_lines

        original_value = working_lines[working_index]
        working_lines[working_index] = value

        # Return True when this text has been changed.
        if len(value) != len(original_value):
            # For Python 2, it seems that when two strings have a different
            # length and one is a prefix of the other, Python still scans
            # character by character to see whether the strings are different.
            # (Some benchmarking showed significant differences for big
            # documents. >100,000 of lines.)
            return True
        elif value != original_value:
            return True
        return False

    def _set_cursor_position(self, value: int) -> bool:
        """Set cursor position. Return whether it changed."""
        original_position = self.__cursor_position
        self.__cursor_position = max(0, value)

        return self.__cursor_position != original_position

    @property
    def text(self) -> str:
        return self._working_lines[self.working_index]

    @text.setter
    def text(self, value: str) -> None:
        """
        Setting text. (When doing this, make sure that the cursor_position is
        valid for this text. text/cursor_position should be consistent at any time,
        otherwise set a Document instead.)
        """
        # Ensure cursor position remains within the size of the text.
        if self.cursor_position > len(value):
            self.cursor_position = len(value)

        # Don't allow editing of read-only buffers.
        if self.read_only():
            raise EditReadOnlyBuffer()

        changed = self._set_text(value)

        if changed:
            self._text_changed()

            # Reset history search text.
            # (Note that this doesn't need to happen when working_index
            #  changes, which is when we traverse the history. That's why we
            #  don't do this in `self._text_changed`.)
            self.history_search_text = None

    @property
    def cursor_position(self) -> int:
        return self.__cursor_position

    @cursor_position.setter
    def cursor_position(self, value: int) -> None:
        """
        Setting cursor position.
        """
        assert isinstance(value, int)

        # Ensure cursor position is within the size of the text.
        if value > len(self.text):
            value = len(self.text)
        if value < 0:
            value = 0

        changed = self._set_cursor_position(value)

        if changed:
            self._cursor_position_changed()

    @property
    def working_index(self) -> int:
        return self.__working_index

    @working_index.setter
    def working_index(self, value: int) -> None:
        if self.__working_index != value:
            self.__working_index = value
            # Make sure to reset the cursor position, otherwise we end up in
            # situations where the cursor position is out of the bounds of the
            # text.
            self.cursor_position = 0
            self._text_changed()

    def _text_changed(self) -> None:
        # Remove any validation errors and complete state.
        self.validation_error = None
        self.validation_state = ValidationState.UNKNOWN
        self.complete_state = None
        self.yank_nth_arg_state = None
        self.document_before_paste = None
        self.selection_state = None
        self.suggestion = None
        self.preferred_column = None

        # fire 'on_text_changed' event.
        self.on_text_changed.fire()

        # Input validation.
        # (This happens on all change events, unlike auto completion, also when
        # deleting text.)
        if self.validator and self.validate_while_typing():
            get_app().create_background_task(self._async_validator())

    def _cursor_position_changed(self) -> None:
        # Remove any complete state.
        # (Input validation should only be undone when the cursor position
        # changes.)
        self.complete_state = None
        self.yank_nth_arg_state = None
        self.document_before_paste = None

        # Unset preferred_column. (Will be set after the cursor movement, if
        # required.)
        self.preferred_column = None

        # Note that the cursor position can change if we have a selection the
        # new position of the cursor determines the end of the selection.

        # fire 'on_cursor_position_changed' event.
        self.on_cursor_position_changed.fire()

    @property
    def document(self) -> Document:
        """
        Return :class:`~prompt_toolkit.document.Document` instance from the
        current text, cursor position and selection state.
        """
        return self._document_cache[
            self.text, self.cursor_position, self.selection_state
        ]

    @document.setter
    def document(self, value: Document) -> None:
        """
        Set :class:`~prompt_toolkit.document.Document` instance.

        This will set both the text and cursor position at the same time, but
        atomically. (Change events will be triggered only after both have been set.)
        """
        self.set_document(value)

    def set_document(self, value: Document, bypass_readonly: bool = False) -> None:
        """
        Set :class:`~prompt_toolkit.document.Document` instance. Like the
        ``document`` property, but accept an ``bypass_readonly`` argument.

        :param bypass_readonly: When True, don't raise an
                                :class:`.EditReadOnlyBuffer` exception, even
                                when the buffer is read-only.

        .. warning::

            When this buffer is read-only and `bypass_readonly` was not passed,
            the `EditReadOnlyBuffer` exception will be caught by the
            `KeyProcessor` and is silently suppressed. This is important to
            keep in mind when writing key bindings, because it won't do what
            you expect, and there won't be a stack trace. Use try/finally
            around this function if you need some cleanup code.
        """
        # Don't allow editing of read-only buffers.
        if not bypass_readonly and self.read_only():
            raise EditReadOnlyBuffer()

        # Set text and cursor position first.
        text_changed = self._set_text(value.text)
        cursor_position_changed = self._set_cursor_position(value.cursor_position)

        # Now handle change events. (We do this when text/cursor position is
        # both set and consistent.)
        if text_changed:
            self._text_changed()
            self.history_search_text = None

        if cursor_position_changed:
            self._cursor_position_changed()

    @property
    def is_returnable(self) -> bool:
        """
        True when there is something handling accept.
        """
        return bool(self.accept_handler)

    # End of <getters/setters>

    def save_to_undo_stack(self, clear_redo_stack: bool = True) -> None:
        """
        Safe current state (input text and cursor position), so that we can
        restore it by calling undo.
        """
        # Safe if the text is different from the text at the top of the stack
        # is different. If the text is the same, just update the cursor position.
        if self._undo_stack and self._undo_stack[-1][0] == self.text:
            self._undo_stack[-1] = (self._undo_stack[-1][0], self.cursor_position)
        else:
            self._undo_stack.append((self.text, self.cursor_position))

        # Saving anything to the undo stack, clears the redo stack.
        if clear_redo_stack:
            self._redo_stack = []

    def transform_lines(
        self,
        line_index_iterator: Iterable[int],
        transform_callback: Callable[[str], str],
    ) -> str:
        """
        Transforms the text on a range of lines.
        When the iterator yield an index not in the range of lines that the
        document contains, it skips them silently.

        To uppercase some lines::

            new_text = transform_lines(range(5,10), lambda text: text.upper())

        :param line_index_iterator: Iterator of line numbers (int)
        :param transform_callback: callable that takes the original text of a
                                   line, and return the new text for this line.

        :returns: The new text.
        """
        # Split lines
        lines = self.text.split("\n")

        # Apply transformation
        for index in line_index_iterator:
            try:
                lines[index] = transform_callback(lines[index])
            except IndexError:
                pass

        return "\n".join(lines)

    def transform_current_line(self, transform_callback: Callable[[str], str]) -> None:
        """
        Apply the given transformation function to the current line.

        :param transform_callback: callable that takes a string and return a new string.
        """
        document = self.document
        a = document.cursor_position + document.get_start_of_line_position()
        b = document.cursor_position + document.get_end_of_line_position()
        self.text = (
            document.text[:a]
            + transform_callback(document.text[a:b])
            + document.text[b:]
        )

    def transform_region(
        self, from_: int, to: int, transform_callback: Callable[[str], str]
    ) -> None:
        """
        Transform a part of the input string.

        :param from_: (int) start position.
        :param to: (int) end position.
        :param transform_callback: Callable which accepts a string and returns
            the transformed string.
        """
        assert from_ < to

        self.text = "".join(
            [
                self.text[:from_]
                + transform_callback(self.text[from_:to])
                + self.text[to:]
            ]
        )

    def cursor_left(self, count: int = 1) -> None:
        self.cursor_position += self.document.get_cursor_left_position(count=count)

    def cursor_right(self, count: int = 1) -> None:
        self.cursor_position += self.document.get_cursor_right_position(count=count)

    def cursor_up(self, count: int = 1) -> None:
        """(for multiline edit). Move cursor to the previous line."""
        original_column = self.preferred_column or self.document.cursor_position_col
        self.cursor_position += self.document.get_cursor_up_position(
            count=count, preferred_column=original_column
        )

        # Remember the original column for the next up/down movement.
        self.preferred_column = original_column

    def cursor_down(self, count: int = 1) -> None:
        """(for multiline edit). Move cursor to the next line."""
        original_column = self.preferred_column or self.document.cursor_position_col
        self.cursor_position += self.document.get_cursor_down_position(
            count=count, preferred_column=original_column
        )

        # Remember the original column for the next up/down movement.
        self.preferred_column = original_column

    def auto_up(
        self, count: int = 1, go_to_start_of_line_if_history_changes: bool = False
    ) -> None:
        """
        If we're not on the first line (of a multiline input) go a line up,
        otherwise go back in history. (If nothing is selected.)
        """
        if self.complete_state:
            self.complete_previous(count=count)
        elif self.document.cursor_position_row > 0:
            self.cursor_up(count=count)
        elif not self.selection_state:
            self.history_backward(count=count)

            # Go to the start of the line?
            if go_to_start_of_line_if_history_changes:
                self.cursor_position += self.document.get_start_of_line_position()

    def auto_down(
        self, count: int = 1, go_to_start_of_line_if_history_changes: bool = False
    ) -> None:
        """
        If we're not on the last line (of a multiline input) go a line down,
        otherwise go forward in history. (If nothing is selected.)
        """
        if self.complete_state:
            self.complete_next(count=count)
        elif self.document.cursor_position_row < self.document.line_count - 1:
            self.cursor_down(count=count)
        elif not self.selection_state:
            self.history_forward(count=count)

            # Go to the start of the line?
            if go_to_start_of_line_if_history_changes:
                self.cursor_position += self.document.get_start_of_line_position()

    def delete_before_cursor(self, count: int = 1) -> str:
        """
        Delete specified number of characters before cursor and return the
        deleted text.
        """
        assert count >= 0
        deleted = ""

        if self.cursor_position > 0:
            deleted = self.text[self.cursor_position - count : self.cursor_position]

            new_text = (
                self.text[: self.cursor_position - count]
                + self.text[self.cursor_position :]
            )
            new_cursor_position = self.cursor_position - len(deleted)

            # Set new Document atomically.
            self.document = Document(new_text, new_cursor_position)

        return deleted

    def delete(self, count: int = 1) -> str:
        """
        Delete specified number of characters and Return the deleted text.
        """
        if self.cursor_position < len(self.text):
            deleted = self.document.text_after_cursor[:count]
            self.text = (
                self.text[: self.cursor_position]
                + self.text[self.cursor_position + len(deleted) :]
            )
            return deleted
        else:
            return ""

    def join_next_line(self, separator: str = " ") -> None:
        """
        Join the next line to the current one by deleting the line ending after
        the current line.
        """
        if not self.document.on_last_line:
            self.cursor_position += self.document.get_end_of_line_position()
            self.delete()

            # Remove spaces.
            self.text = (
                self.document.text_before_cursor
                + separator
                + self.document.text_after_cursor.lstrip(" ")
            )

    def join_selected_lines(self, separator: str = " ") -> None:
        """
        Join the selected lines.
        """
        assert self.selection_state

        # Get lines.
        from_, to = sorted(
            [self.cursor_position, self.selection_state.original_cursor_position]
        )

        before = self.text[:from_]
        lines = self.text[from_:to].splitlines()
        after = self.text[to:]

        # Replace leading spaces with just one space.
        lines = [l.lstrip(" ") + separator for l in lines]

        # Set new document.
        self.document = Document(
            text=before + "".join(lines) + after,
            cursor_position=len(before + "".join(lines[:-1])) - 1,
        )

    def swap_characters_before_cursor(self) -> None:
        """
        Swap the last two characters before the cursor.
        """
        pos = self.cursor_position

        if pos >= 2:
            a = self.text[pos - 2]
            b = self.text[pos - 1]

            self.text = self.text[: pos - 2] + b + a + self.text[pos:]

    def go_to_history(self, index: int) -> None:
        """
        Go to this item in the history.
        """
        if index < len(self._working_lines):
            self.working_index = index
            self.cursor_position = len(self.text)

    def complete_next(self, count: int = 1, disable_wrap_around: bool = False) -> None:
        """
        Browse to the next completions.
        (Does nothing if there are no completion.)
        """
        index: int | None

        if self.complete_state:
            completions_count = len(self.complete_state.completions)

            if self.complete_state.complete_index is None:
                index = 0
            elif self.complete_state.complete_index == completions_count - 1:
                index = None

                if disable_wrap_around:
                    return
            else:
                index = min(
                    completions_count - 1, self.complete_state.complete_index + count
                )
            self.go_to_completion(index)

    def complete_previous(
        self, count: int = 1, disable_wrap_around: bool = False
    ) -> None:
        """
        Browse to the previous completions.
        (Does nothing if there are no completion.)
        """
        index: int | None

        if self.complete_state:
            if self.complete_state.complete_index == 0:
                index = None

                if disable_wrap_around:
                    return
            elif self.complete_state.complete_index is None:
                index = len(self.complete_state.completions) - 1
            else:
                index = max(0, self.complete_state.complete_index - count)

            self.go_to_completion(index)

    def cancel_completion(self) -> None:
        """
        Cancel completion, go back to the original text.
        """
        if self.complete_state:
            self.go_to_completion(None)
            self.complete_state = None

    def _set_completions(self, completions: list[Completion]) -> CompletionState:
        """
        Start completions. (Generate list of completions and initialize.)

        By default, no completion will be selected.
        """
        self.complete_state = CompletionState(
            original_document=self.document, completions=completions
        )

        # Trigger event. This should eventually invalidate the layout.
        self.on_completions_changed.fire()

        return self.complete_state

    def start_history_lines_completion(self) -> None:
        """
        Start a completion based on all the other lines in the document and the
        history.
        """
        found_completions: set[str] = set()
        completions = []

        # For every line of the whole history, find matches with the current line.
        current_line = self.document.current_line_before_cursor.lstrip()

        for i, string in enumerate(self._working_lines):
            for j, l in enumerate(string.split("\n")):
                l = l.strip()
                if l and l.startswith(current_line):
                    # When a new line has been found.
                    if l not in found_completions:
                        found_completions.add(l)

                        # Create completion.
                        if i == self.working_index:
                            display_meta = "Current, line %s" % (j + 1)
                        else:
                            display_meta = f"History {i + 1}, line {j + 1}"

                        completions.append(
                            Completion(
                                text=l,
                                start_position=-len(current_line),
                                display_meta=display_meta,
                            )
                        )

        self._set_completions(completions=completions[::-1])
        self.go_to_completion(0)

    def go_to_completion(self, index: int | None) -> None:
        """
        Select a completion from the list of current completions.
        """
        assert self.complete_state

        # Set new completion
        state = self.complete_state
        state.go_to_index(index)

        # Set text/cursor position
        new_text, new_cursor_position = state.new_text_and_position()
        self.document = Document(new_text, new_cursor_position)

        # (changing text/cursor position will unset complete_state.)
        self.complete_state = state

    def apply_completion(self, completion: Completion) -> None:
        """
        Insert a given completion.
        """
        # If there was already a completion active, cancel that one.
        if self.complete_state:
            self.go_to_completion(None)
        self.complete_state = None

        # Insert text from the given completion.
        self.delete_before_cursor(-completion.start_position)
        self.insert_text(completion.text)

    def _set_history_search(self) -> None:
        """
        Set `history_search_text`.
        (The text before the cursor will be used for filtering the history.)
        """
        if self.enable_history_search():
            if self.history_search_text is None:
                self.history_search_text = self.document.text_before_cursor
        else:
            self.history_search_text = None

    def _history_matches(self, i: int) -> bool:
        """
        True when the current entry matches the history search.
        (when we don't have history search, it's also True.)
        """
        return self.history_search_text is None or self._working_lines[i].startswith(
            self.history_search_text
        )

    def history_forward(self, count: int = 1) -> None:
        """
        Move forwards through the history.

        :param count: Amount of items to move forward.
        """
        self._set_history_search()

        # Go forward in history.
        found_something = False

        for i in range(self.working_index + 1, len(self._working_lines)):
            if self._history_matches(i):
                self.working_index = i
                count -= 1
                found_something = True
            if count == 0:
                break

        # If we found an entry, move cursor to the end of the first line.
        if found_something:
            self.cursor_position = 0
            self.cursor_position += self.document.get_end_of_line_position()

    def history_backward(self, count: int = 1) -> None:
        """
        Move backwards through history.
        """
        self._set_history_search()

        # Go back in history.
        found_something = False

        for i in range(self.working_index - 1, -1, -1):
            if self._history_matches(i):
                self.working_index = i
                count -= 1
                found_something = True
            if count == 0:
                break

        # If we move to another entry, move cursor to the end of the line.
        if found_something:
            self.cursor_position = len(self.text)

    def yank_nth_arg(self, n: int | None = None, _yank_last_arg: bool = False) -> None:
        """
        Pick nth word from previous history entry (depending on current
        `yank_nth_arg_state`) and insert it at current position. Rotate through
        history if called repeatedly. If no `n` has been given, take the first
        argument. (The second word.)

        :param n: (None or int), The index of the word from the previous line
            to take.
        """
        assert n is None or isinstance(n, int)
        history_strings = self.history.get_strings()

        if not len(history_strings):
            return

        # Make sure we have a `YankNthArgState`.
        if self.yank_nth_arg_state is None:
            state = YankNthArgState(n=-1 if _yank_last_arg else 1)
        else:
            state = self.yank_nth_arg_state

        if n is not None:
            state.n = n

        # Get new history position.
        new_pos = state.history_position - 1
        if -new_pos > len(history_strings):
            new_pos = -1

        # Take argument from line.
        line = history_strings[new_pos]

        words = [w.strip() for w in _QUOTED_WORDS_RE.split(line)]
        words = [w for w in words if w]
        try:
            word = words[state.n]
        except IndexError:
            word = ""

        # Insert new argument.
        if state.previous_inserted_word:
            self.delete_before_cursor(len(state.previous_inserted_word))
        self.insert_text(word)

        # Save state again for next completion. (Note that the 'insert'
        # operation from above clears `self.yank_nth_arg_state`.)
        state.previous_inserted_word = word
        state.history_position = new_pos
        self.yank_nth_arg_state = state

    def yank_last_arg(self, n: int | None = None) -> None:
        """
        Like `yank_nth_arg`, but if no argument has been given, yank the last
        word by default.
        """
        self.yank_nth_arg(n=n, _yank_last_arg=True)

    def start_selection(
        self, selection_type: SelectionType = SelectionType.CHARACTERS
    ) -> None:
        """
        Take the current cursor position as the start of this selection.
        """
        self.selection_state = SelectionState(self.cursor_position, selection_type)

    def copy_selection(self, _cut: bool = False) -> ClipboardData:
        """
        Copy selected text and return :class:`.ClipboardData` instance.

        Notice that this doesn't store the copied data on the clipboard yet.
        You can store it like this:

        .. code:: python

            data = buffer.copy_selection()
            get_app().clipboard.set_data(data)
        """
        new_document, clipboard_data = self.document.cut_selection()
        if _cut:
            self.document = new_document

        self.selection_state = None
        return clipboard_data

    def cut_selection(self) -> ClipboardData:
        """
        Delete selected text and return :class:`.ClipboardData` instance.
        """
        return self.copy_selection(_cut=True)

    def paste_clipboard_data(
        self,
        data: ClipboardData,
        paste_mode: PasteMode = PasteMode.EMACS,
        count: int = 1,
    ) -> None:
        """
        Insert the data from the clipboard.
        """
        assert isinstance(data, ClipboardData)
        assert paste_mode in (PasteMode.VI_BEFORE, PasteMode.VI_AFTER, PasteMode.EMACS)

        original_document = self.document
        self.document = self.document.paste_clipboard_data(
            data, paste_mode=paste_mode, count=count
        )

        # Remember original document. This assignment should come at the end,
        # because assigning to 'document' will erase it.
        self.document_before_paste = original_document

    def newline(self, copy_margin: bool = True) -> None:
        """
        Insert a line ending at the current position.
        """
        if copy_margin:
            self.insert_text("\n" + self.document.leading_whitespace_in_current_line)
        else:
            self.insert_text("\n")

    def insert_line_above(self, copy_margin: bool = True) -> None:
        """
        Insert a new line above the current one.
        """
        if copy_margin:
            insert = self.document.leading_whitespace_in_current_line + "\n"
        else:
            insert = "\n"

        self.cursor_position += self.document.get_start_of_line_position()
        self.insert_text(insert)
        self.cursor_position -= 1

    def insert_line_below(self, copy_margin: bool = True) -> None:
        """
        Insert a new line below the current one.
        """
        if copy_margin:
            insert = "\n" + self.document.leading_whitespace_in_current_line
        else:
            insert = "\n"

        self.cursor_position += self.document.get_end_of_line_position()
        self.insert_text(insert)

    def insert_text(
        self,
        data: str,
        overwrite: bool = False,
        move_cursor: bool = True,
        fire_event: bool = True,
    ) -> None:
        """
        Insert characters at cursor position.

        :param fire_event: Fire `on_text_insert` event. This is mainly used to
            trigger autocompletion while typing.
        """
        # Original text & cursor position.
        otext = self.text
        ocpos = self.cursor_position

        # In insert/text mode.
        if overwrite:
            # Don't overwrite the newline itself. Just before the line ending,
            # it should act like insert mode.
            overwritten_text = otext[ocpos : ocpos + len(data)]
            if "\n" in overwritten_text:
                overwritten_text = overwritten_text[: overwritten_text.find("\n")]

            text = otext[:ocpos] + data + otext[ocpos + len(overwritten_text) :]
        else:
            text = otext[:ocpos] + data + otext[ocpos:]

        if move_cursor:
            cpos = self.cursor_position + len(data)
        else:
            cpos = self.cursor_position

        # Set new document.
        # (Set text and cursor position at the same time. Otherwise, setting
        # the text will fire a change event before the cursor position has been
        # set. It works better to have this atomic.)
        self.document = Document(text, cpos)

        # Fire 'on_text_insert' event.
        if fire_event:  # XXX: rename to `start_complete`.
            self.on_text_insert.fire()

            # Only complete when "complete_while_typing" is enabled.
            if self.completer and self.complete_while_typing():
                get_app().create_background_task(self._async_completer())

            # Call auto_suggest.
            if self.auto_suggest:
                get_app().create_background_task(self._async_suggester())

    def undo(self) -> None:
        # Pop from the undo-stack until we find a text that if different from
        # the current text. (The current logic of `save_to_undo_stack` will
        # cause that the top of the undo stack is usually the same as the
        # current text, so in that case we have to pop twice.)
        while self._undo_stack:
            text, pos = self._undo_stack.pop()

            if text != self.text:
                # Push current text to redo stack.
                self._redo_stack.append((self.text, self.cursor_position))

                # Set new text/cursor_position.
                self.document = Document(text, cursor_position=pos)
                break

    def redo(self) -> None:
        if self._redo_stack:
            # Copy current state on undo stack.
            self.save_to_undo_stack(clear_redo_stack=False)

            # Pop state from redo stack.
            text, pos = self._redo_stack.pop()
            self.document = Document(text, cursor_position=pos)

    def validate(self, set_cursor: bool = False) -> bool:
        """
        Returns `True` if valid.

        :param set_cursor: Set the cursor position, if an error was found.
        """
        # Don't call the validator again, if it was already called for the
        # current input.
        if self.validation_state != ValidationState.UNKNOWN:
            return self.validation_state == ValidationState.VALID

        # Call validator.
        if self.validator:
            try:
                self.validator.validate(self.document)
            except ValidationError as e:
                # Set cursor position (don't allow invalid values.)
                if set_cursor:
                    self.cursor_position = min(
                        max(0, e.cursor_position), len(self.text)
                    )

                self.validation_state = ValidationState.INVALID
                self.validation_error = e
                return False

        # Handle validation result.
        self.validation_state = ValidationState.VALID
        self.validation_error = None
        return True

    async def _validate_async(self) -> None:
        """
        Asynchronous version of `validate()`.
        This one doesn't set the cursor position.

        We have both variants, because a synchronous version is required.
        Handling the ENTER key needs to be completely synchronous, otherwise
        stuff like type-ahead is going to give very weird results. (People
        could type input while the ENTER key is still processed.)

        An asynchronous version is required if we have `validate_while_typing`
        enabled.
        """
        while True:
            # Don't call the validator again, if it was already called for the
            # current input.
            if self.validation_state != ValidationState.UNKNOWN:
                return

            # Call validator.
            error = None
            document = self.document

            if self.validator:
                try:
                    await self.validator.validate_async(self.document)
                except ValidationError as e:
                    error = e

                # If the document changed during the validation, try again.
                if self.document != document:
                    continue

            # Handle validation result.
            if error:
                self.validation_state = ValidationState.INVALID
            else:
                self.validation_state = ValidationState.VALID

            self.validation_error = error
            get_app().invalidate()  # Trigger redraw (display error).

    def append_to_history(self) -> None:
        """
        Append the current input to the history.
        """
        # Save at the tail of the history. (But don't if the last entry the
        # history is already the same.)
        if self.text:
            history_strings = self.history.get_strings()
            if not len(history_strings) or history_strings[-1] != self.text:
                self.history.append_string(self.text)

    def _search(
        self,
        search_state: SearchState,
        include_current_position: bool = False,
        count: int = 1,
    ) -> tuple[int, int] | None:
        """
        Execute search. Return (working_index, cursor_position) tuple when this
        search is applied. Returns `None` when this text cannot be found.
        """
        assert count > 0

        text = search_state.text
        direction = search_state.direction
        ignore_case = search_state.ignore_case()

        def search_once(
            working_index: int, document: Document
        ) -> tuple[int, Document] | None:
            """
            Do search one time.
            Return (working_index, document) or `None`
            """
            if direction == SearchDirection.FORWARD:
                # Try find at the current input.
                new_index = document.find(
                    text,
                    include_current_position=include_current_position,
                    ignore_case=ignore_case,
                )

                if new_index is not None:
                    return (
                        working_index,
                        Document(document.text, document.cursor_position + new_index),
                    )
                else:
                    # No match, go forward in the history. (Include len+1 to wrap around.)
                    # (Here we should always include all cursor positions, because
                    # it's a different line.)
                    for i in range(working_index + 1, len(self._working_lines) + 1):
                        i %= len(self._working_lines)

                        document = Document(self._working_lines[i], 0)
                        new_index = document.find(
                            text, include_current_position=True, ignore_case=ignore_case
                        )
                        if new_index is not None:
                            return (i, Document(document.text, new_index))
            else:
                # Try find at the current input.
                new_index = document.find_backwards(text, ignore_case=ignore_case)

                if new_index is not None:
                    return (
                        working_index,
                        Document(document.text, document.cursor_position + new_index),
                    )
                else:
                    # No match, go back in the history. (Include -1 to wrap around.)
                    for i in range(working_index - 1, -2, -1):
                        i %= len(self._working_lines)

                        document = Document(
                            self._working_lines[i], len(self._working_lines[i])
                        )
                        new_index = document.find_backwards(
                            text, ignore_case=ignore_case
                        )
                        if new_index is not None:
                            return (
                                i,
                                Document(document.text, len(document.text) + new_index),
                            )
            return None

        # Do 'count' search iterations.
        working_index = self.working_index
        document = self.document
        for _ in range(count):
            result = search_once(working_index, document)
            if result is None:
                return None  # Nothing found.
            else:
                working_index, document = result

        return (working_index, document.cursor_position)

    def document_for_search(self, search_state: SearchState) -> Document:
        """
        Return a :class:`~prompt_toolkit.document.Document` instance that has
        the text/cursor position for this search, if we would apply it. This
        will be used in the
        :class:`~prompt_toolkit.layout.BufferControl` to display feedback while
        searching.
        """
        search_result = self._search(search_state, include_current_position=True)

        if search_result is None:
            return self.document
        else:
            working_index, cursor_position = search_result

            # Keep selection, when `working_index` was not changed.
            if working_index == self.working_index:
                selection = self.selection_state
            else:
                selection = None

            return Document(
                self._working_lines[working_index], cursor_position, selection=selection
            )

    def get_search_position(
        self,
        search_state: SearchState,
        include_current_position: bool = True,
        count: int = 1,
    ) -> int:
        """
        Get the cursor position for this search.
        (This operation won't change the `working_index`. It's won't go through
        the history. Vi text objects can't span multiple items.)
        """
        search_result = self._search(
            search_state, include_current_position=include_current_position, count=count
        )

        if search_result is None:
            return self.cursor_position
        else:
            working_index, cursor_position = search_result
            return cursor_position

    def apply_search(
        self,
        search_state: SearchState,
        include_current_position: bool = True,
        count: int = 1,
    ) -> None:
        """
        Apply search. If something is found, set `working_index` and
        `cursor_position`.
        """
        search_result = self._search(
            search_state, include_current_position=include_current_position, count=count
        )

        if search_result is not None:
            working_index, cursor_position = search_result
            self.working_index = working_index
            self.cursor_position = cursor_position

    def exit_selection(self) -> None:
        self.selection_state = None

    def _editor_simple_tempfile(self) -> tuple[str, Callable[[], None]]:
        """
        Simple (file) tempfile implementation.
        Return (tempfile, cleanup_func).
        """
        suffix = to_str(self.tempfile_suffix)
        descriptor, filename = tempfile.mkstemp(suffix)

        os.write(descriptor, self.text.encode("utf-8"))
        os.close(descriptor)

        def cleanup() -> None:
            os.unlink(filename)

        return filename, cleanup

    def _editor_complex_tempfile(self) -> tuple[str, Callable[[], None]]:
        # Complex (directory) tempfile implementation.
        headtail = to_str(self.tempfile)
        if not headtail:
            # Revert to simple case.
            return self._editor_simple_tempfile()
        headtail = str(headtail)

        # Try to make according to tempfile logic.
        head, tail = os.path.split(headtail)
        if os.path.isabs(head):
            head = head[1:]

        dirpath = tempfile.mkdtemp()
        if head:
            dirpath = os.path.join(dirpath, head)
        # Assume there is no issue creating dirs in this temp dir.
        os.makedirs(dirpath)

        # Open the filename and write current text.
        filename = os.path.join(dirpath, tail)
        with open(filename, "w", encoding="utf-8") as fh:
            fh.write(self.text)

        def cleanup() -> None:
            shutil.rmtree(dirpath)

        return filename, cleanup

    def open_in_editor(self, validate_and_handle: bool = False) -> asyncio.Task[None]:
        """
        Open code in editor.

        This returns a future, and runs in a thread executor.
        """
        if self.read_only():
            raise EditReadOnlyBuffer()

        # Write current text to temporary file
        if self.tempfile:
            filename, cleanup_func = self._editor_complex_tempfile()
        else:
            filename, cleanup_func = self._editor_simple_tempfile()

        async def run() -> None:
            try:
                # Open in editor
                # (We need to use `run_in_terminal`, because not all editors go to
                # the alternate screen buffer, and some could influence the cursor
                # position.)
                success = await run_in_terminal(
                    lambda: self._open_file_in_editor(filename), in_executor=True
                )

                # Read content again.
                if success:
                    with open(filename, "rb") as f:
                        text = f.read().decode("utf-8")

                        # Drop trailing newline. (Editors are supposed to add it at the
                        # end, but we don't need it.)
                        if text.endswith("\n"):
                            text = text[:-1]

                        self.document = Document(text=text, cursor_position=len(text))

                    # Accept the input.
                    if validate_and_handle:
                        self.validate_and_handle()

            finally:
                # Clean up temp dir/file.
                cleanup_func()

        return get_app().create_background_task(run())

    def _open_file_in_editor(self, filename: str) -> bool:
        """
        Call editor executable.

        Return True when we received a zero return code.
        """
        # If the 'VISUAL' or 'EDITOR' environment variable has been set, use that.
        # Otherwise, fall back to the first available editor that we can find.
        visual = os.environ.get("VISUAL")
        editor = os.environ.get("EDITOR")

        editors = [
            visual,
            editor,
            # Order of preference.
            "/usr/bin/editor",
            "/usr/bin/nano",
            "/usr/bin/pico",
            "/usr/bin/vi",
            "/usr/bin/emacs",
        ]

        for e in editors:
            if e:
                try:
                    # Use 'shlex.split()', because $VISUAL can contain spaces
                    # and quotes.
                    returncode = subprocess.call(shlex.split(e) + [filename])
                    return returncode == 0

                except OSError:
                    # Executable does not exist, try the next one.
                    pass

        return False

    def start_completion(
        self,
        select_first: bool = False,
        select_last: bool = False,
        insert_common_part: bool = False,
        complete_event: CompleteEvent | None = None,
    ) -> None:
        """
        Start asynchronous autocompletion of this buffer.
        (This will do nothing if a previous completion was still in progress.)
        """
        # Only one of these options can be selected.
        assert select_first + select_last + insert_common_part <= 1

        get_app().create_background_task(
            self._async_completer(
                select_first=select_first,
                select_last=select_last,
                insert_common_part=insert_common_part,
                complete_event=complete_event
                or CompleteEvent(completion_requested=True),
            )
        )

    def _create_completer_coroutine(self) -> Callable[..., Coroutine[Any, Any, None]]:
        """
        Create function for asynchronous autocompletion.

        (This consumes the asynchronous completer generator, which possibly
        runs the completion algorithm in another thread.)
        """

        def completion_does_nothing(document: Document, completion: Completion) -> bool:
            """
            Return `True` if applying this completion doesn't have any effect.
            (When it doesn't insert any new text.
            """
            text_before_cursor = document.text_before_cursor
            replaced_text = text_before_cursor[
                len(text_before_cursor) + completion.start_position :
            ]
            return replaced_text == completion.text

        @_only_one_at_a_time
        async def async_completer(
            select_first: bool = False,
            select_last: bool = False,
            insert_common_part: bool = False,
            complete_event: CompleteEvent | None = None,
        ) -> None:
            document = self.document
            complete_event = complete_event or CompleteEvent(text_inserted=True)

            # Don't complete when we already have completions.
            if self.complete_state or not self.completer:
                return

            # Create an empty CompletionState.
            complete_state = CompletionState(original_document=self.document)
            self.complete_state = complete_state

            def proceed() -> bool:
                """Keep retrieving completions. Input text has not yet changed
                while generating completions."""
                return self.complete_state == complete_state

            refresh_needed = asyncio.Event()

            async def refresh_while_loading() -> None:
                """Background loop to refresh the UI at most 3 times a second
                while the completion are loading. Calling
                `on_completions_changed.fire()` for every completion that we
                receive is too expensive when there are many completions. (We
                could tune `Application.max_render_postpone_time` and
                `Application.min_redraw_interval`, but having this here is a
                better approach.)
                """
                while True:
                    self.on_completions_changed.fire()
                    refresh_needed.clear()
                    await asyncio.sleep(0.3)
                    await refresh_needed.wait()

            refresh_task = asyncio.ensure_future(refresh_while_loading())
            try:
                # Load.
                async with aclosing(
                    self.completer.get_completions_async(document, complete_event)
                ) as async_generator:
                    async for completion in async_generator:
                        complete_state.completions.append(completion)
                        refresh_needed.set()

                        # If the input text changes, abort.
                        if not proceed():
                            break

                        # Always stop at 10k completions.
                        if (
                            len(complete_state.completions)
                            >= self.max_number_of_completions
                        ):
                            break
            finally:
                refresh_task.cancel()

                # Refresh one final time after we got everything.
                self.on_completions_changed.fire()

            completions = complete_state.completions

            # When there is only one completion, which has nothing to add, ignore it.
            if len(completions) == 1 and completion_does_nothing(
                document, completions[0]
            ):
                del completions[:]

            # Set completions if the text was not yet changed.
            if proceed():
                # When no completions were found, or when the user selected
                # already a completion by using the arrow keys, don't do anything.
                if (
                    not self.complete_state
                    or self.complete_state.complete_index is not None
                ):
                    return

                # When there are no completions, reset completion state anyway.
                if not completions:
                    self.complete_state = None
                    # Render the ui if the completion menu was shown
                    # it is needed especially if there is one completion and it was deleted.
                    self.on_completions_changed.fire()
                    return

                # Select first/last or insert common part, depending on the key
                # binding. (For this we have to wait until all completions are
                # loaded.)

                if select_first:
                    self.go_to_completion(0)

                elif select_last:
                    self.go_to_completion(len(completions) - 1)

                elif insert_common_part:
                    common_part = get_common_complete_suffix(document, completions)
                    if common_part:
                        # Insert the common part, update completions.
                        self.insert_text(common_part)
                        if len(completions) > 1:
                            # (Don't call `async_completer` again, but
                            # recalculate completions. See:
                            # https://github.com/ipython/ipython/issues/9658)
                            completions[:] = [
                                c.new_completion_from_position(len(common_part))
                                for c in completions
                            ]

                            self._set_completions(completions=completions)
                        else:
                            self.complete_state = None
                    else:
                        # When we were asked to insert the "common"
                        # prefix, but there was no common suffix but
                        # still exactly one match, then select the
                        # first. (It could be that we have a completion
                        # which does * expansion, like '*.py', with
                        # exactly one match.)
                        if len(completions) == 1:
                            self.go_to_completion(0)

            else:
                # If the last operation was an insert, (not a delete), restart
                # the completion coroutine.

                if self.document.text_before_cursor == document.text_before_cursor:
                    return  # Nothing changed.

                if self.document.text_before_cursor.startswith(
                    document.text_before_cursor
                ):
                    raise _Retry

        return async_completer

    def _create_auto_suggest_coroutine(self) -> Callable[[], Coroutine[Any, Any, None]]:
        """
        Create function for asynchronous auto suggestion.
        (This can be in another thread.)
        """

        @_only_one_at_a_time
        async def async_suggestor() -> None:
            document = self.document

            # Don't suggest when we already have a suggestion.
            if self.suggestion or not self.auto_suggest:
                return

            suggestion = await self.auto_suggest.get_suggestion_async(self, document)

            # Set suggestion only if the text was not yet changed.
            if self.document == document:
                # Set suggestion and redraw interface.
                self.suggestion = suggestion
                self.on_suggestion_set.fire()
            else:
                # Otherwise, restart thread.
                raise _Retry

        return async_suggestor

    def _create_auto_validate_coroutine(
        self,
    ) -> Callable[[], Coroutine[Any, Any, None]]:
        """
        Create a function for asynchronous validation while typing.
        (This can be in another thread.)
        """

        @_only_one_at_a_time
        async def async_validator() -> None:
            await self._validate_async()

        return async_validator

    def validate_and_handle(self) -> None:
        """
        Validate buffer and handle the accept action.
        """
        valid = self.validate(set_cursor=True)

        # When the validation succeeded, accept the input.
        if valid:
            if self.accept_handler:
                keep_text = self.accept_handler(self)
            else:
                keep_text = False

            self.append_to_history()

            if not keep_text:
                self.reset()


_T = TypeVar("_T", bound=Callable[..., Coroutine[Any, Any, None]])


def _only_one_at_a_time(coroutine: _T) -> _T:
    """
    Decorator that only starts the coroutine only if the previous call has
    finished. (Used to make sure that we have only one autocompleter, auto
    suggestor and validator running at a time.)

    When the coroutine raises `_Retry`, it is restarted.
    """
    running = False

    @wraps(coroutine)
    async def new_coroutine(*a: Any, **kw: Any) -> Any:
        nonlocal running

        # Don't start a new function, if the previous is still in progress.
        if running:
            return

        running = True

        try:
            while True:
                try:
                    await coroutine(*a, **kw)
                except _Retry:
                    continue
                else:
                    return None
        finally:
            running = False

    return cast(_T, new_coroutine)


class _Retry(Exception):
    "Retry in `_only_one_at_a_time`."


def indent(buffer: Buffer, from_row: int, to_row: int, count: int = 1) -> None:
    """
    Indent text of a :class:`.Buffer` object.
    """
    current_row = buffer.document.cursor_position_row
    current_col = buffer.document.cursor_position_col
    line_range = range(from_row, to_row)

    # Apply transformation.
    indent_content = "    " * count
    new_text = buffer.transform_lines(line_range, lambda l: indent_content + l)
    buffer.document = Document(
        new_text, Document(new_text).translate_row_col_to_index(current_row, 0)
    )

    # Place cursor in the same position in text after indenting
    buffer.cursor_position += current_col + len(indent_content)


def unindent(buffer: Buffer, from_row: int, to_row: int, count: int = 1) -> None:
    """
    Unindent text of a :class:`.Buffer` object.
    """
    current_row = buffer.document.cursor_position_row
    current_col = buffer.document.cursor_position_col
    line_range = range(from_row, to_row)

    indent_content = "    " * count

    def transform(text: str) -> str:
        remove = indent_content
        if text.startswith(remove):
            return text[len(remove) :]
        else:
            return text.lstrip()

    # Apply transformation.
    new_text = buffer.transform_lines(line_range, transform)
    buffer.document = Document(
        new_text, Document(new_text).translate_row_col_to_index(current_row, 0)
    )

    # Place cursor in the same position in text after dedent
    buffer.cursor_position += current_col - len(indent_content)


def reshape_text(buffer: Buffer, from_row: int, to_row: int) -> None:
    """
    Reformat text, taking the width into account.
    `to_row` is included.
    (Vi 'gq' operator.)
    """
    lines = buffer.text.splitlines(True)
    lines_before = lines[:from_row]
    lines_after = lines[to_row + 1 :]
    lines_to_reformat = lines[from_row : to_row + 1]

    if lines_to_reformat:
        # Take indentation from the first line.
        match = re.search(r"^\s*", lines_to_reformat[0])
        length = match.end() if match else 0  # `match` can't be None, actually.

        indent = lines_to_reformat[0][:length].replace("\n", "")

        # Now, take all the 'words' from the lines to be reshaped.
        words = "".join(lines_to_reformat).split()

        # And reshape.
        width = (buffer.text_width or 80) - len(indent)
        reshaped_text = [indent]
        current_width = 0
        for w in words:
            if current_width:
                if len(w) + current_width + 1 > width:
                    reshaped_text.append("\n")
                    reshaped_text.append(indent)
                    current_width = 0
                else:
                    reshaped_text.append(" ")
                    current_width += 1

            reshaped_text.append(w)
            current_width += len(w)

        if reshaped_text[-1] != "\n":
            reshaped_text.append("\n")

        # Apply result.
        buffer.document = Document(
            text="".join(lines_before + reshaped_text + lines_after),
            cursor_position=len("".join(lines_before + reshaped_text)),
        )

# === NexusCore/openenv\Lib\site-packages\fontTools\ufoLib\glifLib.py ===
"""
Generic module for reading and writing the .glif format.

More info about the .glif format (GLyphInterchangeFormat) can be found here:

	http://unifiedfontobject.org

The main class in this module is :class:`GlyphSet`. It manages a set of .glif files
in a folder. It offers two ways to read glyph data, and one way to write
glyph data. See the class doc string for details.
"""

from __future__ import annotations

import logging
import enum
from warnings import warn
from collections import OrderedDict
import fs
import fs.base
import fs.errors
import fs.osfs
import fs.path
from fontTools.misc.textTools import tobytes
from fontTools.misc import plistlib
from fontTools.pens.pointPen import AbstractPointPen, PointToSegmentPen
from fontTools.ufoLib.errors import GlifLibError
from fontTools.ufoLib.filenames import userNameToFileName
from fontTools.ufoLib.validators import (
    genericTypeValidator,
    colorValidator,
    guidelinesValidator,
    anchorsValidator,
    identifierValidator,
    imageValidator,
    glyphLibValidator,
)
from fontTools.misc import etree
from fontTools.ufoLib import _UFOBaseIO, UFOFormatVersion
from fontTools.ufoLib.utils import numberTypes, _VersionTupleEnumMixin


__all__ = [
    "GlyphSet",
    "GlifLibError",
    "readGlyphFromString",
    "writeGlyphToString",
    "glyphNameToFileName",
]

logger = logging.getLogger(__name__)


# ---------
# Constants
# ---------

CONTENTS_FILENAME = "contents.plist"
LAYERINFO_FILENAME = "layerinfo.plist"


class GLIFFormatVersion(tuple, _VersionTupleEnumMixin, enum.Enum):
    """Class representing the versions of the .glif format supported by the UFO version in use.

    For a given :mod:`fontTools.ufoLib.UFOFormatVersion`, the :func:`supported_versions` method will
    return the supported versions of the GLIF file format. If the UFO version is unspecified, the
    :func:`supported_versions` method will return all available GLIF format versions.
    """

    FORMAT_1_0 = (1, 0)
    FORMAT_2_0 = (2, 0)

    @classmethod
    def default(cls, ufoFormatVersion=None):
        if ufoFormatVersion is not None:
            return max(cls.supported_versions(ufoFormatVersion))
        return super().default()

    @classmethod
    def supported_versions(cls, ufoFormatVersion=None):
        if ufoFormatVersion is None:
            # if ufo format unspecified, return all the supported GLIF formats
            return super().supported_versions()
        # else only return the GLIF formats supported by the given UFO format
        versions = {cls.FORMAT_1_0}
        if ufoFormatVersion >= UFOFormatVersion.FORMAT_3_0:
            versions.add(cls.FORMAT_2_0)
        return frozenset(versions)


# workaround for py3.11, see https://github.com/fonttools/fonttools/pull/2655
GLIFFormatVersion.__str__ = _VersionTupleEnumMixin.__str__


# ------------
# Simple Glyph
# ------------


class Glyph:
    """
    Minimal glyph object. It has no glyph attributes until either
    the draw() or the drawPoints() method has been called.
    """

    def __init__(self, glyphName, glyphSet):
        self.glyphName = glyphName
        self.glyphSet = glyphSet

    def draw(self, pen, outputImpliedClosingLine=False):
        """
        Draw this glyph onto a *FontTools* Pen.
        """
        pointPen = PointToSegmentPen(
            pen, outputImpliedClosingLine=outputImpliedClosingLine
        )
        self.drawPoints(pointPen)

    def drawPoints(self, pointPen):
        """
        Draw this glyph onto a PointPen.
        """
        self.glyphSet.readGlyph(self.glyphName, self, pointPen)


# ---------
# Glyph Set
# ---------


class GlyphSet(_UFOBaseIO):
    """
    GlyphSet manages a set of .glif files inside one directory.

    GlyphSet's constructor takes a path to an existing directory as it's
    first argument. Reading glyph data can either be done through the
    readGlyph() method, or by using GlyphSet's dictionary interface, where
    the keys are glyph names and the values are (very) simple glyph objects.

    To write a glyph to the glyph set, you use the writeGlyph() method.
    The simple glyph objects returned through the dict interface do not
    support writing, they are just a convenient way to get at the glyph data.
    """

    glyphClass = Glyph

    def __init__(
        self,
        path,
        glyphNameToFileNameFunc=None,
        ufoFormatVersion=None,
        validateRead=True,
        validateWrite=True,
        expectContentsFile=False,
    ):
        """
        'path' should be a path (string) to an existing local directory, or
        an instance of fs.base.FS class.

        The optional 'glyphNameToFileNameFunc' argument must be a callback
        function that takes two arguments: a glyph name and a list of all
        existing filenames (if any exist). It should return a file name
        (including the .glif extension). The glyphNameToFileName function
        is called whenever a file name is created for a given glyph name.

        ``validateRead`` will validate read operations. Its default is ``True``.
        ``validateWrite`` will validate write operations. Its default is ``True``.
        ``expectContentsFile`` will raise a GlifLibError if a contents.plist file is
        not found on the glyph set file system. This should be set to ``True`` if you
        are reading an existing UFO and ``False`` if you create a fresh	glyph set.
        """
        try:
            ufoFormatVersion = UFOFormatVersion(ufoFormatVersion)
        except ValueError as e:
            from fontTools.ufoLib.errors import UnsupportedUFOFormat

            raise UnsupportedUFOFormat(
                f"Unsupported UFO format: {ufoFormatVersion!r}"
            ) from e

        if hasattr(path, "__fspath__"):  # support os.PathLike objects
            path = path.__fspath__()

        if isinstance(path, str):
            try:
                filesystem = fs.osfs.OSFS(path)
            except fs.errors.CreateFailed:
                raise GlifLibError("No glyphs directory '%s'" % path)
            self._shouldClose = True
        elif isinstance(path, fs.base.FS):
            filesystem = path
            try:
                filesystem.check()
            except fs.errors.FilesystemClosed:
                raise GlifLibError("the filesystem '%s' is closed" % filesystem)
            self._shouldClose = False
        else:
            raise TypeError(
                "Expected a path string or fs object, found %s" % type(path).__name__
            )
        try:
            path = filesystem.getsyspath("/")
        except fs.errors.NoSysPath:
            # network or in-memory FS may not map to the local one
            path = str(filesystem)
        # 'dirName' is kept for backward compatibility only, but it's DEPRECATED
        # as it's not guaranteed that it maps to an existing OSFS directory.
        # Client could use the FS api via the `self.fs` attribute instead.
        self.dirName = fs.path.parts(path)[-1]
        self.fs = filesystem
        # if glyphSet contains no 'contents.plist', we consider it empty
        self._havePreviousFile = filesystem.exists(CONTENTS_FILENAME)
        if expectContentsFile and not self._havePreviousFile:
            raise GlifLibError(f"{CONTENTS_FILENAME} is missing.")
        # attribute kept for backward compatibility
        self.ufoFormatVersion = ufoFormatVersion.major
        self.ufoFormatVersionTuple = ufoFormatVersion
        if glyphNameToFileNameFunc is None:
            glyphNameToFileNameFunc = glyphNameToFileName
        self.glyphNameToFileName = glyphNameToFileNameFunc
        self._validateRead = validateRead
        self._validateWrite = validateWrite
        self._existingFileNames: set[str] | None = None
        self._reverseContents = None

        self.rebuildContents()

    def rebuildContents(self, validateRead=None):
        """
        Rebuild the contents dict by loading contents.plist.

        ``validateRead`` will validate the data, by default it is set to the
        class's ``validateRead`` value, can be overridden.
        """
        if validateRead is None:
            validateRead = self._validateRead
        contents = self._getPlist(CONTENTS_FILENAME, {})
        # validate the contents
        if validateRead:
            invalidFormat = False
            if not isinstance(contents, dict):
                invalidFormat = True
            else:
                for name, fileName in contents.items():
                    if not isinstance(name, str):
                        invalidFormat = True
                    if not isinstance(fileName, str):
                        invalidFormat = True
                    elif not self.fs.exists(fileName):
                        raise GlifLibError(
                            "%s references a file that does not exist: %s"
                            % (CONTENTS_FILENAME, fileName)
                        )
            if invalidFormat:
                raise GlifLibError("%s is not properly formatted" % CONTENTS_FILENAME)
        self.contents = contents
        self._existingFileNames = None
        self._reverseContents = None

    def getReverseContents(self):
        """
        Return a reversed dict of self.contents, mapping file names to
        glyph names. This is primarily an aid for custom glyph name to file
        name schemes that want to make sure they don't generate duplicate
        file names. The file names are converted to lowercase so we can
        reliably check for duplicates that only differ in case, which is
        important for case-insensitive file systems.
        """
        if self._reverseContents is None:
            d = {}
            for k, v in self.contents.items():
                d[v.lower()] = k
            self._reverseContents = d
        return self._reverseContents

    def writeContents(self):
        """
        Write the contents.plist file out to disk. Call this method when
        you're done writing glyphs.
        """
        self._writePlist(CONTENTS_FILENAME, self.contents)

    # layer info

    def readLayerInfo(self, info, validateRead=None):
        """
        ``validateRead`` will validate the data, by default it is set to the
        class's ``validateRead`` value, can be overridden.
        """
        if validateRead is None:
            validateRead = self._validateRead
        infoDict = self._getPlist(LAYERINFO_FILENAME, {})
        if validateRead:
            if not isinstance(infoDict, dict):
                raise GlifLibError("layerinfo.plist is not properly formatted.")
            infoDict = validateLayerInfoVersion3Data(infoDict)
        # populate the object
        for attr, value in infoDict.items():
            try:
                setattr(info, attr, value)
            except AttributeError:
                raise GlifLibError(
                    "The supplied layer info object does not support setting a necessary attribute (%s)."
                    % attr
                )

    def writeLayerInfo(self, info, validateWrite=None):
        """
        ``validateWrite`` will validate the data, by default it is set to the
        class's ``validateWrite`` value, can be overridden.
        """
        if validateWrite is None:
            validateWrite = self._validateWrite
        if self.ufoFormatVersionTuple.major < 3:
            raise GlifLibError(
                "layerinfo.plist is not allowed in UFO %d."
                % self.ufoFormatVersionTuple.major
            )
        # gather data
        infoData = {}
        for attr in layerInfoVersion3ValueData.keys():
            if hasattr(info, attr):
                try:
                    value = getattr(info, attr)
                except AttributeError:
                    raise GlifLibError(
                        "The supplied info object does not support getting a necessary attribute (%s)."
                        % attr
                    )
                if value is None or (attr == "lib" and not value):
                    continue
                infoData[attr] = value
        if infoData:
            # validate
            if validateWrite:
                infoData = validateLayerInfoVersion3Data(infoData)
            # write file
            self._writePlist(LAYERINFO_FILENAME, infoData)
        elif self._havePreviousFile and self.fs.exists(LAYERINFO_FILENAME):
            # data empty, remove existing file
            self.fs.remove(LAYERINFO_FILENAME)

    def getGLIF(self, glyphName):
        """
        Get the raw GLIF text for a given glyph name. This only works
        for GLIF files that are already on disk.

        This method is useful in situations when the raw XML needs to be
        read from a glyph set for a particular glyph before fully parsing
        it into an object structure via the readGlyph method.

        Raises KeyError if 'glyphName' is not in contents.plist, or
        GlifLibError if the file associated with can't be found.
        """
        fileName = self.contents[glyphName]
        try:
            return self.fs.readbytes(fileName)
        except fs.errors.ResourceNotFound:
            raise GlifLibError(
                "The file '%s' associated with glyph '%s' in contents.plist "
                "does not exist on %s" % (fileName, glyphName, self.fs)
            )

    def getGLIFModificationTime(self, glyphName):
        """
        Returns the modification time for the GLIF file with 'glyphName', as
        a floating point number giving the number of seconds since the epoch.
        Return None if the associated file does not exist or the underlying
        filesystem does not support getting modified times.
        Raises KeyError if the glyphName is not in contents.plist.
        """
        fileName = self.contents[glyphName]
        return self.getFileModificationTime(fileName)

    # reading/writing API

    def readGlyph(self, glyphName, glyphObject=None, pointPen=None, validate=None):
        """
        Read a .glif file for 'glyphName' from the glyph set. The
        'glyphObject' argument can be any kind of object (even None);
        the readGlyph() method will attempt to set the following
        attributes on it:

        width
                the advance width of the glyph
        height
                the advance height of the glyph
        unicodes
                a list of unicode values for this glyph
        note
                a string
        lib
                a dictionary containing custom data
        image
                a dictionary containing image data
        guidelines
                a list of guideline data dictionaries
        anchors
                a list of anchor data dictionaries

        All attributes are optional, in two ways:

        1) An attribute *won't* be set if the .glif file doesn't
           contain data for it. 'glyphObject' will have to deal
           with default values itself.
        2) If setting the attribute fails with an AttributeError
           (for example if the 'glyphObject' attribute is read-
           only), readGlyph() will not propagate that exception,
           but ignore that attribute.

        To retrieve outline information, you need to pass an object
        conforming to the PointPen protocol as the 'pointPen' argument.
        This argument may be None if you don't need the outline data.

        readGlyph() will raise KeyError if the glyph is not present in
        the glyph set.

        ``validate`` will validate the data, by default it is set to the
        class's ``validateRead`` value, can be overridden.
        """
        if validate is None:
            validate = self._validateRead
        text = self.getGLIF(glyphName)
        try:
            tree = _glifTreeFromString(text)
            formatVersions = GLIFFormatVersion.supported_versions(
                self.ufoFormatVersionTuple
            )
            _readGlyphFromTree(
                tree,
                glyphObject,
                pointPen,
                formatVersions=formatVersions,
                validate=validate,
            )
        except GlifLibError as glifLibError:
            # Re-raise with a note that gives extra context, describing where
            # the error occurred.
            fileName = self.contents[glyphName]
            try:
                glifLocation = f"'{self.fs.getsyspath(fileName)}'"
            except fs.errors.NoSysPath:
                # Network or in-memory FS may not map to a local path, so use
                # the best string representation we have.
                glifLocation = f"'{fileName}' from '{str(self.fs)}'"

            glifLibError._add_note(
                f"The issue is in glyph '{glyphName}', located in {glifLocation}."
            )
            raise

    def writeGlyph(
        self,
        glyphName,
        glyphObject=None,
        drawPointsFunc=None,
        formatVersion=None,
        validate=None,
    ):
        """
        Write a .glif file for 'glyphName' to the glyph set. The
        'glyphObject' argument can be any kind of object (even None);
        the writeGlyph() method will attempt to get the following
        attributes from it:

        width
                the advance width of the glyph
        height
                the advance height of the glyph
        unicodes
                a list of unicode values for this glyph
        note
                a string
        lib
                a dictionary containing custom data
        image
                a dictionary containing image data
        guidelines
                a list of guideline data dictionaries
        anchors
                a list of anchor data dictionaries

        All attributes are optional: if 'glyphObject' doesn't
        have the attribute, it will simply be skipped.

        To write outline data to the .glif file, writeGlyph() needs
        a function (any callable object actually) that will take one
        argument: an object that conforms to the PointPen protocol.
        The function will be called by writeGlyph(); it has to call the
        proper PointPen methods to transfer the outline to the .glif file.

        The GLIF format version will be chosen based on the ufoFormatVersion
        passed during the creation of this object. If a particular format
        version is desired, it can be passed with the formatVersion argument.
        The formatVersion argument accepts either a tuple of integers for
        (major, minor), or a single integer for the major digit only (with
        minor digit implied as 0).

        An UnsupportedGLIFFormat exception is raised if the requested GLIF
        formatVersion is not supported.

        ``validate`` will validate the data, by default it is set to the
        class's ``validateWrite`` value, can be overridden.
        """
        if formatVersion is None:
            formatVersion = GLIFFormatVersion.default(self.ufoFormatVersionTuple)
        else:
            try:
                formatVersion = GLIFFormatVersion(formatVersion)
            except ValueError as e:
                from fontTools.ufoLib.errors import UnsupportedGLIFFormat

                raise UnsupportedGLIFFormat(
                    f"Unsupported GLIF format version: {formatVersion!r}"
                ) from e
        if formatVersion not in GLIFFormatVersion.supported_versions(
            self.ufoFormatVersionTuple
        ):
            from fontTools.ufoLib.errors import UnsupportedGLIFFormat

            raise UnsupportedGLIFFormat(
                f"Unsupported GLIF format version ({formatVersion!s}) "
                f"for UFO format version {self.ufoFormatVersionTuple!s}."
            )
        if validate is None:
            validate = self._validateWrite
        fileName = self.contents.get(glyphName)
        if fileName is None:
            if self._existingFileNames is None:
                self._existingFileNames = {
                    fileName.lower() for fileName in self.contents.values()
                }
            fileName = self.glyphNameToFileName(glyphName, self._existingFileNames)
            self.contents[glyphName] = fileName
            self._existingFileNames.add(fileName.lower())
            if self._reverseContents is not None:
                self._reverseContents[fileName.lower()] = glyphName
        data = _writeGlyphToBytes(
            glyphName,
            glyphObject,
            drawPointsFunc,
            formatVersion=formatVersion,
            validate=validate,
        )
        if (
            self._havePreviousFile
            and self.fs.exists(fileName)
            and data == self.fs.readbytes(fileName)
        ):
            return
        self.fs.writebytes(fileName, data)

    def deleteGlyph(self, glyphName):
        """Permanently delete the glyph from the glyph set on disk. Will
        raise KeyError if the glyph is not present in the glyph set.
        """
        fileName = self.contents[glyphName]
        self.fs.remove(fileName)
        if self._existingFileNames is not None:
            self._existingFileNames.remove(fileName.lower())
        if self._reverseContents is not None:
            del self._reverseContents[fileName.lower()]
        del self.contents[glyphName]

    # dict-like support

    def keys(self):
        return list(self.contents.keys())

    def has_key(self, glyphName):
        return glyphName in self.contents

    __contains__ = has_key

    def __len__(self):
        return len(self.contents)

    def __getitem__(self, glyphName):
        if glyphName not in self.contents:
            raise KeyError(glyphName)
        return self.glyphClass(glyphName, self)

    # quickly fetch unicode values

    def getUnicodes(self, glyphNames=None):
        """
        Return a dictionary that maps glyph names to lists containing
        the unicode value[s] for that glyph, if any. This parses the .glif
        files partially, so it is a lot faster than parsing all files completely.
        By default this checks all glyphs, but a subset can be passed with glyphNames.
        """
        unicodes = {}
        if glyphNames is None:
            glyphNames = self.contents.keys()
        for glyphName in glyphNames:
            text = self.getGLIF(glyphName)
            unicodes[glyphName] = _fetchUnicodes(text)
        return unicodes

    def getComponentReferences(self, glyphNames=None):
        """
        Return a dictionary that maps glyph names to lists containing the
        base glyph name of components in the glyph. This parses the .glif
        files partially, so it is a lot faster than parsing all files completely.
        By default this checks all glyphs, but a subset can be passed with glyphNames.
        """
        components = {}
        if glyphNames is None:
            glyphNames = self.contents.keys()
        for glyphName in glyphNames:
            text = self.getGLIF(glyphName)
            components[glyphName] = _fetchComponentBases(text)
        return components

    def getImageReferences(self, glyphNames=None):
        """
        Return a dictionary that maps glyph names to the file name of the image
        referenced by the glyph. This parses the .glif files partially, so it is a
        lot faster than parsing all files completely.
        By default this checks all glyphs, but a subset can be passed with glyphNames.
        """
        images = {}
        if glyphNames is None:
            glyphNames = self.contents.keys()
        for glyphName in glyphNames:
            text = self.getGLIF(glyphName)
            images[glyphName] = _fetchImageFileName(text)
        return images

    def close(self):
        if self._shouldClose:
            self.fs.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()


# -----------------------
# Glyph Name to File Name
# -----------------------


def glyphNameToFileName(glyphName, existingFileNames):
    """
    Wrapper around the userNameToFileName function in filenames.py

    Note that existingFileNames should be a set for large glyphsets
    or performance will suffer.
    """
    if existingFileNames is None:
        existingFileNames = set()
    return userNameToFileName(glyphName, existing=existingFileNames, suffix=".glif")


# -----------------------
# GLIF To and From String
# -----------------------


def readGlyphFromString(
    aString,
    glyphObject=None,
    pointPen=None,
    formatVersions=None,
    validate=True,
):
    """
    Read .glif data from a string into a glyph object.

    The 'glyphObject' argument can be any kind of object (even None);
    the readGlyphFromString() method will attempt to set the following
    attributes on it:

    width
            the advance width of the glyph
    height
            the advance height of the glyph
    unicodes
            a list of unicode values for this glyph
    note
            a string
    lib
            a dictionary containing custom data
    image
            a dictionary containing image data
    guidelines
            a list of guideline data dictionaries
    anchors
            a list of anchor data dictionaries

    All attributes are optional, in two ways:

    1) An attribute *won't* be set if the .glif file doesn't
       contain data for it. 'glyphObject' will have to deal
       with default values itself.
    2) If setting the attribute fails with an AttributeError
       (for example if the 'glyphObject' attribute is read-
       only), readGlyphFromString() will not propagate that
       exception, but ignore that attribute.

    To retrieve outline information, you need to pass an object
    conforming to the PointPen protocol as the 'pointPen' argument.
    This argument may be None if you don't need the outline data.

    The formatVersions optional argument define the GLIF format versions
    that are allowed to be read.
    The type is Optional[Iterable[Tuple[int, int], int]]. It can contain
    either integers (for the major versions to be allowed, with minor
    digits defaulting to 0), or tuples of integers to specify both
    (major, minor) versions.
    By default when formatVersions is None all the GLIF format versions
    currently defined are allowed to be read.

    ``validate`` will validate the read data. It is set to ``True`` by default.
    """
    tree = _glifTreeFromString(aString)

    if formatVersions is None:
        validFormatVersions = GLIFFormatVersion.supported_versions()
    else:
        validFormatVersions, invalidFormatVersions = set(), set()
        for v in formatVersions:
            try:
                formatVersion = GLIFFormatVersion(v)
            except ValueError:
                invalidFormatVersions.add(v)
            else:
                validFormatVersions.add(formatVersion)
        if not validFormatVersions:
            raise ValueError(
                "None of the requested GLIF formatVersions are supported: "
                f"{formatVersions!r}"
            )

    _readGlyphFromTree(
        tree,
        glyphObject,
        pointPen,
        formatVersions=validFormatVersions,
        validate=validate,
    )


def _writeGlyphToBytes(
    glyphName,
    glyphObject=None,
    drawPointsFunc=None,
    writer=None,
    formatVersion=None,
    validate=True,
):
    """Return .glif data for a glyph as a UTF-8 encoded bytes string."""
    try:
        formatVersion = GLIFFormatVersion(formatVersion)
    except ValueError:
        from fontTools.ufoLib.errors import UnsupportedGLIFFormat

        raise UnsupportedGLIFFormat(
            "Unsupported GLIF format version: {formatVersion!r}"
        )
    # start
    if validate and not isinstance(glyphName, str):
        raise GlifLibError("The glyph name is not properly formatted.")
    if validate and len(glyphName) == 0:
        raise GlifLibError("The glyph name is empty.")
    glyphAttrs = OrderedDict(
        [("name", glyphName), ("format", repr(formatVersion.major))]
    )
    if formatVersion.minor != 0:
        glyphAttrs["formatMinor"] = repr(formatVersion.minor)
    root = etree.Element("glyph", glyphAttrs)
    identifiers = set()
    # advance
    _writeAdvance(glyphObject, root, validate)
    # unicodes
    if getattr(glyphObject, "unicodes", None):
        _writeUnicodes(glyphObject, root, validate)
    # note
    if getattr(glyphObject, "note", None):
        _writeNote(glyphObject, root, validate)
    # image
    if formatVersion.major >= 2 and getattr(glyphObject, "image", None):
        _writeImage(glyphObject, root, validate)
    # guidelines
    if formatVersion.major >= 2 and getattr(glyphObject, "guidelines", None):
        _writeGuidelines(glyphObject, root, identifiers, validate)
    # anchors
    anchors = getattr(glyphObject, "anchors", None)
    if formatVersion.major >= 2 and anchors:
        _writeAnchors(glyphObject, root, identifiers, validate)
    # outline
    if drawPointsFunc is not None:
        outline = etree.SubElement(root, "outline")
        pen = GLIFPointPen(outline, identifiers=identifiers, validate=validate)
        drawPointsFunc(pen)
        if formatVersion.major == 1 and anchors:
            _writeAnchorsFormat1(pen, anchors, validate)
        # prevent lxml from writing self-closing tags
        if not len(outline):
            outline.text = "\n  "
    # lib
    if getattr(glyphObject, "lib", None):
        _writeLib(glyphObject, root, validate)
    # return the text
    data = etree.tostring(
        root, encoding="UTF-8", xml_declaration=True, pretty_print=True
    )
    return data


def writeGlyphToString(
    glyphName,
    glyphObject=None,
    drawPointsFunc=None,
    formatVersion=None,
    validate=True,
):
    """
    Return .glif data for a glyph as a string. The XML declaration's
    encoding is always set to "UTF-8".
    The 'glyphObject' argument can be any kind of object (even None);
    the writeGlyphToString() method will attempt to get the following
    attributes from it:

    width
            the advance width of the glyph
    height
            the advance height of the glyph
    unicodes
            a list of unicode values for this glyph
    note
            a string
    lib
            a dictionary containing custom data
    image
            a dictionary containing image data
    guidelines
            a list of guideline data dictionaries
    anchors
            a list of anchor data dictionaries

    All attributes are optional: if 'glyphObject' doesn't
    have the attribute, it will simply be skipped.

    To write outline data to the .glif file, writeGlyphToString() needs
    a function (any callable object actually) that will take one
    argument: an object that conforms to the PointPen protocol.
    The function will be called by writeGlyphToString(); it has to call the
    proper PointPen methods to transfer the outline to the .glif file.

    The GLIF format version can be specified with the formatVersion argument.
    This accepts either a tuple of integers for (major, minor), or a single
    integer for the major digit only (with minor digit implied as 0).
    By default when formatVesion is None the latest GLIF format version will
    be used; currently it's 2.0, which is equivalent to formatVersion=(2, 0).

    An UnsupportedGLIFFormat exception is raised if the requested UFO
    formatVersion is not supported.

    ``validate`` will validate the written data. It is set to ``True`` by default.
    """
    data = _writeGlyphToBytes(
        glyphName,
        glyphObject=glyphObject,
        drawPointsFunc=drawPointsFunc,
        formatVersion=formatVersion,
        validate=validate,
    )
    return data.decode("utf-8")


def _writeAdvance(glyphObject, element, validate):
    width = getattr(glyphObject, "width", None)
    if width is not None:
        if validate and not isinstance(width, numberTypes):
            raise GlifLibError("width attribute must be int or float")
        if width == 0:
            width = None
    height = getattr(glyphObject, "height", None)
    if height is not None:
        if validate and not isinstance(height, numberTypes):
            raise GlifLibError("height attribute must be int or float")
        if height == 0:
            height = None
    if width is not None and height is not None:
        etree.SubElement(
            element,
            "advance",
            OrderedDict([("height", repr(height)), ("width", repr(width))]),
        )
    elif width is not None:
        etree.SubElement(element, "advance", dict(width=repr(width)))
    elif height is not None:
        etree.SubElement(element, "advance", dict(height=repr(height)))


def _writeUnicodes(glyphObject, element, validate):
    unicodes = getattr(glyphObject, "unicodes", None)
    if validate and isinstance(unicodes, int):
        unicodes = [unicodes]
    seen = set()
    for code in unicodes:
        if validate and not isinstance(code, int):
            raise GlifLibError("unicode values must be int")
        if code in seen:
            continue
        seen.add(code)
        hexCode = "%04X" % code
        etree.SubElement(element, "unicode", dict(hex=hexCode))


def _writeNote(glyphObject, element, validate):
    note = getattr(glyphObject, "note", None)
    if validate and not isinstance(note, str):
        raise GlifLibError("note attribute must be str")
    note = note.strip()
    note = "\n" + note + "\n"
    etree.SubElement(element, "note").text = note


def _writeImage(glyphObject, element, validate):
    image = getattr(glyphObject, "image", None)
    if validate and not imageValidator(image):
        raise GlifLibError(
            "image attribute must be a dict or dict-like object with the proper structure."
        )
    attrs = OrderedDict([("fileName", image["fileName"])])
    for attr, default in _transformationInfo:
        value = image.get(attr, default)
        if value != default:
            attrs[attr] = repr(value)
    color = image.get("color")
    if color is not None:
        attrs["color"] = color
    etree.SubElement(element, "image", attrs)


def _writeGuidelines(glyphObject, element, identifiers, validate):
    guidelines = getattr(glyphObject, "guidelines", [])
    if validate and not guidelinesValidator(guidelines):
        raise GlifLibError("guidelines attribute does not have the proper structure.")
    for guideline in guidelines:
        attrs = OrderedDict()
        x = guideline.get("x")
        if x is not None:
            attrs["x"] = repr(x)
        y = guideline.get("y")
        if y is not None:
            attrs["y"] = repr(y)
        angle = guideline.get("angle")
        if angle is not None:
            attrs["angle"] = repr(angle)
        name = guideline.get("name")
        if name is not None:
            attrs["name"] = name
        color = guideline.get("color")
        if color is not None:
            attrs["color"] = color
        identifier = guideline.get("identifier")
        if identifier is not None:
            if validate and identifier in identifiers:
                raise GlifLibError("identifier used more than once: %s" % identifier)
            attrs["identifier"] = identifier
            identifiers.add(identifier)
        etree.SubElement(element, "guideline", attrs)


def _writeAnchorsFormat1(pen, anchors, validate):
    if validate and not anchorsValidator(anchors):
        raise GlifLibError("anchors attribute does not have the proper structure.")
    for anchor in anchors:
        attrs = {}
        x = anchor["x"]
        attrs["x"] = repr(x)
        y = anchor["y"]
        attrs["y"] = repr(y)
        name = anchor.get("name")
        if name is not None:
            attrs["name"] = name
        pen.beginPath()
        pen.addPoint((x, y), segmentType="move", name=name)
        pen.endPath()


def _writeAnchors(glyphObject, element, identifiers, validate):
    anchors = getattr(glyphObject, "anchors", [])
    if validate and not anchorsValidator(anchors):
        raise GlifLibError("anchors attribute does not have the proper structure.")
    for anchor in anchors:
        attrs = OrderedDict()
        x = anchor["x"]
        attrs["x"] = repr(x)
        y = anchor["y"]
        attrs["y"] = repr(y)
        name = anchor.get("name")
        if name is not None:
            attrs["name"] = name
        color = anchor.get("color")
        if color is not None:
            attrs["color"] = color
        identifier = anchor.get("identifier")
        if identifier is not None:
            if validate and identifier in identifiers:
                raise GlifLibError("identifier used more than once: %s" % identifier)
            attrs["identifier"] = identifier
            identifiers.add(identifier)
        etree.SubElement(element, "anchor", attrs)


def _writeLib(glyphObject, element, validate):
    lib = getattr(glyphObject, "lib", None)
    if not lib:
        # don't write empty lib
        return
    if validate:
        valid, message = glyphLibValidator(lib)
        if not valid:
            raise GlifLibError(message)
    if not isinstance(lib, dict):
        lib = dict(lib)
    # plist inside GLIF begins with 2 levels of indentation
    e = plistlib.totree(lib, indent_level=2)
    etree.SubElement(element, "lib").append(e)


# -----------------------
# layerinfo.plist Support
# -----------------------

layerInfoVersion3ValueData = {
    "color": dict(type=str, valueValidator=colorValidator),
    "lib": dict(type=dict, valueValidator=genericTypeValidator),
}


def validateLayerInfoVersion3ValueForAttribute(attr, value):
    """
    This performs very basic validation of the value for attribute
    following the UFO 3 fontinfo.plist specification. The results
    of this should not be interpretted as *correct* for the font
    that they are part of. This merely indicates that the value
    is of the proper type and, where the specification defines
    a set range of possible values for an attribute, that the
    value is in the accepted range.
    """
    if attr not in layerInfoVersion3ValueData:
        return False
    dataValidationDict = layerInfoVersion3ValueData[attr]
    valueType = dataValidationDict.get("type")
    validator = dataValidationDict.get("valueValidator")
    valueOptions = dataValidationDict.get("valueOptions")
    # have specific options for the validator
    if valueOptions is not None:
        isValidValue = validator(value, valueOptions)
    # no specific options
    else:
        if validator == genericTypeValidator:
            isValidValue = validator(value, valueType)
        else:
            isValidValue = validator(value)
    return isValidValue


def validateLayerInfoVersion3Data(infoData):
    """
    This performs very basic validation of the value for infoData
    following the UFO 3 layerinfo.plist specification. The results
    of this should not be interpretted as *correct* for the font
    that they are part of. This merely indicates that the values
    are of the proper type and, where the specification defines
    a set range of possible values for an attribute, that the
    value is in the accepted range.
    """
    for attr, value in infoData.items():
        if attr not in layerInfoVersion3ValueData:
            raise GlifLibError("Unknown attribute %s." % attr)
        isValidValue = validateLayerInfoVersion3ValueForAttribute(attr, value)
        if not isValidValue:
            raise GlifLibError(f"Invalid value for attribute {attr} ({value!r}).")
    return infoData


# -----------------
# GLIF Tree Support
# -----------------


def _glifTreeFromFile(aFile):
    if etree._have_lxml:
        tree = etree.parse(aFile, parser=etree.XMLParser(remove_comments=True))
    else:
        tree = etree.parse(aFile)
    root = tree.getroot()
    if root.tag != "glyph":
        raise GlifLibError("The GLIF is not properly formatted.")
    if root.text and root.text.strip() != "":
        raise GlifLibError("Invalid GLIF structure.")
    return root


def _glifTreeFromString(aString):
    data = tobytes(aString, encoding="utf-8")
    try:
        if etree._have_lxml:
            root = etree.fromstring(data, parser=etree.XMLParser(remove_comments=True))
        else:
            root = etree.fromstring(data)
    except Exception as etree_exception:
        raise GlifLibError("GLIF contains invalid XML.") from etree_exception

    if root.tag != "glyph":
        raise GlifLibError("The GLIF is not properly formatted.")
    if root.text and root.text.strip() != "":
        raise GlifLibError("Invalid GLIF structure.")
    return root


def _readGlyphFromTree(
    tree,
    glyphObject=None,
    pointPen=None,
    formatVersions=GLIFFormatVersion.supported_versions(),
    validate=True,
):
    # check the format version
    formatVersionMajor = tree.get("format")
    if validate and formatVersionMajor is None:
        raise GlifLibError("Unspecified format version in GLIF.")
    formatVersionMinor = tree.get("formatMinor", 0)
    try:
        formatVersion = GLIFFormatVersion(
            (int(formatVersionMajor), int(formatVersionMinor))
        )
    except ValueError as e:
        msg = "Unsupported GLIF format: %s.%s" % (
            formatVersionMajor,
            formatVersionMinor,
        )
        if validate:
            from fontTools.ufoLib.errors import UnsupportedGLIFFormat

            raise UnsupportedGLIFFormat(msg) from e
        # warn but continue using the latest supported format
        formatVersion = GLIFFormatVersion.default()
        logger.warning(
            "%s. Assuming the latest supported version (%s). "
            "Some data may be skipped or parsed incorrectly.",
            msg,
            formatVersion,
        )

    if validate and formatVersion not in formatVersions:
        raise GlifLibError(f"Forbidden GLIF format version: {formatVersion!s}")

    try:
        readGlyphFromTree = _READ_GLYPH_FROM_TREE_FUNCS[formatVersion]
    except KeyError:
        raise NotImplementedError(formatVersion)

    readGlyphFromTree(
        tree=tree,
        glyphObject=glyphObject,
        pointPen=pointPen,
        validate=validate,
        formatMinor=formatVersion.minor,
    )


def _readGlyphFromTreeFormat1(
    tree, glyphObject=None, pointPen=None, validate=None, **kwargs
):
    # get the name
    _readName(glyphObject, tree, validate)
    # populate the sub elements
    unicodes = []
    haveSeenAdvance = haveSeenOutline = haveSeenLib = haveSeenNote = False
    for element in tree:
        if element.tag == "outline":
            if validate:
                if haveSeenOutline:
                    raise GlifLibError("The outline element occurs more than once.")
                if element.attrib:
                    raise GlifLibError(
                        "The outline element contains unknown attributes."
                    )
                if element.text and element.text.strip() != "":
                    raise GlifLibError("Invalid outline structure.")
            haveSeenOutline = True
            buildOutlineFormat1(glyphObject, pointPen, element, validate)
        elif glyphObject is None:
            continue
        elif element.tag == "advance":
            if validate and haveSeenAdvance:
                raise GlifLibError("The advance element occurs more than once.")
            haveSeenAdvance = True
            _readAdvance(glyphObject, element)
        elif element.tag == "unicode":
            v = element.get("hex")
            if v is None:
                raise GlifLibError(
                    "A unicode element is missing its required hex attribute."
                )
            try:
                v = int(v, 16)
                if v not in unicodes:
                    unicodes.append(v)
            except ValueError:
                raise GlifLibError(
                    "Illegal value for hex attribute of unicode element."
                )
        elif element.tag == "note":
            if validate and haveSeenNote:
                raise GlifLibError("The note element occurs more than once.")
            haveSeenNote = True
            _readNote(glyphObject, element)
        elif element.tag == "lib":
            if validate and haveSeenLib:
                raise GlifLibError("The lib element occurs more than once.")
            haveSeenLib = True
            _readLib(glyphObject, element, validate)
        else:
            raise GlifLibError("Unknown element in GLIF: %s" % element)
    # set the collected unicodes
    if unicodes:
        _relaxedSetattr(glyphObject, "unicodes", unicodes)


def _readGlyphFromTreeFormat2(
    tree, glyphObject=None, pointPen=None, validate=None, formatMinor=0
):
    # get the name
    _readName(glyphObject, tree, validate)
    # populate the sub elements
    unicodes = []
    guidelines = []
    anchors = []
    haveSeenAdvance = haveSeenImage = haveSeenOutline = haveSeenLib = haveSeenNote = (
        False
    )
    identifiers = set()
    for element in tree:
        if element.tag == "outline":
            if validate:
                if haveSeenOutline:
                    raise GlifLibError("The outline element occurs more than once.")
                if element.attrib:
                    raise GlifLibError(
                        "The outline element contains unknown attributes."
                    )
                if element.text and element.text.strip() != "":
                    raise GlifLibError("Invalid outline structure.")
            haveSeenOutline = True
            if pointPen is not None:
                buildOutlineFormat2(
                    glyphObject, pointPen, element, identifiers, validate
                )
        elif glyphObject is None:
            continue
        elif element.tag == "advance":
            if validate and haveSeenAdvance:
                raise GlifLibError("The advance element occurs more than once.")
            haveSeenAdvance = True
            _readAdvance(glyphObject, element)
        elif element.tag == "unicode":
            v = element.get("hex")
            if v is None:
                raise GlifLibError(
                    "A unicode element is missing its required hex attribute."
                )
            try:
                v = int(v, 16)
                if v not in unicodes:
                    unicodes.append(v)
            except ValueError:
                raise GlifLibError(
                    "Illegal value for hex attribute of unicode element."
                )
        elif element.tag == "guideline":
            if validate and len(element):
                raise GlifLibError("Unknown children in guideline element.")
            attrib = dict(element.attrib)
            for attr in ("x", "y", "angle"):
                if attr in attrib:
                    attrib[attr] = _number(attrib[attr])
            guidelines.append(attrib)
        elif element.tag == "anchor":
            if validate and len(element):
                raise GlifLibError("Unknown children in anchor element.")
            attrib = dict(element.attrib)
            for attr in ("x", "y"):
                if attr in element.attrib:
                    attrib[attr] = _number(attrib[attr])
            anchors.append(attrib)
        elif element.tag == "image":
            if validate:
                if haveSeenImage:
                    raise GlifLibError("The image element occurs more than once.")
                if len(element):
                    raise GlifLibError("Unknown children in image element.")
            haveSeenImage = True
            _readImage(glyphObject, element, validate)
        elif element.tag == "note":
            if validate and haveSeenNote:
                raise GlifLibError("The note element occurs more than once.")
            haveSeenNote = True
            _readNote(glyphObject, element)
        elif element.tag == "lib":
            if validate and haveSeenLib:
                raise GlifLibError("The lib element occurs more than once.")
            haveSeenLib = True
            _readLib(glyphObject, element, validate)
        else:
            raise GlifLibError("Unknown element in GLIF: %s" % element)
    # set the collected unicodes
    if unicodes:
        _relaxedSetattr(glyphObject, "unicodes", unicodes)
    # set the collected guidelines
    if guidelines:
        if validate and not guidelinesValidator(guidelines, identifiers):
            raise GlifLibError("The guidelines are improperly formatted.")
        _relaxedSetattr(glyphObject, "guidelines", guidelines)
    # set the collected anchors
    if anchors:
        if validate and not anchorsValidator(anchors, identifiers):
            raise GlifLibError("The anchors are improperly formatted.")
        _relaxedSetattr(glyphObject, "anchors", anchors)


_READ_GLYPH_FROM_TREE_FUNCS = {
    GLIFFormatVersion.FORMAT_1_0: _readGlyphFromTreeFormat1,
    GLIFFormatVersion.FORMAT_2_0: _readGlyphFromTreeFormat2,
}


def _readName(glyphObject, root, validate):
    glyphName = root.get("name")
    if validate and not glyphName:
        raise GlifLibError("Empty glyph name in GLIF.")
    if glyphName and glyphObject is not None:
        _relaxedSetattr(glyphObject, "name", glyphName)


def _readAdvance(glyphObject, advance):
    width = _number(advance.get("width", 0))
    _relaxedSetattr(glyphObject, "width", width)
    height = _number(advance.get("height", 0))
    _relaxedSetattr(glyphObject, "height", height)


def _readNote(glyphObject, note):
    lines = note.text.split("\n")
    note = "\n".join(line.strip() for line in lines if line.strip())
    _relaxedSetattr(glyphObject, "note", note)


def _readLib(glyphObject, lib, validate):
    assert len(lib) == 1
    child = lib[0]
    plist = plistlib.fromtree(child)
    if validate:
        valid, message = glyphLibValidator(plist)
        if not valid:
            raise GlifLibError(message)
    _relaxedSetattr(glyphObject, "lib", plist)


def _readImage(glyphObject, image, validate):
    imageData = dict(image.attrib)
    for attr, default in _transformationInfo:
        value = imageData.get(attr, default)
        imageData[attr] = _number(value)
    if validate and not imageValidator(imageData):
        raise GlifLibError("The image element is not properly formatted.")
    _relaxedSetattr(glyphObject, "image", imageData)


# ----------------
# GLIF to PointPen
# ----------------

contourAttributesFormat2 = {"identifier"}
componentAttributesFormat1 = {
    "base",
    "xScale",
    "xyScale",
    "yxScale",
    "yScale",
    "xOffset",
    "yOffset",
}
componentAttributesFormat2 = componentAttributesFormat1 | {"identifier"}
pointAttributesFormat1 = {"x", "y", "type", "smooth", "name"}
pointAttributesFormat2 = pointAttributesFormat1 | {"identifier"}
pointSmoothOptions = {"no", "yes"}
pointTypeOptions = {"move", "line", "offcurve", "curve", "qcurve"}

# format 1


def buildOutlineFormat1(glyphObject, pen, outline, validate):
    anchors = []
    for element in outline:
        if element.tag == "contour":
            if len(element) == 1:
                point = element[0]
                if point.tag == "point":
                    anchor = _buildAnchorFormat1(point, validate)
                    if anchor is not None:
                        anchors.append(anchor)
                        continue
            if pen is not None:
                _buildOutlineContourFormat1(pen, element, validate)
        elif element.tag == "component":
            if pen is not None:
                _buildOutlineComponentFormat1(pen, element, validate)
        else:
            raise GlifLibError("Unknown element in outline element: %s" % element)
    if glyphObject is not None and anchors:
        if validate and not anchorsValidator(anchors):
            raise GlifLibError("GLIF 1 anchors are not properly formatted.")
        _relaxedSetattr(glyphObject, "anchors", anchors)


def _buildAnchorFormat1(point, validate):
    if point.get("type") != "move":
        return None
    name = point.get("name")
    if name is None:
        return None
    x = point.get("x")
    y = point.get("y")
    if validate and x is None:
        raise GlifLibError("Required x attribute is missing in point element.")
    if validate and y is None:
        raise GlifLibError("Required y attribute is missing in point element.")
    x = _number(x)
    y = _number(y)
    anchor = dict(x=x, y=y, name=name)
    return anchor


def _buildOutlineContourFormat1(pen, contour, validate):
    if validate and contour.attrib:
        raise GlifLibError("Unknown attributes in contour element.")
    pen.beginPath()
    if len(contour):
        massaged = _validateAndMassagePointStructures(
            contour,
            pointAttributesFormat1,
            openContourOffCurveLeniency=True,
            validate=validate,
        )
        _buildOutlinePointsFormat1(pen, massaged)
    pen.endPath()


def _buildOutlinePointsFormat1(pen, contour):
    for point in contour:
        x = point["x"]
        y = point["y"]
        segmentType = point["segmentType"]
        smooth = point["smooth"]
        name = point["name"]
        pen.addPoint((x, y), segmentType=segmentType, smooth=smooth, name=name)


def _buildOutlineComponentFormat1(pen, component, validate):
    if validate:
        if len(component):
            raise GlifLibError("Unknown child elements of component element.")
        for attr in component.attrib.keys():
            if attr not in componentAttributesFormat1:
                raise GlifLibError("Unknown attribute in component element: %s" % attr)
    baseGlyphName = component.get("base")
    if validate and baseGlyphName is None:
        raise GlifLibError("The base attribute is not defined in the component.")
    transformation = []
    for attr, default in _transformationInfo:
        value = component.get(attr)
        if value is None:
            value = default
        else:
            value = _number(value)
        transformation.append(value)
    pen.addComponent(baseGlyphName, tuple(transformation))


# format 2


def buildOutlineFormat2(glyphObject, pen, outline, identifiers, validate):
    for element in outline:
        if element.tag == "contour":
            _buildOutlineContourFormat2(pen, element, identifiers, validate)
        elif element.tag == "component":
            _buildOutlineComponentFormat2(pen, element, identifiers, validate)
        else:
            raise GlifLibError("Unknown element in outline element: %s" % element.tag)


def _buildOutlineContourFormat2(pen, contour, identifiers, validate):
    if validate:
        for attr in contour.attrib.keys():
            if attr not in contourAttributesFormat2:
                raise GlifLibError("Unknown attribute in contour element: %s" % attr)
    identifier = contour.get("identifier")
    if identifier is not None:
        if validate:
            if identifier in identifiers:
                raise GlifLibError(
                    "The identifier %s is used more than once." % identifier
                )
            if not identifierValidator(identifier):
                raise GlifLibError(
                    "The contour identifier %s is not valid." % identifier
                )
        identifiers.add(identifier)
    try:
        pen.beginPath(identifier=identifier)
    except TypeError:
        pen.beginPath()
        warn(
            "The beginPath method needs an identifier kwarg. The contour's identifier value has been discarded.",
            DeprecationWarning,
        )
    if len(contour):
        massaged = _validateAndMassagePointStructures(
            contour, pointAttributesFormat2, validate=validate
        )
        _buildOutlinePointsFormat2(pen, massaged, identifiers, validate)
    pen.endPath()


def _buildOutlinePointsFormat2(pen, contour, identifiers, validate):
    for point in contour:
        x = point["x"]
        y = point["y"]
        segmentType = point["segmentType"]
        smooth = point["smooth"]
        name = point["name"]
        identifier = point.get("identifier")
        if identifier is not None:
            if validate:
                if identifier in identifiers:
                    raise GlifLibError(
                        "The identifier %s is used more than once." % identifier
                    )
                if not identifierValidator(identifier):
                    raise GlifLibError("The identifier %s is not valid." % identifier)
            identifiers.add(identifier)
        try:
            pen.addPoint(
                (x, y),
                segmentType=segmentType,
                smooth=smooth,
                name=name,
                identifier=identifier,
            )
        except TypeError:
            pen.addPoint((x, y), segmentType=segmentType, smooth=smooth, name=name)
            warn(
                "The addPoint method needs an identifier kwarg. The point's identifier value has been discarded.",
                DeprecationWarning,
            )


def _buildOutlineComponentFormat2(pen, component, identifiers, validate):
    if validate:
        if len(component):
            raise GlifLibError("Unknown child elements of component element.")
        for attr in component.attrib.keys():
            if attr not in componentAttributesFormat2:
                raise GlifLibError("Unknown attribute in component element: %s" % attr)
    baseGlyphName = component.get("base")
    if validate and baseGlyphName is None:
        raise GlifLibError("The base attribute is not defined in the component.")
    transformation = []
    for attr, default in _transformationInfo:
        value = component.get(attr)
        if value is None:
            value = default
        else:
            value = _number(value)
        transformation.append(value)
    identifier = component.get("identifier")
    if identifier is not None:
        if validate:
            if identifier in identifiers:
                raise GlifLibError(
                    "The identifier %s is used more than once." % identifier
                )
            if validate and not identifierValidator(identifier):
                raise GlifLibError("The identifier %s is not valid." % identifier)
        identifiers.add(identifier)
    try:
        pen.addComponent(baseGlyphName, tuple(transformation), identifier=identifier)
    except TypeError:
        pen.addComponent(baseGlyphName, tuple(transformation))
        warn(
            "The addComponent method needs an identifier kwarg. The component's identifier value has been discarded.",
            DeprecationWarning,
        )


# all formats


def _validateAndMassagePointStructures(
    contour, pointAttributes, openContourOffCurveLeniency=False, validate=True
):
    if not len(contour):
        return
    # store some data for later validation
    lastOnCurvePoint = None
    haveOffCurvePoint = False
    # validate and massage the individual point elements
    massaged = []
    for index, element in enumerate(contour):
        # not <point>
        if element.tag != "point":
            raise GlifLibError(
                "Unknown child element (%s) of contour element." % element.tag
            )
        point = dict(element.attrib)
        massaged.append(point)
        if validate:
            # unknown attributes
            for attr in point.keys():
                if attr not in pointAttributes:
                    raise GlifLibError("Unknown attribute in point element: %s" % attr)
            # search for unknown children
            if len(element):
                raise GlifLibError("Unknown child elements in point element.")
        # x and y are required
        for attr in ("x", "y"):
            try:
                point[attr] = _number(point[attr])
            except KeyError as e:
                raise GlifLibError(
                    f"Required {attr} attribute is missing in point element."
                ) from e
        # segment type
        pointType = point.pop("type", "offcurve")
        if validate and pointType not in pointTypeOptions:
            raise GlifLibError("Unknown point type: %s" % pointType)
        if pointType == "offcurve":
            pointType = None
        point["segmentType"] = pointType
        if pointType is None:
            haveOffCurvePoint = True
        else:
            lastOnCurvePoint = index
        # move can only occur as the first point
        if validate and pointType == "move" and index != 0:
            raise GlifLibError(
                "A move point occurs after the first point in the contour."
            )
        # smooth is optional
        smooth = point.get("smooth", "no")
        if validate and smooth is not None:
            if smooth not in pointSmoothOptions:
                raise GlifLibError("Unknown point smooth value: %s" % smooth)
        smooth = smooth == "yes"
        point["smooth"] = smooth
        # smooth can only be applied to curve and qcurve
        if validate and smooth and pointType is None:
            raise GlifLibError("smooth attribute set in an offcurve point.")
        # name is optional
        if "name" not in element.attrib:
            point["name"] = None
    if openContourOffCurveLeniency:
        # remove offcurves that precede a move. this is technically illegal,
        # but we let it slide because there are fonts out there in the wild like this.
        if massaged[0]["segmentType"] == "move":
            count = 0
            for point in reversed(massaged):
                if point["segmentType"] is None:
                    count += 1
                else:
                    break
            if count:
                massaged = massaged[:-count]
    # validate the off-curves in the segments
    if validate and haveOffCurvePoint and lastOnCurvePoint is not None:
        # we only care about how many offCurves there are before an onCurve
        # filter out the trailing offCurves
        offCurvesCount = len(massaged) - 1 - lastOnCurvePoint
        for point in massaged:
            segmentType = point["segmentType"]
            if segmentType is None:
                offCurvesCount += 1
            else:
                if offCurvesCount:
                    # move and line can't be preceded by off-curves
                    if segmentType == "move":
                        # this will have been filtered out already
                        raise GlifLibError("move can not have an offcurve.")
                    elif segmentType == "line":
                        raise GlifLibError("line can not have an offcurve.")
                    elif segmentType == "curve":
                        if offCurvesCount > 2:
                            raise GlifLibError("Too many offcurves defined for curve.")
                    elif segmentType == "qcurve":
                        pass
                    else:
                        # unknown segment type. it'll be caught later.
                        pass
                offCurvesCount = 0
    return massaged


# ---------------------
# Misc Helper Functions
# ---------------------


def _relaxedSetattr(object, attr, value):
    try:
        setattr(object, attr, value)
    except AttributeError:
        pass


def _number(s):
    """
    Given a numeric string, return an integer or a float, whichever
    the string indicates. _number("1") will return the integer 1,
    _number("1.0") will return the float 1.0.

    >>> _number("1")
    1
    >>> _number("1.0")
    1.0
    >>> _number("a")  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    GlifLibError: Could not convert a to an int or float.
    """
    try:
        n = int(s)
        return n
    except ValueError:
        pass
    try:
        n = float(s)
        return n
    except ValueError:
        raise GlifLibError("Could not convert %s to an int or float." % s)


# --------------------
# Rapid Value Fetching
# --------------------

# base


class _DoneParsing(Exception):
    pass


class _BaseParser:
    def __init__(self):
        self._elementStack = []

    def parse(self, text):
        from xml.parsers.expat import ParserCreate

        parser = ParserCreate()
        parser.StartElementHandler = self.startElementHandler
        parser.EndElementHandler = self.endElementHandler
        parser.Parse(text, 1)

    def startElementHandler(self, name, attrs):
        self._elementStack.append(name)

    def endElementHandler(self, name):
        other = self._elementStack.pop(-1)
        assert other == name


# unicodes


def _fetchUnicodes(glif):
    """
    Get a list of unicodes listed in glif.
    """
    parser = _FetchUnicodesParser()
    parser.parse(glif)
    return parser.unicodes


class _FetchUnicodesParser(_BaseParser):
    def __init__(self):
        self.unicodes = []
        super().__init__()

    def startElementHandler(self, name, attrs):
        if (
            name == "unicode"
            and self._elementStack
            and self._elementStack[-1] == "glyph"
        ):
            value = attrs.get("hex")
            if value is not None:
                try:
                    value = int(value, 16)
                    if value not in self.unicodes:
                        self.unicodes.append(value)
                except ValueError:
                    pass
        super().startElementHandler(name, attrs)


# image


def _fetchImageFileName(glif):
    """
    The image file name (if any) from glif.
    """
    parser = _FetchImageFileNameParser()
    try:
        parser.parse(glif)
    except _DoneParsing:
        pass
    return parser.fileName


class _FetchImageFileNameParser(_BaseParser):
    def __init__(self):
        self.fileName = None
        super().__init__()

    def startElementHandler(self, name, attrs):
        if name == "image" and self._elementStack and self._elementStack[-1] == "glyph":
            self.fileName = attrs.get("fileName")
            raise _DoneParsing
        super().startElementHandler(name, attrs)


# component references


def _fetchComponentBases(glif):
    """
    Get a list of component base glyphs listed in glif.
    """
    parser = _FetchComponentBasesParser()
    try:
        parser.parse(glif)
    except _DoneParsing:
        pass
    return list(parser.bases)


class _FetchComponentBasesParser(_BaseParser):
    def __init__(self):
        self.bases = []
        super().__init__()

    def startElementHandler(self, name, attrs):
        if (
            name == "component"
            and self._elementStack
            and self._elementStack[-1] == "outline"
        ):
            base = attrs.get("base")
            if base is not None:
                self.bases.append(base)
        super().startElementHandler(name, attrs)

    def endElementHandler(self, name):
        if name == "outline":
            raise _DoneParsing
        super().endElementHandler(name)


# --------------
# GLIF Point Pen
# --------------

_transformationInfo = [
    # field name, default value
    ("xScale", 1),
    ("xyScale", 0),
    ("yxScale", 0),
    ("yScale", 1),
    ("xOffset", 0),
    ("yOffset", 0),
]


class GLIFPointPen(AbstractPointPen):
    """
    Helper class using the PointPen protocol to write the <outline>
    part of .glif files.
    """

    def __init__(self, element, formatVersion=None, identifiers=None, validate=True):
        if identifiers is None:
            identifiers = set()
        self.formatVersion = GLIFFormatVersion(formatVersion)
        self.identifiers = identifiers
        self.outline = element
        self.contour = None
        self.prevOffCurveCount = 0
        self.prevPointTypes = []
        self.validate = validate

    def beginPath(self, identifier=None, **kwargs):
        attrs = OrderedDict()
        if identifier is not None and self.formatVersion.major >= 2:
            if self.validate:
                if identifier in self.identifiers:
                    raise GlifLibError(
                        "identifier used more than once: %s" % identifier
                    )
                if not identifierValidator(identifier):
                    raise GlifLibError(
                        "identifier not formatted properly: %s" % identifier
                    )
            attrs["identifier"] = identifier
            self.identifiers.add(identifier)
        self.contour = etree.SubElement(self.outline, "contour", attrs)
        self.prevOffCurveCount = 0

    def endPath(self):
        if self.prevPointTypes and self.prevPointTypes[0] == "move":
            if self.validate and self.prevPointTypes[-1] == "offcurve":
                raise GlifLibError("open contour has loose offcurve point")
        # prevent lxml from writing self-closing tags
        if not len(self.contour):
            self.contour.text = "\n  "
        self.contour = None
        self.prevPointType = None
        self.prevOffCurveCount = 0
        self.prevPointTypes = []

    def addPoint(
        self, pt, segmentType=None, smooth=None, name=None, identifier=None, **kwargs
    ):
        attrs = OrderedDict()
        # coordinates
        if pt is not None:
            if self.validate:
                for coord in pt:
                    if not isinstance(coord, numberTypes):
                        raise GlifLibError("coordinates must be int or float")
            attrs["x"] = repr(pt[0])
            attrs["y"] = repr(pt[1])
        # segment type
        if segmentType == "offcurve":
            segmentType = None
        if self.validate:
            if segmentType == "move" and self.prevPointTypes:
                raise GlifLibError(
                    "move occurs after a point has already been added to the contour."
                )
            if (
                segmentType in ("move", "line")
                and self.prevPointTypes
                and self.prevPointTypes[-1] == "offcurve"
            ):
                raise GlifLibError("offcurve occurs before %s point." % segmentType)
            if segmentType == "curve" and self.prevOffCurveCount > 2:
                raise GlifLibError("too many offcurve points before curve point.")
        if segmentType is not None:
            attrs["type"] = segmentType
        else:
            segmentType = "offcurve"
        if segmentType == "offcurve":
            self.prevOffCurveCount += 1
        else:
            self.prevOffCurveCount = 0
        self.prevPointTypes.append(segmentType)
        # smooth
        if smooth:
            if self.validate and segmentType == "offcurve":
                raise GlifLibError("can't set smooth in an offcurve point.")
            attrs["smooth"] = "yes"
        # name
        if name is not None:
            attrs["name"] = name
        # identifier
        if identifier is not None and self.formatVersion.major >= 2:
            if self.validate:
                if identifier in self.identifiers:
                    raise GlifLibError(
                        "identifier used more than once: %s" % identifier
                    )
                if not identifierValidator(identifier):
                    raise GlifLibError(
                        "identifier not formatted properly: %s" % identifier
                    )
            attrs["identifier"] = identifier
            self.identifiers.add(identifier)
        etree.SubElement(self.contour, "point", attrs)

    def addComponent(self, glyphName, transformation, identifier=None, **kwargs):
        attrs = OrderedDict([("base", glyphName)])
        for (attr, default), value in zip(_transformationInfo, transformation):
            if self.validate and not isinstance(value, numberTypes):
                raise GlifLibError("transformation values must be int or float")
            if value != default:
                attrs[attr] = repr(value)
        if identifier is not None and self.formatVersion.major >= 2:
            if self.validate:
                if identifier in self.identifiers:
                    raise GlifLibError(
                        "identifier used more than once: %s" % identifier
                    )
                if self.validate and not identifierValidator(identifier):
                    raise GlifLibError(
                        "identifier not formatted properly: %s" % identifier
                    )
            attrs["identifier"] = identifier
            self.identifiers.add(identifier)
        etree.SubElement(self.outline, "component", attrs)


if __name__ == "__main__":
    import doctest

    doctest.testmod()

# === NexusCore/openenv\Lib\site-packages\httpx\_client.py ===
from __future__ import annotations

import datetime
import enum
import logging
import time
import typing
import warnings
from contextlib import asynccontextmanager, contextmanager
from types import TracebackType

from .__version__ import __version__
from ._auth import Auth, BasicAuth, FunctionAuth
from ._config import (
    DEFAULT_LIMITS,
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_TIMEOUT_CONFIG,
    Limits,
    Proxy,
    Timeout,
)
from ._decoders import SUPPORTED_DECODERS
from ._exceptions import (
    InvalidURL,
    RemoteProtocolError,
    TooManyRedirects,
    request_context,
)
from ._models import Cookies, Headers, Request, Response
from ._status_codes import codes
from ._transports.base import AsyncBaseTransport, BaseTransport
from ._transports.default import AsyncHTTPTransport, HTTPTransport
from ._types import (
    AsyncByteStream,
    AuthTypes,
    CertTypes,
    CookieTypes,
    HeaderTypes,
    ProxyTypes,
    QueryParamTypes,
    RequestContent,
    RequestData,
    RequestExtensions,
    RequestFiles,
    SyncByteStream,
    TimeoutTypes,
)
from ._urls import URL, QueryParams
from ._utils import URLPattern, get_environment_proxies

if typing.TYPE_CHECKING:
    import ssl  # pragma: no cover

__all__ = ["USE_CLIENT_DEFAULT", "AsyncClient", "Client"]

# The type annotation for @classmethod and context managers here follows PEP 484
# https://www.python.org/dev/peps/pep-0484/#annotating-instance-and-class-methods
T = typing.TypeVar("T", bound="Client")
U = typing.TypeVar("U", bound="AsyncClient")


def _is_https_redirect(url: URL, location: URL) -> bool:
    """
    Return 'True' if 'location' is a HTTPS upgrade of 'url'
    """
    if url.host != location.host:
        return False

    return (
        url.scheme == "http"
        and _port_or_default(url) == 80
        and location.scheme == "https"
        and _port_or_default(location) == 443
    )


def _port_or_default(url: URL) -> int | None:
    if url.port is not None:
        return url.port
    return {"http": 80, "https": 443}.get(url.scheme)


def _same_origin(url: URL, other: URL) -> bool:
    """
    Return 'True' if the given URLs share the same origin.
    """
    return (
        url.scheme == other.scheme
        and url.host == other.host
        and _port_or_default(url) == _port_or_default(other)
    )


class UseClientDefault:
    """
    For some parameters such as `auth=...` and `timeout=...` we need to be able
    to indicate the default "unset" state, in a way that is distinctly different
    to using `None`.

    The default "unset" state indicates that whatever default is set on the
    client should be used. This is different to setting `None`, which
    explicitly disables the parameter, possibly overriding a client default.

    For example we use `timeout=USE_CLIENT_DEFAULT` in the `request()` signature.
    Omitting the `timeout` parameter will send a request using whatever default
    timeout has been configured on the client. Including `timeout=None` will
    ensure no timeout is used.

    Note that user code shouldn't need to use the `USE_CLIENT_DEFAULT` constant,
    but it is used internally when a parameter is not included.
    """


USE_CLIENT_DEFAULT = UseClientDefault()


logger = logging.getLogger("httpx")

USER_AGENT = f"python-httpx/{__version__}"
ACCEPT_ENCODING = ", ".join(
    [key for key in SUPPORTED_DECODERS.keys() if key != "identity"]
)


class ClientState(enum.Enum):
    # UNOPENED:
    #   The client has been instantiated, but has not been used to send a request,
    #   or been opened by entering the context of a `with` block.
    UNOPENED = 1
    # OPENED:
    #   The client has either sent a request, or is within a `with` block.
    OPENED = 2
    # CLOSED:
    #   The client has either exited the `with` block, or `close()` has
    #   been called explicitly.
    CLOSED = 3


class BoundSyncStream(SyncByteStream):
    """
    A byte stream that is bound to a given response instance, and that
    ensures the `response.elapsed` is set once the response is closed.
    """

    def __init__(
        self, stream: SyncByteStream, response: Response, start: float
    ) -> None:
        self._stream = stream
        self._response = response
        self._start = start

    def __iter__(self) -> typing.Iterator[bytes]:
        for chunk in self._stream:
            yield chunk

    def close(self) -> None:
        elapsed = time.perf_counter() - self._start
        self._response.elapsed = datetime.timedelta(seconds=elapsed)
        self._stream.close()


class BoundAsyncStream(AsyncByteStream):
    """
    An async byte stream that is bound to a given response instance, and that
    ensures the `response.elapsed` is set once the response is closed.
    """

    def __init__(
        self, stream: AsyncByteStream, response: Response, start: float
    ) -> None:
        self._stream = stream
        self._response = response
        self._start = start

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        async for chunk in self._stream:
            yield chunk

    async def aclose(self) -> None:
        elapsed = time.perf_counter() - self._start
        self._response.elapsed = datetime.timedelta(seconds=elapsed)
        await self._stream.aclose()


EventHook = typing.Callable[..., typing.Any]


class BaseClient:
    def __init__(
        self,
        *,
        auth: AuthTypes | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        follow_redirects: bool = False,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        event_hooks: None | (typing.Mapping[str, list[EventHook]]) = None,
        base_url: URL | str = "",
        trust_env: bool = True,
        default_encoding: str | typing.Callable[[bytes], str] = "utf-8",
    ) -> None:
        event_hooks = {} if event_hooks is None else event_hooks

        self._base_url = self._enforce_trailing_slash(URL(base_url))

        self._auth = self._build_auth(auth)
        self._params = QueryParams(params)
        self.headers = Headers(headers)
        self._cookies = Cookies(cookies)
        self._timeout = Timeout(timeout)
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects
        self._event_hooks = {
            "request": list(event_hooks.get("request", [])),
            "response": list(event_hooks.get("response", [])),
        }
        self._trust_env = trust_env
        self._default_encoding = default_encoding
        self._state = ClientState.UNOPENED

    @property
    def is_closed(self) -> bool:
        """
        Check if the client being closed
        """
        return self._state == ClientState.CLOSED

    @property
    def trust_env(self) -> bool:
        return self._trust_env

    def _enforce_trailing_slash(self, url: URL) -> URL:
        if url.raw_path.endswith(b"/"):
            return url
        return url.copy_with(raw_path=url.raw_path + b"/")

    def _get_proxy_map(
        self, proxy: ProxyTypes | None, allow_env_proxies: bool
    ) -> dict[str, Proxy | None]:
        if proxy is None:
            if allow_env_proxies:
                return {
                    key: None if url is None else Proxy(url=url)
                    for key, url in get_environment_proxies().items()
                }
            return {}
        else:
            proxy = Proxy(url=proxy) if isinstance(proxy, (str, URL)) else proxy
            return {"all://": proxy}

    @property
    def timeout(self) -> Timeout:
        return self._timeout

    @timeout.setter
    def timeout(self, timeout: TimeoutTypes) -> None:
        self._timeout = Timeout(timeout)

    @property
    def event_hooks(self) -> dict[str, list[EventHook]]:
        return self._event_hooks

    @event_hooks.setter
    def event_hooks(self, event_hooks: dict[str, list[EventHook]]) -> None:
        self._event_hooks = {
            "request": list(event_hooks.get("request", [])),
            "response": list(event_hooks.get("response", [])),
        }

    @property
    def auth(self) -> Auth | None:
        """
        Authentication class used when none is passed at the request-level.

        See also [Authentication][0].

        [0]: /quickstart/#authentication
        """
        return self._auth

    @auth.setter
    def auth(self, auth: AuthTypes) -> None:
        self._auth = self._build_auth(auth)

    @property
    def base_url(self) -> URL:
        """
        Base URL to use when sending requests with relative URLs.
        """
        return self._base_url

    @base_url.setter
    def base_url(self, url: URL | str) -> None:
        self._base_url = self._enforce_trailing_slash(URL(url))

    @property
    def headers(self) -> Headers:
        """
        HTTP headers to include when sending requests.
        """
        return self._headers

    @headers.setter
    def headers(self, headers: HeaderTypes) -> None:
        client_headers = Headers(
            {
                b"Accept": b"*/*",
                b"Accept-Encoding": ACCEPT_ENCODING.encode("ascii"),
                b"Connection": b"keep-alive",
                b"User-Agent": USER_AGENT.encode("ascii"),
            }
        )
        client_headers.update(headers)
        self._headers = client_headers

    @property
    def cookies(self) -> Cookies:
        """
        Cookie values to include when sending requests.
        """
        return self._cookies

    @cookies.setter
    def cookies(self, cookies: CookieTypes) -> None:
        self._cookies = Cookies(cookies)

    @property
    def params(self) -> QueryParams:
        """
        Query parameters to include in the URL when sending requests.
        """
        return self._params

    @params.setter
    def params(self, params: QueryParamTypes) -> None:
        self._params = QueryParams(params)

    def build_request(
        self,
        method: str,
        url: URL | str,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Request:
        """
        Build and return a request instance.

        * The `params`, `headers` and `cookies` arguments
        are merged with any values set on the client.
        * The `url` argument is merged with any `base_url` set on the client.

        See also: [Request instances][0]

        [0]: /advanced/clients/#request-instances
        """
        url = self._merge_url(url)
        headers = self._merge_headers(headers)
        cookies = self._merge_cookies(cookies)
        params = self._merge_queryparams(params)
        extensions = {} if extensions is None else extensions
        if "timeout" not in extensions:
            timeout = (
                self.timeout
                if isinstance(timeout, UseClientDefault)
                else Timeout(timeout)
            )
            extensions = dict(**extensions, timeout=timeout.as_dict())
        return Request(
            method,
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            extensions=extensions,
        )

    def _merge_url(self, url: URL | str) -> URL:
        """
        Merge a URL argument together with any 'base_url' on the client,
        to create the URL used for the outgoing request.
        """
        merge_url = URL(url)
        if merge_url.is_relative_url:
            # To merge URLs we always append to the base URL. To get this
            # behaviour correct we always ensure the base URL ends in a '/'
            # separator, and strip any leading '/' from the merge URL.
            #
            # So, eg...
            #
            # >>> client = Client(base_url="https://www.example.com/subpath")
            # >>> client.base_url
            # URL('https://www.example.com/subpath/')
            # >>> client.build_request("GET", "/path").url
            # URL('https://www.example.com/subpath/path')
            merge_raw_path = self.base_url.raw_path + merge_url.raw_path.lstrip(b"/")
            return self.base_url.copy_with(raw_path=merge_raw_path)
        return merge_url

    def _merge_cookies(self, cookies: CookieTypes | None = None) -> CookieTypes | None:
        """
        Merge a cookies argument together with any cookies on the client,
        to create the cookies used for the outgoing request.
        """
        if cookies or self.cookies:
            merged_cookies = Cookies(self.cookies)
            merged_cookies.update(cookies)
            return merged_cookies
        return cookies

    def _merge_headers(self, headers: HeaderTypes | None = None) -> HeaderTypes | None:
        """
        Merge a headers argument together with any headers on the client,
        to create the headers used for the outgoing request.
        """
        merged_headers = Headers(self.headers)
        merged_headers.update(headers)
        return merged_headers

    def _merge_queryparams(
        self, params: QueryParamTypes | None = None
    ) -> QueryParamTypes | None:
        """
        Merge a queryparams argument together with any queryparams on the client,
        to create the queryparams used for the outgoing request.
        """
        if params or self.params:
            merged_queryparams = QueryParams(self.params)
            return merged_queryparams.merge(params)
        return params

    def _build_auth(self, auth: AuthTypes | None) -> Auth | None:
        if auth is None:
            return None
        elif isinstance(auth, tuple):
            return BasicAuth(username=auth[0], password=auth[1])
        elif isinstance(auth, Auth):
            return auth
        elif callable(auth):
            return FunctionAuth(func=auth)
        else:
            raise TypeError(f'Invalid "auth" argument: {auth!r}')

    def _build_request_auth(
        self,
        request: Request,
        auth: AuthTypes | UseClientDefault | None = USE_CLIENT_DEFAULT,
    ) -> Auth:
        auth = (
            self._auth if isinstance(auth, UseClientDefault) else self._build_auth(auth)
        )

        if auth is not None:
            return auth

        username, password = request.url.username, request.url.password
        if username or password:
            return BasicAuth(username=username, password=password)

        return Auth()

    def _build_redirect_request(self, request: Request, response: Response) -> Request:
        """
        Given a request and a redirect response, return a new request that
        should be used to effect the redirect.
        """
        method = self._redirect_method(request, response)
        url = self._redirect_url(request, response)
        headers = self._redirect_headers(request, url, method)
        stream = self._redirect_stream(request, method)
        cookies = Cookies(self.cookies)
        return Request(
            method=method,
            url=url,
            headers=headers,
            cookies=cookies,
            stream=stream,
            extensions=request.extensions,
        )

    def _redirect_method(self, request: Request, response: Response) -> str:
        """
        When being redirected we may want to change the method of the request
        based on certain specs or browser behavior.
        """
        method = request.method

        # https://tools.ietf.org/html/rfc7231#section-6.4.4
        if response.status_code == codes.SEE_OTHER and method != "HEAD":
            method = "GET"

        # Do what the browsers do, despite standards...
        # Turn 302s into GETs.
        if response.status_code == codes.FOUND and method != "HEAD":
            method = "GET"

        # If a POST is responded to with a 301, turn it into a GET.
        # This bizarre behaviour is explained in 'requests' issue 1704.
        if response.status_code == codes.MOVED_PERMANENTLY and method == "POST":
            method = "GET"

        return method

    def _redirect_url(self, request: Request, response: Response) -> URL:
        """
        Return the URL for the redirect to follow.
        """
        location = response.headers["Location"]

        try:
            url = URL(location)
        except InvalidURL as exc:
            raise RemoteProtocolError(
                f"Invalid URL in location header: {exc}.", request=request
            ) from None

        # Handle malformed 'Location' headers that are "absolute" form, have no host.
        # See: https://github.com/encode/httpx/issues/771
        if url.scheme and not url.host:
            url = url.copy_with(host=request.url.host)

        # Facilitate relative 'Location' headers, as allowed by RFC 7231.
        # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
        if url.is_relative_url:
            url = request.url.join(url)

        # Attach previous fragment if needed (RFC 7231 7.1.2)
        if request.url.fragment and not url.fragment:
            url = url.copy_with(fragment=request.url.fragment)

        return url

    def _redirect_headers(self, request: Request, url: URL, method: str) -> Headers:
        """
        Return the headers that should be used for the redirect request.
        """
        headers = Headers(request.headers)

        if not _same_origin(url, request.url):
            if not _is_https_redirect(request.url, url):
                # Strip Authorization headers when responses are redirected
                # away from the origin. (Except for direct HTTP to HTTPS redirects.)
                headers.pop("Authorization", None)

            # Update the Host header.
            headers["Host"] = url.netloc.decode("ascii")

        if method != request.method and method == "GET":
            # If we've switch to a 'GET' request, then strip any headers which
            # are only relevant to the request body.
            headers.pop("Content-Length", None)
            headers.pop("Transfer-Encoding", None)

        # We should use the client cookie store to determine any cookie header,
        # rather than whatever was on the original outgoing request.
        headers.pop("Cookie", None)

        return headers

    def _redirect_stream(
        self, request: Request, method: str
    ) -> SyncByteStream | AsyncByteStream | None:
        """
        Return the body that should be used for the redirect request.
        """
        if method != request.method and method == "GET":
            return None

        return request.stream

    def _set_timeout(self, request: Request) -> None:
        if "timeout" not in request.extensions:
            timeout = (
                self.timeout
                if isinstance(self.timeout, UseClientDefault)
                else Timeout(self.timeout)
            )
            request.extensions = dict(**request.extensions, timeout=timeout.as_dict())


class Client(BaseClient):
    """
    An HTTP client, with connection pooling, HTTP/2, redirects, cookie persistence, etc.

    It can be shared between threads.

    Usage:

    ```python
    >>> client = httpx.Client()
    >>> response = client.get('https://example.org')
    ```

    **Parameters:**

    * **auth** - *(optional)* An authentication class to use when sending
    requests.
    * **params** - *(optional)* Query parameters to include in request URLs, as
    a string, dictionary, or sequence of two-tuples.
    * **headers** - *(optional)* Dictionary of HTTP headers to include when
    sending requests.
    * **cookies** - *(optional)* Dictionary of Cookie items to include when
    sending requests.
    * **verify** - *(optional)* Either `True` to use an SSL context with the
    default CA bundle, `False` to disable verification, or an instance of
    `ssl.SSLContext` to use a custom context.
    * **http2** - *(optional)* A boolean indicating if HTTP/2 support should be
    enabled. Defaults to `False`.
    * **proxy** - *(optional)* A proxy URL where all the traffic should be routed.
    * **timeout** - *(optional)* The timeout configuration to use when sending
    requests.
    * **limits** - *(optional)* The limits configuration to use.
    * **max_redirects** - *(optional)* The maximum number of redirect responses
    that should be followed.
    * **base_url** - *(optional)* A URL to use as the base when building
    request URLs.
    * **transport** - *(optional)* A transport class to use for sending requests
    over the network.
    * **trust_env** - *(optional)* Enables or disables usage of environment
    variables for configuration.
    * **default_encoding** - *(optional)* The default encoding to use for decoding
    response text, if no charset information is included in a response Content-Type
    header. Set to a callable for automatic character set detection. Default: "utf-8".
    """

    def __init__(
        self,
        *,
        auth: AuthTypes | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        verify: ssl.SSLContext | str | bool = True,
        cert: CertTypes | None = None,
        trust_env: bool = True,
        http1: bool = True,
        http2: bool = False,
        proxy: ProxyTypes | None = None,
        mounts: None | (typing.Mapping[str, BaseTransport | None]) = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        follow_redirects: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        event_hooks: None | (typing.Mapping[str, list[EventHook]]) = None,
        base_url: URL | str = "",
        transport: BaseTransport | None = None,
        default_encoding: str | typing.Callable[[bytes], str] = "utf-8",
    ) -> None:
        super().__init__(
            auth=auth,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            follow_redirects=follow_redirects,
            max_redirects=max_redirects,
            event_hooks=event_hooks,
            base_url=base_url,
            trust_env=trust_env,
            default_encoding=default_encoding,
        )

        if http2:
            try:
                import h2  # noqa
            except ImportError:  # pragma: no cover
                raise ImportError(
                    "Using http2=True, but the 'h2' package is not installed. "
                    "Make sure to install httpx using `pip install httpx[http2]`."
                ) from None

        allow_env_proxies = trust_env and transport is None
        proxy_map = self._get_proxy_map(proxy, allow_env_proxies)

        self._transport = self._init_transport(
            verify=verify,
            cert=cert,
            trust_env=trust_env,
            http1=http1,
            http2=http2,
            limits=limits,
            transport=transport,
        )
        self._mounts: dict[URLPattern, BaseTransport | None] = {
            URLPattern(key): None
            if proxy is None
            else self._init_proxy_transport(
                proxy,
                verify=verify,
                cert=cert,
                trust_env=trust_env,
                http1=http1,
                http2=http2,
                limits=limits,
            )
            for key, proxy in proxy_map.items()
        }
        if mounts is not None:
            self._mounts.update(
                {URLPattern(key): transport for key, transport in mounts.items()}
            )

        self._mounts = dict(sorted(self._mounts.items()))

    def _init_transport(
        self,
        verify: ssl.SSLContext | str | bool = True,
        cert: CertTypes | None = None,
        trust_env: bool = True,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        transport: BaseTransport | None = None,
    ) -> BaseTransport:
        if transport is not None:
            return transport

        return HTTPTransport(
            verify=verify,
            cert=cert,
            trust_env=trust_env,
            http1=http1,
            http2=http2,
            limits=limits,
        )

    def _init_proxy_transport(
        self,
        proxy: Proxy,
        verify: ssl.SSLContext | str | bool = True,
        cert: CertTypes | None = None,
        trust_env: bool = True,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
    ) -> BaseTransport:
        return HTTPTransport(
            verify=verify,
            cert=cert,
            trust_env=trust_env,
            http1=http1,
            http2=http2,
            limits=limits,
            proxy=proxy,
        )

    def _transport_for_url(self, url: URL) -> BaseTransport:
        """
        Returns the transport instance that should be used for a given URL.
        This will either be the standard connection pool, or a proxy.
        """
        for pattern, transport in self._mounts.items():
            if pattern.matches(url):
                return self._transport if transport is None else transport

        return self._transport

    def request(
        self,
        method: str,
        url: URL | str,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault | None = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Build and send a request.

        Equivalent to:

        ```python
        request = client.build_request(...)
        response = client.send(request, ...)
        ```

        See `Client.build_request()`, `Client.send()` and
        [Merging of configuration][0] for how the various parameters
        are merged with client-level configuration.

        [0]: /advanced/clients/#merging-of-configuration
        """
        if cookies is not None:
            message = (
                "Setting per-request cookies=<...> is being deprecated, because "
                "the expected behaviour on cookie persistence is ambiguous. Set "
                "cookies directly on the client instance instead."
            )
            warnings.warn(message, DeprecationWarning, stacklevel=2)

        request = self.build_request(
            method=method,
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            extensions=extensions,
        )
        return self.send(request, auth=auth, follow_redirects=follow_redirects)

    @contextmanager
    def stream(
        self,
        method: str,
        url: URL | str,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault | None = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> typing.Iterator[Response]:
        """
        Alternative to `httpx.request()` that streams the response body
        instead of loading it into memory at once.

        **Parameters**: See `httpx.request`.

        See also: [Streaming Responses][0]

        [0]: /quickstart#streaming-responses
        """
        request = self.build_request(
            method=method,
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            extensions=extensions,
        )
        response = self.send(
            request=request,
            auth=auth,
            follow_redirects=follow_redirects,
            stream=True,
        )
        try:
            yield response
        finally:
            response.close()

    def send(
        self,
        request: Request,
        *,
        stream: bool = False,
        auth: AuthTypes | UseClientDefault | None = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
    ) -> Response:
        """
        Send a request.

        The request is sent as-is, unmodified.

        Typically you'll want to build one with `Client.build_request()`
        so that any client-level configuration is merged into the request,
        but passing an explicit `httpx.Request()` is supported as well.

        See also: [Request instances][0]

        [0]: /advanced/clients/#request-instances
        """
        if self._state == ClientState.CLOSED:
            raise RuntimeError("Cannot send a request, as the client has been closed.")

        self._state = ClientState.OPENED
        follow_redirects = (
            self.follow_redirects
            if isinstance(follow_redirects, UseClientDefault)
            else follow_redirects
        )

        self._set_timeout(request)

        auth = self._build_request_auth(request, auth)

        response = self._send_handling_auth(
            request,
            auth=auth,
            follow_redirects=follow_redirects,
            history=[],
        )
        try:
            if not stream:
                response.read()

            return response

        except BaseException as exc:
            response.close()
            raise exc

    def _send_handling_auth(
        self,
        request: Request,
        auth: Auth,
        follow_redirects: bool,
        history: list[Response],
    ) -> Response:
        auth_flow = auth.sync_auth_flow(request)
        try:
            request = next(auth_flow)

            while True:
                response = self._send_handling_redirects(
                    request,
                    follow_redirects=follow_redirects,
                    history=history,
                )
                try:
                    try:
                        next_request = auth_flow.send(response)
                    except StopIteration:
                        return response

                    response.history = list(history)
                    response.read()
                    request = next_request
                    history.append(response)

                except BaseException as exc:
                    response.close()
                    raise exc
        finally:
            auth_flow.close()

    def _send_handling_redirects(
        self,
        request: Request,
        follow_redirects: bool,
        history: list[Response],
    ) -> Response:
        while True:
            if len(history) > self.max_redirects:
                raise TooManyRedirects(
                    "Exceeded maximum allowed redirects.", request=request
                )

            for hook in self._event_hooks["request"]:
                hook(request)

            response = self._send_single_request(request)
            try:
                for hook in self._event_hooks["response"]:
                    hook(response)
                response.history = list(history)

                if not response.has_redirect_location:
                    return response

                request = self._build_redirect_request(request, response)
                history = history + [response]

                if follow_redirects:
                    response.read()
                else:
                    response.next_request = request
                    return response

            except BaseException as exc:
                response.close()
                raise exc

    def _send_single_request(self, request: Request) -> Response:
        """
        Sends a single request, without handling any redirections.
        """
        transport = self._transport_for_url(request.url)
        start = time.perf_counter()

        if not isinstance(request.stream, SyncByteStream):
            raise RuntimeError(
                "Attempted to send an async request with a sync Client instance."
            )

        with request_context(request=request):
            response = transport.handle_request(request)

        assert isinstance(response.stream, SyncByteStream)

        response.request = request
        response.stream = BoundSyncStream(
            response.stream, response=response, start=start
        )
        self.cookies.extract_cookies(response)
        response.default_encoding = self._default_encoding

        logger.info(
            'HTTP Request: %s %s "%s %d %s"',
            request.method,
            request.url,
            response.http_version,
            response.status_code,
            response.reason_phrase,
        )

        return response

    def get(
        self,
        url: URL | str,
        *,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault | None = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send a `GET` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "GET",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def options(
        self,
        url: URL | str,
        *,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send an `OPTIONS` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "OPTIONS",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def head(
        self,
        url: URL | str,
        *,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send a `HEAD` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "HEAD",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def post(
        self,
        url: URL | str,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send a `POST` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "POST",
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def put(
        self,
        url: URL | str,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send a `PUT` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "PUT",
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def patch(
        self,
        url: URL | str,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send a `PATCH` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "PATCH",
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def delete(
        self,
        url: URL | str,
        *,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send a `DELETE` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "DELETE",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def close(self) -> None:
        """
        Close transport and proxies.
        """
        if self._state != ClientState.CLOSED:
            self._state = ClientState.CLOSED

            self._transport.close()
            for transport in self._mounts.values():
                if transport is not None:
                    transport.close()

    def __enter__(self: T) -> T:
        if self._state != ClientState.UNOPENED:
            msg = {
                ClientState.OPENED: "Cannot open a client instance more than once.",
                ClientState.CLOSED: (
                    "Cannot reopen a client instance, once it has been closed."
                ),
            }[self._state]
            raise RuntimeError(msg)

        self._state = ClientState.OPENED

        self._transport.__enter__()
        for transport in self._mounts.values():
            if transport is not None:
                transport.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        self._state = ClientState.CLOSED

        self._transport.__exit__(exc_type, exc_value, traceback)
        for transport in self._mounts.values():
            if transport is not None:
                transport.__exit__(exc_type, exc_value, traceback)


class AsyncClient(BaseClient):
    """
    An asynchronous HTTP client, with connection pooling, HTTP/2, redirects,
    cookie persistence, etc.

    It can be shared between tasks.

    Usage:

    ```python
    >>> async with httpx.AsyncClient() as client:
    >>>     response = await client.get('https://example.org')
    ```

    **Parameters:**

    * **auth** - *(optional)* An authentication class to use when sending
    requests.
    * **params** - *(optional)* Query parameters to include in request URLs, as
    a string, dictionary, or sequence of two-tuples.
    * **headers** - *(optional)* Dictionary of HTTP headers to include when
    sending requests.
    * **cookies** - *(optional)* Dictionary of Cookie items to include when
    sending requests.
    * **verify** - *(optional)* Either `True` to use an SSL context with the
    default CA bundle, `False` to disable verification, or an instance of
    `ssl.SSLContext` to use a custom context.
    * **http2** - *(optional)* A boolean indicating if HTTP/2 support should be
    enabled. Defaults to `False`.
    * **proxy** - *(optional)* A proxy URL where all the traffic should be routed.
    * **timeout** - *(optional)* The timeout configuration to use when sending
    requests.
    * **limits** - *(optional)* The limits configuration to use.
    * **max_redirects** - *(optional)* The maximum number of redirect responses
    that should be followed.
    * **base_url** - *(optional)* A URL to use as the base when building
    request URLs.
    * **transport** - *(optional)* A transport class to use for sending requests
    over the network.
    * **trust_env** - *(optional)* Enables or disables usage of environment
    variables for configuration.
    * **default_encoding** - *(optional)* The default encoding to use for decoding
    response text, if no charset information is included in a response Content-Type
    header. Set to a callable for automatic character set detection. Default: "utf-8".
    """

    def __init__(
        self,
        *,
        auth: AuthTypes | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        verify: ssl.SSLContext | str | bool = True,
        cert: CertTypes | None = None,
        http1: bool = True,
        http2: bool = False,
        proxy: ProxyTypes | None = None,
        mounts: None | (typing.Mapping[str, AsyncBaseTransport | None]) = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        follow_redirects: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        event_hooks: None | (typing.Mapping[str, list[EventHook]]) = None,
        base_url: URL | str = "",
        transport: AsyncBaseTransport | None = None,
        trust_env: bool = True,
        default_encoding: str | typing.Callable[[bytes], str] = "utf-8",
    ) -> None:
        super().__init__(
            auth=auth,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            follow_redirects=follow_redirects,
            max_redirects=max_redirects,
            event_hooks=event_hooks,
            base_url=base_url,
            trust_env=trust_env,
            default_encoding=default_encoding,
        )

        if http2:
            try:
                import h2  # noqa
            except ImportError:  # pragma: no cover
                raise ImportError(
                    "Using http2=True, but the 'h2' package is not installed. "
                    "Make sure to install httpx using `pip install httpx[http2]`."
                ) from None

        allow_env_proxies = trust_env and transport is None
        proxy_map = self._get_proxy_map(proxy, allow_env_proxies)

        self._transport = self._init_transport(
            verify=verify,
            cert=cert,
            trust_env=trust_env,
            http1=http1,
            http2=http2,
            limits=limits,
            transport=transport,
        )

        self._mounts: dict[URLPattern, AsyncBaseTransport | None] = {
            URLPattern(key): None
            if proxy is None
            else self._init_proxy_transport(
                proxy,
                verify=verify,
                cert=cert,
                trust_env=trust_env,
                http1=http1,
                http2=http2,
                limits=limits,
            )
            for key, proxy in proxy_map.items()
        }
        if mounts is not None:
            self._mounts.update(
                {URLPattern(key): transport for key, transport in mounts.items()}
            )
        self._mounts = dict(sorted(self._mounts.items()))

    def _init_transport(
        self,
        verify: ssl.SSLContext | str | bool = True,
        cert: CertTypes | None = None,
        trust_env: bool = True,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        transport: AsyncBaseTransport | None = None,
    ) -> AsyncBaseTransport:
        if transport is not None:
            return transport

        return AsyncHTTPTransport(
            verify=verify,
            cert=cert,
            trust_env=trust_env,
            http1=http1,
            http2=http2,
            limits=limits,
        )

    def _init_proxy_transport(
        self,
        proxy: Proxy,
        verify: ssl.SSLContext | str | bool = True,
        cert: CertTypes | None = None,
        trust_env: bool = True,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
    ) -> AsyncBaseTransport:
        return AsyncHTTPTransport(
            verify=verify,
            cert=cert,
            trust_env=trust_env,
            http1=http1,
            http2=http2,
            limits=limits,
            proxy=proxy,
        )

    def _transport_for_url(self, url: URL) -> AsyncBaseTransport:
        """
        Returns the transport instance that should be used for a given URL.
        This will either be the standard connection pool, or a proxy.
        """
        for pattern, transport in self._mounts.items():
            if pattern.matches(url):
                return self._transport if transport is None else transport

        return self._transport

    async def request(
        self,
        method: str,
        url: URL | str,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault | None = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Build and send a request.

        Equivalent to:

        ```python
        request = client.build_request(...)
        response = await client.send(request, ...)
        ```

        See `AsyncClient.build_request()`, `AsyncClient.send()`
        and [Merging of configuration][0] for how the various parameters
        are merged with client-level configuration.

        [0]: /advanced/clients/#merging-of-configuration
        """

        if cookies is not None:  # pragma: no cover
            message = (
                "Setting per-request cookies=<...> is being deprecated, because "
                "the expected behaviour on cookie persistence is ambiguous. Set "
                "cookies directly on the client instance instead."
            )
            warnings.warn(message, DeprecationWarning, stacklevel=2)

        request = self.build_request(
            method=method,
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            extensions=extensions,
        )
        return await self.send(request, auth=auth, follow_redirects=follow_redirects)

    @asynccontextmanager
    async def stream(
        self,
        method: str,
        url: URL | str,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault | None = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> typing.AsyncIterator[Response]:
        """
        Alternative to `httpx.request()` that streams the response body
        instead of loading it into memory at once.

        **Parameters**: See `httpx.request`.

        See also: [Streaming Responses][0]

        [0]: /quickstart#streaming-responses
        """
        request = self.build_request(
            method=method,
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            extensions=extensions,
        )
        response = await self.send(
            request=request,
            auth=auth,
            follow_redirects=follow_redirects,
            stream=True,
        )
        try:
            yield response
        finally:
            await response.aclose()

    async def send(
        self,
        request: Request,
        *,
        stream: bool = False,
        auth: AuthTypes | UseClientDefault | None = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
    ) -> Response:
        """
        Send a request.

        The request is sent as-is, unmodified.

        Typically you'll want to build one with `AsyncClient.build_request()`
        so that any client-level configuration is merged into the request,
        but passing an explicit `httpx.Request()` is supported as well.

        See also: [Request instances][0]

        [0]: /advanced/clients/#request-instances
        """
        if self._state == ClientState.CLOSED:
            raise RuntimeError("Cannot send a request, as the client has been closed.")

        self._state = ClientState.OPENED
        follow_redirects = (
            self.follow_redirects
            if isinstance(follow_redirects, UseClientDefault)
            else follow_redirects
        )

        self._set_timeout(request)

        auth = self._build_request_auth(request, auth)

        response = await self._send_handling_auth(
            request,
            auth=auth,
            follow_redirects=follow_redirects,
            history=[],
        )
        try:
            if not stream:
                await response.aread()

            return response

        except BaseException as exc:
            await response.aclose()
            raise exc

    async def _send_handling_auth(
        self,
        request: Request,
        auth: Auth,
        follow_redirects: bool,
        history: list[Response],
    ) -> Response:
        auth_flow = auth.async_auth_flow(request)
        try:
            request = await auth_flow.__anext__()

            while True:
                response = await self._send_handling_redirects(
                    request,
                    follow_redirects=follow_redirects,
                    history=history,
                )
                try:
                    try:
                        next_request = await auth_flow.asend(response)
                    except StopAsyncIteration:
                        return response

                    response.history = list(history)
                    await response.aread()
                    request = next_request
                    history.append(response)

                except BaseException as exc:
                    await response.aclose()
                    raise exc
        finally:
            await auth_flow.aclose()

    async def _send_handling_redirects(
        self,
        request: Request,
        follow_redirects: bool,
        history: list[Response],
    ) -> Response:
        while True:
            if len(history) > self.max_redirects:
                raise TooManyRedirects(
                    "Exceeded maximum allowed redirects.", request=request
                )

            for hook in self._event_hooks["request"]:
                await hook(request)

            response = await self._send_single_request(request)
            try:
                for hook in self._event_hooks["response"]:
                    await hook(response)

                response.history = list(history)

                if not response.has_redirect_location:
                    return response

                request = self._build_redirect_request(request, response)
                history = history + [response]

                if follow_redirects:
                    await response.aread()
                else:
                    response.next_request = request
                    return response

            except BaseException as exc:
                await response.aclose()
                raise exc

    async def _send_single_request(self, request: Request) -> Response:
        """
        Sends a single request, without handling any redirections.
        """
        transport = self._transport_for_url(request.url)
        start = time.perf_counter()

        if not isinstance(request.stream, AsyncByteStream):
            raise RuntimeError(
                "Attempted to send an sync request with an AsyncClient instance."
            )

        with request_context(request=request):
            response = await transport.handle_async_request(request)

        assert isinstance(response.stream, AsyncByteStream)
        response.request = request
        response.stream = BoundAsyncStream(
            response.stream, response=response, start=start
        )
        self.cookies.extract_cookies(response)
        response.default_encoding = self._default_encoding

        logger.info(
            'HTTP Request: %s %s "%s %d %s"',
            request.method,
            request.url,
            response.http_version,
            response.status_code,
            response.reason_phrase,
        )

        return response

    async def get(
        self,
        url: URL | str,
        *,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault | None = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send a `GET` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "GET",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def options(
        self,
        url: URL | str,
        *,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send an `OPTIONS` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "OPTIONS",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def head(
        self,
        url: URL | str,
        *,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send a `HEAD` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "HEAD",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def post(
        self,
        url: URL | str,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send a `POST` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "POST",
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def put(
        self,
        url: URL | str,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send a `PUT` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "PUT",
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def patch(
        self,
        url: URL | str,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send a `PATCH` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "PATCH",
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def delete(
        self,
        url: URL | str,
        *,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: RequestExtensions | None = None,
    ) -> Response:
        """
        Send a `DELETE` request.

        **Parameters**: See `httpx.request`.
        """
        return await self.request(
            "DELETE",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def aclose(self) -> None:
        """
        Close transport and proxies.
        """
        if self._state != ClientState.CLOSED:
            self._state = ClientState.CLOSED

            await self._transport.aclose()
            for proxy in self._mounts.values():
                if proxy is not None:
                    await proxy.aclose()

    async def __aenter__(self: U) -> U:
        if self._state != ClientState.UNOPENED:
            msg = {
                ClientState.OPENED: "Cannot open a client instance more than once.",
                ClientState.CLOSED: (
                    "Cannot reopen a client instance, once it has been closed."
                ),
            }[self._state]
            raise RuntimeError(msg)

        self._state = ClientState.OPENED

        await self._transport.__aenter__()
        for proxy in self._mounts.values():
            if proxy is not None:
                await proxy.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        self._state = ClientState.CLOSED

        await self._transport.__aexit__(exc_type, exc_value, traceback)
        for proxy in self._mounts.values():
            if proxy is not None:
                await proxy.__aexit__(exc_type, exc_value, traceback)

# === NexusCore/openenv\Lib\site-packages\openai\_base_client.py ===
from __future__ import annotations

import sys
import json
import time
import uuid
import email
import asyncio
import inspect
import logging
import platform
import email.utils
from types import TracebackType
from random import random
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Type,
    Union,
    Generic,
    Mapping,
    TypeVar,
    Iterable,
    Iterator,
    Optional,
    Generator,
    AsyncIterator,
    cast,
    overload,
)
from typing_extensions import Literal, override, get_origin

import anyio
import httpx
import distro
import pydantic
from httpx import URL
from pydantic import PrivateAttr

from . import _exceptions
from ._qs import Querystring
from ._files import to_httpx_files, async_to_httpx_files
from ._types import (
    NOT_GIVEN,
    Body,
    Omit,
    Query,
    Headers,
    Timeout,
    NotGiven,
    ResponseT,
    AnyMapping,
    PostParser,
    RequestFiles,
    HttpxSendArgs,
    RequestOptions,
    HttpxRequestFiles,
    ModelBuilderProtocol,
)
from ._utils import SensitiveHeadersFilter, is_dict, is_list, asyncify, is_given, lru_cache, is_mapping
from ._compat import PYDANTIC_V2, model_copy, model_dump
from ._models import GenericModel, FinalRequestOptions, validate_type, construct_type
from ._response import (
    APIResponse,
    BaseAPIResponse,
    AsyncAPIResponse,
    extract_response_type,
)
from ._constants import (
    DEFAULT_TIMEOUT,
    MAX_RETRY_DELAY,
    DEFAULT_MAX_RETRIES,
    INITIAL_RETRY_DELAY,
    RAW_RESPONSE_HEADER,
    OVERRIDE_CAST_TO_HEADER,
    DEFAULT_CONNECTION_LIMITS,
)
from ._streaming import Stream, SSEDecoder, AsyncStream, SSEBytesDecoder
from ._exceptions import (
    APIStatusError,
    APITimeoutError,
    APIConnectionError,
    APIResponseValidationError,
)
from ._legacy_response import LegacyAPIResponse

log: logging.Logger = logging.getLogger(__name__)
log.addFilter(SensitiveHeadersFilter())

# TODO: make base page type vars covariant
SyncPageT = TypeVar("SyncPageT", bound="BaseSyncPage[Any]")
AsyncPageT = TypeVar("AsyncPageT", bound="BaseAsyncPage[Any]")


_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)

_StreamT = TypeVar("_StreamT", bound=Stream[Any])
_AsyncStreamT = TypeVar("_AsyncStreamT", bound=AsyncStream[Any])

if TYPE_CHECKING:
    from httpx._config import (
        DEFAULT_TIMEOUT_CONFIG,  # pyright: ignore[reportPrivateImportUsage]
    )

    HTTPX_DEFAULT_TIMEOUT = DEFAULT_TIMEOUT_CONFIG
else:
    try:
        from httpx._config import DEFAULT_TIMEOUT_CONFIG as HTTPX_DEFAULT_TIMEOUT
    except ImportError:
        # taken from https://github.com/encode/httpx/blob/3ba5fe0d7ac70222590e759c31442b1cab263791/httpx/_config.py#L366
        HTTPX_DEFAULT_TIMEOUT = Timeout(5.0)


class PageInfo:
    """Stores the necessary information to build the request to retrieve the next page.

    Either `url` or `params` must be set.
    """

    url: URL | NotGiven
    params: Query | NotGiven
    json: Body | NotGiven

    @overload
    def __init__(
        self,
        *,
        url: URL,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        params: Query,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        json: Body,
    ) -> None: ...

    def __init__(
        self,
        *,
        url: URL | NotGiven = NOT_GIVEN,
        json: Body | NotGiven = NOT_GIVEN,
        params: Query | NotGiven = NOT_GIVEN,
    ) -> None:
        self.url = url
        self.json = json
        self.params = params

    @override
    def __repr__(self) -> str:
        if self.url:
            return f"{self.__class__.__name__}(url={self.url})"
        if self.json:
            return f"{self.__class__.__name__}(json={self.json})"
        return f"{self.__class__.__name__}(params={self.params})"


class BasePage(GenericModel, Generic[_T]):
    """
    Defines the core interface for pagination.

    Type Args:
        ModelT: The pydantic model that represents an item in the response.

    Methods:
        has_next_page(): Check if there is another page available
        next_page_info(): Get the necessary information to make a request for the next page
    """

    _options: FinalRequestOptions = PrivateAttr()
    _model: Type[_T] = PrivateAttr()

    def has_next_page(self) -> bool:
        items = self._get_page_items()
        if not items:
            return False
        return self.next_page_info() is not None

    def next_page_info(self) -> Optional[PageInfo]: ...

    def _get_page_items(self) -> Iterable[_T]:  # type: ignore[empty-body]
        ...

    def _params_from_url(self, url: URL) -> httpx.QueryParams:
        # TODO: do we have to preprocess params here?
        return httpx.QueryParams(cast(Any, self._options.params)).merge(url.params)

    def _info_to_options(self, info: PageInfo) -> FinalRequestOptions:
        options = model_copy(self._options)
        options._strip_raw_response_header()

        if not isinstance(info.params, NotGiven):
            options.params = {**options.params, **info.params}
            return options

        if not isinstance(info.url, NotGiven):
            params = self._params_from_url(info.url)
            url = info.url.copy_with(params=params)
            options.params = dict(url.params)
            options.url = str(url)
            return options

        if not isinstance(info.json, NotGiven):
            if not is_mapping(info.json):
                raise TypeError("Pagination is only supported with mappings")

            if not options.json_data:
                options.json_data = {**info.json}
            else:
                if not is_mapping(options.json_data):
                    raise TypeError("Pagination is only supported with mappings")

                options.json_data = {**options.json_data, **info.json}
            return options

        raise ValueError("Unexpected PageInfo state")


class BaseSyncPage(BasePage[_T], Generic[_T]):
    _client: SyncAPIClient = pydantic.PrivateAttr()

    def _set_private_attributes(
        self,
        client: SyncAPIClient,
        model: Type[_T],
        options: FinalRequestOptions,
    ) -> None:
        if PYDANTIC_V2 and getattr(self, "__pydantic_private__", None) is None:
            self.__pydantic_private__ = {}

        self._model = model
        self._client = client
        self._options = options

    # Pydantic uses a custom `__iter__` method to support casting BaseModels
    # to dictionaries. e.g. dict(model).
    # As we want to support `for item in page`, this is inherently incompatible
    # with the default pydantic behaviour. It is not possible to support both
    # use cases at once. Fortunately, this is not a big deal as all other pydantic
    # methods should continue to work as expected as there is an alternative method
    # to cast a model to a dictionary, model.dict(), which is used internally
    # by pydantic.
    def __iter__(self) -> Iterator[_T]:  # type: ignore
        for page in self.iter_pages():
            for item in page._get_page_items():
                yield item

    def iter_pages(self: SyncPageT) -> Iterator[SyncPageT]:
        page = self
        while True:
            yield page
            if page.has_next_page():
                page = page.get_next_page()
            else:
                return

    def get_next_page(self: SyncPageT) -> SyncPageT:
        info = self.next_page_info()
        if not info:
            raise RuntimeError(
                "No next page expected; please check `.has_next_page()` before calling `.get_next_page()`."
            )

        options = self._info_to_options(info)
        return self._client._request_api_list(self._model, page=self.__class__, options=options)


class AsyncPaginator(Generic[_T, AsyncPageT]):
    def __init__(
        self,
        client: AsyncAPIClient,
        options: FinalRequestOptions,
        page_cls: Type[AsyncPageT],
        model: Type[_T],
    ) -> None:
        self._model = model
        self._client = client
        self._options = options
        self._page_cls = page_cls

    def __await__(self) -> Generator[Any, None, AsyncPageT]:
        return self._get_page().__await__()

    async def _get_page(self) -> AsyncPageT:
        def _parser(resp: AsyncPageT) -> AsyncPageT:
            resp._set_private_attributes(
                model=self._model,
                options=self._options,
                client=self._client,
            )
            return resp

        self._options.post_parser = _parser

        return await self._client.request(self._page_cls, self._options)

    async def __aiter__(self) -> AsyncIterator[_T]:
        # https://github.com/microsoft/pyright/issues/3464
        page = cast(
            AsyncPageT,
            await self,  # type: ignore
        )
        async for item in page:
            yield item


class BaseAsyncPage(BasePage[_T], Generic[_T]):
    _client: AsyncAPIClient = pydantic.PrivateAttr()

    def _set_private_attributes(
        self,
        model: Type[_T],
        client: AsyncAPIClient,
        options: FinalRequestOptions,
    ) -> None:
        if PYDANTIC_V2 and getattr(self, "__pydantic_private__", None) is None:
            self.__pydantic_private__ = {}

        self._model = model
        self._client = client
        self._options = options

    async def __aiter__(self) -> AsyncIterator[_T]:
        async for page in self.iter_pages():
            for item in page._get_page_items():
                yield item

    async def iter_pages(self: AsyncPageT) -> AsyncIterator[AsyncPageT]:
        page = self
        while True:
            yield page
            if page.has_next_page():
                page = await page.get_next_page()
            else:
                return

    async def get_next_page(self: AsyncPageT) -> AsyncPageT:
        info = self.next_page_info()
        if not info:
            raise RuntimeError(
                "No next page expected; please check `.has_next_page()` before calling `.get_next_page()`."
            )

        options = self._info_to_options(info)
        return await self._client._request_api_list(self._model, page=self.__class__, options=options)


_HttpxClientT = TypeVar("_HttpxClientT", bound=Union[httpx.Client, httpx.AsyncClient])
_DefaultStreamT = TypeVar("_DefaultStreamT", bound=Union[Stream[Any], AsyncStream[Any]])


class BaseClient(Generic[_HttpxClientT, _DefaultStreamT]):
    _client: _HttpxClientT
    _version: str
    _base_url: URL
    max_retries: int
    timeout: Union[float, Timeout, None]
    _strict_response_validation: bool
    _idempotency_header: str | None
    _default_stream_cls: type[_DefaultStreamT] | None = None

    def __init__(
        self,
        *,
        version: str,
        base_url: str | URL,
        _strict_response_validation: bool,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float | Timeout | None = DEFAULT_TIMEOUT,
        custom_headers: Mapping[str, str] | None = None,
        custom_query: Mapping[str, object] | None = None,
    ) -> None:
        self._version = version
        self._base_url = self._enforce_trailing_slash(URL(base_url))
        self.max_retries = max_retries
        self.timeout = timeout
        self._custom_headers = custom_headers or {}
        self._custom_query = custom_query or {}
        self._strict_response_validation = _strict_response_validation
        self._idempotency_header = None
        self._platform: Platform | None = None

        if max_retries is None:  # pyright: ignore[reportUnnecessaryComparison]
            raise TypeError(
                "max_retries cannot be None. If you want to disable retries, pass `0`; if you want unlimited retries, pass `math.inf` or a very high number; if you want the default behavior, pass `openai.DEFAULT_MAX_RETRIES`"
            )

    def _enforce_trailing_slash(self, url: URL) -> URL:
        if url.raw_path.endswith(b"/"):
            return url
        return url.copy_with(raw_path=url.raw_path + b"/")

    def _make_status_error_from_response(
        self,
        response: httpx.Response,
    ) -> APIStatusError:
        if response.is_closed and not response.is_stream_consumed:
            # We can't read the response body as it has been closed
            # before it was read. This can happen if an event hook
            # raises a status error.
            body = None
            err_msg = f"Error code: {response.status_code}"
        else:
            err_text = response.text.strip()
            body = err_text

            try:
                body = json.loads(err_text)
                err_msg = f"Error code: {response.status_code} - {body}"
            except Exception:
                err_msg = err_text or f"Error code: {response.status_code}"

        return self._make_status_error(err_msg, body=body, response=response)

    def _make_status_error(
        self,
        err_msg: str,
        *,
        body: object,
        response: httpx.Response,
    ) -> _exceptions.APIStatusError:
        raise NotImplementedError()

    def _build_headers(self, options: FinalRequestOptions, *, retries_taken: int = 0) -> httpx.Headers:
        custom_headers = options.headers or {}
        headers_dict = _merge_mappings(self.default_headers, custom_headers)
        self._validate_headers(headers_dict, custom_headers)

        # headers are case-insensitive while dictionaries are not.
        headers = httpx.Headers(headers_dict)

        idempotency_header = self._idempotency_header
        if idempotency_header and options.idempotency_key and idempotency_header not in headers:
            headers[idempotency_header] = options.idempotency_key

        # Don't set these headers if they were already set or removed by the caller. We check
        # `custom_headers`, which can contain `Omit()`, instead of `headers` to account for the removal case.
        lower_custom_headers = [header.lower() for header in custom_headers]
        if "x-stainless-retry-count" not in lower_custom_headers:
            headers["x-stainless-retry-count"] = str(retries_taken)
        if "x-stainless-read-timeout" not in lower_custom_headers:
            timeout = self.timeout if isinstance(options.timeout, NotGiven) else options.timeout
            if isinstance(timeout, Timeout):
                timeout = timeout.read
            if timeout is not None:
                headers["x-stainless-read-timeout"] = str(timeout)

        return headers

    def _prepare_url(self, url: str) -> URL:
        """
        Merge a URL argument together with any 'base_url' on the client,
        to create the URL used for the outgoing request.
        """
        # Copied from httpx's `_merge_url` method.
        merge_url = URL(url)
        if merge_url.is_relative_url:
            merge_raw_path = self.base_url.raw_path + merge_url.raw_path.lstrip(b"/")
            return self.base_url.copy_with(raw_path=merge_raw_path)

        return merge_url

    def _make_sse_decoder(self) -> SSEDecoder | SSEBytesDecoder:
        return SSEDecoder()

    def _build_request(
        self,
        options: FinalRequestOptions,
        *,
        retries_taken: int = 0,
    ) -> httpx.Request:
        if log.isEnabledFor(logging.DEBUG):
            log.debug("Request options: %s", model_dump(options, exclude_unset=True))

        kwargs: dict[str, Any] = {}

        json_data = options.json_data
        if options.extra_json is not None:
            if json_data is None:
                json_data = cast(Body, options.extra_json)
            elif is_mapping(json_data):
                json_data = _merge_mappings(json_data, options.extra_json)
            else:
                raise RuntimeError(f"Unexpected JSON data type, {type(json_data)}, cannot merge with `extra_body`")

        headers = self._build_headers(options, retries_taken=retries_taken)
        params = _merge_mappings(self.default_query, options.params)
        content_type = headers.get("Content-Type")
        files = options.files

        # If the given Content-Type header is multipart/form-data then it
        # has to be removed so that httpx can generate the header with
        # additional information for us as it has to be in this form
        # for the server to be able to correctly parse the request:
        # multipart/form-data; boundary=---abc--
        if content_type is not None and content_type.startswith("multipart/form-data"):
            if "boundary" not in content_type:
                # only remove the header if the boundary hasn't been explicitly set
                # as the caller doesn't want httpx to come up with their own boundary
                headers.pop("Content-Type")

            # As we are now sending multipart/form-data instead of application/json
            # we need to tell httpx to use it, https://www.python-httpx.org/advanced/clients/#multipart-file-encoding
            if json_data:
                if not is_dict(json_data):
                    raise TypeError(
                        f"Expected query input to be a dictionary for multipart requests but got {type(json_data)} instead."
                    )
                kwargs["data"] = self._serialize_multipartform(json_data)

            # httpx determines whether or not to send a "multipart/form-data"
            # request based on the truthiness of the "files" argument.
            # This gets around that issue by generating a dict value that
            # evaluates to true.
            #
            # https://github.com/encode/httpx/discussions/2399#discussioncomment-3814186
            if not files:
                files = cast(HttpxRequestFiles, ForceMultipartDict())

        prepared_url = self._prepare_url(options.url)
        if "_" in prepared_url.host:
            # work around https://github.com/encode/httpx/discussions/2880
            kwargs["extensions"] = {"sni_hostname": prepared_url.host.replace("_", "-")}

        # TODO: report this error to httpx
        return self._client.build_request(  # pyright: ignore[reportUnknownMemberType]
            headers=headers,
            timeout=self.timeout if isinstance(options.timeout, NotGiven) else options.timeout,
            method=options.method,
            url=prepared_url,
            # the `Query` type that we use is incompatible with qs'
            # `Params` type as it needs to be typed as `Mapping[str, object]`
            # so that passing a `TypedDict` doesn't cause an error.
            # https://github.com/microsoft/pyright/issues/3526#event-6715453066
            params=self.qs.stringify(cast(Mapping[str, Any], params)) if params else None,
            json=json_data if is_given(json_data) else None,
            files=files,
            **kwargs,
        )

    def _serialize_multipartform(self, data: Mapping[object, object]) -> dict[str, object]:
        items = self.qs.stringify_items(
            # TODO: type ignore is required as stringify_items is well typed but we can't be
            # well typed without heavy validation.
            data,  # type: ignore
            array_format="brackets",
        )
        serialized: dict[str, object] = {}
        for key, value in items:
            existing = serialized.get(key)

            if not existing:
                serialized[key] = value
                continue

            # If a value has already been set for this key then that
            # means we're sending data like `array[]=[1, 2, 3]` and we
            # need to tell httpx that we want to send multiple values with
            # the same key which is done by using a list or a tuple.
            #
            # Note: 2d arrays should never result in the same key at both
            # levels so it's safe to assume that if the value is a list,
            # it was because we changed it to be a list.
            if is_list(existing):
                existing.append(value)
            else:
                serialized[key] = [existing, value]

        return serialized

    def _maybe_override_cast_to(self, cast_to: type[ResponseT], options: FinalRequestOptions) -> type[ResponseT]:
        if not is_given(options.headers):
            return cast_to

        # make a copy of the headers so we don't mutate user-input
        headers = dict(options.headers)

        # we internally support defining a temporary header to override the
        # default `cast_to` type for use with `.with_raw_response` and `.with_streaming_response`
        # see _response.py for implementation details
        override_cast_to = headers.pop(OVERRIDE_CAST_TO_HEADER, NOT_GIVEN)
        if is_given(override_cast_to):
            options.headers = headers
            return cast(Type[ResponseT], override_cast_to)

        return cast_to

    def _should_stream_response_body(self, request: httpx.Request) -> bool:
        return request.headers.get(RAW_RESPONSE_HEADER) == "stream"  # type: ignore[no-any-return]

    def _process_response_data(
        self,
        *,
        data: object,
        cast_to: type[ResponseT],
        response: httpx.Response,
    ) -> ResponseT:
        if data is None:
            return cast(ResponseT, None)

        if cast_to is object:
            return cast(ResponseT, data)

        try:
            if inspect.isclass(cast_to) and issubclass(cast_to, ModelBuilderProtocol):
                return cast(ResponseT, cast_to.build(response=response, data=data))

            if self._strict_response_validation:
                return cast(ResponseT, validate_type(type_=cast_to, value=data))

            return cast(ResponseT, construct_type(type_=cast_to, value=data))
        except pydantic.ValidationError as err:
            raise APIResponseValidationError(response=response, body=data) from err

    @property
    def qs(self) -> Querystring:
        return Querystring()

    @property
    def custom_auth(self) -> httpx.Auth | None:
        return None

    @property
    def auth_headers(self) -> dict[str, str]:
        return {}

    @property
    def default_headers(self) -> dict[str, str | Omit]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
            **self.platform_headers(),
            **self.auth_headers,
            **self._custom_headers,
        }

    @property
    def default_query(self) -> dict[str, object]:
        return {
            **self._custom_query,
        }

    def _validate_headers(
        self,
        headers: Headers,  # noqa: ARG002
        custom_headers: Headers,  # noqa: ARG002
    ) -> None:
        """Validate the given default headers and custom headers.

        Does nothing by default.
        """
        return

    @property
    def user_agent(self) -> str:
        return f"{self.__class__.__name__}/Python {self._version}"

    @property
    def base_url(self) -> URL:
        return self._base_url

    @base_url.setter
    def base_url(self, url: URL | str) -> None:
        self._base_url = self._enforce_trailing_slash(url if isinstance(url, URL) else URL(url))

    def platform_headers(self) -> Dict[str, str]:
        # the actual implementation is in a separate `lru_cache` decorated
        # function because adding `lru_cache` to methods will leak memory
        # https://github.com/python/cpython/issues/88476
        return platform_headers(self._version, platform=self._platform)

    def _parse_retry_after_header(self, response_headers: Optional[httpx.Headers] = None) -> float | None:
        """Returns a float of the number of seconds (not milliseconds) to wait after retrying, or None if unspecified.

        About the Retry-After header: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Retry-After
        See also  https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Retry-After#syntax
        """
        if response_headers is None:
            return None

        # First, try the non-standard `retry-after-ms` header for milliseconds,
        # which is more precise than integer-seconds `retry-after`
        try:
            retry_ms_header = response_headers.get("retry-after-ms", None)
            return float(retry_ms_header) / 1000
        except (TypeError, ValueError):
            pass

        # Next, try parsing `retry-after` header as seconds (allowing nonstandard floats).
        retry_header = response_headers.get("retry-after")
        try:
            # note: the spec indicates that this should only ever be an integer
            # but if someone sends a float there's no reason for us to not respect it
            return float(retry_header)
        except (TypeError, ValueError):
            pass

        # Last, try parsing `retry-after` as a date.
        retry_date_tuple = email.utils.parsedate_tz(retry_header)
        if retry_date_tuple is None:
            return None

        retry_date = email.utils.mktime_tz(retry_date_tuple)
        return float(retry_date - time.time())

    def _calculate_retry_timeout(
        self,
        remaining_retries: int,
        options: FinalRequestOptions,
        response_headers: Optional[httpx.Headers] = None,
    ) -> float:
        max_retries = options.get_max_retries(self.max_retries)

        # If the API asks us to wait a certain amount of time (and it's a reasonable amount), just do what it says.
        retry_after = self._parse_retry_after_header(response_headers)
        if retry_after is not None and 0 < retry_after <= 60:
            return retry_after

        # Also cap retry count to 1000 to avoid any potential overflows with `pow`
        nb_retries = min(max_retries - remaining_retries, 1000)

        # Apply exponential backoff, but not more than the max.
        sleep_seconds = min(INITIAL_RETRY_DELAY * pow(2.0, nb_retries), MAX_RETRY_DELAY)

        # Apply some jitter, plus-or-minus half a second.
        jitter = 1 - 0.25 * random()
        timeout = sleep_seconds * jitter
        return timeout if timeout >= 0 else 0

    def _should_retry(self, response: httpx.Response) -> bool:
        # Note: this is not a standard header
        should_retry_header = response.headers.get("x-should-retry")

        # If the server explicitly says whether or not to retry, obey.
        if should_retry_header == "true":
            log.debug("Retrying as header `x-should-retry` is set to `true`")
            return True
        if should_retry_header == "false":
            log.debug("Not retrying as header `x-should-retry` is set to `false`")
            return False

        # Retry on request timeouts.
        if response.status_code == 408:
            log.debug("Retrying due to status code %i", response.status_code)
            return True

        # Retry on lock timeouts.
        if response.status_code == 409:
            log.debug("Retrying due to status code %i", response.status_code)
            return True

        # Retry on rate limits.
        if response.status_code == 429:
            log.debug("Retrying due to status code %i", response.status_code)
            return True

        # Retry internal errors.
        if response.status_code >= 500:
            log.debug("Retrying due to status code %i", response.status_code)
            return True

        log.debug("Not retrying")
        return False

    def _idempotency_key(self) -> str:
        return f"stainless-python-retry-{uuid.uuid4()}"


class _DefaultHttpxClient(httpx.Client):
    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        kwargs.setdefault("limits", DEFAULT_CONNECTION_LIMITS)
        kwargs.setdefault("follow_redirects", True)
        super().__init__(**kwargs)


if TYPE_CHECKING:
    DefaultHttpxClient = httpx.Client
    """An alias to `httpx.Client` that provides the same defaults that this SDK
    uses internally.

    This is useful because overriding the `http_client` with your own instance of
    `httpx.Client` will result in httpx's defaults being used, not ours.
    """
else:
    DefaultHttpxClient = _DefaultHttpxClient


class SyncHttpxClientWrapper(DefaultHttpxClient):
    def __del__(self) -> None:
        if self.is_closed:
            return

        try:
            self.close()
        except Exception:
            pass


class SyncAPIClient(BaseClient[httpx.Client, Stream[Any]]):
    _client: httpx.Client
    _default_stream_cls: type[Stream[Any]] | None = None

    def __init__(
        self,
        *,
        version: str,
        base_url: str | URL,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.Client | None = None,
        custom_headers: Mapping[str, str] | None = None,
        custom_query: Mapping[str, object] | None = None,
        _strict_response_validation: bool,
    ) -> None:
        if not is_given(timeout):
            # if the user passed in a custom http client with a non-default
            # timeout set then we use that timeout.
            #
            # note: there is an edge case here where the user passes in a client
            # where they've explicitly set the timeout to match the default timeout
            # as this check is structural, meaning that we'll think they didn't
            # pass in a timeout and will ignore it
            if http_client and http_client.timeout != HTTPX_DEFAULT_TIMEOUT:
                timeout = http_client.timeout
            else:
                timeout = DEFAULT_TIMEOUT

        if http_client is not None and not isinstance(http_client, httpx.Client):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(
                f"Invalid `http_client` argument; Expected an instance of `httpx.Client` but got {type(http_client)}"
            )

        super().__init__(
            version=version,
            # cast to a valid type because mypy doesn't understand our type narrowing
            timeout=cast(Timeout, timeout),
            base_url=base_url,
            max_retries=max_retries,
            custom_query=custom_query,
            custom_headers=custom_headers,
            _strict_response_validation=_strict_response_validation,
        )
        self._client = http_client or SyncHttpxClientWrapper(
            base_url=base_url,
            # cast to a valid type because mypy doesn't understand our type narrowing
            timeout=cast(Timeout, timeout),
        )

    def is_closed(self) -> bool:
        return self._client.is_closed

    def close(self) -> None:
        """Close the underlying HTTPX client.

        The client will *not* be usable after this.
        """
        # If an error is thrown while constructing a client, self._client
        # may not be present
        if hasattr(self, "_client"):
            self._client.close()

    def __enter__(self: _T) -> _T:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def _prepare_options(
        self,
        options: FinalRequestOptions,  # noqa: ARG002
    ) -> FinalRequestOptions:
        """Hook for mutating the given options"""
        return options

    def _prepare_request(
        self,
        request: httpx.Request,  # noqa: ARG002
    ) -> None:
        """This method is used as a callback for mutating the `Request` object
        after it has been constructed.
        This is useful for cases where you want to add certain headers based off of
        the request properties, e.g. `url`, `method` etc.
        """
        return None

    @overload
    def request(
        self,
        cast_to: Type[ResponseT],
        options: FinalRequestOptions,
        *,
        stream: Literal[True],
        stream_cls: Type[_StreamT],
    ) -> _StreamT: ...

    @overload
    def request(
        self,
        cast_to: Type[ResponseT],
        options: FinalRequestOptions,
        *,
        stream: Literal[False] = False,
    ) -> ResponseT: ...

    @overload
    def request(
        self,
        cast_to: Type[ResponseT],
        options: FinalRequestOptions,
        *,
        stream: bool = False,
        stream_cls: Type[_StreamT] | None = None,
    ) -> ResponseT | _StreamT: ...

    def request(
        self,
        cast_to: Type[ResponseT],
        options: FinalRequestOptions,
        *,
        stream: bool = False,
        stream_cls: type[_StreamT] | None = None,
    ) -> ResponseT | _StreamT:
        cast_to = self._maybe_override_cast_to(cast_to, options)

        # create a copy of the options we were given so that if the
        # options are mutated later & we then retry, the retries are
        # given the original options
        input_options = model_copy(options)
        if input_options.idempotency_key is None and input_options.method.lower() != "get":
            # ensure the idempotency key is reused between requests
            input_options.idempotency_key = self._idempotency_key()

        response: httpx.Response | None = None
        max_retries = input_options.get_max_retries(self.max_retries)

        retries_taken = 0
        for retries_taken in range(max_retries + 1):
            options = model_copy(input_options)
            options = self._prepare_options(options)

            remaining_retries = max_retries - retries_taken
            request = self._build_request(options, retries_taken=retries_taken)
            self._prepare_request(request)

            kwargs: HttpxSendArgs = {}
            if self.custom_auth is not None:
                kwargs["auth"] = self.custom_auth

            if options.follow_redirects is not None:
                kwargs["follow_redirects"] = options.follow_redirects

            log.debug("Sending HTTP Request: %s %s", request.method, request.url)

            response = None
            try:
                response = self._client.send(
                    request,
                    stream=stream or self._should_stream_response_body(request=request),
                    **kwargs,
                )
            except httpx.TimeoutException as err:
                log.debug("Encountered httpx.TimeoutException", exc_info=True)

                if remaining_retries > 0:
                    self._sleep_for_retry(
                        retries_taken=retries_taken,
                        max_retries=max_retries,
                        options=input_options,
                        response=None,
                    )
                    continue

                log.debug("Raising timeout error")
                raise APITimeoutError(request=request) from err
            except Exception as err:
                log.debug("Encountered Exception", exc_info=True)

                if remaining_retries > 0:
                    self._sleep_for_retry(
                        retries_taken=retries_taken,
                        max_retries=max_retries,
                        options=input_options,
                        response=None,
                    )
                    continue

                log.debug("Raising connection error")
                raise APIConnectionError(request=request) from err

            log.debug(
                'HTTP Response: %s %s "%i %s" %s',
                request.method,
                request.url,
                response.status_code,
                response.reason_phrase,
                response.headers,
            )
            log.debug("request_id: %s", response.headers.get("x-request-id"))

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as err:  # thrown on 4xx and 5xx status code
                log.debug("Encountered httpx.HTTPStatusError", exc_info=True)

                if remaining_retries > 0 and self._should_retry(err.response):
                    err.response.close()
                    self._sleep_for_retry(
                        retries_taken=retries_taken,
                        max_retries=max_retries,
                        options=input_options,
                        response=response,
                    )
                    continue

                # If the response is streamed then we need to explicitly read the response
                # to completion before attempting to access the response text.
                if not err.response.is_closed:
                    err.response.read()

                log.debug("Re-raising status error")
                raise self._make_status_error_from_response(err.response) from None

            break

        assert response is not None, "could not resolve response (should never happen)"
        return self._process_response(
            cast_to=cast_to,
            options=options,
            response=response,
            stream=stream,
            stream_cls=stream_cls,
            retries_taken=retries_taken,
        )

    def _sleep_for_retry(
        self, *, retries_taken: int, max_retries: int, options: FinalRequestOptions, response: httpx.Response | None
    ) -> None:
        remaining_retries = max_retries - retries_taken
        if remaining_retries == 1:
            log.debug("1 retry left")
        else:
            log.debug("%i retries left", remaining_retries)

        timeout = self._calculate_retry_timeout(remaining_retries, options, response.headers if response else None)
        log.info("Retrying request to %s in %f seconds", options.url, timeout)

        time.sleep(timeout)

    def _process_response(
        self,
        *,
        cast_to: Type[ResponseT],
        options: FinalRequestOptions,
        response: httpx.Response,
        stream: bool,
        stream_cls: type[Stream[Any]] | type[AsyncStream[Any]] | None,
        retries_taken: int = 0,
    ) -> ResponseT:
        if response.request.headers.get(RAW_RESPONSE_HEADER) == "true":
            return cast(
                ResponseT,
                LegacyAPIResponse(
                    raw=response,
                    client=self,
                    cast_to=cast_to,
                    stream=stream,
                    stream_cls=stream_cls,
                    options=options,
                    retries_taken=retries_taken,
                ),
            )

        origin = get_origin(cast_to) or cast_to

        if (
            inspect.isclass(origin)
            and issubclass(origin, BaseAPIResponse)
            # we only want to actually return the custom BaseAPIResponse class if we're
            # returning the raw response, or if we're not streaming SSE, as if we're streaming
            # SSE then `cast_to` doesn't actively reflect the type we need to parse into
            and (not stream or bool(response.request.headers.get(RAW_RESPONSE_HEADER)))
        ):
            if not issubclass(origin, APIResponse):
                raise TypeError(f"API Response types must subclass {APIResponse}; Received {origin}")

            response_cls = cast("type[BaseAPIResponse[Any]]", cast_to)
            return cast(
                ResponseT,
                response_cls(
                    raw=response,
                    client=self,
                    cast_to=extract_response_type(response_cls),
                    stream=stream,
                    stream_cls=stream_cls,
                    options=options,
                    retries_taken=retries_taken,
                ),
            )

        if cast_to == httpx.Response:
            return cast(ResponseT, response)

        api_response = APIResponse(
            raw=response,
            client=self,
            cast_to=cast("type[ResponseT]", cast_to),  # pyright: ignore[reportUnnecessaryCast]
            stream=stream,
            stream_cls=stream_cls,
            options=options,
            retries_taken=retries_taken,
        )
        if bool(response.request.headers.get(RAW_RESPONSE_HEADER)):
            return cast(ResponseT, api_response)

        return api_response.parse()

    def _request_api_list(
        self,
        model: Type[object],
        page: Type[SyncPageT],
        options: FinalRequestOptions,
    ) -> SyncPageT:
        def _parser(resp: SyncPageT) -> SyncPageT:
            resp._set_private_attributes(
                client=self,
                model=model,
                options=options,
            )
            return resp

        options.post_parser = _parser

        return self.request(page, options, stream=False)

    @overload
    def get(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        options: RequestOptions = {},
        stream: Literal[False] = False,
    ) -> ResponseT: ...

    @overload
    def get(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        options: RequestOptions = {},
        stream: Literal[True],
        stream_cls: type[_StreamT],
    ) -> _StreamT: ...

    @overload
    def get(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        options: RequestOptions = {},
        stream: bool,
        stream_cls: type[_StreamT] | None = None,
    ) -> ResponseT | _StreamT: ...

    def get(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        options: RequestOptions = {},
        stream: bool = False,
        stream_cls: type[_StreamT] | None = None,
    ) -> ResponseT | _StreamT:
        opts = FinalRequestOptions.construct(method="get", url=path, **options)
        # cast is required because mypy complains about returning Any even though
        # it understands the type variables
        return cast(ResponseT, self.request(cast_to, opts, stream=stream, stream_cls=stream_cls))

    @overload
    def post(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        options: RequestOptions = {},
        files: RequestFiles | None = None,
        stream: Literal[False] = False,
    ) -> ResponseT: ...

    @overload
    def post(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        options: RequestOptions = {},
        files: RequestFiles | None = None,
        stream: Literal[True],
        stream_cls: type[_StreamT],
    ) -> _StreamT: ...

    @overload
    def post(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        options: RequestOptions = {},
        files: RequestFiles | None = None,
        stream: bool,
        stream_cls: type[_StreamT] | None = None,
    ) -> ResponseT | _StreamT: ...

    def post(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        options: RequestOptions = {},
        files: RequestFiles | None = None,
        stream: bool = False,
        stream_cls: type[_StreamT] | None = None,
    ) -> ResponseT | _StreamT:
        opts = FinalRequestOptions.construct(
            method="post", url=path, json_data=body, files=to_httpx_files(files), **options
        )
        return cast(ResponseT, self.request(cast_to, opts, stream=stream, stream_cls=stream_cls))

    def patch(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        options: RequestOptions = {},
    ) -> ResponseT:
        opts = FinalRequestOptions.construct(method="patch", url=path, json_data=body, **options)
        return self.request(cast_to, opts)

    def put(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        files: RequestFiles | None = None,
        options: RequestOptions = {},
    ) -> ResponseT:
        opts = FinalRequestOptions.construct(
            method="put", url=path, json_data=body, files=to_httpx_files(files), **options
        )
        return self.request(cast_to, opts)

    def delete(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        options: RequestOptions = {},
    ) -> ResponseT:
        opts = FinalRequestOptions.construct(method="delete", url=path, json_data=body, **options)
        return self.request(cast_to, opts)

    def get_api_list(
        self,
        path: str,
        *,
        model: Type[object],
        page: Type[SyncPageT],
        body: Body | None = None,
        options: RequestOptions = {},
        method: str = "get",
    ) -> SyncPageT:
        opts = FinalRequestOptions.construct(method=method, url=path, json_data=body, **options)
        return self._request_api_list(model, page, opts)


class _DefaultAsyncHttpxClient(httpx.AsyncClient):
    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        kwargs.setdefault("limits", DEFAULT_CONNECTION_LIMITS)
        kwargs.setdefault("follow_redirects", True)
        super().__init__(**kwargs)


try:
    import httpx_aiohttp
except ImportError:

    class _DefaultAioHttpClient(httpx.AsyncClient):
        def __init__(self, **_kwargs: Any) -> None:
            raise RuntimeError("To use the aiohttp client you must have installed the package with the `aiohttp` extra")
else:

    class _DefaultAioHttpClient(httpx_aiohttp.HttpxAiohttpClient):  # type: ignore
        def __init__(self, **kwargs: Any) -> None:
            kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
            kwargs.setdefault("limits", DEFAULT_CONNECTION_LIMITS)
            kwargs.setdefault("follow_redirects", True)

            super().__init__(**kwargs)


if TYPE_CHECKING:
    DefaultAsyncHttpxClient = httpx.AsyncClient
    """An alias to `httpx.AsyncClient` that provides the same defaults that this SDK
    uses internally.

    This is useful because overriding the `http_client` with your own instance of
    `httpx.AsyncClient` will result in httpx's defaults being used, not ours.
    """

    DefaultAioHttpClient = httpx.AsyncClient
    """An alias to `httpx.AsyncClient` that changes the default HTTP transport to `aiohttp`."""
else:
    DefaultAsyncHttpxClient = _DefaultAsyncHttpxClient
    DefaultAioHttpClient = _DefaultAioHttpClient


class AsyncHttpxClientWrapper(DefaultAsyncHttpxClient):
    def __del__(self) -> None:
        if self.is_closed:
            return

        try:
            # TODO(someday): support non asyncio runtimes here
            asyncio.get_running_loop().create_task(self.aclose())
        except Exception:
            pass


class AsyncAPIClient(BaseClient[httpx.AsyncClient, AsyncStream[Any]]):
    _client: httpx.AsyncClient
    _default_stream_cls: type[AsyncStream[Any]] | None = None

    def __init__(
        self,
        *,
        version: str,
        base_url: str | URL,
        _strict_response_validation: bool,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.AsyncClient | None = None,
        custom_headers: Mapping[str, str] | None = None,
        custom_query: Mapping[str, object] | None = None,
    ) -> None:
        if not is_given(timeout):
            # if the user passed in a custom http client with a non-default
            # timeout set then we use that timeout.
            #
            # note: there is an edge case here where the user passes in a client
            # where they've explicitly set the timeout to match the default timeout
            # as this check is structural, meaning that we'll think they didn't
            # pass in a timeout and will ignore it
            if http_client and http_client.timeout != HTTPX_DEFAULT_TIMEOUT:
                timeout = http_client.timeout
            else:
                timeout = DEFAULT_TIMEOUT

        if http_client is not None and not isinstance(http_client, httpx.AsyncClient):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(
                f"Invalid `http_client` argument; Expected an instance of `httpx.AsyncClient` but got {type(http_client)}"
            )

        super().__init__(
            version=version,
            base_url=base_url,
            # cast to a valid type because mypy doesn't understand our type narrowing
            timeout=cast(Timeout, timeout),
            max_retries=max_retries,
            custom_query=custom_query,
            custom_headers=custom_headers,
            _strict_response_validation=_strict_response_validation,
        )
        self._client = http_client or AsyncHttpxClientWrapper(
            base_url=base_url,
            # cast to a valid type because mypy doesn't understand our type narrowing
            timeout=cast(Timeout, timeout),
        )

    def is_closed(self) -> bool:
        return self._client.is_closed

    async def close(self) -> None:
        """Close the underlying HTTPX client.

        The client will *not* be usable after this.
        """
        await self._client.aclose()

    async def __aenter__(self: _T) -> _T:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def _prepare_options(
        self,
        options: FinalRequestOptions,  # noqa: ARG002
    ) -> FinalRequestOptions:
        """Hook for mutating the given options"""
        return options

    async def _prepare_request(
        self,
        request: httpx.Request,  # noqa: ARG002
    ) -> None:
        """This method is used as a callback for mutating the `Request` object
        after it has been constructed.
        This is useful for cases where you want to add certain headers based off of
        the request properties, e.g. `url`, `method` etc.
        """
        return None

    @overload
    async def request(
        self,
        cast_to: Type[ResponseT],
        options: FinalRequestOptions,
        *,
        stream: Literal[False] = False,
    ) -> ResponseT: ...

    @overload
    async def request(
        self,
        cast_to: Type[ResponseT],
        options: FinalRequestOptions,
        *,
        stream: Literal[True],
        stream_cls: type[_AsyncStreamT],
    ) -> _AsyncStreamT: ...

    @overload
    async def request(
        self,
        cast_to: Type[ResponseT],
        options: FinalRequestOptions,
        *,
        stream: bool,
        stream_cls: type[_AsyncStreamT] | None = None,
    ) -> ResponseT | _AsyncStreamT: ...

    async def request(
        self,
        cast_to: Type[ResponseT],
        options: FinalRequestOptions,
        *,
        stream: bool = False,
        stream_cls: type[_AsyncStreamT] | None = None,
    ) -> ResponseT | _AsyncStreamT:
        if self._platform is None:
            # `get_platform` can make blocking IO calls so we
            # execute it earlier while we are in an async context
            self._platform = await asyncify(get_platform)()

        cast_to = self._maybe_override_cast_to(cast_to, options)

        # create a copy of the options we were given so that if the
        # options are mutated later & we then retry, the retries are
        # given the original options
        input_options = model_copy(options)
        if input_options.idempotency_key is None and input_options.method.lower() != "get":
            # ensure the idempotency key is reused between requests
            input_options.idempotency_key = self._idempotency_key()

        response: httpx.Response | None = None
        max_retries = input_options.get_max_retries(self.max_retries)

        retries_taken = 0
        for retries_taken in range(max_retries + 1):
            options = model_copy(input_options)
            options = await self._prepare_options(options)

            remaining_retries = max_retries - retries_taken
            request = self._build_request(options, retries_taken=retries_taken)
            await self._prepare_request(request)

            kwargs: HttpxSendArgs = {}
            if self.custom_auth is not None:
                kwargs["auth"] = self.custom_auth

            if options.follow_redirects is not None:
                kwargs["follow_redirects"] = options.follow_redirects

            log.debug("Sending HTTP Request: %s %s", request.method, request.url)

            response = None
            try:
                response = await self._client.send(
                    request,
                    stream=stream or self._should_stream_response_body(request=request),
                    **kwargs,
                )
            except httpx.TimeoutException as err:
                log.debug("Encountered httpx.TimeoutException", exc_info=True)

                if remaining_retries > 0:
                    await self._sleep_for_retry(
                        retries_taken=retries_taken,
                        max_retries=max_retries,
                        options=input_options,
                        response=None,
                    )
                    continue

                log.debug("Raising timeout error")
                raise APITimeoutError(request=request) from err
            except Exception as err:
                log.debug("Encountered Exception", exc_info=True)

                if remaining_retries > 0:
                    await self._sleep_for_retry(
                        retries_taken=retries_taken,
                        max_retries=max_retries,
                        options=input_options,
                        response=None,
                    )
                    continue

                log.debug("Raising connection error")
                raise APIConnectionError(request=request) from err

            log.debug(
                'HTTP Response: %s %s "%i %s" %s',
                request.method,
                request.url,
                response.status_code,
                response.reason_phrase,
                response.headers,
            )
            log.debug("request_id: %s", response.headers.get("x-request-id"))

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as err:  # thrown on 4xx and 5xx status code
                log.debug("Encountered httpx.HTTPStatusError", exc_info=True)

                if remaining_retries > 0 and self._should_retry(err.response):
                    await err.response.aclose()
                    await self._sleep_for_retry(
                        retries_taken=retries_taken,
                        max_retries=max_retries,
                        options=input_options,
                        response=response,
                    )
                    continue

                # If the response is streamed then we need to explicitly read the response
                # to completion before attempting to access the response text.
                if not err.response.is_closed:
                    await err.response.aread()

                log.debug("Re-raising status error")
                raise self._make_status_error_from_response(err.response) from None

            break

        assert response is not None, "could not resolve response (should never happen)"
        return await self._process_response(
            cast_to=cast_to,
            options=options,
            response=response,
            stream=stream,
            stream_cls=stream_cls,
            retries_taken=retries_taken,
        )

    async def _sleep_for_retry(
        self, *, retries_taken: int, max_retries: int, options: FinalRequestOptions, response: httpx.Response | None
    ) -> None:
        remaining_retries = max_retries - retries_taken
        if remaining_retries == 1:
            log.debug("1 retry left")
        else:
            log.debug("%i retries left", remaining_retries)

        timeout = self._calculate_retry_timeout(remaining_retries, options, response.headers if response else None)
        log.info("Retrying request to %s in %f seconds", options.url, timeout)

        await anyio.sleep(timeout)

    async def _process_response(
        self,
        *,
        cast_to: Type[ResponseT],
        options: FinalRequestOptions,
        response: httpx.Response,
        stream: bool,
        stream_cls: type[Stream[Any]] | type[AsyncStream[Any]] | None,
        retries_taken: int = 0,
    ) -> ResponseT:
        if response.request.headers.get(RAW_RESPONSE_HEADER) == "true":
            return cast(
                ResponseT,
                LegacyAPIResponse(
                    raw=response,
                    client=self,
                    cast_to=cast_to,
                    stream=stream,
                    stream_cls=stream_cls,
                    options=options,
                    retries_taken=retries_taken,
                ),
            )

        origin = get_origin(cast_to) or cast_to

        if (
            inspect.isclass(origin)
            and issubclass(origin, BaseAPIResponse)
            # we only want to actually return the custom BaseAPIResponse class if we're
            # returning the raw response, or if we're not streaming SSE, as if we're streaming
            # SSE then `cast_to` doesn't actively reflect the type we need to parse into
            and (not stream or bool(response.request.headers.get(RAW_RESPONSE_HEADER)))
        ):
            if not issubclass(origin, AsyncAPIResponse):
                raise TypeError(f"API Response types must subclass {AsyncAPIResponse}; Received {origin}")

            response_cls = cast("type[BaseAPIResponse[Any]]", cast_to)
            return cast(
                "ResponseT",
                response_cls(
                    raw=response,
                    client=self,
                    cast_to=extract_response_type(response_cls),
                    stream=stream,
                    stream_cls=stream_cls,
                    options=options,
                    retries_taken=retries_taken,
                ),
            )

        if cast_to == httpx.Response:
            return cast(ResponseT, response)

        api_response = AsyncAPIResponse(
            raw=response,
            client=self,
            cast_to=cast("type[ResponseT]", cast_to),  # pyright: ignore[reportUnnecessaryCast]
            stream=stream,
            stream_cls=stream_cls,
            options=options,
            retries_taken=retries_taken,
        )
        if bool(response.request.headers.get(RAW_RESPONSE_HEADER)):
            return cast(ResponseT, api_response)

        return await api_response.parse()

    def _request_api_list(
        self,
        model: Type[_T],
        page: Type[AsyncPageT],
        options: FinalRequestOptions,
    ) -> AsyncPaginator[_T, AsyncPageT]:
        return AsyncPaginator(client=self, options=options, page_cls=page, model=model)

    @overload
    async def get(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        options: RequestOptions = {},
        stream: Literal[False] = False,
    ) -> ResponseT: ...

    @overload
    async def get(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        options: RequestOptions = {},
        stream: Literal[True],
        stream_cls: type[_AsyncStreamT],
    ) -> _AsyncStreamT: ...

    @overload
    async def get(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        options: RequestOptions = {},
        stream: bool,
        stream_cls: type[_AsyncStreamT] | None = None,
    ) -> ResponseT | _AsyncStreamT: ...

    async def get(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        options: RequestOptions = {},
        stream: bool = False,
        stream_cls: type[_AsyncStreamT] | None = None,
    ) -> ResponseT | _AsyncStreamT:
        opts = FinalRequestOptions.construct(method="get", url=path, **options)
        return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)

    @overload
    async def post(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        files: RequestFiles | None = None,
        options: RequestOptions = {},
        stream: Literal[False] = False,
    ) -> ResponseT: ...

    @overload
    async def post(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        files: RequestFiles | None = None,
        options: RequestOptions = {},
        stream: Literal[True],
        stream_cls: type[_AsyncStreamT],
    ) -> _AsyncStreamT: ...

    @overload
    async def post(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        files: RequestFiles | None = None,
        options: RequestOptions = {},
        stream: bool,
        stream_cls: type[_AsyncStreamT] | None = None,
    ) -> ResponseT | _AsyncStreamT: ...

    async def post(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        files: RequestFiles | None = None,
        options: RequestOptions = {},
        stream: bool = False,
        stream_cls: type[_AsyncStreamT] | None = None,
    ) -> ResponseT | _AsyncStreamT:
        opts = FinalRequestOptions.construct(
            method="post", url=path, json_data=body, files=await async_to_httpx_files(files), **options
        )
        return await self.request(cast_to, opts, stream=stream, stream_cls=stream_cls)

    async def patch(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        options: RequestOptions = {},
    ) -> ResponseT:
        opts = FinalRequestOptions.construct(method="patch", url=path, json_data=body, **options)
        return await self.request(cast_to, opts)

    async def put(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        files: RequestFiles | None = None,
        options: RequestOptions = {},
    ) -> ResponseT:
        opts = FinalRequestOptions.construct(
            method="put", url=path, json_data=body, files=await async_to_httpx_files(files), **options
        )
        return await self.request(cast_to, opts)

    async def delete(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        body: Body | None = None,
        options: RequestOptions = {},
    ) -> ResponseT:
        opts = FinalRequestOptions.construct(method="delete", url=path, json_data=body, **options)
        return await self.request(cast_to, opts)

    def get_api_list(
        self,
        path: str,
        *,
        model: Type[_T],
        page: Type[AsyncPageT],
        body: Body | None = None,
        options: RequestOptions = {},
        method: str = "get",
    ) -> AsyncPaginator[_T, AsyncPageT]:
        opts = FinalRequestOptions.construct(method=method, url=path, json_data=body, **options)
        return self._request_api_list(model, page, opts)


def make_request_options(
    *,
    query: Query | None = None,
    extra_headers: Headers | None = None,
    extra_query: Query | None = None,
    extra_body: Body | None = None,
    idempotency_key: str | None = None,
    timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    post_parser: PostParser | NotGiven = NOT_GIVEN,
) -> RequestOptions:
    """Create a dict of type RequestOptions without keys of NotGiven values."""
    options: RequestOptions = {}
    if extra_headers is not None:
        options["headers"] = extra_headers

    if extra_body is not None:
        options["extra_json"] = cast(AnyMapping, extra_body)

    if query is not None:
        options["params"] = query

    if extra_query is not None:
        options["params"] = {**options.get("params", {}), **extra_query}

    if not isinstance(timeout, NotGiven):
        options["timeout"] = timeout

    if idempotency_key is not None:
        options["idempotency_key"] = idempotency_key

    if is_given(post_parser):
        # internal
        options["post_parser"] = post_parser  # type: ignore

    return options


class ForceMultipartDict(Dict[str, None]):
    def __bool__(self) -> bool:
        return True


class OtherPlatform:
    def __init__(self, name: str) -> None:
        self.name = name

    @override
    def __str__(self) -> str:
        return f"Other:{self.name}"


Platform = Union[
    OtherPlatform,
    Literal[
        "MacOS",
        "Linux",
        "Windows",
        "FreeBSD",
        "OpenBSD",
        "iOS",
        "Android",
        "Unknown",
    ],
]


def get_platform() -> Platform:
    try:
        system = platform.system().lower()
        platform_name = platform.platform().lower()
    except Exception:
        return "Unknown"

    if "iphone" in platform_name or "ipad" in platform_name:
        # Tested using Python3IDE on an iPhone 11 and Pythonista on an iPad 7
        # system is Darwin and platform_name is a string like:
        # - Darwin-21.6.0-iPhone12,1-64bit
        # - Darwin-21.6.0-iPad7,11-64bit
        return "iOS"

    if system == "darwin":
        return "MacOS"

    if system == "windows":
        return "Windows"

    if "android" in platform_name:
        # Tested using Pydroid 3
        # system is Linux and platform_name is a string like 'Linux-5.10.81-android12-9-00001-geba40aecb3b7-ab8534902-aarch64-with-libc'
        return "Android"

    if system == "linux":
        # https://distro.readthedocs.io/en/latest/#distro.id
        distro_id = distro.id()
        if distro_id == "freebsd":
            return "FreeBSD"

        if distro_id == "openbsd":
            return "OpenBSD"

        return "Linux"

    if platform_name:
        return OtherPlatform(platform_name)

    return "Unknown"


@lru_cache(maxsize=None)
def platform_headers(version: str, *, platform: Platform | None) -> Dict[str, str]:
    return {
        "X-Stainless-Lang": "python",
        "X-Stainless-Package-Version": version,
        "X-Stainless-OS": str(platform or get_platform()),
        "X-Stainless-Arch": str(get_architecture()),
        "X-Stainless-Runtime": get_python_runtime(),
        "X-Stainless-Runtime-Version": get_python_version(),
    }


class OtherArch:
    def __init__(self, name: str) -> None:
        self.name = name

    @override
    def __str__(self) -> str:
        return f"other:{self.name}"


Arch = Union[OtherArch, Literal["x32", "x64", "arm", "arm64", "unknown"]]


def get_python_runtime() -> str:
    try:
        return platform.python_implementation()
    except Exception:
        return "unknown"


def get_python_version() -> str:
    try:
        return platform.python_version()
    except Exception:
        return "unknown"


def get_architecture() -> Arch:
    try:
        machine = platform.machine().lower()
    except Exception:
        return "unknown"

    if machine in ("arm64", "aarch64"):
        return "arm64"

    # TODO: untested
    if machine == "arm":
        return "arm"

    if machine == "x86_64":
        return "x64"

    # TODO: untested
    if sys.maxsize <= 2**32:
        return "x32"

    if machine:
        return OtherArch(machine)

    return "unknown"


def _merge_mappings(
    obj1: Mapping[_T_co, Union[_T, Omit]],
    obj2: Mapping[_T_co, Union[_T, Omit]],
) -> Dict[_T_co, _T]:
    """Merge two mappings of the same type, removing any values that are instances of `Omit`.

    In cases with duplicate keys the second mapping takes precedence.
    """
    merged = {**obj1, **obj2}
    return {key: value for key, value in merged.items() if not isinstance(value, Omit)}

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\prometheus.py ===
# used for /metrics endpoint on LiteLLM Proxy
#### What this does ####
#    On success, log events to Prometheus
import sys
from datetime import datetime, timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    cast,
)

import litellm
from litellm._logging import print_verbose, verbose_logger
from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy._types import LiteLLM_TeamTable, UserAPIKeyAuth
from litellm.types.integrations.prometheus import *
from litellm.types.utils import StandardLoggingPayload
from litellm.utils import get_end_user_id_for_cost_tracking

if TYPE_CHECKING:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
else:
    AsyncIOScheduler = Any


class PrometheusLogger(CustomLogger):
    # Class variables or attributes
    def __init__(
        self,
        **kwargs,
    ):
        try:
            from prometheus_client import Counter, Gauge, Histogram

            from litellm.proxy.proxy_server import CommonProxyErrors, premium_user

            # Always initialize label_filters, even for non-premium users
            self.label_filters = self._parse_prometheus_config()

            if premium_user is not True:
                verbose_logger.warning(
                    f"🚨🚨🚨 Prometheus Metrics is on LiteLLM Enterprise\n🚨 {CommonProxyErrors.not_premium_user.value}"
                )
                self.litellm_not_a_premium_user_metric = Counter(
                    name="litellm_not_a_premium_user_metric",
                    documentation=f"🚨🚨🚨 Prometheus Metrics is on LiteLLM Enterprise. 🚨 {CommonProxyErrors.not_premium_user.value}",
                )
                return

            # Create metric factory functions
            self._counter_factory = self._create_metric_factory(Counter)
            self._gauge_factory = self._create_metric_factory(Gauge)
            self._histogram_factory = self._create_metric_factory(Histogram)

            self.litellm_proxy_failed_requests_metric = self._counter_factory(
                name="litellm_proxy_failed_requests_metric",
                documentation="Total number of failed responses from proxy - the client did not get a success response from litellm proxy",
                labelnames=self.get_labels_for_metric(
                    "litellm_proxy_failed_requests_metric"
                ),
            )

            self.litellm_proxy_total_requests_metric = self._counter_factory(
                name="litellm_proxy_total_requests_metric",
                documentation="Total number of requests made to the proxy server - track number of client side requests",
                labelnames=self.get_labels_for_metric(
                    "litellm_proxy_total_requests_metric"
                ),
            )

            # request latency metrics
            self.litellm_request_total_latency_metric = self._histogram_factory(
                "litellm_request_total_latency_metric",
                "Total latency (seconds) for a request to LiteLLM",
                labelnames=self.get_labels_for_metric(
                    "litellm_request_total_latency_metric"
                ),
                buckets=LATENCY_BUCKETS,
            )

            self.litellm_llm_api_latency_metric = self._histogram_factory(
                "litellm_llm_api_latency_metric",
                "Total latency (seconds) for a models LLM API call",
                labelnames=self.get_labels_for_metric("litellm_llm_api_latency_metric"),
                buckets=LATENCY_BUCKETS,
            )

            self.litellm_llm_api_time_to_first_token_metric = self._histogram_factory(
                "litellm_llm_api_time_to_first_token_metric",
                "Time to first token for a models LLM API call",
                labelnames=[
                    "model",
                    "hashed_api_key",
                    "api_key_alias",
                    "team",
                    "team_alias",
                ],
                buckets=LATENCY_BUCKETS,
            )

            # Counter for spend
            self.litellm_spend_metric = self._counter_factory(
                "litellm_spend_metric",
                "Total spend on LLM requests",
                labelnames=[
                    "end_user",
                    "hashed_api_key",
                    "api_key_alias",
                    "model",
                    "team",
                    "team_alias",
                    "user",
                ],
            )

            # Counter for total_output_tokens
            self.litellm_tokens_metric = self._counter_factory(
                "litellm_total_tokens",
                "Total number of input + output tokens from LLM requests",
                labelnames=self.get_labels_for_metric("litellm_total_tokens_metric"),
            )

            self.litellm_input_tokens_metric = self._counter_factory(
                "litellm_input_tokens",
                "Total number of input tokens from LLM requests",
                labelnames=self.get_labels_for_metric("litellm_input_tokens_metric"),
            )

            self.litellm_output_tokens_metric = self._counter_factory(
                "litellm_output_tokens",
                "Total number of output tokens from LLM requests",
                labelnames=self.get_labels_for_metric("litellm_output_tokens_metric"),
            )

            # Remaining Budget for Team
            self.litellm_remaining_team_budget_metric = self._gauge_factory(
                "litellm_remaining_team_budget_metric",
                "Remaining budget for team",
                labelnames=self.get_labels_for_metric(
                    "litellm_remaining_team_budget_metric"
                ),
            )

            # Max Budget for Team
            self.litellm_team_max_budget_metric = self._gauge_factory(
                "litellm_team_max_budget_metric",
                "Maximum budget set for team",
                labelnames=self.get_labels_for_metric("litellm_team_max_budget_metric"),
            )

            # Team Budget Reset At
            self.litellm_team_budget_remaining_hours_metric = self._gauge_factory(
                "litellm_team_budget_remaining_hours_metric",
                "Remaining days for team budget to be reset",
                labelnames=self.get_labels_for_metric(
                    "litellm_team_budget_remaining_hours_metric"
                ),
            )

            # Remaining Budget for API Key
            self.litellm_remaining_api_key_budget_metric = self._gauge_factory(
                "litellm_remaining_api_key_budget_metric",
                "Remaining budget for api key",
                labelnames=self.get_labels_for_metric(
                    "litellm_remaining_api_key_budget_metric"
                ),
            )

            # Max Budget for API Key
            self.litellm_api_key_max_budget_metric = self._gauge_factory(
                "litellm_api_key_max_budget_metric",
                "Maximum budget set for api key",
                labelnames=self.get_labels_for_metric(
                    "litellm_api_key_max_budget_metric"
                ),
            )

            self.litellm_api_key_budget_remaining_hours_metric = self._gauge_factory(
                "litellm_api_key_budget_remaining_hours_metric",
                "Remaining hours for api key budget to be reset",
                labelnames=self.get_labels_for_metric(
                    "litellm_api_key_budget_remaining_hours_metric"
                ),
            )

            ########################################
            # LiteLLM Virtual API KEY metrics
            ########################################
            # Remaining MODEL RPM limit for API Key
            self.litellm_remaining_api_key_requests_for_model = self._gauge_factory(
                "litellm_remaining_api_key_requests_for_model",
                "Remaining Requests API Key can make for model (model based rpm limit on key)",
                labelnames=["hashed_api_key", "api_key_alias", "model"],
            )

            # Remaining MODEL TPM limit for API Key
            self.litellm_remaining_api_key_tokens_for_model = self._gauge_factory(
                "litellm_remaining_api_key_tokens_for_model",
                "Remaining Tokens API Key can make for model (model based tpm limit on key)",
                labelnames=["hashed_api_key", "api_key_alias", "model"],
            )

            ########################################
            # LLM API Deployment Metrics / analytics
            ########################################

            # Remaining Rate Limit for model
            self.litellm_remaining_requests_metric = self._gauge_factory(
                "litellm_remaining_requests",
                "LLM Deployment Analytics - remaining requests for model, returned from LLM API Provider",
                labelnames=self.get_labels_for_metric(
                    "litellm_remaining_requests_metric"
                ),
            )

            self.litellm_remaining_tokens_metric = self._gauge_factory(
                "litellm_remaining_tokens",
                "remaining tokens for model, returned from LLM API Provider",
                labelnames=self.get_labels_for_metric(
                    "litellm_remaining_tokens_metric"
                ),
            )

            self.litellm_overhead_latency_metric = self._histogram_factory(
                "litellm_overhead_latency_metric",
                "Latency overhead (milliseconds) added by LiteLLM processing",
                labelnames=self.get_labels_for_metric(
                    "litellm_overhead_latency_metric"
                ),
                buckets=LATENCY_BUCKETS,
            )
            # llm api provider budget metrics
            self.litellm_provider_remaining_budget_metric = self._gauge_factory(
                "litellm_provider_remaining_budget_metric",
                "Remaining budget for provider - used when you set provider budget limits",
                labelnames=["api_provider"],
            )

            # Get all keys
            _logged_llm_labels = [
                UserAPIKeyLabelNames.v2_LITELLM_MODEL_NAME.value,
                UserAPIKeyLabelNames.MODEL_ID.value,
                UserAPIKeyLabelNames.API_BASE.value,
                UserAPIKeyLabelNames.API_PROVIDER.value,
            ]

            # Metric for deployment state
            self.litellm_deployment_state = self._gauge_factory(
                "litellm_deployment_state",
                "LLM Deployment Analytics - The state of the deployment: 0 = healthy, 1 = partial outage, 2 = complete outage",
                labelnames=_logged_llm_labels,
            )

            self.litellm_deployment_cooled_down = self._counter_factory(
                "litellm_deployment_cooled_down",
                "LLM Deployment Analytics - Number of times a deployment has been cooled down by LiteLLM load balancing logic. exception_status is the status of the exception that caused the deployment to be cooled down",
                labelnames=_logged_llm_labels + [EXCEPTION_STATUS],
            )

            self.litellm_deployment_success_responses = self._counter_factory(
                name="litellm_deployment_success_responses",
                documentation="LLM Deployment Analytics - Total number of successful LLM API calls via litellm",
                labelnames=self.get_labels_for_metric(
                    "litellm_deployment_success_responses"
                ),
            )
            self.litellm_deployment_failure_responses = self._counter_factory(
                name="litellm_deployment_failure_responses",
                documentation="LLM Deployment Analytics - Total number of failed LLM API calls for a specific LLM deploymeny. exception_status is the status of the exception from the llm api",
                labelnames=self.get_labels_for_metric(
                    "litellm_deployment_failure_responses"
                ),
            )
            self.litellm_deployment_failure_by_tag_responses = self._counter_factory(
                "litellm_deployment_failure_by_tag_responses",
                "Total number of failed LLM API calls for a specific LLM deploymeny by custom metadata tags",
                labelnames=[
                    UserAPIKeyLabelNames.REQUESTED_MODEL.value,
                    UserAPIKeyLabelNames.TAG.value,
                ]
                + _logged_llm_labels
                + EXCEPTION_LABELS,
            )
            self.litellm_deployment_total_requests = self._counter_factory(
                name="litellm_deployment_total_requests",
                documentation="LLM Deployment Analytics - Total number of LLM API calls via litellm - success + failure",
                labelnames=self.get_labels_for_metric(
                    "litellm_deployment_total_requests"
                ),
            )

            # Deployment Latency tracking
            self.litellm_deployment_latency_per_output_token = self._histogram_factory(
                name="litellm_deployment_latency_per_output_token",
                documentation="LLM Deployment Analytics - Latency per output token",
                labelnames=self.get_labels_for_metric(
                    "litellm_deployment_latency_per_output_token"
                ),
            )

            self.litellm_deployment_successful_fallbacks = self._counter_factory(
                "litellm_deployment_successful_fallbacks",
                "LLM Deployment Analytics - Number of successful fallback requests from primary model -> fallback model",
                self.get_labels_for_metric("litellm_deployment_successful_fallbacks"),
            )

            self.litellm_deployment_failed_fallbacks = self._counter_factory(
                "litellm_deployment_failed_fallbacks",
                "LLM Deployment Analytics - Number of failed fallback requests from primary model -> fallback model",
                self.get_labels_for_metric("litellm_deployment_failed_fallbacks"),
            )

            self.litellm_llm_api_failed_requests_metric = self._counter_factory(
                name="litellm_llm_api_failed_requests_metric",
                documentation="deprecated - use litellm_proxy_failed_requests_metric",
                labelnames=[
                    "end_user",
                    "hashed_api_key",
                    "api_key_alias",
                    "model",
                    "team",
                    "team_alias",
                    "user",
                ],
            )

            self.litellm_requests_metric = self._counter_factory(
                name="litellm_requests_metric",
                documentation="deprecated - use litellm_proxy_total_requests_metric. Total number of LLM calls to litellm - track total per API Key, team, user",
                labelnames=self.get_labels_for_metric("litellm_requests_metric"),
            )
        except Exception as e:
            print_verbose(f"Got exception on init prometheus client {str(e)}")
            raise e

    def _parse_prometheus_config(self) -> Dict[str, List[str]]:
        """Parse prometheus metrics configuration for label filtering and enabled metrics"""
        import litellm
        from litellm.types.integrations.prometheus import PrometheusMetricsConfig

        config = litellm.prometheus_metrics_config

        # If no config is provided, return empty dict (no filtering)
        if not config:
            return {}

        verbose_logger.debug(f"prometheus config: {config}")

        label_filters = {}
        self.enabled_metrics = set()

        # Parse each configuration group
        for group_config in config:
            # Validate configuration using Pydantic
            if isinstance(group_config, dict):
                parsed_config = PrometheusMetricsConfig(**group_config)
            else:
                parsed_config = group_config

            # Add enabled metrics to the set
            self.enabled_metrics.update(parsed_config.metrics)

            # Set label filters for each metric in this group
            for metric_name in parsed_config.metrics:
                if parsed_config.include_labels:
                    label_filters[metric_name] = parsed_config.include_labels

        # Pretty print the processed configuration
        self._pretty_print_prometheus_config(label_filters)

        return label_filters

    def _pretty_print_prometheus_config(
        self, label_filters: Dict[str, List[str]]
    ) -> None:
        """Pretty print the processed prometheus configuration using rich"""
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text

            console = Console()

            # Create main panel title
            title = Text("Prometheus Configuration Processed", style="bold blue")

            # Create enabled metrics table
            metrics_table = Table(
                title="📊 Enabled Metrics",
                show_header=True,
                header_style="bold magenta",
                title_justify="left",
            )
            metrics_table.add_column("Metric Name", style="cyan", no_wrap=True)

            if hasattr(self, "enabled_metrics") and self.enabled_metrics:
                for metric in sorted(self.enabled_metrics):
                    metrics_table.add_row(metric)
            else:
                metrics_table.add_row(
                    "[yellow]All metrics enabled (no filter applied)[/yellow]"
                )

            # Create label filters table
            labels_table = Table(
                title="🏷️  Label Filters",
                show_header=True,
                header_style="bold green",
                title_justify="left",
            )
            labels_table.add_column("Metric Name", style="cyan", no_wrap=True)
            labels_table.add_column("Allowed Labels", style="yellow")

            if label_filters:
                for metric_name, labels in sorted(label_filters.items()):
                    labels_str = (
                        ", ".join(labels)
                        if labels
                        else "[dim]No labels specified[/dim]"
                    )
                    labels_table.add_row(metric_name, labels_str)
            else:
                labels_table.add_row(
                    "[yellow]No label filtering applied[/yellow]",
                    "[dim]All default labels will be used[/dim]",
                )

            # Print everything in a nice panel
            console.print("\n")
            console.print(Panel(title, border_style="blue"))
            console.print(metrics_table)
            console.print(labels_table)
            console.print("\n")

        except ImportError:
            # Fallback to simple logging if rich is not available
            verbose_logger.info(
                f"Enabled metrics: {sorted(self.enabled_metrics) if hasattr(self, 'enabled_metrics') else 'All metrics'}"
            )
            verbose_logger.info(f"Label filters: {label_filters}")

    def _is_metric_enabled(self, metric_name: str) -> bool:
        """Check if a metric is enabled based on configuration"""
        # If no specific configuration is provided, enable all metrics (default behavior)
        if not hasattr(self, "enabled_metrics"):
            return True

        # If enabled_metrics is empty, enable all metrics
        if not self.enabled_metrics:
            return True

        return metric_name in self.enabled_metrics

    def _create_metric_factory(self, metric_class):
        """Create a factory function that returns either a real metric or a no-op metric"""

        def factory(*args, **kwargs):
            # Extract metric name from the first argument or 'name' keyword argument
            metric_name = args[0] if args else kwargs.get("name", "")

            if self._is_metric_enabled(metric_name):
                return metric_class(*args, **kwargs)
            else:
                return NoOpMetric()

        return factory

    def get_labels_for_metric(
        self, metric_name: DEFINED_PROMETHEUS_METRICS
    ) -> List[str]:
        """
        Get the labels for a metric, filtered if configured
        """
        # Get default labels for this metric from PrometheusMetricLabels
        default_labels = PrometheusMetricLabels.get_labels(metric_name)

        # If no label filtering is configured for this metric, use default labels
        if metric_name not in self.label_filters:
            return default_labels

        # Get configured labels for this metric
        configured_labels = self.label_filters[metric_name]

        # Return intersection of configured and default labels to ensure we only use valid labels
        filtered_labels = [
            label for label in default_labels if label in configured_labels
        ]

        return filtered_labels

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        # Define prometheus client
        from litellm.types.utils import StandardLoggingPayload

        verbose_logger.debug(
            f"prometheus Logging - Enters success logging function for kwargs {kwargs}"
        )

        # unpack kwargs
        standard_logging_payload: Optional[StandardLoggingPayload] = kwargs.get(
            "standard_logging_object"
        )

        if standard_logging_payload is None or not isinstance(
            standard_logging_payload, dict
        ):
            raise ValueError(
                f"standard_logging_object is required, got={standard_logging_payload}"
            )

        model = kwargs.get("model", "")
        litellm_params = kwargs.get("litellm_params", {}) or {}
        _metadata = litellm_params.get("metadata", {})
        end_user_id = get_end_user_id_for_cost_tracking(
            litellm_params, service_type="prometheus"
        )
        user_id = standard_logging_payload["metadata"]["user_api_key_user_id"]
        user_api_key = standard_logging_payload["metadata"]["user_api_key_hash"]
        user_api_key_alias = standard_logging_payload["metadata"]["user_api_key_alias"]
        user_api_team = standard_logging_payload["metadata"]["user_api_key_team_id"]
        user_api_team_alias = standard_logging_payload["metadata"][
            "user_api_key_team_alias"
        ]
        output_tokens = standard_logging_payload["completion_tokens"]
        tokens_used = standard_logging_payload["total_tokens"]
        response_cost = standard_logging_payload["response_cost"]
        _requester_metadata = standard_logging_payload["metadata"].get(
            "requester_metadata"
        )
        if standard_logging_payload is not None and isinstance(
            standard_logging_payload, dict
        ):
            _tags = standard_logging_payload["request_tags"]
        else:
            _tags = []

        print_verbose(
            f"inside track_prometheus_metrics, model {model}, response_cost {response_cost}, tokens_used {tokens_used}, end_user_id {end_user_id}, user_api_key {user_api_key}"
        )

        enum_values = UserAPIKeyLabelValues(
            end_user=end_user_id,
            hashed_api_key=user_api_key,
            api_key_alias=user_api_key_alias,
            requested_model=standard_logging_payload["model_group"],
            model_group=standard_logging_payload["model_group"],
            team=user_api_team,
            team_alias=user_api_team_alias,
            user=user_id,
            user_email=standard_logging_payload["metadata"]["user_api_key_user_email"],
            status_code="200",
            model=model,
            litellm_model_name=model,
            tags=_tags,
            model_id=standard_logging_payload["model_id"],
            api_base=standard_logging_payload["api_base"],
            api_provider=standard_logging_payload["custom_llm_provider"],
            exception_status=None,
            exception_class=None,
            custom_metadata_labels=get_custom_labels_from_metadata(
                metadata=standard_logging_payload["metadata"].get("requester_metadata")
                or {}
            ),
            route=standard_logging_payload["metadata"].get(
                "user_api_key_request_route"
            ),
        )

        if (
            user_api_key is not None
            and isinstance(user_api_key, str)
            and user_api_key.startswith("sk-")
        ):
            from litellm.proxy.utils import hash_token

            user_api_key = hash_token(user_api_key)

        # increment total LLM requests and spend metric
        self._increment_top_level_request_and_spend_metrics(
            end_user_id=end_user_id,
            user_api_key=user_api_key,
            user_api_key_alias=user_api_key_alias,
            model=model,
            user_api_team=user_api_team,
            user_api_team_alias=user_api_team_alias,
            user_id=user_id,
            response_cost=response_cost,
            enum_values=enum_values,
        )

        # input, output, total token metrics
        self._increment_token_metrics(
            # why type ignore below?
            # 1. We just checked if isinstance(standard_logging_payload, dict). Pyright complains.
            # 2. Pyright does not allow us to run isinstance(standard_logging_payload, StandardLoggingPayload) <- this would be ideal
            standard_logging_payload=standard_logging_payload,  # type: ignore
            end_user_id=end_user_id,
            user_api_key=user_api_key,
            user_api_key_alias=user_api_key_alias,
            model=model,
            user_api_team=user_api_team,
            user_api_team_alias=user_api_team_alias,
            user_id=user_id,
            enum_values=enum_values,
        )

        # remaining budget metrics
        await self._increment_remaining_budget_metrics(
            user_api_team=user_api_team,
            user_api_team_alias=user_api_team_alias,
            user_api_key=user_api_key,
            user_api_key_alias=user_api_key_alias,
            litellm_params=litellm_params,
            response_cost=response_cost,
        )

        # set proxy virtual key rpm/tpm metrics
        self._set_virtual_key_rate_limit_metrics(
            user_api_key=user_api_key,
            user_api_key_alias=user_api_key_alias,
            kwargs=kwargs,
            metadata=_metadata,
        )

        # set latency metrics
        self._set_latency_metrics(
            kwargs=kwargs,
            model=model,
            user_api_key=user_api_key,
            user_api_key_alias=user_api_key_alias,
            user_api_team=user_api_team,
            user_api_team_alias=user_api_team_alias,
            # why type ignore below?
            # 1. We just checked if isinstance(standard_logging_payload, dict). Pyright complains.
            # 2. Pyright does not allow us to run isinstance(standard_logging_payload, StandardLoggingPayload) <- this would be ideal
            enum_values=enum_values,
        )

        # set x-ratelimit headers
        self.set_llm_deployment_success_metrics(
            kwargs, start_time, end_time, enum_values, output_tokens
        )

        if (
            standard_logging_payload["stream"] is True
        ):  # log successful streaming requests from logging event hook.
            _labels = prometheus_label_factory(
                supported_enum_labels=self.get_labels_for_metric(
                    metric_name="litellm_proxy_total_requests_metric"
                ),
                enum_values=enum_values,
            )
            self.litellm_proxy_total_requests_metric.labels(**_labels).inc()

    def _increment_token_metrics(
        self,
        standard_logging_payload: StandardLoggingPayload,
        end_user_id: Optional[str],
        user_api_key: Optional[str],
        user_api_key_alias: Optional[str],
        model: Optional[str],
        user_api_team: Optional[str],
        user_api_team_alias: Optional[str],
        user_id: Optional[str],
        enum_values: UserAPIKeyLabelValues,
    ):
        verbose_logger.debug("prometheus Logging - Enters token metrics function")
        # token metrics

        if standard_logging_payload is not None and isinstance(
            standard_logging_payload, dict
        ):
            _tags = standard_logging_payload["request_tags"]

        _labels = prometheus_label_factory(
            supported_enum_labels=self.get_labels_for_metric(
                metric_name="litellm_proxy_total_requests_metric"
            ),
            enum_values=enum_values,
        )

        _labels = prometheus_label_factory(
            supported_enum_labels=self.get_labels_for_metric(
                metric_name="litellm_total_tokens_metric"
            ),
            enum_values=enum_values,
        )
        self.litellm_tokens_metric.labels(**_labels).inc(
            standard_logging_payload["total_tokens"]
        )

        _labels = prometheus_label_factory(
            supported_enum_labels=self.get_labels_for_metric(
                metric_name="litellm_input_tokens_metric"
            ),
            enum_values=enum_values,
        )
        self.litellm_input_tokens_metric.labels(**_labels).inc(
            standard_logging_payload["prompt_tokens"]
        )

        _labels = prometheus_label_factory(
            supported_enum_labels=self.get_labels_for_metric(
                metric_name="litellm_output_tokens_metric"
            ),
            enum_values=enum_values,
        )

        self.litellm_output_tokens_metric.labels(**_labels).inc(
            standard_logging_payload["completion_tokens"]
        )

    async def _increment_remaining_budget_metrics(
        self,
        user_api_team: Optional[str],
        user_api_team_alias: Optional[str],
        user_api_key: Optional[str],
        user_api_key_alias: Optional[str],
        litellm_params: dict,
        response_cost: float,
    ):
        _team_spend = litellm_params.get("metadata", {}).get(
            "user_api_key_team_spend", None
        )
        _team_max_budget = litellm_params.get("metadata", {}).get(
            "user_api_key_team_max_budget", None
        )

        _api_key_spend = litellm_params.get("metadata", {}).get(
            "user_api_key_spend", None
        )
        _api_key_max_budget = litellm_params.get("metadata", {}).get(
            "user_api_key_max_budget", None
        )
        await self._set_api_key_budget_metrics_after_api_request(
            user_api_key=user_api_key,
            user_api_key_alias=user_api_key_alias,
            response_cost=response_cost,
            key_max_budget=_api_key_max_budget,
            key_spend=_api_key_spend,
        )

        await self._set_team_budget_metrics_after_api_request(
            user_api_team=user_api_team,
            user_api_team_alias=user_api_team_alias,
            team_spend=_team_spend,
            team_max_budget=_team_max_budget,
            response_cost=response_cost,
        )

    def _increment_top_level_request_and_spend_metrics(
        self,
        end_user_id: Optional[str],
        user_api_key: Optional[str],
        user_api_key_alias: Optional[str],
        model: Optional[str],
        user_api_team: Optional[str],
        user_api_team_alias: Optional[str],
        user_id: Optional[str],
        response_cost: float,
        enum_values: UserAPIKeyLabelValues,
    ):
        _labels = prometheus_label_factory(
            supported_enum_labels=self.get_labels_for_metric(
                metric_name="litellm_requests_metric"
            ),
            enum_values=enum_values,
        )

        self.litellm_requests_metric.labels(**_labels).inc()

        _labels = prometheus_label_factory(
            supported_enum_labels=self.get_labels_for_metric(
                metric_name="litellm_proxy_total_requests_metric"
            ),
            enum_values=enum_values,
        )

        self.litellm_spend_metric.labels(
            end_user_id,
            user_api_key,
            user_api_key_alias,
            model,
            user_api_team,
            user_api_team_alias,
            user_id,
        ).inc(response_cost)

    def _set_virtual_key_rate_limit_metrics(
        self,
        user_api_key: Optional[str],
        user_api_key_alias: Optional[str],
        kwargs: dict,
        metadata: dict,
    ):
        from litellm.proxy.common_utils.callback_utils import (
            get_model_group_from_litellm_kwargs,
        )

        # Set remaining rpm/tpm for API Key + model
        # see parallel_request_limiter.py - variables are set there
        model_group = get_model_group_from_litellm_kwargs(kwargs)
        remaining_requests_variable_name = (
            f"litellm-key-remaining-requests-{model_group}"
        )
        remaining_tokens_variable_name = f"litellm-key-remaining-tokens-{model_group}"

        remaining_requests = (
            metadata.get(remaining_requests_variable_name, sys.maxsize) or sys.maxsize
        )
        remaining_tokens = (
            metadata.get(remaining_tokens_variable_name, sys.maxsize) or sys.maxsize
        )

        self.litellm_remaining_api_key_requests_for_model.labels(
            user_api_key, user_api_key_alias, model_group
        ).set(remaining_requests)

        self.litellm_remaining_api_key_tokens_for_model.labels(
            user_api_key, user_api_key_alias, model_group
        ).set(remaining_tokens)

    def _set_latency_metrics(
        self,
        kwargs: dict,
        model: Optional[str],
        user_api_key: Optional[str],
        user_api_key_alias: Optional[str],
        user_api_team: Optional[str],
        user_api_team_alias: Optional[str],
        enum_values: UserAPIKeyLabelValues,
    ):
        # latency metrics
        end_time: datetime = kwargs.get("end_time") or datetime.now()
        start_time: Optional[datetime] = kwargs.get("start_time")
        api_call_start_time = kwargs.get("api_call_start_time", None)
        completion_start_time = kwargs.get("completion_start_time", None)
        time_to_first_token_seconds = self._safe_duration_seconds(
            start_time=api_call_start_time,
            end_time=completion_start_time,
        )
        if (
            time_to_first_token_seconds is not None
            and kwargs.get("stream", False) is True  # only emit for streaming requests
        ):
            self.litellm_llm_api_time_to_first_token_metric.labels(
                model,
                user_api_key,
                user_api_key_alias,
                user_api_team,
                user_api_team_alias,
            ).observe(time_to_first_token_seconds)
        else:
            verbose_logger.debug(
                "Time to first token metric not emitted, stream option in model_parameters is not True"
            )

        api_call_total_time_seconds = self._safe_duration_seconds(
            start_time=api_call_start_time,
            end_time=end_time,
        )
        if api_call_total_time_seconds is not None:
            _labels = prometheus_label_factory(
                supported_enum_labels=self.get_labels_for_metric(
                    metric_name="litellm_llm_api_latency_metric"
                ),
                enum_values=enum_values,
            )
            self.litellm_llm_api_latency_metric.labels(**_labels).observe(
                api_call_total_time_seconds
            )

        # total request latency
        total_time_seconds = self._safe_duration_seconds(
            start_time=start_time,
            end_time=end_time,
        )
        if total_time_seconds is not None:
            _labels = prometheus_label_factory(
                supported_enum_labels=self.get_labels_for_metric(
                    metric_name="litellm_request_total_latency_metric"
                ),
                enum_values=enum_values,
            )
            self.litellm_request_total_latency_metric.labels(**_labels).observe(
                total_time_seconds
            )

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        from litellm.types.utils import StandardLoggingPayload

        verbose_logger.debug(
            f"prometheus Logging - Enters failure logging function for kwargs {kwargs}"
        )

        # unpack kwargs
        model = kwargs.get("model", "")
        standard_logging_payload: StandardLoggingPayload = kwargs.get(
            "standard_logging_object", {}
        )
        litellm_params = kwargs.get("litellm_params", {}) or {}
        end_user_id = get_end_user_id_for_cost_tracking(
            litellm_params, service_type="prometheus"
        )
        user_id = standard_logging_payload["metadata"]["user_api_key_user_id"]
        user_api_key = standard_logging_payload["metadata"]["user_api_key_hash"]
        user_api_key_alias = standard_logging_payload["metadata"]["user_api_key_alias"]
        user_api_team = standard_logging_payload["metadata"]["user_api_key_team_id"]
        user_api_team_alias = standard_logging_payload["metadata"][
            "user_api_key_team_alias"
        ]
        kwargs.get("exception", None)

        try:
            self.litellm_llm_api_failed_requests_metric.labels(
                end_user_id,
                user_api_key,
                user_api_key_alias,
                model,
                user_api_team,
                user_api_team_alias,
                user_id,
            ).inc()
            self.set_llm_deployment_failure_metrics(kwargs)
        except Exception as e:
            verbose_logger.exception(
                "prometheus Layer Error(): Exception occured - {}".format(str(e))
            )
            pass
        pass

    async def async_post_call_failure_hook(
        self,
        request_data: dict,
        original_exception: Exception,
        user_api_key_dict: UserAPIKeyAuth,
        traceback_str: Optional[str] = None,
    ):
        """
        Track client side failures

        Proxy level tracking - failed client side requests

        labelnames=[
                    "end_user",
                    "hashed_api_key",
                    "api_key_alias",
                    REQUESTED_MODEL,
                    "team",
                    "team_alias",
                ] + EXCEPTION_LABELS,
        """
        try:
            _tags = cast(List[str], request_data.get("tags") or [])
            enum_values = UserAPIKeyLabelValues(
                end_user=user_api_key_dict.end_user_id,
                user=user_api_key_dict.user_id,
                user_email=user_api_key_dict.user_email,
                hashed_api_key=user_api_key_dict.api_key,
                api_key_alias=user_api_key_dict.key_alias,
                team=user_api_key_dict.team_id,
                team_alias=user_api_key_dict.team_alias,
                requested_model=request_data.get("model", ""),
                status_code=str(getattr(original_exception, "status_code", None)),
                exception_status=str(getattr(original_exception, "status_code", None)),
                exception_class=self._get_exception_class_name(original_exception),
                tags=_tags,
                route=user_api_key_dict.request_route,
            )
            _labels = prometheus_label_factory(
                supported_enum_labels=self.get_labels_for_metric(
                    metric_name="litellm_proxy_failed_requests_metric"
                ),
                enum_values=enum_values,
            )
            self.litellm_proxy_failed_requests_metric.labels(**_labels).inc()

            _labels = prometheus_label_factory(
                supported_enum_labels=self.get_labels_for_metric(
                    metric_name="litellm_proxy_total_requests_metric"
                ),
                enum_values=enum_values,
            )
            self.litellm_proxy_total_requests_metric.labels(**_labels).inc()

        except Exception as e:
            verbose_logger.exception(
                "prometheus Layer Error(): Exception occured - {}".format(str(e))
            )
            pass

    async def async_post_call_success_hook(
        self, data: dict, user_api_key_dict: UserAPIKeyAuth, response
    ):
        """
        Proxy level tracking - triggered when the proxy responds with a success response to the client
        """
        try:
            enum_values = UserAPIKeyLabelValues(
                end_user=user_api_key_dict.end_user_id,
                hashed_api_key=user_api_key_dict.api_key,
                api_key_alias=user_api_key_dict.key_alias,
                requested_model=data.get("model", ""),
                team=user_api_key_dict.team_id,
                team_alias=user_api_key_dict.team_alias,
                user=user_api_key_dict.user_id,
                user_email=user_api_key_dict.user_email,
                status_code="200",
                route=user_api_key_dict.request_route,
            )
            _labels = prometheus_label_factory(
                supported_enum_labels=self.get_labels_for_metric(
                    metric_name="litellm_proxy_total_requests_metric"
                ),
                enum_values=enum_values,
            )
            self.litellm_proxy_total_requests_metric.labels(**_labels).inc()

        except Exception as e:
            verbose_logger.exception(
                "prometheus Layer Error(): Exception occured - {}".format(str(e))
            )
            pass

    def set_llm_deployment_failure_metrics(self, request_kwargs: dict):
        """
        Sets Failure metrics when an LLM API call fails

        - mark the deployment as partial outage
        - increment deployment failure responses metric
        - increment deployment total requests metric

        Args:
            request_kwargs: dict

        """
        try:
            verbose_logger.debug("setting remaining tokens requests metric")
            standard_logging_payload: StandardLoggingPayload = request_kwargs.get(
                "standard_logging_object", {}
            )
            _litellm_params = request_kwargs.get("litellm_params", {}) or {}
            litellm_model_name = request_kwargs.get("model", None)
            model_group = standard_logging_payload.get("model_group", None)
            api_base = standard_logging_payload.get("api_base", None)
            model_id = standard_logging_payload.get("model_id", None)
            exception = request_kwargs.get("exception", None)

            llm_provider = _litellm_params.get("custom_llm_provider", None)

            # Create enum_values for the label factory (always create for use in different metrics)
            enum_values = UserAPIKeyLabelValues(
                litellm_model_name=litellm_model_name,
                model_id=model_id,
                api_base=api_base,
                api_provider=llm_provider,
                exception_status=(
                    str(getattr(exception, "status_code", None)) if exception else None
                ),
                exception_class=(
                    self._get_exception_class_name(exception) if exception else None
                ),
                requested_model=model_group,
                hashed_api_key=standard_logging_payload["metadata"][
                    "user_api_key_hash"
                ],
                api_key_alias=standard_logging_payload["metadata"][
                    "user_api_key_alias"
                ],
                team=standard_logging_payload["metadata"]["user_api_key_team_id"],
                team_alias=standard_logging_payload["metadata"][
                    "user_api_key_team_alias"
                ],
            )

            """
            log these labels
            ["litellm_model_name", "model_id", "api_base", "api_provider"]
            """
            self.set_deployment_partial_outage(
                litellm_model_name=litellm_model_name or "",
                model_id=model_id,
                api_base=api_base,
                api_provider=llm_provider or "",
            )
            if exception is not None:

                _labels = prometheus_label_factory(
                    supported_enum_labels=self.get_labels_for_metric(
                        metric_name="litellm_deployment_failure_responses"
                    ),
                    enum_values=enum_values,
                )
                self.litellm_deployment_failure_responses.labels(**_labels).inc()

                # tag based tracking
                if standard_logging_payload is not None and isinstance(
                    standard_logging_payload, dict
                ):
                    _tags = standard_logging_payload["request_tags"]
                    for tag in _tags:
                        self.litellm_deployment_failure_by_tag_responses.labels(
                            **{
                                UserAPIKeyLabelNames.REQUESTED_MODEL.value: model_group,
                                UserAPIKeyLabelNames.TAG.value: tag,
                                UserAPIKeyLabelNames.v2_LITELLM_MODEL_NAME.value: litellm_model_name,
                                UserAPIKeyLabelNames.MODEL_ID.value: model_id,
                                UserAPIKeyLabelNames.API_BASE.value: api_base,
                                UserAPIKeyLabelNames.API_PROVIDER.value: llm_provider,
                                UserAPIKeyLabelNames.EXCEPTION_CLASS.value: exception.__class__.__name__,
                                UserAPIKeyLabelNames.EXCEPTION_STATUS.value: str(
                                    getattr(exception, "status_code", None)
                                ),
                            }
                        ).inc()

            _labels = prometheus_label_factory(
                supported_enum_labels=self.get_labels_for_metric(
                    metric_name="litellm_deployment_total_requests"
                ),
                enum_values=enum_values,
            )
            self.litellm_deployment_total_requests.labels(**_labels).inc()

            pass
        except Exception as e:
            verbose_logger.debug(
                "Prometheus Error: set_llm_deployment_failure_metrics. Exception occured - {}".format(
                    str(e)
                )
            )

    def set_llm_deployment_success_metrics(
        self,
        request_kwargs: dict,
        start_time,
        end_time,
        enum_values: UserAPIKeyLabelValues,
        output_tokens: float = 1.0,
    ):

        try:
            verbose_logger.debug("setting remaining tokens requests metric")
            standard_logging_payload: Optional[StandardLoggingPayload] = (
                request_kwargs.get("standard_logging_object")
            )

            if standard_logging_payload is None:
                return

            api_base = standard_logging_payload["api_base"]
            _litellm_params = request_kwargs.get("litellm_params", {}) or {}
            _metadata = _litellm_params.get("metadata", {})
            litellm_model_name = request_kwargs.get("model", None)
            llm_provider = _litellm_params.get("custom_llm_provider", None)
            _model_info = _metadata.get("model_info") or {}
            model_id = _model_info.get("id", None)

            remaining_requests: Optional[int] = None
            remaining_tokens: Optional[int] = None
            if additional_headers := standard_logging_payload["hidden_params"][
                "additional_headers"
            ]:
                # OpenAI / OpenAI Compatible headers
                remaining_requests = additional_headers.get(
                    "x_ratelimit_remaining_requests", None
                )
                remaining_tokens = additional_headers.get(
                    "x_ratelimit_remaining_tokens", None
                )

            if litellm_overhead_time_ms := standard_logging_payload[
                "hidden_params"
            ].get("litellm_overhead_time_ms"):
                _labels = prometheus_label_factory(
                    supported_enum_labels=self.get_labels_for_metric(
                        metric_name="litellm_overhead_latency_metric"
                    ),
                    enum_values=enum_values,
                )
                self.litellm_overhead_latency_metric.labels(**_labels).observe(
                    litellm_overhead_time_ms / 1000
                )  # set as seconds

            if remaining_requests:
                """
                "model_group",
                "api_provider",
                "api_base",
                "litellm_model_name"
                """
                _labels = prometheus_label_factory(
                    supported_enum_labels=self.get_labels_for_metric(
                        metric_name="litellm_remaining_requests_metric"
                    ),
                    enum_values=enum_values,
                )
                self.litellm_remaining_requests_metric.labels(**_labels).set(
                    remaining_requests
                )

            if remaining_tokens:
                _labels = prometheus_label_factory(
                    supported_enum_labels=self.get_labels_for_metric(
                        metric_name="litellm_remaining_tokens_metric"
                    ),
                    enum_values=enum_values,
                )
                self.litellm_remaining_tokens_metric.labels(**_labels).set(
                    remaining_tokens
                )

            """
            log these labels
            ["litellm_model_name", "requested_model", model_id", "api_base", "api_provider"]
            """
            self.set_deployment_healthy(
                litellm_model_name=litellm_model_name or "",
                model_id=model_id or "",
                api_base=api_base or "",
                api_provider=llm_provider or "",
            )

            _labels = prometheus_label_factory(
                supported_enum_labels=self.get_labels_for_metric(
                    metric_name="litellm_deployment_success_responses"
                ),
                enum_values=enum_values,
            )
            self.litellm_deployment_success_responses.labels(**_labels).inc()

            _labels = prometheus_label_factory(
                supported_enum_labels=self.get_labels_for_metric(
                    metric_name="litellm_deployment_total_requests"
                ),
                enum_values=enum_values,
            )
            self.litellm_deployment_total_requests.labels(**_labels).inc()

            # Track deployment Latency
            response_ms: timedelta = end_time - start_time
            time_to_first_token_response_time: Optional[timedelta] = None

            if (
                request_kwargs.get("stream", None) is not None
                and request_kwargs["stream"] is True
            ):
                # only log ttft for streaming request
                time_to_first_token_response_time = (
                    request_kwargs.get("completion_start_time", end_time) - start_time
                )

            # use the metric that is not None
            # if streaming - use time_to_first_token_response
            # if not streaming - use response_ms
            _latency: timedelta = time_to_first_token_response_time or response_ms
            _latency_seconds = _latency.total_seconds()

            # latency per output token
            latency_per_token = None
            if output_tokens is not None and output_tokens > 0:
                latency_per_token = _latency_seconds / output_tokens
                _labels = prometheus_label_factory(
                    supported_enum_labels=self.get_labels_for_metric(
                        metric_name="litellm_deployment_latency_per_output_token"
                    ),
                    enum_values=enum_values,
                )
                self.litellm_deployment_latency_per_output_token.labels(
                    **_labels
                ).observe(latency_per_token)

        except Exception as e:
            verbose_logger.exception(
                "Prometheus Error: set_llm_deployment_success_metrics. Exception occured - {}".format(
                    str(e)
                )
            )
            return

    @staticmethod
    def _get_exception_class_name(exception: Exception) -> str:
        exception_class_name = ""
        if hasattr(exception, "llm_provider"):
            exception_class_name = getattr(exception, "llm_provider") or ""

        # pretty print the provider name on prometheus
        # eg. `openai` -> `Openai.`
        if len(exception_class_name) >= 1:
            exception_class_name = (
                exception_class_name[0].upper() + exception_class_name[1:] + "."
            )

        exception_class_name += exception.__class__.__name__
        return exception_class_name

    async def log_success_fallback_event(
        self, original_model_group: str, kwargs: dict, original_exception: Exception
    ):
        """

        Logs a successful LLM fallback event on prometheus

        """
        from litellm.litellm_core_utils.litellm_logging import (
            StandardLoggingMetadata,
            StandardLoggingPayloadSetup,
        )

        verbose_logger.debug(
            "Prometheus: log_success_fallback_event, original_model_group: %s, kwargs: %s",
            original_model_group,
            kwargs,
        )
        _metadata = kwargs.get("metadata", {})
        standard_metadata: StandardLoggingMetadata = (
            StandardLoggingPayloadSetup.get_standard_logging_metadata(
                metadata=_metadata
            )
        )
        _new_model = kwargs.get("model")
        _tags = cast(List[str], kwargs.get("tags") or [])

        enum_values = UserAPIKeyLabelValues(
            requested_model=original_model_group,
            fallback_model=_new_model,
            hashed_api_key=standard_metadata["user_api_key_hash"],
            api_key_alias=standard_metadata["user_api_key_alias"],
            team=standard_metadata["user_api_key_team_id"],
            team_alias=standard_metadata["user_api_key_team_alias"],
            exception_status=str(getattr(original_exception, "status_code", None)),
            exception_class=self._get_exception_class_name(original_exception),
            tags=_tags,
        )
        _labels = prometheus_label_factory(
            supported_enum_labels=self.get_labels_for_metric(
                metric_name="litellm_deployment_successful_fallbacks"
            ),
            enum_values=enum_values,
        )
        self.litellm_deployment_successful_fallbacks.labels(**_labels).inc()

    async def log_failure_fallback_event(
        self, original_model_group: str, kwargs: dict, original_exception: Exception
    ):
        """
        Logs a failed LLM fallback event on prometheus
        """
        from litellm.litellm_core_utils.litellm_logging import (
            StandardLoggingMetadata,
            StandardLoggingPayloadSetup,
        )

        verbose_logger.debug(
            "Prometheus: log_failure_fallback_event, original_model_group: %s, kwargs: %s",
            original_model_group,
            kwargs,
        )
        _new_model = kwargs.get("model")
        _metadata = kwargs.get("metadata", {})
        _tags = cast(List[str], kwargs.get("tags") or [])
        standard_metadata: StandardLoggingMetadata = (
            StandardLoggingPayloadSetup.get_standard_logging_metadata(
                metadata=_metadata
            )
        )

        enum_values = UserAPIKeyLabelValues(
            requested_model=original_model_group,
            fallback_model=_new_model,
            hashed_api_key=standard_metadata["user_api_key_hash"],
            api_key_alias=standard_metadata["user_api_key_alias"],
            team=standard_metadata["user_api_key_team_id"],
            team_alias=standard_metadata["user_api_key_team_alias"],
            exception_status=str(getattr(original_exception, "status_code", None)),
            exception_class=self._get_exception_class_name(original_exception),
            tags=_tags,
        )

        _labels = prometheus_label_factory(
            supported_enum_labels=self.get_labels_for_metric(
                metric_name="litellm_deployment_failed_fallbacks"
            ),
            enum_values=enum_values,
        )
        self.litellm_deployment_failed_fallbacks.labels(**_labels).inc()

    def set_litellm_deployment_state(
        self,
        state: int,
        litellm_model_name: str,
        model_id: Optional[str],
        api_base: Optional[str],
        api_provider: str,
    ):
        self.litellm_deployment_state.labels(
            litellm_model_name, model_id, api_base, api_provider
        ).set(state)

    def set_deployment_healthy(
        self,
        litellm_model_name: str,
        model_id: str,
        api_base: str,
        api_provider: str,
    ):
        self.set_litellm_deployment_state(
            0, litellm_model_name, model_id, api_base, api_provider
        )

    def set_deployment_partial_outage(
        self,
        litellm_model_name: str,
        model_id: Optional[str],
        api_base: Optional[str],
        api_provider: str,
    ):
        self.set_litellm_deployment_state(
            1, litellm_model_name, model_id, api_base, api_provider
        )

    def set_deployment_complete_outage(
        self,
        litellm_model_name: str,
        model_id: Optional[str],
        api_base: Optional[str],
        api_provider: str,
    ):
        self.set_litellm_deployment_state(
            2, litellm_model_name, model_id, api_base, api_provider
        )

    def increment_deployment_cooled_down(
        self,
        litellm_model_name: str,
        model_id: str,
        api_base: str,
        api_provider: str,
        exception_status: str,
    ):
        """
        increment metric when litellm.Router / load balancing logic places a deployment in cool down
        """
        self.litellm_deployment_cooled_down.labels(
            litellm_model_name, model_id, api_base, api_provider, exception_status
        ).inc()

    def track_provider_remaining_budget(
        self, provider: str, spend: float, budget_limit: float
    ):
        """
        Track provider remaining budget in Prometheus
        """
        self.litellm_provider_remaining_budget_metric.labels(provider).set(
            self._safe_get_remaining_budget(
                max_budget=budget_limit,
                spend=spend,
            )
        )

    def _safe_get_remaining_budget(
        self, max_budget: Optional[float], spend: Optional[float]
    ) -> float:
        if max_budget is None:
            return float("inf")

        if spend is None:
            return max_budget

        return max_budget - spend

    async def _initialize_budget_metrics(
        self,
        data_fetch_function: Callable[..., Awaitable[Tuple[List[Any], Optional[int]]]],
        set_metrics_function: Callable[[List[Any]], Awaitable[None]],
        data_type: Literal["teams", "keys"],
    ):
        """
        Generic method to initialize budget metrics for teams or API keys.

        Args:
            data_fetch_function: Function to fetch data with pagination.
            set_metrics_function: Function to set metrics for the fetched data.
            data_type: String representing the type of data ("teams" or "keys") for logging purposes.
        """
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            return

        try:
            page = 1
            page_size = 50
            data, total_count = await data_fetch_function(
                page_size=page_size, page=page
            )

            if total_count is None:
                total_count = len(data)

            # Calculate total pages needed
            total_pages = (total_count + page_size - 1) // page_size

            # Set metrics for first page of data
            await set_metrics_function(data)

            # Get and set metrics for remaining pages
            for page in range(2, total_pages + 1):
                data, _ = await data_fetch_function(page_size=page_size, page=page)
                await set_metrics_function(data)

        except Exception as e:
            verbose_logger.exception(
                f"Error initializing {data_type} budget metrics: {str(e)}"
            )

    async def _initialize_team_budget_metrics(self):
        """
        Initialize team budget metrics by reusing the generic pagination logic.
        """
        from litellm.proxy.management_endpoints.team_endpoints import (
            get_paginated_teams,
        )
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            verbose_logger.debug(
                "Prometheus: skipping team metrics initialization, DB not initialized"
            )
            return

        async def fetch_teams(
            page_size: int, page: int
        ) -> Tuple[List[LiteLLM_TeamTable], Optional[int]]:
            teams, total_count = await get_paginated_teams(
                prisma_client=prisma_client, page_size=page_size, page=page
            )
            if total_count is None:
                total_count = len(teams)
            return teams, total_count

        await self._initialize_budget_metrics(
            data_fetch_function=fetch_teams,
            set_metrics_function=self._set_team_list_budget_metrics,
            data_type="teams",
        )

    async def _initialize_api_key_budget_metrics(self):
        """
        Initialize API key budget metrics by reusing the generic pagination logic.
        """
        from typing import Union

        from litellm.constants import UI_SESSION_TOKEN_TEAM_ID
        from litellm.proxy.management_endpoints.key_management_endpoints import (
            _list_key_helper,
        )
        from litellm.proxy.proxy_server import prisma_client

        if prisma_client is None:
            verbose_logger.debug(
                "Prometheus: skipping key metrics initialization, DB not initialized"
            )
            return

        async def fetch_keys(
            page_size: int, page: int
        ) -> Tuple[List[Union[str, UserAPIKeyAuth]], Optional[int]]:
            key_list_response = await _list_key_helper(
                prisma_client=prisma_client,
                page=page,
                size=page_size,
                user_id=None,
                team_id=None,
                key_alias=None,
                key_hash=None,
                exclude_team_id=UI_SESSION_TOKEN_TEAM_ID,
                return_full_object=True,
                organization_id=None,
            )
            keys = key_list_response.get("keys", [])
            total_count = key_list_response.get("total_count")
            if total_count is None:
                total_count = len(keys)
            return keys, total_count

        await self._initialize_budget_metrics(
            data_fetch_function=fetch_keys,
            set_metrics_function=self._set_key_list_budget_metrics,
            data_type="keys",
        )

    async def initialize_remaining_budget_metrics(self):
        """
        Handler for initializing remaining budget metrics for all teams to avoid metric discrepancies.

        Runs when prometheus logger starts up.

        - If redis cache is available, we use the pod lock manager to acquire a lock and initialize the metrics.
            - Ensures only one pod emits the metrics at a time.
        - If redis cache is not available, we initialize the metrics directly.
        """
        from litellm.constants import PROMETHEUS_EMIT_BUDGET_METRICS_JOB_NAME
        from litellm.proxy.proxy_server import proxy_logging_obj

        pod_lock_manager = proxy_logging_obj.db_spend_update_writer.pod_lock_manager

        # if using redis, ensure only one pod emits the metrics at a time
        if pod_lock_manager and pod_lock_manager.redis_cache:
            if await pod_lock_manager.acquire_lock(
                cronjob_id=PROMETHEUS_EMIT_BUDGET_METRICS_JOB_NAME
            ):
                try:
                    await self._initialize_remaining_budget_metrics()
                finally:
                    await pod_lock_manager.release_lock(
                        cronjob_id=PROMETHEUS_EMIT_BUDGET_METRICS_JOB_NAME
                    )
        else:
            # if not using redis, initialize the metrics directly
            await self._initialize_remaining_budget_metrics()

    async def _initialize_remaining_budget_metrics(self):
        """
        Helper to initialize remaining budget metrics for all teams and API keys.
        """
        verbose_logger.debug("Emitting key, team budget metrics....")
        await self._initialize_team_budget_metrics()
        await self._initialize_api_key_budget_metrics()

    async def _set_key_list_budget_metrics(
        self, keys: List[Union[str, UserAPIKeyAuth]]
    ):
        """Helper function to set budget metrics for a list of keys"""
        for key in keys:
            if isinstance(key, UserAPIKeyAuth):
                self._set_key_budget_metrics(key)

    async def _set_team_list_budget_metrics(self, teams: List[LiteLLM_TeamTable]):
        """Helper function to set budget metrics for a list of teams"""
        for team in teams:
            self._set_team_budget_metrics(team)

    async def _set_team_budget_metrics_after_api_request(
        self,
        user_api_team: Optional[str],
        user_api_team_alias: Optional[str],
        team_spend: float,
        team_max_budget: float,
        response_cost: float,
    ):
        """
        Set team budget metrics after an LLM API request

        - Assemble a LiteLLM_TeamTable object
            - looks up team info from db if not available in metadata
        - Set team budget metrics
        """
        if user_api_team:
            team_object = await self._assemble_team_object(
                team_id=user_api_team,
                team_alias=user_api_team_alias or "",
                spend=team_spend,
                max_budget=team_max_budget,
                response_cost=response_cost,
            )

            self._set_team_budget_metrics(team_object)

    async def _assemble_team_object(
        self,
        team_id: str,
        team_alias: str,
        spend: Optional[float],
        max_budget: Optional[float],
        response_cost: float,
    ) -> LiteLLM_TeamTable:
        """
        Assemble a LiteLLM_TeamTable object

        for fields not available in metadata, we fetch from db
        Fields not available in metadata:
        - `budget_reset_at`
        """
        from litellm.proxy.auth.auth_checks import get_team_object
        from litellm.proxy.proxy_server import prisma_client, user_api_key_cache

        _total_team_spend = (spend or 0) + response_cost
        team_object = LiteLLM_TeamTable(
            team_id=team_id,
            team_alias=team_alias,
            spend=_total_team_spend,
            max_budget=max_budget,
        )
        try:
            team_info = await get_team_object(
                team_id=team_id,
                prisma_client=prisma_client,
                user_api_key_cache=user_api_key_cache,
            )
        except Exception as e:
            verbose_logger.debug(
                f"[Non-Blocking] Prometheus: Error getting team info: {str(e)}"
            )
            return team_object

        if team_info:
            team_object.budget_reset_at = team_info.budget_reset_at

        return team_object

    def _set_team_budget_metrics(
        self,
        team: LiteLLM_TeamTable,
    ):
        """
        Set team budget metrics for a single team

        - Remaining Budget
        - Max Budget
        - Budget Reset At
        """
        enum_values = UserAPIKeyLabelValues(
            team=team.team_id,
            team_alias=team.team_alias or "",
        )

        _labels = prometheus_label_factory(
            supported_enum_labels=self.get_labels_for_metric(
                metric_name="litellm_remaining_team_budget_metric"
            ),
            enum_values=enum_values,
        )
        self.litellm_remaining_team_budget_metric.labels(**_labels).set(
            self._safe_get_remaining_budget(
                max_budget=team.max_budget,
                spend=team.spend,
            )
        )

        if team.max_budget is not None:
            _labels = prometheus_label_factory(
                supported_enum_labels=self.get_labels_for_metric(
                    metric_name="litellm_team_max_budget_metric"
                ),
                enum_values=enum_values,
            )
            self.litellm_team_max_budget_metric.labels(**_labels).set(team.max_budget)

        if team.budget_reset_at is not None:
            _labels = prometheus_label_factory(
                supported_enum_labels=self.get_labels_for_metric(
                    metric_name="litellm_team_budget_remaining_hours_metric"
                ),
                enum_values=enum_values,
            )
            self.litellm_team_budget_remaining_hours_metric.labels(**_labels).set(
                self._get_remaining_hours_for_budget_reset(
                    budget_reset_at=team.budget_reset_at
                )
            )

    def _set_key_budget_metrics(self, user_api_key_dict: UserAPIKeyAuth):
        """
        Set virtual key budget metrics

        - Remaining Budget
        - Max Budget
        - Budget Reset At
        """
        enum_values = UserAPIKeyLabelValues(
            hashed_api_key=user_api_key_dict.token,
            api_key_alias=user_api_key_dict.key_alias or "",
        )
        _labels = prometheus_label_factory(
            supported_enum_labels=self.get_labels_for_metric(
                metric_name="litellm_remaining_api_key_budget_metric"
            ),
            enum_values=enum_values,
        )
        self.litellm_remaining_api_key_budget_metric.labels(**_labels).set(
            self._safe_get_remaining_budget(
                max_budget=user_api_key_dict.max_budget,
                spend=user_api_key_dict.spend,
            )
        )

        if user_api_key_dict.max_budget is not None:
            _labels = prometheus_label_factory(
                supported_enum_labels=self.get_labels_for_metric(
                    metric_name="litellm_api_key_max_budget_metric"
                ),
                enum_values=enum_values,
            )
            self.litellm_api_key_max_budget_metric.labels(**_labels).set(
                user_api_key_dict.max_budget
            )

        if user_api_key_dict.budget_reset_at is not None:
            self.litellm_api_key_budget_remaining_hours_metric.labels(**_labels).set(
                self._get_remaining_hours_for_budget_reset(
                    budget_reset_at=user_api_key_dict.budget_reset_at
                )
            )

    async def _set_api_key_budget_metrics_after_api_request(
        self,
        user_api_key: Optional[str],
        user_api_key_alias: Optional[str],
        response_cost: float,
        key_max_budget: float,
        key_spend: Optional[float],
    ):
        if user_api_key:
            user_api_key_dict = await self._assemble_key_object(
                user_api_key=user_api_key,
                user_api_key_alias=user_api_key_alias or "",
                key_max_budget=key_max_budget,
                key_spend=key_spend,
                response_cost=response_cost,
            )
            self._set_key_budget_metrics(user_api_key_dict)

    async def _assemble_key_object(
        self,
        user_api_key: str,
        user_api_key_alias: str,
        key_max_budget: float,
        key_spend: Optional[float],
        response_cost: float,
    ) -> UserAPIKeyAuth:
        """
        Assemble a UserAPIKeyAuth object
        """
        from litellm.proxy.auth.auth_checks import get_key_object
        from litellm.proxy.proxy_server import prisma_client, user_api_key_cache

        _total_key_spend = (key_spend or 0) + response_cost
        user_api_key_dict = UserAPIKeyAuth(
            token=user_api_key,
            key_alias=user_api_key_alias,
            max_budget=key_max_budget,
            spend=_total_key_spend,
        )
        try:
            if user_api_key_dict.token:
                key_object = await get_key_object(
                    hashed_token=user_api_key_dict.token,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                )
                if key_object:
                    user_api_key_dict.budget_reset_at = key_object.budget_reset_at
        except Exception as e:
            verbose_logger.debug(
                f"[Non-Blocking] Prometheus: Error getting key info: {str(e)}"
            )

        return user_api_key_dict

    def _get_remaining_hours_for_budget_reset(self, budget_reset_at: datetime) -> float:
        """
        Get remaining hours for budget reset
        """
        return (
            budget_reset_at - datetime.now(budget_reset_at.tzinfo)
        ).total_seconds() / 3600

    def _safe_duration_seconds(
        self,
        start_time: Any,
        end_time: Any,
    ) -> Optional[float]:
        """
        Compute the duration in seconds between two objects.

        Returns the duration as a float if both start and end are instances of datetime,
        otherwise returns None.
        """
        if isinstance(start_time, datetime) and isinstance(end_time, datetime):
            return (end_time - start_time).total_seconds()
        return None

    @staticmethod
    def initialize_budget_metrics_cron_job(scheduler: AsyncIOScheduler):
        """
        Initialize budget metrics as a cron job. This job runs every `PROMETHEUS_BUDGET_METRICS_REFRESH_INTERVAL_MINUTES` minutes.

        It emits the current remaining budget metrics for all Keys and Teams.
        """
        from litellm.constants import PROMETHEUS_BUDGET_METRICS_REFRESH_INTERVAL_MINUTES
        from litellm.integrations.custom_logger import CustomLogger
        from litellm.integrations.prometheus import PrometheusLogger

        prometheus_loggers: List[CustomLogger] = (
            litellm.logging_callback_manager.get_custom_loggers_for_type(
                callback_type=PrometheusLogger
            )
        )
        # we need to get the initialized prometheus logger instance(s) and call logger.initialize_remaining_budget_metrics() on them
        verbose_logger.debug("found %s prometheus loggers", len(prometheus_loggers))
        if len(prometheus_loggers) > 0:
            prometheus_logger = cast(PrometheusLogger, prometheus_loggers[0])
            verbose_logger.debug(
                "Initializing remaining budget metrics as a cron job executing every %s minutes"
                % PROMETHEUS_BUDGET_METRICS_REFRESH_INTERVAL_MINUTES
            )
            scheduler.add_job(
                prometheus_logger.initialize_remaining_budget_metrics,
                "interval",
                minutes=PROMETHEUS_BUDGET_METRICS_REFRESH_INTERVAL_MINUTES,
            )

    @staticmethod
    def _mount_metrics_endpoint(premium_user: bool):
        """
        Mount the Prometheus metrics endpoint with optional authentication.

        Args:
            premium_user (bool): Whether the user is a premium user
            require_auth (bool, optional): Whether to require authentication for the metrics endpoint.
                                        Defaults to False.
        """
        from prometheus_client import make_asgi_app

        from litellm._logging import verbose_proxy_logger
        from litellm.proxy._types import CommonProxyErrors
        from litellm.proxy.proxy_server import app

        if premium_user is not True:
            verbose_proxy_logger.warning(
                f"Prometheus metrics are only available for premium users. {CommonProxyErrors.not_premium_user.value}"
            )

        # Create metrics ASGI app
        metrics_app = make_asgi_app()

        # Mount the metrics app to the app
        app.mount("/metrics", metrics_app)
        verbose_proxy_logger.debug(
            "Starting Prometheus Metrics on /metrics (no authentication)"
        )


def prometheus_label_factory(
    supported_enum_labels: List[str],
    enum_values: UserAPIKeyLabelValues,
    tag: Optional[str] = None,
) -> dict:
    """
    Returns a dictionary of label + values for prometheus.

    Ensures end_user param is not sent to prometheus if it is not supported.
    """
    # Extract dictionary from Pydantic object
    enum_dict = enum_values.model_dump()

    # Filter supported labels
    filtered_labels = {
        label: value
        for label, value in enum_dict.items()
        if label in supported_enum_labels
    }

    if UserAPIKeyLabelNames.END_USER.value in filtered_labels:
        filtered_labels["end_user"] = get_end_user_id_for_cost_tracking(
            litellm_params={"user_api_key_end_user_id": enum_values.end_user},
            service_type="prometheus",
        )

    if enum_values.custom_metadata_labels is not None:
        for key, value in enum_values.custom_metadata_labels.items():
            if key in supported_enum_labels:
                filtered_labels[key] = value

    for label in supported_enum_labels:
        if label not in filtered_labels:
            filtered_labels[label] = None

    return filtered_labels


def get_custom_labels_from_metadata(metadata: dict) -> Dict[str, str]:
    """
    Get custom labels from metadata
    """
    keys = litellm.custom_prometheus_metadata_labels
    if keys is None or len(keys) == 0:
        return {}

    result: Dict[str, str] = {}

    for key in keys:
        # Split the dot notation key into parts
        original_key = key
        key = key.replace("metadata.", "", 1) if key.startswith("metadata.") else key

        keys_parts = key.split(".")
        # Traverse through the dictionary using the parts
        value = metadata
        for part in keys_parts:
            value = value.get(part, None)  # Get the value, return None if not found
            if value is None:
                break

        if value is not None and isinstance(value, str):
            result[original_key.replace(".", "_")] = value

    return result