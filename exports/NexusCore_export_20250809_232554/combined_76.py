
# === NexusCore/tools\exports\export_20250803_114325\combined_25.py ===

# === NexusCore/openenv\Lib\site-packages\typing_extensions.py ===
import abc
import builtins
import collections
import collections.abc
import contextlib
import enum
import functools
import inspect
import keyword
import operator
import sys
import types as _types
import typing
import warnings

__all__ = [
    # Super-special typing primitives.
    'Any',
    'ClassVar',
    'Concatenate',
    'Final',
    'LiteralString',
    'ParamSpec',
    'ParamSpecArgs',
    'ParamSpecKwargs',
    'Self',
    'Type',
    'TypeVar',
    'TypeVarTuple',
    'Unpack',

    # ABCs (from collections.abc).
    'Awaitable',
    'AsyncIterator',
    'AsyncIterable',
    'Coroutine',
    'AsyncGenerator',
    'AsyncContextManager',
    'Buffer',
    'ChainMap',

    # Concrete collection types.
    'ContextManager',
    'Counter',
    'Deque',
    'DefaultDict',
    'NamedTuple',
    'OrderedDict',
    'TypedDict',

    # Structural checks, a.k.a. protocols.
    'SupportsAbs',
    'SupportsBytes',
    'SupportsComplex',
    'SupportsFloat',
    'SupportsIndex',
    'SupportsInt',
    'SupportsRound',

    # One-off things.
    'Annotated',
    'assert_never',
    'assert_type',
    'clear_overloads',
    'dataclass_transform',
    'deprecated',
    'Doc',
    'evaluate_forward_ref',
    'get_overloads',
    'final',
    'Format',
    'get_annotations',
    'get_args',
    'get_origin',
    'get_original_bases',
    'get_protocol_members',
    'get_type_hints',
    'IntVar',
    'is_protocol',
    'is_typeddict',
    'Literal',
    'NewType',
    'overload',
    'override',
    'Protocol',
    'reveal_type',
    'runtime',
    'runtime_checkable',
    'Text',
    'TypeAlias',
    'TypeAliasType',
    'TypeForm',
    'TypeGuard',
    'TypeIs',
    'TYPE_CHECKING',
    'Never',
    'NoReturn',
    'ReadOnly',
    'Required',
    'NotRequired',
    'NoDefault',
    'NoExtraItems',

    # Pure aliases, have always been in typing
    'AbstractSet',
    'AnyStr',
    'BinaryIO',
    'Callable',
    'Collection',
    'Container',
    'Dict',
    'ForwardRef',
    'FrozenSet',
    'Generator',
    'Generic',
    'Hashable',
    'IO',
    'ItemsView',
    'Iterable',
    'Iterator',
    'KeysView',
    'List',
    'Mapping',
    'MappingView',
    'Match',
    'MutableMapping',
    'MutableSequence',
    'MutableSet',
    'Optional',
    'Pattern',
    'Reversible',
    'Sequence',
    'Set',
    'Sized',
    'TextIO',
    'Tuple',
    'Union',
    'ValuesView',
    'cast',
    'no_type_check',
    'no_type_check_decorator',
]

# for backward compatibility
PEP_560 = True
GenericMeta = type
_PEP_696_IMPLEMENTED = sys.version_info >= (3, 13, 0, "beta")

# Added with bpo-45166 to 3.10.1+ and some 3.9 versions
_FORWARD_REF_HAS_CLASS = "__forward_is_class__" in typing.ForwardRef.__slots__

# The functions below are modified copies of typing internal helpers.
# They are needed by _ProtocolMeta and they provide support for PEP 646.


class _Sentinel:
    def __repr__(self):
        return "<sentinel>"


_marker = _Sentinel()


if sys.version_info >= (3, 10):
    def _should_collect_from_parameters(t):
        return isinstance(
            t, (typing._GenericAlias, _types.GenericAlias, _types.UnionType)
        )
elif sys.version_info >= (3, 9):
    def _should_collect_from_parameters(t):
        return isinstance(t, (typing._GenericAlias, _types.GenericAlias))
else:
    def _should_collect_from_parameters(t):
        return isinstance(t, typing._GenericAlias) and not t._special


NoReturn = typing.NoReturn

# Some unconstrained type variables.  These are used by the container types.
# (These are not for export.)
T = typing.TypeVar('T')  # Any type.
KT = typing.TypeVar('KT')  # Key type.
VT = typing.TypeVar('VT')  # Value type.
T_co = typing.TypeVar('T_co', covariant=True)  # Any type covariant containers.
T_contra = typing.TypeVar('T_contra', contravariant=True)  # Ditto contravariant.


if sys.version_info >= (3, 11):
    from typing import Any
else:

    class _AnyMeta(type):
        def __instancecheck__(self, obj):
            if self is Any:
                raise TypeError("typing_extensions.Any cannot be used with isinstance()")
            return super().__instancecheck__(obj)

        def __repr__(self):
            if self is Any:
                return "typing_extensions.Any"
            return super().__repr__()

    class Any(metaclass=_AnyMeta):
        """Special type indicating an unconstrained type.
        - Any is compatible with every type.
        - Any assumed to have all methods.
        - All values assumed to be instances of Any.
        Note that all the above statements are true from the point of view of
        static type checkers. At runtime, Any should not be used with instance
        checks.
        """
        def __new__(cls, *args, **kwargs):
            if cls is Any:
                raise TypeError("Any cannot be instantiated")
            return super().__new__(cls, *args, **kwargs)


ClassVar = typing.ClassVar


class _ExtensionsSpecialForm(typing._SpecialForm, _root=True):
    def __repr__(self):
        return 'typing_extensions.' + self._name


Final = typing.Final

if sys.version_info >= (3, 11):
    final = typing.final
else:
    # @final exists in 3.8+, but we backport it for all versions
    # before 3.11 to keep support for the __final__ attribute.
    # See https://bugs.python.org/issue46342
    def final(f):
        """This decorator can be used to indicate to type checkers that
        the decorated method cannot be overridden, and decorated class
        cannot be subclassed. For example:

            class Base:
                @final
                def done(self) -> None:
                    ...
            class Sub(Base):
                def done(self) -> None:  # Error reported by type checker
                    ...
            @final
            class Leaf:
                ...
            class Other(Leaf):  # Error reported by type checker
                ...

        There is no runtime checking of these properties. The decorator
        sets the ``__final__`` attribute to ``True`` on the decorated object
        to allow runtime introspection.
        """
        try:
            f.__final__ = True
        except (AttributeError, TypeError):
            # Skip the attribute silently if it is not writable.
            # AttributeError happens if the object has __slots__ or a
            # read-only property, TypeError if it's a builtin class.
            pass
        return f


def IntVar(name):
    return typing.TypeVar(name)


# A Literal bug was fixed in 3.11.0, 3.10.1 and 3.9.8
if sys.version_info >= (3, 10, 1):
    Literal = typing.Literal
else:
    def _flatten_literal_params(parameters):
        """An internal helper for Literal creation: flatten Literals among parameters"""
        params = []
        for p in parameters:
            if isinstance(p, _LiteralGenericAlias):
                params.extend(p.__args__)
            else:
                params.append(p)
        return tuple(params)

    def _value_and_type_iter(params):
        for p in params:
            yield p, type(p)

    class _LiteralGenericAlias(typing._GenericAlias, _root=True):
        def __eq__(self, other):
            if not isinstance(other, _LiteralGenericAlias):
                return NotImplemented
            these_args_deduped = set(_value_and_type_iter(self.__args__))
            other_args_deduped = set(_value_and_type_iter(other.__args__))
            return these_args_deduped == other_args_deduped

        def __hash__(self):
            return hash(frozenset(_value_and_type_iter(self.__args__)))

    class _LiteralForm(_ExtensionsSpecialForm, _root=True):
        def __init__(self, doc: str):
            self._name = 'Literal'
            self._doc = self.__doc__ = doc

        def __getitem__(self, parameters):
            if not isinstance(parameters, tuple):
                parameters = (parameters,)

            parameters = _flatten_literal_params(parameters)

            val_type_pairs = list(_value_and_type_iter(parameters))
            try:
                deduped_pairs = set(val_type_pairs)
            except TypeError:
                # unhashable parameters
                pass
            else:
                # similar logic to typing._deduplicate on Python 3.9+
                if len(deduped_pairs) < len(val_type_pairs):
                    new_parameters = []
                    for pair in val_type_pairs:
                        if pair in deduped_pairs:
                            new_parameters.append(pair[0])
                            deduped_pairs.remove(pair)
                    assert not deduped_pairs, deduped_pairs
                    parameters = tuple(new_parameters)

            return _LiteralGenericAlias(self, parameters)

    Literal = _LiteralForm(doc="""\
                           A type that can be used to indicate to type checkers
                           that the corresponding value has a value literally equivalent
                           to the provided parameter. For example:

                               var: Literal[4] = 4

                           The type checker understands that 'var' is literally equal to
                           the value 4 and no other value.

                           Literal[...] cannot be subclassed. There is no runtime
                           checking verifying that the parameter is actually a value
                           instead of a type.""")


_overload_dummy = typing._overload_dummy


if hasattr(typing, "get_overloads"):  # 3.11+
    overload = typing.overload
    get_overloads = typing.get_overloads
    clear_overloads = typing.clear_overloads
else:
    # {module: {qualname: {firstlineno: func}}}
    _overload_registry = collections.defaultdict(
        functools.partial(collections.defaultdict, dict)
    )

    def overload(func):
        """Decorator for overloaded functions/methods.

        In a stub file, place two or more stub definitions for the same
        function in a row, each decorated with @overload.  For example:

        @overload
        def utf8(value: None) -> None: ...
        @overload
        def utf8(value: bytes) -> bytes: ...
        @overload
        def utf8(value: str) -> bytes: ...

        In a non-stub file (i.e. a regular .py file), do the same but
        follow it with an implementation.  The implementation should *not*
        be decorated with @overload.  For example:

        @overload
        def utf8(value: None) -> None: ...
        @overload
        def utf8(value: bytes) -> bytes: ...
        @overload
        def utf8(value: str) -> bytes: ...
        def utf8(value):
            # implementation goes here

        The overloads for a function can be retrieved at runtime using the
        get_overloads() function.
        """
        # classmethod and staticmethod
        f = getattr(func, "__func__", func)
        try:
            _overload_registry[f.__module__][f.__qualname__][
                f.__code__.co_firstlineno
            ] = func
        except AttributeError:
            # Not a normal function; ignore.
            pass
        return _overload_dummy

    def get_overloads(func):
        """Return all defined overloads for *func* as a sequence."""
        # classmethod and staticmethod
        f = getattr(func, "__func__", func)
        if f.__module__ not in _overload_registry:
            return []
        mod_dict = _overload_registry[f.__module__]
        if f.__qualname__ not in mod_dict:
            return []
        return list(mod_dict[f.__qualname__].values())

    def clear_overloads():
        """Clear all overloads in the registry."""
        _overload_registry.clear()


# This is not a real generic class.  Don't use outside annotations.
Type = typing.Type

# Various ABCs mimicking those in collections.abc.
# A few are simply re-exported for completeness.
Awaitable = typing.Awaitable
Coroutine = typing.Coroutine
AsyncIterable = typing.AsyncIterable
AsyncIterator = typing.AsyncIterator
Deque = typing.Deque
DefaultDict = typing.DefaultDict
OrderedDict = typing.OrderedDict
Counter = typing.Counter
ChainMap = typing.ChainMap
Text = typing.Text
TYPE_CHECKING = typing.TYPE_CHECKING


if sys.version_info >= (3, 13, 0, "beta"):
    from typing import AsyncContextManager, AsyncGenerator, ContextManager, Generator
else:
    def _is_dunder(attr):
        return attr.startswith('__') and attr.endswith('__')

    # Python <3.9 doesn't have typing._SpecialGenericAlias
    _special_generic_alias_base = getattr(
        typing, "_SpecialGenericAlias", typing._GenericAlias
    )

    class _SpecialGenericAlias(_special_generic_alias_base, _root=True):
        def __init__(self, origin, nparams, *, inst=True, name=None, defaults=()):
            if _special_generic_alias_base is typing._GenericAlias:
                # Python <3.9
                self.__origin__ = origin
                self._nparams = nparams
                super().__init__(origin, nparams, special=True, inst=inst, name=name)
            else:
                # Python >= 3.9
                super().__init__(origin, nparams, inst=inst, name=name)
            self._defaults = defaults

        def __setattr__(self, attr, val):
            allowed_attrs = {'_name', '_inst', '_nparams', '_defaults'}
            if _special_generic_alias_base is typing._GenericAlias:
                # Python <3.9
                allowed_attrs.add("__origin__")
            if _is_dunder(attr) or attr in allowed_attrs:
                object.__setattr__(self, attr, val)
            else:
                setattr(self.__origin__, attr, val)

        @typing._tp_cache
        def __getitem__(self, params):
            if not isinstance(params, tuple):
                params = (params,)
            msg = "Parameters to generic types must be types."
            params = tuple(typing._type_check(p, msg) for p in params)
            if (
                self._defaults
                and len(params) < self._nparams
                and len(params) + len(self._defaults) >= self._nparams
            ):
                params = (*params, *self._defaults[len(params) - self._nparams:])
            actual_len = len(params)

            if actual_len != self._nparams:
                if self._defaults:
                    expected = f"at least {self._nparams - len(self._defaults)}"
                else:
                    expected = str(self._nparams)
                if not self._nparams:
                    raise TypeError(f"{self} is not a generic class")
                raise TypeError(
                    f"Too {'many' if actual_len > self._nparams else 'few'}"
                    f" arguments for {self};"
                    f" actual {actual_len}, expected {expected}"
                )
            return self.copy_with(params)

    _NoneType = type(None)
    Generator = _SpecialGenericAlias(
        collections.abc.Generator, 3, defaults=(_NoneType, _NoneType)
    )
    AsyncGenerator = _SpecialGenericAlias(
        collections.abc.AsyncGenerator, 2, defaults=(_NoneType,)
    )
    ContextManager = _SpecialGenericAlias(
        contextlib.AbstractContextManager,
        2,
        name="ContextManager",
        defaults=(typing.Optional[bool],)
    )
    AsyncContextManager = _SpecialGenericAlias(
        contextlib.AbstractAsyncContextManager,
        2,
        name="AsyncContextManager",
        defaults=(typing.Optional[bool],)
    )


_PROTO_ALLOWLIST = {
    'collections.abc': [
        'Callable', 'Awaitable', 'Iterable', 'Iterator', 'AsyncIterable',
        'Hashable', 'Sized', 'Container', 'Collection', 'Reversible', 'Buffer',
    ],
    'contextlib': ['AbstractContextManager', 'AbstractAsyncContextManager'],
    'typing_extensions': ['Buffer'],
}


_EXCLUDED_ATTRS = frozenset(typing.EXCLUDED_ATTRIBUTES) | {
    "__match_args__", "__protocol_attrs__", "__non_callable_proto_members__",
    "__final__",
}


def _get_protocol_attrs(cls):
    attrs = set()
    for base in cls.__mro__[:-1]:  # without object
        if base.__name__ in {'Protocol', 'Generic'}:
            continue
        annotations = getattr(base, '__annotations__', {})
        for attr in (*base.__dict__, *annotations):
            if (not attr.startswith('_abc_') and attr not in _EXCLUDED_ATTRS):
                attrs.add(attr)
    return attrs


def _caller(depth=2):
    try:
        return sys._getframe(depth).f_globals.get('__name__', '__main__')
    except (AttributeError, ValueError):  # For platforms without _getframe()
        return None


# `__match_args__` attribute was removed from protocol members in 3.13,
# we want to backport this change to older Python versions.
if sys.version_info >= (3, 13):
    Protocol = typing.Protocol
else:
    def _allow_reckless_class_checks(depth=3):
        """Allow instance and class checks for special stdlib modules.
        The abc and functools modules indiscriminately call isinstance() and
        issubclass() on the whole MRO of a user class, which may contain protocols.
        """
        return _caller(depth) in {'abc', 'functools', None}

    def _no_init(self, *args, **kwargs):
        if type(self)._is_protocol:
            raise TypeError('Protocols cannot be instantiated')

    def _type_check_issubclass_arg_1(arg):
        """Raise TypeError if `arg` is not an instance of `type`
        in `issubclass(arg, <protocol>)`.

        In most cases, this is verified by type.__subclasscheck__.
        Checking it again unnecessarily would slow down issubclass() checks,
        so, we don't perform this check unless we absolutely have to.

        For various error paths, however,
        we want to ensure that *this* error message is shown to the user
        where relevant, rather than a typing.py-specific error message.
        """
        if not isinstance(arg, type):
            # Same error message as for issubclass(1, int).
            raise TypeError('issubclass() arg 1 must be a class')

    # Inheriting from typing._ProtocolMeta isn't actually desirable,
    # but is necessary to allow typing.Protocol and typing_extensions.Protocol
    # to mix without getting TypeErrors about "metaclass conflict"
    class _ProtocolMeta(type(typing.Protocol)):
        # This metaclass is somewhat unfortunate,
        # but is necessary for several reasons...
        #
        # NOTE: DO NOT call super() in any methods in this class
        # That would call the methods on typing._ProtocolMeta on Python 3.8-3.11
        # and those are slow
        def __new__(mcls, name, bases, namespace, **kwargs):
            if name == "Protocol" and len(bases) < 2:
                pass
            elif {Protocol, typing.Protocol} & set(bases):
                for base in bases:
                    if not (
                        base in {object, typing.Generic, Protocol, typing.Protocol}
                        or base.__name__ in _PROTO_ALLOWLIST.get(base.__module__, [])
                        or is_protocol(base)
                    ):
                        raise TypeError(
                            f"Protocols can only inherit from other protocols, "
                            f"got {base!r}"
                        )
            return abc.ABCMeta.__new__(mcls, name, bases, namespace, **kwargs)

        def __init__(cls, *args, **kwargs):
            abc.ABCMeta.__init__(cls, *args, **kwargs)
            if getattr(cls, "_is_protocol", False):
                cls.__protocol_attrs__ = _get_protocol_attrs(cls)

        def __subclasscheck__(cls, other):
            if cls is Protocol:
                return type.__subclasscheck__(cls, other)
            if (
                getattr(cls, '_is_protocol', False)
                and not _allow_reckless_class_checks()
            ):
                if not getattr(cls, '_is_runtime_protocol', False):
                    _type_check_issubclass_arg_1(other)
                    raise TypeError(
                        "Instance and class checks can only be used with "
                        "@runtime_checkable protocols"
                    )
                if (
                    # this attribute is set by @runtime_checkable:
                    cls.__non_callable_proto_members__
                    and cls.__dict__.get("__subclasshook__") is _proto_hook
                ):
                    _type_check_issubclass_arg_1(other)
                    non_method_attrs = sorted(cls.__non_callable_proto_members__)
                    raise TypeError(
                        "Protocols with non-method members don't support issubclass()."
                        f" Non-method members: {str(non_method_attrs)[1:-1]}."
                    )
            return abc.ABCMeta.__subclasscheck__(cls, other)

        def __instancecheck__(cls, instance):
            # We need this method for situations where attributes are
            # assigned in __init__.
            if cls is Protocol:
                return type.__instancecheck__(cls, instance)
            if not getattr(cls, "_is_protocol", False):
                # i.e., it's a concrete subclass of a protocol
                return abc.ABCMeta.__instancecheck__(cls, instance)

            if (
                not getattr(cls, '_is_runtime_protocol', False) and
                not _allow_reckless_class_checks()
            ):
                raise TypeError("Instance and class checks can only be used with"
                                " @runtime_checkable protocols")

            if abc.ABCMeta.__instancecheck__(cls, instance):
                return True

            for attr in cls.__protocol_attrs__:
                try:
                    val = inspect.getattr_static(instance, attr)
                except AttributeError:
                    break
                # this attribute is set by @runtime_checkable:
                if val is None and attr not in cls.__non_callable_proto_members__:
                    break
            else:
                return True

            return False

        def __eq__(cls, other):
            # Hack so that typing.Generic.__class_getitem__
            # treats typing_extensions.Protocol
            # as equivalent to typing.Protocol
            if abc.ABCMeta.__eq__(cls, other) is True:
                return True
            return cls is Protocol and other is typing.Protocol

        # This has to be defined, or the abc-module cache
        # complains about classes with this metaclass being unhashable,
        # if we define only __eq__!
        def __hash__(cls) -> int:
            return type.__hash__(cls)

    @classmethod
    def _proto_hook(cls, other):
        if not cls.__dict__.get('_is_protocol', False):
            return NotImplemented

        for attr in cls.__protocol_attrs__:
            for base in other.__mro__:
                # Check if the members appears in the class dictionary...
                if attr in base.__dict__:
                    if base.__dict__[attr] is None:
                        return NotImplemented
                    break

                # ...or in annotations, if it is a sub-protocol.
                annotations = getattr(base, '__annotations__', {})
                if (
                    isinstance(annotations, collections.abc.Mapping)
                    and attr in annotations
                    and is_protocol(other)
                ):
                    break
            else:
                return NotImplemented
        return True

    class Protocol(typing.Generic, metaclass=_ProtocolMeta):
        __doc__ = typing.Protocol.__doc__
        __slots__ = ()
        _is_protocol = True
        _is_runtime_protocol = False

        def __init_subclass__(cls, *args, **kwargs):
            super().__init_subclass__(*args, **kwargs)

            # Determine if this is a protocol or a concrete subclass.
            if not cls.__dict__.get('_is_protocol', False):
                cls._is_protocol = any(b is Protocol for b in cls.__bases__)

            # Set (or override) the protocol subclass hook.
            if '__subclasshook__' not in cls.__dict__:
                cls.__subclasshook__ = _proto_hook

            # Prohibit instantiation for protocol classes
            if cls._is_protocol and cls.__init__ is Protocol.__init__:
                cls.__init__ = _no_init


if sys.version_info >= (3, 13):
    runtime_checkable = typing.runtime_checkable
else:
    def runtime_checkable(cls):
        """Mark a protocol class as a runtime protocol.

        Such protocol can be used with isinstance() and issubclass().
        Raise TypeError if applied to a non-protocol class.
        This allows a simple-minded structural check very similar to
        one trick ponies in collections.abc such as Iterable.

        For example::

            @runtime_checkable
            class Closable(Protocol):
                def close(self): ...

            assert isinstance(open('/some/file'), Closable)

        Warning: this will check only the presence of the required methods,
        not their type signatures!
        """
        if not issubclass(cls, typing.Generic) or not getattr(cls, '_is_protocol', False):
            raise TypeError(f'@runtime_checkable can be only applied to protocol classes,'
                            f' got {cls!r}')
        cls._is_runtime_protocol = True

        # typing.Protocol classes on <=3.11 break if we execute this block,
        # because typing.Protocol classes on <=3.11 don't have a
        # `__protocol_attrs__` attribute, and this block relies on the
        # `__protocol_attrs__` attribute. Meanwhile, typing.Protocol classes on 3.12.2+
        # break if we *don't* execute this block, because *they* assume that all
        # protocol classes have a `__non_callable_proto_members__` attribute
        # (which this block sets)
        if isinstance(cls, _ProtocolMeta) or sys.version_info >= (3, 12, 2):
            # PEP 544 prohibits using issubclass()
            # with protocols that have non-method members.
            # See gh-113320 for why we compute this attribute here,
            # rather than in `_ProtocolMeta.__init__`
            cls.__non_callable_proto_members__ = set()
            for attr in cls.__protocol_attrs__:
                try:
                    is_callable = callable(getattr(cls, attr, None))
                except Exception as e:
                    raise TypeError(
                        f"Failed to determine whether protocol member {attr!r} "
                        "is a method member"
                    ) from e
                else:
                    if not is_callable:
                        cls.__non_callable_proto_members__.add(attr)

        return cls


# The "runtime" alias exists for backwards compatibility.
runtime = runtime_checkable


# Our version of runtime-checkable protocols is faster on Python 3.8-3.11
if sys.version_info >= (3, 12):
    SupportsInt = typing.SupportsInt
    SupportsFloat = typing.SupportsFloat
    SupportsComplex = typing.SupportsComplex
    SupportsBytes = typing.SupportsBytes
    SupportsIndex = typing.SupportsIndex
    SupportsAbs = typing.SupportsAbs
    SupportsRound = typing.SupportsRound
else:
    @runtime_checkable
    class SupportsInt(Protocol):
        """An ABC with one abstract method __int__."""
        __slots__ = ()

        @abc.abstractmethod
        def __int__(self) -> int:
            pass

    @runtime_checkable
    class SupportsFloat(Protocol):
        """An ABC with one abstract method __float__."""
        __slots__ = ()

        @abc.abstractmethod
        def __float__(self) -> float:
            pass

    @runtime_checkable
    class SupportsComplex(Protocol):
        """An ABC with one abstract method __complex__."""
        __slots__ = ()

        @abc.abstractmethod
        def __complex__(self) -> complex:
            pass

    @runtime_checkable
    class SupportsBytes(Protocol):
        """An ABC with one abstract method __bytes__."""
        __slots__ = ()

        @abc.abstractmethod
        def __bytes__(self) -> bytes:
            pass

    @runtime_checkable
    class SupportsIndex(Protocol):
        __slots__ = ()

        @abc.abstractmethod
        def __index__(self) -> int:
            pass

    @runtime_checkable
    class SupportsAbs(Protocol[T_co]):
        """
        An ABC with one abstract method __abs__ that is covariant in its return type.
        """
        __slots__ = ()

        @abc.abstractmethod
        def __abs__(self) -> T_co:
            pass

    @runtime_checkable
    class SupportsRound(Protocol[T_co]):
        """
        An ABC with one abstract method __round__ that is covariant in its return type.
        """
        __slots__ = ()

        @abc.abstractmethod
        def __round__(self, ndigits: int = 0) -> T_co:
            pass


def _ensure_subclassable(mro_entries):
    def inner(func):
        if sys.implementation.name == "pypy" and sys.version_info < (3, 9):
            cls_dict = {
                "__call__": staticmethod(func),
                "__mro_entries__": staticmethod(mro_entries)
            }
            t = type(func.__name__, (), cls_dict)
            return functools.update_wrapper(t(), func)
        else:
            func.__mro_entries__ = mro_entries
            return func
    return inner


_NEEDS_SINGLETONMETA = (
    not hasattr(typing, "NoDefault") or not hasattr(typing, "NoExtraItems")
)

if _NEEDS_SINGLETONMETA:
    class SingletonMeta(type):
        def __setattr__(cls, attr, value):
            # TypeError is consistent with the behavior of NoneType
            raise TypeError(
                f"cannot set {attr!r} attribute of immutable type {cls.__name__!r}"
            )


if hasattr(typing, "NoDefault"):
    NoDefault = typing.NoDefault
else:
    class NoDefaultType(metaclass=SingletonMeta):
        """The type of the NoDefault singleton."""

        __slots__ = ()

        def __new__(cls):
            return globals().get("NoDefault") or object.__new__(cls)

        def __repr__(self):
            return "typing_extensions.NoDefault"

        def __reduce__(self):
            return "NoDefault"

    NoDefault = NoDefaultType()
    del NoDefaultType

if hasattr(typing, "NoExtraItems"):
    NoExtraItems = typing.NoExtraItems
else:
    class NoExtraItemsType(metaclass=SingletonMeta):
        """The type of the NoExtraItems singleton."""

        __slots__ = ()

        def __new__(cls):
            return globals().get("NoExtraItems") or object.__new__(cls)

        def __repr__(self):
            return "typing_extensions.NoExtraItems"

        def __reduce__(self):
            return "NoExtraItems"

    NoExtraItems = NoExtraItemsType()
    del NoExtraItemsType

if _NEEDS_SINGLETONMETA:
    del SingletonMeta


# Update this to something like >=3.13.0b1 if and when
# PEP 728 is implemented in CPython
_PEP_728_IMPLEMENTED = False

if _PEP_728_IMPLEMENTED:
    # The standard library TypedDict in Python 3.8 does not store runtime information
    # about which (if any) keys are optional.  See https://bugs.python.org/issue38834
    # The standard library TypedDict in Python 3.9.0/1 does not honour the "total"
    # keyword with old-style TypedDict().  See https://bugs.python.org/issue42059
    # The standard library TypedDict below Python 3.11 does not store runtime
    # information about optional and required keys when using Required or NotRequired.
    # Generic TypedDicts are also impossible using typing.TypedDict on Python <3.11.
    # Aaaand on 3.12 we add __orig_bases__ to TypedDict
    # to enable better runtime introspection.
    # On 3.13 we deprecate some odd ways of creating TypedDicts.
    # Also on 3.13, PEP 705 adds the ReadOnly[] qualifier.
    # PEP 728 (still pending) makes more changes.
    TypedDict = typing.TypedDict
    _TypedDictMeta = typing._TypedDictMeta
    is_typeddict = typing.is_typeddict
else:
    # 3.10.0 and later
    _TAKES_MODULE = "module" in inspect.signature(typing._type_check).parameters

    def _get_typeddict_qualifiers(annotation_type):
        while True:
            annotation_origin = get_origin(annotation_type)
            if annotation_origin is Annotated:
                annotation_args = get_args(annotation_type)
                if annotation_args:
                    annotation_type = annotation_args[0]
                else:
                    break
            elif annotation_origin is Required:
                yield Required
                annotation_type, = get_args(annotation_type)
            elif annotation_origin is NotRequired:
                yield NotRequired
                annotation_type, = get_args(annotation_type)
            elif annotation_origin is ReadOnly:
                yield ReadOnly
                annotation_type, = get_args(annotation_type)
            else:
                break

    class _TypedDictMeta(type):

        def __new__(cls, name, bases, ns, *, total=True, closed=None,
                    extra_items=NoExtraItems):
            """Create new typed dict class object.

            This method is called when TypedDict is subclassed,
            or when TypedDict is instantiated. This way
            TypedDict supports all three syntax forms described in its docstring.
            Subclasses and instances of TypedDict return actual dictionaries.
            """
            for base in bases:
                if type(base) is not _TypedDictMeta and base is not typing.Generic:
                    raise TypeError('cannot inherit from both a TypedDict type '
                                    'and a non-TypedDict base class')
            if closed is not None and extra_items is not NoExtraItems:
                raise TypeError(f"Cannot combine closed={closed!r} and extra_items")

            if any(issubclass(b, typing.Generic) for b in bases):
                generic_base = (typing.Generic,)
            else:
                generic_base = ()

            # typing.py generally doesn't let you inherit from plain Generic, unless
            # the name of the class happens to be "Protocol"
            tp_dict = type.__new__(_TypedDictMeta, "Protocol", (*generic_base, dict), ns)
            tp_dict.__name__ = name
            if tp_dict.__qualname__ == "Protocol":
                tp_dict.__qualname__ = name

            if not hasattr(tp_dict, '__orig_bases__'):
                tp_dict.__orig_bases__ = bases

            annotations = {}
            if "__annotations__" in ns:
                own_annotations = ns["__annotations__"]
            elif "__annotate__" in ns:
                # TODO: Use inspect.VALUE here, and make the annotations lazily evaluated
                own_annotations = ns["__annotate__"](1)
            else:
                own_annotations = {}
            msg = "TypedDict('Name', {f0: t0, f1: t1, ...}); each t must be a type"
            if _TAKES_MODULE:
                own_annotations = {
                    n: typing._type_check(tp, msg, module=tp_dict.__module__)
                    for n, tp in own_annotations.items()
                }
            else:
                own_annotations = {
                    n: typing._type_check(tp, msg)
                    for n, tp in own_annotations.items()
                }
            required_keys = set()
            optional_keys = set()
            readonly_keys = set()
            mutable_keys = set()
            extra_items_type = extra_items

            for base in bases:
                base_dict = base.__dict__

                annotations.update(base_dict.get('__annotations__', {}))
                required_keys.update(base_dict.get('__required_keys__', ()))
                optional_keys.update(base_dict.get('__optional_keys__', ()))
                readonly_keys.update(base_dict.get('__readonly_keys__', ()))
                mutable_keys.update(base_dict.get('__mutable_keys__', ()))

            # This was specified in an earlier version of PEP 728. Support
            # is retained for backwards compatibility, but only for Python
            # 3.13 and lower.
            if (closed and sys.version_info < (3, 14)
                       and "__extra_items__" in own_annotations):
                annotation_type = own_annotations.pop("__extra_items__")
                qualifiers = set(_get_typeddict_qualifiers(annotation_type))
                if Required in qualifiers:
                    raise TypeError(
                        "Special key __extra_items__ does not support "
                        "Required"
                    )
                if NotRequired in qualifiers:
                    raise TypeError(
                        "Special key __extra_items__ does not support "
                        "NotRequired"
                    )
                extra_items_type = annotation_type

            annotations.update(own_annotations)
            for annotation_key, annotation_type in own_annotations.items():
                qualifiers = set(_get_typeddict_qualifiers(annotation_type))

                if Required in qualifiers:
                    required_keys.add(annotation_key)
                elif NotRequired in qualifiers:
                    optional_keys.add(annotation_key)
                elif total:
                    required_keys.add(annotation_key)
                else:
                    optional_keys.add(annotation_key)
                if ReadOnly in qualifiers:
                    mutable_keys.discard(annotation_key)
                    readonly_keys.add(annotation_key)
                else:
                    mutable_keys.add(annotation_key)
                    readonly_keys.discard(annotation_key)

            tp_dict.__annotations__ = annotations
            tp_dict.__required_keys__ = frozenset(required_keys)
            tp_dict.__optional_keys__ = frozenset(optional_keys)
            tp_dict.__readonly_keys__ = frozenset(readonly_keys)
            tp_dict.__mutable_keys__ = frozenset(mutable_keys)
            tp_dict.__total__ = total
            tp_dict.__closed__ = closed
            tp_dict.__extra_items__ = extra_items_type
            return tp_dict

        __call__ = dict  # static method

        def __subclasscheck__(cls, other):
            # Typed dicts are only for static structural subtyping.
            raise TypeError('TypedDict does not support instance and class checks')

        __instancecheck__ = __subclasscheck__

    _TypedDict = type.__new__(_TypedDictMeta, 'TypedDict', (), {})

    @_ensure_subclassable(lambda bases: (_TypedDict,))
    def TypedDict(
        typename,
        fields=_marker,
        /,
        *,
        total=True,
        closed=None,
        extra_items=NoExtraItems,
        **kwargs
    ):
        """A simple typed namespace. At runtime it is equivalent to a plain dict.

        TypedDict creates a dictionary type such that a type checker will expect all
        instances to have a certain set of keys, where each key is
        associated with a value of a consistent type. This expectation
        is not checked at runtime.

        Usage::

            class Point2D(TypedDict):
                x: int
                y: int
                label: str

            a: Point2D = {'x': 1, 'y': 2, 'label': 'good'}  # OK
            b: Point2D = {'z': 3, 'label': 'bad'}           # Fails type check

            assert Point2D(x=1, y=2, label='first') == dict(x=1, y=2, label='first')

        The type info can be accessed via the Point2D.__annotations__ dict, and
        the Point2D.__required_keys__ and Point2D.__optional_keys__ frozensets.
        TypedDict supports an additional equivalent form::

            Point2D = TypedDict('Point2D', {'x': int, 'y': int, 'label': str})

        By default, all keys must be present in a TypedDict. It is possible
        to override this by specifying totality::

            class Point2D(TypedDict, total=False):
                x: int
                y: int

        This means that a Point2D TypedDict can have any of the keys omitted. A type
        checker is only expected to support a literal False or True as the value of
        the total argument. True is the default, and makes all items defined in the
        class body be required.

        The Required and NotRequired special forms can also be used to mark
        individual keys as being required or not required::

            class Point2D(TypedDict):
                x: int  # the "x" key must always be present (Required is the default)
                y: NotRequired[int]  # the "y" key can be omitted

        See PEP 655 for more details on Required and NotRequired.
        """
        if fields is _marker or fields is None:
            if fields is _marker:
                deprecated_thing = "Failing to pass a value for the 'fields' parameter"
            else:
                deprecated_thing = "Passing `None` as the 'fields' parameter"

            example = f"`{typename} = TypedDict({typename!r}, {{}})`"
            deprecation_msg = (
                f"{deprecated_thing} is deprecated and will be disallowed in "
                "Python 3.15. To create a TypedDict class with 0 fields "
                "using the functional syntax, pass an empty dictionary, e.g. "
            ) + example + "."
            warnings.warn(deprecation_msg, DeprecationWarning, stacklevel=2)
            # Support a field called "closed"
            if closed is not False and closed is not True and closed is not None:
                kwargs["closed"] = closed
                closed = None
            # Or "extra_items"
            if extra_items is not NoExtraItems:
                kwargs["extra_items"] = extra_items
                extra_items = NoExtraItems
            fields = kwargs
        elif kwargs:
            raise TypeError("TypedDict takes either a dict or keyword arguments,"
                            " but not both")
        if kwargs:
            if sys.version_info >= (3, 13):
                raise TypeError("TypedDict takes no keyword arguments")
            warnings.warn(
                "The kwargs-based syntax for TypedDict definitions is deprecated "
                "in Python 3.11, will be removed in Python 3.13, and may not be "
                "understood by third-party type checkers.",
                DeprecationWarning,
                stacklevel=2,
            )

        ns = {'__annotations__': dict(fields)}
        module = _caller()
        if module is not None:
            # Setting correct module is necessary to make typed dict classes pickleable.
            ns['__module__'] = module

        td = _TypedDictMeta(typename, (), ns, total=total, closed=closed,
                            extra_items=extra_items)
        td.__orig_bases__ = (TypedDict,)
        return td

    if hasattr(typing, "_TypedDictMeta"):
        _TYPEDDICT_TYPES = (typing._TypedDictMeta, _TypedDictMeta)
    else:
        _TYPEDDICT_TYPES = (_TypedDictMeta,)

    def is_typeddict(tp):
        """Check if an annotation is a TypedDict class

        For example::
            class Film(TypedDict):
                title: str
                year: int

            is_typeddict(Film)  # => True
            is_typeddict(Union[list, str])  # => False
        """
        # On 3.8, this would otherwise return True
        if hasattr(typing, "TypedDict") and tp is typing.TypedDict:
            return False
        return isinstance(tp, _TYPEDDICT_TYPES)


if hasattr(typing, "assert_type"):
    assert_type = typing.assert_type

else:
    def assert_type(val, typ, /):
        """Assert (to the type checker) that the value is of the given type.

        When the type checker encounters a call to assert_type(), it
        emits an error if the value is not of the specified type::

            def greet(name: str) -> None:
                assert_type(name, str)  # ok
                assert_type(name, int)  # type checker error

        At runtime this returns the first argument unchanged and otherwise
        does nothing.
        """
        return val


if hasattr(typing, "ReadOnly"):  # 3.13+
    get_type_hints = typing.get_type_hints
else:  # <=3.13
    # replaces _strip_annotations()
    def _strip_extras(t):
        """Strips Annotated, Required and NotRequired from a given type."""
        if isinstance(t, _AnnotatedAlias):
            return _strip_extras(t.__origin__)
        if hasattr(t, "__origin__") and t.__origin__ in (Required, NotRequired, ReadOnly):
            return _strip_extras(t.__args__[0])
        if isinstance(t, typing._GenericAlias):
            stripped_args = tuple(_strip_extras(a) for a in t.__args__)
            if stripped_args == t.__args__:
                return t
            return t.copy_with(stripped_args)
        if hasattr(_types, "GenericAlias") and isinstance(t, _types.GenericAlias):
            stripped_args = tuple(_strip_extras(a) for a in t.__args__)
            if stripped_args == t.__args__:
                return t
            return _types.GenericAlias(t.__origin__, stripped_args)
        if hasattr(_types, "UnionType") and isinstance(t, _types.UnionType):
            stripped_args = tuple(_strip_extras(a) for a in t.__args__)
            if stripped_args == t.__args__:
                return t
            return functools.reduce(operator.or_, stripped_args)

        return t

    def get_type_hints(obj, globalns=None, localns=None, include_extras=False):
        """Return type hints for an object.

        This is often the same as obj.__annotations__, but it handles
        forward references encoded as string literals, adds Optional[t] if a
        default value equal to None is set and recursively replaces all
        'Annotated[T, ...]', 'Required[T]' or 'NotRequired[T]' with 'T'
        (unless 'include_extras=True').

        The argument may be a module, class, method, or function. The annotations
        are returned as a dictionary. For classes, annotations include also
        inherited members.

        TypeError is raised if the argument is not of a type that can contain
        annotations, and an empty dictionary is returned if no annotations are
        present.

        BEWARE -- the behavior of globalns and localns is counterintuitive
        (unless you are familiar with how eval() and exec() work).  The
        search order is locals first, then globals.

        - If no dict arguments are passed, an attempt is made to use the
          globals from obj (or the respective module's globals for classes),
          and these are also used as the locals.  If the object does not appear
          to have globals, an empty dictionary is used.

        - If one dict argument is passed, it is used for both globals and
          locals.

        - If two dict arguments are passed, they specify globals and
          locals, respectively.
        """
        if hasattr(typing, "Annotated"):  # 3.9+
            hint = typing.get_type_hints(
                obj, globalns=globalns, localns=localns, include_extras=True
            )
        else:  # 3.8
            hint = typing.get_type_hints(obj, globalns=globalns, localns=localns)
        if sys.version_info < (3, 11):
            _clean_optional(obj, hint, globalns, localns)
        if sys.version_info < (3, 9):
            # In 3.8 eval_type does not flatten Optional[ForwardRef] correctly
            # This will recreate and and cache Unions.
            hint = {
                k: (t
                    if get_origin(t) != Union
                    else Union[t.__args__])
                for k, t in hint.items()
            }
        if include_extras:
            return hint
        return {k: _strip_extras(t) for k, t in hint.items()}

    _NoneType = type(None)

    def _could_be_inserted_optional(t):
        """detects Union[..., None] pattern"""
        # 3.8+ compatible checking before _UnionGenericAlias
        if get_origin(t) is not Union:
            return False
        # Assume if last argument is not None they are user defined
        if t.__args__[-1] is not _NoneType:
            return False
        return True

    # < 3.11
    def _clean_optional(obj, hints, globalns=None, localns=None):
        # reverts injected Union[..., None] cases from typing.get_type_hints
        # when a None default value is used.
        # see https://github.com/python/typing_extensions/issues/310
        if not hints or isinstance(obj, type):
            return
        defaults = typing._get_defaults(obj)  # avoid accessing __annotations___
        if not defaults:
            return
        original_hints = obj.__annotations__
        for name, value in hints.items():
            # Not a Union[..., None] or replacement conditions not fullfilled
            if (not _could_be_inserted_optional(value)
                or name not in defaults
                or defaults[name] is not None
            ):
                continue
            original_value = original_hints[name]
            # value=NoneType should have caused a skip above but check for safety
            if original_value is None:
                original_value = _NoneType
            # Forward reference
            if isinstance(original_value, str):
                if globalns is None:
                    if isinstance(obj, _types.ModuleType):
                        globalns = obj.__dict__
                    else:
                        nsobj = obj
                        # Find globalns for the unwrapped object.
                        while hasattr(nsobj, '__wrapped__'):
                            nsobj = nsobj.__wrapped__
                        globalns = getattr(nsobj, '__globals__', {})
                    if localns is None:
                        localns = globalns
                elif localns is None:
                    localns = globalns
                if sys.version_info < (3, 9):
                    original_value = ForwardRef(original_value)
                else:
                    original_value = ForwardRef(
                        original_value,
                        is_argument=not isinstance(obj, _types.ModuleType)
                    )
            original_evaluated = typing._eval_type(original_value, globalns, localns)
            if sys.version_info < (3, 9) and get_origin(original_evaluated) is Union:
                # Union[str, None, "str"] is not reduced to Union[str, None]
                original_evaluated = Union[original_evaluated.__args__]
            # Compare if values differ. Note that even if equal
            # value might be cached by typing._tp_cache contrary to original_evaluated
            if original_evaluated != value or (
                # 3.10: ForwardRefs of UnionType might be turned into _UnionGenericAlias
                hasattr(_types, "UnionType")
                and isinstance(original_evaluated, _types.UnionType)
                and not isinstance(value, _types.UnionType)
            ):
                hints[name] = original_evaluated

# Python 3.9+ has PEP 593 (Annotated)
if hasattr(typing, 'Annotated'):
    Annotated = typing.Annotated
    # Not exported and not a public API, but needed for get_origin() and get_args()
    # to work.
    _AnnotatedAlias = typing._AnnotatedAlias
# 3.8
else:
    class _AnnotatedAlias(typing._GenericAlias, _root=True):
        """Runtime representation of an annotated type.

        At its core 'Annotated[t, dec1, dec2, ...]' is an alias for the type 't'
        with extra annotations. The alias behaves like a normal typing alias,
        instantiating is the same as instantiating the underlying type, binding
        it to types is also the same.
        """
        def __init__(self, origin, metadata):
            if isinstance(origin, _AnnotatedAlias):
                metadata = origin.__metadata__ + metadata
                origin = origin.__origin__
            super().__init__(origin, origin)
            self.__metadata__ = metadata

        def copy_with(self, params):
            assert len(params) == 1
            new_type = params[0]
            return _AnnotatedAlias(new_type, self.__metadata__)

        def __repr__(self):
            return (f"typing_extensions.Annotated[{typing._type_repr(self.__origin__)}, "
                    f"{', '.join(repr(a) for a in self.__metadata__)}]")

        def __reduce__(self):
            return operator.getitem, (
                Annotated, (self.__origin__, *self.__metadata__)
            )

        def __eq__(self, other):
            if not isinstance(other, _AnnotatedAlias):
                return NotImplemented
            if self.__origin__ != other.__origin__:
                return False
            return self.__metadata__ == other.__metadata__

        def __hash__(self):
            return hash((self.__origin__, self.__metadata__))

    class Annotated:
        """Add context specific metadata to a type.

        Example: Annotated[int, runtime_check.Unsigned] indicates to the
        hypothetical runtime_check module that this type is an unsigned int.
        Every other consumer of this type can ignore this metadata and treat
        this type as int.

        The first argument to Annotated must be a valid type (and will be in
        the __origin__ field), the remaining arguments are kept as a tuple in
        the __extra__ field.

        Details:

        - It's an error to call `Annotated` with less than two arguments.
        - Nested Annotated are flattened::

            Annotated[Annotated[T, Ann1, Ann2], Ann3] == Annotated[T, Ann1, Ann2, Ann3]

        - Instantiating an annotated type is equivalent to instantiating the
        underlying type::

            Annotated[C, Ann1](5) == C(5)

        - Annotated can be used as a generic type alias::

            Optimized = Annotated[T, runtime.Optimize()]
            Optimized[int] == Annotated[int, runtime.Optimize()]

            OptimizedList = Annotated[List[T], runtime.Optimize()]
            OptimizedList[int] == Annotated[List[int], runtime.Optimize()]
        """

        __slots__ = ()

        def __new__(cls, *args, **kwargs):
            raise TypeError("Type Annotated cannot be instantiated.")

        @typing._tp_cache
        def __class_getitem__(cls, params):
            if not isinstance(params, tuple) or len(params) < 2:
                raise TypeError("Annotated[...] should be used "
                                "with at least two arguments (a type and an "
                                "annotation).")
            allowed_special_forms = (ClassVar, Final)
            if get_origin(params[0]) in allowed_special_forms:
                origin = params[0]
            else:
                msg = "Annotated[t, ...]: t must be a type."
                origin = typing._type_check(params[0], msg)
            metadata = tuple(params[1:])
            return _AnnotatedAlias(origin, metadata)

        def __init_subclass__(cls, *args, **kwargs):
            raise TypeError(
                f"Cannot subclass {cls.__module__}.Annotated"
            )

# Python 3.8 has get_origin() and get_args() but those implementations aren't
# Annotated-aware, so we can't use those. Python 3.9's versions don't support
# ParamSpecArgs and ParamSpecKwargs, so only Python 3.10's versions will do.
if sys.version_info[:2] >= (3, 10):
    get_origin = typing.get_origin
    get_args = typing.get_args
# 3.8-3.9
else:
    try:
        # 3.9+
        from typing import _BaseGenericAlias
    except ImportError:
        _BaseGenericAlias = typing._GenericAlias
    try:
        # 3.9+
        from typing import GenericAlias as _typing_GenericAlias
    except ImportError:
        _typing_GenericAlias = typing._GenericAlias

    def get_origin(tp):
        """Get the unsubscripted version of a type.

        This supports generic types, Callable, Tuple, Union, Literal, Final, ClassVar
        and Annotated. Return None for unsupported types. Examples::

            get_origin(Literal[42]) is Literal
            get_origin(int) is None
            get_origin(ClassVar[int]) is ClassVar
            get_origin(Generic) is Generic
            get_origin(Generic[T]) is Generic
            get_origin(Union[T, int]) is Union
            get_origin(List[Tuple[T, T]][int]) == list
            get_origin(P.args) is P
        """
        if isinstance(tp, _AnnotatedAlias):
            return Annotated
        if isinstance(tp, (typing._GenericAlias, _typing_GenericAlias, _BaseGenericAlias,
                           ParamSpecArgs, ParamSpecKwargs)):
            return tp.__origin__
        if tp is typing.Generic:
            return typing.Generic
        return None

    def get_args(tp):
        """Get type arguments with all substitutions performed.

        For unions, basic simplifications used by Union constructor are performed.
        Examples::
            get_args(Dict[str, int]) == (str, int)
            get_args(int) == ()
            get_args(Union[int, Union[T, int], str][int]) == (int, str)
            get_args(Union[int, Tuple[T, int]][str]) == (int, Tuple[str, int])
            get_args(Callable[[], T][int]) == ([], int)
        """
        if isinstance(tp, _AnnotatedAlias):
            return (tp.__origin__, *tp.__metadata__)
        if isinstance(tp, (typing._GenericAlias, _typing_GenericAlias)):
            if getattr(tp, "_special", False):
                return ()
            res = tp.__args__
            if get_origin(tp) is collections.abc.Callable and res[0] is not Ellipsis:
                res = (list(res[:-1]), res[-1])
            return res
        return ()


# 3.10+
if hasattr(typing, 'TypeAlias'):
    TypeAlias = typing.TypeAlias
# 3.9
elif sys.version_info[:2] >= (3, 9):
    @_ExtensionsSpecialForm
    def TypeAlias(self, parameters):
        """Special marker indicating that an assignment should
        be recognized as a proper type alias definition by type
        checkers.

        For example::

            Predicate: TypeAlias = Callable[..., bool]

        It's invalid when used anywhere except as in the example above.
        """
        raise TypeError(f"{self} is not subscriptable")
# 3.8
else:
    TypeAlias = _ExtensionsSpecialForm(
        'TypeAlias',
        doc="""Special marker indicating that an assignment should
        be recognized as a proper type alias definition by type
        checkers.

        For example::

            Predicate: TypeAlias = Callable[..., bool]

        It's invalid when used anywhere except as in the example
        above."""
    )


def _set_default(type_param, default):
    type_param.has_default = lambda: default is not NoDefault
    type_param.__default__ = default


def _set_module(typevarlike):
    # for pickling:
    def_mod = _caller(depth=3)
    if def_mod != 'typing_extensions':
        typevarlike.__module__ = def_mod


class _DefaultMixin:
    """Mixin for TypeVarLike defaults."""

    __slots__ = ()
    __init__ = _set_default


# Classes using this metaclass must provide a _backported_typevarlike ClassVar
class _TypeVarLikeMeta(type):
    def __instancecheck__(cls, __instance: Any) -> bool:
        return isinstance(__instance, cls._backported_typevarlike)


if _PEP_696_IMPLEMENTED:
    from typing import TypeVar
else:
    # Add default and infer_variance parameters from PEP 696 and 695
    class TypeVar(metaclass=_TypeVarLikeMeta):
        """Type variable."""

        _backported_typevarlike = typing.TypeVar

        def __new__(cls, name, *constraints, bound=None,
                    covariant=False, contravariant=False,
                    default=NoDefault, infer_variance=False):
            if hasattr(typing, "TypeAliasType"):
                # PEP 695 implemented (3.12+), can pass infer_variance to typing.TypeVar
                typevar = typing.TypeVar(name, *constraints, bound=bound,
                                         covariant=covariant, contravariant=contravariant,
                                         infer_variance=infer_variance)
            else:
                typevar = typing.TypeVar(name, *constraints, bound=bound,
                                         covariant=covariant, contravariant=contravariant)
                if infer_variance and (covariant or contravariant):
                    raise ValueError("Variance cannot be specified with infer_variance.")
                typevar.__infer_variance__ = infer_variance

            _set_default(typevar, default)
            _set_module(typevar)

            def _tvar_prepare_subst(alias, args):
                if (
                    typevar.has_default()
                    and alias.__parameters__.index(typevar) == len(args)
                ):
                    args += (typevar.__default__,)
                return args

            typevar.__typing_prepare_subst__ = _tvar_prepare_subst
            return typevar

        def __init_subclass__(cls) -> None:
            raise TypeError(f"type '{__name__}.TypeVar' is not an acceptable base type")


# Python 3.10+ has PEP 612
if hasattr(typing, 'ParamSpecArgs'):
    ParamSpecArgs = typing.ParamSpecArgs
    ParamSpecKwargs = typing.ParamSpecKwargs
# 3.8-3.9
else:
    class _Immutable:
        """Mixin to indicate that object should not be copied."""
        __slots__ = ()

        def __copy__(self):
            return self

        def __deepcopy__(self, memo):
            return self

    class ParamSpecArgs(_Immutable):
        """The args for a ParamSpec object.

        Given a ParamSpec object P, P.args is an instance of ParamSpecArgs.

        ParamSpecArgs objects have a reference back to their ParamSpec:

        P.args.__origin__ is P

        This type is meant for runtime introspection and has no special meaning to
        static type checkers.
        """
        def __init__(self, origin):
            self.__origin__ = origin

        def __repr__(self):
            return f"{self.__origin__.__name__}.args"

        def __eq__(self, other):
            if not isinstance(other, ParamSpecArgs):
                return NotImplemented
            return self.__origin__ == other.__origin__

    class ParamSpecKwargs(_Immutable):
        """The kwargs for a ParamSpec object.

        Given a ParamSpec object P, P.kwargs is an instance of ParamSpecKwargs.

        ParamSpecKwargs objects have a reference back to their ParamSpec:

        P.kwargs.__origin__ is P

        This type is meant for runtime introspection and has no special meaning to
        static type checkers.
        """
        def __init__(self, origin):
            self.__origin__ = origin

        def __repr__(self):
            return f"{self.__origin__.__name__}.kwargs"

        def __eq__(self, other):
            if not isinstance(other, ParamSpecKwargs):
                return NotImplemented
            return self.__origin__ == other.__origin__


if _PEP_696_IMPLEMENTED:
    from typing import ParamSpec

# 3.10+
elif hasattr(typing, 'ParamSpec'):

    # Add default parameter - PEP 696
    class ParamSpec(metaclass=_TypeVarLikeMeta):
        """Parameter specification."""

        _backported_typevarlike = typing.ParamSpec

        def __new__(cls, name, *, bound=None,
                    covariant=False, contravariant=False,
                    infer_variance=False, default=NoDefault):
            if hasattr(typing, "TypeAliasType"):
                # PEP 695 implemented, can pass infer_variance to typing.TypeVar
                paramspec = typing.ParamSpec(name, bound=bound,
                                             covariant=covariant,
                                             contravariant=contravariant,
                                             infer_variance=infer_variance)
            else:
                paramspec = typing.ParamSpec(name, bound=bound,
                                             covariant=covariant,
                                             contravariant=contravariant)
                paramspec.__infer_variance__ = infer_variance

            _set_default(paramspec, default)
            _set_module(paramspec)

            def _paramspec_prepare_subst(alias, args):
                params = alias.__parameters__
                i = params.index(paramspec)
                if i == len(args) and paramspec.has_default():
                    args = [*args, paramspec.__default__]
                if i >= len(args):
                    raise TypeError(f"Too few arguments for {alias}")
                # Special case where Z[[int, str, bool]] == Z[int, str, bool] in PEP 612.
                if len(params) == 1 and not typing._is_param_expr(args[0]):
                    assert i == 0
                    args = (args,)
                # Convert lists to tuples to help other libraries cache the results.
                elif isinstance(args[i], list):
                    args = (*args[:i], tuple(args[i]), *args[i + 1:])
                return args

            paramspec.__typing_prepare_subst__ = _paramspec_prepare_subst
            return paramspec

        def __init_subclass__(cls) -> None:
            raise TypeError(f"type '{__name__}.ParamSpec' is not an acceptable base type")

# 3.8-3.9
else:

    # Inherits from list as a workaround for Callable checks in Python < 3.9.2.
    class ParamSpec(list, _DefaultMixin):
        """Parameter specification variable.

        Usage::

           P = ParamSpec('P')

        Parameter specification variables exist primarily for the benefit of static
        type checkers.  They are used to forward the parameter types of one
        callable to another callable, a pattern commonly found in higher order
        functions and decorators.  They are only valid when used in ``Concatenate``,
        or s the first argument to ``Callable``. In Python 3.10 and higher,
        they are also supported in user-defined Generics at runtime.
        See class Generic for more information on generic types.  An
        example for annotating a decorator::

           T = TypeVar('T')
           P = ParamSpec('P')

           def add_logging(f: Callable[P, T]) -> Callable[P, T]:
               '''A type-safe decorator to add logging to a function.'''
               def inner(*args: P.args, **kwargs: P.kwargs) -> T:
                   logging.info(f'{f.__name__} was called')
                   return f(*args, **kwargs)
               return inner

           @add_logging
           def add_two(x: float, y: float) -> float:
               '''Add two numbers together.'''
               return x + y

        Parameter specification variables defined with covariant=True or
        contravariant=True can be used to declare covariant or contravariant
        generic types.  These keyword arguments are valid, but their actual semantics
        are yet to be decided.  See PEP 612 for details.

        Parameter specification variables can be introspected. e.g.:

           P.__name__ == 'T'
           P.__bound__ == None
           P.__covariant__ == False
           P.__contravariant__ == False

        Note that only parameter specification variables defined in global scope can
        be pickled.
        """

        # Trick Generic __parameters__.
        __class__ = typing.TypeVar

        @property
        def args(self):
            return ParamSpecArgs(self)

        @property
        def kwargs(self):
            return ParamSpecKwargs(self)

        def __init__(self, name, *, bound=None, covariant=False, contravariant=False,
                     infer_variance=False, default=NoDefault):
            list.__init__(self, [self])
            self.__name__ = name
            self.__covariant__ = bool(covariant)
            self.__contravariant__ = bool(contravariant)
            self.__infer_variance__ = bool(infer_variance)
            if bound:
                self.__bound__ = typing._type_check(bound, 'Bound must be a type.')
            else:
                self.__bound__ = None
            _DefaultMixin.__init__(self, default)

            # for pickling:
            def_mod = _caller()
            if def_mod != 'typing_extensions':
                self.__module__ = def_mod

        def __repr__(self):
            if self.__infer_variance__:
                prefix = ''
            elif self.__covariant__:
                prefix = '+'
            elif self.__contravariant__:
                prefix = '-'
            else:
                prefix = '~'
            return prefix + self.__name__

        def __hash__(self):
            return object.__hash__(self)

        def __eq__(self, other):
            return self is other

        def __reduce__(self):
            return self.__name__

        # Hack to get typing._type_check to pass.
        def __call__(self, *args, **kwargs):
            pass


# 3.8-3.9
if not hasattr(typing, 'Concatenate'):
    # Inherits from list as a workaround for Callable checks in Python < 3.9.2.

    # 3.9.0-1
    if not hasattr(typing, '_type_convert'):
        def _type_convert(arg, module=None, *, allow_special_forms=False):
            """For converting None to type(None), and strings to ForwardRef."""
            if arg is None:
                return type(None)
            if isinstance(arg, str):
                if sys.version_info <= (3, 9, 6):
                    return ForwardRef(arg)
                if sys.version_info <= (3, 9, 7):
                    return ForwardRef(arg, module=module)
                return ForwardRef(arg, module=module, is_class=allow_special_forms)
            return arg
    else:
        _type_convert = typing._type_convert

    class _ConcatenateGenericAlias(list):

        # Trick Generic into looking into this for __parameters__.
        __class__ = typing._GenericAlias

        # Flag in 3.8.
        _special = False

        def __init__(self, origin, args):
            super().__init__(args)
            self.__origin__ = origin
            self.__args__ = args

        def __repr__(self):
            _type_repr = typing._type_repr
            return (f'{_type_repr(self.__origin__)}'
                    f'[{", ".join(_type_repr(arg) for arg in self.__args__)}]')

        def __hash__(self):
            return hash((self.__origin__, self.__args__))

        # Hack to get typing._type_check to pass in Generic.
        def __call__(self, *args, **kwargs):
            pass

        @property
        def __parameters__(self):
            return tuple(
                tp for tp in self.__args__ if isinstance(tp, (typing.TypeVar, ParamSpec))
            )

        # 3.8; needed for typing._subst_tvars
        # 3.9 used by __getitem__ below
        def copy_with(self, params):
            if isinstance(params[-1], _ConcatenateGenericAlias):
                params = (*params[:-1], *params[-1].__args__)
            elif isinstance(params[-1], (list, tuple)):
                return (*params[:-1], *params[-1])
            elif (not (params[-1] is ... or isinstance(params[-1], ParamSpec))):
                raise TypeError("The last parameter to Concatenate should be a "
                        "ParamSpec variable or ellipsis.")
            return self.__class__(self.__origin__, params)

        # 3.9; accessed during GenericAlias.__getitem__ when substituting
        def __getitem__(self, args):
            if self.__origin__ in (Generic, Protocol):
                # Can't subscript Generic[...] or Protocol[...].
                raise TypeError(f"Cannot subscript already-subscripted {self}")
            if not self.__parameters__:
                raise TypeError(f"{self} is not a generic class")

            if not isinstance(args, tuple):
                args = (args,)
            args = _unpack_args(*(_type_convert(p) for p in args))
            params = self.__parameters__
            for param in params:
                prepare = getattr(param, "__typing_prepare_subst__", None)
                if prepare is not None:
                    args = prepare(self, args)
                # 3.8 - 3.9 & typing.ParamSpec
                elif isinstance(param, ParamSpec):
                    i = params.index(param)
                    if (
                        i == len(args)
                        and getattr(param, '__default__', NoDefault) is not NoDefault
                    ):
                        args = [*args, param.__default__]
                    if i >= len(args):
                        raise TypeError(f"Too few arguments for {self}")
                    # Special case for Z[[int, str, bool]] == Z[int, str, bool]
                    if len(params) == 1 and not _is_param_expr(args[0]):
                        assert i == 0
                        args = (args,)
                    elif (
                        isinstance(args[i], list)
                        # 3.8 - 3.9
                        # This class inherits from list do not convert
                        and not isinstance(args[i], _ConcatenateGenericAlias)
                    ):
                        args = (*args[:i], tuple(args[i]), *args[i + 1:])

            alen = len(args)
            plen = len(params)
            if alen != plen:
                raise TypeError(
                    f"Too {'many' if alen > plen else 'few'} arguments for {self};"
                    f" actual {alen}, expected {plen}"
                )

            subst = dict(zip(self.__parameters__, args))
            # determine new args
            new_args = []
            for arg in self.__args__:
                if isinstance(arg, type):
                    new_args.append(arg)
                    continue
                if isinstance(arg, TypeVar):
                    arg = subst[arg]
                    if (
                        (isinstance(arg, typing._GenericAlias) and _is_unpack(arg))
                        or (
                            hasattr(_types, "GenericAlias")
                            and isinstance(arg, _types.GenericAlias)
                            and getattr(arg, "__unpacked__", False)
                        )
                    ):
                        raise TypeError(f"{arg} is not valid as type argument")

                elif isinstance(arg,
                    typing._GenericAlias
                    if not hasattr(_types, "GenericAlias") else
                    (typing._GenericAlias, _types.GenericAlias)
                ):
                    subparams = arg.__parameters__
                    if subparams:
                        subargs = tuple(subst[x] for x in subparams)
                        arg = arg[subargs]
                new_args.append(arg)
            return self.copy_with(tuple(new_args))

# 3.10+
else:
    _ConcatenateGenericAlias = typing._ConcatenateGenericAlias

    # 3.10
    if sys.version_info < (3, 11):

        class _ConcatenateGenericAlias(typing._ConcatenateGenericAlias, _root=True):
            # needed for checks in collections.abc.Callable to accept this class
            __module__ = "typing"

            def copy_with(self, params):
                if isinstance(params[-1], (list, tuple)):
                    return (*params[:-1], *params[-1])
                if isinstance(params[-1], typing._ConcatenateGenericAlias):
                    params = (*params[:-1], *params[-1].__args__)
                elif not (params[-1] is ... or isinstance(params[-1], ParamSpec)):
                    raise TypeError("The last parameter to Concatenate should be a "
                            "ParamSpec variable or ellipsis.")
                return super(typing._ConcatenateGenericAlias, self).copy_with(params)

            def __getitem__(self, args):
                value = super().__getitem__(args)
                if isinstance(value, tuple) and any(_is_unpack(t) for t in value):
                    return tuple(_unpack_args(*(n for n in value)))
                return value


# 3.8-3.9.2
class _EllipsisDummy: ...


# 3.8-3.10
def _create_concatenate_alias(origin, parameters):
    if parameters[-1] is ... and sys.version_info < (3, 9, 2):
        # Hack: Arguments must be types, replace it with one.
        parameters = (*parameters[:-1], _EllipsisDummy)
    if sys.version_info >= (3, 10, 3):
        concatenate = _ConcatenateGenericAlias(origin, parameters,
                                        _typevar_types=(TypeVar, ParamSpec),
                                        _paramspec_tvars=True)
    else:
        concatenate = _ConcatenateGenericAlias(origin, parameters)
    if parameters[-1] is not _EllipsisDummy:
        return concatenate
    # Remove dummy again
    concatenate.__args__ = tuple(p if p is not _EllipsisDummy else ...
                                    for p in concatenate.__args__)
    if sys.version_info < (3, 10):
        # backport needs __args__ adjustment only
        return concatenate
    concatenate.__parameters__ = tuple(p for p in concatenate.__parameters__
                                        if p is not _EllipsisDummy)
    return concatenate


# 3.8-3.10
@typing._tp_cache
def _concatenate_getitem(self, parameters):
    if parameters == ():
        raise TypeError("Cannot take a Concatenate of no types.")
    if not isinstance(parameters, tuple):
        parameters = (parameters,)
    if not (parameters[-1] is ... or isinstance(parameters[-1], ParamSpec)):
        raise TypeError("The last parameter to Concatenate should be a "
                        "ParamSpec variable or ellipsis.")
    msg = "Concatenate[arg, ...]: each arg must be a type."
    parameters = (*(typing._type_check(p, msg) for p in parameters[:-1]),
                    parameters[-1])
    return _create_concatenate_alias(self, parameters)


# 3.11+; Concatenate does not accept ellipsis in 3.10
if sys.version_info >= (3, 11):
    Concatenate = typing.Concatenate
# 3.9-3.10
elif sys.version_info[:2] >= (3, 9):
    @_ExtensionsSpecialForm
    def Concatenate(self, parameters):
        """Used in conjunction with ``ParamSpec`` and ``Callable`` to represent a
        higher order function which adds, removes or transforms parameters of a
        callable.

        For example::

           Callable[Concatenate[int, P], int]

        See PEP 612 for detailed information.
        """
        return _concatenate_getitem(self, parameters)
# 3.8
else:
    class _ConcatenateForm(_ExtensionsSpecialForm, _root=True):
        def __getitem__(self, parameters):
            return _concatenate_getitem(self, parameters)

    Concatenate = _ConcatenateForm(
        'Concatenate',
        doc="""Used in conjunction with ``ParamSpec`` and ``Callable`` to represent a
        higher order function which adds, removes or transforms parameters of a
        callable.

        For example::

           Callable[Concatenate[int, P], int]

        See PEP 612 for detailed information.
        """)

# 3.10+
if hasattr(typing, 'TypeGuard'):
    TypeGuard = typing.TypeGuard
# 3.9
elif sys.version_info[:2] >= (3, 9):
    @_ExtensionsSpecialForm
    def TypeGuard(self, parameters):
        """Special typing form used to annotate the return type of a user-defined
        type guard function.  ``TypeGuard`` only accepts a single type argument.
        At runtime, functions marked this way should return a boolean.

        ``TypeGuard`` aims to benefit *type narrowing* -- a technique used by static
        type checkers to determine a more precise type of an expression within a
        program's code flow.  Usually type narrowing is done by analyzing
        conditional code flow and applying the narrowing to a block of code.  The
        conditional expression here is sometimes referred to as a "type guard".

        Sometimes it would be convenient to use a user-defined boolean function
        as a type guard.  Such a function should use ``TypeGuard[...]`` as its
        return type to alert static type checkers to this intention.

        Using  ``-> TypeGuard`` tells the static type checker that for a given
        function:

        1. The return value is a boolean.
        2. If the return value is ``True``, the type of its argument
        is the type inside ``TypeGuard``.

        For example::

            def is_str(val: Union[str, float]):
                # "isinstance" type guard
                if isinstance(val, str):
                    # Type of ``val`` is narrowed to ``str``
                    ...
                else:
                    # Else, type of ``val`` is narrowed to ``float``.
                    ...

        Strict type narrowing is not enforced -- ``TypeB`` need not be a narrower
        form of ``TypeA`` (it can even be a wider form) and this may lead to
        type-unsafe results.  The main reason is to allow for things like
        narrowing ``List[object]`` to ``List[str]`` even though the latter is not
        a subtype of the former, since ``List`` is invariant.  The responsibility of
        writing type-safe type guards is left to the user.

        ``TypeGuard`` also works with type variables.  For more information, see
        PEP 647 (User-Defined Type Guards).
        """
        item = typing._type_check(parameters, f'{self} accepts only a single type.')
        return typing._GenericAlias(self, (item,))
# 3.8
else:
    class _TypeGuardForm(_ExtensionsSpecialForm, _root=True):
        def __getitem__(self, parameters):
            item = typing._type_check(parameters,
                                      f'{self._name} accepts only a single type')
            return typing._GenericAlias(self, (item,))

    TypeGuard = _TypeGuardForm(
        'TypeGuard',
        doc="""Special typing form used to annotate the return type of a user-defined
        type guard function.  ``TypeGuard`` only accepts a single type argument.
        At runtime, functions marked this way should return a boolean.

        ``TypeGuard`` aims to benefit *type narrowing* -- a technique used by static
        type checkers to determine a more precise type of an expression within a
        program's code flow.  Usually type narrowing is done by analyzing
        conditional code flow and applying the narrowing to a block of code.  The
        conditional expression here is sometimes referred to as a "type guard".

        Sometimes it would be convenient to use a user-defined boolean function
        as a type guard.  Such a function should use ``TypeGuard[...]`` as its
        return type to alert static type checkers to this intention.

        Using  ``-> TypeGuard`` tells the static type checker that for a given
        function:

        1. The return value is a boolean.
        2. If the return value is ``True``, the type of its argument
        is the type inside ``TypeGuard``.

        For example::

            def is_str(val: Union[str, float]):
                # "isinstance" type guard
                if isinstance(val, str):
                    # Type of ``val`` is narrowed to ``str``
                    ...
                else:
                    # Else, type of ``val`` is narrowed to ``float``.
                    ...

        Strict type narrowing is not enforced -- ``TypeB`` need not be a narrower
        form of ``TypeA`` (it can even be a wider form) and this may lead to
        type-unsafe results.  The main reason is to allow for things like
        narrowing ``List[object]`` to ``List[str]`` even though the latter is not
        a subtype of the former, since ``List`` is invariant.  The responsibility of
        writing type-safe type guards is left to the user.

        ``TypeGuard`` also works with type variables.  For more information, see
        PEP 647 (User-Defined Type Guards).
        """)

# 3.13+
if hasattr(typing, 'TypeIs'):
    TypeIs = typing.TypeIs
# 3.9
elif sys.version_info[:2] >= (3, 9):
    @_ExtensionsSpecialForm
    def TypeIs(self, parameters):
        """Special typing form used to annotate the return type of a user-defined
        type narrower function.  ``TypeIs`` only accepts a single type argument.
        At runtime, functions marked this way should return a boolean.

        ``TypeIs`` aims to benefit *type narrowing* -- a technique used by static
        type checkers to determine a more precise type of an expression within a
        program's code flow.  Usually type narrowing is done by analyzing
        conditional code flow and applying the narrowing to a block of code.  The
        conditional expression here is sometimes referred to as a "type guard".

        Sometimes it would be convenient to use a user-defined boolean function
        as a type guard.  Such a function should use ``TypeIs[...]`` as its
        return type to alert static type checkers to this intention.

        Using  ``-> TypeIs`` tells the static type checker that for a given
        function:

        1. The return value is a boolean.
        2. If the return value is ``True``, the type of its argument
        is the intersection of the type inside ``TypeIs`` and the argument's
        previously known type.

        For example::

            def is_awaitable(val: object) -> TypeIs[Awaitable[Any]]:
                return hasattr(val, '__await__')

            def f(val: Union[int, Awaitable[int]]) -> int:
                if is_awaitable(val):
                    assert_type(val, Awaitable[int])
                else:
                    assert_type(val, int)

        ``TypeIs`` also works with type variables.  For more information, see
        PEP 742 (Narrowing types with TypeIs).
        """
        item = typing._type_check(parameters, f'{self} accepts only a single type.')
        return typing._GenericAlias(self, (item,))
# 3.8
else:
    class _TypeIsForm(_ExtensionsSpecialForm, _root=True):
        def __getitem__(self, parameters):
            item = typing._type_check(parameters,
                                      f'{self._name} accepts only a single type')
            return typing._GenericAlias(self, (item,))

    TypeIs = _TypeIsForm(
        'TypeIs',
        doc="""Special typing form used to annotate the return type of a user-defined
        type narrower function.  ``TypeIs`` only accepts a single type argument.
        At runtime, functions marked this way should return a boolean.

        ``TypeIs`` aims to benefit *type narrowing* -- a technique used by static
        type checkers to determine a more precise type of an expression within a
        program's code flow.  Usually type narrowing is done by analyzing
        conditional code flow and applying the narrowing to a block of code.  The
        conditional expression here is sometimes referred to as a "type guard".

        Sometimes it would be convenient to use a user-defined boolean function
        as a type guard.  Such a function should use ``TypeIs[...]`` as its
        return type to alert static type checkers to this intention.

        Using  ``-> TypeIs`` tells the static type checker that for a given
        function:

        1. The return value is a boolean.
        2. If the return value is ``True``, the type of its argument
        is the intersection of the type inside ``TypeIs`` and the argument's
        previously known type.

        For example::

            def is_awaitable(val: object) -> TypeIs[Awaitable[Any]]:
                return hasattr(val, '__await__')

            def f(val: Union[int, Awaitable[int]]) -> int:
                if is_awaitable(val):
                    assert_type(val, Awaitable[int])
                else:
                    assert_type(val, int)

        ``TypeIs`` also works with type variables.  For more information, see
        PEP 742 (Narrowing types with TypeIs).
        """)

# 3.14+?
if hasattr(typing, 'TypeForm'):
    TypeForm = typing.TypeForm
# 3.9
elif sys.version_info[:2] >= (3, 9):
    class _TypeFormForm(_ExtensionsSpecialForm, _root=True):
        # TypeForm(X) is equivalent to X but indicates to the type checker
        # that the object is a TypeForm.
        def __call__(self, obj, /):
            return obj

    @_TypeFormForm
    def TypeForm(self, parameters):
        """A special form representing the value that results from the evaluation
        of a type expression. This value encodes the information supplied in the
        type expression, and it represents the type described by that type expression.

        When used in a type expression, TypeForm describes a set of type form objects.
        It accepts a single type argument, which must be a valid type expression.
        ``TypeForm[T]`` describes the set of all type form objects that represent
        the type T or types that are assignable to T.

        Usage:

            def cast[T](typ: TypeForm[T], value: Any) -> T: ...

            reveal_type(cast(int, "x"))  # int

        See PEP 747 for more information.
        """
        item = typing._type_check(parameters, f'{self} accepts only a single type.')
        return typing._GenericAlias(self, (item,))
# 3.8
else:
    class _TypeFormForm(_ExtensionsSpecialForm, _root=True):
        def __getitem__(self, parameters):
            item = typing._type_check(parameters,
                                      f'{self._name} accepts only a single type')
            return typing._GenericAlias(self, (item,))

        def __call__(self, obj, /):
            return obj

    TypeForm = _TypeFormForm(
        'TypeForm',
        doc="""A special form representing the value that results from the evaluation
        of a type expression. This value encodes the information supplied in the
        type expression, and it represents the type described by that type expression.

        When used in a type expression, TypeForm describes a set of type form objects.
        It accepts a single type argument, which must be a valid type expression.
        ``TypeForm[T]`` describes the set of all type form objects that represent
        the type T or types that are assignable to T.

        Usage:

            def cast[T](typ: TypeForm[T], value: Any) -> T: ...

            reveal_type(cast(int, "x"))  # int

        See PEP 747 for more information.
        """)


# Vendored from cpython typing._SpecialFrom
class _SpecialForm(typing._Final, _root=True):
    __slots__ = ('_name', '__doc__', '_getitem')

    def __init__(self, getitem):
        self._getitem = getitem
        self._name = getitem.__name__
        self.__doc__ = getitem.__doc__

    def __getattr__(self, item):
        if item in {'__name__', '__qualname__'}:
            return self._name

        raise AttributeError(item)

    def __mro_entries__(self, bases):
        raise TypeError(f"Cannot subclass {self!r}")

    def __repr__(self):
        return f'typing_extensions.{self._name}'

    def __reduce__(self):
        return self._name

    def __call__(self, *args, **kwds):
        raise TypeError(f"Cannot instantiate {self!r}")

    def __or__(self, other):
        return typing.Union[self, other]

    def __ror__(self, other):
        return typing.Union[other, self]

    def __instancecheck__(self, obj):
        raise TypeError(f"{self} cannot be used with isinstance()")

    def __subclasscheck__(self, cls):
        raise TypeError(f"{self} cannot be used with issubclass()")

    @typing._tp_cache
    def __getitem__(self, parameters):
        return self._getitem(self, parameters)


if hasattr(typing, "LiteralString"):  # 3.11+
    LiteralString = typing.LiteralString
else:
    @_SpecialForm
    def LiteralString(self, params):
        """Represents an arbitrary literal string.

        Example::

          from typing_extensions import LiteralString

          def query(sql: LiteralString) -> ...:
              ...

          query("SELECT * FROM table")  # ok
          query(f"SELECT * FROM {input()}")  # not ok

        See PEP 675 for details.

        """
        raise TypeError(f"{self} is not subscriptable")


if hasattr(typing, "Self"):  # 3.11+
    Self = typing.Self
else:
    @_SpecialForm
    def Self(self, params):
        """Used to spell the type of "self" in classes.

        Example::

          from typing import Self

          class ReturnsSelf:
              def parse(self, data: bytes) -> Self:
                  ...
                  return self

        """

        raise TypeError(f"{self} is not subscriptable")


if hasattr(typing, "Never"):  # 3.11+
    Never = typing.Never
else:
    @_SpecialForm
    def Never(self, params):
        """The bottom type, a type that has no members.

        This can be used to define a function that should never be
        called, or a function that never returns::

            from typing_extensions import Never

            def never_call_me(arg: Never) -> None:
                pass

            def int_or_str(arg: int | str) -> None:
                never_call_me(arg)  # type checker error
                match arg:
                    case int():
                        print("It's an int")
                    case str():
                        print("It's a str")
                    case _:
                        never_call_me(arg)  # ok, arg is of type Never

        """

        raise TypeError(f"{self} is not subscriptable")


if hasattr(typing, 'Required'):  # 3.11+
    Required = typing.Required
    NotRequired = typing.NotRequired
elif sys.version_info[:2] >= (3, 9):  # 3.9-3.10
    @_ExtensionsSpecialForm
    def Required(self, parameters):
        """A special typing construct to mark a key of a total=False TypedDict
        as required. For example:

            class Movie(TypedDict, total=False):
                title: Required[str]
                year: int

            m = Movie(
                title='The Matrix',  # typechecker error if key is omitted
                year=1999,
            )

        There is no runtime checking that a required key is actually provided
        when instantiating a related TypedDict.
        """
        item = typing._type_check(parameters, f'{self._name} accepts only a single type.')
        return typing._GenericAlias(self, (item,))

    @_ExtensionsSpecialForm
    def NotRequired(self, parameters):
        """A special typing construct to mark a key of a TypedDict as
        potentially missing. For example:

            class Movie(TypedDict):
                title: str
                year: NotRequired[int]

            m = Movie(
                title='The Matrix',  # typechecker error if key is omitted
                year=1999,
            )
        """
        item = typing._type_check(parameters, f'{self._name} accepts only a single type.')
        return typing._GenericAlias(self, (item,))

else:  # 3.8
    class _RequiredForm(_ExtensionsSpecialForm, _root=True):
        def __getitem__(self, parameters):
            item = typing._type_check(parameters,
                                      f'{self._name} accepts only a single type.')
            return typing._GenericAlias(self, (item,))

    Required = _RequiredForm(
        'Required',
        doc="""A special typing construct to mark a key of a total=False TypedDict
        as required. For example:

            class Movie(TypedDict, total=False):
                title: Required[str]
                year: int

            m = Movie(
                title='The Matrix',  # typechecker error if key is omitted
                year=1999,
            )

        There is no runtime checking that a required key is actually provided
        when instantiating a related TypedDict.
        """)
    NotRequired = _RequiredForm(
        'NotRequired',
        doc="""A special typing construct to mark a key of a TypedDict as
        potentially missing. For example:

            class Movie(TypedDict):
                title: str
                year: NotRequired[int]

            m = Movie(
                title='The Matrix',  # typechecker error if key is omitted
                year=1999,
            )
        """)


if hasattr(typing, 'ReadOnly'):
    ReadOnly = typing.ReadOnly
elif sys.version_info[:2] >= (3, 9):  # 3.9-3.12
    @_ExtensionsSpecialForm
    def ReadOnly(self, parameters):
        """A special typing construct to mark an item of a TypedDict as read-only.

        For example:

            class Movie(TypedDict):
                title: ReadOnly[str]
                year: int

            def mutate_movie(m: Movie) -> None:
                m["year"] = 1992  # allowed
                m["title"] = "The Matrix"  # typechecker error

        There is no runtime checking for this property.
        """
        item = typing._type_check(parameters, f'{self._name} accepts only a single type.')
        return typing._GenericAlias(self, (item,))

else:  # 3.8
    class _ReadOnlyForm(_ExtensionsSpecialForm, _root=True):
        def __getitem__(self, parameters):
            item = typing._type_check(parameters,
                                      f'{self._name} accepts only a single type.')
            return typing._GenericAlias(self, (item,))

    ReadOnly = _ReadOnlyForm(
        'ReadOnly',
        doc="""A special typing construct to mark a key of a TypedDict as read-only.

        For example:

            class Movie(TypedDict):
                title: ReadOnly[str]
                year: int

            def mutate_movie(m: Movie) -> None:
                m["year"] = 1992  # allowed
                m["title"] = "The Matrix"  # typechecker error

        There is no runtime checking for this propery.
        """)


_UNPACK_DOC = """\
Type unpack operator.

The type unpack operator takes the child types from some container type,
such as `tuple[int, str]` or a `TypeVarTuple`, and 'pulls them out'. For
example:

  # For some generic class `Foo`:
  Foo[Unpack[tuple[int, str]]]  # Equivalent to Foo[int, str]

  Ts = TypeVarTuple('Ts')
  # Specifies that `Bar` is generic in an arbitrary number of types.
  # (Think of `Ts` as a tuple of an arbitrary number of individual
  #  `TypeVar`s, which the `Unpack` is 'pulling out' directly into the
  #  `Generic[]`.)
  class Bar(Generic[Unpack[Ts]]): ...
  Bar[int]  # Valid
  Bar[int, str]  # Also valid

From Python 3.11, this can also be done using the `*` operator:

    Foo[*tuple[int, str]]
    class Bar(Generic[*Ts]): ...

The operator can also be used along with a `TypedDict` to annotate
`**kwargs` in a function signature. For instance:

  class Movie(TypedDict):
    name: str
    year: int

  # This function expects two keyword arguments - *name* of type `str` and
  # *year* of type `int`.
  def foo(**kwargs: Unpack[Movie]): ...

Note that there is only some runtime checking of this operator. Not
everything the runtime allows may be accepted by static type checkers.

For more information, see PEP 646 and PEP 692.
"""


if sys.version_info >= (3, 12):  # PEP 692 changed the repr of Unpack[]
    Unpack = typing.Unpack

    def _is_unpack(obj):
        return get_origin(obj) is Unpack

elif sys.version_info[:2] >= (3, 9):  # 3.9+
    class _UnpackSpecialForm(_ExtensionsSpecialForm, _root=True):
        def __init__(self, getitem):
            super().__init__(getitem)
            self.__doc__ = _UNPACK_DOC

    class _UnpackAlias(typing._GenericAlias, _root=True):
        if sys.version_info < (3, 11):
            # needed for compatibility with Generic[Unpack[Ts]]
            __class__ = typing.TypeVar

        @property
        def __typing_unpacked_tuple_args__(self):
            assert self.__origin__ is Unpack
            assert len(self.__args__) == 1
            arg, = self.__args__
            if isinstance(arg, (typing._GenericAlias, _types.GenericAlias)):
                if arg.__origin__ is not tuple:
                    raise TypeError("Unpack[...] must be used with a tuple type")
                return arg.__args__
            return None

        @property
        def __typing_is_unpacked_typevartuple__(self):
            assert self.__origin__ is Unpack
            assert len(self.__args__) == 1
            return isinstance(self.__args__[0], TypeVarTuple)

        def __getitem__(self, args):
            if self.__typing_is_unpacked_typevartuple__:
                return args
            return super().__getitem__(args)

    @_UnpackSpecialForm
    def Unpack(self, parameters):
        item = typing._type_check(parameters, f'{self._name} accepts only a single type.')
        return _UnpackAlias(self, (item,))

    def _is_unpack(obj):
        return isinstance(obj, _UnpackAlias)

else:  # 3.8
    class _UnpackAlias(typing._GenericAlias, _root=True):
        __class__ = typing.TypeVar

        @property
        def __typing_unpacked_tuple_args__(self):
            assert self.__origin__ is Unpack
            assert len(self.__args__) == 1
            arg, = self.__args__
            if isinstance(arg, typing._GenericAlias):
                if arg.__origin__ is not tuple:
                    raise TypeError("Unpack[...] must be used with a tuple type")
                return arg.__args__
            return None

        @property
        def __typing_is_unpacked_typevartuple__(self):
            assert self.__origin__ is Unpack
            assert len(self.__args__) == 1
            return isinstance(self.__args__[0], TypeVarTuple)

        def __getitem__(self, args):
            if self.__typing_is_unpacked_typevartuple__:
                return args
            return super().__getitem__(args)

    class _UnpackForm(_ExtensionsSpecialForm, _root=True):
        def __getitem__(self, parameters):
            item = typing._type_check(parameters,
                                      f'{self._name} accepts only a single type.')
            return _UnpackAlias(self, (item,))

    Unpack = _UnpackForm('Unpack', doc=_UNPACK_DOC)

    def _is_unpack(obj):
        return isinstance(obj, _UnpackAlias)


def _unpack_args(*args):
    newargs = []
    for arg in args:
        subargs = getattr(arg, '__typing_unpacked_tuple_args__', None)
        if subargs is not None and (not (subargs and subargs[-1] is ...)):
            newargs.extend(subargs)
        else:
            newargs.append(arg)
    return newargs


if _PEP_696_IMPLEMENTED:
    from typing import TypeVarTuple

elif hasattr(typing, "TypeVarTuple"):  # 3.11+

    # Add default parameter - PEP 696
    class TypeVarTuple(metaclass=_TypeVarLikeMeta):
        """Type variable tuple."""

        _backported_typevarlike = typing.TypeVarTuple

        def __new__(cls, name, *, default=NoDefault):
            tvt = typing.TypeVarTuple(name)
            _set_default(tvt, default)
            _set_module(tvt)

            def _typevartuple_prepare_subst(alias, args):
                params = alias.__parameters__
                typevartuple_index = params.index(tvt)
                for param in params[typevartuple_index + 1:]:
                    if isinstance(param, TypeVarTuple):
                        raise TypeError(
                            f"More than one TypeVarTuple parameter in {alias}"
                        )

                alen = len(args)
                plen = len(params)
                left = typevartuple_index
                right = plen - typevartuple_index - 1
                var_tuple_index = None
                fillarg = None
                for k, arg in enumerate(args):
                    if not isinstance(arg, type):
                        subargs = getattr(arg, '__typing_unpacked_tuple_args__', None)
                        if subargs and len(subargs) == 2 and subargs[-1] is ...:
                            if var_tuple_index is not None:
                                raise TypeError(
                                    "More than one unpacked "
                                    "arbitrary-length tuple argument"
                                )
                            var_tuple_index = k
                            fillarg = subargs[0]
                if var_tuple_index is not None:
                    left = min(left, var_tuple_index)
                    right = min(right, alen - var_tuple_index - 1)
                elif left + right > alen:
                    raise TypeError(f"Too few arguments for {alias};"
                                    f" actual {alen}, expected at least {plen - 1}")
                if left == alen - right and tvt.has_default():
                    replacement = _unpack_args(tvt.__default__)
                else:
                    replacement = args[left: alen - right]

                return (
                    *args[:left],
                    *([fillarg] * (typevartuple_index - left)),
                    replacement,
                    *([fillarg] * (plen - right - left - typevartuple_index - 1)),
                    *args[alen - right:],
                )

            tvt.__typing_prepare_subst__ = _typevartuple_prepare_subst
            return tvt

        def __init_subclass__(self, *args, **kwds):
            raise TypeError("Cannot subclass special typing classes")

else:  # <=3.10
    class TypeVarTuple(_DefaultMixin):
        """Type variable tuple.

        Usage::

            Ts = TypeVarTuple('Ts')

        In the same way that a normal type variable is a stand-in for a single
        type such as ``int``, a type variable *tuple* is a stand-in for a *tuple*
        type such as ``Tuple[int, str]``.

        Type variable tuples can be used in ``Generic`` declarations.
        Consider the following example::

            class Array(Generic[*Ts]): ...

        The ``Ts`` type variable tuple here behaves like ``tuple[T1, T2]``,
        where ``T1`` and ``T2`` are type variables. To use these type variables
        as type parameters of ``Array``, we must *unpack* the type variable tuple using
        the star operator: ``*Ts``. The signature of ``Array`` then behaves
        as if we had simply written ``class Array(Generic[T1, T2]): ...``.
        In contrast to ``Generic[T1, T2]``, however, ``Generic[*Shape]`` allows
        us to parameterise the class with an *arbitrary* number of type parameters.

        Type variable tuples can be used anywhere a normal ``TypeVar`` can.
        This includes class definitions, as shown above, as well as function
        signatures and variable annotations::

            class Array(Generic[*Ts]):

                def __init__(self, shape: Tuple[*Ts]):
                    self._shape: Tuple[*Ts] = shape

                def get_shape(self) -> Tuple[*Ts]:
                    return self._shape

            shape = (Height(480), Width(640))
            x: Array[Height, Width] = Array(shape)
            y = abs(x)  # Inferred type is Array[Height, Width]
            z = x + x   #        ...    is Array[Height, Width]
            x.get_shape()  #     ...    is tuple[Height, Width]

        """

        # Trick Generic __parameters__.
        __class__ = typing.TypeVar

        def __iter__(self):
            yield self.__unpacked__

        def __init__(self, name, *, default=NoDefault):
            self.__name__ = name
            _DefaultMixin.__init__(self, default)

            # for pickling:
            def_mod = _caller()
            if def_mod != 'typing_extensions':
                self.__module__ = def_mod

            self.__unpacked__ = Unpack[self]

        def __repr__(self):
            return self.__name__

        def __hash__(self):
            return object.__hash__(self)

        def __eq__(self, other):
            return self is other

        def __reduce__(self):
            return self.__name__

        def __init_subclass__(self, *args, **kwds):
            if '_root' not in kwds:
                raise TypeError("Cannot subclass special typing classes")


if hasattr(typing, "reveal_type"):  # 3.11+
    reveal_type = typing.reveal_type
else:  # <=3.10
    def reveal_type(obj: T, /) -> T:
        """Reveal the inferred type of a variable.

        When a static type checker encounters a call to ``reveal_type()``,
        it will emit the inferred type of the argument::

            x: int = 1
            reveal_type(x)

        Running a static type checker (e.g., ``mypy``) on this example
        will produce output similar to 'Revealed type is "builtins.int"'.

        At runtime, the function prints the runtime type of the
        argument and returns it unchanged.

        """
        print(f"Runtime type is {type(obj).__name__!r}", file=sys.stderr)
        return obj


if hasattr(typing, "_ASSERT_NEVER_REPR_MAX_LENGTH"):  # 3.11+
    _ASSERT_NEVER_REPR_MAX_LENGTH = typing._ASSERT_NEVER_REPR_MAX_LENGTH
else:  # <=3.10
    _ASSERT_NEVER_REPR_MAX_LENGTH = 100


if hasattr(typing, "assert_never"):  # 3.11+
    assert_never = typing.assert_never
else:  # <=3.10
    def assert_never(arg: Never, /) -> Never:
        """Assert to the type checker that a line of code is unreachable.

        Example::

            def int_or_str(arg: int | str) -> None:
                match arg:
                    case int():
                        print("It's an int")
                    case str():
                        print("It's a str")
                    case _:
                        assert_never(arg)

        If a type checker finds that a call to assert_never() is
        reachable, it will emit an error.

        At runtime, this throws an exception when called.

        """
        value = repr(arg)
        if len(value) > _ASSERT_NEVER_REPR_MAX_LENGTH:
            value = value[:_ASSERT_NEVER_REPR_MAX_LENGTH] + '...'
        raise AssertionError(f"Expected code to be unreachable, but got: {value}")


if sys.version_info >= (3, 12):  # 3.12+
    # dataclass_transform exists in 3.11 but lacks the frozen_default parameter
    dataclass_transform = typing.dataclass_transform
else:  # <=3.11
    def dataclass_transform(
        *,
        eq_default: bool = True,
        order_default: bool = False,
        kw_only_default: bool = False,
        frozen_default: bool = False,
        field_specifiers: typing.Tuple[
            typing.Union[typing.Type[typing.Any], typing.Callable[..., typing.Any]],
            ...
        ] = (),
        **kwargs: typing.Any,
    ) -> typing.Callable[[T], T]:
        """Decorator that marks a function, class, or metaclass as providing
        dataclass-like behavior.

        Example:

            from typing_extensions import dataclass_transform

            _T = TypeVar("_T")

            # Used on a decorator function
            @dataclass_transform()
            def create_model(cls: type[_T]) -> type[_T]:
                ...
                return cls

            @create_model
            class CustomerModel:
                id: int
                name: str

            # Used on a base class
            @dataclass_transform()
            class ModelBase: ...

            class CustomerModel(ModelBase):
                id: int
                name: str

            # Used on a metaclass
            @dataclass_transform()
            class ModelMeta(type): ...

            class ModelBase(metaclass=ModelMeta): ...

            class CustomerModel(ModelBase):
                id: int
                name: str

        Each of the ``CustomerModel`` classes defined in this example will now
        behave similarly to a dataclass created with the ``@dataclasses.dataclass``
        decorator. For example, the type checker will synthesize an ``__init__``
        method.

        The arguments to this decorator can be used to customize this behavior:
        - ``eq_default`` indicates whether the ``eq`` parameter is assumed to be
          True or False if it is omitted by the caller.
        - ``order_default`` indicates whether the ``order`` parameter is
          assumed to be True or False if it is omitted by the caller.
        - ``kw_only_default`` indicates whether the ``kw_only`` parameter is
          assumed to be True or False if it is omitted by the caller.
        - ``frozen_default`` indicates whether the ``frozen`` parameter is
          assumed to be True or False if it is omitted by the caller.
        - ``field_specifiers`` specifies a static list of supported classes
          or functions that describe fields, similar to ``dataclasses.field()``.

        At runtime, this decorator records its arguments in the
        ``__dataclass_transform__`` attribute on the decorated object.

        See PEP 681 for details.

        """
        def decorator(cls_or_fn):
            cls_or_fn.__dataclass_transform__ = {
                "eq_default": eq_default,
                "order_default": order_default,
                "kw_only_default": kw_only_default,
                "frozen_default": frozen_default,
                "field_specifiers": field_specifiers,
                "kwargs": kwargs,
            }
            return cls_or_fn
        return decorator


if hasattr(typing, "override"):  # 3.12+
    override = typing.override
else:  # <=3.11
    _F = typing.TypeVar("_F", bound=typing.Callable[..., typing.Any])

    def override(arg: _F, /) -> _F:
        """Indicate that a method is intended to override a method in a base class.

        Usage:

            class Base:
                def method(self) -> None:
                    pass

            class Child(Base):
                @override
                def method(self) -> None:
                    super().method()

        When this decorator is applied to a method, the type checker will
        validate that it overrides a method with the same name on a base class.
        This helps prevent bugs that may occur when a base class is changed
        without an equivalent change to a child class.

        There is no runtime checking of these properties. The decorator
        sets the ``__override__`` attribute to ``True`` on the decorated object
        to allow runtime introspection.

        See PEP 698 for details.

        """
        try:
            arg.__override__ = True
        except (AttributeError, TypeError):
            # Skip the attribute silently if it is not writable.
            # AttributeError happens if the object has __slots__ or a
            # read-only property, TypeError if it's a builtin class.
            pass
        return arg


# Python 3.13.3+ contains a fix for the wrapped __new__
if sys.version_info >= (3, 13, 3):
    deprecated = warnings.deprecated
else:
    _T = typing.TypeVar("_T")

    class deprecated:
        """Indicate that a class, function or overload is deprecated.

        When this decorator is applied to an object, the type checker
        will generate a diagnostic on usage of the deprecated object.

        Usage:

            @deprecated("Use B instead")
            class A:
                pass

            @deprecated("Use g instead")
            def f():
                pass

            @overload
            @deprecated("int support is deprecated")
            def g(x: int) -> int: ...
            @overload
            def g(x: str) -> int: ...

        The warning specified by *category* will be emitted at runtime
        on use of deprecated objects. For functions, that happens on calls;
        for classes, on instantiation and on creation of subclasses.
        If the *category* is ``None``, no warning is emitted at runtime.
        The *stacklevel* determines where the
        warning is emitted. If it is ``1`` (the default), the warning
        is emitted at the direct caller of the deprecated object; if it
        is higher, it is emitted further up the stack.
        Static type checker behavior is not affected by the *category*
        and *stacklevel* arguments.

        The deprecation message passed to the decorator is saved in the
        ``__deprecated__`` attribute on the decorated object.
        If applied to an overload, the decorator
        must be after the ``@overload`` decorator for the attribute to
        exist on the overload as returned by ``get_overloads()``.

        See PEP 702 for details.

        """
        def __init__(
            self,
            message: str,
            /,
            *,
            category: typing.Optional[typing.Type[Warning]] = DeprecationWarning,
            stacklevel: int = 1,
        ) -> None:
            if not isinstance(message, str):
                raise TypeError(
                    "Expected an object of type str for 'message', not "
                    f"{type(message).__name__!r}"
                )
            self.message = message
            self.category = category
            self.stacklevel = stacklevel

        def __call__(self, arg: _T, /) -> _T:
            # Make sure the inner functions created below don't
            # retain a reference to self.
            msg = self.message
            category = self.category
            stacklevel = self.stacklevel
            if category is None:
                arg.__deprecated__ = msg
                return arg
            elif isinstance(arg, type):
                import functools
                from types import MethodType

                original_new = arg.__new__

                @functools.wraps(original_new)
                def __new__(cls, /, *args, **kwargs):
                    if cls is arg:
                        warnings.warn(msg, category=category, stacklevel=stacklevel + 1)
                    if original_new is not object.__new__:
                        return original_new(cls, *args, **kwargs)
                    # Mirrors a similar check in object.__new__.
                    elif cls.__init__ is object.__init__ and (args or kwargs):
                        raise TypeError(f"{cls.__name__}() takes no arguments")
                    else:
                        return original_new(cls)

                arg.__new__ = staticmethod(__new__)

                original_init_subclass = arg.__init_subclass__
                # We need slightly different behavior if __init_subclass__
                # is a bound method (likely if it was implemented in Python)
                if isinstance(original_init_subclass, MethodType):
                    original_init_subclass = original_init_subclass.__func__

                    @functools.wraps(original_init_subclass)
                    def __init_subclass__(*args, **kwargs):
                        warnings.warn(msg, category=category, stacklevel=stacklevel + 1)
                        return original_init_subclass(*args, **kwargs)

                    arg.__init_subclass__ = classmethod(__init_subclass__)
                # Or otherwise, which likely means it's a builtin such as
                # object's implementation of __init_subclass__.
                else:
                    @functools.wraps(original_init_subclass)
                    def __init_subclass__(*args, **kwargs):
                        warnings.warn(msg, category=category, stacklevel=stacklevel + 1)
                        return original_init_subclass(*args, **kwargs)

                    arg.__init_subclass__ = __init_subclass__

                arg.__deprecated__ = __new__.__deprecated__ = msg
                __init_subclass__.__deprecated__ = msg
                return arg
            elif callable(arg):
                import asyncio.coroutines
                import functools
                import inspect

                @functools.wraps(arg)
                def wrapper(*args, **kwargs):
                    warnings.warn(msg, category=category, stacklevel=stacklevel + 1)
                    return arg(*args, **kwargs)

                if asyncio.coroutines.iscoroutinefunction(arg):
                    if sys.version_info >= (3, 12):
                        wrapper = inspect.markcoroutinefunction(wrapper)
                    else:
                        wrapper._is_coroutine = asyncio.coroutines._is_coroutine

                arg.__deprecated__ = wrapper.__deprecated__ = msg
                return wrapper
            else:
                raise TypeError(
                    "@deprecated decorator with non-None category must be applied to "
                    f"a class or callable, not {arg!r}"
                )

if sys.version_info < (3, 10):
    def _is_param_expr(arg):
        return arg is ... or isinstance(
            arg, (tuple, list, ParamSpec, _ConcatenateGenericAlias)
        )
else:
    def _is_param_expr(arg):
        return arg is ... or isinstance(
            arg,
            (
                tuple,
                list,
                ParamSpec,
                _ConcatenateGenericAlias,
                typing._ConcatenateGenericAlias,
            ),
        )


# We have to do some monkey patching to deal with the dual nature of
# Unpack/TypeVarTuple:
# - We want Unpack to be a kind of TypeVar so it gets accepted in
#   Generic[Unpack[Ts]]
# - We want it to *not* be treated as a TypeVar for the purposes of
#   counting generic parameters, so that when we subscript a generic,
#   the runtime doesn't try to substitute the Unpack with the subscripted type.
if not hasattr(typing, "TypeVarTuple"):
    def _check_generic(cls, parameters, elen=_marker):
        """Check correct count for parameters of a generic cls (internal helper).

        This gives a nice error message in case of count mismatch.
        """
        # If substituting a single ParamSpec with multiple arguments
        # we do not check the count
        if (inspect.isclass(cls) and issubclass(cls, typing.Generic)
            and len(cls.__parameters__) == 1
            and isinstance(cls.__parameters__[0], ParamSpec)
            and parameters
            and not _is_param_expr(parameters[0])
        ):
            # Generic modifies parameters variable, but here we cannot do this
            return

        if not elen:
            raise TypeError(f"{cls} is not a generic class")
        if elen is _marker:
            if not hasattr(cls, "__parameters__") or not cls.__parameters__:
                raise TypeError(f"{cls} is not a generic class")
            elen = len(cls.__parameters__)
        alen = len(parameters)
        if alen != elen:
            expect_val = elen
            if hasattr(cls, "__parameters__"):
                parameters = [p for p in cls.__parameters__ if not _is_unpack(p)]
                num_tv_tuples = sum(isinstance(p, TypeVarTuple) for p in parameters)
                if (num_tv_tuples > 0) and (alen >= elen - num_tv_tuples):
                    return

                # deal with TypeVarLike defaults
                # required TypeVarLikes cannot appear after a defaulted one.
                if alen < elen:
                    # since we validate TypeVarLike default in _collect_type_vars
                    # or _collect_parameters we can safely check parameters[alen]
                    if (
                        getattr(parameters[alen], '__default__', NoDefault)
                        is not NoDefault
                    ):
                        return

                    num_default_tv = sum(getattr(p, '__default__', NoDefault)
                                         is not NoDefault for p in parameters)

                    elen -= num_default_tv

                    expect_val = f"at least {elen}"

            things = "arguments" if sys.version_info >= (3, 10) else "parameters"
            raise TypeError(f"Too {'many' if alen > elen else 'few'} {things}"
                            f" for {cls}; actual {alen}, expected {expect_val}")
else:
    # Python 3.11+

    def _check_generic(cls, parameters, elen):
        """Check correct count for parameters of a generic cls (internal helper).

        This gives a nice error message in case of count mismatch.
        """
        if not elen:
            raise TypeError(f"{cls} is not a generic class")
        alen = len(parameters)
        if alen != elen:
            expect_val = elen
            if hasattr(cls, "__parameters__"):
                parameters = [p for p in cls.__parameters__ if not _is_unpack(p)]

                # deal with TypeVarLike defaults
                # required TypeVarLikes cannot appear after a defaulted one.
                if alen < elen:
                    # since we validate TypeVarLike default in _collect_type_vars
                    # or _collect_parameters we can safely check parameters[alen]
                    if (
                        getattr(parameters[alen], '__default__', NoDefault)
                        is not NoDefault
                    ):
                        return

                    num_default_tv = sum(getattr(p, '__default__', NoDefault)
                                         is not NoDefault for p in parameters)

                    elen -= num_default_tv

                    expect_val = f"at least {elen}"

            raise TypeError(f"Too {'many' if alen > elen else 'few'} arguments"
                            f" for {cls}; actual {alen}, expected {expect_val}")

if not _PEP_696_IMPLEMENTED:
    typing._check_generic = _check_generic


def _has_generic_or_protocol_as_origin() -> bool:
    try:
        frame = sys._getframe(2)
    # - Catch AttributeError: not all Python implementations have sys._getframe()
    # - Catch ValueError: maybe we're called from an unexpected module
    #   and the call stack isn't deep enough
    except (AttributeError, ValueError):
        return False  # err on the side of leniency
    else:
        # If we somehow get invoked from outside typing.py,
        # also err on the side of leniency
        if frame.f_globals.get("__name__") != "typing":
            return False
        origin = frame.f_locals.get("origin")
        # Cannot use "in" because origin may be an object with a buggy __eq__ that
        # throws an error.
        return origin is typing.Generic or origin is Protocol or origin is typing.Protocol


_TYPEVARTUPLE_TYPES = {TypeVarTuple, getattr(typing, "TypeVarTuple", None)}


def _is_unpacked_typevartuple(x) -> bool:
    if get_origin(x) is not Unpack:
        return False
    args = get_args(x)
    return (
        bool(args)
        and len(args) == 1
        and type(args[0]) in _TYPEVARTUPLE_TYPES
    )


# Python 3.11+ _collect_type_vars was renamed to _collect_parameters
if hasattr(typing, '_collect_type_vars'):
    def _collect_type_vars(types, typevar_types=None):
        """Collect all type variable contained in types in order of
        first appearance (lexicographic order). For example::

            _collect_type_vars((T, List[S, T])) == (T, S)
        """
        if typevar_types is None:
            typevar_types = typing.TypeVar
        tvars = []

        # A required TypeVarLike cannot appear after a TypeVarLike with a default
        # if it was a direct call to `Generic[]` or `Protocol[]`
        enforce_default_ordering = _has_generic_or_protocol_as_origin()
        default_encountered = False

        # Also, a TypeVarLike with a default cannot appear after a TypeVarTuple
        type_var_tuple_encountered = False

        for t in types:
            if _is_unpacked_typevartuple(t):
                type_var_tuple_encountered = True
            elif (
                isinstance(t, typevar_types) and not isinstance(t, _UnpackAlias)
                and t not in tvars
            ):
                if enforce_default_ordering:
                    has_default = getattr(t, '__default__', NoDefault) is not NoDefault
                    if has_default:
                        if type_var_tuple_encountered:
                            raise TypeError('Type parameter with a default'
                                            ' follows TypeVarTuple')
                        default_encountered = True
                    elif default_encountered:
                        raise TypeError(f'Type parameter {t!r} without a default'
                                        ' follows type parameter with a default')

                tvars.append(t)
            if _should_collect_from_parameters(t):
                tvars.extend([t for t in t.__parameters__ if t not in tvars])
            elif isinstance(t, tuple):
                # Collect nested type_vars
                # tuple wrapped by  _prepare_paramspec_params(cls, params)
                for x in t:
                    for collected in _collect_type_vars([x]):
                        if collected not in tvars:
                            tvars.append(collected)
        return tuple(tvars)

    typing._collect_type_vars = _collect_type_vars
else:
    def _collect_parameters(args):
        """Collect all type variables and parameter specifications in args
        in order of first appearance (lexicographic order).

        For example::

            assert _collect_parameters((T, Callable[P, T])) == (T, P)
        """
        parameters = []

        # A required TypeVarLike cannot appear after a TypeVarLike with default
        # if it was a direct call to `Generic[]` or `Protocol[]`
        enforce_default_ordering = _has_generic_or_protocol_as_origin()
        default_encountered = False

        # Also, a TypeVarLike with a default cannot appear after a TypeVarTuple
        type_var_tuple_encountered = False

        for t in args:
            if isinstance(t, type):
                # We don't want __parameters__ descriptor of a bare Python class.
                pass
            elif isinstance(t, tuple):
                # `t` might be a tuple, when `ParamSpec` is substituted with
                # `[T, int]`, or `[int, *Ts]`, etc.
                for x in t:
                    for collected in _collect_parameters([x]):
                        if collected not in parameters:
                            parameters.append(collected)
            elif hasattr(t, '__typing_subst__'):
                if t not in parameters:
                    if enforce_default_ordering:
                        has_default = (
                            getattr(t, '__default__', NoDefault) is not NoDefault
                        )

                        if type_var_tuple_encountered and has_default:
                            raise TypeError('Type parameter with a default'
                                            ' follows TypeVarTuple')

                        if has_default:
                            default_encountered = True
                        elif default_encountered:
                            raise TypeError(f'Type parameter {t!r} without a default'
                                            ' follows type parameter with a default')

                    parameters.append(t)
            else:
                if _is_unpacked_typevartuple(t):
                    type_var_tuple_encountered = True
                for x in getattr(t, '__parameters__', ()):
                    if x not in parameters:
                        parameters.append(x)

        return tuple(parameters)

    if not _PEP_696_IMPLEMENTED:
        typing._collect_parameters = _collect_parameters

# Backport typing.NamedTuple as it exists in Python 3.13.
# In 3.11, the ability to define generic `NamedTuple`s was supported.
# This was explicitly disallowed in 3.9-3.10, and only half-worked in <=3.8.
# On 3.12, we added __orig_bases__ to call-based NamedTuples
# On 3.13, we deprecated kwargs-based NamedTuples
if sys.version_info >= (3, 13):
    NamedTuple = typing.NamedTuple
else:
    def _make_nmtuple(name, types, module, defaults=()):
        fields = [n for n, t in types]
        annotations = {n: typing._type_check(t, f"field {n} annotation must be a type")
                       for n, t in types}
        nm_tpl = collections.namedtuple(name, fields,
                                        defaults=defaults, module=module)
        nm_tpl.__annotations__ = nm_tpl.__new__.__annotations__ = annotations
        # The `_field_types` attribute was removed in 3.9;
        # in earlier versions, it is the same as the `__annotations__` attribute
        if sys.version_info < (3, 9):
            nm_tpl._field_types = annotations
        return nm_tpl

    _prohibited_namedtuple_fields = typing._prohibited
    _special_namedtuple_fields = frozenset({'__module__', '__name__', '__annotations__'})

    class _NamedTupleMeta(type):
        def __new__(cls, typename, bases, ns):
            assert _NamedTuple in bases
            for base in bases:
                if base is not _NamedTuple and base is not typing.Generic:
                    raise TypeError(
                        'can only inherit from a NamedTuple type and Generic')
            bases = tuple(tuple if base is _NamedTuple else base for base in bases)
            if "__annotations__" in ns:
                types = ns["__annotations__"]
            elif "__annotate__" in ns:
                # TODO: Use inspect.VALUE here, and make the annotations lazily evaluated
                types = ns["__annotate__"](1)
            else:
                types = {}
            default_names = []
            for field_name in types:
                if field_name in ns:
                    default_names.append(field_name)
                elif default_names:
                    raise TypeError(f"Non-default namedtuple field {field_name} "
                                    f"cannot follow default field"
                                    f"{'s' if len(default_names) > 1 else ''} "
                                    f"{', '.join(default_names)}")
            nm_tpl = _make_nmtuple(
                typename, types.items(),
                defaults=[ns[n] for n in default_names],
                module=ns['__module__']
            )
            nm_tpl.__bases__ = bases
            if typing.Generic in bases:
                if hasattr(typing, '_generic_class_getitem'):  # 3.12+
                    nm_tpl.__class_getitem__ = classmethod(typing._generic_class_getitem)
                else:
                    class_getitem = typing.Generic.__class_getitem__.__func__
                    nm_tpl.__class_getitem__ = classmethod(class_getitem)
            # update from user namespace without overriding special namedtuple attributes
            for key, val in ns.items():
                if key in _prohibited_namedtuple_fields:
                    raise AttributeError("Cannot overwrite NamedTuple attribute " + key)
                elif key not in _special_namedtuple_fields:
                    if key not in nm_tpl._fields:
                        setattr(nm_tpl, key, ns[key])
                    try:
                        set_name = type(val).__set_name__
                    except AttributeError:
                        pass
                    else:
                        try:
                            set_name(val, nm_tpl, key)
                        except BaseException as e:
                            msg = (
                                f"Error calling __set_name__ on {type(val).__name__!r} "
                                f"instance {key!r} in {typename!r}"
                            )
                            # BaseException.add_note() existed on py311,
                            # but the __set_name__ machinery didn't start
                            # using add_note() until py312.
                            # Making sure exceptions are raised in the same way
                            # as in "normal" classes seems most important here.
                            if sys.version_info >= (3, 12):
                                e.add_note(msg)
                                raise
                            else:
                                raise RuntimeError(msg) from e

            if typing.Generic in bases:
                nm_tpl.__init_subclass__()
            return nm_tpl

    _NamedTuple = type.__new__(_NamedTupleMeta, 'NamedTuple', (), {})

    def _namedtuple_mro_entries(bases):
        assert NamedTuple in bases
        return (_NamedTuple,)

    @_ensure_subclassable(_namedtuple_mro_entries)
    def NamedTuple(typename, fields=_marker, /, **kwargs):
        """Typed version of namedtuple.

        Usage::

            class Employee(NamedTuple):
                name: str
                id: int

        This is equivalent to::

            Employee = collections.namedtuple('Employee', ['name', 'id'])

        The resulting class has an extra __annotations__ attribute, giving a
        dict that maps field names to types.  (The field names are also in
        the _fields attribute, which is part of the namedtuple API.)
        An alternative equivalent functional syntax is also accepted::

            Employee = NamedTuple('Employee', [('name', str), ('id', int)])
        """
        if fields is _marker:
            if kwargs:
                deprecated_thing = "Creating NamedTuple classes using keyword arguments"
                deprecation_msg = (
                    "{name} is deprecated and will be disallowed in Python {remove}. "
                    "Use the class-based or functional syntax instead."
                )
            else:
                deprecated_thing = "Failing to pass a value for the 'fields' parameter"
                example = f"`{typename} = NamedTuple({typename!r}, [])`"
                deprecation_msg = (
                    "{name} is deprecated and will be disallowed in Python {remove}. "
                    "To create a NamedTuple class with 0 fields "
                    "using the functional syntax, "
                    "pass an empty list, e.g. "
                ) + example + "."
        elif fields is None:
            if kwargs:
                raise TypeError(
                    "Cannot pass `None` as the 'fields' parameter "
                    "and also specify fields using keyword arguments"
                )
            else:
                deprecated_thing = "Passing `None` as the 'fields' parameter"
                example = f"`{typename} = NamedTuple({typename!r}, [])`"
                deprecation_msg = (
                    "{name} is deprecated and will be disallowed in Python {remove}. "
                    "To create a NamedTuple class with 0 fields "
                    "using the functional syntax, "
                    "pass an empty list, e.g. "
                ) + example + "."
        elif kwargs:
            raise TypeError("Either list of fields or keywords"
                            " can be provided to NamedTuple, not both")
        if fields is _marker or fields is None:
            warnings.warn(
                deprecation_msg.format(name=deprecated_thing, remove="3.15"),
                DeprecationWarning,
                stacklevel=2,
            )
            fields = kwargs.items()
        nt = _make_nmtuple(typename, fields, module=_caller())
        nt.__orig_bases__ = (NamedTuple,)
        return nt


if hasattr(collections.abc, "Buffer"):
    Buffer = collections.abc.Buffer
else:
    class Buffer(abc.ABC):  # noqa: B024
        """Base class for classes that implement the buffer protocol.

        The buffer protocol allows Python objects to expose a low-level
        memory buffer interface. Before Python 3.12, it is not possible
        to implement the buffer protocol in pure Python code, or even
        to check whether a class implements the buffer protocol. In
        Python 3.12 and higher, the ``__buffer__`` method allows access
        to the buffer protocol from Python code, and the
        ``collections.abc.Buffer`` ABC allows checking whether a class
        implements the buffer protocol.

        To indicate support for the buffer protocol in earlier versions,
        inherit from this ABC, either in a stub file or at runtime,
        or use ABC registration. This ABC provides no methods, because
        there is no Python-accessible methods shared by pre-3.12 buffer
        classes. It is useful primarily for static checks.

        """

    # As a courtesy, register the most common stdlib buffer classes.
    Buffer.register(memoryview)
    Buffer.register(bytearray)
    Buffer.register(bytes)


# Backport of types.get_original_bases, available on 3.12+ in CPython
if hasattr(_types, "get_original_bases"):
    get_original_bases = _types.get_original_bases
else:
    def get_original_bases(cls, /):
        """Return the class's "original" bases prior to modification by `__mro_entries__`.

        Examples::

            from typing import TypeVar, Generic
            from typing_extensions import NamedTuple, TypedDict

            T = TypeVar("T")
            class Foo(Generic[T]): ...
            class Bar(Foo[int], float): ...
            class Baz(list[str]): ...
            Eggs = NamedTuple("Eggs", [("a", int), ("b", str)])
            Spam = TypedDict("Spam", {"a": int, "b": str})

            assert get_original_bases(Bar) == (Foo[int], float)
            assert get_original_bases(Baz) == (list[str],)
            assert get_original_bases(Eggs) == (NamedTuple,)
            assert get_original_bases(Spam) == (TypedDict,)
            assert get_original_bases(int) == (object,)
        """
        try:
            return cls.__dict__.get("__orig_bases__", cls.__bases__)
        except AttributeError:
            raise TypeError(
                f'Expected an instance of type, not {type(cls).__name__!r}'
            ) from None


# NewType is a class on Python 3.10+, making it pickleable
# The error message for subclassing instances of NewType was improved on 3.11+
if sys.version_info >= (3, 11):
    NewType = typing.NewType
else:
    class NewType:
        """NewType creates simple unique types with almost zero
        runtime overhead. NewType(name, tp) is considered a subtype of tp
        by static type checkers. At runtime, NewType(name, tp) returns
        a dummy callable that simply returns its argument. Usage::
            UserId = NewType('UserId', int)
            def name_by_id(user_id: UserId) -> str:
                ...
            UserId('user')          # Fails type check
            name_by_id(42)          # Fails type check
            name_by_id(UserId(42))  # OK
            num = UserId(5) + 1     # type: int
        """

        def __call__(self, obj, /):
            return obj

        def __init__(self, name, tp):
            self.__qualname__ = name
            if '.' in name:
                name = name.rpartition('.')[-1]
            self.__name__ = name
            self.__supertype__ = tp
            def_mod = _caller()
            if def_mod != 'typing_extensions':
                self.__module__ = def_mod

        def __mro_entries__(self, bases):
            # We defined __mro_entries__ to get a better error message
            # if a user attempts to subclass a NewType instance. bpo-46170
            supercls_name = self.__name__

            class Dummy:
                def __init_subclass__(cls):
                    subcls_name = cls.__name__
                    raise TypeError(
                        f"Cannot subclass an instance of NewType. "
                        f"Perhaps you were looking for: "
                        f"`{subcls_name} = NewType({subcls_name!r}, {supercls_name})`"
                    )

            return (Dummy,)

        def __repr__(self):
            return f'{self.__module__}.{self.__qualname__}'

        def __reduce__(self):
            return self.__qualname__

        if sys.version_info >= (3, 10):
            # PEP 604 methods
            # It doesn't make sense to have these methods on Python <3.10

            def __or__(self, other):
                return typing.Union[self, other]

            def __ror__(self, other):
                return typing.Union[other, self]


if sys.version_info >= (3, 14):
    TypeAliasType = typing.TypeAliasType
# 3.8-3.13
else:
    if sys.version_info >= (3, 12):
        # 3.12-3.14
        def _is_unionable(obj):
            """Corresponds to is_unionable() in unionobject.c in CPython."""
            return obj is None or isinstance(obj, (
                type,
                _types.GenericAlias,
                _types.UnionType,
                typing.TypeAliasType,
                TypeAliasType,
            ))
    else:
        # 3.8-3.11
        def _is_unionable(obj):
            """Corresponds to is_unionable() in unionobject.c in CPython."""
            return obj is None or isinstance(obj, (
                type,
                _types.GenericAlias,
                _types.UnionType,
                TypeAliasType,
            ))

    if sys.version_info < (3, 10):
        # Copied and pasted from https://github.com/python/cpython/blob/986a4e1b6fcae7fe7a1d0a26aea446107dd58dd2/Objects/genericaliasobject.c#L568-L582,
        # so that we emulate the behaviour of `types.GenericAlias`
        # on the latest versions of CPython
        _ATTRIBUTE_DELEGATION_EXCLUSIONS = frozenset({
            "__class__",
            "__bases__",
            "__origin__",
            "__args__",
            "__unpacked__",
            "__parameters__",
            "__typing_unpacked_tuple_args__",
            "__mro_entries__",
            "__reduce_ex__",
            "__reduce__",
            "__copy__",
            "__deepcopy__",
        })

        class _TypeAliasGenericAlias(typing._GenericAlias, _root=True):
            def __getattr__(self, attr):
                if attr in _ATTRIBUTE_DELEGATION_EXCLUSIONS:
                    return object.__getattr__(self, attr)
                return getattr(self.__origin__, attr)

            if sys.version_info < (3, 9):
                def __getitem__(self, item):
                    result = super().__getitem__(item)
                    result.__class__ = type(self)
                    return result

    class TypeAliasType:
        """Create named, parameterized type aliases.

        This provides a backport of the new `type` statement in Python 3.12:

            type ListOrSet[T] = list[T] | set[T]

        is equivalent to:

            T = TypeVar("T")
            ListOrSet = TypeAliasType("ListOrSet", list[T] | set[T], type_params=(T,))

        The name ListOrSet can then be used as an alias for the type it refers to.

        The type_params argument should contain all the type parameters used
        in the value of the type alias. If the alias is not generic, this
        argument is omitted.

        Static type checkers should only support type aliases declared using
        TypeAliasType that follow these rules:

        - The first argument (the name) must be a string literal.
        - The TypeAliasType instance must be immediately assigned to a variable
          of the same name. (For example, 'X = TypeAliasType("Y", int)' is invalid,
          as is 'X, Y = TypeAliasType("X", int), TypeAliasType("Y", int)').

        """

        def __init__(self, name: str, value, *, type_params=()):
            if not isinstance(name, str):
                raise TypeError("TypeAliasType name must be a string")
            if not isinstance(type_params, tuple):
                raise TypeError("type_params must be a tuple")
            self.__value__ = value
            self.__type_params__ = type_params

            default_value_encountered = False
            parameters = []
            for type_param in type_params:
                if (
                    not isinstance(type_param, (TypeVar, TypeVarTuple, ParamSpec))
                    # 3.8-3.11
                    # Unpack Backport passes isinstance(type_param, TypeVar)
                    or _is_unpack(type_param)
                ):
                    raise TypeError(f"Expected a type param, got {type_param!r}")
                has_default = (
                    getattr(type_param, '__default__', NoDefault) is not NoDefault
                )
                if default_value_encountered and not has_default:
                    raise TypeError(f"non-default type parameter '{type_param!r}'"
                                    " follows default type parameter")
                if has_default:
                    default_value_encountered = True
                if isinstance(type_param, TypeVarTuple):
                    parameters.extend(type_param)
                else:
                    parameters.append(type_param)
            self.__parameters__ = tuple(parameters)
            def_mod = _caller()
            if def_mod != 'typing_extensions':
                self.__module__ = def_mod
            # Setting this attribute closes the TypeAliasType from further modification
            self.__name__ = name

        def __setattr__(self, name: str, value: object, /) -> None:
            if hasattr(self, "__name__"):
                self._raise_attribute_error(name)
            super().__setattr__(name, value)

        def __delattr__(self, name: str, /) -> Never:
            self._raise_attribute_error(name)

        def _raise_attribute_error(self, name: str) -> Never:
            # Match the Python 3.12 error messages exactly
            if name == "__name__":
                raise AttributeError("readonly attribute")
            elif name in {"__value__", "__type_params__", "__parameters__", "__module__"}:
                raise AttributeError(
                    f"attribute '{name}' of 'typing.TypeAliasType' objects "
                    "is not writable"
                )
            else:
                raise AttributeError(
                    f"'typing.TypeAliasType' object has no attribute '{name}'"
                )

        def __repr__(self) -> str:
            return self.__name__

        if sys.version_info < (3, 11):
            def _check_single_param(self, param, recursion=0):
                # Allow [], [int], [int, str], [int, ...], [int, T]
                if param is ...:
                    return ...
                if param is None:
                    return None
                # Note in <= 3.9 _ConcatenateGenericAlias inherits from list
                if isinstance(param, list) and recursion == 0:
                    return [self._check_single_param(arg, recursion+1)
                            for arg in param]
                return typing._type_check(
                        param, f'Subscripting {self.__name__} requires a type.'
                    )

        def _check_parameters(self, parameters):
            if sys.version_info < (3, 11):
                return tuple(
                    self._check_single_param(item)
                    for item in parameters
                )
            return tuple(typing._type_check(
                        item, f'Subscripting {self.__name__} requires a type.'
                    )
                    for item in parameters
            )

        def __getitem__(self, parameters):
            if not self.__type_params__:
                raise TypeError("Only generic type aliases are subscriptable")
            if not isinstance(parameters, tuple):
                parameters = (parameters,)
            # Using 3.9 here will create problems with Concatenate
            if sys.version_info >= (3, 10):
                return _types.GenericAlias(self, parameters)
            type_vars = _collect_type_vars(parameters)
            parameters = self._check_parameters(parameters)
            alias = _TypeAliasGenericAlias(self, parameters)
            # alias.__parameters__ is not complete if Concatenate is present
            # as it is converted to a list from which no parameters are extracted.
            if alias.__parameters__ != type_vars:
                alias.__parameters__ = type_vars
            return alias

        def __reduce__(self):
            return self.__name__

        def __init_subclass__(cls, *args, **kwargs):
            raise TypeError(
                "type 'typing_extensions.TypeAliasType' is not an acceptable base type"
            )

        # The presence of this method convinces typing._type_check
        # that TypeAliasTypes are types.
        def __call__(self):
            raise TypeError("Type alias is not callable")

        if sys.version_info >= (3, 10):
            def __or__(self, right):
                # For forward compatibility with 3.12, reject Unions
                # that are not accepted by the built-in Union.
                if not _is_unionable(right):
                    return NotImplemented
                return typing.Union[self, right]

            def __ror__(self, left):
                if not _is_unionable(left):
                    return NotImplemented
                return typing.Union[left, self]


if hasattr(typing, "is_protocol"):
    is_protocol = typing.is_protocol
    get_protocol_members = typing.get_protocol_members
else:
    def is_protocol(tp: type, /) -> bool:
        """Return True if the given type is a Protocol.

        Example::

            >>> from typing_extensions import Protocol, is_protocol
            >>> class P(Protocol):
            ...     def a(self) -> str: ...
            ...     b: int
            >>> is_protocol(P)
            True
            >>> is_protocol(int)
            False
        """
        return (
            isinstance(tp, type)
            and getattr(tp, '_is_protocol', False)
            and tp is not Protocol
            and tp is not typing.Protocol
        )

    def get_protocol_members(tp: type, /) -> typing.FrozenSet[str]:
        """Return the set of members defined in a Protocol.

        Example::

            >>> from typing_extensions import Protocol, get_protocol_members
            >>> class P(Protocol):
            ...     def a(self) -> str: ...
            ...     b: int
            >>> get_protocol_members(P)
            frozenset({'a', 'b'})

        Raise a TypeError for arguments that are not Protocols.
        """
        if not is_protocol(tp):
            raise TypeError(f'{tp!r} is not a Protocol')
        if hasattr(tp, '__protocol_attrs__'):
            return frozenset(tp.__protocol_attrs__)
        return frozenset(_get_protocol_attrs(tp))


if hasattr(typing, "Doc"):
    Doc = typing.Doc
else:
    class Doc:
        """Define the documentation of a type annotation using ``Annotated``, to be
         used in class attributes, function and method parameters, return values,
         and variables.

        The value should be a positional-only string literal to allow static tools
        like editors and documentation generators to use it.

        This complements docstrings.

        The string value passed is available in the attribute ``documentation``.

        Example::

            >>> from typing_extensions import Annotated, Doc
            >>> def hi(to: Annotated[str, Doc("Who to say hi to")]) -> None: ...
        """
        def __init__(self, documentation: str, /) -> None:
            self.documentation = documentation

        def __repr__(self) -> str:
            return f"Doc({self.documentation!r})"

        def __hash__(self) -> int:
            return hash(self.documentation)

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, Doc):
                return NotImplemented
            return self.documentation == other.documentation


_CapsuleType = getattr(_types, "CapsuleType", None)

if _CapsuleType is None:
    try:
        import _socket
    except ImportError:
        pass
    else:
        _CAPI = getattr(_socket, "CAPI", None)
        if _CAPI is not None:
            _CapsuleType = type(_CAPI)

if _CapsuleType is not None:
    CapsuleType = _CapsuleType
    __all__.append("CapsuleType")


# Using this convoluted approach so that this keeps working
# whether we end up using PEP 649 as written, PEP 749, or
# some other variation: in any case, inspect.get_annotations
# will continue to exist and will gain a `format` parameter.
_PEP_649_OR_749_IMPLEMENTED = (
    hasattr(inspect, 'get_annotations')
    and inspect.get_annotations.__kwdefaults__ is not None
    and "format" in inspect.get_annotations.__kwdefaults__
)


class Format(enum.IntEnum):
    VALUE = 1
    FORWARDREF = 2
    STRING = 3


if _PEP_649_OR_749_IMPLEMENTED:
    get_annotations = inspect.get_annotations
else:
    def get_annotations(obj, *, globals=None, locals=None, eval_str=False,
                        format=Format.VALUE):
        """Compute the annotations dict for an object.

        obj may be a callable, class, or module.
        Passing in an object of any other type raises TypeError.

        Returns a dict.  get_annotations() returns a new dict every time
        it's called; calling it twice on the same object will return two
        different but equivalent dicts.

        This is a backport of `inspect.get_annotations`, which has been
        in the standard library since Python 3.10. See the standard library
        documentation for more:

            https://docs.python.org/3/library/inspect.html#inspect.get_annotations

        This backport adds the *format* argument introduced by PEP 649. The
        three formats supported are:
        * VALUE: the annotations are returned as-is. This is the default and
          it is compatible with the behavior on previous Python versions.
        * FORWARDREF: return annotations as-is if possible, but replace any
          undefined names with ForwardRef objects. The implementation proposed by
          PEP 649 relies on language changes that cannot be backported; the
          typing-extensions implementation simply returns the same result as VALUE.
        * STRING: return annotations as strings, in a format close to the original
          source. Again, this behavior cannot be replicated directly in a backport.
          As an approximation, typing-extensions retrieves the annotations under
          VALUE semantics and then stringifies them.

        The purpose of this backport is to allow users who would like to use
        FORWARDREF or STRING semantics once PEP 649 is implemented, but who also
        want to support earlier Python versions, to simply write:

            typing_extensions.get_annotations(obj, format=Format.FORWARDREF)

        """
        format = Format(format)

        if eval_str and format is not Format.VALUE:
            raise ValueError("eval_str=True is only supported with format=Format.VALUE")

        if isinstance(obj, type):
            # class
            obj_dict = getattr(obj, '__dict__', None)
            if obj_dict and hasattr(obj_dict, 'get'):
                ann = obj_dict.get('__annotations__', None)
                if isinstance(ann, _types.GetSetDescriptorType):
                    ann = None
            else:
                ann = None

            obj_globals = None
            module_name = getattr(obj, '__module__', None)
            if module_name:
                module = sys.modules.get(module_name, None)
                if module:
                    obj_globals = getattr(module, '__dict__', None)
            obj_locals = dict(vars(obj))
            unwrap = obj
        elif isinstance(obj, _types.ModuleType):
            # module
            ann = getattr(obj, '__annotations__', None)
            obj_globals = obj.__dict__
            obj_locals = None
            unwrap = None
        elif callable(obj):
            # this includes types.Function, types.BuiltinFunctionType,
            # types.BuiltinMethodType, functools.partial, functools.singledispatch,
            # "class funclike" from Lib/test/test_inspect... on and on it goes.
            ann = getattr(obj, '__annotations__', None)
            obj_globals = getattr(obj, '__globals__', None)
            obj_locals = None
            unwrap = obj
        elif hasattr(obj, '__annotations__'):
            ann = obj.__annotations__
            obj_globals = obj_locals = unwrap = None
        else:
            raise TypeError(f"{obj!r} is not a module, class, or callable.")

        if ann is None:
            return {}

        if not isinstance(ann, dict):
            raise ValueError(f"{obj!r}.__annotations__ is neither a dict nor None")

        if not ann:
            return {}

        if not eval_str:
            if format is Format.STRING:
                return {
                    key: value if isinstance(value, str) else typing._type_repr(value)
                    for key, value in ann.items()
                }
            return dict(ann)

        if unwrap is not None:
            while True:
                if hasattr(unwrap, '__wrapped__'):
                    unwrap = unwrap.__wrapped__
                    continue
                if isinstance(unwrap, functools.partial):
                    unwrap = unwrap.func
                    continue
                break
            if hasattr(unwrap, "__globals__"):
                obj_globals = unwrap.__globals__

        if globals is None:
            globals = obj_globals
        if locals is None:
            locals = obj_locals or {}

        # "Inject" type parameters into the local namespace
        # (unless they are shadowed by assignments *in* the local namespace),
        # as a way of emulating annotation scopes when calling `eval()`
        if type_params := getattr(obj, "__type_params__", ()):
            locals = {param.__name__: param for param in type_params} | locals

        return_value = {key:
            value if not isinstance(value, str) else eval(value, globals, locals)
            for key, value in ann.items() }
        return return_value


if hasattr(typing, "evaluate_forward_ref"):
    evaluate_forward_ref = typing.evaluate_forward_ref
else:
    # Implements annotationlib.ForwardRef.evaluate
    def _eval_with_owner(
        forward_ref, *, owner=None, globals=None, locals=None, type_params=None
    ):
        if forward_ref.__forward_evaluated__:
            return forward_ref.__forward_value__
        if getattr(forward_ref, "__cell__", None) is not None:
            try:
                value = forward_ref.__cell__.cell_contents
            except ValueError:
                pass
            else:
                forward_ref.__forward_evaluated__ = True
                forward_ref.__forward_value__ = value
                return value
        if owner is None:
            owner = getattr(forward_ref, "__owner__", None)

        if (
            globals is None
            and getattr(forward_ref, "__forward_module__", None) is not None
        ):
            globals = getattr(
                sys.modules.get(forward_ref.__forward_module__, None), "__dict__", None
            )
        if globals is None:
            globals = getattr(forward_ref, "__globals__", None)
        if globals is None:
            if isinstance(owner, type):
                module_name = getattr(owner, "__module__", None)
                if module_name:
                    module = sys.modules.get(module_name, None)
                    if module:
                        globals = getattr(module, "__dict__", None)
            elif isinstance(owner, _types.ModuleType):
                globals = getattr(owner, "__dict__", None)
            elif callable(owner):
                globals = getattr(owner, "__globals__", None)

        # If we pass None to eval() below, the globals of this module are used.
        if globals is None:
            globals = {}

        if locals is None:
            locals = {}
            if isinstance(owner, type):
                locals.update(vars(owner))

        if type_params is None and owner is not None:
            # "Inject" type parameters into the local namespace
            # (unless they are shadowed by assignments *in* the local namespace),
            # as a way of emulating annotation scopes when calling `eval()`
            type_params = getattr(owner, "__type_params__", None)

        # type parameters require some special handling,
        # as they exist in their own scope
        # but `eval()` does not have a dedicated parameter for that scope.
        # For classes, names in type parameter scopes should override
        # names in the global scope (which here are called `localns`!),
        # but should in turn be overridden by names in the class scope
        # (which here are called `globalns`!)
        if type_params is not None:
            globals = dict(globals)
            locals = dict(locals)
            for param in type_params:
                param_name = param.__name__
                if (
                    _FORWARD_REF_HAS_CLASS and not forward_ref.__forward_is_class__
                ) or param_name not in globals:
                    globals[param_name] = param
                    locals.pop(param_name, None)

        arg = forward_ref.__forward_arg__
        if arg.isidentifier() and not keyword.iskeyword(arg):
            if arg in locals:
                value = locals[arg]
            elif arg in globals:
                value = globals[arg]
            elif hasattr(builtins, arg):
                return getattr(builtins, arg)
            else:
                raise NameError(arg)
        else:
            code = forward_ref.__forward_code__
            value = eval(code, globals, locals)
        forward_ref.__forward_evaluated__ = True
        forward_ref.__forward_value__ = value
        return value

    def _lax_type_check(
        value, msg, is_argument=True, *, module=None, allow_special_forms=False
    ):
        """
        A lax Python 3.11+ like version of typing._type_check
        """
        if hasattr(typing, "_type_convert"):
            if (
                sys.version_info >= (3, 10, 3)
                or (3, 9, 10) < sys.version_info[:3] < (3, 10)
            ):
                # allow_special_forms introduced later cpython/#30926 (bpo-46539)
                type_ = typing._type_convert(
                    value,
                    module=module,
                    allow_special_forms=allow_special_forms,
                )
            # module was added with bpo-41249 before is_class (bpo-46539)
            elif "__forward_module__" in typing.ForwardRef.__slots__:
                type_ = typing._type_convert(value, module=module)
            else:
                type_ = typing._type_convert(value)
        else:
            if value is None:
                return type(None)
            if isinstance(value, str):
                return ForwardRef(value)
            type_ = value
        invalid_generic_forms = (Generic, Protocol)
        if not allow_special_forms:
            invalid_generic_forms += (ClassVar,)
            if is_argument:
                invalid_generic_forms += (Final,)
        if (
            isinstance(type_, typing._GenericAlias)
            and get_origin(type_) in invalid_generic_forms
        ):
            raise TypeError(f"{type_} is not valid as type argument") from None
        if type_ in (Any, LiteralString, NoReturn, Never, Self, TypeAlias):
            return type_
        if allow_special_forms and type_ in (ClassVar, Final):
            return type_
        if (
            isinstance(type_, (_SpecialForm, typing._SpecialForm))
            or type_ in (Generic, Protocol)
        ):
            raise TypeError(f"Plain {type_} is not valid as type argument") from None
        if type(type_) is tuple:  # lax version with tuple instead of callable
            raise TypeError(f"{msg} Got {type_!r:.100}.")
        return type_

    def evaluate_forward_ref(
        forward_ref,
        *,
        owner=None,
        globals=None,
        locals=None,
        type_params=None,
        format=Format.VALUE,
        _recursive_guard=frozenset(),
    ):
        """Evaluate a forward reference as a type hint.

        This is similar to calling the ForwardRef.evaluate() method,
        but unlike that method, evaluate_forward_ref() also:

        * Recursively evaluates forward references nested within the type hint.
        * Rejects certain objects that are not valid type hints.
        * Replaces type hints that evaluate to None with types.NoneType.
        * Supports the *FORWARDREF* and *STRING* formats.

        *forward_ref* must be an instance of ForwardRef. *owner*, if given,
        should be the object that holds the annotations that the forward reference
        derived from, such as a module, class object, or function. It is used to
        infer the namespaces to use for looking up names. *globals* and *locals*
        can also be explicitly given to provide the global and local namespaces.
        *type_params* is a tuple of type parameters that are in scope when
        evaluating the forward reference. This parameter must be provided (though
        it may be an empty tuple) if *owner* is not given and the forward reference
        does not already have an owner set. *format* specifies the format of the
        annotation and is a member of the annotationlib.Format enum.

        """
        if format == Format.STRING:
            return forward_ref.__forward_arg__
        if forward_ref.__forward_arg__ in _recursive_guard:
            return forward_ref

        # Evaluate the forward reference
        try:
            value = _eval_with_owner(
                forward_ref,
                owner=owner,
                globals=globals,
                locals=locals,
                type_params=type_params,
            )
        except NameError:
            if format == Format.FORWARDREF:
                return forward_ref
            else:
                raise

        msg = "Forward references must evaluate to types."
        if not _FORWARD_REF_HAS_CLASS:
            allow_special_forms = not forward_ref.__forward_is_argument__
        else:
            allow_special_forms = forward_ref.__forward_is_class__
        type_ = _lax_type_check(
            value,
            msg,
            is_argument=forward_ref.__forward_is_argument__,
            allow_special_forms=allow_special_forms,
        )

        # Recursively evaluate the type
        if isinstance(type_, ForwardRef):
            if getattr(type_, "__forward_module__", True) is not None:
                globals = None
            return evaluate_forward_ref(
                type_,
                globals=globals,
                locals=locals,
                 type_params=type_params, owner=owner,
                _recursive_guard=_recursive_guard, format=format
            )
        if sys.version_info < (3, 12, 5) and type_params:
            # Make use of type_params
            locals = dict(locals) if locals else {}
            for tvar in type_params:
                if tvar.__name__ not in locals:  # lets not overwrite something present
                    locals[tvar.__name__] = tvar
        if sys.version_info < (3, 9):
            return typing._eval_type(
                type_,
                globals,
                locals,
            )
        if sys.version_info < (3, 12, 5):
            return typing._eval_type(
                type_,
                globals,
                locals,
                recursive_guard=_recursive_guard | {forward_ref.__forward_arg__},
            )
        if sys.version_info < (3, 14):
            return typing._eval_type(
                type_,
                globals,
                locals,
                type_params,
                recursive_guard=_recursive_guard | {forward_ref.__forward_arg__},
            )
        return typing._eval_type(
            type_,
            globals,
            locals,
            type_params,
            recursive_guard=_recursive_guard | {forward_ref.__forward_arg__},
            format=format,
            owner=owner,
        )


# Aliases for items that have always been in typing.
# Explicitly assign these (rather than using `from typing import *` at the top),
# so that we get a CI error if one of these is deleted from typing.py
# in a future version of Python
AbstractSet = typing.AbstractSet
AnyStr = typing.AnyStr
BinaryIO = typing.BinaryIO
Callable = typing.Callable
Collection = typing.Collection
Container = typing.Container
Dict = typing.Dict
ForwardRef = typing.ForwardRef
FrozenSet = typing.FrozenSet
Generic = typing.Generic
Hashable = typing.Hashable
IO = typing.IO
ItemsView = typing.ItemsView
Iterable = typing.Iterable
Iterator = typing.Iterator
KeysView = typing.KeysView
List = typing.List
Mapping = typing.Mapping
MappingView = typing.MappingView
Match = typing.Match
MutableMapping = typing.MutableMapping
MutableSequence = typing.MutableSequence
MutableSet = typing.MutableSet
Optional = typing.Optional
Pattern = typing.Pattern
Reversible = typing.Reversible
Sequence = typing.Sequence
Set = typing.Set
Sized = typing.Sized
TextIO = typing.TextIO
Tuple = typing.Tuple
Union = typing.Union
ValuesView = typing.ValuesView
cast = typing.cast
no_type_check = typing.no_type_check
no_type_check_decorator = typing.no_type_check_decorator

# === NexusCore/openenv\Lib\site-packages\regex\_regex_core.py ===
#
# Secret Labs' Regular Expression Engine core module
#
# Copyright (c) 1998-2001 by Secret Labs AB.  All rights reserved.
#
# This version of the SRE library can be redistributed under CNRI's
# Python 1.6 license.  For any other use, please contact Secret Labs
# AB (info@pythonware.com).
#
# Portions of this engine have been developed in cooperation with
# CNRI.  Hewlett-Packard provided funding for 1.6 integration and
# other compatibility work.
#
# 2010-01-16 mrab Python front-end re-written and extended

import enum
import string
import unicodedata
from collections import defaultdict

import regex._regex as _regex

__all__ = ["A", "ASCII", "B", "BESTMATCH", "D", "DEBUG", "E", "ENHANCEMATCH",
  "F", "FULLCASE", "I", "IGNORECASE", "L", "LOCALE", "M", "MULTILINE", "P",
  "POSIX", "R", "REVERSE", "S", "DOTALL", "T", "TEMPLATE", "U", "UNICODE",
  "V0", "VERSION0", "V1", "VERSION1", "W", "WORD", "X", "VERBOSE", "error",
  "Scanner", "RegexFlag"]

# The regex exception.
class error(Exception):
    """Exception raised for invalid regular expressions.

    Attributes:

        msg: The unformatted error message
        pattern: The regular expression pattern
        pos: The position in the pattern where compilation failed, or None
        lineno: The line number where compilation failed, unless pos is None
        colno: The column number where compilation failed, unless pos is None
    """

    def __init__(self, message, pattern=None, pos=None):
        newline = '\n' if isinstance(pattern, str) else b'\n'
        self.msg = message
        self.pattern = pattern
        self.pos = pos
        if pattern is not None and pos is not None:
            self.lineno = pattern.count(newline, 0, pos) + 1
            self.colno = pos - pattern.rfind(newline, 0, pos)

            message = "{} at position {}".format(message, pos)

            if newline in pattern:
                message += " (line {}, column {})".format(self.lineno,
                  self.colno)

        Exception.__init__(self, message)

# The exception for when a positional flag has been turned on in the old
# behaviour.
class _UnscopedFlagSet(Exception):
    pass

# The exception for when parsing fails and we want to try something else.
class ParseError(Exception):
    pass

# The exception for when there isn't a valid first set.
class _FirstSetError(Exception):
    pass

# Flags.
class RegexFlag(enum.IntFlag):
    A = ASCII = 0x80          # Assume ASCII locale.
    B = BESTMATCH = 0x1000    # Best fuzzy match.
    D = DEBUG = 0x200         # Print parsed pattern.
    E = ENHANCEMATCH = 0x8000 # Attempt to improve the fit after finding the first
                              # fuzzy match.
    F = FULLCASE = 0x4000     # Unicode full case-folding.
    I = IGNORECASE = 0x2      # Ignore case.
    L = LOCALE = 0x4          # Assume current 8-bit locale.
    M = MULTILINE = 0x8       # Make anchors look for newline.
    P = POSIX = 0x10000       # POSIX-style matching (leftmost longest).
    R = REVERSE = 0x400       # Search backwards.
    S = DOTALL = 0x10         # Make dot match newline.
    U = UNICODE = 0x20        # Assume Unicode locale.
    V0 = VERSION0 = 0x2000    # Old legacy behaviour.
    V1 = VERSION1 = 0x100     # New enhanced behaviour.
    W = WORD = 0x800          # Default Unicode word breaks.
    X = VERBOSE = 0x40        # Ignore whitespace and comments.
    T = TEMPLATE = 0x1        # Template (present because re module has it).

    def __repr__(self):
        if self._name_ is not None:
            return 'regex.%s' % self._name_

        value = self._value_
        members = []
        negative = value < 0

        if negative:
            value = ~value

        for m in self.__class__:
            if value & m._value_:
                value &= ~m._value_
                members.append('regex.%s' % m._name_)

        if value:
            members.append(hex(value))

        res = '|'.join(members)

        if negative:
            if len(members) > 1:
                res = '~(%s)' % res
            else:
                res = '~%s' % res

        return res

    __str__ = object.__str__

globals().update(RegexFlag.__members__)

DEFAULT_VERSION = VERSION1

_ALL_VERSIONS = VERSION0 | VERSION1
_ALL_ENCODINGS = ASCII | LOCALE | UNICODE

# The default flags for the various versions.
DEFAULT_FLAGS = {VERSION0: 0, VERSION1: FULLCASE}

# The mask for the flags.
GLOBAL_FLAGS = (_ALL_VERSIONS | BESTMATCH | DEBUG | ENHANCEMATCH | POSIX |
  REVERSE)
SCOPED_FLAGS = (FULLCASE | IGNORECASE | MULTILINE | DOTALL | WORD | VERBOSE |
  _ALL_ENCODINGS)

ALPHA = frozenset(string.ascii_letters)
DIGITS = frozenset(string.digits)
ALNUM = ALPHA | DIGITS
OCT_DIGITS = frozenset(string.octdigits)
HEX_DIGITS = frozenset(string.hexdigits)
SPECIAL_CHARS = frozenset("()|?*+{^$.[\\#") | frozenset([""])
NAMED_CHAR_PART = ALNUM | frozenset(" -")
PROPERTY_NAME_PART = ALNUM | frozenset(" &_-.")
SET_OPS = ("||", "~~", "&&", "--")

# The width of the code words inside the regex engine.
BYTES_PER_CODE = _regex.get_code_size()
BITS_PER_CODE = BYTES_PER_CODE * 8

# The repeat count which represents infinity.
UNLIMITED = (1 << BITS_PER_CODE) - 1

# The regular expression flags.
REGEX_FLAGS = {"a": ASCII, "b": BESTMATCH, "e": ENHANCEMATCH, "f": FULLCASE,
  "i": IGNORECASE, "L": LOCALE, "m": MULTILINE, "p": POSIX, "r": REVERSE,
  "s": DOTALL, "u": UNICODE, "V0": VERSION0, "V1": VERSION1, "w": WORD, "x":
  VERBOSE}

# The case flags.
CASE_FLAGS = FULLCASE | IGNORECASE
NOCASE = 0
FULLIGNORECASE = FULLCASE | IGNORECASE

FULL_CASE_FOLDING = UNICODE | FULLIGNORECASE

CASE_FLAGS_COMBINATIONS = {0: 0, FULLCASE: 0, IGNORECASE: IGNORECASE,
  FULLIGNORECASE: FULLIGNORECASE}

# The number of digits in hexadecimal escapes.
HEX_ESCAPES = {"x": 2, "u": 4, "U": 8}

# The names of the opcodes.
OPCODES = """
FAILURE
SUCCESS
ANY
ANY_ALL
ANY_ALL_REV
ANY_REV
ANY_U
ANY_U_REV
ATOMIC
BOUNDARY
BRANCH
CALL_REF
CHARACTER
CHARACTER_IGN
CHARACTER_IGN_REV
CHARACTER_REV
CONDITIONAL
DEFAULT_BOUNDARY
DEFAULT_END_OF_WORD
DEFAULT_START_OF_WORD
END
END_OF_LINE
END_OF_LINE_U
END_OF_STRING
END_OF_STRING_LINE
END_OF_STRING_LINE_U
END_OF_WORD
FUZZY
GRAPHEME_BOUNDARY
GREEDY_REPEAT
GROUP
GROUP_CALL
GROUP_EXISTS
KEEP
LAZY_REPEAT
LOOKAROUND
NEXT
PROPERTY
PROPERTY_IGN
PROPERTY_IGN_REV
PROPERTY_REV
PRUNE
RANGE
RANGE_IGN
RANGE_IGN_REV
RANGE_REV
REF_GROUP
REF_GROUP_FLD
REF_GROUP_FLD_REV
REF_GROUP_IGN
REF_GROUP_IGN_REV
REF_GROUP_REV
SEARCH_ANCHOR
SET_DIFF
SET_DIFF_IGN
SET_DIFF_IGN_REV
SET_DIFF_REV
SET_INTER
SET_INTER_IGN
SET_INTER_IGN_REV
SET_INTER_REV
SET_SYM_DIFF
SET_SYM_DIFF_IGN
SET_SYM_DIFF_IGN_REV
SET_SYM_DIFF_REV
SET_UNION
SET_UNION_IGN
SET_UNION_IGN_REV
SET_UNION_REV
SKIP
START_OF_LINE
START_OF_LINE_U
START_OF_STRING
START_OF_WORD
STRING
STRING_FLD
STRING_FLD_REV
STRING_IGN
STRING_IGN_REV
STRING_REV
FUZZY_EXT
"""

# Define the opcodes in a namespace.
class Namespace:
    pass

OP = Namespace()
for i, op in enumerate(OPCODES.split()):
    setattr(OP, op, i)

def _shrink_cache(cache_dict, args_dict, locale_sensitive, max_length, divisor=5):
    """Make room in the given cache.

    Args:
        cache_dict: The cache dictionary to modify.
        args_dict: The dictionary of named list args used by patterns.
        max_length: Maximum # of entries in cache_dict before it is shrunk.
        divisor: Cache will shrink to max_length - 1/divisor*max_length items.
    """
    # Toss out a fraction of the entries at random to make room for new ones.
    # A random algorithm was chosen as opposed to simply cache_dict.popitem()
    # as popitem could penalize the same regular expression repeatedly based
    # on its internal hash value.  Being random should spread the cache miss
    # love around.
    cache_keys = tuple(cache_dict.keys())
    overage = len(cache_keys) - max_length
    if overage < 0:
        # Cache is already within limits.  Normally this should not happen
        # but it could due to multithreading.
        return

    number_to_toss = max_length // divisor + overage

    # The import is done here to avoid a circular dependency.
    import random
    if not hasattr(random, 'sample'):
        # Do nothing while resolving the circular dependency:
        #  re->random->warnings->tokenize->string->re
        return

    for doomed_key in random.sample(cache_keys, number_to_toss):
        try:
            del cache_dict[doomed_key]
        except KeyError:
            # Ignore problems if the cache changed from another thread.
            pass

    # Rebuild the arguments and locale-sensitivity dictionaries.
    args_dict.clear()
    sensitivity_dict = {}
    for pattern, pattern_type, flags, args, default_version, locale in tuple(cache_dict):
        args_dict[pattern, pattern_type, flags, default_version, locale] = args
        try:
            sensitivity_dict[pattern_type, pattern] = locale_sensitive[pattern_type, pattern]
        except KeyError:
            pass

    locale_sensitive.clear()
    locale_sensitive.update(sensitivity_dict)

def _fold_case(info, string):
    "Folds the case of a string."
    flags = info.flags
    if (flags & _ALL_ENCODINGS) == 0:
        flags |= info.guess_encoding

    return _regex.fold_case(flags, string)

def is_cased_i(info, char):
    "Checks whether a character is cased."
    return len(_regex.get_all_cases(info.flags, char)) > 1

def is_cased_f(flags, char):
    "Checks whether a character is cased."
    return len(_regex.get_all_cases(flags, char)) > 1

def _compile_firstset(info, fs):
    "Compiles the firstset for the pattern."
    reverse = bool(info.flags & REVERSE)
    fs = _check_firstset(info, reverse, fs)
    if not fs:
        return []

    # Compile the firstset.
    return fs.compile(reverse)

def _check_firstset(info, reverse, fs):
    "Checks the firstset for the pattern."
    if not fs or None in fs:
        return None

    # If we ignore the case, for simplicity we won't build a firstset.
    members = set()
    case_flags = NOCASE
    for i in fs:
        if isinstance(i, Character) and not i.positive:
            return None

#        if i.case_flags:
#            if isinstance(i, Character):
#                if is_cased_i(info, i.value):
#                    return []
#            elif isinstance(i, SetBase):
#                return []
        case_flags |= i.case_flags
        members.add(i.with_flags(case_flags=NOCASE))

    if case_flags == (FULLCASE | IGNORECASE):
        return None

    # Build the firstset.
    fs = SetUnion(info, list(members), case_flags=case_flags & ~FULLCASE,
      zerowidth=True)
    fs = fs.optimise(info, reverse, in_set=True)

    return fs

def _flatten_code(code):
    "Flattens the code from a list of tuples."
    flat_code = []
    for c in code:
        flat_code.extend(c)

    return flat_code

def make_case_flags(info):
    "Makes the case flags."
    flags = info.flags & CASE_FLAGS

    # Turn off FULLCASE if ASCII is turned on.
    if info.flags & ASCII:
        flags &= ~FULLCASE

    return flags

def make_character(info, value, in_set=False):
    "Makes a character literal."
    if in_set:
        # A character set is built case-sensitively.
        return Character(value)

    return Character(value, case_flags=make_case_flags(info))

def make_ref_group(info, name, position):
    "Makes a group reference."
    return RefGroup(info, name, position, case_flags=make_case_flags(info))

def make_string_set(info, name):
    "Makes a string set."
    return StringSet(info, name, case_flags=make_case_flags(info))

def make_property(info, prop, in_set):
    "Makes a property."
    if in_set:
        return prop

    return prop.with_flags(case_flags=make_case_flags(info))

def _parse_pattern(source, info):
    "Parses a pattern, eg. 'a|b|c'."
    branches = [parse_sequence(source, info)]
    while source.match("|"):
        branches.append(parse_sequence(source, info))

    if len(branches) == 1:
        return branches[0]
    return Branch(branches)

def parse_sequence(source, info):
    "Parses a sequence, eg. 'abc'."
    sequence = [None]
    case_flags = make_case_flags(info)
    while True:
        saved_pos = source.pos
        ch = source.get()
        if ch in SPECIAL_CHARS:
            if ch in ")|":
                # The end of a sequence. At the end of the pattern ch is "".
                source.pos = saved_pos
                break
            elif ch == "\\":
                # An escape sequence outside a set.
                sequence.append(parse_escape(source, info, False))
            elif ch == "(":
                # A parenthesised subpattern or a flag.
                element = parse_paren(source, info)
                if element is None:
                    case_flags = make_case_flags(info)
                else:
                    sequence.append(element)
            elif ch == ".":
                # Any character.
                if info.flags & DOTALL:
                    sequence.append(AnyAll())
                elif info.flags & WORD:
                    sequence.append(AnyU())
                else:
                    sequence.append(Any())
            elif ch == "[":
                # A character set.
                sequence.append(parse_set(source, info))
            elif ch == "^":
                # The start of a line or the string.
                if info.flags & MULTILINE:
                    if info.flags & WORD:
                        sequence.append(StartOfLineU())
                    else:
                        sequence.append(StartOfLine())
                else:
                    sequence.append(StartOfString())
            elif ch == "$":
                # The end of a line or the string.
                if info.flags & MULTILINE:
                    if info.flags & WORD:
                        sequence.append(EndOfLineU())
                    else:
                        sequence.append(EndOfLine())
                else:
                    if info.flags & WORD:
                        sequence.append(EndOfStringLineU())
                    else:
                        sequence.append(EndOfStringLine())
            elif ch in "?*+{":
                # Looks like a quantifier.
                counts = parse_quantifier(source, info, ch)
                if counts:
                    # It _is_ a quantifier.
                    apply_quantifier(source, info, counts, case_flags, ch,
                      saved_pos, sequence)
                    sequence.append(None)
                else:
                    # It's not a quantifier. Maybe it's a fuzzy constraint.
                    constraints = parse_fuzzy(source, info, ch, case_flags)
                    if constraints:
                        # It _is_ a fuzzy constraint.
                        apply_constraint(source, info, constraints, case_flags,
                          saved_pos, sequence)
                        sequence.append(None)
                    else:
                        # The element was just a literal.
                        sequence.append(Character(ord(ch),
                          case_flags=case_flags))
            else:
                # A literal.
                sequence.append(Character(ord(ch), case_flags=case_flags))
        else:
            # A literal.
            sequence.append(Character(ord(ch), case_flags=case_flags))

    sequence = [item for item in sequence if item is not None]
    return Sequence(sequence)

def apply_quantifier(source, info, counts, case_flags, ch, saved_pos,
  sequence):
    element = sequence.pop()
    if element is None:
        if sequence:
            raise error("multiple repeat", source.string, saved_pos)
        raise error("nothing to repeat", source.string, saved_pos)

    if isinstance(element, (GreedyRepeat, LazyRepeat, PossessiveRepeat)):
        raise error("multiple repeat", source.string, saved_pos)

    min_count, max_count = counts
    saved_pos = source.pos
    ch = source.get()
    if ch == "?":
        # The "?" suffix that means it's a lazy repeat.
        repeated = LazyRepeat
    elif ch == "+":
        # The "+" suffix that means it's a possessive repeat.
        repeated = PossessiveRepeat
    else:
        # No suffix means that it's a greedy repeat.
        source.pos = saved_pos
        repeated = GreedyRepeat

    # Ignore the quantifier if it applies to a zero-width item or the number of
    # repeats is fixed at 1.
    if not element.is_empty() and (min_count != 1 or max_count != 1):
        element = repeated(element, min_count, max_count)

    sequence.append(element)

def apply_constraint(source, info, constraints, case_flags, saved_pos,
  sequence):
    element = sequence.pop()
    if element is None:
        raise error("nothing for fuzzy constraint", source.string, saved_pos)

    # If a group is marked as fuzzy then put all of the fuzzy part in the
    # group.
    if isinstance(element, Group):
        element.subpattern = Fuzzy(element.subpattern, constraints)
        sequence.append(element)
    else:
        sequence.append(Fuzzy(element, constraints))

_QUANTIFIERS = {"?": (0, 1), "*": (0, None), "+": (1, None)}

def parse_quantifier(source, info, ch):
    "Parses a quantifier."
    q = _QUANTIFIERS.get(ch)
    if q:
        # It's a quantifier.
        return q

    if ch == "{":
        # Looks like a limited repeated element, eg. 'a{2,3}'.
        counts = parse_limited_quantifier(source)
        if counts:
            return counts

    return None

def is_above_limit(count):
    "Checks whether a count is above the maximum."
    return count is not None and count >= UNLIMITED

def parse_limited_quantifier(source):
    "Parses a limited quantifier."
    saved_pos = source.pos
    min_count = parse_count(source)
    if source.match(","):
        max_count = parse_count(source)

        # No minimum means 0 and no maximum means unlimited.
        min_count = int(min_count or 0)
        max_count = int(max_count) if max_count else None
    else:
        if not min_count:
            source.pos = saved_pos
            return None

        min_count = max_count = int(min_count)

    if not source.match ("}"):
        source.pos = saved_pos
        return None

    if is_above_limit(min_count) or is_above_limit(max_count):
        raise error("repeat count too big", source.string, saved_pos)

    if max_count is not None and min_count > max_count:
        raise error("min repeat greater than max repeat", source.string,
          saved_pos)

    return min_count, max_count

def parse_fuzzy(source, info, ch, case_flags):
    "Parses a fuzzy setting, if present."
    saved_pos = source.pos

    if ch != "{":
        return None

    constraints = {}
    try:
        parse_fuzzy_item(source, constraints)
        while source.match(","):
            parse_fuzzy_item(source, constraints)
    except ParseError:
        source.pos = saved_pos
        return None

    if source.match(":"):
        constraints["test"] = parse_fuzzy_test(source, info, case_flags)

    if not source.match("}"):
        raise error("expected }", source.string, source.pos)

    return constraints

def parse_fuzzy_item(source, constraints):
    "Parses a fuzzy setting item."
    saved_pos = source.pos
    try:
        parse_cost_constraint(source, constraints)
    except ParseError:
        source.pos = saved_pos

        parse_cost_equation(source, constraints)

def parse_cost_constraint(source, constraints):
    "Parses a cost constraint."
    saved_pos = source.pos
    ch = source.get()
    if ch in ALPHA:
        # Syntax: constraint [("<=" | "<") cost]
        constraint = parse_constraint(source, constraints, ch)

        max_inc = parse_fuzzy_compare(source)

        if max_inc is None:
            # No maximum cost.
            constraints[constraint] = 0, None
        else:
            # There's a maximum cost.
            cost_pos = source.pos
            max_cost = parse_cost_limit(source)

            # Inclusive or exclusive limit?
            if not max_inc:
                max_cost -= 1

            if max_cost < 0:
                raise error("bad fuzzy cost limit", source.string, cost_pos)

            constraints[constraint] = 0, max_cost
    elif ch in DIGITS:
        # Syntax: cost ("<=" | "<") constraint ("<=" | "<") cost
        source.pos = saved_pos

        # Minimum cost.
        cost_pos = source.pos
        min_cost = parse_cost_limit(source)

        min_inc = parse_fuzzy_compare(source)
        if min_inc is None:
            raise ParseError()

        constraint = parse_constraint(source, constraints, source.get())

        max_inc = parse_fuzzy_compare(source)
        if max_inc is None:
            raise ParseError()

        # Maximum cost.
        cost_pos = source.pos
        max_cost = parse_cost_limit(source)

        # Inclusive or exclusive limits?
        if not min_inc:
            min_cost += 1
        if not max_inc:
            max_cost -= 1

        if not 0 <= min_cost <= max_cost:
            raise error("bad fuzzy cost limit", source.string, cost_pos)

        constraints[constraint] = min_cost, max_cost
    else:
        raise ParseError()

def parse_cost_limit(source):
    "Parses a cost limit."
    cost_pos = source.pos
    digits = parse_count(source)

    try:
        return int(digits)
    except ValueError:
        pass

    raise error("bad fuzzy cost limit", source.string, cost_pos)

def parse_constraint(source, constraints, ch):
    "Parses a constraint."
    if ch not in "deis":
        raise ParseError()

    if ch in constraints:
        raise ParseError()

    return ch

def parse_fuzzy_compare(source):
    "Parses a cost comparator."
    if source.match("<="):
        return True
    elif source.match("<"):
        return False
    else:
        return None

def parse_cost_equation(source, constraints):
    "Parses a cost equation."
    if "cost" in constraints:
        raise error("more than one cost equation", source.string, source.pos)

    cost = {}

    parse_cost_term(source, cost)
    while source.match("+"):
        parse_cost_term(source, cost)

    max_inc = parse_fuzzy_compare(source)
    if max_inc is None:
        raise ParseError()

    max_cost = int(parse_count(source))

    if not max_inc:
        max_cost -= 1

    if max_cost < 0:
        raise error("bad fuzzy cost limit", source.string, source.pos)

    cost["max"] = max_cost

    constraints["cost"] = cost

def parse_cost_term(source, cost):
    "Parses a cost equation term."
    coeff = parse_count(source)
    ch = source.get()
    if ch not in "dis":
        raise ParseError()

    if ch in cost:
        raise error("repeated fuzzy cost", source.string, source.pos)

    cost[ch] = int(coeff or 1)

def parse_fuzzy_test(source, info, case_flags):
    saved_pos = source.pos
    ch = source.get()
    if ch in SPECIAL_CHARS:
        if ch == "\\":
            # An escape sequence outside a set.
            return parse_escape(source, info, False)
        elif ch == ".":
            # Any character.
            if info.flags & DOTALL:
                return AnyAll()
            elif info.flags & WORD:
                return AnyU()
            else:
                return Any()
        elif ch == "[":
            # A character set.
            return parse_set(source, info)
        else:
            raise error("expected character set", source.string, saved_pos)
    elif ch:
        # A literal.
        return Character(ord(ch), case_flags=case_flags)
    else:
        raise error("expected character set", source.string, saved_pos)

def parse_count(source):
    "Parses a quantifier's count, which can be empty."
    return source.get_while(DIGITS)

def parse_paren(source, info):
    """Parses a parenthesised subpattern or a flag. Returns FLAGS if it's an
    inline flag.
    """
    saved_pos = source.pos
    ch = source.get(True)
    if ch == "?":
        # (?...
        saved_pos_2 = source.pos
        ch = source.get(True)
        if ch == "<":
            # (?<...
            saved_pos_3 = source.pos
            ch = source.get()
            if ch in ("=", "!"):
                # (?<=... or (?<!...: lookbehind.
                return parse_lookaround(source, info, True, ch == "=")

            # (?<...: a named capture group.
            source.pos = saved_pos_3
            name = parse_name(source)
            group = info.open_group(name)
            source.expect(">")
            saved_flags = info.flags
            try:
                subpattern = _parse_pattern(source, info)
                source.expect(")")
            finally:
                info.flags = saved_flags
                source.ignore_space = bool(info.flags & VERBOSE)

            info.close_group()
            return Group(info, group, subpattern)
        if ch in ("=", "!"):
            # (?=... or (?!...: lookahead.
            return parse_lookaround(source, info, False, ch == "=")
        if ch == "P":
            # (?P...: a Python extension.
            return parse_extension(source, info)
        if ch == "#":
            # (?#...: a comment.
            return parse_comment(source)
        if ch == "(":
            # (?(...: a conditional subpattern.
            return parse_conditional(source, info)
        if ch == ">":
            # (?>...: an atomic subpattern.
            return parse_atomic(source, info)
        if ch == "|":
            # (?|...: a common/reset groups branch.
            return parse_common(source, info)
        if ch == "R" or "0" <= ch <= "9":
            # (?R...: probably a call to a group.
            return parse_call_group(source, info, ch, saved_pos_2)
        if ch == "&":
            # (?&...: a call to a named group.
            return parse_call_named_group(source, info, saved_pos_2)

        # (?...: probably a flags subpattern.
        source.pos = saved_pos_2
        return parse_flags_subpattern(source, info)

    if ch == "*":
        # (*...
        saved_pos_2 = source.pos
        word = source.get_while(set(")>"), include=False)
        if word[ : 1].isalpha():
            verb = VERBS.get(word)
            if not verb:
                raise error("unknown verb", source.string, saved_pos_2)

            source.expect(")")

            return verb

    # (...: an unnamed capture group.
    source.pos = saved_pos
    group = info.open_group()
    saved_flags = info.flags
    try:
        subpattern = _parse_pattern(source, info)
        source.expect(")")
    finally:
        info.flags = saved_flags
        source.ignore_space = bool(info.flags & VERBOSE)

    info.close_group()

    return Group(info, group, subpattern)

def parse_extension(source, info):
    "Parses a Python extension."
    saved_pos = source.pos
    ch = source.get()
    if ch == "<":
        # (?P<...: a named capture group.
        name = parse_name(source)
        group = info.open_group(name)
        source.expect(">")
        saved_flags = info.flags
        try:
            subpattern = _parse_pattern(source, info)
            source.expect(")")
        finally:
            info.flags = saved_flags
            source.ignore_space = bool(info.flags & VERBOSE)

        info.close_group()

        return Group(info, group, subpattern)
    if ch == "=":
        # (?P=...: a named group reference.
        name = parse_name(source, allow_numeric=True)
        source.expect(")")
        if info.is_open_group(name):
            raise error("cannot refer to an open group", source.string,
              saved_pos)

        return make_ref_group(info, name, saved_pos)
    if ch == ">" or ch == "&":
        # (?P>...: a call to a group.
        return parse_call_named_group(source, info, saved_pos)

    source.pos = saved_pos
    raise error("unknown extension", source.string, saved_pos)

def parse_comment(source):
    "Parses a comment."
    while True:
        saved_pos = source.pos
        c = source.get(True)

        if not c or c == ")":
            break

        if c == "\\":
            c = source.get(True)

    source.pos = saved_pos
    source.expect(")")

    return None

def parse_lookaround(source, info, behind, positive):
    "Parses a lookaround."
    saved_flags = info.flags
    try:
        subpattern = _parse_pattern(source, info)
        source.expect(")")
    finally:
        info.flags = saved_flags
        source.ignore_space = bool(info.flags & VERBOSE)

    return LookAround(behind, positive, subpattern)

def parse_conditional(source, info):
    "Parses a conditional subpattern."
    saved_flags = info.flags
    saved_pos = source.pos
    ch = source.get()
    if ch == "?":
        # (?(?...
        ch = source.get()
        if ch in ("=", "!"):
            # (?(?=... or (?(?!...: lookahead conditional.
            return parse_lookaround_conditional(source, info, False, ch == "=")
        if ch == "<":
            # (?(?<...
            ch = source.get()
            if ch in ("=", "!"):
                # (?(?<=... or (?(?<!...: lookbehind conditional.
                return parse_lookaround_conditional(source, info, True, ch ==
                  "=")

        source.pos = saved_pos
        raise error("expected lookaround conditional", source.string,
          source.pos)

    source.pos = saved_pos
    try:
        group = parse_name(source, True)
        source.expect(")")
        yes_branch = parse_sequence(source, info)
        if source.match("|"):
            no_branch = parse_sequence(source, info)
        else:
            no_branch = Sequence()

        source.expect(")")
    finally:
        info.flags = saved_flags
        source.ignore_space = bool(info.flags & VERBOSE)

    if yes_branch.is_empty() and no_branch.is_empty():
        return Sequence()

    return Conditional(info, group, yes_branch, no_branch, saved_pos)

def parse_lookaround_conditional(source, info, behind, positive):
    saved_flags = info.flags
    try:
        subpattern = _parse_pattern(source, info)
        source.expect(")")
    finally:
        info.flags = saved_flags
        source.ignore_space = bool(info.flags & VERBOSE)

    yes_branch = parse_sequence(source, info)
    if source.match("|"):
        no_branch = parse_sequence(source, info)
    else:
        no_branch = Sequence()

    source.expect(")")

    return LookAroundConditional(behind, positive, subpattern, yes_branch,
      no_branch)

def parse_atomic(source, info):
    "Parses an atomic subpattern."
    saved_flags = info.flags
    try:
        subpattern = _parse_pattern(source, info)
        source.expect(")")
    finally:
        info.flags = saved_flags
        source.ignore_space = bool(info.flags & VERBOSE)

    return Atomic(subpattern)

def parse_common(source, info):
    "Parses a common groups branch."
    # Capture group numbers in different branches can reuse the group numbers.
    initial_group_count = info.group_count
    branches = [parse_sequence(source, info)]
    final_group_count = info.group_count
    while source.match("|"):
        info.group_count = initial_group_count
        branches.append(parse_sequence(source, info))
        final_group_count = max(final_group_count, info.group_count)

    info.group_count = final_group_count
    source.expect(")")

    if len(branches) == 1:
        return branches[0]
    return Branch(branches)

def parse_call_group(source, info, ch, pos):
    "Parses a call to a group."
    if ch == "R":
        group = "0"
    else:
        group = ch + source.get_while(DIGITS)

    source.expect(")")

    return CallGroup(info, group, pos)

def parse_call_named_group(source, info, pos):
    "Parses a call to a named group."
    group = parse_name(source)
    source.expect(")")

    return CallGroup(info, group, pos)

def parse_flag_set(source):
    "Parses a set of inline flags."
    flags = 0

    try:
        while True:
            saved_pos = source.pos
            ch = source.get()
            if ch == "V":
                ch += source.get()
            flags |= REGEX_FLAGS[ch]
    except KeyError:
        source.pos = saved_pos

    return flags

def parse_flags(source, info):
    "Parses flags being turned on/off."
    flags_on = parse_flag_set(source)
    if source.match("-"):
        flags_off = parse_flag_set(source)
        if not flags_off:
            raise error("bad inline flags: no flags after '-'", source.string,
              source.pos)
    else:
        flags_off = 0

    if flags_on & LOCALE:
        # Remember that this pattern as an inline locale flag.
        info.inline_locale = True

    return flags_on, flags_off

def parse_subpattern(source, info, flags_on, flags_off):
    "Parses a subpattern with scoped flags."
    saved_flags = info.flags
    info.flags = (info.flags | flags_on) & ~flags_off
    source.ignore_space = bool(info.flags & VERBOSE)
    try:
        subpattern = _parse_pattern(source, info)
        source.expect(")")
    finally:
        info.flags = saved_flags
        source.ignore_space = bool(info.flags & VERBOSE)

    return subpattern

def parse_flags_subpattern(source, info):
    """Parses a flags subpattern. It could be inline flags or a subpattern
    possibly with local flags. If it's a subpattern, then that's returned;
    if it's a inline flags, then None is returned.
    """
    flags_on, flags_off = parse_flags(source, info)

    if flags_off & GLOBAL_FLAGS:
        raise error("bad inline flags: cannot turn off global flag",
          source.string, source.pos)

    if flags_on & flags_off:
        raise error("bad inline flags: flag turned on and off", source.string,
          source.pos)

    # Handle flags which are global in all regex behaviours.
    new_global_flags = (flags_on & ~info.global_flags) & GLOBAL_FLAGS
    if new_global_flags:
        info.global_flags |= new_global_flags

        # A global has been turned on, so reparse the pattern.
        raise _UnscopedFlagSet(info.global_flags)

    # Ensure that from now on we have only scoped flags.
    flags_on &= ~GLOBAL_FLAGS

    if source.match(":"):
        return parse_subpattern(source, info, flags_on, flags_off)

    if source.match(")"):
        parse_positional_flags(source, info, flags_on, flags_off)
        return None

    raise error("unknown extension", source.string, source.pos)

def parse_positional_flags(source, info, flags_on, flags_off):
    "Parses positional flags."
    info.flags = (info.flags | flags_on) & ~flags_off
    source.ignore_space = bool(info.flags & VERBOSE)

def parse_name(source, allow_numeric=False, allow_group_0=False):
    "Parses a name."
    name = source.get_while(set(")>"), include=False)

    if not name:
        raise error("missing group name", source.string, source.pos)

    if name.isdigit():
        min_group = 0 if allow_group_0 else 1
        if not allow_numeric or int(name) < min_group:
            raise error("bad character in group name", source.string,
              source.pos)
    else:
        if not name.isidentifier():
            raise error("bad character in group name", source.string,
              source.pos)

    return name

def is_octal(string):
    "Checks whether a string is octal."
    return all(ch in OCT_DIGITS for ch in string)

def is_decimal(string):
    "Checks whether a string is decimal."
    return all(ch in DIGITS for ch in string)

def is_hexadecimal(string):
    "Checks whether a string is hexadecimal."
    return all(ch in HEX_DIGITS for ch in string)

def parse_escape(source, info, in_set):
    "Parses an escape sequence."
    saved_ignore = source.ignore_space
    source.ignore_space = False
    ch = source.get()
    source.ignore_space = saved_ignore
    if not ch:
        # A backslash at the end of the pattern.
        raise error("bad escape (end of pattern)", source.string, source.pos)
    if ch in HEX_ESCAPES:
        # A hexadecimal escape sequence.
        return parse_hex_escape(source, info, ch, HEX_ESCAPES[ch], in_set, ch)
    elif ch == "g" and not in_set:
        # A group reference.
        saved_pos = source.pos
        try:
            return parse_group_ref(source, info)
        except error:
            # Invalid as a group reference, so assume it's a literal.
            source.pos = saved_pos

        return make_character(info, ord(ch), in_set)
    elif ch == "G" and not in_set:
        # A search anchor.
        return SearchAnchor()
    elif ch == "L" and not in_set:
        # A string set.
        return parse_string_set(source, info)
    elif ch == "N":
        # A named codepoint.
        return parse_named_char(source, info, in_set)
    elif ch in "pP":
        # A Unicode property, positive or negative.
        return parse_property(source, info, ch == "p", in_set)
    elif ch == "R" and not in_set:
        # A line ending.
        charset = [0x0A, 0x0B, 0x0C, 0x0D]
        if info.guess_encoding == UNICODE:
            charset.extend([0x85, 0x2028, 0x2029])

        return Atomic(Branch([String([0x0D, 0x0A]), SetUnion(info, [Character(c)
          for c in charset])]))
    elif ch == "X" and not in_set:
        # A grapheme cluster.
        return Grapheme()
    elif ch in ALPHA:
        # An alphabetic escape sequence.
        # Positional escapes aren't allowed inside a character set.
        if not in_set:
            if info.flags & WORD:
                value = WORD_POSITION_ESCAPES.get(ch)
            else:
                value = POSITION_ESCAPES.get(ch)

            if value:
                return value

        value = CHARSET_ESCAPES.get(ch)
        if value:
            return value

        value = CHARACTER_ESCAPES.get(ch)
        if value:
            return Character(ord(value))

        raise error("bad escape \\%s" % ch, source.string, source.pos)
    elif ch in DIGITS:
        # A numeric escape sequence.
        return parse_numeric_escape(source, info, ch, in_set)
    else:
        # A literal.
        return make_character(info, ord(ch), in_set)

def parse_numeric_escape(source, info, ch, in_set):
    "Parses a numeric escape sequence."
    if in_set or ch == "0":
        # Octal escape sequence, max 3 digits.
        return parse_octal_escape(source, info, [ch], in_set)

    # At least 1 digit, so either octal escape or group.
    digits = ch
    saved_pos = source.pos
    ch = source.get()
    if ch in DIGITS:
        # At least 2 digits, so either octal escape or group.
        digits += ch
        saved_pos = source.pos
        ch = source.get()
        if is_octal(digits) and ch in OCT_DIGITS:
            # 3 octal digits, so octal escape sequence.
            encoding = info.flags & _ALL_ENCODINGS
            if encoding == ASCII or encoding == LOCALE:
                octal_mask = 0xFF
            else:
                octal_mask = 0x1FF

            value = int(digits + ch, 8) & octal_mask
            return make_character(info, value)

    # Group reference.
    source.pos = saved_pos
    if info.is_open_group(digits):
        raise error("cannot refer to an open group", source.string, source.pos)

    return make_ref_group(info, digits, source.pos)

def parse_octal_escape(source, info, digits, in_set):
    "Parses an octal escape sequence."
    saved_pos = source.pos
    ch = source.get()
    while len(digits) < 3 and ch in OCT_DIGITS:
        digits.append(ch)
        saved_pos = source.pos
        ch = source.get()

    source.pos = saved_pos
    try:
        value = int("".join(digits), 8)
        return make_character(info, value, in_set)
    except ValueError:
        if digits[0] in OCT_DIGITS:
            raise error("incomplete escape \\%s" % ''.join(digits),
              source.string, source.pos)
        else:
            raise error("bad escape \\%s" % digits[0], source.string,
              source.pos)

def parse_hex_escape(source, info, esc, expected_len, in_set, type):
    "Parses a hex escape sequence."
    saved_pos = source.pos
    digits = []
    for i in range(expected_len):
        ch = source.get()
        if ch not in HEX_DIGITS:
            raise error("incomplete escape \\%s%s" % (type, ''.join(digits)),
              source.string, saved_pos)
        digits.append(ch)

    try:
        value = int("".join(digits), 16)
    except ValueError:
        pass
    else:
        if value < 0x110000:
            return make_character(info, value, in_set)

    # Bad hex escape.
    raise error("bad hex escape \\%s%s" % (esc, ''.join(digits)),
      source.string, saved_pos)

def parse_group_ref(source, info):
    "Parses a group reference."
    source.expect("<")
    saved_pos = source.pos
    name = parse_name(source, True)
    source.expect(">")
    if info.is_open_group(name):
        raise error("cannot refer to an open group", source.string, source.pos)

    return make_ref_group(info, name, saved_pos)

def parse_string_set(source, info):
    "Parses a string set reference."
    source.expect("<")
    name = parse_name(source, True)
    source.expect(">")
    if name is None or name not in info.kwargs:
        raise error("undefined named list", source.string, source.pos)

    return make_string_set(info, name)

def parse_named_char(source, info, in_set):
    "Parses a named character."
    saved_pos = source.pos
    if source.match("{"):
        name = source.get_while(NAMED_CHAR_PART, keep_spaces=True)
        if source.match("}"):
            try:
                value = unicodedata.lookup(name)
                return make_character(info, ord(value), in_set)
            except KeyError:
                raise error("undefined character name", source.string,
                  source.pos)

    source.pos = saved_pos
    return make_character(info, ord("N"), in_set)

def parse_property(source, info, positive, in_set):
    "Parses a Unicode property."
    saved_pos = source.pos
    ch = source.get()
    if ch == "{":
        negate = source.match("^")
        prop_name, name = parse_property_name(source)
        if source.match("}"):
            # It's correctly delimited.
            prop = lookup_property(prop_name, name, positive != negate, source)
            return make_property(info, prop, in_set)
    elif ch and ch in "CLMNPSZ":
        # An abbreviated property, eg \pL.
        prop = lookup_property(None, ch, positive, source)
        return make_property(info, prop, in_set)

    # Not a property, so treat as a literal "p" or "P".
    source.pos = saved_pos
    ch = "p" if positive else "P"
    return make_character(info, ord(ch), in_set)

def parse_property_name(source):
    "Parses a property name, which may be qualified."
    name = source.get_while(PROPERTY_NAME_PART)
    saved_pos = source.pos

    ch = source.get()
    if ch and ch in ":=":
        prop_name = name
        name = source.get_while(ALNUM | set(" &_-./")).strip()

        if name:
            # Name after the ":" or "=", so it's a qualified name.
            saved_pos = source.pos
        else:
            # No name after the ":" or "=", so assume it's an unqualified name.
            prop_name, name = None, prop_name
    else:
        prop_name = None

    source.pos = saved_pos
    return prop_name, name

def parse_set(source, info):
    "Parses a character set."
    version = (info.flags & _ALL_VERSIONS) or DEFAULT_VERSION

    saved_ignore = source.ignore_space
    source.ignore_space = False
    # Negative set?
    negate = source.match("^")
    try:
        if version == VERSION0:
            item = parse_set_imp_union(source, info)
        else:
            item = parse_set_union(source, info)

        if not source.match("]"):
            raise error("missing ]", source.string, source.pos)
    finally:
        source.ignore_space = saved_ignore

    if negate:
        item = item.with_flags(positive=not item.positive)

    item = item.with_flags(case_flags=make_case_flags(info))

    return item

def parse_set_union(source, info):
    "Parses a set union ([x||y])."
    items = [parse_set_symm_diff(source, info)]
    while source.match("||"):
        items.append(parse_set_symm_diff(source, info))

    if len(items) == 1:
        return items[0]
    return SetUnion(info, items)

def parse_set_symm_diff(source, info):
    "Parses a set symmetric difference ([x~~y])."
    items = [parse_set_inter(source, info)]
    while source.match("~~"):
        items.append(parse_set_inter(source, info))

    if len(items) == 1:
        return items[0]
    return SetSymDiff(info, items)

def parse_set_inter(source, info):
    "Parses a set intersection ([x&&y])."
    items = [parse_set_diff(source, info)]
    while source.match("&&"):
        items.append(parse_set_diff(source, info))

    if len(items) == 1:
        return items[0]
    return SetInter(info, items)

def parse_set_diff(source, info):
    "Parses a set difference ([x--y])."
    items = [parse_set_imp_union(source, info)]
    while source.match("--"):
        items.append(parse_set_imp_union(source, info))

    if len(items) == 1:
        return items[0]
    return SetDiff(info, items)

def parse_set_imp_union(source, info):
    "Parses a set implicit union ([xy])."
    version = (info.flags & _ALL_VERSIONS) or DEFAULT_VERSION

    items = [parse_set_member(source, info)]
    while True:
        saved_pos = source.pos
        if source.match("]"):
            # End of the set.
            source.pos = saved_pos
            break

        if version == VERSION1 and any(source.match(op) for op in SET_OPS):
            # The new behaviour has set operators.
            source.pos = saved_pos
            break

        items.append(parse_set_member(source, info))

    if len(items) == 1:
        return items[0]
    return SetUnion(info, items)

def parse_set_member(source, info):
    "Parses a member in a character set."
    # Parse a set item.
    start = parse_set_item(source, info)
    saved_pos1 = source.pos
    if (not isinstance(start, Character) or not start.positive or not
      source.match("-")):
        # It's not the start of a range.
        return start

    version = (info.flags & _ALL_VERSIONS) or DEFAULT_VERSION

    # It looks like the start of a range of characters.
    saved_pos2 = source.pos
    if version == VERSION1 and source.match("-"):
        # It's actually the set difference operator '--', so return the
        # character.
        source.pos = saved_pos1
        return start

    if source.match("]"):
        # We've reached the end of the set, so return both the character and
        # hyphen.
        source.pos = saved_pos2
        return SetUnion(info, [start, Character(ord("-"))])

    # Parse a set item.
    end = parse_set_item(source, info)
    if not isinstance(end, Character) or not end.positive:
        # It's not a range, so return the character, hyphen and property.
        return SetUnion(info, [start, Character(ord("-")), end])

    # It _is_ a range.
    if start.value > end.value:
        raise error("bad character range", source.string, source.pos)

    if start.value == end.value:
        return start

    return Range(start.value, end.value)

def parse_set_item(source, info):
    "Parses an item in a character set."
    version = (info.flags & _ALL_VERSIONS) or DEFAULT_VERSION

    if source.match("\\"):
        # An escape sequence in a set.
        return parse_escape(source, info, True)

    saved_pos = source.pos
    if source.match("[:"):
        # Looks like a POSIX character class.
        try:
            return parse_posix_class(source, info)
        except ParseError:
            # Not a POSIX character class.
            source.pos = saved_pos

    if version == VERSION1 and source.match("["):
        # It's the start of a nested set.

        # Negative set?
        negate = source.match("^")
        item = parse_set_union(source, info)

        if not source.match("]"):
            raise error("missing ]", source.string, source.pos)

        if negate:
            item = item.with_flags(positive=not item.positive)

        return item

    ch = source.get()
    if not ch:
        raise error("unterminated character set", source.string, source.pos)

    return Character(ord(ch))

def parse_posix_class(source, info):
    "Parses a POSIX character class."
    negate = source.match("^")
    prop_name, name = parse_property_name(source)
    if not source.match(":]"):
        raise ParseError()

    return lookup_property(prop_name, name, not negate, source, posix=True)

def float_to_rational(flt):
    "Converts a float to a rational pair."
    int_part = int(flt)
    error = flt - int_part
    if abs(error) < 0.0001:
        return int_part, 1

    den, num = float_to_rational(1.0 / error)

    return int_part * den + num, den

def numeric_to_rational(numeric):
    "Converts a numeric string to a rational string, if possible."
    if numeric[ : 1] == "-":
        sign, numeric = numeric[0], numeric[1 : ]
    else:
        sign = ""

    parts = numeric.split("/")
    if len(parts) == 2:
        num, den = float_to_rational(float(parts[0]) / float(parts[1]))
    elif len(parts) == 1:
        num, den = float_to_rational(float(parts[0]))
    else:
        raise ValueError()

    result = "{}{}/{}".format(sign, num, den)
    if result.endswith("/1"):
        return result[ : -2]

    return result

def standardise_name(name):
    "Standardises a property or value name."
    try:
        return numeric_to_rational("".join(name))
    except (ValueError, ZeroDivisionError):
        return "".join(ch for ch in name if ch not in "_- ").upper()

_POSIX_CLASSES = set('ALNUM DIGIT PUNCT XDIGIT'.split())

_BINARY_VALUES = set('YES Y NO N TRUE T FALSE F'.split())

def lookup_property(property, value, positive, source=None, posix=False):
    "Looks up a property."
    # Normalise the names (which may still be lists).
    property = standardise_name(property) if property else None
    value = standardise_name(value)

    if (property, value) == ("GENERALCATEGORY", "ASSIGNED"):
        property, value, positive = "GENERALCATEGORY", "UNASSIGNED", not positive

    if posix and not property and value.upper() in _POSIX_CLASSES:
        value = 'POSIX' + value

    if property:
        # Both the property and the value are provided.
        prop = PROPERTIES.get(property)
        if not prop:
            if not source:
                raise error("unknown property")

            raise error("unknown property", source.string, source.pos)

        prop_id, value_dict = prop
        val_id = value_dict.get(value)
        if val_id is None:
            if not source:
                raise error("unknown property value")

            raise error("unknown property value", source.string, source.pos)

        return Property((prop_id << 16) | val_id, positive)

    # Only the value is provided.
    # It might be the name of a GC, script or block value.
    for property in ("GC", "SCRIPT", "BLOCK"):
        prop_id, value_dict = PROPERTIES.get(property)
        val_id = value_dict.get(value)
        if val_id is not None:
            return Property((prop_id << 16) | val_id, positive)

    # It might be the name of a binary property.
    prop = PROPERTIES.get(value)
    if prop:
        prop_id, value_dict = prop
        if set(value_dict) == _BINARY_VALUES:
            return Property((prop_id << 16) | 1, positive)

        return Property(prop_id << 16, not positive)

    # It might be the name of a binary property starting with a prefix.
    if value.startswith("IS"):
        prop = PROPERTIES.get(value[2 : ])
        if prop:
            prop_id, value_dict = prop
            if "YES" in value_dict:
                return Property((prop_id << 16) | 1, positive)

    # It might be the name of a script or block starting with a prefix.
    for prefix, property in (("IS", "SCRIPT"), ("IN", "BLOCK")):
        if value.startswith(prefix):
            prop_id, value_dict = PROPERTIES.get(property)
            val_id = value_dict.get(value[2 : ])
            if val_id is not None:
                return Property((prop_id << 16) | val_id, positive)

    # Unknown property.
    if not source:
        raise error("unknown property")

    raise error("unknown property", source.string, source.pos)

def _compile_replacement(source, pattern, is_unicode):
    "Compiles a replacement template escape sequence."
    ch = source.get()
    if ch in ALPHA:
        # An alphabetic escape sequence.
        value = CHARACTER_ESCAPES.get(ch)
        if value:
            return False, [ord(value)]

        if ch in HEX_ESCAPES and (ch == "x" or is_unicode):
            # A hexadecimal escape sequence.
            return False, [parse_repl_hex_escape(source, HEX_ESCAPES[ch], ch)]

        if ch == "g":
            # A group preference.
            return True, [compile_repl_group(source, pattern)]

        if ch == "N" and is_unicode:
            # A named character.
            value = parse_repl_named_char(source)
            if value is not None:
                return False, [value]

        raise error("bad escape \\%s" % ch, source.string, source.pos)

    if isinstance(source.sep, bytes):
        octal_mask = 0xFF
    else:
        octal_mask = 0x1FF

    if ch == "0":
        # An octal escape sequence.
        digits = ch
        while len(digits) < 3:
            saved_pos = source.pos
            ch = source.get()
            if ch not in OCT_DIGITS:
                source.pos = saved_pos
                break
            digits += ch

        return False, [int(digits, 8) & octal_mask]

    if ch in DIGITS:
        # Either an octal escape sequence (3 digits) or a group reference (max
        # 2 digits).
        digits = ch
        saved_pos = source.pos
        ch = source.get()
        if ch in DIGITS:
            digits += ch
            saved_pos = source.pos
            ch = source.get()
            if ch and is_octal(digits + ch):
                # An octal escape sequence.
                return False, [int(digits + ch, 8) & octal_mask]

        # A group reference.
        source.pos = saved_pos
        return True, [int(digits)]

    if ch == "\\":
        # An escaped backslash is a backslash.
        return False, [ord("\\")]

    if not ch:
        # A trailing backslash.
        raise error("bad escape (end of pattern)", source.string, source.pos)

    # An escaped non-backslash is a backslash followed by the literal.
    return False, [ord("\\"), ord(ch)]

def parse_repl_hex_escape(source, expected_len, type):
    "Parses a hex escape sequence in a replacement string."
    digits = []
    for i in range(expected_len):
        ch = source.get()
        if ch not in HEX_DIGITS:
            raise error("incomplete escape \\%s%s" % (type, ''.join(digits)),
              source.string, source.pos)
        digits.append(ch)

    return int("".join(digits), 16)

def parse_repl_named_char(source):
    "Parses a named character in a replacement string."
    saved_pos = source.pos
    if source.match("{"):
        name = source.get_while(ALPHA | set(" "))

        if source.match("}"):
            try:
                value = unicodedata.lookup(name)
                return ord(value)
            except KeyError:
                raise error("undefined character name", source.string,
                  source.pos)

    source.pos = saved_pos
    return None

def compile_repl_group(source, pattern):
    "Compiles a replacement template group reference."
    source.expect("<")
    name = parse_name(source, True, True)

    source.expect(">")
    if name.isdigit():
        index = int(name)
        if not 0 <= index <= pattern.groups:
            raise error("invalid group reference", source.string, source.pos)

        return index

    try:
        return pattern.groupindex[name]
    except KeyError:
        raise IndexError("unknown group")

# The regular expression is parsed into a syntax tree. The different types of
# node are defined below.

INDENT = "  "
POSITIVE_OP = 0x1
ZEROWIDTH_OP = 0x2
FUZZY_OP = 0x4
REVERSE_OP = 0x8
REQUIRED_OP = 0x10

POS_TEXT = {False: "NON-MATCH", True: "MATCH"}
CASE_TEXT = {NOCASE: "", IGNORECASE: " SIMPLE_IGNORE_CASE", FULLCASE: "",
  FULLIGNORECASE: " FULL_IGNORE_CASE"}

def make_sequence(items):
    if len(items) == 1:
        return items[0]
    return Sequence(items)

# Common base class for all nodes.
class RegexBase:
    def __init__(self):
        self._key = self.__class__

    def with_flags(self, positive=None, case_flags=None, zerowidth=None):
        if positive is None:
            positive = self.positive
        else:
            positive = bool(positive)
        if case_flags is None:
            case_flags = self.case_flags
        else:
            case_flags = CASE_FLAGS_COMBINATIONS[case_flags & CASE_FLAGS]
        if zerowidth is None:
            zerowidth = self.zerowidth
        else:
            zerowidth = bool(zerowidth)

        if (positive == self.positive and case_flags == self.case_flags and
          zerowidth == self.zerowidth):
            return self

        return self.rebuild(positive, case_flags, zerowidth)

    def fix_groups(self, pattern, reverse, fuzzy):
        pass

    def optimise(self, info, reverse):
        return self

    def pack_characters(self, info):
        return self

    def remove_captures(self):
        return self

    def is_atomic(self):
        return True

    def can_be_affix(self):
        return True

    def contains_group(self):
        return False

    def get_firstset(self, reverse):
        raise _FirstSetError()

    def has_simple_start(self):
        return False

    def compile(self, reverse=False, fuzzy=False):
        return self._compile(reverse, fuzzy)

    def is_empty(self):
        return False

    def __hash__(self):
        return hash(self._key)

    def __eq__(self, other):
        return type(self) is type(other) and self._key == other._key

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_required_string(self, reverse):
        return self.max_width(), None

# Base class for zero-width nodes.
class ZeroWidthBase(RegexBase):
    def __init__(self, positive=True):
        RegexBase.__init__(self)
        self.positive = bool(positive)

        self._key = self.__class__, self.positive

    def get_firstset(self, reverse):
        return set([None])

    def _compile(self, reverse, fuzzy):
        flags = 0
        if self.positive:
            flags |= POSITIVE_OP
        if fuzzy:
            flags |= FUZZY_OP
        if reverse:
            flags |= REVERSE_OP
        return [(self._opcode, flags)]

    def dump(self, indent, reverse):
        print("{}{} {}".format(INDENT * indent, self._op_name,
          POS_TEXT[self.positive]))

    def max_width(self):
        return 0

class Any(RegexBase):
    _opcode = {False: OP.ANY, True: OP.ANY_REV}
    _op_name = "ANY"

    def has_simple_start(self):
        return True

    def _compile(self, reverse, fuzzy):
        flags = 0
        if fuzzy:
            flags |= FUZZY_OP
        return [(self._opcode[reverse], flags)]

    def dump(self, indent, reverse):
        print("{}{}".format(INDENT * indent, self._op_name))

    def max_width(self):
        return 1

class AnyAll(Any):
    _opcode = {False: OP.ANY_ALL, True: OP.ANY_ALL_REV}
    _op_name = "ANY_ALL"

class AnyU(Any):
    _opcode = {False: OP.ANY_U, True: OP.ANY_U_REV}
    _op_name = "ANY_U"

class Atomic(RegexBase):
    def __init__(self, subpattern):
        RegexBase.__init__(self)
        self.subpattern = subpattern

    def fix_groups(self, pattern, reverse, fuzzy):
        self.subpattern.fix_groups(pattern, reverse, fuzzy)

    def optimise(self, info, reverse):
        self.subpattern = self.subpattern.optimise(info, reverse)

        if self.subpattern.is_empty():
            return self.subpattern
        return self

    def pack_characters(self, info):
        self.subpattern = self.subpattern.pack_characters(info)
        return self

    def remove_captures(self):
        self.subpattern = self.subpattern.remove_captures()
        return self

    def can_be_affix(self):
        return self.subpattern.can_be_affix()

    def contains_group(self):
        return self.subpattern.contains_group()

    def get_firstset(self, reverse):
        return self.subpattern.get_firstset(reverse)

    def has_simple_start(self):
        return self.subpattern.has_simple_start()

    def _compile(self, reverse, fuzzy):
        return ([(OP.ATOMIC, )] + self.subpattern.compile(reverse, fuzzy) +
          [(OP.END, )])

    def dump(self, indent, reverse):
        print("{}ATOMIC".format(INDENT * indent))
        self.subpattern.dump(indent + 1, reverse)

    def is_empty(self):
        return self.subpattern.is_empty()

    def __eq__(self, other):
        return (type(self) is type(other) and self.subpattern ==
          other.subpattern)

    def max_width(self):
        return self.subpattern.max_width()

    def get_required_string(self, reverse):
        return self.subpattern.get_required_string(reverse)

class Boundary(ZeroWidthBase):
    _opcode = OP.BOUNDARY
    _op_name = "BOUNDARY"

class Branch(RegexBase):
    def __init__(self, branches):
        RegexBase.__init__(self)
        self.branches = branches

    def fix_groups(self, pattern, reverse, fuzzy):
        for b in self.branches:
            b.fix_groups(pattern, reverse, fuzzy)

    def optimise(self, info, reverse):
        if not self.branches:
            return Sequence([])

        # Flatten branches within branches.
        branches = Branch._flatten_branches(info, reverse, self.branches)

        # Move any common prefix or suffix out of the branches.
        if reverse:
            suffix, branches = Branch._split_common_suffix(info, branches)
            prefix = []
        else:
            prefix, branches = Branch._split_common_prefix(info, branches)
            suffix = []

        # Try to reduce adjacent single-character branches to sets.
        branches = Branch._reduce_to_set(info, reverse, branches)

        if len(branches) > 1:
            sequence = [Branch(branches)]

            if not prefix or not suffix:
                # We might be able to add a quick precheck before the branches.
                firstset = self._add_precheck(info, reverse, branches)

                if firstset:
                    if reverse:
                        sequence.append(firstset)
                    else:
                        sequence.insert(0, firstset)
        else:
            sequence = branches

        return make_sequence(prefix + sequence + suffix)

    def _add_precheck(self, info, reverse, branches):
        charset = set()
        pos = -1 if reverse else 0

        for branch in branches:
            if type(branch) is Literal and branch.case_flags == NOCASE:
                charset.add(branch.characters[pos])
            else:
                return

        if not charset:
            return None

        return _check_firstset(info, reverse, [Character(c) for c in charset])

    def pack_characters(self, info):
        self.branches = [b.pack_characters(info) for b in self.branches]
        return self

    def remove_captures(self):
        self.branches = [b.remove_captures() for b in self.branches]
        return self

    def is_atomic(self):
        return all(b.is_atomic() for b in self.branches)

    def can_be_affix(self):
        return all(b.can_be_affix() for b in self.branches)

    def contains_group(self):
        return any(b.contains_group() for b in self.branches)

    def get_firstset(self, reverse):
        fs = set()
        for b in self.branches:
            fs |= b.get_firstset(reverse)

        return fs or set([None])

    def _compile(self, reverse, fuzzy):
        if not self.branches:
            return []

        code = [(OP.BRANCH, )]
        for b in self.branches:
            code.extend(b.compile(reverse, fuzzy))
            code.append((OP.NEXT, ))

        code[-1] = (OP.END, )

        return code

    def dump(self, indent, reverse):
        print("{}BRANCH".format(INDENT * indent))
        self.branches[0].dump(indent + 1, reverse)
        for b in self.branches[1 : ]:
            print("{}OR".format(INDENT * indent))
            b.dump(indent + 1, reverse)

    @staticmethod
    def _flatten_branches(info, reverse, branches):
        # Flatten the branches so that there aren't branches of branches.
        new_branches = []
        for b in branches:
            b = b.optimise(info, reverse)
            if isinstance(b, Branch):
                new_branches.extend(b.branches)
            else:
                new_branches.append(b)

        return new_branches

    @staticmethod
    def _split_common_prefix(info, branches):
        # Common leading items can be moved out of the branches.
        # Get the items in the branches.
        alternatives = []
        for b in branches:
            if isinstance(b, Sequence):
                alternatives.append(b.items)
            else:
                alternatives.append([b])

        # What is the maximum possible length of the prefix?
        max_count = min(len(a) for a in alternatives)

        # What is the longest common prefix?
        prefix = alternatives[0]
        pos = 0
        end_pos = max_count
        while pos < end_pos and prefix[pos].can_be_affix() and all(a[pos] ==
          prefix[pos] for a in alternatives):
            pos += 1
        count = pos

        if info.flags & UNICODE:
            # We need to check that we're not splitting a sequence of
            # characters which could form part of full case-folding.
            count = pos
            while count > 0 and not all(Branch._can_split(a, count) for a in
              alternatives):
                count -= 1

        # No common prefix is possible.
        if count == 0:
            return [], branches

        # Rebuild the branches.
        new_branches = []
        for a in alternatives:
            new_branches.append(make_sequence(a[count : ]))

        return prefix[ : count], new_branches

    @staticmethod
    def _split_common_suffix(info, branches):
        # Common trailing items can be moved out of the branches.
        # Get the items in the branches.
        alternatives = []
        for b in branches:
            if isinstance(b, Sequence):
                alternatives.append(b.items)
            else:
                alternatives.append([b])

        # What is the maximum possible length of the suffix?
        max_count = min(len(a) for a in alternatives)

        # What is the longest common suffix?
        suffix = alternatives[0]
        pos = -1
        end_pos = -1 - max_count
        while pos > end_pos and suffix[pos].can_be_affix() and all(a[pos] ==
          suffix[pos] for a in alternatives):
            pos -= 1
        count = -1 - pos

        if info.flags & UNICODE:
            # We need to check that we're not splitting a sequence of
            # characters which could form part of full case-folding.
            while count > 0 and not all(Branch._can_split_rev(a, count) for a
              in alternatives):
                count -= 1

        # No common suffix is possible.
        if count == 0:
            return [], branches

        # Rebuild the branches.
        new_branches = []
        for a in alternatives:
            new_branches.append(make_sequence(a[ : -count]))

        return suffix[-count : ], new_branches

    @staticmethod
    def _can_split(items, count):
        # Check the characters either side of the proposed split.
        if not Branch._is_full_case(items, count - 1):
            return True

        if not Branch._is_full_case(items, count):
            return True

        # Check whether a 1-1 split would be OK.
        if Branch._is_folded(items[count - 1 : count + 1]):
            return False

        # Check whether a 1-2 split would be OK.
        if (Branch._is_full_case(items, count + 2) and
          Branch._is_folded(items[count - 1 : count + 2])):
            return False

        # Check whether a 2-1 split would be OK.
        if (Branch._is_full_case(items, count - 2) and
          Branch._is_folded(items[count - 2 : count + 1])):
            return False

        return True

    @staticmethod
    def _can_split_rev(items, count):
        end = len(items)

        # Check the characters either side of the proposed split.
        if not Branch._is_full_case(items, end - count):
            return True

        if not Branch._is_full_case(items, end - count - 1):
            return True

        # Check whether a 1-1 split would be OK.
        if Branch._is_folded(items[end - count - 1 : end - count + 1]):
            return False

        # Check whether a 1-2 split would be OK.
        if (Branch._is_full_case(items, end - count + 2) and
          Branch._is_folded(items[end - count - 1 : end - count + 2])):
            return False

        # Check whether a 2-1 split would be OK.
        if (Branch._is_full_case(items, end - count - 2) and
          Branch._is_folded(items[end - count - 2 : end - count + 1])):
            return False

        return True

    @staticmethod
    def _merge_common_prefixes(info, reverse, branches):
        # Branches with the same case-sensitive character prefix can be grouped
        # together if they are separated only by other branches with a
        # character prefix.
        prefixed = defaultdict(list)
        order = {}
        new_branches = []
        for b in branches:
            if Branch._is_simple_character(b):
                # Branch starts with a simple character.
                prefixed[b.value].append([b])
                order.setdefault(b.value, len(order))
            elif (isinstance(b, Sequence) and b.items and
              Branch._is_simple_character(b.items[0])):
                # Branch starts with a simple character.
                prefixed[b.items[0].value].append(b.items)
                order.setdefault(b.items[0].value, len(order))
            else:
                Branch._flush_char_prefix(info, reverse, prefixed, order,
                  new_branches)

                new_branches.append(b)

        Branch._flush_char_prefix(info, prefixed, order, new_branches)

        return new_branches

    @staticmethod
    def _is_simple_character(c):
        return isinstance(c, Character) and c.positive and not c.case_flags

    @staticmethod
    def _reduce_to_set(info, reverse, branches):
        # Can the branches be reduced to a set?
        new_branches = []
        items = set()
        case_flags = NOCASE
        for b in branches:
            if isinstance(b, (Character, Property, SetBase)):
                # Branch starts with a single character.
                if b.case_flags != case_flags:
                    # Different case sensitivity, so flush.
                    Branch._flush_set_members(info, reverse, items, case_flags,
                      new_branches)

                    case_flags = b.case_flags

                items.add(b.with_flags(case_flags=NOCASE))
            else:
                Branch._flush_set_members(info, reverse, items, case_flags,
                  new_branches)

                new_branches.append(b)

        Branch._flush_set_members(info, reverse, items, case_flags,
          new_branches)

        return new_branches

    @staticmethod
    def _flush_char_prefix(info, reverse, prefixed, order, new_branches):
        # Flush the prefixed branches.
        if not prefixed:
            return

        for value, branches in sorted(prefixed.items(), key=lambda pair:
          order[pair[0]]):
            if len(branches) == 1:
                new_branches.append(make_sequence(branches[0]))
            else:
                subbranches = []
                optional = False
                for b in branches:
                    if len(b) > 1:
                        subbranches.append(make_sequence(b[1 : ]))
                    elif not optional:
                        subbranches.append(Sequence())
                        optional = True

                sequence = Sequence([Character(value), Branch(subbranches)])
                new_branches.append(sequence.optimise(info, reverse))

        prefixed.clear()
        order.clear()

    @staticmethod
    def _flush_set_members(info, reverse, items, case_flags, new_branches):
        # Flush the set members.
        if not items:
            return

        if len(items) == 1:
            item = list(items)[0]
        else:
            item = SetUnion(info, list(items)).optimise(info, reverse)

        new_branches.append(item.with_flags(case_flags=case_flags))

        items.clear()

    @staticmethod
    def _is_full_case(items, i):
        if not 0 <= i < len(items):
            return False

        item = items[i]
        return (isinstance(item, Character) and item.positive and
          (item.case_flags & FULLIGNORECASE) == FULLIGNORECASE)

    @staticmethod
    def _is_folded(items):
        if len(items) < 2:
            return False

        for i in items:
            if (not isinstance(i, Character) or not i.positive or not
              i.case_flags):
                return False

        folded = "".join(chr(i.value) for i in items)
        folded = _regex.fold_case(FULL_CASE_FOLDING, folded)

        # Get the characters which expand to multiple codepoints on folding.
        expanding_chars = _regex.get_expand_on_folding()

        for c in expanding_chars:
            if folded == _regex.fold_case(FULL_CASE_FOLDING, c):
                return True

        return False

    def is_empty(self):
        return all(b.is_empty() for b in self.branches)

    def __eq__(self, other):
        return type(self) is type(other) and self.branches == other.branches

    def max_width(self):
        return max(b.max_width() for b in self.branches)

class CallGroup(RegexBase):
    def __init__(self, info, group, position):
        RegexBase.__init__(self)
        self.info = info
        self.group = group
        self.position = position

        self._key = self.__class__, self.group

    def fix_groups(self, pattern, reverse, fuzzy):
        try:
            self.group = int(self.group)
        except ValueError:
            try:
                self.group = self.info.group_index[self.group]
            except KeyError:
                raise error("invalid group reference", pattern, self.position)

        if not 0 <= self.group <= self.info.group_count:
            raise error("unknown group", pattern, self.position)

        if self.group > 0 and self.info.open_group_count[self.group] > 1:
            raise error("ambiguous group reference", pattern, self.position)

        self.info.group_calls.append((self, reverse, fuzzy))

        self._key = self.__class__, self.group

    def remove_captures(self):
        raise error("group reference not allowed", pattern, self.position)

    def _compile(self, reverse, fuzzy):
        return [(OP.GROUP_CALL, self.call_ref)]

    def dump(self, indent, reverse):
        print("{}GROUP_CALL {}".format(INDENT * indent, self.group))

    def __eq__(self, other):
        return type(self) is type(other) and self.group == other.group

    def max_width(self):
        return UNLIMITED

    def __del__(self):
        self.info = None

class CallRef(RegexBase):
    def __init__(self, ref, parsed):
        self.ref = ref
        self.parsed = parsed

    def _compile(self, reverse, fuzzy):
        return ([(OP.CALL_REF, self.ref)] + self.parsed._compile(reverse,
          fuzzy) + [(OP.END, )])

class Character(RegexBase):
    _opcode = {(NOCASE, False): OP.CHARACTER, (IGNORECASE, False):
      OP.CHARACTER_IGN, (FULLCASE, False): OP.CHARACTER, (FULLIGNORECASE,
      False): OP.CHARACTER_IGN, (NOCASE, True): OP.CHARACTER_REV, (IGNORECASE,
      True): OP.CHARACTER_IGN_REV, (FULLCASE, True): OP.CHARACTER_REV,
      (FULLIGNORECASE, True): OP.CHARACTER_IGN_REV}

    def __init__(self, value, positive=True, case_flags=NOCASE,
      zerowidth=False):
        RegexBase.__init__(self)
        self.value = value
        self.positive = bool(positive)
        self.case_flags = CASE_FLAGS_COMBINATIONS[case_flags]
        self.zerowidth = bool(zerowidth)

        if (self.positive and (self.case_flags & FULLIGNORECASE) ==
          FULLIGNORECASE):
            self.folded = _regex.fold_case(FULL_CASE_FOLDING, chr(self.value))
        else:
            self.folded = chr(self.value)

        self._key = (self.__class__, self.value, self.positive,
          self.case_flags, self.zerowidth)

    def rebuild(self, positive, case_flags, zerowidth):
        return Character(self.value, positive, case_flags, zerowidth)

    def optimise(self, info, reverse, in_set=False):
        return self

    def get_firstset(self, reverse):
        return set([self])

    def has_simple_start(self):
        return True

    def _compile(self, reverse, fuzzy):
        flags = 0
        if self.positive:
            flags |= POSITIVE_OP
        if self.zerowidth:
            flags |= ZEROWIDTH_OP
        if fuzzy:
            flags |= FUZZY_OP

        code = PrecompiledCode([self._opcode[self.case_flags, reverse], flags,
          self.value])

        if len(self.folded) > 1:
            # The character expands on full case-folding.
            code = Branch([code, String([ord(c) for c in self.folded],
              case_flags=self.case_flags)])

        return code.compile(reverse, fuzzy)

    def dump(self, indent, reverse):
        display = ascii(chr(self.value)).lstrip("bu")
        print("{}CHARACTER {} {}{}".format(INDENT * indent,
          POS_TEXT[self.positive], display, CASE_TEXT[self.case_flags]))

    def matches(self, ch):
        return (ch == self.value) == self.positive

    def max_width(self):
        return len(self.folded)

    def get_required_string(self, reverse):
        if not self.positive:
            return 1, None

        self.folded_characters = tuple(ord(c) for c in self.folded)

        return 0, self

class Conditional(RegexBase):
    def __init__(self, info, group, yes_item, no_item, position):
        RegexBase.__init__(self)
        self.info = info
        self.group = group
        self.yes_item = yes_item
        self.no_item = no_item
        self.position = position

    def fix_groups(self, pattern, reverse, fuzzy):
        try:
            self.group = int(self.group)
        except ValueError:
            try:
                self.group = self.info.group_index[self.group]
            except KeyError:
                if self.group == 'DEFINE':
                    # 'DEFINE' is a special name unless there's a group with
                    # that name.
                    self.group = 0
                else:
                    raise error("unknown group", pattern, self.position)

        if not 0 <= self.group <= self.info.group_count:
            raise error("invalid group reference", pattern, self.position)

        self.yes_item.fix_groups(pattern, reverse, fuzzy)
        self.no_item.fix_groups(pattern, reverse, fuzzy)

    def optimise(self, info, reverse):
        yes_item = self.yes_item.optimise(info, reverse)
        no_item = self.no_item.optimise(info, reverse)

        return Conditional(info, self.group, yes_item, no_item, self.position)

    def pack_characters(self, info):
        self.yes_item = self.yes_item.pack_characters(info)
        self.no_item = self.no_item.pack_characters(info)
        return self

    def remove_captures(self):
        self.yes_item = self.yes_item.remove_captures()
        self.no_item = self.no_item.remove_captures()

    def is_atomic(self):
        return self.yes_item.is_atomic() and self.no_item.is_atomic()

    def can_be_affix(self):
        return self.yes_item.can_be_affix() and self.no_item.can_be_affix()

    def contains_group(self):
        return self.yes_item.contains_group() or self.no_item.contains_group()

    def get_firstset(self, reverse):
        return (self.yes_item.get_firstset(reverse) |
          self.no_item.get_firstset(reverse))

    def _compile(self, reverse, fuzzy):
        code = [(OP.GROUP_EXISTS, self.group)]
        code.extend(self.yes_item.compile(reverse, fuzzy))
        add_code = self.no_item.compile(reverse, fuzzy)
        if add_code:
            code.append((OP.NEXT, ))
            code.extend(add_code)

        code.append((OP.END, ))

        return code

    def dump(self, indent, reverse):
        print("{}GROUP_EXISTS {}".format(INDENT * indent, self.group))
        self.yes_item.dump(indent + 1, reverse)
        if not self.no_item.is_empty():
            print("{}OR".format(INDENT * indent))
            self.no_item.dump(indent + 1, reverse)

    def is_empty(self):
        return self.yes_item.is_empty() and self.no_item.is_empty()

    def __eq__(self, other):
        return type(self) is type(other) and (self.group, self.yes_item,
          self.no_item) == (other.group, other.yes_item, other.no_item)

    def max_width(self):
        return max(self.yes_item.max_width(), self.no_item.max_width())

    def __del__(self):
        self.info = None

class DefaultBoundary(ZeroWidthBase):
    _opcode = OP.DEFAULT_BOUNDARY
    _op_name = "DEFAULT_BOUNDARY"

class DefaultEndOfWord(ZeroWidthBase):
    _opcode = OP.DEFAULT_END_OF_WORD
    _op_name = "DEFAULT_END_OF_WORD"

class DefaultStartOfWord(ZeroWidthBase):
    _opcode = OP.DEFAULT_START_OF_WORD
    _op_name = "DEFAULT_START_OF_WORD"

class EndOfLine(ZeroWidthBase):
    _opcode = OP.END_OF_LINE
    _op_name = "END_OF_LINE"

class EndOfLineU(EndOfLine):
    _opcode = OP.END_OF_LINE_U
    _op_name = "END_OF_LINE_U"

class EndOfString(ZeroWidthBase):
    _opcode = OP.END_OF_STRING
    _op_name = "END_OF_STRING"

class EndOfStringLine(ZeroWidthBase):
    _opcode = OP.END_OF_STRING_LINE
    _op_name = "END_OF_STRING_LINE"

class EndOfStringLineU(EndOfStringLine):
    _opcode = OP.END_OF_STRING_LINE_U
    _op_name = "END_OF_STRING_LINE_U"

class EndOfWord(ZeroWidthBase):
    _opcode = OP.END_OF_WORD
    _op_name = "END_OF_WORD"

class Failure(ZeroWidthBase):
    _op_name = "FAILURE"

    def _compile(self, reverse, fuzzy):
        return [(OP.FAILURE, )]

class Fuzzy(RegexBase):
    def __init__(self, subpattern, constraints=None):
        RegexBase.__init__(self)
        if constraints is None:
            constraints = {}
        self.subpattern = subpattern
        self.constraints = constraints

        # If an error type is mentioned in the cost equation, then its maximum
        # defaults to unlimited.
        if "cost" in constraints:
            for e in "dis":
                if e in constraints["cost"]:
                    constraints.setdefault(e, (0, None))

        # If any error type is mentioned, then all the error maxima default to
        # 0, otherwise they default to unlimited.
        if set(constraints) & set("dis"):
            for e in "dis":
                constraints.setdefault(e, (0, 0))
        else:
            for e in "dis":
                constraints.setdefault(e, (0, None))

        # The maximum of the generic error type defaults to unlimited.
        constraints.setdefault("e", (0, None))

        # The cost equation defaults to equal costs. Also, the cost of any
        # error type not mentioned in the cost equation defaults to 0.
        if "cost" in constraints:
            for e in "dis":
                constraints["cost"].setdefault(e, 0)
        else:
            constraints["cost"] = {"d": 1, "i": 1, "s": 1, "max":
              constraints["e"][1]}

    def fix_groups(self, pattern, reverse, fuzzy):
        self.subpattern.fix_groups(pattern, reverse, True)

    def pack_characters(self, info):
        self.subpattern = self.subpattern.pack_characters(info)
        return self

    def remove_captures(self):
        self.subpattern = self.subpattern.remove_captures()
        return self

    def is_atomic(self):
        return self.subpattern.is_atomic()

    def contains_group(self):
        return self.subpattern.contains_group()

    def _compile(self, reverse, fuzzy):
        # The individual limits.
        arguments = []
        for e in "dise":
            v = self.constraints[e]
            arguments.append(v[0])
            arguments.append(UNLIMITED if v[1] is None else v[1])

        # The coeffs of the cost equation.
        for e in "dis":
            arguments.append(self.constraints["cost"][e])

        # The maximum of the cost equation.
        v = self.constraints["cost"]["max"]
        arguments.append(UNLIMITED if v is None else v)

        flags = 0
        if reverse:
            flags |= REVERSE_OP

        test = self.constraints.get("test")

        if test:
            return ([(OP.FUZZY_EXT, flags) + tuple(arguments)] +
              test.compile(reverse, True) + [(OP.NEXT,)] +
              self.subpattern.compile(reverse, True) + [(OP.END,)])

        return ([(OP.FUZZY, flags) + tuple(arguments)] +
          self.subpattern.compile(reverse, True) + [(OP.END,)])

    def dump(self, indent, reverse):
        constraints = self._constraints_to_string()
        if constraints:
            constraints = " " + constraints
        print("{}FUZZY{}".format(INDENT * indent, constraints))
        self.subpattern.dump(indent + 1, reverse)

    def is_empty(self):
        return self.subpattern.is_empty()

    def __eq__(self, other):
        return (type(self) is type(other) and self.subpattern ==
          other.subpattern and self.constraints == other.constraints)

    def max_width(self):
        return UNLIMITED

    def _constraints_to_string(self):
        constraints = []

        for name in "ids":
            min, max = self.constraints[name]
            if max == 0:
                continue

            con = ""

            if min > 0:
                con = "{}<=".format(min)

            con += name

            if max is not None:
                con += "<={}".format(max)

            constraints.append(con)

        cost = []
        for name in "ids":
            coeff = self.constraints["cost"][name]
            if coeff > 0:
                cost.append("{}{}".format(coeff, name))

        limit = self.constraints["cost"]["max"]
        if limit is not None and limit > 0:
            cost = "{}<={}".format("+".join(cost), limit)
            constraints.append(cost)

        return ",".join(constraints)

class Grapheme(RegexBase):
    def _compile(self, reverse, fuzzy):
        # Match at least 1 character until a grapheme boundary is reached. Note
        # that this is the same whether matching forwards or backwards.
        grapheme_matcher = Atomic(Sequence([LazyRepeat(AnyAll(), 1, None),
          GraphemeBoundary()]))

        return grapheme_matcher.compile(reverse, fuzzy)

    def dump(self, indent, reverse):
        print("{}GRAPHEME".format(INDENT * indent))

    def max_width(self):
        return UNLIMITED

class GraphemeBoundary:
    def compile(self, reverse, fuzzy):
        return [(OP.GRAPHEME_BOUNDARY, 1)]

class GreedyRepeat(RegexBase):
    _opcode = OP.GREEDY_REPEAT
    _op_name = "GREEDY_REPEAT"

    def __init__(self, subpattern, min_count, max_count):
        RegexBase.__init__(self)
        self.subpattern = subpattern
        self.min_count = min_count
        self.max_count = max_count

    def fix_groups(self, pattern, reverse, fuzzy):
        self.subpattern.fix_groups(pattern, reverse, fuzzy)

    def optimise(self, info, reverse):
        subpattern = self.subpattern.optimise(info, reverse)

        return type(self)(subpattern, self.min_count, self.max_count)

    def pack_characters(self, info):
        self.subpattern = self.subpattern.pack_characters(info)
        return self

    def remove_captures(self):
        self.subpattern = self.subpattern.remove_captures()
        return self

    def is_atomic(self):
        return self.min_count == self.max_count and self.subpattern.is_atomic()

    def can_be_affix(self):
        return False

    def contains_group(self):
        return self.subpattern.contains_group()

    def get_firstset(self, reverse):
        fs = self.subpattern.get_firstset(reverse)
        if self.min_count == 0:
            fs.add(None)

        return fs

    def _compile(self, reverse, fuzzy):
        repeat = [self._opcode, self.min_count]
        if self.max_count is None:
            repeat.append(UNLIMITED)
        else:
            repeat.append(self.max_count)

        subpattern = self.subpattern.compile(reverse, fuzzy)
        if not subpattern:
            return []

        return ([tuple(repeat)] + subpattern + [(OP.END, )])

    def dump(self, indent, reverse):
        if self.max_count is None:
            limit = "INF"
        else:
            limit = self.max_count
        print("{}{} {} {}".format(INDENT * indent, self._op_name,
          self.min_count, limit))

        self.subpattern.dump(indent + 1, reverse)

    def is_empty(self):
        return self.subpattern.is_empty()

    def __eq__(self, other):
        return type(self) is type(other) and (self.subpattern, self.min_count,
          self.max_count) == (other.subpattern, other.min_count,
          other.max_count)

    def max_width(self):
        if self.max_count is None:
            return UNLIMITED

        return self.subpattern.max_width() * self.max_count

    def get_required_string(self, reverse):
        max_count = UNLIMITED if self.max_count is None else self.max_count
        if self.min_count == 0:
            w = self.subpattern.max_width() * max_count
            return min(w, UNLIMITED), None

        ofs, req = self.subpattern.get_required_string(reverse)
        if req:
            return ofs, req

        w = self.subpattern.max_width() * max_count
        return min(w, UNLIMITED), None

class PossessiveRepeat(GreedyRepeat):
    def is_atomic(self):
        return True

    def _compile(self, reverse, fuzzy):
        subpattern = self.subpattern.compile(reverse, fuzzy)
        if not subpattern:
            return []

        repeat = [self._opcode, self.min_count]
        if self.max_count is None:
            repeat.append(UNLIMITED)
        else:
            repeat.append(self.max_count)

        return ([(OP.ATOMIC, ), tuple(repeat)] + subpattern + [(OP.END, ),
          (OP.END, )])

    def dump(self, indent, reverse):
        print("{}ATOMIC".format(INDENT * indent))

        if self.max_count is None:
            limit = "INF"
        else:
            limit = self.max_count
        print("{}{} {} {}".format(INDENT * (indent + 1), self._op_name,
          self.min_count, limit))

        self.subpattern.dump(indent + 2, reverse)

class Group(RegexBase):
    def __init__(self, info, group, subpattern):
        RegexBase.__init__(self)
        self.info = info
        self.group = group
        self.subpattern = subpattern

        self.call_ref = None

    def fix_groups(self, pattern, reverse, fuzzy):
        self.info.defined_groups[self.group] = (self, reverse, fuzzy)
        self.subpattern.fix_groups(pattern, reverse, fuzzy)

    def optimise(self, info, reverse):
        subpattern = self.subpattern.optimise(info, reverse)

        return Group(self.info, self.group, subpattern)

    def pack_characters(self, info):
        self.subpattern = self.subpattern.pack_characters(info)
        return self

    def remove_captures(self):
        return self.subpattern.remove_captures()

    def is_atomic(self):
        return self.subpattern.is_atomic()

    def can_be_affix(self):
        return False

    def contains_group(self):
        return True

    def get_firstset(self, reverse):
        return self.subpattern.get_firstset(reverse)

    def has_simple_start(self):
        return self.subpattern.has_simple_start()

    def _compile(self, reverse, fuzzy):
        code = []

        public_group = private_group = self.group
        if private_group < 0:
            public_group = self.info.private_groups[private_group]
            private_group = self.info.group_count - private_group

        key = self.group, reverse, fuzzy
        ref = self.info.call_refs.get(key)
        if ref is not None:
            code += [(OP.CALL_REF, ref)]

        code += [(OP.GROUP, int(not reverse), private_group, public_group)]
        code += self.subpattern.compile(reverse, fuzzy)
        code += [(OP.END, )]

        if ref is not None:
            code += [(OP.END, )]

        return code

    def dump(self, indent, reverse):
        group = self.group
        if group < 0:
            group = private_groups[group]
        print("{}GROUP {}".format(INDENT * indent, group))
        self.subpattern.dump(indent + 1, reverse)

    def __eq__(self, other):
        return (type(self) is type(other) and (self.group, self.subpattern) ==
          (other.group, other.subpattern))

    def max_width(self):
        return self.subpattern.max_width()

    def get_required_string(self, reverse):
        return self.subpattern.get_required_string(reverse)

    def __del__(self):
        self.info = None

class Keep(ZeroWidthBase):
    _opcode = OP.KEEP
    _op_name = "KEEP"

class LazyRepeat(GreedyRepeat):
    _opcode = OP.LAZY_REPEAT
    _op_name = "LAZY_REPEAT"

class LookAround(RegexBase):
    _dir_text = {False: "AHEAD", True: "BEHIND"}

    def __init__(self, behind, positive, subpattern):
        RegexBase.__init__(self)
        self.behind = bool(behind)
        self.positive = bool(positive)
        self.subpattern = subpattern

    def fix_groups(self, pattern, reverse, fuzzy):
        self.subpattern.fix_groups(pattern, self.behind, fuzzy)

    def optimise(self, info, reverse):
        subpattern = self.subpattern.optimise(info, self.behind)
        if self.positive and subpattern.is_empty():
            return subpattern

        return LookAround(self.behind, self.positive, subpattern)

    def pack_characters(self, info):
        self.subpattern = self.subpattern.pack_characters(info)
        return self

    def remove_captures(self):
        return self.subpattern.remove_captures()

    def is_atomic(self):
        return self.subpattern.is_atomic()

    def can_be_affix(self):
        return self.subpattern.can_be_affix()

    def contains_group(self):
        return self.subpattern.contains_group()

    def get_firstset(self, reverse):
        if self.positive and self.behind == reverse:
            return self.subpattern.get_firstset(reverse)

        return set([None])

    def _compile(self, reverse, fuzzy):
        flags = 0
        if self.positive:
            flags |= POSITIVE_OP
        if fuzzy:
            flags |= FUZZY_OP
        if reverse:
            flags |= REVERSE_OP

        return ([(OP.LOOKAROUND, flags, int(not self.behind))] +
          self.subpattern.compile(self.behind) + [(OP.END, )])

    def dump(self, indent, reverse):
        print("{}LOOK{} {}".format(INDENT * indent,
          self._dir_text[self.behind], POS_TEXT[self.positive]))
        self.subpattern.dump(indent + 1, self.behind)

    def is_empty(self):
        return self.positive and self.subpattern.is_empty()

    def __eq__(self, other):
        return type(self) is type(other) and (self.behind, self.positive,
          self.subpattern) == (other.behind, other.positive, other.subpattern)

    def max_width(self):
        return 0

class LookAroundConditional(RegexBase):
    _dir_text = {False: "AHEAD", True: "BEHIND"}

    def __init__(self, behind, positive, subpattern, yes_item, no_item):
        RegexBase.__init__(self)
        self.behind = bool(behind)
        self.positive = bool(positive)
        self.subpattern = subpattern
        self.yes_item = yes_item
        self.no_item = no_item

    def fix_groups(self, pattern, reverse, fuzzy):
        self.subpattern.fix_groups(pattern, reverse, fuzzy)
        self.yes_item.fix_groups(pattern, reverse, fuzzy)
        self.no_item.fix_groups(pattern, reverse, fuzzy)

    def optimise(self, info, reverse):
        subpattern = self.subpattern.optimise(info, self.behind)
        yes_item = self.yes_item.optimise(info, self.behind)
        no_item = self.no_item.optimise(info, self.behind)

        return LookAroundConditional(self.behind, self.positive, subpattern,
          yes_item, no_item)

    def pack_characters(self, info):
        self.subpattern = self.subpattern.pack_characters(info)
        self.yes_item = self.yes_item.pack_characters(info)
        self.no_item = self.no_item.pack_characters(info)
        return self

    def remove_captures(self):
        self.subpattern = self.subpattern.remove_captures()
        self.yes_item = self.yes_item.remove_captures()
        self.no_item = self.no_item.remove_captures()

    def is_atomic(self):
        return (self.subpattern.is_atomic() and self.yes_item.is_atomic() and
          self.no_item.is_atomic())

    def can_be_affix(self):
        return (self.subpattern.can_be_affix() and self.yes_item.can_be_affix()
          and self.no_item.can_be_affix())

    def contains_group(self):
        return (self.subpattern.contains_group() or
          self.yes_item.contains_group() or self.no_item.contains_group())

    def _compile(self, reverse, fuzzy):
        code = [(OP.CONDITIONAL, int(self.positive), int(not self.behind))]
        code.extend(self.subpattern.compile(self.behind, fuzzy))
        code.append((OP.NEXT, ))
        code.extend(self.yes_item.compile(reverse, fuzzy))
        add_code = self.no_item.compile(reverse, fuzzy)
        if add_code:
            code.append((OP.NEXT, ))
            code.extend(add_code)

        code.append((OP.END, ))

        return code

    def dump(self, indent, reverse):
        print("{}CONDITIONAL {} {}".format(INDENT * indent,
          self._dir_text[self.behind], POS_TEXT[self.positive]))
        self.subpattern.dump(indent + 1, self.behind)
        print("{}EITHER".format(INDENT * indent))
        self.yes_item.dump(indent + 1, reverse)
        if not self.no_item.is_empty():
            print("{}OR".format(INDENT * indent))
            self.no_item.dump(indent + 1, reverse)

    def is_empty(self):
        return (self.subpattern.is_empty() and self.yes_item.is_empty() or
          self.no_item.is_empty())

    def __eq__(self, other):
        return type(self) is type(other) and (self.subpattern, self.yes_item,
          self.no_item) == (other.subpattern, other.yes_item, other.no_item)

    def max_width(self):
        return max(self.yes_item.max_width(), self.no_item.max_width())

    def get_required_string(self, reverse):
        return self.max_width(), None

class PrecompiledCode(RegexBase):
    def __init__(self, code):
        self.code = code

    def _compile(self, reverse, fuzzy):
        return [tuple(self.code)]

class Property(RegexBase):
    _opcode = {(NOCASE, False): OP.PROPERTY, (IGNORECASE, False):
      OP.PROPERTY_IGN, (FULLCASE, False): OP.PROPERTY, (FULLIGNORECASE, False):
      OP.PROPERTY_IGN, (NOCASE, True): OP.PROPERTY_REV, (IGNORECASE, True):
      OP.PROPERTY_IGN_REV, (FULLCASE, True): OP.PROPERTY_REV, (FULLIGNORECASE,
      True): OP.PROPERTY_IGN_REV}

    def __init__(self, value, positive=True, case_flags=NOCASE,
      zerowidth=False):
        RegexBase.__init__(self)
        self.value = value
        self.positive = bool(positive)
        self.case_flags = CASE_FLAGS_COMBINATIONS[case_flags]
        self.zerowidth = bool(zerowidth)

        self._key = (self.__class__, self.value, self.positive,
          self.case_flags, self.zerowidth)

    def rebuild(self, positive, case_flags, zerowidth):
        return Property(self.value, positive, case_flags, zerowidth)

    def optimise(self, info, reverse, in_set=False):
        return self

    def get_firstset(self, reverse):
        return set([self])

    def has_simple_start(self):
        return True

    def _compile(self, reverse, fuzzy):
        flags = 0
        if self.positive:
            flags |= POSITIVE_OP
        if self.zerowidth:
            flags |= ZEROWIDTH_OP
        if fuzzy:
            flags |= FUZZY_OP
        return [(self._opcode[self.case_flags, reverse], flags, self.value)]

    def dump(self, indent, reverse):
        prop = PROPERTY_NAMES[self.value >> 16]
        name, value = prop[0], prop[1][self.value & 0xFFFF]
        print("{}PROPERTY {} {}:{}{}".format(INDENT * indent,
          POS_TEXT[self.positive], name, value, CASE_TEXT[self.case_flags]))

    def matches(self, ch):
        return _regex.has_property_value(self.value, ch) == self.positive

    def max_width(self):
        return 1

class Prune(ZeroWidthBase):
    _op_name = "PRUNE"

    def _compile(self, reverse, fuzzy):
        return [(OP.PRUNE, )]

class Range(RegexBase):
    _opcode = {(NOCASE, False): OP.RANGE, (IGNORECASE, False): OP.RANGE_IGN,
      (FULLCASE, False): OP.RANGE, (FULLIGNORECASE, False): OP.RANGE_IGN,
      (NOCASE, True): OP.RANGE_REV, (IGNORECASE, True): OP.RANGE_IGN_REV,
      (FULLCASE, True): OP.RANGE_REV, (FULLIGNORECASE, True): OP.RANGE_IGN_REV}
    _op_name = "RANGE"

    def __init__(self, lower, upper, positive=True, case_flags=NOCASE,
      zerowidth=False):
        RegexBase.__init__(self)
        self.lower = lower
        self.upper = upper
        self.positive = bool(positive)
        self.case_flags = CASE_FLAGS_COMBINATIONS[case_flags]
        self.zerowidth = bool(zerowidth)

        self._key = (self.__class__, self.lower, self.upper, self.positive,
          self.case_flags, self.zerowidth)

    def rebuild(self, positive, case_flags, zerowidth):
        return Range(self.lower, self.upper, positive, case_flags, zerowidth)

    def optimise(self, info, reverse, in_set=False):
        # Is the range case-sensitive?
        if not self.positive or not (self.case_flags & IGNORECASE) or in_set:
            return self

        # Is full case-folding possible?
        if (not (info.flags & UNICODE) or (self.case_flags & FULLIGNORECASE) !=
          FULLIGNORECASE):
            return self

        # Get the characters which expand to multiple codepoints on folding.
        expanding_chars = _regex.get_expand_on_folding()

        # Get the folded characters in the range.
        items = []
        for ch in expanding_chars:
            if self.lower <= ord(ch) <= self.upper:
                folded = _regex.fold_case(FULL_CASE_FOLDING, ch)
                items.append(String([ord(c) for c in folded],
                  case_flags=self.case_flags))

        if not items:
            # We can fall back to simple case-folding.
            return self

        if len(items) < self.upper - self.lower + 1:
            # Not all the characters are covered by the full case-folding.
            items.insert(0, self)

        return Branch(items)

    def _compile(self, reverse, fuzzy):
        flags = 0
        if self.positive:
            flags |= POSITIVE_OP
        if self.zerowidth:
            flags |= ZEROWIDTH_OP
        if fuzzy:
            flags |= FUZZY_OP
        return [(self._opcode[self.case_flags, reverse], flags, self.lower,
          self.upper)]

    def dump(self, indent, reverse):
        display_lower = ascii(chr(self.lower)).lstrip("bu")
        display_upper = ascii(chr(self.upper)).lstrip("bu")
        print("{}RANGE {} {} {}{}".format(INDENT * indent,
          POS_TEXT[self.positive], display_lower, display_upper,
          CASE_TEXT[self.case_flags]))

    def matches(self, ch):
        return (self.lower <= ch <= self.upper) == self.positive

    def max_width(self):
        return 1

class RefGroup(RegexBase):
    _opcode = {(NOCASE, False): OP.REF_GROUP, (IGNORECASE, False):
      OP.REF_GROUP_IGN, (FULLCASE, False): OP.REF_GROUP, (FULLIGNORECASE,
      False): OP.REF_GROUP_FLD, (NOCASE, True): OP.REF_GROUP_REV, (IGNORECASE,
      True): OP.REF_GROUP_IGN_REV, (FULLCASE, True): OP.REF_GROUP_REV,
      (FULLIGNORECASE, True): OP.REF_GROUP_FLD_REV}

    def __init__(self, info, group, position, case_flags=NOCASE):
        RegexBase.__init__(self)
        self.info = info
        self.group = group
        self.position = position
        self.case_flags = CASE_FLAGS_COMBINATIONS[case_flags]

        self._key = self.__class__, self.group, self.case_flags

    def fix_groups(self, pattern, reverse, fuzzy):
        try:
            self.group = int(self.group)
        except ValueError:
            try:
                self.group = self.info.group_index[self.group]
            except KeyError:
                raise error("unknown group", pattern, self.position)

        if not 1 <= self.group <= self.info.group_count:
            raise error("invalid group reference", pattern, self.position)

        self._key = self.__class__, self.group, self.case_flags

    def remove_captures(self):
        raise error("group reference not allowed", pattern, self.position)

    def _compile(self, reverse, fuzzy):
        flags = 0
        if fuzzy:
            flags |= FUZZY_OP
        return [(self._opcode[self.case_flags, reverse], flags, self.group)]

    def dump(self, indent, reverse):
        print("{}REF_GROUP {}{}".format(INDENT * indent, self.group,
          CASE_TEXT[self.case_flags]))

    def max_width(self):
        return UNLIMITED

    def __del__(self):
        self.info = None

class SearchAnchor(ZeroWidthBase):
    _opcode = OP.SEARCH_ANCHOR
    _op_name = "SEARCH_ANCHOR"

class Sequence(RegexBase):
    def __init__(self, items=None):
        RegexBase.__init__(self)
        if items is None:
            items = []

        self.items = items

    def fix_groups(self, pattern, reverse, fuzzy):
        for s in self.items:
            s.fix_groups(pattern, reverse, fuzzy)

    def optimise(self, info, reverse):
        # Flatten the sequences.
        items = []
        for s in self.items:
            s = s.optimise(info, reverse)
            if isinstance(s, Sequence):
                items.extend(s.items)
            else:
                items.append(s)

        return make_sequence(items)

    def pack_characters(self, info):
        "Packs sequences of characters into strings."
        items = []
        characters = []
        case_flags = NOCASE
        for s in self.items:
            if type(s) is Character and s.positive and not s.zerowidth:
                if s.case_flags != case_flags:
                    # Different case sensitivity, so flush, unless neither the
                    # previous nor the new character are cased.
                    if s.case_flags or is_cased_i(info, s.value):
                        Sequence._flush_characters(info, characters,
                          case_flags, items)

                        case_flags = s.case_flags

                characters.append(s.value)
            elif type(s) is String or type(s) is Literal:
                if s.case_flags != case_flags:
                    # Different case sensitivity, so flush, unless the neither
                    # the previous nor the new string are cased.
                    if s.case_flags or any(is_cased_i(info, c) for c in
                      characters):
                        Sequence._flush_characters(info, characters,
                          case_flags, items)

                        case_flags = s.case_flags

                characters.extend(s.characters)
            else:
                Sequence._flush_characters(info, characters, case_flags, items)

                items.append(s.pack_characters(info))

        Sequence._flush_characters(info, characters, case_flags, items)

        return make_sequence(items)

    def remove_captures(self):
        self.items = [s.remove_captures() for s in self.items]
        return self

    def is_atomic(self):
        return all(s.is_atomic() for s in self.items)

    def can_be_affix(self):
        return False

    def contains_group(self):
        return any(s.contains_group() for s in self.items)

    def get_firstset(self, reverse):
        fs = set()
        items = self.items
        if reverse:
            items.reverse()
        for s in items:
            fs |= s.get_firstset(reverse)
            if None not in fs:
                return fs
            fs.discard(None)

        return fs | set([None])

    def has_simple_start(self):
        return bool(self.items) and self.items[0].has_simple_start()

    def _compile(self, reverse, fuzzy):
        seq = self.items
        if reverse:
            seq = seq[::-1]

        code = []
        for s in seq:
            code.extend(s.compile(reverse, fuzzy))

        return code

    def dump(self, indent, reverse):
        for s in self.items:
            s.dump(indent, reverse)

    @staticmethod
    def _flush_characters(info, characters, case_flags, items):
        if not characters:
            return

        # Disregard case_flags if all of the characters are case-less.
        if case_flags & IGNORECASE:
            if not any(is_cased_i(info, c) for c in characters):
                case_flags = NOCASE

        if (case_flags & FULLIGNORECASE) == FULLIGNORECASE:
            literals = Sequence._fix_full_casefold(characters)

            for item in literals:
                chars = item.characters

                if len(chars) == 1:
                    items.append(Character(chars[0], case_flags=item.case_flags))
                else:
                    items.append(String(chars, case_flags=item.case_flags))
        else:
            if len(characters) == 1:
                items.append(Character(characters[0], case_flags=case_flags))
            else:
                items.append(String(characters, case_flags=case_flags))

        characters[:] = []

    @staticmethod
    def _fix_full_casefold(characters):
        # Split a literal needing full case-folding into chunks that need it
        # and chunks that can use simple case-folding, which is faster.
        expanded = [_regex.fold_case(FULL_CASE_FOLDING, c) for c in
          _regex.get_expand_on_folding()]
        string = _regex.fold_case(FULL_CASE_FOLDING, ''.join(chr(c)
          for c in characters)).lower()
        chunks = []

        for e in expanded:
            found = string.find(e)

            while found >= 0:
                chunks.append((found, found + len(e)))
                found = string.find(e, found + 1)

        pos = 0
        literals = []

        for start, end in Sequence._merge_chunks(chunks):
            if pos < start:
                literals.append(Literal(characters[pos : start],
                  case_flags=IGNORECASE))

            literals.append(Literal(characters[start : end],
              case_flags=FULLIGNORECASE))
            pos = end

        if pos < len(characters):
            literals.append(Literal(characters[pos : ], case_flags=IGNORECASE))

        return literals

    @staticmethod
    def _merge_chunks(chunks):
        if len(chunks) < 2:
            return chunks

        chunks.sort()

        start, end = chunks[0]
        new_chunks = []

        for s, e in chunks[1 : ]:
            if s <= end:
                end = max(end, e)
            else:
                new_chunks.append((start, end))
                start, end = s, e

        new_chunks.append((start, end))

        return new_chunks

    def is_empty(self):
        return all(i.is_empty() for i in self.items)

    def __eq__(self, other):
        return type(self) is type(other) and self.items == other.items

    def max_width(self):
        return sum(s.max_width() for s in self.items)

    def get_required_string(self, reverse):
        seq = self.items
        if reverse:
            seq = seq[::-1]

        offset = 0

        for s in seq:
            ofs, req = s.get_required_string(reverse)
            offset += ofs
            if req:
                return offset, req

        return offset, None

class SetBase(RegexBase):
    def __init__(self, info, items, positive=True, case_flags=NOCASE,
      zerowidth=False):
        RegexBase.__init__(self)
        self.info = info
        self.items = tuple(items)
        self.positive = bool(positive)
        self.case_flags = CASE_FLAGS_COMBINATIONS[case_flags]
        self.zerowidth = bool(zerowidth)

        self.char_width = 1

        self._key = (self.__class__, self.items, self.positive,
          self.case_flags, self.zerowidth)

    def rebuild(self, positive, case_flags, zerowidth):
        return type(self)(self.info, self.items, positive, case_flags,
          zerowidth).optimise(self.info, False)

    def get_firstset(self, reverse):
        return set([self])

    def has_simple_start(self):
        return True

    def _compile(self, reverse, fuzzy):
        flags = 0
        if self.positive:
            flags |= POSITIVE_OP
        if self.zerowidth:
            flags |= ZEROWIDTH_OP
        if fuzzy:
            flags |= FUZZY_OP
        code = [(self._opcode[self.case_flags, reverse], flags)]
        for m in self.items:
            code.extend(m.compile())

        code.append((OP.END, ))

        return code

    def dump(self, indent, reverse):
        print("{}{} {}{}".format(INDENT * indent, self._op_name,
          POS_TEXT[self.positive], CASE_TEXT[self.case_flags]))
        for i in self.items:
            i.dump(indent + 1, reverse)

    def _handle_case_folding(self, info, in_set):
        # Is the set case-sensitive?
        if not self.positive or not (self.case_flags & IGNORECASE) or in_set:
            return self

        # Is full case-folding possible?
        if (not (self.info.flags & UNICODE) or (self.case_flags &
          FULLIGNORECASE) != FULLIGNORECASE):
            return self

        # Get the characters which expand to multiple codepoints on folding.
        expanding_chars = _regex.get_expand_on_folding()

        # Get the folded characters in the set.
        items = []
        seen = set()
        for ch in expanding_chars:
            if self.matches(ord(ch)):
                folded = _regex.fold_case(FULL_CASE_FOLDING, ch)
                if folded not in seen:
                    items.append(String([ord(c) for c in folded],
                      case_flags=self.case_flags))
                    seen.add(folded)

        if not items:
            # We can fall back to simple case-folding.
            return self

        return Branch([self] + items)

    def max_width(self):
        # Is the set case-sensitive?
        if not self.positive or not (self.case_flags & IGNORECASE):
            return 1

        # Is full case-folding possible?
        if (not (self.info.flags & UNICODE) or (self.case_flags &
          FULLIGNORECASE) != FULLIGNORECASE):
            return 1

        # Get the characters which expand to multiple codepoints on folding.
        expanding_chars = _regex.get_expand_on_folding()

        # Get the folded characters in the set.
        seen = set()
        for ch in expanding_chars:
            if self.matches(ord(ch)):
                folded = _regex.fold_case(FULL_CASE_FOLDING, ch)
                seen.add(folded)

        if not seen:
            return 1

        return max(len(folded) for folded in seen)

    def __del__(self):
        self.info = None

class SetDiff(SetBase):
    _opcode = {(NOCASE, False): OP.SET_DIFF, (IGNORECASE, False):
      OP.SET_DIFF_IGN, (FULLCASE, False): OP.SET_DIFF, (FULLIGNORECASE, False):
      OP.SET_DIFF_IGN, (NOCASE, True): OP.SET_DIFF_REV, (IGNORECASE, True):
      OP.SET_DIFF_IGN_REV, (FULLCASE, True): OP.SET_DIFF_REV, (FULLIGNORECASE,
      True): OP.SET_DIFF_IGN_REV}
    _op_name = "SET_DIFF"

    def optimise(self, info, reverse, in_set=False):
        items = self.items
        if len(items) > 2:
            items = [items[0], SetUnion(info, items[1 : ])]

        if len(items) == 1:
            return items[0].with_flags(case_flags=self.case_flags,
              zerowidth=self.zerowidth).optimise(info, reverse, in_set)

        self.items = tuple(m.optimise(info, reverse, in_set=True) for m in
          items)

        return self._handle_case_folding(info, in_set)

    def matches(self, ch):
        m = self.items[0].matches(ch) and not self.items[1].matches(ch)
        return m == self.positive

class SetInter(SetBase):
    _opcode = {(NOCASE, False): OP.SET_INTER, (IGNORECASE, False):
      OP.SET_INTER_IGN, (FULLCASE, False): OP.SET_INTER, (FULLIGNORECASE,
      False): OP.SET_INTER_IGN, (NOCASE, True): OP.SET_INTER_REV, (IGNORECASE,
      True): OP.SET_INTER_IGN_REV, (FULLCASE, True): OP.SET_INTER_REV,
      (FULLIGNORECASE, True): OP.SET_INTER_IGN_REV}
    _op_name = "SET_INTER"

    def optimise(self, info, reverse, in_set=False):
        items = []
        for m in self.items:
            m = m.optimise(info, reverse, in_set=True)
            if isinstance(m, SetInter) and m.positive:
                # Intersection in intersection.
                items.extend(m.items)
            else:
                items.append(m)

        if len(items) == 1:
            return items[0].with_flags(case_flags=self.case_flags,
              zerowidth=self.zerowidth).optimise(info, reverse, in_set)

        self.items = tuple(items)

        return self._handle_case_folding(info, in_set)

    def matches(self, ch):
        m = all(i.matches(ch) for i in self.items)
        return m == self.positive

class SetSymDiff(SetBase):
    _opcode = {(NOCASE, False): OP.SET_SYM_DIFF, (IGNORECASE, False):
      OP.SET_SYM_DIFF_IGN, (FULLCASE, False): OP.SET_SYM_DIFF, (FULLIGNORECASE,
      False): OP.SET_SYM_DIFF_IGN, (NOCASE, True): OP.SET_SYM_DIFF_REV,
      (IGNORECASE, True): OP.SET_SYM_DIFF_IGN_REV, (FULLCASE, True):
      OP.SET_SYM_DIFF_REV, (FULLIGNORECASE, True): OP.SET_SYM_DIFF_IGN_REV}
    _op_name = "SET_SYM_DIFF"

    def optimise(self, info, reverse, in_set=False):
        items = []
        for m in self.items:
            m = m.optimise(info, reverse, in_set=True)
            if isinstance(m, SetSymDiff) and m.positive:
                # Symmetric difference in symmetric difference.
                items.extend(m.items)
            else:
                items.append(m)

        if len(items) == 1:
            return items[0].with_flags(case_flags=self.case_flags,
              zerowidth=self.zerowidth).optimise(info, reverse, in_set)

        self.items = tuple(items)

        return self._handle_case_folding(info, in_set)

    def matches(self, ch):
        m = False
        for i in self.items:
            m = m != i.matches(ch)

        return m == self.positive

class SetUnion(SetBase):
    _opcode = {(NOCASE, False): OP.SET_UNION, (IGNORECASE, False):
      OP.SET_UNION_IGN, (FULLCASE, False): OP.SET_UNION, (FULLIGNORECASE,
      False): OP.SET_UNION_IGN, (NOCASE, True): OP.SET_UNION_REV, (IGNORECASE,
      True): OP.SET_UNION_IGN_REV, (FULLCASE, True): OP.SET_UNION_REV,
      (FULLIGNORECASE, True): OP.SET_UNION_IGN_REV}
    _op_name = "SET_UNION"

    def optimise(self, info, reverse, in_set=False):
        items = []
        for m in self.items:
            m = m.optimise(info, reverse, in_set=True)
            if isinstance(m, SetUnion) and m.positive:
                # Union in union.
                items.extend(m.items)
            else:
                items.append(m)

        if len(items) == 1:
            i = items[0]
            return i.with_flags(positive=i.positive == self.positive,
              case_flags=self.case_flags,
              zerowidth=self.zerowidth).optimise(info, reverse, in_set)

        self.items = tuple(items)

        return self._handle_case_folding(info, in_set)

    def _compile(self, reverse, fuzzy):
        flags = 0
        if self.positive:
            flags |= POSITIVE_OP
        if self.zerowidth:
            flags |= ZEROWIDTH_OP
        if fuzzy:
            flags |= FUZZY_OP

        characters, others = defaultdict(list), []
        for m in self.items:
            if isinstance(m, Character):
                characters[m.positive].append(m.value)
            else:
                others.append(m)

        code = [(self._opcode[self.case_flags, reverse], flags)]

        for positive, values in characters.items():
            flags = 0
            if positive:
                flags |= POSITIVE_OP
            if len(values) == 1:
                code.append((OP.CHARACTER, flags, values[0]))
            else:
                code.append((OP.STRING, flags, len(values)) + tuple(values))

        for m in others:
            code.extend(m.compile())

        code.append((OP.END, ))

        return code

    def matches(self, ch):
        m = any(i.matches(ch) for i in self.items)
        return m == self.positive

class Skip(ZeroWidthBase):
    _op_name = "SKIP"
    _opcode = OP.SKIP

class StartOfLine(ZeroWidthBase):
    _opcode = OP.START_OF_LINE
    _op_name = "START_OF_LINE"

class StartOfLineU(StartOfLine):
    _opcode = OP.START_OF_LINE_U
    _op_name = "START_OF_LINE_U"

class StartOfString(ZeroWidthBase):
    _opcode = OP.START_OF_STRING
    _op_name = "START_OF_STRING"

class StartOfWord(ZeroWidthBase):
    _opcode = OP.START_OF_WORD
    _op_name = "START_OF_WORD"

class String(RegexBase):
    _opcode = {(NOCASE, False): OP.STRING, (IGNORECASE, False): OP.STRING_IGN,
      (FULLCASE, False): OP.STRING, (FULLIGNORECASE, False): OP.STRING_FLD,
      (NOCASE, True): OP.STRING_REV, (IGNORECASE, True): OP.STRING_IGN_REV,
      (FULLCASE, True): OP.STRING_REV, (FULLIGNORECASE, True):
      OP.STRING_FLD_REV}

    def __init__(self, characters, case_flags=NOCASE):
        self.characters = tuple(characters)
        self.case_flags = CASE_FLAGS_COMBINATIONS[case_flags]

        if (self.case_flags & FULLIGNORECASE) == FULLIGNORECASE:
            folded_characters = []
            for char in self.characters:
                folded = _regex.fold_case(FULL_CASE_FOLDING, chr(char))
                folded_characters.extend(ord(c) for c in folded)
        else:
            folded_characters = self.characters

        self.folded_characters = tuple(folded_characters)
        self.required = False

        self._key = self.__class__, self.characters, self.case_flags

    def get_firstset(self, reverse):
        if reverse:
            pos = -1
        else:
            pos = 0
        return set([Character(self.characters[pos],
          case_flags=self.case_flags)])

    def has_simple_start(self):
        return True

    def _compile(self, reverse, fuzzy):
        flags = 0
        if fuzzy:
            flags |= FUZZY_OP
        if self.required:
            flags |= REQUIRED_OP
        return [(self._opcode[self.case_flags, reverse], flags,
          len(self.folded_characters)) + self.folded_characters]

    def dump(self, indent, reverse):
        display = ascii("".join(chr(c) for c in self.characters)).lstrip("bu")
        print("{}STRING {}{}".format(INDENT * indent, display,
          CASE_TEXT[self.case_flags]))

    def max_width(self):
        return len(self.folded_characters)

    def get_required_string(self, reverse):
        return 0, self

class Literal(String):
    def dump(self, indent, reverse):
        literal = ''.join(chr(c) for c in self.characters)
        display = ascii(literal).lstrip("bu")
        print("{}LITERAL MATCH {}{}".format(INDENT * indent, display,
          CASE_TEXT[self.case_flags]))

class StringSet(Branch):
    def __init__(self, info, name, case_flags=NOCASE):
        self.info = info
        self.name = name
        self.case_flags = CASE_FLAGS_COMBINATIONS[case_flags]

        self._key = self.__class__, self.name, self.case_flags

        self.set_key = (name, self.case_flags)
        if self.set_key not in info.named_lists_used:
            info.named_lists_used[self.set_key] = len(info.named_lists_used)

        index = self.info.named_lists_used[self.set_key]
        items = self.info.kwargs[self.name]

        case_flags = self.case_flags

        encoding = self.info.flags & _ALL_ENCODINGS
        fold_flags = encoding | case_flags

        choices = []

        for string in items:
            if isinstance(string, str):
                string = [ord(c) for c in string]

            choices.append([Character(c, case_flags=case_flags) for c in
              string])

        # Sort from longest to shortest.
        choices.sort(key=len, reverse=True)

        self.branches = [Sequence(choice) for choice in choices]

    def dump(self, indent, reverse):
        print("{}STRING_SET {}{}".format(INDENT * indent, self.name,
          CASE_TEXT[self.case_flags]))

    def __del__(self):
        self.info = None

class Source:
    "Scanner for the regular expression source string."
    def __init__(self, string):
        if isinstance(string, str):
            self.string = string
            self.char_type = chr
        else:
            self.string = string.decode("latin-1")
            self.char_type = lambda c: bytes([c])

        self.pos = 0
        self.ignore_space = False
        self.sep = string[ : 0]

    def get(self, override_ignore=False):
        string = self.string
        pos = self.pos

        try:
            if self.ignore_space and not override_ignore:
                while True:
                    if string[pos].isspace():
                        # Skip over the whitespace.
                        pos += 1
                    elif string[pos] == "#":
                        # Skip over the comment to the end of the line.
                        pos = string.index("\n", pos)
                    else:
                        break

            ch = string[pos]
            self.pos = pos + 1
            return ch
        except IndexError:
            # We've reached the end of the string.
            self.pos = pos
            return string[ : 0]
        except ValueError:
            # The comment extended to the end of the string.
            self.pos = len(string)
            return string[ : 0]

    def get_many(self, count=1):
        string = self.string
        pos = self.pos

        try:
            if self.ignore_space:
                substring = []

                while len(substring) < count:
                    while True:
                        if string[pos].isspace():
                            # Skip over the whitespace.
                            pos += 1
                        elif string[pos] == "#":
                            # Skip over the comment to the end of the line.
                            pos = string.index("\n", pos)
                        else:
                            break

                    substring.append(string[pos])
                    pos += 1

                substring = "".join(substring)
            else:
                substring = string[pos : pos + count]
                pos += len(substring)

            self.pos = pos
            return substring
        except IndexError:
            # We've reached the end of the string.
            self.pos = len(string)
            return "".join(substring)
        except ValueError:
            # The comment extended to the end of the string.
            self.pos = len(string)
            return "".join(substring)

    def get_while(self, test_set, include=True, keep_spaces=False):
        string = self.string
        pos = self.pos

        if self.ignore_space and not keep_spaces:
            try:
                substring = []

                while True:
                    if string[pos].isspace():
                        # Skip over the whitespace.
                        pos += 1
                    elif string[pos] == "#":
                        # Skip over the comment to the end of the line.
                        pos = string.index("\n", pos)
                    elif (string[pos] in test_set) == include:
                        substring.append(string[pos])
                        pos += 1
                    else:
                        break

                self.pos = pos
            except IndexError:
                # We've reached the end of the string.
                self.pos = len(string)
            except ValueError:
                # The comment extended to the end of the string.
                self.pos = len(string)

            return "".join(substring)
        else:
            try:
                while (string[pos] in test_set) == include:
                    pos += 1

                substring = string[self.pos : pos]

                self.pos = pos

                return substring
            except IndexError:
                # We've reached the end of the string.
                substring = string[self.pos : pos]

                self.pos = pos

                return substring

    def skip_while(self, test_set, include=True):
        string = self.string
        pos = self.pos

        try:
            if self.ignore_space:
                while True:
                    if string[pos].isspace():
                        # Skip over the whitespace.
                        pos += 1
                    elif string[pos] == "#":
                        # Skip over the comment to the end of the line.
                        pos = string.index("\n", pos)
                    elif (string[pos] in test_set) == include:
                        pos += 1
                    else:
                        break
            else:
                while (string[pos] in test_set) == include:
                    pos += 1

            self.pos = pos
        except IndexError:
            # We've reached the end of the string.
            self.pos = len(string)
        except ValueError:
            # The comment extended to the end of the string.
            self.pos = len(string)

    def match(self, substring):
        string = self.string
        pos = self.pos

        if self.ignore_space:
            try:
                for c in substring:
                    while True:
                        if string[pos].isspace():
                            # Skip over the whitespace.
                            pos += 1
                        elif string[pos] == "#":
                            # Skip over the comment to the end of the line.
                            pos = string.index("\n", pos)
                        else:
                            break

                    if string[pos] != c:
                        return False

                    pos += 1

                self.pos = pos

                return True
            except IndexError:
                # We've reached the end of the string.
                return False
            except ValueError:
                # The comment extended to the end of the string.
                return False
        else:
            if not string.startswith(substring, pos):
                return False

            self.pos = pos + len(substring)

            return True

    def expect(self, substring):
        if not self.match(substring):
            raise error("missing {}".format(substring), self.string, self.pos)

    def at_end(self):
        string = self.string
        pos = self.pos

        try:
            if self.ignore_space:
                while True:
                    if string[pos].isspace():
                        pos += 1
                    elif string[pos] == "#":
                        pos = string.index("\n", pos)
                    else:
                        break

            return pos >= len(string)
        except IndexError:
            # We've reached the end of the string.
            return True
        except ValueError:
            # The comment extended to the end of the string.
            return True

class Info:
    "Info about the regular expression."

    def __init__(self, flags=0, char_type=None, kwargs={}):
        flags |= DEFAULT_FLAGS[(flags & _ALL_VERSIONS) or DEFAULT_VERSION]
        self.flags = flags
        self.global_flags = flags
        self.inline_locale = False

        self.kwargs = kwargs

        self.group_count = 0
        self.group_index = {}
        self.group_name = {}
        self.char_type = char_type
        self.named_lists_used = {}
        self.open_groups = []
        self.open_group_count = {}
        self.defined_groups = {}
        self.group_calls = []
        self.private_groups = {}

    def open_group(self, name=None):
        group = self.group_index.get(name)
        if group is None:
            while True:
                self.group_count += 1
                if name is None or self.group_count not in self.group_name:
                    break

            group = self.group_count
            if name:
                self.group_index[name] = group
                self.group_name[group] = name

        if group in self.open_groups:
            # We have a nested named group. We'll assign it a private group
            # number, initially negative until we can assign a proper
            # (positive) number.
            group_alias = -(len(self.private_groups) + 1)
            self.private_groups[group_alias] = group
            group = group_alias

        self.open_groups.append(group)
        self.open_group_count[group] = self.open_group_count.get(group, 0) + 1

        return group

    def close_group(self):
        self.open_groups.pop()

    def is_open_group(self, name):
        # In version 1, a group reference can refer to an open group. We'll
        # just pretend the group isn't open.
        version = (self.flags & _ALL_VERSIONS) or DEFAULT_VERSION
        if version == VERSION1:
            return False

        if name.isdigit():
            group = int(name)
        else:
            group = self.group_index.get(name)

        return group in self.open_groups

def _check_group_features(info, parsed):
    """Checks whether the reverse and fuzzy features of the group calls match
    the groups which they call.
    """
    call_refs = {}
    additional_groups = []
    for call, reverse, fuzzy in info.group_calls:
        # Look up the reference of this group call.
        key = (call.group, reverse, fuzzy)
        ref = call_refs.get(key)
        if ref is None:
            # This group doesn't have a reference yet, so look up its features.
            if call.group == 0:
                # Calling the pattern as a whole.
                rev = bool(info.flags & REVERSE)
                fuz = isinstance(parsed, Fuzzy)
                if (rev, fuz) != (reverse, fuzzy):
                    # The pattern as a whole doesn't have the features we want,
                    # so we'll need to make a copy of it with the desired
                    # features.
                    additional_groups.append((CallRef(len(call_refs), parsed),
                      reverse, fuzzy))
            else:
                # Calling a capture group.
                def_info = info.defined_groups[call.group]
                group = def_info[0]
                if def_info[1 : ] != (reverse, fuzzy):
                    # The group doesn't have the features we want, so we'll
                    # need to make a copy of it with the desired features.
                    additional_groups.append((group, reverse, fuzzy))

            ref = len(call_refs)
            call_refs[key] = ref

        call.call_ref = ref

    info.call_refs = call_refs
    info.additional_groups = additional_groups

def _get_required_string(parsed, flags):
    "Gets the required string and related info of a parsed pattern."

    req_offset, required = parsed.get_required_string(bool(flags & REVERSE))
    if required:
        required.required = True
        if req_offset >= UNLIMITED:
            req_offset = -1

        req_flags = required.case_flags
        if not (flags & UNICODE):
            req_flags &= ~UNICODE

        req_chars = required.folded_characters
    else:
        req_offset = 0
        req_chars = ()
        req_flags = 0

    return req_offset, req_chars, req_flags

class Scanner:
    def __init__(self, lexicon, flags=0):
        self.lexicon = lexicon

        # Combine phrases into a compound pattern.
        patterns = []
        for phrase, action in lexicon:
            # Parse the regular expression.
            source = Source(phrase)
            info = Info(flags, source.char_type)
            source.ignore_space = bool(info.flags & VERBOSE)
            parsed = _parse_pattern(source, info)
            if not source.at_end():
                raise error("unbalanced parenthesis", source.string,
                  source.pos)

            # We want to forbid capture groups within each phrase.
            patterns.append(parsed.remove_captures())

        # Combine all the subpatterns into one pattern.
        info = Info(flags)
        patterns = [Group(info, g + 1, p) for g, p in enumerate(patterns)]
        parsed = Branch(patterns)

        # Optimise the compound pattern.
        reverse = bool(info.flags & REVERSE)
        parsed = parsed.optimise(info, reverse)
        parsed = parsed.pack_characters(info)

        # Get the required string.
        req_offset, req_chars, req_flags = _get_required_string(parsed,
          info.flags)

        # Check the features of the groups.
        _check_group_features(info, parsed)

        # Complain if there are any group calls. They are not supported by the
        # Scanner class.
        if info.call_refs:
            raise error("recursive regex not supported by Scanner",
              source.string, source.pos)

        reverse = bool(info.flags & REVERSE)

        # Compile the compound pattern. The result is a list of tuples.
        code = parsed.compile(reverse) + [(OP.SUCCESS, )]

        # Flatten the code into a list of ints.
        code = _flatten_code(code)

        if not parsed.has_simple_start():
            # Get the first set, if possible.
            try:
                fs_code = _compile_firstset(info, parsed.get_firstset(reverse))
                fs_code = _flatten_code(fs_code)
                code = fs_code + code
            except _FirstSetError:
                pass

        # Check the global flags for conflicts.
        version = (info.flags & _ALL_VERSIONS) or DEFAULT_VERSION
        if version not in (0, VERSION0, VERSION1):
            raise ValueError("VERSION0 and VERSION1 flags are mutually incompatible")

        # Create the PatternObject.
        #
        # Local flags like IGNORECASE affect the code generation, but aren't
        # needed by the PatternObject itself. Conversely, global flags like
        # LOCALE _don't_ affect the code generation but _are_ needed by the
        # PatternObject.
        self.scanner = _regex.compile(None, (flags & GLOBAL_FLAGS) | version,
          code, {}, {}, {}, [], req_offset, req_chars, req_flags,
          len(patterns))

    def scan(self, string):
        result = []
        append = result.append
        match = self.scanner.scanner(string).match
        i = 0
        while True:
            m = match()
            if not m:
                break
            j = m.end()
            if i == j:
                break
            action = self.lexicon[m.lastindex - 1][1]
            if hasattr(action, '__call__'):
                self.match = m
                action = action(self, m.group())
            if action is not None:
                append(action)
            i = j

        return result, string[i : ]

# Get the known properties dict.
PROPERTIES = _regex.get_properties()

# Build the inverse of the properties dict.
PROPERTY_NAMES = {}
for prop_name, (prop_id, values) in PROPERTIES.items():
    name, prop_values = PROPERTY_NAMES.get(prop_id, ("", {}))
    name = max(name, prop_name, key=len)
    PROPERTY_NAMES[prop_id] = name, prop_values

    for val_name, val_id in values.items():
        prop_values[val_id] = max(prop_values.get(val_id, ""), val_name,
          key=len)

# Character escape sequences.
CHARACTER_ESCAPES = {
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
}

# Predefined character set escape sequences.
CHARSET_ESCAPES = {
    "d": lookup_property(None, "Digit", True),
    "D": lookup_property(None, "Digit", False),
    "h": lookup_property(None, "Blank", True),
    "s": lookup_property(None, "Space", True),
    "S": lookup_property(None, "Space", False),
    "w": lookup_property(None, "Word", True),
    "W": lookup_property(None, "Word", False),
}

# Positional escape sequences.
POSITION_ESCAPES = {
    "A": StartOfString(),
    "b": Boundary(),
    "B": Boundary(False),
    "K": Keep(),
    "m": StartOfWord(),
    "M": EndOfWord(),
    "Z": EndOfString(),
}

# Positional escape sequences when WORD flag set.
WORD_POSITION_ESCAPES = dict(POSITION_ESCAPES)
WORD_POSITION_ESCAPES.update({
    "b": DefaultBoundary(),
    "B": DefaultBoundary(False),
    "m": DefaultStartOfWord(),
    "M": DefaultEndOfWord(),
})

# Regex control verbs.
VERBS = {
    "FAIL": Failure(),
    "F": Failure(),
    "PRUNE": Prune(),
    "SKIP": Skip(),
}

# === NexusCore/openenv\Lib\site-packages\regex\test_regex.py ===
from weakref import proxy
import copy
import pickle
import regex
import string
import sys
import unittest

# String subclasses for issue 18468.
class StrSubclass(str):
    def __getitem__(self, index):
        return StrSubclass(super().__getitem__(index))

class BytesSubclass(bytes):
    def __getitem__(self, index):
        return BytesSubclass(super().__getitem__(index))

class RegexTests(unittest.TestCase):
    PATTERN_CLASS = "<class '_regex.Pattern'>"
    FLAGS_WITH_COMPILED_PAT = "cannot process flags argument with a compiled pattern"
    INVALID_GROUP_REF = "invalid group reference"
    MISSING_GT = "missing >"
    BAD_GROUP_NAME = "bad character in group name"
    MISSING_GROUP_NAME = "missing group name"
    MISSING_LT = "missing <"
    UNKNOWN_GROUP_I = "unknown group"
    UNKNOWN_GROUP = "unknown group"
    BAD_ESCAPE = r"bad escape \(end of pattern\)"
    BAD_OCTAL_ESCAPE = r"bad escape \\"
    BAD_SET = "unterminated character set"
    STR_PAT_ON_BYTES = "cannot use a string pattern on a bytes-like object"
    BYTES_PAT_ON_STR = "cannot use a bytes pattern on a string-like object"
    STR_PAT_BYTES_TEMPL = "expected str instance, bytes found"
    BYTES_PAT_STR_TEMPL = "expected a bytes-like object, str found"
    BYTES_PAT_UNI_FLAG = "cannot use UNICODE flag with a bytes pattern"
    MIXED_FLAGS = "ASCII, LOCALE and UNICODE flags are mutually incompatible"
    MISSING_RPAREN = "missing \\)"
    TRAILING_CHARS = "unbalanced parenthesis"
    BAD_CHAR_RANGE = "bad character range"
    NOTHING_TO_REPEAT = "nothing to repeat"
    MULTIPLE_REPEAT = "multiple repeat"
    OPEN_GROUP = "cannot refer to an open group"
    DUPLICATE_GROUP = "duplicate group"
    CANT_TURN_OFF = "bad inline flags: cannot turn flags off"
    UNDEF_CHAR_NAME = "undefined character name"

    def assertTypedEqual(self, actual, expect, msg=None):
        self.assertEqual(actual, expect, msg)

        def recurse(actual, expect):
            if isinstance(expect, (tuple, list)):
                for x, y in zip(actual, expect):
                    recurse(x, y)
            else:
                self.assertIs(type(actual), type(expect), msg)

        recurse(actual, expect)

    def test_weakref(self):
        s = 'QabbbcR'
        x = regex.compile('ab+c')
        y = proxy(x)
        if x.findall('QabbbcR') != y.findall('QabbbcR'):
            self.fail()

    def test_search_star_plus(self):
        self.assertEqual(regex.search('a*', 'xxx').span(0), (0, 0))
        self.assertEqual(regex.search('x*', 'axx').span(), (0, 0))
        self.assertEqual(regex.search('x+', 'axx').span(0), (1, 3))
        self.assertEqual(regex.search('x+', 'axx').span(), (1, 3))
        self.assertEqual(regex.search('x', 'aaa'), None)
        self.assertEqual(regex.match('a*', 'xxx').span(0), (0, 0))
        self.assertEqual(regex.match('a*', 'xxx').span(), (0, 0))
        self.assertEqual(regex.match('x*', 'xxxa').span(0), (0, 3))
        self.assertEqual(regex.match('x*', 'xxxa').span(), (0, 3))
        self.assertEqual(regex.match('a+', 'xxx'), None)

    def bump_num(self, matchobj):
        int_value = int(matchobj[0])
        return str(int_value + 1)

    def test_basic_regex_sub(self):
        self.assertEqual(regex.sub("(?i)b+", "x", "bbbb BBBB"), 'x x')
        self.assertEqual(regex.sub(r'\d+', self.bump_num, '08.2 -2 23x99y'),
          '9.3 -3 24x100y')
        self.assertEqual(regex.sub(r'\d+', self.bump_num, '08.2 -2 23x99y', 3),
          '9.3 -3 23x99y')

        self.assertEqual(regex.sub('.', lambda m: r"\n", 'x'), "\\n")
        self.assertEqual(regex.sub('.', r"\n", 'x'), "\n")

        self.assertEqual(regex.sub('(?P<a>x)', r'\g<a>\g<a>', 'xx'), 'xxxx')
        self.assertEqual(regex.sub('(?P<a>x)', r'\g<a>\g<1>', 'xx'), 'xxxx')
        self.assertEqual(regex.sub('(?P<unk>x)', r'\g<unk>\g<unk>', 'xx'),
          'xxxx')
        self.assertEqual(regex.sub('(?P<unk>x)', r'\g<1>\g<1>', 'xx'), 'xxxx')

        self.assertEqual(regex.sub('a', r'\t\n\v\r\f\a\b', 'a'), "\t\n\v\r\f\a\b")
        self.assertEqual(regex.sub('a', '\t\n\v\r\f\a', 'a'), "\t\n\v\r\f\a")
        self.assertEqual(regex.sub('a', '\t\n\v\r\f\a', 'a'), chr(9) + chr(10)
          + chr(11) + chr(13) + chr(12) + chr(7))

        self.assertEqual(regex.sub(r'^\s*', 'X', 'test'), 'Xtest')

        self.assertEqual(regex.sub(r"x", r"\x0A", "x"), "\n")
        self.assertEqual(regex.sub(r"x", r"\u000A", "x"), "\n")
        self.assertEqual(regex.sub(r"x", r"\U0000000A", "x"), "\n")
        self.assertEqual(regex.sub(r"x", r"\N{LATIN CAPITAL LETTER A}",
          "x"), "A")

        self.assertEqual(regex.sub(br"x", br"\x0A", b"x"), b"\n")

    def test_bug_449964(self):
        # Fails for group followed by other escape.
        self.assertEqual(regex.sub(r'(?P<unk>x)', r'\g<1>\g<1>\b', 'xx'),
          "xx\bxx\b")

    def test_bug_449000(self):
        # Test for sub() on escaped characters.
        self.assertEqual(regex.sub(r'\r\n', r'\n', 'abc\r\ndef\r\n'),
          "abc\ndef\n")
        self.assertEqual(regex.sub('\r\n', r'\n', 'abc\r\ndef\r\n'),
          "abc\ndef\n")
        self.assertEqual(regex.sub(r'\r\n', '\n', 'abc\r\ndef\r\n'),
          "abc\ndef\n")
        self.assertEqual(regex.sub('\r\n', '\n', 'abc\r\ndef\r\n'),
          "abc\ndef\n")

    def test_bug_1661(self):
        # Verify that flags do not get silently ignored with compiled patterns
        pattern = regex.compile('.')
        self.assertRaisesRegex(ValueError, self.FLAGS_WITH_COMPILED_PAT,
          lambda: regex.match(pattern, 'A', regex.I))
        self.assertRaisesRegex(ValueError, self.FLAGS_WITH_COMPILED_PAT,
          lambda: regex.search(pattern, 'A', regex.I))
        self.assertRaisesRegex(ValueError, self.FLAGS_WITH_COMPILED_PAT,
          lambda: regex.findall(pattern, 'A', regex.I))
        self.assertRaisesRegex(ValueError, self.FLAGS_WITH_COMPILED_PAT,
          lambda: regex.compile(pattern, regex.I))

    def test_bug_3629(self):
        # A regex that triggered a bug in the sre-code validator
        self.assertEqual(repr(type(regex.compile("(?P<quote>)(?(quote))"))),
          self.PATTERN_CLASS)

    def test_sub_template_numeric_escape(self):
        # Bug 776311 and friends.
        self.assertEqual(regex.sub('x', r'\0', 'x'), "\0")
        self.assertEqual(regex.sub('x', r'\000', 'x'), "\000")
        self.assertEqual(regex.sub('x', r'\001', 'x'), "\001")
        self.assertEqual(regex.sub('x', r'\008', 'x'), "\0" + "8")
        self.assertEqual(regex.sub('x', r'\009', 'x'), "\0" + "9")
        self.assertEqual(regex.sub('x', r'\111', 'x'), "\111")
        self.assertEqual(regex.sub('x', r'\117', 'x'), "\117")

        self.assertEqual(regex.sub('x', r'\1111', 'x'), "\1111")
        self.assertEqual(regex.sub('x', r'\1111', 'x'), "\111" + "1")

        self.assertEqual(regex.sub('x', r'\00', 'x'), '\x00')
        self.assertEqual(regex.sub('x', r'\07', 'x'), '\x07')
        self.assertEqual(regex.sub('x', r'\08', 'x'), "\0" + "8")
        self.assertEqual(regex.sub('x', r'\09', 'x'), "\0" + "9")
        self.assertEqual(regex.sub('x', r'\0a', 'x'), "\0" + "a")

        self.assertEqual(regex.sub('x', r'\400', 'x'), "\u0100")
        self.assertEqual(regex.sub('x', r'\777', 'x'), "\u01FF")
        self.assertEqual(regex.sub(b'x', br'\400', b'x'), b"\x00")
        self.assertEqual(regex.sub(b'x', br'\777', b'x'), b"\xFF")

        self.assertRaisesRegex(regex.error, self.INVALID_GROUP_REF, lambda:
          regex.sub('x', r'\1', 'x'))
        self.assertRaisesRegex(regex.error, self.INVALID_GROUP_REF, lambda:
          regex.sub('x', r'\8', 'x'))
        self.assertRaisesRegex(regex.error, self.INVALID_GROUP_REF, lambda:
          regex.sub('x', r'\9', 'x'))
        self.assertRaisesRegex(regex.error, self.INVALID_GROUP_REF, lambda:
          regex.sub('x', r'\11', 'x'))
        self.assertRaisesRegex(regex.error, self.INVALID_GROUP_REF, lambda:
          regex.sub('x', r'\18', 'x'))
        self.assertRaisesRegex(regex.error, self.INVALID_GROUP_REF, lambda:
          regex.sub('x', r'\1a', 'x'))
        self.assertRaisesRegex(regex.error, self.INVALID_GROUP_REF, lambda:
          regex.sub('x', r'\90', 'x'))
        self.assertRaisesRegex(regex.error, self.INVALID_GROUP_REF, lambda:
          regex.sub('x', r'\99', 'x'))
        self.assertRaisesRegex(regex.error, self.INVALID_GROUP_REF, lambda:
          regex.sub('x', r'\118', 'x')) # r'\11' + '8'
        self.assertRaisesRegex(regex.error, self.INVALID_GROUP_REF, lambda:
          regex.sub('x', r'\11a', 'x'))
        self.assertRaisesRegex(regex.error, self.INVALID_GROUP_REF, lambda:
          regex.sub('x', r'\181', 'x')) # r'\18' + '1'
        self.assertRaisesRegex(regex.error, self.INVALID_GROUP_REF, lambda:
          regex.sub('x', r'\800', 'x')) # r'\80' + '0'

        # In Python 2.3 (etc), these loop endlessly in sre_parser.py.
        self.assertEqual(regex.sub('(((((((((((x)))))))))))', r'\11', 'x'),
          'x')
        self.assertEqual(regex.sub('((((((((((y))))))))))(.)', r'\118', 'xyz'),
          'xz8')
        self.assertEqual(regex.sub('((((((((((y))))))))))(.)', r'\11a', 'xyz'),
          'xza')

    def test_qualified_re_sub(self):
        self.assertEqual(regex.sub('a', 'b', 'aaaaa'), 'bbbbb')
        self.assertEqual(regex.sub('a', 'b', 'aaaaa', 1), 'baaaa')

    def test_bug_114660(self):
        self.assertEqual(regex.sub(r'(\S)\s+(\S)', r'\1 \2', 'hello  there'),
          'hello there')

    def test_bug_462270(self):
        # Test for empty sub() behaviour, see SF bug #462270
        if sys.version_info >= (3, 7, 0):
            self.assertEqual(regex.sub('(?V0)x*', '-', 'abxd'), '-a-b--d-')
        else:
            self.assertEqual(regex.sub('(?V0)x*', '-', 'abxd'), '-a-b-d-')
        self.assertEqual(regex.sub('(?V1)x*', '-', 'abxd'), '-a-b--d-')
        self.assertEqual(regex.sub('x+', '-', 'abxd'), 'ab-d')

    def test_bug_14462(self):
        # chr(255) is a valid identifier in Python 3.
        group_name = '\xFF'
        self.assertEqual(regex.search(r'(?P<' + group_name + '>a)',
          'abc').group(group_name), 'a')

    def test_symbolic_refs(self):
        self.assertRaisesRegex(regex.error, self.MISSING_GT, lambda:
          regex.sub('(?P<a>x)', r'\g<a', 'xx'))
        self.assertRaisesRegex(regex.error, self.MISSING_GROUP_NAME, lambda:
          regex.sub('(?P<a>x)', r'\g<', 'xx'))
        self.assertRaisesRegex(regex.error, self.MISSING_LT, lambda:
          regex.sub('(?P<a>x)', r'\g', 'xx'))
        self.assertRaisesRegex(regex.error, self.BAD_GROUP_NAME, lambda:
          regex.sub('(?P<a>x)', r'\g<a a>', 'xx'))
        self.assertRaisesRegex(regex.error, self.BAD_GROUP_NAME, lambda:
          regex.sub('(?P<a>x)', r'\g<1a1>', 'xx'))
        self.assertRaisesRegex(IndexError, self.UNKNOWN_GROUP_I, lambda:
          regex.sub('(?P<a>x)', r'\g<ab>', 'xx'))

        # The new behaviour of unmatched but valid groups is to treat them like
        # empty matches in the replacement template, like in Perl.
        self.assertEqual(regex.sub('(?P<a>x)|(?P<b>y)', r'\g<b>', 'xx'), '')
        self.assertEqual(regex.sub('(?P<a>x)|(?P<b>y)', r'\2', 'xx'), '')

        # The old behaviour was to raise it as an IndexError.
        self.assertRaisesRegex(regex.error, self.BAD_GROUP_NAME, lambda:
          regex.sub('(?P<a>x)', r'\g<-1>', 'xx'))

    def test_re_subn(self):
        self.assertEqual(regex.subn("(?i)b+", "x", "bbbb BBBB"), ('x x', 2))
        self.assertEqual(regex.subn("b+", "x", "bbbb BBBB"), ('x BBBB', 1))
        self.assertEqual(regex.subn("b+", "x", "xyz"), ('xyz', 0))
        self.assertEqual(regex.subn("b*", "x", "xyz"), ('xxxyxzx', 4))
        self.assertEqual(regex.subn("b*", "x", "xyz", 2), ('xxxyz', 2))

    def test_re_split(self):
        self.assertEqual(regex.split(":", ":a:b::c"), ['', 'a', 'b', '', 'c'])
        if sys.version_info >= (3, 7, 0):
            self.assertEqual(regex.split(":*", ":a:b::c"), ['', '', 'a', '',
              'b', '', 'c', ''])
            self.assertEqual(regex.split("(:*)", ":a:b::c"), ['', ':', '', '',
              'a', ':', '', '', 'b', '::', '', '', 'c', '', ''])
            self.assertEqual(regex.split("(?::*)", ":a:b::c"), ['', '', 'a',
              '', 'b', '', 'c', ''])
            self.assertEqual(regex.split("(:)*", ":a:b::c"), ['', ':', '',
              None, 'a', ':', '', None, 'b', ':', '', None, 'c', None, ''])
        else:
            self.assertEqual(regex.split(":*", ":a:b::c"), ['', 'a', 'b', 'c'])
            self.assertEqual(regex.split("(:*)", ":a:b::c"), ['', ':', 'a',
              ':', 'b', '::', 'c'])
            self.assertEqual(regex.split("(?::*)", ":a:b::c"), ['', 'a', 'b',
              'c'])
            self.assertEqual(regex.split("(:)*", ":a:b::c"), ['', ':', 'a',
              ':', 'b', ':', 'c'])
        self.assertEqual(regex.split("([b:]+)", ":a:b::c"), ['', ':', 'a',
          ':b::', 'c'])
        self.assertEqual(regex.split("(b)|(:+)", ":a:b::c"), ['', None, ':',
          'a', None, ':', '', 'b', None, '', None, '::', 'c'])
        self.assertEqual(regex.split("(?:b)|(?::+)", ":a:b::c"), ['', 'a', '',
          '', 'c'])

        self.assertEqual(regex.split("x", "xaxbxc"), ['', 'a', 'b', 'c'])
        self.assertEqual([m for m in regex.splititer("x", "xaxbxc")], ['', 'a',
          'b', 'c'])

        self.assertEqual(regex.split("(?r)x", "xaxbxc"), ['c', 'b', 'a', ''])
        self.assertEqual([m for m in regex.splititer("(?r)x", "xaxbxc")], ['c',
          'b', 'a', ''])

        self.assertEqual(regex.split("(x)|(y)", "xaxbxc"), ['', 'x', None, 'a',
          'x', None, 'b', 'x', None, 'c'])
        self.assertEqual([m for m in regex.splititer("(x)|(y)", "xaxbxc")],
          ['', 'x', None, 'a', 'x', None, 'b', 'x', None, 'c'])

        self.assertEqual(regex.split("(?r)(x)|(y)", "xaxbxc"), ['c', 'x', None,
          'b', 'x', None, 'a', 'x', None, ''])
        self.assertEqual([m for m in regex.splititer("(?r)(x)|(y)", "xaxbxc")],
          ['c', 'x', None, 'b', 'x', None, 'a', 'x', None, ''])

        self.assertEqual(regex.split(r"(?V1)\b", "a b c"), ['', 'a', ' ', 'b',
          ' ', 'c', ''])
        self.assertEqual(regex.split(r"(?V1)\m", "a b c"), ['', 'a ', 'b ',
          'c'])
        self.assertEqual(regex.split(r"(?V1)\M", "a b c"), ['a', ' b', ' c',
          ''])

    def test_qualified_re_split(self):
        self.assertEqual(regex.split(":", ":a:b::c", 2), ['', 'a', 'b::c'])
        self.assertEqual(regex.split(':', 'a:b:c:d', 2), ['a', 'b', 'c:d'])
        self.assertEqual(regex.split("(:)", ":a:b::c", 2), ['', ':', 'a', ':',
          'b::c'])

        if sys.version_info >= (3, 7, 0):
            self.assertEqual(regex.split("(:*)", ":a:b::c", 2), ['', ':', '',
              '', 'a:b::c'])
        else:
            self.assertEqual(regex.split("(:*)", ":a:b::c", 2), ['', ':', 'a',
              ':', 'b::c'])

    def test_re_findall(self):
        self.assertEqual(regex.findall(":+", "abc"), [])
        self.assertEqual(regex.findall(":+", "a:b::c:::d"), [':', '::', ':::'])
        self.assertEqual(regex.findall("(:+)", "a:b::c:::d"), [':', '::',
          ':::'])
        self.assertEqual(regex.findall("(:)(:*)", "a:b::c:::d"), [(':', ''),
          (':', ':'), (':', '::')])

        self.assertEqual(regex.findall(r"\((?P<test>.{0,5}?TEST)\)",
          "(MY TEST)"), ["MY TEST"])
        self.assertEqual(regex.findall(r"\((?P<test>.{0,3}?TEST)\)",
          "(MY TEST)"), ["MY TEST"])
        self.assertEqual(regex.findall(r"\((?P<test>.{0,3}?T)\)", "(MY T)"),
          ["MY T"])

        self.assertEqual(regex.findall(r"[^a]{2}[A-Z]", "\n  S"), ['  S'])
        self.assertEqual(regex.findall(r"[^a]{2,3}[A-Z]", "\n  S"), ['\n  S'])
        self.assertEqual(regex.findall(r"[^a]{2,3}[A-Z]", "\n   S"), ['   S'])

        self.assertEqual(regex.findall(r"X(Y[^Y]+?){1,2}( |Q)+DEF",
          "XYABCYPPQ\nQ DEF"), [('YPPQ\n', ' ')])

        self.assertEqual(regex.findall(r"(\nTest(\n+.+?){0,2}?)?\n+End",
          "\nTest\nxyz\nxyz\nEnd"), [('\nTest\nxyz\nxyz', '\nxyz')])

    def test_bug_117612(self):
        self.assertEqual(regex.findall(r"(a|(b))", "aba"), [('a', ''), ('b',
          'b'), ('a', '')])

    def test_re_match(self):
        self.assertEqual(regex.match('a', 'a')[:], ('a',))
        self.assertEqual(regex.match('(a)', 'a')[:], ('a', 'a'))
        self.assertEqual(regex.match(r'(a)', 'a')[0], 'a')
        self.assertEqual(regex.match(r'(a)', 'a')[1], 'a')
        self.assertEqual(regex.match(r'(a)', 'a').group(1, 1), ('a', 'a'))

        pat = regex.compile('((a)|(b))(c)?')
        self.assertEqual(pat.match('a')[:], ('a', 'a', 'a', None, None))
        self.assertEqual(pat.match('b')[:], ('b', 'b', None, 'b', None))
        self.assertEqual(pat.match('ac')[:], ('ac', 'a', 'a', None, 'c'))
        self.assertEqual(pat.match('bc')[:], ('bc', 'b', None, 'b', 'c'))
        self.assertEqual(pat.match('bc')[:], ('bc', 'b', None, 'b', 'c'))

        # A single group.
        m = regex.match('(a)', 'a')
        self.assertEqual(m.group(), 'a')
        self.assertEqual(m.group(0), 'a')
        self.assertEqual(m.group(1), 'a')
        self.assertEqual(m.group(1, 1), ('a', 'a'))

        pat = regex.compile('(?:(?P<a1>a)|(?P<b2>b))(?P<c3>c)?')
        self.assertEqual(pat.match('a').group(1, 2, 3), ('a', None, None))
        self.assertEqual(pat.match('b').group('a1', 'b2', 'c3'), (None, 'b',
          None))
        self.assertEqual(pat.match('ac').group(1, 'b2', 3), ('a', None, 'c'))

    def test_re_groupref_exists(self):
        self.assertEqual(regex.match(r'^(\()?([^()]+)(?(1)\))$', '(a)')[:],
          ('(a)', '(', 'a'))
        self.assertEqual(regex.match(r'^(\()?([^()]+)(?(1)\))$', 'a')[:], ('a',
          None, 'a'))
        self.assertEqual(regex.match(r'^(\()?([^()]+)(?(1)\))$', 'a)'), None)
        self.assertEqual(regex.match(r'^(\()?([^()]+)(?(1)\))$', '(a'), None)
        self.assertEqual(regex.match('^(?:(a)|c)((?(1)b|d))$', 'ab')[:], ('ab',
          'a', 'b'))
        self.assertEqual(regex.match('^(?:(a)|c)((?(1)b|d))$', 'cd')[:], ('cd',
          None, 'd'))
        self.assertEqual(regex.match('^(?:(a)|c)((?(1)|d))$', 'cd')[:], ('cd',
          None, 'd'))
        self.assertEqual(regex.match('^(?:(a)|c)((?(1)|d))$', 'a')[:], ('a',
          'a', ''))

        # Tests for bug #1177831: exercise groups other than the first group.
        p = regex.compile('(?P<g1>a)(?P<g2>b)?((?(g2)c|d))')
        self.assertEqual(p.match('abc')[:], ('abc', 'a', 'b', 'c'))
        self.assertEqual(p.match('ad')[:], ('ad', 'a', None, 'd'))
        self.assertEqual(p.match('abd'), None)
        self.assertEqual(p.match('ac'), None)

    def test_re_groupref(self):
        self.assertEqual(regex.match(r'^(\|)?([^()]+)\1$', '|a|')[:], ('|a|',
          '|', 'a'))
        self.assertEqual(regex.match(r'^(\|)?([^()]+)\1?$', 'a')[:], ('a',
          None, 'a'))
        self.assertEqual(regex.match(r'^(\|)?([^()]+)\1$', 'a|'), None)
        self.assertEqual(regex.match(r'^(\|)?([^()]+)\1$', '|a'), None)
        self.assertEqual(regex.match(r'^(?:(a)|c)(\1)$', 'aa')[:], ('aa', 'a',
          'a'))
        self.assertEqual(regex.match(r'^(?:(a)|c)(\1)?$', 'c')[:], ('c', None,
          None))

        self.assertEqual(regex.findall(r"(?i)(.{1,40}?),(.{1,40}?)(?:;)+(.{1,80}).{1,40}?\3(\ |;)+(.{1,80}?)\1",
          "TEST, BEST; LEST ; Lest 123 Test, Best"), [('TEST', ' BEST',
          ' LEST', ' ', '123 ')])

    def test_groupdict(self):
        self.assertEqual(regex.match('(?P<first>first) (?P<second>second)',
          'first second').groupdict(), {'first': 'first', 'second': 'second'})

    def test_expand(self):
        self.assertEqual(regex.match("(?P<first>first) (?P<second>second)",
          "first second").expand(r"\2 \1 \g<second> \g<first>"),
          'second first second first')

    def test_repeat_minmax(self):
        self.assertEqual(regex.match(r"^(\w){1}$", "abc"), None)
        self.assertEqual(regex.match(r"^(\w){1}?$", "abc"), None)
        self.assertEqual(regex.match(r"^(\w){1,2}$", "abc"), None)
        self.assertEqual(regex.match(r"^(\w){1,2}?$", "abc"), None)

        self.assertEqual(regex.match(r"^(\w){3}$", "abc")[1], 'c')
        self.assertEqual(regex.match(r"^(\w){1,3}$", "abc")[1], 'c')
        self.assertEqual(regex.match(r"^(\w){1,4}$", "abc")[1], 'c')
        self.assertEqual(regex.match(r"^(\w){3,4}?$", "abc")[1], 'c')
        self.assertEqual(regex.match(r"^(\w){3}?$", "abc")[1], 'c')
        self.assertEqual(regex.match(r"^(\w){1,3}?$", "abc")[1], 'c')
        self.assertEqual(regex.match(r"^(\w){1,4}?$", "abc")[1], 'c')
        self.assertEqual(regex.match(r"^(\w){3,4}?$", "abc")[1], 'c')

        self.assertEqual(regex.match("^x{1}$", "xxx"), None)
        self.assertEqual(regex.match("^x{1}?$", "xxx"), None)
        self.assertEqual(regex.match("^x{1,2}$", "xxx"), None)
        self.assertEqual(regex.match("^x{1,2}?$", "xxx"), None)

        self.assertEqual(regex.match("^x{1}", "xxx")[0], 'x')
        self.assertEqual(regex.match("^x{1}?", "xxx")[0], 'x')
        self.assertEqual(regex.match("^x{0,1}", "xxx")[0], 'x')
        self.assertEqual(regex.match("^x{0,1}?", "xxx")[0], '')

        self.assertEqual(bool(regex.match("^x{3}$", "xxx")), True)
        self.assertEqual(bool(regex.match("^x{1,3}$", "xxx")), True)
        self.assertEqual(bool(regex.match("^x{1,4}$", "xxx")), True)
        self.assertEqual(bool(regex.match("^x{3,4}?$", "xxx")), True)
        self.assertEqual(bool(regex.match("^x{3}?$", "xxx")), True)
        self.assertEqual(bool(regex.match("^x{1,3}?$", "xxx")), True)
        self.assertEqual(bool(regex.match("^x{1,4}?$", "xxx")), True)
        self.assertEqual(bool(regex.match("^x{3,4}?$", "xxx")), True)

        self.assertEqual(regex.match("^x{}$", "xxx"), None)
        self.assertEqual(bool(regex.match("^x{}$", "x{}")), True)

    def test_getattr(self):
        self.assertEqual(regex.compile("(?i)(a)(b)").pattern, '(?i)(a)(b)')
        self.assertEqual(regex.compile("(?i)(a)(b)").flags, regex.I | regex.U |
          regex.DEFAULT_VERSION)
        self.assertEqual(regex.compile(b"(?i)(a)(b)").flags, regex.A | regex.I
          | regex.DEFAULT_VERSION)
        self.assertEqual(regex.compile("(?i)(a)(b)").groups, 2)
        self.assertEqual(regex.compile("(?i)(a)(b)").groupindex, {})

        self.assertEqual(regex.compile("(?i)(?P<first>a)(?P<other>b)").groupindex,
          {'first': 1, 'other': 2})

        self.assertEqual(regex.match("(a)", "a").pos, 0)
        self.assertEqual(regex.match("(a)", "a").endpos, 1)

        self.assertEqual(regex.search("b(c)", "abcdef").pos, 0)
        self.assertEqual(regex.search("b(c)", "abcdef").endpos, 6)
        self.assertEqual(regex.search("b(c)", "abcdef").span(), (1, 3))
        self.assertEqual(regex.search("b(c)", "abcdef").span(1), (2, 3))

        self.assertEqual(regex.match("(a)", "a").string, 'a')
        self.assertEqual(regex.match("(a)", "a").regs, ((0, 1), (0, 1)))
        self.assertEqual(repr(type(regex.match("(a)", "a").re)),
          self.PATTERN_CLASS)

        # Issue 14260.
        p = regex.compile(r'abc(?P<n>def)')
        p.groupindex["n"] = 0
        self.assertEqual(p.groupindex["n"], 1)

    def test_special_escapes(self):
        self.assertEqual(regex.search(r"\b(b.)\b", "abcd abc bcd bx")[1], 'bx')
        self.assertEqual(regex.search(r"\B(b.)\B", "abc bcd bc abxd")[1], 'bx')
        self.assertEqual(regex.search(br"\b(b.)\b", b"abcd abc bcd bx",
          regex.LOCALE)[1], b'bx')
        self.assertEqual(regex.search(br"\B(b.)\B", b"abc bcd bc abxd",
          regex.LOCALE)[1], b'bx')
        self.assertEqual(regex.search(r"\b(b.)\b", "abcd abc bcd bx",
          regex.UNICODE)[1], 'bx')
        self.assertEqual(regex.search(r"\B(b.)\B", "abc bcd bc abxd",
          regex.UNICODE)[1], 'bx')

        self.assertEqual(regex.search(r"^abc$", "\nabc\n", regex.M)[0], 'abc')
        self.assertEqual(regex.search(r"^\Aabc\Z$", "abc", regex.M)[0], 'abc')
        self.assertEqual(regex.search(r"^\Aabc\Z$", "\nabc\n", regex.M), None)

        self.assertEqual(regex.search(br"\b(b.)\b", b"abcd abc bcd bx")[1],
          b'bx')
        self.assertEqual(regex.search(br"\B(b.)\B", b"abc bcd bc abxd")[1],
          b'bx')
        self.assertEqual(regex.search(br"^abc$", b"\nabc\n", regex.M)[0],
          b'abc')
        self.assertEqual(regex.search(br"^\Aabc\Z$", b"abc", regex.M)[0],
          b'abc')
        self.assertEqual(regex.search(br"^\Aabc\Z$", b"\nabc\n", regex.M),
          None)

        self.assertEqual(regex.search(r"\d\D\w\W\s\S", "1aa! a")[0], '1aa! a')
        self.assertEqual(regex.search(br"\d\D\w\W\s\S", b"1aa! a",
          regex.LOCALE)[0], b'1aa! a')
        self.assertEqual(regex.search(r"\d\D\w\W\s\S", "1aa! a",
          regex.UNICODE)[0], '1aa! a')

    def test_bigcharset(self):
        self.assertEqual(regex.match(r"([\u2222\u2223])", "\u2222")[1],
          '\u2222')
        self.assertEqual(regex.match(r"([\u2222\u2223])", "\u2222",
          regex.UNICODE)[1], '\u2222')
        self.assertEqual("".join(regex.findall(".",
          "e\xe8\xe9\xea\xeb\u0113\u011b\u0117", flags=regex.UNICODE)),
          'e\xe8\xe9\xea\xeb\u0113\u011b\u0117')
        self.assertEqual("".join(regex.findall(r"[e\xe8\xe9\xea\xeb\u0113\u011b\u0117]",
          "e\xe8\xe9\xea\xeb\u0113\u011b\u0117", flags=regex.UNICODE)),
          'e\xe8\xe9\xea\xeb\u0113\u011b\u0117')
        self.assertEqual("".join(regex.findall(r"e|\xe8|\xe9|\xea|\xeb|\u0113|\u011b|\u0117",
          "e\xe8\xe9\xea\xeb\u0113\u011b\u0117", flags=regex.UNICODE)),
          'e\xe8\xe9\xea\xeb\u0113\u011b\u0117')

    def test_anyall(self):
        self.assertEqual(regex.match("a.b", "a\nb", regex.DOTALL)[0], "a\nb")
        self.assertEqual(regex.match("a.*b", "a\n\nb", regex.DOTALL)[0],
          "a\n\nb")

    def test_non_consuming(self):
        self.assertEqual(regex.match(r"(a(?=\s[^a]))", "a b")[1], 'a')
        self.assertEqual(regex.match(r"(a(?=\s[^a]*))", "a b")[1], 'a')
        self.assertEqual(regex.match(r"(a(?=\s[abc]))", "a b")[1], 'a')
        self.assertEqual(regex.match(r"(a(?=\s[abc]*))", "a bc")[1], 'a')
        self.assertEqual(regex.match(r"(a)(?=\s\1)", "a a")[1], 'a')
        self.assertEqual(regex.match(r"(a)(?=\s\1*)", "a aa")[1], 'a')
        self.assertEqual(regex.match(r"(a)(?=\s(abc|a))", "a a")[1], 'a')

        self.assertEqual(regex.match(r"(a(?!\s[^a]))", "a a")[1], 'a')
        self.assertEqual(regex.match(r"(a(?!\s[abc]))", "a d")[1], 'a')
        self.assertEqual(regex.match(r"(a)(?!\s\1)", "a b")[1], 'a')
        self.assertEqual(regex.match(r"(a)(?!\s(abc|a))", "a b")[1], 'a')

    def test_ignore_case(self):
        self.assertEqual(regex.match("abc", "ABC", regex.I)[0], 'ABC')
        self.assertEqual(regex.match(b"abc", b"ABC", regex.I)[0], b'ABC')

        self.assertEqual(regex.match(r"(a\s[^a]*)", "a bb", regex.I)[1],
          'a bb')
        self.assertEqual(regex.match(r"(a\s[abc])", "a b", regex.I)[1], 'a b')
        self.assertEqual(regex.match(r"(a\s[abc]*)", "a bb", regex.I)[1],
          'a bb')
        self.assertEqual(regex.match(r"((a)\s\2)", "a a", regex.I)[1], 'a a')
        self.assertEqual(regex.match(r"((a)\s\2*)", "a aa", regex.I)[1],
          'a aa')
        self.assertEqual(regex.match(r"((a)\s(abc|a))", "a a", regex.I)[1],
          'a a')
        self.assertEqual(regex.match(r"((a)\s(abc|a)*)", "a aa", regex.I)[1],
          'a aa')

        # Issue 3511.
        self.assertEqual(regex.match(r"[Z-a]", "_").span(), (0, 1))
        self.assertEqual(regex.match(r"(?i)[Z-a]", "_").span(), (0, 1))

        self.assertEqual(bool(regex.match(r"(?i)nao", "nAo")), True)
        self.assertEqual(bool(regex.match(r"(?i)n\xE3o", "n\xC3o")), True)
        self.assertEqual(bool(regex.match(r"(?i)n\xE3o", "N\xC3O")), True)
        self.assertEqual(bool(regex.match(r"(?i)s", "\u017F")), True)

    def test_case_folding(self):
        self.assertEqual(regex.search(r"(?fi)ss", "SS").span(), (0, 2))
        self.assertEqual(regex.search(r"(?fi)SS", "ss").span(), (0, 2))
        self.assertEqual(regex.search(r"(?fi)SS",
          "\N{LATIN SMALL LETTER SHARP S}").span(), (0, 1))
        self.assertEqual(regex.search(r"(?fi)\N{LATIN SMALL LETTER SHARP S}",
          "SS").span(), (0, 2))

        self.assertEqual(regex.search(r"(?fi)\N{LATIN SMALL LIGATURE ST}",
          "ST").span(), (0, 2))
        self.assertEqual(regex.search(r"(?fi)ST",
          "\N{LATIN SMALL LIGATURE ST}").span(), (0, 1))
        self.assertEqual(regex.search(r"(?fi)ST",
          "\N{LATIN SMALL LIGATURE LONG S T}").span(), (0, 1))

        self.assertEqual(regex.search(r"(?fi)SST",
          "\N{LATIN SMALL LETTER SHARP S}t").span(), (0, 2))
        self.assertEqual(regex.search(r"(?fi)SST",
          "s\N{LATIN SMALL LIGATURE LONG S T}").span(), (0, 2))
        self.assertEqual(regex.search(r"(?fi)SST",
          "s\N{LATIN SMALL LIGATURE ST}").span(), (0, 2))
        self.assertEqual(regex.search(r"(?fi)\N{LATIN SMALL LIGATURE ST}",
          "SST").span(), (1, 3))
        self.assertEqual(regex.search(r"(?fi)SST",
          "s\N{LATIN SMALL LIGATURE ST}").span(), (0, 2))

        self.assertEqual(regex.search(r"(?fi)FFI",
          "\N{LATIN SMALL LIGATURE FFI}").span(), (0, 1))
        self.assertEqual(regex.search(r"(?fi)FFI",
          "\N{LATIN SMALL LIGATURE FF}i").span(), (0, 2))
        self.assertEqual(regex.search(r"(?fi)FFI",
          "f\N{LATIN SMALL LIGATURE FI}").span(), (0, 2))
        self.assertEqual(regex.search(r"(?fi)\N{LATIN SMALL LIGATURE FFI}",
          "FFI").span(), (0, 3))
        self.assertEqual(regex.search(r"(?fi)\N{LATIN SMALL LIGATURE FF}i",
          "FFI").span(), (0, 3))
        self.assertEqual(regex.search(r"(?fi)f\N{LATIN SMALL LIGATURE FI}",
          "FFI").span(), (0, 3))

        sigma = "\u03A3\u03C3\u03C2"
        for ch1 in sigma:
            for ch2 in sigma:
                if not regex.match(r"(?fi)" + ch1, ch2):
                    self.fail()

        self.assertEqual(bool(regex.search(r"(?iV1)ff", "\uFB00\uFB01")),
          True)
        self.assertEqual(bool(regex.search(r"(?iV1)ff", "\uFB01\uFB00")),
          True)
        self.assertEqual(bool(regex.search(r"(?iV1)fi", "\uFB00\uFB01")),
          True)
        self.assertEqual(bool(regex.search(r"(?iV1)fi", "\uFB01\uFB00")),
          True)
        self.assertEqual(bool(regex.search(r"(?iV1)fffi", "\uFB00\uFB01")),
          True)
        self.assertEqual(bool(regex.search(r"(?iV1)f\uFB03",
          "\uFB00\uFB01")), True)
        self.assertEqual(bool(regex.search(r"(?iV1)ff", "\uFB00\uFB01")),
          True)
        self.assertEqual(bool(regex.search(r"(?iV1)fi", "\uFB00\uFB01")),
          True)
        self.assertEqual(bool(regex.search(r"(?iV1)fffi", "\uFB00\uFB01")),
          True)
        self.assertEqual(bool(regex.search(r"(?iV1)f\uFB03",
          "\uFB00\uFB01")), True)
        self.assertEqual(bool(regex.search(r"(?iV1)f\uFB01", "\uFB00i")),
          True)
        self.assertEqual(bool(regex.search(r"(?iV1)f\uFB01", "\uFB00i")),
          True)

        self.assertEqual(regex.findall(r"(?iV0)\m(?:word){e<=3}\M(?<!\m(?:word){e<=1}\M)",
          "word word2 word word3 word word234 word23 word"), ["word234",
          "word23"])
        self.assertEqual(regex.findall(r"(?iV1)\m(?:word){e<=3}\M(?<!\m(?:word){e<=1}\M)",
          "word word2 word word3 word word234 word23 word"), ["word234",
          "word23"])

        self.assertEqual(regex.search(r"(?fi)a\N{LATIN SMALL LIGATURE FFI}ne",
          "  affine  ").span(), (2, 8))
        self.assertEqual(regex.search(r"(?fi)a(?:\N{LATIN SMALL LIGATURE FFI}|x)ne",
           "  affine  ").span(), (2, 8))
        self.assertEqual(regex.search(r"(?fi)a(?:\N{LATIN SMALL LIGATURE FFI}|xy)ne",
           "  affine  ").span(), (2, 8))
        self.assertEqual(regex.search(r"(?fi)a\L<options>ne", "affine",
          options=["\N{LATIN SMALL LIGATURE FFI}"]).span(), (0, 6))
        self.assertEqual(regex.search(r"(?fi)a\L<options>ne",
          "a\N{LATIN SMALL LIGATURE FFI}ne", options=["ffi"]).span(), (0, 4))

    def test_category(self):
        self.assertEqual(regex.match(r"(\s)", " ")[1], ' ')

    def test_not_literal(self):
        self.assertEqual(regex.search(r"\s([^a])", " b")[1], 'b')
        self.assertEqual(regex.search(r"\s([^a]*)", " bb")[1], 'bb')

    def test_search_coverage(self):
        self.assertEqual(regex.search(r"\s(b)", " b")[1], 'b')
        self.assertEqual(regex.search(r"a\s", "a ")[0], 'a ')

    def test_re_escape(self):
        p = ""
        self.assertEqual(regex.escape(p), p)
        for i in range(0, 256):
            p += chr(i)
            self.assertEqual(bool(regex.match(regex.escape(chr(i)), chr(i))),
              True)
            self.assertEqual(regex.match(regex.escape(chr(i)), chr(i)).span(),
              (0, 1))

        pat = regex.compile(regex.escape(p))
        self.assertEqual(pat.match(p).span(), (0, 256))

    def test_re_escape_byte(self):
        p = b""
        self.assertEqual(regex.escape(p), p)
        for i in range(0, 256):
            b = bytes([i])
            p += b
            self.assertEqual(bool(regex.match(regex.escape(b), b)), True)
            self.assertEqual(regex.match(regex.escape(b), b).span(), (0, 1))

        pat = regex.compile(regex.escape(p))
        self.assertEqual(pat.match(p).span(), (0, 256))

    def test_constants(self):
        if regex.I != regex.IGNORECASE:
            self.fail()
        if regex.L != regex.LOCALE:
            self.fail()
        if regex.M != regex.MULTILINE:
            self.fail()
        if regex.S != regex.DOTALL:
            self.fail()
        if regex.X != regex.VERBOSE:
            self.fail()

    def test_flags(self):
        for flag in [regex.I, regex.M, regex.X, regex.S, regex.L]:
            self.assertEqual(repr(type(regex.compile('^pattern$', flag))),
              self.PATTERN_CLASS)

    def test_sre_character_literals(self):
        for i in [0, 8, 16, 32, 64, 127, 128, 255]:
            self.assertEqual(bool(regex.match(r"\%03o" % i, chr(i))), True)
            self.assertEqual(bool(regex.match(r"\%03o0" % i, chr(i) + "0")),
              True)
            self.assertEqual(bool(regex.match(r"\%03o8" % i, chr(i) + "8")),
              True)
            self.assertEqual(bool(regex.match(r"\x%02x" % i, chr(i))), True)
            self.assertEqual(bool(regex.match(r"\x%02x0" % i, chr(i) + "0")),
              True)
            self.assertEqual(bool(regex.match(r"\x%02xz" % i, chr(i) + "z")),
              True)

        self.assertRaisesRegex(regex.error, self.INVALID_GROUP_REF, lambda:
          regex.match(r"\911", ""))

    def test_sre_character_class_literals(self):
        for i in [0, 8, 16, 32, 64, 127, 128, 255]:
            self.assertEqual(bool(regex.match(r"[\%03o]" % i, chr(i))), True)
            self.assertEqual(bool(regex.match(r"[\%03o0]" % i, chr(i))), True)
            self.assertEqual(bool(regex.match(r"[\%03o8]" % i, chr(i))), True)
            self.assertEqual(bool(regex.match(r"[\x%02x]" % i, chr(i))), True)
            self.assertEqual(bool(regex.match(r"[\x%02x0]" % i, chr(i))), True)
            self.assertEqual(bool(regex.match(r"[\x%02xz]" % i, chr(i))), True)

        self.assertRaisesRegex(regex.error, self.BAD_OCTAL_ESCAPE, lambda:
          regex.match(r"[\911]", ""))

    def test_bug_113254(self):
        self.assertEqual(regex.match(r'(a)|(b)', 'b').start(1), -1)
        self.assertEqual(regex.match(r'(a)|(b)', 'b').end(1), -1)
        self.assertEqual(regex.match(r'(a)|(b)', 'b').span(1), (-1, -1))

    def test_bug_527371(self):
        # Bug described in patches 527371/672491.
        self.assertEqual(regex.match(r'(a)?a','a').lastindex, None)
        self.assertEqual(regex.match(r'(a)(b)?b','ab').lastindex, 1)
        self.assertEqual(regex.match(r'(?P<a>a)(?P<b>b)?b','ab').lastgroup,
          'a')
        self.assertEqual(regex.match("(?P<a>a(b))", "ab").lastgroup, 'a')
        self.assertEqual(regex.match("((a))", "a").lastindex, 1)

    def test_bug_545855(self):
        # Bug 545855 -- This pattern failed to cause a compile error as it
        # should, instead provoking a TypeError.
        self.assertRaisesRegex(regex.error, self.BAD_SET, lambda:
          regex.compile('foo[a-'))

    def test_bug_418626(self):
        # Bugs 418626 at al. -- Testing Greg Chapman's addition of op code
        # SRE_OP_MIN_REPEAT_ONE for eliminating recursion on simple uses of
        # pattern '*?' on a long string.
        self.assertEqual(regex.match('.*?c', 10000 * 'ab' + 'cd').end(0),
          20001)
        self.assertEqual(regex.match('.*?cd', 5000 * 'ab' + 'c' + 5000 * 'ab' +
          'cde').end(0), 20003)
        self.assertEqual(regex.match('.*?cd', 20000 * 'abc' + 'de').end(0),
          60001)
        # Non-simple '*?' still used to hit the recursion limit, before the
        # non-recursive scheme was implemented.
        self.assertEqual(regex.search('(a|b)*?c', 10000 * 'ab' + 'cd').end(0),
          20001)

    def test_bug_612074(self):
        pat = "[" + regex.escape("\u2039") + "]"
        self.assertEqual(regex.compile(pat) and 1, 1)

    def test_stack_overflow(self):
        # Nasty cases that used to overflow the straightforward recursive
        # implementation of repeated groups.
        self.assertEqual(regex.match('(x)*', 50000 * 'x')[1], 'x')
        self.assertEqual(regex.match('(x)*y', 50000 * 'x' + 'y')[1], 'x')
        self.assertEqual(regex.match('(x)*?y', 50000 * 'x' + 'y')[1], 'x')

    def test_scanner(self):
        def s_ident(scanner, token): return token
        def s_operator(scanner, token): return "op%s" % token
        def s_float(scanner, token): return float(token)
        def s_int(scanner, token): return int(token)

        scanner = regex.Scanner([(r"[a-zA-Z_]\w*", s_ident), (r"\d+\.\d*",
          s_float), (r"\d+", s_int), (r"=|\+|-|\*|/", s_operator), (r"\s+",
            None), ])

        self.assertEqual(repr(type(scanner.scanner.scanner("").pattern)),
          self.PATTERN_CLASS)

        self.assertEqual(scanner.scan("sum = 3*foo + 312.50 + bar"), (['sum',
          'op=', 3, 'op*', 'foo', 'op+', 312.5, 'op+', 'bar'], ''))

    def test_bug_448951(self):
        # Bug 448951 (similar to 429357, but with single char match).
        # (Also test greedy matches.)
        for op in '', '?', '*':
            self.assertEqual(regex.match(r'((.%s):)?z' % op, 'z')[:], ('z',
              None, None))
            self.assertEqual(regex.match(r'((.%s):)?z' % op, 'a:z')[:], ('a:z',
              'a:', 'a'))

    def test_bug_725106(self):
        # Capturing groups in alternatives in repeats.
        self.assertEqual(regex.match('^((a)|b)*', 'abc')[:], ('ab', 'b', 'a'))
        self.assertEqual(regex.match('^(([ab])|c)*', 'abc')[:], ('abc', 'c',
          'b'))
        self.assertEqual(regex.match('^((d)|[ab])*', 'abc')[:], ('ab', 'b',
          None))
        self.assertEqual(regex.match('^((a)c|[ab])*', 'abc')[:], ('ab', 'b',
          None))
        self.assertEqual(regex.match('^((a)|b)*?c', 'abc')[:], ('abc', 'b',
          'a'))
        self.assertEqual(regex.match('^(([ab])|c)*?d', 'abcd')[:], ('abcd',
          'c', 'b'))
        self.assertEqual(regex.match('^((d)|[ab])*?c', 'abc')[:], ('abc', 'b',
          None))
        self.assertEqual(regex.match('^((a)c|[ab])*?c', 'abc')[:], ('abc', 'b',
          None))

    def test_bug_725149(self):
        # Mark_stack_base restoring before restoring marks.
        self.assertEqual(regex.match('(a)(?:(?=(b)*)c)*', 'abb')[:], ('a', 'a',
          None))
        self.assertEqual(regex.match('(a)((?!(b)*))*', 'abb')[:], ('a', 'a',
          None, None))

    def test_bug_764548(self):
        # Bug 764548, regex.compile() barfs on str/unicode subclasses.
        class my_unicode(str): pass
        pat = regex.compile(my_unicode("abc"))
        self.assertEqual(pat.match("xyz"), None)

    def test_finditer(self):
        it = regex.finditer(r":+", "a:b::c:::d")
        self.assertEqual([item[0] for item in it], [':', '::', ':::'])

    def test_bug_926075(self):
        if regex.compile('bug_926075') is regex.compile(b'bug_926075'):
            self.fail()

    def test_bug_931848(self):
        pattern = "[\u002E\u3002\uFF0E\uFF61]"
        self.assertEqual(regex.compile(pattern).split("a.b.c"), ['a', 'b',
          'c'])

    def test_bug_581080(self):
        it = regex.finditer(r"\s", "a b")
        self.assertEqual(next(it).span(), (1, 2))
        self.assertRaises(StopIteration, lambda: next(it))

        scanner = regex.compile(r"\s").scanner("a b")
        self.assertEqual(scanner.search().span(), (1, 2))
        self.assertEqual(scanner.search(), None)

    def test_bug_817234(self):
        it = regex.finditer(r".*", "asdf")
        self.assertEqual(next(it).span(), (0, 4))
        self.assertEqual(next(it).span(), (4, 4))
        self.assertRaises(StopIteration, lambda: next(it))

    def test_empty_array(self):
        # SF buf 1647541.
        import array
        for typecode in 'bBuhHiIlLfd':
            a = array.array(typecode)
            self.assertEqual(regex.compile(b"bla").match(a), None)
            self.assertEqual(regex.compile(b"").match(a)[1 : ], ())

    def test_inline_flags(self):
        # Bug #1700.
        upper_char = chr(0x1ea0) # Latin Capital Letter A with Dot Below
        lower_char = chr(0x1ea1) # Latin Small Letter A with Dot Below

        p = regex.compile(upper_char, regex.I | regex.U)
        self.assertEqual(bool(p.match(lower_char)), True)

        p = regex.compile(lower_char, regex.I | regex.U)
        self.assertEqual(bool(p.match(upper_char)), True)

        p = regex.compile('(?i)' + upper_char, regex.U)
        self.assertEqual(bool(p.match(lower_char)), True)

        p = regex.compile('(?i)' + lower_char, regex.U)
        self.assertEqual(bool(p.match(upper_char)), True)

        p = regex.compile('(?iu)' + upper_char)
        self.assertEqual(bool(p.match(lower_char)), True)

        p = regex.compile('(?iu)' + lower_char)
        self.assertEqual(bool(p.match(upper_char)), True)

        # Changed to positional flags in regex 2023.12.23.
        self.assertEqual(bool(regex.match(r"(?i)a", "A")), True)
        self.assertEqual(regex.match(r"a(?i)", "A"), None)

    def test_dollar_matches_twice(self):
        # $ matches the end of string, and just before the terminating \n.
        pattern = regex.compile('$')
        self.assertEqual(pattern.sub('#', 'a\nb\n'), 'a\nb#\n#')
        self.assertEqual(pattern.sub('#', 'a\nb\nc'), 'a\nb\nc#')
        self.assertEqual(pattern.sub('#', '\n'), '#\n#')

        pattern = regex.compile('$', regex.MULTILINE)
        self.assertEqual(pattern.sub('#', 'a\nb\n' ), 'a#\nb#\n#')
        self.assertEqual(pattern.sub('#', 'a\nb\nc'), 'a#\nb#\nc#')
        self.assertEqual(pattern.sub('#', '\n'), '#\n#')

    def test_bytes_str_mixing(self):
        # Mixing str and bytes is disallowed.
        pat = regex.compile('.')
        bpat = regex.compile(b'.')
        self.assertRaisesRegex(TypeError, self.STR_PAT_ON_BYTES, lambda:
          pat.match(b'b'))
        self.assertRaisesRegex(TypeError, self.BYTES_PAT_ON_STR, lambda:
          bpat.match('b'))
        self.assertRaisesRegex(TypeError, self.STR_PAT_BYTES_TEMPL, lambda:
          pat.sub(b'b', 'c'))
        self.assertRaisesRegex(TypeError, self.STR_PAT_ON_BYTES, lambda:
          pat.sub('b', b'c'))
        self.assertRaisesRegex(TypeError, self.STR_PAT_ON_BYTES, lambda:
          pat.sub(b'b', b'c'))
        self.assertRaisesRegex(TypeError, self.BYTES_PAT_ON_STR, lambda:
          bpat.sub(b'b', 'c'))
        self.assertRaisesRegex(TypeError, self.BYTES_PAT_STR_TEMPL, lambda:
          bpat.sub('b', b'c'))
        self.assertRaisesRegex(TypeError, self.BYTES_PAT_ON_STR, lambda:
          bpat.sub('b', 'c'))

        self.assertRaisesRegex(ValueError, self.BYTES_PAT_UNI_FLAG, lambda:
          regex.compile(br'\w', regex.UNICODE))
        self.assertRaisesRegex(ValueError, self.BYTES_PAT_UNI_FLAG, lambda:
          regex.compile(br'(?u)\w'))
        self.assertRaisesRegex(ValueError, self.MIXED_FLAGS, lambda:
          regex.compile(r'\w', regex.UNICODE | regex.ASCII))
        self.assertRaisesRegex(ValueError, self.MIXED_FLAGS, lambda:
          regex.compile(r'(?u)\w', regex.ASCII))
        self.assertRaisesRegex(ValueError, self.MIXED_FLAGS, lambda:
          regex.compile(r'(?a)\w', regex.UNICODE))
        self.assertRaisesRegex(ValueError, self.MIXED_FLAGS, lambda:
          regex.compile(r'(?au)\w'))

    def test_ascii_and_unicode_flag(self):
        # String patterns.
        for flags in (0, regex.UNICODE):
            pat = regex.compile('\xc0', flags | regex.IGNORECASE)
            self.assertEqual(bool(pat.match('\xe0')), True)
            pat = regex.compile(r'\w', flags)
            self.assertEqual(bool(pat.match('\xe0')), True)

        pat = regex.compile('\xc0', regex.ASCII | regex.IGNORECASE)
        self.assertEqual(pat.match('\xe0'), None)
        pat = regex.compile('(?a)\xc0', regex.IGNORECASE)
        self.assertEqual(pat.match('\xe0'), None)
        pat = regex.compile(r'\w', regex.ASCII)
        self.assertEqual(pat.match('\xe0'), None)
        pat = regex.compile(r'(?a)\w')
        self.assertEqual(pat.match('\xe0'), None)

        # Bytes patterns.
        for flags in (0, regex.ASCII):
            pat = regex.compile(b'\xc0', flags | regex.IGNORECASE)
            self.assertEqual(pat.match(b'\xe0'), None)
            pat = regex.compile(br'\w')
            self.assertEqual(pat.match(b'\xe0'), None)

        self.assertRaisesRegex(ValueError, self.MIXED_FLAGS, lambda:
          regex.compile(r'(?au)\w'))

    def test_subscripting_match(self):
        m = regex.match(r'(?<a>\w)', 'xy')
        if not m:
            self.fail("Failed: expected match but returned None")
        elif not m or m[0] != m.group(0) or m[1] != m.group(1):
            self.fail("Failed")
        if not m:
            self.fail("Failed: expected match but returned None")
        elif m[:] != ('x', 'x'):
            self.fail("Failed: expected \"('x', 'x')\" but got {} instead".format(ascii(m[:])))

    def test_new_named_groups(self):
        m0 = regex.match(r'(?P<a>\w)', 'x')
        m1 = regex.match(r'(?<a>\w)', 'x')
        if not (m0 and m1 and m0[:] == m1[:]):
            self.fail("Failed")

    def test_properties(self):
        self.assertEqual(regex.match(b'(?ai)\xC0', b'\xE0'), None)
        self.assertEqual(regex.match(br'(?ai)\xC0', b'\xE0'), None)
        self.assertEqual(regex.match(br'(?a)\w', b'\xE0'), None)
        self.assertEqual(bool(regex.match(r'\w', '\xE0')), True)

        # Dropped the following test. It's not possible to determine what the
        # correct result should be in the general case.
#        self.assertEqual(bool(regex.match(br'(?L)\w', b'\xE0')),
#          b'\xE0'.isalnum())

        self.assertEqual(bool(regex.match(br'(?L)\d', b'0')), True)
        self.assertEqual(bool(regex.match(br'(?L)\s', b' ')), True)
        self.assertEqual(bool(regex.match(br'(?L)\w', b'a')), True)
        self.assertEqual(regex.match(br'(?L)\d', b'?'), None)
        self.assertEqual(regex.match(br'(?L)\s', b'?'), None)
        self.assertEqual(regex.match(br'(?L)\w', b'?'), None)

        self.assertEqual(regex.match(br'(?L)\D', b'0'), None)
        self.assertEqual(regex.match(br'(?L)\S', b' '), None)
        self.assertEqual(regex.match(br'(?L)\W', b'a'), None)
        self.assertEqual(bool(regex.match(br'(?L)\D', b'?')), True)
        self.assertEqual(bool(regex.match(br'(?L)\S', b'?')), True)
        self.assertEqual(bool(regex.match(br'(?L)\W', b'?')), True)

        self.assertEqual(bool(regex.match(r'\p{Cyrillic}',
          '\N{CYRILLIC CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'(?i)\p{Cyrillic}',
          '\N{CYRILLIC CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'\p{IsCyrillic}',
          '\N{CYRILLIC CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'\p{Script=Cyrillic}',
          '\N{CYRILLIC CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'\p{InCyrillic}',
          '\N{CYRILLIC CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'\p{Block=Cyrillic}',
          '\N{CYRILLIC CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'[[:Cyrillic:]]',
          '\N{CYRILLIC CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'[[:IsCyrillic:]]',
          '\N{CYRILLIC CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'[[:Script=Cyrillic:]]',
          '\N{CYRILLIC CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'[[:InCyrillic:]]',
          '\N{CYRILLIC CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'[[:Block=Cyrillic:]]',
          '\N{CYRILLIC CAPITAL LETTER A}')), True)

        self.assertEqual(bool(regex.match(r'\P{Cyrillic}',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'\P{IsCyrillic}',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'\P{Script=Cyrillic}',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'\P{InCyrillic}',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'\P{Block=Cyrillic}',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'\p{^Cyrillic}',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'\p{^IsCyrillic}',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'\p{^Script=Cyrillic}',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'\p{^InCyrillic}',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'\p{^Block=Cyrillic}',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'[[:^Cyrillic:]]',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'[[:^IsCyrillic:]]',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'[[:^Script=Cyrillic:]]',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'[[:^InCyrillic:]]',
          '\N{LATIN CAPITAL LETTER A}')), True)
        self.assertEqual(bool(regex.match(r'[[:^Block=Cyrillic:]]',
          '\N{LATIN CAPITAL LETTER A}')), True)

        self.assertEqual(bool(regex.match(r'\d', '0')), True)
        self.assertEqual(bool(regex.match(r'\s', ' ')), True)
        self.assertEqual(bool(regex.match(r'\w', 'A')), True)
        self.assertEqual(regex.match(r"\d", "?"), None)
        self.assertEqual(regex.match(r"\s", "?"), None)
        self.assertEqual(regex.match(r"\w", "?"), None)
        self.assertEqual(regex.match(r"\D", "0"), None)
        self.assertEqual(regex.match(r"\S", " "), None)
        self.assertEqual(regex.match(r"\W", "A"), None)
        self.assertEqual(bool(regex.match(r'\D', '?')), True)
        self.assertEqual(bool(regex.match(r'\S', '?')), True)
        self.assertEqual(bool(regex.match(r'\W', '?')), True)

        self.assertEqual(bool(regex.match(r'\p{L}', 'A')), True)
        self.assertEqual(bool(regex.match(r'\p{L}', 'a')), True)
        self.assertEqual(bool(regex.match(r'\p{Lu}', 'A')), True)
        self.assertEqual(bool(regex.match(r'\p{Ll}', 'a')), True)

        self.assertEqual(bool(regex.match(r'(?i)a', 'a')), True)
        self.assertEqual(bool(regex.match(r'(?i)a', 'A')), True)

        self.assertEqual(bool(regex.match(r'\w', '0')), True)
        self.assertEqual(bool(regex.match(r'\w', 'a')), True)
        self.assertEqual(bool(regex.match(r'\w', '_')), True)

        self.assertEqual(regex.match(r"\X", "\xE0").span(), (0, 1))
        self.assertEqual(regex.match(r"\X", "a\u0300").span(), (0, 2))
        self.assertEqual(regex.findall(r"\X",
          "a\xE0a\u0300e\xE9e\u0301"), ['a', '\xe0', 'a\u0300', 'e',
          '\xe9', 'e\u0301'])
        self.assertEqual(regex.findall(r"\X{3}",
          "a\xE0a\u0300e\xE9e\u0301"), ['a\xe0a\u0300', 'e\xe9e\u0301'])
        self.assertEqual(regex.findall(r"\X", "\r\r\n\u0301A\u0301"),
          ['\r', '\r\n', '\u0301', 'A\u0301'])

        self.assertEqual(bool(regex.match(r'\p{Ll}', 'a')), True)

        chars_u = "-09AZaz_\u0393\u03b3"
        chars_b = b"-09AZaz_"
        word_set = set("Ll Lm Lo Lt Lu Mc Me Mn Nd Nl No Pc".split())

        tests = [
            (r"\w", chars_u, "09AZaz_\u0393\u03b3"),
            (r"[[:word:]]", chars_u, "09AZaz_\u0393\u03b3"),
            (r"\W", chars_u, "-"),
            (r"[[:^word:]]", chars_u, "-"),
            (r"\d", chars_u, "09"),
            (r"[[:digit:]]", chars_u, "09"),
            (r"\D", chars_u, "-AZaz_\u0393\u03b3"),
            (r"[[:^digit:]]", chars_u, "-AZaz_\u0393\u03b3"),
            (r"[[:alpha:]]", chars_u, "AZaz\u0393\u03b3"),
            (r"[[:^alpha:]]", chars_u, "-09_"),
            (r"[[:alnum:]]", chars_u, "09AZaz\u0393\u03b3"),
            (r"[[:^alnum:]]", chars_u, "-_"),
            (r"[[:xdigit:]]", chars_u, "09Aa"),
            (r"[[:^xdigit:]]", chars_u, "-Zz_\u0393\u03b3"),
            (r"\p{InBasicLatin}", "a\xE1", "a"),
            (r"\P{InBasicLatin}", "a\xE1", "\xE1"),
            (r"(?i)\p{InBasicLatin}", "a\xE1", "a"),
            (r"(?i)\P{InBasicLatin}", "a\xE1", "\xE1"),

            (br"(?L)\w", chars_b, b"09AZaz_"),
            (br"(?L)[[:word:]]", chars_b, b"09AZaz_"),
            (br"(?L)\W", chars_b, b"-"),
            (br"(?L)[[:^word:]]", chars_b, b"-"),
            (br"(?L)\d", chars_b, b"09"),
            (br"(?L)[[:digit:]]", chars_b, b"09"),
            (br"(?L)\D", chars_b, b"-AZaz_"),
            (br"(?L)[[:^digit:]]", chars_b, b"-AZaz_"),
            (br"(?L)[[:alpha:]]", chars_b, b"AZaz"),
            (br"(?L)[[:^alpha:]]", chars_b, b"-09_"),
            (br"(?L)[[:alnum:]]", chars_b, b"09AZaz"),
            (br"(?L)[[:^alnum:]]", chars_b, b"-_"),
            (br"(?L)[[:xdigit:]]", chars_b, b"09Aa"),
            (br"(?L)[[:^xdigit:]]", chars_b, b"-Zz_"),

            (br"(?a)\w", chars_b, b"09AZaz_"),
            (br"(?a)[[:word:]]", chars_b, b"09AZaz_"),
            (br"(?a)\W", chars_b, b"-"),
            (br"(?a)[[:^word:]]", chars_b, b"-"),
            (br"(?a)\d", chars_b, b"09"),
            (br"(?a)[[:digit:]]", chars_b, b"09"),
            (br"(?a)\D", chars_b, b"-AZaz_"),
            (br"(?a)[[:^digit:]]", chars_b, b"-AZaz_"),
            (br"(?a)[[:alpha:]]", chars_b, b"AZaz"),
            (br"(?a)[[:^alpha:]]", chars_b, b"-09_"),
            (br"(?a)[[:alnum:]]", chars_b, b"09AZaz"),
            (br"(?a)[[:^alnum:]]", chars_b, b"-_"),
            (br"(?a)[[:xdigit:]]", chars_b, b"09Aa"),
            (br"(?a)[[:^xdigit:]]", chars_b, b"-Zz_"),
        ]
        for pattern, chars, expected in tests:
            try:
                if chars[ : 0].join(regex.findall(pattern, chars)) != expected:
                    self.fail("Failed: {}".format(pattern))
            except Exception as e:
                self.fail("Failed: {} raised {}".format(pattern, ascii(e)))

        self.assertEqual(bool(regex.match(r"\p{NumericValue=0}", "0")),
          True)
        self.assertEqual(bool(regex.match(r"\p{NumericValue=1/2}",
          "\N{VULGAR FRACTION ONE HALF}")), True)
        self.assertEqual(bool(regex.match(r"\p{NumericValue=0.5}",
          "\N{VULGAR FRACTION ONE HALF}")), True)

    def test_word_class(self):
        self.assertEqual(regex.findall(r"\w+",
          " \u0939\u093f\u0928\u094d\u0926\u0940,"),
          ['\u0939\u093f\u0928\u094d\u0926\u0940'])
        self.assertEqual(regex.findall(r"\W+",
          " \u0939\u093f\u0928\u094d\u0926\u0940,"), [' ', ','])
        self.assertEqual(regex.split(r"(?V1)\b",
          " \u0939\u093f\u0928\u094d\u0926\u0940,"), [' ',
          '\u0939\u093f\u0928\u094d\u0926\u0940', ','])
        self.assertEqual(regex.split(r"(?V1)\B",
          " \u0939\u093f\u0928\u094d\u0926\u0940,"), ['', ' \u0939',
          '\u093f', '\u0928', '\u094d', '\u0926', '\u0940,', ''])

    def test_search_anchor(self):
        self.assertEqual(regex.findall(r"\G\w{2}", "abcd ef"), ['ab', 'cd'])

    def test_search_reverse(self):
        self.assertEqual(regex.findall(r"(?r).", "abc"), ['c', 'b', 'a'])
        self.assertEqual(regex.findall(r"(?r).", "abc", overlapped=True), ['c',
          'b', 'a'])
        self.assertEqual(regex.findall(r"(?r)..", "abcde"), ['de', 'bc'])
        self.assertEqual(regex.findall(r"(?r)..", "abcde", overlapped=True),
          ['de', 'cd', 'bc', 'ab'])
        self.assertEqual(regex.findall(r"(?r)(.)(-)(.)", "a-b-c",
          overlapped=True), [("b", "-", "c"), ("a", "-", "b")])

        self.assertEqual([m[0] for m in regex.finditer(r"(?r).", "abc")], ['c',
          'b', 'a'])
        self.assertEqual([m[0] for m in regex.finditer(r"(?r)..", "abcde",
          overlapped=True)], ['de', 'cd', 'bc', 'ab'])
        self.assertEqual([m[0] for m in regex.finditer(r"(?r).", "abc")], ['c',
          'b', 'a'])
        self.assertEqual([m[0] for m in regex.finditer(r"(?r)..", "abcde",
          overlapped=True)], ['de', 'cd', 'bc', 'ab'])

        self.assertEqual(regex.findall(r"^|\w+", "foo bar"), ['', 'foo',
          'bar'])
        self.assertEqual(regex.findall(r"(?V1)^|\w+", "foo bar"), ['', 'foo',
          'bar'])
        self.assertEqual(regex.findall(r"(?r)^|\w+", "foo bar"), ['bar', 'foo',
          ''])
        self.assertEqual(regex.findall(r"(?rV1)^|\w+", "foo bar"), ['bar',
          'foo', ''])

        self.assertEqual([m[0] for m in regex.finditer(r"^|\w+", "foo bar")],
          ['', 'foo', 'bar'])
        self.assertEqual([m[0] for m in regex.finditer(r"(?V1)^|\w+",
          "foo bar")], ['', 'foo', 'bar'])
        self.assertEqual([m[0] for m in regex.finditer(r"(?r)^|\w+",
          "foo bar")], ['bar', 'foo', ''])
        self.assertEqual([m[0] for m in regex.finditer(r"(?rV1)^|\w+",
          "foo bar")], ['bar', 'foo', ''])

        self.assertEqual(regex.findall(r"\G\w{2}", "abcd ef"), ['ab', 'cd'])
        self.assertEqual(regex.findall(r".{2}(?<=\G.*)", "abcd"), ['ab', 'cd'])
        self.assertEqual(regex.findall(r"(?r)\G\w{2}", "abcd ef"), [])
        self.assertEqual(regex.findall(r"(?r)\w{2}\G", "abcd ef"), ['ef'])

        self.assertEqual(regex.findall(r"q*", "qqwe"), ['qq', '', '', ''])
        self.assertEqual(regex.findall(r"(?V1)q*", "qqwe"), ['qq', '', '', ''])
        self.assertEqual(regex.findall(r"(?r)q*", "qqwe"), ['', '', 'qq', ''])
        self.assertEqual(regex.findall(r"(?rV1)q*", "qqwe"), ['', '', 'qq',
          ''])

        self.assertEqual(regex.findall(".", "abcd", pos=1, endpos=3), ['b',
          'c'])
        self.assertEqual(regex.findall(".", "abcd", pos=1, endpos=-1), ['b',
          'c'])
        self.assertEqual([m[0] for m in regex.finditer(".", "abcd", pos=1,
          endpos=3)], ['b', 'c'])
        self.assertEqual([m[0] for m in regex.finditer(".", "abcd", pos=1,
          endpos=-1)], ['b', 'c'])

        self.assertEqual([m[0] for m in regex.finditer("(?r).", "abcd", pos=1,
          endpos=3)], ['c', 'b'])
        self.assertEqual([m[0] for m in regex.finditer("(?r).", "abcd", pos=1,
          endpos=-1)], ['c', 'b'])
        self.assertEqual(regex.findall("(?r).", "abcd", pos=1, endpos=3), ['c',
          'b'])
        self.assertEqual(regex.findall("(?r).", "abcd", pos=1, endpos=-1),
          ['c', 'b'])

        self.assertEqual(regex.findall(r"[ab]", "aB", regex.I), ['a', 'B'])
        self.assertEqual(regex.findall(r"(?r)[ab]", "aB", regex.I), ['B', 'a'])

        self.assertEqual(regex.findall(r"(?r).{2}", "abc"), ['bc'])
        self.assertEqual(regex.findall(r"(?r).{2}", "abc", overlapped=True),
          ['bc', 'ab'])
        self.assertEqual(regex.findall(r"(\w+) (\w+)",
          "first second third fourth fifth"), [('first', 'second'), ('third',
          'fourth')])
        self.assertEqual(regex.findall(r"(?r)(\w+) (\w+)",
          "first second third fourth fifth"), [('fourth', 'fifth'), ('second',
          'third')])

        self.assertEqual([m[0] for m in regex.finditer(r"(?r).{2}", "abc")],
          ['bc'])
        self.assertEqual([m[0] for m in regex.finditer(r"(?r).{2}", "abc",
          overlapped=True)], ['bc', 'ab'])
        self.assertEqual([m[0] for m in regex.finditer(r"(\w+) (\w+)",
          "first second third fourth fifth")], ['first second',
          'third fourth'])
        self.assertEqual([m[0] for m in regex.finditer(r"(?r)(\w+) (\w+)",
          "first second third fourth fifth")], ['fourth fifth',
          'second third'])

        self.assertEqual(regex.search("abcdef", "abcdef").span(), (0, 6))
        self.assertEqual(regex.search("(?r)abcdef", "abcdef").span(), (0, 6))
        self.assertEqual(regex.search("(?i)abcdef", "ABCDEF").span(), (0, 6))
        self.assertEqual(regex.search("(?ir)abcdef", "ABCDEF").span(), (0, 6))

        self.assertEqual(regex.sub(r"(.)", r"\1", "abc"), 'abc')
        self.assertEqual(regex.sub(r"(?r)(.)", r"\1", "abc"), 'abc')

    def test_atomic(self):
        # Issue 433030.
        self.assertEqual(regex.search(r"(?>a*)a", "aa"), None)

    def test_possessive(self):
        # Single-character non-possessive.
        self.assertEqual(regex.search(r"a?a", "a").span(), (0, 1))
        self.assertEqual(regex.search(r"a*a", "aaa").span(), (0, 3))
        self.assertEqual(regex.search(r"a+a", "aaa").span(), (0, 3))
        self.assertEqual(regex.search(r"a{1,3}a", "aaa").span(), (0, 3))

        # Multiple-character non-possessive.
        self.assertEqual(regex.search(r"(?:ab)?ab", "ab").span(), (0, 2))
        self.assertEqual(regex.search(r"(?:ab)*ab", "ababab").span(), (0, 6))
        self.assertEqual(regex.search(r"(?:ab)+ab", "ababab").span(), (0, 6))
        self.assertEqual(regex.search(r"(?:ab){1,3}ab", "ababab").span(), (0,
          6))

        # Single-character possessive.
        self.assertEqual(regex.search(r"a?+a", "a"), None)
        self.assertEqual(regex.search(r"a*+a", "aaa"), None)
        self.assertEqual(regex.search(r"a++a", "aaa"), None)
        self.assertEqual(regex.search(r"a{1,3}+a", "aaa"), None)

        # Multiple-character possessive.
        self.assertEqual(regex.search(r"(?:ab)?+ab", "ab"), None)
        self.assertEqual(regex.search(r"(?:ab)*+ab", "ababab"), None)
        self.assertEqual(regex.search(r"(?:ab)++ab", "ababab"), None)
        self.assertEqual(regex.search(r"(?:ab){1,3}+ab", "ababab"), None)

    def test_zerowidth(self):
        # Issue 3262.
        if sys.version_info >= (3, 7, 0):
            self.assertEqual(regex.split(r"\b", "a b"), ['', 'a', ' ', 'b',
              ''])
        else:
            self.assertEqual(regex.split(r"\b", "a b"), ['a b'])
        self.assertEqual(regex.split(r"(?V1)\b", "a b"), ['', 'a', ' ', 'b',
          ''])

        # Issue 1647489.
        self.assertEqual(regex.findall(r"^|\w+", "foo bar"), ['', 'foo',
          'bar'])
        self.assertEqual([m[0] for m in regex.finditer(r"^|\w+", "foo bar")],
          ['', 'foo', 'bar'])
        self.assertEqual(regex.findall(r"(?r)^|\w+", "foo bar"), ['bar',
          'foo', ''])
        self.assertEqual([m[0] for m in regex.finditer(r"(?r)^|\w+",
          "foo bar")], ['bar', 'foo', ''])
        self.assertEqual(regex.findall(r"(?V1)^|\w+", "foo bar"), ['', 'foo',
          'bar'])
        self.assertEqual([m[0] for m in regex.finditer(r"(?V1)^|\w+",
          "foo bar")], ['', 'foo', 'bar'])
        self.assertEqual(regex.findall(r"(?rV1)^|\w+", "foo bar"), ['bar',
          'foo', ''])
        self.assertEqual([m[0] for m in regex.finditer(r"(?rV1)^|\w+",
          "foo bar")], ['bar', 'foo', ''])

        if sys.version_info >= (3, 7, 0):
            self.assertEqual(regex.split("", "xaxbxc"), ['', 'x', 'a', 'x',
              'b', 'x', 'c', ''])
            self.assertEqual([m for m in regex.splititer("", "xaxbxc")], ['',
              'x', 'a', 'x', 'b', 'x', 'c', ''])
        else:
            self.assertEqual(regex.split("", "xaxbxc"), ['xaxbxc'])
            self.assertEqual([m for m in regex.splititer("", "xaxbxc")],
              ['xaxbxc'])

        if sys.version_info >= (3, 7, 0):
            self.assertEqual(regex.split("(?r)", "xaxbxc"), ['', 'c', 'x', 'b',
              'x', 'a', 'x', ''])
            self.assertEqual([m for m in regex.splititer("(?r)", "xaxbxc")],
              ['', 'c', 'x', 'b', 'x', 'a', 'x', ''])
        else:
            self.assertEqual(regex.split("(?r)", "xaxbxc"), ['xaxbxc'])
            self.assertEqual([m for m in regex.splititer("(?r)", "xaxbxc")],
              ['xaxbxc'])

        self.assertEqual(regex.split("(?V1)", "xaxbxc"), ['', 'x', 'a', 'x',
          'b', 'x', 'c', ''])
        self.assertEqual([m for m in regex.splititer("(?V1)", "xaxbxc")], ['',
          'x', 'a', 'x', 'b', 'x', 'c', ''])

        self.assertEqual(regex.split("(?rV1)", "xaxbxc"), ['', 'c', 'x', 'b',
          'x', 'a', 'x', ''])
        self.assertEqual([m for m in regex.splititer("(?rV1)", "xaxbxc")], ['',
          'c', 'x', 'b', 'x', 'a', 'x', ''])

    def test_scoped_and_inline_flags(self):
        # Issues 433028, 433024, 433027.
        self.assertEqual(regex.search(r"(?i)Ab", "ab").span(), (0, 2))
        self.assertEqual(regex.search(r"(?i:A)b", "ab").span(), (0, 2))
        # Changed to positional flags in regex 2023.12.23.
        self.assertEqual(regex.search(r"A(?i)b", "ab"), None)

        self.assertEqual(regex.search(r"(?V0)Ab", "ab"), None)
        self.assertEqual(regex.search(r"(?V1)Ab", "ab"), None)
        self.assertEqual(regex.search(r"(?-i)Ab", "ab", flags=regex.I), None)
        self.assertEqual(regex.search(r"(?-i:A)b", "ab", flags=regex.I), None)
        self.assertEqual(regex.search(r"A(?-i)b", "ab", flags=regex.I).span(),
          (0, 2))

    def test_repeated_repeats(self):
        # Issue 2537.
        self.assertEqual(regex.search(r"(?:a+)+", "aaa").span(), (0, 3))
        self.assertEqual(regex.search(r"(?:(?:ab)+c)+", "abcabc").span(), (0,
          6))

        # Hg issue 286.
        self.assertEqual(regex.search(r"(?:a+){2,}", "aaa").span(), (0, 3))

    def test_lookbehind(self):
        self.assertEqual(regex.search(r"123(?<=a\d+)", "a123").span(), (1, 4))
        self.assertEqual(regex.search(r"123(?<=a\d+)", "b123"), None)
        self.assertEqual(regex.search(r"123(?<!a\d+)", "a123"), None)
        self.assertEqual(regex.search(r"123(?<!a\d+)", "b123").span(), (1, 4))

        self.assertEqual(bool(regex.match("(a)b(?<=b)(c)", "abc")), True)
        self.assertEqual(regex.match("(a)b(?<=c)(c)", "abc"), None)
        self.assertEqual(bool(regex.match("(a)b(?=c)(c)", "abc")), True)
        self.assertEqual(regex.match("(a)b(?=b)(c)", "abc"), None)

        self.assertEqual(regex.match("(?:(a)|(x))b(?<=(?(2)x|c))c", "abc"),
          None)
        self.assertEqual(regex.match("(?:(a)|(x))b(?<=(?(2)b|x))c", "abc"),
          None)
        self.assertEqual(bool(regex.match("(?:(a)|(x))b(?<=(?(2)x|b))c",
          "abc")), True)
        self.assertEqual(regex.match("(?:(a)|(x))b(?<=(?(1)c|x))c", "abc"),
          None)
        self.assertEqual(bool(regex.match("(?:(a)|(x))b(?<=(?(1)b|x))c",
          "abc")), True)

        self.assertEqual(bool(regex.match("(?:(a)|(x))b(?=(?(2)x|c))c",
          "abc")), True)
        self.assertEqual(regex.match("(?:(a)|(x))b(?=(?(2)c|x))c", "abc"),
          None)
        self.assertEqual(bool(regex.match("(?:(a)|(x))b(?=(?(2)x|c))c",
          "abc")), True)
        self.assertEqual(regex.match("(?:(a)|(x))b(?=(?(1)b|x))c", "abc"),
          None)
        self.assertEqual(bool(regex.match("(?:(a)|(x))b(?=(?(1)c|x))c",
          "abc")), True)

        self.assertEqual(regex.match("(a)b(?<=(?(2)x|c))(c)", "abc"), None)
        self.assertEqual(regex.match("(a)b(?<=(?(2)b|x))(c)", "abc"), None)
        self.assertEqual(regex.match("(a)b(?<=(?(1)c|x))(c)", "abc"), None)
        self.assertEqual(bool(regex.match("(a)b(?<=(?(1)b|x))(c)", "abc")),
          True)

        self.assertEqual(bool(regex.match("(a)b(?=(?(2)x|c))(c)", "abc")),
          True)
        self.assertEqual(regex.match("(a)b(?=(?(2)b|x))(c)", "abc"), None)
        self.assertEqual(bool(regex.match("(a)b(?=(?(1)c|x))(c)", "abc")),
          True)

        self.assertEqual(repr(type(regex.compile(r"(a)\2(b)"))),
          self.PATTERN_CLASS)

    def test_unmatched_in_sub(self):
        # Issue 1519638.

        if sys.version_info >= (3, 7, 0):
            self.assertEqual(regex.sub(r"(?V0)(x)?(y)?", r"\2-\1", "xy"),
              'y-x-')
        else:
            self.assertEqual(regex.sub(r"(?V0)(x)?(y)?", r"\2-\1", "xy"),
              'y-x')
        self.assertEqual(regex.sub(r"(?V1)(x)?(y)?", r"\2-\1", "xy"), 'y-x-')
        if sys.version_info >= (3, 7, 0):
            self.assertEqual(regex.sub(r"(?V0)(x)?(y)?", r"\2-\1", "x"), '-x-')
        else:
            self.assertEqual(regex.sub(r"(?V0)(x)?(y)?", r"\2-\1", "x"), '-x')
        self.assertEqual(regex.sub(r"(?V1)(x)?(y)?", r"\2-\1", "x"), '-x-')
        if sys.version_info >= (3, 7, 0):
            self.assertEqual(regex.sub(r"(?V0)(x)?(y)?", r"\2-\1", "y"), 'y--')
        else:
            self.assertEqual(regex.sub(r"(?V0)(x)?(y)?", r"\2-\1", "y"), 'y-')
        self.assertEqual(regex.sub(r"(?V1)(x)?(y)?", r"\2-\1", "y"), 'y--')

    def test_bug_10328 (self):
        # Issue 10328.
        pat = regex.compile(r'(?mV0)(?P<trailing_ws>[ \t]+\r*$)|(?P<no_final_newline>(?<=[^\n])\Z)')
        if sys.version_info >= (3, 7, 0):
            self.assertEqual(pat.subn(lambda m: '<' + m.lastgroup + '>',
              'foobar '), ('foobar<trailing_ws><no_final_newline>', 2))
        else:
            self.assertEqual(pat.subn(lambda m: '<' + m.lastgroup + '>',
              'foobar '), ('foobar<trailing_ws>', 1))
        self.assertEqual([m.group() for m in pat.finditer('foobar ')], [' ',
          ''])
        pat = regex.compile(r'(?mV1)(?P<trailing_ws>[ \t]+\r*$)|(?P<no_final_newline>(?<=[^\n])\Z)')
        self.assertEqual(pat.subn(lambda m: '<' + m.lastgroup + '>',
          'foobar '), ('foobar<trailing_ws><no_final_newline>', 2))
        self.assertEqual([m.group() for m in pat.finditer('foobar ')], [' ',
          ''])

    def test_overlapped(self):
        self.assertEqual(regex.findall(r"..", "abcde"), ['ab', 'cd'])
        self.assertEqual(regex.findall(r"..", "abcde", overlapped=True), ['ab',
          'bc', 'cd', 'de'])
        self.assertEqual(regex.findall(r"(?r)..", "abcde"), ['de', 'bc'])
        self.assertEqual(regex.findall(r"(?r)..", "abcde", overlapped=True),
          ['de', 'cd', 'bc', 'ab'])
        self.assertEqual(regex.findall(r"(.)(-)(.)", "a-b-c", overlapped=True),
          [("a", "-", "b"), ("b", "-", "c")])

        self.assertEqual([m[0] for m in regex.finditer(r"..", "abcde")], ['ab',
          'cd'])
        self.assertEqual([m[0] for m in regex.finditer(r"..", "abcde",
          overlapped=True)], ['ab', 'bc', 'cd', 'de'])
        self.assertEqual([m[0] for m in regex.finditer(r"(?r)..", "abcde")],
          ['de', 'bc'])
        self.assertEqual([m[0] for m in regex.finditer(r"(?r)..", "abcde",
          overlapped=True)], ['de', 'cd', 'bc', 'ab'])

        self.assertEqual([m.groups() for m in regex.finditer(r"(.)(-)(.)",
          "a-b-c", overlapped=True)], [("a", "-", "b"), ("b", "-", "c")])
        self.assertEqual([m.groups() for m in regex.finditer(r"(?r)(.)(-)(.)",
          "a-b-c", overlapped=True)], [("b", "-", "c"), ("a", "-", "b")])

    def test_splititer(self):
        self.assertEqual(regex.split(r",", "a,b,,c,"), ['a', 'b', '', 'c', ''])
        self.assertEqual([m for m in regex.splititer(r",", "a,b,,c,")], ['a',
          'b', '', 'c', ''])

    def test_grapheme(self):
        self.assertEqual(regex.match(r"\X", "\xE0").span(), (0, 1))
        self.assertEqual(regex.match(r"\X", "a\u0300").span(), (0, 2))

        self.assertEqual(regex.findall(r"\X",
          "a\xE0a\u0300e\xE9e\u0301"), ['a', '\xe0', 'a\u0300', 'e',
          '\xe9', 'e\u0301'])
        self.assertEqual(regex.findall(r"\X{3}",
          "a\xE0a\u0300e\xE9e\u0301"), ['a\xe0a\u0300', 'e\xe9e\u0301'])
        self.assertEqual(regex.findall(r"\X", "\r\r\n\u0301A\u0301"),
          ['\r', '\r\n', '\u0301', 'A\u0301'])

    def test_word_boundary(self):
        text = 'The quick ("brown") fox can\'t jump 32.3 feet, right?'
        self.assertEqual(regex.split(r'(?V1)\b', text), ['', 'The', ' ',
          'quick', ' ("', 'brown', '") ', 'fox', ' ', 'can', "'", 't',
          ' ', 'jump', ' ', '32', '.', '3', ' ', 'feet', ', ',
          'right', '?'])
        self.assertEqual(regex.split(r'(?V1w)\b', text), ['', 'The', ' ',
          'quick', ' ', '(', '"', 'brown', '"', ')', ' ', 'fox', ' ',
          "can't", ' ', 'jump', ' ', '32.3', ' ', 'feet', ',', ' ',
          'right', '?', ''])

        text = "The  fox"
        self.assertEqual(regex.split(r'(?V1)\b', text), ['', 'The', '  ',
          'fox', ''])
        self.assertEqual(regex.split(r'(?V1w)\b', text), ['', 'The', '  ',
          'fox', ''])

        text = "can't aujourd'hui l'objectif"
        self.assertEqual(regex.split(r'(?V1)\b', text), ['', 'can', "'",
          't', ' ', 'aujourd', "'", 'hui', ' ', 'l', "'", 'objectif',
          ''])
        self.assertEqual(regex.split(r'(?V1w)\b', text), ['', "can't", ' ',
          "aujourd'hui", ' ', "l'objectif", ''])

    def test_line_boundary(self):
        self.assertEqual(regex.findall(r".+", "Line 1\nLine 2\n"), ["Line 1",
          "Line 2"])
        self.assertEqual(regex.findall(r".+", "Line 1\rLine 2\r"),
          ["Line 1\rLine 2\r"])
        self.assertEqual(regex.findall(r".+", "Line 1\r\nLine 2\r\n"),
          ["Line 1\r", "Line 2\r"])
        self.assertEqual(regex.findall(r"(?w).+", "Line 1\nLine 2\n"),
          ["Line 1", "Line 2"])
        self.assertEqual(regex.findall(r"(?w).+", "Line 1\rLine 2\r"),
          ["Line 1", "Line 2"])
        self.assertEqual(regex.findall(r"(?w).+", "Line 1\r\nLine 2\r\n"),
          ["Line 1", "Line 2"])

        self.assertEqual(regex.search(r"^abc", "abc").start(), 0)
        self.assertEqual(regex.search(r"^abc", "\nabc"), None)
        self.assertEqual(regex.search(r"^abc", "\rabc"), None)
        self.assertEqual(regex.search(r"(?w)^abc", "abc").start(), 0)
        self.assertEqual(regex.search(r"(?w)^abc", "\nabc"), None)
        self.assertEqual(regex.search(r"(?w)^abc", "\rabc"), None)

        self.assertEqual(regex.search(r"abc$", "abc").start(), 0)
        self.assertEqual(regex.search(r"abc$", "abc\n").start(), 0)
        self.assertEqual(regex.search(r"abc$", "abc\r"), None)
        self.assertEqual(regex.search(r"(?w)abc$", "abc").start(), 0)
        self.assertEqual(regex.search(r"(?w)abc$", "abc\n").start(), 0)
        self.assertEqual(regex.search(r"(?w)abc$", "abc\r").start(), 0)

        self.assertEqual(regex.search(r"(?m)^abc", "abc").start(), 0)
        self.assertEqual(regex.search(r"(?m)^abc", "\nabc").start(), 1)
        self.assertEqual(regex.search(r"(?m)^abc", "\rabc"), None)
        self.assertEqual(regex.search(r"(?mw)^abc", "abc").start(), 0)
        self.assertEqual(regex.search(r"(?mw)^abc", "\nabc").start(), 1)
        self.assertEqual(regex.search(r"(?mw)^abc", "\rabc").start(), 1)

        self.assertEqual(regex.search(r"(?m)abc$", "abc").start(), 0)
        self.assertEqual(regex.search(r"(?m)abc$", "abc\n").start(), 0)
        self.assertEqual(regex.search(r"(?m)abc$", "abc\r"), None)
        self.assertEqual(regex.search(r"(?mw)abc$", "abc").start(), 0)
        self.assertEqual(regex.search(r"(?mw)abc$", "abc\n").start(), 0)
        self.assertEqual(regex.search(r"(?mw)abc$", "abc\r").start(), 0)

    def test_branch_reset(self):
        self.assertEqual(regex.match(r"(?:(a)|(b))(c)", "ac").groups(), ('a',
          None, 'c'))
        self.assertEqual(regex.match(r"(?:(a)|(b))(c)", "bc").groups(), (None,
          'b', 'c'))
        self.assertEqual(regex.match(r"(?:(?<a>a)|(?<b>b))(?<c>c)",
          "ac").groups(), ('a', None, 'c'))
        self.assertEqual(regex.match(r"(?:(?<a>a)|(?<b>b))(?<c>c)",
          "bc").groups(), (None, 'b', 'c'))

        self.assertEqual(regex.match(r"(?<a>a)(?:(?<b>b)|(?<c>c))(?<d>d)",
          "abd").groups(), ('a', 'b', None, 'd'))
        self.assertEqual(regex.match(r"(?<a>a)(?:(?<b>b)|(?<c>c))(?<d>d)",
          "acd").groups(), ('a', None, 'c', 'd'))
        self.assertEqual(regex.match(r"(a)(?:(b)|(c))(d)", "abd").groups(),
          ('a', 'b', None, 'd'))

        self.assertEqual(regex.match(r"(a)(?:(b)|(c))(d)", "acd").groups(),
          ('a', None, 'c', 'd'))
        self.assertEqual(regex.match(r"(a)(?|(b)|(b))(d)", "abd").groups(),
          ('a', 'b', 'd'))
        self.assertEqual(regex.match(r"(?|(?<a>a)|(?<b>b))(c)", "ac").groups(),
          ('a', None, 'c'))
        self.assertEqual(regex.match(r"(?|(?<a>a)|(?<b>b))(c)", "bc").groups(),
          (None, 'b', 'c'))
        self.assertEqual(regex.match(r"(?|(?<a>a)|(?<a>b))(c)", "ac").groups(),
          ('a', 'c'))

        self.assertEqual(regex.match(r"(?|(?<a>a)|(?<a>b))(c)", "bc").groups(),
          ('b', 'c'))

        self.assertEqual(regex.match(r"(?|(?<a>a)(?<b>b)|(?<b>c)(?<a>d))(e)",
          "abe").groups(), ('a', 'b', 'e'))
        self.assertEqual(regex.match(r"(?|(?<a>a)(?<b>b)|(?<b>c)(?<a>d))(e)",
          "cde").groups(), ('d', 'c', 'e'))
        self.assertEqual(regex.match(r"(?|(?<a>a)(?<b>b)|(?<b>c)(d))(e)",
          "abe").groups(), ('a', 'b', 'e'))
        self.assertEqual(regex.match(r"(?|(?<a>a)(?<b>b)|(?<b>c)(d))(e)",
          "cde").groups(), ('d', 'c', 'e'))
        self.assertEqual(regex.match(r"(?|(?<a>a)(?<b>b)|(c)(d))(e)",
          "abe").groups(), ('a', 'b', 'e'))
        self.assertEqual(regex.match(r"(?|(?<a>a)(?<b>b)|(c)(d))(e)",
          "cde").groups(), ('c', 'd', 'e'))

        # Hg issue 87: Allow duplicate names of groups
        self.assertEqual(regex.match(r"(?|(?<a>a)(?<b>b)|(c)(?<a>d))(e)",
          "abe").groups(), ("a", "b", "e"))
        self.assertEqual(regex.match(r"(?|(?<a>a)(?<b>b)|(c)(?<a>d))(e)",
          "abe").capturesdict(), {"a": ["a"], "b": ["b"]})
        self.assertEqual(regex.match(r"(?|(?<a>a)(?<b>b)|(c)(?<a>d))(e)",
          "cde").groups(), ("d", None, "e"))
        self.assertEqual(regex.match(r"(?|(?<a>a)(?<b>b)|(c)(?<a>d))(e)",
          "cde").capturesdict(), {"a": ["c", "d"], "b": []})

    def test_set(self):
        self.assertEqual(regex.match(r"[a]", "a").span(), (0, 1))
        self.assertEqual(regex.match(r"(?i)[a]", "A").span(), (0, 1))
        self.assertEqual(regex.match(r"[a-b]", r"a").span(), (0, 1))
        self.assertEqual(regex.match(r"(?i)[a-b]", r"A").span(), (0, 1))

        self.assertEqual(regex.sub(r"(?V0)([][])", r"-", "a[b]c"), "a-b-c")

        self.assertEqual(regex.findall(r"[\p{Alpha}]", "a0"), ["a"])
        self.assertEqual(regex.findall(r"(?i)[\p{Alpha}]", "A0"), ["A"])

        self.assertEqual(regex.findall(r"[a\p{Alpha}]", "ab0"), ["a", "b"])
        self.assertEqual(regex.findall(r"[a\P{Alpha}]", "ab0"), ["a", "0"])
        self.assertEqual(regex.findall(r"(?i)[a\p{Alpha}]", "ab0"), ["a",
          "b"])
        self.assertEqual(regex.findall(r"(?i)[a\P{Alpha}]", "ab0"), ["a",
          "0"])

        self.assertEqual(regex.findall(r"[a-b\p{Alpha}]", "abC0"), ["a",
          "b", "C"])
        self.assertEqual(regex.findall(r"(?i)[a-b\p{Alpha}]", "AbC0"), ["A",
          "b", "C"])

        self.assertEqual(regex.findall(r"[\p{Alpha}]", "a0"), ["a"])
        self.assertEqual(regex.findall(r"[\P{Alpha}]", "a0"), ["0"])
        self.assertEqual(regex.findall(r"[^\p{Alpha}]", "a0"), ["0"])
        self.assertEqual(regex.findall(r"[^\P{Alpha}]", "a0"), ["a"])

        self.assertEqual("".join(regex.findall(r"[^\d-h]", "a^b12c-h")),
          'a^bc')
        self.assertEqual("".join(regex.findall(r"[^\dh]", "a^b12c-h")),
          'a^bc-')
        self.assertEqual("".join(regex.findall(r"[^h\s\db]", "a^b 12c-h")),
          'a^c-')
        self.assertEqual("".join(regex.findall(r"[^b\w]", "a b")), ' ')
        self.assertEqual("".join(regex.findall(r"[^b\S]", "a b")), ' ')
        self.assertEqual("".join(regex.findall(r"[^8\d]", "a 1b2")), 'a b')

        all_chars = "".join(chr(c) for c in range(0x100))
        self.assertEqual(len(regex.findall(r"\p{ASCII}", all_chars)), 128)
        self.assertEqual(len(regex.findall(r"\p{Letter}", all_chars)),
          117)
        self.assertEqual(len(regex.findall(r"\p{Digit}", all_chars)), 10)

        # Set operators
        self.assertEqual(len(regex.findall(r"(?V1)[\p{ASCII}&&\p{Letter}]",
          all_chars)), 52)
        self.assertEqual(len(regex.findall(r"(?V1)[\p{ASCII}&&\p{Alnum}&&\p{Letter}]",
          all_chars)), 52)
        self.assertEqual(len(regex.findall(r"(?V1)[\p{ASCII}&&\p{Alnum}&&\p{Digit}]",
          all_chars)), 10)
        self.assertEqual(len(regex.findall(r"(?V1)[\p{ASCII}&&\p{Cc}]",
          all_chars)), 33)
        self.assertEqual(len(regex.findall(r"(?V1)[\p{ASCII}&&\p{Graph}]",
          all_chars)), 94)
        self.assertEqual(len(regex.findall(r"(?V1)[\p{ASCII}--\p{Cc}]",
          all_chars)), 95)
        self.assertEqual(len(regex.findall(r"[\p{Letter}\p{Digit}]",
          all_chars)), 127)
        self.assertEqual(len(regex.findall(r"(?V1)[\p{Letter}||\p{Digit}]",
          all_chars)), 127)
        self.assertEqual(len(regex.findall(r"\p{HexDigit}", all_chars)),
          22)
        self.assertEqual(len(regex.findall(r"(?V1)[\p{HexDigit}~~\p{Digit}]",
          all_chars)), 12)
        self.assertEqual(len(regex.findall(r"(?V1)[\p{Digit}~~\p{HexDigit}]",
          all_chars)), 12)

        self.assertEqual(repr(type(regex.compile(r"(?V0)([][-])"))),
          self.PATTERN_CLASS)
        self.assertEqual(regex.findall(r"(?V1)[[a-z]--[aei]]", "abc"), ["b",
          "c"])
        self.assertEqual(regex.findall(r"(?iV1)[[a-z]--[aei]]", "abc"), ["b",
          "c"])
        self.assertEqual(regex.findall(r"(?V1)[\w--a]","abc"), ["b", "c"])
        self.assertEqual(regex.findall(r"(?iV1)[\w--a]","abc"), ["b", "c"])

    def test_various(self):
        tests = [
            # Test ?P< and ?P= extensions.
            ('(?P<foo_123', '', '', regex.error, self.MISSING_GT),      # Unterminated group identifier.
            ('(?P<1>a)', '', '', regex.error, self.BAD_GROUP_NAME),     # Begins with a digit.
            ('(?P<!>a)', '', '', regex.error, self.BAD_GROUP_NAME),     # Begins with an illegal char.
            ('(?P<foo!>a)', '', '', regex.error, self.BAD_GROUP_NAME),  # Begins with an illegal char.

            # Same tests, for the ?P= form.
            ('(?P<foo_123>a)(?P=foo_123', 'aa', '', regex.error,
              self.MISSING_RPAREN),
            ('(?P<foo_123>a)(?P=1)', 'aa', '1', ascii('a')),
            ('(?P<foo_123>a)(?P=0)', 'aa', '', regex.error,
              self.BAD_GROUP_NAME),
            ('(?P<foo_123>a)(?P=-1)', 'aa', '', regex.error,
              self.BAD_GROUP_NAME),
            ('(?P<foo_123>a)(?P=!)', 'aa', '', regex.error,
              self.BAD_GROUP_NAME),
            ('(?P<foo_123>a)(?P=foo_124)', 'aa', '', regex.error,
              self.UNKNOWN_GROUP),  # Backref to undefined group.

            ('(?P<foo_123>a)', 'a', '1', ascii('a')),
            ('(?P<foo_123>a)(?P=foo_123)', 'aa', '1', ascii('a')),

            # Mal-formed \g in pattern treated as literal for compatibility.
            (r'(?<foo_123>a)\g<foo_123', 'aa', '', ascii(None)),
            (r'(?<foo_123>a)\g<1>', 'aa', '1', ascii('a')),
            (r'(?<foo_123>a)\g<!>', 'aa', '', ascii(None)),
            (r'(?<foo_123>a)\g<foo_124>', 'aa', '', regex.error,
              self.UNKNOWN_GROUP),  # Backref to undefined group.

            ('(?<foo_123>a)', 'a', '1', ascii('a')),
            (r'(?<foo_123>a)\g<foo_123>', 'aa', '1', ascii('a')),

            # Test octal escapes.
            ('\\1', 'a', '', regex.error, self.INVALID_GROUP_REF),    # Backreference.
            ('[\\1]', '\1', '0', "'\\x01'"),  # Character.
            ('\\09', chr(0) + '9', '0', ascii(chr(0) + '9')),
            ('\\141', 'a', '0', ascii('a')),
            ('(a)(b)(c)(d)(e)(f)(g)(h)(i)(j)(k)(l)\\119', 'abcdefghijklk9',
              '0,11', ascii(('abcdefghijklk9', 'k'))),

            # Test \0 is handled everywhere.
            (r'\0', '\0', '0', ascii('\0')),
            (r'[\0a]', '\0', '0', ascii('\0')),
            (r'[a\0]', '\0', '0', ascii('\0')),
            (r'[^a\0]', '\0', '', ascii(None)),

            # Test various letter escapes.
            (r'\a[\b]\f\n\r\t\v', '\a\b\f\n\r\t\v', '0',
              ascii('\a\b\f\n\r\t\v')),
            (r'[\a][\b][\f][\n][\r][\t][\v]', '\a\b\f\n\r\t\v', '0',
              ascii('\a\b\f\n\r\t\v')),
            (r'\xff', '\377', '0', ascii(chr(255))),

            # New \x semantics.
            (r'\x00ffffffffffffff', '\377', '', ascii(None)),
            (r'\x00f', '\017', '', ascii(None)),
            (r'\x00fe', '\376', '', ascii(None)),

            (r'\x00ff', '\377', '', ascii(None)),
            (r'\t\n\v\r\f\a\g', '\t\n\v\r\f\ag', '0', ascii('\t\n\v\r\f\ag')),
            ('\t\n\v\r\f\a\\g', '\t\n\v\r\f\ag', '0', ascii('\t\n\v\r\f\ag')),
            (r'\t\n\v\r\f\a', '\t\n\v\r\f\a', '0', ascii(chr(9) + chr(10) +
              chr(11) + chr(13) + chr(12) + chr(7))),
            (r'[\t][\n][\v][\r][\f][\b]', '\t\n\v\r\f\b', '0',
              ascii('\t\n\v\r\f\b')),

            (r"^\w+=(\\[\000-\277]|[^\n\\])*",
              "SRC=eval.c g.c blah blah blah \\\\\n\tapes.c", '0',
              ascii("SRC=eval.c g.c blah blah blah \\\\")),

            # Test that . only matches \n in DOTALL mode.
            ('a.b', 'acb', '0', ascii('acb')),
            ('a.b', 'a\nb', '', ascii(None)),
            ('a.*b', 'acc\nccb', '', ascii(None)),
            ('a.{4,5}b', 'acc\nccb', '', ascii(None)),
            ('a.b', 'a\rb', '0', ascii('a\rb')),
            # Changed to positional flags in regex 2023.12.23.
            ('a.b(?s)', 'a\nb', '', ascii(None)),
            ('(?s)a.b', 'a\nb', '0', ascii('a\nb')),
            ('a.*(?s)b', 'acc\nccb', '', ascii(None)),
            ('(?s)a.*b', 'acc\nccb', '0', ascii('acc\nccb')),
            ('(?s)a.{4,5}b', 'acc\nccb', '0', ascii('acc\nccb')),

            (')', '', '', regex.error, self.TRAILING_CHARS),           # Unmatched right bracket.
            ('', '', '0', "''"),    # Empty pattern.
            ('abc', 'abc', '0', ascii('abc')),
            ('abc', 'xbc', '', ascii(None)),
            ('abc', 'axc', '', ascii(None)),
            ('abc', 'abx', '', ascii(None)),
            ('abc', 'xabcy', '0', ascii('abc')),
            ('abc', 'ababc', '0', ascii('abc')),
            ('ab*c', 'abc', '0', ascii('abc')),
            ('ab*bc', 'abc', '0', ascii('abc')),

            ('ab*bc', 'abbc', '0', ascii('abbc')),
            ('ab*bc', 'abbbbc', '0', ascii('abbbbc')),
            ('ab+bc', 'abbc', '0', ascii('abbc')),
            ('ab+bc', 'abc', '', ascii(None)),
            ('ab+bc', 'abq', '', ascii(None)),
            ('ab+bc', 'abbbbc', '0', ascii('abbbbc')),
            ('ab?bc', 'abbc', '0', ascii('abbc')),
            ('ab?bc', 'abc', '0', ascii('abc')),
            ('ab?bc', 'abbbbc', '', ascii(None)),
            ('ab?c', 'abc', '0', ascii('abc')),

            ('^abc$', 'abc', '0', ascii('abc')),
            ('^abc$', 'abcc', '', ascii(None)),
            ('^abc', 'abcc', '0', ascii('abc')),
            ('^abc$', 'aabc', '', ascii(None)),
            ('abc$', 'aabc', '0', ascii('abc')),
            ('^', 'abc', '0', ascii('')),
            ('$', 'abc', '0', ascii('')),
            ('a.c', 'abc', '0', ascii('abc')),
            ('a.c', 'axc', '0', ascii('axc')),
            ('a.*c', 'axyzc', '0', ascii('axyzc')),

            ('a.*c', 'axyzd', '', ascii(None)),
            ('a[bc]d', 'abc', '', ascii(None)),
            ('a[bc]d', 'abd', '0', ascii('abd')),
            ('a[b-d]e', 'abd', '', ascii(None)),
            ('a[b-d]e', 'ace', '0', ascii('ace')),
            ('a[b-d]', 'aac', '0', ascii('ac')),
            ('a[-b]', 'a-', '0', ascii('a-')),
            ('a[\\-b]', 'a-', '0', ascii('a-')),
            ('a[b-]', 'a-', '0', ascii('a-')),
            ('a[]b', '-', '', regex.error, self.BAD_SET),

            ('a[', '-', '', regex.error, self.BAD_SET),
            ('a\\', '-', '', regex.error, self.BAD_ESCAPE),
            ('abc)', '-', '', regex.error, self.TRAILING_CHARS),
            ('(abc', '-', '', regex.error, self.MISSING_RPAREN),
            ('a]', 'a]', '0', ascii('a]')),
            ('a[]]b', 'a]b', '0', ascii('a]b')),
            ('a[]]b', 'a]b', '0', ascii('a]b')),
            ('a[^bc]d', 'aed', '0', ascii('aed')),
            ('a[^bc]d', 'abd', '', ascii(None)),
            ('a[^-b]c', 'adc', '0', ascii('adc')),

            ('a[^-b]c', 'a-c', '', ascii(None)),
            ('a[^]b]c', 'a]c', '', ascii(None)),
            ('a[^]b]c', 'adc', '0', ascii('adc')),
            ('\\ba\\b', 'a-', '0', ascii('a')),
            ('\\ba\\b', '-a', '0', ascii('a')),
            ('\\ba\\b', '-a-', '0', ascii('a')),
            ('\\by\\b', 'xy', '', ascii(None)),
            ('\\by\\b', 'yz', '', ascii(None)),
            ('\\by\\b', 'xyz', '', ascii(None)),
            ('x\\b', 'xyz', '', ascii(None)),

            ('x\\B', 'xyz', '0', ascii('x')),
            ('\\Bz', 'xyz', '0', ascii('z')),
            ('z\\B', 'xyz', '', ascii(None)),
            ('\\Bx', 'xyz', '', ascii(None)),
            ('\\Ba\\B', 'a-', '', ascii(None)),
            ('\\Ba\\B', '-a', '', ascii(None)),
            ('\\Ba\\B', '-a-', '', ascii(None)),
            ('\\By\\B', 'xy', '', ascii(None)),
            ('\\By\\B', 'yz', '', ascii(None)),
            ('\\By\\b', 'xy', '0', ascii('y')),

            ('\\by\\B', 'yz', '0', ascii('y')),
            ('\\By\\B', 'xyz', '0', ascii('y')),
            ('ab|cd', 'abc', '0', ascii('ab')),
            ('ab|cd', 'abcd', '0', ascii('ab')),
            ('()ef', 'def', '0,1', ascii(('ef', ''))),
            ('$b', 'b', '', ascii(None)),
            ('a\\(b', 'a(b', '', ascii(('a(b',))),
            ('a\\(*b', 'ab', '0', ascii('ab')),
            ('a\\(*b', 'a((b', '0', ascii('a((b')),
            ('a\\\\b', 'a\\b', '0', ascii('a\\b')),

            ('((a))', 'abc', '0,1,2', ascii(('a', 'a', 'a'))),
            ('(a)b(c)', 'abc', '0,1,2', ascii(('abc', 'a', 'c'))),
            ('a+b+c', 'aabbabc', '0', ascii('abc')),
            ('(a+|b)*', 'ab', '0,1', ascii(('ab', 'b'))),
            ('(a+|b)+', 'ab', '0,1', ascii(('ab', 'b'))),
            ('(a+|b)?', 'ab', '0,1', ascii(('a', 'a'))),
            (')(', '-', '', regex.error, self.TRAILING_CHARS),
            ('[^ab]*', 'cde', '0', ascii('cde')),
            ('abc', '', '', ascii(None)),
            ('a*', '', '0', ascii('')),

            ('a|b|c|d|e', 'e', '0', ascii('e')),
            ('(a|b|c|d|e)f', 'ef', '0,1', ascii(('ef', 'e'))),
            ('abcd*efg', 'abcdefg', '0', ascii('abcdefg')),
            ('ab*', 'xabyabbbz', '0', ascii('ab')),
            ('ab*', 'xayabbbz', '0', ascii('a')),
            ('(ab|cd)e', 'abcde', '0,1', ascii(('cde', 'cd'))),
            ('[abhgefdc]ij', 'hij', '0', ascii('hij')),
            ('^(ab|cd)e', 'abcde', '', ascii(None)),
            ('(abc|)ef', 'abcdef', '0,1', ascii(('ef', ''))),
            ('(a|b)c*d', 'abcd', '0,1', ascii(('bcd', 'b'))),

            ('(ab|ab*)bc', 'abc', '0,1', ascii(('abc', 'a'))),
            ('a([bc]*)c*', 'abc', '0,1', ascii(('abc', 'bc'))),
            ('a([bc]*)(c*d)', 'abcd', '0,1,2', ascii(('abcd', 'bc', 'd'))),
            ('a([bc]+)(c*d)', 'abcd', '0,1,2', ascii(('abcd', 'bc', 'd'))),
            ('a([bc]*)(c+d)', 'abcd', '0,1,2', ascii(('abcd', 'b', 'cd'))),
            ('a[bcd]*dcdcde', 'adcdcde', '0', ascii('adcdcde')),
            ('a[bcd]+dcdcde', 'adcdcde', '', ascii(None)),
            ('(ab|a)b*c', 'abc', '0,1', ascii(('abc', 'ab'))),
            ('((a)(b)c)(d)', 'abcd', '1,2,3,4', ascii(('abc', 'a', 'b', 'd'))),
            ('[a-zA-Z_][a-zA-Z0-9_]*', 'alpha', '0', ascii('alpha')),

            ('^a(bc+|b[eh])g|.h$', 'abh', '0,1', ascii(('bh', None))),
            ('(bc+d$|ef*g.|h?i(j|k))', 'effgz', '0,1,2', ascii(('effgz',
              'effgz', None))),
            ('(bc+d$|ef*g.|h?i(j|k))', 'ij', '0,1,2', ascii(('ij', 'ij',
              'j'))),
            ('(bc+d$|ef*g.|h?i(j|k))', 'effg', '', ascii(None)),
            ('(bc+d$|ef*g.|h?i(j|k))', 'bcdd', '', ascii(None)),
            ('(bc+d$|ef*g.|h?i(j|k))', 'reffgz', '0,1,2', ascii(('effgz',
              'effgz', None))),
            ('(((((((((a)))))))))', 'a', '0', ascii('a')),
            ('multiple words of text', 'uh-uh', '', ascii(None)),
            ('multiple words', 'multiple words, yeah', '0',
              ascii('multiple words')),
            ('(.*)c(.*)', 'abcde', '0,1,2', ascii(('abcde', 'ab', 'de'))),

            ('\\((.*), (.*)\\)', '(a, b)', '2,1', ascii(('b', 'a'))),
            ('[k]', 'ab', '', ascii(None)),
            ('a[-]?c', 'ac', '0', ascii('ac')),
            ('(abc)\\1', 'abcabc', '1', ascii('abc')),
            ('([a-c]*)\\1', 'abcabc', '1', ascii('abc')),
            ('^(.+)?B', 'AB', '1', ascii('A')),
            ('(a+).\\1$', 'aaaaa', '0,1', ascii(('aaaaa', 'aa'))),
            ('^(a+).\\1$', 'aaaa', '', ascii(None)),
            ('(abc)\\1', 'abcabc', '0,1', ascii(('abcabc', 'abc'))),
            ('([a-c]+)\\1', 'abcabc', '0,1', ascii(('abcabc', 'abc'))),

            ('(a)\\1', 'aa', '0,1', ascii(('aa', 'a'))),
            ('(a+)\\1', 'aa', '0,1', ascii(('aa', 'a'))),
            ('(a+)+\\1', 'aa', '0,1', ascii(('aa', 'a'))),
            ('(a).+\\1', 'aba', '0,1', ascii(('aba', 'a'))),
            ('(a)ba*\\1', 'aba', '0,1', ascii(('aba', 'a'))),
            ('(aa|a)a\\1$', 'aaa', '0,1', ascii(('aaa', 'a'))),
            ('(a|aa)a\\1$', 'aaa', '0,1', ascii(('aaa', 'a'))),
            ('(a+)a\\1$', 'aaa', '0,1', ascii(('aaa', 'a'))),
            ('([abc]*)\\1', 'abcabc', '0,1', ascii(('abcabc', 'abc'))),
            ('(a)(b)c|ab', 'ab', '0,1,2', ascii(('ab', None, None))),

            ('(a)+x', 'aaax', '0,1', ascii(('aaax', 'a'))),
            ('([ac])+x', 'aacx', '0,1', ascii(('aacx', 'c'))),
            ('([^/]*/)*sub1/', 'd:msgs/tdir/sub1/trial/away.cpp', '0,1',
              ascii(('d:msgs/tdir/sub1/', 'tdir/'))),
            ('([^.]*)\\.([^:]*):[T ]+(.*)', 'track1.title:TBlah blah blah',
              '0,1,2,3', ascii(('track1.title:TBlah blah blah', 'track1',
              'title', 'Blah blah blah'))),
            ('([^N]*N)+', 'abNNxyzN', '0,1', ascii(('abNNxyzN', 'xyzN'))),
            ('([^N]*N)+', 'abNNxyz', '0,1', ascii(('abNN', 'N'))),
            ('([abc]*)x', 'abcx', '0,1', ascii(('abcx', 'abc'))),
            ('([abc]*)x', 'abc', '', ascii(None)),
            ('([xyz]*)x', 'abcx', '0,1', ascii(('x', ''))),
            ('(a)+b|aac', 'aac', '0,1', ascii(('aac', None))),

            # Test symbolic groups.
            ('(?P<i d>aaa)a', 'aaaa', '', regex.error, self.BAD_GROUP_NAME),
            ('(?P<id>aaa)a', 'aaaa', '0,id', ascii(('aaaa', 'aaa'))),
            ('(?P<id>aa)(?P=id)', 'aaaa', '0,id', ascii(('aaaa', 'aa'))),
            ('(?P<id>aa)(?P=xd)', 'aaaa', '', regex.error, self.UNKNOWN_GROUP),

            # Character properties.
            (r"\g", "g", '0', ascii('g')),
            (r"\g<1>", "g", '', regex.error, self.INVALID_GROUP_REF),
            (r"(.)\g<1>", "gg", '0', ascii('gg')),
            (r"(.)\g<1>", "gg", '', ascii(('gg', 'g'))),
            (r"\N", "N", '0', ascii('N')),
            (r"\N{LATIN SMALL LETTER A}", "a", '0', ascii('a')),
            (r"\p", "p", '0', ascii('p')),
            (r"\p{Ll}", "a", '0', ascii('a')),
            (r"\P", "P", '0', ascii('P')),
            (r"\P{Lu}", "p", '0', ascii('p')),

            # All tests from Perl.
            ('abc', 'abc', '0', ascii('abc')),
            ('abc', 'xbc', '', ascii(None)),
            ('abc', 'axc', '', ascii(None)),
            ('abc', 'abx', '', ascii(None)),
            ('abc', 'xabcy', '0', ascii('abc')),
            ('abc', 'ababc', '0', ascii('abc')),

            ('ab*c', 'abc', '0', ascii('abc')),
            ('ab*bc', 'abc', '0', ascii('abc')),
            ('ab*bc', 'abbc', '0', ascii('abbc')),
            ('ab*bc', 'abbbbc', '0', ascii('abbbbc')),
            ('ab{0,}bc', 'abbbbc', '0', ascii('abbbbc')),
            ('ab+bc', 'abbc', '0', ascii('abbc')),
            ('ab+bc', 'abc', '', ascii(None)),
            ('ab+bc', 'abq', '', ascii(None)),
            ('ab{1,}bc', 'abq', '', ascii(None)),
            ('ab+bc', 'abbbbc', '0', ascii('abbbbc')),

            ('ab{1,}bc', 'abbbbc', '0', ascii('abbbbc')),
            ('ab{1,3}bc', 'abbbbc', '0', ascii('abbbbc')),
            ('ab{3,4}bc', 'abbbbc', '0', ascii('abbbbc')),
            ('ab{4,5}bc', 'abbbbc', '', ascii(None)),
            ('ab?bc', 'abbc', '0', ascii('abbc')),
            ('ab?bc', 'abc', '0', ascii('abc')),
            ('ab{0,1}bc', 'abc', '0', ascii('abc')),
            ('ab?bc', 'abbbbc', '', ascii(None)),
            ('ab?c', 'abc', '0', ascii('abc')),
            ('ab{0,1}c', 'abc', '0', ascii('abc')),

            ('^abc$', 'abc', '0', ascii('abc')),
            ('^abc$', 'abcc', '', ascii(None)),
            ('^abc', 'abcc', '0', ascii('abc')),
            ('^abc$', 'aabc', '', ascii(None)),
            ('abc$', 'aabc', '0', ascii('abc')),
            ('^', 'abc', '0', ascii('')),
            ('$', 'abc', '0', ascii('')),
            ('a.c', 'abc', '0', ascii('abc')),
            ('a.c', 'axc', '0', ascii('axc')),
            ('a.*c', 'axyzc', '0', ascii('axyzc')),

            ('a.*c', 'axyzd', '', ascii(None)),
            ('a[bc]d', 'abc', '', ascii(None)),
            ('a[bc]d', 'abd', '0', ascii('abd')),
            ('a[b-d]e', 'abd', '', ascii(None)),
            ('a[b-d]e', 'ace', '0', ascii('ace')),
            ('a[b-d]', 'aac', '0', ascii('ac')),
            ('a[-b]', 'a-', '0', ascii('a-')),
            ('a[b-]', 'a-', '0', ascii('a-')),
            ('a[b-a]', '-', '', regex.error, self.BAD_CHAR_RANGE),
            ('a[]b', '-', '', regex.error, self.BAD_SET),

            ('a[', '-', '', regex.error, self.BAD_SET),
            ('a]', 'a]', '0', ascii('a]')),
            ('a[]]b', 'a]b', '0', ascii('a]b')),
            ('a[^bc]d', 'aed', '0', ascii('aed')),
            ('a[^bc]d', 'abd', '', ascii(None)),
            ('a[^-b]c', 'adc', '0', ascii('adc')),
            ('a[^-b]c', 'a-c', '', ascii(None)),
            ('a[^]b]c', 'a]c', '', ascii(None)),
            ('a[^]b]c', 'adc', '0', ascii('adc')),
            ('ab|cd', 'abc', '0', ascii('ab')),

            ('ab|cd', 'abcd', '0', ascii('ab')),
            ('()ef', 'def', '0,1', ascii(('ef', ''))),
            ('*a', '-', '', regex.error, self.NOTHING_TO_REPEAT),
            ('(*)b', '-', '', regex.error, self.NOTHING_TO_REPEAT),
            ('$b', 'b', '', ascii(None)),
            ('a\\', '-', '', regex.error, self.BAD_ESCAPE),
            ('a\\(b', 'a(b', '', ascii(('a(b',))),
            ('a\\(*b', 'ab', '0', ascii('ab')),
            ('a\\(*b', 'a((b', '0', ascii('a((b')),
            ('a\\\\b', 'a\\b', '0', ascii('a\\b')),

            ('abc)', '-', '', regex.error, self.TRAILING_CHARS),
            ('(abc', '-', '', regex.error, self.MISSING_RPAREN),
            ('((a))', 'abc', '0,1,2', ascii(('a', 'a', 'a'))),
            ('(a)b(c)', 'abc', '0,1,2', ascii(('abc', 'a', 'c'))),
            ('a+b+c', 'aabbabc', '0', ascii('abc')),
            ('a{1,}b{1,}c', 'aabbabc', '0', ascii('abc')),
            ('a**', '-', '', regex.error, self.MULTIPLE_REPEAT),
            ('a.+?c', 'abcabc', '0', ascii('abc')),
            ('(a+|b)*', 'ab', '0,1', ascii(('ab', 'b'))),
            ('(a+|b){0,}', 'ab', '0,1', ascii(('ab', 'b'))),

            ('(a+|b)+', 'ab', '0,1', ascii(('ab', 'b'))),
            ('(a+|b){1,}', 'ab', '0,1', ascii(('ab', 'b'))),
            ('(a+|b)?', 'ab', '0,1', ascii(('a', 'a'))),
            ('(a+|b){0,1}', 'ab', '0,1', ascii(('a', 'a'))),
            (')(', '-', '', regex.error, self.TRAILING_CHARS),
            ('[^ab]*', 'cde', '0', ascii('cde')),
            ('abc', '', '', ascii(None)),
            ('a*', '', '0', ascii('')),
            ('([abc])*d', 'abbbcd', '0,1', ascii(('abbbcd', 'c'))),
            ('([abc])*bcd', 'abcd', '0,1', ascii(('abcd', 'a'))),

            ('a|b|c|d|e', 'e', '0', ascii('e')),
            ('(a|b|c|d|e)f', 'ef', '0,1', ascii(('ef', 'e'))),
            ('abcd*efg', 'abcdefg', '0', ascii('abcdefg')),
            ('ab*', 'xabyabbbz', '0', ascii('ab')),
            ('ab*', 'xayabbbz', '0', ascii('a')),
            ('(ab|cd)e', 'abcde', '0,1', ascii(('cde', 'cd'))),
            ('[abhgefdc]ij', 'hij', '0', ascii('hij')),
            ('^(ab|cd)e', 'abcde', '', ascii(None)),
            ('(abc|)ef', 'abcdef', '0,1', ascii(('ef', ''))),
            ('(a|b)c*d', 'abcd', '0,1', ascii(('bcd', 'b'))),

            ('(ab|ab*)bc', 'abc', '0,1', ascii(('abc', 'a'))),
            ('a([bc]*)c*', 'abc', '0,1', ascii(('abc', 'bc'))),
            ('a([bc]*)(c*d)', 'abcd', '0,1,2', ascii(('abcd', 'bc', 'd'))),
            ('a([bc]+)(c*d)', 'abcd', '0,1,2', ascii(('abcd', 'bc', 'd'))),
            ('a([bc]*)(c+d)', 'abcd', '0,1,2', ascii(('abcd', 'b', 'cd'))),
            ('a[bcd]*dcdcde', 'adcdcde', '0', ascii('adcdcde')),
            ('a[bcd]+dcdcde', 'adcdcde', '', ascii(None)),
            ('(ab|a)b*c', 'abc', '0,1', ascii(('abc', 'ab'))),
            ('((a)(b)c)(d)', 'abcd', '1,2,3,4', ascii(('abc', 'a', 'b', 'd'))),
            ('[a-zA-Z_][a-zA-Z0-9_]*', 'alpha', '0', ascii('alpha')),

            ('^a(bc+|b[eh])g|.h$', 'abh', '0,1', ascii(('bh', None))),
            ('(bc+d$|ef*g.|h?i(j|k))', 'effgz', '0,1,2', ascii(('effgz',
              'effgz', None))),
            ('(bc+d$|ef*g.|h?i(j|k))', 'ij', '0,1,2', ascii(('ij', 'ij',
              'j'))),
            ('(bc+d$|ef*g.|h?i(j|k))', 'effg', '', ascii(None)),
            ('(bc+d$|ef*g.|h?i(j|k))', 'bcdd', '', ascii(None)),
            ('(bc+d$|ef*g.|h?i(j|k))', 'reffgz', '0,1,2', ascii(('effgz',
              'effgz', None))),
            ('((((((((((a))))))))))', 'a', '10', ascii('a')),
            ('((((((((((a))))))))))\\10', 'aa', '0', ascii('aa')),

            # Python does not have the same rules for \\41 so this is a syntax error
            #    ('((((((((((a))))))))))\\41', 'aa', '', ascii(None)),
            #    ('((((((((((a))))))))))\\41', 'a!', '0', ascii('a!')),
            ('((((((((((a))))))))))\\41', '', '', regex.error,
              self.INVALID_GROUP_REF),
            ('(?i)((((((((((a))))))))))\\41', '', '', regex.error,
              self.INVALID_GROUP_REF),

            ('(((((((((a)))))))))', 'a', '0', ascii('a')),
            ('multiple words of text', 'uh-uh', '', ascii(None)),
            ('multiple words', 'multiple words, yeah', '0',
              ascii('multiple words')),
            ('(.*)c(.*)', 'abcde', '0,1,2', ascii(('abcde', 'ab', 'de'))),
            ('\\((.*), (.*)\\)', '(a, b)', '2,1', ascii(('b', 'a'))),
            ('[k]', 'ab', '', ascii(None)),
            ('a[-]?c', 'ac', '0', ascii('ac')),
            ('(abc)\\1', 'abcabc', '1', ascii('abc')),
            ('([a-c]*)\\1', 'abcabc', '1', ascii('abc')),
            ('(?i)abc', 'ABC', '0', ascii('ABC')),

            ('(?i)abc', 'XBC', '', ascii(None)),
            ('(?i)abc', 'AXC', '', ascii(None)),
            ('(?i)abc', 'ABX', '', ascii(None)),
            ('(?i)abc', 'XABCY', '0', ascii('ABC')),
            ('(?i)abc', 'ABABC', '0', ascii('ABC')),
            ('(?i)ab*c', 'ABC', '0', ascii('ABC')),
            ('(?i)ab*bc', 'ABC', '0', ascii('ABC')),
            ('(?i)ab*bc', 'ABBC', '0', ascii('ABBC')),
            ('(?i)ab*?bc', 'ABBBBC', '0', ascii('ABBBBC')),
            ('(?i)ab{0,}?bc', 'ABBBBC', '0', ascii('ABBBBC')),

            ('(?i)ab+?bc', 'ABBC', '0', ascii('ABBC')),
            ('(?i)ab+bc', 'ABC', '', ascii(None)),
            ('(?i)ab+bc', 'ABQ', '', ascii(None)),
            ('(?i)ab{1,}bc', 'ABQ', '', ascii(None)),
            ('(?i)ab+bc', 'ABBBBC', '0', ascii('ABBBBC')),
            ('(?i)ab{1,}?bc', 'ABBBBC', '0', ascii('ABBBBC')),
            ('(?i)ab{1,3}?bc', 'ABBBBC', '0', ascii('ABBBBC')),
            ('(?i)ab{3,4}?bc', 'ABBBBC', '0', ascii('ABBBBC')),
            ('(?i)ab{4,5}?bc', 'ABBBBC', '', ascii(None)),
            ('(?i)ab??bc', 'ABBC', '0', ascii('ABBC')),

            ('(?i)ab??bc', 'ABC', '0', ascii('ABC')),
            ('(?i)ab{0,1}?bc', 'ABC', '0', ascii('ABC')),
            ('(?i)ab??bc', 'ABBBBC', '', ascii(None)),
            ('(?i)ab??c', 'ABC', '0', ascii('ABC')),
            ('(?i)ab{0,1}?c', 'ABC', '0', ascii('ABC')),
            ('(?i)^abc$', 'ABC', '0', ascii('ABC')),
            ('(?i)^abc$', 'ABCC', '', ascii(None)),
            ('(?i)^abc', 'ABCC', '0', ascii('ABC')),
            ('(?i)^abc$', 'AABC', '', ascii(None)),
            ('(?i)abc$', 'AABC', '0', ascii('ABC')),

            ('(?i)^', 'ABC', '0', ascii('')),
            ('(?i)$', 'ABC', '0', ascii('')),
            ('(?i)a.c', 'ABC', '0', ascii('ABC')),
            ('(?i)a.c', 'AXC', '0', ascii('AXC')),
            ('(?i)a.*?c', 'AXYZC', '0', ascii('AXYZC')),
            ('(?i)a.*c', 'AXYZD', '', ascii(None)),
            ('(?i)a[bc]d', 'ABC', '', ascii(None)),
            ('(?i)a[bc]d', 'ABD', '0', ascii('ABD')),
            ('(?i)a[b-d]e', 'ABD', '', ascii(None)),
            ('(?i)a[b-d]e', 'ACE', '0', ascii('ACE')),

            ('(?i)a[b-d]', 'AAC', '0', ascii('AC')),
            ('(?i)a[-b]', 'A-', '0', ascii('A-')),
            ('(?i)a[b-]', 'A-', '0', ascii('A-')),
            ('(?i)a[b-a]', '-', '', regex.error, self.BAD_CHAR_RANGE),
            ('(?i)a[]b', '-', '', regex.error, self.BAD_SET),
            ('(?i)a[', '-', '', regex.error, self.BAD_SET),
            ('(?i)a]', 'A]', '0', ascii('A]')),
            ('(?i)a[]]b', 'A]B', '0', ascii('A]B')),
            ('(?i)a[^bc]d', 'AED', '0', ascii('AED')),
            ('(?i)a[^bc]d', 'ABD', '', ascii(None)),

            ('(?i)a[^-b]c', 'ADC', '0', ascii('ADC')),
            ('(?i)a[^-b]c', 'A-C', '', ascii(None)),
            ('(?i)a[^]b]c', 'A]C', '', ascii(None)),
            ('(?i)a[^]b]c', 'ADC', '0', ascii('ADC')),
            ('(?i)ab|cd', 'ABC', '0', ascii('AB')),
            ('(?i)ab|cd', 'ABCD', '0', ascii('AB')),
            ('(?i)()ef', 'DEF', '0,1', ascii(('EF', ''))),
            ('(?i)*a', '-', '', regex.error, self.NOTHING_TO_REPEAT),
            ('(?i)(*)b', '-', '', regex.error, self.NOTHING_TO_REPEAT),
            ('(?i)$b', 'B', '', ascii(None)),

            ('(?i)a\\', '-', '', regex.error, self.BAD_ESCAPE),
            ('(?i)a\\(b', 'A(B', '', ascii(('A(B',))),
            ('(?i)a\\(*b', 'AB', '0', ascii('AB')),
            ('(?i)a\\(*b', 'A((B', '0', ascii('A((B')),
            ('(?i)a\\\\b', 'A\\B', '0', ascii('A\\B')),
            ('(?i)abc)', '-', '', regex.error, self.TRAILING_CHARS),
            ('(?i)(abc', '-', '', regex.error, self.MISSING_RPAREN),
            ('(?i)((a))', 'ABC', '0,1,2', ascii(('A', 'A', 'A'))),
            ('(?i)(a)b(c)', 'ABC', '0,1,2', ascii(('ABC', 'A', 'C'))),
            ('(?i)a+b+c', 'AABBABC', '0', ascii('ABC')),

            ('(?i)a{1,}b{1,}c', 'AABBABC', '0', ascii('ABC')),
            ('(?i)a**', '-', '', regex.error, self.MULTIPLE_REPEAT),
            ('(?i)a.+?c', 'ABCABC', '0', ascii('ABC')),
            ('(?i)a.*?c', 'ABCABC', '0', ascii('ABC')),
            ('(?i)a.{0,5}?c', 'ABCABC', '0', ascii('ABC')),
            ('(?i)(a+|b)*', 'AB', '0,1', ascii(('AB', 'B'))),
            ('(?i)(a+|b){0,}', 'AB', '0,1', ascii(('AB', 'B'))),
            ('(?i)(a+|b)+', 'AB', '0,1', ascii(('AB', 'B'))),
            ('(?i)(a+|b){1,}', 'AB', '0,1', ascii(('AB', 'B'))),
            ('(?i)(a+|b)?', 'AB', '0,1', ascii(('A', 'A'))),

            ('(?i)(a+|b){0,1}', 'AB', '0,1', ascii(('A', 'A'))),
            ('(?i)(a+|b){0,1}?', 'AB', '0,1', ascii(('', None))),
            ('(?i))(', '-', '', regex.error, self.TRAILING_CHARS),
            ('(?i)[^ab]*', 'CDE', '0', ascii('CDE')),
            ('(?i)abc', '', '', ascii(None)),
            ('(?i)a*', '', '0', ascii('')),
            ('(?i)([abc])*d', 'ABBBCD', '0,1', ascii(('ABBBCD', 'C'))),
            ('(?i)([abc])*bcd', 'ABCD', '0,1', ascii(('ABCD', 'A'))),
            ('(?i)a|b|c|d|e', 'E', '0', ascii('E')),
            ('(?i)(a|b|c|d|e)f', 'EF', '0,1', ascii(('EF', 'E'))),

            ('(?i)abcd*efg', 'ABCDEFG', '0', ascii('ABCDEFG')),
            ('(?i)ab*', 'XABYABBBZ', '0', ascii('AB')),
            ('(?i)ab*', 'XAYABBBZ', '0', ascii('A')),
            ('(?i)(ab|cd)e', 'ABCDE', '0,1', ascii(('CDE', 'CD'))),
            ('(?i)[abhgefdc]ij', 'HIJ', '0', ascii('HIJ')),
            ('(?i)^(ab|cd)e', 'ABCDE', '', ascii(None)),
            ('(?i)(abc|)ef', 'ABCDEF', '0,1', ascii(('EF', ''))),
            ('(?i)(a|b)c*d', 'ABCD', '0,1', ascii(('BCD', 'B'))),
            ('(?i)(ab|ab*)bc', 'ABC', '0,1', ascii(('ABC', 'A'))),
            ('(?i)a([bc]*)c*', 'ABC', '0,1', ascii(('ABC', 'BC'))),

            ('(?i)a([bc]*)(c*d)', 'ABCD', '0,1,2', ascii(('ABCD', 'BC', 'D'))),
            ('(?i)a([bc]+)(c*d)', 'ABCD', '0,1,2', ascii(('ABCD', 'BC', 'D'))),
            ('(?i)a([bc]*)(c+d)', 'ABCD', '0,1,2', ascii(('ABCD', 'B', 'CD'))),
            ('(?i)a[bcd]*dcdcde', 'ADCDCDE', '0', ascii('ADCDCDE')),
            ('(?i)a[bcd]+dcdcde', 'ADCDCDE', '', ascii(None)),
            ('(?i)(ab|a)b*c', 'ABC', '0,1', ascii(('ABC', 'AB'))),
            ('(?i)((a)(b)c)(d)', 'ABCD', '1,2,3,4', ascii(('ABC', 'A', 'B',
              'D'))),
            ('(?i)[a-zA-Z_][a-zA-Z0-9_]*', 'ALPHA', '0', ascii('ALPHA')),
            ('(?i)^a(bc+|b[eh])g|.h$', 'ABH', '0,1', ascii(('BH', None))),
            ('(?i)(bc+d$|ef*g.|h?i(j|k))', 'EFFGZ', '0,1,2', ascii(('EFFGZ',
              'EFFGZ', None))),

            ('(?i)(bc+d$|ef*g.|h?i(j|k))', 'IJ', '0,1,2', ascii(('IJ', 'IJ',
              'J'))),
            ('(?i)(bc+d$|ef*g.|h?i(j|k))', 'EFFG', '', ascii(None)),
            ('(?i)(bc+d$|ef*g.|h?i(j|k))', 'BCDD', '', ascii(None)),
            ('(?i)(bc+d$|ef*g.|h?i(j|k))', 'REFFGZ', '0,1,2', ascii(('EFFGZ',
              'EFFGZ', None))),
            ('(?i)((((((((((a))))))))))', 'A', '10', ascii('A')),
            ('(?i)((((((((((a))))))))))\\10', 'AA', '0', ascii('AA')),
            #('(?i)((((((((((a))))))))))\\41', 'AA', '', ascii(None)),
            #('(?i)((((((((((a))))))))))\\41', 'A!', '0', ascii('A!')),
            ('(?i)(((((((((a)))))))))', 'A', '0', ascii('A')),
            ('(?i)(?:(?:(?:(?:(?:(?:(?:(?:(?:(a))))))))))', 'A', '1',
              ascii('A')),
            ('(?i)(?:(?:(?:(?:(?:(?:(?:(?:(?:(a|b|c))))))))))', 'C', '1',
              ascii('C')),
            ('(?i)multiple words of text', 'UH-UH', '', ascii(None)),

            ('(?i)multiple words', 'MULTIPLE WORDS, YEAH', '0',
             ascii('MULTIPLE WORDS')),
            ('(?i)(.*)c(.*)', 'ABCDE', '0,1,2', ascii(('ABCDE', 'AB', 'DE'))),
            ('(?i)\\((.*), (.*)\\)', '(A, B)', '2,1', ascii(('B', 'A'))),
            ('(?i)[k]', 'AB', '', ascii(None)),
        #    ('(?i)abcd', 'ABCD', SUCCEED, 'found+"-"+\\found+"-"+\\\\found', ascii(ABCD-$&-\\ABCD)),
        #    ('(?i)a(bc)d', 'ABCD', SUCCEED, 'g1+"-"+\\g1+"-"+\\\\g1', ascii(BC-$1-\\BC)),
            ('(?i)a[-]?c', 'AC', '0', ascii('AC')),
            ('(?i)(abc)\\1', 'ABCABC', '1', ascii('ABC')),
            ('(?i)([a-c]*)\\1', 'ABCABC', '1', ascii('ABC')),
            ('a(?!b).', 'abad', '0', ascii('ad')),
            ('a(?=d).', 'abad', '0', ascii('ad')),
            ('a(?=c|d).', 'abad', '0', ascii('ad')),

            ('a(?:b|c|d)(.)', 'ace', '1', ascii('e')),
            ('a(?:b|c|d)*(.)', 'ace', '1', ascii('e')),
            ('a(?:b|c|d)+?(.)', 'ace', '1', ascii('e')),
            ('a(?:b|(c|e){1,2}?|d)+?(.)', 'ace', '1,2', ascii(('c', 'e'))),

            # Lookbehind: split by : but not if it is escaped by -.
            ('(?<!-):(.*?)(?<!-):', 'a:bc-:de:f', '1', ascii('bc-:de')),
            # Escaping with \ as we know it.
            ('(?<!\\\\):(.*?)(?<!\\\\):', 'a:bc\\:de:f', '1', ascii('bc\\:de')),
            # Terminating with ' and escaping with ? as in edifact.
            ("(?<!\\?)'(.*?)(?<!\\?)'", "a'bc?'de'f", '1', ascii("bc?'de")),

            # Comments using the (?#...) syntax.

            ('w(?# comment', 'w', '', regex.error, self.MISSING_RPAREN),
            ('w(?# comment 1)xy(?# comment 2)z', 'wxyz', '0', ascii('wxyz')),

            # Check odd placement of embedded pattern modifiers.

            # Not an error under PCRE/PRE:
            # When the new behaviour is turned on positional inline flags affect
            # only what follows.
            ('w(?i)', 'W', '0', ascii(None)),
            ('w(?i)', 'w', '0', ascii('w')),
            ('(?i)w', 'W', '0', ascii('W')),

            # Comments using the x embedded pattern modifier.
            ("""(?x)w# comment 1
x y
# comment 2
z""", 'wxyz', '0', ascii('wxyz')),

            # Using the m embedded pattern modifier.
            ('^abc', """jkl
abc
xyz""", '', ascii(None)),
            ('(?m)^abc', """jkl
abc
xyz""", '0', ascii('abc')),

            ('(?m)abc$', """jkl
xyzabc
123""", '0', ascii('abc')),

            # Using the s embedded pattern modifier.
            ('a.b', 'a\nb', '', ascii(None)),
            ('(?s)a.b', 'a\nb', '0', ascii('a\nb')),

            # Test \w, etc. both inside and outside character classes.
            ('\\w+', '--ab_cd0123--', '0', ascii('ab_cd0123')),
            ('[\\w]+', '--ab_cd0123--', '0', ascii('ab_cd0123')),
            ('\\D+', '1234abc5678', '0', ascii('abc')),
            ('[\\D]+', '1234abc5678', '0', ascii('abc')),
            ('[\\da-fA-F]+', '123abc', '0', ascii('123abc')),
            # Not an error under PCRE/PRE:
            # ('[\\d-x]', '-', '', regex.error, self.BAD_CHAR_RANGE),
            (r'([\s]*)([\S]*)([\s]*)', ' testing!1972', '3,2,1', ascii(('',
              'testing!1972', ' '))),
            (r'(\s*)(\S*)(\s*)', ' testing!1972', '3,2,1', ascii(('',
              'testing!1972', ' '))),

            #
            # Post-1.5.2 additions.

            # xmllib problem.
            (r'(([a-z]+):)?([a-z]+)$', 'smil', '1,2,3', ascii((None, None,
              'smil'))),
            # Bug 110866: reference to undefined group.
            (r'((.)\1+)', '', '', regex.error, self.OPEN_GROUP),
            # Bug 111869: search (PRE/PCRE fails on this one, SRE doesn't).
            (r'.*d', 'abc\nabd', '0', ascii('abd')),
            # Bug 112468: various expected syntax errors.
            (r'(', '', '', regex.error, self.MISSING_RPAREN),
            (r'[\41]', '!', '0', ascii('!')),
            # Bug 114033: nothing to repeat.
            (r'(x?)?', 'x', '0', ascii('x')),
            # Bug 115040: rescan if flags are modified inside pattern.
            # Changed to positional flags in regex 2023.12.23.
            (r' (?x)foo ', 'foo', '0', ascii(None)),
            (r'(?x) foo ', 'foo', '0', ascii('foo')),
            (r'(?x)foo ', 'foo', '0', ascii('foo')),
            # Bug 115618: negative lookahead.
            (r'(?<!abc)(d.f)', 'abcdefdof', '0', ascii('dof')),
            # Bug 116251: character class bug.
            (r'[\w-]+', 'laser_beam', '0', ascii('laser_beam')),
            # Bug 123769+127259: non-greedy backtracking bug.
            (r'.*?\S *:', 'xx:', '0', ascii('xx:')),
            (r'a[ ]*?\ (\d+).*', 'a   10', '0', ascii('a   10')),
            (r'a[ ]*?\ (\d+).*', 'a    10', '0', ascii('a    10')),
            # Bug 127259: \Z shouldn't depend on multiline mode.
            (r'(?ms).*?x\s*\Z(.*)','xx\nx\n', '1', ascii('')),
            # Bug 128899: uppercase literals under the ignorecase flag.
            (r'(?i)M+', 'MMM', '0', ascii('MMM')),
            (r'(?i)m+', 'MMM', '0', ascii('MMM')),
            (r'(?i)[M]+', 'MMM', '0', ascii('MMM')),
            (r'(?i)[m]+', 'MMM', '0', ascii('MMM')),
            # Bug 130748: ^* should be an error (nothing to repeat).
            # In 'regex' we won't bother to complain about this.
            # (r'^*', '', '', regex.error, self.NOTHING_TO_REPEAT),
            # Bug 133283: minimizing repeat problem.
            (r'"(?:\\"|[^"])*?"', r'"\""', '0', ascii(r'"\""')),
            # Bug 477728: minimizing repeat problem.
            (r'^.*?$', 'one\ntwo\nthree\n', '', ascii(None)),
            # Bug 483789: minimizing repeat problem.
            (r'a[^>]*?b', 'a>b', '', ascii(None)),
            # Bug 490573: minimizing repeat problem.
            (r'^a*?$', 'foo', '', ascii(None)),
            # Bug 470582: nested groups problem.
            (r'^((a)c)?(ab)$', 'ab', '1,2,3', ascii((None, None, 'ab'))),
            # Another minimizing repeat problem (capturing groups in assertions).
            ('^([ab]*?)(?=(b)?)c', 'abc', '1,2', ascii(('ab', None))),
            ('^([ab]*?)(?!(b))c', 'abc', '1,2', ascii(('ab', None))),
            ('^([ab]*?)(?<!(a))c', 'abc', '1,2', ascii(('ab', None))),
            # Bug 410271: \b broken under locales.
            (r'\b.\b', 'a', '0', ascii('a')),
            (r'\b.\b', '\N{LATIN CAPITAL LETTER A WITH DIAERESIS}', '0',
              ascii('\xc4')),
            (r'\w', '\N{LATIN CAPITAL LETTER A WITH DIAERESIS}', '0',
              ascii('\xc4')),
        ]

        for t in tests:
            excval = None
            try:
                if len(t) == 4:
                    pattern, string, groups, expected = t
                else:
                    pattern, string, groups, expected, excval = t
            except ValueError:
                fields = ", ".join([ascii(f) for f in t[ : 3]] + ["..."])
                self.fail("Incorrect number of test fields: ({})".format(fields))
            else:
                group_list = []
                if groups:
                    for group in groups.split(","):
                        try:
                            group_list.append(int(group))
                        except ValueError:
                            group_list.append(group)

                if excval is not None:
                    with self.subTest(pattern=pattern, string=string):
                        self.assertRaisesRegex(expected, excval, regex.search,
                          pattern, string)
                else:
                    m = regex.search(pattern, string)
                    if m:
                        if group_list:
                            actual = ascii(m.group(*group_list))
                        else:
                            actual = ascii(m[:])
                    else:
                        actual = ascii(m)

                    self.assertEqual(actual, expected)

    def test_replacement(self):
        self.assertEqual(regex.sub(r"test\?", "result\\?\\.\a\n", "test?"),
          "result\\?\\.\a\n")

        self.assertEqual(regex.sub('(.)', r"\1\1", 'x'), 'xx')
        self.assertEqual(regex.sub('(.)', regex.escape(r"\1\1"), 'x'), r"\1\1")
        self.assertEqual(regex.sub('(.)', r"\\1\\1", 'x'), r"\1\1")
        self.assertEqual(regex.sub('(.)', lambda m: r"\1\1", 'x'), r"\1\1")

    def test_common_prefix(self):
        # Very long common prefix
        all = string.ascii_lowercase + string.digits + string.ascii_uppercase
        side = all * 4
        regexp = '(' + side + '|' + side + ')'
        self.assertEqual(repr(type(regex.compile(regexp))), self.PATTERN_CLASS)

    def test_captures(self):
        self.assertEqual(regex.search(r"(\w)+", "abc").captures(1), ['a', 'b',
          'c'])
        self.assertEqual(regex.search(r"(\w{3})+", "abcdef").captures(0, 1),
          (['abcdef'], ['abc', 'def']))
        self.assertEqual(regex.search(r"^(\d{1,3})(?:\.(\d{1,3})){3}$",
          "192.168.0.1").captures(1, 2), (['192', ], ['168', '0', '1']))
        self.assertEqual(regex.match(r"^([0-9A-F]{2}){4} ([a-z]\d){5}$",
          "3FB52A0C a2c4g3k9d3").captures(1, 2), (['3F', 'B5', '2A', '0C'],
          ['a2', 'c4', 'g3', 'k9', 'd3']))
        self.assertEqual(regex.match("([a-z]W)([a-z]X)+([a-z]Y)",
          "aWbXcXdXeXfY").captures(1, 2, 3), (['aW'], ['bX', 'cX', 'dX', 'eX'],
          ['fY']))

        self.assertEqual(regex.search(r".*?(?=(.)+)b", "ab").captures(1),
          ['b'])
        self.assertEqual(regex.search(r".*?(?>(.){0,2})d", "abcd").captures(1),
          ['b', 'c'])
        self.assertEqual(regex.search(r"(.)+", "a").captures(1), ['a'])

    def test_guards(self):
        m = regex.search(r"(X.*?Y\s*){3}(X\s*)+AB:",
          "XY\nX Y\nX  Y\nXY\nXX AB:")
        self.assertEqual(m.span(0, 1, 2), ((3, 21), (12, 15), (16, 18)))

        m = regex.search(r"(X.*?Y\s*){3,}(X\s*)+AB:",
          "XY\nX Y\nX  Y\nXY\nXX AB:")
        self.assertEqual(m.span(0, 1, 2), ((0, 21), (12, 15), (16, 18)))

        m = regex.search(r'\d{4}(\s*\w)?\W*((?!\d)\w){2}', "9999XX")
        self.assertEqual(m.span(0, 1, 2), ((0, 6), (-1, -1), (5, 6)))

        m = regex.search(r'A\s*?.*?(\n+.*?\s*?){0,2}\(X', 'A\n1\nS\n1 (X')
        self.assertEqual(m.span(0, 1), ((0, 10), (5, 8)))

        m = regex.search(r'Derde\s*:', 'aaaaaa:\nDerde:')
        self.assertEqual(m.span(), (8, 14))
        m = regex.search(r'Derde\s*:', 'aaaaa:\nDerde:')
        self.assertEqual(m.span(), (7, 13))

    def test_turkic(self):
        # Turkish has dotted and dotless I/i.
        pairs = "I=i;I=\u0131;i=\u0130"

        all_chars = set()
        matching = set()
        for pair in pairs.split(";"):
            ch1, ch2 = pair.split("=")
            all_chars.update((ch1, ch2))
            matching.add((ch1, ch1))
            matching.add((ch1, ch2))
            matching.add((ch2, ch1))
            matching.add((ch2, ch2))

        for ch1 in all_chars:
            for ch2 in all_chars:
                m = regex.match(r"(?i)\A" + ch1 + r"\Z", ch2)
                if m:
                    if (ch1, ch2) not in matching:
                        self.fail("{} matching {}".format(ascii(ch1),
                          ascii(ch2)))
                else:
                    if (ch1, ch2) in matching:
                        self.fail("{} not matching {}".format(ascii(ch1),
                          ascii(ch2)))

    def test_named_lists(self):
        options = ["one", "two", "three"]
        self.assertEqual(regex.match(r"333\L<bar>444", "333one444",
          bar=options).group(), "333one444")
        self.assertEqual(regex.match(r"(?i)333\L<bar>444", "333TWO444",
          bar=options).group(), "333TWO444")
        self.assertEqual(regex.match(r"333\L<bar>444", "333four444",
          bar=options), None)

        options = [b"one", b"two", b"three"]
        self.assertEqual(regex.match(br"333\L<bar>444", b"333one444",
          bar=options).group(), b"333one444")
        self.assertEqual(regex.match(br"(?i)333\L<bar>444", b"333TWO444",
          bar=options).group(), b"333TWO444")
        self.assertEqual(regex.match(br"333\L<bar>444", b"333four444",
          bar=options), None)

        self.assertEqual(repr(type(regex.compile(r"3\L<bar>4\L<bar>+5",
          bar=["one", "two", "three"]))), self.PATTERN_CLASS)

        self.assertEqual(regex.findall(r"^\L<options>", "solid QWERT",
          options=set(['good', 'brilliant', '+s\\ol[i}d'])), [])
        self.assertEqual(regex.findall(r"^\L<options>", "+solid QWERT",
          options=set(['good', 'brilliant', '+solid'])), ['+solid'])

        options = ["STRASSE"]
        self.assertEqual(regex.match(r"(?fi)\L<words>",
          "stra\N{LATIN SMALL LETTER SHARP S}e", words=options).span(), (0,
          6))

        options = ["STRASSE", "stress"]
        self.assertEqual(regex.match(r"(?fi)\L<words>",
          "stra\N{LATIN SMALL LETTER SHARP S}e", words=options).span(), (0,
          6))

        options = ["stra\N{LATIN SMALL LETTER SHARP S}e"]
        self.assertEqual(regex.match(r"(?fi)\L<words>", "STRASSE",
          words=options).span(), (0, 7))

        options = ["kit"]
        self.assertEqual(regex.search(r"(?i)\L<words>", "SKITS",
          words=options).span(), (1, 4))
        self.assertEqual(regex.search(r"(?i)\L<words>",
          "SK\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}TS",
          words=options).span(), (1, 4))

        self.assertEqual(regex.search(r"(?fi)\b(\w+) +\1\b",
          " stra\N{LATIN SMALL LETTER SHARP S}e STRASSE ").span(), (1, 15))
        self.assertEqual(regex.search(r"(?fi)\b(\w+) +\1\b",
          " STRASSE stra\N{LATIN SMALL LETTER SHARP S}e ").span(), (1, 15))

        self.assertEqual(regex.search(r"^\L<options>$", "", options=[]).span(),
          (0, 0))

    def test_fuzzy(self):
        # Some tests borrowed from TRE library tests.
        self.assertEqual(repr(type(regex.compile('(fou){s,e<=1}'))),
          self.PATTERN_CLASS)
        self.assertEqual(repr(type(regex.compile('(fuu){s}'))),
          self.PATTERN_CLASS)
        self.assertEqual(repr(type(regex.compile('(fuu){s,e}'))),
          self.PATTERN_CLASS)
        self.assertEqual(repr(type(regex.compile('(anaconda){1i+1d<1,s<=1}'))),
          self.PATTERN_CLASS)
        self.assertEqual(repr(type(regex.compile('(anaconda){1i+1d<1,s<=1,e<=10}'))),
          self.PATTERN_CLASS)
        self.assertEqual(repr(type(regex.compile('(anaconda){s<=1,e<=1,1i+1d<1}'))),
          self.PATTERN_CLASS)

        text = 'molasses anaconda foo bar baz smith anderson '
        self.assertEqual(regex.search('(znacnda){s<=1,e<=3,1i+1d<1}', text),
          None)
        self.assertEqual(regex.search('(znacnda){s<=1,e<=3,1i+1d<2}',
          text).span(0, 1), ((9, 17), (9, 17)))
        self.assertEqual(regex.search('(ananda){1i+1d<2}', text), None)
        self.assertEqual(regex.search(r"(?:\bznacnda){e<=2}", text)[0],
          "anaconda")
        self.assertEqual(regex.search(r"(?:\bnacnda){e<=2}", text)[0],
          "anaconda")

        text = 'anaconda foo bar baz smith anderson'
        self.assertEqual(regex.search('(fuu){i<=3,d<=3,e<=5}', text).span(0,
          1), ((0, 0), (0, 0)))
        self.assertEqual(regex.search('(?b)(fuu){i<=3,d<=3,e<=5}',
          text).span(0, 1), ((9, 10), (9, 10)))
        self.assertEqual(regex.search('(fuu){i<=2,d<=2,e<=5}', text).span(0,
          1), ((7, 10), (7, 10)))
        self.assertEqual(regex.search('(?e)(fuu){i<=2,d<=2,e<=5}',
          text).span(0, 1), ((9, 10), (9, 10)))
        self.assertEqual(regex.search('(fuu){i<=3,d<=3,e}', text).span(0, 1),
          ((0, 0), (0, 0)))
        self.assertEqual(regex.search('(?b)(fuu){i<=3,d<=3,e}', text).span(0,
          1), ((9, 10), (9, 10)))

        self.assertEqual(repr(type(regex.compile('(approximate){s<=3,1i+1d<3}'))),
          self.PATTERN_CLASS)

        # No cost limit.
        self.assertEqual(regex.search('(foobar){e}',
          'xirefoabralfobarxie').span(0, 1), ((0, 6), (0, 6)))
        self.assertEqual(regex.search('(?e)(foobar){e}',
          'xirefoabralfobarxie').span(0, 1), ((0, 3), (0, 3)))
        self.assertEqual(regex.search('(?b)(foobar){e}',
          'xirefoabralfobarxie').span(0, 1), ((11, 16), (11, 16)))

        # At most two errors.
        self.assertEqual(regex.search('(foobar){e<=2}',
          'xirefoabrzlfd').span(0, 1), ((4, 9), (4, 9)))
        self.assertEqual(regex.search('(foobar){e<=2}', 'xirefoabzlfd'), None)

        # At most two inserts or substitutions and max two errors total.
        self.assertEqual(regex.search('(foobar){i<=2,s<=2,e<=2}',
          'oobargoobaploowap').span(0, 1), ((5, 11), (5, 11)))

        # Find best whole word match for "foobar".
        self.assertEqual(regex.search('\\b(foobar){e}\\b', 'zfoobarz').span(0,
          1), ((0, 8), (0, 8)))
        self.assertEqual(regex.search('\\b(foobar){e}\\b',
          'boing zfoobarz goobar woop').span(0, 1), ((0, 6), (0, 6)))
        self.assertEqual(regex.search('(?b)\\b(foobar){e}\\b',
          'boing zfoobarz goobar woop').span(0, 1), ((15, 21), (15, 21)))

        # Match whole string, allow only 1 error.
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'foobar').span(0, 1),
          ((0, 6), (0, 6)))
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'xfoobar').span(0,
          1), ((0, 7), (0, 7)))
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'foobarx').span(0,
          1), ((0, 7), (0, 7)))
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'fooxbar').span(0,
          1), ((0, 7), (0, 7)))
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'foxbar').span(0, 1),
          ((0, 6), (0, 6)))
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'xoobar').span(0, 1),
          ((0, 6), (0, 6)))
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'foobax').span(0, 1),
          ((0, 6), (0, 6)))
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'oobar').span(0, 1),
          ((0, 5), (0, 5)))
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'fobar').span(0, 1),
          ((0, 5), (0, 5)))
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'fooba').span(0, 1),
          ((0, 5), (0, 5)))
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'xfoobarx'), None)
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'foobarxx'), None)
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'xxfoobar'), None)
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'xfoxbar'), None)
        self.assertEqual(regex.search('^(foobar){e<=1}$', 'foxbarx'), None)

        # At most one insert, two deletes, and three substitutions.
        # Additionally, deletes cost two and substitutes one, and total
        # cost must be less than 4.
        self.assertEqual(regex.search('(foobar){i<=1,d<=2,s<=3,2d+1s<4}',
          '3oifaowefbaoraofuiebofasebfaobfaorfeoaro').span(0, 1), ((6, 13), (6,
          13)))
        self.assertEqual(regex.search('(?b)(foobar){i<=1,d<=2,s<=3,2d+1s<4}',
          '3oifaowefbaoraofuiebofasebfaobfaorfeoaro').span(0, 1), ((34, 39),
          (34, 39)))

        # Partially fuzzy matches.
        self.assertEqual(regex.search('foo(bar){e<=1}zap', 'foobarzap').span(0,
          1), ((0, 9), (3, 6)))
        self.assertEqual(regex.search('foo(bar){e<=1}zap', 'fobarzap'), None)
        self.assertEqual(regex.search('foo(bar){e<=1}zap', 'foobrzap').span(0,
          1), ((0, 8), (3, 5)))

        text = ('www.cnn.com 64.236.16.20\nwww.slashdot.org 66.35.250.150\n'
          'For useful information, use www.slashdot.org\nthis is demo data!\n')
        self.assertEqual(regex.search(r'(?s)^.*(dot.org){e}.*$', text).span(0,
          1), ((0, 120), (120, 120)))
        self.assertEqual(regex.search(r'(?es)^.*(dot.org){e}.*$', text).span(0,
          1), ((0, 120), (93, 100)))
        self.assertEqual(regex.search(r'^.*(dot.org){e}.*$', text).span(0, 1),
          ((0, 119), (24, 101)))

        # Behaviour is unexpected, but arguably not wrong. It first finds the
        # best match, then the best in what follows, etc.
        self.assertEqual(regex.findall(r"\b\L<words>{e<=1}\b",
          " book cot dog desk ", words="cat dog".split()), ["cot", "dog"])
        self.assertEqual(regex.findall(r"\b\L<words>{e<=1}\b",
          " book dog cot desk ", words="cat dog".split()), [" dog", "cot"])
        self.assertEqual(regex.findall(r"(?e)\b\L<words>{e<=1}\b",
          " book dog cot desk ", words="cat dog".split()), ["dog", "cot"])
        self.assertEqual(regex.findall(r"(?r)\b\L<words>{e<=1}\b",
          " book cot dog desk ", words="cat dog".split()), ["dog ", "cot"])
        self.assertEqual(regex.findall(r"(?er)\b\L<words>{e<=1}\b",
          " book cot dog desk ", words="cat dog".split()), ["dog", "cot"])
        self.assertEqual(regex.findall(r"(?r)\b\L<words>{e<=1}\b",
          " book dog cot desk ", words="cat dog".split()), ["cot", "dog"])
        self.assertEqual(regex.findall(br"\b\L<words>{e<=1}\b",
          b" book cot dog desk ", words=b"cat dog".split()), [b"cot", b"dog"])
        self.assertEqual(regex.findall(br"\b\L<words>{e<=1}\b",
          b" book dog cot desk ", words=b"cat dog".split()), [b" dog", b"cot"])
        self.assertEqual(regex.findall(br"(?e)\b\L<words>{e<=1}\b",
          b" book dog cot desk ", words=b"cat dog".split()), [b"dog", b"cot"])
        self.assertEqual(regex.findall(br"(?r)\b\L<words>{e<=1}\b",
          b" book cot dog desk ", words=b"cat dog".split()), [b"dog ", b"cot"])
        self.assertEqual(regex.findall(br"(?er)\b\L<words>{e<=1}\b",
          b" book cot dog desk ", words=b"cat dog".split()), [b"dog", b"cot"])
        self.assertEqual(regex.findall(br"(?r)\b\L<words>{e<=1}\b",
          b" book dog cot desk ", words=b"cat dog".split()), [b"cot", b"dog"])

        self.assertEqual(regex.search(r"(\w+) (\1{e<=1})", "foo fou").groups(),
          ("foo", "fou"))
        self.assertEqual(regex.search(r"(?r)(\2{e<=1}) (\w+)",
          "foo fou").groups(), ("foo", "fou"))
        self.assertEqual(regex.search(br"(\w+) (\1{e<=1})",
          b"foo fou").groups(), (b"foo", b"fou"))

        self.assertEqual(regex.findall(r"(?:(?:QR)+){e}", "abcde"), ["abcde",
          ""])
        self.assertEqual(regex.findall(r"(?:Q+){e}", "abc"), ["abc", ""])

        # Hg issue 41: = for fuzzy matches
        self.assertEqual(regex.match(r"(?:service detection){0<e<5}",
          "servic detection").span(), (0, 16))
        self.assertEqual(regex.match(r"(?:service detection){0<e<5}",
          "service detect").span(), (0, 14))
        self.assertEqual(regex.match(r"(?:service detection){0<e<5}",
          "service detecti").span(), (0, 15))
        self.assertEqual(regex.match(r"(?:service detection){0<e<5}",
          "service detection"), None)
        self.assertEqual(regex.match(r"(?:service detection){0<e<5}",
          "in service detection").span(), (0, 20))

        # Hg issue 109: Edit distance of fuzzy match
        self.assertEqual(regex.fullmatch(r"(?:cats|cat){e<=1}",
          "cat").fuzzy_counts, (0, 0, 1))
        self.assertEqual(regex.fullmatch(r"(?e)(?:cats|cat){e<=1}",
          "cat").fuzzy_counts, (0, 0, 0))

        self.assertEqual(regex.fullmatch(r"(?:cat|cats){e<=1}",
          "cats").fuzzy_counts, (0, 1, 0))
        self.assertEqual(regex.fullmatch(r"(?e)(?:cat|cats){e<=1}",
          "cats").fuzzy_counts, (0, 0, 0))

        self.assertEqual(regex.fullmatch(r"(?:cat){e<=1} (?:cat){e<=1}",
          "cat cot").fuzzy_counts, (1, 0, 0))

        # Incorrect fuzzy changes
        self.assertEqual(regex.search(r"(?e)(GTTTTCATTCCTCATA){i<=4,d<=4,s<=4,i+d+s<=8}",
          "ATTATTTATTTTTCATA").fuzzy_changes, ([0, 6, 10, 11], [3], []))

        # Fuzzy constraints ignored when checking for prefix/suffix in branches
        self.assertEqual(bool(regex.match('(?:fo){e<=1}|(?:fo){e<=2}', 'FO')),
          True)

    def test_recursive(self):
        self.assertEqual(regex.search(r"(\w)(?:(?R)|(\w?))\1", "xx")[ : ],
          ("xx", "x", ""))
        self.assertEqual(regex.search(r"(\w)(?:(?R)|(\w?))\1", "aba")[ : ],
          ("aba", "a", "b"))
        self.assertEqual(regex.search(r"(\w)(?:(?R)|(\w?))\1", "abba")[ : ],
          ("abba", "a", None))
        self.assertEqual(regex.search(r"(\w)(?:(?R)|(\w?))\1", "kayak")[ : ],
          ("kayak", "k", None))
        self.assertEqual(regex.search(r"(\w)(?:(?R)|(\w?))\1", "paper")[ : ],
          ("pap", "p", "a"))
        self.assertEqual(regex.search(r"(\w)(?:(?R)|(\w?))\1", "dontmatchme"),
          None)

        self.assertEqual(regex.search(r"(?r)\2(?:(\w?)|(?R))(\w)", "xx")[ : ],
          ("xx", "", "x"))
        self.assertEqual(regex.search(r"(?r)\2(?:(\w?)|(?R))(\w)", "aba")[ : ],
          ("aba", "b", "a"))
        self.assertEqual(regex.search(r"(?r)\2(?:(\w?)|(?R))(\w)", "abba")[ :
          ], ("abba", None, "a"))
        self.assertEqual(regex.search(r"(?r)\2(?:(\w?)|(?R))(\w)", "kayak")[ :
          ], ("kayak", None, "k"))
        self.assertEqual(regex.search(r"(?r)\2(?:(\w?)|(?R))(\w)", "paper")[ :
          ], ("pap", "a", "p"))
        self.assertEqual(regex.search(r"(?r)\2(?:(\w?)|(?R))(\w)",
          "dontmatchme"), None)

        self.assertEqual(regex.search(r"\(((?>[^()]+)|(?R))*\)", "(ab(cd)ef)")[
          : ], ("(ab(cd)ef)", "ef"))
        self.assertEqual(regex.search(r"\(((?>[^()]+)|(?R))*\)",
          "(ab(cd)ef)").captures(1), ["ab", "cd", "(cd)", "ef"])

        self.assertEqual(regex.search(r"(?r)\(((?R)|(?>[^()]+))*\)",
          "(ab(cd)ef)")[ : ], ("(ab(cd)ef)", "ab"))
        self.assertEqual(regex.search(r"(?r)\(((?R)|(?>[^()]+))*\)",
          "(ab(cd)ef)").captures(1), ["ef", "cd", "(cd)", "ab"])

        self.assertEqual(regex.search(r"\(([^()]+|(?R))*\)",
          "some text (a(b(c)d)e) more text")[ : ], ("(a(b(c)d)e)", "e"))

        self.assertEqual(regex.search(r"(?r)\(((?R)|[^()]+)*\)",
          "some text (a(b(c)d)e) more text")[ : ], ("(a(b(c)d)e)", "a"))

        self.assertEqual(regex.search(r"(foo(\(((?:(?>[^()]+)|(?2))*)\)))",
          "foo(bar(baz)+baz(bop))")[ : ], ("foo(bar(baz)+baz(bop))",
          "foo(bar(baz)+baz(bop))", "(bar(baz)+baz(bop))",
          "bar(baz)+baz(bop)"))

        self.assertEqual(regex.search(r"(?r)(foo(\(((?:(?2)|(?>[^()]+))*)\)))",
          "foo(bar(baz)+baz(bop))")[ : ], ("foo(bar(baz)+baz(bop))",
          "foo(bar(baz)+baz(bop))", "(bar(baz)+baz(bop))",
          "bar(baz)+baz(bop)"))

        rgx = regex.compile(r"""^\s*(<\s*([a-zA-Z:]+)(?:\s*[a-zA-Z:]*\s*=\s*(?:'[^']*'|"[^"]*"))*\s*(/\s*)?>(?:[^<>]*|(?1))*(?(3)|<\s*/\s*\2\s*>))\s*$""")
        self.assertEqual(bool(rgx.search('<foo><bar></bar></foo>')), True)
        self.assertEqual(bool(rgx.search('<foo><bar></foo></bar>')), False)
        self.assertEqual(bool(rgx.search('<foo><bar/></foo>')), True)
        self.assertEqual(bool(rgx.search('<foo><bar></foo>')), False)
        self.assertEqual(bool(rgx.search('<foo bar=baz/>')), False)

        self.assertEqual(bool(rgx.search('<foo bar="baz">')), False)
        self.assertEqual(bool(rgx.search('<foo bar="baz"/>')), True)
        self.assertEqual(bool(rgx.search('<    fooo   /  >')), True)
        # The next regex should and does match. Perl 5.14 agrees.
        #self.assertEqual(bool(rgx.search('<foo/>foo')), False)
        self.assertEqual(bool(rgx.search('foo<foo/>')), False)

        self.assertEqual(bool(rgx.search('<foo>foo</foo>')), True)
        self.assertEqual(bool(rgx.search('<foo><bar/>foo</foo>')), True)
        self.assertEqual(bool(rgx.search('<a><b><c></c></b></a>')), True)

    def test_copy(self):
        # PatternObjects are immutable, therefore there's no need to clone them.
        r = regex.compile("a")
        self.assertTrue(copy.copy(r) is r)
        self.assertTrue(copy.deepcopy(r) is r)

        # MatchObjects are normally mutable because the target string can be
        # detached. However, after the target string has been detached, a
        # MatchObject becomes immutable, so there's no need to clone it.
        m = r.match("a")
        self.assertTrue(copy.copy(m) is not m)
        self.assertTrue(copy.deepcopy(m) is not m)

        self.assertTrue(m.string is not None)
        m2 = copy.copy(m)
        m2.detach_string()
        self.assertTrue(m.string is not None)
        self.assertTrue(m2.string is None)

        # The following behaviour matches that of the re module.
        it = regex.finditer(".", "ab")
        it2 = copy.copy(it)
        self.assertEqual(next(it).group(), "a")
        self.assertEqual(next(it2).group(), "b")

        # The following behaviour matches that of the re module.
        it = regex.finditer(".", "ab")
        it2 = copy.deepcopy(it)
        self.assertEqual(next(it).group(), "a")
        self.assertEqual(next(it2).group(), "b")

        # The following behaviour is designed to match that of copying 'finditer'.
        it = regex.splititer(" ", "a b")
        it2 = copy.copy(it)
        self.assertEqual(next(it), "a")
        self.assertEqual(next(it2), "b")

        # The following behaviour is designed to match that of copying 'finditer'.
        it = regex.splititer(" ", "a b")
        it2 = copy.deepcopy(it)
        self.assertEqual(next(it), "a")
        self.assertEqual(next(it2), "b")

    def test_format(self):
        self.assertEqual(regex.subf(r"(\w+) (\w+)", "{0} => {2} {1}",
          "foo bar"), "foo bar => bar foo")
        self.assertEqual(regex.subf(r"(?<word1>\w+) (?<word2>\w+)",
          "{word2} {word1}", "foo bar"), "bar foo")

        self.assertEqual(regex.subfn(r"(\w+) (\w+)", "{0} => {2} {1}",
          "foo bar"), ("foo bar => bar foo", 1))
        self.assertEqual(regex.subfn(r"(?<word1>\w+) (?<word2>\w+)",
          "{word2} {word1}", "foo bar"), ("bar foo", 1))

        self.assertEqual(regex.match(r"(\w+) (\w+)",
          "foo bar").expandf("{0} => {2} {1}"), "foo bar => bar foo")

    def test_fullmatch(self):
        self.assertEqual(bool(regex.fullmatch(r"abc", "abc")), True)
        self.assertEqual(bool(regex.fullmatch(r"abc", "abcx")), False)
        self.assertEqual(bool(regex.fullmatch(r"abc", "abcx", endpos=3)), True)

        self.assertEqual(bool(regex.fullmatch(r"abc", "xabc", pos=1)), True)
        self.assertEqual(bool(regex.fullmatch(r"abc", "xabcy", pos=1)), False)
        self.assertEqual(bool(regex.fullmatch(r"abc", "xabcy", pos=1,
          endpos=4)), True)

        self.assertEqual(bool(regex.fullmatch(r"(?r)abc", "abc")), True)
        self.assertEqual(bool(regex.fullmatch(r"(?r)abc", "abcx")), False)
        self.assertEqual(bool(regex.fullmatch(r"(?r)abc", "abcx", endpos=3)),
          True)

        self.assertEqual(bool(regex.fullmatch(r"(?r)abc", "xabc", pos=1)),
          True)
        self.assertEqual(bool(regex.fullmatch(r"(?r)abc", "xabcy", pos=1)),
          False)
        self.assertEqual(bool(regex.fullmatch(r"(?r)abc", "xabcy", pos=1,
          endpos=4)), True)

    def test_issue_18468(self):
        self.assertTypedEqual(regex.sub('y', 'a', 'xyz'), 'xaz')
        self.assertTypedEqual(regex.sub('y', StrSubclass('a'),
          StrSubclass('xyz')), 'xaz')
        self.assertTypedEqual(regex.sub(b'y', b'a', b'xyz'), b'xaz')
        self.assertTypedEqual(regex.sub(b'y', BytesSubclass(b'a'),
          BytesSubclass(b'xyz')), b'xaz')
        self.assertTypedEqual(regex.sub(b'y', bytearray(b'a'),
          bytearray(b'xyz')), b'xaz')
        self.assertTypedEqual(regex.sub(b'y', memoryview(b'a'),
          memoryview(b'xyz')), b'xaz')

        for string in ":a:b::c", StrSubclass(":a:b::c"):
            self.assertTypedEqual(regex.split(":", string), ['', 'a', 'b', '',
              'c'])
            if sys.version_info >= (3, 7, 0):
                self.assertTypedEqual(regex.split(":*", string), ['', '', 'a',
                  '', 'b', '', 'c', ''])
                self.assertTypedEqual(regex.split("(:*)", string), ['', ':',
                  '', '', 'a', ':', '', '', 'b', '::', '', '', 'c', '', ''])
            else:
                self.assertTypedEqual(regex.split(":*", string), ['', 'a', 'b',
                  'c'])
                self.assertTypedEqual(regex.split("(:*)", string), ['', ':',
                  'a', ':', 'b', '::', 'c'])

        for string in (b":a:b::c", BytesSubclass(b":a:b::c"),
          bytearray(b":a:b::c"), memoryview(b":a:b::c")):
            self.assertTypedEqual(regex.split(b":", string), [b'', b'a', b'b',
              b'', b'c'])
            if sys.version_info >= (3, 7, 0):
                self.assertTypedEqual(regex.split(b":*", string), [b'', b'',
                  b'a', b'', b'b', b'', b'c', b''])
                self.assertTypedEqual(regex.split(b"(:*)", string), [b'', b':',
                  b'', b'', b'a', b':', b'', b'', b'b', b'::', b'', b'', b'c',
                  b'', b''])
            else:
                self.assertTypedEqual(regex.split(b":*", string), [b'', b'a',
                  b'b', b'c'])
                self.assertTypedEqual(regex.split(b"(:*)", string), [b'', b':',
                  b'a', b':', b'b', b'::', b'c'])

        for string in "a:b::c:::d", StrSubclass("a:b::c:::d"):
            self.assertTypedEqual(regex.findall(":+", string), [":", "::",
              ":::"])
            self.assertTypedEqual(regex.findall("(:+)", string), [":", "::",
              ":::"])
            self.assertTypedEqual(regex.findall("(:)(:*)", string), [(":", ""),
              (":", ":"), (":", "::")])

        for string in (b"a:b::c:::d", BytesSubclass(b"a:b::c:::d"),
          bytearray(b"a:b::c:::d"), memoryview(b"a:b::c:::d")):
            self.assertTypedEqual(regex.findall(b":+", string), [b":", b"::",
              b":::"])
            self.assertTypedEqual(regex.findall(b"(:+)", string), [b":", b"::",
              b":::"])
            self.assertTypedEqual(regex.findall(b"(:)(:*)", string), [(b":",
              b""), (b":", b":"), (b":", b"::")])

        for string in 'a', StrSubclass('a'):
            self.assertEqual(regex.match('a', string).groups(), ())
            self.assertEqual(regex.match('(a)', string).groups(), ('a',))
            self.assertEqual(regex.match('(a)', string).group(0), 'a')
            self.assertEqual(regex.match('(a)', string).group(1), 'a')
            self.assertEqual(regex.match('(a)', string).group(1, 1), ('a',
              'a'))

        for string in (b'a', BytesSubclass(b'a'), bytearray(b'a'),
          memoryview(b'a')):
            self.assertEqual(regex.match(b'a', string).groups(), ())
            self.assertEqual(regex.match(b'(a)', string).groups(), (b'a',))
            self.assertEqual(regex.match(b'(a)', string).group(0), b'a')
            self.assertEqual(regex.match(b'(a)', string).group(1), b'a')
            self.assertEqual(regex.match(b'(a)', string).group(1, 1), (b'a',
              b'a'))

    def test_partial(self):
        self.assertEqual(regex.match('ab', 'a', partial=True).partial, True)
        self.assertEqual(regex.match('ab', 'a', partial=True).span(), (0, 1))
        self.assertEqual(regex.match(r'cats', 'cat', partial=True).partial,
          True)
        self.assertEqual(regex.match(r'cats', 'cat', partial=True).span(), (0,
          3))
        self.assertEqual(regex.match(r'cats', 'catch', partial=True), None)
        self.assertEqual(regex.match(r'abc\w{3}', 'abcdef',
          partial=True).partial, False)
        self.assertEqual(regex.match(r'abc\w{3}', 'abcdef',
          partial=True).span(), (0, 6))
        self.assertEqual(regex.match(r'abc\w{3}', 'abcde',
          partial=True).partial, True)
        self.assertEqual(regex.match(r'abc\w{3}', 'abcde',
          partial=True).span(), (0, 5))

        self.assertEqual(regex.match(r'\d{4}$', '1234', partial=True).partial,
          False)

        self.assertEqual(regex.match(r'\L<words>', 'post', partial=True,
          words=['post']).partial, False)
        self.assertEqual(regex.match(r'\L<words>', 'post', partial=True,
          words=['post']).span(), (0, 4))
        self.assertEqual(regex.match(r'\L<words>', 'pos', partial=True,
          words=['post']).partial, True)
        self.assertEqual(regex.match(r'\L<words>', 'pos', partial=True,
          words=['post']).span(), (0, 3))

        self.assertEqual(regex.match(r'(?fi)\L<words>', 'POST', partial=True,
          words=['po\uFB06']).partial, False)
        self.assertEqual(regex.match(r'(?fi)\L<words>', 'POST', partial=True,
          words=['po\uFB06']).span(), (0, 4))
        self.assertEqual(regex.match(r'(?fi)\L<words>', 'POS', partial=True,
          words=['po\uFB06']).partial, True)
        self.assertEqual(regex.match(r'(?fi)\L<words>', 'POS', partial=True,
          words=['po\uFB06']).span(), (0, 3))
        self.assertEqual(regex.match(r'(?fi)\L<words>', 'po\uFB06',
          partial=True, words=['POS']), None)

        self.assertEqual(regex.match(r'[a-z]*4R$', 'a', partial=True).span(),
          (0, 1))
        self.assertEqual(regex.match(r'[a-z]*4R$', 'ab', partial=True).span(),
          (0, 2))
        self.assertEqual(regex.match(r'[a-z]*4R$', 'ab4', partial=True).span(),
          (0, 3))
        self.assertEqual(regex.match(r'[a-z]*4R$', 'a4', partial=True).span(),
          (0, 2))
        self.assertEqual(regex.match(r'[a-z]*4R$', 'a4R', partial=True).span(),
          (0, 3))
        self.assertEqual(regex.match(r'[a-z]*4R$', '4a', partial=True), None)
        self.assertEqual(regex.match(r'[a-z]*4R$', 'a44', partial=True), None)

    def test_hg_bugs(self):
        # Hg issue 28: regex.compile("(?>b)") causes "TypeError: 'Character'
        # object is not subscriptable"
        self.assertEqual(bool(regex.compile("(?>b)", flags=regex.V1)), True)

        # Hg issue 29: regex.compile("^((?>\w+)|(?>\s+))*$") causes
        # "TypeError: 'GreedyRepeat' object is not iterable"
        self.assertEqual(bool(regex.compile(r"^((?>\w+)|(?>\s+))*$",
          flags=regex.V1)), True)

        # Hg issue 31: atomic and normal groups in recursive patterns
        self.assertEqual(regex.findall(r"\((?:(?>[^()]+)|(?R))*\)",
          "a(bcd(e)f)g(h)"), ['(bcd(e)f)', '(h)'])
        self.assertEqual(regex.findall(r"\((?:(?:[^()]+)|(?R))*\)",
          "a(bcd(e)f)g(h)"), ['(bcd(e)f)', '(h)'])
        self.assertEqual(regex.findall(r"\((?:(?>[^()]+)|(?R))*\)",
          "a(b(cd)e)f)g)h"), ['(b(cd)e)'])
        self.assertEqual(regex.findall(r"\((?:(?>[^()]+)|(?R))*\)",
          "a(bc(d(e)f)gh"), ['(d(e)f)'])
        self.assertEqual(regex.findall(r"(?r)\((?:(?>[^()]+)|(?R))*\)",
          "a(bc(d(e)f)gh"), ['(d(e)f)'])
        self.assertEqual([m.group() for m in
          regex.finditer(r"\((?:[^()]*+|(?0))*\)", "a(b(c(de)fg)h")],
          ['(c(de)fg)'])

        # Hg issue 32: regex.search("a(bc)d", "abcd", regex.I|regex.V1) returns
        # None
        self.assertEqual(regex.search("a(bc)d", "abcd", regex.I |
          regex.V1).group(0), "abcd")

        # Hg issue 33: regex.search("([\da-f:]+)$", "E", regex.I|regex.V1)
        # returns None
        self.assertEqual(regex.search(r"([\da-f:]+)$", "E", regex.I |
          regex.V1).group(0), "E")
        self.assertEqual(regex.search(r"([\da-f:]+)$", "e", regex.I |
          regex.V1).group(0), "e")

        # Hg issue 34: regex.search("^(?=ab(de))(abd)(e)", "abde").groups()
        # returns (None, 'abd', 'e') instead of ('de', 'abd', 'e')
        self.assertEqual(regex.search("^(?=ab(de))(abd)(e)", "abde").groups(),
          ('de', 'abd', 'e'))

        # Hg issue 35: regex.compile("\ ", regex.X) causes "_regex_core.error:
        # bad escape"
        self.assertEqual(bool(regex.match(r"\ ", " ", flags=regex.X)), True)

        # Hg issue 36: regex.search("^(a|)\1{2}b", "b") returns None
        self.assertEqual(regex.search(r"^(a|)\1{2}b", "b").group(0, 1), ('b',
          ''))

        # Hg issue 37: regex.search("^(a){0,0}", "abc").group(0,1) returns
        # ('a', 'a') instead of ('', None)
        self.assertEqual(regex.search("^(a){0,0}", "abc").group(0, 1), ('',
          None))

        # Hg issue 38: regex.search("(?>.*/)b", "a/b") returns None
        self.assertEqual(regex.search("(?>.*/)b", "a/b").group(0), "a/b")

        # Hg issue 39: regex.search("((?i)blah)\\s+\\1", "blah BLAH") doesn't
        # return None
        # Changed to positional flags in regex 2023.12.23.
        self.assertEqual(regex.search(r"((?i)blah)\s+\1", "blah BLAH"), None)

        # Hg issue 40: regex.search("(\()?[^()]+(?(1)\)|)", "(abcd").group(0)
        # returns "bcd" instead of "abcd"
        self.assertEqual(regex.search(r"(\()?[^()]+(?(1)\)|)",
          "(abcd").group(0), "abcd")

        # Hg issue 42: regex.search("(a*)*", "a", flags=regex.V1).span(1)
        # returns (0, 1) instead of (1, 1)
        self.assertEqual(regex.search("(a*)*", "a").span(1), (1, 1))
        self.assertEqual(regex.search("(a*)*", "aa").span(1), (2, 2))
        self.assertEqual(regex.search("(a*)*", "aaa").span(1), (3, 3))

        # Hg issue 43: regex.compile("a(?#xxx)*") causes "_regex_core.error:
        # nothing to repeat"
        self.assertEqual(regex.search("a(?#xxx)*", "aaa").group(), "aaa")

        # Hg issue 44: regex.compile("(?=abc){3}abc") causes
        # "_regex_core.error: nothing to repeat"
        self.assertEqual(regex.search("(?=abc){3}abc", "abcabcabc").span(), (0,
          3))

        # Hg issue 45: regex.compile("^(?:a(?:(?:))+)+") causes
        # "_regex_core.error: nothing to repeat"
        self.assertEqual(regex.search("^(?:a(?:(?:))+)+", "a").span(), (0, 1))
        self.assertEqual(regex.search("^(?:a(?:(?:))+)+", "aa").span(), (0, 2))

        # Hg issue 46: regex.compile("a(?x: b c )d") causes
        # "_regex_core.error: missing )"
        self.assertEqual(regex.search("a(?x: b c )d", "abcd").group(0), "abcd")

        # Hg issue 47: regex.compile("a#comment\n*", flags=regex.X) causes
        # "_regex_core.error: nothing to repeat"
        self.assertEqual(regex.search("a#comment\n*", "aaa",
          flags=regex.X).group(0), "aaa")

        # Hg issue 48: regex.search("(a(?(1)\\1)){4}", "a"*10,
        # flags=regex.V1).group(0,1) returns ('aaaaa', 'a') instead of ('aaaaaaaaaa', 'aaaa')
        self.assertEqual(regex.search(r"(?V1)(a(?(1)\1)){1}",
          "aaaaaaaaaa").span(0, 1), ((0, 1), (0, 1)))
        self.assertEqual(regex.search(r"(?V1)(a(?(1)\1)){2}",
          "aaaaaaaaaa").span(0, 1), ((0, 3), (1, 3)))
        self.assertEqual(regex.search(r"(?V1)(a(?(1)\1)){3}",
          "aaaaaaaaaa").span(0, 1), ((0, 6), (3, 6)))
        self.assertEqual(regex.search(r"(?V1)(a(?(1)\1)){4}",
          "aaaaaaaaaa").span(0, 1), ((0, 10), (6, 10)))

        # Hg issue 49: regex.search("(a)(?<=b(?1))", "baz", regex.V1) returns
        # None incorrectly
        self.assertEqual(regex.search("(?V1)(a)(?<=b(?1))", "baz").group(0),
          "a")

        # Hg issue 50: not all keywords are found by named list with
        # overlapping keywords when full Unicode casefolding is required
        self.assertEqual(regex.findall(r'(?fi)\L<keywords>',
          'POST, Post, post, po\u017Ft, po\uFB06, and po\uFB05',
          keywords=['post','pos']), ['POST', 'Post', 'post', 'po\u017Ft',
          'po\uFB06', 'po\uFB05'])
        self.assertEqual(regex.findall(r'(?fi)pos|post',
          'POST, Post, post, po\u017Ft, po\uFB06, and po\uFB05'), ['POS',
          'Pos', 'pos', 'po\u017F', 'po\uFB06', 'po\uFB05'])
        self.assertEqual(regex.findall(r'(?fi)post|pos',
          'POST, Post, post, po\u017Ft, po\uFB06, and po\uFB05'), ['POST',
          'Post', 'post', 'po\u017Ft', 'po\uFB06', 'po\uFB05'])
        self.assertEqual(regex.findall(r'(?fi)post|another',
          'POST, Post, post, po\u017Ft, po\uFB06, and po\uFB05'), ['POST',
          'Post', 'post', 'po\u017Ft', 'po\uFB06', 'po\uFB05'])

        # Hg issue 51: regex.search("((a)(?1)|(?2))", "a", flags=regex.V1)
        # returns None incorrectly
        self.assertEqual(regex.search("(?V1)((a)(?1)|(?2))", "a").group(0, 1,
          2), ('a', 'a', None))

        # Hg issue 52: regex.search("(\\1xx|){6}", "xx",
        # flags=regex.V1).span(0,1) returns incorrect value
        self.assertEqual(regex.search(r"(?V1)(\1xx|){6}", "xx").span(0, 1),
          ((0, 2), (2, 2)))

        # Hg issue 53: regex.search("(a|)+", "a") causes MemoryError
        self.assertEqual(regex.search("(a|)+", "a").group(0, 1), ("a", ""))

        # Hg issue 54: regex.search("(a|)*\\d", "a"*80) causes MemoryError
        self.assertEqual(regex.search(r"(a|)*\d", "a" * 80), None)

        # Hg issue 55: regex.search("^(?:a?b?)*$", "ac") take a very long time.
        self.assertEqual(regex.search("^(?:a?b?)*$", "ac"), None)

        # Hg issue 58: bad named character escape sequences like "\\N{1}"
        # treats as "N"
        self.assertRaisesRegex(regex.error, self.UNDEF_CHAR_NAME, lambda:
          regex.compile("\\N{1}"))

        # Hg issue 59: regex.search("\\Z", "a\na\n") returns None incorrectly
        self.assertEqual(regex.search("\\Z", "a\na\n").span(0), (4, 4))

        # Hg issue 60: regex.search("(q1|.)*(q2|.)*(x(a|bc)*y){2,}", "xayxay")
        # returns None incorrectly
        self.assertEqual(regex.search("(q1|.)*(q2|.)*(x(a|bc)*y){2,}",
          "xayxay").group(0), "xayxay")

        # Hg issue 61: regex.search("[^a]", "A", regex.I).group(0) returns ''
        # incorrectly
        self.assertEqual(regex.search("(?i)[^a]", "A"), None)

        # Hg issue 63: regex.search("[[:ascii:]]", "\N{KELVIN SIGN}",
        # flags=regex.I|regex.V1) doesn't return None
        self.assertEqual(regex.search("(?i)[[:ascii:]]", "\N{KELVIN SIGN}"),
          None)

        # Hg issue 66: regex.search("((a|b(?1)c){3,5})", "baaaaca",
        # flags=regex.V1).groups() returns ('baaaac', 'baaaac') instead of ('aaaa', 'a')
        self.assertEqual(regex.search("((a|b(?1)c){3,5})", "baaaaca").group(0,
          1, 2), ('aaaa', 'aaaa', 'a'))

        # Hg issue 71: non-greedy quantifier in lookbehind
        self.assertEqual(regex.findall(r"(?<=:\S+ )\w+", ":9 abc :10 def"),
          ['abc', 'def'])
        self.assertEqual(regex.findall(r"(?<=:\S* )\w+", ":9 abc :10 def"),
          ['abc', 'def'])
        self.assertEqual(regex.findall(r"(?<=:\S+? )\w+", ":9 abc :10 def"),
          ['abc', 'def'])
        self.assertEqual(regex.findall(r"(?<=:\S*? )\w+", ":9 abc :10 def"),
          ['abc', 'def'])

        # Hg issue 73: conditional patterns
        self.assertEqual(regex.search(r"(?:fe)?male", "female").group(),
          "female")
        self.assertEqual([m.group() for m in
          regex.finditer(r"(fe)?male: h(?(1)(er)|(is)) (\w+)",
          "female: her dog; male: his cat. asdsasda")], ['female: her dog',
          'male: his cat'])

        # Hg issue 78: "Captures" doesn't work for recursive calls
        self.assertEqual(regex.search(r'(?<rec>\((?:[^()]++|(?&rec))*\))',
          'aaa(((1+0)+1)+1)bbb').captures('rec'), ['(1+0)', '((1+0)+1)',
          '(((1+0)+1)+1)'])

        # Hg issue 80: Escape characters throws an exception
        self.assertRaisesRegex(regex.error, self.BAD_ESCAPE, lambda:
          regex.sub('x', '\\', 'x'), )

        # Hg issue 82: error range does not work
        fz = "(CAGCCTCCCATTTCAGAATATACATCC){1<e<=2}"
        seq = "tcagacgagtgcgttgtaaaacgacggccagtCAGCCTCCCATTCAGAATATACATCCcgacggccagttaaaaacaatgccaaggaggtcatagctgtttcctgccagttaaaaacaatgccaaggaggtcatagctgtttcctgacgcactcgtctgagcgggctggcaagg"
        self.assertEqual(regex.search(fz, seq, regex.BESTMATCH)[0],
          "tCAGCCTCCCATTCAGAATATACATCC")

        # Hg issue 83: slash handling in presence of a quantifier
        self.assertEqual(regex.findall(r"c..+/c", "cA/c\ncAb/c"), ['cAb/c'])

        # Hg issue 85: Non-conformance to Unicode UAX#29 re: ZWJ / ZWNJ
        self.assertEqual(ascii(regex.sub(r"(\w+)", r"[\1]",
          '\u0905\u0928\u094d\u200d\u0928 \u0d28\u0d4d\u200d \u0915\u093f\u0928',
          regex.WORD)),
          ascii('[\u0905\u0928\u094d\u200d\u0928] [\u0d28\u0d4d\u200d] [\u0915\u093f\u0928]'))

        # Hg issue 88: regex.match() hangs
        self.assertEqual(regex.match(r".*a.*ba.*aa", "ababba"), None)

        # Hg issue 87: Allow duplicate names of groups
        self.assertEqual(regex.match(r'(?<x>a(?<x>b))', "ab").spans("x"), [(1,
          2), (0, 2)])

        # Hg issue 91: match.expand is extremely slow
        # Check that the replacement cache works.
        self.assertEqual(regex.sub(r'(-)', lambda m: m.expand(r'x'), 'a-b-c'),
          'axbxc')

        # Hg issue 94: Python crashes when executing regex updates
        # pattern.findall
        rx = regex.compile(r'\bt(est){i<2}', flags=regex.V1)
        self.assertEqual(rx.search("Some text"), None)
        self.assertEqual(rx.findall("Some text"), [])

        # Hg issue 95: 'pos' for regex.error
        self.assertRaisesRegex(regex.error, self.MULTIPLE_REPEAT, lambda:
          regex.compile(r'.???'))

        # Hg issue 97: behaviour of regex.escape's special_only is wrong
        #
        # Hg issue 244: Make `special_only=True` the default in
        # `regex.escape()`
        self.assertEqual(regex.escape('foo!?', special_only=False), 'foo\\!\\?')
        self.assertEqual(regex.escape('foo!?', special_only=True), 'foo!\\?')
        self.assertEqual(regex.escape('foo!?'), 'foo!\\?')

        self.assertEqual(regex.escape(b'foo!?', special_only=False), b'foo\\!\\?')
        self.assertEqual(regex.escape(b'foo!?', special_only=True),
          b'foo!\\?')
        self.assertEqual(regex.escape(b'foo!?'), b'foo!\\?')

        # Hg issue 100: strange results from regex.search
        self.assertEqual(regex.search('^([^z]*(?:WWWi|W))?$',
          'WWWi').groups(), ('WWWi', ))
        self.assertEqual(regex.search('^([^z]*(?:WWWi|w))?$',
          'WWWi').groups(), ('WWWi', ))
        self.assertEqual(regex.search('^([^z]*?(?:WWWi|W))?$',
          'WWWi').groups(), ('WWWi', ))

        # Hg issue 101: findall() broken (seems like memory corruption)
        pat = regex.compile(r'xxx', flags=regex.FULLCASE | regex.UNICODE)
        self.assertEqual([x.group() for x in pat.finditer('yxxx')], ['xxx'])
        self.assertEqual(pat.findall('yxxx'), ['xxx'])

        raw = 'yxxx'
        self.assertEqual([x.group() for x in pat.finditer(raw)], ['xxx'])
        self.assertEqual(pat.findall(raw), ['xxx'])

        pat = regex.compile(r'xxx', flags=regex.FULLCASE | regex.IGNORECASE |
          regex.UNICODE)
        self.assertEqual([x.group() for x in pat.finditer('yxxx')], ['xxx'])
        self.assertEqual(pat.findall('yxxx'), ['xxx'])

        raw = 'yxxx'
        self.assertEqual([x.group() for x in pat.finditer(raw)], ['xxx'])
        self.assertEqual(pat.findall(raw), ['xxx'])

        # Hg issue 106: * operator not working correctly with sub()
        if sys.version_info >= (3, 7, 0):
            self.assertEqual(regex.sub('(?V0).*', 'x', 'test'), 'xx')
        else:
            self.assertEqual(regex.sub('(?V0).*', 'x', 'test'), 'x')
        self.assertEqual(regex.sub('(?V1).*', 'x', 'test'), 'xx')

        if sys.version_info >= (3, 7, 0):
            self.assertEqual(regex.sub('(?V0).*?', '|', 'test'), '|||||||||')
        else:
            self.assertEqual(regex.sub('(?V0).*?', '|', 'test'), '|t|e|s|t|')
        self.assertEqual(regex.sub('(?V1).*?', '|', 'test'), '|||||||||')

        # Hg issue 112: re: OK, but regex: SystemError
        self.assertEqual(regex.sub(r'^(@)\n(?!.*?@)(.*)',
          r'\1\n==========\n\2', '@\n', flags=regex.DOTALL), '@\n==========\n')

        # Hg issue 109: Edit distance of fuzzy match
        self.assertEqual(regex.match(r'(?:cats|cat){e<=1}',
         'caz').fuzzy_counts, (1, 0, 0))
        self.assertEqual(regex.match(r'(?e)(?:cats|cat){e<=1}',
          'caz').fuzzy_counts, (1, 0, 0))
        self.assertEqual(regex.match(r'(?b)(?:cats|cat){e<=1}',
          'caz').fuzzy_counts, (1, 0, 0))

        self.assertEqual(regex.match(r'(?:cat){e<=1}', 'caz').fuzzy_counts,
          (1, 0, 0))
        self.assertEqual(regex.match(r'(?e)(?:cat){e<=1}',
          'caz').fuzzy_counts, (1, 0, 0))
        self.assertEqual(regex.match(r'(?b)(?:cat){e<=1}',
          'caz').fuzzy_counts, (1, 0, 0))

        self.assertEqual(regex.match(r'(?:cats){e<=2}', 'c ats').fuzzy_counts,
          (1, 1, 0))
        self.assertEqual(regex.match(r'(?e)(?:cats){e<=2}',
          'c ats').fuzzy_counts, (0, 1, 0))
        self.assertEqual(regex.match(r'(?b)(?:cats){e<=2}',
          'c ats').fuzzy_counts, (0, 1, 0))

        self.assertEqual(regex.match(r'(?:cats){e<=2}',
          'c a ts').fuzzy_counts, (0, 2, 0))
        self.assertEqual(regex.match(r'(?e)(?:cats){e<=2}',
          'c a ts').fuzzy_counts, (0, 2, 0))
        self.assertEqual(regex.match(r'(?b)(?:cats){e<=2}',
          'c a ts').fuzzy_counts, (0, 2, 0))

        self.assertEqual(regex.match(r'(?:cats){e<=1}', 'c ats').fuzzy_counts,
          (0, 1, 0))
        self.assertEqual(regex.match(r'(?e)(?:cats){e<=1}',
          'c ats').fuzzy_counts, (0, 1, 0))
        self.assertEqual(regex.match(r'(?b)(?:cats){e<=1}',
          'c ats').fuzzy_counts, (0, 1, 0))

        # Hg issue 115: Infinite loop when processing backreferences
        self.assertEqual(regex.findall(r'\bof ([a-z]+) of \1\b',
          'To make use of one of these modules'), [])

        # Hg issue 125: Reference to entire match (\g&lt;0&gt;) in
        # Pattern.sub() doesn't work as of 2014.09.22 release.
        self.assertEqual(regex.sub(r'x', r'\g<0>', 'x'), 'x')

        # Unreported issue: no such builtin as 'ascii' in Python 2.
        self.assertEqual(bool(regex.match(r'a', 'a', regex.DEBUG)), True)

        # Hg issue 131: nested sets behaviour
        self.assertEqual(regex.findall(r'(?V1)[[b-e]--cd]', 'abcdef'), ['b',
          'e'])
        self.assertEqual(regex.findall(r'(?V1)[b-e--cd]', 'abcdef'), ['b',
          'e'])
        self.assertEqual(regex.findall(r'(?V1)[[bcde]--cd]', 'abcdef'), ['b',
          'e'])
        self.assertEqual(regex.findall(r'(?V1)[bcde--cd]', 'abcdef'), ['b',
          'e'])

        # Hg issue 132: index out of range on null property \p{}
        self.assertRaisesRegex(regex.error, '^unknown property at position 4$',
          lambda: regex.compile(r'\p{}'))

        # Issue 23692.
        self.assertEqual(regex.match('(?:()|(?(1)()|z)){2}(?(2)a|z)',
          'a').group(0, 1, 2), ('a', '', ''))
        self.assertEqual(regex.match('(?:()|(?(1)()|z)){0,2}(?(2)a|z)',
          'a').group(0, 1, 2), ('a', '', ''))

        # Hg issue 137: Posix character class :punct: does not seem to be
        # supported.

        # Posix compatibility as recommended here:
        # http://www.unicode.org/reports/tr18/#Compatibility_Properties

        # Posix in Unicode.
        chars = ''.join(chr(c) for c in range(0x10000))

        self.assertEqual(ascii(''.join(regex.findall(r'''[[:alnum:]]+''',
          chars))), ascii(''.join(regex.findall(r'''[\p{Alpha}\p{PosixDigit}]+''',
          chars))))
        self.assertEqual(ascii(''.join(regex.findall(r'''[[:alpha:]]+''',
          chars))), ascii(''.join(regex.findall(r'''\p{Alpha}+''',
          chars))))
        self.assertEqual(ascii(''.join(regex.findall(r'''[[:ascii:]]+''',
          chars))), ascii(''.join(regex.findall(r'''[\p{InBasicLatin}]+''',
          chars))))
        self.assertEqual(ascii(''.join(regex.findall(r'''[[:blank:]]+''',
          chars))), ascii(''.join(regex.findall(r'''[\p{gc=Space_Separator}\t]+''',
          chars))))
        self.assertEqual(ascii(''.join(regex.findall(r'''[[:cntrl:]]+''',
          chars))), ascii(''.join(regex.findall(r'''\p{gc=Control}+''', chars))))
        self.assertEqual(ascii(''.join(regex.findall(r'''[[:digit:]]+''',
          chars))), ascii(''.join(regex.findall(r'''[0-9]+''', chars))))
        self.assertEqual(ascii(''.join(regex.findall(r'''[[:graph:]]+''',
          chars))), ascii(''.join(regex.findall(r'''[^\p{Space}\p{gc=Control}\p{gc=Surrogate}\p{gc=Unassigned}]+''',
          chars))))
        self.assertEqual(ascii(''.join(regex.findall(r'''[[:lower:]]+''',
          chars))), ascii(''.join(regex.findall(r'''\p{Lower}+''',
          chars))))
        self.assertEqual(ascii(''.join(regex.findall(r'''[[:print:]]+''',
          chars))), ascii(''.join(regex.findall(r'''(?V1)[\p{Graph}\p{Blank}--\p{Cntrl}]+''', chars))))
        self.assertEqual(ascii(''.join(regex.findall(r'''[[:punct:]]+''',
          chars))),
          ascii(''.join(regex.findall(r'''(?V1)[\p{gc=Punctuation}\p{gc=Symbol}--\p{Alpha}]+''',
          chars))))
        self.assertEqual(ascii(''.join(regex.findall(r'''[[:space:]]+''',
          chars))), ascii(''.join(regex.findall(r'''\p{Whitespace}+''',
          chars))))
        self.assertEqual(ascii(''.join(regex.findall(r'''[[:upper:]]+''',
          chars))), ascii(''.join(regex.findall(r'''\p{Upper}+''',
          chars))))
        self.assertEqual(ascii(''.join(regex.findall(r'''[[:word:]]+''',
          chars))), ascii(''.join(regex.findall(r'''[\p{Alpha}\p{gc=Mark}\p{Digit}\p{gc=Connector_Punctuation}\p{Join_Control}]+''',
          chars))))
        self.assertEqual(ascii(''.join(regex.findall(r'''[[:xdigit:]]+''',
          chars))), ascii(''.join(regex.findall(r'''[0-9A-Fa-f]+''',
          chars))))

        # Posix in ASCII.
        chars = bytes(range(0x100))

        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:alnum:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?a)[\p{Alpha}\p{PosixDigit}]+''',
          chars))))
        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:alpha:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?a)\p{Alpha}+''', chars))))
        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:ascii:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?a)[\x00-\x7F]+''', chars))))
        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:blank:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?a)[\p{gc=Space_Separator}\t]+''',
          chars))))
        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:cntrl:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?a)\p{gc=Control}+''',
          chars))))
        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:digit:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?a)[0-9]+''', chars))))
        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:graph:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?a)[^\p{Space}\p{gc=Control}\p{gc=Surrogate}\p{gc=Unassigned}]+''', chars))))
        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:lower:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?a)\p{Lower}+''', chars))))
        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:print:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?aV1)[\p{Graph}\p{Blank}--\p{Cntrl}]+''', chars))))
        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:punct:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?aV1)[\p{gc=Punctuation}\p{gc=Symbol}--\p{Alpha}]+''',
          chars))))
        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:space:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?a)\p{Whitespace}+''', chars))))
        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:upper:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?a)\p{Upper}+''', chars))))
        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:word:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?a)[\p{Alpha}\p{gc=Mark}\p{Digit}\p{gc=Connector_Punctuation}\p{Join_Control}]+''', chars))))
        self.assertEqual(ascii(b''.join(regex.findall(br'''(?a)[[:xdigit:]]+''',
          chars))), ascii(b''.join(regex.findall(br'''(?a)[0-9A-Fa-f]+''', chars))))

        # Hg issue 138: grapheme anchored search not working properly.
        self.assertEqual(ascii(regex.search(r'\X$', 'ab\u2103').group()),
          ascii('\u2103'))

        # Hg issue 139: Regular expression with multiple wildcards where first
        # should match empty string does not always work.
        self.assertEqual(regex.search("([^L]*)([^R]*R)", "LtR").groups(), ('',
          'LtR'))

        # Hg issue 140: Replace with REVERSE and groups has unexpected
        # behavior.
        self.assertEqual(regex.sub(r'(.)', r'x\1y', 'ab'), 'xayxby')
        self.assertEqual(regex.sub(r'(?r)(.)', r'x\1y', 'ab'), 'xayxby')
        self.assertEqual(regex.subf(r'(.)', 'x{1}y', 'ab'), 'xayxby')
        self.assertEqual(regex.subf(r'(?r)(.)', 'x{1}y', 'ab'), 'xayxby')

        # Hg issue 141: Crash on a certain partial match.
        self.assertEqual(regex.fullmatch('(a)*abc', 'ab',
          partial=True).span(), (0, 2))
        self.assertEqual(regex.fullmatch('(a)*abc', 'ab',
          partial=True).partial, True)

        # Hg issue 143: Partial matches have incorrect span if prefix is '.'
        # wildcard.
        self.assertEqual(regex.search('OXRG', 'OOGOX', partial=True).span(),
          (3, 5))
        self.assertEqual(regex.search('.XRG', 'OOGOX', partial=True).span(),
          (3, 5))
        self.assertEqual(regex.search('.{1,3}XRG', 'OOGOX',
          partial=True).span(), (1, 5))

        # Hg issue 144: Latest version problem with matching 'R|R'.
        self.assertEqual(regex.match('R|R', 'R').span(), (0, 1))

        # Hg issue 146: Forced-fail (?!) works improperly in conditional.
        self.assertEqual(regex.match(r'(.)(?(1)(?!))', 'xy'), None)

        # Groups cleared after failure.
        self.assertEqual(regex.findall(r'(y)?(\d)(?(1)\b\B)', 'ax1y2z3b'),
          [('', '1'), ('', '2'), ('', '3')])
        self.assertEqual(regex.findall(r'(y)?+(\d)(?(1)\b\B)', 'ax1y2z3b'),
          [('', '1'), ('', '2'), ('', '3')])

        # Hg issue 147: Fuzzy match can return match points beyond buffer end.
        self.assertEqual([m.span() for m in regex.finditer(r'(?i)(?:error){e}',
          'regex failure')], [(0, 5), (5, 10), (10, 13), (13, 13)])
        self.assertEqual([m.span() for m in
          regex.finditer(r'(?fi)(?:error){e}', 'regex failure')], [(0, 5), (5,
          10), (10, 13), (13, 13)])

        # Hg issue 150: Have an option for POSIX-compatible longest match of
        # alternates.
        self.assertEqual(regex.search(r'(?p)\d+(\w(\d*)?|[eE]([+-]\d+))',
          '10b12')[0], '10b12')
        self.assertEqual(regex.search(r'(?p)\d+(\w(\d*)?|[eE]([+-]\d+))',
          '10E+12')[0], '10E+12')

        self.assertEqual(regex.search(r'(?p)(\w|ae|oe|ue|ss)', 'ae')[0], 'ae')
        self.assertEqual(regex.search(r'(?p)one(self)?(selfsufficient)?',
          'oneselfsufficient')[0], 'oneselfsufficient')

        # Hg issue 151: Request: \K.
        self.assertEqual(regex.search(r'(ab\Kcd)', 'abcd').group(0, 1), ('cd',
          'abcd'))
        self.assertEqual(regex.findall(r'\w\w\K\w\w', 'abcdefgh'), ['cd',
          'gh'])
        self.assertEqual(regex.findall(r'(\w\w\K\w\w)', 'abcdefgh'), ['abcd',
          'efgh'])

        self.assertEqual(regex.search(r'(?r)(ab\Kcd)', 'abcd').group(0, 1),
          ('ab', 'abcd'))
        self.assertEqual(regex.findall(r'(?r)\w\w\K\w\w', 'abcdefgh'), ['ef',
          'ab'])
        self.assertEqual(regex.findall(r'(?r)(\w\w\K\w\w)', 'abcdefgh'),
          ['efgh', 'abcd'])

        # Hg issue 152: Request: Request: (?(DEFINE)...).
        self.assertEqual(regex.search(r'(?(DEFINE)(?<quant>\d+)(?<item>\w+))(?&quant) (?&item)',
          '5 elephants')[0], '5 elephants')

        self.assertEqual(regex.search(r'(?&routine)(?(DEFINE)(?<routine>.))', 'a').group('routine'), None)
        self.assertEqual(regex.search(r'(?&routine)(?(DEFINE)(?<routine>.))', 'a').captures('routine'), ['a'])

        # Hg issue 153: Request: (*SKIP).
        self.assertEqual(regex.search(r'12(*FAIL)|3', '123')[0], '3')
        self.assertEqual(regex.search(r'(?r)12(*FAIL)|3', '123')[0], '3')

        self.assertEqual(regex.search(r'\d+(*PRUNE)\d', '123'), None)
        self.assertEqual(regex.search(r'\d+(?=(*PRUNE))\d', '123')[0], '123')
        self.assertEqual(regex.search(r'\d+(*PRUNE)bcd|[3d]', '123bcd')[0],
          '123bcd')
        self.assertEqual(regex.search(r'\d+(*PRUNE)bcd|[3d]', '123zzd')[0],
          'd')
        self.assertEqual(regex.search(r'\d+?(*PRUNE)bcd|[3d]', '123bcd')[0],
          '3bcd')
        self.assertEqual(regex.search(r'\d+?(*PRUNE)bcd|[3d]', '123zzd')[0],
          'd')
        self.assertEqual(regex.search(r'\d++(?<=3(*PRUNE))zzd|[4d]$',
          '123zzd')[0], '123zzd')
        self.assertEqual(regex.search(r'\d++(?<=3(*PRUNE))zzd|[4d]$',
          '124zzd')[0], 'd')
        self.assertEqual(regex.search(r'\d++(?<=(*PRUNE)3)zzd|[4d]$',
          '124zzd')[0], 'd')
        self.assertEqual(regex.search(r'\d++(?<=2(*PRUNE)3)zzd|[3d]$',
          '124zzd')[0], 'd')

        self.assertEqual(regex.search(r'(?r)\d(*PRUNE)\d+', '123'), None)
        self.assertEqual(regex.search(r'(?r)\d(?<=(*PRUNE))\d+', '123')[0],
          '123')
        self.assertEqual(regex.search(r'(?r)\d+(*PRUNE)bcd|[3d]',
          '123bcd')[0], '123bcd')
        self.assertEqual(regex.search(r'(?r)\d+(*PRUNE)bcd|[3d]',
          '123zzd')[0], 'd')
        self.assertEqual(regex.search(r'(?r)\d++(?<=3(*PRUNE))zzd|[4d]$',
          '123zzd')[0], '123zzd')
        self.assertEqual(regex.search(r'(?r)\d++(?<=3(*PRUNE))zzd|[4d]$',
          '124zzd')[0], 'd')
        self.assertEqual(regex.search(r'(?r)\d++(?<=(*PRUNE)3)zzd|[4d]$',
          '124zzd')[0], 'd')
        self.assertEqual(regex.search(r'(?r)\d++(?<=2(*PRUNE)3)zzd|[3d]$',
          '124zzd')[0], 'd')

        self.assertEqual(regex.search(r'\d+(*SKIP)bcd|[3d]', '123bcd')[0],
          '123bcd')
        self.assertEqual(regex.search(r'\d+(*SKIP)bcd|[3d]', '123zzd')[0],
          'd')
        self.assertEqual(regex.search(r'\d+?(*SKIP)bcd|[3d]', '123bcd')[0],
          '3bcd')
        self.assertEqual(regex.search(r'\d+?(*SKIP)bcd|[3d]', '123zzd')[0],
          'd')
        self.assertEqual(regex.search(r'\d++(?<=3(*SKIP))zzd|[4d]$',
          '123zzd')[0], '123zzd')
        self.assertEqual(regex.search(r'\d++(?<=3(*SKIP))zzd|[4d]$',
          '124zzd')[0], 'd')
        self.assertEqual(regex.search(r'\d++(?<=(*SKIP)3)zzd|[4d]$',
          '124zzd')[0], 'd')
        self.assertEqual(regex.search(r'\d++(?<=2(*SKIP)3)zzd|[3d]$',
          '124zzd')[0], 'd')

        self.assertEqual(regex.search(r'(?r)\d+(*SKIP)bcd|[3d]', '123bcd')[0],
          '123bcd')
        self.assertEqual(regex.search(r'(?r)\d+(*SKIP)bcd|[3d]', '123zzd')[0],
          'd')
        self.assertEqual(regex.search(r'(?r)\d++(?<=3(*SKIP))zzd|[4d]$',
          '123zzd')[0], '123zzd')
        self.assertEqual(regex.search(r'(?r)\d++(?<=3(*SKIP))zzd|[4d]$',
          '124zzd')[0], 'd')
        self.assertEqual(regex.search(r'(?r)\d++(?<=(*SKIP)3)zzd|[4d]$',
          '124zzd')[0], 'd')
        self.assertEqual(regex.search(r'(?r)\d++(?<=2(*SKIP)3)zzd|[3d]$',
          '124zzd')[0], 'd')

        # Hg issue 154: Segmentation fault 11 when working with an atomic group
        text = """June 30, December 31, 2013 2012
some words follow:
more words and numbers 1,234,567 9,876,542
more words and numbers 1,234,567 9,876,542"""
        self.assertEqual(len(regex.findall(r'(?<!\d)(?>2014|2013 ?2012)', text)), 1)

        # Hg issue 156: regression on atomic grouping
        self.assertEqual(regex.match('1(?>2)', '12').span(), (0, 2))

        # Hg issue 157: regression: segfault on complex lookaround
        self.assertEqual(regex.match(r'(?V1w)(?=(?=[^A-Z]*+[A-Z])(?=[^a-z]*+[a-z]))(?=\D*+\d)(?=\p{Alphanumeric}*+\P{Alphanumeric})\A(?s:.){8,255}+\Z',
          'AAaa11!!')[0], 'AAaa11!!')

        # Hg issue 158: Group issue with (?(DEFINE)...)
        TEST_REGEX = regex.compile(r'''(?smx)
(?(DEFINE)
  (?<subcat>
   ^,[^,]+,
   )
)

# Group 2 is defined on this line
^,([^,]+),

(?:(?!(?&subcat)[\r\n]+(?&subcat)).)+
''')

        TEST_DATA = '''
,Cat 1,
,Brand 1,
some
thing
,Brand 2,
other
things
,Cat 2,
,Brand,
Some
thing
'''

        self.assertEqual([m.span(1, 2) for m in
          TEST_REGEX.finditer(TEST_DATA)], [((-1, -1), (2, 7)), ((-1, -1), (54,
          59))])

        # Hg issue 161: Unexpected fuzzy match results
        self.assertEqual(regex.search('(abcdefgh){e}',
          '******abcdefghijklmnopqrtuvwxyz', regex.BESTMATCH).span(), (6, 14))
        self.assertEqual(regex.search('(abcdefghi){e}',
          '******abcdefghijklmnopqrtuvwxyz', regex.BESTMATCH).span(), (6, 15))

        # Hg issue 163: allow lookarounds in conditionals.
        self.assertEqual(regex.match(r'(?:(?=\d)\d+\b|\w+)', '123abc').span(),
          (0, 6))
        self.assertEqual(regex.match(r'(?(?=\d)\d+\b|\w+)', '123abc'), None)
        self.assertEqual(regex.search(r'(?(?<=love\s)you|(?<=hate\s)her)',
          "I love you").span(), (7, 10))
        self.assertEqual(regex.findall(r'(?(?<=love\s)you|(?<=hate\s)her)',
          "I love you but I don't hate her either"), ['you', 'her'])

        # Hg issue 180: bug of POSIX matching.
        self.assertEqual(regex.search(r'(?p)a*(.*?)', 'aaabbb').group(0, 1),
          ('aaabbb', 'bbb'))
        self.assertEqual(regex.search(r'(?p)a*(.*)', 'aaabbb').group(0, 1),
          ('aaabbb', 'bbb'))
        self.assertEqual(regex.sub(r'(?p)a*(.*?)', r'\1', 'aaabbb'), 'bbb')
        self.assertEqual(regex.sub(r'(?p)a*(.*)', r'\1', 'aaabbb'), 'bbb')

        # Hg issue 192: Named lists reverse matching doesn't work with
        # IGNORECASE and V1
        self.assertEqual(regex.match(r'(?irV0)\L<kw>', '21', kw=['1']).span(),
          (1, 2))
        self.assertEqual(regex.match(r'(?irV1)\L<kw>', '21', kw=['1']).span(),
          (1, 2))

        # Hg issue 193: Alternation and .REVERSE flag.
        self.assertEqual(regex.search('a|b', '111a222').span(), (3, 4))
        self.assertEqual(regex.search('(?r)a|b', '111a222').span(), (3, 4))

        # Hg issue 194: .FULLCASE and Backreference
        self.assertEqual(regex.search(r'(?if)<(CLI)><\1>',
          '<cli><cli>').span(), (0, 10))
        self.assertEqual(regex.search(r'(?if)<(CLI)><\1>',
          '<cli><clI>').span(), (0, 10))
        self.assertEqual(regex.search(r'(?ifr)<\1><(CLI)>',
          '<cli><clI>').span(), (0, 10))

        # Hg issue 195: Pickle (or otherwise serial) the compiled regex
        r = regex.compile(r'\L<options>', options=['foo', 'bar'])
        p = pickle.dumps(r)
        r = pickle.loads(p)
        self.assertEqual(r.match('foo').span(), (0, 3))

        # Hg issue 196: Fuzzy matching on repeated regex not working as
        # expected
        self.assertEqual(regex.match('(x{6}){e<=1}', 'xxxxxx',
          flags=regex.BESTMATCH).span(), (0, 6))
        self.assertEqual(regex.match('(x{6}){e<=1}', 'xxxxx',
          flags=regex.BESTMATCH).span(), (0, 5))
        self.assertEqual(regex.match('(x{6}){e<=1}', 'x',
          flags=regex.BESTMATCH), None)
        self.assertEqual(regex.match('(?r)(x{6}){e<=1}', 'xxxxxx',
          flags=regex.BESTMATCH).span(), (0, 6))
        self.assertEqual(regex.match('(?r)(x{6}){e<=1}', 'xxxxx',
          flags=regex.BESTMATCH).span(), (0, 5))
        self.assertEqual(regex.match('(?r)(x{6}){e<=1}', 'x',
          flags=regex.BESTMATCH), None)

        # Hg issue 197: ValueError in regex.compile
        self.assertRaises(regex.error, lambda:
          regex.compile(b'00000\\0\\00\\^\50\\00\\U05000000'))

        # Hg issue 198: ValueError in regex.compile
        self.assertRaises(regex.error, lambda: regex.compile(b"{e<l"))

        # Hg issue 199: Segfault in re.compile
        self.assertEqual(bool(regex.compile('((?0)){e}')), True)

        # Hg issue 200: AttributeError in regex.compile with latest regex
        self.assertEqual(bool(regex.compile('\x00?(?0){e}')), True)

        # Hg issue 201: ENHANCEMATCH crashes interpreter
        self.assertEqual(regex.findall(r'((brown)|(lazy)){1<=e<=3} ((dog)|(fox)){1<=e<=3}',
          'The quick borwn fax jumped over the lzy hog', regex.ENHANCEMATCH),
          [('borwn', 'borwn', '', 'fax', '', 'fax'), ('lzy', '', 'lzy', 'hog',
          'hog', '')])

        # Hg issue 203: partial matching bug
        self.assertEqual(regex.search(r'\d\d\d-\d\d-\d\d\d\d',
          "My SSN is 999-89-76, but don't tell.", partial=True).span(), (36,
          36))

        # Hg issue 204: confusion of (?aif) flags
        upper_i = '\N{CYRILLIC CAPITAL LETTER SHORT I}'
        lower_i = '\N{CYRILLIC SMALL LETTER SHORT I}'

        self.assertEqual(bool(regex.match(r'(?ui)' + upper_i,
          lower_i)), True)
        self.assertEqual(bool(regex.match(r'(?ui)' + lower_i,
          upper_i)), True)

        self.assertEqual(bool(regex.match(r'(?ai)' + upper_i,
          lower_i)), False)
        self.assertEqual(bool(regex.match(r'(?ai)' + lower_i,
          upper_i)), False)

        self.assertEqual(bool(regex.match(r'(?afi)' + upper_i,
          lower_i)), False)
        self.assertEqual(bool(regex.match(r'(?afi)' + lower_i,
          upper_i)), False)

        # Hg issue 205: Named list and (?ri) flags
        self.assertEqual(bool(regex.search(r'(?i)\L<aa>', '22', aa=['121',
          '22'])), True)
        self.assertEqual(bool(regex.search(r'(?ri)\L<aa>', '22', aa=['121',
          '22'])), True)
        self.assertEqual(bool(regex.search(r'(?fi)\L<aa>', '22', aa=['121',
          '22'])), True)
        self.assertEqual(bool(regex.search(r'(?fri)\L<aa>', '22', aa=['121',
          '22'])), True)

        # Hg issue 208: Named list, (?ri) flags, Backreference
        self.assertEqual(regex.search(r'(?r)\1dog..(?<=(\L<aa>))$', 'ccdogcc',
          aa=['bcb', 'cc']). span(), (0, 7))
        self.assertEqual(regex.search(r'(?ir)\1dog..(?<=(\L<aa>))$',
          'ccdogcc', aa=['bcb', 'cc']). span(), (0, 7))

        # Hg issue 210: Fuzzy matching and Backreference
        self.assertEqual(regex.search(r'(2)(?:\1{5}){e<=1}',
          '3222212').span(), (1, 7))
        self.assertEqual(regex.search(r'(\d)(?:\1{5}){e<=1}',
          '3222212').span(), (1, 7))

        # Hg issue 211: Segmentation fault with recursive matches and atomic
        # groups
        self.assertEqual(regex.match(r'''\A(?P<whole>(?>\((?&whole)\)|[+\-]))\Z''',
          '((-))').span(), (0, 5))
        self.assertEqual(regex.match(r'''\A(?P<whole>(?>\((?&whole)\)|[+\-]))\Z''',
          '((-)+)'), None)

        # Hg issue 212: Unexpected matching difference with .*? between re and
        # regex
        self.assertEqual(regex.match(r"x.*? (.).*\1(.*)\1",
          'x  |y| z|').span(), (0, 9))
        self.assertEqual(regex.match(r"\.sr (.*?) (.)(.*)\2(.*)\2(.*)",
          r'.sr  h |<nw>|<span class="locked">|').span(), (0, 35))

        # Hg issue 213: Segmentation Fault
        a = '"\\xF9\\x80\\xAEqdz\\x95L\\xA7\\x89[\\xFE \\x91)\\xF9]\\xDB\'\\x99\\x09=\\x00\\xFD\\x98\\x22\\xDD\\xF1\\xB6\\xC3 Z\\xB6gv\\xA5x\\x93P\\xE1r\\x14\\x8Cv\\x0C\\xC0w\\x15r\\xFFc%" '
        py_regex_pattern = r'''(?P<http_referer>((?>(?<!\\)(?>"(?>\\.|[^\\"]+)+"|""|(?>'(?>\\.|[^\\']+)+')|''|(?>`(?>\\.|[^\\`]+)+`)|``)))) (?P<useragent>((?>(?<!\\)(?>"(?>\\.|[^\\"]+)+"|""|(?>'(?>\\.|[^\\']+)+')|''|(?>`(?>\\.|[^\\`]+)+`)|``))))'''
        self.assertEqual(bool(regex.search(py_regex_pattern, a)), False)

        # Hg Issue 216: Invalid match when using negative lookbehind and pipe
        self.assertEqual(bool(regex.match('foo(?<=foo)', 'foo')), True)
        self.assertEqual(bool(regex.match('foo(?<!foo)', 'foo')), False)
        self.assertEqual(bool(regex.match('foo(?<=foo|x)', 'foo')), True)
        self.assertEqual(bool(regex.match('foo(?<!foo|x)', 'foo')), False)

        # Hg issue 217: Core dump in conditional ahead match and matching \!
        # character
        self.assertEqual(bool(regex.match(r'(?(?=.*\!.*)(?P<true>.*\!\w*\:.*)|(?P<false>.*))',
          '!')), False)

        # Hg issue 220: Misbehavior of group capture with OR operand
        self.assertEqual(regex.match(r'\w*(ea)\w*|\w*e(?!a)\w*',
          'easier').groups(), ('ea', ))

        # Hg issue 225: BESTMATCH in fuzzy match not working
        self.assertEqual(regex.search('(^1234$){i,d}', '12234',
          regex.BESTMATCH).span(), (0, 5))
        self.assertEqual(regex.search('(^1234$){i,d}', '12234',
          regex.BESTMATCH).fuzzy_counts, (0, 1, 0))

        self.assertEqual(regex.search('(^1234$){s,i,d}', '12234',
          regex.BESTMATCH).span(), (0, 5))
        self.assertEqual(regex.search('(^1234$){s,i,d}', '12234',
          regex.BESTMATCH).fuzzy_counts, (0, 1, 0))

        # Hg issue 226: Error matching at start of string
        self.assertEqual(regex.search('(^123$){s,i,d}', 'xxxxxxxx123',
          regex.BESTMATCH).span(), (0, 11))
        self.assertEqual(regex.search('(^123$){s,i,d}', 'xxxxxxxx123',
          regex.BESTMATCH).fuzzy_counts, (0, 8, 0))

        # Hg issue 227: Incorrect behavior for ? operator with UNICODE +
        # IGNORECASE
        self.assertEqual(regex.search(r'a?yz', 'xxxxyz', flags=regex.FULLCASE |
          regex.IGNORECASE).span(), (4, 6))

        # Hg issue 230: Is it a bug of (?(DEFINE)...)
        self.assertEqual(regex.findall(r'(?:(?![a-d]).)+', 'abcdefgh'),
          ['efgh'])
        self.assertEqual(regex.findall(r'''(?(DEFINE)(?P<mydef>(?:(?![a-d]).)))(?&mydef)+''',
          'abcdefgh'), ['efgh'])

        # Hg issue 238: Not fully re backward compatible
        self.assertEqual(regex.findall(r'((\w{1,3})(\.{2,10})){1,3}',
          '"Erm....yes. T..T...Thank you for that."'), [('Erm....', 'Erm',
          '....'), ('T...', 'T', '...')])
        self.assertEqual(regex.findall(r'((\w{1,3})(\.{2,10})){3}',
          '"Erm....yes. T..T...Thank you for that."'), [])
        self.assertEqual(regex.findall(r'((\w{1,3})(\.{2,10})){2}',
          '"Erm....yes. T..T...Thank you for that."'), [('T...', 'T', '...')])
        self.assertEqual(regex.findall(r'((\w{1,3})(\.{2,10})){1}',
          '"Erm....yes. T..T...Thank you for that."'), [('Erm....', 'Erm',
          '....'), ('T..', 'T', '..'), ('T...', 'T', '...')])

        # Hg issue 247: Unexpected result with fuzzy matching and lookahead
        # expression
        self.assertEqual(regex.search(r'(?:ESTONIA(?!\w)){e<=1}',
          'ESTONIAN WORKERS').group(), 'ESTONIAN')
        self.assertEqual(regex.search(r'(?:ESTONIA(?=\W)){e<=1}',
          'ESTONIAN WORKERS').group(), 'ESTONIAN')

        self.assertEqual(regex.search(r'(?:(?<!\w)ESTONIA){e<=1}',
          'BLUB NESTONIA').group(), 'NESTONIA')
        self.assertEqual(regex.search(r'(?:(?<=\W)ESTONIA){e<=1}',
          'BLUB NESTONIA').group(), 'NESTONIA')

        self.assertEqual(regex.search(r'(?r)(?:ESTONIA(?!\w)){e<=1}',
          'ESTONIAN WORKERS').group(), 'ESTONIAN')
        self.assertEqual(regex.search(r'(?r)(?:ESTONIA(?=\W)){e<=1}',
          'ESTONIAN WORKERS').group(), 'ESTONIAN')

        self.assertEqual(regex.search(r'(?r)(?:(?<!\w)ESTONIA){e<=1}',
          'BLUB NESTONIA').group(), 'NESTONIA')
        self.assertEqual(regex.search(r'(?r)(?:(?<=\W)ESTONIA){e<=1}',
          'BLUB NESTONIA').group(), 'NESTONIA')

        # Hg issue 248: Unexpected result with fuzzy matching and more than one
        # non-greedy quantifier
        self.assertEqual(regex.search(r'(?:A.*B.*CDE){e<=2}',
          'A B CYZ').group(), 'A B CYZ')
        self.assertEqual(regex.search(r'(?:A.*B.*?CDE){e<=2}',
          'A B CYZ').group(), 'A B CYZ')
        self.assertEqual(regex.search(r'(?:A.*?B.*CDE){e<=2}',
          'A B CYZ').group(), 'A B CYZ')
        self.assertEqual(regex.search(r'(?:A.*?B.*?CDE){e<=2}',
          'A B CYZ').group(), 'A B CYZ')

        # Hg issue 249: Add an option to regex.escape() to not escape spaces
        self.assertEqual(regex.escape(' ,0A[', special_only=False, literal_spaces=False), '\\ \\,0A\\[')
        self.assertEqual(regex.escape(' ,0A[', special_only=False, literal_spaces=True), ' \\,0A\\[')
        self.assertEqual(regex.escape(' ,0A[', special_only=True, literal_spaces=False), '\\ ,0A\\[')
        self.assertEqual(regex.escape(' ,0A[', special_only=True, literal_spaces=True), ' ,0A\\[')

        self.assertEqual(regex.escape(' ,0A['), '\\ ,0A\\[')

        # Hg issue 251: Segfault with a particular expression
        self.assertEqual(regex.search(r'(?(?=A)A|B)', 'A').span(), (0, 1))
        self.assertEqual(regex.search(r'(?(?=A)A|B)', 'B').span(), (0, 1))
        self.assertEqual(regex.search(r'(?(?=A)A|)', 'B').span(), (0, 0))
        self.assertEqual(regex.search(r'(?(?=X)X|)', '').span(), (0, 0))
        self.assertEqual(regex.search(r'(?(?=X))', '').span(), (0, 0))

        # Hg issue 252: Empty capture strings when using DEFINE group reference
        # within look-behind expression
        self.assertEqual(regex.search(r'(?(DEFINE)(?<func>.))(?&func)',
          'abc').groups(), (None, ))
        self.assertEqual(regex.search(r'(?(DEFINE)(?<func>.))(?&func)',
          'abc').groupdict(), {'func': None})
        self.assertEqual(regex.search(r'(?(DEFINE)(?<func>.))(?&func)',
          'abc').capturesdict(), {'func': ['a']})

        self.assertEqual(regex.search(r'(?(DEFINE)(?<func>.))(?=(?&func))',
          'abc').groups(), (None, ))
        self.assertEqual(regex.search(r'(?(DEFINE)(?<func>.))(?=(?&func))',
          'abc').groupdict(), {'func': None})
        self.assertEqual(regex.search(r'(?(DEFINE)(?<func>.))(?=(?&func))',
          'abc').capturesdict(), {'func': ['a']})

        self.assertEqual(regex.search(r'(?(DEFINE)(?<func>.)).(?<=(?&func))',
          'abc').groups(), (None, ))
        self.assertEqual(regex.search(r'(?(DEFINE)(?<func>.)).(?<=(?&func))',
          'abc').groupdict(), {'func': None})
        self.assertEqual(regex.search(r'(?(DEFINE)(?<func>.)).(?<=(?&func))',
          'abc').capturesdict(), {'func': ['a']})

        # Hg issue 271: Comment logic different between Re and Regex
        self.assertEqual(bool(regex.match(r'ab(?#comment\))cd', 'abcd')), True)

        # Hg issue 276: Partial Matches yield incorrect matches and bounds
        self.assertEqual(regex.search(r'[a-z]+ [a-z]*?:', 'foo bar',
          partial=True).span(), (0, 7))
        self.assertEqual(regex.search(r'(?r):[a-z]*? [a-z]+', 'foo bar',
          partial=True).span(), (0, 7))

        # Hg issue 291: Include Script Extensions as a supported Unicode property
        self.assertEqual(bool(regex.match(r'(?u)\p{Script:Beng}',
          '\u09EF')), True)
        self.assertEqual(bool(regex.match(r'(?u)\p{Script:Bengali}',
          '\u09EF')), True)
        self.assertEqual(bool(regex.match(r'(?u)\p{Script_Extensions:Bengali}',
          '\u09EF')), True)
        self.assertEqual(bool(regex.match(r'(?u)\p{Script_Extensions:Beng}',
          '\u09EF')), True)
        self.assertEqual(bool(regex.match(r'(?u)\p{Script_Extensions:Cakm}',
          '\u09EF')), True)
        self.assertEqual(bool(regex.match(r'(?u)\p{Script_Extensions:Sylo}',
          '\u09EF')), True)

        # Hg issue #293: scx (Script Extensions) property currently matches
        # incorrectly
        self.assertEqual(bool(regex.match(r'(?u)\p{scx:Latin}', 'P')), True)
        self.assertEqual(bool(regex.match(r'(?u)\p{scx:Ahom}', 'P')), False)
        self.assertEqual(bool(regex.match(r'(?u)\p{scx:Common}', '4')), True)
        self.assertEqual(bool(regex.match(r'(?u)\p{scx:Caucasian_Albanian}', '4')),
          False)
        self.assertEqual(bool(regex.match(r'(?u)\p{scx:Arabic}', '\u062A')), True)
        self.assertEqual(bool(regex.match(r'(?u)\p{scx:Balinese}', '\u062A')),
          False)
        self.assertEqual(bool(regex.match(r'(?u)\p{scx:Devanagari}', '\u091C')),
          True)
        self.assertEqual(bool(regex.match(r'(?u)\p{scx:Batak}', '\u091C')), False)

        # Hg issue 296: Group references are not taken into account when group is reporting the last match
        self.assertEqual(regex.fullmatch('(?P<x>.)*(?&x)', 'abc').captures('x'),
          ['a', 'b', 'c'])
        self.assertEqual(regex.fullmatch('(?P<x>.)*(?&x)', 'abc').group('x'),
          'b')

        self.assertEqual(regex.fullmatch('(?P<x>.)(?P<x>.)(?P<x>.)',
          'abc').captures('x'), ['a', 'b', 'c'])
        self.assertEqual(regex.fullmatch('(?P<x>.)(?P<x>.)(?P<x>.)',
          'abc').group('x'), 'c')

        # Hg issue 299: Partial gives misleading results with "open ended" regexp
        self.assertEqual(regex.match('(?:ab)*', 'ab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?:ab)*', 'abab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?:ab)*?', '', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?:ab)*+', 'ab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?:ab)*+', 'abab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?:ab)+', 'ab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?:ab)+', 'abab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?:ab)+?', 'ab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?:ab)++', 'ab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?:ab)++', 'abab', partial=True).partial,
          False)

        self.assertEqual(regex.match('(?r)(?:ab)*', 'ab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?r)(?:ab)*', 'abab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?r)(?:ab)*?', '', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?r)(?:ab)*+', 'ab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?r)(?:ab)*+', 'abab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?r)(?:ab)+', 'ab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?r)(?:ab)+', 'abab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?r)(?:ab)+?', 'ab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?r)(?:ab)++', 'ab', partial=True).partial,
          False)
        self.assertEqual(regex.match('(?r)(?:ab)++', 'abab', partial=True).partial,
          False)

        self.assertEqual(regex.match('a*', '', partial=True).partial, False)
        self.assertEqual(regex.match('a*?', '', partial=True).partial, False)
        self.assertEqual(regex.match('a*+', '', partial=True).partial, False)
        self.assertEqual(regex.match('a+', '', partial=True).partial, True)
        self.assertEqual(regex.match('a+?', '', partial=True).partial, True)
        self.assertEqual(regex.match('a++', '', partial=True).partial, True)
        self.assertEqual(regex.match('a+', 'a', partial=True).partial, False)
        self.assertEqual(regex.match('a+?', 'a', partial=True).partial, False)
        self.assertEqual(regex.match('a++', 'a', partial=True).partial, False)

        self.assertEqual(regex.match('(?r)a*', '', partial=True).partial, False)
        self.assertEqual(regex.match('(?r)a*?', '', partial=True).partial, False)
        self.assertEqual(regex.match('(?r)a*+', '', partial=True).partial, False)
        self.assertEqual(regex.match('(?r)a+', '', partial=True).partial, True)
        self.assertEqual(regex.match('(?r)a+?', '', partial=True).partial, True)
        self.assertEqual(regex.match('(?r)a++', '', partial=True).partial, True)
        self.assertEqual(regex.match('(?r)a+', 'a', partial=True).partial, False)
        self.assertEqual(regex.match('(?r)a+?', 'a', partial=True).partial, False)
        self.assertEqual(regex.match('(?r)a++', 'a', partial=True).partial, False)

        self.assertEqual(regex.match(r"(?:\s*\w+'*)+", 'whatever', partial=True).partial,
          False)

        # Hg issue 300: segmentation fault
        pattern = ('(?P<termini5>GGCGTCACACTTTGCTATGCCATAGCAT[AG]TTTATCCATAAGA'
          'TTAGCGGATCCTACCTGACGCTTTTTATCGCAACTCTCTACTGTTTCTCCATAACAGAACATATTGA'
          'CTATCCGGTATTACCCGGCATGACAGGAGTAAAA){e<=1}'
          '(?P<gene>[ACGT]{1059}){e<=2}'
          '(?P<spacer>TAATCGTCTTGTTTGATACACAAGGGTCGCATCTGCGGCCCTTTTGCTTTTTTAAG'
          'TTGTAAGGATATGCCATTCTAGA){e<=0}'
          '(?P<barcode>[ACGT]{18}){e<=0}'
          '(?P<termini3>AGATCGG[CT]AGAGCGTCGTGTAGGGAAAGAGTGTGG){e<=1}')

        text = ('GCACGGCGTCACACTTTGCTATGCCATAGCATATTTATCCATAAGATTAGCGGATCCTACC'
          'TGACGCTTTTTATCGCAACTCTCTACTGTTTCTCCATAACAGAACATATTGACTATCCGGTATTACC'
          'CGGCATGACAGGAGTAAAAATGGCTATCGACGAAAACAAACAGAAAGCGTTGGCGGCAGCACTGGGC'
          'CAGATTGAGAAACAATTTGGTAAAGGCTCCATCATGCGCCTGGGTGAAGACCGTTCCATGGATGTGG'
          'AAACCATCTCTACCGGTTCGCTTTCACTGGATATCGCGCTTGGGGCAGGTGGTCTGCCGATGGGCCG'
          'TATCGTCGAAATCTACGGACCGGAATCTTCCGGTAAAACCACGCTGACGCTGCAGGTGATCGCCGCA'
          'GCGCAGCGTGAAGGTAAAACCTGTGCGTTTATCGATGCTGAACACGCGCTGGACCCAATCTACGCAC'
          'GTAAACTGGGCGTCGATATCGACAACCTGCTGTGCTCCCAGCCGGACACCGGCGAGCAGGCACTGGA'
          'AATCTGTGACGCCCTGGCGCGTTCTGGCGCAGTAGACGTTATCGTCGTTGACTCCGTGGCGGCACTG'
          'ACGCCGAAAGCGGAAATCGAAGGCGAAATCGGCGACTCTCATATGGGCCTTGCGGCACGTATGATGA'
          'GCCAGGCGATGCGTAAGCTGGCGGGTAACCTGAAGCAGTCCAACACGCTGCTGATCTTCATCAACCC'
          'CATCCGTATGAAAATTGGTGTGATGTTCGGCAACCCGGAAACCACTTACCGGTGGTAACGCGCTGAA'
          'ATTCTACGCCTCTGTTCGTCTCGACATCCGTTAAATCGGCGCGGTGAAAGAGGGCGAAAACGTGGTG'
          'GGTAGCGAAACCCGCGTGAAAGTGGTGAAGAACAAAATCGCTGCGCCGTTTAAACAGGCTGAATTCC'
          'AGATCCTCTACGGCGAAGGTATCAACTTCTACCCCGAACTGGTTGACCTGGGCGTAAAAGAGAAGCT'
          'GATCGAGAAAGCAGGCGCGTGGTACAGCTACAAAGGTGAGAAGATCGGTCAGGGTAAAGCGAATGCG'
          'ACTGCCTGGCTGAAATTTAACCCGGAAACCGCGAAAGAGATCGAGTGAAAAGTACGTGAGTTGCTGC'
          'TGAGCAACCCGAACTCAACGCCGGATTTCTCTGTAGATGATAGCGAAGGCGTAGCAGAAACTAACGA'
          'AGATTTTTAATCGTCTTGTTTGATACACAAGGGTCGCATCTGCGGCCCTTTTGCTTTTTTAAGTTGT'
          'AAGGATATGCCATTCTAGACAGTTAACACACCAACAAAGATCGGTAGAGCGTCGTGTAGGGAAAGAG'
          'TGTGGTACC')

        m = regex.search(pattern, text, flags=regex.BESTMATCH)
        self.assertEqual(m.fuzzy_counts, (0, 1, 0))
        self.assertEqual(m.fuzzy_changes, ([], [1206], []))

        # Hg issue 306: Fuzzy match parameters not respecting quantifier scope
        self.assertEqual(regex.search(r'(?e)(dogf(((oo){e<1})|((00){e<1}))d){e<2}',
          'dogfood').fuzzy_counts, (0, 0, 0))
        self.assertEqual(regex.search(r'(?e)(dogf(((oo){e<1})|((00){e<1}))d){e<2}',
          'dogfoot').fuzzy_counts, (1, 0, 0))

        # Hg issue 312: \X not matching graphemes with zero-width-joins
        self.assertEqual(regex.findall(r'\X',
          '\U0001F468\u200D\U0001F469\u200D\U0001F467\u200D\U0001F466'),
          ['\U0001F468\u200D\U0001F469\u200D\U0001F467\u200D\U0001F466'])

        # Hg issue 320: Abnormal performance
        self.assertEqual(bool(regex.search(r'(?=a)a', 'a')), True)
        self.assertEqual(bool(regex.search(r'(?!b)a', 'a')), True)

        # Hg issue 327: .fullmatch() causes MemoryError
        self.assertEqual(regex.fullmatch(r'((\d)*?)*?', '123').span(), (0, 3))

        # Hg issue 329: Wrong group matches when question mark quantifier is used within a look behind
        self.assertEqual(regex.search(r'''(?(DEFINE)(?<mydef>(?<wrong>THIS_SHOULD_NOT_MATCHx?)|(?<right>right))).*(?<=(?&mydef).*)''',
          'x right').capturesdict(), {'mydef': ['right'], 'wrong': [], 'right':
          ['right']})

        # Hg issue 338: specifying allowed characters when fuzzy-matching
        self.assertEqual(bool(regex.match(r'(?:cat){e<=1:[u]}', 'cut')), True)
        self.assertEqual(bool(regex.match(r'(?:cat){e<=1:u}', 'cut')), True)

        # Hg issue 353: fuzzy changes negative indexes
        self.assertEqual(regex.search(r'(?be)(AGTGTTCCCCGCGCCAGCGGGGATAAACCG){s<=5,i<=5,d<=5,s+i+d<=10}',
          'TTCCCCGCGCCAGCGGGGATAAACCG').fuzzy_changes, ([], [], [0, 1, 3, 5]))

        # Git issue 364: Contradictory values in fuzzy_counts and fuzzy_changes
        self.assertEqual(regex.match(r'(?:bc){e}', 'c').fuzzy_counts, (1, 0,
          1))
        self.assertEqual(regex.match(r'(?:bc){e}', 'c').fuzzy_changes, ([0],
          [], [1]))
        self.assertEqual(regex.match(r'(?e)(?:bc){e}', 'c').fuzzy_counts, (0,
          0, 1))
        self.assertEqual(regex.match(r'(?e)(?:bc){e}', 'c').fuzzy_changes,
          ([], [], [0]))
        self.assertEqual(regex.match(r'(?b)(?:bc){e}', 'c').fuzzy_counts, (0,
          0, 1))
        self.assertEqual(regex.match(r'(?b)(?:bc){e}', 'c').fuzzy_changes,
          ([], [], [0]))

        # Git issue 370: Confusions about Fuzzy matching behavior
        self.assertEqual(regex.match('(?e)(?:^(\\$ )?\\d{1,3}(,\\d{3})*(\\.\\d{2})$){e}',
          '$ 10,112.111.12').fuzzy_counts, (6, 0, 5))
        self.assertEqual(regex.match('(?e)(?:^(\\$ )?\\d{1,3}(,\\d{3})*(\\.\\d{2})$){s<=1}',
          '$ 10,112.111.12').fuzzy_counts, (1, 0, 0))
        self.assertEqual(regex.match('(?e)(?:^(\\$ )?\\d{1,3}(,\\d{3})*(\\.\\d{2})$){s<=1,i<=1,d<=1}',
          '$ 10,112.111.12').fuzzy_counts, (1, 0, 0))
        self.assertEqual(regex.match('(?e)(?:^(\\$ )?\\d{1,3}(,\\d{3})*(\\.\\d{2})$){s<=3}',
          '$ 10,1a2.111.12').fuzzy_counts, (2, 0, 0))
        self.assertEqual(regex.match('(?e)(?:^(\\$ )?\\d{1,3}(,\\d{3})*(\\.\\d{2})$){s<=2}',
          '$ 10,1a2.111.12').fuzzy_counts, (2, 0, 0))

        self.assertEqual(regex.fullmatch(r'(?e)(?:0?,0(?:,0)?){s<=1,d<=1}',
          ',0;0').fuzzy_counts, (1, 0, 0))
        self.assertEqual(regex.fullmatch(r'(?e)(?:0??,0(?:,0)?){s<=1,d<=1}',
          ',0;0').fuzzy_counts, (1, 0, 0))

        # Git issue 371: Specifying character set when fuzzy-matching allows characters not in the set
        self.assertEqual(regex.search(r"\b(?e)(?:\d{6,20}){i<=5:[\-\\\/]}\b",
          "cat dog starting at 00:01132.000. hello world"), None)

        # Git issue 385: Comments in expressions
        self.assertEqual(bool(regex.compile('(?#)')), True)
        self.assertEqual(bool(regex.compile('(?x)(?#)')), True)

        # Git issue 394: Unexpected behaviour in fuzzy matching with limited character set with IGNORECASE flag
        self.assertEqual(regex.findall(r'(\d+){i<=2:[ab]}', '123X4Y5'),
          ['123', '4', '5'])
        self.assertEqual(regex.findall(r'(?i)(\d+){i<=2:[ab]}', '123X4Y5'),
          ['123', '4', '5'])

        # Git issue 403: Fuzzy matching with wrong distance (unnecessary substitutions)
        self.assertEqual(regex.match(r'^(test){e<=5}$', 'terstin',
          flags=regex.B).fuzzy_counts, (0, 3, 0))

        # Git issue 408: regex fails with a quantified backreference but succeeds with repeated backref
        self.assertEqual(bool(regex.match(r"(?:(x*)\1\1\1)*x$", "x" * 5)), True)
        self.assertEqual(bool(regex.match(r"(?:(x*)\1{3})*x$", "x" * 5)), True)

        # Git issue 415: Fuzzy character restrictions don't apply to insertions at "right edge"
        self.assertEqual(regex.match(r't(?:es){s<=1:\d}t', 'te5t').group(),
          'te5t')
        self.assertEqual(regex.match(r't(?:es){s<=1:\d}t', 'tezt'), None)
        self.assertEqual(regex.match(r't(?:es){i<=1:\d}t', 'tes5t').group(),
          'tes5t')
        self.assertEqual(regex.match(r't(?:es){i<=1:\d}t', 'teszt'), None)
        self.assertEqual(regex.match(r't(?:es){i<=1:\d}t',
          'tes5t').fuzzy_changes, ([], [3], []))
        self.assertEqual(regex.match(r't(es){i<=1,0<e<=1}t', 'tes5t').group(),
          'tes5t')
        self.assertEqual(regex.match(r't(?:es){i<=1,0<e<=1:\d}t',
          'tes5t').fuzzy_changes, ([], [3], []))

        # Git issue 421: Fatal Python error: Segmentation fault
        self.assertEqual(regex.compile(r"(\d+ week|\d+ days)").split("7 days"), ['', '7 days', ''])
        self.assertEqual(regex.compile(r"(\d+ week|\d+ days)").split("10 days"), ['', '10 days', ''])

        self.assertEqual(regex.compile(r"[ ]* Name[ ]*\* ").search("  Name *"), None)

        self.assertEqual(regex.compile('a|\\.*pb\\.py').search('.geojs'), None)

        p = regex.compile('(?<=(?:\\A|\\W|_))(\\d+ decades? ago|\\d+ minutes ago|\\d+ seconds ago|in \\d+ decades?|\\d+ months ago|in \\d+ minutes|\\d+ minute ago|in \\d+ seconds|\\d+ second ago|\\d+ years ago|in \\d+ months|\\d+ month ago|\\d+ weeks ago|\\d+ hours ago|in \\d+ minute|in \\d+ second|in \\d+ years|\\d+ year ago|in \\d+ month|in \\d+ weeks|\\d+ week ago|\\d+ days ago|in \\d+ hours|\\d+ hour ago|in \\d+ year|in \\d+ week|in \\d+ days|\\d+ day ago|in \\d+ hour|\\d+ min ago|\\d+ sec ago|\\d+ yr ago|\\d+ mo ago|\\d+ wk ago|in \\d+ day|\\d+ hr ago|in \\d+ min|in \\d+ sec|in \\d+ yr|in \\d+ mo|in \\d+ wk|in \\d+ hr)(?=(?:\\Z|\\W|_))', flags=regex.I | regex.V0)
        self.assertEqual(p.search('1 month ago').group(), '1 month ago')
        self.assertEqual(p.search('9 hours 1 minute ago').group(), '1 minute ago')
        self.assertEqual(p.search('10 months 1 hour ago').group(), '1 hour ago')
        self.assertEqual(p.search('1 month 10 hours ago').group(), '10 hours ago')

        # Git issue 427: Possible bug with BESTMATCH
        sequence = 'TTCAGACGTGTGCTCTTCCGATCTCAATACCGACTCCTCACTGTGTGTCT'
        pattern = r'(?P<insert>.*)(?P<anchor>CTTCC){e<=1}(?P<umi>([ACGT]){4,6})(?P<sid>CAATACCGACTCCTCACTGTGT){e<=2}(?P<end>([ACGT]){0,6}$)'

        m = regex.match(pattern, sequence, flags=regex.BESTMATCH)
        self.assertEqual(m.span(), (0, 50))
        self.assertEqual(m.groupdict(), {'insert': 'TTCAGACGTGTGCT', 'anchor': 'CTTCC', 'umi': 'GATCT', 'sid': 'CAATACCGACTCCTCACTGTGT', 'end': 'GTCT'})

        m = regex.match(pattern, sequence, flags=regex.ENHANCEMATCH)
        self.assertEqual(m.span(), (0, 50))
        self.assertEqual(m.groupdict(), {'insert': 'TTCAGACGTGTGCT', 'anchor': 'CTTCC', 'umi': 'GATCT', 'sid': 'CAATACCGACTCCTCACTGTGT', 'end': 'GTCT'})

        # Git issue 433: Disagreement between fuzzy_counts and fuzzy_changes
        pattern = r'(?P<insert>.*)(?P<anchor>AACACTGG){e<=1}(?P<umi>([AT][CG]){5}){e<=2}(?P<sid>GTAACCGAAG){e<=2}(?P<end>([ACGT]){0,6}$)'

        sequence = 'GGAAAACACTGGTCTCAGTCTCGTAACCGAAGTGGTCG'
        m = regex.match(pattern, sequence, flags=regex.BESTMATCH)
        self.assertEqual(m.fuzzy_counts, (0, 0, 0))
        self.assertEqual(m.fuzzy_changes, ([], [], []))

        sequence = 'GGAAAACACTGGTCTCAGTCTCGTCCCCGAAGTGGTCG'
        m = regex.match(pattern, sequence, flags=regex.BESTMATCH)
        self.assertEqual(m.fuzzy_counts, (2, 0, 0))
        self.assertEqual(m.fuzzy_changes, ([24, 25], [], []))

        # Git issue 439: Unmatched groups: sub vs subf
        self.assertEqual(regex.sub(r'(test1)|(test2)', r'matched: \1\2', 'test1'), 'matched: test1')
        self.assertEqual(regex.subf(r'(test1)|(test2)', r'matched: {1}{2}', 'test1'), 'matched: test1')
        self.assertEqual(regex.search(r'(test1)|(test2)', 'matched: test1').expand(r'matched: \1\2'), 'matched: test1'),
        self.assertEqual(regex.search(r'(test1)|(test2)', 'matched: test1').expandf(r'matched: {1}{2}'), 'matched: test1')

        # Git issue 442: Fuzzy regex matching doesn't seem to test insertions correctly
        self.assertEqual(regex.search(r"(?:\bha\b){i:[ ]}", "having"), None)
        self.assertEqual(regex.search(r"(?:\bha\b){i:[ ]}", "having", flags=regex.I), None)

        # Git issue 467: Scoped inline flags 'a', 'u' and 'L' affect global flags
        self.assertEqual(regex.match(r'(?a:\w)\w', 'd\N{CYRILLIC SMALL LETTER ZHE}').span(), (0, 2))
        self.assertEqual(regex.match(r'(?a:\w)(?u:\w)', 'd\N{CYRILLIC SMALL LETTER ZHE}').span(), (0, 2))

        # Git issue 473: Emoji classified as letter
        self.assertEqual(regex.match(r'^\p{LC}+$', '\N{SMILING CAT FACE WITH OPEN MOUTH}'), None)
        self.assertEqual(regex.match(r'^\p{So}+$', '\N{SMILING CAT FACE WITH OPEN MOUTH}').span(), (0, 1))

        # Git issue 474: regex has no equivalent to `re.Match.groups()` for captures
        self.assertEqual(regex.match(r'(.)+', 'abc').allcaptures(), (['abc'], ['a', 'b', 'c']))
        self.assertEqual(regex.match(r'(.)+', 'abc').allspans(), ([(0, 3)], [(0, 1), (1, 2), (2, 3)]))

        # Git issue 477: \v for vertical spacing
        self.assertEqual(bool(regex.fullmatch(r'\p{HorizSpace}+', '\t \xA0\u1680\u180E\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200A\u202F\u205F\u3000')), True)
        self.assertEqual(bool(regex.fullmatch(r'\p{VertSpace}+', '\n\v\f\r\x85\u2028\u2029')), True)

        # Git issue 479: Segmentation fault when using conditional pattern
        self.assertEqual(regex.match(r'(?(?<=A)|(?(?![^B])C|D))', 'A'), None)
        self.assertEqual(regex.search(r'(?(?<=A)|(?(?![^B])C|D))', 'A').span(), (1, 1))

        # Git issue 494: Backtracking failure matching regex ^a?(a?)b?c\1$ against string abca
        self.assertEqual(regex.search(r"^a?(a?)b?c\1$", "abca").span(), (0, 4))

        # Git issue 498: Conditional negative lookahead inside positive lookahead fails to match
        self.assertEqual(regex.match(r'(?(?=a).|..)', 'ab').span(), (0, 1))
        self.assertEqual(regex.match(r'(?(?=b).|..)', 'ab').span(), (0, 2))
        self.assertEqual(regex.match(r'(?(?!a).|..)', 'ab').span(), (0, 2))
        self.assertEqual(regex.match(r'(?(?!b).|..)', 'ab').span(), (0, 1))

        # Git issue 525: segfault when fuzzy matching empty list
        self.assertEqual(regex.match(r"(\L<foo>){e<=5}", "blah", foo=[]).span(), (0, 0))

        # Git issue 527: `VERBOSE`/`X` flag breaks `\N` escapes
        self.assertEqual(regex.compile(r'\N{LATIN SMALL LETTER A}').match('a').span(), (0, 1))
        self.assertEqual(regex.compile(r'\N{LATIN SMALL LETTER A}', flags=regex.X).match('a').span(), (0, 1))

        # Git issue 539: Bug: Partial matching fails on a simple example
        self.assertEqual(regex.match(r"[^/]*b/ccc", "b/ccc", partial=True).span(), (0, 5))
        self.assertEqual(regex.match(r"[^/]*b/ccc", "b/ccb", partial=True), None)
        self.assertEqual(regex.match(r"[^/]*b/ccc", "b/cc", partial=True).span(), (0, 4))
        self.assertEqual(regex.match(r"[^/]*b/xyz", "b/xy", partial=True).span(), (0, 4))
        self.assertEqual(regex.match(r"[^/]*b/xyz", "b/yz", partial=True), None)

        self.assertEqual(regex.match(r"(?i)[^/]*b/ccc", "b/ccc", partial=True).span(), (0, 5))
        self.assertEqual(regex.match(r"(?i)[^/]*b/ccc", "b/ccb", partial=True), None)
        self.assertEqual(regex.match(r"(?i)[^/]*b/ccc", "b/cc", partial=True).span(), (0, 4))
        self.assertEqual(regex.match(r"(?i)[^/]*b/xyz", "b/xy", partial=True).span(), (0, 4))
        self.assertEqual(regex.match(r"(?i)[^/]*b/xyz", "b/yz", partial=True), None)

        # Git issue 546: Partial match not working in some instances with non-greedy capture
        self.assertEqual(bool(regex.match(r'<thinking>.*?</thinking>', '<', partial=True)), True)
        self.assertEqual(bool(regex.match(r'<thinking>.*?</thinking>', '<thinking', partial=True)), True)
        self.assertEqual(bool(regex.match(r'<thinking>.*?</thinking>', '<thinking>', partial=True)), True)
        self.assertEqual(bool(regex.match(r'<thinking>.*?</thinking>', '<thinking>x', partial=True)), True)
        self.assertEqual(bool(regex.match(r'<thinking>.*?</thinking>', '<thinking>xyz abc', partial=True)), True)
        self.assertEqual(bool(regex.match(r'<thinking>.*?</thinking>', '<thinking>xyz abc foo', partial=True)), True)
        self.assertEqual(bool(regex.match(r'<thinking>.*?</thinking>', '<thinking>xyz abc foo ', partial=True)), True)
        self.assertEqual(bool(regex.match(r'<thinking>.*?</thinking>', '<thinking>xyz abc foo bar', partial=True)), True)

    def test_fuzzy_ext(self):
        self.assertEqual(bool(regex.fullmatch(r'(?r)(?:a){e<=1:[a-z]}', 'e')),
          True)
        self.assertEqual(bool(regex.fullmatch(r'(?:a){e<=1:[a-z]}', 'e')),
          True)
        self.assertEqual(bool(regex.fullmatch(r'(?:a){e<=1:[a-z]}', '-')),
          False)
        self.assertEqual(bool(regex.fullmatch(r'(?r)(?:a){e<=1:[a-z]}', '-')),
          False)

        self.assertEqual(bool(regex.fullmatch(r'(?:a){e<=1:[a-z]}', 'ae')),
          True)
        self.assertEqual(bool(regex.fullmatch(r'(?r)(?:a){e<=1:[a-z]}',
          'ae')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?:a){e<=1:[a-z]}', 'a-')),
          False)
        self.assertEqual(bool(regex.fullmatch(r'(?r)(?:a){e<=1:[a-z]}',
          'a-')), False)

        self.assertEqual(bool(regex.fullmatch(r'(?:ab){e<=1:[a-z]}', 'ae')),
           True)
        self.assertEqual(bool(regex.fullmatch(r'(?r)(?:ab){e<=1:[a-z]}',
           'ae')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?:ab){e<=1:[a-z]}', 'a-')),
           False)
        self.assertEqual(bool(regex.fullmatch(r'(?r)(?:ab){e<=1:[a-z]}',
           'a-')), False)

        self.assertEqual(bool(regex.fullmatch(r'(a)\1{e<=1:[a-z]}', 'ae')),
           True)
        self.assertEqual(bool(regex.fullmatch(r'(?r)\1{e<=1:[a-z]}(a)',
           'ea')), True)
        self.assertEqual(bool(regex.fullmatch(r'(a)\1{e<=1:[a-z]}', 'a-')),
           False)
        self.assertEqual(bool(regex.fullmatch(r'(?r)\1{e<=1:[a-z]}(a)',
           '-a')), False)

        self.assertEqual(bool(regex.fullmatch(r'(?fiu)(?:\N{LATIN SMALL LETTER SHARP S}){e<=1:[a-z]}',
          'ts')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?fiu)(?:\N{LATIN SMALL LETTER SHARP S}){e<=1:[a-z]}',
          'st')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?firu)(?:\N{LATIN SMALL LETTER SHARP S}){e<=1:[a-z]}',
          'st')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?firu)(?:\N{LATIN SMALL LETTER SHARP S}){e<=1:[a-z]}',
          'ts')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?fiu)(?:\N{LATIN SMALL LETTER SHARP S}){e<=1:[a-z]}',
          '-s')), False)
        self.assertEqual(bool(regex.fullmatch(r'(?fiu)(?:\N{LATIN SMALL LETTER SHARP S}){e<=1:[a-z]}',
          's-')), False)
        self.assertEqual(bool(regex.fullmatch(r'(?firu)(?:\N{LATIN SMALL LETTER SHARP S}){e<=1:[a-z]}',
          's-')), False)
        self.assertEqual(bool(regex.fullmatch(r'(?firu)(?:\N{LATIN SMALL LETTER SHARP S}){e<=1:[a-z]}',
          '-s')), False)

        self.assertEqual(bool(regex.fullmatch(r'(?fiu)(\N{LATIN SMALL LETTER SHARP S})\1{e<=1:[a-z]}',
           'ssst')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?fiu)(\N{LATIN SMALL LETTER SHARP S})\1{e<=1:[a-z]}',
           'ssts')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?firu)\1{e<=1:[a-z]}(\N{LATIN SMALL LETTER SHARP S})',
           'stss')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?firu)\1{e<=1:[a-z]}(\N{LATIN SMALL LETTER SHARP S})',
           'tsss')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?fiu)(\N{LATIN SMALL LETTER SHARP S})\1{e<=1:[a-z]}',
           'ss-s')), False)
        self.assertEqual(bool(regex.fullmatch(r'(?fiu)(\N{LATIN SMALL LETTER SHARP S})\1{e<=1:[a-z]}',
           'sss-')), False)
        self.assertEqual(bool(regex.fullmatch(r'(?firu)(\N{LATIN SMALL LETTER SHARP S})\1{e<=1:[a-z]}',
           '-s')), False)
        self.assertEqual(bool(regex.fullmatch(r'(?firu)(\N{LATIN SMALL LETTER SHARP S})\1{e<=1:[a-z]}',
           's-')), False)

        self.assertEqual(bool(regex.fullmatch(r'(?fiu)(ss)\1{e<=1:[a-z]}',
           '\N{LATIN SMALL LETTER SHARP S}ts')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?fiu)(ss)\1{e<=1:[a-z]}',
           '\N{LATIN SMALL LETTER SHARP S}st')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?firu)\1{e<=1:[a-z]}(ss)',
           'st\N{LATIN SMALL LETTER SHARP S}')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?firu)\1{e<=1:[a-z]}(ss)',
           'ts\N{LATIN SMALL LETTER SHARP S}')), True)
        self.assertEqual(bool(regex.fullmatch(r'(?fiu)(ss)\1{e<=1:[a-z]}',
           '\N{LATIN SMALL LETTER SHARP S}-s')), False)
        self.assertEqual(bool(regex.fullmatch(r'(?fiu)(ss)\1{e<=1:[a-z]}',
           '\N{LATIN SMALL LETTER SHARP S}s-')), False)
        self.assertEqual(bool(regex.fullmatch(r'(?firu)(ss)\1{e<=1:[a-z]}',
           's-\N{LATIN SMALL LETTER SHARP S}')), False)
        self.assertEqual(bool(regex.fullmatch(r'(?firu)(ss)\1{e<=1:[a-z]}',
           '-s\N{LATIN SMALL LETTER SHARP S}')), False)

    def test_subscripted_captures(self):
        self.assertEqual(regex.match(r'(?P<x>.)+',
          'abc').expandf('{0} {0[0]} {0[-1]}'), 'abc abc abc')
        self.assertEqual(regex.match(r'(?P<x>.)+',
          'abc').expandf('{1} {1[0]} {1[1]} {1[2]} {1[-1]} {1[-2]} {1[-3]}'),
          'c a b c c b a')
        self.assertEqual(regex.match(r'(?P<x>.)+',
          'abc').expandf('{x} {x[0]} {x[1]} {x[2]} {x[-1]} {x[-2]} {x[-3]}'),
          'c a b c c b a')

        self.assertEqual(regex.subf(r'(?P<x>.)+', r'{0} {0[0]} {0[-1]}',
          'abc'), 'abc abc abc')
        self.assertEqual(regex.subf(r'(?P<x>.)+',
          '{1} {1[0]} {1[1]} {1[2]} {1[-1]} {1[-2]} {1[-3]}', 'abc'),
          'c a b c c b a')
        self.assertEqual(regex.subf(r'(?P<x>.)+',
          '{x} {x[0]} {x[1]} {x[2]} {x[-1]} {x[-2]} {x[-3]}', 'abc'),
          'c a b c c b a')

    def test_more_zerowidth(self):
        if sys.version_info >= (3, 7, 0):
            self.assertEqual(regex.split(r'\b|:+', 'a::bc'), ['', 'a', '', '',
              'bc', ''])
            self.assertEqual(regex.sub(r'\b|:+', '-', 'a::bc'), '-a---bc-')
            self.assertEqual(regex.findall(r'\b|:+', 'a::bc'), ['', '', '::',
              '', ''])
            self.assertEqual([m.span() for m in regex.finditer(r'\b|:+',
              'a::bc')], [(0, 0), (1, 1), (1, 3), (3, 3), (5, 5)])
            self.assertEqual([m.span() for m in regex.finditer(r'(?m)^\s*?$',
              'foo\n\n\nbar')], [(4, 4), (4, 5), (5, 5)])

    def test_line_ending(self):
      self.assertEqual(regex.findall(r'\R', '\r\n\n\x0B\f\r\x85\u2028\u2029'),
        ['\r\n', '\n', '\x0B', '\f', '\r', '\x85', '\u2028', '\u2029'])
      self.assertEqual(regex.findall(br'\R', b'\r\n\n\x0B\f\r\x85'), [b'\r\n',
        b'\n', b'\x0B', b'\f', b'\r'])

def test_main():
    unittest.main(verbosity=2)

if __name__ == "__main__":
    test_main()