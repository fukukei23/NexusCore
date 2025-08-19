
# === NexusCore/openenv\Lib\site-packages\anyio\_core\_fileio.py ===
from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import (
    AsyncIterator,
    Callable,
    Iterable,
    Iterator,
    Sequence,
)
from dataclasses import dataclass
from functools import partial
from os import PathLike
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    AnyStr,
    ClassVar,
    Final,
    Generic,
    overload,
)

from .. import to_thread
from ..abc import AsyncResource

if TYPE_CHECKING:
    from types import ModuleType

    from _typeshed import OpenBinaryMode, OpenTextMode, ReadableBuffer, WriteableBuffer
else:
    ReadableBuffer = OpenBinaryMode = OpenTextMode = WriteableBuffer = object


class AsyncFile(AsyncResource, Generic[AnyStr]):
    """
    An asynchronous file object.

    This class wraps a standard file object and provides async friendly versions of the
    following blocking methods (where available on the original file object):

    * read
    * read1
    * readline
    * readlines
    * readinto
    * readinto1
    * write
    * writelines
    * truncate
    * seek
    * tell
    * flush

    All other methods are directly passed through.

    This class supports the asynchronous context manager protocol which closes the
    underlying file at the end of the context block.

    This class also supports asynchronous iteration::

        async with await open_file(...) as f:
            async for line in f:
                print(line)
    """

    def __init__(self, fp: IO[AnyStr]) -> None:
        self._fp: Any = fp

    def __getattr__(self, name: str) -> object:
        return getattr(self._fp, name)

    @property
    def wrapped(self) -> IO[AnyStr]:
        """The wrapped file object."""
        return self._fp

    async def __aiter__(self) -> AsyncIterator[AnyStr]:
        while True:
            line = await self.readline()
            if line:
                yield line
            else:
                break

    async def aclose(self) -> None:
        return await to_thread.run_sync(self._fp.close)

    async def read(self, size: int = -1) -> AnyStr:
        return await to_thread.run_sync(self._fp.read, size)

    async def read1(self: AsyncFile[bytes], size: int = -1) -> bytes:
        return await to_thread.run_sync(self._fp.read1, size)

    async def readline(self) -> AnyStr:
        return await to_thread.run_sync(self._fp.readline)

    async def readlines(self) -> list[AnyStr]:
        return await to_thread.run_sync(self._fp.readlines)

    async def readinto(self: AsyncFile[bytes], b: WriteableBuffer) -> int:
        return await to_thread.run_sync(self._fp.readinto, b)

    async def readinto1(self: AsyncFile[bytes], b: WriteableBuffer) -> int:
        return await to_thread.run_sync(self._fp.readinto1, b)

    @overload
    async def write(self: AsyncFile[bytes], b: ReadableBuffer) -> int: ...

    @overload
    async def write(self: AsyncFile[str], b: str) -> int: ...

    async def write(self, b: ReadableBuffer | str) -> int:
        return await to_thread.run_sync(self._fp.write, b)

    @overload
    async def writelines(
        self: AsyncFile[bytes], lines: Iterable[ReadableBuffer]
    ) -> None: ...

    @overload
    async def writelines(self: AsyncFile[str], lines: Iterable[str]) -> None: ...

    async def writelines(self, lines: Iterable[ReadableBuffer] | Iterable[str]) -> None:
        return await to_thread.run_sync(self._fp.writelines, lines)

    async def truncate(self, size: int | None = None) -> int:
        return await to_thread.run_sync(self._fp.truncate, size)

    async def seek(self, offset: int, whence: int | None = os.SEEK_SET) -> int:
        return await to_thread.run_sync(self._fp.seek, offset, whence)

    async def tell(self) -> int:
        return await to_thread.run_sync(self._fp.tell)

    async def flush(self) -> None:
        return await to_thread.run_sync(self._fp.flush)


@overload
async def open_file(
    file: str | PathLike[str] | int,
    mode: OpenBinaryMode,
    buffering: int = ...,
    encoding: str | None = ...,
    errors: str | None = ...,
    newline: str | None = ...,
    closefd: bool = ...,
    opener: Callable[[str, int], int] | None = ...,
) -> AsyncFile[bytes]: ...


@overload
async def open_file(
    file: str | PathLike[str] | int,
    mode: OpenTextMode = ...,
    buffering: int = ...,
    encoding: str | None = ...,
    errors: str | None = ...,
    newline: str | None = ...,
    closefd: bool = ...,
    opener: Callable[[str, int], int] | None = ...,
) -> AsyncFile[str]: ...


async def open_file(
    file: str | PathLike[str] | int,
    mode: str = "r",
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: Callable[[str, int], int] | None = None,
) -> AsyncFile[Any]:
    """
    Open a file asynchronously.

    The arguments are exactly the same as for the builtin :func:`open`.

    :return: an asynchronous file object

    """
    fp = await to_thread.run_sync(
        open, file, mode, buffering, encoding, errors, newline, closefd, opener
    )
    return AsyncFile(fp)


def wrap_file(file: IO[AnyStr]) -> AsyncFile[AnyStr]:
    """
    Wrap an existing file as an asynchronous file.

    :param file: an existing file-like object
    :return: an asynchronous file object

    """
    return AsyncFile(file)


@dataclass(eq=False)
class _PathIterator(AsyncIterator["Path"]):
    iterator: Iterator[PathLike[str]]

    async def __anext__(self) -> Path:
        nextval = await to_thread.run_sync(
            next, self.iterator, None, abandon_on_cancel=True
        )
        if nextval is None:
            raise StopAsyncIteration from None

        return Path(nextval)


class Path:
    """
    An asynchronous version of :class:`pathlib.Path`.

    This class cannot be substituted for :class:`pathlib.Path` or
    :class:`pathlib.PurePath`, but it is compatible with the :class:`os.PathLike`
    interface.

    It implements the Python 3.10 version of :class:`pathlib.Path` interface, except for
    the deprecated :meth:`~pathlib.Path.link_to` method.

    Some methods may be unavailable or have limited functionality, based on the Python
    version:

    * :meth:`~pathlib.Path.copy` (available on Python 3.14 or later)
    * :meth:`~pathlib.Path.copy_into` (available on Python 3.14 or later)
    * :meth:`~pathlib.Path.from_uri` (available on Python 3.13 or later)
    * :meth:`~pathlib.PurePath.full_match` (available on Python 3.13 or later)
    * :attr:`~pathlib.Path.info` (available on Python 3.14 or later)
    * :meth:`~pathlib.Path.is_junction` (available on Python 3.12 or later)
    * :meth:`~pathlib.PurePath.match` (the ``case_sensitive`` parameter is only
      available on Python 3.13 or later)
    * :meth:`~pathlib.Path.move` (available on Python 3.14 or later)
    * :meth:`~pathlib.Path.move_into` (available on Python 3.14 or later)
    * :meth:`~pathlib.PurePath.relative_to` (the ``walk_up`` parameter is only available
      on Python 3.12 or later)
    * :meth:`~pathlib.Path.walk` (available on Python 3.12 or later)

    Any methods that do disk I/O need to be awaited on. These methods are:

    * :meth:`~pathlib.Path.absolute`
    * :meth:`~pathlib.Path.chmod`
    * :meth:`~pathlib.Path.cwd`
    * :meth:`~pathlib.Path.exists`
    * :meth:`~pathlib.Path.expanduser`
    * :meth:`~pathlib.Path.group`
    * :meth:`~pathlib.Path.hardlink_to`
    * :meth:`~pathlib.Path.home`
    * :meth:`~pathlib.Path.is_block_device`
    * :meth:`~pathlib.Path.is_char_device`
    * :meth:`~pathlib.Path.is_dir`
    * :meth:`~pathlib.Path.is_fifo`
    * :meth:`~pathlib.Path.is_file`
    * :meth:`~pathlib.Path.is_junction`
    * :meth:`~pathlib.Path.is_mount`
    * :meth:`~pathlib.Path.is_socket`
    * :meth:`~pathlib.Path.is_symlink`
    * :meth:`~pathlib.Path.lchmod`
    * :meth:`~pathlib.Path.lstat`
    * :meth:`~pathlib.Path.mkdir`
    * :meth:`~pathlib.Path.open`
    * :meth:`~pathlib.Path.owner`
    * :meth:`~pathlib.Path.read_bytes`
    * :meth:`~pathlib.Path.read_text`
    * :meth:`~pathlib.Path.readlink`
    * :meth:`~pathlib.Path.rename`
    * :meth:`~pathlib.Path.replace`
    * :meth:`~pathlib.Path.resolve`
    * :meth:`~pathlib.Path.rmdir`
    * :meth:`~pathlib.Path.samefile`
    * :meth:`~pathlib.Path.stat`
    * :meth:`~pathlib.Path.symlink_to`
    * :meth:`~pathlib.Path.touch`
    * :meth:`~pathlib.Path.unlink`
    * :meth:`~pathlib.Path.walk`
    * :meth:`~pathlib.Path.write_bytes`
    * :meth:`~pathlib.Path.write_text`

    Additionally, the following methods return an async iterator yielding
    :class:`~.Path` objects:

    * :meth:`~pathlib.Path.glob`
    * :meth:`~pathlib.Path.iterdir`
    * :meth:`~pathlib.Path.rglob`
    """

    __slots__ = "_path", "__weakref__"

    __weakref__: Any

    def __init__(self, *args: str | PathLike[str]) -> None:
        self._path: Final[pathlib.Path] = pathlib.Path(*args)

    def __fspath__(self) -> str:
        return self._path.__fspath__()

    def __str__(self) -> str:
        return self._path.__str__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.as_posix()!r})"

    def __bytes__(self) -> bytes:
        return self._path.__bytes__()

    def __hash__(self) -> int:
        return self._path.__hash__()

    def __eq__(self, other: object) -> bool:
        target = other._path if isinstance(other, Path) else other
        return self._path.__eq__(target)

    def __lt__(self, other: pathlib.PurePath | Path) -> bool:
        target = other._path if isinstance(other, Path) else other
        return self._path.__lt__(target)

    def __le__(self, other: pathlib.PurePath | Path) -> bool:
        target = other._path if isinstance(other, Path) else other
        return self._path.__le__(target)

    def __gt__(self, other: pathlib.PurePath | Path) -> bool:
        target = other._path if isinstance(other, Path) else other
        return self._path.__gt__(target)

    def __ge__(self, other: pathlib.PurePath | Path) -> bool:
        target = other._path if isinstance(other, Path) else other
        return self._path.__ge__(target)

    def __truediv__(self, other: str | PathLike[str]) -> Path:
        return Path(self._path / other)

    def __rtruediv__(self, other: str | PathLike[str]) -> Path:
        return Path(other) / self

    @property
    def parts(self) -> tuple[str, ...]:
        return self._path.parts

    @property
    def drive(self) -> str:
        return self._path.drive

    @property
    def root(self) -> str:
        return self._path.root

    @property
    def anchor(self) -> str:
        return self._path.anchor

    @property
    def parents(self) -> Sequence[Path]:
        return tuple(Path(p) for p in self._path.parents)

    @property
    def parent(self) -> Path:
        return Path(self._path.parent)

    @property
    def name(self) -> str:
        return self._path.name

    @property
    def suffix(self) -> str:
        return self._path.suffix

    @property
    def suffixes(self) -> list[str]:
        return self._path.suffixes

    @property
    def stem(self) -> str:
        return self._path.stem

    async def absolute(self) -> Path:
        path = await to_thread.run_sync(self._path.absolute)
        return Path(path)

    def as_posix(self) -> str:
        return self._path.as_posix()

    def as_uri(self) -> str:
        return self._path.as_uri()

    if sys.version_info >= (3, 13):
        parser: ClassVar[ModuleType] = pathlib.Path.parser

        @classmethod
        def from_uri(cls, uri: str) -> Path:
            return Path(pathlib.Path.from_uri(uri))

        def full_match(
            self, path_pattern: str, *, case_sensitive: bool | None = None
        ) -> bool:
            return self._path.full_match(path_pattern, case_sensitive=case_sensitive)

        def match(
            self, path_pattern: str, *, case_sensitive: bool | None = None
        ) -> bool:
            return self._path.match(path_pattern, case_sensitive=case_sensitive)
    else:

        def match(self, path_pattern: str) -> bool:
            return self._path.match(path_pattern)

    if sys.version_info >= (3, 14):

        @property
        def info(self) -> Any:  # TODO: add return type annotation when Typeshed gets it
            return self._path.info

        async def copy(
            self,
            target: str | os.PathLike[str],
            *,
            follow_symlinks: bool = True,
            dirs_exist_ok: bool = False,
            preserve_metadata: bool = False,
        ) -> Path:
            func = partial(
                self._path.copy,
                follow_symlinks=follow_symlinks,
                dirs_exist_ok=dirs_exist_ok,
                preserve_metadata=preserve_metadata,
            )
            return Path(await to_thread.run_sync(func, target))

        async def copy_into(
            self,
            target_dir: str | os.PathLike[str],
            *,
            follow_symlinks: bool = True,
            dirs_exist_ok: bool = False,
            preserve_metadata: bool = False,
        ) -> Path:
            func = partial(
                self._path.copy_into,
                follow_symlinks=follow_symlinks,
                dirs_exist_ok=dirs_exist_ok,
                preserve_metadata=preserve_metadata,
            )
            return Path(await to_thread.run_sync(func, target_dir))

        async def move(self, target: str | os.PathLike[str]) -> Path:
            # Upstream does not handle anyio.Path properly as a PathLike
            target = pathlib.Path(target)
            return Path(await to_thread.run_sync(self._path.move, target))

        async def move_into(
            self,
            target_dir: str | os.PathLike[str],
        ) -> Path:
            return Path(await to_thread.run_sync(self._path.move_into, target_dir))

    def is_relative_to(self, other: str | PathLike[str]) -> bool:
        try:
            self.relative_to(other)
            return True
        except ValueError:
            return False

    async def chmod(self, mode: int, *, follow_symlinks: bool = True) -> None:
        func = partial(os.chmod, follow_symlinks=follow_symlinks)
        return await to_thread.run_sync(func, self._path, mode)

    @classmethod
    async def cwd(cls) -> Path:
        path = await to_thread.run_sync(pathlib.Path.cwd)
        return cls(path)

    async def exists(self) -> bool:
        return await to_thread.run_sync(self._path.exists, abandon_on_cancel=True)

    async def expanduser(self) -> Path:
        return Path(
            await to_thread.run_sync(self._path.expanduser, abandon_on_cancel=True)
        )

    def glob(self, pattern: str) -> AsyncIterator[Path]:
        gen = self._path.glob(pattern)
        return _PathIterator(gen)

    async def group(self) -> str:
        return await to_thread.run_sync(self._path.group, abandon_on_cancel=True)

    async def hardlink_to(
        self, target: str | bytes | PathLike[str] | PathLike[bytes]
    ) -> None:
        if isinstance(target, Path):
            target = target._path

        await to_thread.run_sync(os.link, target, self)

    @classmethod
    async def home(cls) -> Path:
        home_path = await to_thread.run_sync(pathlib.Path.home)
        return cls(home_path)

    def is_absolute(self) -> bool:
        return self._path.is_absolute()

    async def is_block_device(self) -> bool:
        return await to_thread.run_sync(
            self._path.is_block_device, abandon_on_cancel=True
        )

    async def is_char_device(self) -> bool:
        return await to_thread.run_sync(
            self._path.is_char_device, abandon_on_cancel=True
        )

    async def is_dir(self) -> bool:
        return await to_thread.run_sync(self._path.is_dir, abandon_on_cancel=True)

    async def is_fifo(self) -> bool:
        return await to_thread.run_sync(self._path.is_fifo, abandon_on_cancel=True)

    async def is_file(self) -> bool:
        return await to_thread.run_sync(self._path.is_file, abandon_on_cancel=True)

    if sys.version_info >= (3, 12):

        async def is_junction(self) -> bool:
            return await to_thread.run_sync(self._path.is_junction)

    async def is_mount(self) -> bool:
        return await to_thread.run_sync(
            os.path.ismount, self._path, abandon_on_cancel=True
        )

    def is_reserved(self) -> bool:
        return self._path.is_reserved()

    async def is_socket(self) -> bool:
        return await to_thread.run_sync(self._path.is_socket, abandon_on_cancel=True)

    async def is_symlink(self) -> bool:
        return await to_thread.run_sync(self._path.is_symlink, abandon_on_cancel=True)

    async def iterdir(self) -> AsyncIterator[Path]:
        gen = (
            self._path.iterdir()
            if sys.version_info < (3, 13)
            else await to_thread.run_sync(self._path.iterdir, abandon_on_cancel=True)
        )
        async for path in _PathIterator(gen):
            yield path

    def joinpath(self, *args: str | PathLike[str]) -> Path:
        return Path(self._path.joinpath(*args))

    async def lchmod(self, mode: int) -> None:
        await to_thread.run_sync(self._path.lchmod, mode)

    async def lstat(self) -> os.stat_result:
        return await to_thread.run_sync(self._path.lstat, abandon_on_cancel=True)

    async def mkdir(
        self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        await to_thread.run_sync(self._path.mkdir, mode, parents, exist_ok)

    @overload
    async def open(
        self,
        mode: OpenBinaryMode,
        buffering: int = ...,
        encoding: str | None = ...,
        errors: str | None = ...,
        newline: str | None = ...,
    ) -> AsyncFile[bytes]: ...

    @overload
    async def open(
        self,
        mode: OpenTextMode = ...,
        buffering: int = ...,
        encoding: str | None = ...,
        errors: str | None = ...,
        newline: str | None = ...,
    ) -> AsyncFile[str]: ...

    async def open(
        self,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> AsyncFile[Any]:
        fp = await to_thread.run_sync(
            self._path.open, mode, buffering, encoding, errors, newline
        )
        return AsyncFile(fp)

    async def owner(self) -> str:
        return await to_thread.run_sync(self._path.owner, abandon_on_cancel=True)

    async def read_bytes(self) -> bytes:
        return await to_thread.run_sync(self._path.read_bytes)

    async def read_text(
        self, encoding: str | None = None, errors: str | None = None
    ) -> str:
        return await to_thread.run_sync(self._path.read_text, encoding, errors)

    if sys.version_info >= (3, 12):

        def relative_to(
            self, *other: str | PathLike[str], walk_up: bool = False
        ) -> Path:
            return Path(self._path.relative_to(*other, walk_up=walk_up))

    else:

        def relative_to(self, *other: str | PathLike[str]) -> Path:
            return Path(self._path.relative_to(*other))

    async def readlink(self) -> Path:
        target = await to_thread.run_sync(os.readlink, self._path)
        return Path(target)

    async def rename(self, target: str | pathlib.PurePath | Path) -> Path:
        if isinstance(target, Path):
            target = target._path

        await to_thread.run_sync(self._path.rename, target)
        return Path(target)

    async def replace(self, target: str | pathlib.PurePath | Path) -> Path:
        if isinstance(target, Path):
            target = target._path

        await to_thread.run_sync(self._path.replace, target)
        return Path(target)

    async def resolve(self, strict: bool = False) -> Path:
        func = partial(self._path.resolve, strict=strict)
        return Path(await to_thread.run_sync(func, abandon_on_cancel=True))

    def rglob(self, pattern: str) -> AsyncIterator[Path]:
        gen = self._path.rglob(pattern)
        return _PathIterator(gen)

    async def rmdir(self) -> None:
        await to_thread.run_sync(self._path.rmdir)

    async def samefile(self, other_path: str | PathLike[str]) -> bool:
        if isinstance(other_path, Path):
            other_path = other_path._path

        return await to_thread.run_sync(
            self._path.samefile, other_path, abandon_on_cancel=True
        )

    async def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
        func = partial(os.stat, follow_symlinks=follow_symlinks)
        return await to_thread.run_sync(func, self._path, abandon_on_cancel=True)

    async def symlink_to(
        self,
        target: str | bytes | PathLike[str] | PathLike[bytes],
        target_is_directory: bool = False,
    ) -> None:
        if isinstance(target, Path):
            target = target._path

        await to_thread.run_sync(self._path.symlink_to, target, target_is_directory)

    async def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None:
        await to_thread.run_sync(self._path.touch, mode, exist_ok)

    async def unlink(self, missing_ok: bool = False) -> None:
        try:
            await to_thread.run_sync(self._path.unlink)
        except FileNotFoundError:
            if not missing_ok:
                raise

    if sys.version_info >= (3, 12):

        async def walk(
            self,
            top_down: bool = True,
            on_error: Callable[[OSError], object] | None = None,
            follow_symlinks: bool = False,
        ) -> AsyncIterator[tuple[Path, list[str], list[str]]]:
            def get_next_value() -> tuple[pathlib.Path, list[str], list[str]] | None:
                try:
                    return next(gen)
                except StopIteration:
                    return None

            gen = self._path.walk(top_down, on_error, follow_symlinks)
            while True:
                value = await to_thread.run_sync(get_next_value)
                if value is None:
                    return

                root, dirs, paths = value
                yield Path(root), dirs, paths

    def with_name(self, name: str) -> Path:
        return Path(self._path.with_name(name))

    def with_stem(self, stem: str) -> Path:
        return Path(self._path.with_name(stem + self._path.suffix))

    def with_suffix(self, suffix: str) -> Path:
        return Path(self._path.with_suffix(suffix))

    def with_segments(self, *pathsegments: str | PathLike[str]) -> Path:
        return Path(*pathsegments)

    async def write_bytes(self, data: bytes) -> int:
        return await to_thread.run_sync(self._path.write_bytes, data)

    async def write_text(
        self,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        # Path.write_text() does not support the "newline" parameter before Python 3.10
        def sync_write_text() -> int:
            with self._path.open(
                "w", encoding=encoding, errors=errors, newline=newline
            ) as fp:
                return fp.write(data)

        return await to_thread.run_sync(sync_write_text)


PathLike.register(Path)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\operations\install\wheel.py ===
"""Support for installing and building the "wheel" binary package format.
"""

import collections
import compileall
import contextlib
import csv
import importlib
import logging
import os.path
import re
import shutil
import sys
import warnings
from base64 import urlsafe_b64encode
from email.message import Message
from itertools import chain, filterfalse, starmap
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Callable,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    NewType,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    Union,
    cast,
)
from zipfile import ZipFile, ZipInfo

from pip._vendor.distlib.scripts import ScriptMaker
from pip._vendor.distlib.util import get_export_entry
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.exceptions import InstallationError
from pip._internal.locations import get_major_minor_version
from pip._internal.metadata import (
    BaseDistribution,
    FilesystemWheel,
    get_wheel_distribution,
)
from pip._internal.models.direct_url import DIRECT_URL_METADATA_NAME, DirectUrl
from pip._internal.models.scheme import SCHEME_KEYS, Scheme
from pip._internal.utils.filesystem import adjacent_tmp_file, replace
from pip._internal.utils.misc import StreamWrapper, ensure_dir, hash_file, partition
from pip._internal.utils.unpacking import (
    current_umask,
    is_within_directory,
    set_extracted_file_to_default_mode_plus_executable,
    zip_item_is_executable,
)
from pip._internal.utils.wheel import parse_wheel

if TYPE_CHECKING:

    class File(Protocol):
        src_record_path: "RecordPath"
        dest_path: str
        changed: bool

        def save(self) -> None:
            pass


logger = logging.getLogger(__name__)

RecordPath = NewType("RecordPath", str)
InstalledCSVRow = Tuple[RecordPath, str, Union[int, str]]


def rehash(path: str, blocksize: int = 1 << 20) -> Tuple[str, str]:
    """Return (encoded_digest, length) for path using hashlib.sha256()"""
    h, length = hash_file(path, blocksize)
    digest = "sha256=" + urlsafe_b64encode(h.digest()).decode("latin1").rstrip("=")
    return (digest, str(length))


def csv_io_kwargs(mode: str) -> Dict[str, Any]:
    """Return keyword arguments to properly open a CSV file
    in the given mode.
    """
    return {"mode": mode, "newline": "", "encoding": "utf-8"}


def fix_script(path: str) -> bool:
    """Replace #!python with #!/path/to/python
    Return True if file was changed.
    """
    # XXX RECORD hashes will need to be updated
    assert os.path.isfile(path)

    with open(path, "rb") as script:
        firstline = script.readline()
        if not firstline.startswith(b"#!python"):
            return False
        exename = sys.executable.encode(sys.getfilesystemencoding())
        firstline = b"#!" + exename + os.linesep.encode("ascii")
        rest = script.read()
    with open(path, "wb") as script:
        script.write(firstline)
        script.write(rest)
    return True


def wheel_root_is_purelib(metadata: Message) -> bool:
    return metadata.get("Root-Is-Purelib", "").lower() == "true"


def get_entrypoints(dist: BaseDistribution) -> Tuple[Dict[str, str], Dict[str, str]]:
    console_scripts = {}
    gui_scripts = {}
    for entry_point in dist.iter_entry_points():
        if entry_point.group == "console_scripts":
            console_scripts[entry_point.name] = entry_point.value
        elif entry_point.group == "gui_scripts":
            gui_scripts[entry_point.name] = entry_point.value
    return console_scripts, gui_scripts


def message_about_scripts_not_on_PATH(scripts: Sequence[str]) -> Optional[str]:
    """Determine if any scripts are not on PATH and format a warning.
    Returns a warning message if one or more scripts are not on PATH,
    otherwise None.
    """
    if not scripts:
        return None

    # Group scripts by the path they were installed in
    grouped_by_dir: Dict[str, Set[str]] = collections.defaultdict(set)
    for destfile in scripts:
        parent_dir = os.path.dirname(destfile)
        script_name = os.path.basename(destfile)
        grouped_by_dir[parent_dir].add(script_name)

    # We don't want to warn for directories that are on PATH.
    not_warn_dirs = [
        os.path.normcase(os.path.normpath(i)).rstrip(os.sep)
        for i in os.environ.get("PATH", "").split(os.pathsep)
    ]
    # If an executable sits with sys.executable, we don't warn for it.
    #     This covers the case of venv invocations without activating the venv.
    not_warn_dirs.append(
        os.path.normcase(os.path.normpath(os.path.dirname(sys.executable)))
    )
    warn_for: Dict[str, Set[str]] = {
        parent_dir: scripts
        for parent_dir, scripts in grouped_by_dir.items()
        if os.path.normcase(os.path.normpath(parent_dir)) not in not_warn_dirs
    }
    if not warn_for:
        return None

    # Format a message
    msg_lines = []
    for parent_dir, dir_scripts in warn_for.items():
        sorted_scripts: List[str] = sorted(dir_scripts)
        if len(sorted_scripts) == 1:
            start_text = f"script {sorted_scripts[0]} is"
        else:
            start_text = "scripts {} are".format(
                ", ".join(sorted_scripts[:-1]) + " and " + sorted_scripts[-1]
            )

        msg_lines.append(
            f"The {start_text} installed in '{parent_dir}' which is not on PATH."
        )

    last_line_fmt = (
        "Consider adding {} to PATH or, if you prefer "
        "to suppress this warning, use --no-warn-script-location."
    )
    if len(msg_lines) == 1:
        msg_lines.append(last_line_fmt.format("this directory"))
    else:
        msg_lines.append(last_line_fmt.format("these directories"))

    # Add a note if any directory starts with ~
    warn_for_tilde = any(
        i[0] == "~" for i in os.environ.get("PATH", "").split(os.pathsep) if i
    )
    if warn_for_tilde:
        tilde_warning_msg = (
            "NOTE: The current PATH contains path(s) starting with `~`, "
            "which may not be expanded by all applications."
        )
        msg_lines.append(tilde_warning_msg)

    # Returns the formatted multiline message
    return "\n".join(msg_lines)


def _normalized_outrows(
    outrows: Iterable[InstalledCSVRow],
) -> List[Tuple[str, str, str]]:
    """Normalize the given rows of a RECORD file.

    Items in each row are converted into str. Rows are then sorted to make
    the value more predictable for tests.

    Each row is a 3-tuple (path, hash, size) and corresponds to a record of
    a RECORD file (see PEP 376 and PEP 427 for details).  For the rows
    passed to this function, the size can be an integer as an int or string,
    or the empty string.
    """
    # Normally, there should only be one row per path, in which case the
    # second and third elements don't come into play when sorting.
    # However, in cases in the wild where a path might happen to occur twice,
    # we don't want the sort operation to trigger an error (but still want
    # determinism).  Since the third element can be an int or string, we
    # coerce each element to a string to avoid a TypeError in this case.
    # For additional background, see--
    # https://github.com/pypa/pip/issues/5868
    return sorted(
        (record_path, hash_, str(size)) for record_path, hash_, size in outrows
    )


def _record_to_fs_path(record_path: RecordPath, lib_dir: str) -> str:
    return os.path.join(lib_dir, record_path)


def _fs_to_record_path(path: str, lib_dir: str) -> RecordPath:
    # On Windows, do not handle relative paths if they belong to different
    # logical disks
    if os.path.splitdrive(path)[0].lower() == os.path.splitdrive(lib_dir)[0].lower():
        path = os.path.relpath(path, lib_dir)

    path = path.replace(os.path.sep, "/")
    return cast("RecordPath", path)


def get_csv_rows_for_installed(
    old_csv_rows: List[List[str]],
    installed: Dict[RecordPath, RecordPath],
    changed: Set[RecordPath],
    generated: List[str],
    lib_dir: str,
) -> List[InstalledCSVRow]:
    """
    :param installed: A map from archive RECORD path to installation RECORD
        path.
    """
    installed_rows: List[InstalledCSVRow] = []
    for row in old_csv_rows:
        if len(row) > 3:
            logger.warning("RECORD line has more than three elements: %s", row)
        old_record_path = cast("RecordPath", row[0])
        new_record_path = installed.pop(old_record_path, old_record_path)
        if new_record_path in changed:
            digest, length = rehash(_record_to_fs_path(new_record_path, lib_dir))
        else:
            digest = row[1] if len(row) > 1 else ""
            length = row[2] if len(row) > 2 else ""
        installed_rows.append((new_record_path, digest, length))
    for f in generated:
        path = _fs_to_record_path(f, lib_dir)
        digest, length = rehash(f)
        installed_rows.append((path, digest, length))
    return installed_rows + [
        (installed_record_path, "", "") for installed_record_path in installed.values()
    ]


def get_console_script_specs(console: Dict[str, str]) -> List[str]:
    """
    Given the mapping from entrypoint name to callable, return the relevant
    console script specs.
    """
    # Don't mutate caller's version
    console = console.copy()

    scripts_to_generate = []

    # Special case pip and setuptools to generate versioned wrappers
    #
    # The issue is that some projects (specifically, pip and setuptools) use
    # code in setup.py to create "versioned" entry points - pip2.7 on Python
    # 2.7, pip3.3 on Python 3.3, etc. But these entry points are baked into
    # the wheel metadata at build time, and so if the wheel is installed with
    # a *different* version of Python the entry points will be wrong. The
    # correct fix for this is to enhance the metadata to be able to describe
    # such versioned entry points.
    # Currently, projects using versioned entry points will either have
    # incorrect versioned entry points, or they will not be able to distribute
    # "universal" wheels (i.e., they will need a wheel per Python version).
    #
    # Because setuptools and pip are bundled with _ensurepip and virtualenv,
    # we need to use universal wheels. As a workaround, we
    # override the versioned entry points in the wheel and generate the
    # correct ones.
    #
    # To add the level of hack in this section of code, in order to support
    # ensurepip this code will look for an ``ENSUREPIP_OPTIONS`` environment
    # variable which will control which version scripts get installed.
    #
    # ENSUREPIP_OPTIONS=altinstall
    #   - Only pipX.Y and easy_install-X.Y will be generated and installed
    # ENSUREPIP_OPTIONS=install
    #   - pipX.Y, pipX, easy_install-X.Y will be generated and installed. Note
    #     that this option is technically if ENSUREPIP_OPTIONS is set and is
    #     not altinstall
    # DEFAULT
    #   - The default behavior is to install pip, pipX, pipX.Y, easy_install
    #     and easy_install-X.Y.
    pip_script = console.pop("pip", None)
    if pip_script:
        if "ENSUREPIP_OPTIONS" not in os.environ:
            scripts_to_generate.append("pip = " + pip_script)

        if os.environ.get("ENSUREPIP_OPTIONS", "") != "altinstall":
            scripts_to_generate.append(f"pip{sys.version_info[0]} = {pip_script}")

        scripts_to_generate.append(f"pip{get_major_minor_version()} = {pip_script}")
        # Delete any other versioned pip entry points
        pip_ep = [k for k in console if re.match(r"pip(\d+(\.\d+)?)?$", k)]
        for k in pip_ep:
            del console[k]
    easy_install_script = console.pop("easy_install", None)
    if easy_install_script:
        if "ENSUREPIP_OPTIONS" not in os.environ:
            scripts_to_generate.append("easy_install = " + easy_install_script)

        scripts_to_generate.append(
            f"easy_install-{get_major_minor_version()} = {easy_install_script}"
        )
        # Delete any other versioned easy_install entry points
        easy_install_ep = [
            k for k in console if re.match(r"easy_install(-\d+\.\d+)?$", k)
        ]
        for k in easy_install_ep:
            del console[k]

    # Generate the console entry points specified in the wheel
    scripts_to_generate.extend(starmap("{} = {}".format, console.items()))

    return scripts_to_generate


class ZipBackedFile:
    def __init__(
        self, src_record_path: RecordPath, dest_path: str, zip_file: ZipFile
    ) -> None:
        self.src_record_path = src_record_path
        self.dest_path = dest_path
        self._zip_file = zip_file
        self.changed = False

    def _getinfo(self) -> ZipInfo:
        return self._zip_file.getinfo(self.src_record_path)

    def save(self) -> None:
        # When we open the output file below, any existing file is truncated
        # before we start writing the new contents. This is fine in most
        # cases, but can cause a segfault if pip has loaded a shared
        # object (e.g. from pyopenssl through its vendored urllib3)
        # Since the shared object is mmap'd an attempt to call a
        # symbol in it will then cause a segfault. Unlinking the file
        # allows writing of new contents while allowing the process to
        # continue to use the old copy.
        if os.path.exists(self.dest_path):
            os.unlink(self.dest_path)

        zipinfo = self._getinfo()

        # optimization: the file is created by open(),
        # skip the decompression when there is 0 bytes to decompress.
        with open(self.dest_path, "wb") as dest:
            if zipinfo.file_size > 0:
                with self._zip_file.open(zipinfo) as f:
                    blocksize = min(zipinfo.file_size, 1024 * 1024)
                    shutil.copyfileobj(f, dest, blocksize)

        if zip_item_is_executable(zipinfo):
            set_extracted_file_to_default_mode_plus_executable(self.dest_path)


class ScriptFile:
    def __init__(self, file: "File") -> None:
        self._file = file
        self.src_record_path = self._file.src_record_path
        self.dest_path = self._file.dest_path
        self.changed = False

    def save(self) -> None:
        self._file.save()
        self.changed = fix_script(self.dest_path)


class MissingCallableSuffix(InstallationError):
    def __init__(self, entry_point: str) -> None:
        super().__init__(
            f"Invalid script entry point: {entry_point} - A callable "
            "suffix is required. Cf https://packaging.python.org/"
            "specifications/entry-points/#use-for-scripts for more "
            "information."
        )


def _raise_for_invalid_entrypoint(specification: str) -> None:
    entry = get_export_entry(specification)
    if entry is not None and entry.suffix is None:
        raise MissingCallableSuffix(str(entry))


class PipScriptMaker(ScriptMaker):
    def make(
        self, specification: str, options: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        _raise_for_invalid_entrypoint(specification)
        return super().make(specification, options)


def _install_wheel(  # noqa: C901, PLR0915 function is too long
    name: str,
    wheel_zip: ZipFile,
    wheel_path: str,
    scheme: Scheme,
    pycompile: bool = True,
    warn_script_location: bool = True,
    direct_url: Optional[DirectUrl] = None,
    requested: bool = False,
) -> None:
    """Install a wheel.

    :param name: Name of the project to install
    :param wheel_zip: open ZipFile for wheel being installed
    :param scheme: Distutils scheme dictating the install directories
    :param req_description: String used in place of the requirement, for
        logging
    :param pycompile: Whether to byte-compile installed Python files
    :param warn_script_location: Whether to check that scripts are installed
        into a directory on PATH
    :raises UnsupportedWheel:
        * when the directory holds an unpacked wheel with incompatible
          Wheel-Version
        * when the .dist-info dir does not match the wheel
    """
    info_dir, metadata = parse_wheel(wheel_zip, name)

    if wheel_root_is_purelib(metadata):
        lib_dir = scheme.purelib
    else:
        lib_dir = scheme.platlib

    # Record details of the files moved
    #   installed = files copied from the wheel to the destination
    #   changed = files changed while installing (scripts #! line typically)
    #   generated = files newly generated during the install (script wrappers)
    installed: Dict[RecordPath, RecordPath] = {}
    changed: Set[RecordPath] = set()
    generated: List[str] = []

    def record_installed(
        srcfile: RecordPath, destfile: str, modified: bool = False
    ) -> None:
        """Map archive RECORD paths to installation RECORD paths."""
        newpath = _fs_to_record_path(destfile, lib_dir)
        installed[srcfile] = newpath
        if modified:
            changed.add(newpath)

    def is_dir_path(path: RecordPath) -> bool:
        return path.endswith("/")

    def assert_no_path_traversal(dest_dir_path: str, target_path: str) -> None:
        if not is_within_directory(dest_dir_path, target_path):
            message = (
                "The wheel {!r} has a file {!r} trying to install"
                " outside the target directory {!r}"
            )
            raise InstallationError(
                message.format(wheel_path, target_path, dest_dir_path)
            )

    def root_scheme_file_maker(
        zip_file: ZipFile, dest: str
    ) -> Callable[[RecordPath], "File"]:
        def make_root_scheme_file(record_path: RecordPath) -> "File":
            normed_path = os.path.normpath(record_path)
            dest_path = os.path.join(dest, normed_path)
            assert_no_path_traversal(dest, dest_path)
            return ZipBackedFile(record_path, dest_path, zip_file)

        return make_root_scheme_file

    def data_scheme_file_maker(
        zip_file: ZipFile, scheme: Scheme
    ) -> Callable[[RecordPath], "File"]:
        scheme_paths = {key: getattr(scheme, key) for key in SCHEME_KEYS}

        def make_data_scheme_file(record_path: RecordPath) -> "File":
            normed_path = os.path.normpath(record_path)
            try:
                _, scheme_key, dest_subpath = normed_path.split(os.path.sep, 2)
            except ValueError:
                message = (
                    f"Unexpected file in {wheel_path}: {record_path!r}. .data directory"
                    " contents should be named like: '<scheme key>/<path>'."
                )
                raise InstallationError(message)

            try:
                scheme_path = scheme_paths[scheme_key]
            except KeyError:
                valid_scheme_keys = ", ".join(sorted(scheme_paths))
                message = (
                    f"Unknown scheme key used in {wheel_path}: {scheme_key} "
                    f"(for file {record_path!r}). .data directory contents "
                    f"should be in subdirectories named with a valid scheme "
                    f"key ({valid_scheme_keys})"
                )
                raise InstallationError(message)

            dest_path = os.path.join(scheme_path, dest_subpath)
            assert_no_path_traversal(scheme_path, dest_path)
            return ZipBackedFile(record_path, dest_path, zip_file)

        return make_data_scheme_file

    def is_data_scheme_path(path: RecordPath) -> bool:
        return path.split("/", 1)[0].endswith(".data")

    paths = cast(List[RecordPath], wheel_zip.namelist())
    file_paths = filterfalse(is_dir_path, paths)
    root_scheme_paths, data_scheme_paths = partition(is_data_scheme_path, file_paths)

    make_root_scheme_file = root_scheme_file_maker(wheel_zip, lib_dir)
    files: Iterator[File] = map(make_root_scheme_file, root_scheme_paths)

    def is_script_scheme_path(path: RecordPath) -> bool:
        parts = path.split("/", 2)
        return len(parts) > 2 and parts[0].endswith(".data") and parts[1] == "scripts"

    other_scheme_paths, script_scheme_paths = partition(
        is_script_scheme_path, data_scheme_paths
    )

    make_data_scheme_file = data_scheme_file_maker(wheel_zip, scheme)
    other_scheme_files = map(make_data_scheme_file, other_scheme_paths)
    files = chain(files, other_scheme_files)

    # Get the defined entry points
    distribution = get_wheel_distribution(
        FilesystemWheel(wheel_path),
        canonicalize_name(name),
    )
    console, gui = get_entrypoints(distribution)

    def is_entrypoint_wrapper(file: "File") -> bool:
        # EP, EP.exe and EP-script.py are scripts generated for
        # entry point EP by setuptools
        path = file.dest_path
        name = os.path.basename(path)
        if name.lower().endswith(".exe"):
            matchname = name[:-4]
        elif name.lower().endswith("-script.py"):
            matchname = name[:-10]
        elif name.lower().endswith(".pya"):
            matchname = name[:-4]
        else:
            matchname = name
        # Ignore setuptools-generated scripts
        return matchname in console or matchname in gui

    script_scheme_files: Iterator[File] = map(
        make_data_scheme_file, script_scheme_paths
    )
    script_scheme_files = filterfalse(is_entrypoint_wrapper, script_scheme_files)
    script_scheme_files = map(ScriptFile, script_scheme_files)
    files = chain(files, script_scheme_files)

    existing_parents = set()
    for file in files:
        # directory creation is lazy and after file filtering
        # to ensure we don't install empty dirs; empty dirs can't be
        # uninstalled.
        parent_dir = os.path.dirname(file.dest_path)
        if parent_dir not in existing_parents:
            ensure_dir(parent_dir)
            existing_parents.add(parent_dir)
        file.save()
        record_installed(file.src_record_path, file.dest_path, file.changed)

    def pyc_source_file_paths() -> Generator[str, None, None]:
        # We de-duplicate installation paths, since there can be overlap (e.g.
        # file in .data maps to same location as file in wheel root).
        # Sorting installation paths makes it easier to reproduce and debug
        # issues related to permissions on existing files.
        for installed_path in sorted(set(installed.values())):
            full_installed_path = os.path.join(lib_dir, installed_path)
            if not os.path.isfile(full_installed_path):
                continue
            if not full_installed_path.endswith(".py"):
                continue
            yield full_installed_path

    def pyc_output_path(path: str) -> str:
        """Return the path the pyc file would have been written to."""
        return importlib.util.cache_from_source(path)

    # Compile all of the pyc files for the installed files
    if pycompile:
        with contextlib.redirect_stdout(
            StreamWrapper.from_stream(sys.stdout)
        ) as stdout:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                for path in pyc_source_file_paths():
                    success = compileall.compile_file(path, force=True, quiet=True)
                    if success:
                        pyc_path = pyc_output_path(path)
                        assert os.path.exists(pyc_path)
                        pyc_record_path = cast(
                            "RecordPath", pyc_path.replace(os.path.sep, "/")
                        )
                        record_installed(pyc_record_path, pyc_path)
        logger.debug(stdout.getvalue())

    maker = PipScriptMaker(None, scheme.scripts)

    # Ensure old scripts are overwritten.
    # See https://github.com/pypa/pip/issues/1800
    maker.clobber = True

    # Ensure we don't generate any variants for scripts because this is almost
    # never what somebody wants.
    # See https://bitbucket.org/pypa/distlib/issue/35/
    maker.variants = {""}

    # This is required because otherwise distlib creates scripts that are not
    # executable.
    # See https://bitbucket.org/pypa/distlib/issue/32/
    maker.set_mode = True

    # Generate the console and GUI entry points specified in the wheel
    scripts_to_generate = get_console_script_specs(console)

    gui_scripts_to_generate = list(starmap("{} = {}".format, gui.items()))

    generated_console_scripts = maker.make_multiple(scripts_to_generate)
    generated.extend(generated_console_scripts)

    generated.extend(maker.make_multiple(gui_scripts_to_generate, {"gui": True}))

    if warn_script_location:
        msg = message_about_scripts_not_on_PATH(generated_console_scripts)
        if msg is not None:
            logger.warning(msg)

    generated_file_mode = 0o666 & ~current_umask()

    @contextlib.contextmanager
    def _generate_file(path: str, **kwargs: Any) -> Generator[BinaryIO, None, None]:
        with adjacent_tmp_file(path, **kwargs) as f:
            yield f
        os.chmod(f.name, generated_file_mode)
        replace(f.name, path)

    dest_info_dir = os.path.join(lib_dir, info_dir)

    # Record pip as the installer
    installer_path = os.path.join(dest_info_dir, "INSTALLER")
    with _generate_file(installer_path) as installer_file:
        installer_file.write(b"pip\n")
    generated.append(installer_path)

    # Record the PEP 610 direct URL reference
    if direct_url is not None:
        direct_url_path = os.path.join(dest_info_dir, DIRECT_URL_METADATA_NAME)
        with _generate_file(direct_url_path) as direct_url_file:
            direct_url_file.write(direct_url.to_json().encode("utf-8"))
        generated.append(direct_url_path)

    # Record the REQUESTED file
    if requested:
        requested_path = os.path.join(dest_info_dir, "REQUESTED")
        with open(requested_path, "wb"):
            pass
        generated.append(requested_path)

    record_text = distribution.read_text("RECORD")
    record_rows = list(csv.reader(record_text.splitlines()))

    rows = get_csv_rows_for_installed(
        record_rows,
        installed=installed,
        changed=changed,
        generated=generated,
        lib_dir=lib_dir,
    )

    # Record details of all files installed
    record_path = os.path.join(dest_info_dir, "RECORD")

    with _generate_file(record_path, **csv_io_kwargs("w")) as record_file:
        # Explicitly cast to typing.IO[str] as a workaround for the mypy error:
        # "writer" has incompatible type "BinaryIO"; expected "_Writer"
        writer = csv.writer(cast("IO[str]", record_file))
        writer.writerows(_normalized_outrows(rows))


@contextlib.contextmanager
def req_error_context(req_description: str) -> Generator[None, None, None]:
    try:
        yield
    except InstallationError as e:
        message = f"For req: {req_description}. {e.args[0]}"
        raise InstallationError(message) from e


def install_wheel(
    name: str,
    wheel_path: str,
    scheme: Scheme,
    req_description: str,
    pycompile: bool = True,
    warn_script_location: bool = True,
    direct_url: Optional[DirectUrl] = None,
    requested: bool = False,
) -> None:
    with ZipFile(wheel_path, allowZip64=True) as z:
        with req_error_context(req_description):
            _install_wheel(
                name=name,
                wheel_zip=z,
                wheel_path=wheel_path,
                scheme=scheme,
                pycompile=pycompile,
                warn_script_location=warn_script_location,
                direct_url=direct_url,
                requested=requested,
            )

# === NexusCore/openenv\Lib\site-packages\pip\_internal\operations\install\wheel.py ===
"""Support for installing and building the "wheel" binary package format.
"""

import collections
import compileall
import contextlib
import csv
import importlib
import logging
import os.path
import re
import shutil
import sys
import warnings
from base64 import urlsafe_b64encode
from email.message import Message
from itertools import chain, filterfalse, starmap
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Callable,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    NewType,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    Union,
    cast,
)
from zipfile import ZipFile, ZipInfo

from pip._vendor.distlib.scripts import ScriptMaker
from pip._vendor.distlib.util import get_export_entry
from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.exceptions import InstallationError
from pip._internal.locations import get_major_minor_version
from pip._internal.metadata import (
    BaseDistribution,
    FilesystemWheel,
    get_wheel_distribution,
)
from pip._internal.models.direct_url import DIRECT_URL_METADATA_NAME, DirectUrl
from pip._internal.models.scheme import SCHEME_KEYS, Scheme
from pip._internal.utils.filesystem import adjacent_tmp_file, replace
from pip._internal.utils.misc import StreamWrapper, ensure_dir, hash_file, partition
from pip._internal.utils.unpacking import (
    current_umask,
    is_within_directory,
    set_extracted_file_to_default_mode_plus_executable,
    zip_item_is_executable,
)
from pip._internal.utils.wheel import parse_wheel

if TYPE_CHECKING:

    class File(Protocol):
        src_record_path: "RecordPath"
        dest_path: str
        changed: bool

        def save(self) -> None:
            pass


logger = logging.getLogger(__name__)

RecordPath = NewType("RecordPath", str)
InstalledCSVRow = Tuple[RecordPath, str, Union[int, str]]


def rehash(path: str, blocksize: int = 1 << 20) -> Tuple[str, str]:
    """Return (encoded_digest, length) for path using hashlib.sha256()"""
    h, length = hash_file(path, blocksize)
    digest = "sha256=" + urlsafe_b64encode(h.digest()).decode("latin1").rstrip("=")
    return (digest, str(length))


def csv_io_kwargs(mode: str) -> Dict[str, Any]:
    """Return keyword arguments to properly open a CSV file
    in the given mode.
    """
    return {"mode": mode, "newline": "", "encoding": "utf-8"}


def fix_script(path: str) -> bool:
    """Replace #!python with #!/path/to/python
    Return True if file was changed.
    """
    # XXX RECORD hashes will need to be updated
    assert os.path.isfile(path)

    with open(path, "rb") as script:
        firstline = script.readline()
        if not firstline.startswith(b"#!python"):
            return False
        exename = sys.executable.encode(sys.getfilesystemencoding())
        firstline = b"#!" + exename + os.linesep.encode("ascii")
        rest = script.read()
    with open(path, "wb") as script:
        script.write(firstline)
        script.write(rest)
    return True


def wheel_root_is_purelib(metadata: Message) -> bool:
    return metadata.get("Root-Is-Purelib", "").lower() == "true"


def get_entrypoints(dist: BaseDistribution) -> Tuple[Dict[str, str], Dict[str, str]]:
    console_scripts = {}
    gui_scripts = {}
    for entry_point in dist.iter_entry_points():
        if entry_point.group == "console_scripts":
            console_scripts[entry_point.name] = entry_point.value
        elif entry_point.group == "gui_scripts":
            gui_scripts[entry_point.name] = entry_point.value
    return console_scripts, gui_scripts


def message_about_scripts_not_on_PATH(scripts: Sequence[str]) -> Optional[str]:
    """Determine if any scripts are not on PATH and format a warning.
    Returns a warning message if one or more scripts are not on PATH,
    otherwise None.
    """
    if not scripts:
        return None

    # Group scripts by the path they were installed in
    grouped_by_dir: Dict[str, Set[str]] = collections.defaultdict(set)
    for destfile in scripts:
        parent_dir = os.path.dirname(destfile)
        script_name = os.path.basename(destfile)
        grouped_by_dir[parent_dir].add(script_name)

    # We don't want to warn for directories that are on PATH.
    not_warn_dirs = [
        os.path.normcase(os.path.normpath(i)).rstrip(os.sep)
        for i in os.environ.get("PATH", "").split(os.pathsep)
    ]
    # If an executable sits with sys.executable, we don't warn for it.
    #     This covers the case of venv invocations without activating the venv.
    not_warn_dirs.append(
        os.path.normcase(os.path.normpath(os.path.dirname(sys.executable)))
    )
    warn_for: Dict[str, Set[str]] = {
        parent_dir: scripts
        for parent_dir, scripts in grouped_by_dir.items()
        if os.path.normcase(os.path.normpath(parent_dir)) not in not_warn_dirs
    }
    if not warn_for:
        return None

    # Format a message
    msg_lines = []
    for parent_dir, dir_scripts in warn_for.items():
        sorted_scripts: List[str] = sorted(dir_scripts)
        if len(sorted_scripts) == 1:
            start_text = f"script {sorted_scripts[0]} is"
        else:
            start_text = "scripts {} are".format(
                ", ".join(sorted_scripts[:-1]) + " and " + sorted_scripts[-1]
            )

        msg_lines.append(
            f"The {start_text} installed in '{parent_dir}' which is not on PATH."
        )

    last_line_fmt = (
        "Consider adding {} to PATH or, if you prefer "
        "to suppress this warning, use --no-warn-script-location."
    )
    if len(msg_lines) == 1:
        msg_lines.append(last_line_fmt.format("this directory"))
    else:
        msg_lines.append(last_line_fmt.format("these directories"))

    # Add a note if any directory starts with ~
    warn_for_tilde = any(
        i[0] == "~" for i in os.environ.get("PATH", "").split(os.pathsep) if i
    )
    if warn_for_tilde:
        tilde_warning_msg = (
            "NOTE: The current PATH contains path(s) starting with `~`, "
            "which may not be expanded by all applications."
        )
        msg_lines.append(tilde_warning_msg)

    # Returns the formatted multiline message
    return "\n".join(msg_lines)


def _normalized_outrows(
    outrows: Iterable[InstalledCSVRow],
) -> List[Tuple[str, str, str]]:
    """Normalize the given rows of a RECORD file.

    Items in each row are converted into str. Rows are then sorted to make
    the value more predictable for tests.

    Each row is a 3-tuple (path, hash, size) and corresponds to a record of
    a RECORD file (see PEP 376 and PEP 427 for details).  For the rows
    passed to this function, the size can be an integer as an int or string,
    or the empty string.
    """
    # Normally, there should only be one row per path, in which case the
    # second and third elements don't come into play when sorting.
    # However, in cases in the wild where a path might happen to occur twice,
    # we don't want the sort operation to trigger an error (but still want
    # determinism).  Since the third element can be an int or string, we
    # coerce each element to a string to avoid a TypeError in this case.
    # For additional background, see--
    # https://github.com/pypa/pip/issues/5868
    return sorted(
        (record_path, hash_, str(size)) for record_path, hash_, size in outrows
    )


def _record_to_fs_path(record_path: RecordPath, lib_dir: str) -> str:
    return os.path.join(lib_dir, record_path)


def _fs_to_record_path(path: str, lib_dir: str) -> RecordPath:
    # On Windows, do not handle relative paths if they belong to different
    # logical disks
    if os.path.splitdrive(path)[0].lower() == os.path.splitdrive(lib_dir)[0].lower():
        path = os.path.relpath(path, lib_dir)

    path = path.replace(os.path.sep, "/")
    return cast("RecordPath", path)


def get_csv_rows_for_installed(
    old_csv_rows: List[List[str]],
    installed: Dict[RecordPath, RecordPath],
    changed: Set[RecordPath],
    generated: List[str],
    lib_dir: str,
) -> List[InstalledCSVRow]:
    """
    :param installed: A map from archive RECORD path to installation RECORD
        path.
    """
    installed_rows: List[InstalledCSVRow] = []
    for row in old_csv_rows:
        if len(row) > 3:
            logger.warning("RECORD line has more than three elements: %s", row)
        old_record_path = cast("RecordPath", row[0])
        new_record_path = installed.pop(old_record_path, old_record_path)
        if new_record_path in changed:
            digest, length = rehash(_record_to_fs_path(new_record_path, lib_dir))
        else:
            digest = row[1] if len(row) > 1 else ""
            length = row[2] if len(row) > 2 else ""
        installed_rows.append((new_record_path, digest, length))
    for f in generated:
        path = _fs_to_record_path(f, lib_dir)
        digest, length = rehash(f)
        installed_rows.append((path, digest, length))
    return installed_rows + [
        (installed_record_path, "", "") for installed_record_path in installed.values()
    ]


def get_console_script_specs(console: Dict[str, str]) -> List[str]:
    """
    Given the mapping from entrypoint name to callable, return the relevant
    console script specs.
    """
    # Don't mutate caller's version
    console = console.copy()

    scripts_to_generate = []

    # Special case pip and setuptools to generate versioned wrappers
    #
    # The issue is that some projects (specifically, pip and setuptools) use
    # code in setup.py to create "versioned" entry points - pip2.7 on Python
    # 2.7, pip3.3 on Python 3.3, etc. But these entry points are baked into
    # the wheel metadata at build time, and so if the wheel is installed with
    # a *different* version of Python the entry points will be wrong. The
    # correct fix for this is to enhance the metadata to be able to describe
    # such versioned entry points.
    # Currently, projects using versioned entry points will either have
    # incorrect versioned entry points, or they will not be able to distribute
    # "universal" wheels (i.e., they will need a wheel per Python version).
    #
    # Because setuptools and pip are bundled with _ensurepip and virtualenv,
    # we need to use universal wheels. As a workaround, we
    # override the versioned entry points in the wheel and generate the
    # correct ones.
    #
    # To add the level of hack in this section of code, in order to support
    # ensurepip this code will look for an ``ENSUREPIP_OPTIONS`` environment
    # variable which will control which version scripts get installed.
    #
    # ENSUREPIP_OPTIONS=altinstall
    #   - Only pipX.Y and easy_install-X.Y will be generated and installed
    # ENSUREPIP_OPTIONS=install
    #   - pipX.Y, pipX, easy_install-X.Y will be generated and installed. Note
    #     that this option is technically if ENSUREPIP_OPTIONS is set and is
    #     not altinstall
    # DEFAULT
    #   - The default behavior is to install pip, pipX, pipX.Y, easy_install
    #     and easy_install-X.Y.
    pip_script = console.pop("pip", None)
    if pip_script:
        if "ENSUREPIP_OPTIONS" not in os.environ:
            scripts_to_generate.append("pip = " + pip_script)

        if os.environ.get("ENSUREPIP_OPTIONS", "") != "altinstall":
            scripts_to_generate.append(f"pip{sys.version_info[0]} = {pip_script}")

        scripts_to_generate.append(f"pip{get_major_minor_version()} = {pip_script}")
        # Delete any other versioned pip entry points
        pip_ep = [k for k in console if re.match(r"pip(\d+(\.\d+)?)?$", k)]
        for k in pip_ep:
            del console[k]
    easy_install_script = console.pop("easy_install", None)
    if easy_install_script:
        if "ENSUREPIP_OPTIONS" not in os.environ:
            scripts_to_generate.append("easy_install = " + easy_install_script)

        scripts_to_generate.append(
            f"easy_install-{get_major_minor_version()} = {easy_install_script}"
        )
        # Delete any other versioned easy_install entry points
        easy_install_ep = [
            k for k in console if re.match(r"easy_install(-\d+\.\d+)?$", k)
        ]
        for k in easy_install_ep:
            del console[k]

    # Generate the console entry points specified in the wheel
    scripts_to_generate.extend(starmap("{} = {}".format, console.items()))

    return scripts_to_generate


class ZipBackedFile:
    def __init__(
        self, src_record_path: RecordPath, dest_path: str, zip_file: ZipFile
    ) -> None:
        self.src_record_path = src_record_path
        self.dest_path = dest_path
        self._zip_file = zip_file
        self.changed = False

    def _getinfo(self) -> ZipInfo:
        return self._zip_file.getinfo(self.src_record_path)

    def save(self) -> None:
        # When we open the output file below, any existing file is truncated
        # before we start writing the new contents. This is fine in most
        # cases, but can cause a segfault if pip has loaded a shared
        # object (e.g. from pyopenssl through its vendored urllib3)
        # Since the shared object is mmap'd an attempt to call a
        # symbol in it will then cause a segfault. Unlinking the file
        # allows writing of new contents while allowing the process to
        # continue to use the old copy.
        if os.path.exists(self.dest_path):
            os.unlink(self.dest_path)

        zipinfo = self._getinfo()

        # optimization: the file is created by open(),
        # skip the decompression when there is 0 bytes to decompress.
        with open(self.dest_path, "wb") as dest:
            if zipinfo.file_size > 0:
                with self._zip_file.open(zipinfo) as f:
                    blocksize = min(zipinfo.file_size, 1024 * 1024)
                    shutil.copyfileobj(f, dest, blocksize)

        if zip_item_is_executable(zipinfo):
            set_extracted_file_to_default_mode_plus_executable(self.dest_path)


class ScriptFile:
    def __init__(self, file: "File") -> None:
        self._file = file
        self.src_record_path = self._file.src_record_path
        self.dest_path = self._file.dest_path
        self.changed = False

    def save(self) -> None:
        self._file.save()
        self.changed = fix_script(self.dest_path)


class MissingCallableSuffix(InstallationError):
    def __init__(self, entry_point: str) -> None:
        super().__init__(
            f"Invalid script entry point: {entry_point} - A callable "
            "suffix is required. Cf https://packaging.python.org/"
            "specifications/entry-points/#use-for-scripts for more "
            "information."
        )


def _raise_for_invalid_entrypoint(specification: str) -> None:
    entry = get_export_entry(specification)
    if entry is not None and entry.suffix is None:
        raise MissingCallableSuffix(str(entry))


class PipScriptMaker(ScriptMaker):
    def make(
        self, specification: str, options: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        _raise_for_invalid_entrypoint(specification)
        return super().make(specification, options)


def _install_wheel(  # noqa: C901, PLR0915 function is too long
    name: str,
    wheel_zip: ZipFile,
    wheel_path: str,
    scheme: Scheme,
    pycompile: bool = True,
    warn_script_location: bool = True,
    direct_url: Optional[DirectUrl] = None,
    requested: bool = False,
) -> None:
    """Install a wheel.

    :param name: Name of the project to install
    :param wheel_zip: open ZipFile for wheel being installed
    :param scheme: Distutils scheme dictating the install directories
    :param req_description: String used in place of the requirement, for
        logging
    :param pycompile: Whether to byte-compile installed Python files
    :param warn_script_location: Whether to check that scripts are installed
        into a directory on PATH
    :raises UnsupportedWheel:
        * when the directory holds an unpacked wheel with incompatible
          Wheel-Version
        * when the .dist-info dir does not match the wheel
    """
    info_dir, metadata = parse_wheel(wheel_zip, name)

    if wheel_root_is_purelib(metadata):
        lib_dir = scheme.purelib
    else:
        lib_dir = scheme.platlib

    # Record details of the files moved
    #   installed = files copied from the wheel to the destination
    #   changed = files changed while installing (scripts #! line typically)
    #   generated = files newly generated during the install (script wrappers)
    installed: Dict[RecordPath, RecordPath] = {}
    changed: Set[RecordPath] = set()
    generated: List[str] = []

    def record_installed(
        srcfile: RecordPath, destfile: str, modified: bool = False
    ) -> None:
        """Map archive RECORD paths to installation RECORD paths."""
        newpath = _fs_to_record_path(destfile, lib_dir)
        installed[srcfile] = newpath
        if modified:
            changed.add(newpath)

    def is_dir_path(path: RecordPath) -> bool:
        return path.endswith("/")

    def assert_no_path_traversal(dest_dir_path: str, target_path: str) -> None:
        if not is_within_directory(dest_dir_path, target_path):
            message = (
                "The wheel {!r} has a file {!r} trying to install"
                " outside the target directory {!r}"
            )
            raise InstallationError(
                message.format(wheel_path, target_path, dest_dir_path)
            )

    def root_scheme_file_maker(
        zip_file: ZipFile, dest: str
    ) -> Callable[[RecordPath], "File"]:
        def make_root_scheme_file(record_path: RecordPath) -> "File":
            normed_path = os.path.normpath(record_path)
            dest_path = os.path.join(dest, normed_path)
            assert_no_path_traversal(dest, dest_path)
            return ZipBackedFile(record_path, dest_path, zip_file)

        return make_root_scheme_file

    def data_scheme_file_maker(
        zip_file: ZipFile, scheme: Scheme
    ) -> Callable[[RecordPath], "File"]:
        scheme_paths = {key: getattr(scheme, key) for key in SCHEME_KEYS}

        def make_data_scheme_file(record_path: RecordPath) -> "File":
            normed_path = os.path.normpath(record_path)
            try:
                _, scheme_key, dest_subpath = normed_path.split(os.path.sep, 2)
            except ValueError:
                message = (
                    f"Unexpected file in {wheel_path}: {record_path!r}. .data directory"
                    " contents should be named like: '<scheme key>/<path>'."
                )
                raise InstallationError(message)

            try:
                scheme_path = scheme_paths[scheme_key]
            except KeyError:
                valid_scheme_keys = ", ".join(sorted(scheme_paths))
                message = (
                    f"Unknown scheme key used in {wheel_path}: {scheme_key} "
                    f"(for file {record_path!r}). .data directory contents "
                    f"should be in subdirectories named with a valid scheme "
                    f"key ({valid_scheme_keys})"
                )
                raise InstallationError(message)

            dest_path = os.path.join(scheme_path, dest_subpath)
            assert_no_path_traversal(scheme_path, dest_path)
            return ZipBackedFile(record_path, dest_path, zip_file)

        return make_data_scheme_file

    def is_data_scheme_path(path: RecordPath) -> bool:
        return path.split("/", 1)[0].endswith(".data")

    paths = cast(List[RecordPath], wheel_zip.namelist())
    file_paths = filterfalse(is_dir_path, paths)
    root_scheme_paths, data_scheme_paths = partition(is_data_scheme_path, file_paths)

    make_root_scheme_file = root_scheme_file_maker(wheel_zip, lib_dir)
    files: Iterator[File] = map(make_root_scheme_file, root_scheme_paths)

    def is_script_scheme_path(path: RecordPath) -> bool:
        parts = path.split("/", 2)
        return len(parts) > 2 and parts[0].endswith(".data") and parts[1] == "scripts"

    other_scheme_paths, script_scheme_paths = partition(
        is_script_scheme_path, data_scheme_paths
    )

    make_data_scheme_file = data_scheme_file_maker(wheel_zip, scheme)
    other_scheme_files = map(make_data_scheme_file, other_scheme_paths)
    files = chain(files, other_scheme_files)

    # Get the defined entry points
    distribution = get_wheel_distribution(
        FilesystemWheel(wheel_path),
        canonicalize_name(name),
    )
    console, gui = get_entrypoints(distribution)

    def is_entrypoint_wrapper(file: "File") -> bool:
        # EP, EP.exe and EP-script.py are scripts generated for
        # entry point EP by setuptools
        path = file.dest_path
        name = os.path.basename(path)
        if name.lower().endswith(".exe"):
            matchname = name[:-4]
        elif name.lower().endswith("-script.py"):
            matchname = name[:-10]
        elif name.lower().endswith(".pya"):
            matchname = name[:-4]
        else:
            matchname = name
        # Ignore setuptools-generated scripts
        return matchname in console or matchname in gui

    script_scheme_files: Iterator[File] = map(
        make_data_scheme_file, script_scheme_paths
    )
    script_scheme_files = filterfalse(is_entrypoint_wrapper, script_scheme_files)
    script_scheme_files = map(ScriptFile, script_scheme_files)
    files = chain(files, script_scheme_files)

    existing_parents = set()
    for file in files:
        # directory creation is lazy and after file filtering
        # to ensure we don't install empty dirs; empty dirs can't be
        # uninstalled.
        parent_dir = os.path.dirname(file.dest_path)
        if parent_dir not in existing_parents:
            ensure_dir(parent_dir)
            existing_parents.add(parent_dir)
        file.save()
        record_installed(file.src_record_path, file.dest_path, file.changed)

    def pyc_source_file_paths() -> Generator[str, None, None]:
        # We de-duplicate installation paths, since there can be overlap (e.g.
        # file in .data maps to same location as file in wheel root).
        # Sorting installation paths makes it easier to reproduce and debug
        # issues related to permissions on existing files.
        for installed_path in sorted(set(installed.values())):
            full_installed_path = os.path.join(lib_dir, installed_path)
            if not os.path.isfile(full_installed_path):
                continue
            if not full_installed_path.endswith(".py"):
                continue
            yield full_installed_path

    def pyc_output_path(path: str) -> str:
        """Return the path the pyc file would have been written to."""
        return importlib.util.cache_from_source(path)

    # Compile all of the pyc files for the installed files
    if pycompile:
        with contextlib.redirect_stdout(
            StreamWrapper.from_stream(sys.stdout)
        ) as stdout:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                for path in pyc_source_file_paths():
                    success = compileall.compile_file(path, force=True, quiet=True)
                    if success:
                        pyc_path = pyc_output_path(path)
                        assert os.path.exists(pyc_path)
                        pyc_record_path = cast(
                            "RecordPath", pyc_path.replace(os.path.sep, "/")
                        )
                        record_installed(pyc_record_path, pyc_path)
        logger.debug(stdout.getvalue())

    maker = PipScriptMaker(None, scheme.scripts)

    # Ensure old scripts are overwritten.
    # See https://github.com/pypa/pip/issues/1800
    maker.clobber = True

    # Ensure we don't generate any variants for scripts because this is almost
    # never what somebody wants.
    # See https://bitbucket.org/pypa/distlib/issue/35/
    maker.variants = {""}

    # This is required because otherwise distlib creates scripts that are not
    # executable.
    # See https://bitbucket.org/pypa/distlib/issue/32/
    maker.set_mode = True

    # Generate the console and GUI entry points specified in the wheel
    scripts_to_generate = get_console_script_specs(console)

    gui_scripts_to_generate = list(starmap("{} = {}".format, gui.items()))

    generated_console_scripts = maker.make_multiple(scripts_to_generate)
    generated.extend(generated_console_scripts)

    generated.extend(maker.make_multiple(gui_scripts_to_generate, {"gui": True}))

    if warn_script_location:
        msg = message_about_scripts_not_on_PATH(generated_console_scripts)
        if msg is not None:
            logger.warning(msg)

    generated_file_mode = 0o666 & ~current_umask()

    @contextlib.contextmanager
    def _generate_file(path: str, **kwargs: Any) -> Generator[BinaryIO, None, None]:
        with adjacent_tmp_file(path, **kwargs) as f:
            yield f
        os.chmod(f.name, generated_file_mode)
        replace(f.name, path)

    dest_info_dir = os.path.join(lib_dir, info_dir)

    # Record pip as the installer
    installer_path = os.path.join(dest_info_dir, "INSTALLER")
    with _generate_file(installer_path) as installer_file:
        installer_file.write(b"pip\n")
    generated.append(installer_path)

    # Record the PEP 610 direct URL reference
    if direct_url is not None:
        direct_url_path = os.path.join(dest_info_dir, DIRECT_URL_METADATA_NAME)
        with _generate_file(direct_url_path) as direct_url_file:
            direct_url_file.write(direct_url.to_json().encode("utf-8"))
        generated.append(direct_url_path)

    # Record the REQUESTED file
    if requested:
        requested_path = os.path.join(dest_info_dir, "REQUESTED")
        with open(requested_path, "wb"):
            pass
        generated.append(requested_path)

    record_text = distribution.read_text("RECORD")
    record_rows = list(csv.reader(record_text.splitlines()))

    rows = get_csv_rows_for_installed(
        record_rows,
        installed=installed,
        changed=changed,
        generated=generated,
        lib_dir=lib_dir,
    )

    # Record details of all files installed
    record_path = os.path.join(dest_info_dir, "RECORD")

    with _generate_file(record_path, **csv_io_kwargs("w")) as record_file:
        # Explicitly cast to typing.IO[str] as a workaround for the mypy error:
        # "writer" has incompatible type "BinaryIO"; expected "_Writer"
        writer = csv.writer(cast("IO[str]", record_file))
        writer.writerows(_normalized_outrows(rows))


@contextlib.contextmanager
def req_error_context(req_description: str) -> Generator[None, None, None]:
    try:
        yield
    except InstallationError as e:
        message = f"For req: {req_description}. {e.args[0]}"
        raise InstallationError(message) from e


def install_wheel(
    name: str,
    wheel_path: str,
    scheme: Scheme,
    req_description: str,
    pycompile: bool = True,
    warn_script_location: bool = True,
    direct_url: Optional[DirectUrl] = None,
    requested: bool = False,
) -> None:
    with ZipFile(wheel_path, allowZip64=True) as z:
        with req_error_context(req_description):
            _install_wheel(
                name=name,
                wheel_zip=z,
                wheel_path=wheel_path,
                scheme=scheme,
                pycompile=pycompile,
                warn_script_location=warn_script_location,
                direct_url=direct_url,
                requested=requested,
            )

# === NexusCore/openenv\Lib\site-packages\fsspec\utils.py ===
from __future__ import annotations

import contextlib
import logging
import math
import os
import re
import sys
import tempfile
from functools import partial
from hashlib import md5
from importlib.metadata import version
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Iterator,
    Sequence,
    TypeVar,
)
from urllib.parse import urlsplit

if TYPE_CHECKING:
    import pathlib

    from typing_extensions import TypeGuard

    from fsspec.spec import AbstractFileSystem


DEFAULT_BLOCK_SIZE = 5 * 2**20

T = TypeVar("T")


def infer_storage_options(
    urlpath: str, inherit_storage_options: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Infer storage options from URL path and merge it with existing storage
    options.

    Parameters
    ----------
    urlpath: str or unicode
        Either local absolute file path or URL (hdfs://namenode:8020/file.csv)
    inherit_storage_options: dict (optional)
        Its contents will get merged with the inferred information from the
        given path

    Returns
    -------
    Storage options dict.

    Examples
    --------
    >>> infer_storage_options('/mnt/datasets/test.csv')  # doctest: +SKIP
    {"protocol": "file", "path", "/mnt/datasets/test.csv"}
    >>> infer_storage_options(
    ...     'hdfs://username:pwd@node:123/mnt/datasets/test.csv?q=1',
    ...     inherit_storage_options={'extra': 'value'},
    ... )  # doctest: +SKIP
    {"protocol": "hdfs", "username": "username", "password": "pwd",
    "host": "node", "port": 123, "path": "/mnt/datasets/test.csv",
    "url_query": "q=1", "extra": "value"}
    """
    # Handle Windows paths including disk name in this special case
    if (
        re.match(r"^[a-zA-Z]:[\\/]", urlpath)
        or re.match(r"^[a-zA-Z0-9]+://", urlpath) is None
    ):
        return {"protocol": "file", "path": urlpath}

    parsed_path = urlsplit(urlpath)
    protocol = parsed_path.scheme or "file"
    if parsed_path.fragment:
        path = "#".join([parsed_path.path, parsed_path.fragment])
    else:
        path = parsed_path.path
    if protocol == "file":
        # Special case parsing file protocol URL on Windows according to:
        # https://msdn.microsoft.com/en-us/library/jj710207.aspx
        windows_path = re.match(r"^/([a-zA-Z])[:|]([\\/].*)$", path)
        if windows_path:
            drive, path = windows_path.groups()
            path = f"{drive}:{path}"

    if protocol in ["http", "https"]:
        # for HTTP, we don't want to parse, as requests will anyway
        return {"protocol": protocol, "path": urlpath}

    options: dict[str, Any] = {"protocol": protocol, "path": path}

    if parsed_path.netloc:
        # Parse `hostname` from netloc manually because `parsed_path.hostname`
        # lowercases the hostname which is not always desirable (e.g. in S3):
        # https://github.com/dask/dask/issues/1417
        options["host"] = parsed_path.netloc.rsplit("@", 1)[-1].rsplit(":", 1)[0]

        if protocol in ("s3", "s3a", "gcs", "gs"):
            options["path"] = options["host"] + options["path"]
        else:
            options["host"] = options["host"]
        if parsed_path.port:
            options["port"] = parsed_path.port
        if parsed_path.username:
            options["username"] = parsed_path.username
        if parsed_path.password:
            options["password"] = parsed_path.password

    if parsed_path.query:
        options["url_query"] = parsed_path.query
    if parsed_path.fragment:
        options["url_fragment"] = parsed_path.fragment

    if inherit_storage_options:
        update_storage_options(options, inherit_storage_options)

    return options


def update_storage_options(
    options: dict[str, Any], inherited: dict[str, Any] | None = None
) -> None:
    if not inherited:
        inherited = {}
    collisions = set(options) & set(inherited)
    if collisions:
        for collision in collisions:
            if options.get(collision) != inherited.get(collision):
                raise KeyError(
                    f"Collision between inferred and specified storage "
                    f"option:\n{collision}"
                )
    options.update(inherited)


# Compression extensions registered via fsspec.compression.register_compression
compressions: dict[str, str] = {}


def infer_compression(filename: str) -> str | None:
    """Infer compression, if available, from filename.

    Infer a named compression type, if registered and available, from filename
    extension. This includes builtin (gz, bz2, zip) compressions, as well as
    optional compressions. See fsspec.compression.register_compression.
    """
    extension = os.path.splitext(filename)[-1].strip(".").lower()
    if extension in compressions:
        return compressions[extension]
    return None


def build_name_function(max_int: float) -> Callable[[int], str]:
    """Returns a function that receives a single integer
    and returns it as a string padded by enough zero characters
    to align with maximum possible integer

    >>> name_f = build_name_function(57)

    >>> name_f(7)
    '07'
    >>> name_f(31)
    '31'
    >>> build_name_function(1000)(42)
    '0042'
    >>> build_name_function(999)(42)
    '042'
    >>> build_name_function(0)(0)
    '0'
    """
    # handle corner cases max_int is 0 or exact power of 10
    max_int += 1e-8

    pad_length = int(math.ceil(math.log10(max_int)))

    def name_function(i: int) -> str:
        return str(i).zfill(pad_length)

    return name_function


def seek_delimiter(file: IO[bytes], delimiter: bytes, blocksize: int) -> bool:
    r"""Seek current file to file start, file end, or byte after delimiter seq.

    Seeks file to next chunk delimiter, where chunks are defined on file start,
    a delimiting sequence, and file end. Use file.tell() to see location afterwards.
    Note that file start is a valid split, so must be at offset > 0 to seek for
    delimiter.

    Parameters
    ----------
    file: a file
    delimiter: bytes
        a delimiter like ``b'\n'`` or message sentinel, matching file .read() type
    blocksize: int
        Number of bytes to read from the file at once.


    Returns
    -------
    Returns True if a delimiter was found, False if at file start or end.

    """

    if file.tell() == 0:
        # beginning-of-file, return without seek
        return False

    # Interface is for binary IO, with delimiter as bytes, but initialize last
    # with result of file.read to preserve compatibility with text IO.
    last: bytes | None = None
    while True:
        current = file.read(blocksize)
        if not current:
            # end-of-file without delimiter
            return False
        full = last + current if last else current
        try:
            if delimiter in full:
                i = full.index(delimiter)
                file.seek(file.tell() - (len(full) - i) + len(delimiter))
                return True
            elif len(current) < blocksize:
                # end-of-file without delimiter
                return False
        except (OSError, ValueError):
            pass
        last = full[-len(delimiter) :]


def read_block(
    f: IO[bytes],
    offset: int,
    length: int | None,
    delimiter: bytes | None = None,
    split_before: bool = False,
) -> bytes:
    """Read a block of bytes from a file

    Parameters
    ----------
    f: File
        Open file
    offset: int
        Byte offset to start read
    length: int
        Number of bytes to read, read through end of file if None
    delimiter: bytes (optional)
        Ensure reading starts and stops at delimiter bytestring
    split_before: bool (optional)
        Start/stop read *before* delimiter bytestring.


    If using the ``delimiter=`` keyword argument we ensure that the read
    starts and stops at delimiter boundaries that follow the locations
    ``offset`` and ``offset + length``.  If ``offset`` is zero then we
    start at zero, regardless of delimiter.  The bytestring returned WILL
    include the terminating delimiter string.

    Examples
    --------

    >>> from io import BytesIO  # doctest: +SKIP
    >>> f = BytesIO(b'Alice, 100\\nBob, 200\\nCharlie, 300')  # doctest: +SKIP
    >>> read_block(f, 0, 13)  # doctest: +SKIP
    b'Alice, 100\\nBo'

    >>> read_block(f, 0, 13, delimiter=b'\\n')  # doctest: +SKIP
    b'Alice, 100\\nBob, 200\\n'

    >>> read_block(f, 10, 10, delimiter=b'\\n')  # doctest: +SKIP
    b'Bob, 200\\nCharlie, 300'
    """
    if delimiter:
        f.seek(offset)
        found_start_delim = seek_delimiter(f, delimiter, 2**16)
        if length is None:
            return f.read()
        start = f.tell()
        length -= start - offset

        f.seek(start + length)
        found_end_delim = seek_delimiter(f, delimiter, 2**16)
        end = f.tell()

        # Adjust split location to before delimiter if seek found the
        # delimiter sequence, not start or end of file.
        if found_start_delim and split_before:
            start -= len(delimiter)

        if found_end_delim and split_before:
            end -= len(delimiter)

        offset = start
        length = end - start

    f.seek(offset)

    # TODO: allow length to be None and read to the end of the file?
    assert length is not None
    b = f.read(length)
    return b


def tokenize(*args: Any, **kwargs: Any) -> str:
    """Deterministic token

    (modified from dask.base)

    >>> tokenize([1, 2, '3'])
    '9d71491b50023b06fc76928e6eddb952'

    >>> tokenize('Hello') == tokenize('Hello')
    True
    """
    if kwargs:
        args += (kwargs,)
    try:
        h = md5(str(args).encode())
    except ValueError:
        # FIPS systems: https://github.com/fsspec/filesystem_spec/issues/380
        h = md5(str(args).encode(), usedforsecurity=False)
    return h.hexdigest()


def stringify_path(filepath: str | os.PathLike[str] | pathlib.Path) -> str:
    """Attempt to convert a path-like object to a string.

    Parameters
    ----------
    filepath: object to be converted

    Returns
    -------
    filepath_str: maybe a string version of the object

    Notes
    -----
    Objects supporting the fspath protocol are coerced according to its
    __fspath__ method.

    For backwards compatibility with older Python version, pathlib.Path
    objects are specially coerced.

    Any other object is passed through unchanged, which includes bytes,
    strings, buffers, or anything else that's not even path-like.
    """
    if isinstance(filepath, str):
        return filepath
    elif hasattr(filepath, "__fspath__"):
        return filepath.__fspath__()
    elif hasattr(filepath, "path"):
        return filepath.path
    else:
        return filepath  # type: ignore[return-value]


def make_instance(
    cls: Callable[..., T], args: Sequence[Any], kwargs: dict[str, Any]
) -> T:
    inst = cls(*args, **kwargs)
    inst._determine_worker()  # type: ignore[attr-defined]
    return inst


def common_prefix(paths: Iterable[str]) -> str:
    """For a list of paths, find the shortest prefix common to all"""
    parts = [p.split("/") for p in paths]
    lmax = min(len(p) for p in parts)
    end = 0
    for i in range(lmax):
        end = all(p[i] == parts[0][i] for p in parts)
        if not end:
            break
    i += end
    return "/".join(parts[0][:i])


def other_paths(
    paths: list[str],
    path2: str | list[str],
    exists: bool = False,
    flatten: bool = False,
) -> list[str]:
    """In bulk file operations, construct a new file tree from a list of files

    Parameters
    ----------
    paths: list of str
        The input file tree
    path2: str or list of str
        Root to construct the new list in. If this is already a list of str, we just
        assert it has the right number of elements.
    exists: bool (optional)
        For a str destination, it is already exists (and is a dir), files should
        end up inside.
    flatten: bool (optional)
        Whether to flatten the input directory tree structure so that the output files
        are in the same directory.

    Returns
    -------
    list of str
    """

    if isinstance(path2, str):
        path2 = path2.rstrip("/")

        if flatten:
            path2 = ["/".join((path2, p.split("/")[-1])) for p in paths]
        else:
            cp = common_prefix(paths)
            if exists:
                cp = cp.rsplit("/", 1)[0]
            if not cp and all(not s.startswith("/") for s in paths):
                path2 = ["/".join([path2, p]) for p in paths]
            else:
                path2 = [p.replace(cp, path2, 1) for p in paths]
    else:
        assert len(paths) == len(path2)
    return path2


def is_exception(obj: Any) -> bool:
    return isinstance(obj, BaseException)


def isfilelike(f: Any) -> TypeGuard[IO[bytes]]:
    return all(hasattr(f, attr) for attr in ["read", "close", "tell"])


def get_protocol(url: str) -> str:
    url = stringify_path(url)
    parts = re.split(r"(\:\:|\://)", url, maxsplit=1)
    if len(parts) > 1:
        return parts[0]
    return "file"


def can_be_local(path: str) -> bool:
    """Can the given URL be used with open_local?"""
    from fsspec import get_filesystem_class

    try:
        return getattr(get_filesystem_class(get_protocol(path)), "local_file", False)
    except (ValueError, ImportError):
        # not in registry or import failed
        return False


def get_package_version_without_import(name: str) -> str | None:
    """For given package name, try to find the version without importing it

    Import and package.__version__ is still the backup here, so an import
    *might* happen.

    Returns either the version string, or None if the package
    or the version was not readily  found.
    """
    if name in sys.modules:
        mod = sys.modules[name]
        if hasattr(mod, "__version__"):
            return mod.__version__
    try:
        return version(name)
    except:  # noqa: E722
        pass
    try:
        import importlib

        mod = importlib.import_module(name)
        return mod.__version__
    except (ImportError, AttributeError):
        return None


def setup_logging(
    logger: logging.Logger | None = None,
    logger_name: str | None = None,
    level: str = "DEBUG",
    clear: bool = True,
) -> logging.Logger:
    if logger is None and logger_name is None:
        raise ValueError("Provide either logger object or logger name")
    logger = logger or logging.getLogger(logger_name)
    handle = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s -- %(message)s"
    )
    handle.setFormatter(formatter)
    if clear:
        logger.handlers.clear()
    logger.addHandler(handle)
    logger.setLevel(level)
    return logger


def _unstrip_protocol(name: str, fs: AbstractFileSystem) -> str:
    return fs.unstrip_protocol(name)


def mirror_from(
    origin_name: str, methods: Iterable[str]
) -> Callable[[type[T]], type[T]]:
    """Mirror attributes and methods from the given
    origin_name attribute of the instance to the
    decorated class"""

    def origin_getter(method: str, self: Any) -> Any:
        origin = getattr(self, origin_name)
        return getattr(origin, method)

    def wrapper(cls: type[T]) -> type[T]:
        for method in methods:
            wrapped_method = partial(origin_getter, method)
            setattr(cls, method, property(wrapped_method))
        return cls

    return wrapper


@contextlib.contextmanager
def nullcontext(obj: T) -> Iterator[T]:
    yield obj


def merge_offset_ranges(
    paths: list[str],
    starts: list[int] | int,
    ends: list[int] | int,
    max_gap: int = 0,
    max_block: int | None = None,
    sort: bool = True,
) -> tuple[list[str], list[int], list[int]]:
    """Merge adjacent byte-offset ranges when the inter-range
    gap is <= `max_gap`, and when the merged byte range does not
    exceed `max_block` (if specified). By default, this function
    will re-order the input paths and byte ranges to ensure sorted
    order. If the user can guarantee that the inputs are already
    sorted, passing `sort=False` will skip the re-ordering.
    """
    # Check input
    if not isinstance(paths, list):
        raise TypeError
    if not isinstance(starts, list):
        starts = [starts] * len(paths)
    if not isinstance(ends, list):
        ends = [ends] * len(paths)
    if len(starts) != len(paths) or len(ends) != len(paths):
        raise ValueError

    # Early Return
    if len(starts) <= 1:
        return paths, starts, ends

    starts = [s or 0 for s in starts]
    # Sort by paths and then ranges if `sort=True`
    if sort:
        paths, starts, ends = (
            list(v)
            for v in zip(
                *sorted(
                    zip(paths, starts, ends),
                )
            )
        )

    if paths:
        # Loop through the coupled `paths`, `starts`, and
        # `ends`, and merge adjacent blocks when appropriate
        new_paths = paths[:1]
        new_starts = starts[:1]
        new_ends = ends[:1]
        for i in range(1, len(paths)):
            if paths[i] == paths[i - 1] and new_ends[-1] is None:
                continue
            elif (
                paths[i] != paths[i - 1]
                or ((starts[i] - new_ends[-1]) > max_gap)
                or (max_block is not None and (ends[i] - new_starts[-1]) > max_block)
            ):
                # Cannot merge with previous block.
                # Add new `paths`, `starts`, and `ends` elements
                new_paths.append(paths[i])
                new_starts.append(starts[i])
                new_ends.append(ends[i])
            else:
                # Merge with previous block by updating the
                # last element of `ends`
                new_ends[-1] = ends[i]
        return new_paths, new_starts, new_ends

    # `paths` is empty. Just return input lists
    return paths, starts, ends


def file_size(filelike: IO[bytes]) -> int:
    """Find length of any open read-mode file-like"""
    pos = filelike.tell()
    try:
        return filelike.seek(0, 2)
    finally:
        filelike.seek(pos)


@contextlib.contextmanager
def atomic_write(path: str, mode: str = "wb"):
    """
    A context manager that opens a temporary file next to `path` and, on exit,
    replaces `path` with the temporary file, thereby updating `path`
    atomically.
    """
    fd, fn = tempfile.mkstemp(
        dir=os.path.dirname(path), prefix=os.path.basename(path) + "-"
    )
    try:
        with open(fd, mode) as fp:
            yield fp
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(fn)
        raise
    else:
        os.replace(fn, path)


def _translate(pat, STAR, QUESTION_MARK):
    # Copied from: https://github.com/python/cpython/pull/106703.
    res: list[str] = []
    add = res.append
    i, n = 0, len(pat)
    while i < n:
        c = pat[i]
        i = i + 1
        if c == "*":
            # compress consecutive `*` into one
            if (not res) or res[-1] is not STAR:
                add(STAR)
        elif c == "?":
            add(QUESTION_MARK)
        elif c == "[":
            j = i
            if j < n and pat[j] == "!":
                j = j + 1
            if j < n and pat[j] == "]":
                j = j + 1
            while j < n and pat[j] != "]":
                j = j + 1
            if j >= n:
                add("\\[")
            else:
                stuff = pat[i:j]
                if "-" not in stuff:
                    stuff = stuff.replace("\\", r"\\")
                else:
                    chunks = []
                    k = i + 2 if pat[i] == "!" else i + 1
                    while True:
                        k = pat.find("-", k, j)
                        if k < 0:
                            break
                        chunks.append(pat[i:k])
                        i = k + 1
                        k = k + 3
                    chunk = pat[i:j]
                    if chunk:
                        chunks.append(chunk)
                    else:
                        chunks[-1] += "-"
                    # Remove empty ranges -- invalid in RE.
                    for k in range(len(chunks) - 1, 0, -1):
                        if chunks[k - 1][-1] > chunks[k][0]:
                            chunks[k - 1] = chunks[k - 1][:-1] + chunks[k][1:]
                            del chunks[k]
                    # Escape backslashes and hyphens for set difference (--).
                    # Hyphens that create ranges shouldn't be escaped.
                    stuff = "-".join(
                        s.replace("\\", r"\\").replace("-", r"\-") for s in chunks
                    )
                # Escape set operations (&&, ~~ and ||).
                stuff = re.sub(r"([&~|])", r"\\\1", stuff)
                i = j + 1
                if not stuff:
                    # Empty range: never match.
                    add("(?!)")
                elif stuff == "!":
                    # Negated empty range: match any character.
                    add(".")
                else:
                    if stuff[0] == "!":
                        stuff = "^" + stuff[1:]
                    elif stuff[0] in ("^", "["):
                        stuff = "\\" + stuff
                    add(f"[{stuff}]")
        else:
            add(re.escape(c))
    assert i == n
    return res


def glob_translate(pat):
    # Copied from: https://github.com/python/cpython/pull/106703.
    # The keyword parameters' values are fixed to:
    # recursive=True, include_hidden=True, seps=None
    """Translate a pathname with shell wildcards to a regular expression."""
    if os.path.altsep:
        seps = os.path.sep + os.path.altsep
    else:
        seps = os.path.sep
    escaped_seps = "".join(map(re.escape, seps))
    any_sep = f"[{escaped_seps}]" if len(seps) > 1 else escaped_seps
    not_sep = f"[^{escaped_seps}]"
    one_last_segment = f"{not_sep}+"
    one_segment = f"{one_last_segment}{any_sep}"
    any_segments = f"(?:.+{any_sep})?"
    any_last_segments = ".*"
    results = []
    parts = re.split(any_sep, pat)
    last_part_idx = len(parts) - 1
    for idx, part in enumerate(parts):
        if part == "*":
            results.append(one_segment if idx < last_part_idx else one_last_segment)
            continue
        if part == "**":
            results.append(any_segments if idx < last_part_idx else any_last_segments)
            continue
        elif "**" in part:
            raise ValueError(
                "Invalid pattern: '**' can only be an entire path component"
            )
        if part:
            results.extend(_translate(part, f"{not_sep}*", not_sep))
        if idx < last_part_idx:
            results.append(any_sep)
    res = "".join(results)
    return rf"(?s:{res})\Z"

# === NexusCore/openenv\Lib\site-packages\referencing\_core.py ===
from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from enum import Enum
from typing import Any, Callable, ClassVar, Generic, Protocol
from urllib.parse import unquote, urldefrag, urljoin

from attrs import evolve, field
from rpds import HashTrieMap, HashTrieSet, List

try:
    from typing_extensions import TypeVar
except ImportError:  # pragma: no cover
    from typing import TypeVar

from referencing import exceptions
from referencing._attrs import frozen
from referencing.typing import URI, Anchor as AnchorType, D, Mapping, Retrieve

EMPTY_UNCRAWLED: HashTrieSet[URI] = HashTrieSet()
EMPTY_PREVIOUS_RESOLVERS: List[URI] = List()


class _Unset(Enum):
    """
    What sillyness...
    """

    SENTINEL = 1


_UNSET = _Unset.SENTINEL


class _MaybeInSubresource(Protocol[D]):
    def __call__(
        self,
        segments: Sequence[int | str],
        resolver: Resolver[D],
        subresource: Resource[D],
    ) -> Resolver[D]: ...


def _detect_or_error(contents: D) -> Specification[D]:
    if not isinstance(contents, Mapping):
        raise exceptions.CannotDetermineSpecification(contents)

    jsonschema_dialect_id = contents.get("$schema")  # type: ignore[reportUnknownMemberType]
    if not isinstance(jsonschema_dialect_id, str):
        raise exceptions.CannotDetermineSpecification(contents)

    from referencing.jsonschema import specification_with

    return specification_with(jsonschema_dialect_id)


def _detect_or_default(
    default: Specification[D],
) -> Callable[[D], Specification[D]]:
    def _detect(contents: D) -> Specification[D]:
        if not isinstance(contents, Mapping):
            return default

        jsonschema_dialect_id = contents.get("$schema")  # type: ignore[reportUnknownMemberType]
        if jsonschema_dialect_id is None:
            return default

        from referencing.jsonschema import specification_with

        return specification_with(
            jsonschema_dialect_id,  # type: ignore[reportUnknownArgumentType]
            default=default,
        )

    return _detect


class _SpecificationDetector:
    def __get__(
        self,
        instance: Specification[D] | None,
        cls: type[Specification[D]],
    ) -> Callable[[D], Specification[D]]:
        if instance is None:
            return _detect_or_error
        else:
            return _detect_or_default(instance)


@frozen
class Specification(Generic[D]):
    """
    A specification which defines referencing behavior.

    The various methods of a `Specification` allow for varying referencing
    behavior across JSON Schema specification versions, etc.
    """

    #: A short human-readable name for the specification, used for debugging.
    name: str

    #: Find the ID of a given document.
    id_of: Callable[[D], URI | None]

    #: Retrieve the subresources of the given document (without traversing into
    #: the subresources themselves).
    subresources_of: Callable[[D], Iterable[D]]

    #: While resolving a JSON pointer, conditionally enter a subresource
    #: (if e.g. we have just entered a keyword whose value is a subresource)
    maybe_in_subresource: _MaybeInSubresource[D]

    #: Retrieve the anchors contained in the given document.
    _anchors_in: Callable[
        [Specification[D], D],
        Iterable[AnchorType[D]],
    ] = field(alias="anchors_in")

    #: An opaque specification where resources have no subresources
    #: nor internal identifiers.
    OPAQUE: ClassVar[Specification[Any]]

    #: Attempt to discern which specification applies to the given contents.
    #:
    #: May be called either as an instance method or as a class method, with
    #: slightly different behavior in the following case:
    #:
    #: Recall that not all contents contains enough internal information about
    #: which specification it is written for -- the JSON Schema ``{}``,
    #: for instance, is valid under many different dialects and may be
    #: interpreted as any one of them.
    #:
    #: When this method is used as an instance method (i.e. called on a
    #: specific specification), that specification is used as the default
    #: if the given contents are unidentifiable.
    #:
    #: On the other hand when called as a class method, an error is raised.
    #:
    #: To reiterate, ``DRAFT202012.detect({})`` will return ``DRAFT202012``
    #: whereas the class method ``Specification.detect({})`` will raise an
    #: error.
    #:
    #: (Note that of course ``DRAFT202012.detect(...)`` may return some other
    #: specification when given a schema which *does* identify as being for
    #: another version).
    #:
    #: Raises:
    #:
    #:     `CannotDetermineSpecification`
    #:
    #:         if the given contents don't have any discernible
    #:         information which could be used to guess which
    #:         specification they identify as
    detect = _SpecificationDetector()

    def __repr__(self) -> str:
        return f"<Specification name={self.name!r}>"

    def anchors_in(self, contents: D):
        """
        Retrieve the anchors contained in the given document.
        """
        return self._anchors_in(self, contents)

    def create_resource(self, contents: D) -> Resource[D]:
        """
        Create a resource which is interpreted using this specification.
        """
        return Resource(contents=contents, specification=self)


Specification.OPAQUE = Specification(
    name="opaque",
    id_of=lambda contents: None,
    subresources_of=lambda contents: [],
    anchors_in=lambda specification, contents: [],
    maybe_in_subresource=lambda segments, resolver, subresource: resolver,
)


@frozen
class Resource(Generic[D]):
    r"""
    A document (deserialized JSON) with a concrete interpretation under a spec.

    In other words, a Python object, along with an instance of `Specification`
    which describes how the document interacts with referencing -- both
    internally (how it refers to other `Resource`\ s) and externally (how it
    should be identified such that it is referenceable by other documents).
    """

    contents: D
    _specification: Specification[D] = field(alias="specification")

    @classmethod
    def from_contents(
        cls,
        contents: D,
        default_specification: (
            type[Specification[D]] | Specification[D]
        ) = Specification,
    ) -> Resource[D]:
        """
        Create a resource guessing which specification applies to the contents.

        Raises:

            `CannotDetermineSpecification`

                if the given contents don't have any discernible
                information which could be used to guess which
                specification they identify as

        """
        specification = default_specification.detect(contents)
        return specification.create_resource(contents=contents)

    @classmethod
    def opaque(cls, contents: D) -> Resource[D]:
        """
        Create an opaque `Resource` -- i.e. one with opaque specification.

        See `Specification.OPAQUE` for details.
        """
        return Specification.OPAQUE.create_resource(contents=contents)

    def id(self) -> URI | None:
        """
        Retrieve this resource's (specification-specific) identifier.
        """
        id = self._specification.id_of(self.contents)
        if id is None:
            return
        return id.rstrip("#")

    def subresources(self) -> Iterable[Resource[D]]:
        """
        Retrieve this resource's subresources.
        """
        return (
            Resource.from_contents(
                each,
                default_specification=self._specification,
            )
            for each in self._specification.subresources_of(self.contents)
        )

    def anchors(self) -> Iterable[AnchorType[D]]:
        """
        Retrieve this resource's (specification-specific) identifier.
        """
        return self._specification.anchors_in(self.contents)

    def pointer(self, pointer: str, resolver: Resolver[D]) -> Resolved[D]:
        """
        Resolve the given JSON pointer.

        Raises:

            `exceptions.PointerToNowhere`

                if the pointer points to a location not present in the document

        """
        if not pointer:
            return Resolved(contents=self.contents, resolver=resolver)

        contents = self.contents
        segments: list[int | str] = []
        for segment in unquote(pointer[1:]).split("/"):
            if isinstance(contents, Sequence):
                segment = int(segment)
            else:
                segment = segment.replace("~1", "/").replace("~0", "~")
            try:
                contents = contents[segment]  # type: ignore[reportUnknownArgumentType]
            except LookupError as lookup_error:
                error = exceptions.PointerToNowhere(ref=pointer, resource=self)
                raise error from lookup_error

            segments.append(segment)
            last = resolver
            resolver = self._specification.maybe_in_subresource(
                segments=segments,
                resolver=resolver,
                subresource=self._specification.create_resource(contents),
            )
            if resolver is not last:
                segments = []
        return Resolved(contents=contents, resolver=resolver)  # type: ignore[reportUnknownArgumentType]


def _fail_to_retrieve(uri: URI):
    raise exceptions.NoSuchResource(ref=uri)


@frozen
class Registry(Mapping[URI, Resource[D]]):
    r"""
    A registry of `Resource`\ s, each identified by their canonical URIs.

    Registries store a collection of in-memory resources, and optionally
    enable additional resources which may be stored elsewhere (e.g. in a
    database, a separate set of files, over the network, etc.).

    They also lazily walk their known resources, looking for subresources
    within them. In other words, subresources contained within any added
    resources will be retrievable via their own IDs (though this discovery of
    subresources will be delayed until necessary).

    Registries are immutable, and their methods return new instances of the
    registry with the additional resources added to them.

    The ``retrieve`` argument can be used to configure retrieval of resources
    dynamically, either over the network, from a database, or the like.
    Pass it a callable which will be called if any URI not present in the
    registry is accessed. It must either return a `Resource` or else raise a
    `NoSuchResource` exception indicating that the resource does not exist
    even according to the retrieval logic.
    """

    _resources: HashTrieMap[URI, Resource[D]] = field(
        default=HashTrieMap(),
        converter=HashTrieMap.convert,  # type: ignore[reportGeneralTypeIssues]
        alias="resources",
    )
    _anchors: HashTrieMap[tuple[URI, str], AnchorType[D]] = HashTrieMap()
    _uncrawled: HashTrieSet[URI] = EMPTY_UNCRAWLED
    _retrieve: Retrieve[D] = field(default=_fail_to_retrieve, alias="retrieve")

    def __getitem__(self, uri: URI) -> Resource[D]:
        """
        Return the (already crawled) `Resource` identified by the given URI.
        """
        try:
            return self._resources[uri.rstrip("#")]
        except KeyError:
            raise exceptions.NoSuchResource(ref=uri) from None

    def __iter__(self) -> Iterator[URI]:
        """
        Iterate over all crawled URIs in the registry.
        """
        return iter(self._resources)

    def __len__(self) -> int:
        """
        Count the total number of fully crawled resources in this registry.
        """
        return len(self._resources)

    def __rmatmul__(
        self,
        new: Resource[D] | Iterable[Resource[D]],
    ) -> Registry[D]:
        """
        Create a new registry with resource(s) added using their internal IDs.

        Resources must have a internal IDs (e.g. the :kw:`$id` keyword in
        modern JSON Schema versions), otherwise an error will be raised.

        Both a single resource as well as an iterable of resources works, i.e.:

            * ``resource @ registry`` or

            * ``[iterable, of, multiple, resources] @ registry``

        which -- again, assuming the resources have internal IDs -- is
        equivalent to calling `Registry.with_resources` as such:

        .. code:: python

            registry.with_resources(
                (resource.id(), resource) for resource in new_resources
            )

        Raises:

            `NoInternalID`

                if the resource(s) in fact do not have IDs

        """
        if isinstance(new, Resource):
            new = (new,)

        resources = self._resources
        uncrawled = self._uncrawled
        for resource in new:
            id = resource.id()
            if id is None:
                raise exceptions.NoInternalID(resource=resource)
            uncrawled = uncrawled.insert(id)
            resources = resources.insert(id, resource)
        return evolve(self, resources=resources, uncrawled=uncrawled)

    def __repr__(self) -> str:
        size = len(self)
        pluralized = "resource" if size == 1 else "resources"
        if self._uncrawled:
            uncrawled = len(self._uncrawled)
            if uncrawled == size:
                summary = f"uncrawled {pluralized}"
            else:
                summary = f"{pluralized}, {uncrawled} uncrawled"
        else:
            summary = f"{pluralized}"
        return f"<Registry ({size} {summary})>"

    def get_or_retrieve(self, uri: URI) -> Retrieved[D, Resource[D]]:
        """
        Get a resource from the registry, crawling or retrieving if necessary.

        May involve crawling to find the given URI if it is not already known,
        so the returned object is a `Retrieved` object which contains both the
        resource value as well as the registry which ultimately contained it.
        """
        resource = self._resources.get(uri)
        if resource is not None:
            return Retrieved(registry=self, value=resource)

        registry = self.crawl()
        resource = registry._resources.get(uri)
        if resource is not None:
            return Retrieved(registry=registry, value=resource)

        try:
            resource = registry._retrieve(uri)
        except (
            exceptions.CannotDetermineSpecification,
            exceptions.NoSuchResource,
        ):
            raise
        except Exception as error:
            raise exceptions.Unretrievable(ref=uri) from error
        else:
            registry = registry.with_resource(uri, resource)
            return Retrieved(registry=registry, value=resource)

    def remove(self, uri: URI):
        """
        Return a registry with the resource identified by a given URI removed.
        """
        if uri not in self._resources:
            raise exceptions.NoSuchResource(ref=uri)

        return evolve(
            self,
            resources=self._resources.remove(uri),
            uncrawled=self._uncrawled.discard(uri),
            anchors=HashTrieMap(
                (k, v) for k, v in self._anchors.items() if k[0] != uri
            ),
        )

    def anchor(self, uri: URI, name: str):
        """
        Retrieve a given anchor from a resource which must already be crawled.
        """
        value = self._anchors.get((uri, name))
        if value is not None:
            return Retrieved(value=value, registry=self)

        registry = self.crawl()
        value = registry._anchors.get((uri, name))
        if value is not None:
            return Retrieved(value=value, registry=registry)

        resource = self[uri]
        canonical_uri = resource.id()
        if canonical_uri is not None:
            value = registry._anchors.get((canonical_uri, name))
            if value is not None:
                return Retrieved(value=value, registry=registry)

        if "/" in name:
            raise exceptions.InvalidAnchor(
                ref=uri,
                resource=resource,
                anchor=name,
            )
        raise exceptions.NoSuchAnchor(ref=uri, resource=resource, anchor=name)

    def contents(self, uri: URI) -> D:
        """
        Retrieve the (already crawled) contents identified by the given URI.
        """
        return self[uri].contents

    def crawl(self) -> Registry[D]:
        """
        Crawl all added resources, discovering subresources.
        """
        resources = self._resources
        anchors = self._anchors
        uncrawled = [(uri, resources[uri]) for uri in self._uncrawled]
        while uncrawled:
            uri, resource = uncrawled.pop()

            id = resource.id()
            if id is not None:
                uri = urljoin(uri, id)
                resources = resources.insert(uri, resource)
            for each in resource.anchors():
                anchors = anchors.insert((uri, each.name), each)
            uncrawled.extend((uri, each) for each in resource.subresources())
        return evolve(
            self,
            resources=resources,
            anchors=anchors,
            uncrawled=EMPTY_UNCRAWLED,
        )

    def with_resource(self, uri: URI, resource: Resource[D]):
        """
        Add the given `Resource` to the registry, without crawling it.
        """
        return self.with_resources([(uri, resource)])

    def with_resources(
        self,
        pairs: Iterable[tuple[URI, Resource[D]]],
    ) -> Registry[D]:
        r"""
        Add the given `Resource`\ s to the registry, without crawling them.
        """
        resources = self._resources
        uncrawled = self._uncrawled
        for uri, resource in pairs:
            # Empty fragment URIs are equivalent to URIs without the fragment.
            # TODO: Is this true for non JSON Schema resources? Probably not.
            uri = uri.rstrip("#")
            uncrawled = uncrawled.insert(uri)
            resources = resources.insert(uri, resource)
        return evolve(self, resources=resources, uncrawled=uncrawled)

    def with_contents(
        self,
        pairs: Iterable[tuple[URI, D]],
        **kwargs: Any,
    ) -> Registry[D]:
        r"""
        Add the given contents to the registry, autodetecting when necessary.
        """
        return self.with_resources(
            (uri, Resource.from_contents(each, **kwargs))
            for uri, each in pairs
        )

    def combine(self, *registries: Registry[D]) -> Registry[D]:
        """
        Combine together one or more other registries, producing a unified one.
        """
        if registries == (self,):
            return self
        resources = self._resources
        anchors = self._anchors
        uncrawled = self._uncrawled
        retrieve = self._retrieve
        for registry in registries:
            resources = resources.update(registry._resources)
            anchors = anchors.update(registry._anchors)
            uncrawled = uncrawled.update(registry._uncrawled)

            if registry._retrieve is not _fail_to_retrieve:  # type: ignore[reportUnnecessaryComparison] ???
                if registry._retrieve is not retrieve is not _fail_to_retrieve:  # type: ignore[reportUnnecessaryComparison] ???
                    raise ValueError(  # noqa: TRY003
                        "Cannot combine registries with conflicting retrieval "
                        "functions.",
                    )
                retrieve = registry._retrieve
        return evolve(
            self,
            anchors=anchors,
            resources=resources,
            uncrawled=uncrawled,
            retrieve=retrieve,
        )

    def resolver(self, base_uri: URI = "") -> Resolver[D]:
        """
        Return a `Resolver` which resolves references against this registry.
        """
        return Resolver(base_uri=base_uri, registry=self)

    def resolver_with_root(self, resource: Resource[D]) -> Resolver[D]:
        """
        Return a `Resolver` with a specific root resource.
        """
        uri = resource.id() or ""
        return Resolver(
            base_uri=uri,
            registry=self.with_resource(uri, resource),
        )


#: An anchor or resource.
AnchorOrResource = TypeVar(
    "AnchorOrResource",
    AnchorType[Any],
    Resource[Any],
    default=Resource[Any],
)


@frozen
class Retrieved(Generic[D, AnchorOrResource]):
    """
    A value retrieved from a `Registry`.
    """

    value: AnchorOrResource
    registry: Registry[D]


@frozen
class Resolved(Generic[D]):
    """
    A reference resolved to its contents by a `Resolver`.
    """

    contents: D
    resolver: Resolver[D]


@frozen
class Resolver(Generic[D]):
    """
    A reference resolver.

    Resolvers help resolve references (including relative ones) by
    pairing a fixed base URI with a `Registry`.

    This object, under normal circumstances, is expected to be used by
    *implementers of libraries* built on top of `referencing` (e.g. JSON Schema
    implementations or other libraries resolving JSON references),
    not directly by end-users populating registries or while writing
    schemas or other resources.

    References are resolved against the base URI, and the combined URI
    is then looked up within the registry.

    The process of resolving a reference may itself involve calculating
    a *new* base URI for future reference resolution (e.g. if an
    intermediate resource sets a new base URI), or may involve encountering
    additional subresources and adding them to a new registry.
    """

    _base_uri: URI = field(alias="base_uri")
    _registry: Registry[D] = field(alias="registry")
    _previous: List[URI] = field(default=List(), repr=False, alias="previous")

    def lookup(self, ref: URI) -> Resolved[D]:
        """
        Resolve the given reference to the resource it points to.

        Raises:

            `exceptions.Unresolvable`

                or a subclass thereof (see below) if the reference isn't
                resolvable

            `exceptions.NoSuchAnchor`

                if the reference is to a URI where a resource exists but
                contains a plain name fragment which does not exist within
                the resource

            `exceptions.PointerToNowhere`

                if the reference is to a URI where a resource exists but
                contains a JSON pointer to a location within the resource
                that does not exist

        """
        if ref.startswith("#"):
            uri, fragment = self._base_uri, ref[1:]
        else:
            uri, fragment = urldefrag(urljoin(self._base_uri, ref))
        try:
            retrieved = self._registry.get_or_retrieve(uri)
        except exceptions.NoSuchResource:
            raise exceptions.Unresolvable(ref=ref) from None
        except exceptions.Unretrievable as error:
            raise exceptions.Unresolvable(ref=ref) from error

        if fragment.startswith("/"):
            resolver = self._evolve(registry=retrieved.registry, base_uri=uri)
            return retrieved.value.pointer(pointer=fragment, resolver=resolver)

        if fragment:
            retrieved = retrieved.registry.anchor(uri, fragment)
            resolver = self._evolve(registry=retrieved.registry, base_uri=uri)
            return retrieved.value.resolve(resolver=resolver)

        resolver = self._evolve(registry=retrieved.registry, base_uri=uri)
        return Resolved(contents=retrieved.value.contents, resolver=resolver)

    def in_subresource(self, subresource: Resource[D]) -> Resolver[D]:
        """
        Create a resolver for a subresource (which may have a new base URI).
        """
        id = subresource.id()
        if id is None:
            return self
        return evolve(self, base_uri=urljoin(self._base_uri, id))

    def dynamic_scope(self) -> Iterable[tuple[URI, Registry[D]]]:
        """
        In specs with such a notion, return the URIs in the dynamic scope.
        """
        for uri in self._previous:
            yield uri, self._registry

    def _evolve(self, base_uri: URI, **kwargs: Any):
        """
        Evolve, appending to the dynamic scope.
        """
        previous = self._previous
        if self._base_uri and (not previous or base_uri != self._base_uri):
            previous = previous.push_front(self._base_uri)
        return evolve(self, base_uri=base_uri, previous=previous, **kwargs)


@frozen
class Anchor(Generic[D]):
    """
    A simple anchor in a `Resource`.
    """

    name: str
    resource: Resource[D]

    def resolve(self, resolver: Resolver[D]):
        """
        Return the resource for this anchor.
        """
        return Resolved(contents=self.resource.contents, resolver=resolver)

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\varStore.py ===
from fontTools.misc.roundTools import noRound, otRound
from fontTools.misc.intTools import bit_count
from fontTools.ttLib.tables import otTables as ot
from fontTools.varLib.models import supportScalar
from fontTools.varLib.builder import (
    buildVarRegionList,
    buildVarStore,
    buildVarRegion,
    buildVarData,
)
from functools import partial
from collections import defaultdict
from heapq import heappush, heappop


NO_VARIATION_INDEX = ot.NO_VARIATION_INDEX
ot.VarStore.NO_VARIATION_INDEX = NO_VARIATION_INDEX


def _getLocationKey(loc):
    return tuple(sorted(loc.items(), key=lambda kv: kv[0]))


class OnlineVarStoreBuilder(object):
    def __init__(self, axisTags):
        self._axisTags = axisTags
        self._regionMap = {}
        self._regionList = buildVarRegionList([], axisTags)
        self._store = buildVarStore(self._regionList, [])
        self._data = None
        self._model = None
        self._supports = None
        self._varDataIndices = {}
        self._varDataCaches = {}
        self._cache = None

    def setModel(self, model):
        self.setSupports(model.supports)
        self._model = model

    def setSupports(self, supports):
        self._model = None
        self._supports = list(supports)
        if self._supports and not self._supports[0]:
            del self._supports[0]  # Drop base master support
        self._cache = None
        self._data = None

    def finish(self, optimize=True):
        self._regionList.RegionCount = len(self._regionList.Region)
        self._store.VarDataCount = len(self._store.VarData)
        for data in self._store.VarData:
            data.ItemCount = len(data.Item)
            data.calculateNumShorts(optimize=optimize)
        return self._store

    def _add_VarData(self, num_items=1):
        regionMap = self._regionMap
        regionList = self._regionList

        regions = self._supports
        regionIndices = []
        for region in regions:
            key = _getLocationKey(region)
            idx = regionMap.get(key)
            if idx is None:
                varRegion = buildVarRegion(region, self._axisTags)
                idx = regionMap[key] = len(regionList.Region)
                regionList.Region.append(varRegion)
            regionIndices.append(idx)

        # Check if we have one already...
        key = tuple(regionIndices)
        varDataIdx = self._varDataIndices.get(key)
        if varDataIdx is not None:
            self._outer = varDataIdx
            self._data = self._store.VarData[varDataIdx]
            self._cache = self._varDataCaches[key]
            if len(self._data.Item) + num_items > 0xFFFF:
                # This is full.  Need new one.
                varDataIdx = None

        if varDataIdx is None:
            self._data = buildVarData(regionIndices, [], optimize=False)
            self._outer = len(self._store.VarData)
            self._store.VarData.append(self._data)
            self._varDataIndices[key] = self._outer
            if key not in self._varDataCaches:
                self._varDataCaches[key] = {}
            self._cache = self._varDataCaches[key]

    def storeMasters(self, master_values, *, round=round):
        deltas = self._model.getDeltas(master_values, round=round)
        base = deltas.pop(0)
        return base, self.storeDeltas(deltas, round=noRound)

    def storeMastersMany(self, master_values_list, *, round=round):
        deltas_list = [
            self._model.getDeltas(master_values, round=round)
            for master_values in master_values_list
        ]
        base_list = [deltas.pop(0) for deltas in deltas_list]
        return base_list, self.storeDeltasMany(deltas_list, round=noRound)

    def storeDeltas(self, deltas, *, round=round):
        deltas = [round(d) for d in deltas]
        if len(deltas) == len(self._supports) + 1:
            deltas = tuple(deltas[1:])
        else:
            assert len(deltas) == len(self._supports)
            deltas = tuple(deltas)

        if not self._data:
            self._add_VarData()

        varIdx = self._cache.get(deltas)
        if varIdx is not None:
            return varIdx

        inner = len(self._data.Item)
        if inner == 0xFFFF:
            # Full array. Start new one.
            self._add_VarData()
            return self.storeDeltas(deltas, round=noRound)
        self._data.addItem(deltas, round=noRound)

        varIdx = (self._outer << 16) + inner
        self._cache[deltas] = varIdx
        return varIdx

    def storeDeltasMany(self, deltas_list, *, round=round):
        deltas_list = [[round(d) for d in deltas] for deltas in deltas_list]
        deltas_list = tuple(tuple(deltas) for deltas in deltas_list)

        if not self._data:
            self._add_VarData(len(deltas_list))

        varIdx = self._cache.get(deltas_list)
        if varIdx is not None:
            return varIdx

        inner = len(self._data.Item)
        if inner + len(deltas_list) > 0xFFFF:
            # Full array. Start new one.
            self._add_VarData(len(deltas_list))
            return self.storeDeltasMany(deltas_list, round=noRound)
        for i, deltas in enumerate(deltas_list):
            self._data.addItem(deltas, round=noRound)

            varIdx = (self._outer << 16) + inner + i
            self._cache[deltas] = varIdx

        varIdx = (self._outer << 16) + inner
        self._cache[deltas_list] = varIdx

        return varIdx


def VarData_addItem(self, deltas, *, round=round):
    deltas = [round(d) for d in deltas]

    countUs = self.VarRegionCount
    countThem = len(deltas)
    if countUs + 1 == countThem:
        deltas = list(deltas[1:])
    else:
        assert countUs == countThem, (countUs, countThem)
        deltas = list(deltas)
    self.Item.append(deltas)
    self.ItemCount = len(self.Item)


ot.VarData.addItem = VarData_addItem


def VarRegion_get_support(self, fvar_axes):
    return {
        fvar_axes[i].axisTag: (reg.StartCoord, reg.PeakCoord, reg.EndCoord)
        for i, reg in enumerate(self.VarRegionAxis)
        if reg.PeakCoord != 0
    }


ot.VarRegion.get_support = VarRegion_get_support


def VarStore___bool__(self):
    return bool(self.VarData)


ot.VarStore.__bool__ = VarStore___bool__


class VarStoreInstancer(object):
    def __init__(self, varstore, fvar_axes, location={}):
        self.fvar_axes = fvar_axes
        assert varstore is None or varstore.Format == 1
        self._varData = varstore.VarData if varstore else []
        self._regions = varstore.VarRegionList.Region if varstore else []
        self.setLocation(location)

    def setLocation(self, location):
        self.location = dict(location)
        self._clearCaches()

    def _clearCaches(self):
        self._scalars = {}

    def _getScalar(self, regionIdx):
        scalar = self._scalars.get(regionIdx)
        if scalar is None:
            support = self._regions[regionIdx].get_support(self.fvar_axes)
            scalar = supportScalar(self.location, support)
            self._scalars[regionIdx] = scalar
        return scalar

    @staticmethod
    def interpolateFromDeltasAndScalars(deltas, scalars):
        delta = 0.0
        for d, s in zip(deltas, scalars):
            if not s:
                continue
            delta += d * s
        return delta

    def __getitem__(self, varidx):
        major, minor = varidx >> 16, varidx & 0xFFFF
        if varidx == NO_VARIATION_INDEX:
            return 0.0
        varData = self._varData
        scalars = [self._getScalar(ri) for ri in varData[major].VarRegionIndex]
        deltas = varData[major].Item[minor]
        return self.interpolateFromDeltasAndScalars(deltas, scalars)

    def interpolateFromDeltas(self, varDataIndex, deltas):
        varData = self._varData
        scalars = [self._getScalar(ri) for ri in varData[varDataIndex].VarRegionIndex]
        return self.interpolateFromDeltasAndScalars(deltas, scalars)


#
# Optimizations
#
# retainFirstMap - If true, major 0 mappings are retained. Deltas for unused indices are zeroed
# advIdxes - Set of major 0 indices for advance deltas to be listed first. Other major 0 indices follow.


def VarStore_subset_varidxes(
    self,
    varIdxes,
    optimize=True,
    retainFirstMap=False,
    advIdxes=set(),
    *,
    VarData="VarData",
):
    # Sort out used varIdxes by major/minor.
    used = defaultdict(set)
    for varIdx in varIdxes:
        if varIdx == NO_VARIATION_INDEX:
            continue
        major = varIdx >> 16
        minor = varIdx & 0xFFFF
        used[major].add(minor)
    del varIdxes

    #
    # Subset VarData
    #

    varData = getattr(self, VarData)
    newVarData = []
    varDataMap = {NO_VARIATION_INDEX: NO_VARIATION_INDEX}
    for major, data in enumerate(varData):
        usedMinors = used.get(major)
        if usedMinors is None:
            continue
        newMajor = len(newVarData)
        newVarData.append(data)

        items = data.Item
        newItems = []
        if major == 0 and retainFirstMap:
            for minor in range(len(items)):
                newItems.append(
                    items[minor] if minor in usedMinors else [0] * len(items[minor])
                )
                varDataMap[minor] = minor
        else:
            if major == 0:
                minors = sorted(advIdxes) + sorted(usedMinors - advIdxes)
            else:
                minors = sorted(usedMinors)
            for minor in minors:
                newMinor = len(newItems)
                newItems.append(items[minor])
                varDataMap[(major << 16) + minor] = (newMajor << 16) + newMinor

        data.Item = newItems
        data.ItemCount = len(data.Item)

        if VarData == "VarData":
            data.calculateNumShorts(optimize=optimize)

    setattr(self, VarData, newVarData)
    setattr(self, VarData + "Count", len(newVarData))

    self.prune_regions()

    return varDataMap


ot.VarStore.subset_varidxes = VarStore_subset_varidxes


def VarStore_prune_regions(self, *, VarData="VarData", VarRegionList="VarRegionList"):
    """Remove unused VarRegions."""
    #
    # Subset VarRegionList
    #

    # Collect.
    usedRegions = set()
    for data in getattr(self, VarData):
        usedRegions.update(data.VarRegionIndex)
    # Subset.
    regionList = getattr(self, VarRegionList)
    regions = regionList.Region
    newRegions = []
    regionMap = {}
    for i in sorted(usedRegions):
        regionMap[i] = len(newRegions)
        newRegions.append(regions[i])
    regionList.Region = newRegions
    regionList.RegionCount = len(regionList.Region)
    # Map.
    for data in getattr(self, VarData):
        data.VarRegionIndex = [regionMap[i] for i in data.VarRegionIndex]


ot.VarStore.prune_regions = VarStore_prune_regions


def _visit(self, func):
    """Recurse down from self, if type of an object is ot.Device,
    call func() on it.  Works on otData-style classes."""

    if type(self) == ot.Device:
        func(self)

    elif isinstance(self, list):
        for that in self:
            _visit(that, func)

    elif hasattr(self, "getConverters") and not hasattr(self, "postRead"):
        for conv in self.getConverters():
            that = getattr(self, conv.name, None)
            if that is not None:
                _visit(that, func)

    elif isinstance(self, ot.ValueRecord):
        for that in self.__dict__.values():
            _visit(that, func)


def _Device_recordVarIdx(self, s):
    """Add VarIdx in this Device table (if any) to the set s."""
    if self.DeltaFormat == 0x8000:
        s.add((self.StartSize << 16) + self.EndSize)


def Object_collect_device_varidxes(self, varidxes):
    adder = partial(_Device_recordVarIdx, s=varidxes)
    _visit(self, adder)


ot.GDEF.collect_device_varidxes = Object_collect_device_varidxes
ot.GPOS.collect_device_varidxes = Object_collect_device_varidxes


def _Device_mapVarIdx(self, mapping, done):
    """Map VarIdx in this Device table (if any) through mapping."""
    if id(self) in done:
        return
    done.add(id(self))
    if self.DeltaFormat == 0x8000:
        varIdx = mapping[(self.StartSize << 16) + self.EndSize]
        self.StartSize = varIdx >> 16
        self.EndSize = varIdx & 0xFFFF


def Object_remap_device_varidxes(self, varidxes_map):
    mapper = partial(_Device_mapVarIdx, mapping=varidxes_map, done=set())
    _visit(self, mapper)


ot.GDEF.remap_device_varidxes = Object_remap_device_varidxes
ot.GPOS.remap_device_varidxes = Object_remap_device_varidxes


class _Encoding(object):
    def __init__(self, chars):
        self.chars = chars
        self.width = bit_count(chars)
        self.columns = self._columns(chars)
        self.overhead = self._characteristic_overhead(self.columns)
        self.items = set()

    def append(self, row):
        self.items.add(row)

    def extend(self, lst):
        self.items.update(lst)

    def width_sort_key(self):
        return self.width, self.chars

    @staticmethod
    def _characteristic_overhead(columns):
        """Returns overhead in bytes of encoding this characteristic
        as a VarData."""
        c = 4 + 6  # 4 bytes for LOffset, 6 bytes for VarData header
        c += bit_count(columns) * 2
        return c

    @staticmethod
    def _columns(chars):
        cols = 0
        i = 1
        while chars:
            if chars & 0b1111:
                cols |= i
            chars >>= 4
            i <<= 1
        return cols

    def gain_from_merging(self, other_encoding):
        combined_chars = other_encoding.chars | self.chars
        combined_width = bit_count(combined_chars)
        combined_columns = self.columns | other_encoding.columns
        combined_overhead = _Encoding._characteristic_overhead(combined_columns)
        combined_gain = (
            +self.overhead
            + other_encoding.overhead
            - combined_overhead
            - (combined_width - self.width) * len(self.items)
            - (combined_width - other_encoding.width) * len(other_encoding.items)
        )
        return combined_gain


class _EncodingDict(dict):
    def __missing__(self, chars):
        r = self[chars] = _Encoding(chars)
        return r

    def add_row(self, row):
        chars = self._row_characteristics(row)
        self[chars].append(row)

    @staticmethod
    def _row_characteristics(row):
        """Returns encoding characteristics for a row."""
        longWords = False

        chars = 0
        i = 1
        for v in row:
            if v:
                chars += i
            if not (-128 <= v <= 127):
                chars += i * 0b0010
            if not (-32768 <= v <= 32767):
                longWords = True
                break
            i <<= 4

        if longWords:
            # Redo; only allow 2byte/4byte encoding
            chars = 0
            i = 1
            for v in row:
                if v:
                    chars += i * 0b0011
                if not (-32768 <= v <= 32767):
                    chars += i * 0b1100
                i <<= 4

        return chars


def VarStore_optimize(self, use_NO_VARIATION_INDEX=True, quantization=1):
    """Optimize storage. Returns mapping from old VarIdxes to new ones."""

    # Overview:
    #
    # For each VarData row, we first extend it with zeroes to have
    # one column per region in VarRegionList. We then group the
    # rows into _Encoding objects, by their "characteristic" bitmap.
    # The characteristic bitmap is a binary number representing how
    # many bytes each column of the data takes up to encode. Each
    # column is encoded in four bits. For example, if a column has
    # only values in the range -128..127, it would only have a single
    # bit set in the characteristic bitmap for that column. If it has
    # values in the range -32768..32767, it would have two bits set.
    # The number of ones in the characteristic bitmap is the "width"
    # of the encoding.
    #
    # Each encoding as such has a number of "active" (ie. non-zero)
    # columns. The overhead of encoding the characteristic bitmap
    # is 10 bytes, plus 2 bytes per active column.
    #
    # When an encoding is merged into another one, if the characteristic
    # of the old encoding is a subset of the new one, then the overhead
    # of the old encoding is completely eliminated. However, each row
    # now would require more bytes to encode, to the tune of one byte
    # per characteristic bit that is active in the new encoding but not
    # in the old one.
    #
    # The "gain" of merging two encodings is how many bytes we save by doing so.
    #
    # High-level algorithm:
    #
    # - Each encoding has a minimal way to encode it. However, because
    #   of the overhead of encoding the characteristic bitmap, it may
    #   be beneficial to merge two encodings together, if there is
    #   gain in doing so. As such, we need to search for the best
    #   such successive merges.
    #
    # Algorithm:
    #
    # - Put all encodings into a "todo" list.
    #
    # - Sort todo list (for stability) by width_sort_key(), which is a tuple
    #   of the following items:
    #   * The "width" of the encoding.
    #   * The characteristic bitmap of the encoding, with higher-numbered
    #     columns compared first.
    #
    # - Make a priority-queue of the gain from combining each two
    #   encodings in the todo list. The priority queue is sorted by
    #   decreasing gain. Only positive gains are included.
    #
    # - While priority queue is not empty:
    #   - Pop the first item from the priority queue,
    #   - Merge the two encodings it represents,
    #   - Remove the two encodings from the todo list,
    #   - Insert positive gains from combining the new encoding with
    #     all existing todo list items into the priority queue,
    #   - If a todo list item with the same characteristic bitmap as
    #     the new encoding exists, remove it from the todo list and
    #     merge it into the new encoding.
    #   - Insert the new encoding into the todo list,
    #
    # - Encode all remaining items in the todo list.
    #
    # The output is then sorted for stability, in the following way:
    # - The VarRegionList of the input is kept intact.
    # - The VarData is sorted by the same width_sort_key() used at the beginning.
    # - Within each VarData, the items are sorted as vectors of numbers.
    #
    # Finally, each VarData is optimized to remove the empty columns and
    # reorder columns as needed.

    # TODO
    # Check that no two VarRegions are the same; if they are, fold them.

    n = len(self.VarRegionList.Region)  # Number of columns
    zeroes = [0] * n

    front_mapping = {}  # Map from old VarIdxes to full row tuples

    encodings = _EncodingDict()

    # Collect all items into a set of full rows (with lots of zeroes.)
    for major, data in enumerate(self.VarData):
        regionIndices = data.VarRegionIndex

        for minor, item in enumerate(data.Item):
            row = list(zeroes)

            if quantization == 1:
                for regionIdx, v in zip(regionIndices, item):
                    row[regionIdx] += v
            else:
                for regionIdx, v in zip(regionIndices, item):
                    row[regionIdx] += (
                        round(v / quantization) * quantization
                    )  # TODO https://github.com/fonttools/fonttools/pull/3126#discussion_r1205439785

            row = tuple(row)

            if use_NO_VARIATION_INDEX and not any(row):
                front_mapping[(major << 16) + minor] = None
                continue

            encodings.add_row(row)
            front_mapping[(major << 16) + minor] = row

    # Prepare for the main algorithm.
    todo = sorted(encodings.values(), key=_Encoding.width_sort_key)
    del encodings

    # Repeatedly pick two best encodings to combine, and combine them.

    heap = []
    for i, encoding in enumerate(todo):
        for j in range(i + 1, len(todo)):
            other_encoding = todo[j]
            combining_gain = encoding.gain_from_merging(other_encoding)
            if combining_gain > 0:
                heappush(heap, (-combining_gain, i, j))

    while heap:
        _, i, j = heappop(heap)
        if todo[i] is None or todo[j] is None:
            continue

        encoding, other_encoding = todo[i], todo[j]
        todo[i], todo[j] = None, None

        # Combine the two encodings
        combined_chars = other_encoding.chars | encoding.chars
        combined_encoding = _Encoding(combined_chars)
        combined_encoding.extend(encoding.items)
        combined_encoding.extend(other_encoding.items)

        for k, enc in enumerate(todo):
            if enc is None:
                continue

            # In the unlikely event that the same encoding exists already,
            # combine it.
            if enc.chars == combined_chars:
                combined_encoding.extend(enc.items)
                todo[k] = None
                continue

            combining_gain = combined_encoding.gain_from_merging(enc)
            if combining_gain > 0:
                heappush(heap, (-combining_gain, k, len(todo)))

        todo.append(combined_encoding)

    encodings = [encoding for encoding in todo if encoding is not None]

    # Assemble final store.
    back_mapping = {}  # Mapping from full rows to new VarIdxes
    encodings.sort(key=_Encoding.width_sort_key)
    self.VarData = []
    for encoding in encodings:
        items = sorted(encoding.items)

        while items:
            major = len(self.VarData)
            data = ot.VarData()
            self.VarData.append(data)
            data.VarRegionIndex = range(n)
            data.VarRegionCount = len(data.VarRegionIndex)

            # Each major can only encode up to 0xFFFF entries.
            data.Item, items = items[:0xFFFF], items[0xFFFF:]

            for minor, item in enumerate(data.Item):
                back_mapping[item] = (major << 16) + minor

    # Compile final mapping.
    varidx_map = {NO_VARIATION_INDEX: NO_VARIATION_INDEX}
    for k, v in front_mapping.items():
        varidx_map[k] = back_mapping[v] if v is not None else NO_VARIATION_INDEX

    # Recalculate things and go home.
    self.VarRegionList.RegionCount = len(self.VarRegionList.Region)
    self.VarDataCount = len(self.VarData)
    for data in self.VarData:
        data.ItemCount = len(data.Item)
        data.optimize()

    # Remove unused regions.
    self.prune_regions()

    return varidx_map


ot.VarStore.optimize = VarStore_optimize


def main(args=None):
    """Optimize a font's GDEF variation store"""
    from argparse import ArgumentParser
    from fontTools import configLogger
    from fontTools.ttLib import TTFont
    from fontTools.ttLib.tables.otBase import OTTableWriter

    parser = ArgumentParser(prog="varLib.varStore", description=main.__doc__)
    parser.add_argument("--quantization", type=int, default=1)
    parser.add_argument("fontfile")
    parser.add_argument("outfile", nargs="?")
    options = parser.parse_args(args)

    # TODO: allow user to configure logging via command-line options
    configLogger(level="INFO")

    quantization = options.quantization
    fontfile = options.fontfile
    outfile = options.outfile

    font = TTFont(fontfile)
    gdef = font["GDEF"]
    store = gdef.table.VarStore

    writer = OTTableWriter()
    store.compile(writer, font)
    size = len(writer.getAllData())
    print("Before: %7d bytes" % size)

    varidx_map = store.optimize(quantization=quantization)

    writer = OTTableWriter()
    store.compile(writer, font)
    size = len(writer.getAllData())
    print("After:  %7d bytes" % size)

    if outfile is not None:
        gdef.table.remap_device_varidxes(varidx_map)
        if "GPOS" in font:
            font["GPOS"].table.remap_device_varidxes(varidx_map)

        font.save(outfile)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        sys.exit(main())
    import doctest

    sys.exit(doctest.testmod().failed)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_postgres_builtins.py ===
"""
    pygments.lexers._postgres_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Self-updating data files for PostgreSQL lexer.

    Run with `python -I` to update itself.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# Autogenerated: please edit them if you like wasting your time.

KEYWORDS = (
    'ABORT',
    'ABSOLUTE',
    'ACCESS',
    'ACTION',
    'ADD',
    'ADMIN',
    'AFTER',
    'AGGREGATE',
    'ALL',
    'ALSO',
    'ALTER',
    'ALWAYS',
    'ANALYSE',
    'ANALYZE',
    'AND',
    'ANY',
    'ARRAY',
    'AS',
    'ASC',
    'ASENSITIVE',
    'ASSERTION',
    'ASSIGNMENT',
    'ASYMMETRIC',
    'AT',
    'ATOMIC',
    'ATTACH',
    'ATTRIBUTE',
    'AUTHORIZATION',
    'BACKWARD',
    'BEFORE',
    'BEGIN',
    'BETWEEN',
    'BIGINT',
    'BINARY',
    'BIT',
    'BOOLEAN',
    'BOTH',
    'BREADTH',
    'BY',
    'CACHE',
    'CALL',
    'CALLED',
    'CASCADE',
    'CASCADED',
    'CASE',
    'CAST',
    'CATALOG',
    'CHAIN',
    'CHAR',
    'CHARACTER',
    'CHARACTERISTICS',
    'CHECK',
    'CHECKPOINT',
    'CLASS',
    'CLOSE',
    'CLUSTER',
    'COALESCE',
    'COLLATE',
    'COLLATION',
    'COLUMN',
    'COLUMNS',
    'COMMENT',
    'COMMENTS',
    'COMMIT',
    'COMMITTED',
    'COMPRESSION',
    'CONCURRENTLY',
    'CONFIGURATION',
    'CONFLICT',
    'CONNECTION',
    'CONSTRAINT',
    'CONSTRAINTS',
    'CONTENT',
    'CONTINUE',
    'CONVERSION',
    'COPY',
    'COST',
    'CREATE',
    'CROSS',
    'CSV',
    'CUBE',
    'CURRENT',
    'CURRENT_CATALOG',
    'CURRENT_DATE',
    'CURRENT_ROLE',
    'CURRENT_SCHEMA',
    'CURRENT_TIME',
    'CURRENT_TIMESTAMP',
    'CURRENT_USER',
    'CURSOR',
    'CYCLE',
    'DATA',
    'DATABASE',
    'DAY',
    'DEALLOCATE',
    'DEC',
    'DECIMAL',
    'DECLARE',
    'DEFAULT',
    'DEFAULTS',
    'DEFERRABLE',
    'DEFERRED',
    'DEFINER',
    'DELETE',
    'DELIMITER',
    'DELIMITERS',
    'DEPENDS',
    'DEPTH',
    'DESC',
    'DETACH',
    'DICTIONARY',
    'DISABLE',
    'DISCARD',
    'DISTINCT',
    'DO',
    'DOCUMENT',
    'DOMAIN',
    'DOUBLE',
    'DROP',
    'EACH',
    'ELSE',
    'ENABLE',
    'ENCODING',
    'ENCRYPTED',
    'END',
    'ENUM',
    'ESCAPE',
    'EVENT',
    'EXCEPT',
    'EXCLUDE',
    'EXCLUDING',
    'EXCLUSIVE',
    'EXECUTE',
    'EXISTS',
    'EXPLAIN',
    'EXPRESSION',
    'EXTENSION',
    'EXTERNAL',
    'EXTRACT',
    'FALSE',
    'FAMILY',
    'FETCH',
    'FILTER',
    'FINALIZE',
    'FIRST',
    'FLOAT',
    'FOLLOWING',
    'FOR',
    'FORCE',
    'FOREIGN',
    'FORWARD',
    'FREEZE',
    'FROM',
    'FULL',
    'FUNCTION',
    'FUNCTIONS',
    'GENERATED',
    'GLOBAL',
    'GRANT',
    'GRANTED',
    'GREATEST',
    'GROUP',
    'GROUPING',
    'GROUPS',
    'HANDLER',
    'HAVING',
    'HEADER',
    'HOLD',
    'HOUR',
    'IDENTITY',
    'IF',
    'ILIKE',
    'IMMEDIATE',
    'IMMUTABLE',
    'IMPLICIT',
    'IMPORT',
    'IN',
    'INCLUDE',
    'INCLUDING',
    'INCREMENT',
    'INDEX',
    'INDEXES',
    'INHERIT',
    'INHERITS',
    'INITIALLY',
    'INLINE',
    'INNER',
    'INOUT',
    'INPUT',
    'INSENSITIVE',
    'INSERT',
    'INSTEAD',
    'INT',
    'INTEGER',
    'INTERSECT',
    'INTERVAL',
    'INTO',
    'INVOKER',
    'IS',
    'ISNULL',
    'ISOLATION',
    'JOIN',
    'KEY',
    'LABEL',
    'LANGUAGE',
    'LARGE',
    'LAST',
    'LATERAL',
    'LEADING',
    'LEAKPROOF',
    'LEAST',
    'LEFT',
    'LEVEL',
    'LIKE',
    'LIMIT',
    'LISTEN',
    'LOAD',
    'LOCAL',
    'LOCALTIME',
    'LOCALTIMESTAMP',
    'LOCATION',
    'LOCK',
    'LOCKED',
    'LOGGED',
    'MAPPING',
    'MATCH',
    'MATERIALIZED',
    'MAXVALUE',
    'METHOD',
    'MINUTE',
    'MINVALUE',
    'MODE',
    'MONTH',
    'MOVE',
    'NAME',
    'NAMES',
    'NATIONAL',
    'NATURAL',
    'NCHAR',
    'NEW',
    'NEXT',
    'NFC',
    'NFD',
    'NFKC',
    'NFKD',
    'NO',
    'NONE',
    'NORMALIZE',
    'NORMALIZED',
    'NOT',
    'NOTHING',
    'NOTIFY',
    'NOTNULL',
    'NOWAIT',
    'NULL',
    'NULLIF',
    'NULLS',
    'NUMERIC',
    'OBJECT',
    'OF',
    'OFF',
    'OFFSET',
    'OIDS',
    'OLD',
    'ON',
    'ONLY',
    'OPERATOR',
    'OPTION',
    'OPTIONS',
    'OR',
    'ORDER',
    'ORDINALITY',
    'OTHERS',
    'OUT',
    'OUTER',
    'OVER',
    'OVERLAPS',
    'OVERLAY',
    'OVERRIDING',
    'OWNED',
    'OWNER',
    'PARALLEL',
    'PARSER',
    'PARTIAL',
    'PARTITION',
    'PASSING',
    'PASSWORD',
    'PLACING',
    'PLANS',
    'POLICY',
    'POSITION',
    'PRECEDING',
    'PRECISION',
    'PREPARE',
    'PREPARED',
    'PRESERVE',
    'PRIMARY',
    'PRIOR',
    'PRIVILEGES',
    'PROCEDURAL',
    'PROCEDURE',
    'PROCEDURES',
    'PROGRAM',
    'PUBLICATION',
    'QUOTE',
    'RANGE',
    'READ',
    'REAL',
    'REASSIGN',
    'RECHECK',
    'RECURSIVE',
    'REF',
    'REFERENCES',
    'REFERENCING',
    'REFRESH',
    'REINDEX',
    'RELATIVE',
    'RELEASE',
    'RENAME',
    'REPEATABLE',
    'REPLACE',
    'REPLICA',
    'RESET',
    'RESTART',
    'RESTRICT',
    'RETURN',
    'RETURNING',
    'RETURNS',
    'REVOKE',
    'RIGHT',
    'ROLE',
    'ROLLBACK',
    'ROLLUP',
    'ROUTINE',
    'ROUTINES',
    'ROW',
    'ROWS',
    'RULE',
    'SAVEPOINT',
    'SCHEMA',
    'SCHEMAS',
    'SCROLL',
    'SEARCH',
    'SECOND',
    'SECURITY',
    'SELECT',
    'SEQUENCE',
    'SEQUENCES',
    'SERIALIZABLE',
    'SERVER',
    'SESSION',
    'SESSION_USER',
    'SET',
    'SETOF',
    'SETS',
    'SHARE',
    'SHOW',
    'SIMILAR',
    'SIMPLE',
    'SKIP',
    'SMALLINT',
    'SNAPSHOT',
    'SOME',
    'SQL',
    'STABLE',
    'STANDALONE',
    'START',
    'STATEMENT',
    'STATISTICS',
    'STDIN',
    'STDOUT',
    'STORAGE',
    'STORED',
    'STRICT',
    'STRIP',
    'SUBSCRIPTION',
    'SUBSTRING',
    'SUPPORT',
    'SYMMETRIC',
    'SYSID',
    'SYSTEM',
    'TABLE',
    'TABLES',
    'TABLESAMPLE',
    'TABLESPACE',
    'TEMP',
    'TEMPLATE',
    'TEMPORARY',
    'TEXT',
    'THEN',
    'TIES',
    'TIME',
    'TIMESTAMP',
    'TO',
    'TRAILING',
    'TRANSACTION',
    'TRANSFORM',
    'TREAT',
    'TRIGGER',
    'TRIM',
    'TRUE',
    'TRUNCATE',
    'TRUSTED',
    'TYPE',
    'TYPES',
    'UESCAPE',
    'UNBOUNDED',
    'UNCOMMITTED',
    'UNENCRYPTED',
    'UNION',
    'UNIQUE',
    'UNKNOWN',
    'UNLISTEN',
    'UNLOGGED',
    'UNTIL',
    'UPDATE',
    'USER',
    'USING',
    'VACUUM',
    'VALID',
    'VALIDATE',
    'VALIDATOR',
    'VALUE',
    'VALUES',
    'VARCHAR',
    'VARIADIC',
    'VARYING',
    'VERBOSE',
    'VERSION',
    'VIEW',
    'VIEWS',
    'VOLATILE',
    'WHEN',
    'WHERE',
    'WHITESPACE',
    'WINDOW',
    'WITH',
    'WITHIN',
    'WITHOUT',
    'WORK',
    'WRAPPER',
    'WRITE',
    'XML',
    'XMLATTRIBUTES',
    'XMLCONCAT',
    'XMLELEMENT',
    'XMLEXISTS',
    'XMLFOREST',
    'XMLNAMESPACES',
    'XMLPARSE',
    'XMLPI',
    'XMLROOT',
    'XMLSERIALIZE',
    'XMLTABLE',
    'YEAR',
    'YES',
    'ZONE',
)

DATATYPES = (
    'bigint',
    'bigserial',
    'bit',
    'bit varying',
    'bool',
    'boolean',
    'box',
    'bytea',
    'char',
    'character',
    'character varying',
    'cidr',
    'circle',
    'date',
    'decimal',
    'double precision',
    'float4',
    'float8',
    'inet',
    'int',
    'int2',
    'int4',
    'int8',
    'integer',
    'interval',
    'json',
    'jsonb',
    'line',
    'lseg',
    'macaddr',
    'macaddr8',
    'money',
    'numeric',
    'path',
    'pg_lsn',
    'pg_snapshot',
    'point',
    'polygon',
    'real',
    'serial',
    'serial2',
    'serial4',
    'serial8',
    'smallint',
    'smallserial',
    'text',
    'time',
    'timestamp',
    'timestamptz',
    'timetz',
    'tsquery',
    'tsvector',
    'txid_snapshot',
    'uuid',
    'varbit',
    'varchar',
    'with time zone',
    'without time zone',
    'xml',
)

PSEUDO_TYPES = (
    'any',
    'anyarray',
    'anycompatible',
    'anycompatiblearray',
    'anycompatiblemultirange',
    'anycompatiblenonarray',
    'anycompatiblerange',
    'anyelement',
    'anyenum',
    'anymultirange',
    'anynonarray',
    'anyrange',
    'cstring',
    'event_trigger',
    'fdw_handler',
    'index_am_handler',
    'internal',
    'language_handler',
    'pg_ddl_command',
    'record',
    'table_am_handler',
    'trigger',
    'tsm_handler',
    'unknown',
    'void',
)

# Remove 'trigger' from types
PSEUDO_TYPES = tuple(sorted(set(PSEUDO_TYPES) - set(map(str.lower, KEYWORDS))))

PLPGSQL_KEYWORDS = (
    'ALIAS', 'CONSTANT', 'DIAGNOSTICS', 'ELSIF', 'EXCEPTION', 'EXIT',
    'FOREACH', 'GET', 'LOOP', 'NOTICE', 'OPEN', 'PERFORM', 'QUERY', 'RAISE',
    'RETURN', 'REVERSE', 'SQLSTATE', 'WHILE',
)

# Most of these keywords are from ExplainNode function
# in src/backend/commands/explain.c

EXPLAIN_KEYWORDS = (
    'Aggregate',
    'Append',
    'Bitmap Heap Scan',
    'Bitmap Index Scan',
    'BitmapAnd',
    'BitmapOr',
    'CTE Scan',
    'Custom Scan',
    'Delete',
    'Foreign Scan',
    'Function Scan',
    'Gather Merge',
    'Gather',
    'Group',
    'GroupAggregate',
    'Hash Join',
    'Hash',
    'HashAggregate',
    'Incremental Sort',
    'Index Only Scan',
    'Index Scan',
    'Insert',
    'Limit',
    'LockRows',
    'Materialize',
    'Memoize',
    'Merge Append',
    'Merge Join',
    'Merge',
    'MixedAggregate',
    'Named Tuplestore Scan',
    'Nested Loop',
    'ProjectSet',
    'Recursive Union',
    'Result',
    'Sample Scan',
    'Seq Scan',
    'SetOp',
    'Sort',
    'SubPlan',
    'Subquery Scan',
    'Table Function Scan',
    'Tid Range Scan',
    'Tid Scan',
    'Unique',
    'Update',
    'Values Scan',
    'WindowAgg',
    'WorkTable Scan',
)


if __name__ == '__main__':  # pragma: no cover
    import re
    from urllib.request import urlopen

    from pygments.util import format_lines

    # One man's constant is another man's variable.
    SOURCE_URL = 'https://github.com/postgres/postgres/raw/master'
    KEYWORDS_URL = SOURCE_URL + '/src/include/parser/kwlist.h'
    DATATYPES_URL = SOURCE_URL + '/doc/src/sgml/datatype.sgml'

    def update_myself():
        content = urlopen(DATATYPES_URL).read().decode('utf-8', errors='ignore')
        data_file = list(content.splitlines())
        datatypes = parse_datatypes(data_file)
        pseudos = parse_pseudos(data_file)

        content = urlopen(KEYWORDS_URL).read().decode('utf-8', errors='ignore')
        keywords = parse_keywords(content)

        update_consts(__file__, 'DATATYPES', datatypes)
        update_consts(__file__, 'PSEUDO_TYPES', pseudos)
        update_consts(__file__, 'KEYWORDS', keywords)

    def parse_keywords(f):
        kw = []
        for m in re.finditer(r'PG_KEYWORD\("(.+?)"', f):
            kw.append(m.group(1).upper())

        if not kw:
            raise ValueError('no keyword found')

        kw.sort()
        return kw

    def parse_datatypes(f):
        dt = set()
        for line in f:
            if '<sect1' in line:
                break
            if '<entry><type>' not in line:
                continue

            # Parse a string such as
            # time [ (<replaceable>p</replaceable>) ] [ without time zone ]
            # into types "time" and "without time zone"

            # remove all the tags
            line = re.sub("<replaceable>[^<]+</replaceable>", "", line)
            line = re.sub("<[^>]+>", "", line)

            # Drop the parts containing braces
            for tmp in [t for tmp in line.split('[')
                        for t in tmp.split(']') if "(" not in t]:
                for t in tmp.split(','):
                    t = t.strip()
                    if not t:
                        continue
                    dt.add(" ".join(t.split()))

        dt = list(dt)
        dt.sort()
        return dt

    def parse_pseudos(f):
        dt = []
        re_start = re.compile(r'\s*<table id="datatype-pseudotypes-table">')
        re_entry = re.compile(r'\s*<entry><type>(.+?)</type></entry>')
        re_end = re.compile(r'\s*</table>')

        f = iter(f)
        for line in f:
            if re_start.match(line) is not None:
                break
        else:
            raise ValueError('pseudo datatypes table not found')

        for line in f:
            m = re_entry.match(line)
            if m is not None:
                dt.append(m.group(1))

            if re_end.match(line) is not None:
                break
        else:
            raise ValueError('end of pseudo datatypes table not found')

        if not dt:
            raise ValueError('pseudo datatypes not found')

        dt.sort()
        return dt

    def update_consts(filename, constname, content):
        with open(filename, encoding='utf-8') as f:
            data = f.read()

        # Line to start/end inserting
        re_match = re.compile(rf'^{constname}\s*=\s*\($.*?^\s*\)$', re.M | re.S)
        m = re_match.search(data)
        if not m:
            raise ValueError(f'Could not find existing definition for {constname}')

        new_block = format_lines(constname, content)
        data = data[:m.start()] + new_block + data[m.end():]

        with open(filename, 'w', encoding='utf-8', newline='\n') as f:
            f.write(data)

    update_myself()

# === NexusCore/openenv\Lib\site-packages\cachetools\__init__.py ===
"""Extensible memoizing collections and decorators."""

__all__ = (
    "Cache",
    "FIFOCache",
    "LFUCache",
    "LRUCache",
    "MRUCache",
    "RRCache",
    "TLRUCache",
    "TTLCache",
    "cached",
    "cachedmethod",
)

__version__ = "5.5.2"

import collections
import collections.abc
import functools
import heapq
import random
import time

from . import keys
from ._decorators import _cached_wrapper


class _DefaultSize:
    __slots__ = ()

    def __getitem__(self, _):
        return 1

    def __setitem__(self, _, value):
        assert value == 1

    def pop(self, _):
        return 1


class Cache(collections.abc.MutableMapping):
    """Mutable mapping to serve as a simple cache or cache base class."""

    __marker = object()

    __size = _DefaultSize()

    def __init__(self, maxsize, getsizeof=None):
        if getsizeof:
            self.getsizeof = getsizeof
        if self.getsizeof is not Cache.getsizeof:
            self.__size = dict()
        self.__data = dict()
        self.__currsize = 0
        self.__maxsize = maxsize

    def __repr__(self):
        return "%s(%s, maxsize=%r, currsize=%r)" % (
            self.__class__.__name__,
            repr(self.__data),
            self.__maxsize,
            self.__currsize,
        )

    def __getitem__(self, key):
        try:
            return self.__data[key]
        except KeyError:
            return self.__missing__(key)

    def __setitem__(self, key, value):
        maxsize = self.__maxsize
        size = self.getsizeof(value)
        if size > maxsize:
            raise ValueError("value too large")
        if key not in self.__data or self.__size[key] < size:
            while self.__currsize + size > maxsize:
                self.popitem()
        if key in self.__data:
            diffsize = size - self.__size[key]
        else:
            diffsize = size
        self.__data[key] = value
        self.__size[key] = size
        self.__currsize += diffsize

    def __delitem__(self, key):
        size = self.__size.pop(key)
        del self.__data[key]
        self.__currsize -= size

    def __contains__(self, key):
        return key in self.__data

    def __missing__(self, key):
        raise KeyError(key)

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    def get(self, key, default=None):
        if key in self:
            return self[key]
        else:
            return default

    def pop(self, key, default=__marker):
        if key in self:
            value = self[key]
            del self[key]
        elif default is self.__marker:
            raise KeyError(key)
        else:
            value = default
        return value

    def setdefault(self, key, default=None):
        if key in self:
            value = self[key]
        else:
            self[key] = value = default
        return value

    @property
    def maxsize(self):
        """The maximum size of the cache."""
        return self.__maxsize

    @property
    def currsize(self):
        """The current size of the cache."""
        return self.__currsize

    @staticmethod
    def getsizeof(value):
        """Return the size of a cache element's value."""
        return 1


class FIFOCache(Cache):
    """First In First Out (FIFO) cache implementation."""

    def __init__(self, maxsize, getsizeof=None):
        Cache.__init__(self, maxsize, getsizeof)
        self.__order = collections.OrderedDict()

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        cache_setitem(self, key, value)
        try:
            self.__order.move_to_end(key)
        except KeyError:
            self.__order[key] = None

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        cache_delitem(self, key)
        del self.__order[key]

    def popitem(self):
        """Remove and return the `(key, value)` pair first inserted."""
        try:
            key = next(iter(self.__order))
        except StopIteration:
            raise KeyError("%s is empty" % type(self).__name__) from None
        else:
            return (key, self.pop(key))


class LFUCache(Cache):
    """Least Frequently Used (LFU) cache implementation."""

    def __init__(self, maxsize, getsizeof=None):
        Cache.__init__(self, maxsize, getsizeof)
        self.__counter = collections.Counter()

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        value = cache_getitem(self, key)
        if key in self:  # __missing__ may not store item
            self.__counter[key] -= 1
        return value

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        cache_setitem(self, key, value)
        self.__counter[key] -= 1

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        cache_delitem(self, key)
        del self.__counter[key]

    def popitem(self):
        """Remove and return the `(key, value)` pair least frequently used."""
        try:
            ((key, _),) = self.__counter.most_common(1)
        except ValueError:
            raise KeyError("%s is empty" % type(self).__name__) from None
        else:
            return (key, self.pop(key))


class LRUCache(Cache):
    """Least Recently Used (LRU) cache implementation."""

    def __init__(self, maxsize, getsizeof=None):
        Cache.__init__(self, maxsize, getsizeof)
        self.__order = collections.OrderedDict()

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        value = cache_getitem(self, key)
        if key in self:  # __missing__ may not store item
            self.__update(key)
        return value

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        cache_setitem(self, key, value)
        self.__update(key)

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        cache_delitem(self, key)
        del self.__order[key]

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used."""
        try:
            key = next(iter(self.__order))
        except StopIteration:
            raise KeyError("%s is empty" % type(self).__name__) from None
        else:
            return (key, self.pop(key))

    def __update(self, key):
        try:
            self.__order.move_to_end(key)
        except KeyError:
            self.__order[key] = None


class MRUCache(Cache):
    """Most Recently Used (MRU) cache implementation."""

    def __init__(self, maxsize, getsizeof=None):
        from warnings import warn

        warn("MRUCache is deprecated", DeprecationWarning, stacklevel=2)

        Cache.__init__(self, maxsize, getsizeof)
        self.__order = collections.OrderedDict()

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        value = cache_getitem(self, key)
        if key in self:  # __missing__ may not store item
            self.__update(key)
        return value

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        cache_setitem(self, key, value)
        self.__update(key)

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        cache_delitem(self, key)
        del self.__order[key]

    def popitem(self):
        """Remove and return the `(key, value)` pair most recently used."""
        try:
            key = next(iter(self.__order))
        except StopIteration:
            raise KeyError("%s is empty" % type(self).__name__) from None
        else:
            return (key, self.pop(key))

    def __update(self, key):
        try:
            self.__order.move_to_end(key, last=False)
        except KeyError:
            self.__order[key] = None


class RRCache(Cache):
    """Random Replacement (RR) cache implementation."""

    def __init__(self, maxsize, choice=random.choice, getsizeof=None):
        Cache.__init__(self, maxsize, getsizeof)
        self.__choice = choice

    @property
    def choice(self):
        """The `choice` function used by the cache."""
        return self.__choice

    def popitem(self):
        """Remove and return a random `(key, value)` pair."""
        try:
            key = self.__choice(list(self))
        except IndexError:
            raise KeyError("%s is empty" % type(self).__name__) from None
        else:
            return (key, self.pop(key))


class _TimedCache(Cache):
    """Base class for time aware cache implementations."""

    class _Timer:
        def __init__(self, timer):
            self.__timer = timer
            self.__nesting = 0

        def __call__(self):
            if self.__nesting == 0:
                return self.__timer()
            else:
                return self.__time

        def __enter__(self):
            if self.__nesting == 0:
                self.__time = time = self.__timer()
            else:
                time = self.__time
            self.__nesting += 1
            return time

        def __exit__(self, *exc):
            self.__nesting -= 1

        def __reduce__(self):
            return _TimedCache._Timer, (self.__timer,)

        def __getattr__(self, name):
            return getattr(self.__timer, name)

    def __init__(self, maxsize, timer=time.monotonic, getsizeof=None):
        Cache.__init__(self, maxsize, getsizeof)
        self.__timer = _TimedCache._Timer(timer)

    def __repr__(self, cache_repr=Cache.__repr__):
        with self.__timer as time:
            self.expire(time)
            return cache_repr(self)

    def __len__(self, cache_len=Cache.__len__):
        with self.__timer as time:
            self.expire(time)
            return cache_len(self)

    @property
    def currsize(self):
        with self.__timer as time:
            self.expire(time)
            return super().currsize

    @property
    def timer(self):
        """The timer function used by the cache."""
        return self.__timer

    def clear(self):
        with self.__timer as time:
            self.expire(time)
            Cache.clear(self)

    def get(self, *args, **kwargs):
        with self.__timer:
            return Cache.get(self, *args, **kwargs)

    def pop(self, *args, **kwargs):
        with self.__timer:
            return Cache.pop(self, *args, **kwargs)

    def setdefault(self, *args, **kwargs):
        with self.__timer:
            return Cache.setdefault(self, *args, **kwargs)


class TTLCache(_TimedCache):
    """LRU Cache implementation with per-item time-to-live (TTL) value."""

    class _Link:
        __slots__ = ("key", "expires", "next", "prev")

        def __init__(self, key=None, expires=None):
            self.key = key
            self.expires = expires

        def __reduce__(self):
            return TTLCache._Link, (self.key, self.expires)

        def unlink(self):
            next = self.next
            prev = self.prev
            prev.next = next
            next.prev = prev

    def __init__(self, maxsize, ttl, timer=time.monotonic, getsizeof=None):
        _TimedCache.__init__(self, maxsize, timer, getsizeof)
        self.__root = root = TTLCache._Link()
        root.prev = root.next = root
        self.__links = collections.OrderedDict()
        self.__ttl = ttl

    def __contains__(self, key):
        try:
            link = self.__links[key]  # no reordering
        except KeyError:
            return False
        else:
            return self.timer() < link.expires

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        try:
            link = self.__getlink(key)
        except KeyError:
            expired = False
        else:
            expired = not (self.timer() < link.expires)
        if expired:
            return self.__missing__(key)
        else:
            return cache_getitem(self, key)

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        with self.timer as time:
            self.expire(time)
            cache_setitem(self, key, value)
        try:
            link = self.__getlink(key)
        except KeyError:
            self.__links[key] = link = TTLCache._Link(key)
        else:
            link.unlink()
        link.expires = time + self.__ttl
        link.next = root = self.__root
        link.prev = prev = root.prev
        prev.next = root.prev = link

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        cache_delitem(self, key)
        link = self.__links.pop(key)
        link.unlink()
        if not (self.timer() < link.expires):
            raise KeyError(key)

    def __iter__(self):
        root = self.__root
        curr = root.next
        while curr is not root:
            # "freeze" time for iterator access
            with self.timer as time:
                if time < curr.expires:
                    yield curr.key
            curr = curr.next

    def __setstate__(self, state):
        self.__dict__.update(state)
        root = self.__root
        root.prev = root.next = root
        for link in sorted(self.__links.values(), key=lambda obj: obj.expires):
            link.next = root
            link.prev = prev = root.prev
            prev.next = root.prev = link
        self.expire(self.timer())

    @property
    def ttl(self):
        """The time-to-live value of the cache's items."""
        return self.__ttl

    def expire(self, time=None):
        """Remove expired items from the cache and return an iterable of the
        expired `(key, value)` pairs.

        """
        if time is None:
            time = self.timer()
        root = self.__root
        curr = root.next
        links = self.__links
        expired = []
        cache_delitem = Cache.__delitem__
        cache_getitem = Cache.__getitem__
        while curr is not root and not (time < curr.expires):
            expired.append((curr.key, cache_getitem(self, curr.key)))
            cache_delitem(self, curr.key)
            del links[curr.key]
            next = curr.next
            curr.unlink()
            curr = next
        return expired

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used that
        has not already expired.

        """
        with self.timer as time:
            self.expire(time)
            try:
                key = next(iter(self.__links))
            except StopIteration:
                raise KeyError("%s is empty" % type(self).__name__) from None
            else:
                return (key, self.pop(key))

    def __getlink(self, key):
        value = self.__links[key]
        self.__links.move_to_end(key)
        return value


class TLRUCache(_TimedCache):
    """Time aware Least Recently Used (TLRU) cache implementation."""

    @functools.total_ordering
    class _Item:
        __slots__ = ("key", "expires", "removed")

        def __init__(self, key=None, expires=None):
            self.key = key
            self.expires = expires
            self.removed = False

        def __lt__(self, other):
            return self.expires < other.expires

    def __init__(self, maxsize, ttu, timer=time.monotonic, getsizeof=None):
        _TimedCache.__init__(self, maxsize, timer, getsizeof)
        self.__items = collections.OrderedDict()
        self.__order = []
        self.__ttu = ttu

    def __contains__(self, key):
        try:
            item = self.__items[key]  # no reordering
        except KeyError:
            return False
        else:
            return self.timer() < item.expires

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        try:
            item = self.__getitem(key)
        except KeyError:
            expired = False
        else:
            expired = not (self.timer() < item.expires)
        if expired:
            return self.__missing__(key)
        else:
            return cache_getitem(self, key)

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        with self.timer as time:
            expires = self.__ttu(key, value, time)
            if not (time < expires):
                return  # skip expired items
            self.expire(time)
            cache_setitem(self, key, value)
        # removing an existing item would break the heap structure, so
        # only mark it as removed for now
        try:
            self.__getitem(key).removed = True
        except KeyError:
            pass
        self.__items[key] = item = TLRUCache._Item(key, expires)
        heapq.heappush(self.__order, item)

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        with self.timer as time:
            # no self.expire() for performance reasons, e.g. self.clear() [#67]
            cache_delitem(self, key)
        item = self.__items.pop(key)
        item.removed = True
        if not (time < item.expires):
            raise KeyError(key)

    def __iter__(self):
        for curr in self.__order:
            # "freeze" time for iterator access
            with self.timer as time:
                if time < curr.expires and not curr.removed:
                    yield curr.key

    @property
    def ttu(self):
        """The local time-to-use function used by the cache."""
        return self.__ttu

    def expire(self, time=None):
        """Remove expired items from the cache and return an iterable of the
        expired `(key, value)` pairs.

        """
        if time is None:
            time = self.timer()
        items = self.__items
        order = self.__order
        # clean up the heap if too many items are marked as removed
        if len(order) > len(items) * 2:
            self.__order = order = [item for item in order if not item.removed]
            heapq.heapify(order)
        expired = []
        cache_delitem = Cache.__delitem__
        cache_getitem = Cache.__getitem__
        while order and (order[0].removed or not (time < order[0].expires)):
            item = heapq.heappop(order)
            if not item.removed:
                expired.append((item.key, cache_getitem(self, item.key)))
                cache_delitem(self, item.key)
                del items[item.key]
        return expired

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used that
        has not already expired.

        """
        with self.timer as time:
            self.expire(time)
            try:
                key = next(iter(self.__items))
            except StopIteration:
                raise KeyError("%s is empty" % self.__class__.__name__) from None
            else:
                return (key, self.pop(key))

    def __getitem(self, key):
        value = self.__items[key]
        self.__items.move_to_end(key)
        return value


_CacheInfo = collections.namedtuple(
    "CacheInfo", ["hits", "misses", "maxsize", "currsize"]
)


def cached(cache, key=keys.hashkey, lock=None, info=False):
    """Decorator to wrap a function with a memoizing callable that saves
    results in a cache.

    """

    def decorator(func):
        if info:
            if isinstance(cache, Cache):

                def make_info(hits, misses):
                    return _CacheInfo(hits, misses, cache.maxsize, cache.currsize)

            elif isinstance(cache, collections.abc.Mapping):

                def make_info(hits, misses):
                    return _CacheInfo(hits, misses, None, len(cache))

            else:

                def make_info(hits, misses):
                    return _CacheInfo(hits, misses, 0, 0)

            wrapper = _cached_wrapper(func, cache, key, lock, make_info)
        else:
            wrapper = _cached_wrapper(func, cache, key, lock, None)

        wrapper.cache = cache
        wrapper.cache_key = key
        wrapper.cache_lock = lock

        return functools.update_wrapper(wrapper, func)

    return decorator


def cachedmethod(cache, key=keys.methodkey, lock=None):
    """Decorator to wrap a class or instance method with a memoizing
    callable that saves results in a cache.

    """

    def decorator(method):
        if lock is None:

            def wrapper(self, *args, **kwargs):
                c = cache(self)
                if c is None:
                    return method(self, *args, **kwargs)
                k = key(self, *args, **kwargs)
                try:
                    return c[k]
                except KeyError:
                    pass  # key not found
                v = method(self, *args, **kwargs)
                try:
                    c[k] = v
                except ValueError:
                    pass  # value too large
                return v

            def clear(self):
                c = cache(self)
                if c is not None:
                    c.clear()

        else:

            def wrapper(self, *args, **kwargs):
                c = cache(self)
                if c is None:
                    return method(self, *args, **kwargs)
                k = key(self, *args, **kwargs)
                try:
                    with lock(self):
                        return c[k]
                except KeyError:
                    pass  # key not found
                v = method(self, *args, **kwargs)
                # in case of a race, prefer the item already in the cache
                try:
                    with lock(self):
                        return c.setdefault(k, v)
                except ValueError:
                    return v  # value too large

            def clear(self):
                c = cache(self)
                if c is not None:
                    with lock(self):
                        c.clear()

        wrapper.cache = cache
        wrapper.cache_key = key
        wrapper.cache_lock = lock
        wrapper.cache_clear = clear

        return functools.update_wrapper(wrapper, method)

    return decorator

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\c_like.py ===
"""
    pygments.lexers.c_like
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for other C-like languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, inherit, words, \
    default
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace

from pygments.lexers.c_cpp import CLexer, CppLexer
from pygments.lexers import _mql_builtins

__all__ = ['PikeLexer', 'NesCLexer', 'ClayLexer', 'ECLexer', 'ValaLexer',
           'CudaLexer', 'SwigLexer', 'MqlLexer', 'ArduinoLexer', 'CharmciLexer',
           'OmgIdlLexer', 'PromelaLexer']


class PikeLexer(CppLexer):
    """
    For `Pike <http://pike.lysator.liu.se/>`_ source code.
    """
    name = 'Pike'
    aliases = ['pike']
    filenames = ['*.pike', '*.pmod']
    mimetypes = ['text/x-pike']
    version_added = '2.0'

    tokens = {
        'statements': [
            (words((
                'catch', 'new', 'private', 'protected', 'public', 'gauge',
                'throw', 'throws', 'class', 'interface', 'implement', 'abstract',
                'extends', 'from', 'this', 'super', 'constant', 'final', 'static',
                'import', 'use', 'extern', 'inline', 'proto', 'break', 'continue',
                'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'as', 'in',
                'version', 'return', 'true', 'false', 'null',
                '__VERSION__', '__MAJOR__', '__MINOR__', '__BUILD__', '__REAL_VERSION__',
                '__REAL_MAJOR__', '__REAL_MINOR__', '__REAL_BUILD__', '__DATE__', '__TIME__',
                '__FILE__', '__DIR__', '__LINE__', '__AUTO_BIGNUM__', '__NT__', '__PIKE__',
                '__amigaos__', '_Pragma', 'static_assert', 'defined', 'sscanf'), suffix=r'\b'),
             Keyword),
            (r'(bool|int|long|float|short|double|char|string|object|void|mapping|'
             r'array|multiset|program|function|lambda|mixed|'
             r'[a-z_][a-z0-9_]*_t)\b',
             Keyword.Type),
            (r'(class)(\s+)', bygroups(Keyword, Whitespace), 'classname'),
            (r'[~!%^&*+=|?:<>/@-]', Operator),
            inherit,
        ],
        'classname': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop'),
            # template specification
            (r'\s*(?=>)', Whitespace, '#pop'),
        ],
    }


class NesCLexer(CLexer):
    """
    For `nesC <https://github.com/tinyos/nesc>`_ source code with preprocessor
    directives.
    """
    name = 'nesC'
    aliases = ['nesc']
    filenames = ['*.nc']
    mimetypes = ['text/x-nescsrc']
    version_added = '2.0'

    tokens = {
        'statements': [
            (words((
                'abstract', 'as', 'async', 'atomic', 'call', 'command', 'component',
                'components', 'configuration', 'event', 'extends', 'generic',
                'implementation', 'includes', 'interface', 'module', 'new', 'norace',
                'post', 'provides', 'signal', 'task', 'uses'), suffix=r'\b'),
             Keyword),
            (words(('nx_struct', 'nx_union', 'nx_int8_t', 'nx_int16_t', 'nx_int32_t',
                    'nx_int64_t', 'nx_uint8_t', 'nx_uint16_t', 'nx_uint32_t',
                    'nx_uint64_t'), suffix=r'\b'),
             Keyword.Type),
            inherit,
        ],
    }


class ClayLexer(RegexLexer):
    """
    For Clay source.
    """
    name = 'Clay'
    filenames = ['*.clay']
    aliases = ['clay']
    mimetypes = ['text/x-clay']
    url = 'http://claylabs.com/clay'
    version_added = '2.0'

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'//.*?$', Comment.Single),
            (r'/(\\\n)?[*](.|\n)*?[*](\\\n)?/', Comment.Multiline),
            (r'\b(public|private|import|as|record|variant|instance'
             r'|define|overload|default|external|alias'
             r'|rvalue|ref|forward|inline|noinline|forceinline'
             r'|enum|var|and|or|not|if|else|goto|return|while'
             r'|switch|case|break|continue|for|in|true|false|try|catch|throw'
             r'|finally|onerror|staticassert|eval|when|newtype'
             r'|__FILE__|__LINE__|__COLUMN__|__ARG__'
             r')\b', Keyword),
            (r'[~!%^&*+=|:<>/-]', Operator),
            (r'[#(){}\[\],;.]', Punctuation),
            (r'0x[0-9a-fA-F]+[LlUu]*', Number.Hex),
            (r'\d+[LlUu]*', Number.Integer),
            (r'\b(true|false)\b', Name.Builtin),
            (r'(?i)[a-z_?][\w?]*', Name),
            (r'"""', String, 'tdqs'),
            (r'"', String, 'dqs'),
        ],
        'strings': [
            (r'(?i)\\(x[0-9a-f]{2}|.)', String.Escape),
            (r'[^\\"]+', String),
        ],
        'nl': [
            (r'\n', String),
        ],
        'dqs': [
            (r'"', String, '#pop'),
            include('strings'),
        ],
        'tdqs': [
            (r'"""', String, '#pop'),
            include('strings'),
            include('nl'),
        ],
    }


class ECLexer(CLexer):
    """
    For eC source code with preprocessor directives.
    """
    name = 'eC'
    aliases = ['ec']
    filenames = ['*.ec', '*.eh']
    mimetypes = ['text/x-echdr', 'text/x-ecsrc']
    url = 'https://ec-lang.org'
    version_added = '1.5'

    tokens = {
        'statements': [
            (words((
                'virtual', 'class', 'private', 'public', 'property', 'import',
                'delete', 'new', 'new0', 'renew', 'renew0', 'define', 'get',
                'set', 'remote', 'dllexport', 'dllimport', 'stdcall', 'subclass',
                '__on_register_module', 'namespace', 'using', 'typed_object',
                'any_object', 'incref', 'register', 'watch', 'stopwatching', 'firewatchers',
                'watchable', 'class_designer', 'class_fixed', 'class_no_expansion', 'isset',
                'class_default_property', 'property_category', 'class_data',
                'class_property', 'thisclass', 'dbtable', 'dbindex',
                'database_open', 'dbfield'), suffix=r'\b'), Keyword),
            (words(('uint', 'uint16', 'uint32', 'uint64', 'bool', 'byte',
                    'unichar', 'int64'), suffix=r'\b'),
             Keyword.Type),
            (r'(class)(\s+)', bygroups(Keyword, Whitespace), 'classname'),
            (r'(null|value|this)\b', Name.Builtin),
            inherit,
        ]
    }


class ValaLexer(RegexLexer):
    """
    For Vala source code with preprocessor directives.
    """
    name = 'Vala'
    aliases = ['vala', 'vapi']
    filenames = ['*.vala', '*.vapi']
    mimetypes = ['text/x-vala']
    url = 'https://vala.dev'
    version_added = '1.1'

    tokens = {
        'whitespace': [
            (r'^\s*#if\s+0', Comment.Preproc, 'if0'),
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
            (r'\\\n', Text),  # line continuation
            (r'//(\n|(.|\n)*?[^\\]\n)', Comment.Single),
            (r'/(\\\n)?[*](.|\n)*?[*](\\\n)?/', Comment.Multiline),
        ],
        'statements': [
            (r'[L@]?"', String, 'string'),
            (r"L?'(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,2}|[^\\\'\n])'",
             String.Char),
            (r'(?s)""".*?"""', String),  # verbatim strings
            (r'(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+[lL]?', Number.Float),
            (r'(\d+\.\d*|\.\d+|\d+[fF])[fF]?', Number.Float),
            (r'0x[0-9a-fA-F]+[Ll]?', Number.Hex),
            (r'0[0-7]+[Ll]?', Number.Oct),
            (r'\d+[Ll]?', Number.Integer),
            (r'[~!%^&*+=|?:<>/-]', Operator),
            (r'(\[)(Compact|Immutable|(?:Boolean|Simple)Type)(\])',
             bygroups(Punctuation, Name.Decorator, Punctuation)),
            # TODO: "correctly" parse complex code attributes
            (r'(\[)(CCode|(?:Integer|Floating)Type)',
             bygroups(Punctuation, Name.Decorator)),
            (r'[()\[\],.]', Punctuation),
            (words((
                'as', 'base', 'break', 'case', 'catch', 'construct', 'continue',
                'default', 'delete', 'do', 'else', 'enum', 'finally', 'for',
                'foreach', 'get', 'if', 'in', 'is', 'lock', 'new', 'out', 'params',
                'return', 'set', 'sizeof', 'switch', 'this', 'throw', 'try',
                'typeof', 'while', 'yield'), suffix=r'\b'),
             Keyword),
            (words((
                'abstract', 'const', 'delegate', 'dynamic', 'ensures', 'extern',
                'inline', 'internal', 'override', 'owned', 'private', 'protected',
                'public', 'ref', 'requires', 'signal', 'static', 'throws', 'unowned',
                'var', 'virtual', 'volatile', 'weak', 'yields'), suffix=r'\b'),
             Keyword.Declaration),
            (r'(namespace|using)(\s+)', bygroups(Keyword.Namespace, Whitespace),
             'namespace'),
            (r'(class|errordomain|interface|struct)(\s+)',
             bygroups(Keyword.Declaration, Whitespace), 'class'),
            (r'(\.)([a-zA-Z_]\w*)',
             bygroups(Operator, Name.Attribute)),
            # void is an actual keyword, others are in glib-2.0.vapi
            (words((
                'void', 'bool', 'char', 'double', 'float', 'int', 'int8', 'int16',
                'int32', 'int64', 'long', 'short', 'size_t', 'ssize_t', 'string',
                'time_t', 'uchar', 'uint', 'uint8', 'uint16', 'uint32', 'uint64',
                'ulong', 'unichar', 'ushort'), suffix=r'\b'),
             Keyword.Type),
            (r'(true|false|null)\b', Name.Builtin),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'root': [
            include('whitespace'),
            default('statement'),
        ],
        'statement': [
            include('whitespace'),
            include('statements'),
            ('[{}]', Punctuation),
            (';', Punctuation, '#pop'),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|[0-7]{1,3})', String.Escape),
            (r'[^\\"\n]+', String),  # all other characters
            (r'\\\n', String),  # line continuation
            (r'\\', String),  # stray backslash
        ],
        'if0': [
            (r'^\s*#if.*?(?<!\\)\n', Comment.Preproc, '#push'),
            (r'^\s*#el(?:se|if).*\n', Comment.Preproc, '#pop'),
            (r'^\s*#endif.*?(?<!\\)\n', Comment.Preproc, '#pop'),
            (r'.*?\n', Comment),
        ],
        'class': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'namespace': [
            (r'[a-zA-Z_][\w.]*', Name.Namespace, '#pop')
        ],
    }


class CudaLexer(CLexer):
    """
    For NVIDIA CUDA™ source.
    """
    name = 'CUDA'
    filenames = ['*.cu', '*.cuh']
    aliases = ['cuda', 'cu']
    mimetypes = ['text/x-cuda']
    url = 'https://developer.nvidia.com/category/zone/cuda-zone'
    version_added = '1.6'

    function_qualifiers = {'__device__', '__global__', '__host__',
                           '__noinline__', '__forceinline__'}
    variable_qualifiers = {'__device__', '__constant__', '__shared__',
                           '__restrict__'}
    vector_types = {'char1', 'uchar1', 'char2', 'uchar2', 'char3', 'uchar3',
                    'char4', 'uchar4', 'short1', 'ushort1', 'short2', 'ushort2',
                    'short3', 'ushort3', 'short4', 'ushort4', 'int1', 'uint1',
                    'int2', 'uint2', 'int3', 'uint3', 'int4', 'uint4', 'long1',
                    'ulong1', 'long2', 'ulong2', 'long3', 'ulong3', 'long4',
                    'ulong4', 'longlong1', 'ulonglong1', 'longlong2',
                    'ulonglong2', 'float1', 'float2', 'float3', 'float4',
                    'double1', 'double2', 'dim3'}
    variables = {'gridDim', 'blockIdx', 'blockDim', 'threadIdx', 'warpSize'}
    functions = {'__threadfence_block', '__threadfence', '__threadfence_system',
                 '__syncthreads', '__syncthreads_count', '__syncthreads_and',
                 '__syncthreads_or'}
    execution_confs = {'<<<', '>>>'}

    def get_tokens_unprocessed(self, text, stack=('root',)):
        for index, token, value in CLexer.get_tokens_unprocessed(self, text, stack):
            if token is Name:
                if value in self.variable_qualifiers:
                    token = Keyword.Type
                elif value in self.vector_types:
                    token = Keyword.Type
                elif value in self.variables:
                    token = Name.Builtin
                elif value in self.execution_confs:
                    token = Keyword.Pseudo
                elif value in self.function_qualifiers:
                    token = Keyword.Reserved
                elif value in self.functions:
                    token = Name.Function
            yield index, token, value


class SwigLexer(CppLexer):
    """
    For `SWIG <http://www.swig.org/>`_ source code.
    """
    name = 'SWIG'
    aliases = ['swig']
    filenames = ['*.swg', '*.i']
    mimetypes = ['text/swig']
    version_added = '2.0'
    priority = 0.04  # Lower than C/C++ and Objective C/C++

    tokens = {
        'root': [
            # Match it here so it won't be matched as a function in the rest of root
            (r'\$\**\&?\w+', Name),
            inherit
        ],
        'statements': [
            # SWIG directives
            (r'(%[a-z_][a-z0-9_]*)', Name.Function),
            # Special variables
            (r'\$\**\&?\w+', Name),
            # Stringification / additional preprocessor directives
            (r'##*[a-zA-Z_]\w*', Comment.Preproc),
            inherit,
        ],
    }

    # This is a far from complete set of SWIG directives
    swig_directives = {
        # Most common directives
        '%apply', '%define', '%director', '%enddef', '%exception', '%extend',
        '%feature', '%fragment', '%ignore', '%immutable', '%import', '%include',
        '%inline', '%insert', '%module', '%newobject', '%nspace', '%pragma',
        '%rename', '%shared_ptr', '%template', '%typecheck', '%typemap',
        # Less common directives
        '%arg', '%attribute', '%bang', '%begin', '%callback', '%catches', '%clear',
        '%constant', '%copyctor', '%csconst', '%csconstvalue', '%csenum',
        '%csmethodmodifiers', '%csnothrowexception', '%default', '%defaultctor',
        '%defaultdtor', '%defined', '%delete', '%delobject', '%descriptor',
        '%exceptionclass', '%exceptionvar', '%extend_smart_pointer', '%fragments',
        '%header', '%ifcplusplus', '%ignorewarn', '%implicit', '%implicitconv',
        '%init', '%javaconst', '%javaconstvalue', '%javaenum', '%javaexception',
        '%javamethodmodifiers', '%kwargs', '%luacode', '%mutable', '%naturalvar',
        '%nestedworkaround', '%perlcode', '%pythonabc', '%pythonappend',
        '%pythoncallback', '%pythoncode', '%pythondynamic', '%pythonmaybecall',
        '%pythonnondynamic', '%pythonprepend', '%refobject', '%shadow', '%sizeof',
        '%trackobjects', '%types', '%unrefobject', '%varargs', '%warn',
        '%warnfilter'}

    def analyse_text(text):
        rv = 0
        # Search for SWIG directives, which are conventionally at the beginning of
        # a line. The probability of them being within a line is low, so let another
        # lexer win in this case.
        matches = re.findall(r'^\s*(%[a-z_][a-z0-9_]*)', text, re.M)
        for m in matches:
            if m in SwigLexer.swig_directives:
                rv = 0.98
                break
            else:
                rv = 0.91  # Fraction higher than MatlabLexer
        return rv


class MqlLexer(CppLexer):
    """
    For `MQL4 <http://docs.mql4.com/>`_ and
    `MQL5 <http://www.mql5.com/en/docs>`_ source code.
    """
    name = 'MQL'
    aliases = ['mql', 'mq4', 'mq5', 'mql4', 'mql5']
    filenames = ['*.mq4', '*.mq5', '*.mqh']
    mimetypes = ['text/x-mql']
    version_added = '2.0'

    tokens = {
        'statements': [
            (words(_mql_builtins.keywords, suffix=r'\b'), Keyword),
            (words(_mql_builtins.c_types, suffix=r'\b'), Keyword.Type),
            (words(_mql_builtins.types, suffix=r'\b'), Name.Function),
            (words(_mql_builtins.constants, suffix=r'\b'), Name.Constant),
            (words(_mql_builtins.colors, prefix='(clr)?', suffix=r'\b'),
             Name.Constant),
            inherit,
        ],
    }


class ArduinoLexer(CppLexer):
    """
    For `Arduino(tm) <https://arduino.cc/>`_ source.

    This is an extension of the CppLexer, as the Arduino® Language is a superset
    of C++
    """

    name = 'Arduino'
    aliases = ['arduino']
    filenames = ['*.ino']
    mimetypes = ['text/x-arduino']
    version_added = '2.1'

    # Language sketch main structure functions
    structure = {'setup', 'loop'}

    # Language operators
    operators = {'not', 'or', 'and', 'xor'}

    # Language 'variables'
    variables = {
        'DIGITAL_MESSAGE', 'FIRMATA_STRING', 'ANALOG_MESSAGE', 'REPORT_DIGITAL',
        'REPORT_ANALOG', 'INPUT_PULLUP', 'SET_PIN_MODE', 'INTERNAL2V56', 'SYSTEM_RESET',
        'LED_BUILTIN', 'INTERNAL1V1', 'SYSEX_START', 'INTERNAL', 'EXTERNAL', 'HIGH',
        'LOW', 'INPUT', 'OUTPUT', 'INPUT_PULLUP', 'LED_BUILTIN', 'true', 'false',
        'void', 'boolean', 'char', 'unsigned char', 'byte', 'int', 'unsigned int',
        'word', 'long', 'unsigned long', 'short', 'float', 'double', 'string', 'String',
        'array', 'static', 'volatile', 'const', 'boolean', 'byte', 'word', 'string',
        'String', 'array', 'int', 'float', 'private', 'char', 'virtual', 'operator',
        'sizeof', 'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t', 'int8_t', 'int16_t',
        'int32_t', 'int64_t', 'dynamic_cast', 'typedef', 'const_cast', 'const',
        'struct', 'static_cast', 'union', 'unsigned', 'long', 'volatile', 'static',
        'protected', 'bool', 'public', 'friend', 'auto', 'void', 'enum', 'extern',
        'class', 'short', 'reinterpret_cast', 'double', 'register', 'explicit',
        'signed', 'inline', 'delete', '_Bool', 'complex', '_Complex', '_Imaginary',
        'atomic_bool', 'atomic_char', 'atomic_schar', 'atomic_uchar', 'atomic_short',
        'atomic_ushort', 'atomic_int', 'atomic_uint', 'atomic_long', 'atomic_ulong',
        'atomic_llong', 'atomic_ullong', 'PROGMEM'}

    # Language shipped functions and class ( )
    functions = {
        'KeyboardController', 'MouseController', 'SoftwareSerial', 'EthernetServer',
        'EthernetClient', 'LiquidCrystal', 'RobotControl', 'GSMVoiceCall',
        'EthernetUDP', 'EsploraTFT', 'HttpClient', 'RobotMotor', 'WiFiClient',
        'GSMScanner', 'FileSystem', 'Scheduler', 'GSMServer', 'YunClient', 'YunServer',
        'IPAddress', 'GSMClient', 'GSMModem', 'Keyboard', 'Ethernet', 'Console',
        'GSMBand', 'Esplora', 'Stepper', 'Process', 'WiFiUDP', 'GSM_SMS', 'Mailbox',
        'USBHost', 'Firmata', 'PImage', 'Client', 'Server', 'GSMPIN', 'FileIO',
        'Bridge', 'Serial', 'EEPROM', 'Stream', 'Mouse', 'Audio', 'Servo', 'File',
        'Task', 'GPRS', 'WiFi', 'Wire', 'TFT', 'GSM', 'SPI', 'SD',
        'runShellCommandAsynchronously', 'analogWriteResolution',
        'retrieveCallingNumber', 'printFirmwareVersion', 'analogReadResolution',
        'sendDigitalPortPair', 'noListenOnLocalhost', 'readJoystickButton',
        'setFirmwareVersion', 'readJoystickSwitch', 'scrollDisplayRight',
        'getVoiceCallStatus', 'scrollDisplayLeft', 'writeMicroseconds',
        'delayMicroseconds', 'beginTransmission', 'getSignalStrength',
        'runAsynchronously', 'getAsynchronously', 'listenOnLocalhost',
        'getCurrentCarrier', 'readAccelerometer', 'messageAvailable',
        'sendDigitalPorts', 'lineFollowConfig', 'countryNameWrite', 'runShellCommand',
        'readStringUntil', 'rewindDirectory', 'readTemperature', 'setClockDivider',
        'readLightSensor', 'endTransmission', 'analogReference', 'detachInterrupt',
        'countryNameRead', 'attachInterrupt', 'encryptionType', 'readBytesUntil',
        'robotNameWrite', 'readMicrophone', 'robotNameRead', 'cityNameWrite',
        'userNameWrite', 'readJoystickY', 'readJoystickX', 'mouseReleased',
        'openNextFile', 'scanNetworks', 'noInterrupts', 'digitalWrite', 'beginSpeaker',
        'mousePressed', 'isActionDone', 'mouseDragged', 'displayLogos', 'noAutoscroll',
        'addParameter', 'remoteNumber', 'getModifiers', 'keyboardRead', 'userNameRead',
        'waitContinue', 'processInput', 'parseCommand', 'printVersion', 'readNetworks',
        'writeMessage', 'blinkVersion', 'cityNameRead', 'readMessage', 'setDataMode',
        'parsePacket', 'isListening', 'setBitOrder', 'beginPacket', 'isDirectory',
        'motorsWrite', 'drawCompass', 'digitalRead', 'clearScreen', 'serialEvent',
        'rightToLeft', 'setTextSize', 'leftToRight', 'requestFrom', 'keyReleased',
        'compassRead', 'analogWrite', 'interrupts', 'WiFiServer', 'disconnect',
        'playMelody', 'parseFloat', 'autoscroll', 'getPINUsed', 'setPINUsed',
        'setTimeout', 'sendAnalog', 'readSlider', 'analogRead', 'beginWrite',
        'createChar', 'motorsStop', 'keyPressed', 'tempoWrite', 'readButton',
        'subnetMask', 'debugPrint', 'macAddress', 'writeGreen', 'randomSeed',
        'attachGPRS', 'readString', 'sendString', 'remotePort', 'releaseAll',
        'mouseMoved', 'background', 'getXChange', 'getYChange', 'answerCall',
        'getResult', 'voiceCall', 'endPacket', 'constrain', 'getSocket', 'writeJSON',
        'getButton', 'available', 'connected', 'findUntil', 'readBytes', 'exitValue',
        'readGreen', 'writeBlue', 'startLoop', 'IPAddress', 'isPressed', 'sendSysex',
        'pauseMode', 'gatewayIP', 'setCursor', 'getOemKey', 'tuneWrite', 'noDisplay',
        'loadImage', 'switchPIN', 'onRequest', 'onReceive', 'changePIN', 'playFile',
        'noBuffer', 'parseInt', 'overflow', 'checkPIN', 'knobRead', 'beginTFT',
        'bitClear', 'updateIR', 'bitWrite', 'position', 'writeRGB', 'highByte',
        'writeRed', 'setSpeed', 'readBlue', 'noStroke', 'remoteIP', 'transfer',
        'shutdown', 'hangCall', 'beginSMS', 'endWrite', 'attached', 'maintain',
        'noCursor', 'checkReg', 'checkPUK', 'shiftOut', 'isValid', 'shiftIn', 'pulseIn',
        'connect', 'println', 'localIP', 'pinMode', 'getIMEI', 'display', 'noBlink',
        'process', 'getBand', 'running', 'beginSD', 'drawBMP', 'lowByte', 'setBand',
        'release', 'bitRead', 'prepare', 'pointTo', 'readRed', 'setMode', 'noFill',
        'remove', 'listen', 'stroke', 'detach', 'attach', 'noTone', 'exists', 'buffer',
        'height', 'bitSet', 'circle', 'config', 'cursor', 'random', 'IRread', 'setDNS',
        'endSMS', 'getKey', 'micros', 'millis', 'begin', 'print', 'write', 'ready',
        'flush', 'width', 'isPIN', 'blink', 'clear', 'press', 'mkdir', 'rmdir', 'close',
        'point', 'yield', 'image', 'BSSID', 'click', 'delay', 'read', 'text', 'move',
        'peek', 'beep', 'rect', 'line', 'open', 'seek', 'fill', 'size', 'turn', 'stop',
        'home', 'find', 'step', 'tone', 'sqrt', 'RSSI', 'SSID', 'end', 'bit', 'tan',
        'cos', 'sin', 'pow', 'map', 'abs', 'max', 'min', 'get', 'run', 'put',
        'isAlphaNumeric', 'isAlpha', 'isAscii', 'isWhitespace', 'isControl', 'isDigit',
        'isGraph', 'isLowerCase', 'isPrintable', 'isPunct', 'isSpace', 'isUpperCase',
        'isHexadecimalDigit'}

    # do not highlight
    suppress_highlight = {
        'namespace', 'template', 'mutable', 'using', 'asm', 'typeid',
        'typename', 'this', 'alignof', 'constexpr', 'decltype', 'noexcept',
        'static_assert', 'thread_local', 'restrict'}

    def get_tokens_unprocessed(self, text, stack=('root',)):
        for index, token, value in CppLexer.get_tokens_unprocessed(self, text, stack):
            if value in self.structure:
                yield index, Name.Builtin, value
            elif value in self.operators:
                yield index, Operator, value
            elif value in self.variables:
                yield index, Keyword.Reserved, value
            elif value in self.suppress_highlight:
                yield index, Name, value
            elif value in self.functions:
                yield index, Name.Function, value
            else:
                yield index, token, value


class CharmciLexer(CppLexer):
    """
    For `Charm++ <https://charm.cs.illinois.edu>`_ interface files (.ci).
    """

    name = 'Charmci'
    aliases = ['charmci']
    filenames = ['*.ci']
    version_added = '2.4'

    mimetypes = []

    tokens = {
        'keywords': [
            (r'(module)(\s+)', bygroups(Keyword, Text), 'classname'),
            (words(('mainmodule', 'mainchare', 'chare', 'array', 'group',
                    'nodegroup', 'message', 'conditional')), Keyword),
            (words(('entry', 'aggregate', 'threaded', 'sync', 'exclusive',
                    'nokeep', 'notrace', 'immediate', 'expedited', 'inline',
                    'local', 'python', 'accel', 'readwrite', 'writeonly',
                    'accelblock', 'memcritical', 'packed', 'varsize',
                    'initproc', 'initnode', 'initcall', 'stacksize',
                    'createhere', 'createhome', 'reductiontarget', 'iget',
                    'nocopy', 'mutable', 'migratable', 'readonly')), Keyword),
            inherit,
        ],
    }


class OmgIdlLexer(CLexer):
    """
    Lexer for Object Management Group Interface Definition Language.
    """

    name = 'OMG Interface Definition Language'
    url = 'https://www.omg.org/spec/IDL/About-IDL/'
    aliases = ['omg-idl']
    filenames = ['*.idl', '*.pidl']
    mimetypes = []
    version_added = '2.9'

    scoped_name = r'((::)?\w+)+'

    tokens = {
        'values': [
            (words(('true', 'false'), prefix=r'(?i)', suffix=r'\b'), Number),
            (r'([Ll]?)(")', bygroups(String.Affix, String.Double), 'string'),
            (r'([Ll]?)(\')(\\[^\']+)(\')',
                bygroups(String.Affix, String.Char, String.Escape, String.Char)),
            (r'([Ll]?)(\')(\\\')(\')',
                bygroups(String.Affix, String.Char, String.Escape, String.Char)),
            (r'([Ll]?)(\'.\')', bygroups(String.Affix, String.Char)),
            (r'[+-]?\d+(\.\d*)?[Ee][+-]?\d+', Number.Float),
            (r'[+-]?(\d+\.\d*)|(\d*\.\d+)([Ee][+-]?\d+)?', Number.Float),
            (r'(?i)[+-]?0x[0-9a-f]+', Number.Hex),
            (r'[+-]?[1-9]\d*', Number.Integer),
            (r'[+-]?0[0-7]*', Number.Oct),
            (r'[\+\-\*\/%^&\|~]', Operator),
            (words(('<<', '>>')), Operator),
            (scoped_name, Name),
            (r'[{};:,<>\[\]]', Punctuation),
        ],
        'annotation_params': [
            include('whitespace'),
            (r'\(', Punctuation, '#push'),
            include('values'),
            (r'=', Punctuation),
            (r'\)', Punctuation, '#pop'),
        ],
        'annotation_params_maybe': [
            (r'\(', Punctuation, 'annotation_params'),
            include('whitespace'),
            default('#pop'),
        ],
        'annotation_appl': [
            (r'@' + scoped_name, Name.Decorator, 'annotation_params_maybe'),
        ],
        'enum': [
            include('whitespace'),
            (r'[{,]', Punctuation),
            (r'\w+', Name.Constant),
            include('annotation_appl'),
            (r'\}', Punctuation, '#pop'),
        ],
        'root': [
            include('whitespace'),
            (words((
                'typedef', 'const',
                'in', 'out', 'inout', 'local',
            ), prefix=r'(?i)', suffix=r'\b'), Keyword.Declaration),
            (words((
                'void', 'any', 'native', 'bitfield',
                'unsigned', 'boolean', 'char', 'wchar', 'octet', 'short', 'long',
                'int8', 'uint8', 'int16', 'int32', 'int64', 'uint16', 'uint32', 'uint64',
                'float', 'double', 'fixed',
                'sequence', 'string', 'wstring', 'map',
            ), prefix=r'(?i)', suffix=r'\b'), Keyword.Type),
            (words((
                '@annotation', 'struct', 'union', 'bitset', 'interface',
                'exception', 'valuetype', 'eventtype', 'component',
            ), prefix=r'(?i)', suffix=r'(\s+)(\w+)'), bygroups(Keyword, Whitespace, Name.Class)),
            (words((
                'abstract', 'alias', 'attribute', 'case', 'connector',
                'consumes', 'context', 'custom', 'default', 'emits', 'factory',
                'finder', 'getraises', 'home', 'import', 'manages', 'mirrorport',
                'multiple', 'Object', 'oneway', 'primarykey', 'private', 'port',
                'porttype', 'provides', 'public', 'publishes', 'raises',
                'readonly', 'setraises', 'supports', 'switch', 'truncatable',
                'typeid', 'typename', 'typeprefix', 'uses', 'ValueBase',
            ), prefix=r'(?i)', suffix=r'\b'), Keyword),
            (r'(?i)(enum|bitmask)(\s+)(\w+)',
                bygroups(Keyword, Whitespace, Name.Class), 'enum'),
            (r'(?i)(module)(\s+)(\w+)',
                bygroups(Keyword.Namespace, Whitespace, Name.Namespace)),
            (r'(\w+)(\s*)(=)', bygroups(Name.Constant, Whitespace, Operator)),
            (r'[\(\)]', Punctuation),
            include('values'),
            include('annotation_appl'),
        ],
    }


class PromelaLexer(CLexer):
    """
    For the Promela language used with SPIN.
    """
    
    name = 'Promela'
    aliases = ['promela']
    filenames = ['*.pml', '*.prom', '*.prm', '*.promela', '*.pr', '*.pm']
    mimetypes = ['text/x-promela']
    url = 'https://spinroot.com/spin/whatispin.html'
    version_added = '2.18'

    # Promela's language reference:
    # https://spinroot.com/spin/Man/promela.html
    # Promela's grammar definition:
    # https://spinroot.com/spin/Man/grammar.html

    tokens = {
        'statements': [
            (r'(\[\]|<>|/\\|\\/)|(U|W|V)\b', Operator), # LTL Operators
            (r'@', Punctuation), #remoterefs
            (r'(\.)([a-zA-Z_]\w*)', bygroups(Operator, Name.Attribute)),
            inherit
        ],
        'types': [
            # Predefined (data types)
            (words((
                'bit', 'bool', 'byte', 'pid', 'short', 'int', 'unsigned'),
                suffix=r'\b'),
             Keyword.Type),
        ],
        'keywords': [
            # ControlFlow
            (words((
                'atomic', 'break', 'd_step', 'do', 'od', 'for', 'in', 'goto',
                'if', 'fi', 'unless'), suffix=r'\b'),
             Keyword),
            # BasicStatements
            (words((
                'assert', 'get_priority', 'printf', 'printm', 'set_priority'),
                suffix=r'\b'),
             Name.Function),
            # Embedded C Code
            (words((
                'c_code', 'c_decl', 'c_expr', 'c_state', 'c_track'),
                suffix=r'\b'),
             Keyword),
            # Predefined (local/global variables)
            (words((
                '_', '_last', '_nr_pr', '_pid', '_priority', 'else', 'np_',
                'STDIN'), suffix=r'\b'),
             Name.Builtin),
            # Predefined (functions)
            (words((
                'empty', 'enabled', 'eval', 'full', 'len', 'nempty', 'nfull',
                'pc_value'), suffix=r'\b'),
             Name.Function),
            # Predefined (operators)
            (r'run\b', Operator.Word),
            # Declarators
            (words((
                'active', 'chan', 'D_proctype', 'hidden', 'init', 'local',
                'mtype', 'never', 'notrace', 'proctype', 'show', 'trace',
                'typedef', 'xr', 'xs'), suffix=r'\b'),
             Keyword.Declaration),
            # Declarators (suffixes)
            (words((
                'priority', 'provided'), suffix=r'\b'),
             Keyword),
            # MetaTerms (declarators)
            (words((
                'inline', 'ltl', 'select'), suffix=r'\b'),
             Keyword.Declaration),
            # MetaTerms (keywords)
            (r'skip\b', Keyword),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\zmq\_future.py ===
"""Future-returning APIs for coroutines."""

# Copyright (c) PyZMQ Developers.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import warnings
from asyncio import Future
from collections import deque
from functools import partial
from itertools import chain
from typing import (
    Any,
    Awaitable,
    Callable,
    NamedTuple,
    TypeVar,
    cast,
)

import zmq as _zmq
from zmq import EVENTS, POLLIN, POLLOUT


class _FutureEvent(NamedTuple):
    future: Future
    kind: str
    args: tuple
    kwargs: dict
    msg: Any
    timer: Any


# These are incomplete classes and need a Mixin for compatibility with an eventloop
# defining the following attributes:
#
# _Future
# _READ
# _WRITE
# _default_loop()


class _Async:
    """Mixin for common async logic"""

    _current_loop: Any = None
    _Future: type[Future]

    def _get_loop(self) -> Any:
        """Get event loop

        Notice if event loop has changed,
        and register init_io_state on activation of a new event loop
        """
        if self._current_loop is None:
            self._current_loop = self._default_loop()
            self._init_io_state(self._current_loop)
            return self._current_loop
        current_loop = self._default_loop()
        if current_loop is not self._current_loop:
            # warn? This means a socket is being used in multiple loops!
            self._current_loop = current_loop
            self._init_io_state(current_loop)
        return current_loop

    def _default_loop(self) -> Any:
        raise NotImplementedError("Must be implemented in a subclass")

    def _init_io_state(self, loop=None) -> None:
        pass


class _AsyncPoller(_Async, _zmq.Poller):
    """Poller that returns a Future on poll, instead of blocking."""

    _socket_class: type[_AsyncSocket]
    _READ: int
    _WRITE: int
    raw_sockets: list[Any]

    def _watch_raw_socket(self, loop: Any, socket: Any, evt: int, f: Callable) -> None:
        """Schedule callback for a raw socket"""
        raise NotImplementedError()

    def _unwatch_raw_sockets(self, loop: Any, *sockets: Any) -> None:
        """Unschedule callback for a raw socket"""
        raise NotImplementedError()

    def poll(self, timeout=-1) -> Awaitable[list[tuple[Any, int]]]:  # type: ignore
        """Return a Future for a poll event"""
        future = self._Future()
        if timeout == 0:
            try:
                result = super().poll(0)
            except Exception as e:
                future.set_exception(e)
            else:
                future.set_result(result)
            return future

        loop = self._get_loop()

        # register Future to be called as soon as any event is available on any socket
        watcher = self._Future()

        # watch raw sockets:
        raw_sockets: list[Any] = []

        def wake_raw(*args):
            if not watcher.done():
                watcher.set_result(None)

        watcher.add_done_callback(
            lambda f: self._unwatch_raw_sockets(loop, *raw_sockets)
        )

        wrapped_sockets: list[_AsyncSocket] = []

        def _clear_wrapper_io(f):
            for s in wrapped_sockets:
                s._clear_io_state()

        for socket, mask in self.sockets:
            if isinstance(socket, _zmq.Socket):
                if not isinstance(socket, self._socket_class):
                    # it's a blocking zmq.Socket, wrap it in async
                    socket = self._socket_class.from_socket(socket)
                    wrapped_sockets.append(socket)
                if mask & _zmq.POLLIN:
                    socket._add_recv_event('poll', future=watcher)
                if mask & _zmq.POLLOUT:
                    socket._add_send_event('poll', future=watcher)
            else:
                raw_sockets.append(socket)
                evt = 0
                if mask & _zmq.POLLIN:
                    evt |= self._READ
                if mask & _zmq.POLLOUT:
                    evt |= self._WRITE
                self._watch_raw_socket(loop, socket, evt, wake_raw)

        def on_poll_ready(f):
            if future.done():
                return
            if watcher.cancelled():
                try:
                    future.cancel()
                except RuntimeError:
                    # RuntimeError may be called during teardown
                    pass
                return
            if watcher.exception():
                future.set_exception(watcher.exception())
            else:
                try:
                    result = super(_AsyncPoller, self).poll(0)
                except Exception as e:
                    future.set_exception(e)
                else:
                    future.set_result(result)

        watcher.add_done_callback(on_poll_ready)

        if wrapped_sockets:
            watcher.add_done_callback(_clear_wrapper_io)

        if timeout is not None and timeout > 0:
            # schedule cancel to fire on poll timeout, if any
            def trigger_timeout():
                if not watcher.done():
                    watcher.set_result(None)

            timeout_handle = loop.call_later(1e-3 * timeout, trigger_timeout)

            def cancel_timeout(f):
                if hasattr(timeout_handle, 'cancel'):
                    timeout_handle.cancel()
                else:
                    loop.remove_timeout(timeout_handle)

            future.add_done_callback(cancel_timeout)

        def cancel_watcher(f):
            if not watcher.done():
                watcher.cancel()

        future.add_done_callback(cancel_watcher)

        return future


class _NoTimer:
    @staticmethod
    def cancel():
        pass


T = TypeVar("T", bound="_AsyncSocket")


class _AsyncSocket(_Async, _zmq.Socket[Future]):
    # Warning : these class variables are only here to allow to call super().__setattr__.
    # They be overridden at instance initialization and not shared in the whole class
    _recv_futures = None
    _send_futures = None
    _state = 0
    _shadow_sock: _zmq.Socket
    _poller_class = _AsyncPoller
    _fd = None

    def __init__(
        self,
        context=None,
        socket_type=-1,
        io_loop=None,
        _from_socket: _zmq.Socket | None = None,
        **kwargs,
    ) -> None:
        if isinstance(context, _zmq.Socket):
            context, _from_socket = (None, context)
        if _from_socket is not None:
            super().__init__(shadow=_from_socket.underlying)  # type: ignore
            self._shadow_sock = _from_socket
        else:
            super().__init__(context, socket_type, **kwargs)  # type: ignore
            self._shadow_sock = _zmq.Socket.shadow(self.underlying)

        if io_loop is not None:
            warnings.warn(
                f"{self.__class__.__name__}(io_loop) argument is deprecated in pyzmq 22.2."
                " The currently active loop will always be used.",
                DeprecationWarning,
                stacklevel=3,
            )
        self._recv_futures = deque()
        self._send_futures = deque()
        self._state = 0
        self._fd = self._shadow_sock.FD

    @classmethod
    def from_socket(cls: type[T], socket: _zmq.Socket, io_loop: Any = None) -> T:
        """Create an async socket from an existing Socket"""
        return cls(_from_socket=socket, io_loop=io_loop)

    def close(self, linger: int | None = None) -> None:
        if not self.closed and self._fd is not None:
            event_list: list[_FutureEvent] = list(
                chain(self._recv_futures or [], self._send_futures or [])
            )
            for event in event_list:
                if not event.future.done():
                    try:
                        event.future.cancel()
                    except RuntimeError:
                        # RuntimeError may be called during teardown
                        pass
            self._clear_io_state()
        super().close(linger=linger)

    close.__doc__ = _zmq.Socket.close.__doc__

    def get(self, key):
        result = super().get(key)
        if key == EVENTS:
            self._schedule_remaining_events(result)
        return result

    get.__doc__ = _zmq.Socket.get.__doc__

    def recv_multipart(
        self, flags: int = 0, copy: bool = True, track: bool = False
    ) -> Awaitable[list[bytes] | list[_zmq.Frame]]:
        """Receive a complete multipart zmq message.

        Returns a Future whose result will be a multipart message.
        """
        return self._add_recv_event(
            'recv_multipart', kwargs=dict(flags=flags, copy=copy, track=track)
        )

    def recv(  # type: ignore
        self, flags: int = 0, copy: bool = True, track: bool = False
    ) -> Awaitable[bytes | _zmq.Frame]:
        """Receive a single zmq frame.

        Returns a Future, whose result will be the received frame.

        Recommend using recv_multipart instead.
        """
        return self._add_recv_event(
            'recv', kwargs=dict(flags=flags, copy=copy, track=track)
        )

    def recv_into(  # type: ignore
        self, buf, /, *, nbytes: int = 0, flags: int = 0
    ) -> Awaitable[int]:
        """Receive a single zmq frame into a pre-allocated buffer.

        Returns a Future, whose result will be the number of bytes received.
        """
        return self._add_recv_event(
            'recv_into', args=(buf,), kwargs=dict(nbytes=nbytes, flags=flags)
        )

    def send_multipart(  # type: ignore
        self, msg_parts: Any, flags: int = 0, copy: bool = True, track=False, **kwargs
    ) -> Awaitable[_zmq.MessageTracker | None]:
        """Send a complete multipart zmq message.

        Returns a Future that resolves when sending is complete.
        """
        kwargs['flags'] = flags
        kwargs['copy'] = copy
        kwargs['track'] = track
        return self._add_send_event('send_multipart', msg=msg_parts, kwargs=kwargs)

    def send(  # type: ignore
        self,
        data: Any,
        flags: int = 0,
        copy: bool = True,
        track: bool = False,
        **kwargs: Any,
    ) -> Awaitable[_zmq.MessageTracker | None]:
        """Send a single zmq frame.

        Returns a Future that resolves when sending is complete.

        Recommend using send_multipart instead.
        """
        kwargs['flags'] = flags
        kwargs['copy'] = copy
        kwargs['track'] = track
        kwargs.update(dict(flags=flags, copy=copy, track=track))
        return self._add_send_event('send', msg=data, kwargs=kwargs)

    def _deserialize(self, recvd, load):
        """Deserialize with Futures"""
        f = self._Future()

        def _chain(_):
            """Chain result through serialization to recvd"""
            if f.done():
                # chained future may be cancelled, which means nobody is going to get this result
                # if it's an error, that's no big deal (probably zmq.Again),
                # but if it's a successful recv, this is a dropped message!
                if not recvd.cancelled() and recvd.exception() is None:
                    warnings.warn(
                        # is there a useful stacklevel?
                        # ideally, it would point to where `f.cancel()` was called
                        f"Future {f} completed while awaiting {recvd}. A message has been dropped!",
                        RuntimeWarning,
                    )
                return
            if recvd.exception():
                f.set_exception(recvd.exception())
            else:
                buf = recvd.result()
                try:
                    loaded = load(buf)
                except Exception as e:
                    f.set_exception(e)
                else:
                    f.set_result(loaded)

        recvd.add_done_callback(_chain)

        def _chain_cancel(_):
            """Chain cancellation from f to recvd"""
            if recvd.done():
                return
            if f.cancelled():
                recvd.cancel()

        f.add_done_callback(_chain_cancel)

        return f

    def poll(self, timeout=None, flags=_zmq.POLLIN) -> Awaitable[int]:  # type: ignore
        """poll the socket for events

        returns a Future for the poll results.
        """

        if self.closed:
            raise _zmq.ZMQError(_zmq.ENOTSUP)

        p = self._poller_class()
        p.register(self, flags)
        poll_future = cast(Future, p.poll(timeout))

        future = self._Future()

        def unwrap_result(f):
            if future.done():
                return
            if poll_future.cancelled():
                try:
                    future.cancel()
                except RuntimeError:
                    # RuntimeError may be called during teardown
                    pass
                return
            if f.exception():
                future.set_exception(poll_future.exception())
            else:
                evts = dict(poll_future.result())
                future.set_result(evts.get(self, 0))

        if poll_future.done():
            # hook up result if already done
            unwrap_result(poll_future)
        else:
            poll_future.add_done_callback(unwrap_result)

        def cancel_poll(future):
            """Cancel underlying poll if request has been cancelled"""
            if not poll_future.done():
                try:
                    poll_future.cancel()
                except RuntimeError:
                    # RuntimeError may be called during teardown
                    pass

        future.add_done_callback(cancel_poll)

        return future

    def _add_timeout(self, future, timeout):
        """Add a timeout for a send or recv Future"""

        def future_timeout():
            if future.done():
                # future already resolved, do nothing
                return

            # raise EAGAIN
            future.set_exception(_zmq.Again())

        return self._call_later(timeout, future_timeout)

    def _call_later(self, delay, callback):
        """Schedule a function to be called later

        Override for different IOLoop implementations

        Tornado and asyncio happen to both have ioloop.call_later
        with the same signature.
        """
        return self._get_loop().call_later(delay, callback)

    @staticmethod
    def _remove_finished_future(future, event_list, event=None):
        """Make sure that futures are removed from the event list when they resolve

        Avoids delaying cleanup until the next send/recv event,
        which may never come.
        """
        # "future" instance is shared between sockets, but each socket has its own event list.
        if not event_list:
            return
        # only unconsumed events (e.g. cancelled calls)
        # will be present when this happens
        try:
            event_list.remove(event)
        except ValueError:
            # usually this will have been removed by being consumed
            return

    def _add_recv_event(
        self,
        kind: str,
        *,
        args: tuple | None = None,
        kwargs: dict[str, Any] | None = None,
        future: Future | None = None,
    ) -> Future:
        """Add a recv event, returning the corresponding Future"""
        f = future or self._Future()
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        if kind.startswith('recv') and kwargs.get('flags', 0) & _zmq.DONTWAIT:
            # short-circuit non-blocking calls
            recv = getattr(self._shadow_sock, kind)
            try:
                r = recv(*args, **kwargs)
            except Exception as e:
                f.set_exception(e)
            else:
                f.set_result(r)
            return f

        timer = _NoTimer
        if hasattr(_zmq, 'RCVTIMEO'):
            timeout_ms = self._shadow_sock.rcvtimeo
            if timeout_ms >= 0:
                timer = self._add_timeout(f, timeout_ms * 1e-3)

        # we add it to the list of futures before we add the timeout as the
        # timeout will remove the future from recv_futures to avoid leaks
        _future_event = _FutureEvent(
            f, kind, args=args, kwargs=kwargs, msg=None, timer=timer
        )
        self._recv_futures.append(_future_event)

        if self._shadow_sock.get(EVENTS) & POLLIN:
            # recv immediately, if we can
            self._handle_recv()
        if self._recv_futures and _future_event in self._recv_futures:
            # Don't let the Future sit in _recv_events after it's done
            # no need to register this if we've already been handled
            # (i.e. immediately-resolved recv)
            f.add_done_callback(
                partial(
                    self._remove_finished_future,
                    event_list=self._recv_futures,
                    event=_future_event,
                )
            )
            self._add_io_state(POLLIN)
        return f

    def _add_send_event(self, kind, msg=None, kwargs=None, future=None):
        """Add a send event, returning the corresponding Future"""
        f = future or self._Future()
        # attempt send with DONTWAIT if no futures are waiting
        # short-circuit for sends that will resolve immediately
        # only call if no send Futures are waiting
        if kind in ('send', 'send_multipart') and not self._send_futures:
            flags = kwargs.get('flags', 0)
            nowait_kwargs = kwargs.copy()
            nowait_kwargs['flags'] = flags | _zmq.DONTWAIT

            # short-circuit non-blocking calls
            send = getattr(self._shadow_sock, kind)
            # track if the send resolved or not
            # (EAGAIN if DONTWAIT is not set should proceed with)
            finish_early = True
            try:
                r = send(msg, **nowait_kwargs)
            except _zmq.Again as e:
                if flags & _zmq.DONTWAIT:
                    f.set_exception(e)
                else:
                    # EAGAIN raised and DONTWAIT not requested,
                    # proceed with async send
                    finish_early = False
            except Exception as e:
                f.set_exception(e)
            else:
                f.set_result(r)

            if finish_early:
                # short-circuit resolved, return finished Future
                # schedule wake for recv if there are any receivers waiting
                if self._recv_futures:
                    self._schedule_remaining_events()
                return f

        timer = _NoTimer
        if hasattr(_zmq, 'SNDTIMEO'):
            timeout_ms = self._shadow_sock.get(_zmq.SNDTIMEO)
            if timeout_ms >= 0:
                timer = self._add_timeout(f, timeout_ms * 1e-3)

        # we add it to the list of futures before we add the timeout as the
        # timeout will remove the future from recv_futures to avoid leaks
        _future_event = _FutureEvent(
            f, kind, args=(), kwargs=kwargs, msg=msg, timer=timer
        )
        self._send_futures.append(_future_event)
        # Don't let the Future sit in _send_futures after it's done
        f.add_done_callback(
            partial(
                self._remove_finished_future,
                event_list=self._send_futures,
                event=_future_event,
            )
        )

        self._add_io_state(POLLOUT)
        return f

    def _handle_recv(self):
        """Handle recv events"""
        if not self._shadow_sock.get(EVENTS) & POLLIN:
            # event triggered, but state may have been changed between trigger and callback
            return
        f = None
        while self._recv_futures:
            f, kind, args, kwargs, _, timer = self._recv_futures.popleft()
            # skip any cancelled futures
            if f.done():
                f = None
            else:
                break

        if not self._recv_futures:
            self._drop_io_state(POLLIN)

        if f is None:
            return

        timer.cancel()

        if kind == 'poll':
            # on poll event, just signal ready, nothing else.
            f.set_result(None)
            return
        elif kind == 'recv_multipart':
            recv = self._shadow_sock.recv_multipart
        elif kind == 'recv':
            recv = self._shadow_sock.recv
        elif kind == 'recv_into':
            recv = self._shadow_sock.recv_into
        else:
            raise ValueError(f"Unhandled recv event type: {kind!r}")

        kwargs['flags'] |= _zmq.DONTWAIT
        try:
            result = recv(*args, **kwargs)
        except Exception as e:
            f.set_exception(e)
        else:
            f.set_result(result)

    def _handle_send(self):
        if not self._shadow_sock.get(EVENTS) & POLLOUT:
            # event triggered, but state may have been changed between trigger and callback
            return
        f = None
        while self._send_futures:
            f, kind, args, kwargs, msg, timer = self._send_futures.popleft()
            # skip any cancelled futures
            if f.done():
                f = None
            else:
                break

        if not self._send_futures:
            self._drop_io_state(POLLOUT)

        if f is None:
            return

        timer.cancel()

        if kind == 'poll':
            # on poll event, just signal ready, nothing else.
            f.set_result(None)
            return
        elif kind == 'send_multipart':
            send = self._shadow_sock.send_multipart
        elif kind == 'send':
            send = self._shadow_sock.send
        else:
            raise ValueError(f"Unhandled send event type: {kind!r}")

        kwargs['flags'] |= _zmq.DONTWAIT
        try:
            result = send(msg, **kwargs)
        except Exception as e:
            f.set_exception(e)
        else:
            f.set_result(result)

    # event masking from ZMQStream
    def _handle_events(self, fd=0, events=0):
        """Dispatch IO events to _handle_recv, etc."""
        if self._shadow_sock.closed:
            return

        zmq_events = self._shadow_sock.get(EVENTS)
        if zmq_events & _zmq.POLLIN:
            self._handle_recv()
        if zmq_events & _zmq.POLLOUT:
            self._handle_send()
        self._schedule_remaining_events()

    def _schedule_remaining_events(self, events=None):
        """Schedule a call to handle_events next loop iteration

        If there are still events to handle.
        """
        # edge-triggered handling
        # allow passing events in, in case this is triggered by retrieving events,
        # so we don't have to retrieve it twice.
        if self._state == 0:
            # not watching for anything, nothing to schedule
            return
        if events is None:
            events = self._shadow_sock.get(EVENTS)
        if events & self._state:
            self._call_later(0, self._handle_events)

    def _add_io_state(self, state):
        """Add io_state to poller."""
        if self._state != state:
            state = self._state = self._state | state
        self._update_handler(self._state)

    def _drop_io_state(self, state):
        """Stop poller from watching an io_state."""
        if self._state & state:
            self._state = self._state & (~state)
        self._update_handler(self._state)

    def _update_handler(self, state):
        """Update IOLoop handler with state.

        zmq FD is always read-only.
        """
        # ensure loop is registered and init_io has been called
        # if there are any events to watch for
        if state:
            self._get_loop()
        self._schedule_remaining_events()

    def _init_io_state(self, loop=None):
        """initialize the ioloop event handler"""
        if loop is None:
            loop = self._get_loop()
        loop.add_handler(self._shadow_sock, self._handle_events, self._READ)
        self._call_later(0, self._handle_events)

    def _clear_io_state(self):
        """unregister the ioloop event handler

        called once during close
        """
        fd = self._shadow_sock
        if self._shadow_sock.closed:
            fd = self._fd
        if self._current_loop is not None:
            self._current_loop.remove_handler(fd)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\win32\defines.py ===
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009-2014, Mario Vilas
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice,this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Common definitions.
"""

# TODO
# + add TCHAR and related types?

__revision__ = "$Id$"

import ctypes
import functools
from winappdbg import compat

# ------------------------------------------------------------------------------

# Some stuff from ctypes we'll be using very frequently.
addressof = ctypes.addressof
sizeof = ctypes.sizeof
SIZEOF = ctypes.sizeof
POINTER = ctypes.POINTER
Structure = ctypes.Structure
Union = ctypes.Union
WINFUNCTYPE = ctypes.WINFUNCTYPE
windll = ctypes.windll

# The IronPython implementation of byref() was giving me problems,
# so I'm replacing it with the slower pointer() function.
try:
    ctypes.c_void_p(ctypes.byref(ctypes.c_char()))  # this fails in IronPython
    byref = ctypes.byref
except TypeError:
    byref = ctypes.pointer

# XXX DEBUG
# The following code can be enabled to make the Win32 API wrappers log to
# standard output the dll and function names, the parameter values and the
# return value for each call.

##WIN32_VERBOSE_MODE = True
WIN32_VERBOSE_MODE = False

if WIN32_VERBOSE_MODE:

    class WinDllHook(object):
        def __getattr__(self, name):
            if name.startswith("_"):
                return object.__getattr__(self, name)
            return WinFuncHook(name)

    class WinFuncHook(object):
        def __init__(self, name):
            self.__name = name

        def __getattr__(self, name):
            if name.startswith("_"):
                return object.__getattr__(self, name)
            return WinCallHook(self.__name, name)

    class WinCallHook(object):
        def __init__(self, dllname, funcname):
            self.__dllname = dllname
            self.__funcname = funcname
            self.__func = getattr(getattr(ctypes.windll, dllname), funcname)

        def __copy_attribute(self, attribute):
            try:
                value = getattr(self, attribute)
                setattr(self.__func, attribute, value)
            except AttributeError:
                try:
                    delattr(self.__func, attribute)
                except AttributeError:
                    pass

        def __call__(self, *argv):
            self.__copy_attribute("argtypes")
            self.__copy_attribute("restype")
            self.__copy_attribute("errcheck")
            print("-" * 10)
            print("%s ! %s %r" % (self.__dllname, self.__funcname, argv))
            retval = self.__func(*argv)
            print("== %r" % (retval,))
            return retval

    windll = WinDllHook()

# ==============================================================================
# This is used later on to calculate the list of exported symbols.
_all = None
_all = set(vars().keys())
# ==============================================================================


def RaiseIfZero(result, func=None, arguments=()):
    """
    Error checking for most Win32 API calls.

    The function is assumed to return an integer, which is C{0} on error.
    In that case the C{WindowsError} exception is raised.
    """
    if not result:
        raise ctypes.WinError()
    return result


def RaiseIfNotZero(result, func=None, arguments=()):
    """
    Error checking for some odd Win32 API calls.

    The function is assumed to return an integer, which is zero on success.
    If the return value is nonzero the C{WindowsError} exception is raised.

    This is mostly useful for free() like functions, where the return value is
    the pointer to the memory block on failure or a C{NULL} pointer on success.
    """
    if result:
        raise ctypes.WinError()
    return result


def RaiseIfNotErrorSuccess(result, func=None, arguments=()):
    """
    Error checking for Win32 Registry API calls.

    The function is assumed to return a Win32 error code. If the code is not
    C{ERROR_SUCCESS} then a C{WindowsError} exception is raised.
    """
    if result != ERROR_SUCCESS:
        raise ctypes.WinError(result)
    return result


class GuessStringType(object):
    """
    Decorator that guesses the correct version (A or W) to call
    based on the types of the strings passed as parameters.

    Calls the B{ANSI} version if the only string types are ANSI.

    Calls the B{Unicode} version if Unicode or mixed string types are passed.

    The default if no string arguments are passed depends on the value of the
    L{t_default} class variable.

    @type fn_ansi: function
    @ivar fn_ansi: ANSI version of the API function to call.
    @type fn_unicode: function
    @ivar fn_unicode: Unicode (wide) version of the API function to call.

    @type t_default: type
    @cvar t_default: Default string type to use.
        Possible values are:
         - type('') for ANSI
         - type(u'') for Unicode
    """

    # ANSI and Unicode types
    t_ansi = type("")
    t_unicode = type("")

    # Default is ANSI for Python 2.x
    t_default = t_ansi

    def __init__(self, fn_ansi, fn_unicode):
        """
        @type  fn_ansi: function
        @param fn_ansi: ANSI version of the API function to call.
        @type  fn_unicode: function
        @param fn_unicode: Unicode (wide) version of the API function to call.
        """
        self.fn_ansi = fn_ansi
        self.fn_unicode = fn_unicode

        # Copy the wrapped function attributes.
        try:
            self.__name__ = self.fn_ansi.__name__[:-1]  # remove the A or W
        except AttributeError:
            pass
        try:
            self.__module__ = self.fn_ansi.__module__
        except AttributeError:
            pass
        try:
            self.__doc__ = self.fn_ansi.__doc__
        except AttributeError:
            pass

    def __call__(self, *argv, **argd):
        # Shortcut to self.t_ansi
        t_ansi = self.t_ansi

        # Get the types of all arguments for the function
        v_types = [type(item) for item in argv]
        v_types.extend([type(value) for (key, value) in compat.iteritems(argd)])

        # Get the appropriate function for the default type
        if self.t_default == t_ansi:
            fn = self.fn_ansi
        else:
            fn = self.fn_unicode

        # If at least one argument is a Unicode string...
        if self.t_unicode in v_types:
            # If al least one argument is an ANSI string,
            # convert all ANSI strings to Unicode
            if t_ansi in v_types:
                argv = list(argv)
                for index in compat.xrange(len(argv)):
                    if v_types[index] == t_ansi:
                        argv[index] = compat.unicode(argv[index])
                for key, value in argd.items():
                    if type(value) == t_ansi:
                        argd[key] = compat.unicode(value)

            # Use the W version
            fn = self.fn_unicode

        # If at least one argument is an ANSI string,
        # but there are no Unicode strings...
        elif t_ansi in v_types:
            # Use the A version
            fn = self.fn_ansi

        # Call the function and return the result
        return fn(*argv, **argd)


class DefaultStringType(object):
    """
    Decorator that uses the default version (A or W) to call
    based on the configuration of the L{GuessStringType} decorator.

    @see: L{GuessStringType.t_default}

    @type fn_ansi: function
    @ivar fn_ansi: ANSI version of the API function to call.
    @type fn_unicode: function
    @ivar fn_unicode: Unicode (wide) version of the API function to call.
    """

    def __init__(self, fn_ansi, fn_unicode):
        """
        @type  fn_ansi: function
        @param fn_ansi: ANSI version of the API function to call.
        @type  fn_unicode: function
        @param fn_unicode: Unicode (wide) version of the API function to call.
        """
        self.fn_ansi = fn_ansi
        self.fn_unicode = fn_unicode

        # Copy the wrapped function attributes.
        try:
            self.__name__ = self.fn_ansi.__name__[:-1]  # remove the A or W
        except AttributeError:
            pass
        try:
            self.__module__ = self.fn_ansi.__module__
        except AttributeError:
            pass
        try:
            self.__doc__ = self.fn_ansi.__doc__
        except AttributeError:
            pass

    def __call__(self, *argv, **argd):
        # Get the appropriate function based on the default.
        if GuessStringType.t_default == GuessStringType.t_ansi:
            fn = self.fn_ansi
        else:
            fn = self.fn_unicode

        # Call the function and return the result
        return fn(*argv, **argd)


def MakeANSIVersion(fn):
    """
    Decorator that generates an ANSI version of a Unicode (wide) only API call.

    @type  fn: callable
    @param fn: Unicode (wide) version of the API function to call.
    """

    @functools.wraps(fn)
    def wrapper(*argv, **argd):
        t_ansi = GuessStringType.t_ansi
        t_unicode = GuessStringType.t_unicode
        v_types = [type(item) for item in argv]
        v_types.extend([type(value) for (key, value) in compat.iteritems(argd)])
        if t_ansi in v_types:
            argv = list(argv)
            for index in compat.xrange(len(argv)):
                if v_types[index] == t_ansi:
                    argv[index] = t_unicode(argv[index])
            for key, value in argd.items():
                if type(value) == t_ansi:
                    argd[key] = t_unicode(value)
        return fn(*argv, **argd)

    return wrapper


def MakeWideVersion(fn):
    """
    Decorator that generates a Unicode (wide) version of an ANSI only API call.

    @type  fn: callable
    @param fn: ANSI version of the API function to call.
    """

    @functools.wraps(fn)
    def wrapper(*argv, **argd):
        t_ansi = GuessStringType.t_ansi
        t_unicode = GuessStringType.t_unicode
        v_types = [type(item) for item in argv]
        v_types.extend([type(value) for (key, value) in compat.iteritems(argd)])
        if t_unicode in v_types:
            argv = list(argv)
            for index in compat.xrange(len(argv)):
                if v_types[index] == t_unicode:
                    argv[index] = t_ansi(argv[index])
            for key, value in argd.items():
                if type(value) == t_unicode:
                    argd[key] = t_ansi(value)
        return fn(*argv, **argd)

    return wrapper


# --- Types --------------------------------------------------------------------
# http://msdn.microsoft.com/en-us/library/aa383751(v=vs.85).aspx

# Map of basic C types to Win32 types
LPVOID = ctypes.c_void_p
CHAR = ctypes.c_char
WCHAR = ctypes.c_wchar
BYTE = ctypes.c_ubyte
SBYTE = ctypes.c_byte
WORD = ctypes.c_uint16
SWORD = ctypes.c_int16
DWORD = ctypes.c_uint32
SDWORD = ctypes.c_int32
QWORD = ctypes.c_uint64
SQWORD = ctypes.c_int64
SHORT = ctypes.c_short
USHORT = ctypes.c_ushort
INT = ctypes.c_int
UINT = ctypes.c_uint
LONG = ctypes.c_long
ULONG = ctypes.c_ulong
LONGLONG = ctypes.c_int64  # c_longlong
ULONGLONG = ctypes.c_uint64  # c_ulonglong
LPSTR = ctypes.c_char_p
LPWSTR = ctypes.c_wchar_p
INT8 = ctypes.c_int8
INT16 = ctypes.c_int16
INT32 = ctypes.c_int32
INT64 = ctypes.c_int64
UINT8 = ctypes.c_uint8
UINT16 = ctypes.c_uint16
UINT32 = ctypes.c_uint32
UINT64 = ctypes.c_uint64
LONG32 = ctypes.c_int32
LONG64 = ctypes.c_int64
ULONG32 = ctypes.c_uint32
ULONG64 = ctypes.c_uint64
DWORD32 = ctypes.c_uint32
DWORD64 = ctypes.c_uint64
BOOL = ctypes.c_int
FLOAT = ctypes.c_float

# Map size_t to SIZE_T
try:
    SIZE_T = ctypes.c_size_t
    SSIZE_T = ctypes.c_ssize_t
except AttributeError:
    # Size of a pointer
    SIZE_T = {1: BYTE, 2: WORD, 4: DWORD, 8: QWORD}[sizeof(LPVOID)]
    SSIZE_T = {1: SBYTE, 2: SWORD, 4: SDWORD, 8: SQWORD}[sizeof(LPVOID)]
PSIZE_T = POINTER(SIZE_T)

# Not really pointers but pointer-sized integers
DWORD_PTR = SIZE_T
ULONG_PTR = SIZE_T
LONG_PTR = SIZE_T

# Other Win32 types, more may be added as needed
PVOID = LPVOID
PPVOID = POINTER(PVOID)
PSTR = LPSTR
PWSTR = LPWSTR
PCHAR = LPSTR
PWCHAR = LPWSTR
LPBYTE = POINTER(BYTE)
LPSBYTE = POINTER(SBYTE)
LPWORD = POINTER(WORD)
LPSWORD = POINTER(SWORD)
LPDWORD = POINTER(DWORD)
LPSDWORD = POINTER(SDWORD)
LPULONG = POINTER(ULONG)
LPLONG = POINTER(LONG)
PDWORD = LPDWORD
PDWORD_PTR = POINTER(DWORD_PTR)
PULONG = LPULONG
PLONG = LPLONG
CCHAR = CHAR
BOOLEAN = BYTE
PBOOL = POINTER(BOOL)
LPBOOL = PBOOL
TCHAR = CHAR  # XXX ANSI by default?
UCHAR = BYTE
DWORDLONG = ULONGLONG
LPDWORD32 = POINTER(DWORD32)
LPULONG32 = POINTER(ULONG32)
LPDWORD64 = POINTER(DWORD64)
LPULONG64 = POINTER(ULONG64)
PDWORD32 = LPDWORD32
PULONG32 = LPULONG32
PDWORD64 = LPDWORD64
PULONG64 = LPULONG64
ATOM = WORD
HANDLE = LPVOID
PHANDLE = POINTER(HANDLE)
LPHANDLE = PHANDLE
HMODULE = HANDLE
HINSTANCE = HANDLE
HTASK = HANDLE
HKEY = HANDLE
PHKEY = POINTER(HKEY)
HDESK = HANDLE
HRSRC = HANDLE
HSTR = HANDLE
HWINSTA = HANDLE
HKL = HANDLE
HDWP = HANDLE
HFILE = HANDLE
HRESULT = LONG
HGLOBAL = HANDLE
HLOCAL = HANDLE
HGDIOBJ = HANDLE
HDC = HGDIOBJ
HRGN = HGDIOBJ
HBITMAP = HGDIOBJ
HPALETTE = HGDIOBJ
HPEN = HGDIOBJ
HBRUSH = HGDIOBJ
HMF = HGDIOBJ
HEMF = HGDIOBJ
HENHMETAFILE = HGDIOBJ
HMETAFILE = HGDIOBJ
HMETAFILEPICT = HGDIOBJ
HWND = HANDLE
NTSTATUS = LONG
PNTSTATUS = POINTER(NTSTATUS)
KAFFINITY = ULONG_PTR
RVA = DWORD
RVA64 = QWORD
WPARAM = DWORD
LPARAM = LPVOID
LRESULT = LPVOID
ACCESS_MASK = DWORD
REGSAM = ACCESS_MASK
PACCESS_MASK = POINTER(ACCESS_MASK)
PREGSAM = POINTER(REGSAM)

# Since the SID is an opaque structure, let's treat its pointers as void*
PSID = PVOID

# typedef union _LARGE_INTEGER {
#   struct {
#     DWORD LowPart;
#     LONG HighPart;
#   } ;
#   struct {
#     DWORD LowPart;
#     LONG HighPart;
#   } u;
#   LONGLONG QuadPart;
# } LARGE_INTEGER,
#  *PLARGE_INTEGER;

# XXX TODO


# typedef struct _FLOAT128 {
#     __int64 LowPart;
#     __int64 HighPart;
# } FLOAT128;
class FLOAT128(Structure):
    _fields_ = [
        ("LowPart", QWORD),
        ("HighPart", QWORD),
    ]


PFLOAT128 = POINTER(FLOAT128)


# typedef struct DECLSPEC_ALIGN(16) _M128A {
#     ULONGLONG Low;
#     LONGLONG High;
# } M128A, *PM128A;
class M128A(Structure):
    _fields_ = [
        ("Low", ULONGLONG),
        ("High", LONGLONG),
    ]


PM128A = POINTER(M128A)

# --- Constants ----------------------------------------------------------------

NULL = None
INFINITE = -1
TRUE = 1
FALSE = 0

# http://blogs.msdn.com/oldnewthing/archive/2004/08/26/220873.aspx
ANYSIZE_ARRAY = 1

# Invalid handle value is -1 casted to void pointer.
try:
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value  # -1 #0xFFFFFFFF
except TypeError:
    if sizeof(ctypes.c_void_p) == 4:
        INVALID_HANDLE_VALUE = 0xFFFFFFFF
    elif sizeof(ctypes.c_void_p) == 8:
        INVALID_HANDLE_VALUE = 0xFFFFFFFFFFFFFFFF
    else:
        raise

MAX_MODULE_NAME32 = 255
MAX_PATH = 260

# Error codes
# TODO maybe add more error codes?
# if they're too many they could be pickled instead,
# or at the very least put in a new file
ERROR_SUCCESS = 0
ERROR_INVALID_FUNCTION = 1
ERROR_FILE_NOT_FOUND = 2
ERROR_PATH_NOT_FOUND = 3
ERROR_ACCESS_DENIED = 5
ERROR_INVALID_HANDLE = 6
ERROR_NOT_ENOUGH_MEMORY = 8
ERROR_INVALID_DRIVE = 15
ERROR_NO_MORE_FILES = 18
ERROR_BAD_LENGTH = 24
ERROR_HANDLE_EOF = 38
ERROR_HANDLE_DISK_FULL = 39
ERROR_NOT_SUPPORTED = 50
ERROR_FILE_EXISTS = 80
ERROR_INVALID_PARAMETER = 87
ERROR_BUFFER_OVERFLOW = 111
ERROR_DISK_FULL = 112
ERROR_CALL_NOT_IMPLEMENTED = 120
ERROR_SEM_TIMEOUT = 121
ERROR_INSUFFICIENT_BUFFER = 122
ERROR_INVALID_NAME = 123
ERROR_MOD_NOT_FOUND = 126
ERROR_PROC_NOT_FOUND = 127
ERROR_DIR_NOT_EMPTY = 145
ERROR_BAD_THREADID_ADDR = 159
ERROR_BAD_ARGUMENTS = 160
ERROR_BAD_PATHNAME = 161
ERROR_ALREADY_EXISTS = 183
ERROR_INVALID_FLAG_NUMBER = 186
ERROR_ENVVAR_NOT_FOUND = 203
ERROR_FILENAME_EXCED_RANGE = 206
ERROR_MORE_DATA = 234

WAIT_TIMEOUT = 258

ERROR_NO_MORE_ITEMS = 259
ERROR_PARTIAL_COPY = 299
ERROR_INVALID_ADDRESS = 487
ERROR_THREAD_NOT_IN_PROCESS = 566
ERROR_CONTROL_C_EXIT = 572
ERROR_UNHANDLED_EXCEPTION = 574
ERROR_ASSERTION_FAILURE = 668
ERROR_WOW_ASSERTION = 670

ERROR_DBG_EXCEPTION_NOT_HANDLED = 688
ERROR_DBG_REPLY_LATER = 689
ERROR_DBG_UNABLE_TO_PROVIDE_HANDLE = 690
ERROR_DBG_TERMINATE_THREAD = 691
ERROR_DBG_TERMINATE_PROCESS = 692
ERROR_DBG_CONTROL_C = 693
ERROR_DBG_PRINTEXCEPTION_C = 694
ERROR_DBG_RIPEXCEPTION = 695
ERROR_DBG_CONTROL_BREAK = 696
ERROR_DBG_COMMAND_EXCEPTION = 697
ERROR_DBG_EXCEPTION_HANDLED = 766
ERROR_DBG_CONTINUE = 767

ERROR_ELEVATION_REQUIRED = 740
ERROR_NOACCESS = 998

ERROR_CIRCULAR_DEPENDENCY = 1059
ERROR_SERVICE_DOES_NOT_EXIST = 1060
ERROR_SERVICE_CANNOT_ACCEPT_CTRL = 1061
ERROR_SERVICE_NOT_ACTIVE = 1062
ERROR_FAILED_SERVICE_CONTROLLER_CONNECT = 1063
ERROR_EXCEPTION_IN_SERVICE = 1064
ERROR_DATABASE_DOES_NOT_EXIST = 1065
ERROR_SERVICE_SPECIFIC_ERROR = 1066
ERROR_PROCESS_ABORTED = 1067
ERROR_SERVICE_DEPENDENCY_FAIL = 1068
ERROR_SERVICE_LOGON_FAILED = 1069
ERROR_SERVICE_START_HANG = 1070
ERROR_INVALID_SERVICE_LOCK = 1071
ERROR_SERVICE_MARKED_FOR_DELETE = 1072
ERROR_SERVICE_EXISTS = 1073
ERROR_ALREADY_RUNNING_LKG = 1074
ERROR_SERVICE_DEPENDENCY_DELETED = 1075
ERROR_BOOT_ALREADY_ACCEPTED = 1076
ERROR_SERVICE_NEVER_STARTED = 1077
ERROR_DUPLICATE_SERVICE_NAME = 1078
ERROR_DIFFERENT_SERVICE_ACCOUNT = 1079
ERROR_CANNOT_DETECT_DRIVER_FAILURE = 1080
ERROR_CANNOT_DETECT_PROCESS_ABORT = 1081
ERROR_NO_RECOVERY_PROGRAM = 1082
ERROR_SERVICE_NOT_IN_EXE = 1083
ERROR_NOT_SAFEBOOT_SERVICE = 1084

ERROR_DEBUGGER_INACTIVE = 1284

ERROR_PRIVILEGE_NOT_HELD = 1314

ERROR_NONE_MAPPED = 1332

RPC_S_SERVER_UNAVAILABLE = 1722

# Standard access rights
import sys

if sys.version_info[0] >= 3:
    long = int

DELETE = long(0x00010000)
READ_CONTROL = long(0x00020000)
WRITE_DAC = long(0x00040000)
WRITE_OWNER = long(0x00080000)
SYNCHRONIZE = long(0x00100000)
STANDARD_RIGHTS_REQUIRED = long(0x000F0000)
STANDARD_RIGHTS_READ = READ_CONTROL
STANDARD_RIGHTS_WRITE = READ_CONTROL
STANDARD_RIGHTS_EXECUTE = READ_CONTROL
STANDARD_RIGHTS_ALL = long(0x001F0000)
SPECIFIC_RIGHTS_ALL = long(0x0000FFFF)

# --- Structures ---------------------------------------------------------------


# typedef struct _LSA_UNICODE_STRING {
#   USHORT Length;
#   USHORT MaximumLength;
#   PWSTR Buffer;
# } LSA_UNICODE_STRING,
#  *PLSA_UNICODE_STRING,
#  UNICODE_STRING,
#  *PUNICODE_STRING;
class UNICODE_STRING(Structure):
    _fields_ = [
        ("Length", USHORT),
        ("MaximumLength", USHORT),
        ("Buffer", PVOID),
    ]


# From MSDN:
#
# typedef struct _GUID {
#   DWORD Data1;
#   WORD Data2;
#   WORD Data3;
#   BYTE Data4[8];
# } GUID;
class GUID(Structure):
    _fields_ = [
        ("Data1", DWORD),
        ("Data2", WORD),
        ("Data3", WORD),
        ("Data4", BYTE * 8),
    ]


# From MSDN:
#
# typedef struct _LIST_ENTRY {
#     struct _LIST_ENTRY *Flink;
#     struct _LIST_ENTRY *Blink;
# } LIST_ENTRY, *PLIST_ENTRY, *RESTRICTED_POINTER PRLIST_ENTRY;
class LIST_ENTRY(Structure):
    _fields_ = [
        ("Flink", PVOID),  # POINTER(LIST_ENTRY)
        ("Blink", PVOID),  # POINTER(LIST_ENTRY)
    ]


# ==============================================================================
# This calculates the list of exported symbols.
_all = set(vars().keys()).difference(_all)
##__all__ = [_x for _x in _all if not _x.startswith('_')]
##__all__.sort()
# ==============================================================================

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\display\point\point.py ===
import hashlib
import io
import os
import subprocess
from typing import List

import cv2
import nltk
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageEnhance, ImageFont
from sentence_transformers import SentenceTransformer, util

from .....terminal_interface.utils.oi_dir import oi_dir
from ...utils.computer_vision import pytesseract_get_text_bounding_boxes

try:
    nltk.corpus.words.words()
except LookupError:
    nltk.download("words", quiet=True)
from nltk.corpus import words

# Create a set of English words
english_words = set(words.words())


def take_screenshot_to_pil(filename="temp_screenshot.png"):
    # Capture the screenshot and save it to a temporary file
    subprocess.run(["screencapture", "-x", filename], check=True)

    # Open the image file with PIL
    with open(filename, "rb") as f:
        image_data = f.read()
    image = Image.open(io.BytesIO(image_data))

    # Optionally, delete the temporary file if you don't need it after loading
    os.remove(filename)

    return image


from ...utils.computer_vision import find_text_in_image


def point(description, screenshot=None, debug=False, hashes=None):
    if description.startswith('"') and description.endswith('"'):
        return find_text_in_image(description.strip('"'), screenshot, debug)
    else:
        return find_icon(description, screenshot, debug, hashes)


def find_icon(description, screenshot=None, debug=False, hashes=None):
    if debug:
        print("STARTING")
    if screenshot == None:
        image_data = take_screenshot_to_pil()
    else:
        image_data = screenshot

    if hashes == None:
        hashes = {}

    image_width, image_height = image_data.size

    # Create a temporary file to save the image data
    #   with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
    #     temp_file.write(base64.b64decode(request.base64))
    #     temp_image_path = temp_file.name
    #   print("yeah took", time.time()-thetime)

    icons_bounding_boxes = get_element_boxes(image_data, debug)

    if debug:
        print("GOT ICON BOUNDING BOXES")

    debug_path = os.path.join(os.path.expanduser("~"), "Desktop", "oi-debug")

    if debug:
        # Create a draw object
        image_data_copy = image_data.copy()
        draw = ImageDraw.Draw(image_data_copy)
        # Draw red rectangles around all blocks
        for block in icons_bounding_boxes:
            left, top, width, height = (
                block["x"],
                block["y"],
                block["width"],
                block["height"],
            )
            draw.rectangle([(left, top), (left + width, top + height)], outline="red")
        image_data_copy.save(
            os.path.join(debug_path, "before_filtering_out_extremes.png")
        )

    # Filter out extremes
    min_icon_width = int(os.getenv("OI_POINT_MIN_ICON_WIDTH", "10"))
    max_icon_width = int(os.getenv("OI_POINT_MAX_ICON_WIDTH", "500"))
    min_icon_height = int(os.getenv("OI_POINT_MIN_ICON_HEIGHT", "10"))
    max_icon_height = int(os.getenv("OI_POINT_MAX_ICON_HEIGHT", "500"))
    icons_bounding_boxes = [
        box
        for box in icons_bounding_boxes
        if min_icon_width <= box["width"] <= max_icon_width
        and min_icon_height <= box["height"] <= max_icon_height
    ]

    if debug:
        # Create a draw object
        image_data_copy = image_data.copy()
        draw = ImageDraw.Draw(image_data_copy)
        # Draw red rectangles around all blocks
        for block in icons_bounding_boxes:
            left, top, width, height = (
                block["x"],
                block["y"],
                block["width"],
                block["height"],
            )
            draw.rectangle([(left, top), (left + width, top + height)], outline="red")
        image_data_copy.save(
            os.path.join(debug_path, "after_filtering_out_extremes.png")
        )

    # Compute center_x and center_y for each box
    for box in icons_bounding_boxes:
        box["center_x"] = box["x"] + box["width"] / 2
        box["center_y"] = box["y"] + box["height"] / 2

    # # Filter out text

    if debug:
        print("GETTING TEXT")

    response = pytesseract_get_text_bounding_boxes(screenshot)

    if debug:
        print("GOT TEXT, processing it")

    if debug:
        # Create a draw object
        image_data_copy = image_data.copy()
        draw = ImageDraw.Draw(image_data_copy)
        # Draw red rectangles around all blocks
        for block in response:
            left, top, width, height = (
                block["left"],
                block["top"],
                block["width"],
                block["height"],
            )
            draw.rectangle([(left, top), (left + width, top + height)], outline="blue")

        # Save the image to the desktop
        if not os.path.exists(debug_path):
            os.makedirs(debug_path)
        image_data_copy.save(os.path.join(debug_path, "pytesseract_blocks_image.png"))

    blocks = [
        b for b in response if len(b["text"]) > 2
    ]  # icons are sometimes text, like "X"

    # Filter blocks so the text.lower() needs to be a real word in the English dictionary
    filtered_blocks = []
    for b in blocks:
        words = b["text"].lower().split()
        words = [
            "".join(e for e in word if e.isalnum()) for word in words
        ]  # remove punctuation
        if all(word in english_words for word in words):
            filtered_blocks.append(b)
    blocks = filtered_blocks

    if debug:
        # Create a draw object
        image_data_copy = image_data.copy()
        draw = ImageDraw.Draw(image_data_copy)
        # Draw red rectangles around all blocks
        for block in blocks:
            left, top, width, height = (
                block["left"],
                block["top"],
                block["width"],
                block["height"],
            )
            draw.rectangle([(left, top), (left + width, top + height)], outline="green")
        image_data_copy.save(
            os.path.join(debug_path, "pytesseract_filtered_blocks_image.png")
        )

    if debug:
        # Create a draw object
        image_data_copy = image_data.copy()
        draw = ImageDraw.Draw(image_data_copy)
        # Draw red rectangles around all blocks
        for block in blocks:
            left, top, width, height = (
                block["left"],
                block["top"],
                block["width"],
                block["height"],
            )
            draw.rectangle([(left, top), (left + width, top + height)], outline="green")
            # Draw the detected text in the rectangle in small font
            # Use PIL's built-in bitmap font
            font = ImageFont.load_default()
            draw.text(
                (block["left"], block["top"]), block["text"], fill="red", font=font
            )
        image_data_copy.save(
            os.path.join(debug_path, "pytesseract_filtered_blocks_image_with_text.png")
        )

    # Create an empty list to store the filtered boxes
    filtered_boxes = []

    # Filter out boxes that fall inside text
    for box in icons_bounding_boxes:
        if not any(
            text_box["left"] <= box["x"] <= text_box["left"] + text_box["width"]
            and text_box["top"] <= box["y"] <= text_box["top"] + text_box["height"]
            and text_box["left"]
            <= box["x"] + box["width"]
            <= text_box["left"] + text_box["width"]
            and text_box["top"]
            <= box["y"] + box["height"]
            <= text_box["top"] + text_box["height"]
            for text_box in blocks
        ):
            filtered_boxes.append(box)
        else:
            pass
            # print("Filtered out an icon because I think it is text.")

    icons_bounding_boxes = filtered_boxes

    if debug:
        # Create a copy of the image data
        image_data_copy = image_data.copy()
        draw = ImageDraw.Draw(image_data_copy)
        # Draw green rectangles around all filtered boxes
        for box in filtered_boxes:
            left, top, width, height = (
                box["x"],
                box["y"],
                box["width"],
                box["height"],
            )
            draw.rectangle([(left, top), (left + width, top + height)], outline="green")
        # Save the image with the drawn rectangles
        image_data_copy.save(
            os.path.join(debug_path, "pytesseract_filtered_boxes_image.png")
        )

    # Filter out boxes that intersect with text at all
    filtered_boxes = []
    for box in icons_bounding_boxes:
        if not any(
            max(text_box["left"], box["x"])
            < min(text_box["left"] + text_box["width"], box["x"] + box["width"])
            and max(text_box["top"], box["y"])
            < min(text_box["top"] + text_box["height"], box["y"] + box["height"])
            for text_box in blocks
        ):
            filtered_boxes.append(box)
    icons_bounding_boxes = filtered_boxes

    if debug:
        # Create a copy of the image data
        image_data_copy = image_data.copy()
        draw = ImageDraw.Draw(image_data_copy)
        # Draw green rectangles around all filtered boxes
        for box in icons_bounding_boxes:
            left, top, width, height = (
                box["x"],
                box["y"],
                box["width"],
                box["height"],
            )
            draw.rectangle([(left, top), (left + width, top + height)], outline="green")
        # Save the image with the drawn rectangles
        image_data_copy.save(
            os.path.join(debug_path, "debug_image_after_filtering_boxes.png")
        )

    # # (DISABLED)
    # # Filter to the most icon-like dimensions

    # # Desired dimensions
    # desired_width = 30
    # desired_height = 30

    # # Calculating the distance of each box's dimensions from the desired dimensions
    # for box in icons_bounding_boxes:
    #     width_diff = abs(box["width"] - desired_width)
    #     height_diff = abs(box["height"] - desired_height)
    #     # Sum of absolute differences as a simple measure of "closeness"
    #     box["distance"] = width_diff + height_diff

    # # Sorting the boxes based on their closeness to the desired dimensions
    # sorted_boxes = sorted(icons_bounding_boxes, key=lambda x: x["distance"])

    # # Selecting the top 150 closest boxes
    # icons_bounding_boxes = sorted_boxes  # DISABLED [:150]

    # Expand a little

    # Define the pixel expansion amount
    pixel_expand = int(os.getenv("OI_POINT_PIXEL_EXPAND", 7))

    # Expand each box by pixel_expand
    for box in icons_bounding_boxes:
        # Expand x, y by pixel_expand if they are greater than 0
        box["x"] = box["x"] - pixel_expand if box["x"] - pixel_expand >= 0 else box["x"]
        box["y"] = box["y"] - pixel_expand if box["y"] - pixel_expand >= 0 else box["y"]

        # Expand w, h by pixel_expand, but not beyond image_width and image_height
        box["width"] = (
            box["width"] + pixel_expand * 2
            if box["x"] + box["width"] + pixel_expand * 2 <= image_width
            else image_width - box["x"] - box["width"]
        )
        box["height"] = (
            box["height"] + pixel_expand * 2
            if box["y"] + box["height"] + pixel_expand * 2 <= image_height
            else image_height - box["y"] - box["height"]
        )

    # Save a debug image with a descriptive name for the step we just went through
    if debug:
        image_data_copy = image_data.copy()
        draw = ImageDraw.Draw(image_data_copy)
        for box in icons_bounding_boxes:
            left = box["x"]
            top = box["y"]
            width = box["width"]
            height = box["height"]
            draw.rectangle([(left, top), (left + width, top + height)], outline="red")
        image_data_copy.save(
            os.path.join(debug_path, "debug_image_after_expanding_boxes.png")
        )

    def combine_boxes(icons_bounding_boxes):
        while True:
            combined_boxes = []
            for box in icons_bounding_boxes:
                for i, combined_box in enumerate(combined_boxes):
                    if (
                        box["x"] < combined_box["x"] + combined_box["width"]
                        and box["x"] + box["width"] > combined_box["x"]
                        and box["y"] < combined_box["y"] + combined_box["height"]
                        and box["y"] + box["height"] > combined_box["y"]
                    ):
                        combined_box["x"] = min(box["x"], combined_box["x"])
                        combined_box["y"] = min(box["y"], combined_box["y"])
                        combined_box["width"] = (
                            max(
                                box["x"] + box["width"],
                                combined_box["x"] + combined_box["width"],
                            )
                            - combined_box["x"]
                        )
                        combined_box["height"] = (
                            max(
                                box["y"] + box["height"],
                                combined_box["y"] + combined_box["height"],
                            )
                            - combined_box["y"]
                        )
                        break
                else:
                    combined_boxes.append(box.copy())
            if len(combined_boxes) == len(icons_bounding_boxes):
                break
            else:
                icons_bounding_boxes = combined_boxes
        return combined_boxes

    if os.getenv("OI_POINT_OVERLAP", "True") == "True":
        icons_bounding_boxes = combine_boxes(icons_bounding_boxes)

    if debug:
        image_data_copy = image_data.copy()
        draw = ImageDraw.Draw(image_data_copy)
        for box in icons_bounding_boxes:
            x, y, w, h = box["x"], box["y"], box["width"], box["height"]
            draw.rectangle([(x, y), (x + w, y + h)], outline="blue")
        image_data_copy.save(
            os.path.join(debug_path, "debug_image_after_combining_boxes.png")
        )

    icons = []
    for box in icons_bounding_boxes:
        x, y, w, h = box["x"], box["y"], box["width"], box["height"]

        icon_image = image_data.crop((x, y, x + w, y + h))

        # icon_image.show()
        # input("Press Enter to finish looking at the image...")

        icon = {}
        icon["data"] = icon_image
        icon["x"] = x
        icon["y"] = y
        icon["width"] = w
        icon["height"] = h

        icon_image_hash = hashlib.sha256(icon_image.tobytes()).hexdigest()
        icon["hash"] = icon_image_hash

        # Calculate the relative central xy coordinates of the bounding box
        center_x = box["center_x"] / image_width  # Relative X coordinate
        center_y = box["center_y"] / image_height  # Relative Y coordinate
        icon["coordinate"] = (center_x, center_y)

        icons.append(icon)

    # Draw and show an image with the full screenshot and all the icons bounding boxes drawn on it in red
    if debug:
        image_data_copy = image_data.copy()
        draw = ImageDraw.Draw(image_data_copy)
        for icon in icons:
            x, y, w, h = icon["x"], icon["y"], icon["width"], icon["height"]
            draw.rectangle([(x, y), (x + w, y + h)], outline="red")
        desktop = os.path.join(os.path.join(os.path.expanduser("~")), "Desktop")
        image_data_copy.save(os.path.join(desktop, "point_vision.png"))

    if "icon" not in description.lower():
        description += " icon"

    if debug:
        print("FINALLY, SEARCHING")

    top_icons = image_search(description, icons, hashes, debug)

    if debug:
        print("DONE")

    coordinates = [t["coordinate"] for t in top_icons]

    # Return the top pick icon data
    return coordinates


# torch.set_num_threads(4)

fast_model = True

# First, we load the respective CLIP model
model = SentenceTransformer("clip-ViT-B-32")


import os

import timm

if fast_model == False:
    # Check if the model file exists
    if not os.path.isfile(model_path):
        # If not, create and save the model
        model = timm.create_model(
            "vit_base_patch16_siglip_224",
            pretrained=True,
            num_classes=0,
        )
        model = model.eval()
        torch.save(model.state_dict(), model_path)
    else:
        # If the model file exists, load the model from the saved state
        model = timm.create_model(
            "vit_base_patch16_siglip_256",
            pretrained=False,  # Don't load pretrained weights
            num_classes=0,
        )
        model.load_state_dict(torch.load(model_path))
        model = model.eval()

    # get model specific transforms (normalization, resize)
    data_config = timm.data.resolve_model_data_config(model)
    transforms = timm.data.create_transform(**data_config, is_training=False)

    def embed_images(images: List[Image.Image], model, transforms):
        # Stack images along the batch dimension
        image_batch = torch.stack([transforms(image) for image in images])
        # Get embeddings
        embeddings = model(image_batch)
        return embeddings

    # Usage:
    # images = [Image.open(io.BytesIO(image_bytes1)), Image.open(io.BytesIO(image_bytes2)), ...]
    # embeddings = embed_images(images, model, transforms)


if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")

# Move the model to the specified device
model = model.to(device)


def image_search(query, icons, hashes, debug):
    hashed_icons = [icon for icon in icons if icon["hash"] in hashes]
    unhashed_icons = [icon for icon in icons if icon["hash"] not in hashes]

    # Embed the unhashed icons
    if fast_model:
        query_and_unhashed_icons_embeds = model.encode(
            [query] + [icon["data"] for icon in unhashed_icons],
            batch_size=128,
            convert_to_tensor=True,
            show_progress_bar=debug,
        )
    else:
        query_and_unhashed_icons_embeds = embed_images(
            [query] + [icon["data"] for icon in unhashed_icons], model, transforms
        )

    query_embed = query_and_unhashed_icons_embeds[0]
    unhashed_icons_embeds = query_and_unhashed_icons_embeds[1:]

    # Store hashes for unhashed icons
    for icon, emb in zip(unhashed_icons, unhashed_icons_embeds):
        hashes[icon["hash"]] = emb

    # Move tensors to the specified device before concatenating
    unhashed_icons_embeds = unhashed_icons_embeds.to(device)

    # Include hashed icons in img_emb
    img_emb = torch.cat(
        [unhashed_icons_embeds]
        + [hashes[icon["hash"]].unsqueeze(0) for icon in hashed_icons]
    )

    # Perform semantic search
    hits = util.semantic_search(query_embed, img_emb)[0]

    # Filter hits with score over 90
    results = [hit for hit in hits if hit["score"] > 90]

    # Ensure top result is included
    if hits and (hits[0] not in results):
        results.insert(0, hits[0])

    # Convert results to original icon format
    return [icons[hit["corpus_id"]] for hit in results]


def get_element_boxes(image_data, debug):
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    debug_path = os.path.join(desktop_path, "oi-debug")

    if debug:
        if not os.path.exists(debug_path):
            os.makedirs(debug_path)

    # Re-import the original image for contrast adjustment
    # original_image = cv2.imread(image_path)

    # Convert the image to a format that PIL can work with
    # pil_image = Image.fromarray(cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB))

    pil_image = image_data

    # Convert to grayscale
    pil_image = pil_image.convert("L")

    def process_image(
        pil_image,
        contrast_level=1.8,
        debug=False,
        debug_path=None,
        adaptive_method=cv2.ADAPTIVE_THRESH_MEAN_C,
        threshold_type=cv2.THRESH_BINARY_INV,
        block_size=11,
        C=3,
    ):
        # Apply an extreme contrast filter
        enhancer = ImageEnhance.Contrast(pil_image)
        contrasted_image = enhancer.enhance(
            contrast_level
        )  # Significantly increase contrast

        # Create a string with all parameters
        parameters_string = f"contrast_level_{contrast_level}-adaptive_method_{adaptive_method}-threshold_type_{threshold_type}-block_size_{block_size}-C_{C}"

        if debug:
            print("TRYING:", parameters_string)
            contrasted_image_path = os.path.join(
                debug_path, f"contrasted_image_{parameters_string}.jpg"
            )
            contrasted_image.save(contrasted_image_path)
            print(f"DEBUG: Contrasted image saved to {contrasted_image_path}")

        # Convert the contrast-enhanced image to OpenCV format
        contrasted_image_cv = cv2.cvtColor(
            np.array(contrasted_image), cv2.COLOR_RGB2BGR
        )

        # Convert the contrast-enhanced image to grayscale
        gray_contrasted = cv2.cvtColor(contrasted_image_cv, cv2.COLOR_BGR2GRAY)
        if debug:
            image_path = os.path.join(
                debug_path, f"gray_contrasted_image_{parameters_string}.jpg"
            )
            cv2.imwrite(image_path, gray_contrasted)
            print("DEBUG: Grayscale contrasted image saved at:", image_path)

        # Apply adaptive thresholding to create a binary image where the GUI elements are isolated
        binary_contrasted = cv2.adaptiveThreshold(
            src=gray_contrasted,
            maxValue=255,
            adaptiveMethod=adaptive_method,
            thresholdType=threshold_type,
            blockSize=block_size,
            C=C,
        )

        if debug:
            binary_contrasted_image_path = os.path.join(
                debug_path, f"binary_contrasted_image_{parameters_string}.jpg"
            )
            cv2.imwrite(binary_contrasted_image_path, binary_contrasted)
            print(
                f"DEBUG: Binary contrasted image saved to {binary_contrasted_image_path}"
            )

        # Find contours from the binary image
        contours_contrasted, _ = cv2.findContours(
            binary_contrasted, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE
        )

        # Optionally, draw contours on the image for visualization
        contour_image = np.zeros_like(binary_contrasted)
        cv2.drawContours(contour_image, contours_contrasted, -1, (255, 255, 255), 1)

        if debug:
            contoured_contrasted_image_path = os.path.join(
                debug_path, f"contoured_contrasted_image_{parameters_string}.jpg"
            )
            cv2.imwrite(contoured_contrasted_image_path, contour_image)
            print(
                f"DEBUG: Contoured contrasted image saved at: {contoured_contrasted_image_path}"
            )

        return contours_contrasted

    if os.getenv("OI_POINT_PERMUTATE", "False") == "True":
        import random

        for _ in range(10):
            random_contrast = random.uniform(
                1, 40
            )  # Random contrast in range 0.5 to 1.5
            random_block_size = random.choice(
                range(1, 11, 2)
            )  # Random block size in range 1 to 10, but only odd numbers
            random_block_size = 11
            random_adaptive_method = random.choice(
                [cv2.ADAPTIVE_THRESH_MEAN_C, cv2.ADAPTIVE_THRESH_GAUSSIAN_C]
            )  # Random adaptive method
            random_threshold_type = random.choice(
                [cv2.THRESH_BINARY, cv2.THRESH_BINARY_INV]
            )  # Random threshold type
            random_C = random.randint(-10, 10)  # Random C in range 1 to 10
            contours_contrasted = process_image(
                pil_image,
                contrast_level=random_contrast,
                block_size=random_block_size,
                adaptive_method=random_adaptive_method,
                threshold_type=random_threshold_type,
                C=random_C,
                debug=debug,
                debug_path=debug_path,
            )

        print("Random Contrast: ", random_contrast)
        print("Random Block Size: ", random_block_size)
        print("Random Adaptive Method: ", random_adaptive_method)
        print("Random Threshold Type: ", random_threshold_type)
        print("Random C: ", random_C)
    else:
        contours_contrasted = process_image(
            pil_image, debug=debug, debug_path=debug_path
        )

    if debug:
        print("WE HERE")

    # Initialize an empty list to store the boxes
    boxes = []
    for contour in contours_contrasted:
        # Get the rectangle that bounds the contour
        x, y, w, h = cv2.boundingRect(contour)
        # Append the box as a dictionary to the list
        boxes.append({"x": x, "y": y, "width": w, "height": h})

    if debug:
        print("WE HHERE")

    if (
        False
    ):  # Disabled. I thought this would be faster but it's actually slower than just embedding all of them.
        # Remove any boxes whose edges cross over any contours
        filtered_boxes = []
        for box in boxes:
            crosses_contour = False
            for contour in contours_contrasted:
                if (
                    cv2.pointPolygonTest(contour, (box["x"], box["y"]), False) >= 0
                    or cv2.pointPolygonTest(
                        contour, (box["x"] + box["width"], box["y"]), False
                    )
                    >= 0
                    or cv2.pointPolygonTest(
                        contour, (box["x"], box["y"] + box["height"]), False
                    )
                    >= 0
                    or cv2.pointPolygonTest(
                        contour,
                        (box["x"] + box["width"], box["y"] + box["height"]),
                        False,
                    )
                    >= 0
                ):
                    crosses_contour = True
                    break
            if not crosses_contour:
                filtered_boxes.append(box)
        boxes = filtered_boxes

    if debug:
        print("WE HHHERE")

    return boxes

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc7906.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# NSA's CMS Key Management Attributes
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc7906.txt
# https://www.rfc-editor.org/errata/eid5850
#

from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import tag
from pyasn1.type import univ

from pyasn1_modules import rfc2634
from pyasn1_modules import rfc4108
from pyasn1_modules import rfc5280
from pyasn1_modules import rfc5652
from pyasn1_modules import rfc6010
from pyasn1_modules import rfc6019
from pyasn1_modules import rfc7191

MAX = float('inf')


# Imports From RFC 2634

id_aa_contentHint = rfc2634.id_aa_contentHint

ContentHints = rfc2634.ContentHints

id_aa_securityLabel = rfc2634.id_aa_securityLabel

SecurityPolicyIdentifier = rfc2634.SecurityPolicyIdentifier

SecurityClassification = rfc2634.SecurityClassification

ESSPrivacyMark = rfc2634.ESSPrivacyMark

SecurityCategories= rfc2634.SecurityCategories

ESSSecurityLabel = rfc2634.ESSSecurityLabel


# Imports From RFC 4108

id_aa_communityIdentifiers = rfc4108.id_aa_communityIdentifiers

CommunityIdentifier = rfc4108.CommunityIdentifier

CommunityIdentifiers = rfc4108.CommunityIdentifiers


# Imports From RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier

Name = rfc5280.Name

Certificate = rfc5280.Certificate

GeneralNames = rfc5280.GeneralNames

GeneralName = rfc5280.GeneralName


SubjectInfoAccessSyntax = rfc5280.SubjectInfoAccessSyntax

id_pkix = rfc5280.id_pkix

id_pe = rfc5280.id_pe

id_pe_subjectInfoAccess = rfc5280.id_pe_subjectInfoAccess


# Imports From RFC 6010

CMSContentConstraints = rfc6010.CMSContentConstraints


# Imports From RFC 6019

BinaryTime = rfc6019.BinaryTime

id_aa_binarySigningTime = rfc6019.id_aa_binarySigningTime

BinarySigningTime = rfc6019.BinarySigningTime


# Imports From RFC 5652

Attribute = rfc5652.Attribute

CertificateSet = rfc5652.CertificateSet

CertificateChoices = rfc5652.CertificateChoices

id_contentType = rfc5652.id_contentType

ContentType = rfc5652.ContentType

id_messageDigest = rfc5652.id_messageDigest

MessageDigest = rfc5652.MessageDigest


# Imports From RFC 7191

SIREntityName = rfc7191.SIREntityName

id_aa_KP_keyPkgIdAndReceiptReq = rfc7191.id_aa_KP_keyPkgIdAndReceiptReq

KeyPkgIdentifierAndReceiptReq = rfc7191.KeyPkgIdentifierAndReceiptReq


# Key Province Attribute

id_aa_KP_keyProvinceV2 = univ.ObjectIdentifier('2.16.840.1.101.2.1.5.71')


class KeyProvinceV2(univ.ObjectIdentifier):
    pass


aa_keyProvince_v2 = Attribute()
aa_keyProvince_v2['attrType'] = id_aa_KP_keyProvinceV2
aa_keyProvince_v2['attrValues'][0] = KeyProvinceV2()
 

# Manifest Attribute

id_aa_KP_manifest = univ.ObjectIdentifier('2.16.840.1.101.2.1.5.72')


class ShortTitle(char.PrintableString):
    pass


class Manifest(univ.SequenceOf):
    pass

Manifest.componentType = ShortTitle()
Manifest.subtypeSpec=constraint.ValueSizeConstraint(1, MAX)


aa_manifest = Attribute()
aa_manifest['attrType'] = id_aa_KP_manifest
aa_manifest['attrValues'][0] = Manifest()


# Key Algorithm Attribute

id_kma_keyAlgorithm = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.1')


class KeyAlgorithm(univ.Sequence):
    pass

KeyAlgorithm.componentType = namedtype.NamedTypes(
    namedtype.NamedType('keyAlg', univ.ObjectIdentifier()),
    namedtype.OptionalNamedType('checkWordAlg', univ.ObjectIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('crcAlg', univ.ObjectIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
)


aa_keyAlgorithm = Attribute()
aa_keyAlgorithm['attrType'] = id_kma_keyAlgorithm
aa_keyAlgorithm['attrValues'][0] = KeyAlgorithm()


# User Certificate Attribute

id_at_userCertificate = univ.ObjectIdentifier('2.5.4.36')


aa_userCertificate = Attribute()
aa_userCertificate['attrType'] = id_at_userCertificate
aa_userCertificate['attrValues'][0] =  Certificate()


# Key Package Receivers Attribute

id_kma_keyPkgReceiversV2 = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.16')


class KeyPkgReceiver(univ.Choice):
    pass

KeyPkgReceiver.componentType = namedtype.NamedTypes(
    namedtype.NamedType('sirEntity', SIREntityName().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('community', CommunityIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class KeyPkgReceiversV2(univ.SequenceOf):
    pass

KeyPkgReceiversV2.componentType = KeyPkgReceiver()
KeyPkgReceiversV2.subtypeSpec=constraint.ValueSizeConstraint(1, MAX)


aa_keyPackageReceivers_v2 = Attribute()
aa_keyPackageReceivers_v2['attrType'] = id_kma_keyPkgReceiversV2
aa_keyPackageReceivers_v2['attrValues'][0] = KeyPkgReceiversV2()


# TSEC Nomenclature Attribute

id_kma_TSECNomenclature = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.3')


class CharEdition(char.PrintableString):
    pass


class CharEditionRange(univ.Sequence):
    pass

CharEditionRange.componentType = namedtype.NamedTypes(
    namedtype.NamedType('firstCharEdition', CharEdition()),
    namedtype.NamedType('lastCharEdition', CharEdition())
)


class NumEdition(univ.Integer):
    pass

NumEdition.subtypeSpec = constraint.ValueRangeConstraint(0, 308915776)


class NumEditionRange(univ.Sequence):
    pass

NumEditionRange.componentType = namedtype.NamedTypes(
    namedtype.NamedType('firstNumEdition', NumEdition()),
    namedtype.NamedType('lastNumEdition', NumEdition())
)


class EditionID(univ.Choice):
    pass

EditionID.componentType = namedtype.NamedTypes(
    namedtype.NamedType('char', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('charEdition', CharEdition().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.NamedType('charEditionRange', CharEditionRange().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2)))
    ))
    ),
    namedtype.NamedType('num', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('numEdition', NumEdition().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
        namedtype.NamedType('numEditionRange', NumEditionRange().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4)))
    ))
    )
)


class Register(univ.Integer):
    pass

Register.subtypeSpec = constraint.ValueRangeConstraint(0, 2147483647)


class RegisterRange(univ.Sequence):
    pass

RegisterRange.componentType = namedtype.NamedTypes(
    namedtype.NamedType('firstRegister', Register()),
    namedtype.NamedType('lastRegister', Register())
)


class RegisterID(univ.Choice):
    pass

RegisterID.componentType = namedtype.NamedTypes(
    namedtype.NamedType('register', Register().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 5))),
    namedtype.NamedType('registerRange', RegisterRange().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 6)))
)


class SegmentNumber(univ.Integer):
    pass

SegmentNumber.subtypeSpec = constraint.ValueRangeConstraint(1, 127)


class SegmentRange(univ.Sequence):
    pass

SegmentRange.componentType = namedtype.NamedTypes(
    namedtype.NamedType('firstSegment', SegmentNumber()),
    namedtype.NamedType('lastSegment', SegmentNumber())
)


class SegmentID(univ.Choice):
    pass

SegmentID.componentType = namedtype.NamedTypes(
    namedtype.NamedType('segmentNumber', SegmentNumber().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 7))),
    namedtype.NamedType('segmentRange', SegmentRange().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 8)))
)


class TSECNomenclature(univ.Sequence):
    pass

TSECNomenclature.componentType = namedtype.NamedTypes(
    namedtype.NamedType('shortTitle', ShortTitle()),
    namedtype.OptionalNamedType('editionID', EditionID()),
    namedtype.OptionalNamedType('registerID', RegisterID()),
    namedtype.OptionalNamedType('segmentID', SegmentID())
)


aa_tsecNomenclature = Attribute()
aa_tsecNomenclature['attrType'] = id_kma_TSECNomenclature
aa_tsecNomenclature['attrValues'][0] = TSECNomenclature()


# Key Purpose Attribute

id_kma_keyPurpose = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.13')


class KeyPurpose(univ.Enumerated):
    pass

KeyPurpose.namedValues = namedval.NamedValues(
    ('n-a', 0),
    ('a', 65),
    ('b', 66),
    ('l', 76),
    ('m', 77),
    ('r', 82),
    ('s', 83),
    ('t', 84),
    ('v', 86),
    ('x', 88),
    ('z', 90)
)


aa_keyPurpose = Attribute()
aa_keyPurpose['attrType'] = id_kma_keyPurpose
aa_keyPurpose['attrValues'][0] = KeyPurpose()


# Key Use Attribute

id_kma_keyUse = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.14')


class KeyUse(univ.Enumerated):
    pass

KeyUse.namedValues = namedval.NamedValues(
    ('n-a', 0),
    ('ffk', 1),
    ('kek', 2),
    ('kpk', 3),
    ('msk', 4),
    ('qkek', 5),
    ('tek', 6),
    ('tsk', 7),
    ('trkek', 8),
    ('nfk', 9),
    ('effk', 10),
    ('ebfk', 11),
    ('aek', 12),
    ('wod', 13),
    ('kesk', 246),
    ('eik', 247),
    ('ask', 248),
    ('kmk', 249),
    ('rsk', 250),
    ('csk', 251),
    ('sak', 252),
    ('rgk', 253),
    ('cek', 254),
    ('exk', 255)
)


aa_keyUse = Attribute()
aa_keyPurpose['attrType'] = id_kma_keyUse
aa_keyPurpose['attrValues'][0] = KeyUse()


# Transport Key Attribute

id_kma_transportKey = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.15')


class TransOp(univ.Enumerated):
    pass

TransOp.namedValues = namedval.NamedValues(
    ('transport', 1),
    ('operational', 2)
)


aa_transportKey = Attribute()
aa_transportKey['attrType'] = id_kma_transportKey
aa_transportKey['attrValues'][0] = TransOp()


# Key Distribution Period Attribute

id_kma_keyDistPeriod = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.5')


class KeyDistPeriod(univ.Sequence):
    pass

KeyDistPeriod.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('doNotDistBefore', BinaryTime().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('doNotDistAfter', BinaryTime())
)


aa_keyDistributionPeriod = Attribute()
aa_keyDistributionPeriod['attrType'] = id_kma_keyDistPeriod
aa_keyDistributionPeriod['attrValues'][0] = KeyDistPeriod()


# Key Validity Period Attribute

id_kma_keyValidityPeriod = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.6')


class KeyValidityPeriod(univ.Sequence):
    pass

KeyValidityPeriod.componentType = namedtype.NamedTypes(
    namedtype.NamedType('doNotUseBefore', BinaryTime()),
    namedtype.OptionalNamedType('doNotUseAfter', BinaryTime())
)


aa_keyValidityPeriod = Attribute()
aa_keyValidityPeriod['attrType'] = id_kma_keyValidityPeriod
aa_keyValidityPeriod['attrValues'][0] = KeyValidityPeriod()


# Key Duration Attribute

id_kma_keyDuration = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.7')


ub_KeyDuration_months = univ.Integer(72)

ub_KeyDuration_hours = univ.Integer(96)

ub_KeyDuration_days = univ.Integer(732)

ub_KeyDuration_weeks = univ.Integer(104)

ub_KeyDuration_years = univ.Integer(100)


class KeyDuration(univ.Choice):
    pass

KeyDuration.componentType = namedtype.NamedTypes(
    namedtype.NamedType('hours', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(1, ub_KeyDuration_hours)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('days', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(1, ub_KeyDuration_days))),
    namedtype.NamedType('weeks', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(1, ub_KeyDuration_weeks)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('months', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(1, ub_KeyDuration_months)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('years', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(1, ub_KeyDuration_years)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)


aa_keyDurationPeriod = Attribute()
aa_keyDurationPeriod['attrType'] = id_kma_keyDuration
aa_keyDurationPeriod['attrValues'][0] = KeyDuration()


# Classification Attribute

id_aa_KP_classification = univ.ObjectIdentifier(id_aa_securityLabel)


id_enumeratedPermissiveAttributes = univ.ObjectIdentifier('2.16.840.1.101.2.1.8.3.1')

id_enumeratedRestrictiveAttributes = univ.ObjectIdentifier('2.16.840.1.101.2.1.8.3.4')

id_informativeAttributes = univ.ObjectIdentifier('2.16.840.1.101.2.1.8.3.3')


class SecurityAttribute(univ.Integer):
    pass

SecurityAttribute.subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


class EnumeratedTag(univ.Sequence):
    pass

EnumeratedTag.componentType = namedtype.NamedTypes(
    namedtype.NamedType('tagName', univ.ObjectIdentifier()),
    namedtype.NamedType('attributeList', univ.SetOf(componentType=SecurityAttribute()))
)


class FreeFormField(univ.Choice):
    pass

FreeFormField.componentType = namedtype.NamedTypes(
    namedtype.NamedType('bitSetAttributes', univ.BitString()), # Not permitted in RFC 7906
    namedtype.NamedType('securityAttributes', univ.SetOf(componentType=SecurityAttribute()))
)


class InformativeTag(univ.Sequence):
    pass

InformativeTag.componentType = namedtype.NamedTypes(
    namedtype.NamedType('tagName', univ.ObjectIdentifier()),
    namedtype.NamedType('attributes', FreeFormField())
)


class Classification(ESSSecurityLabel):
    pass


aa_classification = Attribute()
aa_classification['attrType'] = id_aa_KP_classification
aa_classification['attrValues'][0] = Classification()


# Split Identifier Attribute

id_kma_splitID = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.11')


class SplitID(univ.Sequence):
    pass

SplitID.componentType = namedtype.NamedTypes(
    namedtype.NamedType('half', univ.Enumerated(
        namedValues=namedval.NamedValues(('a', 0), ('b', 1)))),
    namedtype.OptionalNamedType('combineAlg', AlgorithmIdentifier())
)


aa_splitIdentifier = Attribute()
aa_splitIdentifier['attrType'] = id_kma_splitID
aa_splitIdentifier['attrValues'][0] = SplitID()


# Key Package Type Attribute

id_kma_keyPkgType = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.12')


class KeyPkgType(univ.ObjectIdentifier):
    pass


aa_keyPackageType = Attribute()
aa_keyPackageType['attrType'] = id_kma_keyPkgType
aa_keyPackageType['attrValues'][0] = KeyPkgType()


# Signature Usage Attribute

id_kma_sigUsageV3 = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.22')


class SignatureUsage(CMSContentConstraints):
    pass


aa_signatureUsage_v3 = Attribute()
aa_signatureUsage_v3['attrType'] = id_kma_sigUsageV3
aa_signatureUsage_v3['attrValues'][0] = SignatureUsage()


# Other Certificate Format Attribute

id_kma_otherCertFormats = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.19')


aa_otherCertificateFormats = Attribute()
aa_signatureUsage_v3['attrType'] = id_kma_otherCertFormats
aa_signatureUsage_v3['attrValues'][0] = CertificateChoices()


# PKI Path Attribute

id_at_pkiPath = univ.ObjectIdentifier('2.5.4.70')


class PkiPath(univ.SequenceOf):
    pass

PkiPath.componentType = Certificate()
PkiPath.subtypeSpec=constraint.ValueSizeConstraint(1, MAX)


aa_pkiPath = Attribute()
aa_pkiPath['attrType'] = id_at_pkiPath
aa_pkiPath['attrValues'][0] = PkiPath()


# Useful Certificates Attribute

id_kma_usefulCerts = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.20')


aa_usefulCertificates = Attribute()
aa_usefulCertificates['attrType'] = id_kma_usefulCerts
aa_usefulCertificates['attrValues'][0] = CertificateSet()


# Key Wrap Attribute

id_kma_keyWrapAlgorithm = univ.ObjectIdentifier('2.16.840.1.101.2.1.13.21')


aa_keyWrapAlgorithm  = Attribute()
aa_keyWrapAlgorithm['attrType'] = id_kma_keyWrapAlgorithm
aa_keyWrapAlgorithm['attrValues'][0] = AlgorithmIdentifier()


# Content Decryption Key Identifier Attribute

id_aa_KP_contentDecryptKeyID = univ.ObjectIdentifier('2.16.840.1.101.2.1.5.66')


class ContentDecryptKeyID(univ.OctetString):
    pass


aa_contentDecryptKeyIdentifier = Attribute()
aa_contentDecryptKeyIdentifier['attrType'] = id_aa_KP_contentDecryptKeyID
aa_contentDecryptKeyIdentifier['attrValues'][0] = ContentDecryptKeyID()


# Certificate Pointers Attribute

aa_certificatePointers = Attribute()
aa_certificatePointers['attrType'] = id_pe_subjectInfoAccess
aa_certificatePointers['attrValues'][0] = SubjectInfoAccessSyntax()


# CRL Pointers Attribute

id_aa_KP_crlPointers = univ.ObjectIdentifier('2.16.840.1.101.2.1.5.70')


aa_cRLDistributionPoints = Attribute()
aa_cRLDistributionPoints['attrType'] = id_aa_KP_crlPointers
aa_cRLDistributionPoints['attrValues'][0] = GeneralNames()


# Extended Error Codes

id_errorCodes = univ.ObjectIdentifier('2.16.840.1.101.2.1.22')

id_missingKeyType = univ.ObjectIdentifier('2.16.840.1.101.2.1.22.1')

id_privacyMarkTooLong = univ.ObjectIdentifier('2.16.840.1.101.2.1.22.2')

id_unrecognizedSecurityPolicy = univ.ObjectIdentifier('2.16.840.1.101.2.1.22.3')


# Map of Attribute Type OIDs to Attributes added to the
# ones that are in rfc5652.py

_cmsAttributesMapUpdate = {
    id_aa_contentHint: ContentHints(),
    id_aa_communityIdentifiers: CommunityIdentifiers(),
    id_aa_binarySigningTime: BinarySigningTime(),
    id_contentType: ContentType(),
    id_messageDigest: MessageDigest(),
    id_aa_KP_keyPkgIdAndReceiptReq: KeyPkgIdentifierAndReceiptReq(),
    id_aa_KP_keyProvinceV2: KeyProvinceV2(),
    id_aa_KP_manifest: Manifest(),
    id_kma_keyAlgorithm: KeyAlgorithm(),
    id_at_userCertificate: Certificate(),
    id_kma_keyPkgReceiversV2: KeyPkgReceiversV2(),
    id_kma_TSECNomenclature: TSECNomenclature(),
    id_kma_keyPurpose: KeyPurpose(),
    id_kma_keyUse: KeyUse(),
    id_kma_transportKey: TransOp(),
    id_kma_keyDistPeriod: KeyDistPeriod(),
    id_kma_keyValidityPeriod: KeyValidityPeriod(),
    id_kma_keyDuration: KeyDuration(),
    id_aa_KP_classification: Classification(),
    id_kma_splitID: SplitID(),
    id_kma_keyPkgType: KeyPkgType(),
    id_kma_sigUsageV3: SignatureUsage(),
    id_kma_otherCertFormats: CertificateChoices(),
    id_at_pkiPath: PkiPath(),
    id_kma_usefulCerts: CertificateSet(),
    id_kma_keyWrapAlgorithm: AlgorithmIdentifier(),
    id_aa_KP_contentDecryptKeyID: ContentDecryptKeyID(),
    id_pe_subjectInfoAccess: SubjectInfoAccessSyntax(),
    id_aa_KP_crlPointers: GeneralNames(),
}

rfc5652.cmsAttributesMap.update(_cmsAttributesMapUpdate)

# === NexusCore/openenv\Lib\site-packages\anthropic\resources\beta\messages\batches.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Iterable
from itertools import chain

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import (
    is_given,
    maybe_transform,
    strip_not_given,
    async_maybe_transform,
)
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ....pagination import SyncPage, AsyncPage
from ...._exceptions import AnthropicError
from ...._base_client import AsyncPaginator, make_request_options
from ...._decoders.jsonl import JSONLDecoder, AsyncJSONLDecoder
from ....types.beta.messages import batch_list_params, batch_create_params
from ....types.anthropic_beta_param import AnthropicBetaParam
from ....types.beta.messages.beta_message_batch import BetaMessageBatch
from ....types.beta.messages.beta_message_batch_individual_response import BetaMessageBatchIndividualResponse

__all__ = ["Batches", "AsyncBatches"]


class Batches(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> BatchesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#accessing-raw-response-data-eg-headers
        """
        return BatchesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> BatchesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#with_streaming_response
        """
        return BatchesWithStreamingResponse(self)

    def create(
        self,
        *,
        requests: Iterable[batch_create_params.Request],
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> BetaMessageBatch:
        """
        Send a batch of Message creation requests.

        The Message Batches API can be used to process multiple Messages API requests at
        once. Once a Message Batch is created, it begins processing immediately. Batches
        can take up to 24 hours to complete.

        Args:
          requests: List of requests for prompt completion. Each is an individual request to create
              a Message.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {
            **strip_not_given(
                {
                    "anthropic-beta": ",".join(chain((str(e) for e in betas), ["message-batches-2024-09-24"]))
                    if is_given(betas)
                    else NOT_GIVEN
                }
            ),
            **(extra_headers or {}),
        }
        extra_headers = {"anthropic-beta": "message-batches-2024-09-24", **(extra_headers or {})}
        return self._post(
            "/v1/messages/batches?beta=true",
            body=maybe_transform({"requests": requests}, batch_create_params.BatchCreateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=BetaMessageBatch,
        )

    def retrieve(
        self,
        message_batch_id: str,
        *,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> BetaMessageBatch:
        """This endpoint is idempotent and can be used to poll for Message Batch
        completion.

        To access the results of a Message Batch, make a request to the
        `results_url` field in the response.

        Args:
          message_batch_id: ID of the Message Batch.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not message_batch_id:
            raise ValueError(f"Expected a non-empty value for `message_batch_id` but received {message_batch_id!r}")
        extra_headers = {
            **strip_not_given(
                {
                    "anthropic-beta": ",".join(chain((str(e) for e in betas), ["message-batches-2024-09-24"]))
                    if is_given(betas)
                    else NOT_GIVEN
                }
            ),
            **(extra_headers or {}),
        }
        extra_headers = {"anthropic-beta": "message-batches-2024-09-24", **(extra_headers or {})}
        return self._get(
            f"/v1/messages/batches/{message_batch_id}?beta=true",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=BetaMessageBatch,
        )

    def list(
        self,
        *,
        after_id: str | NotGiven = NOT_GIVEN,
        before_id: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncPage[BetaMessageBatch]:
        """List all Message Batches within a Workspace.

        Most recently created batches are
        returned first.

        Args:
          after_id: ID of the object to use as a cursor for pagination. When provided, returns the
              page of results immediately after this object.

          before_id: ID of the object to use as a cursor for pagination. When provided, returns the
              page of results immediately before this object.

          limit: Number of items to return per page.

              Defaults to `20`. Ranges from `1` to `100`.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {
            **strip_not_given(
                {
                    "anthropic-beta": ",".join(chain((str(e) for e in betas), ["message-batches-2024-09-24"]))
                    if is_given(betas)
                    else NOT_GIVEN
                }
            ),
            **(extra_headers or {}),
        }
        extra_headers = {"anthropic-beta": "message-batches-2024-09-24", **(extra_headers or {})}
        return self._get_api_list(
            "/v1/messages/batches?beta=true",
            page=SyncPage[BetaMessageBatch],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after_id": after_id,
                        "before_id": before_id,
                        "limit": limit,
                    },
                    batch_list_params.BatchListParams,
                ),
            ),
            model=BetaMessageBatch,
        )

    def cancel(
        self,
        message_batch_id: str,
        *,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> BetaMessageBatch:
        """Batches may be canceled any time before processing ends.

        Once cancellation is
        initiated, the batch enters a `canceling` state, at which time the system may
        complete any in-progress, non-interruptible requests before finalizing
        cancellation.

        The number of canceled requests is specified in `request_counts`. To determine
        which requests were canceled, check the individual results within the batch.
        Note that cancellation may not result in any canceled requests if they were
        non-interruptible.

        Args:
          message_batch_id: ID of the Message Batch.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not message_batch_id:
            raise ValueError(f"Expected a non-empty value for `message_batch_id` but received {message_batch_id!r}")
        extra_headers = {
            **strip_not_given(
                {
                    "anthropic-beta": ",".join(chain((str(e) for e in betas), ["message-batches-2024-09-24"]))
                    if is_given(betas)
                    else NOT_GIVEN
                }
            ),
            **(extra_headers or {}),
        }
        extra_headers = {"anthropic-beta": "message-batches-2024-09-24", **(extra_headers or {})}
        return self._post(
            f"/v1/messages/batches/{message_batch_id}/cancel?beta=true",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=BetaMessageBatch,
        )

    def results(
        self,
        message_batch_id: str,
        *,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> JSONLDecoder[BetaMessageBatchIndividualResponse]:
        """
        Streams the results of a Message Batch as a `.jsonl` file.

        Each line in the file is a JSON object containing the result of a single request
        in the Message Batch. Results are not guaranteed to be in the same order as
        requests. Use the `custom_id` field to match results to requests.

        Args:
          message_batch_id: ID of the Message Batch.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not message_batch_id:
            raise ValueError(f"Expected a non-empty value for `message_batch_id` but received {message_batch_id!r}")

        batch = self.retrieve(message_batch_id=message_batch_id)
        if not batch.results_url:
            raise AnthropicError(
                f"No `results_url` for the given batch; Has it finished processing? {batch.processing_status}"
            )

        extra_headers = {"Accept": "application/binary", **(extra_headers or {})}
        extra_headers = {
            **strip_not_given(
                {
                    "anthropic-beta": ",".join(chain((str(e) for e in betas), ["message-batches-2024-09-24"]))
                    if is_given(betas)
                    else NOT_GIVEN
                }
            ),
            **(extra_headers or {}),
        }
        extra_headers = {"anthropic-beta": "message-batches-2024-09-24", **(extra_headers or {})}
        return self._get(
            batch.results_url,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            stream=True,
            cast_to=JSONLDecoder[BetaMessageBatchIndividualResponse],
        )


class AsyncBatches(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncBatchesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#accessing-raw-response-data-eg-headers
        """
        return AsyncBatchesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncBatchesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#with_streaming_response
        """
        return AsyncBatchesWithStreamingResponse(self)

    async def create(
        self,
        *,
        requests: Iterable[batch_create_params.Request],
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> BetaMessageBatch:
        """
        Send a batch of Message creation requests.

        The Message Batches API can be used to process multiple Messages API requests at
        once. Once a Message Batch is created, it begins processing immediately. Batches
        can take up to 24 hours to complete.

        Args:
          requests: List of requests for prompt completion. Each is an individual request to create
              a Message.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {
            **strip_not_given(
                {
                    "anthropic-beta": ",".join(chain((str(e) for e in betas), ["message-batches-2024-09-24"]))
                    if is_given(betas)
                    else NOT_GIVEN
                }
            ),
            **(extra_headers or {}),
        }
        extra_headers = {"anthropic-beta": "message-batches-2024-09-24", **(extra_headers or {})}
        return await self._post(
            "/v1/messages/batches?beta=true",
            body=await async_maybe_transform({"requests": requests}, batch_create_params.BatchCreateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=BetaMessageBatch,
        )

    async def retrieve(
        self,
        message_batch_id: str,
        *,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> BetaMessageBatch:
        """This endpoint is idempotent and can be used to poll for Message Batch
        completion.

        To access the results of a Message Batch, make a request to the
        `results_url` field in the response.

        Args:
          message_batch_id: ID of the Message Batch.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not message_batch_id:
            raise ValueError(f"Expected a non-empty value for `message_batch_id` but received {message_batch_id!r}")
        extra_headers = {
            **strip_not_given(
                {
                    "anthropic-beta": ",".join(chain((str(e) for e in betas), ["message-batches-2024-09-24"]))
                    if is_given(betas)
                    else NOT_GIVEN
                }
            ),
            **(extra_headers or {}),
        }
        extra_headers = {"anthropic-beta": "message-batches-2024-09-24", **(extra_headers or {})}
        return await self._get(
            f"/v1/messages/batches/{message_batch_id}?beta=true",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=BetaMessageBatch,
        )

    def list(
        self,
        *,
        after_id: str | NotGiven = NOT_GIVEN,
        before_id: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[BetaMessageBatch, AsyncPage[BetaMessageBatch]]:
        """List all Message Batches within a Workspace.

        Most recently created batches are
        returned first.

        Args:
          after_id: ID of the object to use as a cursor for pagination. When provided, returns the
              page of results immediately after this object.

          before_id: ID of the object to use as a cursor for pagination. When provided, returns the
              page of results immediately before this object.

          limit: Number of items to return per page.

              Defaults to `20`. Ranges from `1` to `100`.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {
            **strip_not_given(
                {
                    "anthropic-beta": ",".join(chain((str(e) for e in betas), ["message-batches-2024-09-24"]))
                    if is_given(betas)
                    else NOT_GIVEN
                }
            ),
            **(extra_headers or {}),
        }
        extra_headers = {"anthropic-beta": "message-batches-2024-09-24", **(extra_headers or {})}
        return self._get_api_list(
            "/v1/messages/batches?beta=true",
            page=AsyncPage[BetaMessageBatch],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after_id": after_id,
                        "before_id": before_id,
                        "limit": limit,
                    },
                    batch_list_params.BatchListParams,
                ),
            ),
            model=BetaMessageBatch,
        )

    async def cancel(
        self,
        message_batch_id: str,
        *,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> BetaMessageBatch:
        """Batches may be canceled any time before processing ends.

        Once cancellation is
        initiated, the batch enters a `canceling` state, at which time the system may
        complete any in-progress, non-interruptible requests before finalizing
        cancellation.

        The number of canceled requests is specified in `request_counts`. To determine
        which requests were canceled, check the individual results within the batch.
        Note that cancellation may not result in any canceled requests if they were
        non-interruptible.

        Args:
          message_batch_id: ID of the Message Batch.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not message_batch_id:
            raise ValueError(f"Expected a non-empty value for `message_batch_id` but received {message_batch_id!r}")
        extra_headers = {
            **strip_not_given(
                {
                    "anthropic-beta": ",".join(chain((str(e) for e in betas), ["message-batches-2024-09-24"]))
                    if is_given(betas)
                    else NOT_GIVEN
                }
            ),
            **(extra_headers or {}),
        }
        extra_headers = {"anthropic-beta": "message-batches-2024-09-24", **(extra_headers or {})}
        return await self._post(
            f"/v1/messages/batches/{message_batch_id}/cancel?beta=true",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=BetaMessageBatch,
        )

    async def results(
        self,
        message_batch_id: str,
        *,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncJSONLDecoder[BetaMessageBatchIndividualResponse]:
        """
        Streams the results of a Message Batch as a `.jsonl` file.

        Each line in the file is a JSON object containing the result of a single request
        in the Message Batch. Results are not guaranteed to be in the same order as
        requests. Use the `custom_id` field to match results to requests.

        Args:
          message_batch_id: ID of the Message Batch.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not message_batch_id:
            raise ValueError(f"Expected a non-empty value for `message_batch_id` but received {message_batch_id!r}")

        batch = await self.retrieve(message_batch_id=message_batch_id)
        if not batch.results_url:
            raise AnthropicError(
                f"No `results_url` for the given batch; Has it finished processing? {batch.processing_status}"
            )

        extra_headers = {"Accept": "application/binary", **(extra_headers or {})}
        extra_headers = {
            **strip_not_given(
                {
                    "anthropic-beta": ",".join(chain((str(e) for e in betas), ["message-batches-2024-09-24"]))
                    if is_given(betas)
                    else NOT_GIVEN
                }
            ),
            **(extra_headers or {}),
        }
        extra_headers = {"anthropic-beta": "message-batches-2024-09-24", **(extra_headers or {})}
        return await self._get(
            batch.results_url,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            stream=True,
            cast_to=AsyncJSONLDecoder[BetaMessageBatchIndividualResponse],
        )


class BatchesWithRawResponse:
    def __init__(self, batches: Batches) -> None:
        self._batches = batches

        self.create = _legacy_response.to_raw_response_wrapper(
            batches.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            batches.retrieve,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            batches.list,
        )
        self.cancel = _legacy_response.to_raw_response_wrapper(
            batches.cancel,
        )


class AsyncBatchesWithRawResponse:
    def __init__(self, batches: AsyncBatches) -> None:
        self._batches = batches

        self.create = _legacy_response.async_to_raw_response_wrapper(
            batches.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            batches.retrieve,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            batches.list,
        )
        self.cancel = _legacy_response.async_to_raw_response_wrapper(
            batches.cancel,
        )


class BatchesWithStreamingResponse:
    def __init__(self, batches: Batches) -> None:
        self._batches = batches

        self.create = to_streamed_response_wrapper(
            batches.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            batches.retrieve,
        )
        self.list = to_streamed_response_wrapper(
            batches.list,
        )
        self.cancel = to_streamed_response_wrapper(
            batches.cancel,
        )


class AsyncBatchesWithStreamingResponse:
    def __init__(self, batches: AsyncBatches) -> None:
        self._batches = batches

        self.create = async_to_streamed_response_wrapper(
            batches.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            batches.retrieve,
        )
        self.list = async_to_streamed_response_wrapper(
            batches.list,
        )
        self.cancel = async_to_streamed_response_wrapper(
            batches.cancel,
        )