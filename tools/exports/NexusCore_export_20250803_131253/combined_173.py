
# === NexusCore/tools\exports\export_20250803_114325\combined_72.py ===

# === NexusCore/openenv\Lib\site-packages\rich\progress.py ===
import io
import sys
import typing
import warnings
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import timedelta
from io import RawIOBase, UnsupportedOperation
from math import ceil
from mmap import mmap
from operator import length_hint
from os import PathLike, stat
from threading import Event, RLock, Thread
from types import TracebackType
from typing import (
    Any,
    BinaryIO,
    Callable,
    ContextManager,
    Deque,
    Dict,
    Generic,
    Iterable,
    List,
    NamedTuple,
    NewType,
    Optional,
    Sequence,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
)

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal  # pragma: no cover

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self  # pragma: no cover

from . import filesize, get_console
from .console import Console, Group, JustifyMethod, RenderableType
from .highlighter import Highlighter
from .jupyter import JupyterMixin
from .live import Live
from .progress_bar import ProgressBar
from .spinner import Spinner
from .style import StyleType
from .table import Column, Table
from .text import Text, TextType

TaskID = NewType("TaskID", int)

ProgressType = TypeVar("ProgressType")

GetTimeCallable = Callable[[], float]


_I = typing.TypeVar("_I", TextIO, BinaryIO)


class _TrackThread(Thread):
    """A thread to periodically update progress."""

    def __init__(self, progress: "Progress", task_id: "TaskID", update_period: float):
        self.progress = progress
        self.task_id = task_id
        self.update_period = update_period
        self.done = Event()

        self.completed = 0
        super().__init__(daemon=True)

    def run(self) -> None:
        task_id = self.task_id
        advance = self.progress.advance
        update_period = self.update_period
        last_completed = 0
        wait = self.done.wait
        while not wait(update_period) and self.progress.live.is_started:
            completed = self.completed
            if last_completed != completed:
                advance(task_id, completed - last_completed)
                last_completed = completed

        self.progress.update(self.task_id, completed=self.completed, refresh=True)

    def __enter__(self) -> "_TrackThread":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.done.set()
        self.join()


def track(
    sequence: Union[Sequence[ProgressType], Iterable[ProgressType]],
    description: str = "Working...",
    total: Optional[float] = None,
    completed: int = 0,
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    update_period: float = 0.1,
    disable: bool = False,
    show_speed: bool = True,
) -> Iterable[ProgressType]:
    """Track progress by iterating over a sequence.

    Args:
        sequence (Iterable[ProgressType]): A sequence (must support "len") you wish to iterate over.
        description (str, optional): Description of task show next to progress bar. Defaults to "Working".
        total: (float, optional): Total number of steps. Default is len(sequence).
        completed (int, optional): Number of steps completed so far. Defaults to 0.
        auto_refresh (bool, optional): Automatic refresh, disable to force a refresh after each iteration. Default is True.
        transient: (bool, optional): Clear the progress on exit. Defaults to False.
        console (Console, optional): Console to write to. Default creates internal Console instance.
        refresh_per_second (float): Number of times per second to refresh the progress information. Defaults to 10.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
        update_period (float, optional): Minimum time (in seconds) between calls to update(). Defaults to 0.1.
        disable (bool, optional): Disable display of progress.
        show_speed (bool, optional): Show speed if total isn't known. Defaults to True.
    Returns:
        Iterable[ProgressType]: An iterable of the values in the sequence.

    """

    columns: List["ProgressColumn"] = (
        [TextColumn("[progress.description]{task.description}")] if description else []
    )
    columns.extend(
        (
            BarColumn(
                style=style,
                complete_style=complete_style,
                finished_style=finished_style,
                pulse_style=pulse_style,
            ),
            TaskProgressColumn(show_speed=show_speed),
            TimeRemainingColumn(elapsed_when_finished=True),
        )
    )
    progress = Progress(
        *columns,
        auto_refresh=auto_refresh,
        console=console,
        transient=transient,
        get_time=get_time,
        refresh_per_second=refresh_per_second or 10,
        disable=disable,
    )

    with progress:
        yield from progress.track(
            sequence,
            total=total,
            completed=completed,
            description=description,
            update_period=update_period,
        )


class _Reader(RawIOBase, BinaryIO):
    """A reader that tracks progress while it's being read from."""

    def __init__(
        self,
        handle: BinaryIO,
        progress: "Progress",
        task: TaskID,
        close_handle: bool = True,
    ) -> None:
        self.handle = handle
        self.progress = progress
        self.task = task
        self.close_handle = close_handle
        self._closed = False

    def __enter__(self) -> "_Reader":
        self.handle.__enter__()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def __iter__(self) -> BinaryIO:
        return self

    def __next__(self) -> bytes:
        line = next(self.handle)
        self.progress.advance(self.task, advance=len(line))
        return line

    @property
    def closed(self) -> bool:
        return self._closed

    def fileno(self) -> int:
        return self.handle.fileno()

    def isatty(self) -> bool:
        return self.handle.isatty()

    @property
    def mode(self) -> str:
        return self.handle.mode

    @property
    def name(self) -> str:
        return self.handle.name

    def readable(self) -> bool:
        return self.handle.readable()

    def seekable(self) -> bool:
        return self.handle.seekable()

    def writable(self) -> bool:
        return False

    def read(self, size: int = -1) -> bytes:
        block = self.handle.read(size)
        self.progress.advance(self.task, advance=len(block))
        return block

    def readinto(self, b: Union[bytearray, memoryview, mmap]):  # type: ignore[no-untyped-def, override]
        n = self.handle.readinto(b)  # type: ignore[attr-defined]
        self.progress.advance(self.task, advance=n)
        return n

    def readline(self, size: int = -1) -> bytes:  # type: ignore[override]
        line = self.handle.readline(size)
        self.progress.advance(self.task, advance=len(line))
        return line

    def readlines(self, hint: int = -1) -> List[bytes]:
        lines = self.handle.readlines(hint)
        self.progress.advance(self.task, advance=sum(map(len, lines)))
        return lines

    def close(self) -> None:
        if self.close_handle:
            self.handle.close()
        self._closed = True

    def seek(self, offset: int, whence: int = 0) -> int:
        pos = self.handle.seek(offset, whence)
        self.progress.update(self.task, completed=pos)
        return pos

    def tell(self) -> int:
        return self.handle.tell()

    def write(self, s: Any) -> int:
        raise UnsupportedOperation("write")

    def writelines(self, lines: Iterable[Any]) -> None:
        raise UnsupportedOperation("writelines")


class _ReadContext(ContextManager[_I], Generic[_I]):
    """A utility class to handle a context for both a reader and a progress."""

    def __init__(self, progress: "Progress", reader: _I) -> None:
        self.progress = progress
        self.reader: _I = reader

    def __enter__(self) -> _I:
        self.progress.start()
        return self.reader.__enter__()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.progress.stop()
        self.reader.__exit__(exc_type, exc_val, exc_tb)


def wrap_file(
    file: BinaryIO,
    total: int,
    *,
    description: str = "Reading...",
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    disable: bool = False,
) -> ContextManager[BinaryIO]:
    """Read bytes from a file while tracking progress.

    Args:
        file (Union[str, PathLike[str], BinaryIO]): The path to the file to read, or a file-like object in binary mode.
        total (int): Total number of bytes to read.
        description (str, optional): Description of task show next to progress bar. Defaults to "Reading".
        auto_refresh (bool, optional): Automatic refresh, disable to force a refresh after each iteration. Default is True.
        transient: (bool, optional): Clear the progress on exit. Defaults to False.
        console (Console, optional): Console to write to. Default creates internal Console instance.
        refresh_per_second (float): Number of times per second to refresh the progress information. Defaults to 10.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
        disable (bool, optional): Disable display of progress.
    Returns:
        ContextManager[BinaryIO]: A context manager yielding a progress reader.

    """

    columns: List["ProgressColumn"] = (
        [TextColumn("[progress.description]{task.description}")] if description else []
    )
    columns.extend(
        (
            BarColumn(
                style=style,
                complete_style=complete_style,
                finished_style=finished_style,
                pulse_style=pulse_style,
            ),
            DownloadColumn(),
            TimeRemainingColumn(),
        )
    )
    progress = Progress(
        *columns,
        auto_refresh=auto_refresh,
        console=console,
        transient=transient,
        get_time=get_time,
        refresh_per_second=refresh_per_second or 10,
        disable=disable,
    )

    reader = progress.wrap_file(file, total=total, description=description)
    return _ReadContext(progress, reader)


@typing.overload
def open(
    file: Union[str, "PathLike[str]", bytes],
    mode: Union[Literal["rt"], Literal["r"]],
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    *,
    total: Optional[int] = None,
    description: str = "Reading...",
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    disable: bool = False,
) -> ContextManager[TextIO]:
    pass


@typing.overload
def open(
    file: Union[str, "PathLike[str]", bytes],
    mode: Literal["rb"],
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    *,
    total: Optional[int] = None,
    description: str = "Reading...",
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    disable: bool = False,
) -> ContextManager[BinaryIO]:
    pass


def open(
    file: Union[str, "PathLike[str]", bytes],
    mode: Union[Literal["rb"], Literal["rt"], Literal["r"]] = "r",
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    *,
    total: Optional[int] = None,
    description: str = "Reading...",
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    disable: bool = False,
) -> Union[ContextManager[BinaryIO], ContextManager[TextIO]]:
    """Read bytes from a file while tracking progress.

    Args:
        path (Union[str, PathLike[str], BinaryIO]): The path to the file to read, or a file-like object in binary mode.
        mode (str): The mode to use to open the file. Only supports "r", "rb" or "rt".
        buffering (int): The buffering strategy to use, see :func:`io.open`.
        encoding (str, optional): The encoding to use when reading in text mode, see :func:`io.open`.
        errors (str, optional): The error handling strategy for decoding errors, see :func:`io.open`.
        newline (str, optional): The strategy for handling newlines in text mode, see :func:`io.open`
        total: (int, optional): Total number of bytes to read. Must be provided if reading from a file handle. Default for a path is os.stat(file).st_size.
        description (str, optional): Description of task show next to progress bar. Defaults to "Reading".
        auto_refresh (bool, optional): Automatic refresh, disable to force a refresh after each iteration. Default is True.
        transient: (bool, optional): Clear the progress on exit. Defaults to False.
        console (Console, optional): Console to write to. Default creates internal Console instance.
        refresh_per_second (float): Number of times per second to refresh the progress information. Defaults to 10.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
        disable (bool, optional): Disable display of progress.
        encoding (str, optional): The encoding to use when reading in text mode.

    Returns:
        ContextManager[BinaryIO]: A context manager yielding a progress reader.

    """

    columns: List["ProgressColumn"] = (
        [TextColumn("[progress.description]{task.description}")] if description else []
    )
    columns.extend(
        (
            BarColumn(
                style=style,
                complete_style=complete_style,
                finished_style=finished_style,
                pulse_style=pulse_style,
            ),
            DownloadColumn(),
            TimeRemainingColumn(),
        )
    )
    progress = Progress(
        *columns,
        auto_refresh=auto_refresh,
        console=console,
        transient=transient,
        get_time=get_time,
        refresh_per_second=refresh_per_second or 10,
        disable=disable,
    )

    reader = progress.open(
        file,
        mode=mode,
        buffering=buffering,
        encoding=encoding,
        errors=errors,
        newline=newline,
        total=total,
        description=description,
    )
    return _ReadContext(progress, reader)  # type: ignore[return-value, type-var]


class ProgressColumn(ABC):
    """Base class for a widget to use in progress display."""

    max_refresh: Optional[float] = None

    def __init__(self, table_column: Optional[Column] = None) -> None:
        self._table_column = table_column
        self._renderable_cache: Dict[TaskID, Tuple[float, RenderableType]] = {}
        self._update_time: Optional[float] = None

    def get_table_column(self) -> Column:
        """Get a table column, used to build tasks table."""
        return self._table_column or Column()

    def __call__(self, task: "Task") -> RenderableType:
        """Called by the Progress object to return a renderable for the given task.

        Args:
            task (Task): An object containing information regarding the task.

        Returns:
            RenderableType: Anything renderable (including str).
        """
        current_time = task.get_time()
        if self.max_refresh is not None and not task.completed:
            try:
                timestamp, renderable = self._renderable_cache[task.id]
            except KeyError:
                pass
            else:
                if timestamp + self.max_refresh > current_time:
                    return renderable

        renderable = self.render(task)
        self._renderable_cache[task.id] = (current_time, renderable)
        return renderable

    @abstractmethod
    def render(self, task: "Task") -> RenderableType:
        """Should return a renderable object."""


class RenderableColumn(ProgressColumn):
    """A column to insert an arbitrary column.

    Args:
        renderable (RenderableType, optional): Any renderable. Defaults to empty string.
    """

    def __init__(
        self, renderable: RenderableType = "", *, table_column: Optional[Column] = None
    ):
        self.renderable = renderable
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> RenderableType:
        return self.renderable


class SpinnerColumn(ProgressColumn):
    """A column with a 'spinner' animation.

    Args:
        spinner_name (str, optional): Name of spinner animation. Defaults to "dots".
        style (StyleType, optional): Style of spinner. Defaults to "progress.spinner".
        speed (float, optional): Speed factor of spinner. Defaults to 1.0.
        finished_text (TextType, optional): Text used when task is finished. Defaults to " ".
    """

    def __init__(
        self,
        spinner_name: str = "dots",
        style: Optional[StyleType] = "progress.spinner",
        speed: float = 1.0,
        finished_text: TextType = " ",
        table_column: Optional[Column] = None,
    ):
        self.spinner = Spinner(spinner_name, style=style, speed=speed)
        self.finished_text = (
            Text.from_markup(finished_text)
            if isinstance(finished_text, str)
            else finished_text
        )
        super().__init__(table_column=table_column)

    def set_spinner(
        self,
        spinner_name: str,
        spinner_style: Optional[StyleType] = "progress.spinner",
        speed: float = 1.0,
    ) -> None:
        """Set a new spinner.

        Args:
            spinner_name (str): Spinner name, see python -m rich.spinner.
            spinner_style (Optional[StyleType], optional): Spinner style. Defaults to "progress.spinner".
            speed (float, optional): Speed factor of spinner. Defaults to 1.0.
        """
        self.spinner = Spinner(spinner_name, style=spinner_style, speed=speed)

    def render(self, task: "Task") -> RenderableType:
        text = (
            self.finished_text
            if task.finished
            else self.spinner.render(task.get_time())
        )
        return text


class TextColumn(ProgressColumn):
    """A column containing text."""

    def __init__(
        self,
        text_format: str,
        style: StyleType = "none",
        justify: JustifyMethod = "left",
        markup: bool = True,
        highlighter: Optional[Highlighter] = None,
        table_column: Optional[Column] = None,
    ) -> None:
        self.text_format = text_format
        self.justify: JustifyMethod = justify
        self.style = style
        self.markup = markup
        self.highlighter = highlighter
        super().__init__(table_column=table_column or Column(no_wrap=True))

    def render(self, task: "Task") -> Text:
        _text = self.text_format.format(task=task)
        if self.markup:
            text = Text.from_markup(_text, style=self.style, justify=self.justify)
        else:
            text = Text(_text, style=self.style, justify=self.justify)
        if self.highlighter:
            self.highlighter.highlight(text)
        return text


class BarColumn(ProgressColumn):
    """Renders a visual progress bar.

    Args:
        bar_width (Optional[int], optional): Width of bar or None for full width. Defaults to 40.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
    """

    def __init__(
        self,
        bar_width: Optional[int] = 40,
        style: StyleType = "bar.back",
        complete_style: StyleType = "bar.complete",
        finished_style: StyleType = "bar.finished",
        pulse_style: StyleType = "bar.pulse",
        table_column: Optional[Column] = None,
    ) -> None:
        self.bar_width = bar_width
        self.style = style
        self.complete_style = complete_style
        self.finished_style = finished_style
        self.pulse_style = pulse_style
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> ProgressBar:
        """Gets a progress bar widget for a task."""
        return ProgressBar(
            total=max(0, task.total) if task.total is not None else None,
            completed=max(0, task.completed),
            width=None if self.bar_width is None else max(1, self.bar_width),
            pulse=not task.started,
            animation_time=task.get_time(),
            style=self.style,
            complete_style=self.complete_style,
            finished_style=self.finished_style,
            pulse_style=self.pulse_style,
        )


class TimeElapsedColumn(ProgressColumn):
    """Renders time elapsed."""

    def render(self, task: "Task") -> Text:
        """Show time elapsed."""
        elapsed = task.finished_time if task.finished else task.elapsed
        if elapsed is None:
            return Text("-:--:--", style="progress.elapsed")
        delta = timedelta(seconds=max(0, int(elapsed)))
        return Text(str(delta), style="progress.elapsed")


class TaskProgressColumn(TextColumn):
    """Show task progress as a percentage.

    Args:
        text_format (str, optional): Format for percentage display. Defaults to "[progress.percentage]{task.percentage:>3.0f}%".
        text_format_no_percentage (str, optional): Format if percentage is unknown. Defaults to "".
        style (StyleType, optional): Style of output. Defaults to "none".
        justify (JustifyMethod, optional): Text justification. Defaults to "left".
        markup (bool, optional): Enable markup. Defaults to True.
        highlighter (Optional[Highlighter], optional): Highlighter to apply to output. Defaults to None.
        table_column (Optional[Column], optional): Table Column to use. Defaults to None.
        show_speed (bool, optional): Show speed if total is unknown. Defaults to False.
    """

    def __init__(
        self,
        text_format: str = "[progress.percentage]{task.percentage:>3.0f}%",
        text_format_no_percentage: str = "",
        style: StyleType = "none",
        justify: JustifyMethod = "left",
        markup: bool = True,
        highlighter: Optional[Highlighter] = None,
        table_column: Optional[Column] = None,
        show_speed: bool = False,
    ) -> None:
        self.text_format_no_percentage = text_format_no_percentage
        self.show_speed = show_speed
        super().__init__(
            text_format=text_format,
            style=style,
            justify=justify,
            markup=markup,
            highlighter=highlighter,
            table_column=table_column,
        )

    @classmethod
    def render_speed(cls, speed: Optional[float]) -> Text:
        """Render the speed in iterations per second.

        Args:
            task (Task): A Task object.

        Returns:
            Text: Text object containing the task speed.
        """
        if speed is None:
            return Text("", style="progress.percentage")
        unit, suffix = filesize.pick_unit_and_suffix(
            int(speed),
            ["", "×10³", "×10⁶", "×10⁹", "×10¹²"],
            1000,
        )
        data_speed = speed / unit
        return Text(f"{data_speed:.1f}{suffix} it/s", style="progress.percentage")

    def render(self, task: "Task") -> Text:
        if task.total is None and self.show_speed:
            return self.render_speed(task.finished_speed or task.speed)
        text_format = (
            self.text_format_no_percentage if task.total is None else self.text_format
        )
        _text = text_format.format(task=task)
        if self.markup:
            text = Text.from_markup(_text, style=self.style, justify=self.justify)
        else:
            text = Text(_text, style=self.style, justify=self.justify)
        if self.highlighter:
            self.highlighter.highlight(text)
        return text


class TimeRemainingColumn(ProgressColumn):
    """Renders estimated time remaining.

    Args:
        compact (bool, optional): Render MM:SS when time remaining is less than an hour. Defaults to False.
        elapsed_when_finished (bool, optional): Render time elapsed when the task is finished. Defaults to False.
    """

    # Only refresh twice a second to prevent jitter
    max_refresh = 0.5

    def __init__(
        self,
        compact: bool = False,
        elapsed_when_finished: bool = False,
        table_column: Optional[Column] = None,
    ):
        self.compact = compact
        self.elapsed_when_finished = elapsed_when_finished
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> Text:
        """Show time remaining."""
        if self.elapsed_when_finished and task.finished:
            task_time = task.finished_time
            style = "progress.elapsed"
        else:
            task_time = task.time_remaining
            style = "progress.remaining"

        if task.total is None:
            return Text("", style=style)

        if task_time is None:
            return Text("--:--" if self.compact else "-:--:--", style=style)

        # Based on https://github.com/tqdm/tqdm/blob/master/tqdm/std.py
        minutes, seconds = divmod(int(task_time), 60)
        hours, minutes = divmod(minutes, 60)

        if self.compact and not hours:
            formatted = f"{minutes:02d}:{seconds:02d}"
        else:
            formatted = f"{hours:d}:{minutes:02d}:{seconds:02d}"

        return Text(formatted, style=style)


class FileSizeColumn(ProgressColumn):
    """Renders completed filesize."""

    def render(self, task: "Task") -> Text:
        """Show data completed."""
        data_size = filesize.decimal(int(task.completed))
        return Text(data_size, style="progress.filesize")


class TotalFileSizeColumn(ProgressColumn):
    """Renders total filesize."""

    def render(self, task: "Task") -> Text:
        """Show data completed."""
        data_size = filesize.decimal(int(task.total)) if task.total is not None else ""
        return Text(data_size, style="progress.filesize.total")


class MofNCompleteColumn(ProgressColumn):
    """Renders completed count/total, e.g. '  10/1000'.

    Best for bounded tasks with int quantities.

    Space pads the completed count so that progress length does not change as task progresses
    past powers of 10.

    Args:
        separator (str, optional): Text to separate completed and total values. Defaults to "/".
    """

    def __init__(self, separator: str = "/", table_column: Optional[Column] = None):
        self.separator = separator
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> Text:
        """Show completed/total."""
        completed = int(task.completed)
        total = int(task.total) if task.total is not None else "?"
        total_width = len(str(total))
        return Text(
            f"{completed:{total_width}d}{self.separator}{total}",
            style="progress.download",
        )


class DownloadColumn(ProgressColumn):
    """Renders file size downloaded and total, e.g. '0.5/2.3 GB'.

    Args:
        binary_units (bool, optional): Use binary units, KiB, MiB etc. Defaults to False.
    """

    def __init__(
        self, binary_units: bool = False, table_column: Optional[Column] = None
    ) -> None:
        self.binary_units = binary_units
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> Text:
        """Calculate common unit for completed and total."""
        completed = int(task.completed)

        unit_and_suffix_calculation_base = (
            int(task.total) if task.total is not None else completed
        )
        if self.binary_units:
            unit, suffix = filesize.pick_unit_and_suffix(
                unit_and_suffix_calculation_base,
                ["bytes", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"],
                1024,
            )
        else:
            unit, suffix = filesize.pick_unit_and_suffix(
                unit_and_suffix_calculation_base,
                ["bytes", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"],
                1000,
            )
        precision = 0 if unit == 1 else 1

        completed_ratio = completed / unit
        completed_str = f"{completed_ratio:,.{precision}f}"

        if task.total is not None:
            total = int(task.total)
            total_ratio = total / unit
            total_str = f"{total_ratio:,.{precision}f}"
        else:
            total_str = "?"

        download_status = f"{completed_str}/{total_str} {suffix}"
        download_text = Text(download_status, style="progress.download")
        return download_text


class TransferSpeedColumn(ProgressColumn):
    """Renders human readable transfer speed."""

    def render(self, task: "Task") -> Text:
        """Show data transfer speed."""
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("?", style="progress.data.speed")
        data_speed = filesize.decimal(int(speed))
        return Text(f"{data_speed}/s", style="progress.data.speed")


class ProgressSample(NamedTuple):
    """Sample of progress for a given time."""

    timestamp: float
    """Timestamp of sample."""
    completed: float
    """Number of steps completed."""


@dataclass
class Task:
    """Information regarding a progress task.

    This object should be considered read-only outside of the :class:`~Progress` class.

    """

    id: TaskID
    """Task ID associated with this task (used in Progress methods)."""

    description: str
    """str: Description of the task."""

    total: Optional[float]
    """Optional[float]: Total number of steps in this task."""

    completed: float
    """float: Number of steps completed"""

    _get_time: GetTimeCallable
    """Callable to get the current time."""

    finished_time: Optional[float] = None
    """float: Time task was finished."""

    visible: bool = True
    """bool: Indicates if this task is visible in the progress display."""

    fields: Dict[str, Any] = field(default_factory=dict)
    """dict: Arbitrary fields passed in via Progress.update."""

    start_time: Optional[float] = field(default=None, init=False, repr=False)
    """Optional[float]: Time this task was started, or None if not started."""

    stop_time: Optional[float] = field(default=None, init=False, repr=False)
    """Optional[float]: Time this task was stopped, or None if not stopped."""

    finished_speed: Optional[float] = None
    """Optional[float]: The last speed for a finished task."""

    _progress: Deque[ProgressSample] = field(
        default_factory=lambda: deque(maxlen=1000), init=False, repr=False
    )

    _lock: RLock = field(repr=False, default_factory=RLock)
    """Thread lock."""

    def get_time(self) -> float:
        """float: Get the current time, in seconds."""
        return self._get_time()

    @property
    def started(self) -> bool:
        """bool: Check if the task as started."""
        return self.start_time is not None

    @property
    def remaining(self) -> Optional[float]:
        """Optional[float]: Get the number of steps remaining, if a non-None total was set."""
        if self.total is None:
            return None
        return self.total - self.completed

    @property
    def elapsed(self) -> Optional[float]:
        """Optional[float]: Time elapsed since task was started, or ``None`` if the task hasn't started."""
        if self.start_time is None:
            return None
        if self.stop_time is not None:
            return self.stop_time - self.start_time
        return self.get_time() - self.start_time

    @property
    def finished(self) -> bool:
        """Check if the task has finished."""
        return self.finished_time is not None

    @property
    def percentage(self) -> float:
        """float: Get progress of task as a percentage. If a None total was set, returns 0"""
        if not self.total:
            return 0.0
        completed = (self.completed / self.total) * 100.0
        completed = min(100.0, max(0.0, completed))
        return completed

    @property
    def speed(self) -> Optional[float]:
        """Optional[float]: Get the estimated speed in steps per second."""
        if self.start_time is None:
            return None
        with self._lock:
            progress = self._progress
            if not progress:
                return None
            total_time = progress[-1].timestamp - progress[0].timestamp
            if total_time == 0:
                return None
            iter_progress = iter(progress)
            next(iter_progress)
            total_completed = sum(sample.completed for sample in iter_progress)
            speed = total_completed / total_time
            return speed

    @property
    def time_remaining(self) -> Optional[float]:
        """Optional[float]: Get estimated time to completion, or ``None`` if no data."""
        if self.finished:
            return 0.0
        speed = self.speed
        if not speed:
            return None
        remaining = self.remaining
        if remaining is None:
            return None
        estimate = ceil(remaining / speed)
        return estimate

    def _reset(self) -> None:
        """Reset progress."""
        self._progress.clear()
        self.finished_time = None
        self.finished_speed = None


class Progress(JupyterMixin):
    """Renders an auto-updating progress bar(s).

    Args:
        console (Console, optional): Optional Console instance. Defaults to an internal Console instance writing to stdout.
        auto_refresh (bool, optional): Enable auto refresh. If disabled, you will need to call `refresh()`.
        refresh_per_second (Optional[float], optional): Number of times per second to refresh the progress information or None to use default (10). Defaults to None.
        speed_estimate_period: (float, optional): Period (in seconds) used to calculate the speed estimate. Defaults to 30.
        transient: (bool, optional): Clear the progress on exit. Defaults to False.
        redirect_stdout: (bool, optional): Enable redirection of stdout, so ``print`` may be used. Defaults to True.
        redirect_stderr: (bool, optional): Enable redirection of stderr. Defaults to True.
        get_time: (Callable, optional): A callable that gets the current time, or None to use Console.get_time. Defaults to None.
        disable (bool, optional): Disable progress display. Defaults to False
        expand (bool, optional): Expand tasks table to fit width. Defaults to False.
    """

    def __init__(
        self,
        *columns: Union[str, ProgressColumn],
        console: Optional[Console] = None,
        auto_refresh: bool = True,
        refresh_per_second: float = 10,
        speed_estimate_period: float = 30.0,
        transient: bool = False,
        redirect_stdout: bool = True,
        redirect_stderr: bool = True,
        get_time: Optional[GetTimeCallable] = None,
        disable: bool = False,
        expand: bool = False,
    ) -> None:
        assert refresh_per_second > 0, "refresh_per_second must be > 0"
        self._lock = RLock()
        self.columns = columns or self.get_default_columns()
        self.speed_estimate_period = speed_estimate_period

        self.disable = disable
        self.expand = expand
        self._tasks: Dict[TaskID, Task] = {}
        self._task_index: TaskID = TaskID(0)
        self.live = Live(
            console=console or get_console(),
            auto_refresh=auto_refresh,
            refresh_per_second=refresh_per_second,
            transient=transient,
            redirect_stdout=redirect_stdout,
            redirect_stderr=redirect_stderr,
            get_renderable=self.get_renderable,
        )
        self.get_time = get_time or self.console.get_time
        self.print = self.console.print
        self.log = self.console.log

    @classmethod
    def get_default_columns(cls) -> Tuple[ProgressColumn, ...]:
        """Get the default columns used for a new Progress instance:
           - a text column for the description (TextColumn)
           - the bar itself (BarColumn)
           - a text column showing completion percentage (TextColumn)
           - an estimated-time-remaining column (TimeRemainingColumn)
        If the Progress instance is created without passing a columns argument,
        the default columns defined here will be used.

        You can also create a Progress instance using custom columns before
        and/or after the defaults, as in this example:

            progress = Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                "Elapsed:",
                TimeElapsedColumn(),
            )

        This code shows the creation of a Progress display, containing
        a spinner to the left, the default columns, and a labeled elapsed
        time column.
        """
        return (
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
        )

    @property
    def console(self) -> Console:
        return self.live.console

    @property
    def tasks(self) -> List[Task]:
        """Get a list of Task instances."""
        with self._lock:
            return list(self._tasks.values())

    @property
    def task_ids(self) -> List[TaskID]:
        """A list of task IDs."""
        with self._lock:
            return list(self._tasks.keys())

    @property
    def finished(self) -> bool:
        """Check if all tasks have been completed."""
        with self._lock:
            if not self._tasks:
                return True
            return all(task.finished for task in self._tasks.values())

    def start(self) -> None:
        """Start the progress display."""
        if not self.disable:
            self.live.start(refresh=True)

    def stop(self) -> None:
        """Stop the progress display."""
        self.live.stop()
        if not self.console.is_interactive and not self.console.is_jupyter:
            self.console.print()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.stop()

    def track(
        self,
        sequence: Union[Iterable[ProgressType], Sequence[ProgressType]],
        total: Optional[float] = None,
        completed: int = 0,
        task_id: Optional[TaskID] = None,
        description: str = "Working...",
        update_period: float = 0.1,
    ) -> Iterable[ProgressType]:
        """Track progress by iterating over a sequence.

        Args:
            sequence (Sequence[ProgressType]): A sequence of values you want to iterate over and track progress.
            total: (float, optional): Total number of steps. Default is len(sequence).
            completed (int, optional): Number of steps completed so far. Defaults to 0.
            task_id: (TaskID): Task to track. Default is new task.
            description: (str, optional): Description of task, if new task is created.
            update_period (float, optional): Minimum time (in seconds) between calls to update(). Defaults to 0.1.

        Returns:
            Iterable[ProgressType]: An iterable of values taken from the provided sequence.
        """
        if total is None:
            total = float(length_hint(sequence)) or None

        if task_id is None:
            task_id = self.add_task(description, total=total, completed=completed)
        else:
            self.update(task_id, total=total, completed=completed)

        if self.live.auto_refresh:
            with _TrackThread(self, task_id, update_period) as track_thread:
                for value in sequence:
                    yield value
                    track_thread.completed += 1
        else:
            advance = self.advance
            refresh = self.refresh
            for value in sequence:
                yield value
                advance(task_id, 1)
                refresh()

    def wrap_file(
        self,
        file: BinaryIO,
        total: Optional[int] = None,
        *,
        task_id: Optional[TaskID] = None,
        description: str = "Reading...",
    ) -> BinaryIO:
        """Track progress file reading from a binary file.

        Args:
            file (BinaryIO): A file-like object opened in binary mode.
            total (int, optional): Total number of bytes to read. This must be provided unless a task with a total is also given.
            task_id (TaskID): Task to track. Default is new task.
            description (str, optional): Description of task, if new task is created.

        Returns:
            BinaryIO: A readable file-like object in binary mode.

        Raises:
            ValueError: When no total value can be extracted from the arguments or the task.
        """
        # attempt to recover the total from the task
        total_bytes: Optional[float] = None
        if total is not None:
            total_bytes = total
        elif task_id is not None:
            with self._lock:
                total_bytes = self._tasks[task_id].total
        if total_bytes is None:
            raise ValueError(
                f"unable to get the total number of bytes, please specify 'total'"
            )

        # update total of task or create new task
        if task_id is None:
            task_id = self.add_task(description, total=total_bytes)
        else:
            self.update(task_id, total=total_bytes)

        return _Reader(file, self, task_id, close_handle=False)

    @typing.overload
    def open(
        self,
        file: Union[str, "PathLike[str]", bytes],
        mode: Literal["rb"],
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        *,
        total: Optional[int] = None,
        task_id: Optional[TaskID] = None,
        description: str = "Reading...",
    ) -> BinaryIO:
        pass

    @typing.overload
    def open(
        self,
        file: Union[str, "PathLike[str]", bytes],
        mode: Union[Literal["r"], Literal["rt"]],
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        *,
        total: Optional[int] = None,
        task_id: Optional[TaskID] = None,
        description: str = "Reading...",
    ) -> TextIO:
        pass

    def open(
        self,
        file: Union[str, "PathLike[str]", bytes],
        mode: Union[Literal["rb"], Literal["rt"], Literal["r"]] = "r",
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        *,
        total: Optional[int] = None,
        task_id: Optional[TaskID] = None,
        description: str = "Reading...",
    ) -> Union[BinaryIO, TextIO]:
        """Track progress while reading from a binary file.

        Args:
            path (Union[str, PathLike[str]]): The path to the file to read.
            mode (str): The mode to use to open the file. Only supports "r", "rb" or "rt".
            buffering (int): The buffering strategy to use, see :func:`io.open`.
            encoding (str, optional): The encoding to use when reading in text mode, see :func:`io.open`.
            errors (str, optional): The error handling strategy for decoding errors, see :func:`io.open`.
            newline (str, optional): The strategy for handling newlines in text mode, see :func:`io.open`.
            total (int, optional): Total number of bytes to read. If none given, os.stat(path).st_size is used.
            task_id (TaskID): Task to track. Default is new task.
            description (str, optional): Description of task, if new task is created.

        Returns:
            BinaryIO: A readable file-like object in binary mode.

        Raises:
            ValueError: When an invalid mode is given.
        """
        # normalize the mode (always rb, rt)
        _mode = "".join(sorted(mode, reverse=False))
        if _mode not in ("br", "rt", "r"):
            raise ValueError(f"invalid mode {mode!r}")

        # patch buffering to provide the same behaviour as the builtin `open`
        line_buffering = buffering == 1
        if _mode == "br" and buffering == 1:
            warnings.warn(
                "line buffering (buffering=1) isn't supported in binary mode, the default buffer size will be used",
                RuntimeWarning,
            )
            buffering = -1
        elif _mode in ("rt", "r"):
            if buffering == 0:
                raise ValueError("can't have unbuffered text I/O")
            elif buffering == 1:
                buffering = -1

        # attempt to get the total with `os.stat`
        if total is None:
            total = stat(file).st_size

        # update total of task or create new task
        if task_id is None:
            task_id = self.add_task(description, total=total)
        else:
            self.update(task_id, total=total)

        # open the file in binary mode,
        handle = io.open(file, "rb", buffering=buffering)
        reader = _Reader(handle, self, task_id, close_handle=True)

        # wrap the reader in a `TextIOWrapper` if text mode
        if mode in ("r", "rt"):
            return io.TextIOWrapper(
                reader,
                encoding=encoding,
                errors=errors,
                newline=newline,
                line_buffering=line_buffering,
            )

        return reader

    def start_task(self, task_id: TaskID) -> None:
        """Start a task.

        Starts a task (used when calculating elapsed time). You may need to call this manually,
        if you called ``add_task`` with ``start=False``.

        Args:
            task_id (TaskID): ID of task.
        """
        with self._lock:
            task = self._tasks[task_id]
            if task.start_time is None:
                task.start_time = self.get_time()

    def stop_task(self, task_id: TaskID) -> None:
        """Stop a task.

        This will freeze the elapsed time on the task.

        Args:
            task_id (TaskID): ID of task.
        """
        with self._lock:
            task = self._tasks[task_id]
            current_time = self.get_time()
            if task.start_time is None:
                task.start_time = current_time
            task.stop_time = current_time

    def update(
        self,
        task_id: TaskID,
        *,
        total: Optional[float] = None,
        completed: Optional[float] = None,
        advance: Optional[float] = None,
        description: Optional[str] = None,
        visible: Optional[bool] = None,
        refresh: bool = False,
        **fields: Any,
    ) -> None:
        """Update information associated with a task.

        Args:
            task_id (TaskID): Task id (returned by add_task).
            total (float, optional): Updates task.total if not None.
            completed (float, optional): Updates task.completed if not None.
            advance (float, optional): Add a value to task.completed if not None.
            description (str, optional): Change task description if not None.
            visible (bool, optional): Set visible flag if not None.
            refresh (bool): Force a refresh of progress information. Default is False.
            **fields (Any): Additional data fields required for rendering.
        """
        with self._lock:
            task = self._tasks[task_id]
            completed_start = task.completed

            if total is not None and total != task.total:
                task.total = total
                task._reset()
            if advance is not None:
                task.completed += advance
            if completed is not None:
                task.completed = completed
            if description is not None:
                task.description = description
            if visible is not None:
                task.visible = visible
            task.fields.update(fields)
            update_completed = task.completed - completed_start

            current_time = self.get_time()
            old_sample_time = current_time - self.speed_estimate_period
            _progress = task._progress

            popleft = _progress.popleft
            while _progress and _progress[0].timestamp < old_sample_time:
                popleft()
            if update_completed > 0:
                _progress.append(ProgressSample(current_time, update_completed))
            if (
                task.total is not None
                and task.completed >= task.total
                and task.finished_time is None
            ):
                task.finished_time = task.elapsed

        if refresh:
            self.refresh()

    def reset(
        self,
        task_id: TaskID,
        *,
        start: bool = True,
        total: Optional[float] = None,
        completed: int = 0,
        visible: Optional[bool] = None,
        description: Optional[str] = None,
        **fields: Any,
    ) -> None:
        """Reset a task so completed is 0 and the clock is reset.

        Args:
            task_id (TaskID): ID of task.
            start (bool, optional): Start the task after reset. Defaults to True.
            total (float, optional): New total steps in task, or None to use current total. Defaults to None.
            completed (int, optional): Number of steps completed. Defaults to 0.
            visible (bool, optional): Enable display of the task. Defaults to True.
            description (str, optional): Change task description if not None. Defaults to None.
            **fields (str): Additional data fields required for rendering.
        """
        current_time = self.get_time()
        with self._lock:
            task = self._tasks[task_id]
            task._reset()
            task.start_time = current_time if start else None
            if total is not None:
                task.total = total
            task.completed = completed
            if visible is not None:
                task.visible = visible
            if fields:
                task.fields = fields
            if description is not None:
                task.description = description
            task.finished_time = None
        self.refresh()

    def advance(self, task_id: TaskID, advance: float = 1) -> None:
        """Advance task by a number of steps.

        Args:
            task_id (TaskID): ID of task.
            advance (float): Number of steps to advance. Default is 1.
        """
        current_time = self.get_time()
        with self._lock:
            task = self._tasks[task_id]
            completed_start = task.completed
            task.completed += advance
            update_completed = task.completed - completed_start
            old_sample_time = current_time - self.speed_estimate_period
            _progress = task._progress

            popleft = _progress.popleft
            while _progress and _progress[0].timestamp < old_sample_time:
                popleft()
            while len(_progress) > 1000:
                popleft()
            _progress.append(ProgressSample(current_time, update_completed))
            if (
                task.total is not None
                and task.completed >= task.total
                and task.finished_time is None
            ):
                task.finished_time = task.elapsed
                task.finished_speed = task.speed

    def refresh(self) -> None:
        """Refresh (render) the progress information."""
        if not self.disable and self.live.is_started:
            self.live.refresh()

    def get_renderable(self) -> RenderableType:
        """Get a renderable for the progress display."""
        renderable = Group(*self.get_renderables())
        return renderable

    def get_renderables(self) -> Iterable[RenderableType]:
        """Get a number of renderables for the progress display."""
        table = self.make_tasks_table(self.tasks)
        yield table

    def make_tasks_table(self, tasks: Iterable[Task]) -> Table:
        """Get a table to render the Progress display.

        Args:
            tasks (Iterable[Task]): An iterable of Task instances, one per row of the table.

        Returns:
            Table: A table instance.
        """
        table_columns = (
            (
                Column(no_wrap=True)
                if isinstance(_column, str)
                else _column.get_table_column().copy()
            )
            for _column in self.columns
        )
        table = Table.grid(*table_columns, padding=(0, 1), expand=self.expand)

        for task in tasks:
            if task.visible:
                table.add_row(
                    *(
                        (
                            column.format(task=task)
                            if isinstance(column, str)
                            else column(task)
                        )
                        for column in self.columns
                    )
                )
        return table

    def __rich__(self) -> RenderableType:
        """Makes the Progress class itself renderable."""
        with self._lock:
            return self.get_renderable()

    def add_task(
        self,
        description: str,
        start: bool = True,
        total: Optional[float] = 100.0,
        completed: int = 0,
        visible: bool = True,
        **fields: Any,
    ) -> TaskID:
        """Add a new 'task' to the Progress display.

        Args:
            description (str): A description of the task.
            start (bool, optional): Start the task immediately (to calculate elapsed time). If set to False,
                you will need to call `start` manually. Defaults to True.
            total (float, optional): Number of total steps in the progress if known.
                Set to None to render a pulsing animation. Defaults to 100.
            completed (int, optional): Number of steps completed so far. Defaults to 0.
            visible (bool, optional): Enable display of the task. Defaults to True.
            **fields (str): Additional data fields required for rendering.

        Returns:
            TaskID: An ID you can use when calling `update`.
        """
        with self._lock:
            task = Task(
                self._task_index,
                description,
                total,
                completed,
                visible=visible,
                fields=fields,
                _get_time=self.get_time,
                _lock=self._lock,
            )
            self._tasks[self._task_index] = task
            if start:
                self.start_task(self._task_index)
            new_task_index = self._task_index
            self._task_index = TaskID(int(self._task_index) + 1)
        self.refresh()
        return new_task_index

    def remove_task(self, task_id: TaskID) -> None:
        """Delete a task if it exists.

        Args:
            task_id (TaskID): A task ID.

        """
        with self._lock:
            del self._tasks[task_id]


if __name__ == "__main__":  # pragma: no coverage
    import random
    import time

    from .panel import Panel
    from .rule import Rule
    from .syntax import Syntax
    from .table import Table

    syntax = Syntax(
        '''def loop_last(values: Iterable[T]) -> Iterable[Tuple[bool, T]]:
    """Iterate and generate a tuple with a flag for last value."""
    iter_values = iter(values)
    try:
        previous_value = next(iter_values)
    except StopIteration:
        return
    for value in iter_values:
        yield False, previous_value
        previous_value = value
    yield True, previous_value''',
        "python",
        line_numbers=True,
    )

    table = Table("foo", "bar", "baz")
    table.add_row("1", "2", "3")

    progress_renderables = [
        "Text may be printed while the progress bars are rendering.",
        Panel("In fact, [i]any[/i] renderable will work"),
        "Such as [magenta]tables[/]...",
        table,
        "Pretty printed structures...",
        {"type": "example", "text": "Pretty printed"},
        "Syntax...",
        syntax,
        Rule("Give it a try!"),
    ]

    from itertools import cycle

    examples = cycle(progress_renderables)

    console = Console(record=True)

    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task1 = progress.add_task("[red]Downloading", total=1000)
        task2 = progress.add_task("[green]Processing", total=1000)
        task3 = progress.add_task("[yellow]Thinking", total=None)

        while not progress.finished:
            progress.update(task1, advance=0.5)
            progress.update(task2, advance=0.3)
            time.sleep(0.01)
            if random.randint(0, 100) < 1:
                progress.log(next(examples))

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\progress.py ===
import io
import sys
import typing
import warnings
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import timedelta
from io import RawIOBase, UnsupportedOperation
from math import ceil
from mmap import mmap
from operator import length_hint
from os import PathLike, stat
from threading import Event, RLock, Thread
from types import TracebackType
from typing import (
    Any,
    BinaryIO,
    Callable,
    ContextManager,
    Deque,
    Dict,
    Generic,
    Iterable,
    List,
    NamedTuple,
    NewType,
    Optional,
    Sequence,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
)

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from pip._vendor.typing_extensions import Literal  # pragma: no cover

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from pip._vendor.typing_extensions import Self  # pragma: no cover

from . import filesize, get_console
from .console import Console, Group, JustifyMethod, RenderableType
from .highlighter import Highlighter
from .jupyter import JupyterMixin
from .live import Live
from .progress_bar import ProgressBar
from .spinner import Spinner
from .style import StyleType
from .table import Column, Table
from .text import Text, TextType

TaskID = NewType("TaskID", int)

ProgressType = TypeVar("ProgressType")

GetTimeCallable = Callable[[], float]


_I = typing.TypeVar("_I", TextIO, BinaryIO)


class _TrackThread(Thread):
    """A thread to periodically update progress."""

    def __init__(self, progress: "Progress", task_id: "TaskID", update_period: float):
        self.progress = progress
        self.task_id = task_id
        self.update_period = update_period
        self.done = Event()

        self.completed = 0
        super().__init__(daemon=True)

    def run(self) -> None:
        task_id = self.task_id
        advance = self.progress.advance
        update_period = self.update_period
        last_completed = 0
        wait = self.done.wait
        while not wait(update_period) and self.progress.live.is_started:
            completed = self.completed
            if last_completed != completed:
                advance(task_id, completed - last_completed)
                last_completed = completed

        self.progress.update(self.task_id, completed=self.completed, refresh=True)

    def __enter__(self) -> "_TrackThread":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.done.set()
        self.join()


def track(
    sequence: Union[Sequence[ProgressType], Iterable[ProgressType]],
    description: str = "Working...",
    total: Optional[float] = None,
    completed: int = 0,
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    update_period: float = 0.1,
    disable: bool = False,
    show_speed: bool = True,
) -> Iterable[ProgressType]:
    """Track progress by iterating over a sequence.

    Args:
        sequence (Iterable[ProgressType]): A sequence (must support "len") you wish to iterate over.
        description (str, optional): Description of task show next to progress bar. Defaults to "Working".
        total: (float, optional): Total number of steps. Default is len(sequence).
        completed (int, optional): Number of steps completed so far. Defaults to 0.
        auto_refresh (bool, optional): Automatic refresh, disable to force a refresh after each iteration. Default is True.
        transient: (bool, optional): Clear the progress on exit. Defaults to False.
        console (Console, optional): Console to write to. Default creates internal Console instance.
        refresh_per_second (float): Number of times per second to refresh the progress information. Defaults to 10.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
        update_period (float, optional): Minimum time (in seconds) between calls to update(). Defaults to 0.1.
        disable (bool, optional): Disable display of progress.
        show_speed (bool, optional): Show speed if total isn't known. Defaults to True.
    Returns:
        Iterable[ProgressType]: An iterable of the values in the sequence.

    """

    columns: List["ProgressColumn"] = (
        [TextColumn("[progress.description]{task.description}")] if description else []
    )
    columns.extend(
        (
            BarColumn(
                style=style,
                complete_style=complete_style,
                finished_style=finished_style,
                pulse_style=pulse_style,
            ),
            TaskProgressColumn(show_speed=show_speed),
            TimeRemainingColumn(elapsed_when_finished=True),
        )
    )
    progress = Progress(
        *columns,
        auto_refresh=auto_refresh,
        console=console,
        transient=transient,
        get_time=get_time,
        refresh_per_second=refresh_per_second or 10,
        disable=disable,
    )

    with progress:
        yield from progress.track(
            sequence,
            total=total,
            completed=completed,
            description=description,
            update_period=update_period,
        )


class _Reader(RawIOBase, BinaryIO):
    """A reader that tracks progress while it's being read from."""

    def __init__(
        self,
        handle: BinaryIO,
        progress: "Progress",
        task: TaskID,
        close_handle: bool = True,
    ) -> None:
        self.handle = handle
        self.progress = progress
        self.task = task
        self.close_handle = close_handle
        self._closed = False

    def __enter__(self) -> "_Reader":
        self.handle.__enter__()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def __iter__(self) -> BinaryIO:
        return self

    def __next__(self) -> bytes:
        line = next(self.handle)
        self.progress.advance(self.task, advance=len(line))
        return line

    @property
    def closed(self) -> bool:
        return self._closed

    def fileno(self) -> int:
        return self.handle.fileno()

    def isatty(self) -> bool:
        return self.handle.isatty()

    @property
    def mode(self) -> str:
        return self.handle.mode

    @property
    def name(self) -> str:
        return self.handle.name

    def readable(self) -> bool:
        return self.handle.readable()

    def seekable(self) -> bool:
        return self.handle.seekable()

    def writable(self) -> bool:
        return False

    def read(self, size: int = -1) -> bytes:
        block = self.handle.read(size)
        self.progress.advance(self.task, advance=len(block))
        return block

    def readinto(self, b: Union[bytearray, memoryview, mmap]):  # type: ignore[no-untyped-def, override]
        n = self.handle.readinto(b)  # type: ignore[attr-defined]
        self.progress.advance(self.task, advance=n)
        return n

    def readline(self, size: int = -1) -> bytes:  # type: ignore[override]
        line = self.handle.readline(size)
        self.progress.advance(self.task, advance=len(line))
        return line

    def readlines(self, hint: int = -1) -> List[bytes]:
        lines = self.handle.readlines(hint)
        self.progress.advance(self.task, advance=sum(map(len, lines)))
        return lines

    def close(self) -> None:
        if self.close_handle:
            self.handle.close()
        self._closed = True

    def seek(self, offset: int, whence: int = 0) -> int:
        pos = self.handle.seek(offset, whence)
        self.progress.update(self.task, completed=pos)
        return pos

    def tell(self) -> int:
        return self.handle.tell()

    def write(self, s: Any) -> int:
        raise UnsupportedOperation("write")

    def writelines(self, lines: Iterable[Any]) -> None:
        raise UnsupportedOperation("writelines")


class _ReadContext(ContextManager[_I], Generic[_I]):
    """A utility class to handle a context for both a reader and a progress."""

    def __init__(self, progress: "Progress", reader: _I) -> None:
        self.progress = progress
        self.reader: _I = reader

    def __enter__(self) -> _I:
        self.progress.start()
        return self.reader.__enter__()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.progress.stop()
        self.reader.__exit__(exc_type, exc_val, exc_tb)


def wrap_file(
    file: BinaryIO,
    total: int,
    *,
    description: str = "Reading...",
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    disable: bool = False,
) -> ContextManager[BinaryIO]:
    """Read bytes from a file while tracking progress.

    Args:
        file (Union[str, PathLike[str], BinaryIO]): The path to the file to read, or a file-like object in binary mode.
        total (int): Total number of bytes to read.
        description (str, optional): Description of task show next to progress bar. Defaults to "Reading".
        auto_refresh (bool, optional): Automatic refresh, disable to force a refresh after each iteration. Default is True.
        transient: (bool, optional): Clear the progress on exit. Defaults to False.
        console (Console, optional): Console to write to. Default creates internal Console instance.
        refresh_per_second (float): Number of times per second to refresh the progress information. Defaults to 10.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
        disable (bool, optional): Disable display of progress.
    Returns:
        ContextManager[BinaryIO]: A context manager yielding a progress reader.

    """

    columns: List["ProgressColumn"] = (
        [TextColumn("[progress.description]{task.description}")] if description else []
    )
    columns.extend(
        (
            BarColumn(
                style=style,
                complete_style=complete_style,
                finished_style=finished_style,
                pulse_style=pulse_style,
            ),
            DownloadColumn(),
            TimeRemainingColumn(),
        )
    )
    progress = Progress(
        *columns,
        auto_refresh=auto_refresh,
        console=console,
        transient=transient,
        get_time=get_time,
        refresh_per_second=refresh_per_second or 10,
        disable=disable,
    )

    reader = progress.wrap_file(file, total=total, description=description)
    return _ReadContext(progress, reader)


@typing.overload
def open(
    file: Union[str, "PathLike[str]", bytes],
    mode: Union[Literal["rt"], Literal["r"]],
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    *,
    total: Optional[int] = None,
    description: str = "Reading...",
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    disable: bool = False,
) -> ContextManager[TextIO]:
    pass


@typing.overload
def open(
    file: Union[str, "PathLike[str]", bytes],
    mode: Literal["rb"],
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    *,
    total: Optional[int] = None,
    description: str = "Reading...",
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    disable: bool = False,
) -> ContextManager[BinaryIO]:
    pass


def open(
    file: Union[str, "PathLike[str]", bytes],
    mode: Union[Literal["rb"], Literal["rt"], Literal["r"]] = "r",
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    *,
    total: Optional[int] = None,
    description: str = "Reading...",
    auto_refresh: bool = True,
    console: Optional[Console] = None,
    transient: bool = False,
    get_time: Optional[Callable[[], float]] = None,
    refresh_per_second: float = 10,
    style: StyleType = "bar.back",
    complete_style: StyleType = "bar.complete",
    finished_style: StyleType = "bar.finished",
    pulse_style: StyleType = "bar.pulse",
    disable: bool = False,
) -> Union[ContextManager[BinaryIO], ContextManager[TextIO]]:
    """Read bytes from a file while tracking progress.

    Args:
        path (Union[str, PathLike[str], BinaryIO]): The path to the file to read, or a file-like object in binary mode.
        mode (str): The mode to use to open the file. Only supports "r", "rb" or "rt".
        buffering (int): The buffering strategy to use, see :func:`io.open`.
        encoding (str, optional): The encoding to use when reading in text mode, see :func:`io.open`.
        errors (str, optional): The error handling strategy for decoding errors, see :func:`io.open`.
        newline (str, optional): The strategy for handling newlines in text mode, see :func:`io.open`
        total: (int, optional): Total number of bytes to read. Must be provided if reading from a file handle. Default for a path is os.stat(file).st_size.
        description (str, optional): Description of task show next to progress bar. Defaults to "Reading".
        auto_refresh (bool, optional): Automatic refresh, disable to force a refresh after each iteration. Default is True.
        transient: (bool, optional): Clear the progress on exit. Defaults to False.
        console (Console, optional): Console to write to. Default creates internal Console instance.
        refresh_per_second (float): Number of times per second to refresh the progress information. Defaults to 10.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
        disable (bool, optional): Disable display of progress.
        encoding (str, optional): The encoding to use when reading in text mode.

    Returns:
        ContextManager[BinaryIO]: A context manager yielding a progress reader.

    """

    columns: List["ProgressColumn"] = (
        [TextColumn("[progress.description]{task.description}")] if description else []
    )
    columns.extend(
        (
            BarColumn(
                style=style,
                complete_style=complete_style,
                finished_style=finished_style,
                pulse_style=pulse_style,
            ),
            DownloadColumn(),
            TimeRemainingColumn(),
        )
    )
    progress = Progress(
        *columns,
        auto_refresh=auto_refresh,
        console=console,
        transient=transient,
        get_time=get_time,
        refresh_per_second=refresh_per_second or 10,
        disable=disable,
    )

    reader = progress.open(
        file,
        mode=mode,
        buffering=buffering,
        encoding=encoding,
        errors=errors,
        newline=newline,
        total=total,
        description=description,
    )
    return _ReadContext(progress, reader)  # type: ignore[return-value, type-var]


class ProgressColumn(ABC):
    """Base class for a widget to use in progress display."""

    max_refresh: Optional[float] = None

    def __init__(self, table_column: Optional[Column] = None) -> None:
        self._table_column = table_column
        self._renderable_cache: Dict[TaskID, Tuple[float, RenderableType]] = {}
        self._update_time: Optional[float] = None

    def get_table_column(self) -> Column:
        """Get a table column, used to build tasks table."""
        return self._table_column or Column()

    def __call__(self, task: "Task") -> RenderableType:
        """Called by the Progress object to return a renderable for the given task.

        Args:
            task (Task): An object containing information regarding the task.

        Returns:
            RenderableType: Anything renderable (including str).
        """
        current_time = task.get_time()
        if self.max_refresh is not None and not task.completed:
            try:
                timestamp, renderable = self._renderable_cache[task.id]
            except KeyError:
                pass
            else:
                if timestamp + self.max_refresh > current_time:
                    return renderable

        renderable = self.render(task)
        self._renderable_cache[task.id] = (current_time, renderable)
        return renderable

    @abstractmethod
    def render(self, task: "Task") -> RenderableType:
        """Should return a renderable object."""


class RenderableColumn(ProgressColumn):
    """A column to insert an arbitrary column.

    Args:
        renderable (RenderableType, optional): Any renderable. Defaults to empty string.
    """

    def __init__(
        self, renderable: RenderableType = "", *, table_column: Optional[Column] = None
    ):
        self.renderable = renderable
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> RenderableType:
        return self.renderable


class SpinnerColumn(ProgressColumn):
    """A column with a 'spinner' animation.

    Args:
        spinner_name (str, optional): Name of spinner animation. Defaults to "dots".
        style (StyleType, optional): Style of spinner. Defaults to "progress.spinner".
        speed (float, optional): Speed factor of spinner. Defaults to 1.0.
        finished_text (TextType, optional): Text used when task is finished. Defaults to " ".
    """

    def __init__(
        self,
        spinner_name: str = "dots",
        style: Optional[StyleType] = "progress.spinner",
        speed: float = 1.0,
        finished_text: TextType = " ",
        table_column: Optional[Column] = None,
    ):
        self.spinner = Spinner(spinner_name, style=style, speed=speed)
        self.finished_text = (
            Text.from_markup(finished_text)
            if isinstance(finished_text, str)
            else finished_text
        )
        super().__init__(table_column=table_column)

    def set_spinner(
        self,
        spinner_name: str,
        spinner_style: Optional[StyleType] = "progress.spinner",
        speed: float = 1.0,
    ) -> None:
        """Set a new spinner.

        Args:
            spinner_name (str): Spinner name, see python -m rich.spinner.
            spinner_style (Optional[StyleType], optional): Spinner style. Defaults to "progress.spinner".
            speed (float, optional): Speed factor of spinner. Defaults to 1.0.
        """
        self.spinner = Spinner(spinner_name, style=spinner_style, speed=speed)

    def render(self, task: "Task") -> RenderableType:
        text = (
            self.finished_text
            if task.finished
            else self.spinner.render(task.get_time())
        )
        return text


class TextColumn(ProgressColumn):
    """A column containing text."""

    def __init__(
        self,
        text_format: str,
        style: StyleType = "none",
        justify: JustifyMethod = "left",
        markup: bool = True,
        highlighter: Optional[Highlighter] = None,
        table_column: Optional[Column] = None,
    ) -> None:
        self.text_format = text_format
        self.justify: JustifyMethod = justify
        self.style = style
        self.markup = markup
        self.highlighter = highlighter
        super().__init__(table_column=table_column or Column(no_wrap=True))

    def render(self, task: "Task") -> Text:
        _text = self.text_format.format(task=task)
        if self.markup:
            text = Text.from_markup(_text, style=self.style, justify=self.justify)
        else:
            text = Text(_text, style=self.style, justify=self.justify)
        if self.highlighter:
            self.highlighter.highlight(text)
        return text


class BarColumn(ProgressColumn):
    """Renders a visual progress bar.

    Args:
        bar_width (Optional[int], optional): Width of bar or None for full width. Defaults to 40.
        style (StyleType, optional): Style for the bar background. Defaults to "bar.back".
        complete_style (StyleType, optional): Style for the completed bar. Defaults to "bar.complete".
        finished_style (StyleType, optional): Style for a finished bar. Defaults to "bar.finished".
        pulse_style (StyleType, optional): Style for pulsing bars. Defaults to "bar.pulse".
    """

    def __init__(
        self,
        bar_width: Optional[int] = 40,
        style: StyleType = "bar.back",
        complete_style: StyleType = "bar.complete",
        finished_style: StyleType = "bar.finished",
        pulse_style: StyleType = "bar.pulse",
        table_column: Optional[Column] = None,
    ) -> None:
        self.bar_width = bar_width
        self.style = style
        self.complete_style = complete_style
        self.finished_style = finished_style
        self.pulse_style = pulse_style
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> ProgressBar:
        """Gets a progress bar widget for a task."""
        return ProgressBar(
            total=max(0, task.total) if task.total is not None else None,
            completed=max(0, task.completed),
            width=None if self.bar_width is None else max(1, self.bar_width),
            pulse=not task.started,
            animation_time=task.get_time(),
            style=self.style,
            complete_style=self.complete_style,
            finished_style=self.finished_style,
            pulse_style=self.pulse_style,
        )


class TimeElapsedColumn(ProgressColumn):
    """Renders time elapsed."""

    def render(self, task: "Task") -> Text:
        """Show time elapsed."""
        elapsed = task.finished_time if task.finished else task.elapsed
        if elapsed is None:
            return Text("-:--:--", style="progress.elapsed")
        delta = timedelta(seconds=max(0, int(elapsed)))
        return Text(str(delta), style="progress.elapsed")


class TaskProgressColumn(TextColumn):
    """Show task progress as a percentage.

    Args:
        text_format (str, optional): Format for percentage display. Defaults to "[progress.percentage]{task.percentage:>3.0f}%".
        text_format_no_percentage (str, optional): Format if percentage is unknown. Defaults to "".
        style (StyleType, optional): Style of output. Defaults to "none".
        justify (JustifyMethod, optional): Text justification. Defaults to "left".
        markup (bool, optional): Enable markup. Defaults to True.
        highlighter (Optional[Highlighter], optional): Highlighter to apply to output. Defaults to None.
        table_column (Optional[Column], optional): Table Column to use. Defaults to None.
        show_speed (bool, optional): Show speed if total is unknown. Defaults to False.
    """

    def __init__(
        self,
        text_format: str = "[progress.percentage]{task.percentage:>3.0f}%",
        text_format_no_percentage: str = "",
        style: StyleType = "none",
        justify: JustifyMethod = "left",
        markup: bool = True,
        highlighter: Optional[Highlighter] = None,
        table_column: Optional[Column] = None,
        show_speed: bool = False,
    ) -> None:
        self.text_format_no_percentage = text_format_no_percentage
        self.show_speed = show_speed
        super().__init__(
            text_format=text_format,
            style=style,
            justify=justify,
            markup=markup,
            highlighter=highlighter,
            table_column=table_column,
        )

    @classmethod
    def render_speed(cls, speed: Optional[float]) -> Text:
        """Render the speed in iterations per second.

        Args:
            task (Task): A Task object.

        Returns:
            Text: Text object containing the task speed.
        """
        if speed is None:
            return Text("", style="progress.percentage")
        unit, suffix = filesize.pick_unit_and_suffix(
            int(speed),
            ["", "×10³", "×10⁶", "×10⁹", "×10¹²"],
            1000,
        )
        data_speed = speed / unit
        return Text(f"{data_speed:.1f}{suffix} it/s", style="progress.percentage")

    def render(self, task: "Task") -> Text:
        if task.total is None and self.show_speed:
            return self.render_speed(task.finished_speed or task.speed)
        text_format = (
            self.text_format_no_percentage if task.total is None else self.text_format
        )
        _text = text_format.format(task=task)
        if self.markup:
            text = Text.from_markup(_text, style=self.style, justify=self.justify)
        else:
            text = Text(_text, style=self.style, justify=self.justify)
        if self.highlighter:
            self.highlighter.highlight(text)
        return text


class TimeRemainingColumn(ProgressColumn):
    """Renders estimated time remaining.

    Args:
        compact (bool, optional): Render MM:SS when time remaining is less than an hour. Defaults to False.
        elapsed_when_finished (bool, optional): Render time elapsed when the task is finished. Defaults to False.
    """

    # Only refresh twice a second to prevent jitter
    max_refresh = 0.5

    def __init__(
        self,
        compact: bool = False,
        elapsed_when_finished: bool = False,
        table_column: Optional[Column] = None,
    ):
        self.compact = compact
        self.elapsed_when_finished = elapsed_when_finished
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> Text:
        """Show time remaining."""
        if self.elapsed_when_finished and task.finished:
            task_time = task.finished_time
            style = "progress.elapsed"
        else:
            task_time = task.time_remaining
            style = "progress.remaining"

        if task.total is None:
            return Text("", style=style)

        if task_time is None:
            return Text("--:--" if self.compact else "-:--:--", style=style)

        # Based on https://github.com/tqdm/tqdm/blob/master/tqdm/std.py
        minutes, seconds = divmod(int(task_time), 60)
        hours, minutes = divmod(minutes, 60)

        if self.compact and not hours:
            formatted = f"{minutes:02d}:{seconds:02d}"
        else:
            formatted = f"{hours:d}:{minutes:02d}:{seconds:02d}"

        return Text(formatted, style=style)


class FileSizeColumn(ProgressColumn):
    """Renders completed filesize."""

    def render(self, task: "Task") -> Text:
        """Show data completed."""
        data_size = filesize.decimal(int(task.completed))
        return Text(data_size, style="progress.filesize")


class TotalFileSizeColumn(ProgressColumn):
    """Renders total filesize."""

    def render(self, task: "Task") -> Text:
        """Show data completed."""
        data_size = filesize.decimal(int(task.total)) if task.total is not None else ""
        return Text(data_size, style="progress.filesize.total")


class MofNCompleteColumn(ProgressColumn):
    """Renders completed count/total, e.g. '  10/1000'.

    Best for bounded tasks with int quantities.

    Space pads the completed count so that progress length does not change as task progresses
    past powers of 10.

    Args:
        separator (str, optional): Text to separate completed and total values. Defaults to "/".
    """

    def __init__(self, separator: str = "/", table_column: Optional[Column] = None):
        self.separator = separator
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> Text:
        """Show completed/total."""
        completed = int(task.completed)
        total = int(task.total) if task.total is not None else "?"
        total_width = len(str(total))
        return Text(
            f"{completed:{total_width}d}{self.separator}{total}",
            style="progress.download",
        )


class DownloadColumn(ProgressColumn):
    """Renders file size downloaded and total, e.g. '0.5/2.3 GB'.

    Args:
        binary_units (bool, optional): Use binary units, KiB, MiB etc. Defaults to False.
    """

    def __init__(
        self, binary_units: bool = False, table_column: Optional[Column] = None
    ) -> None:
        self.binary_units = binary_units
        super().__init__(table_column=table_column)

    def render(self, task: "Task") -> Text:
        """Calculate common unit for completed and total."""
        completed = int(task.completed)

        unit_and_suffix_calculation_base = (
            int(task.total) if task.total is not None else completed
        )
        if self.binary_units:
            unit, suffix = filesize.pick_unit_and_suffix(
                unit_and_suffix_calculation_base,
                ["bytes", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"],
                1024,
            )
        else:
            unit, suffix = filesize.pick_unit_and_suffix(
                unit_and_suffix_calculation_base,
                ["bytes", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"],
                1000,
            )
        precision = 0 if unit == 1 else 1

        completed_ratio = completed / unit
        completed_str = f"{completed_ratio:,.{precision}f}"

        if task.total is not None:
            total = int(task.total)
            total_ratio = total / unit
            total_str = f"{total_ratio:,.{precision}f}"
        else:
            total_str = "?"

        download_status = f"{completed_str}/{total_str} {suffix}"
        download_text = Text(download_status, style="progress.download")
        return download_text


class TransferSpeedColumn(ProgressColumn):
    """Renders human readable transfer speed."""

    def render(self, task: "Task") -> Text:
        """Show data transfer speed."""
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("?", style="progress.data.speed")
        data_speed = filesize.decimal(int(speed))
        return Text(f"{data_speed}/s", style="progress.data.speed")


class ProgressSample(NamedTuple):
    """Sample of progress for a given time."""

    timestamp: float
    """Timestamp of sample."""
    completed: float
    """Number of steps completed."""


@dataclass
class Task:
    """Information regarding a progress task.

    This object should be considered read-only outside of the :class:`~Progress` class.

    """

    id: TaskID
    """Task ID associated with this task (used in Progress methods)."""

    description: str
    """str: Description of the task."""

    total: Optional[float]
    """Optional[float]: Total number of steps in this task."""

    completed: float
    """float: Number of steps completed"""

    _get_time: GetTimeCallable
    """Callable to get the current time."""

    finished_time: Optional[float] = None
    """float: Time task was finished."""

    visible: bool = True
    """bool: Indicates if this task is visible in the progress display."""

    fields: Dict[str, Any] = field(default_factory=dict)
    """dict: Arbitrary fields passed in via Progress.update."""

    start_time: Optional[float] = field(default=None, init=False, repr=False)
    """Optional[float]: Time this task was started, or None if not started."""

    stop_time: Optional[float] = field(default=None, init=False, repr=False)
    """Optional[float]: Time this task was stopped, or None if not stopped."""

    finished_speed: Optional[float] = None
    """Optional[float]: The last speed for a finished task."""

    _progress: Deque[ProgressSample] = field(
        default_factory=lambda: deque(maxlen=1000), init=False, repr=False
    )

    _lock: RLock = field(repr=False, default_factory=RLock)
    """Thread lock."""

    def get_time(self) -> float:
        """float: Get the current time, in seconds."""
        return self._get_time()

    @property
    def started(self) -> bool:
        """bool: Check if the task as started."""
        return self.start_time is not None

    @property
    def remaining(self) -> Optional[float]:
        """Optional[float]: Get the number of steps remaining, if a non-None total was set."""
        if self.total is None:
            return None
        return self.total - self.completed

    @property
    def elapsed(self) -> Optional[float]:
        """Optional[float]: Time elapsed since task was started, or ``None`` if the task hasn't started."""
        if self.start_time is None:
            return None
        if self.stop_time is not None:
            return self.stop_time - self.start_time
        return self.get_time() - self.start_time

    @property
    def finished(self) -> bool:
        """Check if the task has finished."""
        return self.finished_time is not None

    @property
    def percentage(self) -> float:
        """float: Get progress of task as a percentage. If a None total was set, returns 0"""
        if not self.total:
            return 0.0
        completed = (self.completed / self.total) * 100.0
        completed = min(100.0, max(0.0, completed))
        return completed

    @property
    def speed(self) -> Optional[float]:
        """Optional[float]: Get the estimated speed in steps per second."""
        if self.start_time is None:
            return None
        with self._lock:
            progress = self._progress
            if not progress:
                return None
            total_time = progress[-1].timestamp - progress[0].timestamp
            if total_time == 0:
                return None
            iter_progress = iter(progress)
            next(iter_progress)
            total_completed = sum(sample.completed for sample in iter_progress)
            speed = total_completed / total_time
            return speed

    @property
    def time_remaining(self) -> Optional[float]:
        """Optional[float]: Get estimated time to completion, or ``None`` if no data."""
        if self.finished:
            return 0.0
        speed = self.speed
        if not speed:
            return None
        remaining = self.remaining
        if remaining is None:
            return None
        estimate = ceil(remaining / speed)
        return estimate

    def _reset(self) -> None:
        """Reset progress."""
        self._progress.clear()
        self.finished_time = None
        self.finished_speed = None


class Progress(JupyterMixin):
    """Renders an auto-updating progress bar(s).

    Args:
        console (Console, optional): Optional Console instance. Defaults to an internal Console instance writing to stdout.
        auto_refresh (bool, optional): Enable auto refresh. If disabled, you will need to call `refresh()`.
        refresh_per_second (Optional[float], optional): Number of times per second to refresh the progress information or None to use default (10). Defaults to None.
        speed_estimate_period: (float, optional): Period (in seconds) used to calculate the speed estimate. Defaults to 30.
        transient: (bool, optional): Clear the progress on exit. Defaults to False.
        redirect_stdout: (bool, optional): Enable redirection of stdout, so ``print`` may be used. Defaults to True.
        redirect_stderr: (bool, optional): Enable redirection of stderr. Defaults to True.
        get_time: (Callable, optional): A callable that gets the current time, or None to use Console.get_time. Defaults to None.
        disable (bool, optional): Disable progress display. Defaults to False
        expand (bool, optional): Expand tasks table to fit width. Defaults to False.
    """

    def __init__(
        self,
        *columns: Union[str, ProgressColumn],
        console: Optional[Console] = None,
        auto_refresh: bool = True,
        refresh_per_second: float = 10,
        speed_estimate_period: float = 30.0,
        transient: bool = False,
        redirect_stdout: bool = True,
        redirect_stderr: bool = True,
        get_time: Optional[GetTimeCallable] = None,
        disable: bool = False,
        expand: bool = False,
    ) -> None:
        assert refresh_per_second > 0, "refresh_per_second must be > 0"
        self._lock = RLock()
        self.columns = columns or self.get_default_columns()
        self.speed_estimate_period = speed_estimate_period

        self.disable = disable
        self.expand = expand
        self._tasks: Dict[TaskID, Task] = {}
        self._task_index: TaskID = TaskID(0)
        self.live = Live(
            console=console or get_console(),
            auto_refresh=auto_refresh,
            refresh_per_second=refresh_per_second,
            transient=transient,
            redirect_stdout=redirect_stdout,
            redirect_stderr=redirect_stderr,
            get_renderable=self.get_renderable,
        )
        self.get_time = get_time or self.console.get_time
        self.print = self.console.print
        self.log = self.console.log

    @classmethod
    def get_default_columns(cls) -> Tuple[ProgressColumn, ...]:
        """Get the default columns used for a new Progress instance:
           - a text column for the description (TextColumn)
           - the bar itself (BarColumn)
           - a text column showing completion percentage (TextColumn)
           - an estimated-time-remaining column (TimeRemainingColumn)
        If the Progress instance is created without passing a columns argument,
        the default columns defined here will be used.

        You can also create a Progress instance using custom columns before
        and/or after the defaults, as in this example:

            progress = Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                "Elapsed:",
                TimeElapsedColumn(),
            )

        This code shows the creation of a Progress display, containing
        a spinner to the left, the default columns, and a labeled elapsed
        time column.
        """
        return (
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
        )

    @property
    def console(self) -> Console:
        return self.live.console

    @property
    def tasks(self) -> List[Task]:
        """Get a list of Task instances."""
        with self._lock:
            return list(self._tasks.values())

    @property
    def task_ids(self) -> List[TaskID]:
        """A list of task IDs."""
        with self._lock:
            return list(self._tasks.keys())

    @property
    def finished(self) -> bool:
        """Check if all tasks have been completed."""
        with self._lock:
            if not self._tasks:
                return True
            return all(task.finished for task in self._tasks.values())

    def start(self) -> None:
        """Start the progress display."""
        if not self.disable:
            self.live.start(refresh=True)

    def stop(self) -> None:
        """Stop the progress display."""
        self.live.stop()
        if not self.console.is_interactive and not self.console.is_jupyter:
            self.console.print()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.stop()

    def track(
        self,
        sequence: Union[Iterable[ProgressType], Sequence[ProgressType]],
        total: Optional[float] = None,
        completed: int = 0,
        task_id: Optional[TaskID] = None,
        description: str = "Working...",
        update_period: float = 0.1,
    ) -> Iterable[ProgressType]:
        """Track progress by iterating over a sequence.

        Args:
            sequence (Sequence[ProgressType]): A sequence of values you want to iterate over and track progress.
            total: (float, optional): Total number of steps. Default is len(sequence).
            completed (int, optional): Number of steps completed so far. Defaults to 0.
            task_id: (TaskID): Task to track. Default is new task.
            description: (str, optional): Description of task, if new task is created.
            update_period (float, optional): Minimum time (in seconds) between calls to update(). Defaults to 0.1.

        Returns:
            Iterable[ProgressType]: An iterable of values taken from the provided sequence.
        """
        if total is None:
            total = float(length_hint(sequence)) or None

        if task_id is None:
            task_id = self.add_task(description, total=total, completed=completed)
        else:
            self.update(task_id, total=total, completed=completed)

        if self.live.auto_refresh:
            with _TrackThread(self, task_id, update_period) as track_thread:
                for value in sequence:
                    yield value
                    track_thread.completed += 1
        else:
            advance = self.advance
            refresh = self.refresh
            for value in sequence:
                yield value
                advance(task_id, 1)
                refresh()

    def wrap_file(
        self,
        file: BinaryIO,
        total: Optional[int] = None,
        *,
        task_id: Optional[TaskID] = None,
        description: str = "Reading...",
    ) -> BinaryIO:
        """Track progress file reading from a binary file.

        Args:
            file (BinaryIO): A file-like object opened in binary mode.
            total (int, optional): Total number of bytes to read. This must be provided unless a task with a total is also given.
            task_id (TaskID): Task to track. Default is new task.
            description (str, optional): Description of task, if new task is created.

        Returns:
            BinaryIO: A readable file-like object in binary mode.

        Raises:
            ValueError: When no total value can be extracted from the arguments or the task.
        """
        # attempt to recover the total from the task
        total_bytes: Optional[float] = None
        if total is not None:
            total_bytes = total
        elif task_id is not None:
            with self._lock:
                total_bytes = self._tasks[task_id].total
        if total_bytes is None:
            raise ValueError(
                f"unable to get the total number of bytes, please specify 'total'"
            )

        # update total of task or create new task
        if task_id is None:
            task_id = self.add_task(description, total=total_bytes)
        else:
            self.update(task_id, total=total_bytes)

        return _Reader(file, self, task_id, close_handle=False)

    @typing.overload
    def open(
        self,
        file: Union[str, "PathLike[str]", bytes],
        mode: Literal["rb"],
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        *,
        total: Optional[int] = None,
        task_id: Optional[TaskID] = None,
        description: str = "Reading...",
    ) -> BinaryIO:
        pass

    @typing.overload
    def open(
        self,
        file: Union[str, "PathLike[str]", bytes],
        mode: Union[Literal["r"], Literal["rt"]],
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        *,
        total: Optional[int] = None,
        task_id: Optional[TaskID] = None,
        description: str = "Reading...",
    ) -> TextIO:
        pass

    def open(
        self,
        file: Union[str, "PathLike[str]", bytes],
        mode: Union[Literal["rb"], Literal["rt"], Literal["r"]] = "r",
        buffering: int = -1,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
        *,
        total: Optional[int] = None,
        task_id: Optional[TaskID] = None,
        description: str = "Reading...",
    ) -> Union[BinaryIO, TextIO]:
        """Track progress while reading from a binary file.

        Args:
            path (Union[str, PathLike[str]]): The path to the file to read.
            mode (str): The mode to use to open the file. Only supports "r", "rb" or "rt".
            buffering (int): The buffering strategy to use, see :func:`io.open`.
            encoding (str, optional): The encoding to use when reading in text mode, see :func:`io.open`.
            errors (str, optional): The error handling strategy for decoding errors, see :func:`io.open`.
            newline (str, optional): The strategy for handling newlines in text mode, see :func:`io.open`.
            total (int, optional): Total number of bytes to read. If none given, os.stat(path).st_size is used.
            task_id (TaskID): Task to track. Default is new task.
            description (str, optional): Description of task, if new task is created.

        Returns:
            BinaryIO: A readable file-like object in binary mode.

        Raises:
            ValueError: When an invalid mode is given.
        """
        # normalize the mode (always rb, rt)
        _mode = "".join(sorted(mode, reverse=False))
        if _mode not in ("br", "rt", "r"):
            raise ValueError(f"invalid mode {mode!r}")

        # patch buffering to provide the same behaviour as the builtin `open`
        line_buffering = buffering == 1
        if _mode == "br" and buffering == 1:
            warnings.warn(
                "line buffering (buffering=1) isn't supported in binary mode, the default buffer size will be used",
                RuntimeWarning,
            )
            buffering = -1
        elif _mode in ("rt", "r"):
            if buffering == 0:
                raise ValueError("can't have unbuffered text I/O")
            elif buffering == 1:
                buffering = -1

        # attempt to get the total with `os.stat`
        if total is None:
            total = stat(file).st_size

        # update total of task or create new task
        if task_id is None:
            task_id = self.add_task(description, total=total)
        else:
            self.update(task_id, total=total)

        # open the file in binary mode,
        handle = io.open(file, "rb", buffering=buffering)
        reader = _Reader(handle, self, task_id, close_handle=True)

        # wrap the reader in a `TextIOWrapper` if text mode
        if mode in ("r", "rt"):
            return io.TextIOWrapper(
                reader,
                encoding=encoding,
                errors=errors,
                newline=newline,
                line_buffering=line_buffering,
            )

        return reader

    def start_task(self, task_id: TaskID) -> None:
        """Start a task.

        Starts a task (used when calculating elapsed time). You may need to call this manually,
        if you called ``add_task`` with ``start=False``.

        Args:
            task_id (TaskID): ID of task.
        """
        with self._lock:
            task = self._tasks[task_id]
            if task.start_time is None:
                task.start_time = self.get_time()

    def stop_task(self, task_id: TaskID) -> None:
        """Stop a task.

        This will freeze the elapsed time on the task.

        Args:
            task_id (TaskID): ID of task.
        """
        with self._lock:
            task = self._tasks[task_id]
            current_time = self.get_time()
            if task.start_time is None:
                task.start_time = current_time
            task.stop_time = current_time

    def update(
        self,
        task_id: TaskID,
        *,
        total: Optional[float] = None,
        completed: Optional[float] = None,
        advance: Optional[float] = None,
        description: Optional[str] = None,
        visible: Optional[bool] = None,
        refresh: bool = False,
        **fields: Any,
    ) -> None:
        """Update information associated with a task.

        Args:
            task_id (TaskID): Task id (returned by add_task).
            total (float, optional): Updates task.total if not None.
            completed (float, optional): Updates task.completed if not None.
            advance (float, optional): Add a value to task.completed if not None.
            description (str, optional): Change task description if not None.
            visible (bool, optional): Set visible flag if not None.
            refresh (bool): Force a refresh of progress information. Default is False.
            **fields (Any): Additional data fields required for rendering.
        """
        with self._lock:
            task = self._tasks[task_id]
            completed_start = task.completed

            if total is not None and total != task.total:
                task.total = total
                task._reset()
            if advance is not None:
                task.completed += advance
            if completed is not None:
                task.completed = completed
            if description is not None:
                task.description = description
            if visible is not None:
                task.visible = visible
            task.fields.update(fields)
            update_completed = task.completed - completed_start

            current_time = self.get_time()
            old_sample_time = current_time - self.speed_estimate_period
            _progress = task._progress

            popleft = _progress.popleft
            while _progress and _progress[0].timestamp < old_sample_time:
                popleft()
            if update_completed > 0:
                _progress.append(ProgressSample(current_time, update_completed))
            if (
                task.total is not None
                and task.completed >= task.total
                and task.finished_time is None
            ):
                task.finished_time = task.elapsed

        if refresh:
            self.refresh()

    def reset(
        self,
        task_id: TaskID,
        *,
        start: bool = True,
        total: Optional[float] = None,
        completed: int = 0,
        visible: Optional[bool] = None,
        description: Optional[str] = None,
        **fields: Any,
    ) -> None:
        """Reset a task so completed is 0 and the clock is reset.

        Args:
            task_id (TaskID): ID of task.
            start (bool, optional): Start the task after reset. Defaults to True.
            total (float, optional): New total steps in task, or None to use current total. Defaults to None.
            completed (int, optional): Number of steps completed. Defaults to 0.
            visible (bool, optional): Enable display of the task. Defaults to True.
            description (str, optional): Change task description if not None. Defaults to None.
            **fields (str): Additional data fields required for rendering.
        """
        current_time = self.get_time()
        with self._lock:
            task = self._tasks[task_id]
            task._reset()
            task.start_time = current_time if start else None
            if total is not None:
                task.total = total
            task.completed = completed
            if visible is not None:
                task.visible = visible
            if fields:
                task.fields = fields
            if description is not None:
                task.description = description
            task.finished_time = None
        self.refresh()

    def advance(self, task_id: TaskID, advance: float = 1) -> None:
        """Advance task by a number of steps.

        Args:
            task_id (TaskID): ID of task.
            advance (float): Number of steps to advance. Default is 1.
        """
        current_time = self.get_time()
        with self._lock:
            task = self._tasks[task_id]
            completed_start = task.completed
            task.completed += advance
            update_completed = task.completed - completed_start
            old_sample_time = current_time - self.speed_estimate_period
            _progress = task._progress

            popleft = _progress.popleft
            while _progress and _progress[0].timestamp < old_sample_time:
                popleft()
            while len(_progress) > 1000:
                popleft()
            _progress.append(ProgressSample(current_time, update_completed))
            if (
                task.total is not None
                and task.completed >= task.total
                and task.finished_time is None
            ):
                task.finished_time = task.elapsed
                task.finished_speed = task.speed

    def refresh(self) -> None:
        """Refresh (render) the progress information."""
        if not self.disable and self.live.is_started:
            self.live.refresh()

    def get_renderable(self) -> RenderableType:
        """Get a renderable for the progress display."""
        renderable = Group(*self.get_renderables())
        return renderable

    def get_renderables(self) -> Iterable[RenderableType]:
        """Get a number of renderables for the progress display."""
        table = self.make_tasks_table(self.tasks)
        yield table

    def make_tasks_table(self, tasks: Iterable[Task]) -> Table:
        """Get a table to render the Progress display.

        Args:
            tasks (Iterable[Task]): An iterable of Task instances, one per row of the table.

        Returns:
            Table: A table instance.
        """
        table_columns = (
            (
                Column(no_wrap=True)
                if isinstance(_column, str)
                else _column.get_table_column().copy()
            )
            for _column in self.columns
        )
        table = Table.grid(*table_columns, padding=(0, 1), expand=self.expand)

        for task in tasks:
            if task.visible:
                table.add_row(
                    *(
                        (
                            column.format(task=task)
                            if isinstance(column, str)
                            else column(task)
                        )
                        for column in self.columns
                    )
                )
        return table

    def __rich__(self) -> RenderableType:
        """Makes the Progress class itself renderable."""
        with self._lock:
            return self.get_renderable()

    def add_task(
        self,
        description: str,
        start: bool = True,
        total: Optional[float] = 100.0,
        completed: int = 0,
        visible: bool = True,
        **fields: Any,
    ) -> TaskID:
        """Add a new 'task' to the Progress display.

        Args:
            description (str): A description of the task.
            start (bool, optional): Start the task immediately (to calculate elapsed time). If set to False,
                you will need to call `start` manually. Defaults to True.
            total (float, optional): Number of total steps in the progress if known.
                Set to None to render a pulsing animation. Defaults to 100.
            completed (int, optional): Number of steps completed so far. Defaults to 0.
            visible (bool, optional): Enable display of the task. Defaults to True.
            **fields (str): Additional data fields required for rendering.

        Returns:
            TaskID: An ID you can use when calling `update`.
        """
        with self._lock:
            task = Task(
                self._task_index,
                description,
                total,
                completed,
                visible=visible,
                fields=fields,
                _get_time=self.get_time,
                _lock=self._lock,
            )
            self._tasks[self._task_index] = task
            if start:
                self.start_task(self._task_index)
            new_task_index = self._task_index
            self._task_index = TaskID(int(self._task_index) + 1)
        self.refresh()
        return new_task_index

    def remove_task(self, task_id: TaskID) -> None:
        """Delete a task if it exists.

        Args:
            task_id (TaskID): A task ID.

        """
        with self._lock:
            del self._tasks[task_id]


if __name__ == "__main__":  # pragma: no coverage
    import random
    import time

    from .panel import Panel
    from .rule import Rule
    from .syntax import Syntax
    from .table import Table

    syntax = Syntax(
        '''def loop_last(values: Iterable[T]) -> Iterable[Tuple[bool, T]]:
    """Iterate and generate a tuple with a flag for last value."""
    iter_values = iter(values)
    try:
        previous_value = next(iter_values)
    except StopIteration:
        return
    for value in iter_values:
        yield False, previous_value
        previous_value = value
    yield True, previous_value''',
        "python",
        line_numbers=True,
    )

    table = Table("foo", "bar", "baz")
    table.add_row("1", "2", "3")

    progress_renderables = [
        "Text may be printed while the progress bars are rendering.",
        Panel("In fact, [i]any[/i] renderable will work"),
        "Such as [magenta]tables[/]...",
        table,
        "Pretty printed structures...",
        {"type": "example", "text": "Pretty printed"},
        "Syntax...",
        syntax,
        Rule("Give it a try!"),
    ]

    from itertools import cycle

    examples = cycle(progress_renderables)

    console = Console(record=True)

    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task1 = progress.add_task("[red]Downloading", total=1000)
        task2 = progress.add_task("[green]Processing", total=1000)
        task3 = progress.add_task("[yellow]Thinking", total=None)

        while not progress.finished:
            progress.update(task1, advance=0.5)
            progress.update(task2, advance=0.3)
            time.sleep(0.01)
            if random.randint(0, 100) < 1:
                progress.log(next(examples))

# === NexusCore/openenv\Lib\site-packages\tornado\websocket.py ===
"""Implementation of the WebSocket protocol.

`WebSockets <http://dev.w3.org/html5/websockets/>`_ allow for bidirectional
communication between the browser and server. WebSockets are supported in the
current versions of all major browsers.

This module implements the final version of the WebSocket protocol as
defined in `RFC 6455 <http://tools.ietf.org/html/rfc6455>`_.

.. versionchanged:: 4.0
   Removed support for the draft 76 protocol version.
"""

import abc
import asyncio
import base64
import functools
import hashlib
import logging
import os
import sys
import struct
import tornado
from urllib.parse import urlparse
import warnings
import zlib

from tornado.concurrent import Future, future_set_result_unless_cancelled
from tornado.escape import utf8, native_str, to_unicode
from tornado import gen, httpclient, httputil
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError, IOStream
from tornado.log import gen_log, app_log
from tornado.netutil import Resolver
from tornado import simple_httpclient
from tornado.queues import Queue
from tornado.tcpclient import TCPClient
from tornado.util import _websocket_mask

from typing import (
    TYPE_CHECKING,
    cast,
    Any,
    Optional,
    Dict,
    Union,
    List,
    Awaitable,
    Callable,
    Tuple,
    Type,
)
from types import TracebackType

if TYPE_CHECKING:
    from typing_extensions import Protocol

    # The zlib compressor types aren't actually exposed anywhere
    # publicly, so declare protocols for the portions we use.
    class _Compressor(Protocol):
        def compress(self, data: bytes) -> bytes:
            pass

        def flush(self, mode: int) -> bytes:
            pass

    class _Decompressor(Protocol):
        unconsumed_tail = b""  # type: bytes

        def decompress(self, data: bytes, max_length: int) -> bytes:
            pass

    class _WebSocketDelegate(Protocol):
        # The common base interface implemented by WebSocketHandler on
        # the server side and WebSocketClientConnection on the client
        # side.
        def on_ws_connection_close(
            self, close_code: Optional[int] = None, close_reason: Optional[str] = None
        ) -> None:
            pass

        def on_message(self, message: Union[str, bytes]) -> Optional["Awaitable[None]"]:
            pass

        def on_ping(self, data: bytes) -> None:
            pass

        def on_pong(self, data: bytes) -> None:
            pass

        def log_exception(
            self,
            typ: Optional[Type[BaseException]],
            value: Optional[BaseException],
            tb: Optional[TracebackType],
        ) -> None:
            pass


_default_max_message_size = 10 * 1024 * 1024

# log to "gen_log" but suppress duplicate log messages
de_dupe_gen_log = functools.lru_cache(gen_log.log)


class WebSocketError(Exception):
    pass


class WebSocketClosedError(WebSocketError):
    """Raised by operations on a closed connection.

    .. versionadded:: 3.2
    """

    pass


class _DecompressTooLargeError(Exception):
    pass


class _WebSocketParams:
    def __init__(
        self,
        ping_interval: Optional[float] = None,
        ping_timeout: Optional[float] = None,
        max_message_size: int = _default_max_message_size,
        compression_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.max_message_size = max_message_size
        self.compression_options = compression_options


class WebSocketHandler(tornado.web.RequestHandler):
    """Subclass this class to create a basic WebSocket handler.

    Override `on_message` to handle incoming messages, and use
    `write_message` to send messages to the client. You can also
    override `open` and `on_close` to handle opened and closed
    connections.

    Custom upgrade response headers can be sent by overriding
    `~tornado.web.RequestHandler.set_default_headers` or
    `~tornado.web.RequestHandler.prepare`.

    See http://dev.w3.org/html5/websockets/ for details on the
    JavaScript interface.  The protocol is specified at
    http://tools.ietf.org/html/rfc6455.

    Here is an example WebSocket handler that echos back all received messages
    back to the client:

    .. testcode::

      class EchoWebSocket(tornado.websocket.WebSocketHandler):
          def open(self):
              print("WebSocket opened")

          def on_message(self, message):
              self.write_message(u"You said: " + message)

          def on_close(self):
              print("WebSocket closed")

    WebSockets are not standard HTTP connections. The "handshake" is
    HTTP, but after the handshake, the protocol is
    message-based. Consequently, most of the Tornado HTTP facilities
    are not available in handlers of this type. The only communication
    methods available to you are `write_message()`, `ping()`, and
    `close()`. Likewise, your request handler class should implement
    `open()` method rather than ``get()`` or ``post()``.

    If you map the handler above to ``/websocket`` in your application, you can
    invoke it in JavaScript with::

      var ws = new WebSocket("ws://localhost:8888/websocket");
      ws.onopen = function() {
         ws.send("Hello, world");
      };
      ws.onmessage = function (evt) {
         alert(evt.data);
      };

    This script pops up an alert box that says "You said: Hello, world".

    Web browsers allow any site to open a websocket connection to any other,
    instead of using the same-origin policy that governs other network
    access from JavaScript.  This can be surprising and is a potential
    security hole, so since Tornado 4.0 `WebSocketHandler` requires
    applications that wish to receive cross-origin websockets to opt in
    by overriding the `~WebSocketHandler.check_origin` method (see that
    method's docs for details).  Failure to do so is the most likely
    cause of 403 errors when making a websocket connection.

    When using a secure websocket connection (``wss://``) with a self-signed
    certificate, the connection from a browser may fail because it wants
    to show the "accept this certificate" dialog but has nowhere to show it.
    You must first visit a regular HTML page using the same certificate
    to accept it before the websocket connection will succeed.

    If the application setting ``websocket_ping_interval`` has a non-zero
    value, a ping will be sent periodically, and the connection will be
    closed if a response is not received before the ``websocket_ping_timeout``.
    Both settings are in seconds; floating point values are allowed.
    The default timeout is equal to the interval.

    Messages larger than the ``websocket_max_message_size`` application setting
    (default 10MiB) will not be accepted.

    .. versionchanged:: 4.5
       Added ``websocket_ping_interval``, ``websocket_ping_timeout``, and
       ``websocket_max_message_size``.
    """

    def __init__(
        self,
        application: tornado.web.Application,
        request: httputil.HTTPServerRequest,
        **kwargs: Any,
    ) -> None:
        super().__init__(application, request, **kwargs)
        self.ws_connection = None  # type: Optional[WebSocketProtocol]
        self.close_code = None  # type: Optional[int]
        self.close_reason = None  # type: Optional[str]
        self._on_close_called = False

    async def get(self, *args: Any, **kwargs: Any) -> None:
        self.open_args = args
        self.open_kwargs = kwargs

        # Upgrade header should be present and should be equal to WebSocket
        if self.request.headers.get("Upgrade", "").lower() != "websocket":
            self.set_status(400)
            log_msg = 'Can "Upgrade" only to "WebSocket".'
            self.finish(log_msg)
            gen_log.debug(log_msg)
            return

        # Connection header should be upgrade.
        # Some proxy servers/load balancers
        # might mess with it.
        headers = self.request.headers
        connection = map(
            lambda s: s.strip().lower(), headers.get("Connection", "").split(",")
        )
        if "upgrade" not in connection:
            self.set_status(400)
            log_msg = '"Connection" must be "Upgrade".'
            self.finish(log_msg)
            gen_log.debug(log_msg)
            return

        # Handle WebSocket Origin naming convention differences
        # The difference between version 8 and 13 is that in 8 the
        # client sends a "Sec-Websocket-Origin" header and in 13 it's
        # simply "Origin".
        if "Origin" in self.request.headers:
            origin = self.request.headers.get("Origin")
        else:
            origin = self.request.headers.get("Sec-Websocket-Origin", None)

        # If there was an origin header, check to make sure it matches
        # according to check_origin. When the origin is None, we assume it
        # did not come from a browser and that it can be passed on.
        if origin is not None and not self.check_origin(origin):
            self.set_status(403)
            log_msg = "Cross origin websockets not allowed"
            self.finish(log_msg)
            gen_log.debug(log_msg)
            return

        self.ws_connection = self.get_websocket_protocol()
        if self.ws_connection:
            await self.ws_connection.accept_connection(self)
        else:
            self.set_status(426, "Upgrade Required")
            self.set_header("Sec-WebSocket-Version", "7, 8, 13")

    @property
    def ping_interval(self) -> Optional[float]:
        """The interval for sending websocket pings.

        If this is non-zero, the websocket will send a ping every
        ping_interval seconds.
        The client will respond with a "pong". The connection can be configured
        to timeout on late pong delivery using ``websocket_ping_timeout``.

        Set ``websocket_ping_interval = 0`` to disable pings.

        Default: ``0``
        """
        return self.settings.get("websocket_ping_interval", None)

    @property
    def ping_timeout(self) -> Optional[float]:
        """Timeout if no pong is received in this many seconds.

        To be used in combination with ``websocket_ping_interval > 0``.
        If a ping response (a "pong") is not received within
        ``websocket_ping_timeout`` seconds, then the websocket connection
        will be closed.

        This can help to clean up clients which have disconnected without
        cleanly closing the websocket connection.

        Note, the ping timeout cannot be longer than the ping interval.

        Set ``websocket_ping_timeout = 0`` to disable the ping timeout.

        Default: equal to the ``ping_interval``.

        .. versionchanged:: 6.5.0
           Default changed from the max of 3 pings or 30 seconds.
           The ping timeout can no longer be configured longer than the
           ping interval.
        """
        return self.settings.get("websocket_ping_timeout", None)

    @property
    def max_message_size(self) -> int:
        """Maximum allowed message size.

        If the remote peer sends a message larger than this, the connection
        will be closed.

        Default is 10MiB.
        """
        return self.settings.get(
            "websocket_max_message_size", _default_max_message_size
        )

    def write_message(
        self, message: Union[bytes, str, Dict[str, Any]], binary: bool = False
    ) -> "Future[None]":
        """Sends the given message to the client of this Web Socket.

        The message may be either a string or a dict (which will be
        encoded as json).  If the ``binary`` argument is false, the
        message will be sent as utf8; in binary mode any byte string
        is allowed.

        If the connection is already closed, raises `WebSocketClosedError`.
        Returns a `.Future` which can be used for flow control.

        .. versionchanged:: 3.2
           `WebSocketClosedError` was added (previously a closed connection
           would raise an `AttributeError`)

        .. versionchanged:: 4.3
           Returns a `.Future` which can be used for flow control.

        .. versionchanged:: 5.0
           Consistently raises `WebSocketClosedError`. Previously could
           sometimes raise `.StreamClosedError`.
        """
        if self.ws_connection is None or self.ws_connection.is_closing():
            raise WebSocketClosedError()
        if isinstance(message, dict):
            message = tornado.escape.json_encode(message)
        return self.ws_connection.write_message(message, binary=binary)

    def select_subprotocol(self, subprotocols: List[str]) -> Optional[str]:
        """Override to implement subprotocol negotiation.

        ``subprotocols`` is a list of strings identifying the
        subprotocols proposed by the client.  This method may be
        overridden to return one of those strings to select it, or
        ``None`` to not select a subprotocol.

        Failure to select a subprotocol does not automatically abort
        the connection, although clients may close the connection if
        none of their proposed subprotocols was selected.

        The list may be empty, in which case this method must return
        None. This method is always called exactly once even if no
        subprotocols were proposed so that the handler can be advised
        of this fact.

        .. versionchanged:: 5.1

           Previously, this method was called with a list containing
           an empty string instead of an empty list if no subprotocols
           were proposed by the client.
        """
        return None

    @property
    def selected_subprotocol(self) -> Optional[str]:
        """The subprotocol returned by `select_subprotocol`.

        .. versionadded:: 5.1
        """
        assert self.ws_connection is not None
        return self.ws_connection.selected_subprotocol

    def get_compression_options(self) -> Optional[Dict[str, Any]]:
        """Override to return compression options for the connection.

        If this method returns None (the default), compression will
        be disabled.  If it returns a dict (even an empty one), it
        will be enabled.  The contents of the dict may be used to
        control the following compression options:

        ``compression_level`` specifies the compression level.

        ``mem_level`` specifies the amount of memory used for the internal compression state.

         These parameters are documented in detail here:
         https://docs.python.org/3.13/library/zlib.html#zlib.compressobj

        .. versionadded:: 4.1

        .. versionchanged:: 4.5

           Added ``compression_level`` and ``mem_level``.
        """
        # TODO: Add wbits option.
        return None

    def open(self, *args: str, **kwargs: str) -> Optional[Awaitable[None]]:
        """Invoked when a new WebSocket is opened.

        The arguments to `open` are extracted from the `tornado.web.URLSpec`
        regular expression, just like the arguments to
        `tornado.web.RequestHandler.get`.

        `open` may be a coroutine. `on_message` will not be called until
        `open` has returned.

        .. versionchanged:: 5.1

           ``open`` may be a coroutine.
        """
        pass

    def on_message(self, message: Union[str, bytes]) -> Optional[Awaitable[None]]:
        """Handle incoming messages on the WebSocket

        This method must be overridden.

        .. versionchanged:: 4.5

           ``on_message`` can be a coroutine.
        """
        raise NotImplementedError

    def ping(self, data: Union[str, bytes] = b"") -> None:
        """Send ping frame to the remote end.

        The data argument allows a small amount of data (up to 125
        bytes) to be sent as a part of the ping message. Note that not
        all websocket implementations expose this data to
        applications.

        Consider using the ``websocket_ping_interval`` application
        setting instead of sending pings manually.

        .. versionchanged:: 5.1

           The data argument is now optional.

        """
        data = utf8(data)
        if self.ws_connection is None or self.ws_connection.is_closing():
            raise WebSocketClosedError()
        self.ws_connection.write_ping(data)

    def on_pong(self, data: bytes) -> None:
        """Invoked when the response to a ping frame is received."""
        pass

    def on_ping(self, data: bytes) -> None:
        """Invoked when the a ping frame is received."""
        pass

    def on_close(self) -> None:
        """Invoked when the WebSocket is closed.

        If the connection was closed cleanly and a status code or reason
        phrase was supplied, these values will be available as the attributes
        ``self.close_code`` and ``self.close_reason``.

        .. versionchanged:: 4.0

           Added ``close_code`` and ``close_reason`` attributes.
        """
        pass

    def close(self, code: Optional[int] = None, reason: Optional[str] = None) -> None:
        """Closes this Web Socket.

        Once the close handshake is successful the socket will be closed.

        ``code`` may be a numeric status code, taken from the values
        defined in `RFC 6455 section 7.4.1
        <https://tools.ietf.org/html/rfc6455#section-7.4.1>`_.
        ``reason`` may be a textual message about why the connection is
        closing.  These values are made available to the client, but are
        not otherwise interpreted by the websocket protocol.

        .. versionchanged:: 4.0

           Added the ``code`` and ``reason`` arguments.
        """
        if self.ws_connection:
            self.ws_connection.close(code, reason)
            self.ws_connection = None

    def check_origin(self, origin: str) -> bool:
        """Override to enable support for allowing alternate origins.

        The ``origin`` argument is the value of the ``Origin`` HTTP
        header, the url responsible for initiating this request.  This
        method is not called for clients that do not send this header;
        such requests are always allowed (because all browsers that
        implement WebSockets support this header, and non-browser
        clients do not have the same cross-site security concerns).

        Should return ``True`` to accept the request or ``False`` to
        reject it. By default, rejects all requests with an origin on
        a host other than this one.

        This is a security protection against cross site scripting attacks on
        browsers, since WebSockets are allowed to bypass the usual same-origin
        policies and don't use CORS headers.

        .. warning::

           This is an important security measure; don't disable it
           without understanding the security implications. In
           particular, if your authentication is cookie-based, you
           must either restrict the origins allowed by
           ``check_origin()`` or implement your own XSRF-like
           protection for websocket connections. See `these
           <https://www.christian-schneider.net/CrossSiteWebSocketHijacking.html>`_
           `articles
           <https://devcenter.heroku.com/articles/websocket-security>`_
           for more.

        To accept all cross-origin traffic (which was the default prior to
        Tornado 4.0), simply override this method to always return ``True``::

            def check_origin(self, origin):
                return True

        To allow connections from any subdomain of your site, you might
        do something like::

            def check_origin(self, origin):
                parsed_origin = urllib.parse.urlparse(origin)
                return parsed_origin.netloc.endswith(".mydomain.com")

        .. versionadded:: 4.0

        """
        parsed_origin = urlparse(origin)
        origin = parsed_origin.netloc
        origin = origin.lower()

        host = self.request.headers.get("Host")

        # Check to see that origin matches host directly, including ports
        return origin == host

    def set_nodelay(self, value: bool) -> None:
        """Set the no-delay flag for this stream.

        By default, small messages may be delayed and/or combined to minimize
        the number of packets sent.  This can sometimes cause 200-500ms delays
        due to the interaction between Nagle's algorithm and TCP delayed
        ACKs.  To reduce this delay (at the expense of possibly increasing
        bandwidth usage), call ``self.set_nodelay(True)`` once the websocket
        connection is established.

        See `.BaseIOStream.set_nodelay` for additional details.

        .. versionadded:: 3.1
        """
        assert self.ws_connection is not None
        self.ws_connection.set_nodelay(value)

    def on_connection_close(self) -> None:
        if self.ws_connection:
            self.ws_connection.on_connection_close()
            self.ws_connection = None
        if not self._on_close_called:
            self._on_close_called = True
            self.on_close()
            self._break_cycles()

    def on_ws_connection_close(
        self, close_code: Optional[int] = None, close_reason: Optional[str] = None
    ) -> None:
        self.close_code = close_code
        self.close_reason = close_reason
        self.on_connection_close()

    def _break_cycles(self) -> None:
        # WebSocketHandlers call finish() early, but we don't want to
        # break up reference cycles (which makes it impossible to call
        # self.render_string) until after we've really closed the
        # connection (if it was established in the first place,
        # indicated by status code 101).
        if self.get_status() != 101 or self._on_close_called:
            super()._break_cycles()

    def get_websocket_protocol(self) -> Optional["WebSocketProtocol"]:
        websocket_version = self.request.headers.get("Sec-WebSocket-Version")
        if websocket_version in ("7", "8", "13"):
            params = _WebSocketParams(
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
                max_message_size=self.max_message_size,
                compression_options=self.get_compression_options(),
            )
            return WebSocketProtocol13(self, False, params)
        return None

    def _detach_stream(self) -> IOStream:
        # disable non-WS methods
        for method in [
            "write",
            "redirect",
            "set_header",
            "set_cookie",
            "set_status",
            "flush",
            "finish",
        ]:
            setattr(self, method, _raise_not_supported_for_websockets)
        return self.detach()


def _raise_not_supported_for_websockets(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError("Method not supported for Web Sockets")


class WebSocketProtocol(abc.ABC):
    """Base class for WebSocket protocol versions."""

    def __init__(self, handler: "_WebSocketDelegate") -> None:
        self.handler = handler
        self.stream = None  # type: Optional[IOStream]
        self.client_terminated = False
        self.server_terminated = False

    def _run_callback(
        self, callback: Callable, *args: Any, **kwargs: Any
    ) -> "Optional[Future[Any]]":
        """Runs the given callback with exception handling.

        If the callback is a coroutine, returns its Future. On error, aborts the
        websocket connection and returns None.
        """
        try:
            result = callback(*args, **kwargs)
        except Exception:
            self.handler.log_exception(*sys.exc_info())
            self._abort()
            return None
        else:
            if result is not None:
                result = gen.convert_yielded(result)
                assert self.stream is not None
                self.stream.io_loop.add_future(result, lambda f: f.result())
            return result

    def on_connection_close(self) -> None:
        self._abort()

    def _abort(self) -> None:
        """Instantly aborts the WebSocket connection by closing the socket"""
        self.client_terminated = True
        self.server_terminated = True
        if self.stream is not None:
            self.stream.close()  # forcibly tear down the connection
        self.close()  # let the subclass cleanup

    @abc.abstractmethod
    def close(self, code: Optional[int] = None, reason: Optional[str] = None) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def is_closing(self) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    async def accept_connection(self, handler: WebSocketHandler) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def write_message(
        self, message: Union[str, bytes, Dict[str, Any]], binary: bool = False
    ) -> "Future[None]":
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def selected_subprotocol(self) -> Optional[str]:
        raise NotImplementedError()

    @abc.abstractmethod
    def write_ping(self, data: bytes) -> None:
        raise NotImplementedError()

    # The entry points below are used by WebSocketClientConnection,
    # which was introduced after we only supported a single version of
    # WebSocketProtocol. The WebSocketProtocol/WebSocketProtocol13
    # boundary is currently pretty ad-hoc.
    @abc.abstractmethod
    def _process_server_headers(
        self, key: Union[str, bytes], headers: httputil.HTTPHeaders
    ) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def start_pinging(self) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    async def _receive_frame_loop(self) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def set_nodelay(self, x: bool) -> None:
        raise NotImplementedError()


class _PerMessageDeflateCompressor:
    def __init__(
        self,
        persistent: bool,
        max_wbits: Optional[int],
        compression_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        if max_wbits is None:
            max_wbits = zlib.MAX_WBITS
        # There is no symbolic constant for the minimum wbits value.
        if not (8 <= max_wbits <= zlib.MAX_WBITS):
            raise ValueError(
                "Invalid max_wbits value %r; allowed range 8-%d",
                max_wbits,
                zlib.MAX_WBITS,
            )
        self._max_wbits = max_wbits

        if (
            compression_options is None
            or "compression_level" not in compression_options
        ):
            self._compression_level = tornado.web.GZipContentEncoding.GZIP_LEVEL
        else:
            self._compression_level = compression_options["compression_level"]

        if compression_options is None or "mem_level" not in compression_options:
            self._mem_level = 8
        else:
            self._mem_level = compression_options["mem_level"]

        if persistent:
            self._compressor = self._create_compressor()  # type: Optional[_Compressor]
        else:
            self._compressor = None

    def _create_compressor(self) -> "_Compressor":
        return zlib.compressobj(
            self._compression_level, zlib.DEFLATED, -self._max_wbits, self._mem_level
        )

    def compress(self, data: bytes) -> bytes:
        compressor = self._compressor or self._create_compressor()
        data = compressor.compress(data) + compressor.flush(zlib.Z_SYNC_FLUSH)
        assert data.endswith(b"\x00\x00\xff\xff")
        return data[:-4]


class _PerMessageDeflateDecompressor:
    def __init__(
        self,
        persistent: bool,
        max_wbits: Optional[int],
        max_message_size: int,
        compression_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._max_message_size = max_message_size
        if max_wbits is None:
            max_wbits = zlib.MAX_WBITS
        if not (8 <= max_wbits <= zlib.MAX_WBITS):
            raise ValueError(
                "Invalid max_wbits value %r; allowed range 8-%d",
                max_wbits,
                zlib.MAX_WBITS,
            )
        self._max_wbits = max_wbits
        if persistent:
            self._decompressor = (
                self._create_decompressor()
            )  # type: Optional[_Decompressor]
        else:
            self._decompressor = None

    def _create_decompressor(self) -> "_Decompressor":
        return zlib.decompressobj(-self._max_wbits)

    def decompress(self, data: bytes) -> bytes:
        decompressor = self._decompressor or self._create_decompressor()
        result = decompressor.decompress(
            data + b"\x00\x00\xff\xff", self._max_message_size
        )
        if decompressor.unconsumed_tail:
            raise _DecompressTooLargeError()
        return result


class WebSocketProtocol13(WebSocketProtocol):
    """Implementation of the WebSocket protocol from RFC 6455.

    This class supports versions 7 and 8 of the protocol in addition to the
    final version 13.
    """

    # Bit masks for the first byte of a frame.
    FIN = 0x80
    RSV1 = 0x40
    RSV2 = 0x20
    RSV3 = 0x10
    RSV_MASK = RSV1 | RSV2 | RSV3
    OPCODE_MASK = 0x0F

    stream = None  # type: IOStream

    def __init__(
        self,
        handler: "_WebSocketDelegate",
        mask_outgoing: bool,
        params: _WebSocketParams,
    ) -> None:
        WebSocketProtocol.__init__(self, handler)
        self.mask_outgoing = mask_outgoing
        self.params = params
        self._final_frame = False
        self._frame_opcode = None
        self._masked_frame = None
        self._frame_mask = None  # type: Optional[bytes]
        self._frame_length = None
        self._fragmented_message_buffer = None  # type: Optional[bytearray]
        self._fragmented_message_opcode = None
        self._waiting = None  # type: object
        self._compression_options = params.compression_options
        self._decompressor = None  # type: Optional[_PerMessageDeflateDecompressor]
        self._compressor = None  # type: Optional[_PerMessageDeflateCompressor]
        self._frame_compressed = None  # type: Optional[bool]
        # The total uncompressed size of all messages received or sent.
        # Unicode messages are encoded to utf8.
        # Only for testing; subject to change.
        self._message_bytes_in = 0
        self._message_bytes_out = 0
        # The total size of all packets received or sent.  Includes
        # the effect of compression, frame overhead, and control frames.
        self._wire_bytes_in = 0
        self._wire_bytes_out = 0
        self._received_pong = False  # type: bool
        self.close_code = None  # type: Optional[int]
        self.close_reason = None  # type: Optional[str]
        self._ping_coroutine = None  # type: Optional[asyncio.Task]

    # Use a property for this to satisfy the abc.
    @property
    def selected_subprotocol(self) -> Optional[str]:
        return self._selected_subprotocol

    @selected_subprotocol.setter
    def selected_subprotocol(self, value: Optional[str]) -> None:
        self._selected_subprotocol = value

    async def accept_connection(self, handler: WebSocketHandler) -> None:
        try:
            self._handle_websocket_headers(handler)
        except ValueError:
            handler.set_status(400)
            log_msg = "Missing/Invalid WebSocket headers"
            handler.finish(log_msg)
            gen_log.debug(log_msg)
            return

        try:
            await self._accept_connection(handler)
        except asyncio.CancelledError:
            self._abort()
            return
        except ValueError:
            gen_log.debug("Malformed WebSocket request received", exc_info=True)
            self._abort()
            return

    def _handle_websocket_headers(self, handler: WebSocketHandler) -> None:
        """Verifies all invariant- and required headers

        If a header is missing or have an incorrect value ValueError will be
        raised
        """
        fields = ("Host", "Sec-Websocket-Key", "Sec-Websocket-Version")
        if not all(map(lambda f: handler.request.headers.get(f), fields)):
            raise ValueError("Missing/Invalid WebSocket headers")

    @staticmethod
    def compute_accept_value(key: Union[str, bytes]) -> str:
        """Computes the value for the Sec-WebSocket-Accept header,
        given the value for Sec-WebSocket-Key.
        """
        sha1 = hashlib.sha1()
        sha1.update(utf8(key))
        sha1.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")  # Magic value
        return native_str(base64.b64encode(sha1.digest()))

    def _challenge_response(self, handler: WebSocketHandler) -> str:
        return WebSocketProtocol13.compute_accept_value(
            cast(str, handler.request.headers.get("Sec-Websocket-Key"))
        )

    async def _accept_connection(self, handler: WebSocketHandler) -> None:
        subprotocol_header = handler.request.headers.get("Sec-WebSocket-Protocol")
        if subprotocol_header:
            subprotocols = [s.strip() for s in subprotocol_header.split(",")]
        else:
            subprotocols = []
        self.selected_subprotocol = handler.select_subprotocol(subprotocols)
        if self.selected_subprotocol:
            assert self.selected_subprotocol in subprotocols
            handler.set_header("Sec-WebSocket-Protocol", self.selected_subprotocol)

        extensions = self._parse_extensions_header(handler.request.headers)
        for ext in extensions:
            if ext[0] == "permessage-deflate" and self._compression_options is not None:
                # TODO: negotiate parameters if compression_options
                # specifies limits.
                self._create_compressors("server", ext[1], self._compression_options)
                if (
                    "client_max_window_bits" in ext[1]
                    and ext[1]["client_max_window_bits"] is None
                ):
                    # Don't echo an offered client_max_window_bits
                    # parameter with no value.
                    del ext[1]["client_max_window_bits"]
                handler.set_header(
                    "Sec-WebSocket-Extensions",
                    httputil._encode_header("permessage-deflate", ext[1]),
                )
                break

        handler.clear_header("Content-Type")
        handler.set_status(101)
        handler.set_header("Upgrade", "websocket")
        handler.set_header("Connection", "Upgrade")
        handler.set_header("Sec-WebSocket-Accept", self._challenge_response(handler))
        handler.finish()

        self.stream = handler._detach_stream()

        self.start_pinging()
        try:
            open_result = handler.open(*handler.open_args, **handler.open_kwargs)
            if open_result is not None:
                await open_result
        except Exception:
            handler.log_exception(*sys.exc_info())
            self._abort()
            return

        await self._receive_frame_loop()

    def _parse_extensions_header(
        self, headers: httputil.HTTPHeaders
    ) -> List[Tuple[str, Dict[str, str]]]:
        extensions = headers.get("Sec-WebSocket-Extensions", "")
        if extensions:
            return [httputil._parse_header(e.strip()) for e in extensions.split(",")]
        return []

    def _process_server_headers(
        self, key: Union[str, bytes], headers: httputil.HTTPHeaders
    ) -> None:
        """Process the headers sent by the server to this client connection.

        'key' is the websocket handshake challenge/response key.
        """
        assert headers["Upgrade"].lower() == "websocket"
        assert headers["Connection"].lower() == "upgrade"
        accept = self.compute_accept_value(key)
        assert headers["Sec-Websocket-Accept"] == accept

        extensions = self._parse_extensions_header(headers)
        for ext in extensions:
            if ext[0] == "permessage-deflate" and self._compression_options is not None:
                self._create_compressors("client", ext[1])
            else:
                raise ValueError("unsupported extension %r", ext)

        self.selected_subprotocol = headers.get("Sec-WebSocket-Protocol", None)

    def _get_compressor_options(
        self,
        side: str,
        agreed_parameters: Dict[str, Any],
        compression_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Converts a websocket agreed_parameters set to keyword arguments
        for our compressor objects.
        """
        options = dict(
            persistent=(side + "_no_context_takeover") not in agreed_parameters
        )  # type: Dict[str, Any]
        wbits_header = agreed_parameters.get(side + "_max_window_bits", None)
        if wbits_header is None:
            options["max_wbits"] = zlib.MAX_WBITS
        else:
            options["max_wbits"] = int(wbits_header)
        options["compression_options"] = compression_options
        return options

    def _create_compressors(
        self,
        side: str,
        agreed_parameters: Dict[str, Any],
        compression_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        # TODO: handle invalid parameters gracefully
        allowed_keys = {
            "server_no_context_takeover",
            "client_no_context_takeover",
            "server_max_window_bits",
            "client_max_window_bits",
        }
        for key in agreed_parameters:
            if key not in allowed_keys:
                raise ValueError("unsupported compression parameter %r" % key)
        other_side = "client" if (side == "server") else "server"
        self._compressor = _PerMessageDeflateCompressor(
            **self._get_compressor_options(side, agreed_parameters, compression_options)
        )
        self._decompressor = _PerMessageDeflateDecompressor(
            max_message_size=self.params.max_message_size,
            **self._get_compressor_options(
                other_side, agreed_parameters, compression_options
            ),
        )

    def _write_frame(
        self, fin: bool, opcode: int, data: bytes, flags: int = 0
    ) -> "Future[None]":
        data_len = len(data)
        if opcode & 0x8:
            # All control frames MUST have a payload length of 125
            # bytes or less and MUST NOT be fragmented.
            if not fin:
                raise ValueError("control frames may not be fragmented")
            if data_len > 125:
                raise ValueError("control frame payloads may not exceed 125 bytes")
        if fin:
            finbit = self.FIN
        else:
            finbit = 0
        frame = struct.pack("B", finbit | opcode | flags)
        if self.mask_outgoing:
            mask_bit = 0x80
        else:
            mask_bit = 0
        if data_len < 126:
            frame += struct.pack("B", data_len | mask_bit)
        elif data_len <= 0xFFFF:
            frame += struct.pack("!BH", 126 | mask_bit, data_len)
        else:
            frame += struct.pack("!BQ", 127 | mask_bit, data_len)
        if self.mask_outgoing:
            mask = os.urandom(4)
            data = mask + _websocket_mask(mask, data)
        frame += data
        self._wire_bytes_out += len(frame)
        return self.stream.write(frame)

    def write_message(
        self, message: Union[str, bytes, Dict[str, Any]], binary: bool = False
    ) -> "Future[None]":
        """Sends the given message to the client of this Web Socket."""
        if binary:
            opcode = 0x2
        else:
            opcode = 0x1
        if isinstance(message, dict):
            message = tornado.escape.json_encode(message)
        message = tornado.escape.utf8(message)
        assert isinstance(message, bytes)
        self._message_bytes_out += len(message)
        flags = 0
        if self._compressor:
            message = self._compressor.compress(message)
            flags |= self.RSV1
        # For historical reasons, write methods in Tornado operate in a semi-synchronous
        # mode in which awaiting the Future they return is optional (But errors can
        # still be raised). This requires us to go through an awkward dance here
        # to transform the errors that may be returned while presenting the same
        # semi-synchronous interface.
        try:
            fut = self._write_frame(True, opcode, message, flags=flags)
        except StreamClosedError:
            raise WebSocketClosedError()

        async def wrapper() -> None:
            try:
                await fut
            except StreamClosedError:
                raise WebSocketClosedError()

        return asyncio.ensure_future(wrapper())

    def write_ping(self, data: bytes) -> None:
        """Send ping frame."""
        assert isinstance(data, bytes)
        self._write_frame(True, 0x9, data)

    async def _receive_frame_loop(self) -> None:
        try:
            while not self.client_terminated:
                await self._receive_frame()
        except StreamClosedError:
            self._abort()
        self.handler.on_ws_connection_close(self.close_code, self.close_reason)

    async def _read_bytes(self, n: int) -> bytes:
        data = await self.stream.read_bytes(n)
        self._wire_bytes_in += n
        return data

    async def _receive_frame(self) -> None:
        # Read the frame header.
        data = await self._read_bytes(2)
        header, mask_payloadlen = struct.unpack("BB", data)
        is_final_frame = header & self.FIN
        reserved_bits = header & self.RSV_MASK
        opcode = header & self.OPCODE_MASK
        opcode_is_control = opcode & 0x8
        if self._decompressor is not None and opcode != 0:
            # Compression flag is present in the first frame's header,
            # but we can't decompress until we have all the frames of
            # the message.
            self._frame_compressed = bool(reserved_bits & self.RSV1)
            reserved_bits &= ~self.RSV1
        if reserved_bits:
            # client is using as-yet-undefined extensions; abort
            self._abort()
            return
        is_masked = bool(mask_payloadlen & 0x80)
        payloadlen = mask_payloadlen & 0x7F

        # Parse and validate the length.
        if opcode_is_control and payloadlen >= 126:
            # control frames must have payload < 126
            self._abort()
            return
        if payloadlen < 126:
            self._frame_length = payloadlen
        elif payloadlen == 126:
            data = await self._read_bytes(2)
            payloadlen = struct.unpack("!H", data)[0]
        elif payloadlen == 127:
            data = await self._read_bytes(8)
            payloadlen = struct.unpack("!Q", data)[0]
        new_len = payloadlen
        if self._fragmented_message_buffer is not None:
            new_len += len(self._fragmented_message_buffer)
        if new_len > self.params.max_message_size:
            self.close(1009, "message too big")
            self._abort()
            return

        # Read the payload, unmasking if necessary.
        if is_masked:
            self._frame_mask = await self._read_bytes(4)
        data = await self._read_bytes(payloadlen)
        if is_masked:
            assert self._frame_mask is not None
            data = _websocket_mask(self._frame_mask, data)

        # Decide what to do with this frame.
        if opcode_is_control:
            # control frames may be interleaved with a series of fragmented
            # data frames, so control frames must not interact with
            # self._fragmented_*
            if not is_final_frame:
                # control frames must not be fragmented
                self._abort()
                return
        elif opcode == 0:  # continuation frame
            if self._fragmented_message_buffer is None:
                # nothing to continue
                self._abort()
                return
            self._fragmented_message_buffer.extend(data)
            if is_final_frame:
                opcode = self._fragmented_message_opcode
                data = bytes(self._fragmented_message_buffer)
                self._fragmented_message_buffer = None
        else:  # start of new data message
            if self._fragmented_message_buffer is not None:
                # can't start new message until the old one is finished
                self._abort()
                return
            if not is_final_frame:
                self._fragmented_message_opcode = opcode
                self._fragmented_message_buffer = bytearray(data)

        if is_final_frame:
            handled_future = self._handle_message(opcode, data)
            if handled_future is not None:
                await handled_future

    def _handle_message(self, opcode: int, data: bytes) -> "Optional[Future[None]]":
        """Execute on_message, returning its Future if it is a coroutine."""
        if self.client_terminated:
            return None

        if self._frame_compressed:
            assert self._decompressor is not None
            try:
                data = self._decompressor.decompress(data)
            except _DecompressTooLargeError:
                self.close(1009, "message too big after decompression")
                self._abort()
                return None

        if opcode == 0x1:
            # UTF-8 data
            self._message_bytes_in += len(data)
            try:
                decoded = data.decode("utf-8")
            except UnicodeDecodeError:
                self._abort()
                return None
            return self._run_callback(self.handler.on_message, decoded)
        elif opcode == 0x2:
            # Binary data
            self._message_bytes_in += len(data)
            return self._run_callback(self.handler.on_message, data)
        elif opcode == 0x8:
            # Close
            self.client_terminated = True
            if len(data) >= 2:
                self.close_code = struct.unpack(">H", data[:2])[0]
            if len(data) > 2:
                self.close_reason = to_unicode(data[2:])
            # Echo the received close code, if any (RFC 6455 section 5.5.1).
            self.close(self.close_code)
        elif opcode == 0x9:
            # Ping
            try:
                self._write_frame(True, 0xA, data)
            except StreamClosedError:
                self._abort()
            self._run_callback(self.handler.on_ping, data)
        elif opcode == 0xA:
            # Pong
            self._received_pong = True
            return self._run_callback(self.handler.on_pong, data)
        else:
            self._abort()
        return None

    def close(self, code: Optional[int] = None, reason: Optional[str] = None) -> None:
        """Closes the WebSocket connection."""
        if not self.server_terminated:
            if not self.stream.closed():
                if code is None and reason is not None:
                    code = 1000  # "normal closure" status code
                if code is None:
                    close_data = b""
                else:
                    close_data = struct.pack(">H", code)
                if reason is not None:
                    close_data += utf8(reason)
                try:
                    self._write_frame(True, 0x8, close_data)
                except StreamClosedError:
                    self._abort()
            self.server_terminated = True
        if self.client_terminated:
            if self._waiting is not None:
                self.stream.io_loop.remove_timeout(self._waiting)
                self._waiting = None
            self.stream.close()
        elif self._waiting is None:
            # Give the client a few seconds to complete a clean shutdown,
            # otherwise just close the connection.
            self._waiting = self.stream.io_loop.add_timeout(
                self.stream.io_loop.time() + 5, self._abort
            )
        if self._ping_coroutine:
            self._ping_coroutine.cancel()
            self._ping_coroutine = None

    def is_closing(self) -> bool:
        """Return ``True`` if this connection is closing.

        The connection is considered closing if either side has
        initiated its closing handshake or if the stream has been
        shut down uncleanly.
        """
        return self.stream.closed() or self.client_terminated or self.server_terminated

    def set_nodelay(self, x: bool) -> None:
        self.stream.set_nodelay(x)

    @property
    def ping_interval(self) -> float:
        interval = self.params.ping_interval
        if interval is not None:
            return interval
        return 0

    @property
    def ping_timeout(self) -> float:
        timeout = self.params.ping_timeout
        if timeout is not None:
            if self.ping_interval and timeout > self.ping_interval:
                de_dupe_gen_log(
                    # Note: using de_dupe_gen_log to prevent this message from
                    # being duplicated for each connection
                    logging.WARNING,
                    f"The websocket_ping_timeout ({timeout}) cannot be longer"
                    f" than the websocket_ping_interval ({self.ping_interval})."
                    f"\nSetting websocket_ping_timeout={self.ping_interval}",
                )
                return self.ping_interval
            return timeout
        return self.ping_interval

    def start_pinging(self) -> None:
        """Start sending periodic pings to keep the connection alive"""
        if (
            # prevent multiple ping coroutines being run in parallel
            not self._ping_coroutine
            # only run the ping coroutine if a ping interval is configured
            and self.ping_interval > 0
        ):
            self._ping_coroutine = asyncio.create_task(self.periodic_ping())

    async def periodic_ping(self) -> None:
        """Send a ping and wait for a pong if ping_timeout is configured.

        Called periodically if the websocket_ping_interval is set and non-zero.
        """
        interval = self.ping_interval
        timeout = self.ping_timeout

        await asyncio.sleep(interval)

        while True:
            # send a ping
            self._received_pong = False
            ping_time = IOLoop.current().time()
            self.write_ping(b"")

            # wait until the ping timeout
            await asyncio.sleep(timeout)

            # make sure we received a pong within the timeout
            if timeout > 0 and not self._received_pong:
                self.close(reason="ping timed out")
                return

            # wait until the next scheduled ping
            await asyncio.sleep(IOLoop.current().time() - ping_time + interval)


class WebSocketClientConnection(simple_httpclient._HTTPConnection):
    """WebSocket client connection.

    This class should not be instantiated directly; use the
    `websocket_connect` function instead.
    """

    protocol = None  # type: WebSocketProtocol

    def __init__(
        self,
        request: httpclient.HTTPRequest,
        on_message_callback: Optional[Callable[[Union[None, str, bytes]], None]] = None,
        compression_options: Optional[Dict[str, Any]] = None,
        ping_interval: Optional[float] = None,
        ping_timeout: Optional[float] = None,
        max_message_size: int = _default_max_message_size,
        subprotocols: Optional[List[str]] = None,
        resolver: Optional[Resolver] = None,
    ) -> None:
        self.connect_future = Future()  # type: Future[WebSocketClientConnection]
        self.read_queue = Queue(1)  # type: Queue[Union[None, str, bytes]]
        self.key = base64.b64encode(os.urandom(16))
        self._on_message_callback = on_message_callback
        self.close_code = None  # type: Optional[int]
        self.close_reason = None  # type: Optional[str]
        self.params = _WebSocketParams(
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
            max_message_size=max_message_size,
            compression_options=compression_options,
        )

        scheme, sep, rest = request.url.partition(":")
        scheme = {"ws": "http", "wss": "https"}[scheme]
        request.url = scheme + sep + rest
        request.headers.update(
            {
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Sec-WebSocket-Key": to_unicode(self.key),
                "Sec-WebSocket-Version": "13",
            }
        )
        if subprotocols is not None:
            request.headers["Sec-WebSocket-Protocol"] = ",".join(subprotocols)
        if compression_options is not None:
            # Always offer to let the server set our max_wbits (and even though
            # we don't offer it, we will accept a client_no_context_takeover
            # from the server).
            # TODO: set server parameters for deflate extension
            # if requested in self.compression_options.
            request.headers["Sec-WebSocket-Extensions"] = (
                "permessage-deflate; client_max_window_bits"
            )

        # Websocket connection is currently unable to follow redirects
        request.follow_redirects = False

        self.tcp_client = TCPClient(resolver=resolver)
        super().__init__(
            None,
            request,
            lambda: None,
            self._on_http_response,
            104857600,
            self.tcp_client,
            65536,
            104857600,
        )

    def __del__(self) -> None:
        if self.protocol is not None:
            # Unclosed client connections can sometimes log "task was destroyed but
            # was pending" warnings if shutdown strikes at the wrong time (such as
            # while a ping is being processed due to ping_interval). Log our own
            # warning to make it a little more deterministic (although it's still
            # dependent on GC timing).
            warnings.warn("Unclosed WebSocketClientConnection", ResourceWarning)

    def close(self, code: Optional[int] = None, reason: Optional[str] = None) -> None:
        """Closes the websocket connection.

        ``code`` and ``reason`` are documented under
        `WebSocketHandler.close`.

        .. versionadded:: 3.2

        .. versionchanged:: 4.0

           Added the ``code`` and ``reason`` arguments.
        """
        if self.protocol is not None:
            self.protocol.close(code, reason)
            self.protocol = None  # type: ignore

    def on_connection_close(self) -> None:
        if not self.connect_future.done():
            self.connect_future.set_exception(StreamClosedError())
        self._on_message(None)
        self.tcp_client.close()
        super().on_connection_close()

    def on_ws_connection_close(
        self, close_code: Optional[int] = None, close_reason: Optional[str] = None
    ) -> None:
        self.close_code = close_code
        self.close_reason = close_reason
        self.on_connection_close()

    def _on_http_response(self, response: httpclient.HTTPResponse) -> None:
        if not self.connect_future.done():
            if response.error:
                self.connect_future.set_exception(response.error)
            else:
                self.connect_future.set_exception(
                    WebSocketError("Non-websocket response")
                )

    async def headers_received(
        self,
        start_line: Union[httputil.RequestStartLine, httputil.ResponseStartLine],
        headers: httputil.HTTPHeaders,
    ) -> None:
        assert isinstance(start_line, httputil.ResponseStartLine)
        if start_line.code != 101:
            await super().headers_received(start_line, headers)
            return

        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
            self._timeout = None

        self.headers = headers
        self.protocol = self.get_websocket_protocol()
        self.protocol._process_server_headers(self.key, self.headers)
        self.protocol.stream = self.connection.detach()

        IOLoop.current().add_callback(self.protocol._receive_frame_loop)
        self.protocol.start_pinging()

        # Once we've taken over the connection, clear the final callback
        # we set on the http request.  This deactivates the error handling
        # in simple_httpclient that would otherwise interfere with our
        # ability to see exceptions.
        self.final_callback = None  # type: ignore

        future_set_result_unless_cancelled(self.connect_future, self)

    def write_message(
        self, message: Union[str, bytes, Dict[str, Any]], binary: bool = False
    ) -> "Future[None]":
        """Sends a message to the WebSocket server.

        If the stream is closed, raises `WebSocketClosedError`.
        Returns a `.Future` which can be used for flow control.

        .. versionchanged:: 5.0
           Exception raised on a closed stream changed from `.StreamClosedError`
           to `WebSocketClosedError`.
        """
        if self.protocol is None:
            raise WebSocketClosedError("Client connection has been closed")
        return self.protocol.write_message(message, binary=binary)

    def read_message(
        self,
        callback: Optional[Callable[["Future[Union[None, str, bytes]]"], None]] = None,
    ) -> Awaitable[Union[None, str, bytes]]:
        """Reads a message from the WebSocket server.

        If on_message_callback was specified at WebSocket
        initialization, this function will never return messages

        Returns a future whose result is the message, or None
        if the connection is closed.  If a callback argument
        is given it will be called with the future when it is
        ready.
        """

        awaitable = self.read_queue.get()
        if callback is not None:
            self.io_loop.add_future(asyncio.ensure_future(awaitable), callback)
        return awaitable

    def on_message(self, message: Union[str, bytes]) -> Optional[Awaitable[None]]:
        return self._on_message(message)

    def _on_message(
        self, message: Union[None, str, bytes]
    ) -> Optional[Awaitable[None]]:
        if self._on_message_callback:
            self._on_message_callback(message)
            return None
        else:
            return self.read_queue.put(message)

    def ping(self, data: bytes = b"") -> None:
        """Send ping frame to the remote end.

        The data argument allows a small amount of data (up to 125
        bytes) to be sent as a part of the ping message. Note that not
        all websocket implementations expose this data to
        applications.

        Consider using the ``ping_interval`` argument to
        `websocket_connect` instead of sending pings manually.

        .. versionadded:: 5.1

        """
        data = utf8(data)
        if self.protocol is None:
            raise WebSocketClosedError()
        self.protocol.write_ping(data)

    def on_pong(self, data: bytes) -> None:
        pass

    def on_ping(self, data: bytes) -> None:
        pass

    def get_websocket_protocol(self) -> WebSocketProtocol:
        return WebSocketProtocol13(self, mask_outgoing=True, params=self.params)

    @property
    def selected_subprotocol(self) -> Optional[str]:
        """The subprotocol selected by the server.

        .. versionadded:: 5.1
        """
        return self.protocol.selected_subprotocol

    def log_exception(
        self,
        typ: "Optional[Type[BaseException]]",
        value: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        assert typ is not None
        assert value is not None
        app_log.error("Uncaught exception %s", value, exc_info=(typ, value, tb))


def websocket_connect(
    url: Union[str, httpclient.HTTPRequest],
    callback: Optional[Callable[["Future[WebSocketClientConnection]"], None]] = None,
    connect_timeout: Optional[float] = None,
    on_message_callback: Optional[Callable[[Union[None, str, bytes]], None]] = None,
    compression_options: Optional[Dict[str, Any]] = None,
    ping_interval: Optional[float] = None,
    ping_timeout: Optional[float] = None,
    max_message_size: int = _default_max_message_size,
    subprotocols: Optional[List[str]] = None,
    resolver: Optional[Resolver] = None,
) -> "Awaitable[WebSocketClientConnection]":
    """Client-side websocket support.

    Takes a url and returns a Future whose result is a
    `WebSocketClientConnection`.

    ``compression_options`` is interpreted in the same way as the
    return value of `.WebSocketHandler.get_compression_options`.

    The connection supports two styles of operation. In the coroutine
    style, the application typically calls
    `~.WebSocketClientConnection.read_message` in a loop::

        conn = yield websocket_connect(url)
        while True:
            msg = yield conn.read_message()
            if msg is None: break
            # Do something with msg

    In the callback style, pass an ``on_message_callback`` to
    ``websocket_connect``. In both styles, a message of ``None``
    indicates that the connection has been closed.

    ``subprotocols`` may be a list of strings specifying proposed
    subprotocols. The selected protocol may be found on the
    ``selected_subprotocol`` attribute of the connection object
    when the connection is complete.

    .. versionchanged:: 3.2
       Also accepts ``HTTPRequest`` objects in place of urls.

    .. versionchanged:: 4.1
       Added ``compression_options`` and ``on_message_callback``.

    .. versionchanged:: 4.5
       Added the ``ping_interval``, ``ping_timeout``, and ``max_message_size``
       arguments, which have the same meaning as in `WebSocketHandler`.

    .. versionchanged:: 5.0
       The ``io_loop`` argument (deprecated since version 4.1) has been removed.

    .. versionchanged:: 5.1
       Added the ``subprotocols`` argument.

    .. versionchanged:: 6.3
       Added the ``resolver`` argument.

    .. deprecated:: 6.5
       The ``callback`` argument is deprecated and will be removed in Tornado 7.0.
       Use the returned Future instead. Note that ``on_message_callback`` is not
       deprecated and may still be used.
    """
    if isinstance(url, httpclient.HTTPRequest):
        assert connect_timeout is None
        request = url
        # Copy and convert the headers dict/object (see comments in
        # AsyncHTTPClient.fetch)
        request.headers = httputil.HTTPHeaders(request.headers)
    else:
        request = httpclient.HTTPRequest(url, connect_timeout=connect_timeout)
    request = cast(
        httpclient.HTTPRequest,
        httpclient._RequestProxy(request, httpclient.HTTPRequest._DEFAULTS),
    )
    conn = WebSocketClientConnection(
        request,
        on_message_callback=on_message_callback,
        compression_options=compression_options,
        ping_interval=ping_interval,
        ping_timeout=ping_timeout,
        max_message_size=max_message_size,
        subprotocols=subprotocols,
        resolver=resolver,
    )
    if callback is not None:
        warnings.warn(
            "The callback argument to websocket_connect is deprecated. "
            "Use the returned Future instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        IOLoop.current().add_future(conn.connect_future, callback)
    return conn.connect_future

# === NexusCore/openenv\Lib\site-packages\nltk\grammar.py ===
# Natural Language Toolkit: Context Free Grammars
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
#         Jason Narad <jason.narad@gmail.com>
#         Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
#         Tom Aarsen <>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Basic data classes for representing context free grammars.  A
"grammar" specifies which trees can represent the structure of a
given text.  Each of these trees is called a "parse tree" for the
text (or simply a "parse").  In a "context free" grammar, the set of
parse trees for any piece of a text can depend only on that piece, and
not on the rest of the text (i.e., the piece's context).  Context free
grammars are often used to find possible syntactic structures for
sentences.  In this context, the leaves of a parse tree are word
tokens; and the node values are phrasal categories, such as ``NP``
and ``VP``.

The ``CFG`` class is used to encode context free grammars.  Each
``CFG`` consists of a start symbol and a set of productions.
The "start symbol" specifies the root node value for parse trees.  For example,
the start symbol for syntactic parsing is usually ``S``.  Start
symbols are encoded using the ``Nonterminal`` class, which is discussed
below.

A Grammar's "productions" specify what parent-child relationships a parse
tree can contain.  Each production specifies that a particular
node can be the parent of a particular set of children.  For example,
the production ``<S> -> <NP> <VP>`` specifies that an ``S`` node can
be the parent of an ``NP`` node and a ``VP`` node.

Grammar productions are implemented by the ``Production`` class.
Each ``Production`` consists of a left hand side and a right hand
side.  The "left hand side" is a ``Nonterminal`` that specifies the
node type for a potential parent; and the "right hand side" is a list
that specifies allowable children for that parent.  This lists
consists of ``Nonterminals`` and text types: each ``Nonterminal``
indicates that the corresponding child may be a ``TreeToken`` with the
specified node type; and each text type indicates that the
corresponding child may be a ``Token`` with the with that type.

The ``Nonterminal`` class is used to distinguish node values from leaf
values.  This prevents the grammar from accidentally using a leaf
value (such as the English word "A") as the node of a subtree.  Within
a ``CFG``, all node values are wrapped in the ``Nonterminal``
class. Note, however, that the trees that are specified by the grammar do
*not* include these ``Nonterminal`` wrappers.

Grammars can also be given a more procedural interpretation.  According to
this interpretation, a Grammar specifies any tree structure *tree* that
can be produced by the following procedure:

| Set tree to the start symbol
| Repeat until tree contains no more nonterminal leaves:
|   Choose a production prod with whose left hand side
|     lhs is a nonterminal leaf of tree.
|   Replace the nonterminal leaf with a subtree, whose node
|     value is the value wrapped by the nonterminal lhs, and
|     whose children are the right hand side of prod.

The operation of replacing the left hand side (*lhs*) of a production
with the right hand side (*rhs*) in a tree (*tree*) is known as
"expanding" *lhs* to *rhs* in *tree*.
"""
import re
from collections import deque
from functools import total_ordering

from nltk.featstruct import SLASH, TYPE, FeatDict, FeatStruct, FeatStructReader
from nltk.internals import raise_unorderable_types
from nltk.probability import ImmutableProbabilisticMixIn
from nltk.util import invert_graph, transitive_closure

#################################################################
# Nonterminal
#################################################################


@total_ordering
class Nonterminal:
    """
    A non-terminal symbol for a context free grammar.  ``Nonterminal``
    is a wrapper class for node values; it is used by ``Production``
    objects to distinguish node values from leaf values.
    The node value that is wrapped by a ``Nonterminal`` is known as its
    "symbol".  Symbols are typically strings representing phrasal
    categories (such as ``"NP"`` or ``"VP"``).  However, more complex
    symbol types are sometimes used (e.g., for lexicalized grammars).
    Since symbols are node values, they must be immutable and
    hashable.  Two ``Nonterminals`` are considered equal if their
    symbols are equal.

    :see: ``CFG``, ``Production``
    :type _symbol: any
    :ivar _symbol: The node value corresponding to this
        ``Nonterminal``.  This value must be immutable and hashable.
    """

    def __init__(self, symbol):
        """
        Construct a new non-terminal from the given symbol.

        :type symbol: any
        :param symbol: The node value corresponding to this
            ``Nonterminal``.  This value must be immutable and
            hashable.
        """
        self._symbol = symbol

    def symbol(self):
        """
        Return the node value corresponding to this ``Nonterminal``.

        :rtype: (any)
        """
        return self._symbol

    def __eq__(self, other):
        """
        Return True if this non-terminal is equal to ``other``.  In
        particular, return True if ``other`` is a ``Nonterminal``
        and this non-terminal's symbol is equal to ``other`` 's symbol.

        :rtype: bool
        """
        return type(self) == type(other) and self._symbol == other._symbol

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, Nonterminal):
            raise_unorderable_types("<", self, other)
        return self._symbol < other._symbol

    def __hash__(self):
        return hash(self._symbol)

    def __repr__(self):
        """
        Return a string representation for this ``Nonterminal``.

        :rtype: str
        """
        if isinstance(self._symbol, str):
            return "%s" % self._symbol
        else:
            return "%s" % repr(self._symbol)

    def __str__(self):
        """
        Return a string representation for this ``Nonterminal``.

        :rtype: str
        """
        if isinstance(self._symbol, str):
            return "%s" % self._symbol
        else:
            return "%s" % repr(self._symbol)

    def __div__(self, rhs):
        """
        Return a new nonterminal whose symbol is ``A/B``, where ``A`` is
        the symbol for this nonterminal, and ``B`` is the symbol for rhs.

        :param rhs: The nonterminal used to form the right hand side
            of the new nonterminal.
        :type rhs: Nonterminal
        :rtype: Nonterminal
        """
        return Nonterminal(f"{self._symbol}/{rhs._symbol}")

    def __truediv__(self, rhs):
        """
        Return a new nonterminal whose symbol is ``A/B``, where ``A`` is
        the symbol for this nonterminal, and ``B`` is the symbol for rhs.
        This function allows use of the slash ``/`` operator with
        the future import of division.

        :param rhs: The nonterminal used to form the right hand side
            of the new nonterminal.
        :type rhs: Nonterminal
        :rtype: Nonterminal
        """
        return self.__div__(rhs)


def nonterminals(symbols):
    """
    Given a string containing a list of symbol names, return a list of
    ``Nonterminals`` constructed from those symbols.

    :param symbols: The symbol name string.  This string can be
        delimited by either spaces or commas.
    :type symbols: str
    :return: A list of ``Nonterminals`` constructed from the symbol
        names given in ``symbols``.  The ``Nonterminals`` are sorted
        in the same order as the symbols names.
    :rtype: list(Nonterminal)
    """
    if "," in symbols:
        symbol_list = symbols.split(",")
    else:
        symbol_list = symbols.split()
    return [Nonterminal(s.strip()) for s in symbol_list]


class FeatStructNonterminal(FeatDict, Nonterminal):
    """A feature structure that's also a nonterminal.  It acts as its
    own symbol, and automatically freezes itself when hashed."""

    def __hash__(self):
        self.freeze()
        return FeatStruct.__hash__(self)

    def symbol(self):
        return self


def is_nonterminal(item):
    """
    :return: True if the item is a ``Nonterminal``.
    :rtype: bool
    """
    return isinstance(item, Nonterminal)


#################################################################
# Terminals
#################################################################


def is_terminal(item):
    """
    Return True if the item is a terminal, which currently is
    if it is hashable and not a ``Nonterminal``.

    :rtype: bool
    """
    return hasattr(item, "__hash__") and not isinstance(item, Nonterminal)


#################################################################
# Productions
#################################################################


@total_ordering
class Production:
    """
    A grammar production.  Each production maps a single symbol
    on the "left-hand side" to a sequence of symbols on the
    "right-hand side".  (In the case of context-free productions,
    the left-hand side must be a ``Nonterminal``, and the right-hand
    side is a sequence of terminals and ``Nonterminals``.)
    "terminals" can be any immutable hashable object that is
    not a ``Nonterminal``.  Typically, terminals are strings
    representing words, such as ``"dog"`` or ``"under"``.

    :see: ``CFG``
    :see: ``DependencyGrammar``
    :see: ``Nonterminal``
    :type _lhs: Nonterminal
    :ivar _lhs: The left-hand side of the production.
    :type _rhs: tuple(Nonterminal, terminal)
    :ivar _rhs: The right-hand side of the production.
    """

    def __init__(self, lhs, rhs):
        """
        Construct a new ``Production``.

        :param lhs: The left-hand side of the new ``Production``.
        :type lhs: Nonterminal
        :param rhs: The right-hand side of the new ``Production``.
        :type rhs: sequence(Nonterminal and terminal)
        """
        if isinstance(rhs, str):
            raise TypeError(
                "production right hand side should be a list, " "not a string"
            )
        self._lhs = lhs
        self._rhs = tuple(rhs)

    def lhs(self):
        """
        Return the left-hand side of this ``Production``.

        :rtype: Nonterminal
        """
        return self._lhs

    def rhs(self):
        """
        Return the right-hand side of this ``Production``.

        :rtype: sequence(Nonterminal and terminal)
        """
        return self._rhs

    def __len__(self):
        """
        Return the length of the right-hand side.

        :rtype: int
        """
        return len(self._rhs)

    def is_nonlexical(self):
        """
        Return True if the right-hand side only contains ``Nonterminals``

        :rtype: bool
        """
        return all(is_nonterminal(n) for n in self._rhs)

    def is_lexical(self):
        """
        Return True if the right-hand contain at least one terminal token.

        :rtype: bool
        """
        return not self.is_nonlexical()

    def __str__(self):
        """
        Return a verbose string representation of the ``Production``.

        :rtype: str
        """
        result = "%s -> " % repr(self._lhs)
        result += " ".join(repr(el) for el in self._rhs)
        return result

    def __repr__(self):
        """
        Return a concise string representation of the ``Production``.

        :rtype: str
        """
        return "%s" % self

    def __eq__(self, other):
        """
        Return True if this ``Production`` is equal to ``other``.

        :rtype: bool
        """
        return (
            type(self) == type(other)
            and self._lhs == other._lhs
            and self._rhs == other._rhs
        )

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, Production):
            raise_unorderable_types("<", self, other)
        return (self._lhs, self._rhs) < (other._lhs, other._rhs)

    def __hash__(self):
        """
        Return a hash value for the ``Production``.

        :rtype: int
        """
        return hash((self._lhs, self._rhs))


class DependencyProduction(Production):
    """
    A dependency grammar production.  Each production maps a single
    head word to an unordered list of one or more modifier words.
    """

    def __str__(self):
        """
        Return a verbose string representation of the ``DependencyProduction``.

        :rtype: str
        """
        result = f"'{self._lhs}' ->"
        for elt in self._rhs:
            result += f" '{elt}'"
        return result


class ProbabilisticProduction(Production, ImmutableProbabilisticMixIn):
    """
    A probabilistic context free grammar production.
    A PCFG ``ProbabilisticProduction`` is essentially just a ``Production`` that
    has an associated probability, which represents how likely it is that
    this production will be used.  In particular, the probability of a
    ``ProbabilisticProduction`` records the likelihood that its right-hand side is
    the correct instantiation for any given occurrence of its left-hand side.

    :see: ``Production``
    """

    def __init__(self, lhs, rhs, **prob):
        """
        Construct a new ``ProbabilisticProduction``.

        :param lhs: The left-hand side of the new ``ProbabilisticProduction``.
        :type lhs: Nonterminal
        :param rhs: The right-hand side of the new ``ProbabilisticProduction``.
        :type rhs: sequence(Nonterminal and terminal)
        :param prob: Probability parameters of the new ``ProbabilisticProduction``.
        """
        ImmutableProbabilisticMixIn.__init__(self, **prob)
        Production.__init__(self, lhs, rhs)

    def __str__(self):
        return super().__str__() + (
            " [1.0]" if (self.prob() == 1.0) else " [%g]" % self.prob()
        )

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self._lhs == other._lhs
            and self._rhs == other._rhs
            and self.prob() == other.prob()
        )

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self._lhs, self._rhs, self.prob()))


#################################################################
# Grammars
#################################################################


class CFG:
    """
    A context-free grammar.  A grammar consists of a start state and
    a set of productions.  The set of terminals and nonterminals is
    implicitly specified by the productions.

    If you need efficient key-based access to productions, you
    can use a subclass to implement it.
    """

    def __init__(self, start, productions, calculate_leftcorners=True):
        """
        Create a new context-free grammar, from the given start state
        and set of ``Production`` instances.

        :param start: The start symbol
        :type start: Nonterminal
        :param productions: The list of productions that defines the grammar
        :type productions: list(Production)
        :param calculate_leftcorners: False if we don't want to calculate the
            leftcorner relation. In that case, some optimized chart parsers won't work.
        :type calculate_leftcorners: bool
        """
        if not is_nonterminal(start):
            raise TypeError(
                "start should be a Nonterminal object,"
                " not a %s" % type(start).__name__
            )

        self._start = start
        self._productions = productions
        self._categories = {prod.lhs() for prod in productions}
        self._calculate_indexes()
        self._calculate_grammar_forms()
        if calculate_leftcorners:
            self._calculate_leftcorners()

    def _calculate_indexes(self):
        self._lhs_index = {}
        self._rhs_index = {}
        self._empty_index = {}
        self._lexical_index = {}
        for prod in self._productions:
            # Left hand side.
            lhs = prod._lhs
            if lhs not in self._lhs_index:
                self._lhs_index[lhs] = []
            self._lhs_index[lhs].append(prod)
            if prod._rhs:
                # First item in right hand side.
                rhs0 = prod._rhs[0]
                if rhs0 not in self._rhs_index:
                    self._rhs_index[rhs0] = []
                self._rhs_index[rhs0].append(prod)
            else:
                # The right hand side is empty.
                self._empty_index[prod.lhs()] = prod
            # Lexical tokens in the right hand side.
            for token in prod._rhs:
                if is_terminal(token):
                    self._lexical_index.setdefault(token, set()).add(prod)

    def _calculate_leftcorners(self):
        # Calculate leftcorner relations, for use in optimized parsing.
        self._immediate_leftcorner_categories = {cat: {cat} for cat in self._categories}
        self._immediate_leftcorner_words = {cat: set() for cat in self._categories}
        for prod in self.productions():
            if len(prod) > 0:
                cat, left = prod.lhs(), prod.rhs()[0]
                if is_nonterminal(left):
                    self._immediate_leftcorner_categories[cat].add(left)
                else:
                    self._immediate_leftcorner_words[cat].add(left)

        lc = transitive_closure(self._immediate_leftcorner_categories, reflexive=True)
        self._leftcorners = lc
        self._leftcorner_parents = invert_graph(lc)

        nr_leftcorner_categories = sum(
            map(len, self._immediate_leftcorner_categories.values())
        )
        nr_leftcorner_words = sum(map(len, self._immediate_leftcorner_words.values()))
        if nr_leftcorner_words > nr_leftcorner_categories > 10000:
            # If the grammar is big, the leftcorner-word dictionary will be too large.
            # In that case it is better to calculate the relation on demand.
            self._leftcorner_words = None
            return

        self._leftcorner_words = {}
        for cat in self._leftcorners:
            lefts = self._leftcorners[cat]
            lc = self._leftcorner_words[cat] = set()
            for left in lefts:
                lc.update(self._immediate_leftcorner_words.get(left, set()))

    @classmethod
    def fromstring(cls, input, encoding=None):
        """
        Return the grammar instance corresponding to the input string(s).

        :param input: a grammar, either in the form of a string or as a list of strings.
        """
        start, productions = read_grammar(
            input, standard_nonterm_parser, encoding=encoding
        )
        return cls(start, productions)

    def start(self):
        """
        Return the start symbol of the grammar

        :rtype: Nonterminal
        """
        return self._start

    # tricky to balance readability and efficiency here!
    # can't use set operations as they don't preserve ordering
    def productions(self, lhs=None, rhs=None, empty=False):
        """
        Return the grammar productions, filtered by the left-hand side
        or the first item in the right-hand side.

        :param lhs: Only return productions with the given left-hand side.
        :param rhs: Only return productions with the given first item
            in the right-hand side.
        :param empty: Only return productions with an empty right-hand side.
        :return: A list of productions matching the given constraints.
        :rtype: list(Production)
        """
        if rhs and empty:
            raise ValueError(
                "You cannot select empty and non-empty " "productions at the same time."
            )

        # no constraints so return everything
        if not lhs and not rhs:
            if not empty:
                return self._productions
            else:
                return self._empty_index.values()

        # only lhs specified so look up its index
        elif lhs and not rhs:
            if not empty:
                return self._lhs_index.get(lhs, [])
            elif lhs in self._empty_index:
                return [self._empty_index[lhs]]
            else:
                return []

        # only rhs specified so look up its index
        elif rhs and not lhs:
            return self._rhs_index.get(rhs, [])

        # intersect
        else:
            return [
                prod
                for prod in self._lhs_index.get(lhs, [])
                if prod in self._rhs_index.get(rhs, [])
            ]

    def leftcorners(self, cat):
        """
        Return the set of all nonterminals that the given nonterminal
        can start with, including itself.

        This is the reflexive, transitive closure of the immediate
        leftcorner relation:  (A > B)  iff  (A -> B beta)

        :param cat: the parent of the leftcorners
        :type cat: Nonterminal
        :return: the set of all leftcorners
        :rtype: set(Nonterminal)
        """
        return self._leftcorners.get(cat, {cat})

    def is_leftcorner(self, cat, left):
        """
        True if left is a leftcorner of cat, where left can be a
        terminal or a nonterminal.

        :param cat: the parent of the leftcorner
        :type cat: Nonterminal
        :param left: the suggested leftcorner
        :type left: Terminal or Nonterminal
        :rtype: bool
        """
        if is_nonterminal(left):
            return left in self.leftcorners(cat)
        elif self._leftcorner_words:
            return left in self._leftcorner_words.get(cat, set())
        else:
            return any(
                left in self._immediate_leftcorner_words.get(parent, set())
                for parent in self.leftcorners(cat)
            )

    def leftcorner_parents(self, cat):
        """
        Return the set of all nonterminals for which the given category
        is a left corner. This is the inverse of the leftcorner relation.

        :param cat: the suggested leftcorner
        :type cat: Nonterminal
        :return: the set of all parents to the leftcorner
        :rtype: set(Nonterminal)
        """
        return self._leftcorner_parents.get(cat, {cat})

    def check_coverage(self, tokens):
        """
        Check whether the grammar rules cover the given list of tokens.
        If not, then raise an exception.

        :type tokens: list(str)
        """
        missing = [tok for tok in tokens if not self._lexical_index.get(tok)]
        if missing:
            missing = ", ".join(f"{w!r}" for w in missing)
            raise ValueError(
                "Grammar does not cover some of the " "input words: %r." % missing
            )

    def _calculate_grammar_forms(self):
        """
        Pre-calculate of which form(s) the grammar is.
        """
        prods = self._productions
        self._is_lexical = all(p.is_lexical() for p in prods)
        self._is_nonlexical = all(p.is_nonlexical() for p in prods if len(p) != 1)
        self._min_len = min(len(p) for p in prods)
        self._max_len = max(len(p) for p in prods)
        self._all_unary_are_lexical = all(p.is_lexical() for p in prods if len(p) == 1)

    def is_lexical(self):
        """
        Return True if all productions are lexicalised.
        """
        return self._is_lexical

    def is_nonlexical(self):
        """
        Return True if all lexical rules are "preterminals", that is,
        unary rules which can be separated in a preprocessing step.

        This means that all productions are of the forms
        A -> B1 ... Bn (n>=0), or A -> "s".

        Note: is_lexical() and is_nonlexical() are not opposites.
        There are grammars which are neither, and grammars which are both.
        """
        return self._is_nonlexical

    def min_len(self):
        """
        Return the right-hand side length of the shortest grammar production.
        """
        return self._min_len

    def max_len(self):
        """
        Return the right-hand side length of the longest grammar production.
        """
        return self._max_len

    def is_nonempty(self):
        """
        Return True if there are no empty productions.
        """
        return self._min_len > 0

    def is_binarised(self):
        """
        Return True if all productions are at most binary.
        Note that there can still be empty and unary productions.
        """
        return self._max_len <= 2

    def is_flexible_chomsky_normal_form(self):
        """
        Return True if all productions are of the forms
        A -> B C, A -> B, or A -> "s".
        """
        return self.is_nonempty() and self.is_nonlexical() and self.is_binarised()

    def is_chomsky_normal_form(self):
        """
        Return True if the grammar is of Chomsky Normal Form, i.e. all productions
        are of the form A -> B C, or A -> "s".
        """
        return self.is_flexible_chomsky_normal_form() and self._all_unary_are_lexical

    def chomsky_normal_form(self, new_token_padding="@$@", flexible=False):
        """
        Returns a new Grammar that is in chomsky normal

        :param: new_token_padding
            Customise new rule formation during binarisation
        """
        if self.is_chomsky_normal_form():
            return self
        if self.productions(empty=True):
            raise ValueError(
                "Grammar has Empty rules. " "Cannot deal with them at the moment"
            )

        # check for mixed rules
        for rule in self.productions():
            if rule.is_lexical() and len(rule.rhs()) > 1:
                raise ValueError(
                    f"Cannot handled mixed rule {rule.lhs()} => {rule.rhs()}"
                )

        step1 = CFG.eliminate_start(self)
        step2 = CFG.binarize(step1, new_token_padding)
        if flexible:
            return step2
        step3 = CFG.remove_unitary_rules(step2)
        step4 = CFG(step3.start(), list(set(step3.productions())))
        return step4

    @classmethod
    def remove_unitary_rules(cls, grammar):
        """
        Remove nonlexical unitary rules and convert them to
        lexical
        """
        result = []
        unitary = deque([])
        for rule in grammar.productions():
            if len(rule) == 1 and rule.is_nonlexical():
                unitary.append(rule)
            else:
                result.append(rule)

        while unitary:
            rule = unitary.popleft()
            for item in grammar.productions(lhs=rule.rhs()[0]):
                new_rule = Production(rule.lhs(), item.rhs())
                if len(new_rule) != 1 or new_rule.is_lexical():
                    result.append(new_rule)
                else:
                    unitary.append(new_rule)

        n_grammar = CFG(grammar.start(), result)
        return n_grammar

    @classmethod
    def binarize(cls, grammar, padding="@$@"):
        """
        Convert all non-binary rules into binary by introducing
        new tokens.
        Example::

            Original:
                A => B C D
            After Conversion:
                A => B A@$@B
                A@$@B => C D
        """
        result = []

        for rule in grammar.productions():
            if len(rule.rhs()) > 2:
                # this rule needs to be broken down
                left_side = rule.lhs()
                for k in range(0, len(rule.rhs()) - 2):
                    tsym = rule.rhs()[k]
                    new_sym = Nonterminal(left_side.symbol() + padding + tsym.symbol())
                    new_production = Production(left_side, (tsym, new_sym))
                    left_side = new_sym
                    result.append(new_production)
                last_prd = Production(left_side, rule.rhs()[-2:])
                result.append(last_prd)
            else:
                result.append(rule)

        n_grammar = CFG(grammar.start(), result)
        return n_grammar

    @classmethod
    def eliminate_start(cls, grammar):
        """
        Eliminate start rule in case it appears on RHS
        Example: S -> S0 S1 and S0 -> S1 S
        Then another rule S0_Sigma -> S is added
        """
        start = grammar.start()
        result = []
        need_to_add = None
        for rule in grammar.productions():
            if start in rule.rhs():
                need_to_add = True
            result.append(rule)
        if need_to_add:
            start = Nonterminal("S0_SIGMA")
            result.append(Production(start, [grammar.start()]))
            n_grammar = CFG(start, result)
            return n_grammar
        return grammar

    def __repr__(self):
        return "<Grammar with %d productions>" % len(self._productions)

    def __str__(self):
        result = "Grammar with %d productions" % len(self._productions)
        result += " (start state = %r)" % self._start
        for production in self._productions:
            result += "\n    %s" % production
        return result


class FeatureGrammar(CFG):
    """
    A feature-based grammar.  This is equivalent to a
    ``CFG`` whose nonterminals are all
    ``FeatStructNonterminal``.

    A grammar consists of a start state and a set of
    productions.  The set of terminals and nonterminals
    is implicitly specified by the productions.
    """

    def __init__(self, start, productions):
        """
        Create a new feature-based grammar, from the given start
        state and set of ``Productions``.

        :param start: The start symbol
        :type start: FeatStructNonterminal
        :param productions: The list of productions that defines the grammar
        :type productions: list(Production)
        """
        CFG.__init__(self, start, productions)

    # The difference with CFG is that the productions are
    # indexed on the TYPE feature of the nonterminals.
    # This is calculated by the method _get_type_if_possible().

    def _calculate_indexes(self):
        self._lhs_index = {}
        self._rhs_index = {}
        self._empty_index = {}
        self._empty_productions = []
        self._lexical_index = {}
        for prod in self._productions:
            # Left hand side.
            lhs = self._get_type_if_possible(prod._lhs)
            if lhs not in self._lhs_index:
                self._lhs_index[lhs] = []
            self._lhs_index[lhs].append(prod)
            if prod._rhs:
                # First item in right hand side.
                rhs0 = self._get_type_if_possible(prod._rhs[0])
                if rhs0 not in self._rhs_index:
                    self._rhs_index[rhs0] = []
                self._rhs_index[rhs0].append(prod)
            else:
                # The right hand side is empty.
                if lhs not in self._empty_index:
                    self._empty_index[lhs] = []
                self._empty_index[lhs].append(prod)
                self._empty_productions.append(prod)
            # Lexical tokens in the right hand side.
            for token in prod._rhs:
                if is_terminal(token):
                    self._lexical_index.setdefault(token, set()).add(prod)

    @classmethod
    def fromstring(
        cls, input, features=None, logic_parser=None, fstruct_reader=None, encoding=None
    ):
        """
        Return a feature structure based grammar.

        :param input: a grammar, either in the form of a string or else
        as a list of strings.
        :param features: a tuple of features (default: SLASH, TYPE)
        :param logic_parser: a parser for lambda-expressions,
        by default, ``LogicParser()``
        :param fstruct_reader: a feature structure parser
        (only if features and logic_parser is None)
        """
        if features is None:
            features = (SLASH, TYPE)

        if fstruct_reader is None:
            fstruct_reader = FeatStructReader(
                features, FeatStructNonterminal, logic_parser=logic_parser
            )
        elif logic_parser is not None:
            raise Exception(
                "'logic_parser' and 'fstruct_reader' must " "not both be set"
            )

        start, productions = read_grammar(
            input, fstruct_reader.read_partial, encoding=encoding
        )
        return cls(start, productions)

    def productions(self, lhs=None, rhs=None, empty=False):
        """
        Return the grammar productions, filtered by the left-hand side
        or the first item in the right-hand side.

        :param lhs: Only return productions with the given left-hand side.
        :param rhs: Only return productions with the given first item
            in the right-hand side.
        :param empty: Only return productions with an empty right-hand side.
        :rtype: list(Production)
        """
        if rhs and empty:
            raise ValueError(
                "You cannot select empty and non-empty " "productions at the same time."
            )

        # no constraints so return everything
        if not lhs and not rhs:
            if empty:
                return self._empty_productions
            else:
                return self._productions

        # only lhs specified so look up its index
        elif lhs and not rhs:
            if empty:
                return self._empty_index.get(self._get_type_if_possible(lhs), [])
            else:
                return self._lhs_index.get(self._get_type_if_possible(lhs), [])

        # only rhs specified so look up its index
        elif rhs and not lhs:
            return self._rhs_index.get(self._get_type_if_possible(rhs), [])

        # intersect
        else:
            return [
                prod
                for prod in self._lhs_index.get(self._get_type_if_possible(lhs), [])
                if prod in self._rhs_index.get(self._get_type_if_possible(rhs), [])
            ]

    def leftcorners(self, cat):
        """
        Return the set of all words that the given category can start with.
        Also called the "first set" in compiler construction.
        """
        raise NotImplementedError("Not implemented yet")

    def leftcorner_parents(self, cat):
        """
        Return the set of all categories for which the given category
        is a left corner.
        """
        raise NotImplementedError("Not implemented yet")

    def _get_type_if_possible(self, item):
        """
        Helper function which returns the ``TYPE`` feature of the ``item``,
        if it exists, otherwise it returns the ``item`` itself
        """
        if isinstance(item, dict) and TYPE in item:
            return FeatureValueType(item[TYPE])
        else:
            return item


@total_ordering
class FeatureValueType:
    """
    A helper class for ``FeatureGrammars``, designed to be different
    from ordinary strings.  This is to stop the ``FeatStruct``
    ``FOO[]`` from being compare equal to the terminal "FOO".
    """

    def __init__(self, value):
        self._value = value

    def __repr__(self):
        return "<%s>" % self._value

    def __eq__(self, other):
        return type(self) == type(other) and self._value == other._value

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, FeatureValueType):
            raise_unorderable_types("<", self, other)
        return self._value < other._value

    def __hash__(self):
        return hash(self._value)


class DependencyGrammar:
    """
    A dependency grammar.  A DependencyGrammar consists of a set of
    productions.  Each production specifies a head/modifier relationship
    between a pair of words.
    """

    def __init__(self, productions):
        """
        Create a new dependency grammar, from the set of ``Productions``.

        :param productions: The list of productions that defines the grammar
        :type productions: list(Production)
        """
        self._productions = productions

    @classmethod
    def fromstring(cls, input):
        productions = []
        for linenum, line in enumerate(input.split("\n")):
            line = line.strip()
            if line.startswith("#") or line == "":
                continue
            try:
                productions += _read_dependency_production(line)
            except ValueError as e:
                raise ValueError(f"Unable to parse line {linenum}: {line}") from e
        if len(productions) == 0:
            raise ValueError("No productions found!")
        return cls(productions)

    def contains(self, head, mod):
        """
        :param head: A head word.
        :type head: str
        :param mod: A mod word, to test as a modifier of 'head'.
        :type mod: str

        :return: true if this ``DependencyGrammar`` contains a
            ``DependencyProduction`` mapping 'head' to 'mod'.
        :rtype: bool
        """
        for production in self._productions:
            for possibleMod in production._rhs:
                if production._lhs == head and possibleMod == mod:
                    return True
        return False

    def __contains__(self, head_mod):
        """
        Return True if this ``DependencyGrammar`` contains a
        ``DependencyProduction`` mapping 'head' to 'mod'.

        :param head_mod: A tuple of a head word and a mod word,
            to test as a modifier of 'head'.
        :type head: Tuple[str, str]
        :rtype: bool
        """
        try:
            head, mod = head_mod
        except ValueError as e:
            raise ValueError(
                "Must use a tuple of strings, e.g. `('price', 'of') in grammar`"
            ) from e
        return self.contains(head, mod)

    #   # should be rewritten, the set comp won't work in all comparisons
    # def contains_exactly(self, head, modlist):
    #   for production in self._productions:
    #       if(len(production._rhs) == len(modlist)):
    #           if(production._lhs == head):
    #               set1 = Set(production._rhs)
    #               set2 = Set(modlist)
    #               if(set1 == set2):
    #                   return True
    #   return False

    def __str__(self):
        """
        Return a verbose string representation of the ``DependencyGrammar``

        :rtype: str
        """
        str = "Dependency grammar with %d productions" % len(self._productions)
        for production in self._productions:
            str += "\n  %s" % production
        return str

    def __repr__(self):
        """
        Return a concise string representation of the ``DependencyGrammar``
        """
        return "Dependency grammar with %d productions" % len(self._productions)


class ProbabilisticDependencyGrammar:
    """ """

    def __init__(self, productions, events, tags):
        self._productions = productions
        self._events = events
        self._tags = tags

    def contains(self, head, mod):
        """
        Return True if this ``DependencyGrammar`` contains a
        ``DependencyProduction`` mapping 'head' to 'mod'.

        :param head: A head word.
        :type head: str
        :param mod: A mod word, to test as a modifier of 'head'.
        :type mod: str
        :rtype: bool
        """
        for production in self._productions:
            for possibleMod in production._rhs:
                if production._lhs == head and possibleMod == mod:
                    return True
        return False

    def __str__(self):
        """
        Return a verbose string representation of the ``ProbabilisticDependencyGrammar``

        :rtype: str
        """
        str = "Statistical dependency grammar with %d productions" % len(
            self._productions
        )
        for production in self._productions:
            str += "\n  %s" % production
        str += "\nEvents:"
        for event in self._events:
            str += "\n  %d:%s" % (self._events[event], event)
        str += "\nTags:"
        for tag_word in self._tags:
            str += f"\n {tag_word}:\t({self._tags[tag_word]})"
        return str

    def __repr__(self):
        """
        Return a concise string representation of the ``ProbabilisticDependencyGrammar``
        """
        return "Statistical Dependency grammar with %d productions" % len(
            self._productions
        )


class PCFG(CFG):
    """
    A probabilistic context-free grammar.  A PCFG consists of a
    start state and a set of productions with probabilities.  The set of
    terminals and nonterminals is implicitly specified by the productions.

    PCFG productions use the ``ProbabilisticProduction`` class.
    ``PCFGs`` impose the constraint that the set of productions with
    any given left-hand-side must have probabilities that sum to 1
    (allowing for a small margin of error).

    If you need efficient key-based access to productions, you can use
    a subclass to implement it.

    :type EPSILON: float
    :cvar EPSILON: The acceptable margin of error for checking that
        productions with a given left-hand side have probabilities
        that sum to 1.
    """

    EPSILON = 0.01

    def __init__(self, start, productions, calculate_leftcorners=True):
        """
        Create a new context-free grammar, from the given start state
        and set of ``ProbabilisticProductions``.

        :param start: The start symbol
        :type start: Nonterminal
        :param productions: The list of productions that defines the grammar
        :type productions: list(Production)
        :raise ValueError: if the set of productions with any left-hand-side
            do not have probabilities that sum to a value within
            EPSILON of 1.
        :param calculate_leftcorners: False if we don't want to calculate the
            leftcorner relation. In that case, some optimized chart parsers won't work.
        :type calculate_leftcorners: bool
        """
        CFG.__init__(self, start, productions, calculate_leftcorners)

        # Make sure that the probabilities sum to one.
        probs = {}
        for production in productions:
            probs[production.lhs()] = probs.get(production.lhs(), 0) + production.prob()
        for lhs, p in probs.items():
            if not ((1 - PCFG.EPSILON) < p < (1 + PCFG.EPSILON)):
                raise ValueError("Productions for %r do not sum to 1" % lhs)

    @classmethod
    def fromstring(cls, input, encoding=None):
        """
        Return a probabilistic context-free grammar corresponding to the
        input string(s).

        :param input: a grammar, either in the form of a string or else
             as a list of strings.
        """
        start, productions = read_grammar(
            input, standard_nonterm_parser, probabilistic=True, encoding=encoding
        )
        return cls(start, productions)


#################################################################
# Inducing Grammars
#################################################################

# Contributed by Nathan Bodenstab <bodenstab@cslu.ogi.edu>


def induce_pcfg(start, productions):
    r"""
    Induce a PCFG grammar from a list of productions.

    The probability of a production A -> B C in a PCFG is:

    |                count(A -> B C)
    |  P(B, C | A) = ---------------       where \* is any right hand side
    |                 count(A -> \*)

    :param start: The start symbol
    :type start: Nonterminal
    :param productions: The list of productions that defines the grammar
    :type productions: list(Production)
    """
    # Production count: the number of times a given production occurs
    pcount = {}

    # LHS-count: counts the number of times a given lhs occurs
    lcount = {}

    for prod in productions:
        lcount[prod.lhs()] = lcount.get(prod.lhs(), 0) + 1
        pcount[prod] = pcount.get(prod, 0) + 1

    prods = [
        ProbabilisticProduction(p.lhs(), p.rhs(), prob=pcount[p] / lcount[p.lhs()])
        for p in pcount
    ]
    return PCFG(start, prods)


#################################################################
# Helper functions for reading productions
#################################################################


def _read_cfg_production(input):
    """
    Return a list of context-free ``Productions``.
    """
    return _read_production(input, standard_nonterm_parser)


def _read_pcfg_production(input):
    """
    Return a list of PCFG ``ProbabilisticProductions``.
    """
    return _read_production(input, standard_nonterm_parser, probabilistic=True)


def _read_fcfg_production(input, fstruct_reader):
    """
    Return a list of feature-based ``Productions``.
    """
    return _read_production(input, fstruct_reader)


# Parsing generic grammars

_ARROW_RE = re.compile(r"\s* -> \s*", re.VERBOSE)
_PROBABILITY_RE = re.compile(r"( \[ [\d\.]+ \] ) \s*", re.VERBOSE)
_TERMINAL_RE = re.compile(r'( "[^"]*" | \'[^\']*\' ) \s*', re.VERBOSE)
_DISJUNCTION_RE = re.compile(r"\| \s*", re.VERBOSE)


def _read_production(line, nonterm_parser, probabilistic=False):
    """
    Parse a grammar rule, given as a string, and return
    a list of productions.
    """
    pos = 0

    # Parse the left-hand side.
    lhs, pos = nonterm_parser(line, pos)

    # Skip over the arrow.
    m = _ARROW_RE.match(line, pos)
    if not m:
        raise ValueError("Expected an arrow")
    pos = m.end()

    # Parse the right hand side.
    probabilities = [0.0]
    rhsides = [[]]
    while pos < len(line):
        # Probability.
        m = _PROBABILITY_RE.match(line, pos)
        if probabilistic and m:
            pos = m.end()
            probabilities[-1] = float(m.group(1)[1:-1])
            if probabilities[-1] > 1.0:
                raise ValueError(
                    "Production probability %f, "
                    "should not be greater than 1.0" % (probabilities[-1],)
                )

        # String -- add terminal.
        elif line[pos] in "'\"":
            m = _TERMINAL_RE.match(line, pos)
            if not m:
                raise ValueError("Unterminated string")
            rhsides[-1].append(m.group(1)[1:-1])
            pos = m.end()

        # Vertical bar -- start new rhside.
        elif line[pos] == "|":
            m = _DISJUNCTION_RE.match(line, pos)
            probabilities.append(0.0)
            rhsides.append([])
            pos = m.end()

        # Anything else -- nonterminal.
        else:
            nonterm, pos = nonterm_parser(line, pos)
            rhsides[-1].append(nonterm)

    if probabilistic:
        return [
            ProbabilisticProduction(lhs, rhs, prob=probability)
            for (rhs, probability) in zip(rhsides, probabilities)
        ]
    else:
        return [Production(lhs, rhs) for rhs in rhsides]


#################################################################
# Reading Phrase Structure Grammars
#################################################################


def read_grammar(input, nonterm_parser, probabilistic=False, encoding=None):
    """
    Return a pair consisting of a starting category and a list of
    ``Productions``.

    :param input: a grammar, either in the form of a string or else
        as a list of strings.
    :param nonterm_parser: a function for parsing nonterminals.
        It should take a ``(string, position)`` as argument and
        return a ``(nonterminal, position)`` as result.
    :param probabilistic: are the grammar rules probabilistic?
    :type probabilistic: bool
    :param encoding: the encoding of the grammar, if it is a binary string
    :type encoding: str
    """
    if encoding is not None:
        input = input.decode(encoding)
    if isinstance(input, str):
        lines = input.split("\n")
    else:
        lines = input

    start = None
    productions = []
    continue_line = ""
    for linenum, line in enumerate(lines):
        line = continue_line + line.strip()
        if line.startswith("#") or line == "":
            continue
        if line.endswith("\\"):
            continue_line = line[:-1].rstrip() + " "
            continue
        continue_line = ""
        try:
            if line[0] == "%":
                directive, args = line[1:].split(None, 1)
                if directive == "start":
                    start, pos = nonterm_parser(args, 0)
                    if pos != len(args):
                        raise ValueError("Bad argument to start directive")
                else:
                    raise ValueError("Bad directive")
            else:
                # expand out the disjunctions on the RHS
                productions += _read_production(line, nonterm_parser, probabilistic)
        except ValueError as e:
            raise ValueError(f"Unable to parse line {linenum + 1}: {line}\n{e}") from e

    if not productions:
        raise ValueError("No productions found!")
    if not start:
        start = productions[0].lhs()
    return (start, productions)


_STANDARD_NONTERM_RE = re.compile(r"( [\w/][\w/^<>-]* ) \s*", re.VERBOSE)


def standard_nonterm_parser(string, pos):
    m = _STANDARD_NONTERM_RE.match(string, pos)
    if not m:
        raise ValueError("Expected a nonterminal, found: " + string[pos:])
    return (Nonterminal(m.group(1)), m.end())


#################################################################
# Reading Dependency Grammars
#################################################################

_READ_DG_RE = re.compile(
    r"""^\s*                # leading whitespace
                              ('[^']+')\s*        # single-quoted lhs
                              (?:[-=]+>)\s*        # arrow
                              (?:(                 # rhs:
                                   "[^"]+"         # doubled-quoted terminal
                                 | '[^']+'         # single-quoted terminal
                                 | \|              # disjunction
                                 )
                                 \s*)              # trailing space
                                 *$""",  # zero or more copies
    re.VERBOSE,
)
_SPLIT_DG_RE = re.compile(r"""('[^']'|[-=]+>|"[^"]+"|'[^']+'|\|)""")


def _read_dependency_production(s):
    if not _READ_DG_RE.match(s):
        raise ValueError("Bad production string")
    pieces = _SPLIT_DG_RE.split(s)
    pieces = [p for i, p in enumerate(pieces) if i % 2 == 1]
    lhside = pieces[0].strip("'\"")
    rhsides = [[]]
    for piece in pieces[2:]:
        if piece == "|":
            rhsides.append([])
        else:
            rhsides[-1].append(piece.strip("'\""))
    return [DependencyProduction(lhside, rhside) for rhside in rhsides]


#################################################################
# Demonstration
#################################################################


def cfg_demo():
    """
    A demonstration showing how ``CFGs`` can be created and used.
    """

    from nltk import CFG, Production, nonterminals

    # Create some nonterminals
    S, NP, VP, PP = nonterminals("S, NP, VP, PP")
    N, V, P, Det = nonterminals("N, V, P, Det")
    VP_slash_NP = VP / NP

    print("Some nonterminals:", [S, NP, VP, PP, N, V, P, Det, VP / NP])
    print("    S.symbol() =>", repr(S.symbol()))
    print()

    print(Production(S, [NP]))

    # Create some Grammar Productions
    grammar = CFG.fromstring(
        """
      S -> NP VP
      PP -> P NP
      NP -> Det N | NP PP
      VP -> V NP | VP PP
      Det -> 'a' | 'the'
      N -> 'dog' | 'cat'
      V -> 'chased' | 'sat'
      P -> 'on' | 'in'
    """
    )

    print("A Grammar:", repr(grammar))
    print("    grammar.start()       =>", repr(grammar.start()))
    print("    grammar.productions() =>", end=" ")
    # Use string.replace(...) is to line-wrap the output.
    print(repr(grammar.productions()).replace(",", ",\n" + " " * 25))
    print()


def pcfg_demo():
    """
    A demonstration showing how a ``PCFG`` can be created and used.
    """

    from nltk import induce_pcfg, treetransforms
    from nltk.corpus import treebank
    from nltk.parse import pchart

    toy_pcfg1 = PCFG.fromstring(
        """
        S -> NP VP [1.0]
        NP -> Det N [0.5] | NP PP [0.25] | 'John' [0.1] | 'I' [0.15]
        Det -> 'the' [0.8] | 'my' [0.2]
        N -> 'man' [0.5] | 'telescope' [0.5]
        VP -> VP PP [0.1] | V NP [0.7] | V [0.2]
        V -> 'ate' [0.35] | 'saw' [0.65]
        PP -> P NP [1.0]
        P -> 'with' [0.61] | 'under' [0.39]
        """
    )

    toy_pcfg2 = PCFG.fromstring(
        """
        S    -> NP VP         [1.0]
        VP   -> V NP          [.59]
        VP   -> V             [.40]
        VP   -> VP PP         [.01]
        NP   -> Det N         [.41]
        NP   -> Name          [.28]
        NP   -> NP PP         [.31]
        PP   -> P NP          [1.0]
        V    -> 'saw'         [.21]
        V    -> 'ate'         [.51]
        V    -> 'ran'         [.28]
        N    -> 'boy'         [.11]
        N    -> 'cookie'      [.12]
        N    -> 'table'       [.13]
        N    -> 'telescope'   [.14]
        N    -> 'hill'        [.5]
        Name -> 'Jack'        [.52]
        Name -> 'Bob'         [.48]
        P    -> 'with'        [.61]
        P    -> 'under'       [.39]
        Det  -> 'the'         [.41]
        Det  -> 'a'           [.31]
        Det  -> 'my'          [.28]
        """
    )

    pcfg_prods = toy_pcfg1.productions()

    pcfg_prod = pcfg_prods[2]
    print("A PCFG production:", repr(pcfg_prod))
    print("    pcfg_prod.lhs()  =>", repr(pcfg_prod.lhs()))
    print("    pcfg_prod.rhs()  =>", repr(pcfg_prod.rhs()))
    print("    pcfg_prod.prob() =>", repr(pcfg_prod.prob()))
    print()

    grammar = toy_pcfg2
    print("A PCFG grammar:", repr(grammar))
    print("    grammar.start()       =>", repr(grammar.start()))
    print("    grammar.productions() =>", end=" ")
    # Use .replace(...) is to line-wrap the output.
    print(repr(grammar.productions()).replace(",", ",\n" + " " * 26))
    print()

    # extract productions from three trees and induce the PCFG
    print("Induce PCFG grammar from treebank data:")

    productions = []
    item = treebank._fileids[0]
    for tree in treebank.parsed_sents(item)[:3]:
        # perform optional tree transformations, e.g.:
        tree.collapse_unary(collapsePOS=False)
        tree.chomsky_normal_form(horzMarkov=2)

        productions += tree.productions()

    S = Nonterminal("S")
    grammar = induce_pcfg(S, productions)
    print(grammar)
    print()

    print("Parse sentence using induced grammar:")

    parser = pchart.InsideChartParser(grammar)
    parser.trace(3)

    # doesn't work as tokens are different:
    # sent = treebank.tokenized('wsj_0001.mrg')[0]

    sent = treebank.parsed_sents(item)[0].leaves()
    print(sent)
    for parse in parser.parse(sent):
        print(parse)


def fcfg_demo():
    import nltk.data

    g = nltk.data.load("grammars/book_grammars/feat0.fcfg")
    print(g)
    print()


def dg_demo():
    """
    A demonstration showing the creation and inspection of a
    ``DependencyGrammar``.
    """
    grammar = DependencyGrammar.fromstring(
        """
    'scratch' -> 'cats' | 'walls'
    'walls' -> 'the'
    'cats' -> 'the'
    """
    )
    print(grammar)


def sdg_demo():
    """
    A demonstration of how to read a string representation of
    a CoNLL format dependency tree.
    """
    from nltk.parse import DependencyGraph

    dg = DependencyGraph(
        """
    1   Ze                ze                Pron  Pron  per|3|evofmv|nom                 2   su      _  _
    2   had               heb               V     V     trans|ovt|1of2of3|ev             0   ROOT    _  _
    3   met               met               Prep  Prep  voor                             8   mod     _  _
    4   haar              haar              Pron  Pron  bez|3|ev|neut|attr               5   det     _  _
    5   moeder            moeder            N     N     soort|ev|neut                    3   obj1    _  _
    6   kunnen            kan               V     V     hulp|ott|1of2of3|mv              2   vc      _  _
    7   gaan              ga                V     V     hulp|inf                         6   vc      _  _
    8   winkelen          winkel            V     V     intrans|inf                      11  cnj     _  _
    9   ,                 ,                 Punc  Punc  komma                            8   punct   _  _
    10  zwemmen           zwem              V     V     intrans|inf                      11  cnj     _  _
    11  of                of                Conj  Conj  neven                            7   vc      _  _
    12  terrassen         terras            N     N     soort|mv|neut                    11  cnj     _  _
    13  .                 .                 Punc  Punc  punt                             12  punct   _  _
    """
    )
    tree = dg.tree()
    print(tree.pprint())


def demo():
    cfg_demo()
    pcfg_demo()
    fcfg_demo()
    dg_demo()
    sdg_demo()


if __name__ == "__main__":
    demo()

__all__ = [
    "Nonterminal",
    "nonterminals",
    "CFG",
    "Production",
    "PCFG",
    "ProbabilisticProduction",
    "DependencyGrammar",
    "DependencyProduction",
    "ProbabilisticDependencyGrammar",
    "induce_pcfg",
    "read_grammar",
]

# === NexusCore/openenv\Lib\site-packages\matplotlib\contour.py ===
"""
Classes to support contour plotting and labelling for the Axes class.
"""

from contextlib import ExitStack
import functools
import math
from numbers import Integral

import numpy as np
from numpy import ma

import matplotlib as mpl
from matplotlib import _api, _docstring
from matplotlib.backend_bases import MouseButton
from matplotlib.lines import Line2D
from matplotlib.path import Path
from matplotlib.text import Text
import matplotlib.ticker as ticker
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.collections as mcoll
import matplotlib.font_manager as font_manager
import matplotlib.cbook as cbook
import matplotlib.patches as mpatches
import matplotlib.transforms as mtransforms


def _contour_labeler_event_handler(cs, inline, inline_spacing, event):
    canvas = cs.axes.get_figure(root=True).canvas
    is_button = event.name == "button_press_event"
    is_key = event.name == "key_press_event"
    # Quit (even if not in infinite mode; this is consistent with
    # MATLAB and sometimes quite useful, but will require the user to
    # test how many points were actually returned before using data).
    if (is_button and event.button == MouseButton.MIDDLE
            or is_key and event.key in ["escape", "enter"]):
        canvas.stop_event_loop()
    # Pop last click.
    elif (is_button and event.button == MouseButton.RIGHT
          or is_key and event.key in ["backspace", "delete"]):
        # Unfortunately, if one is doing inline labels, then there is currently
        # no way to fix the broken contour - once humpty-dumpty is broken, he
        # can't be put back together.  In inline mode, this does nothing.
        if not inline:
            cs.pop_label()
            canvas.draw()
    # Add new click.
    elif (is_button and event.button == MouseButton.LEFT
          # On macOS/gtk, some keys return None.
          or is_key and event.key is not None):
        if cs.axes.contains(event)[0]:
            cs.add_label_near(event.x, event.y, transform=False,
                              inline=inline, inline_spacing=inline_spacing)
            canvas.draw()


class ContourLabeler:
    """Mixin to provide labelling capability to `.ContourSet`."""

    def clabel(self, levels=None, *,
               fontsize=None, inline=True, inline_spacing=5, fmt=None,
               colors=None, use_clabeltext=False, manual=False,
               rightside_up=True, zorder=None):
        """
        Label a contour plot.

        Adds labels to line contours in this `.ContourSet` (which inherits from
        this mixin class).

        Parameters
        ----------
        levels : array-like, optional
            A list of level values, that should be labeled. The list must be
            a subset of ``cs.levels``. If not given, all levels are labeled.

        fontsize : str or float, default: :rc:`font.size`
            Size in points or relative size e.g., 'smaller', 'x-large'.
            See `.Text.set_size` for accepted string values.

        colors : :mpltype:`color` or colors or None, default: None
            The label colors:

            - If *None*, the color of each label matches the color of
              the corresponding contour.

            - If one string color, e.g., *colors* = 'r' or *colors* =
              'red', all labels will be plotted in this color.

            - If a tuple of colors (string, float, RGB, etc), different labels
              will be plotted in different colors in the order specified.

        inline : bool, default: True
            If ``True`` the underlying contour is removed where the label is
            placed.

        inline_spacing : float, default: 5
            Space in pixels to leave on each side of label when placing inline.

            This spacing will be exact for labels at locations where the
            contour is straight, less so for labels on curved contours.

        fmt : `.Formatter` or str or callable or dict, optional
            How the levels are formatted:

            - If a `.Formatter`, it is used to format all levels at once, using
              its `.Formatter.format_ticks` method.
            - If a str, it is interpreted as a %-style format string.
            - If a callable, it is called with one level at a time and should
              return the corresponding label.
            - If a dict, it should directly map levels to labels.

            The default is to use a standard `.ScalarFormatter`.

        manual : bool or iterable, default: False
            If ``True``, contour labels will be placed manually using
            mouse clicks. Click the first button near a contour to
            add a label, click the second button (or potentially both
            mouse buttons at once) to finish adding labels. The third
            button can be used to remove the last label added, but
            only if labels are not inline. Alternatively, the keyboard
            can be used to select label locations (enter to end label
            placement, delete or backspace act like the third mouse button,
            and any other key will select a label location).

            *manual* can also be an iterable object of (x, y) tuples.
            Contour labels will be created as if mouse is clicked at each
            (x, y) position.

        rightside_up : bool, default: True
            If ``True``, label rotations will always be plus
            or minus 90 degrees from level.

        use_clabeltext : bool, default: False
            If ``True``, use `.Text.set_transform_rotates_text` to ensure that
            label rotation is updated whenever the Axes aspect changes.

        zorder : float or None, default: ``(2 + contour.get_zorder())``
            zorder of the contour labels.

        Returns
        -------
        labels
            A list of `.Text` instances for the labels.
        """

        # Based on the input arguments, clabel() adds a list of "label
        # specific" attributes to the ContourSet object.  These attributes are
        # all of the form label* and names should be fairly self explanatory.
        #
        # Once these attributes are set, clabel passes control to the labels()
        # method (for automatic label placement) or blocking_input_loop and
        # _contour_labeler_event_handler (for manual label placement).

        if fmt is None:
            fmt = ticker.ScalarFormatter(useOffset=False)
            fmt.create_dummy_axis()
        self.labelFmt = fmt
        self._use_clabeltext = use_clabeltext
        self.labelManual = manual
        self.rightside_up = rightside_up
        self._clabel_zorder = 2 + self.get_zorder() if zorder is None else zorder

        if levels is None:
            levels = self.levels
            indices = list(range(len(self.cvalues)))
        else:
            levlabs = list(levels)
            indices, levels = [], []
            for i, lev in enumerate(self.levels):
                if lev in levlabs:
                    indices.append(i)
                    levels.append(lev)
            if len(levels) < len(levlabs):
                raise ValueError(f"Specified levels {levlabs} don't match "
                                 f"available levels {self.levels}")
        self.labelLevelList = levels
        self.labelIndiceList = indices

        self._label_font_props = font_manager.FontProperties(size=fontsize)

        if colors is None:
            self.labelMappable = self
            self.labelCValueList = np.take(self.cvalues, self.labelIndiceList)
        else:
            cmap = mcolors.ListedColormap(colors, N=len(self.labelLevelList))
            self.labelCValueList = list(range(len(self.labelLevelList)))
            self.labelMappable = cm.ScalarMappable(cmap=cmap,
                                                   norm=mcolors.NoNorm())

        self.labelXYs = []

        if np.iterable(manual):
            for x, y in manual:
                self.add_label_near(x, y, inline, inline_spacing)
        elif manual:
            print('Select label locations manually using first mouse button.')
            print('End manual selection with second mouse button.')
            if not inline:
                print('Remove last label by clicking third mouse button.')
            mpl._blocking_input.blocking_input_loop(
                self.axes.get_figure(root=True),
                ["button_press_event", "key_press_event"],
                timeout=-1, handler=functools.partial(
                    _contour_labeler_event_handler,
                    self, inline, inline_spacing))
        else:
            self.labels(inline, inline_spacing)

        return cbook.silent_list('text.Text', self.labelTexts)

    def print_label(self, linecontour, labelwidth):
        """Return whether a contour is long enough to hold a label."""
        return (len(linecontour) > 10 * labelwidth
                or (len(linecontour)
                    and (np.ptp(linecontour, axis=0) > 1.2 * labelwidth).any()))

    def too_close(self, x, y, lw):
        """Return whether a label is already near this location."""
        thresh = (1.2 * lw) ** 2
        return any((x - loc[0]) ** 2 + (y - loc[1]) ** 2 < thresh
                   for loc in self.labelXYs)

    def _get_nth_label_width(self, nth):
        """Return the width of the *nth* label, in pixels."""
        fig = self.axes.get_figure(root=False)
        renderer = fig.get_figure(root=True)._get_renderer()
        return (Text(0, 0,
                     self.get_text(self.labelLevelList[nth], self.labelFmt),
                     figure=fig, fontproperties=self._label_font_props)
                .get_window_extent(renderer).width)

    def get_text(self, lev, fmt):
        """Get the text of the label."""
        if isinstance(lev, str):
            return lev
        elif isinstance(fmt, dict):
            return fmt.get(lev, '%1.3f')
        elif callable(getattr(fmt, "format_ticks", None)):
            return fmt.format_ticks([*self.labelLevelList, lev])[-1]
        elif callable(fmt):
            return fmt(lev)
        else:
            return fmt % lev

    def locate_label(self, linecontour, labelwidth):
        """
        Find good place to draw a label (relatively flat part of the contour).
        """
        ctr_size = len(linecontour)
        n_blocks = int(np.ceil(ctr_size / labelwidth)) if labelwidth > 1 else 1
        block_size = ctr_size if n_blocks == 1 else int(labelwidth)
        # Split contour into blocks of length ``block_size``, filling the last
        # block by cycling the contour start (per `np.resize` semantics).  (Due
        # to cycling, the index returned is taken modulo ctr_size.)
        xx = np.resize(linecontour[:, 0], (n_blocks, block_size))
        yy = np.resize(linecontour[:, 1], (n_blocks, block_size))
        yfirst = yy[:, :1]
        ylast = yy[:, -1:]
        xfirst = xx[:, :1]
        xlast = xx[:, -1:]
        s = (yfirst - yy) * (xlast - xfirst) - (xfirst - xx) * (ylast - yfirst)
        l = np.hypot(xlast - xfirst, ylast - yfirst)
        # Ignore warning that divide by zero throws, as this is a valid option
        with np.errstate(divide='ignore', invalid='ignore'):
            distances = (abs(s) / l).sum(axis=-1)
        # Labels are drawn in the middle of the block (``hbsize``) where the
        # contour is the closest (per ``distances``) to a straight line, but
        # not `too_close()` to a preexisting label.
        hbsize = block_size // 2
        adist = np.argsort(distances)
        # If all candidates are `too_close()`, go back to the straightest part
        # (``adist[0]``).
        for idx in np.append(adist, adist[0]):
            x, y = xx[idx, hbsize], yy[idx, hbsize]
            if not self.too_close(x, y, labelwidth):
                break
        return x, y, (idx * block_size + hbsize) % ctr_size

    def _split_path_and_get_label_rotation(self, path, idx, screen_pos, lw, spacing=5):
        """
        Prepare for insertion of a label at index *idx* of *path*.

        Parameters
        ----------
        path : Path
            The path where the label will be inserted, in data space.
        idx : int
            The vertex index after which the label will be inserted.
        screen_pos : (float, float)
            The position where the label will be inserted, in screen space.
        lw : float
            The label width, in screen space.
        spacing : float
            Extra spacing around the label, in screen space.

        Returns
        -------
        path : Path
            The path, broken so that the label can be drawn over it.
        angle : float
            The rotation of the label.

        Notes
        -----
        Both tasks are done together to avoid calculating path lengths multiple times,
        which is relatively costly.

        The method used here involves computing the path length along the contour in
        pixel coordinates and then looking (label width / 2) away from central point to
        determine rotation and then to break contour if desired.  The extra spacing is
        taken into account when breaking the path, but not when computing the angle.
        """
        xys = path.vertices
        codes = path.codes

        # Insert a vertex at idx/pos (converting back to data space), if there isn't yet
        # a vertex there.  With infinite precision one could also always insert the
        # extra vertex (it will get masked out by the label below anyways), but floating
        # point inaccuracies (the point can have undergone a data->screen->data
        # transform loop) can slightly shift the point and e.g. shift the angle computed
        # below from exactly zero to nonzero.
        pos = self.get_transform().inverted().transform(screen_pos)
        if not np.allclose(pos, xys[idx]):
            xys = np.insert(xys, idx, pos, axis=0)
            codes = np.insert(codes, idx, Path.LINETO)

        # Find the connected component where the label will be inserted.  Note that a
        # path always starts with a MOVETO, and we consider there's an implicit
        # MOVETO (closing the last path) at the end.
        movetos = (codes == Path.MOVETO).nonzero()[0]
        start = movetos[movetos <= idx][-1]
        try:
            stop = movetos[movetos > idx][0]
        except IndexError:
            stop = len(codes)

        # Restrict ourselves to the connected component.
        cc_xys = xys[start:stop]
        idx -= start

        # If the path is closed, rotate it s.t. it starts at the label.
        is_closed_path = codes[stop - 1] == Path.CLOSEPOLY
        if is_closed_path:
            cc_xys = np.concatenate([cc_xys[idx:-1], cc_xys[:idx+1]])
            idx = 0

        # Like np.interp, but additionally vectorized over fp.
        def interp_vec(x, xp, fp): return [np.interp(x, xp, col) for col in fp.T]

        # Use cumulative path lengths ("cpl") as curvilinear coordinate along contour.
        screen_xys = self.get_transform().transform(cc_xys)
        path_cpls = np.insert(
            np.cumsum(np.hypot(*np.diff(screen_xys, axis=0).T)), 0, 0)
        path_cpls -= path_cpls[idx]

        # Use linear interpolation to get end coordinates of label.
        target_cpls = np.array([-lw/2, lw/2])
        if is_closed_path:  # For closed paths, target from the other end.
            target_cpls[0] += (path_cpls[-1] - path_cpls[0])
        (sx0, sx1), (sy0, sy1) = interp_vec(target_cpls, path_cpls, screen_xys)
        angle = np.rad2deg(np.arctan2(sy1 - sy0, sx1 - sx0))  # Screen space.
        if self.rightside_up:  # Fix angle so text is never upside-down
            angle = (angle + 90) % 180 - 90

        target_cpls += [-spacing, +spacing]  # Expand range by spacing.

        # Get indices near points of interest; use -1 as out of bounds marker.
        i0, i1 = np.interp(target_cpls, path_cpls, range(len(path_cpls)),
                           left=-1, right=-1)
        i0 = math.floor(i0)
        i1 = math.ceil(i1)
        (x0, x1), (y0, y1) = interp_vec(target_cpls, path_cpls, cc_xys)

        # Actually break contours (dropping zero-len parts).
        new_xy_blocks = []
        new_code_blocks = []
        if is_closed_path:
            if i0 != -1 and i1 != -1:
                # This is probably wrong in the case that the entire contour would
                # be discarded, but ensures that a valid path is returned and is
                # consistent with behavior of mpl <3.8
                points = cc_xys[i1:i0+1]
                new_xy_blocks.extend([[(x1, y1)], points, [(x0, y0)]])
                nlines = len(points) + 1
                new_code_blocks.extend([[Path.MOVETO], [Path.LINETO] * nlines])
        else:
            if i0 != -1:
                new_xy_blocks.extend([cc_xys[:i0 + 1], [(x0, y0)]])
                new_code_blocks.extend([[Path.MOVETO], [Path.LINETO] * (i0 + 1)])
            if i1 != -1:
                new_xy_blocks.extend([[(x1, y1)], cc_xys[i1:]])
                new_code_blocks.extend([
                    [Path.MOVETO], [Path.LINETO] * (len(cc_xys) - i1)])

        # Back to the full path.
        xys = np.concatenate([xys[:start], *new_xy_blocks, xys[stop:]])
        codes = np.concatenate([codes[:start], *new_code_blocks, codes[stop:]])

        return angle, Path(xys, codes)

    def add_label(self, x, y, rotation, lev, cvalue):
        """Add a contour label, respecting whether *use_clabeltext* was set."""
        data_x, data_y = self.axes.transData.inverted().transform((x, y))
        t = Text(
            data_x, data_y,
            text=self.get_text(lev, self.labelFmt),
            rotation=rotation,
            horizontalalignment='center', verticalalignment='center',
            zorder=self._clabel_zorder,
            color=self.labelMappable.to_rgba(cvalue, alpha=self.get_alpha()),
            fontproperties=self._label_font_props,
            clip_box=self.axes.bbox)
        if self._use_clabeltext:
            data_rotation, = self.axes.transData.inverted().transform_angles(
                [rotation], [[x, y]])
            t.set(rotation=data_rotation, transform_rotates_text=True)
        self.labelTexts.append(t)
        self.labelCValues.append(cvalue)
        self.labelXYs.append((x, y))
        # Add label to plot here - useful for manual mode label selection
        self.axes.add_artist(t)

    def add_label_near(self, x, y, inline=True, inline_spacing=5,
                       transform=None):
        """
        Add a label near the point ``(x, y)``.

        Parameters
        ----------
        x, y : float
            The approximate location of the label.
        inline : bool, default: True
            If *True* remove the segment of the contour beneath the label.
        inline_spacing : int, default: 5
            Space in pixels to leave on each side of label when placing
            inline. This spacing will be exact for labels at locations where
            the contour is straight, less so for labels on curved contours.
        transform : `.Transform` or `False`, default: ``self.axes.transData``
            A transform applied to ``(x, y)`` before labeling.  The default
            causes ``(x, y)`` to be interpreted as data coordinates.  `False`
            is a synonym for `.IdentityTransform`; i.e. ``(x, y)`` should be
            interpreted as display coordinates.
        """

        if transform is None:
            transform = self.axes.transData
        if transform:
            x, y = transform.transform((x, y))

        idx_level_min, idx_vtx_min, proj = self._find_nearest_contour(
            (x, y), self.labelIndiceList)
        path = self._paths[idx_level_min]
        level = self.labelIndiceList.index(idx_level_min)
        label_width = self._get_nth_label_width(level)
        rotation, path = self._split_path_and_get_label_rotation(
            path, idx_vtx_min, proj, label_width, inline_spacing)
        self.add_label(*proj, rotation, self.labelLevelList[idx_level_min],
                       self.labelCValueList[idx_level_min])

        if inline:
            self._paths[idx_level_min] = path

    def pop_label(self, index=-1):
        """Defaults to removing last label, but any index can be supplied"""
        self.labelCValues.pop(index)
        t = self.labelTexts.pop(index)
        t.remove()

    def labels(self, inline, inline_spacing):
        for idx, (icon, lev, cvalue) in enumerate(zip(
                self.labelIndiceList,
                self.labelLevelList,
                self.labelCValueList,
        )):
            trans = self.get_transform()
            label_width = self._get_nth_label_width(idx)
            additions = []
            for subpath in self._paths[icon]._iter_connected_components():
                screen_xys = trans.transform(subpath.vertices)
                # Check if long enough for a label
                if self.print_label(screen_xys, label_width):
                    x, y, idx = self.locate_label(screen_xys, label_width)
                    rotation, path = self._split_path_and_get_label_rotation(
                        subpath, idx, (x, y),
                        label_width, inline_spacing)
                    self.add_label(x, y, rotation, lev, cvalue)  # Really add label.
                    if inline:  # If inline, add new contours
                        additions.append(path)
                else:  # If not adding label, keep old path
                    additions.append(subpath)
            # After looping over all segments on a contour, replace old path by new one
            # if inlining.
            if inline:
                self._paths[icon] = Path.make_compound_path(*additions)

    def remove(self):
        super().remove()
        for text in self.labelTexts:
            text.remove()


def _find_closest_point_on_path(xys, p):
    """
    Parameters
    ----------
    xys : (N, 2) array-like
        Coordinates of vertices.
    p : (float, float)
        Coordinates of point.

    Returns
    -------
    d2min : float
        Minimum square distance of *p* to *xys*.
    proj : (float, float)
        Projection of *p* onto *xys*.
    imin : (int, int)
        Consecutive indices of vertices of segment in *xys* where *proj* is.
        Segments are considered as including their end-points; i.e. if the
        closest point on the path is a node in *xys* with index *i*, this
        returns ``(i-1, i)``.  For the special case where *xys* is a single
        point, this returns ``(0, 0)``.
    """
    if len(xys) == 1:
        return (((p - xys[0]) ** 2).sum(), xys[0], (0, 0))
    dxys = xys[1:] - xys[:-1]  # Individual segment vectors.
    norms = (dxys ** 2).sum(axis=1)
    norms[norms == 0] = 1  # For zero-length segment, replace 0/0 by 0/1.
    rel_projs = np.clip(  # Project onto each segment in relative 0-1 coords.
        ((p - xys[:-1]) * dxys).sum(axis=1) / norms,
        0, 1)[:, None]
    projs = xys[:-1] + rel_projs * dxys  # Projs. onto each segment, in (x, y).
    d2s = ((projs - p) ** 2).sum(axis=1)  # Squared distances.
    imin = np.argmin(d2s)
    return (d2s[imin], projs[imin], (imin, imin+1))


_docstring.interpd.register(contour_set_attributes=r"""
Attributes
----------
levels : array
    The values of the contour levels.

layers : array
    Same as levels for line contours; half-way between
    levels for filled contours.  See ``ContourSet._process_colors``.
""")


@_docstring.interpd
class ContourSet(ContourLabeler, mcoll.Collection):
    """
    Store a set of contour lines or filled regions.

    User-callable method: `~.Axes.clabel`

    Parameters
    ----------
    ax : `~matplotlib.axes.Axes`

    levels : [level0, level1, ..., leveln]
        A list of floating point numbers indicating the contour levels.

    allsegs : [level0segs, level1segs, ...]
        List of all the polygon segments for all the *levels*.
        For contour lines ``len(allsegs) == len(levels)``, and for
        filled contour regions ``len(allsegs) = len(levels)-1``. The lists
        should look like ::

            level0segs = [polygon0, polygon1, ...]
            polygon0 = [[x0, y0], [x1, y1], ...]

    allkinds : ``None`` or [level0kinds, level1kinds, ...]
        Optional list of all the polygon vertex kinds (code types), as
        described and used in Path. This is used to allow multiply-
        connected paths such as holes within filled polygons.
        If not ``None``, ``len(allkinds) == len(allsegs)``. The lists
        should look like ::

            level0kinds = [polygon0kinds, ...]
            polygon0kinds = [vertexcode0, vertexcode1, ...]

        If *allkinds* is not ``None``, usually all polygons for a
        particular contour level are grouped together so that
        ``level0segs = [polygon0]`` and ``level0kinds = [polygon0kinds]``.

    **kwargs
        Keyword arguments are as described in the docstring of
        `~.Axes.contour`.

    %(contour_set_attributes)s
    """

    def __init__(self, ax, *args,
                 levels=None, filled=False, linewidths=None, linestyles=None,
                 hatches=(None,), alpha=None, origin=None, extent=None,
                 cmap=None, colors=None, norm=None, vmin=None, vmax=None,
                 colorizer=None, extend='neither', antialiased=None, nchunk=0,
                 locator=None, transform=None, negative_linestyles=None, clip_path=None,
                 **kwargs):
        """
        Draw contour lines or filled regions, depending on
        whether keyword arg *filled* is ``False`` (default) or ``True``.

        Call signature::

            ContourSet(ax, levels, allsegs, [allkinds], **kwargs)

        Parameters
        ----------
        ax : `~matplotlib.axes.Axes`
            The `~.axes.Axes` object to draw on.

        levels : [level0, level1, ..., leveln]
            A list of floating point numbers indicating the contour
            levels.

        allsegs : [level0segs, level1segs, ...]
            List of all the polygon segments for all the *levels*.
            For contour lines ``len(allsegs) == len(levels)``, and for
            filled contour regions ``len(allsegs) = len(levels)-1``. The lists
            should look like ::

                level0segs = [polygon0, polygon1, ...]
                polygon0 = [[x0, y0], [x1, y1], ...]

        allkinds : [level0kinds, level1kinds, ...], optional
            Optional list of all the polygon vertex kinds (code types), as
            described and used in Path. This is used to allow multiply-
            connected paths such as holes within filled polygons.
            If not ``None``, ``len(allkinds) == len(allsegs)``. The lists
            should look like ::

                level0kinds = [polygon0kinds, ...]
                polygon0kinds = [vertexcode0, vertexcode1, ...]

            If *allkinds* is not ``None``, usually all polygons for a
            particular contour level are grouped together so that
            ``level0segs = [polygon0]`` and ``level0kinds = [polygon0kinds]``.

        **kwargs
            Keyword arguments are as described in the docstring of
            `~.Axes.contour`.
        """
        if antialiased is None and filled:
            # Eliminate artifacts; we are not stroking the boundaries.
            antialiased = False
            # The default for line contours will be taken from the
            # LineCollection default, which uses :rc:`lines.antialiased`.
        super().__init__(
            antialiaseds=antialiased,
            alpha=alpha,
            clip_path=clip_path,
            transform=transform,
            colorizer=colorizer,
        )
        self.axes = ax
        self.levels = levels
        self.filled = filled
        self.hatches = hatches
        self.origin = origin
        self.extent = extent
        self.colors = colors
        self.extend = extend

        self.nchunk = nchunk
        self.locator = locator

        if colorizer:
            self._set_colorizer_check_keywords(colorizer, cmap=cmap,
                                               norm=norm, vmin=vmin,
                                               vmax=vmax, colors=colors)
            norm = colorizer.norm
            cmap = colorizer.cmap
        if (isinstance(norm, mcolors.LogNorm)
                or isinstance(self.locator, ticker.LogLocator)):
            self.logscale = True
            if norm is None:
                norm = mcolors.LogNorm()
        else:
            self.logscale = False

        _api.check_in_list([None, 'lower', 'upper', 'image'], origin=origin)
        if self.extent is not None and len(self.extent) != 4:
            raise ValueError(
                "If given, 'extent' must be None or (x0, x1, y0, y1)")
        if self.colors is not None and cmap is not None:
            raise ValueError('Either colors or cmap must be None')
        if self.origin == 'image':
            self.origin = mpl.rcParams['image.origin']

        self._orig_linestyles = linestyles  # Only kept for user access.
        self.negative_linestyles = negative_linestyles
        # If negative_linestyles was not defined as a keyword argument, define
        # negative_linestyles with rcParams
        if self.negative_linestyles is None:
            self.negative_linestyles = \
                mpl.rcParams['contour.negative_linestyle']

        kwargs = self._process_args(*args, **kwargs)
        self._process_levels()

        self._extend_min = self.extend in ['min', 'both']
        self._extend_max = self.extend in ['max', 'both']
        if self.colors is not None:
            if mcolors.is_color_like(self.colors):
                color_sequence = [self.colors]
            else:
                color_sequence = self.colors

            ncolors = len(self.levels)
            if self.filled:
                ncolors -= 1
            i0 = 0

            # Handle the case where colors are given for the extended
            # parts of the contour.

            use_set_under_over = False
            # if we are extending the lower end, and we've been given enough
            # colors then skip the first color in the resulting cmap. For the
            # extend_max case we don't need to worry about passing more colors
            # than ncolors as ListedColormap will clip.
            total_levels = (ncolors +
                            int(self._extend_min) +
                            int(self._extend_max))
            if (len(color_sequence) == total_levels and
                    (self._extend_min or self._extend_max)):
                use_set_under_over = True
                if self._extend_min:
                    i0 = 1

            cmap = mcolors.ListedColormap(color_sequence[i0:None], N=ncolors)

            if use_set_under_over:
                if self._extend_min:
                    cmap.set_under(color_sequence[0])
                if self._extend_max:
                    cmap.set_over(color_sequence[-1])

        # label lists must be initialized here
        self.labelTexts = []
        self.labelCValues = []

        self.set_cmap(cmap)
        if norm is not None:
            self.set_norm(norm)
        with self.norm.callbacks.blocked(signal="changed"):
            if vmin is not None:
                self.norm.vmin = vmin
            if vmax is not None:
                self.norm.vmax = vmax
        self.norm._changed()
        self._process_colors()

        if self._paths is None:
            self._paths = self._make_paths_from_contour_generator()

        if self.filled:
            if linewidths is not None:
                _api.warn_external('linewidths is ignored by contourf')
            # Lower and upper contour levels.
            lowers, uppers = self._get_lowers_and_uppers()
            self.set(
                edgecolor="none",
                # Default zorder taken from Collection
                zorder=kwargs.pop("zorder", 1),
            )

        else:
            self.set(
                facecolor="none",
                linewidths=self._process_linewidths(linewidths),
                linestyle=self._process_linestyles(linestyles),
                # Default zorder taken from LineCollection, which is higher
                # than for filled contours so that lines are displayed on top.
                zorder=kwargs.pop("zorder", 2),
                label="_nolegend_",
            )

        self.axes.add_collection(self, autolim=False)
        self.sticky_edges.x[:] = [self._mins[0], self._maxs[0]]
        self.sticky_edges.y[:] = [self._mins[1], self._maxs[1]]
        self.axes.update_datalim([self._mins, self._maxs])
        self.axes.autoscale_view(tight=True)

        self.changed()  # set the colors

        if kwargs:
            _api.warn_external(
                'The following kwargs were not used by contour: ' +
                ", ".join(map(repr, kwargs))
            )

    allsegs = property(lambda self: [
        [subp.vertices for subp in p._iter_connected_components()]
        for p in self.get_paths()])
    allkinds = property(lambda self: [
        [subp.codes for subp in p._iter_connected_components()]
        for p in self.get_paths()])
    alpha = property(lambda self: self.get_alpha())
    linestyles = property(lambda self: self._orig_linestyles)

    def get_transform(self):
        """Return the `.Transform` instance used by this ContourSet."""
        if self._transform is None:
            self._transform = self.axes.transData
        elif (not isinstance(self._transform, mtransforms.Transform)
              and hasattr(self._transform, '_as_mpl_transform')):
            self._transform = self._transform._as_mpl_transform(self.axes)
        return self._transform

    def __getstate__(self):
        state = self.__dict__.copy()
        # the C object _contour_generator cannot currently be pickled. This
        # isn't a big issue as it is not actually used once the contour has
        # been calculated.
        state['_contour_generator'] = None
        return state

    def legend_elements(self, variable_name='x', str_format=str):
        """
        Return a list of artists and labels suitable for passing through
        to `~.Axes.legend` which represent this ContourSet.

        The labels have the form "0 < x <= 1" stating the data ranges which
        the artists represent.

        Parameters
        ----------
        variable_name : str
            The string used inside the inequality used on the labels.
        str_format : function: float -> str
            Function used to format the numbers in the labels.

        Returns
        -------
        artists : list[`.Artist`]
            A list of the artists.
        labels : list[str]
            A list of the labels.
        """
        artists = []
        labels = []

        if self.filled:
            lowers, uppers = self._get_lowers_and_uppers()
            n_levels = len(self._paths)
            for idx in range(n_levels):
                artists.append(mpatches.Rectangle(
                    (0, 0), 1, 1,
                    facecolor=self.get_facecolor()[idx],
                    hatch=self.hatches[idx % len(self.hatches)],
                ))
                lower = str_format(lowers[idx])
                upper = str_format(uppers[idx])
                if idx == 0 and self.extend in ('min', 'both'):
                    labels.append(fr'${variable_name} \leq {lower}s$')
                elif idx == n_levels - 1 and self.extend in ('max', 'both'):
                    labels.append(fr'${variable_name} > {upper}s$')
                else:
                    labels.append(fr'${lower} < {variable_name} \leq {upper}$')
        else:
            for idx, level in enumerate(self.levels):
                artists.append(Line2D(
                    [], [],
                    color=self.get_edgecolor()[idx],
                    linewidth=self.get_linewidths()[idx],
                    linestyle=self.get_linestyles()[idx],
                ))
                labels.append(fr'${variable_name} = {str_format(level)}$')

        return artists, labels

    def _process_args(self, *args, **kwargs):
        """
        Process *args* and *kwargs*; override in derived classes.

        Must set self.levels, self.zmin and self.zmax, and update Axes limits.
        """
        self.levels = args[0]
        allsegs = args[1]
        allkinds = args[2] if len(args) > 2 else None
        self.zmax = np.max(self.levels)
        self.zmin = np.min(self.levels)

        if allkinds is None:
            allkinds = [[None] * len(segs) for segs in allsegs]

        # Check lengths of levels and allsegs.
        if self.filled:
            if len(allsegs) != len(self.levels) - 1:
                raise ValueError('must be one less number of segments as '
                                 'levels')
        else:
            if len(allsegs) != len(self.levels):
                raise ValueError('must be same number of segments as levels')

        # Check length of allkinds.
        if len(allkinds) != len(allsegs):
            raise ValueError('allkinds has different length to allsegs')

        # Determine x, y bounds and update axes data limits.
        flatseglist = [s for seg in allsegs for s in seg]
        points = np.concatenate(flatseglist, axis=0)
        self._mins = points.min(axis=0)
        self._maxs = points.max(axis=0)

        # Each entry in (allsegs, allkinds) is a list of (segs, kinds): segs is a list
        # of (N, 2) arrays of xy coordinates, kinds is a list of arrays of corresponding
        # pathcodes.  However, kinds can also be None; in which case all paths in that
        # list are codeless (this case is normalized above).  These lists are used to
        # construct paths, which then get concatenated.
        self._paths = [Path.make_compound_path(*map(Path, segs, kinds))
                       for segs, kinds in zip(allsegs, allkinds)]

        return kwargs

    def _make_paths_from_contour_generator(self):
        """Compute ``paths`` using C extension."""
        if self._paths is not None:
            return self._paths
        cg = self._contour_generator
        empty_path = Path(np.empty((0, 2)))
        vertices_and_codes = (
            map(cg.create_filled_contour, *self._get_lowers_and_uppers())
            if self.filled else
            map(cg.create_contour, self.levels))
        return [Path(np.concatenate(vs), np.concatenate(cs)) if len(vs) else empty_path
                for vs, cs in vertices_and_codes]

    def _get_lowers_and_uppers(self):
        """
        Return ``(lowers, uppers)`` for filled contours.
        """
        lowers = self._levels[:-1]
        if self.zmin == lowers[0]:
            # Include minimum values in lowest interval
            lowers = lowers.copy()  # so we don't change self._levels
            if self.logscale:
                lowers[0] = 0.99 * self.zmin
            else:
                lowers[0] -= 1
        uppers = self._levels[1:]
        return (lowers, uppers)

    def changed(self):
        if not hasattr(self, "cvalues"):
            self._process_colors()  # Sets cvalues.
        # Force an autoscale immediately because self.to_rgba() calls
        # autoscale_None() internally with the data passed to it,
        # so if vmin/vmax are not set yet, this would override them with
        # content from *cvalues* rather than levels like we want
        self.norm.autoscale_None(self.levels)
        self.set_array(self.cvalues)
        self.update_scalarmappable()
        alphas = np.broadcast_to(self.get_alpha(), len(self.cvalues))
        for label, cv, alpha in zip(self.labelTexts, self.labelCValues, alphas):
            label.set_alpha(alpha)
            label.set_color(self.labelMappable.to_rgba(cv))
        super().changed()

    def _autolev(self, N):
        """
        Select contour levels to span the data.

        The target number of levels, *N*, is used only when the
        scale is not log and default locator is used.

        We need two more levels for filled contours than for
        line contours, because for the latter we need to specify
        the lower and upper boundary of each range. For example,
        a single contour boundary, say at z = 0, requires only
        one contour line, but two filled regions, and therefore
        three levels to provide boundaries for both regions.
        """
        if self.locator is None:
            if self.logscale:
                self.locator = ticker.LogLocator()
            else:
                self.locator = ticker.MaxNLocator(N + 1, min_n_ticks=1)

        lev = self.locator.tick_values(self.zmin, self.zmax)

        try:
            if self.locator._symmetric:
                return lev
        except AttributeError:
            pass

        # Trim excess levels the locator may have supplied.
        under = np.nonzero(lev < self.zmin)[0]
        i0 = under[-1] if len(under) else 0
        over = np.nonzero(lev > self.zmax)[0]
        i1 = over[0] + 1 if len(over) else len(lev)
        if self.extend in ('min', 'both'):
            i0 += 1
        if self.extend in ('max', 'both'):
            i1 -= 1

        if i1 - i0 < 3:
            i0, i1 = 0, len(lev)

        return lev[i0:i1]

    def _process_contour_level_args(self, args, z_dtype):
        """
        Determine the contour levels and store in self.levels.
        """
        if self.levels is None:
            if args:
                levels_arg = args[0]
            elif np.issubdtype(z_dtype, bool):
                if self.filled:
                    levels_arg = [0, .5, 1]
                else:
                    levels_arg = [.5]
            else:
                levels_arg = 7  # Default, hard-wired.
        else:
            levels_arg = self.levels
        if isinstance(levels_arg, Integral):
            self.levels = self._autolev(levels_arg)
        else:
            self.levels = np.asarray(levels_arg, np.float64)
        if self.filled and len(self.levels) < 2:
            raise ValueError("Filled contours require at least 2 levels.")
        if len(self.levels) > 1 and np.min(np.diff(self.levels)) <= 0.0:
            raise ValueError("Contour levels must be increasing")

    def _process_levels(self):
        """
        Assign values to :attr:`layers` based on :attr:`levels`,
        adding extended layers as needed if contours are filled.

        For line contours, layers simply coincide with levels;
        a line is a thin layer.  No extended levels are needed
        with line contours.
        """
        # Make a private _levels to include extended regions; we
        # want to leave the original levels attribute unchanged.
        # (Colorbar needs this even for line contours.)
        self._levels = list(self.levels)

        if self.logscale:
            lower, upper = 1e-250, 1e250
        else:
            lower, upper = -1e250, 1e250

        if self.extend in ('both', 'min'):
            self._levels.insert(0, lower)
        if self.extend in ('both', 'max'):
            self._levels.append(upper)
        self._levels = np.asarray(self._levels)

        if not self.filled:
            self.layers = self.levels
            return

        # Layer values are mid-way between levels in screen space.
        if self.logscale:
            # Avoid overflow by taking sqrt before multiplying.
            self.layers = (np.sqrt(self._levels[:-1])
                           * np.sqrt(self._levels[1:]))
        else:
            self.layers = 0.5 * (self._levels[:-1] + self._levels[1:])

    def _process_colors(self):
        """
        Color argument processing for contouring.

        Note that we base the colormapping on the contour levels
        and layers, not on the actual range of the Z values.  This
        means we don't have to worry about bad values in Z, and we
        always have the full dynamic range available for the selected
        levels.

        The color is based on the midpoint of the layer, except for
        extended end layers.  By default, the norm vmin and vmax
        are the extreme values of the non-extended levels.  Hence,
        the layer color extremes are not the extreme values of
        the colormap itself, but approach those values as the number
        of levels increases.  An advantage of this scheme is that
        line contours, when added to filled contours, take on
        colors that are consistent with those of the filled regions;
        for example, a contour line on the boundary between two
        regions will have a color intermediate between those
        of the regions.

        """
        self.monochrome = self.cmap.monochrome
        if self.colors is not None:
            # Generate integers for direct indexing.
            i0, i1 = 0, len(self.levels)
            if self.filled:
                i1 -= 1
                # Out of range indices for over and under:
                if self.extend in ('both', 'min'):
                    i0 -= 1
                if self.extend in ('both', 'max'):
                    i1 += 1
            self.cvalues = list(range(i0, i1))
            self.set_norm(mcolors.NoNorm())
        else:
            self.cvalues = self.layers
        self.norm.autoscale_None(self.levels)
        self.set_array(self.cvalues)
        self.update_scalarmappable()
        if self.extend in ('both', 'max', 'min'):
            self.norm.clip = False

    def _process_linewidths(self, linewidths):
        Nlev = len(self.levels)
        if linewidths is None:
            default_linewidth = mpl.rcParams['contour.linewidth']
            if default_linewidth is None:
                default_linewidth = mpl.rcParams['lines.linewidth']
            return [default_linewidth] * Nlev
        elif not np.iterable(linewidths):
            return [linewidths] * Nlev
        else:
            linewidths = list(linewidths)
            return (linewidths * math.ceil(Nlev / len(linewidths)))[:Nlev]

    def _process_linestyles(self, linestyles):
        Nlev = len(self.levels)
        if linestyles is None:
            tlinestyles = ['solid'] * Nlev
            if self.monochrome:
                eps = - (self.zmax - self.zmin) * 1e-15
                for i, lev in enumerate(self.levels):
                    if lev < eps:
                        tlinestyles[i] = self.negative_linestyles
        else:
            if isinstance(linestyles, str):
                tlinestyles = [linestyles] * Nlev
            elif np.iterable(linestyles):
                tlinestyles = list(linestyles)
                if len(tlinestyles) < Nlev:
                    nreps = int(np.ceil(Nlev / len(linestyles)))
                    tlinestyles = tlinestyles * nreps
                if len(tlinestyles) > Nlev:
                    tlinestyles = tlinestyles[:Nlev]
            else:
                raise ValueError("Unrecognized type for linestyles kwarg")
        return tlinestyles

    def _find_nearest_contour(self, xy, indices=None):
        """
        Find the point in the unfilled contour plot that is closest (in screen
        space) to point *xy*.

        Parameters
        ----------
        xy : tuple[float, float]
            The reference point (in screen space).
        indices : list of int or None, default: None
            Indices of contour levels to consider.  If None (the default), all levels
            are considered.

        Returns
        -------
        idx_level_min : int
            The index of the contour level closest to *xy*.
        idx_vtx_min : int
            The index of the `.Path` segment closest to *xy* (at that level).
        proj : (float, float)
            The point in the contour plot closest to *xy*.
        """

        # Convert each contour segment to pixel coordinates and then compare the given
        # point to those coordinates for each contour. This is fast enough in normal
        # cases, but speedups may be possible.

        if self.filled:
            raise ValueError("Method does not support filled contours")

        if indices is None:
            indices = range(len(self._paths))

        d2min = np.inf
        idx_level_min = idx_vtx_min = proj_min = None

        for idx_level in indices:
            path = self._paths[idx_level]
            idx_vtx_start = 0
            for subpath in path._iter_connected_components():
                if not len(subpath.vertices):
                    continue
                lc = self.get_transform().transform(subpath.vertices)
                d2, proj, leg = _find_closest_point_on_path(lc, xy)
                if d2 < d2min:
                    d2min = d2
                    idx_level_min = idx_level
                    idx_vtx_min = leg[1] + idx_vtx_start
                    proj_min = proj
                idx_vtx_start += len(subpath)

        return idx_level_min, idx_vtx_min, proj_min

    def find_nearest_contour(self, x, y, indices=None, pixel=True):
        """
        Find the point in the contour plot that is closest to ``(x, y)``.

        This method does not support filled contours.

        Parameters
        ----------
        x, y : float
            The reference point.
        indices : list of int or None, default: None
            Indices of contour levels to consider.  If None (the default), all
            levels are considered.
        pixel : bool, default: True
            If *True*, measure distance in pixel (screen) space, which is
            useful for manual contour labeling; else, measure distance in axes
            space.

        Returns
        -------
        path : int
            The index of the path that is closest to ``(x, y)``.  Each path corresponds
            to one contour level.
        subpath : int
            The index within that closest path of the subpath that is closest to
            ``(x, y)``.  Each subpath corresponds to one unbroken contour line.
        index : int
            The index of the vertices within that subpath that are closest to
            ``(x, y)``.
        xmin, ymin : float
            The point in the contour plot that is closest to ``(x, y)``.
        d2 : float
            The squared distance from ``(xmin, ymin)`` to ``(x, y)``.
        """
        segment = index = d2 = None

        with ExitStack() as stack:
            if not pixel:
                # _find_nearest_contour works in pixel space. We want axes space, so
                # effectively disable the transformation here by setting to identity.
                stack.enter_context(self._cm_set(
                    transform=mtransforms.IdentityTransform()))

            i_level, i_vtx, (xmin, ymin) = self._find_nearest_contour((x, y), indices)

        if i_level is not None:
            cc_cumlens = np.cumsum(
                [*map(len, self._paths[i_level]._iter_connected_components())])
            segment = cc_cumlens.searchsorted(i_vtx, "right")
            index = i_vtx if segment == 0 else i_vtx - cc_cumlens[segment - 1]
            d2 = (xmin-x)**2 + (ymin-y)**2

        return (i_level, segment, index, xmin, ymin, d2)

    def draw(self, renderer):
        paths = self._paths
        n_paths = len(paths)
        if not self.filled or all(hatch is None for hatch in self.hatches):
            super().draw(renderer)
            return
        # In presence of hatching, draw contours one at a time.
        edgecolors = self.get_edgecolors()
        if edgecolors.size == 0:
            edgecolors = ("none",)
        for idx in range(n_paths):
            with cbook._setattr_cm(self, _paths=[paths[idx]]), self._cm_set(
                hatch=self.hatches[idx % len(self.hatches)],
                array=[self.get_array()[idx]],
                linewidths=[self.get_linewidths()[idx % len(self.get_linewidths())]],
                linestyles=[self.get_linestyles()[idx % len(self.get_linestyles())]],
                edgecolors=edgecolors[idx % len(edgecolors)],
            ):
                super().draw(renderer)


@_docstring.interpd
class QuadContourSet(ContourSet):
    """
    Create and store a set of contour lines or filled regions.

    This class is typically not instantiated directly by the user but by
    `~.Axes.contour` and `~.Axes.contourf`.

    %(contour_set_attributes)s
    """

    def _process_args(self, *args, corner_mask=None, algorithm=None, **kwargs):
        """
        Process args and kwargs.
        """
        if args and isinstance(args[0], QuadContourSet):
            if self.levels is None:
                self.levels = args[0].levels
            self.zmin = args[0].zmin
            self.zmax = args[0].zmax
            self._corner_mask = args[0]._corner_mask
            contour_generator = args[0]._contour_generator
            self._mins = args[0]._mins
            self._maxs = args[0]._maxs
            self._algorithm = args[0]._algorithm
        else:
            import contourpy

            if algorithm is None:
                algorithm = mpl.rcParams['contour.algorithm']
            mpl.rcParams.validate["contour.algorithm"](algorithm)
            self._algorithm = algorithm

            if corner_mask is None:
                if self._algorithm == "mpl2005":
                    # mpl2005 does not support corner_mask=True so if not
                    # specifically requested then disable it.
                    corner_mask = False
                else:
                    corner_mask = mpl.rcParams['contour.corner_mask']
            self._corner_mask = corner_mask

            x, y, z = self._contour_args(args, kwargs)

            contour_generator = contourpy.contour_generator(
                x, y, z, name=self._algorithm, corner_mask=self._corner_mask,
                line_type=contourpy.LineType.SeparateCode,
                fill_type=contourpy.FillType.OuterCode,
                chunk_size=self.nchunk)

            t = self.get_transform()

            # if the transform is not trans data, and some part of it
            # contains transData, transform the xs and ys to data coordinates
            if (t != self.axes.transData and
                    any(t.contains_branch_seperately(self.axes.transData))):
                trans_to_data = t - self.axes.transData
                pts = np.vstack([x.flat, y.flat]).T
                transformed_pts = trans_to_data.transform(pts)
                x = transformed_pts[..., 0]
                y = transformed_pts[..., 1]

            self._mins = [ma.min(x), ma.min(y)]
            self._maxs = [ma.max(x), ma.max(y)]

        self._contour_generator = contour_generator

        return kwargs

    def _contour_args(self, args, kwargs):
        if self.filled:
            fn = 'contourf'
        else:
            fn = 'contour'
        nargs = len(args)

        if 0 < nargs <= 2:
            z, *args = args
            z = ma.asarray(z)
            x, y = self._initialize_x_y(z)
        elif 2 < nargs <= 4:
            x, y, z_orig, *args = args
            x, y, z = self._check_xyz(x, y, z_orig, kwargs)

        else:
            raise _api.nargs_error(fn, takes="from 1 to 4", given=nargs)
        z = ma.masked_invalid(z, copy=False)
        self.zmax = z.max().astype(float)
        self.zmin = z.min().astype(float)
        if self.logscale and self.zmin <= 0:
            z = ma.masked_where(z <= 0, z)
            _api.warn_external('Log scale: values of z <= 0 have been masked')
            self.zmin = z.min().astype(float)
        self._process_contour_level_args(args, z.dtype)
        return (x, y, z)

    def _check_xyz(self, x, y, z, kwargs):
        """
        Check that the shapes of the input arrays match; if x and y are 1D,
        convert them to 2D using meshgrid.
        """
        x, y = self.axes._process_unit_info([("x", x), ("y", y)], kwargs)

        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        z = ma.asarray(z)

        if z.ndim != 2:
            raise TypeError(f"Input z must be 2D, not {z.ndim}D")
        if z.shape[0] < 2 or z.shape[1] < 2:
            raise TypeError(f"Input z must be at least a (2, 2) shaped array, "
                            f"but has shape {z.shape}")
        Ny, Nx = z.shape

        if x.ndim != y.ndim:
            raise TypeError(f"Number of dimensions of x ({x.ndim}) and y "
                            f"({y.ndim}) do not match")
        if x.ndim == 1:
            nx, = x.shape
            ny, = y.shape
            if nx != Nx:
                raise TypeError(f"Length of x ({nx}) must match number of "
                                f"columns in z ({Nx})")
            if ny != Ny:
                raise TypeError(f"Length of y ({ny}) must match number of "
                                f"rows in z ({Ny})")
            x, y = np.meshgrid(x, y)
        elif x.ndim == 2:
            if x.shape != z.shape:
                raise TypeError(
                    f"Shapes of x {x.shape} and z {z.shape} do not match")
            if y.shape != z.shape:
                raise TypeError(
                    f"Shapes of y {y.shape} and z {z.shape} do not match")
        else:
            raise TypeError(f"Inputs x and y must be 1D or 2D, not {x.ndim}D")

        return x, y, z

    def _initialize_x_y(self, z):
        """
        Return X, Y arrays such that contour(Z) will match imshow(Z)
        if origin is not None.
        The center of pixel Z[i, j] depends on origin:
        if origin is None, x = j, y = i;
        if origin is 'lower', x = j + 0.5, y = i + 0.5;
        if origin is 'upper', x = j + 0.5, y = Nrows - i - 0.5
        If extent is not None, x and y will be scaled to match,
        as in imshow.
        If origin is None and extent is not None, then extent
        will give the minimum and maximum values of x and y.
        """
        if z.ndim != 2:
            raise TypeError(f"Input z must be 2D, not {z.ndim}D")
        elif z.shape[0] < 2 or z.shape[1] < 2:
            raise TypeError(f"Input z must be at least a (2, 2) shaped array, "
                            f"but has shape {z.shape}")
        else:
            Ny, Nx = z.shape
        if self.origin is None:  # Not for image-matching.
            if self.extent is None:
                return np.meshgrid(np.arange(Nx), np.arange(Ny))
            else:
                x0, x1, y0, y1 = self.extent
                x = np.linspace(x0, x1, Nx)
                y = np.linspace(y0, y1, Ny)
                return np.meshgrid(x, y)
        # Match image behavior:
        if self.extent is None:
            x0, x1, y0, y1 = (0, Nx, 0, Ny)
        else:
            x0, x1, y0, y1 = self.extent
        dx = (x1 - x0) / Nx
        dy = (y1 - y0) / Ny
        x = x0 + (np.arange(Nx) + 0.5) * dx
        y = y0 + (np.arange(Ny) + 0.5) * dy
        if self.origin == 'upper':
            y = y[::-1]
        return np.meshgrid(x, y)


_docstring.interpd.register(contour_doc="""
`.contour` and `.contourf` draw contour lines and filled contours,
respectively.  Except as noted, function signatures and return values
are the same for both versions.

Parameters
----------
X, Y : array-like, optional
    The coordinates of the values in *Z*.

    *X* and *Y* must both be 2D with the same shape as *Z* (e.g.
    created via `numpy.meshgrid`), or they must both be 1-D such
    that ``len(X) == N`` is the number of columns in *Z* and
    ``len(Y) == M`` is the number of rows in *Z*.

    *X* and *Y* must both be ordered monotonically.

    If not given, they are assumed to be integer indices, i.e.
    ``X = range(N)``, ``Y = range(M)``.

Z : (M, N) array-like
    The height values over which the contour is drawn.  Color-mapping is
    controlled by *cmap*, *norm*, *vmin*, and *vmax*.

levels : int or array-like, optional
    Determines the number and positions of the contour lines / regions.

    If an int *n*, use `~matplotlib.ticker.MaxNLocator`, which tries
    to automatically choose no more than *n+1* "nice" contour levels
    between minimum and maximum numeric values of *Z*.

    If array-like, draw contour lines at the specified levels.
    The values must be in increasing order.

Returns
-------
`~.contour.QuadContourSet`

Other Parameters
----------------
corner_mask : bool, default: :rc:`contour.corner_mask`
    Enable/disable corner masking, which only has an effect if *Z* is
    a masked array.  If ``False``, any quad touching a masked point is
    masked out.  If ``True``, only the triangular corners of quads
    nearest those points are always masked out, other triangular
    corners comprising three unmasked points are contoured as usual.

colors : :mpltype:`color` or list of :mpltype:`color`, optional
    The colors of the levels, i.e. the lines for `.contour` and the
    areas for `.contourf`.

    The sequence is cycled for the levels in ascending order. If the
    sequence is shorter than the number of levels, it's repeated.

    As a shortcut, a single color may be used in place of one-element lists, i.e.
    ``'red'`` instead of ``['red']`` to color all levels with the same color.

    .. versionchanged:: 3.10
        Previously a single color had to be expressed as a string, but now any
        valid color format may be passed.

    By default (value *None*), the colormap specified by *cmap*
    will be used.

alpha : float, default: 1
    The alpha blending value, between 0 (transparent) and 1 (opaque).

%(cmap_doc)s

    This parameter is ignored if *colors* is set.

%(norm_doc)s

    This parameter is ignored if *colors* is set.

%(vmin_vmax_doc)s

    If *vmin* or *vmax* are not given, the default color scaling is based on
    *levels*.

    This parameter is ignored if *colors* is set.

%(colorizer_doc)s

    This parameter is ignored if *colors* is set.

origin : {*None*, 'upper', 'lower', 'image'}, default: None
    Determines the orientation and exact position of *Z* by specifying
    the position of ``Z[0, 0]``.  This is only relevant, if *X*, *Y*
    are not given.

    - *None*: ``Z[0, 0]`` is at X=0, Y=0 in the lower left corner.
    - 'lower': ``Z[0, 0]`` is at X=0.5, Y=0.5 in the lower left corner.
    - 'upper': ``Z[0, 0]`` is at X=N+0.5, Y=0.5 in the upper left
      corner.
    - 'image': Use the value from :rc:`image.origin`.

extent : (x0, x1, y0, y1), optional
    If *origin* is not *None*, then *extent* is interpreted as in
    `.imshow`: it gives the outer pixel boundaries. In this case, the
    position of Z[0, 0] is the center of the pixel, not a corner. If
    *origin* is *None*, then (*x0*, *y0*) is the position of Z[0, 0],
    and (*x1*, *y1*) is the position of Z[-1, -1].

    This argument is ignored if *X* and *Y* are specified in the call
    to contour.

locator : ticker.Locator subclass, optional
    The locator is used to determine the contour levels if they
    are not given explicitly via *levels*.
    Defaults to `~.ticker.MaxNLocator`.

extend : {'neither', 'both', 'min', 'max'}, default: 'neither'
    Determines the ``contourf``-coloring of values that are outside the
    *levels* range.

    If 'neither', values outside the *levels* range are not colored.
    If 'min', 'max' or 'both', color the values below, above or below
    and above the *levels* range.

    Values below ``min(levels)`` and above ``max(levels)`` are mapped
    to the under/over values of the `.Colormap`. Note that most
    colormaps do not have dedicated colors for these by default, so
    that the over and under values are the edge values of the colormap.
    You may want to set these values explicitly using
    `.Colormap.set_under` and `.Colormap.set_over`.

    .. note::

        An existing `.QuadContourSet` does not get notified if
        properties of its colormap are changed. Therefore, an explicit
        call `~.ContourSet.changed()` is needed after modifying the
        colormap. The explicit call can be left out, if a colorbar is
        assigned to the `.QuadContourSet` because it internally calls
        `~.ContourSet.changed()`.

    Example::

        x = np.arange(1, 10)
        y = x.reshape(-1, 1)
        h = x * y

        cs = plt.contourf(h, levels=[10, 30, 50],
            colors=['#808080', '#A0A0A0', '#C0C0C0'], extend='both')
        cs.cmap.set_over('red')
        cs.cmap.set_under('blue')
        cs.changed()

xunits, yunits : registered units, optional
    Override axis units by specifying an instance of a
    :class:`matplotlib.units.ConversionInterface`.

antialiased : bool, optional
    Enable antialiasing, overriding the defaults.  For
    filled contours, the default is *False*.  For line contours,
    it is taken from :rc:`lines.antialiased`.

nchunk : int >= 0, optional
    If 0, no subdivision of the domain.  Specify a positive integer to
    divide the domain into subdomains of *nchunk* by *nchunk* quads.
    Chunking reduces the maximum length of polygons generated by the
    contouring algorithm which reduces the rendering workload passed
    on to the backend and also requires slightly less RAM.  It can
    however introduce rendering artifacts at chunk boundaries depending
    on the backend, the *antialiased* flag and value of *alpha*.

linewidths : float or array-like, default: :rc:`contour.linewidth`
    *Only applies to* `.contour`.

    The line width of the contour lines.

    If a number, all levels will be plotted with this linewidth.

    If a sequence, the levels in ascending order will be plotted with
    the linewidths in the order specified.

    If None, this falls back to :rc:`lines.linewidth`.

linestyles : {*None*, 'solid', 'dashed', 'dashdot', 'dotted'}, optional
    *Only applies to* `.contour`.

    If *linestyles* is *None*, the default is 'solid' unless the lines are
    monochrome. In that case, negative contours will instead take their
    linestyle from the *negative_linestyles* argument.

    *linestyles* can also be an iterable of the above strings specifying a set
    of linestyles to be used. If this iterable is shorter than the number of
    contour levels it will be repeated as necessary.

negative_linestyles : {*None*, 'solid', 'dashed', 'dashdot', 'dotted'}, \
                       optional
    *Only applies to* `.contour`.

    If *linestyles* is *None* and the lines are monochrome, this argument
    specifies the line style for negative contours.

    If *negative_linestyles* is *None*, the default is taken from
    :rc:`contour.negative_linestyle`.

    *negative_linestyles* can also be an iterable of the above strings
    specifying a set of linestyles to be used. If this iterable is shorter than
    the number of contour levels it will be repeated as necessary.

hatches : list[str], optional
    *Only applies to* `.contourf`.

    A list of cross hatch patterns to use on the filled areas.
    If None, no hatching will be added to the contour.

algorithm : {'mpl2005', 'mpl2014', 'serial', 'threaded'}, optional
    Which contouring algorithm to use to calculate the contour lines and
    polygons. The algorithms are implemented in
    `ContourPy <https://github.com/contourpy/contourpy>`_, consult the
    `ContourPy documentation <https://contourpy.readthedocs.io>`_ for
    further information.

    The default is taken from :rc:`contour.algorithm`.

clip_path : `~matplotlib.patches.Patch` or `.Path` or `.TransformedPath`
    Set the clip path.  See `~matplotlib.artist.Artist.set_clip_path`.

    .. versionadded:: 3.8

data : indexable object, optional
    DATA_PARAMETER_PLACEHOLDER

Notes
-----
1. `.contourf` differs from the MATLAB version in that it does not draw
   the polygon edges. To draw edges, add line contours with calls to
   `.contour`.

2. `.contourf` fills intervals that are closed at the top; that is, for
   boundaries *z1* and *z2*, the filled region is::

      z1 < Z <= z2

   except for the lowest interval, which is closed on both sides (i.e.
   it includes the lowest value).

3. `.contour` and `.contourf` use a `marching squares
   <https://en.wikipedia.org/wiki/Marching_squares>`_ algorithm to
   compute contour locations.  More information can be found in
   `ContourPy documentation <https://contourpy.readthedocs.io>`_.
""" % _docstring.interpd.params)

# === NexusCore/openenv\Lib\site-packages\google\generativeai\types\retriever_types.py ===
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
import re
import abc
import dataclasses
from typing import Any, AsyncIterable, Optional, Union, Iterable, Mapping
from typing_extensions import deprecated  # type: ignore

import google.ai.generativelanguage as glm
from google.generativeai import protos

from google.protobuf import field_mask_pb2
from google.generativeai.client import get_default_retriever_client
from google.generativeai.client import get_default_retriever_async_client
from google.generativeai import string_utils
from google.generativeai.types import helper_types

from google.generativeai.types import permission_types
from google.generativeai.types.model_types import idecode_time
from google.generativeai.utils import flatten_update_paths

_VALID_NAME = r"[a-z0-9]([a-z0-9-]{0,38}[a-z0-9])$"
NAME_ERROR_MSG = """The `name` must consist of alphanumeric characters (or -) and be 40 or fewer characters; or be empty. The name you entered:
    len(name)== {length}
    name={name}
"""


def valid_name(name):
    return re.match(_VALID_NAME, name) and len(name) < 40


Operator = protos.Condition.Operator
State = protos.Chunk.State

OperatorOptions = Union[str, int, Operator]
StateOptions = Union[str, int, State]

ChunkOptions = Union[
    protos.Chunk,
    str,
    tuple[str, str],
    tuple[str, str, Any],
    Mapping[str, Any],
]  # fmt: no

BatchCreateChunkOptions = Union[
    protos.BatchCreateChunksRequest,
    Mapping[str, str],
    Mapping[str, tuple[str, str]],
    Iterable[ChunkOptions],
]  # fmt: no

UpdateChunkOptions = Union[protos.UpdateChunkRequest, Mapping[str, Any], tuple[str, Any]]

BatchUpdateChunksOptions = Union[protos.BatchUpdateChunksRequest, Iterable[UpdateChunkOptions]]

BatchDeleteChunkOptions = Union[list[protos.DeleteChunkRequest], Iterable[str]]

_OPERATOR: dict[OperatorOptions, Operator] = {
    Operator.OPERATOR_UNSPECIFIED: Operator.OPERATOR_UNSPECIFIED,
    0: Operator.OPERATOR_UNSPECIFIED,
    "operator_unspecified": Operator.OPERATOR_UNSPECIFIED,
    "unspecified": Operator.OPERATOR_UNSPECIFIED,
    Operator.LESS: Operator.LESS,
    1: Operator.LESS,
    "operator_less": Operator.LESS,
    "less": Operator.LESS,
    "<": Operator.LESS,
    Operator.LESS_EQUAL: Operator.LESS_EQUAL,
    2: Operator.LESS_EQUAL,
    "operator_less_equal": Operator.LESS_EQUAL,
    "less_equal": Operator.LESS_EQUAL,
    "<=": Operator.LESS_EQUAL,
    Operator.EQUAL: Operator.EQUAL,
    3: Operator.EQUAL,
    "operator_equal": Operator.EQUAL,
    "equal": Operator.EQUAL,
    "==": Operator.EQUAL,
    Operator.GREATER_EQUAL: Operator.GREATER_EQUAL,
    4: Operator.GREATER_EQUAL,
    "operator_greater_equal": Operator.GREATER_EQUAL,
    "greater_equal": Operator.GREATER_EQUAL,
    Operator.EQUAL: Operator.EQUAL,
    5: Operator.EQUAL,
    "operator_equal": Operator.EQUAL,
    "equal": Operator.EQUAL,
    "==": Operator.EQUAL,
    Operator.NOT_EQUAL: Operator.NOT_EQUAL,
    6: Operator.NOT_EQUAL,
    "operator_not_equal": Operator.NOT_EQUAL,
    "not_equal": Operator.NOT_EQUAL,
    "!=": Operator.NOT_EQUAL,
    Operator.INCLUDES: Operator.INCLUDES,
    7: Operator.INCLUDES,
    "operator_includes": Operator.INCLUDES,
    "includes": Operator.INCLUDES,
    Operator.EXCLUDES: Operator.EXCLUDES,
    8: Operator.EXCLUDES,
    "operator_excludes": Operator.EXCLUDES,
    "excludes": Operator.EXCLUDES,
    "not in": Operator.EXCLUDES,
}

_STATE: dict[StateOptions, State] = {
    State.STATE_UNSPECIFIED: State.STATE_UNSPECIFIED,
    0: State.STATE_UNSPECIFIED,
    "state_unspecifed": State.STATE_UNSPECIFIED,
    "unspecified": State.STATE_UNSPECIFIED,
    State.STATE_PENDING_PROCESSING: State.STATE_PENDING_PROCESSING,
    1: State.STATE_PENDING_PROCESSING,
    "pending_processing": State.STATE_PENDING_PROCESSING,
    "pending": State.STATE_PENDING_PROCESSING,
    State.STATE_ACTIVE: State.STATE_ACTIVE,
    2: State.STATE_ACTIVE,
    "state_active": State.STATE_ACTIVE,
    "active": State.STATE_ACTIVE,
    State.STATE_FAILED: State.STATE_FAILED,
    10: State.STATE_FAILED,
    "state_failed": State.STATE_FAILED,
    "failed": State.STATE_FAILED,
}


def to_operator(x: OperatorOptions) -> Operator:
    if isinstance(x, str):
        x = x.lower()
    return _OPERATOR[x]


def to_state(x: StateOptions) -> State:
    if isinstance(x, str):
        x = x.lower()
    return _STATE[x]


@string_utils.prettyprint
@dataclasses.dataclass
class MetadataFilter:
    key: str
    conditions: Iterable[Condition]

    def _to_proto(self):
        kwargs = {}
        conditions = []
        for c in self.conditions:
            if isinstance(c.value, str):
                kwargs["string_value"] = c.value
            elif isinstance(c.value, (int, float)):
                kwargs["numeric_value"] = float(c.value)
            else:
                raise ValueError(
                    f"Invalid value type: The value for the condition must be either a string or an integer/float. Received: '{c.value}' of type {type(c.value).__name__}."
                )
            kwargs["operation"] = c.operation

            condition = protos.Condition(**kwargs)
            conditions.append(condition)

        return protos.MetadataFilter(key=self.key, conditions=conditions)


@string_utils.prettyprint
@dataclasses.dataclass
class Condition:
    value: str | float
    operation: Operator


@string_utils.prettyprint
@dataclasses.dataclass
class CustomMetadata:
    key: str
    value: str | Iterable[str] | float

    def _to_proto(self):
        kwargs = {}
        if isinstance(self.value, str):
            kwargs["string_value"] = self.value
        elif isinstance(self.value, Iterable):
            if isinstance(self.value, Mapping):
                # If already converted to a protos.StringList, get the values
                kwargs["string_list_value"] = self.value
            else:
                kwargs["string_list_value"] = protos.StringList(values=self.value)
        elif isinstance(self.value, (int, float)):
            kwargs["numeric_value"] = float(self.value)
        else:
            raise ValueError(
                f"Invalid value type: The value for a custom_metadata specification must be either a list of string values, a string, or an integer/float. Received: '{self.value}' of type {type(self.value).__name__}."
            )
        return protos.CustomMetadata(key=self.key, **kwargs)

    @classmethod
    def _from_dict(cls, cm):
        key = cm["key"]
        value = (
            cm.get("value", None)
            or cm.get("string_value", None)
            or cm.get("string_list_value", None)
            or cm.get("numeric_value", None)
        )
        return cls(key=key, value=value)

    def _to_dict(self):
        proto = self._to_proto()
        return type(proto).to_dict(proto)


CustomMetadataOptions = Union[CustomMetadata, protos.CustomMetadata, dict]


def make_custom_metadata(cm: CustomMetadataOptions) -> CustomMetadata:
    if isinstance(cm, CustomMetadata):
        return cm

    if isinstance(cm, protos.CustomMetadata):
        cm = type(cm).to_dict(cm)

    if isinstance(cm, dict):
        return CustomMetadata._from_dict(cm)
    else:
        raise ValueError(  # nofmt
            f"Invalid input: Could not create a 'CustomMetadata' from the provided input. Received type: '{type(cm).__name__}', value: '{cm}'."
        )


@string_utils.prettyprint
@dataclasses.dataclass
class ChunkData:
    string_value: str


@string_utils.prettyprint
@dataclasses.dataclass()
class Corpus:
    """
    A `Corpus` is a collection of `Documents`.
    """

    name: str
    display_name: str
    create_time: datetime.datetime
    update_time: datetime.datetime

    @property
    def permissions(self) -> permission_types.Permissions:
        return permission_types.Permissions(self)

    def create_document(
        self,
        name: str | None = None,
        display_name: str | None = None,
        custom_metadata: Iterable[CustomMetadata] | None = None,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> Document:
        """
        Request to create a `Document`.

        Args:
            name: The `Document` resource name. The ID (name excluding the "corpora/*/documents/" prefix) can contain up to 40 characters
                that are lowercase alphanumeric or dashes (-). The ID cannot start or end with a dash.
            display_name: The human-readable display name for the `Document`.
            custom_metadata: User provided custom metadata stored as key-value pairs used for querying.
            request_options: Options for the request.

        Return:
            Document object with specified name or display name.

        Raises:
            ValueError: When the name is not specified or formatted incorrectly.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        # Handle the custom_metadata parameter
        c_data = []
        if custom_metadata:
            for cm in custom_metadata:
                c_data.append(cm._to_proto())

        if name is None:
            document = protos.Document(display_name=display_name, custom_metadata=c_data)
        elif valid_name(name):
            document = protos.Document(
                name=f"{self.name}/documents/{name}",
                display_name=display_name,
                custom_metadata=c_data,
            )
        else:
            raise ValueError(NAME_ERROR_MSG.format(length=len(name), name=name))

        request = protos.CreateDocumentRequest(parent=self.name, document=document)
        response = client.create_document(request, **request_options)
        return decode_document(response)

    async def create_document_async(
        self,
        name: str | None = None,
        display_name: str | None = None,
        custom_metadata: Iterable[CustomMetadata] | None = None,
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> Document:
        """This is the async version of `Corpus.create_document`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        # Handle the custom_metadata parameter
        c_data = []
        if custom_metadata:
            for cm in custom_metadata:
                c_data.append(cm._to_proto())

        if name is None:
            document = protos.Document(display_name=display_name, custom_metadata=c_data)
        elif valid_name(name):
            document = protos.Document(
                name=f"{self.name}/documents/{name}",
                display_name=display_name,
                custom_metadata=c_data,
            )
        else:
            raise ValueError(NAME_ERROR_MSG.format(length=len(name), name=name))

        request = protos.CreateDocumentRequest(parent=self.name, document=document)
        response = await client.create_document(request, **request_options)
        return decode_document(response)

    def get_document(
        self,
        name: str,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> Document:
        """
        Get information about a specific `Document`.

        Args:
            name: The `Document` name.
            request_options: Options for the request.

        Return:
            `Document` of interest.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        if "/" not in name:
            name = f"{self.name}/documents/{name}"

        request = protos.GetDocumentRequest(name=name)
        response = client.get_document(request, **request_options)
        return decode_document(response)

    async def get_document_async(
        self,
        name: str,
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> Document:
        """This is the async version of `Corpus.get_document`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        if "/" not in name:
            name = f"{self.name}/documents/{name}"

        request = protos.GetDocumentRequest(name=name)
        response = await client.get_document(request, **request_options)
        return decode_document(response)

    def _apply_update(self, path, value):
        parts = path.split(".")
        for part in parts[:-1]:
            self = getattr(self, part)
        setattr(self, parts[-1], value)

    def update(
        self,
        updates: dict[str, Any],
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """
        Update a list of fields for a specified `Corpus`.

        Args:
            updates: List of fields to update in a `Corpus`.
            request_options: Options for the request.

        Return:
            Updated version of the `Corpus` object.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        updates = flatten_update_paths(updates)
        # At this time, only `display_name` can be updated
        for item in updates:
            if item != "display_name":
                raise ValueError(
                    "Invalid operation: Currently, only the 'display_name' attribute can be updated for a 'Corpus'."
                )
        field_mask = field_mask_pb2.FieldMask()

        for path in updates.keys():
            field_mask.paths.append(path)
        for path, value in updates.items():
            self._apply_update(path, value)

        request = protos.UpdateCorpusRequest(corpus=self.to_dict(), update_mask=field_mask)
        client.update_corpus(request, **request_options)
        return self

    async def update_async(
        self,
        updates: dict[str, Any],
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """This is the async version of `Corpus.update`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        updates = flatten_update_paths(updates)
        # At this time, only `display_name` can be updated
        for item in updates:
            if item != "display_name":
                raise ValueError(
                    "Invalid operation: Currently, only the 'display_name' attribute can be updated for a 'Corpus'."
                )
        field_mask = field_mask_pb2.FieldMask()

        for path in updates.keys():
            field_mask.paths.append(path)
        for path, value in updates.items():
            self._apply_update(path, value)

        request = protos.UpdateCorpusRequest(corpus=self.to_dict(), update_mask=field_mask)
        await client.update_corpus(request, **request_options)
        return self

    def query(
        self,
        query: str,
        metadata_filters: Iterable[MetadataFilter] | None = None,
        results_count: int | None = None,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> Iterable[RelevantChunk]:
        """
        Query a corpus for information.

        Args:
            query: Query string to perform semantic search.
            metadata_filters: Filter for `Chunk` metadata.
            results_count: The maximum number of `Chunk`s to return; must be less than 100.
            request_options: Options for the request.

        Returns:
            List of relevant chunks.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        if results_count:
            if results_count > 100:
                raise ValueError(
                    "Invalid operation: The number of results returned must be between 1 and 100."
                )

        m_f_ = []
        if metadata_filters:
            for mf in metadata_filters:
                m_f_.append(mf._to_proto())

        request = protos.QueryCorpusRequest(
            name=self.name,
            query=query,
            metadata_filters=m_f_,
            results_count=results_count,
        )
        response = client.query_corpus(request, **request_options)
        response = type(response).to_dict(response)

        # Create a RelevantChunk object for each chunk listed in response['relevant_chunks']
        relevant_chunks = []
        for c in response["relevant_chunks"]:
            rc = RelevantChunk(
                chunk_relevance_score=c["chunk_relevance_score"], chunk=Chunk(**c["chunk"])
            )
            relevant_chunks.append(rc)

        return relevant_chunks

    async def query_async(
        self,
        query: str,
        metadata_filters: Iterable[MetadataFilter] | None = None,
        results_count: int | None = None,
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> Iterable[RelevantChunk]:
        """This is the async version of `Corpus.query`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        if results_count:
            if results_count > 100:
                raise ValueError(
                    "Invalid operation: The number of results returned must be between 1 and 100."
                )

        m_f_ = []
        if metadata_filters:
            for mf in metadata_filters:
                m_f_.append(mf._to_proto())

        request = protos.QueryCorpusRequest(
            name=self.name,
            query=query,
            metadata_filters=m_f_,
            results_count=results_count,
        )
        response = await client.query_corpus(request, **request_options)
        response = type(response).to_dict(response)

        # Create a RelevantChunk object for each chunk listed in response['relevant_chunks']
        relevant_chunks = []
        for c in response["relevant_chunks"]:
            rc = RelevantChunk(
                chunk_relevance_score=c["chunk_relevance_score"], chunk=Chunk(**c["chunk"])
            )
            relevant_chunks.append(rc)

        return relevant_chunks

    def delete_document(
        self,
        name: str,
        force: bool = False,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """
        Delete a document in the corpus.

        Args:
            name: The `Document` name.
            force: If set to true, any `Chunk`s and objects related to this `Document` will also be deleted.
            request_options: Options for the request.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        if "/" not in name:
            name = f"{self.name}/documents/{name}"

        request = protos.DeleteDocumentRequest(name=name, force=bool(force))
        client.delete_document(request, **request_options)

    async def delete_document_async(
        self,
        name: str,
        force: bool = False,
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """This is the async version of `Corpus.delete_document`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        if "/" not in name:
            name = f"{self.name}/documents/{name}"

        request = protos.DeleteDocumentRequest(name=name, force=bool(force))
        await client.delete_document(request, **request_options)

    def list_documents(
        self,
        page_size: int | None = None,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> Iterable[Document]:
        """
        List documents in corpus.

        Args:
            name: The name of the `Corpus` containing `Document`s.
            page_size: The maximum number of `Document`s to return (per page). The service may return fewer `Document`s.
            request_options: Options for the request.

        Return:
            Paginated list of `Document`s.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        request = protos.ListDocumentsRequest(
            parent=self.name,
            page_size=page_size,
        )
        for doc in client.list_documents(request, **request_options):
            yield decode_document(doc)

    async def list_documents_async(
        self,
        page_size: int | None = None,
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> AsyncIterable[Document]:
        """This is the async version of `Corpus.list_documents`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        request = protos.ListDocumentsRequest(
            parent=self.name,
            page_size=page_size,
        )
        async for doc in await client.list_documents(request, **request_options):
            yield decode_document(doc)

    # PERMISSIONS STUBS: ..deprecated:: >0.5.2
    @deprecated(
        "`Corpus.create_permission` is deprecated and will be removed in a future release. \
            Corpus permissions are now managed using the `permissions` property. Use `Corpus.permissions.create` instead."
    )
    def create_permission(
        self,
        role: permission_types.RoleOptions,
        grantee_type: Optional[permission_types.GranteeTypeOptions] = None,
        email_address: Optional[str] = None,
        client: glm.PermissionServiceClient | None = None,
    ) -> permission_types.Permission:
        return self.permissions.create(
            role=role, grantee_type=grantee_type, email_address=email_address, client=client
        )

    @deprecated(
        "`Corpus.create_permission_async` is deprecated and will be removed in a future release. \
            Corpus permissions are now managed using the `permissions` property. Use `Corpus.permissions.create_async` instead."
    )
    async def create_permission_async(
        self,
        role: permission_types.RoleOptions,
        grantee_type: Optional[permission_types.GranteeTypeOptions] = None,
        email_address: Optional[str] = None,
        client: glm.PermissionServiceAsyncClient | None = None,
    ) -> permission_types.Permission:
        return await self.permissions.create_async(
            role=role, grantee_type=grantee_type, email_address=email_address, client=client
        )

    @deprecated(
        "`Corpus.list_permission` is deprecated and will be removed in a future release. \
            Corpus permissions are now managed using the `permissions` property. Use `Corpus.permissions.list` instead."
    )
    def list_permissions(
        self,
        page_size: Optional[int] = None,
        client: glm.PermissionServiceClient | None = None,
    ) -> Iterable[permission_types.Permission]:
        return self.permissions.list(page_size=page_size, client=client)

    @deprecated(
        "`Corpus.list_permission_async` is deprecated and will be removed in a future release. \
            Corpus permissions are now managed using the `permissions` property. Use `Corpus.permissions.list_async` instead."
    )
    async def list_permissions_async(
        self,
        page_size: Optional[int] = None,
        client: glm.PermissionServiceAsyncClient | None = None,
    ) -> AsyncIterable[permission_types.Permission]:
        return self.permissions.list_async(page_size=page_size, client=client)

    # PERMISSIONS STUBS END

    def to_dict(self) -> dict[str, Any]:
        result = {"name": self.name, "display_name": self.display_name}
        return result


def decode_document(document):
    document = type(document).to_dict(document)
    idecode_time(document, "create_time")
    idecode_time(document, "update_time")
    return Document(**document)


@string_utils.prettyprint
@dataclasses.dataclass()
class Document(abc.ABC):
    """
    A `Document` is a collection of `Chunk`s.
    """

    name: str
    display_name: str
    custom_metadata: list[CustomMetadata]
    create_time: datetime.datetime
    update_time: datetime.datetime

    def create_chunk(
        self,
        data: str | ChunkData,
        name: str | None = None,
        custom_metadata: Iterable[CustomMetadata] | None = None,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> Chunk:
        """
        Create a `Chunk` object which has textual data.

        Args:
            data: The content for the `Chunk`, such as the text string.
            name: The `Chunk` resource name. The ID (name excluding the "corpora/*/documents/*/chunks/" prefix) can contain up to 40 characters that are lowercase alphanumeric or dashes (-).
            custom_metadata: User provided custom metadata stored as key-value pairs.
            state: States for the lifecycle of a `Chunk`.
            request_options: Options for the request.

        Return:
            `Chunk` object with specified data.

        Raises:
            ValueError when chunk name not specified correctly.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        # Handle the custom_metadata parameter
        c_data = []
        if custom_metadata:
            for cm in custom_metadata:
                c_data.append(cm._to_proto())

        if name is not None:
            if valid_name(name):
                chunk_name = f"{self.name}/chunks/{name}"
            else:
                raise ValueError(NAME_ERROR_MSG.format(length=len(name), name=name))
        else:
            chunk_name = name

        if isinstance(data, str):
            chunk = protos.Chunk(
                name=chunk_name, data={"string_value": data}, custom_metadata=c_data
            )
        else:
            chunk = protos.Chunk(
                name=chunk_name,
                data={"string_value": data.string_value},
                custom_metadata=c_data,
            )

        request = protos.CreateChunkRequest(parent=self.name, chunk=chunk)
        response = client.create_chunk(request, **request_options)
        return decode_chunk(response)

    async def create_chunk_async(
        self,
        data: str | ChunkData,
        name: str | None = None,
        custom_metadata: Iterable[CustomMetadata] | None = None,
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> Chunk:
        """This is the async version of `Document.create_chunk`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        # Handle the custom_metadata parameter
        c_data = []
        if custom_metadata:
            for cm in custom_metadata:
                c_data.append(cm._to_proto())

        if name is not None:
            if valid_name(name):
                chunk_name = f"{self.name}/chunks/{name}"
            else:
                raise ValueError(NAME_ERROR_MSG.format(length=len(name), name=name))
        else:
            chunk_name = name

        if isinstance(data, str):
            chunk = protos.Chunk(
                name=chunk_name, data={"string_value": data}, custom_metadata=c_data
            )
        else:
            chunk = protos.Chunk(
                name=chunk_name,
                data={"string_value": data.string_value},
                custom_metadata=c_data,
            )

        request = protos.CreateChunkRequest(parent=self.name, chunk=chunk)
        response = await client.create_chunk(request, **request_options)
        return decode_chunk(response)

    def _make_chunk(self, chunk: ChunkOptions) -> protos.Chunk:
        # del self
        if isinstance(chunk, protos.Chunk):
            return protos.Chunk(chunk)
        elif isinstance(chunk, str):
            return protos.Chunk(data={"string_value": chunk})
        elif isinstance(chunk, tuple):
            if len(chunk) == 2:
                name, data = chunk  # pytype: disable=bad-unpacking
                custom_metadata = None
            elif len(chunk) == 3:
                name, data, custom_metadata = chunk  # pytype: disable=bad-unpacking
            else:
                raise ValueError(
                    f"Tuples should have length 2 or 3, got length: {len(chunk)}\n"
                    f"value: {chunk}"
                )

            return protos.Chunk(
                name=name,
                data={"string_value": data},
                custom_metadata=custom_metadata,
            )
        elif isinstance(chunk, Mapping):
            if isinstance(chunk["data"], str):
                chunk = dict(chunk)
                chunk["data"] = {"string_value": chunk["data"]}
            return protos.Chunk(chunk)
        else:
            raise TypeError(
                f"Invalid input: Could not convert instance of type '{type(chunk).__name__}' to a chunk. Received value: '{chunk}'."
            )

    def _make_batch_create_chunk_request(
        self, chunks: BatchCreateChunkOptions
    ) -> protos.BatchCreateChunksRequest:
        if isinstance(chunks, protos.BatchCreateChunksRequest):
            return chunks

        if isinstance(chunks, Mapping):
            chunks = chunks.items()
            chunks = (
                # Flatten tuples
                (key,) + value if isinstance(value, tuple) else (key, value)
                for key, value in chunks
            )

        requests = []
        for i, chunk in enumerate(chunks):
            chunk = self._make_chunk(chunk)
            if chunk.name == "":
                chunk.name = str(i)

            chunk.name = f"{self.name}/chunks/{chunk.name}"

            requests.append(protos.CreateChunkRequest(parent=self.name, chunk=chunk))

        return protos.BatchCreateChunksRequest(parent=self.name, requests=requests)

    def batch_create_chunks(
        self,
        chunks: BatchCreateChunkOptions,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """
        Create chunks within the given document.

        Args:
            chunks: `Chunks` to create.
            request_options: Options for the request.

        Return:
            Information about the created chunks.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        request = self._make_batch_create_chunk_request(chunks)
        response = client.batch_create_chunks(request, **request_options)
        return [decode_chunk(chunk) for chunk in response.chunks]

    async def batch_create_chunks_async(
        self,
        chunks: BatchCreateChunkOptions,
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """This is the async version of `Document.batch_create_chunk`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        request = self._make_batch_create_chunk_request(chunks)
        response = await client.batch_create_chunks(request, **request_options)
        return [decode_chunk(chunk) for chunk in response.chunks]

    def get_chunk(
        self,
        name: str,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """
        Get information about a specific chunk.

        Args:
            name: Name of `Chunk`.
            request_options: Options for the request.

        Returns:
            `Chunk` that was requested.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        if "/" not in name:
            name = f"{self.name}/chunks/{name}"

        request = protos.GetChunkRequest(name=name)
        response = client.get_chunk(request, **request_options)
        return decode_chunk(response)

    async def get_chunk_async(
        self,
        name: str,
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """This is the async version of `Document.get_chunk`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        if "/" not in name:
            name = f"{self.name}/chunks/{name}"

        request = protos.GetChunkRequest(name=name)
        response = await client.get_chunk(request, **request_options)
        return decode_chunk(response)

    def list_chunks(
        self,
        page_size: int | None = None,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> Iterable[Chunk]:
        """
        List chunks of a document.

        Args:
            page_size: Maximum number of `Chunk`s to request.
            request_options: Options for the request.

        Return:
            List of chunks in the document.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        request = protos.ListChunksRequest(parent=self.name, page_size=page_size)
        for chunk in client.list_chunks(request, **request_options):
            yield decode_chunk(chunk)

    async def list_chunks_async(
        self,
        page_size: int | None = None,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> AsyncIterable[Chunk]:
        """This is the async version of `Document.list_chunks`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        request = protos.ListChunksRequest(parent=self.name, page_size=page_size)
        async for chunk in await client.list_chunks(request, **request_options):
            yield decode_chunk(chunk)

    def query(
        self,
        query: str,
        metadata_filters: Iterable[MetadataFilter] | None = None,
        results_count: int | None = None,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> list[RelevantChunk]:
        """
        Query a `Document` in the `Corpus` for information.

        Args:
            query: Query string to perform semantic search.
            metadata_filters: Filter for `Chunk` metadata.
            results_count: The maximum number of `Chunk`s to return.

        Returns:
            List of relevant chunks.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        if results_count:
            if results_count < 0 or results_count >= 100:
                raise ValueError(
                    "Invalid operation: The number of results returned must be between 1 and 100."
                )

        m_f_ = []
        if metadata_filters:
            for mf in metadata_filters:
                m_f_.append(mf._to_proto())

        request = protos.QueryDocumentRequest(
            name=self.name,
            query=query,
            metadata_filters=m_f_,
            results_count=results_count,
        )
        response = client.query_document(request, **request_options)
        response = type(response).to_dict(response)

        # Create a RelevantChunk object for each chunk listed in response['relevant_chunks']
        relevant_chunks = []
        for c in response["relevant_chunks"]:
            rc = RelevantChunk(
                chunk_relevance_score=c["chunk_relevance_score"], chunk=Chunk(**c["chunk"])
            )
            relevant_chunks.append(rc)

        return relevant_chunks

    async def query_async(
        self,
        query: str,
        metadata_filters: Iterable[MetadataFilter] | None = None,
        results_count: int | None = None,
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ) -> list[RelevantChunk]:
        """This is the async version of `Document.query`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        if results_count:
            if results_count < 0 or results_count >= 100:
                raise ValueError(
                    "Invalid operation: The number of results returned must be between 1 and 100."
                )

        m_f_ = []
        if metadata_filters:
            for mf in metadata_filters:
                m_f_.append(mf._to_proto())

        request = protos.QueryDocumentRequest(
            name=self.name,
            query=query,
            metadata_filters=m_f_,
            results_count=results_count,
        )
        response = await client.query_document(request, **request_options)
        response = type(response).to_dict(response)

        # Create a RelevantChunk object for each chunk listed in response['relevant_chunks']
        relevant_chunks = []
        for c in response["relevant_chunks"]:
            rc = RelevantChunk(
                chunk_relevance_score=c["chunk_relevance_score"], chunk=Chunk(**c["chunk"])
            )
            relevant_chunks.append(rc)

        return relevant_chunks

    def _apply_update(self, path, value):
        parts = path.split(".")
        for part in parts[:-1]:
            self = getattr(self, part)
        setattr(self, parts[-1], value)

    def update(
        self,
        updates: dict[str, Any],
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """
        Update a list of fields for a specified document.

        Args:
            updates: The list of fields to update.
            request_options: Options for the request.

        Return:
            `Chunk` object with specified updates.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        updates = flatten_update_paths(updates)
        # At this time, only `display_name` can be updated
        for item in updates:
            if item != "display_name":
                raise ValueError(
                    "Invalid operation: Currently, only the 'display_name' attribute can be updated for a 'Document'."
                )
        field_mask = field_mask_pb2.FieldMask()
        for path in updates.keys():
            field_mask.paths.append(path)
        for path, value in updates.items():
            self._apply_update(path, value)

        request = protos.UpdateDocumentRequest(document=self.to_dict(), update_mask=field_mask)
        client.update_document(request, **request_options)
        return self

    async def update_async(
        self,
        updates: dict[str, Any],
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """This is the async version of `Document.update`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        updates = flatten_update_paths(updates)
        # At this time, only `display_name` can be updated
        for item in updates:
            if item != "display_name":
                raise ValueError(
                    "Invalid operation: Currently, only the 'display_name' attribute can be updated for a 'Document'."
                )
        field_mask = field_mask_pb2.FieldMask()
        for path in updates.keys():
            field_mask.paths.append(path)
        for path, value in updates.items():
            self._apply_update(path, value)

        request = protos.UpdateDocumentRequest(document=self.to_dict(), update_mask=field_mask)
        await client.update_document(request, **request_options)
        return self

    def batch_update_chunks(
        self,
        chunks: BatchUpdateChunksOptions,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """
        Update multiple chunks within the same document.

        Args:
            chunks: Data structure specifying which `Chunk`s to update and what the required updates are.
            request_options: Options for the request.

        Return:
            Updated `Chunk`s.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        if isinstance(chunks, protos.BatchUpdateChunksRequest):
            response = client.batch_update_chunks(chunks)
            response = type(response).to_dict(response)
            return response

        _requests = []
        if isinstance(chunks, Mapping):
            # Key is name of chunk, value is a dictionary of updates
            for key, value in chunks.items():
                chunk_to_update = self.get_chunk(name=key)

                # Handle the custom_metadata parameter
                c_data = []
                if chunk_to_update.custom_metadata:
                    for cm in chunk_to_update.custom_metadata:
                        c_data.append(cm._to_proto())

                # When handling updates, use to the _to_proto result of the custom_metadata
                chunk_to_update.custom_metadata = c_data

                updates = flatten_update_paths(value)
                # At this time, only `data` can be updated
                for item in updates:
                    if item != "data.string_value":
                        raise ValueError(
                            f"Invalid operation: Currently, only the 'data' attribute can be updated for a 'Chunk'. Attempted to update '{item}'."
                        )
                field_mask = field_mask_pb2.FieldMask()
                for path in updates.keys():
                    field_mask.paths.append(path)
                for path, value in updates.items():
                    chunk_to_update._apply_update(path, value)
                _requests.append(
                    protos.UpdateChunkRequest(
                        chunk=chunk_to_update.to_dict(), update_mask=field_mask
                    )
                )
            request = protos.BatchUpdateChunksRequest(parent=self.name, requests=_requests)
            response = client.batch_update_chunks(request, **request_options)
            response = type(response).to_dict(response)
            return response
        if isinstance(chunks, Iterable) and not isinstance(chunks, Mapping):
            for chunk in chunks:
                if isinstance(chunk, protos.UpdateChunkRequest):
                    _requests.append(chunk)
                elif isinstance(chunk, tuple):
                    # First element is name of chunk, second element contains updates
                    chunk_to_update = self.get_chunk(name=chunk[0])

                    # Handle the custom_metadata parameter
                    c_data = []
                    if chunk_to_update.custom_metadata:
                        for cm in chunk_to_update.custom_metadata:
                            c_data.append(cm._to_proto())

                    # When handling updates, use to the _to_proto result of the custom_metadata
                    chunk_to_update.custom_metadata = c_data

                    updates = flatten_update_paths(chunk[1])
                    field_mask = field_mask_pb2.FieldMask()
                    for path in updates.keys():
                        field_mask.paths.append(path)
                    for path, value in updates.items():
                        chunk_to_update._apply_update(path, value)
                    _requests.append(
                        {"chunk": chunk_to_update.to_dict(), "update_mask": field_mask}
                    )
                else:
                    raise TypeError(
                        "Invalid input: The 'chunks' parameter must be a list of 'protos.UpdateChunkRequests',"
                        " dictionaries, or tuples of dictionaries."
                    )
            request = protos.BatchUpdateChunksRequest(parent=self.name, requests=_requests)
            response = client.batch_update_chunks(request, **request_options)
            response = type(response).to_dict(response)
            return response

    async def batch_update_chunks_async(
        self,
        chunks: BatchUpdateChunksOptions,
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """This is the async version of `Document.batch_update_chunks`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        if isinstance(chunks, protos.BatchUpdateChunksRequest):
            response = client.batch_update_chunks(chunks)
            response = type(response).to_dict(response)
            return response

        _requests = []
        if isinstance(chunks, Mapping):
            # Key is name of chunk, value is a dictionary of updates
            for key, value in chunks.items():
                chunk_to_update = self.get_chunk(name=key)

                # Handle the custom_metadata parameter
                c_data = []
                if chunk_to_update.custom_metadata:
                    for cm in chunk_to_update.custom_metadata:
                        c_data.append(cm._to_proto())

                # When handling updates, use to the _to_proto result of the custom_metadata
                chunk_to_update.custom_metadata = c_data

                updates = flatten_update_paths(value)
                # At this time, only `data` can be updated
                for item in updates:
                    if item != "data.string_value":
                        raise ValueError(
                            f"Invalid operation: Currently, only the 'data' attribute can be updated for a 'Chunk'. Attempted to update '{item}'."
                        )
                field_mask = field_mask_pb2.FieldMask()
                for path in updates.keys():
                    field_mask.paths.append(path)
                for path, value in updates.items():
                    chunk_to_update._apply_update(path, value)
                _requests.append(
                    protos.UpdateChunkRequest(
                        chunk=chunk_to_update.to_dict(), update_mask=field_mask
                    )
                )
            request = protos.BatchUpdateChunksRequest(parent=self.name, requests=_requests)
            response = await client.batch_update_chunks(request, **request_options)
            response = type(response).to_dict(response)
            return response
        if isinstance(chunks, Iterable) and not isinstance(chunks, Mapping):
            for chunk in chunks:
                if isinstance(chunk, protos.UpdateChunkRequest):
                    _requests.append(chunk)
                elif isinstance(chunk, tuple):
                    # First element is name of chunk, second element contains updates
                    chunk_to_update = self.get_chunk(name=chunk[0])

                    # Handle the custom_metadata parameter
                    c_data = []
                    if chunk_to_update.custom_metadata:
                        for cm in chunk_to_update.custom_metadata:
                            c_data.append(cm._to_proto())

                    # When handling updates, use to the _to_proto result of the custom_metadata
                    chunk_to_update.custom_metadata = c_data

                    updates = flatten_update_paths(chunk[1])
                    field_mask = field_mask_pb2.FieldMask()
                    for path in updates.keys():
                        field_mask.paths.append(path)
                    for path, value in updates.items():
                        chunk_to_update._apply_update(path, value)
                    _requests.append(
                        {"chunk": chunk_to_update.to_dict(), "update_mask": field_mask}
                    )
                else:
                    raise TypeError(
                        "Invalid input: The 'chunks' parameter must be a list of 'protos.UpdateChunkRequests', "
                        "dictionaries, or tuples of dictionaries."
                    )
            request = protos.BatchUpdateChunksRequest(parent=self.name, requests=_requests)
            response = await client.batch_update_chunks(request, **request_options)
            response = type(response).to_dict(response)
            return response

    def delete_chunk(
        self,
        name: str,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,  # fmt: {}
    ):
        """
        Delete a `Chunk`.

        Args:
            name: The `Chunk` name.
            request_options: Options for the request.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        if "/" not in name:
            name = f"{self.name}/chunks/{name}"

        request = protos.DeleteChunkRequest(name=name)
        client.delete_chunk(request, **request_options)

    async def delete_chunk_async(
        self,
        name: str,
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,  # fmt: {}
    ):
        """This is the async version of `Document.delete_chunk`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        if "/" not in name:
            name = f"{self.name}/chunks/{name}"

        request = protos.DeleteChunkRequest(name=name)
        await client.delete_chunk(request, **request_options)

    def batch_delete_chunks(
        self,
        chunks: BatchDeleteChunkOptions,
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """
        Delete multiple `Chunk`s from a document.

        Args:
            chunks: Names of `Chunks` to delete.
            request_options: Options for the request.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        if all(isinstance(x, protos.DeleteChunkRequest) for x in chunks):
            request = protos.BatchDeleteChunksRequest(parent=self.name, requests=chunks)
            client.batch_delete_chunks(request, **request_options)
        elif isinstance(chunks, Iterable):
            _request_list = []
            for chunk_name in chunks:
                _request_list.append(protos.DeleteChunkRequest(name=chunk_name))
            request = protos.BatchDeleteChunksRequest(parent=self.name, requests=_request_list)
            client.batch_delete_chunks(request, **request_options)
        else:
            raise ValueError(
                "Invalid operation: To delete chunks, you must pass in either the names of the chunks as an iterable, "
                "or multiple 'protos.DeleteChunkRequest's."
            )

    async def batch_delete_chunks_async(
        self,
        chunks: BatchDeleteChunkOptions,
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """This is the async version of `Document.batch_delete_chunks`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        if all(isinstance(x, protos.DeleteChunkRequest) for x in chunks):
            request = protos.BatchDeleteChunksRequest(parent=self.name, requests=chunks)
            await client.batch_delete_chunks(request, **request_options)
        elif isinstance(chunks, Iterable):
            _request_list = []
            for chunk_name in chunks:
                _request_list.append(protos.DeleteChunkRequest(name=chunk_name))
            request = protos.BatchDeleteChunksRequest(parent=self.name, requests=_request_list)
            await client.batch_delete_chunks(request, **request_options)
        else:
            raise ValueError(
                "Invalid operation: To delete chunks, you must pass in either the names of the chunks as an iterable, "
                "or multiple 'protos.DeleteChunkRequest's."
            )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "name": self.name,
            "display_name": self.display_name,
            "custom_metadata": self.custom_metadata,
        }
        return result


def decode_chunk(chunk: protos.Chunk) -> Chunk:
    chunk = type(chunk).to_dict(chunk)
    idecode_time(chunk, "create_time")
    idecode_time(chunk, "update_time")
    return Chunk(**chunk)


@string_utils.prettyprint
@dataclasses.dataclass
class RelevantChunk:
    chunk_relevance_score: float
    chunk: Chunk


@string_utils.prettyprint
@dataclasses.dataclass(init=False)
class Chunk(abc.ABC):
    """
    A `Chunk` is part of the `Document`, or the actual text.
    """

    name: str
    data: ChunkData
    custom_metadata: list[CustomMetadata] | None
    state: State
    create_time: datetime.datetime | None
    update_time: datetime.datetime | None

    def __init__(
        self,
        name: str,
        data: ChunkData | str,
        custom_metadata: Iterable[CustomMetadata] | None,
        state: State,
        create_time: datetime.datetime | str | None = None,
        update_time: datetime.datetime | str | None = None,
    ):
        self.name = name
        if isinstance(data, str):
            self.data = ChunkData(string_value=data)
        elif isinstance(data, dict):
            self.data = ChunkData(string_value=data["string_value"])

        if custom_metadata is None:
            self.custom_metadata = []
        else:
            self.custom_metadata = [make_custom_metadata(cm) for cm in custom_metadata]

        self.state = to_state(state)

        if create_time is None:
            self.create_time = None
        elif isinstance(create_time, datetime.datetime):
            self.create_time = create_time
        else:
            self.create_time = datetime.datetime.strptime(create_time, "%Y-%m-%dT%H:%M:%S.%fZ")

        if update_time is None:
            self.update_time = None
        elif isinstance(update_time, datetime.datetime):
            self.update_time = update_time
        else:
            self.update_time = datetime.datetime.strptime(update_time, "%Y-%m-%dT%H:%M:%S.%fZ")

    def _apply_update(self, path, value):
        parts = path.split(".")
        for part in parts[:-1]:
            self = getattr(self, part)
        setattr(self, parts[-1], value)

    def update(
        self,
        updates: dict[str, Any],
        client: glm.RetrieverServiceClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """
        Update a list of fields for a specified `Chunk`.

        Args:
            updates: List of fields to update for a `Chunk`.
            request_options: Options for the request.

        Return:
            Updated `Chunk` object.
        """
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_client()

        # Handle the custom_metadata parameter
        c_data = []
        if self.custom_metadata:
            for cm in self.custom_metadata:
                c_data.append(cm._to_proto())

        # When handling updates, use to the _to_proto result of the custom_metadata
        self.custom_metadata = c_data

        updates = flatten_update_paths(updates)
        # At this time, only `data` can be updated
        for item in updates:
            if item != "data.string_value":
                raise ValueError(
                    f"Invalid operation: Currently, only the 'data' attribute can be updated for a 'Chunk'. Attempted to update '{item}'."
                )
        field_mask = field_mask_pb2.FieldMask()

        for path in updates.keys():
            field_mask.paths.append(path)
        for path, value in updates.items():
            self._apply_update(path, value)
        request = protos.UpdateChunkRequest(chunk=self.to_dict(), update_mask=field_mask)

        client.update_chunk(request, **request_options)
        return self

    async def update_async(
        self,
        updates: dict[str, Any],
        client: glm.RetrieverServiceAsyncClient | None = None,
        request_options: helper_types.RequestOptionsType | None = None,
    ):
        """This is the async version of `Chunk.update`."""
        if request_options is None:
            request_options = {}

        if client is None:
            client = get_default_retriever_async_client()

        # Handle the custom_metadata parameter
        c_data = []
        if self.custom_metadata:
            for cm in self.custom_metadata:
                c_data.append(cm._to_proto())

        # When handling updates, use to the _to_proto result of the custom_metadata
        self.custom_metadata = c_data

        updates = flatten_update_paths(updates)
        # At this time, only `data` can be updated
        for item in updates:
            if item != "data.string_value":
                raise ValueError(
                    f"Invalid operation: Currently, only the 'data' attribute can be updated for a 'Chunk'. Attempted to update '{item}'."
                )
        field_mask = field_mask_pb2.FieldMask()

        for path in updates.keys():
            field_mask.paths.append(path)
        for path, value in updates.items():
            self._apply_update(path, value)
        request = protos.UpdateChunkRequest(chunk=self.to_dict(), update_mask=field_mask)

        await client.update_chunk(request, **request_options)
        return self

    def to_dict(self) -> dict[str, Any]:
        result = {
            "name": self.name,
            "data": dataclasses.asdict(self.data),
            "custom_metadata": [cm._to_dict() for cm in self.custom_metadata],
            "state": self.state,
        }
        return result