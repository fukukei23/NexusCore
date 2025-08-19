
# === NexusCore/tools\exports\export_20250803_114325\combined_173.py ===

# === NexusCore/openenv\Lib\site-packages\openai\_legacy_response.py ===
from __future__ import annotations

import os
import inspect
import logging
import datetime
import functools
from typing import (
    TYPE_CHECKING,
    Any,
    Union,
    Generic,
    TypeVar,
    Callable,
    Iterator,
    AsyncIterator,
    cast,
    overload,
)
from typing_extensions import Awaitable, ParamSpec, override, deprecated, get_origin

import anyio
import httpx
import pydantic

from ._types import NoneType
from ._utils import is_given, extract_type_arg, is_annotated_type, is_type_alias_type
from ._models import BaseModel, is_basemodel, add_request_id
from ._constants import RAW_RESPONSE_HEADER
from ._streaming import Stream, AsyncStream, is_stream_class_type, extract_stream_chunk_type
from ._exceptions import APIResponseValidationError

if TYPE_CHECKING:
    from ._models import FinalRequestOptions
    from ._base_client import BaseClient


P = ParamSpec("P")
R = TypeVar("R")
_T = TypeVar("_T")

log: logging.Logger = logging.getLogger(__name__)


class LegacyAPIResponse(Generic[R]):
    """This is a legacy class as it will be replaced by `APIResponse`
    and `AsyncAPIResponse` in the `_response.py` file in the next major
    release.

    For the sync client this will mostly be the same with the exception
    of `content` & `text` will be methods instead of properties. In the
    async client, all methods will be async.

    A migration script will be provided & the migration in general should
    be smooth.
    """

    _cast_to: type[R]
    _client: BaseClient[Any, Any]
    _parsed_by_type: dict[type[Any], Any]
    _stream: bool
    _stream_cls: type[Stream[Any]] | type[AsyncStream[Any]] | None
    _options: FinalRequestOptions

    http_response: httpx.Response

    retries_taken: int
    """The number of retries made. If no retries happened this will be `0`"""

    def __init__(
        self,
        *,
        raw: httpx.Response,
        cast_to: type[R],
        client: BaseClient[Any, Any],
        stream: bool,
        stream_cls: type[Stream[Any]] | type[AsyncStream[Any]] | None,
        options: FinalRequestOptions,
        retries_taken: int = 0,
    ) -> None:
        self._cast_to = cast_to
        self._client = client
        self._parsed_by_type = {}
        self._stream = stream
        self._stream_cls = stream_cls
        self._options = options
        self.http_response = raw
        self.retries_taken = retries_taken

    @property
    def request_id(self) -> str | None:
        return self.http_response.headers.get("x-request-id")  # type: ignore[no-any-return]

    @overload
    def parse(self, *, to: type[_T]) -> _T: ...

    @overload
    def parse(self) -> R: ...

    def parse(self, *, to: type[_T] | None = None) -> R | _T:
        """Returns the rich python representation of this response's data.

        NOTE: For the async client: this will become a coroutine in the next major version.

        For lower-level control, see `.read()`, `.json()`, `.iter_bytes()`.

        You can customise the type that the response is parsed into through
        the `to` argument, e.g.

        ```py
        from openai import BaseModel


        class MyModel(BaseModel):
            foo: str


        obj = response.parse(to=MyModel)
        print(obj.foo)
        ```

        We support parsing:
          - `BaseModel`
          - `dict`
          - `list`
          - `Union`
          - `str`
          - `int`
          - `float`
          - `httpx.Response`
        """
        cache_key = to if to is not None else self._cast_to
        cached = self._parsed_by_type.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        parsed = self._parse(to=to)
        if is_given(self._options.post_parser):
            parsed = self._options.post_parser(parsed)

        if isinstance(parsed, BaseModel):
            add_request_id(parsed, self.request_id)

        self._parsed_by_type[cache_key] = parsed
        return cast(R, parsed)

    @property
    def headers(self) -> httpx.Headers:
        return self.http_response.headers

    @property
    def http_request(self) -> httpx.Request:
        return self.http_response.request

    @property
    def status_code(self) -> int:
        return self.http_response.status_code

    @property
    def url(self) -> httpx.URL:
        return self.http_response.url

    @property
    def method(self) -> str:
        return self.http_request.method

    @property
    def content(self) -> bytes:
        """Return the binary response content.

        NOTE: this will be removed in favour of `.read()` in the
        next major version.
        """
        return self.http_response.content

    @property
    def text(self) -> str:
        """Return the decoded response content.

        NOTE: this will be turned into a method in the next major version.
        """
        return self.http_response.text

    @property
    def http_version(self) -> str:
        return self.http_response.http_version

    @property
    def is_closed(self) -> bool:
        return self.http_response.is_closed

    @property
    def elapsed(self) -> datetime.timedelta:
        """The time taken for the complete request/response cycle to complete."""
        return self.http_response.elapsed

    def _parse(self, *, to: type[_T] | None = None) -> R | _T:
        cast_to = to if to is not None else self._cast_to

        # unwrap `TypeAlias('Name', T)` -> `T`
        if is_type_alias_type(cast_to):
            cast_to = cast_to.__value__  # type: ignore[unreachable]

        # unwrap `Annotated[T, ...]` -> `T`
        if cast_to and is_annotated_type(cast_to):
            cast_to = extract_type_arg(cast_to, 0)

        origin = get_origin(cast_to) or cast_to

        if self._stream:
            if to:
                if not is_stream_class_type(to):
                    raise TypeError(f"Expected custom parse type to be a subclass of {Stream} or {AsyncStream}")

                return cast(
                    _T,
                    to(
                        cast_to=extract_stream_chunk_type(
                            to,
                            failure_message="Expected custom stream type to be passed with a type argument, e.g. Stream[ChunkType]",
                        ),
                        response=self.http_response,
                        client=cast(Any, self._client),
                    ),
                )

            if self._stream_cls:
                return cast(
                    R,
                    self._stream_cls(
                        cast_to=extract_stream_chunk_type(self._stream_cls),
                        response=self.http_response,
                        client=cast(Any, self._client),
                    ),
                )

            stream_cls = cast("type[Stream[Any]] | type[AsyncStream[Any]] | None", self._client._default_stream_cls)
            if stream_cls is None:
                raise MissingStreamClassError()

            return cast(
                R,
                stream_cls(
                    cast_to=cast_to,
                    response=self.http_response,
                    client=cast(Any, self._client),
                ),
            )

        if cast_to is NoneType:
            return cast(R, None)

        response = self.http_response
        if cast_to == str:
            return cast(R, response.text)

        if cast_to == int:
            return cast(R, int(response.text))

        if cast_to == float:
            return cast(R, float(response.text))

        if cast_to == bool:
            return cast(R, response.text.lower() == "true")

        if inspect.isclass(origin) and issubclass(origin, HttpxBinaryResponseContent):
            return cast(R, cast_to(response))  # type: ignore

        if origin == LegacyAPIResponse:
            raise RuntimeError("Unexpected state - cast_to is `APIResponse`")

        if inspect.isclass(
            origin  # pyright: ignore[reportUnknownArgumentType]
        ) and issubclass(origin, httpx.Response):
            # Because of the invariance of our ResponseT TypeVar, users can subclass httpx.Response
            # and pass that class to our request functions. We cannot change the variance to be either
            # covariant or contravariant as that makes our usage of ResponseT illegal. We could construct
            # the response class ourselves but that is something that should be supported directly in httpx
            # as it would be easy to incorrectly construct the Response object due to the multitude of arguments.
            if cast_to != httpx.Response:
                raise ValueError(f"Subclasses of httpx.Response cannot be passed to `cast_to`")
            return cast(R, response)

        if (
            inspect.isclass(
                origin  # pyright: ignore[reportUnknownArgumentType]
            )
            and not issubclass(origin, BaseModel)
            and issubclass(origin, pydantic.BaseModel)
        ):
            raise TypeError("Pydantic models must subclass our base model type, e.g. `from openai import BaseModel`")

        if (
            cast_to is not object
            and not origin is list
            and not origin is dict
            and not origin is Union
            and not issubclass(origin, BaseModel)
        ):
            raise RuntimeError(
                f"Unsupported type, expected {cast_to} to be a subclass of {BaseModel}, {dict}, {list}, {Union}, {NoneType}, {str} or {httpx.Response}."
            )

        # split is required to handle cases where additional information is included
        # in the response, e.g. application/json; charset=utf-8
        content_type, *_ = response.headers.get("content-type", "*").split(";")
        if not content_type.endswith("json"):
            if is_basemodel(cast_to):
                try:
                    data = response.json()
                except Exception as exc:
                    log.debug("Could not read JSON from response data due to %s - %s", type(exc), exc)
                else:
                    return self._client._process_response_data(
                        data=data,
                        cast_to=cast_to,  # type: ignore
                        response=response,
                    )

            if self._client._strict_response_validation:
                raise APIResponseValidationError(
                    response=response,
                    message=f"Expected Content-Type response header to be `application/json` but received `{content_type}` instead.",
                    body=response.text,
                )

            # If the API responds with content that isn't JSON then we just return
            # the (decoded) text without performing any parsing so that you can still
            # handle the response however you need to.
            return response.text  # type: ignore

        data = response.json()

        return self._client._process_response_data(
            data=data,
            cast_to=cast_to,  # type: ignore
            response=response,
        )

    @override
    def __repr__(self) -> str:
        return f"<APIResponse [{self.status_code} {self.http_response.reason_phrase}] type={self._cast_to}>"


class MissingStreamClassError(TypeError):
    def __init__(self) -> None:
        super().__init__(
            "The `stream` argument was set to `True` but the `stream_cls` argument was not given. See `openai._streaming` for reference",
        )


def to_raw_response_wrapper(func: Callable[P, R]) -> Callable[P, LegacyAPIResponse[R]]:
    """Higher order function that takes one of our bound API methods and wraps it
    to support returning the raw `APIResponse` object directly.
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> LegacyAPIResponse[R]:
        extra_headers: dict[str, str] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "true"

        kwargs["extra_headers"] = extra_headers

        return cast(LegacyAPIResponse[R], func(*args, **kwargs))

    return wrapped


def async_to_raw_response_wrapper(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[LegacyAPIResponse[R]]]:
    """Higher order function that takes one of our bound API methods and wraps it
    to support returning the raw `APIResponse` object directly.
    """

    @functools.wraps(func)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> LegacyAPIResponse[R]:
        extra_headers: dict[str, str] = {**(cast(Any, kwargs.get("extra_headers")) or {})}
        extra_headers[RAW_RESPONSE_HEADER] = "true"

        kwargs["extra_headers"] = extra_headers

        return cast(LegacyAPIResponse[R], await func(*args, **kwargs))

    return wrapped


class HttpxBinaryResponseContent:
    response: httpx.Response

    def __init__(self, response: httpx.Response) -> None:
        self.response = response

    @property
    def content(self) -> bytes:
        return self.response.content

    @property
    def text(self) -> str:
        return self.response.text

    @property
    def encoding(self) -> str | None:
        return self.response.encoding

    @property
    def charset_encoding(self) -> str | None:
        return self.response.charset_encoding

    def json(self, **kwargs: Any) -> Any:
        return self.response.json(**kwargs)

    def read(self) -> bytes:
        return self.response.read()

    def iter_bytes(self, chunk_size: int | None = None) -> Iterator[bytes]:
        return self.response.iter_bytes(chunk_size)

    def iter_text(self, chunk_size: int | None = None) -> Iterator[str]:
        return self.response.iter_text(chunk_size)

    def iter_lines(self) -> Iterator[str]:
        return self.response.iter_lines()

    def iter_raw(self, chunk_size: int | None = None) -> Iterator[bytes]:
        return self.response.iter_raw(chunk_size)

    def write_to_file(
        self,
        file: str | os.PathLike[str],
    ) -> None:
        """Write the output to the given file.

        Accepts a filename or any path-like object, e.g. pathlib.Path

        Note: if you want to stream the data to the file instead of writing
        all at once then you should use `.with_streaming_response` when making
        the API request, e.g. `client.with_streaming_response.foo().stream_to_file('my_filename.txt')`
        """
        with open(file, mode="wb") as f:
            for data in self.response.iter_bytes():
                f.write(data)

    @deprecated(
        "Due to a bug, this method doesn't actually stream the response content, `.with_streaming_response.method()` should be used instead"
    )
    def stream_to_file(
        self,
        file: str | os.PathLike[str],
        *,
        chunk_size: int | None = None,
    ) -> None:
        with open(file, mode="wb") as f:
            for data in self.response.iter_bytes(chunk_size):
                f.write(data)

    def close(self) -> None:
        return self.response.close()

    async def aread(self) -> bytes:
        return await self.response.aread()

    async def aiter_bytes(self, chunk_size: int | None = None) -> AsyncIterator[bytes]:
        return self.response.aiter_bytes(chunk_size)

    async def aiter_text(self, chunk_size: int | None = None) -> AsyncIterator[str]:
        return self.response.aiter_text(chunk_size)

    async def aiter_lines(self) -> AsyncIterator[str]:
        return self.response.aiter_lines()

    async def aiter_raw(self, chunk_size: int | None = None) -> AsyncIterator[bytes]:
        return self.response.aiter_raw(chunk_size)

    @deprecated(
        "Due to a bug, this method doesn't actually stream the response content, `.with_streaming_response.method()` should be used instead"
    )
    async def astream_to_file(
        self,
        file: str | os.PathLike[str],
        *,
        chunk_size: int | None = None,
    ) -> None:
        path = anyio.Path(file)
        async with await path.open(mode="wb") as f:
            async for data in self.response.aiter_bytes(chunk_size):
                await f.write(data)

    async def aclose(self) -> None:
        return await self.response.aclose()

# === NexusCore/openenv\Lib\site-packages\parso\tree.py ===
from abc import abstractmethod, abstractproperty
from typing import List, Optional, Tuple, Union

from parso.utils import split_lines


def search_ancestor(node: 'NodeOrLeaf', *node_types: str) -> 'Optional[BaseNode]':
    """
    Recursively looks at the parents of a node and returns the first found node
    that matches ``node_types``. Returns ``None`` if no matching node is found.

    This function is deprecated, use :meth:`NodeOrLeaf.search_ancestor` instead.

    :param node: The ancestors of this node will be checked.
    :param node_types: type names that are searched for.
    """
    n = node.parent
    while n is not None:
        if n.type in node_types:
            return n
        n = n.parent
    return None


class NodeOrLeaf:
    """
    The base class for nodes and leaves.
    """
    __slots__ = ('parent',)
    type: str
    '''
    The type is a string that typically matches the types of the grammar file.
    '''
    parent: 'Optional[BaseNode]'
    '''
    The parent :class:`BaseNode` of this node or leaf.
    None if this is the root node.
    '''

    def get_root_node(self):
        """
        Returns the root node of a parser tree. The returned node doesn't have
        a parent node like all the other nodes/leaves.
        """
        scope = self
        while scope.parent is not None:
            scope = scope.parent
        return scope

    def get_next_sibling(self):
        """
        Returns the node immediately following this node in this parent's
        children list. If this node does not have a next sibling, it is None
        """
        parent = self.parent
        if parent is None:
            return None

        # Can't use index(); we need to test by identity
        for i, child in enumerate(parent.children):
            if child is self:
                try:
                    return self.parent.children[i + 1]
                except IndexError:
                    return None

    def get_previous_sibling(self):
        """
        Returns the node immediately preceding this node in this parent's
        children list. If this node does not have a previous sibling, it is
        None.
        """
        parent = self.parent
        if parent is None:
            return None

        # Can't use index(); we need to test by identity
        for i, child in enumerate(parent.children):
            if child is self:
                if i == 0:
                    return None
                return self.parent.children[i - 1]

    def get_previous_leaf(self):
        """
        Returns the previous leaf in the parser tree.
        Returns `None` if this is the first element in the parser tree.
        """
        if self.parent is None:
            return None

        node = self
        while True:
            c = node.parent.children
            i = c.index(node)
            if i == 0:
                node = node.parent
                if node.parent is None:
                    return None
            else:
                node = c[i - 1]
                break

        while True:
            try:
                node = node.children[-1]
            except AttributeError:  # A Leaf doesn't have children.
                return node

    def get_next_leaf(self):
        """
        Returns the next leaf in the parser tree.
        Returns None if this is the last element in the parser tree.
        """
        if self.parent is None:
            return None

        node = self
        while True:
            c = node.parent.children
            i = c.index(node)
            if i == len(c) - 1:
                node = node.parent
                if node.parent is None:
                    return None
            else:
                node = c[i + 1]
                break

        while True:
            try:
                node = node.children[0]
            except AttributeError:  # A Leaf doesn't have children.
                return node

    @abstractproperty
    def start_pos(self) -> Tuple[int, int]:
        """
        Returns the starting position of the prefix as a tuple, e.g. `(3, 4)`.

        :return tuple of int: (line, column)
        """

    @abstractproperty
    def end_pos(self) -> Tuple[int, int]:
        """
        Returns the end position of the prefix as a tuple, e.g. `(3, 4)`.

        :return tuple of int: (line, column)
        """

    @abstractmethod
    def get_start_pos_of_prefix(self):
        """
        Returns the start_pos of the prefix. This means basically it returns
        the end_pos of the last prefix. The `get_start_pos_of_prefix()` of the
        prefix `+` in `2 + 1` would be `(1, 1)`, while the start_pos is
        `(1, 2)`.

        :return tuple of int: (line, column)
        """

    @abstractmethod
    def get_first_leaf(self):
        """
        Returns the first leaf of a node or itself if this is a leaf.
        """

    @abstractmethod
    def get_last_leaf(self):
        """
        Returns the last leaf of a node or itself if this is a leaf.
        """

    @abstractmethod
    def get_code(self, include_prefix=True):
        """
        Returns the code that was the input for the parser for this node.

        :param include_prefix: Removes the prefix (whitespace and comments) of
            e.g. a statement.
        """

    def search_ancestor(self, *node_types: str) -> 'Optional[BaseNode]':
        """
        Recursively looks at the parents of this node or leaf and returns the
        first found node that matches ``node_types``. Returns ``None`` if no
        matching node is found.

        :param node_types: type names that are searched for.
        """
        node = self.parent
        while node is not None:
            if node.type in node_types:
                return node
            node = node.parent
        return None

    def dump(self, *, indent: Optional[Union[int, str]] = 4) -> str:
        """
        Returns a formatted dump of the parser tree rooted at this node or leaf. This is
        mainly useful for debugging purposes.

        The ``indent`` parameter is interpreted in a similar way as :py:func:`ast.dump`.
        If ``indent`` is a non-negative integer or string, then the tree will be
        pretty-printed with that indent level. An indent level of 0, negative, or ``""``
        will only insert newlines. ``None`` selects the single line representation.
        Using a positive integer indent indents that many spaces per level. If
        ``indent`` is a string (such as ``"\\t"``), that string is used to indent each
        level.

        :param indent: Indentation style as described above. The default indentation is
            4 spaces, which yields a pretty-printed dump.

        >>> import parso
        >>> print(parso.parse("lambda x, y: x + y").dump())
        Module([
            Lambda([
                Keyword('lambda', (1, 0)),
                Param([
                    Name('x', (1, 7), prefix=' '),
                    Operator(',', (1, 8)),
                ]),
                Param([
                    Name('y', (1, 10), prefix=' '),
                ]),
                Operator(':', (1, 11)),
                PythonNode('arith_expr', [
                    Name('x', (1, 13), prefix=' '),
                    Operator('+', (1, 15), prefix=' '),
                    Name('y', (1, 17), prefix=' '),
                ]),
            ]),
            EndMarker('', (1, 18)),
        ])
        """
        if indent is None:
            newline = False
            indent_string = ''
        elif isinstance(indent, int):
            newline = True
            indent_string = ' ' * indent
        elif isinstance(indent, str):
            newline = True
            indent_string = indent
        else:
            raise TypeError(f"expect 'indent' to be int, str or None, got {indent!r}")

        def _format_dump(node: NodeOrLeaf, indent: str = '', top_level: bool = True) -> str:
            result = ''
            node_type = type(node).__name__
            if isinstance(node, Leaf):
                result += f'{indent}{node_type}('
                if isinstance(node, ErrorLeaf):
                    result += f'{node.token_type!r}, '
                elif isinstance(node, TypedLeaf):
                    result += f'{node.type!r}, '
                result += f'{node.value!r}, {node.start_pos!r}'
                if node.prefix:
                    result += f', prefix={node.prefix!r}'
                result += ')'
            elif isinstance(node, BaseNode):
                result += f'{indent}{node_type}('
                if isinstance(node, Node):
                    result += f'{node.type!r}, '
                result += '['
                if newline:
                    result += '\n'
                for child in node.children:
                    result += _format_dump(child, indent=indent + indent_string, top_level=False)
                result += f'{indent}])'
            else:  # pragma: no cover
                # We shouldn't ever reach here, unless:
                # - `NodeOrLeaf` is incorrectly subclassed else where
                # - or a node's children list contains invalid nodes or leafs
                # Both are unexpected internal errors.
                raise TypeError(f'unsupported node encountered: {node!r}')
            if not top_level:
                if newline:
                    result += ',\n'
                else:
                    result += ', '
            return result

        return _format_dump(self)


class Leaf(NodeOrLeaf):
    '''
    Leafs are basically tokens with a better API. Leafs exactly know where they
    were defined and what text preceeds them.
    '''
    __slots__ = ('value', 'line', 'column', 'prefix')
    prefix: str

    def __init__(self, value: str, start_pos: Tuple[int, int], prefix: str = '') -> None:
        self.value = value
        '''
        :py:func:`str` The value of the current token.
        '''
        self.start_pos = start_pos
        self.prefix = prefix
        '''
        :py:func:`str` Typically a mixture of whitespace and comments. Stuff
        that is syntactically irrelevant for the syntax tree.
        '''
        self.parent: Optional[BaseNode] = None
        '''
        The parent :class:`BaseNode` of this leaf.
        '''

    @property
    def start_pos(self) -> Tuple[int, int]:
        return self.line, self.column

    @start_pos.setter
    def start_pos(self, value: Tuple[int, int]) -> None:
        self.line = value[0]
        self.column = value[1]

    def get_start_pos_of_prefix(self):
        previous_leaf = self.get_previous_leaf()
        if previous_leaf is None:
            lines = split_lines(self.prefix)
            # + 1 is needed because split_lines always returns at least [''].
            return self.line - len(lines) + 1, 0  # It's the first leaf.
        return previous_leaf.end_pos

    def get_first_leaf(self):
        return self

    def get_last_leaf(self):
        return self

    def get_code(self, include_prefix=True):
        if include_prefix:
            return self.prefix + self.value
        else:
            return self.value

    @property
    def end_pos(self) -> Tuple[int, int]:
        lines = split_lines(self.value)
        end_pos_line = self.line + len(lines) - 1
        # Check for multiline token
        if self.line == end_pos_line:
            end_pos_column = self.column + len(lines[-1])
        else:
            end_pos_column = len(lines[-1])
        return end_pos_line, end_pos_column

    def __repr__(self):
        value = self.value
        if not value:
            value = self.type
        return "<%s: %s>" % (type(self).__name__, value)


class TypedLeaf(Leaf):
    __slots__ = ('type',)

    def __init__(self, type, value, start_pos, prefix=''):
        super().__init__(value, start_pos, prefix)
        self.type = type


class BaseNode(NodeOrLeaf):
    """
    The super class for all nodes.
    A node has children, a type and possibly a parent node.
    """
    __slots__ = ('children',)

    def __init__(self, children: List[NodeOrLeaf]) -> None:
        self.children = children
        """
        A list of :class:`NodeOrLeaf` child nodes.
        """
        self.parent: Optional[BaseNode] = None
        '''
        The parent :class:`BaseNode` of this node.
        None if this is the root node.
        '''
        for child in children:
            child.parent = self

    @property
    def start_pos(self) -> Tuple[int, int]:
        return self.children[0].start_pos

    def get_start_pos_of_prefix(self):
        return self.children[0].get_start_pos_of_prefix()

    @property
    def end_pos(self) -> Tuple[int, int]:
        return self.children[-1].end_pos

    def _get_code_for_children(self, children, include_prefix):
        if include_prefix:
            return "".join(c.get_code() for c in children)
        else:
            first = children[0].get_code(include_prefix=False)
            return first + "".join(c.get_code() for c in children[1:])

    def get_code(self, include_prefix=True):
        return self._get_code_for_children(self.children, include_prefix)

    def get_leaf_for_position(self, position, include_prefixes=False):
        """
        Get the :py:class:`parso.tree.Leaf` at ``position``

        :param tuple position: A position tuple, row, column. Rows start from 1
        :param bool include_prefixes: If ``False``, ``None`` will be returned if ``position`` falls
            on whitespace or comments before a leaf
        :return: :py:class:`parso.tree.Leaf` at ``position``, or ``None``
        """
        def binary_search(lower, upper):
            if lower == upper:
                element = self.children[lower]
                if not include_prefixes and position < element.start_pos:
                    # We're on a prefix.
                    return None
                # In case we have prefixes, a leaf always matches
                try:
                    return element.get_leaf_for_position(position, include_prefixes)
                except AttributeError:
                    return element

            index = int((lower + upper) / 2)
            element = self.children[index]
            if position <= element.end_pos:
                return binary_search(lower, index)
            else:
                return binary_search(index + 1, upper)

        if not ((1, 0) <= position <= self.children[-1].end_pos):
            raise ValueError('Please provide a position that exists within this node.')
        return binary_search(0, len(self.children) - 1)

    def get_first_leaf(self):
        return self.children[0].get_first_leaf()

    def get_last_leaf(self):
        return self.children[-1].get_last_leaf()

    def __repr__(self):
        code = self.get_code().replace('\n', ' ').replace('\r', ' ').strip()
        return "<%s: %s@%s,%s>" % \
            (type(self).__name__, code, self.start_pos[0], self.start_pos[1])


class Node(BaseNode):
    """Concrete implementation for interior nodes."""
    __slots__ = ('type',)

    def __init__(self, type, children):
        super().__init__(children)
        self.type = type

    def __repr__(self):
        return "%s(%s, %r)" % (self.__class__.__name__, self.type, self.children)


class ErrorNode(BaseNode):
    """
    A node that contains valid nodes/leaves that we're follow by a token that
    was invalid. This basically means that the leaf after this node is where
    Python would mark a syntax error.
    """
    __slots__ = ()
    type = 'error_node'


class ErrorLeaf(Leaf):
    """
    A leaf that is either completely invalid in a language (like `$` in Python)
    or is invalid at that position. Like the star in `1 +* 1`.
    """
    __slots__ = ('token_type',)
    type = 'error_leaf'

    def __init__(self, token_type, value, start_pos, prefix=''):
        super().__init__(value, start_pos, prefix)
        self.token_type = token_type

    def __repr__(self):
        return "<%s: %s:%s, %s>" % \
            (type(self).__name__, self.token_type, repr(self.value), self.start_pos)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\vendored\bytecode\peephole_opt.py ===
"""
Peephole optimizer of CPython 3.6 reimplemented in pure Python using
the bytecode module.
"""
import opcode
import operator
import sys
from _pydevd_frame_eval.vendored.bytecode import Instr, Bytecode, ControlFlowGraph, BasicBlock, Compare

JUMPS_ON_TRUE = frozenset(
    (
        "POP_JUMP_IF_TRUE",
        "JUMP_IF_TRUE_OR_POP",
    )
)

NOT_COMPARE = {
    Compare.IN: Compare.NOT_IN,
    Compare.NOT_IN: Compare.IN,
    Compare.IS: Compare.IS_NOT,
    Compare.IS_NOT: Compare.IS,
}

MAX_SIZE = 20


class ExitUnchanged(Exception):
    """Exception used to skip the peephole optimizer"""

    pass


class PeepholeOptimizer:
    """Python reimplementation of the peephole optimizer.

    Copy of the C comment:

    Perform basic peephole optimizations to components of a code object.
    The consts object should still be in list form to allow new constants
    to be appended.

    To keep the optimizer simple, it bails out (does nothing) for code that
    has a length over 32,700, and does not calculate extended arguments.
    That allows us to avoid overflow and sign issues. Likewise, it bails when
    the lineno table has complex encoding for gaps >= 255. EXTENDED_ARG can
    appear before MAKE_FUNCTION; in this case both opcodes are skipped.
    EXTENDED_ARG preceding any other opcode causes the optimizer to bail.

    Optimizations are restricted to simple transformations occuring within a
    single basic block.  All transformations keep the code size the same or
    smaller.  For those that reduce size, the gaps are initially filled with
    NOPs.  Later those NOPs are removed and the jump addresses retargeted in
    a single pass.  Code offset is adjusted accordingly.
    """

    def __init__(self):
        # bytecode.ControlFlowGraph instance
        self.code = None
        self.const_stack = None
        self.block_index = None
        self.block = None
        # index of the current instruction in self.block instructions
        self.index = None
        # whether we are in a LOAD_CONST sequence
        self.in_consts = False

    def check_result(self, value):
        try:
            size = len(value)
        except TypeError:
            return True
        return size <= MAX_SIZE

    def replace_load_const(self, nconst, instr, result):
        # FIXME: remove temporary computed constants?
        # FIXME: or at least reuse existing constants?

        self.in_consts = True

        load_const = Instr("LOAD_CONST", result, lineno=instr.lineno)
        start = self.index - nconst - 1
        self.block[start : self.index] = (load_const,)
        self.index -= nconst

        if nconst:
            del self.const_stack[-nconst:]
        self.const_stack.append(result)
        self.in_consts = True

    def eval_LOAD_CONST(self, instr):
        self.in_consts = True
        value = instr.arg
        self.const_stack.append(value)
        self.in_consts = True

    def unaryop(self, op, instr):
        try:
            value = self.const_stack[-1]
            result = op(value)
        except IndexError:
            return

        if not self.check_result(result):
            return

        self.replace_load_const(1, instr, result)

    def eval_UNARY_POSITIVE(self, instr):
        return self.unaryop(operator.pos, instr)

    def eval_UNARY_NEGATIVE(self, instr):
        return self.unaryop(operator.neg, instr)

    def eval_UNARY_INVERT(self, instr):
        return self.unaryop(operator.invert, instr)

    def get_next_instr(self, name):
        try:
            next_instr = self.block[self.index]
        except IndexError:
            return None
        if next_instr.name == name:
            return next_instr
        return None

    def eval_UNARY_NOT(self, instr):
        # Note: UNARY_NOT <const> is not optimized

        next_instr = self.get_next_instr("POP_JUMP_IF_FALSE")
        if next_instr is None:
            return None

        # Replace UNARY_NOT+POP_JUMP_IF_FALSE with POP_JUMP_IF_TRUE
        instr.set("POP_JUMP_IF_TRUE", next_instr.arg)
        del self.block[self.index]

    def binop(self, op, instr):
        try:
            left = self.const_stack[-2]
            right = self.const_stack[-1]
        except IndexError:
            return

        try:
            result = op(left, right)
        except Exception:
            return

        if not self.check_result(result):
            return

        self.replace_load_const(2, instr, result)

    def eval_BINARY_ADD(self, instr):
        return self.binop(operator.add, instr)

    def eval_BINARY_SUBTRACT(self, instr):
        return self.binop(operator.sub, instr)

    def eval_BINARY_MULTIPLY(self, instr):
        return self.binop(operator.mul, instr)

    def eval_BINARY_TRUE_DIVIDE(self, instr):
        return self.binop(operator.truediv, instr)

    def eval_BINARY_FLOOR_DIVIDE(self, instr):
        return self.binop(operator.floordiv, instr)

    def eval_BINARY_MODULO(self, instr):
        return self.binop(operator.mod, instr)

    def eval_BINARY_POWER(self, instr):
        return self.binop(operator.pow, instr)

    def eval_BINARY_LSHIFT(self, instr):
        return self.binop(operator.lshift, instr)

    def eval_BINARY_RSHIFT(self, instr):
        return self.binop(operator.rshift, instr)

    def eval_BINARY_AND(self, instr):
        return self.binop(operator.and_, instr)

    def eval_BINARY_OR(self, instr):
        return self.binop(operator.or_, instr)

    def eval_BINARY_XOR(self, instr):
        return self.binop(operator.xor, instr)

    def eval_BINARY_SUBSCR(self, instr):
        return self.binop(operator.getitem, instr)

    def replace_container_of_consts(self, instr, container_type):
        items = self.const_stack[-instr.arg :]
        value = container_type(items)
        self.replace_load_const(instr.arg, instr, value)

    def build_tuple_unpack_seq(self, instr):
        next_instr = self.get_next_instr("UNPACK_SEQUENCE")
        if next_instr is None or next_instr.arg != instr.arg:
            return

        if instr.arg < 1:
            return

        if self.const_stack and instr.arg <= len(self.const_stack):
            nconst = instr.arg
            start = self.index - 1

            # Rewrite LOAD_CONST instructions in the reverse order
            load_consts = self.block[start - nconst : start]
            self.block[start - nconst : start] = reversed(load_consts)

            # Remove BUILD_TUPLE+UNPACK_SEQUENCE
            self.block[start : start + 2] = ()
            self.index -= 2
            self.const_stack.clear()
            return

        if instr.arg == 1:
            # Replace BUILD_TUPLE 1 + UNPACK_SEQUENCE 1 with NOP
            del self.block[self.index - 1 : self.index + 1]
        elif instr.arg == 2:
            # Replace BUILD_TUPLE 2 + UNPACK_SEQUENCE 2 with ROT_TWO
            rot2 = Instr("ROT_TWO", lineno=instr.lineno)
            self.block[self.index - 1 : self.index + 1] = (rot2,)
            self.index -= 1
            self.const_stack.clear()
        elif instr.arg == 3:
            # Replace BUILD_TUPLE 3 + UNPACK_SEQUENCE 3
            # with ROT_THREE + ROT_TWO
            rot3 = Instr("ROT_THREE", lineno=instr.lineno)
            rot2 = Instr("ROT_TWO", lineno=instr.lineno)
            self.block[self.index - 1 : self.index + 1] = (rot3, rot2)
            self.index -= 1
            self.const_stack.clear()

    def build_tuple(self, instr, container_type):
        if instr.arg > len(self.const_stack):
            return

        next_instr = self.get_next_instr("COMPARE_OP")
        if next_instr is None or next_instr.arg not in (Compare.IN, Compare.NOT_IN):
            return

        self.replace_container_of_consts(instr, container_type)
        return True

    def eval_BUILD_TUPLE(self, instr):
        if not instr.arg:
            return

        if instr.arg <= len(self.const_stack):
            self.replace_container_of_consts(instr, tuple)
        else:
            self.build_tuple_unpack_seq(instr)

    def eval_BUILD_LIST(self, instr):
        if not instr.arg:
            return

        if not self.build_tuple(instr, tuple):
            self.build_tuple_unpack_seq(instr)

    def eval_BUILD_SET(self, instr):
        if not instr.arg:
            return

        self.build_tuple(instr, frozenset)

    # Note: BUILD_SLICE is not optimized

    def eval_COMPARE_OP(self, instr):
        # Note: COMPARE_OP: 2 < 3 is not optimized

        try:
            new_arg = NOT_COMPARE[instr.arg]
        except KeyError:
            return

        if self.get_next_instr("UNARY_NOT") is None:
            return

        # not (a is b) -->  a is not b
        # not (a in b) -->  a not in b
        # not (a is not b) -->  a is b
        # not (a not in b) -->  a in b
        instr.arg = new_arg
        self.block[self.index - 1 : self.index + 1] = (instr,)

    def jump_if_or_pop(self, instr):
        # Simplify conditional jump to conditional jump where the
        # result of the first test implies the success of a similar
        # test or the failure of the opposite test.
        #
        # Arises in code like:
        # "if a and b:"
        # "if a or b:"
        # "a and b or c"
        # "(a and b) and c"
        #
        # x:JUMP_IF_FALSE_OR_POP y   y:JUMP_IF_FALSE_OR_POP z
        #    -->  x:JUMP_IF_FALSE_OR_POP z
        #
        # x:JUMP_IF_FALSE_OR_POP y   y:JUMP_IF_TRUE_OR_POP z
        #    -->  x:POP_JUMP_IF_FALSE y+3
        # where y+3 is the instruction following the second test.
        target_block = instr.arg
        try:
            target_instr = target_block[0]
        except IndexError:
            return

        if not target_instr.is_cond_jump():
            self.optimize_jump_to_cond_jump(instr)
            return

        if (target_instr.name in JUMPS_ON_TRUE) == (instr.name in JUMPS_ON_TRUE):
            # The second jump will be taken iff the first is.

            target2 = target_instr.arg
            # The current opcode inherits its target's stack behaviour
            instr.name = target_instr.name
            instr.arg = target2
            self.block[self.index - 1] = instr
            self.index -= 1
        else:
            # The second jump is not taken if the first is (so jump past it),
            # and all conditional jumps pop their argument when they're not
            # taken (so change the first jump to pop its argument when it's
            # taken).
            if instr.name in JUMPS_ON_TRUE:
                name = "POP_JUMP_IF_TRUE"
            else:
                name = "POP_JUMP_IF_FALSE"

            new_label = self.code.split_block(target_block, 1)

            instr.name = name
            instr.arg = new_label
            self.block[self.index - 1] = instr
            self.index -= 1

    def eval_JUMP_IF_FALSE_OR_POP(self, instr):
        self.jump_if_or_pop(instr)

    def eval_JUMP_IF_TRUE_OR_POP(self, instr):
        self.jump_if_or_pop(instr)

    def eval_NOP(self, instr):
        # Remove NOP
        del self.block[self.index - 1]
        self.index -= 1

    def optimize_jump_to_cond_jump(self, instr):
        # Replace jumps to unconditional jumps
        jump_label = instr.arg
        assert isinstance(jump_label, BasicBlock), jump_label

        try:
            target_instr = jump_label[0]
        except IndexError:
            return

        if instr.is_uncond_jump() and target_instr.name == "RETURN_VALUE":
            # Replace JUMP_ABSOLUTE => RETURN_VALUE with RETURN_VALUE
            self.block[self.index - 1] = target_instr

        elif target_instr.is_uncond_jump():
            # Replace JUMP_FORWARD t1 jumping to JUMP_FORWARD t2
            # with JUMP_ABSOLUTE t2
            jump_target2 = target_instr.arg

            name = instr.name
            if instr.name == "JUMP_FORWARD":
                name = "JUMP_ABSOLUTE"
            else:
                # FIXME: reimplement this check
                # if jump_target2 < 0:
                #    # No backward relative jumps
                #    return

                # FIXME: remove this workaround and implement comment code ^^
                if instr.opcode in opcode.hasjrel:
                    return

            instr.name = name
            instr.arg = jump_target2
            self.block[self.index - 1] = instr

    def optimize_jump(self, instr):
        if instr.is_uncond_jump() and self.index == len(self.block):
            # JUMP_ABSOLUTE at the end of a block which points to the
            # following block: remove the jump, link the current block
            # to the following block
            block_index = self.block_index
            target_block = instr.arg
            target_block_index = self.code.get_block_index(target_block)
            if target_block_index == block_index:
                del self.block[self.index - 1]
                self.block.next_block = target_block
                return

        self.optimize_jump_to_cond_jump(instr)

    def iterblock(self, block):
        self.block = block
        self.index = 0
        while self.index < len(block):
            instr = self.block[self.index]
            self.index += 1
            yield instr

    def optimize_block(self, block):
        self.const_stack.clear()
        self.in_consts = False

        for instr in self.iterblock(block):
            if not self.in_consts:
                self.const_stack.clear()
            self.in_consts = False

            meth_name = "eval_%s" % instr.name
            meth = getattr(self, meth_name, None)
            if meth is not None:
                meth(instr)
            elif instr.has_jump():
                self.optimize_jump(instr)

            # Note: Skipping over LOAD_CONST trueconst; POP_JUMP_IF_FALSE
            # <target> is not implemented, since it looks like the optimization
            # is never trigerred in practice. The compiler already optimizes if
            # and while statements.

    def remove_dead_blocks(self):
        # FIXME: remove empty blocks?

        used_blocks = {id(self.code[0])}
        for block in self.code:
            if block.next_block is not None:
                used_blocks.add(id(block.next_block))
            for instr in block:
                if isinstance(instr, Instr) and isinstance(instr.arg, BasicBlock):
                    used_blocks.add(id(instr.arg))

        block_index = 0
        while block_index < len(self.code):
            block = self.code[block_index]
            if id(block) not in used_blocks:
                del self.code[block_index]
            else:
                block_index += 1

        # FIXME: merge following blocks if block1 does not contain any
        # jump and block1.next_block is block2

    def optimize_cfg(self, cfg):
        self.code = cfg
        self.const_stack = []

        self.remove_dead_blocks()

        self.block_index = 0
        while self.block_index < len(self.code):
            block = self.code[self.block_index]
            self.block_index += 1
            self.optimize_block(block)

    def optimize(self, code_obj):
        bytecode = Bytecode.from_code(code_obj)
        cfg = ControlFlowGraph.from_bytecode(bytecode)

        self.optimize_cfg(cfg)

        bytecode = cfg.to_bytecode()
        code = bytecode.to_code()
        return code


# Code transformer for the PEP 511
class CodeTransformer:
    name = "pyopt"

    def code_transformer(self, code, context):
        if sys.flags.verbose:
            print("Optimize %s:%s: %s" % (code.co_filename, code.co_firstlineno, code.co_name))
        optimizer = PeepholeOptimizer()
        return optimizer.optimize(code)

# === NexusCore/openenv\Lib\site-packages\jedi\inference\gradual\typing.py ===
"""
We need to somehow work with the typing objects. Since the typing objects are
pretty bare we need to add all the Jedi customizations to make them work as
values.

This file deals with all the typing.py cases.
"""
import itertools

from jedi import debug
from jedi.inference.compiled import builtin_from_name, create_simple_object
from jedi.inference.base_value import ValueSet, NO_VALUES, Value, \
    LazyValueWrapper, ValueWrapper
from jedi.inference.lazy_value import LazyKnownValues
from jedi.inference.arguments import repack_with_argument_clinic
from jedi.inference.filters import FilterWrapper
from jedi.inference.names import NameWrapper, ValueName
from jedi.inference.value.klass import ClassMixin
from jedi.inference.gradual.base import BaseTypingValue, \
    BaseTypingClassWithGenerics, BaseTypingInstance
from jedi.inference.gradual.type_var import TypeVarClass
from jedi.inference.gradual.generics import LazyGenericManager, TupleGenericManager

_PROXY_CLASS_TYPES = 'Tuple Generic Protocol Callable Type'.split()
_TYPE_ALIAS_TYPES = {
    'List': 'builtins.list',
    'Dict': 'builtins.dict',
    'Set': 'builtins.set',
    'FrozenSet': 'builtins.frozenset',
    'ChainMap': 'collections.ChainMap',
    'Counter': 'collections.Counter',
    'DefaultDict': 'collections.defaultdict',
    'Deque': 'collections.deque',
}
_PROXY_TYPES = 'Optional Union ClassVar Annotated'.split()


class TypingModuleName(NameWrapper):
    def infer(self):
        return ValueSet(self._remap())

    def _remap(self):
        name = self.string_name
        inference_state = self.parent_context.inference_state
        try:
            actual = _TYPE_ALIAS_TYPES[name]
        except KeyError:
            pass
        else:
            yield TypeAlias.create_cached(
                inference_state, self.parent_context, self.tree_name, actual)
            return

        if name in _PROXY_CLASS_TYPES:
            yield ProxyTypingClassValue.create_cached(
                inference_state, self.parent_context, self.tree_name)
        elif name in _PROXY_TYPES:
            yield ProxyTypingValue.create_cached(
                inference_state, self.parent_context, self.tree_name)
        elif name == 'runtime':
            # We don't want anything here, not sure what this function is
            # supposed to do, since it just appears in the stubs and shouldn't
            # have any effects there (because it's never executed).
            return
        elif name == 'TypeVar':
            cls, = self._wrapped_name.infer()
            yield TypeVarClass.create_cached(inference_state, cls)
        elif name == 'Any':
            yield AnyClass.create_cached(
                inference_state, self.parent_context, self.tree_name)
        elif name == 'TYPE_CHECKING':
            # This is needed for e.g. imports that are only available for type
            # checking or are in cycles. The user can then check this variable.
            yield builtin_from_name(inference_state, 'True')
        elif name == 'overload':
            yield OverloadFunction.create_cached(
                inference_state, self.parent_context, self.tree_name)
        elif name == 'NewType':
            v, = self._wrapped_name.infer()
            yield NewTypeFunction.create_cached(inference_state, v)
        elif name == 'cast':
            cast_fn, = self._wrapped_name.infer()
            yield CastFunction.create_cached(inference_state, cast_fn)
        elif name == 'TypedDict':
            # TODO doesn't even exist in typeshed/typing.py, yet. But will be
            # added soon.
            yield TypedDictClass.create_cached(
                inference_state, self.parent_context, self.tree_name)
        else:
            # Not necessary, as long as we are not doing type checking:
            # no_type_check & no_type_check_decorator
            # Everything else shouldn't be relevant...
            yield from self._wrapped_name.infer()


class TypingModuleFilterWrapper(FilterWrapper):
    name_wrapper_class = TypingModuleName


class ProxyWithGenerics(BaseTypingClassWithGenerics):
    def execute_annotation(self):
        string_name = self._tree_name.value

        if string_name == 'Union':
            # This is kind of a special case, because we have Unions (in Jedi
            # ValueSets).
            return self.gather_annotation_classes().execute_annotation()
        elif string_name == 'Optional':
            # Optional is basically just saying it's either None or the actual
            # type.
            return self.gather_annotation_classes().execute_annotation() \
                | ValueSet([builtin_from_name(self.inference_state, 'None')])
        elif string_name == 'Type':
            # The type is actually already given in the index_value
            return self._generics_manager[0]
        elif string_name in ['ClassVar', 'Annotated']:
            # For now don't do anything here, ClassVars are always used.
            return self._generics_manager[0].execute_annotation()

        mapped = {
            'Tuple': Tuple,
            'Generic': Generic,
            'Protocol': Protocol,
            'Callable': Callable,
        }
        cls = mapped[string_name]
        return ValueSet([cls(
            self.parent_context,
            self,
            self._tree_name,
            generics_manager=self._generics_manager,
        )])

    def gather_annotation_classes(self):
        return ValueSet.from_sets(self._generics_manager.to_tuple())

    def _create_instance_with_generics(self, generics_manager):
        return ProxyWithGenerics(
            self.parent_context,
            self._tree_name,
            generics_manager
        )

    def infer_type_vars(self, value_set):
        annotation_generics = self.get_generics()

        if not annotation_generics:
            return {}

        annotation_name = self.py__name__()
        if annotation_name == 'Optional':
            # Optional[T] is equivalent to Union[T, None]. In Jedi unions
            # are represented by members within a ValueSet, so we extract
            # the T from the Optional[T] by removing the None value.
            none = builtin_from_name(self.inference_state, 'None')
            return annotation_generics[0].infer_type_vars(
                value_set.filter(lambda x: x != none),
            )

        return {}


class ProxyTypingValue(BaseTypingValue):
    index_class = ProxyWithGenerics

    def with_generics(self, generics_tuple):
        return self.index_class.create_cached(
            self.inference_state,
            self.parent_context,
            self._tree_name,
            generics_manager=TupleGenericManager(generics_tuple)
        )

    def py__getitem__(self, index_value_set, contextualized_node):
        return ValueSet(
            self.index_class.create_cached(
                self.inference_state,
                self.parent_context,
                self._tree_name,
                generics_manager=LazyGenericManager(
                    context_of_index=contextualized_node.context,
                    index_value=index_value,
                )
            ) for index_value in index_value_set
        )


class _TypingClassMixin(ClassMixin):
    def py__bases__(self):
        return [LazyKnownValues(
            self.inference_state.builtins_module.py__getattribute__('object')
        )]

    def get_metaclasses(self):
        return []

    @property
    def name(self):
        return ValueName(self, self._tree_name)


class TypingClassWithGenerics(ProxyWithGenerics, _TypingClassMixin):
    def infer_type_vars(self, value_set):
        type_var_dict = {}
        annotation_generics = self.get_generics()

        if not annotation_generics:
            return type_var_dict

        annotation_name = self.py__name__()
        if annotation_name == 'Type':
            return annotation_generics[0].infer_type_vars(
                # This is basically a trick to avoid extra code: We execute the
                # incoming classes to be able to use the normal code for type
                # var inference.
                value_set.execute_annotation(),
            )

        elif annotation_name == 'Callable':
            if len(annotation_generics) == 2:
                return annotation_generics[1].infer_type_vars(
                    value_set.execute_annotation(),
                )

        elif annotation_name == 'Tuple':
            tuple_annotation, = self.execute_annotation()
            return tuple_annotation.infer_type_vars(value_set)

        return type_var_dict

    def _create_instance_with_generics(self, generics_manager):
        return TypingClassWithGenerics(
            self.parent_context,
            self._tree_name,
            generics_manager
        )


class ProxyTypingClassValue(ProxyTypingValue, _TypingClassMixin):
    index_class = TypingClassWithGenerics


class TypeAlias(LazyValueWrapper):
    def __init__(self, parent_context, origin_tree_name, actual):
        self.inference_state = parent_context.inference_state
        self.parent_context = parent_context
        self._origin_tree_name = origin_tree_name
        self._actual = actual  # e.g. builtins.list

    @property
    def name(self):
        return ValueName(self, self._origin_tree_name)

    def py__name__(self):
        return self.name.string_name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self._actual)

    def _get_wrapped_value(self):
        module_name, class_name = self._actual.split('.')

        # TODO use inference_state.import_module?
        from jedi.inference.imports import Importer
        module, = Importer(
            self.inference_state, [module_name], self.inference_state.builtins_module
        ).follow()
        classes = module.py__getattribute__(class_name)
        # There should only be one, because it's code that we control.
        assert len(classes) == 1, classes
        cls = next(iter(classes))
        return cls

    def gather_annotation_classes(self):
        return ValueSet([self._get_wrapped_value()])

    def get_signatures(self):
        return []


class Callable(BaseTypingInstance):
    def py__call__(self, arguments):
        """
            def x() -> Callable[[Callable[..., _T]], _T]: ...
        """
        # The 0th index are the arguments.
        try:
            param_values = self._generics_manager[0]
            result_values = self._generics_manager[1]
        except IndexError:
            debug.warning('Callable[...] defined without two arguments')
            return NO_VALUES
        else:
            from jedi.inference.gradual.annotation import infer_return_for_callable
            return infer_return_for_callable(arguments, param_values, result_values)

    def py__get__(self, instance, class_value):
        return ValueSet([self])


class Tuple(BaseTypingInstance):
    def _is_homogenous(self):
        # To specify a variable-length tuple of homogeneous type, Tuple[T, ...]
        # is used.
        return self._generics_manager.is_homogenous_tuple()

    def py__simple_getitem__(self, index):
        if self._is_homogenous():
            return self._generics_manager.get_index_and_execute(0)
        else:
            if isinstance(index, int):
                return self._generics_manager.get_index_and_execute(index)

            debug.dbg('The getitem type on Tuple was %s' % index)
            return NO_VALUES

    def py__iter__(self, contextualized_node=None):
        if self._is_homogenous():
            yield LazyKnownValues(self._generics_manager.get_index_and_execute(0))
        else:
            for v in self._generics_manager.to_tuple():
                yield LazyKnownValues(v.execute_annotation())

    def py__getitem__(self, index_value_set, contextualized_node):
        if self._is_homogenous():
            return self._generics_manager.get_index_and_execute(0)

        return ValueSet.from_sets(
            self._generics_manager.to_tuple()
        ).execute_annotation()

    def _get_wrapped_value(self):
        tuple_, = self.inference_state.builtins_module \
            .py__getattribute__('tuple').execute_annotation()
        return tuple_

    @property
    def name(self):
        return self._wrapped_value.name

    def infer_type_vars(self, value_set):
        # Circular
        from jedi.inference.gradual.annotation import merge_pairwise_generics, merge_type_var_dicts

        value_set = value_set.filter(
            lambda x: x.py__name__().lower() == 'tuple',
        )

        if self._is_homogenous():
            # The parameter annotation is of the form `Tuple[T, ...]`,
            # so we treat the incoming tuple like a iterable sequence
            # rather than a positional container of elements.
            return self._class_value.get_generics()[0].infer_type_vars(
                value_set.merge_types_of_iterate(),
            )

        else:
            # The parameter annotation has only explicit type parameters
            # (e.g: `Tuple[T]`, `Tuple[T, U]`, `Tuple[T, U, V]`, etc.) so we
            # treat the incoming values as needing to match the annotation
            # exactly, just as we would for non-tuple annotations.

            type_var_dict = {}
            for element in value_set:
                try:
                    method = element.get_annotated_class_object
                except AttributeError:
                    # This might still happen, because the tuple name matching
                    # above is not 100% correct, so just catch the remaining
                    # cases here.
                    continue

                py_class = method()
                merge_type_var_dicts(
                    type_var_dict,
                    merge_pairwise_generics(self._class_value, py_class),
                )

            return type_var_dict


class Generic(BaseTypingInstance):
    pass


class Protocol(BaseTypingInstance):
    pass


class AnyClass(BaseTypingValue):
    def execute_annotation(self):
        debug.warning('Used Any - returned no results')
        return NO_VALUES


class OverloadFunction(BaseTypingValue):
    @repack_with_argument_clinic('func, /')
    def py__call__(self, func_value_set):
        # Just pass arguments through.
        return func_value_set


class NewTypeFunction(ValueWrapper):
    def py__call__(self, arguments):
        ordered_args = arguments.unpack()
        next(ordered_args, (None, None))
        _, second_arg = next(ordered_args, (None, None))
        if second_arg is None:
            return NO_VALUES
        return ValueSet(
            NewType(
                self.inference_state,
                contextualized_node.context,
                contextualized_node.node,
                second_arg.infer(),
            ) for contextualized_node in arguments.get_calling_nodes())


class NewType(Value):
    def __init__(self, inference_state, parent_context, tree_node, type_value_set):
        super().__init__(inference_state, parent_context)
        self._type_value_set = type_value_set
        self.tree_node = tree_node

    def py__class__(self):
        c, = self._type_value_set.py__class__()
        return c

    def py__call__(self, arguments):
        return self._type_value_set.execute_annotation()

    @property
    def name(self):
        from jedi.inference.compiled.value import CompiledValueName
        return CompiledValueName(self, 'NewType')

    def __repr__(self) -> str:
        return '<NewType: %s>%s' % (self.tree_node, self._type_value_set)


class CastFunction(ValueWrapper):
    @repack_with_argument_clinic('type, object, /')
    def py__call__(self, type_value_set, object_value_set):
        return type_value_set.execute_annotation()


class TypedDictClass(BaseTypingValue):
    """
    This class has no responsibilities and is just here to make sure that typed
    dicts can be identified.
    """


class TypedDict(LazyValueWrapper):
    """Represents the instance version of ``TypedDictClass``."""
    def __init__(self, definition_class):
        self.inference_state = definition_class.inference_state
        self.parent_context = definition_class.parent_context
        self.tree_node = definition_class.tree_node
        self._definition_class = definition_class

    @property
    def name(self):
        return ValueName(self, self.tree_node.name)

    def py__simple_getitem__(self, index):
        if isinstance(index, str):
            return ValueSet.from_sets(
                name.infer()
                for filter in self._definition_class.get_filters(is_instance=True)
                for name in filter.get(index)
            )
        return NO_VALUES

    def get_key_values(self):
        filtered_values = itertools.chain.from_iterable((
            f.values()
            for f in self._definition_class.get_filters(is_instance=True)
        ))
        return ValueSet({
            create_simple_object(self.inference_state, v.string_name)
            for v in filtered_values
        })

    def _get_wrapped_value(self):
        d, = self.inference_state.builtins_module.py__getattribute__('dict')
        result, = d.execute_with_values()
        return result

# === NexusCore/openenv\Lib\site-packages\litellm\types\guardrails.py ===
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from typing_extensions import Required, TypedDict

"""
Pydantic object defining how to set guardrails on litellm proxy

guardrails:
  - guardrail_name: "bedrock-pre-guard"
    litellm_params:
      guardrail: bedrock  # supported values: "aporia", "bedrock", "lakera"
      mode: "during_call"
      guardrailIdentifier: ff6ujrregl1q
      guardrailVersion: "DRAFT"
      default_on: true
"""


class SupportedGuardrailIntegrations(Enum):
    APORIA = "aporia"
    BEDROCK = "bedrock"
    GURDRAILS_AI = "guardrails_ai"
    LAKERA = "lakera"
    LAKERA_V2 = "lakera_v2"
    PRESIDIO = "presidio"
    HIDE_SECRETS = "hide-secrets"
    AIM = "aim"
    PANGEA = "pangea"
    LASSO = "lasso"


class Role(Enum):
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"


default_roles = [Role.SYSTEM, Role.ASSISTANT, Role.USER]


class GuardrailItemSpec(TypedDict, total=False):
    callbacks: Required[List[str]]
    default_on: bool
    logging_only: Optional[bool]
    enabled_roles: Optional[List[Role]]
    callback_args: Dict[str, Dict]


class GuardrailItem(BaseModel):
    callbacks: List[str]
    default_on: bool
    logging_only: Optional[bool]
    guardrail_name: str
    callback_args: Dict[str, Dict]
    enabled_roles: Optional[List[Role]]

    model_config = ConfigDict(use_enum_values=True)

    def __init__(
        self,
        callbacks: List[str],
        guardrail_name: str,
        default_on: bool = False,
        logging_only: Optional[bool] = None,
        enabled_roles: Optional[List[Role]] = default_roles,
        callback_args: Dict[str, Dict] = {},
    ):
        super().__init__(
            callbacks=callbacks,
            default_on=default_on,
            logging_only=logging_only,
            guardrail_name=guardrail_name,
            enabled_roles=enabled_roles,
            callback_args=callback_args,
        )


# Define the TypedDicts
class LakeraCategoryThresholds(TypedDict, total=False):
    prompt_injection: float
    jailbreak: float


class PiiAction(str, Enum):
    BLOCK = "BLOCK"
    MASK = "MASK"


class PiiEntityCategory(str, Enum):
    GENERAL = "General"
    FINANCE = "Finance"
    USA = "USA"
    UK = "UK"
    SPAIN = "Spain"
    ITALY = "Italy"
    POLAND = "Poland"
    SINGAPORE = "Singapore"
    AUSTRALIA = "Australia"
    INDIA = "India"
    FINLAND = "Finland"


class PiiEntityType(str, Enum):
    # General
    CREDIT_CARD = "CREDIT_CARD"
    CRYPTO = "CRYPTO"
    DATE_TIME = "DATE_TIME"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    IBAN_CODE = "IBAN_CODE"
    IP_ADDRESS = "IP_ADDRESS"
    NRP = "NRP"
    LOCATION = "LOCATION"
    PERSON = "PERSON"
    PHONE_NUMBER = "PHONE_NUMBER"
    MEDICAL_LICENSE = "MEDICAL_LICENSE"
    URL = "URL"
    # USA
    US_BANK_NUMBER = "US_BANK_NUMBER"
    US_DRIVER_LICENSE = "US_DRIVER_LICENSE"
    US_ITIN = "US_ITIN"
    US_PASSPORT = "US_PASSPORT"
    US_SSN = "US_SSN"
    # UK
    UK_NHS = "UK_NHS"
    UK_NINO = "UK_NINO"
    # Spain
    ES_NIF = "ES_NIF"
    ES_NIE = "ES_NIE"
    # Italy
    IT_FISCAL_CODE = "IT_FISCAL_CODE"
    IT_DRIVER_LICENSE = "IT_DRIVER_LICENSE"
    IT_VAT_CODE = "IT_VAT_CODE"
    IT_PASSPORT = "IT_PASSPORT"
    IT_IDENTITY_CARD = "IT_IDENTITY_CARD"
    # Poland
    PL_PESEL = "PL_PESEL"
    # Singapore
    SG_NRIC_FIN = "SG_NRIC_FIN"
    SG_UEN = "SG_UEN"
    # Australia
    AU_ABN = "AU_ABN"
    AU_ACN = "AU_ACN"
    AU_TFN = "AU_TFN"
    AU_MEDICARE = "AU_MEDICARE"
    # India
    IN_PAN = "IN_PAN"
    IN_AADHAAR = "IN_AADHAAR"
    IN_VEHICLE_REGISTRATION = "IN_VEHICLE_REGISTRATION"
    IN_VOTER = "IN_VOTER"
    IN_PASSPORT = "IN_PASSPORT"
    # Finland
    FI_PERSONAL_IDENTITY_CODE = "FI_PERSONAL_IDENTITY_CODE"


# Define mappings of PII entity types by category
PII_ENTITY_CATEGORIES_MAP = {
    PiiEntityCategory.GENERAL: [
        PiiEntityType.DATE_TIME,
        PiiEntityType.EMAIL_ADDRESS,
        PiiEntityType.IP_ADDRESS,
        PiiEntityType.NRP,
        PiiEntityType.LOCATION,
        PiiEntityType.PERSON,
        PiiEntityType.PHONE_NUMBER,
        PiiEntityType.MEDICAL_LICENSE,
        PiiEntityType.URL,
    ],
    PiiEntityCategory.FINANCE: [
        PiiEntityType.CREDIT_CARD,
        PiiEntityType.CRYPTO,
        PiiEntityType.IBAN_CODE,
    ],
    PiiEntityCategory.USA: [
        PiiEntityType.US_BANK_NUMBER,
        PiiEntityType.US_DRIVER_LICENSE,
        PiiEntityType.US_ITIN,
        PiiEntityType.US_PASSPORT,
        PiiEntityType.US_SSN,
    ],
    PiiEntityCategory.UK: [PiiEntityType.UK_NHS, PiiEntityType.UK_NINO],
    PiiEntityCategory.SPAIN: [PiiEntityType.ES_NIF, PiiEntityType.ES_NIE],
    PiiEntityCategory.ITALY: [
        PiiEntityType.IT_FISCAL_CODE,
        PiiEntityType.IT_DRIVER_LICENSE,
        PiiEntityType.IT_VAT_CODE,
        PiiEntityType.IT_PASSPORT,
        PiiEntityType.IT_IDENTITY_CARD,
    ],
    PiiEntityCategory.POLAND: [PiiEntityType.PL_PESEL],
    PiiEntityCategory.SINGAPORE: [PiiEntityType.SG_NRIC_FIN, PiiEntityType.SG_UEN],
    PiiEntityCategory.AUSTRALIA: [
        PiiEntityType.AU_ABN,
        PiiEntityType.AU_ACN,
        PiiEntityType.AU_TFN,
        PiiEntityType.AU_MEDICARE,
    ],
    PiiEntityCategory.INDIA: [
        PiiEntityType.IN_PAN,
        PiiEntityType.IN_AADHAAR,
        PiiEntityType.IN_VEHICLE_REGISTRATION,
        PiiEntityType.IN_VOTER,
        PiiEntityType.IN_PASSPORT,
    ],
    PiiEntityCategory.FINLAND: [PiiEntityType.FI_PERSONAL_IDENTITY_CODE],
}


class PiiEntityCategoryMap(TypedDict):
    category: PiiEntityCategory
    entities: List[PiiEntityType]


class GuardrailParamUITypes(str, Enum):
    BOOL = "bool"
    STR = "str"


class PresidioPresidioConfigModelUserInterface(BaseModel):
    """Configuration parameters for the Presidio PII masking guardrail on LiteLLM UI"""

    presidio_analyzer_api_base: Optional[str] = Field(
        default=None,
        description="Base URL for the Presidio analyzer API",
    )
    presidio_anonymizer_api_base: Optional[str] = Field(
        default=None,
        description="Base URL for the Presidio anonymizer API",
    )
    output_parse_pii: Optional[bool] = Field(
        default=None,
        description="When True, LiteLLM will replace the masked text with the original text in the response",
        # extra param to let the ui know this is a boolean
        json_schema_extra={"ui_type": GuardrailParamUITypes.BOOL},
    )
    presidio_language: Optional[str] = Field(
        default="en",
        description="Language code for Presidio PII analysis (e.g., 'en', 'de', 'es', 'fr')",
    )


class PresidioConfigModel(PresidioPresidioConfigModelUserInterface):
    """Configuration parameters for the Presidio PII masking guardrail"""

    pii_entities_config: Optional[Dict[PiiEntityType, PiiAction]] = Field(
        default=None, description="Configuration for PII entity types and actions"
    )
    presidio_ad_hoc_recognizers: Optional[str] = Field(
        default=None,
        description="Path to a JSON file containing ad-hoc recognizers for Presidio",
    )
    mock_redacted_text: Optional[dict] = Field(
        default=None, description="Mock redacted text for testing"
    )


class BedrockGuardrailConfigModel(BaseModel):
    """Configuration parameters for the AWS Bedrock guardrail"""

    guardrailIdentifier: Optional[str] = Field(
        default=None, description="The ID of your guardrail on Bedrock"
    )
    guardrailVersion: Optional[str] = Field(
        default=None,
        description="The version of your Bedrock guardrail (e.g., DRAFT or version number)",
    )
    aws_region_name: Optional[str] = Field(
        default=None, description="AWS region where your guardrail is deployed"
    )
    aws_access_key_id: Optional[str] = Field(
        default=None, description="AWS access key ID for authentication"
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None, description="AWS secret access key for authentication"
    )
    aws_session_token: Optional[str] = Field(
        default=None, description="AWS session token for temporary credentials"
    )
    aws_session_name: Optional[str] = Field(
        default=None, description="Name of the AWS session"
    )
    aws_profile_name: Optional[str] = Field(
        default=None, description="AWS profile name for credential retrieval"
    )
    aws_role_name: Optional[str] = Field(
        default=None, description="AWS role name for assuming roles"
    )
    aws_web_identity_token: Optional[str] = Field(
        default=None, description="Web identity token for AWS role assumption"
    )
    aws_sts_endpoint: Optional[str] = Field(
        default=None, description="AWS STS endpoint URL"
    )
    aws_bedrock_runtime_endpoint: Optional[str] = Field(
        default=None, description="AWS Bedrock runtime endpoint URL"
    )


class LakeraV2GuardrailConfigModel(BaseModel):
    """Configuration parameters for the Lakera AI v2 guardrail"""

    api_key: Optional[str] = Field(
        default=None, description="API key for the Lakera AI service"
    )
    api_base: Optional[str] = Field(
        default=None, description="Base URL for the Lakera AI API"
    )
    project_id: Optional[str] = Field(
        default=None, description="Project ID for the Lakera AI project"
    )
    payload: Optional[bool] = Field(
        default=True, description="Whether to include payload in the response"
    )
    breakdown: Optional[bool] = Field(
        default=True, description="Whether to include breakdown in the response"
    )
    metadata: Optional[Dict] = Field(
        default=None, description="Additional metadata to include in the request"
    )
    dev_info: Optional[bool] = Field(
        default=True,
        description="Whether to include developer information in the response",
    )


class LassoGuardrailConfigModel(BaseModel):
    """Configuration parameters for the Lasso guardrail"""

    lasso_user_id: Optional[str] = Field(
        default=None, description="User ID for the Lasso guardrail"
    )
    lasso_conversation_id: Optional[str] = Field(
        default=None, description="Conversation ID for the Lasso guardrail"
    )


class LitellmParams(
    PresidioConfigModel,
    BedrockGuardrailConfigModel,
    LakeraV2GuardrailConfigModel,
    LassoGuardrailConfigModel,
):
    guardrail: str = Field(description="The type of guardrail integration to use")
    mode: Union[str, List[str]] = Field(
        description="When to apply the guardrail (pre_call, post_call, during_call, logging_only)"
    )
    api_key: Optional[str] = Field(
        default=None, description="API key for the guardrail service"
    )
    api_base: Optional[str] = Field(
        default=None, description="Base URL for the guardrail service API"
    )

    # Lakera specific params
    category_thresholds: Optional[LakeraCategoryThresholds] = Field(
        default=None,
        description="Threshold configuration for Lakera guardrail categories",
    )

    # hide secrets params
    detect_secrets_config: Optional[dict] = Field(
        default=None, description="Configuration for detect-secrets guardrail"
    )

    # guardrails ai params
    guard_name: Optional[str] = Field(
        default=None, description="Name of the guardrail in guardrails.ai"
    )
    default_on: Optional[bool] = Field(
        default=None, description="Whether the guardrail is enabled by default"
    )

    ################## PII control params #################
    ########################################################
    mask_request_content: Optional[bool] = Field(
        default=None,
        description="Will mask request content if guardrail makes any changes",
    )
    mask_response_content: Optional[bool] = Field(
        default=None,
        description="Will mask response content if guardrail makes any changes",
    )

    # pangea params
    pangea_input_recipe: Optional[str] = Field(
        default=None, description="Recipe for input (LLM request)"
    )

    pangea_output_recipe: Optional[str] = Field(
        default=None, description="Recipe for output (LLM response)"
    )


class Guardrail(TypedDict, total=False):
    guardrail_id: Optional[str]
    guardrail_name: str
    litellm_params: LitellmParams
    guardrail_info: Optional[Dict]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class guardrailConfig(TypedDict):
    guardrails: List[Guardrail]


class GuardrailEventHooks(str, Enum):
    pre_call = "pre_call"
    post_call = "post_call"
    during_call = "during_call"
    logging_only = "logging_only"


class DynamicGuardrailParams(TypedDict):
    extra_body: Dict[str, Any]


class GuardrailInfoLiteLLMParamsResponse(BaseModel):
    """The returned LiteLLM Params object for /guardrails/list"""

    guardrail: str
    mode: Union[str, List[str]]
    default_on: Optional[bool] = False
    pii_entities_config: Optional[Dict[PiiEntityType, PiiAction]] = None

    def __init__(self, **kwargs):
        default_on = kwargs.get("default_on")
        if default_on is None:
            default_on = False

        super().__init__(**kwargs)


class GuardrailInfoResponse(BaseModel):
    guardrail_id: Optional[str] = None
    guardrail_name: str
    litellm_params: Optional[GuardrailInfoLiteLLMParamsResponse] = None
    guardrail_info: Optional[Dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    guardrail_definition_location: Literal["config", "db"] = "config"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ListGuardrailsResponse(BaseModel):
    guardrails: List[GuardrailInfoResponse]


class GuardrailUIAddGuardrailSettings(BaseModel):
    supported_entities: List[PiiEntityType]
    supported_actions: List[PiiAction]
    supported_modes: List[GuardrailEventHooks]
    pii_entity_categories: List[PiiEntityCategoryMap]


class PresidioPerRequestConfig(BaseModel):
    """
    presdio params that can be controlled per request, api key
    """

    language: Optional[str] = None
    entities: Optional[List[PiiEntityType]] = None


class ApplyGuardrailRequest(BaseModel):
    guardrail_name: str
    text: str
    language: Optional[str] = None
    entities: Optional[List[PiiEntityType]] = None


class ApplyGuardrailResponse(BaseModel):
    response_text: str


class PatchGuardrailLitellmParams(BaseModel):
    default_on: Optional[bool] = None
    pii_entities_config: Optional[Dict[PiiEntityType, PiiAction]] = None


class PatchGuardrailRequest(BaseModel):
    guardrail_name: Optional[str] = None
    litellm_params: Optional[PatchGuardrailLitellmParams] = None
    guardrail_info: Optional[Dict[str, Any]] = None

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\nkjp.py ===
# Natural Language Toolkit: NKJP Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Gabriela Kaczka
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import functools
import os
import re
import tempfile

from nltk.corpus.reader.util import concat
from nltk.corpus.reader.xmldocs import XMLCorpusReader, XMLCorpusView


def _parse_args(fun):
    """
    Wraps function arguments:
    if fileids not specified then function set NKJPCorpusReader paths.
    """

    @functools.wraps(fun)
    def decorator(self, fileids=None, **kwargs):
        if not fileids:
            fileids = self._paths
        return fun(self, fileids, **kwargs)

    return decorator


class NKJPCorpusReader(XMLCorpusReader):
    WORDS_MODE = 0
    SENTS_MODE = 1
    HEADER_MODE = 2
    RAW_MODE = 3

    def __init__(self, root, fileids=".*"):
        """
        Corpus reader designed to work with National Corpus of Polish.
        See http://nkjp.pl/ for more details about NKJP.
        use example:
        import nltk
        import nkjp
        from nkjp import NKJPCorpusReader
        x = NKJPCorpusReader(root='/home/USER/nltk_data/corpora/nkjp/', fileids='') # obtain the whole corpus
        x.header()
        x.raw()
        x.words()
        x.tagged_words(tags=['subst', 'comp'])  #Link to find more tags: nkjp.pl/poliqarp/help/ense2.html
        x.sents()
        x = NKJPCorpusReader(root='/home/USER/nltk_data/corpora/nkjp/', fileids='Wilk*') # obtain particular file(s)
        x.header(fileids=['WilkDom', '/home/USER/nltk_data/corpora/nkjp/WilkWilczy'])
        x.tagged_words(fileids=['WilkDom', '/home/USER/nltk_data/corpora/nkjp/WilkWilczy'], tags=['subst', 'comp'])
        """
        if isinstance(fileids, str):
            XMLCorpusReader.__init__(self, root, fileids + ".*/header.xml")
        else:
            XMLCorpusReader.__init__(
                self, root, [fileid + "/header.xml" for fileid in fileids]
            )
        self._paths = self.get_paths()

    def get_paths(self):
        return [
            os.path.join(str(self._root), f.split("header.xml")[0])
            for f in self._fileids
        ]

    def fileids(self):
        """
        Returns a list of file identifiers for the fileids that make up
        this corpus.
        """
        return [f.split("header.xml")[0] for f in self._fileids]

    def _view(self, filename, tags=None, **kwargs):
        """
        Returns a view specialised for use with particular corpus file.
        """
        mode = kwargs.pop("mode", NKJPCorpusReader.WORDS_MODE)
        if mode is NKJPCorpusReader.WORDS_MODE:
            return NKJPCorpus_Morph_View(filename, tags=tags)
        elif mode is NKJPCorpusReader.SENTS_MODE:
            return NKJPCorpus_Segmentation_View(filename, tags=tags)
        elif mode is NKJPCorpusReader.HEADER_MODE:
            return NKJPCorpus_Header_View(filename, tags=tags)
        elif mode is NKJPCorpusReader.RAW_MODE:
            return NKJPCorpus_Text_View(
                filename, tags=tags, mode=NKJPCorpus_Text_View.RAW_MODE
            )

        else:
            raise NameError("No such mode!")

    def add_root(self, fileid):
        """
        Add root if necessary to specified fileid.
        """
        if self.root in fileid:
            return fileid
        return self.root + fileid

    @_parse_args
    def header(self, fileids=None, **kwargs):
        """
        Returns header(s) of specified fileids.
        """
        return concat(
            [
                self._view(
                    self.add_root(fileid), mode=NKJPCorpusReader.HEADER_MODE, **kwargs
                ).handle_query()
                for fileid in fileids
            ]
        )

    @_parse_args
    def sents(self, fileids=None, **kwargs):
        """
        Returns sentences in specified fileids.
        """
        return concat(
            [
                self._view(
                    self.add_root(fileid), mode=NKJPCorpusReader.SENTS_MODE, **kwargs
                ).handle_query()
                for fileid in fileids
            ]
        )

    @_parse_args
    def words(self, fileids=None, **kwargs):
        """
        Returns words in specified fileids.
        """

        return concat(
            [
                self._view(
                    self.add_root(fileid), mode=NKJPCorpusReader.WORDS_MODE, **kwargs
                ).handle_query()
                for fileid in fileids
            ]
        )

    @_parse_args
    def tagged_words(self, fileids=None, **kwargs):
        """
        Call with specified tags as a list, e.g. tags=['subst', 'comp'].
        Returns tagged words in specified fileids.
        """
        tags = kwargs.pop("tags", [])
        return concat(
            [
                self._view(
                    self.add_root(fileid),
                    mode=NKJPCorpusReader.WORDS_MODE,
                    tags=tags,
                    **kwargs
                ).handle_query()
                for fileid in fileids
            ]
        )

    @_parse_args
    def raw(self, fileids=None, **kwargs):
        """
        Returns words in specified fileids.
        """
        return concat(
            [
                self._view(
                    self.add_root(fileid), mode=NKJPCorpusReader.RAW_MODE, **kwargs
                ).handle_query()
                for fileid in fileids
            ]
        )


class NKJPCorpus_Header_View(XMLCorpusView):
    def __init__(self, filename, **kwargs):
        """
        HEADER_MODE
        A stream backed corpus view specialized for use with
        header.xml files in NKJP corpus.
        """
        self.tagspec = ".*/sourceDesc$"
        XMLCorpusView.__init__(self, filename + "header.xml", self.tagspec)

    def handle_query(self):
        self._open()
        header = []
        while True:
            segm = XMLCorpusView.read_block(self, self._stream)
            if len(segm) == 0:
                break
            header.extend(segm)
        self.close()
        return header

    def handle_elt(self, elt, context):
        titles = elt.findall("bibl/title")
        title = []
        if titles:
            title = "\n".join(title.text.strip() for title in titles)

        authors = elt.findall("bibl/author")
        author = []
        if authors:
            author = "\n".join(author.text.strip() for author in authors)

        dates = elt.findall("bibl/date")
        date = []
        if dates:
            date = "\n".join(date.text.strip() for date in dates)

        publishers = elt.findall("bibl/publisher")
        publisher = []
        if publishers:
            publisher = "\n".join(publisher.text.strip() for publisher in publishers)

        idnos = elt.findall("bibl/idno")
        idno = []
        if idnos:
            idno = "\n".join(idno.text.strip() for idno in idnos)

        notes = elt.findall("bibl/note")
        note = []
        if notes:
            note = "\n".join(note.text.strip() for note in notes)

        return {
            "title": title,
            "author": author,
            "date": date,
            "publisher": publisher,
            "idno": idno,
            "note": note,
        }


class XML_Tool:
    """
    Helper class creating xml file to one without references to nkjp: namespace.
    That's needed because the XMLCorpusView assumes that one can find short substrings
    of XML that are valid XML, which is not true if a namespace is declared at top level
    """

    def __init__(self, root, filename):
        self.read_file = os.path.join(root, filename)
        self.write_file = tempfile.NamedTemporaryFile(delete=False)

    def build_preprocessed_file(self):
        try:
            fr = open(self.read_file)
            fw = self.write_file
            line = " "
            while len(line):
                line = fr.readline()
                x = re.split(r"nkjp:[^ ]* ", line)  # in all files
                ret = " ".join(x)
                x = re.split("<nkjp:paren>", ret)  # in ann_segmentation.xml
                ret = " ".join(x)
                x = re.split("</nkjp:paren>", ret)  # in ann_segmentation.xml
                ret = " ".join(x)
                x = re.split("<choice>", ret)  # in ann_segmentation.xml
                ret = " ".join(x)
                x = re.split("</choice>", ret)  # in ann_segmentation.xml
                ret = " ".join(x)
                fw.write(ret)
            fr.close()
            fw.close()
            return self.write_file.name
        except Exception as e:
            self.remove_preprocessed_file()
            raise Exception from e

    def remove_preprocessed_file(self):
        os.remove(self.write_file.name)


class NKJPCorpus_Segmentation_View(XMLCorpusView):
    """
    A stream backed corpus view specialized for use with
    ann_segmentation.xml files in NKJP corpus.
    """

    def __init__(self, filename, **kwargs):
        self.tagspec = ".*p/.*s"
        # intersperse NKJPCorpus_Text_View
        self.text_view = NKJPCorpus_Text_View(
            filename, mode=NKJPCorpus_Text_View.SENTS_MODE
        )
        self.text_view.handle_query()
        # xml preprocessing
        self.xml_tool = XML_Tool(filename, "ann_segmentation.xml")
        # base class init
        XMLCorpusView.__init__(
            self, self.xml_tool.build_preprocessed_file(), self.tagspec
        )

    def get_segm_id(self, example_word):
        return example_word.split("(")[1].split(",")[0]

    def get_sent_beg(self, beg_word):
        # returns index of beginning letter in sentence
        return int(beg_word.split(",")[1])

    def get_sent_end(self, end_word):
        # returns index of end letter in sentence
        splitted = end_word.split(")")[0].split(",")
        return int(splitted[1]) + int(splitted[2])

    def get_sentences(self, sent_segm):
        # returns one sentence
        id = self.get_segm_id(sent_segm[0])
        segm = self.text_view.segm_dict[id]  # text segment
        beg = self.get_sent_beg(sent_segm[0])
        end = self.get_sent_end(sent_segm[len(sent_segm) - 1])
        return segm[beg:end]

    def remove_choice(self, segm):
        ret = []
        prev_txt_end = -1
        prev_txt_nr = -1
        for word in segm:
            txt_nr = self.get_segm_id(word)
            # get increasing sequence of ids: in case of choice get first possibility
            if self.get_sent_beg(word) > prev_txt_end - 1 or prev_txt_nr != txt_nr:
                ret.append(word)
                prev_txt_end = self.get_sent_end(word)
            prev_txt_nr = txt_nr

        return ret

    def handle_query(self):
        try:
            self._open()
            sentences = []
            while True:
                sent_segm = XMLCorpusView.read_block(self, self._stream)
                if len(sent_segm) == 0:
                    break
                for segm in sent_segm:
                    segm = self.remove_choice(segm)
                    sentences.append(self.get_sentences(segm))
            self.close()
            self.xml_tool.remove_preprocessed_file()
            return sentences
        except Exception as e:
            self.xml_tool.remove_preprocessed_file()
            raise Exception from e

    def handle_elt(self, elt, context):
        ret = []
        for seg in elt:
            ret.append(seg.get("corresp"))
        return ret


class NKJPCorpus_Text_View(XMLCorpusView):
    """
    A stream backed corpus view specialized for use with
    text.xml files in NKJP corpus.
    """

    SENTS_MODE = 0
    RAW_MODE = 1

    def __init__(self, filename, **kwargs):
        self.mode = kwargs.pop("mode", 0)
        self.tagspec = ".*/div/ab"
        self.segm_dict = dict()
        # xml preprocessing
        self.xml_tool = XML_Tool(filename, "text.xml")
        # base class init
        XMLCorpusView.__init__(
            self, self.xml_tool.build_preprocessed_file(), self.tagspec
        )

    def handle_query(self):
        try:
            self._open()
            x = self.read_block(self._stream)
            self.close()
            self.xml_tool.remove_preprocessed_file()
            return x
        except Exception as e:
            self.xml_tool.remove_preprocessed_file()
            raise Exception from e

    def read_block(self, stream, tagspec=None, elt_handler=None):
        """
        Returns text as a list of sentences.
        """
        txt = []
        while True:
            segm = XMLCorpusView.read_block(self, stream)
            if len(segm) == 0:
                break
            for part in segm:
                txt.append(part)

        return [" ".join([segm for segm in txt])]

    def get_segm_id(self, elt):
        for attr in elt.attrib:
            if attr.endswith("id"):
                return elt.get(attr)

    def handle_elt(self, elt, context):
        # fill dictionary to use later in sents mode
        if self.mode is NKJPCorpus_Text_View.SENTS_MODE:
            self.segm_dict[self.get_segm_id(elt)] = elt.text
        return elt.text


class NKJPCorpus_Morph_View(XMLCorpusView):
    """
    A stream backed corpus view specialized for use with
    ann_morphosyntax.xml files in NKJP corpus.
    """

    def __init__(self, filename, **kwargs):
        self.tags = kwargs.pop("tags", None)
        self.tagspec = ".*/seg/fs"
        self.xml_tool = XML_Tool(filename, "ann_morphosyntax.xml")
        XMLCorpusView.__init__(
            self, self.xml_tool.build_preprocessed_file(), self.tagspec
        )

    def handle_query(self):
        try:
            self._open()
            words = []
            while True:
                segm = XMLCorpusView.read_block(self, self._stream)
                if len(segm) == 0:
                    break
                for part in segm:
                    if part is not None:
                        words.append(part)
            self.close()
            self.xml_tool.remove_preprocessed_file()
            return words
        except Exception as e:
            self.xml_tool.remove_preprocessed_file()
            raise Exception from e

    def handle_elt(self, elt, context):
        word = ""
        flag = False
        is_not_interp = True
        # if tags not specified, then always return word
        if self.tags is None:
            flag = True

        for child in elt:
            # get word
            if "name" in child.keys() and child.attrib["name"] == "orth":
                for symbol in child:
                    if symbol.tag == "string":
                        word = symbol.text
            elif "name" in child.keys() and child.attrib["name"] == "interps":
                for symbol in child:
                    if "type" in symbol.keys() and symbol.attrib["type"] == "lex":
                        for symbol2 in symbol:
                            if (
                                "name" in symbol2.keys()
                                and symbol2.attrib["name"] == "ctag"
                            ):
                                for symbol3 in symbol2:
                                    if (
                                        "value" in symbol3.keys()
                                        and self.tags is not None
                                        and symbol3.attrib["value"] in self.tags
                                    ):
                                        flag = True
                                    elif (
                                        "value" in symbol3.keys()
                                        and symbol3.attrib["value"] == "interp"
                                    ):
                                        is_not_interp = False
        if flag and is_not_interp:
            return word

# === NexusCore/openenv\Lib\site-packages\numpy\_utils\_pep440.py ===
"""Utility to compare pep440 compatible version strings.

The LooseVersion and StrictVersion classes that distutils provides don't
work; they don't recognize anything like alpha/beta/rc/dev versions.
"""

# Copyright (c) Donald Stufft and individual contributors.
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.

#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import collections
import itertools
import re

__all__ = [
    "parse", "Version", "LegacyVersion", "InvalidVersion", "VERSION_PATTERN",
]


# BEGIN packaging/_structures.py


class Infinity:
    def __repr__(self):
        return "Infinity"

    def __hash__(self):
        return hash(repr(self))

    def __lt__(self, other):
        return False

    def __le__(self, other):
        return False

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __ne__(self, other):
        return not isinstance(other, self.__class__)

    def __gt__(self, other):
        return True

    def __ge__(self, other):
        return True

    def __neg__(self):
        return NegativeInfinity


Infinity = Infinity()


class NegativeInfinity:
    def __repr__(self):
        return "-Infinity"

    def __hash__(self):
        return hash(repr(self))

    def __lt__(self, other):
        return True

    def __le__(self, other):
        return True

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __ne__(self, other):
        return not isinstance(other, self.__class__)

    def __gt__(self, other):
        return False

    def __ge__(self, other):
        return False

    def __neg__(self):
        return Infinity


# BEGIN packaging/version.py


NegativeInfinity = NegativeInfinity()

_Version = collections.namedtuple(
    "_Version",
    ["epoch", "release", "dev", "pre", "post", "local"],
)


def parse(version):
    """
    Parse the given version string and return either a :class:`Version` object
    or a :class:`LegacyVersion` object depending on if the given version is
    a valid PEP 440 version or a legacy version.
    """
    try:
        return Version(version)
    except InvalidVersion:
        return LegacyVersion(version)


class InvalidVersion(ValueError):
    """
    An invalid version was found, users should refer to PEP 440.
    """


class _BaseVersion:

    def __hash__(self):
        return hash(self._key)

    def __lt__(self, other):
        return self._compare(other, lambda s, o: s < o)

    def __le__(self, other):
        return self._compare(other, lambda s, o: s <= o)

    def __eq__(self, other):
        return self._compare(other, lambda s, o: s == o)

    def __ge__(self, other):
        return self._compare(other, lambda s, o: s >= o)

    def __gt__(self, other):
        return self._compare(other, lambda s, o: s > o)

    def __ne__(self, other):
        return self._compare(other, lambda s, o: s != o)

    def _compare(self, other, method):
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return method(self._key, other._key)


class LegacyVersion(_BaseVersion):

    def __init__(self, version):
        self._version = str(version)
        self._key = _legacy_cmpkey(self._version)

    def __str__(self):
        return self._version

    def __repr__(self):
        return f"<LegacyVersion({str(self)!r})>"

    @property
    def public(self):
        return self._version

    @property
    def base_version(self):
        return self._version

    @property
    def local(self):
        return None

    @property
    def is_prerelease(self):
        return False

    @property
    def is_postrelease(self):
        return False


_legacy_version_component_re = re.compile(
    r"(\d+ | [a-z]+ | \.| -)", re.VERBOSE,
)

_legacy_version_replacement_map = {
    "pre": "c", "preview": "c", "-": "final-", "rc": "c", "dev": "@",
}


def _parse_version_parts(s):
    for part in _legacy_version_component_re.split(s):
        part = _legacy_version_replacement_map.get(part, part)

        if not part or part == ".":
            continue

        if part[:1] in "0123456789":
            # pad for numeric comparison
            yield part.zfill(8)
        else:
            yield "*" + part

    # ensure that alpha/beta/candidate are before final
    yield "*final"


def _legacy_cmpkey(version):
    # We hardcode an epoch of -1 here. A PEP 440 version can only have an epoch
    # greater than or equal to 0. This will effectively put the LegacyVersion,
    # which uses the defacto standard originally implemented by setuptools,
    # as before all PEP 440 versions.
    epoch = -1

    # This scheme is taken from pkg_resources.parse_version setuptools prior to
    # its adoption of the packaging library.
    parts = []
    for part in _parse_version_parts(version.lower()):
        if part.startswith("*"):
            # remove "-" before a prerelease tag
            if part < "*final":
                while parts and parts[-1] == "*final-":
                    parts.pop()

            # remove trailing zeros from each series of numeric parts
            while parts and parts[-1] == "00000000":
                parts.pop()

        parts.append(part)
    parts = tuple(parts)

    return epoch, parts


# Deliberately not anchored to the start and end of the string, to make it
# easier for 3rd party code to reuse
VERSION_PATTERN = r"""
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_\.]?
            (?P<pre_l>(a|b|c|rc|alpha|beta|pre|preview))
            [-_\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\.]?
                (?P<post_l>post|rev|r)
                [-_\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\.]?
            (?P<dev_l>dev)
            [-_\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
"""


class Version(_BaseVersion):

    _regex = re.compile(
        r"^\s*" + VERSION_PATTERN + r"\s*$",
        re.VERBOSE | re.IGNORECASE,
    )

    def __init__(self, version):
        # Validate the version and parse it into pieces
        match = self._regex.search(version)
        if not match:
            raise InvalidVersion(f"Invalid version: '{version}'")

        # Store the parsed out pieces of the version
        self._version = _Version(
            epoch=int(match.group("epoch")) if match.group("epoch") else 0,
            release=tuple(int(i) for i in match.group("release").split(".")),
            pre=_parse_letter_version(
                match.group("pre_l"),
                match.group("pre_n"),
            ),
            post=_parse_letter_version(
                match.group("post_l"),
                match.group("post_n1") or match.group("post_n2"),
            ),
            dev=_parse_letter_version(
                match.group("dev_l"),
                match.group("dev_n"),
            ),
            local=_parse_local_version(match.group("local")),
        )

        # Generate a key which will be used for sorting
        self._key = _cmpkey(
            self._version.epoch,
            self._version.release,
            self._version.pre,
            self._version.post,
            self._version.dev,
            self._version.local,
        )

    def __repr__(self):
        return f"<Version({str(self)!r})>"

    def __str__(self):
        parts = []

        # Epoch
        if self._version.epoch != 0:
            parts.append(f"{self._version.epoch}!")

        # Release segment
        parts.append(".".join(str(x) for x in self._version.release))

        # Pre-release
        if self._version.pre is not None:
            parts.append("".join(str(x) for x in self._version.pre))

        # Post-release
        if self._version.post is not None:
            parts.append(f".post{self._version.post[1]}")

        # Development release
        if self._version.dev is not None:
            parts.append(f".dev{self._version.dev[1]}")

        # Local version segment
        if self._version.local is not None:
            parts.append(
                f"+{'.'.join(str(x) for x in self._version.local)}"
            )

        return "".join(parts)

    @property
    def public(self):
        return str(self).split("+", 1)[0]

    @property
    def base_version(self):
        parts = []

        # Epoch
        if self._version.epoch != 0:
            parts.append(f"{self._version.epoch}!")

        # Release segment
        parts.append(".".join(str(x) for x in self._version.release))

        return "".join(parts)

    @property
    def local(self):
        version_string = str(self)
        if "+" in version_string:
            return version_string.split("+", 1)[1]

    @property
    def is_prerelease(self):
        return bool(self._version.dev or self._version.pre)

    @property
    def is_postrelease(self):
        return bool(self._version.post)


def _parse_letter_version(letter, number):
    if letter:
        # We assume there is an implicit 0 in a pre-release if there is
        # no numeral associated with it.
        if number is None:
            number = 0

        # We normalize any letters to their lower-case form
        letter = letter.lower()

        # We consider some words to be alternate spellings of other words and
        # in those cases we want to normalize the spellings to our preferred
        # spelling.
        if letter == "alpha":
            letter = "a"
        elif letter == "beta":
            letter = "b"
        elif letter in ["c", "pre", "preview"]:
            letter = "rc"
        elif letter in ["rev", "r"]:
            letter = "post"

        return letter, int(number)
    if not letter and number:
        # We assume that if we are given a number but not given a letter,
        # then this is using the implicit post release syntax (e.g., 1.0-1)
        letter = "post"

        return letter, int(number)


_local_version_seperators = re.compile(r"[\._-]")


def _parse_local_version(local):
    """
    Takes a string like abc.1.twelve and turns it into ("abc", 1, "twelve").
    """
    if local is not None:
        return tuple(
            part.lower() if not part.isdigit() else int(part)
            for part in _local_version_seperators.split(local)
        )


def _cmpkey(epoch, release, pre, post, dev, local):
    # When we compare a release version, we want to compare it with all of the
    # trailing zeros removed. So we'll use a reverse the list, drop all the now
    # leading zeros until we come to something non-zero, then take the rest,
    # re-reverse it back into the correct order, and make it a tuple and use
    # that for our sorting key.
    release = tuple(
        reversed(list(
            itertools.dropwhile(
                lambda x: x == 0,
                reversed(release),
            )
        ))
    )

    # We need to "trick" the sorting algorithm to put 1.0.dev0 before 1.0a0.
    # We'll do this by abusing the pre-segment, but we _only_ want to do this
    # if there is no pre- or a post-segment. If we have one of those, then
    # the normal sorting rules will handle this case correctly.
    if pre is None and post is None and dev is not None:
        pre = -Infinity
    # Versions without a pre-release (except as noted above) should sort after
    # those with one.
    elif pre is None:
        pre = Infinity

    # Versions without a post-segment should sort before those with one.
    if post is None:
        post = -Infinity

    # Versions without a development segment should sort after those with one.
    if dev is None:
        dev = Infinity

    if local is None:
        # Versions without a local segment should sort before those with one.
        local = -Infinity
    else:
        # Versions with a local segment need that segment parsed to implement
        # the sorting rules in PEP440.
        # - Alphanumeric segments sort before numeric segments
        # - Alphanumeric segments sort lexicographically
        # - Numeric segments sort numerically
        # - Shorter versions sort before longer versions when the prefixes
        #   match exactly
        local = tuple(
            (i, "") if isinstance(i, int) else (-Infinity, i)
            for i in local
        )

    return epoch, release, pre, post, dev, local

# === NexusCore/openenv\Lib\site-packages\asttokens\util.py ===
# Copyright 2016 Grist Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ast
import collections
import io
import sys
import token
import tokenize
from abc import ABCMeta
from ast import Module, expr, AST
from functools import lru_cache
from typing import (
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    cast,
    Any,
    TYPE_CHECKING,
    Type,
)

if TYPE_CHECKING:  # pragma: no cover
  from .astroid_compat import NodeNG

  # Type class used to expand out the definition of AST to include fields added by this library
  # It's not actually used for anything other than type checking though!
  class EnhancedAST(AST):
    # Additional attributes set by mark_tokens
    first_token = None  # type: Token
    last_token = None  # type: Token
    lineno = 0  # type: int

  AstNode = Union[EnhancedAST, NodeNG]

  TokenInfo = tokenize.TokenInfo


def token_repr(tok_type, string):
  # type: (int, Optional[str]) -> str
  """Returns a human-friendly representation of a token with the given type and string."""
  # repr() prefixes unicode with 'u' on Python2 but not Python3; strip it out for consistency.
  return '%s:%s' % (token.tok_name[tok_type], repr(string).lstrip('u'))


class Token(collections.namedtuple('Token', 'type string start end line index startpos endpos')):
  """
  TokenInfo is an 8-tuple containing the same 5 fields as the tokens produced by the tokenize
  module, and 3 additional ones useful for this module:

  - [0] .type     Token type (see token.py)
  - [1] .string   Token (a string)
  - [2] .start    Starting (row, column) indices of the token (a 2-tuple of ints)
  - [3] .end      Ending (row, column) indices of the token (a 2-tuple of ints)
  - [4] .line     Original line (string)
  - [5] .index    Index of the token in the list of tokens that it belongs to.
  - [6] .startpos Starting character offset into the input text.
  - [7] .endpos   Ending character offset into the input text.
  """
  def __str__(self):
    # type: () -> str
    return token_repr(self.type, self.string)


def match_token(token, tok_type, tok_str=None):
  # type: (Token, int, Optional[str]) -> bool
  """Returns true if token is of the given type and, if a string is given, has that string."""
  return token.type == tok_type and (tok_str is None or token.string == tok_str)


def expect_token(token, tok_type, tok_str=None):
  # type: (Token, int, Optional[str]) -> None
  """
  Verifies that the given token is of the expected type. If tok_str is given, the token string
  is verified too. If the token doesn't match, raises an informative ValueError.
  """
  if not match_token(token, tok_type, tok_str):
    raise ValueError("Expected token %s, got %s on line %s col %s" % (
      token_repr(tok_type, tok_str), str(token),
      token.start[0], token.start[1] + 1))


def is_non_coding_token(token_type):
  # type: (int) -> bool
  """
  These are considered non-coding tokens, as they don't affect the syntax tree.
  """
  return token_type in (token.NL, token.COMMENT, token.ENCODING)


def generate_tokens(text):
  # type: (str) -> Iterator[TokenInfo]
  """
  Generates standard library tokens for the given code.
  """
  # tokenize.generate_tokens is technically an undocumented API for Python3, but allows us to use the same API as for
  # Python2. See http://stackoverflow.com/a/4952291/328565.
  # FIXME: Remove cast once https://github.com/python/typeshed/issues/7003 gets fixed
  return tokenize.generate_tokens(cast(Callable[[], str], io.StringIO(text).readline))


def iter_children_func(node):
  # type: (AST) -> Callable
  """
  Returns a function which yields all direct children of a AST node,
  skipping children that are singleton nodes.
  The function depends on whether ``node`` is from ``ast`` or from the ``astroid`` module.
  """
  return iter_children_astroid if hasattr(node, 'get_children') else iter_children_ast


def iter_children_astroid(node, include_joined_str=False):
  # type: (NodeNG, bool) -> Union[Iterator, List]
  if not include_joined_str and is_joined_str(node):
    return []

  return node.get_children()


SINGLETONS = {c for n, c in ast.__dict__.items() if isinstance(c, type) and
              issubclass(c, (ast.expr_context, ast.boolop, ast.operator, ast.unaryop, ast.cmpop))}


def iter_children_ast(node, include_joined_str=False):
  # type: (AST, bool) -> Iterator[Union[AST, expr]]
  if not include_joined_str and is_joined_str(node):
    return

  if isinstance(node, ast.Dict):
    # override the iteration order: instead of <all keys>, <all values>,
    # yield keys and values in source order (key1, value1, key2, value2, ...)
    for (key, value) in zip(node.keys, node.values):
      if key is not None:
        yield key
      yield value
    return

  for child in ast.iter_child_nodes(node):
    # Skip singleton children; they don't reflect particular positions in the code and break the
    # assumptions about the tree consisting of distinct nodes. Note that collecting classes
    # beforehand and checking them in a set is faster than using isinstance each time.
    if child.__class__ not in SINGLETONS:
      yield child


stmt_class_names = {n for n, c in ast.__dict__.items()
                    if isinstance(c, type) and issubclass(c, ast.stmt)}
expr_class_names = ({n for n, c in ast.__dict__.items()
                    if isinstance(c, type) and issubclass(c, ast.expr)} |
                    {'AssignName', 'DelName', 'Const', 'AssignAttr', 'DelAttr'})

# These feel hacky compared to isinstance() but allow us to work with both ast and astroid nodes
# in the same way, and without even importing astroid.
def is_expr(node):
  # type: (AstNode) -> bool
  """Returns whether node is an expression node."""
  return node.__class__.__name__ in expr_class_names

def is_stmt(node):
  # type: (AstNode) -> bool
  """Returns whether node is a statement node."""
  return node.__class__.__name__ in stmt_class_names

def is_module(node):
  # type: (AstNode) -> bool
  """Returns whether node is a module node."""
  return node.__class__.__name__ == 'Module'

def is_joined_str(node):
  # type: (AstNode) -> bool
  """Returns whether node is a JoinedStr node, used to represent f-strings."""
  # At the moment, nodes below JoinedStr have wrong line/col info, and trying to process them only
  # leads to errors.
  return node.__class__.__name__ == 'JoinedStr'


def is_expr_stmt(node):
  # type: (AstNode) -> bool
  """Returns whether node is an `Expr` node, which is a statement that is an expression."""
  return node.__class__.__name__ == 'Expr'



CONSTANT_CLASSES: Tuple[Type, ...] = (ast.Constant,)
try:
  from astroid import Const
  CONSTANT_CLASSES += (Const,)
except ImportError:  # pragma: no cover
  # astroid is not available
  pass

def is_constant(node):
  # type: (AstNode) -> bool
  """Returns whether node is a Constant node."""
  return isinstance(node, CONSTANT_CLASSES)


def is_ellipsis(node):
  # type: (AstNode) -> bool
  """Returns whether node is an Ellipsis node."""
  return is_constant(node) and node.value is Ellipsis  # type: ignore


def is_starred(node):
  # type: (AstNode) -> bool
  """Returns whether node is a starred expression node."""
  return node.__class__.__name__ == 'Starred'


def is_slice(node):
  # type: (AstNode) -> bool
  """Returns whether node represents a slice, e.g. `1:2` in `x[1:2]`"""
  # Before 3.9, a tuple containing a slice is an ExtSlice,
  # but this was removed in https://bugs.python.org/issue34822
  return (
      node.__class__.__name__ in ('Slice', 'ExtSlice')
      or (
          node.__class__.__name__ == 'Tuple'
          and any(map(is_slice, cast(ast.Tuple, node).elts))
      )
  )


def is_empty_astroid_slice(node):
  # type: (AstNode) -> bool
  return (
      node.__class__.__name__ == "Slice"
      and not isinstance(node, ast.AST)
      and node.lower is node.upper is node.step is None
  )


# Sentinel value used by visit_tree().
_PREVISIT = object()

def visit_tree(node, previsit, postvisit):
  # type: (Module, Callable[[AstNode, Optional[Token]], Tuple[Optional[Token], Optional[Token]]], Optional[Callable[[AstNode, Optional[Token], Optional[Token]], None]])   -> None
  """
  Scans the tree under the node depth-first using an explicit stack. It avoids implicit recursion
  via the function call stack to avoid hitting 'maximum recursion depth exceeded' error.

  It calls ``previsit()`` and ``postvisit()`` as follows:

  * ``previsit(node, par_value)`` - should return ``(par_value, value)``
        ``par_value`` is as returned from ``previsit()`` of the parent.

  * ``postvisit(node, par_value, value)`` - should return ``value``
        ``par_value`` is as returned from ``previsit()`` of the parent, and ``value`` is as
        returned from ``previsit()`` of this node itself. The return ``value`` is ignored except
        the one for the root node, which is returned from the overall ``visit_tree()`` call.

  For the initial node, ``par_value`` is None. ``postvisit`` may be None.
  """
  if not postvisit:
    postvisit = lambda node, pvalue, value: None

  iter_children = iter_children_func(node)
  done = set()
  ret = None
  stack = [(node, None, _PREVISIT)] # type: List[Tuple[AstNode, Optional[Token], Union[Optional[Token], object]]]
  while stack:
    current, par_value, value = stack.pop()
    if value is _PREVISIT:
      assert current not in done    # protect againt infinite loop in case of a bad tree.
      done.add(current)

      pvalue, post_value = previsit(current, par_value)
      stack.append((current, par_value, post_value))

      # Insert all children in reverse order (so that first child ends up on top of the stack).
      ins = len(stack)
      for n in iter_children(current):
        stack.insert(ins, (n, pvalue, _PREVISIT))
    else:
      ret = postvisit(current, par_value, cast(Optional[Token], value))
  return ret


def walk(node, include_joined_str=False):
  # type: (AST, bool) -> Iterator[Union[Module, AstNode]]
  """
  Recursively yield all descendant nodes in the tree starting at ``node`` (including ``node``
  itself), using depth-first pre-order traversal (yieling parents before their children).

  This is similar to ``ast.walk()``, but with a different order, and it works for both ``ast`` and
  ``astroid`` trees. Also, as ``iter_children()``, it skips singleton nodes generated by ``ast``.

  By default, ``JoinedStr`` (f-string) nodes and their contents are skipped
  because they previously couldn't be handled. Set ``include_joined_str`` to True to include them.
  """
  iter_children = iter_children_func(node)
  done = set()
  stack = [node]
  while stack:
    current = stack.pop()
    assert current not in done    # protect againt infinite loop in case of a bad tree.
    done.add(current)

    yield current

    # Insert all children in reverse order (so that first child ends up on top of the stack).
    # This is faster than building a list and reversing it.
    ins = len(stack)
    for c in iter_children(current, include_joined_str):
      stack.insert(ins, c)


def replace(text, replacements):
  # type: (str, List[Tuple[int, int, str]]) -> str
  """
  Replaces multiple slices of text with new values. This is a convenience method for making code
  modifications of ranges e.g. as identified by ``ASTTokens.get_text_range(node)``. Replacements is
  an iterable of ``(start, end, new_text)`` tuples.

  For example, ``replace("this is a test", [(0, 4, "X"), (8, 9, "THE")])`` produces
  ``"X is THE test"``.
  """
  p = 0
  parts = []
  for (start, end, new_text) in sorted(replacements):
    parts.append(text[p:start])
    parts.append(new_text)
    p = end
  parts.append(text[p:])
  return ''.join(parts)


class NodeMethods:
  """
  Helper to get `visit_{node_type}` methods given a node's class and cache the results.
  """
  def __init__(self):
    # type: () -> None
    self._cache = {} # type: Dict[Union[ABCMeta, type], Callable[[AstNode, Token, Token], Tuple[Token, Token]]]

  def get(self, obj, cls):
    # type: (Any, Union[ABCMeta, type]) -> Callable
    """
    Using the lowercase name of the class as node_type, returns `obj.visit_{node_type}`,
    or `obj.visit_default` if the type-specific method is not found.
    """
    method = self._cache.get(cls)
    if not method:
      name = "visit_" + cls.__name__.lower()
      method = getattr(obj, name, obj.visit_default)
      self._cache[cls] = method
    return method


def patched_generate_tokens(original_tokens):
    # type: (Iterable[TokenInfo]) -> Iterator[TokenInfo]
    """
    Fixes tokens yielded by `tokenize.generate_tokens` to handle more non-ASCII characters in identifiers.
    Workaround for https://github.com/python/cpython/issues/68382.
    Should only be used when tokenizing a string that is known to be valid syntax,
    because it assumes that error tokens are not actually errors.
    Combines groups of consecutive NAME, NUMBER, and/or ERRORTOKEN tokens into a single NAME token.
    """
    group = []  # type: List[tokenize.TokenInfo]
    for tok in original_tokens:
      if (
          tok.type in (tokenize.NAME, tokenize.ERRORTOKEN, tokenize.NUMBER)
          # Only combine tokens if they have no whitespace in between
          and (not group or group[-1].end == tok.start)
      ):
        group.append(tok)
      else:
        for combined_token in combine_tokens(group):
          yield combined_token
        group = []
        yield tok
    for combined_token in combine_tokens(group):
      yield combined_token

def combine_tokens(group):
    # type: (List[tokenize.TokenInfo]) -> List[tokenize.TokenInfo]
    if not any(tok.type == tokenize.ERRORTOKEN for tok in group) or len({tok.line for tok in group}) != 1:
      return group
    return [
      tokenize.TokenInfo(
        type=tokenize.NAME,
        string="".join(t.string for t in group),
        start=group[0].start,
        end=group[-1].end,
        line=group[0].line,
      )
    ]


def last_stmt(node):
  # type: (ast.AST) -> ast.AST
  """
  If the given AST node contains multiple statements, return the last one.
  Otherwise, just return the node.
  """
  child_stmts = [
    child for child in iter_children_func(node)(node)
    if is_stmt(child) or type(child).__name__ in (
      "excepthandler",
      "ExceptHandler",
      "match_case",
      "MatchCase",
      "TryExcept",
      "TryFinally",
    )
  ]
  if child_stmts:
    return last_stmt(child_stmts[-1])
  return node



@lru_cache(maxsize=None)
def fstring_positions_work():
  # type: () -> bool
  """
  The positions attached to nodes inside f-string FormattedValues have some bugs
  that were fixed in Python 3.9.7 in https://github.com/python/cpython/pull/27729.
  This checks for those bugs more concretely without relying on the Python version.
  Specifically this checks:
   - Values with a format spec or conversion
   - Repeated (i.e. identical-looking) expressions
   - f-strings implicitly concatenated over multiple lines.
   - Multiline, triple-quoted f-strings.
  """
  source = """(
    f"a {b}{b} c {d!r} e {f:g} h {i:{j}} k {l:{m:n}}"
    f"a {b}{b} c {d!r} e {f:g} h {i:{j}} k {l:{m:n}}"
    f"{x + y + z} {x} {y} {z} {z} {z!a} {z:z}"
    f'''
    {s} {t}
    {u} {v}
    '''
  )"""
  tree = ast.parse(source)
  name_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Name)]
  name_positions = [(node.lineno, node.col_offset) for node in name_nodes]
  positions_are_unique = len(set(name_positions)) == len(name_positions)
  correct_source_segments = all(
    ast.get_source_segment(source, node) == node.id
    for node in name_nodes
  )
  return positions_are_unique and correct_source_segments

def annotate_fstring_nodes(tree):
  # type: (ast.AST) -> None
  """
  Add a special attribute `_broken_positions` to nodes inside f-strings
  if the lineno/col_offset cannot be trusted.
  """
  if sys.version_info >= (3, 12):
    # f-strings were weirdly implemented until https://peps.python.org/pep-0701/
    # In Python 3.12, inner nodes have sensible positions.
    return
  for joinedstr in walk(tree, include_joined_str=True):
    if not isinstance(joinedstr, ast.JoinedStr):
      continue
    for part in joinedstr.values:
      # The ast positions of the FormattedValues/Constant nodes span the full f-string, which is weird.
      setattr(part, '_broken_positions', True)  # use setattr for mypy

      if isinstance(part, ast.FormattedValue):
        if not fstring_positions_work():
          for child in walk(part.value):
            setattr(child, '_broken_positions', True)

        if part.format_spec:  # this is another JoinedStr
          # Again, the standard positions span the full f-string.
          setattr(part.format_spec, '_broken_positions', True)

# === NexusCore/openenv\Lib\site-packages\ipykernel\pickleutil.py ===
"""Pickle related utilities. Perhaps this should be called 'can'."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
import copy
import pickle
import sys
import typing
import warnings
from types import FunctionType

# This registers a hook when it's imported
try:
    from ipyparallel.serialize import codeutil  # noqa: F401
except ImportError:
    pass
from traitlets.log import get_logger
from traitlets.utils.importstring import import_item

warnings.warn(
    "ipykernel.pickleutil is deprecated. It has moved to ipyparallel.",
    DeprecationWarning,
    stacklevel=2,
)

buffer = memoryview
class_type = type

PICKLE_PROTOCOL = pickle.DEFAULT_PROTOCOL


def _get_cell_type(a=None):
    """the type of a closure cell doesn't seem to be importable,
    so just create one
    """

    def inner():
        return a

    return type(inner.__closure__[0])  # type:ignore[index]


cell_type = _get_cell_type()

# -------------------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------------------


def interactive(f):
    """decorator for making functions appear as interactively defined.
    This results in the function being linked to the user_ns as globals()
    instead of the module globals().
    """

    # build new FunctionType, so it can have the right globals
    # interactive functions never have closures, that's kind of the point
    if isinstance(f, FunctionType):
        mainmod = __import__("__main__")
        f = FunctionType(
            f.__code__,
            mainmod.__dict__,
            f.__name__,
            f.__defaults__,
        )
    # associate with __main__ for uncanning
    f.__module__ = "__main__"
    return f


def use_dill():
    """use dill to expand serialization support

    adds support for object methods and closures to serialization.
    """
    # import dill causes most of the magic
    import dill

    # dill doesn't work with cPickle,
    # tell the two relevant modules to use plain pickle

    global pickle  # noqa: PLW0603
    pickle = dill

    try:
        from ipykernel import serialize
    except ImportError:
        pass
    else:
        serialize.pickle = dill  # type:ignore[attr-defined]

    # disable special function handling, let dill take care of it
    can_map.pop(FunctionType, None)


def use_cloudpickle():
    """use cloudpickle to expand serialization support

    adds support for object methods and closures to serialization.
    """
    import cloudpickle

    global pickle  # noqa: PLW0603
    pickle = cloudpickle

    try:
        from ipykernel import serialize
    except ImportError:
        pass
    else:
        serialize.pickle = cloudpickle  # type:ignore[attr-defined]

    # disable special function handling, let cloudpickle take care of it
    can_map.pop(FunctionType, None)


# -------------------------------------------------------------------------------
# Classes
# -------------------------------------------------------------------------------


class CannedObject:
    """A canned object."""

    def __init__(self, obj, keys=None, hook=None):
        """can an object for safe pickling

        Parameters
        ----------
        obj
            The object to be canned
        keys : list (optional)
            list of attribute names that will be explicitly canned / uncanned
        hook : callable (optional)
            An optional extra callable,
            which can do additional processing of the uncanned object.

        Notes
        -----
        large data may be offloaded into the buffers list,
        used for zero-copy transfers.
        """
        self.keys = keys or []
        self.obj = copy.copy(obj)
        self.hook = can(hook)
        for key in keys:
            setattr(self.obj, key, can(getattr(obj, key)))

        self.buffers = []

    def get_object(self, g=None):
        """Get an object."""
        if g is None:
            g = {}
        obj = self.obj
        for key in self.keys:
            setattr(obj, key, uncan(getattr(obj, key), g))

        if self.hook:
            self.hook = uncan(self.hook, g)
            self.hook(obj, g)
        return self.obj


class Reference(CannedObject):
    """object for wrapping a remote reference by name."""

    def __init__(self, name):
        """Initialize the reference."""
        if not isinstance(name, str):
            raise TypeError("illegal name: %r" % name)
        self.name = name
        self.buffers = []

    def __repr__(self):
        """Get the string repr of the reference."""
        return "<Reference: %r>" % self.name

    def get_object(self, g=None):
        """Get an object in the reference."""
        if g is None:
            g = {}

        return eval(self.name, g)


class CannedCell(CannedObject):
    """Can a closure cell"""

    def __init__(self, cell):
        """Initialize the canned cell."""
        self.cell_contents = can(cell.cell_contents)

    def get_object(self, g=None):
        """Get an object in the cell."""
        cell_contents = uncan(self.cell_contents, g)

        def inner():
            """Inner function."""
            return cell_contents

        return inner.__closure__[0]  # type:ignore[index]


class CannedFunction(CannedObject):
    """Can a function."""

    def __init__(self, f):
        """Initialize the can"""
        self._check_type(f)
        self.code = f.__code__
        self.defaults: typing.Optional[typing.List[typing.Any]]
        if f.__defaults__:
            self.defaults = [can(fd) for fd in f.__defaults__]
        else:
            self.defaults = None

        self.closure: typing.Any
        closure = f.__closure__
        if closure:
            self.closure = tuple(can(cell) for cell in closure)
        else:
            self.closure = None

        self.module = f.__module__ or "__main__"
        self.__name__ = f.__name__
        self.buffers = []

    def _check_type(self, obj):
        assert isinstance(obj, FunctionType), "Not a function type"

    def get_object(self, g=None):
        """Get an object out of the can."""
        # try to load function back into its module:
        if not self.module.startswith("__"):
            __import__(self.module)
            g = sys.modules[self.module].__dict__

        if g is None:
            g = {}
        defaults = tuple(uncan(cfd, g) for cfd in self.defaults) if self.defaults else None
        closure = tuple(uncan(cell, g) for cell in self.closure) if self.closure else None
        return FunctionType(self.code, g, self.__name__, defaults, closure)


class CannedClass(CannedObject):
    """A canned class object."""

    def __init__(self, cls):
        """Initialize the can."""
        self._check_type(cls)
        self.name = cls.__name__
        self.old_style = not isinstance(cls, type)
        self._canned_dict = {}
        for k, v in cls.__dict__.items():
            if k not in ("__weakref__", "__dict__"):
                self._canned_dict[k] = can(v)
        mro = [] if self.old_style else cls.mro()

        self.parents = [can(c) for c in mro[1:]]
        self.buffers = []

    def _check_type(self, obj):
        assert isinstance(obj, class_type), "Not a class type"

    def get_object(self, g=None):
        """Get an object from the can."""
        parents = tuple(uncan(p, g) for p in self.parents)
        return type(self.name, parents, uncan_dict(self._canned_dict, g=g))


class CannedArray(CannedObject):
    """A canned numpy array."""

    def __init__(self, obj):
        """Initialize the can."""
        from numpy import ascontiguousarray

        self.shape = obj.shape
        self.dtype = obj.dtype.descr if obj.dtype.fields else obj.dtype.str
        self.pickled = False
        if sum(obj.shape) == 0:
            self.pickled = True
        elif obj.dtype == "O":
            # can't handle object dtype with buffer approach
            self.pickled = True
        elif obj.dtype.fields and any(dt == "O" for dt, sz in obj.dtype.fields.values()):
            self.pickled = True
        if self.pickled:
            # just pickle it
            self.buffers = [pickle.dumps(obj, PICKLE_PROTOCOL)]
        else:
            # ensure contiguous
            obj = ascontiguousarray(obj, dtype=None)
            self.buffers = [buffer(obj)]

    def get_object(self, g=None):
        """Get the object."""
        from numpy import frombuffer

        data = self.buffers[0]
        if self.pickled:
            # we just pickled it
            return pickle.loads(data)
        return frombuffer(data, dtype=self.dtype).reshape(self.shape)


class CannedBytes(CannedObject):
    """A canned bytes object."""

    @staticmethod
    def wrap(buf: typing.Union[memoryview, bytes, typing.SupportsBytes]) -> bytes:
        """Cast a buffer or memoryview object to bytes"""
        if isinstance(buf, memoryview):
            return buf.tobytes()
        if not isinstance(buf, bytes):
            return bytes(buf)
        return buf

    def __init__(self, obj):
        """Initialize the can."""
        self.buffers = [obj]

    def get_object(self, g=None):
        """Get the canned object."""
        data = self.buffers[0]
        return self.wrap(data)


class CannedBuffer(CannedBytes):
    """A canned buffer."""

    wrap = buffer  # type:ignore[assignment]


class CannedMemoryView(CannedBytes):
    """A canned memory view."""

    wrap = memoryview  # type:ignore[assignment]


# -------------------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------------------


def _import_mapping(mapping, original=None):
    """import any string-keys in a type mapping"""
    log = get_logger()
    log.debug("Importing canning map")
    for key, _ in list(mapping.items()):
        if isinstance(key, str):
            try:
                cls = import_item(key)
            except Exception:
                if original and key not in original:
                    # only message on user-added classes
                    log.error("canning class not importable: %r", key, exc_info=True)  # noqa: G201
                mapping.pop(key)
            else:
                mapping[cls] = mapping.pop(key)


def istype(obj, check):
    """like isinstance(obj, check), but strict

    This won't catch subclasses.
    """
    if isinstance(check, tuple):
        return any(type(obj) is cls for cls in check)
    return type(obj) is check


def can(obj):
    """prepare an object for pickling"""

    import_needed = False

    for cls, canner in can_map.items():
        if isinstance(cls, str):
            import_needed = True
            break
        if istype(obj, cls):
            return canner(obj)

    if import_needed:
        # perform can_map imports, then try again
        # this will usually only happen once
        _import_mapping(can_map, _original_can_map)
        return can(obj)

    return obj


def can_class(obj):
    """Can a class object."""
    if isinstance(obj, class_type) and obj.__module__ == "__main__":
        return CannedClass(obj)
    return obj


def can_dict(obj):
    """can the *values* of a dict"""
    if istype(obj, dict):
        newobj = {}
        for k, v in obj.items():
            newobj[k] = can(v)
        return newobj
    return obj


sequence_types = (list, tuple, set)


def can_sequence(obj):
    """can the elements of a sequence"""
    if istype(obj, sequence_types):
        t = type(obj)
        return t([can(i) for i in obj])
    return obj


def uncan(obj, g=None):
    """invert canning"""

    import_needed = False
    for cls, uncanner in uncan_map.items():
        if isinstance(cls, str):
            import_needed = True
            break
        if isinstance(obj, cls):
            return uncanner(obj, g)

    if import_needed:
        # perform uncan_map imports, then try again
        # this will usually only happen once
        _import_mapping(uncan_map, _original_uncan_map)
        return uncan(obj, g)

    return obj


def uncan_dict(obj, g=None):
    """Uncan a dict object."""
    if istype(obj, dict):
        newobj = {}
        for k, v in obj.items():
            newobj[k] = uncan(v, g)
        return newobj
    return obj


def uncan_sequence(obj, g=None):
    """Uncan a sequence."""
    if istype(obj, sequence_types):
        t = type(obj)
        return t([uncan(i, g) for i in obj])
    return obj


# -------------------------------------------------------------------------------
# API dictionaries
# -------------------------------------------------------------------------------

# These dicts can be extended for custom serialization of new objects

can_map = {
    "numpy.ndarray": CannedArray,
    FunctionType: CannedFunction,
    bytes: CannedBytes,
    memoryview: CannedMemoryView,
    cell_type: CannedCell,
    class_type: can_class,
}
if buffer is not memoryview:
    can_map[buffer] = CannedBuffer

uncan_map: typing.Dict[type, typing.Any] = {
    CannedObject: lambda obj, g: obj.get_object(g),
    dict: uncan_dict,
}

# for use in _import_mapping:
_original_can_map = can_map.copy()
_original_uncan_map = uncan_map.copy()

# === NexusCore/openenv\Lib\site-packages\rsa\pkcs1.py ===
#  Copyright 2011 Sybren A. Stüvel <sybren@stuvel.eu>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Functions for PKCS#1 version 1.5 encryption and signing

This module implements certain functionality from PKCS#1 version 1.5. For a
very clear example, read http://www.di-mgt.com.au/rsa_alg.html#pkcs1schemes

At least 8 bytes of random padding is used when encrypting a message. This makes
these methods much more secure than the ones in the ``rsa`` module.

WARNING: this module leaks information when decryption fails. The exceptions
that are raised contain the Python traceback information, which can be used to
deduce where in the process the failure occurred. DO NOT PASS SUCH INFORMATION
to your users.
"""

import hashlib
import os
import sys
import typing
from hmac import compare_digest

from . import common, transform, core, key

if typing.TYPE_CHECKING:
    HashType = hashlib._Hash
else:
    HashType = typing.Any

# ASN.1 codes that describe the hash algorithm used.
HASH_ASN1 = {
    "MD5": b"\x30\x20\x30\x0c\x06\x08\x2a\x86\x48\x86\xf7\x0d\x02\x05\x05\x00\x04\x10",
    "SHA-1": b"\x30\x21\x30\x09\x06\x05\x2b\x0e\x03\x02\x1a\x05\x00\x04\x14",
    "SHA-224": b"\x30\x2d\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x04\x05\x00\x04\x1c",
    "SHA-256": b"\x30\x31\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x01\x05\x00\x04\x20",
    "SHA-384": b"\x30\x41\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x02\x05\x00\x04\x30",
    "SHA-512": b"\x30\x51\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x03\x05\x00\x04\x40",
}

HASH_METHODS: typing.Dict[str, typing.Callable[[], HashType]] = {
    "MD5": hashlib.md5,
    "SHA-1": hashlib.sha1,
    "SHA-224": hashlib.sha224,
    "SHA-256": hashlib.sha256,
    "SHA-384": hashlib.sha384,
    "SHA-512": hashlib.sha512,
}
"""Hash methods supported by this library."""


if sys.version_info >= (3, 6):
    # Python 3.6 introduced SHA3 support.
    HASH_ASN1.update(
        {
            "SHA3-256": b"\x30\x31\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x08\x05\x00\x04\x20",
            "SHA3-384": b"\x30\x41\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x09\x05\x00\x04\x30",
            "SHA3-512": b"\x30\x51\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x0a\x05\x00\x04\x40",
        }
    )

    HASH_METHODS.update(
        {
            "SHA3-256": hashlib.sha3_256,
            "SHA3-384": hashlib.sha3_384,
            "SHA3-512": hashlib.sha3_512,
        }
    )


class CryptoError(Exception):
    """Base class for all exceptions in this module."""


class DecryptionError(CryptoError):
    """Raised when decryption fails."""


class VerificationError(CryptoError):
    """Raised when verification fails."""


def _pad_for_encryption(message: bytes, target_length: int) -> bytes:
    r"""Pads the message for encryption, returning the padded message.

    :return: 00 02 RANDOM_DATA 00 MESSAGE

    >>> block = _pad_for_encryption(b'hello', 16)
    >>> len(block)
    16
    >>> block[0:2]
    b'\x00\x02'
    >>> block[-6:]
    b'\x00hello'

    """

    max_msglength = target_length - 11
    msglength = len(message)

    if msglength > max_msglength:
        raise OverflowError(
            "%i bytes needed for message, but there is only"
            " space for %i" % (msglength, max_msglength)
        )

    # Get random padding
    padding = b""
    padding_length = target_length - msglength - 3

    # We remove 0-bytes, so we'll end up with less padding than we've asked for,
    # so keep adding data until we're at the correct length.
    while len(padding) < padding_length:
        needed_bytes = padding_length - len(padding)

        # Always read at least 8 bytes more than we need, and trim off the rest
        # after removing the 0-bytes. This increases the chance of getting
        # enough bytes, especially when needed_bytes is small
        new_padding = os.urandom(needed_bytes + 5)
        new_padding = new_padding.replace(b"\x00", b"")
        padding = padding + new_padding[:needed_bytes]

    assert len(padding) == padding_length

    return b"".join([b"\x00\x02", padding, b"\x00", message])


def _pad_for_signing(message: bytes, target_length: int) -> bytes:
    r"""Pads the message for signing, returning the padded message.

    The padding is always a repetition of FF bytes.

    :return: 00 01 PADDING 00 MESSAGE

    >>> block = _pad_for_signing(b'hello', 16)
    >>> len(block)
    16
    >>> block[0:2]
    b'\x00\x01'
    >>> block[-6:]
    b'\x00hello'
    >>> block[2:-6]
    b'\xff\xff\xff\xff\xff\xff\xff\xff'

    """

    max_msglength = target_length - 11
    msglength = len(message)

    if msglength > max_msglength:
        raise OverflowError(
            "%i bytes needed for message, but there is only"
            " space for %i" % (msglength, max_msglength)
        )

    padding_length = target_length - msglength - 3

    return b"".join([b"\x00\x01", padding_length * b"\xff", b"\x00", message])


def encrypt(message: bytes, pub_key: key.PublicKey) -> bytes:
    """Encrypts the given message using PKCS#1 v1.5

    :param message: the message to encrypt. Must be a byte string no longer than
        ``k-11`` bytes, where ``k`` is the number of bytes needed to encode
        the ``n`` component of the public key.
    :param pub_key: the :py:class:`rsa.PublicKey` to encrypt with.
    :raise OverflowError: when the message is too large to fit in the padded
        block.

    >>> from rsa import key, common
    >>> (pub_key, priv_key) = key.newkeys(256)
    >>> message = b'hello'
    >>> crypto = encrypt(message, pub_key)

    The crypto text should be just as long as the public key 'n' component:

    >>> len(crypto) == common.byte_size(pub_key.n)
    True

    """

    keylength = common.byte_size(pub_key.n)
    padded = _pad_for_encryption(message, keylength)

    payload = transform.bytes2int(padded)
    encrypted = core.encrypt_int(payload, pub_key.e, pub_key.n)
    block = transform.int2bytes(encrypted, keylength)

    return block


def decrypt(crypto: bytes, priv_key: key.PrivateKey) -> bytes:
    r"""Decrypts the given message using PKCS#1 v1.5

    The decryption is considered 'failed' when the resulting cleartext doesn't
    start with the bytes 00 02, or when the 00 byte between the padding and
    the message cannot be found.

    :param crypto: the crypto text as returned by :py:func:`rsa.encrypt`
    :param priv_key: the :py:class:`rsa.PrivateKey` to decrypt with.
    :raise DecryptionError: when the decryption fails. No details are given as
        to why the code thinks the decryption fails, as this would leak
        information about the private key.


    >>> import rsa
    >>> (pub_key, priv_key) = rsa.newkeys(256)

    It works with strings:

    >>> crypto = encrypt(b'hello', pub_key)
    >>> decrypt(crypto, priv_key)
    b'hello'

    And with binary data:

    >>> crypto = encrypt(b'\x00\x00\x00\x00\x01', pub_key)
    >>> decrypt(crypto, priv_key)
    b'\x00\x00\x00\x00\x01'

    Altering the encrypted information will *likely* cause a
    :py:class:`rsa.pkcs1.DecryptionError`. If you want to be *sure*, use
    :py:func:`rsa.sign`.


    .. warning::

        Never display the stack trace of a
        :py:class:`rsa.pkcs1.DecryptionError` exception. It shows where in the
        code the exception occurred, and thus leaks information about the key.
        It's only a tiny bit of information, but every bit makes cracking the
        keys easier.

    >>> crypto = encrypt(b'hello', pub_key)
    >>> crypto = crypto[0:5] + b'X' + crypto[6:] # change a byte
    >>> decrypt(crypto, priv_key)
    Traceback (most recent call last):
    ...
    rsa.pkcs1.DecryptionError: Decryption failed

    """

    blocksize = common.byte_size(priv_key.n)
    encrypted = transform.bytes2int(crypto)
    decrypted = priv_key.blinded_decrypt(encrypted)
    cleartext = transform.int2bytes(decrypted, blocksize)

    # Detect leading zeroes in the crypto. These are not reflected in the
    # encrypted value (as leading zeroes do not influence the value of an
    # integer). This fixes CVE-2020-13757.
    if len(crypto) > blocksize:
        # This is operating on public information, so doesn't need to be constant-time.
        raise DecryptionError("Decryption failed")

    # If we can't find the cleartext marker, decryption failed.
    cleartext_marker_bad = not compare_digest(cleartext[:2], b"\x00\x02")

    # Find the 00 separator between the padding and the message
    sep_idx = cleartext.find(b"\x00", 2)

    # sep_idx indicates the position of the `\x00` separator that separates the
    # padding from the actual message. The padding should be at least 8 bytes
    # long (see https://tools.ietf.org/html/rfc8017#section-7.2.2 step 3), which
    # means the separator should be at least at index 10 (because of the
    # `\x00\x02` marker that precedes it).
    sep_idx_bad = sep_idx < 10

    anything_bad = cleartext_marker_bad | sep_idx_bad
    if anything_bad:
        raise DecryptionError("Decryption failed")

    return cleartext[sep_idx + 1 :]


def sign_hash(hash_value: bytes, priv_key: key.PrivateKey, hash_method: str) -> bytes:
    """Signs a precomputed hash with the private key.

    Hashes the message, then signs the hash with the given key. This is known
    as a "detached signature", because the message itself isn't altered.

    :param hash_value: A precomputed hash to sign (ignores message).
    :param priv_key: the :py:class:`rsa.PrivateKey` to sign with
    :param hash_method: the hash method used on the message. Use 'MD5', 'SHA-1',
        'SHA-224', SHA-256', 'SHA-384' or 'SHA-512'.
    :return: a message signature block.
    :raise OverflowError: if the private key is too small to contain the
        requested hash.

    """

    # Get the ASN1 code for this hash method
    if hash_method not in HASH_ASN1:
        raise ValueError("Invalid hash method: %s" % hash_method)
    asn1code = HASH_ASN1[hash_method]

    # Encrypt the hash with the private key
    cleartext = asn1code + hash_value
    keylength = common.byte_size(priv_key.n)
    padded = _pad_for_signing(cleartext, keylength)

    payload = transform.bytes2int(padded)
    encrypted = priv_key.blinded_encrypt(payload)
    block = transform.int2bytes(encrypted, keylength)

    return block


def sign(message: bytes, priv_key: key.PrivateKey, hash_method: str) -> bytes:
    """Signs the message with the private key.

    Hashes the message, then signs the hash with the given key. This is known
    as a "detached signature", because the message itself isn't altered.

    :param message: the message to sign. Can be an 8-bit string or a file-like
        object. If ``message`` has a ``read()`` method, it is assumed to be a
        file-like object.
    :param priv_key: the :py:class:`rsa.PrivateKey` to sign with
    :param hash_method: the hash method used on the message. Use 'MD5', 'SHA-1',
        'SHA-224', SHA-256', 'SHA-384' or 'SHA-512'.
    :return: a message signature block.
    :raise OverflowError: if the private key is too small to contain the
        requested hash.

    """

    msg_hash = compute_hash(message, hash_method)
    return sign_hash(msg_hash, priv_key, hash_method)


def verify(message: bytes, signature: bytes, pub_key: key.PublicKey) -> str:
    """Verifies that the signature matches the message.

    The hash method is detected automatically from the signature.

    :param message: the signed message. Can be an 8-bit string or a file-like
        object. If ``message`` has a ``read()`` method, it is assumed to be a
        file-like object.
    :param signature: the signature block, as created with :py:func:`rsa.sign`.
    :param pub_key: the :py:class:`rsa.PublicKey` of the person signing the message.
    :raise VerificationError: when the signature doesn't match the message.
    :returns: the name of the used hash.

    """

    keylength = common.byte_size(pub_key.n)
    encrypted = transform.bytes2int(signature)
    decrypted = core.decrypt_int(encrypted, pub_key.e, pub_key.n)
    clearsig = transform.int2bytes(decrypted, keylength)

    # Get the hash method
    method_name = _find_method_hash(clearsig)
    message_hash = compute_hash(message, method_name)

    # Reconstruct the expected padded hash
    cleartext = HASH_ASN1[method_name] + message_hash
    expected = _pad_for_signing(cleartext, keylength)

    if len(signature) != keylength:
        raise VerificationError("Verification failed")

    # Compare with the signed one
    if expected != clearsig:
        raise VerificationError("Verification failed")

    return method_name


def find_signature_hash(signature: bytes, pub_key: key.PublicKey) -> str:
    """Returns the hash name detected from the signature.

    If you also want to verify the message, use :py:func:`rsa.verify()` instead.
    It also returns the name of the used hash.

    :param signature: the signature block, as created with :py:func:`rsa.sign`.
    :param pub_key: the :py:class:`rsa.PublicKey` of the person signing the message.
    :returns: the name of the used hash.
    """

    keylength = common.byte_size(pub_key.n)
    encrypted = transform.bytes2int(signature)
    decrypted = core.decrypt_int(encrypted, pub_key.e, pub_key.n)
    clearsig = transform.int2bytes(decrypted, keylength)

    return _find_method_hash(clearsig)


def yield_fixedblocks(infile: typing.BinaryIO, blocksize: int) -> typing.Iterator[bytes]:
    """Generator, yields each block of ``blocksize`` bytes in the input file.

    :param infile: file to read and separate in blocks.
    :param blocksize: block size in bytes.
    :returns: a generator that yields the contents of each block
    """

    while True:
        block = infile.read(blocksize)

        read_bytes = len(block)
        if read_bytes == 0:
            break

        yield block

        if read_bytes < blocksize:
            break


def compute_hash(message: typing.Union[bytes, typing.BinaryIO], method_name: str) -> bytes:
    """Returns the message digest.

    :param message: the signed message. Can be an 8-bit string or a file-like
        object. If ``message`` has a ``read()`` method, it is assumed to be a
        file-like object.
    :param method_name: the hash method, must be a key of
        :py:const:`rsa.pkcs1.HASH_METHODS`.

    """

    if method_name not in HASH_METHODS:
        raise ValueError("Invalid hash method: %s" % method_name)

    method = HASH_METHODS[method_name]
    hasher = method()

    if isinstance(message, bytes):
        hasher.update(message)
    else:
        assert hasattr(message, "read") and hasattr(message.read, "__call__")
        # read as 1K blocks
        for block in yield_fixedblocks(message, 1024):
            hasher.update(block)

    return hasher.digest()


def _find_method_hash(clearsig: bytes) -> str:
    """Finds the hash method.

    :param clearsig: full padded ASN1 and hash.
    :return: the used hash method.
    :raise VerificationFailed: when the hash method cannot be found
    """

    for (hashname, asn1code) in HASH_ASN1.items():
        if asn1code in clearsig:
            return hashname

    raise VerificationError("Verification failed")


__all__ = [
    "encrypt",
    "decrypt",
    "sign",
    "verify",
    "DecryptionError",
    "VerificationError",
    "CryptoError",
]

if __name__ == "__main__":
    print("Running doctests 1000x or until failure")
    import doctest

    for count in range(1000):
        (failures, tests) = doctest.testmod()
        if failures:
            break

        if count % 100 == 0 and count:
            print("%i times" % count)

    print("Doctests done")

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\_pydev_jy_imports_tipper.py ===
import traceback
from io import StringIO
from java.lang import StringBuffer  # @UnresolvedImport
from java.lang import String  # @UnresolvedImport
import java.lang  # @UnresolvedImport
import sys
from _pydev_bundle._pydev_tipper_common import do_find

from org.python.core import PyReflectedFunction  # @UnresolvedImport

from org.python import core  # @UnresolvedImport
from org.python.core import PyClass  # @UnresolvedImport

# completion types.
TYPE_IMPORT = "0"
TYPE_CLASS = "1"
TYPE_FUNCTION = "2"
TYPE_ATTR = "3"
TYPE_BUILTIN = "4"
TYPE_PARAM = "5"


def _imp(name):
    try:
        return __import__(name)
    except:
        if "." in name:
            sub = name[0 : name.rfind(".")]
            return _imp(sub)
        else:
            s = "Unable to import module: %s - sys.path: %s" % (str(name), sys.path)
            raise RuntimeError(s)


import java.util

_java_rt_file = getattr(java.util, "__file__", None)


def Find(name):
    f = None
    if name.startswith("__builtin__"):
        if name == "__builtin__.str":
            name = "org.python.core.PyString"
        elif name == "__builtin__.dict":
            name = "org.python.core.PyDictionary"

    mod = _imp(name)
    parent = mod
    foundAs = ""

    try:
        f = getattr(mod, "__file__", None)
    except:
        f = None

    components = name.split(".")
    old_comp = None
    for comp in components[1:]:
        try:
            # this happens in the following case:
            # we have mx.DateTime.mxDateTime.mxDateTime.pyd
            # but after importing it, mx.DateTime.mxDateTime does shadows access to mxDateTime.pyd
            mod = getattr(mod, comp)
        except AttributeError:
            if old_comp != comp:
                raise

        if hasattr(mod, "__file__"):
            f = mod.__file__
        else:
            if len(foundAs) > 0:
                foundAs = foundAs + "."
            foundAs = foundAs + comp

        old_comp = comp

    if f is None and name.startswith("java.lang"):
        # Hack: java.lang.__file__ is None on Jython 2.7 (whereas it pointed to rt.jar on Jython 2.5).
        f = _java_rt_file

    if f is not None:
        if f.endswith(".pyc"):
            f = f[:-1]
        elif f.endswith("$py.class"):
            f = f[: -len("$py.class")] + ".py"
    return f, mod, parent, foundAs


def format_param_class_name(paramClassName):
    if paramClassName.startswith("<type '") and paramClassName.endswith("'>"):
        paramClassName = paramClassName[len("<type '") : -2]
    if paramClassName.startswith("["):
        if paramClassName == "[C":
            paramClassName = "char[]"

        elif paramClassName == "[B":
            paramClassName = "byte[]"

        elif paramClassName == "[I":
            paramClassName = "int[]"

        elif paramClassName.startswith("[L") and paramClassName.endswith(";"):
            paramClassName = paramClassName[2:-1]
            paramClassName += "[]"
    return paramClassName


def generate_tip(data, log=None):
    data = data.replace("\n", "")
    if data.endswith("."):
        data = data.rstrip(".")

    f, mod, parent, foundAs = Find(data)
    tips = generate_imports_tip_for_module(mod)
    return f, tips


# =======================================================================================================================
# Info
# =======================================================================================================================
class Info:
    def __init__(self, name, **kwargs):
        self.name = name
        self.doc = kwargs.get("doc", None)
        self.args = kwargs.get("args", ())  # tuple of strings
        self.varargs = kwargs.get("varargs", None)  # string
        self.kwargs = kwargs.get("kwargs", None)  # string
        self.ret = kwargs.get("ret", None)  # string

    def basic_as_str(self):
        """@returns this class information as a string (just basic format)"""
        args = self.args
        s = "function:%s args=%s, varargs=%s, kwargs=%s, docs:%s" % (self.name, args, self.varargs, self.kwargs, self.doc)
        return s

    def get_as_doc(self):
        s = str(self.name)
        if self.doc:
            s += "\n@doc %s\n" % str(self.doc)

        if self.args:
            s += "\n@params "
            for arg in self.args:
                s += str(format_param_class_name(arg))
                s += "  "

        if self.varargs:
            s += "\n@varargs "
            s += str(self.varargs)

        if self.kwargs:
            s += "\n@kwargs "
            s += str(self.kwargs)

        if self.ret:
            s += "\n@return "
            s += str(format_param_class_name(str(self.ret)))

        return str(s)


def isclass(cls):
    return isinstance(cls, core.PyClass) or type(cls) == java.lang.Class


def ismethod(func):
    """this function should return the information gathered on a function

    @param func: this is the function we want to get info on
    @return a tuple where:
        0 = indicates whether the parameter passed is a method or not
        1 = a list of classes 'Info', with the info gathered from the function
            this is a list because when we have methods from java with the same name and different signatures,
            we actually have many methods, each with its own set of arguments
    """

    try:
        if isinstance(func, core.PyFunction):
            # ok, this is from python, created by jython
            # print_ '    PyFunction'

            def getargs(func_code):
                """Get information about the arguments accepted by a code object.

                Three things are returned: (args, varargs, varkw), where 'args' is
                a list of argument names (possibly containing nested lists), and
                'varargs' and 'varkw' are the names of the * and ** arguments or None."""

                nargs = func_code.co_argcount
                names = func_code.co_varnames
                args = list(names[:nargs])
                step = 0

                if not hasattr(func_code, "CO_VARARGS"):
                    from org.python.core import CodeFlag  # @UnresolvedImport

                    co_varargs_flag = CodeFlag.CO_VARARGS.flag
                    co_varkeywords_flag = CodeFlag.CO_VARKEYWORDS.flag
                else:
                    co_varargs_flag = func_code.CO_VARARGS
                    co_varkeywords_flag = func_code.CO_VARKEYWORDS

                varargs = None
                if func_code.co_flags & co_varargs_flag:
                    varargs = func_code.co_varnames[nargs]
                    nargs = nargs + 1
                varkw = None
                if func_code.co_flags & co_varkeywords_flag:
                    varkw = func_code.co_varnames[nargs]
                return args, varargs, varkw

            args = getargs(func.func_code)
            return 1, [Info(func.func_name, args=args[0], varargs=args[1], kwargs=args[2], doc=func.func_doc)]

        if isinstance(func, core.PyMethod):
            # this is something from java itself, and jython just wrapped it...

            # things to play in func:
            # ['__call__', '__class__', '__cmp__', '__delattr__', '__dir__', '__doc__', '__findattr__', '__name__', '_doget', 'im_class',
            # 'im_func', 'im_self', 'toString']
            # print_ '    PyMethod'
            # that's the PyReflectedFunction... keep going to get it
            func = func.im_func

        if isinstance(func, PyReflectedFunction):
            # this is something from java itself, and jython just wrapped it...

            # print_ '    PyReflectedFunction'

            infos = []
            for i in range(len(func.argslist)):
                # things to play in func.argslist[i]:

                # 'PyArgsCall', 'PyArgsKeywordsCall', 'REPLACE', 'StandardCall', 'args', 'compare', 'compareTo', 'data', 'declaringClass'
                # 'flags', 'isStatic', 'matches', 'precedence']

                # print_ '        ', func.argslist[i].data.__class__
                # func.argslist[i].data.__class__ == java.lang.reflect.Method

                if func.argslist[i]:
                    met = func.argslist[i].data
                    name = met.getName()
                    try:
                        ret = met.getReturnType()
                    except AttributeError:
                        ret = ""
                    parameterTypes = met.getParameterTypes()

                    args = []
                    for j in range(len(parameterTypes)):
                        paramTypesClass = parameterTypes[j]
                        try:
                            try:
                                paramClassName = paramTypesClass.getName()
                            except:
                                paramClassName = paramTypesClass.getName(paramTypesClass)
                        except AttributeError:
                            try:
                                paramClassName = repr(paramTypesClass)  # should be something like <type 'object'>
                                paramClassName = paramClassName.split("'")[1]
                            except:
                                paramClassName = repr(paramTypesClass)  # just in case something else happens... it will at least be visible
                        # if the parameter equals [C, it means it it a char array, so, let's change it

                        a = format_param_class_name(paramClassName)
                        # a = a.replace('[]','Array')
                        # a = a.replace('Object', 'obj')
                        # a = a.replace('String', 's')
                        # a = a.replace('Integer', 'i')
                        # a = a.replace('Char', 'c')
                        # a = a.replace('Double', 'd')
                        args.append(a)  # so we don't leave invalid code

                    info = Info(name, args=args, ret=ret)
                    # print_ info.basic_as_str()
                    infos.append(info)

            return 1, infos
    except Exception:
        s = StringIO()
        traceback.print_exc(file=s)
        return 1, [Info(str("ERROR"), doc=s.getvalue())]

    return 0, None


def ismodule(mod):
    # java modules... do we have other way to know that?
    if not hasattr(mod, "getClass") and not hasattr(mod, "__class__") and hasattr(mod, "__name__"):
        return 1

    return isinstance(mod, core.PyModule)


def dir_obj(obj):
    ret = []
    found = java.util.HashMap()
    original = obj
    if hasattr(obj, "__class__"):
        if obj.__class__ == java.lang.Class:
            # get info about superclasses
            classes = []
            classes.append(obj)
            try:
                c = obj.getSuperclass()
            except TypeError:
                # may happen on jython when getting the java.lang.Class class
                c = obj.getSuperclass(obj)

            while c != None:
                classes.append(c)
                c = c.getSuperclass()

            # get info about interfaces
            interfs = []
            for obj in classes:
                try:
                    interfs.extend(obj.getInterfaces())
                except TypeError:
                    interfs.extend(obj.getInterfaces(obj))
            classes.extend(interfs)

            # now is the time when we actually get info on the declared methods and fields
            for obj in classes:
                try:
                    declaredMethods = obj.getDeclaredMethods()
                except TypeError:
                    declaredMethods = obj.getDeclaredMethods(obj)

                try:
                    declaredFields = obj.getDeclaredFields()
                except TypeError:
                    declaredFields = obj.getDeclaredFields(obj)

                for i in range(len(declaredMethods)):
                    name = declaredMethods[i].getName()
                    ret.append(name)
                    found.put(name, 1)

                for i in range(len(declaredFields)):
                    name = declaredFields[i].getName()
                    ret.append(name)
                    found.put(name, 1)

        elif isclass(obj.__class__):
            d = dir(obj.__class__)
            for name in d:
                ret.append(name)
                found.put(name, 1)

    # this simple dir does not always get all the info, that's why we have the part before
    # (e.g.: if we do a dir on String, some methods that are from other interfaces such as
    # charAt don't appear)
    d = dir(original)
    for name in d:
        if found.get(name) != 1:
            ret.append(name)

    return ret


def format_arg(arg):
    """formats an argument to be shown"""

    s = str(arg)
    dot = s.rfind(".")
    if dot >= 0:
        s = s[dot + 1 :]

    s = s.replace(";", "")
    s = s.replace("[]", "Array")
    if len(s) > 0:
        c = s[0].lower()
        s = c + s[1:]

    return s


def search_definition(data):
    """@return file, line, col"""

    data = data.replace("\n", "")
    if data.endswith("."):
        data = data.rstrip(".")
    f, mod, parent, foundAs = Find(data)
    try:
        return do_find(f, mod), foundAs
    except:
        return do_find(f, parent), foundAs


def generate_imports_tip_for_module(obj_to_complete, dir_comps=None, getattr=getattr, filter=lambda name: True):
    """
    @param obj_to_complete: the object from where we should get the completions
    @param dir_comps: if passed, we should not 'dir' the object and should just iterate those passed as a parameter
    @param getattr: the way to get a given object from the obj_to_complete (used for the completer)
    @param filter: a callable that receives the name and decides if it should be appended or not to the results
    @return: list of tuples, so that each tuple represents a completion with:
        name, doc, args, type (from the TYPE_* constants)
    """
    ret = []

    if dir_comps is None:
        dir_comps = dir_obj(obj_to_complete)

    for d in dir_comps:
        if d is None:
            continue

        if not filter(d):
            continue

        args = ""
        doc = ""
        retType = TYPE_BUILTIN

        try:
            obj = getattr(obj_to_complete, d)
        except (AttributeError, java.lang.NoClassDefFoundError):
            # jython has a bug in its custom classloader that prevents some things from working correctly, so, let's see if
            # we can fix that... (maybe fixing it in jython itself would be a better idea, as this is clearly a bug)
            # for that we need a custom classloader... we have references from it in the below places:
            #
            # http://mindprod.com/jgloss/classloader.html
            # http://www.javaworld.com/javaworld/jw-03-2000/jw-03-classload-p2.html
            # http://freshmeat.net/articles/view/1643/
            #
            # note: this only happens when we add things to the sys.path at runtime, if they are added to the classpath
            # before the run, everything goes fine.
            #
            # The code below ilustrates what I mean...
            #
            # import sys
            # sys.path.insert(1, r"C:\bin\eclipse310\plugins\org.junit_3.8.1\junit.jar" )
            #
            # import junit.framework
            # print_ dir(junit.framework) #shows the TestCase class here
            #
            # import junit.framework.TestCase
            #
            # raises the error:
            # Traceback (innermost last):
            #  File "<console>", line 1, in ?
            # ImportError: No module named TestCase
            #
            # whereas if we had added the jar to the classpath before, everything would be fine by now...

            ret.append((d, "", "", retType))
            # that's ok, private things cannot be gotten...
            continue
        else:
            isMet = ismethod(obj)
            if isMet[0] and isMet[1]:
                info = isMet[1][0]
                try:
                    args, vargs, kwargs = info.args, info.varargs, info.kwargs
                    doc = info.get_as_doc()
                    r = ""
                    for a in args:
                        if len(r) > 0:
                            r += ", "
                        r += format_arg(a)
                    args = "(%s)" % (r)
                except TypeError:
                    traceback.print_exc()
                    args = "()"

                retType = TYPE_FUNCTION

            elif isclass(obj):
                retType = TYPE_CLASS

            elif ismodule(obj):
                retType = TYPE_IMPORT

        # add token and doc to return - assure only strings.
        ret.append((d, doc, args, retType))

    return ret


if __name__ == "__main__":
    sys.path.append(r"D:\dev_programs\eclipse_3\310\eclipse\plugins\org.junit_3.8.1\junit.jar")
    sys.stdout.write("%s\n" % Find("junit.framework.TestCase"))

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\webhdfs.py ===
# https://hadoop.apache.org/docs/r1.0.4/webhdfs.html

import logging
import os
import secrets
import shutil
import tempfile
import uuid
from contextlib import suppress
from urllib.parse import quote

import requests

from ..spec import AbstractBufferedFile, AbstractFileSystem
from ..utils import infer_storage_options, tokenize

logger = logging.getLogger("webhdfs")


class WebHDFS(AbstractFileSystem):
    """
    Interface to HDFS over HTTP using the WebHDFS API. Supports also HttpFS gateways.

    Four auth mechanisms are supported:

    insecure: no auth is done, and the user is assumed to be whoever they
        say they are (parameter ``user``), or a predefined value such as
        "dr.who" if not given
    spnego: when kerberos authentication is enabled, auth is negotiated by
        requests_kerberos https://github.com/requests/requests-kerberos .
        This establishes a session based on existing kinit login and/or
        specified principal/password; parameters are passed with ``kerb_kwargs``
    token: uses an existing Hadoop delegation token from another secured
        service. Indeed, this client can also generate such tokens when
        not insecure. Note that tokens expire, but can be renewed (by a
        previously specified user) and may allow for proxying.
    basic-auth: used when both parameter ``user`` and parameter ``password``
        are provided.

    """

    tempdir = str(tempfile.gettempdir())
    protocol = "webhdfs", "webHDFS"

    def __init__(
        self,
        host,
        port=50070,
        kerberos=False,
        token=None,
        user=None,
        password=None,
        proxy_to=None,
        kerb_kwargs=None,
        data_proxy=None,
        use_https=False,
        session_cert=None,
        session_verify=True,
        **kwargs,
    ):
        """
        Parameters
        ----------
        host: str
            Name-node address
        port: int
            Port for webHDFS
        kerberos: bool
            Whether to authenticate with kerberos for this connection
        token: str or None
            If given, use this token on every call to authenticate. A user
            and user-proxy may be encoded in the token and should not be also
            given
        user: str or None
            If given, assert the user name to connect with
        password: str or None
            If given, assert the password to use for basic auth. If password
            is provided, user must be provided also
        proxy_to: str or None
            If given, the user has the authority to proxy, and this value is
            the user in who's name actions are taken
        kerb_kwargs: dict
            Any extra arguments for HTTPKerberosAuth, see
            `<https://github.com/requests/requests-kerberos/blob/master/requests_kerberos/kerberos_.py>`_
        data_proxy: dict, callable or None
            If given, map data-node addresses. This can be necessary if the
            HDFS cluster is behind a proxy, running on Docker or otherwise has
            a mismatch between the host-names given by the name-node and the
            address by which to refer to them from the client. If a dict,
            maps host names ``host->data_proxy[host]``; if a callable, full
            URLs are passed, and function must conform to
            ``url->data_proxy(url)``.
        use_https: bool
            Whether to connect to the Name-node using HTTPS instead of HTTP
        session_cert: str or Tuple[str, str] or None
            Path to a certificate file, or tuple of (cert, key) files to use
            for the requests.Session
        session_verify: str, bool or None
            Path to a certificate file to use for verifying the requests.Session.
        kwargs
        """
        if self._cached:
            return
        super().__init__(**kwargs)
        self.url = f"{'https' if use_https else 'http'}://{host}:{port}/webhdfs/v1"
        self.kerb = kerberos
        self.kerb_kwargs = kerb_kwargs or {}
        self.pars = {}
        self.proxy = data_proxy or {}
        if token is not None:
            if user is not None or proxy_to is not None:
                raise ValueError(
                    "If passing a delegation token, must not set "
                    "user or proxy_to, as these are encoded in the"
                    " token"
                )
            self.pars["delegation"] = token
        self.user = user
        self.password = password

        if password is not None:
            if user is None:
                raise ValueError(
                    "If passing a password, the user must also be"
                    "set in order to set up the basic-auth"
                )
        else:
            if user is not None:
                self.pars["user.name"] = user

        if proxy_to is not None:
            self.pars["doas"] = proxy_to
        if kerberos and user is not None:
            raise ValueError(
                "If using Kerberos auth, do not specify the "
                "user, this is handled by kinit."
            )

        self.session_cert = session_cert
        self.session_verify = session_verify

        self._connect()

        self._fsid = f"webhdfs_{tokenize(host, port)}"

    @property
    def fsid(self):
        return self._fsid

    def _connect(self):
        self.session = requests.Session()

        if self.session_cert:
            self.session.cert = self.session_cert

        self.session.verify = self.session_verify

        if self.kerb:
            from requests_kerberos import HTTPKerberosAuth

            self.session.auth = HTTPKerberosAuth(**self.kerb_kwargs)

        if self.user is not None and self.password is not None:
            from requests.auth import HTTPBasicAuth

            self.session.auth = HTTPBasicAuth(self.user, self.password)

    def _call(self, op, method="get", path=None, data=None, redirect=True, **kwargs):
        path = self._strip_protocol(path) if path is not None else ""
        url = self._apply_proxy(self.url + quote(path, safe="/="))
        args = kwargs.copy()
        args.update(self.pars)
        args["op"] = op.upper()
        logger.debug("sending %s with %s", url, method)
        out = self.session.request(
            method=method.upper(),
            url=url,
            params=args,
            data=data,
            allow_redirects=redirect,
        )
        if out.status_code in [400, 401, 403, 404, 500]:
            try:
                err = out.json()
                msg = err["RemoteException"]["message"]
                exp = err["RemoteException"]["exception"]
            except (ValueError, KeyError):
                pass
            else:
                if exp in ["IllegalArgumentException", "UnsupportedOperationException"]:
                    raise ValueError(msg)
                elif exp in ["SecurityException", "AccessControlException"]:
                    raise PermissionError(msg)
                elif exp in ["FileNotFoundException"]:
                    raise FileNotFoundError(msg)
                else:
                    raise RuntimeError(msg)
        out.raise_for_status()
        return out

    def _open(
        self,
        path,
        mode="rb",
        block_size=None,
        autocommit=True,
        replication=None,
        permissions=None,
        **kwargs,
    ):
        """

        Parameters
        ----------
        path: str
            File location
        mode: str
            'rb', 'wb', etc.
        block_size: int
            Client buffer size for read-ahead or write buffer
        autocommit: bool
            If False, writes to temporary file that only gets put in final
            location upon commit
        replication: int
            Number of copies of file on the cluster, write mode only
        permissions: str or int
            posix permissions, write mode only
        kwargs

        Returns
        -------
        WebHDFile instance
        """
        block_size = block_size or self.blocksize
        return WebHDFile(
            self,
            path,
            mode=mode,
            block_size=block_size,
            tempdir=self.tempdir,
            autocommit=autocommit,
            replication=replication,
            permissions=permissions,
        )

    @staticmethod
    def _process_info(info):
        info["type"] = info["type"].lower()
        info["size"] = info["length"]
        return info

    @classmethod
    def _strip_protocol(cls, path):
        return infer_storage_options(path)["path"]

    @staticmethod
    def _get_kwargs_from_urls(urlpath):
        out = infer_storage_options(urlpath)
        out.pop("path", None)
        out.pop("protocol", None)
        if "username" in out:
            out["user"] = out.pop("username")
        return out

    def info(self, path):
        out = self._call("GETFILESTATUS", path=path)
        info = out.json()["FileStatus"]
        info["name"] = path
        return self._process_info(info)

    def ls(self, path, detail=False):
        out = self._call("LISTSTATUS", path=path)
        infos = out.json()["FileStatuses"]["FileStatus"]
        for info in infos:
            self._process_info(info)
            info["name"] = path.rstrip("/") + "/" + info["pathSuffix"]
        if detail:
            return sorted(infos, key=lambda i: i["name"])
        else:
            return sorted(info["name"] for info in infos)

    def content_summary(self, path):
        """Total numbers of files, directories and bytes under path"""
        out = self._call("GETCONTENTSUMMARY", path=path)
        return out.json()["ContentSummary"]

    def ukey(self, path):
        """Checksum info of file, giving method and result"""
        out = self._call("GETFILECHECKSUM", path=path, redirect=False)
        if "Location" in out.headers:
            location = self._apply_proxy(out.headers["Location"])
            out2 = self.session.get(location)
            out2.raise_for_status()
            return out2.json()["FileChecksum"]
        else:
            out.raise_for_status()
            return out.json()["FileChecksum"]

    def home_directory(self):
        """Get user's home directory"""
        out = self._call("GETHOMEDIRECTORY")
        return out.json()["Path"]

    def get_delegation_token(self, renewer=None):
        """Retrieve token which can give the same authority to other uses

        Parameters
        ----------
        renewer: str or None
            User who may use this token; if None, will be current user
        """
        if renewer:
            out = self._call("GETDELEGATIONTOKEN", renewer=renewer)
        else:
            out = self._call("GETDELEGATIONTOKEN")
        t = out.json()["Token"]
        if t is None:
            raise ValueError("No token available for this user/security context")
        return t["urlString"]

    def renew_delegation_token(self, token):
        """Make token live longer. Returns new expiry time"""
        out = self._call("RENEWDELEGATIONTOKEN", method="put", token=token)
        return out.json()["long"]

    def cancel_delegation_token(self, token):
        """Stop the token from being useful"""
        self._call("CANCELDELEGATIONTOKEN", method="put", token=token)

    def chmod(self, path, mod):
        """Set the permission at path

        Parameters
        ----------
        path: str
            location to set (file or directory)
        mod: str or int
            posix epresentation or permission, give as oct string, e.g, '777'
            or 0o777
        """
        self._call("SETPERMISSION", method="put", path=path, permission=mod)

    def chown(self, path, owner=None, group=None):
        """Change owning user and/or group"""
        kwargs = {}
        if owner is not None:
            kwargs["owner"] = owner
        if group is not None:
            kwargs["group"] = group
        self._call("SETOWNER", method="put", path=path, **kwargs)

    def set_replication(self, path, replication):
        """
        Set file replication factor

        Parameters
        ----------
        path: str
            File location (not for directories)
        replication: int
            Number of copies of file on the cluster. Should be smaller than
            number of data nodes; normally 3 on most systems.
        """
        self._call("SETREPLICATION", path=path, method="put", replication=replication)

    def mkdir(self, path, **kwargs):
        self._call("MKDIRS", method="put", path=path)

    def makedirs(self, path, exist_ok=False):
        if exist_ok is False and self.exists(path):
            raise FileExistsError(path)
        self.mkdir(path)

    def mv(self, path1, path2, **kwargs):
        self._call("RENAME", method="put", path=path1, destination=path2)

    def rm(self, path, recursive=False, **kwargs):
        self._call(
            "DELETE",
            method="delete",
            path=path,
            recursive="true" if recursive else "false",
        )

    def rm_file(self, path, **kwargs):
        self.rm(path)

    def cp_file(self, lpath, rpath, **kwargs):
        with self.open(lpath) as lstream:
            tmp_fname = "/".join([self._parent(rpath), f".tmp.{secrets.token_hex(16)}"])
            # Perform an atomic copy (stream to a temporary file and
            # move it to the actual destination).
            try:
                with self.open(tmp_fname, "wb") as rstream:
                    shutil.copyfileobj(lstream, rstream)
                self.mv(tmp_fname, rpath)
            except BaseException:
                with suppress(FileNotFoundError):
                    self.rm(tmp_fname)
                raise

    def _apply_proxy(self, location):
        if self.proxy and callable(self.proxy):
            location = self.proxy(location)
        elif self.proxy:
            # as a dict
            for k, v in self.proxy.items():
                location = location.replace(k, v, 1)
        return location


class WebHDFile(AbstractBufferedFile):
    """A file living in HDFS over webHDFS"""

    def __init__(self, fs, path, **kwargs):
        super().__init__(fs, path, **kwargs)
        kwargs = kwargs.copy()
        if kwargs.get("permissions", None) is None:
            kwargs.pop("permissions", None)
        if kwargs.get("replication", None) is None:
            kwargs.pop("replication", None)
        self.permissions = kwargs.pop("permissions", 511)
        tempdir = kwargs.pop("tempdir")
        if kwargs.pop("autocommit", False) is False:
            self.target = self.path
            self.path = os.path.join(tempdir, str(uuid.uuid4()))

    def _upload_chunk(self, final=False):
        """Write one part of a multi-block file upload

        Parameters
        ==========
        final: bool
            This is the last block, so should complete file, if
            self.autocommit is True.
        """
        out = self.fs.session.post(
            self.location,
            data=self.buffer.getvalue(),
            headers={"content-type": "application/octet-stream"},
        )
        out.raise_for_status()
        return True

    def _initiate_upload(self):
        """Create remote file/upload"""
        kwargs = self.kwargs.copy()
        if "a" in self.mode:
            op, method = "APPEND", "POST"
        else:
            op, method = "CREATE", "PUT"
            kwargs["overwrite"] = "true"
        out = self.fs._call(op, method, self.path, redirect=False, **kwargs)
        location = self.fs._apply_proxy(out.headers["Location"])
        if "w" in self.mode:
            # create empty file to append to
            out2 = self.fs.session.put(
                location, headers={"content-type": "application/octet-stream"}
            )
            out2.raise_for_status()
            # after creating empty file, change location to append to
            out2 = self.fs._call("APPEND", "POST", self.path, redirect=False, **kwargs)
            self.location = self.fs._apply_proxy(out2.headers["Location"])

    def _fetch_range(self, start, end):
        start = max(start, 0)
        end = min(self.size, end)
        if start >= end or start >= self.size:
            return b""
        out = self.fs._call(
            "OPEN", path=self.path, offset=start, length=end - start, redirect=False
        )
        out.raise_for_status()
        if "Location" in out.headers:
            location = out.headers["Location"]
            out2 = self.fs.session.get(self.fs._apply_proxy(location))
            return out2.content
        else:
            return out.content

    def commit(self):
        self.fs.mv(self.path, self.target)

    def discard(self):
        self.fs.rm(self.path)

# === NexusCore/openenv\Lib\site-packages\google\api_core\operations_v1\transports\rest.py ===
# -*- coding: utf-8 -*-
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
#

from typing import Callable, Dict, Optional, Sequence, Tuple, Union

from requests import __version__ as requests_version

from google.api_core import exceptions as core_exceptions  # type: ignore
from google.api_core import gapic_v1  # type: ignore
from google.api_core import path_template  # type: ignore
from google.api_core import rest_helpers  # type: ignore
from google.api_core import retry as retries  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.requests import AuthorizedSession  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore
from google.protobuf import json_format  # type: ignore
import google.protobuf

import grpc
from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO, OperationsTransport

PROTOBUF_VERSION = google.protobuf.__version__

OptionalRetry = Union[retries.Retry, object]

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=f"requests@{requests_version}",
)


class OperationsRestTransport(OperationsTransport):
    """REST backend transport for Operations.

    Manages long-running operations with an API service.

    When an API method normally takes long time to complete, it can be
    designed to return [Operation][google.api_core.operations_v1.Operation] to the
    client, and the client can use this interface to receive the real
    response asynchronously by polling the operation resource, or pass
    the operation resource to another API (such as Google Cloud Pub/Sub
    API) to receive the response. Any API service that returns
    long-running operations should implement the ``Operations``
    interface so developers can have a consistent client experience.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1
    """

    def __init__(
        self,
        *,
        host: str = "longrunning.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        url_scheme: str = "https",
        http_options: Optional[Dict] = None,
        path_prefix: str = "v1",
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to.
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.

            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if ``channel`` is provided.

                .. warning::
                    Important: If you accept a credential configuration (credential JSON/File/Stream)
                    from an external source for authentication to Google Cloud Platform, you must
                    validate it before providing it to any Google API or client library. Providing an
                    unvalidated credential configuration to Google APIs or libraries can compromise
                    the security of your systems and data. For more information, refer to
                    `Validate credential configurations from external sources`_.

                .. _Validate credential configurations from external sources:

                https://cloud.google.com/docs/authentication/external/externally-sourced-credentials
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if ``channel`` is provided.
            client_cert_source_for_mtls (Callable[[], Tuple[bytes, bytes]]): Client
                certificate to configure mutual TLS HTTP channel. It is ignored
                if ``channel`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
            http_options: a dictionary of http_options for transcoding, to override
                the defaults from operations.proto.  Each method has an entry
                with the corresponding http rules as value.
            path_prefix: path prefix (usually represents API version). Set to
                "v1" by default.

        """
        # Run the base constructor
        # TODO(yon-mg): resolve other ctor params i.e. scopes, quota, etc.
        # TODO: When custom host (api_endpoint) is set, `scopes` must *also* be set on the
        # credentials object
        super().__init__(
            host=host,
            credentials=credentials,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
        )
        self._session = AuthorizedSession(
            self._credentials, default_host=self.DEFAULT_HOST
        )
        if client_cert_source_for_mtls:
            self._session.configure_mtls_channel(client_cert_source_for_mtls)
        # TODO(https://github.com/googleapis/python-api-core/issues/720): Add wrap logic directly to the property methods for callables.
        self._prep_wrapped_messages(client_info)
        self._http_options = http_options or {}
        self._path_prefix = path_prefix

    def _list_operations(
        self,
        request: operations_pb2.ListOperationsRequest,
        *,
        # TODO(https://github.com/googleapis/python-api-core/issues/723): Leverage `retry`
        # to allow configuring retryable error codes.
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Optional[float] = None,
        compression: Optional[grpc.Compression] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operations_pb2.ListOperationsResponse:
        r"""Call the list operations method over HTTP.

        Args:
            request (~.operations_pb2.ListOperationsRequest):
                The request object. The request message for
                [Operations.ListOperations][google.api_core.operations_v1.Operations.ListOperations].

            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            ~.operations_pb2.ListOperationsResponse:
                The response message for
                [Operations.ListOperations][google.api_core.operations_v1.Operations.ListOperations].

        """

        http_options = [
            {
                "method": "get",
                "uri": "/{}/{{name=**}}/operations".format(self._path_prefix),
            },
        ]
        if "google.longrunning.Operations.ListOperations" in self._http_options:
            http_options = self._http_options[
                "google.longrunning.Operations.ListOperations"
            ]

        request_kwargs = self._convert_protobuf_message_to_dict(request)
        transcoded_request = path_template.transcode(http_options, **request_kwargs)

        uri = transcoded_request["uri"]
        method = transcoded_request["method"]

        # Jsonify the query params
        query_params_request = operations_pb2.ListOperationsRequest()
        json_format.ParseDict(transcoded_request["query_params"], query_params_request)
        query_params = json_format.MessageToDict(
            query_params_request,
            preserving_proto_field_name=False,
            use_integers_for_enums=False,
        )

        # Send the request
        headers = dict(metadata)
        headers["Content-Type"] = "application/json"
        # TODO(https://github.com/googleapis/python-api-core/issues/721): Update incorrect use of `uri`` variable name.
        response = getattr(self._session, method)(
            "{host}{uri}".format(host=self._host, uri=uri),
            timeout=timeout,
            headers=headers,
            params=rest_helpers.flatten_query_params(query_params),
        )

        # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
        # subclass.
        if response.status_code >= 400:
            raise core_exceptions.from_http_response(response)

        # Return the response
        api_response = operations_pb2.ListOperationsResponse()
        json_format.Parse(response.content, api_response, ignore_unknown_fields=False)
        return api_response

    def _get_operation(
        self,
        request: operations_pb2.GetOperationRequest,
        *,
        # TODO(https://github.com/googleapis/python-api-core/issues/723): Leverage `retry`
        # to allow configuring retryable error codes.
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Optional[float] = None,
        compression: Optional[grpc.Compression] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operations_pb2.Operation:
        r"""Call the get operation method over HTTP.

        Args:
            request (~.operations_pb2.GetOperationRequest):
                The request object. The request message for
                [Operations.GetOperation][google.api_core.operations_v1.Operations.GetOperation].

            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            ~.operations_pb2.Operation:
                This resource represents a long-
                running operation that is the result of a
                network API call.

        """

        http_options = [
            {
                "method": "get",
                "uri": "/{}/{{name=**/operations/*}}".format(self._path_prefix),
            },
        ]
        if "google.longrunning.Operations.GetOperation" in self._http_options:
            http_options = self._http_options[
                "google.longrunning.Operations.GetOperation"
            ]

        request_kwargs = self._convert_protobuf_message_to_dict(request)
        transcoded_request = path_template.transcode(http_options, **request_kwargs)

        uri = transcoded_request["uri"]
        method = transcoded_request["method"]

        # Jsonify the query params
        query_params_request = operations_pb2.GetOperationRequest()
        json_format.ParseDict(transcoded_request["query_params"], query_params_request)
        query_params = json_format.MessageToDict(
            query_params_request,
            preserving_proto_field_name=False,
            use_integers_for_enums=False,
        )

        # Send the request
        headers = dict(metadata)
        headers["Content-Type"] = "application/json"
        # TODO(https://github.com/googleapis/python-api-core/issues/721): Update incorrect use of `uri`` variable name.
        response = getattr(self._session, method)(
            "{host}{uri}".format(host=self._host, uri=uri),
            timeout=timeout,
            headers=headers,
            params=rest_helpers.flatten_query_params(query_params),
        )

        # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
        # subclass.
        if response.status_code >= 400:
            raise core_exceptions.from_http_response(response)

        # Return the response
        api_response = operations_pb2.Operation()
        json_format.Parse(response.content, api_response, ignore_unknown_fields=False)
        return api_response

    def _delete_operation(
        self,
        request: operations_pb2.DeleteOperationRequest,
        *,
        # TODO(https://github.com/googleapis/python-api-core/issues/723): Leverage `retry`
        # to allow configuring retryable error codes.
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Optional[float] = None,
        compression: Optional[grpc.Compression] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> empty_pb2.Empty:
        r"""Call the delete operation method over HTTP.

        Args:
            request (~.operations_pb2.DeleteOperationRequest):
                The request object. The request message for
                [Operations.DeleteOperation][google.api_core.operations_v1.Operations.DeleteOperation].

            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """

        http_options = [
            {
                "method": "delete",
                "uri": "/{}/{{name=**/operations/*}}".format(self._path_prefix),
            },
        ]
        if "google.longrunning.Operations.DeleteOperation" in self._http_options:
            http_options = self._http_options[
                "google.longrunning.Operations.DeleteOperation"
            ]

        request_kwargs = self._convert_protobuf_message_to_dict(request)
        transcoded_request = path_template.transcode(http_options, **request_kwargs)

        uri = transcoded_request["uri"]
        method = transcoded_request["method"]

        # Jsonify the query params
        query_params_request = operations_pb2.DeleteOperationRequest()
        json_format.ParseDict(transcoded_request["query_params"], query_params_request)
        query_params = json_format.MessageToDict(
            query_params_request,
            preserving_proto_field_name=False,
            use_integers_for_enums=False,
        )

        # Send the request
        headers = dict(metadata)
        headers["Content-Type"] = "application/json"
        # TODO(https://github.com/googleapis/python-api-core/issues/721): Update incorrect use of `uri`` variable name.
        response = getattr(self._session, method)(
            "{host}{uri}".format(host=self._host, uri=uri),
            timeout=timeout,
            headers=headers,
            params=rest_helpers.flatten_query_params(query_params),
        )

        # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
        # subclass.
        if response.status_code >= 400:
            raise core_exceptions.from_http_response(response)

        return empty_pb2.Empty()

    def _cancel_operation(
        self,
        request: operations_pb2.CancelOperationRequest,
        *,
        # TODO(https://github.com/googleapis/python-api-core/issues/723): Leverage `retry`
        # to allow configuring retryable error codes.
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Optional[float] = None,
        compression: Optional[grpc.Compression] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> empty_pb2.Empty:
        r"""Call the cancel operation method over HTTP.

        Args:
            request (~.operations_pb2.CancelOperationRequest):
                The request object. The request message for
                [Operations.CancelOperation][google.api_core.operations_v1.Operations.CancelOperation].

            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """

        http_options = [
            {
                "method": "post",
                "uri": "/{}/{{name=**/operations/*}}:cancel".format(self._path_prefix),
                "body": "*",
            },
        ]
        if "google.longrunning.Operations.CancelOperation" in self._http_options:
            http_options = self._http_options[
                "google.longrunning.Operations.CancelOperation"
            ]

        request_kwargs = self._convert_protobuf_message_to_dict(request)
        transcoded_request = path_template.transcode(http_options, **request_kwargs)

        # Jsonify the request body
        body_request = operations_pb2.CancelOperationRequest()
        json_format.ParseDict(transcoded_request["body"], body_request)
        body = json_format.MessageToDict(
            body_request,
            preserving_proto_field_name=False,
            use_integers_for_enums=False,
        )
        uri = transcoded_request["uri"]
        method = transcoded_request["method"]

        # Jsonify the query params
        query_params_request = operations_pb2.CancelOperationRequest()
        json_format.ParseDict(transcoded_request["query_params"], query_params_request)
        query_params = json_format.MessageToDict(
            query_params_request,
            preserving_proto_field_name=False,
            use_integers_for_enums=False,
        )

        # Send the request
        headers = dict(metadata)
        headers["Content-Type"] = "application/json"
        # TODO(https://github.com/googleapis/python-api-core/issues/721): Update incorrect use of `uri`` variable name.
        response = getattr(self._session, method)(
            "{host}{uri}".format(host=self._host, uri=uri),
            timeout=timeout,
            headers=headers,
            params=rest_helpers.flatten_query_params(query_params),
            data=body,
        )

        # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
        # subclass.
        if response.status_code >= 400:
            raise core_exceptions.from_http_response(response)

        return empty_pb2.Empty()

    @property
    def list_operations(
        self,
    ) -> Callable[
        [operations_pb2.ListOperationsRequest], operations_pb2.ListOperationsResponse
    ]:
        return self._list_operations

    @property
    def get_operation(
        self,
    ) -> Callable[[operations_pb2.GetOperationRequest], operations_pb2.Operation]:
        return self._get_operation

    @property
    def delete_operation(
        self,
    ) -> Callable[[operations_pb2.DeleteOperationRequest], empty_pb2.Empty]:
        return self._delete_operation

    @property
    def cancel_operation(
        self,
    ) -> Callable[[operations_pb2.CancelOperationRequest], empty_pb2.Empty]:
        return self._cancel_operation


__all__ = ("OperationsRestTransport",)

# === NexusCore/openenv\Lib\site-packages\jsonschema\exceptions.py ===
"""
Validation errors, and some surrounding helpers.
"""
from __future__ import annotations

from collections import defaultdict, deque
from pprint import pformat
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Any, ClassVar
import heapq
import warnings

from attrs import define
from referencing.exceptions import Unresolvable as _Unresolvable

from jsonschema import _utils

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, MutableMapping, Sequence

    from jsonschema import _types

WEAK_MATCHES: frozenset[str] = frozenset(["anyOf", "oneOf"])
STRONG_MATCHES: frozenset[str] = frozenset()

_unset = _utils.Unset()


def _pretty(thing: Any, prefix: str):
    """
    Format something for an error message as prettily as we currently can.
    """
    return indent(pformat(thing, width=72, sort_dicts=False), prefix).lstrip()


def __getattr__(name):
    if name == "RefResolutionError":
        warnings.warn(
            _RefResolutionError._DEPRECATION_MESSAGE,
            DeprecationWarning,
            stacklevel=2,
        )
        return _RefResolutionError
    raise AttributeError(f"module {__name__} has no attribute {name}")


class _Error(Exception):

    _word_for_schema_in_error_message: ClassVar[str]
    _word_for_instance_in_error_message: ClassVar[str]

    def __init__(
        self,
        message: str,
        validator: str = _unset,  # type: ignore[assignment]
        path: Iterable[str | int] = (),
        cause: Exception | None = None,
        context=(),
        validator_value: Any = _unset,
        instance: Any = _unset,
        schema: Mapping[str, Any] | bool = _unset,  # type: ignore[assignment]
        schema_path: Iterable[str | int] = (),
        parent: _Error | None = None,
        type_checker: _types.TypeChecker = _unset,  # type: ignore[assignment]
    ) -> None:
        super().__init__(
            message,
            validator,
            path,
            cause,
            context,
            validator_value,
            instance,
            schema,
            schema_path,
            parent,
        )
        self.message = message
        self.path = self.relative_path = deque(path)
        self.schema_path = self.relative_schema_path = deque(schema_path)
        self.context = list(context)
        self.cause = self.__cause__ = cause
        self.validator = validator
        self.validator_value = validator_value
        self.instance = instance
        self.schema = schema
        self.parent = parent
        self._type_checker = type_checker

        for error in context:
            error.parent = self

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.message!r}>"

    def __str__(self) -> str:
        essential_for_verbose = (
            self.validator, self.validator_value, self.instance, self.schema,
        )
        if any(m is _unset for m in essential_for_verbose):
            return self.message

        schema_path = _utils.format_as_index(
            container=self._word_for_schema_in_error_message,
            indices=list(self.relative_schema_path)[:-1],
        )
        instance_path = _utils.format_as_index(
            container=self._word_for_instance_in_error_message,
            indices=self.relative_path,
        )
        prefix = 16 * " "

        return dedent(
            f"""\
            {self.message}

            Failed validating {self.validator!r} in {schema_path}:
                {_pretty(self.schema, prefix=prefix)}

            On {instance_path}:
                {_pretty(self.instance, prefix=prefix)}
            """.rstrip(),
        )

    @classmethod
    def create_from(cls, other: _Error):
        return cls(**other._contents())

    @property
    def absolute_path(self) -> Sequence[str | int]:
        parent = self.parent
        if parent is None:
            return self.relative_path

        path = deque(self.relative_path)
        path.extendleft(reversed(parent.absolute_path))
        return path

    @property
    def absolute_schema_path(self) -> Sequence[str | int]:
        parent = self.parent
        if parent is None:
            return self.relative_schema_path

        path = deque(self.relative_schema_path)
        path.extendleft(reversed(parent.absolute_schema_path))
        return path

    @property
    def json_path(self) -> str:
        path = "$"
        for elem in self.absolute_path:
            if isinstance(elem, int):
                path += "[" + str(elem) + "]"
            else:
                path += "." + elem
        return path

    def _set(
        self,
        type_checker: _types.TypeChecker | None = None,
        **kwargs: Any,
    ) -> None:
        if type_checker is not None and self._type_checker is _unset:
            self._type_checker = type_checker

        for k, v in kwargs.items():
            if getattr(self, k) is _unset:
                setattr(self, k, v)

    def _contents(self):
        attrs = (
            "message", "cause", "context", "validator", "validator_value",
            "path", "schema_path", "instance", "schema", "parent",
        )
        return {attr: getattr(self, attr) for attr in attrs}

    def _matches_type(self) -> bool:
        try:
            # We ignore this as we want to simply crash if this happens
            expected = self.schema["type"]  # type: ignore[index]
        except (KeyError, TypeError):
            return False

        if isinstance(expected, str):
            return self._type_checker.is_type(self.instance, expected)

        return any(
            self._type_checker.is_type(self.instance, expected_type)
            for expected_type in expected
        )


class ValidationError(_Error):
    """
    An instance was invalid under a provided schema.
    """

    _word_for_schema_in_error_message = "schema"
    _word_for_instance_in_error_message = "instance"


class SchemaError(_Error):
    """
    A schema was invalid under its corresponding metaschema.
    """

    _word_for_schema_in_error_message = "metaschema"
    _word_for_instance_in_error_message = "schema"


@define(slots=False)
class _RefResolutionError(Exception):
    """
    A ref could not be resolved.
    """

    _DEPRECATION_MESSAGE = (
        "jsonschema.exceptions.RefResolutionError is deprecated as of version "
        "4.18.0. If you wish to catch potential reference resolution errors, "
        "directly catch referencing.exceptions.Unresolvable."
    )

    _cause: Exception

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented  # pragma: no cover -- uncovered but deprecated  # noqa: E501
        return self._cause == other._cause

    def __str__(self) -> str:
        return str(self._cause)


class _WrappedReferencingError(_RefResolutionError, _Unresolvable):  # pragma: no cover -- partially uncovered but to be removed  # noqa: E501
    def __init__(self, cause: _Unresolvable):
        object.__setattr__(self, "_wrapped", cause)

    def __eq__(self, other):
        if other.__class__ is self.__class__:
            return self._wrapped == other._wrapped
        elif other.__class__ is self._wrapped.__class__:
            return self._wrapped == other
        return NotImplemented

    def __getattr__(self, attr):
        return getattr(self._wrapped, attr)

    def __hash__(self):
        return hash(self._wrapped)

    def __repr__(self):
        return f"<WrappedReferencingError {self._wrapped!r}>"

    def __str__(self):
        return f"{self._wrapped.__class__.__name__}: {self._wrapped}"


class UndefinedTypeCheck(Exception):
    """
    A type checker was asked to check a type it did not have registered.
    """

    def __init__(self, type: str) -> None:
        self.type = type

    def __str__(self) -> str:
        return f"Type {self.type!r} is unknown to this type checker"


class UnknownType(Exception):
    """
    A validator was asked to validate an instance against an unknown type.
    """

    def __init__(self, type, instance, schema):
        self.type = type
        self.instance = instance
        self.schema = schema

    def __str__(self):
        prefix = 16 * " "

        return dedent(
            f"""\
            Unknown type {self.type!r} for validator with schema:
                {_pretty(self.schema, prefix=prefix)}

            While checking instance:
                {_pretty(self.instance, prefix=prefix)}
            """.rstrip(),
        )


class FormatError(Exception):
    """
    Validating a format failed.
    """

    def __init__(self, message, cause=None):
        super().__init__(message, cause)
        self.message = message
        self.cause = self.__cause__ = cause

    def __str__(self):
        return self.message


class ErrorTree:
    """
    ErrorTrees make it easier to check which validations failed.
    """

    _instance = _unset

    def __init__(self, errors: Iterable[ValidationError] = ()):
        self.errors: MutableMapping[str, ValidationError] = {}
        self._contents: Mapping[str, ErrorTree] = defaultdict(self.__class__)

        for error in errors:
            container = self
            for element in error.path:
                container = container[element]
            container.errors[error.validator] = error

            container._instance = error.instance

    def __contains__(self, index: str | int):
        """
        Check whether ``instance[index]`` has any errors.
        """
        return index in self._contents

    def __getitem__(self, index):
        """
        Retrieve the child tree one level down at the given ``index``.

        If the index is not in the instance that this tree corresponds
        to and is not known by this tree, whatever error would be raised
        by ``instance.__getitem__`` will be propagated (usually this is
        some subclass of `LookupError`.
        """
        if self._instance is not _unset and index not in self:
            self._instance[index]
        return self._contents[index]

    def __setitem__(self, index: str | int, value: ErrorTree):
        """
        Add an error to the tree at the given ``index``.

        .. deprecated:: v4.20.0

            Setting items on an `ErrorTree` is deprecated without replacement.
            To populate a tree, provide all of its sub-errors when you
            construct the tree.
        """
        warnings.warn(
            "ErrorTree.__setitem__ is deprecated without replacement.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._contents[index] = value  # type: ignore[index]

    def __iter__(self):
        """
        Iterate (non-recursively) over the indices in the instance with errors.
        """
        return iter(self._contents)

    def __len__(self):
        """
        Return the `total_errors`.
        """
        return self.total_errors

    def __repr__(self):
        total = len(self)
        errors = "error" if total == 1 else "errors"
        return f"<{self.__class__.__name__} ({total} total {errors})>"

    @property
    def total_errors(self):
        """
        The total number of errors in the entire tree, including children.
        """
        child_errors = sum(len(tree) for _, tree in self._contents.items())
        return len(self.errors) + child_errors


def by_relevance(weak=WEAK_MATCHES, strong=STRONG_MATCHES):
    """
    Create a key function that can be used to sort errors by relevance.

    Arguments:
        weak (set):
            a collection of validation keywords to consider to be
            "weak".  If there are two errors at the same level of the
            instance and one is in the set of weak validation keywords,
            the other error will take priority. By default, :kw:`anyOf`
            and :kw:`oneOf` are considered weak keywords and will be
            superseded by other same-level validation errors.

        strong (set):
            a collection of validation keywords to consider to be
            "strong"

    """

    def relevance(error):
        validator = error.validator
        return (                        # prefer errors which are ...
            -len(error.path),           # 'deeper' and thereby more specific
            error.path,                 # earlier (for sibling errors)
            validator not in weak,      # for a non-low-priority keyword
            validator in strong,        # for a high priority keyword
            not error._matches_type(),  # at least match the instance's type
        )                               # otherwise we'll treat them the same

    return relevance


relevance = by_relevance()
"""
A key function (e.g. to use with `sorted`) which sorts errors by relevance.

Example:

.. code:: python

    sorted(validator.iter_errors(12), key=jsonschema.exceptions.relevance)
"""


def best_match(errors, key=relevance):
    """
    Try to find an error that appears to be the best match among given errors.

    In general, errors that are higher up in the instance (i.e. for which
    `ValidationError.path` is shorter) are considered better matches,
    since they indicate "more" is wrong with the instance.

    If the resulting match is either :kw:`oneOf` or :kw:`anyOf`, the
    *opposite* assumption is made -- i.e. the deepest error is picked,
    since these keywords only need to match once, and any other errors
    may not be relevant.

    Arguments:
        errors (collections.abc.Iterable):

            the errors to select from. Do not provide a mixture of
            errors from different validation attempts (i.e. from
            different instances or schemas), since it won't produce
            sensical output.

        key (collections.abc.Callable):

            the key to use when sorting errors. See `relevance` and
            transitively `by_relevance` for more details (the default is
            to sort with the defaults of that function). Changing the
            default is only useful if you want to change the function
            that rates errors but still want the error context descent
            done by this function.

    Returns:
        the best matching error, or ``None`` if the iterable was empty

    .. note::

        This function is a heuristic. Its return value may change for a given
        set of inputs from version to version if better heuristics are added.

    """
    best = max(errors, key=key, default=None)
    if best is None:
        return

    while best.context:
        # Calculate the minimum via nsmallest, because we don't recurse if
        # all nested errors have the same relevance (i.e. if min == max == all)
        smallest = heapq.nsmallest(2, best.context, key=key)
        if len(smallest) == 2 and key(smallest[0]) == key(smallest[1]):  # noqa: PLR2004
            return best
        best = smallest[0]
    return best

# === NexusCore/openenv\Lib\site-packages\psutil\_compat.py ===
# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module which provides compatibility with older Python versions.
This is more future-compatible rather than the opposite (prefer latest
Python 3 way of doing things).
"""

import collections
import contextlib
import errno
import functools
import os
import sys
import types


# fmt: off
__all__ = [
    # constants
    "PY3",
    # builtins
    "long", "range", "super", "unicode", "basestring",
    # literals
    "u", "b",
    # collections module
    "lru_cache",
    # shutil module
    "which", "get_terminal_size",
    # contextlib module
    "redirect_stderr",
    # python 3 exceptions
    "FileNotFoundError", "PermissionError", "ProcessLookupError",
    "InterruptedError", "ChildProcessError", "FileExistsError",
]
# fmt: on


PY3 = sys.version_info[0] >= 3
_SENTINEL = object()

if PY3:
    long = int
    xrange = range
    unicode = str
    basestring = str
    range = range

    def u(s):
        return s

    def b(s):
        return s.encode("latin-1")

else:
    long = long
    range = xrange
    unicode = unicode
    basestring = basestring

    def u(s):
        return unicode(s, "unicode_escape")

    def b(s):
        return s


# --- builtins


# Python 3 super().
# Taken from "future" package.
# Credit: Ryan Kelly
if PY3:
    super = super
else:
    _builtin_super = super

    def super(type_=_SENTINEL, type_or_obj=_SENTINEL, framedepth=1):
        """Like Python 3 builtin super(). If called without any arguments
        it attempts to infer them at runtime.
        """
        if type_ is _SENTINEL:
            f = sys._getframe(framedepth)
            try:
                # Get the function's first positional argument.
                type_or_obj = f.f_locals[f.f_code.co_varnames[0]]
            except (IndexError, KeyError):
                msg = 'super() used in a function with no args'
                raise RuntimeError(msg)
            try:
                # Get the MRO so we can crawl it.
                mro = type_or_obj.__mro__
            except (AttributeError, RuntimeError):
                try:
                    mro = type_or_obj.__class__.__mro__
                except AttributeError:
                    msg = 'super() used in a non-newstyle class'
                    raise RuntimeError(msg)
            for type_ in mro:
                #  Find the class that owns the currently-executing method.
                for meth in type_.__dict__.values():
                    # Drill down through any wrappers to the underlying func.
                    # This handles e.g. classmethod() and staticmethod().
                    try:
                        while not isinstance(meth, types.FunctionType):
                            if isinstance(meth, property):
                                # Calling __get__ on the property will invoke
                                # user code which might throw exceptions or
                                # have side effects
                                meth = meth.fget
                            else:
                                try:
                                    meth = meth.__func__
                                except AttributeError:
                                    meth = meth.__get__(type_or_obj, type_)
                    except (AttributeError, TypeError):
                        continue
                    if meth.func_code is f.f_code:
                        break  # found
                else:
                    # Not found. Move onto the next class in MRO.
                    continue
                break  # found
            else:
                msg = 'super() called outside a method'
                raise RuntimeError(msg)

        # Dispatch to builtin super().
        if type_or_obj is not _SENTINEL:
            return _builtin_super(type_, type_or_obj)
        return _builtin_super(type_)


# --- exceptions


if PY3:
    FileNotFoundError = FileNotFoundError  # NOQA
    PermissionError = PermissionError  # NOQA
    ProcessLookupError = ProcessLookupError  # NOQA
    InterruptedError = InterruptedError  # NOQA
    ChildProcessError = ChildProcessError  # NOQA
    FileExistsError = FileExistsError  # NOQA
else:
    # https://github.com/PythonCharmers/python-future/blob/exceptions/
    #     src/future/types/exceptions/pep3151.py
    import platform

    def _instance_checking_exception(base_exception=Exception):
        def wrapped(instance_checker):
            class TemporaryClass(base_exception):
                def __init__(self, *args, **kwargs):
                    if len(args) == 1 and isinstance(args[0], TemporaryClass):
                        unwrap_me = args[0]
                        for attr in dir(unwrap_me):
                            if not attr.startswith('__'):
                                setattr(self, attr, getattr(unwrap_me, attr))
                    else:
                        super(TemporaryClass, self).__init__(  # noqa
                            *args, **kwargs
                        )

                class __metaclass__(type):
                    def __instancecheck__(cls, inst):
                        return instance_checker(inst)

                    def __subclasscheck__(cls, classinfo):
                        value = sys.exc_info()[1]
                        return isinstance(value, cls)

            TemporaryClass.__name__ = instance_checker.__name__
            TemporaryClass.__doc__ = instance_checker.__doc__
            return TemporaryClass

        return wrapped

    @_instance_checking_exception(EnvironmentError)
    def FileNotFoundError(inst):
        return getattr(inst, 'errno', _SENTINEL) == errno.ENOENT

    @_instance_checking_exception(EnvironmentError)
    def ProcessLookupError(inst):
        return getattr(inst, 'errno', _SENTINEL) == errno.ESRCH

    @_instance_checking_exception(EnvironmentError)
    def PermissionError(inst):
        return getattr(inst, 'errno', _SENTINEL) in (errno.EACCES, errno.EPERM)

    @_instance_checking_exception(EnvironmentError)
    def InterruptedError(inst):
        return getattr(inst, 'errno', _SENTINEL) == errno.EINTR

    @_instance_checking_exception(EnvironmentError)
    def ChildProcessError(inst):
        return getattr(inst, 'errno', _SENTINEL) == errno.ECHILD

    @_instance_checking_exception(EnvironmentError)
    def FileExistsError(inst):
        return getattr(inst, 'errno', _SENTINEL) == errno.EEXIST

    if platform.python_implementation() != "CPython":
        try:
            raise OSError(errno.EEXIST, "perm")
        except FileExistsError:
            pass
        except OSError:
            msg = (
                "broken or incompatible Python implementation, see: "
                "https://github.com/giampaolo/psutil/issues/1659"
            )
            raise RuntimeError(msg)


# --- stdlib additions


# py 3.2 functools.lru_cache
# Taken from: http://code.activestate.com/recipes/578078
# Credit: Raymond Hettinger
try:
    from functools import lru_cache
except ImportError:
    try:
        from threading import RLock
    except ImportError:
        from dummy_threading import RLock

    _CacheInfo = collections.namedtuple(
        "CacheInfo", ["hits", "misses", "maxsize", "currsize"]
    )

    class _HashedSeq(list):
        __slots__ = ('hashvalue',)

        def __init__(self, tup, hash=hash):
            self[:] = tup
            self.hashvalue = hash(tup)

        def __hash__(self):
            return self.hashvalue

    def _make_key(
        args,
        kwds,
        typed,
        kwd_mark=(_SENTINEL,),
        fasttypes=set((int, str, frozenset, type(None))),  # noqa
        sorted=sorted,
        tuple=tuple,
        type=type,
        len=len,
    ):
        key = args
        if kwds:
            sorted_items = sorted(kwds.items())
            key += kwd_mark
            for item in sorted_items:
                key += item
        if typed:
            key += tuple(type(v) for v in args)
            if kwds:
                key += tuple(type(v) for k, v in sorted_items)
        elif len(key) == 1 and type(key[0]) in fasttypes:
            return key[0]
        return _HashedSeq(key)

    def lru_cache(maxsize=100, typed=False):
        """Least-recently-used cache decorator, see:
        http://docs.python.org/3/library/functools.html#functools.lru_cache.
        """

        def decorating_function(user_function):
            cache = {}
            stats = [0, 0]
            HITS, MISSES = 0, 1
            make_key = _make_key
            cache_get = cache.get
            _len = len
            lock = RLock()
            root = []
            root[:] = [root, root, None, None]
            nonlocal_root = [root]
            PREV, NEXT, KEY, RESULT = 0, 1, 2, 3
            if maxsize == 0:

                def wrapper(*args, **kwds):
                    result = user_function(*args, **kwds)
                    stats[MISSES] += 1
                    return result

            elif maxsize is None:

                def wrapper(*args, **kwds):
                    key = make_key(args, kwds, typed)
                    result = cache_get(key, root)
                    if result is not root:
                        stats[HITS] += 1
                        return result
                    result = user_function(*args, **kwds)
                    cache[key] = result
                    stats[MISSES] += 1
                    return result

            else:

                def wrapper(*args, **kwds):
                    if kwds or typed:
                        key = make_key(args, kwds, typed)
                    else:
                        key = args
                    lock.acquire()
                    try:
                        link = cache_get(key)
                        if link is not None:
                            (root,) = nonlocal_root
                            link_prev, link_next, key, result = link
                            link_prev[NEXT] = link_next
                            link_next[PREV] = link_prev
                            last = root[PREV]
                            last[NEXT] = root[PREV] = link
                            link[PREV] = last
                            link[NEXT] = root
                            stats[HITS] += 1
                            return result
                    finally:
                        lock.release()
                    result = user_function(*args, **kwds)
                    lock.acquire()
                    try:
                        (root,) = nonlocal_root
                        if key in cache:
                            pass
                        elif _len(cache) >= maxsize:
                            oldroot = root
                            oldroot[KEY] = key
                            oldroot[RESULT] = result
                            root = nonlocal_root[0] = oldroot[NEXT]
                            oldkey = root[KEY]
                            root[KEY] = root[RESULT] = None
                            del cache[oldkey]
                            cache[key] = oldroot
                        else:
                            last = root[PREV]
                            link = [last, root, key, result]
                            last[NEXT] = root[PREV] = cache[key] = link
                        stats[MISSES] += 1
                    finally:
                        lock.release()
                    return result

            def cache_info():
                """Report cache statistics."""
                lock.acquire()
                try:
                    return _CacheInfo(
                        stats[HITS], stats[MISSES], maxsize, len(cache)
                    )
                finally:
                    lock.release()

            def cache_clear():
                """Clear the cache and cache statistics."""
                lock.acquire()
                try:
                    cache.clear()
                    root = nonlocal_root[0]
                    root[:] = [root, root, None, None]
                    stats[:] = [0, 0]
                finally:
                    lock.release()

            wrapper.__wrapped__ = user_function
            wrapper.cache_info = cache_info
            wrapper.cache_clear = cache_clear
            return functools.update_wrapper(wrapper, user_function)

        return decorating_function


# python 3.3
try:
    from shutil import which
except ImportError:

    def which(cmd, mode=os.F_OK | os.X_OK, path=None):
        """Given a command, mode, and a PATH string, return the path which
        conforms to the given mode on the PATH, or None if there is no such
        file.

        `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
        of os.environ.get("PATH"), or can be overridden with a custom search
        path.
        """

        def _access_check(fn, mode):
            return (
                os.path.exists(fn)
                and os.access(fn, mode)
                and not os.path.isdir(fn)
            )

        if os.path.dirname(cmd):
            if _access_check(cmd, mode):
                return cmd
            return None

        if path is None:
            path = os.environ.get("PATH", os.defpath)
        if not path:
            return None
        path = path.split(os.pathsep)

        if sys.platform == "win32":
            if os.curdir not in path:
                path.insert(0, os.curdir)

            pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
            if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
                files = [cmd]
            else:
                files = [cmd + ext for ext in pathext]
        else:
            files = [cmd]

        seen = set()
        for dir in path:
            normdir = os.path.normcase(dir)
            if normdir not in seen:
                seen.add(normdir)
                for thefile in files:
                    name = os.path.join(dir, thefile)
                    if _access_check(name, mode):
                        return name
        return None


# python 3.3
try:
    from shutil import get_terminal_size
except ImportError:

    def get_terminal_size(fallback=(80, 24)):
        try:
            import fcntl
            import struct
            import termios
        except ImportError:
            return fallback
        else:
            try:
                # This should work on Linux.
                res = struct.unpack(
                    'hh', fcntl.ioctl(1, termios.TIOCGWINSZ, '1234')
                )
                return (res[1], res[0])
            except Exception:  # noqa: BLE001
                return fallback


# python 3.3
try:
    from subprocess import TimeoutExpired as SubprocessTimeoutExpired
except ImportError:

    class SubprocessTimeoutExpired(Exception):
        pass


# python 3.5
try:
    from contextlib import redirect_stderr
except ImportError:

    @contextlib.contextmanager
    def redirect_stderr(new_target):
        original = sys.stderr
        try:
            sys.stderr = new_target
            yield new_target
        finally:
            sys.stderr = original

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\_spinners.py ===
"""
Spinners are from:
* cli-spinners:
    MIT License
    Copyright (c) Sindre Sorhus <sindresorhus@gmail.com> (sindresorhus.com)
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights to
    use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
    the Software, and to permit persons to whom the Software is furnished to do so,
    subject to the following conditions:
    The above copyright notice and this permission notice shall be included
    in all copies or substantial portions of the Software.
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
    INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
    PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
    FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
    IN THE SOFTWARE.
"""

SPINNERS = {
    "dots": {
        "interval": 80,
        "frames": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
    },
    "dots2": {"interval": 80, "frames": "⣾⣽⣻⢿⡿⣟⣯⣷"},
    "dots3": {
        "interval": 80,
        "frames": "⠋⠙⠚⠞⠖⠦⠴⠲⠳⠓",
    },
    "dots4": {
        "interval": 80,
        "frames": "⠄⠆⠇⠋⠙⠸⠰⠠⠰⠸⠙⠋⠇⠆",
    },
    "dots5": {
        "interval": 80,
        "frames": "⠋⠙⠚⠒⠂⠂⠒⠲⠴⠦⠖⠒⠐⠐⠒⠓⠋",
    },
    "dots6": {
        "interval": 80,
        "frames": "⠁⠉⠙⠚⠒⠂⠂⠒⠲⠴⠤⠄⠄⠤⠴⠲⠒⠂⠂⠒⠚⠙⠉⠁",
    },
    "dots7": {
        "interval": 80,
        "frames": "⠈⠉⠋⠓⠒⠐⠐⠒⠖⠦⠤⠠⠠⠤⠦⠖⠒⠐⠐⠒⠓⠋⠉⠈",
    },
    "dots8": {
        "interval": 80,
        "frames": "⠁⠁⠉⠙⠚⠒⠂⠂⠒⠲⠴⠤⠄⠄⠤⠠⠠⠤⠦⠖⠒⠐⠐⠒⠓⠋⠉⠈⠈",
    },
    "dots9": {"interval": 80, "frames": "⢹⢺⢼⣸⣇⡧⡗⡏"},
    "dots10": {"interval": 80, "frames": "⢄⢂⢁⡁⡈⡐⡠"},
    "dots11": {"interval": 100, "frames": "⠁⠂⠄⡀⢀⠠⠐⠈"},
    "dots12": {
        "interval": 80,
        "frames": [
            "⢀⠀",
            "⡀⠀",
            "⠄⠀",
            "⢂⠀",
            "⡂⠀",
            "⠅⠀",
            "⢃⠀",
            "⡃⠀",
            "⠍⠀",
            "⢋⠀",
            "⡋⠀",
            "⠍⠁",
            "⢋⠁",
            "⡋⠁",
            "⠍⠉",
            "⠋⠉",
            "⠋⠉",
            "⠉⠙",
            "⠉⠙",
            "⠉⠩",
            "⠈⢙",
            "⠈⡙",
            "⢈⠩",
            "⡀⢙",
            "⠄⡙",
            "⢂⠩",
            "⡂⢘",
            "⠅⡘",
            "⢃⠨",
            "⡃⢐",
            "⠍⡐",
            "⢋⠠",
            "⡋⢀",
            "⠍⡁",
            "⢋⠁",
            "⡋⠁",
            "⠍⠉",
            "⠋⠉",
            "⠋⠉",
            "⠉⠙",
            "⠉⠙",
            "⠉⠩",
            "⠈⢙",
            "⠈⡙",
            "⠈⠩",
            "⠀⢙",
            "⠀⡙",
            "⠀⠩",
            "⠀⢘",
            "⠀⡘",
            "⠀⠨",
            "⠀⢐",
            "⠀⡐",
            "⠀⠠",
            "⠀⢀",
            "⠀⡀",
        ],
    },
    "dots8Bit": {
        "interval": 80,
        "frames": "⠀⠁⠂⠃⠄⠅⠆⠇⡀⡁⡂⡃⡄⡅⡆⡇⠈⠉⠊⠋⠌⠍⠎⠏⡈⡉⡊⡋⡌⡍⡎⡏⠐⠑⠒⠓⠔⠕⠖⠗⡐⡑⡒⡓⡔⡕⡖⡗⠘⠙⠚⠛⠜⠝⠞⠟⡘⡙"
        "⡚⡛⡜⡝⡞⡟⠠⠡⠢⠣⠤⠥⠦⠧⡠⡡⡢⡣⡤⡥⡦⡧⠨⠩⠪⠫⠬⠭⠮⠯⡨⡩⡪⡫⡬⡭⡮⡯⠰⠱⠲⠳⠴⠵⠶⠷⡰⡱⡲⡳⡴⡵⡶⡷⠸⠹⠺⠻"
        "⠼⠽⠾⠿⡸⡹⡺⡻⡼⡽⡾⡿⢀⢁⢂⢃⢄⢅⢆⢇⣀⣁⣂⣃⣄⣅⣆⣇⢈⢉⢊⢋⢌⢍⢎⢏⣈⣉⣊⣋⣌⣍⣎⣏⢐⢑⢒⢓⢔⢕⢖⢗⣐⣑⣒⣓⣔⣕"
        "⣖⣗⢘⢙⢚⢛⢜⢝⢞⢟⣘⣙⣚⣛⣜⣝⣞⣟⢠⢡⢢⢣⢤⢥⢦⢧⣠⣡⣢⣣⣤⣥⣦⣧⢨⢩⢪⢫⢬⢭⢮⢯⣨⣩⣪⣫⣬⣭⣮⣯⢰⢱⢲⢳⢴⢵⢶⢷"
        "⣰⣱⣲⣳⣴⣵⣶⣷⢸⢹⢺⢻⢼⢽⢾⢿⣸⣹⣺⣻⣼⣽⣾⣿",
    },
    "line": {"interval": 130, "frames": ["-", "\\", "|", "/"]},
    "line2": {"interval": 100, "frames": "⠂-–—–-"},
    "pipe": {"interval": 100, "frames": "┤┘┴└├┌┬┐"},
    "simpleDots": {"interval": 400, "frames": [".  ", ".. ", "...", "   "]},
    "simpleDotsScrolling": {
        "interval": 200,
        "frames": [".  ", ".. ", "...", " ..", "  .", "   "],
    },
    "star": {"interval": 70, "frames": "✶✸✹✺✹✷"},
    "star2": {"interval": 80, "frames": "+x*"},
    "flip": {
        "interval": 70,
        "frames": "___-``'´-___",
    },
    "hamburger": {"interval": 100, "frames": "☱☲☴"},
    "growVertical": {
        "interval": 120,
        "frames": "▁▃▄▅▆▇▆▅▄▃",
    },
    "growHorizontal": {
        "interval": 120,
        "frames": "▏▎▍▌▋▊▉▊▋▌▍▎",
    },
    "balloon": {"interval": 140, "frames": " .oO@* "},
    "balloon2": {"interval": 120, "frames": ".oO°Oo."},
    "noise": {"interval": 100, "frames": "▓▒░"},
    "bounce": {"interval": 120, "frames": "⠁⠂⠄⠂"},
    "boxBounce": {"interval": 120, "frames": "▖▘▝▗"},
    "boxBounce2": {"interval": 100, "frames": "▌▀▐▄"},
    "triangle": {"interval": 50, "frames": "◢◣◤◥"},
    "arc": {"interval": 100, "frames": "◜◠◝◞◡◟"},
    "circle": {"interval": 120, "frames": "◡⊙◠"},
    "squareCorners": {"interval": 180, "frames": "◰◳◲◱"},
    "circleQuarters": {"interval": 120, "frames": "◴◷◶◵"},
    "circleHalves": {"interval": 50, "frames": "◐◓◑◒"},
    "squish": {"interval": 100, "frames": "╫╪"},
    "toggle": {"interval": 250, "frames": "⊶⊷"},
    "toggle2": {"interval": 80, "frames": "▫▪"},
    "toggle3": {"interval": 120, "frames": "□■"},
    "toggle4": {"interval": 100, "frames": "■□▪▫"},
    "toggle5": {"interval": 100, "frames": "▮▯"},
    "toggle6": {"interval": 300, "frames": "ဝ၀"},
    "toggle7": {"interval": 80, "frames": "⦾⦿"},
    "toggle8": {"interval": 100, "frames": "◍◌"},
    "toggle9": {"interval": 100, "frames": "◉◎"},
    "toggle10": {"interval": 100, "frames": "㊂㊀㊁"},
    "toggle11": {"interval": 50, "frames": "⧇⧆"},
    "toggle12": {"interval": 120, "frames": "☗☖"},
    "toggle13": {"interval": 80, "frames": "=*-"},
    "arrow": {"interval": 100, "frames": "←↖↑↗→↘↓↙"},
    "arrow2": {
        "interval": 80,
        "frames": ["⬆️ ", "↗️ ", "➡️ ", "↘️ ", "⬇️ ", "↙️ ", "⬅️ ", "↖️ "],
    },
    "arrow3": {
        "interval": 120,
        "frames": ["▹▹▹▹▹", "▸▹▹▹▹", "▹▸▹▹▹", "▹▹▸▹▹", "▹▹▹▸▹", "▹▹▹▹▸"],
    },
    "bouncingBar": {
        "interval": 80,
        "frames": [
            "[    ]",
            "[=   ]",
            "[==  ]",
            "[=== ]",
            "[ ===]",
            "[  ==]",
            "[   =]",
            "[    ]",
            "[   =]",
            "[  ==]",
            "[ ===]",
            "[====]",
            "[=== ]",
            "[==  ]",
            "[=   ]",
        ],
    },
    "bouncingBall": {
        "interval": 80,
        "frames": [
            "( ●    )",
            "(  ●   )",
            "(   ●  )",
            "(    ● )",
            "(     ●)",
            "(    ● )",
            "(   ●  )",
            "(  ●   )",
            "( ●    )",
            "(●     )",
        ],
    },
    "smiley": {"interval": 200, "frames": ["😄 ", "😝 "]},
    "monkey": {"interval": 300, "frames": ["🙈 ", "🙈 ", "🙉 ", "🙊 "]},
    "hearts": {"interval": 100, "frames": ["💛 ", "💙 ", "💜 ", "💚 ", "❤️ "]},
    "clock": {
        "interval": 100,
        "frames": [
            "🕛 ",
            "🕐 ",
            "🕑 ",
            "🕒 ",
            "🕓 ",
            "🕔 ",
            "🕕 ",
            "🕖 ",
            "🕗 ",
            "🕘 ",
            "🕙 ",
            "🕚 ",
        ],
    },
    "earth": {"interval": 180, "frames": ["🌍 ", "🌎 ", "🌏 "]},
    "material": {
        "interval": 17,
        "frames": [
            "█▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "██▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "███▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "████▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "██████▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "██████▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "███████▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "████████▁▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "██████████▁▁▁▁▁▁▁▁▁▁",
            "███████████▁▁▁▁▁▁▁▁▁",
            "█████████████▁▁▁▁▁▁▁",
            "██████████████▁▁▁▁▁▁",
            "██████████████▁▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁▁██████████████▁▁▁▁",
            "▁▁▁██████████████▁▁▁",
            "▁▁▁▁█████████████▁▁▁",
            "▁▁▁▁██████████████▁▁",
            "▁▁▁▁██████████████▁▁",
            "▁▁▁▁▁██████████████▁",
            "▁▁▁▁▁██████████████▁",
            "▁▁▁▁▁██████████████▁",
            "▁▁▁▁▁▁██████████████",
            "▁▁▁▁▁▁██████████████",
            "▁▁▁▁▁▁▁█████████████",
            "▁▁▁▁▁▁▁█████████████",
            "▁▁▁▁▁▁▁▁████████████",
            "▁▁▁▁▁▁▁▁████████████",
            "▁▁▁▁▁▁▁▁▁███████████",
            "▁▁▁▁▁▁▁▁▁███████████",
            "▁▁▁▁▁▁▁▁▁▁██████████",
            "▁▁▁▁▁▁▁▁▁▁██████████",
            "▁▁▁▁▁▁▁▁▁▁▁▁████████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁███████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁██████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█████",
            "█▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁████",
            "██▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "██▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "███▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "████▁▁▁▁▁▁▁▁▁▁▁▁▁▁██",
            "█████▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "█████▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "██████▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "████████▁▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "███████████▁▁▁▁▁▁▁▁▁",
            "████████████▁▁▁▁▁▁▁▁",
            "████████████▁▁▁▁▁▁▁▁",
            "██████████████▁▁▁▁▁▁",
            "██████████████▁▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁▁▁█████████████▁▁▁▁",
            "▁▁▁▁▁████████████▁▁▁",
            "▁▁▁▁▁████████████▁▁▁",
            "▁▁▁▁▁▁███████████▁▁▁",
            "▁▁▁▁▁▁▁▁█████████▁▁▁",
            "▁▁▁▁▁▁▁▁█████████▁▁▁",
            "▁▁▁▁▁▁▁▁▁█████████▁▁",
            "▁▁▁▁▁▁▁▁▁█████████▁▁",
            "▁▁▁▁▁▁▁▁▁▁█████████▁",
            "▁▁▁▁▁▁▁▁▁▁▁████████▁",
            "▁▁▁▁▁▁▁▁▁▁▁████████▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁███████▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁███████▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁███████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁███████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁██",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁██",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁██",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
        ],
    },
    "moon": {
        "interval": 80,
        "frames": ["🌑 ", "🌒 ", "🌓 ", "🌔 ", "🌕 ", "🌖 ", "🌗 ", "🌘 "],
    },
    "runner": {"interval": 140, "frames": ["🚶 ", "🏃 "]},
    "pong": {
        "interval": 80,
        "frames": [
            "▐⠂       ▌",
            "▐⠈       ▌",
            "▐ ⠂      ▌",
            "▐ ⠠      ▌",
            "▐  ⡀     ▌",
            "▐  ⠠     ▌",
            "▐   ⠂    ▌",
            "▐   ⠈    ▌",
            "▐    ⠂   ▌",
            "▐    ⠠   ▌",
            "▐     ⡀  ▌",
            "▐     ⠠  ▌",
            "▐      ⠂ ▌",
            "▐      ⠈ ▌",
            "▐       ⠂▌",
            "▐       ⠠▌",
            "▐       ⡀▌",
            "▐      ⠠ ▌",
            "▐      ⠂ ▌",
            "▐     ⠈  ▌",
            "▐     ⠂  ▌",
            "▐    ⠠   ▌",
            "▐    ⡀   ▌",
            "▐   ⠠    ▌",
            "▐   ⠂    ▌",
            "▐  ⠈     ▌",
            "▐  ⠂     ▌",
            "▐ ⠠      ▌",
            "▐ ⡀      ▌",
            "▐⠠       ▌",
        ],
    },
    "shark": {
        "interval": 120,
        "frames": [
            "▐|\\____________▌",
            "▐_|\\___________▌",
            "▐__|\\__________▌",
            "▐___|\\_________▌",
            "▐____|\\________▌",
            "▐_____|\\_______▌",
            "▐______|\\______▌",
            "▐_______|\\_____▌",
            "▐________|\\____▌",
            "▐_________|\\___▌",
            "▐__________|\\__▌",
            "▐___________|\\_▌",
            "▐____________|\\▌",
            "▐____________/|▌",
            "▐___________/|_▌",
            "▐__________/|__▌",
            "▐_________/|___▌",
            "▐________/|____▌",
            "▐_______/|_____▌",
            "▐______/|______▌",
            "▐_____/|_______▌",
            "▐____/|________▌",
            "▐___/|_________▌",
            "▐__/|__________▌",
            "▐_/|___________▌",
            "▐/|____________▌",
        ],
    },
    "dqpb": {"interval": 100, "frames": "dqpb"},
    "weather": {
        "interval": 100,
        "frames": [
            "☀️ ",
            "☀️ ",
            "☀️ ",
            "🌤 ",
            "⛅️ ",
            "🌥 ",
            "☁️ ",
            "🌧 ",
            "🌨 ",
            "🌧 ",
            "🌨 ",
            "🌧 ",
            "🌨 ",
            "⛈ ",
            "🌨 ",
            "🌧 ",
            "🌨 ",
            "☁️ ",
            "🌥 ",
            "⛅️ ",
            "🌤 ",
            "☀️ ",
            "☀️ ",
        ],
    },
    "christmas": {"interval": 400, "frames": "🌲🎄"},
    "grenade": {
        "interval": 80,
        "frames": [
            "،   ",
            "′   ",
            " ´ ",
            " ‾ ",
            "  ⸌",
            "  ⸊",
            "  |",
            "  ⁎",
            "  ⁕",
            " ෴ ",
            "  ⁓",
            "   ",
            "   ",
            "   ",
        ],
    },
    "point": {"interval": 125, "frames": ["∙∙∙", "●∙∙", "∙●∙", "∙∙●", "∙∙∙"]},
    "layer": {"interval": 150, "frames": "-=≡"},
    "betaWave": {
        "interval": 80,
        "frames": [
            "ρββββββ",
            "βρβββββ",
            "ββρββββ",
            "βββρβββ",
            "ββββρββ",
            "βββββρβ",
            "ββββββρ",
        ],
    },
    "aesthetic": {
        "interval": 80,
        "frames": [
            "▰▱▱▱▱▱▱",
            "▰▰▱▱▱▱▱",
            "▰▰▰▱▱▱▱",
            "▰▰▰▰▱▱▱",
            "▰▰▰▰▰▱▱",
            "▰▰▰▰▰▰▱",
            "▰▰▰▰▰▰▰",
            "▰▱▱▱▱▱▱",
        ],
    },
}

# === NexusCore/openenv\Lib\site-packages\rich\_spinners.py ===
"""
Spinners are from:
* cli-spinners:
    MIT License
    Copyright (c) Sindre Sorhus <sindresorhus@gmail.com> (sindresorhus.com)
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights to
    use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
    the Software, and to permit persons to whom the Software is furnished to do so,
    subject to the following conditions:
    The above copyright notice and this permission notice shall be included
    in all copies or substantial portions of the Software.
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
    INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
    PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
    FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
    IN THE SOFTWARE.
"""

SPINNERS = {
    "dots": {
        "interval": 80,
        "frames": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
    },
    "dots2": {"interval": 80, "frames": "⣾⣽⣻⢿⡿⣟⣯⣷"},
    "dots3": {
        "interval": 80,
        "frames": "⠋⠙⠚⠞⠖⠦⠴⠲⠳⠓",
    },
    "dots4": {
        "interval": 80,
        "frames": "⠄⠆⠇⠋⠙⠸⠰⠠⠰⠸⠙⠋⠇⠆",
    },
    "dots5": {
        "interval": 80,
        "frames": "⠋⠙⠚⠒⠂⠂⠒⠲⠴⠦⠖⠒⠐⠐⠒⠓⠋",
    },
    "dots6": {
        "interval": 80,
        "frames": "⠁⠉⠙⠚⠒⠂⠂⠒⠲⠴⠤⠄⠄⠤⠴⠲⠒⠂⠂⠒⠚⠙⠉⠁",
    },
    "dots7": {
        "interval": 80,
        "frames": "⠈⠉⠋⠓⠒⠐⠐⠒⠖⠦⠤⠠⠠⠤⠦⠖⠒⠐⠐⠒⠓⠋⠉⠈",
    },
    "dots8": {
        "interval": 80,
        "frames": "⠁⠁⠉⠙⠚⠒⠂⠂⠒⠲⠴⠤⠄⠄⠤⠠⠠⠤⠦⠖⠒⠐⠐⠒⠓⠋⠉⠈⠈",
    },
    "dots9": {"interval": 80, "frames": "⢹⢺⢼⣸⣇⡧⡗⡏"},
    "dots10": {"interval": 80, "frames": "⢄⢂⢁⡁⡈⡐⡠"},
    "dots11": {"interval": 100, "frames": "⠁⠂⠄⡀⢀⠠⠐⠈"},
    "dots12": {
        "interval": 80,
        "frames": [
            "⢀⠀",
            "⡀⠀",
            "⠄⠀",
            "⢂⠀",
            "⡂⠀",
            "⠅⠀",
            "⢃⠀",
            "⡃⠀",
            "⠍⠀",
            "⢋⠀",
            "⡋⠀",
            "⠍⠁",
            "⢋⠁",
            "⡋⠁",
            "⠍⠉",
            "⠋⠉",
            "⠋⠉",
            "⠉⠙",
            "⠉⠙",
            "⠉⠩",
            "⠈⢙",
            "⠈⡙",
            "⢈⠩",
            "⡀⢙",
            "⠄⡙",
            "⢂⠩",
            "⡂⢘",
            "⠅⡘",
            "⢃⠨",
            "⡃⢐",
            "⠍⡐",
            "⢋⠠",
            "⡋⢀",
            "⠍⡁",
            "⢋⠁",
            "⡋⠁",
            "⠍⠉",
            "⠋⠉",
            "⠋⠉",
            "⠉⠙",
            "⠉⠙",
            "⠉⠩",
            "⠈⢙",
            "⠈⡙",
            "⠈⠩",
            "⠀⢙",
            "⠀⡙",
            "⠀⠩",
            "⠀⢘",
            "⠀⡘",
            "⠀⠨",
            "⠀⢐",
            "⠀⡐",
            "⠀⠠",
            "⠀⢀",
            "⠀⡀",
        ],
    },
    "dots8Bit": {
        "interval": 80,
        "frames": "⠀⠁⠂⠃⠄⠅⠆⠇⡀⡁⡂⡃⡄⡅⡆⡇⠈⠉⠊⠋⠌⠍⠎⠏⡈⡉⡊⡋⡌⡍⡎⡏⠐⠑⠒⠓⠔⠕⠖⠗⡐⡑⡒⡓⡔⡕⡖⡗⠘⠙⠚⠛⠜⠝⠞⠟⡘⡙"
        "⡚⡛⡜⡝⡞⡟⠠⠡⠢⠣⠤⠥⠦⠧⡠⡡⡢⡣⡤⡥⡦⡧⠨⠩⠪⠫⠬⠭⠮⠯⡨⡩⡪⡫⡬⡭⡮⡯⠰⠱⠲⠳⠴⠵⠶⠷⡰⡱⡲⡳⡴⡵⡶⡷⠸⠹⠺⠻"
        "⠼⠽⠾⠿⡸⡹⡺⡻⡼⡽⡾⡿⢀⢁⢂⢃⢄⢅⢆⢇⣀⣁⣂⣃⣄⣅⣆⣇⢈⢉⢊⢋⢌⢍⢎⢏⣈⣉⣊⣋⣌⣍⣎⣏⢐⢑⢒⢓⢔⢕⢖⢗⣐⣑⣒⣓⣔⣕"
        "⣖⣗⢘⢙⢚⢛⢜⢝⢞⢟⣘⣙⣚⣛⣜⣝⣞⣟⢠⢡⢢⢣⢤⢥⢦⢧⣠⣡⣢⣣⣤⣥⣦⣧⢨⢩⢪⢫⢬⢭⢮⢯⣨⣩⣪⣫⣬⣭⣮⣯⢰⢱⢲⢳⢴⢵⢶⢷"
        "⣰⣱⣲⣳⣴⣵⣶⣷⢸⢹⢺⢻⢼⢽⢾⢿⣸⣹⣺⣻⣼⣽⣾⣿",
    },
    "line": {"interval": 130, "frames": ["-", "\\", "|", "/"]},
    "line2": {"interval": 100, "frames": "⠂-–—–-"},
    "pipe": {"interval": 100, "frames": "┤┘┴└├┌┬┐"},
    "simpleDots": {"interval": 400, "frames": [".  ", ".. ", "...", "   "]},
    "simpleDotsScrolling": {
        "interval": 200,
        "frames": [".  ", ".. ", "...", " ..", "  .", "   "],
    },
    "star": {"interval": 70, "frames": "✶✸✹✺✹✷"},
    "star2": {"interval": 80, "frames": "+x*"},
    "flip": {
        "interval": 70,
        "frames": "___-``'´-___",
    },
    "hamburger": {"interval": 100, "frames": "☱☲☴"},
    "growVertical": {
        "interval": 120,
        "frames": "▁▃▄▅▆▇▆▅▄▃",
    },
    "growHorizontal": {
        "interval": 120,
        "frames": "▏▎▍▌▋▊▉▊▋▌▍▎",
    },
    "balloon": {"interval": 140, "frames": " .oO@* "},
    "balloon2": {"interval": 120, "frames": ".oO°Oo."},
    "noise": {"interval": 100, "frames": "▓▒░"},
    "bounce": {"interval": 120, "frames": "⠁⠂⠄⠂"},
    "boxBounce": {"interval": 120, "frames": "▖▘▝▗"},
    "boxBounce2": {"interval": 100, "frames": "▌▀▐▄"},
    "triangle": {"interval": 50, "frames": "◢◣◤◥"},
    "arc": {"interval": 100, "frames": "◜◠◝◞◡◟"},
    "circle": {"interval": 120, "frames": "◡⊙◠"},
    "squareCorners": {"interval": 180, "frames": "◰◳◲◱"},
    "circleQuarters": {"interval": 120, "frames": "◴◷◶◵"},
    "circleHalves": {"interval": 50, "frames": "◐◓◑◒"},
    "squish": {"interval": 100, "frames": "╫╪"},
    "toggle": {"interval": 250, "frames": "⊶⊷"},
    "toggle2": {"interval": 80, "frames": "▫▪"},
    "toggle3": {"interval": 120, "frames": "□■"},
    "toggle4": {"interval": 100, "frames": "■□▪▫"},
    "toggle5": {"interval": 100, "frames": "▮▯"},
    "toggle6": {"interval": 300, "frames": "ဝ၀"},
    "toggle7": {"interval": 80, "frames": "⦾⦿"},
    "toggle8": {"interval": 100, "frames": "◍◌"},
    "toggle9": {"interval": 100, "frames": "◉◎"},
    "toggle10": {"interval": 100, "frames": "㊂㊀㊁"},
    "toggle11": {"interval": 50, "frames": "⧇⧆"},
    "toggle12": {"interval": 120, "frames": "☗☖"},
    "toggle13": {"interval": 80, "frames": "=*-"},
    "arrow": {"interval": 100, "frames": "←↖↑↗→↘↓↙"},
    "arrow2": {
        "interval": 80,
        "frames": ["⬆️ ", "↗️ ", "➡️ ", "↘️ ", "⬇️ ", "↙️ ", "⬅️ ", "↖️ "],
    },
    "arrow3": {
        "interval": 120,
        "frames": ["▹▹▹▹▹", "▸▹▹▹▹", "▹▸▹▹▹", "▹▹▸▹▹", "▹▹▹▸▹", "▹▹▹▹▸"],
    },
    "bouncingBar": {
        "interval": 80,
        "frames": [
            "[    ]",
            "[=   ]",
            "[==  ]",
            "[=== ]",
            "[ ===]",
            "[  ==]",
            "[   =]",
            "[    ]",
            "[   =]",
            "[  ==]",
            "[ ===]",
            "[====]",
            "[=== ]",
            "[==  ]",
            "[=   ]",
        ],
    },
    "bouncingBall": {
        "interval": 80,
        "frames": [
            "( ●    )",
            "(  ●   )",
            "(   ●  )",
            "(    ● )",
            "(     ●)",
            "(    ● )",
            "(   ●  )",
            "(  ●   )",
            "( ●    )",
            "(●     )",
        ],
    },
    "smiley": {"interval": 200, "frames": ["😄 ", "😝 "]},
    "monkey": {"interval": 300, "frames": ["🙈 ", "🙈 ", "🙉 ", "🙊 "]},
    "hearts": {"interval": 100, "frames": ["💛 ", "💙 ", "💜 ", "💚 ", "❤️ "]},
    "clock": {
        "interval": 100,
        "frames": [
            "🕛 ",
            "🕐 ",
            "🕑 ",
            "🕒 ",
            "🕓 ",
            "🕔 ",
            "🕕 ",
            "🕖 ",
            "🕗 ",
            "🕘 ",
            "🕙 ",
            "🕚 ",
        ],
    },
    "earth": {"interval": 180, "frames": ["🌍 ", "🌎 ", "🌏 "]},
    "material": {
        "interval": 17,
        "frames": [
            "█▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "██▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "███▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "████▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "██████▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "██████▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "███████▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "████████▁▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "██████████▁▁▁▁▁▁▁▁▁▁",
            "███████████▁▁▁▁▁▁▁▁▁",
            "█████████████▁▁▁▁▁▁▁",
            "██████████████▁▁▁▁▁▁",
            "██████████████▁▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁▁██████████████▁▁▁▁",
            "▁▁▁██████████████▁▁▁",
            "▁▁▁▁█████████████▁▁▁",
            "▁▁▁▁██████████████▁▁",
            "▁▁▁▁██████████████▁▁",
            "▁▁▁▁▁██████████████▁",
            "▁▁▁▁▁██████████████▁",
            "▁▁▁▁▁██████████████▁",
            "▁▁▁▁▁▁██████████████",
            "▁▁▁▁▁▁██████████████",
            "▁▁▁▁▁▁▁█████████████",
            "▁▁▁▁▁▁▁█████████████",
            "▁▁▁▁▁▁▁▁████████████",
            "▁▁▁▁▁▁▁▁████████████",
            "▁▁▁▁▁▁▁▁▁███████████",
            "▁▁▁▁▁▁▁▁▁███████████",
            "▁▁▁▁▁▁▁▁▁▁██████████",
            "▁▁▁▁▁▁▁▁▁▁██████████",
            "▁▁▁▁▁▁▁▁▁▁▁▁████████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁███████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁██████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█████",
            "█▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁████",
            "██▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "██▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "███▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "████▁▁▁▁▁▁▁▁▁▁▁▁▁▁██",
            "█████▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "█████▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "██████▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "████████▁▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "███████████▁▁▁▁▁▁▁▁▁",
            "████████████▁▁▁▁▁▁▁▁",
            "████████████▁▁▁▁▁▁▁▁",
            "██████████████▁▁▁▁▁▁",
            "██████████████▁▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁▁▁█████████████▁▁▁▁",
            "▁▁▁▁▁████████████▁▁▁",
            "▁▁▁▁▁████████████▁▁▁",
            "▁▁▁▁▁▁███████████▁▁▁",
            "▁▁▁▁▁▁▁▁█████████▁▁▁",
            "▁▁▁▁▁▁▁▁█████████▁▁▁",
            "▁▁▁▁▁▁▁▁▁█████████▁▁",
            "▁▁▁▁▁▁▁▁▁█████████▁▁",
            "▁▁▁▁▁▁▁▁▁▁█████████▁",
            "▁▁▁▁▁▁▁▁▁▁▁████████▁",
            "▁▁▁▁▁▁▁▁▁▁▁████████▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁███████▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁███████▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁███████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁███████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁██",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁██",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁██",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
        ],
    },
    "moon": {
        "interval": 80,
        "frames": ["🌑 ", "🌒 ", "🌓 ", "🌔 ", "🌕 ", "🌖 ", "🌗 ", "🌘 "],
    },
    "runner": {"interval": 140, "frames": ["🚶 ", "🏃 "]},
    "pong": {
        "interval": 80,
        "frames": [
            "▐⠂       ▌",
            "▐⠈       ▌",
            "▐ ⠂      ▌",
            "▐ ⠠      ▌",
            "▐  ⡀     ▌",
            "▐  ⠠     ▌",
            "▐   ⠂    ▌",
            "▐   ⠈    ▌",
            "▐    ⠂   ▌",
            "▐    ⠠   ▌",
            "▐     ⡀  ▌",
            "▐     ⠠  ▌",
            "▐      ⠂ ▌",
            "▐      ⠈ ▌",
            "▐       ⠂▌",
            "▐       ⠠▌",
            "▐       ⡀▌",
            "▐      ⠠ ▌",
            "▐      ⠂ ▌",
            "▐     ⠈  ▌",
            "▐     ⠂  ▌",
            "▐    ⠠   ▌",
            "▐    ⡀   ▌",
            "▐   ⠠    ▌",
            "▐   ⠂    ▌",
            "▐  ⠈     ▌",
            "▐  ⠂     ▌",
            "▐ ⠠      ▌",
            "▐ ⡀      ▌",
            "▐⠠       ▌",
        ],
    },
    "shark": {
        "interval": 120,
        "frames": [
            "▐|\\____________▌",
            "▐_|\\___________▌",
            "▐__|\\__________▌",
            "▐___|\\_________▌",
            "▐____|\\________▌",
            "▐_____|\\_______▌",
            "▐______|\\______▌",
            "▐_______|\\_____▌",
            "▐________|\\____▌",
            "▐_________|\\___▌",
            "▐__________|\\__▌",
            "▐___________|\\_▌",
            "▐____________|\\▌",
            "▐____________/|▌",
            "▐___________/|_▌",
            "▐__________/|__▌",
            "▐_________/|___▌",
            "▐________/|____▌",
            "▐_______/|_____▌",
            "▐______/|______▌",
            "▐_____/|_______▌",
            "▐____/|________▌",
            "▐___/|_________▌",
            "▐__/|__________▌",
            "▐_/|___________▌",
            "▐/|____________▌",
        ],
    },
    "dqpb": {"interval": 100, "frames": "dqpb"},
    "weather": {
        "interval": 100,
        "frames": [
            "☀️ ",
            "☀️ ",
            "☀️ ",
            "🌤 ",
            "⛅️ ",
            "🌥 ",
            "☁️ ",
            "🌧 ",
            "🌨 ",
            "🌧 ",
            "🌨 ",
            "🌧 ",
            "🌨 ",
            "⛈ ",
            "🌨 ",
            "🌧 ",
            "🌨 ",
            "☁️ ",
            "🌥 ",
            "⛅️ ",
            "🌤 ",
            "☀️ ",
            "☀️ ",
        ],
    },
    "christmas": {"interval": 400, "frames": "🌲🎄"},
    "grenade": {
        "interval": 80,
        "frames": [
            "،   ",
            "′   ",
            " ´ ",
            " ‾ ",
            "  ⸌",
            "  ⸊",
            "  |",
            "  ⁎",
            "  ⁕",
            " ෴ ",
            "  ⁓",
            "   ",
            "   ",
            "   ",
        ],
    },
    "point": {"interval": 125, "frames": ["∙∙∙", "●∙∙", "∙●∙", "∙∙●", "∙∙∙"]},
    "layer": {"interval": 150, "frames": "-=≡"},
    "betaWave": {
        "interval": 80,
        "frames": [
            "ρββββββ",
            "βρβββββ",
            "ββρββββ",
            "βββρβββ",
            "ββββρββ",
            "βββββρβ",
            "ββββββρ",
        ],
    },
    "aesthetic": {
        "interval": 80,
        "frames": [
            "▰▱▱▱▱▱▱",
            "▰▰▱▱▱▱▱",
            "▰▰▰▱▱▱▱",
            "▰▰▰▰▱▱▱",
            "▰▰▰▰▰▱▱",
            "▰▰▰▰▰▰▱",
            "▰▰▰▰▰▰▰",
            "▰▱▱▱▱▱▱",
        ],
    },
}

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_concurrency_analyser\pydevd_concurrency_logger.py ===
import time

from _pydev_bundle._pydev_filesystem_encoding import getfilesystemencoding
from _pydev_bundle._pydev_saved_modules import threading
from _pydevd_bundle import pydevd_xml
from _pydevd_bundle.pydevd_constants import GlobalDebuggerHolder
from _pydevd_bundle.pydevd_constants import get_thread_id
from _pydevd_bundle.pydevd_net_command import NetCommand
from _pydevd_bundle.pydevd_concurrency_analyser.pydevd_thread_wrappers import ObjectWrapper, wrap_attr
import pydevd_file_utils
from _pydev_bundle import pydev_log
import sys

file_system_encoding = getfilesystemencoding()

from urllib.parse import quote

threadingCurrentThread = threading.current_thread

DONT_TRACE_THREADING = ["threading.py", "pydevd.py"]
INNER_METHODS = ["_stop"]
INNER_FILES = ["threading.py"]
THREAD_METHODS = ["start", "_stop", "join"]
LOCK_METHODS = ["__init__", "acquire", "release", "__enter__", "__exit__"]
QUEUE_METHODS = ["put", "get"]

# return time since epoch in milliseconds
cur_time = lambda: int(round(time.time() * 1000000))


def get_text_list_for_frame(frame):
    # partial copy-paste from make_thread_suspend_str
    curFrame = frame
    cmdTextList = []
    try:
        while curFrame:
            # print cmdText
            myId = str(id(curFrame))
            # print "id is ", myId

            if curFrame.f_code is None:
                break  # Iron Python sometimes does not have it!

            myName = curFrame.f_code.co_name  # method name (if in method) or ? if global
            if myName is None:
                break  # Iron Python sometimes does not have it!

            # print "name is ", myName

            absolute_filename = pydevd_file_utils.get_abs_path_real_path_and_base_from_frame(curFrame)[0]

            my_file, _applied_mapping = pydevd_file_utils.map_file_to_client(absolute_filename)

            # print "file is ", my_file
            # my_file = inspect.getsourcefile(curFrame) or inspect.getfile(frame)

            myLine = str(curFrame.f_lineno)
            # print "line is ", myLine

            # the variables are all gotten 'on-demand'
            # variables = pydevd_xml.frame_vars_to_xml(curFrame.f_locals)

            variables = ""
            cmdTextList.append('<frame id="%s" name="%s" ' % (myId, pydevd_xml.make_valid_xml_value(myName)))
            cmdTextList.append('file="%s" line="%s">' % (quote(my_file, "/>_= \t"), myLine))
            cmdTextList.append(variables)
            cmdTextList.append("</frame>")
            curFrame = curFrame.f_back
    except:
        pydev_log.exception()

    return cmdTextList


def send_concurrency_message(event_class, time, name, thread_id, type, event, file, line, frame, lock_id=0, parent=None):
    dbg = GlobalDebuggerHolder.global_dbg
    if dbg is None:
        return
    cmdTextList = ["<xml>"]

    cmdTextList.append("<" + event_class)
    cmdTextList.append(' time="%s"' % pydevd_xml.make_valid_xml_value(str(time)))
    cmdTextList.append(' name="%s"' % pydevd_xml.make_valid_xml_value(name))
    cmdTextList.append(' thread_id="%s"' % pydevd_xml.make_valid_xml_value(thread_id))
    cmdTextList.append(' type="%s"' % pydevd_xml.make_valid_xml_value(type))
    if type == "lock":
        cmdTextList.append(' lock_id="%s"' % pydevd_xml.make_valid_xml_value(str(lock_id)))
    if parent is not None:
        cmdTextList.append(' parent="%s"' % pydevd_xml.make_valid_xml_value(parent))
    cmdTextList.append(' event="%s"' % pydevd_xml.make_valid_xml_value(event))
    cmdTextList.append(' file="%s"' % pydevd_xml.make_valid_xml_value(file))
    cmdTextList.append(' line="%s"' % pydevd_xml.make_valid_xml_value(str(line)))
    cmdTextList.append("></" + event_class + ">")

    cmdTextList += get_text_list_for_frame(frame)
    cmdTextList.append("</xml>")

    text = "".join(cmdTextList)
    if dbg.writer is not None:
        dbg.writer.add_command(NetCommand(145, 0, text))


def log_new_thread(global_debugger, t):
    event_time = cur_time() - global_debugger.thread_analyser.start_time
    send_concurrency_message(
        "threading_event", event_time, t.name, get_thread_id(t), "thread", "start", "code_name", 0, None, parent=get_thread_id(t)
    )


class ThreadingLogger:
    def __init__(self):
        self.start_time = cur_time()

    def set_start_time(self, time):
        self.start_time = time

    def log_event(self, frame):
        write_log = False
        self_obj = None
        if "self" in frame.f_locals:
            self_obj = frame.f_locals["self"]
            if isinstance(self_obj, threading.Thread) or self_obj.__class__ == ObjectWrapper:
                write_log = True
        if hasattr(frame, "f_back") and frame.f_back is not None:
            back = frame.f_back
            if hasattr(back, "f_back") and back.f_back is not None:
                back = back.f_back
                if "self" in back.f_locals:
                    if isinstance(back.f_locals["self"], threading.Thread):
                        write_log = True
        try:
            if write_log:
                t = threadingCurrentThread()
                back = frame.f_back
                if not back:
                    return
                name, _, back_base = pydevd_file_utils.get_abs_path_real_path_and_base_from_frame(back)
                event_time = cur_time() - self.start_time
                method_name = frame.f_code.co_name

                if isinstance(self_obj, threading.Thread):
                    if not hasattr(self_obj, "_pydev_run_patched"):
                        wrap_attr(self_obj, "run")
                    if (method_name in THREAD_METHODS) and (
                        back_base not in DONT_TRACE_THREADING or (method_name in INNER_METHODS and back_base in INNER_FILES)
                    ):
                        thread_id = get_thread_id(self_obj)
                        name = self_obj.getName()
                        real_method = frame.f_code.co_name
                        parent = None
                        if real_method == "_stop":
                            if back_base in INNER_FILES and back.f_code.co_name == "_wait_for_tstate_lock":
                                back = back.f_back.f_back
                            real_method = "stop"
                            if hasattr(self_obj, "_pydev_join_called"):
                                parent = get_thread_id(t)
                        elif real_method == "join":
                            # join called in the current thread, not in self object
                            if not self_obj.is_alive():
                                return
                            thread_id = get_thread_id(t)
                            name = t.name
                            self_obj._pydev_join_called = True

                        if real_method == "start":
                            parent = get_thread_id(t)
                        send_concurrency_message(
                            "threading_event",
                            event_time,
                            name,
                            thread_id,
                            "thread",
                            real_method,
                            back.f_code.co_filename,
                            back.f_lineno,
                            back,
                            parent=parent,
                        )
                        # print(event_time, self_obj.getName(), thread_id, "thread",
                        #       real_method, back.f_code.co_filename, back.f_lineno)

                if method_name == "pydev_after_run_call":
                    if hasattr(frame, "f_back") and frame.f_back is not None:
                        back = frame.f_back
                        if hasattr(back, "f_back") and back.f_back is not None:
                            back = back.f_back
                        if "self" in back.f_locals:
                            if isinstance(back.f_locals["self"], threading.Thread):
                                my_self_obj = frame.f_back.f_back.f_locals["self"]
                                my_back = frame.f_back.f_back
                                my_thread_id = get_thread_id(my_self_obj)
                                send_massage = True
                                if hasattr(my_self_obj, "_pydev_join_called"):
                                    send_massage = False
                                    # we can't detect stop after join in Python 2 yet
                                if send_massage:
                                    send_concurrency_message(
                                        "threading_event",
                                        event_time,
                                        "Thread",
                                        my_thread_id,
                                        "thread",
                                        "stop",
                                        my_back.f_code.co_filename,
                                        my_back.f_lineno,
                                        my_back,
                                        parent=None,
                                    )

                if self_obj.__class__ == ObjectWrapper:
                    if back_base in DONT_TRACE_THREADING:
                        # do not trace methods called from threading
                        return
                    back_back_base = pydevd_file_utils.get_abs_path_real_path_and_base_from_frame(back.f_back)[2]
                    back = back.f_back
                    if back_back_base in DONT_TRACE_THREADING:
                        # back_back_base is the file, where the method was called froms
                        return
                    if method_name == "__init__":
                        send_concurrency_message(
                            "threading_event",
                            event_time,
                            t.name,
                            get_thread_id(t),
                            "lock",
                            method_name,
                            back.f_code.co_filename,
                            back.f_lineno,
                            back,
                            lock_id=str(id(frame.f_locals["self"])),
                        )
                    if "attr" in frame.f_locals and (frame.f_locals["attr"] in LOCK_METHODS or frame.f_locals["attr"] in QUEUE_METHODS):
                        real_method = frame.f_locals["attr"]
                        if method_name == "call_begin":
                            real_method += "_begin"
                        elif method_name == "call_end":
                            real_method += "_end"
                        else:
                            return
                        if real_method == "release_end":
                            # do not log release end. Maybe use it later
                            return
                        send_concurrency_message(
                            "threading_event",
                            event_time,
                            t.name,
                            get_thread_id(t),
                            "lock",
                            real_method,
                            back.f_code.co_filename,
                            back.f_lineno,
                            back,
                            lock_id=str(id(self_obj)),
                        )

                        if real_method in ("put_end", "get_end"):
                            # fake release for queue, cause we don't call it directly
                            send_concurrency_message(
                                "threading_event",
                                event_time,
                                t.name,
                                get_thread_id(t),
                                "lock",
                                "release",
                                back.f_code.co_filename,
                                back.f_lineno,
                                back,
                                lock_id=str(id(self_obj)),
                            )
                        # print(event_time, t.name, get_thread_id(t), "lock",
                        #       real_method, back.f_code.co_filename, back.f_lineno)

        except Exception:
            pydev_log.exception()


class NameManager:
    def __init__(self, name_prefix):
        self.tasks = {}
        self.last = 0
        self.prefix = name_prefix

    def get(self, id):
        if id not in self.tasks:
            self.last += 1
            self.tasks[id] = self.prefix + "-" + str(self.last)
        return self.tasks[id]


class AsyncioLogger:
    def __init__(self):
        self.task_mgr = NameManager("Task")
        self.coro_mgr = NameManager("Coro")
        self.start_time = cur_time()

    def get_task_id(self, frame):
        asyncio = sys.modules.get("asyncio")
        if asyncio is None:
            # If asyncio was not imported, there's nothing to be done
            # (also fixes issue where multiprocessing is imported due
            # to asyncio).
            return None
        while frame is not None:
            if "self" in frame.f_locals:
                self_obj = frame.f_locals["self"]
                if isinstance(self_obj, asyncio.Task):
                    method_name = frame.f_code.co_name
                    if method_name == "_step":
                        return id(self_obj)
            frame = frame.f_back
        return None

    def log_event(self, frame):
        event_time = cur_time() - self.start_time

        # Debug loop iterations
        # if isinstance(self_obj, asyncio.base_events.BaseEventLoop):
        #     if method_name == "_run_once":
        #         print("Loop iteration")

        if not hasattr(frame, "f_back") or frame.f_back is None:
            return

        asyncio = sys.modules.get("asyncio")
        if asyncio is None:
            # If asyncio was not imported, there's nothing to be done
            # (also fixes issue where multiprocessing is imported due
            # to asyncio).
            return

        back = frame.f_back

        if "self" in frame.f_locals:
            self_obj = frame.f_locals["self"]
            if isinstance(self_obj, asyncio.Task):
                method_name = frame.f_code.co_name
                if method_name == "set_result":
                    task_id = id(self_obj)
                    task_name = self.task_mgr.get(str(task_id))
                    send_concurrency_message(
                        "asyncio_event", event_time, task_name, task_name, "thread", "stop", frame.f_code.co_filename, frame.f_lineno, frame
                    )

                method_name = back.f_code.co_name
                if method_name == "__init__":
                    task_id = id(self_obj)
                    task_name = self.task_mgr.get(str(task_id))
                    send_concurrency_message(
                        "asyncio_event",
                        event_time,
                        task_name,
                        task_name,
                        "thread",
                        "start",
                        frame.f_code.co_filename,
                        frame.f_lineno,
                        frame,
                    )

            method_name = frame.f_code.co_name
            if isinstance(self_obj, asyncio.Lock):
                if method_name in ("acquire", "release"):
                    task_id = self.get_task_id(frame)
                    task_name = self.task_mgr.get(str(task_id))

                    if method_name == "acquire":
                        if not self_obj._waiters and not self_obj.locked():
                            send_concurrency_message(
                                "asyncio_event",
                                event_time,
                                task_name,
                                task_name,
                                "lock",
                                method_name + "_begin",
                                frame.f_code.co_filename,
                                frame.f_lineno,
                                frame,
                                lock_id=str(id(self_obj)),
                            )
                        if self_obj.locked():
                            method_name += "_begin"
                        else:
                            method_name += "_end"
                    elif method_name == "release":
                        method_name += "_end"

                    send_concurrency_message(
                        "asyncio_event",
                        event_time,
                        task_name,
                        task_name,
                        "lock",
                        method_name,
                        frame.f_code.co_filename,
                        frame.f_lineno,
                        frame,
                        lock_id=str(id(self_obj)),
                    )

            if isinstance(self_obj, asyncio.Queue):
                if method_name in ("put", "get", "_put", "_get"):
                    task_id = self.get_task_id(frame)
                    task_name = self.task_mgr.get(str(task_id))

                    if method_name == "put":
                        send_concurrency_message(
                            "asyncio_event",
                            event_time,
                            task_name,
                            task_name,
                            "lock",
                            "acquire_begin",
                            frame.f_code.co_filename,
                            frame.f_lineno,
                            frame,
                            lock_id=str(id(self_obj)),
                        )
                    elif method_name == "_put":
                        send_concurrency_message(
                            "asyncio_event",
                            event_time,
                            task_name,
                            task_name,
                            "lock",
                            "acquire_end",
                            frame.f_code.co_filename,
                            frame.f_lineno,
                            frame,
                            lock_id=str(id(self_obj)),
                        )
                        send_concurrency_message(
                            "asyncio_event",
                            event_time,
                            task_name,
                            task_name,
                            "lock",
                            "release",
                            frame.f_code.co_filename,
                            frame.f_lineno,
                            frame,
                            lock_id=str(id(self_obj)),
                        )
                    elif method_name == "get":
                        back = frame.f_back
                        if back.f_code.co_name != "send":
                            send_concurrency_message(
                                "asyncio_event",
                                event_time,
                                task_name,
                                task_name,
                                "lock",
                                "acquire_begin",
                                frame.f_code.co_filename,
                                frame.f_lineno,
                                frame,
                                lock_id=str(id(self_obj)),
                            )
                        else:
                            send_concurrency_message(
                                "asyncio_event",
                                event_time,
                                task_name,
                                task_name,
                                "lock",
                                "acquire_end",
                                frame.f_code.co_filename,
                                frame.f_lineno,
                                frame,
                                lock_id=str(id(self_obj)),
                            )
                            send_concurrency_message(
                                "asyncio_event",
                                event_time,
                                task_name,
                                task_name,
                                "lock",
                                "release",
                                frame.f_code.co_filename,
                                frame.f_lineno,
                                frame,
                                lock_id=str(id(self_obj)),
                            )

# === NexusCore/openenv\Lib\site-packages\jinxed\terminfo\xterm.py ===
"""
xterm terminal info

Since most of the Windows virtual processing schemes are based on xterm
This file is intended to be sourced and includes the man page descriptions

Most of this information came from the terminfo man pages, part of ncurses
More information on ncurses can be found at:
https://www.gnu.org/software/ncurses/ncurses.html

The values are as reported by infocmp on Fedora 30 with ncurses 6.1
"""

# pylint: disable=wrong-spelling-in-comment,line-too-long
# flake8: noqa: E501

BOOL_CAPS = [
    'am',  # (auto_right_margin) terminal has automatic margins
    'bce',  # (back_color_erase) screen erased with background color
    # 'bw',  # (auto_left_margin) cub1 wraps from column 0 to last column
    # 'ccc',  # (can_change) terminal can re-define existing colors
    # 'chts',  # (hard_cursor) cursor is hard to see
    # 'cpix',  # (cpi_changes_res) changing character pitch changes resolution
    # 'crxm',  # (cr_cancels_micro_mode) using cr turns off micro mode
    # 'daisy',  # (has_print_wheel) printer needs operator to change character set
    # 'da',  # (memory_above) display may be retained above the screen
    # 'db',  # (memory_below) display may be retained below the screen
    # 'eo',  # (erase_overstrike) can erase overstrikes with a blank
    # 'eslok',  # (status_line_esc_ok) escape can be used on the status line
    # 'gn',  # (generic_type) generic line type
    # 'hc',  # (hard_copy) hardcopy terminal
    # 'hls',  # (hue_lightness_saturation) terminal uses only HLS color notation (Tektronix)
    # 'hs',  # (has_status_line) has extra status line
    # 'hz',  # (tilde_glitch) cannot print ~'s (Hazeltine)
    # 'in',  # (insert_null_glitch) insert mode distinguishes nulls
    'km',  # (has_meta_key) Has a meta key (i.e., sets 8th-bit)
    # 'lpix',  # (lpi_changes_res) changing line pitch changes resolution
    'mc5i',  # (prtr_silent) printer will not echo on screen
    'mir',  # (move_insert_mode) safe to move while in insert mode
    'msgr',  # (move_standout_mode) safe to move while in standout mode
    # 'ndscr',  # (non_dest_scroll_region) scrolling region is non-destructive
    'npc',  # (no_pad_char) pad character does not exist
    # 'nrrmc',  # (non_rev_rmcup) smcup does not reverse rmcup
    # 'nxon',  # (needs_xon_xoff) padding will not work, xon/xoff required
    # 'os',  # (over_strike) terminal can overstrike
    # 'sam',  # (semi_auto_right_margin) printing in last column causes cr
    # 'ul',  # (transparent_underline) underline character overstrikes
    'xenl',  # (eat_newline_glitch) newline ignored after 80 cols (concept)
    # 'xhpa',  # (col_addr_glitch) only positive motion for hpa/mhpa caps
    # 'xhp',  # (ceol_standout_glitch) standout not erased by overwriting (hp)
    # 'xon',  # (xon_xoff) terminal uses xon/xoff handshaking
    # 'xsb',  # (no_esc_ctlc) beehive (f1=escape, f2=ctrl C)
    # 'xt',  # (dest_tabs_magic_smso) tabs destructive, magic so char (t1061)
    # 'xvpa',  # (row_addr_glitch) only positive motion for vpa/mvpa caps
]

NUM_CAPS = {
    # 'bitwin': 0,  # (bit_image_entwining) number of passes for each bit-image row
    # 'bitype': 0,  # (bit_image_type) type of bit-image device
    # 'btns': 0,  # (buttons) number of buttons on mouse
    # 'bufsz': 0,  # (buffer_capacity) numbers of bytes buffered before printing
    'colors': 8,  # (max_colors) maximum number of colors on screen
    'cols': 80,  # (columns) number of columns in a line
    # 'cps': 0,  # (print_rate) print rate in characters per second
    'it': 8,  # (init_tabs) tabs initially every # spaces
    # 'lh': 0,  # (label_height) rows in each label
    'lines': 24,  # (lines) number of lines on screen or page
    # 'lm': 0,  # (lines_of_memory) lines of memory if > line. 0 means varies
    # 'lw': 0,  # (label_width) columns in each label
    # 'ma': 0,  # (max_attributes) maximum combined attributes terminal can handle
    # 'maddr': 0,  # (max_micro_address) maximum value in micro_..._address
    # 'mcs': 0,  # (micro_col_size) character step size when in micro mode
    # 'mjump': 0,  # (max_micro_jump) maximum value in parm_..._micro
    # 'mls': 0,  # (micro_line_size) line step size when in micro mode
    # 'ncv': 0,  # (no_color_video) video attributes that cannot be used with colors
    # 'nlab': 0,  # (num_labels) number of labels on screen
    # 'npins': 0,  # (number_of_pins) numbers of pins in print-head
    # 'orc': 0,  # (output_res_char) horizontal resolution in units per line
    # 'orhi': 0,  # (output_res_horz_inch) horizontal resolution in units per inch
    # 'orl': 0,  # (output_res_line) vertical resolution in units per line
    # 'orvi': 0,  # (output_res_vert_inch) vertical resolution in units per inch
    'pairs': 64,  # (max_pairs) maximum number of color-pairs on the screen
    # 'pb': 0,  # (padding_baud_rate) lowest baud rate where padding needed
    # 'spinh': 0,  # (dot_horz_spacing) spacing of dots horizontally in dots per inch
    # 'spinv': 0,  # (dot_vert_spacing) spacing of pins vertically in pins per inch
    # 'vt': 0,  # (virtual_terminal) virtual terminal number (CB/unix)
    # 'widcs': 0,  # (wide_char_size) character step size when in double wide mode
    # 'wnum': 0,  # (maximum_windows) maximum number of definable windows
    # 'wsl': 0,  # (width_status_line) number of columns in status line
    # 'xmc': 0,  # (magic_cookie_glitch) number of blank characters left by smso or rmso
}

STR_CAPS = {
    'acsc': b'``aaffggiijjkkllmmnnooppqqrrssttuuvvwwxxyyzz{{||}}~~',  # (acs_chars) graphics charset pairs, based on vt100
    'bel': b'^G',  # (bell) audible signal (bell) (P)
    # 'bicr': b'',  # (bit_image_carriage_return) Move to beginning of same row
    # 'binel': b'',  # (bit_image_newline) Move to next row of the bit image
    # 'birep': b'',  # (bit_image_repeat) Repeat bit image cell #1 #2 times
    'blink': b'\x1b[5m',  # (enter_blink_mode) turn on blinking
    'bold': b'\x1b[1m',  # (enter_bold_mode) turn on bold (extra bright) mode
    'cbt': b'\x1b[Z',  # (back_tab) back tab (P)
    # 'chr': b'',  # (change_res_horz) Change horizontal resolution to #1
    'civis': b'\x1b[?25l',  # (cursor_invisible) make cursor invisible
    'clear': b'\x1b[H\x1b[2J',  # (clear_screen) clear screen and home cursor (P*)
    # 'cmdch': b'',  # (command_character) terminal settable cmd character in prototype !?
    'cnorm': b'\x1b[?12l\x1b[?25h',  # (cursor_normal) make cursor appear normal (undo civis/cvvis)
    # 'colornm': b'',  # (color_names) Give name for color #1
    # 'cpi': b'',  # (change_char_pitch) Change number of characters per inch to #1
    'cr': b'\r',  # (carriage_return) carriage return (P*) (P*)
    # 'csin': b'',  # (code_set_init) Init sequence for multiple codesets
    # 'csnm': b'',  # (char_set_names) Produce #1'th item from list of character set names
    'csr': b'\x1b[%i%p1%d;%p2%dr',  # (change_scroll_region) change region to line #1 to line #2 (P)
    'cub1': b'^H',  # (cursor_left) move left one space
    'cub': b'\x1b[%p1%dD',  # (parm_left_cursor) move #1 characters to the left (P)
    'cud1': b'\n',  # (cursor_down) down one line
    'cud': b'\x1b[%p1%dB',  # (parm_down_cursor) down #1 lines (P*)
    'cuf1': b'\x1b[C',  # (cursor_right) non-destructive space (move right one space)
    'cuf': b'\x1b[%p1%dC',  # (parm_right_cursor) move #1 characters to the right (P*)
    'cup': b'\x1b[%i%p1%d;%p2%dH',  # (cursor_address) move to row #1 columns #2
    'cuu1': b'\x1b[A',  # (cursor_up) up one line
    'cuu': b'\x1b[%p1%dA',  # (parm_up_cursor) up #1 lines (P*)
    # 'cvr': b'',  # (change_res_vert) Change vertical resolution to #1
    'cvvis': b'\x1b[?12;25h',  # (cursor_visible) make cursor very visible
    # 'cwin': b'',  # (create_window) define a window #1 from #2,#3 to #4,#5
    'dch1': b'\x1b[P',  # (delete_character) delete character (P*)
    'dch': b'\x1b[%p1%dP',  # (parm_dch) delete #1 characters (P*)
    # 'dclk': b'',  # (display_clock) display clock
    # 'defbi': b'',  # (define_bit_image_region) Define rectangular bit image region
    # 'defc': b'',  # (define_char) Define a character #1, #2 dots wide, descender #3
    # 'devt': b'',  # (device_type) Indicate language/codeset support
    # 'dial': b'',  # (dial_phone) dial number #1
    'dim': b'\x1b[2m',  # (enter_dim_mode) turn on half-bright mode
    # 'dispc': b'',  # (display_pc_char) Display PC character #1
    'dl1': b'\x1b[M',  # (delete_line) delete line (P*)
    'dl': b'\x1b[%p1%dM',  # (parm_delete_line) delete #1 lines (P*)
    # 'docr': b'',  # (these_cause_cr) Printing any of these characters causes CR
    # 'dsl': b'',  # (dis_status_line) disable status line
    'ech': b'\x1b[%p1%dX',  # (erase_chars) erase #1 characters (P)
    'ed': b'\x1b[J',  # (clr_eos) clear to end of screen (P*)
    'el1': b'\x1b[1K',  # (clr_bol) Clear to beginning of line
    'el': b'\x1b[K',  # (clr_eol) clear to end of line (P)
    # 'enacs': b'',  # (ena_acs) enable alternate char set
    # 'endbi': b'',  # (end_bit_image_region) End a bit-image region
    # 'ff': b'',  # (form_feed) hardcopy terminal page eject (P*)
    'flash': b'\x1b[?5h$<100/>\x1b[?5l',  # (flash_screen) visible bell (may not move cursor)
    # 'fln': b'',  # (label_format) label format
    # 'fsl': b'',  # (from_status_line) return from status line
    # 'getm': b'',  # (get_mouse) Curses should get button events, parameter #1 not documented.
    # 'hd': b'',  # (down_half_line) half a line down
    'home': b'\x1b[H',  # (cursor_home) home cursor (if no cup)
    # 'hook': b'',  # (flash_hook) flash switch hook
    'hpa': b'\x1b[%i%p1%dG',  # (column_address) horizontal position #1, absolute (P)
    'ht': b'^I',  # (tab) tab to next 8-space hardware tab stop
    'hts': b'\x1bH',  # (set_tab) set a tab in every row, current columns
    # 'hu': b'',  # (up_half_line) half a line up
    # 'hup': b'',  # (hangup) hang-up phone
    # 'ich1': b'',  # (insert_character) insert character (P)
    'ich': b'\x1b[%p1%d@',  # (parm_ich) insert #1 characters (P*)
    # 'if': b'',  # (init_file) name of initialization file
    'il1': b'\x1b[L',  # (insert_line) insert line (P*)
    'il': b'\x1b[%p1%dL',  # (parm_insert_line) insert #1 lines (P*)
    'ind': b'\n',  # (scroll_forward) scroll text up (P)
    'indn': b'\x1b[%p1%dS',  # (parm_index) scroll forward #1 lines (P)
    # 'initc': b'',  # (initialize_color) initialize color #1 to (#2,#3,#4)
    # 'initp': b'',  # (initialize_pair) Initialize color pair #1 to fg=(#2,#3,#4), bg=(#5,#6,#7)
    'invis': b'\x1b[8m',  # (enter_secure_mode) turn on blank mode (characters invisible)
    # 'ip': b'',  # (insert_padding) insert padding after inserted character
    # 'iprog': b'',  # (init_prog) path name of program for initialization
    # 'is1': b'',  # (init_1string) initialization string
    'is2': b'\x1b[!p\x1b[?3;4l\x1b[4l\x1b>',  # (init_2string) initialization string
    # 'is3': b'',  # (init_3string) initialization string
    # 'ka1': b'',  # (key_a1) upper left of keypad
    # 'ka3': b'',  # (key_a3) upper right of keypad
    'kb2': b'\x1bOE',  # (key_b2) center of keypad
    # 'kbeg': b'',  # (key_beg) begin key
    # 'kBEG': b'',  # (key_sbeg) shifted begin key
    'kbs': b'^?',  # (key_backspace) backspace key
    # 'kc1': b'',  # (key_c1) lower left of keypad
    # 'kc3': b'',  # (key_c3) lower right of keypad
    # 'kcan': b'',  # (key_cancel) cancel key
    # 'kCAN': b'',  # (key_scancel) shifted cancel key
    'kcbt': b'\x1b[Z',  # (key_btab) back-tab key
    # 'kclo': b'',  # (key_close) close key
    # 'kclr': b'',  # (key_clear) clear-screen or erase key
    # 'kcmd': b'',  # (key_command) command key
    # 'kCMD': b'',  # (key_scommand) shifted command key
    # 'kcpy': b'',  # (key_copy) copy key
    # 'kCPY': b'',  # (key_scopy) shifted copy key
    # 'kcrt': b'',  # (key_create) create key
    # 'kCRT': b'',  # (key_screate) shifted create key
    # 'kctab': b'',  # (key_ctab) clear-tab key
    'kcub1': b'\x1bOD',  # (key_left) left-arrow key
    'kcud1': b'\x1bOB',  # (key_down) down-arrow key
    'kcuf1': b'\x1bOC',  # (key_right) right-arrow key
    'kcuu1': b'\x1bOA',  # (key_up) up-arrow key
    'kDC': b'\x1b[3;2~',  # (key_sdc) shifted delete- character key
    'kdch1': b'\x1b[3~',  # (key_dc) delete-character key
    # 'kdl1': b'',  # (key_dl) delete-line key
    # 'kDL': b'',  # (key_sdl) shifted delete-line key
    # 'ked': b'',  # (key_eos) clear-to-end-of- screen key
    # 'kel': b'',  # (key_eol) clear-to-end-of-line key
    'kEND': b'\x1b[1;2F',  # (key_send) shifted end key
    'kend': b'\x1bOF',  # (key_end) end key
    'kent': b'\x1bOM',  # (key_enter) enter/send key
    # 'kEOL': b'',  # (key_seol) shifted clear-to- end-of-line key
    # 'kext': b'',  # (key_exit) exit key
    # 'kEXT': b'',  # (key_sexit) shifted exit key
    # 'kf0': b'',  # (key_f0) F0 function key
    'kf1': b'\x1bOP',  # (key_f1) F1 function key
    'kf2': b'\x1bOQ',  # (key_f2) F2 function key
    'kf3': b'\x1bOR',  # (key_f3) F3 function key
    'kf4': b'\x1bOS',  # (key_f4) F4 function key
    'kf5': b'\x1b[15~',  # (key_f5) F5 function key
    'kf6': b'\x1b[17~',  # (key_f6) F6 function key
    'kf7': b'\x1b[18~',  # (key_f7) F7 function key
    'kf8': b'\x1b[19~',  # (key_f8) F8 function key
    'kf9': b'\x1b[20~',  # (key_f9) F9 function key
    'kf10': b'\x1b[21~',  # (key_f10) F10 function key
    'kf11': b'\x1b[23~',  # (key_f11) F11 function key
    'kf12': b'\x1b[24~',  # (key_f12) F12 function key
    'kf13': b'\x1b[1;2P',  # (key_f13) F13 function key
    'kf14': b'\x1b[1;2Q',  # (key_f14) F14 function key
    'kf15': b'\x1b[1;2R',  # (key_f15) F15 function key
    'kf16': b'\x1b[1;2S',  # (key_f16) F16 function key
    'kf17': b'\x1b[15;2~',  # (key_f17) F17 function key
    'kf18': b'\x1b[17;2~',  # (key_f18) F18 function key
    'kf19': b'\x1b[18;2~',  # (key_f19) F19 function key
    'kf20': b'\x1b[19;2~',  # (key_f20) F20 function key
    'kf21': b'\x1b[20;2~',  # (key_f21) F21 function key
    'kf22': b'\x1b[21;2~',  # (key_f22) F22 function key
    'kf23': b'\x1b[23;2~',  # (key_f23) F23 function key
    'kf24': b'\x1b[24;2~',  # (key_f24) F24 function key
    'kf25': b'\x1b[1;5P',  # (key_f25) F25 function key
    'kf26': b'\x1b[1;5Q',  # (key_f26) F26 function key
    'kf27': b'\x1b[1;5R',  # (key_f27) F27 function key
    'kf28': b'\x1b[1;5S',  # (key_f28) F28 function key
    'kf29': b'\x1b[15;5~',  # (key_f29) F29 function key
    'kf30': b'\x1b[17;5~',  # (key_f30) F30 function key
    'kf31': b'\x1b[18;5~',  # (key_f31) F31 function key
    'kf32': b'\x1b[19;5~',  # (key_f32) F32 function key
    'kf33': b'\x1b[20;5~',  # (key_f33) F33 function key
    'kf34': b'\x1b[21;5~',  # (key_f34) F34 function key
    'kf35': b'\x1b[23;5~',  # (key_f35) F35 function key
    'kf36': b'\x1b[24;5~',  # (key_f36) F36 function key
    'kf37': b'\x1b[1;6P',  # (key_f37) F37 function key
    'kf38': b'\x1b[1;6Q',  # (key_f38) F38 function key
    'kf39': b'\x1b[1;6R',  # (key_f39) F39 function key
    'kf40': b'\x1b[1;6S',  # (key_f40) F40 function key
    'kf41': b'\x1b[15;6~',  # (key_f41) F41 function key
    'kf42': b'\x1b[17;6~',  # (key_f42) F42 function key
    'kf43': b'\x1b[18;6~',  # (key_f43) F43 function key
    'kf44': b'\x1b[19;6~',  # (key_f44) F44 function key
    'kf45': b'\x1b[20;6~',  # (key_f45) F45 function key
    'kf46': b'\x1b[21;6~',  # (key_f46) F46 function key
    'kf47': b'\x1b[23;6~',  # (key_f47) F47 function key
    'kf48': b'\x1b[24;6~',  # (key_f48) F48 function key
    'kf49': b'\x1b[1;3P',  # (key_f49) F49 function key
    'kf50': b'\x1b[1;3Q',  # (key_f50) F50 function key
    'kf51': b'\x1b[1;3R',  # (key_f51) F51 function key
    'kf52': b'\x1b[1;3S',  # (key_f52) F52 function key
    'kf53': b'\x1b[15;3~',  # (key_f53) F53 function key
    'kf54': b'\x1b[17;3~',  # (key_f54) F54 function key
    'kf55': b'\x1b[18;3~',  # (key_f55) F55 function key
    'kf56': b'\x1b[19;3~',  # (key_f56) F56 function key
    'kf57': b'\x1b[20;3~',  # (key_f57) F57 function key
    'kf58': b'\x1b[21;3~',  # (key_f58) F58 function key
    'kf59': b'\x1b[23;3~',  # (key_f59) F59 function key
    'kf60': b'\x1b[24;3~',  # (key_f60) F60 function key
    'kf61': b'\x1b[1;4P',  # (key_f61) F61 function key
    'kf62': b'\x1b[1;4Q',  # (key_f62) F62 function key
    'kf63': b'\x1b[1;4R',  # (key_f63) F63 function key
    # 'kfnd': b'',  # (key_find) find key
    # 'kFND': b'',  # (key_sfind) shifted find key
    # 'khlp': b'',  # (key_help) help key
    # 'kHLP': b'',  # (key_shelp) shifted help key
    'kHOM': b'\x1b[1;2H',  # (key_shome) shifted home key
    'khome': b'\x1bOH',  # (key_home) home key
    # 'khts': b'',  # (key_stab) set-tab key
    'kIC': b'\x1b[2;2~',  # (key_sic) shifted insert- character key
    'kich1': b'\x1b[2~',  # (key_ic) insert-character key
    # 'kil1': b'',  # (key_il) insert-line key
    'kind': b'\x1b[1;2B',  # (key_sf) scroll-forward key
    'kLFT': b'\x1b[1;2D',  # (key_sleft) shifted left-arrow key
    # 'kll': b'',  # (key_ll) lower-left key (home down)
    'kmous': b'\x1b[<',  # (key_mouse) Mouse event has occurred
    # 'kmov': b'',  # (key_move) move key
    # 'kMOV': b'',  # (key_smove) shifted move key
    # 'kmrk': b'',  # (key_mark) mark key
    # 'kmsg': b'',  # (key_message) message key
    # 'kMSG': b'',  # (key_smessage) shifted message key
    'knp': b'\x1b[6~',  # (key_npage) next-page key
    # 'knxt': b'',  # (key_next) next key
    'kNXT': b'\x1b[6;2~',  # (key_snext) shifted next key
    # 'kopn': b'',  # (key_open) open key
    # 'kopt': b'',  # (key_options) options key
    # 'kOPT': b'',  # (key_soptions) shifted options key
    'kpp': b'\x1b[5~',  # (key_ppage) previous-page key
    # 'kprt': b'',  # (key_print) print key
    # 'kPRT': b'',  # (key_sprint) shifted print key
    # 'kprv': b'',  # (key_previous) previous key
    'kPRV': b'\x1b[5;2~',  # (key_sprevious) shifted previous key
    # 'krdo': b'',  # (key_redo) redo key
    # 'kRDO': b'',  # (key_sredo) shifted redo key
    # 'kref': b'',  # (key_reference) reference key
    # 'kres': b'',  # (key_resume) resume key
    # 'kRES': b'',  # (key_srsume) shifted resume key
    # 'krfr': b'',  # (key_refresh) refresh key
    'kri': b'\x1b[1;2A',  # (key_sr) scroll-backward key
    'kRIT': b'\x1b[1;2C',  # (key_sright) shifted right-arrow key
    # 'krmir': b'',  # (key_eic) sent by rmir or smir in insert mode
    # 'krpl': b'',  # (key_replace) replace key
    # 'kRPL': b'',  # (key_sreplace) shifted replace key
    # 'krst': b'',  # (key_restart) restart key
    # 'ksav': b'',  # (key_save) save key
    # 'kSAV': b'',  # (key_ssave) shifted save key
    # 'kslt': b'',  # (key_select) select key
    # 'kSPD': b'',  # (key_ssuspend) shifted suspend key
    # 'kspd': b'',  # (key_suspend) suspend key
    # 'ktbc': b'',  # (key_catab) clear-all-tabs key
    # 'kUND': b'',  # (key_sundo) shifted undo key
    # 'kund': b'',  # (key_undo) undo key
    # 'lf0': b'',  # (lab_f0) label on function key f0 if not f0
    # 'lf10': b'',  # (lab_f10) label on function key f10 if not f10
    # 'lf1': b'',  # (lab_f1) label on function key f1 if not f1
    # 'lf2': b'',  # (lab_f2) label on function key f2 if not f2
    # 'lf3': b'',  # (lab_f3) label on function key f3 if not f3
    # 'lf4': b'',  # (lab_f4) label on function key f4 if not f4
    # 'lf5': b'',  # (lab_f5) label on function key f5 if not f5
    # 'lf6': b'',  # (lab_f6) label on function key f6 if not f6
    # 'lf7': b'',  # (lab_f7) label on function key f7 if not f7
    # 'lf8': b'',  # (lab_f8) label on function key f8 if not f8
    # 'lf9': b'',  # (lab_f9) label on function key f9 if not f9
    # 'll': b'',  # (cursor_to_ll) last line, first column (if no cup)
    # 'lpi': b'',  # (change_line_pitch) Change number of lines per inch to #1
    'meml': b'\x1bl',  # lock memory above the curser
    'memu': b'\x1bl',  # unlock memory above the curser
    'mc0': b'\x1b[i',  # (print_screen) print contents of screen
    'mc4': b'\x1b[4i',  # (prtr_off) turn off printer
    'mc5': b'\x1b[5i',  # (prtr_on) turn on printer
    # 'mc5p': b'',  # (prtr_non) turn on printer for #1 bytes
    # 'mcub1': b'',  # (micro_left) Like cursor_left in micro mode
    # 'mcub': b'',  # (parm_left_micro) Like parm_left_cursor in micro mode
    # 'mcud1': b'',  # (micro_down) Like cursor_down in micro mode
    # 'mcud': b'',  # (parm_down_micro) Like parm_down_cursor in micro mode
    # 'mcuf1': b'',  # (micro_right) Like cursor_right in micro mode
    # 'mcuf': b'',  # (parm_right_micro) Like parm_right_cursor in micro mode
    # 'mcuu1': b'',  # (micro_up) Like cursor_up in micro mode
    # 'mcuu': b'',  # (parm_up_micro) Like parm_up_cursor in micro mode
    # 'mgc': b'',  # (clear_margins) clear right and left soft margins
    # 'mhpa': b'',  # (micro_column_address) Like column_address in micro mode
    # 'minfo': b'',  # (mouse_info) Mouse status information
    # 'mrcup': b'',  # (cursor_mem_address) memory relative cursor addressing, move to row #1 columns #2
    # 'mvpa': b'',  # (micro_row_address) Like row_address #1 in micro mode
    # 'nel': b'',  # (newline) newline (behave like cr followed by lf)
    # 'oc': b'',  # (orig_colors) Set all color pairs to the original ones
    'op': b'\x1b[39;49m',  # (orig_pair) Set default pair to its original value
    # 'pad': b'',  # (pad_char) padding char (instead of null)
    # 'pause': b'',  # (fixed_pause) pause for 2-3 seconds
    # 'pctrm': b'',  # (pc_term_options) PC terminal options
    # 'pfkey': b'',  # (pkey_key) program function key #1 to type string #2
    # 'pfloc': b'',  # (pkey_local) program function key #1 to execute string #2
    # 'pfx': b'',  # (pkey_xmit) program function key #1 to transmit string #2
    # 'pfxl': b'',  # (pkey_plab) Program function key #1 to type string #2 and show string #3
    # 'pln': b'',  # (plab_norm) program label #1 to show string #2
    # 'porder': b'',  # (order_of_pins) Match software bits to print-head pins
    # 'prot': b'',  # (enter_protected_mode) turn on protected mode
    # 'pulse': b'',  # (pulse) select pulse dialing
    # 'qdial': b'',  # (quick_dial) dial number #1 without checking
    # 'rbim': b'',  # (stop_bit_image) Stop printing bit image graphics
    'rc': b'\x1b8',  # (restore_cursor) restore cursor to position of last save_cursor
    # 'rcsd': b'',  # (stop_char_set_def) End definition of character set #1
    'rep': b'%p1%c\x1b[%p2%{1}%-%db',  # (repeat_char) repeat char #1 #2 times (P*)
    # 'reqmp': b'',  # (req_mouse_pos) Request mouse position
    'rev': b'\x1b[7m',  # (enter_reverse_mode) turn on reverse video mode
    # 'rf': b'',  # (reset_file) name of reset file
    # 'rfi': b'',  # (req_for_input) send next input char (for ptys)
    'ri': b'\x1bM',  # (scroll_reverse) scroll text down (P)
    'rin': b'\x1b[%p1%dT',  # (parm_rindex) scroll back #1 lines (P)
    'ritm': b'\x1b[23m',  # (exit_italics_mode) End italic mode
    # 'rlm': b'',  # (exit_leftward_mode) End left-motion mode
    'rmacs': b'\x1b(B',  # (exit_alt_charset_mode) end alternate character set (P)
    'rmam': b'\x1b[?7l',  # (exit_am_mode) turn off automatic margins
    # 'rmclk': b'',  # (remove_clock) remove clock
    'rmcup': b'\x1b[?1049l\x1b[23;0;0t',  # (exit_ca_mode) strings to end programs using cup
    # 'rmdc': b'',  # (exit_delete_mode) end delete mode
    # 'rmicm': b'',  # (exit_micro_mode) End micro-motion mode
    'rmir': b'\x1b[4l',  # (exit_insert_mode) exit insert mode
    'rmkx': b'\x1b[?1l\x1b>',  # (keypad_local) leave 'keyboard_transmit' mode
    # 'rmln': b'',  # (label_off) turn off soft labels
    'rmm': b'\x1b[?1034l',  # (meta_off) turn off meta mode
    # 'rmp': b'',  # (char_padding) like ip but when in insert mode
    # 'rmpch': b'',  # (exit_pc_charset_mode) Exit PC character display mode
    # 'rmsc': b'',  # (exit_scancode_mode) Exit PC scancode mode
    'rmso': b'\x1b[27m',  # (exit_standout_mode) exit standout mode
    'rmul': b'\x1b[24m',  # (exit_underline_mode) exit underline mode
    # 'rmxon': b'',  # (exit_xon_mode) turn off xon/xoff handshaking
    'rs1': b'\x1bc',  # (reset_1string) reset string
    'rs2': b'\x1b[!p\x1b[?3;4l\x1b[4l\x1b>',  # (reset_2string) reset string
    # 'rs3': b'',  # (reset_3string) reset string
    # 'rshm': b'',  # (exit_shadow_mode) End shadow-print mode
    # 'rsubm': b'',  # (exit_subscript_mode) End subscript mode
    # 'rsupm': b'',  # (exit_superscript_mode) End superscript mode
    # 'rum': b'',  # (exit_upward_mode) End reverse character motion
    # 'rwidm': b'',  # (exit_doublewide_mode) End double-wide mode
    # 's0ds': b'',  # (set0_des_seq) Shift to codeset 0 (EUC set 0, ASCII)
    # 's1ds': b'',  # (set1_des_seq) Shift to codeset 1
    # 's2ds': b'',  # (set2_des_seq) Shift to codeset 2
    # 's3ds': b'',  # (set3_des_seq) Shift to codeset 3
    # 'sbim': b'',  # (start_bit_image) Start printing bit image graphics
    'sc': b'\x1b7',  # (save_cursor) save current cursor position (P)
    # 'scesa': b'',  # (alt_scancode_esc) Alternate escape for scancode emulation
    # 'scesc': b'',  # (scancode_escape) Escape for scancode emulation
    # 'sclk': b'',  # (set_clock) set clock, #1 hrs #2 mins #3 secs
    # 'scp': b'',  # (set_color_pair) Set current color pair to #1
    # 'scs': b'',  # (select_char_set) Select character set, #1
    # 'scsd': b'',  # (start_char_set_def) Start character set definition #1, with #2 characters in the set
    # 'sdrfq': b'',  # (enter_draft_quality) Enter draft-quality mode
    'setab': b'\x1b[4%p1%dm',  # (set_a_background) Set background color to #1, using ANSI escape
    'setaf': b'\x1b[3%p1%dm',  # (set_a_foreground) Set foreground color to #1, using ANSI escape
    'setb': b'\x1b[4%?%p1%{1}%=%t4%e%p1%{3}%=%t6%e%p1%{4}%=%t1%e%p1%{6}%=%t3%e%p1%d%;m',  # (set_background) Set background color #1
    # 'setcolor': b'',  # (set_color_band) Change to ribbon color #1
    'setf': b'\x1b[3%?%p1%{1}%=%t4%e%p1%{3}%=%t6%e%p1%{4}%=%t1%e%p1%{6}%=%t3%e%p1%d%;m',  # (set_foreground) Set foreground color #1
    'sgr0': b'\x1b(B\x1b[m',  # (exit_attribute_mode) turn off all attributes
    'sgr': b'%?%p9%t\x1b(0%e\x1b(B%;\x1b[0%?%p6%t;1%;%?%p5%t;2%;%?%p2%t;4%;%?%p1%p3%|%t;7%;%?%p4%t;5%;%?%p7%t;8%;m',  # (set_attributes) define video attributes #1-#9 (PG9)
    'sitm': b'\x1b[3m',  # (enter_italics_mode) Enter italic mode
    # 'slines': b'',  # (set_page_length) Set page length to #1 lines
    # 'slm': b'',  # (enter_leftward_mode) Start leftward carriage motion
    'smacs': b'\x1b(0',  # (enter_alt_charset_mode) start alternate character set (P)
    'smam': b'\x1b[?7h',  # (enter_am_mode) turn on automatic margins
    'smcup': b'\x1b[?1049h\x1b[22;0;0t',  # (enter_ca_mode) string to start programs using cup
    # 'smdc': b'',  # (enter_delete_mode) enter delete mode
    # 'smgb': b'',  # (set_bottom_margin) Set bottom margin at current line
    # 'smgbp': b'',  # (set_bottom_margin_parm) Set bottom margin at line #1 or (if smgtp is not given) #2 lines from bottom
    # 'smgl': b'',  # (set_left_margin) set left soft margin at current column.     See smgl. (ML is not in BSD termcap).
    # 'smglp': b'',  # (set_left_margin_parm) Set left (right) margin at column #1
    # 'smglr': b'',  # (set_lr_margin) Set both left and right margins to #1, #2.  (ML is not in BSD termcap).
    # 'smgr': b'',  # (set_right_margin) set right soft margin at current column
    # 'smgrp': b'',  # (set_right_margin_parm) Set right margin at column #1
    # 'smgtb': b'',  # (set_tb_margin) Sets both top and bottom margins to #1, #2
    # 'smgt': b'',  # (set_top_margin) Set top margin at current line
    # 'smgtp': b'',  # (set_top_margin_parm) Set top (bottom) margin at row #1
    # 'smicm': b'',  # (enter_micro_mode) Start micro-motion mode
    'smir': b'\x1b[4h',  # (enter_insert_mode) enter insert mode
    'smkx': b'\x1b[?1h\x1b=',  # (keypad_xmit) enter 'keyboard_transmit' mode
    # 'smln': b'',  # (label_on) turn on soft labels
    'smm': b'\x1b[?1034h',  # (meta_on) turn on meta mode (8th-bit on)
    # 'smpch': b'',  # (enter_pc_charset_mode) Enter PC character display mode
    # 'smsc': b'',  # (enter_scancode_mode) Enter PC scancode mode
    'smso': b'\x1b[7m',  # (enter_standout_mode) begin standout mode
    'smul': b'\x1b[4m',  # (enter_underline_mode) begin underline mode
    # 'smxon': b'',  # (enter_xon_mode) turn on xon/xoff handshaking
    # 'snlq': b'',  # (enter_near_letter_quality) Enter NLQ mode
    # 'snrmq': b'',  # (enter_normal_quality) Enter normal-quality mode
    # 'sshm': b'',  # (enter_shadow_mode) Enter shadow-print mode
    # 'ssubm': b'',  # (enter_subscript_mode) Enter subscript mode
    # 'ssupm': b'',  # (enter_superscript_mode) Enter superscript mode
    # 'subcs': b'',  # (subscript_characters) List of subscriptable characters
    # 'sum': b'',  # (enter_upward_mode) Start upward carriage motion
    # 'supcs': b'',  # (superscript_characters) List of superscriptable characters
    # 'swidm': b'',  # (enter_doublewide_mode) Enter double-wide mode
    'tbc': b'\x1b[3g',  # (clear_all_tabs) clear all tab stops (P)
    # 'tone': b'',  # (tone) select touch tone dialing
    # 'tsl': b'',  # (to_status_line) move to status line, column #1
    # 'u0': b'',  # (user0) User string #0
    # 'u1': b'',  # (user1) User string #1
    # 'u2': b'',  # (user2) User string #2
    # 'u3': b'',  # (user3) User string #3
    # 'u4': b'',  # (user4) User string #4
    # 'u5': b'',  # (user5) User string #5
    'u6': b'\x1b[%i%d;%dR',  # (user6) User string #6 [cursor position report (equiv. to ANSI/ECMA-48 CPR)]
    'u7': b'\x1b[6n',  # (user7) User string #7 [cursor position request (equiv. to VT100/ANSI/ECMA-48 DSR 6)]
    'u8': b'\x1b[?%[;0123456789]c',  # (user8) User string #8 [terminal answerback description]
    'u9': b'\x1b[c',  # (user9) User string #9 [terminal enquire string (equiv. to ANSI/ECMA-48 DA)]
    # 'uc': b'',  # (underline_char) underline char and move past it
    'vpa': b'\x1b[%i%p1%dd',  # (row_address) vertical position #1 absolute (P)
    # 'wait': b'',  # (wait_tone) wait for dial-tone
    # 'wind': b'',  # (set_window) current window is lines #1-#2 cols #3-#4
    # 'wingo': b'',  # (goto_window) go to window #1
    # 'xoffc': b'',  # (xoff_character) XOFF character
    # 'xonc': b'',  # (xon_character) XON character
    # 'zerom': b'',  # (zero_motion) No motion for subsequent character
}

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_endpoints\tag_management_endpoints.py ===
"""
TAG MANAGEMENT

All /tag management endpoints

/tag/new
/tag/info
/tag/update
/tag/delete
/tag/list
"""

import asyncio
import datetime
import json
from typing import TYPE_CHECKING, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from litellm._logging import verbose_proxy_logger
from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
from litellm.proxy._types import UserAPIKeyAuth
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.management_endpoints.common_daily_activity import (
    SpendAnalyticsPaginatedResponse,
    get_daily_activity,
)
from litellm.types.tag_management import (
    LiteLLM_DailyTagSpendTable,
    TagConfig,
    TagDeleteRequest,
    TagInfoRequest,
    TagNewRequest,
    TagUpdateRequest,
)

if TYPE_CHECKING:
    from litellm import Router
    from litellm.types.router import Deployment

router = APIRouter()


async def _get_model_names(prisma_client, model_ids: list) -> Dict[str, str]:
    """Helper function to get model names from model IDs"""
    try:
        models = await prisma_client.db.litellm_proxymodeltable.find_many(
            where={"model_id": {"in": model_ids}}
        )
        return {model.model_id: model.model_name for model in models}
    except Exception as e:
        verbose_proxy_logger.error(f"Error getting model names: {str(e)}")
        return {}


async def _get_tags_config(prisma_client) -> Dict[str, TagConfig]:
    """Helper function to get tags config from db"""
    try:
        tags_config = await prisma_client.db.litellm_config.find_unique(
            where={"param_name": "tags_config"}
        )
        if tags_config is None:
            return {}
        # Convert from JSON if needed
        if isinstance(tags_config.param_value, str):
            config_dict = json.loads(tags_config.param_value)
        else:
            config_dict = tags_config.param_value or {}

        # For each tag, get the model names
        for tag_name, tag_config in config_dict.items():
            if isinstance(tag_config, dict) and tag_config.get("models"):
                model_info = await _get_model_names(prisma_client, tag_config["models"])
                tag_config["model_info"] = model_info

        return config_dict
    except Exception:
        return {}


async def _save_tags_config(prisma_client, tags_config: Dict[str, TagConfig]):
    """Helper function to save tags config to db"""
    try:
        verbose_proxy_logger.debug(f"Saving tags config: {tags_config}")
        # Convert TagConfig objects to dictionaries
        tags_config_dict = {}
        for name, tag in tags_config.items():
            if isinstance(tag, TagConfig):
                tag_dict = tag.model_dump()
                # Remove model_info before saving as it will be dynamically generated
                if "model_info" in tag_dict:
                    del tag_dict["model_info"]
                tags_config_dict[name] = tag_dict
            else:
                # If it's already a dict, remove model_info
                tag_copy = tag.copy()
                if "model_info" in tag_copy:
                    del tag_copy["model_info"]
                tags_config_dict[name] = tag_copy

        json_tags_config = json.dumps(tags_config_dict, default=str)
        verbose_proxy_logger.debug(f"JSON tags config: {json_tags_config}")
        await prisma_client.db.litellm_config.upsert(
            where={"param_name": "tags_config"},
            data={
                "create": {
                    "param_name": "tags_config",
                    "param_value": json_tags_config,
                },
                "update": {"param_value": json_tags_config},
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving tags config: {str(e)}"
        )


async def get_deployments_by_model(
    model: str, llm_router: "Router"
) -> List["Deployment"]:
    """
    Get all deployments by model
    """
    from litellm.types.router import Deployment, LiteLLM_Params, ModelInfo

    # Check if model id
    deployment = llm_router.get_deployment(model_id=model)
    if deployment is not None:
        return [deployment]

    # Check if model name
    deployments = llm_router.get_model_list(model_name=model)
    if deployments is None:
        return []
    return [
        Deployment(
            model_name=deployment["model_name"],
            litellm_params=LiteLLM_Params(**deployment["litellm_params"]),  # type: ignore
            model_info=ModelInfo(**deployment.get("model_info") or {}),
        )
        for deployment in deployments
    ]


@router.post(
    "/tag/new",
    tags=["tag management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def new_tag(
    tag: TagNewRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Create a new tag.

    Parameters:
    - name: str - The name of the tag
    - description: Optional[str] - Description of what this tag represents
    - models: List[str] - List of either 'model_id' or 'model_name' allowed for this tag
    """
    from litellm.proxy._types import CommonProxyErrors
    from litellm.proxy.proxy_server import llm_router, prisma_client

    if prisma_client is None:
        raise HTTPException(
            status_code=500, detail=CommonProxyErrors.db_not_connected_error.value
        )
    if llm_router is None:
        raise HTTPException(
            status_code=500, detail=CommonProxyErrors.no_llm_router.value
        )
    try:
        # Get existing tags config
        tags_config = await _get_tags_config(prisma_client)

        # Check if tag already exists
        if tag.name in tags_config:
            raise HTTPException(
                status_code=400, detail=f"Tag {tag.name} already exists"
            )

        # Add new tag
        tags_config[tag.name] = TagConfig(
            name=tag.name,
            description=tag.description,
            models=tag.models,
            created_at=str(datetime.datetime.now()),
            updated_at=str(datetime.datetime.now()),
            created_by=user_api_key_dict.user_id,
        )

        # Save updated config
        await _save_tags_config(
            prisma_client=prisma_client,
            tags_config=tags_config,
        )

        # Update models with new tag
        if tag.models:
            tasks = []
            for model in tag.models:
                deployments = await get_deployments_by_model(model, llm_router)
                tasks.extend(
                    [
                        _add_tag_to_deployment(
                            deployment=deployment,
                            tag=tag.name,
                        )
                        for deployment in deployments
                    ]
                )
            await asyncio.gather(*tasks)

        # Get model names for response
        model_info = await _get_model_names(prisma_client, tag.models or [])
        tags_config[tag.name].model_info = model_info

        return {
            "message": f"Tag {tag.name} created successfully",
            "tag": tags_config[tag.name],
        }
    except Exception as e:
        verbose_proxy_logger.exception(f"Error creating tag: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _add_tag_to_deployment(deployment: "Deployment", tag: str):
    """Helper function to add tag to deployment"""
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    litellm_params = deployment.litellm_params
    if "tags" not in litellm_params:
        litellm_params["tags"] = []
    litellm_params["tags"].append(tag)

    try:
        await prisma_client.db.litellm_proxymodeltable.update(
            where={"model_id": deployment.model_info.id},
            data={"litellm_params": safe_dumps(litellm_params)},
        )
    except Exception as e:
        verbose_proxy_logger.exception(f"Error adding tag to deployment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/tag/update",
    tags=["tag management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def update_tag(
    tag: TagUpdateRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Update an existing tag.

    Parameters:
    - name: str - The name of the tag to update
    - description: Optional[str] - Updated description
    - models: List[str] - Updated list of allowed LLM models
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    try:
        # Get existing tags config
        tags_config = await _get_tags_config(prisma_client)

        # Check if tag exists
        if tag.name not in tags_config:
            raise HTTPException(status_code=404, detail=f"Tag {tag.name} not found")

        # Update tag
        tag_config_dict = dict(tags_config[tag.name])
        tag_config_dict.update(
            {
                "description": tag.description,
                "models": tag.models,
                "updated_at": str(datetime.datetime.now()),
                "updated_by": user_api_key_dict.user_id,
            }
        )
        tags_config[tag.name] = TagConfig(**tag_config_dict)

        # Save updated config
        await _save_tags_config(prisma_client, tags_config)

        # Get model names for response
        model_info = await _get_model_names(prisma_client, tag.models or [])
        tags_config[tag.name].model_info = model_info

        return {
            "message": f"Tag {tag.name} updated successfully",
            "tag": tags_config[tag.name],
        }
    except Exception as e:
        verbose_proxy_logger.exception(f"Error updating tag: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/tag/info",
    tags=["tag management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def info_tag(
    data: TagInfoRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get information about specific tags.

    Parameters:
    - names: List[str] - List of tag names to get information for
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    try:
        tags_config = await _get_tags_config(prisma_client)

        # Filter tags based on requested names
        requested_tags = {name: tags_config.get(name) for name in data.names}

        # Check if any requested tags don't exist
        missing_tags = [name for name in data.names if name not in tags_config]
        if missing_tags:
            raise HTTPException(
                status_code=404, detail=f"Tags not found: {missing_tags}"
            )

        return requested_tags
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tag/list",
    tags=["tag management"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=List[TagConfig],
)
async def list_tags(
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    List all available tags.
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    try:
        ## QUERY STORED TAGS ##
        tags_config = await _get_tags_config(prisma_client)
        list_of_tags = list(tags_config.values())

        ## QUERY DYNAMIC TAGS ##
        dynamic_tags = await prisma_client.db.litellm_dailytagspend.find_many(
            distinct=["tag"],
        )

        dynamic_tags_list = [
            LiteLLM_DailyTagSpendTable(**dynamic_tag.model_dump())
            for dynamic_tag in dynamic_tags
        ]

        dynamic_tag_config = [
            TagConfig(
                name=tag.tag,
                description="This is just a spend tag that was passed dynamically in a request. It does not control any LLM models.",
                models=None,
                created_at=tag.created_at.isoformat(),
                updated_at=tag.updated_at.isoformat(),
            )
            for tag in dynamic_tags_list
            if tag.tag not in tags_config
        ]

        return list_of_tags + dynamic_tag_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/tag/delete",
    tags=["tag management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def delete_tag(
    data: TagDeleteRequest,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Delete a tag.

    Parameters:
    - name: str - The name of the tag to delete
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    try:
        # Get existing tags config
        tags_config = await _get_tags_config(prisma_client)

        # Check if tag exists
        if data.name not in tags_config:
            raise HTTPException(status_code=404, detail=f"Tag {data.name} not found")

        # Delete tag
        del tags_config[data.name]

        # Save updated config
        await _save_tags_config(prisma_client, tags_config)

        return {"message": f"Tag {data.name} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tag/daily/activity",
    response_model=SpendAnalyticsPaginatedResponse,
    tags=["tag management"],
    dependencies=[Depends(user_api_key_auth)],
)
async def get_tag_daily_activity(
    tags: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
):
    """
    Get daily activity for specific tags or all tags.

    Args:
        tags (Optional[str]): Comma-separated list of tags to filter by. If not provided, returns data for all tags.
        start_date (Optional[str]): Start date for the activity period (YYYY-MM-DD).
        end_date (Optional[str]): End date for the activity period (YYYY-MM-DD).
        model (Optional[str]): Filter by model name.
        api_key (Optional[str]): Filter by API key.
        page (int): Page number for pagination.
        page_size (int): Number of items per page.

    Returns:
        SpendAnalyticsPaginatedResponse: Paginated response containing daily activity data.
    """
    from litellm.proxy.proxy_server import prisma_client

    # Convert comma-separated tags string to list if provided
    tag_list = tags.split(",") if tags else None

    return await get_daily_activity(
        prisma_client=prisma_client,
        table_name="litellm_dailytagspend",
        entity_id_field="tag",
        entity_id=tag_list,
        entity_metadata_field=None,
        start_date=start_date,
        end_date=end_date,
        model=model,
        api_key=api_key,
        page=page,
        page_size=page_size,
    )

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\_spinners.py ===
"""
Spinners are from:
* cli-spinners:
    MIT License
    Copyright (c) Sindre Sorhus <sindresorhus@gmail.com> (sindresorhus.com)
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights to
    use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
    the Software, and to permit persons to whom the Software is furnished to do so,
    subject to the following conditions:
    The above copyright notice and this permission notice shall be included
    in all copies or substantial portions of the Software.
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
    INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
    PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
    FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
    IN THE SOFTWARE.
"""

SPINNERS = {
    "dots": {
        "interval": 80,
        "frames": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
    },
    "dots2": {"interval": 80, "frames": "⣾⣽⣻⢿⡿⣟⣯⣷"},
    "dots3": {
        "interval": 80,
        "frames": "⠋⠙⠚⠞⠖⠦⠴⠲⠳⠓",
    },
    "dots4": {
        "interval": 80,
        "frames": "⠄⠆⠇⠋⠙⠸⠰⠠⠰⠸⠙⠋⠇⠆",
    },
    "dots5": {
        "interval": 80,
        "frames": "⠋⠙⠚⠒⠂⠂⠒⠲⠴⠦⠖⠒⠐⠐⠒⠓⠋",
    },
    "dots6": {
        "interval": 80,
        "frames": "⠁⠉⠙⠚⠒⠂⠂⠒⠲⠴⠤⠄⠄⠤⠴⠲⠒⠂⠂⠒⠚⠙⠉⠁",
    },
    "dots7": {
        "interval": 80,
        "frames": "⠈⠉⠋⠓⠒⠐⠐⠒⠖⠦⠤⠠⠠⠤⠦⠖⠒⠐⠐⠒⠓⠋⠉⠈",
    },
    "dots8": {
        "interval": 80,
        "frames": "⠁⠁⠉⠙⠚⠒⠂⠂⠒⠲⠴⠤⠄⠄⠤⠠⠠⠤⠦⠖⠒⠐⠐⠒⠓⠋⠉⠈⠈",
    },
    "dots9": {"interval": 80, "frames": "⢹⢺⢼⣸⣇⡧⡗⡏"},
    "dots10": {"interval": 80, "frames": "⢄⢂⢁⡁⡈⡐⡠"},
    "dots11": {"interval": 100, "frames": "⠁⠂⠄⡀⢀⠠⠐⠈"},
    "dots12": {
        "interval": 80,
        "frames": [
            "⢀⠀",
            "⡀⠀",
            "⠄⠀",
            "⢂⠀",
            "⡂⠀",
            "⠅⠀",
            "⢃⠀",
            "⡃⠀",
            "⠍⠀",
            "⢋⠀",
            "⡋⠀",
            "⠍⠁",
            "⢋⠁",
            "⡋⠁",
            "⠍⠉",
            "⠋⠉",
            "⠋⠉",
            "⠉⠙",
            "⠉⠙",
            "⠉⠩",
            "⠈⢙",
            "⠈⡙",
            "⢈⠩",
            "⡀⢙",
            "⠄⡙",
            "⢂⠩",
            "⡂⢘",
            "⠅⡘",
            "⢃⠨",
            "⡃⢐",
            "⠍⡐",
            "⢋⠠",
            "⡋⢀",
            "⠍⡁",
            "⢋⠁",
            "⡋⠁",
            "⠍⠉",
            "⠋⠉",
            "⠋⠉",
            "⠉⠙",
            "⠉⠙",
            "⠉⠩",
            "⠈⢙",
            "⠈⡙",
            "⠈⠩",
            "⠀⢙",
            "⠀⡙",
            "⠀⠩",
            "⠀⢘",
            "⠀⡘",
            "⠀⠨",
            "⠀⢐",
            "⠀⡐",
            "⠀⠠",
            "⠀⢀",
            "⠀⡀",
        ],
    },
    "dots8Bit": {
        "interval": 80,
        "frames": "⠀⠁⠂⠃⠄⠅⠆⠇⡀⡁⡂⡃⡄⡅⡆⡇⠈⠉⠊⠋⠌⠍⠎⠏⡈⡉⡊⡋⡌⡍⡎⡏⠐⠑⠒⠓⠔⠕⠖⠗⡐⡑⡒⡓⡔⡕⡖⡗⠘⠙⠚⠛⠜⠝⠞⠟⡘⡙"
        "⡚⡛⡜⡝⡞⡟⠠⠡⠢⠣⠤⠥⠦⠧⡠⡡⡢⡣⡤⡥⡦⡧⠨⠩⠪⠫⠬⠭⠮⠯⡨⡩⡪⡫⡬⡭⡮⡯⠰⠱⠲⠳⠴⠵⠶⠷⡰⡱⡲⡳⡴⡵⡶⡷⠸⠹⠺⠻"
        "⠼⠽⠾⠿⡸⡹⡺⡻⡼⡽⡾⡿⢀⢁⢂⢃⢄⢅⢆⢇⣀⣁⣂⣃⣄⣅⣆⣇⢈⢉⢊⢋⢌⢍⢎⢏⣈⣉⣊⣋⣌⣍⣎⣏⢐⢑⢒⢓⢔⢕⢖⢗⣐⣑⣒⣓⣔⣕"
        "⣖⣗⢘⢙⢚⢛⢜⢝⢞⢟⣘⣙⣚⣛⣜⣝⣞⣟⢠⢡⢢⢣⢤⢥⢦⢧⣠⣡⣢⣣⣤⣥⣦⣧⢨⢩⢪⢫⢬⢭⢮⢯⣨⣩⣪⣫⣬⣭⣮⣯⢰⢱⢲⢳⢴⢵⢶⢷"
        "⣰⣱⣲⣳⣴⣵⣶⣷⢸⢹⢺⢻⢼⢽⢾⢿⣸⣹⣺⣻⣼⣽⣾⣿",
    },
    "line": {"interval": 130, "frames": ["-", "\\", "|", "/"]},
    "line2": {"interval": 100, "frames": "⠂-–—–-"},
    "pipe": {"interval": 100, "frames": "┤┘┴└├┌┬┐"},
    "simpleDots": {"interval": 400, "frames": [".  ", ".. ", "...", "   "]},
    "simpleDotsScrolling": {
        "interval": 200,
        "frames": [".  ", ".. ", "...", " ..", "  .", "   "],
    },
    "star": {"interval": 70, "frames": "✶✸✹✺✹✷"},
    "star2": {"interval": 80, "frames": "+x*"},
    "flip": {
        "interval": 70,
        "frames": "___-``'´-___",
    },
    "hamburger": {"interval": 100, "frames": "☱☲☴"},
    "growVertical": {
        "interval": 120,
        "frames": "▁▃▄▅▆▇▆▅▄▃",
    },
    "growHorizontal": {
        "interval": 120,
        "frames": "▏▎▍▌▋▊▉▊▋▌▍▎",
    },
    "balloon": {"interval": 140, "frames": " .oO@* "},
    "balloon2": {"interval": 120, "frames": ".oO°Oo."},
    "noise": {"interval": 100, "frames": "▓▒░"},
    "bounce": {"interval": 120, "frames": "⠁⠂⠄⠂"},
    "boxBounce": {"interval": 120, "frames": "▖▘▝▗"},
    "boxBounce2": {"interval": 100, "frames": "▌▀▐▄"},
    "triangle": {"interval": 50, "frames": "◢◣◤◥"},
    "arc": {"interval": 100, "frames": "◜◠◝◞◡◟"},
    "circle": {"interval": 120, "frames": "◡⊙◠"},
    "squareCorners": {"interval": 180, "frames": "◰◳◲◱"},
    "circleQuarters": {"interval": 120, "frames": "◴◷◶◵"},
    "circleHalves": {"interval": 50, "frames": "◐◓◑◒"},
    "squish": {"interval": 100, "frames": "╫╪"},
    "toggle": {"interval": 250, "frames": "⊶⊷"},
    "toggle2": {"interval": 80, "frames": "▫▪"},
    "toggle3": {"interval": 120, "frames": "□■"},
    "toggle4": {"interval": 100, "frames": "■□▪▫"},
    "toggle5": {"interval": 100, "frames": "▮▯"},
    "toggle6": {"interval": 300, "frames": "ဝ၀"},
    "toggle7": {"interval": 80, "frames": "⦾⦿"},
    "toggle8": {"interval": 100, "frames": "◍◌"},
    "toggle9": {"interval": 100, "frames": "◉◎"},
    "toggle10": {"interval": 100, "frames": "㊂㊀㊁"},
    "toggle11": {"interval": 50, "frames": "⧇⧆"},
    "toggle12": {"interval": 120, "frames": "☗☖"},
    "toggle13": {"interval": 80, "frames": "=*-"},
    "arrow": {"interval": 100, "frames": "←↖↑↗→↘↓↙"},
    "arrow2": {
        "interval": 80,
        "frames": ["⬆️ ", "↗️ ", "➡️ ", "↘️ ", "⬇️ ", "↙️ ", "⬅️ ", "↖️ "],
    },
    "arrow3": {
        "interval": 120,
        "frames": ["▹▹▹▹▹", "▸▹▹▹▹", "▹▸▹▹▹", "▹▹▸▹▹", "▹▹▹▸▹", "▹▹▹▹▸"],
    },
    "bouncingBar": {
        "interval": 80,
        "frames": [
            "[    ]",
            "[=   ]",
            "[==  ]",
            "[=== ]",
            "[ ===]",
            "[  ==]",
            "[   =]",
            "[    ]",
            "[   =]",
            "[  ==]",
            "[ ===]",
            "[====]",
            "[=== ]",
            "[==  ]",
            "[=   ]",
        ],
    },
    "bouncingBall": {
        "interval": 80,
        "frames": [
            "( ●    )",
            "(  ●   )",
            "(   ●  )",
            "(    ● )",
            "(     ●)",
            "(    ● )",
            "(   ●  )",
            "(  ●   )",
            "( ●    )",
            "(●     )",
        ],
    },
    "smiley": {"interval": 200, "frames": ["😄 ", "😝 "]},
    "monkey": {"interval": 300, "frames": ["🙈 ", "🙈 ", "🙉 ", "🙊 "]},
    "hearts": {"interval": 100, "frames": ["💛 ", "💙 ", "💜 ", "💚 ", "❤️ "]},
    "clock": {
        "interval": 100,
        "frames": [
            "🕛 ",
            "🕐 ",
            "🕑 ",
            "🕒 ",
            "🕓 ",
            "🕔 ",
            "🕕 ",
            "🕖 ",
            "🕗 ",
            "🕘 ",
            "🕙 ",
            "🕚 ",
        ],
    },
    "earth": {"interval": 180, "frames": ["🌍 ", "🌎 ", "🌏 "]},
    "material": {
        "interval": 17,
        "frames": [
            "█▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "██▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "███▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "████▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "██████▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "██████▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "███████▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "████████▁▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "██████████▁▁▁▁▁▁▁▁▁▁",
            "███████████▁▁▁▁▁▁▁▁▁",
            "█████████████▁▁▁▁▁▁▁",
            "██████████████▁▁▁▁▁▁",
            "██████████████▁▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁▁██████████████▁▁▁▁",
            "▁▁▁██████████████▁▁▁",
            "▁▁▁▁█████████████▁▁▁",
            "▁▁▁▁██████████████▁▁",
            "▁▁▁▁██████████████▁▁",
            "▁▁▁▁▁██████████████▁",
            "▁▁▁▁▁██████████████▁",
            "▁▁▁▁▁██████████████▁",
            "▁▁▁▁▁▁██████████████",
            "▁▁▁▁▁▁██████████████",
            "▁▁▁▁▁▁▁█████████████",
            "▁▁▁▁▁▁▁█████████████",
            "▁▁▁▁▁▁▁▁████████████",
            "▁▁▁▁▁▁▁▁████████████",
            "▁▁▁▁▁▁▁▁▁███████████",
            "▁▁▁▁▁▁▁▁▁███████████",
            "▁▁▁▁▁▁▁▁▁▁██████████",
            "▁▁▁▁▁▁▁▁▁▁██████████",
            "▁▁▁▁▁▁▁▁▁▁▁▁████████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁███████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁██████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█████",
            "█▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁████",
            "██▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "██▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "███▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "████▁▁▁▁▁▁▁▁▁▁▁▁▁▁██",
            "█████▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "█████▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "██████▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "████████▁▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "█████████▁▁▁▁▁▁▁▁▁▁▁",
            "███████████▁▁▁▁▁▁▁▁▁",
            "████████████▁▁▁▁▁▁▁▁",
            "████████████▁▁▁▁▁▁▁▁",
            "██████████████▁▁▁▁▁▁",
            "██████████████▁▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁██████████████▁▁▁▁▁",
            "▁▁▁█████████████▁▁▁▁",
            "▁▁▁▁▁████████████▁▁▁",
            "▁▁▁▁▁████████████▁▁▁",
            "▁▁▁▁▁▁███████████▁▁▁",
            "▁▁▁▁▁▁▁▁█████████▁▁▁",
            "▁▁▁▁▁▁▁▁█████████▁▁▁",
            "▁▁▁▁▁▁▁▁▁█████████▁▁",
            "▁▁▁▁▁▁▁▁▁█████████▁▁",
            "▁▁▁▁▁▁▁▁▁▁█████████▁",
            "▁▁▁▁▁▁▁▁▁▁▁████████▁",
            "▁▁▁▁▁▁▁▁▁▁▁████████▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁███████▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁███████▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁███████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁███████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁████",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁███",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁██",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁██",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁██",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁█",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
        ],
    },
    "moon": {
        "interval": 80,
        "frames": ["🌑 ", "🌒 ", "🌓 ", "🌔 ", "🌕 ", "🌖 ", "🌗 ", "🌘 "],
    },
    "runner": {"interval": 140, "frames": ["🚶 ", "🏃 "]},
    "pong": {
        "interval": 80,
        "frames": [
            "▐⠂       ▌",
            "▐⠈       ▌",
            "▐ ⠂      ▌",
            "▐ ⠠      ▌",
            "▐  ⡀     ▌",
            "▐  ⠠     ▌",
            "▐   ⠂    ▌",
            "▐   ⠈    ▌",
            "▐    ⠂   ▌",
            "▐    ⠠   ▌",
            "▐     ⡀  ▌",
            "▐     ⠠  ▌",
            "▐      ⠂ ▌",
            "▐      ⠈ ▌",
            "▐       ⠂▌",
            "▐       ⠠▌",
            "▐       ⡀▌",
            "▐      ⠠ ▌",
            "▐      ⠂ ▌",
            "▐     ⠈  ▌",
            "▐     ⠂  ▌",
            "▐    ⠠   ▌",
            "▐    ⡀   ▌",
            "▐   ⠠    ▌",
            "▐   ⠂    ▌",
            "▐  ⠈     ▌",
            "▐  ⠂     ▌",
            "▐ ⠠      ▌",
            "▐ ⡀      ▌",
            "▐⠠       ▌",
        ],
    },
    "shark": {
        "interval": 120,
        "frames": [
            "▐|\\____________▌",
            "▐_|\\___________▌",
            "▐__|\\__________▌",
            "▐___|\\_________▌",
            "▐____|\\________▌",
            "▐_____|\\_______▌",
            "▐______|\\______▌",
            "▐_______|\\_____▌",
            "▐________|\\____▌",
            "▐_________|\\___▌",
            "▐__________|\\__▌",
            "▐___________|\\_▌",
            "▐____________|\\▌",
            "▐____________/|▌",
            "▐___________/|_▌",
            "▐__________/|__▌",
            "▐_________/|___▌",
            "▐________/|____▌",
            "▐_______/|_____▌",
            "▐______/|______▌",
            "▐_____/|_______▌",
            "▐____/|________▌",
            "▐___/|_________▌",
            "▐__/|__________▌",
            "▐_/|___________▌",
            "▐/|____________▌",
        ],
    },
    "dqpb": {"interval": 100, "frames": "dqpb"},
    "weather": {
        "interval": 100,
        "frames": [
            "☀️ ",
            "☀️ ",
            "☀️ ",
            "🌤 ",
            "⛅️ ",
            "🌥 ",
            "☁️ ",
            "🌧 ",
            "🌨 ",
            "🌧 ",
            "🌨 ",
            "🌧 ",
            "🌨 ",
            "⛈ ",
            "🌨 ",
            "🌧 ",
            "🌨 ",
            "☁️ ",
            "🌥 ",
            "⛅️ ",
            "🌤 ",
            "☀️ ",
            "☀️ ",
        ],
    },
    "christmas": {"interval": 400, "frames": "🌲🎄"},
    "grenade": {
        "interval": 80,
        "frames": [
            "،   ",
            "′   ",
            " ´ ",
            " ‾ ",
            "  ⸌",
            "  ⸊",
            "  |",
            "  ⁎",
            "  ⁕",
            " ෴ ",
            "  ⁓",
            "   ",
            "   ",
            "   ",
        ],
    },
    "point": {"interval": 125, "frames": ["∙∙∙", "●∙∙", "∙●∙", "∙∙●", "∙∙∙"]},
    "layer": {"interval": 150, "frames": "-=≡"},
    "betaWave": {
        "interval": 80,
        "frames": [
            "ρββββββ",
            "βρβββββ",
            "ββρββββ",
            "βββρβββ",
            "ββββρββ",
            "βββββρβ",
            "ββββββρ",
        ],
    },
    "aesthetic": {
        "interval": 80,
        "frames": [
            "▰▱▱▱▱▱▱",
            "▰▰▱▱▱▱▱",
            "▰▰▰▱▱▱▱",
            "▰▰▰▰▱▱▱",
            "▰▰▰▰▰▱▱",
            "▰▰▰▰▰▰▱",
            "▰▰▰▰▰▰▰",
            "▰▱▱▱▱▱▱",
        ],
    },
}