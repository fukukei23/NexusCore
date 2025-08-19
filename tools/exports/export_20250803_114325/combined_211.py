
# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_path.py ===
from __future__ import annotations

import os
import pathlib
from typing import TYPE_CHECKING, Union

import pytest

import trio
from trio._file_io import AsyncIOWrapper

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


@pytest.fixture
def path(tmp_path: pathlib.Path) -> trio.Path:
    return trio.Path(tmp_path / "test")


def method_pair(
    path: str,
    method_name: str,
) -> tuple[Callable[[], object], Callable[[], Awaitable[object]]]:
    sync_path = pathlib.Path(path)
    async_path = trio.Path(path)
    return getattr(sync_path, method_name), getattr(async_path, method_name)


@pytest.mark.skipif(os.name == "nt", reason="OS is not posix")
def test_instantiate_posix() -> None:
    assert isinstance(trio.Path(), trio.PosixPath)


@pytest.mark.skipif(os.name != "nt", reason="OS is not Windows")
def test_instantiate_windows() -> None:
    assert isinstance(trio.Path(), trio.WindowsPath)


async def test_open_is_async_context_manager(path: trio.Path) -> None:
    async with await path.open("w") as f:
        assert isinstance(f, AsyncIOWrapper)

    assert f.closed


def test_magic() -> None:
    path = trio.Path("test")

    assert str(path) == "test"
    assert bytes(path) == b"test"


EitherPathType = Union[type[trio.Path], type[pathlib.Path]]
PathOrStrType = Union[EitherPathType, type[str]]
cls_pairs: list[tuple[EitherPathType, EitherPathType]] = [
    (trio.Path, pathlib.Path),
    (pathlib.Path, trio.Path),
    (trio.Path, trio.Path),
]


@pytest.mark.parametrize(("cls_a", "cls_b"), cls_pairs)
def test_cmp_magic(cls_a: EitherPathType, cls_b: EitherPathType) -> None:
    a, b = cls_a(""), cls_b("")
    assert a == b
    assert not a != b  # noqa: SIM202  # negate-not-equal-op

    a, b = cls_a("a"), cls_b("b")
    assert a < b
    assert b > a

    # this is intentionally testing equivalence with none, due to the
    # other=sentinel logic in _forward_magic
    assert not a == None  # noqa
    assert not b == None  # noqa


# upstream python3.8 bug: we should also test (pathlib.Path, trio.Path), but
# __*div__ does not properly raise NotImplementedError like the other comparison
# magic, so trio.Path's implementation does not get dispatched
cls_pairs_str: list[tuple[PathOrStrType, PathOrStrType]] = [
    (trio.Path, pathlib.Path),
    (trio.Path, trio.Path),
    (trio.Path, str),
    (str, trio.Path),
]


@pytest.mark.parametrize(("cls_a", "cls_b"), cls_pairs_str)
def test_div_magic(cls_a: PathOrStrType, cls_b: PathOrStrType) -> None:
    a, b = cls_a("a"), cls_b("b")

    result = a / b  # type: ignore[operator]
    # Type checkers think str / str could happen. Check each combo manually in type_tests/.
    assert isinstance(result, trio.Path)
    assert str(result) == os.path.join("a", "b")


@pytest.mark.parametrize(
    ("cls_a", "cls_b"),
    [(trio.Path, pathlib.Path), (trio.Path, trio.Path)],
)
@pytest.mark.parametrize("path", ["foo", "foo/bar/baz", "./foo"])
def test_hash_magic(
    cls_a: EitherPathType,
    cls_b: EitherPathType,
    path: str,
) -> None:
    a, b = cls_a(path), cls_b(path)
    assert hash(a) == hash(b)


def test_forwarded_properties(path: trio.Path) -> None:
    # use `name` as a representative of forwarded properties

    assert "name" in dir(path)
    assert path.name == "test"


def test_async_method_signature(path: trio.Path) -> None:
    # use `resolve` as a representative of wrapped methods

    assert path.resolve.__name__ == "resolve"
    assert path.resolve.__qualname__ == "Path.resolve"

    assert path.resolve.__doc__ is not None
    assert path.resolve.__qualname__ in path.resolve.__doc__


@pytest.mark.parametrize("method_name", ["is_dir", "is_file"])
async def test_compare_async_stat_methods(method_name: str) -> None:
    method, async_method = method_pair(".", method_name)

    result = method()
    async_result = await async_method()

    assert result == async_result


def test_invalid_name_not_wrapped(path: trio.Path) -> None:
    with pytest.raises(AttributeError):
        getattr(path, "invalid_fake_attr")  # noqa: B009  # "get-attr-with-constant"


@pytest.mark.parametrize("method_name", ["absolute", "resolve"])
async def test_async_methods_rewrap(method_name: str) -> None:
    method, async_method = method_pair(".", method_name)

    result = method()
    async_result = await async_method()

    assert isinstance(async_result, trio.Path)
    assert str(result) == str(async_result)


def test_forward_methods_rewrap(path: trio.Path, tmp_path: pathlib.Path) -> None:
    with_name = path.with_name("foo")
    with_suffix = path.with_suffix(".py")

    assert isinstance(with_name, trio.Path)
    assert with_name == tmp_path / "foo"
    assert isinstance(with_suffix, trio.Path)
    assert with_suffix == tmp_path / "test.py"


def test_forward_properties_rewrap(path: trio.Path) -> None:
    assert isinstance(path.parent, trio.Path)


def test_forward_methods_without_rewrap(path: trio.Path) -> None:
    assert "totally-unique-path" in str(path.joinpath("totally-unique-path"))


def test_repr() -> None:
    path = trio.Path(".")

    assert repr(path) == "trio.Path('.')"


@pytest.mark.parametrize("meth", [trio.Path.__init__, trio.Path.joinpath])
async def test_path_wraps_path(
    path: trio.Path,
    meth: Callable[[trio.Path, trio.Path], object],
) -> None:
    wrapped = await path.absolute()
    result = meth(path, wrapped)
    if result is None:
        result = path

    assert wrapped == result


def test_path_nonpath() -> None:
    with pytest.raises(TypeError):
        trio.Path(1)  # type: ignore


async def test_open_file_can_open_path(path: trio.Path) -> None:
    async with await trio.open_file(path, "w") as f:
        assert f.name == os.fspath(path)


async def test_globmethods(path: trio.Path) -> None:
    # Populate a directory tree
    await path.mkdir()
    await (path / "foo").mkdir()
    await (path / "foo" / "_bar.txt").write_bytes(b"")
    await (path / "bar.txt").write_bytes(b"")
    await (path / "bar.dat").write_bytes(b"")

    # Path.glob
    for _pattern, _results in {
        "*.txt": {"bar.txt"},
        "**/*.txt": {"_bar.txt", "bar.txt"},
    }.items():
        entries = set()
        for entry in await path.glob(_pattern):
            assert isinstance(entry, trio.Path)
            entries.add(entry.name)

        assert entries == _results

    # Path.rglob
    entries = set()
    for entry in await path.rglob("*.txt"):
        assert isinstance(entry, trio.Path)
        entries.add(entry.name)

    assert entries == {"_bar.txt", "bar.txt"}


async def test_as_uri(path: trio.Path) -> None:
    path = await path.parent.resolve()

    assert path.as_uri().startswith("file:///")


async def test_iterdir(path: trio.Path) -> None:
    # Populate a directory
    await path.mkdir()
    await (path / "foo").mkdir()
    await (path / "bar.txt").write_bytes(b"")

    entries = set()
    for entry in await path.iterdir():
        assert isinstance(entry, trio.Path)
        entries.add(entry.name)

    assert entries == {"bar.txt", "foo"}


async def test_classmethods() -> None:
    assert isinstance(await trio.Path.home(), trio.Path)

    # pathlib.Path has only two classmethods
    assert str(await trio.Path.home()) == os.path.expanduser("~")
    assert str(await trio.Path.cwd()) == os.getcwd()

    # Wrapped method has docstring
    assert trio.Path.home.__doc__


@pytest.mark.parametrize(
    "wrapper",
    [
        trio._path._wraps_async,
        trio._path._wrap_method,
        trio._path._wrap_method_path,
        trio._path._wrap_method_path_iterable,
    ],
)
def test_wrapping_without_docstrings(
    wrapper: Callable[[Callable[[], None]], Callable[[], None]],
) -> None:
    @wrapper
    def func_without_docstring() -> None: ...  # pragma: no cover

    assert func_without_docstring.__doc__ is None

# === NexusCore/openenv\Lib\site-packages\win32comext\axdebug\codecontainer.py ===
"""A utility class for a code container.

A code container is a class which holds source code for a debugger.  It knows how
to color the text, and also how to translate lines into offsets, and back.
"""

from __future__ import annotations

import os
import sys
import tokenize
from keyword import kwlist
from typing import Any

import win32api
import winerror
from win32com.axdebug import axdebug, contexts
from win32com.axdebug.util import _wrap
from win32com.server.exception import COMException

_keywords = {
    _keyword
    for _keyword in kwlist
    # Avoids including True/False/None
    if _keyword.islower()
}
"""set of Python keywords"""


class SourceCodeContainer:
    def __init__(
        self,
        text: str | None,
        fileName="<Remove Me!>",
        sourceContext=0,
        startLineNumber=0,
        site=None,
        debugDocument=None,
    ):
        self.sourceContext = sourceContext  # The source context added by a smart host.
        self.text: str | None = text
        if text:
            self._buildlines()
        self.nextLineNo = 0
        self.fileName = fileName
        # Any: PyIDispatch type is not statically exposed
        self.codeContexts: dict[int, Any] = {}
        self.site = site
        self.startLineNumber = startLineNumber
        self.debugDocument = debugDocument

    def _Close(self):
        self.text = self.lines = self.lineOffsets = None
        self.codeContexts = None
        self.debugDocument = None
        self.site = None
        self.sourceContext = None

    def GetText(self):
        return self.text

    def GetName(self, dnt):
        raise NotImplementedError("You must subclass this")

    def GetFileName(self):
        return self.fileName

    def GetPositionOfLine(self, cLineNumber):
        self.GetText()  # Prime us.
        try:
            return self.lineOffsets[cLineNumber]
        except IndexError:
            raise COMException(scode=winerror.S_FALSE)

    def GetLineOfPosition(self, charPos):
        self.GetText()  # Prime us.
        lastOffset = 0
        lineNo = 0
        for lineOffset in self.lineOffsets[1:]:
            if lineOffset > charPos:
                break
            lastOffset = lineOffset
            lineNo += 1
        else:  # for not broken.
            # print("Can't find", charPos, "in", self.lineOffsets)
            raise COMException(scode=winerror.S_FALSE)
        # print("GLOP ret=", lineNo, (charPos - lastOffset))
        return lineNo, (charPos - lastOffset)

    def GetNextLine(self):
        if self.nextLineNo >= len(self.lines):
            self.nextLineNo = 0  # auto-reset.
            return ""
        rc = self.lines[self.nextLineNo]
        self.nextLineNo += 1
        return rc

    def GetLine(self, num):
        self.GetText()  # Prime us.
        return self.lines[num]

    def GetNumChars(self):
        return len(self.GetText())

    def GetNumLines(self):
        self.GetText()  # Prime us.
        return len(self.lines)

    def _buildline(self, pos):
        i = self.text.find("\n", pos)
        if i < 0:
            newpos = len(self.text)
        else:
            newpos = i + 1
        r = self.text[pos:newpos]
        return r, newpos

    def _buildlines(self):
        self.lines = []
        self.lineOffsets = [0]
        line, pos = self._buildline(0)
        while line:
            self.lines.append(line)
            self.lineOffsets.append(pos)
            line, pos = self._buildline(pos)

    def _ProcessToken(self, type, token, spos, epos, line):
        srow, scol = spos
        erow, ecol = epos
        self.GetText()  # Prime us.
        linenum = srow - 1  # Lines zero based for us too.
        realCharPos = self.lineOffsets[linenum] + scol
        numskipped = realCharPos - self.lastPos
        if numskipped == 0:
            pass
        elif numskipped == 1:
            self.attrs.append(axdebug.SOURCETEXT_ATTR_COMMENT)
        else:
            self.attrs.append((axdebug.SOURCETEXT_ATTR_COMMENT, numskipped))
        kwSize = len(token)
        self.lastPos = realCharPos + kwSize
        attr = 0

        if type == tokenize.NAME:
            if token in _keywords:
                attr = axdebug.SOURCETEXT_ATTR_KEYWORD
        elif type == tokenize.STRING:
            attr = axdebug.SOURCETEXT_ATTR_STRING
        elif type == tokenize.NUMBER:
            attr = axdebug.SOURCETEXT_ATTR_NUMBER
        elif type == tokenize.OP:
            attr = axdebug.SOURCETEXT_ATTR_OPERATOR
        elif type == tokenize.COMMENT:
            attr = axdebug.SOURCETEXT_ATTR_COMMENT
        # else attr remains zero...
        if kwSize == 0:
            pass
        elif kwSize == 1:
            self.attrs.append(attr)
        else:
            self.attrs.append((attr, kwSize))

    def GetSyntaxColorAttributes(self):
        self.lastPos = 0
        self.attrs = []
        try:
            for tokens in tokenize.tokenize(self.GetNextLine):
                self._ProcessToken(*tokens)
        except tokenize.TokenError:
            pass  # Ignore - will cause all subsequent text to be commented.
        numAtEnd = len(self.GetText()) - self.lastPos
        if numAtEnd:
            self.attrs.append((axdebug.SOURCETEXT_ATTR_COMMENT, numAtEnd))
        return self.attrs

    # We also provide and manage DebugDocumentContext objects
    def _MakeDebugCodeContext(self, lineNo, charPos, len):
        return _wrap(
            contexts.DebugCodeContext(lineNo, charPos, len, self, self.site),
            axdebug.IID_IDebugCodeContext,
        )

    # Make a context at the given position.  It should take up the entire context.
    def _MakeContextAtPosition(self, charPos):
        lineNo, offset = self.GetLineOfPosition(charPos)
        try:
            endPos = self.GetPositionOfLine(lineNo + 1)
        except:
            endPos = charPos
        codecontext = self._MakeDebugCodeContext(lineNo, charPos, endPos - charPos)
        return codecontext

    # Returns a DebugCodeContext.  debugDocument can be None for smart hosts.
    def GetCodeContextAtPosition(self, charPos):
        # trace("GetContextOfPos", charPos, maxChars)
        # Convert to line number.
        lineNo, offset = self.GetLineOfPosition(charPos)
        charPos = self.GetPositionOfLine(lineNo)
        try:
            cc = self.codeContexts[charPos]
        except KeyError:
            cc = self._MakeContextAtPosition(charPos)
            self.codeContexts[charPos] = cc
        return cc


class SourceModuleContainer(SourceCodeContainer):
    def __init__(self, module):
        self.module = module
        if hasattr(module, "__file__"):
            fname = self.module.__file__
            # Check for .pyc or .pyo or even .pys!
            if fname[-1] in ["O", "o", "C", "c", "S", "s"]:
                fname = fname[:-1]
            try:
                fname = win32api.GetFullPathName(fname)
            except win32api.error:
                pass
        else:
            if module.__name__ == "__main__" and len(sys.argv) > 0:
                fname = sys.argv[0]
            else:
                fname = "<Unknown!>"
        SourceCodeContainer.__init__(self, None, fname)

    def GetText(self):
        if self.text is None:
            fname = self.GetFileName()
            if fname:
                try:
                    self.text = open(fname, "r").read()
                except OSError as details:
                    self.text = f"# COMException opening file\n# {details!r}"
            else:
                self.text = f"# No file available for module '{self.module}'"
            self._buildlines()
        return self.text

    def GetName(self, dnt):
        name = self.module.__name__
        try:
            fname = win32api.GetFullPathName(self.module.__file__)
        except win32api.error:
            fname = self.module.__file__
        except AttributeError:
            fname = name
        if dnt == axdebug.DOCUMENTNAMETYPE_APPNODE:
            return name.split(".")[-1]
        elif dnt == axdebug.DOCUMENTNAMETYPE_TITLE:
            return fname
        elif dnt == axdebug.DOCUMENTNAMETYPE_FILE_TAIL:
            return os.path.split(fname)[1]
        elif dnt == axdebug.DOCUMENTNAMETYPE_URL:
            return f"file:{fname}"
        else:
            raise COMException(scode=winerror.E_UNEXPECTED)


if __name__ == "__main__":
    from Test import ttest

    sc = SourceModuleContainer(ttest)
    # sc = SourceCodeContainer(open(sys.argv[1], "rb").read(), sys.argv[1])
    attrs = sc.GetSyntaxColorAttributes()
    attrlen = 0
    for attr in attrs:
        if isinstance(attr, tuple):
            attrlen += attr[1]
        else:
            attrlen += 1
    text = sc.GetText()
    if attrlen != len(text):
        print(f"Lengths don't match!!! ({attrlen}/{len(text)})")

    # print("Attributes:")
    # print(attrs)
    print("GetLineOfPos=", sc.GetLineOfPosition(0))
    print("GetLineOfPos=", sc.GetLineOfPosition(4))
    print("GetLineOfPos=", sc.GetLineOfPosition(10))

# === NexusCore/openenv\Lib\site-packages\aiohttp\compression_utils.py ===
import asyncio
import sys
import zlib
from concurrent.futures import Executor
from typing import Any, Final, Optional, Protocol, TypedDict, cast

if sys.version_info >= (3, 12):
    from collections.abc import Buffer
else:
    from typing import Union

    Buffer = Union[bytes, bytearray, "memoryview[int]", "memoryview[bytes]"]

try:
    try:
        import brotlicffi as brotli
    except ImportError:
        import brotli

    HAS_BROTLI = True
except ImportError:  # pragma: no cover
    HAS_BROTLI = False

MAX_SYNC_CHUNK_SIZE = 1024


class ZLibCompressObjProtocol(Protocol):
    def compress(self, data: Buffer) -> bytes: ...
    def flush(self, mode: int = ..., /) -> bytes: ...


class ZLibDecompressObjProtocol(Protocol):
    def decompress(self, data: Buffer, max_length: int = ...) -> bytes: ...
    def flush(self, length: int = ..., /) -> bytes: ...

    @property
    def eof(self) -> bool: ...


class ZLibBackendProtocol(Protocol):
    MAX_WBITS: int
    Z_FULL_FLUSH: int
    Z_SYNC_FLUSH: int
    Z_BEST_SPEED: int
    Z_FINISH: int

    def compressobj(
        self,
        level: int = ...,
        method: int = ...,
        wbits: int = ...,
        memLevel: int = ...,
        strategy: int = ...,
        zdict: Optional[Buffer] = ...,
    ) -> ZLibCompressObjProtocol: ...
    def decompressobj(
        self, wbits: int = ..., zdict: Buffer = ...
    ) -> ZLibDecompressObjProtocol: ...

    def compress(
        self, data: Buffer, /, level: int = ..., wbits: int = ...
    ) -> bytes: ...
    def decompress(
        self, data: Buffer, /, wbits: int = ..., bufsize: int = ...
    ) -> bytes: ...


class CompressObjArgs(TypedDict, total=False):
    wbits: int
    strategy: int
    level: int


class ZLibBackendWrapper:
    def __init__(self, _zlib_backend: ZLibBackendProtocol):
        self._zlib_backend: ZLibBackendProtocol = _zlib_backend

    @property
    def name(self) -> str:
        return getattr(self._zlib_backend, "__name__", "undefined")

    @property
    def MAX_WBITS(self) -> int:
        return self._zlib_backend.MAX_WBITS

    @property
    def Z_FULL_FLUSH(self) -> int:
        return self._zlib_backend.Z_FULL_FLUSH

    @property
    def Z_SYNC_FLUSH(self) -> int:
        return self._zlib_backend.Z_SYNC_FLUSH

    @property
    def Z_BEST_SPEED(self) -> int:
        return self._zlib_backend.Z_BEST_SPEED

    @property
    def Z_FINISH(self) -> int:
        return self._zlib_backend.Z_FINISH

    def compressobj(self, *args: Any, **kwargs: Any) -> ZLibCompressObjProtocol:
        return self._zlib_backend.compressobj(*args, **kwargs)

    def decompressobj(self, *args: Any, **kwargs: Any) -> ZLibDecompressObjProtocol:
        return self._zlib_backend.decompressobj(*args, **kwargs)

    def compress(self, data: Buffer, *args: Any, **kwargs: Any) -> bytes:
        return self._zlib_backend.compress(data, *args, **kwargs)

    def decompress(self, data: Buffer, *args: Any, **kwargs: Any) -> bytes:
        return self._zlib_backend.decompress(data, *args, **kwargs)

    # Everything not explicitly listed in the Protocol we just pass through
    def __getattr__(self, attrname: str) -> Any:
        return getattr(self._zlib_backend, attrname)


ZLibBackend: ZLibBackendWrapper = ZLibBackendWrapper(zlib)


def set_zlib_backend(new_zlib_backend: ZLibBackendProtocol) -> None:
    ZLibBackend._zlib_backend = new_zlib_backend


def encoding_to_mode(
    encoding: Optional[str] = None,
    suppress_deflate_header: bool = False,
) -> int:
    if encoding == "gzip":
        return 16 + ZLibBackend.MAX_WBITS

    return -ZLibBackend.MAX_WBITS if suppress_deflate_header else ZLibBackend.MAX_WBITS


class ZlibBaseHandler:
    def __init__(
        self,
        mode: int,
        executor: Optional[Executor] = None,
        max_sync_chunk_size: Optional[int] = MAX_SYNC_CHUNK_SIZE,
    ):
        self._mode = mode
        self._executor = executor
        self._max_sync_chunk_size = max_sync_chunk_size


class ZLibCompressor(ZlibBaseHandler):
    def __init__(
        self,
        encoding: Optional[str] = None,
        suppress_deflate_header: bool = False,
        level: Optional[int] = None,
        wbits: Optional[int] = None,
        strategy: Optional[int] = None,
        executor: Optional[Executor] = None,
        max_sync_chunk_size: Optional[int] = MAX_SYNC_CHUNK_SIZE,
    ):
        super().__init__(
            mode=(
                encoding_to_mode(encoding, suppress_deflate_header)
                if wbits is None
                else wbits
            ),
            executor=executor,
            max_sync_chunk_size=max_sync_chunk_size,
        )
        self._zlib_backend: Final = ZLibBackendWrapper(ZLibBackend._zlib_backend)

        kwargs: CompressObjArgs = {}
        kwargs["wbits"] = self._mode
        if strategy is not None:
            kwargs["strategy"] = strategy
        if level is not None:
            kwargs["level"] = level
        self._compressor = self._zlib_backend.compressobj(**kwargs)
        self._compress_lock = asyncio.Lock()

    def compress_sync(self, data: bytes) -> bytes:
        return self._compressor.compress(data)

    async def compress(self, data: bytes) -> bytes:
        """Compress the data and returned the compressed bytes.

        Note that flush() must be called after the last call to compress()

        If the data size is large than the max_sync_chunk_size, the compression
        will be done in the executor. Otherwise, the compression will be done
        in the event loop.
        """
        async with self._compress_lock:
            # To ensure the stream is consistent in the event
            # there are multiple writers, we need to lock
            # the compressor so that only one writer can
            # compress at a time.
            if (
                self._max_sync_chunk_size is not None
                and len(data) > self._max_sync_chunk_size
            ):
                return await asyncio.get_running_loop().run_in_executor(
                    self._executor, self._compressor.compress, data
                )
            return self.compress_sync(data)

    def flush(self, mode: Optional[int] = None) -> bytes:
        return self._compressor.flush(
            mode if mode is not None else self._zlib_backend.Z_FINISH
        )


class ZLibDecompressor(ZlibBaseHandler):
    def __init__(
        self,
        encoding: Optional[str] = None,
        suppress_deflate_header: bool = False,
        executor: Optional[Executor] = None,
        max_sync_chunk_size: Optional[int] = MAX_SYNC_CHUNK_SIZE,
    ):
        super().__init__(
            mode=encoding_to_mode(encoding, suppress_deflate_header),
            executor=executor,
            max_sync_chunk_size=max_sync_chunk_size,
        )
        self._zlib_backend: Final = ZLibBackendWrapper(ZLibBackend._zlib_backend)
        self._decompressor = self._zlib_backend.decompressobj(wbits=self._mode)

    def decompress_sync(self, data: bytes, max_length: int = 0) -> bytes:
        return self._decompressor.decompress(data, max_length)

    async def decompress(self, data: bytes, max_length: int = 0) -> bytes:
        """Decompress the data and return the decompressed bytes.

        If the data size is large than the max_sync_chunk_size, the decompression
        will be done in the executor. Otherwise, the decompression will be done
        in the event loop.
        """
        if (
            self._max_sync_chunk_size is not None
            and len(data) > self._max_sync_chunk_size
        ):
            return await asyncio.get_running_loop().run_in_executor(
                self._executor, self._decompressor.decompress, data, max_length
            )
        return self.decompress_sync(data, max_length)

    def flush(self, length: int = 0) -> bytes:
        return (
            self._decompressor.flush(length)
            if length > 0
            else self._decompressor.flush()
        )

    @property
    def eof(self) -> bool:
        return self._decompressor.eof


class BrotliDecompressor:
    # Supports both 'brotlipy' and 'Brotli' packages
    # since they share an import name. The top branches
    # are for 'brotlipy' and bottom branches for 'Brotli'
    def __init__(self) -> None:
        if not HAS_BROTLI:
            raise RuntimeError(
                "The brotli decompression is not available. "
                "Please install `Brotli` module"
            )
        self._obj = brotli.Decompressor()

    def decompress_sync(self, data: bytes) -> bytes:
        if hasattr(self._obj, "decompress"):
            return cast(bytes, self._obj.decompress(data))
        return cast(bytes, self._obj.process(data))

    def flush(self) -> bytes:
        if hasattr(self._obj, "flush"):
            return cast(bytes, self._obj.flush())
        return b""

# === NexusCore/openenv\Lib\site-packages\aiohttp\__init__.py ===
__version__ = "3.12.13"

from typing import TYPE_CHECKING, Tuple

from . import hdrs as hdrs
from .client import (
    BaseConnector,
    ClientConnectionError,
    ClientConnectionResetError,
    ClientConnectorCertificateError,
    ClientConnectorDNSError,
    ClientConnectorError,
    ClientConnectorSSLError,
    ClientError,
    ClientHttpProxyError,
    ClientOSError,
    ClientPayloadError,
    ClientProxyConnectionError,
    ClientRequest,
    ClientResponse,
    ClientResponseError,
    ClientSession,
    ClientSSLError,
    ClientTimeout,
    ClientWebSocketResponse,
    ClientWSTimeout,
    ConnectionTimeoutError,
    ContentTypeError,
    Fingerprint,
    InvalidURL,
    InvalidUrlClientError,
    InvalidUrlRedirectClientError,
    NamedPipeConnector,
    NonHttpUrlClientError,
    NonHttpUrlRedirectClientError,
    RedirectClientError,
    RequestInfo,
    ServerConnectionError,
    ServerDisconnectedError,
    ServerFingerprintMismatch,
    ServerTimeoutError,
    SocketTimeoutError,
    TCPConnector,
    TooManyRedirects,
    UnixConnector,
    WSMessageTypeError,
    WSServerHandshakeError,
    request,
)
from .client_middleware_digest_auth import DigestAuthMiddleware
from .client_middlewares import ClientHandlerType, ClientMiddlewareType
from .compression_utils import set_zlib_backend
from .connector import (
    AddrInfoType as AddrInfoType,
    SocketFactoryType as SocketFactoryType,
)
from .cookiejar import CookieJar as CookieJar, DummyCookieJar as DummyCookieJar
from .formdata import FormData as FormData
from .helpers import BasicAuth, ChainMapProxy, ETag
from .http import (
    HttpVersion as HttpVersion,
    HttpVersion10 as HttpVersion10,
    HttpVersion11 as HttpVersion11,
    WebSocketError as WebSocketError,
    WSCloseCode as WSCloseCode,
    WSMessage as WSMessage,
    WSMsgType as WSMsgType,
)
from .multipart import (
    BadContentDispositionHeader as BadContentDispositionHeader,
    BadContentDispositionParam as BadContentDispositionParam,
    BodyPartReader as BodyPartReader,
    MultipartReader as MultipartReader,
    MultipartWriter as MultipartWriter,
    content_disposition_filename as content_disposition_filename,
    parse_content_disposition as parse_content_disposition,
)
from .payload import (
    PAYLOAD_REGISTRY as PAYLOAD_REGISTRY,
    AsyncIterablePayload as AsyncIterablePayload,
    BufferedReaderPayload as BufferedReaderPayload,
    BytesIOPayload as BytesIOPayload,
    BytesPayload as BytesPayload,
    IOBasePayload as IOBasePayload,
    JsonPayload as JsonPayload,
    Payload as Payload,
    StringIOPayload as StringIOPayload,
    StringPayload as StringPayload,
    TextIOPayload as TextIOPayload,
    get_payload as get_payload,
    payload_type as payload_type,
)
from .payload_streamer import streamer as streamer
from .resolver import (
    AsyncResolver as AsyncResolver,
    DefaultResolver as DefaultResolver,
    ThreadedResolver as ThreadedResolver,
)
from .streams import (
    EMPTY_PAYLOAD as EMPTY_PAYLOAD,
    DataQueue as DataQueue,
    EofStream as EofStream,
    FlowControlDataQueue as FlowControlDataQueue,
    StreamReader as StreamReader,
)
from .tracing import (
    TraceConfig as TraceConfig,
    TraceConnectionCreateEndParams as TraceConnectionCreateEndParams,
    TraceConnectionCreateStartParams as TraceConnectionCreateStartParams,
    TraceConnectionQueuedEndParams as TraceConnectionQueuedEndParams,
    TraceConnectionQueuedStartParams as TraceConnectionQueuedStartParams,
    TraceConnectionReuseconnParams as TraceConnectionReuseconnParams,
    TraceDnsCacheHitParams as TraceDnsCacheHitParams,
    TraceDnsCacheMissParams as TraceDnsCacheMissParams,
    TraceDnsResolveHostEndParams as TraceDnsResolveHostEndParams,
    TraceDnsResolveHostStartParams as TraceDnsResolveHostStartParams,
    TraceRequestChunkSentParams as TraceRequestChunkSentParams,
    TraceRequestEndParams as TraceRequestEndParams,
    TraceRequestExceptionParams as TraceRequestExceptionParams,
    TraceRequestHeadersSentParams as TraceRequestHeadersSentParams,
    TraceRequestRedirectParams as TraceRequestRedirectParams,
    TraceRequestStartParams as TraceRequestStartParams,
    TraceResponseChunkReceivedParams as TraceResponseChunkReceivedParams,
)

if TYPE_CHECKING:
    # At runtime these are lazy-loaded at the bottom of the file.
    from .worker import (
        GunicornUVLoopWebWorker as GunicornUVLoopWebWorker,
        GunicornWebWorker as GunicornWebWorker,
    )

__all__: Tuple[str, ...] = (
    "hdrs",
    # client
    "AddrInfoType",
    "BaseConnector",
    "ClientConnectionError",
    "ClientConnectionResetError",
    "ClientConnectorCertificateError",
    "ClientConnectorDNSError",
    "ClientConnectorError",
    "ClientConnectorSSLError",
    "ClientError",
    "ClientHttpProxyError",
    "ClientOSError",
    "ClientPayloadError",
    "ClientProxyConnectionError",
    "ClientResponse",
    "ClientRequest",
    "ClientResponseError",
    "ClientSSLError",
    "ClientSession",
    "ClientTimeout",
    "ClientWebSocketResponse",
    "ClientWSTimeout",
    "ConnectionTimeoutError",
    "ContentTypeError",
    "Fingerprint",
    "FlowControlDataQueue",
    "InvalidURL",
    "InvalidUrlClientError",
    "InvalidUrlRedirectClientError",
    "NonHttpUrlClientError",
    "NonHttpUrlRedirectClientError",
    "RedirectClientError",
    "RequestInfo",
    "ServerConnectionError",
    "ServerDisconnectedError",
    "ServerFingerprintMismatch",
    "ServerTimeoutError",
    "SocketFactoryType",
    "SocketTimeoutError",
    "TCPConnector",
    "TooManyRedirects",
    "UnixConnector",
    "NamedPipeConnector",
    "WSServerHandshakeError",
    "request",
    # client_middleware
    "ClientMiddlewareType",
    "ClientHandlerType",
    # cookiejar
    "CookieJar",
    "DummyCookieJar",
    # formdata
    "FormData",
    # helpers
    "BasicAuth",
    "ChainMapProxy",
    "DigestAuthMiddleware",
    "ETag",
    "set_zlib_backend",
    # http
    "HttpVersion",
    "HttpVersion10",
    "HttpVersion11",
    "WSMsgType",
    "WSCloseCode",
    "WSMessage",
    "WebSocketError",
    # multipart
    "BadContentDispositionHeader",
    "BadContentDispositionParam",
    "BodyPartReader",
    "MultipartReader",
    "MultipartWriter",
    "content_disposition_filename",
    "parse_content_disposition",
    # payload
    "AsyncIterablePayload",
    "BufferedReaderPayload",
    "BytesIOPayload",
    "BytesPayload",
    "IOBasePayload",
    "JsonPayload",
    "PAYLOAD_REGISTRY",
    "Payload",
    "StringIOPayload",
    "StringPayload",
    "TextIOPayload",
    "get_payload",
    "payload_type",
    # payload_streamer
    "streamer",
    # resolver
    "AsyncResolver",
    "DefaultResolver",
    "ThreadedResolver",
    # streams
    "DataQueue",
    "EMPTY_PAYLOAD",
    "EofStream",
    "StreamReader",
    # tracing
    "TraceConfig",
    "TraceConnectionCreateEndParams",
    "TraceConnectionCreateStartParams",
    "TraceConnectionQueuedEndParams",
    "TraceConnectionQueuedStartParams",
    "TraceConnectionReuseconnParams",
    "TraceDnsCacheHitParams",
    "TraceDnsCacheMissParams",
    "TraceDnsResolveHostEndParams",
    "TraceDnsResolveHostStartParams",
    "TraceRequestChunkSentParams",
    "TraceRequestEndParams",
    "TraceRequestExceptionParams",
    "TraceRequestHeadersSentParams",
    "TraceRequestRedirectParams",
    "TraceRequestStartParams",
    "TraceResponseChunkReceivedParams",
    # workers (imported lazily with __getattr__)
    "GunicornUVLoopWebWorker",
    "GunicornWebWorker",
    "WSMessageTypeError",
)


def __dir__() -> Tuple[str, ...]:
    return __all__ + ("__doc__",)


def __getattr__(name: str) -> object:
    global GunicornUVLoopWebWorker, GunicornWebWorker

    # Importing gunicorn takes a long time (>100ms), so only import if actually needed.
    if name in ("GunicornUVLoopWebWorker", "GunicornWebWorker"):
        try:
            from .worker import GunicornUVLoopWebWorker as guv, GunicornWebWorker as gw
        except ImportError:
            return None

        GunicornUVLoopWebWorker = guv  # type: ignore[misc]
        GunicornWebWorker = gw  # type: ignore[misc]
        return guv if name == "GunicornUVLoopWebWorker" else gw

    raise AttributeError(f"module {__name__} has no attribute {name}")

# === NexusCore/openenv\Lib\site-packages\starlette\formparsers.py ===
from __future__ import annotations

import typing
from dataclasses import dataclass, field
from enum import Enum
from tempfile import SpooledTemporaryFile
from urllib.parse import unquote_plus

from starlette.datastructures import FormData, Headers, UploadFile

try:
    import multipart
    from multipart.multipart import parse_options_header
except ModuleNotFoundError:  # pragma: nocover
    parse_options_header = None
    multipart = None


class FormMessage(Enum):
    FIELD_START = 1
    FIELD_NAME = 2
    FIELD_DATA = 3
    FIELD_END = 4
    END = 5


@dataclass
class MultipartPart:
    content_disposition: bytes | None = None
    field_name: str = ""
    data: bytes = b""
    file: UploadFile | None = None
    item_headers: list[tuple[bytes, bytes]] = field(default_factory=list)


def _user_safe_decode(src: bytes, codec: str) -> str:
    try:
        return src.decode(codec)
    except (UnicodeDecodeError, LookupError):
        return src.decode("latin-1")


class MultiPartException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


class FormParser:
    def __init__(
        self, headers: Headers, stream: typing.AsyncGenerator[bytes, None]
    ) -> None:
        assert (
            multipart is not None
        ), "The `python-multipart` library must be installed to use form parsing."
        self.headers = headers
        self.stream = stream
        self.messages: list[tuple[FormMessage, bytes]] = []

    def on_field_start(self) -> None:
        message = (FormMessage.FIELD_START, b"")
        self.messages.append(message)

    def on_field_name(self, data: bytes, start: int, end: int) -> None:
        message = (FormMessage.FIELD_NAME, data[start:end])
        self.messages.append(message)

    def on_field_data(self, data: bytes, start: int, end: int) -> None:
        message = (FormMessage.FIELD_DATA, data[start:end])
        self.messages.append(message)

    def on_field_end(self) -> None:
        message = (FormMessage.FIELD_END, b"")
        self.messages.append(message)

    def on_end(self) -> None:
        message = (FormMessage.END, b"")
        self.messages.append(message)

    async def parse(self) -> FormData:
        # Callbacks dictionary.
        callbacks = {
            "on_field_start": self.on_field_start,
            "on_field_name": self.on_field_name,
            "on_field_data": self.on_field_data,
            "on_field_end": self.on_field_end,
            "on_end": self.on_end,
        }

        # Create the parser.
        parser = multipart.QuerystringParser(callbacks)
        field_name = b""
        field_value = b""

        items: list[tuple[str, str | UploadFile]] = []

        # Feed the parser with data from the request.
        async for chunk in self.stream:
            if chunk:
                parser.write(chunk)
            else:
                parser.finalize()
            messages = list(self.messages)
            self.messages.clear()
            for message_type, message_bytes in messages:
                if message_type == FormMessage.FIELD_START:
                    field_name = b""
                    field_value = b""
                elif message_type == FormMessage.FIELD_NAME:
                    field_name += message_bytes
                elif message_type == FormMessage.FIELD_DATA:
                    field_value += message_bytes
                elif message_type == FormMessage.FIELD_END:
                    name = unquote_plus(field_name.decode("latin-1"))
                    value = unquote_plus(field_value.decode("latin-1"))
                    items.append((name, value))

        return FormData(items)


class MultiPartParser:
    max_file_size = 1024 * 1024

    def __init__(
        self,
        headers: Headers,
        stream: typing.AsyncGenerator[bytes, None],
        *,
        max_files: int | float = 1000,
        max_fields: int | float = 1000,
    ) -> None:
        assert (
            multipart is not None
        ), "The `python-multipart` library must be installed to use form parsing."
        self.headers = headers
        self.stream = stream
        self.max_files = max_files
        self.max_fields = max_fields
        self.items: list[tuple[str, str | UploadFile]] = []
        self._current_files = 0
        self._current_fields = 0
        self._current_partial_header_name: bytes = b""
        self._current_partial_header_value: bytes = b""
        self._current_part = MultipartPart()
        self._charset = ""
        self._file_parts_to_write: list[tuple[MultipartPart, bytes]] = []
        self._file_parts_to_finish: list[MultipartPart] = []
        self._files_to_close_on_error: list[SpooledTemporaryFile[bytes]] = []

    def on_part_begin(self) -> None:
        self._current_part = MultipartPart()

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        message_bytes = data[start:end]
        if self._current_part.file is None:
            self._current_part.data += message_bytes
        else:
            self._file_parts_to_write.append((self._current_part, message_bytes))

    def on_part_end(self) -> None:
        if self._current_part.file is None:
            self.items.append(
                (
                    self._current_part.field_name,
                    _user_safe_decode(self._current_part.data, self._charset),
                )
            )
        else:
            self._file_parts_to_finish.append(self._current_part)
            # The file can be added to the items right now even though it's not
            # finished yet, because it will be finished in the `parse()` method, before
            # self.items is used in the return value.
            self.items.append((self._current_part.field_name, self._current_part.file))

    def on_header_field(self, data: bytes, start: int, end: int) -> None:
        self._current_partial_header_name += data[start:end]

    def on_header_value(self, data: bytes, start: int, end: int) -> None:
        self._current_partial_header_value += data[start:end]

    def on_header_end(self) -> None:
        field = self._current_partial_header_name.lower()
        if field == b"content-disposition":
            self._current_part.content_disposition = self._current_partial_header_value
        self._current_part.item_headers.append(
            (field, self._current_partial_header_value)
        )
        self._current_partial_header_name = b""
        self._current_partial_header_value = b""

    def on_headers_finished(self) -> None:
        disposition, options = parse_options_header(
            self._current_part.content_disposition
        )
        try:
            self._current_part.field_name = _user_safe_decode(
                options[b"name"], self._charset
            )
        except KeyError:
            raise MultiPartException(
                'The Content-Disposition header field "name" must be ' "provided."
            )
        if b"filename" in options:
            self._current_files += 1
            if self._current_files > self.max_files:
                raise MultiPartException(
                    f"Too many files. Maximum number of files is {self.max_files}."
                )
            filename = _user_safe_decode(options[b"filename"], self._charset)
            tempfile = SpooledTemporaryFile(max_size=self.max_file_size)
            self._files_to_close_on_error.append(tempfile)
            self._current_part.file = UploadFile(
                file=tempfile,  # type: ignore[arg-type]
                size=0,
                filename=filename,
                headers=Headers(raw=self._current_part.item_headers),
            )
        else:
            self._current_fields += 1
            if self._current_fields > self.max_fields:
                raise MultiPartException(
                    f"Too many fields. Maximum number of fields is {self.max_fields}."
                )
            self._current_part.file = None

    def on_end(self) -> None:
        pass

    async def parse(self) -> FormData:
        # Parse the Content-Type header to get the multipart boundary.
        _, params = parse_options_header(self.headers["Content-Type"])
        charset = params.get(b"charset", "utf-8")
        if isinstance(charset, bytes):
            charset = charset.decode("latin-1")
        self._charset = charset
        try:
            boundary = params[b"boundary"]
        except KeyError:
            raise MultiPartException("Missing boundary in multipart.")

        # Callbacks dictionary.
        callbacks = {
            "on_part_begin": self.on_part_begin,
            "on_part_data": self.on_part_data,
            "on_part_end": self.on_part_end,
            "on_header_field": self.on_header_field,
            "on_header_value": self.on_header_value,
            "on_header_end": self.on_header_end,
            "on_headers_finished": self.on_headers_finished,
            "on_end": self.on_end,
        }

        # Create the parser.
        parser = multipart.MultipartParser(boundary, callbacks)
        try:
            # Feed the parser with data from the request.
            async for chunk in self.stream:
                parser.write(chunk)
                # Write file data, it needs to use await with the UploadFile methods
                # that call the corresponding file methods *in a threadpool*,
                # otherwise, if they were called directly in the callback methods above
                # (regular, non-async functions), that would block the event loop in
                # the main thread.
                for part, data in self._file_parts_to_write:
                    assert part.file  # for type checkers
                    await part.file.write(data)
                for part in self._file_parts_to_finish:
                    assert part.file  # for type checkers
                    await part.file.seek(0)
                self._file_parts_to_write.clear()
                self._file_parts_to_finish.clear()
        except MultiPartException as exc:
            # Close all the files if there was an error.
            for file in self._files_to_close_on_error:
                file.close()
            raise exc

        parser.finalize()
        return FormData(self.items)

# === NexusCore/openenv\Lib\site-packages\urllib3\_request_methods.py ===
from __future__ import annotations

import json as _json
import typing
from urllib.parse import urlencode

from ._base_connection import _TYPE_BODY
from ._collections import HTTPHeaderDict
from .filepost import _TYPE_FIELDS, encode_multipart_formdata
from .response import BaseHTTPResponse

__all__ = ["RequestMethods"]

_TYPE_ENCODE_URL_FIELDS = typing.Union[
    typing.Sequence[tuple[str, typing.Union[str, bytes]]],
    typing.Mapping[str, typing.Union[str, bytes]],
]


class RequestMethods:
    """
    Convenience mixin for classes who implement a :meth:`urlopen` method, such
    as :class:`urllib3.HTTPConnectionPool` and
    :class:`urllib3.PoolManager`.

    Provides behavior for making common types of HTTP request methods and
    decides which type of request field encoding to use.

    Specifically,

    :meth:`.request_encode_url` is for sending requests whose fields are
    encoded in the URL (such as GET, HEAD, DELETE).

    :meth:`.request_encode_body` is for sending requests whose fields are
    encoded in the *body* of the request using multipart or www-form-urlencoded
    (such as for POST, PUT, PATCH).

    :meth:`.request` is for making any kind of request, it will look up the
    appropriate encoding format and use one of the above two methods to make
    the request.

    Initializer parameters:

    :param headers:
        Headers to include with all requests, unless other headers are given
        explicitly.
    """

    _encode_url_methods = {"DELETE", "GET", "HEAD", "OPTIONS"}

    def __init__(self, headers: typing.Mapping[str, str] | None = None) -> None:
        self.headers = headers or {}

    def urlopen(
        self,
        method: str,
        url: str,
        body: _TYPE_BODY | None = None,
        headers: typing.Mapping[str, str] | None = None,
        encode_multipart: bool = True,
        multipart_boundary: str | None = None,
        **kw: typing.Any,
    ) -> BaseHTTPResponse:  # Abstract
        raise NotImplementedError(
            "Classes extending RequestMethods must implement "
            "their own ``urlopen`` method."
        )

    def request(
        self,
        method: str,
        url: str,
        body: _TYPE_BODY | None = None,
        fields: _TYPE_FIELDS | None = None,
        headers: typing.Mapping[str, str] | None = None,
        json: typing.Any | None = None,
        **urlopen_kw: typing.Any,
    ) -> BaseHTTPResponse:
        """
        Make a request using :meth:`urlopen` with the appropriate encoding of
        ``fields`` based on the ``method`` used.

        This is a convenience method that requires the least amount of manual
        effort. It can be used in most situations, while still having the
        option to drop down to more specific methods when necessary, such as
        :meth:`request_encode_url`, :meth:`request_encode_body`,
        or even the lowest level :meth:`urlopen`.

        :param method:
            HTTP request method (such as GET, POST, PUT, etc.)

        :param url:
            The URL to perform the request on.

        :param body:
            Data to send in the request body, either :class:`str`, :class:`bytes`,
            an iterable of :class:`str`/:class:`bytes`, or a file-like object.

        :param fields:
            Data to encode and send in the URL or request body, depending on ``method``.

        :param headers:
            Dictionary of custom headers to send, such as User-Agent,
            If-None-Match, etc. If None, pool headers are used. If provided,
            these headers completely replace any pool-specific headers.

        :param json:
            Data to encode and send as JSON with UTF-encoded in the request body.
            The ``"Content-Type"`` header will be set to ``"application/json"``
            unless specified otherwise.
        """
        method = method.upper()

        if json is not None and body is not None:
            raise TypeError(
                "request got values for both 'body' and 'json' parameters which are mutually exclusive"
            )

        if json is not None:
            if headers is None:
                headers = self.headers

            if not ("content-type" in map(str.lower, headers.keys())):
                headers = HTTPHeaderDict(headers)
                headers["Content-Type"] = "application/json"

            body = _json.dumps(json, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )

        if body is not None:
            urlopen_kw["body"] = body

        if method in self._encode_url_methods:
            return self.request_encode_url(
                method,
                url,
                fields=fields,  # type: ignore[arg-type]
                headers=headers,
                **urlopen_kw,
            )
        else:
            return self.request_encode_body(
                method, url, fields=fields, headers=headers, **urlopen_kw
            )

    def request_encode_url(
        self,
        method: str,
        url: str,
        fields: _TYPE_ENCODE_URL_FIELDS | None = None,
        headers: typing.Mapping[str, str] | None = None,
        **urlopen_kw: str,
    ) -> BaseHTTPResponse:
        """
        Make a request using :meth:`urlopen` with the ``fields`` encoded in
        the url. This is useful for request methods like GET, HEAD, DELETE, etc.

        :param method:
            HTTP request method (such as GET, POST, PUT, etc.)

        :param url:
            The URL to perform the request on.

        :param fields:
            Data to encode and send in the URL.

        :param headers:
            Dictionary of custom headers to send, such as User-Agent,
            If-None-Match, etc. If None, pool headers are used. If provided,
            these headers completely replace any pool-specific headers.
        """
        if headers is None:
            headers = self.headers

        extra_kw: dict[str, typing.Any] = {"headers": headers}
        extra_kw.update(urlopen_kw)

        if fields:
            url += "?" + urlencode(fields)

        return self.urlopen(method, url, **extra_kw)

    def request_encode_body(
        self,
        method: str,
        url: str,
        fields: _TYPE_FIELDS | None = None,
        headers: typing.Mapping[str, str] | None = None,
        encode_multipart: bool = True,
        multipart_boundary: str | None = None,
        **urlopen_kw: str,
    ) -> BaseHTTPResponse:
        """
        Make a request using :meth:`urlopen` with the ``fields`` encoded in
        the body. This is useful for request methods like POST, PUT, PATCH, etc.

        When ``encode_multipart=True`` (default), then
        :func:`urllib3.encode_multipart_formdata` is used to encode
        the payload with the appropriate content type. Otherwise
        :func:`urllib.parse.urlencode` is used with the
        'application/x-www-form-urlencoded' content type.

        Multipart encoding must be used when posting files, and it's reasonably
        safe to use it in other times too. However, it may break request
        signing, such as with OAuth.

        Supports an optional ``fields`` parameter of key/value strings AND
        key/filetuple. A filetuple is a (filename, data, MIME type) tuple where
        the MIME type is optional. For example::

            fields = {
                'foo': 'bar',
                'fakefile': ('foofile.txt', 'contents of foofile'),
                'realfile': ('barfile.txt', open('realfile').read()),
                'typedfile': ('bazfile.bin', open('bazfile').read(),
                              'image/jpeg'),
                'nonamefile': 'contents of nonamefile field',
            }

        When uploading a file, providing a filename (the first parameter of the
        tuple) is optional but recommended to best mimic behavior of browsers.

        Note that if ``headers`` are supplied, the 'Content-Type' header will
        be overwritten because it depends on the dynamic random boundary string
        which is used to compose the body of the request. The random boundary
        string can be explicitly set with the ``multipart_boundary`` parameter.

        :param method:
            HTTP request method (such as GET, POST, PUT, etc.)

        :param url:
            The URL to perform the request on.

        :param fields:
            Data to encode and send in the request body.

        :param headers:
            Dictionary of custom headers to send, such as User-Agent,
            If-None-Match, etc. If None, pool headers are used. If provided,
            these headers completely replace any pool-specific headers.

        :param encode_multipart:
            If True, encode the ``fields`` using the multipart/form-data MIME
            format.

        :param multipart_boundary:
            If not specified, then a random boundary will be generated using
            :func:`urllib3.filepost.choose_boundary`.
        """
        if headers is None:
            headers = self.headers

        extra_kw: dict[str, typing.Any] = {"headers": HTTPHeaderDict(headers)}
        body: bytes | str

        if fields:
            if "body" in urlopen_kw:
                raise TypeError(
                    "request got values for both 'fields' and 'body', can only specify one."
                )

            if encode_multipart:
                body, content_type = encode_multipart_formdata(
                    fields, boundary=multipart_boundary
                )
            else:
                body, content_type = (
                    urlencode(fields),  # type: ignore[arg-type]
                    "application/x-www-form-urlencoded",
                )

            extra_kw["body"] = body
            extra_kw["headers"].setdefault("Content-Type", content_type)

        extra_kw.update(urlopen_kw)

        return self.urlopen(method, url, **extra_kw)

# === NexusCore/openenv\Lib\site-packages\gitdb\db\base.py ===
# Copyright (C) 2010, 2011 Sebastian Thiel (byronimo@gmail.com) and contributors
#
# This module is part of GitDB and is released under
# the New BSD License: https://opensource.org/license/bsd-3-clause/
"""Contains implementations of database retrieveing objects"""
from gitdb.util import (
    join,
    LazyMixin,
    hex_to_bin
)

from gitdb.utils.encoding import force_text
from gitdb.exc import (
    BadObject,
    AmbiguousObjectName
)

from itertools import chain
from functools import reduce


__all__ = ('ObjectDBR', 'ObjectDBW', 'FileDBBase', 'CompoundDB', 'CachingDB')


class ObjectDBR:

    """Defines an interface for object database lookup.
    Objects are identified either by their 20 byte bin sha"""

    def __contains__(self, sha):
        return self.has_obj

    #{ Query Interface
    def has_object(self, sha):
        """
        Whether the object identified by the given 20 bytes
            binary sha is contained in the database

        :return: True if the object identified by the given 20 bytes
            binary sha is contained in the database"""
        raise NotImplementedError("To be implemented in subclass")

    def info(self, sha):
        """ :return: OInfo instance
        :param sha: bytes binary sha
        :raise BadObject:"""
        raise NotImplementedError("To be implemented in subclass")

    def stream(self, sha):
        """:return: OStream instance
        :param sha: 20 bytes binary sha
        :raise BadObject:"""
        raise NotImplementedError("To be implemented in subclass")

    def size(self):
        """:return: amount of objects in this database"""
        raise NotImplementedError()

    def sha_iter(self):
        """Return iterator yielding 20 byte shas for all objects in this data base"""
        raise NotImplementedError()

    #} END query interface


class ObjectDBW:

    """Defines an interface to create objects in the database"""

    def __init__(self, *args, **kwargs):
        self._ostream = None

    #{ Edit Interface
    def set_ostream(self, stream):
        """
        Adjusts the stream to which all data should be sent when storing new objects

        :param stream: if not None, the stream to use, if None the default stream
            will be used.
        :return: previously installed stream, or None if there was no override
        :raise TypeError: if the stream doesn't have the supported functionality"""
        cstream = self._ostream
        self._ostream = stream
        return cstream

    def ostream(self):
        """
        Return the output stream

        :return: overridden output stream this instance will write to, or None
            if it will write to the default stream"""
        return self._ostream

    def store(self, istream):
        """
        Create a new object in the database
        :return: the input istream object with its sha set to its corresponding value

        :param istream: IStream compatible instance. If its sha is already set
            to a value, the object will just be stored in the our database format,
            in which case the input stream is expected to be in object format ( header + contents ).
        :raise IOError: if data could not be written"""
        raise NotImplementedError("To be implemented in subclass")

    #} END edit interface


class FileDBBase:

    """Provides basic facilities to retrieve files of interest, including
    caching facilities to help mapping hexsha's to objects"""

    def __init__(self, root_path):
        """Initialize this instance to look for its files at the given root path
        All subsequent operations will be relative to this path
        :raise InvalidDBRoot:
        **Note:** The base will not perform any accessablity checking as the base
            might not yet be accessible, but become accessible before the first
            access."""
        super().__init__()
        self._root_path = root_path

    #{ Interface
    def root_path(self):
        """:return: path at which this db operates"""
        return self._root_path

    def db_path(self, rela_path):
        """
        :return: the given relative path relative to our database root, allowing
            to pontentially access datafiles"""
        return join(self._root_path, force_text(rela_path))
    #} END interface


class CachingDB:

    """A database which uses caches to speed-up access"""

    #{ Interface
    def update_cache(self, force=False):
        """
        Call this method if the underlying data changed to trigger an update
        of the internal caching structures.

        :param force: if True, the update must be performed. Otherwise the implementation
            may decide not to perform an update if it thinks nothing has changed.
        :return: True if an update was performed as something change indeed"""

    # END interface


def _databases_recursive(database, output):
    """Fill output list with database from db, in order. Deals with Loose, Packed
    and compound databases."""
    if isinstance(database, CompoundDB):
        dbs = database.databases()
        output.extend(db for db in dbs if not isinstance(db, CompoundDB))
        for cdb in (db for db in dbs if isinstance(db, CompoundDB)):
            _databases_recursive(cdb, output)
    else:
        output.append(database)
    # END handle database type


class CompoundDB(ObjectDBR, LazyMixin, CachingDB):

    """A database which delegates calls to sub-databases.

    Databases are stored in the lazy-loaded _dbs attribute.
    Define _set_cache_ to update it with your databases"""

    def _set_cache_(self, attr):
        if attr == '_dbs':
            self._dbs = list()
        elif attr == '_db_cache':
            self._db_cache = dict()
        else:
            super()._set_cache_(attr)

    def _db_query(self, sha):
        """:return: database containing the given 20 byte sha
        :raise BadObject:"""
        # most databases use binary representations, prevent converting
        # it every time a database is being queried
        try:
            return self._db_cache[sha]
        except KeyError:
            pass
        # END first level cache

        for db in self._dbs:
            if db.has_object(sha):
                self._db_cache[sha] = db
                return db
        # END for each database
        raise BadObject(sha)

    #{ ObjectDBR interface

    def has_object(self, sha):
        try:
            self._db_query(sha)
            return True
        except BadObject:
            return False
        # END handle exceptions

    def info(self, sha):
        return self._db_query(sha).info(sha)

    def stream(self, sha):
        return self._db_query(sha).stream(sha)

    def size(self):
        """:return: total size of all contained databases"""
        return reduce(lambda x, y: x + y, (db.size() for db in self._dbs), 0)

    def sha_iter(self):
        return chain(*(db.sha_iter() for db in self._dbs))

    #} END object DBR Interface

    #{ Interface

    def databases(self):
        """:return: tuple of database instances we use for lookups"""
        return tuple(self._dbs)

    def update_cache(self, force=False):
        # something might have changed, clear everything
        self._db_cache.clear()
        stat = False
        for db in self._dbs:
            if isinstance(db, CachingDB):
                stat |= db.update_cache(force)
            # END if is caching db
        # END for each database to update
        return stat

    def partial_to_complete_sha_hex(self, partial_hexsha):
        """
        :return: 20 byte binary sha1 from the given less-than-40 byte hexsha (bytes or str)
        :param partial_hexsha: hexsha with less than 40 byte
        :raise AmbiguousObjectName: """
        databases = list()
        _databases_recursive(self, databases)
        partial_hexsha = force_text(partial_hexsha)
        len_partial_hexsha = len(partial_hexsha)
        if len_partial_hexsha % 2 != 0:
            partial_binsha = hex_to_bin(partial_hexsha + "0")
        else:
            partial_binsha = hex_to_bin(partial_hexsha)
        # END assure successful binary conversion

        candidate = None
        for db in databases:
            full_bin_sha = None
            try:
                if hasattr(db, 'partial_to_complete_sha_hex'):
                    full_bin_sha = db.partial_to_complete_sha_hex(partial_hexsha)
                else:
                    full_bin_sha = db.partial_to_complete_sha(partial_binsha, len_partial_hexsha)
                # END handle database type
            except BadObject:
                continue
            # END ignore bad objects
            if full_bin_sha:
                if candidate and candidate != full_bin_sha:
                    raise AmbiguousObjectName(partial_hexsha)
                candidate = full_bin_sha
            # END handle candidate
        # END for each db
        if not candidate:
            raise BadObject(partial_binsha)
        return candidate

    #} END interface

# === NexusCore/openenv\Lib\site-packages\litellm\llms\openai\fine_tuning\handler.py ===
from typing import Any, Coroutine, Optional, Union, cast

import httpx
from openai import AsyncAzureOpenAI, AsyncOpenAI, AzureOpenAI, OpenAI

from litellm._logging import verbose_logger
from litellm.types.utils import LiteLLMFineTuningJob


class OpenAIFineTuningAPI:
    """
    OpenAI methods to support for batches
    """

    def __init__(self) -> None:
        super().__init__()

    def get_openai_client(
        self,
        api_key: Optional[str],
        api_base: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        organization: Optional[str],
        client: Optional[
            Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI]
        ] = None,
        _is_async: bool = False,
        api_version: Optional[str] = None,
        litellm_params: Optional[dict] = None,
    ) -> Optional[Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI,]]:
        received_args = locals()
        openai_client: Optional[
            Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI]
        ] = None
        if client is None:
            data = {}
            for k, v in received_args.items():
                if k == "self" or k == "client" or k == "_is_async":
                    pass
                elif k == "api_base" and v is not None:
                    data["base_url"] = v
                elif v is not None:
                    data[k] = v
            if _is_async is True:
                openai_client = AsyncOpenAI(**data)
            else:
                openai_client = OpenAI(**data)  # type: ignore
        else:
            openai_client = client

        return openai_client

    async def acreate_fine_tuning_job(
        self,
        create_fine_tuning_job_data: dict,
        openai_client: Union[AsyncOpenAI, AsyncAzureOpenAI],
    ) -> LiteLLMFineTuningJob:
        response = await openai_client.fine_tuning.jobs.create(
            **create_fine_tuning_job_data
        )

        return LiteLLMFineTuningJob(**response.model_dump())

    def create_fine_tuning_job(
        self,
        _is_async: bool,
        create_fine_tuning_job_data: dict,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        organization: Optional[str],
        client: Optional[
            Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI]
        ] = None,
    ) -> Union[LiteLLMFineTuningJob, Coroutine[Any, Any, LiteLLMFineTuningJob]]:
        openai_client: Optional[
            Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI]
        ] = self.get_openai_client(
            api_key=api_key,
            api_base=api_base,
            timeout=timeout,
            max_retries=max_retries,
            organization=organization,
            client=client,
            _is_async=_is_async,
            api_version=api_version,
        )
        if openai_client is None:
            raise ValueError(
                "OpenAI client is not initialized. Make sure api_key is passed or OPENAI_API_KEY is set in the environment."
            )

        if _is_async is True:
            if not isinstance(openai_client, (AsyncOpenAI, AsyncAzureOpenAI)):
                raise ValueError(
                    "OpenAI client is not an instance of AsyncOpenAI. Make sure you passed an AsyncOpenAI client."
                )
            return self.acreate_fine_tuning_job(  # type: ignore
                create_fine_tuning_job_data=create_fine_tuning_job_data,
                openai_client=openai_client,
            )
        verbose_logger.debug(
            "creating fine tuning job, args= %s", create_fine_tuning_job_data
        )
        response = cast(OpenAI, openai_client).fine_tuning.jobs.create(
            **create_fine_tuning_job_data
        )
        return LiteLLMFineTuningJob(**response.model_dump())

    async def acancel_fine_tuning_job(
        self,
        fine_tuning_job_id: str,
        openai_client: Union[AsyncOpenAI, AsyncAzureOpenAI],
    ) -> LiteLLMFineTuningJob:
        response = await openai_client.fine_tuning.jobs.cancel(
            fine_tuning_job_id=fine_tuning_job_id
        )
        return LiteLLMFineTuningJob(**response.model_dump())

    def cancel_fine_tuning_job(
        self,
        _is_async: bool,
        fine_tuning_job_id: str,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        organization: Optional[str],
        client: Optional[
            Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI]
        ] = None,
    ) -> Union[LiteLLMFineTuningJob, Coroutine[Any, Any, LiteLLMFineTuningJob]]:
        openai_client: Optional[
            Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI]
        ] = self.get_openai_client(
            api_key=api_key,
            api_base=api_base,
            timeout=timeout,
            max_retries=max_retries,
            organization=organization,
            client=client,
            _is_async=_is_async,
            api_version=api_version,
        )
        if openai_client is None:
            raise ValueError(
                "OpenAI client is not initialized. Make sure api_key is passed or OPENAI_API_KEY is set in the environment."
            )

        if _is_async is True:
            if not isinstance(openai_client, (AsyncOpenAI, AsyncAzureOpenAI)):
                raise ValueError(
                    "OpenAI client is not an instance of AsyncOpenAI. Make sure you passed an AsyncOpenAI client."
                )
            return self.acancel_fine_tuning_job(  # type: ignore
                fine_tuning_job_id=fine_tuning_job_id,
                openai_client=openai_client,
            )
        verbose_logger.debug("canceling fine tuning job, args= %s", fine_tuning_job_id)
        response = cast(OpenAI, openai_client).fine_tuning.jobs.cancel(
            fine_tuning_job_id=fine_tuning_job_id
        )
        return LiteLLMFineTuningJob(**response.model_dump())

    async def alist_fine_tuning_jobs(
        self,
        openai_client: Union[AsyncOpenAI, AsyncAzureOpenAI],
        after: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        response = await openai_client.fine_tuning.jobs.list(after=after, limit=limit)  # type: ignore
        return response

    def list_fine_tuning_jobs(
        self,
        _is_async: bool,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        organization: Optional[str],
        client: Optional[
            Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI]
        ] = None,
        after: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        openai_client: Optional[
            Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI]
        ] = self.get_openai_client(
            api_key=api_key,
            api_base=api_base,
            timeout=timeout,
            max_retries=max_retries,
            organization=organization,
            client=client,
            _is_async=_is_async,
            api_version=api_version,
        )
        if openai_client is None:
            raise ValueError(
                "OpenAI client is not initialized. Make sure api_key is passed or OPENAI_API_KEY is set in the environment."
            )

        if _is_async is True:
            if not isinstance(openai_client, (AsyncOpenAI, AsyncAzureOpenAI)):
                raise ValueError(
                    "OpenAI client is not an instance of AsyncOpenAI. Make sure you passed an AsyncOpenAI client."
                )
            return self.alist_fine_tuning_jobs(  # type: ignore
                after=after,
                limit=limit,
                openai_client=openai_client,
            )
        verbose_logger.debug("list fine tuning job, after= %s, limit= %s", after, limit)
        response = openai_client.fine_tuning.jobs.list(after=after, limit=limit)  # type: ignore
        return response

    async def aretrieve_fine_tuning_job(
        self,
        fine_tuning_job_id: str,
        openai_client: Union[AsyncOpenAI, AsyncAzureOpenAI],
    ) -> LiteLLMFineTuningJob:
        response = await openai_client.fine_tuning.jobs.retrieve(
            fine_tuning_job_id=fine_tuning_job_id
        )
        return LiteLLMFineTuningJob(**response.model_dump())

    def retrieve_fine_tuning_job(
        self,
        _is_async: bool,
        fine_tuning_job_id: str,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        organization: Optional[str],
        client: Optional[
            Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI]
        ] = None,
    ) -> Union[LiteLLMFineTuningJob, Coroutine[Any, Any, LiteLLMFineTuningJob]]:
        openai_client: Optional[
            Union[OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI]
        ] = self.get_openai_client(
            api_key=api_key,
            api_base=api_base,
            timeout=timeout,
            max_retries=max_retries,
            organization=organization,
            client=client,
            _is_async=_is_async,
            api_version=api_version,
        )
        if openai_client is None:
            raise ValueError(
                "OpenAI client is not initialized. Make sure api_key is passed or OPENAI_API_KEY is set in the environment."
            )

        if _is_async is True:
            if not isinstance(openai_client, AsyncOpenAI):
                raise ValueError(
                    "OpenAI client is not an instance of AsyncOpenAI. Make sure you passed an AsyncOpenAI client."
                )
            return self.aretrieve_fine_tuning_job(  # type: ignore
                fine_tuning_job_id=fine_tuning_job_id,
                openai_client=openai_client,
            )
        verbose_logger.debug("retrieving fine tuning job, id= %s", fine_tuning_job_id)
        response = cast(OpenAI, openai_client).fine_tuning.jobs.retrieve(
            fine_tuning_job_id=fine_tuning_job_id
        )
        return LiteLLMFineTuningJob(**response.model_dump())

# === NexusCore/openenv\Lib\site-packages\colorama\ansitowin32.py ===
# Copyright Jonathan Hartley 2013. BSD 3-Clause license, see LICENSE file.
import re
import sys
import os

from .ansi import AnsiFore, AnsiBack, AnsiStyle, Style, BEL
from .winterm import enable_vt_processing, WinTerm, WinColor, WinStyle
from .win32 import windll, winapi_test


winterm = None
if windll is not None:
    winterm = WinTerm()


class StreamWrapper(object):
    '''
    Wraps a stream (such as stdout), acting as a transparent proxy for all
    attribute access apart from method 'write()', which is delegated to our
    Converter instance.
    '''
    def __init__(self, wrapped, converter):
        # double-underscore everything to prevent clashes with names of
        # attributes on the wrapped stream object.
        self.__wrapped = wrapped
        self.__convertor = converter

    def __getattr__(self, name):
        return getattr(self.__wrapped, name)

    def __enter__(self, *args, **kwargs):
        # special method lookup bypasses __getattr__/__getattribute__, see
        # https://stackoverflow.com/questions/12632894/why-doesnt-getattr-work-with-exit
        # thus, contextlib magic methods are not proxied via __getattr__
        return self.__wrapped.__enter__(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        return self.__wrapped.__exit__(*args, **kwargs)

    def __setstate__(self, state):
        self.__dict__ = state

    def __getstate__(self):
        return self.__dict__

    def write(self, text):
        self.__convertor.write(text)

    def isatty(self):
        stream = self.__wrapped
        if 'PYCHARM_HOSTED' in os.environ:
            if stream is not None and (stream is sys.__stdout__ or stream is sys.__stderr__):
                return True
        try:
            stream_isatty = stream.isatty
        except AttributeError:
            return False
        else:
            return stream_isatty()

    @property
    def closed(self):
        stream = self.__wrapped
        try:
            return stream.closed
        # AttributeError in the case that the stream doesn't support being closed
        # ValueError for the case that the stream has already been detached when atexit runs
        except (AttributeError, ValueError):
            return True


class AnsiToWin32(object):
    '''
    Implements a 'write()' method which, on Windows, will strip ANSI character
    sequences from the text, and if outputting to a tty, will convert them into
    win32 function calls.
    '''
    ANSI_CSI_RE = re.compile('\001?\033\\[((?:\\d|;)*)([a-zA-Z])\002?')   # Control Sequence Introducer
    ANSI_OSC_RE = re.compile('\001?\033\\]([^\a]*)(\a)\002?')             # Operating System Command

    def __init__(self, wrapped, convert=None, strip=None, autoreset=False):
        # The wrapped stream (normally sys.stdout or sys.stderr)
        self.wrapped = wrapped

        # should we reset colors to defaults after every .write()
        self.autoreset = autoreset

        # create the proxy wrapping our output stream
        self.stream = StreamWrapper(wrapped, self)

        on_windows = os.name == 'nt'
        # We test if the WinAPI works, because even if we are on Windows
        # we may be using a terminal that doesn't support the WinAPI
        # (e.g. Cygwin Terminal). In this case it's up to the terminal
        # to support the ANSI codes.
        conversion_supported = on_windows and winapi_test()
        try:
            fd = wrapped.fileno()
        except Exception:
            fd = -1
        system_has_native_ansi = not on_windows or enable_vt_processing(fd)
        have_tty = not self.stream.closed and self.stream.isatty()
        need_conversion = conversion_supported and not system_has_native_ansi

        # should we strip ANSI sequences from our output?
        if strip is None:
            strip = need_conversion or not have_tty
        self.strip = strip

        # should we should convert ANSI sequences into win32 calls?
        if convert is None:
            convert = need_conversion and have_tty
        self.convert = convert

        # dict of ansi codes to win32 functions and parameters
        self.win32_calls = self.get_win32_calls()

        # are we wrapping stderr?
        self.on_stderr = self.wrapped is sys.stderr

    def should_wrap(self):
        '''
        True if this class is actually needed. If false, then the output
        stream will not be affected, nor will win32 calls be issued, so
        wrapping stdout is not actually required. This will generally be
        False on non-Windows platforms, unless optional functionality like
        autoreset has been requested using kwargs to init()
        '''
        return self.convert or self.strip or self.autoreset

    def get_win32_calls(self):
        if self.convert and winterm:
            return {
                AnsiStyle.RESET_ALL: (winterm.reset_all, ),
                AnsiStyle.BRIGHT: (winterm.style, WinStyle.BRIGHT),
                AnsiStyle.DIM: (winterm.style, WinStyle.NORMAL),
                AnsiStyle.NORMAL: (winterm.style, WinStyle.NORMAL),
                AnsiFore.BLACK: (winterm.fore, WinColor.BLACK),
                AnsiFore.RED: (winterm.fore, WinColor.RED),
                AnsiFore.GREEN: (winterm.fore, WinColor.GREEN),
                AnsiFore.YELLOW: (winterm.fore, WinColor.YELLOW),
                AnsiFore.BLUE: (winterm.fore, WinColor.BLUE),
                AnsiFore.MAGENTA: (winterm.fore, WinColor.MAGENTA),
                AnsiFore.CYAN: (winterm.fore, WinColor.CYAN),
                AnsiFore.WHITE: (winterm.fore, WinColor.GREY),
                AnsiFore.RESET: (winterm.fore, ),
                AnsiFore.LIGHTBLACK_EX: (winterm.fore, WinColor.BLACK, True),
                AnsiFore.LIGHTRED_EX: (winterm.fore, WinColor.RED, True),
                AnsiFore.LIGHTGREEN_EX: (winterm.fore, WinColor.GREEN, True),
                AnsiFore.LIGHTYELLOW_EX: (winterm.fore, WinColor.YELLOW, True),
                AnsiFore.LIGHTBLUE_EX: (winterm.fore, WinColor.BLUE, True),
                AnsiFore.LIGHTMAGENTA_EX: (winterm.fore, WinColor.MAGENTA, True),
                AnsiFore.LIGHTCYAN_EX: (winterm.fore, WinColor.CYAN, True),
                AnsiFore.LIGHTWHITE_EX: (winterm.fore, WinColor.GREY, True),
                AnsiBack.BLACK: (winterm.back, WinColor.BLACK),
                AnsiBack.RED: (winterm.back, WinColor.RED),
                AnsiBack.GREEN: (winterm.back, WinColor.GREEN),
                AnsiBack.YELLOW: (winterm.back, WinColor.YELLOW),
                AnsiBack.BLUE: (winterm.back, WinColor.BLUE),
                AnsiBack.MAGENTA: (winterm.back, WinColor.MAGENTA),
                AnsiBack.CYAN: (winterm.back, WinColor.CYAN),
                AnsiBack.WHITE: (winterm.back, WinColor.GREY),
                AnsiBack.RESET: (winterm.back, ),
                AnsiBack.LIGHTBLACK_EX: (winterm.back, WinColor.BLACK, True),
                AnsiBack.LIGHTRED_EX: (winterm.back, WinColor.RED, True),
                AnsiBack.LIGHTGREEN_EX: (winterm.back, WinColor.GREEN, True),
                AnsiBack.LIGHTYELLOW_EX: (winterm.back, WinColor.YELLOW, True),
                AnsiBack.LIGHTBLUE_EX: (winterm.back, WinColor.BLUE, True),
                AnsiBack.LIGHTMAGENTA_EX: (winterm.back, WinColor.MAGENTA, True),
                AnsiBack.LIGHTCYAN_EX: (winterm.back, WinColor.CYAN, True),
                AnsiBack.LIGHTWHITE_EX: (winterm.back, WinColor.GREY, True),
            }
        return dict()

    def write(self, text):
        if self.strip or self.convert:
            self.write_and_convert(text)
        else:
            self.wrapped.write(text)
            self.wrapped.flush()
        if self.autoreset:
            self.reset_all()


    def reset_all(self):
        if self.convert:
            self.call_win32('m', (0,))
        elif not self.strip and not self.stream.closed:
            self.wrapped.write(Style.RESET_ALL)


    def write_and_convert(self, text):
        '''
        Write the given text to our wrapped stream, stripping any ANSI
        sequences from the text, and optionally converting them into win32
        calls.
        '''
        cursor = 0
        text = self.convert_osc(text)
        for match in self.ANSI_CSI_RE.finditer(text):
            start, end = match.span()
            self.write_plain_text(text, cursor, start)
            self.convert_ansi(*match.groups())
            cursor = end
        self.write_plain_text(text, cursor, len(text))


    def write_plain_text(self, text, start, end):
        if start < end:
            self.wrapped.write(text[start:end])
            self.wrapped.flush()


    def convert_ansi(self, paramstring, command):
        if self.convert:
            params = self.extract_params(command, paramstring)
            self.call_win32(command, params)


    def extract_params(self, command, paramstring):
        if command in 'Hf':
            params = tuple(int(p) if len(p) != 0 else 1 for p in paramstring.split(';'))
            while len(params) < 2:
                # defaults:
                params = params + (1,)
        else:
            params = tuple(int(p) for p in paramstring.split(';') if len(p) != 0)
            if len(params) == 0:
                # defaults:
                if command in 'JKm':
                    params = (0,)
                elif command in 'ABCD':
                    params = (1,)

        return params


    def call_win32(self, command, params):
        if command == 'm':
            for param in params:
                if param in self.win32_calls:
                    func_args = self.win32_calls[param]
                    func = func_args[0]
                    args = func_args[1:]
                    kwargs = dict(on_stderr=self.on_stderr)
                    func(*args, **kwargs)
        elif command in 'J':
            winterm.erase_screen(params[0], on_stderr=self.on_stderr)
        elif command in 'K':
            winterm.erase_line(params[0], on_stderr=self.on_stderr)
        elif command in 'Hf':     # cursor position - absolute
            winterm.set_cursor_position(params, on_stderr=self.on_stderr)
        elif command in 'ABCD':   # cursor position - relative
            n = params[0]
            # A - up, B - down, C - forward, D - back
            x, y = {'A': (0, -n), 'B': (0, n), 'C': (n, 0), 'D': (-n, 0)}[command]
            winterm.cursor_adjust(x, y, on_stderr=self.on_stderr)


    def convert_osc(self, text):
        for match in self.ANSI_OSC_RE.finditer(text):
            start, end = match.span()
            text = text[:start] + text[end:]
            paramstring, command = match.groups()
            if command == BEL:
                if paramstring.count(";") == 1:
                    params = paramstring.split(";")
                    # 0 - change title and icon (we will only change title)
                    # 1 - change icon (we don't support this)
                    # 2 - change title
                    if params[0] in '02':
                        winterm.set_title(params[1])
        return text


    def flush(self):
        self.wrapped.flush()

# === NexusCore/openenv\Lib\site-packages\anthropic\types\beta\message_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable
from typing_extensions import Literal, Required, TypedDict

from ..model_param import ModelParam
from .beta_message_param import BetaMessageParam
from .beta_metadata_param import BetaMetadataParam
from .beta_text_block_param import BetaTextBlockParam
from .beta_tool_union_param import BetaToolUnionParam
from .beta_tool_choice_param import BetaToolChoiceParam

__all__ = ["MessageCreateParamsBase", "MessageCreateParamsNonStreaming", "MessageCreateParamsStreaming"]


class MessageCreateParamsBase(TypedDict, total=False):
    max_tokens: Required[int]
    """The maximum number of tokens to generate before stopping.

    Note that our models may stop _before_ reaching this maximum. This parameter
    only specifies the absolute maximum number of tokens to generate.

    Different models have different maximum values for this parameter. See
    [models](https://docs.anthropic.com/en/docs/models-overview) for details.
    """

    messages: Required[Iterable[BetaMessageParam]]
    """Input messages.

    Our models are trained to operate on alternating `user` and `assistant`
    conversational turns. When creating a new `Message`, you specify the prior
    conversational turns with the `messages` parameter, and the model then generates
    the next `Message` in the conversation. Consecutive `user` or `assistant` turns
    in your request will be combined into a single turn.

    Each input message must be an object with a `role` and `content`. You can
    specify a single `user`-role message, or you can include multiple `user` and
    `assistant` messages.

    If the final message uses the `assistant` role, the response content will
    continue immediately from the content in that message. This can be used to
    constrain part of the model's response.

    Example with a single `user` message:

    ```json
    [{ "role": "user", "content": "Hello, Claude" }]
    ```

    Example with multiple conversational turns:

    ```json
    [
      { "role": "user", "content": "Hello there." },
      { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
      { "role": "user", "content": "Can you explain LLMs in plain English?" }
    ]
    ```

    Example with a partially-filled response from Claude:

    ```json
    [
      {
        "role": "user",
        "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
      },
      { "role": "assistant", "content": "The best answer is (" }
    ]
    ```

    Each input message `content` may be either a single `string` or an array of
    content blocks, where each block has a specific `type`. Using a `string` for
    `content` is shorthand for an array of one content block of type `"text"`. The
    following input messages are equivalent:

    ```json
    { "role": "user", "content": "Hello, Claude" }
    ```

    ```json
    { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
    ```

    Starting with Claude 3 models, you can also send image content blocks:

    ```json
    {
      "role": "user",
      "content": [
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": "/9j/4AAQSkZJRg..."
          }
        },
        { "type": "text", "text": "What is in this image?" }
      ]
    }
    ```

    We currently support the `base64` source type for images, and the `image/jpeg`,
    `image/png`, `image/gif`, and `image/webp` media types.

    See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
    more input examples.

    Note that if you want to include a
    [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
    the top-level `system` parameter — there is no `"system"` role for input
    messages in the Messages API.
    """

    model: Required[ModelParam]
    """
    The model that will complete your prompt.\n\nSee
    [models](https://docs.anthropic.com/en/docs/models-overview) for additional
    details and options.
    """

    metadata: BetaMetadataParam
    """An object describing metadata about the request."""

    stop_sequences: List[str]
    """Custom text sequences that will cause the model to stop generating.

    Our models will normally stop when they have naturally completed their turn,
    which will result in a response `stop_reason` of `"end_turn"`.

    If you want the model to stop generating when it encounters custom strings of
    text, you can use the `stop_sequences` parameter. If the model encounters one of
    the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
    and the response `stop_sequence` value will contain the matched stop sequence.
    """

    system: Union[str, Iterable[BetaTextBlockParam]]
    """System prompt.

    A system prompt is a way of providing context and instructions to Claude, such
    as specifying a particular goal or role. See our
    [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).
    """

    temperature: float
    """Amount of randomness injected into the response.

    Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
    for analytical / multiple choice, and closer to `1.0` for creative and
    generative tasks.

    Note that even with `temperature` of `0.0`, the results will not be fully
    deterministic.
    """

    tool_choice: BetaToolChoiceParam
    """How the model should use the provided tools.

    The model can use a specific tool, any available tool, or decide by itself.
    """

    tools: Iterable[BetaToolUnionParam]
    """Definitions of tools that the model may use.

    If you include `tools` in your API request, the model may return `tool_use`
    content blocks that represent the model's use of those tools. You can then run
    those tools using the tool input generated by the model and then optionally
    return results back to the model using `tool_result` content blocks.

    Each tool definition includes:

    - `name`: Name of the tool.
    - `description`: Optional, but strongly-recommended description of the tool.
    - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
      shape that the model will produce in `tool_use` output content blocks.

    For example, if you defined `tools` as:

    ```json
    [
      {
        "name": "get_stock_price",
        "description": "Get the current stock price for a given ticker symbol.",
        "input_schema": {
          "type": "object",
          "properties": {
            "ticker": {
              "type": "string",
              "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
            }
          },
          "required": ["ticker"]
        }
      }
    ]
    ```

    And then asked the model "What's the S&P 500 at today?", the model might produce
    `tool_use` content blocks in the response like this:

    ```json
    [
      {
        "type": "tool_use",
        "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
        "name": "get_stock_price",
        "input": { "ticker": "^GSPC" }
      }
    ]
    ```

    You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
    input, and return the following back to the model in a subsequent `user`
    message:

    ```json
    [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
        "content": "259.75 USD"
      }
    ]
    ```

    Tools can be used for workflows that include running client-side tools and
    functions, or more generally whenever you want the model to produce a particular
    JSON structure of output.

    See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.
    """

    top_k: int
    """Only sample from the top K options for each subsequent token.

    Used to remove "long tail" low probability responses.
    [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

    Recommended for advanced use cases only. You usually only need to use
    `temperature`.
    """

    top_p: float
    """Use nucleus sampling.

    In nucleus sampling, we compute the cumulative distribution over all the options
    for each subsequent token in decreasing probability order and cut it off once it
    reaches a particular probability specified by `top_p`. You should either alter
    `temperature` or `top_p`, but not both.

    Recommended for advanced use cases only. You usually only need to use
    `temperature`.
    """


class MessageCreateParamsNonStreaming(MessageCreateParamsBase, total=False):
    stream: Literal[False]
    """Whether to incrementally stream the response using server-sent events.

    See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
    details.
    """


class MessageCreateParamsStreaming(MessageCreateParamsBase):
    stream: Required[Literal[True]]
    """Whether to incrementally stream the response using server-sent events.

    See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
    details.
    """


MessageCreateParams = Union[MessageCreateParamsNonStreaming, MessageCreateParamsStreaming]

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\logging_callback_manager.py ===
from typing import Callable, List, Set, Type, Union

import litellm
from litellm._logging import verbose_logger
from litellm.integrations.additional_logging_utils import AdditionalLoggingUtils
from litellm.integrations.custom_logger import CustomLogger


class LoggingCallbackManager:
    """
    A centralized class that allows easy add / remove callbacks for litellm.

    Goals of this class:
    - Prevent adding duplicate callbacks / success_callback / failure_callback
    - Keep a reasonable MAX_CALLBACKS limit (this ensures callbacks don't exponentially grow and consume CPU Resources)
    """

    # healthy maximum number of callbacks - unlikely someone needs more than 20
    MAX_CALLBACKS = 30

    def add_litellm_input_callback(self, callback: Union[CustomLogger, str]):
        """
        Add a input callback to litellm.input_callback
        """
        self._safe_add_callback_to_list(
            callback=callback, parent_list=litellm.input_callback
        )

    def add_litellm_service_callback(
        self, callback: Union[CustomLogger, str, Callable]
    ):
        """
        Add a service callback to litellm.service_callback
        """
        self._safe_add_callback_to_list(
            callback=callback, parent_list=litellm.service_callback
        )

    def add_litellm_callback(self, callback: Union[CustomLogger, str, Callable]):
        """
        Add a callback to litellm.callbacks

        Ensures no duplicates are added.
        """
        self._safe_add_callback_to_list(
            callback=callback, parent_list=litellm.callbacks  # type: ignore
        )

    def add_litellm_success_callback(
        self, callback: Union[CustomLogger, str, Callable]
    ):
        """
        Add a success callback to `litellm.success_callback`
        """
        self._safe_add_callback_to_list(
            callback=callback, parent_list=litellm.success_callback
        )

    def add_litellm_failure_callback(
        self, callback: Union[CustomLogger, str, Callable]
    ):
        """
        Add a failure callback to `litellm.failure_callback`
        """
        self._safe_add_callback_to_list(
            callback=callback, parent_list=litellm.failure_callback
        )

    def add_litellm_async_success_callback(
        self, callback: Union[CustomLogger, Callable, str]
    ):
        """
        Add a success callback to litellm._async_success_callback
        """
        self._safe_add_callback_to_list(
            callback=callback, parent_list=litellm._async_success_callback
        )

    def add_litellm_async_failure_callback(
        self, callback: Union[CustomLogger, Callable, str]
    ):
        """
        Add a failure callback to litellm._async_failure_callback
        """
        self._safe_add_callback_to_list(
            callback=callback, parent_list=litellm._async_failure_callback
        )

    def remove_callback_from_list_by_object(self, callback_list, obj):
        """
        Remove callbacks that are methods of a particular object (e.g., router cleanup)
        """
        if not isinstance(callback_list, list):  # Not list -> do nothing
            return

        remove_list = [
            c for c in callback_list if hasattr(c, "__self__") and c.__self__ == obj
        ]

        for c in remove_list:
            callback_list.remove(c)

    def _add_string_callback_to_list(
        self, callback: str, parent_list: List[Union[CustomLogger, Callable, str]]
    ):
        """
        Add a string callback to a list, if the callback is already in the list, do not add it again.
        """
        if callback not in parent_list:
            parent_list.append(callback)
        else:
            verbose_logger.debug(
                f"Callback {callback} already exists in {parent_list}, not adding again.."
            )

    def _check_callback_list_size(
        self, parent_list: List[Union[CustomLogger, Callable, str]]
    ) -> bool:
        """
        Check if adding another callback would exceed MAX_CALLBACKS
        Returns True if safe to add, False if would exceed limit
        """
        if len(parent_list) >= self.MAX_CALLBACKS:
            verbose_logger.warning(
                f"Cannot add callback - would exceed MAX_CALLBACKS limit of {self.MAX_CALLBACKS}. Current callbacks: {len(parent_list)}"
            )
            return False
        return True

    def _safe_add_callback_to_list(
        self,
        callback: Union[CustomLogger, Callable, str],
        parent_list: List[Union[CustomLogger, Callable, str]],
    ):
        """
        Safe add a callback to a list, if the callback is already in the list, do not add it again.

        Ensures no duplicates are added for `str`, `Callable`, and `CustomLogger` callbacks.
        """
        # Check max callbacks limit first
        if not self._check_callback_list_size(parent_list):
            return

        if isinstance(callback, str):
            self._add_string_callback_to_list(
                callback=callback, parent_list=parent_list
            )
        elif isinstance(callback, CustomLogger):
            self._add_custom_logger_to_list(
                custom_logger=callback,
                parent_list=parent_list,
            )
        elif callable(callback):
            self._add_callback_function_to_list(
                callback=callback, parent_list=parent_list
            )

    def _add_callback_function_to_list(
        self, callback: Callable, parent_list: List[Union[CustomLogger, Callable, str]]
    ):
        """
        Add a callback function to a list, if the callback is already in the list, do not add it again.
        """
        # Check if the function already exists in the list by comparing function objects
        if callback not in parent_list:
            parent_list.append(callback)
        else:
            verbose_logger.debug(
                f"Callback function {callback.__name__} already exists in {parent_list}, not adding again.."
            )

    def _add_custom_logger_to_list(
        self,
        custom_logger: CustomLogger,
        parent_list: List[Union[CustomLogger, Callable, str]],
    ):
        """
        Add a custom logger to a list, if another instance of the same custom logger exists in the list, do not add it again.
        """
        # Check if an instance of the same class already exists in the list
        custom_logger_key = self._get_custom_logger_key(custom_logger)
        custom_logger_type_name = type(custom_logger).__name__
        for existing_logger in parent_list:
            if (
                isinstance(existing_logger, CustomLogger)
                and self._get_custom_logger_key(existing_logger) == custom_logger_key
            ):
                verbose_logger.debug(
                    f"Custom logger of type {custom_logger_type_name}, key: {custom_logger_key} already exists in {parent_list}, not adding again.."
                )
                return
        parent_list.append(custom_logger)

    def _get_custom_logger_key(self, custom_logger: CustomLogger):
        """
        Get a unique key for a custom logger that considers only fundamental instance variables

        Returns:
            str: A unique key combining the class name and fundamental instance variables (str, bool, int)
        """
        key_parts = [type(custom_logger).__name__]

        # Add only fundamental type instance variables to the key
        for attr_name, attr_value in vars(custom_logger).items():
            if not attr_name.startswith("_"):  # Skip private attributes
                if isinstance(attr_value, (str, bool, int)):
                    key_parts.append(f"{attr_name}={attr_value}")

        return "-".join(key_parts)

    def _reset_all_callbacks(self):
        """
        Reset all callbacks to an empty list

        Note: this is an internal function and should be used sparingly.
        """
        litellm.input_callback = []
        litellm.success_callback = []
        litellm.failure_callback = []
        litellm._async_success_callback = []
        litellm._async_failure_callback = []
        litellm.callbacks = []

    def _get_all_callbacks(self) -> List[Union[CustomLogger, Callable, str]]:
        """
        Get all callbacks from litellm.callbacks, litellm.success_callback, litellm.failure_callback, litellm._async_success_callback, litellm._async_failure_callback
        """
        return (
            litellm.callbacks
            + litellm.success_callback
            + litellm.failure_callback
            + litellm._async_success_callback
            + litellm._async_failure_callback
        )

    def get_active_additional_logging_utils_from_custom_logger(
        self,
    ) -> Set[AdditionalLoggingUtils]:
        """
        Get all custom loggers that are instances of the given class type

        Args:
            class_type: The class type to match against (e.g., AdditionalLoggingUtils)

        Returns:
            Set[CustomLogger]: Set of custom loggers that are instances of the given class type
        """
        all_callbacks = self._get_all_callbacks()
        matched_callbacks: Set[AdditionalLoggingUtils] = set()
        for callback in all_callbacks:
            if isinstance(callback, CustomLogger) and isinstance(
                callback, AdditionalLoggingUtils
            ):
                matched_callbacks.add(callback)
        return matched_callbacks

    def get_custom_loggers_for_type(
        self, callback_type: Type[CustomLogger]
    ) -> List[CustomLogger]:
        """
        Get all custom loggers that are instances of the given class type
        """
        # ensure we don't have duplicate instances
        all_callbacks = []
        for callback in self._get_all_callbacks():
            if isinstance(callback, callback_type) and callback not in all_callbacks:
                all_callbacks.append(callback)
        return all_callbacks

    def callback_is_active(self, callback_type: Type[CustomLogger]) -> bool:
        """
        Returns True if any of the active callbacks are of the given type
        """
        return any(
            isinstance(callback, callback_type)
            for callback in self._get_all_callbacks()
        )

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\mfc\dialog.py ===
""" \
Base class for Dialogs.  Also contains a few useful utility functions
"""

# dialog.py
# Python class for Dialog Boxes in PythonWin.

import win32con
import win32ui

from . import window


def dllFromDll(dllid):
    "given a 'dll' (maybe a dll, filename, etc), return a DLL object"
    if dllid is None:
        return None
    elif isinstance(dllid, str):
        return win32ui.LoadLibrary(dllid)
    else:
        try:
            dllid.GetFileName()
        except AttributeError:
            raise TypeError("DLL parameter must be None, a filename or a dll object")
        return dllid


class Dialog(window.Wnd):
    "Base class for a dialog"

    def __init__(self, id, dllid=None):
        """id is the resource ID, or a template
        dllid may be None, a dll object, or a string with a dll name"""
        # must take a reference to the DLL until InitDialog.
        self.dll = dllFromDll(dllid)
        if isinstance(id, list):  # a template
            dlg = win32ui.CreateDialogIndirect(id)
        else:
            dlg = win32ui.CreateDialog(id, self.dll)
        window.Wnd.__init__(self, dlg)
        self.HookCommands()
        self.bHaveInit = None

    def HookCommands(self):
        pass

    def OnAttachedObjectDeath(self):
        self.data = self._obj_.data
        window.Wnd.OnAttachedObjectDeath(self)

    # provide virtuals.
    def OnOK(self):
        self._obj_.OnOK()

    def OnCancel(self):
        self._obj_.OnCancel()

    def OnInitDialog(self):
        self.bHaveInit = 1
        if self._obj_.data:
            self._obj_.UpdateData(0)
        return 1  # I did NOT set focus to a child window.

    def OnDestroy(self, msg):
        self.dll = None  # theoretically not needed if object destructs normally.

    # DDX support
    def AddDDX(self, *args):
        self._obj_.datalist.append(args)

    # Make a dialog object look like a dictionary for the DDX support
    def __bool__(self):
        return True

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, item):
        self._obj_.data[key] = item  # self.UpdateData(0)

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def values(self):
        return self.data.values()

    def __contains__(self, key):
        return key in self.data

    has_key = __contains__


class PrintDialog(Dialog):
    "Base class for a print dialog"

    def __init__(
        self,
        pInfo,
        dlgID,
        printSetupOnly=0,
        flags=(
            win32ui.PD_ALLPAGES
            | win32ui.PD_USEDEVMODECOPIES
            | win32ui.PD_NOPAGENUMS
            | win32ui.PD_HIDEPRINTTOFILE
            | win32ui.PD_NOSELECTION
        ),
        parent=None,
        dllid=None,
    ):
        self.dll = dllFromDll(dllid)
        if isinstance(dlgID, list):  # a template
            raise TypeError("dlgID parameter must be an integer resource ID")
        dlg = win32ui.CreatePrintDialog(dlgID, printSetupOnly, flags, parent, self.dll)
        window.Wnd.__init__(self, dlg)
        self.HookCommands()
        self.bHaveInit = None
        self.pInfo = pInfo
        # init values (if PrintSetup is called, values still available)
        flags = pInfo.GetFlags()
        self["toFile"] = flags & win32ui.PD_PRINTTOFILE != 0
        self["direct"] = pInfo.GetDirect()
        self["preview"] = pInfo.GetPreview()
        self["continuePrinting"] = pInfo.GetContinuePrinting()
        self["curPage"] = pInfo.GetCurPage()
        self["numPreviewPages"] = pInfo.GetNumPreviewPages()
        self["userData"] = pInfo.GetUserData()
        self["draw"] = pInfo.GetDraw()
        self["pageDesc"] = pInfo.GetPageDesc()
        self["minPage"] = pInfo.GetMinPage()
        self["maxPage"] = pInfo.GetMaxPage()
        self["offsetPage"] = pInfo.GetOffsetPage()
        self["fromPage"] = pInfo.GetFromPage()
        self["toPage"] = pInfo.GetToPage()
        # these values updated after OnOK
        self["copies"] = 0
        self["deviceName"] = ""
        self["driverName"] = ""
        self["printAll"] = 0
        self["printCollate"] = 0
        self["printRange"] = 0
        self["printSelection"] = 0

    def OnInitDialog(self):
        self.pInfo.CreatePrinterDC()  # This also sets the hDC of the pInfo structure.
        return self._obj_.OnInitDialog()

    def OnCancel(self):
        del self.pInfo

    def OnOK(self):
        """DoModal has finished. Can now access the users choices"""
        self._obj_.OnOK()
        pInfo = self.pInfo
        # user values
        flags = pInfo.GetFlags()
        self["toFile"] = flags & win32ui.PD_PRINTTOFILE != 0
        self["direct"] = pInfo.GetDirect()
        self["preview"] = pInfo.GetPreview()
        self["continuePrinting"] = pInfo.GetContinuePrinting()
        self["curPage"] = pInfo.GetCurPage()
        self["numPreviewPages"] = pInfo.GetNumPreviewPages()
        self["userData"] = pInfo.GetUserData()
        self["draw"] = pInfo.GetDraw()
        self["pageDesc"] = pInfo.GetPageDesc()
        self["minPage"] = pInfo.GetMinPage()
        self["maxPage"] = pInfo.GetMaxPage()
        self["offsetPage"] = pInfo.GetOffsetPage()
        self["fromPage"] = pInfo.GetFromPage()
        self["toPage"] = pInfo.GetToPage()
        self["copies"] = pInfo.GetCopies()
        self["deviceName"] = pInfo.GetDeviceName()
        self["driverName"] = pInfo.GetDriverName()
        self["printAll"] = pInfo.PrintAll()
        self["printCollate"] = pInfo.PrintCollate()
        self["printRange"] = pInfo.PrintRange()
        self["printSelection"] = pInfo.PrintSelection()
        del self.pInfo


class PropertyPage(Dialog):
    "Base class for a Property Page"

    def __init__(self, id, dllid=None, caption=0):
        """id is the resource ID
        dllid may be None, a dll object, or a string with a dll name"""

        self.dll = dllFromDll(dllid)
        if self.dll:
            oldRes = win32ui.SetResource(self.dll)
        if isinstance(id, list):
            dlg = win32ui.CreatePropertyPageIndirect(id)
        else:
            dlg = win32ui.CreatePropertyPage(id, caption)
        if self.dll:
            win32ui.SetResource(oldRes)
        # don't call dialog init!
        window.Wnd.__init__(self, dlg)
        self.HookCommands()


class PropertySheet(window.Wnd):
    def __init__(self, caption, dll=None, pageList=None):  # parent=None, style,etc):
        "Initialize a property sheet.  pageList is a list of ID's"
        # must take a reference to the DLL until InitDialog.
        self.dll = dllFromDll(dll)
        self.sheet = win32ui.CreatePropertySheet(caption)
        window.Wnd.__init__(self, self.sheet)
        if not pageList is None:
            self.AddPage(pageList)

    def OnInitDialog(self):
        return self._obj_.OnInitDialog()

    def DoModal(self):
        if self.dll:
            oldRes = win32ui.SetResource(self.dll)
        rc = self.sheet.DoModal()
        if self.dll:
            win32ui.SetResource(oldRes)
        return rc

    def AddPage(self, pages):
        if self.dll:
            oldRes = win32ui.SetResource(self.dll)
        try:  # try list style access
            pages[0]
            isSeq = 1
        except (TypeError, KeyError):
            isSeq = 0
        if isSeq:
            for page in pages:
                self.DoAddSinglePage(page)
        else:
            self.DoAddSinglePage(pages)
        if self.dll:
            win32ui.SetResource(oldRes)

    def DoAddSinglePage(self, page):
        "Page may be page, or int ID. Assumes DLL setup"
        if isinstance(page, int):
            self.sheet.AddPage(win32ui.CreatePropertyPage(page))
        else:
            self.sheet.AddPage(page)


# define some app utility functions.
def GetSimpleInput(prompt, defValue="", title=None):
    """displays a dialog, and returns a string, or None if cancelled.
    args prompt, defValue='', title=main frames title"""
    # uses a simple dialog to return a string object.
    if title is None:
        title = win32ui.GetMainFrame().GetWindowText()

    class DlgSimpleInput(Dialog):
        def __init__(self, prompt, defValue, title):
            self.title = title
            Dialog.__init__(self, win32ui.IDD_SIMPLE_INPUT)
            self.AddDDX(win32ui.IDC_EDIT1, "result")
            self.AddDDX(win32ui.IDC_PROMPT1, "prompt")
            self._obj_.data["result"] = defValue
            self._obj_.data["prompt"] = prompt

        def OnInitDialog(self):
            self.SetWindowText(self.title)
            return Dialog.OnInitDialog(self)

    dlg = DlgSimpleInput(prompt, defValue, title)
    if dlg.DoModal() != win32con.IDOK:
        return None
    return dlg["result"]

# === NexusCore/openenv\Lib\site-packages\urllib3\contrib\emscripten\response.py ===
from __future__ import annotations

import json as _json
import logging
import typing
from contextlib import contextmanager
from dataclasses import dataclass
from http.client import HTTPException as HTTPException
from io import BytesIO, IOBase

from ...exceptions import InvalidHeader, TimeoutError
from ...response import BaseHTTPResponse
from ...util.retry import Retry
from .request import EmscriptenRequest

if typing.TYPE_CHECKING:
    from ..._base_connection import BaseHTTPConnection, BaseHTTPSConnection

log = logging.getLogger(__name__)


@dataclass
class EmscriptenResponse:
    status_code: int
    headers: dict[str, str]
    body: IOBase | bytes
    request: EmscriptenRequest


class EmscriptenHttpResponseWrapper(BaseHTTPResponse):
    def __init__(
        self,
        internal_response: EmscriptenResponse,
        url: str | None = None,
        connection: BaseHTTPConnection | BaseHTTPSConnection | None = None,
    ):
        self._pool = None  # set by pool class
        self._body = None
        self._response = internal_response
        self._url = url
        self._connection = connection
        self._closed = False
        super().__init__(
            headers=internal_response.headers,
            status=internal_response.status_code,
            request_url=url,
            version=0,
            version_string="HTTP/?",
            reason="",
            decode_content=True,
        )
        self.length_remaining = self._init_length(self._response.request.method)
        self.length_is_certain = False

    @property
    def url(self) -> str | None:
        return self._url

    @url.setter
    def url(self, url: str | None) -> None:
        self._url = url

    @property
    def connection(self) -> BaseHTTPConnection | BaseHTTPSConnection | None:
        return self._connection

    @property
    def retries(self) -> Retry | None:
        return self._retries

    @retries.setter
    def retries(self, retries: Retry | None) -> None:
        # Override the request_url if retries has a redirect location.
        self._retries = retries

    def stream(
        self, amt: int | None = 2**16, decode_content: bool | None = None
    ) -> typing.Generator[bytes]:
        """
        A generator wrapper for the read() method. A call will block until
        ``amt`` bytes have been read from the connection or until the
        connection is closed.

        :param amt:
            How much of the content to read. The generator will return up to
            much data per iteration, but may return less. This is particularly
            likely when using compressed data. However, the empty string will
            never be returned.

        :param decode_content:
            If True, will attempt to decode the body based on the
            'content-encoding' header.
        """
        while True:
            data = self.read(amt=amt, decode_content=decode_content)

            if data:
                yield data
            else:
                break

    def _init_length(self, request_method: str | None) -> int | None:
        length: int | None
        content_length: str | None = self.headers.get("content-length")

        if content_length is not None:
            try:
                # RFC 7230 section 3.3.2 specifies multiple content lengths can
                # be sent in a single Content-Length header
                # (e.g. Content-Length: 42, 42). This line ensures the values
                # are all valid ints and that as long as the `set` length is 1,
                # all values are the same. Otherwise, the header is invalid.
                lengths = {int(val) for val in content_length.split(",")}
                if len(lengths) > 1:
                    raise InvalidHeader(
                        "Content-Length contained multiple "
                        "unmatching values (%s)" % content_length
                    )
                length = lengths.pop()
            except ValueError:
                length = None
            else:
                if length < 0:
                    length = None

        else:  # if content_length is None
            length = None

        # Check for responses that shouldn't include a body
        if (
            self.status in (204, 304)
            or 100 <= self.status < 200
            or request_method == "HEAD"
        ):
            length = 0

        return length

    def read(
        self,
        amt: int | None = None,
        decode_content: bool | None = None,  # ignored because browser decodes always
        cache_content: bool = False,
    ) -> bytes:
        if (
            self._closed
            or self._response is None
            or (isinstance(self._response.body, IOBase) and self._response.body.closed)
        ):
            return b""

        with self._error_catcher():
            # body has been preloaded as a string by XmlHttpRequest
            if not isinstance(self._response.body, IOBase):
                self.length_remaining = len(self._response.body)
                self.length_is_certain = True
                # wrap body in IOStream
                self._response.body = BytesIO(self._response.body)
            if amt is not None and amt >= 0:
                # don't cache partial content
                cache_content = False
                data = self._response.body.read(amt)
            else:  # read all we can (and cache it)
                data = self._response.body.read()
                if cache_content:
                    self._body = data
            if self.length_remaining is not None:
                self.length_remaining = max(self.length_remaining - len(data), 0)
            if len(data) == 0 or (
                self.length_is_certain and self.length_remaining == 0
            ):
                # definitely finished reading, close response stream
                self._response.body.close()
            return typing.cast(bytes, data)

    def read_chunked(
        self,
        amt: int | None = None,
        decode_content: bool | None = None,
    ) -> typing.Generator[bytes]:
        # chunked is handled by browser
        while True:
            bytes = self.read(amt, decode_content)
            if not bytes:
                break
            yield bytes

    def release_conn(self) -> None:
        if not self._pool or not self._connection:
            return None

        self._pool._put_conn(self._connection)
        self._connection = None

    def drain_conn(self) -> None:
        self.close()

    @property
    def data(self) -> bytes:
        if self._body:
            return self._body
        else:
            return self.read(cache_content=True)

    def json(self) -> typing.Any:
        """
        Deserializes the body of the HTTP response as a Python object.

        The body of the HTTP response must be encoded using UTF-8, as per
        `RFC 8529 Section 8.1 <https://www.rfc-editor.org/rfc/rfc8259#section-8.1>`_.

        To use a custom JSON decoder pass the result of :attr:`HTTPResponse.data` to
        your custom decoder instead.

        If the body of the HTTP response is not decodable to UTF-8, a
        `UnicodeDecodeError` will be raised. If the body of the HTTP response is not a
        valid JSON document, a `json.JSONDecodeError` will be raised.

        Read more :ref:`here <json_content>`.

        :returns: The body of the HTTP response as a Python object.
        """
        data = self.data.decode("utf-8")
        return _json.loads(data)

    def close(self) -> None:
        if not self._closed:
            if isinstance(self._response.body, IOBase):
                self._response.body.close()
            if self._connection:
                self._connection.close()
                self._connection = None
            self._closed = True

    @contextmanager
    def _error_catcher(self) -> typing.Generator[None]:
        """
        Catch Emscripten specific exceptions thrown by fetch.py,
        instead re-raising urllib3 variants, so that low-level exceptions
        are not leaked in the high-level api.

        On exit, release the connection back to the pool.
        """
        from .fetch import _RequestError, _TimeoutError  # avoid circular import

        clean_exit = False

        try:
            yield
            # If no exception is thrown, we should avoid cleaning up
            # unnecessarily.
            clean_exit = True
        except _TimeoutError as e:
            raise TimeoutError(str(e))
        except _RequestError as e:
            raise HTTPException(str(e))
        finally:
            # If we didn't terminate cleanly, we need to throw away our
            # connection.
            if not clean_exit:
                # The response may not be closed but we're not going to use it
                # anymore so close it now
                if (
                    isinstance(self._response.body, IOBase)
                    and not self._response.body.closed
                ):
                    self._response.body.close()
                # release the connection back to the pool
                self.release_conn()
            else:
                # If we have read everything from the response stream,
                # return the connection back to the pool.
                if (
                    isinstance(self._response.body, IOBase)
                    and self._response.body.closed
                ):
                    self.release_conn()

# === NexusCore/openenv\Lib\site-packages\win32com\client\tlbrowse.py ===
import commctrl
import pythoncom
import win32api
import win32con
import win32ui
from pywin.mfc import dialog


class TLBrowserException(Exception):
    "TypeLib browser internal error"


error = TLBrowserException  # Re-exported alias

FRAMEDLG_STD = win32con.WS_CAPTION | win32con.WS_SYSMENU
SS_STD = win32con.WS_CHILD | win32con.WS_VISIBLE
BS_STD = SS_STD | win32con.WS_TABSTOP
ES_STD = BS_STD | win32con.WS_BORDER
LBS_STD = (
    ES_STD | win32con.LBS_NOTIFY | win32con.LBS_NOINTEGRALHEIGHT | win32con.WS_VSCROLL
)
CBS_STD = ES_STD | win32con.CBS_NOINTEGRALHEIGHT | win32con.WS_VSCROLL

typekindmap = {
    pythoncom.TKIND_ENUM: "Enumeration",
    pythoncom.TKIND_RECORD: "Record",
    pythoncom.TKIND_MODULE: "Module",
    pythoncom.TKIND_INTERFACE: "Interface",
    pythoncom.TKIND_DISPATCH: "Dispatch",
    pythoncom.TKIND_COCLASS: "CoClass",
    pythoncom.TKIND_ALIAS: "Alias",
    pythoncom.TKIND_UNION: "Union",
}

TypeBrowseDialog_Parent = dialog.Dialog


class TypeBrowseDialog(TypeBrowseDialog_Parent):
    "Browse a type library"

    IDC_TYPELIST = 1000
    IDC_MEMBERLIST = 1001
    IDC_PARAMLIST = 1002
    IDC_LISTVIEW = 1003

    def __init__(self, typefile=None):
        TypeBrowseDialog_Parent.__init__(self, self.GetTemplate())
        try:
            if typefile:
                self.tlb = pythoncom.LoadTypeLib(typefile)
            else:
                self.tlb = None
        except pythoncom.ole_error:
            self.MessageBox("The file does not contain type information")
            self.tlb = None
        self.HookCommand(self.CmdTypeListbox, self.IDC_TYPELIST)
        self.HookCommand(self.CmdMemberListbox, self.IDC_MEMBERLIST)

    def OnAttachedObjectDeath(self):
        self.tlb = None
        self.typeinfo = None
        self.attr = None
        return TypeBrowseDialog_Parent.OnAttachedObjectDeath(self)

    def _SetupMenu(self):
        menu = win32ui.CreateMenu()
        flags = win32con.MF_STRING | win32con.MF_ENABLED
        menu.AppendMenu(flags, win32ui.ID_FILE_OPEN, "&Open...")
        menu.AppendMenu(flags, win32con.IDCANCEL, "&Close")
        mainMenu = win32ui.CreateMenu()
        mainMenu.AppendMenu(flags | win32con.MF_POPUP, menu.GetHandle(), "&File")
        self.SetMenu(mainMenu)
        self.HookCommand(self.OnFileOpen, win32ui.ID_FILE_OPEN)

    def OnFileOpen(self, id, code):
        openFlags = win32con.OFN_OVERWRITEPROMPT | win32con.OFN_FILEMUSTEXIST
        fspec = "Type Libraries (*.tlb, *.olb)|*.tlb;*.olb|OCX Files (*.ocx)|*.ocx|DLL's (*.dll)|*.dll|All Files (*.*)|*.*||"
        dlg = win32ui.CreateFileDialog(1, None, None, openFlags, fspec)
        if dlg.DoModal() == win32con.IDOK:
            try:
                self.tlb = pythoncom.LoadTypeLib(dlg.GetPathName())
            except pythoncom.ole_error:
                self.MessageBox("The file does not contain type information")
                self.tlb = None
            self._SetupTLB()

    def OnInitDialog(self):
        self._SetupMenu()
        self.typelb = self.GetDlgItem(self.IDC_TYPELIST)
        self.memberlb = self.GetDlgItem(self.IDC_MEMBERLIST)
        self.paramlb = self.GetDlgItem(self.IDC_PARAMLIST)
        self.listview = self.GetDlgItem(self.IDC_LISTVIEW)

        # Setup the listview columns
        itemDetails = (commctrl.LVCFMT_LEFT, 100, "Item", 0)
        self.listview.InsertColumn(0, itemDetails)
        itemDetails = (commctrl.LVCFMT_LEFT, 1024, "Details", 0)
        self.listview.InsertColumn(1, itemDetails)

        if self.tlb is None:
            self.OnFileOpen(None, None)
        else:
            self._SetupTLB()
        return TypeBrowseDialog_Parent.OnInitDialog(self)

    def _SetupTLB(self):
        self.typelb.ResetContent()
        self.memberlb.ResetContent()
        self.paramlb.ResetContent()
        self.typeinfo = None
        self.attr = None
        if self.tlb is None:
            return
        n = self.tlb.GetTypeInfoCount()
        for i in range(n):
            self.typelb.AddString(self.tlb.GetDocumentation(i)[0])

    def _SetListviewTextItems(self, items):
        self.listview.DeleteAllItems()
        index = -1
        for item in items:
            index = self.listview.InsertItem(index + 1, item[0])
            data = item[1]
            if data is None:
                data = ""
            self.listview.SetItemText(index, 1, data)

    def SetupAllInfoTypes(self):
        infos = self._GetMainInfoTypes() + self._GetMethodInfoTypes()
        self._SetListviewTextItems(infos)

    def _GetMainInfoTypes(self):
        pos = self.typelb.GetCurSel()
        if pos < 0:
            return []
        docinfo = self.tlb.GetDocumentation(pos)
        infos = [("GUID", str(self.attr[0]))]
        infos.append(("Help File", docinfo[3]))
        infos.append(("Help Context", str(docinfo[2])))
        try:
            infos.append(("Type Kind", typekindmap[self.tlb.GetTypeInfoType(pos)]))
        except:
            pass

        info = self.tlb.GetTypeInfo(pos)
        attr = info.GetTypeAttr()
        infos.append(("Attributes", str(attr)))

        for j in range(attr[8]):
            flags = info.GetImplTypeFlags(j)
            refInfo = info.GetRefTypeInfo(info.GetRefTypeOfImplType(j))
            doc = refInfo.GetDocumentation(-1)
            attr = refInfo.GetTypeAttr()
            typeKind = attr[5]
            typeFlags = attr[11]

            desc = doc[0]
            desc += ", Flags=0x{:x}, typeKind=0x{:x}, typeFlags=0x{:x}".format(
                flags, typeKind, typeFlags
            )
            if flags & pythoncom.IMPLTYPEFLAG_FSOURCE:
                desc += "(Source)"
            infos.append(("Implements", desc))

        return infos

    def _GetMethodInfoTypes(self):
        pos = self.memberlb.GetCurSel()
        if pos < 0:
            return []

        realPos, isMethod = self._GetRealMemberPos(pos)
        ret = []
        if isMethod:
            funcDesc = self.typeinfo.GetFuncDesc(realPos)
            id = funcDesc[0]
            ret.append(("Func Desc", str(funcDesc)))
        else:
            id = self.typeinfo.GetVarDesc(realPos)[0]

        docinfo = self.typeinfo.GetDocumentation(id)
        ret.append(("Help String", docinfo[1]))
        ret.append(("Help Context", str(docinfo[2])))
        return ret

    def CmdTypeListbox(self, id, code):
        if code == win32con.LBN_SELCHANGE:
            pos = self.typelb.GetCurSel()
            if pos >= 0:
                self.memberlb.ResetContent()
                self.typeinfo = self.tlb.GetTypeInfo(pos)
                self.attr = self.typeinfo.GetTypeAttr()
                for i in range(self.attr[7]):
                    id = self.typeinfo.GetVarDesc(i)[0]
                    self.memberlb.AddString(self.typeinfo.GetNames(id)[0])
                for i in range(self.attr[6]):
                    id = self.typeinfo.GetFuncDesc(i)[0]
                    self.memberlb.AddString(self.typeinfo.GetNames(id)[0])
                self.SetupAllInfoTypes()
            return 1

    def _GetRealMemberPos(self, pos):
        pos = self.memberlb.GetCurSel()
        if pos >= self.attr[7]:
            return pos - self.attr[7], 1
        elif pos >= 0:
            return pos, 0
        else:
            raise error("The position is not valid")

    def CmdMemberListbox(self, id, code):
        if code == win32con.LBN_SELCHANGE:
            self.paramlb.ResetContent()
            pos = self.memberlb.GetCurSel()
            realPos, isMethod = self._GetRealMemberPos(pos)
            if isMethod:
                id = self.typeinfo.GetFuncDesc(realPos)[0]
                names = self.typeinfo.GetNames(id)
                for i in range(len(names)):
                    if i > 0:
                        self.paramlb.AddString(names[i])
            self.SetupAllInfoTypes()
            return 1

    def GetTemplate(self):
        "Return the template used to create this dialog"

        w = 272  # Dialog width
        h = 192  # Dialog height
        style = (
            FRAMEDLG_STD
            | win32con.WS_VISIBLE
            | win32con.DS_SETFONT
            | win32con.WS_MINIMIZEBOX
        )
        template = [
            ["Type Library Browser", (0, 0, w, h), style, None, (8, "Helv")],
        ]
        template.append([130, "&Type", -1, (10, 10, 62, 9), SS_STD | win32con.SS_LEFT])
        template.append([131, None, self.IDC_TYPELIST, (10, 20, 80, 80), LBS_STD])
        template.append(
            [130, "&Members", -1, (100, 10, 62, 9), SS_STD | win32con.SS_LEFT]
        )
        template.append([131, None, self.IDC_MEMBERLIST, (100, 20, 80, 80), LBS_STD])
        template.append(
            [130, "&Parameters", -1, (190, 10, 62, 9), SS_STD | win32con.SS_LEFT]
        )
        template.append([131, None, self.IDC_PARAMLIST, (190, 20, 75, 80), LBS_STD])

        lvStyle = (
            SS_STD
            | commctrl.LVS_REPORT
            | commctrl.LVS_AUTOARRANGE
            | commctrl.LVS_ALIGNLEFT
            | win32con.WS_BORDER
            | win32con.WS_TABSTOP
        )
        template.append(
            ["SysListView32", "", self.IDC_LISTVIEW, (10, 110, 255, 65), lvStyle]
        )

        return template


if __name__ == "__main__":
    import sys

    fname = None
    try:
        fname = sys.argv[1]
    except:
        pass
    dlg = TypeBrowseDialog(fname)
    if win32api.GetConsoleTitle():  # empty string w/o console
        dlg.DoModal()
    else:
        dlg.CreateWindow(win32ui.GetMainFrame())

# === NexusCore/openenv\Lib\site-packages\markdown_it\ruler.py ===
"""
class Ruler

Helper class, used by [[MarkdownIt#core]], [[MarkdownIt#block]] and
[[MarkdownIt#inline]] to manage sequences of functions (rules):

- keep rules in defined order
- assign the name to each rule
- enable/disable rules
- add/replace rules
- allow assign rules to additional named chains (in the same)
- caching lists of active rules

You will not need use this class directly until write plugins. For simple
rules control use [[MarkdownIt.disable]], [[MarkdownIt.enable]] and
[[MarkdownIt.use]].
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, TypedDict, TypeVar
import warnings

from markdown_it._compat import DATACLASS_KWARGS

from .utils import EnvType

if TYPE_CHECKING:
    from markdown_it import MarkdownIt


class StateBase:
    def __init__(self, src: str, md: MarkdownIt, env: EnvType):
        self.src = src
        self.env = env
        self.md = md

    @property
    def src(self) -> str:
        return self._src

    @src.setter
    def src(self, value: str) -> None:
        self._src = value
        self._srcCharCode: tuple[int, ...] | None = None

    @property
    def srcCharCode(self) -> tuple[int, ...]:
        warnings.warn(
            "StateBase.srcCharCode is deprecated. Use StateBase.src instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self._srcCharCode is None:
            self._srcCharCode = tuple(ord(c) for c in self._src)
        return self._srcCharCode


class RuleOptionsType(TypedDict, total=False):
    alt: list[str]


RuleFuncTv = TypeVar("RuleFuncTv")
"""A rule function, whose signature is dependent on the state type."""


@dataclass(**DATACLASS_KWARGS)
class Rule(Generic[RuleFuncTv]):
    name: str
    enabled: bool
    fn: RuleFuncTv = field(repr=False)
    alt: list[str]


class Ruler(Generic[RuleFuncTv]):
    def __init__(self) -> None:
        # List of added rules.
        self.__rules__: list[Rule[RuleFuncTv]] = []
        # Cached rule chains.
        # First level - chain name, '' for default.
        # Second level - diginal anchor for fast filtering by charcodes.
        self.__cache__: dict[str, list[RuleFuncTv]] | None = None

    def __find__(self, name: str) -> int:
        """Find rule index by name"""
        for i, rule in enumerate(self.__rules__):
            if rule.name == name:
                return i
        return -1

    def __compile__(self) -> None:
        """Build rules lookup cache"""
        chains = {""}
        # collect unique names
        for rule in self.__rules__:
            if not rule.enabled:
                continue
            for name in rule.alt:
                chains.add(name)
        self.__cache__ = {}
        for chain in chains:
            self.__cache__[chain] = []
            for rule in self.__rules__:
                if not rule.enabled:
                    continue
                if chain and (chain not in rule.alt):
                    continue
                self.__cache__[chain].append(rule.fn)

    def at(
        self, ruleName: str, fn: RuleFuncTv, options: RuleOptionsType | None = None
    ) -> None:
        """Replace rule by name with new function & options.

        :param ruleName: rule name to replace.
        :param fn: new rule function.
        :param options: new rule options (not mandatory).
        :raises: KeyError if name not found
        """
        index = self.__find__(ruleName)
        options = options or {}
        if index == -1:
            raise KeyError(f"Parser rule not found: {ruleName}")
        self.__rules__[index].fn = fn
        self.__rules__[index].alt = options.get("alt", [])
        self.__cache__ = None

    def before(
        self,
        beforeName: str,
        ruleName: str,
        fn: RuleFuncTv,
        options: RuleOptionsType | None = None,
    ) -> None:
        """Add new rule to chain before one with given name.

        :param beforeName: new rule will be added before this one.
        :param ruleName: new rule will be added before this one.
        :param fn: new rule function.
        :param options: new rule options (not mandatory).
        :raises: KeyError if name not found
        """
        index = self.__find__(beforeName)
        options = options or {}
        if index == -1:
            raise KeyError(f"Parser rule not found: {beforeName}")
        self.__rules__.insert(
            index, Rule[RuleFuncTv](ruleName, True, fn, options.get("alt", []))
        )
        self.__cache__ = None

    def after(
        self,
        afterName: str,
        ruleName: str,
        fn: RuleFuncTv,
        options: RuleOptionsType | None = None,
    ) -> None:
        """Add new rule to chain after one with given name.

        :param afterName: new rule will be added after this one.
        :param ruleName: new rule will be added after this one.
        :param fn: new rule function.
        :param options: new rule options (not mandatory).
        :raises: KeyError if name not found
        """
        index = self.__find__(afterName)
        options = options or {}
        if index == -1:
            raise KeyError(f"Parser rule not found: {afterName}")
        self.__rules__.insert(
            index + 1, Rule[RuleFuncTv](ruleName, True, fn, options.get("alt", []))
        )
        self.__cache__ = None

    def push(
        self, ruleName: str, fn: RuleFuncTv, options: RuleOptionsType | None = None
    ) -> None:
        """Push new rule to the end of chain.

        :param ruleName: new rule will be added to the end of chain.
        :param fn: new rule function.
        :param options: new rule options (not mandatory).

        """
        self.__rules__.append(
            Rule[RuleFuncTv](ruleName, True, fn, (options or {}).get("alt", []))
        )
        self.__cache__ = None

    def enable(
        self, names: str | Iterable[str], ignoreInvalid: bool = False
    ) -> list[str]:
        """Enable rules with given names.

        :param names: name or list of rule names to enable.
        :param ignoreInvalid: ignore errors when rule not found
        :raises: KeyError if name not found and not ignoreInvalid
        :return: list of found rule names
        """
        if isinstance(names, str):
            names = [names]
        result: list[str] = []
        for name in names:
            idx = self.__find__(name)
            if (idx < 0) and ignoreInvalid:
                continue
            if (idx < 0) and not ignoreInvalid:
                raise KeyError(f"Rules manager: invalid rule name {name}")
            self.__rules__[idx].enabled = True
            result.append(name)
        self.__cache__ = None
        return result

    def enableOnly(
        self, names: str | Iterable[str], ignoreInvalid: bool = False
    ) -> list[str]:
        """Enable rules with given names, and disable everything else.

        :param names: name or list of rule names to enable.
        :param ignoreInvalid: ignore errors when rule not found
        :raises: KeyError if name not found and not ignoreInvalid
        :return: list of found rule names
        """
        if isinstance(names, str):
            names = [names]
        for rule in self.__rules__:
            rule.enabled = False
        return self.enable(names, ignoreInvalid)

    def disable(
        self, names: str | Iterable[str], ignoreInvalid: bool = False
    ) -> list[str]:
        """Disable rules with given names.

        :param names: name or list of rule names to enable.
        :param ignoreInvalid: ignore errors when rule not found
        :raises: KeyError if name not found and not ignoreInvalid
        :return: list of found rule names
        """
        if isinstance(names, str):
            names = [names]
        result = []
        for name in names:
            idx = self.__find__(name)
            if (idx < 0) and ignoreInvalid:
                continue
            if (idx < 0) and not ignoreInvalid:
                raise KeyError(f"Rules manager: invalid rule name {name}")
            self.__rules__[idx].enabled = False
            result.append(name)
        self.__cache__ = None
        return result

    def getRules(self, chainName: str = "") -> list[RuleFuncTv]:
        """Return array of active functions (rules) for given chain name.
        It analyzes rules configuration, compiles caches if not exists and returns result.

        Default chain name is `''` (empty string). It can't be skipped.
        That's done intentionally, to keep signature monomorphic for high speed.

        """
        if self.__cache__ is None:
            self.__compile__()
            assert self.__cache__ is not None
        # Chain can be empty, if rules disabled. But we still have to return Array.
        return self.__cache__.get(chainName, []) or []

    def get_all_rules(self) -> list[str]:
        """Return all available rule names."""
        return [r.name for r in self.__rules__]

    def get_active_rules(self) -> list[str]:
        """Return the active rule names."""
        return [r.name for r in self.__rules__ if r.enabled]

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\anthropic_endpoints\endpoints.py ===
"""
Unified /v1/messages endpoint - (Anthropic Spec)
"""

import asyncio
import json
import time
import traceback

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.constants import STREAM_SSE_DATA_PREFIX
from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
from litellm.proxy._types import *
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.common_request_processing import (
    ProxyBaseLLMRequestProcessing,
    create_streaming_response,
)
from litellm.proxy.common_utils.http_parsing_utils import _read_request_body
from litellm.proxy.litellm_pre_call_utils import add_litellm_data_to_request
from litellm.proxy.utils import ProxyLogging

router = APIRouter()


def return_anthropic_chunk(chunk: Any) -> str:
    """
    Helper function to format streaming chunks for Anthropic API format

    Args:
        chunk: A string or dictionary to be returned in SSE format

    Returns:
        str: A properly formatted SSE chunk string
    """
    if isinstance(chunk, dict):
        # Use safe_dumps for proper JSON serialization with circular reference detection
        chunk_str = safe_dumps(chunk)
        return f"{STREAM_SSE_DATA_PREFIX}{chunk_str}\n\n"
    else:
        return chunk


async def async_data_generator_anthropic(
    response,
    user_api_key_dict: UserAPIKeyAuth,
    request_data: dict,
    proxy_logging_obj: ProxyLogging,
):
    verbose_proxy_logger.debug("inside generator")
    try:
        time.time()
        async for chunk in response:
            verbose_proxy_logger.debug(
                "async_data_generator: received streaming chunk - {}".format(chunk)
            )
            ### CALL HOOKS ### - modify outgoing data
            chunk = await proxy_logging_obj.async_post_call_streaming_hook(
                user_api_key_dict=user_api_key_dict, response=chunk
            )

            # Format chunk using helper function
            yield return_anthropic_chunk(chunk)
    except Exception as e:
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.async_data_generator(): Exception occured - {}".format(
                str(e)
            )
        )
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict,
            original_exception=e,
            request_data=request_data,
        )
        verbose_proxy_logger.debug(
            f"\033[1;31mAn error occurred: {e}\n\n Debug this by setting `--debug`, e.g. `litellm --model gpt-3.5-turbo --debug`"
        )

        if isinstance(e, HTTPException):
            raise e
        else:
            error_traceback = traceback.format_exc()
            error_msg = f"{str(e)}\n\n{error_traceback}"

        proxy_exception = ProxyException(
            message=getattr(e, "message", error_msg),
            type=getattr(e, "type", "None"),
            param=getattr(e, "param", "None"),
            code=getattr(e, "status_code", 500),
        )
        error_returned = json.dumps({"error": proxy_exception.to_dict()})
        yield f"{STREAM_SSE_DATA_PREFIX}{error_returned}\n\n"


@router.post(
    "/v1/messages",
    tags=["[beta] Anthropic `/v1/messages`"],
    dependencies=[Depends(user_api_key_auth)],
    include_in_schema=False,
)
async def anthropic_response(  # noqa: PLR0915
    fastapi_response: Response,
    request: Request,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Use `{PROXY_BASE_URL}/anthropic/v1/messages` instead - [Docs](https://docs.litellm.ai/docs/anthropic_completion).

    This was a BETA endpoint that calls 100+ LLMs in the anthropic format.
    """
    from litellm.proxy.proxy_server import (
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        user_api_base,
        user_max_tokens,
        user_model,
        user_request_timeout,
        user_temperature,
        version,
    )

    request_data = await _read_request_body(request=request)
    data: dict = {**request_data}
    try:
        data["model"] = (
            general_settings.get("completion_model", None)  # server default
            or user_model  # model name passed via cli args
            or data.get("model", None)  # default passed in http request
        )
        if user_model:
            data["model"] = user_model

        data = await add_litellm_data_to_request(
            data=data,  # type: ignore
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        # override with user settings, these are params passed via cli
        if user_temperature:
            data["temperature"] = user_temperature
        if user_request_timeout:
            data["request_timeout"] = user_request_timeout
        if user_max_tokens:
            data["max_tokens"] = user_max_tokens
        if user_api_base:
            data["api_base"] = user_api_base

        ### MODEL ALIAS MAPPING ###
        # check if model name in model alias map
        # get the actual model name
        if data["model"] in litellm.model_alias_map:
            data["model"] = litellm.model_alias_map[data["model"]]

        ### CALL HOOKS ### - modify incoming data before calling the model
        data = await proxy_logging_obj.pre_call_hook(  # type: ignore
            user_api_key_dict=user_api_key_dict, data=data, call_type="text_completion"
        )

        ### ROUTE THE REQUESTs ###
        router_model_names = llm_router.model_names if llm_router is not None else []

        # skip router if user passed their key
        if (
            llm_router is not None and data["model"] in router_model_names
        ):  # model in router model list
            llm_response = asyncio.create_task(llm_router.aanthropic_messages(**data))
        elif (
            llm_router is not None
            and llm_router.model_group_alias is not None
            and data["model"] in llm_router.model_group_alias
        ):  # model set in model_group_alias
            llm_response = asyncio.create_task(llm_router.aanthropic_messages(**data))
        elif (
            llm_router is not None and data["model"] in llm_router.deployment_names
        ):  # model in router deployments, calling a specific deployment on the router
            llm_response = asyncio.create_task(
                llm_router.aanthropic_messages(**data, specific_deployment=True)
            )
        elif (
            llm_router is not None and data["model"] in llm_router.get_model_ids()
        ):  # model in router model list
            llm_response = asyncio.create_task(llm_router.aanthropic_messages(**data))
        elif (
            llm_router is not None
            and data["model"] not in router_model_names
            and (
                llm_router.default_deployment is not None
                or len(llm_router.pattern_router.patterns) > 0
            )
        ):  # model in router deployments, calling a specific deployment on the router
            llm_response = asyncio.create_task(llm_router.aanthropic_messages(**data))
        elif user_model is not None:  # `litellm --model <your-model-name>`
            llm_response = asyncio.create_task(litellm.anthropic_messages(**data))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "completion: Invalid model name passed in model="
                    + data.get("model", "")
                },
            )

        # Await the llm_response task
        response = await llm_response

        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""
        response_cost = hidden_params.get("response_cost", None) or ""

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=data.get("litellm_call_id", ""), status="success"
            )
        )

        verbose_proxy_logger.debug("final response: %s", response)

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                response_cost=response_cost,
                request_data=data,
                hidden_params=hidden_params,
            )
        )

        if (
            "stream" in data and data["stream"] is True
        ):  # use generate_responses to stream responses
            selected_data_generator = async_data_generator_anthropic(
                response=response,
                user_api_key_dict=user_api_key_dict,
                request_data=data,
                proxy_logging_obj=proxy_logging_obj,
            )

            return await create_streaming_response(
                generator=selected_data_generator,
                media_type="text/event-stream",
                headers=dict(fastapi_response.headers),
            )

        verbose_proxy_logger.info("\nResponse from Litellm:\n{}".format(response))
        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.anthropic_response(): Exception occured - {}".format(
                str(e)
            )
        )
        error_msg = f"{str(e)}"
        raise ProxyException(
            message=getattr(e, "message", error_msg),
            type=getattr(e, "type", "None"),
            param=getattr(e, "param", "None"),
            code=getattr(e, "status_code", 500),
        )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\common_daily_activity.py ===
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

from fastapi import HTTPException, status

from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import CommonProxyErrors
from litellm.proxy.utils import PrismaClient
from litellm.types.proxy.management_endpoints.common_daily_activity import (
    BreakdownMetrics,
    DailySpendData,
    DailySpendMetadata,
    KeyMetadata,
    KeyMetricWithMetadata,
    MetricWithMetadata,
    SpendAnalyticsPaginatedResponse,
    SpendMetrics,
)


def update_metrics(existing_metrics: SpendMetrics, record: Any) -> SpendMetrics:
    """Update metrics with new record data."""
    existing_metrics.spend += record.spend
    existing_metrics.prompt_tokens += record.prompt_tokens
    existing_metrics.completion_tokens += record.completion_tokens
    existing_metrics.total_tokens += record.prompt_tokens + record.completion_tokens
    existing_metrics.cache_read_input_tokens += record.cache_read_input_tokens
    existing_metrics.cache_creation_input_tokens += record.cache_creation_input_tokens
    existing_metrics.api_requests += record.api_requests
    existing_metrics.successful_requests += record.successful_requests
    existing_metrics.failed_requests += record.failed_requests
    return existing_metrics


def update_breakdown_metrics(
    breakdown: BreakdownMetrics,
    record: Any,
    model_metadata: Dict[str, Dict[str, Any]],
    provider_metadata: Dict[str, Dict[str, Any]],
    api_key_metadata: Dict[str, Dict[str, Any]],
    entity_id_field: Optional[str] = None,
    entity_metadata_field: Optional[Dict[str, dict]] = None,
) -> BreakdownMetrics:
    """Updates breakdown metrics for a single record using the existing update_metrics function"""

    # Update model breakdown
    if record.model not in breakdown.models:
        breakdown.models[record.model] = MetricWithMetadata(
            metrics=SpendMetrics(),
            metadata=model_metadata.get(
                record.model, {}
            ),  # Add any model-specific metadata here
        )
    breakdown.models[record.model].metrics = update_metrics(
        breakdown.models[record.model].metrics, record
    )

    # Update provider breakdown
    provider = record.custom_llm_provider or "unknown"
    if provider not in breakdown.providers:
        breakdown.providers[provider] = MetricWithMetadata(
            metrics=SpendMetrics(),
            metadata=provider_metadata.get(
                provider, {}
            ),  # Add any provider-specific metadata here
        )
    breakdown.providers[provider].metrics = update_metrics(
        breakdown.providers[provider].metrics, record
    )

    # Update api key breakdown
    if record.api_key not in breakdown.api_keys:
        breakdown.api_keys[record.api_key] = KeyMetricWithMetadata(
            metrics=SpendMetrics(),
            metadata=KeyMetadata(
                key_alias=api_key_metadata.get(record.api_key, {}).get(
                    "key_alias", None
                ),
                team_id=api_key_metadata.get(record.api_key, {}).get("team_id", None),
            ),  # Add any api_key-specific metadata here
        )
    breakdown.api_keys[record.api_key].metrics = update_metrics(
        breakdown.api_keys[record.api_key].metrics, record
    )

    # Update entity-specific metrics if entity_id_field is provided
    if entity_id_field:
        entity_value = getattr(record, entity_id_field, None)
        entity_value = (
            entity_value if entity_value else "Unassigned"
        )  # allow for null entity_id_field
        if entity_value not in breakdown.entities:
            breakdown.entities[entity_value] = MetricWithMetadata(
                metrics=SpendMetrics(),
                metadata=entity_metadata_field.get(entity_value, {})
                if entity_metadata_field
                else {},
            )
        breakdown.entities[entity_value].metrics = update_metrics(
            breakdown.entities[entity_value].metrics, record
        )

    return breakdown


async def get_api_key_metadata(
    prisma_client: PrismaClient,
    api_keys: Set[str],
) -> Dict[str, Dict[str, Any]]:
    """Update api key metadata for a single record."""
    key_records = await prisma_client.db.litellm_verificationtoken.find_many(
        where={"token": {"in": list(api_keys)}}
    )
    return {
        k.token: {"key_alias": k.key_alias, "team_id": k.team_id} for k in key_records
    }


async def get_daily_activity(
    prisma_client: Optional[PrismaClient],
    table_name: str,
    entity_id_field: str,
    entity_id: Optional[Union[str, List[str]]],
    entity_metadata_field: Optional[Dict[str, dict]],
    start_date: Optional[str],
    end_date: Optional[str],
    model: Optional[str],
    api_key: Optional[str],
    page: int,
    page_size: int,
    exclude_entity_ids: Optional[List[str]] = None,
) -> SpendAnalyticsPaginatedResponse:
    """Common function to get daily activity for any entity type."""
    if prisma_client is None:
        raise HTTPException(
            status_code=500,
            detail={"error": CommonProxyErrors.db_not_connected_error.value},
        )

    if start_date is None or end_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Please provide start_date and end_date"},
        )

    try:
        # Build filter conditions
        where_conditions: Dict[str, Any] = {
            "date": {
                "gte": start_date,
                "lte": end_date,
            }
        }

        if model:
            where_conditions["model"] = model
        if api_key:
            where_conditions["api_key"] = api_key
        if entity_id is not None:
            if isinstance(entity_id, list):
                where_conditions[entity_id_field] = {"in": entity_id}
            else:
                where_conditions[entity_id_field] = entity_id
        if exclude_entity_ids:
            where_conditions.setdefault(entity_id_field, {})["not"] = {
                "in": exclude_entity_ids
            }

        # Get total count for pagination
        total_count = await getattr(prisma_client.db, table_name).count(
            where=where_conditions
        )

        # Fetch paginated results
        daily_spend_data = await getattr(prisma_client.db, table_name).find_many(
            where=where_conditions,
            order=[
                {"date": "desc"},
            ],
            skip=(page - 1) * page_size,
            take=page_size,
        )

        # Get all unique API keys from the spend data
        api_keys = set()
        for record in daily_spend_data:
            if record.api_key:
                api_keys.add(record.api_key)

        # Fetch key aliases in bulk
        api_key_metadata: Dict[str, Dict[str, Any]] = {}
        model_metadata: Dict[str, Dict[str, Any]] = {}
        provider_metadata: Dict[str, Dict[str, Any]] = {}
        if api_keys:
            api_key_metadata = await get_api_key_metadata(prisma_client, api_keys)

        # Process results
        results = []
        total_metrics = SpendMetrics()
        grouped_data: Dict[str, Dict[str, Any]] = {}

        for record in daily_spend_data:
            date_str = record.date
            if date_str not in grouped_data:
                grouped_data[date_str] = {
                    "metrics": SpendMetrics(),
                    "breakdown": BreakdownMetrics(),
                }

            # Update metrics
            grouped_data[date_str]["metrics"] = update_metrics(
                grouped_data[date_str]["metrics"], record
            )
            # Update breakdowns
            grouped_data[date_str]["breakdown"] = update_breakdown_metrics(
                grouped_data[date_str]["breakdown"],
                record,
                model_metadata,
                provider_metadata,
                api_key_metadata,
                entity_id_field=entity_id_field,
                entity_metadata_field=entity_metadata_field,
            )

            # Update total metrics
            total_metrics.spend += record.spend
            total_metrics.prompt_tokens += record.prompt_tokens
            total_metrics.completion_tokens += record.completion_tokens
            total_metrics.total_tokens += (
                record.prompt_tokens + record.completion_tokens
            )
            total_metrics.cache_read_input_tokens += record.cache_read_input_tokens
            total_metrics.cache_creation_input_tokens += (
                record.cache_creation_input_tokens
            )
            total_metrics.api_requests += record.api_requests
            total_metrics.successful_requests += record.successful_requests
            total_metrics.failed_requests += record.failed_requests

        # Convert grouped data to response format
        for date_str, data in grouped_data.items():
            results.append(
                DailySpendData(
                    date=datetime.strptime(date_str, "%Y-%m-%d").date(),
                    metrics=data["metrics"],
                    breakdown=data["breakdown"],
                )
            )

        # Sort results by date
        results.sort(key=lambda x: x.date, reverse=True)

        return SpendAnalyticsPaginatedResponse(
            results=results,
            metadata=DailySpendMetadata(
                total_spend=total_metrics.spend,
                total_prompt_tokens=total_metrics.prompt_tokens,
                total_completion_tokens=total_metrics.completion_tokens,
                total_tokens=total_metrics.total_tokens,
                total_api_requests=total_metrics.api_requests,
                total_successful_requests=total_metrics.successful_requests,
                total_failed_requests=total_metrics.failed_requests,
                total_cache_read_input_tokens=total_metrics.cache_read_input_tokens,
                total_cache_creation_input_tokens=total_metrics.cache_creation_input_tokens,
                page=page,
                total_pages=-(-total_count // page_size),  # Ceiling division
                has_more=(page * page_size) < total_count,
            ),
        )

    except Exception as e:
        verbose_proxy_logger.exception(f"Error fetching daily activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to fetch analytics: {str(e)}"},
        )

# === NexusCore/openenv\Lib\site-packages\tornado\test\routing_test.py ===
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

from tornado.httputil import (
    HTTPHeaders,
    HTTPMessageDelegate,
    HTTPServerConnectionDelegate,
    ResponseStartLine,
)
from tornado.routing import (
    HostMatches,
    PathMatches,
    ReversibleRouter,
    Router,
    Rule,
    RuleRouter,
)
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application, HTTPError, RequestHandler
from tornado.wsgi import WSGIContainer

import typing  # noqa: F401


class BasicRouter(Router):
    def find_handler(self, request, **kwargs):
        class MessageDelegate(HTTPMessageDelegate):
            def __init__(self, connection):
                self.connection = connection

            def finish(self):
                self.connection.write_headers(
                    ResponseStartLine("HTTP/1.1", 200, "OK"),
                    HTTPHeaders({"Content-Length": "2"}),
                    b"OK",
                )
                self.connection.finish()

        return MessageDelegate(request.connection)


class BasicRouterTestCase(AsyncHTTPTestCase):
    def get_app(self):
        return BasicRouter()

    def test_basic_router(self):
        response = self.fetch("/any_request")
        self.assertEqual(response.body, b"OK")


resources = {}  # type: typing.Dict[str, bytes]


class GetResource(RequestHandler):
    def get(self, path):
        if path not in resources:
            raise HTTPError(404)

        self.finish(resources[path])


class PostResource(RequestHandler):
    def post(self, path):
        resources[path] = self.request.body


class HTTPMethodRouter(Router):
    def __init__(self, app):
        self.app = app

    def find_handler(self, request, **kwargs):
        handler = GetResource if request.method == "GET" else PostResource
        return self.app.get_handler_delegate(request, handler, path_args=[request.path])


class HTTPMethodRouterTestCase(AsyncHTTPTestCase):
    def get_app(self):
        return HTTPMethodRouter(Application())

    def test_http_method_router(self):
        response = self.fetch("/post_resource", method="POST", body="data")
        self.assertEqual(response.code, 200)

        response = self.fetch("/get_resource")
        self.assertEqual(response.code, 404)

        response = self.fetch("/post_resource")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b"data")


def _get_named_handler(handler_name):
    class Handler(RequestHandler):
        def get(self, *args, **kwargs):
            if self.application.settings.get("app_name") is not None:
                self.write(self.application.settings["app_name"] + ": ")

            self.finish(handler_name + ": " + self.reverse_url(handler_name))

    return Handler


FirstHandler = _get_named_handler("first_handler")
SecondHandler = _get_named_handler("second_handler")


class CustomRouter(ReversibleRouter):
    def __init__(self):
        super().__init__()
        self.routes = {}  # type: typing.Dict[str, typing.Any]

    def add_routes(self, routes):
        self.routes.update(routes)

    def find_handler(self, request, **kwargs):
        if request.path in self.routes:
            app, handler = self.routes[request.path]
            return app.get_handler_delegate(request, handler)

    def reverse_url(self, name, *args):
        handler_path = "/" + name
        return handler_path if handler_path in self.routes else None


class CustomRouterTestCase(AsyncHTTPTestCase):
    def get_app(self):
        router = CustomRouter()

        class CustomApplication(Application):
            def reverse_url(self, name, *args):
                return router.reverse_url(name, *args)

        app1 = CustomApplication(app_name="app1")
        app2 = CustomApplication(app_name="app2")

        router.add_routes(
            {
                "/first_handler": (app1, FirstHandler),
                "/second_handler": (app2, SecondHandler),
                "/first_handler_second_app": (app2, FirstHandler),
            }
        )

        return router

    def test_custom_router(self):
        response = self.fetch("/first_handler")
        self.assertEqual(response.body, b"app1: first_handler: /first_handler")
        response = self.fetch("/second_handler")
        self.assertEqual(response.body, b"app2: second_handler: /second_handler")
        response = self.fetch("/first_handler_second_app")
        self.assertEqual(response.body, b"app2: first_handler: /first_handler")


class ConnectionDelegate(HTTPServerConnectionDelegate):
    def start_request(self, server_conn, request_conn):
        class MessageDelegate(HTTPMessageDelegate):
            def __init__(self, connection):
                self.connection = connection

            def finish(self):
                response_body = b"OK"
                self.connection.write_headers(
                    ResponseStartLine("HTTP/1.1", 200, "OK"),
                    HTTPHeaders({"Content-Length": str(len(response_body))}),
                )
                self.connection.write(response_body)
                self.connection.finish()

        return MessageDelegate(request_conn)


class RuleRouterTest(AsyncHTTPTestCase):
    def get_app(self):
        app = Application()

        def request_callable(request):
            request.connection.write_headers(
                ResponseStartLine("HTTP/1.1", 200, "OK"),
                HTTPHeaders({"Content-Length": "2"}),
            )
            request.connection.write(b"OK")
            request.connection.finish()

        router = CustomRouter()
        router.add_routes(
            {"/nested_handler": (app, _get_named_handler("nested_handler"))}
        )

        app.add_handlers(
            ".*",
            [
                (
                    HostMatches("www.example.com"),
                    [
                        (
                            PathMatches("/first_handler"),
                            "tornado.test.routing_test.SecondHandler",
                            {},
                            "second_handler",
                        )
                    ],
                ),
                Rule(PathMatches("/.*handler"), router),
                Rule(PathMatches("/first_handler"), FirstHandler, name="first_handler"),
                Rule(PathMatches("/request_callable"), request_callable),
                ("/connection_delegate", ConnectionDelegate()),
            ],
        )

        return app

    def test_rule_based_router(self):
        response = self.fetch("/first_handler")
        self.assertEqual(response.body, b"first_handler: /first_handler")

        response = self.fetch("/first_handler", headers={"Host": "www.example.com"})
        self.assertEqual(response.body, b"second_handler: /first_handler")

        response = self.fetch("/nested_handler")
        self.assertEqual(response.body, b"nested_handler: /nested_handler")

        response = self.fetch("/nested_not_found_handler")
        self.assertEqual(response.code, 404)

        response = self.fetch("/connection_delegate")
        self.assertEqual(response.body, b"OK")

        response = self.fetch("/request_callable")
        self.assertEqual(response.body, b"OK")

        response = self.fetch("/404")
        self.assertEqual(response.code, 404)


class WSGIContainerTestCase(AsyncHTTPTestCase):
    def get_app(self):
        wsgi_app = WSGIContainer(self.wsgi_app)

        class Handler(RequestHandler):
            def get(self, *args, **kwargs):
                self.finish(self.reverse_url("tornado"))

        return RuleRouter(
            [
                (
                    PathMatches("/tornado.*"),
                    Application([(r"/tornado/test", Handler, {}, "tornado")]),
                ),
                (PathMatches("/wsgi"), wsgi_app),
            ]
        )

    def wsgi_app(self, environ, start_response):
        start_response("200 OK", [])
        return [b"WSGI"]

    def test_wsgi_container(self):
        response = self.fetch("/tornado/test")
        self.assertEqual(response.body, b"/tornado/test")

        response = self.fetch("/wsgi")
        self.assertEqual(response.body, b"WSGI")

    def test_delegate_not_found(self):
        response = self.fetch("/404")
        self.assertEqual(response.code, 404)

# === NexusCore/openenv\Lib\site-packages\parso\cache.py ===
import time
import os
import sys
import hashlib
import gc
import shutil
import platform
import logging
import warnings
import pickle
from pathlib import Path
from typing import Dict, Any

LOG = logging.getLogger(__name__)

_CACHED_FILE_MINIMUM_SURVIVAL = 60 * 10  # 10 minutes
"""
Cached files should survive at least a few minutes.
"""

_CACHED_FILE_MAXIMUM_SURVIVAL = 60 * 60 * 24 * 30
"""
Maximum time for a cached file to survive if it is not
accessed within.
"""

_CACHED_SIZE_TRIGGER = 600
"""
This setting limits the amount of cached files. It's basically a way to start
garbage collection.

The reasoning for this limit being as big as it is, is the following:

Numpy, Pandas, Matplotlib and Tensorflow together use about 500 files. This
makes Jedi use ~500mb of memory. Since we might want a bit more than those few
libraries, we just increase it a bit.
"""

_PICKLE_VERSION = 33
"""
Version number (integer) for file system cache.

Increment this number when there are any incompatible changes in
the parser tree classes.  For example, the following changes
are regarded as incompatible.

- A class name is changed.
- A class is moved to another module.
- A __slot__ of a class is changed.
"""

_VERSION_TAG = '%s-%s%s-%s' % (
    platform.python_implementation(),
    sys.version_info[0],
    sys.version_info[1],
    _PICKLE_VERSION
)
"""
Short name for distinguish Python implementations and versions.

It's a bit similar to `sys.implementation.cache_tag`.
See: http://docs.python.org/3/library/sys.html#sys.implementation
"""


def _get_default_cache_path():
    if platform.system().lower() == 'windows':
        dir_ = Path(os.getenv('LOCALAPPDATA') or '~', 'Parso', 'Parso')
    elif platform.system().lower() == 'darwin':
        dir_ = Path('~', 'Library', 'Caches', 'Parso')
    else:
        dir_ = Path(os.getenv('XDG_CACHE_HOME') or '~/.cache', 'parso')
    return dir_.expanduser()


_default_cache_path = _get_default_cache_path()
"""
The path where the cache is stored.

On Linux, this defaults to ``~/.cache/parso/``, on OS X to
``~/Library/Caches/Parso/`` and on Windows to ``%LOCALAPPDATA%\\Parso\\Parso\\``.
On Linux, if environment variable ``$XDG_CACHE_HOME`` is set,
``$XDG_CACHE_HOME/parso`` is used instead of the default one.
"""

_CACHE_CLEAR_THRESHOLD = 60 * 60 * 24


def _get_cache_clear_lock_path(cache_path=None):
    """
    The path where the cache lock is stored.

    Cache lock will prevent continous cache clearing and only allow garbage
    collection once a day (can be configured in _CACHE_CLEAR_THRESHOLD).
    """
    cache_path = cache_path or _default_cache_path
    return cache_path.joinpath("PARSO-CACHE-LOCK")


parser_cache: Dict[str, Any] = {}


class _NodeCacheItem:
    def __init__(self, node, lines, change_time=None):
        self.node = node
        self.lines = lines
        if change_time is None:
            change_time = time.time()
        self.change_time = change_time
        self.last_used = change_time


def load_module(hashed_grammar, file_io, cache_path=None):
    """
    Returns a module or None, if it fails.
    """
    p_time = file_io.get_last_modified()
    if p_time is None:
        return None

    try:
        module_cache_item = parser_cache[hashed_grammar][file_io.path]
        if p_time <= module_cache_item.change_time:
            module_cache_item.last_used = time.time()
            return module_cache_item.node
    except KeyError:
        return _load_from_file_system(
            hashed_grammar,
            file_io.path,
            p_time,
            cache_path=cache_path
        )


def _load_from_file_system(hashed_grammar, path, p_time, cache_path=None):
    cache_path = _get_hashed_path(hashed_grammar, path, cache_path=cache_path)
    try:
        if p_time > os.path.getmtime(cache_path):
            # Cache is outdated
            return None

        with open(cache_path, 'rb') as f:
            gc.disable()
            try:
                module_cache_item = pickle.load(f)
            finally:
                gc.enable()
    except FileNotFoundError:
        return None
    else:
        _set_cache_item(hashed_grammar, path, module_cache_item)
        LOG.debug('pickle loaded: %s', path)
        return module_cache_item.node


def _set_cache_item(hashed_grammar, path, module_cache_item):
    if sum(len(v) for v in parser_cache.values()) >= _CACHED_SIZE_TRIGGER:
        # Garbage collection of old cache files.
        # We are basically throwing everything away that hasn't been accessed
        # in 10 minutes.
        cutoff_time = time.time() - _CACHED_FILE_MINIMUM_SURVIVAL
        for key, path_to_item_map in parser_cache.items():
            parser_cache[key] = {
                path: node_item
                for path, node_item in path_to_item_map.items()
                if node_item.last_used > cutoff_time
            }

    parser_cache.setdefault(hashed_grammar, {})[path] = module_cache_item


def try_to_save_module(hashed_grammar, file_io, module, lines, pickling=True, cache_path=None):
    path = file_io.path
    try:
        p_time = None if path is None else file_io.get_last_modified()
    except OSError:
        p_time = None
        pickling = False

    item = _NodeCacheItem(module, lines, p_time)
    _set_cache_item(hashed_grammar, path, item)
    if pickling and path is not None:
        try:
            _save_to_file_system(hashed_grammar, path, item, cache_path=cache_path)
        except PermissionError:
            # It's not really a big issue if the cache cannot be saved to the
            # file system. It's still in RAM in that case. However we should
            # still warn the user that this is happening.
            warnings.warn(
                'Tried to save a file to %s, but got permission denied.' % path,
                Warning
            )
        else:
            _remove_cache_and_update_lock(cache_path=cache_path)


def _save_to_file_system(hashed_grammar, path, item, cache_path=None):
    with open(_get_hashed_path(hashed_grammar, path, cache_path=cache_path), 'wb') as f:
        pickle.dump(item, f, pickle.HIGHEST_PROTOCOL)


def clear_cache(cache_path=None):
    if cache_path is None:
        cache_path = _default_cache_path
    shutil.rmtree(cache_path)
    parser_cache.clear()


def clear_inactive_cache(
    cache_path=None,
    inactivity_threshold=_CACHED_FILE_MAXIMUM_SURVIVAL,
):
    if cache_path is None:
        cache_path = _default_cache_path
    if not cache_path.exists():
        return False
    for dirname in os.listdir(cache_path):
        version_path = cache_path.joinpath(dirname)
        if not version_path.is_dir():
            continue
        for file in os.scandir(version_path):
            if file.stat().st_atime + _CACHED_FILE_MAXIMUM_SURVIVAL <= time.time():
                try:
                    os.remove(file.path)
                except OSError:  # silently ignore all failures
                    continue
    else:
        return True


def _touch(path):
    try:
        os.utime(path, None)
    except FileNotFoundError:
        try:
            file = open(path, 'a')
            file.close()
        except (OSError, IOError):  # TODO Maybe log this?
            return False
    return True


def _remove_cache_and_update_lock(cache_path=None):
    lock_path = _get_cache_clear_lock_path(cache_path=cache_path)
    try:
        clear_lock_time = os.path.getmtime(lock_path)
    except FileNotFoundError:
        clear_lock_time = None
    if (
        clear_lock_time is None  # first time
        or clear_lock_time + _CACHE_CLEAR_THRESHOLD <= time.time()
    ):
        if not _touch(lock_path):
            # First make sure that as few as possible other cleanup jobs also
            # get started. There is still a race condition but it's probably
            # not a big problem.
            return False

        clear_inactive_cache(cache_path=cache_path)


def _get_hashed_path(hashed_grammar, path, cache_path=None):
    directory = _get_cache_directory_path(cache_path=cache_path)

    file_hash = hashlib.sha256(str(path).encode("utf-8")).hexdigest()
    return os.path.join(directory, '%s-%s.pkl' % (hashed_grammar, file_hash))


def _get_cache_directory_path(cache_path=None):
    if cache_path is None:
        cache_path = _default_cache_path
    directory = cache_path.joinpath(_VERSION_TAG)
    if not directory.exists():
        os.makedirs(directory)
    return directory

# === NexusCore/openenv\Lib\site-packages\tornado\concurrent.py ===
#
# Copyright 2012 Facebook
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
"""Utilities for working with ``Future`` objects.

Tornado previously provided its own ``Future`` class, but now uses
`asyncio.Future`. This module contains utility functions for working
with `asyncio.Future` in a way that is backwards-compatible with
Tornado's old ``Future`` implementation.

While this module is an important part of Tornado's internal
implementation, applications rarely need to interact with it
directly.

"""

import asyncio
from concurrent import futures
import functools
import sys
import types

from tornado.log import app_log

import typing
from typing import Any, Callable, Optional, Tuple, Union

_T = typing.TypeVar("_T")


class ReturnValueIgnoredError(Exception):
    # No longer used; was previously used by @return_future
    pass


Future = asyncio.Future

FUTURES = (futures.Future, Future)


def is_future(x: Any) -> bool:
    return isinstance(x, FUTURES)


class DummyExecutor(futures.Executor):
    def submit(  # type: ignore[override]
        self, fn: Callable[..., _T], *args: Any, **kwargs: Any
    ) -> "futures.Future[_T]":
        future = futures.Future()  # type: futures.Future[_T]
        try:
            future_set_result_unless_cancelled(future, fn(*args, **kwargs))
        except Exception:
            future_set_exc_info(future, sys.exc_info())
        return future

    if sys.version_info >= (3, 9):

        def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
            pass

    else:

        def shutdown(self, wait: bool = True) -> None:
            pass


dummy_executor = DummyExecutor()


def run_on_executor(*args: Any, **kwargs: Any) -> Callable:
    """Decorator to run a synchronous method asynchronously on an executor.

    Returns a future.

    The executor to be used is determined by the ``executor``
    attributes of ``self``. To use a different attribute name, pass a
    keyword argument to the decorator::

        @run_on_executor(executor='_thread_pool')
        def foo(self):
            pass

    This decorator should not be confused with the similarly-named
    `.IOLoop.run_in_executor`. In general, using ``run_in_executor``
    when *calling* a blocking method is recommended instead of using
    this decorator when *defining* a method. If compatibility with older
    versions of Tornado is required, consider defining an executor
    and using ``executor.submit()`` at the call site.

    .. versionchanged:: 4.2
       Added keyword arguments to use alternative attributes.

    .. versionchanged:: 5.0
       Always uses the current IOLoop instead of ``self.io_loop``.

    .. versionchanged:: 5.1
       Returns a `.Future` compatible with ``await`` instead of a
       `concurrent.futures.Future`.

    .. deprecated:: 5.1

       The ``callback`` argument is deprecated and will be removed in
       6.0. The decorator itself is discouraged in new code but will
       not be removed in 6.0.

    .. versionchanged:: 6.0

       The ``callback`` argument was removed.
    """

    # Fully type-checking decorators is tricky, and this one is
    # discouraged anyway so it doesn't have all the generic magic.
    def run_on_executor_decorator(fn: Callable) -> Callable[..., Future]:
        executor = kwargs.get("executor", "executor")

        @functools.wraps(fn)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Future:
            async_future = Future()  # type: Future
            conc_future = getattr(self, executor).submit(fn, self, *args, **kwargs)
            chain_future(conc_future, async_future)
            return async_future

        return wrapper

    if args and kwargs:
        raise ValueError("cannot combine positional and keyword args")
    if len(args) == 1:
        return run_on_executor_decorator(args[0])
    elif len(args) != 0:
        raise ValueError("expected 1 argument, got %d", len(args))
    return run_on_executor_decorator


_NO_RESULT = object()


def chain_future(
    a: Union["Future[_T]", "futures.Future[_T]"],
    b: Union["Future[_T]", "futures.Future[_T]"],
) -> None:
    """Chain two futures together so that when one completes, so does the other.

    The result (success or failure) of ``a`` will be copied to ``b``, unless
    ``b`` has already been completed or cancelled by the time ``a`` finishes.

    .. versionchanged:: 5.0

       Now accepts both Tornado/asyncio `Future` objects and
       `concurrent.futures.Future`.

    """

    def copy(a: "Future[_T]") -> None:
        if b.done():
            return
        if hasattr(a, "exc_info") and a.exc_info() is not None:  # type: ignore
            future_set_exc_info(b, a.exc_info())  # type: ignore
        else:
            a_exc = a.exception()
            if a_exc is not None:
                b.set_exception(a_exc)
            else:
                b.set_result(a.result())

    if isinstance(a, Future):
        future_add_done_callback(a, copy)
    else:
        # concurrent.futures.Future
        from tornado.ioloop import IOLoop

        IOLoop.current().add_future(a, copy)


def future_set_result_unless_cancelled(
    future: "Union[futures.Future[_T], Future[_T]]", value: _T
) -> None:
    """Set the given ``value`` as the `Future`'s result, if not cancelled.

    Avoids ``asyncio.InvalidStateError`` when calling ``set_result()`` on
    a cancelled `asyncio.Future`.

    .. versionadded:: 5.0
    """
    if not future.cancelled():
        future.set_result(value)


def future_set_exception_unless_cancelled(
    future: "Union[futures.Future[_T], Future[_T]]", exc: BaseException
) -> None:
    """Set the given ``exc`` as the `Future`'s exception.

    If the Future is already canceled, logs the exception instead. If
    this logging is not desired, the caller should explicitly check
    the state of the Future and call ``Future.set_exception`` instead of
    this wrapper.

    Avoids ``asyncio.InvalidStateError`` when calling ``set_exception()`` on
    a cancelled `asyncio.Future`.

    .. versionadded:: 6.0

    """
    if not future.cancelled():
        future.set_exception(exc)
    else:
        app_log.error("Exception after Future was cancelled", exc_info=exc)


def future_set_exc_info(
    future: "Union[futures.Future[_T], Future[_T]]",
    exc_info: Tuple[
        Optional[type], Optional[BaseException], Optional[types.TracebackType]
    ],
) -> None:
    """Set the given ``exc_info`` as the `Future`'s exception.

    Understands both `asyncio.Future` and the extensions in older
    versions of Tornado to enable better tracebacks on Python 2.

    .. versionadded:: 5.0

    .. versionchanged:: 6.0

       If the future is already cancelled, this function is a no-op.
       (previously ``asyncio.InvalidStateError`` would be raised)

    """
    if exc_info[1] is None:
        raise Exception("future_set_exc_info called with no exception")
    future_set_exception_unless_cancelled(future, exc_info[1])


@typing.overload
def future_add_done_callback(
    future: "futures.Future[_T]", callback: Callable[["futures.Future[_T]"], None]
) -> None:
    pass


@typing.overload  # noqa: F811
def future_add_done_callback(
    future: "Future[_T]", callback: Callable[["Future[_T]"], None]
) -> None:
    pass


def future_add_done_callback(  # noqa: F811
    future: "Union[futures.Future[_T], Future[_T]]", callback: Callable[..., None]
) -> None:
    """Arrange to call ``callback`` when ``future`` is complete.

    ``callback`` is invoked with one argument, the ``future``.

    If ``future`` is already done, ``callback`` is invoked immediately.
    This may differ from the behavior of ``Future.add_done_callback``,
    which makes no such guarantee.

    .. versionadded:: 5.0
    """
    if future.done():
        callback(future)
    else:
        future.add_done_callback(callback)

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\axisartist\floating_axes.py ===
"""
An experimental support for curvilinear grid.
"""

# TODO :
# see if tick_iterator method can be simplified by reusing the parent method.

import functools

import numpy as np

import matplotlib as mpl
from matplotlib import _api, cbook
import matplotlib.patches as mpatches
from matplotlib.path import Path

from mpl_toolkits.axes_grid1.parasite_axes import host_axes_class_factory

from . import axislines, grid_helper_curvelinear
from .axis_artist import AxisArtist
from .grid_finder import ExtremeFinderSimple


class FloatingAxisArtistHelper(
        grid_helper_curvelinear.FloatingAxisArtistHelper):
    pass


class FixedAxisArtistHelper(grid_helper_curvelinear.FloatingAxisArtistHelper):

    def __init__(self, grid_helper, side, nth_coord_ticks=None):
        """
        nth_coord = along which coordinate value varies.
         nth_coord = 0 ->  x axis, nth_coord = 1 -> y axis
        """
        lon1, lon2, lat1, lat2 = grid_helper.grid_finder.extreme_finder(*[None] * 5)
        value, nth_coord = _api.check_getitem(
            dict(left=(lon1, 0), right=(lon2, 0), bottom=(lat1, 1), top=(lat2, 1)),
            side=side)
        super().__init__(grid_helper, nth_coord, value, axis_direction=side)
        if nth_coord_ticks is None:
            nth_coord_ticks = nth_coord
        self.nth_coord_ticks = nth_coord_ticks

        self.value = value
        self.grid_helper = grid_helper
        self._side = side

    def update_lim(self, axes):
        self.grid_helper.update_lim(axes)
        self._grid_info = self.grid_helper._grid_info

    def get_tick_iterators(self, axes):
        """tick_loc, tick_angle, tick_label, (optionally) tick_label"""

        grid_finder = self.grid_helper.grid_finder

        lat_levs, lat_n, lat_factor = self._grid_info["lat_info"]
        yy0 = lat_levs / lat_factor

        lon_levs, lon_n, lon_factor = self._grid_info["lon_info"]
        xx0 = lon_levs / lon_factor

        extremes = self.grid_helper.grid_finder.extreme_finder(*[None] * 5)
        xmin, xmax = sorted(extremes[:2])
        ymin, ymax = sorted(extremes[2:])

        def trf_xy(x, y):
            trf = grid_finder.get_transform() + axes.transData
            return trf.transform(np.column_stack(np.broadcast_arrays(x, y))).T

        if self.nth_coord == 0:
            mask = (ymin <= yy0) & (yy0 <= ymax)
            (xx1, yy1), (dxx1, dyy1), (dxx2, dyy2) = \
                grid_helper_curvelinear._value_and_jacobian(
                    trf_xy, self.value, yy0[mask], (xmin, xmax), (ymin, ymax))
            labels = self._grid_info["lat_labels"]

        elif self.nth_coord == 1:
            mask = (xmin <= xx0) & (xx0 <= xmax)
            (xx1, yy1), (dxx2, dyy2), (dxx1, dyy1) = \
                grid_helper_curvelinear._value_and_jacobian(
                    trf_xy, xx0[mask], self.value, (xmin, xmax), (ymin, ymax))
            labels = self._grid_info["lon_labels"]

        labels = [l for l, m in zip(labels, mask) if m]

        angle_normal = np.arctan2(dyy1, dxx1)
        angle_tangent = np.arctan2(dyy2, dxx2)
        mm = (dyy1 == 0) & (dxx1 == 0)  # points with degenerate normal
        angle_normal[mm] = angle_tangent[mm] + np.pi / 2

        tick_to_axes = self.get_tick_transform(axes) - axes.transAxes
        in_01 = functools.partial(
            mpl.transforms._interval_contains_close, (0, 1))

        def f1():
            for x, y, normal, tangent, lab \
                    in zip(xx1, yy1, angle_normal, angle_tangent, labels):
                c2 = tick_to_axes.transform((x, y))
                if in_01(c2[0]) and in_01(c2[1]):
                    yield [x, y], *np.rad2deg([normal, tangent]), lab

        return f1(), iter([])

    def get_line(self, axes):
        self.update_lim(axes)
        k, v = dict(left=("lon_lines0", 0),
                    right=("lon_lines0", 1),
                    bottom=("lat_lines0", 0),
                    top=("lat_lines0", 1))[self._side]
        xx, yy = self._grid_info[k][v]
        return Path(np.column_stack([xx, yy]))


class ExtremeFinderFixed(ExtremeFinderSimple):
    # docstring inherited

    def __init__(self, extremes):
        """
        This subclass always returns the same bounding box.

        Parameters
        ----------
        extremes : (float, float, float, float)
            The bounding box that this helper always returns.
        """
        self._extremes = extremes

    def __call__(self, transform_xy, x1, y1, x2, y2):
        # docstring inherited
        return self._extremes


class GridHelperCurveLinear(grid_helper_curvelinear.GridHelperCurveLinear):

    def __init__(self, aux_trans, extremes,
                 grid_locator1=None,
                 grid_locator2=None,
                 tick_formatter1=None,
                 tick_formatter2=None):
        # docstring inherited
        super().__init__(aux_trans,
                         extreme_finder=ExtremeFinderFixed(extremes),
                         grid_locator1=grid_locator1,
                         grid_locator2=grid_locator2,
                         tick_formatter1=tick_formatter1,
                         tick_formatter2=tick_formatter2)

    def new_fixed_axis(
            self, loc, nth_coord=None, axis_direction=None, offset=None, axes=None):
        if axes is None:
            axes = self.axes
        if axis_direction is None:
            axis_direction = loc
        # This is not the same as the FixedAxisArtistHelper class used by
        # grid_helper_curvelinear.GridHelperCurveLinear.new_fixed_axis!
        helper = FixedAxisArtistHelper(
            self, loc, nth_coord_ticks=nth_coord)
        axisline = AxisArtist(axes, helper, axis_direction=axis_direction)
        # Perhaps should be moved to the base class?
        axisline.line.set_clip_on(True)
        axisline.line.set_clip_box(axisline.axes.bbox)
        return axisline

    # new_floating_axis will inherit the grid_helper's extremes.

    # def new_floating_axis(self, nth_coord, value, axes=None, axis_direction="bottom"):
    #     axis = super(GridHelperCurveLinear,
    #                  self).new_floating_axis(nth_coord,
    #                                          value, axes=axes,
    #                                          axis_direction=axis_direction)
    #     # set extreme values of the axis helper
    #     if nth_coord == 1:
    #         axis.get_helper().set_extremes(*self._extremes[:2])
    #     elif nth_coord == 0:
    #         axis.get_helper().set_extremes(*self._extremes[2:])
    #     return axis

    def _update_grid(self, x1, y1, x2, y2):
        if self._grid_info is None:
            self._grid_info = dict()

        grid_info = self._grid_info

        grid_finder = self.grid_finder
        extremes = grid_finder.extreme_finder(grid_finder.inv_transform_xy,
                                              x1, y1, x2, y2)

        lon_min, lon_max = sorted(extremes[:2])
        lat_min, lat_max = sorted(extremes[2:])
        grid_info["extremes"] = lon_min, lon_max, lat_min, lat_max  # extremes

        lon_levs, lon_n, lon_factor = \
            grid_finder.grid_locator1(lon_min, lon_max)
        lon_levs = np.asarray(lon_levs)
        lat_levs, lat_n, lat_factor = \
            grid_finder.grid_locator2(lat_min, lat_max)
        lat_levs = np.asarray(lat_levs)

        grid_info["lon_info"] = lon_levs, lon_n, lon_factor
        grid_info["lat_info"] = lat_levs, lat_n, lat_factor

        grid_info["lon_labels"] = grid_finder._format_ticks(
            1, "bottom", lon_factor, lon_levs)
        grid_info["lat_labels"] = grid_finder._format_ticks(
            2, "bottom", lat_factor, lat_levs)

        lon_values = lon_levs[:lon_n] / lon_factor
        lat_values = lat_levs[:lat_n] / lat_factor

        lon_lines, lat_lines = grid_finder._get_raw_grid_lines(
            lon_values[(lon_min < lon_values) & (lon_values < lon_max)],
            lat_values[(lat_min < lat_values) & (lat_values < lat_max)],
            lon_min, lon_max, lat_min, lat_max)

        grid_info["lon_lines"] = lon_lines
        grid_info["lat_lines"] = lat_lines

        lon_lines, lat_lines = grid_finder._get_raw_grid_lines(
            # lon_min, lon_max, lat_min, lat_max)
            extremes[:2], extremes[2:], *extremes)

        grid_info["lon_lines0"] = lon_lines
        grid_info["lat_lines0"] = lat_lines

    def get_gridlines(self, which="major", axis="both"):
        grid_lines = []
        if axis in ["both", "x"]:
            grid_lines.extend(self._grid_info["lon_lines"])
        if axis in ["both", "y"]:
            grid_lines.extend(self._grid_info["lat_lines"])
        return grid_lines


class FloatingAxesBase:

    def __init__(self, *args, grid_helper, **kwargs):
        _api.check_isinstance(GridHelperCurveLinear, grid_helper=grid_helper)
        super().__init__(*args, grid_helper=grid_helper, **kwargs)
        self.set_aspect(1.)

    def _gen_axes_patch(self):
        # docstring inherited
        x0, x1, y0, y1 = self.get_grid_helper().grid_finder.extreme_finder(*[None] * 5)
        patch = mpatches.Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        patch.get_path()._interpolation_steps = 100
        return patch

    def clear(self):
        super().clear()
        self.patch.set_transform(
            self.get_grid_helper().grid_finder.get_transform()
            + self.transData)
        # The original patch is not in the draw tree; it is only used for
        # clipping purposes.
        orig_patch = super()._gen_axes_patch()
        orig_patch.set_figure(self.get_figure(root=False))
        orig_patch.set_transform(self.transAxes)
        self.patch.set_clip_path(orig_patch)
        self.gridlines.set_clip_path(orig_patch)
        self.adjust_axes_lim()

    def adjust_axes_lim(self):
        bbox = self.patch.get_path().get_extents(
            # First transform to pixel coords, then to parent data coords.
            self.patch.get_transform() - self.transData)
        bbox = bbox.expanded(1.02, 1.02)
        self.set_xlim(bbox.xmin, bbox.xmax)
        self.set_ylim(bbox.ymin, bbox.ymax)


floatingaxes_class_factory = cbook._make_class_factory(FloatingAxesBase, "Floating{}")
FloatingAxes = floatingaxes_class_factory(host_axes_class_factory(axislines.Axes))
FloatingSubplot = FloatingAxes

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\test_corpora.py ===
import unittest

import pytest

from nltk.corpus import (  # mwa_ppdb
    cess_cat,
    cess_esp,
    conll2007,
    floresta,
    indian,
    ptb,
    sinica_treebank,
    udhr,
)
from nltk.tree import Tree


class TestUdhr(unittest.TestCase):
    def test_words(self):
        for name in udhr.fileids():
            words = list(udhr.words(name))
            self.assertTrue(words)

    def test_raw_unicode(self):
        for name in udhr.fileids():
            txt = udhr.raw(name)
            assert not isinstance(txt, bytes), name

    def test_polish_encoding(self):
        text_pl = udhr.raw("Polish-Latin2")[:164]
        text_ppl = udhr.raw("Polish_Polski-Latin2")[:164]
        expected = """POWSZECHNA DEKLARACJA PRAW CZŁOWIEKA
[Preamble]
Trzecia Sesja Ogólnego Zgromadzenia ONZ, obradująca w Paryżu, \
uchwaliła 10 grudnia 1948 roku jednomyślnie Powszechną"""

        assert text_pl == expected, "Polish-Latin2"
        assert text_ppl == expected, "Polish_Polski-Latin2"


class TestIndian(unittest.TestCase):
    def test_words(self):
        words = indian.words()[:3]
        self.assertEqual(words, ["মহিষের", "সন্তান", ":"])

    def test_tagged_words(self):
        tagged_words = indian.tagged_words()[:3]
        self.assertEqual(
            tagged_words, [("মহিষের", "NN"), ("সন্তান", "NN"), (":", "SYM")]
        )


class TestCess(unittest.TestCase):
    def test_catalan(self):
        words = cess_cat.words()[:15]
        txt = "El Tribunal_Suprem -Fpa- TS -Fpt- ha confirmat la condemna a quatre anys d' inhabilitació especial"
        self.assertEqual(words, txt.split())
        self.assertEqual(cess_cat.tagged_sents()[0][34][0], "càrrecs")

    def test_esp(self):
        words = cess_esp.words()[:15]
        txt = "El grupo estatal Electricité_de_France -Fpa- EDF -Fpt- anunció hoy , jueves , la compra del"
        self.assertEqual(words, txt.split())
        self.assertEqual(cess_esp.words()[115], "años")


class TestFloresta(unittest.TestCase):
    def test_words(self):
        words = floresta.words()[:10]
        txt = "Um revivalismo refrescante O 7_e_Meio é um ex-libris de a"
        self.assertEqual(words, txt.split())


class TestSinicaTreebank(unittest.TestCase):
    def test_sents(self):
        first_3_sents = sinica_treebank.sents()[:3]
        self.assertEqual(
            first_3_sents,
            [["一"], ["友情"], ["嘉珍", "和", "我", "住在", "同一條", "巷子"]],
        )

    def test_parsed_sents(self):
        parsed_sents = sinica_treebank.parsed_sents()[25]
        self.assertEqual(
            parsed_sents,
            Tree(
                "S",
                [
                    Tree("NP", [Tree("Nba", ["嘉珍"])]),
                    Tree("V‧地", [Tree("VA11", ["不停"]), Tree("DE", ["的"])]),
                    Tree("VA4", ["哭泣"]),
                ],
            ),
        )


class TestCoNLL2007(unittest.TestCase):
    # Reading the CoNLL 2007 Dependency Treebanks

    def test_sents(self):
        sents = conll2007.sents("esp.train")[0]
        self.assertEqual(
            sents[:6], ["El", "aumento", "del", "índice", "de", "desempleo"]
        )

    def test_parsed_sents(self):
        parsed_sents = conll2007.parsed_sents("esp.train")[0]

        self.assertEqual(
            parsed_sents.tree(),
            Tree(
                "fortaleció",
                [
                    Tree(
                        "aumento",
                        [
                            "El",
                            Tree(
                                "del",
                                [
                                    Tree(
                                        "índice",
                                        [
                                            Tree(
                                                "de",
                                                [Tree("desempleo", ["estadounidense"])],
                                            )
                                        ],
                                    )
                                ],
                            ),
                        ],
                    ),
                    "hoy",
                    "considerablemente",
                    Tree(
                        "al",
                        [
                            Tree(
                                "euro",
                                [
                                    Tree(
                                        "cotizaba",
                                        [
                                            ",",
                                            "que",
                                            Tree("a", [Tree("15.35", ["las", "GMT"])]),
                                            "se",
                                            Tree(
                                                "en",
                                                [
                                                    Tree(
                                                        "mercado",
                                                        [
                                                            "el",
                                                            Tree("de", ["divisas"]),
                                                            Tree("de", ["Fráncfort"]),
                                                        ],
                                                    )
                                                ],
                                            ),
                                            Tree("a", ["0,9452_dólares"]),
                                            Tree(
                                                "frente_a",
                                                [
                                                    ",",
                                                    Tree(
                                                        "0,9349_dólares",
                                                        [
                                                            "los",
                                                            Tree(
                                                                "de",
                                                                [
                                                                    Tree(
                                                                        "mañana",
                                                                        ["esta"],
                                                                    )
                                                                ],
                                                            ),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                        ],
                                    )
                                ],
                            )
                        ],
                    ),
                    ".",
                ],
            ),
        )


@pytest.mark.skipif(
    not ptb.fileids(),
    reason="A full installation of the Penn Treebank is not available",
)
class TestPTB(unittest.TestCase):
    def test_fileids(self):
        self.assertEqual(
            ptb.fileids()[:4],
            [
                "BROWN/CF/CF01.MRG",
                "BROWN/CF/CF02.MRG",
                "BROWN/CF/CF03.MRG",
                "BROWN/CF/CF04.MRG",
            ],
        )

    def test_words(self):
        self.assertEqual(
            ptb.words("WSJ/00/WSJ_0003.MRG")[:7],
            ["A", "form", "of", "asbestos", "once", "used", "*"],
        )

    def test_tagged_words(self):
        self.assertEqual(
            ptb.tagged_words("WSJ/00/WSJ_0003.MRG")[:3],
            [("A", "DT"), ("form", "NN"), ("of", "IN")],
        )

    def test_categories(self):
        self.assertEqual(
            ptb.categories(),
            [
                "adventure",
                "belles_lettres",
                "fiction",
                "humor",
                "lore",
                "mystery",
                "news",
                "romance",
                "science_fiction",
            ],
        )

    def test_news_fileids(self):
        self.assertEqual(
            ptb.fileids("news")[:3],
            ["WSJ/00/WSJ_0001.MRG", "WSJ/00/WSJ_0002.MRG", "WSJ/00/WSJ_0003.MRG"],
        )

    def test_category_words(self):
        self.assertEqual(
            ptb.words(categories=["humor", "fiction"])[:6],
            ["Thirty-three", "Scotty", "did", "not", "go", "back"],
        )


@pytest.mark.skip("Skipping test for mwa_ppdb.")
class TestMWAPPDB(unittest.TestCase):
    def test_fileids(self):
        self.assertEqual(
            mwa_ppdb.fileids(), ["ppdb-1.0-xxxl-lexical.extended.synonyms.uniquepairs"]
        )

    def test_entries(self):
        self.assertEqual(
            mwa_ppdb.entries()[:10],
            [
                ("10/17/01", "17/10/2001"),
                ("102,70", "102.70"),
                ("13,53", "13.53"),
                ("3.2.5.3.2.1", "3.2.5.3.2.1."),
                ("53,76", "53.76"),
                ("6.9.5", "6.9.5."),
                ("7.7.6.3", "7.7.6.3."),
                ("76,20", "76.20"),
                ("79,85", "79.85"),
                ("93,65", "93.65"),
            ],
        )

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\felix.py ===
"""
    pygments.lexers.felix
    ~~~~~~~~~~~~~~~~~~~~~

    Lexer for the Felix language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, bygroups, default, words, \
    combined
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace

__all__ = ['FelixLexer']


class FelixLexer(RegexLexer):
    """
    For Felix source code.
    """

    name = 'Felix'
    url = 'http://www.felix-lang.org'
    aliases = ['felix', 'flx']
    filenames = ['*.flx', '*.flxh']
    mimetypes = ['text/x-felix']
    version_added = '1.2'

    preproc = (
        'elif', 'else', 'endif', 'if', 'ifdef', 'ifndef',
    )

    keywords = (
        '_', '_deref', 'all', 'as',
        'assert', 'attempt', 'call', 'callback', 'case', 'caseno', 'cclass',
        'code', 'compound', 'ctypes', 'do', 'done', 'downto', 'elif', 'else',
        'endattempt', 'endcase', 'endif', 'endmatch', 'enum', 'except',
        'exceptions', 'expect', 'finally', 'for', 'forall', 'forget', 'fork',
        'functor', 'goto', 'ident', 'if', 'incomplete', 'inherit', 'instance',
        'interface', 'jump', 'lambda', 'loop', 'match', 'module', 'namespace',
        'new', 'noexpand', 'nonterm', 'obj', 'of', 'open', 'parse', 'raise',
        'regexp', 'reglex', 'regmatch', 'rename', 'return', 'the', 'then',
        'to', 'type', 'typecase', 'typedef', 'typematch', 'typeof', 'upto',
        'when', 'whilst', 'with', 'yield',
    )

    keyword_directives = (
        '_gc_pointer', '_gc_type', 'body', 'comment', 'const', 'export',
        'header', 'inline', 'lval', 'macro', 'noinline', 'noreturn',
        'package', 'private', 'pod', 'property', 'public', 'publish',
        'requires', 'todo', 'virtual', 'use',
    )

    keyword_declarations = (
        'def', 'let', 'ref', 'val', 'var',
    )

    keyword_types = (
        'unit', 'void', 'any', 'bool',
        'byte',  'offset',
        'address', 'caddress', 'cvaddress', 'vaddress',
        'tiny', 'short', 'int', 'long', 'vlong',
        'utiny', 'ushort', 'vshort', 'uint', 'ulong', 'uvlong',
        'int8', 'int16', 'int32', 'int64',
        'uint8', 'uint16', 'uint32', 'uint64',
        'float', 'double', 'ldouble',
        'complex', 'dcomplex', 'lcomplex',
        'imaginary', 'dimaginary', 'limaginary',
        'char', 'wchar', 'uchar',
        'charp', 'charcp', 'ucharp', 'ucharcp',
        'string', 'wstring', 'ustring',
        'cont',
        'array', 'varray', 'list',
        'lvalue', 'opt', 'slice',
    )

    keyword_constants = (
        'false', 'true',
    )

    operator_words = (
        'and', 'not', 'in', 'is', 'isin', 'or', 'xor',
    )

    name_builtins = (
        '_svc', 'while',
    )

    name_pseudo = (
        'root', 'self', 'this',
    )

    decimal_suffixes = '([tTsSiIlLvV]|ll|LL|([iIuU])(8|16|32|64))?'

    tokens = {
        'root': [
            include('whitespace'),

            # Keywords
            (words(('axiom', 'ctor', 'fun', 'gen', 'proc', 'reduce',
                    'union'), suffix=r'\b'),
             Keyword, 'funcname'),
            (words(('class', 'cclass', 'cstruct', 'obj', 'struct'), suffix=r'\b'),
             Keyword, 'classname'),
            (r'(instance|module|typeclass)\b', Keyword, 'modulename'),

            (words(keywords, suffix=r'\b'), Keyword),
            (words(keyword_directives, suffix=r'\b'), Name.Decorator),
            (words(keyword_declarations, suffix=r'\b'), Keyword.Declaration),
            (words(keyword_types, suffix=r'\b'), Keyword.Type),
            (words(keyword_constants, suffix=r'\b'), Keyword.Constant),

            # Operators
            include('operators'),

            # Float Literal
            # -- Hex Float
            (r'0[xX]([0-9a-fA-F_]*\.[0-9a-fA-F_]+|[0-9a-fA-F_]+)'
             r'[pP][+\-]?[0-9_]+[lLfFdD]?', Number.Float),
            # -- DecimalFloat
            (r'[0-9_]+(\.[0-9_]+[eE][+\-]?[0-9_]+|'
             r'\.[0-9_]*|[eE][+\-]?[0-9_]+)[lLfFdD]?', Number.Float),
            (r'\.(0|[1-9][0-9_]*)([eE][+\-]?[0-9_]+)?[lLfFdD]?',
             Number.Float),

            # IntegerLiteral
            # -- Binary
            (rf'0[Bb][01_]+{decimal_suffixes}', Number.Bin),
            # -- Octal
            (rf'0[0-7_]+{decimal_suffixes}', Number.Oct),
            # -- Hexadecimal
            (rf'0[xX][0-9a-fA-F_]+{decimal_suffixes}', Number.Hex),
            # -- Decimal
            (rf'(0|[1-9][0-9_]*){decimal_suffixes}', Number.Integer),

            # Strings
            ('([rR][cC]?|[cC][rR])"""', String, 'tdqs'),
            ("([rR][cC]?|[cC][rR])'''", String, 'tsqs'),
            ('([rR][cC]?|[cC][rR])"', String, 'dqs'),
            ("([rR][cC]?|[cC][rR])'", String, 'sqs'),
            ('[cCfFqQwWuU]?"""', String, combined('stringescape', 'tdqs')),
            ("[cCfFqQwWuU]?'''", String, combined('stringescape', 'tsqs')),
            ('[cCfFqQwWuU]?"', String, combined('stringescape', 'dqs')),
            ("[cCfFqQwWuU]?'", String, combined('stringescape', 'sqs')),

            # Punctuation
            (r'[\[\]{}:(),;?]', Punctuation),

            # Labels
            (r'[a-zA-Z_]\w*:>', Name.Label),

            # Identifiers
            (r'({})\b'.format('|'.join(name_builtins)), Name.Builtin),
            (r'({})\b'.format('|'.join(name_pseudo)), Name.Builtin.Pseudo),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'whitespace': [
            (r'\s+', Whitespace),

            include('comment'),

            # Preprocessor
            (r'(#)(\s*)(if)(\s+)(0)',
                bygroups(Comment.Preproc, Whitespace, Comment.Preproc,
                    Whitespace, Comment.Preproc), 'if0'),
            (r'#', Comment.Preproc, 'macro'),
        ],
        'operators': [
            (r'({})\b'.format('|'.join(operator_words)), Operator.Word),
            (r'!=|==|<<|>>|\|\||&&|[-~+/*%=<>&^|.$]', Operator),
        ],
        'comment': [
            (r'//(.*?)$', Comment.Single),
            (r'/[*]', Comment.Multiline, 'comment2'),
        ],
        'comment2': [
            (r'[^/*]', Comment.Multiline),
            (r'/[*]', Comment.Multiline, '#push'),
            (r'[*]/', Comment.Multiline, '#pop'),
            (r'[/*]', Comment.Multiline),
        ],
        'if0': [
            (r'^(\s*)(#if.*?(?<!\\))(\n)',
                bygroups(Whitespace, Comment, Whitespace), '#push'),
            (r'^(\s*)(#endif.*?(?<!\\))(\n)',
                bygroups(Whitespace, Comment, Whitespace), '#pop'),
            (r'(.*?)(\n)', bygroups(Comment, Whitespace)),
        ],
        'macro': [
            include('comment'),
            (r'(import|include)(\s+)(<[^>]*?>)',
             bygroups(Comment.Preproc, Whitespace, String), '#pop'),
            (r'(import|include)(\s+)("[^"]*?")',
             bygroups(Comment.Preproc, Whitespace, String), '#pop'),
            (r"(import|include)(\s+)('[^']*?')",
             bygroups(Comment.Preproc, Whitespace, String), '#pop'),
            (r'[^/\n]+', Comment.Preproc),
            # (r'/[*](.|\n)*?[*]/', Comment),
            # (r'//.*?\n', Comment, '#pop'),
            (r'/', Comment.Preproc),
            (r'(?<=\\)\n', Comment.Preproc),
            (r'\n', Whitespace, '#pop'),
        ],
        'funcname': [
            include('whitespace'),
            (r'[a-zA-Z_]\w*', Name.Function, '#pop'),
            # anonymous functions
            (r'(?=\()', Text, '#pop'),
        ],
        'classname': [
            include('whitespace'),
            (r'[a-zA-Z_]\w*', Name.Class, '#pop'),
            # anonymous classes
            (r'(?=\{)', Text, '#pop'),
        ],
        'modulename': [
            include('whitespace'),
            (r'\[', Punctuation, ('modulename2', 'tvarlist')),
            default('modulename2'),
        ],
        'modulename2': [
            include('whitespace'),
            (r'([a-zA-Z_]\w*)', Name.Namespace, '#pop:2'),
        ],
        'tvarlist': [
            include('whitespace'),
            include('operators'),
            (r'\[', Punctuation, '#push'),
            (r'\]', Punctuation, '#pop'),
            (r',', Punctuation),
            (r'(with|where)\b', Keyword),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'strings': [
            (r'%(\([a-zA-Z0-9]+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[E-GXc-giorsux%]', String.Interpol),
            (r'[^\\\'"%\n]+', String),
            # quotes, percents and backslashes must be parsed one at a time
            (r'[\'"\\]', String),
            # unhandled string formatting sign
            (r'%', String)
            # newlines are an error (use "nl" state)
        ],
        'nl': [
            (r'\n', String)
        ],
        'dqs': [
            (r'"', String, '#pop'),
            # included here again for raw strings
            (r'\\\\|\\"|\\\n', String.Escape),
            include('strings')
        ],
        'sqs': [
            (r"'", String, '#pop'),
            # included here again for raw strings
            (r"\\\\|\\'|\\\n", String.Escape),
            include('strings')
        ],
        'tdqs': [
            (r'"""', String, '#pop'),
            include('strings'),
            include('nl')
        ],
        'tsqs': [
            (r"'''", String, '#pop'),
            include('strings'),
            include('nl')
        ],
    }

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\platformdirs\unix.py ===
"""Unix."""

from __future__ import annotations

import os
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Iterator, NoReturn

from .api import PlatformDirsABC

if sys.platform == "win32":

    def getuid() -> NoReturn:
        msg = "should only be used on Unix"
        raise RuntimeError(msg)

else:
    from os import getuid


class Unix(PlatformDirsABC):  # noqa: PLR0904
    """
    On Unix/Linux, we follow the `XDG Basedir Spec <https://specifications.freedesktop.org/basedir-spec/basedir-spec-
    latest.html>`_.

    The spec allows overriding directories with environment variables. The examples shown are the default values,
    alongside the name of the environment variable that overrides them. Makes use of the `appname
    <platformdirs.api.PlatformDirsABC.appname>`, `version <platformdirs.api.PlatformDirsABC.version>`, `multipath
    <platformdirs.api.PlatformDirsABC.multipath>`, `opinion <platformdirs.api.PlatformDirsABC.opinion>`, `ensure_exists
    <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """
        :return: data directory tied to the user, e.g. ``~/.local/share/$appname/$version`` or
         ``$XDG_DATA_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_DATA_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.local/share")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def _site_data_dirs(self) -> list[str]:
        path = os.environ.get("XDG_DATA_DIRS", "")
        if not path.strip():
            path = f"/usr/local/share{os.pathsep}/usr/share"
        return [self._append_app_name_and_version(p) for p in path.split(os.pathsep)]

    @property
    def site_data_dir(self) -> str:
        """
        :return: data directories shared by users (if `multipath <platformdirs.api.PlatformDirsABC.multipath>` is
         enabled and ``XDG_DATA_DIRS`` is set and a multi path the response is also a multi path separated by the
         OS path separator), e.g. ``/usr/local/share/$appname/$version`` or ``/usr/share/$appname/$version``
        """
        # XDG default for $XDG_DATA_DIRS; only first, if multipath is False
        dirs = self._site_data_dirs
        if not self.multipath:
            return dirs[0]
        return os.pathsep.join(dirs)

    @property
    def user_config_dir(self) -> str:
        """
        :return: config directory tied to the user, e.g. ``~/.config/$appname/$version`` or
         ``$XDG_CONFIG_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_CONFIG_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.config")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def _site_config_dirs(self) -> list[str]:
        path = os.environ.get("XDG_CONFIG_DIRS", "")
        if not path.strip():
            path = "/etc/xdg"
        return [self._append_app_name_and_version(p) for p in path.split(os.pathsep)]

    @property
    def site_config_dir(self) -> str:
        """
        :return: config directories shared by users (if `multipath <platformdirs.api.PlatformDirsABC.multipath>`
         is enabled and ``XDG_CONFIG_DIRS`` is set and a multi path the response is also a multi path separated by
         the OS path separator), e.g. ``/etc/xdg/$appname/$version``
        """
        # XDG default for $XDG_CONFIG_DIRS only first, if multipath is False
        dirs = self._site_config_dirs
        if not self.multipath:
            return dirs[0]
        return os.pathsep.join(dirs)

    @property
    def user_cache_dir(self) -> str:
        """
        :return: cache directory tied to the user, e.g. ``~/.cache/$appname/$version`` or
         ``~/$XDG_CACHE_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_CACHE_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.cache")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users, e.g. ``/var/cache/$appname/$version``"""
        return self._append_app_name_and_version("/var/cache")

    @property
    def user_state_dir(self) -> str:
        """
        :return: state directory tied to the user, e.g. ``~/.local/state/$appname/$version`` or
         ``$XDG_STATE_HOME/$appname/$version``
        """
        path = os.environ.get("XDG_STATE_HOME", "")
        if not path.strip():
            path = os.path.expanduser("~/.local/state")  # noqa: PTH111
        return self._append_app_name_and_version(path)

    @property
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user, same as `user_state_dir` if not opinionated else ``log`` in it"""
        path = self.user_state_dir
        if self.opinion:
            path = os.path.join(path, "log")  # noqa: PTH118
            self._optionally_create_directory(path)
        return path

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user, e.g. ``~/Documents``"""
        return _get_user_media_dir("XDG_DOCUMENTS_DIR", "~/Documents")

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user, e.g. ``~/Downloads``"""
        return _get_user_media_dir("XDG_DOWNLOAD_DIR", "~/Downloads")

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user, e.g. ``~/Pictures``"""
        return _get_user_media_dir("XDG_PICTURES_DIR", "~/Pictures")

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user, e.g. ``~/Videos``"""
        return _get_user_media_dir("XDG_VIDEOS_DIR", "~/Videos")

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user, e.g. ``~/Music``"""
        return _get_user_media_dir("XDG_MUSIC_DIR", "~/Music")

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user, e.g. ``~/Desktop``"""
        return _get_user_media_dir("XDG_DESKTOP_DIR", "~/Desktop")

    @property
    def user_runtime_dir(self) -> str:
        """
        :return: runtime directory tied to the user, e.g. ``/run/user/$(id -u)/$appname/$version`` or
         ``$XDG_RUNTIME_DIR/$appname/$version``.

         For FreeBSD/OpenBSD/NetBSD, it would return ``/var/run/user/$(id -u)/$appname/$version`` if
         exists, otherwise ``/tmp/runtime-$(id -u)/$appname/$version``, if``$XDG_RUNTIME_DIR``
         is not set.
        """
        path = os.environ.get("XDG_RUNTIME_DIR", "")
        if not path.strip():
            if sys.platform.startswith(("freebsd", "openbsd", "netbsd")):
                path = f"/var/run/user/{getuid()}"
                if not Path(path).exists():
                    path = f"/tmp/runtime-{getuid()}"  # noqa: S108
            else:
                path = f"/run/user/{getuid()}"
        return self._append_app_name_and_version(path)

    @property
    def site_runtime_dir(self) -> str:
        """
        :return: runtime directory shared by users, e.g. ``/run/$appname/$version`` or \
        ``$XDG_RUNTIME_DIR/$appname/$version``.

        Note that this behaves almost exactly like `user_runtime_dir` if ``$XDG_RUNTIME_DIR`` is set, but will
        fall back to paths associated to the root user instead of a regular logged-in user if it's not set.

        If you wish to ensure that a logged-in root user path is returned e.g. ``/run/user/0``, use `user_runtime_dir`
        instead.

        For FreeBSD/OpenBSD/NetBSD, it would return ``/var/run/$appname/$version`` if ``$XDG_RUNTIME_DIR`` is not set.
        """
        path = os.environ.get("XDG_RUNTIME_DIR", "")
        if not path.strip():
            if sys.platform.startswith(("freebsd", "openbsd", "netbsd")):
                path = "/var/run"
            else:
                path = "/run"
        return self._append_app_name_and_version(path)

    @property
    def site_data_path(self) -> Path:
        """:return: data path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_data_dir)

    @property
    def site_config_path(self) -> Path:
        """:return: config path shared by the users, returns the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_config_dir)

    @property
    def site_cache_path(self) -> Path:
        """:return: cache path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_cache_dir)

    def _first_item_as_path_if_multipath(self, directory: str) -> Path:
        if self.multipath:
            # If multipath is True, the first path is returned.
            directory = directory.split(os.pathsep)[0]
        return Path(directory)

    def iter_config_dirs(self) -> Iterator[str]:
        """:yield: all user and site configuration directories."""
        yield self.user_config_dir
        yield from self._site_config_dirs

    def iter_data_dirs(self) -> Iterator[str]:
        """:yield: all user and site data directories."""
        yield self.user_data_dir
        yield from self._site_data_dirs


def _get_user_media_dir(env_var: str, fallback_tilde_path: str) -> str:
    media_dir = _get_user_dirs_folder(env_var)
    if media_dir is None:
        media_dir = os.environ.get(env_var, "").strip()
        if not media_dir:
            media_dir = os.path.expanduser(fallback_tilde_path)  # noqa: PTH111

    return media_dir


def _get_user_dirs_folder(key: str) -> str | None:
    """
    Return directory from user-dirs.dirs config file.

    See https://freedesktop.org/wiki/Software/xdg-user-dirs/.

    """
    user_dirs_config_path = Path(Unix().user_config_dir) / "user-dirs.dirs"
    if user_dirs_config_path.exists():
        parser = ConfigParser()

        with user_dirs_config_path.open() as stream:
            # Add fake section header, so ConfigParser doesn't complain
            parser.read_string(f"[top]\n{stream.read()}")

        if key not in parser["top"]:
            return None

        path = parser["top"][key].strip('"')
        # Handle relative home paths
        return path.replace("$HOME", os.path.expanduser("~"))  # noqa: PTH111

    return None


__all__ = [
    "Unix",
]

# === NexusCore/openenv\Lib\site-packages\urllib3\util\timeout.py ===
from __future__ import annotations

import time
import typing
from enum import Enum
from socket import getdefaulttimeout

from ..exceptions import TimeoutStateError

if typing.TYPE_CHECKING:
    from typing import Final


class _TYPE_DEFAULT(Enum):
    # This value should never be passed to socket.settimeout() so for safety we use a -1.
    # socket.settimout() raises a ValueError for negative values.
    token = -1


_DEFAULT_TIMEOUT: Final[_TYPE_DEFAULT] = _TYPE_DEFAULT.token

_TYPE_TIMEOUT = typing.Optional[typing.Union[float, _TYPE_DEFAULT]]


class Timeout:
    """Timeout configuration.

    Timeouts can be defined as a default for a pool:

    .. code-block:: python

        import urllib3

        timeout = urllib3.util.Timeout(connect=2.0, read=7.0)

        http = urllib3.PoolManager(timeout=timeout)

        resp = http.request("GET", "https://example.com/")

        print(resp.status)

    Or per-request (which overrides the default for the pool):

    .. code-block:: python

       response = http.request("GET", "https://example.com/", timeout=Timeout(10))

    Timeouts can be disabled by setting all the parameters to ``None``:

    .. code-block:: python

       no_timeout = Timeout(connect=None, read=None)
       response = http.request("GET", "https://example.com/", timeout=no_timeout)


    :param total:
        This combines the connect and read timeouts into one; the read timeout
        will be set to the time leftover from the connect attempt. In the
        event that both a connect timeout and a total are specified, or a read
        timeout and a total are specified, the shorter timeout will be applied.

        Defaults to None.

    :type total: int, float, or None

    :param connect:
        The maximum amount of time (in seconds) to wait for a connection
        attempt to a server to succeed. Omitting the parameter will default the
        connect timeout to the system default, probably `the global default
        timeout in socket.py
        <http://hg.python.org/cpython/file/603b4d593758/Lib/socket.py#l535>`_.
        None will set an infinite timeout for connection attempts.

    :type connect: int, float, or None

    :param read:
        The maximum amount of time (in seconds) to wait between consecutive
        read operations for a response from the server. Omitting the parameter
        will default the read timeout to the system default, probably `the
        global default timeout in socket.py
        <http://hg.python.org/cpython/file/603b4d593758/Lib/socket.py#l535>`_.
        None will set an infinite timeout.

    :type read: int, float, or None

    .. note::

        Many factors can affect the total amount of time for urllib3 to return
        an HTTP response.

        For example, Python's DNS resolver does not obey the timeout specified
        on the socket. Other factors that can affect total request time include
        high CPU load, high swap, the program running at a low priority level,
        or other behaviors.

        In addition, the read and total timeouts only measure the time between
        read operations on the socket connecting the client and the server,
        not the total amount of time for the request to return a complete
        response. For most requests, the timeout is raised because the server
        has not sent the first byte in the specified time. This is not always
        the case; if a server streams one byte every fifteen seconds, a timeout
        of 20 seconds will not trigger, even though the request will take
        several minutes to complete.
    """

    #: A sentinel object representing the default timeout value
    DEFAULT_TIMEOUT: _TYPE_TIMEOUT = _DEFAULT_TIMEOUT

    def __init__(
        self,
        total: _TYPE_TIMEOUT = None,
        connect: _TYPE_TIMEOUT = _DEFAULT_TIMEOUT,
        read: _TYPE_TIMEOUT = _DEFAULT_TIMEOUT,
    ) -> None:
        self._connect = self._validate_timeout(connect, "connect")
        self._read = self._validate_timeout(read, "read")
        self.total = self._validate_timeout(total, "total")
        self._start_connect: float | None = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(connect={self._connect!r}, read={self._read!r}, total={self.total!r})"

    # __str__ provided for backwards compatibility
    __str__ = __repr__

    @staticmethod
    def resolve_default_timeout(timeout: _TYPE_TIMEOUT) -> float | None:
        return getdefaulttimeout() if timeout is _DEFAULT_TIMEOUT else timeout

    @classmethod
    def _validate_timeout(cls, value: _TYPE_TIMEOUT, name: str) -> _TYPE_TIMEOUT:
        """Check that a timeout attribute is valid.

        :param value: The timeout value to validate
        :param name: The name of the timeout attribute to validate. This is
            used to specify in error messages.
        :return: The validated and casted version of the given value.
        :raises ValueError: If it is a numeric value less than or equal to
            zero, or the type is not an integer, float, or None.
        """
        if value is None or value is _DEFAULT_TIMEOUT:
            return value

        if isinstance(value, bool):
            raise ValueError(
                "Timeout cannot be a boolean value. It must "
                "be an int, float or None."
            )
        try:
            float(value)
        except (TypeError, ValueError):
            raise ValueError(
                "Timeout value %s was %s, but it must be an "
                "int, float or None." % (name, value)
            ) from None

        try:
            if value <= 0:
                raise ValueError(
                    "Attempted to set %s timeout to %s, but the "
                    "timeout cannot be set to a value less "
                    "than or equal to 0." % (name, value)
                )
        except TypeError:
            raise ValueError(
                "Timeout value %s was %s, but it must be an "
                "int, float or None." % (name, value)
            ) from None

        return value

    @classmethod
    def from_float(cls, timeout: _TYPE_TIMEOUT) -> Timeout:
        """Create a new Timeout from a legacy timeout value.

        The timeout value used by httplib.py sets the same timeout on the
        connect(), and recv() socket requests. This creates a :class:`Timeout`
        object that sets the individual timeouts to the ``timeout`` value
        passed to this function.

        :param timeout: The legacy timeout value.
        :type timeout: integer, float, :attr:`urllib3.util.Timeout.DEFAULT_TIMEOUT`, or None
        :return: Timeout object
        :rtype: :class:`Timeout`
        """
        return Timeout(read=timeout, connect=timeout)

    def clone(self) -> Timeout:
        """Create a copy of the timeout object

        Timeout properties are stored per-pool but each request needs a fresh
        Timeout object to ensure each one has its own start/stop configured.

        :return: a copy of the timeout object
        :rtype: :class:`Timeout`
        """
        # We can't use copy.deepcopy because that will also create a new object
        # for _GLOBAL_DEFAULT_TIMEOUT, which socket.py uses as a sentinel to
        # detect the user default.
        return Timeout(connect=self._connect, read=self._read, total=self.total)

    def start_connect(self) -> float:
        """Start the timeout clock, used during a connect() attempt

        :raises urllib3.exceptions.TimeoutStateError: if you attempt
            to start a timer that has been started already.
        """
        if self._start_connect is not None:
            raise TimeoutStateError("Timeout timer has already been started.")
        self._start_connect = time.monotonic()
        return self._start_connect

    def get_connect_duration(self) -> float:
        """Gets the time elapsed since the call to :meth:`start_connect`.

        :return: Elapsed time in seconds.
        :rtype: float
        :raises urllib3.exceptions.TimeoutStateError: if you attempt
            to get duration for a timer that hasn't been started.
        """
        if self._start_connect is None:
            raise TimeoutStateError(
                "Can't get connect duration for timer that has not started."
            )
        return time.monotonic() - self._start_connect

    @property
    def connect_timeout(self) -> _TYPE_TIMEOUT:
        """Get the value to use when setting a connection timeout.

        This will be a positive float or integer, the value None
        (never timeout), or the default system timeout.

        :return: Connect timeout.
        :rtype: int, float, :attr:`Timeout.DEFAULT_TIMEOUT` or None
        """
        if self.total is None:
            return self._connect

        if self._connect is None or self._connect is _DEFAULT_TIMEOUT:
            return self.total

        return min(self._connect, self.total)  # type: ignore[type-var]

    @property
    def read_timeout(self) -> float | None:
        """Get the value for the read timeout.

        This assumes some time has elapsed in the connection timeout and
        computes the read timeout appropriately.

        If self.total is set, the read timeout is dependent on the amount of
        time taken by the connect timeout. If the connection time has not been
        established, a :exc:`~urllib3.exceptions.TimeoutStateError` will be
        raised.

        :return: Value to use for the read timeout.
        :rtype: int, float or None
        :raises urllib3.exceptions.TimeoutStateError: If :meth:`start_connect`
            has not yet been called on this object.
        """
        if (
            self.total is not None
            and self.total is not _DEFAULT_TIMEOUT
            and self._read is not None
            and self._read is not _DEFAULT_TIMEOUT
        ):
            # In case the connect timeout has not yet been established.
            if self._start_connect is None:
                return self._read
            return max(0, min(self.total - self.get_connect_duration(), self._read))
        elif self.total is not None and self.total is not _DEFAULT_TIMEOUT:
            return max(0, self.total - self.get_connect_duration())
        else:
            return self.resolve_default_timeout(self._read)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\fields.py ===
from __future__ import absolute_import

import email.utils
import mimetypes
import re

from .packages import six


def guess_content_type(filename, default="application/octet-stream"):
    """
    Guess the "Content-Type" of a file.

    :param filename:
        The filename to guess the "Content-Type" of using :mod:`mimetypes`.
    :param default:
        If no "Content-Type" can be guessed, default to `default`.
    """
    if filename:
        return mimetypes.guess_type(filename)[0] or default
    return default


def format_header_param_rfc2231(name, value):
    """
    Helper function to format and quote a single header parameter using the
    strategy defined in RFC 2231.

    Particularly useful for header parameters which might contain
    non-ASCII values, like file names. This follows
    `RFC 2388 Section 4.4 <https://tools.ietf.org/html/rfc2388#section-4.4>`_.

    :param name:
        The name of the parameter, a string expected to be ASCII only.
    :param value:
        The value of the parameter, provided as ``bytes`` or `str``.
    :ret:
        An RFC-2231-formatted unicode string.
    """
    if isinstance(value, six.binary_type):
        value = value.decode("utf-8")

    if not any(ch in value for ch in '"\\\r\n'):
        result = u'%s="%s"' % (name, value)
        try:
            result.encode("ascii")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        else:
            return result

    if six.PY2:  # Python 2:
        value = value.encode("utf-8")

    # encode_rfc2231 accepts an encoded string and returns an ascii-encoded
    # string in Python 2 but accepts and returns unicode strings in Python 3
    value = email.utils.encode_rfc2231(value, "utf-8")
    value = "%s*=%s" % (name, value)

    if six.PY2:  # Python 2:
        value = value.decode("utf-8")

    return value


_HTML5_REPLACEMENTS = {
    u"\u0022": u"%22",
    # Replace "\" with "\\".
    u"\u005C": u"\u005C\u005C",
}

# All control characters from 0x00 to 0x1F *except* 0x1B.
_HTML5_REPLACEMENTS.update(
    {
        six.unichr(cc): u"%{:02X}".format(cc)
        for cc in range(0x00, 0x1F + 1)
        if cc not in (0x1B,)
    }
)


def _replace_multiple(value, needles_and_replacements):
    def replacer(match):
        return needles_and_replacements[match.group(0)]

    pattern = re.compile(
        r"|".join([re.escape(needle) for needle in needles_and_replacements.keys()])
    )

    result = pattern.sub(replacer, value)

    return result


def format_header_param_html5(name, value):
    """
    Helper function to format and quote a single header parameter using the
    HTML5 strategy.

    Particularly useful for header parameters which might contain
    non-ASCII values, like file names. This follows the `HTML5 Working Draft
    Section 4.10.22.7`_ and matches the behavior of curl and modern browsers.

    .. _HTML5 Working Draft Section 4.10.22.7:
        https://w3c.github.io/html/sec-forms.html#multipart-form-data

    :param name:
        The name of the parameter, a string expected to be ASCII only.
    :param value:
        The value of the parameter, provided as ``bytes`` or `str``.
    :ret:
        A unicode string, stripped of troublesome characters.
    """
    if isinstance(value, six.binary_type):
        value = value.decode("utf-8")

    value = _replace_multiple(value, _HTML5_REPLACEMENTS)

    return u'%s="%s"' % (name, value)


# For backwards-compatibility.
format_header_param = format_header_param_html5


class RequestField(object):
    """
    A data container for request body parameters.

    :param name:
        The name of this request field. Must be unicode.
    :param data:
        The data/value body.
    :param filename:
        An optional filename of the request field. Must be unicode.
    :param headers:
        An optional dict-like object of headers to initially use for the field.
    :param header_formatter:
        An optional callable that is used to encode and format the headers. By
        default, this is :func:`format_header_param_html5`.
    """

    def __init__(
        self,
        name,
        data,
        filename=None,
        headers=None,
        header_formatter=format_header_param_html5,
    ):
        self._name = name
        self._filename = filename
        self.data = data
        self.headers = {}
        if headers:
            self.headers = dict(headers)
        self.header_formatter = header_formatter

    @classmethod
    def from_tuples(cls, fieldname, value, header_formatter=format_header_param_html5):
        """
        A :class:`~urllib3.fields.RequestField` factory from old-style tuple parameters.

        Supports constructing :class:`~urllib3.fields.RequestField` from
        parameter of key/value strings AND key/filetuple. A filetuple is a
        (filename, data, MIME type) tuple where the MIME type is optional.
        For example::

            'foo': 'bar',
            'fakefile': ('foofile.txt', 'contents of foofile'),
            'realfile': ('barfile.txt', open('realfile').read()),
            'typedfile': ('bazfile.bin', open('bazfile').read(), 'image/jpeg'),
            'nonamefile': 'contents of nonamefile field',

        Field names and filenames must be unicode.
        """
        if isinstance(value, tuple):
            if len(value) == 3:
                filename, data, content_type = value
            else:
                filename, data = value
                content_type = guess_content_type(filename)
        else:
            filename = None
            content_type = None
            data = value

        request_param = cls(
            fieldname, data, filename=filename, header_formatter=header_formatter
        )
        request_param.make_multipart(content_type=content_type)

        return request_param

    def _render_part(self, name, value):
        """
        Overridable helper function to format a single header parameter. By
        default, this calls ``self.header_formatter``.

        :param name:
            The name of the parameter, a string expected to be ASCII only.
        :param value:
            The value of the parameter, provided as a unicode string.
        """

        return self.header_formatter(name, value)

    def _render_parts(self, header_parts):
        """
        Helper function to format and quote a single header.

        Useful for single headers that are composed of multiple items. E.g.,
        'Content-Disposition' fields.

        :param header_parts:
            A sequence of (k, v) tuples or a :class:`dict` of (k, v) to format
            as `k1="v1"; k2="v2"; ...`.
        """
        parts = []
        iterable = header_parts
        if isinstance(header_parts, dict):
            iterable = header_parts.items()

        for name, value in iterable:
            if value is not None:
                parts.append(self._render_part(name, value))

        return u"; ".join(parts)

    def render_headers(self):
        """
        Renders the headers for this request field.
        """
        lines = []

        sort_keys = ["Content-Disposition", "Content-Type", "Content-Location"]
        for sort_key in sort_keys:
            if self.headers.get(sort_key, False):
                lines.append(u"%s: %s" % (sort_key, self.headers[sort_key]))

        for header_name, header_value in self.headers.items():
            if header_name not in sort_keys:
                if header_value:
                    lines.append(u"%s: %s" % (header_name, header_value))

        lines.append(u"\r\n")
        return u"\r\n".join(lines)

    def make_multipart(
        self, content_disposition=None, content_type=None, content_location=None
    ):
        """
        Makes this request field into a multipart request field.

        This method overrides "Content-Disposition", "Content-Type" and
        "Content-Location" headers to the request parameter.

        :param content_type:
            The 'Content-Type' of the request body.
        :param content_location:
            The 'Content-Location' of the request body.

        """
        self.headers["Content-Disposition"] = content_disposition or u"form-data"
        self.headers["Content-Disposition"] += u"; ".join(
            [
                u"",
                self._render_parts(
                    ((u"name", self._name), (u"filename", self._filename))
                ),
            ]
        )
        self.headers["Content-Type"] = content_type
        self.headers["Content-Location"] = content_location

# === NexusCore/openenv\Lib\site-packages\aiohttp\resolver.py ===
import asyncio
import socket
import weakref
from typing import Any, Dict, Final, List, Optional, Tuple, Type, Union

from .abc import AbstractResolver, ResolveResult

__all__ = ("ThreadedResolver", "AsyncResolver", "DefaultResolver")


try:
    import aiodns

    aiodns_default = hasattr(aiodns.DNSResolver, "getaddrinfo")
except ImportError:  # pragma: no cover
    aiodns = None  # type: ignore[assignment]
    aiodns_default = False


_NUMERIC_SOCKET_FLAGS = socket.AI_NUMERICHOST | socket.AI_NUMERICSERV
_NAME_SOCKET_FLAGS = socket.NI_NUMERICHOST | socket.NI_NUMERICSERV
_AI_ADDRCONFIG = socket.AI_ADDRCONFIG
if hasattr(socket, "AI_MASK"):
    _AI_ADDRCONFIG &= socket.AI_MASK


class ThreadedResolver(AbstractResolver):
    """Threaded resolver.

    Uses an Executor for synchronous getaddrinfo() calls.
    concurrent.futures.ThreadPoolExecutor is used by default.
    """

    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._loop = loop or asyncio.get_running_loop()

    async def resolve(
        self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET
    ) -> List[ResolveResult]:
        infos = await self._loop.getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM,
            family=family,
            flags=_AI_ADDRCONFIG,
        )

        hosts: List[ResolveResult] = []
        for family, _, proto, _, address in infos:
            if family == socket.AF_INET6:
                if len(address) < 3:
                    # IPv6 is not supported by Python build,
                    # or IPv6 is not enabled in the host
                    continue
                if address[3]:
                    # This is essential for link-local IPv6 addresses.
                    # LL IPv6 is a VERY rare case. Strictly speaking, we should use
                    # getnameinfo() unconditionally, but performance makes sense.
                    resolved_host, _port = await self._loop.getnameinfo(
                        address, _NAME_SOCKET_FLAGS
                    )
                    port = int(_port)
                else:
                    resolved_host, port = address[:2]
            else:  # IPv4
                assert family == socket.AF_INET
                resolved_host, port = address  # type: ignore[misc]
            hosts.append(
                ResolveResult(
                    hostname=host,
                    host=resolved_host,
                    port=port,
                    family=family,
                    proto=proto,
                    flags=_NUMERIC_SOCKET_FLAGS,
                )
            )

        return hosts

    async def close(self) -> None:
        pass


class AsyncResolver(AbstractResolver):
    """Use the `aiodns` package to make asynchronous DNS lookups"""

    def __init__(
        self,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if aiodns is None:
            raise RuntimeError("Resolver requires aiodns library")

        self._loop = loop or asyncio.get_running_loop()
        self._manager: Optional[_DNSResolverManager] = None
        # If custom args are provided, create a dedicated resolver instance
        # This means each AsyncResolver with custom args gets its own
        # aiodns.DNSResolver instance
        if args or kwargs:
            self._resolver = aiodns.DNSResolver(*args, **kwargs)
            return
        # Use the shared resolver from the manager for default arguments
        self._manager = _DNSResolverManager()
        self._resolver = self._manager.get_resolver(self, self._loop)

        if not hasattr(self._resolver, "gethostbyname"):
            # aiodns 1.1 is not available, fallback to DNSResolver.query
            self.resolve = self._resolve_with_query  # type: ignore

    async def resolve(
        self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET
    ) -> List[ResolveResult]:
        try:
            resp = await self._resolver.getaddrinfo(
                host,
                port=port,
                type=socket.SOCK_STREAM,
                family=family,
                flags=_AI_ADDRCONFIG,
            )
        except aiodns.error.DNSError as exc:
            msg = exc.args[1] if len(exc.args) >= 1 else "DNS lookup failed"
            raise OSError(None, msg) from exc
        hosts: List[ResolveResult] = []
        for node in resp.nodes:
            address: Union[Tuple[bytes, int], Tuple[bytes, int, int, int]] = node.addr
            family = node.family
            if family == socket.AF_INET6:
                if len(address) > 3 and address[3]:
                    # This is essential for link-local IPv6 addresses.
                    # LL IPv6 is a VERY rare case. Strictly speaking, we should use
                    # getnameinfo() unconditionally, but performance makes sense.
                    result = await self._resolver.getnameinfo(
                        (address[0].decode("ascii"), *address[1:]),
                        _NAME_SOCKET_FLAGS,
                    )
                    resolved_host = result.node
                else:
                    resolved_host = address[0].decode("ascii")
                    port = address[1]
            else:  # IPv4
                assert family == socket.AF_INET
                resolved_host = address[0].decode("ascii")
                port = address[1]
            hosts.append(
                ResolveResult(
                    hostname=host,
                    host=resolved_host,
                    port=port,
                    family=family,
                    proto=0,
                    flags=_NUMERIC_SOCKET_FLAGS,
                )
            )

        if not hosts:
            raise OSError(None, "DNS lookup failed")

        return hosts

    async def _resolve_with_query(
        self, host: str, port: int = 0, family: int = socket.AF_INET
    ) -> List[Dict[str, Any]]:
        qtype: Final = "AAAA" if family == socket.AF_INET6 else "A"

        try:
            resp = await self._resolver.query(host, qtype)
        except aiodns.error.DNSError as exc:
            msg = exc.args[1] if len(exc.args) >= 1 else "DNS lookup failed"
            raise OSError(None, msg) from exc

        hosts = []
        for rr in resp:
            hosts.append(
                {
                    "hostname": host,
                    "host": rr.host,
                    "port": port,
                    "family": family,
                    "proto": 0,
                    "flags": socket.AI_NUMERICHOST,
                }
            )

        if not hosts:
            raise OSError(None, "DNS lookup failed")

        return hosts

    async def close(self) -> None:
        if self._manager:
            # Release the resolver from the manager if using the shared resolver
            self._manager.release_resolver(self, self._loop)
            self._manager = None  # Clear reference to manager
            self._resolver = None  # type: ignore[assignment] # Clear reference to resolver
            return
        # Otherwise cancel our dedicated resolver
        if self._resolver is not None:
            self._resolver.cancel()
        self._resolver = None  # type: ignore[assignment] # Clear reference


class _DNSResolverManager:
    """Manager for aiodns.DNSResolver objects.

    This class manages shared aiodns.DNSResolver instances
    with no custom arguments across different event loops.
    """

    _instance: Optional["_DNSResolverManager"] = None

    def __new__(cls) -> "_DNSResolverManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        # Use WeakKeyDictionary to allow event loops to be garbage collected
        self._loop_data: weakref.WeakKeyDictionary[
            asyncio.AbstractEventLoop,
            tuple["aiodns.DNSResolver", weakref.WeakSet["AsyncResolver"]],
        ] = weakref.WeakKeyDictionary()

    def get_resolver(
        self, client: "AsyncResolver", loop: asyncio.AbstractEventLoop
    ) -> "aiodns.DNSResolver":
        """Get or create the shared aiodns.DNSResolver instance for a specific event loop.

        Args:
            client: The AsyncResolver instance requesting the resolver.
                   This is required to track resolver usage.
            loop: The event loop to use for the resolver.
        """
        # Create a new resolver and client set for this loop if it doesn't exist
        if loop not in self._loop_data:
            resolver = aiodns.DNSResolver(loop=loop)
            client_set: weakref.WeakSet["AsyncResolver"] = weakref.WeakSet()
            self._loop_data[loop] = (resolver, client_set)
        else:
            # Get the existing resolver and client set
            resolver, client_set = self._loop_data[loop]

        # Register this client with the loop
        client_set.add(client)
        return resolver

    def release_resolver(
        self, client: "AsyncResolver", loop: asyncio.AbstractEventLoop
    ) -> None:
        """Release the resolver for an AsyncResolver client when it's closed.

        Args:
            client: The AsyncResolver instance to release.
            loop: The event loop the resolver was using.
        """
        # Remove client from its loop's tracking
        current_loop_data = self._loop_data.get(loop)
        if current_loop_data is None:
            return
        resolver, client_set = current_loop_data
        client_set.discard(client)
        # If no more clients for this loop, cancel and remove its resolver
        if not client_set:
            if resolver is not None:
                resolver.cancel()
            del self._loop_data[loop]


_DefaultType = Type[Union[AsyncResolver, ThreadedResolver]]
DefaultResolver: _DefaultType = AsyncResolver if aiodns_default else ThreadedResolver

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\fields.py ===
from __future__ import absolute_import

import email.utils
import mimetypes
import re

from .packages import six


def guess_content_type(filename, default="application/octet-stream"):
    """
    Guess the "Content-Type" of a file.

    :param filename:
        The filename to guess the "Content-Type" of using :mod:`mimetypes`.
    :param default:
        If no "Content-Type" can be guessed, default to `default`.
    """
    if filename:
        return mimetypes.guess_type(filename)[0] or default
    return default


def format_header_param_rfc2231(name, value):
    """
    Helper function to format and quote a single header parameter using the
    strategy defined in RFC 2231.

    Particularly useful for header parameters which might contain
    non-ASCII values, like file names. This follows
    `RFC 2388 Section 4.4 <https://tools.ietf.org/html/rfc2388#section-4.4>`_.

    :param name:
        The name of the parameter, a string expected to be ASCII only.
    :param value:
        The value of the parameter, provided as ``bytes`` or `str``.
    :ret:
        An RFC-2231-formatted unicode string.
    """
    if isinstance(value, six.binary_type):
        value = value.decode("utf-8")

    if not any(ch in value for ch in '"\\\r\n'):
        result = u'%s="%s"' % (name, value)
        try:
            result.encode("ascii")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        else:
            return result

    if six.PY2:  # Python 2:
        value = value.encode("utf-8")

    # encode_rfc2231 accepts an encoded string and returns an ascii-encoded
    # string in Python 2 but accepts and returns unicode strings in Python 3
    value = email.utils.encode_rfc2231(value, "utf-8")
    value = "%s*=%s" % (name, value)

    if six.PY2:  # Python 2:
        value = value.decode("utf-8")

    return value


_HTML5_REPLACEMENTS = {
    u"\u0022": u"%22",
    # Replace "\" with "\\".
    u"\u005C": u"\u005C\u005C",
}

# All control characters from 0x00 to 0x1F *except* 0x1B.
_HTML5_REPLACEMENTS.update(
    {
        six.unichr(cc): u"%{:02X}".format(cc)
        for cc in range(0x00, 0x1F + 1)
        if cc not in (0x1B,)
    }
)


def _replace_multiple(value, needles_and_replacements):
    def replacer(match):
        return needles_and_replacements[match.group(0)]

    pattern = re.compile(
        r"|".join([re.escape(needle) for needle in needles_and_replacements.keys()])
    )

    result = pattern.sub(replacer, value)

    return result


def format_header_param_html5(name, value):
    """
    Helper function to format and quote a single header parameter using the
    HTML5 strategy.

    Particularly useful for header parameters which might contain
    non-ASCII values, like file names. This follows the `HTML5 Working Draft
    Section 4.10.22.7`_ and matches the behavior of curl and modern browsers.

    .. _HTML5 Working Draft Section 4.10.22.7:
        https://w3c.github.io/html/sec-forms.html#multipart-form-data

    :param name:
        The name of the parameter, a string expected to be ASCII only.
    :param value:
        The value of the parameter, provided as ``bytes`` or `str``.
    :ret:
        A unicode string, stripped of troublesome characters.
    """
    if isinstance(value, six.binary_type):
        value = value.decode("utf-8")

    value = _replace_multiple(value, _HTML5_REPLACEMENTS)

    return u'%s="%s"' % (name, value)


# For backwards-compatibility.
format_header_param = format_header_param_html5


class RequestField(object):
    """
    A data container for request body parameters.

    :param name:
        The name of this request field. Must be unicode.
    :param data:
        The data/value body.
    :param filename:
        An optional filename of the request field. Must be unicode.
    :param headers:
        An optional dict-like object of headers to initially use for the field.
    :param header_formatter:
        An optional callable that is used to encode and format the headers. By
        default, this is :func:`format_header_param_html5`.
    """

    def __init__(
        self,
        name,
        data,
        filename=None,
        headers=None,
        header_formatter=format_header_param_html5,
    ):
        self._name = name
        self._filename = filename
        self.data = data
        self.headers = {}
        if headers:
            self.headers = dict(headers)
        self.header_formatter = header_formatter

    @classmethod
    def from_tuples(cls, fieldname, value, header_formatter=format_header_param_html5):
        """
        A :class:`~urllib3.fields.RequestField` factory from old-style tuple parameters.

        Supports constructing :class:`~urllib3.fields.RequestField` from
        parameter of key/value strings AND key/filetuple. A filetuple is a
        (filename, data, MIME type) tuple where the MIME type is optional.
        For example::

            'foo': 'bar',
            'fakefile': ('foofile.txt', 'contents of foofile'),
            'realfile': ('barfile.txt', open('realfile').read()),
            'typedfile': ('bazfile.bin', open('bazfile').read(), 'image/jpeg'),
            'nonamefile': 'contents of nonamefile field',

        Field names and filenames must be unicode.
        """
        if isinstance(value, tuple):
            if len(value) == 3:
                filename, data, content_type = value
            else:
                filename, data = value
                content_type = guess_content_type(filename)
        else:
            filename = None
            content_type = None
            data = value

        request_param = cls(
            fieldname, data, filename=filename, header_formatter=header_formatter
        )
        request_param.make_multipart(content_type=content_type)

        return request_param

    def _render_part(self, name, value):
        """
        Overridable helper function to format a single header parameter. By
        default, this calls ``self.header_formatter``.

        :param name:
            The name of the parameter, a string expected to be ASCII only.
        :param value:
            The value of the parameter, provided as a unicode string.
        """

        return self.header_formatter(name, value)

    def _render_parts(self, header_parts):
        """
        Helper function to format and quote a single header.

        Useful for single headers that are composed of multiple items. E.g.,
        'Content-Disposition' fields.

        :param header_parts:
            A sequence of (k, v) tuples or a :class:`dict` of (k, v) to format
            as `k1="v1"; k2="v2"; ...`.
        """
        parts = []
        iterable = header_parts
        if isinstance(header_parts, dict):
            iterable = header_parts.items()

        for name, value in iterable:
            if value is not None:
                parts.append(self._render_part(name, value))

        return u"; ".join(parts)

    def render_headers(self):
        """
        Renders the headers for this request field.
        """
        lines = []

        sort_keys = ["Content-Disposition", "Content-Type", "Content-Location"]
        for sort_key in sort_keys:
            if self.headers.get(sort_key, False):
                lines.append(u"%s: %s" % (sort_key, self.headers[sort_key]))

        for header_name, header_value in self.headers.items():
            if header_name not in sort_keys:
                if header_value:
                    lines.append(u"%s: %s" % (header_name, header_value))

        lines.append(u"\r\n")
        return u"\r\n".join(lines)

    def make_multipart(
        self, content_disposition=None, content_type=None, content_location=None
    ):
        """
        Makes this request field into a multipart request field.

        This method overrides "Content-Disposition", "Content-Type" and
        "Content-Location" headers to the request parameter.

        :param content_type:
            The 'Content-Type' of the request body.
        :param content_location:
            The 'Content-Location' of the request body.

        """
        self.headers["Content-Disposition"] = content_disposition or u"form-data"
        self.headers["Content-Disposition"] += u"; ".join(
            [
                u"",
                self._render_parts(
                    ((u"name", self._name), (u"filename", self._filename))
                ),
            ]
        )
        self.headers["Content-Type"] = content_type
        self.headers["Content-Location"] = content_location

# === NexusCore/openenv\Lib\site-packages\win32comext\adsi\demos\test.py ===
import sys
from collections.abc import Callable

import pythoncom
import win32api
from win32com.adsi import *

verbose_level = 0

server = ""  # Must have trailing /
local_name = win32api.GetComputerName()


def DumpRoot():
    "Dumps the root DSE"
    path = "LDAP://%srootDSE" % server
    rootdse = ADsGetObject(path)

    for item in rootdse.Get("SupportedLDAPVersion"):
        print(f"{path} supports ldap version {item}")

    attributes = ["CurrentTime", "defaultNamingContext"]
    for attr in attributes:
        val = rootdse.Get(attr)
        print(f" {attr}={val}")


###############################################
#
# Code taken from article titled:
# Reading attributeSchema and classSchema Objects
def _DumpClass(child):
    attrs = "Abstract lDAPDisplayName schemaIDGUID schemaNamingContext attributeSyntax oMSyntax"
    _DumpTheseAttributes(child, attrs.split())


def _DumpAttribute(child):
    attrs = "lDAPDisplayName schemaIDGUID adminDescription adminDisplayName rDNAttID defaultHidingValue defaultObjectCategory systemOnly defaultSecurityDescriptor"
    _DumpTheseAttributes(child, attrs.split())


def _DumpTheseAttributes(child, attrs):
    for attr in attrs:
        try:
            val = child.Get(attr)
        except pythoncom.com_error as details:
            continue
            # ###
            (hr, msg, exc, arg) = details
            if exc and exc[2]:
                msg = exc[2]
            val = f"<Error: {msg}>"
        if verbose_level >= 2:
            print(f" {child.Class}: {attr}={val}")


def DumpSchema():
    "Dumps the default DSE schema"
    # Bind to rootDSE to get the schemaNamingContext property.
    path = "LDAP://%srootDSE" % server
    rootdse = ADsGetObject(path)
    name = rootdse.Get("schemaNamingContext")

    # Bind to the actual schema container.
    path = "LDAP://" + server + name
    print("Binding to", path)
    ob = ADsGetObject(path)
    nclasses = nattr = nsub = nunk = 0

    # Enumerate the attribute and class objects in the schema container.
    for child in ob:
        # Find out if this is a class, attribute, or subSchema object.
        class_name = child.Class
        if class_name == "classSchema":
            _DumpClass(child)
            nclasses += 1
        elif class_name == "attributeSchema":
            _DumpAttribute(child)
            nattr += 1
        elif class_name == "subSchema":
            nsub += 1
        else:
            print("Unknown class:", class_name)
            nunk += 1
    if verbose_level:
        print("Processed", nclasses, "classes")
        print("Processed", nattr, "attributes")
        print("Processed", nsub, "sub-schema's")
        print("Processed", nunk, "unknown types")


def _DumpObject(ob, level=0):
    prefix = "  " * level
    print(f"{prefix}{ob.Class} object: {ob.Name}")
    # Do the directory object thing
    try:
        dir_ob = ADsGetObject(ob.ADsPath, IID_IDirectoryObject)
    except pythoncom.com_error:
        dir_ob = None
    if dir_ob is not None:
        info = dir_ob.GetObjectInformation()
        print(f"{prefix} RDN='{info.RDN}', ObjectDN='{info.ObjectDN}'")
        # Create a list of names to fetch
        names = ["distinguishedName"]
        attrs = dir_ob.GetObjectAttributes(names)
        for attr in attrs:
            for val, typ in attr.Values:
                print(f"{prefix} Attribute '{attr.AttrName}' = {val}")

    for child in ob:
        _DumpObject(child, level + 1)


def DumpAllObjects():
    "Recursively dump the entire directory!"
    path = "LDAP://%srootDSE" % server
    rootdse = ADsGetObject(path)
    name = rootdse.Get("defaultNamingContext")

    # Bind to the actual schema container.
    path = "LDAP://" + server + name
    print("Binding to", path)
    ob = ADsGetObject(path)

    # Enumerate the attribute and class objects in the schema container.
    _DumpObject(ob)


##########################################################
#
# Code taken from article:
# Example Code for Enumerating Schema Classes, Attributes, and Syntaxes

# Fill a map with VT_ datatypes, to give us better names:
vt_map = {}
for name, val in pythoncom.__dict__.items():
    if name[:3] == "VT_":
        vt_map[val] = name


def DumpSchema2():
    "Dumps the schema using an alternative technique"
    path = f"LDAP://{server}schema"
    schema = ADsGetObject(path, IID_IADsContainer)
    nclass = nprop = nsyntax = 0
    for item in schema:
        item_class = item.Class.lower()
        if item_class == "class":
            items = []
            if item.Abstract:
                items.append("Abstract")
            if item.Auxiliary:
                items.append("Auxiliary")
            # 			if item.Structural: items.append("Structural")
            desc = ", ".join(items)
            import win32com.util

            iid_name = win32com.util.IIDToInterfaceName(item.PrimaryInterface)
            if verbose_level >= 2:
                print(
                    "Class: Name={}, Flags={}, Primary Interface={}".format(
                        item.Name, desc, iid_name
                    )
                )
            nclass += 1
        elif item_class == "property":
            if item.MultiValued:
                val_type = "Multi-Valued"
            else:
                val_type = "Single-Valued"
            if verbose_level >= 2:
                print(f"Property: Name={item.Name}, {val_type}")
            nprop += 1
        elif item_class == "syntax":
            data_type = vt_map.get(item.OleAutoDataType, "<unknown type>")
            if verbose_level >= 2:
                print(f"Syntax: Name={item.Name}, Datatype = {data_type}")
            nsyntax += 1
    if verbose_level >= 1:
        print("Processed", nclass, "classes")
        print("Processed", nprop, "properties")
        print("Processed", nsyntax, "syntax items")


def DumpGC():
    "Dumps the GC: object (whatever that is!)"
    ob = ADsGetObject("GC:", IID_IADsContainer)
    for sub_ob in ob:
        print(f"GC ob: {sub_ob.Name} ({sub_ob.ADsPath})")


def DumpLocalUsers():
    "Dumps the local machine users"
    path = f"WinNT://{local_name},computer"
    ob = ADsGetObject(path, IID_IADsContainer)
    ob.put_Filter(["User", "Group"])
    for sub_ob in ob:
        print(f"User/Group: {sub_ob.Name} ({sub_ob.ADsPath})")


def DumpLocalGroups():
    "Dumps the local machine groups"
    path = f"WinNT://{local_name},computer"
    ob = ADsGetObject(path, IID_IADsContainer)

    ob.put_Filter(["Group"])
    for sub_ob in ob:
        print(f"Group: {sub_ob.Name} ({sub_ob.ADsPath})")
        # get the members
        members = sub_ob.Members()
        for member in members:
            print(f"  Group member: {member.Name} ({member.ADsPath})")


def usage(tests):
    import os

    print("Usage: %s [-s server ] [-v] [Test ...]" % os.path.basename(sys.argv[0]))
    print("  -v : Verbose - print more information")
    print("  -s : server - execute the tests against the named server")
    print("where Test is one of:")
    for t in tests:
        print(t.__name__, ":", t.__doc__)
    print()
    print("If not tests are specified, all tests are run")
    sys.exit(1)


def main():
    import getopt
    import traceback

    tests = []
    for ob in globals().values():
        if isinstance(ob, Callable) and ob.__doc__:
            tests.append(ob)
    opts, args = getopt.getopt(sys.argv[1:], "s:hv")
    for opt, val in opts:
        if opt == "-s":
            if val[-1] not in "\\/":
                val += "/"
            global server
            server = val
        if opt == "-h":
            usage(tests)
        if opt == "-v":
            global verbose_level
            verbose_level += 1

    if len(args) == 0:
        print("Running all tests - use '-h' to see command-line options...")
        dotests = tests
    else:
        dotests = []
        for arg in args:
            for t in tests:
                if t.__name__ == arg:
                    dotests.append(t)
                    break
            else:
                print("Test '%s' unknown - skipping" % arg)
    if not len(dotests):
        print("Nothing to do!")
        usage(tests)
    for test in dotests:
        try:
            test()
        except:
            print("Test %s failed" % test.__name__)
            traceback.print_exc()


if __name__ == "__main__":
    main()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\__main__.py ===
import colorsys
import io
from time import process_time

from pip._vendor.rich import box
from pip._vendor.rich.color import Color
from pip._vendor.rich.console import Console, ConsoleOptions, Group, RenderableType, RenderResult
from pip._vendor.rich.markdown import Markdown
from pip._vendor.rich.measure import Measurement
from pip._vendor.rich.pretty import Pretty
from pip._vendor.rich.segment import Segment
from pip._vendor.rich.style import Style
from pip._vendor.rich.syntax import Syntax
from pip._vendor.rich.table import Table
from pip._vendor.rich.text import Text


class ColorBox:
    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        for y in range(0, 5):
            for x in range(options.max_width):
                h = x / options.max_width
                l = 0.1 + ((y / 5) * 0.7)
                r1, g1, b1 = colorsys.hls_to_rgb(h, l, 1.0)
                r2, g2, b2 = colorsys.hls_to_rgb(h, l + 0.7 / 10, 1.0)
                bgcolor = Color.from_rgb(r1 * 255, g1 * 255, b1 * 255)
                color = Color.from_rgb(r2 * 255, g2 * 255, b2 * 255)
                yield Segment("▄", Style(color=color, bgcolor=bgcolor))
            yield Segment.line()

    def __rich_measure__(
        self, console: "Console", options: ConsoleOptions
    ) -> Measurement:
        return Measurement(1, options.max_width)


def make_test_card() -> Table:
    """Get a renderable that demonstrates a number of features."""
    table = Table.grid(padding=1, pad_edge=True)
    table.title = "Rich features"
    table.add_column("Feature", no_wrap=True, justify="center", style="bold red")
    table.add_column("Demonstration")

    color_table = Table(
        box=None,
        expand=False,
        show_header=False,
        show_edge=False,
        pad_edge=False,
    )
    color_table.add_row(
        (
            "✓ [bold green]4-bit color[/]\n"
            "✓ [bold blue]8-bit color[/]\n"
            "✓ [bold magenta]Truecolor (16.7 million)[/]\n"
            "✓ [bold yellow]Dumb terminals[/]\n"
            "✓ [bold cyan]Automatic color conversion"
        ),
        ColorBox(),
    )

    table.add_row("Colors", color_table)

    table.add_row(
        "Styles",
        "All ansi styles: [bold]bold[/], [dim]dim[/], [italic]italic[/italic], [underline]underline[/], [strike]strikethrough[/], [reverse]reverse[/], and even [blink]blink[/].",
    )

    lorem = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque in metus sed sapien ultricies pretium a at justo. Maecenas luctus velit et auctor maximus."
    lorem_table = Table.grid(padding=1, collapse_padding=True)
    lorem_table.pad_edge = False
    lorem_table.add_row(
        Text(lorem, justify="left", style="green"),
        Text(lorem, justify="center", style="yellow"),
        Text(lorem, justify="right", style="blue"),
        Text(lorem, justify="full", style="red"),
    )
    table.add_row(
        "Text",
        Group(
            Text.from_markup(
                """Word wrap text. Justify [green]left[/], [yellow]center[/], [blue]right[/] or [red]full[/].\n"""
            ),
            lorem_table,
        ),
    )

    def comparison(renderable1: RenderableType, renderable2: RenderableType) -> Table:
        table = Table(show_header=False, pad_edge=False, box=None, expand=True)
        table.add_column("1", ratio=1)
        table.add_column("2", ratio=1)
        table.add_row(renderable1, renderable2)
        return table

    table.add_row(
        "Asian\nlanguage\nsupport",
        ":flag_for_china:  该库支持中文，日文和韩文文本！\n:flag_for_japan:  ライブラリは中国語、日本語、韓国語のテキストをサポートしています\n:flag_for_south_korea:  이 라이브러리는 중국어, 일본어 및 한국어 텍스트를 지원합니다",
    )

    markup_example = (
        "[bold magenta]Rich[/] supports a simple [i]bbcode[/i]-like [b]markup[/b] for [yellow]color[/], [underline]style[/], and emoji! "
        ":+1: :apple: :ant: :bear: :baguette_bread: :bus: "
    )
    table.add_row("Markup", markup_example)

    example_table = Table(
        show_edge=False,
        show_header=True,
        expand=False,
        row_styles=["none", "dim"],
        box=box.SIMPLE,
    )
    example_table.add_column("[green]Date", style="green", no_wrap=True)
    example_table.add_column("[blue]Title", style="blue")
    example_table.add_column(
        "[cyan]Production Budget",
        style="cyan",
        justify="right",
        no_wrap=True,
    )
    example_table.add_column(
        "[magenta]Box Office",
        style="magenta",
        justify="right",
        no_wrap=True,
    )
    example_table.add_row(
        "Dec 20, 2019",
        "Star Wars: The Rise of Skywalker",
        "$275,000,000",
        "$375,126,118",
    )
    example_table.add_row(
        "May 25, 2018",
        "[b]Solo[/]: A Star Wars Story",
        "$275,000,000",
        "$393,151,347",
    )
    example_table.add_row(
        "Dec 15, 2017",
        "Star Wars Ep. VIII: The Last Jedi",
        "$262,000,000",
        "[bold]$1,332,539,889[/bold]",
    )
    example_table.add_row(
        "May 19, 1999",
        "Star Wars Ep. [b]I[/b]: [i]The phantom Menace",
        "$115,000,000",
        "$1,027,044,677",
    )

    table.add_row("Tables", example_table)

    code = '''\
def iter_last(values: Iterable[T]) -> Iterable[Tuple[bool, T]]:
    """Iterate and generate a tuple with a flag for last value."""
    iter_values = iter(values)
    try:
        previous_value = next(iter_values)
    except StopIteration:
        return
    for value in iter_values:
        yield False, previous_value
        previous_value = value
    yield True, previous_value'''

    pretty_data = {
        "foo": [
            3.1427,
            (
                "Paul Atreides",
                "Vladimir Harkonnen",
                "Thufir Hawat",
            ),
        ],
        "atomic": (False, True, None),
    }
    table.add_row(
        "Syntax\nhighlighting\n&\npretty\nprinting",
        comparison(
            Syntax(code, "python3", line_numbers=True, indent_guides=True),
            Pretty(pretty_data, indent_guides=True),
        ),
    )

    markdown_example = """\
# Markdown

Supports much of the *markdown* __syntax__!

- Headers
- Basic formatting: **bold**, *italic*, `code`
- Block quotes
- Lists, and more...
    """
    table.add_row(
        "Markdown", comparison("[cyan]" + markdown_example, Markdown(markdown_example))
    )

    table.add_row(
        "+more!",
        """Progress bars, columns, styled logging handler, tracebacks, etc...""",
    )
    return table


if __name__ == "__main__":  # pragma: no cover
    console = Console(
        file=io.StringIO(),
        force_terminal=True,
    )
    test_card = make_test_card()

    # Print once to warm cache
    start = process_time()
    console.print(test_card)
    pre_cache_taken = round((process_time() - start) * 1000.0, 1)

    console.file = io.StringIO()

    start = process_time()
    console.print(test_card)
    taken = round((process_time() - start) * 1000.0, 1)

    c = Console(record=True)
    c.print(test_card)

    print(f"rendered in {pre_cache_taken}ms (cold cache)")
    print(f"rendered in {taken}ms (warm cache)")

    from pip._vendor.rich.panel import Panel

    console = Console()

    sponsor_message = Table.grid(padding=1)
    sponsor_message.add_column(style="green", justify="right")
    sponsor_message.add_column(no_wrap=True)

    sponsor_message.add_row(
        "Textualize",
        "[u blue link=https://github.com/textualize]https://github.com/textualize",
    )
    sponsor_message.add_row(
        "Twitter",
        "[u blue link=https://twitter.com/willmcgugan]https://twitter.com/willmcgugan",
    )

    intro_message = Text.from_markup(
        """\
We hope you enjoy using Rich!

Rich is maintained with [red]:heart:[/] by [link=https://www.textualize.io]Textualize.io[/]

- Will McGugan"""
    )

    message = Table.grid(padding=2)
    message.add_column()
    message.add_column(no_wrap=True)
    message.add_row(intro_message, sponsor_message)

    console.print(
        Panel.fit(
            message,
            box=box.ROUNDED,
            padding=(1, 2),
            title="[b red]Thanks for trying out Rich!",
            border_style="bright_blue",
        ),
        justify="center",
    )

# === NexusCore/openenv\Lib\site-packages\astor\source_repr.py ===
# -*- coding: utf-8 -*-
"""
Part of the astor library for Python AST manipulation.

License: 3-clause BSD

Copyright (c) 2015 Patrick Maupin

Pretty-print source -- post-process for the decompiler

The goals of the initial cut of this engine are:

1) Do a passable, if not PEP8, job of line-wrapping.

2) Serve as an example of an interface to the decompiler
   for anybody who wants to do a better job. :)
"""


def pretty_source(source):
    """ Prettify the source.
    """

    return ''.join(split_lines(source))


def split_lines(source, maxline=79):
    """Split inputs according to lines.
       If a line is short enough, just yield it.
       Otherwise, fix it.
    """
    result = []
    extend = result.extend
    append = result.append
    line = []
    multiline = False
    count = 0
    for item in source:
        newline = type(item)('\n')
        index = item.find(newline)
        if index:
            line.append(item)
            multiline = index > 0
            count += len(item)
        else:
            if line:
                if count <= maxline or multiline:
                    extend(line)
                else:
                    wrap_line(line, maxline, result)
                count = 0
                multiline = False
                line = []
            append(item)
    return result


def count(group, slen=str.__len__):
    return sum([slen(x) for x in group])


def wrap_line(line, maxline=79, result=[], count=count):
    """ We have a line that is too long,
        so we're going to try to wrap it.
    """

    # Extract the indentation

    append = result.append
    extend = result.extend

    indentation = line[0]
    lenfirst = len(indentation)
    indent = lenfirst - len(indentation.lstrip())
    assert indent in (0, lenfirst)
    indentation = line.pop(0) if indent else ''

    # Get splittable/non-splittable groups

    dgroups = list(delimiter_groups(line))
    unsplittable = dgroups[::2]
    splittable = dgroups[1::2]

    # If the largest non-splittable group won't fit
    # on a line, try to add parentheses to the line.

    if max(count(x) for x in unsplittable) > maxline - indent:
        line = add_parens(line, maxline, indent)
        dgroups = list(delimiter_groups(line))
        unsplittable = dgroups[::2]
        splittable = dgroups[1::2]

    # Deal with the first (always unsplittable) group, and
    # then set up to deal with the remainder in pairs.

    first = unsplittable[0]
    append(indentation)
    extend(first)
    if not splittable:
        return result
    pos = indent + count(first)
    indentation += '    '
    indent += 4
    if indent >= maxline / 2:
        maxline = maxline / 2 + indent

    for sg, nsg in zip(splittable, unsplittable[1:]):

        if sg:
            # If we already have stuff on the line and even
            # the very first item won't fit, start a new line
            if pos > indent and pos + len(sg[0]) > maxline:
                append('\n')
                append(indentation)
                pos = indent

            # Dump lines out of the splittable group
            # until the entire thing fits
            csg = count(sg)
            while pos + csg > maxline:
                ready, sg = split_group(sg, pos, maxline)
                if ready[-1].endswith(' '):
                    ready[-1] = ready[-1][:-1]
                extend(ready)
                append('\n')
                append(indentation)
                pos = indent
                csg = count(sg)

            # Dump the remainder of the splittable group
            if sg:
                extend(sg)
                pos += csg

        # Dump the unsplittable group, optionally
        # preceded by a linefeed.
        cnsg = count(nsg)
        if pos > indent and pos + cnsg > maxline:
            append('\n')
            append(indentation)
            pos = indent
        extend(nsg)
        pos += cnsg


def split_group(source, pos, maxline):
    """ Split a group into two subgroups.  The
        first will be appended to the current
        line, the second will start the new line.

        Note that the first group must always
        contain at least one item.

        The original group may be destroyed.
    """
    first = []
    source.reverse()
    while source:
        tok = source.pop()
        first.append(tok)
        pos += len(tok)
        if source:
            tok = source[-1]
            allowed = (maxline + 1) if tok.endswith(' ') else (maxline - 4)
            if pos + len(tok) > allowed:
                break

    source.reverse()
    return first, source


begin_delim = set('([{')
end_delim = set(')]}')
end_delim.add('):')


def delimiter_groups(line, begin_delim=begin_delim,
                     end_delim=end_delim):
    """Split a line into alternating groups.
       The first group cannot have a line feed inserted,
       the next one can, etc.
    """
    text = []
    line = iter(line)
    while True:
        # First build and yield an unsplittable group
        for item in line:
            text.append(item)
            if item in begin_delim:
                break
        if not text:
            break
        yield text

        # Now build and yield a splittable group
        level = 0
        text = []
        for item in line:
            if item in begin_delim:
                level += 1
            elif item in end_delim:
                level -= 1
                if level < 0:
                    yield text
                    text = [item]
                    break
            text.append(item)
        else:
            assert not text, text
            break


statements = set(['del ', 'return', 'yield ', 'if ', 'while '])


def add_parens(line, maxline, indent, statements=statements, count=count):
    """Attempt to add parentheses around the line
       in order to make it splittable.
    """

    if line[0] in statements:
        index = 1
        if not line[0].endswith(' '):
            index = 2
            assert line[1] == ' '
        line.insert(index, '(')
        if line[-1] == ':':
            line.insert(-1, ')')
        else:
            line.append(')')

    # That was the easy stuff.  Now for assignments.
    groups = list(get_assign_groups(line))
    if len(groups) == 1:
        # So sad, too bad
        return line

    counts = list(count(x) for x in groups)
    didwrap = False

    # If the LHS is large, wrap it first
    if sum(counts[:-1]) >= maxline - indent - 4:
        for group in groups[:-1]:
            didwrap = False  # Only want to know about last group
            if len(group) > 1:
                group.insert(0, '(')
                group.insert(-1, ')')
                didwrap = True

    # Might not need to wrap the RHS if wrapped the LHS
    if not didwrap or counts[-1] > maxline - indent - 10:
        groups[-1].insert(0, '(')
        groups[-1].append(')')

    return [item for group in groups for item in group]


# Assignment operators
ops = list('|^&+-*/%@~') + '<< >> // **'.split() + ['']
ops = set(' %s= ' % x for x in ops)


def get_assign_groups(line, ops=ops):
    """ Split a line into groups by assignment (including
        augmented assignment)
    """
    group = []
    for item in line:
        group.append(item)
        if item in ops:
            yield group
            group = []
    yield group

# === NexusCore/openenv\Lib\site-packages\rich\__main__.py ===
import colorsys
import io
from time import process_time

from rich import box
from rich.color import Color
from rich.console import Console, ConsoleOptions, Group, RenderableType, RenderResult
from rich.markdown import Markdown
from rich.measure import Measurement
from rich.pretty import Pretty
from rich.segment import Segment
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text


class ColorBox:
    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        for y in range(0, 5):
            for x in range(options.max_width):
                h = x / options.max_width
                l = 0.1 + ((y / 5) * 0.7)
                r1, g1, b1 = colorsys.hls_to_rgb(h, l, 1.0)
                r2, g2, b2 = colorsys.hls_to_rgb(h, l + 0.7 / 10, 1.0)
                bgcolor = Color.from_rgb(r1 * 255, g1 * 255, b1 * 255)
                color = Color.from_rgb(r2 * 255, g2 * 255, b2 * 255)
                yield Segment("▄", Style(color=color, bgcolor=bgcolor))
            yield Segment.line()

    def __rich_measure__(
        self, console: "Console", options: ConsoleOptions
    ) -> Measurement:
        return Measurement(1, options.max_width)


def make_test_card() -> Table:
    """Get a renderable that demonstrates a number of features."""
    table = Table.grid(padding=1, pad_edge=True)
    table.title = "Rich features"
    table.add_column("Feature", no_wrap=True, justify="center", style="bold red")
    table.add_column("Demonstration")

    color_table = Table(
        box=None,
        expand=False,
        show_header=False,
        show_edge=False,
        pad_edge=False,
    )
    color_table.add_row(
        (
            "✓ [bold green]4-bit color[/]\n"
            "✓ [bold blue]8-bit color[/]\n"
            "✓ [bold magenta]Truecolor (16.7 million)[/]\n"
            "✓ [bold yellow]Dumb terminals[/]\n"
            "✓ [bold cyan]Automatic color conversion"
        ),
        ColorBox(),
    )

    table.add_row("Colors", color_table)

    table.add_row(
        "Styles",
        "All ansi styles: [bold]bold[/], [dim]dim[/], [italic]italic[/italic], [underline]underline[/], [strike]strikethrough[/], [reverse]reverse[/], and even [blink]blink[/].",
    )

    lorem = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque in metus sed sapien ultricies pretium a at justo. Maecenas luctus velit et auctor maximus."
    lorem_table = Table.grid(padding=1, collapse_padding=True)
    lorem_table.pad_edge = False
    lorem_table.add_row(
        Text(lorem, justify="left", style="green"),
        Text(lorem, justify="center", style="yellow"),
        Text(lorem, justify="right", style="blue"),
        Text(lorem, justify="full", style="red"),
    )
    table.add_row(
        "Text",
        Group(
            Text.from_markup(
                """Word wrap text. Justify [green]left[/], [yellow]center[/], [blue]right[/] or [red]full[/].\n"""
            ),
            lorem_table,
        ),
    )

    def comparison(renderable1: RenderableType, renderable2: RenderableType) -> Table:
        table = Table(show_header=False, pad_edge=False, box=None, expand=True)
        table.add_column("1", ratio=1)
        table.add_column("2", ratio=1)
        table.add_row(renderable1, renderable2)
        return table

    table.add_row(
        "Asian\nlanguage\nsupport",
        ":flag_for_china:  该库支持中文，日文和韩文文本！\n:flag_for_japan:  ライブラリは中国語、日本語、韓国語のテキストをサポートしています\n:flag_for_south_korea:  이 라이브러리는 중국어, 일본어 및 한국어 텍스트를 지원합니다",
    )

    markup_example = (
        "[bold magenta]Rich[/] supports a simple [i]bbcode[/i]-like [b]markup[/b] for [yellow]color[/], [underline]style[/], and emoji! "
        ":+1: :apple: :ant: :bear: :baguette_bread: :bus: "
    )
    table.add_row("Markup", markup_example)

    example_table = Table(
        show_edge=False,
        show_header=True,
        expand=False,
        row_styles=["none", "dim"],
        box=box.SIMPLE,
    )
    example_table.add_column("[green]Date", style="green", no_wrap=True)
    example_table.add_column("[blue]Title", style="blue")
    example_table.add_column(
        "[cyan]Production Budget",
        style="cyan",
        justify="right",
        no_wrap=True,
    )
    example_table.add_column(
        "[magenta]Box Office",
        style="magenta",
        justify="right",
        no_wrap=True,
    )
    example_table.add_row(
        "Dec 20, 2019",
        "Star Wars: The Rise of Skywalker",
        "$275,000,000",
        "$375,126,118",
    )
    example_table.add_row(
        "May 25, 2018",
        "[b]Solo[/]: A Star Wars Story",
        "$275,000,000",
        "$393,151,347",
    )
    example_table.add_row(
        "Dec 15, 2017",
        "Star Wars Ep. VIII: The Last Jedi",
        "$262,000,000",
        "[bold]$1,332,539,889[/bold]",
    )
    example_table.add_row(
        "May 19, 1999",
        "Star Wars Ep. [b]I[/b]: [i]The phantom Menace",
        "$115,000,000",
        "$1,027,044,677",
    )

    table.add_row("Tables", example_table)

    code = '''\
def iter_last(values: Iterable[T]) -> Iterable[Tuple[bool, T]]:
    """Iterate and generate a tuple with a flag for last value."""
    iter_values = iter(values)
    try:
        previous_value = next(iter_values)
    except StopIteration:
        return
    for value in iter_values:
        yield False, previous_value
        previous_value = value
    yield True, previous_value'''

    pretty_data = {
        "foo": [
            3.1427,
            (
                "Paul Atreides",
                "Vladimir Harkonnen",
                "Thufir Hawat",
            ),
        ],
        "atomic": (False, True, None),
    }
    table.add_row(
        "Syntax\nhighlighting\n&\npretty\nprinting",
        comparison(
            Syntax(code, "python3", line_numbers=True, indent_guides=True),
            Pretty(pretty_data, indent_guides=True),
        ),
    )

    markdown_example = """\
# Markdown

Supports much of the *markdown* __syntax__!

- Headers
- Basic formatting: **bold**, *italic*, `code`
- Block quotes
- Lists, and more...
    """
    table.add_row(
        "Markdown", comparison("[cyan]" + markdown_example, Markdown(markdown_example))
    )

    table.add_row(
        "+more!",
        """Progress bars, columns, styled logging handler, tracebacks, etc...""",
    )
    return table


if __name__ == "__main__":  # pragma: no cover
    console = Console(
        file=io.StringIO(),
        force_terminal=True,
    )
    test_card = make_test_card()

    # Print once to warm cache
    start = process_time()
    console.print(test_card)
    pre_cache_taken = round((process_time() - start) * 1000.0, 1)

    console.file = io.StringIO()

    start = process_time()
    console.print(test_card)
    taken = round((process_time() - start) * 1000.0, 1)

    c = Console(record=True)
    c.print(test_card)

    print(f"rendered in {pre_cache_taken}ms (cold cache)")
    print(f"rendered in {taken}ms (warm cache)")

    from rich.panel import Panel

    console = Console()

    sponsor_message = Table.grid(padding=1)
    sponsor_message.add_column(style="green", justify="right")
    sponsor_message.add_column(no_wrap=True)

    sponsor_message.add_row(
        "Textualize",
        "[u blue link=https://github.com/textualize]https://github.com/textualize",
    )
    sponsor_message.add_row(
        "Twitter",
        "[u blue link=https://twitter.com/willmcgugan]https://twitter.com/willmcgugan",
    )

    intro_message = Text.from_markup(
        """\
We hope you enjoy using Rich!

Rich is maintained with [red]:heart:[/] by [link=https://www.textualize.io]Textualize.io[/]

- Will McGugan"""
    )

    message = Table.grid(padding=2)
    message.add_column()
    message.add_column(no_wrap=True)
    message.add_row(intro_message, sponsor_message)

    console.print(
        Panel.fit(
            message,
            box=box.ROUNDED,
            padding=(1, 2),
            title="[b red]Thanks for trying out Rich!",
            border_style="bright_blue",
        ),
        justify="center",
    )

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_providers\_common.py ===
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from huggingface_hub import constants
from huggingface_hub.hf_api import InferenceProviderMapping
from huggingface_hub.inference._common import RequestParameters
from huggingface_hub.utils import build_hf_headers, get_token, logging


logger = logging.get_logger(__name__)


# Dev purposes only.
# If you want to try to run inference for a new model locally before it's registered on huggingface.co
# for a given Inference Provider, you can add it to the following dictionary.
HARDCODED_MODEL_INFERENCE_MAPPING: Dict[str, Dict[str, InferenceProviderMapping]] = {
    # "HF model ID" => InferenceProviderMapping object initialized with "Model ID on Inference Provider's side"
    #
    # Example:
    # "Qwen/Qwen2.5-Coder-32B-Instruct": InferenceProviderMapping(hf_model_id="Qwen/Qwen2.5-Coder-32B-Instruct",
    #                                    provider_id="Qwen2.5-Coder-32B-Instruct",
    #                                    task="conversational",
    #                                    status="live")
    "cerebras": {},
    "cohere": {},
    "fal-ai": {},
    "fireworks-ai": {},
    "groq": {},
    "hf-inference": {},
    "hyperbolic": {},
    "nebius": {},
    "nscale": {},
    "replicate": {},
    "sambanova": {},
    "together": {},
}


def filter_none(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


class TaskProviderHelper:
    """Base class for task-specific provider helpers."""

    def __init__(self, provider: str, base_url: str, task: str) -> None:
        self.provider = provider
        self.task = task
        self.base_url = base_url

    def prepare_request(
        self,
        *,
        inputs: Any,
        parameters: Dict[str, Any],
        headers: Dict,
        model: Optional[str],
        api_key: Optional[str],
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> RequestParameters:
        """
        Prepare the request to be sent to the provider.

        Each step (api_key, model, headers, url, payload) can be customized in subclasses.
        """
        # api_key from user, or local token, or raise error
        api_key = self._prepare_api_key(api_key)

        # mapped model from HF model ID
        provider_mapping_info = self._prepare_mapping_info(model)

        # default HF headers + user headers (to customize in subclasses)
        headers = self._prepare_headers(headers, api_key)

        # routed URL if HF token, or direct URL (to customize in '_prepare_route' in subclasses)
        url = self._prepare_url(api_key, provider_mapping_info.provider_id)

        # prepare payload (to customize in subclasses)
        payload = self._prepare_payload_as_dict(inputs, parameters, provider_mapping_info=provider_mapping_info)
        if payload is not None:
            payload = recursive_merge(payload, extra_payload or {})

        # body data (to customize in subclasses)
        data = self._prepare_payload_as_bytes(inputs, parameters, provider_mapping_info, extra_payload)

        # check if both payload and data are set and return
        if payload is not None and data is not None:
            raise ValueError("Both payload and data cannot be set in the same request.")
        if payload is None and data is None:
            raise ValueError("Either payload or data must be set in the request.")
        return RequestParameters(
            url=url, task=self.task, model=provider_mapping_info.provider_id, json=payload, data=data, headers=headers
        )

    def get_response(
        self,
        response: Union[bytes, Dict],
        request_params: Optional[RequestParameters] = None,
    ) -> Any:
        """
        Return the response in the expected format.

        Override this method in subclasses for customized response handling."""
        return response

    def _prepare_api_key(self, api_key: Optional[str]) -> str:
        """Return the API key to use for the request.

        Usually not overwritten in subclasses."""
        if api_key is None:
            api_key = get_token()
        if api_key is None:
            raise ValueError(
                f"You must provide an api_key to work with {self.provider} API or log in with `huggingface-cli login`."
            )
        return api_key

    def _prepare_mapping_info(self, model: Optional[str]) -> InferenceProviderMapping:
        """Return the mapped model ID to use for the request.

        Usually not overwritten in subclasses."""
        if model is None:
            raise ValueError(f"Please provide an HF model ID supported by {self.provider}.")

        # hardcoded mapping for local testing
        if HARDCODED_MODEL_INFERENCE_MAPPING.get(self.provider, {}).get(model):
            return HARDCODED_MODEL_INFERENCE_MAPPING[self.provider][model]

        provider_mapping = None
        for mapping in _fetch_inference_provider_mapping(model):
            if mapping.provider == self.provider:
                provider_mapping = mapping
                break

        if provider_mapping is None:
            raise ValueError(f"Model {model} is not supported by provider {self.provider}.")

        if provider_mapping.task != self.task:
            raise ValueError(
                f"Model {model} is not supported for task {self.task} and provider {self.provider}. "
                f"Supported task: {provider_mapping.task}."
            )

        if provider_mapping.status == "staging":
            logger.warning(
                f"Model {model} is in staging mode for provider {self.provider}. Meant for test purposes only."
            )
        if provider_mapping.status == "error":
            logger.warning(
                f"Our latest automated health check on model '{model}' for provider '{self.provider}' did not complete successfully.  "
                "Inference call might fail."
            )
        return provider_mapping

    def _prepare_headers(self, headers: Dict, api_key: str) -> Dict:
        """Return the headers to use for the request.

        Override this method in subclasses for customized headers.
        """
        return {**build_hf_headers(token=api_key), **headers}

    def _prepare_url(self, api_key: str, mapped_model: str) -> str:
        """Return the URL to use for the request.

        Usually not overwritten in subclasses."""
        base_url = self._prepare_base_url(api_key)
        route = self._prepare_route(mapped_model, api_key)
        return f"{base_url.rstrip('/')}/{route.lstrip('/')}"

    def _prepare_base_url(self, api_key: str) -> str:
        """Return the base URL to use for the request.

        Usually not overwritten in subclasses."""
        # Route to the proxy if the api_key is a HF TOKEN
        if api_key.startswith("hf_"):
            logger.info(f"Calling '{self.provider}' provider through Hugging Face router.")
            return constants.INFERENCE_PROXY_TEMPLATE.format(provider=self.provider)
        else:
            logger.info(f"Calling '{self.provider}' provider directly.")
            return self.base_url

    def _prepare_route(self, mapped_model: str, api_key: str) -> str:
        """Return the route to use for the request.

        Override this method in subclasses for customized routes.
        """
        return ""

    def _prepare_payload_as_dict(
        self, inputs: Any, parameters: Dict, provider_mapping_info: InferenceProviderMapping
    ) -> Optional[Dict]:
        """Return the payload to use for the request, as a dict.

        Override this method in subclasses for customized payloads.
        Only one of `_prepare_payload_as_dict` and `_prepare_payload_as_bytes` should return a value.
        """
        return None

    def _prepare_payload_as_bytes(
        self,
        inputs: Any,
        parameters: Dict,
        provider_mapping_info: InferenceProviderMapping,
        extra_payload: Optional[Dict],
    ) -> Optional[bytes]:
        """Return the body to use for the request, as bytes.

        Override this method in subclasses for customized body data.
        Only one of `_prepare_payload_as_dict` and `_prepare_payload_as_bytes` should return a value.
        """
        return None


class BaseConversationalTask(TaskProviderHelper):
    """
    Base class for conversational (chat completion) tasks.
    The schema follows the OpenAI API format defined here: https://platform.openai.com/docs/api-reference/chat
    """

    def __init__(self, provider: str, base_url: str):
        super().__init__(provider=provider, base_url=base_url, task="conversational")

    def _prepare_route(self, mapped_model: str, api_key: str) -> str:
        return "/v1/chat/completions"

    def _prepare_payload_as_dict(
        self, inputs: Any, parameters: Dict, provider_mapping_info: InferenceProviderMapping
    ) -> Optional[Dict]:
        return {"messages": inputs, **filter_none(parameters), "model": provider_mapping_info.provider_id}


class BaseTextGenerationTask(TaskProviderHelper):
    """
    Base class for text-generation (completion) tasks.
    The schema follows the OpenAI API format defined here: https://platform.openai.com/docs/api-reference/completions
    """

    def __init__(self, provider: str, base_url: str):
        super().__init__(provider=provider, base_url=base_url, task="text-generation")

    def _prepare_route(self, mapped_model: str, api_key: str) -> str:
        return "/v1/completions"

    def _prepare_payload_as_dict(
        self, inputs: Any, parameters: Dict, provider_mapping_info: InferenceProviderMapping
    ) -> Optional[Dict]:
        return {"prompt": inputs, **filter_none(parameters), "model": provider_mapping_info.provider_id}


@lru_cache(maxsize=None)
def _fetch_inference_provider_mapping(model: str) -> List["InferenceProviderMapping"]:
    """
    Fetch provider mappings for a model from the Hub.
    """
    from huggingface_hub.hf_api import HfApi

    info = HfApi().model_info(model, expand=["inferenceProviderMapping"])
    provider_mapping = info.inference_provider_mapping
    if provider_mapping is None:
        raise ValueError(f"No provider mapping found for model {model}")
    return provider_mapping


def recursive_merge(dict1: Dict, dict2: Dict) -> Dict:
    return {
        **dict1,
        **{
            key: recursive_merge(dict1[key], value)
            if (key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict))
            else value
            for key, value in dict2.items()
        },
    }

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\chunked.py ===
# Natural Language Toolkit: Chunked Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A reader for corpora that contain chunked (and optionally tagged)
documents.
"""

import codecs
import os.path

import nltk
from nltk.chunk import tagstr2tree
from nltk.corpus.reader.api import *
from nltk.corpus.reader.bracket_parse import BracketParseCorpusReader
from nltk.corpus.reader.util import *
from nltk.tokenize import *
from nltk.tree import Tree


class ChunkedCorpusReader(CorpusReader):
    """
    Reader for chunked (and optionally tagged) corpora.  Paragraphs
    are split using a block reader.  They are then tokenized into
    sentences using a sentence tokenizer.  Finally, these sentences
    are parsed into chunk trees using a string-to-chunktree conversion
    function.  Each of these steps can be performed using a default
    function or a custom function.  By default, paragraphs are split
    on blank lines; sentences are listed one per line; and sentences
    are parsed into chunk trees using ``nltk.chunk.tagstr2tree``.
    """

    def __init__(
        self,
        root,
        fileids,
        extension="",
        str2chunktree=tagstr2tree,
        sent_tokenizer=RegexpTokenizer("\n", gaps=True),
        para_block_reader=read_blankline_block,
        encoding="utf8",
        tagset=None,
    ):
        """
        :param root: The root directory for this corpus.
        :param fileids: A list or regexp specifying the fileids in this corpus.
        """
        CorpusReader.__init__(self, root, fileids, encoding)
        self._cv_args = (str2chunktree, sent_tokenizer, para_block_reader, tagset)
        """Arguments for corpus views generated by this corpus: a tuple
        (str2chunktree, sent_tokenizer, para_block_tokenizer)"""

    def words(self, fileids=None):
        """
        :return: the given file(s) as a list of words
            and punctuation symbols.
        :rtype: list(str)
        """
        return concat(
            [
                ChunkedCorpusView(f, enc, 0, 0, 0, 0, *self._cv_args)
                for (f, enc) in self.abspaths(fileids, True)
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
                ChunkedCorpusView(f, enc, 0, 1, 0, 0, *self._cv_args)
                for (f, enc) in self.abspaths(fileids, True)
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
                ChunkedCorpusView(f, enc, 0, 1, 1, 0, *self._cv_args)
                for (f, enc) in self.abspaths(fileids, True)
            ]
        )

    def tagged_words(self, fileids=None, tagset=None):
        """
        :return: the given file(s) as a list of tagged
            words and punctuation symbols, encoded as tuples
            ``(word,tag)``.
        :rtype: list(tuple(str,str))
        """
        return concat(
            [
                ChunkedCorpusView(
                    f, enc, 1, 0, 0, 0, *self._cv_args, target_tagset=tagset
                )
                for (f, enc) in self.abspaths(fileids, True)
            ]
        )

    def tagged_sents(self, fileids=None, tagset=None):
        """
        :return: the given file(s) as a list of
            sentences, each encoded as a list of ``(word,tag)`` tuples.

        :rtype: list(list(tuple(str,str)))
        """
        return concat(
            [
                ChunkedCorpusView(
                    f, enc, 1, 1, 0, 0, *self._cv_args, target_tagset=tagset
                )
                for (f, enc) in self.abspaths(fileids, True)
            ]
        )

    def tagged_paras(self, fileids=None, tagset=None):
        """
        :return: the given file(s) as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of ``(word,tag)`` tuples.
        :rtype: list(list(list(tuple(str,str))))
        """
        return concat(
            [
                ChunkedCorpusView(
                    f, enc, 1, 1, 1, 0, *self._cv_args, target_tagset=tagset
                )
                for (f, enc) in self.abspaths(fileids, True)
            ]
        )

    def chunked_words(self, fileids=None, tagset=None):
        """
        :return: the given file(s) as a list of tagged
            words and chunks.  Words are encoded as ``(word, tag)``
            tuples (if the corpus has tags) or word strings (if the
            corpus has no tags).  Chunks are encoded as depth-one
            trees over ``(word,tag)`` tuples or word strings.
        :rtype: list(tuple(str,str) and Tree)
        """
        return concat(
            [
                ChunkedCorpusView(
                    f, enc, 1, 0, 0, 1, *self._cv_args, target_tagset=tagset
                )
                for (f, enc) in self.abspaths(fileids, True)
            ]
        )

    def chunked_sents(self, fileids=None, tagset=None):
        """
        :return: the given file(s) as a list of
            sentences, each encoded as a shallow Tree.  The leaves
            of these trees are encoded as ``(word, tag)`` tuples (if
            the corpus has tags) or word strings (if the corpus has no
            tags).
        :rtype: list(Tree)
        """
        return concat(
            [
                ChunkedCorpusView(
                    f, enc, 1, 1, 0, 1, *self._cv_args, target_tagset=tagset
                )
                for (f, enc) in self.abspaths(fileids, True)
            ]
        )

    def chunked_paras(self, fileids=None, tagset=None):
        """
        :return: the given file(s) as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as a shallow Tree.  The leaves of these
            trees are encoded as ``(word, tag)`` tuples (if the corpus
            has tags) or word strings (if the corpus has no tags).
        :rtype: list(list(Tree))
        """
        return concat(
            [
                ChunkedCorpusView(
                    f, enc, 1, 1, 1, 1, *self._cv_args, target_tagset=tagset
                )
                for (f, enc) in self.abspaths(fileids, True)
            ]
        )

    def _read_block(self, stream):
        return [tagstr2tree(t) for t in read_blankline_block(stream)]


class ChunkedCorpusView(StreamBackedCorpusView):
    def __init__(
        self,
        fileid,
        encoding,
        tagged,
        group_by_sent,
        group_by_para,
        chunked,
        str2chunktree,
        sent_tokenizer,
        para_block_reader,
        source_tagset=None,
        target_tagset=None,
    ):
        StreamBackedCorpusView.__init__(self, fileid, encoding=encoding)
        self._tagged = tagged
        self._group_by_sent = group_by_sent
        self._group_by_para = group_by_para
        self._chunked = chunked
        self._str2chunktree = str2chunktree
        self._sent_tokenizer = sent_tokenizer
        self._para_block_reader = para_block_reader
        self._source_tagset = source_tagset
        self._target_tagset = target_tagset

    def read_block(self, stream):
        block = []
        for para_str in self._para_block_reader(stream):
            para = []
            for sent_str in self._sent_tokenizer.tokenize(para_str):
                sent = self._str2chunktree(
                    sent_str,
                    source_tagset=self._source_tagset,
                    target_tagset=self._target_tagset,
                )

                # If requested, throw away the tags.
                if not self._tagged:
                    sent = self._untag(sent)

                # If requested, throw away the chunks.
                if not self._chunked:
                    sent = sent.leaves()

                # Add the sentence to `para`.
                if self._group_by_sent:
                    para.append(sent)
                else:
                    para.extend(sent)

            # Add the paragraph to `block`.
            if self._group_by_para:
                block.append(para)
            else:
                block.extend(para)

        # Return the block
        return block

    def _untag(self, tree):
        for i, child in enumerate(tree):
            if isinstance(child, Tree):
                self._untag(child)
            elif isinstance(child, tuple):
                tree[i] = child[0]
            else:
                raise ValueError("expected child to be Tree or tuple")
        return tree

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\__main__.py ===
import colorsys
import io
from time import process_time

from pip._vendor.rich import box
from pip._vendor.rich.color import Color
from pip._vendor.rich.console import Console, ConsoleOptions, Group, RenderableType, RenderResult
from pip._vendor.rich.markdown import Markdown
from pip._vendor.rich.measure import Measurement
from pip._vendor.rich.pretty import Pretty
from pip._vendor.rich.segment import Segment
from pip._vendor.rich.style import Style
from pip._vendor.rich.syntax import Syntax
from pip._vendor.rich.table import Table
from pip._vendor.rich.text import Text


class ColorBox:
    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        for y in range(0, 5):
            for x in range(options.max_width):
                h = x / options.max_width
                l = 0.1 + ((y / 5) * 0.7)
                r1, g1, b1 = colorsys.hls_to_rgb(h, l, 1.0)
                r2, g2, b2 = colorsys.hls_to_rgb(h, l + 0.7 / 10, 1.0)
                bgcolor = Color.from_rgb(r1 * 255, g1 * 255, b1 * 255)
                color = Color.from_rgb(r2 * 255, g2 * 255, b2 * 255)
                yield Segment("▄", Style(color=color, bgcolor=bgcolor))
            yield Segment.line()

    def __rich_measure__(
        self, console: "Console", options: ConsoleOptions
    ) -> Measurement:
        return Measurement(1, options.max_width)


def make_test_card() -> Table:
    """Get a renderable that demonstrates a number of features."""
    table = Table.grid(padding=1, pad_edge=True)
    table.title = "Rich features"
    table.add_column("Feature", no_wrap=True, justify="center", style="bold red")
    table.add_column("Demonstration")

    color_table = Table(
        box=None,
        expand=False,
        show_header=False,
        show_edge=False,
        pad_edge=False,
    )
    color_table.add_row(
        (
            "✓ [bold green]4-bit color[/]\n"
            "✓ [bold blue]8-bit color[/]\n"
            "✓ [bold magenta]Truecolor (16.7 million)[/]\n"
            "✓ [bold yellow]Dumb terminals[/]\n"
            "✓ [bold cyan]Automatic color conversion"
        ),
        ColorBox(),
    )

    table.add_row("Colors", color_table)

    table.add_row(
        "Styles",
        "All ansi styles: [bold]bold[/], [dim]dim[/], [italic]italic[/italic], [underline]underline[/], [strike]strikethrough[/], [reverse]reverse[/], and even [blink]blink[/].",
    )

    lorem = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque in metus sed sapien ultricies pretium a at justo. Maecenas luctus velit et auctor maximus."
    lorem_table = Table.grid(padding=1, collapse_padding=True)
    lorem_table.pad_edge = False
    lorem_table.add_row(
        Text(lorem, justify="left", style="green"),
        Text(lorem, justify="center", style="yellow"),
        Text(lorem, justify="right", style="blue"),
        Text(lorem, justify="full", style="red"),
    )
    table.add_row(
        "Text",
        Group(
            Text.from_markup(
                """Word wrap text. Justify [green]left[/], [yellow]center[/], [blue]right[/] or [red]full[/].\n"""
            ),
            lorem_table,
        ),
    )

    def comparison(renderable1: RenderableType, renderable2: RenderableType) -> Table:
        table = Table(show_header=False, pad_edge=False, box=None, expand=True)
        table.add_column("1", ratio=1)
        table.add_column("2", ratio=1)
        table.add_row(renderable1, renderable2)
        return table

    table.add_row(
        "Asian\nlanguage\nsupport",
        ":flag_for_china:  该库支持中文，日文和韩文文本！\n:flag_for_japan:  ライブラリは中国語、日本語、韓国語のテキストをサポートしています\n:flag_for_south_korea:  이 라이브러리는 중국어, 일본어 및 한국어 텍스트를 지원합니다",
    )

    markup_example = (
        "[bold magenta]Rich[/] supports a simple [i]bbcode[/i]-like [b]markup[/b] for [yellow]color[/], [underline]style[/], and emoji! "
        ":+1: :apple: :ant: :bear: :baguette_bread: :bus: "
    )
    table.add_row("Markup", markup_example)

    example_table = Table(
        show_edge=False,
        show_header=True,
        expand=False,
        row_styles=["none", "dim"],
        box=box.SIMPLE,
    )
    example_table.add_column("[green]Date", style="green", no_wrap=True)
    example_table.add_column("[blue]Title", style="blue")
    example_table.add_column(
        "[cyan]Production Budget",
        style="cyan",
        justify="right",
        no_wrap=True,
    )
    example_table.add_column(
        "[magenta]Box Office",
        style="magenta",
        justify="right",
        no_wrap=True,
    )
    example_table.add_row(
        "Dec 20, 2019",
        "Star Wars: The Rise of Skywalker",
        "$275,000,000",
        "$375,126,118",
    )
    example_table.add_row(
        "May 25, 2018",
        "[b]Solo[/]: A Star Wars Story",
        "$275,000,000",
        "$393,151,347",
    )
    example_table.add_row(
        "Dec 15, 2017",
        "Star Wars Ep. VIII: The Last Jedi",
        "$262,000,000",
        "[bold]$1,332,539,889[/bold]",
    )
    example_table.add_row(
        "May 19, 1999",
        "Star Wars Ep. [b]I[/b]: [i]The phantom Menace",
        "$115,000,000",
        "$1,027,044,677",
    )

    table.add_row("Tables", example_table)

    code = '''\
def iter_last(values: Iterable[T]) -> Iterable[Tuple[bool, T]]:
    """Iterate and generate a tuple with a flag for last value."""
    iter_values = iter(values)
    try:
        previous_value = next(iter_values)
    except StopIteration:
        return
    for value in iter_values:
        yield False, previous_value
        previous_value = value
    yield True, previous_value'''

    pretty_data = {
        "foo": [
            3.1427,
            (
                "Paul Atreides",
                "Vladimir Harkonnen",
                "Thufir Hawat",
            ),
        ],
        "atomic": (False, True, None),
    }
    table.add_row(
        "Syntax\nhighlighting\n&\npretty\nprinting",
        comparison(
            Syntax(code, "python3", line_numbers=True, indent_guides=True),
            Pretty(pretty_data, indent_guides=True),
        ),
    )

    markdown_example = """\
# Markdown

Supports much of the *markdown* __syntax__!

- Headers
- Basic formatting: **bold**, *italic*, `code`
- Block quotes
- Lists, and more...
    """
    table.add_row(
        "Markdown", comparison("[cyan]" + markdown_example, Markdown(markdown_example))
    )

    table.add_row(
        "+more!",
        """Progress bars, columns, styled logging handler, tracebacks, etc...""",
    )
    return table


if __name__ == "__main__":  # pragma: no cover
    console = Console(
        file=io.StringIO(),
        force_terminal=True,
    )
    test_card = make_test_card()

    # Print once to warm cache
    start = process_time()
    console.print(test_card)
    pre_cache_taken = round((process_time() - start) * 1000.0, 1)

    console.file = io.StringIO()

    start = process_time()
    console.print(test_card)
    taken = round((process_time() - start) * 1000.0, 1)

    c = Console(record=True)
    c.print(test_card)

    print(f"rendered in {pre_cache_taken}ms (cold cache)")
    print(f"rendered in {taken}ms (warm cache)")

    from pip._vendor.rich.panel import Panel

    console = Console()

    sponsor_message = Table.grid(padding=1)
    sponsor_message.add_column(style="green", justify="right")
    sponsor_message.add_column(no_wrap=True)

    sponsor_message.add_row(
        "Textualize",
        "[u blue link=https://github.com/textualize]https://github.com/textualize",
    )
    sponsor_message.add_row(
        "Twitter",
        "[u blue link=https://twitter.com/willmcgugan]https://twitter.com/willmcgugan",
    )

    intro_message = Text.from_markup(
        """\
We hope you enjoy using Rich!

Rich is maintained with [red]:heart:[/] by [link=https://www.textualize.io]Textualize.io[/]

- Will McGugan"""
    )

    message = Table.grid(padding=2)
    message.add_column()
    message.add_column(no_wrap=True)
    message.add_row(intro_message, sponsor_message)

    console.print(
        Panel.fit(
            message,
            box=box.ROUNDED,
            padding=(1, 2),
            title="[b red]Thanks for trying out Rich!",
            border_style="bright_blue",
        ),
        justify="center",
    )

# === NexusCore/openenv\Lib\site-packages\win32\test\test_win32api.py ===
# General test module for win32api - please add some :)

import datetime
import os
import sys
import tempfile
import time
import unittest

import win32api
import win32con
import win32event
import winerror
from pywin32_testutil import TestSkipped


class TestError(Exception):
    pass


class CurrentUserTestCase(unittest.TestCase):
    def testGetCurrentUser(self):
        domain = win32api.GetDomainName()
        if domain == "NT AUTHORITY":
            # Running as a service account, so the comparison will fail
            raise TestSkipped("running as service account")
        name = f"{domain}\\{win32api.GetUserName()}"
        self.assertEqual(name, win32api.GetUserNameEx(win32api.NameSamCompatible))


class TestTime(unittest.TestCase):
    def testTimezone(self):
        # GetTimeZoneInformation
        rc, tzinfo = win32api.GetTimeZoneInformation()
        if rc == win32con.TIME_ZONE_ID_DAYLIGHT:
            tz_str = tzinfo[4]
            tz_time = tzinfo[5]
        else:
            tz_str = tzinfo[1]
            tz_time = tzinfo[2]
        # for the sake of code exercise but don't output
        tz_str.encode()
        if not isinstance(tz_time, datetime.datetime) and not isinstance(
            tz_time, tuple
        ):
            tz_time.Format()

    def TestDateFormat(self):
        DATE_LONGDATE = 2
        date_flags = DATE_LONGDATE
        win32api.GetDateFormat(0, date_flags, None)
        win32api.GetDateFormat(0, date_flags, 0)
        win32api.GetDateFormat(0, date_flags, datetime.datetime.now())
        win32api.GetDateFormat(0, date_flags, time.time())

    def TestTimeFormat(self):
        win32api.GetTimeFormat(0, 0, None)
        win32api.GetTimeFormat(0, 0, 0)
        win32api.GetTimeFormat(0, 0, datetime.datetime.now())
        win32api.GetTimeFormat(0, 0, time.time())


class Registry(unittest.TestCase):
    key_name = r"PythonTestHarness\Whatever"

    def test1(self):
        # This used to leave a stale exception behind.
        def reg_operation():
            hkey = win32api.RegCreateKey(win32con.HKEY_CURRENT_USER, self.key_name)
            raise TestError

        # do the test
        try:
            try:
                try:
                    reg_operation()
                except:
                    raise TestError  # Force a TestError
            finally:
                win32api.RegDeleteKey(win32con.HKEY_CURRENT_USER, self.key_name)
        except TestError:
            pass

    def testValues(self):
        key_name = r"PythonTestHarness\win32api"
        ## tuples containing value name, value type, data
        values = (
            (None, win32con.REG_SZ, "This is default unnamed value"),
            ("REG_SZ", win32con.REG_SZ, "REG_SZ text data"),
            ("REG_EXPAND_SZ", win32con.REG_EXPAND_SZ, "%systemdir%"),
            ## REG_MULTI_SZ value needs to be a list since strings are returned as a list
            (
                "REG_MULTI_SZ",
                win32con.REG_MULTI_SZ,
                ["string 1", "string 2", "string 3", "string 4"],
            ),
            ("REG_MULTI_SZ_empty", win32con.REG_MULTI_SZ, []),
            ("REG_DWORD", win32con.REG_DWORD, 666),
            ("REG_QWORD_INT", win32con.REG_QWORD, 99),
            ("REG_QWORD", win32con.REG_QWORD, 2**33),
            (
                "REG_BINARY",
                win32con.REG_BINARY,
                b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x01\x00",
            ),
        )

        hkey = win32api.RegCreateKey(win32con.HKEY_CURRENT_USER, key_name)
        for value_name, reg_type, data in values:
            win32api.RegSetValueEx(hkey, value_name, None, reg_type, data)

        for value_name, orig_type, orig_data in values:
            data, typ = win32api.RegQueryValueEx(hkey, value_name)
            self.assertEqual(typ, orig_type)
            self.assertEqual(data, orig_data)

    def testNotifyChange(self):
        def change():
            hkey = win32api.RegCreateKey(win32con.HKEY_CURRENT_USER, self.key_name)
            try:
                win32api.RegSetValue(hkey, None, win32con.REG_SZ, "foo")
            finally:
                win32api.RegDeleteKey(win32con.HKEY_CURRENT_USER, self.key_name)

        evt = win32event.CreateEvent(None, 0, 0, None)
        ## REG_NOTIFY_CHANGE_LAST_SET - values
        ## REG_CHANGE_NOTIFY_NAME - keys
        ## REG_NOTIFY_CHANGE_SECURITY - security descriptor
        ## REG_NOTIFY_CHANGE_ATTRIBUTES
        win32api.RegNotifyChangeKeyValue(
            win32con.HKEY_CURRENT_USER,
            1,
            win32api.REG_NOTIFY_CHANGE_LAST_SET,
            evt,
            True,
        )
        ret_code = win32event.WaitForSingleObject(evt, 0)
        # Should be no change.
        self.assertTrue(ret_code == win32con.WAIT_TIMEOUT)
        change()
        # Our event should now be in a signalled state.
        ret_code = win32event.WaitForSingleObject(evt, 0)
        self.assertTrue(ret_code == win32con.WAIT_OBJECT_0)


class FileNames(unittest.TestCase):
    def testShortLongPathNames(self):
        try:
            me = __file__
        except NameError:
            me = sys.argv[0]
        fname = os.path.abspath(me).lower()
        short_name = win32api.GetShortPathName(fname).lower()
        long_name = win32api.GetLongPathName(short_name).lower()
        self.assertTrue(
            long_name == fname,
            f"Expected long name ('{long_name}') to be original name ('{fname}')",
        )
        self.assertEqual(long_name, win32api.GetLongPathNameW(short_name).lower())
        long_name = win32api.GetLongPathNameW(short_name).lower()
        self.assertTrue(
            isinstance(long_name, str),
            f"GetLongPathNameW returned type '{type(long_name)}'",
        )
        self.assertTrue(
            long_name == fname,
            f"Expected long name ('{long_name}') to be original name ('{fname}')",
        )

    def testShortUnicodeNames(self):
        try:
            me = __file__
        except NameError:
            me = sys.argv[0]
        fname = os.path.abspath(me).lower()
        # passing unicode should cause GetShortPathNameW to be called.
        short_name = win32api.GetShortPathName(str(fname)).lower()
        self.assertTrue(isinstance(short_name, str))
        long_name = win32api.GetLongPathName(short_name).lower()
        self.assertTrue(
            long_name == fname,
            f"Expected long name ('{long_name}') to be original name ('{fname}')",
        )
        self.assertEqual(long_name, win32api.GetLongPathNameW(short_name).lower())
        long_name = win32api.GetLongPathNameW(short_name).lower()
        self.assertTrue(
            isinstance(long_name, str),
            f"GetLongPathNameW returned type '{type(long_name)}'",
        )
        self.assertTrue(
            long_name == fname,
            f"Expected long name ('{long_name}') to be original name ('{fname}')",
        )

    def testLongLongPathNames(self):
        # We need filename where the FQN is > 256 - simplest way is to create a
        # 250 character directory in the cwd (except - cwd may be on a drive
        # not supporting \\\\?\\ (eg, network share) - so use temp.
        import win32file

        basename = "a" * 250
        # but we need to ensure we use the 'long' version of the
        # temp dir for later comparison.
        long_temp_dir = win32api.GetLongPathNameW(tempfile.gettempdir())
        fname = "\\\\?\\" + os.path.join(long_temp_dir, basename)
        try:
            win32file.CreateDirectoryW(fname, None)
        except win32api.error as details:
            if details.winerror != winerror.ERROR_ALREADY_EXISTS:
                raise
        try:
            # GetFileAttributes automatically calls GetFileAttributesW when
            # passed unicode
            try:
                attr = win32api.GetFileAttributes(fname)
            except win32api.error as details:
                if details.winerror != winerror.ERROR_FILENAME_EXCED_RANGE:
                    raise

            attr = win32api.GetFileAttributes(str(fname))
            self.assertTrue(attr & win32con.FILE_ATTRIBUTE_DIRECTORY, attr)

            long_name = win32api.GetLongPathNameW(fname)
            self.assertEqual(long_name.lower(), fname.lower())
        finally:
            win32file.RemoveDirectory(fname)


class FormatMessage(unittest.TestCase):
    def test_FromString(self):
        msg = "Hello %1, how are you %2?"
        inserts = ["Mark", "today"]
        result = win32api.FormatMessage(
            win32con.FORMAT_MESSAGE_FROM_STRING,
            msg,  # source
            0,  # ID
            0,  # LangID
            inserts,
        )
        self.assertEqual(result, "Hello Mark, how are you today?")


class Misc(unittest.TestCase):
    def test_last_error(self):
        for x in (0, 1, -1, winerror.TRUST_E_PROVIDER_UNKNOWN):
            win32api.SetLastError(x)
            self.assertEqual(x, win32api.GetLastError())

    def testVkKeyScan(self):
        # hopefully ' ' doesn't depend on the locale!
        self.assertEqual(win32api.VkKeyScan(" "), 32)

    def testVkKeyScanEx(self):
        # hopefully ' ' doesn't depend on the locale!
        self.assertEqual(win32api.VkKeyScanEx(" ", 0), 32)

    def testGetSystemPowerStatus(self):
        # Dummy
        sps = win32api.GetSystemPowerStatus()
        self.assertIsInstance(sps, dict)
        test_keys = (
            "ACLineStatus",
            "BatteryFlag",
            "BatteryLifePercent",
            "SystemStatusFlag",
            "BatteryLifeTime",
            "BatteryFullLifeTime",
        )
        self.assertEqual(set(test_keys), set(sps))


if __name__ == "__main__":
    unittest.main()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\platformdirs\windows.py ===
"""Windows."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import TYPE_CHECKING

from .api import PlatformDirsABC

if TYPE_CHECKING:
    from collections.abc import Callable


class Windows(PlatformDirsABC):
    """
    `MSDN on where to store app data files <https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid>`_.

    Makes use of the `appname <platformdirs.api.PlatformDirsABC.appname>`, `appauthor
    <platformdirs.api.PlatformDirsABC.appauthor>`, `version <platformdirs.api.PlatformDirsABC.version>`, `roaming
    <platformdirs.api.PlatformDirsABC.roaming>`, `opinion <platformdirs.api.PlatformDirsABC.opinion>`, `ensure_exists
    <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """
        :return: data directory tied to the user, e.g.
         ``%USERPROFILE%\\AppData\\Local\\$appauthor\\$appname`` (not roaming) or
         ``%USERPROFILE%\\AppData\\Roaming\\$appauthor\\$appname`` (roaming)
        """
        const = "CSIDL_APPDATA" if self.roaming else "CSIDL_LOCAL_APPDATA"
        path = os.path.normpath(get_win_folder(const))
        return self._append_parts(path)

    def _append_parts(self, path: str, *, opinion_value: str | None = None) -> str:
        params = []
        if self.appname:
            if self.appauthor is not False:
                author = self.appauthor or self.appname
                params.append(author)
            params.append(self.appname)
            if opinion_value is not None and self.opinion:
                params.append(opinion_value)
            if self.version:
                params.append(self.version)
        path = os.path.join(path, *params)  # noqa: PTH118
        self._optionally_create_directory(path)
        return path

    @property
    def site_data_dir(self) -> str:
        """:return: data directory shared by users, e.g. ``C:\\ProgramData\\$appauthor\\$appname``"""
        path = os.path.normpath(get_win_folder("CSIDL_COMMON_APPDATA"))
        return self._append_parts(path)

    @property
    def user_config_dir(self) -> str:
        """:return: config directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users, same as `site_data_dir`"""
        return self.site_data_dir

    @property
    def user_cache_dir(self) -> str:
        """
        :return: cache directory tied to the user (if opinionated with ``Cache`` folder within ``$appname``) e.g.
         ``%USERPROFILE%\\AppData\\Local\\$appauthor\\$appname\\Cache\\$version``
        """
        path = os.path.normpath(get_win_folder("CSIDL_LOCAL_APPDATA"))
        return self._append_parts(path, opinion_value="Cache")

    @property
    def site_cache_dir(self) -> str:
        """:return: cache directory shared by users, e.g. ``C:\\ProgramData\\$appauthor\\$appname\\Cache\\$version``"""
        path = os.path.normpath(get_win_folder("CSIDL_COMMON_APPDATA"))
        return self._append_parts(path, opinion_value="Cache")

    @property
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user, same as `user_data_dir` if not opinionated else ``Logs`` in it"""
        path = self.user_data_dir
        if self.opinion:
            path = os.path.join(path, "Logs")  # noqa: PTH118
            self._optionally_create_directory(path)
        return path

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user e.g. ``%USERPROFILE%\\Documents``"""
        return os.path.normpath(get_win_folder("CSIDL_PERSONAL"))

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user e.g. ``%USERPROFILE%\\Downloads``"""
        return os.path.normpath(get_win_folder("CSIDL_DOWNLOADS"))

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user e.g. ``%USERPROFILE%\\Pictures``"""
        return os.path.normpath(get_win_folder("CSIDL_MYPICTURES"))

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user e.g. ``%USERPROFILE%\\Videos``"""
        return os.path.normpath(get_win_folder("CSIDL_MYVIDEO"))

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user e.g. ``%USERPROFILE%\\Music``"""
        return os.path.normpath(get_win_folder("CSIDL_MYMUSIC"))

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user, e.g. ``%USERPROFILE%\\Desktop``"""
        return os.path.normpath(get_win_folder("CSIDL_DESKTOPDIRECTORY"))

    @property
    def user_runtime_dir(self) -> str:
        """
        :return: runtime directory tied to the user, e.g.
         ``%USERPROFILE%\\AppData\\Local\\Temp\\$appauthor\\$appname``
        """
        path = os.path.normpath(os.path.join(get_win_folder("CSIDL_LOCAL_APPDATA"), "Temp"))  # noqa: PTH118
        return self._append_parts(path)

    @property
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users, same as `user_runtime_dir`"""
        return self.user_runtime_dir


def get_win_folder_from_env_vars(csidl_name: str) -> str:
    """Get folder from environment variables."""
    result = get_win_folder_if_csidl_name_not_env_var(csidl_name)
    if result is not None:
        return result

    env_var_name = {
        "CSIDL_APPDATA": "APPDATA",
        "CSIDL_COMMON_APPDATA": "ALLUSERSPROFILE",
        "CSIDL_LOCAL_APPDATA": "LOCALAPPDATA",
    }.get(csidl_name)
    if env_var_name is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)
    result = os.environ.get(env_var_name)
    if result is None:
        msg = f"Unset environment variable: {env_var_name}"
        raise ValueError(msg)
    return result


def get_win_folder_if_csidl_name_not_env_var(csidl_name: str) -> str | None:
    """Get a folder for a CSIDL name that does not exist as an environment variable."""
    if csidl_name == "CSIDL_PERSONAL":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Documents")  # noqa: PTH118

    if csidl_name == "CSIDL_DOWNLOADS":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Downloads")  # noqa: PTH118

    if csidl_name == "CSIDL_MYPICTURES":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Pictures")  # noqa: PTH118

    if csidl_name == "CSIDL_MYVIDEO":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Videos")  # noqa: PTH118

    if csidl_name == "CSIDL_MYMUSIC":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Music")  # noqa: PTH118
    return None


def get_win_folder_from_registry(csidl_name: str) -> str:
    """
    Get folder from the registry.

    This is a fallback technique at best. I'm not sure if using the registry for these guarantees us the correct answer
    for all CSIDL_* names.

    """
    shell_folder_name = {
        "CSIDL_APPDATA": "AppData",
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
        "CSIDL_PERSONAL": "Personal",
        "CSIDL_DOWNLOADS": "{374DE290-123F-4565-9164-39C4925E467B}",
        "CSIDL_MYPICTURES": "My Pictures",
        "CSIDL_MYVIDEO": "My Video",
        "CSIDL_MYMUSIC": "My Music",
    }.get(csidl_name)
    if shell_folder_name is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)
    if sys.platform != "win32":  # only needed for mypy type checker to know that this code runs only on Windows
        raise NotImplementedError
    import winreg  # noqa: PLC0415

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
    directory, _ = winreg.QueryValueEx(key, shell_folder_name)
    return str(directory)


def get_win_folder_via_ctypes(csidl_name: str) -> str:
    """Get folder with ctypes."""
    # There is no 'CSIDL_DOWNLOADS'.
    # Use 'CSIDL_PROFILE' (40) and append the default folder 'Downloads' instead.
    # https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid

    import ctypes  # noqa: PLC0415

    csidl_const = {
        "CSIDL_APPDATA": 26,
        "CSIDL_COMMON_APPDATA": 35,
        "CSIDL_LOCAL_APPDATA": 28,
        "CSIDL_PERSONAL": 5,
        "CSIDL_MYPICTURES": 39,
        "CSIDL_MYVIDEO": 14,
        "CSIDL_MYMUSIC": 13,
        "CSIDL_DOWNLOADS": 40,
        "CSIDL_DESKTOPDIRECTORY": 16,
    }.get(csidl_name)
    if csidl_const is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)

    buf = ctypes.create_unicode_buffer(1024)
    windll = getattr(ctypes, "windll")  # noqa: B009 # using getattr to avoid false positive with mypy type checker
    windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)

    # Downgrade to short path name if it has high-bit chars.
    if any(ord(c) > 255 for c in buf):  # noqa: PLR2004
        buf2 = ctypes.create_unicode_buffer(1024)
        if windll.kernel32.GetShortPathNameW(buf.value, buf2, 1024):
            buf = buf2

    if csidl_name == "CSIDL_DOWNLOADS":
        return os.path.join(buf.value, "Downloads")  # noqa: PTH118

    return buf.value


def _pick_get_win_folder() -> Callable[[str], str]:
    try:
        import ctypes  # noqa: PLC0415
    except ImportError:
        pass
    else:
        if hasattr(ctypes, "windll"):
            return get_win_folder_via_ctypes
    try:
        import winreg  # noqa: PLC0415, F401
    except ImportError:
        return get_win_folder_from_env_vars
    else:
        return get_win_folder_from_registry


get_win_folder = lru_cache(maxsize=None)(_pick_get_win_folder())

__all__ = [
    "Windows",
]