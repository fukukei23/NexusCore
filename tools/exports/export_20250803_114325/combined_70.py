
# === NexusCore/openenv\Lib\site-packages\pydantic\main.py ===
"""Logic for creating models."""

# Because `dict` is in the local namespace of the `BaseModel` class, we use `Dict` for annotations.
# TODO v3 fallback to `dict` when the deprecated `dict` method gets removed.
# ruff: noqa: UP035

from __future__ import annotations as _annotations

import operator
import sys
import types
import typing
import warnings
from collections.abc import Generator, Mapping
from copy import copy, deepcopy
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Literal,
    TypeVar,
    Union,
    cast,
    overload,
)

import pydantic_core
import typing_extensions
from pydantic_core import PydanticUndefined, ValidationError
from typing_extensions import Self, TypeAlias, Unpack

from . import PydanticDeprecatedSince20, PydanticDeprecatedSince211
from ._internal import (
    _config,
    _decorators,
    _fields,
    _forward_ref,
    _generics,
    _mock_val_ser,
    _model_construction,
    _namespace_utils,
    _repr,
    _typing_extra,
    _utils,
)
from ._migration import getattr_migration
from .aliases import AliasChoices, AliasPath
from .annotated_handlers import GetCoreSchemaHandler, GetJsonSchemaHandler
from .config import ConfigDict
from .errors import PydanticUndefinedAnnotation, PydanticUserError
from .json_schema import DEFAULT_REF_TEMPLATE, GenerateJsonSchema, JsonSchemaMode, JsonSchemaValue, model_json_schema
from .plugin._schema_validator import PluggableSchemaValidator

if TYPE_CHECKING:
    from inspect import Signature
    from pathlib import Path

    from pydantic_core import CoreSchema, SchemaSerializer, SchemaValidator

    from ._internal._namespace_utils import MappingNamespace
    from ._internal._utils import AbstractSetIntStr, MappingIntStrAny
    from .deprecated.parse import Protocol as DeprecatedParseProtocol
    from .fields import ComputedFieldInfo, FieldInfo, ModelPrivateAttr
else:
    # See PyCharm issues https://youtrack.jetbrains.com/issue/PY-21915
    # and https://youtrack.jetbrains.com/issue/PY-51428
    DeprecationWarning = PydanticDeprecatedSince20

__all__ = 'BaseModel', 'create_model'

# Keep these type aliases available at runtime:
TupleGenerator: TypeAlias = Generator[tuple[str, Any], None, None]
# NOTE: In reality, `bool` should be replaced by `Literal[True]` but mypy fails to correctly apply bidirectional
# type inference (e.g. when using `{'a': {'b': True}}`):
# NOTE: Keep this type alias in sync with the stub definition in `pydantic-core`:
IncEx: TypeAlias = Union[set[int], set[str], Mapping[int, Union['IncEx', bool]], Mapping[str, Union['IncEx', bool]]]

_object_setattr = _model_construction.object_setattr


def _check_frozen(model_cls: type[BaseModel], name: str, value: Any) -> None:
    if model_cls.model_config.get('frozen'):
        error_type = 'frozen_instance'
    elif getattr(model_cls.__pydantic_fields__.get(name), 'frozen', False):
        error_type = 'frozen_field'
    else:
        return

    raise ValidationError.from_exception_data(
        model_cls.__name__, [{'type': error_type, 'loc': (name,), 'input': value}]
    )


def _model_field_setattr_handler(model: BaseModel, name: str, val: Any) -> None:
    model.__dict__[name] = val
    model.__pydantic_fields_set__.add(name)


def _private_setattr_handler(model: BaseModel, name: str, val: Any) -> None:
    if getattr(model, '__pydantic_private__', None) is None:
        # While the attribute should be present at this point, this may not be the case if
        # users do unusual stuff with `model_post_init()` (which is where the  `__pydantic_private__`
        # is initialized, by wrapping the user-defined `model_post_init()`), e.g. if they mock
        # the `model_post_init()` call. Ideally we should find a better way to init private attrs.
        object.__setattr__(model, '__pydantic_private__', {})
    model.__pydantic_private__[name] = val  # pyright: ignore[reportOptionalSubscript]


_SIMPLE_SETATTR_HANDLERS: Mapping[str, Callable[[BaseModel, str, Any], None]] = {
    'model_field': _model_field_setattr_handler,
    'validate_assignment': lambda model, name, val: model.__pydantic_validator__.validate_assignment(model, name, val),  # pyright: ignore[reportAssignmentType]
    'private': _private_setattr_handler,
    'cached_property': lambda model, name, val: model.__dict__.__setitem__(name, val),
    'extra_known': lambda model, name, val: _object_setattr(model, name, val),
}


class BaseModel(metaclass=_model_construction.ModelMetaclass):
    """!!! abstract "Usage Documentation"
        [Models](../concepts/models.md)

    A base class for creating Pydantic models.

    Attributes:
        __class_vars__: The names of the class variables defined on the model.
        __private_attributes__: Metadata about the private attributes of the model.
        __signature__: The synthesized `__init__` [`Signature`][inspect.Signature] of the model.

        __pydantic_complete__: Whether model building is completed, or if there are still undefined fields.
        __pydantic_core_schema__: The core schema of the model.
        __pydantic_custom_init__: Whether the model has a custom `__init__` function.
        __pydantic_decorators__: Metadata containing the decorators defined on the model.
            This replaces `Model.__validators__` and `Model.__root_validators__` from Pydantic V1.
        __pydantic_generic_metadata__: Metadata for generic models; contains data used for a similar purpose to
            __args__, __origin__, __parameters__ in typing-module generics. May eventually be replaced by these.
        __pydantic_parent_namespace__: Parent namespace of the model, used for automatic rebuilding of models.
        __pydantic_post_init__: The name of the post-init method for the model, if defined.
        __pydantic_root_model__: Whether the model is a [`RootModel`][pydantic.root_model.RootModel].
        __pydantic_serializer__: The `pydantic-core` `SchemaSerializer` used to dump instances of the model.
        __pydantic_validator__: The `pydantic-core` `SchemaValidator` used to validate instances of the model.

        __pydantic_fields__: A dictionary of field names and their corresponding [`FieldInfo`][pydantic.fields.FieldInfo] objects.
        __pydantic_computed_fields__: A dictionary of computed field names and their corresponding [`ComputedFieldInfo`][pydantic.fields.ComputedFieldInfo] objects.

        __pydantic_extra__: A dictionary containing extra values, if [`extra`][pydantic.config.ConfigDict.extra]
            is set to `'allow'`.
        __pydantic_fields_set__: The names of fields explicitly set during instantiation.
        __pydantic_private__: Values of private attributes set on the model instance.
    """

    # Note: Many of the below class vars are defined in the metaclass, but we define them here for type checking purposes.

    model_config: ClassVar[ConfigDict] = ConfigDict()
    """
    Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].
    """

    __class_vars__: ClassVar[set[str]]
    """The names of the class variables defined on the model."""

    __private_attributes__: ClassVar[Dict[str, ModelPrivateAttr]]  # noqa: UP006
    """Metadata about the private attributes of the model."""

    __signature__: ClassVar[Signature]
    """The synthesized `__init__` [`Signature`][inspect.Signature] of the model."""

    __pydantic_complete__: ClassVar[bool] = False
    """Whether model building is completed, or if there are still undefined fields."""

    __pydantic_core_schema__: ClassVar[CoreSchema]
    """The core schema of the model."""

    __pydantic_custom_init__: ClassVar[bool]
    """Whether the model has a custom `__init__` method."""

    # Must be set for `GenerateSchema.model_schema` to work for a plain `BaseModel` annotation.
    __pydantic_decorators__: ClassVar[_decorators.DecoratorInfos] = _decorators.DecoratorInfos()
    """Metadata containing the decorators defined on the model.
    This replaces `Model.__validators__` and `Model.__root_validators__` from Pydantic V1."""

    __pydantic_generic_metadata__: ClassVar[_generics.PydanticGenericMetadata]
    """Metadata for generic models; contains data used for a similar purpose to
    __args__, __origin__, __parameters__ in typing-module generics. May eventually be replaced by these."""

    __pydantic_parent_namespace__: ClassVar[Dict[str, Any] | None] = None  # noqa: UP006
    """Parent namespace of the model, used for automatic rebuilding of models."""

    __pydantic_post_init__: ClassVar[None | Literal['model_post_init']]
    """The name of the post-init method for the model, if defined."""

    __pydantic_root_model__: ClassVar[bool] = False
    """Whether the model is a [`RootModel`][pydantic.root_model.RootModel]."""

    __pydantic_serializer__: ClassVar[SchemaSerializer]
    """The `pydantic-core` `SchemaSerializer` used to dump instances of the model."""

    __pydantic_validator__: ClassVar[SchemaValidator | PluggableSchemaValidator]
    """The `pydantic-core` `SchemaValidator` used to validate instances of the model."""

    __pydantic_fields__: ClassVar[Dict[str, FieldInfo]]  # noqa: UP006
    """A dictionary of field names and their corresponding [`FieldInfo`][pydantic.fields.FieldInfo] objects.
    This replaces `Model.__fields__` from Pydantic V1.
    """

    __pydantic_setattr_handlers__: ClassVar[Dict[str, Callable[[BaseModel, str, Any], None]]]  # noqa: UP006
    """`__setattr__` handlers. Memoizing the handlers leads to a dramatic performance improvement in `__setattr__`"""

    __pydantic_computed_fields__: ClassVar[Dict[str, ComputedFieldInfo]]  # noqa: UP006
    """A dictionary of computed field names and their corresponding [`ComputedFieldInfo`][pydantic.fields.ComputedFieldInfo] objects."""

    __pydantic_extra__: dict[str, Any] | None = _model_construction.NoInitField(init=False)
    """A dictionary containing extra values, if [`extra`][pydantic.config.ConfigDict.extra] is set to `'allow'`."""

    __pydantic_fields_set__: set[str] = _model_construction.NoInitField(init=False)
    """The names of fields explicitly set during instantiation."""

    __pydantic_private__: dict[str, Any] | None = _model_construction.NoInitField(init=False)
    """Values of private attributes set on the model instance."""

    if not TYPE_CHECKING:
        # Prevent `BaseModel` from being instantiated directly
        # (defined in an `if not TYPE_CHECKING` block for clarity and to avoid type checking errors):
        __pydantic_core_schema__ = _mock_val_ser.MockCoreSchema(
            'Pydantic models should inherit from BaseModel, BaseModel cannot be instantiated directly',
            code='base-model-instantiated',
        )
        __pydantic_validator__ = _mock_val_ser.MockValSer(
            'Pydantic models should inherit from BaseModel, BaseModel cannot be instantiated directly',
            val_or_ser='validator',
            code='base-model-instantiated',
        )
        __pydantic_serializer__ = _mock_val_ser.MockValSer(
            'Pydantic models should inherit from BaseModel, BaseModel cannot be instantiated directly',
            val_or_ser='serializer',
            code='base-model-instantiated',
        )

    __slots__ = '__dict__', '__pydantic_fields_set__', '__pydantic_extra__', '__pydantic_private__'

    def __init__(self, /, **data: Any) -> None:
        """Create a new model by parsing and validating input data from keyword arguments.

        Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
        validated to form a valid model.

        `self` is explicitly positional-only to allow `self` as a field name.
        """
        # `__tracebackhide__` tells pytest and some other tools to omit this function from tracebacks
        __tracebackhide__ = True
        validated_self = self.__pydantic_validator__.validate_python(data, self_instance=self)
        if self is not validated_self:
            warnings.warn(
                'A custom validator is returning a value other than `self`.\n'
                "Returning anything other than `self` from a top level model validator isn't supported when validating via `__init__`.\n"
                'See the `model_validator` docs (https://docs.pydantic.dev/latest/concepts/validators/#model-validators) for more details.',
                stacklevel=2,
            )

    # The following line sets a flag that we use to determine when `__init__` gets overridden by the user
    __init__.__pydantic_base_init__ = True  # pyright: ignore[reportFunctionMemberAccess]

    @_utils.deprecated_instance_property
    @classmethod
    def model_fields(cls) -> dict[str, FieldInfo]:
        """A mapping of field names to their respective [`FieldInfo`][pydantic.fields.FieldInfo] instances.

        !!! warning
            Accessing this attribute from a model instance is deprecated, and will not work in Pydantic V3.
            Instead, you should access this attribute from the model class.
        """
        return getattr(cls, '__pydantic_fields__', {})

    @_utils.deprecated_instance_property
    @classmethod
    def model_computed_fields(cls) -> dict[str, ComputedFieldInfo]:
        """A mapping of computed field names to their respective [`ComputedFieldInfo`][pydantic.fields.ComputedFieldInfo] instances.

        !!! warning
            Accessing this attribute from a model instance is deprecated, and will not work in Pydantic V3.
            Instead, you should access this attribute from the model class.
        """
        return getattr(cls, '__pydantic_computed_fields__', {})

    @property
    def model_extra(self) -> dict[str, Any] | None:
        """Get extra fields set during validation.

        Returns:
            A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.
        """
        return self.__pydantic_extra__

    @property
    def model_fields_set(self) -> set[str]:
        """Returns the set of fields that have been explicitly set on this model instance.

        Returns:
            A set of strings representing the fields that have been set,
                i.e. that were not filled from defaults.
        """
        return self.__pydantic_fields_set__

    @classmethod
    def model_construct(cls, _fields_set: set[str] | None = None, **values: Any) -> Self:  # noqa: C901
        """Creates a new instance of the `Model` class with validated data.

        Creates a new model setting `__dict__` and `__pydantic_fields_set__` from trusted or pre-validated data.
        Default values are respected, but no other validation is performed.

        !!! note
            `model_construct()` generally respects the `model_config.extra` setting on the provided model.
            That is, if `model_config.extra == 'allow'`, then all extra passed values are added to the model instance's `__dict__`
            and `__pydantic_extra__` fields. If `model_config.extra == 'ignore'` (the default), then all extra passed values are ignored.
            Because no validation is performed with a call to `model_construct()`, having `model_config.extra == 'forbid'` does not result in
            an error if extra values are passed, but they will be ignored.

        Args:
            _fields_set: A set of field names that were originally explicitly set during instantiation. If provided,
                this is directly used for the [`model_fields_set`][pydantic.BaseModel.model_fields_set] attribute.
                Otherwise, the field names from the `values` argument will be used.
            values: Trusted or pre-validated data dictionary.

        Returns:
            A new instance of the `Model` class with validated data.
        """
        m = cls.__new__(cls)
        fields_values: dict[str, Any] = {}
        fields_set = set()

        for name, field in cls.__pydantic_fields__.items():
            if field.alias is not None and field.alias in values:
                fields_values[name] = values.pop(field.alias)
                fields_set.add(name)

            if (name not in fields_set) and (field.validation_alias is not None):
                validation_aliases: list[str | AliasPath] = (
                    field.validation_alias.choices
                    if isinstance(field.validation_alias, AliasChoices)
                    else [field.validation_alias]
                )

                for alias in validation_aliases:
                    if isinstance(alias, str) and alias in values:
                        fields_values[name] = values.pop(alias)
                        fields_set.add(name)
                        break
                    elif isinstance(alias, AliasPath):
                        value = alias.search_dict_for_path(values)
                        if value is not PydanticUndefined:
                            fields_values[name] = value
                            fields_set.add(name)
                            break

            if name not in fields_set:
                if name in values:
                    fields_values[name] = values.pop(name)
                    fields_set.add(name)
                elif not field.is_required():
                    fields_values[name] = field.get_default(call_default_factory=True, validated_data=fields_values)
        if _fields_set is None:
            _fields_set = fields_set

        _extra: dict[str, Any] | None = values if cls.model_config.get('extra') == 'allow' else None
        _object_setattr(m, '__dict__', fields_values)
        _object_setattr(m, '__pydantic_fields_set__', _fields_set)
        if not cls.__pydantic_root_model__:
            _object_setattr(m, '__pydantic_extra__', _extra)

        if cls.__pydantic_post_init__:
            m.model_post_init(None)
            # update private attributes with values set
            if hasattr(m, '__pydantic_private__') and m.__pydantic_private__ is not None:
                for k, v in values.items():
                    if k in m.__private_attributes__:
                        m.__pydantic_private__[k] = v

        elif not cls.__pydantic_root_model__:
            # Note: if there are any private attributes, cls.__pydantic_post_init__ would exist
            # Since it doesn't, that means that `__pydantic_private__` should be set to None
            _object_setattr(m, '__pydantic_private__', None)

        return m

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        """!!! abstract "Usage Documentation"
            [`model_copy`](../concepts/serialization.md#model_copy)

        Returns a copy of the model.

        !!! note
            The underlying instance's [`__dict__`][object.__dict__] attribute is copied. This
            might have unexpected side effects if you store anything in it, on top of the model
            fields (e.g. the value of [cached properties][functools.cached_property]).

        Args:
            update: Values to change/add in the new model. Note: the data is not validated
                before creating the new model. You should trust this data.
            deep: Set to `True` to make a deep copy of the model.

        Returns:
            New model instance.
        """
        copied = self.__deepcopy__() if deep else self.__copy__()
        if update:
            if self.model_config.get('extra') == 'allow':
                for k, v in update.items():
                    if k in self.__pydantic_fields__:
                        copied.__dict__[k] = v
                    else:
                        if copied.__pydantic_extra__ is None:
                            copied.__pydantic_extra__ = {}
                        copied.__pydantic_extra__[k] = v
            else:
                copied.__dict__.update(update)
            copied.__pydantic_fields_set__.update(update.keys())
        return copied

    def model_dump(
        self,
        *,
        mode: Literal['json', 'python'] | str = 'python',
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal['none', 'warn', 'error'] = True,
        fallback: Callable[[Any], Any] | None = None,
        serialize_as_any: bool = False,
    ) -> dict[str, Any]:
        """!!! abstract "Usage Documentation"
            [`model_dump`](../concepts/serialization.md#modelmodel_dump)

        Generate a dictionary representation of the model, optionally specifying which fields to include or exclude.

        Args:
            mode: The mode in which `to_python` should run.
                If mode is 'json', the output will only contain JSON serializable types.
                If mode is 'python', the output may contain non-JSON-serializable Python objects.
            include: A set of fields to include in the output.
            exclude: A set of fields to exclude from the output.
            context: Additional context to pass to the serializer.
            by_alias: Whether to use the field's alias in the dictionary key if defined.
            exclude_unset: Whether to exclude fields that have not been explicitly set.
            exclude_defaults: Whether to exclude fields that are set to their default value.
            exclude_none: Whether to exclude fields that have a value of `None`.
            round_trip: If True, dumped values should be valid as input for non-idempotent types such as Json[T].
            warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
                "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
            fallback: A function to call when an unknown value is encountered. If not provided,
                a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError] error is raised.
            serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.

        Returns:
            A dictionary representation of the model.
        """
        return self.__pydantic_serializer__.to_python(
            self,
            mode=mode,
            by_alias=by_alias,
            include=include,
            exclude=exclude,
            context=context,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            fallback=fallback,
            serialize_as_any=serialize_as_any,
        )

    def model_dump_json(
        self,
        *,
        indent: int | None = None,
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal['none', 'warn', 'error'] = True,
        fallback: Callable[[Any], Any] | None = None,
        serialize_as_any: bool = False,
    ) -> str:
        """!!! abstract "Usage Documentation"
            [`model_dump_json`](../concepts/serialization.md#modelmodel_dump_json)

        Generates a JSON representation of the model using Pydantic's `to_json` method.

        Args:
            indent: Indentation to use in the JSON output. If None is passed, the output will be compact.
            include: Field(s) to include in the JSON output.
            exclude: Field(s) to exclude from the JSON output.
            context: Additional context to pass to the serializer.
            by_alias: Whether to serialize using field aliases.
            exclude_unset: Whether to exclude fields that have not been explicitly set.
            exclude_defaults: Whether to exclude fields that are set to their default value.
            exclude_none: Whether to exclude fields that have a value of `None`.
            round_trip: If True, dumped values should be valid as input for non-idempotent types such as Json[T].
            warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
                "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
            fallback: A function to call when an unknown value is encountered. If not provided,
                a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError] error is raised.
            serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.

        Returns:
            A JSON string representation of the model.
        """
        return self.__pydantic_serializer__.to_json(
            self,
            indent=indent,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            fallback=fallback,
            serialize_as_any=serialize_as_any,
        ).decode()

    @classmethod
    def model_json_schema(
        cls,
        by_alias: bool = True,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
        mode: JsonSchemaMode = 'validation',
    ) -> dict[str, Any]:
        """Generates a JSON schema for a model class.

        Args:
            by_alias: Whether to use attribute aliases or not.
            ref_template: The reference template.
            schema_generator: To override the logic used to generate the JSON schema, as a subclass of
                `GenerateJsonSchema` with your desired modifications
            mode: The mode in which to generate the schema.

        Returns:
            The JSON schema for the given model class.
        """
        return model_json_schema(
            cls, by_alias=by_alias, ref_template=ref_template, schema_generator=schema_generator, mode=mode
        )

    @classmethod
    def model_parametrized_name(cls, params: tuple[type[Any], ...]) -> str:
        """Compute the class name for parametrizations of generic classes.

        This method can be overridden to achieve a custom naming scheme for generic BaseModels.

        Args:
            params: Tuple of types of the class. Given a generic class
                `Model` with 2 type variables and a concrete model `Model[str, int]`,
                the value `(str, int)` would be passed to `params`.

        Returns:
            String representing the new class where `params` are passed to `cls` as type variables.

        Raises:
            TypeError: Raised when trying to generate concrete names for non-generic models.
        """
        if not issubclass(cls, typing.Generic):
            raise TypeError('Concrete names should only be generated for generic models.')

        # Any strings received should represent forward references, so we handle them specially below.
        # If we eventually move toward wrapping them in a ForwardRef in __class_getitem__ in the future,
        # we may be able to remove this special case.
        param_names = [param if isinstance(param, str) else _repr.display_as_type(param) for param in params]
        params_component = ', '.join(param_names)
        return f'{cls.__name__}[{params_component}]'

    def model_post_init(self, context: Any, /) -> None:
        """Override this method to perform additional initialization after `__init__` and `model_construct`.
        This is useful if you want to do some validation that requires the entire model to be initialized.
        """
        pass

    @classmethod
    def model_rebuild(
        cls,
        *,
        force: bool = False,
        raise_errors: bool = True,
        _parent_namespace_depth: int = 2,
        _types_namespace: MappingNamespace | None = None,
    ) -> bool | None:
        """Try to rebuild the pydantic-core schema for the model.

        This may be necessary when one of the annotations is a ForwardRef which could not be resolved during
        the initial attempt to build the schema, and automatic rebuilding fails.

        Args:
            force: Whether to force the rebuilding of the model schema, defaults to `False`.
            raise_errors: Whether to raise errors, defaults to `True`.
            _parent_namespace_depth: The depth level of the parent namespace, defaults to 2.
            _types_namespace: The types namespace, defaults to `None`.

        Returns:
            Returns `None` if the schema is already "complete" and rebuilding was not required.
            If rebuilding _was_ required, returns `True` if rebuilding was successful, otherwise `False`.
        """
        if not force and cls.__pydantic_complete__:
            return None

        for attr in ('__pydantic_core_schema__', '__pydantic_validator__', '__pydantic_serializer__'):
            if attr in cls.__dict__ and not isinstance(getattr(cls, attr), _mock_val_ser.MockValSer):
                # Deleting the validator/serializer is necessary as otherwise they can get reused in
                # pydantic-core. We do so only if they aren't mock instances, otherwise — as `model_rebuild()`
                # isn't thread-safe — concurrent model instantiations can lead to the parent validator being used.
                # Same applies for the core schema that can be reused in schema generation.
                delattr(cls, attr)

        cls.__pydantic_complete__ = False

        if _types_namespace is not None:
            rebuild_ns = _types_namespace
        elif _parent_namespace_depth > 0:
            rebuild_ns = _typing_extra.parent_frame_namespace(parent_depth=_parent_namespace_depth, force=True) or {}
        else:
            rebuild_ns = {}

        parent_ns = _model_construction.unpack_lenient_weakvaluedict(cls.__pydantic_parent_namespace__) or {}

        ns_resolver = _namespace_utils.NsResolver(
            parent_namespace={**rebuild_ns, **parent_ns},
        )

        if not cls.__pydantic_fields_complete__:
            typevars_map = _generics.get_model_typevars_map(cls)
            try:
                cls.__pydantic_fields__ = _fields.rebuild_model_fields(
                    cls,
                    ns_resolver=ns_resolver,
                    typevars_map=typevars_map,
                )
            except NameError as e:
                exc = PydanticUndefinedAnnotation.from_name_error(e)
                _mock_val_ser.set_model_mocks(cls, f'`{exc.name}`')
                if raise_errors:
                    raise exc from e

            if not raise_errors and not cls.__pydantic_fields_complete__:
                # No need to continue with schema gen, it is guaranteed to fail
                return False

            assert cls.__pydantic_fields_complete__

        return _model_construction.complete_model_class(
            cls,
            _config.ConfigWrapper(cls.model_config, check=False),
            raise_errors=raise_errors,
            ns_resolver=ns_resolver,
        )

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        """Validate a pydantic model instance.

        Args:
            obj: The object to validate.
            strict: Whether to enforce types strictly.
            from_attributes: Whether to extract data from object attributes.
            context: Additional context to pass to the validator.
            by_alias: Whether to use the field's alias when validating against the provided input data.
            by_name: Whether to use the field's name when validating against the provided input data.

        Raises:
            ValidationError: If the object could not be validated.

        Returns:
            The validated model instance.
        """
        # `__tracebackhide__` tells pytest and some other tools to omit this function from tracebacks
        __tracebackhide__ = True

        if by_alias is False and by_name is not True:
            raise PydanticUserError(
                'At least one of `by_alias` or `by_name` must be set to True.',
                code='validate-by-alias-and-name-false',
            )

        return cls.__pydantic_validator__.validate_python(
            obj, strict=strict, from_attributes=from_attributes, context=context, by_alias=by_alias, by_name=by_name
        )

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        """!!! abstract "Usage Documentation"
            [JSON Parsing](../concepts/json.md#json-parsing)

        Validate the given JSON data against the Pydantic model.

        Args:
            json_data: The JSON data to validate.
            strict: Whether to enforce types strictly.
            context: Extra variables to pass to the validator.
            by_alias: Whether to use the field's alias when validating against the provided input data.
            by_name: Whether to use the field's name when validating against the provided input data.

        Returns:
            The validated Pydantic model.

        Raises:
            ValidationError: If `json_data` is not a JSON string or the object could not be validated.
        """
        # `__tracebackhide__` tells pytest and some other tools to omit this function from tracebacks
        __tracebackhide__ = True

        if by_alias is False and by_name is not True:
            raise PydanticUserError(
                'At least one of `by_alias` or `by_name` must be set to True.',
                code='validate-by-alias-and-name-false',
            )

        return cls.__pydantic_validator__.validate_json(
            json_data, strict=strict, context=context, by_alias=by_alias, by_name=by_name
        )

    @classmethod
    def model_validate_strings(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        """Validate the given object with string data against the Pydantic model.

        Args:
            obj: The object containing string data to validate.
            strict: Whether to enforce types strictly.
            context: Extra variables to pass to the validator.
            by_alias: Whether to use the field's alias when validating against the provided input data.
            by_name: Whether to use the field's name when validating against the provided input data.

        Returns:
            The validated Pydantic model.
        """
        # `__tracebackhide__` tells pytest and some other tools to omit this function from tracebacks
        __tracebackhide__ = True

        if by_alias is False and by_name is not True:
            raise PydanticUserError(
                'At least one of `by_alias` or `by_name` must be set to True.',
                code='validate-by-alias-and-name-false',
            )

        return cls.__pydantic_validator__.validate_strings(
            obj, strict=strict, context=context, by_alias=by_alias, by_name=by_name
        )

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[BaseModel], handler: GetCoreSchemaHandler, /) -> CoreSchema:
        # This warning is only emitted when calling `super().__get_pydantic_core_schema__` from a model subclass.
        # In the generate schema logic, this method (`BaseModel.__get_pydantic_core_schema__`) is special cased to
        # *not* be called if not overridden.
        warnings.warn(
            'The `__get_pydantic_core_schema__` method of the `BaseModel` class is deprecated. If you are calling '
            '`super().__get_pydantic_core_schema__` when overriding the method on a Pydantic model, consider using '
            '`handler(source)` instead. However, note that overriding this method on models can lead to unexpected '
            'side effects.',
            PydanticDeprecatedSince211,
            stacklevel=2,
        )
        # Logic copied over from `GenerateSchema._model_schema`:
        schema = cls.__dict__.get('__pydantic_core_schema__')
        if schema is not None and not isinstance(schema, _mock_val_ser.MockCoreSchema):
            return cls.__pydantic_core_schema__

        return handler(source)

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
        /,
    ) -> JsonSchemaValue:
        """Hook into generating the model's JSON schema.

        Args:
            core_schema: A `pydantic-core` CoreSchema.
                You can ignore this argument and call the handler with a new CoreSchema,
                wrap this CoreSchema (`{'type': 'nullable', 'schema': current_schema}`),
                or just call the handler with the original schema.
            handler: Call into Pydantic's internal JSON schema generation.
                This will raise a `pydantic.errors.PydanticInvalidForJsonSchema` if JSON schema
                generation fails.
                Since this gets called by `BaseModel.model_json_schema` you can override the
                `schema_generator` argument to that function to change JSON schema generation globally
                for a type.

        Returns:
            A JSON schema, as a Python object.
        """
        return handler(core_schema)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """This is intended to behave just like `__init_subclass__`, but is called by `ModelMetaclass`
        only after the class is actually fully initialized. In particular, attributes like `model_fields` will
        be present when this is called.

        This is necessary because `__init_subclass__` will always be called by `type.__new__`,
        and it would require a prohibitively large refactor to the `ModelMetaclass` to ensure that
        `type.__new__` was called in such a manner that the class would already be sufficiently initialized.

        This will receive the same `kwargs` that would be passed to the standard `__init_subclass__`, namely,
        any kwargs passed to the class definition that aren't used internally by pydantic.

        Args:
            **kwargs: Any keyword arguments passed to the class definition that aren't used internally
                by pydantic.
        """
        pass

    def __class_getitem__(
        cls, typevar_values: type[Any] | tuple[type[Any], ...]
    ) -> type[BaseModel] | _forward_ref.PydanticRecursiveRef:
        cached = _generics.get_cached_generic_type_early(cls, typevar_values)
        if cached is not None:
            return cached

        if cls is BaseModel:
            raise TypeError('Type parameters should be placed on typing.Generic, not BaseModel')
        if not hasattr(cls, '__parameters__'):
            raise TypeError(f'{cls} cannot be parametrized because it does not inherit from typing.Generic')
        if not cls.__pydantic_generic_metadata__['parameters'] and typing.Generic not in cls.__bases__:
            raise TypeError(f'{cls} is not a generic class')

        if not isinstance(typevar_values, tuple):
            typevar_values = (typevar_values,)

        # For a model `class Model[T, U, V = int](BaseModel): ...` parametrized with `(str, bool)`,
        # this gives us `{T: str, U: bool, V: int}`:
        typevars_map = _generics.map_generic_model_arguments(cls, typevar_values)
        # We also update the provided args to use defaults values (`(str, bool)` becomes `(str, bool, int)`):
        typevar_values = tuple(v for v in typevars_map.values())

        if _utils.all_identical(typevars_map.keys(), typevars_map.values()) and typevars_map:
            submodel = cls  # if arguments are equal to parameters it's the same object
            _generics.set_cached_generic_type(cls, typevar_values, submodel)
        else:
            parent_args = cls.__pydantic_generic_metadata__['args']
            if not parent_args:
                args = typevar_values
            else:
                args = tuple(_generics.replace_types(arg, typevars_map) for arg in parent_args)

            origin = cls.__pydantic_generic_metadata__['origin'] or cls
            model_name = origin.model_parametrized_name(args)
            params = tuple(
                {param: None for param in _generics.iter_contained_typevars(typevars_map.values())}
            )  # use dict as ordered set

            with _generics.generic_recursion_self_type(origin, args) as maybe_self_type:
                cached = _generics.get_cached_generic_type_late(cls, typevar_values, origin, args)
                if cached is not None:
                    return cached

                if maybe_self_type is not None:
                    return maybe_self_type

                # Attempt to rebuild the origin in case new types have been defined
                try:
                    # depth 2 gets you above this __class_getitem__ call.
                    # Note that we explicitly provide the parent ns, otherwise
                    # `model_rebuild` will use the parent ns no matter if it is the ns of a module.
                    # We don't want this here, as this has unexpected effects when a model
                    # is being parametrized during a forward annotation evaluation.
                    parent_ns = _typing_extra.parent_frame_namespace(parent_depth=2) or {}
                    origin.model_rebuild(_types_namespace=parent_ns)
                except PydanticUndefinedAnnotation:
                    # It's okay if it fails, it just means there are still undefined types
                    # that could be evaluated later.
                    pass

                submodel = _generics.create_generic_submodel(model_name, origin, args, params)

                _generics.set_cached_generic_type(cls, typevar_values, submodel, origin, args)

        return submodel

    def __copy__(self) -> Self:
        """Returns a shallow copy of the model."""
        cls = type(self)
        m = cls.__new__(cls)
        _object_setattr(m, '__dict__', copy(self.__dict__))
        _object_setattr(m, '__pydantic_extra__', copy(self.__pydantic_extra__))
        _object_setattr(m, '__pydantic_fields_set__', copy(self.__pydantic_fields_set__))

        if not hasattr(self, '__pydantic_private__') or self.__pydantic_private__ is None:
            _object_setattr(m, '__pydantic_private__', None)
        else:
            _object_setattr(
                m,
                '__pydantic_private__',
                {k: v for k, v in self.__pydantic_private__.items() if v is not PydanticUndefined},
            )

        return m

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> Self:
        """Returns a deep copy of the model."""
        cls = type(self)
        m = cls.__new__(cls)
        _object_setattr(m, '__dict__', deepcopy(self.__dict__, memo=memo))
        _object_setattr(m, '__pydantic_extra__', deepcopy(self.__pydantic_extra__, memo=memo))
        # This next line doesn't need a deepcopy because __pydantic_fields_set__ is a set[str],
        # and attempting a deepcopy would be marginally slower.
        _object_setattr(m, '__pydantic_fields_set__', copy(self.__pydantic_fields_set__))

        if not hasattr(self, '__pydantic_private__') or self.__pydantic_private__ is None:
            _object_setattr(m, '__pydantic_private__', None)
        else:
            _object_setattr(
                m,
                '__pydantic_private__',
                deepcopy({k: v for k, v in self.__pydantic_private__.items() if v is not PydanticUndefined}, memo=memo),
            )

        return m

    if not TYPE_CHECKING:
        # We put `__getattr__` in a non-TYPE_CHECKING block because otherwise, mypy allows arbitrary attribute access
        # The same goes for __setattr__ and __delattr__, see: https://github.com/pydantic/pydantic/issues/8643

        def __getattr__(self, item: str) -> Any:
            private_attributes = object.__getattribute__(self, '__private_attributes__')
            if item in private_attributes:
                attribute = private_attributes[item]
                if hasattr(attribute, '__get__'):
                    return attribute.__get__(self, type(self))  # type: ignore

                try:
                    # Note: self.__pydantic_private__ cannot be None if self.__private_attributes__ has items
                    return self.__pydantic_private__[item]  # type: ignore
                except KeyError as exc:
                    raise AttributeError(f'{type(self).__name__!r} object has no attribute {item!r}') from exc
            else:
                # `__pydantic_extra__` can fail to be set if the model is not yet fully initialized.
                # See `BaseModel.__repr_args__` for more details
                try:
                    pydantic_extra = object.__getattribute__(self, '__pydantic_extra__')
                except AttributeError:
                    pydantic_extra = None

                if pydantic_extra:
                    try:
                        return pydantic_extra[item]
                    except KeyError as exc:
                        raise AttributeError(f'{type(self).__name__!r} object has no attribute {item!r}') from exc
                else:
                    if hasattr(self.__class__, item):
                        return super().__getattribute__(item)  # Raises AttributeError if appropriate
                    else:
                        # this is the current error
                        raise AttributeError(f'{type(self).__name__!r} object has no attribute {item!r}')

        def __setattr__(self, name: str, value: Any) -> None:
            if (setattr_handler := self.__pydantic_setattr_handlers__.get(name)) is not None:
                setattr_handler(self, name, value)
            # if None is returned from _setattr_handler, the attribute was set directly
            elif (setattr_handler := self._setattr_handler(name, value)) is not None:
                setattr_handler(self, name, value)  # call here to not memo on possibly unknown fields
                self.__pydantic_setattr_handlers__[name] = setattr_handler  # memoize the handler for faster access

        def _setattr_handler(self, name: str, value: Any) -> Callable[[BaseModel, str, Any], None] | None:
            """Get a handler for setting an attribute on the model instance.

            Returns:
                A handler for setting an attribute on the model instance. Used for memoization of the handler.
                Memoizing the handlers leads to a dramatic performance improvement in `__setattr__`
                Returns `None` when memoization is not safe, then the attribute is set directly.
            """
            cls = self.__class__
            if name in cls.__class_vars__:
                raise AttributeError(
                    f'{name!r} is a ClassVar of `{cls.__name__}` and cannot be set on an instance. '
                    f'If you want to set a value on the class, use `{cls.__name__}.{name} = value`.'
                )
            elif not _fields.is_valid_field_name(name):
                if (attribute := cls.__private_attributes__.get(name)) is not None:
                    if hasattr(attribute, '__set__'):
                        return lambda model, _name, val: attribute.__set__(model, val)
                    else:
                        return _SIMPLE_SETATTR_HANDLERS['private']
                else:
                    _object_setattr(self, name, value)
                    return None  # Can not return memoized handler with possibly freeform attr names

            attr = getattr(cls, name, None)
            # NOTE: We currently special case properties and `cached_property`, but we might need
            # to generalize this to all data/non-data descriptors at some point. For non-data descriptors
            # (such as `cached_property`), it isn't obvious though. `cached_property` caches the value
            # to the instance's `__dict__`, but other non-data descriptors might do things differently.
            if isinstance(attr, cached_property):
                return _SIMPLE_SETATTR_HANDLERS['cached_property']

            _check_frozen(cls, name, value)

            # We allow properties to be set only on non frozen models for now (to match dataclasses).
            # This can be changed if it ever gets requested.
            if isinstance(attr, property):
                return lambda model, _name, val: attr.__set__(model, val)
            elif cls.model_config.get('validate_assignment'):
                return _SIMPLE_SETATTR_HANDLERS['validate_assignment']
            elif name not in cls.__pydantic_fields__:
                if cls.model_config.get('extra') != 'allow':
                    # TODO - matching error
                    raise ValueError(f'"{cls.__name__}" object has no field "{name}"')
                elif attr is None:
                    # attribute does not exist, so put it in extra
                    self.__pydantic_extra__[name] = value
                    return None  # Can not return memoized handler with possibly freeform attr names
                else:
                    # attribute _does_ exist, and was not in extra, so update it
                    return _SIMPLE_SETATTR_HANDLERS['extra_known']
            else:
                return _SIMPLE_SETATTR_HANDLERS['model_field']

        def __delattr__(self, item: str) -> Any:
            cls = self.__class__

            if item in self.__private_attributes__:
                attribute = self.__private_attributes__[item]
                if hasattr(attribute, '__delete__'):
                    attribute.__delete__(self)  # type: ignore
                    return

                try:
                    # Note: self.__pydantic_private__ cannot be None if self.__private_attributes__ has items
                    del self.__pydantic_private__[item]  # type: ignore
                    return
                except KeyError as exc:
                    raise AttributeError(f'{cls.__name__!r} object has no attribute {item!r}') from exc

            # Allow cached properties to be deleted (even if the class is frozen):
            attr = getattr(cls, item, None)
            if isinstance(attr, cached_property):
                return object.__delattr__(self, item)

            _check_frozen(cls, name=item, value=None)

            if item in self.__pydantic_fields__:
                object.__delattr__(self, item)
            elif self.__pydantic_extra__ is not None and item in self.__pydantic_extra__:
                del self.__pydantic_extra__[item]
            else:
                try:
                    object.__delattr__(self, item)
                except AttributeError:
                    raise AttributeError(f'{type(self).__name__!r} object has no attribute {item!r}')

        # Because we make use of `@dataclass_transform()`, `__replace__` is already synthesized by
        # type checkers, so we define the implementation in this `if not TYPE_CHECKING:` block:
        def __replace__(self, **changes: Any) -> Self:
            return self.model_copy(update=changes)

    def __getstate__(self) -> dict[Any, Any]:
        private = self.__pydantic_private__
        if private:
            private = {k: v for k, v in private.items() if v is not PydanticUndefined}
        return {
            '__dict__': self.__dict__,
            '__pydantic_extra__': self.__pydantic_extra__,
            '__pydantic_fields_set__': self.__pydantic_fields_set__,
            '__pydantic_private__': private,
        }

    def __setstate__(self, state: dict[Any, Any]) -> None:
        _object_setattr(self, '__pydantic_fields_set__', state.get('__pydantic_fields_set__', {}))
        _object_setattr(self, '__pydantic_extra__', state.get('__pydantic_extra__', {}))
        _object_setattr(self, '__pydantic_private__', state.get('__pydantic_private__', {}))
        _object_setattr(self, '__dict__', state.get('__dict__', {}))

    if not TYPE_CHECKING:

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, BaseModel):
                # When comparing instances of generic types for equality, as long as all field values are equal,
                # only require their generic origin types to be equal, rather than exact type equality.
                # This prevents headaches like MyGeneric(x=1) != MyGeneric[Any](x=1).
                self_type = self.__pydantic_generic_metadata__['origin'] or self.__class__
                other_type = other.__pydantic_generic_metadata__['origin'] or other.__class__

                # Perform common checks first
                if not (
                    self_type == other_type
                    and getattr(self, '__pydantic_private__', None) == getattr(other, '__pydantic_private__', None)
                    and self.__pydantic_extra__ == other.__pydantic_extra__
                ):
                    return False

                # We only want to compare pydantic fields but ignoring fields is costly.
                # We'll perform a fast check first, and fallback only when needed
                # See GH-7444 and GH-7825 for rationale and a performance benchmark

                # First, do the fast (and sometimes faulty) __dict__ comparison
                if self.__dict__ == other.__dict__:
                    # If the check above passes, then pydantic fields are equal, we can return early
                    return True

                # We don't want to trigger unnecessary costly filtering of __dict__ on all unequal objects, so we return
                # early if there are no keys to ignore (we would just return False later on anyway)
                model_fields = type(self).__pydantic_fields__.keys()
                if self.__dict__.keys() <= model_fields and other.__dict__.keys() <= model_fields:
                    return False

                # If we reach here, there are non-pydantic-fields keys, mapped to unequal values, that we need to ignore
                # Resort to costly filtering of the __dict__ objects
                # We use operator.itemgetter because it is much faster than dict comprehensions
                # NOTE: Contrary to standard python class and instances, when the Model class has a default value for an
                # attribute and the model instance doesn't have a corresponding attribute, accessing the missing attribute
                # raises an error in BaseModel.__getattr__ instead of returning the class attribute
                # So we can use operator.itemgetter() instead of operator.attrgetter()
                getter = operator.itemgetter(*model_fields) if model_fields else lambda _: _utils._SENTINEL
                try:
                    return getter(self.__dict__) == getter(other.__dict__)
                except KeyError:
                    # In rare cases (such as when using the deprecated BaseModel.copy() method),
                    # the __dict__ may not contain all model fields, which is how we can get here.
                    # getter(self.__dict__) is much faster than any 'safe' method that accounts
                    # for missing keys, and wrapping it in a `try` doesn't slow things down much
                    # in the common case.
                    self_fields_proxy = _utils.SafeGetItemProxy(self.__dict__)
                    other_fields_proxy = _utils.SafeGetItemProxy(other.__dict__)
                    return getter(self_fields_proxy) == getter(other_fields_proxy)

            # other instance is not a BaseModel
            else:
                return NotImplemented  # delegate to the other item in the comparison

    if TYPE_CHECKING:
        # We put `__init_subclass__` in a TYPE_CHECKING block because, even though we want the type-checking benefits
        # described in the signature of `__init_subclass__` below, we don't want to modify the default behavior of
        # subclass initialization.

        def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]):
            """This signature is included purely to help type-checkers check arguments to class declaration, which
            provides a way to conveniently set model_config key/value pairs.

            ```python
            from pydantic import BaseModel

            class MyModel(BaseModel, extra='allow'): ...
            ```

            However, this may be deceiving, since the _actual_ calls to `__init_subclass__` will not receive any
            of the config arguments, and will only receive any keyword arguments passed during class initialization
            that are _not_ expected keys in ConfigDict. (This is due to the way `ModelMetaclass.__new__` works.)

            Args:
                **kwargs: Keyword arguments passed to the class definition, which set model_config

            Note:
                You may want to override `__pydantic_init_subclass__` instead, which behaves similarly but is called
                *after* the class is fully initialized.
            """

    def __iter__(self) -> TupleGenerator:
        """So `dict(model)` works."""
        yield from [(k, v) for (k, v) in self.__dict__.items() if not k.startswith('_')]
        extra = self.__pydantic_extra__
        if extra:
            yield from extra.items()

    def __repr__(self) -> str:
        return f'{self.__repr_name__()}({self.__repr_str__(", ")})'

    def __repr_args__(self) -> _repr.ReprArgs:
        # Eagerly create the repr of computed fields, as this may trigger access of cached properties and as such
        # modify the instance's `__dict__`. If we don't do it now, it could happen when iterating over the `__dict__`
        # below if the instance happens to be referenced in a field, and would modify the `__dict__` size *during* iteration.
        computed_fields_repr_args = [
            (k, getattr(self, k)) for k, v in self.__pydantic_computed_fields__.items() if v.repr
        ]

        for k, v in self.__dict__.items():
            field = self.__pydantic_fields__.get(k)
            if field and field.repr:
                if v is not self:
                    yield k, v
                else:
                    yield k, self.__repr_recursion__(v)
        # `__pydantic_extra__` can fail to be set if the model is not yet fully initialized.
        # This can happen if a `ValidationError` is raised during initialization and the instance's
        # repr is generated as part of the exception handling. Therefore, we use `getattr` here
        # with a fallback, even though the type hints indicate the attribute will always be present.
        try:
            pydantic_extra = object.__getattribute__(self, '__pydantic_extra__')
        except AttributeError:
            pydantic_extra = None

        if pydantic_extra is not None:
            yield from ((k, v) for k, v in pydantic_extra.items())
        yield from computed_fields_repr_args

    # take logic from `_repr.Representation` without the side effects of inheritance, see #5740
    __repr_name__ = _repr.Representation.__repr_name__
    __repr_recursion__ = _repr.Representation.__repr_recursion__
    __repr_str__ = _repr.Representation.__repr_str__
    __pretty__ = _repr.Representation.__pretty__
    __rich_repr__ = _repr.Representation.__rich_repr__

    def __str__(self) -> str:
        return self.__repr_str__(' ')

    # ##### Deprecated methods from v1 #####
    @property
    @typing_extensions.deprecated(
        'The `__fields__` attribute is deprecated, use `model_fields` instead.', category=None
    )
    def __fields__(self) -> dict[str, FieldInfo]:
        warnings.warn(
            'The `__fields__` attribute is deprecated, use `model_fields` instead.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        return getattr(type(self), '__pydantic_fields__', {})

    @property
    @typing_extensions.deprecated(
        'The `__fields_set__` attribute is deprecated, use `model_fields_set` instead.',
        category=None,
    )
    def __fields_set__(self) -> set[str]:
        warnings.warn(
            'The `__fields_set__` attribute is deprecated, use `model_fields_set` instead.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        return self.__pydantic_fields_set__

    @typing_extensions.deprecated('The `dict` method is deprecated; use `model_dump` instead.', category=None)
    def dict(  # noqa: D102
        self,
        *,
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> Dict[str, Any]:  # noqa UP006
        warnings.warn(
            'The `dict` method is deprecated; use `model_dump` instead.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        return self.model_dump(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

    @typing_extensions.deprecated('The `json` method is deprecated; use `model_dump_json` instead.', category=None)
    def json(  # noqa: D102
        self,
        *,
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        encoder: Callable[[Any], Any] | None = PydanticUndefined,  # type: ignore[assignment]
        models_as_dict: bool = PydanticUndefined,  # type: ignore[assignment]
        **dumps_kwargs: Any,
    ) -> str:
        warnings.warn(
            'The `json` method is deprecated; use `model_dump_json` instead.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        if encoder is not PydanticUndefined:
            raise TypeError('The `encoder` argument is no longer supported; use field serializers instead.')
        if models_as_dict is not PydanticUndefined:
            raise TypeError('The `models_as_dict` argument is no longer supported; use a model serializer instead.')
        if dumps_kwargs:
            raise TypeError('`dumps_kwargs` keyword arguments are no longer supported.')
        return self.model_dump_json(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

    @classmethod
    @typing_extensions.deprecated('The `parse_obj` method is deprecated; use `model_validate` instead.', category=None)
    def parse_obj(cls, obj: Any) -> Self:  # noqa: D102
        warnings.warn(
            'The `parse_obj` method is deprecated; use `model_validate` instead.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        return cls.model_validate(obj)

    @classmethod
    @typing_extensions.deprecated(
        'The `parse_raw` method is deprecated; if your data is JSON use `model_validate_json`, '
        'otherwise load the data then use `model_validate` instead.',
        category=None,
    )
    def parse_raw(  # noqa: D102
        cls,
        b: str | bytes,
        *,
        content_type: str | None = None,
        encoding: str = 'utf8',
        proto: DeprecatedParseProtocol | None = None,
        allow_pickle: bool = False,
    ) -> Self:  # pragma: no cover
        warnings.warn(
            'The `parse_raw` method is deprecated; if your data is JSON use `model_validate_json`, '
            'otherwise load the data then use `model_validate` instead.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        from .deprecated import parse

        try:
            obj = parse.load_str_bytes(
                b,
                proto=proto,
                content_type=content_type,
                encoding=encoding,
                allow_pickle=allow_pickle,
            )
        except (ValueError, TypeError) as exc:
            import json

            # try to match V1
            if isinstance(exc, UnicodeDecodeError):
                type_str = 'value_error.unicodedecode'
            elif isinstance(exc, json.JSONDecodeError):
                type_str = 'value_error.jsondecode'
            elif isinstance(exc, ValueError):
                type_str = 'value_error'
            else:
                type_str = 'type_error'

            # ctx is missing here, but since we've added `input` to the error, we're not pretending it's the same
            error: pydantic_core.InitErrorDetails = {
                # The type: ignore on the next line is to ignore the requirement of LiteralString
                'type': pydantic_core.PydanticCustomError(type_str, str(exc)),  # type: ignore
                'loc': ('__root__',),
                'input': b,
            }
            raise pydantic_core.ValidationError.from_exception_data(cls.__name__, [error])
        return cls.model_validate(obj)

    @classmethod
    @typing_extensions.deprecated(
        'The `parse_file` method is deprecated; load the data from file, then if your data is JSON '
        'use `model_validate_json`, otherwise `model_validate` instead.',
        category=None,
    )
    def parse_file(  # noqa: D102
        cls,
        path: str | Path,
        *,
        content_type: str | None = None,
        encoding: str = 'utf8',
        proto: DeprecatedParseProtocol | None = None,
        allow_pickle: bool = False,
    ) -> Self:
        warnings.warn(
            'The `parse_file` method is deprecated; load the data from file, then if your data is JSON '
            'use `model_validate_json`, otherwise `model_validate` instead.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        from .deprecated import parse

        obj = parse.load_file(
            path,
            proto=proto,
            content_type=content_type,
            encoding=encoding,
            allow_pickle=allow_pickle,
        )
        return cls.parse_obj(obj)

    @classmethod
    @typing_extensions.deprecated(
        'The `from_orm` method is deprecated; set '
        "`model_config['from_attributes']=True` and use `model_validate` instead.",
        category=None,
    )
    def from_orm(cls, obj: Any) -> Self:  # noqa: D102
        warnings.warn(
            'The `from_orm` method is deprecated; set '
            "`model_config['from_attributes']=True` and use `model_validate` instead.",
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        if not cls.model_config.get('from_attributes', None):
            raise PydanticUserError(
                'You must set the config attribute `from_attributes=True` to use from_orm', code=None
            )
        return cls.model_validate(obj)

    @classmethod
    @typing_extensions.deprecated('The `construct` method is deprecated; use `model_construct` instead.', category=None)
    def construct(cls, _fields_set: set[str] | None = None, **values: Any) -> Self:  # noqa: D102
        warnings.warn(
            'The `construct` method is deprecated; use `model_construct` instead.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        return cls.model_construct(_fields_set=_fields_set, **values)

    @typing_extensions.deprecated(
        'The `copy` method is deprecated; use `model_copy` instead. '
        'See the docstring of `BaseModel.copy` for details about how to handle `include` and `exclude`.',
        category=None,
    )
    def copy(
        self,
        *,
        include: AbstractSetIntStr | MappingIntStrAny | None = None,
        exclude: AbstractSetIntStr | MappingIntStrAny | None = None,
        update: Dict[str, Any] | None = None,  # noqa UP006
        deep: bool = False,
    ) -> Self:  # pragma: no cover
        """Returns a copy of the model.

        !!! warning "Deprecated"
            This method is now deprecated; use `model_copy` instead.

        If you need `include` or `exclude`, use:

        ```python {test="skip" lint="skip"}
        data = self.model_dump(include=include, exclude=exclude, round_trip=True)
        data = {**data, **(update or {})}
        copied = self.model_validate(data)
        ```

        Args:
            include: Optional set or mapping specifying which fields to include in the copied model.
            exclude: Optional set or mapping specifying which fields to exclude in the copied model.
            update: Optional dictionary of field-value pairs to override field values in the copied model.
            deep: If True, the values of fields that are Pydantic models will be deep-copied.

        Returns:
            A copy of the model with included, excluded and updated fields as specified.
        """
        warnings.warn(
            'The `copy` method is deprecated; use `model_copy` instead. '
            'See the docstring of `BaseModel.copy` for details about how to handle `include` and `exclude`.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        from .deprecated import copy_internals

        values = dict(
            copy_internals._iter(
                self, to_dict=False, by_alias=False, include=include, exclude=exclude, exclude_unset=False
            ),
            **(update or {}),
        )
        if self.__pydantic_private__ is None:
            private = None
        else:
            private = {k: v for k, v in self.__pydantic_private__.items() if v is not PydanticUndefined}

        if self.__pydantic_extra__ is None:
            extra: dict[str, Any] | None = None
        else:
            extra = self.__pydantic_extra__.copy()
            for k in list(self.__pydantic_extra__):
                if k not in values:  # k was in the exclude
                    extra.pop(k)
            for k in list(values):
                if k in self.__pydantic_extra__:  # k must have come from extra
                    extra[k] = values.pop(k)

        # new `__pydantic_fields_set__` can have unset optional fields with a set value in `update` kwarg
        if update:
            fields_set = self.__pydantic_fields_set__ | update.keys()
        else:
            fields_set = set(self.__pydantic_fields_set__)

        # removing excluded fields from `__pydantic_fields_set__`
        if exclude:
            fields_set -= set(exclude)

        return copy_internals._copy_and_set_values(self, values, fields_set, extra, private, deep=deep)

    @classmethod
    @typing_extensions.deprecated('The `schema` method is deprecated; use `model_json_schema` instead.', category=None)
    def schema(  # noqa: D102
        cls, by_alias: bool = True, ref_template: str = DEFAULT_REF_TEMPLATE
    ) -> Dict[str, Any]:  # noqa UP006
        warnings.warn(
            'The `schema` method is deprecated; use `model_json_schema` instead.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        return cls.model_json_schema(by_alias=by_alias, ref_template=ref_template)

    @classmethod
    @typing_extensions.deprecated(
        'The `schema_json` method is deprecated; use `model_json_schema` and json.dumps instead.',
        category=None,
    )
    def schema_json(  # noqa: D102
        cls, *, by_alias: bool = True, ref_template: str = DEFAULT_REF_TEMPLATE, **dumps_kwargs: Any
    ) -> str:  # pragma: no cover
        warnings.warn(
            'The `schema_json` method is deprecated; use `model_json_schema` and json.dumps instead.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        import json

        from .deprecated.json import pydantic_encoder

        return json.dumps(
            cls.model_json_schema(by_alias=by_alias, ref_template=ref_template),
            default=pydantic_encoder,
            **dumps_kwargs,
        )

    @classmethod
    @typing_extensions.deprecated('The `validate` method is deprecated; use `model_validate` instead.', category=None)
    def validate(cls, value: Any) -> Self:  # noqa: D102
        warnings.warn(
            'The `validate` method is deprecated; use `model_validate` instead.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        return cls.model_validate(value)

    @classmethod
    @typing_extensions.deprecated(
        'The `update_forward_refs` method is deprecated; use `model_rebuild` instead.',
        category=None,
    )
    def update_forward_refs(cls, **localns: Any) -> None:  # noqa: D102
        warnings.warn(
            'The `update_forward_refs` method is deprecated; use `model_rebuild` instead.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        if localns:  # pragma: no cover
            raise TypeError('`localns` arguments are not longer accepted.')
        cls.model_rebuild(force=True)

    @typing_extensions.deprecated(
        'The private method `_iter` will be removed and should no longer be used.', category=None
    )
    def _iter(self, *args: Any, **kwargs: Any) -> Any:
        warnings.warn(
            'The private method `_iter` will be removed and should no longer be used.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        from .deprecated import copy_internals

        return copy_internals._iter(self, *args, **kwargs)

    @typing_extensions.deprecated(
        'The private method `_copy_and_set_values` will be removed and should no longer be used.',
        category=None,
    )
    def _copy_and_set_values(self, *args: Any, **kwargs: Any) -> Any:
        warnings.warn(
            'The private method `_copy_and_set_values` will be removed and should no longer be used.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        from .deprecated import copy_internals

        return copy_internals._copy_and_set_values(self, *args, **kwargs)

    @classmethod
    @typing_extensions.deprecated(
        'The private method `_get_value` will be removed and should no longer be used.',
        category=None,
    )
    def _get_value(cls, *args: Any, **kwargs: Any) -> Any:
        warnings.warn(
            'The private method `_get_value` will be removed and should no longer be used.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        from .deprecated import copy_internals

        return copy_internals._get_value(cls, *args, **kwargs)

    @typing_extensions.deprecated(
        'The private method `_calculate_keys` will be removed and should no longer be used.',
        category=None,
    )
    def _calculate_keys(self, *args: Any, **kwargs: Any) -> Any:
        warnings.warn(
            'The private method `_calculate_keys` will be removed and should no longer be used.',
            category=PydanticDeprecatedSince20,
            stacklevel=2,
        )
        from .deprecated import copy_internals

        return copy_internals._calculate_keys(self, *args, **kwargs)


ModelT = TypeVar('ModelT', bound=BaseModel)


@overload
def create_model(
    model_name: str,
    /,
    *,
    __config__: ConfigDict | None = None,
    __doc__: str | None = None,
    __base__: None = None,
    __module__: str = __name__,
    __validators__: dict[str, Callable[..., Any]] | None = None,
    __cls_kwargs__: dict[str, Any] | None = None,
    **field_definitions: Any | tuple[str, Any],
) -> type[BaseModel]: ...


@overload
def create_model(
    model_name: str,
    /,
    *,
    __config__: ConfigDict | None = None,
    __doc__: str | None = None,
    __base__: type[ModelT] | tuple[type[ModelT], ...],
    __module__: str = __name__,
    __validators__: dict[str, Callable[..., Any]] | None = None,
    __cls_kwargs__: dict[str, Any] | None = None,
    **field_definitions: Any | tuple[str, Any],
) -> type[ModelT]: ...


def create_model(  # noqa: C901
    model_name: str,
    /,
    *,
    __config__: ConfigDict | None = None,
    __doc__: str | None = None,
    __base__: type[ModelT] | tuple[type[ModelT], ...] | None = None,
    __module__: str | None = None,
    __validators__: dict[str, Callable[..., Any]] | None = None,
    __cls_kwargs__: dict[str, Any] | None = None,
    # TODO PEP 747: replace `Any` by the TypeForm:
    **field_definitions: Any | tuple[str, Any],
) -> type[ModelT]:
    """!!! abstract "Usage Documentation"
        [Dynamic Model Creation](../concepts/models.md#dynamic-model-creation)

    Dynamically creates and returns a new Pydantic model, in other words, `create_model` dynamically creates a
    subclass of [`BaseModel`][pydantic.BaseModel].

    Args:
        model_name: The name of the newly created model.
        __config__: The configuration of the new model.
        __doc__: The docstring of the new model.
        __base__: The base class or classes for the new model.
        __module__: The name of the module that the model belongs to;
            if `None`, the value is taken from `sys._getframe(1)`
        __validators__: A dictionary of methods that validate fields. The keys are the names of the validation methods to
            be added to the model, and the values are the validation methods themselves. You can read more about functional
            validators [here](https://docs.pydantic.dev/2.9/concepts/validators/#field-validators).
        __cls_kwargs__: A dictionary of keyword arguments for class creation, such as `metaclass`.
        **field_definitions: Field definitions of the new model. Either:

            - a single element, representing the type annotation of the field.
            - a two-tuple, the first element being the type and the second element the assigned value
              (either a default or the [`Field()`][pydantic.Field] function).

    Returns:
        The new [model][pydantic.BaseModel].

    Raises:
        PydanticUserError: If `__base__` and `__config__` are both passed.
    """
    if __base__ is None:
        __base__ = (cast('type[ModelT]', BaseModel),)
    elif not isinstance(__base__, tuple):
        __base__ = (__base__,)

    __cls_kwargs__ = __cls_kwargs__ or {}

    fields: dict[str, Any] = {}
    annotations: dict[str, Any] = {}

    for f_name, f_def in field_definitions.items():
        if isinstance(f_def, tuple):
            if len(f_def) != 2:
                raise PydanticUserError(
                    f'Field definition for {f_name!r} should a single element representing the type or a two-tuple, the first element '
                    'being the type and the second element the assigned value (either a default or the `Field()` function).',
                    code='create-model-field-definitions',
                )

            annotations[f_name] = f_def[0]
            fields[f_name] = f_def[1]
        else:
            annotations[f_name] = f_def

    if __module__ is None:
        f = sys._getframe(1)
        __module__ = f.f_globals['__name__']

    namespace: dict[str, Any] = {'__annotations__': annotations, '__module__': __module__}
    if __doc__:
        namespace.update({'__doc__': __doc__})
    if __validators__:
        namespace.update(__validators__)
    namespace.update(fields)
    if __config__:
        namespace['model_config'] = __config__
    resolved_bases = types.resolve_bases(__base__)
    meta, ns, kwds = types.prepare_class(model_name, resolved_bases, kwds=__cls_kwargs__)
    if resolved_bases is not __base__:
        ns['__orig_bases__'] = __base__
    namespace.update(ns)

    return meta(
        model_name,
        resolved_bases,
        namespace,
        __pydantic_reset_parent_namespace__=False,
        _create_model_module=__module__,
        **kwds,
    )


__getattr__ = getattr_migration(__name__)

# === NexusCore/openenv\Lib\site-packages\numpy\_core\multiarray.py ===
"""
Create the numpy._core.multiarray namespace for backward compatibility.
In v1.16 the multiarray and umath c-extension modules were merged into
a single _multiarray_umath extension module. So we replicate the old
namespace by importing from the extension module.

"""

import functools

from . import _multiarray_umath, overrides
from ._multiarray_umath import *  # noqa: F403

# These imports are needed for backward compatibility,
# do not change them. issue gh-15518
# _get_ndarray_c_version is semi-public, on purpose not added to __all__
from ._multiarray_umath import (  # noqa: F401
    _ARRAY_API,
    _flagdict,
    _get_madvise_hugepage,
    _get_ndarray_c_version,
    _monotonicity,
    _place,
    _reconstruct,
    _set_madvise_hugepage,
    _vec_string,
    from_dlpack,
)

__all__ = [
    '_ARRAY_API', 'ALLOW_THREADS', 'BUFSIZE', 'CLIP', 'DATETIMEUNITS',
    'ITEM_HASOBJECT', 'ITEM_IS_POINTER', 'LIST_PICKLE', 'MAXDIMS',
    'MAY_SHARE_BOUNDS', 'MAY_SHARE_EXACT', 'NEEDS_INIT', 'NEEDS_PYAPI',
    'RAISE', 'USE_GETITEM', 'USE_SETITEM', 'WRAP',
    '_flagdict', 'from_dlpack', '_place', '_reconstruct', '_vec_string',
    '_monotonicity', 'add_docstring', 'arange', 'array', 'asarray',
    'asanyarray', 'ascontiguousarray', 'asfortranarray', 'bincount',
    'broadcast', 'busday_count', 'busday_offset', 'busdaycalendar', 'can_cast',
    'compare_chararrays', 'concatenate', 'copyto', 'correlate', 'correlate2',
    'count_nonzero', 'c_einsum', 'datetime_as_string', 'datetime_data',
    'dot', 'dragon4_positional', 'dragon4_scientific', 'dtype',
    'empty', 'empty_like', 'error', 'flagsobj', 'flatiter', 'format_longfloat',
    'frombuffer', 'fromfile', 'fromiter', 'fromstring',
    'get_handler_name', 'get_handler_version', 'inner', 'interp',
    'interp_complex', 'is_busday', 'lexsort', 'matmul', 'vecdot',
    'may_share_memory', 'min_scalar_type', 'ndarray', 'nditer', 'nested_iters',
    'normalize_axis_index', 'packbits', 'promote_types', 'putmask',
    'ravel_multi_index', 'result_type', 'scalar', 'set_datetimeparse_function',
    'set_typeDict', 'shares_memory', 'typeinfo',
    'unpackbits', 'unravel_index', 'vdot', 'where', 'zeros']

# For backward compatibility, make sure pickle imports
# these functions from here
_reconstruct.__module__ = 'numpy._core.multiarray'
scalar.__module__ = 'numpy._core.multiarray'


from_dlpack.__module__ = 'numpy'
arange.__module__ = 'numpy'
array.__module__ = 'numpy'
asarray.__module__ = 'numpy'
asanyarray.__module__ = 'numpy'
ascontiguousarray.__module__ = 'numpy'
asfortranarray.__module__ = 'numpy'
datetime_data.__module__ = 'numpy'
empty.__module__ = 'numpy'
frombuffer.__module__ = 'numpy'
fromfile.__module__ = 'numpy'
fromiter.__module__ = 'numpy'
frompyfunc.__module__ = 'numpy'
fromstring.__module__ = 'numpy'
may_share_memory.__module__ = 'numpy'
nested_iters.__module__ = 'numpy'
promote_types.__module__ = 'numpy'
zeros.__module__ = 'numpy'
normalize_axis_index.__module__ = 'numpy.lib.array_utils'
add_docstring.__module__ = 'numpy.lib'
compare_chararrays.__module__ = 'numpy.char'


def _override___module__():
    namespace_names = globals()
    for ufunc_name in [
        'absolute', 'arccos', 'arccosh', 'add', 'arcsin', 'arcsinh', 'arctan',
        'arctan2', 'arctanh', 'bitwise_and', 'bitwise_count', 'invert',
        'left_shift', 'bitwise_or', 'right_shift', 'bitwise_xor', 'cbrt',
        'ceil', 'conjugate', 'copysign', 'cos', 'cosh', 'deg2rad', 'degrees',
        'divide', 'divmod', 'equal', 'exp', 'exp2', 'expm1', 'fabs',
        'float_power', 'floor', 'floor_divide', 'fmax', 'fmin', 'fmod',
        'frexp', 'gcd', 'greater', 'greater_equal', 'heaviside', 'hypot',
        'isfinite', 'isinf', 'isnan', 'isnat', 'lcm', 'ldexp', 'less',
        'less_equal', 'log', 'log10', 'log1p', 'log2', 'logaddexp',
        'logaddexp2', 'logical_and', 'logical_not', 'logical_or',
        'logical_xor', 'matmul', 'matvec', 'maximum', 'minimum', 'remainder',
        'modf', 'multiply', 'negative', 'nextafter', 'not_equal', 'positive',
        'power', 'rad2deg', 'radians', 'reciprocal', 'rint', 'sign', 'signbit',
        'sin', 'sinh', 'spacing', 'sqrt', 'square', 'subtract', 'tan', 'tanh',
        'trunc', 'vecdot', 'vecmat',
    ]:
        ufunc = namespace_names[ufunc_name]
        ufunc.__module__ = "numpy"
        ufunc.__qualname__ = ufunc_name


_override___module__()


# We can't verify dispatcher signatures because NumPy's C functions don't
# support introspection.
array_function_from_c_func_and_dispatcher = functools.partial(
    overrides.array_function_from_dispatcher,
    module='numpy', docs_from_dispatcher=True, verify=False)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.empty_like)
def empty_like(
    prototype, dtype=None, order=None, subok=None, shape=None, *, device=None
):
    """
    empty_like(prototype, dtype=None, order='K', subok=True, shape=None, *,
               device=None)

    Return a new array with the same shape and type as a given array.

    Parameters
    ----------
    prototype : array_like
        The shape and data-type of `prototype` define these same attributes
        of the returned array.
    dtype : data-type, optional
        Overrides the data type of the result.
    order : {'C', 'F', 'A', or 'K'}, optional
        Overrides the memory layout of the result. 'C' means C-order,
        'F' means F-order, 'A' means 'F' if `prototype` is Fortran
        contiguous, 'C' otherwise. 'K' means match the layout of `prototype`
        as closely as possible.
    subok : bool, optional.
        If True, then the newly created array will use the sub-class
        type of `prototype`, otherwise it will be a base-class array. Defaults
        to True.
    shape : int or sequence of ints, optional.
        Overrides the shape of the result. If order='K' and the number of
        dimensions is unchanged, will try to keep order, otherwise,
        order='C' is implied.
    device : str, optional
        The device on which to place the created array. Default: None.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0

    Returns
    -------
    out : ndarray
        Array of uninitialized (arbitrary) data with the same
        shape and type as `prototype`.

    See Also
    --------
    ones_like : Return an array of ones with shape and type of input.
    zeros_like : Return an array of zeros with shape and type of input.
    full_like : Return a new array with shape of input filled with value.
    empty : Return a new uninitialized array.

    Notes
    -----
    Unlike other array creation functions (e.g. `zeros_like`, `ones_like`,
    `full_like`), `empty_like` does not initialize the values of the array,
    and may therefore be marginally faster. However, the values stored in the
    newly allocated array are arbitrary. For reproducible behavior, be sure
    to set each element of the array before reading.

    Examples
    --------
    >>> import numpy as np
    >>> a = ([1,2,3], [4,5,6])                         # a is array-like
    >>> np.empty_like(a)
    array([[-1073741821, -1073741821,           3],    # uninitialized
           [          0,           0, -1073741821]])
    >>> a = np.array([[1., 2., 3.],[4.,5.,6.]])
    >>> np.empty_like(a)
    array([[ -2.00000715e+000,   1.48219694e-323,  -2.00000572e+000], # uninitialized
           [  4.38791518e-305,  -2.00000715e+000,   4.17269252e-309]])

    """
    return (prototype,)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.concatenate)
def concatenate(arrays, axis=None, out=None, *, dtype=None, casting=None):
    """
    concatenate(
        (a1, a2, ...),
        axis=0,
        out=None,
        dtype=None,
        casting="same_kind"
    )

    Join a sequence of arrays along an existing axis.

    Parameters
    ----------
    a1, a2, ... : sequence of array_like
        The arrays must have the same shape, except in the dimension
        corresponding to `axis` (the first, by default).
    axis : int, optional
        The axis along which the arrays will be joined.  If axis is None,
        arrays are flattened before use.  Default is 0.
    out : ndarray, optional
        If provided, the destination to place the result. The shape must be
        correct, matching that of what concatenate would have returned if no
        out argument were specified.
    dtype : str or dtype
        If provided, the destination array will have this dtype. Cannot be
        provided together with `out`.

        .. versionadded:: 1.20.0

    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        Controls what kind of data casting may occur. Defaults to 'same_kind'.
        For a description of the options, please see :term:`casting`.

        .. versionadded:: 1.20.0

    Returns
    -------
    res : ndarray
        The concatenated array.

    See Also
    --------
    ma.concatenate : Concatenate function that preserves input masks.
    array_split : Split an array into multiple sub-arrays of equal or
                  near-equal size.
    split : Split array into a list of multiple sub-arrays of equal size.
    hsplit : Split array into multiple sub-arrays horizontally (column wise).
    vsplit : Split array into multiple sub-arrays vertically (row wise).
    dsplit : Split array into multiple sub-arrays along the 3rd axis (depth).
    stack : Stack a sequence of arrays along a new axis.
    block : Assemble arrays from blocks.
    hstack : Stack arrays in sequence horizontally (column wise).
    vstack : Stack arrays in sequence vertically (row wise).
    dstack : Stack arrays in sequence depth wise (along third dimension).
    column_stack : Stack 1-D arrays as columns into a 2-D array.

    Notes
    -----
    When one or more of the arrays to be concatenated is a MaskedArray,
    this function will return a MaskedArray object instead of an ndarray,
    but the input masks are *not* preserved. In cases where a MaskedArray
    is expected as input, use the ma.concatenate function from the masked
    array module instead.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> b = np.array([[5, 6]])
    >>> np.concatenate((a, b), axis=0)
    array([[1, 2],
           [3, 4],
           [5, 6]])
    >>> np.concatenate((a, b.T), axis=1)
    array([[1, 2, 5],
           [3, 4, 6]])
    >>> np.concatenate((a, b), axis=None)
    array([1, 2, 3, 4, 5, 6])

    This function will not preserve masking of MaskedArray inputs.

    >>> a = np.ma.arange(3)
    >>> a[1] = np.ma.masked
    >>> b = np.arange(2, 5)
    >>> a
    masked_array(data=[0, --, 2],
                 mask=[False,  True, False],
           fill_value=999999)
    >>> b
    array([2, 3, 4])
    >>> np.concatenate([a, b])
    masked_array(data=[0, 1, 2, 2, 3, 4],
                 mask=False,
           fill_value=999999)
    >>> np.ma.concatenate([a, b])
    masked_array(data=[0, --, 2, 2, 3, 4],
                 mask=[False,  True, False, False, False, False],
           fill_value=999999)

    """
    if out is not None:
        # optimize for the typical case where only arrays is provided
        arrays = list(arrays)
        arrays.append(out)
    return arrays


@array_function_from_c_func_and_dispatcher(_multiarray_umath.inner)
def inner(a, b):
    """
    inner(a, b, /)

    Inner product of two arrays.

    Ordinary inner product of vectors for 1-D arrays (without complex
    conjugation), in higher dimensions a sum product over the last axes.

    Parameters
    ----------
    a, b : array_like
        If `a` and `b` are nonscalar, their last dimensions must match.

    Returns
    -------
    out : ndarray
        If `a` and `b` are both
        scalars or both 1-D arrays then a scalar is returned; otherwise
        an array is returned.
        ``out.shape = (*a.shape[:-1], *b.shape[:-1])``

    Raises
    ------
    ValueError
        If both `a` and `b` are nonscalar and their last dimensions have
        different sizes.

    See Also
    --------
    tensordot : Sum products over arbitrary axes.
    dot : Generalised matrix product, using second last dimension of `b`.
    vecdot : Vector dot product of two arrays.
    einsum : Einstein summation convention.

    Notes
    -----
    For vectors (1-D arrays) it computes the ordinary inner-product::

        np.inner(a, b) = sum(a[:]*b[:])

    More generally, if ``ndim(a) = r > 0`` and ``ndim(b) = s > 0``::

        np.inner(a, b) = np.tensordot(a, b, axes=(-1,-1))

    or explicitly::

        np.inner(a, b)[i0,...,ir-2,j0,...,js-2]
             = sum(a[i0,...,ir-2,:]*b[j0,...,js-2,:])

    In addition `a` or `b` may be scalars, in which case::

       np.inner(a,b) = a*b

    Examples
    --------
    Ordinary inner product for vectors:

    >>> import numpy as np
    >>> a = np.array([1,2,3])
    >>> b = np.array([0,1,0])
    >>> np.inner(a, b)
    2

    Some multidimensional examples:

    >>> a = np.arange(24).reshape((2,3,4))
    >>> b = np.arange(4)
    >>> c = np.inner(a, b)
    >>> c.shape
    (2, 3)
    >>> c
    array([[ 14,  38,  62],
           [ 86, 110, 134]])

    >>> a = np.arange(2).reshape((1,1,2))
    >>> b = np.arange(6).reshape((3,2))
    >>> c = np.inner(a, b)
    >>> c.shape
    (1, 1, 3)
    >>> c
    array([[[1, 3, 5]]])

    An example where `b` is a scalar:

    >>> np.inner(np.eye(2), 7)
    array([[7., 0.],
           [0., 7.]])

    """
    return (a, b)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.where)
def where(condition, x=None, y=None):
    """
    where(condition, [x, y], /)

    Return elements chosen from `x` or `y` depending on `condition`.

    .. note::
        When only `condition` is provided, this function is a shorthand for
        ``np.asarray(condition).nonzero()``. Using `nonzero` directly should be
        preferred, as it behaves correctly for subclasses. The rest of this
        documentation covers only the case where all three arguments are
        provided.

    Parameters
    ----------
    condition : array_like, bool
        Where True, yield `x`, otherwise yield `y`.
    x, y : array_like
        Values from which to choose. `x`, `y` and `condition` need to be
        broadcastable to some shape.

    Returns
    -------
    out : ndarray
        An array with elements from `x` where `condition` is True, and elements
        from `y` elsewhere.

    See Also
    --------
    choose
    nonzero : The function that is called when x and y are omitted

    Notes
    -----
    If all the arrays are 1-D, `where` is equivalent to::

        [xv if c else yv
         for c, xv, yv in zip(condition, x, y)]

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(10)
    >>> a
    array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    >>> np.where(a < 5, a, 10*a)
    array([ 0,  1,  2,  3,  4, 50, 60, 70, 80, 90])

    This can be used on multidimensional arrays too:

    >>> np.where([[True, False], [True, True]],
    ...          [[1, 2], [3, 4]],
    ...          [[9, 8], [7, 6]])
    array([[1, 8],
           [3, 4]])

    The shapes of x, y, and the condition are broadcast together:

    >>> x, y = np.ogrid[:3, :4]
    >>> np.where(x < y, x, 10 + y)  # both x and 10+y are broadcast
    array([[10,  0,  0,  0],
           [10, 11,  1,  1],
           [10, 11, 12,  2]])

    >>> a = np.array([[0, 1, 2],
    ...               [0, 2, 4],
    ...               [0, 3, 6]])
    >>> np.where(a < 4, a, -1)  # -1 is broadcast
    array([[ 0,  1,  2],
           [ 0,  2, -1],
           [ 0,  3, -1]])
    """
    return (condition, x, y)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.lexsort)
def lexsort(keys, axis=None):
    """
    lexsort(keys, axis=-1)

    Perform an indirect stable sort using a sequence of keys.

    Given multiple sorting keys, lexsort returns an array of integer indices
    that describes the sort order by multiple keys. The last key in the
    sequence is used for the primary sort order, ties are broken by the
    second-to-last key, and so on.

    Parameters
    ----------
    keys : (k, m, n, ...) array-like
        The `k` keys to be sorted. The *last* key (e.g, the last
        row if `keys` is a 2D array) is the primary sort key.
        Each element of `keys` along the zeroth axis must be
        an array-like object of the same shape.
    axis : int, optional
        Axis to be indirectly sorted. By default, sort over the last axis
        of each sequence. Separate slices along `axis` sorted over
        independently; see last example.

    Returns
    -------
    indices : (m, n, ...) ndarray of ints
        Array of indices that sort the keys along the specified axis.

    See Also
    --------
    argsort : Indirect sort.
    ndarray.sort : In-place sort.
    sort : Return a sorted copy of an array.

    Examples
    --------
    Sort names: first by surname, then by name.

    >>> import numpy as np
    >>> surnames =    ('Hertz',    'Galilei', 'Hertz')
    >>> first_names = ('Heinrich', 'Galileo', 'Gustav')
    >>> ind = np.lexsort((first_names, surnames))
    >>> ind
    array([1, 2, 0])

    >>> [surnames[i] + ", " + first_names[i] for i in ind]
    ['Galilei, Galileo', 'Hertz, Gustav', 'Hertz, Heinrich']

    Sort according to two numerical keys, first by elements
    of ``a``, then breaking ties according to elements of ``b``:

    >>> a = [1, 5, 1, 4, 3, 4, 4]  # First sequence
    >>> b = [9, 4, 0, 4, 0, 2, 1]  # Second sequence
    >>> ind = np.lexsort((b, a))  # Sort by `a`, then by `b`
    >>> ind
    array([2, 0, 4, 6, 5, 3, 1])
    >>> [(a[i], b[i]) for i in ind]
    [(1, 0), (1, 9), (3, 0), (4, 1), (4, 2), (4, 4), (5, 4)]

    Compare against `argsort`, which would sort each key independently.

    >>> np.argsort((b, a), kind='stable')
    array([[2, 4, 6, 5, 1, 3, 0],
           [0, 2, 4, 3, 5, 6, 1]])

    To sort lexicographically with `argsort`, we would need to provide a
    structured array.

    >>> x = np.array([(ai, bi) for ai, bi in zip(a, b)],
    ...              dtype = np.dtype([('x', int), ('y', int)]))
    >>> np.argsort(x)  # or np.argsort(x, order=('x', 'y'))
    array([2, 0, 4, 6, 5, 3, 1])

    The zeroth axis of `keys` always corresponds with the sequence of keys,
    so 2D arrays are treated just like other sequences of keys.

    >>> arr = np.asarray([b, a])
    >>> ind2 = np.lexsort(arr)
    >>> np.testing.assert_equal(ind2, ind)

    Accordingly, the `axis` parameter refers to an axis of *each* key, not of
    the `keys` argument itself. For instance, the array ``arr`` is treated as
    a sequence of two 1-D keys, so specifying ``axis=0`` is equivalent to
    using the default axis, ``axis=-1``.

    >>> np.testing.assert_equal(np.lexsort(arr, axis=0),
    ...                         np.lexsort(arr, axis=-1))

    For higher-dimensional arrays, the axis parameter begins to matter. The
    resulting array has the same shape as each key, and the values are what
    we would expect if `lexsort` were performed on corresponding slices
    of the keys independently. For instance,

    >>> x = [[1, 2, 3, 4],
    ...      [4, 3, 2, 1],
    ...      [2, 1, 4, 3]]
    >>> y = [[2, 2, 1, 1],
    ...      [1, 2, 1, 2],
    ...      [1, 1, 2, 1]]
    >>> np.lexsort((x, y), axis=1)
    array([[2, 3, 0, 1],
           [2, 0, 3, 1],
           [1, 0, 3, 2]])

    Each row of the result is what we would expect if we were to perform
    `lexsort` on the corresponding row of the keys:

    >>> for i in range(3):
    ...     print(np.lexsort((x[i], y[i])))
    [2 3 0 1]
    [2 0 3 1]
    [1 0 3 2]

    """
    if isinstance(keys, tuple):
        return keys
    else:
        return (keys,)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.can_cast)
def can_cast(from_, to, casting=None):
    """
    can_cast(from_, to, casting='safe')

    Returns True if cast between data types can occur according to the
    casting rule.

    Parameters
    ----------
    from_ : dtype, dtype specifier, NumPy scalar, or array
        Data type, NumPy scalar, or array to cast from.
    to : dtype or dtype specifier
        Data type to cast to.
    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        Controls what kind of data casting may occur.

        * 'no' means the data types should not be cast at all.
        * 'equiv' means only byte-order changes are allowed.
        * 'safe' means only casts which can preserve values are allowed.
        * 'same_kind' means only safe casts or casts within a kind,
          like float64 to float32, are allowed.
        * 'unsafe' means any data conversions may be done.

    Returns
    -------
    out : bool
        True if cast can occur according to the casting rule.

    Notes
    -----
    .. versionchanged:: 2.0
       This function does not support Python scalars anymore and does not
       apply any value-based logic for 0-D arrays and NumPy scalars.

    See also
    --------
    dtype, result_type

    Examples
    --------
    Basic examples

    >>> import numpy as np
    >>> np.can_cast(np.int32, np.int64)
    True
    >>> np.can_cast(np.float64, complex)
    True
    >>> np.can_cast(complex, float)
    False

    >>> np.can_cast('i8', 'f8')
    True
    >>> np.can_cast('i8', 'f4')
    False
    >>> np.can_cast('i4', 'S4')
    False

    """
    return (from_,)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.min_scalar_type)
def min_scalar_type(a):
    """
    min_scalar_type(a, /)

    For scalar ``a``, returns the data type with the smallest size
    and smallest scalar kind which can hold its value.  For non-scalar
    array ``a``, returns the vector's dtype unmodified.

    Floating point values are not demoted to integers,
    and complex values are not demoted to floats.

    Parameters
    ----------
    a : scalar or array_like
        The value whose minimal data type is to be found.

    Returns
    -------
    out : dtype
        The minimal data type.

    See Also
    --------
    result_type, promote_types, dtype, can_cast

    Examples
    --------
    >>> import numpy as np
    >>> np.min_scalar_type(10)
    dtype('uint8')

    >>> np.min_scalar_type(-260)
    dtype('int16')

    >>> np.min_scalar_type(3.1)
    dtype('float16')

    >>> np.min_scalar_type(1e50)
    dtype('float64')

    >>> np.min_scalar_type(np.arange(4,dtype='f8'))
    dtype('float64')

    """
    return (a,)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.result_type)
def result_type(*arrays_and_dtypes):
    """
    result_type(*arrays_and_dtypes)

    Returns the type that results from applying the NumPy
    type promotion rules to the arguments.

    Type promotion in NumPy works similarly to the rules in languages
    like C++, with some slight differences.  When both scalars and
    arrays are used, the array's type takes precedence and the actual value
    of the scalar is taken into account.

    For example, calculating 3*a, where a is an array of 32-bit floats,
    intuitively should result in a 32-bit float output.  If the 3 is a
    32-bit integer, the NumPy rules indicate it can't convert losslessly
    into a 32-bit float, so a 64-bit float should be the result type.
    By examining the value of the constant, '3', we see that it fits in
    an 8-bit integer, which can be cast losslessly into the 32-bit float.

    Parameters
    ----------
    arrays_and_dtypes : list of arrays and dtypes
        The operands of some operation whose result type is needed.

    Returns
    -------
    out : dtype
        The result type.

    See also
    --------
    dtype, promote_types, min_scalar_type, can_cast

    Notes
    -----
    The specific algorithm used is as follows.

    Categories are determined by first checking which of boolean,
    integer (int/uint), or floating point (float/complex) the maximum
    kind of all the arrays and the scalars are.

    If there are only scalars or the maximum category of the scalars
    is higher than the maximum category of the arrays,
    the data types are combined with :func:`promote_types`
    to produce the return value.

    Otherwise, `min_scalar_type` is called on each scalar, and
    the resulting data types are all combined with :func:`promote_types`
    to produce the return value.

    The set of int values is not a subset of the uint values for types
    with the same number of bits, something not reflected in
    :func:`min_scalar_type`, but handled as a special case in `result_type`.

    Examples
    --------
    >>> import numpy as np
    >>> np.result_type(3, np.arange(7, dtype='i1'))
    dtype('int8')

    >>> np.result_type('i4', 'c8')
    dtype('complex128')

    >>> np.result_type(3.0, -2)
    dtype('float64')

    """
    return arrays_and_dtypes


@array_function_from_c_func_and_dispatcher(_multiarray_umath.dot)
def dot(a, b, out=None):
    """
    dot(a, b, out=None)

    Dot product of two arrays. Specifically,

    - If both `a` and `b` are 1-D arrays, it is inner product of vectors
      (without complex conjugation).

    - If both `a` and `b` are 2-D arrays, it is matrix multiplication,
      but using :func:`matmul` or ``a @ b`` is preferred.

    - If either `a` or `b` is 0-D (scalar), it is equivalent to
      :func:`multiply` and using ``numpy.multiply(a, b)`` or ``a * b`` is
      preferred.

    - If `a` is an N-D array and `b` is a 1-D array, it is a sum product over
      the last axis of `a` and `b`.

    - If `a` is an N-D array and `b` is an M-D array (where ``M>=2``), it is a
      sum product over the last axis of `a` and the second-to-last axis of
      `b`::

        dot(a, b)[i,j,k,m] = sum(a[i,j,:] * b[k,:,m])

    It uses an optimized BLAS library when possible (see `numpy.linalg`).

    Parameters
    ----------
    a : array_like
        First argument.
    b : array_like
        Second argument.
    out : ndarray, optional
        Output argument. This must have the exact kind that would be returned
        if it was not used. In particular, it must have the right type, must be
        C-contiguous, and its dtype must be the dtype that would be returned
        for `dot(a,b)`. This is a performance feature. Therefore, if these
        conditions are not met, an exception is raised, instead of attempting
        to be flexible.

    Returns
    -------
    output : ndarray
        Returns the dot product of `a` and `b`.  If `a` and `b` are both
        scalars or both 1-D arrays then a scalar is returned; otherwise
        an array is returned.
        If `out` is given, then it is returned.

    Raises
    ------
    ValueError
        If the last dimension of `a` is not the same size as
        the second-to-last dimension of `b`.

    See Also
    --------
    vdot : Complex-conjugating dot product.
    vecdot : Vector dot product of two arrays.
    tensordot : Sum products over arbitrary axes.
    einsum : Einstein summation convention.
    matmul : '@' operator as method with out parameter.
    linalg.multi_dot : Chained dot product.

    Examples
    --------
    >>> import numpy as np
    >>> np.dot(3, 4)
    12

    Neither argument is complex-conjugated:

    >>> np.dot([2j, 3j], [2j, 3j])
    (-13+0j)

    For 2-D arrays it is the matrix product:

    >>> a = [[1, 0], [0, 1]]
    >>> b = [[4, 1], [2, 2]]
    >>> np.dot(a, b)
    array([[4, 1],
           [2, 2]])

    >>> a = np.arange(3*4*5*6).reshape((3,4,5,6))
    >>> b = np.arange(3*4*5*6)[::-1].reshape((5,4,6,3))
    >>> np.dot(a, b)[2,3,2,1,2,2]
    499128
    >>> sum(a[2,3,2,:] * b[1,2,:,2])
    499128

    """
    return (a, b, out)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.vdot)
def vdot(a, b):
    r"""
    vdot(a, b, /)

    Return the dot product of two vectors.

    The `vdot` function handles complex numbers differently than `dot`:
    if the first argument is complex, it is replaced by its complex conjugate
    in the dot product calculation. `vdot` also handles multidimensional
    arrays differently than `dot`: it does not perform a matrix product, but
    flattens the arguments to 1-D arrays before taking a vector dot product.

    Consequently, when the arguments are 2-D arrays of the same shape, this
    function effectively returns their
    `Frobenius inner product <https://en.wikipedia.org/wiki/Frobenius_inner_product>`_
    (also known as the *trace inner product* or the *standard inner product*
    on a vector space of matrices).

    Parameters
    ----------
    a : array_like
        If `a` is complex the complex conjugate is taken before calculation
        of the dot product.
    b : array_like
        Second argument to the dot product.

    Returns
    -------
    output : ndarray
        Dot product of `a` and `b`.  Can be an int, float, or
        complex depending on the types of `a` and `b`.

    See Also
    --------
    dot : Return the dot product without using the complex conjugate of the
          first argument.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([1+2j,3+4j])
    >>> b = np.array([5+6j,7+8j])
    >>> np.vdot(a, b)
    (70-8j)
    >>> np.vdot(b, a)
    (70+8j)

    Note that higher-dimensional arrays are flattened!

    >>> a = np.array([[1, 4], [5, 6]])
    >>> b = np.array([[4, 1], [2, 2]])
    >>> np.vdot(a, b)
    30
    >>> np.vdot(b, a)
    30
    >>> 1*4 + 4*1 + 5*2 + 6*2
    30

    """  # noqa: E501
    return (a, b)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.bincount)
def bincount(x, weights=None, minlength=None):
    """
    bincount(x, /, weights=None, minlength=0)

    Count number of occurrences of each value in array of non-negative ints.

    The number of bins (of size 1) is one larger than the largest value in
    `x`. If `minlength` is specified, there will be at least this number
    of bins in the output array (though it will be longer if necessary,
    depending on the contents of `x`).
    Each bin gives the number of occurrences of its index value in `x`.
    If `weights` is specified the input array is weighted by it, i.e. if a
    value ``n`` is found at position ``i``, ``out[n] += weight[i]`` instead
    of ``out[n] += 1``.

    Parameters
    ----------
    x : array_like, 1 dimension, nonnegative ints
        Input array.
    weights : array_like, optional
        Weights, array of the same shape as `x`.
    minlength : int, optional
        A minimum number of bins for the output array.

    Returns
    -------
    out : ndarray of ints
        The result of binning the input array.
        The length of `out` is equal to ``np.amax(x)+1``.

    Raises
    ------
    ValueError
        If the input is not 1-dimensional, or contains elements with negative
        values, or if `minlength` is negative.
    TypeError
        If the type of the input is float or complex.

    See Also
    --------
    histogram, digitize, unique

    Examples
    --------
    >>> import numpy as np
    >>> np.bincount(np.arange(5))
    array([1, 1, 1, 1, 1])
    >>> np.bincount(np.array([0, 1, 1, 3, 2, 1, 7]))
    array([1, 3, 1, 1, 0, 0, 0, 1])

    >>> x = np.array([0, 1, 1, 3, 2, 1, 7, 23])
    >>> np.bincount(x).size == np.amax(x)+1
    True

    The input array needs to be of integer dtype, otherwise a
    TypeError is raised:

    >>> np.bincount(np.arange(5, dtype=float))
    Traceback (most recent call last):
      ...
    TypeError: Cannot cast array data from dtype('float64') to dtype('int64')
    according to the rule 'safe'

    A possible use of ``bincount`` is to perform sums over
    variable-size chunks of an array, using the ``weights`` keyword.

    >>> w = np.array([0.3, 0.5, 0.2, 0.7, 1., -0.6]) # weights
    >>> x = np.array([0, 1, 1, 2, 2, 2])
    >>> np.bincount(x,  weights=w)
    array([ 0.3,  0.7,  1.1])

    """
    return (x, weights)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.ravel_multi_index)
def ravel_multi_index(multi_index, dims, mode=None, order=None):
    """
    ravel_multi_index(multi_index, dims, mode='raise', order='C')

    Converts a tuple of index arrays into an array of flat
    indices, applying boundary modes to the multi-index.

    Parameters
    ----------
    multi_index : tuple of array_like
        A tuple of integer arrays, one array for each dimension.
    dims : tuple of ints
        The shape of array into which the indices from ``multi_index`` apply.
    mode : {'raise', 'wrap', 'clip'}, optional
        Specifies how out-of-bounds indices are handled.  Can specify
        either one mode or a tuple of modes, one mode per index.

        * 'raise' -- raise an error (default)
        * 'wrap' -- wrap around
        * 'clip' -- clip to the range

        In 'clip' mode, a negative index which would normally
        wrap will clip to 0 instead.
    order : {'C', 'F'}, optional
        Determines whether the multi-index should be viewed as
        indexing in row-major (C-style) or column-major
        (Fortran-style) order.

    Returns
    -------
    raveled_indices : ndarray
        An array of indices into the flattened version of an array
        of dimensions ``dims``.

    See Also
    --------
    unravel_index

    Examples
    --------
    >>> import numpy as np
    >>> arr = np.array([[3,6,6],[4,5,1]])
    >>> np.ravel_multi_index(arr, (7,6))
    array([22, 41, 37])
    >>> np.ravel_multi_index(arr, (7,6), order='F')
    array([31, 41, 13])
    >>> np.ravel_multi_index(arr, (4,6), mode='clip')
    array([22, 23, 19])
    >>> np.ravel_multi_index(arr, (4,4), mode=('clip','wrap'))
    array([12, 13, 13])

    >>> np.ravel_multi_index((3,1,4,1), (6,7,8,9))
    1621
    """
    return multi_index


@array_function_from_c_func_and_dispatcher(_multiarray_umath.unravel_index)
def unravel_index(indices, shape=None, order=None):
    """
    unravel_index(indices, shape, order='C')

    Converts a flat index or array of flat indices into a tuple
    of coordinate arrays.

    Parameters
    ----------
    indices : array_like
        An integer array whose elements are indices into the flattened
        version of an array of dimensions ``shape``. Before version 1.6.0,
        this function accepted just one index value.
    shape : tuple of ints
        The shape of the array to use for unraveling ``indices``.
    order : {'C', 'F'}, optional
        Determines whether the indices should be viewed as indexing in
        row-major (C-style) or column-major (Fortran-style) order.

    Returns
    -------
    unraveled_coords : tuple of ndarray
        Each array in the tuple has the same shape as the ``indices``
        array.

    See Also
    --------
    ravel_multi_index

    Examples
    --------
    >>> import numpy as np
    >>> np.unravel_index([22, 41, 37], (7,6))
    (array([3, 6, 6]), array([4, 5, 1]))
    >>> np.unravel_index([31, 41, 13], (7,6), order='F')
    (array([3, 6, 6]), array([4, 5, 1]))

    >>> np.unravel_index(1621, (6,7,8,9))
    (3, 1, 4, 1)

    """
    return (indices,)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.copyto)
def copyto(dst, src, casting=None, where=None):
    """
    copyto(dst, src, casting='same_kind', where=True)

    Copies values from one array to another, broadcasting as necessary.

    Raises a TypeError if the `casting` rule is violated, and if
    `where` is provided, it selects which elements to copy.

    Parameters
    ----------
    dst : ndarray
        The array into which values are copied.
    src : array_like
        The array from which values are copied.
    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        Controls what kind of data casting may occur when copying.

        * 'no' means the data types should not be cast at all.
        * 'equiv' means only byte-order changes are allowed.
        * 'safe' means only casts which can preserve values are allowed.
        * 'same_kind' means only safe casts or casts within a kind,
          like float64 to float32, are allowed.
        * 'unsafe' means any data conversions may be done.
    where : array_like of bool, optional
        A boolean array which is broadcasted to match the dimensions
        of `dst`, and selects elements to copy from `src` to `dst`
        wherever it contains the value True.

    Examples
    --------
    >>> import numpy as np
    >>> A = np.array([4, 5, 6])
    >>> B = [1, 2, 3]
    >>> np.copyto(A, B)
    >>> A
    array([1, 2, 3])

    >>> A = np.array([[1, 2, 3], [4, 5, 6]])
    >>> B = [[4, 5, 6], [7, 8, 9]]
    >>> np.copyto(A, B)
    >>> A
    array([[4, 5, 6],
           [7, 8, 9]])

    """
    return (dst, src, where)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.putmask)
def putmask(a, /, mask, values):
    """
    putmask(a, mask, values)

    Changes elements of an array based on conditional and input values.

    Sets ``a.flat[n] = values[n]`` for each n where ``mask.flat[n]==True``.

    If `values` is not the same size as `a` and `mask` then it will repeat.
    This gives behavior different from ``a[mask] = values``.

    Parameters
    ----------
    a : ndarray
        Target array.
    mask : array_like
        Boolean mask array. It has to be the same shape as `a`.
    values : array_like
        Values to put into `a` where `mask` is True. If `values` is smaller
        than `a` it will be repeated.

    See Also
    --------
    place, put, take, copyto

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(6).reshape(2, 3)
    >>> np.putmask(x, x>2, x**2)
    >>> x
    array([[ 0,  1,  2],
           [ 9, 16, 25]])

    If `values` is smaller than `a` it is repeated:

    >>> x = np.arange(5)
    >>> np.putmask(x, x>1, [-33, -44])
    >>> x
    array([  0,   1, -33, -44, -33])

    """
    return (a, mask, values)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.packbits)
def packbits(a, axis=None, bitorder='big'):
    """
    packbits(a, /, axis=None, bitorder='big')

    Packs the elements of a binary-valued array into bits in a uint8 array.

    The result is padded to full bytes by inserting zero bits at the end.

    Parameters
    ----------
    a : array_like
        An array of integers or booleans whose elements should be packed to
        bits.
    axis : int, optional
        The dimension over which bit-packing is done.
        ``None`` implies packing the flattened array.
    bitorder : {'big', 'little'}, optional
        The order of the input bits. 'big' will mimic bin(val),
        ``[0, 0, 0, 0, 0, 0, 1, 1] => 3 = 0b00000011``, 'little' will
        reverse the order so ``[1, 1, 0, 0, 0, 0, 0, 0] => 3``.
        Defaults to 'big'.

    Returns
    -------
    packed : ndarray
        Array of type uint8 whose elements represent bits corresponding to the
        logical (0 or nonzero) value of the input elements. The shape of
        `packed` has the same number of dimensions as the input (unless `axis`
        is None, in which case the output is 1-D).

    See Also
    --------
    unpackbits: Unpacks elements of a uint8 array into a binary-valued output
                array.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[[1,0,1],
    ...                [0,1,0]],
    ...               [[1,1,0],
    ...                [0,0,1]]])
    >>> b = np.packbits(a, axis=-1)
    >>> b
    array([[[160],
            [ 64]],
           [[192],
            [ 32]]], dtype=uint8)

    Note that in binary 160 = 1010 0000, 64 = 0100 0000, 192 = 1100 0000,
    and 32 = 0010 0000.

    """
    return (a,)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.unpackbits)
def unpackbits(a, axis=None, count=None, bitorder='big'):
    """
    unpackbits(a, /, axis=None, count=None, bitorder='big')

    Unpacks elements of a uint8 array into a binary-valued output array.

    Each element of `a` represents a bit-field that should be unpacked
    into a binary-valued output array. The shape of the output array is
    either 1-D (if `axis` is ``None``) or the same shape as the input
    array with unpacking done along the axis specified.

    Parameters
    ----------
    a : ndarray, uint8 type
       Input array.
    axis : int, optional
        The dimension over which bit-unpacking is done.
        ``None`` implies unpacking the flattened array.
    count : int or None, optional
        The number of elements to unpack along `axis`, provided as a way
        of undoing the effect of packing a size that is not a multiple
        of eight. A non-negative number means to only unpack `count`
        bits. A negative number means to trim off that many bits from
        the end. ``None`` means to unpack the entire array (the
        default). Counts larger than the available number of bits will
        add zero padding to the output. Negative counts must not
        exceed the available number of bits.
    bitorder : {'big', 'little'}, optional
        The order of the returned bits. 'big' will mimic bin(val),
        ``3 = 0b00000011 => [0, 0, 0, 0, 0, 0, 1, 1]``, 'little' will reverse
        the order to ``[1, 1, 0, 0, 0, 0, 0, 0]``.
        Defaults to 'big'.

    Returns
    -------
    unpacked : ndarray, uint8 type
       The elements are binary-valued (0 or 1).

    See Also
    --------
    packbits : Packs the elements of a binary-valued array into bits in
               a uint8 array.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[2], [7], [23]], dtype=np.uint8)
    >>> a
    array([[ 2],
           [ 7],
           [23]], dtype=uint8)
    >>> b = np.unpackbits(a, axis=1)
    >>> b
    array([[0, 0, 0, 0, 0, 0, 1, 0],
           [0, 0, 0, 0, 0, 1, 1, 1],
           [0, 0, 0, 1, 0, 1, 1, 1]], dtype=uint8)
    >>> c = np.unpackbits(a, axis=1, count=-3)
    >>> c
    array([[0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0],
           [0, 0, 0, 1, 0]], dtype=uint8)

    >>> p = np.packbits(b, axis=0)
    >>> np.unpackbits(p, axis=0)
    array([[0, 0, 0, 0, 0, 0, 1, 0],
           [0, 0, 0, 0, 0, 1, 1, 1],
           [0, 0, 0, 1, 0, 1, 1, 1],
           [0, 0, 0, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 0, 0, 0],
           [0, 0, 0, 0, 0, 0, 0, 0]], dtype=uint8)
    >>> np.array_equal(b, np.unpackbits(p, axis=0, count=b.shape[0]))
    True

    """
    return (a,)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.shares_memory)
def shares_memory(a, b, max_work=None):
    """
    shares_memory(a, b, /, max_work=None)

    Determine if two arrays share memory.

    .. warning::

       This function can be exponentially slow for some inputs, unless
       `max_work` is set to zero or a positive integer.
       If in doubt, use `numpy.may_share_memory` instead.

    Parameters
    ----------
    a, b : ndarray
        Input arrays
    max_work : int, optional
        Effort to spend on solving the overlap problem (maximum number
        of candidate solutions to consider). The following special
        values are recognized:

        max_work=-1 (default)
            The problem is solved exactly. In this case, the function returns
            True only if there is an element shared between the arrays. Finding
            the exact solution may take extremely long in some cases.
        max_work=0
            Only the memory bounds of a and b are checked.
            This is equivalent to using ``may_share_memory()``.

    Raises
    ------
    numpy.exceptions.TooHardError
        Exceeded max_work.

    Returns
    -------
    out : bool

    See Also
    --------
    may_share_memory

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 3, 4])
    >>> np.shares_memory(x, np.array([5, 6, 7]))
    False
    >>> np.shares_memory(x[::2], x)
    True
    >>> np.shares_memory(x[::2], x[1::2])
    False

    Checking whether two arrays share memory is NP-complete, and
    runtime may increase exponentially in the number of
    dimensions. Hence, `max_work` should generally be set to a finite
    number, as it is possible to construct examples that take
    extremely long to run:

    >>> from numpy.lib.stride_tricks import as_strided
    >>> x = np.zeros([192163377], dtype=np.int8)
    >>> x1 = as_strided(
    ...     x, strides=(36674, 61119, 85569), shape=(1049, 1049, 1049))
    >>> x2 = as_strided(
    ...     x[64023025:], strides=(12223, 12224, 1), shape=(1049, 1049, 1))
    >>> np.shares_memory(x1, x2, max_work=1000)
    Traceback (most recent call last):
    ...
    numpy.exceptions.TooHardError: Exceeded max_work

    Running ``np.shares_memory(x1, x2)`` without `max_work` set takes
    around 1 minute for this case. It is possible to find problems
    that take still significantly longer.

    """
    return (a, b)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.may_share_memory)
def may_share_memory(a, b, max_work=None):
    """
    may_share_memory(a, b, /, max_work=None)

    Determine if two arrays might share memory

    A return of True does not necessarily mean that the two arrays
    share any element.  It just means that they *might*.

    Only the memory bounds of a and b are checked by default.

    Parameters
    ----------
    a, b : ndarray
        Input arrays
    max_work : int, optional
        Effort to spend on solving the overlap problem.  See
        `shares_memory` for details.  Default for ``may_share_memory``
        is to do a bounds check.

    Returns
    -------
    out : bool

    See Also
    --------
    shares_memory

    Examples
    --------
    >>> import numpy as np
    >>> np.may_share_memory(np.array([1,2]), np.array([5,8,9]))
    False
    >>> x = np.zeros([3, 4])
    >>> np.may_share_memory(x[:,0], x[:,1])
    True

    """
    return (a, b)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.is_busday)
def is_busday(dates, weekmask=None, holidays=None, busdaycal=None, out=None):
    """
    is_busday(
        dates,
        weekmask='1111100',
        holidays=None,
        busdaycal=None,
        out=None
    )

    Calculates which of the given dates are valid days, and which are not.

    Parameters
    ----------
    dates : array_like of datetime64[D]
        The array of dates to process.
    weekmask : str or array_like of bool, optional
        A seven-element array indicating which of Monday through Sunday are
        valid days. May be specified as a length-seven list or array, like
        [1,1,1,1,1,0,0]; a length-seven string, like '1111100'; or a string
        like "Mon Tue Wed Thu Fri", made up of 3-character abbreviations for
        weekdays, optionally separated by white space. Valid abbreviations
        are: Mon Tue Wed Thu Fri Sat Sun
    holidays : array_like of datetime64[D], optional
        An array of dates to consider as invalid dates.  They may be
        specified in any order, and NaT (not-a-time) dates are ignored.
        This list is saved in a normalized form that is suited for
        fast calculations of valid days.
    busdaycal : busdaycalendar, optional
        A `busdaycalendar` object which specifies the valid days. If this
        parameter is provided, neither weekmask nor holidays may be
        provided.
    out : array of bool, optional
        If provided, this array is filled with the result.

    Returns
    -------
    out : array of bool
        An array with the same shape as ``dates``, containing True for
        each valid day, and False for each invalid day.

    See Also
    --------
    busdaycalendar : An object that specifies a custom set of valid days.
    busday_offset : Applies an offset counted in valid days.
    busday_count : Counts how many valid days are in a half-open date range.

    Examples
    --------
    >>> import numpy as np
    >>> # The weekdays are Friday, Saturday, and Monday
    ... np.is_busday(['2011-07-01', '2011-07-02', '2011-07-18'],
    ...                 holidays=['2011-07-01', '2011-07-04', '2011-07-17'])
    array([False, False,  True])
    """
    return (dates, weekmask, holidays, out)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.busday_offset)
def busday_offset(dates, offsets, roll=None, weekmask=None, holidays=None,
                  busdaycal=None, out=None):
    """
    busday_offset(
        dates,
        offsets,
        roll='raise',
        weekmask='1111100',
        holidays=None,
        busdaycal=None,
        out=None
    )

    First adjusts the date to fall on a valid day according to
    the ``roll`` rule, then applies offsets to the given dates
    counted in valid days.

    Parameters
    ----------
    dates : array_like of datetime64[D]
        The array of dates to process.
    offsets : array_like of int
        The array of offsets, which is broadcast with ``dates``.
    roll : {'raise', 'nat', 'forward', 'following', 'backward', 'preceding', \
        'modifiedfollowing', 'modifiedpreceding'}, optional
        How to treat dates that do not fall on a valid day. The default
        is 'raise'.

        * 'raise' means to raise an exception for an invalid day.
        * 'nat' means to return a NaT (not-a-time) for an invalid day.
        * 'forward' and 'following' mean to take the first valid day
          later in time.
        * 'backward' and 'preceding' mean to take the first valid day
          earlier in time.
        * 'modifiedfollowing' means to take the first valid day
          later in time unless it is across a Month boundary, in which
          case to take the first valid day earlier in time.
        * 'modifiedpreceding' means to take the first valid day
          earlier in time unless it is across a Month boundary, in which
          case to take the first valid day later in time.
    weekmask : str or array_like of bool, optional
        A seven-element array indicating which of Monday through Sunday are
        valid days. May be specified as a length-seven list or array, like
        [1,1,1,1,1,0,0]; a length-seven string, like '1111100'; or a string
        like "Mon Tue Wed Thu Fri", made up of 3-character abbreviations for
        weekdays, optionally separated by white space. Valid abbreviations
        are: Mon Tue Wed Thu Fri Sat Sun
    holidays : array_like of datetime64[D], optional
        An array of dates to consider as invalid dates.  They may be
        specified in any order, and NaT (not-a-time) dates are ignored.
        This list is saved in a normalized form that is suited for
        fast calculations of valid days.
    busdaycal : busdaycalendar, optional
        A `busdaycalendar` object which specifies the valid days. If this
        parameter is provided, neither weekmask nor holidays may be
        provided.
    out : array of datetime64[D], optional
        If provided, this array is filled with the result.

    Returns
    -------
    out : array of datetime64[D]
        An array with a shape from broadcasting ``dates`` and ``offsets``
        together, containing the dates with offsets applied.

    See Also
    --------
    busdaycalendar : An object that specifies a custom set of valid days.
    is_busday : Returns a boolean array indicating valid days.
    busday_count : Counts how many valid days are in a half-open date range.

    Examples
    --------
    >>> import numpy as np
    >>> # First business day in October 2011 (not accounting for holidays)
    ... np.busday_offset('2011-10', 0, roll='forward')
    np.datetime64('2011-10-03')
    >>> # Last business day in February 2012 (not accounting for holidays)
    ... np.busday_offset('2012-03', -1, roll='forward')
    np.datetime64('2012-02-29')
    >>> # Third Wednesday in January 2011
    ... np.busday_offset('2011-01', 2, roll='forward', weekmask='Wed')
    np.datetime64('2011-01-19')
    >>> # 2012 Mother's Day in Canada and the U.S.
    ... np.busday_offset('2012-05', 1, roll='forward', weekmask='Sun')
    np.datetime64('2012-05-13')

    >>> # First business day on or after a date
    ... np.busday_offset('2011-03-20', 0, roll='forward')
    np.datetime64('2011-03-21')
    >>> np.busday_offset('2011-03-22', 0, roll='forward')
    np.datetime64('2011-03-22')
    >>> # First business day after a date
    ... np.busday_offset('2011-03-20', 1, roll='backward')
    np.datetime64('2011-03-21')
    >>> np.busday_offset('2011-03-22', 1, roll='backward')
    np.datetime64('2011-03-23')
    """
    return (dates, offsets, weekmask, holidays, out)


@array_function_from_c_func_and_dispatcher(_multiarray_umath.busday_count)
def busday_count(begindates, enddates, weekmask=None, holidays=None,
                 busdaycal=None, out=None):
    """
    busday_count(
        begindates,
        enddates,
        weekmask='1111100',
        holidays=[],
        busdaycal=None,
        out=None
    )

    Counts the number of valid days between `begindates` and
    `enddates`, not including the day of `enddates`.

    If ``enddates`` specifies a date value that is earlier than the
    corresponding ``begindates`` date value, the count will be negative.

    Parameters
    ----------
    begindates : array_like of datetime64[D]
        The array of the first dates for counting.
    enddates : array_like of datetime64[D]
        The array of the end dates for counting, which are excluded
        from the count themselves.
    weekmask : str or array_like of bool, optional
        A seven-element array indicating which of Monday through Sunday are
        valid days. May be specified as a length-seven list or array, like
        [1,1,1,1,1,0,0]; a length-seven string, like '1111100'; or a string
        like "Mon Tue Wed Thu Fri", made up of 3-character abbreviations for
        weekdays, optionally separated by white space. Valid abbreviations
        are: Mon Tue Wed Thu Fri Sat Sun
    holidays : array_like of datetime64[D], optional
        An array of dates to consider as invalid dates.  They may be
        specified in any order, and NaT (not-a-time) dates are ignored.
        This list is saved in a normalized form that is suited for
        fast calculations of valid days.
    busdaycal : busdaycalendar, optional
        A `busdaycalendar` object which specifies the valid days. If this
        parameter is provided, neither weekmask nor holidays may be
        provided.
    out : array of int, optional
        If provided, this array is filled with the result.

    Returns
    -------
    out : array of int
        An array with a shape from broadcasting ``begindates`` and ``enddates``
        together, containing the number of valid days between
        the begin and end dates.

    See Also
    --------
    busdaycalendar : An object that specifies a custom set of valid days.
    is_busday : Returns a boolean array indicating valid days.
    busday_offset : Applies an offset counted in valid days.

    Examples
    --------
    >>> import numpy as np
    >>> # Number of weekdays in January 2011
    ... np.busday_count('2011-01', '2011-02')
    21
    >>> # Number of weekdays in 2011
    >>> np.busday_count('2011', '2012')
    260
    >>> # Number of Saturdays in 2011
    ... np.busday_count('2011', '2012', weekmask='Sat')
    53
    """
    return (begindates, enddates, weekmask, holidays, out)


@array_function_from_c_func_and_dispatcher(
    _multiarray_umath.datetime_as_string)
def datetime_as_string(arr, unit=None, timezone=None, casting=None):
    """
    datetime_as_string(arr, unit=None, timezone='naive', casting='same_kind')

    Convert an array of datetimes into an array of strings.

    Parameters
    ----------
    arr : array_like of datetime64
        The array of UTC timestamps to format.
    unit : str
        One of None, 'auto', or
        a :ref:`datetime unit <arrays.dtypes.dateunits>`.
    timezone : {'naive', 'UTC', 'local'} or tzinfo
        Timezone information to use when displaying the datetime. If 'UTC',
        end with a Z to indicate UTC time. If 'local', convert to the local
        timezone first, and suffix with a +-#### timezone offset. If a tzinfo
        object, then do as with 'local', but use the specified timezone.
    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}
        Casting to allow when changing between datetime units.

    Returns
    -------
    str_arr : ndarray
        An array of strings the same shape as `arr`.

    Examples
    --------
    >>> import numpy as np
    >>> import pytz
    >>> d = np.arange('2002-10-27T04:30', 4*60, 60, dtype='M8[m]')
    >>> d
    array(['2002-10-27T04:30', '2002-10-27T05:30', '2002-10-27T06:30',
           '2002-10-27T07:30'], dtype='datetime64[m]')

    Setting the timezone to UTC shows the same information, but with a Z suffix

    >>> np.datetime_as_string(d, timezone='UTC')
    array(['2002-10-27T04:30Z', '2002-10-27T05:30Z', '2002-10-27T06:30Z',
           '2002-10-27T07:30Z'], dtype='<U35')

    Note that we picked datetimes that cross a DST boundary. Passing in a
    ``pytz`` timezone object will print the appropriate offset

    >>> np.datetime_as_string(d, timezone=pytz.timezone('US/Eastern'))
    array(['2002-10-27T00:30-0400', '2002-10-27T01:30-0400',
           '2002-10-27T01:30-0500', '2002-10-27T02:30-0500'], dtype='<U39')

    Passing in a unit will change the precision

    >>> np.datetime_as_string(d, unit='h')
    array(['2002-10-27T04', '2002-10-27T05', '2002-10-27T06', '2002-10-27T07'],
          dtype='<U32')
    >>> np.datetime_as_string(d, unit='s')
    array(['2002-10-27T04:30:00', '2002-10-27T05:30:00', '2002-10-27T06:30:00',
           '2002-10-27T07:30:00'], dtype='<U38')

    'casting' can be used to specify whether precision can be changed

    >>> np.datetime_as_string(d, unit='h', casting='safe')
    Traceback (most recent call last):
        ...
    TypeError: Cannot create a datetime string as units 'h' from a NumPy
    datetime with units 'm' according to the rule 'safe'
    """
    return (arr,)

# === NexusCore/openenv\Lib\site-packages\matplotlib\_mathtext_data.py ===
"""
font data tables for truetype and afm computer modern fonts
"""

from __future__ import annotations
from typing import overload

latex_to_bakoma = {
    '\\__sqrt__'                 : ('cmex10', 0x70),
    '\\bigcap'                   : ('cmex10', 0x5c),
    '\\bigcup'                   : ('cmex10', 0x5b),
    '\\bigodot'                  : ('cmex10', 0x4b),
    '\\bigoplus'                 : ('cmex10', 0x4d),
    '\\bigotimes'                : ('cmex10', 0x4f),
    '\\biguplus'                 : ('cmex10', 0x5d),
    '\\bigvee'                   : ('cmex10', 0x5f),
    '\\bigwedge'                 : ('cmex10', 0x5e),
    '\\coprod'                   : ('cmex10', 0x61),
    '\\int'                      : ('cmex10', 0x5a),
    '\\langle'                   : ('cmex10', 0xad),
    '\\leftangle'                : ('cmex10', 0xad),
    '\\leftbrace'                : ('cmex10', 0xa9),
    '\\oint'                     : ('cmex10', 0x49),
    '\\prod'                     : ('cmex10', 0x59),
    '\\rangle'                   : ('cmex10', 0xae),
    '\\rightangle'               : ('cmex10', 0xae),
    '\\rightbrace'               : ('cmex10', 0xaa),
    '\\sum'                      : ('cmex10', 0x58),
    '\\widehat'                  : ('cmex10', 0x62),
    '\\widetilde'                : ('cmex10', 0x65),
    '\\{'                        : ('cmex10', 0xa9),
    '\\}'                        : ('cmex10', 0xaa),
    '{'                          : ('cmex10', 0xa9),
    '}'                          : ('cmex10', 0xaa),

    ','                          : ('cmmi10', 0x3b),
    '.'                          : ('cmmi10', 0x3a),
    '/'                          : ('cmmi10', 0x3d),
    '<'                          : ('cmmi10', 0x3c),
    '>'                          : ('cmmi10', 0x3e),
    '\\alpha'                    : ('cmmi10', 0xae),
    '\\beta'                     : ('cmmi10', 0xaf),
    '\\chi'                      : ('cmmi10', 0xc2),
    '\\combiningrightarrowabove' : ('cmmi10', 0x7e),
    '\\delta'                    : ('cmmi10', 0xb1),
    '\\ell'                      : ('cmmi10', 0x60),
    '\\epsilon'                  : ('cmmi10', 0xb2),
    '\\eta'                      : ('cmmi10', 0xb4),
    '\\flat'                     : ('cmmi10', 0x5b),
    '\\frown'                    : ('cmmi10', 0x5f),
    '\\gamma'                    : ('cmmi10', 0xb0),
    '\\imath'                    : ('cmmi10', 0x7b),
    '\\iota'                     : ('cmmi10', 0xb6),
    '\\jmath'                    : ('cmmi10', 0x7c),
    '\\kappa'                    : ('cmmi10', 0x2219),
    '\\lambda'                   : ('cmmi10', 0xb8),
    '\\leftharpoondown'          : ('cmmi10', 0x29),
    '\\leftharpoonup'            : ('cmmi10', 0x28),
    '\\mu'                       : ('cmmi10', 0xb9),
    '\\natural'                  : ('cmmi10', 0x5c),
    '\\nu'                       : ('cmmi10', 0xba),
    '\\omega'                    : ('cmmi10', 0x21),
    '\\phi'                      : ('cmmi10', 0xc1),
    '\\pi'                       : ('cmmi10', 0xbc),
    '\\psi'                      : ('cmmi10', 0xc3),
    '\\rho'                      : ('cmmi10', 0xbd),
    '\\rightharpoondown'         : ('cmmi10', 0x2b),
    '\\rightharpoonup'           : ('cmmi10', 0x2a),
    '\\sharp'                    : ('cmmi10', 0x5d),
    '\\sigma'                    : ('cmmi10', 0xbe),
    '\\smile'                    : ('cmmi10', 0x5e),
    '\\tau'                      : ('cmmi10', 0xbf),
    '\\theta'                    : ('cmmi10', 0xb5),
    '\\triangleleft'             : ('cmmi10', 0x2f),
    '\\triangleright'            : ('cmmi10', 0x2e),
    '\\upsilon'                  : ('cmmi10', 0xc0),
    '\\varepsilon'               : ('cmmi10', 0x22),
    '\\varphi'                   : ('cmmi10', 0x27),
    '\\varrho'                   : ('cmmi10', 0x25),
    '\\varsigma'                 : ('cmmi10', 0x26),
    '\\vartheta'                 : ('cmmi10', 0x23),
    '\\wp'                       : ('cmmi10', 0x7d),
    '\\xi'                       : ('cmmi10', 0xbb),
    '\\zeta'                     : ('cmmi10', 0xb3),

    '!'                          : ('cmr10', 0x21),
    '%'                          : ('cmr10', 0x25),
    '&'                          : ('cmr10', 0x26),
    '('                          : ('cmr10', 0x28),
    ')'                          : ('cmr10', 0x29),
    '+'                          : ('cmr10', 0x2b),
    '0'                          : ('cmr10', 0x30),
    '1'                          : ('cmr10', 0x31),
    '2'                          : ('cmr10', 0x32),
    '3'                          : ('cmr10', 0x33),
    '4'                          : ('cmr10', 0x34),
    '5'                          : ('cmr10', 0x35),
    '6'                          : ('cmr10', 0x36),
    '7'                          : ('cmr10', 0x37),
    '8'                          : ('cmr10', 0x38),
    '9'                          : ('cmr10', 0x39),
    ':'                          : ('cmr10', 0x3a),
    ';'                          : ('cmr10', 0x3b),
    '='                          : ('cmr10', 0x3d),
    '?'                          : ('cmr10', 0x3f),
    '@'                          : ('cmr10', 0x40),
    '['                          : ('cmr10', 0x5b),
    '\\#'                        : ('cmr10', 0x23),
    '\\$'                        : ('cmr10', 0x24),
    '\\%'                        : ('cmr10', 0x25),
    '\\Delta'                    : ('cmr10', 0xa2),
    '\\Gamma'                    : ('cmr10', 0xa1),
    '\\Lambda'                   : ('cmr10', 0xa4),
    '\\Omega'                    : ('cmr10', 0xad),
    '\\Phi'                      : ('cmr10', 0xa9),
    '\\Pi'                       : ('cmr10', 0xa6),
    '\\Psi'                      : ('cmr10', 0xaa),
    '\\Sigma'                    : ('cmr10', 0xa7),
    '\\Theta'                    : ('cmr10', 0xa3),
    '\\Upsilon'                  : ('cmr10', 0xa8),
    '\\Xi'                       : ('cmr10', 0xa5),
    '\\circumflexaccent'         : ('cmr10', 0x5e),
    '\\combiningacuteaccent'     : ('cmr10', 0xb6),
    '\\combiningbreve'           : ('cmr10', 0xb8),
    '\\combiningdiaeresis'       : ('cmr10', 0xc4),
    '\\combiningdotabove'        : ('cmr10', 0x5f),
    '\\combininggraveaccent'     : ('cmr10', 0xb5),
    '\\combiningoverline'        : ('cmr10', 0xb9),
    '\\combiningtilde'           : ('cmr10', 0x7e),
    '\\leftbracket'              : ('cmr10', 0x5b),
    '\\leftparen'                : ('cmr10', 0x28),
    '\\rightbracket'             : ('cmr10', 0x5d),
    '\\rightparen'               : ('cmr10', 0x29),
    '\\widebar'                  : ('cmr10', 0xb9),
    ']'                          : ('cmr10', 0x5d),

    '*'                          : ('cmsy10', 0xa4),
    '\N{MINUS SIGN}'             : ('cmsy10', 0xa1),
    '\\Downarrow'                : ('cmsy10', 0x2b),
    '\\Im'                       : ('cmsy10', 0x3d),
    '\\Leftarrow'                : ('cmsy10', 0x28),
    '\\Leftrightarrow'           : ('cmsy10', 0x2c),
    '\\P'                        : ('cmsy10', 0x7b),
    '\\Re'                       : ('cmsy10', 0x3c),
    '\\Rightarrow'               : ('cmsy10', 0x29),
    '\\S'                        : ('cmsy10', 0x78),
    '\\Uparrow'                  : ('cmsy10', 0x2a),
    '\\Updownarrow'              : ('cmsy10', 0x6d),
    '\\Vert'                     : ('cmsy10', 0x6b),
    '\\aleph'                    : ('cmsy10', 0x40),
    '\\approx'                   : ('cmsy10', 0xbc),
    '\\ast'                      : ('cmsy10', 0xa4),
    '\\asymp'                    : ('cmsy10', 0xb3),
    '\\backslash'                : ('cmsy10', 0x6e),
    '\\bigcirc'                  : ('cmsy10', 0xb0),
    '\\bigtriangledown'          : ('cmsy10', 0x35),
    '\\bigtriangleup'            : ('cmsy10', 0x34),
    '\\bot'                      : ('cmsy10', 0x3f),
    '\\bullet'                   : ('cmsy10', 0xb2),
    '\\cap'                      : ('cmsy10', 0x5c),
    '\\cdot'                     : ('cmsy10', 0xa2),
    '\\circ'                     : ('cmsy10', 0xb1),
    '\\clubsuit'                 : ('cmsy10', 0x7c),
    '\\cup'                      : ('cmsy10', 0x5b),
    '\\dag'                      : ('cmsy10', 0x79),
    '\\dashv'                    : ('cmsy10', 0x61),
    '\\ddag'                     : ('cmsy10', 0x7a),
    '\\diamond'                  : ('cmsy10', 0xa6),
    '\\diamondsuit'              : ('cmsy10', 0x7d),
    '\\div'                      : ('cmsy10', 0xa5),
    '\\downarrow'                : ('cmsy10', 0x23),
    '\\emptyset'                 : ('cmsy10', 0x3b),
    '\\equiv'                    : ('cmsy10', 0xb4),
    '\\exists'                   : ('cmsy10', 0x39),
    '\\forall'                   : ('cmsy10', 0x38),
    '\\geq'                      : ('cmsy10', 0xb8),
    '\\gg'                       : ('cmsy10', 0xc0),
    '\\heartsuit'                : ('cmsy10', 0x7e),
    '\\in'                       : ('cmsy10', 0x32),
    '\\infty'                    : ('cmsy10', 0x31),
    '\\lbrace'                   : ('cmsy10', 0x66),
    '\\lceil'                    : ('cmsy10', 0x64),
    '\\leftarrow'                : ('cmsy10', 0xc3),
    '\\leftrightarrow'           : ('cmsy10', 0x24),
    '\\leq'                      : ('cmsy10', 0x2219),
    '\\lfloor'                   : ('cmsy10', 0x62),
    '\\ll'                       : ('cmsy10', 0xbf),
    '\\mid'                      : ('cmsy10', 0x6a),
    '\\mp'                       : ('cmsy10', 0xa8),
    '\\nabla'                    : ('cmsy10', 0x72),
    '\\nearrow'                  : ('cmsy10', 0x25),
    '\\neg'                      : ('cmsy10', 0x3a),
    '\\ni'                       : ('cmsy10', 0x33),
    '\\nwarrow'                  : ('cmsy10', 0x2d),
    '\\odot'                     : ('cmsy10', 0xaf),
    '\\ominus'                   : ('cmsy10', 0xaa),
    '\\oplus'                    : ('cmsy10', 0xa9),
    '\\oslash'                   : ('cmsy10', 0xae),
    '\\otimes'                   : ('cmsy10', 0xad),
    '\\pm'                       : ('cmsy10', 0xa7),
    '\\prec'                     : ('cmsy10', 0xc1),
    '\\preceq'                   : ('cmsy10', 0xb9),
    '\\prime'                    : ('cmsy10', 0x30),
    '\\propto'                   : ('cmsy10', 0x2f),
    '\\rbrace'                   : ('cmsy10', 0x67),
    '\\rceil'                    : ('cmsy10', 0x65),
    '\\rfloor'                   : ('cmsy10', 0x63),
    '\\rightarrow'               : ('cmsy10', 0x21),
    '\\searrow'                  : ('cmsy10', 0x26),
    '\\sim'                      : ('cmsy10', 0xbb),
    '\\simeq'                    : ('cmsy10', 0x27),
    '\\slash'                    : ('cmsy10', 0x36),
    '\\spadesuit'                : ('cmsy10', 0xc4),
    '\\sqcap'                    : ('cmsy10', 0x75),
    '\\sqcup'                    : ('cmsy10', 0x74),
    '\\sqsubseteq'               : ('cmsy10', 0x76),
    '\\sqsupseteq'               : ('cmsy10', 0x77),
    '\\subset'                   : ('cmsy10', 0xbd),
    '\\subseteq'                 : ('cmsy10', 0xb5),
    '\\succ'                     : ('cmsy10', 0xc2),
    '\\succeq'                   : ('cmsy10', 0xba),
    '\\supset'                   : ('cmsy10', 0xbe),
    '\\supseteq'                 : ('cmsy10', 0xb6),
    '\\swarrow'                  : ('cmsy10', 0x2e),
    '\\times'                    : ('cmsy10', 0xa3),
    '\\to'                       : ('cmsy10', 0x21),
    '\\top'                      : ('cmsy10', 0x3e),
    '\\uparrow'                  : ('cmsy10', 0x22),
    '\\updownarrow'              : ('cmsy10', 0x6c),
    '\\uplus'                    : ('cmsy10', 0x5d),
    '\\vdash'                    : ('cmsy10', 0x60),
    '\\vee'                      : ('cmsy10', 0x5f),
    '\\vert'                     : ('cmsy10', 0x6a),
    '\\wedge'                    : ('cmsy10', 0x5e),
    '\\wr'                       : ('cmsy10', 0x6f),
    '\\|'                        : ('cmsy10', 0x6b),
    '|'                          : ('cmsy10', 0x6a),

    '\\_'                        : ('cmtt10', 0x5f)
}

# Automatically generated.

type12uni = {
    'aring'          : 229,
    'quotedblright'  : 8221,
    'V'              : 86,
    'dollar'         : 36,
    'four'           : 52,
    'Yacute'         : 221,
    'P'              : 80,
    'underscore'     : 95,
    'p'              : 112,
    'Otilde'         : 213,
    'perthousand'    : 8240,
    'zero'           : 48,
    'dotlessi'       : 305,
    'Scaron'         : 352,
    'zcaron'         : 382,
    'egrave'         : 232,
    'section'        : 167,
    'Icircumflex'    : 206,
    'ntilde'         : 241,
    'ampersand'      : 38,
    'dotaccent'      : 729,
    'degree'         : 176,
    'K'              : 75,
    'acircumflex'    : 226,
    'Aring'          : 197,
    'k'              : 107,
    'smalltilde'     : 732,
    'Agrave'         : 192,
    'divide'         : 247,
    'ocircumflex'    : 244,
    'asciitilde'     : 126,
    'two'            : 50,
    'E'              : 69,
    'scaron'         : 353,
    'F'              : 70,
    'bracketleft'    : 91,
    'asciicircum'    : 94,
    'f'              : 102,
    'ordmasculine'   : 186,
    'mu'             : 181,
    'paragraph'      : 182,
    'nine'           : 57,
    'v'              : 118,
    'guilsinglleft'  : 8249,
    'backslash'      : 92,
    'six'            : 54,
    'A'              : 65,
    'icircumflex'    : 238,
    'a'              : 97,
    'ogonek'         : 731,
    'q'              : 113,
    'oacute'         : 243,
    'ograve'         : 242,
    'edieresis'      : 235,
    'comma'          : 44,
    'otilde'         : 245,
    'guillemotright' : 187,
    'ecircumflex'    : 234,
    'greater'        : 62,
    'uacute'         : 250,
    'L'              : 76,
    'bullet'         : 8226,
    'cedilla'        : 184,
    'ydieresis'      : 255,
    'l'              : 108,
    'logicalnot'     : 172,
    'exclamdown'     : 161,
    'endash'         : 8211,
    'agrave'         : 224,
    'Adieresis'      : 196,
    'germandbls'     : 223,
    'Odieresis'      : 214,
    'space'          : 32,
    'quoteright'     : 8217,
    'ucircumflex'    : 251,
    'G'              : 71,
    'quoteleft'      : 8216,
    'W'              : 87,
    'Q'              : 81,
    'g'              : 103,
    'w'              : 119,
    'question'       : 63,
    'one'            : 49,
    'ring'           : 730,
    'figuredash'     : 8210,
    'B'              : 66,
    'iacute'         : 237,
    'Ydieresis'      : 376,
    'R'              : 82,
    'b'              : 98,
    'r'              : 114,
    'Ccedilla'       : 199,
    'minus'          : 8722,
    'Lslash'         : 321,
    'Uacute'         : 218,
    'yacute'         : 253,
    'Ucircumflex'    : 219,
    'quotedbl'       : 34,
    'onehalf'        : 189,
    'Thorn'          : 222,
    'M'              : 77,
    'eight'          : 56,
    'multiply'       : 215,
    'grave'          : 96,
    'Ocircumflex'    : 212,
    'm'              : 109,
    'Ugrave'         : 217,
    'guilsinglright' : 8250,
    'Ntilde'         : 209,
    'questiondown'   : 191,
    'Atilde'         : 195,
    'ccedilla'       : 231,
    'Z'              : 90,
    'copyright'      : 169,
    'yen'            : 165,
    'Eacute'         : 201,
    'H'              : 72,
    'X'              : 88,
    'Idieresis'      : 207,
    'bar'            : 124,
    'h'              : 104,
    'x'              : 120,
    'udieresis'      : 252,
    'ordfeminine'    : 170,
    'braceleft'      : 123,
    'macron'         : 175,
    'atilde'         : 227,
    'Acircumflex'    : 194,
    'Oslash'         : 216,
    'C'              : 67,
    'quotedblleft'   : 8220,
    'S'              : 83,
    'exclam'         : 33,
    'Zcaron'         : 381,
    'equal'          : 61,
    's'              : 115,
    'eth'            : 240,
    'Egrave'         : 200,
    'hyphen'         : 45,
    'period'         : 46,
    'igrave'         : 236,
    'colon'          : 58,
    'Ecircumflex'    : 202,
    'trademark'      : 8482,
    'Aacute'         : 193,
    'cent'           : 162,
    'lslash'         : 322,
    'c'              : 99,
    'N'              : 78,
    'breve'          : 728,
    'Oacute'         : 211,
    'guillemotleft'  : 171,
    'n'              : 110,
    'idieresis'      : 239,
    'braceright'     : 125,
    'seven'          : 55,
    'brokenbar'      : 166,
    'ugrave'         : 249,
    'periodcentered' : 183,
    'sterling'       : 163,
    'I'              : 73,
    'Y'              : 89,
    'Eth'            : 208,
    'emdash'         : 8212,
    'i'              : 105,
    'daggerdbl'      : 8225,
    'y'              : 121,
    'plusminus'      : 177,
    'less'           : 60,
    'Udieresis'      : 220,
    'D'              : 68,
    'five'           : 53,
    'T'              : 84,
    'oslash'         : 248,
    'acute'          : 180,
    'd'              : 100,
    'OE'             : 338,
    'Igrave'         : 204,
    't'              : 116,
    'parenright'     : 41,
    'adieresis'      : 228,
    'quotesingle'    : 39,
    'twodotenleader' : 8229,
    'slash'          : 47,
    'ellipsis'       : 8230,
    'numbersign'     : 35,
    'odieresis'      : 246,
    'O'              : 79,
    'oe'             : 339,
    'o'              : 111,
    'Edieresis'      : 203,
    'plus'           : 43,
    'dagger'         : 8224,
    'three'          : 51,
    'hungarumlaut'   : 733,
    'parenleft'      : 40,
    'fraction'       : 8260,
    'registered'     : 174,
    'J'              : 74,
    'dieresis'       : 168,
    'Ograve'         : 210,
    'j'              : 106,
    'z'              : 122,
    'ae'             : 230,
    'semicolon'      : 59,
    'at'             : 64,
    'Iacute'         : 205,
    'percent'        : 37,
    'bracketright'   : 93,
    'AE'             : 198,
    'asterisk'       : 42,
    'aacute'         : 225,
    'U'              : 85,
    'eacute'         : 233,
    'e'              : 101,
    'thorn'          : 254,
    'u'              : 117,
}

uni2type1 = {v: k for k, v in type12uni.items()}

#  The script below is to sort and format the tex2uni dict

## For decimal values: int(hex(v), 16)
#  newtex = {k: hex(v) for k, v in tex2uni.items()}
#  sd = dict(sorted(newtex.items(), key=lambda item: item[0]))
#
## For formatting the sorted dictionary with proper spacing
## the value '24' comes from finding the longest string in
## the newtex keys with len(max(newtex, key=len))
#  for key in sd:
#      print("{0:24} : {1: <s},".format("'" + key + "'", sd[key]))

tex2uni = {
    '#'                      : 0x23,
    '$'                      : 0x24,
    '%'                      : 0x25,
    'AA'                     : 0xc5,
    'AE'                     : 0xc6,
    'BbbC'                   : 0x2102,
    'BbbN'                   : 0x2115,
    'BbbP'                   : 0x2119,
    'BbbQ'                   : 0x211a,
    'BbbR'                   : 0x211d,
    'BbbZ'                   : 0x2124,
    'Bumpeq'                 : 0x224e,
    'Cap'                    : 0x22d2,
    'Colon'                  : 0x2237,
    'Cup'                    : 0x22d3,
    'DH'                     : 0xd0,
    'Delta'                  : 0x394,
    'Doteq'                  : 0x2251,
    'Downarrow'              : 0x21d3,
    'Equiv'                  : 0x2263,
    'Finv'                   : 0x2132,
    'Game'                   : 0x2141,
    'Gamma'                  : 0x393,
    'H'                      : 0x30b,
    'Im'                     : 0x2111,
    'Join'                   : 0x2a1d,
    'L'                      : 0x141,
    'Lambda'                 : 0x39b,
    'Ldsh'                   : 0x21b2,
    'Leftarrow'              : 0x21d0,
    'Leftrightarrow'         : 0x21d4,
    'Lleftarrow'             : 0x21da,
    'Longleftarrow'          : 0x27f8,
    'Longleftrightarrow'     : 0x27fa,
    'Longrightarrow'         : 0x27f9,
    'Lsh'                    : 0x21b0,
    'Nearrow'                : 0x21d7,
    'Nwarrow'                : 0x21d6,
    'O'                      : 0xd8,
    'OE'                     : 0x152,
    'Omega'                  : 0x3a9,
    'P'                      : 0xb6,
    'Phi'                    : 0x3a6,
    'Pi'                     : 0x3a0,
    'Psi'                    : 0x3a8,
    'QED'                    : 0x220e,
    'Rdsh'                   : 0x21b3,
    'Re'                     : 0x211c,
    'Rightarrow'             : 0x21d2,
    'Rrightarrow'            : 0x21db,
    'Rsh'                    : 0x21b1,
    'S'                      : 0xa7,
    'Searrow'                : 0x21d8,
    'Sigma'                  : 0x3a3,
    'Subset'                 : 0x22d0,
    'Supset'                 : 0x22d1,
    'Swarrow'                : 0x21d9,
    'Theta'                  : 0x398,
    'Thorn'                  : 0xde,
    'Uparrow'                : 0x21d1,
    'Updownarrow'            : 0x21d5,
    'Upsilon'                : 0x3a5,
    'Vdash'                  : 0x22a9,
    'Vert'                   : 0x2016,
    'Vvdash'                 : 0x22aa,
    'Xi'                     : 0x39e,
    '_'                      : 0x5f,
    '__sqrt__'               : 0x221a,
    'aa'                     : 0xe5,
    'ac'                     : 0x223e,
    'acute'                  : 0x301,
    'acwopencirclearrow'     : 0x21ba,
    'adots'                  : 0x22f0,
    'ae'                     : 0xe6,
    'aleph'                  : 0x2135,
    'alpha'                  : 0x3b1,
    'amalg'                  : 0x2a3f,
    'angle'                  : 0x2220,
    'approx'                 : 0x2248,
    'approxeq'               : 0x224a,
    'approxident'            : 0x224b,
    'arceq'                  : 0x2258,
    'ast'                    : 0x2217,
    'asterisk'               : 0x2a,
    'asymp'                  : 0x224d,
    'backcong'               : 0x224c,
    'backepsilon'            : 0x3f6,
    'backprime'              : 0x2035,
    'backsim'                : 0x223d,
    'backsimeq'              : 0x22cd,
    'backslash'              : 0x5c,
    'bagmember'              : 0x22ff,
    'bar'                    : 0x304,
    'barleftarrow'           : 0x21e4,
    'barvee'                 : 0x22bd,
    'barwedge'               : 0x22bc,
    'because'                : 0x2235,
    'beta'                   : 0x3b2,
    'beth'                   : 0x2136,
    'between'                : 0x226c,
    'bigcap'                 : 0x22c2,
    'bigcirc'                : 0x25cb,
    'bigcup'                 : 0x22c3,
    'bigodot'                : 0x2a00,
    'bigoplus'               : 0x2a01,
    'bigotimes'              : 0x2a02,
    'bigsqcup'               : 0x2a06,
    'bigstar'                : 0x2605,
    'bigtriangledown'        : 0x25bd,
    'bigtriangleup'          : 0x25b3,
    'biguplus'               : 0x2a04,
    'bigvee'                 : 0x22c1,
    'bigwedge'               : 0x22c0,
    'blacksquare'            : 0x25a0,
    'blacktriangle'          : 0x25b4,
    'blacktriangledown'      : 0x25be,
    'blacktriangleleft'      : 0x25c0,
    'blacktriangleright'     : 0x25b6,
    'bot'                    : 0x22a5,
    'bowtie'                 : 0x22c8,
    'boxbar'                 : 0x25eb,
    'boxdot'                 : 0x22a1,
    'boxminus'               : 0x229f,
    'boxplus'                : 0x229e,
    'boxtimes'               : 0x22a0,
    'breve'                  : 0x306,
    'bullet'                 : 0x2219,
    'bumpeq'                 : 0x224f,
    'c'                      : 0x327,
    'candra'                 : 0x310,
    'cap'                    : 0x2229,
    'carriagereturn'         : 0x21b5,
    'cdot'                   : 0x22c5,
    'cdotp'                  : 0xb7,
    'cdots'                  : 0x22ef,
    'cent'                   : 0xa2,
    'check'                  : 0x30c,
    'checkmark'              : 0x2713,
    'chi'                    : 0x3c7,
    'circ'                   : 0x2218,
    'circeq'                 : 0x2257,
    'circlearrowleft'        : 0x21ba,
    'circlearrowright'       : 0x21bb,
    'circledR'               : 0xae,
    'circledS'               : 0x24c8,
    'circledast'             : 0x229b,
    'circledcirc'            : 0x229a,
    'circleddash'            : 0x229d,
    'circumflexaccent'       : 0x302,
    'clubsuit'               : 0x2663,
    'clubsuitopen'           : 0x2667,
    'colon'                  : 0x3a,
    'coloneq'                : 0x2254,
    'combiningacuteaccent'   : 0x301,
    'combiningbreve'         : 0x306,
    'combiningdiaeresis'     : 0x308,
    'combiningdotabove'      : 0x307,
    'combiningfourdotsabove' : 0x20dc,
    'combininggraveaccent'   : 0x300,
    'combiningoverline'      : 0x304,
    'combiningrightarrowabove' : 0x20d7,
    'combiningthreedotsabove' : 0x20db,
    'combiningtilde'         : 0x303,
    'complement'             : 0x2201,
    'cong'                   : 0x2245,
    'coprod'                 : 0x2210,
    'copyright'              : 0xa9,
    'cup'                    : 0x222a,
    'cupdot'                 : 0x228d,
    'cupleftarrow'           : 0x228c,
    'curlyeqprec'            : 0x22de,
    'curlyeqsucc'            : 0x22df,
    'curlyvee'               : 0x22ce,
    'curlywedge'             : 0x22cf,
    'curvearrowleft'         : 0x21b6,
    'curvearrowright'        : 0x21b7,
    'cwopencirclearrow'      : 0x21bb,
    'd'                      : 0x323,
    'dag'                    : 0x2020,
    'dagger'                 : 0x2020,
    'daleth'                 : 0x2138,
    'danger'                 : 0x2621,
    'dashleftarrow'          : 0x290e,
    'dashrightarrow'         : 0x290f,
    'dashv'                  : 0x22a3,
    'ddag'                   : 0x2021,
    'ddagger'                : 0x2021,
    'ddddot'                 : 0x20dc,
    'dddot'                  : 0x20db,
    'ddot'                   : 0x308,
    'ddots'                  : 0x22f1,
    'degree'                 : 0xb0,
    'delta'                  : 0x3b4,
    'dh'                     : 0xf0,
    'diamond'                : 0x22c4,
    'diamondsuit'            : 0x2662,
    'digamma'                : 0x3dd,
    'disin'                  : 0x22f2,
    'div'                    : 0xf7,
    'divideontimes'          : 0x22c7,
    'dot'                    : 0x307,
    'doteq'                  : 0x2250,
    'doteqdot'               : 0x2251,
    'dotminus'               : 0x2238,
    'dotplus'                : 0x2214,
    'dots'                   : 0x2026,
    'dotsminusdots'          : 0x223a,
    'doublebarwedge'         : 0x2306,
    'downarrow'              : 0x2193,
    'downdownarrows'         : 0x21ca,
    'downharpoonleft'        : 0x21c3,
    'downharpoonright'       : 0x21c2,
    'downzigzagarrow'        : 0x21af,
    'ell'                    : 0x2113,
    'emdash'                 : 0x2014,
    'emptyset'               : 0x2205,
    'endash'                 : 0x2013,
    'epsilon'                : 0x3b5,
    'eqcirc'                 : 0x2256,
    'eqcolon'                : 0x2255,
    'eqdef'                  : 0x225d,
    'eqgtr'                  : 0x22dd,
    'eqless'                 : 0x22dc,
    'eqsim'                  : 0x2242,
    'eqslantgtr'             : 0x2a96,
    'eqslantless'            : 0x2a95,
    'equal'                  : 0x3d,
    'equalparallel'          : 0x22d5,
    'equiv'                  : 0x2261,
    'eta'                    : 0x3b7,
    'eth'                    : 0xf0,
    'exists'                 : 0x2203,
    'fallingdotseq'          : 0x2252,
    'flat'                   : 0x266d,
    'forall'                 : 0x2200,
    'frakC'                  : 0x212d,
    'frakZ'                  : 0x2128,
    'frown'                  : 0x2322,
    'gamma'                  : 0x3b3,
    'geq'                    : 0x2265,
    'geqq'                   : 0x2267,
    'geqslant'               : 0x2a7e,
    'gg'                     : 0x226b,
    'ggg'                    : 0x22d9,
    'gimel'                  : 0x2137,
    'gnapprox'               : 0x2a8a,
    'gneqq'                  : 0x2269,
    'gnsim'                  : 0x22e7,
    'grave'                  : 0x300,
    'greater'                : 0x3e,
    'gtrapprox'              : 0x2a86,
    'gtrdot'                 : 0x22d7,
    'gtreqless'              : 0x22db,
    'gtreqqless'             : 0x2a8c,
    'gtrless'                : 0x2277,
    'gtrsim'                 : 0x2273,
    'guillemotleft'          : 0xab,
    'guillemotright'         : 0xbb,
    'guilsinglleft'          : 0x2039,
    'guilsinglright'         : 0x203a,
    'hat'                    : 0x302,
    'hbar'                   : 0x127,
    'heartsuit'              : 0x2661,
    'hermitmatrix'           : 0x22b9,
    'hookleftarrow'          : 0x21a9,
    'hookrightarrow'         : 0x21aa,
    'hslash'                 : 0x210f,
    'i'                      : 0x131,
    'iiiint'                 : 0x2a0c,
    'iiint'                  : 0x222d,
    'iint'                   : 0x222c,
    'imageof'                : 0x22b7,
    'imath'                  : 0x131,
    'in'                     : 0x2208,
    'increment'              : 0x2206,
    'infty'                  : 0x221e,
    'int'                    : 0x222b,
    'intercal'               : 0x22ba,
    'invnot'                 : 0x2310,
    'iota'                   : 0x3b9,
    'isinE'                  : 0x22f9,
    'isindot'                : 0x22f5,
    'isinobar'               : 0x22f7,
    'isins'                  : 0x22f4,
    'isinvb'                 : 0x22f8,
    'jmath'                  : 0x237,
    'k'                      : 0x328,
    'kappa'                  : 0x3ba,
    'kernelcontraction'      : 0x223b,
    'l'                      : 0x142,
    'lambda'                 : 0x3bb,
    'lambdabar'              : 0x19b,
    'langle'                 : 0x27e8,
    'lasp'                   : 0x2bd,
    'lbrace'                 : 0x7b,
    'lbrack'                 : 0x5b,
    'lceil'                  : 0x2308,
    'ldots'                  : 0x2026,
    'leadsto'                : 0x21dd,
    'leftarrow'              : 0x2190,
    'leftarrowtail'          : 0x21a2,
    'leftbrace'              : 0x7b,
    'leftharpoonaccent'      : 0x20d0,
    'leftharpoondown'        : 0x21bd,
    'leftharpoonup'          : 0x21bc,
    'leftleftarrows'         : 0x21c7,
    'leftparen'              : 0x28,
    'leftrightarrow'         : 0x2194,
    'leftrightarrows'        : 0x21c6,
    'leftrightharpoons'      : 0x21cb,
    'leftrightsquigarrow'    : 0x21ad,
    'leftsquigarrow'         : 0x219c,
    'leftthreetimes'         : 0x22cb,
    'leq'                    : 0x2264,
    'leqq'                   : 0x2266,
    'leqslant'               : 0x2a7d,
    'less'                   : 0x3c,
    'lessapprox'             : 0x2a85,
    'lessdot'                : 0x22d6,
    'lesseqgtr'              : 0x22da,
    'lesseqqgtr'             : 0x2a8b,
    'lessgtr'                : 0x2276,
    'lesssim'                : 0x2272,
    'lfloor'                 : 0x230a,
    'lgroup'                 : 0x27ee,
    'lhd'                    : 0x25c1,
    'll'                     : 0x226a,
    'llcorner'               : 0x231e,
    'lll'                    : 0x22d8,
    'lnapprox'               : 0x2a89,
    'lneqq'                  : 0x2268,
    'lnsim'                  : 0x22e6,
    'longleftarrow'          : 0x27f5,
    'longleftrightarrow'     : 0x27f7,
    'longmapsto'             : 0x27fc,
    'longrightarrow'         : 0x27f6,
    'looparrowleft'          : 0x21ab,
    'looparrowright'         : 0x21ac,
    'lq'                     : 0x2018,
    'lrcorner'               : 0x231f,
    'ltimes'                 : 0x22c9,
    'macron'                 : 0xaf,
    'maltese'                : 0x2720,
    'mapsdown'               : 0x21a7,
    'mapsfrom'               : 0x21a4,
    'mapsto'                 : 0x21a6,
    'mapsup'                 : 0x21a5,
    'measeq'                 : 0x225e,
    'measuredangle'          : 0x2221,
    'measuredrightangle'     : 0x22be,
    'merge'                  : 0x2a55,
    'mho'                    : 0x2127,
    'mid'                    : 0x2223,
    'minus'                  : 0x2212,
    'minuscolon'             : 0x2239,
    'models'                 : 0x22a7,
    'mp'                     : 0x2213,
    'mu'                     : 0x3bc,
    'multimap'               : 0x22b8,
    'nLeftarrow'             : 0x21cd,
    'nLeftrightarrow'        : 0x21ce,
    'nRightarrow'            : 0x21cf,
    'nVDash'                 : 0x22af,
    'nVdash'                 : 0x22ae,
    'nabla'                  : 0x2207,
    'napprox'                : 0x2249,
    'natural'                : 0x266e,
    'ncong'                  : 0x2247,
    'ne'                     : 0x2260,
    'nearrow'                : 0x2197,
    'neg'                    : 0xac,
    'neq'                    : 0x2260,
    'nequiv'                 : 0x2262,
    'nexists'                : 0x2204,
    'ngeq'                   : 0x2271,
    'ngtr'                   : 0x226f,
    'ngtrless'               : 0x2279,
    'ngtrsim'                : 0x2275,
    'ni'                     : 0x220b,
    'niobar'                 : 0x22fe,
    'nis'                    : 0x22fc,
    'nisd'                   : 0x22fa,
    'nleftarrow'             : 0x219a,
    'nleftrightarrow'        : 0x21ae,
    'nleq'                   : 0x2270,
    'nless'                  : 0x226e,
    'nlessgtr'               : 0x2278,
    'nlesssim'               : 0x2274,
    'nmid'                   : 0x2224,
    'not'                    : 0x338,
    'notin'                  : 0x2209,
    'notsmallowns'           : 0x220c,
    'nparallel'              : 0x2226,
    'nprec'                  : 0x2280,
    'npreccurlyeq'           : 0x22e0,
    'nrightarrow'            : 0x219b,
    'nsim'                   : 0x2241,
    'nsimeq'                 : 0x2244,
    'nsqsubseteq'            : 0x22e2,
    'nsqsupseteq'            : 0x22e3,
    'nsubset'                : 0x2284,
    'nsubseteq'              : 0x2288,
    'nsucc'                  : 0x2281,
    'nsucccurlyeq'           : 0x22e1,
    'nsupset'                : 0x2285,
    'nsupseteq'              : 0x2289,
    'ntriangleleft'          : 0x22ea,
    'ntrianglelefteq'        : 0x22ec,
    'ntriangleright'         : 0x22eb,
    'ntrianglerighteq'       : 0x22ed,
    'nu'                     : 0x3bd,
    'nvDash'                 : 0x22ad,
    'nvdash'                 : 0x22ac,
    'nwarrow'                : 0x2196,
    'o'                      : 0xf8,
    'obar'                   : 0x233d,
    'ocirc'                  : 0x30a,
    'odot'                   : 0x2299,
    'oe'                     : 0x153,
    'oequal'                 : 0x229c,
    'oiiint'                 : 0x2230,
    'oiint'                  : 0x222f,
    'oint'                   : 0x222e,
    'omega'                  : 0x3c9,
    'ominus'                 : 0x2296,
    'oplus'                  : 0x2295,
    'origof'                 : 0x22b6,
    'oslash'                 : 0x2298,
    'otimes'                 : 0x2297,
    'overarc'                : 0x311,
    'overleftarrow'          : 0x20d6,
    'overleftrightarrow'     : 0x20e1,
    'parallel'               : 0x2225,
    'partial'                : 0x2202,
    'perp'                   : 0x27c2,
    'perthousand'            : 0x2030,
    'phi'                    : 0x3d5,
    'pi'                     : 0x3c0,
    'pitchfork'              : 0x22d4,
    'plus'                   : 0x2b,
    'pm'                     : 0xb1,
    'prec'                   : 0x227a,
    'precapprox'             : 0x2ab7,
    'preccurlyeq'            : 0x227c,
    'preceq'                 : 0x227c,
    'precnapprox'            : 0x2ab9,
    'precnsim'               : 0x22e8,
    'precsim'                : 0x227e,
    'prime'                  : 0x2032,
    'prod'                   : 0x220f,
    'propto'                 : 0x221d,
    'prurel'                 : 0x22b0,
    'psi'                    : 0x3c8,
    'quad'                   : 0x2003,
    'questeq'                : 0x225f,
    'rangle'                 : 0x27e9,
    'rasp'                   : 0x2bc,
    'ratio'                  : 0x2236,
    'rbrace'                 : 0x7d,
    'rbrack'                 : 0x5d,
    'rceil'                  : 0x2309,
    'rfloor'                 : 0x230b,
    'rgroup'                 : 0x27ef,
    'rhd'                    : 0x25b7,
    'rho'                    : 0x3c1,
    'rightModels'            : 0x22ab,
    'rightangle'             : 0x221f,
    'rightarrow'             : 0x2192,
    'rightarrowbar'          : 0x21e5,
    'rightarrowtail'         : 0x21a3,
    'rightassert'            : 0x22a6,
    'rightbrace'             : 0x7d,
    'rightharpoonaccent'     : 0x20d1,
    'rightharpoondown'       : 0x21c1,
    'rightharpoonup'         : 0x21c0,
    'rightleftarrows'        : 0x21c4,
    'rightleftharpoons'      : 0x21cc,
    'rightparen'             : 0x29,
    'rightrightarrows'       : 0x21c9,
    'rightsquigarrow'        : 0x219d,
    'rightthreetimes'        : 0x22cc,
    'rightzigzagarrow'       : 0x21dd,
    'ring'                   : 0x2da,
    'risingdotseq'           : 0x2253,
    'rq'                     : 0x2019,
    'rtimes'                 : 0x22ca,
    'scrB'                   : 0x212c,
    'scrE'                   : 0x2130,
    'scrF'                   : 0x2131,
    'scrH'                   : 0x210b,
    'scrI'                   : 0x2110,
    'scrL'                   : 0x2112,
    'scrM'                   : 0x2133,
    'scrR'                   : 0x211b,
    'scre'                   : 0x212f,
    'scrg'                   : 0x210a,
    'scro'                   : 0x2134,
    'scurel'                 : 0x22b1,
    'searrow'                : 0x2198,
    'setminus'               : 0x2216,
    'sharp'                  : 0x266f,
    'sigma'                  : 0x3c3,
    'sim'                    : 0x223c,
    'simeq'                  : 0x2243,
    'simneqq'                : 0x2246,
    'sinewave'               : 0x223f,
    'slash'                  : 0x2215,
    'smallin'                : 0x220a,
    'smallintclockwise'      : 0x2231,
    'smallointctrcclockwise' : 0x2233,
    'smallowns'              : 0x220d,
    'smallsetminus'          : 0x2216,
    'smallvarointclockwise'  : 0x2232,
    'smile'                  : 0x2323,
    'solbar'                 : 0x233f,
    'spadesuit'              : 0x2660,
    'spadesuitopen'          : 0x2664,
    'sphericalangle'         : 0x2222,
    'sqcap'                  : 0x2293,
    'sqcup'                  : 0x2294,
    'sqsubset'               : 0x228f,
    'sqsubseteq'             : 0x2291,
    'sqsubsetneq'            : 0x22e4,
    'sqsupset'               : 0x2290,
    'sqsupseteq'             : 0x2292,
    'sqsupsetneq'            : 0x22e5,
    'ss'                     : 0xdf,
    'star'                   : 0x22c6,
    'stareq'                 : 0x225b,
    'sterling'               : 0xa3,
    'subset'                 : 0x2282,
    'subseteq'               : 0x2286,
    'subseteqq'              : 0x2ac5,
    'subsetneq'              : 0x228a,
    'subsetneqq'             : 0x2acb,
    'succ'                   : 0x227b,
    'succapprox'             : 0x2ab8,
    'succcurlyeq'            : 0x227d,
    'succeq'                 : 0x227d,
    'succnapprox'            : 0x2aba,
    'succnsim'               : 0x22e9,
    'succsim'                : 0x227f,
    'sum'                    : 0x2211,
    'supset'                 : 0x2283,
    'supseteq'               : 0x2287,
    'supseteqq'              : 0x2ac6,
    'supsetneq'              : 0x228b,
    'supsetneqq'             : 0x2acc,
    'swarrow'                : 0x2199,
    't'                      : 0x361,
    'tau'                    : 0x3c4,
    'textasciiacute'         : 0xb4,
    'textasciicircum'        : 0x5e,
    'textasciigrave'         : 0x60,
    'textasciitilde'         : 0x7e,
    'textexclamdown'         : 0xa1,
    'textquestiondown'       : 0xbf,
    'textquotedblleft'       : 0x201c,
    'textquotedblright'      : 0x201d,
    'therefore'              : 0x2234,
    'theta'                  : 0x3b8,
    'thickspace'             : 0x2005,
    'thorn'                  : 0xfe,
    'tilde'                  : 0x303,
    'times'                  : 0xd7,
    'to'                     : 0x2192,
    'top'                    : 0x22a4,
    'triangle'               : 0x25b3,
    'triangledown'           : 0x25bf,
    'triangleeq'             : 0x225c,
    'triangleleft'           : 0x25c1,
    'trianglelefteq'         : 0x22b4,
    'triangleq'              : 0x225c,
    'triangleright'          : 0x25b7,
    'trianglerighteq'        : 0x22b5,
    'turnednot'              : 0x2319,
    'twoheaddownarrow'       : 0x21a1,
    'twoheadleftarrow'       : 0x219e,
    'twoheadrightarrow'      : 0x21a0,
    'twoheaduparrow'         : 0x219f,
    'ulcorner'               : 0x231c,
    'underbar'               : 0x331,
    'unlhd'                  : 0x22b4,
    'unrhd'                  : 0x22b5,
    'uparrow'                : 0x2191,
    'updownarrow'            : 0x2195,
    'updownarrowbar'         : 0x21a8,
    'updownarrows'           : 0x21c5,
    'upharpoonleft'          : 0x21bf,
    'upharpoonright'         : 0x21be,
    'uplus'                  : 0x228e,
    'upsilon'                : 0x3c5,
    'upuparrows'             : 0x21c8,
    'urcorner'               : 0x231d,
    'vDash'                  : 0x22a8,
    'varepsilon'             : 0x3b5,
    'varisinobar'            : 0x22f6,
    'varisins'               : 0x22f3,
    'varkappa'               : 0x3f0,
    'varlrtriangle'          : 0x22bf,
    'varniobar'              : 0x22fd,
    'varnis'                 : 0x22fb,
    'varnothing'             : 0x2205,
    'varphi'                 : 0x3c6,
    'varpi'                  : 0x3d6,
    'varpropto'              : 0x221d,
    'varrho'                 : 0x3f1,
    'varsigma'               : 0x3c2,
    'vartheta'               : 0x3d1,
    'vartriangle'            : 0x25b5,
    'vartriangleleft'        : 0x22b2,
    'vartriangleright'       : 0x22b3,
    'vdash'                  : 0x22a2,
    'vdots'                  : 0x22ee,
    'vec'                    : 0x20d7,
    'vee'                    : 0x2228,
    'veebar'                 : 0x22bb,
    'veeeq'                  : 0x225a,
    'vert'                   : 0x7c,
    'wedge'                  : 0x2227,
    'wedgeq'                 : 0x2259,
    'widebar'                : 0x305,
    'widehat'                : 0x302,
    'widetilde'              : 0x303,
    'wp'                     : 0x2118,
    'wr'                     : 0x2240,
    'xi'                     : 0x3be,
    'yen'                    : 0xa5,
    'zeta'                   : 0x3b6,
    '{'                      : 0x7b,
    '|'                      : 0x2016,
    '}'                      : 0x7d,
}

# Each element is a 4-tuple of the form:
#   src_start, src_end, dst_font, dst_start

_EntryTypeIn = tuple[str, str, str, str | int]
_EntryTypeOut = tuple[int, int, str, int]

_stix_virtual_fonts: dict[str, dict[str, list[_EntryTypeIn]] | list[_EntryTypeIn]] = {
    'bb': {
        "rm": [
            ("\N{DIGIT ZERO}",
             "\N{DIGIT NINE}",
             "rm",
             "\N{MATHEMATICAL DOUBLE-STRUCK DIGIT ZERO}"),
            ("\N{LATIN CAPITAL LETTER A}",
             "\N{LATIN CAPITAL LETTER B}",
             "rm",
             "\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL A}"),
            ("\N{LATIN CAPITAL LETTER C}",
             "\N{LATIN CAPITAL LETTER C}",
             "rm",
             "\N{DOUBLE-STRUCK CAPITAL C}"),
            ("\N{LATIN CAPITAL LETTER D}",
             "\N{LATIN CAPITAL LETTER G}",
             "rm",
             "\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL D}"),
            ("\N{LATIN CAPITAL LETTER H}",
             "\N{LATIN CAPITAL LETTER H}",
             "rm",
             "\N{DOUBLE-STRUCK CAPITAL H}"),
            ("\N{LATIN CAPITAL LETTER I}",
             "\N{LATIN CAPITAL LETTER M}",
             "rm",
             "\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL I}"),
            ("\N{LATIN CAPITAL LETTER N}",
             "\N{LATIN CAPITAL LETTER N}",
             "rm",
             "\N{DOUBLE-STRUCK CAPITAL N}"),
            ("\N{LATIN CAPITAL LETTER O}",
             "\N{LATIN CAPITAL LETTER O}",
             "rm",
             "\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL O}"),
            ("\N{LATIN CAPITAL LETTER P}",
             "\N{LATIN CAPITAL LETTER Q}",
             "rm",
             "\N{DOUBLE-STRUCK CAPITAL P}"),
            ("\N{LATIN CAPITAL LETTER R}",
             "\N{LATIN CAPITAL LETTER R}",
             "rm",
             "\N{DOUBLE-STRUCK CAPITAL R}"),
            ("\N{LATIN CAPITAL LETTER S}",
             "\N{LATIN CAPITAL LETTER Y}",
             "rm",
             "\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL S}"),
            ("\N{LATIN CAPITAL LETTER Z}",
             "\N{LATIN CAPITAL LETTER Z}",
             "rm",
             "\N{DOUBLE-STRUCK CAPITAL Z}"),
            ("\N{LATIN SMALL LETTER A}",
             "\N{LATIN SMALL LETTER Z}",
             "rm",
             "\N{MATHEMATICAL DOUBLE-STRUCK SMALL A}"),
            ("\N{GREEK CAPITAL LETTER GAMMA}",
             "\N{GREEK CAPITAL LETTER GAMMA}",
             "rm",
             "\N{DOUBLE-STRUCK CAPITAL GAMMA}"),
            ("\N{GREEK CAPITAL LETTER PI}",
             "\N{GREEK CAPITAL LETTER PI}",
             "rm",
             "\N{DOUBLE-STRUCK CAPITAL PI}"),
            ("\N{GREEK CAPITAL LETTER SIGMA}",
             "\N{GREEK CAPITAL LETTER SIGMA}",
             "rm",
             "\N{DOUBLE-STRUCK N-ARY SUMMATION}"),
            ("\N{GREEK SMALL LETTER GAMMA}",
             "\N{GREEK SMALL LETTER GAMMA}",
             "rm",
             "\N{DOUBLE-STRUCK SMALL GAMMA}"),
            ("\N{GREEK SMALL LETTER PI}",
             "\N{GREEK SMALL LETTER PI}",
             "rm",
             "\N{DOUBLE-STRUCK SMALL PI}"),
        ],
        "it": [
            ("\N{DIGIT ZERO}",
             "\N{DIGIT NINE}",
             "rm",
             "\N{MATHEMATICAL DOUBLE-STRUCK DIGIT ZERO}"),
            ("\N{LATIN CAPITAL LETTER A}",
             "\N{LATIN CAPITAL LETTER B}",
             "it",
             0xe154),
            ("\N{LATIN CAPITAL LETTER C}",
             "\N{LATIN CAPITAL LETTER C}",
             "it",
             "\N{DOUBLE-STRUCK CAPITAL C}"),
            ("\N{LATIN CAPITAL LETTER D}",
             "\N{LATIN CAPITAL LETTER D}",
             "it",
             "\N{DOUBLE-STRUCK ITALIC CAPITAL D}"),
            ("\N{LATIN CAPITAL LETTER E}",
             "\N{LATIN CAPITAL LETTER G}",
             "it",
             0xe156),
            ("\N{LATIN CAPITAL LETTER H}",
             "\N{LATIN CAPITAL LETTER H}",
             "it",
             "\N{DOUBLE-STRUCK CAPITAL H}"),
            ("\N{LATIN CAPITAL LETTER I}",
             "\N{LATIN CAPITAL LETTER M}",
             "it",
             0xe159),
            ("\N{LATIN CAPITAL LETTER N}",
             "\N{LATIN CAPITAL LETTER N}",
             "it",
             "\N{DOUBLE-STRUCK CAPITAL N}"),
            ("\N{LATIN CAPITAL LETTER O}",
             "\N{LATIN CAPITAL LETTER O}",
             "it",
             0xe15e),
            ("\N{LATIN CAPITAL LETTER P}",
             "\N{LATIN CAPITAL LETTER Q}",
             "it",
             "\N{DOUBLE-STRUCK CAPITAL P}"),
            ("\N{LATIN CAPITAL LETTER R}",
             "\N{LATIN CAPITAL LETTER R}",
             "it",
             "\N{DOUBLE-STRUCK CAPITAL R}"),
            ("\N{LATIN CAPITAL LETTER S}",
             "\N{LATIN CAPITAL LETTER Y}",
             "it",
             0xe15f),
            ("\N{LATIN CAPITAL LETTER Z}",
             "\N{LATIN CAPITAL LETTER Z}",
             "it",
             "\N{DOUBLE-STRUCK CAPITAL Z}"),
            ("\N{LATIN SMALL LETTER A}",
             "\N{LATIN SMALL LETTER C}",
             "it",
             0xe166),
            ("\N{LATIN SMALL LETTER D}",
             "\N{LATIN SMALL LETTER E}",
             "it",
             "\N{DOUBLE-STRUCK ITALIC SMALL D}"),
            ("\N{LATIN SMALL LETTER F}",
             "\N{LATIN SMALL LETTER H}",
             "it",
             0xe169),
            ("\N{LATIN SMALL LETTER I}",
             "\N{LATIN SMALL LETTER J}",
             "it",
             "\N{DOUBLE-STRUCK ITALIC SMALL I}"),
            ("\N{LATIN SMALL LETTER K}",
             "\N{LATIN SMALL LETTER Z}",
             "it",
             0xe16c),
            ("\N{GREEK CAPITAL LETTER GAMMA}",
             "\N{GREEK CAPITAL LETTER GAMMA}",
             "it",
             "\N{DOUBLE-STRUCK CAPITAL GAMMA}"),  # \Gamma (not in beta STIX fonts)
            ("\N{GREEK CAPITAL LETTER PI}",
             "\N{GREEK CAPITAL LETTER PI}",
             "it",
             "\N{DOUBLE-STRUCK CAPITAL PI}"),
            ("\N{GREEK CAPITAL LETTER SIGMA}",
             "\N{GREEK CAPITAL LETTER SIGMA}",
             "it",
             "\N{DOUBLE-STRUCK N-ARY SUMMATION}"),  # \Sigma (not in beta STIX fonts)
            ("\N{GREEK SMALL LETTER GAMMA}",
             "\N{GREEK SMALL LETTER GAMMA}",
             "it",
             "\N{DOUBLE-STRUCK SMALL GAMMA}"),  # \gamma (not in beta STIX fonts)
            ("\N{GREEK SMALL LETTER PI}",
             "\N{GREEK SMALL LETTER PI}",
             "it",
             "\N{DOUBLE-STRUCK SMALL PI}"),
        ],
        "bf": [
            ("\N{DIGIT ZERO}",
             "\N{DIGIT NINE}",
             "rm",
             "\N{MATHEMATICAL DOUBLE-STRUCK DIGIT ZERO}"),
            ("\N{LATIN CAPITAL LETTER A}",
             "\N{LATIN CAPITAL LETTER B}",
             "bf",
             0xe38a),
            ("\N{LATIN CAPITAL LETTER C}",
             "\N{LATIN CAPITAL LETTER C}",
             "bf",
             "\N{DOUBLE-STRUCK CAPITAL C}"),
            ("\N{LATIN CAPITAL LETTER D}",
             "\N{LATIN CAPITAL LETTER D}",
             "bf",
             "\N{DOUBLE-STRUCK ITALIC CAPITAL D}"),
            ("\N{LATIN CAPITAL LETTER E}",
             "\N{LATIN CAPITAL LETTER G}",
             "bf",
             0xe38d),
            ("\N{LATIN CAPITAL LETTER H}",
             "\N{LATIN CAPITAL LETTER H}",
             "bf",
             "\N{DOUBLE-STRUCK CAPITAL H}"),
            ("\N{LATIN CAPITAL LETTER I}",
             "\N{LATIN CAPITAL LETTER M}",
             "bf",
             0xe390),
            ("\N{LATIN CAPITAL LETTER N}",
             "\N{LATIN CAPITAL LETTER N}",
             "bf",
             "\N{DOUBLE-STRUCK CAPITAL N}"),
            ("\N{LATIN CAPITAL LETTER O}",
             "\N{LATIN CAPITAL LETTER O}",
             "bf",
             0xe395),
            ("\N{LATIN CAPITAL LETTER P}",
             "\N{LATIN CAPITAL LETTER Q}",
             "bf",
             "\N{DOUBLE-STRUCK CAPITAL P}"),
            ("\N{LATIN CAPITAL LETTER R}",
             "\N{LATIN CAPITAL LETTER R}",
             "bf",
             "\N{DOUBLE-STRUCK CAPITAL R}"),
            ("\N{LATIN CAPITAL LETTER S}",
             "\N{LATIN CAPITAL LETTER Y}",
             "bf",
             0xe396),
            ("\N{LATIN CAPITAL LETTER Z}",
             "\N{LATIN CAPITAL LETTER Z}",
             "bf",
             "\N{DOUBLE-STRUCK CAPITAL Z}"),
            ("\N{LATIN SMALL LETTER A}",
             "\N{LATIN SMALL LETTER C}",
             "bf",
             0xe39d),
            ("\N{LATIN SMALL LETTER D}",
             "\N{LATIN SMALL LETTER E}",
             "bf",
             "\N{DOUBLE-STRUCK ITALIC SMALL D}"),
            ("\N{LATIN SMALL LETTER F}",
             "\N{LATIN SMALL LETTER H}",
             "bf",
             0xe3a2),
            ("\N{LATIN SMALL LETTER I}",
             "\N{LATIN SMALL LETTER J}",
             "bf",
             "\N{DOUBLE-STRUCK ITALIC SMALL I}"),
            ("\N{LATIN SMALL LETTER K}",
             "\N{LATIN SMALL LETTER Z}",
             "bf",
             0xe3a7),
            ("\N{GREEK CAPITAL LETTER GAMMA}",
             "\N{GREEK CAPITAL LETTER GAMMA}",
             "bf",
             "\N{DOUBLE-STRUCK CAPITAL GAMMA}"),
            ("\N{GREEK CAPITAL LETTER PI}",
             "\N{GREEK CAPITAL LETTER PI}",
             "bf",
             "\N{DOUBLE-STRUCK CAPITAL PI}"),
            ("\N{GREEK CAPITAL LETTER SIGMA}",
             "\N{GREEK CAPITAL LETTER SIGMA}",
             "bf",
             "\N{DOUBLE-STRUCK N-ARY SUMMATION}"),
            ("\N{GREEK SMALL LETTER GAMMA}",
             "\N{GREEK SMALL LETTER GAMMA}",
             "bf",
             "\N{DOUBLE-STRUCK SMALL GAMMA}"),
            ("\N{GREEK SMALL LETTER PI}",
             "\N{GREEK SMALL LETTER PI}",
             "bf",
             "\N{DOUBLE-STRUCK SMALL PI}"),
        ],
    },
    'cal': [
        ("\N{LATIN CAPITAL LETTER A}",
         "\N{LATIN CAPITAL LETTER Z}",
         "it",
         0xe22d),
    ],
    'frak': {
        "rm": [
            ("\N{LATIN CAPITAL LETTER A}",
             "\N{LATIN CAPITAL LETTER B}",
             "rm",
             "\N{MATHEMATICAL FRAKTUR CAPITAL A}"),
            ("\N{LATIN CAPITAL LETTER C}",
             "\N{LATIN CAPITAL LETTER C}",
             "rm",
             "\N{BLACK-LETTER CAPITAL C}"),
            ("\N{LATIN CAPITAL LETTER D}",
             "\N{LATIN CAPITAL LETTER G}",
             "rm",
             "\N{MATHEMATICAL FRAKTUR CAPITAL D}"),
            ("\N{LATIN CAPITAL LETTER H}",
             "\N{LATIN CAPITAL LETTER H}",
             "rm",
             "\N{BLACK-LETTER CAPITAL H}"),
            ("\N{LATIN CAPITAL LETTER I}",
             "\N{LATIN CAPITAL LETTER I}",
             "rm",
             "\N{BLACK-LETTER CAPITAL I}"),
            ("\N{LATIN CAPITAL LETTER J}",
             "\N{LATIN CAPITAL LETTER Q}",
             "rm",
             "\N{MATHEMATICAL FRAKTUR CAPITAL J}"),
            ("\N{LATIN CAPITAL LETTER R}",
             "\N{LATIN CAPITAL LETTER R}",
             "rm",
             "\N{BLACK-LETTER CAPITAL R}"),
            ("\N{LATIN CAPITAL LETTER S}",
             "\N{LATIN CAPITAL LETTER Y}",
             "rm",
             "\N{MATHEMATICAL FRAKTUR CAPITAL S}"),
            ("\N{LATIN CAPITAL LETTER Z}",
             "\N{LATIN CAPITAL LETTER Z}",
             "rm",
             "\N{BLACK-LETTER CAPITAL Z}"),
            ("\N{LATIN SMALL LETTER A}",
             "\N{LATIN SMALL LETTER Z}",
             "rm",
             "\N{MATHEMATICAL FRAKTUR SMALL A}"),
            ],
        "bf": [
            ("\N{LATIN CAPITAL LETTER A}",
             "\N{LATIN CAPITAL LETTER Z}",
             "bf",
             "\N{MATHEMATICAL BOLD FRAKTUR CAPITAL A}"),
            ("\N{LATIN SMALL LETTER A}",
             "\N{LATIN SMALL LETTER Z}",
             "bf",
             "\N{MATHEMATICAL BOLD FRAKTUR SMALL A}"),
        ],
    },
    'scr': [
        ("\N{LATIN CAPITAL LETTER A}",
         "\N{LATIN CAPITAL LETTER A}",
         "it",
         "\N{MATHEMATICAL SCRIPT CAPITAL A}"),
        ("\N{LATIN CAPITAL LETTER B}",
         "\N{LATIN CAPITAL LETTER B}",
         "it",
         "\N{SCRIPT CAPITAL B}"),
        ("\N{LATIN CAPITAL LETTER C}",
         "\N{LATIN CAPITAL LETTER D}",
         "it",
         "\N{MATHEMATICAL SCRIPT CAPITAL C}"),
        ("\N{LATIN CAPITAL LETTER E}",
         "\N{LATIN CAPITAL LETTER F}",
         "it",
         "\N{SCRIPT CAPITAL E}"),
        ("\N{LATIN CAPITAL LETTER G}",
         "\N{LATIN CAPITAL LETTER G}",
         "it",
         "\N{MATHEMATICAL SCRIPT CAPITAL G}"),
        ("\N{LATIN CAPITAL LETTER H}",
         "\N{LATIN CAPITAL LETTER H}",
         "it",
         "\N{SCRIPT CAPITAL H}"),
        ("\N{LATIN CAPITAL LETTER I}",
         "\N{LATIN CAPITAL LETTER I}",
         "it",
         "\N{SCRIPT CAPITAL I}"),
        ("\N{LATIN CAPITAL LETTER J}",
         "\N{LATIN CAPITAL LETTER K}",
         "it",
         "\N{MATHEMATICAL SCRIPT CAPITAL J}"),
        ("\N{LATIN CAPITAL LETTER L}",
         "\N{LATIN CAPITAL LETTER L}",
         "it",
         "\N{SCRIPT CAPITAL L}"),
        ("\N{LATIN CAPITAL LETTER M}",
         "\N{LATIN CAPITAL LETTER M}",
         "it",
         "\N{SCRIPT CAPITAL M}"),
        ("\N{LATIN CAPITAL LETTER N}",
         "\N{LATIN CAPITAL LETTER Q}",
         "it",
         "\N{MATHEMATICAL SCRIPT CAPITAL N}"),
        ("\N{LATIN CAPITAL LETTER R}",
         "\N{LATIN CAPITAL LETTER R}",
         "it",
         "\N{SCRIPT CAPITAL R}"),
        ("\N{LATIN CAPITAL LETTER S}",
         "\N{LATIN CAPITAL LETTER Z}",
         "it",
         "\N{MATHEMATICAL SCRIPT CAPITAL S}"),
        ("\N{LATIN SMALL LETTER A}",
         "\N{LATIN SMALL LETTER D}",
         "it",
         "\N{MATHEMATICAL SCRIPT SMALL A}"),
        ("\N{LATIN SMALL LETTER E}",
         "\N{LATIN SMALL LETTER E}",
         "it",
         "\N{SCRIPT SMALL E}"),
        ("\N{LATIN SMALL LETTER F}",
         "\N{LATIN SMALL LETTER F}",
         "it",
         "\N{MATHEMATICAL SCRIPT SMALL F}"),
        ("\N{LATIN SMALL LETTER G}",
         "\N{LATIN SMALL LETTER G}",
         "it",
         "\N{SCRIPT SMALL G}"),
        ("\N{LATIN SMALL LETTER H}",
         "\N{LATIN SMALL LETTER N}",
         "it",
         "\N{MATHEMATICAL SCRIPT SMALL H}"),
        ("\N{LATIN SMALL LETTER O}",
         "\N{LATIN SMALL LETTER O}",
         "it",
         "\N{SCRIPT SMALL O}"),
        ("\N{LATIN SMALL LETTER P}",
         "\N{LATIN SMALL LETTER Z}",
         "it",
         "\N{MATHEMATICAL SCRIPT SMALL P}"),
    ],
    'sf': {
        "rm": [
            ("\N{DIGIT ZERO}",
             "\N{DIGIT NINE}",
             "rm",
             "\N{MATHEMATICAL SANS-SERIF DIGIT ZERO}"),
            ("\N{LATIN CAPITAL LETTER A}",
             "\N{LATIN CAPITAL LETTER Z}",
             "rm",
             "\N{MATHEMATICAL SANS-SERIF CAPITAL A}"),
            ("\N{LATIN SMALL LETTER A}",
             "\N{LATIN SMALL LETTER Z}",
             "rm",
             "\N{MATHEMATICAL SANS-SERIF SMALL A}"),
            ("\N{GREEK CAPITAL LETTER ALPHA}",
             "\N{GREEK CAPITAL LETTER OMEGA}",
             "rm",
             0xe17d),
            ("\N{GREEK SMALL LETTER ALPHA}",
             "\N{GREEK SMALL LETTER OMEGA}",
             "rm",
             0xe196),
            ("\N{GREEK THETA SYMBOL}",
             "\N{GREEK THETA SYMBOL}",
             "rm",
             0xe1b0),
            ("\N{GREEK PHI SYMBOL}",
             "\N{GREEK PHI SYMBOL}",
             "rm",
             0xe1b1),
            ("\N{GREEK PI SYMBOL}",
             "\N{GREEK PI SYMBOL}",
             "rm",
             0xe1b3),
            ("\N{GREEK RHO SYMBOL}",
             "\N{GREEK RHO SYMBOL}",
             "rm",
             0xe1b2),
            ("\N{GREEK LUNATE EPSILON SYMBOL}",
             "\N{GREEK LUNATE EPSILON SYMBOL}",
             "rm",
             0xe1af),
            ("\N{PARTIAL DIFFERENTIAL}",
             "\N{PARTIAL DIFFERENTIAL}",
             "rm",
             0xe17c),
        ],
        "it": [
            # These numerals are actually upright.  We don't actually
            # want italic numerals ever.
            ("\N{DIGIT ZERO}",
             "\N{DIGIT NINE}",
             "rm",
             "\N{MATHEMATICAL SANS-SERIF DIGIT ZERO}"),
            ("\N{LATIN CAPITAL LETTER A}",
             "\N{LATIN CAPITAL LETTER Z}",
             "it",
             "\N{MATHEMATICAL SANS-SERIF ITALIC CAPITAL A}"),
            ("\N{LATIN SMALL LETTER A}",
             "\N{LATIN SMALL LETTER Z}",
             "it",
             "\N{MATHEMATICAL SANS-SERIF ITALIC SMALL A}"),
            ("\N{GREEK CAPITAL LETTER ALPHA}",
             "\N{GREEK CAPITAL LETTER OMEGA}",
             "rm",
             0xe17d),
            ("\N{GREEK SMALL LETTER ALPHA}",
             "\N{GREEK SMALL LETTER OMEGA}",
             "it",
             0xe1d8),
            ("\N{GREEK THETA SYMBOL}",
             "\N{GREEK THETA SYMBOL}",
             "it",
             0xe1f2),
            ("\N{GREEK PHI SYMBOL}",
             "\N{GREEK PHI SYMBOL}",
             "it",
             0xe1f3),
            ("\N{GREEK PI SYMBOL}",
             "\N{GREEK PI SYMBOL}",
             "it",
             0xe1f5),
            ("\N{GREEK RHO SYMBOL}",
             "\N{GREEK RHO SYMBOL}",
             "it",
             0xe1f4),
            ("\N{GREEK LUNATE EPSILON SYMBOL}",
             "\N{GREEK LUNATE EPSILON SYMBOL}",
             "it",
             0xe1f1),
        ],
        "bf": [
            ("\N{DIGIT ZERO}",
             "\N{DIGIT NINE}",
             "bf",
             "\N{MATHEMATICAL SANS-SERIF BOLD DIGIT ZERO}"),
            ("\N{LATIN CAPITAL LETTER A}",
             "\N{LATIN CAPITAL LETTER Z}",
             "bf",
             "\N{MATHEMATICAL SANS-SERIF BOLD CAPITAL A}"),
            ("\N{LATIN SMALL LETTER A}",
             "\N{LATIN SMALL LETTER Z}",
             "bf",
             "\N{MATHEMATICAL SANS-SERIF BOLD SMALL A}"),
            ("\N{GREEK CAPITAL LETTER ALPHA}",
             "\N{GREEK CAPITAL LETTER OMEGA}",
             "bf",
             "\N{MATHEMATICAL SANS-SERIF BOLD CAPITAL ALPHA}"),
            ("\N{GREEK SMALL LETTER ALPHA}",
             "\N{GREEK SMALL LETTER OMEGA}",
             "bf",
             "\N{MATHEMATICAL SANS-SERIF BOLD SMALL ALPHA}"),
            ("\N{GREEK THETA SYMBOL}",
             "\N{GREEK THETA SYMBOL}",
             "bf",
             "\N{MATHEMATICAL SANS-SERIF BOLD THETA SYMBOL}"),
            ("\N{GREEK PHI SYMBOL}",
             "\N{GREEK PHI SYMBOL}",
             "bf",
             "\N{MATHEMATICAL SANS-SERIF BOLD PHI SYMBOL}"),
            ("\N{GREEK PI SYMBOL}",
             "\N{GREEK PI SYMBOL}",
             "bf",
             "\N{MATHEMATICAL SANS-SERIF BOLD PI SYMBOL}"),
            ("\N{GREEK KAPPA SYMBOL}",
             "\N{GREEK KAPPA SYMBOL}",
             "bf",
             "\N{MATHEMATICAL SANS-SERIF BOLD KAPPA SYMBOL}"),
            ("\N{GREEK RHO SYMBOL}",
             "\N{GREEK RHO SYMBOL}",
             "bf",
             "\N{MATHEMATICAL SANS-SERIF BOLD RHO SYMBOL}"),
            ("\N{GREEK LUNATE EPSILON SYMBOL}",
             "\N{GREEK LUNATE EPSILON SYMBOL}",
             "bf",
             "\N{MATHEMATICAL SANS-SERIF BOLD EPSILON SYMBOL}"),
            ("\N{PARTIAL DIFFERENTIAL}",
             "\N{PARTIAL DIFFERENTIAL}",
             "bf",
             "\N{MATHEMATICAL SANS-SERIF BOLD PARTIAL DIFFERENTIAL}"),
            ("\N{NABLA}",
             "\N{NABLA}",
             "bf",
             "\N{MATHEMATICAL SANS-SERIF BOLD NABLA}"),
        ],
        "bfit": [
            ("\N{LATIN CAPITAL LETTER A}",
             "\N{LATIN CAPITAL LETTER Z}",
             "bfit",
             "\N{MATHEMATICAL BOLD ITALIC CAPITAL A}"),
            ("\N{LATIN SMALL LETTER A}",
             "\N{LATIN SMALL LETTER Z}",
             "bfit",
             "\N{MATHEMATICAL BOLD ITALIC SMALL A}"),
            ("\N{GREEK CAPITAL LETTER GAMMA}",
             "\N{GREEK CAPITAL LETTER OMEGA}",
             "bfit",
             "\N{MATHEMATICAL BOLD ITALIC CAPITAL GAMMA}"),
            ("\N{GREEK SMALL LETTER ALPHA}",
             "\N{GREEK SMALL LETTER OMEGA}",
             "bfit",
             "\N{MATHEMATICAL BOLD ITALIC SMALL ALPHA}"),
        ],
    },
    'tt': [
        ("\N{DIGIT ZERO}",
         "\N{DIGIT NINE}",
         "rm",
         "\N{MATHEMATICAL MONOSPACE DIGIT ZERO}"),
        ("\N{LATIN CAPITAL LETTER A}",
         "\N{LATIN CAPITAL LETTER Z}",
         "rm",
         "\N{MATHEMATICAL MONOSPACE CAPITAL A}"),
        ("\N{LATIN SMALL LETTER A}",
         "\N{LATIN SMALL LETTER Z}",
         "rm",
         "\N{MATHEMATICAL MONOSPACE SMALL A}")
    ],
}


@overload
def _normalize_stix_fontcodes(d: _EntryTypeIn) -> _EntryTypeOut: ...


@overload
def _normalize_stix_fontcodes(d: list[_EntryTypeIn]) -> list[_EntryTypeOut]: ...


@overload
def _normalize_stix_fontcodes(d: dict[str, list[_EntryTypeIn] |
                                      dict[str, list[_EntryTypeIn]]]
                              ) -> dict[str, list[_EntryTypeOut] |
                                        dict[str, list[_EntryTypeOut]]]: ...


def _normalize_stix_fontcodes(d):
    if isinstance(d, tuple):
        return tuple(ord(x) if isinstance(x, str) and len(x) == 1 else x for x in d)
    elif isinstance(d, list):
        return [_normalize_stix_fontcodes(x) for x in d]
    elif isinstance(d, dict):
        return {k: _normalize_stix_fontcodes(v) for k, v in d.items()}


stix_virtual_fonts: dict[str, dict[str, list[_EntryTypeOut]] | list[_EntryTypeOut]]
stix_virtual_fonts = _normalize_stix_fontcodes(_stix_virtual_fonts)

# Free redundant list now that it has been normalized
del _stix_virtual_fonts

# Fix some incorrect glyphs.
stix_glyph_fixes = {
    # Cap and Cup glyphs are swapped.
    0x22d2: 0x22d3,
    0x22d3: 0x22d2,
}

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\audits.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Audits (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import network
from . import page
from . import runtime


@dataclass
class AffectedCookie:
    '''
    Information about a cookie that is affected by an inspector issue.
    '''
    #: The following three properties uniquely identify a cookie
    name: str

    path: str

    domain: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['path'] = self.path
        json['domain'] = self.domain
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            path=str(json['path']),
            domain=str(json['domain']),
        )


@dataclass
class AffectedRequest:
    '''
    Information about a request that is affected by an inspector issue.
    '''
    url: str

    #: The unique request id.
    request_id: typing.Optional[network.RequestId] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        if self.request_id is not None:
            json['requestId'] = self.request_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            request_id=network.RequestId.from_json(json['requestId']) if 'requestId' in json else None,
        )


@dataclass
class AffectedFrame:
    '''
    Information about the frame affected by an inspector issue.
    '''
    frame_id: page.FrameId

    def to_json(self):
        json = dict()
        json['frameId'] = self.frame_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            frame_id=page.FrameId.from_json(json['frameId']),
        )


class CookieExclusionReason(enum.Enum):
    EXCLUDE_SAME_SITE_UNSPECIFIED_TREATED_AS_LAX = "ExcludeSameSiteUnspecifiedTreatedAsLax"
    EXCLUDE_SAME_SITE_NONE_INSECURE = "ExcludeSameSiteNoneInsecure"
    EXCLUDE_SAME_SITE_LAX = "ExcludeSameSiteLax"
    EXCLUDE_SAME_SITE_STRICT = "ExcludeSameSiteStrict"
    EXCLUDE_INVALID_SAME_PARTY = "ExcludeInvalidSameParty"
    EXCLUDE_SAME_PARTY_CROSS_PARTY_CONTEXT = "ExcludeSamePartyCrossPartyContext"
    EXCLUDE_DOMAIN_NON_ASCII = "ExcludeDomainNonASCII"
    EXCLUDE_THIRD_PARTY_COOKIE_BLOCKED_IN_FIRST_PARTY_SET = "ExcludeThirdPartyCookieBlockedInFirstPartySet"
    EXCLUDE_THIRD_PARTY_PHASEOUT = "ExcludeThirdPartyPhaseout"
    EXCLUDE_PORT_MISMATCH = "ExcludePortMismatch"
    EXCLUDE_SCHEME_MISMATCH = "ExcludeSchemeMismatch"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieWarningReason(enum.Enum):
    WARN_SAME_SITE_UNSPECIFIED_CROSS_SITE_CONTEXT = "WarnSameSiteUnspecifiedCrossSiteContext"
    WARN_SAME_SITE_NONE_INSECURE = "WarnSameSiteNoneInsecure"
    WARN_SAME_SITE_UNSPECIFIED_LAX_ALLOW_UNSAFE = "WarnSameSiteUnspecifiedLaxAllowUnsafe"
    WARN_SAME_SITE_STRICT_LAX_DOWNGRADE_STRICT = "WarnSameSiteStrictLaxDowngradeStrict"
    WARN_SAME_SITE_STRICT_CROSS_DOWNGRADE_STRICT = "WarnSameSiteStrictCrossDowngradeStrict"
    WARN_SAME_SITE_STRICT_CROSS_DOWNGRADE_LAX = "WarnSameSiteStrictCrossDowngradeLax"
    WARN_SAME_SITE_LAX_CROSS_DOWNGRADE_STRICT = "WarnSameSiteLaxCrossDowngradeStrict"
    WARN_SAME_SITE_LAX_CROSS_DOWNGRADE_LAX = "WarnSameSiteLaxCrossDowngradeLax"
    WARN_ATTRIBUTE_VALUE_EXCEEDS_MAX_SIZE = "WarnAttributeValueExceedsMaxSize"
    WARN_DOMAIN_NON_ASCII = "WarnDomainNonASCII"
    WARN_THIRD_PARTY_PHASEOUT = "WarnThirdPartyPhaseout"
    WARN_CROSS_SITE_REDIRECT_DOWNGRADE_CHANGES_INCLUSION = "WarnCrossSiteRedirectDowngradeChangesInclusion"
    WARN_DEPRECATION_TRIAL_METADATA = "WarnDeprecationTrialMetadata"
    WARN_THIRD_PARTY_COOKIE_HEURISTIC = "WarnThirdPartyCookieHeuristic"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieOperation(enum.Enum):
    SET_COOKIE = "SetCookie"
    READ_COOKIE = "ReadCookie"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class InsightType(enum.Enum):
    '''
    Represents the category of insight that a cookie issue falls under.
    '''
    GIT_HUB_RESOURCE = "GitHubResource"
    GRACE_PERIOD = "GracePeriod"
    HEURISTICS = "Heuristics"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class CookieIssueInsight:
    '''
    Information about the suggested solution to a cookie issue.
    '''
    type_: InsightType

    #: Link to table entry in third-party cookie migration readiness list.
    table_entry_url: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_.to_json()
        if self.table_entry_url is not None:
            json['tableEntryUrl'] = self.table_entry_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=InsightType.from_json(json['type']),
            table_entry_url=str(json['tableEntryUrl']) if 'tableEntryUrl' in json else None,
        )


@dataclass
class CookieIssueDetails:
    '''
    This information is currently necessary, as the front-end has a difficult
    time finding a specific cookie. With this, we can convey specific error
    information without the cookie.
    '''
    cookie_warning_reasons: typing.List[CookieWarningReason]

    cookie_exclusion_reasons: typing.List[CookieExclusionReason]

    #: Optionally identifies the site-for-cookies and the cookie url, which
    #: may be used by the front-end as additional context.
    operation: CookieOperation

    #: If AffectedCookie is not set then rawCookieLine contains the raw
    #: Set-Cookie header string. This hints at a problem where the
    #: cookie line is syntactically or semantically malformed in a way
    #: that no valid cookie could be created.
    cookie: typing.Optional[AffectedCookie] = None

    raw_cookie_line: typing.Optional[str] = None

    site_for_cookies: typing.Optional[str] = None

    cookie_url: typing.Optional[str] = None

    request: typing.Optional[AffectedRequest] = None

    #: The recommended solution to the issue.
    insight: typing.Optional[CookieIssueInsight] = None

    def to_json(self):
        json = dict()
        json['cookieWarningReasons'] = [i.to_json() for i in self.cookie_warning_reasons]
        json['cookieExclusionReasons'] = [i.to_json() for i in self.cookie_exclusion_reasons]
        json['operation'] = self.operation.to_json()
        if self.cookie is not None:
            json['cookie'] = self.cookie.to_json()
        if self.raw_cookie_line is not None:
            json['rawCookieLine'] = self.raw_cookie_line
        if self.site_for_cookies is not None:
            json['siteForCookies'] = self.site_for_cookies
        if self.cookie_url is not None:
            json['cookieUrl'] = self.cookie_url
        if self.request is not None:
            json['request'] = self.request.to_json()
        if self.insight is not None:
            json['insight'] = self.insight.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cookie_warning_reasons=[CookieWarningReason.from_json(i) for i in json['cookieWarningReasons']],
            cookie_exclusion_reasons=[CookieExclusionReason.from_json(i) for i in json['cookieExclusionReasons']],
            operation=CookieOperation.from_json(json['operation']),
            cookie=AffectedCookie.from_json(json['cookie']) if 'cookie' in json else None,
            raw_cookie_line=str(json['rawCookieLine']) if 'rawCookieLine' in json else None,
            site_for_cookies=str(json['siteForCookies']) if 'siteForCookies' in json else None,
            cookie_url=str(json['cookieUrl']) if 'cookieUrl' in json else None,
            request=AffectedRequest.from_json(json['request']) if 'request' in json else None,
            insight=CookieIssueInsight.from_json(json['insight']) if 'insight' in json else None,
        )


class MixedContentResolutionStatus(enum.Enum):
    MIXED_CONTENT_BLOCKED = "MixedContentBlocked"
    MIXED_CONTENT_AUTOMATICALLY_UPGRADED = "MixedContentAutomaticallyUpgraded"
    MIXED_CONTENT_WARNING = "MixedContentWarning"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class MixedContentResourceType(enum.Enum):
    ATTRIBUTION_SRC = "AttributionSrc"
    AUDIO = "Audio"
    BEACON = "Beacon"
    CSP_REPORT = "CSPReport"
    DOWNLOAD = "Download"
    EVENT_SOURCE = "EventSource"
    FAVICON = "Favicon"
    FONT = "Font"
    FORM = "Form"
    FRAME = "Frame"
    IMAGE = "Image"
    IMPORT = "Import"
    JSON = "JSON"
    MANIFEST = "Manifest"
    PING = "Ping"
    PLUGIN_DATA = "PluginData"
    PLUGIN_RESOURCE = "PluginResource"
    PREFETCH = "Prefetch"
    RESOURCE = "Resource"
    SCRIPT = "Script"
    SERVICE_WORKER = "ServiceWorker"
    SHARED_WORKER = "SharedWorker"
    SPECULATION_RULES = "SpeculationRules"
    STYLESHEET = "Stylesheet"
    TRACK = "Track"
    VIDEO = "Video"
    WORKER = "Worker"
    XML_HTTP_REQUEST = "XMLHttpRequest"
    XSLT = "XSLT"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class MixedContentIssueDetails:
    #: The way the mixed content issue is being resolved.
    resolution_status: MixedContentResolutionStatus

    #: The unsafe http url causing the mixed content issue.
    insecure_url: str

    #: The url responsible for the call to an unsafe url.
    main_resource_url: str

    #: The type of resource causing the mixed content issue (css, js, iframe,
    #: form,...). Marked as optional because it is mapped to from
    #: blink::mojom::RequestContextType, which will be replaced
    #: by network::mojom::RequestDestination
    resource_type: typing.Optional[MixedContentResourceType] = None

    #: The mixed content request.
    #: Does not always exist (e.g. for unsafe form submission urls).
    request: typing.Optional[AffectedRequest] = None

    #: Optional because not every mixed content issue is necessarily linked to a frame.
    frame: typing.Optional[AffectedFrame] = None

    def to_json(self):
        json = dict()
        json['resolutionStatus'] = self.resolution_status.to_json()
        json['insecureURL'] = self.insecure_url
        json['mainResourceURL'] = self.main_resource_url
        if self.resource_type is not None:
            json['resourceType'] = self.resource_type.to_json()
        if self.request is not None:
            json['request'] = self.request.to_json()
        if self.frame is not None:
            json['frame'] = self.frame.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            resolution_status=MixedContentResolutionStatus.from_json(json['resolutionStatus']),
            insecure_url=str(json['insecureURL']),
            main_resource_url=str(json['mainResourceURL']),
            resource_type=MixedContentResourceType.from_json(json['resourceType']) if 'resourceType' in json else None,
            request=AffectedRequest.from_json(json['request']) if 'request' in json else None,
            frame=AffectedFrame.from_json(json['frame']) if 'frame' in json else None,
        )


class BlockedByResponseReason(enum.Enum):
    '''
    Enum indicating the reason a response has been blocked. These reasons are
    refinements of the net error BLOCKED_BY_RESPONSE.
    '''
    COEP_FRAME_RESOURCE_NEEDS_COEP_HEADER = "CoepFrameResourceNeedsCoepHeader"
    COOP_SANDBOXED_I_FRAME_CANNOT_NAVIGATE_TO_COOP_PAGE = "CoopSandboxedIFrameCannotNavigateToCoopPage"
    CORP_NOT_SAME_ORIGIN = "CorpNotSameOrigin"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_COEP = "CorpNotSameOriginAfterDefaultedToSameOriginByCoep"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_DIP = "CorpNotSameOriginAfterDefaultedToSameOriginByDip"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_COEP_AND_DIP = "CorpNotSameOriginAfterDefaultedToSameOriginByCoepAndDip"
    CORP_NOT_SAME_SITE = "CorpNotSameSite"
    SRI_MESSAGE_SIGNATURE_MISMATCH = "SRIMessageSignatureMismatch"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class BlockedByResponseIssueDetails:
    '''
    Details for a request that has been blocked with the BLOCKED_BY_RESPONSE
    code. Currently only used for COEP/COOP, but may be extended to include
    some CSP errors in the future.
    '''
    request: AffectedRequest

    reason: BlockedByResponseReason

    parent_frame: typing.Optional[AffectedFrame] = None

    blocked_frame: typing.Optional[AffectedFrame] = None

    def to_json(self):
        json = dict()
        json['request'] = self.request.to_json()
        json['reason'] = self.reason.to_json()
        if self.parent_frame is not None:
            json['parentFrame'] = self.parent_frame.to_json()
        if self.blocked_frame is not None:
            json['blockedFrame'] = self.blocked_frame.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            request=AffectedRequest.from_json(json['request']),
            reason=BlockedByResponseReason.from_json(json['reason']),
            parent_frame=AffectedFrame.from_json(json['parentFrame']) if 'parentFrame' in json else None,
            blocked_frame=AffectedFrame.from_json(json['blockedFrame']) if 'blockedFrame' in json else None,
        )


class HeavyAdResolutionStatus(enum.Enum):
    HEAVY_AD_BLOCKED = "HeavyAdBlocked"
    HEAVY_AD_WARNING = "HeavyAdWarning"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class HeavyAdReason(enum.Enum):
    NETWORK_TOTAL_LIMIT = "NetworkTotalLimit"
    CPU_TOTAL_LIMIT = "CpuTotalLimit"
    CPU_PEAK_LIMIT = "CpuPeakLimit"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class HeavyAdIssueDetails:
    #: The resolution status, either blocking the content or warning.
    resolution: HeavyAdResolutionStatus

    #: The reason the ad was blocked, total network or cpu or peak cpu.
    reason: HeavyAdReason

    #: The frame that was blocked.
    frame: AffectedFrame

    def to_json(self):
        json = dict()
        json['resolution'] = self.resolution.to_json()
        json['reason'] = self.reason.to_json()
        json['frame'] = self.frame.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            resolution=HeavyAdResolutionStatus.from_json(json['resolution']),
            reason=HeavyAdReason.from_json(json['reason']),
            frame=AffectedFrame.from_json(json['frame']),
        )


class ContentSecurityPolicyViolationType(enum.Enum):
    K_INLINE_VIOLATION = "kInlineViolation"
    K_EVAL_VIOLATION = "kEvalViolation"
    K_URL_VIOLATION = "kURLViolation"
    K_SRI_VIOLATION = "kSRIViolation"
    K_TRUSTED_TYPES_SINK_VIOLATION = "kTrustedTypesSinkViolation"
    K_TRUSTED_TYPES_POLICY_VIOLATION = "kTrustedTypesPolicyViolation"
    K_WASM_EVAL_VIOLATION = "kWasmEvalViolation"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SourceCodeLocation:
    url: str

    line_number: int

    column_number: int

    script_id: typing.Optional[runtime.ScriptId] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        if self.script_id is not None:
            json['scriptId'] = self.script_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
            script_id=runtime.ScriptId.from_json(json['scriptId']) if 'scriptId' in json else None,
        )


@dataclass
class ContentSecurityPolicyIssueDetails:
    #: Specific directive that is violated, causing the CSP issue.
    violated_directive: str

    is_report_only: bool

    content_security_policy_violation_type: ContentSecurityPolicyViolationType

    #: The url not included in allowed sources.
    blocked_url: typing.Optional[str] = None

    frame_ancestor: typing.Optional[AffectedFrame] = None

    source_code_location: typing.Optional[SourceCodeLocation] = None

    violating_node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['violatedDirective'] = self.violated_directive
        json['isReportOnly'] = self.is_report_only
        json['contentSecurityPolicyViolationType'] = self.content_security_policy_violation_type.to_json()
        if self.blocked_url is not None:
            json['blockedURL'] = self.blocked_url
        if self.frame_ancestor is not None:
            json['frameAncestor'] = self.frame_ancestor.to_json()
        if self.source_code_location is not None:
            json['sourceCodeLocation'] = self.source_code_location.to_json()
        if self.violating_node_id is not None:
            json['violatingNodeId'] = self.violating_node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            violated_directive=str(json['violatedDirective']),
            is_report_only=bool(json['isReportOnly']),
            content_security_policy_violation_type=ContentSecurityPolicyViolationType.from_json(json['contentSecurityPolicyViolationType']),
            blocked_url=str(json['blockedURL']) if 'blockedURL' in json else None,
            frame_ancestor=AffectedFrame.from_json(json['frameAncestor']) if 'frameAncestor' in json else None,
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']) if 'sourceCodeLocation' in json else None,
            violating_node_id=dom.BackendNodeId.from_json(json['violatingNodeId']) if 'violatingNodeId' in json else None,
        )


class SharedArrayBufferIssueType(enum.Enum):
    TRANSFER_ISSUE = "TransferIssue"
    CREATION_ISSUE = "CreationIssue"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SharedArrayBufferIssueDetails:
    '''
    Details for a issue arising from an SAB being instantiated in, or
    transferred to a context that is not cross-origin isolated.
    '''
    source_code_location: SourceCodeLocation

    is_warning: bool

    type_: SharedArrayBufferIssueType

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['isWarning'] = self.is_warning
        json['type'] = self.type_.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            is_warning=bool(json['isWarning']),
            type_=SharedArrayBufferIssueType.from_json(json['type']),
        )


@dataclass
class LowTextContrastIssueDetails:
    violating_node_id: dom.BackendNodeId

    violating_node_selector: str

    contrast_ratio: float

    threshold_aa: float

    threshold_aaa: float

    font_size: str

    font_weight: str

    def to_json(self):
        json = dict()
        json['violatingNodeId'] = self.violating_node_id.to_json()
        json['violatingNodeSelector'] = self.violating_node_selector
        json['contrastRatio'] = self.contrast_ratio
        json['thresholdAA'] = self.threshold_aa
        json['thresholdAAA'] = self.threshold_aaa
        json['fontSize'] = self.font_size
        json['fontWeight'] = self.font_weight
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            violating_node_id=dom.BackendNodeId.from_json(json['violatingNodeId']),
            violating_node_selector=str(json['violatingNodeSelector']),
            contrast_ratio=float(json['contrastRatio']),
            threshold_aa=float(json['thresholdAA']),
            threshold_aaa=float(json['thresholdAAA']),
            font_size=str(json['fontSize']),
            font_weight=str(json['fontWeight']),
        )


@dataclass
class CorsIssueDetails:
    '''
    Details for a CORS related issue, e.g. a warning or error related to
    CORS RFC1918 enforcement.
    '''
    cors_error_status: network.CorsErrorStatus

    is_warning: bool

    request: AffectedRequest

    location: typing.Optional[SourceCodeLocation] = None

    initiator_origin: typing.Optional[str] = None

    resource_ip_address_space: typing.Optional[network.IPAddressSpace] = None

    client_security_state: typing.Optional[network.ClientSecurityState] = None

    def to_json(self):
        json = dict()
        json['corsErrorStatus'] = self.cors_error_status.to_json()
        json['isWarning'] = self.is_warning
        json['request'] = self.request.to_json()
        if self.location is not None:
            json['location'] = self.location.to_json()
        if self.initiator_origin is not None:
            json['initiatorOrigin'] = self.initiator_origin
        if self.resource_ip_address_space is not None:
            json['resourceIPAddressSpace'] = self.resource_ip_address_space.to_json()
        if self.client_security_state is not None:
            json['clientSecurityState'] = self.client_security_state.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cors_error_status=network.CorsErrorStatus.from_json(json['corsErrorStatus']),
            is_warning=bool(json['isWarning']),
            request=AffectedRequest.from_json(json['request']),
            location=SourceCodeLocation.from_json(json['location']) if 'location' in json else None,
            initiator_origin=str(json['initiatorOrigin']) if 'initiatorOrigin' in json else None,
            resource_ip_address_space=network.IPAddressSpace.from_json(json['resourceIPAddressSpace']) if 'resourceIPAddressSpace' in json else None,
            client_security_state=network.ClientSecurityState.from_json(json['clientSecurityState']) if 'clientSecurityState' in json else None,
        )


class AttributionReportingIssueType(enum.Enum):
    PERMISSION_POLICY_DISABLED = "PermissionPolicyDisabled"
    UNTRUSTWORTHY_REPORTING_ORIGIN = "UntrustworthyReportingOrigin"
    INSECURE_CONTEXT = "InsecureContext"
    INVALID_HEADER = "InvalidHeader"
    INVALID_REGISTER_TRIGGER_HEADER = "InvalidRegisterTriggerHeader"
    SOURCE_AND_TRIGGER_HEADERS = "SourceAndTriggerHeaders"
    SOURCE_IGNORED = "SourceIgnored"
    TRIGGER_IGNORED = "TriggerIgnored"
    OS_SOURCE_IGNORED = "OsSourceIgnored"
    OS_TRIGGER_IGNORED = "OsTriggerIgnored"
    INVALID_REGISTER_OS_SOURCE_HEADER = "InvalidRegisterOsSourceHeader"
    INVALID_REGISTER_OS_TRIGGER_HEADER = "InvalidRegisterOsTriggerHeader"
    WEB_AND_OS_HEADERS = "WebAndOsHeaders"
    NO_WEB_OR_OS_SUPPORT = "NoWebOrOsSupport"
    NAVIGATION_REGISTRATION_WITHOUT_TRANSIENT_USER_ACTIVATION = "NavigationRegistrationWithoutTransientUserActivation"
    INVALID_INFO_HEADER = "InvalidInfoHeader"
    NO_REGISTER_SOURCE_HEADER = "NoRegisterSourceHeader"
    NO_REGISTER_TRIGGER_HEADER = "NoRegisterTriggerHeader"
    NO_REGISTER_OS_SOURCE_HEADER = "NoRegisterOsSourceHeader"
    NO_REGISTER_OS_TRIGGER_HEADER = "NoRegisterOsTriggerHeader"
    NAVIGATION_REGISTRATION_UNIQUE_SCOPE_ALREADY_SET = "NavigationRegistrationUniqueScopeAlreadySet"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SharedDictionaryError(enum.Enum):
    USE_ERROR_CROSS_ORIGIN_NO_CORS_REQUEST = "UseErrorCrossOriginNoCorsRequest"
    USE_ERROR_DICTIONARY_LOAD_FAILURE = "UseErrorDictionaryLoadFailure"
    USE_ERROR_MATCHING_DICTIONARY_NOT_USED = "UseErrorMatchingDictionaryNotUsed"
    USE_ERROR_UNEXPECTED_CONTENT_DICTIONARY_HEADER = "UseErrorUnexpectedContentDictionaryHeader"
    WRITE_ERROR_COSS_ORIGIN_NO_CORS_REQUEST = "WriteErrorCossOriginNoCorsRequest"
    WRITE_ERROR_DISALLOWED_BY_SETTINGS = "WriteErrorDisallowedBySettings"
    WRITE_ERROR_EXPIRED_RESPONSE = "WriteErrorExpiredResponse"
    WRITE_ERROR_FEATURE_DISABLED = "WriteErrorFeatureDisabled"
    WRITE_ERROR_INSUFFICIENT_RESOURCES = "WriteErrorInsufficientResources"
    WRITE_ERROR_INVALID_MATCH_FIELD = "WriteErrorInvalidMatchField"
    WRITE_ERROR_INVALID_STRUCTURED_HEADER = "WriteErrorInvalidStructuredHeader"
    WRITE_ERROR_NAVIGATION_REQUEST = "WriteErrorNavigationRequest"
    WRITE_ERROR_NO_MATCH_FIELD = "WriteErrorNoMatchField"
    WRITE_ERROR_NON_LIST_MATCH_DEST_FIELD = "WriteErrorNonListMatchDestField"
    WRITE_ERROR_NON_SECURE_CONTEXT = "WriteErrorNonSecureContext"
    WRITE_ERROR_NON_STRING_ID_FIELD = "WriteErrorNonStringIdField"
    WRITE_ERROR_NON_STRING_IN_MATCH_DEST_LIST = "WriteErrorNonStringInMatchDestList"
    WRITE_ERROR_NON_STRING_MATCH_FIELD = "WriteErrorNonStringMatchField"
    WRITE_ERROR_NON_TOKEN_TYPE_FIELD = "WriteErrorNonTokenTypeField"
    WRITE_ERROR_REQUEST_ABORTED = "WriteErrorRequestAborted"
    WRITE_ERROR_SHUTTING_DOWN = "WriteErrorShuttingDown"
    WRITE_ERROR_TOO_LONG_ID_FIELD = "WriteErrorTooLongIdField"
    WRITE_ERROR_UNSUPPORTED_TYPE = "WriteErrorUnsupportedType"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SRIMessageSignatureError(enum.Enum):
    MISSING_SIGNATURE_HEADER = "MissingSignatureHeader"
    MISSING_SIGNATURE_INPUT_HEADER = "MissingSignatureInputHeader"
    INVALID_SIGNATURE_HEADER = "InvalidSignatureHeader"
    INVALID_SIGNATURE_INPUT_HEADER = "InvalidSignatureInputHeader"
    SIGNATURE_HEADER_VALUE_IS_NOT_BYTE_SEQUENCE = "SignatureHeaderValueIsNotByteSequence"
    SIGNATURE_HEADER_VALUE_IS_PARAMETERIZED = "SignatureHeaderValueIsParameterized"
    SIGNATURE_HEADER_VALUE_IS_INCORRECT_LENGTH = "SignatureHeaderValueIsIncorrectLength"
    SIGNATURE_INPUT_HEADER_MISSING_LABEL = "SignatureInputHeaderMissingLabel"
    SIGNATURE_INPUT_HEADER_VALUE_NOT_INNER_LIST = "SignatureInputHeaderValueNotInnerList"
    SIGNATURE_INPUT_HEADER_VALUE_MISSING_COMPONENTS = "SignatureInputHeaderValueMissingComponents"
    SIGNATURE_INPUT_HEADER_INVALID_COMPONENT_TYPE = "SignatureInputHeaderInvalidComponentType"
    SIGNATURE_INPUT_HEADER_INVALID_COMPONENT_NAME = "SignatureInputHeaderInvalidComponentName"
    SIGNATURE_INPUT_HEADER_INVALID_HEADER_COMPONENT_PARAMETER = "SignatureInputHeaderInvalidHeaderComponentParameter"
    SIGNATURE_INPUT_HEADER_INVALID_DERIVED_COMPONENT_PARAMETER = "SignatureInputHeaderInvalidDerivedComponentParameter"
    SIGNATURE_INPUT_HEADER_KEY_ID_LENGTH = "SignatureInputHeaderKeyIdLength"
    SIGNATURE_INPUT_HEADER_INVALID_PARAMETER = "SignatureInputHeaderInvalidParameter"
    SIGNATURE_INPUT_HEADER_MISSING_REQUIRED_PARAMETERS = "SignatureInputHeaderMissingRequiredParameters"
    VALIDATION_FAILED_SIGNATURE_EXPIRED = "ValidationFailedSignatureExpired"
    VALIDATION_FAILED_INVALID_LENGTH = "ValidationFailedInvalidLength"
    VALIDATION_FAILED_SIGNATURE_MISMATCH = "ValidationFailedSignatureMismatch"
    VALIDATION_FAILED_INTEGRITY_MISMATCH = "ValidationFailedIntegrityMismatch"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AttributionReportingIssueDetails:
    '''
    Details for issues around "Attribution Reporting API" usage.
    Explainer: https://github.com/WICG/attribution-reporting-api
    '''
    violation_type: AttributionReportingIssueType

    request: typing.Optional[AffectedRequest] = None

    violating_node_id: typing.Optional[dom.BackendNodeId] = None

    invalid_parameter: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['violationType'] = self.violation_type.to_json()
        if self.request is not None:
            json['request'] = self.request.to_json()
        if self.violating_node_id is not None:
            json['violatingNodeId'] = self.violating_node_id.to_json()
        if self.invalid_parameter is not None:
            json['invalidParameter'] = self.invalid_parameter
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            violation_type=AttributionReportingIssueType.from_json(json['violationType']),
            request=AffectedRequest.from_json(json['request']) if 'request' in json else None,
            violating_node_id=dom.BackendNodeId.from_json(json['violatingNodeId']) if 'violatingNodeId' in json else None,
            invalid_parameter=str(json['invalidParameter']) if 'invalidParameter' in json else None,
        )


@dataclass
class QuirksModeIssueDetails:
    '''
    Details for issues about documents in Quirks Mode
    or Limited Quirks Mode that affects page layouting.
    '''
    #: If false, it means the document's mode is "quirks"
    #: instead of "limited-quirks".
    is_limited_quirks_mode: bool

    document_node_id: dom.BackendNodeId

    url: str

    frame_id: page.FrameId

    loader_id: network.LoaderId

    def to_json(self):
        json = dict()
        json['isLimitedQuirksMode'] = self.is_limited_quirks_mode
        json['documentNodeId'] = self.document_node_id.to_json()
        json['url'] = self.url
        json['frameId'] = self.frame_id.to_json()
        json['loaderId'] = self.loader_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            is_limited_quirks_mode=bool(json['isLimitedQuirksMode']),
            document_node_id=dom.BackendNodeId.from_json(json['documentNodeId']),
            url=str(json['url']),
            frame_id=page.FrameId.from_json(json['frameId']),
            loader_id=network.LoaderId.from_json(json['loaderId']),
        )


@dataclass
class NavigatorUserAgentIssueDetails:
    url: str

    location: typing.Optional[SourceCodeLocation] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        if self.location is not None:
            json['location'] = self.location.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            location=SourceCodeLocation.from_json(json['location']) if 'location' in json else None,
        )


@dataclass
class SharedDictionaryIssueDetails:
    shared_dictionary_error: SharedDictionaryError

    request: AffectedRequest

    def to_json(self):
        json = dict()
        json['sharedDictionaryError'] = self.shared_dictionary_error.to_json()
        json['request'] = self.request.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            shared_dictionary_error=SharedDictionaryError.from_json(json['sharedDictionaryError']),
            request=AffectedRequest.from_json(json['request']),
        )


@dataclass
class SRIMessageSignatureIssueDetails:
    error: SRIMessageSignatureError

    signature_base: str

    integrity_assertions: typing.List[str]

    request: AffectedRequest

    def to_json(self):
        json = dict()
        json['error'] = self.error.to_json()
        json['signatureBase'] = self.signature_base
        json['integrityAssertions'] = [i for i in self.integrity_assertions]
        json['request'] = self.request.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            error=SRIMessageSignatureError.from_json(json['error']),
            signature_base=str(json['signatureBase']),
            integrity_assertions=[str(i) for i in json['integrityAssertions']],
            request=AffectedRequest.from_json(json['request']),
        )


class GenericIssueErrorType(enum.Enum):
    FORM_LABEL_FOR_NAME_ERROR = "FormLabelForNameError"
    FORM_DUPLICATE_ID_FOR_INPUT_ERROR = "FormDuplicateIdForInputError"
    FORM_INPUT_WITH_NO_LABEL_ERROR = "FormInputWithNoLabelError"
    FORM_AUTOCOMPLETE_ATTRIBUTE_EMPTY_ERROR = "FormAutocompleteAttributeEmptyError"
    FORM_EMPTY_ID_AND_NAME_ATTRIBUTES_FOR_INPUT_ERROR = "FormEmptyIdAndNameAttributesForInputError"
    FORM_ARIA_LABELLED_BY_TO_NON_EXISTING_ID = "FormAriaLabelledByToNonExistingId"
    FORM_INPUT_ASSIGNED_AUTOCOMPLETE_VALUE_TO_ID_OR_NAME_ATTRIBUTE_ERROR = "FormInputAssignedAutocompleteValueToIdOrNameAttributeError"
    FORM_LABEL_HAS_NEITHER_FOR_NOR_NESTED_INPUT = "FormLabelHasNeitherForNorNestedInput"
    FORM_LABEL_FOR_MATCHES_NON_EXISTING_ID_ERROR = "FormLabelForMatchesNonExistingIdError"
    FORM_INPUT_HAS_WRONG_BUT_WELL_INTENDED_AUTOCOMPLETE_VALUE_ERROR = "FormInputHasWrongButWellIntendedAutocompleteValueError"
    RESPONSE_WAS_BLOCKED_BY_ORB = "ResponseWasBlockedByORB"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class GenericIssueDetails:
    '''
    Depending on the concrete errorType, different properties are set.
    '''
    #: Issues with the same errorType are aggregated in the frontend.
    error_type: GenericIssueErrorType

    frame_id: typing.Optional[page.FrameId] = None

    violating_node_id: typing.Optional[dom.BackendNodeId] = None

    violating_node_attribute: typing.Optional[str] = None

    request: typing.Optional[AffectedRequest] = None

    def to_json(self):
        json = dict()
        json['errorType'] = self.error_type.to_json()
        if self.frame_id is not None:
            json['frameId'] = self.frame_id.to_json()
        if self.violating_node_id is not None:
            json['violatingNodeId'] = self.violating_node_id.to_json()
        if self.violating_node_attribute is not None:
            json['violatingNodeAttribute'] = self.violating_node_attribute
        if self.request is not None:
            json['request'] = self.request.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            error_type=GenericIssueErrorType.from_json(json['errorType']),
            frame_id=page.FrameId.from_json(json['frameId']) if 'frameId' in json else None,
            violating_node_id=dom.BackendNodeId.from_json(json['violatingNodeId']) if 'violatingNodeId' in json else None,
            violating_node_attribute=str(json['violatingNodeAttribute']) if 'violatingNodeAttribute' in json else None,
            request=AffectedRequest.from_json(json['request']) if 'request' in json else None,
        )


@dataclass
class DeprecationIssueDetails:
    '''
    This issue tracks information needed to print a deprecation message.
    https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/renderer/core/frame/third_party/blink/renderer/core/frame/deprecation/README.md
    '''
    source_code_location: SourceCodeLocation

    #: One of the deprecation names from third_party/blink/renderer/core/frame/deprecation/deprecation.json5
    type_: str

    affected_frame: typing.Optional[AffectedFrame] = None

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['type'] = self.type_
        if self.affected_frame is not None:
            json['affectedFrame'] = self.affected_frame.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            type_=str(json['type']),
            affected_frame=AffectedFrame.from_json(json['affectedFrame']) if 'affectedFrame' in json else None,
        )


@dataclass
class BounceTrackingIssueDetails:
    '''
    This issue warns about sites in the redirect chain of a finished navigation
    that may be flagged as trackers and have their state cleared if they don't
    receive a user interaction. Note that in this context 'site' means eTLD+1.
    For example, if the URL ``https://example.test:80/bounce`` was in the
    redirect chain, the site reported would be ``example.test``.
    '''
    tracking_sites: typing.List[str]

    def to_json(self):
        json = dict()
        json['trackingSites'] = [i for i in self.tracking_sites]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            tracking_sites=[str(i) for i in json['trackingSites']],
        )


@dataclass
class CookieDeprecationMetadataIssueDetails:
    '''
    This issue warns about third-party sites that are accessing cookies on the
    current page, and have been permitted due to having a global metadata grant.
    Note that in this context 'site' means eTLD+1. For example, if the URL
    ``https://example.test:80/web_page`` was accessing cookies, the site reported
    would be ``example.test``.
    '''
    allowed_sites: typing.List[str]

    opt_out_percentage: float

    is_opt_out_top_level: bool

    operation: CookieOperation

    def to_json(self):
        json = dict()
        json['allowedSites'] = [i for i in self.allowed_sites]
        json['optOutPercentage'] = self.opt_out_percentage
        json['isOptOutTopLevel'] = self.is_opt_out_top_level
        json['operation'] = self.operation.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            allowed_sites=[str(i) for i in json['allowedSites']],
            opt_out_percentage=float(json['optOutPercentage']),
            is_opt_out_top_level=bool(json['isOptOutTopLevel']),
            operation=CookieOperation.from_json(json['operation']),
        )


class ClientHintIssueReason(enum.Enum):
    META_TAG_ALLOW_LIST_INVALID_ORIGIN = "MetaTagAllowListInvalidOrigin"
    META_TAG_MODIFIED_HTML = "MetaTagModifiedHTML"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class FederatedAuthRequestIssueDetails:
    federated_auth_request_issue_reason: FederatedAuthRequestIssueReason

    def to_json(self):
        json = dict()
        json['federatedAuthRequestIssueReason'] = self.federated_auth_request_issue_reason.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            federated_auth_request_issue_reason=FederatedAuthRequestIssueReason.from_json(json['federatedAuthRequestIssueReason']),
        )


class FederatedAuthRequestIssueReason(enum.Enum):
    '''
    Represents the failure reason when a federated authentication reason fails.
    Should be updated alongside RequestIdTokenStatus in
    third_party/blink/public/mojom/devtools/inspector_issue.mojom to include
    all cases except for success.
    '''
    SHOULD_EMBARGO = "ShouldEmbargo"
    TOO_MANY_REQUESTS = "TooManyRequests"
    WELL_KNOWN_HTTP_NOT_FOUND = "WellKnownHttpNotFound"
    WELL_KNOWN_NO_RESPONSE = "WellKnownNoResponse"
    WELL_KNOWN_INVALID_RESPONSE = "WellKnownInvalidResponse"
    WELL_KNOWN_LIST_EMPTY = "WellKnownListEmpty"
    WELL_KNOWN_INVALID_CONTENT_TYPE = "WellKnownInvalidContentType"
    CONFIG_NOT_IN_WELL_KNOWN = "ConfigNotInWellKnown"
    WELL_KNOWN_TOO_BIG = "WellKnownTooBig"
    CONFIG_HTTP_NOT_FOUND = "ConfigHttpNotFound"
    CONFIG_NO_RESPONSE = "ConfigNoResponse"
    CONFIG_INVALID_RESPONSE = "ConfigInvalidResponse"
    CONFIG_INVALID_CONTENT_TYPE = "ConfigInvalidContentType"
    CLIENT_METADATA_HTTP_NOT_FOUND = "ClientMetadataHttpNotFound"
    CLIENT_METADATA_NO_RESPONSE = "ClientMetadataNoResponse"
    CLIENT_METADATA_INVALID_RESPONSE = "ClientMetadataInvalidResponse"
    CLIENT_METADATA_INVALID_CONTENT_TYPE = "ClientMetadataInvalidContentType"
    IDP_NOT_POTENTIALLY_TRUSTWORTHY = "IdpNotPotentiallyTrustworthy"
    DISABLED_IN_SETTINGS = "DisabledInSettings"
    DISABLED_IN_FLAGS = "DisabledInFlags"
    ERROR_FETCHING_SIGNIN = "ErrorFetchingSignin"
    INVALID_SIGNIN_RESPONSE = "InvalidSigninResponse"
    ACCOUNTS_HTTP_NOT_FOUND = "AccountsHttpNotFound"
    ACCOUNTS_NO_RESPONSE = "AccountsNoResponse"
    ACCOUNTS_INVALID_RESPONSE = "AccountsInvalidResponse"
    ACCOUNTS_LIST_EMPTY = "AccountsListEmpty"
    ACCOUNTS_INVALID_CONTENT_TYPE = "AccountsInvalidContentType"
    ID_TOKEN_HTTP_NOT_FOUND = "IdTokenHttpNotFound"
    ID_TOKEN_NO_RESPONSE = "IdTokenNoResponse"
    ID_TOKEN_INVALID_RESPONSE = "IdTokenInvalidResponse"
    ID_TOKEN_IDP_ERROR_RESPONSE = "IdTokenIdpErrorResponse"
    ID_TOKEN_CROSS_SITE_IDP_ERROR_RESPONSE = "IdTokenCrossSiteIdpErrorResponse"
    ID_TOKEN_INVALID_REQUEST = "IdTokenInvalidRequest"
    ID_TOKEN_INVALID_CONTENT_TYPE = "IdTokenInvalidContentType"
    ERROR_ID_TOKEN = "ErrorIdToken"
    CANCELED = "Canceled"
    RP_PAGE_NOT_VISIBLE = "RpPageNotVisible"
    SILENT_MEDIATION_FAILURE = "SilentMediationFailure"
    THIRD_PARTY_COOKIES_BLOCKED = "ThirdPartyCookiesBlocked"
    NOT_SIGNED_IN_WITH_IDP = "NotSignedInWithIdp"
    MISSING_TRANSIENT_USER_ACTIVATION = "MissingTransientUserActivation"
    REPLACED_BY_ACTIVE_MODE = "ReplacedByActiveMode"
    INVALID_FIELDS_SPECIFIED = "InvalidFieldsSpecified"
    RELYING_PARTY_ORIGIN_IS_OPAQUE = "RelyingPartyOriginIsOpaque"
    TYPE_NOT_MATCHING = "TypeNotMatching"
    UI_DISMISSED_NO_EMBARGO = "UiDismissedNoEmbargo"
    CORS_ERROR = "CorsError"
    SUPPRESSED_BY_SEGMENTATION_PLATFORM = "SuppressedBySegmentationPlatform"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class FederatedAuthUserInfoRequestIssueDetails:
    federated_auth_user_info_request_issue_reason: FederatedAuthUserInfoRequestIssueReason

    def to_json(self):
        json = dict()
        json['federatedAuthUserInfoRequestIssueReason'] = self.federated_auth_user_info_request_issue_reason.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            federated_auth_user_info_request_issue_reason=FederatedAuthUserInfoRequestIssueReason.from_json(json['federatedAuthUserInfoRequestIssueReason']),
        )


class FederatedAuthUserInfoRequestIssueReason(enum.Enum):
    '''
    Represents the failure reason when a getUserInfo() call fails.
    Should be updated alongside FederatedAuthUserInfoRequestResult in
    third_party/blink/public/mojom/devtools/inspector_issue.mojom.
    '''
    NOT_SAME_ORIGIN = "NotSameOrigin"
    NOT_IFRAME = "NotIframe"
    NOT_POTENTIALLY_TRUSTWORTHY = "NotPotentiallyTrustworthy"
    NO_API_PERMISSION = "NoApiPermission"
    NOT_SIGNED_IN_WITH_IDP = "NotSignedInWithIdp"
    NO_ACCOUNT_SHARING_PERMISSION = "NoAccountSharingPermission"
    INVALID_CONFIG_OR_WELL_KNOWN = "InvalidConfigOrWellKnown"
    INVALID_ACCOUNTS_RESPONSE = "InvalidAccountsResponse"
    NO_RETURNING_USER_FROM_FETCHED_ACCOUNTS = "NoReturningUserFromFetchedAccounts"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ClientHintIssueDetails:
    '''
    This issue tracks client hints related issues. It's used to deprecate old
    features, encourage the use of new ones, and provide general guidance.
    '''
    source_code_location: SourceCodeLocation

    client_hint_issue_reason: ClientHintIssueReason

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['clientHintIssueReason'] = self.client_hint_issue_reason.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            client_hint_issue_reason=ClientHintIssueReason.from_json(json['clientHintIssueReason']),
        )


@dataclass
class FailedRequestInfo:
    #: The URL that failed to load.
    url: str

    #: The failure message for the failed request.
    failure_message: str

    request_id: typing.Optional[network.RequestId] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['failureMessage'] = self.failure_message
        if self.request_id is not None:
            json['requestId'] = self.request_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            failure_message=str(json['failureMessage']),
            request_id=network.RequestId.from_json(json['requestId']) if 'requestId' in json else None,
        )


class PartitioningBlobURLInfo(enum.Enum):
    BLOCKED_CROSS_PARTITION_FETCHING = "BlockedCrossPartitionFetching"
    ENFORCE_NOOPENER_FOR_NAVIGATION = "EnforceNoopenerForNavigation"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PartitioningBlobURLIssueDetails:
    #: The BlobURL that failed to load.
    url: str

    #: Additional information about the Partitioning Blob URL issue.
    partitioning_blob_url_info: PartitioningBlobURLInfo

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['partitioningBlobURLInfo'] = self.partitioning_blob_url_info.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            partitioning_blob_url_info=PartitioningBlobURLInfo.from_json(json['partitioningBlobURLInfo']),
        )


class SelectElementAccessibilityIssueReason(enum.Enum):
    DISALLOWED_SELECT_CHILD = "DisallowedSelectChild"
    DISALLOWED_OPT_GROUP_CHILD = "DisallowedOptGroupChild"
    NON_PHRASING_CONTENT_OPTION_CHILD = "NonPhrasingContentOptionChild"
    INTERACTIVE_CONTENT_OPTION_CHILD = "InteractiveContentOptionChild"
    INTERACTIVE_CONTENT_LEGEND_CHILD = "InteractiveContentLegendChild"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SelectElementAccessibilityIssueDetails:
    '''
    This issue warns about errors in the select element content model.
    '''
    node_id: dom.BackendNodeId

    select_element_accessibility_issue_reason: SelectElementAccessibilityIssueReason

    has_disallowed_attributes: bool

    def to_json(self):
        json = dict()
        json['nodeId'] = self.node_id.to_json()
        json['selectElementAccessibilityIssueReason'] = self.select_element_accessibility_issue_reason.to_json()
        json['hasDisallowedAttributes'] = self.has_disallowed_attributes
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            node_id=dom.BackendNodeId.from_json(json['nodeId']),
            select_element_accessibility_issue_reason=SelectElementAccessibilityIssueReason.from_json(json['selectElementAccessibilityIssueReason']),
            has_disallowed_attributes=bool(json['hasDisallowedAttributes']),
        )


class StyleSheetLoadingIssueReason(enum.Enum):
    LATE_IMPORT_RULE = "LateImportRule"
    REQUEST_FAILED = "RequestFailed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class StylesheetLoadingIssueDetails:
    '''
    This issue warns when a referenced stylesheet couldn't be loaded.
    '''
    #: Source code position that referenced the failing stylesheet.
    source_code_location: SourceCodeLocation

    #: Reason why the stylesheet couldn't be loaded.
    style_sheet_loading_issue_reason: StyleSheetLoadingIssueReason

    #: Contains additional info when the failure was due to a request.
    failed_request_info: typing.Optional[FailedRequestInfo] = None

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['styleSheetLoadingIssueReason'] = self.style_sheet_loading_issue_reason.to_json()
        if self.failed_request_info is not None:
            json['failedRequestInfo'] = self.failed_request_info.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            style_sheet_loading_issue_reason=StyleSheetLoadingIssueReason.from_json(json['styleSheetLoadingIssueReason']),
            failed_request_info=FailedRequestInfo.from_json(json['failedRequestInfo']) if 'failedRequestInfo' in json else None,
        )


class PropertyRuleIssueReason(enum.Enum):
    INVALID_SYNTAX = "InvalidSyntax"
    INVALID_INITIAL_VALUE = "InvalidInitialValue"
    INVALID_INHERITS = "InvalidInherits"
    INVALID_NAME = "InvalidName"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PropertyRuleIssueDetails:
    '''
    This issue warns about errors in property rules that lead to property
    registrations being ignored.
    '''
    #: Source code position of the property rule.
    source_code_location: SourceCodeLocation

    #: Reason why the property rule was discarded.
    property_rule_issue_reason: PropertyRuleIssueReason

    #: The value of the property rule property that failed to parse
    property_value: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['propertyRuleIssueReason'] = self.property_rule_issue_reason.to_json()
        if self.property_value is not None:
            json['propertyValue'] = self.property_value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            property_rule_issue_reason=PropertyRuleIssueReason.from_json(json['propertyRuleIssueReason']),
            property_value=str(json['propertyValue']) if 'propertyValue' in json else None,
        )


class InspectorIssueCode(enum.Enum):
    '''
    A unique identifier for the type of issue. Each type may use one of the
    optional fields in InspectorIssueDetails to convey more specific
    information about the kind of issue.
    '''
    COOKIE_ISSUE = "CookieIssue"
    MIXED_CONTENT_ISSUE = "MixedContentIssue"
    BLOCKED_BY_RESPONSE_ISSUE = "BlockedByResponseIssue"
    HEAVY_AD_ISSUE = "HeavyAdIssue"
    CONTENT_SECURITY_POLICY_ISSUE = "ContentSecurityPolicyIssue"
    SHARED_ARRAY_BUFFER_ISSUE = "SharedArrayBufferIssue"
    LOW_TEXT_CONTRAST_ISSUE = "LowTextContrastIssue"
    CORS_ISSUE = "CorsIssue"
    ATTRIBUTION_REPORTING_ISSUE = "AttributionReportingIssue"
    QUIRKS_MODE_ISSUE = "QuirksModeIssue"
    PARTITIONING_BLOB_URL_ISSUE = "PartitioningBlobURLIssue"
    NAVIGATOR_USER_AGENT_ISSUE = "NavigatorUserAgentIssue"
    GENERIC_ISSUE = "GenericIssue"
    DEPRECATION_ISSUE = "DeprecationIssue"
    CLIENT_HINT_ISSUE = "ClientHintIssue"
    FEDERATED_AUTH_REQUEST_ISSUE = "FederatedAuthRequestIssue"
    BOUNCE_TRACKING_ISSUE = "BounceTrackingIssue"
    COOKIE_DEPRECATION_METADATA_ISSUE = "CookieDeprecationMetadataIssue"
    STYLESHEET_LOADING_ISSUE = "StylesheetLoadingIssue"
    FEDERATED_AUTH_USER_INFO_REQUEST_ISSUE = "FederatedAuthUserInfoRequestIssue"
    PROPERTY_RULE_ISSUE = "PropertyRuleIssue"
    SHARED_DICTIONARY_ISSUE = "SharedDictionaryIssue"
    SELECT_ELEMENT_ACCESSIBILITY_ISSUE = "SelectElementAccessibilityIssue"
    SRI_MESSAGE_SIGNATURE_ISSUE = "SRIMessageSignatureIssue"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class InspectorIssueDetails:
    '''
    This struct holds a list of optional fields with additional information
    specific to the kind of issue. When adding a new issue code, please also
    add a new optional field to this type.
    '''
    cookie_issue_details: typing.Optional[CookieIssueDetails] = None

    mixed_content_issue_details: typing.Optional[MixedContentIssueDetails] = None

    blocked_by_response_issue_details: typing.Optional[BlockedByResponseIssueDetails] = None

    heavy_ad_issue_details: typing.Optional[HeavyAdIssueDetails] = None

    content_security_policy_issue_details: typing.Optional[ContentSecurityPolicyIssueDetails] = None

    shared_array_buffer_issue_details: typing.Optional[SharedArrayBufferIssueDetails] = None

    low_text_contrast_issue_details: typing.Optional[LowTextContrastIssueDetails] = None

    cors_issue_details: typing.Optional[CorsIssueDetails] = None

    attribution_reporting_issue_details: typing.Optional[AttributionReportingIssueDetails] = None

    quirks_mode_issue_details: typing.Optional[QuirksModeIssueDetails] = None

    partitioning_blob_url_issue_details: typing.Optional[PartitioningBlobURLIssueDetails] = None

    navigator_user_agent_issue_details: typing.Optional[NavigatorUserAgentIssueDetails] = None

    generic_issue_details: typing.Optional[GenericIssueDetails] = None

    deprecation_issue_details: typing.Optional[DeprecationIssueDetails] = None

    client_hint_issue_details: typing.Optional[ClientHintIssueDetails] = None

    federated_auth_request_issue_details: typing.Optional[FederatedAuthRequestIssueDetails] = None

    bounce_tracking_issue_details: typing.Optional[BounceTrackingIssueDetails] = None

    cookie_deprecation_metadata_issue_details: typing.Optional[CookieDeprecationMetadataIssueDetails] = None

    stylesheet_loading_issue_details: typing.Optional[StylesheetLoadingIssueDetails] = None

    property_rule_issue_details: typing.Optional[PropertyRuleIssueDetails] = None

    federated_auth_user_info_request_issue_details: typing.Optional[FederatedAuthUserInfoRequestIssueDetails] = None

    shared_dictionary_issue_details: typing.Optional[SharedDictionaryIssueDetails] = None

    select_element_accessibility_issue_details: typing.Optional[SelectElementAccessibilityIssueDetails] = None

    sri_message_signature_issue_details: typing.Optional[SRIMessageSignatureIssueDetails] = None

    def to_json(self):
        json = dict()
        if self.cookie_issue_details is not None:
            json['cookieIssueDetails'] = self.cookie_issue_details.to_json()
        if self.mixed_content_issue_details is not None:
            json['mixedContentIssueDetails'] = self.mixed_content_issue_details.to_json()
        if self.blocked_by_response_issue_details is not None:
            json['blockedByResponseIssueDetails'] = self.blocked_by_response_issue_details.to_json()
        if self.heavy_ad_issue_details is not None:
            json['heavyAdIssueDetails'] = self.heavy_ad_issue_details.to_json()
        if self.content_security_policy_issue_details is not None:
            json['contentSecurityPolicyIssueDetails'] = self.content_security_policy_issue_details.to_json()
        if self.shared_array_buffer_issue_details is not None:
            json['sharedArrayBufferIssueDetails'] = self.shared_array_buffer_issue_details.to_json()
        if self.low_text_contrast_issue_details is not None:
            json['lowTextContrastIssueDetails'] = self.low_text_contrast_issue_details.to_json()
        if self.cors_issue_details is not None:
            json['corsIssueDetails'] = self.cors_issue_details.to_json()
        if self.attribution_reporting_issue_details is not None:
            json['attributionReportingIssueDetails'] = self.attribution_reporting_issue_details.to_json()
        if self.quirks_mode_issue_details is not None:
            json['quirksModeIssueDetails'] = self.quirks_mode_issue_details.to_json()
        if self.partitioning_blob_url_issue_details is not None:
            json['partitioningBlobURLIssueDetails'] = self.partitioning_blob_url_issue_details.to_json()
        if self.navigator_user_agent_issue_details is not None:
            json['navigatorUserAgentIssueDetails'] = self.navigator_user_agent_issue_details.to_json()
        if self.generic_issue_details is not None:
            json['genericIssueDetails'] = self.generic_issue_details.to_json()
        if self.deprecation_issue_details is not None:
            json['deprecationIssueDetails'] = self.deprecation_issue_details.to_json()
        if self.client_hint_issue_details is not None:
            json['clientHintIssueDetails'] = self.client_hint_issue_details.to_json()
        if self.federated_auth_request_issue_details is not None:
            json['federatedAuthRequestIssueDetails'] = self.federated_auth_request_issue_details.to_json()
        if self.bounce_tracking_issue_details is not None:
            json['bounceTrackingIssueDetails'] = self.bounce_tracking_issue_details.to_json()
        if self.cookie_deprecation_metadata_issue_details is not None:
            json['cookieDeprecationMetadataIssueDetails'] = self.cookie_deprecation_metadata_issue_details.to_json()
        if self.stylesheet_loading_issue_details is not None:
            json['stylesheetLoadingIssueDetails'] = self.stylesheet_loading_issue_details.to_json()
        if self.property_rule_issue_details is not None:
            json['propertyRuleIssueDetails'] = self.property_rule_issue_details.to_json()
        if self.federated_auth_user_info_request_issue_details is not None:
            json['federatedAuthUserInfoRequestIssueDetails'] = self.federated_auth_user_info_request_issue_details.to_json()
        if self.shared_dictionary_issue_details is not None:
            json['sharedDictionaryIssueDetails'] = self.shared_dictionary_issue_details.to_json()
        if self.select_element_accessibility_issue_details is not None:
            json['selectElementAccessibilityIssueDetails'] = self.select_element_accessibility_issue_details.to_json()
        if self.sri_message_signature_issue_details is not None:
            json['sriMessageSignatureIssueDetails'] = self.sri_message_signature_issue_details.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cookie_issue_details=CookieIssueDetails.from_json(json['cookieIssueDetails']) if 'cookieIssueDetails' in json else None,
            mixed_content_issue_details=MixedContentIssueDetails.from_json(json['mixedContentIssueDetails']) if 'mixedContentIssueDetails' in json else None,
            blocked_by_response_issue_details=BlockedByResponseIssueDetails.from_json(json['blockedByResponseIssueDetails']) if 'blockedByResponseIssueDetails' in json else None,
            heavy_ad_issue_details=HeavyAdIssueDetails.from_json(json['heavyAdIssueDetails']) if 'heavyAdIssueDetails' in json else None,
            content_security_policy_issue_details=ContentSecurityPolicyIssueDetails.from_json(json['contentSecurityPolicyIssueDetails']) if 'contentSecurityPolicyIssueDetails' in json else None,
            shared_array_buffer_issue_details=SharedArrayBufferIssueDetails.from_json(json['sharedArrayBufferIssueDetails']) if 'sharedArrayBufferIssueDetails' in json else None,
            low_text_contrast_issue_details=LowTextContrastIssueDetails.from_json(json['lowTextContrastIssueDetails']) if 'lowTextContrastIssueDetails' in json else None,
            cors_issue_details=CorsIssueDetails.from_json(json['corsIssueDetails']) if 'corsIssueDetails' in json else None,
            attribution_reporting_issue_details=AttributionReportingIssueDetails.from_json(json['attributionReportingIssueDetails']) if 'attributionReportingIssueDetails' in json else None,
            quirks_mode_issue_details=QuirksModeIssueDetails.from_json(json['quirksModeIssueDetails']) if 'quirksModeIssueDetails' in json else None,
            partitioning_blob_url_issue_details=PartitioningBlobURLIssueDetails.from_json(json['partitioningBlobURLIssueDetails']) if 'partitioningBlobURLIssueDetails' in json else None,
            navigator_user_agent_issue_details=NavigatorUserAgentIssueDetails.from_json(json['navigatorUserAgentIssueDetails']) if 'navigatorUserAgentIssueDetails' in json else None,
            generic_issue_details=GenericIssueDetails.from_json(json['genericIssueDetails']) if 'genericIssueDetails' in json else None,
            deprecation_issue_details=DeprecationIssueDetails.from_json(json['deprecationIssueDetails']) if 'deprecationIssueDetails' in json else None,
            client_hint_issue_details=ClientHintIssueDetails.from_json(json['clientHintIssueDetails']) if 'clientHintIssueDetails' in json else None,
            federated_auth_request_issue_details=FederatedAuthRequestIssueDetails.from_json(json['federatedAuthRequestIssueDetails']) if 'federatedAuthRequestIssueDetails' in json else None,
            bounce_tracking_issue_details=BounceTrackingIssueDetails.from_json(json['bounceTrackingIssueDetails']) if 'bounceTrackingIssueDetails' in json else None,
            cookie_deprecation_metadata_issue_details=CookieDeprecationMetadataIssueDetails.from_json(json['cookieDeprecationMetadataIssueDetails']) if 'cookieDeprecationMetadataIssueDetails' in json else None,
            stylesheet_loading_issue_details=StylesheetLoadingIssueDetails.from_json(json['stylesheetLoadingIssueDetails']) if 'stylesheetLoadingIssueDetails' in json else None,
            property_rule_issue_details=PropertyRuleIssueDetails.from_json(json['propertyRuleIssueDetails']) if 'propertyRuleIssueDetails' in json else None,
            federated_auth_user_info_request_issue_details=FederatedAuthUserInfoRequestIssueDetails.from_json(json['federatedAuthUserInfoRequestIssueDetails']) if 'federatedAuthUserInfoRequestIssueDetails' in json else None,
            shared_dictionary_issue_details=SharedDictionaryIssueDetails.from_json(json['sharedDictionaryIssueDetails']) if 'sharedDictionaryIssueDetails' in json else None,
            select_element_accessibility_issue_details=SelectElementAccessibilityIssueDetails.from_json(json['selectElementAccessibilityIssueDetails']) if 'selectElementAccessibilityIssueDetails' in json else None,
            sri_message_signature_issue_details=SRIMessageSignatureIssueDetails.from_json(json['sriMessageSignatureIssueDetails']) if 'sriMessageSignatureIssueDetails' in json else None,
        )


class IssueId(str):
    '''
    A unique id for a DevTools inspector issue. Allows other entities (e.g.
    exceptions, CDP message, console messages, etc.) to reference an issue.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> IssueId:
        return cls(json)

    def __repr__(self):
        return 'IssueId({})'.format(super().__repr__())


@dataclass
class InspectorIssue:
    '''
    An inspector issue reported from the back-end.
    '''
    code: InspectorIssueCode

    details: InspectorIssueDetails

    #: A unique id for this issue. May be omitted if no other entity (e.g.
    #: exception, CDP message, etc.) is referencing this issue.
    issue_id: typing.Optional[IssueId] = None

    def to_json(self):
        json = dict()
        json['code'] = self.code.to_json()
        json['details'] = self.details.to_json()
        if self.issue_id is not None:
            json['issueId'] = self.issue_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            code=InspectorIssueCode.from_json(json['code']),
            details=InspectorIssueDetails.from_json(json['details']),
            issue_id=IssueId.from_json(json['issueId']) if 'issueId' in json else None,
        )


def get_encoded_response(
        request_id: network.RequestId,
        encoding: str,
        quality: typing.Optional[float] = None,
        size_only: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[str], int, int]]:
    '''
    Returns the response body and size if it were re-encoded with the specified settings. Only
    applies to images.

    :param request_id: Identifier of the network request to get content for.
    :param encoding: The encoding to use.
    :param quality: *(Optional)* The quality of the encoding (0-1). (defaults to 1)
    :param size_only: *(Optional)* Whether to only return the size information (defaults to false).
    :returns: A tuple with the following items:

        0. **body** - *(Optional)* The encoded body as a base64 string. Omitted if sizeOnly is true.
        1. **originalSize** - Size before re-encoding.
        2. **encodedSize** - Size after re-encoding.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['encoding'] = encoding
    if quality is not None:
        params['quality'] = quality
    if size_only is not None:
        params['sizeOnly'] = size_only
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.getEncodedResponse',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['body']) if 'body' in json else None,
        int(json['originalSize']),
        int(json['encodedSize'])
    )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables issues domain, prevents further issues from being reported to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables issues domain, sends the issues collected so far to the client by means of the
    ``issueAdded`` event.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.enable',
    }
    json = yield cmd_dict


def check_contrast(
        report_aaa: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Runs the contrast check for the target page. Found issues are reported
    using Audits.issueAdded event.

    :param report_aaa: *(Optional)* Whether to report WCAG AAA level issues. Default is false.
    '''
    params: T_JSON_DICT = dict()
    if report_aaa is not None:
        params['reportAAA'] = report_aaa
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.checkContrast',
        'params': params,
    }
    json = yield cmd_dict


def check_forms_issues() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[GenericIssueDetails]]:
    '''
    Runs the form issues check for the target page. Found issues are reported
    using Audits.issueAdded event.

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.checkFormsIssues',
    }
    json = yield cmd_dict
    return [GenericIssueDetails.from_json(i) for i in json['formIssues']]


@event_class('Audits.issueAdded')
@dataclass
class IssueAdded:
    issue: InspectorIssue

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> IssueAdded:
        return cls(
            issue=InspectorIssue.from_json(json['issue'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\audits.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Audits (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import network
from . import page
from . import runtime


@dataclass
class AffectedCookie:
    '''
    Information about a cookie that is affected by an inspector issue.
    '''
    #: The following three properties uniquely identify a cookie
    name: str

    path: str

    domain: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['path'] = self.path
        json['domain'] = self.domain
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            path=str(json['path']),
            domain=str(json['domain']),
        )


@dataclass
class AffectedRequest:
    '''
    Information about a request that is affected by an inspector issue.
    '''
    url: str

    #: The unique request id.
    request_id: typing.Optional[network.RequestId] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        if self.request_id is not None:
            json['requestId'] = self.request_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            request_id=network.RequestId.from_json(json['requestId']) if 'requestId' in json else None,
        )


@dataclass
class AffectedFrame:
    '''
    Information about the frame affected by an inspector issue.
    '''
    frame_id: page.FrameId

    def to_json(self):
        json = dict()
        json['frameId'] = self.frame_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            frame_id=page.FrameId.from_json(json['frameId']),
        )


class CookieExclusionReason(enum.Enum):
    EXCLUDE_SAME_SITE_UNSPECIFIED_TREATED_AS_LAX = "ExcludeSameSiteUnspecifiedTreatedAsLax"
    EXCLUDE_SAME_SITE_NONE_INSECURE = "ExcludeSameSiteNoneInsecure"
    EXCLUDE_SAME_SITE_LAX = "ExcludeSameSiteLax"
    EXCLUDE_SAME_SITE_STRICT = "ExcludeSameSiteStrict"
    EXCLUDE_INVALID_SAME_PARTY = "ExcludeInvalidSameParty"
    EXCLUDE_SAME_PARTY_CROSS_PARTY_CONTEXT = "ExcludeSamePartyCrossPartyContext"
    EXCLUDE_DOMAIN_NON_ASCII = "ExcludeDomainNonASCII"
    EXCLUDE_THIRD_PARTY_COOKIE_BLOCKED_IN_FIRST_PARTY_SET = "ExcludeThirdPartyCookieBlockedInFirstPartySet"
    EXCLUDE_THIRD_PARTY_PHASEOUT = "ExcludeThirdPartyPhaseout"
    EXCLUDE_PORT_MISMATCH = "ExcludePortMismatch"
    EXCLUDE_SCHEME_MISMATCH = "ExcludeSchemeMismatch"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieWarningReason(enum.Enum):
    WARN_SAME_SITE_UNSPECIFIED_CROSS_SITE_CONTEXT = "WarnSameSiteUnspecifiedCrossSiteContext"
    WARN_SAME_SITE_NONE_INSECURE = "WarnSameSiteNoneInsecure"
    WARN_SAME_SITE_UNSPECIFIED_LAX_ALLOW_UNSAFE = "WarnSameSiteUnspecifiedLaxAllowUnsafe"
    WARN_SAME_SITE_STRICT_LAX_DOWNGRADE_STRICT = "WarnSameSiteStrictLaxDowngradeStrict"
    WARN_SAME_SITE_STRICT_CROSS_DOWNGRADE_STRICT = "WarnSameSiteStrictCrossDowngradeStrict"
    WARN_SAME_SITE_STRICT_CROSS_DOWNGRADE_LAX = "WarnSameSiteStrictCrossDowngradeLax"
    WARN_SAME_SITE_LAX_CROSS_DOWNGRADE_STRICT = "WarnSameSiteLaxCrossDowngradeStrict"
    WARN_SAME_SITE_LAX_CROSS_DOWNGRADE_LAX = "WarnSameSiteLaxCrossDowngradeLax"
    WARN_ATTRIBUTE_VALUE_EXCEEDS_MAX_SIZE = "WarnAttributeValueExceedsMaxSize"
    WARN_DOMAIN_NON_ASCII = "WarnDomainNonASCII"
    WARN_THIRD_PARTY_PHASEOUT = "WarnThirdPartyPhaseout"
    WARN_CROSS_SITE_REDIRECT_DOWNGRADE_CHANGES_INCLUSION = "WarnCrossSiteRedirectDowngradeChangesInclusion"
    WARN_DEPRECATION_TRIAL_METADATA = "WarnDeprecationTrialMetadata"
    WARN_THIRD_PARTY_COOKIE_HEURISTIC = "WarnThirdPartyCookieHeuristic"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieOperation(enum.Enum):
    SET_COOKIE = "SetCookie"
    READ_COOKIE = "ReadCookie"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class InsightType(enum.Enum):
    '''
    Represents the category of insight that a cookie issue falls under.
    '''
    GIT_HUB_RESOURCE = "GitHubResource"
    GRACE_PERIOD = "GracePeriod"
    HEURISTICS = "Heuristics"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class CookieIssueInsight:
    '''
    Information about the suggested solution to a cookie issue.
    '''
    type_: InsightType

    #: Link to table entry in third-party cookie migration readiness list.
    table_entry_url: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_.to_json()
        if self.table_entry_url is not None:
            json['tableEntryUrl'] = self.table_entry_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=InsightType.from_json(json['type']),
            table_entry_url=str(json['tableEntryUrl']) if 'tableEntryUrl' in json else None,
        )


@dataclass
class CookieIssueDetails:
    '''
    This information is currently necessary, as the front-end has a difficult
    time finding a specific cookie. With this, we can convey specific error
    information without the cookie.
    '''
    cookie_warning_reasons: typing.List[CookieWarningReason]

    cookie_exclusion_reasons: typing.List[CookieExclusionReason]

    #: Optionally identifies the site-for-cookies and the cookie url, which
    #: may be used by the front-end as additional context.
    operation: CookieOperation

    #: If AffectedCookie is not set then rawCookieLine contains the raw
    #: Set-Cookie header string. This hints at a problem where the
    #: cookie line is syntactically or semantically malformed in a way
    #: that no valid cookie could be created.
    cookie: typing.Optional[AffectedCookie] = None

    raw_cookie_line: typing.Optional[str] = None

    site_for_cookies: typing.Optional[str] = None

    cookie_url: typing.Optional[str] = None

    request: typing.Optional[AffectedRequest] = None

    #: The recommended solution to the issue.
    insight: typing.Optional[CookieIssueInsight] = None

    def to_json(self):
        json = dict()
        json['cookieWarningReasons'] = [i.to_json() for i in self.cookie_warning_reasons]
        json['cookieExclusionReasons'] = [i.to_json() for i in self.cookie_exclusion_reasons]
        json['operation'] = self.operation.to_json()
        if self.cookie is not None:
            json['cookie'] = self.cookie.to_json()
        if self.raw_cookie_line is not None:
            json['rawCookieLine'] = self.raw_cookie_line
        if self.site_for_cookies is not None:
            json['siteForCookies'] = self.site_for_cookies
        if self.cookie_url is not None:
            json['cookieUrl'] = self.cookie_url
        if self.request is not None:
            json['request'] = self.request.to_json()
        if self.insight is not None:
            json['insight'] = self.insight.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cookie_warning_reasons=[CookieWarningReason.from_json(i) for i in json['cookieWarningReasons']],
            cookie_exclusion_reasons=[CookieExclusionReason.from_json(i) for i in json['cookieExclusionReasons']],
            operation=CookieOperation.from_json(json['operation']),
            cookie=AffectedCookie.from_json(json['cookie']) if 'cookie' in json else None,
            raw_cookie_line=str(json['rawCookieLine']) if 'rawCookieLine' in json else None,
            site_for_cookies=str(json['siteForCookies']) if 'siteForCookies' in json else None,
            cookie_url=str(json['cookieUrl']) if 'cookieUrl' in json else None,
            request=AffectedRequest.from_json(json['request']) if 'request' in json else None,
            insight=CookieIssueInsight.from_json(json['insight']) if 'insight' in json else None,
        )


class MixedContentResolutionStatus(enum.Enum):
    MIXED_CONTENT_BLOCKED = "MixedContentBlocked"
    MIXED_CONTENT_AUTOMATICALLY_UPGRADED = "MixedContentAutomaticallyUpgraded"
    MIXED_CONTENT_WARNING = "MixedContentWarning"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class MixedContentResourceType(enum.Enum):
    ATTRIBUTION_SRC = "AttributionSrc"
    AUDIO = "Audio"
    BEACON = "Beacon"
    CSP_REPORT = "CSPReport"
    DOWNLOAD = "Download"
    EVENT_SOURCE = "EventSource"
    FAVICON = "Favicon"
    FONT = "Font"
    FORM = "Form"
    FRAME = "Frame"
    IMAGE = "Image"
    IMPORT = "Import"
    JSON = "JSON"
    MANIFEST = "Manifest"
    PING = "Ping"
    PLUGIN_DATA = "PluginData"
    PLUGIN_RESOURCE = "PluginResource"
    PREFETCH = "Prefetch"
    RESOURCE = "Resource"
    SCRIPT = "Script"
    SERVICE_WORKER = "ServiceWorker"
    SHARED_WORKER = "SharedWorker"
    SPECULATION_RULES = "SpeculationRules"
    STYLESHEET = "Stylesheet"
    TRACK = "Track"
    VIDEO = "Video"
    WORKER = "Worker"
    XML_HTTP_REQUEST = "XMLHttpRequest"
    XSLT = "XSLT"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class MixedContentIssueDetails:
    #: The way the mixed content issue is being resolved.
    resolution_status: MixedContentResolutionStatus

    #: The unsafe http url causing the mixed content issue.
    insecure_url: str

    #: The url responsible for the call to an unsafe url.
    main_resource_url: str

    #: The type of resource causing the mixed content issue (css, js, iframe,
    #: form,...). Marked as optional because it is mapped to from
    #: blink::mojom::RequestContextType, which will be replaced
    #: by network::mojom::RequestDestination
    resource_type: typing.Optional[MixedContentResourceType] = None

    #: The mixed content request.
    #: Does not always exist (e.g. for unsafe form submission urls).
    request: typing.Optional[AffectedRequest] = None

    #: Optional because not every mixed content issue is necessarily linked to a frame.
    frame: typing.Optional[AffectedFrame] = None

    def to_json(self):
        json = dict()
        json['resolutionStatus'] = self.resolution_status.to_json()
        json['insecureURL'] = self.insecure_url
        json['mainResourceURL'] = self.main_resource_url
        if self.resource_type is not None:
            json['resourceType'] = self.resource_type.to_json()
        if self.request is not None:
            json['request'] = self.request.to_json()
        if self.frame is not None:
            json['frame'] = self.frame.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            resolution_status=MixedContentResolutionStatus.from_json(json['resolutionStatus']),
            insecure_url=str(json['insecureURL']),
            main_resource_url=str(json['mainResourceURL']),
            resource_type=MixedContentResourceType.from_json(json['resourceType']) if 'resourceType' in json else None,
            request=AffectedRequest.from_json(json['request']) if 'request' in json else None,
            frame=AffectedFrame.from_json(json['frame']) if 'frame' in json else None,
        )


class BlockedByResponseReason(enum.Enum):
    '''
    Enum indicating the reason a response has been blocked. These reasons are
    refinements of the net error BLOCKED_BY_RESPONSE.
    '''
    COEP_FRAME_RESOURCE_NEEDS_COEP_HEADER = "CoepFrameResourceNeedsCoepHeader"
    COOP_SANDBOXED_I_FRAME_CANNOT_NAVIGATE_TO_COOP_PAGE = "CoopSandboxedIFrameCannotNavigateToCoopPage"
    CORP_NOT_SAME_ORIGIN = "CorpNotSameOrigin"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_COEP = "CorpNotSameOriginAfterDefaultedToSameOriginByCoep"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_DIP = "CorpNotSameOriginAfterDefaultedToSameOriginByDip"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_COEP_AND_DIP = "CorpNotSameOriginAfterDefaultedToSameOriginByCoepAndDip"
    CORP_NOT_SAME_SITE = "CorpNotSameSite"
    SRI_MESSAGE_SIGNATURE_MISMATCH = "SRIMessageSignatureMismatch"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class BlockedByResponseIssueDetails:
    '''
    Details for a request that has been blocked with the BLOCKED_BY_RESPONSE
    code. Currently only used for COEP/COOP, but may be extended to include
    some CSP errors in the future.
    '''
    request: AffectedRequest

    reason: BlockedByResponseReason

    parent_frame: typing.Optional[AffectedFrame] = None

    blocked_frame: typing.Optional[AffectedFrame] = None

    def to_json(self):
        json = dict()
        json['request'] = self.request.to_json()
        json['reason'] = self.reason.to_json()
        if self.parent_frame is not None:
            json['parentFrame'] = self.parent_frame.to_json()
        if self.blocked_frame is not None:
            json['blockedFrame'] = self.blocked_frame.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            request=AffectedRequest.from_json(json['request']),
            reason=BlockedByResponseReason.from_json(json['reason']),
            parent_frame=AffectedFrame.from_json(json['parentFrame']) if 'parentFrame' in json else None,
            blocked_frame=AffectedFrame.from_json(json['blockedFrame']) if 'blockedFrame' in json else None,
        )


class HeavyAdResolutionStatus(enum.Enum):
    HEAVY_AD_BLOCKED = "HeavyAdBlocked"
    HEAVY_AD_WARNING = "HeavyAdWarning"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class HeavyAdReason(enum.Enum):
    NETWORK_TOTAL_LIMIT = "NetworkTotalLimit"
    CPU_TOTAL_LIMIT = "CpuTotalLimit"
    CPU_PEAK_LIMIT = "CpuPeakLimit"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class HeavyAdIssueDetails:
    #: The resolution status, either blocking the content or warning.
    resolution: HeavyAdResolutionStatus

    #: The reason the ad was blocked, total network or cpu or peak cpu.
    reason: HeavyAdReason

    #: The frame that was blocked.
    frame: AffectedFrame

    def to_json(self):
        json = dict()
        json['resolution'] = self.resolution.to_json()
        json['reason'] = self.reason.to_json()
        json['frame'] = self.frame.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            resolution=HeavyAdResolutionStatus.from_json(json['resolution']),
            reason=HeavyAdReason.from_json(json['reason']),
            frame=AffectedFrame.from_json(json['frame']),
        )


class ContentSecurityPolicyViolationType(enum.Enum):
    K_INLINE_VIOLATION = "kInlineViolation"
    K_EVAL_VIOLATION = "kEvalViolation"
    K_URL_VIOLATION = "kURLViolation"
    K_SRI_VIOLATION = "kSRIViolation"
    K_TRUSTED_TYPES_SINK_VIOLATION = "kTrustedTypesSinkViolation"
    K_TRUSTED_TYPES_POLICY_VIOLATION = "kTrustedTypesPolicyViolation"
    K_WASM_EVAL_VIOLATION = "kWasmEvalViolation"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SourceCodeLocation:
    url: str

    line_number: int

    column_number: int

    script_id: typing.Optional[runtime.ScriptId] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        if self.script_id is not None:
            json['scriptId'] = self.script_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
            script_id=runtime.ScriptId.from_json(json['scriptId']) if 'scriptId' in json else None,
        )


@dataclass
class ContentSecurityPolicyIssueDetails:
    #: Specific directive that is violated, causing the CSP issue.
    violated_directive: str

    is_report_only: bool

    content_security_policy_violation_type: ContentSecurityPolicyViolationType

    #: The url not included in allowed sources.
    blocked_url: typing.Optional[str] = None

    frame_ancestor: typing.Optional[AffectedFrame] = None

    source_code_location: typing.Optional[SourceCodeLocation] = None

    violating_node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['violatedDirective'] = self.violated_directive
        json['isReportOnly'] = self.is_report_only
        json['contentSecurityPolicyViolationType'] = self.content_security_policy_violation_type.to_json()
        if self.blocked_url is not None:
            json['blockedURL'] = self.blocked_url
        if self.frame_ancestor is not None:
            json['frameAncestor'] = self.frame_ancestor.to_json()
        if self.source_code_location is not None:
            json['sourceCodeLocation'] = self.source_code_location.to_json()
        if self.violating_node_id is not None:
            json['violatingNodeId'] = self.violating_node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            violated_directive=str(json['violatedDirective']),
            is_report_only=bool(json['isReportOnly']),
            content_security_policy_violation_type=ContentSecurityPolicyViolationType.from_json(json['contentSecurityPolicyViolationType']),
            blocked_url=str(json['blockedURL']) if 'blockedURL' in json else None,
            frame_ancestor=AffectedFrame.from_json(json['frameAncestor']) if 'frameAncestor' in json else None,
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']) if 'sourceCodeLocation' in json else None,
            violating_node_id=dom.BackendNodeId.from_json(json['violatingNodeId']) if 'violatingNodeId' in json else None,
        )


class SharedArrayBufferIssueType(enum.Enum):
    TRANSFER_ISSUE = "TransferIssue"
    CREATION_ISSUE = "CreationIssue"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SharedArrayBufferIssueDetails:
    '''
    Details for a issue arising from an SAB being instantiated in, or
    transferred to a context that is not cross-origin isolated.
    '''
    source_code_location: SourceCodeLocation

    is_warning: bool

    type_: SharedArrayBufferIssueType

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['isWarning'] = self.is_warning
        json['type'] = self.type_.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            is_warning=bool(json['isWarning']),
            type_=SharedArrayBufferIssueType.from_json(json['type']),
        )


@dataclass
class LowTextContrastIssueDetails:
    violating_node_id: dom.BackendNodeId

    violating_node_selector: str

    contrast_ratio: float

    threshold_aa: float

    threshold_aaa: float

    font_size: str

    font_weight: str

    def to_json(self):
        json = dict()
        json['violatingNodeId'] = self.violating_node_id.to_json()
        json['violatingNodeSelector'] = self.violating_node_selector
        json['contrastRatio'] = self.contrast_ratio
        json['thresholdAA'] = self.threshold_aa
        json['thresholdAAA'] = self.threshold_aaa
        json['fontSize'] = self.font_size
        json['fontWeight'] = self.font_weight
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            violating_node_id=dom.BackendNodeId.from_json(json['violatingNodeId']),
            violating_node_selector=str(json['violatingNodeSelector']),
            contrast_ratio=float(json['contrastRatio']),
            threshold_aa=float(json['thresholdAA']),
            threshold_aaa=float(json['thresholdAAA']),
            font_size=str(json['fontSize']),
            font_weight=str(json['fontWeight']),
        )


@dataclass
class CorsIssueDetails:
    '''
    Details for a CORS related issue, e.g. a warning or error related to
    CORS RFC1918 enforcement.
    '''
    cors_error_status: network.CorsErrorStatus

    is_warning: bool

    request: AffectedRequest

    location: typing.Optional[SourceCodeLocation] = None

    initiator_origin: typing.Optional[str] = None

    resource_ip_address_space: typing.Optional[network.IPAddressSpace] = None

    client_security_state: typing.Optional[network.ClientSecurityState] = None

    def to_json(self):
        json = dict()
        json['corsErrorStatus'] = self.cors_error_status.to_json()
        json['isWarning'] = self.is_warning
        json['request'] = self.request.to_json()
        if self.location is not None:
            json['location'] = self.location.to_json()
        if self.initiator_origin is not None:
            json['initiatorOrigin'] = self.initiator_origin
        if self.resource_ip_address_space is not None:
            json['resourceIPAddressSpace'] = self.resource_ip_address_space.to_json()
        if self.client_security_state is not None:
            json['clientSecurityState'] = self.client_security_state.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cors_error_status=network.CorsErrorStatus.from_json(json['corsErrorStatus']),
            is_warning=bool(json['isWarning']),
            request=AffectedRequest.from_json(json['request']),
            location=SourceCodeLocation.from_json(json['location']) if 'location' in json else None,
            initiator_origin=str(json['initiatorOrigin']) if 'initiatorOrigin' in json else None,
            resource_ip_address_space=network.IPAddressSpace.from_json(json['resourceIPAddressSpace']) if 'resourceIPAddressSpace' in json else None,
            client_security_state=network.ClientSecurityState.from_json(json['clientSecurityState']) if 'clientSecurityState' in json else None,
        )


class AttributionReportingIssueType(enum.Enum):
    PERMISSION_POLICY_DISABLED = "PermissionPolicyDisabled"
    UNTRUSTWORTHY_REPORTING_ORIGIN = "UntrustworthyReportingOrigin"
    INSECURE_CONTEXT = "InsecureContext"
    INVALID_HEADER = "InvalidHeader"
    INVALID_REGISTER_TRIGGER_HEADER = "InvalidRegisterTriggerHeader"
    SOURCE_AND_TRIGGER_HEADERS = "SourceAndTriggerHeaders"
    SOURCE_IGNORED = "SourceIgnored"
    TRIGGER_IGNORED = "TriggerIgnored"
    OS_SOURCE_IGNORED = "OsSourceIgnored"
    OS_TRIGGER_IGNORED = "OsTriggerIgnored"
    INVALID_REGISTER_OS_SOURCE_HEADER = "InvalidRegisterOsSourceHeader"
    INVALID_REGISTER_OS_TRIGGER_HEADER = "InvalidRegisterOsTriggerHeader"
    WEB_AND_OS_HEADERS = "WebAndOsHeaders"
    NO_WEB_OR_OS_SUPPORT = "NoWebOrOsSupport"
    NAVIGATION_REGISTRATION_WITHOUT_TRANSIENT_USER_ACTIVATION = "NavigationRegistrationWithoutTransientUserActivation"
    INVALID_INFO_HEADER = "InvalidInfoHeader"
    NO_REGISTER_SOURCE_HEADER = "NoRegisterSourceHeader"
    NO_REGISTER_TRIGGER_HEADER = "NoRegisterTriggerHeader"
    NO_REGISTER_OS_SOURCE_HEADER = "NoRegisterOsSourceHeader"
    NO_REGISTER_OS_TRIGGER_HEADER = "NoRegisterOsTriggerHeader"
    NAVIGATION_REGISTRATION_UNIQUE_SCOPE_ALREADY_SET = "NavigationRegistrationUniqueScopeAlreadySet"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SharedDictionaryError(enum.Enum):
    USE_ERROR_CROSS_ORIGIN_NO_CORS_REQUEST = "UseErrorCrossOriginNoCorsRequest"
    USE_ERROR_DICTIONARY_LOAD_FAILURE = "UseErrorDictionaryLoadFailure"
    USE_ERROR_MATCHING_DICTIONARY_NOT_USED = "UseErrorMatchingDictionaryNotUsed"
    USE_ERROR_UNEXPECTED_CONTENT_DICTIONARY_HEADER = "UseErrorUnexpectedContentDictionaryHeader"
    WRITE_ERROR_COSS_ORIGIN_NO_CORS_REQUEST = "WriteErrorCossOriginNoCorsRequest"
    WRITE_ERROR_DISALLOWED_BY_SETTINGS = "WriteErrorDisallowedBySettings"
    WRITE_ERROR_EXPIRED_RESPONSE = "WriteErrorExpiredResponse"
    WRITE_ERROR_FEATURE_DISABLED = "WriteErrorFeatureDisabled"
    WRITE_ERROR_INSUFFICIENT_RESOURCES = "WriteErrorInsufficientResources"
    WRITE_ERROR_INVALID_MATCH_FIELD = "WriteErrorInvalidMatchField"
    WRITE_ERROR_INVALID_STRUCTURED_HEADER = "WriteErrorInvalidStructuredHeader"
    WRITE_ERROR_NAVIGATION_REQUEST = "WriteErrorNavigationRequest"
    WRITE_ERROR_NO_MATCH_FIELD = "WriteErrorNoMatchField"
    WRITE_ERROR_NON_LIST_MATCH_DEST_FIELD = "WriteErrorNonListMatchDestField"
    WRITE_ERROR_NON_SECURE_CONTEXT = "WriteErrorNonSecureContext"
    WRITE_ERROR_NON_STRING_ID_FIELD = "WriteErrorNonStringIdField"
    WRITE_ERROR_NON_STRING_IN_MATCH_DEST_LIST = "WriteErrorNonStringInMatchDestList"
    WRITE_ERROR_NON_STRING_MATCH_FIELD = "WriteErrorNonStringMatchField"
    WRITE_ERROR_NON_TOKEN_TYPE_FIELD = "WriteErrorNonTokenTypeField"
    WRITE_ERROR_REQUEST_ABORTED = "WriteErrorRequestAborted"
    WRITE_ERROR_SHUTTING_DOWN = "WriteErrorShuttingDown"
    WRITE_ERROR_TOO_LONG_ID_FIELD = "WriteErrorTooLongIdField"
    WRITE_ERROR_UNSUPPORTED_TYPE = "WriteErrorUnsupportedType"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SRIMessageSignatureError(enum.Enum):
    MISSING_SIGNATURE_HEADER = "MissingSignatureHeader"
    MISSING_SIGNATURE_INPUT_HEADER = "MissingSignatureInputHeader"
    INVALID_SIGNATURE_HEADER = "InvalidSignatureHeader"
    INVALID_SIGNATURE_INPUT_HEADER = "InvalidSignatureInputHeader"
    SIGNATURE_HEADER_VALUE_IS_NOT_BYTE_SEQUENCE = "SignatureHeaderValueIsNotByteSequence"
    SIGNATURE_HEADER_VALUE_IS_PARAMETERIZED = "SignatureHeaderValueIsParameterized"
    SIGNATURE_HEADER_VALUE_IS_INCORRECT_LENGTH = "SignatureHeaderValueIsIncorrectLength"
    SIGNATURE_INPUT_HEADER_MISSING_LABEL = "SignatureInputHeaderMissingLabel"
    SIGNATURE_INPUT_HEADER_VALUE_NOT_INNER_LIST = "SignatureInputHeaderValueNotInnerList"
    SIGNATURE_INPUT_HEADER_VALUE_MISSING_COMPONENTS = "SignatureInputHeaderValueMissingComponents"
    SIGNATURE_INPUT_HEADER_INVALID_COMPONENT_TYPE = "SignatureInputHeaderInvalidComponentType"
    SIGNATURE_INPUT_HEADER_INVALID_COMPONENT_NAME = "SignatureInputHeaderInvalidComponentName"
    SIGNATURE_INPUT_HEADER_INVALID_HEADER_COMPONENT_PARAMETER = "SignatureInputHeaderInvalidHeaderComponentParameter"
    SIGNATURE_INPUT_HEADER_INVALID_DERIVED_COMPONENT_PARAMETER = "SignatureInputHeaderInvalidDerivedComponentParameter"
    SIGNATURE_INPUT_HEADER_KEY_ID_LENGTH = "SignatureInputHeaderKeyIdLength"
    SIGNATURE_INPUT_HEADER_INVALID_PARAMETER = "SignatureInputHeaderInvalidParameter"
    SIGNATURE_INPUT_HEADER_MISSING_REQUIRED_PARAMETERS = "SignatureInputHeaderMissingRequiredParameters"
    VALIDATION_FAILED_SIGNATURE_EXPIRED = "ValidationFailedSignatureExpired"
    VALIDATION_FAILED_INVALID_LENGTH = "ValidationFailedInvalidLength"
    VALIDATION_FAILED_SIGNATURE_MISMATCH = "ValidationFailedSignatureMismatch"
    VALIDATION_FAILED_INTEGRITY_MISMATCH = "ValidationFailedIntegrityMismatch"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AttributionReportingIssueDetails:
    '''
    Details for issues around "Attribution Reporting API" usage.
    Explainer: https://github.com/WICG/attribution-reporting-api
    '''
    violation_type: AttributionReportingIssueType

    request: typing.Optional[AffectedRequest] = None

    violating_node_id: typing.Optional[dom.BackendNodeId] = None

    invalid_parameter: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['violationType'] = self.violation_type.to_json()
        if self.request is not None:
            json['request'] = self.request.to_json()
        if self.violating_node_id is not None:
            json['violatingNodeId'] = self.violating_node_id.to_json()
        if self.invalid_parameter is not None:
            json['invalidParameter'] = self.invalid_parameter
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            violation_type=AttributionReportingIssueType.from_json(json['violationType']),
            request=AffectedRequest.from_json(json['request']) if 'request' in json else None,
            violating_node_id=dom.BackendNodeId.from_json(json['violatingNodeId']) if 'violatingNodeId' in json else None,
            invalid_parameter=str(json['invalidParameter']) if 'invalidParameter' in json else None,
        )


@dataclass
class QuirksModeIssueDetails:
    '''
    Details for issues about documents in Quirks Mode
    or Limited Quirks Mode that affects page layouting.
    '''
    #: If false, it means the document's mode is "quirks"
    #: instead of "limited-quirks".
    is_limited_quirks_mode: bool

    document_node_id: dom.BackendNodeId

    url: str

    frame_id: page.FrameId

    loader_id: network.LoaderId

    def to_json(self):
        json = dict()
        json['isLimitedQuirksMode'] = self.is_limited_quirks_mode
        json['documentNodeId'] = self.document_node_id.to_json()
        json['url'] = self.url
        json['frameId'] = self.frame_id.to_json()
        json['loaderId'] = self.loader_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            is_limited_quirks_mode=bool(json['isLimitedQuirksMode']),
            document_node_id=dom.BackendNodeId.from_json(json['documentNodeId']),
            url=str(json['url']),
            frame_id=page.FrameId.from_json(json['frameId']),
            loader_id=network.LoaderId.from_json(json['loaderId']),
        )


@dataclass
class NavigatorUserAgentIssueDetails:
    url: str

    location: typing.Optional[SourceCodeLocation] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        if self.location is not None:
            json['location'] = self.location.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            location=SourceCodeLocation.from_json(json['location']) if 'location' in json else None,
        )


@dataclass
class SharedDictionaryIssueDetails:
    shared_dictionary_error: SharedDictionaryError

    request: AffectedRequest

    def to_json(self):
        json = dict()
        json['sharedDictionaryError'] = self.shared_dictionary_error.to_json()
        json['request'] = self.request.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            shared_dictionary_error=SharedDictionaryError.from_json(json['sharedDictionaryError']),
            request=AffectedRequest.from_json(json['request']),
        )


@dataclass
class SRIMessageSignatureIssueDetails:
    error: SRIMessageSignatureError

    signature_base: str

    integrity_assertions: typing.List[str]

    request: AffectedRequest

    def to_json(self):
        json = dict()
        json['error'] = self.error.to_json()
        json['signatureBase'] = self.signature_base
        json['integrityAssertions'] = [i for i in self.integrity_assertions]
        json['request'] = self.request.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            error=SRIMessageSignatureError.from_json(json['error']),
            signature_base=str(json['signatureBase']),
            integrity_assertions=[str(i) for i in json['integrityAssertions']],
            request=AffectedRequest.from_json(json['request']),
        )


class GenericIssueErrorType(enum.Enum):
    FORM_LABEL_FOR_NAME_ERROR = "FormLabelForNameError"
    FORM_DUPLICATE_ID_FOR_INPUT_ERROR = "FormDuplicateIdForInputError"
    FORM_INPUT_WITH_NO_LABEL_ERROR = "FormInputWithNoLabelError"
    FORM_AUTOCOMPLETE_ATTRIBUTE_EMPTY_ERROR = "FormAutocompleteAttributeEmptyError"
    FORM_EMPTY_ID_AND_NAME_ATTRIBUTES_FOR_INPUT_ERROR = "FormEmptyIdAndNameAttributesForInputError"
    FORM_ARIA_LABELLED_BY_TO_NON_EXISTING_ID = "FormAriaLabelledByToNonExistingId"
    FORM_INPUT_ASSIGNED_AUTOCOMPLETE_VALUE_TO_ID_OR_NAME_ATTRIBUTE_ERROR = "FormInputAssignedAutocompleteValueToIdOrNameAttributeError"
    FORM_LABEL_HAS_NEITHER_FOR_NOR_NESTED_INPUT = "FormLabelHasNeitherForNorNestedInput"
    FORM_LABEL_FOR_MATCHES_NON_EXISTING_ID_ERROR = "FormLabelForMatchesNonExistingIdError"
    FORM_INPUT_HAS_WRONG_BUT_WELL_INTENDED_AUTOCOMPLETE_VALUE_ERROR = "FormInputHasWrongButWellIntendedAutocompleteValueError"
    RESPONSE_WAS_BLOCKED_BY_ORB = "ResponseWasBlockedByORB"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class GenericIssueDetails:
    '''
    Depending on the concrete errorType, different properties are set.
    '''
    #: Issues with the same errorType are aggregated in the frontend.
    error_type: GenericIssueErrorType

    frame_id: typing.Optional[page.FrameId] = None

    violating_node_id: typing.Optional[dom.BackendNodeId] = None

    violating_node_attribute: typing.Optional[str] = None

    request: typing.Optional[AffectedRequest] = None

    def to_json(self):
        json = dict()
        json['errorType'] = self.error_type.to_json()
        if self.frame_id is not None:
            json['frameId'] = self.frame_id.to_json()
        if self.violating_node_id is not None:
            json['violatingNodeId'] = self.violating_node_id.to_json()
        if self.violating_node_attribute is not None:
            json['violatingNodeAttribute'] = self.violating_node_attribute
        if self.request is not None:
            json['request'] = self.request.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            error_type=GenericIssueErrorType.from_json(json['errorType']),
            frame_id=page.FrameId.from_json(json['frameId']) if 'frameId' in json else None,
            violating_node_id=dom.BackendNodeId.from_json(json['violatingNodeId']) if 'violatingNodeId' in json else None,
            violating_node_attribute=str(json['violatingNodeAttribute']) if 'violatingNodeAttribute' in json else None,
            request=AffectedRequest.from_json(json['request']) if 'request' in json else None,
        )


@dataclass
class DeprecationIssueDetails:
    '''
    This issue tracks information needed to print a deprecation message.
    https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/renderer/core/frame/third_party/blink/renderer/core/frame/deprecation/README.md
    '''
    source_code_location: SourceCodeLocation

    #: One of the deprecation names from third_party/blink/renderer/core/frame/deprecation/deprecation.json5
    type_: str

    affected_frame: typing.Optional[AffectedFrame] = None

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['type'] = self.type_
        if self.affected_frame is not None:
            json['affectedFrame'] = self.affected_frame.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            type_=str(json['type']),
            affected_frame=AffectedFrame.from_json(json['affectedFrame']) if 'affectedFrame' in json else None,
        )


@dataclass
class BounceTrackingIssueDetails:
    '''
    This issue warns about sites in the redirect chain of a finished navigation
    that may be flagged as trackers and have their state cleared if they don't
    receive a user interaction. Note that in this context 'site' means eTLD+1.
    For example, if the URL ``https://example.test:80/bounce`` was in the
    redirect chain, the site reported would be ``example.test``.
    '''
    tracking_sites: typing.List[str]

    def to_json(self):
        json = dict()
        json['trackingSites'] = [i for i in self.tracking_sites]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            tracking_sites=[str(i) for i in json['trackingSites']],
        )


@dataclass
class CookieDeprecationMetadataIssueDetails:
    '''
    This issue warns about third-party sites that are accessing cookies on the
    current page, and have been permitted due to having a global metadata grant.
    Note that in this context 'site' means eTLD+1. For example, if the URL
    ``https://example.test:80/web_page`` was accessing cookies, the site reported
    would be ``example.test``.
    '''
    allowed_sites: typing.List[str]

    opt_out_percentage: float

    is_opt_out_top_level: bool

    operation: CookieOperation

    def to_json(self):
        json = dict()
        json['allowedSites'] = [i for i in self.allowed_sites]
        json['optOutPercentage'] = self.opt_out_percentage
        json['isOptOutTopLevel'] = self.is_opt_out_top_level
        json['operation'] = self.operation.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            allowed_sites=[str(i) for i in json['allowedSites']],
            opt_out_percentage=float(json['optOutPercentage']),
            is_opt_out_top_level=bool(json['isOptOutTopLevel']),
            operation=CookieOperation.from_json(json['operation']),
        )


class ClientHintIssueReason(enum.Enum):
    META_TAG_ALLOW_LIST_INVALID_ORIGIN = "MetaTagAllowListInvalidOrigin"
    META_TAG_MODIFIED_HTML = "MetaTagModifiedHTML"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class FederatedAuthRequestIssueDetails:
    federated_auth_request_issue_reason: FederatedAuthRequestIssueReason

    def to_json(self):
        json = dict()
        json['federatedAuthRequestIssueReason'] = self.federated_auth_request_issue_reason.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            federated_auth_request_issue_reason=FederatedAuthRequestIssueReason.from_json(json['federatedAuthRequestIssueReason']),
        )


class FederatedAuthRequestIssueReason(enum.Enum):
    '''
    Represents the failure reason when a federated authentication reason fails.
    Should be updated alongside RequestIdTokenStatus in
    third_party/blink/public/mojom/devtools/inspector_issue.mojom to include
    all cases except for success.
    '''
    SHOULD_EMBARGO = "ShouldEmbargo"
    TOO_MANY_REQUESTS = "TooManyRequests"
    WELL_KNOWN_HTTP_NOT_FOUND = "WellKnownHttpNotFound"
    WELL_KNOWN_NO_RESPONSE = "WellKnownNoResponse"
    WELL_KNOWN_INVALID_RESPONSE = "WellKnownInvalidResponse"
    WELL_KNOWN_LIST_EMPTY = "WellKnownListEmpty"
    WELL_KNOWN_INVALID_CONTENT_TYPE = "WellKnownInvalidContentType"
    CONFIG_NOT_IN_WELL_KNOWN = "ConfigNotInWellKnown"
    WELL_KNOWN_TOO_BIG = "WellKnownTooBig"
    CONFIG_HTTP_NOT_FOUND = "ConfigHttpNotFound"
    CONFIG_NO_RESPONSE = "ConfigNoResponse"
    CONFIG_INVALID_RESPONSE = "ConfigInvalidResponse"
    CONFIG_INVALID_CONTENT_TYPE = "ConfigInvalidContentType"
    CLIENT_METADATA_HTTP_NOT_FOUND = "ClientMetadataHttpNotFound"
    CLIENT_METADATA_NO_RESPONSE = "ClientMetadataNoResponse"
    CLIENT_METADATA_INVALID_RESPONSE = "ClientMetadataInvalidResponse"
    CLIENT_METADATA_INVALID_CONTENT_TYPE = "ClientMetadataInvalidContentType"
    IDP_NOT_POTENTIALLY_TRUSTWORTHY = "IdpNotPotentiallyTrustworthy"
    DISABLED_IN_SETTINGS = "DisabledInSettings"
    DISABLED_IN_FLAGS = "DisabledInFlags"
    ERROR_FETCHING_SIGNIN = "ErrorFetchingSignin"
    INVALID_SIGNIN_RESPONSE = "InvalidSigninResponse"
    ACCOUNTS_HTTP_NOT_FOUND = "AccountsHttpNotFound"
    ACCOUNTS_NO_RESPONSE = "AccountsNoResponse"
    ACCOUNTS_INVALID_RESPONSE = "AccountsInvalidResponse"
    ACCOUNTS_LIST_EMPTY = "AccountsListEmpty"
    ACCOUNTS_INVALID_CONTENT_TYPE = "AccountsInvalidContentType"
    ID_TOKEN_HTTP_NOT_FOUND = "IdTokenHttpNotFound"
    ID_TOKEN_NO_RESPONSE = "IdTokenNoResponse"
    ID_TOKEN_INVALID_RESPONSE = "IdTokenInvalidResponse"
    ID_TOKEN_IDP_ERROR_RESPONSE = "IdTokenIdpErrorResponse"
    ID_TOKEN_CROSS_SITE_IDP_ERROR_RESPONSE = "IdTokenCrossSiteIdpErrorResponse"
    ID_TOKEN_INVALID_REQUEST = "IdTokenInvalidRequest"
    ID_TOKEN_INVALID_CONTENT_TYPE = "IdTokenInvalidContentType"
    ERROR_ID_TOKEN = "ErrorIdToken"
    CANCELED = "Canceled"
    RP_PAGE_NOT_VISIBLE = "RpPageNotVisible"
    SILENT_MEDIATION_FAILURE = "SilentMediationFailure"
    THIRD_PARTY_COOKIES_BLOCKED = "ThirdPartyCookiesBlocked"
    NOT_SIGNED_IN_WITH_IDP = "NotSignedInWithIdp"
    MISSING_TRANSIENT_USER_ACTIVATION = "MissingTransientUserActivation"
    REPLACED_BY_ACTIVE_MODE = "ReplacedByActiveMode"
    INVALID_FIELDS_SPECIFIED = "InvalidFieldsSpecified"
    RELYING_PARTY_ORIGIN_IS_OPAQUE = "RelyingPartyOriginIsOpaque"
    TYPE_NOT_MATCHING = "TypeNotMatching"
    UI_DISMISSED_NO_EMBARGO = "UiDismissedNoEmbargo"
    CORS_ERROR = "CorsError"
    SUPPRESSED_BY_SEGMENTATION_PLATFORM = "SuppressedBySegmentationPlatform"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class FederatedAuthUserInfoRequestIssueDetails:
    federated_auth_user_info_request_issue_reason: FederatedAuthUserInfoRequestIssueReason

    def to_json(self):
        json = dict()
        json['federatedAuthUserInfoRequestIssueReason'] = self.federated_auth_user_info_request_issue_reason.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            federated_auth_user_info_request_issue_reason=FederatedAuthUserInfoRequestIssueReason.from_json(json['federatedAuthUserInfoRequestIssueReason']),
        )


class FederatedAuthUserInfoRequestIssueReason(enum.Enum):
    '''
    Represents the failure reason when a getUserInfo() call fails.
    Should be updated alongside FederatedAuthUserInfoRequestResult in
    third_party/blink/public/mojom/devtools/inspector_issue.mojom.
    '''
    NOT_SAME_ORIGIN = "NotSameOrigin"
    NOT_IFRAME = "NotIframe"
    NOT_POTENTIALLY_TRUSTWORTHY = "NotPotentiallyTrustworthy"
    NO_API_PERMISSION = "NoApiPermission"
    NOT_SIGNED_IN_WITH_IDP = "NotSignedInWithIdp"
    NO_ACCOUNT_SHARING_PERMISSION = "NoAccountSharingPermission"
    INVALID_CONFIG_OR_WELL_KNOWN = "InvalidConfigOrWellKnown"
    INVALID_ACCOUNTS_RESPONSE = "InvalidAccountsResponse"
    NO_RETURNING_USER_FROM_FETCHED_ACCOUNTS = "NoReturningUserFromFetchedAccounts"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ClientHintIssueDetails:
    '''
    This issue tracks client hints related issues. It's used to deprecate old
    features, encourage the use of new ones, and provide general guidance.
    '''
    source_code_location: SourceCodeLocation

    client_hint_issue_reason: ClientHintIssueReason

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['clientHintIssueReason'] = self.client_hint_issue_reason.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            client_hint_issue_reason=ClientHintIssueReason.from_json(json['clientHintIssueReason']),
        )


@dataclass
class FailedRequestInfo:
    #: The URL that failed to load.
    url: str

    #: The failure message for the failed request.
    failure_message: str

    request_id: typing.Optional[network.RequestId] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['failureMessage'] = self.failure_message
        if self.request_id is not None:
            json['requestId'] = self.request_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            failure_message=str(json['failureMessage']),
            request_id=network.RequestId.from_json(json['requestId']) if 'requestId' in json else None,
        )


class PartitioningBlobURLInfo(enum.Enum):
    BLOCKED_CROSS_PARTITION_FETCHING = "BlockedCrossPartitionFetching"
    ENFORCE_NOOPENER_FOR_NAVIGATION = "EnforceNoopenerForNavigation"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PartitioningBlobURLIssueDetails:
    #: The BlobURL that failed to load.
    url: str

    #: Additional information about the Partitioning Blob URL issue.
    partitioning_blob_url_info: PartitioningBlobURLInfo

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['partitioningBlobURLInfo'] = self.partitioning_blob_url_info.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            partitioning_blob_url_info=PartitioningBlobURLInfo.from_json(json['partitioningBlobURLInfo']),
        )


class SelectElementAccessibilityIssueReason(enum.Enum):
    DISALLOWED_SELECT_CHILD = "DisallowedSelectChild"
    DISALLOWED_OPT_GROUP_CHILD = "DisallowedOptGroupChild"
    NON_PHRASING_CONTENT_OPTION_CHILD = "NonPhrasingContentOptionChild"
    INTERACTIVE_CONTENT_OPTION_CHILD = "InteractiveContentOptionChild"
    INTERACTIVE_CONTENT_LEGEND_CHILD = "InteractiveContentLegendChild"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SelectElementAccessibilityIssueDetails:
    '''
    This issue warns about errors in the select element content model.
    '''
    node_id: dom.BackendNodeId

    select_element_accessibility_issue_reason: SelectElementAccessibilityIssueReason

    has_disallowed_attributes: bool

    def to_json(self):
        json = dict()
        json['nodeId'] = self.node_id.to_json()
        json['selectElementAccessibilityIssueReason'] = self.select_element_accessibility_issue_reason.to_json()
        json['hasDisallowedAttributes'] = self.has_disallowed_attributes
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            node_id=dom.BackendNodeId.from_json(json['nodeId']),
            select_element_accessibility_issue_reason=SelectElementAccessibilityIssueReason.from_json(json['selectElementAccessibilityIssueReason']),
            has_disallowed_attributes=bool(json['hasDisallowedAttributes']),
        )


class StyleSheetLoadingIssueReason(enum.Enum):
    LATE_IMPORT_RULE = "LateImportRule"
    REQUEST_FAILED = "RequestFailed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class StylesheetLoadingIssueDetails:
    '''
    This issue warns when a referenced stylesheet couldn't be loaded.
    '''
    #: Source code position that referenced the failing stylesheet.
    source_code_location: SourceCodeLocation

    #: Reason why the stylesheet couldn't be loaded.
    style_sheet_loading_issue_reason: StyleSheetLoadingIssueReason

    #: Contains additional info when the failure was due to a request.
    failed_request_info: typing.Optional[FailedRequestInfo] = None

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['styleSheetLoadingIssueReason'] = self.style_sheet_loading_issue_reason.to_json()
        if self.failed_request_info is not None:
            json['failedRequestInfo'] = self.failed_request_info.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            style_sheet_loading_issue_reason=StyleSheetLoadingIssueReason.from_json(json['styleSheetLoadingIssueReason']),
            failed_request_info=FailedRequestInfo.from_json(json['failedRequestInfo']) if 'failedRequestInfo' in json else None,
        )


class PropertyRuleIssueReason(enum.Enum):
    INVALID_SYNTAX = "InvalidSyntax"
    INVALID_INITIAL_VALUE = "InvalidInitialValue"
    INVALID_INHERITS = "InvalidInherits"
    INVALID_NAME = "InvalidName"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PropertyRuleIssueDetails:
    '''
    This issue warns about errors in property rules that lead to property
    registrations being ignored.
    '''
    #: Source code position of the property rule.
    source_code_location: SourceCodeLocation

    #: Reason why the property rule was discarded.
    property_rule_issue_reason: PropertyRuleIssueReason

    #: The value of the property rule property that failed to parse
    property_value: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['sourceCodeLocation'] = self.source_code_location.to_json()
        json['propertyRuleIssueReason'] = self.property_rule_issue_reason.to_json()
        if self.property_value is not None:
            json['propertyValue'] = self.property_value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            source_code_location=SourceCodeLocation.from_json(json['sourceCodeLocation']),
            property_rule_issue_reason=PropertyRuleIssueReason.from_json(json['propertyRuleIssueReason']),
            property_value=str(json['propertyValue']) if 'propertyValue' in json else None,
        )


class InspectorIssueCode(enum.Enum):
    '''
    A unique identifier for the type of issue. Each type may use one of the
    optional fields in InspectorIssueDetails to convey more specific
    information about the kind of issue.
    '''
    COOKIE_ISSUE = "CookieIssue"
    MIXED_CONTENT_ISSUE = "MixedContentIssue"
    BLOCKED_BY_RESPONSE_ISSUE = "BlockedByResponseIssue"
    HEAVY_AD_ISSUE = "HeavyAdIssue"
    CONTENT_SECURITY_POLICY_ISSUE = "ContentSecurityPolicyIssue"
    SHARED_ARRAY_BUFFER_ISSUE = "SharedArrayBufferIssue"
    LOW_TEXT_CONTRAST_ISSUE = "LowTextContrastIssue"
    CORS_ISSUE = "CorsIssue"
    ATTRIBUTION_REPORTING_ISSUE = "AttributionReportingIssue"
    QUIRKS_MODE_ISSUE = "QuirksModeIssue"
    PARTITIONING_BLOB_URL_ISSUE = "PartitioningBlobURLIssue"
    NAVIGATOR_USER_AGENT_ISSUE = "NavigatorUserAgentIssue"
    GENERIC_ISSUE = "GenericIssue"
    DEPRECATION_ISSUE = "DeprecationIssue"
    CLIENT_HINT_ISSUE = "ClientHintIssue"
    FEDERATED_AUTH_REQUEST_ISSUE = "FederatedAuthRequestIssue"
    BOUNCE_TRACKING_ISSUE = "BounceTrackingIssue"
    COOKIE_DEPRECATION_METADATA_ISSUE = "CookieDeprecationMetadataIssue"
    STYLESHEET_LOADING_ISSUE = "StylesheetLoadingIssue"
    FEDERATED_AUTH_USER_INFO_REQUEST_ISSUE = "FederatedAuthUserInfoRequestIssue"
    PROPERTY_RULE_ISSUE = "PropertyRuleIssue"
    SHARED_DICTIONARY_ISSUE = "SharedDictionaryIssue"
    SELECT_ELEMENT_ACCESSIBILITY_ISSUE = "SelectElementAccessibilityIssue"
    SRI_MESSAGE_SIGNATURE_ISSUE = "SRIMessageSignatureIssue"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class InspectorIssueDetails:
    '''
    This struct holds a list of optional fields with additional information
    specific to the kind of issue. When adding a new issue code, please also
    add a new optional field to this type.
    '''
    cookie_issue_details: typing.Optional[CookieIssueDetails] = None

    mixed_content_issue_details: typing.Optional[MixedContentIssueDetails] = None

    blocked_by_response_issue_details: typing.Optional[BlockedByResponseIssueDetails] = None

    heavy_ad_issue_details: typing.Optional[HeavyAdIssueDetails] = None

    content_security_policy_issue_details: typing.Optional[ContentSecurityPolicyIssueDetails] = None

    shared_array_buffer_issue_details: typing.Optional[SharedArrayBufferIssueDetails] = None

    low_text_contrast_issue_details: typing.Optional[LowTextContrastIssueDetails] = None

    cors_issue_details: typing.Optional[CorsIssueDetails] = None

    attribution_reporting_issue_details: typing.Optional[AttributionReportingIssueDetails] = None

    quirks_mode_issue_details: typing.Optional[QuirksModeIssueDetails] = None

    partitioning_blob_url_issue_details: typing.Optional[PartitioningBlobURLIssueDetails] = None

    navigator_user_agent_issue_details: typing.Optional[NavigatorUserAgentIssueDetails] = None

    generic_issue_details: typing.Optional[GenericIssueDetails] = None

    deprecation_issue_details: typing.Optional[DeprecationIssueDetails] = None

    client_hint_issue_details: typing.Optional[ClientHintIssueDetails] = None

    federated_auth_request_issue_details: typing.Optional[FederatedAuthRequestIssueDetails] = None

    bounce_tracking_issue_details: typing.Optional[BounceTrackingIssueDetails] = None

    cookie_deprecation_metadata_issue_details: typing.Optional[CookieDeprecationMetadataIssueDetails] = None

    stylesheet_loading_issue_details: typing.Optional[StylesheetLoadingIssueDetails] = None

    property_rule_issue_details: typing.Optional[PropertyRuleIssueDetails] = None

    federated_auth_user_info_request_issue_details: typing.Optional[FederatedAuthUserInfoRequestIssueDetails] = None

    shared_dictionary_issue_details: typing.Optional[SharedDictionaryIssueDetails] = None

    select_element_accessibility_issue_details: typing.Optional[SelectElementAccessibilityIssueDetails] = None

    sri_message_signature_issue_details: typing.Optional[SRIMessageSignatureIssueDetails] = None

    def to_json(self):
        json = dict()
        if self.cookie_issue_details is not None:
            json['cookieIssueDetails'] = self.cookie_issue_details.to_json()
        if self.mixed_content_issue_details is not None:
            json['mixedContentIssueDetails'] = self.mixed_content_issue_details.to_json()
        if self.blocked_by_response_issue_details is not None:
            json['blockedByResponseIssueDetails'] = self.blocked_by_response_issue_details.to_json()
        if self.heavy_ad_issue_details is not None:
            json['heavyAdIssueDetails'] = self.heavy_ad_issue_details.to_json()
        if self.content_security_policy_issue_details is not None:
            json['contentSecurityPolicyIssueDetails'] = self.content_security_policy_issue_details.to_json()
        if self.shared_array_buffer_issue_details is not None:
            json['sharedArrayBufferIssueDetails'] = self.shared_array_buffer_issue_details.to_json()
        if self.low_text_contrast_issue_details is not None:
            json['lowTextContrastIssueDetails'] = self.low_text_contrast_issue_details.to_json()
        if self.cors_issue_details is not None:
            json['corsIssueDetails'] = self.cors_issue_details.to_json()
        if self.attribution_reporting_issue_details is not None:
            json['attributionReportingIssueDetails'] = self.attribution_reporting_issue_details.to_json()
        if self.quirks_mode_issue_details is not None:
            json['quirksModeIssueDetails'] = self.quirks_mode_issue_details.to_json()
        if self.partitioning_blob_url_issue_details is not None:
            json['partitioningBlobURLIssueDetails'] = self.partitioning_blob_url_issue_details.to_json()
        if self.navigator_user_agent_issue_details is not None:
            json['navigatorUserAgentIssueDetails'] = self.navigator_user_agent_issue_details.to_json()
        if self.generic_issue_details is not None:
            json['genericIssueDetails'] = self.generic_issue_details.to_json()
        if self.deprecation_issue_details is not None:
            json['deprecationIssueDetails'] = self.deprecation_issue_details.to_json()
        if self.client_hint_issue_details is not None:
            json['clientHintIssueDetails'] = self.client_hint_issue_details.to_json()
        if self.federated_auth_request_issue_details is not None:
            json['federatedAuthRequestIssueDetails'] = self.federated_auth_request_issue_details.to_json()
        if self.bounce_tracking_issue_details is not None:
            json['bounceTrackingIssueDetails'] = self.bounce_tracking_issue_details.to_json()
        if self.cookie_deprecation_metadata_issue_details is not None:
            json['cookieDeprecationMetadataIssueDetails'] = self.cookie_deprecation_metadata_issue_details.to_json()
        if self.stylesheet_loading_issue_details is not None:
            json['stylesheetLoadingIssueDetails'] = self.stylesheet_loading_issue_details.to_json()
        if self.property_rule_issue_details is not None:
            json['propertyRuleIssueDetails'] = self.property_rule_issue_details.to_json()
        if self.federated_auth_user_info_request_issue_details is not None:
            json['federatedAuthUserInfoRequestIssueDetails'] = self.federated_auth_user_info_request_issue_details.to_json()
        if self.shared_dictionary_issue_details is not None:
            json['sharedDictionaryIssueDetails'] = self.shared_dictionary_issue_details.to_json()
        if self.select_element_accessibility_issue_details is not None:
            json['selectElementAccessibilityIssueDetails'] = self.select_element_accessibility_issue_details.to_json()
        if self.sri_message_signature_issue_details is not None:
            json['sriMessageSignatureIssueDetails'] = self.sri_message_signature_issue_details.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cookie_issue_details=CookieIssueDetails.from_json(json['cookieIssueDetails']) if 'cookieIssueDetails' in json else None,
            mixed_content_issue_details=MixedContentIssueDetails.from_json(json['mixedContentIssueDetails']) if 'mixedContentIssueDetails' in json else None,
            blocked_by_response_issue_details=BlockedByResponseIssueDetails.from_json(json['blockedByResponseIssueDetails']) if 'blockedByResponseIssueDetails' in json else None,
            heavy_ad_issue_details=HeavyAdIssueDetails.from_json(json['heavyAdIssueDetails']) if 'heavyAdIssueDetails' in json else None,
            content_security_policy_issue_details=ContentSecurityPolicyIssueDetails.from_json(json['contentSecurityPolicyIssueDetails']) if 'contentSecurityPolicyIssueDetails' in json else None,
            shared_array_buffer_issue_details=SharedArrayBufferIssueDetails.from_json(json['sharedArrayBufferIssueDetails']) if 'sharedArrayBufferIssueDetails' in json else None,
            low_text_contrast_issue_details=LowTextContrastIssueDetails.from_json(json['lowTextContrastIssueDetails']) if 'lowTextContrastIssueDetails' in json else None,
            cors_issue_details=CorsIssueDetails.from_json(json['corsIssueDetails']) if 'corsIssueDetails' in json else None,
            attribution_reporting_issue_details=AttributionReportingIssueDetails.from_json(json['attributionReportingIssueDetails']) if 'attributionReportingIssueDetails' in json else None,
            quirks_mode_issue_details=QuirksModeIssueDetails.from_json(json['quirksModeIssueDetails']) if 'quirksModeIssueDetails' in json else None,
            partitioning_blob_url_issue_details=PartitioningBlobURLIssueDetails.from_json(json['partitioningBlobURLIssueDetails']) if 'partitioningBlobURLIssueDetails' in json else None,
            navigator_user_agent_issue_details=NavigatorUserAgentIssueDetails.from_json(json['navigatorUserAgentIssueDetails']) if 'navigatorUserAgentIssueDetails' in json else None,
            generic_issue_details=GenericIssueDetails.from_json(json['genericIssueDetails']) if 'genericIssueDetails' in json else None,
            deprecation_issue_details=DeprecationIssueDetails.from_json(json['deprecationIssueDetails']) if 'deprecationIssueDetails' in json else None,
            client_hint_issue_details=ClientHintIssueDetails.from_json(json['clientHintIssueDetails']) if 'clientHintIssueDetails' in json else None,
            federated_auth_request_issue_details=FederatedAuthRequestIssueDetails.from_json(json['federatedAuthRequestIssueDetails']) if 'federatedAuthRequestIssueDetails' in json else None,
            bounce_tracking_issue_details=BounceTrackingIssueDetails.from_json(json['bounceTrackingIssueDetails']) if 'bounceTrackingIssueDetails' in json else None,
            cookie_deprecation_metadata_issue_details=CookieDeprecationMetadataIssueDetails.from_json(json['cookieDeprecationMetadataIssueDetails']) if 'cookieDeprecationMetadataIssueDetails' in json else None,
            stylesheet_loading_issue_details=StylesheetLoadingIssueDetails.from_json(json['stylesheetLoadingIssueDetails']) if 'stylesheetLoadingIssueDetails' in json else None,
            property_rule_issue_details=PropertyRuleIssueDetails.from_json(json['propertyRuleIssueDetails']) if 'propertyRuleIssueDetails' in json else None,
            federated_auth_user_info_request_issue_details=FederatedAuthUserInfoRequestIssueDetails.from_json(json['federatedAuthUserInfoRequestIssueDetails']) if 'federatedAuthUserInfoRequestIssueDetails' in json else None,
            shared_dictionary_issue_details=SharedDictionaryIssueDetails.from_json(json['sharedDictionaryIssueDetails']) if 'sharedDictionaryIssueDetails' in json else None,
            select_element_accessibility_issue_details=SelectElementAccessibilityIssueDetails.from_json(json['selectElementAccessibilityIssueDetails']) if 'selectElementAccessibilityIssueDetails' in json else None,
            sri_message_signature_issue_details=SRIMessageSignatureIssueDetails.from_json(json['sriMessageSignatureIssueDetails']) if 'sriMessageSignatureIssueDetails' in json else None,
        )


class IssueId(str):
    '''
    A unique id for a DevTools inspector issue. Allows other entities (e.g.
    exceptions, CDP message, console messages, etc.) to reference an issue.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> IssueId:
        return cls(json)

    def __repr__(self):
        return 'IssueId({})'.format(super().__repr__())


@dataclass
class InspectorIssue:
    '''
    An inspector issue reported from the back-end.
    '''
    code: InspectorIssueCode

    details: InspectorIssueDetails

    #: A unique id for this issue. May be omitted if no other entity (e.g.
    #: exception, CDP message, etc.) is referencing this issue.
    issue_id: typing.Optional[IssueId] = None

    def to_json(self):
        json = dict()
        json['code'] = self.code.to_json()
        json['details'] = self.details.to_json()
        if self.issue_id is not None:
            json['issueId'] = self.issue_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            code=InspectorIssueCode.from_json(json['code']),
            details=InspectorIssueDetails.from_json(json['details']),
            issue_id=IssueId.from_json(json['issueId']) if 'issueId' in json else None,
        )


def get_encoded_response(
        request_id: network.RequestId,
        encoding: str,
        quality: typing.Optional[float] = None,
        size_only: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[str], int, int]]:
    '''
    Returns the response body and size if it were re-encoded with the specified settings. Only
    applies to images.

    :param request_id: Identifier of the network request to get content for.
    :param encoding: The encoding to use.
    :param quality: *(Optional)* The quality of the encoding (0-1). (defaults to 1)
    :param size_only: *(Optional)* Whether to only return the size information (defaults to false).
    :returns: A tuple with the following items:

        0. **body** - *(Optional)* The encoded body as a base64 string. Omitted if sizeOnly is true.
        1. **originalSize** - Size before re-encoding.
        2. **encodedSize** - Size after re-encoding.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['encoding'] = encoding
    if quality is not None:
        params['quality'] = quality
    if size_only is not None:
        params['sizeOnly'] = size_only
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.getEncodedResponse',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['body']) if 'body' in json else None,
        int(json['originalSize']),
        int(json['encodedSize'])
    )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables issues domain, prevents further issues from being reported to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables issues domain, sends the issues collected so far to the client by means of the
    ``issueAdded`` event.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.enable',
    }
    json = yield cmd_dict


def check_contrast(
        report_aaa: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Runs the contrast check for the target page. Found issues are reported
    using Audits.issueAdded event.

    :param report_aaa: *(Optional)* Whether to report WCAG AAA level issues. Default is false.
    '''
    params: T_JSON_DICT = dict()
    if report_aaa is not None:
        params['reportAAA'] = report_aaa
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.checkContrast',
        'params': params,
    }
    json = yield cmd_dict


def check_forms_issues() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[GenericIssueDetails]]:
    '''
    Runs the form issues check for the target page. Found issues are reported
    using Audits.issueAdded event.

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Audits.checkFormsIssues',
    }
    json = yield cmd_dict
    return [GenericIssueDetails.from_json(i) for i in json['formIssues']]


@event_class('Audits.issueAdded')
@dataclass
class IssueAdded:
    issue: InspectorIssue

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> IssueAdded:
        return cls(
            issue=InspectorIssue.from_json(json['issue'])
        )

# === NexusCore/openenv\Lib\site-packages\numpy\polynomial\hermite.py ===
"""
==============================================================
Hermite Series, "Physicists" (:mod:`numpy.polynomial.hermite`)
==============================================================

This module provides a number of objects (mostly functions) useful for
dealing with Hermite series, including a `Hermite` class that
encapsulates the usual arithmetic operations.  (General information
on how this module represents and works with such polynomials is in the
docstring for its "parent" sub-package, `numpy.polynomial`).

Classes
-------
.. autosummary::
   :toctree: generated/

   Hermite

Constants
---------
.. autosummary::
   :toctree: generated/

   hermdomain
   hermzero
   hermone
   hermx

Arithmetic
----------
.. autosummary::
   :toctree: generated/

   hermadd
   hermsub
   hermmulx
   hermmul
   hermdiv
   hermpow
   hermval
   hermval2d
   hermval3d
   hermgrid2d
   hermgrid3d

Calculus
--------
.. autosummary::
   :toctree: generated/

   hermder
   hermint

Misc Functions
--------------
.. autosummary::
   :toctree: generated/

   hermfromroots
   hermroots
   hermvander
   hermvander2d
   hermvander3d
   hermgauss
   hermweight
   hermcompanion
   hermfit
   hermtrim
   hermline
   herm2poly
   poly2herm

See also
--------
`numpy.polynomial`

"""
import numpy as np
import numpy.linalg as la
from numpy.lib.array_utils import normalize_axis_index

from . import polyutils as pu
from ._polybase import ABCPolyBase

__all__ = [
    'hermzero', 'hermone', 'hermx', 'hermdomain', 'hermline', 'hermadd',
    'hermsub', 'hermmulx', 'hermmul', 'hermdiv', 'hermpow', 'hermval',
    'hermder', 'hermint', 'herm2poly', 'poly2herm', 'hermfromroots',
    'hermvander', 'hermfit', 'hermtrim', 'hermroots', 'Hermite',
    'hermval2d', 'hermval3d', 'hermgrid2d', 'hermgrid3d', 'hermvander2d',
    'hermvander3d', 'hermcompanion', 'hermgauss', 'hermweight']

hermtrim = pu.trimcoef


def poly2herm(pol):
    """
    poly2herm(pol)

    Convert a polynomial to a Hermite series.

    Convert an array representing the coefficients of a polynomial (relative
    to the "standard" basis) ordered from lowest degree to highest, to an
    array of the coefficients of the equivalent Hermite series, ordered
    from lowest to highest degree.

    Parameters
    ----------
    pol : array_like
        1-D array containing the polynomial coefficients

    Returns
    -------
    c : ndarray
        1-D array containing the coefficients of the equivalent Hermite
        series.

    See Also
    --------
    herm2poly

    Notes
    -----
    The easy way to do conversions between polynomial basis sets
    is to use the convert method of a class instance.

    Examples
    --------
    >>> from numpy.polynomial.hermite import poly2herm
    >>> poly2herm(np.arange(4))
    array([1.   ,  2.75 ,  0.5  ,  0.375])

    """
    [pol] = pu.as_series([pol])
    deg = len(pol) - 1
    res = 0
    for i in range(deg, -1, -1):
        res = hermadd(hermmulx(res), pol[i])
    return res


def herm2poly(c):
    """
    Convert a Hermite series to a polynomial.

    Convert an array representing the coefficients of a Hermite series,
    ordered from lowest degree to highest, to an array of the coefficients
    of the equivalent polynomial (relative to the "standard" basis) ordered
    from lowest to highest degree.

    Parameters
    ----------
    c : array_like
        1-D array containing the Hermite series coefficients, ordered
        from lowest order term to highest.

    Returns
    -------
    pol : ndarray
        1-D array containing the coefficients of the equivalent polynomial
        (relative to the "standard" basis) ordered from lowest order term
        to highest.

    See Also
    --------
    poly2herm

    Notes
    -----
    The easy way to do conversions between polynomial basis sets
    is to use the convert method of a class instance.

    Examples
    --------
    >>> from numpy.polynomial.hermite import herm2poly
    >>> herm2poly([ 1.   ,  2.75 ,  0.5  ,  0.375])
    array([0., 1., 2., 3.])

    """
    from .polynomial import polyadd, polymulx, polysub

    [c] = pu.as_series([c])
    n = len(c)
    if n == 1:
        return c
    if n == 2:
        c[1] *= 2
        return c
    else:
        c0 = c[-2]
        c1 = c[-1]
        # i is the current degree of c1
        for i in range(n - 1, 1, -1):
            tmp = c0
            c0 = polysub(c[i - 2], c1 * (2 * (i - 1)))
            c1 = polyadd(tmp, polymulx(c1) * 2)
        return polyadd(c0, polymulx(c1) * 2)


#
# These are constant arrays are of integer type so as to be compatible
# with the widest range of other types, such as Decimal.
#

# Hermite
hermdomain = np.array([-1., 1.])

# Hermite coefficients representing zero.
hermzero = np.array([0])

# Hermite coefficients representing one.
hermone = np.array([1])

# Hermite coefficients representing the identity x.
hermx = np.array([0, 1 / 2])


def hermline(off, scl):
    """
    Hermite series whose graph is a straight line.



    Parameters
    ----------
    off, scl : scalars
        The specified line is given by ``off + scl*x``.

    Returns
    -------
    y : ndarray
        This module's representation of the Hermite series for
        ``off + scl*x``.

    See Also
    --------
    numpy.polynomial.polynomial.polyline
    numpy.polynomial.chebyshev.chebline
    numpy.polynomial.legendre.legline
    numpy.polynomial.laguerre.lagline
    numpy.polynomial.hermite_e.hermeline

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermline, hermval
    >>> hermval(0,hermline(3, 2))
    3.0
    >>> hermval(1,hermline(3, 2))
    5.0

    """
    if scl != 0:
        return np.array([off, scl / 2])
    else:
        return np.array([off])


def hermfromroots(roots):
    """
    Generate a Hermite series with given roots.

    The function returns the coefficients of the polynomial

    .. math:: p(x) = (x - r_0) * (x - r_1) * ... * (x - r_n),

    in Hermite form, where the :math:`r_n` are the roots specified in `roots`.
    If a zero has multiplicity n, then it must appear in `roots` n times.
    For instance, if 2 is a root of multiplicity three and 3 is a root of
    multiplicity 2, then `roots` looks something like [2, 2, 2, 3, 3]. The
    roots can appear in any order.

    If the returned coefficients are `c`, then

    .. math:: p(x) = c_0 + c_1 * H_1(x) + ... +  c_n * H_n(x)

    The coefficient of the last term is not generally 1 for monic
    polynomials in Hermite form.

    Parameters
    ----------
    roots : array_like
        Sequence containing the roots.

    Returns
    -------
    out : ndarray
        1-D array of coefficients.  If all roots are real then `out` is a
        real array, if some of the roots are complex, then `out` is complex
        even if all the coefficients in the result are real (see Examples
        below).

    See Also
    --------
    numpy.polynomial.polynomial.polyfromroots
    numpy.polynomial.legendre.legfromroots
    numpy.polynomial.laguerre.lagfromroots
    numpy.polynomial.chebyshev.chebfromroots
    numpy.polynomial.hermite_e.hermefromroots

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermfromroots, hermval
    >>> coef = hermfromroots((-1, 0, 1))
    >>> hermval((-1, 0, 1), coef)
    array([0.,  0.,  0.])
    >>> coef = hermfromroots((-1j, 1j))
    >>> hermval((-1j, 1j), coef)
    array([0.+0.j, 0.+0.j])

    """
    return pu._fromroots(hermline, hermmul, roots)


def hermadd(c1, c2):
    """
    Add one Hermite series to another.

    Returns the sum of two Hermite series `c1` + `c2`.  The arguments
    are sequences of coefficients ordered from lowest order term to
    highest, i.e., [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Array representing the Hermite series of their sum.

    See Also
    --------
    hermsub, hermmulx, hermmul, hermdiv, hermpow

    Notes
    -----
    Unlike multiplication, division, etc., the sum of two Hermite series
    is a Hermite series (without having to "reproject" the result onto
    the basis set) so addition, just like that of "standard" polynomials,
    is simply "component-wise."

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermadd
    >>> hermadd([1, 2, 3], [1, 2, 3, 4])
    array([2., 4., 6., 4.])

    """
    return pu._add(c1, c2)


def hermsub(c1, c2):
    """
    Subtract one Hermite series from another.

    Returns the difference of two Hermite series `c1` - `c2`.  The
    sequences of coefficients are from lowest order term to highest, i.e.,
    [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Of Hermite series coefficients representing their difference.

    See Also
    --------
    hermadd, hermmulx, hermmul, hermdiv, hermpow

    Notes
    -----
    Unlike multiplication, division, etc., the difference of two Hermite
    series is a Hermite series (without having to "reproject" the result
    onto the basis set) so subtraction, just like that of "standard"
    polynomials, is simply "component-wise."

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermsub
    >>> hermsub([1, 2, 3, 4], [1, 2, 3])
    array([0.,  0.,  0.,  4.])

    """
    return pu._sub(c1, c2)


def hermmulx(c):
    """Multiply a Hermite series by x.

    Multiply the Hermite series `c` by x, where x is the independent
    variable.


    Parameters
    ----------
    c : array_like
        1-D array of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Array representing the result of the multiplication.

    See Also
    --------
    hermadd, hermsub, hermmul, hermdiv, hermpow

    Notes
    -----
    The multiplication uses the recursion relationship for Hermite
    polynomials in the form

    .. math::

        xP_i(x) = (P_{i + 1}(x)/2 + i*P_{i - 1}(x))

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermmulx
    >>> hermmulx([1, 2, 3])
    array([2. , 6.5, 1. , 1.5])

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    # The zero series needs special treatment
    if len(c) == 1 and c[0] == 0:
        return c

    prd = np.empty(len(c) + 1, dtype=c.dtype)
    prd[0] = c[0] * 0
    prd[1] = c[0] / 2
    for i in range(1, len(c)):
        prd[i + 1] = c[i] / 2
        prd[i - 1] += c[i] * i
    return prd


def hermmul(c1, c2):
    """
    Multiply one Hermite series by another.

    Returns the product of two Hermite series `c1` * `c2`.  The arguments
    are sequences of coefficients, from lowest order "term" to highest,
    e.g., [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Of Hermite series coefficients representing their product.

    See Also
    --------
    hermadd, hermsub, hermmulx, hermdiv, hermpow

    Notes
    -----
    In general, the (polynomial) product of two C-series results in terms
    that are not in the Hermite polynomial basis set.  Thus, to express
    the product as a Hermite series, it is necessary to "reproject" the
    product onto said basis set, which may produce "unintuitive" (but
    correct) results; see Examples section below.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermmul
    >>> hermmul([1, 2, 3], [0, 1, 2])
    array([52.,  29.,  52.,   7.,   6.])

    """
    # s1, s2 are trimmed copies
    [c1, c2] = pu.as_series([c1, c2])

    if len(c1) > len(c2):
        c = c2
        xs = c1
    else:
        c = c1
        xs = c2

    if len(c) == 1:
        c0 = c[0] * xs
        c1 = 0
    elif len(c) == 2:
        c0 = c[0] * xs
        c1 = c[1] * xs
    else:
        nd = len(c)
        c0 = c[-2] * xs
        c1 = c[-1] * xs
        for i in range(3, len(c) + 1):
            tmp = c0
            nd = nd - 1
            c0 = hermsub(c[-i] * xs, c1 * (2 * (nd - 1)))
            c1 = hermadd(tmp, hermmulx(c1) * 2)
    return hermadd(c0, hermmulx(c1) * 2)


def hermdiv(c1, c2):
    """
    Divide one Hermite series by another.

    Returns the quotient-with-remainder of two Hermite series
    `c1` / `c2`.  The arguments are sequences of coefficients from lowest
    order "term" to highest, e.g., [1,2,3] represents the series
    ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    [quo, rem] : ndarrays
        Of Hermite series coefficients representing the quotient and
        remainder.

    See Also
    --------
    hermadd, hermsub, hermmulx, hermmul, hermpow

    Notes
    -----
    In general, the (polynomial) division of one Hermite series by another
    results in quotient and remainder terms that are not in the Hermite
    polynomial basis set.  Thus, to express these results as a Hermite
    series, it is necessary to "reproject" the results onto the Hermite
    basis set, which may produce "unintuitive" (but correct) results; see
    Examples section below.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermdiv
    >>> hermdiv([ 52.,  29.,  52.,   7.,   6.], [0, 1, 2])
    (array([1., 2., 3.]), array([0.]))
    >>> hermdiv([ 54.,  31.,  52.,   7.,   6.], [0, 1, 2])
    (array([1., 2., 3.]), array([2., 2.]))
    >>> hermdiv([ 53.,  30.,  52.,   7.,   6.], [0, 1, 2])
    (array([1., 2., 3.]), array([1., 1.]))

    """
    return pu._div(hermmul, c1, c2)


def hermpow(c, pow, maxpower=16):
    """Raise a Hermite series to a power.

    Returns the Hermite series `c` raised to the power `pow`. The
    argument `c` is a sequence of coefficients ordered from low to high.
    i.e., [1,2,3] is the series  ``P_0 + 2*P_1 + 3*P_2.``

    Parameters
    ----------
    c : array_like
        1-D array of Hermite series coefficients ordered from low to
        high.
    pow : integer
        Power to which the series will be raised
    maxpower : integer, optional
        Maximum power allowed. This is mainly to limit growth of the series
        to unmanageable size. Default is 16

    Returns
    -------
    coef : ndarray
        Hermite series of power.

    See Also
    --------
    hermadd, hermsub, hermmulx, hermmul, hermdiv

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermpow
    >>> hermpow([1, 2, 3], 2)
    array([81.,  52.,  82.,  12.,   9.])

    """
    return pu._pow(hermmul, c, pow, maxpower)


def hermder(c, m=1, scl=1, axis=0):
    """
    Differentiate a Hermite series.

    Returns the Hermite series coefficients `c` differentiated `m` times
    along `axis`.  At each iteration the result is multiplied by `scl` (the
    scaling factor is for use in a linear change of variable). The argument
    `c` is an array of coefficients from low to high degree along each
    axis, e.g., [1,2,3] represents the series ``1*H_0 + 2*H_1 + 3*H_2``
    while [[1,2],[1,2]] represents ``1*H_0(x)*H_0(y) + 1*H_1(x)*H_0(y) +
    2*H_0(x)*H_1(y) + 2*H_1(x)*H_1(y)`` if axis=0 is ``x`` and axis=1 is
    ``y``.

    Parameters
    ----------
    c : array_like
        Array of Hermite series coefficients. If `c` is multidimensional the
        different axis correspond to different variables with the degree in
        each axis given by the corresponding index.
    m : int, optional
        Number of derivatives taken, must be non-negative. (Default: 1)
    scl : scalar, optional
        Each differentiation is multiplied by `scl`.  The end result is
        multiplication by ``scl**m``.  This is for use in a linear change of
        variable. (Default: 1)
    axis : int, optional
        Axis over which the derivative is taken. (Default: 0).

    Returns
    -------
    der : ndarray
        Hermite series of the derivative.

    See Also
    --------
    hermint

    Notes
    -----
    In general, the result of differentiating a Hermite series does not
    resemble the same operation on a power series. Thus the result of this
    function may be "unintuitive," albeit correct; see Examples section
    below.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermder
    >>> hermder([ 1. ,  0.5,  0.5,  0.5])
    array([1., 2., 3.])
    >>> hermder([-0.5,  1./2.,  1./8.,  1./12.,  1./16.], m=2)
    array([1., 2., 3.])

    """
    c = np.array(c, ndmin=1, copy=True)
    if c.dtype.char in '?bBhHiIlLqQpP':
        c = c.astype(np.double)
    cnt = pu._as_int(m, "the order of derivation")
    iaxis = pu._as_int(axis, "the axis")
    if cnt < 0:
        raise ValueError("The order of derivation must be non-negative")
    iaxis = normalize_axis_index(iaxis, c.ndim)

    if cnt == 0:
        return c

    c = np.moveaxis(c, iaxis, 0)
    n = len(c)
    if cnt >= n:
        c = c[:1] * 0
    else:
        for i in range(cnt):
            n = n - 1
            c *= scl
            der = np.empty((n,) + c.shape[1:], dtype=c.dtype)
            for j in range(n, 0, -1):
                der[j - 1] = (2 * j) * c[j]
            c = der
    c = np.moveaxis(c, 0, iaxis)
    return c


def hermint(c, m=1, k=[], lbnd=0, scl=1, axis=0):
    """
    Integrate a Hermite series.

    Returns the Hermite series coefficients `c` integrated `m` times from
    `lbnd` along `axis`. At each iteration the resulting series is
    **multiplied** by `scl` and an integration constant, `k`, is added.
    The scaling factor is for use in a linear change of variable.  ("Buyer
    beware": note that, depending on what one is doing, one may want `scl`
    to be the reciprocal of what one might expect; for more information,
    see the Notes section below.)  The argument `c` is an array of
    coefficients from low to high degree along each axis, e.g., [1,2,3]
    represents the series ``H_0 + 2*H_1 + 3*H_2`` while [[1,2],[1,2]]
    represents ``1*H_0(x)*H_0(y) + 1*H_1(x)*H_0(y) + 2*H_0(x)*H_1(y) +
    2*H_1(x)*H_1(y)`` if axis=0 is ``x`` and axis=1 is ``y``.

    Parameters
    ----------
    c : array_like
        Array of Hermite series coefficients. If c is multidimensional the
        different axis correspond to different variables with the degree in
        each axis given by the corresponding index.
    m : int, optional
        Order of integration, must be positive. (Default: 1)
    k : {[], list, scalar}, optional
        Integration constant(s).  The value of the first integral at
        ``lbnd`` is the first value in the list, the value of the second
        integral at ``lbnd`` is the second value, etc.  If ``k == []`` (the
        default), all constants are set to zero.  If ``m == 1``, a single
        scalar can be given instead of a list.
    lbnd : scalar, optional
        The lower bound of the integral. (Default: 0)
    scl : scalar, optional
        Following each integration the result is *multiplied* by `scl`
        before the integration constant is added. (Default: 1)
    axis : int, optional
        Axis over which the integral is taken. (Default: 0).

    Returns
    -------
    S : ndarray
        Hermite series coefficients of the integral.

    Raises
    ------
    ValueError
        If ``m < 0``, ``len(k) > m``, ``np.ndim(lbnd) != 0``, or
        ``np.ndim(scl) != 0``.

    See Also
    --------
    hermder

    Notes
    -----
    Note that the result of each integration is *multiplied* by `scl`.
    Why is this important to note?  Say one is making a linear change of
    variable :math:`u = ax + b` in an integral relative to `x`.  Then
    :math:`dx = du/a`, so one will need to set `scl` equal to
    :math:`1/a` - perhaps not what one would have first thought.

    Also note that, in general, the result of integrating a C-series needs
    to be "reprojected" onto the C-series basis set.  Thus, typically,
    the result of this function is "unintuitive," albeit correct; see
    Examples section below.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermint
    >>> hermint([1,2,3]) # integrate once, value 0 at 0.
    array([1. , 0.5, 0.5, 0.5])
    >>> hermint([1,2,3], m=2) # integrate twice, value & deriv 0 at 0
    array([-0.5       ,  0.5       ,  0.125     ,  0.08333333,  0.0625    ]) # may vary
    >>> hermint([1,2,3], k=1) # integrate once, value 1 at 0.
    array([2. , 0.5, 0.5, 0.5])
    >>> hermint([1,2,3], lbnd=-1) # integrate once, value 0 at -1
    array([-2. ,  0.5,  0.5,  0.5])
    >>> hermint([1,2,3], m=2, k=[1,2], lbnd=-1)
    array([ 1.66666667, -0.5       ,  0.125     ,  0.08333333,  0.0625    ]) # may vary

    """
    c = np.array(c, ndmin=1, copy=True)
    if c.dtype.char in '?bBhHiIlLqQpP':
        c = c.astype(np.double)
    if not np.iterable(k):
        k = [k]
    cnt = pu._as_int(m, "the order of integration")
    iaxis = pu._as_int(axis, "the axis")
    if cnt < 0:
        raise ValueError("The order of integration must be non-negative")
    if len(k) > cnt:
        raise ValueError("Too many integration constants")
    if np.ndim(lbnd) != 0:
        raise ValueError("lbnd must be a scalar.")
    if np.ndim(scl) != 0:
        raise ValueError("scl must be a scalar.")
    iaxis = normalize_axis_index(iaxis, c.ndim)

    if cnt == 0:
        return c

    c = np.moveaxis(c, iaxis, 0)
    k = list(k) + [0] * (cnt - len(k))
    for i in range(cnt):
        n = len(c)
        c *= scl
        if n == 1 and np.all(c[0] == 0):
            c[0] += k[i]
        else:
            tmp = np.empty((n + 1,) + c.shape[1:], dtype=c.dtype)
            tmp[0] = c[0] * 0
            tmp[1] = c[0] / 2
            for j in range(1, n):
                tmp[j + 1] = c[j] / (2 * (j + 1))
            tmp[0] += k[i] - hermval(lbnd, tmp)
            c = tmp
    c = np.moveaxis(c, 0, iaxis)
    return c


def hermval(x, c, tensor=True):
    """
    Evaluate an Hermite series at points x.

    If `c` is of length ``n + 1``, this function returns the value:

    .. math:: p(x) = c_0 * H_0(x) + c_1 * H_1(x) + ... + c_n * H_n(x)

    The parameter `x` is converted to an array only if it is a tuple or a
    list, otherwise it is treated as a scalar. In either case, either `x`
    or its elements must support multiplication and addition both with
    themselves and with the elements of `c`.

    If `c` is a 1-D array, then ``p(x)`` will have the same shape as `x`.  If
    `c` is multidimensional, then the shape of the result depends on the
    value of `tensor`. If `tensor` is true the shape will be c.shape[1:] +
    x.shape. If `tensor` is false the shape will be c.shape[1:]. Note that
    scalars have shape (,).

    Trailing zeros in the coefficients will be used in the evaluation, so
    they should be avoided if efficiency is a concern.

    Parameters
    ----------
    x : array_like, compatible object
        If `x` is a list or tuple, it is converted to an ndarray, otherwise
        it is left unchanged and treated as a scalar. In either case, `x`
        or its elements must support addition and multiplication with
        themselves and with the elements of `c`.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree n are contained in c[n]. If `c` is multidimensional the
        remaining indices enumerate multiple polynomials. In the two
        dimensional case the coefficients may be thought of as stored in
        the columns of `c`.
    tensor : boolean, optional
        If True, the shape of the coefficient array is extended with ones
        on the right, one for each dimension of `x`. Scalars have dimension 0
        for this action. The result is that every column of coefficients in
        `c` is evaluated for every element of `x`. If False, `x` is broadcast
        over the columns of `c` for the evaluation.  This keyword is useful
        when `c` is multidimensional. The default value is True.

    Returns
    -------
    values : ndarray, algebra_like
        The shape of the return value is described above.

    See Also
    --------
    hermval2d, hermgrid2d, hermval3d, hermgrid3d

    Notes
    -----
    The evaluation uses Clenshaw recursion, aka synthetic division.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermval
    >>> coef = [1,2,3]
    >>> hermval(1, coef)
    11.0
    >>> hermval([[1,2],[3,4]], coef)
    array([[ 11.,   51.],
           [115.,  203.]])

    """
    c = np.array(c, ndmin=1, copy=None)
    if c.dtype.char in '?bBhHiIlLqQpP':
        c = c.astype(np.double)
    if isinstance(x, (tuple, list)):
        x = np.asarray(x)
    if isinstance(x, np.ndarray) and tensor:
        c = c.reshape(c.shape + (1,) * x.ndim)

    x2 = x * 2
    if len(c) == 1:
        c0 = c[0]
        c1 = 0
    elif len(c) == 2:
        c0 = c[0]
        c1 = c[1]
    else:
        nd = len(c)
        c0 = c[-2]
        c1 = c[-1]
        for i in range(3, len(c) + 1):
            tmp = c0
            nd = nd - 1
            c0 = c[-i] - c1 * (2 * (nd - 1))
            c1 = tmp + c1 * x2
    return c0 + c1 * x2


def hermval2d(x, y, c):
    """
    Evaluate a 2-D Hermite series at points (x, y).

    This function returns the values:

    .. math:: p(x,y) = \\sum_{i,j} c_{i,j} * H_i(x) * H_j(y)

    The parameters `x` and `y` are converted to arrays only if they are
    tuples or a lists, otherwise they are treated as a scalars and they
    must have the same shape after conversion. In either case, either `x`
    and `y` or their elements must support multiplication and addition both
    with themselves and with the elements of `c`.

    If `c` is a 1-D array a one is implicitly appended to its shape to make
    it 2-D. The shape of the result will be c.shape[2:] + x.shape.

    Parameters
    ----------
    x, y : array_like, compatible objects
        The two dimensional series is evaluated at the points ``(x, y)``,
        where `x` and `y` must have the same shape. If `x` or `y` is a list
        or tuple, it is first converted to an ndarray, otherwise it is left
        unchanged and if it isn't an ndarray it is treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficient of the term
        of multi-degree i,j is contained in ``c[i,j]``. If `c` has
        dimension greater than two the remaining indices enumerate multiple
        sets of coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional polynomial at points formed with
        pairs of corresponding values from `x` and `y`.

    See Also
    --------
    hermval, hermgrid2d, hermval3d, hermgrid3d

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermval2d
    >>> x = [1, 2]
    >>> y = [4, 5]
    >>> c = [[1, 2, 3], [4, 5, 6]]
    >>> hermval2d(x, y, c)
    array([1035., 2883.])

    """
    return pu._valnd(hermval, c, x, y)


def hermgrid2d(x, y, c):
    """
    Evaluate a 2-D Hermite series on the Cartesian product of x and y.

    This function returns the values:

    .. math:: p(a,b) = \\sum_{i,j} c_{i,j} * H_i(a) * H_j(b)

    where the points ``(a, b)`` consist of all pairs formed by taking
    `a` from `x` and `b` from `y`. The resulting points form a grid with
    `x` in the first dimension and `y` in the second.

    The parameters `x` and `y` are converted to arrays only if they are
    tuples or a lists, otherwise they are treated as a scalars. In either
    case, either `x` and `y` or their elements must support multiplication
    and addition both with themselves and with the elements of `c`.

    If `c` has fewer than two dimensions, ones are implicitly appended to
    its shape to make it 2-D. The shape of the result will be c.shape[2:] +
    x.shape.

    Parameters
    ----------
    x, y : array_like, compatible objects
        The two dimensional series is evaluated at the points in the
        Cartesian product of `x` and `y`.  If `x` or `y` is a list or
        tuple, it is first converted to an ndarray, otherwise it is left
        unchanged and, if it isn't an ndarray, it is treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree i,j are contained in ``c[i,j]``. If `c` has dimension
        greater than two the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional polynomial at points in the Cartesian
        product of `x` and `y`.

    See Also
    --------
    hermval, hermval2d, hermval3d, hermgrid3d

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermgrid2d
    >>> x = [1, 2, 3]
    >>> y = [4, 5]
    >>> c = [[1, 2, 3], [4, 5, 6]]
    >>> hermgrid2d(x, y, c)
    array([[1035., 1599.],
           [1867., 2883.],
           [2699., 4167.]])

    """
    return pu._gridnd(hermval, c, x, y)


def hermval3d(x, y, z, c):
    """
    Evaluate a 3-D Hermite series at points (x, y, z).

    This function returns the values:

    .. math:: p(x,y,z) = \\sum_{i,j,k} c_{i,j,k} * H_i(x) * H_j(y) * H_k(z)

    The parameters `x`, `y`, and `z` are converted to arrays only if
    they are tuples or a lists, otherwise they are treated as a scalars and
    they must have the same shape after conversion. In either case, either
    `x`, `y`, and `z` or their elements must support multiplication and
    addition both with themselves and with the elements of `c`.

    If `c` has fewer than 3 dimensions, ones are implicitly appended to its
    shape to make it 3-D. The shape of the result will be c.shape[3:] +
    x.shape.

    Parameters
    ----------
    x, y, z : array_like, compatible object
        The three dimensional series is evaluated at the points
        ``(x, y, z)``, where `x`, `y`, and `z` must have the same shape.  If
        any of `x`, `y`, or `z` is a list or tuple, it is first converted
        to an ndarray, otherwise it is left unchanged and if it isn't an
        ndarray it is  treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficient of the term of
        multi-degree i,j,k is contained in ``c[i,j,k]``. If `c` has dimension
        greater than 3 the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the multidimensional polynomial on points formed with
        triples of corresponding values from `x`, `y`, and `z`.

    See Also
    --------
    hermval, hermval2d, hermgrid2d, hermgrid3d

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermval3d
    >>> x = [1, 2]
    >>> y = [4, 5]
    >>> z = [6, 7]
    >>> c = [[[1, 2, 3], [4, 5, 6]], [[7, 8, 9], [10, 11, 12]]]
    >>> hermval3d(x, y, z, c)
    array([ 40077., 120131.])

    """
    return pu._valnd(hermval, c, x, y, z)


def hermgrid3d(x, y, z, c):
    """
    Evaluate a 3-D Hermite series on the Cartesian product of x, y, and z.

    This function returns the values:

    .. math:: p(a,b,c) = \\sum_{i,j,k} c_{i,j,k} * H_i(a) * H_j(b) * H_k(c)

    where the points ``(a, b, c)`` consist of all triples formed by taking
    `a` from `x`, `b` from `y`, and `c` from `z`. The resulting points form
    a grid with `x` in the first dimension, `y` in the second, and `z` in
    the third.

    The parameters `x`, `y`, and `z` are converted to arrays only if they
    are tuples or a lists, otherwise they are treated as a scalars. In
    either case, either `x`, `y`, and `z` or their elements must support
    multiplication and addition both with themselves and with the elements
    of `c`.

    If `c` has fewer than three dimensions, ones are implicitly appended to
    its shape to make it 3-D. The shape of the result will be c.shape[3:] +
    x.shape + y.shape + z.shape.

    Parameters
    ----------
    x, y, z : array_like, compatible objects
        The three dimensional series is evaluated at the points in the
        Cartesian product of `x`, `y`, and `z`.  If `x`, `y`, or `z` is a
        list or tuple, it is first converted to an ndarray, otherwise it is
        left unchanged and, if it isn't an ndarray, it is treated as a
        scalar.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree i,j are contained in ``c[i,j]``. If `c` has dimension
        greater than two the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional polynomial at points in the Cartesian
        product of `x` and `y`.

    See Also
    --------
    hermval, hermval2d, hermgrid2d, hermval3d

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermgrid3d
    >>> x = [1, 2]
    >>> y = [4, 5]
    >>> z = [6, 7]
    >>> c = [[[1, 2, 3], [4, 5, 6]], [[7, 8, 9], [10, 11, 12]]]
    >>> hermgrid3d(x, y, z, c)
    array([[[ 40077.,  54117.],
            [ 49293.,  66561.]],
           [[ 72375.,  97719.],
            [ 88975., 120131.]]])

    """
    return pu._gridnd(hermval, c, x, y, z)


def hermvander(x, deg):
    """Pseudo-Vandermonde matrix of given degree.

    Returns the pseudo-Vandermonde matrix of degree `deg` and sample points
    `x`. The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., i] = H_i(x),

    where ``0 <= i <= deg``. The leading indices of `V` index the elements of
    `x` and the last index is the degree of the Hermite polynomial.

    If `c` is a 1-D array of coefficients of length ``n + 1`` and `V` is the
    array ``V = hermvander(x, n)``, then ``np.dot(V, c)`` and
    ``hermval(x, c)`` are the same up to roundoff. This equivalence is
    useful both for least squares fitting and for the evaluation of a large
    number of Hermite series of the same degree and sample points.

    Parameters
    ----------
    x : array_like
        Array of points. The dtype is converted to float64 or complex128
        depending on whether any of the elements are complex. If `x` is
        scalar it is converted to a 1-D array.
    deg : int
        Degree of the resulting matrix.

    Returns
    -------
    vander : ndarray
        The pseudo-Vandermonde matrix. The shape of the returned matrix is
        ``x.shape + (deg + 1,)``, where The last index is the degree of the
        corresponding Hermite polynomial.  The dtype will be the same as
        the converted `x`.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial.hermite import hermvander
    >>> x = np.array([-1, 0, 1])
    >>> hermvander(x, 3)
    array([[ 1., -2.,  2.,  4.],
           [ 1.,  0., -2., -0.],
           [ 1.,  2.,  2., -4.]])

    """
    ideg = pu._as_int(deg, "deg")
    if ideg < 0:
        raise ValueError("deg must be non-negative")

    x = np.array(x, copy=None, ndmin=1) + 0.0
    dims = (ideg + 1,) + x.shape
    dtyp = x.dtype
    v = np.empty(dims, dtype=dtyp)
    v[0] = x * 0 + 1
    if ideg > 0:
        x2 = x * 2
        v[1] = x2
        for i in range(2, ideg + 1):
            v[i] = (v[i - 1] * x2 - v[i - 2] * (2 * (i - 1)))
    return np.moveaxis(v, 0, -1)


def hermvander2d(x, y, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points ``(x, y)``. The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., (deg[1] + 1)*i + j] = H_i(x) * H_j(y),

    where ``0 <= i <= deg[0]`` and ``0 <= j <= deg[1]``. The leading indices of
    `V` index the points ``(x, y)`` and the last index encodes the degrees of
    the Hermite polynomials.

    If ``V = hermvander2d(x, y, [xdeg, ydeg])``, then the columns of `V`
    correspond to the elements of a 2-D coefficient array `c` of shape
    (xdeg + 1, ydeg + 1) in the order

    .. math:: c_{00}, c_{01}, c_{02} ... , c_{10}, c_{11}, c_{12} ...

    and ``np.dot(V, c.flat)`` and ``hermval2d(x, y, c)`` will be the same
    up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 2-D Hermite
    series of the same degrees and sample points.

    Parameters
    ----------
    x, y : array_like
        Arrays of point coordinates, all of the same shape. The dtypes
        will be converted to either float64 or complex128 depending on
        whether any of the elements are complex. Scalars are converted to 1-D
        arrays.
    deg : list of ints
        List of maximum degrees of the form [x_deg, y_deg].

    Returns
    -------
    vander2d : ndarray
        The shape of the returned matrix is ``x.shape + (order,)``, where
        :math:`order = (deg[0]+1)*(deg[1]+1)`.  The dtype will be the same
        as the converted `x` and `y`.

    See Also
    --------
    hermvander, hermvander3d, hermval2d, hermval3d

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial.hermite import hermvander2d
    >>> x = np.array([-1, 0, 1])
    >>> y = np.array([-1, 0, 1])
    >>> hermvander2d(x, y, [2, 2])
    array([[ 1., -2.,  2., -2.,  4., -4.,  2., -4.,  4.],
           [ 1.,  0., -2.,  0.,  0., -0., -2., -0.,  4.],
           [ 1.,  2.,  2.,  2.,  4.,  4.,  2.,  4.,  4.]])

    """
    return pu._vander_nd_flat((hermvander, hermvander), (x, y), deg)


def hermvander3d(x, y, z, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points ``(x, y, z)``. If `l`, `m`, `n` are the given degrees in `x`, `y`, `z`,
    then The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., (m+1)(n+1)i + (n+1)j + k] = H_i(x)*H_j(y)*H_k(z),

    where ``0 <= i <= l``, ``0 <= j <= m``, and ``0 <= j <= n``.  The leading
    indices of `V` index the points ``(x, y, z)`` and the last index encodes
    the degrees of the Hermite polynomials.

    If ``V = hermvander3d(x, y, z, [xdeg, ydeg, zdeg])``, then the columns
    of `V` correspond to the elements of a 3-D coefficient array `c` of
    shape (xdeg + 1, ydeg + 1, zdeg + 1) in the order

    .. math:: c_{000}, c_{001}, c_{002},... , c_{010}, c_{011}, c_{012},...

    and  ``np.dot(V, c.flat)`` and ``hermval3d(x, y, z, c)`` will be the
    same up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 3-D Hermite
    series of the same degrees and sample points.

    Parameters
    ----------
    x, y, z : array_like
        Arrays of point coordinates, all of the same shape. The dtypes will
        be converted to either float64 or complex128 depending on whether
        any of the elements are complex. Scalars are converted to 1-D
        arrays.
    deg : list of ints
        List of maximum degrees of the form [x_deg, y_deg, z_deg].

    Returns
    -------
    vander3d : ndarray
        The shape of the returned matrix is ``x.shape + (order,)``, where
        :math:`order = (deg[0]+1)*(deg[1]+1)*(deg[2]+1)`.  The dtype will
        be the same as the converted `x`, `y`, and `z`.

    See Also
    --------
    hermvander, hermvander3d, hermval2d, hermval3d

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermvander3d
    >>> x = np.array([-1, 0, 1])
    >>> y = np.array([-1, 0, 1])
    >>> z = np.array([-1, 0, 1])
    >>> hermvander3d(x, y, z, [0, 1, 2])
    array([[ 1., -2.,  2., -2.,  4., -4.],
           [ 1.,  0., -2.,  0.,  0., -0.],
           [ 1.,  2.,  2.,  2.,  4.,  4.]])

    """
    return pu._vander_nd_flat((hermvander, hermvander, hermvander), (x, y, z), deg)


def hermfit(x, y, deg, rcond=None, full=False, w=None):
    """
    Least squares fit of Hermite series to data.

    Return the coefficients of a Hermite series of degree `deg` that is the
    least squares fit to the data values `y` given at points `x`. If `y` is
    1-D the returned coefficients will also be 1-D. If `y` is 2-D multiple
    fits are done, one for each column of `y`, and the resulting
    coefficients are stored in the corresponding columns of a 2-D return.
    The fitted polynomial(s) are in the form

    .. math::  p(x) = c_0 + c_1 * H_1(x) + ... + c_n * H_n(x),

    where `n` is `deg`.

    Parameters
    ----------
    x : array_like, shape (M,)
        x-coordinates of the M sample points ``(x[i], y[i])``.
    y : array_like, shape (M,) or (M, K)
        y-coordinates of the sample points. Several data sets of sample
        points sharing the same x-coordinates can be fitted at once by
        passing in a 2D-array that contains one dataset per column.
    deg : int or 1-D array_like
        Degree(s) of the fitting polynomials. If `deg` is a single integer
        all terms up to and including the `deg`'th term are included in the
        fit. For NumPy versions >= 1.11.0 a list of integers specifying the
        degrees of the terms to include may be used instead.
    rcond : float, optional
        Relative condition number of the fit. Singular values smaller than
        this relative to the largest singular value will be ignored. The
        default value is len(x)*eps, where eps is the relative precision of
        the float type, about 2e-16 in most cases.
    full : bool, optional
        Switch determining nature of return value. When it is False (the
        default) just the coefficients are returned, when True diagnostic
        information from the singular value decomposition is also returned.
    w : array_like, shape (`M`,), optional
        Weights. If not None, the weight ``w[i]`` applies to the unsquared
        residual ``y[i] - y_hat[i]`` at ``x[i]``. Ideally the weights are
        chosen so that the errors of the products ``w[i]*y[i]`` all have the
        same variance.  When using inverse-variance weighting, use
        ``w[i] = 1/sigma(y[i])``.  The default value is None.

    Returns
    -------
    coef : ndarray, shape (M,) or (M, K)
        Hermite coefficients ordered from low to high. If `y` was 2-D,
        the coefficients for the data in column k  of `y` are in column
        `k`.

    [residuals, rank, singular_values, rcond] : list
        These values are only returned if ``full == True``

        - residuals -- sum of squared residuals of the least squares fit
        - rank -- the numerical rank of the scaled Vandermonde matrix
        - singular_values -- singular values of the scaled Vandermonde matrix
        - rcond -- value of `rcond`.

        For more details, see `numpy.linalg.lstsq`.

    Warns
    -----
    RankWarning
        The rank of the coefficient matrix in the least-squares fit is
        deficient. The warning is only raised if ``full == False``.  The
        warnings can be turned off by

        >>> import warnings
        >>> warnings.simplefilter('ignore', np.exceptions.RankWarning)

    See Also
    --------
    numpy.polynomial.chebyshev.chebfit
    numpy.polynomial.legendre.legfit
    numpy.polynomial.laguerre.lagfit
    numpy.polynomial.polynomial.polyfit
    numpy.polynomial.hermite_e.hermefit
    hermval : Evaluates a Hermite series.
    hermvander : Vandermonde matrix of Hermite series.
    hermweight : Hermite weight function
    numpy.linalg.lstsq : Computes a least-squares fit from the matrix.
    scipy.interpolate.UnivariateSpline : Computes spline fits.

    Notes
    -----
    The solution is the coefficients of the Hermite series `p` that
    minimizes the sum of the weighted squared errors

    .. math:: E = \\sum_j w_j^2 * |y_j - p(x_j)|^2,

    where the :math:`w_j` are the weights. This problem is solved by
    setting up the (typically) overdetermined matrix equation

    .. math:: V(x) * c = w * y,

    where `V` is the weighted pseudo Vandermonde matrix of `x`, `c` are the
    coefficients to be solved for, `w` are the weights, `y` are the
    observed values.  This equation is then solved using the singular value
    decomposition of `V`.

    If some of the singular values of `V` are so small that they are
    neglected, then a `~exceptions.RankWarning` will be issued. This means that
    the coefficient values may be poorly determined. Using a lower order fit
    will usually get rid of the warning.  The `rcond` parameter can also be
    set to a value smaller than its default, but the resulting fit may be
    spurious and have large contributions from roundoff error.

    Fits using Hermite series are probably most useful when the data can be
    approximated by ``sqrt(w(x)) * p(x)``, where ``w(x)`` is the Hermite
    weight. In that case the weight ``sqrt(w(x[i]))`` should be used
    together with data values ``y[i]/sqrt(w(x[i]))``. The weight function is
    available as `hermweight`.

    References
    ----------
    .. [1] Wikipedia, "Curve fitting",
           https://en.wikipedia.org/wiki/Curve_fitting

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial.hermite import hermfit, hermval
    >>> x = np.linspace(-10, 10)
    >>> rng = np.random.default_rng()
    >>> err = rng.normal(scale=1./10, size=len(x))
    >>> y = hermval(x, [1, 2, 3]) + err
    >>> hermfit(x, y, 2)
    array([1.02294967, 2.00016403, 2.99994614]) # may vary

    """
    return pu._fit(hermvander, x, y, deg, rcond, full, w)


def hermcompanion(c):
    """Return the scaled companion matrix of c.

    The basis polynomials are scaled so that the companion matrix is
    symmetric when `c` is an Hermite basis polynomial. This provides
    better eigenvalue estimates than the unscaled case and for basis
    polynomials the eigenvalues are guaranteed to be real if
    `numpy.linalg.eigvalsh` is used to obtain them.

    Parameters
    ----------
    c : array_like
        1-D array of Hermite series coefficients ordered from low to high
        degree.

    Returns
    -------
    mat : ndarray
        Scaled companion matrix of dimensions (deg, deg).

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermcompanion
    >>> hermcompanion([1, 0, 1])
    array([[0.        , 0.35355339],
           [0.70710678, 0.        ]])

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    if len(c) < 2:
        raise ValueError('Series must have maximum degree of at least 1.')
    if len(c) == 2:
        return np.array([[-.5 * c[0] / c[1]]])

    n = len(c) - 1
    mat = np.zeros((n, n), dtype=c.dtype)
    scl = np.hstack((1., 1. / np.sqrt(2. * np.arange(n - 1, 0, -1))))
    scl = np.multiply.accumulate(scl)[::-1]
    top = mat.reshape(-1)[1::n + 1]
    bot = mat.reshape(-1)[n::n + 1]
    top[...] = np.sqrt(.5 * np.arange(1, n))
    bot[...] = top
    mat[:, -1] -= scl * c[:-1] / (2.0 * c[-1])
    return mat


def hermroots(c):
    """
    Compute the roots of a Hermite series.

    Return the roots (a.k.a. "zeros") of the polynomial

    .. math:: p(x) = \\sum_i c[i] * H_i(x).

    Parameters
    ----------
    c : 1-D array_like
        1-D array of coefficients.

    Returns
    -------
    out : ndarray
        Array of the roots of the series. If all the roots are real,
        then `out` is also real, otherwise it is complex.

    See Also
    --------
    numpy.polynomial.polynomial.polyroots
    numpy.polynomial.legendre.legroots
    numpy.polynomial.laguerre.lagroots
    numpy.polynomial.chebyshev.chebroots
    numpy.polynomial.hermite_e.hermeroots

    Notes
    -----
    The root estimates are obtained as the eigenvalues of the companion
    matrix, Roots far from the origin of the complex plane may have large
    errors due to the numerical instability of the series for such
    values. Roots with multiplicity greater than 1 will also show larger
    errors as the value of the series near such points is relatively
    insensitive to errors in the roots. Isolated roots near the origin can
    be improved by a few iterations of Newton's method.

    The Hermite series basis polynomials aren't powers of `x` so the
    results of this function may seem unintuitive.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermroots, hermfromroots
    >>> coef = hermfromroots([-1, 0, 1])
    >>> coef
    array([0.   ,  0.25 ,  0.   ,  0.125])
    >>> hermroots(coef)
    array([-1.00000000e+00, -1.38777878e-17,  1.00000000e+00])

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    if len(c) <= 1:
        return np.array([], dtype=c.dtype)
    if len(c) == 2:
        return np.array([-.5 * c[0] / c[1]])

    # rotated companion matrix reduces error
    m = hermcompanion(c)[::-1, ::-1]
    r = la.eigvals(m)
    r.sort()
    return r


def _normed_hermite_n(x, n):
    """
    Evaluate a normalized Hermite polynomial.

    Compute the value of the normalized Hermite polynomial of degree ``n``
    at the points ``x``.


    Parameters
    ----------
    x : ndarray of double.
        Points at which to evaluate the function
    n : int
        Degree of the normalized Hermite function to be evaluated.

    Returns
    -------
    values : ndarray
        The shape of the return value is described above.

    Notes
    -----
    This function is needed for finding the Gauss points and integration
    weights for high degrees. The values of the standard Hermite functions
    overflow when n >= 207.

    """
    if n == 0:
        return np.full(x.shape, 1 / np.sqrt(np.sqrt(np.pi)))

    c0 = 0.
    c1 = 1. / np.sqrt(np.sqrt(np.pi))
    nd = float(n)
    for i in range(n - 1):
        tmp = c0
        c0 = -c1 * np.sqrt((nd - 1.) / nd)
        c1 = tmp + c1 * x * np.sqrt(2. / nd)
        nd = nd - 1.0
    return c0 + c1 * x * np.sqrt(2)


def hermgauss(deg):
    """
    Gauss-Hermite quadrature.

    Computes the sample points and weights for Gauss-Hermite quadrature.
    These sample points and weights will correctly integrate polynomials of
    degree :math:`2*deg - 1` or less over the interval :math:`[-\\inf, \\inf]`
    with the weight function :math:`f(x) = \\exp(-x^2)`.

    Parameters
    ----------
    deg : int
        Number of sample points and weights. It must be >= 1.

    Returns
    -------
    x : ndarray
        1-D ndarray containing the sample points.
    y : ndarray
        1-D ndarray containing the weights.

    Notes
    -----
    The results have only been tested up to degree 100, higher degrees may
    be problematic. The weights are determined by using the fact that

    .. math:: w_k = c / (H'_n(x_k) * H_{n-1}(x_k))

    where :math:`c` is a constant independent of :math:`k` and :math:`x_k`
    is the k'th root of :math:`H_n`, and then scaling the results to get
    the right value when integrating 1.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermgauss
    >>> hermgauss(2)
    (array([-0.70710678,  0.70710678]), array([0.88622693, 0.88622693]))

    """
    ideg = pu._as_int(deg, "deg")
    if ideg <= 0:
        raise ValueError("deg must be a positive integer")

    # first approximation of roots. We use the fact that the companion
    # matrix is symmetric in this case in order to obtain better zeros.
    c = np.array([0] * deg + [1], dtype=np.float64)
    m = hermcompanion(c)
    x = la.eigvalsh(m)

    # improve roots by one application of Newton
    dy = _normed_hermite_n(x, ideg)
    df = _normed_hermite_n(x, ideg - 1) * np.sqrt(2 * ideg)
    x -= dy / df

    # compute the weights. We scale the factor to avoid possible numerical
    # overflow.
    fm = _normed_hermite_n(x, ideg - 1)
    fm /= np.abs(fm).max()
    w = 1 / (fm * fm)

    # for Hermite we can also symmetrize
    w = (w + w[::-1]) / 2
    x = (x - x[::-1]) / 2

    # scale w to get the right value
    w *= np.sqrt(np.pi) / w.sum()

    return x, w


def hermweight(x):
    """
    Weight function of the Hermite polynomials.

    The weight function is :math:`\\exp(-x^2)` and the interval of
    integration is :math:`[-\\inf, \\inf]`. the Hermite polynomials are
    orthogonal, but not normalized, with respect to this weight function.

    Parameters
    ----------
    x : array_like
       Values at which the weight function will be computed.

    Returns
    -------
    w : ndarray
       The weight function at `x`.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial.hermite import hermweight
    >>> x = np.arange(-2, 2)
    >>> hermweight(x)
    array([0.01831564, 0.36787944, 1.        , 0.36787944])

    """
    w = np.exp(-x**2)
    return w


#
# Hermite series class
#

class Hermite(ABCPolyBase):
    """An Hermite series class.

    The Hermite class provides the standard Python numerical methods
    '+', '-', '*', '//', '%', 'divmod', '**', and '()' as well as the
    attributes and methods listed below.

    Parameters
    ----------
    coef : array_like
        Hermite coefficients in order of increasing degree, i.e,
        ``(1, 2, 3)`` gives ``1*H_0(x) + 2*H_1(x) + 3*H_2(x)``.
    domain : (2,) array_like, optional
        Domain to use. The interval ``[domain[0], domain[1]]`` is mapped
        to the interval ``[window[0], window[1]]`` by shifting and scaling.
        The default value is [-1., 1.].
    window : (2,) array_like, optional
        Window, see `domain` for its use. The default value is [-1., 1.].
    symbol : str, optional
        Symbol used to represent the independent variable in string
        representations of the polynomial expression, e.g. for printing.
        The symbol must be a valid Python identifier. Default value is 'x'.

        .. versionadded:: 1.24

    """
    # Virtual Functions
    _add = staticmethod(hermadd)
    _sub = staticmethod(hermsub)
    _mul = staticmethod(hermmul)
    _div = staticmethod(hermdiv)
    _pow = staticmethod(hermpow)
    _val = staticmethod(hermval)
    _int = staticmethod(hermint)
    _der = staticmethod(hermder)
    _fit = staticmethod(hermfit)
    _line = staticmethod(hermline)
    _roots = staticmethod(hermroots)
    _fromroots = staticmethod(hermfromroots)

    # Virtual properties
    domain = np.array(hermdomain)
    window = np.array(hermdomain)
    basis_name = 'H'