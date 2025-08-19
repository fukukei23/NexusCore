
# === NexusCore/openenv\Lib\site-packages\typer\_typing.py ===
# Copied from pydantic 1.9.2 (the latest version to support python 3.6.)
# https://github.com/pydantic/pydantic/blob/v1.9.2/pydantic/typing.py
# mypy: ignore-errors

import sys
from collections.abc import Callable as Callable
from os import PathLike
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    ClassVar,
    Dict,
    ForwardRef,
    Generator,
    List,
    Mapping,
    NewType,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    _eval_type,
    cast,
    get_type_hints,
)
from typing import Callable as TypingCallable

from typing_extensions import Annotated, Literal

AnyCallable = TypingCallable[..., Any]
NoArgAnyCallable = TypingCallable[[], Any]

try:
    from typing import _TypingBase as typing_base  # type: ignore
except ImportError:
    from typing import _Final as typing_base  # type: ignore

try:
    from typing import GenericAlias as TypingGenericAlias  # type: ignore
except ImportError:
    # python < 3.9 does not have GenericAlias (list[int], tuple[str, ...] and so on)
    TypingGenericAlias = ()

try:
    from types import UnionType as TypesUnionType  # type: ignore
except ImportError:
    # python < 3.10 does not have UnionType (str | int, byte | bool and so on)
    TypesUnionType = ()


if sys.version_info < (3, 9):

    def evaluate_forwardref(type_: ForwardRef, globalns: Any, localns: Any) -> Any:
        return type_._evaluate(globalns, localns)

else:

    def evaluate_forwardref(type_: ForwardRef, globalns: Any, localns: Any) -> Any:
        # Even though it is the right signature for python 3.9, mypy complains with
        # `error: Too many arguments for "_evaluate" of "ForwardRef"` hence the cast...
        return cast(Any, type_)._evaluate(globalns, localns, set())


if sys.version_info < (3, 9):
    # Ensure we always get all the whole `Annotated` hint, not just the annotated type.
    # For 3.7 to 3.8, `get_type_hints` doesn't recognize `typing_extensions.Annotated`,
    # so it already returns the full annotation
    get_all_type_hints = get_type_hints

else:

    def get_all_type_hints(obj: Any, globalns: Any = None, localns: Any = None) -> Any:
        return get_type_hints(obj, globalns, localns, include_extras=True)


# Annotated[...] is implemented by returning an instance of one of these classes, depending on
# python/typing_extensions version.
AnnotatedTypeNames = {"AnnotatedMeta", "_AnnotatedAlias"}


if sys.version_info < (3, 8):

    def get_origin(t: Type[Any]) -> Optional[Type[Any]]:
        if type(t).__name__ in AnnotatedTypeNames:
            return cast(
                Type[Any], Annotated
            )  # mypy complains about _SpecialForm in py3.6
        return getattr(t, "__origin__", None)

else:
    from typing import get_origin as _typing_get_origin

    def get_origin(tp: Type[Any]) -> Optional[Type[Any]]:
        """
        We can't directly use `typing.get_origin` since we need a fallback to support
        custom generic classes like `ConstrainedList`
        It should be useless once https://github.com/cython/cython/issues/3537 is
        solved and https://github.com/samuelcolvin/pydantic/pull/1753 is merged.
        """
        if type(tp).__name__ in AnnotatedTypeNames:
            return cast(Type[Any], Annotated)  # mypy complains about _SpecialForm
        return _typing_get_origin(tp) or getattr(tp, "__origin__", None)


if sys.version_info < (3, 8):  # noqa: C901
    from typing import _GenericAlias

    def get_args(t: Type[Any]) -> Tuple[Any, ...]:
        """Compatibility version of get_args for python 3.7.

        Mostly compatible with the python 3.8 `typing` module version
        and able to handle almost all use cases.
        """
        if type(t).__name__ in AnnotatedTypeNames:
            return t.__args__ + t.__metadata__
        if isinstance(t, _GenericAlias):
            res = t.__args__
            if t.__origin__ is Callable and res and res[0] is not Ellipsis:
                res = (list(res[:-1]), res[-1])
            return res
        return getattr(t, "__args__", ())

else:
    from typing import get_args as _typing_get_args

    def _generic_get_args(tp: Type[Any]) -> Tuple[Any, ...]:
        """
        In python 3.9, `typing.Dict`, `typing.List`, ...
        do have an empty `__args__` by default (instead of the generic ~T for example).
        In order to still support `Dict` for example and consider it as `Dict[Any, Any]`,
        we retrieve the `_nparams` value that tells us how many parameters it needs.
        """
        if hasattr(tp, "_nparams"):
            return (Any,) * tp._nparams
        return ()

    def get_args(tp: Type[Any]) -> Tuple[Any, ...]:
        """Get type arguments with all substitutions performed.

        For unions, basic simplifications used by Union constructor are performed.
        Examples::
            get_args(Dict[str, int]) == (str, int)
            get_args(int) == ()
            get_args(Union[int, Union[T, int], str][int]) == (int, str)
            get_args(Union[int, Tuple[T, int]][str]) == (int, Tuple[str, int])
            get_args(Callable[[], T][int]) == ([], int)
        """
        if type(tp).__name__ in AnnotatedTypeNames:
            return tp.__args__ + tp.__metadata__
        # the fallback is needed for the same reasons as `get_origin` (see above)
        return (
            _typing_get_args(tp) or getattr(tp, "__args__", ()) or _generic_get_args(tp)
        )


if sys.version_info < (3, 9):

    def convert_generics(tp: Type[Any]) -> Type[Any]:
        """Python 3.9 and older only supports generics from `typing` module.
        They convert strings to ForwardRef automatically.

        Examples::
            typing.List['Hero'] == typing.List[ForwardRef('Hero')]
        """
        return tp

else:
    from typing import _UnionGenericAlias  # type: ignore

    from typing_extensions import _AnnotatedAlias

    def convert_generics(tp: Type[Any]) -> Type[Any]:
        """
        Recursively searches for `str` type hints and replaces them with ForwardRef.

        Examples::
            convert_generics(list['Hero']) == list[ForwardRef('Hero')]
            convert_generics(dict['Hero', 'Team']) == dict[ForwardRef('Hero'), ForwardRef('Team')]
            convert_generics(typing.Dict['Hero', 'Team']) == typing.Dict[ForwardRef('Hero'), ForwardRef('Team')]
            convert_generics(list[str | 'Hero'] | int) == list[str | ForwardRef('Hero')] | int
        """
        origin = get_origin(tp)
        if not origin or not hasattr(tp, "__args__"):
            return tp

        args = get_args(tp)

        # typing.Annotated needs special treatment
        if origin is Annotated:
            return _AnnotatedAlias(convert_generics(args[0]), args[1:])

        # recursively replace `str` instances inside of `GenericAlias` with `ForwardRef(arg)`
        converted = tuple(
            ForwardRef(arg)
            if isinstance(arg, str) and isinstance(tp, TypingGenericAlias)
            else convert_generics(arg)
            for arg in args
        )

        if converted == args:
            return tp
        elif isinstance(tp, TypingGenericAlias):
            return TypingGenericAlias(origin, converted)
        elif isinstance(tp, TypesUnionType):
            # recreate types.UnionType (PEP604, Python >= 3.10)
            return _UnionGenericAlias(origin, converted)
        else:
            try:
                setattr(tp, "__args__", converted)  # noqa: B010
            except AttributeError:
                pass
            return tp


if sys.version_info < (3, 10):

    def is_union(tp: Optional[Type[Any]]) -> bool:
        return tp is Union

    WithArgsTypes = (TypingGenericAlias,)

else:
    import types
    import typing

    def is_union(tp: Optional[Type[Any]]) -> bool:
        return tp is Union or tp is types.UnionType  # noqa: E721

    WithArgsTypes = (typing._GenericAlias, types.GenericAlias, types.UnionType)


if sys.version_info < (3, 9):
    StrPath = Union[str, PathLike]
else:
    StrPath = Union[str, PathLike]
    # TODO: Once we switch to Cython 3 to handle generics properly
    #  (https://github.com/cython/cython/issues/2753), use following lines instead
    #  of the one above
    # # os.PathLike only becomes subscriptable from Python 3.9 onwards
    # StrPath = Union[str, PathLike[str]]


if TYPE_CHECKING:
    # Only in Pydantic
    # from .fields import ModelField

    TupleGenerator = Generator[Tuple[str, Any], None, None]
    DictStrAny = Dict[str, Any]
    DictAny = Dict[Any, Any]
    SetStr = Set[str]
    ListStr = List[str]
    IntStr = Union[int, str]
    AbstractSetIntStr = AbstractSet[IntStr]
    DictIntStrAny = Dict[IntStr, Any]
    MappingIntStrAny = Mapping[IntStr, Any]
    CallableGenerator = Generator[AnyCallable, None, None]
    ReprArgs = Sequence[Tuple[Optional[str], Any]]
    AnyClassMethod = classmethod[Any]

__all__ = (
    "ForwardRef",
    "Callable",
    "AnyCallable",
    "NoArgAnyCallable",
    "NoneType",
    "is_none_type",
    "display_as_type",
    "resolve_annotations",
    "is_callable_type",
    "is_literal_type",
    "all_literal_values",
    "is_namedtuple",
    "is_typeddict",
    "is_new_type",
    "new_type_supertype",
    "is_classvar",
    "update_field_forward_refs",
    "update_model_forward_refs",
    "TupleGenerator",
    "DictStrAny",
    "DictAny",
    "SetStr",
    "ListStr",
    "IntStr",
    "AbstractSetIntStr",
    "DictIntStrAny",
    "CallableGenerator",
    "ReprArgs",
    "AnyClassMethod",
    "CallableGenerator",
    "WithArgsTypes",
    "get_args",
    "get_origin",
    "get_sub_types",
    "typing_base",
    "get_all_type_hints",
    "is_union",
    "StrPath",
)


NoneType = None.__class__


NONE_TYPES: Tuple[Any, Any, Any] = (None, NoneType, Literal[None])


if sys.version_info < (3, 8):
    # Even though this implementation is slower, we need it for python 3.7:
    # In python 3.7 "Literal" is not a builtin type and uses a different
    # mechanism.
    # for this reason `Literal[None] is Literal[None]` evaluates to `False`,
    # breaking the faster implementation used for the other python versions.

    def is_none_type(type_: Any) -> bool:
        return type_ in NONE_TYPES

elif sys.version_info[:2] == (3, 8):
    # We can use the fast implementation for 3.8 but there is a very weird bug
    # where it can fail for `Literal[None]`.
    # We just need to redefine a useless `Literal[None]` inside the function body to fix this

    def is_none_type(type_: Any) -> bool:
        Literal[None]  # fix edge case
        for none_type in NONE_TYPES:
            if type_ is none_type:
                return True
        return False

else:

    def is_none_type(type_: Any) -> bool:
        for none_type in NONE_TYPES:
            if type_ is none_type:
                return True
        return False


def display_as_type(v: Type[Any]) -> str:
    if (
        not isinstance(v, typing_base)
        and not isinstance(v, WithArgsTypes)
        and not isinstance(v, type)
    ):
        v = v.__class__

    if is_union(get_origin(v)):
        return f'Union[{", ".join(map(display_as_type, get_args(v)))}]'

    if isinstance(v, WithArgsTypes):
        # Generic alias are constructs like `list[int]`
        return str(v).replace("typing.", "")

    try:
        return v.__name__
    except AttributeError:
        # happens with typing objects
        return str(v).replace("typing.", "")


def resolve_annotations(
    raw_annotations: Dict[str, Type[Any]], module_name: Optional[str]
) -> Dict[str, Type[Any]]:
    """
    Partially taken from typing.get_type_hints.

    Resolve string or ForwardRef annotations into type objects if possible.
    """
    base_globals: Optional[Dict[str, Any]] = None
    if module_name:
        try:
            module = sys.modules[module_name]
        except KeyError:
            # happens occasionally, see https://github.com/samuelcolvin/pydantic/issues/2363
            pass
        else:
            base_globals = module.__dict__

    annotations = {}
    for name, value in raw_annotations.items():
        if isinstance(value, str):
            if (3, 10) > sys.version_info >= (3, 9, 8) or sys.version_info >= (
                3,
                10,
                1,
            ):
                value = ForwardRef(value, is_argument=False, is_class=True)
            else:
                value = ForwardRef(value, is_argument=False)
        try:
            value = _eval_type(value, base_globals, None)
        except NameError:
            # this is ok, it can be fixed with update_forward_refs
            pass
        annotations[name] = value
    return annotations


def is_callable_type(type_: Type[Any]) -> bool:
    return type_ is Callable or get_origin(type_) is Callable


def is_literal_type(type_: Type[Any]) -> bool:
    return Literal is not None and get_origin(type_) is Literal


def literal_values(type_: Type[Any]) -> Tuple[Any, ...]:
    return get_args(type_)


def all_literal_values(type_: Type[Any]) -> Tuple[Any, ...]:
    """
    This method is used to retrieve all Literal values as
    Literal can be used recursively (see https://www.python.org/dev/peps/pep-0586)
    e.g. `Literal[Literal[Literal[1, 2, 3], "foo"], 5, None]`
    """
    if not is_literal_type(type_):
        return (type_,)

    values = literal_values(type_)
    return tuple(x for value in values for x in all_literal_values(value))


def is_namedtuple(type_: Type[Any]) -> bool:
    """
    Check if a given class is a named tuple.
    It can be either a `typing.NamedTuple` or `collections.namedtuple`
    """
    from .utils import lenient_issubclass

    return lenient_issubclass(type_, tuple) and hasattr(type_, "_fields")


def is_typeddict(type_: Type[Any]) -> bool:
    """
    Check if a given class is a typed dict (from `typing` or `typing_extensions`)
    In 3.10, there will be a public method (https://docs.python.org/3.10/library/typing.html#typing.is_typeddict)
    """
    from .utils import lenient_issubclass

    return lenient_issubclass(type_, dict) and hasattr(type_, "__total__")


test_type = NewType("test_type", str)


def is_new_type(type_: Type[Any]) -> bool:
    """
    Check whether type_ was created using typing.NewType
    """
    return isinstance(type_, test_type.__class__) and hasattr(type_, "__supertype__")  # type: ignore


def new_type_supertype(type_: Type[Any]) -> Type[Any]:
    while hasattr(type_, "__supertype__"):
        type_ = type_.__supertype__
    return type_


def _check_classvar(v: Optional[Type[Any]]) -> bool:
    if v is None:
        return False

    return v.__class__ == ClassVar.__class__ and getattr(v, "_name", None) == "ClassVar"


def is_classvar(ann_type: Type[Any]) -> bool:
    if _check_classvar(ann_type) or _check_classvar(get_origin(ann_type)):
        return True

    # this is an ugly workaround for class vars that contain forward references and are therefore themselves
    # forward references, see #3679
    if ann_type.__class__ == ForwardRef and ann_type.__forward_arg__.startswith(
        "ClassVar["
    ):
        return True

    return False


# Only in Pydantic
# def update_field_forward_refs(field: "ModelField", globalns: Any, localns: Any) -> None:
#     """
#     Try to update ForwardRefs on fields based on this ModelField, globalns and localns.
#     """
#     if field.type_.__class__ == ForwardRef:
#         field.type_ = evaluate_forwardref(field.type_, globalns, localns or None)
#         field.prepare()

#     if field.sub_fields:
#         for sub_f in field.sub_fields:
#             update_field_forward_refs(sub_f, globalns=globalns, localns=localns)

#     if field.discriminator_key is not None:
#         field.prepare_discriminated_union_sub_fields()


# Only in Pydantic
# def update_model_forward_refs(
#     model: Type[Any],
#     fields: Iterable["ModelField"],
#     json_encoders: Dict[Union[Type[Any], str], AnyCallable],
#     localns: "DictStrAny",
#     exc_to_suppress: Tuple[Type[BaseException], ...] = (),
# ) -> None:
#     """
#     Try to update model fields ForwardRefs based on model and localns.
#     """
#     if model.__module__ in sys.modules:
#         globalns = sys.modules[model.__module__].__dict__.copy()
#     else:
#         globalns = {}

#     globalns.setdefault(model.__name__, model)

#     for f in fields:
#         try:
#             update_field_forward_refs(f, globalns=globalns, localns=localns)
#         except exc_to_suppress:
#             pass

#     for key in set(json_encoders.keys()):
#         if isinstance(key, str):
#             fr: ForwardRef = ForwardRef(key)
#         elif isinstance(key, ForwardRef):
#             fr = key
#         else:
#             continue

#         try:
#             new_key = evaluate_forwardref(fr, globalns, localns or None)
#         except exc_to_suppress:  # pragma: no cover
#             continue

#         json_encoders[new_key] = json_encoders.pop(key)


def get_class(type_: Type[Any]) -> Union[None, bool, Type[Any]]:
    """
    Tries to get the class of a Type[T] annotation. Returns True if Type is used
    without brackets. Otherwise returns None.
    """
    try:
        origin = get_origin(type_)
        if origin is None:  # Python 3.6
            origin = type_
        if issubclass(origin, Type):  # type: ignore
            if not get_args(type_) or not isinstance(get_args(type_)[0], type):
                return True
            return get_args(type_)[0]
    except (AttributeError, TypeError):
        pass
    return None


def get_sub_types(tp: Any) -> List[Any]:
    """
    Return all the types that are allowed by type `tp`
    `tp` can be a `Union` of allowed types or an `Annotated` type
    """
    origin = get_origin(tp)
    if origin is Annotated:
        return get_sub_types(get_args(tp)[0])
    elif is_union(origin):
        return [x for t in get_args(tp) for x in get_sub_types(t)]
    else:
        return [tp]

# === NexusCore/openenv\Lib\site-packages\trio\testing\_check_streams.py ===
# Generic stream tests
from __future__ import annotations

import random
import sys
from collections.abc import Awaitable, Callable, Generator
from contextlib import contextmanager, suppress
from typing import (
    TYPE_CHECKING,
    Generic,
    TypeVar,
)

from .. import CancelScope, _core
from .._abc import AsyncResource, HalfCloseableStream, ReceiveStream, SendStream, Stream
from .._highlevel_generic import aclose_forcefully
from ._checkpoints import assert_checkpoints

if TYPE_CHECKING:
    from types import TracebackType

    from typing_extensions import ParamSpec, TypeAlias

    ArgsT = ParamSpec("ArgsT")

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup

Res1 = TypeVar("Res1", bound=AsyncResource)
Res2 = TypeVar("Res2", bound=AsyncResource)
StreamMaker: TypeAlias = Callable[[], Awaitable[tuple[Res1, Res2]]]


class _ForceCloseBoth(Generic[Res1, Res2]):
    def __init__(self, both: tuple[Res1, Res2]) -> None:
        self._first, self._second = both

    async def __aenter__(self) -> tuple[Res1, Res2]:
        return self._first, self._second

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            await aclose_forcefully(self._first)
        finally:
            await aclose_forcefully(self._second)


# This is used in this file instead of pytest.raises in order to avoid a dependency
# on pytest, as the check_* functions are publicly exported.
@contextmanager
def _assert_raises(
    expected_exc: type[BaseException],
    wrapped: bool = False,
) -> Generator[None, None, None]:
    __tracebackhide__ = True
    try:
        yield
    except BaseExceptionGroup as exc:
        assert wrapped, "caught exceptiongroup, but expected an unwrapped exception"
        # assert in except block ignored below
        assert len(exc.exceptions) == 1  # noqa: PT017
        assert isinstance(exc.exceptions[0], expected_exc)  # noqa: PT017
    except expected_exc:
        assert not wrapped, "caught exception, but expected an exceptiongroup"
    else:
        raise AssertionError(f"expected exception: {expected_exc}")


async def check_one_way_stream(
    stream_maker: StreamMaker[SendStream, ReceiveStream],
    clogged_stream_maker: StreamMaker[SendStream, ReceiveStream] | None,
) -> None:
    """Perform a number of generic tests on a custom one-way stream
    implementation.

    Args:
      stream_maker: An async (!) function which returns a connected
          (:class:`~trio.abc.SendStream`, :class:`~trio.abc.ReceiveStream`)
          pair.
      clogged_stream_maker: Either None, or an async function similar to
          stream_maker, but with the extra property that the returned stream
          is in a state where ``send_all`` and
          ``wait_send_all_might_not_block`` will block until ``receive_some``
          has been called. This allows for more thorough testing of some edge
          cases, especially around ``wait_send_all_might_not_block``.

    Raises:
      AssertionError: if a test fails.

    """
    async with _ForceCloseBoth(await stream_maker()) as (s, r):
        assert isinstance(s, SendStream)
        assert isinstance(r, ReceiveStream)

        async def do_send_all(data: bytes | bytearray | memoryview) -> None:
            with assert_checkpoints():  # We're testing that it doesn't return anything.
                assert await s.send_all(data) is None  # type: ignore[func-returns-value]

        async def do_receive_some(max_bytes: int | None = None) -> bytes | bytearray:
            with assert_checkpoints():
                return await r.receive_some(max_bytes)

        async def checked_receive_1(expected: bytes) -> None:
            assert await do_receive_some(1) == expected

        async def do_aclose(resource: AsyncResource) -> None:
            with assert_checkpoints():
                await resource.aclose()

        # Simple sending/receiving
        async with _core.open_nursery() as nursery:
            nursery.start_soon(do_send_all, b"x")
            nursery.start_soon(checked_receive_1, b"x")

        async def send_empty_then_y() -> None:
            # Streams should tolerate sending b"" without giving it any
            # special meaning.
            await do_send_all(b"")
            await do_send_all(b"y")

        async with _core.open_nursery() as nursery:
            nursery.start_soon(send_empty_then_y)
            nursery.start_soon(checked_receive_1, b"y")

        # ---- Checking various argument types ----

        # send_all accepts bytearray and memoryview
        async with _core.open_nursery() as nursery:
            nursery.start_soon(do_send_all, bytearray(b"1"))
            nursery.start_soon(checked_receive_1, b"1")

        async with _core.open_nursery() as nursery:
            nursery.start_soon(do_send_all, memoryview(b"2"))
            nursery.start_soon(checked_receive_1, b"2")

        # max_bytes must be a positive integer
        with _assert_raises(ValueError):
            await r.receive_some(-1)
        with _assert_raises(ValueError):
            await r.receive_some(0)
        with _assert_raises(TypeError):
            await r.receive_some(1.5)  # type: ignore[arg-type]
        # it can also be missing or None
        async with _core.open_nursery() as nursery:
            nursery.start_soon(do_send_all, b"x")
            assert await do_receive_some() == b"x"
        async with _core.open_nursery() as nursery:
            nursery.start_soon(do_send_all, b"x")
            assert await do_receive_some(None) == b"x"

        with _assert_raises(_core.BusyResourceError, wrapped=True):
            async with _core.open_nursery() as nursery:
                nursery.start_soon(do_receive_some, 1)
                nursery.start_soon(do_receive_some, 1)

        # Method always has to exist, and an empty stream with a blocked
        # receive_some should *always* allow send_all. (Technically it's legal
        # for send_all to wait until receive_some is called to run, though; a
        # stream doesn't *have* to have any internal buffering. That's why we
        # start a concurrent receive_some call, then cancel it.)
        async def simple_check_wait_send_all_might_not_block(
            scope: CancelScope,
        ) -> None:
            with assert_checkpoints():
                await s.wait_send_all_might_not_block()
            scope.cancel()

        async with _core.open_nursery() as nursery:
            nursery.start_soon(
                simple_check_wait_send_all_might_not_block,
                nursery.cancel_scope,
            )
            nursery.start_soon(do_receive_some, 1)

        # closing the r side leads to BrokenResourceError on the s side
        # (eventually)
        async def expect_broken_stream_on_send() -> None:
            with _assert_raises(_core.BrokenResourceError):
                while True:
                    await do_send_all(b"x" * 100)

        async with _core.open_nursery() as nursery:
            nursery.start_soon(expect_broken_stream_on_send)
            nursery.start_soon(do_aclose, r)

        # once detected, the stream stays broken
        with _assert_raises(_core.BrokenResourceError):
            await do_send_all(b"x" * 100)

        # r closed -> ClosedResourceError on the receive side
        with _assert_raises(_core.ClosedResourceError):
            await do_receive_some(4096)

        # we can close the same stream repeatedly, it's fine
        await do_aclose(r)
        await do_aclose(r)

        # closing the sender side
        await do_aclose(s)

        # now trying to send raises ClosedResourceError
        with _assert_raises(_core.ClosedResourceError):
            await do_send_all(b"x" * 100)

        # even if it's an empty send
        with _assert_raises(_core.ClosedResourceError):
            await do_send_all(b"")

        # ditto for wait_send_all_might_not_block
        with _assert_raises(_core.ClosedResourceError):
            with assert_checkpoints():
                await s.wait_send_all_might_not_block()

        # and again, repeated closing is fine
        await do_aclose(s)
        await do_aclose(s)

    async with _ForceCloseBoth(await stream_maker()) as (s, r):
        # if send-then-graceful-close, receiver gets data then b""
        async def send_then_close() -> None:
            await do_send_all(b"y")
            await do_aclose(s)

        async def receive_send_then_close() -> None:
            # We want to make sure that if the sender closes the stream before
            # we read anything, then we still get all the data. But some
            # streams might block on the do_send_all call. So we let the
            # sender get as far as it can, then we receive.
            await _core.wait_all_tasks_blocked()
            await checked_receive_1(b"y")
            await checked_receive_1(b"")
            await do_aclose(r)

        async with _core.open_nursery() as nursery:
            nursery.start_soon(send_then_close)
            nursery.start_soon(receive_send_then_close)

    async with _ForceCloseBoth(await stream_maker()) as (s, r):
        await aclose_forcefully(r)

        with _assert_raises(_core.BrokenResourceError):
            while True:
                await do_send_all(b"x" * 100)

        with _assert_raises(_core.ClosedResourceError):
            await do_receive_some(4096)

    async with _ForceCloseBoth(await stream_maker()) as (s, r):
        await aclose_forcefully(s)

        with _assert_raises(_core.ClosedResourceError):
            await do_send_all(b"123")

        # after the sender does a forceful close, the receiver might either
        # get BrokenResourceError or a clean b""; either is OK. Not OK would be
        # if it freezes, or returns data.
        with suppress(_core.BrokenResourceError):
            await checked_receive_1(b"")

    # cancelled aclose still closes
    async with _ForceCloseBoth(await stream_maker()) as (s, r):
        with _core.CancelScope() as scope:
            scope.cancel()
            await r.aclose()

        with _core.CancelScope() as scope:
            scope.cancel()
            await s.aclose()

        with _assert_raises(_core.ClosedResourceError):
            await do_send_all(b"123")

        with _assert_raises(_core.ClosedResourceError):
            await do_receive_some(4096)

    # Check that we can still gracefully close a stream after an operation has
    # been cancelled. This can be challenging if cancellation can leave the
    # stream internals in an inconsistent state, e.g. for
    # SSLStream. Unfortunately this test isn't very thorough; the really
    # challenging case for something like SSLStream is it gets cancelled
    # *while* it's sending data on the underlying, not before. But testing
    # that requires some special-case handling of the particular stream setup;
    # we can't do it here. Maybe we could do a bit better with
    #     https://github.com/python-trio/trio/issues/77
    async with _ForceCloseBoth(await stream_maker()) as (s, r):

        async def expect_cancelled(
            afn: Callable[ArgsT, Awaitable[object]],
            *args: ArgsT.args,
            **kwargs: ArgsT.kwargs,
        ) -> None:
            with _assert_raises(_core.Cancelled):
                await afn(*args, **kwargs)

        with _core.CancelScope() as scope:
            scope.cancel()
            async with _core.open_nursery() as nursery:
                nursery.start_soon(expect_cancelled, do_send_all, b"x")
                nursery.start_soon(expect_cancelled, do_receive_some, 1)

        async with _core.open_nursery() as nursery:
            nursery.start_soon(do_aclose, s)
            nursery.start_soon(do_aclose, r)

    # Check that if a task is blocked in receive_some, then closing the
    # receive stream causes it to wake up.
    async with _ForceCloseBoth(await stream_maker()) as (s, r):

        async def receive_expecting_closed() -> None:
            with _assert_raises(_core.ClosedResourceError):
                await r.receive_some(10)

        async with _core.open_nursery() as nursery:
            nursery.start_soon(receive_expecting_closed)
            await _core.wait_all_tasks_blocked()
            await aclose_forcefully(r)

    # check wait_send_all_might_not_block, if we can
    if clogged_stream_maker is not None:
        async with _ForceCloseBoth(await clogged_stream_maker()) as (s, r):
            record: list[str] = []

            async def waiter(cancel_scope: CancelScope) -> None:
                record.append("waiter sleeping")
                with assert_checkpoints():
                    await s.wait_send_all_might_not_block()
                record.append("waiter wokeup")
                cancel_scope.cancel()

            async def receiver() -> None:
                # give wait_send_all_might_not_block a chance to block
                await _core.wait_all_tasks_blocked()
                record.append("receiver starting")
                while True:
                    await r.receive_some(16834)

            async with _core.open_nursery() as nursery:
                nursery.start_soon(waiter, nursery.cancel_scope)
                await _core.wait_all_tasks_blocked()
                nursery.start_soon(receiver)

            assert record == [
                "waiter sleeping",
                "receiver starting",
                "waiter wokeup",
            ]

        async with _ForceCloseBoth(await clogged_stream_maker()) as (s, r):
            # simultaneous wait_send_all_might_not_block fails
            with _assert_raises(_core.BusyResourceError, wrapped=True):
                async with _core.open_nursery() as nursery:
                    nursery.start_soon(s.wait_send_all_might_not_block)
                    nursery.start_soon(s.wait_send_all_might_not_block)

            # and simultaneous send_all and wait_send_all_might_not_block (NB
            # this test might destroy the stream b/c we end up cancelling
            # send_all and e.g. SSLStream can't handle that, so we have to
            # recreate afterwards)
            with _assert_raises(_core.BusyResourceError, wrapped=True):
                async with _core.open_nursery() as nursery:
                    nursery.start_soon(s.wait_send_all_might_not_block)
                    nursery.start_soon(s.send_all, b"123")

        async with _ForceCloseBoth(await clogged_stream_maker()) as (s, r):
            # send_all and send_all blocked simultaneously should also raise
            # (but again this might destroy the stream)
            with _assert_raises(_core.BusyResourceError, wrapped=True):
                async with _core.open_nursery() as nursery:
                    nursery.start_soon(s.send_all, b"123")
                    nursery.start_soon(s.send_all, b"123")

        # closing the receiver causes wait_send_all_might_not_block to return,
        # with or without an exception
        async with _ForceCloseBoth(await clogged_stream_maker()) as (s, r):

            async def sender() -> None:
                try:
                    with assert_checkpoints():
                        await s.wait_send_all_might_not_block()
                except _core.BrokenResourceError:  # pragma: no cover
                    pass

            async def receiver() -> None:
                await _core.wait_all_tasks_blocked()
                await aclose_forcefully(r)

            async with _core.open_nursery() as nursery:
                nursery.start_soon(sender)
                nursery.start_soon(receiver)

        # and again with the call starting after the close
        async with _ForceCloseBoth(await clogged_stream_maker()) as (s, r):
            await aclose_forcefully(r)
            try:
                with assert_checkpoints():
                    await s.wait_send_all_might_not_block()
            except _core.BrokenResourceError:  # pragma: no cover
                pass

        # Check that if a task is blocked in a send-side method, then closing
        # the send stream causes it to wake up.
        async def close_soon(s: SendStream) -> None:
            await _core.wait_all_tasks_blocked()
            await aclose_forcefully(s)

        async with _ForceCloseBoth(await clogged_stream_maker()) as (s, r):
            async with _core.open_nursery() as nursery:
                nursery.start_soon(close_soon, s)
                with _assert_raises(_core.ClosedResourceError):
                    await s.send_all(b"xyzzy")

        async with _ForceCloseBoth(await clogged_stream_maker()) as (s, r):
            async with _core.open_nursery() as nursery:
                nursery.start_soon(close_soon, s)
                with _assert_raises(_core.ClosedResourceError):
                    await s.wait_send_all_might_not_block()


async def check_two_way_stream(
    stream_maker: StreamMaker[Stream, Stream],
    clogged_stream_maker: StreamMaker[Stream, Stream] | None,
) -> None:
    """Perform a number of generic tests on a custom two-way stream
    implementation.

    This is similar to :func:`check_one_way_stream`, except that the maker
    functions are expected to return objects implementing the
    :class:`~trio.abc.Stream` interface.

    This function tests a *superset* of what :func:`check_one_way_stream`
    checks – if you call this, then you don't need to also call
    :func:`check_one_way_stream`.

    """
    await check_one_way_stream(stream_maker, clogged_stream_maker)

    async def flipped_stream_maker() -> tuple[Stream, Stream]:
        return (await stream_maker())[::-1]

    flipped_clogged_stream_maker: Callable[[], Awaitable[tuple[Stream, Stream]]] | None

    if clogged_stream_maker is not None:

        async def flipped_clogged_stream_maker() -> tuple[Stream, Stream]:
            return (await clogged_stream_maker())[::-1]

    else:
        flipped_clogged_stream_maker = None
    await check_one_way_stream(flipped_stream_maker, flipped_clogged_stream_maker)

    async with _ForceCloseBoth(await stream_maker()) as (s1, s2):
        assert isinstance(s1, Stream)
        assert isinstance(s2, Stream)

        # Duplex can be a bit tricky, might as well check it as well
        DUPLEX_TEST_SIZE = 2**20
        CHUNK_SIZE_MAX = 2**14

        r = random.Random(0)
        i = r.getrandbits(8 * DUPLEX_TEST_SIZE)
        test_data = i.to_bytes(DUPLEX_TEST_SIZE, "little")

        async def sender(
            s: Stream,
            data: bytes | bytearray | memoryview,
            seed: int,
        ) -> None:
            r = random.Random(seed)
            m = memoryview(data)
            while m:
                chunk_size = r.randint(1, CHUNK_SIZE_MAX)
                await s.send_all(m[:chunk_size])
                m = m[chunk_size:]

        async def receiver(s: Stream, data: bytes | bytearray, seed: int) -> None:
            r = random.Random(seed)
            got = bytearray()
            while len(got) < len(data):
                chunk = await s.receive_some(r.randint(1, CHUNK_SIZE_MAX))
                assert chunk
                got += chunk
            assert got == data

        async with _core.open_nursery() as nursery:
            nursery.start_soon(sender, s1, test_data, 0)
            nursery.start_soon(sender, s2, test_data[::-1], 1)
            nursery.start_soon(receiver, s1, test_data[::-1], 2)
            nursery.start_soon(receiver, s2, test_data, 3)

        async def expect_receive_some_empty() -> None:
            assert await s2.receive_some(10) == b""
            await s2.aclose()

        async with _core.open_nursery() as nursery:
            nursery.start_soon(expect_receive_some_empty)
            nursery.start_soon(s1.aclose)


async def check_half_closeable_stream(
    stream_maker: StreamMaker[HalfCloseableStream, HalfCloseableStream],
    clogged_stream_maker: StreamMaker[HalfCloseableStream, HalfCloseableStream] | None,
) -> None:
    """Perform a number of generic tests on a custom half-closeable stream
    implementation.

    This is similar to :func:`check_two_way_stream`, except that the maker
    functions are expected to return objects that implement the
    :class:`~trio.abc.HalfCloseableStream` interface.

    This function tests a *superset* of what :func:`check_two_way_stream`
    checks – if you call this, then you don't need to also call
    :func:`check_two_way_stream`.

    """
    await check_two_way_stream(stream_maker, clogged_stream_maker)

    async with _ForceCloseBoth(await stream_maker()) as (s1, s2):
        assert isinstance(s1, HalfCloseableStream)
        assert isinstance(s2, HalfCloseableStream)

        async def send_x_then_eof(s: HalfCloseableStream) -> None:
            await s.send_all(b"x")
            with assert_checkpoints():
                await s.send_eof()

        async def expect_x_then_eof(r: HalfCloseableStream) -> None:
            await _core.wait_all_tasks_blocked()
            assert await r.receive_some(10) == b"x"
            assert await r.receive_some(10) == b""

        async with _core.open_nursery() as nursery:
            nursery.start_soon(send_x_then_eof, s1)
            nursery.start_soon(expect_x_then_eof, s2)

        # now sending is disallowed
        with _assert_raises(_core.ClosedResourceError):
            await s1.send_all(b"y")

        # but we can do send_eof again
        with assert_checkpoints():
            await s1.send_eof()

        # and we can still send stuff back the other way
        async with _core.open_nursery() as nursery:
            nursery.start_soon(send_x_then_eof, s2)
            nursery.start_soon(expect_x_then_eof, s1)

    if clogged_stream_maker is not None:
        async with _ForceCloseBoth(await clogged_stream_maker()) as (s1, s2):
            # send_all and send_eof simultaneously is not ok
            with _assert_raises(_core.BusyResourceError, wrapped=True):
                async with _core.open_nursery() as nursery:
                    nursery.start_soon(s1.send_all, b"x")
                    await _core.wait_all_tasks_blocked()
                    nursery.start_soon(s1.send_eof)

        async with _ForceCloseBoth(await clogged_stream_maker()) as (s1, s2):
            # wait_send_all_might_not_block and send_eof simultaneously is not
            # ok either
            with _assert_raises(_core.BusyResourceError, wrapped=True):
                async with _core.open_nursery() as nursery:
                    nursery.start_soon(s1.wait_send_all_might_not_block)
                    await _core.wait_all_tasks_blocked()
                    nursery.start_soon(s1.send_eof)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\truststore\_windows.py ===
import contextlib
import ssl
import typing
from ctypes import WinDLL  # type: ignore
from ctypes import WinError  # type: ignore
from ctypes import (
    POINTER,
    Structure,
    c_char_p,
    c_ulong,
    c_void_p,
    c_wchar_p,
    cast,
    create_unicode_buffer,
    pointer,
    sizeof,
)
from ctypes.wintypes import (
    BOOL,
    DWORD,
    HANDLE,
    LONG,
    LPCSTR,
    LPCVOID,
    LPCWSTR,
    LPFILETIME,
    LPSTR,
    LPWSTR,
)
from typing import TYPE_CHECKING, Any

from ._ssl_constants import _set_ssl_context_verify_mode

HCERTCHAINENGINE = HANDLE
HCERTSTORE = HANDLE
HCRYPTPROV_LEGACY = HANDLE


class CERT_CONTEXT(Structure):
    _fields_ = (
        ("dwCertEncodingType", DWORD),
        ("pbCertEncoded", c_void_p),
        ("cbCertEncoded", DWORD),
        ("pCertInfo", c_void_p),
        ("hCertStore", HCERTSTORE),
    )


PCERT_CONTEXT = POINTER(CERT_CONTEXT)
PCCERT_CONTEXT = POINTER(PCERT_CONTEXT)


class CERT_ENHKEY_USAGE(Structure):
    _fields_ = (
        ("cUsageIdentifier", DWORD),
        ("rgpszUsageIdentifier", POINTER(LPSTR)),
    )


PCERT_ENHKEY_USAGE = POINTER(CERT_ENHKEY_USAGE)


class CERT_USAGE_MATCH(Structure):
    _fields_ = (
        ("dwType", DWORD),
        ("Usage", CERT_ENHKEY_USAGE),
    )


class CERT_CHAIN_PARA(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("RequestedUsage", CERT_USAGE_MATCH),
        ("RequestedIssuancePolicy", CERT_USAGE_MATCH),
        ("dwUrlRetrievalTimeout", DWORD),
        ("fCheckRevocationFreshnessTime", BOOL),
        ("dwRevocationFreshnessTime", DWORD),
        ("pftCacheResync", LPFILETIME),
        ("pStrongSignPara", c_void_p),
        ("dwStrongSignFlags", DWORD),
    )


if TYPE_CHECKING:
    PCERT_CHAIN_PARA = pointer[CERT_CHAIN_PARA]  # type: ignore[misc]
else:
    PCERT_CHAIN_PARA = POINTER(CERT_CHAIN_PARA)


class CERT_TRUST_STATUS(Structure):
    _fields_ = (
        ("dwErrorStatus", DWORD),
        ("dwInfoStatus", DWORD),
    )


class CERT_CHAIN_ELEMENT(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("pCertContext", PCERT_CONTEXT),
        ("TrustStatus", CERT_TRUST_STATUS),
        ("pRevocationInfo", c_void_p),
        ("pIssuanceUsage", PCERT_ENHKEY_USAGE),
        ("pApplicationUsage", PCERT_ENHKEY_USAGE),
        ("pwszExtendedErrorInfo", LPCWSTR),
    )


PCERT_CHAIN_ELEMENT = POINTER(CERT_CHAIN_ELEMENT)


class CERT_SIMPLE_CHAIN(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("TrustStatus", CERT_TRUST_STATUS),
        ("cElement", DWORD),
        ("rgpElement", POINTER(PCERT_CHAIN_ELEMENT)),
        ("pTrustListInfo", c_void_p),
        ("fHasRevocationFreshnessTime", BOOL),
        ("dwRevocationFreshnessTime", DWORD),
    )


PCERT_SIMPLE_CHAIN = POINTER(CERT_SIMPLE_CHAIN)


class CERT_CHAIN_CONTEXT(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("TrustStatus", CERT_TRUST_STATUS),
        ("cChain", DWORD),
        ("rgpChain", POINTER(PCERT_SIMPLE_CHAIN)),
        ("cLowerQualityChainContext", DWORD),
        ("rgpLowerQualityChainContext", c_void_p),
        ("fHasRevocationFreshnessTime", BOOL),
        ("dwRevocationFreshnessTime", DWORD),
    )


PCERT_CHAIN_CONTEXT = POINTER(CERT_CHAIN_CONTEXT)
PCCERT_CHAIN_CONTEXT = POINTER(PCERT_CHAIN_CONTEXT)


class SSL_EXTRA_CERT_CHAIN_POLICY_PARA(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("dwAuthType", DWORD),
        ("fdwChecks", DWORD),
        ("pwszServerName", LPCWSTR),
    )


class CERT_CHAIN_POLICY_PARA(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("dwFlags", DWORD),
        ("pvExtraPolicyPara", c_void_p),
    )


PCERT_CHAIN_POLICY_PARA = POINTER(CERT_CHAIN_POLICY_PARA)


class CERT_CHAIN_POLICY_STATUS(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("dwError", DWORD),
        ("lChainIndex", LONG),
        ("lElementIndex", LONG),
        ("pvExtraPolicyStatus", c_void_p),
    )


PCERT_CHAIN_POLICY_STATUS = POINTER(CERT_CHAIN_POLICY_STATUS)


class CERT_CHAIN_ENGINE_CONFIG(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("hRestrictedRoot", HCERTSTORE),
        ("hRestrictedTrust", HCERTSTORE),
        ("hRestrictedOther", HCERTSTORE),
        ("cAdditionalStore", DWORD),
        ("rghAdditionalStore", c_void_p),
        ("dwFlags", DWORD),
        ("dwUrlRetrievalTimeout", DWORD),
        ("MaximumCachedCertificates", DWORD),
        ("CycleDetectionModulus", DWORD),
        ("hExclusiveRoot", HCERTSTORE),
        ("hExclusiveTrustedPeople", HCERTSTORE),
        ("dwExclusiveFlags", DWORD),
    )


PCERT_CHAIN_ENGINE_CONFIG = POINTER(CERT_CHAIN_ENGINE_CONFIG)
PHCERTCHAINENGINE = POINTER(HCERTCHAINENGINE)

X509_ASN_ENCODING = 0x00000001
PKCS_7_ASN_ENCODING = 0x00010000
CERT_STORE_PROV_MEMORY = b"Memory"
CERT_STORE_ADD_USE_EXISTING = 2
USAGE_MATCH_TYPE_OR = 1
OID_PKIX_KP_SERVER_AUTH = c_char_p(b"1.3.6.1.5.5.7.3.1")
CERT_CHAIN_REVOCATION_CHECK_END_CERT = 0x10000000
CERT_CHAIN_REVOCATION_CHECK_CHAIN = 0x20000000
CERT_CHAIN_POLICY_IGNORE_ALL_NOT_TIME_VALID_FLAGS = 0x00000007
CERT_CHAIN_POLICY_IGNORE_INVALID_BASIC_CONSTRAINTS_FLAG = 0x00000008
CERT_CHAIN_POLICY_ALLOW_UNKNOWN_CA_FLAG = 0x00000010
CERT_CHAIN_POLICY_IGNORE_INVALID_NAME_FLAG = 0x00000040
CERT_CHAIN_POLICY_IGNORE_WRONG_USAGE_FLAG = 0x00000020
CERT_CHAIN_POLICY_IGNORE_INVALID_POLICY_FLAG = 0x00000080
CERT_CHAIN_POLICY_IGNORE_ALL_REV_UNKNOWN_FLAGS = 0x00000F00
CERT_CHAIN_POLICY_ALLOW_TESTROOT_FLAG = 0x00008000
CERT_CHAIN_POLICY_TRUST_TESTROOT_FLAG = 0x00004000
SECURITY_FLAG_IGNORE_CERT_CN_INVALID = 0x00001000
AUTHTYPE_SERVER = 2
CERT_CHAIN_POLICY_SSL = 4
FORMAT_MESSAGE_FROM_SYSTEM = 0x00001000
FORMAT_MESSAGE_IGNORE_INSERTS = 0x00000200

# Flags to set for SSLContext.verify_mode=CERT_NONE
CERT_CHAIN_POLICY_VERIFY_MODE_NONE_FLAGS = (
    CERT_CHAIN_POLICY_IGNORE_ALL_NOT_TIME_VALID_FLAGS
    | CERT_CHAIN_POLICY_IGNORE_INVALID_BASIC_CONSTRAINTS_FLAG
    | CERT_CHAIN_POLICY_ALLOW_UNKNOWN_CA_FLAG
    | CERT_CHAIN_POLICY_IGNORE_INVALID_NAME_FLAG
    | CERT_CHAIN_POLICY_IGNORE_WRONG_USAGE_FLAG
    | CERT_CHAIN_POLICY_IGNORE_INVALID_POLICY_FLAG
    | CERT_CHAIN_POLICY_IGNORE_ALL_REV_UNKNOWN_FLAGS
    | CERT_CHAIN_POLICY_ALLOW_TESTROOT_FLAG
    | CERT_CHAIN_POLICY_TRUST_TESTROOT_FLAG
)

wincrypt = WinDLL("crypt32.dll")
kernel32 = WinDLL("kernel32.dll")


def _handle_win_error(result: bool, _: Any, args: Any) -> Any:
    if not result:
        # Note, actually raises OSError after calling GetLastError and FormatMessage
        raise WinError()
    return args


CertCreateCertificateChainEngine = wincrypt.CertCreateCertificateChainEngine
CertCreateCertificateChainEngine.argtypes = (
    PCERT_CHAIN_ENGINE_CONFIG,
    PHCERTCHAINENGINE,
)
CertCreateCertificateChainEngine.errcheck = _handle_win_error

CertOpenStore = wincrypt.CertOpenStore
CertOpenStore.argtypes = (LPCSTR, DWORD, HCRYPTPROV_LEGACY, DWORD, c_void_p)
CertOpenStore.restype = HCERTSTORE
CertOpenStore.errcheck = _handle_win_error

CertAddEncodedCertificateToStore = wincrypt.CertAddEncodedCertificateToStore
CertAddEncodedCertificateToStore.argtypes = (
    HCERTSTORE,
    DWORD,
    c_char_p,
    DWORD,
    DWORD,
    PCCERT_CONTEXT,
)
CertAddEncodedCertificateToStore.restype = BOOL

CertCreateCertificateContext = wincrypt.CertCreateCertificateContext
CertCreateCertificateContext.argtypes = (DWORD, c_char_p, DWORD)
CertCreateCertificateContext.restype = PCERT_CONTEXT
CertCreateCertificateContext.errcheck = _handle_win_error

CertGetCertificateChain = wincrypt.CertGetCertificateChain
CertGetCertificateChain.argtypes = (
    HCERTCHAINENGINE,
    PCERT_CONTEXT,
    LPFILETIME,
    HCERTSTORE,
    PCERT_CHAIN_PARA,
    DWORD,
    c_void_p,
    PCCERT_CHAIN_CONTEXT,
)
CertGetCertificateChain.restype = BOOL
CertGetCertificateChain.errcheck = _handle_win_error

CertVerifyCertificateChainPolicy = wincrypt.CertVerifyCertificateChainPolicy
CertVerifyCertificateChainPolicy.argtypes = (
    c_ulong,
    PCERT_CHAIN_CONTEXT,
    PCERT_CHAIN_POLICY_PARA,
    PCERT_CHAIN_POLICY_STATUS,
)
CertVerifyCertificateChainPolicy.restype = BOOL

CertCloseStore = wincrypt.CertCloseStore
CertCloseStore.argtypes = (HCERTSTORE, DWORD)
CertCloseStore.restype = BOOL
CertCloseStore.errcheck = _handle_win_error

CertFreeCertificateChain = wincrypt.CertFreeCertificateChain
CertFreeCertificateChain.argtypes = (PCERT_CHAIN_CONTEXT,)

CertFreeCertificateContext = wincrypt.CertFreeCertificateContext
CertFreeCertificateContext.argtypes = (PCERT_CONTEXT,)

CertFreeCertificateChainEngine = wincrypt.CertFreeCertificateChainEngine
CertFreeCertificateChainEngine.argtypes = (HCERTCHAINENGINE,)

FormatMessageW = kernel32.FormatMessageW
FormatMessageW.argtypes = (
    DWORD,
    LPCVOID,
    DWORD,
    DWORD,
    LPWSTR,
    DWORD,
    c_void_p,
)
FormatMessageW.restype = DWORD


def _verify_peercerts_impl(
    ssl_context: ssl.SSLContext,
    cert_chain: list[bytes],
    server_hostname: str | None = None,
) -> None:
    """Verify the cert_chain from the server using Windows APIs."""

    # If the peer didn't send any certificates then
    # we can't do verification. Raise an error.
    if not cert_chain:
        raise ssl.SSLCertVerificationError("Peer sent no certificates to verify")

    pCertContext = None
    hIntermediateCertStore = CertOpenStore(CERT_STORE_PROV_MEMORY, 0, None, 0, None)
    try:
        # Add intermediate certs to an in-memory cert store
        for cert_bytes in cert_chain[1:]:
            CertAddEncodedCertificateToStore(
                hIntermediateCertStore,
                X509_ASN_ENCODING | PKCS_7_ASN_ENCODING,
                cert_bytes,
                len(cert_bytes),
                CERT_STORE_ADD_USE_EXISTING,
                None,
            )

        # Cert context for leaf cert
        leaf_cert = cert_chain[0]
        pCertContext = CertCreateCertificateContext(
            X509_ASN_ENCODING | PKCS_7_ASN_ENCODING, leaf_cert, len(leaf_cert)
        )

        # Chain params to match certs for serverAuth extended usage
        cert_enhkey_usage = CERT_ENHKEY_USAGE()
        cert_enhkey_usage.cUsageIdentifier = 1
        cert_enhkey_usage.rgpszUsageIdentifier = (c_char_p * 1)(OID_PKIX_KP_SERVER_AUTH)
        cert_usage_match = CERT_USAGE_MATCH()
        cert_usage_match.Usage = cert_enhkey_usage
        chain_params = CERT_CHAIN_PARA()
        chain_params.RequestedUsage = cert_usage_match
        chain_params.cbSize = sizeof(chain_params)
        pChainPara = pointer(chain_params)

        if ssl_context.verify_flags & ssl.VERIFY_CRL_CHECK_CHAIN:
            chain_flags = CERT_CHAIN_REVOCATION_CHECK_CHAIN
        elif ssl_context.verify_flags & ssl.VERIFY_CRL_CHECK_LEAF:
            chain_flags = CERT_CHAIN_REVOCATION_CHECK_END_CERT
        else:
            chain_flags = 0

        try:
            # First attempt to verify using the default Windows system trust roots
            # (default chain engine).
            _get_and_verify_cert_chain(
                ssl_context,
                None,
                hIntermediateCertStore,
                pCertContext,
                pChainPara,
                server_hostname,
                chain_flags=chain_flags,
            )
        except ssl.SSLCertVerificationError as e:
            # If that fails but custom CA certs have been added
            # to the SSLContext using load_verify_locations,
            # try verifying using a custom chain engine
            # that trusts the custom CA certs.
            custom_ca_certs: list[bytes] | None = ssl_context.get_ca_certs(
                binary_form=True
            )
            if custom_ca_certs:
                try:
                    _verify_using_custom_ca_certs(
                        ssl_context,
                        custom_ca_certs,
                        hIntermediateCertStore,
                        pCertContext,
                        pChainPara,
                        server_hostname,
                        chain_flags=chain_flags,
                    )
                # Raise the original error, not the new error.
                except ssl.SSLCertVerificationError:
                    raise e from None
            else:
                raise
    finally:
        CertCloseStore(hIntermediateCertStore, 0)
        if pCertContext:
            CertFreeCertificateContext(pCertContext)


def _get_and_verify_cert_chain(
    ssl_context: ssl.SSLContext,
    hChainEngine: HCERTCHAINENGINE | None,
    hIntermediateCertStore: HCERTSTORE,
    pPeerCertContext: c_void_p,
    pChainPara: PCERT_CHAIN_PARA,  # type: ignore[valid-type]
    server_hostname: str | None,
    chain_flags: int,
) -> None:
    ppChainContext = None
    try:
        # Get cert chain
        ppChainContext = pointer(PCERT_CHAIN_CONTEXT())
        CertGetCertificateChain(
            hChainEngine,  # chain engine
            pPeerCertContext,  # leaf cert context
            None,  # current system time
            hIntermediateCertStore,  # additional in-memory cert store
            pChainPara,  # chain-building parameters
            chain_flags,
            None,  # reserved
            ppChainContext,  # the resulting chain context
        )
        pChainContext = ppChainContext.contents

        # Verify cert chain
        ssl_extra_cert_chain_policy_para = SSL_EXTRA_CERT_CHAIN_POLICY_PARA()
        ssl_extra_cert_chain_policy_para.cbSize = sizeof(
            ssl_extra_cert_chain_policy_para
        )
        ssl_extra_cert_chain_policy_para.dwAuthType = AUTHTYPE_SERVER
        ssl_extra_cert_chain_policy_para.fdwChecks = 0
        if ssl_context.check_hostname is False:
            ssl_extra_cert_chain_policy_para.fdwChecks = (
                SECURITY_FLAG_IGNORE_CERT_CN_INVALID
            )
        if server_hostname:
            ssl_extra_cert_chain_policy_para.pwszServerName = c_wchar_p(server_hostname)

        chain_policy = CERT_CHAIN_POLICY_PARA()
        chain_policy.pvExtraPolicyPara = cast(
            pointer(ssl_extra_cert_chain_policy_para), c_void_p
        )
        if ssl_context.verify_mode == ssl.CERT_NONE:
            chain_policy.dwFlags |= CERT_CHAIN_POLICY_VERIFY_MODE_NONE_FLAGS
        chain_policy.cbSize = sizeof(chain_policy)

        pPolicyPara = pointer(chain_policy)
        policy_status = CERT_CHAIN_POLICY_STATUS()
        policy_status.cbSize = sizeof(policy_status)
        pPolicyStatus = pointer(policy_status)
        CertVerifyCertificateChainPolicy(
            CERT_CHAIN_POLICY_SSL,
            pChainContext,
            pPolicyPara,
            pPolicyStatus,
        )

        # Check status
        error_code = policy_status.dwError
        if error_code:
            # Try getting a human readable message for an error code.
            error_message_buf = create_unicode_buffer(1024)
            error_message_chars = FormatMessageW(
                FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
                None,
                error_code,
                0,
                error_message_buf,
                sizeof(error_message_buf),
                None,
            )

            # See if we received a message for the error,
            # otherwise we use a generic error with the
            # error code and hope that it's search-able.
            if error_message_chars <= 0:
                error_message = f"Certificate chain policy error {error_code:#x} [{policy_status.lElementIndex}]"
            else:
                error_message = error_message_buf.value.strip()

            err = ssl.SSLCertVerificationError(error_message)
            err.verify_message = error_message
            err.verify_code = error_code
            raise err from None
    finally:
        if ppChainContext:
            CertFreeCertificateChain(ppChainContext.contents)


def _verify_using_custom_ca_certs(
    ssl_context: ssl.SSLContext,
    custom_ca_certs: list[bytes],
    hIntermediateCertStore: HCERTSTORE,
    pPeerCertContext: c_void_p,
    pChainPara: PCERT_CHAIN_PARA,  # type: ignore[valid-type]
    server_hostname: str | None,
    chain_flags: int,
) -> None:
    hChainEngine = None
    hRootCertStore = CertOpenStore(CERT_STORE_PROV_MEMORY, 0, None, 0, None)
    try:
        # Add custom CA certs to an in-memory cert store
        for cert_bytes in custom_ca_certs:
            CertAddEncodedCertificateToStore(
                hRootCertStore,
                X509_ASN_ENCODING | PKCS_7_ASN_ENCODING,
                cert_bytes,
                len(cert_bytes),
                CERT_STORE_ADD_USE_EXISTING,
                None,
            )

        # Create a custom cert chain engine which exclusively trusts
        # certs from our hRootCertStore
        cert_chain_engine_config = CERT_CHAIN_ENGINE_CONFIG()
        cert_chain_engine_config.cbSize = sizeof(cert_chain_engine_config)
        cert_chain_engine_config.hExclusiveRoot = hRootCertStore
        pConfig = pointer(cert_chain_engine_config)
        phChainEngine = pointer(HCERTCHAINENGINE())
        CertCreateCertificateChainEngine(
            pConfig,
            phChainEngine,
        )
        hChainEngine = phChainEngine.contents

        # Get and verify a cert chain using the custom chain engine
        _get_and_verify_cert_chain(
            ssl_context,
            hChainEngine,
            hIntermediateCertStore,
            pPeerCertContext,
            pChainPara,
            server_hostname,
            chain_flags,
        )
    finally:
        if hChainEngine:
            CertFreeCertificateChainEngine(hChainEngine)
        CertCloseStore(hRootCertStore, 0)


@contextlib.contextmanager
def _configure_context(ctx: ssl.SSLContext) -> typing.Iterator[None]:
    check_hostname = ctx.check_hostname
    verify_mode = ctx.verify_mode
    ctx.check_hostname = False
    _set_ssl_context_verify_mode(ctx, ssl.CERT_NONE)
    try:
        yield
    finally:
        ctx.check_hostname = check_hostname
        _set_ssl_context_verify_mode(ctx, verify_mode)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\model_service\transports\grpc_asyncio.py ===
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
from typing import Awaitable, Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1, grpc_helpers_async, operations_v1
from google.api_core import retry_async as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1beta.types import tuned_model as gag_tuned_model
from google.ai.generativelanguage_v1beta.types import model, model_service
from google.ai.generativelanguage_v1beta.types import tuned_model

from .base import DEFAULT_CLIENT_INFO, ModelServiceTransport
from .grpc import ModelServiceGrpcTransport


class ModelServiceGrpcAsyncIOTransport(ModelServiceTransport):
    """gRPC AsyncIO backend transport for ModelService.

    Provides methods for getting metadata information about
    Generative Models.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _grpc_channel: aio.Channel
    _stubs: Dict[str, Callable] = {}

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> aio.Channel:
        """Create and return a gRPC AsyncIO channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            aio.Channel: A gRPC AsyncIO channel object.
        """

        return grpc_helpers_async.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[aio.Channel, Callable[..., aio.Channel]]] = None,
        api_mtls_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        ssl_channel_credentials: Optional[grpc.ChannelCredentials] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'generativelanguage.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
                This argument is ignored if a ``channel`` instance is provided.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if a ``channel`` instance is provided.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            channel (Optional[Union[aio.Channel, Callable[..., aio.Channel]]]):
                A ``Channel`` instance through which to make calls, or a Callable
                that constructs and returns one. If set to None, ``self.create_channel``
                is used to create the channel. If a Callable is given, it will be called
                with the same arguments as used in ``self.create_channel``.
            api_mtls_endpoint (Optional[str]): Deprecated. The mutual TLS endpoint.
                If provided, it overrides the ``host`` argument and tries to create
                a mutual TLS channel with client SSL credentials from
                ``client_cert_source`` or application default SSL credentials.
            client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]):
                Deprecated. A callback to provide client SSL certificate bytes and
                private key bytes, both in PEM format. It is ignored if
                ``api_mtls_endpoint`` is None.
            ssl_channel_credentials (grpc.ChannelCredentials): SSL credentials
                for the grpc channel. It is ignored if a ``channel`` instance is provided.
            client_cert_source_for_mtls (Optional[Callable[[], Tuple[bytes, bytes]]]):
                A callback to provide client certificate bytes and private key bytes,
                both in PEM format. It is used to configure a mutual TLS channel. It is
                ignored if a ``channel`` instance or ``ssl_channel_credentials`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}
        self._operations_client: Optional[operations_v1.OperationsAsyncClient] = None

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, aio.Channel):
            # Ignore credentials if a channel was passed.
            credentials = False
            # If a channel was explicitly provided, set it.
            self._grpc_channel = channel
            self._ssl_channel_credentials = None
        else:
            if api_mtls_endpoint:
                host = api_mtls_endpoint

                # Create SSL credentials with client_cert_source or application
                # default SSL credentials.
                if client_cert_source:
                    cert, key = client_cert_source()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )
                else:
                    self._ssl_channel_credentials = SslCredentials().ssl_credentials

            else:
                if client_cert_source_for_mtls and not ssl_channel_credentials:
                    cert, key = client_cert_source_for_mtls()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )

        # The base transport sets the host, credentials and scopes
        super().__init__(
            host=host,
            credentials=credentials,
            credentials_file=credentials_file,
            scopes=scopes,
            quota_project_id=quota_project_id,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )

        if not self._grpc_channel:
            # initialize with the provided callable or the default channel
            channel_init = channel or type(self).create_channel
            self._grpc_channel = channel_init(
                self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                # Set ``credentials_file`` to ``None`` here as
                # the credentials that we saved earlier should be used.
                credentials_file=None,
                scopes=self._scopes,
                ssl_credentials=self._ssl_channel_credentials,
                quota_project_id=quota_project_id,
                options=[
                    ("grpc.max_send_message_length", -1),
                    ("grpc.max_receive_message_length", -1),
                ],
            )

        # Wrap messages. This must be done after self._grpc_channel exists
        self._prep_wrapped_messages(client_info)

    @property
    def grpc_channel(self) -> aio.Channel:
        """Create the channel designed to connect to this service.

        This property caches on the instance; repeated calls return
        the same channel.
        """
        # Return the channel from cache.
        return self._grpc_channel

    @property
    def operations_client(self) -> operations_v1.OperationsAsyncClient:
        """Create the client designed to process long-running operations.

        This property caches on the instance; repeated calls return the same
        client.
        """
        # Quick check: Only create a new client if we do not already have one.
        if self._operations_client is None:
            self._operations_client = operations_v1.OperationsAsyncClient(
                self.grpc_channel
            )

        # Return the client from cache.
        return self._operations_client

    @property
    def get_model(
        self,
    ) -> Callable[[model_service.GetModelRequest], Awaitable[model.Model]]:
        r"""Return a callable for the get model method over gRPC.

        Gets information about a specific Model.

        Returns:
            Callable[[~.GetModelRequest],
                    Awaitable[~.Model]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_model" not in self._stubs:
            self._stubs["get_model"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.ModelService/GetModel",
                request_serializer=model_service.GetModelRequest.serialize,
                response_deserializer=model.Model.deserialize,
            )
        return self._stubs["get_model"]

    @property
    def list_models(
        self,
    ) -> Callable[
        [model_service.ListModelsRequest], Awaitable[model_service.ListModelsResponse]
    ]:
        r"""Return a callable for the list models method over gRPC.

        Lists models available through the API.

        Returns:
            Callable[[~.ListModelsRequest],
                    Awaitable[~.ListModelsResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_models" not in self._stubs:
            self._stubs["list_models"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.ModelService/ListModels",
                request_serializer=model_service.ListModelsRequest.serialize,
                response_deserializer=model_service.ListModelsResponse.deserialize,
            )
        return self._stubs["list_models"]

    @property
    def get_tuned_model(
        self,
    ) -> Callable[
        [model_service.GetTunedModelRequest], Awaitable[tuned_model.TunedModel]
    ]:
        r"""Return a callable for the get tuned model method over gRPC.

        Gets information about a specific TunedModel.

        Returns:
            Callable[[~.GetTunedModelRequest],
                    Awaitable[~.TunedModel]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_tuned_model" not in self._stubs:
            self._stubs["get_tuned_model"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.ModelService/GetTunedModel",
                request_serializer=model_service.GetTunedModelRequest.serialize,
                response_deserializer=tuned_model.TunedModel.deserialize,
            )
        return self._stubs["get_tuned_model"]

    @property
    def list_tuned_models(
        self,
    ) -> Callable[
        [model_service.ListTunedModelsRequest],
        Awaitable[model_service.ListTunedModelsResponse],
    ]:
        r"""Return a callable for the list tuned models method over gRPC.

        Lists tuned models owned by the user.

        Returns:
            Callable[[~.ListTunedModelsRequest],
                    Awaitable[~.ListTunedModelsResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_tuned_models" not in self._stubs:
            self._stubs["list_tuned_models"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.ModelService/ListTunedModels",
                request_serializer=model_service.ListTunedModelsRequest.serialize,
                response_deserializer=model_service.ListTunedModelsResponse.deserialize,
            )
        return self._stubs["list_tuned_models"]

    @property
    def create_tuned_model(
        self,
    ) -> Callable[
        [model_service.CreateTunedModelRequest], Awaitable[operations_pb2.Operation]
    ]:
        r"""Return a callable for the create tuned model method over gRPC.

        Creates a tuned model. Intermediate tuning progress (if any) is
        accessed through the [google.longrunning.Operations] service.

        Status and results can be accessed through the Operations
        service. Example: GET
        /v1/tunedModels/az2mb0bpw6i/operations/000-111-222

        Returns:
            Callable[[~.CreateTunedModelRequest],
                    Awaitable[~.Operation]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_tuned_model" not in self._stubs:
            self._stubs["create_tuned_model"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.ModelService/CreateTunedModel",
                request_serializer=model_service.CreateTunedModelRequest.serialize,
                response_deserializer=operations_pb2.Operation.FromString,
            )
        return self._stubs["create_tuned_model"]

    @property
    def update_tuned_model(
        self,
    ) -> Callable[
        [model_service.UpdateTunedModelRequest], Awaitable[gag_tuned_model.TunedModel]
    ]:
        r"""Return a callable for the update tuned model method over gRPC.

        Updates a tuned model.

        Returns:
            Callable[[~.UpdateTunedModelRequest],
                    Awaitable[~.TunedModel]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_tuned_model" not in self._stubs:
            self._stubs["update_tuned_model"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.ModelService/UpdateTunedModel",
                request_serializer=model_service.UpdateTunedModelRequest.serialize,
                response_deserializer=gag_tuned_model.TunedModel.deserialize,
            )
        return self._stubs["update_tuned_model"]

    @property
    def delete_tuned_model(
        self,
    ) -> Callable[[model_service.DeleteTunedModelRequest], Awaitable[empty_pb2.Empty]]:
        r"""Return a callable for the delete tuned model method over gRPC.

        Deletes a tuned model.

        Returns:
            Callable[[~.DeleteTunedModelRequest],
                    Awaitable[~.Empty]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_tuned_model" not in self._stubs:
            self._stubs["delete_tuned_model"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.ModelService/DeleteTunedModel",
                request_serializer=model_service.DeleteTunedModelRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_tuned_model"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.get_model: gapic_v1.method_async.wrap_method(
                self.get_model,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.list_models: gapic_v1.method_async.wrap_method(
                self.list_models,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.get_tuned_model: gapic_v1.method_async.wrap_method(
                self.get_tuned_model,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.list_tuned_models: gapic_v1.method_async.wrap_method(
                self.list_tuned_models,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.create_tuned_model: gapic_v1.method_async.wrap_method(
                self.create_tuned_model,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.update_tuned_model: gapic_v1.method_async.wrap_method(
                self.update_tuned_model,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.delete_tuned_model: gapic_v1.method_async.wrap_method(
                self.delete_tuned_model,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
        }

    def close(self):
        return self.grpc_channel.close()


__all__ = ("ModelServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\google\protobuf\internal\well_known_types.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Contains well known classes.

This files defines well known classes which need extra maintenance including:
  - Any
  - Duration
  - FieldMask
  - Struct
  - Timestamp
"""

__author__ = 'jieluo@google.com (Jie Luo)'

import calendar
import collections.abc
import datetime

from google.protobuf.internal import field_mask

FieldMask = field_mask.FieldMask

_TIMESTAMPFOMAT = '%Y-%m-%dT%H:%M:%S'
_NANOS_PER_SECOND = 1000000000
_NANOS_PER_MILLISECOND = 1000000
_NANOS_PER_MICROSECOND = 1000
_MILLIS_PER_SECOND = 1000
_MICROS_PER_SECOND = 1000000
_SECONDS_PER_DAY = 24 * 3600
_DURATION_SECONDS_MAX = 315576000000

_EPOCH_DATETIME_NAIVE = datetime.datetime(1970, 1, 1, tzinfo=None)
_EPOCH_DATETIME_AWARE = _EPOCH_DATETIME_NAIVE.replace(
    tzinfo=datetime.timezone.utc
)


class Any(object):
  """Class for Any Message type."""

  __slots__ = ()

  def Pack(self, msg, type_url_prefix='type.googleapis.com/',
           deterministic=None):
    """Packs the specified message into current Any message."""
    if len(type_url_prefix) < 1 or type_url_prefix[-1] != '/':
      self.type_url = '%s/%s' % (type_url_prefix, msg.DESCRIPTOR.full_name)
    else:
      self.type_url = '%s%s' % (type_url_prefix, msg.DESCRIPTOR.full_name)
    self.value = msg.SerializeToString(deterministic=deterministic)

  def Unpack(self, msg):
    """Unpacks the current Any message into specified message."""
    descriptor = msg.DESCRIPTOR
    if not self.Is(descriptor):
      return False
    msg.ParseFromString(self.value)
    return True

  def TypeName(self):
    """Returns the protobuf type name of the inner message."""
    # Only last part is to be used: b/25630112
    return self.type_url.split('/')[-1]

  def Is(self, descriptor):
    """Checks if this Any represents the given protobuf type."""
    return '/' in self.type_url and self.TypeName() == descriptor.full_name


class Timestamp(object):
  """Class for Timestamp message type."""

  __slots__ = ()

  def ToJsonString(self):
    """Converts Timestamp to RFC 3339 date string format.

    Returns:
      A string converted from timestamp. The string is always Z-normalized
      and uses 3, 6 or 9 fractional digits as required to represent the
      exact time. Example of the return format: '1972-01-01T10:00:20.021Z'
    """
    nanos = self.nanos % _NANOS_PER_SECOND
    total_sec = self.seconds + (self.nanos - nanos) // _NANOS_PER_SECOND
    seconds = total_sec % _SECONDS_PER_DAY
    days = (total_sec - seconds) // _SECONDS_PER_DAY
    dt = datetime.datetime(1970, 1, 1) + datetime.timedelta(days, seconds)

    result = dt.isoformat()
    if (nanos % 1e9) == 0:
      # If there are 0 fractional digits, the fractional
      # point '.' should be omitted when serializing.
      return result + 'Z'
    if (nanos % 1e6) == 0:
      # Serialize 3 fractional digits.
      return result + '.%03dZ' % (nanos / 1e6)
    if (nanos % 1e3) == 0:
      # Serialize 6 fractional digits.
      return result + '.%06dZ' % (nanos / 1e3)
    # Serialize 9 fractional digits.
    return result + '.%09dZ' % nanos

  def FromJsonString(self, value):
    """Parse a RFC 3339 date string format to Timestamp.

    Args:
      value: A date string. Any fractional digits (or none) and any offset are
          accepted as long as they fit into nano-seconds precision.
          Example of accepted format: '1972-01-01T10:00:20.021-05:00'

    Raises:
      ValueError: On parsing problems.
    """
    if not isinstance(value, str):
      raise ValueError('Timestamp JSON value not a string: {!r}'.format(value))
    timezone_offset = value.find('Z')
    if timezone_offset == -1:
      timezone_offset = value.find('+')
    if timezone_offset == -1:
      timezone_offset = value.rfind('-')
    if timezone_offset == -1:
      raise ValueError(
          'Failed to parse timestamp: missing valid timezone offset.')
    time_value = value[0:timezone_offset]
    # Parse datetime and nanos.
    point_position = time_value.find('.')
    if point_position == -1:
      second_value = time_value
      nano_value = ''
    else:
      second_value = time_value[:point_position]
      nano_value = time_value[point_position + 1:]
    if 't' in second_value:
      raise ValueError(
          'time data \'{0}\' does not match format \'%Y-%m-%dT%H:%M:%S\', '
          'lowercase \'t\' is not accepted'.format(second_value))
    date_object = datetime.datetime.strptime(second_value, _TIMESTAMPFOMAT)
    td = date_object - datetime.datetime(1970, 1, 1)
    seconds = td.seconds + td.days * _SECONDS_PER_DAY
    if len(nano_value) > 9:
      raise ValueError(
          'Failed to parse Timestamp: nanos {0} more than '
          '9 fractional digits.'.format(nano_value))
    if nano_value:
      nanos = round(float('0.' + nano_value) * 1e9)
    else:
      nanos = 0
    # Parse timezone offsets.
    if value[timezone_offset] == 'Z':
      if len(value) != timezone_offset + 1:
        raise ValueError('Failed to parse timestamp: invalid trailing'
                         ' data {0}.'.format(value))
    else:
      timezone = value[timezone_offset:]
      pos = timezone.find(':')
      if pos == -1:
        raise ValueError(
            'Invalid timezone offset value: {0}.'.format(timezone))
      if timezone[0] == '+':
        seconds -= (int(timezone[1:pos])*60+int(timezone[pos+1:]))*60
      else:
        seconds += (int(timezone[1:pos])*60+int(timezone[pos+1:]))*60
    # Set seconds and nanos
    self.seconds = int(seconds)
    self.nanos = int(nanos)

  def GetCurrentTime(self):
    """Get the current UTC into Timestamp."""
    self.FromDatetime(datetime.datetime.utcnow())

  def ToNanoseconds(self):
    """Converts Timestamp to nanoseconds since epoch."""
    return self.seconds * _NANOS_PER_SECOND + self.nanos

  def ToMicroseconds(self):
    """Converts Timestamp to microseconds since epoch."""
    return (self.seconds * _MICROS_PER_SECOND +
            self.nanos // _NANOS_PER_MICROSECOND)

  def ToMilliseconds(self):
    """Converts Timestamp to milliseconds since epoch."""
    return (self.seconds * _MILLIS_PER_SECOND +
            self.nanos // _NANOS_PER_MILLISECOND)

  def ToSeconds(self):
    """Converts Timestamp to seconds since epoch."""
    return self.seconds

  def FromNanoseconds(self, nanos):
    """Converts nanoseconds since epoch to Timestamp."""
    self.seconds = nanos // _NANOS_PER_SECOND
    self.nanos = nanos % _NANOS_PER_SECOND

  def FromMicroseconds(self, micros):
    """Converts microseconds since epoch to Timestamp."""
    self.seconds = micros // _MICROS_PER_SECOND
    self.nanos = (micros % _MICROS_PER_SECOND) * _NANOS_PER_MICROSECOND

  def FromMilliseconds(self, millis):
    """Converts milliseconds since epoch to Timestamp."""
    self.seconds = millis // _MILLIS_PER_SECOND
    self.nanos = (millis % _MILLIS_PER_SECOND) * _NANOS_PER_MILLISECOND

  def FromSeconds(self, seconds):
    """Converts seconds since epoch to Timestamp."""
    self.seconds = seconds
    self.nanos = 0

  def ToDatetime(self, tzinfo=None):
    """Converts Timestamp to a datetime.

    Args:
      tzinfo: A datetime.tzinfo subclass; defaults to None.

    Returns:
      If tzinfo is None, returns a timezone-naive UTC datetime (with no timezone
      information, i.e. not aware that it's UTC).

      Otherwise, returns a timezone-aware datetime in the input timezone.
    """
    # Using datetime.fromtimestamp for this would avoid constructing an extra
    # timedelta object and possibly an extra datetime. Unfortuantely, that has
    # the disadvantage of not handling the full precision (on all platforms, see
    # https://github.com/python/cpython/issues/109849) or full range (on some
    # platforms, see https://github.com/python/cpython/issues/110042) of
    # datetime.
    delta = datetime.timedelta(
        seconds=self.seconds,
        microseconds=_RoundTowardZero(self.nanos, _NANOS_PER_MICROSECOND),
    )
    if tzinfo is None:
      return _EPOCH_DATETIME_NAIVE + delta
    else:
      # Note the tz conversion has to come after the timedelta arithmetic.
      return (_EPOCH_DATETIME_AWARE + delta).astimezone(tzinfo)

  def FromDatetime(self, dt):
    """Converts datetime to Timestamp.

    Args:
      dt: A datetime. If it's timezone-naive, it's assumed to be in UTC.
    """
    # Using this guide: http://wiki.python.org/moin/WorkingWithTime
    # And this conversion guide: http://docs.python.org/library/time.html

    # Turn the date parameter into a tuple (struct_time) that can then be
    # manipulated into a long value of seconds.  During the conversion from
    # struct_time to long, the source date in UTC, and so it follows that the
    # correct transformation is calendar.timegm()
    self.seconds = calendar.timegm(dt.utctimetuple())
    self.nanos = dt.microsecond * _NANOS_PER_MICROSECOND


class Duration(object):
  """Class for Duration message type."""

  __slots__ = ()

  def ToJsonString(self):
    """Converts Duration to string format.

    Returns:
      A string converted from self. The string format will contains
      3, 6, or 9 fractional digits depending on the precision required to
      represent the exact Duration value. For example: "1s", "1.010s",
      "1.000000100s", "-3.100s"
    """
    _CheckDurationValid(self.seconds, self.nanos)
    if self.seconds < 0 or self.nanos < 0:
      result = '-'
      seconds = - self.seconds + int((0 - self.nanos) // 1e9)
      nanos = (0 - self.nanos) % 1e9
    else:
      result = ''
      seconds = self.seconds + int(self.nanos // 1e9)
      nanos = self.nanos % 1e9
    result += '%d' % seconds
    if (nanos % 1e9) == 0:
      # If there are 0 fractional digits, the fractional
      # point '.' should be omitted when serializing.
      return result + 's'
    if (nanos % 1e6) == 0:
      # Serialize 3 fractional digits.
      return result + '.%03ds' % (nanos / 1e6)
    if (nanos % 1e3) == 0:
      # Serialize 6 fractional digits.
      return result + '.%06ds' % (nanos / 1e3)
    # Serialize 9 fractional digits.
    return result + '.%09ds' % nanos

  def FromJsonString(self, value):
    """Converts a string to Duration.

    Args:
      value: A string to be converted. The string must end with 's'. Any
          fractional digits (or none) are accepted as long as they fit into
          precision. For example: "1s", "1.01s", "1.0000001s", "-3.100s

    Raises:
      ValueError: On parsing problems.
    """
    if not isinstance(value, str):
      raise ValueError('Duration JSON value not a string: {!r}'.format(value))
    if len(value) < 1 or value[-1] != 's':
      raise ValueError(
          'Duration must end with letter "s": {0}.'.format(value))
    try:
      pos = value.find('.')
      if pos == -1:
        seconds = int(value[:-1])
        nanos = 0
      else:
        seconds = int(value[:pos])
        if value[0] == '-':
          nanos = int(round(float('-0{0}'.format(value[pos: -1])) *1e9))
        else:
          nanos = int(round(float('0{0}'.format(value[pos: -1])) *1e9))
      _CheckDurationValid(seconds, nanos)
      self.seconds = seconds
      self.nanos = nanos
    except ValueError as e:
      raise ValueError(
          'Couldn\'t parse duration: {0} : {1}.'.format(value, e))

  def ToNanoseconds(self):
    """Converts a Duration to nanoseconds."""
    return self.seconds * _NANOS_PER_SECOND + self.nanos

  def ToMicroseconds(self):
    """Converts a Duration to microseconds."""
    micros = _RoundTowardZero(self.nanos, _NANOS_PER_MICROSECOND)
    return self.seconds * _MICROS_PER_SECOND + micros

  def ToMilliseconds(self):
    """Converts a Duration to milliseconds."""
    millis = _RoundTowardZero(self.nanos, _NANOS_PER_MILLISECOND)
    return self.seconds * _MILLIS_PER_SECOND + millis

  def ToSeconds(self):
    """Converts a Duration to seconds."""
    return self.seconds

  def FromNanoseconds(self, nanos):
    """Converts nanoseconds to Duration."""
    self._NormalizeDuration(nanos // _NANOS_PER_SECOND,
                            nanos % _NANOS_PER_SECOND)

  def FromMicroseconds(self, micros):
    """Converts microseconds to Duration."""
    self._NormalizeDuration(
        micros // _MICROS_PER_SECOND,
        (micros % _MICROS_PER_SECOND) * _NANOS_PER_MICROSECOND)

  def FromMilliseconds(self, millis):
    """Converts milliseconds to Duration."""
    self._NormalizeDuration(
        millis // _MILLIS_PER_SECOND,
        (millis % _MILLIS_PER_SECOND) * _NANOS_PER_MILLISECOND)

  def FromSeconds(self, seconds):
    """Converts seconds to Duration."""
    self.seconds = seconds
    self.nanos = 0

  def ToTimedelta(self):
    """Converts Duration to timedelta."""
    return datetime.timedelta(
        seconds=self.seconds, microseconds=_RoundTowardZero(
            self.nanos, _NANOS_PER_MICROSECOND))

  def FromTimedelta(self, td):
    """Converts timedelta to Duration."""
    self._NormalizeDuration(td.seconds + td.days * _SECONDS_PER_DAY,
                            td.microseconds * _NANOS_PER_MICROSECOND)

  def _NormalizeDuration(self, seconds, nanos):
    """Set Duration by seconds and nanos."""
    # Force nanos to be negative if the duration is negative.
    if seconds < 0 and nanos > 0:
      seconds += 1
      nanos -= _NANOS_PER_SECOND
    self.seconds = seconds
    self.nanos = nanos


def _CheckDurationValid(seconds, nanos):
  if seconds < -_DURATION_SECONDS_MAX or seconds > _DURATION_SECONDS_MAX:
    raise ValueError(
        'Duration is not valid: Seconds {0} must be in range '
        '[-315576000000, 315576000000].'.format(seconds))
  if nanos <= -_NANOS_PER_SECOND or nanos >= _NANOS_PER_SECOND:
    raise ValueError(
        'Duration is not valid: Nanos {0} must be in range '
        '[-999999999, 999999999].'.format(nanos))
  if (nanos < 0 and seconds > 0) or (nanos > 0 and seconds < 0):
    raise ValueError(
        'Duration is not valid: Sign mismatch.')


def _RoundTowardZero(value, divider):
  """Truncates the remainder part after division."""
  # For some languages, the sign of the remainder is implementation
  # dependent if any of the operands is negative. Here we enforce
  # "rounded toward zero" semantics. For example, for (-5) / 2 an
  # implementation may give -3 as the result with the remainder being
  # 1. This function ensures we always return -2 (closer to zero).
  result = value // divider
  remainder = value % divider
  if result < 0 and remainder > 0:
    return result + 1
  else:
    return result


def _SetStructValue(struct_value, value):
  if value is None:
    struct_value.null_value = 0
  elif isinstance(value, bool):
    # Note: this check must come before the number check because in Python
    # True and False are also considered numbers.
    struct_value.bool_value = value
  elif isinstance(value, str):
    struct_value.string_value = value
  elif isinstance(value, (int, float)):
    struct_value.number_value = value
  elif isinstance(value, (dict, Struct)):
    struct_value.struct_value.Clear()
    struct_value.struct_value.update(value)
  elif isinstance(value, (list, tuple, ListValue)):
    struct_value.list_value.Clear()
    struct_value.list_value.extend(value)
  else:
    raise ValueError('Unexpected type')


def _GetStructValue(struct_value):
  which = struct_value.WhichOneof('kind')
  if which == 'struct_value':
    return struct_value.struct_value
  elif which == 'null_value':
    return None
  elif which == 'number_value':
    return struct_value.number_value
  elif which == 'string_value':
    return struct_value.string_value
  elif which == 'bool_value':
    return struct_value.bool_value
  elif which == 'list_value':
    return struct_value.list_value
  elif which is None:
    raise ValueError('Value not set')


class Struct(object):
  """Class for Struct message type."""

  __slots__ = ()

  def __getitem__(self, key):
    return _GetStructValue(self.fields[key])

  def __contains__(self, item):
    return item in self.fields

  def __setitem__(self, key, value):
    _SetStructValue(self.fields[key], value)

  def __delitem__(self, key):
    del self.fields[key]

  def __len__(self):
    return len(self.fields)

  def __iter__(self):
    return iter(self.fields)

  def keys(self):  # pylint: disable=invalid-name
    return self.fields.keys()

  def values(self):  # pylint: disable=invalid-name
    return [self[key] for key in self]

  def items(self):  # pylint: disable=invalid-name
    return [(key, self[key]) for key in self]

  def get_or_create_list(self, key):
    """Returns a list for this key, creating if it didn't exist already."""
    if not self.fields[key].HasField('list_value'):
      # Clear will mark list_value modified which will indeed create a list.
      self.fields[key].list_value.Clear()
    return self.fields[key].list_value

  def get_or_create_struct(self, key):
    """Returns a struct for this key, creating if it didn't exist already."""
    if not self.fields[key].HasField('struct_value'):
      # Clear will mark struct_value modified which will indeed create a struct.
      self.fields[key].struct_value.Clear()
    return self.fields[key].struct_value

  def update(self, dictionary):  # pylint: disable=invalid-name
    for key, value in dictionary.items():
      _SetStructValue(self.fields[key], value)

collections.abc.MutableMapping.register(Struct)


class ListValue(object):
  """Class for ListValue message type."""

  __slots__ = ()

  def __len__(self):
    return len(self.values)

  def append(self, value):
    _SetStructValue(self.values.add(), value)

  def extend(self, elem_seq):
    for value in elem_seq:
      self.append(value)

  def __getitem__(self, index):
    """Retrieves item by the specified index."""
    return _GetStructValue(self.values.__getitem__(index))

  def __setitem__(self, index, value):
    _SetStructValue(self.values.__getitem__(index), value)

  def __delitem__(self, key):
    del self.values[key]

  def items(self):
    for i in range(len(self)):
      yield self[i]

  def add_struct(self):
    """Appends and returns a struct value as the next value in the list."""
    struct_value = self.values.add().struct_value
    # Clear will mark struct_value modified which will indeed create a struct.
    struct_value.Clear()
    return struct_value

  def add_list(self):
    """Appends and returns a list value as the next value in the list."""
    list_value = self.values.add().list_value
    # Clear will mark list_value modified which will indeed create a list.
    list_value.Clear()
    return list_value

collections.abc.MutableSequence.register(ListValue)


# LINT.IfChange(wktbases)
WKTBASES = {
    'google.protobuf.Any': Any,
    'google.protobuf.Duration': Duration,
    'google.protobuf.FieldMask': FieldMask,
    'google.protobuf.ListValue': ListValue,
    'google.protobuf.Struct': Struct,
    'google.protobuf.Timestamp': Timestamp,
}
# LINT.ThenChange(//depot/google.protobuf/compiler/python/pyi_generator.cc:wktbases)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\truststore\_windows.py ===
import contextlib
import ssl
import typing
from ctypes import WinDLL  # type: ignore
from ctypes import WinError  # type: ignore
from ctypes import (
    POINTER,
    Structure,
    c_char_p,
    c_ulong,
    c_void_p,
    c_wchar_p,
    cast,
    create_unicode_buffer,
    pointer,
    sizeof,
)
from ctypes.wintypes import (
    BOOL,
    DWORD,
    HANDLE,
    LONG,
    LPCSTR,
    LPCVOID,
    LPCWSTR,
    LPFILETIME,
    LPSTR,
    LPWSTR,
)
from typing import TYPE_CHECKING, Any

from ._ssl_constants import _set_ssl_context_verify_mode

HCERTCHAINENGINE = HANDLE
HCERTSTORE = HANDLE
HCRYPTPROV_LEGACY = HANDLE


class CERT_CONTEXT(Structure):
    _fields_ = (
        ("dwCertEncodingType", DWORD),
        ("pbCertEncoded", c_void_p),
        ("cbCertEncoded", DWORD),
        ("pCertInfo", c_void_p),
        ("hCertStore", HCERTSTORE),
    )


PCERT_CONTEXT = POINTER(CERT_CONTEXT)
PCCERT_CONTEXT = POINTER(PCERT_CONTEXT)


class CERT_ENHKEY_USAGE(Structure):
    _fields_ = (
        ("cUsageIdentifier", DWORD),
        ("rgpszUsageIdentifier", POINTER(LPSTR)),
    )


PCERT_ENHKEY_USAGE = POINTER(CERT_ENHKEY_USAGE)


class CERT_USAGE_MATCH(Structure):
    _fields_ = (
        ("dwType", DWORD),
        ("Usage", CERT_ENHKEY_USAGE),
    )


class CERT_CHAIN_PARA(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("RequestedUsage", CERT_USAGE_MATCH),
        ("RequestedIssuancePolicy", CERT_USAGE_MATCH),
        ("dwUrlRetrievalTimeout", DWORD),
        ("fCheckRevocationFreshnessTime", BOOL),
        ("dwRevocationFreshnessTime", DWORD),
        ("pftCacheResync", LPFILETIME),
        ("pStrongSignPara", c_void_p),
        ("dwStrongSignFlags", DWORD),
    )


if TYPE_CHECKING:
    PCERT_CHAIN_PARA = pointer[CERT_CHAIN_PARA]  # type: ignore[misc]
else:
    PCERT_CHAIN_PARA = POINTER(CERT_CHAIN_PARA)


class CERT_TRUST_STATUS(Structure):
    _fields_ = (
        ("dwErrorStatus", DWORD),
        ("dwInfoStatus", DWORD),
    )


class CERT_CHAIN_ELEMENT(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("pCertContext", PCERT_CONTEXT),
        ("TrustStatus", CERT_TRUST_STATUS),
        ("pRevocationInfo", c_void_p),
        ("pIssuanceUsage", PCERT_ENHKEY_USAGE),
        ("pApplicationUsage", PCERT_ENHKEY_USAGE),
        ("pwszExtendedErrorInfo", LPCWSTR),
    )


PCERT_CHAIN_ELEMENT = POINTER(CERT_CHAIN_ELEMENT)


class CERT_SIMPLE_CHAIN(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("TrustStatus", CERT_TRUST_STATUS),
        ("cElement", DWORD),
        ("rgpElement", POINTER(PCERT_CHAIN_ELEMENT)),
        ("pTrustListInfo", c_void_p),
        ("fHasRevocationFreshnessTime", BOOL),
        ("dwRevocationFreshnessTime", DWORD),
    )


PCERT_SIMPLE_CHAIN = POINTER(CERT_SIMPLE_CHAIN)


class CERT_CHAIN_CONTEXT(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("TrustStatus", CERT_TRUST_STATUS),
        ("cChain", DWORD),
        ("rgpChain", POINTER(PCERT_SIMPLE_CHAIN)),
        ("cLowerQualityChainContext", DWORD),
        ("rgpLowerQualityChainContext", c_void_p),
        ("fHasRevocationFreshnessTime", BOOL),
        ("dwRevocationFreshnessTime", DWORD),
    )


PCERT_CHAIN_CONTEXT = POINTER(CERT_CHAIN_CONTEXT)
PCCERT_CHAIN_CONTEXT = POINTER(PCERT_CHAIN_CONTEXT)


class SSL_EXTRA_CERT_CHAIN_POLICY_PARA(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("dwAuthType", DWORD),
        ("fdwChecks", DWORD),
        ("pwszServerName", LPCWSTR),
    )


class CERT_CHAIN_POLICY_PARA(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("dwFlags", DWORD),
        ("pvExtraPolicyPara", c_void_p),
    )


PCERT_CHAIN_POLICY_PARA = POINTER(CERT_CHAIN_POLICY_PARA)


class CERT_CHAIN_POLICY_STATUS(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("dwError", DWORD),
        ("lChainIndex", LONG),
        ("lElementIndex", LONG),
        ("pvExtraPolicyStatus", c_void_p),
    )


PCERT_CHAIN_POLICY_STATUS = POINTER(CERT_CHAIN_POLICY_STATUS)


class CERT_CHAIN_ENGINE_CONFIG(Structure):
    _fields_ = (
        ("cbSize", DWORD),
        ("hRestrictedRoot", HCERTSTORE),
        ("hRestrictedTrust", HCERTSTORE),
        ("hRestrictedOther", HCERTSTORE),
        ("cAdditionalStore", DWORD),
        ("rghAdditionalStore", c_void_p),
        ("dwFlags", DWORD),
        ("dwUrlRetrievalTimeout", DWORD),
        ("MaximumCachedCertificates", DWORD),
        ("CycleDetectionModulus", DWORD),
        ("hExclusiveRoot", HCERTSTORE),
        ("hExclusiveTrustedPeople", HCERTSTORE),
        ("dwExclusiveFlags", DWORD),
    )


PCERT_CHAIN_ENGINE_CONFIG = POINTER(CERT_CHAIN_ENGINE_CONFIG)
PHCERTCHAINENGINE = POINTER(HCERTCHAINENGINE)

X509_ASN_ENCODING = 0x00000001
PKCS_7_ASN_ENCODING = 0x00010000
CERT_STORE_PROV_MEMORY = b"Memory"
CERT_STORE_ADD_USE_EXISTING = 2
USAGE_MATCH_TYPE_OR = 1
OID_PKIX_KP_SERVER_AUTH = c_char_p(b"1.3.6.1.5.5.7.3.1")
CERT_CHAIN_REVOCATION_CHECK_END_CERT = 0x10000000
CERT_CHAIN_REVOCATION_CHECK_CHAIN = 0x20000000
CERT_CHAIN_POLICY_IGNORE_ALL_NOT_TIME_VALID_FLAGS = 0x00000007
CERT_CHAIN_POLICY_IGNORE_INVALID_BASIC_CONSTRAINTS_FLAG = 0x00000008
CERT_CHAIN_POLICY_ALLOW_UNKNOWN_CA_FLAG = 0x00000010
CERT_CHAIN_POLICY_IGNORE_INVALID_NAME_FLAG = 0x00000040
CERT_CHAIN_POLICY_IGNORE_WRONG_USAGE_FLAG = 0x00000020
CERT_CHAIN_POLICY_IGNORE_INVALID_POLICY_FLAG = 0x00000080
CERT_CHAIN_POLICY_IGNORE_ALL_REV_UNKNOWN_FLAGS = 0x00000F00
CERT_CHAIN_POLICY_ALLOW_TESTROOT_FLAG = 0x00008000
CERT_CHAIN_POLICY_TRUST_TESTROOT_FLAG = 0x00004000
SECURITY_FLAG_IGNORE_CERT_CN_INVALID = 0x00001000
AUTHTYPE_SERVER = 2
CERT_CHAIN_POLICY_SSL = 4
FORMAT_MESSAGE_FROM_SYSTEM = 0x00001000
FORMAT_MESSAGE_IGNORE_INSERTS = 0x00000200

# Flags to set for SSLContext.verify_mode=CERT_NONE
CERT_CHAIN_POLICY_VERIFY_MODE_NONE_FLAGS = (
    CERT_CHAIN_POLICY_IGNORE_ALL_NOT_TIME_VALID_FLAGS
    | CERT_CHAIN_POLICY_IGNORE_INVALID_BASIC_CONSTRAINTS_FLAG
    | CERT_CHAIN_POLICY_ALLOW_UNKNOWN_CA_FLAG
    | CERT_CHAIN_POLICY_IGNORE_INVALID_NAME_FLAG
    | CERT_CHAIN_POLICY_IGNORE_WRONG_USAGE_FLAG
    | CERT_CHAIN_POLICY_IGNORE_INVALID_POLICY_FLAG
    | CERT_CHAIN_POLICY_IGNORE_ALL_REV_UNKNOWN_FLAGS
    | CERT_CHAIN_POLICY_ALLOW_TESTROOT_FLAG
    | CERT_CHAIN_POLICY_TRUST_TESTROOT_FLAG
)

wincrypt = WinDLL("crypt32.dll")
kernel32 = WinDLL("kernel32.dll")


def _handle_win_error(result: bool, _: Any, args: Any) -> Any:
    if not result:
        # Note, actually raises OSError after calling GetLastError and FormatMessage
        raise WinError()
    return args


CertCreateCertificateChainEngine = wincrypt.CertCreateCertificateChainEngine
CertCreateCertificateChainEngine.argtypes = (
    PCERT_CHAIN_ENGINE_CONFIG,
    PHCERTCHAINENGINE,
)
CertCreateCertificateChainEngine.errcheck = _handle_win_error

CertOpenStore = wincrypt.CertOpenStore
CertOpenStore.argtypes = (LPCSTR, DWORD, HCRYPTPROV_LEGACY, DWORD, c_void_p)
CertOpenStore.restype = HCERTSTORE
CertOpenStore.errcheck = _handle_win_error

CertAddEncodedCertificateToStore = wincrypt.CertAddEncodedCertificateToStore
CertAddEncodedCertificateToStore.argtypes = (
    HCERTSTORE,
    DWORD,
    c_char_p,
    DWORD,
    DWORD,
    PCCERT_CONTEXT,
)
CertAddEncodedCertificateToStore.restype = BOOL

CertCreateCertificateContext = wincrypt.CertCreateCertificateContext
CertCreateCertificateContext.argtypes = (DWORD, c_char_p, DWORD)
CertCreateCertificateContext.restype = PCERT_CONTEXT
CertCreateCertificateContext.errcheck = _handle_win_error

CertGetCertificateChain = wincrypt.CertGetCertificateChain
CertGetCertificateChain.argtypes = (
    HCERTCHAINENGINE,
    PCERT_CONTEXT,
    LPFILETIME,
    HCERTSTORE,
    PCERT_CHAIN_PARA,
    DWORD,
    c_void_p,
    PCCERT_CHAIN_CONTEXT,
)
CertGetCertificateChain.restype = BOOL
CertGetCertificateChain.errcheck = _handle_win_error

CertVerifyCertificateChainPolicy = wincrypt.CertVerifyCertificateChainPolicy
CertVerifyCertificateChainPolicy.argtypes = (
    c_ulong,
    PCERT_CHAIN_CONTEXT,
    PCERT_CHAIN_POLICY_PARA,
    PCERT_CHAIN_POLICY_STATUS,
)
CertVerifyCertificateChainPolicy.restype = BOOL

CertCloseStore = wincrypt.CertCloseStore
CertCloseStore.argtypes = (HCERTSTORE, DWORD)
CertCloseStore.restype = BOOL
CertCloseStore.errcheck = _handle_win_error

CertFreeCertificateChain = wincrypt.CertFreeCertificateChain
CertFreeCertificateChain.argtypes = (PCERT_CHAIN_CONTEXT,)

CertFreeCertificateContext = wincrypt.CertFreeCertificateContext
CertFreeCertificateContext.argtypes = (PCERT_CONTEXT,)

CertFreeCertificateChainEngine = wincrypt.CertFreeCertificateChainEngine
CertFreeCertificateChainEngine.argtypes = (HCERTCHAINENGINE,)

FormatMessageW = kernel32.FormatMessageW
FormatMessageW.argtypes = (
    DWORD,
    LPCVOID,
    DWORD,
    DWORD,
    LPWSTR,
    DWORD,
    c_void_p,
)
FormatMessageW.restype = DWORD


def _verify_peercerts_impl(
    ssl_context: ssl.SSLContext,
    cert_chain: list[bytes],
    server_hostname: str | None = None,
) -> None:
    """Verify the cert_chain from the server using Windows APIs."""

    # If the peer didn't send any certificates then
    # we can't do verification. Raise an error.
    if not cert_chain:
        raise ssl.SSLCertVerificationError("Peer sent no certificates to verify")

    pCertContext = None
    hIntermediateCertStore = CertOpenStore(CERT_STORE_PROV_MEMORY, 0, None, 0, None)
    try:
        # Add intermediate certs to an in-memory cert store
        for cert_bytes in cert_chain[1:]:
            CertAddEncodedCertificateToStore(
                hIntermediateCertStore,
                X509_ASN_ENCODING | PKCS_7_ASN_ENCODING,
                cert_bytes,
                len(cert_bytes),
                CERT_STORE_ADD_USE_EXISTING,
                None,
            )

        # Cert context for leaf cert
        leaf_cert = cert_chain[0]
        pCertContext = CertCreateCertificateContext(
            X509_ASN_ENCODING | PKCS_7_ASN_ENCODING, leaf_cert, len(leaf_cert)
        )

        # Chain params to match certs for serverAuth extended usage
        cert_enhkey_usage = CERT_ENHKEY_USAGE()
        cert_enhkey_usage.cUsageIdentifier = 1
        cert_enhkey_usage.rgpszUsageIdentifier = (c_char_p * 1)(OID_PKIX_KP_SERVER_AUTH)
        cert_usage_match = CERT_USAGE_MATCH()
        cert_usage_match.Usage = cert_enhkey_usage
        chain_params = CERT_CHAIN_PARA()
        chain_params.RequestedUsage = cert_usage_match
        chain_params.cbSize = sizeof(chain_params)
        pChainPara = pointer(chain_params)

        if ssl_context.verify_flags & ssl.VERIFY_CRL_CHECK_CHAIN:
            chain_flags = CERT_CHAIN_REVOCATION_CHECK_CHAIN
        elif ssl_context.verify_flags & ssl.VERIFY_CRL_CHECK_LEAF:
            chain_flags = CERT_CHAIN_REVOCATION_CHECK_END_CERT
        else:
            chain_flags = 0

        try:
            # First attempt to verify using the default Windows system trust roots
            # (default chain engine).
            _get_and_verify_cert_chain(
                ssl_context,
                None,
                hIntermediateCertStore,
                pCertContext,
                pChainPara,
                server_hostname,
                chain_flags=chain_flags,
            )
        except ssl.SSLCertVerificationError as e:
            # If that fails but custom CA certs have been added
            # to the SSLContext using load_verify_locations,
            # try verifying using a custom chain engine
            # that trusts the custom CA certs.
            custom_ca_certs: list[bytes] | None = ssl_context.get_ca_certs(
                binary_form=True
            )
            if custom_ca_certs:
                try:
                    _verify_using_custom_ca_certs(
                        ssl_context,
                        custom_ca_certs,
                        hIntermediateCertStore,
                        pCertContext,
                        pChainPara,
                        server_hostname,
                        chain_flags=chain_flags,
                    )
                # Raise the original error, not the new error.
                except ssl.SSLCertVerificationError:
                    raise e from None
            else:
                raise
    finally:
        CertCloseStore(hIntermediateCertStore, 0)
        if pCertContext:
            CertFreeCertificateContext(pCertContext)


def _get_and_verify_cert_chain(
    ssl_context: ssl.SSLContext,
    hChainEngine: HCERTCHAINENGINE | None,
    hIntermediateCertStore: HCERTSTORE,
    pPeerCertContext: c_void_p,
    pChainPara: PCERT_CHAIN_PARA,  # type: ignore[valid-type]
    server_hostname: str | None,
    chain_flags: int,
) -> None:
    ppChainContext = None
    try:
        # Get cert chain
        ppChainContext = pointer(PCERT_CHAIN_CONTEXT())
        CertGetCertificateChain(
            hChainEngine,  # chain engine
            pPeerCertContext,  # leaf cert context
            None,  # current system time
            hIntermediateCertStore,  # additional in-memory cert store
            pChainPara,  # chain-building parameters
            chain_flags,
            None,  # reserved
            ppChainContext,  # the resulting chain context
        )
        pChainContext = ppChainContext.contents

        # Verify cert chain
        ssl_extra_cert_chain_policy_para = SSL_EXTRA_CERT_CHAIN_POLICY_PARA()
        ssl_extra_cert_chain_policy_para.cbSize = sizeof(
            ssl_extra_cert_chain_policy_para
        )
        ssl_extra_cert_chain_policy_para.dwAuthType = AUTHTYPE_SERVER
        ssl_extra_cert_chain_policy_para.fdwChecks = 0
        if ssl_context.check_hostname is False:
            ssl_extra_cert_chain_policy_para.fdwChecks = (
                SECURITY_FLAG_IGNORE_CERT_CN_INVALID
            )
        if server_hostname:
            ssl_extra_cert_chain_policy_para.pwszServerName = c_wchar_p(server_hostname)

        chain_policy = CERT_CHAIN_POLICY_PARA()
        chain_policy.pvExtraPolicyPara = cast(
            pointer(ssl_extra_cert_chain_policy_para), c_void_p
        )
        if ssl_context.verify_mode == ssl.CERT_NONE:
            chain_policy.dwFlags |= CERT_CHAIN_POLICY_VERIFY_MODE_NONE_FLAGS
        chain_policy.cbSize = sizeof(chain_policy)

        pPolicyPara = pointer(chain_policy)
        policy_status = CERT_CHAIN_POLICY_STATUS()
        policy_status.cbSize = sizeof(policy_status)
        pPolicyStatus = pointer(policy_status)
        CertVerifyCertificateChainPolicy(
            CERT_CHAIN_POLICY_SSL,
            pChainContext,
            pPolicyPara,
            pPolicyStatus,
        )

        # Check status
        error_code = policy_status.dwError
        if error_code:
            # Try getting a human readable message for an error code.
            error_message_buf = create_unicode_buffer(1024)
            error_message_chars = FormatMessageW(
                FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
                None,
                error_code,
                0,
                error_message_buf,
                sizeof(error_message_buf),
                None,
            )

            # See if we received a message for the error,
            # otherwise we use a generic error with the
            # error code and hope that it's search-able.
            if error_message_chars <= 0:
                error_message = f"Certificate chain policy error {error_code:#x} [{policy_status.lElementIndex}]"
            else:
                error_message = error_message_buf.value.strip()

            err = ssl.SSLCertVerificationError(error_message)
            err.verify_message = error_message
            err.verify_code = error_code
            raise err from None
    finally:
        if ppChainContext:
            CertFreeCertificateChain(ppChainContext.contents)


def _verify_using_custom_ca_certs(
    ssl_context: ssl.SSLContext,
    custom_ca_certs: list[bytes],
    hIntermediateCertStore: HCERTSTORE,
    pPeerCertContext: c_void_p,
    pChainPara: PCERT_CHAIN_PARA,  # type: ignore[valid-type]
    server_hostname: str | None,
    chain_flags: int,
) -> None:
    hChainEngine = None
    hRootCertStore = CertOpenStore(CERT_STORE_PROV_MEMORY, 0, None, 0, None)
    try:
        # Add custom CA certs to an in-memory cert store
        for cert_bytes in custom_ca_certs:
            CertAddEncodedCertificateToStore(
                hRootCertStore,
                X509_ASN_ENCODING | PKCS_7_ASN_ENCODING,
                cert_bytes,
                len(cert_bytes),
                CERT_STORE_ADD_USE_EXISTING,
                None,
            )

        # Create a custom cert chain engine which exclusively trusts
        # certs from our hRootCertStore
        cert_chain_engine_config = CERT_CHAIN_ENGINE_CONFIG()
        cert_chain_engine_config.cbSize = sizeof(cert_chain_engine_config)
        cert_chain_engine_config.hExclusiveRoot = hRootCertStore
        pConfig = pointer(cert_chain_engine_config)
        phChainEngine = pointer(HCERTCHAINENGINE())
        CertCreateCertificateChainEngine(
            pConfig,
            phChainEngine,
        )
        hChainEngine = phChainEngine.contents

        # Get and verify a cert chain using the custom chain engine
        _get_and_verify_cert_chain(
            ssl_context,
            hChainEngine,
            hIntermediateCertStore,
            pPeerCertContext,
            pChainPara,
            server_hostname,
            chain_flags,
        )
    finally:
        if hChainEngine:
            CertFreeCertificateChainEngine(hChainEngine)
        CertCloseStore(hRootCertStore, 0)


@contextlib.contextmanager
def _configure_context(ctx: ssl.SSLContext) -> typing.Iterator[None]:
    check_hostname = ctx.check_hostname
    verify_mode = ctx.verify_mode
    ctx.check_hostname = False
    _set_ssl_context_verify_mode(ctx, ssl.CERT_NONE)
    try:
        yield
    finally:
        ctx.check_hostname = check_hostname
        _set_ssl_context_verify_mode(ctx, verify_mode)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\network\auth.py ===
"""Network Authentication Helpers

Contains interface (MultiDomainBasicAuth) and associated glue code for
providing credentials in the context of network requests.
"""

import logging
import os
import shutil
import subprocess
import sysconfig
import typing
import urllib.parse
from abc import ABC, abstractmethod
from functools import lru_cache
from os.path import commonprefix
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from pip._vendor.requests.auth import AuthBase, HTTPBasicAuth
from pip._vendor.requests.models import Request, Response
from pip._vendor.requests.utils import get_netrc_auth

from pip._internal.utils.logging import getLogger
from pip._internal.utils.misc import (
    ask,
    ask_input,
    ask_password,
    remove_auth_from_url,
    split_auth_netloc_from_url,
)
from pip._internal.vcs.versioncontrol import AuthInfo

logger = getLogger(__name__)

KEYRING_DISABLED = False


class Credentials(NamedTuple):
    url: str
    username: str
    password: str


class KeyRingBaseProvider(ABC):
    """Keyring base provider interface"""

    has_keyring: bool

    @abstractmethod
    def get_auth_info(
        self, url: str, username: Optional[str]
    ) -> Optional[AuthInfo]: ...

    @abstractmethod
    def save_auth_info(self, url: str, username: str, password: str) -> None: ...


class KeyRingNullProvider(KeyRingBaseProvider):
    """Keyring null provider"""

    has_keyring = False

    def get_auth_info(self, url: str, username: Optional[str]) -> Optional[AuthInfo]:
        return None

    def save_auth_info(self, url: str, username: str, password: str) -> None:
        return None


class KeyRingPythonProvider(KeyRingBaseProvider):
    """Keyring interface which uses locally imported `keyring`"""

    has_keyring = True

    def __init__(self) -> None:
        import keyring

        self.keyring = keyring

    def get_auth_info(self, url: str, username: Optional[str]) -> Optional[AuthInfo]:
        # Support keyring's get_credential interface which supports getting
        # credentials without a username. This is only available for
        # keyring>=15.2.0.
        if hasattr(self.keyring, "get_credential"):
            logger.debug("Getting credentials from keyring for %s", url)
            cred = self.keyring.get_credential(url, username)
            if cred is not None:
                return cred.username, cred.password
            return None

        if username is not None:
            logger.debug("Getting password from keyring for %s", url)
            password = self.keyring.get_password(url, username)
            if password:
                return username, password
        return None

    def save_auth_info(self, url: str, username: str, password: str) -> None:
        self.keyring.set_password(url, username, password)


class KeyRingCliProvider(KeyRingBaseProvider):
    """Provider which uses `keyring` cli

    Instead of calling the keyring package installed alongside pip
    we call keyring on the command line which will enable pip to
    use which ever installation of keyring is available first in
    PATH.
    """

    has_keyring = True

    def __init__(self, cmd: str) -> None:
        self.keyring = cmd

    def get_auth_info(self, url: str, username: Optional[str]) -> Optional[AuthInfo]:
        # This is the default implementation of keyring.get_credential
        # https://github.com/jaraco/keyring/blob/97689324abcf01bd1793d49063e7ca01e03d7d07/keyring/backend.py#L134-L139
        if username is not None:
            password = self._get_password(url, username)
            if password is not None:
                return username, password
        return None

    def save_auth_info(self, url: str, username: str, password: str) -> None:
        return self._set_password(url, username, password)

    def _get_password(self, service_name: str, username: str) -> Optional[str]:
        """Mirror the implementation of keyring.get_password using cli"""
        if self.keyring is None:
            return None

        cmd = [self.keyring, "get", service_name, username]
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        res = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            env=env,
        )
        if res.returncode:
            return None
        return res.stdout.decode("utf-8").strip(os.linesep)

    def _set_password(self, service_name: str, username: str, password: str) -> None:
        """Mirror the implementation of keyring.set_password using cli"""
        if self.keyring is None:
            return None
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        subprocess.run(
            [self.keyring, "set", service_name, username],
            input=f"{password}{os.linesep}".encode(),
            env=env,
            check=True,
        )
        return None


@lru_cache(maxsize=None)
def get_keyring_provider(provider: str) -> KeyRingBaseProvider:
    logger.verbose("Keyring provider requested: %s", provider)

    # keyring has previously failed and been disabled
    if KEYRING_DISABLED:
        provider = "disabled"
    if provider in ["import", "auto"]:
        try:
            impl = KeyRingPythonProvider()
            logger.verbose("Keyring provider set: import")
            return impl
        except ImportError:
            pass
        except Exception as exc:
            # In the event of an unexpected exception
            # we should warn the user
            msg = "Installed copy of keyring fails with exception %s"
            if provider == "auto":
                msg = msg + ", trying to find a keyring executable as a fallback"
            logger.warning(msg, exc, exc_info=logger.isEnabledFor(logging.DEBUG))
    if provider in ["subprocess", "auto"]:
        cli = shutil.which("keyring")
        if cli and cli.startswith(sysconfig.get_path("scripts")):
            # all code within this function is stolen from shutil.which implementation
            @typing.no_type_check
            def PATH_as_shutil_which_determines_it() -> str:
                path = os.environ.get("PATH", None)
                if path is None:
                    try:
                        path = os.confstr("CS_PATH")
                    except (AttributeError, ValueError):
                        # os.confstr() or CS_PATH is not available
                        path = os.defpath
                # bpo-35755: Don't use os.defpath if the PATH environment variable is
                # set to an empty string

                return path

            scripts = Path(sysconfig.get_path("scripts"))

            paths = []
            for path in PATH_as_shutil_which_determines_it().split(os.pathsep):
                p = Path(path)
                try:
                    if not p.samefile(scripts):
                        paths.append(path)
                except FileNotFoundError:
                    pass

            path = os.pathsep.join(paths)

            cli = shutil.which("keyring", path=path)

        if cli:
            logger.verbose("Keyring provider set: subprocess with executable %s", cli)
            return KeyRingCliProvider(cli)

    logger.verbose("Keyring provider set: disabled")
    return KeyRingNullProvider()


class MultiDomainBasicAuth(AuthBase):
    def __init__(
        self,
        prompting: bool = True,
        index_urls: Optional[List[str]] = None,
        keyring_provider: str = "auto",
    ) -> None:
        self.prompting = prompting
        self.index_urls = index_urls
        self.keyring_provider = keyring_provider  # type: ignore[assignment]
        self.passwords: Dict[str, AuthInfo] = {}
        # When the user is prompted to enter credentials and keyring is
        # available, we will offer to save them. If the user accepts,
        # this value is set to the credentials they entered. After the
        # request authenticates, the caller should call
        # ``save_credentials`` to save these.
        self._credentials_to_save: Optional[Credentials] = None

    @property
    def keyring_provider(self) -> KeyRingBaseProvider:
        return get_keyring_provider(self._keyring_provider)

    @keyring_provider.setter
    def keyring_provider(self, provider: str) -> None:
        # The free function get_keyring_provider has been decorated with
        # functools.cache. If an exception occurs in get_keyring_auth that
        # cache will be cleared and keyring disabled, take that into account
        # if you want to remove this indirection.
        self._keyring_provider = provider

    @property
    def use_keyring(self) -> bool:
        # We won't use keyring when --no-input is passed unless
        # a specific provider is requested because it might require
        # user interaction
        return self.prompting or self._keyring_provider not in ["auto", "disabled"]

    def _get_keyring_auth(
        self,
        url: Optional[str],
        username: Optional[str],
    ) -> Optional[AuthInfo]:
        """Return the tuple auth for a given url from keyring."""
        # Do nothing if no url was provided
        if not url:
            return None

        try:
            return self.keyring_provider.get_auth_info(url, username)
        except Exception as exc:
            # Log the full exception (with stacktrace) at debug, so it'll only
            # show up when running in verbose mode.
            logger.debug("Keyring is skipped due to an exception", exc_info=True)
            # Always log a shortened version of the exception.
            logger.warning(
                "Keyring is skipped due to an exception: %s",
                str(exc),
            )
            global KEYRING_DISABLED
            KEYRING_DISABLED = True
            get_keyring_provider.cache_clear()
            return None

    def _get_index_url(self, url: str) -> Optional[str]:
        """Return the original index URL matching the requested URL.

        Cached or dynamically generated credentials may work against
        the original index URL rather than just the netloc.

        The provided url should have had its username and password
        removed already. If the original index url had credentials then
        they will be included in the return value.

        Returns None if no matching index was found, or if --no-index
        was specified by the user.
        """
        if not url or not self.index_urls:
            return None

        url = remove_auth_from_url(url).rstrip("/") + "/"
        parsed_url = urllib.parse.urlsplit(url)

        candidates = []

        for index in self.index_urls:
            index = index.rstrip("/") + "/"
            parsed_index = urllib.parse.urlsplit(remove_auth_from_url(index))
            if parsed_url == parsed_index:
                return index

            if parsed_url.netloc != parsed_index.netloc:
                continue

            candidate = urllib.parse.urlsplit(index)
            candidates.append(candidate)

        if not candidates:
            return None

        candidates.sort(
            reverse=True,
            key=lambda candidate: commonprefix(
                [
                    parsed_url.path,
                    candidate.path,
                ]
            ).rfind("/"),
        )

        return urllib.parse.urlunsplit(candidates[0])

    def _get_new_credentials(
        self,
        original_url: str,
        *,
        allow_netrc: bool = True,
        allow_keyring: bool = False,
    ) -> AuthInfo:
        """Find and return credentials for the specified URL."""
        # Split the credentials and netloc from the url.
        url, netloc, url_user_password = split_auth_netloc_from_url(
            original_url,
        )

        # Start with the credentials embedded in the url
        username, password = url_user_password
        if username is not None and password is not None:
            logger.debug("Found credentials in url for %s", netloc)
            return url_user_password

        # Find a matching index url for this request
        index_url = self._get_index_url(url)
        if index_url:
            # Split the credentials from the url.
            index_info = split_auth_netloc_from_url(index_url)
            if index_info:
                index_url, _, index_url_user_password = index_info
                logger.debug("Found index url %s", index_url)

        # If an index URL was found, try its embedded credentials
        if index_url and index_url_user_password[0] is not None:
            username, password = index_url_user_password
            if username is not None and password is not None:
                logger.debug("Found credentials in index url for %s", netloc)
                return index_url_user_password

        # Get creds from netrc if we still don't have them
        if allow_netrc:
            netrc_auth = get_netrc_auth(original_url)
            if netrc_auth:
                logger.debug("Found credentials in netrc for %s", netloc)
                return netrc_auth

        # If we don't have a password and keyring is available, use it.
        if allow_keyring:
            # The index url is more specific than the netloc, so try it first
            # fmt: off
            kr_auth = (
                self._get_keyring_auth(index_url, username) or
                self._get_keyring_auth(netloc, username)
            )
            # fmt: on
            if kr_auth:
                logger.debug("Found credentials in keyring for %s", netloc)
                return kr_auth

        return username, password

    def _get_url_and_credentials(
        self, original_url: str
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """Return the credentials to use for the provided URL.

        If allowed, netrc and keyring may be used to obtain the
        correct credentials.

        Returns (url_without_credentials, username, password). Note
        that even if the original URL contains credentials, this
        function may return a different username and password.
        """
        url, netloc, _ = split_auth_netloc_from_url(original_url)

        # Try to get credentials from original url
        username, password = self._get_new_credentials(original_url)

        # If credentials not found, use any stored credentials for this netloc.
        # Do this if either the username or the password is missing.
        # This accounts for the situation in which the user has specified
        # the username in the index url, but the password comes from keyring.
        if (username is None or password is None) and netloc in self.passwords:
            un, pw = self.passwords[netloc]
            # It is possible that the cached credentials are for a different username,
            # in which case the cache should be ignored.
            if username is None or username == un:
                username, password = un, pw

        if username is not None or password is not None:
            # Convert the username and password if they're None, so that
            # this netloc will show up as "cached" in the conditional above.
            # Further, HTTPBasicAuth doesn't accept None, so it makes sense to
            # cache the value that is going to be used.
            username = username or ""
            password = password or ""

            # Store any acquired credentials.
            self.passwords[netloc] = (username, password)

        assert (
            # Credentials were found
            (username is not None and password is not None)
            # Credentials were not found
            or (username is None and password is None)
        ), f"Could not load credentials from url: {original_url}"

        return url, username, password

    def __call__(self, req: Request) -> Request:
        # Get credentials for this request
        url, username, password = self._get_url_and_credentials(req.url)

        # Set the url of the request to the url without any credentials
        req.url = url

        if username is not None and password is not None:
            # Send the basic auth with this request
            req = HTTPBasicAuth(username, password)(req)

        # Attach a hook to handle 401 responses
        req.register_hook("response", self.handle_401)

        return req

    # Factored out to allow for easy patching in tests
    def _prompt_for_password(
        self, netloc: str
    ) -> Tuple[Optional[str], Optional[str], bool]:
        username = ask_input(f"User for {netloc}: ") if self.prompting else None
        if not username:
            return None, None, False
        if self.use_keyring:
            auth = self._get_keyring_auth(netloc, username)
            if auth and auth[0] is not None and auth[1] is not None:
                return auth[0], auth[1], False
        password = ask_password("Password: ")
        return username, password, True

    # Factored out to allow for easy patching in tests
    def _should_save_password_to_keyring(self) -> bool:
        if (
            not self.prompting
            or not self.use_keyring
            or not self.keyring_provider.has_keyring
        ):
            return False
        return ask("Save credentials to keyring [y/N]: ", ["y", "n"]) == "y"

    def handle_401(self, resp: Response, **kwargs: Any) -> Response:
        # We only care about 401 responses, anything else we want to just
        #   pass through the actual response
        if resp.status_code != 401:
            return resp

        username, password = None, None

        # Query the keyring for credentials:
        if self.use_keyring:
            username, password = self._get_new_credentials(
                resp.url,
                allow_netrc=False,
                allow_keyring=True,
            )

        # We are not able to prompt the user so simply return the response
        if not self.prompting and not username and not password:
            return resp

        parsed = urllib.parse.urlparse(resp.url)

        # Prompt the user for a new username and password
        save = False
        if not username and not password:
            username, password, save = self._prompt_for_password(parsed.netloc)

        # Store the new username and password to use for future requests
        self._credentials_to_save = None
        if username is not None and password is not None:
            self.passwords[parsed.netloc] = (username, password)

            # Prompt to save the password to keyring
            if save and self._should_save_password_to_keyring():
                self._credentials_to_save = Credentials(
                    url=parsed.netloc,
                    username=username,
                    password=password,
                )

        # Consume content and release the original connection to allow our new
        #   request to reuse the same one.
        # The result of the assignment isn't used, it's just needed to consume
        # the content.
        _ = resp.content
        resp.raw.release_conn()

        # Add our new username and password to the request
        req = HTTPBasicAuth(username or "", password or "")(resp.request)
        req.register_hook("response", self.warn_on_401)

        # On successful request, save the credentials that were used to
        # keyring. (Note that if the user responded "no" above, this member
        # is not set and nothing will be saved.)
        if self._credentials_to_save:
            req.register_hook("response", self.save_credentials)

        # Send our new request
        new_resp = resp.connection.send(req, **kwargs)
        new_resp.history.append(resp)

        return new_resp

    def warn_on_401(self, resp: Response, **kwargs: Any) -> None:
        """Response callback to warn about incorrect credentials."""
        if resp.status_code == 401:
            logger.warning(
                "401 Error, Credentials not correct for %s",
                resp.request.url,
            )

    def save_credentials(self, resp: Response, **kwargs: Any) -> None:
        """Response callback to save credentials on success."""
        assert (
            self.keyring_provider.has_keyring
        ), "should never reach here without keyring"

        creds = self._credentials_to_save
        self._credentials_to_save = None
        if creds and resp.status_code < 400:
            try:
                logger.info("Saving credentials to keyring")
                self.keyring_provider.save_auth_info(
                    creds.url, creds.username, creds.password
                )
            except Exception:
                logger.exception("Failed to save credentials")

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\auth\auth_utils.py ===
import os
import re
import sys
from typing import Any, List, Optional, Tuple

from fastapi import HTTPException, Request, status

from litellm import Router, provider_list
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import *
from litellm.types.router import CONFIGURABLE_CLIENTSIDE_AUTH_PARAMS


def _get_request_ip_address(
    request: Request, use_x_forwarded_for: Optional[bool] = False
) -> Optional[str]:
    client_ip = None
    if use_x_forwarded_for is True and "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"]
    elif request.client is not None:
        client_ip = request.client.host
    else:
        client_ip = ""

    return client_ip


def _check_valid_ip(
    allowed_ips: Optional[List[str]],
    request: Request,
    use_x_forwarded_for: Optional[bool] = False,
) -> Tuple[bool, Optional[str]]:
    """
    Returns if ip is allowed or not
    """
    if allowed_ips is None:  # if not set, assume true
        return True, None

    # if general_settings.get("use_x_forwarded_for") is True then use x-forwarded-for
    client_ip = _get_request_ip_address(
        request=request, use_x_forwarded_for=use_x_forwarded_for
    )

    # Check if IP address is allowed
    if client_ip not in allowed_ips:
        return False, client_ip

    return True, client_ip


def check_complete_credentials(request_body: dict) -> bool:
    """
    if 'api_base' in request body. Check if complete credentials given. Prevent malicious attacks.
    """
    given_model: Optional[str] = None

    given_model = request_body.get("model")
    if given_model is None:
        return False

    if (
        "sagemaker" in given_model
        or "bedrock" in given_model
        or "vertex_ai" in given_model
        or "vertex_ai_beta" in given_model
    ):
        # complex credentials - easier to make a malicious request
        return False

    if "api_key" in request_body:
        return True

    return False


def check_regex_or_str_match(request_body_value: Any, regex_str: str) -> bool:
    """
    Check if request_body_value matches the regex_str or is equal to param
    """
    if re.match(regex_str, request_body_value) or regex_str == request_body_value:
        return True
    return False


def _is_param_allowed(
    param: str,
    request_body_value: Any,
    configurable_clientside_auth_params: CONFIGURABLE_CLIENTSIDE_AUTH_PARAMS,
) -> bool:
    """
    Check if param is a str or dict and if request_body_value is in the list of allowed values
    """
    if configurable_clientside_auth_params is None:
        return False

    for item in configurable_clientside_auth_params:
        if isinstance(item, str) and param == item:
            return True
        elif isinstance(item, Dict):
            if param == "api_base" and check_regex_or_str_match(
                request_body_value=request_body_value,
                regex_str=item["api_base"],
            ):  # assume param is a regex
                return True

    return False


def _allow_model_level_clientside_configurable_parameters(
    model: str, param: str, request_body_value: Any, llm_router: Optional[Router]
) -> bool:
    """
    Check if model is allowed to use configurable client-side params
    - get matching model
    - check if 'clientside_configurable_parameters' is set for model
    -
    """
    if llm_router is None:
        return False
    # check if model is set
    model_info = llm_router.get_model_group_info(model_group=model)
    if model_info is None:
        # check if wildcard model is set
        if model.split("/", 1)[0] in provider_list:
            model_info = llm_router.get_model_group_info(
                model_group=model.split("/", 1)[0]
            )

    if model_info is None:
        return False

    if model_info is None or model_info.configurable_clientside_auth_params is None:
        return False

    return _is_param_allowed(
        param=param,
        request_body_value=request_body_value,
        configurable_clientside_auth_params=model_info.configurable_clientside_auth_params,
    )


def is_request_body_safe(
    request_body: dict, general_settings: dict, llm_router: Optional[Router], model: str
) -> bool:
    """
    Check if the request body is safe.

    A malicious user can set the ﻿api_base to their own domain and invoke POST /chat/completions to intercept and steal the OpenAI API key.
    Relevant issue: https://huntr.com/bounties/4001e1a2-7b7a-4776-a3ae-e6692ec3d997
    """
    banned_params = ["api_base", "base_url"]

    for param in banned_params:
        if (
            param in request_body
            and not check_complete_credentials(  # allow client-credentials to be passed to proxy
                request_body=request_body
            )
        ):
            if general_settings.get("allow_client_side_credentials") is True:
                return True
            elif (
                _allow_model_level_clientside_configurable_parameters(
                    model=model,
                    param=param,
                    request_body_value=request_body[param],
                    llm_router=llm_router,
                )
                is True
            ):
                return True
            raise ValueError(
                f"Rejected Request: {param} is not allowed in request body. "
                "Enable with `general_settings::allow_client_side_credentials` on proxy config.yaml. "
                "Relevant Issue: https://huntr.com/bounties/4001e1a2-7b7a-4776-a3ae-e6692ec3d997",
            )

    return True


async def pre_db_read_auth_checks(
    request: Request,
    request_data: dict,
    route: str,
):
    """
    1. Checks if request size is under max_request_size_mb (if set)
    2. Check if request body is safe (example user has not set api_base in request body)
    3. Check if IP address is allowed (if set)
    4. Check if request route is an allowed route on the proxy (if set)

    Returns:
    - True

    Raises:
    - HTTPException if request fails initial auth checks
    """
    from litellm.proxy.proxy_server import general_settings, llm_router, premium_user

    # Check 1. request size
    await check_if_request_size_is_safe(request=request)

    # Check 2. Request body is safe
    is_request_body_safe(
        request_body=request_data,
        general_settings=general_settings,
        llm_router=llm_router,
        model=request_data.get(
            "model", ""
        ),  # [TODO] use model passed in url as well (azure openai routes)
    )

    # Check 3. Check if IP address is allowed
    is_valid_ip, passed_in_ip = _check_valid_ip(
        allowed_ips=general_settings.get("allowed_ips", None),
        use_x_forwarded_for=general_settings.get("use_x_forwarded_for", False),
        request=request,
    )

    if not is_valid_ip:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access forbidden: IP address {passed_in_ip} not allowed.",
        )

    # Check 4. Check if request route is an allowed route on the proxy
    if "allowed_routes" in general_settings:
        _allowed_routes = general_settings["allowed_routes"]
        if premium_user is not True:
            verbose_proxy_logger.error(
                f"Trying to set allowed_routes. This is an Enterprise feature. {CommonProxyErrors.not_premium_user.value}"
            )
        if route not in _allowed_routes:
            verbose_proxy_logger.error(
                f"Route {route} not in allowed_routes={_allowed_routes}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Route {route} not allowed",
            )


def route_in_additonal_public_routes(current_route: str):
    """
    Helper to check if the user defined public_routes on config.yaml

    Parameters:
    - current_route: str - the route the user is trying to call

    Returns:
    - bool - True if the route is defined in public_routes
    - bool - False if the route is not defined in public_routes


    In order to use this the litellm config.yaml should have the following in general_settings:

    ```yaml
    general_settings:
        master_key: sk-1234
        public_routes: ["LiteLLMRoutes.public_routes", "/spend/calculate"]
    ```
    """

    # check if user is premium_user - if not do nothing
    from litellm.proxy.proxy_server import general_settings, premium_user

    try:
        if premium_user is not True:
            return False
        # check if this is defined on the config
        if general_settings is None:
            return False

        routes_defined = general_settings.get("public_routes", [])
        if current_route in routes_defined:
            return True

        return False
    except Exception as e:
        verbose_proxy_logger.error(f"route_in_additonal_public_routes: {str(e)}")
        return False


def get_request_route(request: Request) -> str:
    """
    Helper to get the route from the request

    remove base url from path if set e.g. `/genai/chat/completions` -> `/chat/completions
    """
    try:
        if hasattr(request, "base_url") and request.url.path.startswith(
            request.base_url.path
        ):
            # remove base_url from path
            return request.url.path[len(request.base_url.path) - 1 :]
        else:
            return request.url.path
    except Exception as e:
        verbose_proxy_logger.debug(
            f"error on get_request_route: {str(e)}, defaulting to request.url.path={request.url.path}"
        )
        return request.url.path


async def check_if_request_size_is_safe(request: Request) -> bool:
    """
    Enterprise Only:
        - Checks if the request size is within the limit

    Args:
        request (Request): The incoming request.

    Returns:
        bool: True if the request size is within the limit

    Raises:
        ProxyException: If the request size is too large

    """
    from litellm.proxy.proxy_server import general_settings, premium_user

    max_request_size_mb = general_settings.get("max_request_size_mb", None)

    if max_request_size_mb is not None:
        # Check if premium user
        if premium_user is not True:
            verbose_proxy_logger.warning(
                f"using max_request_size_mb - not checking -  this is an enterprise only feature. {CommonProxyErrors.not_premium_user.value}"
            )
            return True

        # Get the request body
        content_length = request.headers.get("content-length")

        if content_length:
            header_size = int(content_length)
            header_size_mb = bytes_to_mb(bytes_value=header_size)
            verbose_proxy_logger.debug(
                f"content_length request size in MB={header_size_mb}"
            )

            if header_size_mb > max_request_size_mb:
                raise ProxyException(
                    message=f"Request size is too large. Request size is {header_size_mb} MB. Max size is {max_request_size_mb} MB",
                    type=ProxyErrorTypes.bad_request_error.value,
                    code=400,
                    param="content-length",
                )
        else:
            # If Content-Length is not available, read the body
            body = await request.body()
            body_size = len(body)
            request_size_mb = bytes_to_mb(bytes_value=body_size)

            verbose_proxy_logger.debug(
                f"request body request size in MB={request_size_mb}"
            )
            if request_size_mb > max_request_size_mb:
                raise ProxyException(
                    message=f"Request size is too large. Request size is {request_size_mb} MB. Max size is {max_request_size_mb} MB",
                    type=ProxyErrorTypes.bad_request_error.value,
                    code=400,
                    param="content-length",
                )

    return True


async def check_response_size_is_safe(response: Any) -> bool:
    """
    Enterprise Only:
        - Checks if the response size is within the limit

    Args:
        response (Any): The response to check.

    Returns:
        bool: True if the response size is within the limit

    Raises:
        ProxyException: If the response size is too large

    """

    from litellm.proxy.proxy_server import general_settings, premium_user

    max_response_size_mb = general_settings.get("max_response_size_mb", None)
    if max_response_size_mb is not None:
        # Check if premium user
        if premium_user is not True:
            verbose_proxy_logger.warning(
                f"using max_response_size_mb - not checking -  this is an enterprise only feature. {CommonProxyErrors.not_premium_user.value}"
            )
            return True

        response_size_mb = bytes_to_mb(bytes_value=sys.getsizeof(response))
        verbose_proxy_logger.debug(f"response size in MB={response_size_mb}")
        if response_size_mb > max_response_size_mb:
            raise ProxyException(
                message=f"Response size is too large. Response size is {response_size_mb} MB. Max size is {max_response_size_mb} MB",
                type=ProxyErrorTypes.bad_request_error.value,
                code=400,
                param="content-length",
            )

    return True


def bytes_to_mb(bytes_value: int):
    """
    Helper to convert bytes to MB
    """
    return bytes_value / (1024 * 1024)


# helpers used by parallel request limiter to handle model rpm/tpm limits for a given api key
def get_key_model_rpm_limit(
    user_api_key_dict: UserAPIKeyAuth,
) -> Optional[Dict[str, int]]:
    if user_api_key_dict.metadata:
        if "model_rpm_limit" in user_api_key_dict.metadata:
            return user_api_key_dict.metadata["model_rpm_limit"]
    elif user_api_key_dict.model_max_budget:
        model_rpm_limit: Dict[str, Any] = {}
        for model, budget in user_api_key_dict.model_max_budget.items():
            if "rpm_limit" in budget and budget["rpm_limit"] is not None:
                model_rpm_limit[model] = budget["rpm_limit"]
        return model_rpm_limit

    return None


def get_key_model_tpm_limit(
    user_api_key_dict: UserAPIKeyAuth,
) -> Optional[Dict[str, int]]:
    if user_api_key_dict.metadata:
        if "model_tpm_limit" in user_api_key_dict.metadata:
            return user_api_key_dict.metadata["model_tpm_limit"]
    elif user_api_key_dict.model_max_budget:
        if "tpm_limit" in user_api_key_dict.model_max_budget:
            return user_api_key_dict.model_max_budget["tpm_limit"]

    return None


def is_pass_through_provider_route(route: str) -> bool:
    PROVIDER_SPECIFIC_PASS_THROUGH_ROUTES = [
        "vertex-ai",
    ]

    # check if any of the prefixes are in the route
    for prefix in PROVIDER_SPECIFIC_PASS_THROUGH_ROUTES:
        if prefix in route:
            return True

    return False


def should_run_auth_on_pass_through_provider_route(route: str) -> bool:
    """
    Use this to decide if the rest of the LiteLLM Virtual Key auth checks should run on /vertex-ai/{endpoint} routes
    Use this to decide if the rest of the LiteLLM Virtual Key auth checks should run on provider pass through routes
    ex /vertex-ai/{endpoint} routes
    Run virtual key auth if the following is try:
    - User is premium_user
    - User has enabled litellm_setting.use_client_credentials_pass_through_routes
    """
    from litellm.proxy.proxy_server import general_settings, premium_user

    if premium_user is not True:
        return False

    # premium use has opted into using client credentials
    if (
        general_settings.get("use_client_credentials_pass_through_routes", False)
        is True
    ):
        return False

    # only enabled for LiteLLM Enterprise
    return True


def _has_user_setup_sso():
    """
    Check if the user has set up single sign-on (SSO) by verifying the presence of Microsoft client ID, Google client ID or generic client ID and UI username environment variables.
    Returns a boolean indicating whether SSO has been set up.
    """
    microsoft_client_id = os.getenv("MICROSOFT_CLIENT_ID", None)
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", None)
    generic_client_id = os.getenv("GENERIC_CLIENT_ID", None)

    sso_setup = (
        (microsoft_client_id is not None)
        or (google_client_id is not None)
        or (generic_client_id is not None)
    )

    return sso_setup


def get_end_user_id_from_request_body(request_body: dict, request_headers: Optional[dict] = None) -> Optional[str]:
    # Import general_settings here to avoid potential circular import issues at module level
    # and to ensure it's fetched at runtime.
    from litellm.proxy.proxy_server import general_settings

    # Check 1: Custom Header from general_settings.user_header_name (only if request_headers is provided)
    # User query: "system not respecting user_header_name property"
    # This implies the key in general_settings is 'user_header_name'.
    if request_headers is not None:
        user_id_header_config_key = "user_header_name" 
        
        custom_header_name_to_check = general_settings.get(user_id_header_config_key) 
        
        if custom_header_name_to_check and isinstance(custom_header_name_to_check, str):
            user_id_from_header = request_headers.get(custom_header_name_to_check)
            if user_id_from_header is not None and user_id_from_header.strip():
                return str(user_id_from_header)

    # Check 2: 'user' field in request_body (commonly OpenAI)
    if "user" in request_body and request_body["user"] is not None:
        user_from_body_user_field = request_body["user"]
        return str(user_from_body_user_field)

    # Check 3: 'litellm_metadata.user' in request_body (commonly Anthropic)
    litellm_metadata = request_body.get("litellm_metadata")
    if isinstance(litellm_metadata, dict):
        user_from_litellm_metadata = litellm_metadata.get("user")
        if user_from_litellm_metadata is not None:
            return str(user_from_litellm_metadata)

    # Check 4: 'metadata.user_id' in request_body (another common pattern)
    metadata_dict = request_body.get("metadata") 
    if isinstance(metadata_dict, dict): 
        user_id_from_metadata_field = metadata_dict.get("user_id")
        if user_id_from_metadata_field is not None:
            return str(user_id_from_metadata_field)
    
    return None


def get_model_from_request(
    request_data: dict, route: str
) -> Optional[Union[str, List[str]]]:
    # First try to get model from request_data
    model = request_data.get("model") or request_data.get("target_model_names")

    if model is not None:
        model_names = model.split(",")
        if len(model_names) == 1:
            model = model_names[0].strip()
        else:
            model = [m.strip() for m in model_names]

    # If model not in request_data, try to extract from route
    if model is None:
        # Parse model from route that follows the pattern /openai/deployments/{model}/*
        match = re.match(r"/openai/deployments/([^/]+)", route)
        if match:
            model = match.group(1)

    return model


def abbreviate_api_key(api_key: str) -> str:
    return f"sk-...{api_key[-4:]}"

# === NexusCore/openenv\Lib\site-packages\pip\_internal\network\auth.py ===
"""Network Authentication Helpers

Contains interface (MultiDomainBasicAuth) and associated glue code for
providing credentials in the context of network requests.
"""

import logging
import os
import shutil
import subprocess
import sysconfig
import typing
import urllib.parse
from abc import ABC, abstractmethod
from functools import lru_cache
from os.path import commonprefix
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from pip._vendor.requests.auth import AuthBase, HTTPBasicAuth
from pip._vendor.requests.models import Request, Response
from pip._vendor.requests.utils import get_netrc_auth

from pip._internal.utils.logging import getLogger
from pip._internal.utils.misc import (
    ask,
    ask_input,
    ask_password,
    remove_auth_from_url,
    split_auth_netloc_from_url,
)
from pip._internal.vcs.versioncontrol import AuthInfo

logger = getLogger(__name__)

KEYRING_DISABLED = False


class Credentials(NamedTuple):
    url: str
    username: str
    password: str


class KeyRingBaseProvider(ABC):
    """Keyring base provider interface"""

    has_keyring: bool

    @abstractmethod
    def get_auth_info(
        self, url: str, username: Optional[str]
    ) -> Optional[AuthInfo]: ...

    @abstractmethod
    def save_auth_info(self, url: str, username: str, password: str) -> None: ...


class KeyRingNullProvider(KeyRingBaseProvider):
    """Keyring null provider"""

    has_keyring = False

    def get_auth_info(self, url: str, username: Optional[str]) -> Optional[AuthInfo]:
        return None

    def save_auth_info(self, url: str, username: str, password: str) -> None:
        return None


class KeyRingPythonProvider(KeyRingBaseProvider):
    """Keyring interface which uses locally imported `keyring`"""

    has_keyring = True

    def __init__(self) -> None:
        import keyring

        self.keyring = keyring

    def get_auth_info(self, url: str, username: Optional[str]) -> Optional[AuthInfo]:
        # Support keyring's get_credential interface which supports getting
        # credentials without a username. This is only available for
        # keyring>=15.2.0.
        if hasattr(self.keyring, "get_credential"):
            logger.debug("Getting credentials from keyring for %s", url)
            cred = self.keyring.get_credential(url, username)
            if cred is not None:
                return cred.username, cred.password
            return None

        if username is not None:
            logger.debug("Getting password from keyring for %s", url)
            password = self.keyring.get_password(url, username)
            if password:
                return username, password
        return None

    def save_auth_info(self, url: str, username: str, password: str) -> None:
        self.keyring.set_password(url, username, password)


class KeyRingCliProvider(KeyRingBaseProvider):
    """Provider which uses `keyring` cli

    Instead of calling the keyring package installed alongside pip
    we call keyring on the command line which will enable pip to
    use which ever installation of keyring is available first in
    PATH.
    """

    has_keyring = True

    def __init__(self, cmd: str) -> None:
        self.keyring = cmd

    def get_auth_info(self, url: str, username: Optional[str]) -> Optional[AuthInfo]:
        # This is the default implementation of keyring.get_credential
        # https://github.com/jaraco/keyring/blob/97689324abcf01bd1793d49063e7ca01e03d7d07/keyring/backend.py#L134-L139
        if username is not None:
            password = self._get_password(url, username)
            if password is not None:
                return username, password
        return None

    def save_auth_info(self, url: str, username: str, password: str) -> None:
        return self._set_password(url, username, password)

    def _get_password(self, service_name: str, username: str) -> Optional[str]:
        """Mirror the implementation of keyring.get_password using cli"""
        if self.keyring is None:
            return None

        cmd = [self.keyring, "get", service_name, username]
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        res = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            env=env,
        )
        if res.returncode:
            return None
        return res.stdout.decode("utf-8").strip(os.linesep)

    def _set_password(self, service_name: str, username: str, password: str) -> None:
        """Mirror the implementation of keyring.set_password using cli"""
        if self.keyring is None:
            return None
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        subprocess.run(
            [self.keyring, "set", service_name, username],
            input=f"{password}{os.linesep}".encode(),
            env=env,
            check=True,
        )
        return None


@lru_cache(maxsize=None)
def get_keyring_provider(provider: str) -> KeyRingBaseProvider:
    logger.verbose("Keyring provider requested: %s", provider)

    # keyring has previously failed and been disabled
    if KEYRING_DISABLED:
        provider = "disabled"
    if provider in ["import", "auto"]:
        try:
            impl = KeyRingPythonProvider()
            logger.verbose("Keyring provider set: import")
            return impl
        except ImportError:
            pass
        except Exception as exc:
            # In the event of an unexpected exception
            # we should warn the user
            msg = "Installed copy of keyring fails with exception %s"
            if provider == "auto":
                msg = msg + ", trying to find a keyring executable as a fallback"
            logger.warning(msg, exc, exc_info=logger.isEnabledFor(logging.DEBUG))
    if provider in ["subprocess", "auto"]:
        cli = shutil.which("keyring")
        if cli and cli.startswith(sysconfig.get_path("scripts")):
            # all code within this function is stolen from shutil.which implementation
            @typing.no_type_check
            def PATH_as_shutil_which_determines_it() -> str:
                path = os.environ.get("PATH", None)
                if path is None:
                    try:
                        path = os.confstr("CS_PATH")
                    except (AttributeError, ValueError):
                        # os.confstr() or CS_PATH is not available
                        path = os.defpath
                # bpo-35755: Don't use os.defpath if the PATH environment variable is
                # set to an empty string

                return path

            scripts = Path(sysconfig.get_path("scripts"))

            paths = []
            for path in PATH_as_shutil_which_determines_it().split(os.pathsep):
                p = Path(path)
                try:
                    if not p.samefile(scripts):
                        paths.append(path)
                except FileNotFoundError:
                    pass

            path = os.pathsep.join(paths)

            cli = shutil.which("keyring", path=path)

        if cli:
            logger.verbose("Keyring provider set: subprocess with executable %s", cli)
            return KeyRingCliProvider(cli)

    logger.verbose("Keyring provider set: disabled")
    return KeyRingNullProvider()


class MultiDomainBasicAuth(AuthBase):
    def __init__(
        self,
        prompting: bool = True,
        index_urls: Optional[List[str]] = None,
        keyring_provider: str = "auto",
    ) -> None:
        self.prompting = prompting
        self.index_urls = index_urls
        self.keyring_provider = keyring_provider  # type: ignore[assignment]
        self.passwords: Dict[str, AuthInfo] = {}
        # When the user is prompted to enter credentials and keyring is
        # available, we will offer to save them. If the user accepts,
        # this value is set to the credentials they entered. After the
        # request authenticates, the caller should call
        # ``save_credentials`` to save these.
        self._credentials_to_save: Optional[Credentials] = None

    @property
    def keyring_provider(self) -> KeyRingBaseProvider:
        return get_keyring_provider(self._keyring_provider)

    @keyring_provider.setter
    def keyring_provider(self, provider: str) -> None:
        # The free function get_keyring_provider has been decorated with
        # functools.cache. If an exception occurs in get_keyring_auth that
        # cache will be cleared and keyring disabled, take that into account
        # if you want to remove this indirection.
        self._keyring_provider = provider

    @property
    def use_keyring(self) -> bool:
        # We won't use keyring when --no-input is passed unless
        # a specific provider is requested because it might require
        # user interaction
        return self.prompting or self._keyring_provider not in ["auto", "disabled"]

    def _get_keyring_auth(
        self,
        url: Optional[str],
        username: Optional[str],
    ) -> Optional[AuthInfo]:
        """Return the tuple auth for a given url from keyring."""
        # Do nothing if no url was provided
        if not url:
            return None

        try:
            return self.keyring_provider.get_auth_info(url, username)
        except Exception as exc:
            # Log the full exception (with stacktrace) at debug, so it'll only
            # show up when running in verbose mode.
            logger.debug("Keyring is skipped due to an exception", exc_info=True)
            # Always log a shortened version of the exception.
            logger.warning(
                "Keyring is skipped due to an exception: %s",
                str(exc),
            )
            global KEYRING_DISABLED
            KEYRING_DISABLED = True
            get_keyring_provider.cache_clear()
            return None

    def _get_index_url(self, url: str) -> Optional[str]:
        """Return the original index URL matching the requested URL.

        Cached or dynamically generated credentials may work against
        the original index URL rather than just the netloc.

        The provided url should have had its username and password
        removed already. If the original index url had credentials then
        they will be included in the return value.

        Returns None if no matching index was found, or if --no-index
        was specified by the user.
        """
        if not url or not self.index_urls:
            return None

        url = remove_auth_from_url(url).rstrip("/") + "/"
        parsed_url = urllib.parse.urlsplit(url)

        candidates = []

        for index in self.index_urls:
            index = index.rstrip("/") + "/"
            parsed_index = urllib.parse.urlsplit(remove_auth_from_url(index))
            if parsed_url == parsed_index:
                return index

            if parsed_url.netloc != parsed_index.netloc:
                continue

            candidate = urllib.parse.urlsplit(index)
            candidates.append(candidate)

        if not candidates:
            return None

        candidates.sort(
            reverse=True,
            key=lambda candidate: commonprefix(
                [
                    parsed_url.path,
                    candidate.path,
                ]
            ).rfind("/"),
        )

        return urllib.parse.urlunsplit(candidates[0])

    def _get_new_credentials(
        self,
        original_url: str,
        *,
        allow_netrc: bool = True,
        allow_keyring: bool = False,
    ) -> AuthInfo:
        """Find and return credentials for the specified URL."""
        # Split the credentials and netloc from the url.
        url, netloc, url_user_password = split_auth_netloc_from_url(
            original_url,
        )

        # Start with the credentials embedded in the url
        username, password = url_user_password
        if username is not None and password is not None:
            logger.debug("Found credentials in url for %s", netloc)
            return url_user_password

        # Find a matching index url for this request
        index_url = self._get_index_url(url)
        if index_url:
            # Split the credentials from the url.
            index_info = split_auth_netloc_from_url(index_url)
            if index_info:
                index_url, _, index_url_user_password = index_info
                logger.debug("Found index url %s", index_url)

        # If an index URL was found, try its embedded credentials
        if index_url and index_url_user_password[0] is not None:
            username, password = index_url_user_password
            if username is not None and password is not None:
                logger.debug("Found credentials in index url for %s", netloc)
                return index_url_user_password

        # Get creds from netrc if we still don't have them
        if allow_netrc:
            netrc_auth = get_netrc_auth(original_url)
            if netrc_auth:
                logger.debug("Found credentials in netrc for %s", netloc)
                return netrc_auth

        # If we don't have a password and keyring is available, use it.
        if allow_keyring:
            # The index url is more specific than the netloc, so try it first
            # fmt: off
            kr_auth = (
                self._get_keyring_auth(index_url, username) or
                self._get_keyring_auth(netloc, username)
            )
            # fmt: on
            if kr_auth:
                logger.debug("Found credentials in keyring for %s", netloc)
                return kr_auth

        return username, password

    def _get_url_and_credentials(
        self, original_url: str
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """Return the credentials to use for the provided URL.

        If allowed, netrc and keyring may be used to obtain the
        correct credentials.

        Returns (url_without_credentials, username, password). Note
        that even if the original URL contains credentials, this
        function may return a different username and password.
        """
        url, netloc, _ = split_auth_netloc_from_url(original_url)

        # Try to get credentials from original url
        username, password = self._get_new_credentials(original_url)

        # If credentials not found, use any stored credentials for this netloc.
        # Do this if either the username or the password is missing.
        # This accounts for the situation in which the user has specified
        # the username in the index url, but the password comes from keyring.
        if (username is None or password is None) and netloc in self.passwords:
            un, pw = self.passwords[netloc]
            # It is possible that the cached credentials are for a different username,
            # in which case the cache should be ignored.
            if username is None or username == un:
                username, password = un, pw

        if username is not None or password is not None:
            # Convert the username and password if they're None, so that
            # this netloc will show up as "cached" in the conditional above.
            # Further, HTTPBasicAuth doesn't accept None, so it makes sense to
            # cache the value that is going to be used.
            username = username or ""
            password = password or ""

            # Store any acquired credentials.
            self.passwords[netloc] = (username, password)

        assert (
            # Credentials were found
            (username is not None and password is not None)
            # Credentials were not found
            or (username is None and password is None)
        ), f"Could not load credentials from url: {original_url}"

        return url, username, password

    def __call__(self, req: Request) -> Request:
        # Get credentials for this request
        url, username, password = self._get_url_and_credentials(req.url)

        # Set the url of the request to the url without any credentials
        req.url = url

        if username is not None and password is not None:
            # Send the basic auth with this request
            req = HTTPBasicAuth(username, password)(req)

        # Attach a hook to handle 401 responses
        req.register_hook("response", self.handle_401)

        return req

    # Factored out to allow for easy patching in tests
    def _prompt_for_password(
        self, netloc: str
    ) -> Tuple[Optional[str], Optional[str], bool]:
        username = ask_input(f"User for {netloc}: ") if self.prompting else None
        if not username:
            return None, None, False
        if self.use_keyring:
            auth = self._get_keyring_auth(netloc, username)
            if auth and auth[0] is not None and auth[1] is not None:
                return auth[0], auth[1], False
        password = ask_password("Password: ")
        return username, password, True

    # Factored out to allow for easy patching in tests
    def _should_save_password_to_keyring(self) -> bool:
        if (
            not self.prompting
            or not self.use_keyring
            or not self.keyring_provider.has_keyring
        ):
            return False
        return ask("Save credentials to keyring [y/N]: ", ["y", "n"]) == "y"

    def handle_401(self, resp: Response, **kwargs: Any) -> Response:
        # We only care about 401 responses, anything else we want to just
        #   pass through the actual response
        if resp.status_code != 401:
            return resp

        username, password = None, None

        # Query the keyring for credentials:
        if self.use_keyring:
            username, password = self._get_new_credentials(
                resp.url,
                allow_netrc=False,
                allow_keyring=True,
            )

        # We are not able to prompt the user so simply return the response
        if not self.prompting and not username and not password:
            return resp

        parsed = urllib.parse.urlparse(resp.url)

        # Prompt the user for a new username and password
        save = False
        if not username and not password:
            username, password, save = self._prompt_for_password(parsed.netloc)

        # Store the new username and password to use for future requests
        self._credentials_to_save = None
        if username is not None and password is not None:
            self.passwords[parsed.netloc] = (username, password)

            # Prompt to save the password to keyring
            if save and self._should_save_password_to_keyring():
                self._credentials_to_save = Credentials(
                    url=parsed.netloc,
                    username=username,
                    password=password,
                )

        # Consume content and release the original connection to allow our new
        #   request to reuse the same one.
        # The result of the assignment isn't used, it's just needed to consume
        # the content.
        _ = resp.content
        resp.raw.release_conn()

        # Add our new username and password to the request
        req = HTTPBasicAuth(username or "", password or "")(resp.request)
        req.register_hook("response", self.warn_on_401)

        # On successful request, save the credentials that were used to
        # keyring. (Note that if the user responded "no" above, this member
        # is not set and nothing will be saved.)
        if self._credentials_to_save:
            req.register_hook("response", self.save_credentials)

        # Send our new request
        new_resp = resp.connection.send(req, **kwargs)
        new_resp.history.append(resp)

        return new_resp

    def warn_on_401(self, resp: Response, **kwargs: Any) -> None:
        """Response callback to warn about incorrect credentials."""
        if resp.status_code == 401:
            logger.warning(
                "401 Error, Credentials not correct for %s",
                resp.request.url,
            )

    def save_credentials(self, resp: Response, **kwargs: Any) -> None:
        """Response callback to save credentials on success."""
        assert (
            self.keyring_provider.has_keyring
        ), "should never reach here without keyring"

        creds = self._credentials_to_save
        self._credentials_to_save = None
        if creds and resp.status_code < 400:
            try:
                logger.info("Saving credentials to keyring")
                self.keyring_provider.save_auth_info(
                    creds.url, creds.username, creds.password
                )
            except Exception:
                logger.exception("Failed to save credentials")

# === NexusCore/openenv\Lib\site-packages\click\testing.py ===
from __future__ import annotations

import collections.abc as cabc
import contextlib
import io
import os
import shlex
import shutil
import sys
import tempfile
import typing as t
from types import TracebackType

from . import _compat
from . import formatting
from . import termui
from . import utils
from ._compat import _find_binary_reader

if t.TYPE_CHECKING:
    from _typeshed import ReadableBuffer

    from .core import Command


class EchoingStdin:
    def __init__(self, input: t.BinaryIO, output: t.BinaryIO) -> None:
        self._input = input
        self._output = output
        self._paused = False

    def __getattr__(self, x: str) -> t.Any:
        return getattr(self._input, x)

    def _echo(self, rv: bytes) -> bytes:
        if not self._paused:
            self._output.write(rv)

        return rv

    def read(self, n: int = -1) -> bytes:
        return self._echo(self._input.read(n))

    def read1(self, n: int = -1) -> bytes:
        return self._echo(self._input.read1(n))  # type: ignore

    def readline(self, n: int = -1) -> bytes:
        return self._echo(self._input.readline(n))

    def readlines(self) -> list[bytes]:
        return [self._echo(x) for x in self._input.readlines()]

    def __iter__(self) -> cabc.Iterator[bytes]:
        return iter(self._echo(x) for x in self._input)

    def __repr__(self) -> str:
        return repr(self._input)


@contextlib.contextmanager
def _pause_echo(stream: EchoingStdin | None) -> cabc.Iterator[None]:
    if stream is None:
        yield
    else:
        stream._paused = True
        yield
        stream._paused = False


class BytesIOCopy(io.BytesIO):
    """Patch ``io.BytesIO`` to let the written stream be copied to another.

    .. versionadded:: 8.2
    """

    def __init__(self, copy_to: io.BytesIO) -> None:
        super().__init__()
        self.copy_to = copy_to

    def flush(self) -> None:
        super().flush()
        self.copy_to.flush()

    def write(self, b: ReadableBuffer) -> int:
        self.copy_to.write(b)
        return super().write(b)


class StreamMixer:
    """Mixes `<stdout>` and `<stderr>` streams.

    The result is available in the ``output`` attribute.

    .. versionadded:: 8.2
    """

    def __init__(self) -> None:
        self.output: io.BytesIO = io.BytesIO()
        self.stdout: io.BytesIO = BytesIOCopy(copy_to=self.output)
        self.stderr: io.BytesIO = BytesIOCopy(copy_to=self.output)


class _NamedTextIOWrapper(io.TextIOWrapper):
    def __init__(
        self, buffer: t.BinaryIO, name: str, mode: str, **kwargs: t.Any
    ) -> None:
        super().__init__(buffer, **kwargs)
        self._name = name
        self._mode = mode

    @property
    def name(self) -> str:
        return self._name

    @property
    def mode(self) -> str:
        return self._mode

    def __next__(self) -> str:  # type: ignore
        try:
            line = super().__next__()
        except StopIteration as e:
            raise EOFError() from e
        return line


def make_input_stream(
    input: str | bytes | t.IO[t.Any] | None, charset: str
) -> t.BinaryIO:
    # Is already an input stream.
    if hasattr(input, "read"):
        rv = _find_binary_reader(t.cast("t.IO[t.Any]", input))

        if rv is not None:
            return rv

        raise TypeError("Could not find binary reader for input stream.")

    if input is None:
        input = b""
    elif isinstance(input, str):
        input = input.encode(charset)

    return io.BytesIO(input)


class Result:
    """Holds the captured result of an invoked CLI script.

    :param runner: The runner that created the result
    :param stdout_bytes: The standard output as bytes.
    :param stderr_bytes: The standard error as bytes.
    :param output_bytes: A mix of ``stdout_bytes`` and ``stderr_bytes``, as the
        user would see  it in its terminal.
    :param return_value: The value returned from the invoked command.
    :param exit_code: The exit code as integer.
    :param exception: The exception that happened if one did.
    :param exc_info: Exception information (exception type, exception instance,
        traceback type).

    .. versionchanged:: 8.2
        ``stderr_bytes`` no longer optional, ``output_bytes`` introduced and
        ``mix_stderr`` has been removed.

    .. versionadded:: 8.0
        Added ``return_value``.
    """

    def __init__(
        self,
        runner: CliRunner,
        stdout_bytes: bytes,
        stderr_bytes: bytes,
        output_bytes: bytes,
        return_value: t.Any,
        exit_code: int,
        exception: BaseException | None,
        exc_info: tuple[type[BaseException], BaseException, TracebackType]
        | None = None,
    ):
        self.runner = runner
        self.stdout_bytes = stdout_bytes
        self.stderr_bytes = stderr_bytes
        self.output_bytes = output_bytes
        self.return_value = return_value
        self.exit_code = exit_code
        self.exception = exception
        self.exc_info = exc_info

    @property
    def output(self) -> str:
        """The terminal output as unicode string, as the user would see it.

        .. versionchanged:: 8.2
            No longer a proxy for ``self.stdout``. Now has its own independent stream
            that is mixing `<stdout>` and `<stderr>`, in the order they were written.
        """
        return self.output_bytes.decode(self.runner.charset, "replace").replace(
            "\r\n", "\n"
        )

    @property
    def stdout(self) -> str:
        """The standard output as unicode string."""
        return self.stdout_bytes.decode(self.runner.charset, "replace").replace(
            "\r\n", "\n"
        )

    @property
    def stderr(self) -> str:
        """The standard error as unicode string.

        .. versionchanged:: 8.2
            No longer raise an exception, always returns the `<stderr>` string.
        """
        return self.stderr_bytes.decode(self.runner.charset, "replace").replace(
            "\r\n", "\n"
        )

    def __repr__(self) -> str:
        exc_str = repr(self.exception) if self.exception else "okay"
        return f"<{type(self).__name__} {exc_str}>"


class CliRunner:
    """The CLI runner provides functionality to invoke a Click command line
    script for unittesting purposes in a isolated environment.  This only
    works in single-threaded systems without any concurrency as it changes the
    global interpreter state.

    :param charset: the character set for the input and output data.
    :param env: a dictionary with environment variables for overriding.
    :param echo_stdin: if this is set to `True`, then reading from `<stdin>` writes
                       to `<stdout>`.  This is useful for showing examples in
                       some circumstances.  Note that regular prompts
                       will automatically echo the input.
    :param catch_exceptions: Whether to catch any exceptions other than
                             ``SystemExit`` when running :meth:`~CliRunner.invoke`.

    .. versionchanged:: 8.2
        Added the ``catch_exceptions`` parameter.

    .. versionchanged:: 8.2
        ``mix_stderr`` parameter has been removed.
    """

    def __init__(
        self,
        charset: str = "utf-8",
        env: cabc.Mapping[str, str | None] | None = None,
        echo_stdin: bool = False,
        catch_exceptions: bool = True,
    ) -> None:
        self.charset = charset
        self.env: cabc.Mapping[str, str | None] = env or {}
        self.echo_stdin = echo_stdin
        self.catch_exceptions = catch_exceptions

    def get_default_prog_name(self, cli: Command) -> str:
        """Given a command object it will return the default program name
        for it.  The default is the `name` attribute or ``"root"`` if not
        set.
        """
        return cli.name or "root"

    def make_env(
        self, overrides: cabc.Mapping[str, str | None] | None = None
    ) -> cabc.Mapping[str, str | None]:
        """Returns the environment overrides for invoking a script."""
        rv = dict(self.env)
        if overrides:
            rv.update(overrides)
        return rv

    @contextlib.contextmanager
    def isolation(
        self,
        input: str | bytes | t.IO[t.Any] | None = None,
        env: cabc.Mapping[str, str | None] | None = None,
        color: bool = False,
    ) -> cabc.Iterator[tuple[io.BytesIO, io.BytesIO, io.BytesIO]]:
        """A context manager that sets up the isolation for invoking of a
        command line tool.  This sets up `<stdin>` with the given input data
        and `os.environ` with the overrides from the given dictionary.
        This also rebinds some internals in Click to be mocked (like the
        prompt functionality).

        This is automatically done in the :meth:`invoke` method.

        :param input: the input stream to put into `sys.stdin`.
        :param env: the environment overrides as dictionary.
        :param color: whether the output should contain color codes. The
                      application can still override this explicitly.

        .. versionadded:: 8.2
            An additional output stream is returned, which is a mix of
            `<stdout>` and `<stderr>` streams.

        .. versionchanged:: 8.2
            Always returns the `<stderr>` stream.

        .. versionchanged:: 8.0
            `<stderr>` is opened with ``errors="backslashreplace"``
            instead of the default ``"strict"``.

        .. versionchanged:: 4.0
            Added the ``color`` parameter.
        """
        bytes_input = make_input_stream(input, self.charset)
        echo_input = None

        old_stdin = sys.stdin
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        old_forced_width = formatting.FORCED_WIDTH
        formatting.FORCED_WIDTH = 80

        env = self.make_env(env)

        stream_mixer = StreamMixer()

        if self.echo_stdin:
            bytes_input = echo_input = t.cast(
                t.BinaryIO, EchoingStdin(bytes_input, stream_mixer.stdout)
            )

        sys.stdin = text_input = _NamedTextIOWrapper(
            bytes_input, encoding=self.charset, name="<stdin>", mode="r"
        )

        if self.echo_stdin:
            # Force unbuffered reads, otherwise TextIOWrapper reads a
            # large chunk which is echoed early.
            text_input._CHUNK_SIZE = 1  # type: ignore

        sys.stdout = _NamedTextIOWrapper(
            stream_mixer.stdout, encoding=self.charset, name="<stdout>", mode="w"
        )

        sys.stderr = _NamedTextIOWrapper(
            stream_mixer.stderr,
            encoding=self.charset,
            name="<stderr>",
            mode="w",
            errors="backslashreplace",
        )

        @_pause_echo(echo_input)  # type: ignore
        def visible_input(prompt: str | None = None) -> str:
            sys.stdout.write(prompt or "")
            val = next(text_input).rstrip("\r\n")
            sys.stdout.write(f"{val}\n")
            sys.stdout.flush()
            return val

        @_pause_echo(echo_input)  # type: ignore
        def hidden_input(prompt: str | None = None) -> str:
            sys.stdout.write(f"{prompt or ''}\n")
            sys.stdout.flush()
            return next(text_input).rstrip("\r\n")

        @_pause_echo(echo_input)  # type: ignore
        def _getchar(echo: bool) -> str:
            char = sys.stdin.read(1)

            if echo:
                sys.stdout.write(char)

            sys.stdout.flush()
            return char

        default_color = color

        def should_strip_ansi(
            stream: t.IO[t.Any] | None = None, color: bool | None = None
        ) -> bool:
            if color is None:
                return not default_color
            return not color

        old_visible_prompt_func = termui.visible_prompt_func
        old_hidden_prompt_func = termui.hidden_prompt_func
        old__getchar_func = termui._getchar
        old_should_strip_ansi = utils.should_strip_ansi  # type: ignore
        old__compat_should_strip_ansi = _compat.should_strip_ansi
        termui.visible_prompt_func = visible_input
        termui.hidden_prompt_func = hidden_input
        termui._getchar = _getchar
        utils.should_strip_ansi = should_strip_ansi  # type: ignore
        _compat.should_strip_ansi = should_strip_ansi

        old_env = {}
        try:
            for key, value in env.items():
                old_env[key] = os.environ.get(key)
                if value is None:
                    try:
                        del os.environ[key]
                    except Exception:
                        pass
                else:
                    os.environ[key] = value
            yield (stream_mixer.stdout, stream_mixer.stderr, stream_mixer.output)
        finally:
            for key, value in old_env.items():
                if value is None:
                    try:
                        del os.environ[key]
                    except Exception:
                        pass
                else:
                    os.environ[key] = value
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            sys.stdin = old_stdin
            termui.visible_prompt_func = old_visible_prompt_func
            termui.hidden_prompt_func = old_hidden_prompt_func
            termui._getchar = old__getchar_func
            utils.should_strip_ansi = old_should_strip_ansi  # type: ignore
            _compat.should_strip_ansi = old__compat_should_strip_ansi
            formatting.FORCED_WIDTH = old_forced_width

    def invoke(
        self,
        cli: Command,
        args: str | cabc.Sequence[str] | None = None,
        input: str | bytes | t.IO[t.Any] | None = None,
        env: cabc.Mapping[str, str | None] | None = None,
        catch_exceptions: bool | None = None,
        color: bool = False,
        **extra: t.Any,
    ) -> Result:
        """Invokes a command in an isolated environment.  The arguments are
        forwarded directly to the command line script, the `extra` keyword
        arguments are passed to the :meth:`~clickpkg.Command.main` function of
        the command.

        This returns a :class:`Result` object.

        :param cli: the command to invoke
        :param args: the arguments to invoke. It may be given as an iterable
                     or a string. When given as string it will be interpreted
                     as a Unix shell command. More details at
                     :func:`shlex.split`.
        :param input: the input data for `sys.stdin`.
        :param env: the environment overrides.
        :param catch_exceptions: Whether to catch any other exceptions than
                                 ``SystemExit``. If :data:`None`, the value
                                 from :class:`CliRunner` is used.
        :param extra: the keyword arguments to pass to :meth:`main`.
        :param color: whether the output should contain color codes. The
                      application can still override this explicitly.

        .. versionadded:: 8.2
            The result object has the ``output_bytes`` attribute with
            the mix of ``stdout_bytes`` and ``stderr_bytes``, as the user would
            see it in its terminal.

        .. versionchanged:: 8.2
            The result object always returns the ``stderr_bytes`` stream.

        .. versionchanged:: 8.0
            The result object has the ``return_value`` attribute with
            the value returned from the invoked command.

        .. versionchanged:: 4.0
            Added the ``color`` parameter.

        .. versionchanged:: 3.0
            Added the ``catch_exceptions`` parameter.

        .. versionchanged:: 3.0
            The result object has the ``exc_info`` attribute with the
            traceback if available.
        """
        exc_info = None
        if catch_exceptions is None:
            catch_exceptions = self.catch_exceptions

        with self.isolation(input=input, env=env, color=color) as outstreams:
            return_value = None
            exception: BaseException | None = None
            exit_code = 0

            if isinstance(args, str):
                args = shlex.split(args)

            try:
                prog_name = extra.pop("prog_name")
            except KeyError:
                prog_name = self.get_default_prog_name(cli)

            try:
                return_value = cli.main(args=args or (), prog_name=prog_name, **extra)
            except SystemExit as e:
                exc_info = sys.exc_info()
                e_code = t.cast("int | t.Any | None", e.code)

                if e_code is None:
                    e_code = 0

                if e_code != 0:
                    exception = e

                if not isinstance(e_code, int):
                    sys.stdout.write(str(e_code))
                    sys.stdout.write("\n")
                    e_code = 1

                exit_code = e_code

            except Exception as e:
                if not catch_exceptions:
                    raise
                exception = e
                exit_code = 1
                exc_info = sys.exc_info()
            finally:
                sys.stdout.flush()
                sys.stderr.flush()
                stdout = outstreams[0].getvalue()
                stderr = outstreams[1].getvalue()
                output = outstreams[2].getvalue()

        return Result(
            runner=self,
            stdout_bytes=stdout,
            stderr_bytes=stderr,
            output_bytes=output,
            return_value=return_value,
            exit_code=exit_code,
            exception=exception,
            exc_info=exc_info,  # type: ignore
        )

    @contextlib.contextmanager
    def isolated_filesystem(
        self, temp_dir: str | os.PathLike[str] | None = None
    ) -> cabc.Iterator[str]:
        """A context manager that creates a temporary directory and
        changes the current working directory to it. This isolates tests
        that affect the contents of the CWD to prevent them from
        interfering with each other.

        :param temp_dir: Create the temporary directory under this
            directory. If given, the created directory is not removed
            when exiting.

        .. versionchanged:: 8.0
            Added the ``temp_dir`` parameter.
        """
        cwd = os.getcwd()
        dt = tempfile.mkdtemp(dir=temp_dir)
        os.chdir(dt)

        try:
            yield dt
        finally:
            os.chdir(cwd)

            if temp_dir is None:
                try:
                    shutil.rmtree(dt)
                except OSError:
                    pass

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\scintilla\control.py ===
# An Python interface to the Scintilla control.
#
# Exposes Python classes that allow you to use Scintilla as
# a "standard" MFC edit control (eg, control.GetTextLength(), control.GetSel()
# plus many Scintilla specific features (eg control.SCIAddStyledText())

import array
import os
import struct

import win32api
import win32con
import win32ui
from pywin import default_scintilla_encoding
from pywin.mfc import window

from . import scintillacon

# Load Scintilla.dll to get access to the control.
# We expect to find this in the same directory as win32ui.pyd
dllid = None
if win32ui.debug:  # If running _d version of Pythonwin...
    try:
        dllid = win32api.LoadLibrary(
            os.path.join(os.path.split(win32ui.__file__)[0], "Scintilla_d.DLL")
        )
    except (
        win32api.error
    ):  # Not there - we don't _need_ a debug ver, so ignore this error.
        pass
if dllid is None:
    try:
        dllid = win32api.LoadLibrary(
            os.path.join(os.path.split(win32ui.__file__)[0], "Scintilla.DLL")
        )
    except win32api.error:
        pass
if dllid is None:
    # Still not there - let's see if Windows can find it by searching?
    dllid = win32api.LoadLibrary("Scintilla.DLL")

null_byte = b"\0"

## These are from Richedit.h - need to add to win32con or commctrl
EM_GETTEXTRANGE = 1099
EM_EXLINEFROMCHAR = 1078
EM_FINDTEXTEX = 1103
EM_GETSELTEXT = 1086
EM_EXSETSEL = win32con.WM_USER + 55


class ScintillaNotification:
    def __init__(self, **args):
        self.__dict__.update(args)


class ScintillaControlInterface:
    def SCIUnpackNotifyMessage(self, msg):
        format = "iiiiPiiiPPiiii"
        bytes = win32ui.GetBytes(msg, struct.calcsize(format))
        (
            position,
            ch,
            modifiers,
            modificationType,
            text_ptr,
            length,
            linesAdded,
            msg,
            wParam,
            lParam,
            line,
            foldLevelNow,
            foldLevelPrev,
            margin,
        ) = struct.unpack(format, bytes)
        return ScintillaNotification(
            position=position,
            ch=ch,
            modifiers=modifiers,
            modificationType=modificationType,
            text_ptr=text_ptr,
            length=length,
            linesAdded=linesAdded,
            msg=msg,
            wParam=wParam,
            lParam=lParam,
            line=line,
            foldLevelNow=foldLevelNow,
            foldLevelPrev=foldLevelPrev,
            margin=margin,
        )

    def SCIAddText(self, text):
        self.SendMessage(
            scintillacon.SCI_ADDTEXT, text.encode(default_scintilla_encoding)
        )

    def SCIAddStyledText(self, text, style=None):
        # If style is None, text is assumed to be a "native" Scintilla buffer.
        # If style is specified, text is a normal string, and the style is
        # assumed to apply to the entire string.
        if style is not None:
            text = list(map(lambda char, style=style: char + chr(style), text))
            text = "".join(text)
        self.SendMessage(
            scintillacon.SCI_ADDSTYLEDTEXT, text.encode(default_scintilla_encoding)
        )

    def SCIInsertText(self, text, pos=-1):
        # SCIInsertText allows unicode or bytes - but if they are bytes,
        # the caller must ensure it is encoded correctly.
        if isinstance(text, str):
            text = text.encode(default_scintilla_encoding)
        self.SendScintilla(scintillacon.SCI_INSERTTEXT, pos, text + null_byte)

    def SCISetSavePoint(self):
        self.SendScintilla(scintillacon.SCI_SETSAVEPOINT)

    def SCISetUndoCollection(self, collectFlag):
        self.SendScintilla(scintillacon.SCI_SETUNDOCOLLECTION, collectFlag)

    def SCIBeginUndoAction(self):
        self.SendScintilla(scintillacon.SCI_BEGINUNDOACTION)

    def SCIEndUndoAction(self):
        self.SendScintilla(scintillacon.SCI_ENDUNDOACTION)

    def SCIGetCurrentPos(self):
        return self.SendScintilla(scintillacon.SCI_GETCURRENTPOS)

    def SCIGetCharAt(self, pos):
        # Must ensure char is unsigned!
        return chr(self.SendScintilla(scintillacon.SCI_GETCHARAT, pos) & 0xFF)

    def SCIGotoLine(self, line):
        self.SendScintilla(scintillacon.SCI_GOTOLINE, line)

    def SCIBraceMatch(self, pos, maxReStyle):
        return self.SendScintilla(scintillacon.SCI_BRACEMATCH, pos, maxReStyle)

    def SCIBraceHighlight(self, pos, posOpposite):
        return self.SendScintilla(scintillacon.SCI_BRACEHIGHLIGHT, pos, posOpposite)

    def SCIBraceBadHighlight(self, pos):
        return self.SendScintilla(scintillacon.SCI_BRACEBADLIGHT, pos)

    ####################################
    # Styling
    # 	def SCIColourise(self, start=0, end=-1):
    #   NOTE - dependent on of we use builtin lexer, so handled below.
    def SCIGetEndStyled(self):
        return self.SendScintilla(scintillacon.SCI_GETENDSTYLED)

    def SCIStyleSetFore(self, num, v):
        return self.SendScintilla(scintillacon.SCI_STYLESETFORE, num, v)

    def SCIStyleSetBack(self, num, v):
        return self.SendScintilla(scintillacon.SCI_STYLESETBACK, num, v)

    def SCIStyleSetEOLFilled(self, num, v):
        return self.SendScintilla(scintillacon.SCI_STYLESETEOLFILLED, num, v)

    def SCIStyleSetFont(self, num, name, characterset=0):
        buff = (name + "\0").encode(default_scintilla_encoding)
        self.SendScintilla(scintillacon.SCI_STYLESETFONT, num, buff)
        self.SendScintilla(scintillacon.SCI_STYLESETCHARACTERSET, num, characterset)

    def SCIStyleSetBold(self, num, bBold):
        self.SendScintilla(scintillacon.SCI_STYLESETBOLD, num, bBold)

    def SCIStyleSetItalic(self, num, bItalic):
        self.SendScintilla(scintillacon.SCI_STYLESETITALIC, num, bItalic)

    def SCIStyleSetSize(self, num, size):
        self.SendScintilla(scintillacon.SCI_STYLESETSIZE, num, size)

    def SCIGetViewWS(self):
        return self.SendScintilla(scintillacon.SCI_GETVIEWWS)

    def SCISetViewWS(self, val):
        self.SendScintilla(scintillacon.SCI_SETVIEWWS, not (val == 0))
        self.InvalidateRect()

    def SCISetIndentationGuides(self, val):
        self.SendScintilla(scintillacon.SCI_SETINDENTATIONGUIDES, val)

    def SCIGetIndentationGuides(self):
        return self.SendScintilla(scintillacon.SCI_GETINDENTATIONGUIDES)

    def SCISetIndent(self, val):
        self.SendScintilla(scintillacon.SCI_SETINDENT, val)

    def SCIGetIndent(self, val):
        return self.SendScintilla(scintillacon.SCI_GETINDENT)

    def SCIGetViewEOL(self):
        return self.SendScintilla(scintillacon.SCI_GETVIEWEOL)

    def SCISetViewEOL(self, val):
        self.SendScintilla(scintillacon.SCI_SETVIEWEOL, not (val == 0))
        self.InvalidateRect()

    def SCISetTabWidth(self, width):
        self.SendScintilla(scintillacon.SCI_SETTABWIDTH, width, 0)

    def SCIStartStyling(self, pos, mask):
        self.SendScintilla(scintillacon.SCI_STARTSTYLING, pos, mask)

    def SCISetStyling(self, pos, attr):
        self.SendScintilla(scintillacon.SCI_SETSTYLING, pos, attr)

    def SCISetStylingEx(self, ray):  # ray is an array.
        address, length = ray.buffer_info()
        self.SendScintilla(scintillacon.SCI_SETSTYLINGEX, length, address)

    def SCIGetStyleAt(self, pos):
        return self.SendScintilla(scintillacon.SCI_GETSTYLEAT, pos)

    def SCISetMarginWidth(self, width):
        self.SendScintilla(scintillacon.SCI_SETMARGINWIDTHN, 1, width)

    def SCISetMarginWidthN(self, n, width):
        self.SendScintilla(scintillacon.SCI_SETMARGINWIDTHN, n, width)

    def SCISetFoldFlags(self, flags):
        self.SendScintilla(scintillacon.SCI_SETFOLDFLAGS, flags)

    # Markers
    def SCIMarkerDefineAll(self, markerNum, markerType, fore, back):
        self.SCIMarkerDefine(markerNum, markerType)
        self.SCIMarkerSetFore(markerNum, fore)
        self.SCIMarkerSetBack(markerNum, back)

    def SCIMarkerDefine(self, markerNum, markerType):
        self.SendScintilla(scintillacon.SCI_MARKERDEFINE, markerNum, markerType)

    def SCIMarkerSetFore(self, markerNum, fore):
        self.SendScintilla(scintillacon.SCI_MARKERSETFORE, markerNum, fore)

    def SCIMarkerSetBack(self, markerNum, back):
        self.SendScintilla(scintillacon.SCI_MARKERSETBACK, markerNum, back)

    def SCIMarkerAdd(self, lineNo, markerNum):
        self.SendScintilla(scintillacon.SCI_MARKERADD, lineNo, markerNum)

    def SCIMarkerDelete(self, lineNo, markerNum):
        self.SendScintilla(scintillacon.SCI_MARKERDELETE, lineNo, markerNum)

    def SCIMarkerDeleteAll(self, markerNum=-1):
        self.SendScintilla(scintillacon.SCI_MARKERDELETEALL, markerNum)

    def SCIMarkerGet(self, lineNo):
        return self.SendScintilla(scintillacon.SCI_MARKERGET, lineNo)

    def SCIMarkerNext(self, lineNo, markerNum):
        return self.SendScintilla(scintillacon.SCI_MARKERNEXT, lineNo, markerNum)

    def SCICancel(self):
        self.SendScintilla(scintillacon.SCI_CANCEL)

    # AutoComplete
    def SCIAutoCShow(self, text):
        if isinstance(text, (list, tuple)):
            text = " ".join(text)
        buff = (text + "\0").encode(default_scintilla_encoding)
        return self.SendScintilla(scintillacon.SCI_AUTOCSHOW, 0, buff)

    def SCIAutoCCancel(self):
        self.SendScintilla(scintillacon.SCI_AUTOCCANCEL)

    def SCIAutoCActive(self):
        return self.SendScintilla(scintillacon.SCI_AUTOCACTIVE)

    def SCIAutoCComplete(self):
        return self.SendScintilla(scintillacon.SCI_AUTOCCOMPLETE)

    def SCIAutoCStops(self, stops):
        buff = (stops + "\0").encode(default_scintilla_encoding)
        self.SendScintilla(scintillacon.SCI_AUTOCSTOPS, 0, buff)

    def SCIAutoCSetAutoHide(self, hide):
        self.SendScintilla(scintillacon.SCI_AUTOCSETAUTOHIDE, hide)

    def SCIAutoCSetFillups(self, fillups):
        self.SendScintilla(scintillacon.SCI_AUTOCSETFILLUPS, fillups)

    # Call tips
    def SCICallTipShow(self, text, pos=-1):
        if pos == -1:
            pos = self.GetSel()[0]
        buff = (text + "\0").encode(default_scintilla_encoding)
        self.SendScintilla(scintillacon.SCI_CALLTIPSHOW, pos, buff)

    def SCICallTipCancel(self):
        self.SendScintilla(scintillacon.SCI_CALLTIPCANCEL)

    def SCICallTipActive(self):
        return self.SendScintilla(scintillacon.SCI_CALLTIPACTIVE)

    def SCICallTipPosStart(self):
        return self.SendScintilla(scintillacon.SCI_CALLTIPPOSSTART)

    def SCINewline(self):
        self.SendScintilla(scintillacon.SCI_NEWLINE)

    # Lexer etc
    def SCISetKeywords(self, keywords, kw_list_no=0):
        buff = (keywords + "\0").encode(default_scintilla_encoding)
        self.SendScintilla(scintillacon.SCI_SETKEYWORDS, kw_list_no, buff)

    def SCISetProperty(self, name, value):
        name_buff = array.array("b", (name + "\0").encode(default_scintilla_encoding))
        val_buff = array.array(
            "b", (str(value) + "\0").encode(default_scintilla_encoding)
        )
        address_name_buffer = name_buff.buffer_info()[0]
        address_val_buffer = val_buff.buffer_info()[0]
        self.SendScintilla(
            scintillacon.SCI_SETPROPERTY, address_name_buffer, address_val_buffer
        )

    def SCISetStyleBits(self, nbits):
        self.SendScintilla(scintillacon.SCI_SETSTYLEBITS, nbits)

    # Folding
    def SCIGetFoldLevel(self, lineno):
        return self.SendScintilla(scintillacon.SCI_GETFOLDLEVEL, lineno)

    def SCIToggleFold(self, lineno):
        return self.SendScintilla(scintillacon.SCI_TOGGLEFOLD, lineno)

    def SCIEnsureVisible(self, lineno):
        self.SendScintilla(scintillacon.SCI_ENSUREVISIBLE, lineno)

    def SCIGetFoldExpanded(self, lineno):
        return self.SendScintilla(scintillacon.SCI_GETFOLDEXPANDED, lineno)

    # right edge
    def SCISetEdgeColumn(self, edge):
        self.SendScintilla(scintillacon.SCI_SETEDGECOLUMN, edge)

    def SCIGetEdgeColumn(self):
        return self.SendScintilla(scintillacon.SCI_GETEDGECOLUMN)

    def SCISetEdgeMode(self, mode):
        self.SendScintilla(scintillacon.SCI_SETEDGEMODE, mode)

    def SCIGetEdgeMode(self):
        return self.SendScintilla(scintillacon.SCI_GETEDGEMODE)

    def SCISetEdgeColor(self, color):
        self.SendScintilla(scintillacon.SCI_SETEDGECOLOUR, color)

    def SCIGetEdgeColor(self):
        return self.SendScintilla(scintillacon.SCI_GETEDGECOLOR)

    # Multi-doc
    def SCIGetDocPointer(self):
        return self.SendScintilla(scintillacon.SCI_GETDOCPOINTER)

    def SCISetDocPointer(self, p):
        return self.SendScintilla(scintillacon.SCI_SETDOCPOINTER, 0, p)

    def SCISetWrapMode(self, mode):
        return self.SendScintilla(scintillacon.SCI_SETWRAPMODE, mode)

    def SCIGetWrapMode(self):
        return self.SendScintilla(scintillacon.SCI_GETWRAPMODE)


class CScintillaEditInterface(ScintillaControlInterface):
    def close(self):
        self.colorizer = None

    def Clear(self):
        self.SendScintilla(win32con.WM_CLEAR)

    def FindText(self, flags, range, findText):
        """LPARAM for EM_FINDTEXTEX:
                typedef struct _findtextex {
                CHARRANGE chrg;
                LPCTSTR lpstrText;
                CHARRANGE chrgText;} FINDTEXTEX;
        typedef struct _charrange {
                LONG cpMin;
                LONG cpMax;} CHARRANGE;
        """
        findtextex_fmt = "llPll"
        ## Scintilla does not handle unicode in EM_FINDTEXT msg (FINDTEXTEX struct)
        txt_buff = (findText + "\0").encode(default_scintilla_encoding)
        txt_array = array.array("b", txt_buff)
        ft_buff = struct.pack(
            findtextex_fmt, range[0], range[1], txt_array.buffer_info()[0], 0, 0
        )
        ft_array = array.array("b", ft_buff)
        rc = self.SendScintilla(EM_FINDTEXTEX, flags, ft_array.buffer_info()[0])
        ftUnpacked = struct.unpack(findtextex_fmt, ft_array)
        return rc, (ftUnpacked[3], ftUnpacked[4])

    def GetSel(self):
        currentPos = self.SendScintilla(scintillacon.SCI_GETCURRENTPOS)
        anchorPos = self.SendScintilla(scintillacon.SCI_GETANCHOR)
        if currentPos < anchorPos:
            return (currentPos, anchorPos)
        else:
            return (anchorPos, currentPos)
        return currentPos

    def GetSelText(self):
        start, end = self.GetSel()
        txtBuf = array.array("b", null_byte * (end - start + 1))
        addressTxtBuf = txtBuf.buffer_info()[0]
        # EM_GETSELTEXT is documented as returning the number of chars
        # not including the NULL, but scintilla includes the NULL.  A
        # quick glance at the scintilla impl doesn't make this
        # obvious - the NULL is included in the 'selection' object
        # and reflected in the length of that 'selection' object.
        # I expect that is a bug in scintilla and may be fixed by now,
        # but we just blindly assume that the last char is \0 and
        # strip it.
        self.SendScintilla(EM_GETSELTEXT, 0, addressTxtBuf)
        return txtBuf.tobytes()[:-1].decode(default_scintilla_encoding)

    def SetSel(self, start=0, end=None):
        if isinstance(start, tuple):
            assert (
                end is None
            ), "If you pass a point in the first param, the second must be None"
            start, end = start
        elif end is None:
            end = start
        if start < 0:
            start = self.GetTextLength()
        if end < 0:
            end = self.GetTextLength()
        assert start <= self.GetTextLength(), "The start postion is invalid (%d/%d)" % (
            start,
            self.GetTextLength(),
        )
        assert end <= self.GetTextLength(), "The end postion is invalid (%d/%d)" % (
            end,
            self.GetTextLength(),
        )
        cr = struct.pack("ll", start, end)
        crBuff = array.array("b", cr)
        addressCrBuff = crBuff.buffer_info()[0]
        rc = self.SendScintilla(EM_EXSETSEL, 0, addressCrBuff)

    def GetLineCount(self):
        return self.SendScintilla(win32con.EM_GETLINECOUNT)

    def LineFromChar(self, charPos=-1):
        if charPos == -1:
            charPos = self.GetSel()[0]
        assert (
            charPos >= 0 and charPos <= self.GetTextLength()
        ), f"The charPos postion ({charPos}) is invalid (max={self.GetTextLength()})"
        # return self.SendScintilla(EM_EXLINEFROMCHAR, charPos)
        # EM_EXLINEFROMCHAR puts charPos in lParam, not wParam
        return self.SendScintilla(EM_EXLINEFROMCHAR, 0, charPos)

    def LineIndex(self, line):
        return self.SendScintilla(win32con.EM_LINEINDEX, line)

    def ScrollCaret(self):
        return self.SendScintilla(win32con.EM_SCROLLCARET)

    def GetCurLineNumber(self):
        return self.LineFromChar(self.SCIGetCurrentPos())

    def GetTextLength(self):
        return self.SendScintilla(scintillacon.SCI_GETTEXTLENGTH)

    def GetTextRange(self, start=0, end=-1, decode=True):
        if end == -1:
            end = self.SendScintilla(scintillacon.SCI_GETTEXTLENGTH)
        assert end >= start, "Negative index requested (%d/%d)" % (start, end)
        assert (
            start >= 0 and start <= self.GetTextLength()
        ), "The start postion is invalid"
        assert end >= 0 and end <= self.GetTextLength(), "The end postion is invalid"
        initer = null_byte * (end - start + 1)
        buff = array.array("b", initer)
        addressBuffer = buff.buffer_info()[0]
        tr = struct.pack("llP", start, end, addressBuffer)
        trBuff = array.array("b", tr)
        addressTrBuff = trBuff.buffer_info()[0]
        num_bytes = self.SendScintilla(EM_GETTEXTRANGE, 0, addressTrBuff)
        ret = buff.tobytes()[:num_bytes]
        if decode:
            ret = ret.decode(default_scintilla_encoding)
        return ret

    def ReplaceSel(self, str):
        buff = (str + "\0").encode(default_scintilla_encoding)
        self.SendScintilla(scintillacon.SCI_REPLACESEL, 0, buff)

    def GetLine(self, line=-1):
        if line == -1:
            line = self.GetCurLineNumber()
        start = self.LineIndex(line)
        end = self.LineIndex(line + 1)
        return self.GetTextRange(start, end)

    def SetReadOnly(self, flag=1):
        return self.SendScintilla(win32con.EM_SETREADONLY, flag)

    def LineScroll(self, lines, cols=0):
        return self.SendScintilla(win32con.EM_LINESCROLL, cols, lines)

    def GetFirstVisibleLine(self):
        return self.SendScintilla(win32con.EM_GETFIRSTVISIBLELINE)

    def SetWordWrap(self, mode):
        if mode != win32ui.CRichEditView_WrapNone:
            raise ValueError("We don't support word-wrap (I don't think :-)")


class CScintillaColorEditInterface(CScintillaEditInterface):
    ################################
    # Plug-in colorizer support
    def _GetColorizer(self):
        if not hasattr(self, "colorizer"):
            self.colorizer = self._MakeColorizer()
        return self.colorizer

    def _MakeColorizer(self):
        # Give parent a chance to hook.
        parent_func = getattr(self.GetParentFrame(), "_MakeColorizer", None)
        if parent_func is not None:
            return parent_func()
        from . import formatter

        ##		return formatter.PythonSourceFormatter(self)
        return formatter.BuiltinPythonSourceFormatter(self)

    def Colorize(self, start=0, end=-1):
        c = self._GetColorizer()
        if c is not None:
            c.Colorize(start, end)

    def ApplyFormattingStyles(self, bReload=1):
        c = self._GetColorizer()
        if c is not None:
            c.ApplyFormattingStyles(bReload)

    # The Parent window will normally hook
    def HookFormatter(self, parent=None):
        c = self._GetColorizer()
        if c is not None:  # No need if we have no color!
            c.HookFormatter(parent)


class CScintillaEdit(window.Wnd, CScintillaColorEditInterface):
    def __init__(self, wnd=None):
        if wnd is None:
            wnd = win32ui.CreateWnd()
        window.Wnd.__init__(self, wnd)

    def SendScintilla(self, msg, w=0, l=0):
        return self.SendMessage(msg, w, l)

    def CreateWindow(self, style, rect, parent, id):
        self._obj_.CreateWindow("Scintilla", "Scintilla", style, rect, parent, id, None)

# === NexusCore/openenv\Lib\site-packages\win32comext\adsi\demos\scp.py ===
"""A re-implementation of the MS DirectoryService samples related to services.

* Adds and removes an ActiveDirectory "Service Connection Point",
  including managing the security on the object.
* Creates and registers Service Principal Names.
* Changes the username for a domain user.

Some of these functions are likely to become move to a module - but there
is also a little command-line-interface to try these functions out.

For example:

scp.py --account-name=domain\\user --service-class=PythonScpTest \\
       --keyword=foo --keyword=bar --binding-string=bind_info \\
       ScpCreate SpnCreate SpnRegister

would:
* Attempt to delete a Service Connection Point for the service class
  'PythonScpTest'
* Attempt to create a Service Connection Point for that class, with 2
  keywords and a binding string of 'bind_info'
* Create a Service Principal Name for the service and register it

to undo those changes, you could execute:

scp.py --account-name=domain\\user --service-class=PythonScpTest \\
       SpnCreate SpnUnregister ScpDelete

which will:
* Create a SPN
* Unregister that SPN from the Active Directory.
* Delete the Service Connection Point

Executing with --test will create and remove one of everything.
"""

import optparse
import textwrap
import traceback

import ntsecuritycon as dscon
import win32api
import win32con
import win32security
import winerror
from win32com.adsi import adsi
from win32com.adsi.adsicon import *
from win32com.client import Dispatch

verbose = 1
g_createdSCP = None
g_createdSPNs = []
g_createdSPNLast = None

import logging

logger = logging  # use logging module global methods for now.

# still a bit confused about log(n, ...) vs logger.info/debug()


# Returns distinguished name of SCP.
def ScpCreate(
    service_binding_info,
    service_class_name,  # Service class string to store in SCP.
    account_name=None,  # Logon account that needs access to SCP.
    container_name=None,
    keywords=None,
    object_class="serviceConnectionPoint",
    dns_name_type="A",
    dn=None,
    dns_name=None,
):
    container_name = container_name or service_class_name
    if not dns_name:
        # Get the DNS name of the local computer
        dns_name = win32api.GetComputerNameEx(win32con.ComputerNameDnsFullyQualified)
    # Get the distinguished name of the computer object for the local computer
    if dn is None:
        dn = win32api.GetComputerObjectName(win32con.NameFullyQualifiedDN)

    # Compose the ADSpath and bind to the computer object for the local computer
    comp = adsi.ADsGetObject("LDAP://" + dn, adsi.IID_IDirectoryObject)

    # Publish the SCP as a child of the computer object
    keywords = keywords or []
    # Fill in the attribute values to be stored in the SCP.
    attrs = [
        ("cn", ADS_ATTR_UPDATE, ADSTYPE_CASE_IGNORE_STRING, (container_name,)),
        ("objectClass", ADS_ATTR_UPDATE, ADSTYPE_CASE_IGNORE_STRING, (object_class,)),
        ("keywords", ADS_ATTR_UPDATE, ADSTYPE_CASE_IGNORE_STRING, keywords),
        ("serviceDnsName", ADS_ATTR_UPDATE, ADSTYPE_CASE_IGNORE_STRING, (dns_name,)),
        (
            "serviceDnsNameType",
            ADS_ATTR_UPDATE,
            ADSTYPE_CASE_IGNORE_STRING,
            (dns_name_type,),
        ),
        (
            "serviceClassName",
            ADS_ATTR_UPDATE,
            ADSTYPE_CASE_IGNORE_STRING,
            (service_class_name,),
        ),
        (
            "serviceBindingInformation",
            ADS_ATTR_UPDATE,
            ADSTYPE_CASE_IGNORE_STRING,
            (service_binding_info,),
        ),
    ]
    new = comp.CreateDSObject("cn=" + container_name, attrs)
    logger.info("New connection point is at %s", container_name)
    # Wrap in a usable IDispatch object.
    new = Dispatch(new)
    # And allow access to the SCP for the specified account name
    AllowAccessToScpProperties(account_name, new)
    return new


def ScpDelete(container_name, dn=None):
    if dn is None:
        dn = win32api.GetComputerObjectName(win32con.NameFullyQualifiedDN)
    logger.debug("Removing connection point '%s' from %s", container_name, dn)

    # Compose the ADSpath and bind to the computer object for the local computer
    comp = adsi.ADsGetObject("LDAP://" + dn, adsi.IID_IDirectoryObject)
    comp.DeleteDSObject("cn=" + container_name)
    logger.info("Deleted service connection point '%s'", container_name)


# This function is described in detail in the MSDN article titled
# "Enabling Service Account to Access SCP Properties"
# From that article:
# The following sample code sets a pair of ACEs on a service connection point
# (SCP) object. The ACEs grant read/write access to the user or computer account
# under which the service instance will be running. Your service installation
# program calls this code to ensure that the service will be allowed to update
# its properties at run time. If you don't set ACEs like these, your service
# will get access-denied errors if it tries to modify the SCP's properties.
#
# The code uses the IADsSecurityDescriptor, IADsAccessControlList, and
# IADsAccessControlEntry interfaces to do the following:
# * Get the SCP object's security descriptor.
# * Set ACEs in the DACL of the security descriptor.
# * Set the security descriptor back on the SCP object.


def AllowAccessToScpProperties(
    accountSAM,  # Service account to allow access.
    scpObject,  # The IADs SCP object.
    schemaIDGUIDs=(  # Attributes to allow write-access to.
        "{28630eb8-41d5-11d1-a9c1-0000f80367c1}",  # serviceDNSName
        "{b7b1311c-b82e-11d0-afee-0000f80367c1}",  # serviceBindingInformation
    ),
):
    # If no service account is specified, service runs under LocalSystem.
    # So allow access to the computer account of the service's host.
    if accountSAM:
        trustee = accountSAM
    else:
        # Get the SAM account name of the computer object for the server.
        trustee = win32api.GetComputerObjectName(win32con.NameSamCompatible)

    # Get the nTSecurityDescriptor attribute
    attribute = "nTSecurityDescriptor"
    sd = getattr(scpObject, attribute)
    acl = sd.DiscretionaryAcl

    for sguid in schemaIDGUIDs:
        ace = Dispatch(adsi.CLSID_AccessControlEntry)

        # Set the properties of the ACE.
        # Allow read and write access to the property.
        ace.AccessMask = ADS_RIGHT_DS_READ_PROP | ADS_RIGHT_DS_WRITE_PROP

        # Set the trustee, which is either the service account or the
        # host computer account.
        ace.Trustee = trustee

        # Set the ACE type.
        ace.AceType = ADS_ACETYPE_ACCESS_ALLOWED_OBJECT

        # Set AceFlags to zero because ACE is not inheritable.
        ace.AceFlags = 0

        # Set Flags to indicate an ACE that protects a specified object.
        ace.Flags = ADS_FLAG_OBJECT_TYPE_PRESENT

        # Set ObjectType to the schemaIDGUID of the attribute.
        ace.ObjectType = sguid

        # Add the ACEs to the DACL.
        acl.AddAce(ace)

    # Write the modified DACL back to the security descriptor.
    sd.DiscretionaryAcl = acl
    # Write the ntSecurityDescriptor property to the property cache.
    setattr(scpObject, attribute, sd)
    # SetInfo updates the SCP object in the directory.
    scpObject.SetInfo()
    logger.info("Set security on object for account %r", trustee)


# Service Principal Names functions from the same sample.
# The example calls the DsWriteAccountSpn function, which stores the SPNs in
# Microsoft Active Directory under the servicePrincipalName attribute of the
# account object specified by the serviceAcctDN parameter. The account object
# corresponds to the logon account specified in the CreateService call for this
# service instance. If the logon account is a domain user account,
# serviceAcctDN must be the distinguished name of the account object in
# Active Directory for that user account. If the service's logon account is the
# LocalSystem account, serviceAcctDN must be the distinguished name of the
# computer account object for the host computer on which the service is
# installed. win32api.TranslateNames and win32security.DsCrackNames can
# be used to convert a domain\account format name to a distinguished name.
def SpnRegister(
    serviceAcctDN,  # DN of the service's logon account
    spns,  # List of SPNs to register
    operation,  # Add, replace, or delete SPNs
):
    assert not isinstance(spns, str) and hasattr(spns, "__iter__"), (
        "spns must be a sequence of strings (got %r)" % spns
    )
    # Bind to a domain controller.
    # Get the domain for the current user.
    samName = win32api.GetUserNameEx(win32api.NameSamCompatible)
    samName = samName.split("\\", 1)[0]

    if not serviceAcctDN:
        # Get the SAM account name of the computer object for the server.
        serviceAcctDN = win32api.GetComputerObjectName(win32con.NameFullyQualifiedDN)
    logger.debug("SpnRegister using DN '%s'", serviceAcctDN)

    # Get the name of a domain controller in that domain.
    info = win32security.DsGetDcName(
        domainName=samName,
        flags=dscon.DS_IS_FLAT_NAME
        | dscon.DS_RETURN_DNS_NAME
        | dscon.DS_DIRECTORY_SERVICE_REQUIRED,
    )
    # Bind to the domain controller.
    handle = win32security.DsBind(info["DomainControllerName"])

    # Write the SPNs to the service account or computer account.
    logger.debug("DsWriteAccountSpn with spns %s")
    win32security.DsWriteAccountSpn(
        handle,  # handle to the directory
        operation,  # Add or remove SPN from account's existing SPNs
        serviceAcctDN,  # DN of service account or computer account
        spns,
    )  # names

    # Unbind the DS in any case (but Python would do it anyway)
    handle.Close()


def UserChangePassword(username_dn, new_password):
    # set the password on the account.
    # Use the distinguished name to bind to the account object.
    accountPath = "LDAP://" + username_dn
    user = adsi.ADsGetObject(accountPath, adsi.IID_IADsUser)

    # Set the password on the account.
    user.SetPassword(new_password)


# functions related to the command-line interface
def log(level, msg, *args):
    if verbose >= level:
        print(msg % args)


class _NoDefault:
    pass


def _get_option(po, opt_name, default=_NoDefault):
    parser, options = po
    ret = getattr(options, opt_name, default)
    if not ret and default is _NoDefault:
        parser.error("The '%s' option must be specified for this operation" % opt_name)
    if not ret:
        ret = default
    return ret


def _option_error(po, why):
    parser = po[0]
    parser.error(why)


def do_ScpCreate(po):
    """Create a Service Connection Point"""
    global g_createdSCP
    scp = ScpCreate(
        _get_option(po, "binding_string"),
        _get_option(po, "service_class"),
        _get_option(po, "account_name_sam", None),
        keywords=_get_option(po, "keywords", None),
    )
    g_createdSCP = scp
    return scp.distinguishedName


def do_ScpDelete(po):
    """Delete a Service Connection Point"""
    sc = _get_option(po, "service_class")
    try:
        ScpDelete(sc)
    except adsi.error as details:
        if details[0] != winerror.ERROR_DS_OBJ_NOT_FOUND:
            raise
        log(2, "ScpDelete ignoring ERROR_DS_OBJ_NOT_FOUND for service-class '%s'", sc)
    return sc


def do_SpnCreate(po):
    """Create a Service Principal Name"""
    # The 'service name' is the dn of our scp.
    if g_createdSCP is None:
        # Could accept an arg to avoid this?
        _option_error(po, "ScpCreate must have been specified before SpnCreate")
    # Create a Service Principal Name"
    spns = win32security.DsGetSpn(
        dscon.DS_SPN_SERVICE,
        _get_option(po, "service_class"),
        g_createdSCP.distinguishedName,
        _get_option(po, "port", 0),
        None,
        None,
    )
    spn = spns[0]
    log(2, "Created SPN: %s", spn)
    global g_createdSPNLast
    g_createdSPNLast = spn
    g_createdSPNs.append(spn)
    return spn


def do_SpnRegister(po):
    """Register a previously created Service Principal Name"""
    if not g_createdSPNLast:
        _option_error(po, "SpnCreate must appear before SpnRegister")

    SpnRegister(
        _get_option(po, "account_name_dn", None),
        (g_createdSPNLast,),
        dscon.DS_SPN_ADD_SPN_OP,
    )
    return g_createdSPNLast


def do_SpnUnregister(po):
    """Unregister a previously created Service Principal Name"""
    if not g_createdSPNLast:
        _option_error(po, "SpnCreate must appear before SpnUnregister")
    SpnRegister(
        _get_option(po, "account_name_dn", None),
        (g_createdSPNLast,),
        dscon.DS_SPN_DELETE_SPN_OP,
    )
    return g_createdSPNLast


def do_UserChangePassword(po):
    """Change the password for a specified user"""
    UserChangePassword(_get_option(po, "account_name_dn"), _get_option(po, "password"))
    return "Password changed OK"


handlers = (
    ("ScpCreate", do_ScpCreate),
    ("ScpDelete", do_ScpDelete),
    ("SpnCreate", do_SpnCreate),
    ("SpnRegister", do_SpnRegister),
    ("SpnUnregister", do_SpnUnregister),
    ("UserChangePassword", do_UserChangePassword),
)


class HelpFormatter(optparse.IndentedHelpFormatter):
    def format_description(self, description):
        return description


def main():
    global verbose
    _handlers_dict = {}

    arg_descs = []
    for arg, func in handlers:
        this_desc = "\n".join(textwrap.wrap(func.__doc__, subsequent_indent=" " * 8))
        arg_descs.append(f"  {arg}: {this_desc}")
        _handlers_dict[arg.lower()] = func

    description = __doc__ + "\ncommands:\n" + "\n".join(arg_descs) + "\n"

    parser = optparse.OptionParser(
        usage="%prog [options] command ...",
        description=description,
        formatter=HelpFormatter(),
    )

    parser.add_option(
        "-v",
        action="count",
        dest="verbose",
        default=1,
        help="increase the verbosity of status messages",
    )

    parser.add_option(
        "-q", "--quiet", action="store_true", help="Don't print any status messages"
    )

    parser.add_option(
        "-t",
        "--test",
        action="store_true",
        help="Execute a mini-test suite, providing defaults for most options and args",
    )

    parser.add_option(
        "",
        "--show-tracebacks",
        action="store_true",
        help="Show the tracebacks for any exceptions",
    )

    parser.add_option("", "--service-class", help="The service class name to use")

    parser.add_option(
        "", "--port", default=0, help="The port number to associate with the SPN"
    )

    parser.add_option(
        "", "--binding-string", help="The binding string to use for SCP creation"
    )

    parser.add_option(
        "", "--account-name", help="The account name to use (default is LocalSystem)"
    )

    parser.add_option("", "--password", help="The password to set.")

    parser.add_option(
        "",
        "--keyword",
        action="append",
        dest="keywords",
        help="""A keyword to add to the SCP.  May be specified
                              multiple times""",
    )

    parser.add_option(
        "",
        "--log-level",
        help="""The log-level to use - may be a number or a logging
                             module constant""",
        default=str(logging.WARNING),
    )

    options, args = parser.parse_args()
    po = (parser, options)
    # fixup misc
    try:
        options.port = int(options.port)
    except (TypeError, ValueError):
        parser.error("--port must be numeric")
    # fixup log-level
    try:
        log_level = int(options.log_level)
    except (TypeError, ValueError):
        try:
            log_level = int(getattr(logging, options.log_level.upper()))
        except (ValueError, TypeError, AttributeError):
            parser.error("Invalid --log-level value")
    try:
        sl = logger.setLevel
        # logger is a real logger
    except AttributeError:
        # logger is logging module
        sl = logging.getLogger().setLevel
    sl(log_level)
    # Check -q/-v
    if options.quiet and options.verbose:
        parser.error("Can't specify --quiet and --verbose")
    if options.quiet:
        options.verbose -= 1
    verbose = options.verbose
    # --test
    if options.test:
        if args:
            parser.error("Can't specify args with --test")

        args = "ScpDelete ScpCreate SpnCreate SpnRegister SpnUnregister ScpDelete"
        log(1, "--test - pretending args are:\n %s", args)
        args = args.split()
        if not options.service_class:
            options.service_class = "PythonScpTest"
            log(2, "--test: --service-class=%s", options.service_class)
        if not options.keywords:
            options.keywords = "Python Powered".split()
            log(2, "--test: --keyword=%s", options.keywords)
        if not options.binding_string:
            options.binding_string = "test binding string"
            log(2, "--test: --binding-string=%s", options.binding_string)

    # check args
    if not args:
        parser.error("No command specified (use --help for valid commands)")
    for arg in args:
        if arg.lower() not in _handlers_dict:
            parser.error("Invalid command '%s' (use --help for valid commands)" % arg)

    # Patch up account-name.
    if options.account_name:
        log(2, "Translating account name '%s'", options.account_name)
        options.account_name_sam = win32security.TranslateName(
            options.account_name, win32api.NameUnknown, win32api.NameSamCompatible
        )
        log(2, "NameSamCompatible is '%s'", options.account_name_sam)
        options.account_name_dn = win32security.TranslateName(
            options.account_name, win32api.NameUnknown, win32api.NameFullyQualifiedDN
        )
        log(2, "NameFullyQualifiedDNis '%s'", options.account_name_dn)

    # do it.
    for arg in args:
        handler = _handlers_dict[arg.lower()]  # already been validated
        if handler is None:
            parser.error("Invalid command '%s'" % arg)
        err_msg = None
        try:
            try:
                log(2, "Executing '%s'...", arg)
                result = handler(po)
                log(1, "%s: %s", arg, result)
            except:
                if options.show_tracebacks:
                    print("--show-tracebacks specified - dumping exception")
                    traceback.print_exc()
                raise
        except adsi.error as xxx_todo_changeme:
            (hr, desc, exc, argerr) = xxx_todo_changeme.args
            if exc:
                extra_desc = exc[2]
            else:
                extra_desc = ""
            err_msg = desc
            if extra_desc:
                err_msg += "\n\t" + extra_desc
        except win32api.error as xxx_todo_changeme1:
            (hr, func, msg) = xxx_todo_changeme1.args
            err_msg = msg
        if err_msg:
            log(1, "Command '%s' failed: %s", arg, err_msg)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("*** Interrupted")

# === NexusCore/openenv\Lib\site-packages\uritemplate\variable.py ===
"""

uritemplate.variable
====================

This module contains the URIVariable class which powers the URITemplate class.

What treasures await you:

- URIVariable class

You see a hammer in front of you.
What do you do?
>

"""

import collections.abc
import enum
import string
import typing as t
import urllib.parse

ScalarVariableValue = t.Union[int, float, complex, str, None]
VariableValue = t.Union[
    t.Sequence[ScalarVariableValue],
    t.List[ScalarVariableValue],
    t.Mapping[str, ScalarVariableValue],
    t.Tuple[str, ScalarVariableValue],
    ScalarVariableValue,
]
VariableValueDict = t.Dict[str, VariableValue]


_UNRESERVED_CHARACTERS: t.Final[str] = (
    f"{string.ascii_letters}{string.digits}~-_."
)
_GEN_DELIMS: t.Final[str] = ":/?#[]@"
_SUB_DELIMS: t.Final[str] = "!$&'()*+,;="
_RESERVED_CHARACTERS: t.Final[str] = f"{_GEN_DELIMS}{_SUB_DELIMS}"


class Operator(enum.Enum):
    # Section 2.2. Expressions
    #      expression    =  "{" [ operator ] variable-list "}"
    #      operator      =  op-level2 / op-level3 / op-reserve
    #      op-level2     =  "+" / "#"
    #      op-level3     =  "." / "/" / ";" / "?" / "&"
    #      op-reserve    =  "=" / "," / "!" / "@" / "|"
    default = ""  # 3.2.2. Simple String Expansiona: {var}
    # Operator Level 2 (op-level2)
    reserved = "+"  # 3.2.3. Reserved Expansion: {+var}
    fragment = "#"  # 3.2.4. Fragment Expansion: {#var}
    # Operator Level 3 (op-level3)
    # 3.2.5. Label Expansion with Dot-Prefix: {.var}
    label_with_dot_prefix = "."
    path_segment = "/"  # 3.2.6. Path Segment Expansion: {/var}
    path_style_parameter = (
        ";"  # 3.2.7. Path-Style Parameter Expansion: {;var}
    )
    form_style_query = "?"  # 3.2.8. Form-Style Query Expansion: {?var}
    # 3.2.9. Form-Style Query Continuation: {&var}
    form_style_query_continuation = "&"
    # Reserved Operators (op-reserve)
    reserved_eq = "="
    reserved_comma = ","
    reserved_bang = "!"
    reserved_at = "@"
    reserved_pipe = "|"

    def reserved_characters(self) -> str:
        # TODO: Re-enable after un-commenting 3.9
        # match self:
        #     case Operator.reserved:
        #         return _RESERVED_CHARACTERS + "%"
        #     # case Operator.default | Operator.reserved | Operator.fragment:
        #     case Operator.fragment:
        #         return _RESERVED_CHARACTERS
        #     case _:
        #         return ""
        if self == Operator.reserved:
            return _RESERVED_CHARACTERS + "%"
        if self == Operator.fragment:
            return _RESERVED_CHARACTERS
        return ""

    def expansion_separator(self) -> str:
        """Identify the separator used during expansion.

        Per `Section 3.2.1. Variable Expansion`_:

        ======  ===========    =========
        Type    Separator
        ======  ===========    =========
                ``","``        (default)
        ``+``   ``","``
        ``#``   ``","``
        ``.``   ``"."``
        ``/``   ``"/"``
        ``;``   ``";"``
        ``?``   ``"&"``
        ``&``   ``"&"``
        ======  ===========    =========

        .. _`Section 3.2.1. Variable Expansion`:
            https://www.rfc-editor.org/rfc/rfc6570#section-3.2.1
        """
        if self == Operator.label_with_dot_prefix:
            return "."
        if self == Operator.path_segment:
            return "/"
        if self == Operator.path_style_parameter:
            return ";"
        if (
            self == Operator.form_style_query
            or self == Operator.form_style_query_continuation
        ):
            return "&"
        # if self == Operator.reserved or self == Operator.fragment:
        #     return ","
        return ","
        # match self:
        #     case Operator.label_with_dot_prefix:
        #         return "."
        #     case Operator.path_segment:
        #         return "/"
        #     case Operator.path_style_parameter:
        #         return ";"
        #     case (
        #         Operator.form_style_query |
        #         Operator.form_style_query_continuation
        #     ):
        #         return "&"
        #     case Operator.reserved | Operator.fragment:
        #         return ","
        #     case _:
        #         return ","

    def variable_prefix(self) -> str:
        if self == Operator.reserved:
            return ""
        return t.cast(str, self.value)
        # match self:
        #     case Operator.reserved:
        #         return ""
        #     case _:
        #         return t.cast(str, self.value)

    def _always_quote(self, value: str) -> str:
        return quote(value, "")

    def _only_quote_unquoted_characters(self, value: str) -> str:
        if urllib.parse.unquote(value) == value:
            return quote(value, _RESERVED_CHARACTERS)
        return value

    def quote(self, value: t.Any) -> str:
        if not isinstance(value, (str, bytes)):
            value = str(value)
        if isinstance(value, bytes):
            value = value.decode()

        if self == Operator.reserved or self == Operator.fragment:
            return self._only_quote_unquoted_characters(value)
        return self._always_quote(value)

    @staticmethod
    def from_string(s: str) -> "Operator":
        return _operators.get(s, Operator.default)


_operators: t.Final[t.Dict[str, Operator]] = {
    "+": Operator.reserved,
    "#": Operator.fragment,
    ".": Operator.label_with_dot_prefix,
    "/": Operator.path_segment,
    ";": Operator.path_style_parameter,
    "?": Operator.form_style_query,
    "&": Operator.form_style_query_continuation,
    "!": Operator.reserved_bang,
    "|": Operator.reserved_pipe,
    "@": Operator.reserved_at,
    "=": Operator.reserved_eq,
    ",": Operator.reserved_comma,
}


class URIVariable:
    """This object validates everything inside the URITemplate object.

    It validates template expansions and will truncate length as decided by
    the template.

    Please note that just like the :class:`URITemplate <URITemplate>`, this
    object's ``__str__`` and ``__repr__`` methods do not return the same
    information. Calling ``str(var)`` will return the original variable.

    This object does the majority of the heavy lifting. The ``URITemplate``
    object finds the variables in the URI and then creates ``URIVariable``
    objects.  Expansions of the URI are handled by each ``URIVariable``
    object. ``URIVariable.expand()`` returns a dictionary of the original
    variable and the expanded value. Check that method's documentation for
    more information.

    """

    def __init__(self, var: str):
        #: The original string that comes through with the variable
        self.original: str = var
        #: The operator for the variable
        self.operator: Operator = Operator.default
        #: List of variables in this variable
        self.variables: t.List[t.Tuple[str, t.MutableMapping[str, t.Any]]] = (
            []
        )
        #: List of variable names
        self.variable_names: t.List[str] = []
        #: List of defaults passed in
        self.defaults: t.MutableMapping[str, ScalarVariableValue] = {}
        # Parse the variable itself.
        self.parse()

    def __repr__(self) -> str:
        return "URIVariable(%s)" % self

    def __str__(self) -> str:
        return self.original

    def parse(self) -> None:
        """Parse the variable.

        This finds the:
            - operator,
            - set of safe characters,
            - variables, and
            - defaults.

        """
        var_list_str = self.original
        if (operator_str := self.original[0]) in _operators:
            self.operator = Operator.from_string(operator_str)
            var_list_str = self.original[1:]

        var_list = var_list_str.split(",")

        for var in var_list:
            default_val = None
            name = var
            # NOTE(sigmavirus24): This is from an earlier draft but is not in
            # the specification
            if "=" in var:
                name, default_val = tuple(var.split("=", 1))

            explode = name.endswith("*")
            name = name.rstrip("*")

            prefix: t.Optional[int] = None
            if ":" in name:
                name, prefix_str = tuple(name.split(":", 1))
                prefix = int(prefix_str, 10)

            if default_val:
                self.defaults[name] = default_val

            self.variables.append(
                (name, {"explode": explode, "prefix": prefix})
            )

        self.variable_names = [varname for (varname, _) in self.variables]

    def _query_expansion(
        self,
        name: str,
        value: VariableValue,
        explode: bool,
        prefix: t.Optional[int],
    ) -> t.Optional[str]:
        """Expansion method for the '?' and '&' operators."""
        if value is None:
            return None

        tuples, items = is_list_of_tuples(value)

        safe = self.operator.reserved_characters()
        _quote = self.operator.quote
        if list_test(value) and not tuples:
            if not value:
                return None
            value = t.cast(t.Sequence[ScalarVariableValue], value)
            if explode:
                return self.operator.expansion_separator().join(
                    f"{name}={_quote(v)}" for v in value
                )
            else:
                value = ",".join(_quote(v) for v in value)
                return f"{name}={value}"

        if dict_test(value) or tuples:
            if not value:
                return None
            value = t.cast(t.Mapping[str, ScalarVariableValue], value)
            items = items or sorted(value.items())
            if explode:
                return self.operator.expansion_separator().join(
                    f"{quote(k, safe)}={_quote(v)}" for k, v in items
                )
            else:
                value = ",".join(
                    f"{quote(k, safe)},{_quote(v)}" for k, v in items
                )
                return f"{name}={value}"

        if value:
            value = t.cast(t.Text, value)
            value = value[:prefix] if prefix else value
            return f"{name}={_quote(value)}"
        return name + "="

    def _label_path_expansion(
        self,
        name: str,
        value: VariableValue,
        explode: bool,
        prefix: t.Optional[int],
    ) -> t.Optional[str]:
        """Label and path expansion method.

        Expands for operators: '/', '.'

        """
        join_str = self.operator.expansion_separator()
        safe = self.operator.reserved_characters()

        if value is None or (
            not isinstance(value, (str, int, float, complex))
            and len(value) == 0
        ):
            return None

        tuples, items = is_list_of_tuples(value)

        if list_test(value) and not tuples:
            if not explode:
                join_str = ","

            value = t.cast(t.Sequence[ScalarVariableValue], value)
            fragments = [
                self.operator.quote(v) for v in value if v is not None
            ]
            return join_str.join(fragments) if fragments else None

        if dict_test(value) or tuples:
            value = t.cast(t.Mapping[str, ScalarVariableValue], value)
            items = items or sorted(value.items())
            format_str = "%s=%s"
            if not explode:
                format_str = "%s,%s"
                join_str = ","

            expanded = join_str.join(
                format_str % (quote(k, safe), self.operator.quote(v))
                for k, v in items
                if v is not None
            )
            return expanded if expanded else None

        value = t.cast(t.Text, value)
        value = value[:prefix] if prefix else value
        return self.operator.quote(value)

    def _semi_path_expansion(
        self,
        name: str,
        value: VariableValue,
        explode: bool,
        prefix: t.Optional[int],
    ) -> t.Optional[str]:
        """Expansion method for ';' operator."""
        join_str = self.operator.expansion_separator()
        safe = self.operator.reserved_characters()

        if value is None:
            return None

        tuples, items = is_list_of_tuples(value)

        if list_test(value) and not tuples:
            value = t.cast(t.Sequence[ScalarVariableValue], value)
            if explode:
                expanded = join_str.join(
                    f"{name}={quote(v, safe)}" for v in value if v is not None
                )
                return expanded if expanded else None
            else:
                value = ",".join(quote(v, safe) for v in value)
                return f"{name}={value}"

        if dict_test(value) or tuples:
            value = t.cast(t.Mapping[str, ScalarVariableValue], value)
            items = items or sorted(value.items())

            if explode:
                return join_str.join(
                    f"{quote(k, safe)}={self.operator.quote(v)}"
                    for k, v in items
                    if v is not None
                )
            else:
                expanded = ",".join(
                    f"{quote(k, safe)},{self.operator.quote(v)}"
                    for k, v in items
                    if v is not None
                )
                return f"{name}={expanded}"

        value = t.cast(t.Text, value)
        value = value[:prefix] if prefix else value
        if value:
            return f"{name}={self.operator.quote(value)}"

        return name

    def _string_expansion(
        self,
        name: str,
        value: VariableValue,
        explode: bool,
        prefix: t.Optional[int],
    ) -> t.Optional[str]:
        if value is None:
            return None

        tuples, items = is_list_of_tuples(value)

        if list_test(value) and not tuples:
            value = t.cast(t.Sequence[ScalarVariableValue], value)
            return ",".join(self.operator.quote(v) for v in value)

        if dict_test(value) or tuples:
            value = t.cast(t.Mapping[str, ScalarVariableValue], value)
            items = items or sorted(value.items())
            format_str = "%s=%s" if explode else "%s,%s"

            return ",".join(
                format_str % (self.operator.quote(k), self.operator.quote(v))
                for k, v in items
            )

        value = t.cast(t.Text, value)
        value = value[:prefix] if prefix else value
        return self.operator.quote(value)

    def expand(
        self, var_dict: t.Optional[VariableValueDict] = None
    ) -> t.Mapping[str, str]:
        """Expand the variable in question.

        Using ``var_dict`` and the previously parsed defaults, expand this
        variable and subvariables.

        :param dict var_dict: dictionary of key-value pairs to be used during
            expansion
        :returns: dict(variable=value)

        Examples::

            # (1)
            v = URIVariable('/var')
            expansion = v.expand({'var': 'value'})
            print(expansion)
            # => {'/var': '/value'}

            # (2)
            v = URIVariable('?var,hello,x,y')
            expansion = v.expand({'var': 'value', 'hello': 'Hello World!',
                                  'x': '1024', 'y': '768'})
            print(expansion)
            # => {'?var,hello,x,y':
            #     '?var=value&hello=Hello%20World%21&x=1024&y=768'}

        """
        return_values = []
        if var_dict is None:
            return {self.original: self.original}

        for name, opts in self.variables:
            value = var_dict.get(name, None)
            if not value and value != "" and name in self.defaults:
                value = self.defaults[name]

            if value is None:
                continue

            expanded = None
            if (
                self.operator == Operator.path_segment
                or self.operator == Operator.label_with_dot_prefix
            ):
                expansion = self._label_path_expansion
            elif (
                self.operator == Operator.form_style_query
                or self.operator == Operator.form_style_query_continuation
            ):
                expansion = self._query_expansion
            elif self.operator == Operator.path_style_parameter:
                expansion = self._semi_path_expansion
            else:
                expansion = self._string_expansion
            # match self.operator:
            #     case Operator.path_segment | Operator.label_with_dot_prefix:
            #         expansion = self._label_path_expansion
            #     case (Operator.form_style_query |
            #           Operator.form_style_query_continuation):
            #         expansion = self._query_expansion
            #     case Operator.path_style_parameter:
            #         expansion = self._semi_path_expansion
            #     case _:
            #         expansion = self._string_expansion

            expanded = expansion(name, value, opts["explode"], opts["prefix"])

            if expanded is not None:
                return_values.append(expanded)

        value = ""
        if return_values:
            value = (
                self.operator.variable_prefix()
                + self.operator.expansion_separator().join(return_values)
            )
        return {self.original: value}


def is_list_of_tuples(
    value: t.Any,
) -> t.Tuple[bool, t.Optional[t.Sequence[t.Tuple[str, ScalarVariableValue]]]]:
    if (
        not value
        or not isinstance(value, (list, tuple))
        or not all(isinstance(t, tuple) and len(t) == 2 for t in value)
    ):
        return False, None

    return True, value


def list_test(value: t.Any) -> bool:
    return isinstance(value, (list, tuple))


def dict_test(value: t.Any) -> bool:
    return isinstance(value, (dict, collections.abc.MutableMapping))


def _encode(value: t.AnyStr, encoding: str = "utf-8") -> bytes:
    if isinstance(value, str):
        return value.encode(encoding)
    return value


def quote(value: t.Any, safe: str) -> str:
    if not isinstance(value, (str, bytes)):
        value = str(value)
    return urllib.parse.quote(_encode(value), safe)

# === NexusCore/openenv\Lib\site-packages\urllib3\contrib\pyopenssl.py ===
"""
Module for using pyOpenSSL as a TLS backend. This module was relevant before
the standard library ``ssl`` module supported SNI, but now that we've dropped
support for Python 2.7 all relevant Python versions support SNI so
**this module is no longer recommended**.

This needs the following packages installed:

* `pyOpenSSL`_ (tested with 16.0.0)
* `cryptography`_ (minimum 1.3.4, from pyopenssl)
* `idna`_ (minimum 2.0)

However, pyOpenSSL depends on cryptography, so while we use all three directly here we
end up having relatively few packages required.

You can install them with the following command:

.. code-block:: bash

    $ python -m pip install pyopenssl cryptography idna

To activate certificate checking, call
:func:`~urllib3.contrib.pyopenssl.inject_into_urllib3` from your Python code
before you begin making HTTP requests. This can be done in a ``sitecustomize``
module, or at any other time before your application begins using ``urllib3``,
like this:

.. code-block:: python

    try:
        import urllib3.contrib.pyopenssl
        urllib3.contrib.pyopenssl.inject_into_urllib3()
    except ImportError:
        pass

.. _pyopenssl: https://www.pyopenssl.org
.. _cryptography: https://cryptography.io
.. _idna: https://github.com/kjd/idna
"""

from __future__ import annotations

import OpenSSL.SSL  # type: ignore[import-untyped]
from cryptography import x509

try:
    from cryptography.x509 import UnsupportedExtension  # type: ignore[attr-defined]
except ImportError:
    # UnsupportedExtension is gone in cryptography >= 2.1.0
    class UnsupportedExtension(Exception):  # type: ignore[no-redef]
        pass


import logging
import ssl
import typing
from io import BytesIO
from socket import socket as socket_cls
from socket import timeout

from .. import util

if typing.TYPE_CHECKING:
    from OpenSSL.crypto import X509  # type: ignore[import-untyped]


__all__ = ["inject_into_urllib3", "extract_from_urllib3"]

# Map from urllib3 to PyOpenSSL compatible parameter-values.
_openssl_versions: dict[int, int] = {
    util.ssl_.PROTOCOL_TLS: OpenSSL.SSL.SSLv23_METHOD,  # type: ignore[attr-defined]
    util.ssl_.PROTOCOL_TLS_CLIENT: OpenSSL.SSL.SSLv23_METHOD,  # type: ignore[attr-defined]
    ssl.PROTOCOL_TLSv1: OpenSSL.SSL.TLSv1_METHOD,
}

if hasattr(ssl, "PROTOCOL_TLSv1_1") and hasattr(OpenSSL.SSL, "TLSv1_1_METHOD"):
    _openssl_versions[ssl.PROTOCOL_TLSv1_1] = OpenSSL.SSL.TLSv1_1_METHOD

if hasattr(ssl, "PROTOCOL_TLSv1_2") and hasattr(OpenSSL.SSL, "TLSv1_2_METHOD"):
    _openssl_versions[ssl.PROTOCOL_TLSv1_2] = OpenSSL.SSL.TLSv1_2_METHOD


_stdlib_to_openssl_verify = {
    ssl.CERT_NONE: OpenSSL.SSL.VERIFY_NONE,
    ssl.CERT_OPTIONAL: OpenSSL.SSL.VERIFY_PEER,
    ssl.CERT_REQUIRED: OpenSSL.SSL.VERIFY_PEER
    + OpenSSL.SSL.VERIFY_FAIL_IF_NO_PEER_CERT,
}
_openssl_to_stdlib_verify = {v: k for k, v in _stdlib_to_openssl_verify.items()}

# The SSLvX values are the most likely to be missing in the future
# but we check them all just to be sure.
_OP_NO_SSLv2_OR_SSLv3: int = getattr(OpenSSL.SSL, "OP_NO_SSLv2", 0) | getattr(
    OpenSSL.SSL, "OP_NO_SSLv3", 0
)
_OP_NO_TLSv1: int = getattr(OpenSSL.SSL, "OP_NO_TLSv1", 0)
_OP_NO_TLSv1_1: int = getattr(OpenSSL.SSL, "OP_NO_TLSv1_1", 0)
_OP_NO_TLSv1_2: int = getattr(OpenSSL.SSL, "OP_NO_TLSv1_2", 0)
_OP_NO_TLSv1_3: int = getattr(OpenSSL.SSL, "OP_NO_TLSv1_3", 0)

_openssl_to_ssl_minimum_version: dict[int, int] = {
    ssl.TLSVersion.MINIMUM_SUPPORTED: _OP_NO_SSLv2_OR_SSLv3,
    ssl.TLSVersion.TLSv1: _OP_NO_SSLv2_OR_SSLv3,
    ssl.TLSVersion.TLSv1_1: _OP_NO_SSLv2_OR_SSLv3 | _OP_NO_TLSv1,
    ssl.TLSVersion.TLSv1_2: _OP_NO_SSLv2_OR_SSLv3 | _OP_NO_TLSv1 | _OP_NO_TLSv1_1,
    ssl.TLSVersion.TLSv1_3: (
        _OP_NO_SSLv2_OR_SSLv3 | _OP_NO_TLSv1 | _OP_NO_TLSv1_1 | _OP_NO_TLSv1_2
    ),
    ssl.TLSVersion.MAXIMUM_SUPPORTED: (
        _OP_NO_SSLv2_OR_SSLv3 | _OP_NO_TLSv1 | _OP_NO_TLSv1_1 | _OP_NO_TLSv1_2
    ),
}
_openssl_to_ssl_maximum_version: dict[int, int] = {
    ssl.TLSVersion.MINIMUM_SUPPORTED: (
        _OP_NO_SSLv2_OR_SSLv3
        | _OP_NO_TLSv1
        | _OP_NO_TLSv1_1
        | _OP_NO_TLSv1_2
        | _OP_NO_TLSv1_3
    ),
    ssl.TLSVersion.TLSv1: (
        _OP_NO_SSLv2_OR_SSLv3 | _OP_NO_TLSv1_1 | _OP_NO_TLSv1_2 | _OP_NO_TLSv1_3
    ),
    ssl.TLSVersion.TLSv1_1: _OP_NO_SSLv2_OR_SSLv3 | _OP_NO_TLSv1_2 | _OP_NO_TLSv1_3,
    ssl.TLSVersion.TLSv1_2: _OP_NO_SSLv2_OR_SSLv3 | _OP_NO_TLSv1_3,
    ssl.TLSVersion.TLSv1_3: _OP_NO_SSLv2_OR_SSLv3,
    ssl.TLSVersion.MAXIMUM_SUPPORTED: _OP_NO_SSLv2_OR_SSLv3,
}

# OpenSSL will only write 16K at a time
SSL_WRITE_BLOCKSIZE = 16384

orig_util_SSLContext = util.ssl_.SSLContext


log = logging.getLogger(__name__)


def inject_into_urllib3() -> None:
    "Monkey-patch urllib3 with PyOpenSSL-backed SSL-support."

    _validate_dependencies_met()

    util.SSLContext = PyOpenSSLContext  # type: ignore[assignment]
    util.ssl_.SSLContext = PyOpenSSLContext  # type: ignore[assignment]
    util.IS_PYOPENSSL = True
    util.ssl_.IS_PYOPENSSL = True


def extract_from_urllib3() -> None:
    "Undo monkey-patching by :func:`inject_into_urllib3`."

    util.SSLContext = orig_util_SSLContext
    util.ssl_.SSLContext = orig_util_SSLContext
    util.IS_PYOPENSSL = False
    util.ssl_.IS_PYOPENSSL = False


def _validate_dependencies_met() -> None:
    """
    Verifies that PyOpenSSL's package-level dependencies have been met.
    Throws `ImportError` if they are not met.
    """
    # Method added in `cryptography==1.1`; not available in older versions
    from cryptography.x509.extensions import Extensions

    if getattr(Extensions, "get_extension_for_class", None) is None:
        raise ImportError(
            "'cryptography' module missing required functionality.  "
            "Try upgrading to v1.3.4 or newer."
        )

    # pyOpenSSL 0.14 and above use cryptography for OpenSSL bindings. The _x509
    # attribute is only present on those versions.
    from OpenSSL.crypto import X509

    x509 = X509()
    if getattr(x509, "_x509", None) is None:
        raise ImportError(
            "'pyOpenSSL' module missing required functionality. "
            "Try upgrading to v0.14 or newer."
        )


def _dnsname_to_stdlib(name: str) -> str | None:
    """
    Converts a dNSName SubjectAlternativeName field to the form used by the
    standard library on the given Python version.

    Cryptography produces a dNSName as a unicode string that was idna-decoded
    from ASCII bytes. We need to idna-encode that string to get it back, and
    then on Python 3 we also need to convert to unicode via UTF-8 (the stdlib
    uses PyUnicode_FromStringAndSize on it, which decodes via UTF-8).

    If the name cannot be idna-encoded then we return None signalling that
    the name given should be skipped.
    """

    def idna_encode(name: str) -> bytes | None:
        """
        Borrowed wholesale from the Python Cryptography Project. It turns out
        that we can't just safely call `idna.encode`: it can explode for
        wildcard names. This avoids that problem.
        """
        import idna

        try:
            for prefix in ["*.", "."]:
                if name.startswith(prefix):
                    name = name[len(prefix) :]
                    return prefix.encode("ascii") + idna.encode(name)
            return idna.encode(name)
        except idna.core.IDNAError:
            return None

    # Don't send IPv6 addresses through the IDNA encoder.
    if ":" in name:
        return name

    encoded_name = idna_encode(name)
    if encoded_name is None:
        return None
    return encoded_name.decode("utf-8")


def get_subj_alt_name(peer_cert: X509) -> list[tuple[str, str]]:
    """
    Given an PyOpenSSL certificate, provides all the subject alternative names.
    """
    cert = peer_cert.to_cryptography()

    # We want to find the SAN extension. Ask Cryptography to locate it (it's
    # faster than looping in Python)
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        # No such extension, return the empty list.
        return []
    except (
        x509.DuplicateExtension,
        UnsupportedExtension,
        x509.UnsupportedGeneralNameType,
        UnicodeError,
    ) as e:
        # A problem has been found with the quality of the certificate. Assume
        # no SAN field is present.
        log.warning(
            "A problem was encountered with the certificate that prevented "
            "urllib3 from finding the SubjectAlternativeName field. This can "
            "affect certificate validation. The error was %s",
            e,
        )
        return []

    # We want to return dNSName and iPAddress fields. We need to cast the IPs
    # back to strings because the match_hostname function wants them as
    # strings.
    # Sadly the DNS names need to be idna encoded and then, on Python 3, UTF-8
    # decoded. This is pretty frustrating, but that's what the standard library
    # does with certificates, and so we need to attempt to do the same.
    # We also want to skip over names which cannot be idna encoded.
    names = [
        ("DNS", name)
        for name in map(_dnsname_to_stdlib, ext.get_values_for_type(x509.DNSName))
        if name is not None
    ]
    names.extend(
        ("IP Address", str(name)) for name in ext.get_values_for_type(x509.IPAddress)
    )

    return names


class WrappedSocket:
    """API-compatibility wrapper for Python OpenSSL's Connection-class."""

    def __init__(
        self,
        connection: OpenSSL.SSL.Connection,
        socket: socket_cls,
        suppress_ragged_eofs: bool = True,
    ) -> None:
        self.connection = connection
        self.socket = socket
        self.suppress_ragged_eofs = suppress_ragged_eofs
        self._io_refs = 0
        self._closed = False

    def fileno(self) -> int:
        return self.socket.fileno()

    # Copy-pasted from Python 3.5 source code
    def _decref_socketios(self) -> None:
        if self._io_refs > 0:
            self._io_refs -= 1
        if self._closed:
            self.close()

    def recv(self, *args: typing.Any, **kwargs: typing.Any) -> bytes:
        try:
            data = self.connection.recv(*args, **kwargs)
        except OpenSSL.SSL.SysCallError as e:
            if self.suppress_ragged_eofs and e.args == (-1, "Unexpected EOF"):
                return b""
            else:
                raise OSError(e.args[0], str(e)) from e
        except OpenSSL.SSL.ZeroReturnError:
            if self.connection.get_shutdown() == OpenSSL.SSL.RECEIVED_SHUTDOWN:
                return b""
            else:
                raise
        except OpenSSL.SSL.WantReadError as e:
            if not util.wait_for_read(self.socket, self.socket.gettimeout()):
                raise timeout("The read operation timed out") from e
            else:
                return self.recv(*args, **kwargs)

        # TLS 1.3 post-handshake authentication
        except OpenSSL.SSL.Error as e:
            raise ssl.SSLError(f"read error: {e!r}") from e
        else:
            return data  # type: ignore[no-any-return]

    def recv_into(self, *args: typing.Any, **kwargs: typing.Any) -> int:
        try:
            return self.connection.recv_into(*args, **kwargs)  # type: ignore[no-any-return]
        except OpenSSL.SSL.SysCallError as e:
            if self.suppress_ragged_eofs and e.args == (-1, "Unexpected EOF"):
                return 0
            else:
                raise OSError(e.args[0], str(e)) from e
        except OpenSSL.SSL.ZeroReturnError:
            if self.connection.get_shutdown() == OpenSSL.SSL.RECEIVED_SHUTDOWN:
                return 0
            else:
                raise
        except OpenSSL.SSL.WantReadError as e:
            if not util.wait_for_read(self.socket, self.socket.gettimeout()):
                raise timeout("The read operation timed out") from e
            else:
                return self.recv_into(*args, **kwargs)

        # TLS 1.3 post-handshake authentication
        except OpenSSL.SSL.Error as e:
            raise ssl.SSLError(f"read error: {e!r}") from e

    def settimeout(self, timeout: float) -> None:
        return self.socket.settimeout(timeout)

    def _send_until_done(self, data: bytes) -> int:
        while True:
            try:
                return self.connection.send(data)  # type: ignore[no-any-return]
            except OpenSSL.SSL.WantWriteError as e:
                if not util.wait_for_write(self.socket, self.socket.gettimeout()):
                    raise timeout() from e
                continue
            except OpenSSL.SSL.SysCallError as e:
                raise OSError(e.args[0], str(e)) from e

    def sendall(self, data: bytes) -> None:
        total_sent = 0
        while total_sent < len(data):
            sent = self._send_until_done(
                data[total_sent : total_sent + SSL_WRITE_BLOCKSIZE]
            )
            total_sent += sent

    def shutdown(self, how: int) -> None:
        try:
            self.connection.shutdown()
        except OpenSSL.SSL.Error as e:
            raise ssl.SSLError(f"shutdown error: {e!r}") from e

    def close(self) -> None:
        self._closed = True
        if self._io_refs <= 0:
            self._real_close()

    def _real_close(self) -> None:
        try:
            return self.connection.close()  # type: ignore[no-any-return]
        except OpenSSL.SSL.Error:
            return

    def getpeercert(
        self, binary_form: bool = False
    ) -> dict[str, list[typing.Any]] | None:
        x509 = self.connection.get_peer_certificate()

        if not x509:
            return x509  # type: ignore[no-any-return]

        if binary_form:
            return OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_ASN1, x509)  # type: ignore[no-any-return]

        return {
            "subject": ((("commonName", x509.get_subject().CN),),),  # type: ignore[dict-item]
            "subjectAltName": get_subj_alt_name(x509),
        }

    def version(self) -> str:
        return self.connection.get_protocol_version_name()  # type: ignore[no-any-return]

    def selected_alpn_protocol(self) -> str | None:
        alpn_proto = self.connection.get_alpn_proto_negotiated()
        return alpn_proto.decode() if alpn_proto else None


WrappedSocket.makefile = socket_cls.makefile  # type: ignore[attr-defined]


class PyOpenSSLContext:
    """
    I am a wrapper class for the PyOpenSSL ``Context`` object. I am responsible
    for translating the interface of the standard library ``SSLContext`` object
    to calls into PyOpenSSL.
    """

    def __init__(self, protocol: int) -> None:
        self.protocol = _openssl_versions[protocol]
        self._ctx = OpenSSL.SSL.Context(self.protocol)
        self._options = 0
        self.check_hostname = False
        self._minimum_version: int = ssl.TLSVersion.MINIMUM_SUPPORTED
        self._maximum_version: int = ssl.TLSVersion.MAXIMUM_SUPPORTED
        self._verify_flags: int = ssl.VERIFY_X509_TRUSTED_FIRST

    @property
    def options(self) -> int:
        return self._options

    @options.setter
    def options(self, value: int) -> None:
        self._options = value
        self._set_ctx_options()

    @property
    def verify_flags(self) -> int:
        return self._verify_flags

    @verify_flags.setter
    def verify_flags(self, value: int) -> None:
        self._verify_flags = value
        self._ctx.get_cert_store().set_flags(self._verify_flags)

    @property
    def verify_mode(self) -> int:
        return _openssl_to_stdlib_verify[self._ctx.get_verify_mode()]

    @verify_mode.setter
    def verify_mode(self, value: ssl.VerifyMode) -> None:
        self._ctx.set_verify(_stdlib_to_openssl_verify[value], _verify_callback)

    def set_default_verify_paths(self) -> None:
        self._ctx.set_default_verify_paths()

    def set_ciphers(self, ciphers: bytes | str) -> None:
        if isinstance(ciphers, str):
            ciphers = ciphers.encode("utf-8")
        self._ctx.set_cipher_list(ciphers)

    def load_verify_locations(
        self,
        cafile: str | None = None,
        capath: str | None = None,
        cadata: bytes | None = None,
    ) -> None:
        if cafile is not None:
            cafile = cafile.encode("utf-8")  # type: ignore[assignment]
        if capath is not None:
            capath = capath.encode("utf-8")  # type: ignore[assignment]
        try:
            self._ctx.load_verify_locations(cafile, capath)
            if cadata is not None:
                self._ctx.load_verify_locations(BytesIO(cadata))
        except OpenSSL.SSL.Error as e:
            raise ssl.SSLError(f"unable to load trusted certificates: {e!r}") from e

    def load_cert_chain(
        self,
        certfile: str,
        keyfile: str | None = None,
        password: str | None = None,
    ) -> None:
        try:
            self._ctx.use_certificate_chain_file(certfile)
            if password is not None:
                if not isinstance(password, bytes):
                    password = password.encode("utf-8")  # type: ignore[assignment]
                self._ctx.set_passwd_cb(lambda *_: password)
            self._ctx.use_privatekey_file(keyfile or certfile)
        except OpenSSL.SSL.Error as e:
            raise ssl.SSLError(f"Unable to load certificate chain: {e!r}") from e

    def set_alpn_protocols(self, protocols: list[bytes | str]) -> None:
        protocols = [util.util.to_bytes(p, "ascii") for p in protocols]
        return self._ctx.set_alpn_protos(protocols)  # type: ignore[no-any-return]

    def wrap_socket(
        self,
        sock: socket_cls,
        server_side: bool = False,
        do_handshake_on_connect: bool = True,
        suppress_ragged_eofs: bool = True,
        server_hostname: bytes | str | None = None,
    ) -> WrappedSocket:
        cnx = OpenSSL.SSL.Connection(self._ctx, sock)

        # If server_hostname is an IP, don't use it for SNI, per RFC6066 Section 3
        if server_hostname and not util.ssl_.is_ipaddress(server_hostname):
            if isinstance(server_hostname, str):
                server_hostname = server_hostname.encode("utf-8")
            cnx.set_tlsext_host_name(server_hostname)

        cnx.set_connect_state()

        while True:
            try:
                cnx.do_handshake()
            except OpenSSL.SSL.WantReadError as e:
                if not util.wait_for_read(sock, sock.gettimeout()):
                    raise timeout("select timed out") from e
                continue
            except OpenSSL.SSL.Error as e:
                raise ssl.SSLError(f"bad handshake: {e!r}") from e
            break

        return WrappedSocket(cnx, sock)

    def _set_ctx_options(self) -> None:
        self._ctx.set_options(
            self._options
            | _openssl_to_ssl_minimum_version[self._minimum_version]
            | _openssl_to_ssl_maximum_version[self._maximum_version]
        )

    @property
    def minimum_version(self) -> int:
        return self._minimum_version

    @minimum_version.setter
    def minimum_version(self, minimum_version: int) -> None:
        self._minimum_version = minimum_version
        self._set_ctx_options()

    @property
    def maximum_version(self) -> int:
        return self._maximum_version

    @maximum_version.setter
    def maximum_version(self, maximum_version: int) -> None:
        self._maximum_version = maximum_version
        self._set_ctx_options()


def _verify_callback(
    cnx: OpenSSL.SSL.Connection,
    x509: X509,
    err_no: int,
    err_depth: int,
    return_code: int,
) -> bool:
    return err_no == 0

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc2251.py ===
#
# This file is part of pyasn1-modules software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
# LDAP message syntax
#
# ASN.1 source from:
# http://www.trl.ibm.com/projects/xml/xss4j/data/asn1/grammars/ldap.asn
#
# Sample captures from:
# http://wiki.wireshark.org/SampleCaptures/
#
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import tag
from pyasn1.type import univ

maxInt = univ.Integer(2147483647)


class LDAPString(univ.OctetString):
    pass


class LDAPOID(univ.OctetString):
    pass


class LDAPDN(LDAPString):
    pass


class RelativeLDAPDN(LDAPString):
    pass


class AttributeType(LDAPString):
    pass


class AttributeDescription(LDAPString):
    pass


class AttributeDescriptionList(univ.SequenceOf):
    componentType = AttributeDescription()


class AttributeValue(univ.OctetString):
    pass


class AssertionValue(univ.OctetString):
    pass


class AttributeValueAssertion(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('attributeDesc', AttributeDescription()),
        namedtype.NamedType('assertionValue', AssertionValue())
    )


class Attribute(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type', AttributeDescription()),
        namedtype.NamedType('vals', univ.SetOf(componentType=AttributeValue()))
    )


class MatchingRuleId(LDAPString):
    pass


class Control(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('controlType', LDAPOID()),
        namedtype.DefaultedNamedType('criticality', univ.Boolean('False')),
        namedtype.OptionalNamedType('controlValue', univ.OctetString())
    )


class Controls(univ.SequenceOf):
    componentType = Control()


class LDAPURL(LDAPString):
    pass


class Referral(univ.SequenceOf):
    componentType = LDAPURL()


class SaslCredentials(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('mechanism', LDAPString()),
        namedtype.OptionalNamedType('credentials', univ.OctetString())
    )


class AuthenticationChoice(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('simple', univ.OctetString().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('reserved-1', univ.OctetString().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.NamedType('reserved-2', univ.OctetString().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
        namedtype.NamedType('sasl',
                            SaslCredentials().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
    )


class BindRequest(univ.Sequence):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 0)
    )
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('version', univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(1, 127))),
        namedtype.NamedType('name', LDAPDN()),
        namedtype.NamedType('authentication', AuthenticationChoice())
    )


class PartialAttributeList(univ.SequenceOf):
    componentType = univ.Sequence(
        componentType=namedtype.NamedTypes(
            namedtype.NamedType('type', AttributeDescription()),
            namedtype.NamedType('vals', univ.SetOf(componentType=AttributeValue()))
        )
    )


class SearchResultEntry(univ.Sequence):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 4)
    )
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('objectName', LDAPDN()),
        namedtype.NamedType('attributes', PartialAttributeList())
    )


class MatchingRuleAssertion(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('matchingRule', MatchingRuleId().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('type', AttributeDescription().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
        namedtype.NamedType('matchValue',
                            AssertionValue().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
        namedtype.DefaultedNamedType('dnAttributes', univ.Boolean('False').subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4)))
    )


class SubstringFilter(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type', AttributeDescription()),
        namedtype.NamedType('substrings',
            univ.SequenceOf(
                componentType=univ.Choice(
                    componentType=namedtype.NamedTypes(
                        namedtype.NamedType(
                            'initial', LDAPString().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))
                        ),
                        namedtype.NamedType(
                            'any', LDAPString().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))
                        ),
                        namedtype.NamedType(
                            'final', LDAPString().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))
                        )
                    )
                )
            )
        )
    )


# Ugly hack to handle recursive Filter reference (up to 3-levels deep).

class Filter3(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('equalityMatch', AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),
        namedtype.NamedType('substrings', SubstringFilter().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4))),
        namedtype.NamedType('greaterOrEqual', AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),
        namedtype.NamedType('lessOrEqual', AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 6))),
        namedtype.NamedType('present', AttributeDescription().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 7))),
        namedtype.NamedType('approxMatch', AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 8))),
        namedtype.NamedType('extensibleMatch', MatchingRuleAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 9)))
    )


class Filter2(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('and', univ.SetOf(componentType=Filter3()).subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.NamedType('or', univ.SetOf(componentType=Filter3()).subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
        namedtype.NamedType('not',
                            Filter3().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),
        namedtype.NamedType('equalityMatch', AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),
        namedtype.NamedType('substrings', SubstringFilter().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4))),
        namedtype.NamedType('greaterOrEqual', AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),
        namedtype.NamedType('lessOrEqual', AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 6))),
        namedtype.NamedType('present', AttributeDescription().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 7))),
        namedtype.NamedType('approxMatch', AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 8))),
        namedtype.NamedType('extensibleMatch', MatchingRuleAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 9)))
    )


class Filter(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('and', univ.SetOf(componentType=Filter2()).subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.NamedType('or', univ.SetOf(componentType=Filter2()).subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
        namedtype.NamedType('not',
                            Filter2().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),
        namedtype.NamedType('equalityMatch', AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),
        namedtype.NamedType('substrings', SubstringFilter().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4))),
        namedtype.NamedType('greaterOrEqual', AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),
        namedtype.NamedType('lessOrEqual', AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 6))),
        namedtype.NamedType('present', AttributeDescription().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 7))),
        namedtype.NamedType('approxMatch', AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 8))),
        namedtype.NamedType('extensibleMatch', MatchingRuleAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 9)))
    )


# End of Filter hack

class SearchRequest(univ.Sequence):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 3)
    )
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('baseObject', LDAPDN()),
        namedtype.NamedType('scope', univ.Enumerated(
            namedValues=namedval.NamedValues(('baseObject', 0), ('singleLevel', 1), ('wholeSubtree', 2)))),
        namedtype.NamedType('derefAliases', univ.Enumerated(
            namedValues=namedval.NamedValues(('neverDerefAliases', 0), ('derefInSearching', 1),
                                             ('derefFindingBaseObj', 2), ('derefAlways', 3)))),
        namedtype.NamedType('sizeLimit',
                            univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, maxInt))),
        namedtype.NamedType('timeLimit',
                            univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, maxInt))),
        namedtype.NamedType('typesOnly', univ.Boolean()),
        namedtype.NamedType('filter', Filter()),
        namedtype.NamedType('attributes', AttributeDescriptionList())
    )


class UnbindRequest(univ.Null):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatSimple, 2)
    )


class BindResponse(univ.Sequence):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 1)
    )
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('resultCode', univ.Enumerated(
            namedValues=namedval.NamedValues(('success', 0), ('operationsError', 1), ('protocolError', 2),
                                             ('timeLimitExceeded', 3), ('sizeLimitExceeded', 4), ('compareFalse', 5),
                                             ('compareTrue', 6), ('authMethodNotSupported', 7),
                                             ('strongAuthRequired', 8), ('reserved-9', 9), ('referral', 10),
                                             ('adminLimitExceeded', 11), ('unavailableCriticalExtension', 12),
                                             ('confidentialityRequired', 13), ('saslBindInProgress', 14),
                                             ('noSuchAttribute', 16), ('undefinedAttributeType', 17),
                                             ('inappropriateMatching', 18), ('constraintViolation', 19),
                                             ('attributeOrValueExists', 20), ('invalidAttributeSyntax', 21),
                                             ('noSuchObject', 32), ('aliasProblem', 33), ('invalidDNSyntax', 34),
                                             ('reserved-35', 35), ('aliasDereferencingProblem', 36),
                                             ('inappropriateAuthentication', 48), ('invalidCredentials', 49),
                                             ('insufficientAccessRights', 50), ('busy', 51), ('unavailable', 52),
                                             ('unwillingToPerform', 53), ('loopDetect', 54), ('namingViolation', 64),
                                             ('objectClassViolation', 65), ('notAllowedOnNonLeaf', 66),
                                             ('notAllowedOnRDN', 67), ('entryAlreadyExists', 68),
                                             ('objectClassModsProhibited', 69), ('reserved-70', 70),
                                             ('affectsMultipleDSAs', 71), ('other', 80), ('reserved-81', 81),
                                             ('reserved-82', 82), ('reserved-83', 83), ('reserved-84', 84),
                                             ('reserved-85', 85), ('reserved-86', 86), ('reserved-87', 87),
                                             ('reserved-88', 88), ('reserved-89', 89), ('reserved-90', 90)))),
        namedtype.NamedType('matchedDN', LDAPDN()),
        namedtype.NamedType('errorMessage', LDAPString()),
        namedtype.OptionalNamedType('referral', Referral().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),
        namedtype.OptionalNamedType('serverSaslCreds', univ.OctetString().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 7)))
    )


class LDAPResult(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('resultCode', univ.Enumerated(
            namedValues=namedval.NamedValues(('success', 0), ('operationsError', 1), ('protocolError', 2),
                                             ('timeLimitExceeded', 3), ('sizeLimitExceeded', 4), ('compareFalse', 5),
                                             ('compareTrue', 6), ('authMethodNotSupported', 7),
                                             ('strongAuthRequired', 8), ('reserved-9', 9), ('referral', 10),
                                             ('adminLimitExceeded', 11), ('unavailableCriticalExtension', 12),
                                             ('confidentialityRequired', 13), ('saslBindInProgress', 14),
                                             ('noSuchAttribute', 16), ('undefinedAttributeType', 17),
                                             ('inappropriateMatching', 18), ('constraintViolation', 19),
                                             ('attributeOrValueExists', 20), ('invalidAttributeSyntax', 21),
                                             ('noSuchObject', 32), ('aliasProblem', 33), ('invalidDNSyntax', 34),
                                             ('reserved-35', 35), ('aliasDereferencingProblem', 36),
                                             ('inappropriateAuthentication', 48), ('invalidCredentials', 49),
                                             ('insufficientAccessRights', 50), ('busy', 51), ('unavailable', 52),
                                             ('unwillingToPerform', 53), ('loopDetect', 54), ('namingViolation', 64),
                                             ('objectClassViolation', 65), ('notAllowedOnNonLeaf', 66),
                                             ('notAllowedOnRDN', 67), ('entryAlreadyExists', 68),
                                             ('objectClassModsProhibited', 69), ('reserved-70', 70),
                                             ('affectsMultipleDSAs', 71), ('other', 80), ('reserved-81', 81),
                                             ('reserved-82', 82), ('reserved-83', 83), ('reserved-84', 84),
                                             ('reserved-85', 85), ('reserved-86', 86), ('reserved-87', 87),
                                             ('reserved-88', 88), ('reserved-89', 89), ('reserved-90', 90)))),
        namedtype.NamedType('matchedDN', LDAPDN()),
        namedtype.NamedType('errorMessage', LDAPString()),
        namedtype.OptionalNamedType('referral', Referral().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3)))
    )


class SearchResultReference(univ.SequenceOf):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 19)
    )
    componentType = LDAPURL()


class SearchResultDone(LDAPResult):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 5)
    )


class AttributeTypeAndValues(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type', AttributeDescription()),
        namedtype.NamedType('vals', univ.SetOf(componentType=AttributeValue()))
    )


class ModifyRequest(univ.Sequence):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 6)
    )
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('object', LDAPDN()),
        namedtype.NamedType('modification',
            univ.SequenceOf(
                componentType=univ.Sequence(
                    componentType=namedtype.NamedTypes(
                        namedtype.NamedType(
                            'operation', univ.Enumerated(namedValues=namedval.NamedValues(('add', 0), ('delete', 1), ('replace', 2)))
                        ),
                        namedtype.NamedType('modification', AttributeTypeAndValues())))
            )
        )
    )


class ModifyResponse(LDAPResult):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 7)
    )


class AttributeList(univ.SequenceOf):
    componentType = univ.Sequence(
        componentType=namedtype.NamedTypes(
           namedtype.NamedType('type', AttributeDescription()),
           namedtype.NamedType('vals', univ.SetOf(componentType=AttributeValue()))
        )
    )


class AddRequest(univ.Sequence):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 8)
    )
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('entry', LDAPDN()),
        namedtype.NamedType('attributes', AttributeList())
    )


class AddResponse(LDAPResult):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 9)
    )


class DelRequest(LDAPResult):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 10)
    )


class DelResponse(LDAPResult):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 11)
    )


class ModifyDNRequest(univ.Sequence):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 12)
    )
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('entry', LDAPDN()),
        namedtype.NamedType('newrdn', RelativeLDAPDN()),
        namedtype.NamedType('deleteoldrdn', univ.Boolean()),
        namedtype.OptionalNamedType('newSuperior',
                                    LDAPDN().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))

    )


class ModifyDNResponse(LDAPResult):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 13)
    )


class CompareRequest(univ.Sequence):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 14)
    )
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('entry', LDAPDN()),
        namedtype.NamedType('ava', AttributeValueAssertion())
    )


class CompareResponse(LDAPResult):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 15)
    )


class AbandonRequest(LDAPResult):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 16)
    )


class ExtendedRequest(univ.Sequence):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 23)
    )
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('requestName',
                            LDAPOID().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('requestValue', univ.OctetString().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class ExtendedResponse(univ.Sequence):
    tagSet = univ.Sequence.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 24)
    )
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('resultCode', univ.Enumerated(
            namedValues=namedval.NamedValues(('success', 0), ('operationsError', 1), ('protocolError', 2),
                                             ('timeLimitExceeded', 3), ('sizeLimitExceeded', 4), ('compareFalse', 5),
                                             ('compareTrue', 6), ('authMethodNotSupported', 7),
                                             ('strongAuthRequired', 8), ('reserved-9', 9), ('referral', 10),
                                             ('adminLimitExceeded', 11), ('unavailableCriticalExtension', 12),
                                             ('confidentialityRequired', 13), ('saslBindInProgress', 14),
                                             ('noSuchAttribute', 16), ('undefinedAttributeType', 17),
                                             ('inappropriateMatching', 18), ('constraintViolation', 19),
                                             ('attributeOrValueExists', 20), ('invalidAttributeSyntax', 21),
                                             ('noSuchObject', 32), ('aliasProblem', 33), ('invalidDNSyntax', 34),
                                             ('reserved-35', 35), ('aliasDereferencingProblem', 36),
                                             ('inappropriateAuthentication', 48), ('invalidCredentials', 49),
                                             ('insufficientAccessRights', 50), ('busy', 51), ('unavailable', 52),
                                             ('unwillingToPerform', 53), ('loopDetect', 54), ('namingViolation', 64),
                                             ('objectClassViolation', 65), ('notAllowedOnNonLeaf', 66),
                                             ('notAllowedOnRDN', 67), ('entryAlreadyExists', 68),
                                             ('objectClassModsProhibited', 69), ('reserved-70', 70),
                                             ('affectsMultipleDSAs', 71), ('other', 80), ('reserved-81', 81),
                                             ('reserved-82', 82), ('reserved-83', 83), ('reserved-84', 84),
                                             ('reserved-85', 85), ('reserved-86', 86), ('reserved-87', 87),
                                             ('reserved-88', 88), ('reserved-89', 89), ('reserved-90', 90)))),
        namedtype.NamedType('matchedDN', LDAPDN()),
        namedtype.NamedType('errorMessage', LDAPString()),
        namedtype.OptionalNamedType('referral', Referral().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),

        namedtype.OptionalNamedType('responseName', LDAPOID().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 10))),
        namedtype.OptionalNamedType('response', univ.OctetString().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 11)))
    )


class MessageID(univ.Integer):
    subtypeSpec = univ.Integer.subtypeSpec + constraint.ValueRangeConstraint(
        0, maxInt
    )


class LDAPMessage(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('messageID', MessageID()),
        namedtype.NamedType(
            'protocolOp', univ.Choice(
                componentType=namedtype.NamedTypes(
                    namedtype.NamedType('bindRequest', BindRequest()),
                    namedtype.NamedType('bindResponse', BindResponse()),
                    namedtype.NamedType('unbindRequest', UnbindRequest()),
                    namedtype.NamedType('searchRequest', SearchRequest()),
                    namedtype.NamedType('searchResEntry', SearchResultEntry()),
                    namedtype.NamedType('searchResDone', SearchResultDone()),
                    namedtype.NamedType('searchResRef', SearchResultReference()),
                    namedtype.NamedType('modifyRequest', ModifyRequest()),
                    namedtype.NamedType('modifyResponse', ModifyResponse()),
                    namedtype.NamedType('addRequest', AddRequest()),
                    namedtype.NamedType('addResponse', AddResponse()),
                    namedtype.NamedType('delRequest', DelRequest()),
                    namedtype.NamedType('delResponse', DelResponse()),
                    namedtype.NamedType('modDNRequest', ModifyDNRequest()),
                    namedtype.NamedType('modDNResponse', ModifyDNResponse()),
                    namedtype.NamedType('compareRequest', CompareRequest()),
                    namedtype.NamedType('compareResponse', CompareResponse()),
                    namedtype.NamedType('abandonRequest', AbandonRequest()),
                    namedtype.NamedType('extendedReq', ExtendedRequest()),
                    namedtype.NamedType('extendedResp', ExtendedResponse())
                )
            )
        ),
        namedtype.OptionalNamedType('controls', Controls().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)))
    )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\spend_tracking\spend_tracking_utils.py ===
import hashlib
import json
import secrets
from datetime import datetime
from datetime import datetime as dt
from datetime import timezone
from typing import Any, List, Literal, Optional, cast

from pydantic import BaseModel

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.constants import REDACTED_BY_LITELM_STRING
from litellm.litellm_core_utils.core_helpers import get_litellm_metadata_from_kwargs
from litellm.proxy._types import SpendLogsMetadata, SpendLogsPayload
from litellm.proxy.utils import PrismaClient, hash_token
from litellm.types.utils import (
    StandardLoggingGuardrailInformation,
    StandardLoggingMCPToolCall,
    StandardLoggingModelInformation,
    StandardLoggingPayload,
    StandardLoggingVectorStoreRequest,
)
from litellm.utils import get_end_user_id_for_cost_tracking


def _is_master_key(api_key: str, _master_key: Optional[str]) -> bool:
    if _master_key is None:
        return False

    ## string comparison
    is_master_key = secrets.compare_digest(api_key, _master_key)
    if is_master_key:
        return True

    ## hash comparison
    is_master_key = secrets.compare_digest(api_key, hash_token(_master_key))
    if is_master_key:
        return True

    return False


def _get_spend_logs_metadata(
    metadata: Optional[dict],
    applied_guardrails: Optional[List[str]] = None,
    batch_models: Optional[List[str]] = None,
    mcp_tool_call_metadata: Optional[StandardLoggingMCPToolCall] = None,
    vector_store_request_metadata: Optional[
        List[StandardLoggingVectorStoreRequest]
    ] = None,
    guardrail_information: Optional[StandardLoggingGuardrailInformation] = None,
    usage_object: Optional[dict] = None,
    model_map_information: Optional[StandardLoggingModelInformation] = None,
) -> SpendLogsMetadata:
    if metadata is None:
        return SpendLogsMetadata(
            user_api_key=None,
            user_api_key_alias=None,
            user_api_key_team_id=None,
            user_api_key_org_id=None,
            user_api_key_user_id=None,
            user_api_key_team_alias=None,
            spend_logs_metadata=None,
            requester_ip_address=None,
            additional_usage_values=None,
            applied_guardrails=None,
            status=None or "success",
            error_information=None,
            proxy_server_request=None,
            batch_models=None,
            mcp_tool_call_metadata=None,
            vector_store_request_metadata=None,
            model_map_information=None,
            usage_object=None,
            guardrail_information=None,
        )
    verbose_proxy_logger.debug(
        "getting payload for SpendLogs, available keys in metadata: "
        + str(list(metadata.keys()))
    )

    # Filter the metadata dictionary to include only the specified keys
    clean_metadata = SpendLogsMetadata(
        **{  # type: ignore
            key: metadata[key]
            for key in SpendLogsMetadata.__annotations__.keys()
            if key in metadata
        }
    )
    clean_metadata["applied_guardrails"] = applied_guardrails
    clean_metadata["batch_models"] = batch_models
    clean_metadata["mcp_tool_call_metadata"] = mcp_tool_call_metadata
    clean_metadata["vector_store_request_metadata"] = (
        _get_vector_store_request_for_spend_logs_payload(vector_store_request_metadata)
    )
    clean_metadata["guardrail_information"] = guardrail_information
    clean_metadata["usage_object"] = usage_object
    clean_metadata["model_map_information"] = model_map_information
    return clean_metadata


def generate_hash_from_response(response_obj: Any) -> str:
    """
    Generate a stable hash from a response object.

    Args:
        response_obj: The response object to hash (can be dict, list, etc.)

    Returns:
        A hex string representation of the MD5 hash
    """
    try:
        # Create a stable JSON string of the entire response object
        # Sort keys to ensure consistent ordering
        json_str = json.dumps(response_obj, sort_keys=True)

        # Generate a hash of the response object
        unique_hash = hashlib.md5(json_str.encode()).hexdigest()
        return unique_hash
    except Exception:
        # Return a fallback hash if serialization fails
        return hashlib.md5(str(response_obj).encode()).hexdigest()


def get_spend_logs_id(
    call_type: str, response_obj: dict, kwargs: dict
) -> Optional[str]:
    if call_type == "aretrieve_batch" or call_type == "acreate_file":
        # Generate a hash from the response object
        id: Optional[str] = generate_hash_from_response(response_obj)
    else:
        id = cast(Optional[str], response_obj.get("id")) or cast(
            Optional[str], kwargs.get("litellm_call_id")
        )
    return id


def get_logging_payload(  # noqa: PLR0915
    kwargs, response_obj, start_time, end_time
) -> SpendLogsPayload:
    from litellm.proxy.proxy_server import general_settings, master_key

    if kwargs is None:
        kwargs = {}
    if response_obj is None or (
        not isinstance(response_obj, BaseModel) and not isinstance(response_obj, dict)
    ):
        response_obj = {}
    # standardize this function to be used across, s3, dynamoDB, langfuse logging
    litellm_params = kwargs.get("litellm_params", {})
    metadata = get_litellm_metadata_from_kwargs(kwargs)
    completion_start_time = kwargs.get("completion_start_time", end_time)
    call_type = kwargs.get("call_type")
    cache_hit = kwargs.get("cache_hit", False)
    usage = cast(dict, response_obj).get("usage", None) or {}
    if isinstance(usage, litellm.Usage):
        usage = dict(usage)

    if isinstance(response_obj, dict):
        response_obj_dict = response_obj
    elif isinstance(response_obj, BaseModel):
        response_obj_dict = response_obj.model_dump()
    else:
        response_obj_dict = {}

    id = get_spend_logs_id(call_type or "acompletion", response_obj_dict, kwargs)
    standard_logging_payload = cast(
        Optional[StandardLoggingPayload], kwargs.get("standard_logging_object", None)
    )

    end_user_id = get_end_user_id_for_cost_tracking(litellm_params)

    api_key = metadata.get("user_api_key", "")

    standard_logging_prompt_tokens: int = 0
    standard_logging_completion_tokens: int = 0
    standard_logging_total_tokens: int = 0
    if standard_logging_payload is not None:
        standard_logging_prompt_tokens = standard_logging_payload.get(
            "prompt_tokens", 0
        )
        standard_logging_completion_tokens = standard_logging_payload.get(
            "completion_tokens", 0
        )
        standard_logging_total_tokens = standard_logging_payload.get("total_tokens", 0)
    if api_key is not None and isinstance(api_key, str):
        if api_key.startswith("sk-"):
            # hash the api_key
            api_key = hash_token(api_key)
        if (
            _is_master_key(api_key=api_key, _master_key=master_key)
            and general_settings.get("disable_adding_master_key_hash_to_db") is True
        ):
            api_key = "litellm_proxy_master_key"  # use a known alias, if the user disabled storing master key in db

    if (
        standard_logging_payload is not None
    ):  # [TODO] migrate completely to sl payload. currently missing pass-through endpoint data
        api_key = (
            api_key
            or standard_logging_payload["metadata"].get("user_api_key_hash")
            or ""
        )
        end_user_id = end_user_id or standard_logging_payload["metadata"].get(
            "user_api_key_end_user_id"
        )
    else:
        api_key = ""
    request_tags = (
        json.dumps(metadata.get("tags", []))
        if isinstance(metadata.get("tags", []), list)
        else "[]"
    )
    if (
        standard_logging_payload is not None
        and standard_logging_payload.get("request_tags") is not None
    ):  # use 'tags' from standard logging payload instead
        request_tags = json.dumps(standard_logging_payload["request_tags"])
    if (
        _is_master_key(api_key=api_key, _master_key=master_key)
        and general_settings.get("disable_adding_master_key_hash_to_db") is True
    ):
        api_key = "litellm_proxy_master_key"  # use a known alias, if the user disabled storing master key in db

    _model_id = metadata.get("model_info", {}).get("id", "")
    _model_group = metadata.get("model_group", "")

    # clean up litellm metadata
    clean_metadata = _get_spend_logs_metadata(
        metadata,
        applied_guardrails=(
            standard_logging_payload["metadata"].get("applied_guardrails", None)
            if standard_logging_payload is not None
            else None
        ),
        batch_models=(
            standard_logging_payload.get("hidden_params", {}).get("batch_models", None)
            if standard_logging_payload is not None
            else None
        ),
        mcp_tool_call_metadata=(
            standard_logging_payload["metadata"].get("mcp_tool_call_metadata", None)
            if standard_logging_payload is not None
            else None
        ),
        vector_store_request_metadata=(
            standard_logging_payload["metadata"].get(
                "vector_store_request_metadata", None
            )
            if standard_logging_payload is not None
            else None
        ),
        usage_object=(
            standard_logging_payload["metadata"].get("usage_object", None)
            if standard_logging_payload is not None
            else None
        ),
        model_map_information=(
            standard_logging_payload["model_map_information"]
            if standard_logging_payload is not None
            else None
        ),
        guardrail_information=(
            standard_logging_payload.get("guardrail_information", None)
            if standard_logging_payload is not None
            else None
        ),
    )

    special_usage_fields = ["completion_tokens", "prompt_tokens", "total_tokens"]
    additional_usage_values = {}
    for k, v in usage.items():
        if k not in special_usage_fields:
            if isinstance(v, BaseModel):
                v = v.model_dump()
            additional_usage_values.update({k: v})
    clean_metadata["additional_usage_values"] = additional_usage_values

    if litellm.cache is not None:
        cache_key = litellm.cache.get_cache_key(**kwargs)
    else:
        cache_key = "Cache OFF"
    if cache_hit is True:
        import time

        id = f"{id}_cache_hit{time.time()}"  # SpendLogs does not allow duplicate request_id

    try:
        payload: SpendLogsPayload = SpendLogsPayload(
            request_id=str(id),
            call_type=call_type or "",
            api_key=str(api_key),
            cache_hit=str(cache_hit),
            startTime=_ensure_datetime_utc(start_time),
            endTime=_ensure_datetime_utc(end_time),
            completionStartTime=_ensure_datetime_utc(completion_start_time),
            model=kwargs.get("model", "") or "",
            user=metadata.get("user_api_key_user_id", "") or "",
            team_id=metadata.get("user_api_key_team_id", "") or "",
            metadata=json.dumps(clean_metadata),
            cache_key=cache_key,
            spend=kwargs.get("response_cost", 0),
            total_tokens=usage.get("total_tokens", standard_logging_total_tokens),
            prompt_tokens=usage.get("prompt_tokens", standard_logging_prompt_tokens),
            completion_tokens=usage.get(
                "completion_tokens", standard_logging_completion_tokens
            ),
            request_tags=request_tags,
            end_user=end_user_id or "",
            api_base=litellm_params.get("api_base", ""),
            model_group=_model_group,
            model_id=_model_id,
            requester_ip_address=clean_metadata.get("requester_ip_address", None),
            custom_llm_provider=kwargs.get("custom_llm_provider", ""),
            messages=_get_messages_for_spend_logs_payload(
                standard_logging_payload=standard_logging_payload, metadata=metadata
            ),
            response=_get_response_for_spend_logs_payload(standard_logging_payload),
            proxy_server_request=_get_proxy_server_request_for_spend_logs_payload(
                metadata=metadata, litellm_params=litellm_params
            ),
            session_id=_get_session_id_for_spend_log(
                kwargs=kwargs,
                standard_logging_payload=standard_logging_payload,
            ),
            status=_get_status_for_spend_log(
                metadata=metadata,
            ),
        )

        verbose_proxy_logger.debug(
            "SpendTable: created payload - payload: %s\n\n",
            json.dumps(payload, indent=4, default=str),
        )

        return payload
    except Exception as e:
        verbose_proxy_logger.exception(
            "Error creating spendlogs object - {}".format(str(e))
        )
        raise e


def _get_session_id_for_spend_log(
    kwargs: dict,
    standard_logging_payload: Optional[StandardLoggingPayload],
) -> str:
    """
    Get the session id for the spend log.

    This ensures each spend log is associated with a unique session id.

    """
    import uuid

    if (
        standard_logging_payload is not None
        and standard_logging_payload.get("trace_id") is not None
    ):
        return str(standard_logging_payload.get("trace_id"))

    # Users can dynamically set the trace_id for each request by passing `litellm_trace_id` in kwargs
    if kwargs.get("litellm_trace_id") is not None:
        return str(kwargs.get("litellm_trace_id"))

    # Ensure we always have a session id, if none is provided
    return str(uuid.uuid4())


def _ensure_datetime_utc(timestamp: datetime) -> datetime:
    """Helper to ensure datetime is in UTC"""
    timestamp = timestamp.astimezone(timezone.utc)
    return timestamp


async def get_spend_by_team_and_customer(
    start_date: dt,
    end_date: dt,
    team_id: str,
    customer_id: str,
    prisma_client: PrismaClient,
):
    sql_query = """
    WITH SpendByModelApiKey AS (
        SELECT
            date_trunc('day', sl."startTime") AS group_by_day,
            COALESCE(tt.team_alias, 'Unassigned Team') AS team_name,
            sl.end_user AS customer,
            sl.model,
            sl.api_key,
            SUM(sl.spend) AS model_api_spend,
            SUM(sl.total_tokens) AS model_api_tokens
        FROM 
            "LiteLLM_SpendLogs" sl
        LEFT JOIN 
            "LiteLLM_TeamTable" tt 
        ON 
            sl.team_id = tt.team_id
        WHERE
            sl."startTime" BETWEEN $1::date AND $2::date
            AND sl.team_id = $3
            AND sl.end_user = $4
        GROUP BY
            date_trunc('day', sl."startTime"),
            tt.team_alias,
            sl.end_user,
            sl.model,
            sl.api_key
    )
        SELECT
            group_by_day,
            jsonb_agg(jsonb_build_object(
                'team_name', team_name,
                'customer', customer,
                'total_spend', total_spend,
                'metadata', metadata
            )) AS teams_customers
        FROM (
            SELECT
                group_by_day,
                team_name,
                customer,
                SUM(model_api_spend) AS total_spend,
                jsonb_agg(jsonb_build_object(
                    'model', model,
                    'api_key', api_key,
                    'spend', model_api_spend,
                    'total_tokens', model_api_tokens
                )) AS metadata
            FROM 
                SpendByModelApiKey
            GROUP BY
                group_by_day,
                team_name,
                customer
        ) AS aggregated
        GROUP BY
            group_by_day
        ORDER BY
            group_by_day;
    """

    db_response = await prisma_client.db.query_raw(
        sql_query, start_date, end_date, team_id, customer_id
    )
    if db_response is None:
        return []

    return db_response


def _get_messages_for_spend_logs_payload(
    standard_logging_payload: Optional[StandardLoggingPayload],
    metadata: Optional[dict] = None,
) -> str:
    return "{}"


def _sanitize_request_body_for_spend_logs_payload(
    request_body: dict,
    visited: Optional[set] = None,
) -> dict:
    """
    Recursively sanitize request body to prevent logging large base64 strings or other large values.
    Truncates strings longer than 1000 characters and handles nested dictionaries.
    """
    MAX_STRING_LENGTH = 1000

    if visited is None:
        visited = set()

    # Get the object's memory address to track visited objects
    obj_id = id(request_body)
    if obj_id in visited:
        return {}
    visited.add(obj_id)

    def _sanitize_value(value: Any) -> Any:
        if isinstance(value, dict):
            return _sanitize_request_body_for_spend_logs_payload(value, visited)
        elif isinstance(value, list):
            return [_sanitize_value(item) for item in value]
        elif isinstance(value, str):
            if len(value) > MAX_STRING_LENGTH:
                return f"{value[:MAX_STRING_LENGTH]}... (truncated {len(value) - MAX_STRING_LENGTH} chars)"
            return value
        return value

    return {k: _sanitize_value(v) for k, v in request_body.items()}


def _get_proxy_server_request_for_spend_logs_payload(
    metadata: dict,
    litellm_params: dict,
) -> str:
    """
    Only store if _should_store_prompts_and_responses_in_spend_logs() is True
    """
    if _should_store_prompts_and_responses_in_spend_logs():
        _proxy_server_request = cast(
            Optional[dict], litellm_params.get("proxy_server_request", {})
        )
        if _proxy_server_request is not None:
            _request_body = _proxy_server_request.get("body", {}) or {}
            _request_body = _sanitize_request_body_for_spend_logs_payload(_request_body)
            _request_body_json_str = json.dumps(_request_body, default=str)
            return _request_body_json_str
    return "{}"


def _get_vector_store_request_for_spend_logs_payload(
    vector_store_request_metadata: Optional[List[StandardLoggingVectorStoreRequest]],
) -> Optional[List[StandardLoggingVectorStoreRequest]]:
    """
    If user does not want to store prompts and responses, then remove the content from the vector store request metadata
    """
    if _should_store_prompts_and_responses_in_spend_logs():
        return vector_store_request_metadata

    # if user does not want to store prompts and responses, then remove the content from the vector store request metadata
    if vector_store_request_metadata is None:
        return None
    for vector_store_request in vector_store_request_metadata:
        vector_store_search_response = (
            vector_store_request.get("vector_store_search_response", {}) or {}
        )
        response_data = vector_store_search_response.get("data", []) or []
        for response_item in response_data:
            for content_item in response_item.get("content", []) or []:
                if "text" in content_item:
                    content_item["text"] = REDACTED_BY_LITELM_STRING
    return vector_store_request_metadata


def _get_response_for_spend_logs_payload(
    payload: Optional[StandardLoggingPayload],
) -> str:
    if payload is None:
        return "{}"
    if _should_store_prompts_and_responses_in_spend_logs():
        return json.dumps(payload.get("response", {}))
    return "{}"


def _should_store_prompts_and_responses_in_spend_logs() -> bool:
    from litellm.proxy.proxy_server import general_settings

    return general_settings.get("store_prompts_in_spend_logs") is True


def _get_status_for_spend_log(
    metadata: dict,
) -> Literal["success", "failure"]:
    """
    Get the status for the spend log.

    It's only a failure if metadata.get("status") is "failure"
    """
    _status: Optional[str] = metadata.get("status", None)
    if _status == "failure":
        return "failure"
    return "success"

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\axes_grid1\axes_grid.py ===
from numbers import Number
import functools
from types import MethodType

import numpy as np

from matplotlib import _api, cbook
from matplotlib.gridspec import SubplotSpec

from .axes_divider import Size, SubplotDivider, Divider
from .mpl_axes import Axes, SimpleAxisArtist


class CbarAxesBase:
    def __init__(self, *args, orientation, **kwargs):
        self.orientation = orientation
        super().__init__(*args, **kwargs)

    def colorbar(self, mappable, **kwargs):
        return self.get_figure(root=False).colorbar(
            mappable, cax=self, location=self.orientation, **kwargs)


_cbaraxes_class_factory = cbook._make_class_factory(CbarAxesBase, "Cbar{}")


class Grid:
    """
    A grid of Axes.

    In Matplotlib, the Axes location (and size) is specified in normalized
    figure coordinates. This may not be ideal for images that needs to be
    displayed with a given aspect ratio; for example, it is difficult to
    display multiple images of a same size with some fixed padding between
    them.  AxesGrid can be used in such case.

    Attributes
    ----------
    axes_all : list of Axes
        A flat list of Axes. Note that you can also access this directly
        from the grid. The following is equivalent ::

            grid[i] == grid.axes_all[i]
            len(grid) == len(grid.axes_all)

    axes_column : list of list of Axes
        A 2D list of Axes where the first index is the column. This results
        in the usage pattern ``grid.axes_column[col][row]``.
    axes_row : list of list of Axes
        A 2D list of Axes where the first index is the row. This results
        in the usage pattern ``grid.axes_row[row][col]``.
    axes_llc : Axes
        The Axes in the lower left corner.
    ngrids : int
        Number of Axes in the grid.
    """

    _defaultAxesClass = Axes

    def __init__(self, fig,
                 rect,
                 nrows_ncols,
                 ngrids=None,
                 direction="row",
                 axes_pad=0.02,
                 *,
                 share_all=False,
                 share_x=True,
                 share_y=True,
                 label_mode="L",
                 axes_class=None,
                 aspect=False,
                 ):
        """
        Parameters
        ----------
        fig : `.Figure`
            The parent figure.
        rect : (float, float, float, float), (int, int, int), int, or \
    `~.SubplotSpec`
            The axes position, as a ``(left, bottom, width, height)`` tuple,
            as a three-digit subplot position code (e.g., ``(1, 2, 1)`` or
            ``121``), or as a `~.SubplotSpec`.
        nrows_ncols : (int, int)
            Number of rows and columns in the grid.
        ngrids : int or None, default: None
            If not None, only the first *ngrids* axes in the grid are created.
        direction : {"row", "column"}, default: "row"
            Whether axes are created in row-major ("row by row") or
            column-major order ("column by column").  This also affects the
            order in which axes are accessed using indexing (``grid[index]``).
        axes_pad : float or (float, float), default: 0.02
            Padding or (horizontal padding, vertical padding) between axes, in
            inches.
        share_all : bool, default: False
            Whether all axes share their x- and y-axis.  Overrides *share_x*
            and *share_y*.
        share_x : bool, default: True
            Whether all axes of a column share their x-axis.
        share_y : bool, default: True
            Whether all axes of a row share their y-axis.
        label_mode : {"L", "1", "all", "keep"}, default: "L"
            Determines which axes will get tick labels:

            - "L": All axes on the left column get vertical tick labels;
              all axes on the bottom row get horizontal tick labels.
            - "1": Only the bottom left axes is labelled.
            - "all": All axes are labelled.
            - "keep": Do not do anything.

        axes_class : subclass of `matplotlib.axes.Axes`, default: `.mpl_axes.Axes`
            The type of Axes to create.
        aspect : bool, default: False
            Whether the axes aspect ratio follows the aspect ratio of the data
            limits.
        """
        self._nrows, self._ncols = nrows_ncols

        if ngrids is None:
            ngrids = self._nrows * self._ncols
        else:
            if not 0 < ngrids <= self._nrows * self._ncols:
                raise ValueError(
                    "ngrids must be positive and not larger than nrows*ncols")

        self.ngrids = ngrids

        self._horiz_pad_size, self._vert_pad_size = map(
            Size.Fixed, np.broadcast_to(axes_pad, 2))

        _api.check_in_list(["column", "row"], direction=direction)
        self._direction = direction

        if axes_class is None:
            axes_class = self._defaultAxesClass
        elif isinstance(axes_class, (list, tuple)):
            cls, kwargs = axes_class
            axes_class = functools.partial(cls, **kwargs)

        kw = dict(horizontal=[], vertical=[], aspect=aspect)
        if isinstance(rect, (Number, SubplotSpec)):
            self._divider = SubplotDivider(fig, rect, **kw)
        elif len(rect) == 3:
            self._divider = SubplotDivider(fig, *rect, **kw)
        elif len(rect) == 4:
            self._divider = Divider(fig, rect, **kw)
        else:
            raise TypeError("Incorrect rect format")

        rect = self._divider.get_position()

        axes_array = np.full((self._nrows, self._ncols), None, dtype=object)
        for i in range(self.ngrids):
            col, row = self._get_col_row(i)
            if share_all:
                sharex = sharey = axes_array[0, 0]
            else:
                sharex = axes_array[0, col] if share_x else None
                sharey = axes_array[row, 0] if share_y else None
            axes_array[row, col] = axes_class(
                fig, rect, sharex=sharex, sharey=sharey)
        self.axes_all = axes_array.ravel(
            order="C" if self._direction == "row" else "F").tolist()
        self.axes_column = axes_array.T.tolist()
        self.axes_row = axes_array.tolist()
        self.axes_llc = self.axes_column[0][-1]

        self._init_locators()

        for ax in self.axes_all:
            fig.add_axes(ax)

        self.set_label_mode(label_mode)

    def _init_locators(self):
        self._divider.set_horizontal(
            [Size.Scaled(1), self._horiz_pad_size] * (self._ncols-1) + [Size.Scaled(1)])
        self._divider.set_vertical(
            [Size.Scaled(1), self._vert_pad_size] * (self._nrows-1) + [Size.Scaled(1)])
        for i in range(self.ngrids):
            col, row = self._get_col_row(i)
            self.axes_all[i].set_axes_locator(
                self._divider.new_locator(nx=2 * col, ny=2 * (self._nrows - 1 - row)))

    def _get_col_row(self, n):
        if self._direction == "column":
            col, row = divmod(n, self._nrows)
        else:
            row, col = divmod(n, self._ncols)

        return col, row

    # Good to propagate __len__ if we have __getitem__
    def __len__(self):
        return len(self.axes_all)

    def __getitem__(self, i):
        return self.axes_all[i]

    def get_geometry(self):
        """
        Return the number of rows and columns of the grid as (nrows, ncols).
        """
        return self._nrows, self._ncols

    def set_axes_pad(self, axes_pad):
        """
        Set the padding between the axes.

        Parameters
        ----------
        axes_pad : (float, float)
            The padding (horizontal pad, vertical pad) in inches.
        """
        self._horiz_pad_size.fixed_size = axes_pad[0]
        self._vert_pad_size.fixed_size = axes_pad[1]

    def get_axes_pad(self):
        """
        Return the axes padding.

        Returns
        -------
        hpad, vpad
            Padding (horizontal pad, vertical pad) in inches.
        """
        return (self._horiz_pad_size.fixed_size,
                self._vert_pad_size.fixed_size)

    def set_aspect(self, aspect):
        """Set the aspect of the SubplotDivider."""
        self._divider.set_aspect(aspect)

    def get_aspect(self):
        """Return the aspect of the SubplotDivider."""
        return self._divider.get_aspect()

    def set_label_mode(self, mode):
        """
        Define which axes have tick labels.

        Parameters
        ----------
        mode : {"L", "1", "all", "keep"}
            The label mode:

            - "L": All axes on the left column get vertical tick labels;
              all axes on the bottom row get horizontal tick labels.
            - "1": Only the bottom left axes is labelled.
            - "all": All axes are labelled.
            - "keep": Do not do anything.
        """
        _api.check_in_list(["all", "L", "1", "keep"], mode=mode)
        is_last_row, is_first_col = (
            np.mgrid[:self._nrows, :self._ncols] == [[[self._nrows - 1]], [[0]]])
        if mode == "all":
            bottom = left = np.full((self._nrows, self._ncols), True)
        elif mode == "L":
            bottom = is_last_row
            left = is_first_col
        elif mode == "1":
            bottom = left = is_last_row & is_first_col
        else:
            return
        for i in range(self._nrows):
            for j in range(self._ncols):
                ax = self.axes_row[i][j]
                if isinstance(ax.axis, MethodType):
                    bottom_axis = SimpleAxisArtist(ax.xaxis, 1, ax.spines["bottom"])
                    left_axis = SimpleAxisArtist(ax.yaxis, 1, ax.spines["left"])
                else:
                    bottom_axis = ax.axis["bottom"]
                    left_axis = ax.axis["left"]
                bottom_axis.toggle(ticklabels=bottom[i, j], label=bottom[i, j])
                left_axis.toggle(ticklabels=left[i, j], label=left[i, j])

    def get_divider(self):
        return self._divider

    def set_axes_locator(self, locator):
        self._divider.set_locator(locator)

    def get_axes_locator(self):
        return self._divider.get_locator()


class ImageGrid(Grid):
    """
    A grid of Axes for Image display.

    This class is a specialization of `~.axes_grid1.axes_grid.Grid` for displaying a
    grid of images.  In particular, it forces all axes in a column to share their x-axis
    and all axes in a row to share their y-axis.  It further provides helpers to add
    colorbars to some or all axes.
    """

    def __init__(self, fig,
                 rect,
                 nrows_ncols,
                 ngrids=None,
                 direction="row",
                 axes_pad=0.02,
                 *,
                 share_all=False,
                 aspect=True,
                 label_mode="L",
                 cbar_mode=None,
                 cbar_location="right",
                 cbar_pad=None,
                 cbar_size="5%",
                 cbar_set_cax=True,
                 axes_class=None,
                 ):
        """
        Parameters
        ----------
        fig : `.Figure`
            The parent figure.
        rect : (float, float, float, float) or int
            The axes position, as a ``(left, bottom, width, height)`` tuple or
            as a three-digit subplot position code (e.g., "121").
        nrows_ncols : (int, int)
            Number of rows and columns in the grid.
        ngrids : int or None, default: None
            If not None, only the first *ngrids* axes in the grid are created.
        direction : {"row", "column"}, default: "row"
            Whether axes are created in row-major ("row by row") or
            column-major order ("column by column").  This also affects the
            order in which axes are accessed using indexing (``grid[index]``).
        axes_pad : float or (float, float), default: 0.02in
            Padding or (horizontal padding, vertical padding) between axes, in
            inches.
        share_all : bool, default: False
            Whether all axes share their x- and y-axis.  Note that in any case,
            all axes in a column share their x-axis and all axes in a row share
            their y-axis.
        aspect : bool, default: True
            Whether the axes aspect ratio follows the aspect ratio of the data
            limits.
        label_mode : {"L", "1", "all"}, default: "L"
            Determines which axes will get tick labels:

            - "L": All axes on the left column get vertical tick labels;
              all axes on the bottom row get horizontal tick labels.
            - "1": Only the bottom left axes is labelled.
            - "all": all axes are labelled.

        cbar_mode : {"each", "single", "edge", None}, default: None
            Whether to create a colorbar for "each" axes, a "single" colorbar
            for the entire grid, colorbars only for axes on the "edge"
            determined by *cbar_location*, or no colorbars.  The colorbars are
            stored in the :attr:`cbar_axes` attribute.
        cbar_location : {"left", "right", "bottom", "top"}, default: "right"
        cbar_pad : float, default: None
            Padding between the image axes and the colorbar axes.

            .. versionchanged:: 3.10
                ``cbar_mode="single"`` no longer adds *axes_pad* between the axes
                and the colorbar if the *cbar_location* is "left" or "bottom".

        cbar_size : size specification (see `.Size.from_any`), default: "5%"
            Colorbar size.
        cbar_set_cax : bool, default: True
            If True, each axes in the grid has a *cax* attribute that is bound
            to associated *cbar_axes*.
        axes_class : subclass of `matplotlib.axes.Axes`, default: None
        """
        _api.check_in_list(["each", "single", "edge", None],
                           cbar_mode=cbar_mode)
        _api.check_in_list(["left", "right", "bottom", "top"],
                           cbar_location=cbar_location)
        self._colorbar_mode = cbar_mode
        self._colorbar_location = cbar_location
        self._colorbar_pad = cbar_pad
        self._colorbar_size = cbar_size
        # The colorbar axes are created in _init_locators().

        super().__init__(
            fig, rect, nrows_ncols, ngrids,
            direction=direction, axes_pad=axes_pad,
            share_all=share_all, share_x=True, share_y=True, aspect=aspect,
            label_mode=label_mode, axes_class=axes_class)

        for ax in self.cbar_axes:
            fig.add_axes(ax)

        if cbar_set_cax:
            if self._colorbar_mode == "single":
                for ax in self.axes_all:
                    ax.cax = self.cbar_axes[0]
            elif self._colorbar_mode == "edge":
                for index, ax in enumerate(self.axes_all):
                    col, row = self._get_col_row(index)
                    if self._colorbar_location in ("left", "right"):
                        ax.cax = self.cbar_axes[row]
                    else:
                        ax.cax = self.cbar_axes[col]
            else:
                for ax, cax in zip(self.axes_all, self.cbar_axes):
                    ax.cax = cax

    def _init_locators(self):
        # Slightly abusing this method to inject colorbar creation into init.

        if self._colorbar_pad is None:
            # horizontal or vertical arrangement?
            if self._colorbar_location in ("left", "right"):
                self._colorbar_pad = self._horiz_pad_size.fixed_size
            else:
                self._colorbar_pad = self._vert_pad_size.fixed_size
        self.cbar_axes = [
            _cbaraxes_class_factory(self._defaultAxesClass)(
                self.axes_all[0].get_figure(root=False), self._divider.get_position(),
                orientation=self._colorbar_location)
            for _ in range(self.ngrids)]

        cb_mode = self._colorbar_mode
        cb_location = self._colorbar_location

        h = []
        v = []

        h_ax_pos = []
        h_cb_pos = []
        if cb_mode == "single" and cb_location in ("left", "bottom"):
            if cb_location == "left":
                sz = self._nrows * Size.AxesX(self.axes_llc)
                h.append(Size.from_any(self._colorbar_size, sz))
                h.append(Size.from_any(self._colorbar_pad, sz))
                locator = self._divider.new_locator(nx=0, ny=0, ny1=-1)
            elif cb_location == "bottom":
                sz = self._ncols * Size.AxesY(self.axes_llc)
                v.append(Size.from_any(self._colorbar_size, sz))
                v.append(Size.from_any(self._colorbar_pad, sz))
                locator = self._divider.new_locator(nx=0, nx1=-1, ny=0)
            for i in range(self.ngrids):
                self.cbar_axes[i].set_visible(False)
            self.cbar_axes[0].set_axes_locator(locator)
            self.cbar_axes[0].set_visible(True)

        for col, ax in enumerate(self.axes_row[0]):
            if col != 0:
                h.append(self._horiz_pad_size)

            if ax:
                sz = Size.AxesX(ax, aspect="axes", ref_ax=self.axes_all[0])
            else:
                sz = Size.AxesX(self.axes_all[0],
                                aspect="axes", ref_ax=self.axes_all[0])

            if (cb_location == "left"
                    and (cb_mode == "each"
                         or (cb_mode == "edge" and col == 0))):
                h_cb_pos.append(len(h))
                h.append(Size.from_any(self._colorbar_size, sz))
                h.append(Size.from_any(self._colorbar_pad, sz))

            h_ax_pos.append(len(h))
            h.append(sz)

            if (cb_location == "right"
                    and (cb_mode == "each"
                         or (cb_mode == "edge" and col == self._ncols - 1))):
                h.append(Size.from_any(self._colorbar_pad, sz))
                h_cb_pos.append(len(h))
                h.append(Size.from_any(self._colorbar_size, sz))

        v_ax_pos = []
        v_cb_pos = []
        for row, ax in enumerate(self.axes_column[0][::-1]):
            if row != 0:
                v.append(self._vert_pad_size)

            if ax:
                sz = Size.AxesY(ax, aspect="axes", ref_ax=self.axes_all[0])
            else:
                sz = Size.AxesY(self.axes_all[0],
                                aspect="axes", ref_ax=self.axes_all[0])

            if (cb_location == "bottom"
                    and (cb_mode == "each"
                         or (cb_mode == "edge" and row == 0))):
                v_cb_pos.append(len(v))
                v.append(Size.from_any(self._colorbar_size, sz))
                v.append(Size.from_any(self._colorbar_pad, sz))

            v_ax_pos.append(len(v))
            v.append(sz)

            if (cb_location == "top"
                    and (cb_mode == "each"
                         or (cb_mode == "edge" and row == self._nrows - 1))):
                v.append(Size.from_any(self._colorbar_pad, sz))
                v_cb_pos.append(len(v))
                v.append(Size.from_any(self._colorbar_size, sz))

        for i in range(self.ngrids):
            col, row = self._get_col_row(i)
            locator = self._divider.new_locator(nx=h_ax_pos[col],
                                                ny=v_ax_pos[self._nrows-1-row])
            self.axes_all[i].set_axes_locator(locator)

            if cb_mode == "each":
                if cb_location in ("right", "left"):
                    locator = self._divider.new_locator(
                        nx=h_cb_pos[col], ny=v_ax_pos[self._nrows - 1 - row])

                elif cb_location in ("top", "bottom"):
                    locator = self._divider.new_locator(
                        nx=h_ax_pos[col], ny=v_cb_pos[self._nrows - 1 - row])

                self.cbar_axes[i].set_axes_locator(locator)
            elif cb_mode == "edge":
                if (cb_location == "left" and col == 0
                        or cb_location == "right" and col == self._ncols - 1):
                    locator = self._divider.new_locator(
                        nx=h_cb_pos[0], ny=v_ax_pos[self._nrows - 1 - row])
                    self.cbar_axes[row].set_axes_locator(locator)
                elif (cb_location == "bottom" and row == self._nrows - 1
                      or cb_location == "top" and row == 0):
                    locator = self._divider.new_locator(nx=h_ax_pos[col],
                                                        ny=v_cb_pos[0])
                    self.cbar_axes[col].set_axes_locator(locator)

        if cb_mode == "single":
            if cb_location == "right":
                sz = self._nrows * Size.AxesX(self.axes_llc)
                h.append(Size.from_any(self._colorbar_pad, sz))
                h.append(Size.from_any(self._colorbar_size, sz))
                locator = self._divider.new_locator(nx=-2, ny=0, ny1=-1)
            elif cb_location == "top":
                sz = self._ncols * Size.AxesY(self.axes_llc)
                v.append(Size.from_any(self._colorbar_pad, sz))
                v.append(Size.from_any(self._colorbar_size, sz))
                locator = self._divider.new_locator(nx=0, nx1=-1, ny=-2)
            if cb_location in ("right", "top"):
                for i in range(self.ngrids):
                    self.cbar_axes[i].set_visible(False)
                self.cbar_axes[0].set_axes_locator(locator)
                self.cbar_axes[0].set_visible(True)
        elif cb_mode == "each":
            for i in range(self.ngrids):
                self.cbar_axes[i].set_visible(True)
        elif cb_mode == "edge":
            if cb_location in ("right", "left"):
                count = self._nrows
            else:
                count = self._ncols
            for i in range(count):
                self.cbar_axes[i].set_visible(True)
            for j in range(i + 1, self.ngrids):
                self.cbar_axes[j].set_visible(False)
        else:
            for i in range(self.ngrids):
                self.cbar_axes[i].set_visible(False)
                self.cbar_axes[i].set_position([1., 1., 0.001, 0.001],
                                               which="active")

        self._divider.set_horizontal(h)
        self._divider.set_vertical(v)


AxesGrid = ImageGrid

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\key_binding\bindings\emacs.py ===
# pylint: disable=function-redefined
from __future__ import annotations

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer, indent, unindent
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.filters import (
    Condition,
    emacs_insert_mode,
    emacs_mode,
    has_arg,
    has_selection,
    in_paste_mode,
    is_multiline,
    is_read_only,
    shift_selection_mode,
    vi_search_direction_reversed,
)
from prompt_toolkit.key_binding.key_bindings import Binding
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.selection import SelectionType

from ..key_bindings import ConditionalKeyBindings, KeyBindings, KeyBindingsBase
from .named_commands import get_by_name

__all__ = [
    "load_emacs_bindings",
    "load_emacs_search_bindings",
    "load_emacs_shift_selection_bindings",
]

E = KeyPressEvent


@Condition
def is_returnable() -> bool:
    return get_app().current_buffer.is_returnable


@Condition
def is_arg() -> bool:
    return get_app().key_processor.arg == "-"


def load_emacs_bindings() -> KeyBindingsBase:
    """
    Some e-macs extensions.
    """
    # Overview of Readline emacs commands:
    # http://www.catonmat.net/download/readline-emacs-editing-mode-cheat-sheet.pdf
    key_bindings = KeyBindings()
    handle = key_bindings.add

    insert_mode = emacs_insert_mode

    @handle("escape")
    def _esc(event: E) -> None:
        """
        By default, ignore escape key.

        (If we don't put this here, and Esc is followed by a key which sequence
        is not handled, we'll insert an Escape character in the input stream.
        Something we don't want and happens to easily in emacs mode.
        Further, people can always use ControlQ to do a quoted insert.)
        """
        pass

    handle("c-a")(get_by_name("beginning-of-line"))
    handle("c-b")(get_by_name("backward-char"))
    handle("c-delete", filter=insert_mode)(get_by_name("kill-word"))
    handle("c-e")(get_by_name("end-of-line"))
    handle("c-f")(get_by_name("forward-char"))
    handle("c-left")(get_by_name("backward-word"))
    handle("c-right")(get_by_name("forward-word"))
    handle("c-x", "r", "y", filter=insert_mode)(get_by_name("yank"))
    handle("c-y", filter=insert_mode)(get_by_name("yank"))
    handle("escape", "b")(get_by_name("backward-word"))
    handle("escape", "c", filter=insert_mode)(get_by_name("capitalize-word"))
    handle("escape", "d", filter=insert_mode)(get_by_name("kill-word"))
    handle("escape", "f")(get_by_name("forward-word"))
    handle("escape", "l", filter=insert_mode)(get_by_name("downcase-word"))
    handle("escape", "u", filter=insert_mode)(get_by_name("uppercase-word"))
    handle("escape", "y", filter=insert_mode)(get_by_name("yank-pop"))
    handle("escape", "backspace", filter=insert_mode)(get_by_name("backward-kill-word"))
    handle("escape", "\\", filter=insert_mode)(get_by_name("delete-horizontal-space"))

    handle("c-home")(get_by_name("beginning-of-buffer"))
    handle("c-end")(get_by_name("end-of-buffer"))

    handle("c-_", save_before=(lambda e: False), filter=insert_mode)(
        get_by_name("undo")
    )

    handle("c-x", "c-u", save_before=(lambda e: False), filter=insert_mode)(
        get_by_name("undo")
    )

    handle("escape", "<", filter=~has_selection)(get_by_name("beginning-of-history"))
    handle("escape", ">", filter=~has_selection)(get_by_name("end-of-history"))

    handle("escape", ".", filter=insert_mode)(get_by_name("yank-last-arg"))
    handle("escape", "_", filter=insert_mode)(get_by_name("yank-last-arg"))
    handle("escape", "c-y", filter=insert_mode)(get_by_name("yank-nth-arg"))
    handle("escape", "#", filter=insert_mode)(get_by_name("insert-comment"))
    handle("c-o")(get_by_name("operate-and-get-next"))

    # ControlQ does a quoted insert. Not that for vt100 terminals, you have to
    # disable flow control by running ``stty -ixon``, otherwise Ctrl-Q and
    # Ctrl-S are captured by the terminal.
    handle("c-q", filter=~has_selection)(get_by_name("quoted-insert"))

    handle("c-x", "(")(get_by_name("start-kbd-macro"))
    handle("c-x", ")")(get_by_name("end-kbd-macro"))
    handle("c-x", "e")(get_by_name("call-last-kbd-macro"))

    @handle("c-n")
    def _next(event: E) -> None:
        "Next line."
        event.current_buffer.auto_down()

    @handle("c-p")
    def _prev(event: E) -> None:
        "Previous line."
        event.current_buffer.auto_up(count=event.arg)

    def handle_digit(c: str) -> None:
        """
        Handle input of arguments.
        The first number needs to be preceded by escape.
        """

        @handle(c, filter=has_arg)
        @handle("escape", c)
        def _(event: E) -> None:
            event.append_to_arg_count(c)

    for c in "0123456789":
        handle_digit(c)

    @handle("escape", "-", filter=~has_arg)
    def _meta_dash(event: E) -> None:
        """"""
        if event._arg is None:
            event.append_to_arg_count("-")

    @handle("-", filter=is_arg)
    def _dash(event: E) -> None:
        """
        When '-' is typed again, after exactly '-' has been given as an
        argument, ignore this.
        """
        event.app.key_processor.arg = "-"

    # Meta + Enter: always accept input.
    handle("escape", "enter", filter=insert_mode & is_returnable)(
        get_by_name("accept-line")
    )

    # Enter: accept input in single line mode.
    handle("enter", filter=insert_mode & is_returnable & ~is_multiline)(
        get_by_name("accept-line")
    )

    def character_search(buff: Buffer, char: str, count: int) -> None:
        if count < 0:
            match = buff.document.find_backwards(
                char, in_current_line=True, count=-count
            )
        else:
            match = buff.document.find(char, in_current_line=True, count=count)

        if match is not None:
            buff.cursor_position += match

    @handle("c-]", Keys.Any)
    def _goto_char(event: E) -> None:
        "When Ctl-] + a character is pressed. go to that character."
        # Also named 'character-search'
        character_search(event.current_buffer, event.data, event.arg)

    @handle("escape", "c-]", Keys.Any)
    def _goto_char_backwards(event: E) -> None:
        "Like Ctl-], but backwards."
        # Also named 'character-search-backward'
        character_search(event.current_buffer, event.data, -event.arg)

    @handle("escape", "a")
    def _prev_sentence(event: E) -> None:
        "Previous sentence."
        # TODO:

    @handle("escape", "e")
    def _end_of_sentence(event: E) -> None:
        "Move to end of sentence."
        # TODO:

    @handle("escape", "t", filter=insert_mode)
    def _swap_characters(event: E) -> None:
        """
        Swap the last two words before the cursor.
        """
        # TODO

    @handle("escape", "*", filter=insert_mode)
    def _insert_all_completions(event: E) -> None:
        """
        `meta-*`: Insert all possible completions of the preceding text.
        """
        buff = event.current_buffer

        # List all completions.
        complete_event = CompleteEvent(text_inserted=False, completion_requested=True)
        completions = list(
            buff.completer.get_completions(buff.document, complete_event)
        )

        # Insert them.
        text_to_insert = " ".join(c.text for c in completions)
        buff.insert_text(text_to_insert)

    @handle("c-x", "c-x")
    def _toggle_start_end(event: E) -> None:
        """
        Move cursor back and forth between the start and end of the current
        line.
        """
        buffer = event.current_buffer

        if buffer.document.is_cursor_at_the_end_of_line:
            buffer.cursor_position += buffer.document.get_start_of_line_position(
                after_whitespace=False
            )
        else:
            buffer.cursor_position += buffer.document.get_end_of_line_position()

    @handle("c-@")  # Control-space or Control-@
    def _start_selection(event: E) -> None:
        """
        Start of the selection (if the current buffer is not empty).
        """
        # Take the current cursor position as the start of this selection.
        buff = event.current_buffer
        if buff.text:
            buff.start_selection(selection_type=SelectionType.CHARACTERS)

    @handle("c-g", filter=~has_selection)
    def _cancel(event: E) -> None:
        """
        Control + G: Cancel completion menu and validation state.
        """
        event.current_buffer.complete_state = None
        event.current_buffer.validation_error = None

    @handle("c-g", filter=has_selection)
    def _cancel_selection(event: E) -> None:
        """
        Cancel selection.
        """
        event.current_buffer.exit_selection()

    @handle("c-w", filter=has_selection)
    @handle("c-x", "r", "k", filter=has_selection)
    def _cut(event: E) -> None:
        """
        Cut selected text.
        """
        data = event.current_buffer.cut_selection()
        event.app.clipboard.set_data(data)

    @handle("escape", "w", filter=has_selection)
    def _copy(event: E) -> None:
        """
        Copy selected text.
        """
        data = event.current_buffer.copy_selection()
        event.app.clipboard.set_data(data)

    @handle("escape", "left")
    def _start_of_word(event: E) -> None:
        """
        Cursor to start of previous word.
        """
        buffer = event.current_buffer
        buffer.cursor_position += (
            buffer.document.find_previous_word_beginning(count=event.arg) or 0
        )

    @handle("escape", "right")
    def _start_next_word(event: E) -> None:
        """
        Cursor to start of next word.
        """
        buffer = event.current_buffer
        buffer.cursor_position += (
            buffer.document.find_next_word_beginning(count=event.arg)
            or buffer.document.get_end_of_document_position()
        )

    @handle("escape", "/", filter=insert_mode)
    def _complete(event: E) -> None:
        """
        M-/: Complete.
        """
        b = event.current_buffer
        if b.complete_state:
            b.complete_next()
        else:
            b.start_completion(select_first=True)

    @handle("c-c", ">", filter=has_selection)
    def _indent(event: E) -> None:
        """
        Indent selected text.
        """
        buffer = event.current_buffer

        buffer.cursor_position += buffer.document.get_start_of_line_position(
            after_whitespace=True
        )

        from_, to = buffer.document.selection_range()
        from_, _ = buffer.document.translate_index_to_position(from_)
        to, _ = buffer.document.translate_index_to_position(to)

        indent(buffer, from_, to + 1, count=event.arg)

    @handle("c-c", "<", filter=has_selection)
    def _unindent(event: E) -> None:
        """
        Unindent selected text.
        """
        buffer = event.current_buffer

        from_, to = buffer.document.selection_range()
        from_, _ = buffer.document.translate_index_to_position(from_)
        to, _ = buffer.document.translate_index_to_position(to)

        unindent(buffer, from_, to + 1, count=event.arg)

    return ConditionalKeyBindings(key_bindings, emacs_mode)


def load_emacs_search_bindings() -> KeyBindingsBase:
    key_bindings = KeyBindings()
    handle = key_bindings.add
    from . import search

    # NOTE: We don't bind 'Escape' to 'abort_search'. The reason is that we
    #       want Alt+Enter to accept input directly in incremental search mode.
    #       Instead, we have double escape.

    handle("c-r")(search.start_reverse_incremental_search)
    handle("c-s")(search.start_forward_incremental_search)

    handle("c-c")(search.abort_search)
    handle("c-g")(search.abort_search)
    handle("c-r")(search.reverse_incremental_search)
    handle("c-s")(search.forward_incremental_search)
    handle("up")(search.reverse_incremental_search)
    handle("down")(search.forward_incremental_search)
    handle("enter")(search.accept_search)

    # Handling of escape.
    handle("escape", eager=True)(search.accept_search)

    # Like Readline, it's more natural to accept the search when escape has
    # been pressed, however instead the following two bindings could be used
    # instead.
    # #handle('escape', 'escape', eager=True)(search.abort_search)
    # #handle('escape', 'enter', eager=True)(search.accept_search_and_accept_input)

    # If Read-only: also include the following key bindings:

    # '/' and '?' key bindings for searching, just like Vi mode.
    handle("?", filter=is_read_only & ~vi_search_direction_reversed)(
        search.start_reverse_incremental_search
    )
    handle("/", filter=is_read_only & ~vi_search_direction_reversed)(
        search.start_forward_incremental_search
    )
    handle("?", filter=is_read_only & vi_search_direction_reversed)(
        search.start_forward_incremental_search
    )
    handle("/", filter=is_read_only & vi_search_direction_reversed)(
        search.start_reverse_incremental_search
    )

    @handle("n", filter=is_read_only)
    def _jump_next(event: E) -> None:
        "Jump to next match."
        event.current_buffer.apply_search(
            event.app.current_search_state,
            include_current_position=False,
            count=event.arg,
        )

    @handle("N", filter=is_read_only)
    def _jump_prev(event: E) -> None:
        "Jump to previous match."
        event.current_buffer.apply_search(
            ~event.app.current_search_state,
            include_current_position=False,
            count=event.arg,
        )

    return ConditionalKeyBindings(key_bindings, emacs_mode)


def load_emacs_shift_selection_bindings() -> KeyBindingsBase:
    """
    Bindings to select text with shift + cursor movements
    """

    key_bindings = KeyBindings()
    handle = key_bindings.add

    def unshift_move(event: E) -> None:
        """
        Used for the shift selection mode. When called with
        a shift + movement key press event, moves the cursor
        as if shift is not pressed.
        """
        key = event.key_sequence[0].key

        if key == Keys.ShiftUp:
            event.current_buffer.auto_up(count=event.arg)
            return
        if key == Keys.ShiftDown:
            event.current_buffer.auto_down(count=event.arg)
            return

        # the other keys are handled through their readline command
        key_to_command: dict[Keys | str, str] = {
            Keys.ShiftLeft: "backward-char",
            Keys.ShiftRight: "forward-char",
            Keys.ShiftHome: "beginning-of-line",
            Keys.ShiftEnd: "end-of-line",
            Keys.ControlShiftLeft: "backward-word",
            Keys.ControlShiftRight: "forward-word",
            Keys.ControlShiftHome: "beginning-of-buffer",
            Keys.ControlShiftEnd: "end-of-buffer",
        }

        try:
            # Both the dict lookup and `get_by_name` can raise KeyError.
            binding = get_by_name(key_to_command[key])
        except KeyError:
            pass
        else:  # (`else` is not really needed here.)
            if isinstance(binding, Binding):
                # (It should always be a binding here)
                binding.call(event)

    @handle("s-left", filter=~has_selection)
    @handle("s-right", filter=~has_selection)
    @handle("s-up", filter=~has_selection)
    @handle("s-down", filter=~has_selection)
    @handle("s-home", filter=~has_selection)
    @handle("s-end", filter=~has_selection)
    @handle("c-s-left", filter=~has_selection)
    @handle("c-s-right", filter=~has_selection)
    @handle("c-s-home", filter=~has_selection)
    @handle("c-s-end", filter=~has_selection)
    def _start_selection(event: E) -> None:
        """
        Start selection with shift + movement.
        """
        # Take the current cursor position as the start of this selection.
        buff = event.current_buffer
        if buff.text:
            buff.start_selection(selection_type=SelectionType.CHARACTERS)

            if buff.selection_state is not None:
                # (`selection_state` should never be `None`, it is created by
                # `start_selection`.)
                buff.selection_state.enter_shift_mode()

            # Then move the cursor
            original_position = buff.cursor_position
            unshift_move(event)
            if buff.cursor_position == original_position:
                # Cursor didn't actually move - so cancel selection
                # to avoid having an empty selection
                buff.exit_selection()

    @handle("s-left", filter=shift_selection_mode)
    @handle("s-right", filter=shift_selection_mode)
    @handle("s-up", filter=shift_selection_mode)
    @handle("s-down", filter=shift_selection_mode)
    @handle("s-home", filter=shift_selection_mode)
    @handle("s-end", filter=shift_selection_mode)
    @handle("c-s-left", filter=shift_selection_mode)
    @handle("c-s-right", filter=shift_selection_mode)
    @handle("c-s-home", filter=shift_selection_mode)
    @handle("c-s-end", filter=shift_selection_mode)
    def _extend_selection(event: E) -> None:
        """
        Extend the selection
        """
        # Just move the cursor, like shift was not pressed
        unshift_move(event)
        buff = event.current_buffer

        if buff.selection_state is not None:
            if buff.cursor_position == buff.selection_state.original_cursor_position:
                # selection is now empty, so cancel selection
                buff.exit_selection()

    @handle(Keys.Any, filter=shift_selection_mode)
    def _replace_selection(event: E) -> None:
        """
        Replace selection by what is typed
        """
        event.current_buffer.cut_selection()
        get_by_name("self-insert").call(event)

    @handle("enter", filter=shift_selection_mode & is_multiline)
    def _newline(event: E) -> None:
        """
        A newline replaces the selection
        """
        event.current_buffer.cut_selection()
        event.current_buffer.newline(copy_margin=not in_paste_mode())

    @handle("backspace", filter=shift_selection_mode)
    def _delete(event: E) -> None:
        """
        Delete selection.
        """
        event.current_buffer.cut_selection()

    @handle("c-y", filter=shift_selection_mode)
    def _yank(event: E) -> None:
        """
        In shift selection mode, yanking (pasting) replace the selection.
        """
        buff = event.current_buffer
        if buff.selection_state:
            buff.cut_selection()
        get_by_name("yank").call(event)

    # moving the cursor in shift selection mode cancels the selection
    @handle("left", filter=shift_selection_mode)
    @handle("right", filter=shift_selection_mode)
    @handle("up", filter=shift_selection_mode)
    @handle("down", filter=shift_selection_mode)
    @handle("home", filter=shift_selection_mode)
    @handle("end", filter=shift_selection_mode)
    @handle("c-left", filter=shift_selection_mode)
    @handle("c-right", filter=shift_selection_mode)
    @handle("c-home", filter=shift_selection_mode)
    @handle("c-end", filter=shift_selection_mode)
    def _cancel(event: E) -> None:
        """
        Cancel selection.
        """
        event.current_buffer.exit_selection()
        # we then process the cursor movement
        key_press = event.key_sequence[0]
        event.key_processor.feed(key_press, first=True)

    return ConditionalKeyBindings(key_bindings, emacs_mode)