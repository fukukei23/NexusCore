
# === NexusCore/tools\exports\export_20250803_114325\combined_44.py ===

# === NexusCore/openenv\Lib\site-packages\attr\_make.py ===
# SPDX-License-Identifier: MIT

from __future__ import annotations

import abc
import contextlib
import copy
import enum
import inspect
import itertools
import linecache
import sys
import types
import unicodedata

from collections.abc import Callable, Mapping
from functools import cached_property
from typing import Any, NamedTuple, TypeVar

# We need to import _compat itself in addition to the _compat members to avoid
# having the thread-local in the globals here.
from . import _compat, _config, setters
from ._compat import (
    PY_3_10_PLUS,
    PY_3_11_PLUS,
    PY_3_13_PLUS,
    _AnnotationExtractor,
    _get_annotations,
    get_generic_base,
)
from .exceptions import (
    DefaultAlreadySetError,
    FrozenInstanceError,
    NotAnAttrsClassError,
    UnannotatedAttributeError,
)


# This is used at least twice, so cache it here.
_OBJ_SETATTR = object.__setattr__
_INIT_FACTORY_PAT = "__attr_factory_%s"
_CLASSVAR_PREFIXES = (
    "typing.ClassVar",
    "t.ClassVar",
    "ClassVar",
    "typing_extensions.ClassVar",
)
# we don't use a double-underscore prefix because that triggers
# name mangling when trying to create a slot for the field
# (when slots=True)
_HASH_CACHE_FIELD = "_attrs_cached_hash"

_EMPTY_METADATA_SINGLETON = types.MappingProxyType({})

# Unique object for unequivocal getattr() defaults.
_SENTINEL = object()

_DEFAULT_ON_SETATTR = setters.pipe(setters.convert, setters.validate)


class _Nothing(enum.Enum):
    """
    Sentinel to indicate the lack of a value when `None` is ambiguous.

    If extending attrs, you can use ``typing.Literal[NOTHING]`` to show
    that a value may be ``NOTHING``.

    .. versionchanged:: 21.1.0 ``bool(NOTHING)`` is now False.
    .. versionchanged:: 22.2.0 ``NOTHING`` is now an ``enum.Enum`` variant.
    """

    NOTHING = enum.auto()

    def __repr__(self):
        return "NOTHING"

    def __bool__(self):
        return False


NOTHING = _Nothing.NOTHING
"""
Sentinel to indicate the lack of a value when `None` is ambiguous.

When using in 3rd party code, use `attrs.NothingType` for type annotations.
"""


class _CacheHashWrapper(int):
    """
    An integer subclass that pickles / copies as None

    This is used for non-slots classes with ``cache_hash=True``, to avoid
    serializing a potentially (even likely) invalid hash value. Since `None`
    is the default value for uncalculated hashes, whenever this is copied,
    the copy's value for the hash should automatically reset.

    See GH #613 for more details.
    """

    def __reduce__(self, _none_constructor=type(None), _args=()):  # noqa: B008
        return _none_constructor, _args


def attrib(
    default=NOTHING,
    validator=None,
    repr=True,
    cmp=None,
    hash=None,
    init=True,
    metadata=None,
    type=None,
    converter=None,
    factory=None,
    kw_only=False,
    eq=None,
    order=None,
    on_setattr=None,
    alias=None,
):
    """
    Create a new field / attribute on a class.

    Identical to `attrs.field`, except it's not keyword-only.

    Consider using `attrs.field` in new code (``attr.ib`` will *never* go away,
    though).

    ..  warning::

        Does **nothing** unless the class is also decorated with
        `attr.s` (or similar)!


    .. versionadded:: 15.2.0 *convert*
    .. versionadded:: 16.3.0 *metadata*
    .. versionchanged:: 17.1.0 *validator* can be a ``list`` now.
    .. versionchanged:: 17.1.0
       *hash* is `None` and therefore mirrors *eq* by default.
    .. versionadded:: 17.3.0 *type*
    .. deprecated:: 17.4.0 *convert*
    .. versionadded:: 17.4.0
       *converter* as a replacement for the deprecated *convert* to achieve
       consistency with other noun-based arguments.
    .. versionadded:: 18.1.0
       ``factory=f`` is syntactic sugar for ``default=attr.Factory(f)``.
    .. versionadded:: 18.2.0 *kw_only*
    .. versionchanged:: 19.2.0 *convert* keyword argument removed.
    .. versionchanged:: 19.2.0 *repr* also accepts a custom callable.
    .. deprecated:: 19.2.0 *cmp* Removal on or after 2021-06-01.
    .. versionadded:: 19.2.0 *eq* and *order*
    .. versionadded:: 20.1.0 *on_setattr*
    .. versionchanged:: 20.3.0 *kw_only* backported to Python 2
    .. versionchanged:: 21.1.0
       *eq*, *order*, and *cmp* also accept a custom callable
    .. versionchanged:: 21.1.0 *cmp* undeprecated
    .. versionadded:: 22.2.0 *alias*
    """
    eq, eq_key, order, order_key = _determine_attrib_eq_order(
        cmp, eq, order, True
    )

    if hash is not None and hash is not True and hash is not False:
        msg = "Invalid value for hash.  Must be True, False, or None."
        raise TypeError(msg)

    if factory is not None:
        if default is not NOTHING:
            msg = (
                "The `default` and `factory` arguments are mutually exclusive."
            )
            raise ValueError(msg)
        if not callable(factory):
            msg = "The `factory` argument must be a callable."
            raise ValueError(msg)
        default = Factory(factory)

    if metadata is None:
        metadata = {}

    # Apply syntactic sugar by auto-wrapping.
    if isinstance(on_setattr, (list, tuple)):
        on_setattr = setters.pipe(*on_setattr)

    if validator and isinstance(validator, (list, tuple)):
        validator = and_(*validator)

    if converter and isinstance(converter, (list, tuple)):
        converter = pipe(*converter)

    return _CountingAttr(
        default=default,
        validator=validator,
        repr=repr,
        cmp=None,
        hash=hash,
        init=init,
        converter=converter,
        metadata=metadata,
        type=type,
        kw_only=kw_only,
        eq=eq,
        eq_key=eq_key,
        order=order,
        order_key=order_key,
        on_setattr=on_setattr,
        alias=alias,
    )


def _compile_and_eval(
    script: str,
    globs: dict[str, Any] | None,
    locs: Mapping[str, object] | None = None,
    filename: str = "",
) -> None:
    """
    Evaluate the script with the given global (globs) and local (locs)
    variables.
    """
    bytecode = compile(script, filename, "exec")
    eval(bytecode, globs, locs)


def _linecache_and_compile(
    script: str,
    filename: str,
    globs: dict[str, Any] | None,
    locals: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    """
    Cache the script with _linecache_, compile it and return the _locals_.
    """

    locs = {} if locals is None else locals

    # In order of debuggers like PDB being able to step through the code,
    # we add a fake linecache entry.
    count = 1
    base_filename = filename
    while True:
        linecache_tuple = (
            len(script),
            None,
            script.splitlines(True),
            filename,
        )
        old_val = linecache.cache.setdefault(filename, linecache_tuple)
        if old_val == linecache_tuple:
            break

        filename = f"{base_filename[:-1]}-{count}>"
        count += 1

    _compile_and_eval(script, globs, locs, filename)

    return locs


def _make_attr_tuple_class(cls_name: str, attr_names: list[str]) -> type:
    """
    Create a tuple subclass to hold `Attribute`s for an `attrs` class.

    The subclass is a bare tuple with properties for names.

    class MyClassAttributes(tuple):
        __slots__ = ()
        x = property(itemgetter(0))
    """
    attr_class_name = f"{cls_name}Attributes"
    body = {}
    for i, attr_name in enumerate(attr_names):

        def getter(self, i=i):
            return self[i]

        body[attr_name] = property(getter)
    return type(attr_class_name, (tuple,), body)


# Tuple class for extracted attributes from a class definition.
# `base_attrs` is a subset of `attrs`.
class _Attributes(NamedTuple):
    attrs: type
    base_attrs: list[Attribute]
    base_attrs_map: dict[str, type]


def _is_class_var(annot):
    """
    Check whether *annot* is a typing.ClassVar.

    The string comparison hack is used to avoid evaluating all string
    annotations which would put attrs-based classes at a performance
    disadvantage compared to plain old classes.
    """
    annot = str(annot)

    # Annotation can be quoted.
    if annot.startswith(("'", '"')) and annot.endswith(("'", '"')):
        annot = annot[1:-1]

    return annot.startswith(_CLASSVAR_PREFIXES)


def _has_own_attribute(cls, attrib_name):
    """
    Check whether *cls* defines *attrib_name* (and doesn't just inherit it).
    """
    return attrib_name in cls.__dict__


def _collect_base_attrs(
    cls, taken_attr_names
) -> tuple[list[Attribute], dict[str, type]]:
    """
    Collect attr.ibs from base classes of *cls*, except *taken_attr_names*.
    """
    base_attrs = []
    base_attr_map = {}  # A dictionary of base attrs to their classes.

    # Traverse the MRO and collect attributes.
    for base_cls in reversed(cls.__mro__[1:-1]):
        for a in getattr(base_cls, "__attrs_attrs__", []):
            if a.inherited or a.name in taken_attr_names:
                continue

            a = a.evolve(inherited=True)  # noqa: PLW2901
            base_attrs.append(a)
            base_attr_map[a.name] = base_cls

    # For each name, only keep the freshest definition i.e. the furthest at the
    # back.  base_attr_map is fine because it gets overwritten with every new
    # instance.
    filtered = []
    seen = set()
    for a in reversed(base_attrs):
        if a.name in seen:
            continue
        filtered.insert(0, a)
        seen.add(a.name)

    return filtered, base_attr_map


def _collect_base_attrs_broken(cls, taken_attr_names):
    """
    Collect attr.ibs from base classes of *cls*, except *taken_attr_names*.

    N.B. *taken_attr_names* will be mutated.

    Adhere to the old incorrect behavior.

    Notably it collects from the front and considers inherited attributes which
    leads to the buggy behavior reported in #428.
    """
    base_attrs = []
    base_attr_map = {}  # A dictionary of base attrs to their classes.

    # Traverse the MRO and collect attributes.
    for base_cls in cls.__mro__[1:-1]:
        for a in getattr(base_cls, "__attrs_attrs__", []):
            if a.name in taken_attr_names:
                continue

            a = a.evolve(inherited=True)  # noqa: PLW2901
            taken_attr_names.add(a.name)
            base_attrs.append(a)
            base_attr_map[a.name] = base_cls

    return base_attrs, base_attr_map


def _transform_attrs(
    cls, these, auto_attribs, kw_only, collect_by_mro, field_transformer
) -> _Attributes:
    """
    Transform all `_CountingAttr`s on a class into `Attribute`s.

    If *these* is passed, use that and don't look for them on the class.

    If *collect_by_mro* is True, collect them in the correct MRO order,
    otherwise use the old -- incorrect -- order.  See #428.

    Return an `_Attributes`.
    """
    cd = cls.__dict__
    anns = _get_annotations(cls)

    if these is not None:
        ca_list = list(these.items())
    elif auto_attribs is True:
        ca_names = {
            name
            for name, attr in cd.items()
            if attr.__class__ is _CountingAttr
        }
        ca_list = []
        annot_names = set()
        for attr_name, type in anns.items():
            if _is_class_var(type):
                continue
            annot_names.add(attr_name)
            a = cd.get(attr_name, NOTHING)

            if a.__class__ is not _CountingAttr:
                a = attrib(a)
            ca_list.append((attr_name, a))

        unannotated = ca_names - annot_names
        if unannotated:
            raise UnannotatedAttributeError(
                "The following `attr.ib`s lack a type annotation: "
                + ", ".join(
                    sorted(unannotated, key=lambda n: cd.get(n).counter)
                )
                + "."
            )
    else:
        ca_list = sorted(
            (
                (name, attr)
                for name, attr in cd.items()
                if attr.__class__ is _CountingAttr
            ),
            key=lambda e: e[1].counter,
        )

    fca = Attribute.from_counting_attr
    own_attrs = [
        fca(attr_name, ca, anns.get(attr_name)) for attr_name, ca in ca_list
    ]

    if collect_by_mro:
        base_attrs, base_attr_map = _collect_base_attrs(
            cls, {a.name for a in own_attrs}
        )
    else:
        base_attrs, base_attr_map = _collect_base_attrs_broken(
            cls, {a.name for a in own_attrs}
        )

    if kw_only:
        own_attrs = [a.evolve(kw_only=True) for a in own_attrs]
        base_attrs = [a.evolve(kw_only=True) for a in base_attrs]

    attrs = base_attrs + own_attrs

    if field_transformer is not None:
        attrs = tuple(field_transformer(cls, attrs))

    # Check attr order after executing the field_transformer.
    # Mandatory vs non-mandatory attr order only matters when they are part of
    # the __init__ signature and when they aren't kw_only (which are moved to
    # the end and can be mandatory or non-mandatory in any order, as they will
    # be specified as keyword args anyway). Check the order of those attrs:
    had_default = False
    for a in (a for a in attrs if a.init is not False and a.kw_only is False):
        if had_default is True and a.default is NOTHING:
            msg = f"No mandatory attributes allowed after an attribute with a default value or factory.  Attribute in question: {a!r}"
            raise ValueError(msg)

        if had_default is False and a.default is not NOTHING:
            had_default = True

    # Resolve default field alias after executing field_transformer.
    # This allows field_transformer to differentiate between explicit vs
    # default aliases and supply their own defaults.
    for a in attrs:
        if not a.alias:
            # Evolve is very slow, so we hold our nose and do it dirty.
            _OBJ_SETATTR.__get__(a)("alias", _default_init_alias_for(a.name))

    # Create AttrsClass *after* applying the field_transformer since it may
    # add or remove attributes!
    attr_names = [a.name for a in attrs]
    AttrsClass = _make_attr_tuple_class(cls.__name__, attr_names)

    return _Attributes(AttrsClass(attrs), base_attrs, base_attr_map)


def _make_cached_property_getattr(cached_properties, original_getattr, cls):
    lines = [
        # Wrapped to get `__class__` into closure cell for super()
        # (It will be replaced with the newly constructed class after construction).
        "def wrapper(_cls):",
        "    __class__ = _cls",
        "    def __getattr__(self, item, cached_properties=cached_properties, original_getattr=original_getattr, _cached_setattr_get=_cached_setattr_get):",
        "         func = cached_properties.get(item)",
        "         if func is not None:",
        "              result = func(self)",
        "              _setter = _cached_setattr_get(self)",
        "              _setter(item, result)",
        "              return result",
    ]
    if original_getattr is not None:
        lines.append(
            "         return original_getattr(self, item)",
        )
    else:
        lines.extend(
            [
                "         try:",
                "             return super().__getattribute__(item)",
                "         except AttributeError:",
                "             if not hasattr(super(), '__getattr__'):",
                "                 raise",
                "             return super().__getattr__(item)",
                "         original_error = f\"'{self.__class__.__name__}' object has no attribute '{item}'\"",
                "         raise AttributeError(original_error)",
            ]
        )

    lines.extend(
        [
            "    return __getattr__",
            "__getattr__ = wrapper(_cls)",
        ]
    )

    unique_filename = _generate_unique_filename(cls, "getattr")

    glob = {
        "cached_properties": cached_properties,
        "_cached_setattr_get": _OBJ_SETATTR.__get__,
        "original_getattr": original_getattr,
    }

    return _linecache_and_compile(
        "\n".join(lines), unique_filename, glob, locals={"_cls": cls}
    )["__getattr__"]


def _frozen_setattrs(self, name, value):
    """
    Attached to frozen classes as __setattr__.
    """
    if isinstance(self, BaseException) and name in (
        "__cause__",
        "__context__",
        "__traceback__",
        "__suppress_context__",
        "__notes__",
    ):
        BaseException.__setattr__(self, name, value)
        return

    raise FrozenInstanceError


def _frozen_delattrs(self, name):
    """
    Attached to frozen classes as __delattr__.
    """
    if isinstance(self, BaseException) and name in ("__notes__",):
        BaseException.__delattr__(self, name)
        return

    raise FrozenInstanceError


def evolve(*args, **changes):
    """
    Create a new instance, based on the first positional argument with
    *changes* applied.

    .. tip::

       On Python 3.13 and later, you can also use `copy.replace` instead.

    Args:

        inst:
            Instance of a class with *attrs* attributes. *inst* must be passed
            as a positional argument.

        changes:
            Keyword changes in the new copy.

    Returns:
        A copy of inst with *changes* incorporated.

    Raises:
        TypeError:
            If *attr_name* couldn't be found in the class ``__init__``.

        attrs.exceptions.NotAnAttrsClassError:
            If *cls* is not an *attrs* class.

    .. versionadded:: 17.1.0
    .. deprecated:: 23.1.0
       It is now deprecated to pass the instance using the keyword argument
       *inst*. It will raise a warning until at least April 2024, after which
       it will become an error. Always pass the instance as a positional
       argument.
    .. versionchanged:: 24.1.0
       *inst* can't be passed as a keyword argument anymore.
    """
    try:
        (inst,) = args
    except ValueError:
        msg = (
            f"evolve() takes 1 positional argument, but {len(args)} were given"
        )
        raise TypeError(msg) from None

    cls = inst.__class__
    attrs = fields(cls)
    for a in attrs:
        if not a.init:
            continue
        attr_name = a.name  # To deal with private attributes.
        init_name = a.alias
        if init_name not in changes:
            changes[init_name] = getattr(inst, attr_name)

    return cls(**changes)


class _ClassBuilder:
    """
    Iteratively build *one* class.
    """

    __slots__ = (
        "_add_method_dunders",
        "_attr_names",
        "_attrs",
        "_base_attr_map",
        "_base_names",
        "_cache_hash",
        "_cls",
        "_cls_dict",
        "_delete_attribs",
        "_frozen",
        "_has_custom_setattr",
        "_has_post_init",
        "_has_pre_init",
        "_is_exc",
        "_on_setattr",
        "_pre_init_has_args",
        "_repr_added",
        "_script_snippets",
        "_slots",
        "_weakref_slot",
        "_wrote_own_setattr",
    )

    def __init__(
        self,
        cls: type,
        these,
        slots,
        frozen,
        weakref_slot,
        getstate_setstate,
        auto_attribs,
        kw_only,
        cache_hash,
        is_exc,
        collect_by_mro,
        on_setattr,
        has_custom_setattr,
        field_transformer,
    ):
        attrs, base_attrs, base_map = _transform_attrs(
            cls,
            these,
            auto_attribs,
            kw_only,
            collect_by_mro,
            field_transformer,
        )

        self._cls = cls
        self._cls_dict = dict(cls.__dict__) if slots else {}
        self._attrs = attrs
        self._base_names = {a.name for a in base_attrs}
        self._base_attr_map = base_map
        self._attr_names = tuple(a.name for a in attrs)
        self._slots = slots
        self._frozen = frozen
        self._weakref_slot = weakref_slot
        self._cache_hash = cache_hash
        self._has_pre_init = bool(getattr(cls, "__attrs_pre_init__", False))
        self._pre_init_has_args = False
        if self._has_pre_init:
            # Check if the pre init method has more arguments than just `self`
            # We want to pass arguments if pre init expects arguments
            pre_init_func = cls.__attrs_pre_init__
            pre_init_signature = inspect.signature(pre_init_func)
            self._pre_init_has_args = len(pre_init_signature.parameters) > 1
        self._has_post_init = bool(getattr(cls, "__attrs_post_init__", False))
        self._delete_attribs = not bool(these)
        self._is_exc = is_exc
        self._on_setattr = on_setattr

        self._has_custom_setattr = has_custom_setattr
        self._wrote_own_setattr = False

        self._cls_dict["__attrs_attrs__"] = self._attrs

        if frozen:
            self._cls_dict["__setattr__"] = _frozen_setattrs
            self._cls_dict["__delattr__"] = _frozen_delattrs

            self._wrote_own_setattr = True
        elif on_setattr in (
            _DEFAULT_ON_SETATTR,
            setters.validate,
            setters.convert,
        ):
            has_validator = has_converter = False
            for a in attrs:
                if a.validator is not None:
                    has_validator = True
                if a.converter is not None:
                    has_converter = True

                if has_validator and has_converter:
                    break
            if (
                (
                    on_setattr == _DEFAULT_ON_SETATTR
                    and not (has_validator or has_converter)
                )
                or (on_setattr == setters.validate and not has_validator)
                or (on_setattr == setters.convert and not has_converter)
            ):
                # If class-level on_setattr is set to convert + validate, but
                # there's no field to convert or validate, pretend like there's
                # no on_setattr.
                self._on_setattr = None

        if getstate_setstate:
            (
                self._cls_dict["__getstate__"],
                self._cls_dict["__setstate__"],
            ) = self._make_getstate_setstate()

        # tuples of script, globs, hook
        self._script_snippets: list[
            tuple[str, dict, Callable[[dict, dict], Any]]
        ] = []
        self._repr_added = False

        # We want to only do this check once; in 99.9% of cases these
        # exist.
        if not hasattr(self._cls, "__module__") or not hasattr(
            self._cls, "__qualname__"
        ):
            self._add_method_dunders = self._add_method_dunders_safe
        else:
            self._add_method_dunders = self._add_method_dunders_unsafe

    def __repr__(self):
        return f"<_ClassBuilder(cls={self._cls.__name__})>"

    def _eval_snippets(self) -> None:
        """
        Evaluate any registered snippets in one go.
        """
        script = "\n".join([snippet[0] for snippet in self._script_snippets])
        globs = {}
        for _, snippet_globs, _ in self._script_snippets:
            globs.update(snippet_globs)

        locs = _linecache_and_compile(
            script,
            _generate_unique_filename(self._cls, "methods"),
            globs,
        )

        for _, _, hook in self._script_snippets:
            hook(self._cls_dict, locs)

    def build_class(self):
        """
        Finalize class based on the accumulated configuration.

        Builder cannot be used after calling this method.
        """
        self._eval_snippets()
        if self._slots is True:
            cls = self._create_slots_class()
        else:
            cls = self._patch_original_class()
            if PY_3_10_PLUS:
                cls = abc.update_abstractmethods(cls)

        # The method gets only called if it's not inherited from a base class.
        # _has_own_attribute does NOT work properly for classmethods.
        if (
            getattr(cls, "__attrs_init_subclass__", None)
            and "__attrs_init_subclass__" not in cls.__dict__
        ):
            cls.__attrs_init_subclass__()

        return cls

    def _patch_original_class(self):
        """
        Apply accumulated methods and return the class.
        """
        cls = self._cls
        base_names = self._base_names

        # Clean class of attribute definitions (`attr.ib()`s).
        if self._delete_attribs:
            for name in self._attr_names:
                if (
                    name not in base_names
                    and getattr(cls, name, _SENTINEL) is not _SENTINEL
                ):
                    # An AttributeError can happen if a base class defines a
                    # class variable and we want to set an attribute with the
                    # same name by using only a type annotation.
                    with contextlib.suppress(AttributeError):
                        delattr(cls, name)

        # Attach our dunder methods.
        for name, value in self._cls_dict.items():
            setattr(cls, name, value)

        # If we've inherited an attrs __setattr__ and don't write our own,
        # reset it to object's.
        if not self._wrote_own_setattr and getattr(
            cls, "__attrs_own_setattr__", False
        ):
            cls.__attrs_own_setattr__ = False

            if not self._has_custom_setattr:
                cls.__setattr__ = _OBJ_SETATTR

        return cls

    def _create_slots_class(self):
        """
        Build and return a new class with a `__slots__` attribute.
        """
        cd = {
            k: v
            for k, v in self._cls_dict.items()
            if k not in (*tuple(self._attr_names), "__dict__", "__weakref__")
        }

        # If our class doesn't have its own implementation of __setattr__
        # (either from the user or by us), check the bases, if one of them has
        # an attrs-made __setattr__, that needs to be reset. We don't walk the
        # MRO because we only care about our immediate base classes.
        # XXX: This can be confused by subclassing a slotted attrs class with
        # XXX: a non-attrs class and subclass the resulting class with an attrs
        # XXX: class.  See `test_slotted_confused` for details.  For now that's
        # XXX: OK with us.
        if not self._wrote_own_setattr:
            cd["__attrs_own_setattr__"] = False

            if not self._has_custom_setattr:
                for base_cls in self._cls.__bases__:
                    if base_cls.__dict__.get("__attrs_own_setattr__", False):
                        cd["__setattr__"] = _OBJ_SETATTR
                        break

        # Traverse the MRO to collect existing slots
        # and check for an existing __weakref__.
        existing_slots = {}
        weakref_inherited = False
        for base_cls in self._cls.__mro__[1:-1]:
            if base_cls.__dict__.get("__weakref__", None) is not None:
                weakref_inherited = True
            existing_slots.update(
                {
                    name: getattr(base_cls, name)
                    for name in getattr(base_cls, "__slots__", [])
                }
            )

        base_names = set(self._base_names)

        names = self._attr_names
        if (
            self._weakref_slot
            and "__weakref__" not in getattr(self._cls, "__slots__", ())
            and "__weakref__" not in names
            and not weakref_inherited
        ):
            names += ("__weakref__",)

        cached_properties = {
            name: cached_prop.func
            for name, cached_prop in cd.items()
            if isinstance(cached_prop, cached_property)
        }

        # Collect methods with a `__class__` reference that are shadowed in the new class.
        # To know to update them.
        additional_closure_functions_to_update = []
        if cached_properties:
            class_annotations = _get_annotations(self._cls)
            for name, func in cached_properties.items():
                # Add cached properties to names for slotting.
                names += (name,)
                # Clear out function from class to avoid clashing.
                del cd[name]
                additional_closure_functions_to_update.append(func)
                annotation = inspect.signature(func).return_annotation
                if annotation is not inspect.Parameter.empty:
                    class_annotations[name] = annotation

            original_getattr = cd.get("__getattr__")
            if original_getattr is not None:
                additional_closure_functions_to_update.append(original_getattr)

            cd["__getattr__"] = _make_cached_property_getattr(
                cached_properties, original_getattr, self._cls
            )

        # We only add the names of attributes that aren't inherited.
        # Setting __slots__ to inherited attributes wastes memory.
        slot_names = [name for name in names if name not in base_names]

        # There are slots for attributes from current class
        # that are defined in parent classes.
        # As their descriptors may be overridden by a child class,
        # we collect them here and update the class dict
        reused_slots = {
            slot: slot_descriptor
            for slot, slot_descriptor in existing_slots.items()
            if slot in slot_names
        }
        slot_names = [name for name in slot_names if name not in reused_slots]
        cd.update(reused_slots)
        if self._cache_hash:
            slot_names.append(_HASH_CACHE_FIELD)

        cd["__slots__"] = tuple(slot_names)

        cd["__qualname__"] = self._cls.__qualname__

        # Create new class based on old class and our methods.
        cls = type(self._cls)(self._cls.__name__, self._cls.__bases__, cd)

        # The following is a fix for
        # <https://github.com/python-attrs/attrs/issues/102>.
        # If a method mentions `__class__` or uses the no-arg super(), the
        # compiler will bake a reference to the class in the method itself
        # as `method.__closure__`.  Since we replace the class with a
        # clone, we rewrite these references so it keeps working.
        for item in itertools.chain(
            cls.__dict__.values(), additional_closure_functions_to_update
        ):
            if isinstance(item, (classmethod, staticmethod)):
                # Class- and staticmethods hide their functions inside.
                # These might need to be rewritten as well.
                closure_cells = getattr(item.__func__, "__closure__", None)
            elif isinstance(item, property):
                # Workaround for property `super()` shortcut (PY3-only).
                # There is no universal way for other descriptors.
                closure_cells = getattr(item.fget, "__closure__", None)
            else:
                closure_cells = getattr(item, "__closure__", None)

            if not closure_cells:  # Catch None or the empty list.
                continue
            for cell in closure_cells:
                try:
                    match = cell.cell_contents is self._cls
                except ValueError:  # noqa: PERF203
                    # ValueError: Cell is empty
                    pass
                else:
                    if match:
                        cell.cell_contents = cls
        return cls

    def add_repr(self, ns):
        script, globs = _make_repr_script(self._attrs, ns)

        def _attach_repr(cls_dict, globs):
            cls_dict["__repr__"] = self._add_method_dunders(globs["__repr__"])

        self._script_snippets.append((script, globs, _attach_repr))
        self._repr_added = True
        return self

    def add_str(self):
        if not self._repr_added:
            msg = "__str__ can only be generated if a __repr__ exists."
            raise ValueError(msg)

        def __str__(self):
            return self.__repr__()

        self._cls_dict["__str__"] = self._add_method_dunders(__str__)
        return self

    def _make_getstate_setstate(self):
        """
        Create custom __setstate__ and __getstate__ methods.
        """
        # __weakref__ is not writable.
        state_attr_names = tuple(
            an for an in self._attr_names if an != "__weakref__"
        )

        def slots_getstate(self):
            """
            Automatically created by attrs.
            """
            return {name: getattr(self, name) for name in state_attr_names}

        hash_caching_enabled = self._cache_hash

        def slots_setstate(self, state):
            """
            Automatically created by attrs.
            """
            __bound_setattr = _OBJ_SETATTR.__get__(self)
            if isinstance(state, tuple):
                # Backward compatibility with attrs instances pickled with
                # attrs versions before v22.2.0 which stored tuples.
                for name, value in zip(state_attr_names, state):
                    __bound_setattr(name, value)
            else:
                for name in state_attr_names:
                    if name in state:
                        __bound_setattr(name, state[name])

            # The hash code cache is not included when the object is
            # serialized, but it still needs to be initialized to None to
            # indicate that the first call to __hash__ should be a cache
            # miss.
            if hash_caching_enabled:
                __bound_setattr(_HASH_CACHE_FIELD, None)

        return slots_getstate, slots_setstate

    def make_unhashable(self):
        self._cls_dict["__hash__"] = None
        return self

    def add_hash(self):
        script, globs = _make_hash_script(
            self._cls,
            self._attrs,
            frozen=self._frozen,
            cache_hash=self._cache_hash,
        )

        def attach_hash(cls_dict: dict, locs: dict) -> None:
            cls_dict["__hash__"] = self._add_method_dunders(locs["__hash__"])

        self._script_snippets.append((script, globs, attach_hash))

        return self

    def add_init(self):
        script, globs, annotations = _make_init_script(
            self._cls,
            self._attrs,
            self._has_pre_init,
            self._pre_init_has_args,
            self._has_post_init,
            self._frozen,
            self._slots,
            self._cache_hash,
            self._base_attr_map,
            self._is_exc,
            self._on_setattr,
            attrs_init=False,
        )

        def _attach_init(cls_dict, globs):
            init = globs["__init__"]
            init.__annotations__ = annotations
            cls_dict["__init__"] = self._add_method_dunders(init)

        self._script_snippets.append((script, globs, _attach_init))

        return self

    def add_replace(self):
        self._cls_dict["__replace__"] = self._add_method_dunders(
            lambda self, **changes: evolve(self, **changes)
        )
        return self

    def add_match_args(self):
        self._cls_dict["__match_args__"] = tuple(
            field.name
            for field in self._attrs
            if field.init and not field.kw_only
        )

    def add_attrs_init(self):
        script, globs, annotations = _make_init_script(
            self._cls,
            self._attrs,
            self._has_pre_init,
            self._pre_init_has_args,
            self._has_post_init,
            self._frozen,
            self._slots,
            self._cache_hash,
            self._base_attr_map,
            self._is_exc,
            self._on_setattr,
            attrs_init=True,
        )

        def _attach_attrs_init(cls_dict, globs):
            init = globs["__attrs_init__"]
            init.__annotations__ = annotations
            cls_dict["__attrs_init__"] = self._add_method_dunders(init)

        self._script_snippets.append((script, globs, _attach_attrs_init))

        return self

    def add_eq(self):
        cd = self._cls_dict

        script, globs = _make_eq_script(self._attrs)

        def _attach_eq(cls_dict, globs):
            cls_dict["__eq__"] = self._add_method_dunders(globs["__eq__"])

        self._script_snippets.append((script, globs, _attach_eq))

        cd["__ne__"] = __ne__

        return self

    def add_order(self):
        cd = self._cls_dict

        cd["__lt__"], cd["__le__"], cd["__gt__"], cd["__ge__"] = (
            self._add_method_dunders(meth)
            for meth in _make_order(self._cls, self._attrs)
        )

        return self

    def add_setattr(self):
        sa_attrs = {}
        for a in self._attrs:
            on_setattr = a.on_setattr or self._on_setattr
            if on_setattr and on_setattr is not setters.NO_OP:
                sa_attrs[a.name] = a, on_setattr

        if not sa_attrs:
            return self

        if self._has_custom_setattr:
            # We need to write a __setattr__ but there already is one!
            msg = "Can't combine custom __setattr__ with on_setattr hooks."
            raise ValueError(msg)

        # docstring comes from _add_method_dunders
        def __setattr__(self, name, val):
            try:
                a, hook = sa_attrs[name]
            except KeyError:
                nval = val
            else:
                nval = hook(self, a, val)

            _OBJ_SETATTR(self, name, nval)

        self._cls_dict["__attrs_own_setattr__"] = True
        self._cls_dict["__setattr__"] = self._add_method_dunders(__setattr__)
        self._wrote_own_setattr = True

        return self

    def _add_method_dunders_unsafe(self, method: Callable) -> Callable:
        """
        Add __module__ and __qualname__ to a *method*.
        """
        method.__module__ = self._cls.__module__

        method.__qualname__ = f"{self._cls.__qualname__}.{method.__name__}"

        method.__doc__ = (
            f"Method generated by attrs for class {self._cls.__qualname__}."
        )

        return method

    def _add_method_dunders_safe(self, method: Callable) -> Callable:
        """
        Add __module__ and __qualname__ to a *method* if possible.
        """
        with contextlib.suppress(AttributeError):
            method.__module__ = self._cls.__module__

        with contextlib.suppress(AttributeError):
            method.__qualname__ = f"{self._cls.__qualname__}.{method.__name__}"

        with contextlib.suppress(AttributeError):
            method.__doc__ = f"Method generated by attrs for class {self._cls.__qualname__}."

        return method


def _determine_attrs_eq_order(cmp, eq, order, default_eq):
    """
    Validate the combination of *cmp*, *eq*, and *order*. Derive the effective
    values of eq and order.  If *eq* is None, set it to *default_eq*.
    """
    if cmp is not None and any((eq is not None, order is not None)):
        msg = "Don't mix `cmp` with `eq' and `order`."
        raise ValueError(msg)

    # cmp takes precedence due to bw-compatibility.
    if cmp is not None:
        return cmp, cmp

    # If left None, equality is set to the specified default and ordering
    # mirrors equality.
    if eq is None:
        eq = default_eq

    if order is None:
        order = eq

    if eq is False and order is True:
        msg = "`order` can only be True if `eq` is True too."
        raise ValueError(msg)

    return eq, order


def _determine_attrib_eq_order(cmp, eq, order, default_eq):
    """
    Validate the combination of *cmp*, *eq*, and *order*. Derive the effective
    values of eq and order.  If *eq* is None, set it to *default_eq*.
    """
    if cmp is not None and any((eq is not None, order is not None)):
        msg = "Don't mix `cmp` with `eq' and `order`."
        raise ValueError(msg)

    def decide_callable_or_boolean(value):
        """
        Decide whether a key function is used.
        """
        if callable(value):
            value, key = True, value
        else:
            key = None
        return value, key

    # cmp takes precedence due to bw-compatibility.
    if cmp is not None:
        cmp, cmp_key = decide_callable_or_boolean(cmp)
        return cmp, cmp_key, cmp, cmp_key

    # If left None, equality is set to the specified default and ordering
    # mirrors equality.
    if eq is None:
        eq, eq_key = default_eq, None
    else:
        eq, eq_key = decide_callable_or_boolean(eq)

    if order is None:
        order, order_key = eq, eq_key
    else:
        order, order_key = decide_callable_or_boolean(order)

    if eq is False and order is True:
        msg = "`order` can only be True if `eq` is True too."
        raise ValueError(msg)

    return eq, eq_key, order, order_key


def _determine_whether_to_implement(
    cls, flag, auto_detect, dunders, default=True
):
    """
    Check whether we should implement a set of methods for *cls*.

    *flag* is the argument passed into @attr.s like 'init', *auto_detect* the
    same as passed into @attr.s and *dunders* is a tuple of attribute names
    whose presence signal that the user has implemented it themselves.

    Return *default* if no reason for either for or against is found.
    """
    if flag is True or flag is False:
        return flag

    if flag is None and auto_detect is False:
        return default

    # Logically, flag is None and auto_detect is True here.
    for dunder in dunders:
        if _has_own_attribute(cls, dunder):
            return False

    return default


def attrs(
    maybe_cls=None,
    these=None,
    repr_ns=None,
    repr=None,
    cmp=None,
    hash=None,
    init=None,
    slots=False,
    frozen=False,
    weakref_slot=True,
    str=False,
    auto_attribs=False,
    kw_only=False,
    cache_hash=False,
    auto_exc=False,
    eq=None,
    order=None,
    auto_detect=False,
    collect_by_mro=False,
    getstate_setstate=None,
    on_setattr=None,
    field_transformer=None,
    match_args=True,
    unsafe_hash=None,
):
    r"""
    A class decorator that adds :term:`dunder methods` according to the
    specified attributes using `attr.ib` or the *these* argument.

    Consider using `attrs.define` / `attrs.frozen` in new code (``attr.s`` will
    *never* go away, though).

    Args:
        repr_ns (str):
            When using nested classes, there was no way in Python 2 to
            automatically detect that.  This argument allows to set a custom
            name for a more meaningful ``repr`` output.  This argument is
            pointless in Python 3 and is therefore deprecated.

    .. caution::
        Refer to `attrs.define` for the rest of the parameters, but note that they
        can have different defaults.

        Notably, leaving *on_setattr* as `None` will **not** add any hooks.

    .. versionadded:: 16.0.0 *slots*
    .. versionadded:: 16.1.0 *frozen*
    .. versionadded:: 16.3.0 *str*
    .. versionadded:: 16.3.0 Support for ``__attrs_post_init__``.
    .. versionchanged:: 17.1.0
       *hash* supports `None` as value which is also the default now.
    .. versionadded:: 17.3.0 *auto_attribs*
    .. versionchanged:: 18.1.0
       If *these* is passed, no attributes are deleted from the class body.
    .. versionchanged:: 18.1.0 If *these* is ordered, the order is retained.
    .. versionadded:: 18.2.0 *weakref_slot*
    .. deprecated:: 18.2.0
       ``__lt__``, ``__le__``, ``__gt__``, and ``__ge__`` now raise a
       `DeprecationWarning` if the classes compared are subclasses of
       each other. ``__eq`` and ``__ne__`` never tried to compared subclasses
       to each other.
    .. versionchanged:: 19.2.0
       ``__lt__``, ``__le__``, ``__gt__``, and ``__ge__`` now do not consider
       subclasses comparable anymore.
    .. versionadded:: 18.2.0 *kw_only*
    .. versionadded:: 18.2.0 *cache_hash*
    .. versionadded:: 19.1.0 *auto_exc*
    .. deprecated:: 19.2.0 *cmp* Removal on or after 2021-06-01.
    .. versionadded:: 19.2.0 *eq* and *order*
    .. versionadded:: 20.1.0 *auto_detect*
    .. versionadded:: 20.1.0 *collect_by_mro*
    .. versionadded:: 20.1.0 *getstate_setstate*
    .. versionadded:: 20.1.0 *on_setattr*
    .. versionadded:: 20.3.0 *field_transformer*
    .. versionchanged:: 21.1.0
       ``init=False`` injects ``__attrs_init__``
    .. versionchanged:: 21.1.0 Support for ``__attrs_pre_init__``
    .. versionchanged:: 21.1.0 *cmp* undeprecated
    .. versionadded:: 21.3.0 *match_args*
    .. versionadded:: 22.2.0
       *unsafe_hash* as an alias for *hash* (for :pep:`681` compliance).
    .. deprecated:: 24.1.0 *repr_ns*
    .. versionchanged:: 24.1.0
       Instances are not compared as tuples of attributes anymore, but using a
       big ``and`` condition. This is faster and has more correct behavior for
       uncomparable values like `math.nan`.
    .. versionadded:: 24.1.0
       If a class has an *inherited* classmethod called
       ``__attrs_init_subclass__``, it is executed after the class is created.
    .. deprecated:: 24.1.0 *hash* is deprecated in favor of *unsafe_hash*.
    """
    if repr_ns is not None:
        import warnings

        warnings.warn(
            DeprecationWarning(
                "The `repr_ns` argument is deprecated and will be removed in or after August 2025."
            ),
            stacklevel=2,
        )

    eq_, order_ = _determine_attrs_eq_order(cmp, eq, order, None)

    #  unsafe_hash takes precedence due to PEP 681.
    if unsafe_hash is not None:
        hash = unsafe_hash

    if isinstance(on_setattr, (list, tuple)):
        on_setattr = setters.pipe(*on_setattr)

    def wrap(cls):
        is_frozen = frozen or _has_frozen_base_class(cls)
        is_exc = auto_exc is True and issubclass(cls, BaseException)
        has_own_setattr = auto_detect and _has_own_attribute(
            cls, "__setattr__"
        )

        if has_own_setattr and is_frozen:
            msg = "Can't freeze a class with a custom __setattr__."
            raise ValueError(msg)

        builder = _ClassBuilder(
            cls,
            these,
            slots,
            is_frozen,
            weakref_slot,
            _determine_whether_to_implement(
                cls,
                getstate_setstate,
                auto_detect,
                ("__getstate__", "__setstate__"),
                default=slots,
            ),
            auto_attribs,
            kw_only,
            cache_hash,
            is_exc,
            collect_by_mro,
            on_setattr,
            has_own_setattr,
            field_transformer,
        )

        if _determine_whether_to_implement(
            cls, repr, auto_detect, ("__repr__",)
        ):
            builder.add_repr(repr_ns)

        if str is True:
            builder.add_str()

        eq = _determine_whether_to_implement(
            cls, eq_, auto_detect, ("__eq__", "__ne__")
        )
        if not is_exc and eq is True:
            builder.add_eq()
        if not is_exc and _determine_whether_to_implement(
            cls, order_, auto_detect, ("__lt__", "__le__", "__gt__", "__ge__")
        ):
            builder.add_order()

        if not frozen:
            builder.add_setattr()

        nonlocal hash
        if (
            hash is None
            and auto_detect is True
            and _has_own_attribute(cls, "__hash__")
        ):
            hash = False

        if hash is not True and hash is not False and hash is not None:
            # Can't use `hash in` because 1 == True for example.
            msg = "Invalid value for hash.  Must be True, False, or None."
            raise TypeError(msg)

        if hash is False or (hash is None and eq is False) or is_exc:
            # Don't do anything. Should fall back to __object__'s __hash__
            # which is by id.
            if cache_hash:
                msg = "Invalid value for cache_hash.  To use hash caching, hashing must be either explicitly or implicitly enabled."
                raise TypeError(msg)
        elif hash is True or (
            hash is None and eq is True and is_frozen is True
        ):
            # Build a __hash__ if told so, or if it's safe.
            builder.add_hash()
        else:
            # Raise TypeError on attempts to hash.
            if cache_hash:
                msg = "Invalid value for cache_hash.  To use hash caching, hashing must be either explicitly or implicitly enabled."
                raise TypeError(msg)
            builder.make_unhashable()

        if _determine_whether_to_implement(
            cls, init, auto_detect, ("__init__",)
        ):
            builder.add_init()
        else:
            builder.add_attrs_init()
            if cache_hash:
                msg = "Invalid value for cache_hash.  To use hash caching, init must be True."
                raise TypeError(msg)

        if PY_3_13_PLUS and not _has_own_attribute(cls, "__replace__"):
            builder.add_replace()

        if (
            PY_3_10_PLUS
            and match_args
            and not _has_own_attribute(cls, "__match_args__")
        ):
            builder.add_match_args()

        return builder.build_class()

    # maybe_cls's type depends on the usage of the decorator.  It's a class
    # if it's used as `@attrs` but `None` if used as `@attrs()`.
    if maybe_cls is None:
        return wrap

    return wrap(maybe_cls)


_attrs = attrs
"""
Internal alias so we can use it in functions that take an argument called
*attrs*.
"""


def _has_frozen_base_class(cls):
    """
    Check whether *cls* has a frozen ancestor by looking at its
    __setattr__.
    """
    return cls.__setattr__ is _frozen_setattrs


def _generate_unique_filename(cls: type, func_name: str) -> str:
    """
    Create a "filename" suitable for a function being generated.
    """
    return (
        f"<attrs generated {func_name} {cls.__module__}."
        f"{getattr(cls, '__qualname__', cls.__name__)}>"
    )


def _make_hash_script(
    cls: type, attrs: list[Attribute], frozen: bool, cache_hash: bool
) -> tuple[str, dict]:
    attrs = tuple(
        a for a in attrs if a.hash is True or (a.hash is None and a.eq is True)
    )

    tab = "        "

    type_hash = hash(_generate_unique_filename(cls, "hash"))
    # If eq is custom generated, we need to include the functions in globs
    globs = {}

    hash_def = "def __hash__(self"
    hash_func = "hash(("
    closing_braces = "))"
    if not cache_hash:
        hash_def += "):"
    else:
        hash_def += ", *"

        hash_def += ", _cache_wrapper=__import__('attr._make')._make._CacheHashWrapper):"
        hash_func = "_cache_wrapper(" + hash_func
        closing_braces += ")"

    method_lines = [hash_def]

    def append_hash_computation_lines(prefix, indent):
        """
        Generate the code for actually computing the hash code.
        Below this will either be returned directly or used to compute
        a value which is then cached, depending on the value of cache_hash
        """

        method_lines.extend(
            [
                indent + prefix + hash_func,
                indent + f"        {type_hash},",
            ]
        )

        for a in attrs:
            if a.eq_key:
                cmp_name = f"_{a.name}_key"
                globs[cmp_name] = a.eq_key
                method_lines.append(
                    indent + f"        {cmp_name}(self.{a.name}),"
                )
            else:
                method_lines.append(indent + f"        self.{a.name},")

        method_lines.append(indent + "    " + closing_braces)

    if cache_hash:
        method_lines.append(tab + f"if self.{_HASH_CACHE_FIELD} is None:")
        if frozen:
            append_hash_computation_lines(
                f"object.__setattr__(self, '{_HASH_CACHE_FIELD}', ", tab * 2
            )
            method_lines.append(tab * 2 + ")")  # close __setattr__
        else:
            append_hash_computation_lines(
                f"self.{_HASH_CACHE_FIELD} = ", tab * 2
            )
        method_lines.append(tab + f"return self.{_HASH_CACHE_FIELD}")
    else:
        append_hash_computation_lines("return ", tab)

    script = "\n".join(method_lines)
    return script, globs


def _add_hash(cls: type, attrs: list[Attribute]):
    """
    Add a hash method to *cls*.
    """
    script, globs = _make_hash_script(
        cls, attrs, frozen=False, cache_hash=False
    )
    _compile_and_eval(
        script, globs, filename=_generate_unique_filename(cls, "__hash__")
    )
    cls.__hash__ = globs["__hash__"]
    return cls


def __ne__(self, other):
    """
    Check equality and either forward a NotImplemented or
    return the result negated.
    """
    result = self.__eq__(other)
    if result is NotImplemented:
        return NotImplemented

    return not result


def _make_eq_script(attrs: list) -> tuple[str, dict]:
    """
    Create __eq__ method for *cls* with *attrs*.
    """
    attrs = [a for a in attrs if a.eq]

    lines = [
        "def __eq__(self, other):",
        "    if other.__class__ is not self.__class__:",
        "        return NotImplemented",
    ]

    globs = {}
    if attrs:
        lines.append("    return  (")
        for a in attrs:
            if a.eq_key:
                cmp_name = f"_{a.name}_key"
                # Add the key function to the global namespace
                # of the evaluated function.
                globs[cmp_name] = a.eq_key
                lines.append(
                    f"        {cmp_name}(self.{a.name}) == {cmp_name}(other.{a.name})"
                )
            else:
                lines.append(f"        self.{a.name} == other.{a.name}")
            if a is not attrs[-1]:
                lines[-1] = f"{lines[-1]} and"
        lines.append("    )")
    else:
        lines.append("    return True")

    script = "\n".join(lines)

    return script, globs


def _make_order(cls, attrs):
    """
    Create ordering methods for *cls* with *attrs*.
    """
    attrs = [a for a in attrs if a.order]

    def attrs_to_tuple(obj):
        """
        Save us some typing.
        """
        return tuple(
            key(value) if key else value
            for value, key in (
                (getattr(obj, a.name), a.order_key) for a in attrs
            )
        )

    def __lt__(self, other):
        """
        Automatically created by attrs.
        """
        if other.__class__ is self.__class__:
            return attrs_to_tuple(self) < attrs_to_tuple(other)

        return NotImplemented

    def __le__(self, other):
        """
        Automatically created by attrs.
        """
        if other.__class__ is self.__class__:
            return attrs_to_tuple(self) <= attrs_to_tuple(other)

        return NotImplemented

    def __gt__(self, other):
        """
        Automatically created by attrs.
        """
        if other.__class__ is self.__class__:
            return attrs_to_tuple(self) > attrs_to_tuple(other)

        return NotImplemented

    def __ge__(self, other):
        """
        Automatically created by attrs.
        """
        if other.__class__ is self.__class__:
            return attrs_to_tuple(self) >= attrs_to_tuple(other)

        return NotImplemented

    return __lt__, __le__, __gt__, __ge__


def _add_eq(cls, attrs=None):
    """
    Add equality methods to *cls* with *attrs*.
    """
    if attrs is None:
        attrs = cls.__attrs_attrs__

    script, globs = _make_eq_script(attrs)
    _compile_and_eval(
        script, globs, filename=_generate_unique_filename(cls, "__eq__")
    )
    cls.__eq__ = globs["__eq__"]
    cls.__ne__ = __ne__

    return cls


def _make_repr_script(attrs, ns) -> tuple[str, dict]:
    """
    Create the source and globs for a __repr__ and return it.
    """
    # Figure out which attributes to include, and which function to use to
    # format them. The a.repr value can be either bool or a custom
    # callable.
    attr_names_with_reprs = tuple(
        (a.name, (repr if a.repr is True else a.repr), a.init)
        for a in attrs
        if a.repr is not False
    )
    globs = {
        name + "_repr": r for name, r, _ in attr_names_with_reprs if r != repr
    }
    globs["_compat"] = _compat
    globs["AttributeError"] = AttributeError
    globs["NOTHING"] = NOTHING
    attribute_fragments = []
    for name, r, i in attr_names_with_reprs:
        accessor = (
            "self." + name if i else 'getattr(self, "' + name + '", NOTHING)'
        )
        fragment = (
            "%s={%s!r}" % (name, accessor)
            if r == repr
            else "%s={%s_repr(%s)}" % (name, name, accessor)
        )
        attribute_fragments.append(fragment)
    repr_fragment = ", ".join(attribute_fragments)

    if ns is None:
        cls_name_fragment = '{self.__class__.__qualname__.rsplit(">.", 1)[-1]}'
    else:
        cls_name_fragment = ns + ".{self.__class__.__name__}"

    lines = [
        "def __repr__(self):",
        "  try:",
        "    already_repring = _compat.repr_context.already_repring",
        "  except AttributeError:",
        "    already_repring = {id(self),}",
        "    _compat.repr_context.already_repring = already_repring",
        "  else:",
        "    if id(self) in already_repring:",
        "      return '...'",
        "    else:",
        "      already_repring.add(id(self))",
        "  try:",
        f"    return f'{cls_name_fragment}({repr_fragment})'",
        "  finally:",
        "    already_repring.remove(id(self))",
    ]

    return "\n".join(lines), globs


def _add_repr(cls, ns=None, attrs=None):
    """
    Add a repr method to *cls*.
    """
    if attrs is None:
        attrs = cls.__attrs_attrs__

    script, globs = _make_repr_script(attrs, ns)
    _compile_and_eval(
        script, globs, filename=_generate_unique_filename(cls, "__repr__")
    )
    cls.__repr__ = globs["__repr__"]
    return cls


def fields(cls):
    """
    Return the tuple of *attrs* attributes for a class.

    The tuple also allows accessing the fields by their names (see below for
    examples).

    Args:
        cls (type): Class to introspect.

    Raises:
        TypeError: If *cls* is not a class.

        attrs.exceptions.NotAnAttrsClassError:
            If *cls* is not an *attrs* class.

    Returns:
        tuple (with name accessors) of `attrs.Attribute`

    .. versionchanged:: 16.2.0 Returned tuple allows accessing the fields
       by name.
    .. versionchanged:: 23.1.0 Add support for generic classes.
    """
    generic_base = get_generic_base(cls)

    if generic_base is None and not isinstance(cls, type):
        msg = "Passed object must be a class."
        raise TypeError(msg)

    attrs = getattr(cls, "__attrs_attrs__", None)

    if attrs is None:
        if generic_base is not None:
            attrs = getattr(generic_base, "__attrs_attrs__", None)
            if attrs is not None:
                # Even though this is global state, stick it on here to speed
                # it up. We rely on `cls` being cached for this to be
                # efficient.
                cls.__attrs_attrs__ = attrs
                return attrs
        msg = f"{cls!r} is not an attrs-decorated class."
        raise NotAnAttrsClassError(msg)

    return attrs


def fields_dict(cls):
    """
    Return an ordered dictionary of *attrs* attributes for a class, whose keys
    are the attribute names.

    Args:
        cls (type): Class to introspect.

    Raises:
        TypeError: If *cls* is not a class.

        attrs.exceptions.NotAnAttrsClassError:
            If *cls* is not an *attrs* class.

    Returns:
        dict[str, attrs.Attribute]: Dict of attribute name to definition

    .. versionadded:: 18.1.0
    """
    if not isinstance(cls, type):
        msg = "Passed object must be a class."
        raise TypeError(msg)
    attrs = getattr(cls, "__attrs_attrs__", None)
    if attrs is None:
        msg = f"{cls!r} is not an attrs-decorated class."
        raise NotAnAttrsClassError(msg)
    return {a.name: a for a in attrs}


def validate(inst):
    """
    Validate all attributes on *inst* that have a validator.

    Leaves all exceptions through.

    Args:
        inst: Instance of a class with *attrs* attributes.
    """
    if _config._run_validators is False:
        return

    for a in fields(inst.__class__):
        v = a.validator
        if v is not None:
            v(inst, a, getattr(inst, a.name))


def _is_slot_attr(a_name, base_attr_map):
    """
    Check if the attribute name comes from a slot class.
    """
    cls = base_attr_map.get(a_name)
    return cls and "__slots__" in cls.__dict__


def _make_init_script(
    cls,
    attrs,
    pre_init,
    pre_init_has_args,
    post_init,
    frozen,
    slots,
    cache_hash,
    base_attr_map,
    is_exc,
    cls_on_setattr,
    attrs_init,
) -> tuple[str, dict, dict]:
    has_cls_on_setattr = (
        cls_on_setattr is not None and cls_on_setattr is not setters.NO_OP
    )

    if frozen and has_cls_on_setattr:
        msg = "Frozen classes can't use on_setattr."
        raise ValueError(msg)

    needs_cached_setattr = cache_hash or frozen
    filtered_attrs = []
    attr_dict = {}
    for a in attrs:
        if not a.init and a.default is NOTHING:
            continue

        filtered_attrs.append(a)
        attr_dict[a.name] = a

        if a.on_setattr is not None:
            if frozen is True:
                msg = "Frozen classes can't use on_setattr."
                raise ValueError(msg)

            needs_cached_setattr = True
        elif has_cls_on_setattr and a.on_setattr is not setters.NO_OP:
            needs_cached_setattr = True

    script, globs, annotations = _attrs_to_init_script(
        filtered_attrs,
        frozen,
        slots,
        pre_init,
        pre_init_has_args,
        post_init,
        cache_hash,
        base_attr_map,
        is_exc,
        needs_cached_setattr,
        has_cls_on_setattr,
        "__attrs_init__" if attrs_init else "__init__",
    )
    if cls.__module__ in sys.modules:
        # This makes typing.get_type_hints(CLS.__init__) resolve string types.
        globs.update(sys.modules[cls.__module__].__dict__)

    globs.update({"NOTHING": NOTHING, "attr_dict": attr_dict})

    if needs_cached_setattr:
        # Save the lookup overhead in __init__ if we need to circumvent
        # setattr hooks.
        globs["_cached_setattr_get"] = _OBJ_SETATTR.__get__

    return script, globs, annotations


def _setattr(attr_name: str, value_var: str, has_on_setattr: bool) -> str:
    """
    Use the cached object.setattr to set *attr_name* to *value_var*.
    """
    return f"_setattr('{attr_name}', {value_var})"


def _setattr_with_converter(
    attr_name: str, value_var: str, has_on_setattr: bool, converter: Converter
) -> str:
    """
    Use the cached object.setattr to set *attr_name* to *value_var*, but run
    its converter first.
    """
    return f"_setattr('{attr_name}', {converter._fmt_converter_call(attr_name, value_var)})"


def _assign(attr_name: str, value: str, has_on_setattr: bool) -> str:
    """
    Unless *attr_name* has an on_setattr hook, use normal assignment. Otherwise
    relegate to _setattr.
    """
    if has_on_setattr:
        return _setattr(attr_name, value, True)

    return f"self.{attr_name} = {value}"


def _assign_with_converter(
    attr_name: str, value_var: str, has_on_setattr: bool, converter: Converter
) -> str:
    """
    Unless *attr_name* has an on_setattr hook, use normal assignment after
    conversion. Otherwise relegate to _setattr_with_converter.
    """
    if has_on_setattr:
        return _setattr_with_converter(attr_name, value_var, True, converter)

    return f"self.{attr_name} = {converter._fmt_converter_call(attr_name, value_var)}"


def _determine_setters(
    frozen: bool, slots: bool, base_attr_map: dict[str, type]
):
    """
    Determine the correct setter functions based on whether a class is frozen
    and/or slotted.
    """
    if frozen is True:
        if slots is True:
            return (), _setattr, _setattr_with_converter

        # Dict frozen classes assign directly to __dict__.
        # But only if the attribute doesn't come from an ancestor slot
        # class.
        # Note _inst_dict will be used again below if cache_hash is True

        def fmt_setter(
            attr_name: str, value_var: str, has_on_setattr: bool
        ) -> str:
            if _is_slot_attr(attr_name, base_attr_map):
                return _setattr(attr_name, value_var, has_on_setattr)

            return f"_inst_dict['{attr_name}'] = {value_var}"

        def fmt_setter_with_converter(
            attr_name: str,
            value_var: str,
            has_on_setattr: bool,
            converter: Converter,
        ) -> str:
            if has_on_setattr or _is_slot_attr(attr_name, base_attr_map):
                return _setattr_with_converter(
                    attr_name, value_var, has_on_setattr, converter
                )

            return f"_inst_dict['{attr_name}'] = {converter._fmt_converter_call(attr_name, value_var)}"

        return (
            ("_inst_dict = self.__dict__",),
            fmt_setter,
            fmt_setter_with_converter,
        )

    # Not frozen -- we can just assign directly.
    return (), _assign, _assign_with_converter


def _attrs_to_init_script(
    attrs: list[Attribute],
    is_frozen: bool,
    is_slotted: bool,
    call_pre_init: bool,
    pre_init_has_args: bool,
    call_post_init: bool,
    does_cache_hash: bool,
    base_attr_map: dict[str, type],
    is_exc: bool,
    needs_cached_setattr: bool,
    has_cls_on_setattr: bool,
    method_name: str,
) -> tuple[str, dict, dict]:
    """
    Return a script of an initializer for *attrs*, a dict of globals, and
    annotations for the initializer.

    The globals are required by the generated script.
    """
    lines = ["self.__attrs_pre_init__()"] if call_pre_init else []

    if needs_cached_setattr:
        lines.append(
            # Circumvent the __setattr__ descriptor to save one lookup per
            # assignment. Note _setattr will be used again below if
            # does_cache_hash is True.
            "_setattr = _cached_setattr_get(self)"
        )

    extra_lines, fmt_setter, fmt_setter_with_converter = _determine_setters(
        is_frozen, is_slotted, base_attr_map
    )
    lines.extend(extra_lines)

    args = []
    kw_only_args = []
    attrs_to_validate = []

    # This is a dictionary of names to validator and converter callables.
    # Injecting this into __init__ globals lets us avoid lookups.
    names_for_globals = {}
    annotations = {"return": None}

    for a in attrs:
        if a.validator:
            attrs_to_validate.append(a)

        attr_name = a.name
        has_on_setattr = a.on_setattr is not None or (
            a.on_setattr is not setters.NO_OP and has_cls_on_setattr
        )
        # a.alias is set to maybe-mangled attr_name in _ClassBuilder if not
        # explicitly provided
        arg_name = a.alias

        has_factory = isinstance(a.default, Factory)
        maybe_self = "self" if has_factory and a.default.takes_self else ""

        if a.converter is not None and not isinstance(a.converter, Converter):
            converter = Converter(a.converter)
        else:
            converter = a.converter

        if a.init is False:
            if has_factory:
                init_factory_name = _INIT_FACTORY_PAT % (a.name,)
                if converter is not None:
                    lines.append(
                        fmt_setter_with_converter(
                            attr_name,
                            init_factory_name + f"({maybe_self})",
                            has_on_setattr,
                            converter,
                        )
                    )
                    names_for_globals[converter._get_global_name(a.name)] = (
                        converter.converter
                    )
                else:
                    lines.append(
                        fmt_setter(
                            attr_name,
                            init_factory_name + f"({maybe_self})",
                            has_on_setattr,
                        )
                    )
                names_for_globals[init_factory_name] = a.default.factory
            elif converter is not None:
                lines.append(
                    fmt_setter_with_converter(
                        attr_name,
                        f"attr_dict['{attr_name}'].default",
                        has_on_setattr,
                        converter,
                    )
                )
                names_for_globals[converter._get_global_name(a.name)] = (
                    converter.converter
                )
            else:
                lines.append(
                    fmt_setter(
                        attr_name,
                        f"attr_dict['{attr_name}'].default",
                        has_on_setattr,
                    )
                )
        elif a.default is not NOTHING and not has_factory:
            arg = f"{arg_name}=attr_dict['{attr_name}'].default"
            if a.kw_only:
                kw_only_args.append(arg)
            else:
                args.append(arg)

            if converter is not None:
                lines.append(
                    fmt_setter_with_converter(
                        attr_name, arg_name, has_on_setattr, converter
                    )
                )
                names_for_globals[converter._get_global_name(a.name)] = (
                    converter.converter
                )
            else:
                lines.append(fmt_setter(attr_name, arg_name, has_on_setattr))

        elif has_factory:
            arg = f"{arg_name}=NOTHING"
            if a.kw_only:
                kw_only_args.append(arg)
            else:
                args.append(arg)
            lines.append(f"if {arg_name} is not NOTHING:")

            init_factory_name = _INIT_FACTORY_PAT % (a.name,)
            if converter is not None:
                lines.append(
                    "    "
                    + fmt_setter_with_converter(
                        attr_name, arg_name, has_on_setattr, converter
                    )
                )
                lines.append("else:")
                lines.append(
                    "    "
                    + fmt_setter_with_converter(
                        attr_name,
                        init_factory_name + "(" + maybe_self + ")",
                        has_on_setattr,
                        converter,
                    )
                )
                names_for_globals[converter._get_global_name(a.name)] = (
                    converter.converter
                )
            else:
                lines.append(
                    "    " + fmt_setter(attr_name, arg_name, has_on_setattr)
                )
                lines.append("else:")
                lines.append(
                    "    "
                    + fmt_setter(
                        attr_name,
                        init_factory_name + "(" + maybe_self + ")",
                        has_on_setattr,
                    )
                )
            names_for_globals[init_factory_name] = a.default.factory
        else:
            if a.kw_only:
                kw_only_args.append(arg_name)
            else:
                args.append(arg_name)

            if converter is not None:
                lines.append(
                    fmt_setter_with_converter(
                        attr_name, arg_name, has_on_setattr, converter
                    )
                )
                names_for_globals[converter._get_global_name(a.name)] = (
                    converter.converter
                )
            else:
                lines.append(fmt_setter(attr_name, arg_name, has_on_setattr))

        if a.init is True:
            if a.type is not None and converter is None:
                annotations[arg_name] = a.type
            elif converter is not None and converter._first_param_type:
                # Use the type from the converter if present.
                annotations[arg_name] = converter._first_param_type

    if attrs_to_validate:  # we can skip this if there are no validators.
        names_for_globals["_config"] = _config
        lines.append("if _config._run_validators is True:")
        for a in attrs_to_validate:
            val_name = "__attr_validator_" + a.name
            attr_name = "__attr_" + a.name
            lines.append(f"    {val_name}(self, {attr_name}, self.{a.name})")
            names_for_globals[val_name] = a.validator
            names_for_globals[attr_name] = a

    if call_post_init:
        lines.append("self.__attrs_post_init__()")

    # Because this is set only after __attrs_post_init__ is called, a crash
    # will result if post-init tries to access the hash code.  This seemed
    # preferable to setting this beforehand, in which case alteration to field
    # values during post-init combined with post-init accessing the hash code
    # would result in silent bugs.
    if does_cache_hash:
        if is_frozen:
            if is_slotted:
                init_hash_cache = f"_setattr('{_HASH_CACHE_FIELD}', None)"
            else:
                init_hash_cache = f"_inst_dict['{_HASH_CACHE_FIELD}'] = None"
        else:
            init_hash_cache = f"self.{_HASH_CACHE_FIELD} = None"
        lines.append(init_hash_cache)

    # For exceptions we rely on BaseException.__init__ for proper
    # initialization.
    if is_exc:
        vals = ",".join(f"self.{a.name}" for a in attrs if a.init)

        lines.append(f"BaseException.__init__(self, {vals})")

    args = ", ".join(args)
    pre_init_args = args
    if kw_only_args:
        # leading comma & kw_only args
        args += f"{', ' if args else ''}*, {', '.join(kw_only_args)}"
        pre_init_kw_only_args = ", ".join(
            [
                f"{kw_arg_name}={kw_arg_name}"
                # We need to remove the defaults from the kw_only_args.
                for kw_arg_name in (kwa.split("=")[0] for kwa in kw_only_args)
            ]
        )
        pre_init_args += ", " if pre_init_args else ""
        pre_init_args += pre_init_kw_only_args

    if call_pre_init and pre_init_has_args:
        # If pre init method has arguments, pass same arguments as `__init__`.
        lines[0] = f"self.__attrs_pre_init__({pre_init_args})"

    # Python <3.12 doesn't allow backslashes in f-strings.
    NL = "\n    "
    return (
        f"""def {method_name}(self, {args}):
    {NL.join(lines) if lines else "pass"}
""",
        names_for_globals,
        annotations,
    )


def _default_init_alias_for(name: str) -> str:
    """
    The default __init__ parameter name for a field.

    This performs private-name adjustment via leading-unscore stripping,
    and is the default value of Attribute.alias if not provided.
    """

    return name.lstrip("_")


class Attribute:
    """
    *Read-only* representation of an attribute.

    .. warning::

       You should never instantiate this class yourself.

    The class has *all* arguments of `attr.ib` (except for ``factory`` which is
    only syntactic sugar for ``default=Factory(...)`` plus the following:

    - ``name`` (`str`): The name of the attribute.
    - ``alias`` (`str`): The __init__ parameter name of the attribute, after
      any explicit overrides and default private-attribute-name handling.
    - ``inherited`` (`bool`): Whether or not that attribute has been inherited
      from a base class.
    - ``eq_key`` and ``order_key`` (`typing.Callable` or `None`): The
      callables that are used for comparing and ordering objects by this
      attribute, respectively. These are set by passing a callable to
      `attr.ib`'s ``eq``, ``order``, or ``cmp`` arguments. See also
      :ref:`comparison customization <custom-comparison>`.

    Instances of this class are frequently used for introspection purposes
    like:

    - `fields` returns a tuple of them.
    - Validators get them passed as the first argument.
    - The :ref:`field transformer <transform-fields>` hook receives a list of
      them.
    - The ``alias`` property exposes the __init__ parameter name of the field,
      with any overrides and default private-attribute handling applied.


    .. versionadded:: 20.1.0 *inherited*
    .. versionadded:: 20.1.0 *on_setattr*
    .. versionchanged:: 20.2.0 *inherited* is not taken into account for
        equality checks and hashing anymore.
    .. versionadded:: 21.1.0 *eq_key* and *order_key*
    .. versionadded:: 22.2.0 *alias*

    For the full version history of the fields, see `attr.ib`.
    """

    # These slots must NOT be reordered because we use them later for
    # instantiation.
    __slots__ = (  # noqa: RUF023
        "name",
        "default",
        "validator",
        "repr",
        "eq",
        "eq_key",
        "order",
        "order_key",
        "hash",
        "init",
        "metadata",
        "type",
        "converter",
        "kw_only",
        "inherited",
        "on_setattr",
        "alias",
    )

    def __init__(
        self,
        name,
        default,
        validator,
        repr,
        cmp,  # XXX: unused, remove along with other cmp code.
        hash,
        init,
        inherited,
        metadata=None,
        type=None,
        converter=None,
        kw_only=False,
        eq=None,
        eq_key=None,
        order=None,
        order_key=None,
        on_setattr=None,
        alias=None,
    ):
        eq, eq_key, order, order_key = _determine_attrib_eq_order(
            cmp, eq_key or eq, order_key or order, True
        )

        # Cache this descriptor here to speed things up later.
        bound_setattr = _OBJ_SETATTR.__get__(self)

        # Despite the big red warning, people *do* instantiate `Attribute`
        # themselves.
        bound_setattr("name", name)
        bound_setattr("default", default)
        bound_setattr("validator", validator)
        bound_setattr("repr", repr)
        bound_setattr("eq", eq)
        bound_setattr("eq_key", eq_key)
        bound_setattr("order", order)
        bound_setattr("order_key", order_key)
        bound_setattr("hash", hash)
        bound_setattr("init", init)
        bound_setattr("converter", converter)
        bound_setattr(
            "metadata",
            (
                types.MappingProxyType(dict(metadata))  # Shallow copy
                if metadata
                else _EMPTY_METADATA_SINGLETON
            ),
        )
        bound_setattr("type", type)
        bound_setattr("kw_only", kw_only)
        bound_setattr("inherited", inherited)
        bound_setattr("on_setattr", on_setattr)
        bound_setattr("alias", alias)

    def __setattr__(self, name, value):
        raise FrozenInstanceError

    @classmethod
    def from_counting_attr(cls, name: str, ca: _CountingAttr, type=None):
        # type holds the annotated value. deal with conflicts:
        if type is None:
            type = ca.type
        elif ca.type is not None:
            msg = f"Type annotation and type argument cannot both be present for '{name}'."
            raise ValueError(msg)
        return cls(
            name,
            ca._default,
            ca._validator,
            ca.repr,
            None,
            ca.hash,
            ca.init,
            False,
            ca.metadata,
            type,
            ca.converter,
            ca.kw_only,
            ca.eq,
            ca.eq_key,
            ca.order,
            ca.order_key,
            ca.on_setattr,
            ca.alias,
        )

    # Don't use attrs.evolve since fields(Attribute) doesn't work
    def evolve(self, **changes):
        """
        Copy *self* and apply *changes*.

        This works similarly to `attrs.evolve` but that function does not work
        with :class:`attrs.Attribute`.

        It is mainly meant to be used for `transform-fields`.

        .. versionadded:: 20.3.0
        """
        new = copy.copy(self)

        new._setattrs(changes.items())

        return new

    # Don't use _add_pickle since fields(Attribute) doesn't work
    def __getstate__(self):
        """
        Play nice with pickle.
        """
        return tuple(
            getattr(self, name) if name != "metadata" else dict(self.metadata)
            for name in self.__slots__
        )

    def __setstate__(self, state):
        """
        Play nice with pickle.
        """
        self._setattrs(zip(self.__slots__, state))

    def _setattrs(self, name_values_pairs):
        bound_setattr = _OBJ_SETATTR.__get__(self)
        for name, value in name_values_pairs:
            if name != "metadata":
                bound_setattr(name, value)
            else:
                bound_setattr(
                    name,
                    (
                        types.MappingProxyType(dict(value))
                        if value
                        else _EMPTY_METADATA_SINGLETON
                    ),
                )


_a = [
    Attribute(
        name=name,
        default=NOTHING,
        validator=None,
        repr=True,
        cmp=None,
        eq=True,
        order=False,
        hash=(name != "metadata"),
        init=True,
        inherited=False,
        alias=_default_init_alias_for(name),
    )
    for name in Attribute.__slots__
]

Attribute = _add_hash(
    _add_eq(
        _add_repr(Attribute, attrs=_a),
        attrs=[a for a in _a if a.name != "inherited"],
    ),
    attrs=[a for a in _a if a.hash and a.name != "inherited"],
)


class _CountingAttr:
    """
    Intermediate representation of attributes that uses a counter to preserve
    the order in which the attributes have been defined.

    *Internal* data structure of the attrs library.  Running into is most
    likely the result of a bug like a forgotten `@attr.s` decorator.
    """

    __slots__ = (
        "_default",
        "_validator",
        "alias",
        "converter",
        "counter",
        "eq",
        "eq_key",
        "hash",
        "init",
        "kw_only",
        "metadata",
        "on_setattr",
        "order",
        "order_key",
        "repr",
        "type",
    )
    __attrs_attrs__ = (
        *tuple(
            Attribute(
                name=name,
                alias=_default_init_alias_for(name),
                default=NOTHING,
                validator=None,
                repr=True,
                cmp=None,
                hash=True,
                init=True,
                kw_only=False,
                eq=True,
                eq_key=None,
                order=False,
                order_key=None,
                inherited=False,
                on_setattr=None,
            )
            for name in (
                "counter",
                "_default",
                "repr",
                "eq",
                "order",
                "hash",
                "init",
                "on_setattr",
                "alias",
            )
        ),
        Attribute(
            name="metadata",
            alias="metadata",
            default=None,
            validator=None,
            repr=True,
            cmp=None,
            hash=False,
            init=True,
            kw_only=False,
            eq=True,
            eq_key=None,
            order=False,
            order_key=None,
            inherited=False,
            on_setattr=None,
        ),
    )
    cls_counter = 0

    def __init__(
        self,
        default,
        validator,
        repr,
        cmp,
        hash,
        init,
        converter,
        metadata,
        type,
        kw_only,
        eq,
        eq_key,
        order,
        order_key,
        on_setattr,
        alias,
    ):
        _CountingAttr.cls_counter += 1
        self.counter = _CountingAttr.cls_counter
        self._default = default
        self._validator = validator
        self.converter = converter
        self.repr = repr
        self.eq = eq
        self.eq_key = eq_key
        self.order = order
        self.order_key = order_key
        self.hash = hash
        self.init = init
        self.metadata = metadata
        self.type = type
        self.kw_only = kw_only
        self.on_setattr = on_setattr
        self.alias = alias

    def validator(self, meth):
        """
        Decorator that adds *meth* to the list of validators.

        Returns *meth* unchanged.

        .. versionadded:: 17.1.0
        """
        if self._validator is None:
            self._validator = meth
        else:
            self._validator = and_(self._validator, meth)
        return meth

    def default(self, meth):
        """
        Decorator that allows to set the default for an attribute.

        Returns *meth* unchanged.

        Raises:
            DefaultAlreadySetError: If default has been set before.

        .. versionadded:: 17.1.0
        """
        if self._default is not NOTHING:
            raise DefaultAlreadySetError

        self._default = Factory(meth, takes_self=True)

        return meth


_CountingAttr = _add_eq(_add_repr(_CountingAttr))


class Factory:
    """
    Stores a factory callable.

    If passed as the default value to `attrs.field`, the factory is used to
    generate a new value.

    Args:
        factory (typing.Callable):
            A callable that takes either none or exactly one mandatory
            positional argument depending on *takes_self*.

        takes_self (bool):
            Pass the partially initialized instance that is being initialized
            as a positional argument.

    .. versionadded:: 17.1.0  *takes_self*
    """

    __slots__ = ("factory", "takes_self")

    def __init__(self, factory, takes_self=False):
        self.factory = factory
        self.takes_self = takes_self

    def __getstate__(self):
        """
        Play nice with pickle.
        """
        return tuple(getattr(self, name) for name in self.__slots__)

    def __setstate__(self, state):
        """
        Play nice with pickle.
        """
        for name, value in zip(self.__slots__, state):
            setattr(self, name, value)


_f = [
    Attribute(
        name=name,
        default=NOTHING,
        validator=None,
        repr=True,
        cmp=None,
        eq=True,
        order=False,
        hash=True,
        init=True,
        inherited=False,
    )
    for name in Factory.__slots__
]

Factory = _add_hash(_add_eq(_add_repr(Factory, attrs=_f), attrs=_f), attrs=_f)


class Converter:
    """
    Stores a converter callable.

    Allows for the wrapped converter to take additional arguments. The
    arguments are passed in the order they are documented.

    Args:
        converter (Callable): A callable that converts the passed value.

        takes_self (bool):
            Pass the partially initialized instance that is being initialized
            as a positional argument. (default: `False`)

        takes_field (bool):
            Pass the field definition (an :class:`Attribute`) into the
            converter as a positional argument. (default: `False`)

    .. versionadded:: 24.1.0
    """

    __slots__ = (
        "__call__",
        "_first_param_type",
        "_global_name",
        "converter",
        "takes_field",
        "takes_self",
    )

    def __init__(self, converter, *, takes_self=False, takes_field=False):
        self.converter = converter
        self.takes_self = takes_self
        self.takes_field = takes_field

        ex = _AnnotationExtractor(converter)
        self._first_param_type = ex.get_first_param_type()

        if not (self.takes_self or self.takes_field):
            self.__call__ = lambda value, _, __: self.converter(value)
        elif self.takes_self and not self.takes_field:
            self.__call__ = lambda value, instance, __: self.converter(
                value, instance
            )
        elif not self.takes_self and self.takes_field:
            self.__call__ = lambda value, __, field: self.converter(
                value, field
            )
        else:
            self.__call__ = lambda value, instance, field: self.converter(
                value, instance, field
            )

        rt = ex.get_return_type()
        if rt is not None:
            self.__call__.__annotations__["return"] = rt

    @staticmethod
    def _get_global_name(attr_name: str) -> str:
        """
        Return the name that a converter for an attribute name *attr_name*
        would have.
        """
        return f"__attr_converter_{attr_name}"

    def _fmt_converter_call(self, attr_name: str, value_var: str) -> str:
        """
        Return a string that calls the converter for an attribute name
        *attr_name* and the value in variable named *value_var* according to
        `self.takes_self` and `self.takes_field`.
        """
        if not (self.takes_self or self.takes_field):
            return f"{self._get_global_name(attr_name)}({value_var})"

        if self.takes_self and self.takes_field:
            return f"{self._get_global_name(attr_name)}({value_var}, self, attr_dict['{attr_name}'])"

        if self.takes_self:
            return f"{self._get_global_name(attr_name)}({value_var}, self)"

        return f"{self._get_global_name(attr_name)}({value_var}, attr_dict['{attr_name}'])"

    def __getstate__(self):
        """
        Return a dict containing only converter and takes_self -- the rest gets
        computed when loading.
        """
        return {
            "converter": self.converter,
            "takes_self": self.takes_self,
            "takes_field": self.takes_field,
        }

    def __setstate__(self, state):
        """
        Load instance from state.
        """
        self.__init__(**state)


_f = [
    Attribute(
        name=name,
        default=NOTHING,
        validator=None,
        repr=True,
        cmp=None,
        eq=True,
        order=False,
        hash=True,
        init=True,
        inherited=False,
    )
    for name in ("converter", "takes_self", "takes_field")
]

Converter = _add_hash(
    _add_eq(_add_repr(Converter, attrs=_f), attrs=_f), attrs=_f
)


def make_class(
    name, attrs, bases=(object,), class_body=None, **attributes_arguments
):
    r"""
    A quick way to create a new class called *name* with *attrs*.

    .. note::

        ``make_class()`` is a thin wrapper around `attr.s`, not `attrs.define`
        which means that it doesn't come with some of the improved defaults.

        For example, if you want the same ``on_setattr`` behavior as in
        `attrs.define`, you have to pass the hooks yourself: ``make_class(...,
        on_setattr=setters.pipe(setters.convert, setters.validate)``

    .. warning::

        It is *your* duty to ensure that the class name and the attribute names
        are valid identifiers. ``make_class()`` will *not* validate them for
        you.

    Args:
        name (str): The name for the new class.

        attrs (list | dict):
            A list of names or a dictionary of mappings of names to `attr.ib`\
            s / `attrs.field`\ s.

            The order is deduced from the order of the names or attributes
            inside *attrs*.  Otherwise the order of the definition of the
            attributes is used.

        bases (tuple[type, ...]): Classes that the new class will subclass.

        class_body (dict):
            An optional dictionary of class attributes for the new class.

        attributes_arguments: Passed unmodified to `attr.s`.

    Returns:
        type: A new class with *attrs*.

    .. versionadded:: 17.1.0 *bases*
    .. versionchanged:: 18.1.0 If *attrs* is ordered, the order is retained.
    .. versionchanged:: 23.2.0 *class_body*
    .. versionchanged:: 25.2.0 Class names can now be unicode.
    """
    # Class identifiers are converted into the normal form NFKC while parsing
    name = unicodedata.normalize("NFKC", name)

    if isinstance(attrs, dict):
        cls_dict = attrs
    elif isinstance(attrs, (list, tuple)):
        cls_dict = {a: attrib() for a in attrs}
    else:
        msg = "attrs argument must be a dict or a list."
        raise TypeError(msg)

    pre_init = cls_dict.pop("__attrs_pre_init__", None)
    post_init = cls_dict.pop("__attrs_post_init__", None)
    user_init = cls_dict.pop("__init__", None)

    body = {}
    if class_body is not None:
        body.update(class_body)
    if pre_init is not None:
        body["__attrs_pre_init__"] = pre_init
    if post_init is not None:
        body["__attrs_post_init__"] = post_init
    if user_init is not None:
        body["__init__"] = user_init

    type_ = types.new_class(name, bases, {}, lambda ns: ns.update(body))

    # For pickling to work, the __module__ variable needs to be set to the
    # frame where the class is created.  Bypass this step in environments where
    # sys._getframe is not defined (Jython for example) or sys._getframe is not
    # defined for arguments greater than 0 (IronPython).
    with contextlib.suppress(AttributeError, ValueError):
        type_.__module__ = sys._getframe(1).f_globals.get(
            "__name__", "__main__"
        )

    # We do it here for proper warnings with meaningful stacklevel.
    cmp = attributes_arguments.pop("cmp", None)
    (
        attributes_arguments["eq"],
        attributes_arguments["order"],
    ) = _determine_attrs_eq_order(
        cmp,
        attributes_arguments.get("eq"),
        attributes_arguments.get("order"),
        True,
    )

    cls = _attrs(these=cls_dict, **attributes_arguments)(type_)
    # Only add type annotations now or "_attrs()" will complain:
    cls.__annotations__ = {
        k: v.type for k, v in cls_dict.items() if v.type is not None
    }
    return cls


# These are required by within this module so we define them here and merely
# import into .validators / .converters.


@attrs(slots=True, unsafe_hash=True)
class _AndValidator:
    """
    Compose many validators to a single one.
    """

    _validators = attrib()

    def __call__(self, inst, attr, value):
        for v in self._validators:
            v(inst, attr, value)


def and_(*validators):
    """
    A validator that composes multiple validators into one.

    When called on a value, it runs all wrapped validators.

    Args:
        validators (~collections.abc.Iterable[typing.Callable]):
            Arbitrary number of validators.

    .. versionadded:: 17.1.0
    """
    vals = []
    for validator in validators:
        vals.extend(
            validator._validators
            if isinstance(validator, _AndValidator)
            else [validator]
        )

    return _AndValidator(tuple(vals))


def pipe(*converters):
    """
    A converter that composes multiple converters into one.

    When called on a value, it runs all wrapped converters, returning the
    *last* value.

    Type annotations will be inferred from the wrapped converters', if they
    have any.

        converters (~collections.abc.Iterable[typing.Callable]):
            Arbitrary number of converters.

    .. versionadded:: 20.1.0
    """

    return_instance = any(isinstance(c, Converter) for c in converters)

    if return_instance:

        def pipe_converter(val, inst, field):
            for c in converters:
                val = (
                    c(val, inst, field) if isinstance(c, Converter) else c(val)
                )

            return val

    else:

        def pipe_converter(val):
            for c in converters:
                val = c(val)

            return val

    if not converters:
        # If the converter list is empty, pipe_converter is the identity.
        A = TypeVar("A")
        pipe_converter.__annotations__.update({"val": A, "return": A})
    else:
        # Get parameter type from first converter.
        t = _AnnotationExtractor(converters[0]).get_first_param_type()
        if t:
            pipe_converter.__annotations__["val"] = t

        last = converters[-1]
        if not PY_3_11_PLUS and isinstance(last, Converter):
            last = last.__call__

        # Get return type from last converter.
        rt = _AnnotationExtractor(last).get_return_type()
        if rt:
            pipe_converter.__annotations__["return"] = rt

    if return_instance:
        return Converter(pipe_converter, takes_self=True, takes_field=True)
    return pipe_converter

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\_types.py ===
import enum
import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional, Union

import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    Json,
    field_validator,
    model_validator,
)
from typing_extensions import Required, TypedDict

from litellm.types.integrations.slack_alerting import AlertType
from litellm.types.llms.openai import AllMessageValues, OpenAIFileObject
from litellm.types.mcp import (
    MCPAuthType,
    MCPSpecVersion,
    MCPSpecVersionType,
    MCPTransport,
    MCPTransportType,
)
from litellm.types.router import RouterErrors, UpdateRouterConfig
from litellm.types.utils import (
    CallTypes,
    EmbeddingResponse,
    GenericBudgetConfigType,
    ImageResponse,
    LiteLLMBatch,
    LiteLLMFineTuningJob,
    LiteLLMPydanticObjectBase,
    ModelResponse,
    ProviderField,
    StandardCallbackDynamicParams,
    StandardLoggingGuardrailInformation,
    StandardLoggingMCPToolCall,
    StandardLoggingModelInformation,
    StandardLoggingPayloadErrorInformation,
    StandardLoggingPayloadStatus,
    StandardLoggingVectorStoreRequest,
    StandardPassThroughResponseObject,
    TextCompletionResponse,
)

from .types_utils.utils import get_instance_fn, validate_custom_validate_return_type

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    Span = Union[_Span, Any]
else:
    Span = Any


class LiteLLMTeamRoles(enum.Enum):
    # team admin
    TEAM_ADMIN = "admin"
    # team member
    TEAM_MEMBER = "user"


class LitellmUserRoles(str, enum.Enum):
    """
    Admin Roles:
    PROXY_ADMIN: admin over the platform
    PROXY_ADMIN_VIEW_ONLY: can login, view all own keys, view all spend
    ORG_ADMIN: admin over a specific organization, can create teams, users only within their organization

    Internal User Roles:
    INTERNAL_USER: can login, view/create/delete their own keys, view their spend
    INTERNAL_USER_VIEW_ONLY: can login, view their own keys, view their own spend


    Team Roles:
    TEAM: used for JWT auth


    Customer Roles:
    CUSTOMER: External users -> these are customers

    """

    # Admin Roles
    PROXY_ADMIN = "proxy_admin"
    PROXY_ADMIN_VIEW_ONLY = "proxy_admin_viewer"

    # Organization admins
    ORG_ADMIN = "org_admin"

    # Internal User Roles
    INTERNAL_USER = "internal_user"
    INTERNAL_USER_VIEW_ONLY = "internal_user_viewer"

    # Team Roles
    TEAM = "team"

    # Customer Roles - External users of proxy
    CUSTOMER = "customer"

    def __str__(self):
        return str(self.value)

    def values(self) -> List[str]:
        return list(self.__annotations__.keys())

    @property
    def description(self):
        """
        Descriptions for the enum values
        """
        descriptions = {
            "proxy_admin": "admin over litellm proxy, has all permissions",
            "proxy_admin_viewer": "view all keys, view all spend",
            "internal_user": "view/create/delete their own keys, view their own spend",
            "internal_user_viewer": "view their own keys, view their own spend",
            "team": "team scope used for JWT auth",
            "customer": "customer",
        }
        return descriptions.get(self.value, "")

    @property
    def ui_label(self):
        """
        UI labels for the enum values
        """
        ui_labels = {
            "proxy_admin": "Admin (All Permissions)",
            "proxy_admin_viewer": "Admin (View Only)",
            "internal_user": "Internal User (Create/Delete/View)",
            "internal_user_viewer": "Internal User (View Only)",
            "team": "Team",
            "customer": "Customer",
        }
        return ui_labels.get(self.value, "")

    @property
    def is_internal_user_role(self) -> bool:
        """returns true if this role is an `internal_user` or `internal_user_viewer` role"""
        return self.value in [
            self.INTERNAL_USER,
            self.INTERNAL_USER_VIEW_ONLY,
        ]


class LitellmTableNames(str, enum.Enum):
    """
    Enum for Table Names used by LiteLLM
    """

    TEAM_TABLE_NAME = "LiteLLM_TeamTable"
    USER_TABLE_NAME = "LiteLLM_UserTable"
    KEY_TABLE_NAME = "LiteLLM_VerificationToken"
    PROXY_MODEL_TABLE_NAME = "LiteLLM_ProxyModelTable"
    MANAGED_FILE_TABLE_NAME = "LiteLLM_ManagedFileTable"


class Litellm_EntityType(enum.Enum):
    """
    Enum for types of entities on litellm

    This enum allows specifying the type of entity that is being tracked in the database.
    """

    KEY = "key"
    USER = "user"
    END_USER = "end_user"
    TEAM = "team"
    TEAM_MEMBER = "team_member"
    ORGANIZATION = "organization"

    # global proxy level entity
    PROXY = "proxy"


def hash_token(token: str):
    import hashlib

    # Hash the string using SHA-256
    hashed_token = hashlib.sha256(token.encode()).hexdigest()

    return hashed_token


class LiteLLM_UpperboundKeyGenerateParams(LiteLLMPydanticObjectBase):
    """
    Set default upperbound to max budget a key called via `/key/generate` can be.

    Args:
        max_budget (Optional[float], optional): Max budget a key can be. Defaults to None.
        budget_duration (Optional[str], optional): Duration of the budget. Defaults to None.
        duration (Optional[str], optional): Duration of the key. Defaults to None.
        max_parallel_requests (Optional[int], optional): Max number of requests that can be made in parallel. Defaults to None.
        tpm_limit (Optional[int], optional): Tpm limit. Defaults to None.
        rpm_limit (Optional[int], optional): Rpm limit. Defaults to None.
    """

    max_budget: Optional[float] = None
    budget_duration: Optional[str] = None
    duration: Optional[str] = None
    max_parallel_requests: Optional[int] = None
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None


class KeyManagementRoutes(str, enum.Enum):
    """
    Enum for key management routes
    """

    # write routes
    KEY_GENERATE = "/key/generate"
    KEY_UPDATE = "/key/update"
    KEY_DELETE = "/key/delete"
    KEY_REGENERATE = "/key/regenerate"
    KEY_REGENERATE_WITH_PATH_PARAM = "/key/{key_id}/regenerate"
    KEY_BLOCK = "/key/block"
    KEY_UNBLOCK = "/key/unblock"

    # info and health routes
    KEY_INFO = "/key/info"
    KEY_HEALTH = "/key/health"

    # list routes
    KEY_LIST = "/key/list"


class LiteLLMRoutes(enum.Enum):
    openai_route_names = [
        "chat_completion",
        "completion",
        "embeddings",
        "image_generation",
        "audio_transcriptions",
        "moderations",
        "model_list",  # OpenAI /v1/models route
    ]
    openai_routes = [
        # chat completions
        "/engines/{model}/chat/completions",
        "/openai/deployments/{model}/chat/completions",
        "/chat/completions",
        "/v1/chat/completions",
        # completions
        "/engines/{model}/completions",
        "/openai/deployments/{model}/completions",
        "/completions",
        "/v1/completions",
        # embeddings
        "/engines/{model}/embeddings",
        "/openai/deployments/{model}/embeddings",
        "/embeddings",
        "/v1/embeddings",
        # image generation
        "/images/generations",
        "/v1/images/generations",
        # image edit
        "/images/edits",
        "/v1/images/edits",
        # audio transcription
        "/audio/transcriptions",
        "/v1/audio/transcriptions",
        # audio Speech
        "/audio/speech",
        "/v1/audio/speech",
        # moderations
        "/moderations",
        "/v1/moderations",
        # batches
        "/v1/batches",
        "/batches",
        "/v1/batches/{batch_id}",
        "/batches/{batch_id}",
        # files
        "/v1/files",
        "/files",
        "/v1/files/{file_id}",
        "/files/{file_id}",
        "/v1/files/{file_id}/content",
        "/files/{file_id}/content",
        # fine_tuning
        "/fine_tuning/jobs",
        "/v1/fine_tuning/jobs",
        "/fine_tuning/jobs/{fine_tuning_job_id}/cancel",
        "/v1/fine_tuning/jobs/{fine_tuning_job_id}/cancel",
        # assistants-related routes
        "/assistants",
        "/v1/assistants",
        "/v1/assistants/{assistant_id}",
        "/assistants/{assistant_id}",
        "/threads",
        "/v1/threads",
        "/threads/{thread_id}",
        "/v1/threads/{thread_id}",
        "/threads/{thread_id}/messages",
        "/v1/threads/{thread_id}/messages",
        "/threads/{thread_id}/runs",
        "/v1/threads/{thread_id}/runs",
        # models
        "/models",
        "/v1/models",
        # token counter
        "/utils/token_counter",
        "/utils/transform_request",
        # rerank
        "/rerank",
        "/v1/rerank",
        "/v2/rerank",
        # realtime
        "/realtime",
        "/v1/realtime",
        "/realtime?{model}",
        "/v1/realtime?{model}",
        # responses API
        "/responses",
        "/v1/responses",
        "/responses/{response_id}",
        "/v1/responses/{response_id}",
        "/responses/{response_id}/input_items",
        "/v1/responses/{response_id}/input_items",
    ]

    mapped_pass_through_routes = [
        "/bedrock",
        "/vertex-ai",
        "/vertex_ai",
        "/cohere",
        "/gemini",
        "/anthropic",
        "/langfuse",
        "/azure",
        "/openai",
        "/assemblyai",
        "/eu.assemblyai",
        "/vllm",
        "/mistral",
    ]

    anthropic_routes = [
        "/v1/messages",
        # MCP routes
        "/mcp/tools",
        "/mcp/tools/list",
        "/mcp/tools/call",
    ]

    apply_guardrail_routes = [
        "/guardrails/apply_guardrail",
    ]

    llm_api_routes = (
        openai_routes
        + anthropic_routes
        + mapped_pass_through_routes
        + apply_guardrail_routes
    )
    info_routes = [
        "/key/info",
        "/key/health",
        "/team/info",
        "/team/list",
        "/v2/team/list",
        "/organization/list",
        "/team/available",
        "/user/info",
        "/model/info",
        "/v1/model/info",
        "/v2/model/info",
        "/v2/key/info",
        "/model_group/info",
        "/health",
        "/key/list",
        "/user/filter/ui",
    ]

    # NOTE: ROUTES ONLY FOR MASTER KEY - only the Master Key should be able to Reset Spend
    master_key_only_routes = ["/global/spend/reset"]

    key_management_routes = [
        KeyManagementRoutes.KEY_GENERATE,
        KeyManagementRoutes.KEY_UPDATE,
        KeyManagementRoutes.KEY_DELETE,
        KeyManagementRoutes.KEY_INFO,
        KeyManagementRoutes.KEY_REGENERATE,
        KeyManagementRoutes.KEY_REGENERATE_WITH_PATH_PARAM,
        KeyManagementRoutes.KEY_LIST,
        KeyManagementRoutes.KEY_BLOCK,
        KeyManagementRoutes.KEY_UNBLOCK,
    ]

    management_routes = [
        # user
        "/user/new",
        "/user/update",
        "/user/delete",
        "/user/info",
        # team
        "/team/new",
        "/team/update",
        "/team/delete",
        "/team/list",
        "/v2/team/list",
        "/team/info",
        "/team/block",
        "/team/unblock",
        "/team/available",
        "/team/permissions_list",
        "/team/permissions_update",
        # model
        "/model/new",
        "/model/update",
        "/model/delete",
        "/model/info",
    ] + key_management_routes

    spend_tracking_routes = [
        # spend
        "/spend/keys",
        "/spend/users",
        "/spend/tags",
        "/spend/calculate",
        "/spend/logs",
    ]

    global_spend_tracking_routes = [
        # global spend
        "/global/spend/logs",
        "/global/spend",
        "/global/spend/keys",
        "/global/spend/teams",
        "/global/spend/end_users",
        "/global/spend/models",
        "/global/predict/spend/logs",
        "/global/spend/report",
        "/global/spend/provider",
    ]

    public_routes = set(
        [
            "/routes",
            "/",
            "/health/liveliness",
            "/health/liveness",
            "/health/readiness",
            "/test",
            "/config/yaml",
            "/metrics",
            "/litellm/.well-known/litellm-ui-config",
            "/.well-known/litellm-ui-config",
        ]
    )

    ui_routes = [
        "/sso",
        "/sso/get/ui_settings",
        "/login",
        "/key/info",
        "/config",
        "/spend",
        "/model/info",
        "/v2/model/info",
        "/v2/key/info",
        "/models",
        "/v1/models",
        "/global/spend",
        "/global/spend/logs",
        "/global/spend/keys",
        "/global/spend/models",
        "/global/predict/spend/logs",
        "/global/activity",
        "/health/services",
        "/get/litellm_model_cost_map",
    ] + info_routes

    internal_user_routes = (
        [
            "/global/spend/tags",
            "/global/spend/keys",
            "/global/spend/models",
            "/global/spend/provider",
            "/global/spend/end_users",
            "/global/activity",
            "/global/activity/model",
        ]
        + spend_tracking_routes
        + key_management_routes
    )

    internal_user_view_only_routes = (
        spend_tracking_routes + global_spend_tracking_routes
    )

    self_managed_routes = [
        "/team/member_add",
        "/team/member_delete",
        "/team/permissions_list",
        "/team/permissions_update",
        "/team/daily/activity",
        "/model/new",
        "/model/update",
        "/model/delete",
        "/user/daily/activity",
        "/model/{model_id}/update",
    ]  # routes that manage their own allowed/disallowed logic

    ## Org Admin Routes ##

    # Routes only an Org Admin Can Access
    org_admin_only_routes = [
        "/organization/info",
        "/organization/delete",
        "/organization/member_add",
        "/organization/member_update",
    ]

    # All routes accesible by an Org Admin
    org_admin_allowed_routes = (
        org_admin_only_routes + management_routes + self_managed_routes
    )


class LiteLLMPromptInjectionParams(LiteLLMPydanticObjectBase):
    heuristics_check: bool = False
    vector_db_check: bool = False
    llm_api_check: bool = False
    llm_api_name: Optional[str] = None
    llm_api_system_prompt: Optional[str] = None
    llm_api_fail_call_string: Optional[str] = None
    reject_as_response: Optional[bool] = Field(
        default=False,
        description="Return rejected request error message as a string to the user. Default behaviour is to raise an exception.",
    )

    @model_validator(mode="before")
    @classmethod
    def check_llm_api_params(cls, values):
        llm_api_check = values.get("llm_api_check")
        if llm_api_check is True:
            if "llm_api_name" not in values or not values["llm_api_name"]:
                raise ValueError(
                    "If llm_api_check is set to True, llm_api_name must be provided"
                )
            if (
                "llm_api_system_prompt" not in values
                or not values["llm_api_system_prompt"]
            ):
                raise ValueError(
                    "If llm_api_check is set to True, llm_api_system_prompt must be provided"
                )
            if (
                "llm_api_fail_call_string" not in values
                or not values["llm_api_fail_call_string"]
            ):
                raise ValueError(
                    "If llm_api_check is set to True, llm_api_fail_call_string must be provided"
                )
        return values


######### Request Class Definition ######
class ProxyChatCompletionRequest(LiteLLMPydanticObjectBase):
    model: str
    messages: List[Dict[str, str]]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stream: Optional[bool] = None
    stop: Optional[List[str]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    response_format: Optional[Dict[str, str]] = None
    seed: Optional[int] = None
    tools: Optional[List[str]] = None
    tool_choice: Optional[str] = None
    functions: Optional[List[str]] = None  # soon to be deprecated
    function_call: Optional[str] = None  # soon to be deprecated

    # Optional LiteLLM params
    caching: Optional[bool] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    api_key: Optional[str] = None
    num_retries: Optional[int] = None
    context_window_fallback_dict: Optional[Dict[str, str]] = None
    fallbacks: Optional[List[str]] = None
    metadata: Optional[Dict[str, str]] = {}
    deployment_id: Optional[str] = None
    request_timeout: Optional[int] = None

    model_config = ConfigDict(
        extra="allow"
    )  # allow params not defined here, these fall in litellm.completion(**kwargs)


class ModelInfoDelete(LiteLLMPydanticObjectBase):
    id: str


class ModelInfo(LiteLLMPydanticObjectBase):
    id: Optional[str]
    mode: Optional[Literal["embedding", "chat", "completion"]]
    input_cost_per_token: Optional[float] = 0.0
    output_cost_per_token: Optional[float] = 0.0
    max_tokens: Optional[int] = 2048  # assume 2048 if not set

    # for azure models we need users to specify the base model, one azure you can call deployments - azure/my-random-model
    # we look up the base model in model_prices_and_context_window.json
    base_model: Optional[
        Literal[
            "gpt-4-1106-preview",
            "gpt-4-32k",
            "gpt-4",
            "gpt-3.5-turbo-16k",
            "gpt-3.5-turbo",
            "text-embedding-ada-002",
        ]
    ]

    model_config = ConfigDict(protected_namespaces=(), extra="allow")

    @model_validator(mode="before")
    @classmethod
    def set_model_info(cls, values):
        if values.get("id") is None:
            values.update({"id": str(uuid.uuid4())})
        if values.get("mode") is None:
            values.update({"mode": None})
        if values.get("input_cost_per_token") is None:
            values.update({"input_cost_per_token": None})
        if values.get("output_cost_per_token") is None:
            values.update({"output_cost_per_token": None})
        if values.get("max_tokens") is None:
            values.update({"max_tokens": None})
        if values.get("base_model") is None:
            values.update({"base_model": None})
        return values


class ProviderInfo(LiteLLMPydanticObjectBase):
    name: str
    fields: List[ProviderField]


class BlockUsers(LiteLLMPydanticObjectBase):
    user_ids: List[str]  # required


class ModelParams(LiteLLMPydanticObjectBase):
    model_name: str
    litellm_params: dict
    model_info: ModelInfo

    model_config = ConfigDict(protected_namespaces=())

    @model_validator(mode="before")
    @classmethod
    def set_model_info(cls, values):
        if values.get("model_info") is None:
            values.update(
                {"model_info": ModelInfo(id=None, mode="chat", base_model=None)}
            )
        return values


class LiteLLM_ObjectPermissionBase(LiteLLMPydanticObjectBase):
    mcp_servers: Optional[List[str]] = None
    vector_stores: Optional[List[str]] = None


class GenerateRequestBase(LiteLLMPydanticObjectBase):
    """
    Overlapping schema between key and user generate/update requests
    """

    key_alias: Optional[str] = None
    duration: Optional[str] = None
    models: Optional[list] = []
    spend: Optional[float] = 0
    max_budget: Optional[float] = None
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    max_parallel_requests: Optional[int] = None
    metadata: Optional[dict] = {}
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None
    budget_duration: Optional[str] = None
    allowed_cache_controls: Optional[list] = []
    config: Optional[dict] = {}
    permissions: Optional[dict] = {}
    model_max_budget: Optional[dict] = (
        {}
    )  # {"gpt-4": 5.0, "gpt-3.5-turbo": 5.0}, defaults to {}

    model_config = ConfigDict(protected_namespaces=())
    model_rpm_limit: Optional[dict] = None
    model_tpm_limit: Optional[dict] = None
    guardrails: Optional[List[str]] = None
    blocked: Optional[bool] = None
    aliases: Optional[dict] = {}
    object_permission: Optional[LiteLLM_ObjectPermissionBase] = None


class KeyRequestBase(GenerateRequestBase):
    key: Optional[str] = None
    budget_id: Optional[str] = None
    tags: Optional[List[str]] = None
    enforced_params: Optional[List[str]] = None
    allowed_routes: Optional[list] = []


class GenerateKeyRequest(KeyRequestBase):
    soft_budget: Optional[float] = None
    send_invite_email: Optional[bool] = None


class GenerateKeyResponse(KeyRequestBase):
    key: str  # type: ignore
    key_name: Optional[str] = None
    expires: Optional[datetime] = None
    user_id: Optional[str] = None
    token_id: Optional[str] = None
    litellm_budget_table: Optional[Any] = None
    token: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def set_model_info(cls, values):
        if values.get("token") is not None:
            values.update({"key": values.get("token")})
        dict_fields = [
            "metadata",
            "aliases",
            "config",
            "permissions",
            "model_max_budget",
        ]
        for field in dict_fields:
            value = values.get(field)
            if value is not None and isinstance(value, str):
                try:
                    values[field] = json.loads(value)
                except json.JSONDecodeError:
                    raise ValueError(f"Field {field} should be a valid dictionary")

        return values


class UpdateKeyRequest(KeyRequestBase):
    # Note: the defaults of all Params here MUST BE NONE
    # else they will get overwritten
    key: str  # type: ignore
    duration: Optional[str] = None
    spend: Optional[float] = None
    metadata: Optional[dict] = None
    temp_budget_increase: Optional[float] = None
    temp_budget_expiry: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_temp_budget(self) -> "UpdateKeyRequest":
        if self.temp_budget_increase is not None or self.temp_budget_expiry is not None:
            if self.temp_budget_increase is None or self.temp_budget_expiry is None:
                raise ValueError(
                    "temp_budget_increase and temp_budget_expiry must be set together"
                )
        return self


class RegenerateKeyRequest(GenerateKeyRequest):
    # This needs to be different from UpdateKeyRequest, because "key" is optional for this
    key: Optional[str] = None
    duration: Optional[str] = None
    spend: Optional[float] = None
    metadata: Optional[dict] = None
    new_master_key: Optional[str] = None


class KeyRequest(LiteLLMPydanticObjectBase):
    keys: Optional[List[str]] = None
    key_aliases: Optional[List[str]] = None

    @model_validator(mode="before")
    @classmethod
    def validate_at_least_one(cls, values):
        if not values.get("keys") and not values.get("key_aliases"):
            raise ValueError(
                "At least one of 'keys' or 'key_aliases' must be provided."
            )
        return values


class LiteLLM_ModelTable(LiteLLMPydanticObjectBase):
    id: Optional[int] = None
    model_aliases: Optional[Union[str, dict]] = None  # json dump the dict
    created_by: str
    updated_by: str
    team: Optional["LiteLLM_TeamTable"] = None

    model_config = ConfigDict(protected_namespaces=())


class LiteLLM_ProxyModelTable(LiteLLMPydanticObjectBase):
    model_id: str
    model_name: str
    litellm_params: dict
    model_info: dict
    created_by: str
    updated_by: str

    @model_validator(mode="before")
    @classmethod
    def check_potential_json_str(cls, values):
        if isinstance(values.get("litellm_params"), str):
            try:
                values["litellm_params"] = json.loads(values["litellm_params"])
            except json.JSONDecodeError:
                pass
        if isinstance(values.get("model_info"), str):
            try:
                values["model_info"] = json.loads(values["model_info"])
            except json.JSONDecodeError:
                pass
        return values


# MCP Types
class SpecialMCPServerName(str, enum.Enum):
    all_team_servers = "all-team-mcpservers"
    all_proxy_servers = "all-proxy-mcpservers"


# MCP Proxy Request Types
class NewMCPServerRequest(LiteLLMPydanticObjectBase):
    server_id: Optional[str] = None
    alias: Optional[str] = None
    description: Optional[str] = None
    transport: MCPTransportType = MCPTransport.sse
    spec_version: MCPSpecVersionType = MCPSpecVersion.mar_2025
    auth_type: Optional[MCPAuthType] = None
    url: str


class UpdateMCPServerRequest(LiteLLMPydanticObjectBase):
    server_id: str
    alias: Optional[str] = None
    description: Optional[str] = None
    transport: MCPTransportType = MCPTransport.sse
    spec_version: MCPSpecVersionType = MCPSpecVersion.mar_2025
    auth_type: Optional[MCPAuthType] = None
    url: str


class LiteLLM_MCPServerTable(LiteLLMPydanticObjectBase):
    """Represents a LiteLLM_MCPServerTable record"""

    server_id: str
    alias: Optional[str] = None
    description: Optional[str] = None
    url: str
    transport: MCPTransportType
    spec_version: MCPSpecVersionType
    auth_type: Optional[MCPAuthType] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class NewUserRequestTeam(LiteLLMPydanticObjectBase):
    team_id: str
    max_budget_in_team: Optional[float] = None
    user_role: Literal["user", "admin"] = "user"


class NewUserRequest(GenerateRequestBase):
    max_budget: Optional[float] = None
    user_email: Optional[str] = None
    user_alias: Optional[str] = None
    user_role: Optional[
        Literal[
            LitellmUserRoles.PROXY_ADMIN,
            LitellmUserRoles.PROXY_ADMIN_VIEW_ONLY,
            LitellmUserRoles.INTERNAL_USER,
            LitellmUserRoles.INTERNAL_USER_VIEW_ONLY,
        ]
    ] = None
    teams: Optional[Union[List[str], List[NewUserRequestTeam]]] = None
    auto_create_key: bool = (
        True  # flag used for returning a key as part of the /user/new response
    )
    send_invite_email: Optional[bool] = None
    sso_user_id: Optional[str] = None
    organizations: Optional[List[str]] = None


class NewUserResponse(GenerateKeyResponse):
    max_budget: Optional[float] = None
    user_email: Optional[str] = None
    user_role: Optional[
        Literal[
            LitellmUserRoles.PROXY_ADMIN,
            LitellmUserRoles.PROXY_ADMIN_VIEW_ONLY,
            LitellmUserRoles.INTERNAL_USER,
            LitellmUserRoles.INTERNAL_USER_VIEW_ONLY,
        ]
    ] = None
    teams: Optional[list] = None
    user_alias: Optional[str] = None
    model_max_budget: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UpdateUserRequest(GenerateRequestBase):
    # Note: the defaults of all Params here MUST BE NONE
    # else they will get overwritten
    user_id: Optional[str] = None
    password: Optional[str] = None
    user_email: Optional[str] = None
    spend: Optional[float] = None
    metadata: Optional[dict] = None
    user_role: Optional[
        Literal[
            LitellmUserRoles.PROXY_ADMIN,
            LitellmUserRoles.PROXY_ADMIN_VIEW_ONLY,
            LitellmUserRoles.INTERNAL_USER,
            LitellmUserRoles.INTERNAL_USER_VIEW_ONLY,
        ]
    ] = None
    max_budget: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def check_user_info(cls, values):
        if values.get("user_id") is None and values.get("user_email") is None:
            raise ValueError("Either user id or user email must be provided")
        return values


class DeleteUserRequest(LiteLLMPydanticObjectBase):
    user_ids: List[str]  # required


AllowedModelRegion = Literal["eu", "us"]


class BudgetNewRequest(LiteLLMPydanticObjectBase):
    budget_id: Optional[str] = Field(default=None, description="The unique budget id.")
    max_budget: Optional[float] = Field(
        default=None,
        description="Requests will fail if this budget (in USD) is exceeded.",
    )
    soft_budget: Optional[float] = Field(
        default=None,
        description="Requests will NOT fail if this is exceeded. Will fire alerting though.",
    )
    max_parallel_requests: Optional[int] = Field(
        default=None, description="Max concurrent requests allowed for this budget id."
    )
    tpm_limit: Optional[int] = Field(
        default=None, description="Max tokens per minute, allowed for this budget id."
    )
    rpm_limit: Optional[int] = Field(
        default=None, description="Max requests per minute, allowed for this budget id."
    )
    budget_duration: Optional[str] = Field(
        default=None,
        description="Max duration budget should be set for (e.g. '1hr', '1d', '28d')",
    )
    model_max_budget: Optional[GenericBudgetConfigType] = Field(
        default=None,
        description="Max budget for each model (e.g. {'gpt-4o': {'max_budget': '0.0000001', 'budget_duration': '1d', 'tpm_limit': 1000, 'rpm_limit': 1000}})",
    )
    budget_reset_at: Optional[datetime] = Field(
        default=None,
        description="Datetime when the budget is reset",
    )


class BudgetRequest(LiteLLMPydanticObjectBase):
    budgets: List[str]


class BudgetDeleteRequest(LiteLLMPydanticObjectBase):
    id: str


class CustomerBase(LiteLLMPydanticObjectBase):
    user_id: str
    alias: Optional[str] = None
    spend: float = 0.0
    allowed_model_region: Optional[AllowedModelRegion] = None
    default_model: Optional[str] = None
    budget_id: Optional[str] = None
    litellm_budget_table: Optional[BudgetNewRequest] = None
    blocked: bool = False


class NewCustomerRequest(BudgetNewRequest):
    """
    Create a new customer, allocate a budget to them
    """

    user_id: str
    alias: Optional[str] = None  # human-friendly alias
    blocked: bool = False  # allow/disallow requests for this end-user
    budget_id: Optional[str] = None  # give either a budget_id or max_budget
    spend: Optional[float] = None
    allowed_model_region: Optional[AllowedModelRegion] = (
        None  # require all user requests to use models in this specific region
    )
    default_model: Optional[str] = (
        None  # if no equivalent model in allowed region - default all requests to this model
    )

    @model_validator(mode="before")
    @classmethod
    def check_user_info(cls, values):
        if values.get("max_budget") is not None and values.get("budget_id") is not None:
            raise ValueError("Set either 'max_budget' or 'budget_id', not both.")

        return values


class UpdateCustomerRequest(LiteLLMPydanticObjectBase):
    """
    Update a Customer, use this to update customer budgets etc

    """

    user_id: str
    alias: Optional[str] = None  # human-friendly alias
    blocked: bool = False  # allow/disallow requests for this end-user
    max_budget: Optional[float] = None
    budget_id: Optional[str] = None  # give either a budget_id or max_budget
    allowed_model_region: Optional[AllowedModelRegion] = (
        None  # require all user requests to use models in this specific region
    )
    default_model: Optional[str] = (
        None  # if no equivalent model in allowed region - default all requests to this model
    )


class DeleteCustomerRequest(LiteLLMPydanticObjectBase):
    """
    Delete multiple Customers
    """

    user_ids: List[str]


class MemberBase(LiteLLMPydanticObjectBase):
    user_id: Optional[str] = None
    user_email: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def check_user_info(cls, values):
        if not isinstance(values, dict):
            raise ValueError("input needs to be a dictionary")
        if values.get("user_id") is None and values.get("user_email") is None:
            raise ValueError("Either user id or user email must be provided")
        return values


class Member(MemberBase):
    role: Literal[
        "admin",
        "user",
    ]


class OrgMember(MemberBase):
    role: Literal[
        LitellmUserRoles.ORG_ADMIN,
        LitellmUserRoles.INTERNAL_USER,
        LitellmUserRoles.INTERNAL_USER_VIEW_ONLY,
    ]


class TeamBase(LiteLLMPydanticObjectBase):
    team_alias: Optional[str] = None
    team_id: Optional[str] = None
    organization_id: Optional[str] = None
    admins: list = []
    members: list = []
    members_with_roles: List[Member] = []
    team_member_permissions: Optional[List[str]] = None
    metadata: Optional[dict] = None
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None

    # Budget fields
    max_budget: Optional[float] = None
    budget_duration: Optional[str] = None

    models: list = []
    blocked: bool = False


class NewTeamRequest(TeamBase):
    model_aliases: Optional[dict] = None
    tags: Optional[list] = None
    guardrails: Optional[List[str]] = None
    object_permission: Optional[LiteLLM_ObjectPermissionBase] = None
    team_member_budget: Optional[float] = (
        None  # allow user to set a budget for all team members
    )

    model_config = ConfigDict(protected_namespaces=())


class GlobalEndUsersSpend(LiteLLMPydanticObjectBase):
    api_key: Optional[str] = None
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None


class UpdateTeamRequest(LiteLLMPydanticObjectBase):
    """
    UpdateTeamRequest, used by /team/update when you need to update a team

    team_id: str
    team_alias: Optional[str] = None
    organization_id: Optional[str] = None
    metadata: Optional[dict] = None
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None
    max_budget: Optional[float] = None
    models: Optional[list] = None
    blocked: Optional[bool] = None
    budget_duration: Optional[str] = None
    guardrails: Optional[List[str]] = None
    """

    team_id: str  # required
    team_alias: Optional[str] = None
    organization_id: Optional[str] = None
    metadata: Optional[dict] = None
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None
    max_budget: Optional[float] = None
    models: Optional[list] = None
    blocked: Optional[bool] = None
    budget_duration: Optional[str] = None
    tags: Optional[list] = None
    model_aliases: Optional[dict] = None
    guardrails: Optional[List[str]] = None
    object_permission: Optional[LiteLLM_ObjectPermissionBase] = None
    team_member_budget: Optional[float] = None


class ResetTeamBudgetRequest(LiteLLMPydanticObjectBase):
    """
    internal type used to reset the budget on a team
    used by reset_budget()

    team_id: str
    spend: float
    budget_reset_at: datetime
    """

    team_id: str
    spend: float
    budget_reset_at: datetime
    updated_at: datetime


class DeleteTeamRequest(LiteLLMPydanticObjectBase):
    team_ids: List[str]  # required


class BlockTeamRequest(LiteLLMPydanticObjectBase):
    team_id: str  # required


class BlockKeyRequest(LiteLLMPydanticObjectBase):
    key: str  # required


class AddTeamCallback(LiteLLMPydanticObjectBase):
    callback_name: str
    callback_type: Optional[Literal["success", "failure", "success_and_failure"]] = (
        "success_and_failure"
    )
    callback_vars: Dict[str, str]

    @model_validator(mode="before")
    @classmethod
    def validate_callback_vars(cls, values):
        callback_vars = values.get("callback_vars", {})
        valid_keys = set(StandardCallbackDynamicParams.__annotations__.keys())
        for key, value in callback_vars.items():
            if key not in valid_keys:
                raise ValueError(
                    f"Invalid callback variable: {key}. Must be one of {valid_keys}"
                )
            if not isinstance(value, str):
                callback_vars[key] = str(value)
        return values


class TeamCallbackMetadata(LiteLLMPydanticObjectBase):
    success_callback: Optional[List[str]] = []
    failure_callback: Optional[List[str]] = []
    callbacks: Optional[List[str]] = []
    # for now - only supported for langfuse
    callback_vars: Optional[Dict[str, str]] = {}

    @model_validator(mode="before")
    @classmethod
    def validate_callback_vars(cls, values):
        success_callback = values.get("success_callback", [])
        if success_callback is None:
            values.pop("success_callback", None)
        failure_callback = values.get("failure_callback", [])
        if failure_callback is None:
            values.pop("failure_callback", None)
        callbacks = values.get("callbacks", [])
        if callbacks is None:
            values.pop("callbacks", None)

        callback_vars = values.get("callback_vars", {})
        if callback_vars is None:
            values.pop("callback_vars", None)
        if all(val is None for val in values.values()):
            return {
                "success_callback": [],
                "failure_callback": [],
                "callbacks": [],
                "callback_vars": {},
            }
        valid_keys = set(StandardCallbackDynamicParams.__annotations__.keys())
        if callback_vars is not None:
            for key in callback_vars:
                if key not in valid_keys:
                    raise ValueError(
                        f"Invalid callback variable: {key}. Must be one of {valid_keys}"
                    )
        return values


class LiteLLM_ObjectPermissionTable(LiteLLMPydanticObjectBase):
    """Represents a LiteLLM_ObjectPermissionTable record"""

    object_permission_id: str
    mcp_servers: Optional[List[str]] = []
    vector_stores: Optional[List[str]] = []


class LiteLLM_TeamTable(TeamBase):
    team_id: str  # type: ignore
    spend: Optional[float] = None
    max_parallel_requests: Optional[int] = None
    budget_duration: Optional[str] = None
    budget_reset_at: Optional[datetime] = None
    model_id: Optional[int] = None
    litellm_model_table: Optional[LiteLLM_ModelTable] = None
    object_permission: Optional[LiteLLM_ObjectPermissionTable] = None
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    #########################################################
    # Object Permission - MCP, Vector Stores etc.
    #########################################################
    object_permission_id: Optional[str] = None

    model_config = ConfigDict(protected_namespaces=())

    @model_validator(mode="before")
    @classmethod
    def set_model_info(cls, values):
        dict_fields = [
            "metadata",
            "aliases",
            "config",
            "permissions",
            "model_max_budget",
            "model_aliases",
        ]

        if isinstance(values, BaseModel):
            values = values.model_dump()

        if (
            isinstance(values.get("members_with_roles"), dict)
            and not values["members_with_roles"]
        ):
            values["members_with_roles"] = []

        for field in dict_fields:
            value = values.get(field)
            if value is not None and isinstance(value, str):
                try:
                    values[field] = json.loads(value)
                except json.JSONDecodeError:
                    raise ValueError(f"Field {field} should be a valid dictionary")

        return values


class LiteLLM_TeamTableCachedObj(LiteLLM_TeamTable):
    last_refreshed_at: Optional[float] = None


class TeamRequest(LiteLLMPydanticObjectBase):
    teams: List[str]


class LiteLLM_BudgetTable(LiteLLMPydanticObjectBase):
    """Represents user-controllable params for a LiteLLM_BudgetTable record"""

    budget_id: Optional[str] = None
    soft_budget: Optional[float] = None
    max_budget: Optional[float] = None
    max_parallel_requests: Optional[int] = None
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None
    model_max_budget: Optional[dict] = None
    budget_duration: Optional[str] = None

    model_config = ConfigDict(protected_namespaces=())


class LiteLLM_BudgetTableFull(LiteLLM_BudgetTable):
    """Represents all params for a LiteLLM_BudgetTable record"""

    budget_reset_at: Optional[datetime] = None
    created_at: datetime


class LiteLLM_TeamMemberTable(LiteLLM_BudgetTable):
    """
    Used to track spend of a user_id within a team_id
    """

    spend: Optional[float] = None
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    budget_id: Optional[str] = None

    model_config = ConfigDict(protected_namespaces=())


class NewOrganizationRequest(LiteLLM_BudgetTable):
    organization_id: Optional[str] = None
    organization_alias: str
    models: List = []
    budget_id: Optional[str] = None
    metadata: Optional[dict] = None

    #########################################################
    # Object Permission - MCP, Vector Stores etc.
    #########################################################
    object_permission: Optional[LiteLLM_ObjectPermissionBase] = None


class OrganizationRequest(LiteLLMPydanticObjectBase):
    organizations: List[str]


class DeleteOrganizationRequest(LiteLLMPydanticObjectBase):
    organization_ids: List[str]  # required


class KeyManagementSystem(enum.Enum):
    GOOGLE_KMS = "google_kms"
    AZURE_KEY_VAULT = "azure_key_vault"
    AWS_SECRET_MANAGER = "aws_secret_manager"
    GOOGLE_SECRET_MANAGER = "google_secret_manager"
    HASHICORP_VAULT = "hashicorp_vault"
    LOCAL = "local"
    AWS_KMS = "aws_kms"


class KeyManagementSettings(LiteLLMPydanticObjectBase):
    hosted_keys: Optional[List] = None
    store_virtual_keys: Optional[bool] = False
    """
    If True, virtual keys created by litellm will be stored in the secret manager
    """
    prefix_for_stored_virtual_keys: str = "litellm/"
    """
    If set, this prefix will be used for stored virtual keys in the secret manager
    """

    access_mode: Literal["read_only", "write_only", "read_and_write"] = "read_only"
    """
    Access mode for the secret manager, when write_only will only use for writing secrets
    """

    primary_secret_name: Optional[str] = None
    """
    If set, will read secrets from this primary secret in the secret manager

    eg. on AWS you can store multiple secret values as K/V pairs in a single secret
    """


class TeamDefaultSettings(LiteLLMPydanticObjectBase):
    team_id: str

    model_config = ConfigDict(
        extra="allow"
    )  # allow params not defined here, these fall in litellm.completion(**kwargs)


class DynamoDBArgs(LiteLLMPydanticObjectBase):
    billing_mode: Literal["PROVISIONED_THROUGHPUT", "PAY_PER_REQUEST"]
    read_capacity_units: Optional[int] = None
    write_capacity_units: Optional[int] = None
    ssl_verify: Optional[bool] = None
    region_name: str
    user_table_name: str = "LiteLLM_UserTable"
    key_table_name: str = "LiteLLM_VerificationToken"
    config_table_name: str = "LiteLLM_Config"
    spend_table_name: str = "LiteLLM_SpendLogs"
    aws_role_name: Optional[str] = None
    aws_session_name: Optional[str] = None
    aws_web_identity_token: Optional[str] = None
    aws_provider_id: Optional[str] = None
    aws_policy_arns: Optional[List[str]] = None
    aws_policy: Optional[str] = None
    aws_duration_seconds: Optional[int] = None
    assume_role_aws_role_name: Optional[str] = None
    assume_role_aws_session_name: Optional[str] = None


class PassThroughGenericEndpoint(LiteLLMPydanticObjectBase):
    id: Optional[str] = Field(
        default=None,
        description="Optional unique identifier for the pass-through endpoint. If not provided, endpoints will be identified by path for backwards compatibility.",
    )
    path: str = Field(description="The route to be added to the LiteLLM Proxy Server.")
    target: str = Field(
        description="The URL to which requests for this path should be forwarded."
    )
    headers: dict = Field(
        default={},
        description="Key-value pairs of headers to be forwarded with the request. You can set any key value pair here and it will be forwarded to your target endpoint",
    )
    include_subpath: bool = Field(
        default=False,
        description="If True, requests to subpaths of the path will be forwarded to the target endpoint. For example, if the path is /bria and include_subpath is True, requests to /bria/v1/text-to-image/base/2.3 will be forwarded to the target endpoint.",
    )
    cost_per_request: float = Field(
        default=0.0,
        description="The USD cost per request to the target endpoint. This is used to calculate the cost of the request to the target endpoint.",
    )


class PassThroughEndpointResponse(LiteLLMPydanticObjectBase):
    endpoints: List[PassThroughGenericEndpoint]


class ConfigFieldUpdate(LiteLLMPydanticObjectBase):
    field_name: str
    field_value: Any
    config_type: Literal["general_settings"]


class ConfigFieldDelete(LiteLLMPydanticObjectBase):
    config_type: Literal["general_settings"]
    field_name: str


class CallbackDelete(LiteLLMPydanticObjectBase):
    callback_name: str


class FieldDetail(BaseModel):
    field_name: str
    field_type: str
    field_description: str
    field_default_value: Any = None
    stored_in_db: Optional[bool]


class ConfigList(LiteLLMPydanticObjectBase):
    field_name: str
    field_type: str
    field_description: str
    field_value: Any
    stored_in_db: Optional[bool]
    field_default_value: Any
    premium_field: bool = False
    nested_fields: Optional[List[FieldDetail]] = (
        None  # For nested dictionary or Pydantic fields
    )


class ConfigGeneralSettings(LiteLLMPydanticObjectBase):
    """
    Documents all the fields supported by `general_settings` in config.yaml
    """

    completion_model: Optional[str] = Field(
        None, description="proxy level default model for all chat completion calls"
    )
    key_management_system: Optional[KeyManagementSystem] = Field(
        None, description="key manager to load keys from / decrypt keys with"
    )
    use_google_kms: Optional[bool] = Field(
        None, description="decrypt keys with google kms"
    )
    use_azure_key_vault: Optional[bool] = Field(
        None, description="load keys from azure key vault"
    )
    master_key: Optional[str] = Field(
        None, description="require a key for all calls to proxy"
    )
    database_url: Optional[str] = Field(
        None,
        description="connect to a postgres db - needed for generating temporary keys + tracking spend / key",
    )
    database_connection_pool_limit: Optional[int] = Field(
        100,
        description="default connection pool for prisma client connecting to postgres db",
    )
    database_connection_timeout: Optional[float] = Field(
        60, description="default timeout for a connection to the database"
    )
    database_type: Optional[Literal["dynamo_db"]] = Field(
        None, description="to use dynamodb instead of postgres db"
    )
    database_args: Optional[DynamoDBArgs] = Field(
        None,
        description="custom args for instantiating dynamodb client - e.g. billing provision",
    )
    otel: Optional[bool] = Field(
        None,
        description="[BETA] OpenTelemetry support - this might change, use with caution.",
    )
    custom_auth: Optional[str] = Field(
        None,
        description="override user_api_key_auth with your own auth script - https://docs.litellm.ai/docs/proxy/virtual_keys#custom-auth",
    )
    max_parallel_requests: Optional[int] = Field(
        None,
        description="maximum parallel requests for each api key",
    )
    global_max_parallel_requests: Optional[int] = Field(
        None, description="global max parallel requests to allow for a proxy instance."
    )
    max_request_size_mb: Optional[int] = Field(
        None,
        description="max request size in MB, if a request is larger than this size it will be rejected",
    )
    max_response_size_mb: Optional[int] = Field(
        None,
        description="max response size in MB, if a response is larger than this size it will be rejected",
    )
    infer_model_from_keys: Optional[bool] = Field(
        None,
        description="for `/models` endpoint, infers available model based on environment keys (e.g. OPENAI_API_KEY)",
    )
    background_health_checks: Optional[bool] = Field(
        None, description="run health checks in background"
    )
    health_check_interval: int = Field(
        300, description="background health check interval in seconds"
    )
    alerting: Optional[List] = Field(
        None,
        description="List of alerting integrations. Today, just slack - `alerting: ['slack']`",
    )
    alert_types: Optional[List[AlertType]] = Field(
        None,
        description="List of alerting types. By default it is all alerts",
    )
    alert_to_webhook_url: Optional[Dict] = Field(
        None,
        description="Mapping of alert type to webhook url. e.g. `alert_to_webhook_url: {'budget_alerts': 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'}`",
    )
    alerting_args: Optional[Dict] = Field(
        None, description="Controllable params for slack alerting - e.g. ttl in cache."
    )
    alerting_threshold: Optional[int] = Field(
        None,
        description="sends alerts if requests hang for 5min+",
    )
    ui_access_mode: Optional[Literal["admin_only", "all"]] = Field(
        "all", description="Control access to the Proxy UI"
    )
    allowed_routes: Optional[List] = Field(
        None, description="Proxy API Endpoints you want users to be able to access"
    )
    enable_public_model_hub: bool = Field(
        default=False,
        description="Public model hub for users to see what models they have access to, supported openai params, etc.",
    )
    pass_through_endpoints: Optional[List[PassThroughGenericEndpoint]] = Field(
        default=None,
        description="Set-up pass-through endpoints for provider-specific endpoints. Docs - https://docs.litellm.ai/docs/proxy/pass_through",
    )


class ConfigYAML(LiteLLMPydanticObjectBase):
    """
    Documents all the fields supported by the config.yaml
    """

    environment_variables: Optional[dict] = Field(
        None,
        description="Object to pass in additional environment variables via POST request",
    )
    model_list: Optional[List[ModelParams]] = Field(
        None,
        description="List of supported models on the server, with model-specific configs",
    )
    litellm_settings: Optional[dict] = Field(
        None,
        description="litellm Module settings. See __init__.py for all, example litellm.drop_params=True, litellm.set_verbose=True, litellm.api_base, litellm.cache",
    )
    general_settings: Optional[ConfigGeneralSettings] = None
    router_settings: Optional[UpdateRouterConfig] = Field(
        None,
        description="litellm router object settings. See router.py __init__ for all, example router.num_retries=5, router.timeout=5, router.max_retries=5, router.retry_after=5",
    )

    model_config = ConfigDict(protected_namespaces=())


class LiteLLM_VerificationToken(LiteLLMPydanticObjectBase):
    token: Optional[str] = None
    key_name: Optional[str] = None
    key_alias: Optional[str] = None
    spend: float = 0.0
    max_budget: Optional[float] = None
    expires: Optional[Union[str, datetime]] = None
    models: List = []
    aliases: Dict = {}
    config: Dict = {}
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    max_parallel_requests: Optional[int] = None
    metadata: Dict = {}
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None
    budget_duration: Optional[str] = None
    budget_reset_at: Optional[datetime] = None
    allowed_cache_controls: Optional[list] = []
    allowed_routes: Optional[list] = []
    permissions: Dict = {}
    model_spend: Dict = {}
    model_max_budget: Dict = {}
    soft_budget_cooldown: bool = False
    blocked: Optional[bool] = None
    litellm_budget_table: Optional[dict] = None
    org_id: Optional[str] = None  # org id for a given key
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    object_permission_id: Optional[str] = None
    object_permission: Optional[LiteLLM_ObjectPermissionTable] = None

    model_config = ConfigDict(protected_namespaces=())


class LiteLLM_VerificationTokenView(LiteLLM_VerificationToken):
    """
    Combined view of litellm verification token + litellm team table (select values)
    """

    team_spend: Optional[float] = None
    team_alias: Optional[str] = None
    team_tpm_limit: Optional[int] = None
    team_rpm_limit: Optional[int] = None
    team_max_budget: Optional[float] = None
    team_models: List = []
    team_blocked: bool = False
    soft_budget: Optional[float] = None
    team_model_aliases: Optional[Dict] = None
    team_member_spend: Optional[float] = None
    team_member: Optional[Member] = None
    team_metadata: Optional[Dict] = None

    # End User Params
    end_user_id: Optional[str] = None
    end_user_tpm_limit: Optional[int] = None
    end_user_rpm_limit: Optional[int] = None
    end_user_max_budget: Optional[float] = None

    # Time stamps
    last_refreshed_at: Optional[float] = None  # last time joint view was pulled from db

    def __init__(self, **kwargs):
        # Handle litellm_budget_table_* keys
        for key, value in list(kwargs.items()):
            if key.startswith("litellm_budget_table_") and value is not None:
                # Extract the corresponding attribute name
                attr_name = key.replace("litellm_budget_table_", "")
                # Check if the value is None and set the corresponding attribute
                if getattr(self, attr_name, None) is None:
                    kwargs[attr_name] = value
            if key == "end_user_id" and value is not None and isinstance(value, int):
                kwargs[key] = str(value)
        # Initialize the superclass
        super().__init__(**kwargs)


class UserAPIKeyAuth(
    LiteLLM_VerificationTokenView
):  # the expected response object for user api key auth
    """
    Return the row in the db
    """

    api_key: Optional[str] = None
    user_role: Optional[LitellmUserRoles] = None
    allowed_model_region: Optional[AllowedModelRegion] = None
    parent_otel_span: Optional[Span] = None
    rpm_limit_per_model: Optional[Dict[str, int]] = None
    tpm_limit_per_model: Optional[Dict[str, int]] = None
    user_tpm_limit: Optional[int] = None
    user_rpm_limit: Optional[int] = None
    user_email: Optional[str] = None
    request_route: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="before")
    @classmethod
    def check_api_key(cls, values):
        if values.get("api_key") is not None:
            values.update({"token": hash_token(values.get("api_key"))})
            if isinstance(values.get("api_key"), str) and values.get(
                "api_key"
            ).startswith("sk-"):
                values.update({"api_key": hash_token(values.get("api_key"))})
        return values


class UserInfoResponse(LiteLLMPydanticObjectBase):
    user_id: Optional[str]
    user_info: Optional[Union[dict, BaseModel]]
    keys: List
    teams: List


class LiteLLM_Config(LiteLLMPydanticObjectBase):
    param_name: str
    param_value: Dict


class LiteLLM_OrganizationMembershipTable(LiteLLMPydanticObjectBase):
    """
    This is the table that track what organizations a user belongs to and users spend within the organization
    """

    user_id: str
    organization_id: str
    user_role: Optional[str] = None
    spend: float = 0.0
    budget_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user: Optional[Any] = (
        None  # You might want to replace 'Any' with a more specific type if available
    )
    litellm_budget_table: Optional[LiteLLM_BudgetTable] = None

    model_config = ConfigDict(protected_namespaces=())


class LiteLLM_OrganizationTableUpdate(LiteLLMPydanticObjectBase):
    """Represents user-controllable params for a LiteLLM_OrganizationTable record"""

    organization_id: Optional[str] = None
    organization_alias: Optional[str] = None
    budget_id: Optional[str] = None
    spend: Optional[float] = None
    metadata: Optional[dict] = None
    models: Optional[List[str]] = None
    updated_by: Optional[str] = None
    object_permission: Optional[LiteLLM_ObjectPermissionTable] = None


class LiteLLM_UserTable(LiteLLMPydanticObjectBase):
    user_id: str
    max_budget: Optional[float] = None
    spend: float = 0.0
    model_max_budget: Optional[Dict] = {}
    model_spend: Optional[Dict] = {}
    user_email: Optional[str] = None
    user_alias: Optional[str] = None
    models: list = []
    tpm_limit: Optional[int] = None
    rpm_limit: Optional[int] = None
    user_role: Optional[str] = None
    organization_memberships: Optional[List[LiteLLM_OrganizationMembershipTable]] = None
    teams: List[str] = []
    sso_user_id: Optional[str] = None
    budget_duration: Optional[str] = None
    budget_reset_at: Optional[datetime] = None
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    object_permission: Optional[LiteLLM_ObjectPermissionTable] = None

    @model_validator(mode="before")
    @classmethod
    def set_model_info(cls, values):
        if values.get("spend") is None:
            values.update({"spend": 0.0})
        if values.get("models") is None:
            values.update({"models": []})
        if values.get("teams") is None:
            values.update({"teams": []})
        return values

    model_config = ConfigDict(protected_namespaces=())


class LiteLLM_OrganizationTable(LiteLLMPydanticObjectBase):
    """Represents user-controllable params for a LiteLLM_OrganizationTable record"""

    organization_id: Optional[str] = None
    organization_alias: Optional[str] = None
    budget_id: str
    spend: float = 0.0
    metadata: Optional[dict] = None
    models: List[str]
    created_by: str
    updated_by: str
    users: Optional[List[LiteLLM_UserTable]] = None
    litellm_budget_table: Optional[LiteLLM_BudgetTable] = None

    #########################################################
    # Object Permission - MCP, Vector Stores etc.
    #########################################################
    object_permission: Optional[LiteLLM_ObjectPermissionTable] = None
    object_permission_id: Optional[str] = None


class LiteLLM_OrganizationTableWithMembers(LiteLLM_OrganizationTable):
    """Returned by the /organization/info endpoint and /organization/list endpoint"""

    members: List[LiteLLM_OrganizationMembershipTable] = []
    teams: List[LiteLLM_TeamTable] = []
    litellm_budget_table: Optional[LiteLLM_BudgetTable] = None
    created_at: datetime
    updated_at: datetime


class NewOrganizationResponse(LiteLLM_OrganizationTable):
    organization_id: str  # type: ignore
    created_at: datetime
    updated_at: datetime


class LiteLLM_UserTableFiltered(BaseModel):  # done to avoid exposing sensitive data
    user_id: str
    user_email: Optional[str] = None


class LiteLLM_UserTableWithKeyCount(LiteLLM_UserTable):
    key_count: int = 0


class LiteLLM_EndUserTable(LiteLLMPydanticObjectBase):
    user_id: str
    blocked: bool
    alias: Optional[str] = None
    spend: float = 0.0
    allowed_model_region: Optional[AllowedModelRegion] = None
    default_model: Optional[str] = None
    litellm_budget_table: Optional[LiteLLM_BudgetTable] = None

    @model_validator(mode="before")
    @classmethod
    def set_model_info(cls, values):
        if values.get("spend") is None:
            values.update({"spend": 0.0})
        return values

    model_config = ConfigDict(protected_namespaces=())


class LiteLLM_SpendLogs(LiteLLMPydanticObjectBase):
    request_id: str
    api_key: str
    model: Optional[str] = ""
    api_base: Optional[str] = ""
    call_type: str
    spend: Optional[float] = 0.0
    total_tokens: Optional[int] = 0
    prompt_tokens: Optional[int] = 0
    completion_tokens: Optional[int] = 0
    startTime: Union[str, datetime, None]
    endTime: Union[str, datetime, None]
    user: Optional[str] = ""
    metadata: Optional[Json] = {}
    cache_hit: Optional[str] = "False"
    cache_key: Optional[str] = None
    request_tags: Optional[Json] = None
    requester_ip_address: Optional[str] = None
    messages: Optional[Union[str, list, dict]]
    response: Optional[Union[str, list, dict]]


class LiteLLM_ErrorLogs(LiteLLMPydanticObjectBase):
    request_id: Optional[str] = str(uuid.uuid4())
    api_base: Optional[str] = ""
    model_group: Optional[str] = ""
    litellm_model_name: Optional[str] = ""
    model_id: Optional[str] = ""
    request_kwargs: Optional[dict] = {}
    exception_type: Optional[str] = ""
    status_code: Optional[str] = ""
    exception_string: Optional[str] = ""
    startTime: Union[str, datetime, None]
    endTime: Union[str, datetime, None]


AUDIT_ACTIONS = Literal["created", "updated", "deleted", "blocked", "rotated"]


class LiteLLM_AuditLogs(LiteLLMPydanticObjectBase):
    id: str
    updated_at: datetime
    changed_by: Optional[Any] = None
    changed_by_api_key: Optional[str] = None
    action: AUDIT_ACTIONS
    table_name: LitellmTableNames
    object_id: str
    before_value: Optional[Json] = None
    updated_values: Optional[Json] = None

    @model_validator(mode="before")
    @classmethod
    def cast_changed_by_to_str(cls, values):
        if values.get("changed_by") is not None:
            values["changed_by"] = str(values["changed_by"])
        return values

    @model_validator(mode="after")
    def mask_api_keys(self):
        from litellm.litellm_core_utils.sensitive_data_masker import SensitiveDataMasker

        masker = SensitiveDataMasker(sensitive_patterns={"key"})

        if self.before_value is not None:
            json_before_value: Optional[dict] = None
            if isinstance(self.before_value, str):
                json_before_value = json.loads(self.before_value)
            elif isinstance(self.before_value, dict):
                json_before_value = self.before_value

            if json_before_value is not None:
                json_before_value = masker.mask_dict(json_before_value)
                self.before_value = json.dumps(json_before_value, default=str)

        if self.updated_values is not None:
            json_updated_values: Optional[dict] = None
            if isinstance(self.updated_values, str):
                json_updated_values = json.loads(self.updated_values)
            elif isinstance(self.updated_values, dict):
                json_updated_values = self.updated_values

            if json_updated_values is not None:
                json_updated_values = masker.mask_dict(json_updated_values)
                self.updated_values = json.dumps(json_updated_values, default=str)

        return self


class LiteLLM_SpendLogs_ResponseObject(LiteLLMPydanticObjectBase):
    response: Optional[List[Union[LiteLLM_SpendLogs, Any]]] = None


class TokenCountRequest(LiteLLMPydanticObjectBase):
    model: str
    prompt: Optional[str] = None
    messages: Optional[List[dict]] = None


class TokenCountResponse(LiteLLMPydanticObjectBase):
    total_tokens: int
    request_model: str
    model_used: str
    tokenizer_type: str


class CallInfo(LiteLLMPydanticObjectBase):
    """Used for slack budget alerting"""

    spend: float
    max_budget: Optional[float] = None
    soft_budget: Optional[float] = None
    token: Optional[str] = Field(default=None, description="Hashed value of that key")
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    team_alias: Optional[str] = None
    user_email: Optional[str] = None
    key_alias: Optional[str] = None
    projected_exceeded_date: Optional[str] = None
    projected_spend: Optional[float] = None
    event_group: Litellm_EntityType


class WebhookEvent(CallInfo):
    event: Literal[
        "budget_crossed",
        "soft_budget_crossed",
        "threshold_crossed",
        "projected_limit_exceeded",
        "key_created",
        "internal_user_created",
        "spend_tracked",
    ]
    event_message: str  # human-readable description of event
    event_group: Litellm_EntityType


class SpecialModelNames(enum.Enum):
    all_team_models = "all-team-models"
    all_proxy_models = "all-proxy-models"
    no_default_models = "no-default-models"


class SpecialProxyStrings(enum.Enum):
    default_user_id = "default_user_id"  # global proxy admin


class InvitationNew(LiteLLMPydanticObjectBase):
    user_id: str


class InvitationUpdate(LiteLLMPydanticObjectBase):
    invitation_id: str
    is_accepted: bool


class InvitationDelete(LiteLLMPydanticObjectBase):
    invitation_id: str


class InvitationModel(LiteLLMPydanticObjectBase):
    id: str
    user_id: str
    is_accepted: bool
    accepted_at: Optional[datetime]
    expires_at: datetime
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


class InvitationClaim(LiteLLMPydanticObjectBase):
    invitation_link: str
    user_id: str
    password: str


class ConfigFieldInfo(LiteLLMPydanticObjectBase):
    field_name: str
    field_value: Any


class CallbackOnUI(LiteLLMPydanticObjectBase):
    litellm_callback_name: str
    litellm_callback_params: Optional[list]
    ui_callback_name: str


class AllCallbacks(LiteLLMPydanticObjectBase):
    langfuse: CallbackOnUI = CallbackOnUI(
        litellm_callback_name="langfuse",
        ui_callback_name="Langfuse",
        litellm_callback_params=[
            "LANGFUSE_PUBLIC_KEY",
            "LANGFUSE_SECRET_KEY",
        ],
    )

    otel: CallbackOnUI = CallbackOnUI(
        litellm_callback_name="otel",
        ui_callback_name="OpenTelemetry",
        litellm_callback_params=[
            "OTEL_EXPORTER",
            "OTEL_ENDPOINT",
            "OTEL_HEADERS",
        ],
    )

    s3: CallbackOnUI = CallbackOnUI(
        litellm_callback_name="s3",
        ui_callback_name="s3 Bucket (AWS)",
        litellm_callback_params=[
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_REGION_NAME",
        ],
    )

    openmeter: CallbackOnUI = CallbackOnUI(
        litellm_callback_name="openmeter",
        ui_callback_name="OpenMeter",
        litellm_callback_params=[
            "OPENMETER_API_ENDPOINT",
            "OPENMETER_API_KEY",
        ],
    )

    custom_callback_api: CallbackOnUI = CallbackOnUI(
        litellm_callback_name="custom_callback_api",
        litellm_callback_params=["GENERIC_LOGGER_ENDPOINT"],
        ui_callback_name="Custom Callback API",
    )

    datadog: CallbackOnUI = CallbackOnUI(
        litellm_callback_name="datadog",
        litellm_callback_params=["DD_API_KEY", "DD_SITE"],
        ui_callback_name="Datadog",
    )

    braintrust: CallbackOnUI = CallbackOnUI(
        litellm_callback_name="braintrust",
        litellm_callback_params=["BRAINTRUST_API_KEY"],
        ui_callback_name="Braintrust",
    )

    langsmith: CallbackOnUI = CallbackOnUI(
        litellm_callback_name="langsmith",
        litellm_callback_params=[
            "LANGSMITH_API_KEY",
            "LANGSMITH_PROJECT",
            "LANGSMITH_DEFAULT_RUN_NAME",
        ],
        ui_callback_name="Langsmith",
    )

    lago: CallbackOnUI = CallbackOnUI(
        litellm_callback_name="lago",
        litellm_callback_params=[
            "LAGO_API_BASE",
            "LAGO_API_KEY",
            "LAGO_API_EVENT_CODE",
            "LAGO_API_CHARGE_BY",
        ],
        ui_callback_name="Lago Billing",
    )


class SpendLogsMetadata(TypedDict):
    """
    Specific metadata k,v pairs logged to spendlogs for easier cost tracking
    """

    additional_usage_values: Optional[
        dict
    ]  # covers provider-specific usage information - e.g. prompt caching
    user_api_key: Optional[str]
    user_api_key_alias: Optional[str]
    user_api_key_team_id: Optional[str]
    user_api_key_org_id: Optional[str]
    user_api_key_user_id: Optional[str]
    user_api_key_team_alias: Optional[str]
    spend_logs_metadata: Optional[
        dict
    ]  # special param to log k,v pairs to spendlogs for a call
    requester_ip_address: Optional[str]
    applied_guardrails: Optional[List[str]]
    mcp_tool_call_metadata: Optional[StandardLoggingMCPToolCall]
    vector_store_request_metadata: Optional[List[StandardLoggingVectorStoreRequest]]
    guardrail_information: Optional[StandardLoggingGuardrailInformation]
    status: StandardLoggingPayloadStatus
    proxy_server_request: Optional[str]
    batch_models: Optional[List[str]]
    error_information: Optional[StandardLoggingPayloadErrorInformation]
    usage_object: Optional[dict]
    model_map_information: Optional[StandardLoggingModelInformation]


class SpendLogsPayload(TypedDict):
    request_id: str
    call_type: str
    api_key: str
    spend: float
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    startTime: Union[datetime, str]
    endTime: Union[datetime, str]
    completionStartTime: Optional[Union[datetime, str]]
    model: str
    model_id: Optional[str]
    model_group: Optional[str]
    api_base: str
    user: str
    metadata: str  # json str
    cache_hit: str
    cache_key: str
    request_tags: str  # json str
    team_id: Optional[str]
    end_user: Optional[str]
    requester_ip_address: Optional[str]
    custom_llm_provider: Optional[str]
    messages: Optional[Union[str, list, dict]]
    response: Optional[Union[str, list, dict]]
    proxy_server_request: Optional[str]
    session_id: Optional[str]
    status: Literal["success", "failure"]


class SpanAttributes(str, enum.Enum):
    # Note: We've taken this from opentelemetry-semantic-conventions-ai
    # I chose to not add a new dependency to litellm for this

    # Semantic Conventions for LLM requests, this needs to be removed after
    # OpenTelemetry Semantic Conventions support Gen AI.
    # Issue at https://github.com/open-telemetry/opentelemetry-python/issues/3868
    # Refer to https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/llm-spans.md

    LLM_SYSTEM = "gen_ai.system"
    LLM_REQUEST_MODEL = "gen_ai.request.model"
    LLM_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    LLM_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    LLM_REQUEST_TOP_P = "gen_ai.request.top_p"
    LLM_PROMPTS = "gen_ai.prompt"
    LLM_COMPLETIONS = "gen_ai.completion"
    LLM_RESPONSE_MODEL = "gen_ai.response.model"
    LLM_USAGE_COMPLETION_TOKENS = "gen_ai.usage.completion_tokens"
    LLM_USAGE_PROMPT_TOKENS = "gen_ai.usage.prompt_tokens"
    LLM_TOKEN_TYPE = "gen_ai.token.type"
    # To be added
    # LLM_RESPONSE_FINISH_REASON = "gen_ai.response.finish_reasons"
    # LLM_RESPONSE_ID = "gen_ai.response.id"

    # LLM
    LLM_REQUEST_TYPE = "llm.request.type"
    LLM_USAGE_TOTAL_TOKENS = "llm.usage.total_tokens"
    LLM_USAGE_TOKEN_TYPE = "llm.usage.token_type"
    LLM_USER = "llm.user"
    LLM_HEADERS = "llm.headers"
    LLM_TOP_K = "llm.top_k"
    LLM_IS_STREAMING = "llm.is_streaming"
    LLM_FREQUENCY_PENALTY = "llm.frequency_penalty"
    LLM_PRESENCE_PENALTY = "llm.presence_penalty"
    LLM_CHAT_STOP_SEQUENCES = "llm.chat.stop_sequences"
    LLM_REQUEST_FUNCTIONS = "llm.request.functions"
    LLM_REQUEST_REPETITION_PENALTY = "llm.request.repetition_penalty"
    LLM_RESPONSE_FINISH_REASON = "llm.response.finish_reason"
    LLM_RESPONSE_STOP_REASON = "llm.response.stop_reason"
    LLM_CONTENT_COMPLETION_CHUNK = "llm.content.completion.chunk"

    # OpenAI
    LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT = "gen_ai.openai.system_fingerprint"
    LLM_OPENAI_API_BASE = "gen_ai.openai.api_base"
    LLM_OPENAI_API_VERSION = "gen_ai.openai.api_version"
    LLM_OPENAI_API_TYPE = "gen_ai.openai.api_type"


class ManagementEndpointLoggingPayload(LiteLLMPydanticObjectBase):
    route: str
    request_data: dict
    response: Optional[dict] = None
    exception: Optional[Any] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ProxyException(Exception):
    # NOTE: DO NOT MODIFY THIS
    # This is used to map exactly to OPENAI Exceptions
    def __init__(
        self,
        message: str,
        type: str,
        param: Optional[str],
        code: Optional[Union[int, str]] = None,  # maps to status code
        headers: Optional[Dict[str, str]] = None,
        openai_code: Optional[str] = None,  # maps to 'code'  in openai
    ):
        self.message = str(message)
        self.type = type
        self.param = param
        self.openai_code = openai_code or code
        # If we look on official python OpenAI lib, the code should be a string:
        # https://github.com/openai/openai-python/blob/195c05a64d39c87b2dfdf1eca2d339597f1fce03/src/openai/types/shared/error_object.py#L11
        # Related LiteLLM issue: https://github.com/BerriAI/litellm/discussions/4834
        self.code = str(code)
        if headers is not None:
            for k, v in headers.items():
                if not isinstance(v, str):
                    headers[k] = str(v)
        self.headers = headers or {}

        # rules for proxyExceptions
        # Litellm router.py returns "No healthy deployment available" when there are no deployments available
        # Should map to 429 errors https://github.com/BerriAI/litellm/issues/2487
        if (
            "No healthy deployment available" in self.message
            or "No deployments available" in self.message
        ):
            self.code = "429"
        elif RouterErrors.no_deployments_with_tag_routing.value in self.message:
            self.code = "401"

    def to_dict(self) -> dict:
        """Converts the ProxyException instance to a dictionary."""
        return {
            "message": self.message,
            "type": self.type,
            "param": self.param,
            "code": self.code,
        }


class CommonProxyErrors(str, enum.Enum):
    db_not_connected_error = (
        "DB not connected. See https://docs.litellm.ai/docs/proxy/virtual_keys"
    )
    no_llm_router = "No models configured on proxy"
    not_allowed_access = "Admin-only endpoint. Not allowed to access this."
    not_premium_user = "You must be a LiteLLM Enterprise user to use this feature. If you have a license please set `LITELLM_LICENSE` in your env. Get a 7 day trial key here: https://www.litellm.ai/enterprise#trial. \nPricing: https://www.litellm.ai/#pricing"
    max_parallel_request_limit_reached = (
        "Crossed TPM / RPM / Max Parallel Request Limit"
    )
    missing_enterprise_package = "Missing litellm-enterprise package. Please install it to use this feature. Run `pip install litellm-enterprise`"
    missing_enterprise_package_docker = (
        "This uses the enterprise folder - only available on the Docker image."
    )


class SpendCalculateRequest(LiteLLMPydanticObjectBase):
    model: Optional[str] = None
    messages: Optional[List] = None
    completion_response: Optional[dict] = None


class ProxyErrorTypes(str, enum.Enum):
    budget_exceeded = "budget_exceeded"
    """
    Object was over budget
    """
    no_db_connection = "no_db_connection"
    """
    No database connection
    """

    token_not_found_in_db = "token_not_found_in_db"
    """
    Requested token was not found in the database
    """

    key_model_access_denied = "key_model_access_denied"
    """
    Key does not have access to the model
    """

    team_model_access_denied = "team_model_access_denied"
    """
    Team does not have access to the model
    """

    user_model_access_denied = "user_model_access_denied"
    """
    User does not have access to the model
    """

    org_model_access_denied = "org_model_access_denied"
    """
    Organization does not have access to the model
    """

    expired_key = "expired_key"
    """
    Key has expired
    """

    auth_error = "auth_error"
    """
    General authentication error
    """

    internal_server_error = "internal_server_error"
    """
    Internal server error
    """

    bad_request_error = "bad_request_error"
    """
    Bad request error
    """

    not_found_error = "not_found_error"
    """
    Not found error
    """

    validation_error = "validation_error"
    """
    Validation error
    """

    cache_ping_error = "cache_ping_error"
    """
    Cache ping error
    """

    team_member_permission_error = "team_member_permission_error"
    """
    Team member permission error
    """

    key_vector_store_access_denied = "key_vector_store_access_denied"
    """
    Key does not have access to the vector store
    """

    team_vector_store_access_denied = "team_vector_store_access_denied"
    """
    Team does not have access to the vector store
    """

    org_vector_store_access_denied = "org_vector_store_access_denied"
    """
    Organization does not have access to the vector store
    """

    team_member_already_in_team = "team_member_already_in_team"
    """
    Team member is already in team
    """

    @classmethod
    def get_model_access_error_type_for_object(
        cls, object_type: Literal["key", "user", "team", "org"]
    ) -> "ProxyErrorTypes":
        """
        Get the model access error type for object_type
        """
        if object_type == "key":
            return cls.key_model_access_denied
        elif object_type == "team":
            return cls.team_model_access_denied
        elif object_type == "user":
            return cls.user_model_access_denied
        elif object_type == "org":
            return cls.org_model_access_denied

    @classmethod
    def get_vector_store_access_error_type_for_object(
        cls, object_type: Literal["key", "team", "org"]
    ) -> "ProxyErrorTypes":
        """
        Get the vector store access error type for object_type
        """
        if object_type == "key":
            return cls.key_vector_store_access_denied
        elif object_type == "team":
            return cls.team_vector_store_access_denied
        elif object_type == "org":
            return cls.org_vector_store_access_denied


DB_CONNECTION_ERROR_TYPES = (
    httpx.ConnectError,
    httpx.ReadError,
    httpx.ReadTimeout,
)


class SSOUserDefinedValues(TypedDict):
    models: List[str]
    user_id: str
    user_email: Optional[str]
    user_role: Optional[str]
    max_budget: Optional[float]
    budget_duration: Optional[str]


class VirtualKeyEvent(LiteLLMPydanticObjectBase):
    created_by_user_id: str
    created_by_user_role: str
    created_by_key_alias: Optional[str]
    request_kwargs: dict


class CreatePassThroughEndpoint(LiteLLMPydanticObjectBase):
    path: str
    target: str
    headers: dict


class LiteLLM_TeamMembership(LiteLLMPydanticObjectBase):
    user_id: str
    team_id: str
    budget_id: Optional[str] = None
    spend: Optional[float] = 0.0
    litellm_budget_table: Optional[LiteLLM_BudgetTable]


#### Organization / Team Member Requests ####


class MemberAddRequest(LiteLLMPydanticObjectBase):
    member: Union[List[Member], Member]

    def __init__(self, **data):
        member_data = data.get("member")
        if isinstance(member_data, list):
            # If member is a list of dictionaries, convert each dictionary to a Member object
            members = [Member(**item) for item in member_data]
            # Replace member_data with the list of Member objects
            data["member"] = members
        elif isinstance(member_data, dict):
            # If member is a dictionary, convert it to a single Member object
            member = Member(**member_data)
            # Replace member_data with the single Member object
            data["member"] = member
        # Call the superclass __init__ method to initialize the object
        super().__init__(**data)


class OrgMemberAddRequest(LiteLLMPydanticObjectBase):
    member: Union[List[OrgMember], OrgMember]

    def __init__(self, **data):
        member_data = data.get("member")
        if isinstance(member_data, list):
            # If member is a list of dictionaries, convert each dictionary to a Member object
            if all(isinstance(item, dict) for item in member_data):
                members = [OrgMember(**item) for item in member_data]
            else:
                members = [item for item in member_data]
            # Replace member_data with the list of Member objects
            data["member"] = members
        elif isinstance(member_data, dict):
            # If member is a dictionary, convert it to a single Member object
            member = OrgMember(**member_data)
            # Replace member_data with the single Member object
            data["member"] = member
        # Call the superclass __init__ method to initialize the object
        super().__init__(**data)


class TeamAddMemberResponse(LiteLLM_TeamTable):
    updated_users: List[LiteLLM_UserTable]
    updated_team_memberships: List[LiteLLM_TeamMembership]


class OrganizationAddMemberResponse(LiteLLMPydanticObjectBase):
    organization_id: str
    updated_users: List[LiteLLM_UserTable]
    updated_organization_memberships: List[LiteLLM_OrganizationMembershipTable]


class MemberDeleteRequest(LiteLLMPydanticObjectBase):
    user_id: Optional[str] = None
    user_email: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def check_user_info(cls, values):
        if values.get("user_id") is None and values.get("user_email") is None:
            raise ValueError("Either user id or user email must be provided")
        return values


class MemberUpdateResponse(LiteLLMPydanticObjectBase):
    user_id: str
    user_email: Optional[str] = None


# Team Member Requests
class TeamMemberAddRequest(MemberAddRequest):
    team_id: str
    max_budget_in_team: Optional[float] = None  # Users max budget within the team


class TeamMemberDeleteRequest(MemberDeleteRequest):
    team_id: str


class TeamMemberUpdateRequest(TeamMemberDeleteRequest):
    max_budget_in_team: Optional[float] = None
    role: Optional[Literal["admin", "user"]] = None


class TeamMemberUpdateResponse(MemberUpdateResponse):
    team_id: str
    max_budget_in_team: Optional[float] = None


class TeamModelAddRequest(BaseModel):
    """Request to add models to a team"""

    team_id: str
    models: List[str]


class TeamModelDeleteRequest(BaseModel):
    """Request to delete models from a team"""

    team_id: str
    models: List[str]


# Organization Member Requests
class OrganizationMemberAddRequest(OrgMemberAddRequest):
    organization_id: str
    max_budget_in_organization: Optional[float] = (
        None  # Users max budget within the organization
    )


class OrganizationMemberDeleteRequest(MemberDeleteRequest):
    organization_id: str


ROLES_WITHIN_ORG = [
    LitellmUserRoles.ORG_ADMIN,
    LitellmUserRoles.INTERNAL_USER,
    LitellmUserRoles.INTERNAL_USER_VIEW_ONLY,
]


class OrganizationMemberUpdateRequest(OrganizationMemberDeleteRequest):
    max_budget_in_organization: Optional[float] = None
    role: Optional[LitellmUserRoles] = None

    @field_validator("role")
    def validate_role(
        cls, value: Optional[LitellmUserRoles]
    ) -> Optional[LitellmUserRoles]:
        if value is not None and value not in ROLES_WITHIN_ORG:
            raise ValueError(
                f"Invalid role. Must be one of: {[role.value for role in ROLES_WITHIN_ORG]}"
            )
        return value


class OrganizationMemberUpdateResponse(MemberUpdateResponse):
    organization_id: str
    max_budget_in_organization: float


##########################################


class TeamInfoResponseObjectTeamTable(LiteLLM_TeamTable):
    team_member_budget_table: Optional[LiteLLM_BudgetTable] = None


class TeamInfoResponseObject(TypedDict):
    team_id: str
    team_info: TeamInfoResponseObjectTeamTable
    keys: List
    team_memberships: List[LiteLLM_TeamMembership]


class TeamListResponseObject(LiteLLM_TeamTable):
    team_memberships: List[LiteLLM_TeamMembership]
    keys: List  # list of keys that belong to the team


class KeyListResponseObject(TypedDict, total=False):
    keys: List[Union[str, UserAPIKeyAuth]]
    total_count: Optional[int]
    current_page: Optional[int]
    total_pages: Optional[int]


class CurrentItemRateLimit(TypedDict):
    current_requests: int
    current_tpm: int
    current_rpm: int


class LoggingCallbackStatus(TypedDict, total=False):
    callbacks: List[str]
    status: Literal["healthy", "unhealthy"]
    details: Optional[str]


class KeyHealthResponse(TypedDict, total=False):
    key: Literal["healthy", "unhealthy"]
    logging_callbacks: Optional[LoggingCallbackStatus]


class SpecialHeaders(enum.Enum):
    """Used by user_api_key_auth.py to get litellm key"""

    openai_authorization = "Authorization"
    azure_authorization = "API-Key"
    anthropic_authorization = "x-api-key"
    google_ai_studio_authorization = "x-goog-api-key"
    azure_apim_authorization = "Ocp-Apim-Subscription-Key"
    custom_litellm_api_key = "x-litellm-api-key"
    mcp_auth = "x-mcp-auth"


class LitellmDataForBackendLLMCall(TypedDict, total=False):
    headers: dict
    organization: str
    timeout: Optional[float]
    user: Optional[str]


class JWTKeyItem(TypedDict, total=False):
    kid: str


JWKKeyValue = Union[List[JWTKeyItem], JWTKeyItem]


class JWKUrlResponse(TypedDict, total=False):
    keys: JWKKeyValue


class UserManagementEndpointParamDocStringEnums(str, enum.Enum):
    user_id_doc_str = (
        "Optional[str] - Specify a user id. If not set, a unique id will be generated."
    )
    user_alias_doc_str = (
        "Optional[str] - A descriptive name for you to know who this user id refers to."
    )
    teams_doc_str = "Optional[list] - specify a list of team id's a user belongs to."
    user_email_doc_str = "Optional[str] - Specify a user email."
    send_invite_email_doc_str = (
        "Optional[bool] - Specify if an invite email should be sent."
    )
    user_role_doc_str = """Optional[str] - Specify a user role - "proxy_admin", "proxy_admin_viewer", "internal_user", "internal_user_viewer", "team", "customer". Info about each role here: `https://github.com/BerriAI/litellm/litellm/proxy/_types.py#L20`"""
    max_budget_doc_str = """Optional[float] - Specify max budget for a given user."""
    budget_duration_doc_str = """Optional[str] - Budget is reset at the end of specified duration. If not set, budget is never reset. You can set duration as seconds ("30s"), minutes ("30m"), hours ("30h"), days ("30d"), months ("1mo")."""
    models_doc_str = """Optional[list] - Model_name's a user is allowed to call. (if empty, key is allowed to call all models)"""
    tpm_limit_doc_str = (
        """Optional[int] - Specify tpm limit for a given user (Tokens per minute)"""
    )
    rpm_limit_doc_str = (
        """Optional[int] - Specify rpm limit for a given user (Requests per minute)"""
    )
    auto_create_key_doc_str = """bool - Default=True. Flag used for returning a key as part of the /user/new response"""
    aliases_doc_str = """Optional[dict] - Model aliases for the user - [Docs](https://litellm.vercel.app/docs/proxy/virtual_keys#model-aliases)"""
    config_doc_str = """Optional[dict] - [DEPRECATED PARAM] User-specific config."""
    allowed_cache_controls_doc_str = """Optional[list] - List of allowed cache control values. Example - ["no-cache", "no-store"]. See all values - https://docs.litellm.ai/docs/proxy/caching#turn-on--off-caching-per-request-"""
    blocked_doc_str = (
        """Optional[bool] - [Not Implemented Yet] Whether the user is blocked."""
    )
    guardrails_doc_str = """Optional[List[str]] - [Not Implemented Yet] List of active guardrails for the user"""
    permissions_doc_str = """Optional[dict] - [Not Implemented Yet] User-specific permissions, eg. turning off pii masking."""
    metadata_doc_str = """Optional[dict] - Metadata for user, store information for user. Example metadata = {"team": "core-infra", "app": "app2", "email": "ishaan@berri.ai" }"""
    max_parallel_requests_doc_str = """Optional[int] - Rate limit a user based on the number of parallel requests. Raises 429 error, if user's parallel requests > x."""
    soft_budget_doc_str = """Optional[float] - Get alerts when user crosses given budget, doesn't block requests."""
    model_max_budget_doc_str = """Optional[dict] - Model-specific max budget for user. [Docs](https://docs.litellm.ai/docs/proxy/users#add-model-specific-budgets-to-keys)"""
    model_rpm_limit_doc_str = """Optional[float] - Model-specific rpm limit for user. [Docs](https://docs.litellm.ai/docs/proxy/users#add-model-specific-limits-to-keys)"""
    model_tpm_limit_doc_str = """Optional[float] - Model-specific tpm limit for user. [Docs](https://docs.litellm.ai/docs/proxy/users#add-model-specific-limits-to-keys)"""
    spend_doc_str = """Optional[float] - Amount spent by user. Default is 0. Will be updated by proxy whenever user is used."""
    team_id_doc_str = """Optional[str] - [DEPRECATED PARAM] The team id of the user. Default is None."""
    duration_doc_str = """Optional[str] - Duration for the key auto-created on `/user/new`. Default is None."""


PassThroughEndpointLoggingResultValues = Union[
    ModelResponse,
    TextCompletionResponse,
    ImageResponse,
    EmbeddingResponse,
    StandardPassThroughResponseObject,
]


class PassThroughEndpointLoggingTypedDict(TypedDict):
    result: Optional[PassThroughEndpointLoggingResultValues]
    kwargs: dict


LiteLLM_ManagementEndpoint_MetadataFields = [
    "model_rpm_limit",
    "model_tpm_limit",
    "guardrails",
    "tags",
    "enforced_params",
    "temp_budget_increase",
    "temp_budget_expiry",
]

LiteLLM_ManagementEndpoint_MetadataFields_Premium = [
    "guardrails",
    "tags",
]


class ProviderBudgetResponseObject(LiteLLMPydanticObjectBase):
    """
    Configuration for a single provider's budget settings
    """

    budget_limit: Optional[float]  # Budget limit in USD for the time period
    time_period: Optional[str]  # Time period for budget (e.g., '1d', '30d', '1mo')
    spend: Optional[float] = 0.0  # Current spend for this provider
    budget_reset_at: Optional[str] = None  # When the current budget period resets


class ProviderBudgetResponse(LiteLLMPydanticObjectBase):
    """
    Complete provider budget configuration and status.
    Maps provider names to their budget configs.
    """

    providers: Dict[str, ProviderBudgetResponseObject] = (
        {}
    )  # Dictionary mapping provider names to their budget configurations


class ProxyStateVariables(TypedDict):
    """
    TypedDict for Proxy state variables.
    """

    spend_logs_row_count: int


UI_TEAM_ID = "litellm-dashboard"


class JWTAuthBuilderResult(TypedDict):
    is_proxy_admin: bool
    team_object: Optional[LiteLLM_TeamTable]
    user_object: Optional[LiteLLM_UserTable]
    end_user_object: Optional[LiteLLM_EndUserTable]
    org_object: Optional[LiteLLM_OrganizationTable]
    token: str
    team_id: Optional[str]
    user_id: Optional[str]
    end_user_id: Optional[str]
    org_id: Optional[str]


class ClientSideFallbackModel(TypedDict, total=False):
    """
    Dictionary passed when client configuring input
    """

    model: Required[str]
    messages: List[AllMessageValues]


ALL_FALLBACK_MODEL_VALUES = Union[str, ClientSideFallbackModel]


RBAC_ROLES = Literal[
    LitellmUserRoles.PROXY_ADMIN,
    LitellmUserRoles.TEAM,
    LitellmUserRoles.INTERNAL_USER,
]


class OIDCPermissions(LiteLLMPydanticObjectBase):
    models: Optional[List[str]] = None
    routes: Optional[List[str]] = None


class RoleBasedPermissions(OIDCPermissions):
    role: RBAC_ROLES

    model_config = {
        "extra": "forbid",
    }


class RoleMapping(BaseModel):
    role: str
    internal_role: RBAC_ROLES


class ScopeMapping(OIDCPermissions):
    scope: str

    model_config = {
        "extra": "forbid",
    }


class LiteLLM_JWTAuth(LiteLLMPydanticObjectBase):
    """
    A class to define the roles and permissions for a LiteLLM Proxy w/ JWT Auth.

    Attributes:
    - admin_jwt_scope: The JWT scope required for proxy admin roles.
    - admin_allowed_routes: list of allowed routes for proxy admin roles.
    - team_jwt_scope: The JWT scope required for proxy team roles.
    - team_id_jwt_field: The field in the JWT token that stores the team ID. Default - `client_id`.
    - team_allowed_routes: list of allowed routes for proxy team roles.
    - user_id_jwt_field: The field in the JWT token that stores the user id (maps to `LiteLLMUserTable`). Use this for internal employees.
    - user_email_jwt_field: The field in the JWT token that stores the user email (maps to `LiteLLMUserTable`). Use this for internal employees.
    - user_allowed_email_subdomain: If specified, only emails from specified subdomain will be allowed to access proxy.
    - end_user_id_jwt_field: The field in the JWT token that stores the end-user ID (maps to `LiteLLMEndUserTable`). Turn this off by setting to `None`. Enables end-user cost tracking. Use this for external customers.
    - public_key_ttl: Default - 600s. TTL for caching public JWT keys.
    - public_allowed_routes: list of allowed routes for authenticated but unknown litellm role jwt tokens.
    - enforce_rbac: If true, enforce RBAC for all routes.
    - custom_validate: A custom function to validates the JWT token.

    See `auth_checks.py` for the specific routes
    """

    admin_jwt_scope: str = "litellm_proxy_admin"
    admin_allowed_routes: List[str] = [
        "management_routes",
        "spend_tracking_routes",
        "global_spend_tracking_routes",
        "info_routes",
    ]
    team_id_jwt_field: Optional[str] = None
    team_id_upsert: bool = False
    team_ids_jwt_field: Optional[str] = None
    upsert_sso_user_to_team: bool = False
    team_allowed_routes: List[
        Literal["openai_routes", "info_routes", "management_routes"]
    ] = ["openai_routes", "info_routes"]
    team_id_default: Optional[str] = Field(
        default=None,
        description="If no team_id given, default permissions/spend-tracking to this team.s",
    )

    org_id_jwt_field: Optional[str] = None
    user_id_jwt_field: Optional[str] = None
    user_email_jwt_field: Optional[str] = None
    user_allowed_email_domain: Optional[str] = None
    user_roles_jwt_field: Optional[str] = None
    user_allowed_roles: Optional[List[str]] = None
    user_id_upsert: bool = Field(
        default=False, description="If user doesn't exist, upsert them into the db."
    )
    end_user_id_jwt_field: Optional[str] = None
    public_key_ttl: float = 600
    public_allowed_routes: List[str] = ["public_routes"]
    enforce_rbac: bool = False
    roles_jwt_field: Optional[str] = None  # v2 on role mappings
    role_mappings: Optional[List[RoleMapping]] = None
    object_id_jwt_field: Optional[str] = (
        None  # can be either user / team, inferred from the role mapping
    )
    scope_mappings: Optional[List[ScopeMapping]] = None
    enforce_scope_based_access: bool = False
    enforce_team_based_model_access: bool = False
    custom_validate: Optional[Callable[..., Literal[True]]] = None

    def __init__(self, **kwargs: Any) -> None:
        # get the attribute names for this Pydantic model
        allowed_keys = self.__annotations__.keys()

        invalid_keys = set(kwargs.keys()) - allowed_keys
        user_roles_jwt_field = kwargs.get("user_roles_jwt_field")
        user_allowed_roles = kwargs.get("user_allowed_roles")
        object_id_jwt_field = kwargs.get("object_id_jwt_field")
        role_mappings = kwargs.get("role_mappings")
        scope_mappings = kwargs.get("scope_mappings")
        enforce_scope_based_access = kwargs.get("enforce_scope_based_access")
        custom_validate = kwargs.get("custom_validate")

        if custom_validate is not None:
            fn = get_instance_fn(custom_validate)
            validate_custom_validate_return_type(fn)
            kwargs["custom_validate"] = fn

        if invalid_keys:
            raise ValueError(
                f"Invalid arguments provided: {', '.join(invalid_keys)}. Allowed arguments are: {', '.join(allowed_keys)}."
            )
        if (user_roles_jwt_field is not None and user_allowed_roles is None) or (
            user_roles_jwt_field is None and user_allowed_roles is not None
        ):
            raise ValueError(
                "user_allowed_roles must be provided if user_roles_jwt_field is set."
            )

        if object_id_jwt_field is not None and role_mappings is None:
            raise ValueError(
                "if object_id_jwt_field is set, role_mappings must also be set. Needed to infer if the caller is a user or team."
            )

        if scope_mappings is not None and not enforce_scope_based_access:
            raise ValueError(
                "scope_mappings must be set if enforce_scope_based_access is true."
            )

        super().__init__(**kwargs)


class PrismaCompatibleUpdateDBModel(TypedDict, total=False):
    model_name: str
    litellm_params: str
    model_info: str
    updated_at: str
    updated_by: str


class SpecialManagementEndpointEnums(enum.Enum):
    DEFAULT_ORGANIZATION = "default_organization"


class TransformRequestBody(BaseModel):
    call_type: CallTypes
    request_body: dict


class DefaultInternalUserParams(LiteLLMPydanticObjectBase):
    """
    Default parameters to apply when a new user signs in via SSO or is created on the /user/new API endpoint
    """

    user_role: Optional[
        Literal[
            LitellmUserRoles.INTERNAL_USER,
            LitellmUserRoles.INTERNAL_USER_VIEW_ONLY,
            LitellmUserRoles.PROXY_ADMIN,
            LitellmUserRoles.PROXY_ADMIN_VIEW_ONLY,
        ]
    ] = Field(
        default=LitellmUserRoles.INTERNAL_USER,
        description="Default role assigned to new users created",
    )
    max_budget: Optional[float] = Field(
        default=None,
        description="Default maximum budget (in USD) for new users created",
    )
    budget_duration: Optional[str] = Field(
        default=None,
        description="Default budget duration for new users (e.g. 'daily', 'weekly', 'monthly')",
    )
    models: Optional[List[str]] = Field(
        default=None, description="Default list of models that new users can access"
    )

    teams: Optional[Union[List[str], List[NewUserRequestTeam]]] = Field(
        default=None,
        description="Default teams for new users created",
    )


class BaseDailySpendTransaction(TypedDict):
    date: str
    api_key: str
    model: str
    model_group: Optional[str]
    custom_llm_provider: Optional[str]

    # token count metrics
    prompt_tokens: int
    completion_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int

    # request level metrics
    spend: float
    api_requests: int
    successful_requests: int
    failed_requests: int


class DailyTeamSpendTransaction(BaseDailySpendTransaction):
    team_id: str


class DailyUserSpendTransaction(BaseDailySpendTransaction):
    user_id: str


class DailyTagSpendTransaction(BaseDailySpendTransaction):
    tag: str


class DBSpendUpdateTransactions(TypedDict):
    """
    Internal Data Structure for buffering spend updates in Redis or in memory before committing them to the database
    """

    user_list_transactions: Optional[Dict[str, float]]
    end_user_list_transactions: Optional[Dict[str, float]]
    key_list_transactions: Optional[Dict[str, float]]
    team_list_transactions: Optional[Dict[str, float]]
    team_member_list_transactions: Optional[Dict[str, float]]
    org_list_transactions: Optional[Dict[str, float]]


class SpendUpdateQueueItem(TypedDict, total=False):
    entity_type: Litellm_EntityType
    entity_id: str
    response_cost: Optional[float]


class LiteLLM_ManagedFileTable(LiteLLMPydanticObjectBase):
    unified_file_id: str
    file_object: OpenAIFileObject
    model_mappings: Dict[str, str]
    flat_model_file_ids: List[str]
    created_by: Optional[str]
    updated_by: Optional[str]


class LiteLLM_ManagedObjectTable(LiteLLMPydanticObjectBase):
    unified_object_id: str
    model_object_id: str
    file_purpose: Literal["batch", "fine-tune"]
    file_object: Union[LiteLLMBatch, LiteLLMFineTuningJob]


class EnterpriseLicenseData(TypedDict, total=False):
    expiration_date: str
    user_id: str
    allowed_features: List[str]
    max_users: int
    max_teams: int

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_scilab_builtins.py ===
"""
    pygments.lexers._scilab_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Builtin list for the ScilabLexer.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# Autogenerated

commands_kw = (
    'abort',
    'apropos',
    'break',
    'case',
    'catch',
    'continue',
    'do',
    'else',
    'elseif',
    'end',
    'endfunction',
    'for',
    'function',
    'help',
    'if',
    'pause',
    'quit',
    'select',
    'then',
    'try',
    'while',
)

functions_kw = (
    '!!_invoke_',
    '%H5Object_e',
    '%H5Object_fieldnames',
    '%H5Object_p',
    '%XMLAttr_6',
    '%XMLAttr_e',
    '%XMLAttr_i_XMLElem',
    '%XMLAttr_length',
    '%XMLAttr_p',
    '%XMLAttr_size',
    '%XMLDoc_6',
    '%XMLDoc_e',
    '%XMLDoc_i_XMLList',
    '%XMLDoc_p',
    '%XMLElem_6',
    '%XMLElem_e',
    '%XMLElem_i_XMLDoc',
    '%XMLElem_i_XMLElem',
    '%XMLElem_i_XMLList',
    '%XMLElem_p',
    '%XMLList_6',
    '%XMLList_e',
    '%XMLList_i_XMLElem',
    '%XMLList_i_XMLList',
    '%XMLList_length',
    '%XMLList_p',
    '%XMLList_size',
    '%XMLNs_6',
    '%XMLNs_e',
    '%XMLNs_i_XMLElem',
    '%XMLNs_p',
    '%XMLSet_6',
    '%XMLSet_e',
    '%XMLSet_length',
    '%XMLSet_p',
    '%XMLSet_size',
    '%XMLValid_p',
    '%_EClass_6',
    '%_EClass_e',
    '%_EClass_p',
    '%_EObj_0',
    '%_EObj_1__EObj',
    '%_EObj_1_b',
    '%_EObj_1_c',
    '%_EObj_1_i',
    '%_EObj_1_s',
    '%_EObj_2__EObj',
    '%_EObj_2_b',
    '%_EObj_2_c',
    '%_EObj_2_i',
    '%_EObj_2_s',
    '%_EObj_3__EObj',
    '%_EObj_3_b',
    '%_EObj_3_c',
    '%_EObj_3_i',
    '%_EObj_3_s',
    '%_EObj_4__EObj',
    '%_EObj_4_b',
    '%_EObj_4_c',
    '%_EObj_4_i',
    '%_EObj_4_s',
    '%_EObj_5',
    '%_EObj_6',
    '%_EObj_a__EObj',
    '%_EObj_a_b',
    '%_EObj_a_c',
    '%_EObj_a_i',
    '%_EObj_a_s',
    '%_EObj_d__EObj',
    '%_EObj_d_b',
    '%_EObj_d_c',
    '%_EObj_d_i',
    '%_EObj_d_s',
    '%_EObj_disp',
    '%_EObj_e',
    '%_EObj_g__EObj',
    '%_EObj_g_b',
    '%_EObj_g_c',
    '%_EObj_g_i',
    '%_EObj_g_s',
    '%_EObj_h__EObj',
    '%_EObj_h_b',
    '%_EObj_h_c',
    '%_EObj_h_i',
    '%_EObj_h_s',
    '%_EObj_i__EObj',
    '%_EObj_j__EObj',
    '%_EObj_j_b',
    '%_EObj_j_c',
    '%_EObj_j_i',
    '%_EObj_j_s',
    '%_EObj_k__EObj',
    '%_EObj_k_b',
    '%_EObj_k_c',
    '%_EObj_k_i',
    '%_EObj_k_s',
    '%_EObj_l__EObj',
    '%_EObj_l_b',
    '%_EObj_l_c',
    '%_EObj_l_i',
    '%_EObj_l_s',
    '%_EObj_m__EObj',
    '%_EObj_m_b',
    '%_EObj_m_c',
    '%_EObj_m_i',
    '%_EObj_m_s',
    '%_EObj_n__EObj',
    '%_EObj_n_b',
    '%_EObj_n_c',
    '%_EObj_n_i',
    '%_EObj_n_s',
    '%_EObj_o__EObj',
    '%_EObj_o_b',
    '%_EObj_o_c',
    '%_EObj_o_i',
    '%_EObj_o_s',
    '%_EObj_p',
    '%_EObj_p__EObj',
    '%_EObj_p_b',
    '%_EObj_p_c',
    '%_EObj_p_i',
    '%_EObj_p_s',
    '%_EObj_q__EObj',
    '%_EObj_q_b',
    '%_EObj_q_c',
    '%_EObj_q_i',
    '%_EObj_q_s',
    '%_EObj_r__EObj',
    '%_EObj_r_b',
    '%_EObj_r_c',
    '%_EObj_r_i',
    '%_EObj_r_s',
    '%_EObj_s__EObj',
    '%_EObj_s_b',
    '%_EObj_s_c',
    '%_EObj_s_i',
    '%_EObj_s_s',
    '%_EObj_t',
    '%_EObj_x__EObj',
    '%_EObj_x_b',
    '%_EObj_x_c',
    '%_EObj_x_i',
    '%_EObj_x_s',
    '%_EObj_y__EObj',
    '%_EObj_y_b',
    '%_EObj_y_c',
    '%_EObj_y_i',
    '%_EObj_y_s',
    '%_EObj_z__EObj',
    '%_EObj_z_b',
    '%_EObj_z_c',
    '%_EObj_z_i',
    '%_EObj_z_s',
    '%_eigs',
    '%_load',
    '%b_1__EObj',
    '%b_2__EObj',
    '%b_3__EObj',
    '%b_4__EObj',
    '%b_a__EObj',
    '%b_d__EObj',
    '%b_g__EObj',
    '%b_h__EObj',
    '%b_i_XMLList',
    '%b_i__EObj',
    '%b_j__EObj',
    '%b_k__EObj',
    '%b_l__EObj',
    '%b_m__EObj',
    '%b_n__EObj',
    '%b_o__EObj',
    '%b_p__EObj',
    '%b_q__EObj',
    '%b_r__EObj',
    '%b_s__EObj',
    '%b_x__EObj',
    '%b_y__EObj',
    '%b_z__EObj',
    '%c_1__EObj',
    '%c_2__EObj',
    '%c_3__EObj',
    '%c_4__EObj',
    '%c_a__EObj',
    '%c_d__EObj',
    '%c_g__EObj',
    '%c_h__EObj',
    '%c_i_XMLAttr',
    '%c_i_XMLDoc',
    '%c_i_XMLElem',
    '%c_i_XMLList',
    '%c_i__EObj',
    '%c_j__EObj',
    '%c_k__EObj',
    '%c_l__EObj',
    '%c_m__EObj',
    '%c_n__EObj',
    '%c_o__EObj',
    '%c_p__EObj',
    '%c_q__EObj',
    '%c_r__EObj',
    '%c_s__EObj',
    '%c_x__EObj',
    '%c_y__EObj',
    '%c_z__EObj',
    '%ce_i_XMLList',
    '%fptr_i_XMLList',
    '%h_i_XMLList',
    '%hm_i_XMLList',
    '%i_1__EObj',
    '%i_2__EObj',
    '%i_3__EObj',
    '%i_4__EObj',
    '%i_a__EObj',
    '%i_abs',
    '%i_cumprod',
    '%i_cumsum',
    '%i_d__EObj',
    '%i_diag',
    '%i_g__EObj',
    '%i_h__EObj',
    '%i_i_XMLList',
    '%i_i__EObj',
    '%i_j__EObj',
    '%i_k__EObj',
    '%i_l__EObj',
    '%i_m__EObj',
    '%i_matrix',
    '%i_max',
    '%i_maxi',
    '%i_min',
    '%i_mini',
    '%i_mput',
    '%i_n__EObj',
    '%i_o__EObj',
    '%i_p',
    '%i_p__EObj',
    '%i_prod',
    '%i_q__EObj',
    '%i_r__EObj',
    '%i_s__EObj',
    '%i_sum',
    '%i_tril',
    '%i_triu',
    '%i_x__EObj',
    '%i_y__EObj',
    '%i_z__EObj',
    '%ip_i_XMLList',
    '%l_i_XMLList',
    '%l_i__EObj',
    '%lss_i_XMLList',
    '%mc_i_XMLList',
    '%msp_full',
    '%msp_i_XMLList',
    '%msp_spget',
    '%p_i_XMLList',
    '%ptr_i_XMLList',
    '%r_i_XMLList',
    '%s_1__EObj',
    '%s_2__EObj',
    '%s_3__EObj',
    '%s_4__EObj',
    '%s_a__EObj',
    '%s_d__EObj',
    '%s_g__EObj',
    '%s_h__EObj',
    '%s_i_XMLList',
    '%s_i__EObj',
    '%s_j__EObj',
    '%s_k__EObj',
    '%s_l__EObj',
    '%s_m__EObj',
    '%s_n__EObj',
    '%s_o__EObj',
    '%s_p__EObj',
    '%s_q__EObj',
    '%s_r__EObj',
    '%s_s__EObj',
    '%s_x__EObj',
    '%s_y__EObj',
    '%s_z__EObj',
    '%sp_i_XMLList',
    '%spb_i_XMLList',
    '%st_i_XMLList',
    'Calendar',
    'ClipBoard',
    'Matplot',
    'Matplot1',
    'PlaySound',
    'TCL_DeleteInterp',
    'TCL_DoOneEvent',
    'TCL_EvalFile',
    'TCL_EvalStr',
    'TCL_ExistArray',
    'TCL_ExistInterp',
    'TCL_ExistVar',
    'TCL_GetVar',
    'TCL_GetVersion',
    'TCL_SetVar',
    'TCL_UnsetVar',
    'TCL_UpVar',
    '_',
    '_code2str',
    '_d',
    '_str2code',
    'about',
    'abs',
    'acos',
    'addModulePreferences',
    'addcolor',
    'addf',
    'addhistory',
    'addinter',
    'addlocalizationdomain',
    'amell',
    'and',
    'argn',
    'arl2_ius',
    'ascii',
    'asin',
    'atan',
    'backslash',
    'balanc',
    'banner',
    'base2dec',
    'basename',
    'bdiag',
    'beep',
    'besselh',
    'besseli',
    'besselj',
    'besselk',
    'bessely',
    'beta',
    'bezout',
    'bfinit',
    'blkfc1i',
    'blkslvi',
    'bool2s',
    'browsehistory',
    'browsevar',
    'bsplin3val',
    'buildDoc',
    'buildouttb',
    'bvode',
    'c_link',
    'call',
    'callblk',
    'captions',
    'cd',
    'cdfbet',
    'cdfbin',
    'cdfchi',
    'cdfchn',
    'cdff',
    'cdffnc',
    'cdfgam',
    'cdfnbn',
    'cdfnor',
    'cdfpoi',
    'cdft',
    'ceil',
    'champ',
    'champ1',
    'chdir',
    'chol',
    'clc',
    'clean',
    'clear',
    'clearfun',
    'clearglobal',
    'closeEditor',
    'closeEditvar',
    'closeXcos',
    'code2str',
    'coeff',
    'color',
    'comp',
    'completion',
    'conj',
    'contour2di',
    'contr',
    'conv2',
    'convstr',
    'copy',
    'copyfile',
    'corr',
    'cos',
    'coserror',
    'createdir',
    'cshep2d',
    'csvDefault',
    'csvIsnum',
    'csvRead',
    'csvStringToDouble',
    'csvTextScan',
    'csvWrite',
    'ctree2',
    'ctree3',
    'ctree4',
    'cumprod',
    'cumsum',
    'curblock',
    'curblockc',
    'daskr',
    'dasrt',
    'dassl',
    'data2sig',
    'datatipCreate',
    'datatipManagerMode',
    'datatipMove',
    'datatipRemove',
    'datatipSetDisplay',
    'datatipSetInterp',
    'datatipSetOrientation',
    'datatipSetStyle',
    'datatipToggle',
    'dawson',
    'dct',
    'debug',
    'dec2base',
    'deff',
    'definedfields',
    'degree',
    'delbpt',
    'delete',
    'deletefile',
    'delip',
    'delmenu',
    'det',
    'dgettext',
    'dhinf',
    'diag',
    'diary',
    'diffobjs',
    'disp',
    'dispbpt',
    'displayhistory',
    'disposefftwlibrary',
    'dlgamma',
    'dnaupd',
    'dneupd',
    'double',
    'drawaxis',
    'drawlater',
    'drawnow',
    'driver',
    'dsaupd',
    'dsearch',
    'dseupd',
    'dst',
    'duplicate',
    'editvar',
    'emptystr',
    'end_scicosim',
    'ereduc',
    'erf',
    'erfc',
    'erfcx',
    'erfi',
    'errcatch',
    'errclear',
    'error',
    'eval_cshep2d',
    'exec',
    'execstr',
    'exists',
    'exit',
    'exp',
    'expm',
    'exportUI',
    'export_to_hdf5',
    'eye',
    'fadj2sp',
    'fec',
    'feval',
    'fft',
    'fftw',
    'fftw_flags',
    'fftw_forget_wisdom',
    'fftwlibraryisloaded',
    'figure',
    'file',
    'filebrowser',
    'fileext',
    'fileinfo',
    'fileparts',
    'filesep',
    'find',
    'findBD',
    'findfiles',
    'fire_closing_finished',
    'floor',
    'format',
    'fort',
    'fprintfMat',
    'freq',
    'frexp',
    'fromc',
    'fromjava',
    'fscanfMat',
    'fsolve',
    'fstair',
    'full',
    'fullpath',
    'funcprot',
    'funptr',
    'gamma',
    'gammaln',
    'geom3d',
    'get',
    'getURL',
    'get_absolute_file_path',
    'get_fftw_wisdom',
    'getblocklabel',
    'getcallbackobject',
    'getdate',
    'getdebuginfo',
    'getdefaultlanguage',
    'getdrives',
    'getdynlibext',
    'getenv',
    'getfield',
    'gethistory',
    'gethistoryfile',
    'getinstalledlookandfeels',
    'getio',
    'getlanguage',
    'getlongpathname',
    'getlookandfeel',
    'getmd5',
    'getmemory',
    'getmodules',
    'getos',
    'getpid',
    'getrelativefilename',
    'getscicosvars',
    'getscilabmode',
    'getshortpathname',
    'gettext',
    'getvariablesonstack',
    'getversion',
    'glist',
    'global',
    'glue',
    'grand',
    'graphicfunction',
    'grayplot',
    'grep',
    'gsort',
    'gstacksize',
    'h5attr',
    'h5close',
    'h5cp',
    'h5dataset',
    'h5dump',
    'h5exists',
    'h5flush',
    'h5get',
    'h5group',
    'h5isArray',
    'h5isAttr',
    'h5isCompound',
    'h5isFile',
    'h5isGroup',
    'h5isList',
    'h5isRef',
    'h5isSet',
    'h5isSpace',
    'h5isType',
    'h5isVlen',
    'h5label',
    'h5ln',
    'h5ls',
    'h5mount',
    'h5mv',
    'h5open',
    'h5read',
    'h5readattr',
    'h5rm',
    'h5umount',
    'h5write',
    'h5writeattr',
    'havewindow',
    'helpbrowser',
    'hess',
    'hinf',
    'historymanager',
    'historysize',
    'host',
    'htmlDump',
    'htmlRead',
    'htmlReadStr',
    'htmlWrite',
    'iconvert',
    'ieee',
    'ilib_verbose',
    'imag',
    'impl',
    'import_from_hdf5',
    'imult',
    'inpnvi',
    'int',
    'int16',
    'int2d',
    'int32',
    'int3d',
    'int8',
    'interp',
    'interp2d',
    'interp3d',
    'intg',
    'intppty',
    'inttype',
    'inv',
    'invoke_lu',
    'is_handle_valid',
    'is_hdf5_file',
    'isalphanum',
    'isascii',
    'isdef',
    'isdigit',
    'isdir',
    'isequal',
    'isequalbitwise',
    'iserror',
    'isfile',
    'isglobal',
    'isletter',
    'isnum',
    'isreal',
    'iswaitingforinput',
    'jallowClassReloading',
    'jarray',
    'jautoTranspose',
    'jautoUnwrap',
    'javaclasspath',
    'javalibrarypath',
    'jcast',
    'jcompile',
    'jconvMatrixMethod',
    'jcreatejar',
    'jdeff',
    'jdisableTrace',
    'jenableTrace',
    'jexists',
    'jgetclassname',
    'jgetfield',
    'jgetfields',
    'jgetinfo',
    'jgetmethods',
    'jimport',
    'jinvoke',
    'jinvoke_db',
    'jnewInstance',
    'jremove',
    'jsetfield',
    'junwrap',
    'junwraprem',
    'jwrap',
    'jwrapinfloat',
    'kron',
    'lasterror',
    'ldiv',
    'ldivf',
    'legendre',
    'length',
    'lib',
    'librarieslist',
    'libraryinfo',
    'light',
    'linear_interpn',
    'lines',
    'link',
    'linmeq',
    'list',
    'listvar_in_hdf5',
    'load',
    'loadGui',
    'loadScicos',
    'loadXcos',
    'loadfftwlibrary',
    'loadhistory',
    'log',
    'log1p',
    'lsq',
    'lsq_splin',
    'lsqrsolve',
    'lsslist',
    'lstcat',
    'lstsize',
    'ltitr',
    'lu',
    'ludel',
    'lufact',
    'luget',
    'lusolve',
    'macr2lst',
    'macr2tree',
    'matfile_close',
    'matfile_listvar',
    'matfile_open',
    'matfile_varreadnext',
    'matfile_varwrite',
    'matrix',
    'max',
    'maxfiles',
    'mclearerr',
    'mclose',
    'meof',
    'merror',
    'messagebox',
    'mfprintf',
    'mfscanf',
    'mget',
    'mgeti',
    'mgetl',
    'mgetstr',
    'min',
    'mlist',
    'mode',
    'model2blk',
    'mopen',
    'move',
    'movefile',
    'mprintf',
    'mput',
    'mputl',
    'mputstr',
    'mscanf',
    'mseek',
    'msprintf',
    'msscanf',
    'mtell',
    'mtlb_mode',
    'mtlb_sparse',
    'mucomp',
    'mulf',
    'name2rgb',
    'nearfloat',
    'newaxes',
    'newest',
    'newfun',
    'nnz',
    'norm',
    'notify',
    'number_properties',
    'ode',
    'odedc',
    'ones',
    'openged',
    'opentk',
    'optim',
    'or',
    'ordmmd',
    'parallel_concurrency',
    'parallel_run',
    'param3d',
    'param3d1',
    'part',
    'pathconvert',
    'pathsep',
    'phase_simulation',
    'plot2d',
    'plot2d1',
    'plot2d2',
    'plot2d3',
    'plot2d4',
    'plot3d',
    'plot3d1',
    'plotbrowser',
    'pointer_xproperty',
    'poly',
    'ppol',
    'pppdiv',
    'predef',
    'preferences',
    'print',
    'printf',
    'printfigure',
    'printsetupbox',
    'prod',
    'progressionbar',
    'prompt',
    'pwd',
    'qld',
    'qp_solve',
    'qr',
    'raise_window',
    'rand',
    'rankqr',
    'rat',
    'rcond',
    'rdivf',
    'read',
    'read4b',
    'read_csv',
    'readb',
    'readgateway',
    'readmps',
    'real',
    'realtime',
    'realtimeinit',
    'regexp',
    'relocate_handle',
    'remez',
    'removeModulePreferences',
    'removedir',
    'removelinehistory',
    'res_with_prec',
    'resethistory',
    'residu',
    'resume',
    'return',
    'ricc',
    'rlist',
    'roots',
    'rotate_axes',
    'round',
    'rpem',
    'rtitr',
    'rubberbox',
    'save',
    'saveGui',
    'saveafterncommands',
    'saveconsecutivecommands',
    'savehistory',
    'schur',
    'sci_haltscicos',
    'sci_tree2',
    'sci_tree3',
    'sci_tree4',
    'sciargs',
    'scicos_debug',
    'scicos_debug_count',
    'scicos_time',
    'scicosim',
    'scinotes',
    'sctree',
    'semidef',
    'set',
    'set_blockerror',
    'set_fftw_wisdom',
    'set_xproperty',
    'setbpt',
    'setdefaultlanguage',
    'setenv',
    'setfield',
    'sethistoryfile',
    'setlanguage',
    'setlookandfeel',
    'setmenu',
    'sfact',
    'sfinit',
    'show_window',
    'sident',
    'sig2data',
    'sign',
    'simp',
    'simp_mode',
    'sin',
    'size',
    'slash',
    'sleep',
    'sorder',
    'sparse',
    'spchol',
    'spcompack',
    'spec',
    'spget',
    'splin',
    'splin2d',
    'splin3d',
    'splitURL',
    'spones',
    'sprintf',
    'sqrt',
    'stacksize',
    'str2code',
    'strcat',
    'strchr',
    'strcmp',
    'strcspn',
    'strindex',
    'string',
    'stringbox',
    'stripblanks',
    'strncpy',
    'strrchr',
    'strrev',
    'strsplit',
    'strspn',
    'strstr',
    'strsubst',
    'strtod',
    'strtok',
    'subf',
    'sum',
    'svd',
    'swap_handles',
    'symfcti',
    'syredi',
    'system_getproperty',
    'system_setproperty',
    'ta2lpd',
    'tan',
    'taucs_chdel',
    'taucs_chfact',
    'taucs_chget',
    'taucs_chinfo',
    'taucs_chsolve',
    'tempname',
    'testmatrix',
    'timer',
    'tlist',
    'tohome',
    'tokens',
    'toolbar',
    'toprint',
    'tr_zer',
    'tril',
    'triu',
    'type',
    'typename',
    'uiDisplayTree',
    'uicontextmenu',
    'uicontrol',
    'uigetcolor',
    'uigetdir',
    'uigetfile',
    'uigetfont',
    'uimenu',
    'uint16',
    'uint32',
    'uint8',
    'uipopup',
    'uiputfile',
    'uiwait',
    'ulink',
    'umf_ludel',
    'umf_lufact',
    'umf_luget',
    'umf_luinfo',
    'umf_lusolve',
    'umfpack',
    'unglue',
    'unix',
    'unsetmenu',
    'unzoom',
    'updatebrowsevar',
    'usecanvas',
    'useeditor',
    'user',
    'var2vec',
    'varn',
    'vec2var',
    'waitbar',
    'warnBlockByUID',
    'warning',
    'what',
    'where',
    'whereis',
    'who',
    'winsid',
    'with_module',
    'writb',
    'write',
    'write4b',
    'write_csv',
    'x_choose',
    'x_choose_modeless',
    'x_dialog',
    'x_mdialog',
    'xarc',
    'xarcs',
    'xarrows',
    'xchange',
    'xchoicesi',
    'xclick',
    'xcos',
    'xcosAddToolsMenu',
    'xcosConfigureXmlFile',
    'xcosDiagramToScilab',
    'xcosPalCategoryAdd',
    'xcosPalDelete',
    'xcosPalDisable',
    'xcosPalEnable',
    'xcosPalGenerateIcon',
    'xcosPalGet',
    'xcosPalLoad',
    'xcosPalMove',
    'xcosSimulationStarted',
    'xcosUpdateBlock',
    'xdel',
    'xend',
    'xfarc',
    'xfarcs',
    'xfpoly',
    'xfpolys',
    'xfrect',
    'xget',
    'xgetmouse',
    'xgraduate',
    'xgrid',
    'xinit',
    'xlfont',
    'xls_open',
    'xls_read',
    'xmlAddNs',
    'xmlAppend',
    'xmlAsNumber',
    'xmlAsText',
    'xmlDTD',
    'xmlDelete',
    'xmlDocument',
    'xmlDump',
    'xmlElement',
    'xmlFormat',
    'xmlGetNsByHref',
    'xmlGetNsByPrefix',
    'xmlGetOpenDocs',
    'xmlIsValidObject',
    'xmlName',
    'xmlNs',
    'xmlRead',
    'xmlReadStr',
    'xmlRelaxNG',
    'xmlRemove',
    'xmlSchema',
    'xmlSetAttributes',
    'xmlValidate',
    'xmlWrite',
    'xmlXPath',
    'xname',
    'xpause',
    'xpoly',
    'xpolys',
    'xrect',
    'xrects',
    'xs2bmp',
    'xs2emf',
    'xs2eps',
    'xs2gif',
    'xs2jpg',
    'xs2pdf',
    'xs2png',
    'xs2ppm',
    'xs2ps',
    'xs2svg',
    'xsegs',
    'xset',
    'xstring',
    'xstringb',
    'xtitle',
    'zeros',
    'znaupd',
    'zneupd',
    'zoom_rect',
)

macros_kw = (
    '!_deff_wrapper',
    '%0_i_st',
    '%3d_i_h',
    '%Block_xcosUpdateBlock',
    '%TNELDER_p',
    '%TNELDER_string',
    '%TNMPLOT_p',
    '%TNMPLOT_string',
    '%TOPTIM_p',
    '%TOPTIM_string',
    '%TSIMPLEX_p',
    '%TSIMPLEX_string',
    '%_EVoid_p',
    '%_gsort',
    '%_listvarinfile',
    '%_rlist',
    '%_save',
    '%_sodload',
    '%_strsplit',
    '%_unwrap',
    '%ar_p',
    '%asn',
    '%b_a_b',
    '%b_a_s',
    '%b_c_s',
    '%b_c_spb',
    '%b_cumprod',
    '%b_cumsum',
    '%b_d_s',
    '%b_diag',
    '%b_e',
    '%b_f_s',
    '%b_f_spb',
    '%b_g_s',
    '%b_g_spb',
    '%b_grand',
    '%b_h_s',
    '%b_h_spb',
    '%b_i_b',
    '%b_i_ce',
    '%b_i_h',
    '%b_i_hm',
    '%b_i_s',
    '%b_i_sp',
    '%b_i_spb',
    '%b_i_st',
    '%b_iconvert',
    '%b_l_b',
    '%b_l_s',
    '%b_m_b',
    '%b_m_s',
    '%b_matrix',
    '%b_n_hm',
    '%b_o_hm',
    '%b_p_s',
    '%b_prod',
    '%b_r_b',
    '%b_r_s',
    '%b_s_b',
    '%b_s_s',
    '%b_string',
    '%b_sum',
    '%b_tril',
    '%b_triu',
    '%b_x_b',
    '%b_x_s',
    '%bicg',
    '%bicgstab',
    '%c_a_c',
    '%c_b_c',
    '%c_b_s',
    '%c_diag',
    '%c_dsearch',
    '%c_e',
    '%c_eye',
    '%c_f_s',
    '%c_grand',
    '%c_i_c',
    '%c_i_ce',
    '%c_i_h',
    '%c_i_hm',
    '%c_i_lss',
    '%c_i_r',
    '%c_i_s',
    '%c_i_st',
    '%c_matrix',
    '%c_n_l',
    '%c_n_st',
    '%c_o_l',
    '%c_o_st',
    '%c_ones',
    '%c_rand',
    '%c_tril',
    '%c_triu',
    '%cblock_c_cblock',
    '%cblock_c_s',
    '%cblock_e',
    '%cblock_f_cblock',
    '%cblock_p',
    '%cblock_size',
    '%ce_6',
    '%ce_c_ce',
    '%ce_e',
    '%ce_f_ce',
    '%ce_i_ce',
    '%ce_i_s',
    '%ce_i_st',
    '%ce_matrix',
    '%ce_p',
    '%ce_size',
    '%ce_string',
    '%ce_t',
    '%cgs',
    '%champdat_i_h',
    '%choose',
    '%diagram_xcos',
    '%dir_p',
    '%fptr_i_st',
    '%grand_perm',
    '%grayplot_i_h',
    '%h_i_st',
    '%hmS_k_hmS_generic',
    '%hm_1_hm',
    '%hm_1_s',
    '%hm_2_hm',
    '%hm_2_s',
    '%hm_3_hm',
    '%hm_3_s',
    '%hm_4_hm',
    '%hm_4_s',
    '%hm_5',
    '%hm_a_hm',
    '%hm_a_r',
    '%hm_a_s',
    '%hm_abs',
    '%hm_and',
    '%hm_bool2s',
    '%hm_c_hm',
    '%hm_ceil',
    '%hm_conj',
    '%hm_cos',
    '%hm_cumprod',
    '%hm_cumsum',
    '%hm_d_hm',
    '%hm_d_s',
    '%hm_degree',
    '%hm_dsearch',
    '%hm_e',
    '%hm_exp',
    '%hm_eye',
    '%hm_f_hm',
    '%hm_find',
    '%hm_floor',
    '%hm_g_hm',
    '%hm_grand',
    '%hm_gsort',
    '%hm_h_hm',
    '%hm_i_b',
    '%hm_i_ce',
    '%hm_i_h',
    '%hm_i_hm',
    '%hm_i_i',
    '%hm_i_p',
    '%hm_i_r',
    '%hm_i_s',
    '%hm_i_st',
    '%hm_iconvert',
    '%hm_imag',
    '%hm_int',
    '%hm_isnan',
    '%hm_isreal',
    '%hm_j_hm',
    '%hm_j_s',
    '%hm_k_hm',
    '%hm_k_s',
    '%hm_log',
    '%hm_m_p',
    '%hm_m_r',
    '%hm_m_s',
    '%hm_matrix',
    '%hm_max',
    '%hm_mean',
    '%hm_median',
    '%hm_min',
    '%hm_n_b',
    '%hm_n_c',
    '%hm_n_hm',
    '%hm_n_i',
    '%hm_n_p',
    '%hm_n_s',
    '%hm_o_b',
    '%hm_o_c',
    '%hm_o_hm',
    '%hm_o_i',
    '%hm_o_p',
    '%hm_o_s',
    '%hm_ones',
    '%hm_or',
    '%hm_p',
    '%hm_prod',
    '%hm_q_hm',
    '%hm_r_s',
    '%hm_rand',
    '%hm_real',
    '%hm_round',
    '%hm_s',
    '%hm_s_hm',
    '%hm_s_r',
    '%hm_s_s',
    '%hm_sign',
    '%hm_sin',
    '%hm_size',
    '%hm_sqrt',
    '%hm_stdev',
    '%hm_string',
    '%hm_sum',
    '%hm_x_hm',
    '%hm_x_p',
    '%hm_x_s',
    '%hm_zeros',
    '%i_1_s',
    '%i_2_s',
    '%i_3_s',
    '%i_4_s',
    '%i_Matplot',
    '%i_a_i',
    '%i_a_s',
    '%i_and',
    '%i_ascii',
    '%i_b_s',
    '%i_bezout',
    '%i_champ',
    '%i_champ1',
    '%i_contour',
    '%i_contour2d',
    '%i_d_i',
    '%i_d_s',
    '%i_dsearch',
    '%i_e',
    '%i_fft',
    '%i_g_i',
    '%i_gcd',
    '%i_grand',
    '%i_h_i',
    '%i_i_ce',
    '%i_i_h',
    '%i_i_hm',
    '%i_i_i',
    '%i_i_s',
    '%i_i_st',
    '%i_j_i',
    '%i_j_s',
    '%i_l_s',
    '%i_lcm',
    '%i_length',
    '%i_m_i',
    '%i_m_s',
    '%i_mfprintf',
    '%i_mprintf',
    '%i_msprintf',
    '%i_n_s',
    '%i_o_s',
    '%i_or',
    '%i_p_i',
    '%i_p_s',
    '%i_plot2d',
    '%i_plot2d1',
    '%i_plot2d2',
    '%i_q_s',
    '%i_r_i',
    '%i_r_s',
    '%i_round',
    '%i_s_i',
    '%i_s_s',
    '%i_sign',
    '%i_string',
    '%i_x_i',
    '%i_x_s',
    '%ip_a_s',
    '%ip_i_st',
    '%ip_m_s',
    '%ip_n_ip',
    '%ip_o_ip',
    '%ip_p',
    '%ip_part',
    '%ip_s_s',
    '%ip_string',
    '%k',
    '%l_i_h',
    '%l_i_s',
    '%l_i_st',
    '%l_isequal',
    '%l_n_c',
    '%l_n_l',
    '%l_n_m',
    '%l_n_p',
    '%l_n_s',
    '%l_n_st',
    '%l_o_c',
    '%l_o_l',
    '%l_o_m',
    '%l_o_p',
    '%l_o_s',
    '%l_o_st',
    '%lss_a_lss',
    '%lss_a_p',
    '%lss_a_r',
    '%lss_a_s',
    '%lss_c_lss',
    '%lss_c_p',
    '%lss_c_r',
    '%lss_c_s',
    '%lss_e',
    '%lss_eye',
    '%lss_f_lss',
    '%lss_f_p',
    '%lss_f_r',
    '%lss_f_s',
    '%lss_i_ce',
    '%lss_i_lss',
    '%lss_i_p',
    '%lss_i_r',
    '%lss_i_s',
    '%lss_i_st',
    '%lss_inv',
    '%lss_l_lss',
    '%lss_l_p',
    '%lss_l_r',
    '%lss_l_s',
    '%lss_m_lss',
    '%lss_m_p',
    '%lss_m_r',
    '%lss_m_s',
    '%lss_n_lss',
    '%lss_n_p',
    '%lss_n_r',
    '%lss_n_s',
    '%lss_norm',
    '%lss_o_lss',
    '%lss_o_p',
    '%lss_o_r',
    '%lss_o_s',
    '%lss_ones',
    '%lss_r_lss',
    '%lss_r_p',
    '%lss_r_r',
    '%lss_r_s',
    '%lss_rand',
    '%lss_s',
    '%lss_s_lss',
    '%lss_s_p',
    '%lss_s_r',
    '%lss_s_s',
    '%lss_size',
    '%lss_t',
    '%lss_v_lss',
    '%lss_v_p',
    '%lss_v_r',
    '%lss_v_s',
    '%lt_i_s',
    '%m_n_l',
    '%m_o_l',
    '%mc_i_h',
    '%mc_i_s',
    '%mc_i_st',
    '%mc_n_st',
    '%mc_o_st',
    '%mc_string',
    '%mps_p',
    '%mps_string',
    '%msp_a_s',
    '%msp_abs',
    '%msp_e',
    '%msp_find',
    '%msp_i_s',
    '%msp_i_st',
    '%msp_length',
    '%msp_m_s',
    '%msp_maxi',
    '%msp_n_msp',
    '%msp_nnz',
    '%msp_o_msp',
    '%msp_p',
    '%msp_sparse',
    '%msp_spones',
    '%msp_t',
    '%p_a_lss',
    '%p_a_r',
    '%p_c_lss',
    '%p_c_r',
    '%p_cumprod',
    '%p_cumsum',
    '%p_d_p',
    '%p_d_r',
    '%p_d_s',
    '%p_det',
    '%p_e',
    '%p_f_lss',
    '%p_f_r',
    '%p_grand',
    '%p_i_ce',
    '%p_i_h',
    '%p_i_hm',
    '%p_i_lss',
    '%p_i_p',
    '%p_i_r',
    '%p_i_s',
    '%p_i_st',
    '%p_inv',
    '%p_j_s',
    '%p_k_p',
    '%p_k_r',
    '%p_k_s',
    '%p_l_lss',
    '%p_l_p',
    '%p_l_r',
    '%p_l_s',
    '%p_m_hm',
    '%p_m_lss',
    '%p_m_r',
    '%p_matrix',
    '%p_n_l',
    '%p_n_lss',
    '%p_n_r',
    '%p_o_l',
    '%p_o_lss',
    '%p_o_r',
    '%p_o_sp',
    '%p_p_s',
    '%p_part',
    '%p_prod',
    '%p_q_p',
    '%p_q_r',
    '%p_q_s',
    '%p_r_lss',
    '%p_r_p',
    '%p_r_r',
    '%p_r_s',
    '%p_s_lss',
    '%p_s_r',
    '%p_simp',
    '%p_string',
    '%p_sum',
    '%p_v_lss',
    '%p_v_p',
    '%p_v_r',
    '%p_v_s',
    '%p_x_hm',
    '%p_x_r',
    '%p_y_p',
    '%p_y_r',
    '%p_y_s',
    '%p_z_p',
    '%p_z_r',
    '%p_z_s',
    '%pcg',
    '%plist_p',
    '%plist_string',
    '%r_0',
    '%r_a_hm',
    '%r_a_lss',
    '%r_a_p',
    '%r_a_r',
    '%r_a_s',
    '%r_c_lss',
    '%r_c_p',
    '%r_c_r',
    '%r_c_s',
    '%r_clean',
    '%r_cumprod',
    '%r_cumsum',
    '%r_d_p',
    '%r_d_r',
    '%r_d_s',
    '%r_det',
    '%r_diag',
    '%r_e',
    '%r_eye',
    '%r_f_lss',
    '%r_f_p',
    '%r_f_r',
    '%r_f_s',
    '%r_i_ce',
    '%r_i_hm',
    '%r_i_lss',
    '%r_i_p',
    '%r_i_r',
    '%r_i_s',
    '%r_i_st',
    '%r_inv',
    '%r_j_s',
    '%r_k_p',
    '%r_k_r',
    '%r_k_s',
    '%r_l_lss',
    '%r_l_p',
    '%r_l_r',
    '%r_l_s',
    '%r_m_hm',
    '%r_m_lss',
    '%r_m_p',
    '%r_m_r',
    '%r_m_s',
    '%r_matrix',
    '%r_n_lss',
    '%r_n_p',
    '%r_n_r',
    '%r_n_s',
    '%r_norm',
    '%r_o_lss',
    '%r_o_p',
    '%r_o_r',
    '%r_o_s',
    '%r_ones',
    '%r_p',
    '%r_p_s',
    '%r_prod',
    '%r_q_p',
    '%r_q_r',
    '%r_q_s',
    '%r_r_lss',
    '%r_r_p',
    '%r_r_r',
    '%r_r_s',
    '%r_rand',
    '%r_s',
    '%r_s_hm',
    '%r_s_lss',
    '%r_s_p',
    '%r_s_r',
    '%r_s_s',
    '%r_simp',
    '%r_size',
    '%r_string',
    '%r_sum',
    '%r_t',
    '%r_tril',
    '%r_triu',
    '%r_v_lss',
    '%r_v_p',
    '%r_v_r',
    '%r_v_s',
    '%r_varn',
    '%r_x_p',
    '%r_x_r',
    '%r_x_s',
    '%r_y_p',
    '%r_y_r',
    '%r_y_s',
    '%r_z_p',
    '%r_z_r',
    '%r_z_s',
    '%s_1_hm',
    '%s_1_i',
    '%s_2_hm',
    '%s_2_i',
    '%s_3_hm',
    '%s_3_i',
    '%s_4_hm',
    '%s_4_i',
    '%s_5',
    '%s_a_b',
    '%s_a_hm',
    '%s_a_i',
    '%s_a_ip',
    '%s_a_lss',
    '%s_a_msp',
    '%s_a_r',
    '%s_a_sp',
    '%s_and',
    '%s_b_i',
    '%s_b_s',
    '%s_bezout',
    '%s_c_b',
    '%s_c_cblock',
    '%s_c_lss',
    '%s_c_r',
    '%s_c_sp',
    '%s_d_b',
    '%s_d_i',
    '%s_d_p',
    '%s_d_r',
    '%s_d_sp',
    '%s_e',
    '%s_f_b',
    '%s_f_cblock',
    '%s_f_lss',
    '%s_f_r',
    '%s_f_sp',
    '%s_g_b',
    '%s_g_s',
    '%s_gcd',
    '%s_grand',
    '%s_h_b',
    '%s_h_s',
    '%s_i_b',
    '%s_i_c',
    '%s_i_ce',
    '%s_i_h',
    '%s_i_hm',
    '%s_i_i',
    '%s_i_lss',
    '%s_i_p',
    '%s_i_r',
    '%s_i_s',
    '%s_i_sp',
    '%s_i_spb',
    '%s_i_st',
    '%s_j_i',
    '%s_k_hm',
    '%s_k_p',
    '%s_k_r',
    '%s_k_sp',
    '%s_l_b',
    '%s_l_hm',
    '%s_l_i',
    '%s_l_lss',
    '%s_l_p',
    '%s_l_r',
    '%s_l_s',
    '%s_l_sp',
    '%s_lcm',
    '%s_m_b',
    '%s_m_hm',
    '%s_m_i',
    '%s_m_ip',
    '%s_m_lss',
    '%s_m_msp',
    '%s_m_r',
    '%s_matrix',
    '%s_n_hm',
    '%s_n_i',
    '%s_n_l',
    '%s_n_lss',
    '%s_n_r',
    '%s_n_st',
    '%s_o_hm',
    '%s_o_i',
    '%s_o_l',
    '%s_o_lss',
    '%s_o_r',
    '%s_o_st',
    '%s_or',
    '%s_p_b',
    '%s_p_i',
    '%s_pow',
    '%s_q_hm',
    '%s_q_i',
    '%s_q_p',
    '%s_q_r',
    '%s_q_sp',
    '%s_r_b',
    '%s_r_i',
    '%s_r_lss',
    '%s_r_p',
    '%s_r_r',
    '%s_r_s',
    '%s_r_sp',
    '%s_s_b',
    '%s_s_hm',
    '%s_s_i',
    '%s_s_ip',
    '%s_s_lss',
    '%s_s_r',
    '%s_s_sp',
    '%s_simp',
    '%s_v_lss',
    '%s_v_p',
    '%s_v_r',
    '%s_v_s',
    '%s_x_b',
    '%s_x_hm',
    '%s_x_i',
    '%s_x_r',
    '%s_y_p',
    '%s_y_r',
    '%s_y_sp',
    '%s_z_p',
    '%s_z_r',
    '%s_z_sp',
    '%sn',
    '%sp_a_s',
    '%sp_a_sp',
    '%sp_and',
    '%sp_c_s',
    '%sp_ceil',
    '%sp_conj',
    '%sp_cos',
    '%sp_cumprod',
    '%sp_cumsum',
    '%sp_d_s',
    '%sp_d_sp',
    '%sp_det',
    '%sp_diag',
    '%sp_e',
    '%sp_exp',
    '%sp_f_s',
    '%sp_floor',
    '%sp_grand',
    '%sp_gsort',
    '%sp_i_ce',
    '%sp_i_h',
    '%sp_i_s',
    '%sp_i_sp',
    '%sp_i_st',
    '%sp_int',
    '%sp_inv',
    '%sp_k_s',
    '%sp_k_sp',
    '%sp_l_s',
    '%sp_l_sp',
    '%sp_length',
    '%sp_max',
    '%sp_min',
    '%sp_norm',
    '%sp_or',
    '%sp_p_s',
    '%sp_prod',
    '%sp_q_s',
    '%sp_q_sp',
    '%sp_r_s',
    '%sp_r_sp',
    '%sp_round',
    '%sp_s_s',
    '%sp_s_sp',
    '%sp_sin',
    '%sp_sqrt',
    '%sp_string',
    '%sp_sum',
    '%sp_tril',
    '%sp_triu',
    '%sp_y_s',
    '%sp_y_sp',
    '%sp_z_s',
    '%sp_z_sp',
    '%spb_and',
    '%spb_c_b',
    '%spb_cumprod',
    '%spb_cumsum',
    '%spb_diag',
    '%spb_e',
    '%spb_f_b',
    '%spb_g_b',
    '%spb_g_spb',
    '%spb_h_b',
    '%spb_h_spb',
    '%spb_i_b',
    '%spb_i_ce',
    '%spb_i_h',
    '%spb_i_st',
    '%spb_or',
    '%spb_prod',
    '%spb_sum',
    '%spb_tril',
    '%spb_triu',
    '%st_6',
    '%st_c_st',
    '%st_e',
    '%st_f_st',
    '%st_i_b',
    '%st_i_c',
    '%st_i_fptr',
    '%st_i_h',
    '%st_i_i',
    '%st_i_ip',
    '%st_i_lss',
    '%st_i_msp',
    '%st_i_p',
    '%st_i_r',
    '%st_i_s',
    '%st_i_sp',
    '%st_i_spb',
    '%st_i_st',
    '%st_matrix',
    '%st_n_c',
    '%st_n_l',
    '%st_n_mc',
    '%st_n_p',
    '%st_n_s',
    '%st_o_c',
    '%st_o_l',
    '%st_o_mc',
    '%st_o_p',
    '%st_o_s',
    '%st_o_tl',
    '%st_p',
    '%st_size',
    '%st_string',
    '%st_t',
    '%ticks_i_h',
    '%xls_e',
    '%xls_p',
    '%xlssheet_e',
    '%xlssheet_p',
    '%xlssheet_size',
    '%xlssheet_string',
    'DominationRank',
    'G_make',
    'IsAScalar',
    'NDcost',
    'OS_Version',
    'PlotSparse',
    'ReadHBSparse',
    'TCL_CreateSlave',
    'abcd',
    'abinv',
    'accept_func_default',
    'accept_func_vfsa',
    'acf',
    'acosd',
    'acosh',
    'acoshm',
    'acosm',
    'acot',
    'acotd',
    'acoth',
    'acsc',
    'acscd',
    'acsch',
    'add_demo',
    'add_help_chapter',
    'add_module_help_chapter',
    'add_param',
    'add_profiling',
    'adj2sp',
    'aff2ab',
    'ana_style',
    'analpf',
    'analyze',
    'aplat',
    'arhnk',
    'arl2',
    'arma2p',
    'arma2ss',
    'armac',
    'armax',
    'armax1',
    'arobasestring2strings',
    'arsimul',
    'ascii2string',
    'asciimat',
    'asec',
    'asecd',
    'asech',
    'asind',
    'asinh',
    'asinhm',
    'asinm',
    'assert_checkalmostequal',
    'assert_checkequal',
    'assert_checkerror',
    'assert_checkfalse',
    'assert_checkfilesequal',
    'assert_checktrue',
    'assert_comparecomplex',
    'assert_computedigits',
    'assert_cond2reltol',
    'assert_cond2reqdigits',
    'assert_generror',
    'atand',
    'atanh',
    'atanhm',
    'atanm',
    'atomsAutoload',
    'atomsAutoloadAdd',
    'atomsAutoloadDel',
    'atomsAutoloadList',
    'atomsCategoryList',
    'atomsCheckModule',
    'atomsDepTreeShow',
    'atomsGetConfig',
    'atomsGetInstalled',
    'atomsGetInstalledPath',
    'atomsGetLoaded',
    'atomsGetLoadedPath',
    'atomsInstall',
    'atomsIsInstalled',
    'atomsIsLoaded',
    'atomsList',
    'atomsLoad',
    'atomsQuit',
    'atomsRemove',
    'atomsRepositoryAdd',
    'atomsRepositoryDel',
    'atomsRepositoryList',
    'atomsRestoreConfig',
    'atomsSaveConfig',
    'atomsSearch',
    'atomsSetConfig',
    'atomsShow',
    'atomsSystemInit',
    'atomsSystemUpdate',
    'atomsTest',
    'atomsUpdate',
    'atomsVersion',
    'augment',
    'auread',
    'auwrite',
    'balreal',
    'bench_run',
    'bilin',
    'bilt',
    'bin2dec',
    'binomial',
    'bitand',
    'bitcmp',
    'bitget',
    'bitor',
    'bitset',
    'bitxor',
    'black',
    'blanks',
    'bloc2exp',
    'bloc2ss',
    'block_parameter_error',
    'bode',
    'bode_asymp',
    'bstap',
    'buttmag',
    'bvodeS',
    'bytecode',
    'bytecodewalk',
    'cainv',
    'calendar',
    'calerf',
    'calfrq',
    'canon',
    'casc',
    'cat',
    'cat_code',
    'cb_m2sci_gui',
    'ccontrg',
    'cell',
    'cell2mat',
    'cellstr',
    'center',
    'cepstrum',
    'cfspec',
    'char',
    'chart',
    'cheb1mag',
    'cheb2mag',
    'check_gateways',
    'check_modules_xml',
    'check_versions',
    'chepol',
    'chfact',
    'chsolve',
    'classmarkov',
    'clean_help',
    'clock',
    'cls2dls',
    'cmb_lin',
    'cmndred',
    'cmoment',
    'coding_ga_binary',
    'coding_ga_identity',
    'coff',
    'coffg',
    'colcomp',
    'colcompr',
    'colinout',
    'colregul',
    'companion',
    'complex',
    'compute_initial_temp',
    'cond',
    'cond2sp',
    'condestsp',
    'configure_msifort',
    'configure_msvc',
    'conjgrad',
    'cont_frm',
    'cont_mat',
    'contrss',
    'conv',
    'convert_to_float',
    'convertindex',
    'convol',
    'convol2d',
    'copfac',
    'correl',
    'cosd',
    'cosh',
    'coshm',
    'cosm',
    'cotd',
    'cotg',
    'coth',
    'cothm',
    'cov',
    'covar',
    'createXConfiguration',
    'createfun',
    'createstruct',
    'cross',
    'crossover_ga_binary',
    'crossover_ga_default',
    'csc',
    'cscd',
    'csch',
    'csgn',
    'csim',
    'cspect',
    'ctr_gram',
    'czt',
    'dae',
    'daeoptions',
    'damp',
    'datafit',
    'date',
    'datenum',
    'datevec',
    'dbphi',
    'dcf',
    'ddp',
    'dec2bin',
    'dec2hex',
    'dec2oct',
    'del_help_chapter',
    'del_module_help_chapter',
    'demo_begin',
    'demo_choose',
    'demo_compiler',
    'demo_end',
    'demo_file_choice',
    'demo_folder_choice',
    'demo_function_choice',
    'demo_gui',
    'demo_run',
    'demo_viewCode',
    'denom',
    'derivat',
    'derivative',
    'des2ss',
    'des2tf',
    'detectmsifort64tools',
    'detectmsvc64tools',
    'determ',
    'detr',
    'detrend',
    'devtools_run_builder',
    'dhnorm',
    'diff',
    'diophant',
    'dir',
    'dirname',
    'dispfiles',
    'dllinfo',
    'dscr',
    'dsimul',
    'dt_ility',
    'dtsi',
    'edit',
    'edit_error',
    'editor',
    'eigenmarkov',
    'eigs',
    'ell1mag',
    'enlarge_shape',
    'entropy',
    'eomday',
    'epred',
    'eqfir',
    'eqiir',
    'equil',
    'equil1',
    'erfinv',
    'etime',
    'eval',
    'evans',
    'evstr',
    'example_run',
    'expression2code',
    'extract_help_examples',
    'factor',
    'factorial',
    'factors',
    'faurre',
    'ffilt',
    'fft2',
    'fftshift',
    'fieldnames',
    'filt_sinc',
    'filter',
    'findABCD',
    'findAC',
    'findBDK',
    'findR',
    'find_freq',
    'find_links',
    'find_scicos_version',
    'findm',
    'findmsifortcompiler',
    'findmsvccompiler',
    'findx0BD',
    'firstnonsingleton',
    'fix',
    'fixedpointgcd',
    'flipdim',
    'flts',
    'fminsearch',
    'formatBlackTip',
    'formatBodeMagTip',
    'formatBodePhaseTip',
    'formatGainplotTip',
    'formatHallModuleTip',
    'formatHallPhaseTip',
    'formatNicholsGainTip',
    'formatNicholsPhaseTip',
    'formatNyquistTip',
    'formatPhaseplotTip',
    'formatSgridDampingTip',
    'formatSgridFreqTip',
    'formatZgridDampingTip',
    'formatZgridFreqTip',
    'format_txt',
    'fourplan',
    'frep2tf',
    'freson',
    'frfit',
    'frmag',
    'fseek_origin',
    'fsfirlin',
    'fspec',
    'fspecg',
    'fstabst',
    'ftest',
    'ftuneq',
    'fullfile',
    'fullrf',
    'fullrfk',
    'fun2string',
    'g_margin',
    'gainplot',
    'gamitg',
    'gcare',
    'gcd',
    'gencompilationflags_unix',
    'generateBlockImage',
    'generateBlockImages',
    'generic_i_ce',
    'generic_i_h',
    'generic_i_hm',
    'generic_i_s',
    'generic_i_st',
    'genlib',
    'genmarkov',
    'geomean',
    'getDiagramVersion',
    'getModelicaPath',
    'getPreferencesValue',
    'get_file_path',
    'get_function_path',
    'get_param',
    'get_profile',
    'get_scicos_version',
    'getd',
    'getscilabkeywords',
    'getshell',
    'gettklib',
    'gfare',
    'gfrancis',
    'givens',
    'glever',
    'gmres',
    'group',
    'gschur',
    'gspec',
    'gtild',
    'h2norm',
    'h_cl',
    'h_inf',
    'h_inf_st',
    'h_norm',
    'hallchart',
    'halt',
    'hank',
    'hankelsv',
    'harmean',
    'haveacompiler',
    'head_comments',
    'help_from_sci',
    'help_skeleton',
    'hermit',
    'hex2dec',
    'hilb',
    'hilbert',
    'histc',
    'horner',
    'householder',
    'hrmt',
    'htrianr',
    'hypermat',
    'idct',
    'idst',
    'ifft',
    'ifftshift',
    'iir',
    'iirgroup',
    'iirlp',
    'iirmod',
    'ilib_build',
    'ilib_build_jar',
    'ilib_compile',
    'ilib_for_link',
    'ilib_gen_Make',
    'ilib_gen_Make_unix',
    'ilib_gen_cleaner',
    'ilib_gen_gateway',
    'ilib_gen_loader',
    'ilib_include_flag',
    'ilib_mex_build',
    'im_inv',
    'importScicosDiagram',
    'importScicosPal',
    'importXcosDiagram',
    'imrep2ss',
    'ind2sub',
    'inistate',
    'init_ga_default',
    'init_param',
    'initial_scicos_tables',
    'input',
    'instruction2code',
    'intc',
    'intdec',
    'integrate',
    'interp1',
    'interpln',
    'intersect',
    'intl',
    'intsplin',
    'inttrap',
    'inv_coeff',
    'invr',
    'invrs',
    'invsyslin',
    'iqr',
    'isLeapYear',
    'is_absolute_path',
    'is_param',
    'iscell',
    'iscellstr',
    'iscolumn',
    'isempty',
    'isfield',
    'isinf',
    'ismatrix',
    'isnan',
    'isrow',
    'isscalar',
    'issparse',
    'issquare',
    'isstruct',
    'isvector',
    'jmat',
    'justify',
    'kalm',
    'karmarkar',
    'kernel',
    'kpure',
    'krac2',
    'kroneck',
    'lattn',
    'lattp',
    'launchtest',
    'lcf',
    'lcm',
    'lcmdiag',
    'leastsq',
    'leqe',
    'leqr',
    'lev',
    'levin',
    'lex_sort',
    'lft',
    'lin',
    'lin2mu',
    'lincos',
    'lindquist',
    'linf',
    'linfn',
    'linsolve',
    'linspace',
    'list2vec',
    'list_param',
    'listfiles',
    'listfunctions',
    'listvarinfile',
    'lmisolver',
    'lmitool',
    'loadXcosLibs',
    'loadmatfile',
    'loadwave',
    'log10',
    'log2',
    'logm',
    'logspace',
    'lqe',
    'lqg',
    'lqg2stan',
    'lqg_ltr',
    'lqr',
    'ls',
    'lyap',
    'm2sci_gui',
    'm_circle',
    'macglov',
    'macrovar',
    'mad',
    'makecell',
    'manedit',
    'mapsound',
    'markp2ss',
    'matfile2sci',
    'mdelete',
    'mean',
    'meanf',
    'median',
    'members',
    'mese',
    'meshgrid',
    'mfft',
    'mfile2sci',
    'minreal',
    'minss',
    'mkdir',
    'modulo',
    'moment',
    'mrfit',
    'msd',
    'mstr2sci',
    'mtlb',
    'mtlb_0',
    'mtlb_a',
    'mtlb_all',
    'mtlb_any',
    'mtlb_axes',
    'mtlb_axis',
    'mtlb_beta',
    'mtlb_box',
    'mtlb_choices',
    'mtlb_close',
    'mtlb_colordef',
    'mtlb_cond',
    'mtlb_cov',
    'mtlb_cumprod',
    'mtlb_cumsum',
    'mtlb_dec2hex',
    'mtlb_delete',
    'mtlb_diag',
    'mtlb_diff',
    'mtlb_dir',
    'mtlb_double',
    'mtlb_e',
    'mtlb_echo',
    'mtlb_error',
    'mtlb_eval',
    'mtlb_exist',
    'mtlb_eye',
    'mtlb_false',
    'mtlb_fft',
    'mtlb_fftshift',
    'mtlb_filter',
    'mtlb_find',
    'mtlb_findstr',
    'mtlb_fliplr',
    'mtlb_fopen',
    'mtlb_format',
    'mtlb_fprintf',
    'mtlb_fread',
    'mtlb_fscanf',
    'mtlb_full',
    'mtlb_fwrite',
    'mtlb_get',
    'mtlb_grid',
    'mtlb_hold',
    'mtlb_i',
    'mtlb_ifft',
    'mtlb_image',
    'mtlb_imp',
    'mtlb_int16',
    'mtlb_int32',
    'mtlb_int8',
    'mtlb_is',
    'mtlb_isa',
    'mtlb_isfield',
    'mtlb_isletter',
    'mtlb_isspace',
    'mtlb_l',
    'mtlb_legendre',
    'mtlb_linspace',
    'mtlb_logic',
    'mtlb_logical',
    'mtlb_loglog',
    'mtlb_lower',
    'mtlb_max',
    'mtlb_mean',
    'mtlb_median',
    'mtlb_mesh',
    'mtlb_meshdom',
    'mtlb_min',
    'mtlb_more',
    'mtlb_num2str',
    'mtlb_ones',
    'mtlb_pcolor',
    'mtlb_plot',
    'mtlb_prod',
    'mtlb_qr',
    'mtlb_qz',
    'mtlb_rand',
    'mtlb_randn',
    'mtlb_rcond',
    'mtlb_realmax',
    'mtlb_realmin',
    'mtlb_s',
    'mtlb_semilogx',
    'mtlb_semilogy',
    'mtlb_setstr',
    'mtlb_size',
    'mtlb_sort',
    'mtlb_sortrows',
    'mtlb_sprintf',
    'mtlb_sscanf',
    'mtlb_std',
    'mtlb_strcmp',
    'mtlb_strcmpi',
    'mtlb_strfind',
    'mtlb_strrep',
    'mtlb_subplot',
    'mtlb_sum',
    'mtlb_t',
    'mtlb_toeplitz',
    'mtlb_tril',
    'mtlb_triu',
    'mtlb_true',
    'mtlb_type',
    'mtlb_uint16',
    'mtlb_uint32',
    'mtlb_uint8',
    'mtlb_upper',
    'mtlb_var',
    'mtlb_zeros',
    'mu2lin',
    'mutation_ga_binary',
    'mutation_ga_default',
    'mvcorrel',
    'mvvacov',
    'nancumsum',
    'nand2mean',
    'nanmax',
    'nanmean',
    'nanmeanf',
    'nanmedian',
    'nanmin',
    'nanreglin',
    'nanstdev',
    'nansum',
    'narsimul',
    'ndgrid',
    'ndims',
    'nehari',
    'neigh_func_csa',
    'neigh_func_default',
    'neigh_func_fsa',
    'neigh_func_vfsa',
    'neldermead_cget',
    'neldermead_configure',
    'neldermead_costf',
    'neldermead_defaultoutput',
    'neldermead_destroy',
    'neldermead_function',
    'neldermead_get',
    'neldermead_log',
    'neldermead_new',
    'neldermead_restart',
    'neldermead_search',
    'neldermead_updatesimp',
    'nextpow2',
    'nfreq',
    'nicholschart',
    'nlev',
    'nmplot_cget',
    'nmplot_configure',
    'nmplot_contour',
    'nmplot_destroy',
    'nmplot_function',
    'nmplot_get',
    'nmplot_historyplot',
    'nmplot_log',
    'nmplot_new',
    'nmplot_outputcmd',
    'nmplot_restart',
    'nmplot_search',
    'nmplot_simplexhistory',
    'noisegen',
    'nonreg_test_run',
    'now',
    'nthroot',
    'null',
    'num2cell',
    'numderivative',
    'numdiff',
    'numer',
    'nyquist',
    'nyquistfrequencybounds',
    'obs_gram',
    'obscont',
    'observer',
    'obsv_mat',
    'obsvss',
    'oct2dec',
    'odeoptions',
    'optim_ga',
    'optim_moga',
    'optim_nsga',
    'optim_nsga2',
    'optim_sa',
    'optimbase_cget',
    'optimbase_checkbounds',
    'optimbase_checkcostfun',
    'optimbase_checkx0',
    'optimbase_configure',
    'optimbase_destroy',
    'optimbase_function',
    'optimbase_get',
    'optimbase_hasbounds',
    'optimbase_hasconstraints',
    'optimbase_hasnlcons',
    'optimbase_histget',
    'optimbase_histset',
    'optimbase_incriter',
    'optimbase_isfeasible',
    'optimbase_isinbounds',
    'optimbase_isinnonlincons',
    'optimbase_log',
    'optimbase_logshutdown',
    'optimbase_logstartup',
    'optimbase_new',
    'optimbase_outputcmd',
    'optimbase_outstruct',
    'optimbase_proj2bnds',
    'optimbase_set',
    'optimbase_stoplog',
    'optimbase_terminate',
    'optimget',
    'optimplotfunccount',
    'optimplotfval',
    'optimplotx',
    'optimset',
    'optimsimplex_center',
    'optimsimplex_check',
    'optimsimplex_compsomefv',
    'optimsimplex_computefv',
    'optimsimplex_deltafv',
    'optimsimplex_deltafvmax',
    'optimsimplex_destroy',
    'optimsimplex_dirmat',
    'optimsimplex_fvmean',
    'optimsimplex_fvstdev',
    'optimsimplex_fvvariance',
    'optimsimplex_getall',
    'optimsimplex_getallfv',
    'optimsimplex_getallx',
    'optimsimplex_getfv',
    'optimsimplex_getn',
    'optimsimplex_getnbve',
    'optimsimplex_getve',
    'optimsimplex_getx',
    'optimsimplex_gradientfv',
    'optimsimplex_log',
    'optimsimplex_new',
    'optimsimplex_reflect',
    'optimsimplex_setall',
    'optimsimplex_setallfv',
    'optimsimplex_setallx',
    'optimsimplex_setfv',
    'optimsimplex_setn',
    'optimsimplex_setnbve',
    'optimsimplex_setve',
    'optimsimplex_setx',
    'optimsimplex_shrink',
    'optimsimplex_size',
    'optimsimplex_sort',
    'optimsimplex_xbar',
    'orth',
    'output_ga_default',
    'output_moga_default',
    'output_nsga2_default',
    'output_nsga_default',
    'p_margin',
    'pack',
    'pareto_filter',
    'parrot',
    'pbig',
    'pca',
    'pcg',
    'pdiv',
    'pen2ea',
    'pencan',
    'pencost',
    'penlaur',
    'perctl',
    'perl',
    'perms',
    'permute',
    'pertrans',
    'pfactors',
    'pfss',
    'phasemag',
    'phaseplot',
    'phc',
    'pinv',
    'playsnd',
    'plotprofile',
    'plzr',
    'pmodulo',
    'pol2des',
    'pol2str',
    'polar',
    'polfact',
    'prbs_a',
    'prettyprint',
    'primes',
    'princomp',
    'profile',
    'proj',
    'projsl',
    'projspec',
    'psmall',
    'pspect',
    'qmr',
    'qpsolve',
    'quart',
    'quaskro',
    'rafiter',
    'randpencil',
    'range',
    'rank',
    'readxls',
    'recompilefunction',
    'recons',
    'reglin',
    'regress',
    'remezb',
    'remove_param',
    'remove_profiling',
    'repfreq',
    'replace_Ix_by_Fx',
    'repmat',
    'reset_profiling',
    'resize_matrix',
    'returntoscilab',
    'rhs2code',
    'ric_desc',
    'riccati',
    'rmdir',
    'routh_t',
    'rowcomp',
    'rowcompr',
    'rowinout',
    'rowregul',
    'rowshuff',
    'rref',
    'sample',
    'samplef',
    'samwr',
    'savematfile',
    'savewave',
    'scanf',
    'sci2exp',
    'sciGUI_init',
    'sci_sparse',
    'scicos_getvalue',
    'scicos_simulate',
    'scicos_workspace_init',
    'scisptdemo',
    'scitest',
    'sdiff',
    'sec',
    'secd',
    'sech',
    'selection_ga_elitist',
    'selection_ga_random',
    'sensi',
    'setPreferencesValue',
    'set_param',
    'setdiff',
    'sgrid',
    'show_margins',
    'show_pca',
    'showprofile',
    'signm',
    'sinc',
    'sincd',
    'sind',
    'sinh',
    'sinhm',
    'sinm',
    'sm2des',
    'sm2ss',
    'smga',
    'smooth',
    'solve',
    'sound',
    'soundsec',
    'sp2adj',
    'spaninter',
    'spanplus',
    'spantwo',
    'specfact',
    'speye',
    'sprand',
    'spzeros',
    'sqroot',
    'sqrtm',
    'squarewave',
    'squeeze',
    'srfaur',
    'srkf',
    'ss2des',
    'ss2ss',
    'ss2tf',
    'sskf',
    'ssprint',
    'ssrand',
    'st_deviation',
    'st_i_generic',
    'st_ility',
    'stabil',
    'statgain',
    'stdev',
    'stdevf',
    'steadycos',
    'strange',
    'strcmpi',
    'struct',
    'sub2ind',
    'sva',
    'svplot',
    'sylm',
    'sylv',
    'sysconv',
    'sysdiag',
    'sysfact',
    'syslin',
    'syssize',
    'system',
    'systmat',
    'tabul',
    'tand',
    'tanh',
    'tanhm',
    'tanm',
    'tbx_build_blocks',
    'tbx_build_cleaner',
    'tbx_build_gateway',
    'tbx_build_gateway_clean',
    'tbx_build_gateway_loader',
    'tbx_build_help',
    'tbx_build_help_loader',
    'tbx_build_loader',
    'tbx_build_localization',
    'tbx_build_macros',
    'tbx_build_pal_loader',
    'tbx_build_src',
    'tbx_builder',
    'tbx_builder_gateway',
    'tbx_builder_gateway_lang',
    'tbx_builder_help',
    'tbx_builder_help_lang',
    'tbx_builder_macros',
    'tbx_builder_src',
    'tbx_builder_src_lang',
    'tbx_generate_pofile',
    'temp_law_csa',
    'temp_law_default',
    'temp_law_fsa',
    'temp_law_huang',
    'temp_law_vfsa',
    'test_clean',
    'test_on_columns',
    'test_run',
    'test_run_level',
    'testexamples',
    'tf2des',
    'tf2ss',
    'thrownan',
    'tic',
    'time_id',
    'toc',
    'toeplitz',
    'tokenpos',
    'toolboxes',
    'trace',
    'trans',
    'translatepaths',
    'tree2code',
    'trfmod',
    'trianfml',
    'trimmean',
    'trisolve',
    'trzeros',
    'typeof',
    'ui_observer',
    'union',
    'unique',
    'unit_test_run',
    'unix_g',
    'unix_s',
    'unix_w',
    'unix_x',
    'unobs',
    'unpack',
    'unwrap',
    'variance',
    'variancef',
    'vec2list',
    'vectorfind',
    'ver',
    'warnobsolete',
    'wavread',
    'wavwrite',
    'wcenter',
    'weekday',
    'wfir',
    'wfir_gui',
    'whereami',
    'who_user',
    'whos',
    'wiener',
    'wigner',
    'window',
    'winlist',
    'with_javasci',
    'with_macros_source',
    'with_modelica_compiler',
    'with_tk',
    'xcorr',
    'xcosBlockEval',
    'xcosBlockInterface',
    'xcosCodeGeneration',
    'xcosConfigureModelica',
    'xcosPal',
    'xcosPalAdd',
    'xcosPalAddBlock',
    'xcosPalExport',
    'xcosPalGenerateAllIcons',
    'xcosShowBlockWarning',
    'xcosValidateBlockSet',
    'xcosValidateCompareBlock',
    'xcos_compile',
    'xcos_debug_gui',
    'xcos_run',
    'xcos_simulate',
    'xcov',
    'xmltochm',
    'xmltoformat',
    'xmltohtml',
    'xmltojar',
    'xmltopdf',
    'xmltops',
    'xmltoweb',
    'yulewalk',
    'zeropen',
    'zgrid',
    'zpbutt',
    'zpch1',
    'zpch2',
    'zpell',
)

variables_kw = (
    '$',
    '%F',
    '%T',
    '%e',
    '%eps',
    '%f',
    '%fftw',
    '%gui',
    '%i',
    '%inf',
    '%io',
    '%modalWarning',
    '%nan',
    '%pi',
    '%s',
    '%t',
    '%tk',
    '%toolboxes',
    '%toolboxes_dir',
    '%z',
    'PWD',
    'SCI',
    'SCIHOME',
    'TMPDIR',
    'arnoldilib',
    'assertlib',
    'atomslib',
    'cacsdlib',
    'compatibility_functilib',
    'corelib',
    'data_structureslib',
    'demo_toolslib',
    'development_toolslib',
    'differential_equationlib',
    'dynamic_linklib',
    'elementary_functionslib',
    'enull',
    'evoid',
    'external_objectslib',
    'fd',
    'fileiolib',
    'functionslib',
    'genetic_algorithmslib',
    'helptoolslib',
    'home',
    'integerlib',
    'interpolationlib',
    'iolib',
    'jnull',
    'jvoid',
    'linear_algebralib',
    'm2scilib',
    'matiolib',
    'modules_managerlib',
    'neldermeadlib',
    'optimbaselib',
    'optimizationlib',
    'optimsimplexlib',
    'output_streamlib',
    'overloadinglib',
    'parameterslib',
    'polynomialslib',
    'preferenceslib',
    'randliblib',
    'scicos_autolib',
    'scicos_utilslib',
    'scinoteslib',
    'signal_processinglib',
    'simulated_annealinglib',
    'soundlib',
    'sparselib',
    'special_functionslib',
    'spreadsheetlib',
    'statisticslib',
    'stringlib',
    'tclscilib',
    'timelib',
    'umfpacklib',
    'xcoslib',
)


if __name__ == '__main__':  # pragma: no cover
    import subprocess
    from pygments.util import format_lines, duplicates_removed

    mapping = {'variables': 'builtin'}

    def extract_completion(var_type):
        s = subprocess.Popen(['scilab', '-nwni'], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = s.communicate(f'''\
fd = mopen("/dev/stderr", "wt");
mputl(strcat(completion("", "{var_type}"), "||"), fd);
mclose(fd)\n''')
        if '||' not in output[1]:
            raise Exception(output[0])
        # Invalid DISPLAY causes this to be output:
        text = output[1].strip()
        if text.startswith('Error: unable to open display \n'):
            text = text[len('Error: unable to open display \n'):]
        return text.split('||')

    new_data = {}
    seen = set()  # only keep first type for a given word
    for t in ('functions', 'commands', 'macros', 'variables'):
        new_data[t] = duplicates_removed(extract_completion(t), seen)
        seen.update(set(new_data[t]))


    with open(__file__, encoding='utf-8') as f:
        content = f.read()

    header = content[:content.find('# Autogenerated')]
    footer = content[content.find("if __name__ == '__main__':"):]

    with open(__file__, 'w', encoding='utf-8') as f:
        f.write(header)
        f.write('# Autogenerated\n\n')
        for k, v in sorted(new_data.items()):
            f.write(format_lines(k + '_kw', v) + '\n\n')
        f.write(footer)

# === NexusCore/openenv\Lib\site-packages\openai\resources\beta\threads\runs\runs.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import typing_extensions
from typing import List, Union, Iterable, Optional
from functools import partial
from typing_extensions import Literal, overload

import httpx

from ..... import _legacy_response
from .steps import (
    Steps,
    AsyncSteps,
    StepsWithRawResponse,
    AsyncStepsWithRawResponse,
    StepsWithStreamingResponse,
    AsyncStepsWithStreamingResponse,
)
from ....._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ....._utils import (
    is_given,
    required_args,
    maybe_transform,
    async_maybe_transform,
)
from ....._compat import cached_property
from ....._resource import SyncAPIResource, AsyncAPIResource
from ....._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ....._streaming import Stream, AsyncStream
from .....pagination import SyncCursorPage, AsyncCursorPage
from ....._base_client import AsyncPaginator, make_request_options
from .....lib.streaming import (
    AssistantEventHandler,
    AssistantEventHandlerT,
    AssistantStreamManager,
    AsyncAssistantEventHandler,
    AsyncAssistantEventHandlerT,
    AsyncAssistantStreamManager,
)
from .....types.beta.threads import (
    run_list_params,
    run_create_params,
    run_update_params,
    run_submit_tool_outputs_params,
)
from .....types.beta.threads.run import Run
from .....types.shared.chat_model import ChatModel
from .....types.shared_params.metadata import Metadata
from .....types.shared.reasoning_effort import ReasoningEffort
from .....types.beta.assistant_tool_param import AssistantToolParam
from .....types.beta.assistant_stream_event import AssistantStreamEvent
from .....types.beta.threads.runs.run_step_include import RunStepInclude
from .....types.beta.assistant_tool_choice_option_param import AssistantToolChoiceOptionParam
from .....types.beta.assistant_response_format_option_param import AssistantResponseFormatOptionParam

__all__ = ["Runs", "AsyncRuns"]


class Runs(SyncAPIResource):
    @cached_property
    def steps(self) -> Steps:
        return Steps(self._client)

    @cached_property
    def with_raw_response(self) -> RunsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return RunsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> RunsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return RunsWithStreamingResponse(self)

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def create(
        self,
        thread_id: str,
        *,
        assistant_id: str,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        Create a run.

        Args:
          assistant_id: The ID of the
              [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
              execute this run.

          include: A list of additional fields to include in the response. Currently the only
              supported value is `step_details.tool_calls[*].file_search.results[*].content`
              to fetch the file search result content.

              See the
              [file search tool documentation](https://platform.openai.com/docs/assistants/tools/file-search#customizing-file-search-settings)
              for more information.

          additional_instructions: Appends additional instructions at the end of the instructions for the run. This
              is useful for modifying the behavior on a per-run basis without overriding other
              instructions.

          additional_messages: Adds additional messages to the thread before creating the run.

          instructions: Overrides the
              [instructions](https://platform.openai.com/docs/api-reference/assistants/createAssistant)
              of the assistant. This is useful for modifying the behavior on a per-run basis.

          max_completion_tokens: The maximum number of completion tokens that may be used over the course of the
              run. The run will make a best effort to use only the number of completion tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              completion tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          max_prompt_tokens: The maximum number of prompt tokens that may be used over the course of the run.
              The run will make a best effort to use only the number of prompt tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              prompt tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
              be used to execute this run. If a value is provided here, it will override the
              model associated with the assistant. If not, the model associated with the
              assistant will be used.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tools and instead generates a message. `auto` is the default value
              and means the model can pick between generating a message or calling one or more
              tools. `required` means the model must call one or more tools before responding
              to the user. Specifying a particular tool like `{"type": "file_search"}` or
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

          tools: Override the tools the assistant can use for this run. This is useful for
              modifying the behavior on a per-run basis.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          truncation_strategy: Controls for how a thread will be truncated prior to the run. Use this to
              control the intial context window of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def create(
        self,
        thread_id: str,
        *,
        assistant_id: str,
        stream: Literal[True],
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Stream[AssistantStreamEvent]:
        """
        Create a run.

        Args:
          assistant_id: The ID of the
              [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
              execute this run.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          include: A list of additional fields to include in the response. Currently the only
              supported value is `step_details.tool_calls[*].file_search.results[*].content`
              to fetch the file search result content.

              See the
              [file search tool documentation](https://platform.openai.com/docs/assistants/tools/file-search#customizing-file-search-settings)
              for more information.

          additional_instructions: Appends additional instructions at the end of the instructions for the run. This
              is useful for modifying the behavior on a per-run basis without overriding other
              instructions.

          additional_messages: Adds additional messages to the thread before creating the run.

          instructions: Overrides the
              [instructions](https://platform.openai.com/docs/api-reference/assistants/createAssistant)
              of the assistant. This is useful for modifying the behavior on a per-run basis.

          max_completion_tokens: The maximum number of completion tokens that may be used over the course of the
              run. The run will make a best effort to use only the number of completion tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              completion tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          max_prompt_tokens: The maximum number of prompt tokens that may be used over the course of the run.
              The run will make a best effort to use only the number of prompt tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              prompt tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
              be used to execute this run. If a value is provided here, it will override the
              model associated with the assistant. If not, the model associated with the
              assistant will be used.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tools and instead generates a message. `auto` is the default value
              and means the model can pick between generating a message or calling one or more
              tools. `required` means the model must call one or more tools before responding
              to the user. Specifying a particular tool like `{"type": "file_search"}` or
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

          tools: Override the tools the assistant can use for this run. This is useful for
              modifying the behavior on a per-run basis.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          truncation_strategy: Controls for how a thread will be truncated prior to the run. Use this to
              control the intial context window of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def create(
        self,
        thread_id: str,
        *,
        assistant_id: str,
        stream: bool,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run | Stream[AssistantStreamEvent]:
        """
        Create a run.

        Args:
          assistant_id: The ID of the
              [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
              execute this run.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          include: A list of additional fields to include in the response. Currently the only
              supported value is `step_details.tool_calls[*].file_search.results[*].content`
              to fetch the file search result content.

              See the
              [file search tool documentation](https://platform.openai.com/docs/assistants/tools/file-search#customizing-file-search-settings)
              for more information.

          additional_instructions: Appends additional instructions at the end of the instructions for the run. This
              is useful for modifying the behavior on a per-run basis without overriding other
              instructions.

          additional_messages: Adds additional messages to the thread before creating the run.

          instructions: Overrides the
              [instructions](https://platform.openai.com/docs/api-reference/assistants/createAssistant)
              of the assistant. This is useful for modifying the behavior on a per-run basis.

          max_completion_tokens: The maximum number of completion tokens that may be used over the course of the
              run. The run will make a best effort to use only the number of completion tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              completion tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          max_prompt_tokens: The maximum number of prompt tokens that may be used over the course of the run.
              The run will make a best effort to use only the number of prompt tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              prompt tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
              be used to execute this run. If a value is provided here, it will override the
              model associated with the assistant. If not, the model associated with the
              assistant will be used.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tools and instead generates a message. `auto` is the default value
              and means the model can pick between generating a message or calling one or more
              tools. `required` means the model must call one or more tools before responding
              to the user. Specifying a particular tool like `{"type": "file_search"}` or
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

          tools: Override the tools the assistant can use for this run. This is useful for
              modifying the behavior on a per-run basis.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          truncation_strategy: Controls for how a thread will be truncated prior to the run. Use this to
              control the intial context window of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    @required_args(["assistant_id"], ["assistant_id", "stream"])
    def create(
        self,
        thread_id: str,
        *,
        assistant_id: str,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run | Stream[AssistantStreamEvent]:
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            f"/threads/{thread_id}/runs",
            body=maybe_transform(
                {
                    "assistant_id": assistant_id,
                    "additional_instructions": additional_instructions,
                    "additional_messages": additional_messages,
                    "instructions": instructions,
                    "max_completion_tokens": max_completion_tokens,
                    "max_prompt_tokens": max_prompt_tokens,
                    "metadata": metadata,
                    "model": model,
                    "parallel_tool_calls": parallel_tool_calls,
                    "reasoning_effort": reasoning_effort,
                    "response_format": response_format,
                    "stream": stream,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_p": top_p,
                    "truncation_strategy": truncation_strategy,
                },
                run_create_params.RunCreateParamsStreaming if stream else run_create_params.RunCreateParamsNonStreaming,
            ),
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform({"include": include}, run_create_params.RunCreateParams),
            ),
            cast_to=Run,
            stream=stream or False,
            stream_cls=Stream[AssistantStreamEvent],
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def retrieve(
        self,
        run_id: str,
        *,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        Retrieves a run.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get(
            f"/threads/{thread_id}/runs/{run_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def update(
        self,
        run_id: str,
        *,
        thread_id: str,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        Modifies a run.

        Args:
          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            f"/threads/{thread_id}/runs/{run_id}",
            body=maybe_transform({"metadata": metadata}, run_update_params.RunUpdateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def list(
        self,
        thread_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[Run]:
        """
        Returns a list of runs belonging to a thread.

        Args:
          after: A cursor for use in pagination. `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          before: A cursor for use in pagination. `before` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              starting with obj_foo, your subsequent call can include before=obj_foo in order
              to fetch the previous page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            f"/threads/{thread_id}/runs",
            page=SyncCursorPage[Run],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "limit": limit,
                        "order": order,
                    },
                    run_list_params.RunListParams,
                ),
            ),
            model=Run,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def cancel(
        self,
        run_id: str,
        *,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        Cancels a run that is `in_progress`.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            f"/threads/{thread_id}/runs/{run_id}/cancel",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def create_and_poll(
        self,
        *,
        assistant_id: str,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        A helper to create a run an poll for a terminal state. More information on Run
        lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        run = self.create(  # pyright: ignore[reportDeprecated]
            thread_id=thread_id,
            assistant_id=assistant_id,
            include=include,
            additional_instructions=additional_instructions,
            additional_messages=additional_messages,
            instructions=instructions,
            max_completion_tokens=max_completion_tokens,
            max_prompt_tokens=max_prompt_tokens,
            metadata=metadata,
            model=model,
            response_format=response_format,
            temperature=temperature,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            reasoning_effort=reasoning_effort,
            # We assume we are not streaming when polling
            stream=False,
            tools=tools,
            truncation_strategy=truncation_strategy,
            top_p=top_p,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
        )
        return self.poll(  # pyright: ignore[reportDeprecated]
            run.id,
            thread_id=thread_id,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            poll_interval_ms=poll_interval_ms,
            timeout=timeout,
        )

    @overload
    @typing_extensions.deprecated("use `stream` instead")
    def create_and_stream(
        self,
        *,
        assistant_id: str,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantStreamManager[AssistantEventHandler]:
        """Create a Run stream"""
        ...

    @overload
    @typing_extensions.deprecated("use `stream` instead")
    def create_and_stream(
        self,
        *,
        assistant_id: str,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        thread_id: str,
        event_handler: AssistantEventHandlerT,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantStreamManager[AssistantEventHandlerT]:
        """Create a Run stream"""
        ...

    @typing_extensions.deprecated("use `stream` instead")
    def create_and_stream(
        self,
        *,
        assistant_id: str,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        thread_id: str,
        event_handler: AssistantEventHandlerT | None = None,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantStreamManager[AssistantEventHandler] | AssistantStreamManager[AssistantEventHandlerT]:
        """Create a Run stream"""
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")

        extra_headers = {
            "OpenAI-Beta": "assistants=v2",
            "X-Stainless-Stream-Helper": "threads.runs.create_and_stream",
            "X-Stainless-Custom-Event-Handler": "true" if event_handler else "false",
            **(extra_headers or {}),
        }
        make_request = partial(
            self._post,
            f"/threads/{thread_id}/runs",
            body=maybe_transform(
                {
                    "assistant_id": assistant_id,
                    "additional_instructions": additional_instructions,
                    "additional_messages": additional_messages,
                    "instructions": instructions,
                    "max_completion_tokens": max_completion_tokens,
                    "max_prompt_tokens": max_prompt_tokens,
                    "metadata": metadata,
                    "model": model,
                    "response_format": response_format,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "stream": True,
                    "tools": tools,
                    "truncation_strategy": truncation_strategy,
                    "parallel_tool_calls": parallel_tool_calls,
                    "reasoning_effort": reasoning_effort,
                    "top_p": top_p,
                },
                run_create_params.RunCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
            stream=True,
            stream_cls=Stream[AssistantStreamEvent],
        )
        return AssistantStreamManager(make_request, event_handler=event_handler or AssistantEventHandler())

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def poll(
        self,
        run_id: str,
        thread_id: str,
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        A helper to poll a run status until it reaches a terminal state. More
        information on Run lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        extra_headers = {"X-Stainless-Poll-Helper": "true", **(extra_headers or {})}

        if is_given(poll_interval_ms):
            extra_headers["X-Stainless-Custom-Poll-Interval"] = str(poll_interval_ms)

        terminal_states = {"requires_action", "cancelled", "completed", "failed", "expired", "incomplete"}
        while True:
            response = self.with_raw_response.retrieve(  # pyright: ignore[reportDeprecated]
                thread_id=thread_id,
                run_id=run_id,
                extra_headers=extra_headers,
                extra_body=extra_body,
                extra_query=extra_query,
                timeout=timeout,
            )

            run = response.parse()
            # Return if we reached a terminal state
            if run.status in terminal_states:
                return run

            if not is_given(poll_interval_ms):
                from_header = response.headers.get("openai-poll-after-ms")
                if from_header is not None:
                    poll_interval_ms = int(from_header)
                else:
                    poll_interval_ms = 1000

            self._sleep(poll_interval_ms / 1000)

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def stream(
        self,
        *,
        assistant_id: str,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantStreamManager[AssistantEventHandler]:
        """Create a Run stream"""
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def stream(
        self,
        *,
        assistant_id: str,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        thread_id: str,
        event_handler: AssistantEventHandlerT,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantStreamManager[AssistantEventHandlerT]:
        """Create a Run stream"""
        ...

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def stream(
        self,
        *,
        assistant_id: str,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        thread_id: str,
        event_handler: AssistantEventHandlerT | None = None,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantStreamManager[AssistantEventHandler] | AssistantStreamManager[AssistantEventHandlerT]:
        """Create a Run stream"""
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")

        extra_headers = {
            "OpenAI-Beta": "assistants=v2",
            "X-Stainless-Stream-Helper": "threads.runs.create_and_stream",
            "X-Stainless-Custom-Event-Handler": "true" if event_handler else "false",
            **(extra_headers or {}),
        }
        make_request = partial(
            self._post,
            f"/threads/{thread_id}/runs",
            body=maybe_transform(
                {
                    "assistant_id": assistant_id,
                    "additional_instructions": additional_instructions,
                    "additional_messages": additional_messages,
                    "instructions": instructions,
                    "max_completion_tokens": max_completion_tokens,
                    "max_prompt_tokens": max_prompt_tokens,
                    "metadata": metadata,
                    "model": model,
                    "response_format": response_format,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "stream": True,
                    "tools": tools,
                    "parallel_tool_calls": parallel_tool_calls,
                    "reasoning_effort": reasoning_effort,
                    "truncation_strategy": truncation_strategy,
                    "top_p": top_p,
                },
                run_create_params.RunCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform({"include": include}, run_create_params.RunCreateParams),
            ),
            cast_to=Run,
            stream=True,
            stream_cls=Stream[AssistantStreamEvent],
        )
        return AssistantStreamManager(make_request, event_handler=event_handler or AssistantEventHandler())

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def submit_tool_outputs(
        self,
        run_id: str,
        *,
        thread_id: str,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        When a run has the `status: "requires_action"` and `required_action.type` is
        `submit_tool_outputs`, this endpoint can be used to submit the outputs from the
        tool calls once they're all completed. All outputs must be submitted in a single
        request.

        Args:
          tool_outputs: A list of tools for which the outputs are being submitted.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def submit_tool_outputs(
        self,
        run_id: str,
        *,
        thread_id: str,
        stream: Literal[True],
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Stream[AssistantStreamEvent]:
        """
        When a run has the `status: "requires_action"` and `required_action.type` is
        `submit_tool_outputs`, this endpoint can be used to submit the outputs from the
        tool calls once they're all completed. All outputs must be submitted in a single
        request.

        Args:
          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          tool_outputs: A list of tools for which the outputs are being submitted.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def submit_tool_outputs(
        self,
        run_id: str,
        *,
        thread_id: str,
        stream: bool,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run | Stream[AssistantStreamEvent]:
        """
        When a run has the `status: "requires_action"` and `required_action.type` is
        `submit_tool_outputs`, this endpoint can be used to submit the outputs from the
        tool calls once they're all completed. All outputs must be submitted in a single
        request.

        Args:
          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          tool_outputs: A list of tools for which the outputs are being submitted.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    @required_args(["thread_id", "tool_outputs"], ["thread_id", "stream", "tool_outputs"])
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def submit_tool_outputs(
        self,
        run_id: str,
        *,
        thread_id: str,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run | Stream[AssistantStreamEvent]:
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            f"/threads/{thread_id}/runs/{run_id}/submit_tool_outputs",
            body=maybe_transform(
                {
                    "tool_outputs": tool_outputs,
                    "stream": stream,
                },
                run_submit_tool_outputs_params.RunSubmitToolOutputsParamsStreaming
                if stream
                else run_submit_tool_outputs_params.RunSubmitToolOutputsParamsNonStreaming,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
            stream=stream or False,
            stream_cls=Stream[AssistantStreamEvent],
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def submit_tool_outputs_and_poll(
        self,
        *,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        run_id: str,
        thread_id: str,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        A helper to submit a tool output to a run and poll for a terminal run state.
        More information on Run lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        run = self.submit_tool_outputs(  # pyright: ignore[reportDeprecated]
            run_id=run_id,
            thread_id=thread_id,
            tool_outputs=tool_outputs,
            stream=False,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
        )
        return self.poll(  # pyright: ignore[reportDeprecated]
            run_id=run.id,
            thread_id=thread_id,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
            poll_interval_ms=poll_interval_ms,
        )

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def submit_tool_outputs_stream(
        self,
        *,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        run_id: str,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantStreamManager[AssistantEventHandler]:
        """
        Submit the tool outputs from a previous run and stream the run to a terminal
        state. More information on Run lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def submit_tool_outputs_stream(
        self,
        *,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        run_id: str,
        thread_id: str,
        event_handler: AssistantEventHandlerT,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantStreamManager[AssistantEventHandlerT]:
        """
        Submit the tool outputs from a previous run and stream the run to a terminal
        state. More information on Run lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        ...

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def submit_tool_outputs_stream(
        self,
        *,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        run_id: str,
        thread_id: str,
        event_handler: AssistantEventHandlerT | None = None,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantStreamManager[AssistantEventHandler] | AssistantStreamManager[AssistantEventHandlerT]:
        """
        Submit the tool outputs from a previous run and stream the run to a terminal
        state. More information on Run lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")

        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")

        extra_headers = {
            "OpenAI-Beta": "assistants=v2",
            "X-Stainless-Stream-Helper": "threads.runs.submit_tool_outputs_stream",
            "X-Stainless-Custom-Event-Handler": "true" if event_handler else "false",
            **(extra_headers or {}),
        }
        request = partial(
            self._post,
            f"/threads/{thread_id}/runs/{run_id}/submit_tool_outputs",
            body=maybe_transform(
                {
                    "tool_outputs": tool_outputs,
                    "stream": True,
                },
                run_submit_tool_outputs_params.RunSubmitToolOutputsParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
            stream=True,
            stream_cls=Stream[AssistantStreamEvent],
        )
        return AssistantStreamManager(request, event_handler=event_handler or AssistantEventHandler())


class AsyncRuns(AsyncAPIResource):
    @cached_property
    def steps(self) -> AsyncSteps:
        return AsyncSteps(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncRunsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncRunsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncRunsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncRunsWithStreamingResponse(self)

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def create(
        self,
        thread_id: str,
        *,
        assistant_id: str,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        Create a run.

        Args:
          assistant_id: The ID of the
              [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
              execute this run.

          include: A list of additional fields to include in the response. Currently the only
              supported value is `step_details.tool_calls[*].file_search.results[*].content`
              to fetch the file search result content.

              See the
              [file search tool documentation](https://platform.openai.com/docs/assistants/tools/file-search#customizing-file-search-settings)
              for more information.

          additional_instructions: Appends additional instructions at the end of the instructions for the run. This
              is useful for modifying the behavior on a per-run basis without overriding other
              instructions.

          additional_messages: Adds additional messages to the thread before creating the run.

          instructions: Overrides the
              [instructions](https://platform.openai.com/docs/api-reference/assistants/createAssistant)
              of the assistant. This is useful for modifying the behavior on a per-run basis.

          max_completion_tokens: The maximum number of completion tokens that may be used over the course of the
              run. The run will make a best effort to use only the number of completion tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              completion tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          max_prompt_tokens: The maximum number of prompt tokens that may be used over the course of the run.
              The run will make a best effort to use only the number of prompt tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              prompt tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
              be used to execute this run. If a value is provided here, it will override the
              model associated with the assistant. If not, the model associated with the
              assistant will be used.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tools and instead generates a message. `auto` is the default value
              and means the model can pick between generating a message or calling one or more
              tools. `required` means the model must call one or more tools before responding
              to the user. Specifying a particular tool like `{"type": "file_search"}` or
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

          tools: Override the tools the assistant can use for this run. This is useful for
              modifying the behavior on a per-run basis.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          truncation_strategy: Controls for how a thread will be truncated prior to the run. Use this to
              control the intial context window of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def create(
        self,
        thread_id: str,
        *,
        assistant_id: str,
        stream: Literal[True],
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[AssistantStreamEvent]:
        """
        Create a run.

        Args:
          assistant_id: The ID of the
              [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
              execute this run.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          include: A list of additional fields to include in the response. Currently the only
              supported value is `step_details.tool_calls[*].file_search.results[*].content`
              to fetch the file search result content.

              See the
              [file search tool documentation](https://platform.openai.com/docs/assistants/tools/file-search#customizing-file-search-settings)
              for more information.

          additional_instructions: Appends additional instructions at the end of the instructions for the run. This
              is useful for modifying the behavior on a per-run basis without overriding other
              instructions.

          additional_messages: Adds additional messages to the thread before creating the run.

          instructions: Overrides the
              [instructions](https://platform.openai.com/docs/api-reference/assistants/createAssistant)
              of the assistant. This is useful for modifying the behavior on a per-run basis.

          max_completion_tokens: The maximum number of completion tokens that may be used over the course of the
              run. The run will make a best effort to use only the number of completion tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              completion tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          max_prompt_tokens: The maximum number of prompt tokens that may be used over the course of the run.
              The run will make a best effort to use only the number of prompt tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              prompt tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
              be used to execute this run. If a value is provided here, it will override the
              model associated with the assistant. If not, the model associated with the
              assistant will be used.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tools and instead generates a message. `auto` is the default value
              and means the model can pick between generating a message or calling one or more
              tools. `required` means the model must call one or more tools before responding
              to the user. Specifying a particular tool like `{"type": "file_search"}` or
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

          tools: Override the tools the assistant can use for this run. This is useful for
              modifying the behavior on a per-run basis.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          truncation_strategy: Controls for how a thread will be truncated prior to the run. Use this to
              control the intial context window of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def create(
        self,
        thread_id: str,
        *,
        assistant_id: str,
        stream: bool,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run | AsyncStream[AssistantStreamEvent]:
        """
        Create a run.

        Args:
          assistant_id: The ID of the
              [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
              execute this run.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          include: A list of additional fields to include in the response. Currently the only
              supported value is `step_details.tool_calls[*].file_search.results[*].content`
              to fetch the file search result content.

              See the
              [file search tool documentation](https://platform.openai.com/docs/assistants/tools/file-search#customizing-file-search-settings)
              for more information.

          additional_instructions: Appends additional instructions at the end of the instructions for the run. This
              is useful for modifying the behavior on a per-run basis without overriding other
              instructions.

          additional_messages: Adds additional messages to the thread before creating the run.

          instructions: Overrides the
              [instructions](https://platform.openai.com/docs/api-reference/assistants/createAssistant)
              of the assistant. This is useful for modifying the behavior on a per-run basis.

          max_completion_tokens: The maximum number of completion tokens that may be used over the course of the
              run. The run will make a best effort to use only the number of completion tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              completion tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          max_prompt_tokens: The maximum number of prompt tokens that may be used over the course of the run.
              The run will make a best effort to use only the number of prompt tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              prompt tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
              be used to execute this run. If a value is provided here, it will override the
              model associated with the assistant. If not, the model associated with the
              assistant will be used.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tools and instead generates a message. `auto` is the default value
              and means the model can pick between generating a message or calling one or more
              tools. `required` means the model must call one or more tools before responding
              to the user. Specifying a particular tool like `{"type": "file_search"}` or
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

          tools: Override the tools the assistant can use for this run. This is useful for
              modifying the behavior on a per-run basis.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          truncation_strategy: Controls for how a thread will be truncated prior to the run. Use this to
              control the intial context window of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    @required_args(["assistant_id"], ["assistant_id", "stream"])
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def create(
        self,
        thread_id: str,
        *,
        assistant_id: str,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run | AsyncStream[AssistantStreamEvent]:
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            f"/threads/{thread_id}/runs",
            body=await async_maybe_transform(
                {
                    "assistant_id": assistant_id,
                    "additional_instructions": additional_instructions,
                    "additional_messages": additional_messages,
                    "instructions": instructions,
                    "max_completion_tokens": max_completion_tokens,
                    "max_prompt_tokens": max_prompt_tokens,
                    "metadata": metadata,
                    "model": model,
                    "parallel_tool_calls": parallel_tool_calls,
                    "reasoning_effort": reasoning_effort,
                    "response_format": response_format,
                    "stream": stream,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_p": top_p,
                    "truncation_strategy": truncation_strategy,
                },
                run_create_params.RunCreateParamsStreaming if stream else run_create_params.RunCreateParamsNonStreaming,
            ),
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=await async_maybe_transform({"include": include}, run_create_params.RunCreateParams),
            ),
            cast_to=Run,
            stream=stream or False,
            stream_cls=AsyncStream[AssistantStreamEvent],
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def retrieve(
        self,
        run_id: str,
        *,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        Retrieves a run.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._get(
            f"/threads/{thread_id}/runs/{run_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def update(
        self,
        run_id: str,
        *,
        thread_id: str,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        Modifies a run.

        Args:
          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            f"/threads/{thread_id}/runs/{run_id}",
            body=await async_maybe_transform({"metadata": metadata}, run_update_params.RunUpdateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def list(
        self,
        thread_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[Run, AsyncCursorPage[Run]]:
        """
        Returns a list of runs belonging to a thread.

        Args:
          after: A cursor for use in pagination. `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          before: A cursor for use in pagination. `before` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              starting with obj_foo, your subsequent call can include before=obj_foo in order
              to fetch the previous page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            f"/threads/{thread_id}/runs",
            page=AsyncCursorPage[Run],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "limit": limit,
                        "order": order,
                    },
                    run_list_params.RunListParams,
                ),
            ),
            model=Run,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def cancel(
        self,
        run_id: str,
        *,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        Cancels a run that is `in_progress`.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            f"/threads/{thread_id}/runs/{run_id}/cancel",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def create_and_poll(
        self,
        *,
        assistant_id: str,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        A helper to create a run an poll for a terminal state. More information on Run
        lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        run = await self.create(  # pyright: ignore[reportDeprecated]
            thread_id=thread_id,
            assistant_id=assistant_id,
            include=include,
            additional_instructions=additional_instructions,
            additional_messages=additional_messages,
            instructions=instructions,
            max_completion_tokens=max_completion_tokens,
            max_prompt_tokens=max_prompt_tokens,
            metadata=metadata,
            model=model,
            response_format=response_format,
            temperature=temperature,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            reasoning_effort=reasoning_effort,
            # We assume we are not streaming when polling
            stream=False,
            tools=tools,
            truncation_strategy=truncation_strategy,
            top_p=top_p,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
        )
        return await self.poll(  # pyright: ignore[reportDeprecated]
            run.id,
            thread_id=thread_id,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            poll_interval_ms=poll_interval_ms,
            timeout=timeout,
        )

    @overload
    @typing_extensions.deprecated("use `stream` instead")
    def create_and_stream(
        self,
        *,
        assistant_id: str,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncAssistantStreamManager[AsyncAssistantEventHandler]:
        """Create a Run stream"""
        ...

    @overload
    @typing_extensions.deprecated("use `stream` instead")
    def create_and_stream(
        self,
        *,
        assistant_id: str,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        thread_id: str,
        event_handler: AsyncAssistantEventHandlerT,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncAssistantStreamManager[AsyncAssistantEventHandlerT]:
        """Create a Run stream"""
        ...

    @typing_extensions.deprecated("use `stream` instead")
    def create_and_stream(
        self,
        *,
        assistant_id: str,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        thread_id: str,
        event_handler: AsyncAssistantEventHandlerT | None = None,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> (
        AsyncAssistantStreamManager[AsyncAssistantEventHandler]
        | AsyncAssistantStreamManager[AsyncAssistantEventHandlerT]
    ):
        """Create a Run stream"""
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")

        extra_headers = {
            "OpenAI-Beta": "assistants=v2",
            "X-Stainless-Stream-Helper": "threads.runs.create_and_stream",
            "X-Stainless-Custom-Event-Handler": "true" if event_handler else "false",
            **(extra_headers or {}),
        }
        request = self._post(
            f"/threads/{thread_id}/runs",
            body=maybe_transform(
                {
                    "assistant_id": assistant_id,
                    "additional_instructions": additional_instructions,
                    "additional_messages": additional_messages,
                    "instructions": instructions,
                    "max_completion_tokens": max_completion_tokens,
                    "max_prompt_tokens": max_prompt_tokens,
                    "metadata": metadata,
                    "model": model,
                    "response_format": response_format,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "stream": True,
                    "tools": tools,
                    "truncation_strategy": truncation_strategy,
                    "top_p": top_p,
                    "parallel_tool_calls": parallel_tool_calls,
                },
                run_create_params.RunCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
            stream=True,
            stream_cls=AsyncStream[AssistantStreamEvent],
        )
        return AsyncAssistantStreamManager(request, event_handler=event_handler or AsyncAssistantEventHandler())

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def poll(
        self,
        run_id: str,
        thread_id: str,
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        A helper to poll a run status until it reaches a terminal state. More
        information on Run lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        extra_headers = {"X-Stainless-Poll-Helper": "true", **(extra_headers or {})}

        if is_given(poll_interval_ms):
            extra_headers["X-Stainless-Custom-Poll-Interval"] = str(poll_interval_ms)

        terminal_states = {"requires_action", "cancelled", "completed", "failed", "expired", "incomplete"}
        while True:
            response = await self.with_raw_response.retrieve(  # pyright: ignore[reportDeprecated]
                thread_id=thread_id,
                run_id=run_id,
                extra_headers=extra_headers,
                extra_body=extra_body,
                extra_query=extra_query,
                timeout=timeout,
            )

            run = response.parse()
            # Return if we reached a terminal state
            if run.status in terminal_states:
                return run

            if not is_given(poll_interval_ms):
                from_header = response.headers.get("openai-poll-after-ms")
                if from_header is not None:
                    poll_interval_ms = int(from_header)
                else:
                    poll_interval_ms = 1000

            await self._sleep(poll_interval_ms / 1000)

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def stream(
        self,
        *,
        assistant_id: str,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncAssistantStreamManager[AsyncAssistantEventHandler]:
        """Create a Run stream"""
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def stream(
        self,
        *,
        assistant_id: str,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        thread_id: str,
        event_handler: AsyncAssistantEventHandlerT,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncAssistantStreamManager[AsyncAssistantEventHandlerT]:
        """Create a Run stream"""
        ...

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def stream(
        self,
        *,
        assistant_id: str,
        include: List[RunStepInclude] | NotGiven = NOT_GIVEN,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[Iterable[run_create_params.AdditionalMessage]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[run_create_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        thread_id: str,
        event_handler: AsyncAssistantEventHandlerT | None = None,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> (
        AsyncAssistantStreamManager[AsyncAssistantEventHandler]
        | AsyncAssistantStreamManager[AsyncAssistantEventHandlerT]
    ):
        """Create a Run stream"""
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")

        extra_headers = {
            "OpenAI-Beta": "assistants=v2",
            "X-Stainless-Stream-Helper": "threads.runs.create_and_stream",
            "X-Stainless-Custom-Event-Handler": "true" if event_handler else "false",
            **(extra_headers or {}),
        }
        request = self._post(
            f"/threads/{thread_id}/runs",
            body=maybe_transform(
                {
                    "assistant_id": assistant_id,
                    "additional_instructions": additional_instructions,
                    "additional_messages": additional_messages,
                    "instructions": instructions,
                    "max_completion_tokens": max_completion_tokens,
                    "max_prompt_tokens": max_prompt_tokens,
                    "metadata": metadata,
                    "model": model,
                    "response_format": response_format,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "stream": True,
                    "tools": tools,
                    "parallel_tool_calls": parallel_tool_calls,
                    "reasoning_effort": reasoning_effort,
                    "truncation_strategy": truncation_strategy,
                    "top_p": top_p,
                },
                run_create_params.RunCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform({"include": include}, run_create_params.RunCreateParams),
            ),
            cast_to=Run,
            stream=True,
            stream_cls=AsyncStream[AssistantStreamEvent],
        )
        return AsyncAssistantStreamManager(request, event_handler=event_handler or AsyncAssistantEventHandler())

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def submit_tool_outputs(
        self,
        run_id: str,
        *,
        thread_id: str,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        When a run has the `status: "requires_action"` and `required_action.type` is
        `submit_tool_outputs`, this endpoint can be used to submit the outputs from the
        tool calls once they're all completed. All outputs must be submitted in a single
        request.

        Args:
          tool_outputs: A list of tools for which the outputs are being submitted.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def submit_tool_outputs(
        self,
        run_id: str,
        *,
        thread_id: str,
        stream: Literal[True],
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[AssistantStreamEvent]:
        """
        When a run has the `status: "requires_action"` and `required_action.type` is
        `submit_tool_outputs`, this endpoint can be used to submit the outputs from the
        tool calls once they're all completed. All outputs must be submitted in a single
        request.

        Args:
          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          tool_outputs: A list of tools for which the outputs are being submitted.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def submit_tool_outputs(
        self,
        run_id: str,
        *,
        thread_id: str,
        stream: bool,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run | AsyncStream[AssistantStreamEvent]:
        """
        When a run has the `status: "requires_action"` and `required_action.type` is
        `submit_tool_outputs`, this endpoint can be used to submit the outputs from the
        tool calls once they're all completed. All outputs must be submitted in a single
        request.

        Args:
          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          tool_outputs: A list of tools for which the outputs are being submitted.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    @required_args(["thread_id", "tool_outputs"], ["thread_id", "stream", "tool_outputs"])
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def submit_tool_outputs(
        self,
        run_id: str,
        *,
        thread_id: str,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run | AsyncStream[AssistantStreamEvent]:
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            f"/threads/{thread_id}/runs/{run_id}/submit_tool_outputs",
            body=await async_maybe_transform(
                {
                    "tool_outputs": tool_outputs,
                    "stream": stream,
                },
                run_submit_tool_outputs_params.RunSubmitToolOutputsParamsStreaming
                if stream
                else run_submit_tool_outputs_params.RunSubmitToolOutputsParamsNonStreaming,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
            stream=stream or False,
            stream_cls=AsyncStream[AssistantStreamEvent],
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def submit_tool_outputs_and_poll(
        self,
        *,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        run_id: str,
        thread_id: str,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        A helper to submit a tool output to a run and poll for a terminal run state.
        More information on Run lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        run = await self.submit_tool_outputs(  # pyright: ignore[reportDeprecated]
            run_id=run_id,
            thread_id=thread_id,
            tool_outputs=tool_outputs,
            stream=False,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
        )
        return await self.poll(  # pyright: ignore[reportDeprecated]
            run_id=run.id,
            thread_id=thread_id,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
            poll_interval_ms=poll_interval_ms,
        )

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def submit_tool_outputs_stream(
        self,
        *,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        run_id: str,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncAssistantStreamManager[AsyncAssistantEventHandler]:
        """
        Submit the tool outputs from a previous run and stream the run to a terminal
        state. More information on Run lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def submit_tool_outputs_stream(
        self,
        *,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        run_id: str,
        thread_id: str,
        event_handler: AsyncAssistantEventHandlerT,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncAssistantStreamManager[AsyncAssistantEventHandlerT]:
        """
        Submit the tool outputs from a previous run and stream the run to a terminal
        state. More information on Run lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        ...

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def submit_tool_outputs_stream(
        self,
        *,
        tool_outputs: Iterable[run_submit_tool_outputs_params.ToolOutput],
        run_id: str,
        thread_id: str,
        event_handler: AsyncAssistantEventHandlerT | None = None,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> (
        AsyncAssistantStreamManager[AsyncAssistantEventHandler]
        | AsyncAssistantStreamManager[AsyncAssistantEventHandlerT]
    ):
        """
        Submit the tool outputs from a previous run and stream the run to a terminal
        state. More information on Run lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")

        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")

        extra_headers = {
            "OpenAI-Beta": "assistants=v2",
            "X-Stainless-Stream-Helper": "threads.runs.submit_tool_outputs_stream",
            "X-Stainless-Custom-Event-Handler": "true" if event_handler else "false",
            **(extra_headers or {}),
        }
        request = self._post(
            f"/threads/{thread_id}/runs/{run_id}/submit_tool_outputs",
            body=maybe_transform(
                {
                    "tool_outputs": tool_outputs,
                    "stream": True,
                },
                run_submit_tool_outputs_params.RunSubmitToolOutputsParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
            stream=True,
            stream_cls=AsyncStream[AssistantStreamEvent],
        )
        return AsyncAssistantStreamManager(request, event_handler=event_handler or AsyncAssistantEventHandler())


class RunsWithRawResponse:
    def __init__(self, runs: Runs) -> None:
        self._runs = runs

        self.create = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                runs.create  # pyright: ignore[reportDeprecated],
            )
        )
        self.retrieve = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                runs.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.update = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                runs.update  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                runs.list  # pyright: ignore[reportDeprecated],
            )
        )
        self.cancel = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                runs.cancel  # pyright: ignore[reportDeprecated],
            )
        )
        self.submit_tool_outputs = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                runs.submit_tool_outputs  # pyright: ignore[reportDeprecated],
            )
        )

    @cached_property
    def steps(self) -> StepsWithRawResponse:
        return StepsWithRawResponse(self._runs.steps)


class AsyncRunsWithRawResponse:
    def __init__(self, runs: AsyncRuns) -> None:
        self._runs = runs

        self.create = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                runs.create  # pyright: ignore[reportDeprecated],
            )
        )
        self.retrieve = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                runs.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.update = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                runs.update  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                runs.list  # pyright: ignore[reportDeprecated],
            )
        )
        self.cancel = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                runs.cancel  # pyright: ignore[reportDeprecated],
            )
        )
        self.submit_tool_outputs = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                runs.submit_tool_outputs  # pyright: ignore[reportDeprecated],
            )
        )

    @cached_property
    def steps(self) -> AsyncStepsWithRawResponse:
        return AsyncStepsWithRawResponse(self._runs.steps)


class RunsWithStreamingResponse:
    def __init__(self, runs: Runs) -> None:
        self._runs = runs

        self.create = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                runs.create  # pyright: ignore[reportDeprecated],
            )
        )
        self.retrieve = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                runs.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.update = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                runs.update  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                runs.list  # pyright: ignore[reportDeprecated],
            )
        )
        self.cancel = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                runs.cancel  # pyright: ignore[reportDeprecated],
            )
        )
        self.submit_tool_outputs = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                runs.submit_tool_outputs  # pyright: ignore[reportDeprecated],
            )
        )

    @cached_property
    def steps(self) -> StepsWithStreamingResponse:
        return StepsWithStreamingResponse(self._runs.steps)


class AsyncRunsWithStreamingResponse:
    def __init__(self, runs: AsyncRuns) -> None:
        self._runs = runs

        self.create = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                runs.create  # pyright: ignore[reportDeprecated],
            )
        )
        self.retrieve = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                runs.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.update = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                runs.update  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                runs.list  # pyright: ignore[reportDeprecated],
            )
        )
        self.cancel = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                runs.cancel  # pyright: ignore[reportDeprecated],
            )
        )
        self.submit_tool_outputs = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                runs.submit_tool_outputs  # pyright: ignore[reportDeprecated],
            )
        )

    @cached_property
    def steps(self) -> AsyncStepsWithStreamingResponse:
        return AsyncStepsWithStreamingResponse(self._runs.steps)