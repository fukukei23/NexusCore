
# === NexusCore/openenv\Lib\site-packages\pip\_vendor\typing_extensions.py ===
import abc
import collections
import collections.abc
import contextlib
import functools
import inspect
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
    'get_overloads',
    'final',
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
    'TypeGuard',
    'TypeIs',
    'TYPE_CHECKING',
    'Never',
    'NoReturn',
    'ReadOnly',
    'Required',
    'NotRequired',

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
    'NoDefault',
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
        def __new__(cls, name, bases, ns, *, total=True, closed=False):
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
            extra_items_type = None

            for base in bases:
                base_dict = base.__dict__

                annotations.update(base_dict.get('__annotations__', {}))
                required_keys.update(base_dict.get('__required_keys__', ()))
                optional_keys.update(base_dict.get('__optional_keys__', ()))
                readonly_keys.update(base_dict.get('__readonly_keys__', ()))
                mutable_keys.update(base_dict.get('__mutable_keys__', ()))
                base_extra_items_type = base_dict.get('__extra_items__', None)
                if base_extra_items_type is not None:
                    extra_items_type = base_extra_items_type

            if closed and extra_items_type is None:
                extra_items_type = Never
            if closed and "__extra_items__" in own_annotations:
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
            if not hasattr(tp_dict, '__total__'):
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
    def TypedDict(typename, fields=_marker, /, *, total=True, closed=False, **kwargs):
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
            if closed is not False and closed is not True:
                kwargs["closed"] = closed
                closed = False
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

        td = _TypedDictMeta(typename, (), ns, total=total, closed=closed)
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
        if include_extras:
            return hint
        return {k: _strip_extras(t) for k, t in hint.items()}


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


if hasattr(typing, "NoDefault"):
    NoDefault = typing.NoDefault
else:
    class NoDefaultTypeMeta(type):
        def __setattr__(cls, attr, value):
            # TypeError is consistent with the behavior of NoneType
            raise TypeError(
                f"cannot set {attr!r} attribute of immutable type {cls.__name__!r}"
            )

    class NoDefaultType(metaclass=NoDefaultTypeMeta):
        """The type of the NoDefault singleton."""

        __slots__ = ()

        def __new__(cls):
            return globals().get("NoDefault") or object.__new__(cls)

        def __repr__(self):
            return "typing_extensions.NoDefault"

        def __reduce__(self):
            return "NoDefault"

    NoDefault = NoDefaultType()
    del NoDefaultType, NoDefaultTypeMeta


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


# 3.8-3.9
@typing._tp_cache
def _concatenate_getitem(self, parameters):
    if parameters == ():
        raise TypeError("Cannot take a Concatenate of no types.")
    if not isinstance(parameters, tuple):
        parameters = (parameters,)
    if not isinstance(parameters[-1], ParamSpec):
        raise TypeError("The last parameter to Concatenate should be a "
                        "ParamSpec variable.")
    msg = "Concatenate[arg, ...]: each arg must be a type."
    parameters = tuple(typing._type_check(p, msg) for p in parameters)
    return _ConcatenateGenericAlias(self, parameters)


# 3.10+
if hasattr(typing, 'Concatenate'):
    Concatenate = typing.Concatenate
    _ConcatenateGenericAlias = typing._ConcatenateGenericAlias
# 3.9
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
        is the intersection of the type inside ``TypeGuard`` and the argument's
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
        is the intersection of the type inside ``TypeGuard`` and the argument's
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

          from pip._vendor.typing_extensions import LiteralString

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

            from pip._vendor.typing_extensions import Never

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

    @_UnpackSpecialForm
    def Unpack(self, parameters):
        item = typing._type_check(parameters, f'{self._name} accepts only a single type.')
        return _UnpackAlias(self, (item,))

    def _is_unpack(obj):
        return isinstance(obj, _UnpackAlias)

else:  # 3.8
    class _UnpackAlias(typing._GenericAlias, _root=True):
        __class__ = typing.TypeVar

    class _UnpackForm(_ExtensionsSpecialForm, _root=True):
        def __getitem__(self, parameters):
            item = typing._type_check(parameters,
                                      f'{self._name} accepts only a single type.')
            return _UnpackAlias(self, (item,))

    Unpack = _UnpackForm('Unpack', doc=_UNPACK_DOC)

    def _is_unpack(obj):
        return isinstance(obj, _UnpackAlias)


if _PEP_696_IMPLEMENTED:
    from typing import TypeVarTuple

elif hasattr(typing, "TypeVarTuple"):  # 3.11+

    def _unpack_args(*args):
        newargs = []
        for arg in args:
            subargs = getattr(arg, '__typing_unpacked_tuple_args__', None)
            if subargs is not None and not (subargs and subargs[-1] is ...):
                newargs.extend(subargs)
            else:
                newargs.append(arg)
        return newargs

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

            from pip._vendor.typing_extensions import dataclass_transform

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


if hasattr(warnings, "deprecated"):
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
                def __new__(cls, *args, **kwargs):
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
                import functools

                @functools.wraps(arg)
                def wrapper(*args, **kwargs):
                    warnings.warn(msg, category=category, stacklevel=stacklevel + 1)
                    return arg(*args, **kwargs)

                arg.__deprecated__ = wrapper.__deprecated__ = msg
                return wrapper
            else:
                raise TypeError(
                    "@deprecated decorator with non-None category must be applied to "
                    f"a class or callable, not {arg!r}"
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
            elif isinstance(t, typevar_types) and t not in tvars:
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
            from pip._vendor.typing_extensions import NamedTuple, TypedDict

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


if hasattr(typing, "TypeAliasType"):
    TypeAliasType = typing.TypeAliasType
else:
    def _is_unionable(obj):
        """Corresponds to is_unionable() in unionobject.c in CPython."""
        return obj is None or isinstance(obj, (
            type,
            _types.GenericAlias,
            _types.UnionType,
            TypeAliasType,
        ))

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
            self.__value__ = value
            self.__type_params__ = type_params

            parameters = []
            for type_param in type_params:
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

        def __getitem__(self, parameters):
            if not isinstance(parameters, tuple):
                parameters = (parameters,)
            parameters = [
                typing._type_check(
                    item, f'Subscripting {self.__name__} requires a type.'
                )
                for item in parameters
            ]
            return typing._GenericAlias(self, tuple(parameters))

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

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\typing_extensions.py ===
import abc
import collections
import collections.abc
import contextlib
import functools
import inspect
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
    'get_overloads',
    'final',
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
    'TypeGuard',
    'TypeIs',
    'TYPE_CHECKING',
    'Never',
    'NoReturn',
    'ReadOnly',
    'Required',
    'NotRequired',

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
    'NoDefault',
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
        def __new__(cls, name, bases, ns, *, total=True, closed=False):
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
            extra_items_type = None

            for base in bases:
                base_dict = base.__dict__

                annotations.update(base_dict.get('__annotations__', {}))
                required_keys.update(base_dict.get('__required_keys__', ()))
                optional_keys.update(base_dict.get('__optional_keys__', ()))
                readonly_keys.update(base_dict.get('__readonly_keys__', ()))
                mutable_keys.update(base_dict.get('__mutable_keys__', ()))
                base_extra_items_type = base_dict.get('__extra_items__', None)
                if base_extra_items_type is not None:
                    extra_items_type = base_extra_items_type

            if closed and extra_items_type is None:
                extra_items_type = Never
            if closed and "__extra_items__" in own_annotations:
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
            if not hasattr(tp_dict, '__total__'):
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
    def TypedDict(typename, fields=_marker, /, *, total=True, closed=False, **kwargs):
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
            if closed is not False and closed is not True:
                kwargs["closed"] = closed
                closed = False
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

        td = _TypedDictMeta(typename, (), ns, total=total, closed=closed)
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
        if include_extras:
            return hint
        return {k: _strip_extras(t) for k, t in hint.items()}


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


if hasattr(typing, "NoDefault"):
    NoDefault = typing.NoDefault
else:
    class NoDefaultTypeMeta(type):
        def __setattr__(cls, attr, value):
            # TypeError is consistent with the behavior of NoneType
            raise TypeError(
                f"cannot set {attr!r} attribute of immutable type {cls.__name__!r}"
            )

    class NoDefaultType(metaclass=NoDefaultTypeMeta):
        """The type of the NoDefault singleton."""

        __slots__ = ()

        def __new__(cls):
            return globals().get("NoDefault") or object.__new__(cls)

        def __repr__(self):
            return "typing_extensions.NoDefault"

        def __reduce__(self):
            return "NoDefault"

    NoDefault = NoDefaultType()
    del NoDefaultType, NoDefaultTypeMeta


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


# 3.8-3.9
@typing._tp_cache
def _concatenate_getitem(self, parameters):
    if parameters == ():
        raise TypeError("Cannot take a Concatenate of no types.")
    if not isinstance(parameters, tuple):
        parameters = (parameters,)
    if not isinstance(parameters[-1], ParamSpec):
        raise TypeError("The last parameter to Concatenate should be a "
                        "ParamSpec variable.")
    msg = "Concatenate[arg, ...]: each arg must be a type."
    parameters = tuple(typing._type_check(p, msg) for p in parameters)
    return _ConcatenateGenericAlias(self, parameters)


# 3.10+
if hasattr(typing, 'Concatenate'):
    Concatenate = typing.Concatenate
    _ConcatenateGenericAlias = typing._ConcatenateGenericAlias
# 3.9
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
        is the intersection of the type inside ``TypeGuard`` and the argument's
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
        is the intersection of the type inside ``TypeGuard`` and the argument's
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

    @_UnpackSpecialForm
    def Unpack(self, parameters):
        item = typing._type_check(parameters, f'{self._name} accepts only a single type.')
        return _UnpackAlias(self, (item,))

    def _is_unpack(obj):
        return isinstance(obj, _UnpackAlias)

else:  # 3.8
    class _UnpackAlias(typing._GenericAlias, _root=True):
        __class__ = typing.TypeVar

    class _UnpackForm(_ExtensionsSpecialForm, _root=True):
        def __getitem__(self, parameters):
            item = typing._type_check(parameters,
                                      f'{self._name} accepts only a single type.')
            return _UnpackAlias(self, (item,))

    Unpack = _UnpackForm('Unpack', doc=_UNPACK_DOC)

    def _is_unpack(obj):
        return isinstance(obj, _UnpackAlias)


if _PEP_696_IMPLEMENTED:
    from typing import TypeVarTuple

elif hasattr(typing, "TypeVarTuple"):  # 3.11+

    def _unpack_args(*args):
        newargs = []
        for arg in args:
            subargs = getattr(arg, '__typing_unpacked_tuple_args__', None)
            if subargs is not None and not (subargs and subargs[-1] is ...):
                newargs.extend(subargs)
            else:
                newargs.append(arg)
        return newargs

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


if hasattr(warnings, "deprecated"):
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
                def __new__(cls, *args, **kwargs):
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
                import functools

                @functools.wraps(arg)
                def wrapper(*args, **kwargs):
                    warnings.warn(msg, category=category, stacklevel=stacklevel + 1)
                    return arg(*args, **kwargs)

                arg.__deprecated__ = wrapper.__deprecated__ = msg
                return wrapper
            else:
                raise TypeError(
                    "@deprecated decorator with non-None category must be applied to "
                    f"a class or callable, not {arg!r}"
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
            elif isinstance(t, typevar_types) and t not in tvars:
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


if hasattr(typing, "TypeAliasType"):
    TypeAliasType = typing.TypeAliasType
else:
    def _is_unionable(obj):
        """Corresponds to is_unionable() in unionobject.c in CPython."""
        return obj is None or isinstance(obj, (
            type,
            _types.GenericAlias,
            _types.UnionType,
            TypeAliasType,
        ))

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
            self.__value__ = value
            self.__type_params__ = type_params

            parameters = []
            for type_param in type_params:
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

        def __getitem__(self, parameters):
            if not isinstance(parameters, tuple):
                parameters = (parameters,)
            parameters = [
                typing._type_check(
                    item, f'Subscripting {self.__name__} requires a type.'
                )
                for item in parameters
            ]
            return typing._GenericAlias(self, tuple(parameters))

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

# === NexusCore/openenv\Lib\site-packages\fontTools\unicodedata\Scripts.py ===
# -*- coding: utf-8 -*-
#
# NOTE: This file was auto-generated with MetaTools/buildUCD.py.
# Source: https://unicode.org/Public/UNIDATA/Scripts.txt
# License: http://unicode.org/copyright.html#License
#
# Scripts-16.0.0.txt
# Date: 2024-04-30, 21:48:40 GMT
# © 2024 Unicode®, Inc.
# Unicode and the Unicode Logo are registered trademarks of Unicode, Inc. in the U.S. and other countries.
# For terms of use and license, see https://www.unicode.org/terms_of_use.html
#
# Unicode Character Database
#   For documentation, see https://www.unicode.org/reports/tr44/
# For more information, see:
#   UAX #24, Unicode Script Property: https://www.unicode.org/reports/tr24/
#     Especially the sections:
#       https://www.unicode.org/reports/tr24/#Assignment_Script_Values
#       https://www.unicode.org/reports/tr24/#Assignment_ScriptX_Values
#

RANGES = [
    0x0000,  # .. 0x0040 ; Common
    0x0041,  # .. 0x005A ; Latin
    0x005B,  # .. 0x0060 ; Common
    0x0061,  # .. 0x007A ; Latin
    0x007B,  # .. 0x00A9 ; Common
    0x00AA,  # .. 0x00AA ; Latin
    0x00AB,  # .. 0x00B9 ; Common
    0x00BA,  # .. 0x00BA ; Latin
    0x00BB,  # .. 0x00BF ; Common
    0x00C0,  # .. 0x00D6 ; Latin
    0x00D7,  # .. 0x00D7 ; Common
    0x00D8,  # .. 0x00F6 ; Latin
    0x00F7,  # .. 0x00F7 ; Common
    0x00F8,  # .. 0x02B8 ; Latin
    0x02B9,  # .. 0x02DF ; Common
    0x02E0,  # .. 0x02E4 ; Latin
    0x02E5,  # .. 0x02E9 ; Common
    0x02EA,  # .. 0x02EB ; Bopomofo
    0x02EC,  # .. 0x02FF ; Common
    0x0300,  # .. 0x036F ; Inherited
    0x0370,  # .. 0x0373 ; Greek
    0x0374,  # .. 0x0374 ; Common
    0x0375,  # .. 0x0377 ; Greek
    0x0378,  # .. 0x0379 ; Unknown
    0x037A,  # .. 0x037D ; Greek
    0x037E,  # .. 0x037E ; Common
    0x037F,  # .. 0x037F ; Greek
    0x0380,  # .. 0x0383 ; Unknown
    0x0384,  # .. 0x0384 ; Greek
    0x0385,  # .. 0x0385 ; Common
    0x0386,  # .. 0x0386 ; Greek
    0x0387,  # .. 0x0387 ; Common
    0x0388,  # .. 0x038A ; Greek
    0x038B,  # .. 0x038B ; Unknown
    0x038C,  # .. 0x038C ; Greek
    0x038D,  # .. 0x038D ; Unknown
    0x038E,  # .. 0x03A1 ; Greek
    0x03A2,  # .. 0x03A2 ; Unknown
    0x03A3,  # .. 0x03E1 ; Greek
    0x03E2,  # .. 0x03EF ; Coptic
    0x03F0,  # .. 0x03FF ; Greek
    0x0400,  # .. 0x0484 ; Cyrillic
    0x0485,  # .. 0x0486 ; Inherited
    0x0487,  # .. 0x052F ; Cyrillic
    0x0530,  # .. 0x0530 ; Unknown
    0x0531,  # .. 0x0556 ; Armenian
    0x0557,  # .. 0x0558 ; Unknown
    0x0559,  # .. 0x058A ; Armenian
    0x058B,  # .. 0x058C ; Unknown
    0x058D,  # .. 0x058F ; Armenian
    0x0590,  # .. 0x0590 ; Unknown
    0x0591,  # .. 0x05C7 ; Hebrew
    0x05C8,  # .. 0x05CF ; Unknown
    0x05D0,  # .. 0x05EA ; Hebrew
    0x05EB,  # .. 0x05EE ; Unknown
    0x05EF,  # .. 0x05F4 ; Hebrew
    0x05F5,  # .. 0x05FF ; Unknown
    0x0600,  # .. 0x0604 ; Arabic
    0x0605,  # .. 0x0605 ; Common
    0x0606,  # .. 0x060B ; Arabic
    0x060C,  # .. 0x060C ; Common
    0x060D,  # .. 0x061A ; Arabic
    0x061B,  # .. 0x061B ; Common
    0x061C,  # .. 0x061E ; Arabic
    0x061F,  # .. 0x061F ; Common
    0x0620,  # .. 0x063F ; Arabic
    0x0640,  # .. 0x0640 ; Common
    0x0641,  # .. 0x064A ; Arabic
    0x064B,  # .. 0x0655 ; Inherited
    0x0656,  # .. 0x066F ; Arabic
    0x0670,  # .. 0x0670 ; Inherited
    0x0671,  # .. 0x06DC ; Arabic
    0x06DD,  # .. 0x06DD ; Common
    0x06DE,  # .. 0x06FF ; Arabic
    0x0700,  # .. 0x070D ; Syriac
    0x070E,  # .. 0x070E ; Unknown
    0x070F,  # .. 0x074A ; Syriac
    0x074B,  # .. 0x074C ; Unknown
    0x074D,  # .. 0x074F ; Syriac
    0x0750,  # .. 0x077F ; Arabic
    0x0780,  # .. 0x07B1 ; Thaana
    0x07B2,  # .. 0x07BF ; Unknown
    0x07C0,  # .. 0x07FA ; Nko
    0x07FB,  # .. 0x07FC ; Unknown
    0x07FD,  # .. 0x07FF ; Nko
    0x0800,  # .. 0x082D ; Samaritan
    0x082E,  # .. 0x082F ; Unknown
    0x0830,  # .. 0x083E ; Samaritan
    0x083F,  # .. 0x083F ; Unknown
    0x0840,  # .. 0x085B ; Mandaic
    0x085C,  # .. 0x085D ; Unknown
    0x085E,  # .. 0x085E ; Mandaic
    0x085F,  # .. 0x085F ; Unknown
    0x0860,  # .. 0x086A ; Syriac
    0x086B,  # .. 0x086F ; Unknown
    0x0870,  # .. 0x088E ; Arabic
    0x088F,  # .. 0x088F ; Unknown
    0x0890,  # .. 0x0891 ; Arabic
    0x0892,  # .. 0x0896 ; Unknown
    0x0897,  # .. 0x08E1 ; Arabic
    0x08E2,  # .. 0x08E2 ; Common
    0x08E3,  # .. 0x08FF ; Arabic
    0x0900,  # .. 0x0950 ; Devanagari
    0x0951,  # .. 0x0954 ; Inherited
    0x0955,  # .. 0x0963 ; Devanagari
    0x0964,  # .. 0x0965 ; Common
    0x0966,  # .. 0x097F ; Devanagari
    0x0980,  # .. 0x0983 ; Bengali
    0x0984,  # .. 0x0984 ; Unknown
    0x0985,  # .. 0x098C ; Bengali
    0x098D,  # .. 0x098E ; Unknown
    0x098F,  # .. 0x0990 ; Bengali
    0x0991,  # .. 0x0992 ; Unknown
    0x0993,  # .. 0x09A8 ; Bengali
    0x09A9,  # .. 0x09A9 ; Unknown
    0x09AA,  # .. 0x09B0 ; Bengali
    0x09B1,  # .. 0x09B1 ; Unknown
    0x09B2,  # .. 0x09B2 ; Bengali
    0x09B3,  # .. 0x09B5 ; Unknown
    0x09B6,  # .. 0x09B9 ; Bengali
    0x09BA,  # .. 0x09BB ; Unknown
    0x09BC,  # .. 0x09C4 ; Bengali
    0x09C5,  # .. 0x09C6 ; Unknown
    0x09C7,  # .. 0x09C8 ; Bengali
    0x09C9,  # .. 0x09CA ; Unknown
    0x09CB,  # .. 0x09CE ; Bengali
    0x09CF,  # .. 0x09D6 ; Unknown
    0x09D7,  # .. 0x09D7 ; Bengali
    0x09D8,  # .. 0x09DB ; Unknown
    0x09DC,  # .. 0x09DD ; Bengali
    0x09DE,  # .. 0x09DE ; Unknown
    0x09DF,  # .. 0x09E3 ; Bengali
    0x09E4,  # .. 0x09E5 ; Unknown
    0x09E6,  # .. 0x09FE ; Bengali
    0x09FF,  # .. 0x0A00 ; Unknown
    0x0A01,  # .. 0x0A03 ; Gurmukhi
    0x0A04,  # .. 0x0A04 ; Unknown
    0x0A05,  # .. 0x0A0A ; Gurmukhi
    0x0A0B,  # .. 0x0A0E ; Unknown
    0x0A0F,  # .. 0x0A10 ; Gurmukhi
    0x0A11,  # .. 0x0A12 ; Unknown
    0x0A13,  # .. 0x0A28 ; Gurmukhi
    0x0A29,  # .. 0x0A29 ; Unknown
    0x0A2A,  # .. 0x0A30 ; Gurmukhi
    0x0A31,  # .. 0x0A31 ; Unknown
    0x0A32,  # .. 0x0A33 ; Gurmukhi
    0x0A34,  # .. 0x0A34 ; Unknown
    0x0A35,  # .. 0x0A36 ; Gurmukhi
    0x0A37,  # .. 0x0A37 ; Unknown
    0x0A38,  # .. 0x0A39 ; Gurmukhi
    0x0A3A,  # .. 0x0A3B ; Unknown
    0x0A3C,  # .. 0x0A3C ; Gurmukhi
    0x0A3D,  # .. 0x0A3D ; Unknown
    0x0A3E,  # .. 0x0A42 ; Gurmukhi
    0x0A43,  # .. 0x0A46 ; Unknown
    0x0A47,  # .. 0x0A48 ; Gurmukhi
    0x0A49,  # .. 0x0A4A ; Unknown
    0x0A4B,  # .. 0x0A4D ; Gurmukhi
    0x0A4E,  # .. 0x0A50 ; Unknown
    0x0A51,  # .. 0x0A51 ; Gurmukhi
    0x0A52,  # .. 0x0A58 ; Unknown
    0x0A59,  # .. 0x0A5C ; Gurmukhi
    0x0A5D,  # .. 0x0A5D ; Unknown
    0x0A5E,  # .. 0x0A5E ; Gurmukhi
    0x0A5F,  # .. 0x0A65 ; Unknown
    0x0A66,  # .. 0x0A76 ; Gurmukhi
    0x0A77,  # .. 0x0A80 ; Unknown
    0x0A81,  # .. 0x0A83 ; Gujarati
    0x0A84,  # .. 0x0A84 ; Unknown
    0x0A85,  # .. 0x0A8D ; Gujarati
    0x0A8E,  # .. 0x0A8E ; Unknown
    0x0A8F,  # .. 0x0A91 ; Gujarati
    0x0A92,  # .. 0x0A92 ; Unknown
    0x0A93,  # .. 0x0AA8 ; Gujarati
    0x0AA9,  # .. 0x0AA9 ; Unknown
    0x0AAA,  # .. 0x0AB0 ; Gujarati
    0x0AB1,  # .. 0x0AB1 ; Unknown
    0x0AB2,  # .. 0x0AB3 ; Gujarati
    0x0AB4,  # .. 0x0AB4 ; Unknown
    0x0AB5,  # .. 0x0AB9 ; Gujarati
    0x0ABA,  # .. 0x0ABB ; Unknown
    0x0ABC,  # .. 0x0AC5 ; Gujarati
    0x0AC6,  # .. 0x0AC6 ; Unknown
    0x0AC7,  # .. 0x0AC9 ; Gujarati
    0x0ACA,  # .. 0x0ACA ; Unknown
    0x0ACB,  # .. 0x0ACD ; Gujarati
    0x0ACE,  # .. 0x0ACF ; Unknown
    0x0AD0,  # .. 0x0AD0 ; Gujarati
    0x0AD1,  # .. 0x0ADF ; Unknown
    0x0AE0,  # .. 0x0AE3 ; Gujarati
    0x0AE4,  # .. 0x0AE5 ; Unknown
    0x0AE6,  # .. 0x0AF1 ; Gujarati
    0x0AF2,  # .. 0x0AF8 ; Unknown
    0x0AF9,  # .. 0x0AFF ; Gujarati
    0x0B00,  # .. 0x0B00 ; Unknown
    0x0B01,  # .. 0x0B03 ; Oriya
    0x0B04,  # .. 0x0B04 ; Unknown
    0x0B05,  # .. 0x0B0C ; Oriya
    0x0B0D,  # .. 0x0B0E ; Unknown
    0x0B0F,  # .. 0x0B10 ; Oriya
    0x0B11,  # .. 0x0B12 ; Unknown
    0x0B13,  # .. 0x0B28 ; Oriya
    0x0B29,  # .. 0x0B29 ; Unknown
    0x0B2A,  # .. 0x0B30 ; Oriya
    0x0B31,  # .. 0x0B31 ; Unknown
    0x0B32,  # .. 0x0B33 ; Oriya
    0x0B34,  # .. 0x0B34 ; Unknown
    0x0B35,  # .. 0x0B39 ; Oriya
    0x0B3A,  # .. 0x0B3B ; Unknown
    0x0B3C,  # .. 0x0B44 ; Oriya
    0x0B45,  # .. 0x0B46 ; Unknown
    0x0B47,  # .. 0x0B48 ; Oriya
    0x0B49,  # .. 0x0B4A ; Unknown
    0x0B4B,  # .. 0x0B4D ; Oriya
    0x0B4E,  # .. 0x0B54 ; Unknown
    0x0B55,  # .. 0x0B57 ; Oriya
    0x0B58,  # .. 0x0B5B ; Unknown
    0x0B5C,  # .. 0x0B5D ; Oriya
    0x0B5E,  # .. 0x0B5E ; Unknown
    0x0B5F,  # .. 0x0B63 ; Oriya
    0x0B64,  # .. 0x0B65 ; Unknown
    0x0B66,  # .. 0x0B77 ; Oriya
    0x0B78,  # .. 0x0B81 ; Unknown
    0x0B82,  # .. 0x0B83 ; Tamil
    0x0B84,  # .. 0x0B84 ; Unknown
    0x0B85,  # .. 0x0B8A ; Tamil
    0x0B8B,  # .. 0x0B8D ; Unknown
    0x0B8E,  # .. 0x0B90 ; Tamil
    0x0B91,  # .. 0x0B91 ; Unknown
    0x0B92,  # .. 0x0B95 ; Tamil
    0x0B96,  # .. 0x0B98 ; Unknown
    0x0B99,  # .. 0x0B9A ; Tamil
    0x0B9B,  # .. 0x0B9B ; Unknown
    0x0B9C,  # .. 0x0B9C ; Tamil
    0x0B9D,  # .. 0x0B9D ; Unknown
    0x0B9E,  # .. 0x0B9F ; Tamil
    0x0BA0,  # .. 0x0BA2 ; Unknown
    0x0BA3,  # .. 0x0BA4 ; Tamil
    0x0BA5,  # .. 0x0BA7 ; Unknown
    0x0BA8,  # .. 0x0BAA ; Tamil
    0x0BAB,  # .. 0x0BAD ; Unknown
    0x0BAE,  # .. 0x0BB9 ; Tamil
    0x0BBA,  # .. 0x0BBD ; Unknown
    0x0BBE,  # .. 0x0BC2 ; Tamil
    0x0BC3,  # .. 0x0BC5 ; Unknown
    0x0BC6,  # .. 0x0BC8 ; Tamil
    0x0BC9,  # .. 0x0BC9 ; Unknown
    0x0BCA,  # .. 0x0BCD ; Tamil
    0x0BCE,  # .. 0x0BCF ; Unknown
    0x0BD0,  # .. 0x0BD0 ; Tamil
    0x0BD1,  # .. 0x0BD6 ; Unknown
    0x0BD7,  # .. 0x0BD7 ; Tamil
    0x0BD8,  # .. 0x0BE5 ; Unknown
    0x0BE6,  # .. 0x0BFA ; Tamil
    0x0BFB,  # .. 0x0BFF ; Unknown
    0x0C00,  # .. 0x0C0C ; Telugu
    0x0C0D,  # .. 0x0C0D ; Unknown
    0x0C0E,  # .. 0x0C10 ; Telugu
    0x0C11,  # .. 0x0C11 ; Unknown
    0x0C12,  # .. 0x0C28 ; Telugu
    0x0C29,  # .. 0x0C29 ; Unknown
    0x0C2A,  # .. 0x0C39 ; Telugu
    0x0C3A,  # .. 0x0C3B ; Unknown
    0x0C3C,  # .. 0x0C44 ; Telugu
    0x0C45,  # .. 0x0C45 ; Unknown
    0x0C46,  # .. 0x0C48 ; Telugu
    0x0C49,  # .. 0x0C49 ; Unknown
    0x0C4A,  # .. 0x0C4D ; Telugu
    0x0C4E,  # .. 0x0C54 ; Unknown
    0x0C55,  # .. 0x0C56 ; Telugu
    0x0C57,  # .. 0x0C57 ; Unknown
    0x0C58,  # .. 0x0C5A ; Telugu
    0x0C5B,  # .. 0x0C5C ; Unknown
    0x0C5D,  # .. 0x0C5D ; Telugu
    0x0C5E,  # .. 0x0C5F ; Unknown
    0x0C60,  # .. 0x0C63 ; Telugu
    0x0C64,  # .. 0x0C65 ; Unknown
    0x0C66,  # .. 0x0C6F ; Telugu
    0x0C70,  # .. 0x0C76 ; Unknown
    0x0C77,  # .. 0x0C7F ; Telugu
    0x0C80,  # .. 0x0C8C ; Kannada
    0x0C8D,  # .. 0x0C8D ; Unknown
    0x0C8E,  # .. 0x0C90 ; Kannada
    0x0C91,  # .. 0x0C91 ; Unknown
    0x0C92,  # .. 0x0CA8 ; Kannada
    0x0CA9,  # .. 0x0CA9 ; Unknown
    0x0CAA,  # .. 0x0CB3 ; Kannada
    0x0CB4,  # .. 0x0CB4 ; Unknown
    0x0CB5,  # .. 0x0CB9 ; Kannada
    0x0CBA,  # .. 0x0CBB ; Unknown
    0x0CBC,  # .. 0x0CC4 ; Kannada
    0x0CC5,  # .. 0x0CC5 ; Unknown
    0x0CC6,  # .. 0x0CC8 ; Kannada
    0x0CC9,  # .. 0x0CC9 ; Unknown
    0x0CCA,  # .. 0x0CCD ; Kannada
    0x0CCE,  # .. 0x0CD4 ; Unknown
    0x0CD5,  # .. 0x0CD6 ; Kannada
    0x0CD7,  # .. 0x0CDC ; Unknown
    0x0CDD,  # .. 0x0CDE ; Kannada
    0x0CDF,  # .. 0x0CDF ; Unknown
    0x0CE0,  # .. 0x0CE3 ; Kannada
    0x0CE4,  # .. 0x0CE5 ; Unknown
    0x0CE6,  # .. 0x0CEF ; Kannada
    0x0CF0,  # .. 0x0CF0 ; Unknown
    0x0CF1,  # .. 0x0CF3 ; Kannada
    0x0CF4,  # .. 0x0CFF ; Unknown
    0x0D00,  # .. 0x0D0C ; Malayalam
    0x0D0D,  # .. 0x0D0D ; Unknown
    0x0D0E,  # .. 0x0D10 ; Malayalam
    0x0D11,  # .. 0x0D11 ; Unknown
    0x0D12,  # .. 0x0D44 ; Malayalam
    0x0D45,  # .. 0x0D45 ; Unknown
    0x0D46,  # .. 0x0D48 ; Malayalam
    0x0D49,  # .. 0x0D49 ; Unknown
    0x0D4A,  # .. 0x0D4F ; Malayalam
    0x0D50,  # .. 0x0D53 ; Unknown
    0x0D54,  # .. 0x0D63 ; Malayalam
    0x0D64,  # .. 0x0D65 ; Unknown
    0x0D66,  # .. 0x0D7F ; Malayalam
    0x0D80,  # .. 0x0D80 ; Unknown
    0x0D81,  # .. 0x0D83 ; Sinhala
    0x0D84,  # .. 0x0D84 ; Unknown
    0x0D85,  # .. 0x0D96 ; Sinhala
    0x0D97,  # .. 0x0D99 ; Unknown
    0x0D9A,  # .. 0x0DB1 ; Sinhala
    0x0DB2,  # .. 0x0DB2 ; Unknown
    0x0DB3,  # .. 0x0DBB ; Sinhala
    0x0DBC,  # .. 0x0DBC ; Unknown
    0x0DBD,  # .. 0x0DBD ; Sinhala
    0x0DBE,  # .. 0x0DBF ; Unknown
    0x0DC0,  # .. 0x0DC6 ; Sinhala
    0x0DC7,  # .. 0x0DC9 ; Unknown
    0x0DCA,  # .. 0x0DCA ; Sinhala
    0x0DCB,  # .. 0x0DCE ; Unknown
    0x0DCF,  # .. 0x0DD4 ; Sinhala
    0x0DD5,  # .. 0x0DD5 ; Unknown
    0x0DD6,  # .. 0x0DD6 ; Sinhala
    0x0DD7,  # .. 0x0DD7 ; Unknown
    0x0DD8,  # .. 0x0DDF ; Sinhala
    0x0DE0,  # .. 0x0DE5 ; Unknown
    0x0DE6,  # .. 0x0DEF ; Sinhala
    0x0DF0,  # .. 0x0DF1 ; Unknown
    0x0DF2,  # .. 0x0DF4 ; Sinhala
    0x0DF5,  # .. 0x0E00 ; Unknown
    0x0E01,  # .. 0x0E3A ; Thai
    0x0E3B,  # .. 0x0E3E ; Unknown
    0x0E3F,  # .. 0x0E3F ; Common
    0x0E40,  # .. 0x0E5B ; Thai
    0x0E5C,  # .. 0x0E80 ; Unknown
    0x0E81,  # .. 0x0E82 ; Lao
    0x0E83,  # .. 0x0E83 ; Unknown
    0x0E84,  # .. 0x0E84 ; Lao
    0x0E85,  # .. 0x0E85 ; Unknown
    0x0E86,  # .. 0x0E8A ; Lao
    0x0E8B,  # .. 0x0E8B ; Unknown
    0x0E8C,  # .. 0x0EA3 ; Lao
    0x0EA4,  # .. 0x0EA4 ; Unknown
    0x0EA5,  # .. 0x0EA5 ; Lao
    0x0EA6,  # .. 0x0EA6 ; Unknown
    0x0EA7,  # .. 0x0EBD ; Lao
    0x0EBE,  # .. 0x0EBF ; Unknown
    0x0EC0,  # .. 0x0EC4 ; Lao
    0x0EC5,  # .. 0x0EC5 ; Unknown
    0x0EC6,  # .. 0x0EC6 ; Lao
    0x0EC7,  # .. 0x0EC7 ; Unknown
    0x0EC8,  # .. 0x0ECE ; Lao
    0x0ECF,  # .. 0x0ECF ; Unknown
    0x0ED0,  # .. 0x0ED9 ; Lao
    0x0EDA,  # .. 0x0EDB ; Unknown
    0x0EDC,  # .. 0x0EDF ; Lao
    0x0EE0,  # .. 0x0EFF ; Unknown
    0x0F00,  # .. 0x0F47 ; Tibetan
    0x0F48,  # .. 0x0F48 ; Unknown
    0x0F49,  # .. 0x0F6C ; Tibetan
    0x0F6D,  # .. 0x0F70 ; Unknown
    0x0F71,  # .. 0x0F97 ; Tibetan
    0x0F98,  # .. 0x0F98 ; Unknown
    0x0F99,  # .. 0x0FBC ; Tibetan
    0x0FBD,  # .. 0x0FBD ; Unknown
    0x0FBE,  # .. 0x0FCC ; Tibetan
    0x0FCD,  # .. 0x0FCD ; Unknown
    0x0FCE,  # .. 0x0FD4 ; Tibetan
    0x0FD5,  # .. 0x0FD8 ; Common
    0x0FD9,  # .. 0x0FDA ; Tibetan
    0x0FDB,  # .. 0x0FFF ; Unknown
    0x1000,  # .. 0x109F ; Myanmar
    0x10A0,  # .. 0x10C5 ; Georgian
    0x10C6,  # .. 0x10C6 ; Unknown
    0x10C7,  # .. 0x10C7 ; Georgian
    0x10C8,  # .. 0x10CC ; Unknown
    0x10CD,  # .. 0x10CD ; Georgian
    0x10CE,  # .. 0x10CF ; Unknown
    0x10D0,  # .. 0x10FA ; Georgian
    0x10FB,  # .. 0x10FB ; Common
    0x10FC,  # .. 0x10FF ; Georgian
    0x1100,  # .. 0x11FF ; Hangul
    0x1200,  # .. 0x1248 ; Ethiopic
    0x1249,  # .. 0x1249 ; Unknown
    0x124A,  # .. 0x124D ; Ethiopic
    0x124E,  # .. 0x124F ; Unknown
    0x1250,  # .. 0x1256 ; Ethiopic
    0x1257,  # .. 0x1257 ; Unknown
    0x1258,  # .. 0x1258 ; Ethiopic
    0x1259,  # .. 0x1259 ; Unknown
    0x125A,  # .. 0x125D ; Ethiopic
    0x125E,  # .. 0x125F ; Unknown
    0x1260,  # .. 0x1288 ; Ethiopic
    0x1289,  # .. 0x1289 ; Unknown
    0x128A,  # .. 0x128D ; Ethiopic
    0x128E,  # .. 0x128F ; Unknown
    0x1290,  # .. 0x12B0 ; Ethiopic
    0x12B1,  # .. 0x12B1 ; Unknown
    0x12B2,  # .. 0x12B5 ; Ethiopic
    0x12B6,  # .. 0x12B7 ; Unknown
    0x12B8,  # .. 0x12BE ; Ethiopic
    0x12BF,  # .. 0x12BF ; Unknown
    0x12C0,  # .. 0x12C0 ; Ethiopic
    0x12C1,  # .. 0x12C1 ; Unknown
    0x12C2,  # .. 0x12C5 ; Ethiopic
    0x12C6,  # .. 0x12C7 ; Unknown
    0x12C8,  # .. 0x12D6 ; Ethiopic
    0x12D7,  # .. 0x12D7 ; Unknown
    0x12D8,  # .. 0x1310 ; Ethiopic
    0x1311,  # .. 0x1311 ; Unknown
    0x1312,  # .. 0x1315 ; Ethiopic
    0x1316,  # .. 0x1317 ; Unknown
    0x1318,  # .. 0x135A ; Ethiopic
    0x135B,  # .. 0x135C ; Unknown
    0x135D,  # .. 0x137C ; Ethiopic
    0x137D,  # .. 0x137F ; Unknown
    0x1380,  # .. 0x1399 ; Ethiopic
    0x139A,  # .. 0x139F ; Unknown
    0x13A0,  # .. 0x13F5 ; Cherokee
    0x13F6,  # .. 0x13F7 ; Unknown
    0x13F8,  # .. 0x13FD ; Cherokee
    0x13FE,  # .. 0x13FF ; Unknown
    0x1400,  # .. 0x167F ; Canadian_Aboriginal
    0x1680,  # .. 0x169C ; Ogham
    0x169D,  # .. 0x169F ; Unknown
    0x16A0,  # .. 0x16EA ; Runic
    0x16EB,  # .. 0x16ED ; Common
    0x16EE,  # .. 0x16F8 ; Runic
    0x16F9,  # .. 0x16FF ; Unknown
    0x1700,  # .. 0x1715 ; Tagalog
    0x1716,  # .. 0x171E ; Unknown
    0x171F,  # .. 0x171F ; Tagalog
    0x1720,  # .. 0x1734 ; Hanunoo
    0x1735,  # .. 0x1736 ; Common
    0x1737,  # .. 0x173F ; Unknown
    0x1740,  # .. 0x1753 ; Buhid
    0x1754,  # .. 0x175F ; Unknown
    0x1760,  # .. 0x176C ; Tagbanwa
    0x176D,  # .. 0x176D ; Unknown
    0x176E,  # .. 0x1770 ; Tagbanwa
    0x1771,  # .. 0x1771 ; Unknown
    0x1772,  # .. 0x1773 ; Tagbanwa
    0x1774,  # .. 0x177F ; Unknown
    0x1780,  # .. 0x17DD ; Khmer
    0x17DE,  # .. 0x17DF ; Unknown
    0x17E0,  # .. 0x17E9 ; Khmer
    0x17EA,  # .. 0x17EF ; Unknown
    0x17F0,  # .. 0x17F9 ; Khmer
    0x17FA,  # .. 0x17FF ; Unknown
    0x1800,  # .. 0x1801 ; Mongolian
    0x1802,  # .. 0x1803 ; Common
    0x1804,  # .. 0x1804 ; Mongolian
    0x1805,  # .. 0x1805 ; Common
    0x1806,  # .. 0x1819 ; Mongolian
    0x181A,  # .. 0x181F ; Unknown
    0x1820,  # .. 0x1878 ; Mongolian
    0x1879,  # .. 0x187F ; Unknown
    0x1880,  # .. 0x18AA ; Mongolian
    0x18AB,  # .. 0x18AF ; Unknown
    0x18B0,  # .. 0x18F5 ; Canadian_Aboriginal
    0x18F6,  # .. 0x18FF ; Unknown
    0x1900,  # .. 0x191E ; Limbu
    0x191F,  # .. 0x191F ; Unknown
    0x1920,  # .. 0x192B ; Limbu
    0x192C,  # .. 0x192F ; Unknown
    0x1930,  # .. 0x193B ; Limbu
    0x193C,  # .. 0x193F ; Unknown
    0x1940,  # .. 0x1940 ; Limbu
    0x1941,  # .. 0x1943 ; Unknown
    0x1944,  # .. 0x194F ; Limbu
    0x1950,  # .. 0x196D ; Tai_Le
    0x196E,  # .. 0x196F ; Unknown
    0x1970,  # .. 0x1974 ; Tai_Le
    0x1975,  # .. 0x197F ; Unknown
    0x1980,  # .. 0x19AB ; New_Tai_Lue
    0x19AC,  # .. 0x19AF ; Unknown
    0x19B0,  # .. 0x19C9 ; New_Tai_Lue
    0x19CA,  # .. 0x19CF ; Unknown
    0x19D0,  # .. 0x19DA ; New_Tai_Lue
    0x19DB,  # .. 0x19DD ; Unknown
    0x19DE,  # .. 0x19DF ; New_Tai_Lue
    0x19E0,  # .. 0x19FF ; Khmer
    0x1A00,  # .. 0x1A1B ; Buginese
    0x1A1C,  # .. 0x1A1D ; Unknown
    0x1A1E,  # .. 0x1A1F ; Buginese
    0x1A20,  # .. 0x1A5E ; Tai_Tham
    0x1A5F,  # .. 0x1A5F ; Unknown
    0x1A60,  # .. 0x1A7C ; Tai_Tham
    0x1A7D,  # .. 0x1A7E ; Unknown
    0x1A7F,  # .. 0x1A89 ; Tai_Tham
    0x1A8A,  # .. 0x1A8F ; Unknown
    0x1A90,  # .. 0x1A99 ; Tai_Tham
    0x1A9A,  # .. 0x1A9F ; Unknown
    0x1AA0,  # .. 0x1AAD ; Tai_Tham
    0x1AAE,  # .. 0x1AAF ; Unknown
    0x1AB0,  # .. 0x1ACE ; Inherited
    0x1ACF,  # .. 0x1AFF ; Unknown
    0x1B00,  # .. 0x1B4C ; Balinese
    0x1B4D,  # .. 0x1B4D ; Unknown
    0x1B4E,  # .. 0x1B7F ; Balinese
    0x1B80,  # .. 0x1BBF ; Sundanese
    0x1BC0,  # .. 0x1BF3 ; Batak
    0x1BF4,  # .. 0x1BFB ; Unknown
    0x1BFC,  # .. 0x1BFF ; Batak
    0x1C00,  # .. 0x1C37 ; Lepcha
    0x1C38,  # .. 0x1C3A ; Unknown
    0x1C3B,  # .. 0x1C49 ; Lepcha
    0x1C4A,  # .. 0x1C4C ; Unknown
    0x1C4D,  # .. 0x1C4F ; Lepcha
    0x1C50,  # .. 0x1C7F ; Ol_Chiki
    0x1C80,  # .. 0x1C8A ; Cyrillic
    0x1C8B,  # .. 0x1C8F ; Unknown
    0x1C90,  # .. 0x1CBA ; Georgian
    0x1CBB,  # .. 0x1CBC ; Unknown
    0x1CBD,  # .. 0x1CBF ; Georgian
    0x1CC0,  # .. 0x1CC7 ; Sundanese
    0x1CC8,  # .. 0x1CCF ; Unknown
    0x1CD0,  # .. 0x1CD2 ; Inherited
    0x1CD3,  # .. 0x1CD3 ; Common
    0x1CD4,  # .. 0x1CE0 ; Inherited
    0x1CE1,  # .. 0x1CE1 ; Common
    0x1CE2,  # .. 0x1CE8 ; Inherited
    0x1CE9,  # .. 0x1CEC ; Common
    0x1CED,  # .. 0x1CED ; Inherited
    0x1CEE,  # .. 0x1CF3 ; Common
    0x1CF4,  # .. 0x1CF4 ; Inherited
    0x1CF5,  # .. 0x1CF7 ; Common
    0x1CF8,  # .. 0x1CF9 ; Inherited
    0x1CFA,  # .. 0x1CFA ; Common
    0x1CFB,  # .. 0x1CFF ; Unknown
    0x1D00,  # .. 0x1D25 ; Latin
    0x1D26,  # .. 0x1D2A ; Greek
    0x1D2B,  # .. 0x1D2B ; Cyrillic
    0x1D2C,  # .. 0x1D5C ; Latin
    0x1D5D,  # .. 0x1D61 ; Greek
    0x1D62,  # .. 0x1D65 ; Latin
    0x1D66,  # .. 0x1D6A ; Greek
    0x1D6B,  # .. 0x1D77 ; Latin
    0x1D78,  # .. 0x1D78 ; Cyrillic
    0x1D79,  # .. 0x1DBE ; Latin
    0x1DBF,  # .. 0x1DBF ; Greek
    0x1DC0,  # .. 0x1DFF ; Inherited
    0x1E00,  # .. 0x1EFF ; Latin
    0x1F00,  # .. 0x1F15 ; Greek
    0x1F16,  # .. 0x1F17 ; Unknown
    0x1F18,  # .. 0x1F1D ; Greek
    0x1F1E,  # .. 0x1F1F ; Unknown
    0x1F20,  # .. 0x1F45 ; Greek
    0x1F46,  # .. 0x1F47 ; Unknown
    0x1F48,  # .. 0x1F4D ; Greek
    0x1F4E,  # .. 0x1F4F ; Unknown
    0x1F50,  # .. 0x1F57 ; Greek
    0x1F58,  # .. 0x1F58 ; Unknown
    0x1F59,  # .. 0x1F59 ; Greek
    0x1F5A,  # .. 0x1F5A ; Unknown
    0x1F5B,  # .. 0x1F5B ; Greek
    0x1F5C,  # .. 0x1F5C ; Unknown
    0x1F5D,  # .. 0x1F5D ; Greek
    0x1F5E,  # .. 0x1F5E ; Unknown
    0x1F5F,  # .. 0x1F7D ; Greek
    0x1F7E,  # .. 0x1F7F ; Unknown
    0x1F80,  # .. 0x1FB4 ; Greek
    0x1FB5,  # .. 0x1FB5 ; Unknown
    0x1FB6,  # .. 0x1FC4 ; Greek
    0x1FC5,  # .. 0x1FC5 ; Unknown
    0x1FC6,  # .. 0x1FD3 ; Greek
    0x1FD4,  # .. 0x1FD5 ; Unknown
    0x1FD6,  # .. 0x1FDB ; Greek
    0x1FDC,  # .. 0x1FDC ; Unknown
    0x1FDD,  # .. 0x1FEF ; Greek
    0x1FF0,  # .. 0x1FF1 ; Unknown
    0x1FF2,  # .. 0x1FF4 ; Greek
    0x1FF5,  # .. 0x1FF5 ; Unknown
    0x1FF6,  # .. 0x1FFE ; Greek
    0x1FFF,  # .. 0x1FFF ; Unknown
    0x2000,  # .. 0x200B ; Common
    0x200C,  # .. 0x200D ; Inherited
    0x200E,  # .. 0x2064 ; Common
    0x2065,  # .. 0x2065 ; Unknown
    0x2066,  # .. 0x2070 ; Common
    0x2071,  # .. 0x2071 ; Latin
    0x2072,  # .. 0x2073 ; Unknown
    0x2074,  # .. 0x207E ; Common
    0x207F,  # .. 0x207F ; Latin
    0x2080,  # .. 0x208E ; Common
    0x208F,  # .. 0x208F ; Unknown
    0x2090,  # .. 0x209C ; Latin
    0x209D,  # .. 0x209F ; Unknown
    0x20A0,  # .. 0x20C0 ; Common
    0x20C1,  # .. 0x20CF ; Unknown
    0x20D0,  # .. 0x20F0 ; Inherited
    0x20F1,  # .. 0x20FF ; Unknown
    0x2100,  # .. 0x2125 ; Common
    0x2126,  # .. 0x2126 ; Greek
    0x2127,  # .. 0x2129 ; Common
    0x212A,  # .. 0x212B ; Latin
    0x212C,  # .. 0x2131 ; Common
    0x2132,  # .. 0x2132 ; Latin
    0x2133,  # .. 0x214D ; Common
    0x214E,  # .. 0x214E ; Latin
    0x214F,  # .. 0x215F ; Common
    0x2160,  # .. 0x2188 ; Latin
    0x2189,  # .. 0x218B ; Common
    0x218C,  # .. 0x218F ; Unknown
    0x2190,  # .. 0x2429 ; Common
    0x242A,  # .. 0x243F ; Unknown
    0x2440,  # .. 0x244A ; Common
    0x244B,  # .. 0x245F ; Unknown
    0x2460,  # .. 0x27FF ; Common
    0x2800,  # .. 0x28FF ; Braille
    0x2900,  # .. 0x2B73 ; Common
    0x2B74,  # .. 0x2B75 ; Unknown
    0x2B76,  # .. 0x2B95 ; Common
    0x2B96,  # .. 0x2B96 ; Unknown
    0x2B97,  # .. 0x2BFF ; Common
    0x2C00,  # .. 0x2C5F ; Glagolitic
    0x2C60,  # .. 0x2C7F ; Latin
    0x2C80,  # .. 0x2CF3 ; Coptic
    0x2CF4,  # .. 0x2CF8 ; Unknown
    0x2CF9,  # .. 0x2CFF ; Coptic
    0x2D00,  # .. 0x2D25 ; Georgian
    0x2D26,  # .. 0x2D26 ; Unknown
    0x2D27,  # .. 0x2D27 ; Georgian
    0x2D28,  # .. 0x2D2C ; Unknown
    0x2D2D,  # .. 0x2D2D ; Georgian
    0x2D2E,  # .. 0x2D2F ; Unknown
    0x2D30,  # .. 0x2D67 ; Tifinagh
    0x2D68,  # .. 0x2D6E ; Unknown
    0x2D6F,  # .. 0x2D70 ; Tifinagh
    0x2D71,  # .. 0x2D7E ; Unknown
    0x2D7F,  # .. 0x2D7F ; Tifinagh
    0x2D80,  # .. 0x2D96 ; Ethiopic
    0x2D97,  # .. 0x2D9F ; Unknown
    0x2DA0,  # .. 0x2DA6 ; Ethiopic
    0x2DA7,  # .. 0x2DA7 ; Unknown
    0x2DA8,  # .. 0x2DAE ; Ethiopic
    0x2DAF,  # .. 0x2DAF ; Unknown
    0x2DB0,  # .. 0x2DB6 ; Ethiopic
    0x2DB7,  # .. 0x2DB7 ; Unknown
    0x2DB8,  # .. 0x2DBE ; Ethiopic
    0x2DBF,  # .. 0x2DBF ; Unknown
    0x2DC0,  # .. 0x2DC6 ; Ethiopic
    0x2DC7,  # .. 0x2DC7 ; Unknown
    0x2DC8,  # .. 0x2DCE ; Ethiopic
    0x2DCF,  # .. 0x2DCF ; Unknown
    0x2DD0,  # .. 0x2DD6 ; Ethiopic
    0x2DD7,  # .. 0x2DD7 ; Unknown
    0x2DD8,  # .. 0x2DDE ; Ethiopic
    0x2DDF,  # .. 0x2DDF ; Unknown
    0x2DE0,  # .. 0x2DFF ; Cyrillic
    0x2E00,  # .. 0x2E5D ; Common
    0x2E5E,  # .. 0x2E7F ; Unknown
    0x2E80,  # .. 0x2E99 ; Han
    0x2E9A,  # .. 0x2E9A ; Unknown
    0x2E9B,  # .. 0x2EF3 ; Han
    0x2EF4,  # .. 0x2EFF ; Unknown
    0x2F00,  # .. 0x2FD5 ; Han
    0x2FD6,  # .. 0x2FEF ; Unknown
    0x2FF0,  # .. 0x3004 ; Common
    0x3005,  # .. 0x3005 ; Han
    0x3006,  # .. 0x3006 ; Common
    0x3007,  # .. 0x3007 ; Han
    0x3008,  # .. 0x3020 ; Common
    0x3021,  # .. 0x3029 ; Han
    0x302A,  # .. 0x302D ; Inherited
    0x302E,  # .. 0x302F ; Hangul
    0x3030,  # .. 0x3037 ; Common
    0x3038,  # .. 0x303B ; Han
    0x303C,  # .. 0x303F ; Common
    0x3040,  # .. 0x3040 ; Unknown
    0x3041,  # .. 0x3096 ; Hiragana
    0x3097,  # .. 0x3098 ; Unknown
    0x3099,  # .. 0x309A ; Inherited
    0x309B,  # .. 0x309C ; Common
    0x309D,  # .. 0x309F ; Hiragana
    0x30A0,  # .. 0x30A0 ; Common
    0x30A1,  # .. 0x30FA ; Katakana
    0x30FB,  # .. 0x30FC ; Common
    0x30FD,  # .. 0x30FF ; Katakana
    0x3100,  # .. 0x3104 ; Unknown
    0x3105,  # .. 0x312F ; Bopomofo
    0x3130,  # .. 0x3130 ; Unknown
    0x3131,  # .. 0x318E ; Hangul
    0x318F,  # .. 0x318F ; Unknown
    0x3190,  # .. 0x319F ; Common
    0x31A0,  # .. 0x31BF ; Bopomofo
    0x31C0,  # .. 0x31E5 ; Common
    0x31E6,  # .. 0x31EE ; Unknown
    0x31EF,  # .. 0x31EF ; Common
    0x31F0,  # .. 0x31FF ; Katakana
    0x3200,  # .. 0x321E ; Hangul
    0x321F,  # .. 0x321F ; Unknown
    0x3220,  # .. 0x325F ; Common
    0x3260,  # .. 0x327E ; Hangul
    0x327F,  # .. 0x32CF ; Common
    0x32D0,  # .. 0x32FE ; Katakana
    0x32FF,  # .. 0x32FF ; Common
    0x3300,  # .. 0x3357 ; Katakana
    0x3358,  # .. 0x33FF ; Common
    0x3400,  # .. 0x4DBF ; Han
    0x4DC0,  # .. 0x4DFF ; Common
    0x4E00,  # .. 0x9FFF ; Han
    0xA000,  # .. 0xA48C ; Yi
    0xA48D,  # .. 0xA48F ; Unknown
    0xA490,  # .. 0xA4C6 ; Yi
    0xA4C7,  # .. 0xA4CF ; Unknown
    0xA4D0,  # .. 0xA4FF ; Lisu
    0xA500,  # .. 0xA62B ; Vai
    0xA62C,  # .. 0xA63F ; Unknown
    0xA640,  # .. 0xA69F ; Cyrillic
    0xA6A0,  # .. 0xA6F7 ; Bamum
    0xA6F8,  # .. 0xA6FF ; Unknown
    0xA700,  # .. 0xA721 ; Common
    0xA722,  # .. 0xA787 ; Latin
    0xA788,  # .. 0xA78A ; Common
    0xA78B,  # .. 0xA7CD ; Latin
    0xA7CE,  # .. 0xA7CF ; Unknown
    0xA7D0,  # .. 0xA7D1 ; Latin
    0xA7D2,  # .. 0xA7D2 ; Unknown
    0xA7D3,  # .. 0xA7D3 ; Latin
    0xA7D4,  # .. 0xA7D4 ; Unknown
    0xA7D5,  # .. 0xA7DC ; Latin
    0xA7DD,  # .. 0xA7F1 ; Unknown
    0xA7F2,  # .. 0xA7FF ; Latin
    0xA800,  # .. 0xA82C ; Syloti_Nagri
    0xA82D,  # .. 0xA82F ; Unknown
    0xA830,  # .. 0xA839 ; Common
    0xA83A,  # .. 0xA83F ; Unknown
    0xA840,  # .. 0xA877 ; Phags_Pa
    0xA878,  # .. 0xA87F ; Unknown
    0xA880,  # .. 0xA8C5 ; Saurashtra
    0xA8C6,  # .. 0xA8CD ; Unknown
    0xA8CE,  # .. 0xA8D9 ; Saurashtra
    0xA8DA,  # .. 0xA8DF ; Unknown
    0xA8E0,  # .. 0xA8FF ; Devanagari
    0xA900,  # .. 0xA92D ; Kayah_Li
    0xA92E,  # .. 0xA92E ; Common
    0xA92F,  # .. 0xA92F ; Kayah_Li
    0xA930,  # .. 0xA953 ; Rejang
    0xA954,  # .. 0xA95E ; Unknown
    0xA95F,  # .. 0xA95F ; Rejang
    0xA960,  # .. 0xA97C ; Hangul
    0xA97D,  # .. 0xA97F ; Unknown
    0xA980,  # .. 0xA9CD ; Javanese
    0xA9CE,  # .. 0xA9CE ; Unknown
    0xA9CF,  # .. 0xA9CF ; Common
    0xA9D0,  # .. 0xA9D9 ; Javanese
    0xA9DA,  # .. 0xA9DD ; Unknown
    0xA9DE,  # .. 0xA9DF ; Javanese
    0xA9E0,  # .. 0xA9FE ; Myanmar
    0xA9FF,  # .. 0xA9FF ; Unknown
    0xAA00,  # .. 0xAA36 ; Cham
    0xAA37,  # .. 0xAA3F ; Unknown
    0xAA40,  # .. 0xAA4D ; Cham
    0xAA4E,  # .. 0xAA4F ; Unknown
    0xAA50,  # .. 0xAA59 ; Cham
    0xAA5A,  # .. 0xAA5B ; Unknown
    0xAA5C,  # .. 0xAA5F ; Cham
    0xAA60,  # .. 0xAA7F ; Myanmar
    0xAA80,  # .. 0xAAC2 ; Tai_Viet
    0xAAC3,  # .. 0xAADA ; Unknown
    0xAADB,  # .. 0xAADF ; Tai_Viet
    0xAAE0,  # .. 0xAAF6 ; Meetei_Mayek
    0xAAF7,  # .. 0xAB00 ; Unknown
    0xAB01,  # .. 0xAB06 ; Ethiopic
    0xAB07,  # .. 0xAB08 ; Unknown
    0xAB09,  # .. 0xAB0E ; Ethiopic
    0xAB0F,  # .. 0xAB10 ; Unknown
    0xAB11,  # .. 0xAB16 ; Ethiopic
    0xAB17,  # .. 0xAB1F ; Unknown
    0xAB20,  # .. 0xAB26 ; Ethiopic
    0xAB27,  # .. 0xAB27 ; Unknown
    0xAB28,  # .. 0xAB2E ; Ethiopic
    0xAB2F,  # .. 0xAB2F ; Unknown
    0xAB30,  # .. 0xAB5A ; Latin
    0xAB5B,  # .. 0xAB5B ; Common
    0xAB5C,  # .. 0xAB64 ; Latin
    0xAB65,  # .. 0xAB65 ; Greek
    0xAB66,  # .. 0xAB69 ; Latin
    0xAB6A,  # .. 0xAB6B ; Common
    0xAB6C,  # .. 0xAB6F ; Unknown
    0xAB70,  # .. 0xABBF ; Cherokee
    0xABC0,  # .. 0xABED ; Meetei_Mayek
    0xABEE,  # .. 0xABEF ; Unknown
    0xABF0,  # .. 0xABF9 ; Meetei_Mayek
    0xABFA,  # .. 0xABFF ; Unknown
    0xAC00,  # .. 0xD7A3 ; Hangul
    0xD7A4,  # .. 0xD7AF ; Unknown
    0xD7B0,  # .. 0xD7C6 ; Hangul
    0xD7C7,  # .. 0xD7CA ; Unknown
    0xD7CB,  # .. 0xD7FB ; Hangul
    0xD7FC,  # .. 0xF8FF ; Unknown
    0xF900,  # .. 0xFA6D ; Han
    0xFA6E,  # .. 0xFA6F ; Unknown
    0xFA70,  # .. 0xFAD9 ; Han
    0xFADA,  # .. 0xFAFF ; Unknown
    0xFB00,  # .. 0xFB06 ; Latin
    0xFB07,  # .. 0xFB12 ; Unknown
    0xFB13,  # .. 0xFB17 ; Armenian
    0xFB18,  # .. 0xFB1C ; Unknown
    0xFB1D,  # .. 0xFB36 ; Hebrew
    0xFB37,  # .. 0xFB37 ; Unknown
    0xFB38,  # .. 0xFB3C ; Hebrew
    0xFB3D,  # .. 0xFB3D ; Unknown
    0xFB3E,  # .. 0xFB3E ; Hebrew
    0xFB3F,  # .. 0xFB3F ; Unknown
    0xFB40,  # .. 0xFB41 ; Hebrew
    0xFB42,  # .. 0xFB42 ; Unknown
    0xFB43,  # .. 0xFB44 ; Hebrew
    0xFB45,  # .. 0xFB45 ; Unknown
    0xFB46,  # .. 0xFB4F ; Hebrew
    0xFB50,  # .. 0xFBC2 ; Arabic
    0xFBC3,  # .. 0xFBD2 ; Unknown
    0xFBD3,  # .. 0xFD3D ; Arabic
    0xFD3E,  # .. 0xFD3F ; Common
    0xFD40,  # .. 0xFD8F ; Arabic
    0xFD90,  # .. 0xFD91 ; Unknown
    0xFD92,  # .. 0xFDC7 ; Arabic
    0xFDC8,  # .. 0xFDCE ; Unknown
    0xFDCF,  # .. 0xFDCF ; Arabic
    0xFDD0,  # .. 0xFDEF ; Unknown
    0xFDF0,  # .. 0xFDFF ; Arabic
    0xFE00,  # .. 0xFE0F ; Inherited
    0xFE10,  # .. 0xFE19 ; Common
    0xFE1A,  # .. 0xFE1F ; Unknown
    0xFE20,  # .. 0xFE2D ; Inherited
    0xFE2E,  # .. 0xFE2F ; Cyrillic
    0xFE30,  # .. 0xFE52 ; Common
    0xFE53,  # .. 0xFE53 ; Unknown
    0xFE54,  # .. 0xFE66 ; Common
    0xFE67,  # .. 0xFE67 ; Unknown
    0xFE68,  # .. 0xFE6B ; Common
    0xFE6C,  # .. 0xFE6F ; Unknown
    0xFE70,  # .. 0xFE74 ; Arabic
    0xFE75,  # .. 0xFE75 ; Unknown
    0xFE76,  # .. 0xFEFC ; Arabic
    0xFEFD,  # .. 0xFEFE ; Unknown
    0xFEFF,  # .. 0xFEFF ; Common
    0xFF00,  # .. 0xFF00 ; Unknown
    0xFF01,  # .. 0xFF20 ; Common
    0xFF21,  # .. 0xFF3A ; Latin
    0xFF3B,  # .. 0xFF40 ; Common
    0xFF41,  # .. 0xFF5A ; Latin
    0xFF5B,  # .. 0xFF65 ; Common
    0xFF66,  # .. 0xFF6F ; Katakana
    0xFF70,  # .. 0xFF70 ; Common
    0xFF71,  # .. 0xFF9D ; Katakana
    0xFF9E,  # .. 0xFF9F ; Common
    0xFFA0,  # .. 0xFFBE ; Hangul
    0xFFBF,  # .. 0xFFC1 ; Unknown
    0xFFC2,  # .. 0xFFC7 ; Hangul
    0xFFC8,  # .. 0xFFC9 ; Unknown
    0xFFCA,  # .. 0xFFCF ; Hangul
    0xFFD0,  # .. 0xFFD1 ; Unknown
    0xFFD2,  # .. 0xFFD7 ; Hangul
    0xFFD8,  # .. 0xFFD9 ; Unknown
    0xFFDA,  # .. 0xFFDC ; Hangul
    0xFFDD,  # .. 0xFFDF ; Unknown
    0xFFE0,  # .. 0xFFE6 ; Common
    0xFFE7,  # .. 0xFFE7 ; Unknown
    0xFFE8,  # .. 0xFFEE ; Common
    0xFFEF,  # .. 0xFFF8 ; Unknown
    0xFFF9,  # .. 0xFFFD ; Common
    0xFFFE,  # .. 0xFFFF ; Unknown
    0x10000,  # .. 0x1000B ; Linear_B
    0x1000C,  # .. 0x1000C ; Unknown
    0x1000D,  # .. 0x10026 ; Linear_B
    0x10027,  # .. 0x10027 ; Unknown
    0x10028,  # .. 0x1003A ; Linear_B
    0x1003B,  # .. 0x1003B ; Unknown
    0x1003C,  # .. 0x1003D ; Linear_B
    0x1003E,  # .. 0x1003E ; Unknown
    0x1003F,  # .. 0x1004D ; Linear_B
    0x1004E,  # .. 0x1004F ; Unknown
    0x10050,  # .. 0x1005D ; Linear_B
    0x1005E,  # .. 0x1007F ; Unknown
    0x10080,  # .. 0x100FA ; Linear_B
    0x100FB,  # .. 0x100FF ; Unknown
    0x10100,  # .. 0x10102 ; Common
    0x10103,  # .. 0x10106 ; Unknown
    0x10107,  # .. 0x10133 ; Common
    0x10134,  # .. 0x10136 ; Unknown
    0x10137,  # .. 0x1013F ; Common
    0x10140,  # .. 0x1018E ; Greek
    0x1018F,  # .. 0x1018F ; Unknown
    0x10190,  # .. 0x1019C ; Common
    0x1019D,  # .. 0x1019F ; Unknown
    0x101A0,  # .. 0x101A0 ; Greek
    0x101A1,  # .. 0x101CF ; Unknown
    0x101D0,  # .. 0x101FC ; Common
    0x101FD,  # .. 0x101FD ; Inherited
    0x101FE,  # .. 0x1027F ; Unknown
    0x10280,  # .. 0x1029C ; Lycian
    0x1029D,  # .. 0x1029F ; Unknown
    0x102A0,  # .. 0x102D0 ; Carian
    0x102D1,  # .. 0x102DF ; Unknown
    0x102E0,  # .. 0x102E0 ; Inherited
    0x102E1,  # .. 0x102FB ; Common
    0x102FC,  # .. 0x102FF ; Unknown
    0x10300,  # .. 0x10323 ; Old_Italic
    0x10324,  # .. 0x1032C ; Unknown
    0x1032D,  # .. 0x1032F ; Old_Italic
    0x10330,  # .. 0x1034A ; Gothic
    0x1034B,  # .. 0x1034F ; Unknown
    0x10350,  # .. 0x1037A ; Old_Permic
    0x1037B,  # .. 0x1037F ; Unknown
    0x10380,  # .. 0x1039D ; Ugaritic
    0x1039E,  # .. 0x1039E ; Unknown
    0x1039F,  # .. 0x1039F ; Ugaritic
    0x103A0,  # .. 0x103C3 ; Old_Persian
    0x103C4,  # .. 0x103C7 ; Unknown
    0x103C8,  # .. 0x103D5 ; Old_Persian
    0x103D6,  # .. 0x103FF ; Unknown
    0x10400,  # .. 0x1044F ; Deseret
    0x10450,  # .. 0x1047F ; Shavian
    0x10480,  # .. 0x1049D ; Osmanya
    0x1049E,  # .. 0x1049F ; Unknown
    0x104A0,  # .. 0x104A9 ; Osmanya
    0x104AA,  # .. 0x104AF ; Unknown
    0x104B0,  # .. 0x104D3 ; Osage
    0x104D4,  # .. 0x104D7 ; Unknown
    0x104D8,  # .. 0x104FB ; Osage
    0x104FC,  # .. 0x104FF ; Unknown
    0x10500,  # .. 0x10527 ; Elbasan
    0x10528,  # .. 0x1052F ; Unknown
    0x10530,  # .. 0x10563 ; Caucasian_Albanian
    0x10564,  # .. 0x1056E ; Unknown
    0x1056F,  # .. 0x1056F ; Caucasian_Albanian
    0x10570,  # .. 0x1057A ; Vithkuqi
    0x1057B,  # .. 0x1057B ; Unknown
    0x1057C,  # .. 0x1058A ; Vithkuqi
    0x1058B,  # .. 0x1058B ; Unknown
    0x1058C,  # .. 0x10592 ; Vithkuqi
    0x10593,  # .. 0x10593 ; Unknown
    0x10594,  # .. 0x10595 ; Vithkuqi
    0x10596,  # .. 0x10596 ; Unknown
    0x10597,  # .. 0x105A1 ; Vithkuqi
    0x105A2,  # .. 0x105A2 ; Unknown
    0x105A3,  # .. 0x105B1 ; Vithkuqi
    0x105B2,  # .. 0x105B2 ; Unknown
    0x105B3,  # .. 0x105B9 ; Vithkuqi
    0x105BA,  # .. 0x105BA ; Unknown
    0x105BB,  # .. 0x105BC ; Vithkuqi
    0x105BD,  # .. 0x105BF ; Unknown
    0x105C0,  # .. 0x105F3 ; Todhri
    0x105F4,  # .. 0x105FF ; Unknown
    0x10600,  # .. 0x10736 ; Linear_A
    0x10737,  # .. 0x1073F ; Unknown
    0x10740,  # .. 0x10755 ; Linear_A
    0x10756,  # .. 0x1075F ; Unknown
    0x10760,  # .. 0x10767 ; Linear_A
    0x10768,  # .. 0x1077F ; Unknown
    0x10780,  # .. 0x10785 ; Latin
    0x10786,  # .. 0x10786 ; Unknown
    0x10787,  # .. 0x107B0 ; Latin
    0x107B1,  # .. 0x107B1 ; Unknown
    0x107B2,  # .. 0x107BA ; Latin
    0x107BB,  # .. 0x107FF ; Unknown
    0x10800,  # .. 0x10805 ; Cypriot
    0x10806,  # .. 0x10807 ; Unknown
    0x10808,  # .. 0x10808 ; Cypriot
    0x10809,  # .. 0x10809 ; Unknown
    0x1080A,  # .. 0x10835 ; Cypriot
    0x10836,  # .. 0x10836 ; Unknown
    0x10837,  # .. 0x10838 ; Cypriot
    0x10839,  # .. 0x1083B ; Unknown
    0x1083C,  # .. 0x1083C ; Cypriot
    0x1083D,  # .. 0x1083E ; Unknown
    0x1083F,  # .. 0x1083F ; Cypriot
    0x10840,  # .. 0x10855 ; Imperial_Aramaic
    0x10856,  # .. 0x10856 ; Unknown
    0x10857,  # .. 0x1085F ; Imperial_Aramaic
    0x10860,  # .. 0x1087F ; Palmyrene
    0x10880,  # .. 0x1089E ; Nabataean
    0x1089F,  # .. 0x108A6 ; Unknown
    0x108A7,  # .. 0x108AF ; Nabataean
    0x108B0,  # .. 0x108DF ; Unknown
    0x108E0,  # .. 0x108F2 ; Hatran
    0x108F3,  # .. 0x108F3 ; Unknown
    0x108F4,  # .. 0x108F5 ; Hatran
    0x108F6,  # .. 0x108FA ; Unknown
    0x108FB,  # .. 0x108FF ; Hatran
    0x10900,  # .. 0x1091B ; Phoenician
    0x1091C,  # .. 0x1091E ; Unknown
    0x1091F,  # .. 0x1091F ; Phoenician
    0x10920,  # .. 0x10939 ; Lydian
    0x1093A,  # .. 0x1093E ; Unknown
    0x1093F,  # .. 0x1093F ; Lydian
    0x10940,  # .. 0x1097F ; Unknown
    0x10980,  # .. 0x1099F ; Meroitic_Hieroglyphs
    0x109A0,  # .. 0x109B7 ; Meroitic_Cursive
    0x109B8,  # .. 0x109BB ; Unknown
    0x109BC,  # .. 0x109CF ; Meroitic_Cursive
    0x109D0,  # .. 0x109D1 ; Unknown
    0x109D2,  # .. 0x109FF ; Meroitic_Cursive
    0x10A00,  # .. 0x10A03 ; Kharoshthi
    0x10A04,  # .. 0x10A04 ; Unknown
    0x10A05,  # .. 0x10A06 ; Kharoshthi
    0x10A07,  # .. 0x10A0B ; Unknown
    0x10A0C,  # .. 0x10A13 ; Kharoshthi
    0x10A14,  # .. 0x10A14 ; Unknown
    0x10A15,  # .. 0x10A17 ; Kharoshthi
    0x10A18,  # .. 0x10A18 ; Unknown
    0x10A19,  # .. 0x10A35 ; Kharoshthi
    0x10A36,  # .. 0x10A37 ; Unknown
    0x10A38,  # .. 0x10A3A ; Kharoshthi
    0x10A3B,  # .. 0x10A3E ; Unknown
    0x10A3F,  # .. 0x10A48 ; Kharoshthi
    0x10A49,  # .. 0x10A4F ; Unknown
    0x10A50,  # .. 0x10A58 ; Kharoshthi
    0x10A59,  # .. 0x10A5F ; Unknown
    0x10A60,  # .. 0x10A7F ; Old_South_Arabian
    0x10A80,  # .. 0x10A9F ; Old_North_Arabian
    0x10AA0,  # .. 0x10ABF ; Unknown
    0x10AC0,  # .. 0x10AE6 ; Manichaean
    0x10AE7,  # .. 0x10AEA ; Unknown
    0x10AEB,  # .. 0x10AF6 ; Manichaean
    0x10AF7,  # .. 0x10AFF ; Unknown
    0x10B00,  # .. 0x10B35 ; Avestan
    0x10B36,  # .. 0x10B38 ; Unknown
    0x10B39,  # .. 0x10B3F ; Avestan
    0x10B40,  # .. 0x10B55 ; Inscriptional_Parthian
    0x10B56,  # .. 0x10B57 ; Unknown
    0x10B58,  # .. 0x10B5F ; Inscriptional_Parthian
    0x10B60,  # .. 0x10B72 ; Inscriptional_Pahlavi
    0x10B73,  # .. 0x10B77 ; Unknown
    0x10B78,  # .. 0x10B7F ; Inscriptional_Pahlavi
    0x10B80,  # .. 0x10B91 ; Psalter_Pahlavi
    0x10B92,  # .. 0x10B98 ; Unknown
    0x10B99,  # .. 0x10B9C ; Psalter_Pahlavi
    0x10B9D,  # .. 0x10BA8 ; Unknown
    0x10BA9,  # .. 0x10BAF ; Psalter_Pahlavi
    0x10BB0,  # .. 0x10BFF ; Unknown
    0x10C00,  # .. 0x10C48 ; Old_Turkic
    0x10C49,  # .. 0x10C7F ; Unknown
    0x10C80,  # .. 0x10CB2 ; Old_Hungarian
    0x10CB3,  # .. 0x10CBF ; Unknown
    0x10CC0,  # .. 0x10CF2 ; Old_Hungarian
    0x10CF3,  # .. 0x10CF9 ; Unknown
    0x10CFA,  # .. 0x10CFF ; Old_Hungarian
    0x10D00,  # .. 0x10D27 ; Hanifi_Rohingya
    0x10D28,  # .. 0x10D2F ; Unknown
    0x10D30,  # .. 0x10D39 ; Hanifi_Rohingya
    0x10D3A,  # .. 0x10D3F ; Unknown
    0x10D40,  # .. 0x10D65 ; Garay
    0x10D66,  # .. 0x10D68 ; Unknown
    0x10D69,  # .. 0x10D85 ; Garay
    0x10D86,  # .. 0x10D8D ; Unknown
    0x10D8E,  # .. 0x10D8F ; Garay
    0x10D90,  # .. 0x10E5F ; Unknown
    0x10E60,  # .. 0x10E7E ; Arabic
    0x10E7F,  # .. 0x10E7F ; Unknown
    0x10E80,  # .. 0x10EA9 ; Yezidi
    0x10EAA,  # .. 0x10EAA ; Unknown
    0x10EAB,  # .. 0x10EAD ; Yezidi
    0x10EAE,  # .. 0x10EAF ; Unknown
    0x10EB0,  # .. 0x10EB1 ; Yezidi
    0x10EB2,  # .. 0x10EC1 ; Unknown
    0x10EC2,  # .. 0x10EC4 ; Arabic
    0x10EC5,  # .. 0x10EFB ; Unknown
    0x10EFC,  # .. 0x10EFF ; Arabic
    0x10F00,  # .. 0x10F27 ; Old_Sogdian
    0x10F28,  # .. 0x10F2F ; Unknown
    0x10F30,  # .. 0x10F59 ; Sogdian
    0x10F5A,  # .. 0x10F6F ; Unknown
    0x10F70,  # .. 0x10F89 ; Old_Uyghur
    0x10F8A,  # .. 0x10FAF ; Unknown
    0x10FB0,  # .. 0x10FCB ; Chorasmian
    0x10FCC,  # .. 0x10FDF ; Unknown
    0x10FE0,  # .. 0x10FF6 ; Elymaic
    0x10FF7,  # .. 0x10FFF ; Unknown
    0x11000,  # .. 0x1104D ; Brahmi
    0x1104E,  # .. 0x11051 ; Unknown
    0x11052,  # .. 0x11075 ; Brahmi
    0x11076,  # .. 0x1107E ; Unknown
    0x1107F,  # .. 0x1107F ; Brahmi
    0x11080,  # .. 0x110C2 ; Kaithi
    0x110C3,  # .. 0x110CC ; Unknown
    0x110CD,  # .. 0x110CD ; Kaithi
    0x110CE,  # .. 0x110CF ; Unknown
    0x110D0,  # .. 0x110E8 ; Sora_Sompeng
    0x110E9,  # .. 0x110EF ; Unknown
    0x110F0,  # .. 0x110F9 ; Sora_Sompeng
    0x110FA,  # .. 0x110FF ; Unknown
    0x11100,  # .. 0x11134 ; Chakma
    0x11135,  # .. 0x11135 ; Unknown
    0x11136,  # .. 0x11147 ; Chakma
    0x11148,  # .. 0x1114F ; Unknown
    0x11150,  # .. 0x11176 ; Mahajani
    0x11177,  # .. 0x1117F ; Unknown
    0x11180,  # .. 0x111DF ; Sharada
    0x111E0,  # .. 0x111E0 ; Unknown
    0x111E1,  # .. 0x111F4 ; Sinhala
    0x111F5,  # .. 0x111FF ; Unknown
    0x11200,  # .. 0x11211 ; Khojki
    0x11212,  # .. 0x11212 ; Unknown
    0x11213,  # .. 0x11241 ; Khojki
    0x11242,  # .. 0x1127F ; Unknown
    0x11280,  # .. 0x11286 ; Multani
    0x11287,  # .. 0x11287 ; Unknown
    0x11288,  # .. 0x11288 ; Multani
    0x11289,  # .. 0x11289 ; Unknown
    0x1128A,  # .. 0x1128D ; Multani
    0x1128E,  # .. 0x1128E ; Unknown
    0x1128F,  # .. 0x1129D ; Multani
    0x1129E,  # .. 0x1129E ; Unknown
    0x1129F,  # .. 0x112A9 ; Multani
    0x112AA,  # .. 0x112AF ; Unknown
    0x112B0,  # .. 0x112EA ; Khudawadi
    0x112EB,  # .. 0x112EF ; Unknown
    0x112F0,  # .. 0x112F9 ; Khudawadi
    0x112FA,  # .. 0x112FF ; Unknown
    0x11300,  # .. 0x11303 ; Grantha
    0x11304,  # .. 0x11304 ; Unknown
    0x11305,  # .. 0x1130C ; Grantha
    0x1130D,  # .. 0x1130E ; Unknown
    0x1130F,  # .. 0x11310 ; Grantha
    0x11311,  # .. 0x11312 ; Unknown
    0x11313,  # .. 0x11328 ; Grantha
    0x11329,  # .. 0x11329 ; Unknown
    0x1132A,  # .. 0x11330 ; Grantha
    0x11331,  # .. 0x11331 ; Unknown
    0x11332,  # .. 0x11333 ; Grantha
    0x11334,  # .. 0x11334 ; Unknown
    0x11335,  # .. 0x11339 ; Grantha
    0x1133A,  # .. 0x1133A ; Unknown
    0x1133B,  # .. 0x1133B ; Inherited
    0x1133C,  # .. 0x11344 ; Grantha
    0x11345,  # .. 0x11346 ; Unknown
    0x11347,  # .. 0x11348 ; Grantha
    0x11349,  # .. 0x1134A ; Unknown
    0x1134B,  # .. 0x1134D ; Grantha
    0x1134E,  # .. 0x1134F ; Unknown
    0x11350,  # .. 0x11350 ; Grantha
    0x11351,  # .. 0x11356 ; Unknown
    0x11357,  # .. 0x11357 ; Grantha
    0x11358,  # .. 0x1135C ; Unknown
    0x1135D,  # .. 0x11363 ; Grantha
    0x11364,  # .. 0x11365 ; Unknown
    0x11366,  # .. 0x1136C ; Grantha
    0x1136D,  # .. 0x1136F ; Unknown
    0x11370,  # .. 0x11374 ; Grantha
    0x11375,  # .. 0x1137F ; Unknown
    0x11380,  # .. 0x11389 ; Tulu_Tigalari
    0x1138A,  # .. 0x1138A ; Unknown
    0x1138B,  # .. 0x1138B ; Tulu_Tigalari
    0x1138C,  # .. 0x1138D ; Unknown
    0x1138E,  # .. 0x1138E ; Tulu_Tigalari
    0x1138F,  # .. 0x1138F ; Unknown
    0x11390,  # .. 0x113B5 ; Tulu_Tigalari
    0x113B6,  # .. 0x113B6 ; Unknown
    0x113B7,  # .. 0x113C0 ; Tulu_Tigalari
    0x113C1,  # .. 0x113C1 ; Unknown
    0x113C2,  # .. 0x113C2 ; Tulu_Tigalari
    0x113C3,  # .. 0x113C4 ; Unknown
    0x113C5,  # .. 0x113C5 ; Tulu_Tigalari
    0x113C6,  # .. 0x113C6 ; Unknown
    0x113C7,  # .. 0x113CA ; Tulu_Tigalari
    0x113CB,  # .. 0x113CB ; Unknown
    0x113CC,  # .. 0x113D5 ; Tulu_Tigalari
    0x113D6,  # .. 0x113D6 ; Unknown
    0x113D7,  # .. 0x113D8 ; Tulu_Tigalari
    0x113D9,  # .. 0x113E0 ; Unknown
    0x113E1,  # .. 0x113E2 ; Tulu_Tigalari
    0x113E3,  # .. 0x113FF ; Unknown
    0x11400,  # .. 0x1145B ; Newa
    0x1145C,  # .. 0x1145C ; Unknown
    0x1145D,  # .. 0x11461 ; Newa
    0x11462,  # .. 0x1147F ; Unknown
    0x11480,  # .. 0x114C7 ; Tirhuta
    0x114C8,  # .. 0x114CF ; Unknown
    0x114D0,  # .. 0x114D9 ; Tirhuta
    0x114DA,  # .. 0x1157F ; Unknown
    0x11580,  # .. 0x115B5 ; Siddham
    0x115B6,  # .. 0x115B7 ; Unknown
    0x115B8,  # .. 0x115DD ; Siddham
    0x115DE,  # .. 0x115FF ; Unknown
    0x11600,  # .. 0x11644 ; Modi
    0x11645,  # .. 0x1164F ; Unknown
    0x11650,  # .. 0x11659 ; Modi
    0x1165A,  # .. 0x1165F ; Unknown
    0x11660,  # .. 0x1166C ; Mongolian
    0x1166D,  # .. 0x1167F ; Unknown
    0x11680,  # .. 0x116B9 ; Takri
    0x116BA,  # .. 0x116BF ; Unknown
    0x116C0,  # .. 0x116C9 ; Takri
    0x116CA,  # .. 0x116CF ; Unknown
    0x116D0,  # .. 0x116E3 ; Myanmar
    0x116E4,  # .. 0x116FF ; Unknown
    0x11700,  # .. 0x1171A ; Ahom
    0x1171B,  # .. 0x1171C ; Unknown
    0x1171D,  # .. 0x1172B ; Ahom
    0x1172C,  # .. 0x1172F ; Unknown
    0x11730,  # .. 0x11746 ; Ahom
    0x11747,  # .. 0x117FF ; Unknown
    0x11800,  # .. 0x1183B ; Dogra
    0x1183C,  # .. 0x1189F ; Unknown
    0x118A0,  # .. 0x118F2 ; Warang_Citi
    0x118F3,  # .. 0x118FE ; Unknown
    0x118FF,  # .. 0x118FF ; Warang_Citi
    0x11900,  # .. 0x11906 ; Dives_Akuru
    0x11907,  # .. 0x11908 ; Unknown
    0x11909,  # .. 0x11909 ; Dives_Akuru
    0x1190A,  # .. 0x1190B ; Unknown
    0x1190C,  # .. 0x11913 ; Dives_Akuru
    0x11914,  # .. 0x11914 ; Unknown
    0x11915,  # .. 0x11916 ; Dives_Akuru
    0x11917,  # .. 0x11917 ; Unknown
    0x11918,  # .. 0x11935 ; Dives_Akuru
    0x11936,  # .. 0x11936 ; Unknown
    0x11937,  # .. 0x11938 ; Dives_Akuru
    0x11939,  # .. 0x1193A ; Unknown
    0x1193B,  # .. 0x11946 ; Dives_Akuru
    0x11947,  # .. 0x1194F ; Unknown
    0x11950,  # .. 0x11959 ; Dives_Akuru
    0x1195A,  # .. 0x1199F ; Unknown
    0x119A0,  # .. 0x119A7 ; Nandinagari
    0x119A8,  # .. 0x119A9 ; Unknown
    0x119AA,  # .. 0x119D7 ; Nandinagari
    0x119D8,  # .. 0x119D9 ; Unknown
    0x119DA,  # .. 0x119E4 ; Nandinagari
    0x119E5,  # .. 0x119FF ; Unknown
    0x11A00,  # .. 0x11A47 ; Zanabazar_Square
    0x11A48,  # .. 0x11A4F ; Unknown
    0x11A50,  # .. 0x11AA2 ; Soyombo
    0x11AA3,  # .. 0x11AAF ; Unknown
    0x11AB0,  # .. 0x11ABF ; Canadian_Aboriginal
    0x11AC0,  # .. 0x11AF8 ; Pau_Cin_Hau
    0x11AF9,  # .. 0x11AFF ; Unknown
    0x11B00,  # .. 0x11B09 ; Devanagari
    0x11B0A,  # .. 0x11BBF ; Unknown
    0x11BC0,  # .. 0x11BE1 ; Sunuwar
    0x11BE2,  # .. 0x11BEF ; Unknown
    0x11BF0,  # .. 0x11BF9 ; Sunuwar
    0x11BFA,  # .. 0x11BFF ; Unknown
    0x11C00,  # .. 0x11C08 ; Bhaiksuki
    0x11C09,  # .. 0x11C09 ; Unknown
    0x11C0A,  # .. 0x11C36 ; Bhaiksuki
    0x11C37,  # .. 0x11C37 ; Unknown
    0x11C38,  # .. 0x11C45 ; Bhaiksuki
    0x11C46,  # .. 0x11C4F ; Unknown
    0x11C50,  # .. 0x11C6C ; Bhaiksuki
    0x11C6D,  # .. 0x11C6F ; Unknown
    0x11C70,  # .. 0x11C8F ; Marchen
    0x11C90,  # .. 0x11C91 ; Unknown
    0x11C92,  # .. 0x11CA7 ; Marchen
    0x11CA8,  # .. 0x11CA8 ; Unknown
    0x11CA9,  # .. 0x11CB6 ; Marchen
    0x11CB7,  # .. 0x11CFF ; Unknown
    0x11D00,  # .. 0x11D06 ; Masaram_Gondi
    0x11D07,  # .. 0x11D07 ; Unknown
    0x11D08,  # .. 0x11D09 ; Masaram_Gondi
    0x11D0A,  # .. 0x11D0A ; Unknown
    0x11D0B,  # .. 0x11D36 ; Masaram_Gondi
    0x11D37,  # .. 0x11D39 ; Unknown
    0x11D3A,  # .. 0x11D3A ; Masaram_Gondi
    0x11D3B,  # .. 0x11D3B ; Unknown
    0x11D3C,  # .. 0x11D3D ; Masaram_Gondi
    0x11D3E,  # .. 0x11D3E ; Unknown
    0x11D3F,  # .. 0x11D47 ; Masaram_Gondi
    0x11D48,  # .. 0x11D4F ; Unknown
    0x11D50,  # .. 0x11D59 ; Masaram_Gondi
    0x11D5A,  # .. 0x11D5F ; Unknown
    0x11D60,  # .. 0x11D65 ; Gunjala_Gondi
    0x11D66,  # .. 0x11D66 ; Unknown
    0x11D67,  # .. 0x11D68 ; Gunjala_Gondi
    0x11D69,  # .. 0x11D69 ; Unknown
    0x11D6A,  # .. 0x11D8E ; Gunjala_Gondi
    0x11D8F,  # .. 0x11D8F ; Unknown
    0x11D90,  # .. 0x11D91 ; Gunjala_Gondi
    0x11D92,  # .. 0x11D92 ; Unknown
    0x11D93,  # .. 0x11D98 ; Gunjala_Gondi
    0x11D99,  # .. 0x11D9F ; Unknown
    0x11DA0,  # .. 0x11DA9 ; Gunjala_Gondi
    0x11DAA,  # .. 0x11EDF ; Unknown
    0x11EE0,  # .. 0x11EF8 ; Makasar
    0x11EF9,  # .. 0x11EFF ; Unknown
    0x11F00,  # .. 0x11F10 ; Kawi
    0x11F11,  # .. 0x11F11 ; Unknown
    0x11F12,  # .. 0x11F3A ; Kawi
    0x11F3B,  # .. 0x11F3D ; Unknown
    0x11F3E,  # .. 0x11F5A ; Kawi
    0x11F5B,  # .. 0x11FAF ; Unknown
    0x11FB0,  # .. 0x11FB0 ; Lisu
    0x11FB1,  # .. 0x11FBF ; Unknown
    0x11FC0,  # .. 0x11FF1 ; Tamil
    0x11FF2,  # .. 0x11FFE ; Unknown
    0x11FFF,  # .. 0x11FFF ; Tamil
    0x12000,  # .. 0x12399 ; Cuneiform
    0x1239A,  # .. 0x123FF ; Unknown
    0x12400,  # .. 0x1246E ; Cuneiform
    0x1246F,  # .. 0x1246F ; Unknown
    0x12470,  # .. 0x12474 ; Cuneiform
    0x12475,  # .. 0x1247F ; Unknown
    0x12480,  # .. 0x12543 ; Cuneiform
    0x12544,  # .. 0x12F8F ; Unknown
    0x12F90,  # .. 0x12FF2 ; Cypro_Minoan
    0x12FF3,  # .. 0x12FFF ; Unknown
    0x13000,  # .. 0x13455 ; Egyptian_Hieroglyphs
    0x13456,  # .. 0x1345F ; Unknown
    0x13460,  # .. 0x143FA ; Egyptian_Hieroglyphs
    0x143FB,  # .. 0x143FF ; Unknown
    0x14400,  # .. 0x14646 ; Anatolian_Hieroglyphs
    0x14647,  # .. 0x160FF ; Unknown
    0x16100,  # .. 0x16139 ; Gurung_Khema
    0x1613A,  # .. 0x167FF ; Unknown
    0x16800,  # .. 0x16A38 ; Bamum
    0x16A39,  # .. 0x16A3F ; Unknown
    0x16A40,  # .. 0x16A5E ; Mro
    0x16A5F,  # .. 0x16A5F ; Unknown
    0x16A60,  # .. 0x16A69 ; Mro
    0x16A6A,  # .. 0x16A6D ; Unknown
    0x16A6E,  # .. 0x16A6F ; Mro
    0x16A70,  # .. 0x16ABE ; Tangsa
    0x16ABF,  # .. 0x16ABF ; Unknown
    0x16AC0,  # .. 0x16AC9 ; Tangsa
    0x16ACA,  # .. 0x16ACF ; Unknown
    0x16AD0,  # .. 0x16AED ; Bassa_Vah
    0x16AEE,  # .. 0x16AEF ; Unknown
    0x16AF0,  # .. 0x16AF5 ; Bassa_Vah
    0x16AF6,  # .. 0x16AFF ; Unknown
    0x16B00,  # .. 0x16B45 ; Pahawh_Hmong
    0x16B46,  # .. 0x16B4F ; Unknown
    0x16B50,  # .. 0x16B59 ; Pahawh_Hmong
    0x16B5A,  # .. 0x16B5A ; Unknown
    0x16B5B,  # .. 0x16B61 ; Pahawh_Hmong
    0x16B62,  # .. 0x16B62 ; Unknown
    0x16B63,  # .. 0x16B77 ; Pahawh_Hmong
    0x16B78,  # .. 0x16B7C ; Unknown
    0x16B7D,  # .. 0x16B8F ; Pahawh_Hmong
    0x16B90,  # .. 0x16D3F ; Unknown
    0x16D40,  # .. 0x16D79 ; Kirat_Rai
    0x16D7A,  # .. 0x16E3F ; Unknown
    0x16E40,  # .. 0x16E9A ; Medefaidrin
    0x16E9B,  # .. 0x16EFF ; Unknown
    0x16F00,  # .. 0x16F4A ; Miao
    0x16F4B,  # .. 0x16F4E ; Unknown
    0x16F4F,  # .. 0x16F87 ; Miao
    0x16F88,  # .. 0x16F8E ; Unknown
    0x16F8F,  # .. 0x16F9F ; Miao
    0x16FA0,  # .. 0x16FDF ; Unknown
    0x16FE0,  # .. 0x16FE0 ; Tangut
    0x16FE1,  # .. 0x16FE1 ; Nushu
    0x16FE2,  # .. 0x16FE3 ; Han
    0x16FE4,  # .. 0x16FE4 ; Khitan_Small_Script
    0x16FE5,  # .. 0x16FEF ; Unknown
    0x16FF0,  # .. 0x16FF1 ; Han
    0x16FF2,  # .. 0x16FFF ; Unknown
    0x17000,  # .. 0x187F7 ; Tangut
    0x187F8,  # .. 0x187FF ; Unknown
    0x18800,  # .. 0x18AFF ; Tangut
    0x18B00,  # .. 0x18CD5 ; Khitan_Small_Script
    0x18CD6,  # .. 0x18CFE ; Unknown
    0x18CFF,  # .. 0x18CFF ; Khitan_Small_Script
    0x18D00,  # .. 0x18D08 ; Tangut
    0x18D09,  # .. 0x1AFEF ; Unknown
    0x1AFF0,  # .. 0x1AFF3 ; Katakana
    0x1AFF4,  # .. 0x1AFF4 ; Unknown
    0x1AFF5,  # .. 0x1AFFB ; Katakana
    0x1AFFC,  # .. 0x1AFFC ; Unknown
    0x1AFFD,  # .. 0x1AFFE ; Katakana
    0x1AFFF,  # .. 0x1AFFF ; Unknown
    0x1B000,  # .. 0x1B000 ; Katakana
    0x1B001,  # .. 0x1B11F ; Hiragana
    0x1B120,  # .. 0x1B122 ; Katakana
    0x1B123,  # .. 0x1B131 ; Unknown
    0x1B132,  # .. 0x1B132 ; Hiragana
    0x1B133,  # .. 0x1B14F ; Unknown
    0x1B150,  # .. 0x1B152 ; Hiragana
    0x1B153,  # .. 0x1B154 ; Unknown
    0x1B155,  # .. 0x1B155 ; Katakana
    0x1B156,  # .. 0x1B163 ; Unknown
    0x1B164,  # .. 0x1B167 ; Katakana
    0x1B168,  # .. 0x1B16F ; Unknown
    0x1B170,  # .. 0x1B2FB ; Nushu
    0x1B2FC,  # .. 0x1BBFF ; Unknown
    0x1BC00,  # .. 0x1BC6A ; Duployan
    0x1BC6B,  # .. 0x1BC6F ; Unknown
    0x1BC70,  # .. 0x1BC7C ; Duployan
    0x1BC7D,  # .. 0x1BC7F ; Unknown
    0x1BC80,  # .. 0x1BC88 ; Duployan
    0x1BC89,  # .. 0x1BC8F ; Unknown
    0x1BC90,  # .. 0x1BC99 ; Duployan
    0x1BC9A,  # .. 0x1BC9B ; Unknown
    0x1BC9C,  # .. 0x1BC9F ; Duployan
    0x1BCA0,  # .. 0x1BCA3 ; Common
    0x1BCA4,  # .. 0x1CBFF ; Unknown
    0x1CC00,  # .. 0x1CCF9 ; Common
    0x1CCFA,  # .. 0x1CCFF ; Unknown
    0x1CD00,  # .. 0x1CEB3 ; Common
    0x1CEB4,  # .. 0x1CEFF ; Unknown
    0x1CF00,  # .. 0x1CF2D ; Inherited
    0x1CF2E,  # .. 0x1CF2F ; Unknown
    0x1CF30,  # .. 0x1CF46 ; Inherited
    0x1CF47,  # .. 0x1CF4F ; Unknown
    0x1CF50,  # .. 0x1CFC3 ; Common
    0x1CFC4,  # .. 0x1CFFF ; Unknown
    0x1D000,  # .. 0x1D0F5 ; Common
    0x1D0F6,  # .. 0x1D0FF ; Unknown
    0x1D100,  # .. 0x1D126 ; Common
    0x1D127,  # .. 0x1D128 ; Unknown
    0x1D129,  # .. 0x1D166 ; Common
    0x1D167,  # .. 0x1D169 ; Inherited
    0x1D16A,  # .. 0x1D17A ; Common
    0x1D17B,  # .. 0x1D182 ; Inherited
    0x1D183,  # .. 0x1D184 ; Common
    0x1D185,  # .. 0x1D18B ; Inherited
    0x1D18C,  # .. 0x1D1A9 ; Common
    0x1D1AA,  # .. 0x1D1AD ; Inherited
    0x1D1AE,  # .. 0x1D1EA ; Common
    0x1D1EB,  # .. 0x1D1FF ; Unknown
    0x1D200,  # .. 0x1D245 ; Greek
    0x1D246,  # .. 0x1D2BF ; Unknown
    0x1D2C0,  # .. 0x1D2D3 ; Common
    0x1D2D4,  # .. 0x1D2DF ; Unknown
    0x1D2E0,  # .. 0x1D2F3 ; Common
    0x1D2F4,  # .. 0x1D2FF ; Unknown
    0x1D300,  # .. 0x1D356 ; Common
    0x1D357,  # .. 0x1D35F ; Unknown
    0x1D360,  # .. 0x1D378 ; Common
    0x1D379,  # .. 0x1D3FF ; Unknown
    0x1D400,  # .. 0x1D454 ; Common
    0x1D455,  # .. 0x1D455 ; Unknown
    0x1D456,  # .. 0x1D49C ; Common
    0x1D49D,  # .. 0x1D49D ; Unknown
    0x1D49E,  # .. 0x1D49F ; Common
    0x1D4A0,  # .. 0x1D4A1 ; Unknown
    0x1D4A2,  # .. 0x1D4A2 ; Common
    0x1D4A3,  # .. 0x1D4A4 ; Unknown
    0x1D4A5,  # .. 0x1D4A6 ; Common
    0x1D4A7,  # .. 0x1D4A8 ; Unknown
    0x1D4A9,  # .. 0x1D4AC ; Common
    0x1D4AD,  # .. 0x1D4AD ; Unknown
    0x1D4AE,  # .. 0x1D4B9 ; Common
    0x1D4BA,  # .. 0x1D4BA ; Unknown
    0x1D4BB,  # .. 0x1D4BB ; Common
    0x1D4BC,  # .. 0x1D4BC ; Unknown
    0x1D4BD,  # .. 0x1D4C3 ; Common
    0x1D4C4,  # .. 0x1D4C4 ; Unknown
    0x1D4C5,  # .. 0x1D505 ; Common
    0x1D506,  # .. 0x1D506 ; Unknown
    0x1D507,  # .. 0x1D50A ; Common
    0x1D50B,  # .. 0x1D50C ; Unknown
    0x1D50D,  # .. 0x1D514 ; Common
    0x1D515,  # .. 0x1D515 ; Unknown
    0x1D516,  # .. 0x1D51C ; Common
    0x1D51D,  # .. 0x1D51D ; Unknown
    0x1D51E,  # .. 0x1D539 ; Common
    0x1D53A,  # .. 0x1D53A ; Unknown
    0x1D53B,  # .. 0x1D53E ; Common
    0x1D53F,  # .. 0x1D53F ; Unknown
    0x1D540,  # .. 0x1D544 ; Common
    0x1D545,  # .. 0x1D545 ; Unknown
    0x1D546,  # .. 0x1D546 ; Common
    0x1D547,  # .. 0x1D549 ; Unknown
    0x1D54A,  # .. 0x1D550 ; Common
    0x1D551,  # .. 0x1D551 ; Unknown
    0x1D552,  # .. 0x1D6A5 ; Common
    0x1D6A6,  # .. 0x1D6A7 ; Unknown
    0x1D6A8,  # .. 0x1D7CB ; Common
    0x1D7CC,  # .. 0x1D7CD ; Unknown
    0x1D7CE,  # .. 0x1D7FF ; Common
    0x1D800,  # .. 0x1DA8B ; SignWriting
    0x1DA8C,  # .. 0x1DA9A ; Unknown
    0x1DA9B,  # .. 0x1DA9F ; SignWriting
    0x1DAA0,  # .. 0x1DAA0 ; Unknown
    0x1DAA1,  # .. 0x1DAAF ; SignWriting
    0x1DAB0,  # .. 0x1DEFF ; Unknown
    0x1DF00,  # .. 0x1DF1E ; Latin
    0x1DF1F,  # .. 0x1DF24 ; Unknown
    0x1DF25,  # .. 0x1DF2A ; Latin
    0x1DF2B,  # .. 0x1DFFF ; Unknown
    0x1E000,  # .. 0x1E006 ; Glagolitic
    0x1E007,  # .. 0x1E007 ; Unknown
    0x1E008,  # .. 0x1E018 ; Glagolitic
    0x1E019,  # .. 0x1E01A ; Unknown
    0x1E01B,  # .. 0x1E021 ; Glagolitic
    0x1E022,  # .. 0x1E022 ; Unknown
    0x1E023,  # .. 0x1E024 ; Glagolitic
    0x1E025,  # .. 0x1E025 ; Unknown
    0x1E026,  # .. 0x1E02A ; Glagolitic
    0x1E02B,  # .. 0x1E02F ; Unknown
    0x1E030,  # .. 0x1E06D ; Cyrillic
    0x1E06E,  # .. 0x1E08E ; Unknown
    0x1E08F,  # .. 0x1E08F ; Cyrillic
    0x1E090,  # .. 0x1E0FF ; Unknown
    0x1E100,  # .. 0x1E12C ; Nyiakeng_Puachue_Hmong
    0x1E12D,  # .. 0x1E12F ; Unknown
    0x1E130,  # .. 0x1E13D ; Nyiakeng_Puachue_Hmong
    0x1E13E,  # .. 0x1E13F ; Unknown
    0x1E140,  # .. 0x1E149 ; Nyiakeng_Puachue_Hmong
    0x1E14A,  # .. 0x1E14D ; Unknown
    0x1E14E,  # .. 0x1E14F ; Nyiakeng_Puachue_Hmong
    0x1E150,  # .. 0x1E28F ; Unknown
    0x1E290,  # .. 0x1E2AE ; Toto
    0x1E2AF,  # .. 0x1E2BF ; Unknown
    0x1E2C0,  # .. 0x1E2F9 ; Wancho
    0x1E2FA,  # .. 0x1E2FE ; Unknown
    0x1E2FF,  # .. 0x1E2FF ; Wancho
    0x1E300,  # .. 0x1E4CF ; Unknown
    0x1E4D0,  # .. 0x1E4F9 ; Nag_Mundari
    0x1E4FA,  # .. 0x1E5CF ; Unknown
    0x1E5D0,  # .. 0x1E5FA ; Ol_Onal
    0x1E5FB,  # .. 0x1E5FE ; Unknown
    0x1E5FF,  # .. 0x1E5FF ; Ol_Onal
    0x1E600,  # .. 0x1E7DF ; Unknown
    0x1E7E0,  # .. 0x1E7E6 ; Ethiopic
    0x1E7E7,  # .. 0x1E7E7 ; Unknown
    0x1E7E8,  # .. 0x1E7EB ; Ethiopic
    0x1E7EC,  # .. 0x1E7EC ; Unknown
    0x1E7ED,  # .. 0x1E7EE ; Ethiopic
    0x1E7EF,  # .. 0x1E7EF ; Unknown
    0x1E7F0,  # .. 0x1E7FE ; Ethiopic
    0x1E7FF,  # .. 0x1E7FF ; Unknown
    0x1E800,  # .. 0x1E8C4 ; Mende_Kikakui
    0x1E8C5,  # .. 0x1E8C6 ; Unknown
    0x1E8C7,  # .. 0x1E8D6 ; Mende_Kikakui
    0x1E8D7,  # .. 0x1E8FF ; Unknown
    0x1E900,  # .. 0x1E94B ; Adlam
    0x1E94C,  # .. 0x1E94F ; Unknown
    0x1E950,  # .. 0x1E959 ; Adlam
    0x1E95A,  # .. 0x1E95D ; Unknown
    0x1E95E,  # .. 0x1E95F ; Adlam
    0x1E960,  # .. 0x1EC70 ; Unknown
    0x1EC71,  # .. 0x1ECB4 ; Common
    0x1ECB5,  # .. 0x1ED00 ; Unknown
    0x1ED01,  # .. 0x1ED3D ; Common
    0x1ED3E,  # .. 0x1EDFF ; Unknown
    0x1EE00,  # .. 0x1EE03 ; Arabic
    0x1EE04,  # .. 0x1EE04 ; Unknown
    0x1EE05,  # .. 0x1EE1F ; Arabic
    0x1EE20,  # .. 0x1EE20 ; Unknown
    0x1EE21,  # .. 0x1EE22 ; Arabic
    0x1EE23,  # .. 0x1EE23 ; Unknown
    0x1EE24,  # .. 0x1EE24 ; Arabic
    0x1EE25,  # .. 0x1EE26 ; Unknown
    0x1EE27,  # .. 0x1EE27 ; Arabic
    0x1EE28,  # .. 0x1EE28 ; Unknown
    0x1EE29,  # .. 0x1EE32 ; Arabic
    0x1EE33,  # .. 0x1EE33 ; Unknown
    0x1EE34,  # .. 0x1EE37 ; Arabic
    0x1EE38,  # .. 0x1EE38 ; Unknown
    0x1EE39,  # .. 0x1EE39 ; Arabic
    0x1EE3A,  # .. 0x1EE3A ; Unknown
    0x1EE3B,  # .. 0x1EE3B ; Arabic
    0x1EE3C,  # .. 0x1EE41 ; Unknown
    0x1EE42,  # .. 0x1EE42 ; Arabic
    0x1EE43,  # .. 0x1EE46 ; Unknown
    0x1EE47,  # .. 0x1EE47 ; Arabic
    0x1EE48,  # .. 0x1EE48 ; Unknown
    0x1EE49,  # .. 0x1EE49 ; Arabic
    0x1EE4A,  # .. 0x1EE4A ; Unknown
    0x1EE4B,  # .. 0x1EE4B ; Arabic
    0x1EE4C,  # .. 0x1EE4C ; Unknown
    0x1EE4D,  # .. 0x1EE4F ; Arabic
    0x1EE50,  # .. 0x1EE50 ; Unknown
    0x1EE51,  # .. 0x1EE52 ; Arabic
    0x1EE53,  # .. 0x1EE53 ; Unknown
    0x1EE54,  # .. 0x1EE54 ; Arabic
    0x1EE55,  # .. 0x1EE56 ; Unknown
    0x1EE57,  # .. 0x1EE57 ; Arabic
    0x1EE58,  # .. 0x1EE58 ; Unknown
    0x1EE59,  # .. 0x1EE59 ; Arabic
    0x1EE5A,  # .. 0x1EE5A ; Unknown
    0x1EE5B,  # .. 0x1EE5B ; Arabic
    0x1EE5C,  # .. 0x1EE5C ; Unknown
    0x1EE5D,  # .. 0x1EE5D ; Arabic
    0x1EE5E,  # .. 0x1EE5E ; Unknown
    0x1EE5F,  # .. 0x1EE5F ; Arabic
    0x1EE60,  # .. 0x1EE60 ; Unknown
    0x1EE61,  # .. 0x1EE62 ; Arabic
    0x1EE63,  # .. 0x1EE63 ; Unknown
    0x1EE64,  # .. 0x1EE64 ; Arabic
    0x1EE65,  # .. 0x1EE66 ; Unknown
    0x1EE67,  # .. 0x1EE6A ; Arabic
    0x1EE6B,  # .. 0x1EE6B ; Unknown
    0x1EE6C,  # .. 0x1EE72 ; Arabic
    0x1EE73,  # .. 0x1EE73 ; Unknown
    0x1EE74,  # .. 0x1EE77 ; Arabic
    0x1EE78,  # .. 0x1EE78 ; Unknown
    0x1EE79,  # .. 0x1EE7C ; Arabic
    0x1EE7D,  # .. 0x1EE7D ; Unknown
    0x1EE7E,  # .. 0x1EE7E ; Arabic
    0x1EE7F,  # .. 0x1EE7F ; Unknown
    0x1EE80,  # .. 0x1EE89 ; Arabic
    0x1EE8A,  # .. 0x1EE8A ; Unknown
    0x1EE8B,  # .. 0x1EE9B ; Arabic
    0x1EE9C,  # .. 0x1EEA0 ; Unknown
    0x1EEA1,  # .. 0x1EEA3 ; Arabic
    0x1EEA4,  # .. 0x1EEA4 ; Unknown
    0x1EEA5,  # .. 0x1EEA9 ; Arabic
    0x1EEAA,  # .. 0x1EEAA ; Unknown
    0x1EEAB,  # .. 0x1EEBB ; Arabic
    0x1EEBC,  # .. 0x1EEEF ; Unknown
    0x1EEF0,  # .. 0x1EEF1 ; Arabic
    0x1EEF2,  # .. 0x1EFFF ; Unknown
    0x1F000,  # .. 0x1F02B ; Common
    0x1F02C,  # .. 0x1F02F ; Unknown
    0x1F030,  # .. 0x1F093 ; Common
    0x1F094,  # .. 0x1F09F ; Unknown
    0x1F0A0,  # .. 0x1F0AE ; Common
    0x1F0AF,  # .. 0x1F0B0 ; Unknown
    0x1F0B1,  # .. 0x1F0BF ; Common
    0x1F0C0,  # .. 0x1F0C0 ; Unknown
    0x1F0C1,  # .. 0x1F0CF ; Common
    0x1F0D0,  # .. 0x1F0D0 ; Unknown
    0x1F0D1,  # .. 0x1F0F5 ; Common
    0x1F0F6,  # .. 0x1F0FF ; Unknown
    0x1F100,  # .. 0x1F1AD ; Common
    0x1F1AE,  # .. 0x1F1E5 ; Unknown
    0x1F1E6,  # .. 0x1F1FF ; Common
    0x1F200,  # .. 0x1F200 ; Hiragana
    0x1F201,  # .. 0x1F202 ; Common
    0x1F203,  # .. 0x1F20F ; Unknown
    0x1F210,  # .. 0x1F23B ; Common
    0x1F23C,  # .. 0x1F23F ; Unknown
    0x1F240,  # .. 0x1F248 ; Common
    0x1F249,  # .. 0x1F24F ; Unknown
    0x1F250,  # .. 0x1F251 ; Common
    0x1F252,  # .. 0x1F25F ; Unknown
    0x1F260,  # .. 0x1F265 ; Common
    0x1F266,  # .. 0x1F2FF ; Unknown
    0x1F300,  # .. 0x1F6D7 ; Common
    0x1F6D8,  # .. 0x1F6DB ; Unknown
    0x1F6DC,  # .. 0x1F6EC ; Common
    0x1F6ED,  # .. 0x1F6EF ; Unknown
    0x1F6F0,  # .. 0x1F6FC ; Common
    0x1F6FD,  # .. 0x1F6FF ; Unknown
    0x1F700,  # .. 0x1F776 ; Common
    0x1F777,  # .. 0x1F77A ; Unknown
    0x1F77B,  # .. 0x1F7D9 ; Common
    0x1F7DA,  # .. 0x1F7DF ; Unknown
    0x1F7E0,  # .. 0x1F7EB ; Common
    0x1F7EC,  # .. 0x1F7EF ; Unknown
    0x1F7F0,  # .. 0x1F7F0 ; Common
    0x1F7F1,  # .. 0x1F7FF ; Unknown
    0x1F800,  # .. 0x1F80B ; Common
    0x1F80C,  # .. 0x1F80F ; Unknown
    0x1F810,  # .. 0x1F847 ; Common
    0x1F848,  # .. 0x1F84F ; Unknown
    0x1F850,  # .. 0x1F859 ; Common
    0x1F85A,  # .. 0x1F85F ; Unknown
    0x1F860,  # .. 0x1F887 ; Common
    0x1F888,  # .. 0x1F88F ; Unknown
    0x1F890,  # .. 0x1F8AD ; Common
    0x1F8AE,  # .. 0x1F8AF ; Unknown
    0x1F8B0,  # .. 0x1F8BB ; Common
    0x1F8BC,  # .. 0x1F8BF ; Unknown
    0x1F8C0,  # .. 0x1F8C1 ; Common
    0x1F8C2,  # .. 0x1F8FF ; Unknown
    0x1F900,  # .. 0x1FA53 ; Common
    0x1FA54,  # .. 0x1FA5F ; Unknown
    0x1FA60,  # .. 0x1FA6D ; Common
    0x1FA6E,  # .. 0x1FA6F ; Unknown
    0x1FA70,  # .. 0x1FA7C ; Common
    0x1FA7D,  # .. 0x1FA7F ; Unknown
    0x1FA80,  # .. 0x1FA89 ; Common
    0x1FA8A,  # .. 0x1FA8E ; Unknown
    0x1FA8F,  # .. 0x1FAC6 ; Common
    0x1FAC7,  # .. 0x1FACD ; Unknown
    0x1FACE,  # .. 0x1FADC ; Common
    0x1FADD,  # .. 0x1FADE ; Unknown
    0x1FADF,  # .. 0x1FAE9 ; Common
    0x1FAEA,  # .. 0x1FAEF ; Unknown
    0x1FAF0,  # .. 0x1FAF8 ; Common
    0x1FAF9,  # .. 0x1FAFF ; Unknown
    0x1FB00,  # .. 0x1FB92 ; Common
    0x1FB93,  # .. 0x1FB93 ; Unknown
    0x1FB94,  # .. 0x1FBF9 ; Common
    0x1FBFA,  # .. 0x1FFFF ; Unknown
    0x20000,  # .. 0x2A6DF ; Han
    0x2A6E0,  # .. 0x2A6FF ; Unknown
    0x2A700,  # .. 0x2B739 ; Han
    0x2B73A,  # .. 0x2B73F ; Unknown
    0x2B740,  # .. 0x2B81D ; Han
    0x2B81E,  # .. 0x2B81F ; Unknown
    0x2B820,  # .. 0x2CEA1 ; Han
    0x2CEA2,  # .. 0x2CEAF ; Unknown
    0x2CEB0,  # .. 0x2EBE0 ; Han
    0x2EBE1,  # .. 0x2EBEF ; Unknown
    0x2EBF0,  # .. 0x2EE5D ; Han
    0x2EE5E,  # .. 0x2F7FF ; Unknown
    0x2F800,  # .. 0x2FA1D ; Han
    0x2FA1E,  # .. 0x2FFFF ; Unknown
    0x30000,  # .. 0x3134A ; Han
    0x3134B,  # .. 0x3134F ; Unknown
    0x31350,  # .. 0x323AF ; Han
    0x323B0,  # .. 0xE0000 ; Unknown
    0xE0001,  # .. 0xE0001 ; Common
    0xE0002,  # .. 0xE001F ; Unknown
    0xE0020,  # .. 0xE007F ; Common
    0xE0080,  # .. 0xE00FF ; Unknown
    0xE0100,  # .. 0xE01EF ; Inherited
    0xE01F0,  # .. 0x10FFFF ; Unknown
]

VALUES = [
    "Zyyy",  # 0000..0040 ; Common
    "Latn",  # 0041..005A ; Latin
    "Zyyy",  # 005B..0060 ; Common
    "Latn",  # 0061..007A ; Latin
    "Zyyy",  # 007B..00A9 ; Common
    "Latn",  # 00AA..00AA ; Latin
    "Zyyy",  # 00AB..00B9 ; Common
    "Latn",  # 00BA..00BA ; Latin
    "Zyyy",  # 00BB..00BF ; Common
    "Latn",  # 00C0..00D6 ; Latin
    "Zyyy",  # 00D7..00D7 ; Common
    "Latn",  # 00D8..00F6 ; Latin
    "Zyyy",  # 00F7..00F7 ; Common
    "Latn",  # 00F8..02B8 ; Latin
    "Zyyy",  # 02B9..02DF ; Common
    "Latn",  # 02E0..02E4 ; Latin
    "Zyyy",  # 02E5..02E9 ; Common
    "Bopo",  # 02EA..02EB ; Bopomofo
    "Zyyy",  # 02EC..02FF ; Common
    "Zinh",  # 0300..036F ; Inherited
    "Grek",  # 0370..0373 ; Greek
    "Zyyy",  # 0374..0374 ; Common
    "Grek",  # 0375..0377 ; Greek
    "Zzzz",  # 0378..0379 ; Unknown
    "Grek",  # 037A..037D ; Greek
    "Zyyy",  # 037E..037E ; Common
    "Grek",  # 037F..037F ; Greek
    "Zzzz",  # 0380..0383 ; Unknown
    "Grek",  # 0384..0384 ; Greek
    "Zyyy",  # 0385..0385 ; Common
    "Grek",  # 0386..0386 ; Greek
    "Zyyy",  # 0387..0387 ; Common
    "Grek",  # 0388..038A ; Greek
    "Zzzz",  # 038B..038B ; Unknown
    "Grek",  # 038C..038C ; Greek
    "Zzzz",  # 038D..038D ; Unknown
    "Grek",  # 038E..03A1 ; Greek
    "Zzzz",  # 03A2..03A2 ; Unknown
    "Grek",  # 03A3..03E1 ; Greek
    "Copt",  # 03E2..03EF ; Coptic
    "Grek",  # 03F0..03FF ; Greek
    "Cyrl",  # 0400..0484 ; Cyrillic
    "Zinh",  # 0485..0486 ; Inherited
    "Cyrl",  # 0487..052F ; Cyrillic
    "Zzzz",  # 0530..0530 ; Unknown
    "Armn",  # 0531..0556 ; Armenian
    "Zzzz",  # 0557..0558 ; Unknown
    "Armn",  # 0559..058A ; Armenian
    "Zzzz",  # 058B..058C ; Unknown
    "Armn",  # 058D..058F ; Armenian
    "Zzzz",  # 0590..0590 ; Unknown
    "Hebr",  # 0591..05C7 ; Hebrew
    "Zzzz",  # 05C8..05CF ; Unknown
    "Hebr",  # 05D0..05EA ; Hebrew
    "Zzzz",  # 05EB..05EE ; Unknown
    "Hebr",  # 05EF..05F4 ; Hebrew
    "Zzzz",  # 05F5..05FF ; Unknown
    "Arab",  # 0600..0604 ; Arabic
    "Zyyy",  # 0605..0605 ; Common
    "Arab",  # 0606..060B ; Arabic
    "Zyyy",  # 060C..060C ; Common
    "Arab",  # 060D..061A ; Arabic
    "Zyyy",  # 061B..061B ; Common
    "Arab",  # 061C..061E ; Arabic
    "Zyyy",  # 061F..061F ; Common
    "Arab",  # 0620..063F ; Arabic
    "Zyyy",  # 0640..0640 ; Common
    "Arab",  # 0641..064A ; Arabic
    "Zinh",  # 064B..0655 ; Inherited
    "Arab",  # 0656..066F ; Arabic
    "Zinh",  # 0670..0670 ; Inherited
    "Arab",  # 0671..06DC ; Arabic
    "Zyyy",  # 06DD..06DD ; Common
    "Arab",  # 06DE..06FF ; Arabic
    "Syrc",  # 0700..070D ; Syriac
    "Zzzz",  # 070E..070E ; Unknown
    "Syrc",  # 070F..074A ; Syriac
    "Zzzz",  # 074B..074C ; Unknown
    "Syrc",  # 074D..074F ; Syriac
    "Arab",  # 0750..077F ; Arabic
    "Thaa",  # 0780..07B1 ; Thaana
    "Zzzz",  # 07B2..07BF ; Unknown
    "Nkoo",  # 07C0..07FA ; Nko
    "Zzzz",  # 07FB..07FC ; Unknown
    "Nkoo",  # 07FD..07FF ; Nko
    "Samr",  # 0800..082D ; Samaritan
    "Zzzz",  # 082E..082F ; Unknown
    "Samr",  # 0830..083E ; Samaritan
    "Zzzz",  # 083F..083F ; Unknown
    "Mand",  # 0840..085B ; Mandaic
    "Zzzz",  # 085C..085D ; Unknown
    "Mand",  # 085E..085E ; Mandaic
    "Zzzz",  # 085F..085F ; Unknown
    "Syrc",  # 0860..086A ; Syriac
    "Zzzz",  # 086B..086F ; Unknown
    "Arab",  # 0870..088E ; Arabic
    "Zzzz",  # 088F..088F ; Unknown
    "Arab",  # 0890..0891 ; Arabic
    "Zzzz",  # 0892..0896 ; Unknown
    "Arab",  # 0897..08E1 ; Arabic
    "Zyyy",  # 08E2..08E2 ; Common
    "Arab",  # 08E3..08FF ; Arabic
    "Deva",  # 0900..0950 ; Devanagari
    "Zinh",  # 0951..0954 ; Inherited
    "Deva",  # 0955..0963 ; Devanagari
    "Zyyy",  # 0964..0965 ; Common
    "Deva",  # 0966..097F ; Devanagari
    "Beng",  # 0980..0983 ; Bengali
    "Zzzz",  # 0984..0984 ; Unknown
    "Beng",  # 0985..098C ; Bengali
    "Zzzz",  # 098D..098E ; Unknown
    "Beng",  # 098F..0990 ; Bengali
    "Zzzz",  # 0991..0992 ; Unknown
    "Beng",  # 0993..09A8 ; Bengali
    "Zzzz",  # 09A9..09A9 ; Unknown
    "Beng",  # 09AA..09B0 ; Bengali
    "Zzzz",  # 09B1..09B1 ; Unknown
    "Beng",  # 09B2..09B2 ; Bengali
    "Zzzz",  # 09B3..09B5 ; Unknown
    "Beng",  # 09B6..09B9 ; Bengali
    "Zzzz",  # 09BA..09BB ; Unknown
    "Beng",  # 09BC..09C4 ; Bengali
    "Zzzz",  # 09C5..09C6 ; Unknown
    "Beng",  # 09C7..09C8 ; Bengali
    "Zzzz",  # 09C9..09CA ; Unknown
    "Beng",  # 09CB..09CE ; Bengali
    "Zzzz",  # 09CF..09D6 ; Unknown
    "Beng",  # 09D7..09D7 ; Bengali
    "Zzzz",  # 09D8..09DB ; Unknown
    "Beng",  # 09DC..09DD ; Bengali
    "Zzzz",  # 09DE..09DE ; Unknown
    "Beng",  # 09DF..09E3 ; Bengali
    "Zzzz",  # 09E4..09E5 ; Unknown
    "Beng",  # 09E6..09FE ; Bengali
    "Zzzz",  # 09FF..0A00 ; Unknown
    "Guru",  # 0A01..0A03 ; Gurmukhi
    "Zzzz",  # 0A04..0A04 ; Unknown
    "Guru",  # 0A05..0A0A ; Gurmukhi
    "Zzzz",  # 0A0B..0A0E ; Unknown
    "Guru",  # 0A0F..0A10 ; Gurmukhi
    "Zzzz",  # 0A11..0A12 ; Unknown
    "Guru",  # 0A13..0A28 ; Gurmukhi
    "Zzzz",  # 0A29..0A29 ; Unknown
    "Guru",  # 0A2A..0A30 ; Gurmukhi
    "Zzzz",  # 0A31..0A31 ; Unknown
    "Guru",  # 0A32..0A33 ; Gurmukhi
    "Zzzz",  # 0A34..0A34 ; Unknown
    "Guru",  # 0A35..0A36 ; Gurmukhi
    "Zzzz",  # 0A37..0A37 ; Unknown
    "Guru",  # 0A38..0A39 ; Gurmukhi
    "Zzzz",  # 0A3A..0A3B ; Unknown
    "Guru",  # 0A3C..0A3C ; Gurmukhi
    "Zzzz",  # 0A3D..0A3D ; Unknown
    "Guru",  # 0A3E..0A42 ; Gurmukhi
    "Zzzz",  # 0A43..0A46 ; Unknown
    "Guru",  # 0A47..0A48 ; Gurmukhi
    "Zzzz",  # 0A49..0A4A ; Unknown
    "Guru",  # 0A4B..0A4D ; Gurmukhi
    "Zzzz",  # 0A4E..0A50 ; Unknown
    "Guru",  # 0A51..0A51 ; Gurmukhi
    "Zzzz",  # 0A52..0A58 ; Unknown
    "Guru",  # 0A59..0A5C ; Gurmukhi
    "Zzzz",  # 0A5D..0A5D ; Unknown
    "Guru",  # 0A5E..0A5E ; Gurmukhi
    "Zzzz",  # 0A5F..0A65 ; Unknown
    "Guru",  # 0A66..0A76 ; Gurmukhi
    "Zzzz",  # 0A77..0A80 ; Unknown
    "Gujr",  # 0A81..0A83 ; Gujarati
    "Zzzz",  # 0A84..0A84 ; Unknown
    "Gujr",  # 0A85..0A8D ; Gujarati
    "Zzzz",  # 0A8E..0A8E ; Unknown
    "Gujr",  # 0A8F..0A91 ; Gujarati
    "Zzzz",  # 0A92..0A92 ; Unknown
    "Gujr",  # 0A93..0AA8 ; Gujarati
    "Zzzz",  # 0AA9..0AA9 ; Unknown
    "Gujr",  # 0AAA..0AB0 ; Gujarati
    "Zzzz",  # 0AB1..0AB1 ; Unknown
    "Gujr",  # 0AB2..0AB3 ; Gujarati
    "Zzzz",  # 0AB4..0AB4 ; Unknown
    "Gujr",  # 0AB5..0AB9 ; Gujarati
    "Zzzz",  # 0ABA..0ABB ; Unknown
    "Gujr",  # 0ABC..0AC5 ; Gujarati
    "Zzzz",  # 0AC6..0AC6 ; Unknown
    "Gujr",  # 0AC7..0AC9 ; Gujarati
    "Zzzz",  # 0ACA..0ACA ; Unknown
    "Gujr",  # 0ACB..0ACD ; Gujarati
    "Zzzz",  # 0ACE..0ACF ; Unknown
    "Gujr",  # 0AD0..0AD0 ; Gujarati
    "Zzzz",  # 0AD1..0ADF ; Unknown
    "Gujr",  # 0AE0..0AE3 ; Gujarati
    "Zzzz",  # 0AE4..0AE5 ; Unknown
    "Gujr",  # 0AE6..0AF1 ; Gujarati
    "Zzzz",  # 0AF2..0AF8 ; Unknown
    "Gujr",  # 0AF9..0AFF ; Gujarati
    "Zzzz",  # 0B00..0B00 ; Unknown
    "Orya",  # 0B01..0B03 ; Oriya
    "Zzzz",  # 0B04..0B04 ; Unknown
    "Orya",  # 0B05..0B0C ; Oriya
    "Zzzz",  # 0B0D..0B0E ; Unknown
    "Orya",  # 0B0F..0B10 ; Oriya
    "Zzzz",  # 0B11..0B12 ; Unknown
    "Orya",  # 0B13..0B28 ; Oriya
    "Zzzz",  # 0B29..0B29 ; Unknown
    "Orya",  # 0B2A..0B30 ; Oriya
    "Zzzz",  # 0B31..0B31 ; Unknown
    "Orya",  # 0B32..0B33 ; Oriya
    "Zzzz",  # 0B34..0B34 ; Unknown
    "Orya",  # 0B35..0B39 ; Oriya
    "Zzzz",  # 0B3A..0B3B ; Unknown
    "Orya",  # 0B3C..0B44 ; Oriya
    "Zzzz",  # 0B45..0B46 ; Unknown
    "Orya",  # 0B47..0B48 ; Oriya
    "Zzzz",  # 0B49..0B4A ; Unknown
    "Orya",  # 0B4B..0B4D ; Oriya
    "Zzzz",  # 0B4E..0B54 ; Unknown
    "Orya",  # 0B55..0B57 ; Oriya
    "Zzzz",  # 0B58..0B5B ; Unknown
    "Orya",  # 0B5C..0B5D ; Oriya
    "Zzzz",  # 0B5E..0B5E ; Unknown
    "Orya",  # 0B5F..0B63 ; Oriya
    "Zzzz",  # 0B64..0B65 ; Unknown
    "Orya",  # 0B66..0B77 ; Oriya
    "Zzzz",  # 0B78..0B81 ; Unknown
    "Taml",  # 0B82..0B83 ; Tamil
    "Zzzz",  # 0B84..0B84 ; Unknown
    "Taml",  # 0B85..0B8A ; Tamil
    "Zzzz",  # 0B8B..0B8D ; Unknown
    "Taml",  # 0B8E..0B90 ; Tamil
    "Zzzz",  # 0B91..0B91 ; Unknown
    "Taml",  # 0B92..0B95 ; Tamil
    "Zzzz",  # 0B96..0B98 ; Unknown
    "Taml",  # 0B99..0B9A ; Tamil
    "Zzzz",  # 0B9B..0B9B ; Unknown
    "Taml",  # 0B9C..0B9C ; Tamil
    "Zzzz",  # 0B9D..0B9D ; Unknown
    "Taml",  # 0B9E..0B9F ; Tamil
    "Zzzz",  # 0BA0..0BA2 ; Unknown
    "Taml",  # 0BA3..0BA4 ; Tamil
    "Zzzz",  # 0BA5..0BA7 ; Unknown
    "Taml",  # 0BA8..0BAA ; Tamil
    "Zzzz",  # 0BAB..0BAD ; Unknown
    "Taml",  # 0BAE..0BB9 ; Tamil
    "Zzzz",  # 0BBA..0BBD ; Unknown
    "Taml",  # 0BBE..0BC2 ; Tamil
    "Zzzz",  # 0BC3..0BC5 ; Unknown
    "Taml",  # 0BC6..0BC8 ; Tamil
    "Zzzz",  # 0BC9..0BC9 ; Unknown
    "Taml",  # 0BCA..0BCD ; Tamil
    "Zzzz",  # 0BCE..0BCF ; Unknown
    "Taml",  # 0BD0..0BD0 ; Tamil
    "Zzzz",  # 0BD1..0BD6 ; Unknown
    "Taml",  # 0BD7..0BD7 ; Tamil
    "Zzzz",  # 0BD8..0BE5 ; Unknown
    "Taml",  # 0BE6..0BFA ; Tamil
    "Zzzz",  # 0BFB..0BFF ; Unknown
    "Telu",  # 0C00..0C0C ; Telugu
    "Zzzz",  # 0C0D..0C0D ; Unknown
    "Telu",  # 0C0E..0C10 ; Telugu
    "Zzzz",  # 0C11..0C11 ; Unknown
    "Telu",  # 0C12..0C28 ; Telugu
    "Zzzz",  # 0C29..0C29 ; Unknown
    "Telu",  # 0C2A..0C39 ; Telugu
    "Zzzz",  # 0C3A..0C3B ; Unknown
    "Telu",  # 0C3C..0C44 ; Telugu
    "Zzzz",  # 0C45..0C45 ; Unknown
    "Telu",  # 0C46..0C48 ; Telugu
    "Zzzz",  # 0C49..0C49 ; Unknown
    "Telu",  # 0C4A..0C4D ; Telugu
    "Zzzz",  # 0C4E..0C54 ; Unknown
    "Telu",  # 0C55..0C56 ; Telugu
    "Zzzz",  # 0C57..0C57 ; Unknown
    "Telu",  # 0C58..0C5A ; Telugu
    "Zzzz",  # 0C5B..0C5C ; Unknown
    "Telu",  # 0C5D..0C5D ; Telugu
    "Zzzz",  # 0C5E..0C5F ; Unknown
    "Telu",  # 0C60..0C63 ; Telugu
    "Zzzz",  # 0C64..0C65 ; Unknown
    "Telu",  # 0C66..0C6F ; Telugu
    "Zzzz",  # 0C70..0C76 ; Unknown
    "Telu",  # 0C77..0C7F ; Telugu
    "Knda",  # 0C80..0C8C ; Kannada
    "Zzzz",  # 0C8D..0C8D ; Unknown
    "Knda",  # 0C8E..0C90 ; Kannada
    "Zzzz",  # 0C91..0C91 ; Unknown
    "Knda",  # 0C92..0CA8 ; Kannada
    "Zzzz",  # 0CA9..0CA9 ; Unknown
    "Knda",  # 0CAA..0CB3 ; Kannada
    "Zzzz",  # 0CB4..0CB4 ; Unknown
    "Knda",  # 0CB5..0CB9 ; Kannada
    "Zzzz",  # 0CBA..0CBB ; Unknown
    "Knda",  # 0CBC..0CC4 ; Kannada
    "Zzzz",  # 0CC5..0CC5 ; Unknown
    "Knda",  # 0CC6..0CC8 ; Kannada
    "Zzzz",  # 0CC9..0CC9 ; Unknown
    "Knda",  # 0CCA..0CCD ; Kannada
    "Zzzz",  # 0CCE..0CD4 ; Unknown
    "Knda",  # 0CD5..0CD6 ; Kannada
    "Zzzz",  # 0CD7..0CDC ; Unknown
    "Knda",  # 0CDD..0CDE ; Kannada
    "Zzzz",  # 0CDF..0CDF ; Unknown
    "Knda",  # 0CE0..0CE3 ; Kannada
    "Zzzz",  # 0CE4..0CE5 ; Unknown
    "Knda",  # 0CE6..0CEF ; Kannada
    "Zzzz",  # 0CF0..0CF0 ; Unknown
    "Knda",  # 0CF1..0CF3 ; Kannada
    "Zzzz",  # 0CF4..0CFF ; Unknown
    "Mlym",  # 0D00..0D0C ; Malayalam
    "Zzzz",  # 0D0D..0D0D ; Unknown
    "Mlym",  # 0D0E..0D10 ; Malayalam
    "Zzzz",  # 0D11..0D11 ; Unknown
    "Mlym",  # 0D12..0D44 ; Malayalam
    "Zzzz",  # 0D45..0D45 ; Unknown
    "Mlym",  # 0D46..0D48 ; Malayalam
    "Zzzz",  # 0D49..0D49 ; Unknown
    "Mlym",  # 0D4A..0D4F ; Malayalam
    "Zzzz",  # 0D50..0D53 ; Unknown
    "Mlym",  # 0D54..0D63 ; Malayalam
    "Zzzz",  # 0D64..0D65 ; Unknown
    "Mlym",  # 0D66..0D7F ; Malayalam
    "Zzzz",  # 0D80..0D80 ; Unknown
    "Sinh",  # 0D81..0D83 ; Sinhala
    "Zzzz",  # 0D84..0D84 ; Unknown
    "Sinh",  # 0D85..0D96 ; Sinhala
    "Zzzz",  # 0D97..0D99 ; Unknown
    "Sinh",  # 0D9A..0DB1 ; Sinhala
    "Zzzz",  # 0DB2..0DB2 ; Unknown
    "Sinh",  # 0DB3..0DBB ; Sinhala
    "Zzzz",  # 0DBC..0DBC ; Unknown
    "Sinh",  # 0DBD..0DBD ; Sinhala
    "Zzzz",  # 0DBE..0DBF ; Unknown
    "Sinh",  # 0DC0..0DC6 ; Sinhala
    "Zzzz",  # 0DC7..0DC9 ; Unknown
    "Sinh",  # 0DCA..0DCA ; Sinhala
    "Zzzz",  # 0DCB..0DCE ; Unknown
    "Sinh",  # 0DCF..0DD4 ; Sinhala
    "Zzzz",  # 0DD5..0DD5 ; Unknown
    "Sinh",  # 0DD6..0DD6 ; Sinhala
    "Zzzz",  # 0DD7..0DD7 ; Unknown
    "Sinh",  # 0DD8..0DDF ; Sinhala
    "Zzzz",  # 0DE0..0DE5 ; Unknown
    "Sinh",  # 0DE6..0DEF ; Sinhala
    "Zzzz",  # 0DF0..0DF1 ; Unknown
    "Sinh",  # 0DF2..0DF4 ; Sinhala
    "Zzzz",  # 0DF5..0E00 ; Unknown
    "Thai",  # 0E01..0E3A ; Thai
    "Zzzz",  # 0E3B..0E3E ; Unknown
    "Zyyy",  # 0E3F..0E3F ; Common
    "Thai",  # 0E40..0E5B ; Thai
    "Zzzz",  # 0E5C..0E80 ; Unknown
    "Laoo",  # 0E81..0E82 ; Lao
    "Zzzz",  # 0E83..0E83 ; Unknown
    "Laoo",  # 0E84..0E84 ; Lao
    "Zzzz",  # 0E85..0E85 ; Unknown
    "Laoo",  # 0E86..0E8A ; Lao
    "Zzzz",  # 0E8B..0E8B ; Unknown
    "Laoo",  # 0E8C..0EA3 ; Lao
    "Zzzz",  # 0EA4..0EA4 ; Unknown
    "Laoo",  # 0EA5..0EA5 ; Lao
    "Zzzz",  # 0EA6..0EA6 ; Unknown
    "Laoo",  # 0EA7..0EBD ; Lao
    "Zzzz",  # 0EBE..0EBF ; Unknown
    "Laoo",  # 0EC0..0EC4 ; Lao
    "Zzzz",  # 0EC5..0EC5 ; Unknown
    "Laoo",  # 0EC6..0EC6 ; Lao
    "Zzzz",  # 0EC7..0EC7 ; Unknown
    "Laoo",  # 0EC8..0ECE ; Lao
    "Zzzz",  # 0ECF..0ECF ; Unknown
    "Laoo",  # 0ED0..0ED9 ; Lao
    "Zzzz",  # 0EDA..0EDB ; Unknown
    "Laoo",  # 0EDC..0EDF ; Lao
    "Zzzz",  # 0EE0..0EFF ; Unknown
    "Tibt",  # 0F00..0F47 ; Tibetan
    "Zzzz",  # 0F48..0F48 ; Unknown
    "Tibt",  # 0F49..0F6C ; Tibetan
    "Zzzz",  # 0F6D..0F70 ; Unknown
    "Tibt",  # 0F71..0F97 ; Tibetan
    "Zzzz",  # 0F98..0F98 ; Unknown
    "Tibt",  # 0F99..0FBC ; Tibetan
    "Zzzz",  # 0FBD..0FBD ; Unknown
    "Tibt",  # 0FBE..0FCC ; Tibetan
    "Zzzz",  # 0FCD..0FCD ; Unknown
    "Tibt",  # 0FCE..0FD4 ; Tibetan
    "Zyyy",  # 0FD5..0FD8 ; Common
    "Tibt",  # 0FD9..0FDA ; Tibetan
    "Zzzz",  # 0FDB..0FFF ; Unknown
    "Mymr",  # 1000..109F ; Myanmar
    "Geor",  # 10A0..10C5 ; Georgian
    "Zzzz",  # 10C6..10C6 ; Unknown
    "Geor",  # 10C7..10C7 ; Georgian
    "Zzzz",  # 10C8..10CC ; Unknown
    "Geor",  # 10CD..10CD ; Georgian
    "Zzzz",  # 10CE..10CF ; Unknown
    "Geor",  # 10D0..10FA ; Georgian
    "Zyyy",  # 10FB..10FB ; Common
    "Geor",  # 10FC..10FF ; Georgian
    "Hang",  # 1100..11FF ; Hangul
    "Ethi",  # 1200..1248 ; Ethiopic
    "Zzzz",  # 1249..1249 ; Unknown
    "Ethi",  # 124A..124D ; Ethiopic
    "Zzzz",  # 124E..124F ; Unknown
    "Ethi",  # 1250..1256 ; Ethiopic
    "Zzzz",  # 1257..1257 ; Unknown
    "Ethi",  # 1258..1258 ; Ethiopic
    "Zzzz",  # 1259..1259 ; Unknown
    "Ethi",  # 125A..125D ; Ethiopic
    "Zzzz",  # 125E..125F ; Unknown
    "Ethi",  # 1260..1288 ; Ethiopic
    "Zzzz",  # 1289..1289 ; Unknown
    "Ethi",  # 128A..128D ; Ethiopic
    "Zzzz",  # 128E..128F ; Unknown
    "Ethi",  # 1290..12B0 ; Ethiopic
    "Zzzz",  # 12B1..12B1 ; Unknown
    "Ethi",  # 12B2..12B5 ; Ethiopic
    "Zzzz",  # 12B6..12B7 ; Unknown
    "Ethi",  # 12B8..12BE ; Ethiopic
    "Zzzz",  # 12BF..12BF ; Unknown
    "Ethi",  # 12C0..12C0 ; Ethiopic
    "Zzzz",  # 12C1..12C1 ; Unknown
    "Ethi",  # 12C2..12C5 ; Ethiopic
    "Zzzz",  # 12C6..12C7 ; Unknown
    "Ethi",  # 12C8..12D6 ; Ethiopic
    "Zzzz",  # 12D7..12D7 ; Unknown
    "Ethi",  # 12D8..1310 ; Ethiopic
    "Zzzz",  # 1311..1311 ; Unknown
    "Ethi",  # 1312..1315 ; Ethiopic
    "Zzzz",  # 1316..1317 ; Unknown
    "Ethi",  # 1318..135A ; Ethiopic
    "Zzzz",  # 135B..135C ; Unknown
    "Ethi",  # 135D..137C ; Ethiopic
    "Zzzz",  # 137D..137F ; Unknown
    "Ethi",  # 1380..1399 ; Ethiopic
    "Zzzz",  # 139A..139F ; Unknown
    "Cher",  # 13A0..13F5 ; Cherokee
    "Zzzz",  # 13F6..13F7 ; Unknown
    "Cher",  # 13F8..13FD ; Cherokee
    "Zzzz",  # 13FE..13FF ; Unknown
    "Cans",  # 1400..167F ; Canadian_Aboriginal
    "Ogam",  # 1680..169C ; Ogham
    "Zzzz",  # 169D..169F ; Unknown
    "Runr",  # 16A0..16EA ; Runic
    "Zyyy",  # 16EB..16ED ; Common
    "Runr",  # 16EE..16F8 ; Runic
    "Zzzz",  # 16F9..16FF ; Unknown
    "Tglg",  # 1700..1715 ; Tagalog
    "Zzzz",  # 1716..171E ; Unknown
    "Tglg",  # 171F..171F ; Tagalog
    "Hano",  # 1720..1734 ; Hanunoo
    "Zyyy",  # 1735..1736 ; Common
    "Zzzz",  # 1737..173F ; Unknown
    "Buhd",  # 1740..1753 ; Buhid
    "Zzzz",  # 1754..175F ; Unknown
    "Tagb",  # 1760..176C ; Tagbanwa
    "Zzzz",  # 176D..176D ; Unknown
    "Tagb",  # 176E..1770 ; Tagbanwa
    "Zzzz",  # 1771..1771 ; Unknown
    "Tagb",  # 1772..1773 ; Tagbanwa
    "Zzzz",  # 1774..177F ; Unknown
    "Khmr",  # 1780..17DD ; Khmer
    "Zzzz",  # 17DE..17DF ; Unknown
    "Khmr",  # 17E0..17E9 ; Khmer
    "Zzzz",  # 17EA..17EF ; Unknown
    "Khmr",  # 17F0..17F9 ; Khmer
    "Zzzz",  # 17FA..17FF ; Unknown
    "Mong",  # 1800..1801 ; Mongolian
    "Zyyy",  # 1802..1803 ; Common
    "Mong",  # 1804..1804 ; Mongolian
    "Zyyy",  # 1805..1805 ; Common
    "Mong",  # 1806..1819 ; Mongolian
    "Zzzz",  # 181A..181F ; Unknown
    "Mong",  # 1820..1878 ; Mongolian
    "Zzzz",  # 1879..187F ; Unknown
    "Mong",  # 1880..18AA ; Mongolian
    "Zzzz",  # 18AB..18AF ; Unknown
    "Cans",  # 18B0..18F5 ; Canadian_Aboriginal
    "Zzzz",  # 18F6..18FF ; Unknown
    "Limb",  # 1900..191E ; Limbu
    "Zzzz",  # 191F..191F ; Unknown
    "Limb",  # 1920..192B ; Limbu
    "Zzzz",  # 192C..192F ; Unknown
    "Limb",  # 1930..193B ; Limbu
    "Zzzz",  # 193C..193F ; Unknown
    "Limb",  # 1940..1940 ; Limbu
    "Zzzz",  # 1941..1943 ; Unknown
    "Limb",  # 1944..194F ; Limbu
    "Tale",  # 1950..196D ; Tai_Le
    "Zzzz",  # 196E..196F ; Unknown
    "Tale",  # 1970..1974 ; Tai_Le
    "Zzzz",  # 1975..197F ; Unknown
    "Talu",  # 1980..19AB ; New_Tai_Lue
    "Zzzz",  # 19AC..19AF ; Unknown
    "Talu",  # 19B0..19C9 ; New_Tai_Lue
    "Zzzz",  # 19CA..19CF ; Unknown
    "Talu",  # 19D0..19DA ; New_Tai_Lue
    "Zzzz",  # 19DB..19DD ; Unknown
    "Talu",  # 19DE..19DF ; New_Tai_Lue
    "Khmr",  # 19E0..19FF ; Khmer
    "Bugi",  # 1A00..1A1B ; Buginese
    "Zzzz",  # 1A1C..1A1D ; Unknown
    "Bugi",  # 1A1E..1A1F ; Buginese
    "Lana",  # 1A20..1A5E ; Tai_Tham
    "Zzzz",  # 1A5F..1A5F ; Unknown
    "Lana",  # 1A60..1A7C ; Tai_Tham
    "Zzzz",  # 1A7D..1A7E ; Unknown
    "Lana",  # 1A7F..1A89 ; Tai_Tham
    "Zzzz",  # 1A8A..1A8F ; Unknown
    "Lana",  # 1A90..1A99 ; Tai_Tham
    "Zzzz",  # 1A9A..1A9F ; Unknown
    "Lana",  # 1AA0..1AAD ; Tai_Tham
    "Zzzz",  # 1AAE..1AAF ; Unknown
    "Zinh",  # 1AB0..1ACE ; Inherited
    "Zzzz",  # 1ACF..1AFF ; Unknown
    "Bali",  # 1B00..1B4C ; Balinese
    "Zzzz",  # 1B4D..1B4D ; Unknown
    "Bali",  # 1B4E..1B7F ; Balinese
    "Sund",  # 1B80..1BBF ; Sundanese
    "Batk",  # 1BC0..1BF3 ; Batak
    "Zzzz",  # 1BF4..1BFB ; Unknown
    "Batk",  # 1BFC..1BFF ; Batak
    "Lepc",  # 1C00..1C37 ; Lepcha
    "Zzzz",  # 1C38..1C3A ; Unknown
    "Lepc",  # 1C3B..1C49 ; Lepcha
    "Zzzz",  # 1C4A..1C4C ; Unknown
    "Lepc",  # 1C4D..1C4F ; Lepcha
    "Olck",  # 1C50..1C7F ; Ol_Chiki
    "Cyrl",  # 1C80..1C8A ; Cyrillic
    "Zzzz",  # 1C8B..1C8F ; Unknown
    "Geor",  # 1C90..1CBA ; Georgian
    "Zzzz",  # 1CBB..1CBC ; Unknown
    "Geor",  # 1CBD..1CBF ; Georgian
    "Sund",  # 1CC0..1CC7 ; Sundanese
    "Zzzz",  # 1CC8..1CCF ; Unknown
    "Zinh",  # 1CD0..1CD2 ; Inherited
    "Zyyy",  # 1CD3..1CD3 ; Common
    "Zinh",  # 1CD4..1CE0 ; Inherited
    "Zyyy",  # 1CE1..1CE1 ; Common
    "Zinh",  # 1CE2..1CE8 ; Inherited
    "Zyyy",  # 1CE9..1CEC ; Common
    "Zinh",  # 1CED..1CED ; Inherited
    "Zyyy",  # 1CEE..1CF3 ; Common
    "Zinh",  # 1CF4..1CF4 ; Inherited
    "Zyyy",  # 1CF5..1CF7 ; Common
    "Zinh",  # 1CF8..1CF9 ; Inherited
    "Zyyy",  # 1CFA..1CFA ; Common
    "Zzzz",  # 1CFB..1CFF ; Unknown
    "Latn",  # 1D00..1D25 ; Latin
    "Grek",  # 1D26..1D2A ; Greek
    "Cyrl",  # 1D2B..1D2B ; Cyrillic
    "Latn",  # 1D2C..1D5C ; Latin
    "Grek",  # 1D5D..1D61 ; Greek
    "Latn",  # 1D62..1D65 ; Latin
    "Grek",  # 1D66..1D6A ; Greek
    "Latn",  # 1D6B..1D77 ; Latin
    "Cyrl",  # 1D78..1D78 ; Cyrillic
    "Latn",  # 1D79..1DBE ; Latin
    "Grek",  # 1DBF..1DBF ; Greek
    "Zinh",  # 1DC0..1DFF ; Inherited
    "Latn",  # 1E00..1EFF ; Latin
    "Grek",  # 1F00..1F15 ; Greek
    "Zzzz",  # 1F16..1F17 ; Unknown
    "Grek",  # 1F18..1F1D ; Greek
    "Zzzz",  # 1F1E..1F1F ; Unknown
    "Grek",  # 1F20..1F45 ; Greek
    "Zzzz",  # 1F46..1F47 ; Unknown
    "Grek",  # 1F48..1F4D ; Greek
    "Zzzz",  # 1F4E..1F4F ; Unknown
    "Grek",  # 1F50..1F57 ; Greek
    "Zzzz",  # 1F58..1F58 ; Unknown
    "Grek",  # 1F59..1F59 ; Greek
    "Zzzz",  # 1F5A..1F5A ; Unknown
    "Grek",  # 1F5B..1F5B ; Greek
    "Zzzz",  # 1F5C..1F5C ; Unknown
    "Grek",  # 1F5D..1F5D ; Greek
    "Zzzz",  # 1F5E..1F5E ; Unknown
    "Grek",  # 1F5F..1F7D ; Greek
    "Zzzz",  # 1F7E..1F7F ; Unknown
    "Grek",  # 1F80..1FB4 ; Greek
    "Zzzz",  # 1FB5..1FB5 ; Unknown
    "Grek",  # 1FB6..1FC4 ; Greek
    "Zzzz",  # 1FC5..1FC5 ; Unknown
    "Grek",  # 1FC6..1FD3 ; Greek
    "Zzzz",  # 1FD4..1FD5 ; Unknown
    "Grek",  # 1FD6..1FDB ; Greek
    "Zzzz",  # 1FDC..1FDC ; Unknown
    "Grek",  # 1FDD..1FEF ; Greek
    "Zzzz",  # 1FF0..1FF1 ; Unknown
    "Grek",  # 1FF2..1FF4 ; Greek
    "Zzzz",  # 1FF5..1FF5 ; Unknown
    "Grek",  # 1FF6..1FFE ; Greek
    "Zzzz",  # 1FFF..1FFF ; Unknown
    "Zyyy",  # 2000..200B ; Common
    "Zinh",  # 200C..200D ; Inherited
    "Zyyy",  # 200E..2064 ; Common
    "Zzzz",  # 2065..2065 ; Unknown
    "Zyyy",  # 2066..2070 ; Common
    "Latn",  # 2071..2071 ; Latin
    "Zzzz",  # 2072..2073 ; Unknown
    "Zyyy",  # 2074..207E ; Common
    "Latn",  # 207F..207F ; Latin
    "Zyyy",  # 2080..208E ; Common
    "Zzzz",  # 208F..208F ; Unknown
    "Latn",  # 2090..209C ; Latin
    "Zzzz",  # 209D..209F ; Unknown
    "Zyyy",  # 20A0..20C0 ; Common
    "Zzzz",  # 20C1..20CF ; Unknown
    "Zinh",  # 20D0..20F0 ; Inherited
    "Zzzz",  # 20F1..20FF ; Unknown
    "Zyyy",  # 2100..2125 ; Common
    "Grek",  # 2126..2126 ; Greek
    "Zyyy",  # 2127..2129 ; Common
    "Latn",  # 212A..212B ; Latin
    "Zyyy",  # 212C..2131 ; Common
    "Latn",  # 2132..2132 ; Latin
    "Zyyy",  # 2133..214D ; Common
    "Latn",  # 214E..214E ; Latin
    "Zyyy",  # 214F..215F ; Common
    "Latn",  # 2160..2188 ; Latin
    "Zyyy",  # 2189..218B ; Common
    "Zzzz",  # 218C..218F ; Unknown
    "Zyyy",  # 2190..2429 ; Common
    "Zzzz",  # 242A..243F ; Unknown
    "Zyyy",  # 2440..244A ; Common
    "Zzzz",  # 244B..245F ; Unknown
    "Zyyy",  # 2460..27FF ; Common
    "Brai",  # 2800..28FF ; Braille
    "Zyyy",  # 2900..2B73 ; Common
    "Zzzz",  # 2B74..2B75 ; Unknown
    "Zyyy",  # 2B76..2B95 ; Common
    "Zzzz",  # 2B96..2B96 ; Unknown
    "Zyyy",  # 2B97..2BFF ; Common
    "Glag",  # 2C00..2C5F ; Glagolitic
    "Latn",  # 2C60..2C7F ; Latin
    "Copt",  # 2C80..2CF3 ; Coptic
    "Zzzz",  # 2CF4..2CF8 ; Unknown
    "Copt",  # 2CF9..2CFF ; Coptic
    "Geor",  # 2D00..2D25 ; Georgian
    "Zzzz",  # 2D26..2D26 ; Unknown
    "Geor",  # 2D27..2D27 ; Georgian
    "Zzzz",  # 2D28..2D2C ; Unknown
    "Geor",  # 2D2D..2D2D ; Georgian
    "Zzzz",  # 2D2E..2D2F ; Unknown
    "Tfng",  # 2D30..2D67 ; Tifinagh
    "Zzzz",  # 2D68..2D6E ; Unknown
    "Tfng",  # 2D6F..2D70 ; Tifinagh
    "Zzzz",  # 2D71..2D7E ; Unknown
    "Tfng",  # 2D7F..2D7F ; Tifinagh
    "Ethi",  # 2D80..2D96 ; Ethiopic
    "Zzzz",  # 2D97..2D9F ; Unknown
    "Ethi",  # 2DA0..2DA6 ; Ethiopic
    "Zzzz",  # 2DA7..2DA7 ; Unknown
    "Ethi",  # 2DA8..2DAE ; Ethiopic
    "Zzzz",  # 2DAF..2DAF ; Unknown
    "Ethi",  # 2DB0..2DB6 ; Ethiopic
    "Zzzz",  # 2DB7..2DB7 ; Unknown
    "Ethi",  # 2DB8..2DBE ; Ethiopic
    "Zzzz",  # 2DBF..2DBF ; Unknown
    "Ethi",  # 2DC0..2DC6 ; Ethiopic
    "Zzzz",  # 2DC7..2DC7 ; Unknown
    "Ethi",  # 2DC8..2DCE ; Ethiopic
    "Zzzz",  # 2DCF..2DCF ; Unknown
    "Ethi",  # 2DD0..2DD6 ; Ethiopic
    "Zzzz",  # 2DD7..2DD7 ; Unknown
    "Ethi",  # 2DD8..2DDE ; Ethiopic
    "Zzzz",  # 2DDF..2DDF ; Unknown
    "Cyrl",  # 2DE0..2DFF ; Cyrillic
    "Zyyy",  # 2E00..2E5D ; Common
    "Zzzz",  # 2E5E..2E7F ; Unknown
    "Hani",  # 2E80..2E99 ; Han
    "Zzzz",  # 2E9A..2E9A ; Unknown
    "Hani",  # 2E9B..2EF3 ; Han
    "Zzzz",  # 2EF4..2EFF ; Unknown
    "Hani",  # 2F00..2FD5 ; Han
    "Zzzz",  # 2FD6..2FEF ; Unknown
    "Zyyy",  # 2FF0..3004 ; Common
    "Hani",  # 3005..3005 ; Han
    "Zyyy",  # 3006..3006 ; Common
    "Hani",  # 3007..3007 ; Han
    "Zyyy",  # 3008..3020 ; Common
    "Hani",  # 3021..3029 ; Han
    "Zinh",  # 302A..302D ; Inherited
    "Hang",  # 302E..302F ; Hangul
    "Zyyy",  # 3030..3037 ; Common
    "Hani",  # 3038..303B ; Han
    "Zyyy",  # 303C..303F ; Common
    "Zzzz",  # 3040..3040 ; Unknown
    "Hira",  # 3041..3096 ; Hiragana
    "Zzzz",  # 3097..3098 ; Unknown
    "Zinh",  # 3099..309A ; Inherited
    "Zyyy",  # 309B..309C ; Common
    "Hira",  # 309D..309F ; Hiragana
    "Zyyy",  # 30A0..30A0 ; Common
    "Kana",  # 30A1..30FA ; Katakana
    "Zyyy",  # 30FB..30FC ; Common
    "Kana",  # 30FD..30FF ; Katakana
    "Zzzz",  # 3100..3104 ; Unknown
    "Bopo",  # 3105..312F ; Bopomofo
    "Zzzz",  # 3130..3130 ; Unknown
    "Hang",  # 3131..318E ; Hangul
    "Zzzz",  # 318F..318F ; Unknown
    "Zyyy",  # 3190..319F ; Common
    "Bopo",  # 31A0..31BF ; Bopomofo
    "Zyyy",  # 31C0..31E5 ; Common
    "Zzzz",  # 31E6..31EE ; Unknown
    "Zyyy",  # 31EF..31EF ; Common
    "Kana",  # 31F0..31FF ; Katakana
    "Hang",  # 3200..321E ; Hangul
    "Zzzz",  # 321F..321F ; Unknown
    "Zyyy",  # 3220..325F ; Common
    "Hang",  # 3260..327E ; Hangul
    "Zyyy",  # 327F..32CF ; Common
    "Kana",  # 32D0..32FE ; Katakana
    "Zyyy",  # 32FF..32FF ; Common
    "Kana",  # 3300..3357 ; Katakana
    "Zyyy",  # 3358..33FF ; Common
    "Hani",  # 3400..4DBF ; Han
    "Zyyy",  # 4DC0..4DFF ; Common
    "Hani",  # 4E00..9FFF ; Han
    "Yiii",  # A000..A48C ; Yi
    "Zzzz",  # A48D..A48F ; Unknown
    "Yiii",  # A490..A4C6 ; Yi
    "Zzzz",  # A4C7..A4CF ; Unknown
    "Lisu",  # A4D0..A4FF ; Lisu
    "Vaii",  # A500..A62B ; Vai
    "Zzzz",  # A62C..A63F ; Unknown
    "Cyrl",  # A640..A69F ; Cyrillic
    "Bamu",  # A6A0..A6F7 ; Bamum
    "Zzzz",  # A6F8..A6FF ; Unknown
    "Zyyy",  # A700..A721 ; Common
    "Latn",  # A722..A787 ; Latin
    "Zyyy",  # A788..A78A ; Common
    "Latn",  # A78B..A7CD ; Latin
    "Zzzz",  # A7CE..A7CF ; Unknown
    "Latn",  # A7D0..A7D1 ; Latin
    "Zzzz",  # A7D2..A7D2 ; Unknown
    "Latn",  # A7D3..A7D3 ; Latin
    "Zzzz",  # A7D4..A7D4 ; Unknown
    "Latn",  # A7D5..A7DC ; Latin
    "Zzzz",  # A7DD..A7F1 ; Unknown
    "Latn",  # A7F2..A7FF ; Latin
    "Sylo",  # A800..A82C ; Syloti_Nagri
    "Zzzz",  # A82D..A82F ; Unknown
    "Zyyy",  # A830..A839 ; Common
    "Zzzz",  # A83A..A83F ; Unknown
    "Phag",  # A840..A877 ; Phags_Pa
    "Zzzz",  # A878..A87F ; Unknown
    "Saur",  # A880..A8C5 ; Saurashtra
    "Zzzz",  # A8C6..A8CD ; Unknown
    "Saur",  # A8CE..A8D9 ; Saurashtra
    "Zzzz",  # A8DA..A8DF ; Unknown
    "Deva",  # A8E0..A8FF ; Devanagari
    "Kali",  # A900..A92D ; Kayah_Li
    "Zyyy",  # A92E..A92E ; Common
    "Kali",  # A92F..A92F ; Kayah_Li
    "Rjng",  # A930..A953 ; Rejang
    "Zzzz",  # A954..A95E ; Unknown
    "Rjng",  # A95F..A95F ; Rejang
    "Hang",  # A960..A97C ; Hangul
    "Zzzz",  # A97D..A97F ; Unknown
    "Java",  # A980..A9CD ; Javanese
    "Zzzz",  # A9CE..A9CE ; Unknown
    "Zyyy",  # A9CF..A9CF ; Common
    "Java",  # A9D0..A9D9 ; Javanese
    "Zzzz",  # A9DA..A9DD ; Unknown
    "Java",  # A9DE..A9DF ; Javanese
    "Mymr",  # A9E0..A9FE ; Myanmar
    "Zzzz",  # A9FF..A9FF ; Unknown
    "Cham",  # AA00..AA36 ; Cham
    "Zzzz",  # AA37..AA3F ; Unknown
    "Cham",  # AA40..AA4D ; Cham
    "Zzzz",  # AA4E..AA4F ; Unknown
    "Cham",  # AA50..AA59 ; Cham
    "Zzzz",  # AA5A..AA5B ; Unknown
    "Cham",  # AA5C..AA5F ; Cham
    "Mymr",  # AA60..AA7F ; Myanmar
    "Tavt",  # AA80..AAC2 ; Tai_Viet
    "Zzzz",  # AAC3..AADA ; Unknown
    "Tavt",  # AADB..AADF ; Tai_Viet
    "Mtei",  # AAE0..AAF6 ; Meetei_Mayek
    "Zzzz",  # AAF7..AB00 ; Unknown
    "Ethi",  # AB01..AB06 ; Ethiopic
    "Zzzz",  # AB07..AB08 ; Unknown
    "Ethi",  # AB09..AB0E ; Ethiopic
    "Zzzz",  # AB0F..AB10 ; Unknown
    "Ethi",  # AB11..AB16 ; Ethiopic
    "Zzzz",  # AB17..AB1F ; Unknown
    "Ethi",  # AB20..AB26 ; Ethiopic
    "Zzzz",  # AB27..AB27 ; Unknown
    "Ethi",  # AB28..AB2E ; Ethiopic
    "Zzzz",  # AB2F..AB2F ; Unknown
    "Latn",  # AB30..AB5A ; Latin
    "Zyyy",  # AB5B..AB5B ; Common
    "Latn",  # AB5C..AB64 ; Latin
    "Grek",  # AB65..AB65 ; Greek
    "Latn",  # AB66..AB69 ; Latin
    "Zyyy",  # AB6A..AB6B ; Common
    "Zzzz",  # AB6C..AB6F ; Unknown
    "Cher",  # AB70..ABBF ; Cherokee
    "Mtei",  # ABC0..ABED ; Meetei_Mayek
    "Zzzz",  # ABEE..ABEF ; Unknown
    "Mtei",  # ABF0..ABF9 ; Meetei_Mayek
    "Zzzz",  # ABFA..ABFF ; Unknown
    "Hang",  # AC00..D7A3 ; Hangul
    "Zzzz",  # D7A4..D7AF ; Unknown
    "Hang",  # D7B0..D7C6 ; Hangul
    "Zzzz",  # D7C7..D7CA ; Unknown
    "Hang",  # D7CB..D7FB ; Hangul
    "Zzzz",  # D7FC..F8FF ; Unknown
    "Hani",  # F900..FA6D ; Han
    "Zzzz",  # FA6E..FA6F ; Unknown
    "Hani",  # FA70..FAD9 ; Han
    "Zzzz",  # FADA..FAFF ; Unknown
    "Latn",  # FB00..FB06 ; Latin
    "Zzzz",  # FB07..FB12 ; Unknown
    "Armn",  # FB13..FB17 ; Armenian
    "Zzzz",  # FB18..FB1C ; Unknown
    "Hebr",  # FB1D..FB36 ; Hebrew
    "Zzzz",  # FB37..FB37 ; Unknown
    "Hebr",  # FB38..FB3C ; Hebrew
    "Zzzz",  # FB3D..FB3D ; Unknown
    "Hebr",  # FB3E..FB3E ; Hebrew
    "Zzzz",  # FB3F..FB3F ; Unknown
    "Hebr",  # FB40..FB41 ; Hebrew
    "Zzzz",  # FB42..FB42 ; Unknown
    "Hebr",  # FB43..FB44 ; Hebrew
    "Zzzz",  # FB45..FB45 ; Unknown
    "Hebr",  # FB46..FB4F ; Hebrew
    "Arab",  # FB50..FBC2 ; Arabic
    "Zzzz",  # FBC3..FBD2 ; Unknown
    "Arab",  # FBD3..FD3D ; Arabic
    "Zyyy",  # FD3E..FD3F ; Common
    "Arab",  # FD40..FD8F ; Arabic
    "Zzzz",  # FD90..FD91 ; Unknown
    "Arab",  # FD92..FDC7 ; Arabic
    "Zzzz",  # FDC8..FDCE ; Unknown
    "Arab",  # FDCF..FDCF ; Arabic
    "Zzzz",  # FDD0..FDEF ; Unknown
    "Arab",  # FDF0..FDFF ; Arabic
    "Zinh",  # FE00..FE0F ; Inherited
    "Zyyy",  # FE10..FE19 ; Common
    "Zzzz",  # FE1A..FE1F ; Unknown
    "Zinh",  # FE20..FE2D ; Inherited
    "Cyrl",  # FE2E..FE2F ; Cyrillic
    "Zyyy",  # FE30..FE52 ; Common
    "Zzzz",  # FE53..FE53 ; Unknown
    "Zyyy",  # FE54..FE66 ; Common
    "Zzzz",  # FE67..FE67 ; Unknown
    "Zyyy",  # FE68..FE6B ; Common
    "Zzzz",  # FE6C..FE6F ; Unknown
    "Arab",  # FE70..FE74 ; Arabic
    "Zzzz",  # FE75..FE75 ; Unknown
    "Arab",  # FE76..FEFC ; Arabic
    "Zzzz",  # FEFD..FEFE ; Unknown
    "Zyyy",  # FEFF..FEFF ; Common
    "Zzzz",  # FF00..FF00 ; Unknown
    "Zyyy",  # FF01..FF20 ; Common
    "Latn",  # FF21..FF3A ; Latin
    "Zyyy",  # FF3B..FF40 ; Common
    "Latn",  # FF41..FF5A ; Latin
    "Zyyy",  # FF5B..FF65 ; Common
    "Kana",  # FF66..FF6F ; Katakana
    "Zyyy",  # FF70..FF70 ; Common
    "Kana",  # FF71..FF9D ; Katakana
    "Zyyy",  # FF9E..FF9F ; Common
    "Hang",  # FFA0..FFBE ; Hangul
    "Zzzz",  # FFBF..FFC1 ; Unknown
    "Hang",  # FFC2..FFC7 ; Hangul
    "Zzzz",  # FFC8..FFC9 ; Unknown
    "Hang",  # FFCA..FFCF ; Hangul
    "Zzzz",  # FFD0..FFD1 ; Unknown
    "Hang",  # FFD2..FFD7 ; Hangul
    "Zzzz",  # FFD8..FFD9 ; Unknown
    "Hang",  # FFDA..FFDC ; Hangul
    "Zzzz",  # FFDD..FFDF ; Unknown
    "Zyyy",  # FFE0..FFE6 ; Common
    "Zzzz",  # FFE7..FFE7 ; Unknown
    "Zyyy",  # FFE8..FFEE ; Common
    "Zzzz",  # FFEF..FFF8 ; Unknown
    "Zyyy",  # FFF9..FFFD ; Common
    "Zzzz",  # FFFE..FFFF ; Unknown
    "Linb",  # 10000..1000B ; Linear_B
    "Zzzz",  # 1000C..1000C ; Unknown
    "Linb",  # 1000D..10026 ; Linear_B
    "Zzzz",  # 10027..10027 ; Unknown
    "Linb",  # 10028..1003A ; Linear_B
    "Zzzz",  # 1003B..1003B ; Unknown
    "Linb",  # 1003C..1003D ; Linear_B
    "Zzzz",  # 1003E..1003E ; Unknown
    "Linb",  # 1003F..1004D ; Linear_B
    "Zzzz",  # 1004E..1004F ; Unknown
    "Linb",  # 10050..1005D ; Linear_B
    "Zzzz",  # 1005E..1007F ; Unknown
    "Linb",  # 10080..100FA ; Linear_B
    "Zzzz",  # 100FB..100FF ; Unknown
    "Zyyy",  # 10100..10102 ; Common
    "Zzzz",  # 10103..10106 ; Unknown
    "Zyyy",  # 10107..10133 ; Common
    "Zzzz",  # 10134..10136 ; Unknown
    "Zyyy",  # 10137..1013F ; Common
    "Grek",  # 10140..1018E ; Greek
    "Zzzz",  # 1018F..1018F ; Unknown
    "Zyyy",  # 10190..1019C ; Common
    "Zzzz",  # 1019D..1019F ; Unknown
    "Grek",  # 101A0..101A0 ; Greek
    "Zzzz",  # 101A1..101CF ; Unknown
    "Zyyy",  # 101D0..101FC ; Common
    "Zinh",  # 101FD..101FD ; Inherited
    "Zzzz",  # 101FE..1027F ; Unknown
    "Lyci",  # 10280..1029C ; Lycian
    "Zzzz",  # 1029D..1029F ; Unknown
    "Cari",  # 102A0..102D0 ; Carian
    "Zzzz",  # 102D1..102DF ; Unknown
    "Zinh",  # 102E0..102E0 ; Inherited
    "Zyyy",  # 102E1..102FB ; Common
    "Zzzz",  # 102FC..102FF ; Unknown
    "Ital",  # 10300..10323 ; Old_Italic
    "Zzzz",  # 10324..1032C ; Unknown
    "Ital",  # 1032D..1032F ; Old_Italic
    "Goth",  # 10330..1034A ; Gothic
    "Zzzz",  # 1034B..1034F ; Unknown
    "Perm",  # 10350..1037A ; Old_Permic
    "Zzzz",  # 1037B..1037F ; Unknown
    "Ugar",  # 10380..1039D ; Ugaritic
    "Zzzz",  # 1039E..1039E ; Unknown
    "Ugar",  # 1039F..1039F ; Ugaritic
    "Xpeo",  # 103A0..103C3 ; Old_Persian
    "Zzzz",  # 103C4..103C7 ; Unknown
    "Xpeo",  # 103C8..103D5 ; Old_Persian
    "Zzzz",  # 103D6..103FF ; Unknown
    "Dsrt",  # 10400..1044F ; Deseret
    "Shaw",  # 10450..1047F ; Shavian
    "Osma",  # 10480..1049D ; Osmanya
    "Zzzz",  # 1049E..1049F ; Unknown
    "Osma",  # 104A0..104A9 ; Osmanya
    "Zzzz",  # 104AA..104AF ; Unknown
    "Osge",  # 104B0..104D3 ; Osage
    "Zzzz",  # 104D4..104D7 ; Unknown
    "Osge",  # 104D8..104FB ; Osage
    "Zzzz",  # 104FC..104FF ; Unknown
    "Elba",  # 10500..10527 ; Elbasan
    "Zzzz",  # 10528..1052F ; Unknown
    "Aghb",  # 10530..10563 ; Caucasian_Albanian
    "Zzzz",  # 10564..1056E ; Unknown
    "Aghb",  # 1056F..1056F ; Caucasian_Albanian
    "Vith",  # 10570..1057A ; Vithkuqi
    "Zzzz",  # 1057B..1057B ; Unknown
    "Vith",  # 1057C..1058A ; Vithkuqi
    "Zzzz",  # 1058B..1058B ; Unknown
    "Vith",  # 1058C..10592 ; Vithkuqi
    "Zzzz",  # 10593..10593 ; Unknown
    "Vith",  # 10594..10595 ; Vithkuqi
    "Zzzz",  # 10596..10596 ; Unknown
    "Vith",  # 10597..105A1 ; Vithkuqi
    "Zzzz",  # 105A2..105A2 ; Unknown
    "Vith",  # 105A3..105B1 ; Vithkuqi
    "Zzzz",  # 105B2..105B2 ; Unknown
    "Vith",  # 105B3..105B9 ; Vithkuqi
    "Zzzz",  # 105BA..105BA ; Unknown
    "Vith",  # 105BB..105BC ; Vithkuqi
    "Zzzz",  # 105BD..105BF ; Unknown
    "Todr",  # 105C0..105F3 ; Todhri
    "Zzzz",  # 105F4..105FF ; Unknown
    "Lina",  # 10600..10736 ; Linear_A
    "Zzzz",  # 10737..1073F ; Unknown
    "Lina",  # 10740..10755 ; Linear_A
    "Zzzz",  # 10756..1075F ; Unknown
    "Lina",  # 10760..10767 ; Linear_A
    "Zzzz",  # 10768..1077F ; Unknown
    "Latn",  # 10780..10785 ; Latin
    "Zzzz",  # 10786..10786 ; Unknown
    "Latn",  # 10787..107B0 ; Latin
    "Zzzz",  # 107B1..107B1 ; Unknown
    "Latn",  # 107B2..107BA ; Latin
    "Zzzz",  # 107BB..107FF ; Unknown
    "Cprt",  # 10800..10805 ; Cypriot
    "Zzzz",  # 10806..10807 ; Unknown
    "Cprt",  # 10808..10808 ; Cypriot
    "Zzzz",  # 10809..10809 ; Unknown
    "Cprt",  # 1080A..10835 ; Cypriot
    "Zzzz",  # 10836..10836 ; Unknown
    "Cprt",  # 10837..10838 ; Cypriot
    "Zzzz",  # 10839..1083B ; Unknown
    "Cprt",  # 1083C..1083C ; Cypriot
    "Zzzz",  # 1083D..1083E ; Unknown
    "Cprt",  # 1083F..1083F ; Cypriot
    "Armi",  # 10840..10855 ; Imperial_Aramaic
    "Zzzz",  # 10856..10856 ; Unknown
    "Armi",  # 10857..1085F ; Imperial_Aramaic
    "Palm",  # 10860..1087F ; Palmyrene
    "Nbat",  # 10880..1089E ; Nabataean
    "Zzzz",  # 1089F..108A6 ; Unknown
    "Nbat",  # 108A7..108AF ; Nabataean
    "Zzzz",  # 108B0..108DF ; Unknown
    "Hatr",  # 108E0..108F2 ; Hatran
    "Zzzz",  # 108F3..108F3 ; Unknown
    "Hatr",  # 108F4..108F5 ; Hatran
    "Zzzz",  # 108F6..108FA ; Unknown
    "Hatr",  # 108FB..108FF ; Hatran
    "Phnx",  # 10900..1091B ; Phoenician
    "Zzzz",  # 1091C..1091E ; Unknown
    "Phnx",  # 1091F..1091F ; Phoenician
    "Lydi",  # 10920..10939 ; Lydian
    "Zzzz",  # 1093A..1093E ; Unknown
    "Lydi",  # 1093F..1093F ; Lydian
    "Zzzz",  # 10940..1097F ; Unknown
    "Mero",  # 10980..1099F ; Meroitic_Hieroglyphs
    "Merc",  # 109A0..109B7 ; Meroitic_Cursive
    "Zzzz",  # 109B8..109BB ; Unknown
    "Merc",  # 109BC..109CF ; Meroitic_Cursive
    "Zzzz",  # 109D0..109D1 ; Unknown
    "Merc",  # 109D2..109FF ; Meroitic_Cursive
    "Khar",  # 10A00..10A03 ; Kharoshthi
    "Zzzz",  # 10A04..10A04 ; Unknown
    "Khar",  # 10A05..10A06 ; Kharoshthi
    "Zzzz",  # 10A07..10A0B ; Unknown
    "Khar",  # 10A0C..10A13 ; Kharoshthi
    "Zzzz",  # 10A14..10A14 ; Unknown
    "Khar",  # 10A15..10A17 ; Kharoshthi
    "Zzzz",  # 10A18..10A18 ; Unknown
    "Khar",  # 10A19..10A35 ; Kharoshthi
    "Zzzz",  # 10A36..10A37 ; Unknown
    "Khar",  # 10A38..10A3A ; Kharoshthi
    "Zzzz",  # 10A3B..10A3E ; Unknown
    "Khar",  # 10A3F..10A48 ; Kharoshthi
    "Zzzz",  # 10A49..10A4F ; Unknown
    "Khar",  # 10A50..10A58 ; Kharoshthi
    "Zzzz",  # 10A59..10A5F ; Unknown
    "Sarb",  # 10A60..10A7F ; Old_South_Arabian
    "Narb",  # 10A80..10A9F ; Old_North_Arabian
    "Zzzz",  # 10AA0..10ABF ; Unknown
    "Mani",  # 10AC0..10AE6 ; Manichaean
    "Zzzz",  # 10AE7..10AEA ; Unknown
    "Mani",  # 10AEB..10AF6 ; Manichaean
    "Zzzz",  # 10AF7..10AFF ; Unknown
    "Avst",  # 10B00..10B35 ; Avestan
    "Zzzz",  # 10B36..10B38 ; Unknown
    "Avst",  # 10B39..10B3F ; Avestan
    "Prti",  # 10B40..10B55 ; Inscriptional_Parthian
    "Zzzz",  # 10B56..10B57 ; Unknown
    "Prti",  # 10B58..10B5F ; Inscriptional_Parthian
    "Phli",  # 10B60..10B72 ; Inscriptional_Pahlavi
    "Zzzz",  # 10B73..10B77 ; Unknown
    "Phli",  # 10B78..10B7F ; Inscriptional_Pahlavi
    "Phlp",  # 10B80..10B91 ; Psalter_Pahlavi
    "Zzzz",  # 10B92..10B98 ; Unknown
    "Phlp",  # 10B99..10B9C ; Psalter_Pahlavi
    "Zzzz",  # 10B9D..10BA8 ; Unknown
    "Phlp",  # 10BA9..10BAF ; Psalter_Pahlavi
    "Zzzz",  # 10BB0..10BFF ; Unknown
    "Orkh",  # 10C00..10C48 ; Old_Turkic
    "Zzzz",  # 10C49..10C7F ; Unknown
    "Hung",  # 10C80..10CB2 ; Old_Hungarian
    "Zzzz",  # 10CB3..10CBF ; Unknown
    "Hung",  # 10CC0..10CF2 ; Old_Hungarian
    "Zzzz",  # 10CF3..10CF9 ; Unknown
    "Hung",  # 10CFA..10CFF ; Old_Hungarian
    "Rohg",  # 10D00..10D27 ; Hanifi_Rohingya
    "Zzzz",  # 10D28..10D2F ; Unknown
    "Rohg",  # 10D30..10D39 ; Hanifi_Rohingya
    "Zzzz",  # 10D3A..10D3F ; Unknown
    "Gara",  # 10D40..10D65 ; Garay
    "Zzzz",  # 10D66..10D68 ; Unknown
    "Gara",  # 10D69..10D85 ; Garay
    "Zzzz",  # 10D86..10D8D ; Unknown
    "Gara",  # 10D8E..10D8F ; Garay
    "Zzzz",  # 10D90..10E5F ; Unknown
    "Arab",  # 10E60..10E7E ; Arabic
    "Zzzz",  # 10E7F..10E7F ; Unknown
    "Yezi",  # 10E80..10EA9 ; Yezidi
    "Zzzz",  # 10EAA..10EAA ; Unknown
    "Yezi",  # 10EAB..10EAD ; Yezidi
    "Zzzz",  # 10EAE..10EAF ; Unknown
    "Yezi",  # 10EB0..10EB1 ; Yezidi
    "Zzzz",  # 10EB2..10EC1 ; Unknown
    "Arab",  # 10EC2..10EC4 ; Arabic
    "Zzzz",  # 10EC5..10EFB ; Unknown
    "Arab",  # 10EFC..10EFF ; Arabic
    "Sogo",  # 10F00..10F27 ; Old_Sogdian
    "Zzzz",  # 10F28..10F2F ; Unknown
    "Sogd",  # 10F30..10F59 ; Sogdian
    "Zzzz",  # 10F5A..10F6F ; Unknown
    "Ougr",  # 10F70..10F89 ; Old_Uyghur
    "Zzzz",  # 10F8A..10FAF ; Unknown
    "Chrs",  # 10FB0..10FCB ; Chorasmian
    "Zzzz",  # 10FCC..10FDF ; Unknown
    "Elym",  # 10FE0..10FF6 ; Elymaic
    "Zzzz",  # 10FF7..10FFF ; Unknown
    "Brah",  # 11000..1104D ; Brahmi
    "Zzzz",  # 1104E..11051 ; Unknown
    "Brah",  # 11052..11075 ; Brahmi
    "Zzzz",  # 11076..1107E ; Unknown
    "Brah",  # 1107F..1107F ; Brahmi
    "Kthi",  # 11080..110C2 ; Kaithi
    "Zzzz",  # 110C3..110CC ; Unknown
    "Kthi",  # 110CD..110CD ; Kaithi
    "Zzzz",  # 110CE..110CF ; Unknown
    "Sora",  # 110D0..110E8 ; Sora_Sompeng
    "Zzzz",  # 110E9..110EF ; Unknown
    "Sora",  # 110F0..110F9 ; Sora_Sompeng
    "Zzzz",  # 110FA..110FF ; Unknown
    "Cakm",  # 11100..11134 ; Chakma
    "Zzzz",  # 11135..11135 ; Unknown
    "Cakm",  # 11136..11147 ; Chakma
    "Zzzz",  # 11148..1114F ; Unknown
    "Mahj",  # 11150..11176 ; Mahajani
    "Zzzz",  # 11177..1117F ; Unknown
    "Shrd",  # 11180..111DF ; Sharada
    "Zzzz",  # 111E0..111E0 ; Unknown
    "Sinh",  # 111E1..111F4 ; Sinhala
    "Zzzz",  # 111F5..111FF ; Unknown
    "Khoj",  # 11200..11211 ; Khojki
    "Zzzz",  # 11212..11212 ; Unknown
    "Khoj",  # 11213..11241 ; Khojki
    "Zzzz",  # 11242..1127F ; Unknown
    "Mult",  # 11280..11286 ; Multani
    "Zzzz",  # 11287..11287 ; Unknown
    "Mult",  # 11288..11288 ; Multani
    "Zzzz",  # 11289..11289 ; Unknown
    "Mult",  # 1128A..1128D ; Multani
    "Zzzz",  # 1128E..1128E ; Unknown
    "Mult",  # 1128F..1129D ; Multani
    "Zzzz",  # 1129E..1129E ; Unknown
    "Mult",  # 1129F..112A9 ; Multani
    "Zzzz",  # 112AA..112AF ; Unknown
    "Sind",  # 112B0..112EA ; Khudawadi
    "Zzzz",  # 112EB..112EF ; Unknown
    "Sind",  # 112F0..112F9 ; Khudawadi
    "Zzzz",  # 112FA..112FF ; Unknown
    "Gran",  # 11300..11303 ; Grantha
    "Zzzz",  # 11304..11304 ; Unknown
    "Gran",  # 11305..1130C ; Grantha
    "Zzzz",  # 1130D..1130E ; Unknown
    "Gran",  # 1130F..11310 ; Grantha
    "Zzzz",  # 11311..11312 ; Unknown
    "Gran",  # 11313..11328 ; Grantha
    "Zzzz",  # 11329..11329 ; Unknown
    "Gran",  # 1132A..11330 ; Grantha
    "Zzzz",  # 11331..11331 ; Unknown
    "Gran",  # 11332..11333 ; Grantha
    "Zzzz",  # 11334..11334 ; Unknown
    "Gran",  # 11335..11339 ; Grantha
    "Zzzz",  # 1133A..1133A ; Unknown
    "Zinh",  # 1133B..1133B ; Inherited
    "Gran",  # 1133C..11344 ; Grantha
    "Zzzz",  # 11345..11346 ; Unknown
    "Gran",  # 11347..11348 ; Grantha
    "Zzzz",  # 11349..1134A ; Unknown
    "Gran",  # 1134B..1134D ; Grantha
    "Zzzz",  # 1134E..1134F ; Unknown
    "Gran",  # 11350..11350 ; Grantha
    "Zzzz",  # 11351..11356 ; Unknown
    "Gran",  # 11357..11357 ; Grantha
    "Zzzz",  # 11358..1135C ; Unknown
    "Gran",  # 1135D..11363 ; Grantha
    "Zzzz",  # 11364..11365 ; Unknown
    "Gran",  # 11366..1136C ; Grantha
    "Zzzz",  # 1136D..1136F ; Unknown
    "Gran",  # 11370..11374 ; Grantha
    "Zzzz",  # 11375..1137F ; Unknown
    "Tutg",  # 11380..11389 ; Tulu_Tigalari
    "Zzzz",  # 1138A..1138A ; Unknown
    "Tutg",  # 1138B..1138B ; Tulu_Tigalari
    "Zzzz",  # 1138C..1138D ; Unknown
    "Tutg",  # 1138E..1138E ; Tulu_Tigalari
    "Zzzz",  # 1138F..1138F ; Unknown
    "Tutg",  # 11390..113B5 ; Tulu_Tigalari
    "Zzzz",  # 113B6..113B6 ; Unknown
    "Tutg",  # 113B7..113C0 ; Tulu_Tigalari
    "Zzzz",  # 113C1..113C1 ; Unknown
    "Tutg",  # 113C2..113C2 ; Tulu_Tigalari
    "Zzzz",  # 113C3..113C4 ; Unknown
    "Tutg",  # 113C5..113C5 ; Tulu_Tigalari
    "Zzzz",  # 113C6..113C6 ; Unknown
    "Tutg",  # 113C7..113CA ; Tulu_Tigalari
    "Zzzz",  # 113CB..113CB ; Unknown
    "Tutg",  # 113CC..113D5 ; Tulu_Tigalari
    "Zzzz",  # 113D6..113D6 ; Unknown
    "Tutg",  # 113D7..113D8 ; Tulu_Tigalari
    "Zzzz",  # 113D9..113E0 ; Unknown
    "Tutg",  # 113E1..113E2 ; Tulu_Tigalari
    "Zzzz",  # 113E3..113FF ; Unknown
    "Newa",  # 11400..1145B ; Newa
    "Zzzz",  # 1145C..1145C ; Unknown
    "Newa",  # 1145D..11461 ; Newa
    "Zzzz",  # 11462..1147F ; Unknown
    "Tirh",  # 11480..114C7 ; Tirhuta
    "Zzzz",  # 114C8..114CF ; Unknown
    "Tirh",  # 114D0..114D9 ; Tirhuta
    "Zzzz",  # 114DA..1157F ; Unknown
    "Sidd",  # 11580..115B5 ; Siddham
    "Zzzz",  # 115B6..115B7 ; Unknown
    "Sidd",  # 115B8..115DD ; Siddham
    "Zzzz",  # 115DE..115FF ; Unknown
    "Modi",  # 11600..11644 ; Modi
    "Zzzz",  # 11645..1164F ; Unknown
    "Modi",  # 11650..11659 ; Modi
    "Zzzz",  # 1165A..1165F ; Unknown
    "Mong",  # 11660..1166C ; Mongolian
    "Zzzz",  # 1166D..1167F ; Unknown
    "Takr",  # 11680..116B9 ; Takri
    "Zzzz",  # 116BA..116BF ; Unknown
    "Takr",  # 116C0..116C9 ; Takri
    "Zzzz",  # 116CA..116CF ; Unknown
    "Mymr",  # 116D0..116E3 ; Myanmar
    "Zzzz",  # 116E4..116FF ; Unknown
    "Ahom",  # 11700..1171A ; Ahom
    "Zzzz",  # 1171B..1171C ; Unknown
    "Ahom",  # 1171D..1172B ; Ahom
    "Zzzz",  # 1172C..1172F ; Unknown
    "Ahom",  # 11730..11746 ; Ahom
    "Zzzz",  # 11747..117FF ; Unknown
    "Dogr",  # 11800..1183B ; Dogra
    "Zzzz",  # 1183C..1189F ; Unknown
    "Wara",  # 118A0..118F2 ; Warang_Citi
    "Zzzz",  # 118F3..118FE ; Unknown
    "Wara",  # 118FF..118FF ; Warang_Citi
    "Diak",  # 11900..11906 ; Dives_Akuru
    "Zzzz",  # 11907..11908 ; Unknown
    "Diak",  # 11909..11909 ; Dives_Akuru
    "Zzzz",  # 1190A..1190B ; Unknown
    "Diak",  # 1190C..11913 ; Dives_Akuru
    "Zzzz",  # 11914..11914 ; Unknown
    "Diak",  # 11915..11916 ; Dives_Akuru
    "Zzzz",  # 11917..11917 ; Unknown
    "Diak",  # 11918..11935 ; Dives_Akuru
    "Zzzz",  # 11936..11936 ; Unknown
    "Diak",  # 11937..11938 ; Dives_Akuru
    "Zzzz",  # 11939..1193A ; Unknown
    "Diak",  # 1193B..11946 ; Dives_Akuru
    "Zzzz",  # 11947..1194F ; Unknown
    "Diak",  # 11950..11959 ; Dives_Akuru
    "Zzzz",  # 1195A..1199F ; Unknown
    "Nand",  # 119A0..119A7 ; Nandinagari
    "Zzzz",  # 119A8..119A9 ; Unknown
    "Nand",  # 119AA..119D7 ; Nandinagari
    "Zzzz",  # 119D8..119D9 ; Unknown
    "Nand",  # 119DA..119E4 ; Nandinagari
    "Zzzz",  # 119E5..119FF ; Unknown
    "Zanb",  # 11A00..11A47 ; Zanabazar_Square
    "Zzzz",  # 11A48..11A4F ; Unknown
    "Soyo",  # 11A50..11AA2 ; Soyombo
    "Zzzz",  # 11AA3..11AAF ; Unknown
    "Cans",  # 11AB0..11ABF ; Canadian_Aboriginal
    "Pauc",  # 11AC0..11AF8 ; Pau_Cin_Hau
    "Zzzz",  # 11AF9..11AFF ; Unknown
    "Deva",  # 11B00..11B09 ; Devanagari
    "Zzzz",  # 11B0A..11BBF ; Unknown
    "Sunu",  # 11BC0..11BE1 ; Sunuwar
    "Zzzz",  # 11BE2..11BEF ; Unknown
    "Sunu",  # 11BF0..11BF9 ; Sunuwar
    "Zzzz",  # 11BFA..11BFF ; Unknown
    "Bhks",  # 11C00..11C08 ; Bhaiksuki
    "Zzzz",  # 11C09..11C09 ; Unknown
    "Bhks",  # 11C0A..11C36 ; Bhaiksuki
    "Zzzz",  # 11C37..11C37 ; Unknown
    "Bhks",  # 11C38..11C45 ; Bhaiksuki
    "Zzzz",  # 11C46..11C4F ; Unknown
    "Bhks",  # 11C50..11C6C ; Bhaiksuki
    "Zzzz",  # 11C6D..11C6F ; Unknown
    "Marc",  # 11C70..11C8F ; Marchen
    "Zzzz",  # 11C90..11C91 ; Unknown
    "Marc",  # 11C92..11CA7 ; Marchen
    "Zzzz",  # 11CA8..11CA8 ; Unknown
    "Marc",  # 11CA9..11CB6 ; Marchen
    "Zzzz",  # 11CB7..11CFF ; Unknown
    "Gonm",  # 11D00..11D06 ; Masaram_Gondi
    "Zzzz",  # 11D07..11D07 ; Unknown
    "Gonm",  # 11D08..11D09 ; Masaram_Gondi
    "Zzzz",  # 11D0A..11D0A ; Unknown
    "Gonm",  # 11D0B..11D36 ; Masaram_Gondi
    "Zzzz",  # 11D37..11D39 ; Unknown
    "Gonm",  # 11D3A..11D3A ; Masaram_Gondi
    "Zzzz",  # 11D3B..11D3B ; Unknown
    "Gonm",  # 11D3C..11D3D ; Masaram_Gondi
    "Zzzz",  # 11D3E..11D3E ; Unknown
    "Gonm",  # 11D3F..11D47 ; Masaram_Gondi
    "Zzzz",  # 11D48..11D4F ; Unknown
    "Gonm",  # 11D50..11D59 ; Masaram_Gondi
    "Zzzz",  # 11D5A..11D5F ; Unknown
    "Gong",  # 11D60..11D65 ; Gunjala_Gondi
    "Zzzz",  # 11D66..11D66 ; Unknown
    "Gong",  # 11D67..11D68 ; Gunjala_Gondi
    "Zzzz",  # 11D69..11D69 ; Unknown
    "Gong",  # 11D6A..11D8E ; Gunjala_Gondi
    "Zzzz",  # 11D8F..11D8F ; Unknown
    "Gong",  # 11D90..11D91 ; Gunjala_Gondi
    "Zzzz",  # 11D92..11D92 ; Unknown
    "Gong",  # 11D93..11D98 ; Gunjala_Gondi
    "Zzzz",  # 11D99..11D9F ; Unknown
    "Gong",  # 11DA0..11DA9 ; Gunjala_Gondi
    "Zzzz",  # 11DAA..11EDF ; Unknown
    "Maka",  # 11EE0..11EF8 ; Makasar
    "Zzzz",  # 11EF9..11EFF ; Unknown
    "Kawi",  # 11F00..11F10 ; Kawi
    "Zzzz",  # 11F11..11F11 ; Unknown
    "Kawi",  # 11F12..11F3A ; Kawi
    "Zzzz",  # 11F3B..11F3D ; Unknown
    "Kawi",  # 11F3E..11F5A ; Kawi
    "Zzzz",  # 11F5B..11FAF ; Unknown
    "Lisu",  # 11FB0..11FB0 ; Lisu
    "Zzzz",  # 11FB1..11FBF ; Unknown
    "Taml",  # 11FC0..11FF1 ; Tamil
    "Zzzz",  # 11FF2..11FFE ; Unknown
    "Taml",  # 11FFF..11FFF ; Tamil
    "Xsux",  # 12000..12399 ; Cuneiform
    "Zzzz",  # 1239A..123FF ; Unknown
    "Xsux",  # 12400..1246E ; Cuneiform
    "Zzzz",  # 1246F..1246F ; Unknown
    "Xsux",  # 12470..12474 ; Cuneiform
    "Zzzz",  # 12475..1247F ; Unknown
    "Xsux",  # 12480..12543 ; Cuneiform
    "Zzzz",  # 12544..12F8F ; Unknown
    "Cpmn",  # 12F90..12FF2 ; Cypro_Minoan
    "Zzzz",  # 12FF3..12FFF ; Unknown
    "Egyp",  # 13000..13455 ; Egyptian_Hieroglyphs
    "Zzzz",  # 13456..1345F ; Unknown
    "Egyp",  # 13460..143FA ; Egyptian_Hieroglyphs
    "Zzzz",  # 143FB..143FF ; Unknown
    "Hluw",  # 14400..14646 ; Anatolian_Hieroglyphs
    "Zzzz",  # 14647..160FF ; Unknown
    "Gukh",  # 16100..16139 ; Gurung_Khema
    "Zzzz",  # 1613A..167FF ; Unknown
    "Bamu",  # 16800..16A38 ; Bamum
    "Zzzz",  # 16A39..16A3F ; Unknown
    "Mroo",  # 16A40..16A5E ; Mro
    "Zzzz",  # 16A5F..16A5F ; Unknown
    "Mroo",  # 16A60..16A69 ; Mro
    "Zzzz",  # 16A6A..16A6D ; Unknown
    "Mroo",  # 16A6E..16A6F ; Mro
    "Tnsa",  # 16A70..16ABE ; Tangsa
    "Zzzz",  # 16ABF..16ABF ; Unknown
    "Tnsa",  # 16AC0..16AC9 ; Tangsa
    "Zzzz",  # 16ACA..16ACF ; Unknown
    "Bass",  # 16AD0..16AED ; Bassa_Vah
    "Zzzz",  # 16AEE..16AEF ; Unknown
    "Bass",  # 16AF0..16AF5 ; Bassa_Vah
    "Zzzz",  # 16AF6..16AFF ; Unknown
    "Hmng",  # 16B00..16B45 ; Pahawh_Hmong
    "Zzzz",  # 16B46..16B4F ; Unknown
    "Hmng",  # 16B50..16B59 ; Pahawh_Hmong
    "Zzzz",  # 16B5A..16B5A ; Unknown
    "Hmng",  # 16B5B..16B61 ; Pahawh_Hmong
    "Zzzz",  # 16B62..16B62 ; Unknown
    "Hmng",  # 16B63..16B77 ; Pahawh_Hmong
    "Zzzz",  # 16B78..16B7C ; Unknown
    "Hmng",  # 16B7D..16B8F ; Pahawh_Hmong
    "Zzzz",  # 16B90..16D3F ; Unknown
    "Krai",  # 16D40..16D79 ; Kirat_Rai
    "Zzzz",  # 16D7A..16E3F ; Unknown
    "Medf",  # 16E40..16E9A ; Medefaidrin
    "Zzzz",  # 16E9B..16EFF ; Unknown
    "Plrd",  # 16F00..16F4A ; Miao
    "Zzzz",  # 16F4B..16F4E ; Unknown
    "Plrd",  # 16F4F..16F87 ; Miao
    "Zzzz",  # 16F88..16F8E ; Unknown
    "Plrd",  # 16F8F..16F9F ; Miao
    "Zzzz",  # 16FA0..16FDF ; Unknown
    "Tang",  # 16FE0..16FE0 ; Tangut
    "Nshu",  # 16FE1..16FE1 ; Nushu
    "Hani",  # 16FE2..16FE3 ; Han
    "Kits",  # 16FE4..16FE4 ; Khitan_Small_Script
    "Zzzz",  # 16FE5..16FEF ; Unknown
    "Hani",  # 16FF0..16FF1 ; Han
    "Zzzz",  # 16FF2..16FFF ; Unknown
    "Tang",  # 17000..187F7 ; Tangut
    "Zzzz",  # 187F8..187FF ; Unknown
    "Tang",  # 18800..18AFF ; Tangut
    "Kits",  # 18B00..18CD5 ; Khitan_Small_Script
    "Zzzz",  # 18CD6..18CFE ; Unknown
    "Kits",  # 18CFF..18CFF ; Khitan_Small_Script
    "Tang",  # 18D00..18D08 ; Tangut
    "Zzzz",  # 18D09..1AFEF ; Unknown
    "Kana",  # 1AFF0..1AFF3 ; Katakana
    "Zzzz",  # 1AFF4..1AFF4 ; Unknown
    "Kana",  # 1AFF5..1AFFB ; Katakana
    "Zzzz",  # 1AFFC..1AFFC ; Unknown
    "Kana",  # 1AFFD..1AFFE ; Katakana
    "Zzzz",  # 1AFFF..1AFFF ; Unknown
    "Kana",  # 1B000..1B000 ; Katakana
    "Hira",  # 1B001..1B11F ; Hiragana
    "Kana",  # 1B120..1B122 ; Katakana
    "Zzzz",  # 1B123..1B131 ; Unknown
    "Hira",  # 1B132..1B132 ; Hiragana
    "Zzzz",  # 1B133..1B14F ; Unknown
    "Hira",  # 1B150..1B152 ; Hiragana
    "Zzzz",  # 1B153..1B154 ; Unknown
    "Kana",  # 1B155..1B155 ; Katakana
    "Zzzz",  # 1B156..1B163 ; Unknown
    "Kana",  # 1B164..1B167 ; Katakana
    "Zzzz",  # 1B168..1B16F ; Unknown
    "Nshu",  # 1B170..1B2FB ; Nushu
    "Zzzz",  # 1B2FC..1BBFF ; Unknown
    "Dupl",  # 1BC00..1BC6A ; Duployan
    "Zzzz",  # 1BC6B..1BC6F ; Unknown
    "Dupl",  # 1BC70..1BC7C ; Duployan
    "Zzzz",  # 1BC7D..1BC7F ; Unknown
    "Dupl",  # 1BC80..1BC88 ; Duployan
    "Zzzz",  # 1BC89..1BC8F ; Unknown
    "Dupl",  # 1BC90..1BC99 ; Duployan
    "Zzzz",  # 1BC9A..1BC9B ; Unknown
    "Dupl",  # 1BC9C..1BC9F ; Duployan
    "Zyyy",  # 1BCA0..1BCA3 ; Common
    "Zzzz",  # 1BCA4..1CBFF ; Unknown
    "Zyyy",  # 1CC00..1CCF9 ; Common
    "Zzzz",  # 1CCFA..1CCFF ; Unknown
    "Zyyy",  # 1CD00..1CEB3 ; Common
    "Zzzz",  # 1CEB4..1CEFF ; Unknown
    "Zinh",  # 1CF00..1CF2D ; Inherited
    "Zzzz",  # 1CF2E..1CF2F ; Unknown
    "Zinh",  # 1CF30..1CF46 ; Inherited
    "Zzzz",  # 1CF47..1CF4F ; Unknown
    "Zyyy",  # 1CF50..1CFC3 ; Common
    "Zzzz",  # 1CFC4..1CFFF ; Unknown
    "Zyyy",  # 1D000..1D0F5 ; Common
    "Zzzz",  # 1D0F6..1D0FF ; Unknown
    "Zyyy",  # 1D100..1D126 ; Common
    "Zzzz",  # 1D127..1D128 ; Unknown
    "Zyyy",  # 1D129..1D166 ; Common
    "Zinh",  # 1D167..1D169 ; Inherited
    "Zyyy",  # 1D16A..1D17A ; Common
    "Zinh",  # 1D17B..1D182 ; Inherited
    "Zyyy",  # 1D183..1D184 ; Common
    "Zinh",  # 1D185..1D18B ; Inherited
    "Zyyy",  # 1D18C..1D1A9 ; Common
    "Zinh",  # 1D1AA..1D1AD ; Inherited
    "Zyyy",  # 1D1AE..1D1EA ; Common
    "Zzzz",  # 1D1EB..1D1FF ; Unknown
    "Grek",  # 1D200..1D245 ; Greek
    "Zzzz",  # 1D246..1D2BF ; Unknown
    "Zyyy",  # 1D2C0..1D2D3 ; Common
    "Zzzz",  # 1D2D4..1D2DF ; Unknown
    "Zyyy",  # 1D2E0..1D2F3 ; Common
    "Zzzz",  # 1D2F4..1D2FF ; Unknown
    "Zyyy",  # 1D300..1D356 ; Common
    "Zzzz",  # 1D357..1D35F ; Unknown
    "Zyyy",  # 1D360..1D378 ; Common
    "Zzzz",  # 1D379..1D3FF ; Unknown
    "Zyyy",  # 1D400..1D454 ; Common
    "Zzzz",  # 1D455..1D455 ; Unknown
    "Zyyy",  # 1D456..1D49C ; Common
    "Zzzz",  # 1D49D..1D49D ; Unknown
    "Zyyy",  # 1D49E..1D49F ; Common
    "Zzzz",  # 1D4A0..1D4A1 ; Unknown
    "Zyyy",  # 1D4A2..1D4A2 ; Common
    "Zzzz",  # 1D4A3..1D4A4 ; Unknown
    "Zyyy",  # 1D4A5..1D4A6 ; Common
    "Zzzz",  # 1D4A7..1D4A8 ; Unknown
    "Zyyy",  # 1D4A9..1D4AC ; Common
    "Zzzz",  # 1D4AD..1D4AD ; Unknown
    "Zyyy",  # 1D4AE..1D4B9 ; Common
    "Zzzz",  # 1D4BA..1D4BA ; Unknown
    "Zyyy",  # 1D4BB..1D4BB ; Common
    "Zzzz",  # 1D4BC..1D4BC ; Unknown
    "Zyyy",  # 1D4BD..1D4C3 ; Common
    "Zzzz",  # 1D4C4..1D4C4 ; Unknown
    "Zyyy",  # 1D4C5..1D505 ; Common
    "Zzzz",  # 1D506..1D506 ; Unknown
    "Zyyy",  # 1D507..1D50A ; Common
    "Zzzz",  # 1D50B..1D50C ; Unknown
    "Zyyy",  # 1D50D..1D514 ; Common
    "Zzzz",  # 1D515..1D515 ; Unknown
    "Zyyy",  # 1D516..1D51C ; Common
    "Zzzz",  # 1D51D..1D51D ; Unknown
    "Zyyy",  # 1D51E..1D539 ; Common
    "Zzzz",  # 1D53A..1D53A ; Unknown
    "Zyyy",  # 1D53B..1D53E ; Common
    "Zzzz",  # 1D53F..1D53F ; Unknown
    "Zyyy",  # 1D540..1D544 ; Common
    "Zzzz",  # 1D545..1D545 ; Unknown
    "Zyyy",  # 1D546..1D546 ; Common
    "Zzzz",  # 1D547..1D549 ; Unknown
    "Zyyy",  # 1D54A..1D550 ; Common
    "Zzzz",  # 1D551..1D551 ; Unknown
    "Zyyy",  # 1D552..1D6A5 ; Common
    "Zzzz",  # 1D6A6..1D6A7 ; Unknown
    "Zyyy",  # 1D6A8..1D7CB ; Common
    "Zzzz",  # 1D7CC..1D7CD ; Unknown
    "Zyyy",  # 1D7CE..1D7FF ; Common
    "Sgnw",  # 1D800..1DA8B ; SignWriting
    "Zzzz",  # 1DA8C..1DA9A ; Unknown
    "Sgnw",  # 1DA9B..1DA9F ; SignWriting
    "Zzzz",  # 1DAA0..1DAA0 ; Unknown
    "Sgnw",  # 1DAA1..1DAAF ; SignWriting
    "Zzzz",  # 1DAB0..1DEFF ; Unknown
    "Latn",  # 1DF00..1DF1E ; Latin
    "Zzzz",  # 1DF1F..1DF24 ; Unknown
    "Latn",  # 1DF25..1DF2A ; Latin
    "Zzzz",  # 1DF2B..1DFFF ; Unknown
    "Glag",  # 1E000..1E006 ; Glagolitic
    "Zzzz",  # 1E007..1E007 ; Unknown
    "Glag",  # 1E008..1E018 ; Glagolitic
    "Zzzz",  # 1E019..1E01A ; Unknown
    "Glag",  # 1E01B..1E021 ; Glagolitic
    "Zzzz",  # 1E022..1E022 ; Unknown
    "Glag",  # 1E023..1E024 ; Glagolitic
    "Zzzz",  # 1E025..1E025 ; Unknown
    "Glag",  # 1E026..1E02A ; Glagolitic
    "Zzzz",  # 1E02B..1E02F ; Unknown
    "Cyrl",  # 1E030..1E06D ; Cyrillic
    "Zzzz",  # 1E06E..1E08E ; Unknown
    "Cyrl",  # 1E08F..1E08F ; Cyrillic
    "Zzzz",  # 1E090..1E0FF ; Unknown
    "Hmnp",  # 1E100..1E12C ; Nyiakeng_Puachue_Hmong
    "Zzzz",  # 1E12D..1E12F ; Unknown
    "Hmnp",  # 1E130..1E13D ; Nyiakeng_Puachue_Hmong
    "Zzzz",  # 1E13E..1E13F ; Unknown
    "Hmnp",  # 1E140..1E149 ; Nyiakeng_Puachue_Hmong
    "Zzzz",  # 1E14A..1E14D ; Unknown
    "Hmnp",  # 1E14E..1E14F ; Nyiakeng_Puachue_Hmong
    "Zzzz",  # 1E150..1E28F ; Unknown
    "Toto",  # 1E290..1E2AE ; Toto
    "Zzzz",  # 1E2AF..1E2BF ; Unknown
    "Wcho",  # 1E2C0..1E2F9 ; Wancho
    "Zzzz",  # 1E2FA..1E2FE ; Unknown
    "Wcho",  # 1E2FF..1E2FF ; Wancho
    "Zzzz",  # 1E300..1E4CF ; Unknown
    "Nagm",  # 1E4D0..1E4F9 ; Nag_Mundari
    "Zzzz",  # 1E4FA..1E5CF ; Unknown
    "Onao",  # 1E5D0..1E5FA ; Ol_Onal
    "Zzzz",  # 1E5FB..1E5FE ; Unknown
    "Onao",  # 1E5FF..1E5FF ; Ol_Onal
    "Zzzz",  # 1E600..1E7DF ; Unknown
    "Ethi",  # 1E7E0..1E7E6 ; Ethiopic
    "Zzzz",  # 1E7E7..1E7E7 ; Unknown
    "Ethi",  # 1E7E8..1E7EB ; Ethiopic
    "Zzzz",  # 1E7EC..1E7EC ; Unknown
    "Ethi",  # 1E7ED..1E7EE ; Ethiopic
    "Zzzz",  # 1E7EF..1E7EF ; Unknown
    "Ethi",  # 1E7F0..1E7FE ; Ethiopic
    "Zzzz",  # 1E7FF..1E7FF ; Unknown
    "Mend",  # 1E800..1E8C4 ; Mende_Kikakui
    "Zzzz",  # 1E8C5..1E8C6 ; Unknown
    "Mend",  # 1E8C7..1E8D6 ; Mende_Kikakui
    "Zzzz",  # 1E8D7..1E8FF ; Unknown
    "Adlm",  # 1E900..1E94B ; Adlam
    "Zzzz",  # 1E94C..1E94F ; Unknown
    "Adlm",  # 1E950..1E959 ; Adlam
    "Zzzz",  # 1E95A..1E95D ; Unknown
    "Adlm",  # 1E95E..1E95F ; Adlam
    "Zzzz",  # 1E960..1EC70 ; Unknown
    "Zyyy",  # 1EC71..1ECB4 ; Common
    "Zzzz",  # 1ECB5..1ED00 ; Unknown
    "Zyyy",  # 1ED01..1ED3D ; Common
    "Zzzz",  # 1ED3E..1EDFF ; Unknown
    "Arab",  # 1EE00..1EE03 ; Arabic
    "Zzzz",  # 1EE04..1EE04 ; Unknown
    "Arab",  # 1EE05..1EE1F ; Arabic
    "Zzzz",  # 1EE20..1EE20 ; Unknown
    "Arab",  # 1EE21..1EE22 ; Arabic
    "Zzzz",  # 1EE23..1EE23 ; Unknown
    "Arab",  # 1EE24..1EE24 ; Arabic
    "Zzzz",  # 1EE25..1EE26 ; Unknown
    "Arab",  # 1EE27..1EE27 ; Arabic
    "Zzzz",  # 1EE28..1EE28 ; Unknown
    "Arab",  # 1EE29..1EE32 ; Arabic
    "Zzzz",  # 1EE33..1EE33 ; Unknown
    "Arab",  # 1EE34..1EE37 ; Arabic
    "Zzzz",  # 1EE38..1EE38 ; Unknown
    "Arab",  # 1EE39..1EE39 ; Arabic
    "Zzzz",  # 1EE3A..1EE3A ; Unknown
    "Arab",  # 1EE3B..1EE3B ; Arabic
    "Zzzz",  # 1EE3C..1EE41 ; Unknown
    "Arab",  # 1EE42..1EE42 ; Arabic
    "Zzzz",  # 1EE43..1EE46 ; Unknown
    "Arab",  # 1EE47..1EE47 ; Arabic
    "Zzzz",  # 1EE48..1EE48 ; Unknown
    "Arab",  # 1EE49..1EE49 ; Arabic
    "Zzzz",  # 1EE4A..1EE4A ; Unknown
    "Arab",  # 1EE4B..1EE4B ; Arabic
    "Zzzz",  # 1EE4C..1EE4C ; Unknown
    "Arab",  # 1EE4D..1EE4F ; Arabic
    "Zzzz",  # 1EE50..1EE50 ; Unknown
    "Arab",  # 1EE51..1EE52 ; Arabic
    "Zzzz",  # 1EE53..1EE53 ; Unknown
    "Arab",  # 1EE54..1EE54 ; Arabic
    "Zzzz",  # 1EE55..1EE56 ; Unknown
    "Arab",  # 1EE57..1EE57 ; Arabic
    "Zzzz",  # 1EE58..1EE58 ; Unknown
    "Arab",  # 1EE59..1EE59 ; Arabic
    "Zzzz",  # 1EE5A..1EE5A ; Unknown
    "Arab",  # 1EE5B..1EE5B ; Arabic
    "Zzzz",  # 1EE5C..1EE5C ; Unknown
    "Arab",  # 1EE5D..1EE5D ; Arabic
    "Zzzz",  # 1EE5E..1EE5E ; Unknown
    "Arab",  # 1EE5F..1EE5F ; Arabic
    "Zzzz",  # 1EE60..1EE60 ; Unknown
    "Arab",  # 1EE61..1EE62 ; Arabic
    "Zzzz",  # 1EE63..1EE63 ; Unknown
    "Arab",  # 1EE64..1EE64 ; Arabic
    "Zzzz",  # 1EE65..1EE66 ; Unknown
    "Arab",  # 1EE67..1EE6A ; Arabic
    "Zzzz",  # 1EE6B..1EE6B ; Unknown
    "Arab",  # 1EE6C..1EE72 ; Arabic
    "Zzzz",  # 1EE73..1EE73 ; Unknown
    "Arab",  # 1EE74..1EE77 ; Arabic
    "Zzzz",  # 1EE78..1EE78 ; Unknown
    "Arab",  # 1EE79..1EE7C ; Arabic
    "Zzzz",  # 1EE7D..1EE7D ; Unknown
    "Arab",  # 1EE7E..1EE7E ; Arabic
    "Zzzz",  # 1EE7F..1EE7F ; Unknown
    "Arab",  # 1EE80..1EE89 ; Arabic
    "Zzzz",  # 1EE8A..1EE8A ; Unknown
    "Arab",  # 1EE8B..1EE9B ; Arabic
    "Zzzz",  # 1EE9C..1EEA0 ; Unknown
    "Arab",  # 1EEA1..1EEA3 ; Arabic
    "Zzzz",  # 1EEA4..1EEA4 ; Unknown
    "Arab",  # 1EEA5..1EEA9 ; Arabic
    "Zzzz",  # 1EEAA..1EEAA ; Unknown
    "Arab",  # 1EEAB..1EEBB ; Arabic
    "Zzzz",  # 1EEBC..1EEEF ; Unknown
    "Arab",  # 1EEF0..1EEF1 ; Arabic
    "Zzzz",  # 1EEF2..1EFFF ; Unknown
    "Zyyy",  # 1F000..1F02B ; Common
    "Zzzz",  # 1F02C..1F02F ; Unknown
    "Zyyy",  # 1F030..1F093 ; Common
    "Zzzz",  # 1F094..1F09F ; Unknown
    "Zyyy",  # 1F0A0..1F0AE ; Common
    "Zzzz",  # 1F0AF..1F0B0 ; Unknown
    "Zyyy",  # 1F0B1..1F0BF ; Common
    "Zzzz",  # 1F0C0..1F0C0 ; Unknown
    "Zyyy",  # 1F0C1..1F0CF ; Common
    "Zzzz",  # 1F0D0..1F0D0 ; Unknown
    "Zyyy",  # 1F0D1..1F0F5 ; Common
    "Zzzz",  # 1F0F6..1F0FF ; Unknown
    "Zyyy",  # 1F100..1F1AD ; Common
    "Zzzz",  # 1F1AE..1F1E5 ; Unknown
    "Zyyy",  # 1F1E6..1F1FF ; Common
    "Hira",  # 1F200..1F200 ; Hiragana
    "Zyyy",  # 1F201..1F202 ; Common
    "Zzzz",  # 1F203..1F20F ; Unknown
    "Zyyy",  # 1F210..1F23B ; Common
    "Zzzz",  # 1F23C..1F23F ; Unknown
    "Zyyy",  # 1F240..1F248 ; Common
    "Zzzz",  # 1F249..1F24F ; Unknown
    "Zyyy",  # 1F250..1F251 ; Common
    "Zzzz",  # 1F252..1F25F ; Unknown
    "Zyyy",  # 1F260..1F265 ; Common
    "Zzzz",  # 1F266..1F2FF ; Unknown
    "Zyyy",  # 1F300..1F6D7 ; Common
    "Zzzz",  # 1F6D8..1F6DB ; Unknown
    "Zyyy",  # 1F6DC..1F6EC ; Common
    "Zzzz",  # 1F6ED..1F6EF ; Unknown
    "Zyyy",  # 1F6F0..1F6FC ; Common
    "Zzzz",  # 1F6FD..1F6FF ; Unknown
    "Zyyy",  # 1F700..1F776 ; Common
    "Zzzz",  # 1F777..1F77A ; Unknown
    "Zyyy",  # 1F77B..1F7D9 ; Common
    "Zzzz",  # 1F7DA..1F7DF ; Unknown
    "Zyyy",  # 1F7E0..1F7EB ; Common
    "Zzzz",  # 1F7EC..1F7EF ; Unknown
    "Zyyy",  # 1F7F0..1F7F0 ; Common
    "Zzzz",  # 1F7F1..1F7FF ; Unknown
    "Zyyy",  # 1F800..1F80B ; Common
    "Zzzz",  # 1F80C..1F80F ; Unknown
    "Zyyy",  # 1F810..1F847 ; Common
    "Zzzz",  # 1F848..1F84F ; Unknown
    "Zyyy",  # 1F850..1F859 ; Common
    "Zzzz",  # 1F85A..1F85F ; Unknown
    "Zyyy",  # 1F860..1F887 ; Common
    "Zzzz",  # 1F888..1F88F ; Unknown
    "Zyyy",  # 1F890..1F8AD ; Common
    "Zzzz",  # 1F8AE..1F8AF ; Unknown
    "Zyyy",  # 1F8B0..1F8BB ; Common
    "Zzzz",  # 1F8BC..1F8BF ; Unknown
    "Zyyy",  # 1F8C0..1F8C1 ; Common
    "Zzzz",  # 1F8C2..1F8FF ; Unknown
    "Zyyy",  # 1F900..1FA53 ; Common
    "Zzzz",  # 1FA54..1FA5F ; Unknown
    "Zyyy",  # 1FA60..1FA6D ; Common
    "Zzzz",  # 1FA6E..1FA6F ; Unknown
    "Zyyy",  # 1FA70..1FA7C ; Common
    "Zzzz",  # 1FA7D..1FA7F ; Unknown
    "Zyyy",  # 1FA80..1FA89 ; Common
    "Zzzz",  # 1FA8A..1FA8E ; Unknown
    "Zyyy",  # 1FA8F..1FAC6 ; Common
    "Zzzz",  # 1FAC7..1FACD ; Unknown
    "Zyyy",  # 1FACE..1FADC ; Common
    "Zzzz",  # 1FADD..1FADE ; Unknown
    "Zyyy",  # 1FADF..1FAE9 ; Common
    "Zzzz",  # 1FAEA..1FAEF ; Unknown
    "Zyyy",  # 1FAF0..1FAF8 ; Common
    "Zzzz",  # 1FAF9..1FAFF ; Unknown
    "Zyyy",  # 1FB00..1FB92 ; Common
    "Zzzz",  # 1FB93..1FB93 ; Unknown
    "Zyyy",  # 1FB94..1FBF9 ; Common
    "Zzzz",  # 1FBFA..1FFFF ; Unknown
    "Hani",  # 20000..2A6DF ; Han
    "Zzzz",  # 2A6E0..2A6FF ; Unknown
    "Hani",  # 2A700..2B739 ; Han
    "Zzzz",  # 2B73A..2B73F ; Unknown
    "Hani",  # 2B740..2B81D ; Han
    "Zzzz",  # 2B81E..2B81F ; Unknown
    "Hani",  # 2B820..2CEA1 ; Han
    "Zzzz",  # 2CEA2..2CEAF ; Unknown
    "Hani",  # 2CEB0..2EBE0 ; Han
    "Zzzz",  # 2EBE1..2EBEF ; Unknown
    "Hani",  # 2EBF0..2EE5D ; Han
    "Zzzz",  # 2EE5E..2F7FF ; Unknown
    "Hani",  # 2F800..2FA1D ; Han
    "Zzzz",  # 2FA1E..2FFFF ; Unknown
    "Hani",  # 30000..3134A ; Han
    "Zzzz",  # 3134B..3134F ; Unknown
    "Hani",  # 31350..323AF ; Han
    "Zzzz",  # 323B0..E0000 ; Unknown
    "Zyyy",  # E0001..E0001 ; Common
    "Zzzz",  # E0002..E001F ; Unknown
    "Zyyy",  # E0020..E007F ; Common
    "Zzzz",  # E0080..E00FF ; Unknown
    "Zinh",  # E0100..E01EF ; Inherited
    "Zzzz",  # E01F0..10FFFF ; Unknown
]

NAMES = {
    "Adlm": "Adlam",
    "Aghb": "Caucasian_Albanian",
    "Ahom": "Ahom",
    "Arab": "Arabic",
    "Armi": "Imperial_Aramaic",
    "Armn": "Armenian",
    "Avst": "Avestan",
    "Bali": "Balinese",
    "Bamu": "Bamum",
    "Bass": "Bassa_Vah",
    "Batk": "Batak",
    "Beng": "Bengali",
    "Bhks": "Bhaiksuki",
    "Bopo": "Bopomofo",
    "Brah": "Brahmi",
    "Brai": "Braille",
    "Bugi": "Buginese",
    "Buhd": "Buhid",
    "Cakm": "Chakma",
    "Cans": "Canadian_Aboriginal",
    "Cari": "Carian",
    "Cham": "Cham",
    "Cher": "Cherokee",
    "Chrs": "Chorasmian",
    "Copt": "Coptic",
    "Cpmn": "Cypro_Minoan",
    "Cprt": "Cypriot",
    "Cyrl": "Cyrillic",
    "Deva": "Devanagari",
    "Diak": "Dives_Akuru",
    "Dogr": "Dogra",
    "Dsrt": "Deseret",
    "Dupl": "Duployan",
    "Egyp": "Egyptian_Hieroglyphs",
    "Elba": "Elbasan",
    "Elym": "Elymaic",
    "Ethi": "Ethiopic",
    "Gara": "Garay",
    "Geor": "Georgian",
    "Glag": "Glagolitic",
    "Gong": "Gunjala_Gondi",
    "Gonm": "Masaram_Gondi",
    "Goth": "Gothic",
    "Gran": "Grantha",
    "Grek": "Greek",
    "Gujr": "Gujarati",
    "Gukh": "Gurung_Khema",
    "Guru": "Gurmukhi",
    "Hang": "Hangul",
    "Hani": "Han",
    "Hano": "Hanunoo",
    "Hatr": "Hatran",
    "Hebr": "Hebrew",
    "Hira": "Hiragana",
    "Hluw": "Anatolian_Hieroglyphs",
    "Hmng": "Pahawh_Hmong",
    "Hmnp": "Nyiakeng_Puachue_Hmong",
    "Hrkt": "Katakana_Or_Hiragana",
    "Hung": "Old_Hungarian",
    "Ital": "Old_Italic",
    "Java": "Javanese",
    "Kali": "Kayah_Li",
    "Kana": "Katakana",
    "Kawi": "Kawi",
    "Khar": "Kharoshthi",
    "Khmr": "Khmer",
    "Khoj": "Khojki",
    "Kits": "Khitan_Small_Script",
    "Knda": "Kannada",
    "Krai": "Kirat_Rai",
    "Kthi": "Kaithi",
    "Lana": "Tai_Tham",
    "Laoo": "Lao",
    "Latn": "Latin",
    "Lepc": "Lepcha",
    "Limb": "Limbu",
    "Lina": "Linear_A",
    "Linb": "Linear_B",
    "Lisu": "Lisu",
    "Lyci": "Lycian",
    "Lydi": "Lydian",
    "Mahj": "Mahajani",
    "Maka": "Makasar",
    "Mand": "Mandaic",
    "Mani": "Manichaean",
    "Marc": "Marchen",
    "Medf": "Medefaidrin",
    "Mend": "Mende_Kikakui",
    "Merc": "Meroitic_Cursive",
    "Mero": "Meroitic_Hieroglyphs",
    "Mlym": "Malayalam",
    "Modi": "Modi",
    "Mong": "Mongolian",
    "Mroo": "Mro",
    "Mtei": "Meetei_Mayek",
    "Mult": "Multani",
    "Mymr": "Myanmar",
    "Nagm": "Nag_Mundari",
    "Nand": "Nandinagari",
    "Narb": "Old_North_Arabian",
    "Nbat": "Nabataean",
    "Newa": "Newa",
    "Nkoo": "Nko",
    "Nshu": "Nushu",
    "Ogam": "Ogham",
    "Olck": "Ol_Chiki",
    "Onao": "Ol_Onal",
    "Orkh": "Old_Turkic",
    "Orya": "Oriya",
    "Osge": "Osage",
    "Osma": "Osmanya",
    "Ougr": "Old_Uyghur",
    "Palm": "Palmyrene",
    "Pauc": "Pau_Cin_Hau",
    "Perm": "Old_Permic",
    "Phag": "Phags_Pa",
    "Phli": "Inscriptional_Pahlavi",
    "Phlp": "Psalter_Pahlavi",
    "Phnx": "Phoenician",
    "Plrd": "Miao",
    "Prti": "Inscriptional_Parthian",
    "Rjng": "Rejang",
    "Rohg": "Hanifi_Rohingya",
    "Runr": "Runic",
    "Samr": "Samaritan",
    "Sarb": "Old_South_Arabian",
    "Saur": "Saurashtra",
    "Sgnw": "SignWriting",
    "Shaw": "Shavian",
    "Shrd": "Sharada",
    "Sidd": "Siddham",
    "Sind": "Khudawadi",
    "Sinh": "Sinhala",
    "Sogd": "Sogdian",
    "Sogo": "Old_Sogdian",
    "Sora": "Sora_Sompeng",
    "Soyo": "Soyombo",
    "Sund": "Sundanese",
    "Sunu": "Sunuwar",
    "Sylo": "Syloti_Nagri",
    "Syrc": "Syriac",
    "Tagb": "Tagbanwa",
    "Takr": "Takri",
    "Tale": "Tai_Le",
    "Talu": "New_Tai_Lue",
    "Taml": "Tamil",
    "Tang": "Tangut",
    "Tavt": "Tai_Viet",
    "Telu": "Telugu",
    "Tfng": "Tifinagh",
    "Tglg": "Tagalog",
    "Thaa": "Thaana",
    "Thai": "Thai",
    "Tibt": "Tibetan",
    "Tirh": "Tirhuta",
    "Tnsa": "Tangsa",
    "Todr": "Todhri",
    "Toto": "Toto",
    "Tutg": "Tulu_Tigalari",
    "Ugar": "Ugaritic",
    "Vaii": "Vai",
    "Vith": "Vithkuqi",
    "Wara": "Warang_Citi",
    "Wcho": "Wancho",
    "Xpeo": "Old_Persian",
    "Xsux": "Cuneiform",
    "Yezi": "Yezidi",
    "Yiii": "Yi",
    "Zanb": "Zanabazar_Square",
    "Zinh": "Inherited",
    "Zyyy": "Common",
    "Zzzz": "Unknown",
}