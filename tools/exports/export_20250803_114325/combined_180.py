
# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\layout.py ===
from abc import ABC, abstractmethod
from itertools import islice
from operator import itemgetter
from threading import RLock
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from ._ratio import ratio_resolve
from .align import Align
from .console import Console, ConsoleOptions, RenderableType, RenderResult
from .highlighter import ReprHighlighter
from .panel import Panel
from .pretty import Pretty
from .region import Region
from .repr import Result, rich_repr
from .segment import Segment
from .style import StyleType

if TYPE_CHECKING:
    from pip._vendor.rich.tree import Tree


class LayoutRender(NamedTuple):
    """An individual layout render."""

    region: Region
    render: List[List[Segment]]


RegionMap = Dict["Layout", Region]
RenderMap = Dict["Layout", LayoutRender]


class LayoutError(Exception):
    """Layout related error."""


class NoSplitter(LayoutError):
    """Requested splitter does not exist."""


class _Placeholder:
    """An internal renderable used as a Layout placeholder."""

    highlighter = ReprHighlighter()

    def __init__(self, layout: "Layout", style: StyleType = "") -> None:
        self.layout = layout
        self.style = style

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        width = options.max_width
        height = options.height or options.size.height
        layout = self.layout
        title = (
            f"{layout.name!r} ({width} x {height})"
            if layout.name
            else f"({width} x {height})"
        )
        yield Panel(
            Align.center(Pretty(layout), vertical="middle"),
            style=self.style,
            title=self.highlighter(title),
            border_style="blue",
            height=height,
        )


class Splitter(ABC):
    """Base class for a splitter."""

    name: str = ""

    @abstractmethod
    def get_tree_icon(self) -> str:
        """Get the icon (emoji) used in layout.tree"""

    @abstractmethod
    def divide(
        self, children: Sequence["Layout"], region: Region
    ) -> Iterable[Tuple["Layout", Region]]:
        """Divide a region amongst several child layouts.

        Args:
            children (Sequence(Layout)): A number of child layouts.
            region (Region): A rectangular region to divide.
        """


class RowSplitter(Splitter):
    """Split a layout region in to rows."""

    name = "row"

    def get_tree_icon(self) -> str:
        return "[layout.tree.row]⬌"

    def divide(
        self, children: Sequence["Layout"], region: Region
    ) -> Iterable[Tuple["Layout", Region]]:
        x, y, width, height = region
        render_widths = ratio_resolve(width, children)
        offset = 0
        _Region = Region
        for child, child_width in zip(children, render_widths):
            yield child, _Region(x + offset, y, child_width, height)
            offset += child_width


class ColumnSplitter(Splitter):
    """Split a layout region in to columns."""

    name = "column"

    def get_tree_icon(self) -> str:
        return "[layout.tree.column]⬍"

    def divide(
        self, children: Sequence["Layout"], region: Region
    ) -> Iterable[Tuple["Layout", Region]]:
        x, y, width, height = region
        render_heights = ratio_resolve(height, children)
        offset = 0
        _Region = Region
        for child, child_height in zip(children, render_heights):
            yield child, _Region(x, y + offset, width, child_height)
            offset += child_height


@rich_repr
class Layout:
    """A renderable to divide a fixed height in to rows or columns.

    Args:
        renderable (RenderableType, optional): Renderable content, or None for placeholder. Defaults to None.
        name (str, optional): Optional identifier for Layout. Defaults to None.
        size (int, optional): Optional fixed size of layout. Defaults to None.
        minimum_size (int, optional): Minimum size of layout. Defaults to 1.
        ratio (int, optional): Optional ratio for flexible layout. Defaults to 1.
        visible (bool, optional): Visibility of layout. Defaults to True.
    """

    splitters = {"row": RowSplitter, "column": ColumnSplitter}

    def __init__(
        self,
        renderable: Optional[RenderableType] = None,
        *,
        name: Optional[str] = None,
        size: Optional[int] = None,
        minimum_size: int = 1,
        ratio: int = 1,
        visible: bool = True,
    ) -> None:
        self._renderable = renderable or _Placeholder(self)
        self.size = size
        self.minimum_size = minimum_size
        self.ratio = ratio
        self.name = name
        self.visible = visible
        self.splitter: Splitter = self.splitters["column"]()
        self._children: List[Layout] = []
        self._render_map: RenderMap = {}
        self._lock = RLock()

    def __rich_repr__(self) -> Result:
        yield "name", self.name, None
        yield "size", self.size, None
        yield "minimum_size", self.minimum_size, 1
        yield "ratio", self.ratio, 1

    @property
    def renderable(self) -> RenderableType:
        """Layout renderable."""
        return self if self._children else self._renderable

    @property
    def children(self) -> List["Layout"]:
        """Gets (visible) layout children."""
        return [child for child in self._children if child.visible]

    @property
    def map(self) -> RenderMap:
        """Get a map of the last render."""
        return self._render_map

    def get(self, name: str) -> Optional["Layout"]:
        """Get a named layout, or None if it doesn't exist.

        Args:
            name (str): Name of layout.

        Returns:
            Optional[Layout]: Layout instance or None if no layout was found.
        """
        if self.name == name:
            return self
        else:
            for child in self._children:
                named_layout = child.get(name)
                if named_layout is not None:
                    return named_layout
        return None

    def __getitem__(self, name: str) -> "Layout":
        layout = self.get(name)
        if layout is None:
            raise KeyError(f"No layout with name {name!r}")
        return layout

    @property
    def tree(self) -> "Tree":
        """Get a tree renderable to show layout structure."""
        from pip._vendor.rich.styled import Styled
        from pip._vendor.rich.table import Table
        from pip._vendor.rich.tree import Tree

        def summary(layout: "Layout") -> Table:
            icon = layout.splitter.get_tree_icon()

            table = Table.grid(padding=(0, 1, 0, 0))

            text: RenderableType = (
                Pretty(layout) if layout.visible else Styled(Pretty(layout), "dim")
            )
            table.add_row(icon, text)
            _summary = table
            return _summary

        layout = self
        tree = Tree(
            summary(layout),
            guide_style=f"layout.tree.{layout.splitter.name}",
            highlight=True,
        )

        def recurse(tree: "Tree", layout: "Layout") -> None:
            for child in layout._children:
                recurse(
                    tree.add(
                        summary(child),
                        guide_style=f"layout.tree.{child.splitter.name}",
                    ),
                    child,
                )

        recurse(tree, self)
        return tree

    def split(
        self,
        *layouts: Union["Layout", RenderableType],
        splitter: Union[Splitter, str] = "column",
    ) -> None:
        """Split the layout in to multiple sub-layouts.

        Args:
            *layouts (Layout): Positional arguments should be (sub) Layout instances.
            splitter (Union[Splitter, str]): Splitter instance or name of splitter.
        """
        _layouts = [
            layout if isinstance(layout, Layout) else Layout(layout)
            for layout in layouts
        ]
        try:
            self.splitter = (
                splitter
                if isinstance(splitter, Splitter)
                else self.splitters[splitter]()
            )
        except KeyError:
            raise NoSplitter(f"No splitter called {splitter!r}")
        self._children[:] = _layouts

    def add_split(self, *layouts: Union["Layout", RenderableType]) -> None:
        """Add a new layout(s) to existing split.

        Args:
            *layouts (Union[Layout, RenderableType]): Positional arguments should be renderables or (sub) Layout instances.

        """
        _layouts = (
            layout if isinstance(layout, Layout) else Layout(layout)
            for layout in layouts
        )
        self._children.extend(_layouts)

    def split_row(self, *layouts: Union["Layout", RenderableType]) -> None:
        """Split the layout in to a row (layouts side by side).

        Args:
            *layouts (Layout): Positional arguments should be (sub) Layout instances.
        """
        self.split(*layouts, splitter="row")

    def split_column(self, *layouts: Union["Layout", RenderableType]) -> None:
        """Split the layout in to a column (layouts stacked on top of each other).

        Args:
            *layouts (Layout): Positional arguments should be (sub) Layout instances.
        """
        self.split(*layouts, splitter="column")

    def unsplit(self) -> None:
        """Reset splits to initial state."""
        del self._children[:]

    def update(self, renderable: RenderableType) -> None:
        """Update renderable.

        Args:
            renderable (RenderableType): New renderable object.
        """
        with self._lock:
            self._renderable = renderable

    def refresh_screen(self, console: "Console", layout_name: str) -> None:
        """Refresh a sub-layout.

        Args:
            console (Console): Console instance where Layout is to be rendered.
            layout_name (str): Name of layout.
        """
        with self._lock:
            layout = self[layout_name]
            region, _lines = self._render_map[layout]
            (x, y, width, height) = region
            lines = console.render_lines(
                layout, console.options.update_dimensions(width, height)
            )
            self._render_map[layout] = LayoutRender(region, lines)
            console.update_screen_lines(lines, x, y)

    def _make_region_map(self, width: int, height: int) -> RegionMap:
        """Create a dict that maps layout on to Region."""
        stack: List[Tuple[Layout, Region]] = [(self, Region(0, 0, width, height))]
        push = stack.append
        pop = stack.pop
        layout_regions: List[Tuple[Layout, Region]] = []
        append_layout_region = layout_regions.append
        while stack:
            append_layout_region(pop())
            layout, region = layout_regions[-1]
            children = layout.children
            if children:
                for child_and_region in layout.splitter.divide(children, region):
                    push(child_and_region)

        region_map = {
            layout: region
            for layout, region in sorted(layout_regions, key=itemgetter(1))
        }
        return region_map

    def render(self, console: Console, options: ConsoleOptions) -> RenderMap:
        """Render the sub_layouts.

        Args:
            console (Console): Console instance.
            options (ConsoleOptions): Console options.

        Returns:
            RenderMap: A dict that maps Layout on to a tuple of Region, lines
        """
        render_width = options.max_width
        render_height = options.height or console.height
        region_map = self._make_region_map(render_width, render_height)
        layout_regions = [
            (layout, region)
            for layout, region in region_map.items()
            if not layout.children
        ]
        render_map: Dict["Layout", "LayoutRender"] = {}
        render_lines = console.render_lines
        update_dimensions = options.update_dimensions

        for layout, region in layout_regions:
            lines = render_lines(
                layout.renderable, update_dimensions(region.width, region.height)
            )
            render_map[layout] = LayoutRender(region, lines)
        return render_map

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        with self._lock:
            width = options.max_width or console.width
            height = options.height or console.height
            render_map = self.render(console, options.update_dimensions(width, height))
            self._render_map = render_map
            layout_lines: List[List[Segment]] = [[] for _ in range(height)]
            _islice = islice
            for region, lines in render_map.values():
                _x, y, _layout_width, layout_height = region
                for row, line in zip(
                    _islice(layout_lines, y, y + layout_height), lines
                ):
                    row.extend(line)

            new_line = Segment.line()
            for layout_row in layout_lines:
                yield from layout_row
                yield new_line


if __name__ == "__main__":
    from pip._vendor.rich.console import Console

    console = Console()
    layout = Layout()

    layout.split_column(
        Layout(name="header", size=3),
        Layout(ratio=1, name="main"),
        Layout(size=10, name="footer"),
    )

    layout["main"].split_row(Layout(name="side"), Layout(name="body", ratio=2))

    layout["body"].split_row(Layout(name="content", ratio=2), Layout(name="s2"))

    layout["s2"].split_column(
        Layout(name="top"), Layout(name="middle"), Layout(name="bottom")
    )

    layout["side"].split_column(Layout(layout.tree, name="left1"), Layout(name="left2"))

    layout["content"].update("foo")

    console.print(layout)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\_local_folder.py ===
# coding=utf-8
# Copyright 2024-present, the HuggingFace Inc. team.
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
"""Contains utilities to handle the `../.cache/huggingface` folder in local directories.

First discussed in https://github.com/huggingface/huggingface_hub/issues/1738 to store
download metadata when downloading files from the hub to a local directory (without
using the cache).

./.cache/huggingface folder structure:
[4.0K]  data
├── [4.0K]  .cache
│   └── [4.0K]  huggingface
│       └── [4.0K]  download
│           ├── [  16]  file.parquet.metadata
│           ├── [  16]  file.txt.metadata
│           └── [4.0K]  folder
│               └── [  16]  file.parquet.metadata
│
├── [6.5G]  file.parquet
├── [1.5K]  file.txt
└── [4.0K]  folder
    └── [   16]  file.parquet


Download metadata file structure:
```
# file.txt.metadata
11c5a3d5811f50298f278a704980280950aedb10
a16a55fda99d2f2e7b69cce5cf93ff4ad3049930
1712656091.123

# file.parquet.metadata
11c5a3d5811f50298f278a704980280950aedb10
7c5d3f4b8b76583b422fcb9189ad6c89d5d97a094541ce8932dce3ecabde1421
1712656091.123
}
```
"""

import base64
import hashlib
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .utils import WeakFileLock


logger = logging.getLogger(__name__)


@dataclass
class LocalDownloadFilePaths:
    """
    Paths to the files related to a download process in a local dir.

    Returned by [`get_local_download_paths`].

    Attributes:
        file_path (`Path`):
            Path where the file will be saved.
        lock_path (`Path`):
            Path to the lock file used to ensure atomicity when reading/writing metadata.
        metadata_path (`Path`):
            Path to the metadata file.
    """

    file_path: Path
    lock_path: Path
    metadata_path: Path

    def incomplete_path(self, etag: str) -> Path:
        """Return the path where a file will be temporarily downloaded before being moved to `file_path`."""
        return self.metadata_path.parent / f"{_short_hash(self.metadata_path.name)}.{etag}.incomplete"


@dataclass(frozen=True)
class LocalUploadFilePaths:
    """
    Paths to the files related to an upload process in a local dir.

    Returned by [`get_local_upload_paths`].

    Attributes:
        path_in_repo (`str`):
            Path of the file in the repo.
        file_path (`Path`):
            Path where the file will be saved.
        lock_path (`Path`):
            Path to the lock file used to ensure atomicity when reading/writing metadata.
        metadata_path (`Path`):
            Path to the metadata file.
    """

    path_in_repo: str
    file_path: Path
    lock_path: Path
    metadata_path: Path


@dataclass
class LocalDownloadFileMetadata:
    """
    Metadata about a file in the local directory related to a download process.

    Attributes:
        filename (`str`):
            Path of the file in the repo.
        commit_hash (`str`):
            Commit hash of the file in the repo.
        etag (`str`):
            ETag of the file in the repo. Used to check if the file has changed.
            For LFS files, this is the sha256 of the file. For regular files, it corresponds to the git hash.
        timestamp (`int`):
            Unix timestamp of when the metadata was saved i.e. when the metadata was accurate.
    """

    filename: str
    commit_hash: str
    etag: str
    timestamp: float


@dataclass
class LocalUploadFileMetadata:
    """
    Metadata about a file in the local directory related to an upload process.
    """

    size: int

    # Default values correspond to "we don't know yet"
    timestamp: Optional[float] = None
    should_ignore: Optional[bool] = None
    sha256: Optional[str] = None
    upload_mode: Optional[str] = None
    remote_oid: Optional[str] = None
    is_uploaded: bool = False
    is_committed: bool = False

    def save(self, paths: LocalUploadFilePaths) -> None:
        """Save the metadata to disk."""
        with WeakFileLock(paths.lock_path):
            with paths.metadata_path.open("w") as f:
                new_timestamp = time.time()
                f.write(str(new_timestamp) + "\n")

                f.write(str(self.size))  # never None
                f.write("\n")

                if self.should_ignore is not None:
                    f.write(str(int(self.should_ignore)))
                f.write("\n")

                if self.sha256 is not None:
                    f.write(self.sha256)
                f.write("\n")

                if self.upload_mode is not None:
                    f.write(self.upload_mode)
                f.write("\n")

                if self.remote_oid is not None:
                    f.write(self.remote_oid)
                f.write("\n")

                f.write(str(int(self.is_uploaded)) + "\n")
                f.write(str(int(self.is_committed)) + "\n")

            self.timestamp = new_timestamp


def get_local_download_paths(local_dir: Path, filename: str) -> LocalDownloadFilePaths:
    """Compute paths to the files related to a download process.

    Folders containing the paths are all guaranteed to exist.

    Args:
        local_dir (`Path`):
            Path to the local directory in which files are downloaded.
        filename (`str`):
            Path of the file in the repo.

    Return:
        [`LocalDownloadFilePaths`]: the paths to the files (file_path, lock_path, metadata_path, incomplete_path).
    """
    # filename is the path in the Hub repository (separated by '/')
    # make sure to have a cross platform transcription
    sanitized_filename = os.path.join(*filename.split("/"))
    if os.name == "nt":
        if sanitized_filename.startswith("..\\") or "\\..\\" in sanitized_filename:
            raise ValueError(
                f"Invalid filename: cannot handle filename '{sanitized_filename}' on Windows. Please ask the repository"
                " owner to rename this file."
            )
    file_path = local_dir / sanitized_filename
    metadata_path = _huggingface_dir(local_dir) / "download" / f"{sanitized_filename}.metadata"
    lock_path = metadata_path.with_suffix(".lock")

    # Some Windows versions do not allow for paths longer than 255 characters.
    # In this case, we must specify it as an extended path by using the "\\?\" prefix
    if os.name == "nt":
        if not str(local_dir).startswith("\\\\?\\") and len(os.path.abspath(lock_path)) > 255:
            file_path = Path("\\\\?\\" + os.path.abspath(file_path))
            lock_path = Path("\\\\?\\" + os.path.abspath(lock_path))
            metadata_path = Path("\\\\?\\" + os.path.abspath(metadata_path))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    return LocalDownloadFilePaths(file_path=file_path, lock_path=lock_path, metadata_path=metadata_path)


def get_local_upload_paths(local_dir: Path, filename: str) -> LocalUploadFilePaths:
    """Compute paths to the files related to an upload process.

    Folders containing the paths are all guaranteed to exist.

    Args:
        local_dir (`Path`):
            Path to the local directory that is uploaded.
        filename (`str`):
            Path of the file in the repo.

    Return:
        [`LocalUploadFilePaths`]: the paths to the files (file_path, lock_path, metadata_path).
    """
    # filename is the path in the Hub repository (separated by '/')
    # make sure to have a cross platform transcription
    sanitized_filename = os.path.join(*filename.split("/"))
    if os.name == "nt":
        if sanitized_filename.startswith("..\\") or "\\..\\" in sanitized_filename:
            raise ValueError(
                f"Invalid filename: cannot handle filename '{sanitized_filename}' on Windows. Please ask the repository"
                " owner to rename this file."
            )
    file_path = local_dir / sanitized_filename
    metadata_path = _huggingface_dir(local_dir) / "upload" / f"{sanitized_filename}.metadata"
    lock_path = metadata_path.with_suffix(".lock")

    # Some Windows versions do not allow for paths longer than 255 characters.
    # In this case, we must specify it as an extended path by using the "\\?\" prefix
    if os.name == "nt":
        if not str(local_dir).startswith("\\\\?\\") and len(os.path.abspath(lock_path)) > 255:
            file_path = Path("\\\\?\\" + os.path.abspath(file_path))
            lock_path = Path("\\\\?\\" + os.path.abspath(lock_path))
            metadata_path = Path("\\\\?\\" + os.path.abspath(metadata_path))

    file_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    return LocalUploadFilePaths(
        path_in_repo=filename, file_path=file_path, lock_path=lock_path, metadata_path=metadata_path
    )


def read_download_metadata(local_dir: Path, filename: str) -> Optional[LocalDownloadFileMetadata]:
    """Read metadata about a file in the local directory related to a download process.

    Args:
        local_dir (`Path`):
            Path to the local directory in which files are downloaded.
        filename (`str`):
            Path of the file in the repo.

    Return:
        `[LocalDownloadFileMetadata]` or `None`: the metadata if it exists, `None` otherwise.
    """
    paths = get_local_download_paths(local_dir, filename)
    with WeakFileLock(paths.lock_path):
        if paths.metadata_path.exists():
            try:
                with paths.metadata_path.open() as f:
                    commit_hash = f.readline().strip()
                    etag = f.readline().strip()
                    timestamp = float(f.readline().strip())
                    metadata = LocalDownloadFileMetadata(
                        filename=filename,
                        commit_hash=commit_hash,
                        etag=etag,
                        timestamp=timestamp,
                    )
            except Exception as e:
                # remove the metadata file if it is corrupted / not the right format
                logger.warning(
                    f"Invalid metadata file {paths.metadata_path}: {e}. Removing it from disk and continue."
                )
                try:
                    paths.metadata_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove corrupted metadata file {paths.metadata_path}: {e}")

            try:
                # check if the file exists and hasn't been modified since the metadata was saved
                stat = paths.file_path.stat()
                if (
                    stat.st_mtime - 1 <= metadata.timestamp
                ):  # allow 1s difference as stat.st_mtime might not be precise
                    return metadata
                logger.info(f"Ignored metadata for '{filename}' (outdated). Will re-compute hash.")
            except FileNotFoundError:
                # file does not exist => metadata is outdated
                return None
    return None


def read_upload_metadata(local_dir: Path, filename: str) -> LocalUploadFileMetadata:
    """Read metadata about a file in the local directory related to an upload process.

    TODO: factorize logic with `read_download_metadata`.

    Args:
        local_dir (`Path`):
            Path to the local directory in which files are downloaded.
        filename (`str`):
            Path of the file in the repo.

    Return:
        `[LocalUploadFileMetadata]` or `None`: the metadata if it exists, `None` otherwise.
    """
    paths = get_local_upload_paths(local_dir, filename)
    with WeakFileLock(paths.lock_path):
        if paths.metadata_path.exists():
            try:
                with paths.metadata_path.open() as f:
                    timestamp = float(f.readline().strip())

                    size = int(f.readline().strip())  # never None

                    _should_ignore = f.readline().strip()
                    should_ignore = None if _should_ignore == "" else bool(int(_should_ignore))

                    _sha256 = f.readline().strip()
                    sha256 = None if _sha256 == "" else _sha256

                    _upload_mode = f.readline().strip()
                    upload_mode = None if _upload_mode == "" else _upload_mode
                    if upload_mode not in (None, "regular", "lfs"):
                        raise ValueError(f"Invalid upload mode in metadata {paths.path_in_repo}: {upload_mode}")

                    _remote_oid = f.readline().strip()
                    remote_oid = None if _remote_oid == "" else _remote_oid

                    is_uploaded = bool(int(f.readline().strip()))
                    is_committed = bool(int(f.readline().strip()))

                    metadata = LocalUploadFileMetadata(
                        timestamp=timestamp,
                        size=size,
                        should_ignore=should_ignore,
                        sha256=sha256,
                        upload_mode=upload_mode,
                        remote_oid=remote_oid,
                        is_uploaded=is_uploaded,
                        is_committed=is_committed,
                    )
            except Exception as e:
                # remove the metadata file if it is corrupted / not the right format
                logger.warning(
                    f"Invalid metadata file {paths.metadata_path}: {e}. Removing it from disk and continue."
                )
                try:
                    paths.metadata_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove corrupted metadata file {paths.metadata_path}: {e}")

            # TODO: can we do better?
            if (
                metadata.timestamp is not None
                and metadata.is_uploaded  # file was uploaded
                and not metadata.is_committed  # but not committed
                and time.time() - metadata.timestamp > 20 * 3600  # and it's been more than 20 hours
            ):  # => we consider it as garbage-collected by S3
                metadata.is_uploaded = False

            # check if the file exists and hasn't been modified since the metadata was saved
            try:
                if metadata.timestamp is not None and paths.file_path.stat().st_mtime <= metadata.timestamp:
                    return metadata
                logger.info(f"Ignored metadata for '{filename}' (outdated). Will re-compute hash.")
            except FileNotFoundError:
                # file does not exist => metadata is outdated
                pass

    # empty metadata => we don't know anything expect its size
    return LocalUploadFileMetadata(size=paths.file_path.stat().st_size)


def write_download_metadata(local_dir: Path, filename: str, commit_hash: str, etag: str) -> None:
    """Write metadata about a file in the local directory related to a download process.

    Args:
        local_dir (`Path`):
            Path to the local directory in which files are downloaded.
    """
    paths = get_local_download_paths(local_dir, filename)
    with WeakFileLock(paths.lock_path):
        with paths.metadata_path.open("w") as f:
            f.write(f"{commit_hash}\n{etag}\n{time.time()}\n")


def _huggingface_dir(local_dir: Path) -> Path:
    """Return the path to the `.cache/huggingface` directory in a local directory."""
    # Wrap in lru_cache to avoid overwriting the .gitignore file if called multiple times
    path = local_dir / ".cache" / "huggingface"
    path.mkdir(exist_ok=True, parents=True)

    # Create a .gitignore file in the .cache/huggingface directory if it doesn't exist
    # Should be thread-safe enough like this.
    gitignore = path / ".gitignore"
    gitignore_lock = path / ".gitignore.lock"
    if not gitignore.exists():
        try:
            with WeakFileLock(gitignore_lock, timeout=0.1):
                gitignore.write_text("*")
        except IndexError:
            pass
        except OSError:  # TimeoutError, FileNotFoundError, PermissionError, etc.
            pass
        try:
            gitignore_lock.unlink()
        except OSError:
            pass
    return path


def _short_hash(filename: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha1(filename.encode()).digest()).decode()

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\types\text_service.py ===
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
from __future__ import annotations

from typing import MutableMapping, MutableSequence

import proto  # type: ignore

from google.ai.generativelanguage_v1beta.types import citation, safety

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "GenerateTextRequest",
        "GenerateTextResponse",
        "TextPrompt",
        "TextCompletion",
        "EmbedTextRequest",
        "EmbedTextResponse",
        "BatchEmbedTextRequest",
        "BatchEmbedTextResponse",
        "Embedding",
        "CountTextTokensRequest",
        "CountTextTokensResponse",
    },
)


class GenerateTextRequest(proto.Message):
    r"""Request to generate a text completion response from the
    model.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        model (str):
            Required. The name of the ``Model`` or ``TunedModel`` to use
            for generating the completion. Examples:
            models/text-bison-001 tunedModels/sentence-translator-u3b7m
        prompt (google.ai.generativelanguage_v1beta.types.TextPrompt):
            Required. The free-form input text given to
            the model as a prompt.
            Given a prompt, the model will generate a
            TextCompletion response it predicts as the
            completion of the input text.
        temperature (float):
            Optional. Controls the randomness of the output. Note: The
            default value varies by model, see the ``Model.temperature``
            attribute of the ``Model`` returned the ``getModel``
            function.

            Values can range from [0.0,1.0], inclusive. A value closer
            to 1.0 will produce responses that are more varied and
            creative, while a value closer to 0.0 will typically result
            in more straightforward responses from the model.

            This field is a member of `oneof`_ ``_temperature``.
        candidate_count (int):
            Optional. Number of generated responses to return.

            This value must be between [1, 8], inclusive. If unset, this
            will default to 1.

            This field is a member of `oneof`_ ``_candidate_count``.
        max_output_tokens (int):
            Optional. The maximum number of tokens to include in a
            candidate.

            If unset, this will default to output_token_limit specified
            in the ``Model`` specification.

            This field is a member of `oneof`_ ``_max_output_tokens``.
        top_p (float):
            Optional. The maximum cumulative probability of tokens to
            consider when sampling.

            The model uses combined Top-k and nucleus sampling.

            Tokens are sorted based on their assigned probabilities so
            that only the most likely tokens are considered. Top-k
            sampling directly limits the maximum number of tokens to
            consider, while Nucleus sampling limits number of tokens
            based on the cumulative probability.

            Note: The default value varies by model, see the
            ``Model.top_p`` attribute of the ``Model`` returned the
            ``getModel`` function.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            Optional. The maximum number of tokens to consider when
            sampling.

            The model uses combined Top-k and nucleus sampling.

            Top-k sampling considers the set of ``top_k`` most probable
            tokens. Defaults to 40.

            Note: The default value varies by model, see the
            ``Model.top_k`` attribute of the ``Model`` returned the
            ``getModel`` function.

            This field is a member of `oneof`_ ``_top_k``.
        safety_settings (MutableSequence[google.ai.generativelanguage_v1beta.types.SafetySetting]):
            Optional. A list of unique ``SafetySetting`` instances for
            blocking unsafe content.

            that will be enforced on the ``GenerateTextRequest.prompt``
            and ``GenerateTextResponse.candidates``. There should not be
            more than one setting for each ``SafetyCategory`` type. The
            API will block any prompts and responses that fail to meet
            the thresholds set by these settings. This list overrides
            the default settings for each ``SafetyCategory`` specified
            in the safety_settings. If there is no ``SafetySetting`` for
            a given ``SafetyCategory`` provided in the list, the API
            will use the default safety setting for that category. Harm
            categories HARM_CATEGORY_DEROGATORY, HARM_CATEGORY_TOXICITY,
            HARM_CATEGORY_VIOLENCE, HARM_CATEGORY_SEXUAL,
            HARM_CATEGORY_MEDICAL, HARM_CATEGORY_DANGEROUS are supported
            in text service.
        stop_sequences (MutableSequence[str]):
            The set of character sequences (up to 5) that
            will stop output generation. If specified, the
            API will stop at the first appearance of a stop
            sequence. The stop sequence will not be included
            as part of the response.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    prompt: "TextPrompt" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="TextPrompt",
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=3,
        optional=True,
    )
    candidate_count: int = proto.Field(
        proto.INT32,
        number=4,
        optional=True,
    )
    max_output_tokens: int = proto.Field(
        proto.INT32,
        number=5,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=6,
        optional=True,
    )
    top_k: int = proto.Field(
        proto.INT32,
        number=7,
        optional=True,
    )
    safety_settings: MutableSequence[safety.SafetySetting] = proto.RepeatedField(
        proto.MESSAGE,
        number=8,
        message=safety.SafetySetting,
    )
    stop_sequences: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=9,
    )


class GenerateTextResponse(proto.Message):
    r"""The response from the model, including candidate completions.

    Attributes:
        candidates (MutableSequence[google.ai.generativelanguage_v1beta.types.TextCompletion]):
            Candidate responses from the model.
        filters (MutableSequence[google.ai.generativelanguage_v1beta.types.ContentFilter]):
            A set of content filtering metadata for the prompt and
            response text.

            This indicates which ``SafetyCategory``\ (s) blocked a
            candidate from this response, the lowest ``HarmProbability``
            that triggered a block, and the HarmThreshold setting for
            that category. This indicates the smallest change to the
            ``SafetySettings`` that would be necessary to unblock at
            least 1 response.

            The blocking is configured by the ``SafetySettings`` in the
            request (or the default ``SafetySettings`` of the API).
        safety_feedback (MutableSequence[google.ai.generativelanguage_v1beta.types.SafetyFeedback]):
            Returns any safety feedback related to
            content filtering.
    """

    candidates: MutableSequence["TextCompletion"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="TextCompletion",
    )
    filters: MutableSequence[safety.ContentFilter] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message=safety.ContentFilter,
    )
    safety_feedback: MutableSequence[safety.SafetyFeedback] = proto.RepeatedField(
        proto.MESSAGE,
        number=4,
        message=safety.SafetyFeedback,
    )


class TextPrompt(proto.Message):
    r"""Text given to the model as a prompt.

    The Model will use this TextPrompt to Generate a text
    completion.

    Attributes:
        text (str):
            Required. The prompt text.
    """

    text: str = proto.Field(
        proto.STRING,
        number=1,
    )


class TextCompletion(proto.Message):
    r"""Output text returned from a model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        output (str):
            Output only. The generated text returned from
            the model.
        safety_ratings (MutableSequence[google.ai.generativelanguage_v1beta.types.SafetyRating]):
            Ratings for the safety of a response.

            There is at most one rating per category.
        citation_metadata (google.ai.generativelanguage_v1beta.types.CitationMetadata):
            Output only. Citation information for model-generated
            ``output`` in this ``TextCompletion``.

            This field may be populated with attribution information for
            any text included in the ``output``.

            This field is a member of `oneof`_ ``_citation_metadata``.
    """

    output: str = proto.Field(
        proto.STRING,
        number=1,
    )
    safety_ratings: MutableSequence[safety.SafetyRating] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message=safety.SafetyRating,
    )
    citation_metadata: citation.CitationMetadata = proto.Field(
        proto.MESSAGE,
        number=3,
        optional=True,
        message=citation.CitationMetadata,
    )


class EmbedTextRequest(proto.Message):
    r"""Request to get a text embedding from the model.

    Attributes:
        model (str):
            Required. The model name to use with the
            format model=models/{model}.
        text (str):
            Optional. The free-form input text that the
            model will turn into an embedding.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    text: str = proto.Field(
        proto.STRING,
        number=2,
    )


class EmbedTextResponse(proto.Message):
    r"""The response to a EmbedTextRequest.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        embedding (google.ai.generativelanguage_v1beta.types.Embedding):
            Output only. The embedding generated from the
            input text.

            This field is a member of `oneof`_ ``_embedding``.
    """

    embedding: "Embedding" = proto.Field(
        proto.MESSAGE,
        number=1,
        optional=True,
        message="Embedding",
    )


class BatchEmbedTextRequest(proto.Message):
    r"""Batch request to get a text embedding from the model.

    Attributes:
        model (str):
            Required. The name of the ``Model`` to use for generating
            the embedding. Examples: models/embedding-gecko-001
        texts (MutableSequence[str]):
            Optional. The free-form input texts that the
            model will turn into an embedding. The current
            limit is 100 texts, over which an error will be
            thrown.
        requests (MutableSequence[google.ai.generativelanguage_v1beta.types.EmbedTextRequest]):
            Optional. Embed requests for the batch. Only one of
            ``texts`` or ``requests`` can be set.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    texts: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=2,
    )
    requests: MutableSequence["EmbedTextRequest"] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message="EmbedTextRequest",
    )


class BatchEmbedTextResponse(proto.Message):
    r"""The response to a EmbedTextRequest.

    Attributes:
        embeddings (MutableSequence[google.ai.generativelanguage_v1beta.types.Embedding]):
            Output only. The embeddings generated from
            the input text.
    """

    embeddings: MutableSequence["Embedding"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="Embedding",
    )


class Embedding(proto.Message):
    r"""A list of floats representing the embedding.

    Attributes:
        value (MutableSequence[float]):
            The embedding values.
    """

    value: MutableSequence[float] = proto.RepeatedField(
        proto.FLOAT,
        number=1,
    )


class CountTextTokensRequest(proto.Message):
    r"""Counts the number of tokens in the ``prompt`` sent to a model.

    Models may tokenize text differently, so each model may return a
    different ``token_count``.

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        prompt (google.ai.generativelanguage_v1beta.types.TextPrompt):
            Required. The free-form input text given to
            the model as a prompt.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    prompt: "TextPrompt" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="TextPrompt",
    )


class CountTextTokensResponse(proto.Message):
    r"""A response from ``CountTextTokens``.

    It returns the model's ``token_count`` for the ``prompt``.

    Attributes:
        token_count (int):
            The number of tokens that the ``model`` tokenizes the
            ``prompt`` into.

            Always non-negative.
    """

    token_count: int = proto.Field(
        proto.INT32,
        number=1,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/evaluation\evalplus\codegen\model.py ===
import json
import os
from abc import ABC, abstractmethod
from typing import List
from warnings import warn

import openai

try:
    import anthropic

    from evalplus.gen.util import anthropic_request
except ImportError:
    warn("Anthropic decoder will not work. Fix by `pip install anthropic`")

# mistral.ai
try:
    from mistralai.client import MistralClient
    from mistralai.models.chat_completion import ChatMessage
except ImportError:
    warn("MistralAI decoder will not work. Fix by `pip install mistralai`")

import torch
from stop_sequencer import StopSequencer
from transformers import AutoModelForCausalLM, AutoTokenizer

try:
    from vllm import LLM, SamplingParams
except ImportError:
    warn("VLLM decoder will not work. Fix by `pip install vllm`")

from evalplus.gen.util import openai_request

EOS = [
    "<|endoftext|>",
    "<|endofmask|>",
    "</s>",
    "\nif __name__",
    "\ndef main(",
    "\nprint(",
]


def extra_eos_for_direct_completion(dataset) -> List[str]:
    if dataset.lower() == "humaneval":
        return ["\ndef ", "\nclass ", "\nimport ", "\nfrom ", "\nassert "]
    elif dataset.lower() == "mbpp":
        return ['\n"""', "\nassert"]
    raise ValueError(f"Unknown dataset: {dataset}")


# some random words which serves as the splitter
_MAGIC_SPLITTER_ = "-[[]]-this-is-really-our-highest-priority-[[]]-"


def make_chat_prompt(prompt: str, tokenizer: AutoTokenizer) -> str:
    # directly return prompt if it does not have a tokenizer.chat_template
    if tokenizer.chat_template is None:
        return prompt

    prompt = f"""\
Please provide a self-contained Python script that solves the following problem in a markdown code block:
```
{prompt.strip()}
```
"""
    response = f"""\
Below is a Python script with a self-contained function that solves the problem and passes correpsonding tests:
```python
{_MAGIC_SPLITTER_}
```
"""
    prompt = tokenizer.apply_chat_template(
        [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response},
        ],
        tokenize=False,
    ).split(_MAGIC_SPLITTER_)[0]
    return prompt


class DecoderBase(ABC):
    def __init__(
        self,
        name: str,
        batch_size: int = 1,
        temperature: float = 0.8,
        max_new_tokens: int = 512,
        dtype: str = "bfloat16",  # default
        trust_remote_code: bool = False,
    ) -> None:
        print("Initializing a decoder model: {} ...".format(name))
        self.name = name
        self.batch_size = batch_size
        self.temperature = temperature
        self.eos = EOS
        self.skip_special_tokens = False
        self.max_new_tokens = max_new_tokens
        self.dtype = dtype
        self.trust_remote_code = trust_remote_code

    @abstractmethod
    def codegen(
        self, prompt: str, do_sample: bool = True, num_samples: int = 200
    ) -> List[str]:
        pass

    @abstractmethod
    def is_direct_completion(self) -> bool:
        pass

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


class VllmDecoder(DecoderBase):
    def __init__(self, name: str, dataset: str, tp: int, **kwargs) -> None:
        super().__init__(name, **kwargs)

        kwargs = {
            "tensor_parallel_size": int(os.getenv("VLLM_N_GPUS", tp)),
            "dtype": self.dtype,
            "trust_remote_code": self.trust_remote_code,
        }

        self.tokenizer = AutoTokenizer.from_pretrained(self.name)
        if self.tokenizer.chat_template is None:
            self.eos += extra_eos_for_direct_completion(dataset)
        self.llm = LLM(model=name, max_model_len=2048, **kwargs)

    def is_direct_completion(self) -> bool:
        return self.tokenizer.chat_template is None

    def codegen(
        self, prompt: str, do_sample: bool = True, num_samples: int = 200
    ) -> List[str]:
        if do_sample:
            assert self.temperature > 0, "Temperature must be greater than 0!"
        batch_size = min(self.batch_size, num_samples)

        vllm_outputs = self.llm.generate(
            [prompt] * batch_size,
            SamplingParams(
                temperature=self.temperature,
                max_tokens=self.max_new_tokens,
                top_p=0.95 if do_sample else 1.0,
                stop=self.eos,
            ),
            use_tqdm=False,
        )

        gen_strs = [x.outputs[0].text.replace("\t", "    ") for x in vllm_outputs]
        return gen_strs


class GeneralVllmDecoder(VllmDecoder):
    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.eos += ["\n```\n"]
        print(f"EOS strings: {self.eos}")

    def codegen(
        self, prompt: str, do_sample: bool = True, num_samples: int = 200
    ) -> List[str]:
        prompt = make_chat_prompt(prompt, self.tokenizer)
        return VllmDecoder.codegen(self, prompt, do_sample, num_samples)


class HfTorchDecoder(DecoderBase):
    def __init__(self, name: str, dataset: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        kwargs = {}
        kwargs["device_map"] = "auto"
        kwargs["trust_remote_code"] = self.trust_remote_code
        # string to torch dtype
        kwargs["torch_dtype"] = getattr(torch, self.dtype)
        self.skip_special_tokens = True

        print(f"{kwargs = }")

        self.tokenizer = AutoTokenizer.from_pretrained(name)
        if self.tokenizer.chat_template is None:
            self.eos += extra_eos_for_direct_completion(dataset)

        self.model = AutoModelForCausalLM.from_pretrained(name, **kwargs)
        self.model = self.model.to(self.device)

    def is_direct_completion(self) -> bool:
        return self.tokenizer.chat_template is not None

    @torch.inference_mode()
    def codegen(
        self, prompt: str, do_sample: bool = True, num_samples: int = 200
    ) -> List[str]:
        if self.temperature == 0:
            assert not do_sample
            assert num_samples == 1

        input_tokens = self.tokenizer.encode(prompt, return_tensors="pt").to(
            self.device
        )
        kwargs = {}
        if do_sample:
            kwargs["top_p"] = 0.95
            kwargs["temperature"] = self.temperature

        stop_sequencer = StopSequencer(
            self.model,
            model_type="causal",  # or seq2seq
            tokenizer=self.tokenizer,
        )

        model = stop_sequencer.register_stop_texts(
            stop_texts=self.eos,
            input_length=input_tokens.size(-1),
        )

        outputs = model.generate(
            input_tokens,
            max_new_tokens=self.max_new_tokens,
            do_sample=do_sample,
            num_return_sequences=min(self.batch_size, num_samples),
            pad_token_id=self.tokenizer.eos_token_id,
            **kwargs,
        )

        gen_strs = self.tokenizer.batch_decode(
            outputs[:, input_tokens.size(-1) :],
            skip_special_tokens=self.skip_special_tokens,
        )
        outputs = []
        # removes eos tokens.
        for output in gen_strs:
            min_index = 10000
            for eos in self.eos:
                if eos in output:
                    min_index = min(min_index, output.index(eos))
            outputs.append(output[:min_index].replace("\t", "    "))
        return outputs


class GenenralHfTorchDecoder(HfTorchDecoder):
    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self.eos += ["\n```\n"]
        print(f"EOS strings: {self.eos}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.name)

    def codegen(
        self, prompt: str, do_sample: bool = True, num_samples: int = 200
    ) -> List[str]:
        prompt = make_chat_prompt(prompt, self.tokenizer)
        return HfTorchDecoder.codegen(self, prompt, do_sample, num_samples)


class OpenAIChatDecoder(DecoderBase):
    def __init__(self, name: str, base_url=None, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.client = openai.OpenAI(base_url=base_url)

    def codegen(
        self, prompt: str, do_sample: bool = True, num_samples: int = 200
    ) -> List[str]:
        if do_sample:
            assert self.temperature > 0, "Temperature must be positive for sampling"
        batch_size = min(self.batch_size, num_samples)

        # construct prompt
        fmt = "json_object" if self.name == "gpt-4-1106-preview" else "text"
        if fmt == "json_object":
            message = r'Please complete the following code snippet by generating JSON like {"code": ""}'
        else:
            message = r"Please generate code to complete the following problem:"

        message += f"\n```python\n{prompt.strip()}\n```"

        ret = openai_request.make_auto_request(
            self.client,
            message=message,
            model=self.name,
            max_tokens=self.max_new_tokens,
            temperature=self.temperature,
            n=batch_size,
            response_format={"type": fmt},
        )

        outputs = []
        for item in ret.choices:
            content = item.message.content
            # if json serializable
            if fmt == "json_object":
                try:
                    json_data = json.loads(content)
                    if json_data.get("code", None) is not None:
                        outputs.append(prompt + "\n" + json_data["code"])
                        continue

                    print(f"'code' field not found in: {json_data}")
                except Exception as e:
                    print(e)
            outputs.append(content)

        return outputs

    def is_direct_completion(self) -> bool:
        return False


class MistralChatDecoder(DecoderBase):
    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.client = MistralClient(api_key=os.getenv("MISTRAL_API_KEY"))

    def codegen(
        self, prompt: str, do_sample: bool = True, num_samples: int = 200
    ) -> List[str]:
        kwargs = {}
        if do_sample:
            assert self.temperature > 0, "Temperature must be positive for sampling"
            kwargs["top_p"] = 0.95
            kwargs["temperature"] = self.temperature
        else:
            self.temperature = 0

        batch_size = min(self.batch_size, num_samples)

        outputs = []
        for _ in range(batch_size):
            ret = self.client.chat(
                model=self.name,
                messages=[
                    ChatMessage(
                        role="user",
                        content="Please generate code to solve the following problem in a Python markdown block:"
                        + f"\n```python\n{prompt.strip()}\n```",
                    )
                ],
                max_tokens=self.max_new_tokens,
                **kwargs,
            )

            outputs.append(ret.choices[0].message.content)

        return outputs

    def is_direct_completion(self) -> bool:
        return False


class AnthropicDecoder(DecoderBase, ABC):
    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_KEY"))

    def is_direct_completion(self) -> bool:
        return False


class AnthropicMessageDecoder(AnthropicDecoder):
    def codegen(
        self, prompt: str, do_sample: bool = True, num_samples: int = 200
    ) -> List[str]:
        if do_sample:
            assert self.temperature > 0, "Temperature must be positive for sampling"

        batch_size = min(self.batch_size, num_samples)
        if not do_sample:
            assert batch_size == 1, "Sampling only supports batch size of 1"

        outputs = []
        for _ in range(batch_size):
            message = anthropic_request.make_auto_request(
                client=self.client,
                model=self.name,
                messages=[
                    {
                        "role": "user",
                        "content": "Please generate code to complete the following problem wrapped in a Python markdown block:"
                        + f"\n```python\n{prompt.strip()}\n```\n",
                    }
                ],
                max_tokens=self.max_new_tokens,
                temperature=self.temperature,
                stop_sequences=["\n```\n", "\nif "],
            )
            outputs.append(message.content[0].text)

        return outputs


def make_model(
    model: str,
    backend: str,
    dataset: str,
    batch_size: int = 1,
    temperature: float = 0.0,
    tp=1,
    base_url=None,
):
    if backend == "vllm":
        return GeneralVllmDecoder(
            name=model,
            batch_size=batch_size,
            temperature=temperature,
            dataset=dataset,
            tp=tp,
        )
    elif backend == "hf":
        return GenenralHfTorchDecoder(
            name=model,
            batch_size=batch_size,
            temperature=temperature,
            dataset=dataset,
        )
    elif backend == "openai":
        return OpenAIChatDecoder(
            name=model,
            batch_size=batch_size,
            temperature=temperature,
            base_url=base_url,
        )
    elif backend == "mistral":
        return MistralChatDecoder(
            name=model,
            batch_size=batch_size,
            temperature=temperature,
        )
    elif backend == "anthropic":
        return AnthropicMessageDecoder(
            name=model,
            batch_size=batch_size,
            temperature=temperature,
        )

# === NexusCore/openenv\Lib\site-packages\fontTools\afmLib.py ===
"""Module for reading and writing AFM (Adobe Font Metrics) files.

Note that this has been designed to read in AFM files generated by Fontographer
and has not been tested on many other files. In particular, it does not
implement the whole Adobe AFM specification [#f1]_ but, it should read most
"common" AFM files.

Here is an example of using `afmLib` to read, modify and write an AFM file:

	>>> from fontTools.afmLib import AFM
	>>> f = AFM("Tests/afmLib/data/TestAFM.afm")
	>>>
	>>> # Accessing a pair gets you the kern value
	>>> f[("V","A")]
	-60
	>>>
	>>> # Accessing a glyph name gets you metrics
	>>> f["A"]
	(65, 668, (8, -25, 660, 666))
	>>> # (charnum, width, bounding box)
	>>>
	>>> # Accessing an attribute gets you metadata
	>>> f.FontName
	'TestFont-Regular'
	>>> f.FamilyName
	'TestFont'
	>>> f.Weight
	'Regular'
	>>> f.XHeight
	500
	>>> f.Ascender
	750
	>>>
	>>> # Attributes and items can also be set
	>>> f[("A","V")] = -150 # Tighten kerning
	>>> f.FontName = "TestFont Squished"
	>>>
	>>> # And the font written out again (remove the # in front)
	>>> #f.write("testfont-squished.afm")

.. rubric:: Footnotes

.. [#f1] `Adobe Technote 5004 <https://www.adobe.com/content/dam/acom/en/devnet/font/pdfs/5004.AFM_Spec.pdf>`_,
   Adobe Font Metrics File Format Specification.

"""

import re

# every single line starts with a "word"
identifierRE = re.compile(r"^([A-Za-z]+).*")

# regular expression to parse char lines
charRE = re.compile(
    r"(-?\d+)"  # charnum
    r"\s*;\s*WX\s+"  # ; WX
    r"(-?\d+)"  # width
    r"\s*;\s*N\s+"  # ; N
    r"([.A-Za-z0-9_]+)"  # charname
    r"\s*;\s*B\s+"  # ; B
    r"(-?\d+)"  # left
    r"\s+"
    r"(-?\d+)"  # bottom
    r"\s+"
    r"(-?\d+)"  # right
    r"\s+"
    r"(-?\d+)"  # top
    r"\s*;\s*"  # ;
)

# regular expression to parse kerning lines
kernRE = re.compile(
    r"([.A-Za-z0-9_]+)"  # leftchar
    r"\s+"
    r"([.A-Za-z0-9_]+)"  # rightchar
    r"\s+"
    r"(-?\d+)"  # value
    r"\s*"
)

# regular expressions to parse composite info lines of the form:
# Aacute 2 ; PCC A 0 0 ; PCC acute 182 211 ;
compositeRE = re.compile(
    r"([.A-Za-z0-9_]+)"  # char name
    r"\s+"
    r"(\d+)"  # number of parts
    r"\s*;\s*"
)
componentRE = re.compile(
    r"PCC\s+"  # PPC
    r"([.A-Za-z0-9_]+)"  # base char name
    r"\s+"
    r"(-?\d+)"  # x offset
    r"\s+"
    r"(-?\d+)"  # y offset
    r"\s*;\s*"
)

preferredAttributeOrder = [
    "FontName",
    "FullName",
    "FamilyName",
    "Weight",
    "ItalicAngle",
    "IsFixedPitch",
    "FontBBox",
    "UnderlinePosition",
    "UnderlineThickness",
    "Version",
    "Notice",
    "EncodingScheme",
    "CapHeight",
    "XHeight",
    "Ascender",
    "Descender",
]


class error(Exception):
    pass


class AFM(object):
    _attrs = None

    _keywords = [
        "StartFontMetrics",
        "EndFontMetrics",
        "StartCharMetrics",
        "EndCharMetrics",
        "StartKernData",
        "StartKernPairs",
        "EndKernPairs",
        "EndKernData",
        "StartComposites",
        "EndComposites",
    ]

    def __init__(self, path=None):
        """AFM file reader.

        Instantiating an object with a path name will cause the file to be opened,
        read, and parsed. Alternatively the path can be left unspecified, and a
        file can be parsed later with the :meth:`read` method."""
        self._attrs = {}
        self._chars = {}
        self._kerning = {}
        self._index = {}
        self._comments = []
        self._composites = {}
        if path is not None:
            self.read(path)

    def read(self, path):
        """Opens, reads and parses a file."""
        lines = readlines(path)
        for line in lines:
            if not line.strip():
                continue
            m = identifierRE.match(line)
            if m is None:
                raise error("syntax error in AFM file: " + repr(line))

            pos = m.regs[1][1]
            word = line[:pos]
            rest = line[pos:].strip()
            if word in self._keywords:
                continue
            if word == "C":
                self.parsechar(rest)
            elif word == "KPX":
                self.parsekernpair(rest)
            elif word == "CC":
                self.parsecomposite(rest)
            else:
                self.parseattr(word, rest)

    def parsechar(self, rest):
        m = charRE.match(rest)
        if m is None:
            raise error("syntax error in AFM file: " + repr(rest))
        things = []
        for fr, to in m.regs[1:]:
            things.append(rest[fr:to])
        charname = things[2]
        del things[2]
        charnum, width, l, b, r, t = (int(thing) for thing in things)
        self._chars[charname] = charnum, width, (l, b, r, t)

    def parsekernpair(self, rest):
        m = kernRE.match(rest)
        if m is None:
            raise error("syntax error in AFM file: " + repr(rest))
        things = []
        for fr, to in m.regs[1:]:
            things.append(rest[fr:to])
        leftchar, rightchar, value = things
        value = int(value)
        self._kerning[(leftchar, rightchar)] = value

    def parseattr(self, word, rest):
        if word == "FontBBox":
            l, b, r, t = [int(thing) for thing in rest.split()]
            self._attrs[word] = l, b, r, t
        elif word == "Comment":
            self._comments.append(rest)
        else:
            try:
                value = int(rest)
            except (ValueError, OverflowError):
                self._attrs[word] = rest
            else:
                self._attrs[word] = value

    def parsecomposite(self, rest):
        m = compositeRE.match(rest)
        if m is None:
            raise error("syntax error in AFM file: " + repr(rest))
        charname = m.group(1)
        ncomponents = int(m.group(2))
        rest = rest[m.regs[0][1] :]
        components = []
        while True:
            m = componentRE.match(rest)
            if m is None:
                raise error("syntax error in AFM file: " + repr(rest))
            basechar = m.group(1)
            xoffset = int(m.group(2))
            yoffset = int(m.group(3))
            components.append((basechar, xoffset, yoffset))
            rest = rest[m.regs[0][1] :]
            if not rest:
                break
        assert len(components) == ncomponents
        self._composites[charname] = components

    def write(self, path, sep="\r"):
        """Writes out an AFM font to the given path."""
        import time

        lines = [
            "StartFontMetrics 2.0",
            "Comment Generated by afmLib; at %s"
            % (time.strftime("%m/%d/%Y %H:%M:%S", time.localtime(time.time()))),
        ]

        # write comments, assuming (possibly wrongly!) they should
        # all appear at the top
        for comment in self._comments:
            lines.append("Comment " + comment)

        # write attributes, first the ones we know about, in
        # a preferred order
        attrs = self._attrs
        for attr in preferredAttributeOrder:
            if attr in attrs:
                value = attrs[attr]
                if attr == "FontBBox":
                    value = "%s %s %s %s" % value
                lines.append(attr + " " + str(value))
        # then write the attributes we don't know about,
        # in alphabetical order
        items = sorted(attrs.items())
        for attr, value in items:
            if attr in preferredAttributeOrder:
                continue
            lines.append(attr + " " + str(value))

        # write char metrics
        lines.append("StartCharMetrics " + repr(len(self._chars)))
        items = [
            (charnum, (charname, width, box))
            for charname, (charnum, width, box) in self._chars.items()
        ]

        def myKey(a):
            """Custom key function to make sure unencoded chars (-1)
            end up at the end of the list after sorting."""
            if a[0] == -1:
                a = (0xFFFF,) + a[1:]  # 0xffff is an arbitrary large number
            return a

        items.sort(key=myKey)

        for charnum, (charname, width, (l, b, r, t)) in items:
            lines.append(
                "C %d ; WX %d ; N %s ; B %d %d %d %d ;"
                % (charnum, width, charname, l, b, r, t)
            )
        lines.append("EndCharMetrics")

        # write kerning info
        lines.append("StartKernData")
        lines.append("StartKernPairs " + repr(len(self._kerning)))
        items = sorted(self._kerning.items())
        for (leftchar, rightchar), value in items:
            lines.append("KPX %s %s %d" % (leftchar, rightchar, value))
        lines.append("EndKernPairs")
        lines.append("EndKernData")

        if self._composites:
            composites = sorted(self._composites.items())
            lines.append("StartComposites %s" % len(self._composites))
            for charname, components in composites:
                line = "CC %s %s ;" % (charname, len(components))
                for basechar, xoffset, yoffset in components:
                    line = line + " PCC %s %s %s ;" % (basechar, xoffset, yoffset)
                lines.append(line)
            lines.append("EndComposites")

        lines.append("EndFontMetrics")

        writelines(path, lines, sep)

    def has_kernpair(self, pair):
        """Returns `True` if the given glyph pair (specified as a tuple) exists
        in the kerning dictionary."""
        return pair in self._kerning

    def kernpairs(self):
        """Returns a list of all kern pairs in the kerning dictionary."""
        return list(self._kerning.keys())

    def has_char(self, char):
        """Returns `True` if the given glyph exists in the font."""
        return char in self._chars

    def chars(self):
        """Returns a list of all glyph names in the font."""
        return list(self._chars.keys())

    def comments(self):
        """Returns all comments from the file."""
        return self._comments

    def addComment(self, comment):
        """Adds a new comment to the file."""
        self._comments.append(comment)

    def addComposite(self, glyphName, components):
        """Specifies that the glyph `glyphName` is made up of the given components.
        The components list should be of the following form::

                [
                        (glyphname, xOffset, yOffset),
                        ...
                ]

        """
        self._composites[glyphName] = components

    def __getattr__(self, attr):
        if attr in self._attrs:
            return self._attrs[attr]
        else:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        # all attrs *not* starting with "_" are consider to be AFM keywords
        if attr[:1] == "_":
            self.__dict__[attr] = value
        else:
            self._attrs[attr] = value

    def __delattr__(self, attr):
        # all attrs *not* starting with "_" are consider to be AFM keywords
        if attr[:1] == "_":
            try:
                del self.__dict__[attr]
            except KeyError:
                raise AttributeError(attr)
        else:
            try:
                del self._attrs[attr]
            except KeyError:
                raise AttributeError(attr)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            # key is a tuple, return the kernpair
            return self._kerning[key]
        else:
            # return the metrics instead
            return self._chars[key]

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            # key is a tuple, set kernpair
            self._kerning[key] = value
        else:
            # set char metrics
            self._chars[key] = value

    def __delitem__(self, key):
        if isinstance(key, tuple):
            # key is a tuple, del kernpair
            del self._kerning[key]
        else:
            # del char metrics
            del self._chars[key]

    def __repr__(self):
        if hasattr(self, "FullName"):
            return "<AFM object for %s>" % self.FullName
        else:
            return "<AFM object at %x>" % id(self)


def readlines(path):
    with open(path, "r", encoding="ascii") as f:
        data = f.read()
    return data.splitlines()


def writelines(path, lines, sep="\r"):
    with open(path, "w", encoding="ascii", newline=sep) as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    import EasyDialogs

    path = EasyDialogs.AskFileForOpen()
    if path:
        afm = AFM(path)
        char = "A"
        if afm.has_char(char):
            print(afm[char])  # print charnum, width and boundingbox
        pair = ("A", "V")
        if afm.has_kernpair(pair):
            print(afm[pair])  # print kerning value for pair
        print(afm.Version)  # various other afm entries have become attributes
        print(afm.Weight)
        # afm.comments() returns a list of all Comment lines found in the AFM
        print(afm.comments())
        # print afm.chars()
        # print afm.kernpairs()
        print(afm)
        afm.write(path + ".muck")

# === NexusCore/openenv\Lib\site-packages\fontTools\otlLib\optimize\gpos.py ===
import logging
import os
from collections import defaultdict, namedtuple
from dataclasses import dataclass
from functools import cached_property, reduce
from itertools import chain
from math import log2
from typing import DefaultDict, Dict, Iterable, List, Sequence, Tuple

from fontTools.config import OPTIONS
from fontTools.misc.intTools import bit_count, bit_indices
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otBase, otTables

log = logging.getLogger(__name__)

COMPRESSION_LEVEL = OPTIONS[f"{__name__}:COMPRESSION_LEVEL"]

# Kept because ufo2ft depends on it, to be removed once ufo2ft uses the config instead
# https://github.com/fonttools/fonttools/issues/2592
GPOS_COMPACT_MODE_ENV_KEY = "FONTTOOLS_GPOS_COMPACT_MODE"
GPOS_COMPACT_MODE_DEFAULT = str(COMPRESSION_LEVEL.default)


def _compression_level_from_env() -> int:
    env_level = GPOS_COMPACT_MODE_DEFAULT
    if GPOS_COMPACT_MODE_ENV_KEY in os.environ:
        import warnings

        warnings.warn(
            f"'{GPOS_COMPACT_MODE_ENV_KEY}' environment variable is deprecated. "
            "Please set the 'fontTools.otlLib.optimize.gpos:COMPRESSION_LEVEL' option "
            "in TTFont.cfg.",
            DeprecationWarning,
        )

        env_level = os.environ[GPOS_COMPACT_MODE_ENV_KEY]
    if len(env_level) == 1 and env_level in "0123456789":
        return int(env_level)
    raise ValueError(f"Bad {GPOS_COMPACT_MODE_ENV_KEY}={env_level}")


def compact(font: TTFont, level: int) -> TTFont:
    # Ideal plan:
    #  1. Find lookups of Lookup Type 2: Pair Adjustment Positioning Subtable
    #     https://docs.microsoft.com/en-us/typography/opentype/spec/gpos#lookup-type-2-pair-adjustment-positioning-subtable
    #  2. Extract glyph-glyph kerning and class-kerning from all present subtables
    #  3. Regroup into different subtable arrangements
    #  4. Put back into the lookup
    #
    # Actual implementation:
    #  2. Only class kerning is optimized currently
    #  3. If the input kerning is already in several subtables, the subtables
    #     are not grouped together first; instead each subtable is treated
    #     independently, so currently this step is:
    #     Split existing subtables into more smaller subtables
    gpos = font.get("GPOS")

    # If the font does not contain a GPOS table, there is nothing to do.
    if gpos is None:
        return font

    for lookup in gpos.table.LookupList.Lookup:
        if lookup.LookupType == 2:
            compact_lookup(font, level, lookup)
        elif lookup.LookupType == 9 and lookup.SubTable[0].ExtensionLookupType == 2:
            compact_ext_lookup(font, level, lookup)

    return font


def compact_lookup(font: TTFont, level: int, lookup: otTables.Lookup) -> None:
    new_subtables = compact_pair_pos(font, level, lookup.SubTable)
    lookup.SubTable = new_subtables
    lookup.SubTableCount = len(new_subtables)


def compact_ext_lookup(font: TTFont, level: int, lookup: otTables.Lookup) -> None:
    new_subtables = compact_pair_pos(
        font, level, [ext_subtable.ExtSubTable for ext_subtable in lookup.SubTable]
    )
    new_ext_subtables = []
    for subtable in new_subtables:
        ext_subtable = otTables.ExtensionPos()
        ext_subtable.Format = 1
        ext_subtable.ExtSubTable = subtable
        new_ext_subtables.append(ext_subtable)
    lookup.SubTable = new_ext_subtables
    lookup.SubTableCount = len(new_ext_subtables)


def compact_pair_pos(
    font: TTFont, level: int, subtables: Sequence[otTables.PairPos]
) -> Sequence[otTables.PairPos]:
    new_subtables = []
    for subtable in subtables:
        if subtable.Format == 1:
            # Not doing anything to Format 1 (yet?)
            new_subtables.append(subtable)
        elif subtable.Format == 2:
            new_subtables.extend(compact_class_pairs(font, level, subtable))
    return new_subtables


def compact_class_pairs(
    font: TTFont, level: int, subtable: otTables.PairPos
) -> List[otTables.PairPos]:
    from fontTools.otlLib.builder import buildPairPosClassesSubtable

    subtables = []
    classes1: DefaultDict[int, List[str]] = defaultdict(list)
    for g in subtable.Coverage.glyphs:
        classes1[subtable.ClassDef1.classDefs.get(g, 0)].append(g)
    classes2: DefaultDict[int, List[str]] = defaultdict(list)
    for g, i in subtable.ClassDef2.classDefs.items():
        classes2[i].append(g)
    all_pairs = {}
    for i, class1 in enumerate(subtable.Class1Record):
        for j, class2 in enumerate(class1.Class2Record):
            if is_really_zero(class2):
                continue
            all_pairs[(tuple(sorted(classes1[i])), tuple(sorted(classes2[j])))] = (
                getattr(class2, "Value1", None),
                getattr(class2, "Value2", None),
            )
    grouped_pairs = cluster_pairs_by_class2_coverage_custom_cost(font, all_pairs, level)
    for pairs in grouped_pairs:
        subtables.append(buildPairPosClassesSubtable(pairs, font.getReverseGlyphMap()))
    return subtables


def is_really_zero(class2: otTables.Class2Record) -> bool:
    v1 = getattr(class2, "Value1", None)
    v2 = getattr(class2, "Value2", None)
    return (v1 is None or v1.getEffectiveFormat() == 0) and (
        v2 is None or v2.getEffectiveFormat() == 0
    )


Pairs = Dict[
    Tuple[Tuple[str, ...], Tuple[str, ...]],
    Tuple[otBase.ValueRecord, otBase.ValueRecord],
]


# Adapted from https://github.com/fonttools/fonttools/blob/f64f0b42f2d1163b2d85194e0979def539f5dca3/Lib/fontTools/ttLib/tables/otTables.py#L935-L958
def _getClassRanges(glyphIDs: Iterable[int]):
    glyphIDs = sorted(glyphIDs)
    last = glyphIDs[0]
    ranges = [[last]]
    for glyphID in glyphIDs[1:]:
        if glyphID != last + 1:
            ranges[-1].append(last)
            ranges.append([glyphID])
        last = glyphID
    ranges[-1].append(last)
    return ranges, glyphIDs[0], glyphIDs[-1]


# Adapted from https://github.com/fonttools/fonttools/blob/f64f0b42f2d1163b2d85194e0979def539f5dca3/Lib/fontTools/ttLib/tables/otTables.py#L960-L989
def _classDef_bytes(
    class_data: List[Tuple[List[Tuple[int, int]], int, int]],
    class_ids: List[int],
    coverage=False,
):
    if not class_ids:
        return 0
    first_ranges, min_glyph_id, max_glyph_id = class_data[class_ids[0]]
    range_count = len(first_ranges)
    for i in class_ids[1:]:
        data = class_data[i]
        range_count += len(data[0])
        min_glyph_id = min(min_glyph_id, data[1])
        max_glyph_id = max(max_glyph_id, data[2])
    glyphCount = max_glyph_id - min_glyph_id + 1
    # https://docs.microsoft.com/en-us/typography/opentype/spec/chapter2#class-definition-table-format-1
    format1_bytes = 6 + glyphCount * 2
    # https://docs.microsoft.com/en-us/typography/opentype/spec/chapter2#class-definition-table-format-2
    format2_bytes = 4 + range_count * 6
    return min(format1_bytes, format2_bytes)


ClusteringContext = namedtuple(
    "ClusteringContext",
    [
        "lines",
        "all_class1",
        "all_class1_data",
        "all_class2_data",
        "valueFormat1_bytes",
        "valueFormat2_bytes",
    ],
)


@dataclass
class Cluster:
    ctx: ClusteringContext
    indices_bitmask: int

    @cached_property
    def indices(self):
        return bit_indices(self.indices_bitmask)

    @cached_property
    def column_indices(self):
        # Indices of columns that have a 1 in at least 1 line
        #   => binary OR all the lines
        bitmask = reduce(int.__or__, (self.ctx.lines[i] for i in self.indices))
        return bit_indices(bitmask)

    @property
    def width(self):
        # Add 1 because Class2=0 cannot be used but needs to be encoded.
        return len(self.column_indices) + 1

    @cached_property
    def cost(self):
        return (
            # 2 bytes to store the offset to this subtable in the Lookup table above
            2
            # Contents of the subtable
            # From: https://docs.microsoft.com/en-us/typography/opentype/spec/gpos#pair-adjustment-positioning-format-2-class-pair-adjustment
            # uint16	posFormat	Format identifier: format = 2
            + 2
            # Offset16	coverageOffset	Offset to Coverage table, from beginning of PairPos subtable.
            + 2
            + self.coverage_bytes
            # uint16	valueFormat1	ValueRecord definition — for the first glyph of the pair (may be zero).
            + 2
            # uint16	valueFormat2	ValueRecord definition — for the second glyph of the pair (may be zero).
            + 2
            # Offset16	classDef1Offset	Offset to ClassDef table, from beginning of PairPos subtable — for the first glyph of the pair.
            + 2
            + self.classDef1_bytes
            # Offset16	classDef2Offset	Offset to ClassDef table, from beginning of PairPos subtable — for the second glyph of the pair.
            + 2
            + self.classDef2_bytes
            # uint16	class1Count	Number of classes in classDef1 table — includes Class 0.
            + 2
            # uint16	class2Count	Number of classes in classDef2 table — includes Class 0.
            + 2
            # Class1Record	class1Records[class1Count]	Array of Class1 records, ordered by classes in classDef1.
            + (self.ctx.valueFormat1_bytes + self.ctx.valueFormat2_bytes)
            * len(self.indices)
            * self.width
        )

    @property
    def coverage_bytes(self):
        format1_bytes = (
            # From https://docs.microsoft.com/en-us/typography/opentype/spec/chapter2#coverage-format-1
            # uint16	coverageFormat	Format identifier — format = 1
            # uint16	glyphCount	Number of glyphs in the glyph array
            4
            # uint16	glyphArray[glyphCount]	Array of glyph IDs — in numerical order
            + sum(len(self.ctx.all_class1[i]) for i in self.indices) * 2
        )
        ranges = sorted(
            chain.from_iterable(self.ctx.all_class1_data[i][0] for i in self.indices)
        )
        merged_range_count = 0
        last = None
        for start, end in ranges:
            if last is not None and start != last + 1:
                merged_range_count += 1
            last = end
        format2_bytes = (
            # From https://docs.microsoft.com/en-us/typography/opentype/spec/chapter2#coverage-format-2
            # uint16	coverageFormat	Format identifier — format = 2
            # uint16	rangeCount	Number of RangeRecords
            4
            # RangeRecord	rangeRecords[rangeCount]	Array of glyph ranges — ordered by startGlyphID.
            # uint16	startGlyphID	First glyph ID in the range
            # uint16	endGlyphID	Last glyph ID in the range
            # uint16	startCoverageIndex	Coverage Index of first glyph ID in range
            + merged_range_count * 6
        )
        return min(format1_bytes, format2_bytes)

    @property
    def classDef1_bytes(self):
        # We can skip encoding one of the Class1 definitions, and use
        # Class1=0 to represent it instead, because Class1 is gated by the
        # Coverage definition. Use Class1=0 for the highest byte savings.
        # Going through all options takes too long, pick the biggest class
        # = what happens in otlLib.builder.ClassDefBuilder.classes()
        biggest_index = max(self.indices, key=lambda i: len(self.ctx.all_class1[i]))
        return _classDef_bytes(
            self.ctx.all_class1_data, [i for i in self.indices if i != biggest_index]
        )

    @property
    def classDef2_bytes(self):
        # All Class2 need to be encoded because we can't use Class2=0
        return _classDef_bytes(self.ctx.all_class2_data, self.column_indices)


def cluster_pairs_by_class2_coverage_custom_cost(
    font: TTFont,
    pairs: Pairs,
    compression: int = 5,
) -> List[Pairs]:
    if not pairs:
        # The subtable was actually empty?
        return [pairs]

    # Sorted for reproducibility/determinism
    all_class1 = sorted(set(pair[0] for pair in pairs))
    all_class2 = sorted(set(pair[1] for pair in pairs))

    # Use Python's big ints for binary vectors representing each line
    lines = [
        sum(
            1 << i if (class1, class2) in pairs else 0
            for i, class2 in enumerate(all_class2)
        )
        for class1 in all_class1
    ]

    # Map glyph names to ids and work with ints throughout for ClassDef formats
    name_to_id = font.getReverseGlyphMap()
    # Each entry in the arrays below is (range_count, min_glyph_id, max_glyph_id)
    all_class1_data = [
        _getClassRanges(name_to_id[name] for name in cls) for cls in all_class1
    ]
    all_class2_data = [
        _getClassRanges(name_to_id[name] for name in cls) for cls in all_class2
    ]

    format1 = 0
    format2 = 0
    for pair, value in pairs.items():
        format1 |= value[0].getEffectiveFormat() if value[0] else 0
        format2 |= value[1].getEffectiveFormat() if value[1] else 0
    valueFormat1_bytes = bit_count(format1) * 2
    valueFormat2_bytes = bit_count(format2) * 2

    ctx = ClusteringContext(
        lines,
        all_class1,
        all_class1_data,
        all_class2_data,
        valueFormat1_bytes,
        valueFormat2_bytes,
    )

    cluster_cache: Dict[int, Cluster] = {}

    def make_cluster(indices: int) -> Cluster:
        cluster = cluster_cache.get(indices, None)
        if cluster is not None:
            return cluster
        cluster = Cluster(ctx, indices)
        cluster_cache[indices] = cluster
        return cluster

    def merge(cluster: Cluster, other: Cluster) -> Cluster:
        return make_cluster(cluster.indices_bitmask | other.indices_bitmask)

    # Agglomerative clustering by hand, checking the cost gain of the new
    # cluster against the previously separate clusters
    # Start with 1 cluster per line
    # cluster = set of lines = new subtable
    clusters = [make_cluster(1 << i) for i in range(len(lines))]

    # Cost of 1 cluster with everything
    # `(1 << len) - 1` gives a bitmask full of 1's of length `len`
    cost_before_splitting = make_cluster((1 << len(lines)) - 1).cost
    log.debug(f"        len(clusters) = {len(clusters)}")

    while len(clusters) > 1:
        lowest_cost_change = None
        best_cluster_index = None
        best_other_index = None
        best_merged = None
        for i, cluster in enumerate(clusters):
            for j, other in enumerate(clusters[i + 1 :]):
                merged = merge(cluster, other)
                cost_change = merged.cost - cluster.cost - other.cost
                if lowest_cost_change is None or cost_change < lowest_cost_change:
                    lowest_cost_change = cost_change
                    best_cluster_index = i
                    best_other_index = i + 1 + j
                    best_merged = merged
        assert lowest_cost_change is not None
        assert best_cluster_index is not None
        assert best_other_index is not None
        assert best_merged is not None

        # If the best merge we found is still taking down the file size, then
        # there's no question: we must do it, because it's beneficial in both
        # ways (lower file size and lower number of subtables).  However, if the
        # best merge we found is not reducing file size anymore, then we need to
        # look at the other stop criteria = the compression factor.
        if lowest_cost_change > 0:
            # Stop critera: check whether we should keep merging.
            # Compute size reduction brought by splitting
            cost_after_splitting = sum(c.cost for c in clusters)
            # size_reduction so that after = before * (1 - size_reduction)
            # E.g. before = 1000, after = 800, 1 - 800/1000 = 0.2
            size_reduction = 1 - cost_after_splitting / cost_before_splitting

            # Force more merging by taking into account the compression number.
            # Target behaviour: compression number = 1 to 9, default 5 like gzip
            #   - 1 = accept to add 1 subtable to reduce size by 50%
            #   - 5 = accept to add 5 subtables to reduce size by 50%
            # See https://github.com/harfbuzz/packtab/blob/master/Lib/packTab/__init__.py#L690-L691
            # Given the size reduction we have achieved so far, compute how many
            # new subtables are acceptable.
            max_new_subtables = -log2(1 - size_reduction) * compression
            log.debug(
                f"            len(clusters) = {len(clusters):3d}    size_reduction={size_reduction:5.2f}    max_new_subtables={max_new_subtables}",
            )
            if compression == 9:
                # Override level 9 to mean: create any number of subtables
                max_new_subtables = len(clusters)

            # If we have managed to take the number of new subtables below the
            # threshold, then we can stop.
            if len(clusters) <= max_new_subtables + 1:
                break

        # No reason to stop yet, do the merge and move on to the next.
        del clusters[best_other_index]
        clusters[best_cluster_index] = best_merged

    # All clusters are final; turn bitmasks back into the "Pairs" format
    pairs_by_class1: Dict[Tuple[str, ...], Pairs] = defaultdict(dict)
    for pair, values in pairs.items():
        pairs_by_class1[pair[0]][pair] = values
    pairs_groups: List[Pairs] = []
    for cluster in clusters:
        pairs_group: Pairs = dict()
        for i in cluster.indices:
            class1 = all_class1[i]
            pairs_group.update(pairs_by_class1[class1])
        pairs_groups.append(pairs_group)
    return pairs_groups

# === NexusCore/openenv\Lib\site-packages\litellm\llms\ollama_chat.py ===
import json
import time
import uuid
from typing import Any, List, Optional, Union

import aiohttp
import httpx
from pydantic import BaseModel

import litellm
from litellm import verbose_logger
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    get_async_httpx_client,
)
from litellm.types.llms.ollama import OllamaToolCall, OllamaToolCallFunction
from litellm.types.llms.openai import ChatCompletionAssistantToolCall
from litellm.types.utils import ModelResponse, StreamingChoices


class OllamaError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        self.request = httpx.Request(method="POST", url="http://localhost:11434")
        self.response = httpx.Response(status_code=status_code, request=self.request)
        super().__init__(
            self.message
        )  # Call the base class constructor with the parameters it needs


# ollama implementation
def get_ollama_response(  # noqa: PLR0915
    model_response: ModelResponse,
    messages: list,
    optional_params: dict,
    model: str,
    logging_obj: Any,
    api_base="http://localhost:11434",
    api_key: Optional[str] = None,
    acompletion: bool = False,
    encoding=None,
    client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
):
    if api_base.endswith("/api/chat"):
        url = api_base
    else:
        url = f"{api_base}/api/chat"

    ## Load Config
    config = litellm.OllamaChatConfig.get_config()
    for k, v in config.items():
        if (
            k not in optional_params
        ):  # completion(top_k=3) > cohere_config(top_k=3) <- allows for dynamic variables to be passed in
            optional_params[k] = v

    stream = optional_params.pop("stream", False)
    format = optional_params.pop("format", None)
    keep_alive = optional_params.pop("keep_alive", None)
    function_name = optional_params.pop("function_name", None)
    tools = optional_params.pop("tools", None)

    new_messages = []
    for m in messages:
        if isinstance(
            m, BaseModel
        ):  # avoid message serialization issues - https://github.com/BerriAI/litellm/issues/5319
            m = m.model_dump(exclude_none=True)
        if m.get("tool_calls") is not None and isinstance(m["tool_calls"], list):
            new_tools: List[OllamaToolCall] = []
            for tool in m["tool_calls"]:
                typed_tool = ChatCompletionAssistantToolCall(**tool)  # type: ignore
                if typed_tool["type"] == "function":
                    arguments = {}
                    if "arguments" in typed_tool["function"]:
                        arguments = json.loads(typed_tool["function"]["arguments"])
                    ollama_tool_call = OllamaToolCall(
                        function=OllamaToolCallFunction(
                            name=typed_tool["function"].get("name") or "",
                            arguments=arguments,
                        )
                    )
                    new_tools.append(ollama_tool_call)
            m["tool_calls"] = new_tools
        new_messages.append(m)

    data = {
        "model": model,
        "messages": new_messages,
        "options": optional_params,
        "stream": stream,
    }
    if format is not None:
        data["format"] = format
    if tools is not None:
        data["tools"] = tools
    if keep_alive is not None:
        data["keep_alive"] = keep_alive
    ## LOGGING
    logging_obj.pre_call(
        input=None,
        api_key=None,
        additional_args={
            "api_base": url,
            "complete_input_dict": data,
            "headers": {},
            "acompletion": acompletion,
        },
    )
    if acompletion is True:
        if stream is True:
            response = ollama_async_streaming(
                url=url,
                api_key=api_key,
                data=data,
                model_response=model_response,
                encoding=encoding,
                logging_obj=logging_obj,
            )
        else:
            response = ollama_acompletion(
                url=url,
                api_key=api_key,
                data=data,
                model_response=model_response,
                encoding=encoding,
                logging_obj=logging_obj,
                function_name=function_name,
            )
        return response
    elif stream is True:
        return ollama_completion_stream(
            url=url, api_key=api_key, data=data, logging_obj=logging_obj
        )

    headers: Optional[dict] = None
    if api_key is not None:
        headers = {"Authorization": "Bearer {}".format(api_key)}

    sync_client = litellm.module_level_client
    if client is not None and isinstance(client, HTTPHandler):
        sync_client = client
    response = sync_client.post(
        url=url,
        json=data,
        headers=headers,
    )
    if response.status_code != 200:
        raise OllamaError(status_code=response.status_code, message=response.text)

    ## LOGGING
    logging_obj.post_call(
        input=messages,
        api_key="",
        original_response=response.text,
        additional_args={
            "headers": None,
            "api_base": api_base,
        },
    )

    response_json = response.json()

    ## RESPONSE OBJECT
    model_response.choices[0].finish_reason = "stop"
    if data.get("format", "") == "json" and function_name is not None:
        function_call = json.loads(response_json["message"]["content"])
        message = litellm.Message(
            content=None,
            tool_calls=[
                {
                    "id": f"call_{str(uuid.uuid4())}",
                    "function": {
                        "name": function_call.get("name", function_name),
                        "arguments": json.dumps(
                            function_call.get("arguments", function_call)
                        ),
                    },
                    "type": "function",
                }
            ],
        )
        model_response.choices[0].message = message  # type: ignore
        model_response.choices[0].finish_reason = "tool_calls"
    else:
        _message = litellm.Message(**response_json["message"])
        model_response.choices[0].message = _message  # type: ignore
    model_response.created = int(time.time())
    model_response.model = "ollama_chat/" + model
    prompt_tokens = response_json.get("prompt_eval_count", litellm.token_counter(messages=messages))  # type: ignore
    completion_tokens = response_json.get(
        "eval_count", litellm.token_counter(text=response_json["message"]["content"])
    )
    setattr(
        model_response,
        "usage",
        litellm.Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )
    return model_response


def ollama_completion_stream(url, api_key, data, logging_obj):
    _request = {
        "url": f"{url}",
        "json": data,
        "method": "POST",
        "timeout": litellm.request_timeout,
        "follow_redirects": True,
    }
    if api_key is not None:
        _request["headers"] = {"Authorization": "Bearer {}".format(api_key)}
    with httpx.stream(**_request) as response:
        try:
            if response.status_code != 200:
                raise OllamaError(
                    status_code=response.status_code, message=response.iter_lines()
                )

            streamwrapper = litellm.CustomStreamWrapper(
                completion_stream=response.iter_lines(),
                model=data["model"],
                custom_llm_provider="ollama_chat",
                logging_obj=logging_obj,
            )

            # If format is JSON, this was a function call
            # Gather all chunks and return the function call as one delta to simplify parsing
            if data.get("format", "") == "json":
                content_chunks = []
                for chunk in streamwrapper:
                    chunk_choice = chunk.choices[0]
                    if (
                        isinstance(chunk_choice, StreamingChoices)
                        and hasattr(chunk_choice, "delta")
                        and hasattr(chunk_choice.delta, "content")
                    ):
                        content_chunks.append(chunk_choice.delta.content)
                response_content = "".join(content_chunks)

                function_call = json.loads(response_content)
                delta = litellm.utils.Delta(
                    content=None,
                    tool_calls=[
                        {
                            "id": f"call_{str(uuid.uuid4())}",
                            "function": {
                                "name": function_call["name"],
                                "arguments": json.dumps(function_call["arguments"]),
                            },
                            "type": "function",
                        }
                    ],
                )
                model_response = content_chunks[0]
                model_response.choices[0].delta = delta  # type: ignore
                model_response.choices[0].finish_reason = "tool_calls"
                yield model_response
            else:
                for transformed_chunk in streamwrapper:
                    yield transformed_chunk
        except Exception as e:
            raise e


async def ollama_async_streaming(
    url, api_key, data, model_response, encoding, logging_obj
):
    try:
        _async_http_client = get_async_httpx_client(
            llm_provider=litellm.LlmProviders.OLLAMA
        )
        client = _async_http_client.client
        _request = {
            "url": f"{url}",
            "json": data,
            "method": "POST",
            "timeout": litellm.request_timeout,
        }
        if api_key is not None:
            _request["headers"] = {"Authorization": "Bearer {}".format(api_key)}
        async with client.stream(**_request) as response:
            if response.status_code != 200:
                raise OllamaError(
                    status_code=response.status_code, message=response.text
                )

            streamwrapper = litellm.CustomStreamWrapper(
                completion_stream=response.aiter_lines(),
                model=data["model"],
                custom_llm_provider="ollama_chat",
                logging_obj=logging_obj,
            )

            # If format is JSON, this was a function call
            # Gather all chunks and return the function call as one delta to simplify parsing
            if data.get("format", "") == "json":
                first_chunk = await anext(streamwrapper)  # noqa F821
                chunk_choice = first_chunk.choices[0]
                if (
                    isinstance(chunk_choice, StreamingChoices)
                    and hasattr(chunk_choice, "delta")
                    and hasattr(chunk_choice.delta, "content")
                ):
                    first_chunk_content = chunk_choice.delta.content or ""
                else:
                    first_chunk_content = ""

                content_chunks = []
                async for chunk in streamwrapper:
                    chunk_choice = chunk.choices[0]
                    if (
                        isinstance(chunk_choice, StreamingChoices)
                        and hasattr(chunk_choice, "delta")
                        and hasattr(chunk_choice.delta, "content")
                    ):
                        content_chunks.append(chunk_choice.delta.content)
                response_content = first_chunk_content + "".join(content_chunks)

                function_call = json.loads(response_content)
                delta = litellm.utils.Delta(
                    content=None,
                    tool_calls=[
                        {
                            "id": f"call_{str(uuid.uuid4())}",
                            "function": {
                                "name": function_call.get(
                                    "name", function_call.get("function", None)
                                ),
                                "arguments": json.dumps(function_call["arguments"]),
                            },
                            "type": "function",
                        }
                    ],
                )
                model_response = first_chunk
                model_response.choices[0].delta = delta  # type: ignore
                model_response.choices[0].finish_reason = "tool_calls"
                yield model_response
            else:
                async for transformed_chunk in streamwrapper:
                    yield transformed_chunk
    except Exception as e:
        verbose_logger.exception(
            "LiteLLM.ollama(): Exception occured - {}".format(str(e))
        )
        raise e


async def ollama_acompletion(
    url,
    api_key: Optional[str],
    data,
    model_response: litellm.ModelResponse,
    encoding,
    logging_obj,
    function_name,
):
    data["stream"] = False
    try:
        timeout = aiohttp.ClientTimeout(total=litellm.request_timeout)  # 10 minutes
        async with aiohttp.ClientSession(timeout=timeout) as session:
            _request = {
                "url": f"{url}",
                "json": data,
            }
            if api_key is not None:
                _request["headers"] = {"Authorization": "Bearer {}".format(api_key)}
            resp = await session.post(**_request)

            if resp.status != 200:
                text = await resp.text()
                raise OllamaError(status_code=resp.status, message=text)

            response_json = await resp.json()

            ## LOGGING
            logging_obj.post_call(
                input=data,
                api_key="",
                original_response=response_json,
                additional_args={
                    "headers": None,
                    "api_base": url,
                },
            )

            ## RESPONSE OBJECT
            model_response.choices[0].finish_reason = "stop"

            if data.get("format", "") == "json" and function_name is not None:
                function_call = json.loads(response_json["message"]["content"])
                message = litellm.Message(
                    content=None,
                    tool_calls=[
                        {
                            "id": f"call_{str(uuid.uuid4())}",
                            "function": {
                                "name": function_call.get("name", function_name),
                                "arguments": json.dumps(
                                    function_call.get("arguments", function_call)
                                ),
                            },
                            "type": "function",
                        }
                    ],
                )
                model_response.choices[0].message = message  # type: ignore
                model_response.choices[0].finish_reason = "tool_calls"
            else:
                _message = litellm.Message(**response_json["message"])
                model_response.choices[0].message = _message  # type: ignore

            model_response.created = int(time.time())
            model_response.model = "ollama_chat/" + data["model"]
            prompt_tokens = response_json.get("prompt_eval_count", litellm.token_counter(messages=data["messages"]))  # type: ignore
            completion_tokens = response_json.get(
                "eval_count",
                litellm.token_counter(
                    text=response_json["message"]["content"], count_response_tokens=True
                ),
            )
            setattr(
                model_response,
                "usage",
                litellm.Usage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
            )
            return model_response
    except Exception as e:
        raise e  # don't use verbose_logger.exception, if exception is raised

# === NexusCore/openenv\Lib\site-packages\httpx\_api.py ===
from __future__ import annotations

import typing
from contextlib import contextmanager

from ._client import Client
from ._config import DEFAULT_TIMEOUT_CONFIG
from ._models import Response
from ._types import (
    AuthTypes,
    CookieTypes,
    HeaderTypes,
    ProxyTypes,
    QueryParamTypes,
    RequestContent,
    RequestData,
    RequestFiles,
    TimeoutTypes,
)
from ._urls import URL

if typing.TYPE_CHECKING:
    import ssl  # pragma: no cover


__all__ = [
    "delete",
    "get",
    "head",
    "options",
    "patch",
    "post",
    "put",
    "request",
    "stream",
]


def request(
    method: str,
    url: URL | str,
    *,
    params: QueryParamTypes | None = None,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: typing.Any | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    trust_env: bool = True,
) -> Response:
    """
    Sends an HTTP request.

    **Parameters:**

    * **method** - HTTP method for the new `Request` object: `GET`, `OPTIONS`,
    `HEAD`, `POST`, `PUT`, `PATCH`, or `DELETE`.
    * **url** - URL for the new `Request` object.
    * **params** - *(optional)* Query parameters to include in the URL, as a
    string, dictionary, or sequence of two-tuples.
    * **content** - *(optional)* Binary content to include in the body of the
    request, as bytes or a byte iterator.
    * **data** - *(optional)* Form data to include in the body of the request,
    as a dictionary.
    * **files** - *(optional)* A dictionary of upload files to include in the
    body of the request.
    * **json** - *(optional)* A JSON serializable object to include in the body
    of the request.
    * **headers** - *(optional)* Dictionary of HTTP headers to include in the
    request.
    * **cookies** - *(optional)* Dictionary of Cookie items to include in the
    request.
    * **auth** - *(optional)* An authentication class to use when sending the
    request.
    * **proxy** - *(optional)* A proxy URL where all the traffic should be routed.
    * **timeout** - *(optional)* The timeout configuration to use when sending
    the request.
    * **follow_redirects** - *(optional)* Enables or disables HTTP redirects.
    * **verify** - *(optional)* Either `True` to use an SSL context with the
    default CA bundle, `False` to disable verification, or an instance of
    `ssl.SSLContext` to use a custom context.
    * **trust_env** - *(optional)* Enables or disables usage of environment
    variables for configuration.

    **Returns:** `Response`

    Usage:

    ```
    >>> import httpx
    >>> response = httpx.request('GET', 'https://httpbin.org/get')
    >>> response
    <Response [200 OK]>
    ```
    """
    with Client(
        cookies=cookies,
        proxy=proxy,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    ) as client:
        return client.request(
            method=method,
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            auth=auth,
            follow_redirects=follow_redirects,
        )


@contextmanager
def stream(
    method: str,
    url: URL | str,
    *,
    params: QueryParamTypes | None = None,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: typing.Any | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    trust_env: bool = True,
) -> typing.Iterator[Response]:
    """
    Alternative to `httpx.request()` that streams the response body
    instead of loading it into memory at once.

    **Parameters**: See `httpx.request`.

    See also: [Streaming Responses][0]

    [0]: /quickstart#streaming-responses
    """
    with Client(
        cookies=cookies,
        proxy=proxy,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    ) as client:
        with client.stream(
            method=method,
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            auth=auth,
            follow_redirects=follow_redirects,
        ) as response:
            yield response


def get(
    url: URL | str,
    *,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    trust_env: bool = True,
) -> Response:
    """
    Sends a `GET` request.

    **Parameters**: See `httpx.request`.

    Note that the `data`, `files`, `json` and `content` parameters are not available
    on this function, as `GET` requests should not include a request body.
    """
    return request(
        "GET",
        url,
        params=params,
        headers=headers,
        cookies=cookies,
        auth=auth,
        proxy=proxy,
        follow_redirects=follow_redirects,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )


def options(
    url: URL | str,
    *,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    trust_env: bool = True,
) -> Response:
    """
    Sends an `OPTIONS` request.

    **Parameters**: See `httpx.request`.

    Note that the `data`, `files`, `json` and `content` parameters are not available
    on this function, as `OPTIONS` requests should not include a request body.
    """
    return request(
        "OPTIONS",
        url,
        params=params,
        headers=headers,
        cookies=cookies,
        auth=auth,
        proxy=proxy,
        follow_redirects=follow_redirects,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )


def head(
    url: URL | str,
    *,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    trust_env: bool = True,
) -> Response:
    """
    Sends a `HEAD` request.

    **Parameters**: See `httpx.request`.

    Note that the `data`, `files`, `json` and `content` parameters are not available
    on this function, as `HEAD` requests should not include a request body.
    """
    return request(
        "HEAD",
        url,
        params=params,
        headers=headers,
        cookies=cookies,
        auth=auth,
        proxy=proxy,
        follow_redirects=follow_redirects,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )


def post(
    url: URL | str,
    *,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: typing.Any | None = None,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    trust_env: bool = True,
) -> Response:
    """
    Sends a `POST` request.

    **Parameters**: See `httpx.request`.
    """
    return request(
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
        proxy=proxy,
        follow_redirects=follow_redirects,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )


def put(
    url: URL | str,
    *,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: typing.Any | None = None,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    trust_env: bool = True,
) -> Response:
    """
    Sends a `PUT` request.

    **Parameters**: See `httpx.request`.
    """
    return request(
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
        proxy=proxy,
        follow_redirects=follow_redirects,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )


def patch(
    url: URL | str,
    *,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: typing.Any | None = None,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    trust_env: bool = True,
) -> Response:
    """
    Sends a `PATCH` request.

    **Parameters**: See `httpx.request`.
    """
    return request(
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
        proxy=proxy,
        follow_redirects=follow_redirects,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )


def delete(
    url: URL | str,
    *,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    verify: ssl.SSLContext | str | bool = True,
    trust_env: bool = True,
) -> Response:
    """
    Sends a `DELETE` request.

    **Parameters**: See `httpx.request`.

    Note that the `data`, `files`, `json` and `content` parameters are not available
    on this function, as `DELETE` requests should not include a request body.
    """
    return request(
        "DELETE",
        url,
        params=params,
        headers=headers,
        cookies=cookies,
        auth=auth,
        proxy=proxy,
        follow_redirects=follow_redirects,
        verify=verify,
        timeout=timeout,
        trust_env=trust_env,
    )

# === NexusCore/openenv\Lib\site-packages\pyparsing\util.py ===
# util.py
import contextlib
import re
from functools import lru_cache, wraps
import inspect
import itertools
import types
from typing import Callable, Union, Iterable, TypeVar, cast
import warnings

_bslash = chr(92)
C = TypeVar("C", bound=Callable)


class __config_flags:
    """Internal class for defining compatibility and debugging flags"""

    _all_names: list[str] = []
    _fixed_names: list[str] = []
    _type_desc = "configuration"

    @classmethod
    def _set(cls, dname, value):
        if dname in cls._fixed_names:
            warnings.warn(
                f"{cls.__name__}.{dname} {cls._type_desc} is {str(getattr(cls, dname)).upper()}"
                f" and cannot be overridden",
                stacklevel=3,
            )
            return
        if dname in cls._all_names:
            setattr(cls, dname, value)
        else:
            raise ValueError(f"no such {cls._type_desc} {dname!r}")

    enable = classmethod(lambda cls, name: cls._set(name, True))
    disable = classmethod(lambda cls, name: cls._set(name, False))


@lru_cache(maxsize=128)
def col(loc: int, strg: str) -> int:
    """
    Returns current column within a string, counting newlines as line separators.
    The first column is number 1.

    Note: the default parsing behavior is to expand tabs in the input string
    before starting the parsing process.  See
    :class:`ParserElement.parse_string` for more
    information on parsing strings containing ``<TAB>`` s, and suggested
    methods to maintain a consistent view of the parsed string, the parse
    location, and line and column positions within the parsed string.
    """
    s = strg
    return 1 if 0 < loc < len(s) and s[loc - 1] == "\n" else loc - s.rfind("\n", 0, loc)


@lru_cache(maxsize=128)
def lineno(loc: int, strg: str) -> int:
    """Returns current line number within a string, counting newlines as line separators.
    The first line is number 1.

    Note - the default parsing behavior is to expand tabs in the input string
    before starting the parsing process.  See :class:`ParserElement.parse_string`
    for more information on parsing strings containing ``<TAB>`` s, and
    suggested methods to maintain a consistent view of the parsed string, the
    parse location, and line and column positions within the parsed string.
    """
    return strg.count("\n", 0, loc) + 1


@lru_cache(maxsize=128)
def line(loc: int, strg: str) -> str:
    """
    Returns the line of text containing loc within a string, counting newlines as line separators.
    """
    last_cr = strg.rfind("\n", 0, loc)
    next_cr = strg.find("\n", loc)
    return strg[last_cr + 1 : next_cr] if next_cr >= 0 else strg[last_cr + 1 :]


class _UnboundedCache:
    def __init__(self):
        cache = {}
        cache_get = cache.get
        self.not_in_cache = not_in_cache = object()

        def get(_, key):
            return cache_get(key, not_in_cache)

        def set_(_, key, value):
            cache[key] = value

        def clear(_):
            cache.clear()

        self.size = None
        self.get = types.MethodType(get, self)
        self.set = types.MethodType(set_, self)
        self.clear = types.MethodType(clear, self)


class _FifoCache:
    def __init__(self, size):
        cache = {}
        self.size = size
        self.not_in_cache = not_in_cache = object()
        cache_get = cache.get
        cache_pop = cache.pop

        def get(_, key):
            return cache_get(key, not_in_cache)

        def set_(_, key, value):
            cache[key] = value
            while len(cache) > size:
                # pop oldest element in cache by getting the first key
                cache_pop(next(iter(cache)))

        def clear(_):
            cache.clear()

        self.get = types.MethodType(get, self)
        self.set = types.MethodType(set_, self)
        self.clear = types.MethodType(clear, self)


class LRUMemo:
    """
    A memoizing mapping that retains `capacity` deleted items

    The memo tracks retained items by their access order; once `capacity` items
    are retained, the least recently used item is discarded.
    """

    def __init__(self, capacity):
        self._capacity = capacity
        self._active = {}
        self._memory = {}

    def __getitem__(self, key):
        try:
            return self._active[key]
        except KeyError:
            self._memory[key] = self._memory.pop(key)
            return self._memory[key]

    def __setitem__(self, key, value):
        self._memory.pop(key, None)
        self._active[key] = value

    def __delitem__(self, key):
        try:
            value = self._active.pop(key)
        except KeyError:
            pass
        else:
            oldest_keys = list(self._memory)[: -(self._capacity + 1)]
            for key_to_delete in oldest_keys:
                self._memory.pop(key_to_delete)
            self._memory[key] = value

    def clear(self):
        self._active.clear()
        self._memory.clear()


class UnboundedMemo(dict):
    """
    A memoizing mapping that retains all deleted items
    """

    def __delitem__(self, key):
        pass


def _escape_regex_range_chars(s: str) -> str:
    # escape these chars: ^-[]
    for c in r"\^-[]":
        s = s.replace(c, _bslash + c)
    s = s.replace("\n", r"\n")
    s = s.replace("\t", r"\t")
    return str(s)


class _GroupConsecutive:
    """
    Used as a callable `key` for itertools.groupby to group
    characters that are consecutive:
        itertools.groupby("abcdejkmpqrs", key=IsConsecutive())
        yields:
            (0, iter(['a', 'b', 'c', 'd', 'e']))
            (1, iter(['j', 'k']))
            (2, iter(['m']))
            (3, iter(['p', 'q', 'r', 's']))
    """

    def __init__(self) -> None:
        self.prev = 0
        self.counter = itertools.count()
        self.value = -1

    def __call__(self, char: str) -> int:
        c_int = ord(char)
        self.prev, prev = c_int, self.prev
        if c_int - prev > 1:
            self.value = next(self.counter)
        return self.value


def _collapse_string_to_ranges(
    s: Union[str, Iterable[str]], re_escape: bool = True
) -> str:
    r"""
    Take a string or list of single-character strings, and return
    a string of the consecutive characters in that string collapsed
    into groups, as might be used in a regular expression '[a-z]'
    character set:
        'a' -> 'a' -> '[a]'
        'bc' -> 'bc' -> '[bc]'
        'defgh' -> 'd-h' -> '[d-h]'
        'fdgeh' -> 'd-h' -> '[d-h]'
        'jklnpqrtu' -> 'j-lnp-rtu' -> '[j-lnp-rtu]'
    Duplicates get collapsed out:
        'aaa' -> 'a' -> '[a]'
        'bcbccb' -> 'bc' -> '[bc]'
        'defghhgf' -> 'd-h' -> '[d-h]'
        'jklnpqrjjjtu' -> 'j-lnp-rtu' -> '[j-lnp-rtu]'
    Spaces are preserved:
        'ab c' -> ' a-c' -> '[ a-c]'
    Characters that are significant when defining regex ranges
    get escaped:
        'acde[]-' -> r'\-\[\]ac-e' -> r'[\-\[\]ac-e]'
    """

    # Developer notes:
    # - Do not optimize this code assuming that the given input string
    #   or internal lists will be short (such as in loading generators into
    #   lists to make it easier to find the last element); this method is also
    #   used to generate regex ranges for character sets in the pyparsing.unicode
    #   classes, and these can be _very_ long lists of strings

    def escape_re_range_char(c: str) -> str:
        return "\\" + c if c in r"\^-][" else c

    def no_escape_re_range_char(c: str) -> str:
        return c

    if not re_escape:
        escape_re_range_char = no_escape_re_range_char

    ret = []

    # reduce input string to remove duplicates, and put in sorted order
    s_chars: list[str] = sorted(set(s))

    if len(s_chars) > 2:
        # find groups of characters that are consecutive (can be collapsed
        # down to "<first>-<last>")
        for _, chars in itertools.groupby(s_chars, key=_GroupConsecutive()):
            # _ is unimportant, is just used to identify groups
            # chars is an iterator of one or more consecutive characters
            # that comprise the current group
            first = last = next(chars)
            with contextlib.suppress(ValueError):
                *_, last = chars

            if first == last:
                # there was only a single char in this group
                ret.append(escape_re_range_char(first))

            elif last == chr(ord(first) + 1):
                # there were only 2 characters in this group
                #   'a','b' -> 'ab'
                ret.append(f"{escape_re_range_char(first)}{escape_re_range_char(last)}")

            else:
                # there were > 2 characters in this group, make into a range
                #   'c','d','e' -> 'c-e'
                ret.append(
                    f"{escape_re_range_char(first)}-{escape_re_range_char(last)}"
                )
    else:
        # only 1 or 2 chars were given to form into groups
        #   'a' -> ['a']
        #   'bc' -> ['b', 'c']
        #   'dg' -> ['d', 'g']
        # no need to list them with "-", just return as a list
        # (after escaping)
        ret = [escape_re_range_char(c) for c in s_chars]

    return "".join(ret)


def _flatten(ll: Iterable) -> list:
    ret = []
    to_visit = [*ll]
    while to_visit:
        i = to_visit.pop(0)
        if isinstance(i, Iterable) and not isinstance(i, str):
            to_visit[:0] = i
        else:
            ret.append(i)
    return ret


def make_compressed_re(
    word_list: Iterable[str],
    max_level: int = 2,
    *,
    non_capturing_groups: bool = True,
    _level: int = 1,
) -> str:
    """
    Create a regular expression string from a list of words, collapsing by common
    prefixes and optional suffixes.

    Calls itself recursively to build nested sublists for each group of suffixes
    that have a shared prefix.
    """

    def get_suffixes_from_common_prefixes(namelist: list[str]):
        if len(namelist) > 1:
            for prefix, suffixes in itertools.groupby(namelist, key=lambda s: s[:1]):
                yield prefix, sorted([s[1:] for s in suffixes], key=len, reverse=True)
        else:
            yield namelist[0][0], [namelist[0][1:]]

    if _level == 1:
        if not word_list:
            raise ValueError("no words given to make_compressed_re()")

        if "" in word_list:
            raise ValueError("word list cannot contain empty string")
    else:
        # internal recursive call, just return empty string if no words
        if not word_list:
            return ""

    # dedupe the word list
    word_list = list({}.fromkeys(word_list))

    if max_level == 0:
        if any(len(wd) > 1 for wd in word_list):
            return "|".join(
                sorted([re.escape(wd) for wd in word_list], key=len, reverse=True)
            )
        else:
            return f"[{''.join(_escape_regex_range_chars(wd) for wd in word_list)}]"

    ret = []
    sep = ""
    ncgroup = "?:" if non_capturing_groups else ""

    for initial, suffixes in get_suffixes_from_common_prefixes(sorted(word_list)):
        ret.append(sep)
        sep = "|"

        initial = re.escape(initial)

        trailing = ""
        if "" in suffixes:
            trailing = "?"
            suffixes.remove("")

        if len(suffixes) > 1:
            if all(len(s) == 1 for s in suffixes):
                ret.append(
                    f"{initial}[{''.join(_escape_regex_range_chars(s) for s in suffixes)}]{trailing}"
                )
            else:
                if _level < max_level:
                    suffix_re = make_compressed_re(
                        sorted(suffixes),
                        max_level,
                        non_capturing_groups=non_capturing_groups,
                        _level=_level + 1,
                    )
                    ret.append(f"{initial}({ncgroup}{suffix_re}){trailing}")
                else:
                    if all(len(s) == 1 for s in suffixes):
                        ret.append(
                            f"{initial}[{''.join(_escape_regex_range_chars(s) for s in suffixes)}]{trailing}"
                        )
                    else:
                        suffixes.sort(key=len, reverse=True)
                        ret.append(
                            f"{initial}({ncgroup}{'|'.join(re.escape(s) for s in suffixes)}){trailing}"
                        )
        else:
            if suffixes:
                suffix = re.escape(suffixes[0])
                if len(suffix) > 1 and trailing:
                    ret.append(f"{initial}({ncgroup}{suffix}){trailing}")
                else:
                    ret.append(f"{initial}{suffix}{trailing}")
            else:
                ret.append(initial)
    return "".join(ret)


def replaced_by_pep8(compat_name: str, fn: C) -> C:
    # In a future version, uncomment the code in the internal _inner() functions
    # to begin emitting DeprecationWarnings.

    # Unwrap staticmethod/classmethod
    fn = getattr(fn, "__func__", fn)

    # (Presence of 'self' arg in signature is used by explain_exception() methods, so we take
    # some extra steps to add it if present in decorated function.)
    if ["self"] == list(inspect.signature(fn).parameters)[:1]:

        @wraps(fn)
        def _inner(self, *args, **kwargs):
            # warnings.warn(
            #     f"Deprecated - use {fn.__name__}", DeprecationWarning, stacklevel=2
            # )
            return fn(self, *args, **kwargs)

    else:

        @wraps(fn)
        def _inner(*args, **kwargs):
            # warnings.warn(
            #     f"Deprecated - use {fn.__name__}", DeprecationWarning, stacklevel=2
            # )
            return fn(*args, **kwargs)

    _inner.__doc__ = f"""Deprecated - use :class:`{fn.__name__}`"""
    _inner.__name__ = compat_name
    _inner.__annotations__ = fn.__annotations__
    if isinstance(fn, types.FunctionType):
        _inner.__kwdefaults__ = fn.__kwdefaults__  # type: ignore [attr-defined]
    elif isinstance(fn, type) and hasattr(fn, "__init__"):
        _inner.__kwdefaults__ = fn.__init__.__kwdefaults__  # type: ignore [misc,attr-defined]
    else:
        _inner.__kwdefaults__ = None  # type: ignore [attr-defined]
    _inner.__qualname__ = fn.__qualname__
    return cast(C, _inner)

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\s3_v2.py ===
"""
s3 Bucket Logging Integration

async_log_success_event: Processes the event, stores it in memory for DEFAULT_S3_FLUSH_INTERVAL_SECONDS seconds or until DEFAULT_S3_BATCH_SIZE and then flushes to s3 

NOTE 1: S3 does not provide a BATCH PUT API endpoint, so we create tasks to upload each element individually
"""

import asyncio
import json
from datetime import datetime
from typing import List, Optional, cast

import litellm
from litellm._logging import print_verbose, verbose_logger
from litellm.constants import DEFAULT_S3_BATCH_SIZE, DEFAULT_S3_FLUSH_INTERVAL_SECONDS
from litellm.integrations.s3 import get_s3_object_key
from litellm.llms.bedrock.base_aws_llm import BaseAWSLLM
from litellm.llms.custom_httpx.http_handler import (
    _get_httpx_client,
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.types.integrations.s3_v2 import s3BatchLoggingElement
from litellm.types.utils import StandardLoggingPayload

from .custom_batch_logger import CustomBatchLogger


class S3Logger(CustomBatchLogger, BaseAWSLLM):
    def __init__(
        self,
        s3_bucket_name: Optional[str] = None,
        s3_path: Optional[str] = None,
        s3_region_name: Optional[str] = None,
        s3_api_version: Optional[str] = None,
        s3_use_ssl: bool = True,
        s3_verify: Optional[bool] = None,
        s3_endpoint_url: Optional[str] = None,
        s3_aws_access_key_id: Optional[str] = None,
        s3_aws_secret_access_key: Optional[str] = None,
        s3_aws_session_token: Optional[str] = None,
        s3_aws_session_name: Optional[str] = None,
        s3_aws_profile_name: Optional[str] = None,
        s3_aws_role_name: Optional[str] = None,
        s3_aws_web_identity_token: Optional[str] = None,
        s3_aws_sts_endpoint: Optional[str] = None,
        s3_flush_interval: Optional[int] = DEFAULT_S3_FLUSH_INTERVAL_SECONDS,
        s3_batch_size: Optional[int] = DEFAULT_S3_BATCH_SIZE,
        s3_config=None,
        s3_use_team_prefix: bool = False,
        **kwargs,
    ):
        try:
            verbose_logger.debug(
                f"in init s3 logger - s3_callback_params {litellm.s3_callback_params}"
            )

            # IMPORTANT: We use a concurrent limit of 1 to upload to s3
            # Files should get uploaded BUT they should not impact latency of LLM calling logic
            self.async_httpx_client = get_async_httpx_client(
                llm_provider=httpxSpecialProvider.LoggingCallback,
            )

            self._init_s3_params(
                s3_bucket_name=s3_bucket_name,
                s3_region_name=s3_region_name,
                s3_api_version=s3_api_version,
                s3_use_ssl=s3_use_ssl,
                s3_verify=s3_verify,
                s3_endpoint_url=s3_endpoint_url,
                s3_aws_access_key_id=s3_aws_access_key_id,
                s3_aws_secret_access_key=s3_aws_secret_access_key,
                s3_aws_session_token=s3_aws_session_token,
                s3_aws_session_name=s3_aws_session_name,
                s3_aws_profile_name=s3_aws_profile_name,
                s3_aws_role_name=s3_aws_role_name,
                s3_aws_web_identity_token=s3_aws_web_identity_token,
                s3_aws_sts_endpoint=s3_aws_sts_endpoint,
                s3_config=s3_config,
                s3_path=s3_path,
                s3_use_team_prefix=s3_use_team_prefix,
            )
            verbose_logger.debug(f"s3 logger using endpoint url {s3_endpoint_url}")

            asyncio.create_task(self.periodic_flush())
            self.flush_lock = asyncio.Lock()

            verbose_logger.debug(
                f"s3 flush interval: {s3_flush_interval}, s3 batch size: {s3_batch_size}"
            )
            # Call CustomLogger's __init__
            CustomBatchLogger.__init__(
                self,
                flush_lock=self.flush_lock,
                flush_interval=s3_flush_interval,
                batch_size=s3_batch_size,
            )
            self.log_queue: List[s3BatchLoggingElement] = []

            # Call BaseAWSLLM's __init__
            BaseAWSLLM.__init__(self)

        except Exception as e:
            print_verbose(f"Got exception on init s3 client {str(e)}")
            raise e

    def _init_s3_params(
        self,
        s3_bucket_name: Optional[str] = None,
        s3_region_name: Optional[str] = None,
        s3_api_version: Optional[str] = None,
        s3_use_ssl: bool = True,
        s3_verify: Optional[bool] = None,
        s3_endpoint_url: Optional[str] = None,
        s3_aws_access_key_id: Optional[str] = None,
        s3_aws_secret_access_key: Optional[str] = None,
        s3_aws_session_token: Optional[str] = None,
        s3_aws_session_name: Optional[str] = None,
        s3_aws_profile_name: Optional[str] = None,
        s3_aws_role_name: Optional[str] = None,
        s3_aws_web_identity_token: Optional[str] = None,
        s3_aws_sts_endpoint: Optional[str] = None,
        s3_config=None,
        s3_path: Optional[str] = None,
        s3_use_team_prefix: bool = False,
    ):
        """
        Initialize the s3 params for this logging callback
        """
        litellm.s3_callback_params = litellm.s3_callback_params or {}
        # read in .env variables - example os.environ/AWS_BUCKET_NAME
        for key, value in litellm.s3_callback_params.items():
            if isinstance(value, str) and value.startswith("os.environ/"):
                litellm.s3_callback_params[key] = litellm.get_secret(value)

        self.s3_bucket_name = (
            litellm.s3_callback_params.get("s3_bucket_name") or s3_bucket_name
        )
        self.s3_region_name = (
            litellm.s3_callback_params.get("s3_region_name") or s3_region_name
        )
        self.s3_api_version = (
            litellm.s3_callback_params.get("s3_api_version") or s3_api_version
        )
        self.s3_use_ssl = (
            litellm.s3_callback_params.get("s3_use_ssl", True) or s3_use_ssl
        )
        self.s3_verify = litellm.s3_callback_params.get("s3_verify") or s3_verify
        self.s3_endpoint_url = (
            litellm.s3_callback_params.get("s3_endpoint_url") or s3_endpoint_url
        )
        self.s3_aws_access_key_id = (
            litellm.s3_callback_params.get("s3_aws_access_key_id")
            or s3_aws_access_key_id
        )

        self.s3_aws_secret_access_key = (
            litellm.s3_callback_params.get("s3_aws_secret_access_key")
            or s3_aws_secret_access_key
        )

        self.s3_aws_session_token = (
            litellm.s3_callback_params.get("s3_aws_session_token")
            or s3_aws_session_token
        )

        self.s3_aws_session_name = (
            litellm.s3_callback_params.get("s3_aws_session_name") or s3_aws_session_name
        )

        self.s3_aws_profile_name = (
            litellm.s3_callback_params.get("s3_aws_profile_name") or s3_aws_profile_name
        )

        self.s3_aws_role_name = (
            litellm.s3_callback_params.get("s3_aws_role_name") or s3_aws_role_name
        )

        self.s3_aws_web_identity_token = (
            litellm.s3_callback_params.get("s3_aws_web_identity_token")
            or s3_aws_web_identity_token
        )

        self.s3_aws_sts_endpoint = (
            litellm.s3_callback_params.get("s3_aws_sts_endpoint") or s3_aws_sts_endpoint
        )

        self.s3_config = litellm.s3_callback_params.get("s3_config") or s3_config
        self.s3_path = litellm.s3_callback_params.get("s3_path") or s3_path
        # done reading litellm.s3_callback_params
        self.s3_use_team_prefix = (
            bool(litellm.s3_callback_params.get("s3_use_team_prefix", False))
            or s3_use_team_prefix
        )

        return

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            verbose_logger.debug(
                f"s3 Logging - Enters logging function for model {kwargs}"
            )

            s3_batch_logging_element = self.create_s3_batch_logging_element(
                start_time=start_time,
                standard_logging_payload=kwargs.get("standard_logging_object", None),
            )

            if s3_batch_logging_element is None:
                raise ValueError("s3_batch_logging_element is None")

            verbose_logger.debug(
                "\ns3 Logger - Logging payload = %s", s3_batch_logging_element
            )

            self.log_queue.append(s3_batch_logging_element)
            verbose_logger.debug(
                "s3 logging: queue length %s, batch size %s",
                len(self.log_queue),
                self.batch_size,
            )
        except Exception as e:
            verbose_logger.exception(f"s3 Layer Error - {str(e)}")
            pass

    async def async_upload_data_to_s3(
        self, batch_logging_element: s3BatchLoggingElement
    ):
        try:
            import hashlib

            import requests
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")
        try:
            from litellm.litellm_core_utils.asyncify import asyncify

            asyncified_get_credentials = asyncify(self.get_credentials)
            credentials = await asyncified_get_credentials(
                aws_access_key_id=self.s3_aws_access_key_id,
                aws_secret_access_key=self.s3_aws_secret_access_key,
                aws_session_token=self.s3_aws_session_token,
                aws_region_name=self.s3_region_name,
                aws_session_name=self.s3_aws_session_name,
                aws_profile_name=self.s3_aws_profile_name,
                aws_role_name=self.s3_aws_role_name,
                aws_web_identity_token=self.s3_aws_web_identity_token,
                aws_sts_endpoint=self.s3_aws_sts_endpoint,
            )

            verbose_logger.debug(
                f"s3_v2 logger - uploading data to s3 - {batch_logging_element.s3_object_key}"
            )

            # Prepare the URL
            url = f"https://{self.s3_bucket_name}.s3.{self.s3_region_name}.amazonaws.com/{batch_logging_element.s3_object_key}"

            if self.s3_endpoint_url:
                url = self.s3_endpoint_url + "/" + batch_logging_element.s3_object_key

            # Convert JSON to string
            json_string = json.dumps(batch_logging_element.payload)

            # Calculate SHA256 hash of the content
            content_hash = hashlib.sha256(json_string.encode("utf-8")).hexdigest()

            # Prepare the request
            headers = {
                "Content-Type": "application/json",
                "x-amz-content-sha256": content_hash,
                "Content-Language": "en",
                "Content-Disposition": f'inline; filename="{batch_logging_element.s3_object_download_filename}"',
                "Cache-Control": "private, immutable, max-age=31536000, s-maxage=0",
            }
            req = requests.Request("PUT", url, data=json_string, headers=headers)
            prepped = req.prepare()

            # Sign the request
            aws_request = AWSRequest(
                method=prepped.method,
                url=prepped.url,
                data=prepped.body,
                headers=prepped.headers,
            )
            SigV4Auth(credentials, "s3", self.s3_region_name).add_auth(aws_request)

            # Prepare the signed headers
            signed_headers = dict(aws_request.headers.items())

            # Make the request
            response = await self.async_httpx_client.put(
                url, data=json_string, headers=signed_headers
            )
            response.raise_for_status()
        except Exception as e:
            verbose_logger.exception(f"Error uploading to s3: {str(e)}")

    async def async_send_batch(self):
        """

        Sends runs from self.log_queue

        Returns: None

        Raises: Does not raise an exception, will only verbose_logger.exception()
        """
        verbose_logger.debug(f"s3_v2 logger - sending batch of {len(self.log_queue)}")
        if not self.log_queue:
            return

        #########################################################
        #  Flush the log queue to s3
        #  the log queue can be bounded by DEFAULT_S3_BATCH_SIZE
        #  see custom_batch_logger.py which triggers the flush
        #########################################################
        for payload in self.log_queue:
            asyncio.create_task(self.async_upload_data_to_s3(payload))

    def create_s3_batch_logging_element(
        self,
        start_time: datetime,
        standard_logging_payload: Optional[StandardLoggingPayload],
    ) -> Optional[s3BatchLoggingElement]:
        """
        Helper function to create an s3BatchLoggingElement.

        Args:
            start_time (datetime): The start time of the logging event.
            standard_logging_payload (Optional[StandardLoggingPayload]): The payload to be logged.
            s3_path (Optional[str]): The S3 path prefix.

        Returns:
            Optional[s3BatchLoggingElement]: The created s3BatchLoggingElement, or None if payload is None.
        """
        if standard_logging_payload is None:
            return None

        team_alias = standard_logging_payload["metadata"].get("user_api_key_team_alias")

        team_alias_prefix = ""
        if (
            litellm.enable_preview_features
            and self.s3_use_team_prefix
            and team_alias is not None
        ):
            team_alias_prefix = f"{team_alias}/"

        s3_file_name = (
            litellm.utils.get_logging_id(start_time, standard_logging_payload) or ""
        )
        s3_object_key = get_s3_object_key(
            s3_path=cast(Optional[str], self.s3_path) or "",
            team_alias_prefix=team_alias_prefix,
            start_time=start_time,
            s3_file_name=s3_file_name,
        )

        s3_object_download_filename = (
            "time-"
            + start_time.strftime("%Y-%m-%dT%H-%M-%S-%f")
            + "_"
            + standard_logging_payload["id"]
            + ".json"
        )

        s3_object_download_filename = f"time-{start_time.strftime('%Y-%m-%dT%H-%M-%S-%f')}_{standard_logging_payload['id']}.json"

        return s3BatchLoggingElement(
            payload=dict(standard_logging_payload),
            s3_object_key=s3_object_key,
            s3_object_download_filename=s3_object_download_filename,
        )

    def upload_data_to_s3(self, batch_logging_element: s3BatchLoggingElement):
        try:
            import hashlib

            import requests
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            from botocore.credentials import Credentials
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")
        try:
            verbose_logger.debug(
                f"s3_v2 logger - uploading data to s3 - {batch_logging_element.s3_object_key}"
            )
            credentials: Credentials = self.get_credentials(
                aws_access_key_id=self.s3_aws_access_key_id,
                aws_secret_access_key=self.s3_aws_secret_access_key,
                aws_session_token=self.s3_aws_session_token,
                aws_region_name=self.s3_region_name,
            )

            # Prepare the URL
            url = f"https://{self.s3_bucket_name}.s3.{self.s3_region_name}.amazonaws.com/{batch_logging_element.s3_object_key}"

            if self.s3_endpoint_url:
                url = self.s3_endpoint_url + "/" + batch_logging_element.s3_object_key

            # Convert JSON to string
            json_string = json.dumps(batch_logging_element.payload)

            # Calculate SHA256 hash of the content
            content_hash = hashlib.sha256(json_string.encode("utf-8")).hexdigest()

            # Prepare the request
            headers = {
                "Content-Type": "application/json",
                "x-amz-content-sha256": content_hash,
                "Content-Language": "en",
                "Content-Disposition": f'inline; filename="{batch_logging_element.s3_object_download_filename}"',
                "Cache-Control": "private, immutable, max-age=31536000, s-maxage=0",
            }
            req = requests.Request("PUT", url, data=json_string, headers=headers)
            prepped = req.prepare()

            # Sign the request
            aws_request = AWSRequest(
                method=prepped.method,
                url=prepped.url,
                data=prepped.body,
                headers=prepped.headers,
            )
            SigV4Auth(credentials, "s3", self.s3_region_name).add_auth(aws_request)

            # Prepare the signed headers
            signed_headers = dict(aws_request.headers.items())

            httpx_client = _get_httpx_client()
            # Make the request
            response = httpx_client.put(url, data=json_string, headers=signed_headers)
            response.raise_for_status()
        except Exception as e:
            verbose_logger.exception(f"Error uploading to s3: {str(e)}")

# === NexusCore/openenv\Lib\site-packages\litellm\router_utils\cooldown_handlers.py ===
"""
Router cooldown handlers
- _set_cooldown_deployments: puts a deployment in the cooldown list
- get_cooldown_deployments: returns the list of deployments in the cooldown list
- async_get_cooldown_deployments: ASYNC: returns the list of deployments in the cooldown list

"""

import asyncio
from typing import TYPE_CHECKING, Any, List, Optional, Union

import litellm
from litellm._logging import verbose_router_logger
from litellm.constants import (
    DEFAULT_COOLDOWN_TIME_SECONDS,
    DEFAULT_FAILURE_THRESHOLD_PERCENT,
    SINGLE_DEPLOYMENT_TRAFFIC_FAILURE_THRESHOLD,
)
from litellm.router_utils.cooldown_callbacks import router_cooldown_event_callback

from .router_callbacks.track_deployment_metrics import (
    get_deployment_failures_for_current_minute,
    get_deployment_successes_for_current_minute,
)

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    from litellm.router import Router as _Router

    LitellmRouter = _Router
    Span = Union[_Span, Any]
else:
    LitellmRouter = Any
    Span = Any


def _is_cooldown_required(
    litellm_router_instance: LitellmRouter,
    model_id: str,
    exception_status: Union[str, int],
    exception_str: Optional[str] = None,
) -> bool:
    """
    A function to determine if a cooldown is required based on the exception status.

    Parameters:
        model_id (str) The id of the model in the model list
        exception_status (Union[str, int]): The status of the exception.

    Returns:
        bool: True if a cooldown is required, False otherwise.
    """
    try:
        ignored_strings = ["APIConnectionError"]
        if (
            exception_str is not None
        ):  # don't cooldown on litellm api connection errors errors
            for ignored_string in ignored_strings:
                if ignored_string in exception_str:
                    return False

        if isinstance(exception_status, str):
            exception_status = int(exception_status)

        if exception_status >= 400 and exception_status < 500:
            if exception_status == 429:
                # Cool down 429 Rate Limit Errors
                return True

            elif exception_status == 401:
                # Cool down 401 Auth Errors
                return True

            elif exception_status == 408:
                return True

            elif exception_status == 404:
                return True

            else:
                # Do NOT cool down all other 4XX Errors
                return False

        else:
            # should cool down for all other errors
            return True

    except Exception:
        # Catch all - if any exceptions default to cooling down
        return True


def _should_run_cooldown_logic(
    litellm_router_instance: LitellmRouter,
    deployment: Optional[str],
    exception_status: Union[str, int],
    original_exception: Any,
) -> bool:
    """
    Helper that decides if cooldown logic should be run
    Returns False if cooldown logic should not be run

    Does not run cooldown logic when:
    - router.disable_cooldowns is True
    - deployment is None
    - _is_cooldown_required() returns False
    - deployment is in litellm_router_instance.provider_default_deployment_ids
    - exception_status is not one that should be immediately retried (e.g. 401)
    """
    if (
        deployment is None
        or litellm_router_instance.get_model_group(id=deployment) is None
    ):
        verbose_router_logger.debug(
            "Should Not Run Cooldown Logic: deployment id is none or model group can't be found."
        )
        return False

    if litellm_router_instance.disable_cooldowns:
        verbose_router_logger.debug(
            "Should Not Run Cooldown Logic: disable_cooldowns is True"
        )
        return False

    if deployment is None:
        verbose_router_logger.debug("Should Not Run Cooldown Logic: deployment is None")
        return False

    if not _is_cooldown_required(
        litellm_router_instance=litellm_router_instance,
        model_id=deployment,
        exception_status=exception_status,
        exception_str=str(original_exception),
    ):
        verbose_router_logger.debug(
            "Should Not Run Cooldown Logic: _is_cooldown_required returned False"
        )
        return False

    if deployment in litellm_router_instance.provider_default_deployment_ids:
        verbose_router_logger.debug(
            "Should Not Run Cooldown Logic: deployment is in provider_default_deployment_ids"
        )
        return False

    return True


def _should_cooldown_deployment(
    litellm_router_instance: LitellmRouter,
    deployment: str,
    exception_status: Union[str, int],
    original_exception: Any,
) -> bool:
    """
    Helper that decides if a deployment should be put in cooldown

    Returns True if the deployment should be put in cooldown
    Returns False if the deployment should not be put in cooldown


    Deployment is put in cooldown when:
    - v2 logic (Current):
    cooldown if:
        - got a 429 error from LLM API
        - if %fails/%(successes + fails) > ALLOWED_FAILURE_RATE_PER_MINUTE
        - got 401 Auth error, 404 NotFounder - checked by litellm._should_retry()



    - v1 logic (Legacy): if allowed fails or allowed fail policy set, coolsdown if num fails in this minute > allowed fails
    """
    ## BASE CASE - single deployment
    model_group = litellm_router_instance.get_model_group(id=deployment)
    is_single_deployment_model_group = False
    if model_group is not None and len(model_group) == 1:
        is_single_deployment_model_group = True
    if (
        litellm_router_instance.allowed_fails_policy is None
        and _is_allowed_fails_set_on_router(
            litellm_router_instance=litellm_router_instance
        )
        is False
    ):
        num_successes_this_minute = get_deployment_successes_for_current_minute(
            litellm_router_instance=litellm_router_instance, deployment_id=deployment
        )
        num_fails_this_minute = get_deployment_failures_for_current_minute(
            litellm_router_instance=litellm_router_instance, deployment_id=deployment
        )

        total_requests_this_minute = num_successes_this_minute + num_fails_this_minute
        percent_fails = 0.0
        if total_requests_this_minute > 0:
            percent_fails = num_fails_this_minute / (
                num_successes_this_minute + num_fails_this_minute
            )
        verbose_router_logger.debug(
            "percent fails for deployment = %s, percent fails = %s, num successes = %s, num fails = %s",
            deployment,
            percent_fails,
            num_successes_this_minute,
            num_fails_this_minute,
        )

        exception_status_int = cast_exception_status_to_int(exception_status)
        if exception_status_int == 429 and not is_single_deployment_model_group:
            return True
        elif (
            percent_fails == 1.0
            and total_requests_this_minute
            >= SINGLE_DEPLOYMENT_TRAFFIC_FAILURE_THRESHOLD
        ):
            # Cooldown if all requests failed and we have reasonable traffic
            return True
        elif (
            percent_fails > DEFAULT_FAILURE_THRESHOLD_PERCENT
            and not is_single_deployment_model_group  # by default we should avoid cooldowns on single deployment model groups
        ):
            return True

        elif (
            litellm._should_retry(
                status_code=cast_exception_status_to_int(exception_status)
            )
            is False
        ):
            return True

        return False
    else:
        return should_cooldown_based_on_allowed_fails_policy(
            litellm_router_instance=litellm_router_instance,
            deployment=deployment,
            original_exception=original_exception,
        )

    return False


def _set_cooldown_deployments(
    litellm_router_instance: LitellmRouter,
    original_exception: Any,
    exception_status: Union[str, int],
    deployment: Optional[str] = None,
    time_to_cooldown: Optional[float] = None,
) -> bool:
    """
    Add a model to the list of models being cooled down for that minute, if it exceeds the allowed fails / minute

    or

    the exception is not one that should be immediately retried (e.g. 401)

    Returns:
    - True if the deployment should be put in cooldown
    - False if the deployment should not be put in cooldown
    """
    verbose_router_logger.debug("checks 'should_run_cooldown_logic'")

    if (
        _should_run_cooldown_logic(
            litellm_router_instance, deployment, exception_status, original_exception
        )
        is False
        or deployment is None
    ):
        verbose_router_logger.debug("should_run_cooldown_logic returned False")
        return False

    exception_status_int = cast_exception_status_to_int(exception_status)

    verbose_router_logger.debug(f"Attempting to add {deployment} to cooldown list")
    cooldown_time = litellm_router_instance.cooldown_time or 1
    if time_to_cooldown is not None:
        cooldown_time = time_to_cooldown

    if _should_cooldown_deployment(
        litellm_router_instance, deployment, exception_status, original_exception
    ):
        litellm_router_instance.cooldown_cache.add_deployment_to_cooldown(
            model_id=deployment,
            original_exception=original_exception,
            exception_status=exception_status_int,
            cooldown_time=cooldown_time,
        )

        # Trigger cooldown callback handler
        asyncio.create_task(
            router_cooldown_event_callback(
                litellm_router_instance=litellm_router_instance,
                deployment_id=deployment,
                exception_status=exception_status,
                cooldown_time=cooldown_time,
            )
        )
        return True
    return False


async def _async_get_cooldown_deployments(
    litellm_router_instance: LitellmRouter,
    parent_otel_span: Optional[Span],
) -> List[str]:
    """
    Async implementation of '_get_cooldown_deployments'
    """
    model_ids = litellm_router_instance.get_model_ids()
    cooldown_models = (
        await litellm_router_instance.cooldown_cache.async_get_active_cooldowns(
            model_ids=model_ids,
            parent_otel_span=parent_otel_span,
        )
    )

    cached_value_deployment_ids = []
    if (
        cooldown_models is not None
        and isinstance(cooldown_models, list)
        and len(cooldown_models) > 0
        and isinstance(cooldown_models[0], tuple)
    ):
        cached_value_deployment_ids = [cv[0] for cv in cooldown_models]

    verbose_router_logger.debug(f"retrieve cooldown models: {cooldown_models}")
    return cached_value_deployment_ids


async def _async_get_cooldown_deployments_with_debug_info(
    litellm_router_instance: LitellmRouter,
    parent_otel_span: Optional[Span],
) -> List[tuple]:
    """
    Async implementation of '_get_cooldown_deployments'
    """
    model_ids = litellm_router_instance.get_model_ids()
    cooldown_models = (
        await litellm_router_instance.cooldown_cache.async_get_active_cooldowns(
            model_ids=model_ids, parent_otel_span=parent_otel_span
        )
    )

    verbose_router_logger.debug(f"retrieve cooldown models: {cooldown_models}")
    return cooldown_models


def _get_cooldown_deployments(
    litellm_router_instance: LitellmRouter, parent_otel_span: Optional[Span]
) -> List[str]:
    """
    Get the list of models being cooled down for this minute
    """
    # get the current cooldown list for that minute

    # ----------------------
    # Return cooldown models
    # ----------------------
    model_ids = litellm_router_instance.get_model_ids()

    cooldown_models = litellm_router_instance.cooldown_cache.get_active_cooldowns(
        model_ids=model_ids, parent_otel_span=parent_otel_span
    )

    cached_value_deployment_ids = []
    if (
        cooldown_models is not None
        and isinstance(cooldown_models, list)
        and len(cooldown_models) > 0
        and isinstance(cooldown_models[0], tuple)
    ):
        cached_value_deployment_ids = [cv[0] for cv in cooldown_models]

    return cached_value_deployment_ids


def should_cooldown_based_on_allowed_fails_policy(
    litellm_router_instance: LitellmRouter,
    deployment: str,
    original_exception: Any,
) -> bool:
    """
    Check if fails are within the allowed limit and update the number of fails.

    Returns:
    - True if fails exceed the allowed limit (should cooldown)
    - False if fails are within the allowed limit (should not cooldown)
    """
    allowed_fails = (
        litellm_router_instance.get_allowed_fails_from_policy(
            exception=original_exception,
        )
        or litellm_router_instance.allowed_fails
    )
    cooldown_time = (
        litellm_router_instance.cooldown_time or DEFAULT_COOLDOWN_TIME_SECONDS
    )

    current_fails = litellm_router_instance.failed_calls.get_cache(key=deployment) or 0
    updated_fails = current_fails + 1

    if updated_fails > allowed_fails:
        return True
    else:
        litellm_router_instance.failed_calls.set_cache(
            key=deployment, value=updated_fails, ttl=cooldown_time
        )

    return False


def _is_allowed_fails_set_on_router(
    litellm_router_instance: LitellmRouter,
) -> bool:
    """
    Check if Router.allowed_fails is set or is Non-default Value

    Returns:
    - True if Router.allowed_fails is set or is Non-default Value
    - False if Router.allowed_fails is None or is Default Value
    """
    if litellm_router_instance.allowed_fails is None:
        return False
    if litellm_router_instance.allowed_fails != litellm.allowed_fails:
        return True
    return False


def cast_exception_status_to_int(exception_status: Union[str, int]) -> int:
    if isinstance(exception_status, str):
        try:
            exception_status = int(exception_status)
        except Exception:
            verbose_router_logger.debug(
                f"Unable to cast exception status to int {exception_status}. Defaulting to status=500."
            )
            exception_status = 500
    return exception_status

# === NexusCore/openenv\Lib\site-packages\openai\_utils\_utils.py ===
from __future__ import annotations

import os
import re
import inspect
import functools
from typing import (
    TYPE_CHECKING,
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
from datetime import date, datetime
from typing_extensions import TypeGuard

import sniffio

from .._types import NotGiven, FileTypes, NotGivenOr, HeadersLike
from .._compat import parse_date as parse_date, parse_datetime as parse_datetime

_T = TypeVar("_T")
_TupleT = TypeVar("_TupleT", bound=Tuple[object, ...])
_MappingT = TypeVar("_MappingT", bound=Mapping[str, object])
_SequenceT = TypeVar("_SequenceT", bound=Sequence[object])
CallableT = TypeVar("CallableT", bound=Callable[..., Any])

if TYPE_CHECKING:
    from ..lib.azure import AzureOpenAI, AsyncAzureOpenAI


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
        assert flattened_key is not None

        if is_list(obj):
            files: list[tuple[str, FileTypes]] = []
            for entry in obj:
                assert_is_file_content(entry, key=flattened_key + "[]" if flattened_key else "")
                files.append((flattened_key + "[]", cast(FileTypes, entry)))
            return files

        assert_is_file_content(obj, key=flattened_key)
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


def json_safe(data: object) -> object:
    """Translates a mapping / sequence recursively in the same fashion
    as `pydantic` v2's `model_dump(mode="json")`.
    """
    if is_mapping(data):
        return {json_safe(key): json_safe(value) for key, value in data.items()}

    if is_iterable(data) and not isinstance(data, (str, bytes, bytearray)):
        return [json_safe(item) for item in data]

    if isinstance(data, (datetime, date)):
        return data.isoformat()

    return data


def is_azure_client(client: object) -> TypeGuard[AzureOpenAI]:
    from ..lib.azure import AzureOpenAI

    return isinstance(client, AzureOpenAI)


def is_async_azure_client(client: object) -> TypeGuard[AsyncAzureOpenAI]:
    from ..lib.azure import AsyncAzureOpenAI

    return isinstance(client, AsyncAzureOpenAI)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\completion\base.py ===
""" """

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import AsyncGenerator, Callable, Iterable, Sequence

from prompt_toolkit.document import Document
from prompt_toolkit.eventloop import aclosing, generator_to_async_generator
from prompt_toolkit.filters import FilterOrBool, to_filter
from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples

__all__ = [
    "Completion",
    "Completer",
    "ThreadedCompleter",
    "DummyCompleter",
    "DynamicCompleter",
    "CompleteEvent",
    "ConditionalCompleter",
    "merge_completers",
    "get_common_complete_suffix",
]


class Completion:
    """
    :param text: The new string that will be inserted into the document.
    :param start_position: Position relative to the cursor_position where the
        new text will start. The text will be inserted between the
        start_position and the original cursor position.
    :param display: (optional string or formatted text) If the completion has
        to be displayed differently in the completion menu.
    :param display_meta: (Optional string or formatted text) Meta information
        about the completion, e.g. the path or source where it's coming from.
        This can also be a callable that returns a string.
    :param style: Style string.
    :param selected_style: Style string, used for a selected completion.
        This can override the `style` parameter.
    """

    def __init__(
        self,
        text: str,
        start_position: int = 0,
        display: AnyFormattedText | None = None,
        display_meta: AnyFormattedText | None = None,
        style: str = "",
        selected_style: str = "",
    ) -> None:
        from prompt_toolkit.formatted_text import to_formatted_text

        self.text = text
        self.start_position = start_position
        self._display_meta = display_meta

        if display is None:
            display = text

        self.display = to_formatted_text(display)

        self.style = style
        self.selected_style = selected_style

        assert self.start_position <= 0

    def __repr__(self) -> str:
        if isinstance(self.display, str) and self.display == self.text:
            return f"{self.__class__.__name__}(text={self.text!r}, start_position={self.start_position!r})"
        else:
            return f"{self.__class__.__name__}(text={self.text!r}, start_position={self.start_position!r}, display={self.display!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Completion):
            return False
        return (
            self.text == other.text
            and self.start_position == other.start_position
            and self.display == other.display
            and self._display_meta == other._display_meta
        )

    def __hash__(self) -> int:
        return hash((self.text, self.start_position, self.display, self._display_meta))

    @property
    def display_text(self) -> str:
        "The 'display' field as plain text."
        from prompt_toolkit.formatted_text import fragment_list_to_text

        return fragment_list_to_text(self.display)

    @property
    def display_meta(self) -> StyleAndTextTuples:
        "Return meta-text. (This is lazy when using a callable)."
        from prompt_toolkit.formatted_text import to_formatted_text

        return to_formatted_text(self._display_meta or "")

    @property
    def display_meta_text(self) -> str:
        "The 'meta' field as plain text."
        from prompt_toolkit.formatted_text import fragment_list_to_text

        return fragment_list_to_text(self.display_meta)

    def new_completion_from_position(self, position: int) -> Completion:
        """
        (Only for internal use!)
        Get a new completion by splitting this one. Used by `Application` when
        it needs to have a list of new completions after inserting the common
        prefix.
        """
        assert position - self.start_position >= 0

        return Completion(
            text=self.text[position - self.start_position :],
            display=self.display,
            display_meta=self._display_meta,
        )


class CompleteEvent:
    """
    Event that called the completer.

    :param text_inserted: When True, it means that completions are requested
        because of a text insert. (`Buffer.complete_while_typing`.)
    :param completion_requested: When True, it means that the user explicitly
        pressed the `Tab` key in order to view the completions.

    These two flags can be used for instance to implement a completer that
    shows some completions when ``Tab`` has been pressed, but not
    automatically when the user presses a space. (Because of
    `complete_while_typing`.)
    """

    def __init__(
        self, text_inserted: bool = False, completion_requested: bool = False
    ) -> None:
        assert not (text_inserted and completion_requested)

        #: Automatic completion while typing.
        self.text_inserted = text_inserted

        #: Used explicitly requested completion by pressing 'tab'.
        self.completion_requested = completion_requested

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(text_inserted={self.text_inserted!r}, completion_requested={self.completion_requested!r})"


class Completer(metaclass=ABCMeta):
    """
    Base class for completer implementations.
    """

    @abstractmethod
    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """
        This should be a generator that yields :class:`.Completion` instances.

        If the generation of completions is something expensive (that takes a
        lot of time), consider wrapping this `Completer` class in a
        `ThreadedCompleter`. In that case, the completer algorithm runs in a
        background thread and completions will be displayed as soon as they
        arrive.

        :param document: :class:`~prompt_toolkit.document.Document` instance.
        :param complete_event: :class:`.CompleteEvent` instance.
        """
        while False:
            yield

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> AsyncGenerator[Completion, None]:
        """
        Asynchronous generator for completions. (Probably, you won't have to
        override this.)

        Asynchronous generator of :class:`.Completion` objects.
        """
        for item in self.get_completions(document, complete_event):
            yield item


class ThreadedCompleter(Completer):
    """
    Wrapper that runs the `get_completions` generator in a thread.

    (Use this to prevent the user interface from becoming unresponsive if the
    generation of completions takes too much time.)

    The completions will be displayed as soon as they are produced. The user
    can already select a completion, even if not all completions are displayed.
    """

    def __init__(self, completer: Completer) -> None:
        self.completer = completer

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        return self.completer.get_completions(document, complete_event)

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> AsyncGenerator[Completion, None]:
        """
        Asynchronous generator of completions.
        """
        # NOTE: Right now, we are consuming the `get_completions` generator in
        #       a synchronous background thread, then passing the results one
        #       at a time over a queue, and consuming this queue in the main
        #       thread (that's what `generator_to_async_generator` does). That
        #       means that if the completer is *very* slow, we'll be showing
        #       completions in the UI once they are computed.

        #       It's very tempting to replace this implementation with the
        #       commented code below for several reasons:

        #       - `generator_to_async_generator` is not perfect and hard to get
        #         right. It's a lot of complexity for little gain. The
        #         implementation needs a huge buffer for it to be efficient
        #         when there are many completions (like 50k+).
        #       - Normally, a completer is supposed to be fast, users can have
        #         "complete while typing" enabled, and want to see the
        #         completions within a second. Handling one completion at a
        #         time, and rendering once we get it here doesn't make any
        #         sense if this is quick anyway.
        #       - Completers like `FuzzyCompleter` prepare all completions
        #         anyway so that they can be sorted by accuracy before they are
        #         yielded. At the point that we start yielding completions
        #         here, we already have all completions.
        #       - The `Buffer` class has complex logic to invalidate the UI
        #         while it is consuming the completions. We don't want to
        #         invalidate the UI for every completion (if there are many),
        #         but we want to do it often enough so that completions are
        #         being displayed while they are produced.

        #       We keep the current behavior mainly for backward-compatibility.
        #       Similarly, it would be better for this function to not return
        #       an async generator, but simply be a coroutine that returns a
        #       list of `Completion` objects, containing all completions at
        #       once.

        #       Note that this argument doesn't mean we shouldn't use
        #       `ThreadedCompleter`. It still makes sense to produce
        #       completions in a background thread, because we don't want to
        #       freeze the UI while the user is typing. But sending the
        #       completions one at a time to the UI maybe isn't worth it.

        # def get_all_in_thread() -> List[Completion]:
        #   return list(self.get_completions(document, complete_event))

        # completions = await get_running_loop().run_in_executor(None, get_all_in_thread)
        # for completion in completions:
        #   yield completion

        async with aclosing(
            generator_to_async_generator(
                lambda: self.completer.get_completions(document, complete_event)
            )
        ) as async_generator:
            async for completion in async_generator:
                yield completion

    def __repr__(self) -> str:
        return f"ThreadedCompleter({self.completer!r})"


class DummyCompleter(Completer):
    """
    A completer that doesn't return any completion.
    """

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        return []

    def __repr__(self) -> str:
        return "DummyCompleter()"


class DynamicCompleter(Completer):
    """
    Completer class that can dynamically returns any Completer.

    :param get_completer: Callable that returns a :class:`.Completer` instance.
    """

    def __init__(self, get_completer: Callable[[], Completer | None]) -> None:
        self.get_completer = get_completer

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        completer = self.get_completer() or DummyCompleter()
        return completer.get_completions(document, complete_event)

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> AsyncGenerator[Completion, None]:
        completer = self.get_completer() or DummyCompleter()

        async for completion in completer.get_completions_async(
            document, complete_event
        ):
            yield completion

    def __repr__(self) -> str:
        return f"DynamicCompleter({self.get_completer!r} -> {self.get_completer()!r})"


class ConditionalCompleter(Completer):
    """
    Wrapper around any other completer that will enable/disable the completions
    depending on whether the received condition is satisfied.

    :param completer: :class:`.Completer` instance.
    :param filter: :class:`.Filter` instance.
    """

    def __init__(self, completer: Completer, filter: FilterOrBool) -> None:
        self.completer = completer
        self.filter = to_filter(filter)

    def __repr__(self) -> str:
        return f"ConditionalCompleter({self.completer!r}, filter={self.filter!r})"

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        # Get all completions in a blocking way.
        if self.filter():
            yield from self.completer.get_completions(document, complete_event)

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> AsyncGenerator[Completion, None]:
        # Get all completions in a non-blocking way.
        if self.filter():
            async with aclosing(
                self.completer.get_completions_async(document, complete_event)
            ) as async_generator:
                async for item in async_generator:
                    yield item


class _MergedCompleter(Completer):
    """
    Combine several completers into one.
    """

    def __init__(self, completers: Sequence[Completer]) -> None:
        self.completers = completers

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        # Get all completions from the other completers in a blocking way.
        for completer in self.completers:
            yield from completer.get_completions(document, complete_event)

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> AsyncGenerator[Completion, None]:
        # Get all completions from the other completers in a non-blocking way.
        for completer in self.completers:
            async with aclosing(
                completer.get_completions_async(document, complete_event)
            ) as async_generator:
                async for item in async_generator:
                    yield item


def merge_completers(
    completers: Sequence[Completer], deduplicate: bool = False
) -> Completer:
    """
    Combine several completers into one.

    :param deduplicate: If `True`, wrap the result in a `DeduplicateCompleter`
        so that completions that would result in the same text will be
        deduplicated.
    """
    if deduplicate:
        from .deduplicate import DeduplicateCompleter

        return DeduplicateCompleter(_MergedCompleter(completers))

    return _MergedCompleter(completers)


def get_common_complete_suffix(
    document: Document, completions: Sequence[Completion]
) -> str:
    """
    Return the common prefix for all completions.
    """

    # Take only completions that don't change the text before the cursor.
    def doesnt_change_before_cursor(completion: Completion) -> bool:
        end = completion.text[: -completion.start_position]
        return document.text_before_cursor.endswith(end)

    completions2 = [c for c in completions if doesnt_change_before_cursor(c)]

    # When there is at least one completion that changes the text before the
    # cursor, don't return any common part.
    if len(completions2) != len(completions):
        return ""

    # Return the common prefix.
    def get_suffix(completion: Completion) -> str:
        return completion.text[-completion.start_position :]

    return _commonprefix([get_suffix(c) for c in completions2])


def _commonprefix(strings: Iterable[str]) -> str:
    # Similar to os.path.commonprefix
    if not strings:
        return ""

    else:
        s1 = min(strings)
        s2 = max(strings)

        for i, c in enumerate(s1):
            if c != s2[i]:
                return s1[:i]

        return s1

# === NexusCore/openenv\Lib\site-packages\win32comext\axscript\client\pyscript.py ===
"""Python ActiveX Scripting Implementation

This module implements the Python ActiveX Scripting client.

To register the implementation, simply "run" this Python program - ie
either double-click on it, or run "python.exe pyscript.py" from the
command line.
"""

import re
import types

import pythoncom
import win32com
import win32com.client.dynamic
import win32com.server.register
import winerror
from win32com.axscript import axscript
from win32com.axscript.client import framework, scriptdispatch
from win32com.axscript.client.framework import (
    SCRIPTTEXT_FORCEEXECUTION,
    SCRIPTTEXT_ISEXPRESSION,
    SCRIPTTEXT_ISPERSISTENT,
    trace,
)
from win32com.server.exception import COMException

PyScript_CLSID = "{DF630910-1C1D-11d0-AE36-8C0F5E000000}"

debugging_attr = 0


def debug_attr_print(*args):
    if debugging_attr:
        trace(*args)


def ExpandTabs(text):
    return re.sub(r"\t", "    ", text)


def AddCR(text):
    return re.sub(r"\n", "\r\n", text)


class AXScriptCodeBlock(framework.AXScriptCodeBlock):
    def GetDisplayName(self):
        return "PyScript - " + framework.AXScriptCodeBlock.GetDisplayName(self)


# There is only ever _one_ ax object - it exists in the global namespace
# for all script items.
# It performs a search from all global/visible objects
# down.
# This means that if 2 sub-objects of the same name are used
# then only one is ever reachable using the ax shortcut.
class AXScriptAttribute:
    "An attribute in a scripts namespace."

    def __init__(self, engine):
        self.__dict__["_scriptEngine_"] = engine

    def __getattr__(self, attr):
        if attr[1] == "_" and attr[:-1] == "_":
            raise AttributeError(attr)
        rc = self._FindAttribute_(attr)
        if rc is None:
            raise AttributeError(attr)
        return rc

    def _Close_(self):
        self.__dict__["_scriptEngine_"] = None

    def _DoFindAttribute_(self, obj, attr):
        try:
            return obj.subItems[attr.lower()].attributeObject
        except KeyError:
            pass
        # Check out the sub-items
        for item in obj.subItems.values():
            try:
                return self._DoFindAttribute_(item, attr)
            except AttributeError:
                pass
        raise AttributeError(attr)

    def _FindAttribute_(self, attr):
        for item in self._scriptEngine_.subItems.values():
            try:
                return self._DoFindAttribute_(item, attr)
            except AttributeError:
                pass
        # All else fails, see if it is a global
        # (mainly b/w compat)
        return getattr(self._scriptEngine_.globalNameSpaceModule, attr)


# 		raise AttributeError(attr)


class NamedScriptAttribute:
    "An explicitly named object in an objects namespace"

    # Each named object holds a reference to one of these.
    # Whenever a sub-item appears in a namespace, it is really one of these
    # objects.  Has a circular reference back to the item itself, which is
    # closed via _Close_()
    def __init__(self, scriptItem):
        self.__dict__["_scriptItem_"] = scriptItem

    def __repr__(self):
        return f"<NamedItemAttribute{self._scriptItem_!r}>"

    def __getattr__(self, attr):
        # If a known subitem, return it.
        try:
            return self._scriptItem_.subItems[attr.lower()].attributeObject
        except KeyError:
            # Otherwise see if the dispatch can give it to us
            if self._scriptItem_.dispatchContainer:
                return getattr(self._scriptItem_.dispatchContainer, attr)
        raise AttributeError(attr)

    def __setattr__(self, attr, value):
        # XXX - todo - if a known item, then should call its default
        # dispatch method.
        attr = attr.lower()
        if self._scriptItem_.dispatchContainer:
            try:
                return setattr(self._scriptItem_.dispatchContainer, attr, value)
            except AttributeError:
                pass
        raise AttributeError(attr)

    def _Close_(self):
        self.__dict__["_scriptItem_"] = None


class ScriptItem(framework.ScriptItem):
    def __init__(self, parentItem, name, dispatch, flags):
        framework.ScriptItem.__init__(self, parentItem, name, dispatch, flags)
        self.scriptlets = {}
        self.attributeObject = None

    def Reset(self):
        framework.ScriptItem.Reset(self)
        if self.attributeObject:
            self.attributeObject._Close_()
        self.attributeObject = None

    def Close(self):
        framework.ScriptItem.Close(self)  # calls reset.
        self.dispatchContainer = None
        self.scriptlets = {}

    def Register(self):
        framework.ScriptItem.Register(self)
        self.attributeObject = NamedScriptAttribute(self)
        if self.dispatch:
            # Need to avoid the new Python "lazy" dispatch behaviour.
            olerepr, clsid = None
            try:
                engine = self.GetEngine()
                typeinfo = self.dispatch.GetTypeInfo()
                clsid = typeinfo.GetTypeAttr()[0]
                olerepr = engine.mapKnownCOMTypes.get(clsid)
            except pythoncom.com_error:
                typeinfo = None
            if olerepr is None:
                olerepr = win32com.client.dynamic.MakeOleRepr(
                    self.dispatch, typeinfo, None
                )
                if clsid is not None:
                    engine.mapKnownCOMTypes[clsid] = olerepr
            self.dispatchContainer = win32com.client.dynamic.CDispatch(
                self.dispatch, olerepr, self.name
            )


# 			self.dispatchContainer = win32com.client.dynamic.Dispatch(self.dispatch, userName = self.name)
# 			self.dispatchContainer = win32com.client.dynamic.DumbDispatch(self.dispatch, userName = self.name)

# 	def Connect(self):
# 		framework.ScriptItem.Connect(self)
# 	def Disconnect(self):
# 		framework.ScriptItem.Disconnect(self)


class PyScript(framework.COMScript):
    # Setup the auto-registration stuff...
    _reg_verprogid_ = "Python.AXScript.2"
    _reg_progid_ = "Python"
    # 	_reg_policy_spec_ = default
    _reg_catids_ = [axscript.CATID_ActiveScript, axscript.CATID_ActiveScriptParse]
    _reg_desc_ = "Python ActiveX Scripting Engine"
    _reg_clsid_ = PyScript_CLSID
    _reg_class_spec_ = "win32com.axscript.client.pyscript.PyScript"
    _reg_remove_keys_ = [(".pys",), ("pysFile",)]
    _reg_threading_ = "both"

    def __init__(self):
        framework.COMScript.__init__(self)
        self.globalNameSpaceModule = None
        self.codeBlocks = []
        self.scriptDispatch = None

    def InitNew(self):
        framework.COMScript.InitNew(self)

        self.scriptDispatch = None
        self.globalNameSpaceModule = types.ModuleType("__ax_main__")
        self.globalNameSpaceModule.__dict__["ax"] = AXScriptAttribute(self)

        self.codeBlocks = []
        self.persistedCodeBlocks = []
        self.mapKnownCOMTypes = {}  # Map of known CLSID to typereprs
        self.codeBlockCounter = 0

    def Stop(self):
        # Flag every pending script as already done
        for b in self.codeBlocks:
            b.beenExecuted = 1
        return framework.COMScript.Stop(self)

    def Reset(self):
        # Reset all code-blocks that are persistent, and discard the rest
        oldCodeBlocks = self.codeBlocks[:]
        self.codeBlocks = []
        for b in oldCodeBlocks:
            if b.flags & SCRIPTTEXT_ISPERSISTENT:
                b.beenExecuted = 0
                self.codeBlocks.append(b)
        return framework.COMScript.Reset(self)

    def _GetNextCodeBlockNumber(self):
        self.codeBlockCounter += 1
        return self.codeBlockCounter

    def RegisterNamedItem(self, item):
        wasReg = item.isRegistered
        framework.COMScript.RegisterNamedItem(self, item)
        if not wasReg:
            # Insert into our namespace.
            # Add every item by name
            if item.IsVisible():
                self.globalNameSpaceModule.__dict__[item.name] = item.attributeObject
            if item.IsGlobal():
                # Global items means sub-items are also added...
                for subitem in item.subItems.values():
                    self.globalNameSpaceModule.__dict__[subitem.name] = (
                        subitem.attributeObject
                    )
                # Also add all methods
                for name, entry in item.dispatchContainer._olerepr_.mapFuncs.items():
                    if not entry.hidden:
                        self.globalNameSpaceModule.__dict__[name] = getattr(
                            item.dispatchContainer, name
                        )

    def DoExecutePendingScripts(self):
        try:
            globs = self.globalNameSpaceModule.__dict__
            for codeBlock in self.codeBlocks:
                if not codeBlock.beenExecuted:
                    if self.CompileInScriptedSection(codeBlock, "exec"):
                        self.ExecInScriptedSection(codeBlock, globs)
        finally:
            pass

    def DoRun(self):
        pass

    def Close(self):
        self.ResetNamespace()
        self.globalNameSpaceModule = None
        self.codeBlocks = []
        self.scriptDispatch = None
        framework.COMScript.Close(self)

    def GetScriptDispatch(self, name):
        # 		trace("GetScriptDispatch with", name)
        # 		if name is not None: return None
        if self.scriptDispatch is None:
            self.scriptDispatch = scriptdispatch.MakeScriptDispatch(
                self, self.globalNameSpaceModule
            )
        return self.scriptDispatch

    def MakeEventMethodName(self, subItemName, eventName):
        return (
            subItemName[0].upper()
            + subItemName[1:]
            + "_"
            + eventName[0].upper()
            + eventName[1:]
        )

    def DoAddScriptlet(
        self,
        defaultName,
        code,
        itemName,
        subItemName,
        eventName,
        delimiter,
        sourceContextCookie,
        startLineNumber,
    ):
        # Just store the code away - compile when called.  (JIT :-)
        item = self.GetNamedItem(itemName)
        if (
            itemName == subItemName
        ):  # Explicit handlers - eg <SCRIPT LANGUAGE="Python" for="TestForm" Event="onSubmit">
            subItem = item
        else:
            subItem = item.GetCreateSubItem(item, subItemName, None, None)
        funcName = self.MakeEventMethodName(subItemName, eventName)

        codeBlock = AXScriptCodeBlock(
            "Script Event %s" % funcName, code, sourceContextCookie, startLineNumber, 0
        )
        self._AddScriptCodeBlock(codeBlock)
        subItem.scriptlets[funcName] = codeBlock

    def DoProcessScriptItemEvent(self, item, event, lcid, wFlags, args):
        # 		trace("ScriptItemEvent", self, item, event, event.name, lcid, wFlags, args)
        funcName = self.MakeEventMethodName(item.name, event.name)
        codeBlock = function = None
        try:
            function = item.scriptlets[funcName]
            if isinstance(function, PyScript):  # ie, is a CodeBlock instance
                codeBlock = function
                function = None
        except KeyError:
            pass
        if codeBlock is not None:
            realCode = "def %s():\n" % funcName
            for line in framework.RemoveCR(codeBlock.codeText).split("\n"):
                realCode += "\t" + line + "\n"
            realCode += "\n"
            if not self.CompileInScriptedSection(codeBlock, "exec", realCode):
                return
            dict = {}
            self.ExecInScriptedSection(
                codeBlock, self.globalNameSpaceModule.__dict__, dict
            )
            function = dict[funcName]
            # cache back in scriptlets as a function.
            item.scriptlets[funcName] = function
        if function is None:
            # still no function - see if in the global namespace.
            try:
                function = self.globalNameSpaceModule.__dict__[funcName]
            except KeyError:
                # Not there _exactly_ - do case ins search.
                funcNameLook = funcName.lower()
                for attr in self.globalNameSpaceModule.__dict__:
                    if funcNameLook == attr.lower():
                        function = self.globalNameSpaceModule.__dict__[attr]
                        # cache back in scriptlets, to avoid this overhead next time
                        item.scriptlets[funcName] = function

        if function is None:
            raise COMException(scode=winerror.DISP_E_MEMBERNOTFOUND)
        return self.ApplyInScriptedSection(codeBlock, function, args)

    def DoParseScriptText(
        self, code, sourceContextCookie, startLineNumber, bWantResult, flags
    ):
        code = framework.RemoveCR(code) + "\n"
        if flags & SCRIPTTEXT_ISEXPRESSION:
            name = "Script Expression"
            exec_type = "eval"
        else:
            name = "Script Block"
            exec_type = "exec"
        num = self._GetNextCodeBlockNumber()
        if num == 1:
            num = ""
        name += f" {num}"
        codeBlock = AXScriptCodeBlock(
            name, code, sourceContextCookie, startLineNumber, flags
        )
        self._AddScriptCodeBlock(codeBlock)
        globs = self.globalNameSpaceModule.__dict__
        if bWantResult:  # always immediate.
            if self.CompileInScriptedSection(codeBlock, exec_type):
                if flags & SCRIPTTEXT_ISEXPRESSION:
                    return self.EvalInScriptedSection(codeBlock, globs)
                else:
                    return self.ExecInScriptedSection(codeBlock, globs)

            # else compile failed, but user chose to keep running...
        else:
            if flags & SCRIPTTEXT_FORCEEXECUTION:
                if self.CompileInScriptedSection(codeBlock, exec_type):
                    self.ExecInScriptedSection(codeBlock, globs)
            else:
                self.codeBlocks.append(codeBlock)

    def GetNamedItemClass(self):
        return ScriptItem

    def ResetNamespace(self):
        if self.globalNameSpaceModule is not None:
            try:
                self.globalNameSpaceModule.ax._Reset_()
            except AttributeError:
                pass  # ???
            globalNameSpaceModule = None


def DllRegisterServer():
    klass = PyScript
    win32com.server.register._set_subkeys(
        klass._reg_progid_ + "\\OLEScript", {}
    )  # Just a CreateKey
    # Basic Registration for wsh.
    win32com.server.register._set_string(".pys", "pysFile")
    win32com.server.register._set_string("pysFile\\ScriptEngine", klass._reg_progid_)
    guid_wsh_shellex = "{60254CA5-953B-11CF-8C96-00AA00B8708C}"
    win32com.server.register._set_string(
        "pysFile\\ShellEx\\DropHandler", guid_wsh_shellex
    )
    win32com.server.register._set_string(
        "pysFile\\ShellEx\\PropertySheetHandlers\\WSHProps", guid_wsh_shellex
    )


def Register(klass=PyScript):
    ret = win32com.server.register.UseCommandLine(
        klass, finalize_register=DllRegisterServer
    )
    return ret


if __name__ == "__main__":
    Register()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\idna\core.py ===
import bisect
import re
import unicodedata
from typing import Optional, Union

from . import idnadata
from .intranges import intranges_contain

_virama_combining_class = 9
_alabel_prefix = b"xn--"
_unicode_dots_re = re.compile("[\u002e\u3002\uff0e\uff61]")


class IDNAError(UnicodeError):
    """Base exception for all IDNA-encoding related problems"""

    pass


class IDNABidiError(IDNAError):
    """Exception when bidirectional requirements are not satisfied"""

    pass


class InvalidCodepoint(IDNAError):
    """Exception when a disallowed or unallocated codepoint is used"""

    pass


class InvalidCodepointContext(IDNAError):
    """Exception when the codepoint is not valid in the context it is used"""

    pass


def _combining_class(cp: int) -> int:
    v = unicodedata.combining(chr(cp))
    if v == 0:
        if not unicodedata.name(chr(cp)):
            raise ValueError("Unknown character in unicodedata")
    return v


def _is_script(cp: str, script: str) -> bool:
    return intranges_contain(ord(cp), idnadata.scripts[script])


def _punycode(s: str) -> bytes:
    return s.encode("punycode")


def _unot(s: int) -> str:
    return "U+{:04X}".format(s)


def valid_label_length(label: Union[bytes, str]) -> bool:
    if len(label) > 63:
        return False
    return True


def valid_string_length(label: Union[bytes, str], trailing_dot: bool) -> bool:
    if len(label) > (254 if trailing_dot else 253):
        return False
    return True


def check_bidi(label: str, check_ltr: bool = False) -> bool:
    # Bidi rules should only be applied if string contains RTL characters
    bidi_label = False
    for idx, cp in enumerate(label, 1):
        direction = unicodedata.bidirectional(cp)
        if direction == "":
            # String likely comes from a newer version of Unicode
            raise IDNABidiError("Unknown directionality in label {} at position {}".format(repr(label), idx))
        if direction in ["R", "AL", "AN"]:
            bidi_label = True
    if not bidi_label and not check_ltr:
        return True

    # Bidi rule 1
    direction = unicodedata.bidirectional(label[0])
    if direction in ["R", "AL"]:
        rtl = True
    elif direction == "L":
        rtl = False
    else:
        raise IDNABidiError("First codepoint in label {} must be directionality L, R or AL".format(repr(label)))

    valid_ending = False
    number_type: Optional[str] = None
    for idx, cp in enumerate(label, 1):
        direction = unicodedata.bidirectional(cp)

        if rtl:
            # Bidi rule 2
            if direction not in [
                "R",
                "AL",
                "AN",
                "EN",
                "ES",
                "CS",
                "ET",
                "ON",
                "BN",
                "NSM",
            ]:
                raise IDNABidiError("Invalid direction for codepoint at position {} in a right-to-left label".format(idx))
            # Bidi rule 3
            if direction in ["R", "AL", "EN", "AN"]:
                valid_ending = True
            elif direction != "NSM":
                valid_ending = False
            # Bidi rule 4
            if direction in ["AN", "EN"]:
                if not number_type:
                    number_type = direction
                else:
                    if number_type != direction:
                        raise IDNABidiError("Can not mix numeral types in a right-to-left label")
        else:
            # Bidi rule 5
            if direction not in ["L", "EN", "ES", "CS", "ET", "ON", "BN", "NSM"]:
                raise IDNABidiError("Invalid direction for codepoint at position {} in a left-to-right label".format(idx))
            # Bidi rule 6
            if direction in ["L", "EN"]:
                valid_ending = True
            elif direction != "NSM":
                valid_ending = False

    if not valid_ending:
        raise IDNABidiError("Label ends with illegal codepoint directionality")

    return True


def check_initial_combiner(label: str) -> bool:
    if unicodedata.category(label[0])[0] == "M":
        raise IDNAError("Label begins with an illegal combining character")
    return True


def check_hyphen_ok(label: str) -> bool:
    if label[2:4] == "--":
        raise IDNAError("Label has disallowed hyphens in 3rd and 4th position")
    if label[0] == "-" or label[-1] == "-":
        raise IDNAError("Label must not start or end with a hyphen")
    return True


def check_nfc(label: str) -> None:
    if unicodedata.normalize("NFC", label) != label:
        raise IDNAError("Label must be in Normalization Form C")


def valid_contextj(label: str, pos: int) -> bool:
    cp_value = ord(label[pos])

    if cp_value == 0x200C:
        if pos > 0:
            if _combining_class(ord(label[pos - 1])) == _virama_combining_class:
                return True

        ok = False
        for i in range(pos - 1, -1, -1):
            joining_type = idnadata.joining_types.get(ord(label[i]))
            if joining_type == ord("T"):
                continue
            elif joining_type in [ord("L"), ord("D")]:
                ok = True
                break
            else:
                break

        if not ok:
            return False

        ok = False
        for i in range(pos + 1, len(label)):
            joining_type = idnadata.joining_types.get(ord(label[i]))
            if joining_type == ord("T"):
                continue
            elif joining_type in [ord("R"), ord("D")]:
                ok = True
                break
            else:
                break
        return ok

    if cp_value == 0x200D:
        if pos > 0:
            if _combining_class(ord(label[pos - 1])) == _virama_combining_class:
                return True
        return False

    else:
        return False


def valid_contexto(label: str, pos: int, exception: bool = False) -> bool:
    cp_value = ord(label[pos])

    if cp_value == 0x00B7:
        if 0 < pos < len(label) - 1:
            if ord(label[pos - 1]) == 0x006C and ord(label[pos + 1]) == 0x006C:
                return True
        return False

    elif cp_value == 0x0375:
        if pos < len(label) - 1 and len(label) > 1:
            return _is_script(label[pos + 1], "Greek")
        return False

    elif cp_value == 0x05F3 or cp_value == 0x05F4:
        if pos > 0:
            return _is_script(label[pos - 1], "Hebrew")
        return False

    elif cp_value == 0x30FB:
        for cp in label:
            if cp == "\u30fb":
                continue
            if _is_script(cp, "Hiragana") or _is_script(cp, "Katakana") or _is_script(cp, "Han"):
                return True
        return False

    elif 0x660 <= cp_value <= 0x669:
        for cp in label:
            if 0x6F0 <= ord(cp) <= 0x06F9:
                return False
        return True

    elif 0x6F0 <= cp_value <= 0x6F9:
        for cp in label:
            if 0x660 <= ord(cp) <= 0x0669:
                return False
        return True

    return False


def check_label(label: Union[str, bytes, bytearray]) -> None:
    if isinstance(label, (bytes, bytearray)):
        label = label.decode("utf-8")
    if len(label) == 0:
        raise IDNAError("Empty Label")

    check_nfc(label)
    check_hyphen_ok(label)
    check_initial_combiner(label)

    for pos, cp in enumerate(label):
        cp_value = ord(cp)
        if intranges_contain(cp_value, idnadata.codepoint_classes["PVALID"]):
            continue
        elif intranges_contain(cp_value, idnadata.codepoint_classes["CONTEXTJ"]):
            try:
                if not valid_contextj(label, pos):
                    raise InvalidCodepointContext(
                        "Joiner {} not allowed at position {} in {}".format(_unot(cp_value), pos + 1, repr(label))
                    )
            except ValueError:
                raise IDNAError(
                    "Unknown codepoint adjacent to joiner {} at position {} in {}".format(
                        _unot(cp_value), pos + 1, repr(label)
                    )
                )
        elif intranges_contain(cp_value, idnadata.codepoint_classes["CONTEXTO"]):
            if not valid_contexto(label, pos):
                raise InvalidCodepointContext(
                    "Codepoint {} not allowed at position {} in {}".format(_unot(cp_value), pos + 1, repr(label))
                )
        else:
            raise InvalidCodepoint(
                "Codepoint {} at position {} of {} not allowed".format(_unot(cp_value), pos + 1, repr(label))
            )

    check_bidi(label)


def alabel(label: str) -> bytes:
    try:
        label_bytes = label.encode("ascii")
        ulabel(label_bytes)
        if not valid_label_length(label_bytes):
            raise IDNAError("Label too long")
        return label_bytes
    except UnicodeEncodeError:
        pass

    check_label(label)
    label_bytes = _alabel_prefix + _punycode(label)

    if not valid_label_length(label_bytes):
        raise IDNAError("Label too long")

    return label_bytes


def ulabel(label: Union[str, bytes, bytearray]) -> str:
    if not isinstance(label, (bytes, bytearray)):
        try:
            label_bytes = label.encode("ascii")
        except UnicodeEncodeError:
            check_label(label)
            return label
    else:
        label_bytes = label

    label_bytes = label_bytes.lower()
    if label_bytes.startswith(_alabel_prefix):
        label_bytes = label_bytes[len(_alabel_prefix) :]
        if not label_bytes:
            raise IDNAError("Malformed A-label, no Punycode eligible content found")
        if label_bytes.decode("ascii")[-1] == "-":
            raise IDNAError("A-label must not end with a hyphen")
    else:
        check_label(label_bytes)
        return label_bytes.decode("ascii")

    try:
        label = label_bytes.decode("punycode")
    except UnicodeError:
        raise IDNAError("Invalid A-label")
    check_label(label)
    return label


def uts46_remap(domain: str, std3_rules: bool = True, transitional: bool = False) -> str:
    """Re-map the characters in the string according to UTS46 processing."""
    from .uts46data import uts46data

    output = ""

    for pos, char in enumerate(domain):
        code_point = ord(char)
        try:
            uts46row = uts46data[code_point if code_point < 256 else bisect.bisect_left(uts46data, (code_point, "Z")) - 1]
            status = uts46row[1]
            replacement: Optional[str] = None
            if len(uts46row) == 3:
                replacement = uts46row[2]
            if (
                status == "V"
                or (status == "D" and not transitional)
                or (status == "3" and not std3_rules and replacement is None)
            ):
                output += char
            elif replacement is not None and (
                status == "M" or (status == "3" and not std3_rules) or (status == "D" and transitional)
            ):
                output += replacement
            elif status != "I":
                raise IndexError()
        except IndexError:
            raise InvalidCodepoint(
                "Codepoint {} not allowed at position {} in {}".format(_unot(code_point), pos + 1, repr(domain))
            )

    return unicodedata.normalize("NFC", output)


def encode(
    s: Union[str, bytes, bytearray],
    strict: bool = False,
    uts46: bool = False,
    std3_rules: bool = False,
    transitional: bool = False,
) -> bytes:
    if not isinstance(s, str):
        try:
            s = str(s, "ascii")
        except UnicodeDecodeError:
            raise IDNAError("should pass a unicode string to the function rather than a byte string.")
    if uts46:
        s = uts46_remap(s, std3_rules, transitional)
    trailing_dot = False
    result = []
    if strict:
        labels = s.split(".")
    else:
        labels = _unicode_dots_re.split(s)
    if not labels or labels == [""]:
        raise IDNAError("Empty domain")
    if labels[-1] == "":
        del labels[-1]
        trailing_dot = True
    for label in labels:
        s = alabel(label)
        if s:
            result.append(s)
        else:
            raise IDNAError("Empty label")
    if trailing_dot:
        result.append(b"")
    s = b".".join(result)
    if not valid_string_length(s, trailing_dot):
        raise IDNAError("Domain too long")
    return s


def decode(
    s: Union[str, bytes, bytearray],
    strict: bool = False,
    uts46: bool = False,
    std3_rules: bool = False,
) -> str:
    try:
        if not isinstance(s, str):
            s = str(s, "ascii")
    except UnicodeDecodeError:
        raise IDNAError("Invalid ASCII in A-label")
    if uts46:
        s = uts46_remap(s, std3_rules, False)
    trailing_dot = False
    result = []
    if not strict:
        labels = _unicode_dots_re.split(s)
    else:
        labels = s.split(".")
    if not labels or labels == [""]:
        raise IDNAError("Empty domain")
    if not labels[-1]:
        del labels[-1]
        trailing_dot = True
    for label in labels:
        s = ulabel(label)
        if s:
            result.append(s)
        else:
            raise IDNAError("Empty label")
    if trailing_dot:
        result.append("")
    return ".".join(result)

# === NexusCore/openenv\Lib\site-packages\idna\core.py ===
import bisect
import re
import unicodedata
from typing import Optional, Union

from . import idnadata
from .intranges import intranges_contain

_virama_combining_class = 9
_alabel_prefix = b"xn--"
_unicode_dots_re = re.compile("[\u002e\u3002\uff0e\uff61]")


class IDNAError(UnicodeError):
    """Base exception for all IDNA-encoding related problems"""

    pass


class IDNABidiError(IDNAError):
    """Exception when bidirectional requirements are not satisfied"""

    pass


class InvalidCodepoint(IDNAError):
    """Exception when a disallowed or unallocated codepoint is used"""

    pass


class InvalidCodepointContext(IDNAError):
    """Exception when the codepoint is not valid in the context it is used"""

    pass


def _combining_class(cp: int) -> int:
    v = unicodedata.combining(chr(cp))
    if v == 0:
        if not unicodedata.name(chr(cp)):
            raise ValueError("Unknown character in unicodedata")
    return v


def _is_script(cp: str, script: str) -> bool:
    return intranges_contain(ord(cp), idnadata.scripts[script])


def _punycode(s: str) -> bytes:
    return s.encode("punycode")


def _unot(s: int) -> str:
    return "U+{:04X}".format(s)


def valid_label_length(label: Union[bytes, str]) -> bool:
    if len(label) > 63:
        return False
    return True


def valid_string_length(label: Union[bytes, str], trailing_dot: bool) -> bool:
    if len(label) > (254 if trailing_dot else 253):
        return False
    return True


def check_bidi(label: str, check_ltr: bool = False) -> bool:
    # Bidi rules should only be applied if string contains RTL characters
    bidi_label = False
    for idx, cp in enumerate(label, 1):
        direction = unicodedata.bidirectional(cp)
        if direction == "":
            # String likely comes from a newer version of Unicode
            raise IDNABidiError("Unknown directionality in label {} at position {}".format(repr(label), idx))
        if direction in ["R", "AL", "AN"]:
            bidi_label = True
    if not bidi_label and not check_ltr:
        return True

    # Bidi rule 1
    direction = unicodedata.bidirectional(label[0])
    if direction in ["R", "AL"]:
        rtl = True
    elif direction == "L":
        rtl = False
    else:
        raise IDNABidiError("First codepoint in label {} must be directionality L, R or AL".format(repr(label)))

    valid_ending = False
    number_type: Optional[str] = None
    for idx, cp in enumerate(label, 1):
        direction = unicodedata.bidirectional(cp)

        if rtl:
            # Bidi rule 2
            if direction not in [
                "R",
                "AL",
                "AN",
                "EN",
                "ES",
                "CS",
                "ET",
                "ON",
                "BN",
                "NSM",
            ]:
                raise IDNABidiError("Invalid direction for codepoint at position {} in a right-to-left label".format(idx))
            # Bidi rule 3
            if direction in ["R", "AL", "EN", "AN"]:
                valid_ending = True
            elif direction != "NSM":
                valid_ending = False
            # Bidi rule 4
            if direction in ["AN", "EN"]:
                if not number_type:
                    number_type = direction
                else:
                    if number_type != direction:
                        raise IDNABidiError("Can not mix numeral types in a right-to-left label")
        else:
            # Bidi rule 5
            if direction not in ["L", "EN", "ES", "CS", "ET", "ON", "BN", "NSM"]:
                raise IDNABidiError("Invalid direction for codepoint at position {} in a left-to-right label".format(idx))
            # Bidi rule 6
            if direction in ["L", "EN"]:
                valid_ending = True
            elif direction != "NSM":
                valid_ending = False

    if not valid_ending:
        raise IDNABidiError("Label ends with illegal codepoint directionality")

    return True


def check_initial_combiner(label: str) -> bool:
    if unicodedata.category(label[0])[0] == "M":
        raise IDNAError("Label begins with an illegal combining character")
    return True


def check_hyphen_ok(label: str) -> bool:
    if label[2:4] == "--":
        raise IDNAError("Label has disallowed hyphens in 3rd and 4th position")
    if label[0] == "-" or label[-1] == "-":
        raise IDNAError("Label must not start or end with a hyphen")
    return True


def check_nfc(label: str) -> None:
    if unicodedata.normalize("NFC", label) != label:
        raise IDNAError("Label must be in Normalization Form C")


def valid_contextj(label: str, pos: int) -> bool:
    cp_value = ord(label[pos])

    if cp_value == 0x200C:
        if pos > 0:
            if _combining_class(ord(label[pos - 1])) == _virama_combining_class:
                return True

        ok = False
        for i in range(pos - 1, -1, -1):
            joining_type = idnadata.joining_types.get(ord(label[i]))
            if joining_type == ord("T"):
                continue
            elif joining_type in [ord("L"), ord("D")]:
                ok = True
                break
            else:
                break

        if not ok:
            return False

        ok = False
        for i in range(pos + 1, len(label)):
            joining_type = idnadata.joining_types.get(ord(label[i]))
            if joining_type == ord("T"):
                continue
            elif joining_type in [ord("R"), ord("D")]:
                ok = True
                break
            else:
                break
        return ok

    if cp_value == 0x200D:
        if pos > 0:
            if _combining_class(ord(label[pos - 1])) == _virama_combining_class:
                return True
        return False

    else:
        return False


def valid_contexto(label: str, pos: int, exception: bool = False) -> bool:
    cp_value = ord(label[pos])

    if cp_value == 0x00B7:
        if 0 < pos < len(label) - 1:
            if ord(label[pos - 1]) == 0x006C and ord(label[pos + 1]) == 0x006C:
                return True
        return False

    elif cp_value == 0x0375:
        if pos < len(label) - 1 and len(label) > 1:
            return _is_script(label[pos + 1], "Greek")
        return False

    elif cp_value == 0x05F3 or cp_value == 0x05F4:
        if pos > 0:
            return _is_script(label[pos - 1], "Hebrew")
        return False

    elif cp_value == 0x30FB:
        for cp in label:
            if cp == "\u30fb":
                continue
            if _is_script(cp, "Hiragana") or _is_script(cp, "Katakana") or _is_script(cp, "Han"):
                return True
        return False

    elif 0x660 <= cp_value <= 0x669:
        for cp in label:
            if 0x6F0 <= ord(cp) <= 0x06F9:
                return False
        return True

    elif 0x6F0 <= cp_value <= 0x6F9:
        for cp in label:
            if 0x660 <= ord(cp) <= 0x0669:
                return False
        return True

    return False


def check_label(label: Union[str, bytes, bytearray]) -> None:
    if isinstance(label, (bytes, bytearray)):
        label = label.decode("utf-8")
    if len(label) == 0:
        raise IDNAError("Empty Label")

    check_nfc(label)
    check_hyphen_ok(label)
    check_initial_combiner(label)

    for pos, cp in enumerate(label):
        cp_value = ord(cp)
        if intranges_contain(cp_value, idnadata.codepoint_classes["PVALID"]):
            continue
        elif intranges_contain(cp_value, idnadata.codepoint_classes["CONTEXTJ"]):
            try:
                if not valid_contextj(label, pos):
                    raise InvalidCodepointContext(
                        "Joiner {} not allowed at position {} in {}".format(_unot(cp_value), pos + 1, repr(label))
                    )
            except ValueError:
                raise IDNAError(
                    "Unknown codepoint adjacent to joiner {} at position {} in {}".format(
                        _unot(cp_value), pos + 1, repr(label)
                    )
                )
        elif intranges_contain(cp_value, idnadata.codepoint_classes["CONTEXTO"]):
            if not valid_contexto(label, pos):
                raise InvalidCodepointContext(
                    "Codepoint {} not allowed at position {} in {}".format(_unot(cp_value), pos + 1, repr(label))
                )
        else:
            raise InvalidCodepoint(
                "Codepoint {} at position {} of {} not allowed".format(_unot(cp_value), pos + 1, repr(label))
            )

    check_bidi(label)


def alabel(label: str) -> bytes:
    try:
        label_bytes = label.encode("ascii")
        ulabel(label_bytes)
        if not valid_label_length(label_bytes):
            raise IDNAError("Label too long")
        return label_bytes
    except UnicodeEncodeError:
        pass

    check_label(label)
    label_bytes = _alabel_prefix + _punycode(label)

    if not valid_label_length(label_bytes):
        raise IDNAError("Label too long")

    return label_bytes


def ulabel(label: Union[str, bytes, bytearray]) -> str:
    if not isinstance(label, (bytes, bytearray)):
        try:
            label_bytes = label.encode("ascii")
        except UnicodeEncodeError:
            check_label(label)
            return label
    else:
        label_bytes = label

    label_bytes = label_bytes.lower()
    if label_bytes.startswith(_alabel_prefix):
        label_bytes = label_bytes[len(_alabel_prefix) :]
        if not label_bytes:
            raise IDNAError("Malformed A-label, no Punycode eligible content found")
        if label_bytes.decode("ascii")[-1] == "-":
            raise IDNAError("A-label must not end with a hyphen")
    else:
        check_label(label_bytes)
        return label_bytes.decode("ascii")

    try:
        label = label_bytes.decode("punycode")
    except UnicodeError:
        raise IDNAError("Invalid A-label")
    check_label(label)
    return label


def uts46_remap(domain: str, std3_rules: bool = True, transitional: bool = False) -> str:
    """Re-map the characters in the string according to UTS46 processing."""
    from .uts46data import uts46data

    output = ""

    for pos, char in enumerate(domain):
        code_point = ord(char)
        try:
            uts46row = uts46data[code_point if code_point < 256 else bisect.bisect_left(uts46data, (code_point, "Z")) - 1]
            status = uts46row[1]
            replacement: Optional[str] = None
            if len(uts46row) == 3:
                replacement = uts46row[2]
            if (
                status == "V"
                or (status == "D" and not transitional)
                or (status == "3" and not std3_rules and replacement is None)
            ):
                output += char
            elif replacement is not None and (
                status == "M" or (status == "3" and not std3_rules) or (status == "D" and transitional)
            ):
                output += replacement
            elif status != "I":
                raise IndexError()
        except IndexError:
            raise InvalidCodepoint(
                "Codepoint {} not allowed at position {} in {}".format(_unot(code_point), pos + 1, repr(domain))
            )

    return unicodedata.normalize("NFC", output)


def encode(
    s: Union[str, bytes, bytearray],
    strict: bool = False,
    uts46: bool = False,
    std3_rules: bool = False,
    transitional: bool = False,
) -> bytes:
    if not isinstance(s, str):
        try:
            s = str(s, "ascii")
        except UnicodeDecodeError:
            raise IDNAError("should pass a unicode string to the function rather than a byte string.")
    if uts46:
        s = uts46_remap(s, std3_rules, transitional)
    trailing_dot = False
    result = []
    if strict:
        labels = s.split(".")
    else:
        labels = _unicode_dots_re.split(s)
    if not labels or labels == [""]:
        raise IDNAError("Empty domain")
    if labels[-1] == "":
        del labels[-1]
        trailing_dot = True
    for label in labels:
        s = alabel(label)
        if s:
            result.append(s)
        else:
            raise IDNAError("Empty label")
    if trailing_dot:
        result.append(b"")
    s = b".".join(result)
    if not valid_string_length(s, trailing_dot):
        raise IDNAError("Domain too long")
    return s


def decode(
    s: Union[str, bytes, bytearray],
    strict: bool = False,
    uts46: bool = False,
    std3_rules: bool = False,
) -> str:
    try:
        if not isinstance(s, str):
            s = str(s, "ascii")
    except UnicodeDecodeError:
        raise IDNAError("Invalid ASCII in A-label")
    if uts46:
        s = uts46_remap(s, std3_rules, False)
    trailing_dot = False
    result = []
    if not strict:
        labels = _unicode_dots_re.split(s)
    else:
        labels = s.split(".")
    if not labels or labels == [""]:
        raise IDNAError("Empty domain")
    if not labels[-1]:
        del labels[-1]
        trailing_dot = True
    for label in labels:
        s = ulabel(label)
        if s:
            result.append(s)
        else:
            raise IDNAError("Empty label")
    if trailing_dot:
        result.append("")
    return ".".join(result)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\base_llm\chat\transformation.py ===
"""
Common base config for all LLM providers
"""

import types
from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

import httpx
from pydantic import BaseModel

from litellm.constants import DEFAULT_MAX_TOKENS, RESPONSE_FORMAT_TOOL_NAME
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler
from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionToolChoiceFunctionParam,
    ChatCompletionToolChoiceObjectParam,
    ChatCompletionToolParam,
    ChatCompletionToolParamFunctionChunk,
)

if TYPE_CHECKING:
    from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
    from litellm.types.utils import ModelResponse

from ..base_utils import (
    map_developer_role_to_system_role,
    type_to_response_format_param,
)

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class BaseLLMException(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        headers: Optional[Union[dict, httpx.Headers]] = None,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
        body: Optional[dict] = None,
    ):
        self.status_code = status_code
        self.message: str = message
        self.headers = headers
        if request:
            self.request = request
        else:
            self.request = httpx.Request(
                method="POST", url="https://docs.litellm.ai/docs"
            )
        if response:
            self.response = response
        else:
            self.response = httpx.Response(
                status_code=status_code, request=self.request
            )
        self.body = body
        super().__init__(
            self.message
        )  # Call the base class constructor with the parameters it needs


class BaseConfig(ABC):
    def __init__(self):
        pass

    @classmethod
    def get_config(cls):
        return {
            k: v
            for k, v in cls.__dict__.items()
            if not k.startswith("__")
            and not k.startswith("_abc")
            and not k.startswith("_is_base_class")
            and not isinstance(
                v,
                (
                    types.FunctionType,
                    types.BuiltinFunctionType,
                    classmethod,
                    staticmethod,
                    property,
                ),
            )
            and v is not None
        }

    def get_json_schema_from_pydantic_object(
        self, response_format: Optional[Union[Type[BaseModel], dict]]
    ) -> Optional[dict]:
        return type_to_response_format_param(response_format=response_format)

    def is_thinking_enabled(self, non_default_params: dict) -> bool:
        return (
            non_default_params.get("thinking", {}).get("type") == "enabled"
            or non_default_params.get("reasoning_effort") is not None
        )

    def is_max_tokens_in_request(self, non_default_params: dict) -> bool:
        """
        OpenAI spec allows max_tokens or max_completion_tokens to be specified.
        """
        return (
            "max_tokens" in non_default_params
            or "max_completion_tokens" in non_default_params
        )

    def update_optional_params_with_thinking_tokens(
        self, non_default_params: dict, optional_params: dict
    ):
        """
        Handles scenario where max tokens is not specified. For anthropic models (anthropic api/bedrock/vertex ai), this requires having the max tokens being set and being greater than the thinking token budget.

        Checks 'non_default_params' for 'thinking' and 'max_tokens'

        if 'thinking' is enabled and 'max_tokens' is not specified, set 'max_tokens' to the thinking token budget + DEFAULT_MAX_TOKENS
        """
        is_thinking_enabled = self.is_thinking_enabled(optional_params)
        if is_thinking_enabled and "max_tokens" not in non_default_params:
            thinking_token_budget = cast(dict, optional_params["thinking"]).get(
                "budget_tokens", None
            )
            if thinking_token_budget is not None:
                optional_params["max_tokens"] = (
                    thinking_token_budget + DEFAULT_MAX_TOKENS
                )

    def should_fake_stream(
        self,
        model: Optional[str],
        stream: Optional[bool],
        custom_llm_provider: Optional[str] = None,
    ) -> bool:
        """
        Returns True if the model/provider should fake stream
        """
        return False

    def _add_tools_to_optional_params(self, optional_params: dict, tools: List) -> dict:
        """
        Helper util to add tools to optional_params.
        """
        if "tools" not in optional_params:
            optional_params["tools"] = tools
        else:
            optional_params["tools"] = [
                *optional_params["tools"],
                *tools,
            ]
        return optional_params

    def translate_developer_role_to_system_role(
        self,
        messages: List[AllMessageValues],
    ) -> List[AllMessageValues]:
        """
        Translate `developer` role to `system` role for non-OpenAI providers.

        Overriden by OpenAI/Azure
        """
        return map_developer_role_to_system_role(messages=messages)

    def should_retry_llm_api_inside_llm_translation_on_http_error(
        self, e: httpx.HTTPStatusError, litellm_params: dict
    ) -> bool:
        """
        Returns True if the model/provider should retry the LLM API on UnprocessableEntityError

        Overriden by azure ai - where different models support different parameters
        """
        return False

    def transform_request_on_unprocessable_entity_error(
        self, e: httpx.HTTPStatusError, request_data: dict
    ) -> dict:
        """
        Transform the request data on UnprocessableEntityError
        """
        return request_data

    @property
    def max_retry_on_unprocessable_entity_error(self) -> int:
        """
        Returns the max retry count for UnprocessableEntityError

        Used if `should_retry_llm_api_inside_llm_translation_on_http_error` is True
        """
        return 0

    @abstractmethod
    def get_supported_openai_params(self, model: str) -> list:
        pass

    def _add_response_format_to_tools(
        self,
        optional_params: dict,
        value: dict,
        is_response_format_supported: bool,
        enforce_tool_choice: bool = True,
    ) -> dict:
        """
        Follow similar approach to anthropic - translate to a single tool call.

        When using tools in this way: - https://docs.anthropic.com/en/docs/build-with-claude/tool-use#json-mode
        - You usually want to provide a single tool
        - You should set tool_choice (see Forcing tool use) to instruct the model to explicitly use that tool
        - Remember that the model will pass the input to the tool, so the name of the tool and description should be from the model’s perspective.

        Add response format to tools

        This is used to translate response_format to a tool call, for models/APIs that don't support response_format directly.
        """
        json_schema: Optional[dict] = None
        if "response_schema" in value:
            json_schema = value["response_schema"]
        elif "json_schema" in value:
            json_schema = value["json_schema"]["schema"]

        if json_schema and not is_response_format_supported:
            _tool_choice = ChatCompletionToolChoiceObjectParam(
                type="function",
                function=ChatCompletionToolChoiceFunctionParam(
                    name=RESPONSE_FORMAT_TOOL_NAME
                ),
            )

            _tool = ChatCompletionToolParam(
                type="function",
                function=ChatCompletionToolParamFunctionChunk(
                    name=RESPONSE_FORMAT_TOOL_NAME, parameters=json_schema
                ),
            )

            optional_params.setdefault("tools", [])
            optional_params["tools"].append(_tool)
            if enforce_tool_choice:
                optional_params["tool_choice"] = _tool_choice

            optional_params["json_mode"] = True
        elif is_response_format_supported:
            optional_params["response_format"] = value
        return optional_params

    @abstractmethod
    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        pass

    @abstractmethod
    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        pass

    def sign_request(
        self,
        headers: dict,
        optional_params: dict,
        request_data: dict,
        api_base: str,
        model: Optional[str] = None,
        stream: Optional[bool] = None,
        fake_stream: Optional[bool] = None,
    ) -> Tuple[dict, Optional[bytes]]:
        """
        Some providers like Bedrock require signing the request. The sign request funtion needs access to `request_data` and `complete_url`
        Args:
            headers: dict
            optional_params: dict
            request_data: dict - the request body being sent in http request
            api_base: str - the complete url being sent in http request
        Returns:
            dict - the signed headers

        Update the headers with the signed headers in this function. The return values will be sent as headers in the http request.
        """
        return headers, None

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        """
        OPTIONAL

        Get the complete url for the request

        Some providers need `model` in `api_base`
        """
        if api_base is None:
            raise ValueError("api_base is required")
        return api_base

    @abstractmethod
    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        pass

    async def async_transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        """
        Override to allow for http requests on async calls - e.g. converting url to base64

        Currently only used by openai.py
        """
        return self.transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            headers=headers,
        )

    @abstractmethod
    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: "ModelResponse",
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> "ModelResponse":
        pass

    @abstractmethod
    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        pass

    def get_model_response_iterator(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], "ModelResponse"],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ) -> Any:
        pass

    async def get_async_custom_stream_wrapper(
        self,
        model: str,
        custom_llm_provider: str,
        logging_obj: LiteLLMLoggingObj,
        api_base: str,
        headers: dict,
        data: dict,
        messages: list,
        client: Optional[AsyncHTTPHandler] = None,
        json_mode: Optional[bool] = None,
        signed_json_body: Optional[bytes] = None,
    ) -> "CustomStreamWrapper":
        raise NotImplementedError

    def get_sync_custom_stream_wrapper(
        self,
        model: str,
        custom_llm_provider: str,
        logging_obj: LiteLLMLoggingObj,
        api_base: str,
        headers: dict,
        data: dict,
        messages: list,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        json_mode: Optional[bool] = None,
        signed_json_body: Optional[bytes] = None,
    ) -> "CustomStreamWrapper":
        raise NotImplementedError

    @property
    def custom_llm_provider(self) -> Optional[str]:
        return None

    @property
    def has_custom_stream_wrapper(self) -> bool:
        return False

    @property
    def supports_stream_param_in_request_body(self) -> bool:
        """
        Some providers like Bedrock invoke do not support the stream parameter in the request body.

        By default, this is true for almost all providers.
        """
        return True

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\idna\core.py ===
import bisect
import re
import unicodedata
from typing import Optional, Union

from . import idnadata
from .intranges import intranges_contain

_virama_combining_class = 9
_alabel_prefix = b"xn--"
_unicode_dots_re = re.compile("[\u002e\u3002\uff0e\uff61]")


class IDNAError(UnicodeError):
    """Base exception for all IDNA-encoding related problems"""

    pass


class IDNABidiError(IDNAError):
    """Exception when bidirectional requirements are not satisfied"""

    pass


class InvalidCodepoint(IDNAError):
    """Exception when a disallowed or unallocated codepoint is used"""

    pass


class InvalidCodepointContext(IDNAError):
    """Exception when the codepoint is not valid in the context it is used"""

    pass


def _combining_class(cp: int) -> int:
    v = unicodedata.combining(chr(cp))
    if v == 0:
        if not unicodedata.name(chr(cp)):
            raise ValueError("Unknown character in unicodedata")
    return v


def _is_script(cp: str, script: str) -> bool:
    return intranges_contain(ord(cp), idnadata.scripts[script])


def _punycode(s: str) -> bytes:
    return s.encode("punycode")


def _unot(s: int) -> str:
    return "U+{:04X}".format(s)


def valid_label_length(label: Union[bytes, str]) -> bool:
    if len(label) > 63:
        return False
    return True


def valid_string_length(label: Union[bytes, str], trailing_dot: bool) -> bool:
    if len(label) > (254 if trailing_dot else 253):
        return False
    return True


def check_bidi(label: str, check_ltr: bool = False) -> bool:
    # Bidi rules should only be applied if string contains RTL characters
    bidi_label = False
    for idx, cp in enumerate(label, 1):
        direction = unicodedata.bidirectional(cp)
        if direction == "":
            # String likely comes from a newer version of Unicode
            raise IDNABidiError("Unknown directionality in label {} at position {}".format(repr(label), idx))
        if direction in ["R", "AL", "AN"]:
            bidi_label = True
    if not bidi_label and not check_ltr:
        return True

    # Bidi rule 1
    direction = unicodedata.bidirectional(label[0])
    if direction in ["R", "AL"]:
        rtl = True
    elif direction == "L":
        rtl = False
    else:
        raise IDNABidiError("First codepoint in label {} must be directionality L, R or AL".format(repr(label)))

    valid_ending = False
    number_type: Optional[str] = None
    for idx, cp in enumerate(label, 1):
        direction = unicodedata.bidirectional(cp)

        if rtl:
            # Bidi rule 2
            if direction not in [
                "R",
                "AL",
                "AN",
                "EN",
                "ES",
                "CS",
                "ET",
                "ON",
                "BN",
                "NSM",
            ]:
                raise IDNABidiError("Invalid direction for codepoint at position {} in a right-to-left label".format(idx))
            # Bidi rule 3
            if direction in ["R", "AL", "EN", "AN"]:
                valid_ending = True
            elif direction != "NSM":
                valid_ending = False
            # Bidi rule 4
            if direction in ["AN", "EN"]:
                if not number_type:
                    number_type = direction
                else:
                    if number_type != direction:
                        raise IDNABidiError("Can not mix numeral types in a right-to-left label")
        else:
            # Bidi rule 5
            if direction not in ["L", "EN", "ES", "CS", "ET", "ON", "BN", "NSM"]:
                raise IDNABidiError("Invalid direction for codepoint at position {} in a left-to-right label".format(idx))
            # Bidi rule 6
            if direction in ["L", "EN"]:
                valid_ending = True
            elif direction != "NSM":
                valid_ending = False

    if not valid_ending:
        raise IDNABidiError("Label ends with illegal codepoint directionality")

    return True


def check_initial_combiner(label: str) -> bool:
    if unicodedata.category(label[0])[0] == "M":
        raise IDNAError("Label begins with an illegal combining character")
    return True


def check_hyphen_ok(label: str) -> bool:
    if label[2:4] == "--":
        raise IDNAError("Label has disallowed hyphens in 3rd and 4th position")
    if label[0] == "-" or label[-1] == "-":
        raise IDNAError("Label must not start or end with a hyphen")
    return True


def check_nfc(label: str) -> None:
    if unicodedata.normalize("NFC", label) != label:
        raise IDNAError("Label must be in Normalization Form C")


def valid_contextj(label: str, pos: int) -> bool:
    cp_value = ord(label[pos])

    if cp_value == 0x200C:
        if pos > 0:
            if _combining_class(ord(label[pos - 1])) == _virama_combining_class:
                return True

        ok = False
        for i in range(pos - 1, -1, -1):
            joining_type = idnadata.joining_types.get(ord(label[i]))
            if joining_type == ord("T"):
                continue
            elif joining_type in [ord("L"), ord("D")]:
                ok = True
                break
            else:
                break

        if not ok:
            return False

        ok = False
        for i in range(pos + 1, len(label)):
            joining_type = idnadata.joining_types.get(ord(label[i]))
            if joining_type == ord("T"):
                continue
            elif joining_type in [ord("R"), ord("D")]:
                ok = True
                break
            else:
                break
        return ok

    if cp_value == 0x200D:
        if pos > 0:
            if _combining_class(ord(label[pos - 1])) == _virama_combining_class:
                return True
        return False

    else:
        return False


def valid_contexto(label: str, pos: int, exception: bool = False) -> bool:
    cp_value = ord(label[pos])

    if cp_value == 0x00B7:
        if 0 < pos < len(label) - 1:
            if ord(label[pos - 1]) == 0x006C and ord(label[pos + 1]) == 0x006C:
                return True
        return False

    elif cp_value == 0x0375:
        if pos < len(label) - 1 and len(label) > 1:
            return _is_script(label[pos + 1], "Greek")
        return False

    elif cp_value == 0x05F3 or cp_value == 0x05F4:
        if pos > 0:
            return _is_script(label[pos - 1], "Hebrew")
        return False

    elif cp_value == 0x30FB:
        for cp in label:
            if cp == "\u30fb":
                continue
            if _is_script(cp, "Hiragana") or _is_script(cp, "Katakana") or _is_script(cp, "Han"):
                return True
        return False

    elif 0x660 <= cp_value <= 0x669:
        for cp in label:
            if 0x6F0 <= ord(cp) <= 0x06F9:
                return False
        return True

    elif 0x6F0 <= cp_value <= 0x6F9:
        for cp in label:
            if 0x660 <= ord(cp) <= 0x0669:
                return False
        return True

    return False


def check_label(label: Union[str, bytes, bytearray]) -> None:
    if isinstance(label, (bytes, bytearray)):
        label = label.decode("utf-8")
    if len(label) == 0:
        raise IDNAError("Empty Label")

    check_nfc(label)
    check_hyphen_ok(label)
    check_initial_combiner(label)

    for pos, cp in enumerate(label):
        cp_value = ord(cp)
        if intranges_contain(cp_value, idnadata.codepoint_classes["PVALID"]):
            continue
        elif intranges_contain(cp_value, idnadata.codepoint_classes["CONTEXTJ"]):
            try:
                if not valid_contextj(label, pos):
                    raise InvalidCodepointContext(
                        "Joiner {} not allowed at position {} in {}".format(_unot(cp_value), pos + 1, repr(label))
                    )
            except ValueError:
                raise IDNAError(
                    "Unknown codepoint adjacent to joiner {} at position {} in {}".format(
                        _unot(cp_value), pos + 1, repr(label)
                    )
                )
        elif intranges_contain(cp_value, idnadata.codepoint_classes["CONTEXTO"]):
            if not valid_contexto(label, pos):
                raise InvalidCodepointContext(
                    "Codepoint {} not allowed at position {} in {}".format(_unot(cp_value), pos + 1, repr(label))
                )
        else:
            raise InvalidCodepoint(
                "Codepoint {} at position {} of {} not allowed".format(_unot(cp_value), pos + 1, repr(label))
            )

    check_bidi(label)


def alabel(label: str) -> bytes:
    try:
        label_bytes = label.encode("ascii")
        ulabel(label_bytes)
        if not valid_label_length(label_bytes):
            raise IDNAError("Label too long")
        return label_bytes
    except UnicodeEncodeError:
        pass

    check_label(label)
    label_bytes = _alabel_prefix + _punycode(label)

    if not valid_label_length(label_bytes):
        raise IDNAError("Label too long")

    return label_bytes


def ulabel(label: Union[str, bytes, bytearray]) -> str:
    if not isinstance(label, (bytes, bytearray)):
        try:
            label_bytes = label.encode("ascii")
        except UnicodeEncodeError:
            check_label(label)
            return label
    else:
        label_bytes = label

    label_bytes = label_bytes.lower()
    if label_bytes.startswith(_alabel_prefix):
        label_bytes = label_bytes[len(_alabel_prefix) :]
        if not label_bytes:
            raise IDNAError("Malformed A-label, no Punycode eligible content found")
        if label_bytes.decode("ascii")[-1] == "-":
            raise IDNAError("A-label must not end with a hyphen")
    else:
        check_label(label_bytes)
        return label_bytes.decode("ascii")

    try:
        label = label_bytes.decode("punycode")
    except UnicodeError:
        raise IDNAError("Invalid A-label")
    check_label(label)
    return label


def uts46_remap(domain: str, std3_rules: bool = True, transitional: bool = False) -> str:
    """Re-map the characters in the string according to UTS46 processing."""
    from .uts46data import uts46data

    output = ""

    for pos, char in enumerate(domain):
        code_point = ord(char)
        try:
            uts46row = uts46data[code_point if code_point < 256 else bisect.bisect_left(uts46data, (code_point, "Z")) - 1]
            status = uts46row[1]
            replacement: Optional[str] = None
            if len(uts46row) == 3:
                replacement = uts46row[2]
            if (
                status == "V"
                or (status == "D" and not transitional)
                or (status == "3" and not std3_rules and replacement is None)
            ):
                output += char
            elif replacement is not None and (
                status == "M" or (status == "3" and not std3_rules) or (status == "D" and transitional)
            ):
                output += replacement
            elif status != "I":
                raise IndexError()
        except IndexError:
            raise InvalidCodepoint(
                "Codepoint {} not allowed at position {} in {}".format(_unot(code_point), pos + 1, repr(domain))
            )

    return unicodedata.normalize("NFC", output)


def encode(
    s: Union[str, bytes, bytearray],
    strict: bool = False,
    uts46: bool = False,
    std3_rules: bool = False,
    transitional: bool = False,
) -> bytes:
    if not isinstance(s, str):
        try:
            s = str(s, "ascii")
        except UnicodeDecodeError:
            raise IDNAError("should pass a unicode string to the function rather than a byte string.")
    if uts46:
        s = uts46_remap(s, std3_rules, transitional)
    trailing_dot = False
    result = []
    if strict:
        labels = s.split(".")
    else:
        labels = _unicode_dots_re.split(s)
    if not labels or labels == [""]:
        raise IDNAError("Empty domain")
    if labels[-1] == "":
        del labels[-1]
        trailing_dot = True
    for label in labels:
        s = alabel(label)
        if s:
            result.append(s)
        else:
            raise IDNAError("Empty label")
    if trailing_dot:
        result.append(b"")
    s = b".".join(result)
    if not valid_string_length(s, trailing_dot):
        raise IDNAError("Domain too long")
    return s


def decode(
    s: Union[str, bytes, bytearray],
    strict: bool = False,
    uts46: bool = False,
    std3_rules: bool = False,
) -> str:
    try:
        if not isinstance(s, str):
            s = str(s, "ascii")
    except UnicodeDecodeError:
        raise IDNAError("Invalid ASCII in A-label")
    if uts46:
        s = uts46_remap(s, std3_rules, False)
    trailing_dot = False
    result = []
    if not strict:
        labels = _unicode_dots_re.split(s)
    else:
        labels = s.split(".")
    if not labels or labels == [""]:
        raise IDNAError("Empty domain")
    if not labels[-1]:
        del labels[-1]
        trailing_dot = True
    for label in labels:
        s = ulabel(label)
        if s:
            result.append(s)
        else:
            raise IDNAError("Empty label")
    if trailing_dot:
        result.append("")
    return ".".join(result)

# === NexusCore/openenv\Lib\site-packages\jinja2\sandbox.py ===
"""A sandbox layer that ensures unsafe operations cannot be performed.
Useful when the template itself comes from an untrusted source.
"""

import operator
import types
import typing as t
from _string import formatter_field_name_split  # type: ignore
from collections import abc
from collections import deque
from functools import update_wrapper
from string import Formatter

from markupsafe import EscapeFormatter
from markupsafe import Markup

from .environment import Environment
from .exceptions import SecurityError
from .runtime import Context
from .runtime import Undefined

F = t.TypeVar("F", bound=t.Callable[..., t.Any])

#: maximum number of items a range may produce
MAX_RANGE = 100000

#: Unsafe function attributes.
UNSAFE_FUNCTION_ATTRIBUTES: t.Set[str] = set()

#: Unsafe method attributes. Function attributes are unsafe for methods too.
UNSAFE_METHOD_ATTRIBUTES: t.Set[str] = set()

#: unsafe generator attributes.
UNSAFE_GENERATOR_ATTRIBUTES = {"gi_frame", "gi_code"}

#: unsafe attributes on coroutines
UNSAFE_COROUTINE_ATTRIBUTES = {"cr_frame", "cr_code"}

#: unsafe attributes on async generators
UNSAFE_ASYNC_GENERATOR_ATTRIBUTES = {"ag_code", "ag_frame"}

_mutable_spec: t.Tuple[t.Tuple[t.Type[t.Any], t.FrozenSet[str]], ...] = (
    (
        abc.MutableSet,
        frozenset(
            [
                "add",
                "clear",
                "difference_update",
                "discard",
                "pop",
                "remove",
                "symmetric_difference_update",
                "update",
            ]
        ),
    ),
    (
        abc.MutableMapping,
        frozenset(["clear", "pop", "popitem", "setdefault", "update"]),
    ),
    (
        abc.MutableSequence,
        frozenset(
            ["append", "clear", "pop", "reverse", "insert", "sort", "extend", "remove"]
        ),
    ),
    (
        deque,
        frozenset(
            [
                "append",
                "appendleft",
                "clear",
                "extend",
                "extendleft",
                "pop",
                "popleft",
                "remove",
                "rotate",
            ]
        ),
    ),
)


def safe_range(*args: int) -> range:
    """A range that can't generate ranges with a length of more than
    MAX_RANGE items.
    """
    rng = range(*args)

    if len(rng) > MAX_RANGE:
        raise OverflowError(
            "Range too big. The sandbox blocks ranges larger than"
            f" MAX_RANGE ({MAX_RANGE})."
        )

    return rng


def unsafe(f: F) -> F:
    """Marks a function or method as unsafe.

    .. code-block: python

        @unsafe
        def delete(self):
            pass
    """
    f.unsafe_callable = True  # type: ignore
    return f


def is_internal_attribute(obj: t.Any, attr: str) -> bool:
    """Test if the attribute given is an internal python attribute.  For
    example this function returns `True` for the `func_code` attribute of
    python objects.  This is useful if the environment method
    :meth:`~SandboxedEnvironment.is_safe_attribute` is overridden.

    >>> from jinja2.sandbox import is_internal_attribute
    >>> is_internal_attribute(str, "mro")
    True
    >>> is_internal_attribute(str, "upper")
    False
    """
    if isinstance(obj, types.FunctionType):
        if attr in UNSAFE_FUNCTION_ATTRIBUTES:
            return True
    elif isinstance(obj, types.MethodType):
        if attr in UNSAFE_FUNCTION_ATTRIBUTES or attr in UNSAFE_METHOD_ATTRIBUTES:
            return True
    elif isinstance(obj, type):
        if attr == "mro":
            return True
    elif isinstance(obj, (types.CodeType, types.TracebackType, types.FrameType)):
        return True
    elif isinstance(obj, types.GeneratorType):
        if attr in UNSAFE_GENERATOR_ATTRIBUTES:
            return True
    elif hasattr(types, "CoroutineType") and isinstance(obj, types.CoroutineType):
        if attr in UNSAFE_COROUTINE_ATTRIBUTES:
            return True
    elif hasattr(types, "AsyncGeneratorType") and isinstance(
        obj, types.AsyncGeneratorType
    ):
        if attr in UNSAFE_ASYNC_GENERATOR_ATTRIBUTES:
            return True
    return attr.startswith("__")


def modifies_known_mutable(obj: t.Any, attr: str) -> bool:
    """This function checks if an attribute on a builtin mutable object
    (list, dict, set or deque) or the corresponding ABCs would modify it
    if called.

    >>> modifies_known_mutable({}, "clear")
    True
    >>> modifies_known_mutable({}, "keys")
    False
    >>> modifies_known_mutable([], "append")
    True
    >>> modifies_known_mutable([], "index")
    False

    If called with an unsupported object, ``False`` is returned.

    >>> modifies_known_mutable("foo", "upper")
    False
    """
    for typespec, unsafe in _mutable_spec:
        if isinstance(obj, typespec):
            return attr in unsafe
    return False


class SandboxedEnvironment(Environment):
    """The sandboxed environment.  It works like the regular environment but
    tells the compiler to generate sandboxed code.  Additionally subclasses of
    this environment may override the methods that tell the runtime what
    attributes or functions are safe to access.

    If the template tries to access insecure code a :exc:`SecurityError` is
    raised.  However also other exceptions may occur during the rendering so
    the caller has to ensure that all exceptions are caught.
    """

    sandboxed = True

    #: default callback table for the binary operators.  A copy of this is
    #: available on each instance of a sandboxed environment as
    #: :attr:`binop_table`
    default_binop_table: t.Dict[str, t.Callable[[t.Any, t.Any], t.Any]] = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
        "//": operator.floordiv,
        "**": operator.pow,
        "%": operator.mod,
    }

    #: default callback table for the unary operators.  A copy of this is
    #: available on each instance of a sandboxed environment as
    #: :attr:`unop_table`
    default_unop_table: t.Dict[str, t.Callable[[t.Any], t.Any]] = {
        "+": operator.pos,
        "-": operator.neg,
    }

    #: a set of binary operators that should be intercepted.  Each operator
    #: that is added to this set (empty by default) is delegated to the
    #: :meth:`call_binop` method that will perform the operator.  The default
    #: operator callback is specified by :attr:`binop_table`.
    #:
    #: The following binary operators are interceptable:
    #: ``//``, ``%``, ``+``, ``*``, ``-``, ``/``, and ``**``
    #:
    #: The default operation form the operator table corresponds to the
    #: builtin function.  Intercepted calls are always slower than the native
    #: operator call, so make sure only to intercept the ones you are
    #: interested in.
    #:
    #: .. versionadded:: 2.6
    intercepted_binops: t.FrozenSet[str] = frozenset()

    #: a set of unary operators that should be intercepted.  Each operator
    #: that is added to this set (empty by default) is delegated to the
    #: :meth:`call_unop` method that will perform the operator.  The default
    #: operator callback is specified by :attr:`unop_table`.
    #:
    #: The following unary operators are interceptable: ``+``, ``-``
    #:
    #: The default operation form the operator table corresponds to the
    #: builtin function.  Intercepted calls are always slower than the native
    #: operator call, so make sure only to intercept the ones you are
    #: interested in.
    #:
    #: .. versionadded:: 2.6
    intercepted_unops: t.FrozenSet[str] = frozenset()

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self.globals["range"] = safe_range
        self.binop_table = self.default_binop_table.copy()
        self.unop_table = self.default_unop_table.copy()

    def is_safe_attribute(self, obj: t.Any, attr: str, value: t.Any) -> bool:
        """The sandboxed environment will call this method to check if the
        attribute of an object is safe to access.  Per default all attributes
        starting with an underscore are considered private as well as the
        special attributes of internal python objects as returned by the
        :func:`is_internal_attribute` function.
        """
        return not (attr.startswith("_") or is_internal_attribute(obj, attr))

    def is_safe_callable(self, obj: t.Any) -> bool:
        """Check if an object is safely callable. By default callables
        are considered safe unless decorated with :func:`unsafe`.

        This also recognizes the Django convention of setting
        ``func.alters_data = True``.
        """
        return not (
            getattr(obj, "unsafe_callable", False) or getattr(obj, "alters_data", False)
        )

    def call_binop(
        self, context: Context, operator: str, left: t.Any, right: t.Any
    ) -> t.Any:
        """For intercepted binary operator calls (:meth:`intercepted_binops`)
        this function is executed instead of the builtin operator.  This can
        be used to fine tune the behavior of certain operators.

        .. versionadded:: 2.6
        """
        return self.binop_table[operator](left, right)

    def call_unop(self, context: Context, operator: str, arg: t.Any) -> t.Any:
        """For intercepted unary operator calls (:meth:`intercepted_unops`)
        this function is executed instead of the builtin operator.  This can
        be used to fine tune the behavior of certain operators.

        .. versionadded:: 2.6
        """
        return self.unop_table[operator](arg)

    def getitem(
        self, obj: t.Any, argument: t.Union[str, t.Any]
    ) -> t.Union[t.Any, Undefined]:
        """Subscribe an object from sandboxed code."""
        try:
            return obj[argument]
        except (TypeError, LookupError):
            if isinstance(argument, str):
                try:
                    attr = str(argument)
                except Exception:
                    pass
                else:
                    try:
                        value = getattr(obj, attr)
                    except AttributeError:
                        pass
                    else:
                        fmt = self.wrap_str_format(value)
                        if fmt is not None:
                            return fmt
                        if self.is_safe_attribute(obj, argument, value):
                            return value
                        return self.unsafe_undefined(obj, argument)
        return self.undefined(obj=obj, name=argument)

    def getattr(self, obj: t.Any, attribute: str) -> t.Union[t.Any, Undefined]:
        """Subscribe an object from sandboxed code and prefer the
        attribute.  The attribute passed *must* be a bytestring.
        """
        try:
            value = getattr(obj, attribute)
        except AttributeError:
            try:
                return obj[attribute]
            except (TypeError, LookupError):
                pass
        else:
            fmt = self.wrap_str_format(value)
            if fmt is not None:
                return fmt
            if self.is_safe_attribute(obj, attribute, value):
                return value
            return self.unsafe_undefined(obj, attribute)
        return self.undefined(obj=obj, name=attribute)

    def unsafe_undefined(self, obj: t.Any, attribute: str) -> Undefined:
        """Return an undefined object for unsafe attributes."""
        return self.undefined(
            f"access to attribute {attribute!r} of"
            f" {type(obj).__name__!r} object is unsafe.",
            name=attribute,
            obj=obj,
            exc=SecurityError,
        )

    def wrap_str_format(self, value: t.Any) -> t.Optional[t.Callable[..., str]]:
        """If the given value is a ``str.format`` or ``str.format_map`` method,
        return a new function than handles sandboxing. This is done at access
        rather than in :meth:`call`, so that calls made without ``call`` are
        also sandboxed.
        """
        if not isinstance(
            value, (types.MethodType, types.BuiltinMethodType)
        ) or value.__name__ not in ("format", "format_map"):
            return None

        f_self: t.Any = value.__self__

        if not isinstance(f_self, str):
            return None

        str_type: t.Type[str] = type(f_self)
        is_format_map = value.__name__ == "format_map"
        formatter: SandboxedFormatter

        if isinstance(f_self, Markup):
            formatter = SandboxedEscapeFormatter(self, escape=f_self.escape)
        else:
            formatter = SandboxedFormatter(self)

        vformat = formatter.vformat

        def wrapper(*args: t.Any, **kwargs: t.Any) -> str:
            if is_format_map:
                if kwargs:
                    raise TypeError("format_map() takes no keyword arguments")

                if len(args) != 1:
                    raise TypeError(
                        f"format_map() takes exactly one argument ({len(args)} given)"
                    )

                kwargs = args[0]
                args = ()

            return str_type(vformat(f_self, args, kwargs))

        return update_wrapper(wrapper, value)

    def call(
        __self,  # noqa: B902
        __context: Context,
        __obj: t.Any,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> t.Any:
        """Call an object from sandboxed code."""

        # the double prefixes are to avoid double keyword argument
        # errors when proxying the call.
        if not __self.is_safe_callable(__obj):
            raise SecurityError(f"{__obj!r} is not safely callable")
        return __context.call(__obj, *args, **kwargs)


class ImmutableSandboxedEnvironment(SandboxedEnvironment):
    """Works exactly like the regular `SandboxedEnvironment` but does not
    permit modifications on the builtin mutable objects `list`, `set`, and
    `dict` by using the :func:`modifies_known_mutable` function.
    """

    def is_safe_attribute(self, obj: t.Any, attr: str, value: t.Any) -> bool:
        if not super().is_safe_attribute(obj, attr, value):
            return False

        return not modifies_known_mutable(obj, attr)


class SandboxedFormatter(Formatter):
    def __init__(self, env: Environment, **kwargs: t.Any) -> None:
        self._env = env
        super().__init__(**kwargs)

    def get_field(
        self, field_name: str, args: t.Sequence[t.Any], kwargs: t.Mapping[str, t.Any]
    ) -> t.Tuple[t.Any, str]:
        first, rest = formatter_field_name_split(field_name)
        obj = self.get_value(first, args, kwargs)
        for is_attr, i in rest:
            if is_attr:
                obj = self._env.getattr(obj, i)
            else:
                obj = self._env.getitem(obj, i)
        return obj, first


class SandboxedEscapeFormatter(SandboxedFormatter, EscapeFormatter):
    pass

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\scaleUpem.py ===
"""Change the units-per-EM of a font.

AAT and Graphite tables are not supported. CFF/CFF2 fonts
are de-subroutinized."""

from fontTools.ttLib.ttVisitor import TTVisitor
import fontTools.ttLib as ttLib
import fontTools.ttLib.tables.otBase as otBase
import fontTools.ttLib.tables.otTables as otTables
from fontTools.cffLib import VarStoreData
import fontTools.cffLib.specializer as cffSpecializer
from fontTools.varLib import builder  # for VarData.calculateNumShorts
from fontTools.varLib.multiVarStore import OnlineMultiVarStoreBuilder
from fontTools.misc.vector import Vector
from fontTools.misc.fixedTools import otRound
from fontTools.misc.iterTools import batched


__all__ = ["scale_upem", "ScalerVisitor"]


class ScalerVisitor(TTVisitor):
    def __init__(self, scaleFactor):
        self.scaleFactor = scaleFactor

    def scale(self, v):
        return otRound(v * self.scaleFactor)


@ScalerVisitor.register_attrs(
    (
        (ttLib.getTableClass("head"), ("unitsPerEm", "xMin", "yMin", "xMax", "yMax")),
        (ttLib.getTableClass("post"), ("underlinePosition", "underlineThickness")),
        (ttLib.getTableClass("VORG"), ("defaultVertOriginY")),
        (
            ttLib.getTableClass("hhea"),
            (
                "ascent",
                "descent",
                "lineGap",
                "advanceWidthMax",
                "minLeftSideBearing",
                "minRightSideBearing",
                "xMaxExtent",
                "caretOffset",
            ),
        ),
        (
            ttLib.getTableClass("vhea"),
            (
                "ascent",
                "descent",
                "lineGap",
                "advanceHeightMax",
                "minTopSideBearing",
                "minBottomSideBearing",
                "yMaxExtent",
                "caretOffset",
            ),
        ),
        (
            ttLib.getTableClass("OS/2"),
            (
                "xAvgCharWidth",
                "ySubscriptXSize",
                "ySubscriptYSize",
                "ySubscriptXOffset",
                "ySubscriptYOffset",
                "ySuperscriptXSize",
                "ySuperscriptYSize",
                "ySuperscriptXOffset",
                "ySuperscriptYOffset",
                "yStrikeoutSize",
                "yStrikeoutPosition",
                "sTypoAscender",
                "sTypoDescender",
                "sTypoLineGap",
                "usWinAscent",
                "usWinDescent",
                "sxHeight",
                "sCapHeight",
            ),
        ),
        (
            otTables.ValueRecord,
            ("XAdvance", "YAdvance", "XPlacement", "YPlacement"),
        ),  # GPOS
        (otTables.Anchor, ("XCoordinate", "YCoordinate")),  # GPOS
        (otTables.CaretValue, ("Coordinate")),  # GDEF
        (otTables.BaseCoord, ("Coordinate")),  # BASE
        (otTables.MathValueRecord, ("Value")),  # MATH
        (otTables.ClipBox, ("xMin", "yMin", "xMax", "yMax")),  # COLR
    )
)
def visit(visitor, obj, attr, value):
    setattr(obj, attr, visitor.scale(value))


@ScalerVisitor.register_attr(
    (ttLib.getTableClass("hmtx"), ttLib.getTableClass("vmtx")), "metrics"
)
def visit(visitor, obj, attr, metrics):
    for g in metrics:
        advance, lsb = metrics[g]
        metrics[g] = visitor.scale(advance), visitor.scale(lsb)


@ScalerVisitor.register_attr(ttLib.getTableClass("VMTX"), "VOriginRecords")
def visit(visitor, obj, attr, VOriginRecords):
    for g in VOriginRecords:
        VOriginRecords[g] = visitor.scale(VOriginRecords[g])


@ScalerVisitor.register_attr(ttLib.getTableClass("glyf"), "glyphs")
def visit(visitor, obj, attr, glyphs):
    for g in glyphs.values():
        for attr in ("xMin", "xMax", "yMin", "yMax"):
            v = getattr(g, attr, None)
            if v is not None:
                setattr(g, attr, visitor.scale(v))

        if g.isComposite():
            for component in g.components:
                component.x = visitor.scale(component.x)
                component.y = visitor.scale(component.y)
            continue

        if hasattr(g, "coordinates"):
            coordinates = g.coordinates
            for i, (x, y) in enumerate(coordinates):
                coordinates[i] = visitor.scale(x), visitor.scale(y)


@ScalerVisitor.register_attr(ttLib.getTableClass("gvar"), "variations")
def visit(visitor, obj, attr, variations):
    glyfTable = visitor.font["glyf"]

    for glyphName, varlist in variations.items():
        glyph = glyfTable[glyphName]
        for var in varlist:
            coordinates = var.coordinates
            for i, xy in enumerate(coordinates):
                if xy is None:
                    continue
                coordinates[i] = visitor.scale(xy[0]), visitor.scale(xy[1])


@ScalerVisitor.register_attr(ttLib.getTableClass("VARC"), "table")
def visit(visitor, obj, attr, varc):
    # VarComposite variations are a pain

    fvar = visitor.font["fvar"]
    fvarAxes = [a.axisTag for a in fvar.axes]

    store = varc.MultiVarStore
    storeBuilder = OnlineMultiVarStoreBuilder(fvarAxes)

    for g in varc.VarCompositeGlyphs.VarCompositeGlyph:
        for component in g.components:
            t = component.transform
            t.translateX = visitor.scale(t.translateX)
            t.translateY = visitor.scale(t.translateY)
            t.tCenterX = visitor.scale(t.tCenterX)
            t.tCenterY = visitor.scale(t.tCenterY)

            if component.axisValuesVarIndex != otTables.NO_VARIATION_INDEX:
                varIdx = component.axisValuesVarIndex
                # TODO Move this code duplicated below to MultiVarStore.__getitem__,
                # or a getDeltasAndSupports().
                if varIdx != otTables.NO_VARIATION_INDEX:
                    major = varIdx >> 16
                    minor = varIdx & 0xFFFF
                    varData = store.MultiVarData[major]
                    vec = varData.Item[minor]
                    storeBuilder.setSupports(store.get_supports(major, fvar.axes))
                    if vec:
                        m = len(vec) // varData.VarRegionCount
                        vec = list(batched(vec, m))
                        vec = [Vector(v) for v in vec]
                        component.axisValuesVarIndex = storeBuilder.storeDeltas(vec)
                    else:
                        component.axisValuesVarIndex = otTables.NO_VARIATION_INDEX

            if component.transformVarIndex != otTables.NO_VARIATION_INDEX:
                varIdx = component.transformVarIndex
                if varIdx != otTables.NO_VARIATION_INDEX:
                    major = varIdx >> 16
                    minor = varIdx & 0xFFFF
                    vec = varData.Item[varIdx & 0xFFFF]
                    major = varIdx >> 16
                    minor = varIdx & 0xFFFF
                    varData = store.MultiVarData[major]
                    vec = varData.Item[minor]
                    storeBuilder.setSupports(store.get_supports(major, fvar.axes))
                    if vec:
                        m = len(vec) // varData.VarRegionCount
                        flags = component.flags
                        vec = list(batched(vec, m))
                        newVec = []
                        for v in vec:
                            v = list(v)
                            i = 0
                            ## Scale translate & tCenter
                            if flags & otTables.VarComponentFlags.HAVE_TRANSLATE_X:
                                v[i] = visitor.scale(v[i])
                                i += 1
                            if flags & otTables.VarComponentFlags.HAVE_TRANSLATE_Y:
                                v[i] = visitor.scale(v[i])
                                i += 1
                            if flags & otTables.VarComponentFlags.HAVE_ROTATION:
                                i += 1
                            if flags & otTables.VarComponentFlags.HAVE_SCALE_X:
                                i += 1
                            if flags & otTables.VarComponentFlags.HAVE_SCALE_Y:
                                i += 1
                            if flags & otTables.VarComponentFlags.HAVE_SKEW_X:
                                i += 1
                            if flags & otTables.VarComponentFlags.HAVE_SKEW_Y:
                                i += 1
                            if flags & otTables.VarComponentFlags.HAVE_TCENTER_X:
                                v[i] = visitor.scale(v[i])
                                i += 1
                            if flags & otTables.VarComponentFlags.HAVE_TCENTER_Y:
                                v[i] = visitor.scale(v[i])
                                i += 1

                            newVec.append(Vector(v))
                        vec = newVec

                        component.transformVarIndex = storeBuilder.storeDeltas(vec)
                    else:
                        component.transformVarIndex = otTables.NO_VARIATION_INDEX

    varc.MultiVarStore = storeBuilder.finish()


@ScalerVisitor.register_attr(ttLib.getTableClass("kern"), "kernTables")
def visit(visitor, obj, attr, kernTables):
    for table in kernTables:
        kernTable = table.kernTable
        for k in kernTable.keys():
            kernTable[k] = visitor.scale(kernTable[k])


def _cff_scale(visitor, args):
    for i, arg in enumerate(args):
        if not isinstance(arg, list):
            if not isinstance(arg, bytes):
                args[i] = visitor.scale(arg)
        else:
            num_blends = arg[-1]
            _cff_scale(visitor, arg)
            arg[-1] = num_blends


@ScalerVisitor.register_attr(
    (ttLib.getTableClass("CFF "), ttLib.getTableClass("CFF2")), "cff"
)
def visit(visitor, obj, attr, cff):
    cff.desubroutinize()
    topDict = cff.topDictIndex[0]
    varStore = getattr(topDict, "VarStore", None)
    getNumRegions = varStore.getNumRegions if varStore is not None else None
    privates = set()
    for fontname in cff.keys():
        font = cff[fontname]
        cs = font.CharStrings
        for g in font.charset:
            c, _ = cs.getItemAndSelector(g)
            privates.add(c.private)

            commands = cffSpecializer.programToCommands(
                c.program, getNumRegions=getNumRegions
            )
            for op, args in commands:
                if op == "vsindex":
                    continue
                _cff_scale(visitor, args)
            c.program[:] = cffSpecializer.commandsToProgram(commands)

        # Annoying business of scaling numbers that do not matter whatsoever

        for attr in (
            "UnderlinePosition",
            "UnderlineThickness",
            "FontBBox",
            "StrokeWidth",
        ):
            value = getattr(topDict, attr, None)
            if value is None:
                continue
            if isinstance(value, list):
                _cff_scale(visitor, value)
            else:
                setattr(topDict, attr, visitor.scale(value))

        for i in range(6):
            topDict.FontMatrix[i] /= visitor.scaleFactor

        for private in privates:
            for attr in (
                "BlueValues",
                "OtherBlues",
                "FamilyBlues",
                "FamilyOtherBlues",
                # "BlueScale",
                # "BlueShift",
                # "BlueFuzz",
                "StdHW",
                "StdVW",
                "StemSnapH",
                "StemSnapV",
                "defaultWidthX",
                "nominalWidthX",
            ):
                value = getattr(private, attr, None)
                if value is None:
                    continue
                if isinstance(value, list):
                    _cff_scale(visitor, value)
                else:
                    setattr(private, attr, visitor.scale(value))


# ItemVariationStore


@ScalerVisitor.register(otTables.VarData)
def visit(visitor, varData):
    for item in varData.Item:
        for i, v in enumerate(item):
            item[i] = visitor.scale(v)
    varData.calculateNumShorts()


# COLRv1


def _setup_scale_paint(paint, scale):
    if -2 <= scale <= 2 - (1 >> 14):
        paint.Format = otTables.PaintFormat.PaintScaleUniform
        paint.scale = scale
        return

    transform = otTables.Affine2x3()
    transform.populateDefaults()
    transform.xy = transform.yx = transform.dx = transform.dy = 0
    transform.xx = transform.yy = scale

    paint.Format = otTables.PaintFormat.PaintTransform
    paint.Transform = transform


@ScalerVisitor.register(otTables.BaseGlyphPaintRecord)
def visit(visitor, record):
    oldPaint = record.Paint

    scale = otTables.Paint()
    _setup_scale_paint(scale, visitor.scaleFactor)
    scale.Paint = oldPaint

    record.Paint = scale

    return True


@ScalerVisitor.register(otTables.Paint)
def visit(visitor, paint):
    if paint.Format != otTables.PaintFormat.PaintGlyph:
        return True

    newPaint = otTables.Paint()
    newPaint.Format = paint.Format
    newPaint.Paint = paint.Paint
    newPaint.Glyph = paint.Glyph
    del paint.Paint
    del paint.Glyph

    _setup_scale_paint(paint, 1 / visitor.scaleFactor)
    paint.Paint = newPaint

    visitor.visit(newPaint.Paint)

    return False


def scale_upem(font, new_upem):
    """Change the units-per-EM of font to the new value."""
    upem = font["head"].unitsPerEm
    visitor = ScalerVisitor(new_upem / upem)
    visitor.visit(font)


def main(args=None):
    """Change the units-per-EM of fonts"""

    if args is None:
        import sys

        args = sys.argv[1:]

    from fontTools.ttLib import TTFont
    from fontTools.misc.cliTools import makeOutputFileName
    import argparse

    parser = argparse.ArgumentParser(
        "fonttools ttLib.scaleUpem", description="Change the units-per-EM of fonts"
    )
    parser.add_argument("font", metavar="font", help="Font file.")
    parser.add_argument(
        "new_upem", metavar="new-upem", help="New units-per-EM integer value."
    )
    parser.add_argument(
        "--output-file", metavar="path", default=None, help="Output file."
    )

    options = parser.parse_args(args)

    font = TTFont(options.font)
    new_upem = int(options.new_upem)
    output_file = (
        options.output_file
        if options.output_file is not None
        else makeOutputFileName(options.font, overWrite=True, suffix="-scaled")
    )

    scale_upem(font, new_upem)

    print("Writing %s" % output_file)
    font.save(output_file)


if __name__ == "__main__":
    import sys

    sys.exit(main())

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\embed.py ===
# encoding: utf-8
"""
An embedded IPython shell.
"""
# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.


import sys
import warnings

from IPython.core import ultratb, compilerop
from IPython.core import magic_arguments
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.core.interactiveshell import InteractiveShell, make_main_module_type
from IPython.terminal.interactiveshell import TerminalInteractiveShell
from IPython.terminal.ipapp import load_default_config

from traitlets import Bool, CBool, Unicode
from IPython.utils.io import ask_yes_no

from typing import Set

class KillEmbedded(Exception):pass

# kept for backward compatibility as IPython 6 was released with
# the typo. See https://github.com/ipython/ipython/pull/10706
KillEmbeded = KillEmbedded

# This is an additional magic that is exposed in embedded shells.
@magics_class
class EmbeddedMagics(Magics):

    @line_magic
    @magic_arguments.magic_arguments()
    @magic_arguments.argument('-i', '--instance', action='store_true',
                              help='Kill instance instead of call location')
    @magic_arguments.argument('-x', '--exit', action='store_true',
                              help='Also exit the current session')
    @magic_arguments.argument('-y', '--yes', action='store_true',
                              help='Do not ask confirmation')
    def kill_embedded(self, parameter_s=''):
        """%kill_embedded : deactivate for good the current embedded IPython

        This function (after asking for confirmation) sets an internal flag so
        that an embedded IPython will never activate again for the given call
        location. This is useful to permanently disable a shell that is being
        called inside a loop: once you've figured out what you needed from it,
        you may then kill it and the program will then continue to run without
        the interactive shell interfering again.

        Kill Instance Option:

            If for some reasons you need to kill the location where the instance
            is created and not called, for example if you create a single
            instance in one place and debug in many locations, you can use the
            ``--instance`` option to kill this specific instance. Like for the
            ``call location`` killing an "instance" should work even if it is
            recreated within a loop.

        .. note::

            This was the default behavior before IPython 5.2

        """

        args = magic_arguments.parse_argstring(self.kill_embedded, parameter_s)
        print(args)
        if args.instance:
            # let no ask
            if not args.yes:
                kill = ask_yes_no(
                    "Are you sure you want to kill this embedded instance? [y/N] ", 'n')
            else:
                kill = True
            if kill:
                self.shell._disable_init_location()
                print("This embedded IPython instance will not reactivate anymore "
                      "once you exit.")
        else:
            if not args.yes:
                kill = ask_yes_no(
                    "Are you sure you want to kill this embedded call_location? [y/N] ", 'n')
            else:
                kill = True
            if kill:
                self.shell.embedded_active = False
                print("This embedded IPython  call location will not reactivate anymore "
                      "once you exit.")

        if args.exit:
            # Ask-exit does not really ask, it just set internals flags to exit
            # on next loop.
            self.shell.ask_exit()


    @line_magic
    def exit_raise(self, parameter_s=''):
        """%exit_raise Make the current embedded kernel exit and raise and exception.

        This function sets an internal flag so that an embedded IPython will
        raise a `IPython.terminal.embed.KillEmbedded` Exception on exit, and then exit the current I. This is
        useful to permanently exit a loop that create IPython embed instance.
        """

        self.shell.should_raise = True
        self.shell.ask_exit()


class _Sentinel:
    def __init__(self, repr):
        assert isinstance(repr, str)
        self.repr = repr

    def __repr__(self):
        return repr


class InteractiveShellEmbed(TerminalInteractiveShell):

    dummy_mode = Bool(False)
    exit_msg = Unicode('')
    embedded = CBool(True)
    should_raise = CBool(False)
    # Like the base class display_banner is not configurable, but here it
    # is True by default.
    display_banner = CBool(True)
    exit_msg = Unicode()

    # When embedding, by default we don't change the terminal title
    term_title = Bool(False,
        help="Automatically set the terminal title"
    ).tag(config=True)

    _inactive_locations: Set[str] = set()

    def _disable_init_location(self):
        """Disable the current Instance creation location"""
        InteractiveShellEmbed._inactive_locations.add(self._init_location_id)

    @property
    def embedded_active(self):
        return (self._call_location_id not in InteractiveShellEmbed._inactive_locations)\
            and (self._init_location_id not in InteractiveShellEmbed._inactive_locations)

    @embedded_active.setter
    def embedded_active(self, value):
        if value:
            InteractiveShellEmbed._inactive_locations.discard(
                self._call_location_id)
            InteractiveShellEmbed._inactive_locations.discard(
                self._init_location_id)
        else:
            InteractiveShellEmbed._inactive_locations.add(
                self._call_location_id)

    def __init__(self, **kw):
        assert (
            "user_global_ns" not in kw
        ), "Key word argument `user_global_ns` has been replaced by `user_module` since IPython 4.0."
        # temporary fix for https://github.com/ipython/ipython/issues/14164
        cls = type(self)
        if cls._instance is None:
            for subclass in cls._walk_mro():
                subclass._instance = self
            cls._instance = self

        clid = kw.pop('_init_location_id', None)
        if not clid:
            frame = sys._getframe(1)
            clid = '%s:%s' % (frame.f_code.co_filename, frame.f_lineno)
        self._init_location_id = clid

        super(InteractiveShellEmbed,self).__init__(**kw)

        # don't use the ipython crash handler so that user exceptions aren't
        # trapped
        sys.excepthook = ultratb.FormattedTB(
            theme_name=self.colors,
            mode=self.xmode,
            call_pdb=self.pdb,
        )

    def init_sys_modules(self):
        """
        Explicitly overwrite :mod:`IPython.core.interactiveshell` to do nothing.
        """
        pass

    def init_magics(self):
        super(InteractiveShellEmbed, self).init_magics()
        self.register_magics(EmbeddedMagics)

    def __call__(
        self,
        header="",
        local_ns=None,
        module=None,
        dummy=None,
        stack_depth=1,
        compile_flags=None,
        **kw,
    ):
        """Activate the interactive interpreter.

        __call__(self,header='',local_ns=None,module=None,dummy=None) -> Start
        the interpreter shell with the given local and global namespaces, and
        optionally print a header string at startup.

        The shell can be globally activated/deactivated using the
        dummy_mode attribute. This allows you to turn off a shell used
        for debugging globally.

        However, *each* time you call the shell you can override the current
        state of dummy_mode with the optional keyword parameter 'dummy'. For
        example, if you set dummy mode on with IPShell.dummy_mode = True, you
        can still have a specific call work by making it as IPShell(dummy=False).
        """

        # we are called, set the underlying interactiveshell not to exit.
        self.keep_running = True

        # If the user has turned it off, go away
        clid = kw.pop('_call_location_id', None)
        if not clid:
            frame = sys._getframe(1)
            clid = '%s:%s' % (frame.f_code.co_filename, frame.f_lineno)
        self._call_location_id = clid

        if not self.embedded_active:
            return

        # Normal exits from interactive mode set this flag, so the shell can't
        # re-enter (it checks this variable at the start of interactive mode).
        self.exit_now = False

        # Allow the dummy parameter to override the global __dummy_mode
        if dummy or (dummy != 0 and self.dummy_mode):
            return

        # self.banner is auto computed
        if header:
            self.old_banner2 = self.banner2
            self.banner2 = self.banner2 + '\n' + header + '\n'
        else:
            self.old_banner2 = ''

        if self.display_banner:
            self.show_banner()

        # Call the embedding code with a stack depth of 1 so it can skip over
        # our call and get the original caller's namespaces.
        self.mainloop(
            local_ns, module, stack_depth=stack_depth, compile_flags=compile_flags
        )

        self.banner2 = self.old_banner2

        if self.exit_msg is not None:
            print(self.exit_msg)

        if self.should_raise:
            raise KillEmbedded('Embedded IPython raising error, as user requested.')

    def mainloop(
        self,
        local_ns=None,
        module=None,
        stack_depth=0,
        compile_flags=None,
    ):
        """Embeds IPython into a running python program.

        Parameters
        ----------
        local_ns, module
            Working local namespace (a dict) and module (a module or similar
            object). If given as None, they are automatically taken from the scope
            where the shell was called, so that program variables become visible.
        stack_depth : int
            How many levels in the stack to go to looking for namespaces (when
            local_ns or module is None). This allows an intermediate caller to
            make sure that this function gets the namespace from the intended
            level in the stack. By default (0) it will get its locals and globals
            from the immediate caller.
        compile_flags
            A bit field identifying the __future__ features
            that are enabled, as passed to the builtin :func:`compile` function.
            If given as None, they are automatically taken from the scope where
            the shell was called.

        """
        
        # Get locals and globals from caller
        if ((local_ns is None or module is None or compile_flags is None)
            and self.default_user_namespaces):
            call_frame = sys._getframe(stack_depth).f_back

            if local_ns is None:
                local_ns = call_frame.f_locals
            if module is None:
                global_ns = call_frame.f_globals
                try:
                    module = sys.modules[global_ns['__name__']]
                except KeyError:
                    warnings.warn("Failed to get module %s" % \
                        global_ns.get('__name__', 'unknown module')
                    )
                    module = make_main_module_type(global_ns)()
            if compile_flags is None:
                compile_flags = (call_frame.f_code.co_flags &
                                 compilerop.PyCF_MASK)
        
        # Save original namespace and module so we can restore them after 
        # embedding; otherwise the shell doesn't shut down correctly.
        orig_user_module = self.user_module
        orig_user_ns = self.user_ns
        orig_compile_flags = self.compile.flags
        
        # Update namespaces and fire up interpreter
        
        # The global one is easy, we can just throw it in
        if module is not None:
            self.user_module = module

        # But the user/local one is tricky: ipython needs it to store internal
        # data, but we also need the locals. We'll throw our hidden variables
        # like _ih and get_ipython() into the local namespace, but delete them
        # later.
        if local_ns is not None:
            reentrant_local_ns = {k: v for (k, v) in local_ns.items() if k not in self.user_ns_hidden.keys()}
            self.user_ns = reentrant_local_ns
            self.init_user_ns()

        # Compiler flags
        if compile_flags is not None:
            self.compile.flags = compile_flags

        # make sure the tab-completer has the correct frame information, so it
        # actually completes using the frame's locals/globals
        self.set_completer_frame()

        with self.builtin_trap, self.display_trap:
            self.interact()
        
        # now, purge out the local namespace of IPython's hidden variables.
        if local_ns is not None:
            local_ns.update({k: v for (k, v) in self.user_ns.items() if k not in self.user_ns_hidden.keys()})

        
        # Restore original namespace so shell can shut down when we exit.
        self.user_module = orig_user_module
        self.user_ns = orig_user_ns
        self.compile.flags = orig_compile_flags


def embed(*, header="", compile_flags=None, **kwargs):
    """Call this to embed IPython at the current point in your program.

    The first invocation of this will create a :class:`terminal.embed.InteractiveShellEmbed`
    instance and then call it.  Consecutive calls just call the already
    created instance.

    If you don't want the kernel to initialize the namespace
    from the scope of the surrounding function,
    and/or you want to load full IPython configuration,
    you probably want `IPython.start_ipython()` instead.

    Here is a simple example::

        from IPython import embed
        a = 10
        b = 20
        embed(header='First time')
        c = 30
        d = 40
        embed()

    Parameters
    ----------

    header : str
        Optional header string to print at startup.
    compile_flags
        Passed to the `compile_flags` parameter of :py:meth:`terminal.embed.InteractiveShellEmbed.mainloop()`,
        which is called when the :class:`terminal.embed.InteractiveShellEmbed` instance is called.
    **kwargs : various, optional
        Any other kwargs will be passed to the :class:`terminal.embed.InteractiveShellEmbed` constructor.
        Full customization can be done by passing a traitlets :class:`Config` in as the
        `config` argument (see :ref:`configure_start_ipython` and :ref:`terminal_options`).
    """
    config = kwargs.get('config')
    if config is None:
        config = load_default_config()
        config.InteractiveShellEmbed = config.TerminalInteractiveShell
        kwargs["config"] = config
    using = kwargs.get("using", "sync")
    colors = kwargs.pop("colors", "nocolor")
    if using:
        kwargs["config"].update(
            {
                "TerminalInteractiveShell": {
                    "loop_runner": using,
                    "colors": colors,
                    "autoawait": using != "sync",
                }
            }
        )
    # save ps1/ps2 if defined
    ps1 = None
    ps2 = None
    try:
        ps1 = sys.ps1
        ps2 = sys.ps2
    except AttributeError:
        pass
    #save previous instance
    saved_shell_instance = InteractiveShell._instance
    if saved_shell_instance is not None:
        cls = type(saved_shell_instance)
        cls.clear_instance()
    frame = sys._getframe(1)
    shell = InteractiveShellEmbed.instance(_init_location_id='%s:%s' % (
        frame.f_code.co_filename, frame.f_lineno), **kwargs)
    shell(header=header, stack_depth=2, compile_flags=compile_flags,
        _call_location_id='%s:%s' % (frame.f_code.co_filename, frame.f_lineno))
    InteractiveShellEmbed.clear_instance()
    #restore previous instance
    if saved_shell_instance is not None:
        cls = type(saved_shell_instance)
        cls.clear_instance()
        for subclass in cls._walk_mro():
            subclass._instance = saved_shell_instance
    if ps1 is not None:
        sys.ps1 = ps1
        sys.ps2 = ps2

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\ui_crud_endpoints\proxy_setting_endpoints.py ===
#### CRUD ENDPOINTS for UI Settings #####
from typing import Any, Dict, List, Union

from fastapi import APIRouter, Depends, HTTPException

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import *
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.types.proxy.management_endpoints.ui_sso import DefaultTeamSSOParams, SSOConfig

router = APIRouter()


class IPAddress(BaseModel):
    ip: str


class SettingsResponse(BaseModel):
    """Base response model for settings with values and schema information"""
    
    values: Dict[str, Any]
    """The current configuration values"""
    
    field_schema: Dict[str, Any]
    """Schema information including descriptions and property types for UI display"""


class SSOSettingsResponse(SettingsResponse):
    """Response model for SSO settings"""
    pass


class InternalUserSettingsResponse(SettingsResponse):
    """Response model for internal user settings"""
    pass


class DefaultTeamSettingsResponse(SettingsResponse):
    """Response model for default team settings"""
    pass


@router.get(
    "/get/allowed_ips",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def get_allowed_ips():
    from litellm.proxy.proxy_server import general_settings

    _allowed_ip = general_settings.get("allowed_ips")
    return {"data": _allowed_ip}


@router.post(
    "/add/allowed_ip",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
)
async def add_allowed_ip(ip_address: IPAddress):
    from litellm.proxy.proxy_server import (
        general_settings,
        prisma_client,
        proxy_config,
        store_model_in_db,
    )

    _allowed_ips: List = general_settings.get("allowed_ips", [])
    if ip_address.ip not in _allowed_ips:
        _allowed_ips.append(ip_address.ip)
        general_settings["allowed_ips"] = _allowed_ips
    else:
        raise HTTPException(status_code=400, detail="IP address already exists")

    if prisma_client is None:
        raise Exception("No DB Connected")

    if store_model_in_db is not True:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Set `'STORE_MODEL_IN_DB='True'` in your env to enable this feature."
            },
        )

    # Load existing config
    config = await proxy_config.get_config()
    verbose_proxy_logger.debug("Loaded config: %s", config)
    if "general_settings" not in config:
        config["general_settings"] = {}

    if "allowed_ips" not in config["general_settings"]:
        config["general_settings"]["allowed_ips"] = []

    if ip_address.ip not in config["general_settings"]["allowed_ips"]:
        config["general_settings"]["allowed_ips"].append(ip_address.ip)

    await proxy_config.save_config(new_config=config)

    return {
        "message": f"IP {ip_address.ip} address added successfully",
        "status": "success",
    }


@router.post(
    "/delete/allowed_ip",
    tags=["Budget & Spend Tracking"],
    dependencies=[Depends(user_api_key_auth)],
)
async def delete_allowed_ip(ip_address: IPAddress):
    from litellm.proxy.proxy_server import general_settings, proxy_config

    _allowed_ips: List = general_settings.get("allowed_ips", [])
    if ip_address.ip in _allowed_ips:
        _allowed_ips.remove(ip_address.ip)
        general_settings["allowed_ips"] = _allowed_ips
    else:
        raise HTTPException(status_code=404, detail="IP address not found")

    # Load existing config
    config = await proxy_config.get_config()
    verbose_proxy_logger.debug("Loaded config: %s", config)
    if "general_settings" not in config:
        config["general_settings"] = {}

    if "allowed_ips" not in config["general_settings"]:
        config["general_settings"]["allowed_ips"] = []

    if ip_address.ip in config["general_settings"]["allowed_ips"]:
        config["general_settings"]["allowed_ips"].remove(ip_address.ip)

    await proxy_config.save_config(new_config=config)

    return {"message": f"IP {ip_address.ip} deleted successfully", "status": "success"}


async def _get_settings_with_schema(
    settings_key: str,
    settings_class: Any,
    config: dict,
) -> dict:
    """
    Common utility function to get settings with schema information.

    Args:
        settings_key: The key in litellm_settings to get
        settings_class: The Pydantic class to use for schema
        config: The config dictionary
    """
    from pydantic import TypeAdapter

    litellm_settings = config.get("litellm_settings", {}) or {}
    settings_data = litellm_settings.get(settings_key, {}) or {}

    # Create the settings object
    settings = settings_class(**(settings_data))
    # Get the schema
    schema = TypeAdapter(settings_class).json_schema(by_alias=True)

    # Convert to dict for response
    settings_dict = settings.model_dump()

    # Add descriptions to the response
    result = {
        "values": settings_dict,
        "field_schema": {"description": schema.get("description", ""), "properties": {}},
    }

    # Add property descriptions
    for field_name, field_info in schema["properties"].items():
        result["field_schema"]["properties"][field_name] = {
            "description": field_info.get("description", ""),
            "type": field_info.get("type", "string"),
        }

    # Add nested object descriptions
    for def_name, def_schema in schema.get("definitions", {}).items():
        result["field_schema"][def_name] = {
            "description": def_schema.get("description", ""),
            "properties": {
                prop_name: {"description": prop_info.get("description", "")}
                for prop_name, prop_info in def_schema.get("properties", {}).items()
            },
        }

    return result


@router.get(
    "/get/internal_user_settings",
    tags=["SSO Settings"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=InternalUserSettingsResponse,
)
async def get_internal_user_settings():
    """
    Get all SSO settings from the litellm_settings configuration.
    Returns a structured object with values and descriptions for UI display.
    """
    from litellm.proxy.proxy_server import proxy_config

    # Load existing config
    config = await proxy_config.get_config()

    return await _get_settings_with_schema(
        settings_key="default_internal_user_params",
        settings_class=DefaultInternalUserParams,
        config=config,
    )


@router.get(
    "/get/default_team_settings",
    tags=["SSO Settings"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=DefaultTeamSettingsResponse,
)
async def get_default_team_settings():
    """
    Get all SSO settings from the litellm_settings configuration.
    Returns a structured object with values and descriptions for UI display.
    """
    from litellm.proxy.proxy_server import proxy_config

    # Load existing config
    config = await proxy_config.get_config()

    return await _get_settings_with_schema(
        settings_key="default_team_params",
        settings_class=DefaultTeamSSOParams,
        config=config,
    )


async def _update_litellm_setting(
    settings: Union[DefaultInternalUserParams, DefaultTeamSSOParams],
    settings_key: str,
    in_memory_var: Any,
    success_message: str,
):
    """
    Common utility function to update `litellm_settings` in both memory and config.

    Args:
        settings: The settings object to update
        settings_key: The key in litellm_settings to update
        in_memory_var: The in-memory variable to update
        success_message: Message to return on success
    """
    from litellm.proxy.proxy_server import proxy_config

    # Update the in-memory settings
    in_memory_var = settings.model_dump(exclude_none=True)

    # Load existing config
    config = await proxy_config.get_config()

    # Update config with new settings
    if "litellm_settings" not in config:
        config["litellm_settings"] = {}

    config["litellm_settings"][settings_key] = settings.model_dump(exclude_none=True)

    # Save the updated config
    await proxy_config.save_config(new_config=config)

    return {
        "message": success_message,
        "status": "success",
        "settings": in_memory_var,
    }


@router.patch(
    "/update/internal_user_settings",
    tags=["SSO Settings"],
    dependencies=[Depends(user_api_key_auth)],
)
async def update_internal_user_settings(settings: DefaultInternalUserParams):
    """
    Update the default internal user parameters for SSO users.
    These settings will be applied to new users who sign in via SSO.
    """
    return await _update_litellm_setting(
        settings=settings,
        settings_key="default_internal_user_params",
        in_memory_var=litellm.default_internal_user_params,
        success_message="Internal user settings updated successfully",
    )


@router.patch(
    "/update/default_team_settings",
    tags=["SSO Settings"],
    dependencies=[Depends(user_api_key_auth)],
)
async def update_default_team_settings(settings: DefaultTeamSSOParams):
    """
    Update the default team parameters for SSO users.
    These settings will be applied to new teams created from SSO.
    """
    return await _update_litellm_setting(
        settings=settings,
        settings_key="default_team_params",
        in_memory_var=litellm.default_team_params,
        success_message="Default team settings updated successfully",
    )


@router.get(
    "/get/sso_settings",
    tags=["SSO Settings"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=SSOSettingsResponse,
)
async def get_sso_settings():
    """
    Get all SSO configuration settings from the environment variables.
    Returns a structured object with values and descriptions for UI display.
    """
    import os
    from litellm.proxy.proxy_server import proxy_config
    
    # Load existing config to get both environment variables and general settings
    config = await proxy_config.get_config()
    general_settings = config.get("general_settings", {}) or {}
    environment_variables = config.get("environment_variables", {}) or {}
    
    # Get user_email from general_settings
    proxy_admin_email = general_settings.get("proxy_admin_email", None)
    
    # Helper function to get env var value (first from config, then from environment)
    def get_env_value(env_var_name: str):
        return environment_variables.get(env_var_name) or os.getenv(env_var_name)
    
    # Get current environment variables for SSO
    sso_config = SSOConfig(
        google_client_id=get_env_value("GOOGLE_CLIENT_ID"),
        google_client_secret=get_env_value("GOOGLE_CLIENT_SECRET"),
        microsoft_client_id=get_env_value("MICROSOFT_CLIENT_ID"),
        microsoft_client_secret=get_env_value("MICROSOFT_CLIENT_SECRET"),
        microsoft_tenant=get_env_value("MICROSOFT_TENANT"),
        generic_client_id=get_env_value("GENERIC_CLIENT_ID"),
        generic_client_secret=get_env_value("GENERIC_CLIENT_SECRET"),
        generic_authorization_endpoint=get_env_value("GENERIC_AUTHORIZATION_ENDPOINT"),
        generic_token_endpoint=get_env_value("GENERIC_TOKEN_ENDPOINT"),
        generic_userinfo_endpoint=get_env_value("GENERIC_USERINFO_ENDPOINT"),
        proxy_base_url=get_env_value("PROXY_BASE_URL"),
        user_email=proxy_admin_email,  # Get from config instead of environment
    )
    
    # Get the schema for UI display
    from pydantic import TypeAdapter
    schema = TypeAdapter(SSOConfig).json_schema(by_alias=True)
    
    # Convert to dict for response
    sso_dict = sso_config.model_dump()
    
    # Add descriptions to the response
    result = {
        "values": sso_dict,
        "field_schema": {"description": schema.get("description", ""), "properties": {}},
    }
    
    # Add property descriptions
    for field_name, field_info in schema["properties"].items():
        result["field_schema"]["properties"][field_name] = {
            "description": field_info.get("description", ""),
            "type": field_info.get("type", "string"),
        }
    
    return result


@router.patch(
    "/update/sso_settings",
    tags=["SSO Settings"],
    dependencies=[Depends(user_api_key_auth)],
)
async def update_sso_settings(sso_config: SSOConfig):
    """
    Update SSO configuration by saving to both environment variables and config file.
    """
    from litellm.proxy.proxy_server import proxy_config
    import os
    
    # Update environment variables
    env_var_mapping = {
        'google_client_id': 'GOOGLE_CLIENT_ID',
        'google_client_secret': 'GOOGLE_CLIENT_SECRET',
        'microsoft_client_id': 'MICROSOFT_CLIENT_ID',
        'microsoft_client_secret': 'MICROSOFT_CLIENT_SECRET',
        'microsoft_tenant': 'MICROSOFT_TENANT',
        'generic_client_id': 'GENERIC_CLIENT_ID',
        'generic_client_secret': 'GENERIC_CLIENT_SECRET',
        'generic_authorization_endpoint': 'GENERIC_AUTHORIZATION_ENDPOINT',
        'generic_token_endpoint': 'GENERIC_TOKEN_ENDPOINT',
        'generic_userinfo_endpoint': 'GENERIC_USERINFO_ENDPOINT',
        'proxy_base_url': 'PROXY_BASE_URL',
    }
    
    # Load existing config
    config = await proxy_config.get_config()
    
    # Update config with new environment variables
    if "environment_variables" not in config:
        config["environment_variables"] = {}
    
    # Update general_settings for user_email (admin email)
    if "general_settings" not in config:
        config["general_settings"] = {}
    
    # Update environment variables in config and in memory
    sso_data = sso_config.model_dump(exclude_none=True)
    for field_name, value in sso_data.items():
        if field_name == 'user_email' and value is not None:
            # Store user_email in general_settings instead of environment variables
            config["general_settings"]["proxy_admin_email"] = value
        elif field_name in env_var_mapping and value is not None:
            env_var_name = env_var_mapping[field_name]
            # Update in config
            config["environment_variables"][env_var_name] = value
            # Update in runtime environment
            os.environ[env_var_name] = value
    
    # Save the updated config
    await proxy_config.save_config(new_config=config)
    
    return {
        "message": "SSO settings updated successfully",
        "status": "success",
        "settings": sso_data,
    }

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\client\cli\commands\models.py ===
# stdlib imports
from datetime import datetime
import re
from typing import Optional, Literal, Any
import yaml
from dataclasses import dataclass
from collections import defaultdict

# third party imports
import click
import rich

# local imports
from ... import Client


@dataclass
class ModelYamlInfo:
    model_name: str
    model_params: dict[str, Any]
    model_info: dict[str, Any]
    model_id: str
    access_groups: list[str]
    provider: str

    @property
    def access_groups_str(self) -> str:
        return ", ".join(self.access_groups) if self.access_groups else ""


def _get_model_info_obj_from_yaml(model: dict[str, Any]) -> ModelYamlInfo:
    """Extract model info from a model dict and return as ModelYamlInfo dataclass."""
    model_name: str = model["model_name"]
    model_params: dict[str, Any] = model["litellm_params"]
    model_info: dict[str, Any] = model.get("model_info", {})
    model_id: str = model_params["model"]
    access_groups = model_info.get("access_groups", [])
    provider = model_id.split("/", 1)[0] if "/" in model_id else model_id
    return ModelYamlInfo(
        model_name=model_name,
        model_params=model_params,
        model_info=model_info,
        model_id=model_id,
        access_groups=access_groups,
        provider=provider,
    )


def format_iso_datetime_str(iso_datetime_str: Optional[str]) -> str:
    """Format an ISO format datetime string to human-readable date with minute resolution."""
    if not iso_datetime_str:
        return ""
    try:
        # Parse ISO format datetime string
        dt = datetime.fromisoformat(iso_datetime_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return str(iso_datetime_str)


def format_timestamp(timestamp: Optional[int]) -> str:
    """Format a Unix timestamp (integer) to human-readable date with minute resolution."""
    if timestamp is None:
        return ""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return str(timestamp)


def format_cost_per_1k_tokens(cost: Optional[float]) -> str:
    """Format a per-token cost to cost per 1000 tokens."""
    if cost is None:
        return ""
    try:
        # Convert string to float if needed
        cost_float = float(cost)
        # Multiply by 1000 and format to 4 decimal places
        return f"${cost_float * 1000:.4f}"
    except (TypeError, ValueError):
        return str(cost)


def create_client(ctx: click.Context) -> Client:
    """Helper function to create a client from context."""
    return Client(base_url=ctx.obj["base_url"], api_key=ctx.obj["api_key"])


@click.group()
def models() -> None:
    """Manage models on your LiteLLM proxy server"""
    pass


@models.command("list")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format (table or json)",
)
@click.pass_context
def list_models(ctx: click.Context, output_format: Literal["table", "json"]) -> None:
    """List all available models"""
    client = create_client(ctx)
    models_list = client.models.list()
    assert isinstance(models_list, list)

    if output_format == "json":
        rich.print_json(data=models_list)
    else:  # table format
        table = rich.table.Table(title="Available Models")

        # Add columns based on the data structure
        table.add_column("ID", style="cyan")
        table.add_column("Object", style="green")
        table.add_column("Created", style="magenta")
        table.add_column("Owned By", style="yellow")

        # Add rows
        for model in models_list:
            created = model.get("created")
            # Convert string timestamp to integer if needed
            if isinstance(created, str) and created.isdigit():
                created = int(created)

            table.add_row(
                str(model.get("id", "")),
                str(model.get("object", "model")),
                format_timestamp(created) if isinstance(created, int) else format_iso_datetime_str(created),
                str(model.get("owned_by", "")),
            )

        rich.print(table)


@models.command("add")
@click.argument("model-name")
@click.option(
    "--param",
    "-p",
    multiple=True,
    help="Model parameters in key=value format (can be specified multiple times)",
)
@click.option(
    "--info",
    "-i",
    multiple=True,
    help="Model info in key=value format (can be specified multiple times)",
)
@click.pass_context
def add_model(ctx: click.Context, model_name: str, param: tuple[str, ...], info: tuple[str, ...]) -> None:
    """Add a new model to the proxy"""
    # Convert parameters from key=value format to dict
    model_params = dict(p.split("=", 1) for p in param)
    model_info = dict(i.split("=", 1) for i in info) if info else None

    client = create_client(ctx)
    result = client.models.new(
        model_name=model_name,
        model_params=model_params,
        model_info=model_info,
    )
    rich.print_json(data=result)


@models.command("delete")
@click.argument("model-id")
@click.pass_context
def delete_model(ctx: click.Context, model_id: str) -> None:
    """Delete a model from the proxy"""
    client = create_client(ctx)
    result = client.models.delete(model_id=model_id)
    rich.print_json(data=result)


@models.command("get")
@click.option("--id", "model_id", help="ID of the model to retrieve")
@click.option("--name", "model_name", help="Name of the model to retrieve")
@click.pass_context
def get_model(ctx: click.Context, model_id: Optional[str], model_name: Optional[str]) -> None:
    """Get information about a specific model"""
    if not model_id and not model_name:
        raise click.UsageError("Either --id or --name must be provided")

    client = create_client(ctx)
    result = client.models.get(model_id=model_id, model_name=model_name)
    rich.print_json(data=result)


@models.command("info")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format (table or json)",
)
@click.option(
    "--columns",
    "columns",
    default="public_model,upstream_model,updated_at",
    help="Comma-separated list of columns to display. Valid columns: public_model, upstream_model, credential_name, created_at, updated_at, id, input_cost, output_cost. Default: public_model,upstream_model,updated_at",
)
@click.pass_context
def get_models_info(ctx: click.Context, output_format: Literal["table", "json"], columns: str) -> None:
    """Get detailed information about all models"""
    client = create_client(ctx)
    models_info = client.models.info()
    assert isinstance(models_info, list)

    if output_format == "json":
        rich.print_json(data=models_info)
    else:  # table format
        table = rich.table.Table(title="Models Information")

        # Define all possible columns with their configurations
        column_configs: dict[str, dict[str, Any]] = {
            "public_model": {
                "header": "Public Model",
                "style": "cyan",
                "get_value": lambda m: str(m.get("model_name", "")),
            },
            "upstream_model": {
                "header": "Upstream Model",
                "style": "green",
                "get_value": lambda m: str(m.get("litellm_params", {}).get("model", "")),
            },
            "credential_name": {
                "header": "Credential Name",
                "style": "yellow",
                "get_value": lambda m: str(m.get("litellm_params", {}).get("litellm_credential_name", "")),
            },
            "created_at": {
                "header": "Created At",
                "style": "magenta",
                "get_value": lambda m: format_iso_datetime_str(m.get("model_info", {}).get("created_at")),
            },
            "updated_at": {
                "header": "Updated At",
                "style": "magenta",
                "get_value": lambda m: format_iso_datetime_str(m.get("model_info", {}).get("updated_at")),
            },
            "id": {
                "header": "ID",
                "style": "blue",
                "get_value": lambda m: str(m.get("model_info", {}).get("id", "")),
            },
            "input_cost": {
                "header": "Input Cost",
                "style": "green",
                "justify": "right",
                "get_value": lambda m: format_cost_per_1k_tokens(m.get("model_info", {}).get("input_cost_per_token")),
            },
            "output_cost": {
                "header": "Output Cost",
                "style": "green",
                "justify": "right",
                "get_value": lambda m: format_cost_per_1k_tokens(m.get("model_info", {}).get("output_cost_per_token")),
            },
        }

        # Add requested columns
        requested_columns = [col.strip() for col in columns.split(",")]
        for col_name in requested_columns:
            if col_name in column_configs:
                config = column_configs[col_name]
                table.add_column(config["header"], style=config["style"], justify=config.get("justify", "left"))
            else:
                click.echo(f"Warning: Unknown column '{col_name}'", err=True)

        # Add rows with only the requested columns
        for model in models_info:
            row_values = []
            for col_name in requested_columns:
                if col_name in column_configs:
                    row_values.append(column_configs[col_name]["get_value"](model))
            if row_values:
                table.add_row(*row_values)

        rich.print(table)


@models.command("update")
@click.argument("model-id")
@click.option(
    "--param",
    "-p",
    multiple=True,
    help="Model parameters in key=value format (can be specified multiple times)",
)
@click.option(
    "--info",
    "-i",
    multiple=True,
    help="Model info in key=value format (can be specified multiple times)",
)
@click.pass_context
def update_model(ctx: click.Context, model_id: str, param: tuple[str, ...], info: tuple[str, ...]) -> None:
    """Update an existing model's configuration"""
    # Convert parameters from key=value format to dict
    model_params = dict(p.split("=", 1) for p in param)
    model_info = dict(i.split("=", 1) for i in info) if info else None

    client = create_client(ctx)
    result = client.models.update(
        model_id=model_id,
        model_params=model_params,
        model_info=model_info,
    )
    rich.print_json(data=result)


def _filter_model(model, model_regex, access_group_regex):
    model_name = model.get("model_name")
    model_params = model.get("litellm_params")
    model_info = model.get("model_info", {})
    if not model_name or not model_params:
        return False
    model_id = model_params.get("model")
    if not model_id or not isinstance(model_id, str):
        return False
    if model_regex and not model_regex.search(model_id):
        return False
    access_groups = model_info.get("access_groups", [])
    if access_group_regex:
        if not isinstance(access_groups, list):
            return False
        if not any(isinstance(group, str) and access_group_regex.search(group) for group in access_groups):
            return False
    return True


def _print_models_table(added_models: list[ModelYamlInfo], table_title: str):
    if not added_models:
        return
    table = rich.table.Table(title=table_title)
    table.add_column("Model Name", style="cyan")
    table.add_column("Upstream Model", style="green")
    table.add_column("Access Groups", style="magenta")
    for m in added_models:
        table.add_row(m.model_name, m.model_id, m.access_groups_str)
    rich.print(table)


def _print_summary_table(provider_counts):
    summary_table = rich.table.Table(title="Model Import Summary")
    summary_table.add_column("Provider", style="cyan")
    summary_table.add_column("Count", style="green")

    for provider, count in provider_counts.items():
        summary_table.add_row(str(provider), str(count))

    total = sum(provider_counts.values())
    summary_table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")

    rich.print(summary_table)


def get_model_list_from_yaml_file(yaml_file: str) -> list[dict[str, Any]]:
    """Load and validate the model list from a YAML file."""
    with open(yaml_file, "r") as f:
        data = yaml.safe_load(f)
    if not data or "model_list" not in data:
        raise click.ClickException("YAML file must contain a 'model_list' key with a list of models.")
    model_list = data["model_list"]
    if not isinstance(model_list, list):
        raise click.ClickException("'model_list' must be a list of model definitions.")
    return model_list


def _get_filtered_model_list(model_list, only_models_matching_regex, only_access_groups_matching_regex):
    """Return a list of models that pass the filter criteria."""
    model_regex = re.compile(only_models_matching_regex) if only_models_matching_regex else None
    access_group_regex = re.compile(only_access_groups_matching_regex) if only_access_groups_matching_regex else None
    return [model for model in model_list if _filter_model(model, model_regex, access_group_regex)]


def _import_models_get_table_title(dry_run: bool) -> str:
    if dry_run:
        return "Models that would be imported if [yellow]--dry-run[/yellow] was not provided"
    else:
        return "Models Imported"


@models.command("import")
@click.argument("yaml_file", type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option("--dry-run", is_flag=True, help="Show what would be imported without making any changes.")
@click.option(
    "--only-models-matching-regex",
    default=None,
    help="Only import models where litellm_params.model matches the given regex.",
)
@click.option(
    "--only-access-groups-matching-regex",
    default=None,
    help="Only import models where at least one item in model_info.access_groups matches the given regex.",
)
@click.pass_context
def import_models(
    ctx: click.Context,
    yaml_file: str,
    dry_run: bool,
    only_models_matching_regex: Optional[str],
    only_access_groups_matching_regex: Optional[str],
) -> None:
    """Import models from a YAML file and add them to the proxy."""
    provider_counts: dict[str, int] = defaultdict(int)
    added_models: list[ModelYamlInfo] = []
    model_list = get_model_list_from_yaml_file(yaml_file)
    filtered_model_list = _get_filtered_model_list(
        model_list, only_models_matching_regex, only_access_groups_matching_regex
    )

    if not dry_run:
        client = create_client(ctx)

    for model in filtered_model_list:
        model_info_obj = _get_model_info_obj_from_yaml(model)
        if not dry_run:
            try:
                client.models.new(
                    model_name=model_info_obj.model_name,
                    model_params=model_info_obj.model_params,
                    model_info=model_info_obj.model_info,
                )
            except Exception:
                pass  # For summary, ignore errors
        added_models.append(model_info_obj)
        provider_counts[model_info_obj.provider] += 1

    table_title = _import_models_get_table_title(dry_run)
    _print_models_table(added_models, table_title)
    _print_summary_table(provider_counts)