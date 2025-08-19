
# === NexusCore/tools\exports\NexusCore_export_20250803_131253\combined_35.py ===

# === NexusCore/tools\exports\export_20250803_114325\combined_26.py ===

# === NexusCore/openenv\Lib\site-packages\pydantic_core\core_schema.py ===
"""
This module contains definitions to build schemas which `pydantic_core` can
validate and serialize.
"""

from __future__ import annotations as _annotations

import sys
import warnings
from collections.abc import Hashable, Mapping
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from re import Pattern
from typing import TYPE_CHECKING, Any, Callable, Literal, Union

from typing_extensions import deprecated

if sys.version_info < (3, 12):
    from typing_extensions import TypedDict
else:
    from typing import TypedDict

if sys.version_info < (3, 11):
    from typing_extensions import Protocol, Required, TypeAlias
else:
    from typing import Protocol, Required, TypeAlias

if TYPE_CHECKING:
    from pydantic_core import PydanticUndefined
else:
    # The initial build of pydantic_core requires PydanticUndefined to generate
    # the core schema; so we need to conditionally skip it. mypy doesn't like
    # this at all, hence the TYPE_CHECKING branch above.
    try:
        from pydantic_core import PydanticUndefined
    except ImportError:
        PydanticUndefined = object()


ExtraBehavior = Literal['allow', 'forbid', 'ignore']


class CoreConfig(TypedDict, total=False):
    """
    Base class for schema configuration options.

    Attributes:
        title: The name of the configuration.
        strict: Whether the configuration should strictly adhere to specified rules.
        extra_fields_behavior: The behavior for handling extra fields.
        typed_dict_total: Whether the TypedDict should be considered total. Default is `True`.
        from_attributes: Whether to use attributes for models, dataclasses, and tagged union keys.
        loc_by_alias: Whether to use the used alias (or first alias for "field required" errors) instead of
            `field_names` to construct error `loc`s. Default is `True`.
        revalidate_instances: Whether instances of models and dataclasses should re-validate. Default is 'never'.
        validate_default: Whether to validate default values during validation. Default is `False`.
        str_max_length: The maximum length for string fields.
        str_min_length: The minimum length for string fields.
        str_strip_whitespace: Whether to strip whitespace from string fields.
        str_to_lower: Whether to convert string fields to lowercase.
        str_to_upper: Whether to convert string fields to uppercase.
        allow_inf_nan: Whether to allow infinity and NaN values for float fields. Default is `True`.
        ser_json_timedelta: The serialization option for `timedelta` values. Default is 'iso8601'.
        ser_json_bytes: The serialization option for `bytes` values. Default is 'utf8'.
        ser_json_inf_nan: The serialization option for infinity and NaN values
            in float fields. Default is 'null'.
        val_json_bytes: The validation option for `bytes` values, complementing ser_json_bytes. Default is 'utf8'.
        hide_input_in_errors: Whether to hide input data from `ValidationError` representation.
        validation_error_cause: Whether to add user-python excs to the __cause__ of a ValidationError.
            Requires exceptiongroup backport pre Python 3.11.
        coerce_numbers_to_str: Whether to enable coercion of any `Number` type to `str` (not applicable in `strict` mode).
        regex_engine: The regex engine to use for regex pattern validation. Default is 'rust-regex'. See `StringSchema`.
        cache_strings: Whether to cache strings. Default is `True`, `True` or `'all'` is required to cache strings
            during general validation since validators don't know if they're in a key or a value.
        validate_by_alias: Whether to use the field's alias when validating against the provided input data. Default is `True`.
        validate_by_name: Whether to use the field's name when validating against the provided input data. Default is `False`. Replacement for `populate_by_name`.
        serialize_by_alias: Whether to serialize by alias. Default is `False`, expected to change to `True` in V3.
    """

    title: str
    strict: bool
    # settings related to typed dicts, model fields, dataclass fields
    extra_fields_behavior: ExtraBehavior
    typed_dict_total: bool  # default: True
    # used for models, dataclasses, and tagged union keys
    from_attributes: bool
    # whether to use the used alias (or first alias for "field required" errors) instead of field_names
    # to construct error `loc`s, default True
    loc_by_alias: bool
    # whether instances of models and dataclasses (including subclass instances) should re-validate, default 'never'
    revalidate_instances: Literal['always', 'never', 'subclass-instances']
    # whether to validate default values during validation, default False
    validate_default: bool
    # used on typed-dicts and arguments
    # fields related to string fields only
    str_max_length: int
    str_min_length: int
    str_strip_whitespace: bool
    str_to_lower: bool
    str_to_upper: bool
    # fields related to float fields only
    allow_inf_nan: bool  # default: True
    # the config options are used to customise serialization to JSON
    ser_json_timedelta: Literal['iso8601', 'float']  # default: 'iso8601'
    ser_json_bytes: Literal['utf8', 'base64', 'hex']  # default: 'utf8'
    ser_json_inf_nan: Literal['null', 'constants', 'strings']  # default: 'null'
    val_json_bytes: Literal['utf8', 'base64', 'hex']  # default: 'utf8'
    # used to hide input data from ValidationError repr
    hide_input_in_errors: bool
    validation_error_cause: bool  # default: False
    coerce_numbers_to_str: bool  # default: False
    regex_engine: Literal['rust-regex', 'python-re']  # default: 'rust-regex'
    cache_strings: Union[bool, Literal['all', 'keys', 'none']]  # default: 'True'
    validate_by_alias: bool  # default: True
    validate_by_name: bool  # default: False
    serialize_by_alias: bool  # default: False


IncExCall: TypeAlias = 'set[int | str] | dict[int | str, IncExCall] | None'


class SerializationInfo(Protocol):
    @property
    def include(self) -> IncExCall: ...

    @property
    def exclude(self) -> IncExCall: ...

    @property
    def context(self) -> Any | None:
        """Current serialization context."""

    @property
    def mode(self) -> str: ...

    @property
    def by_alias(self) -> bool: ...

    @property
    def exclude_unset(self) -> bool: ...

    @property
    def exclude_defaults(self) -> bool: ...

    @property
    def exclude_none(self) -> bool: ...

    @property
    def serialize_as_any(self) -> bool: ...

    @property
    def round_trip(self) -> bool: ...

    def mode_is_json(self) -> bool: ...

    def __str__(self) -> str: ...

    def __repr__(self) -> str: ...


class FieldSerializationInfo(SerializationInfo, Protocol):
    @property
    def field_name(self) -> str: ...


class ValidationInfo(Protocol):
    """
    Argument passed to validation functions.
    """

    @property
    def context(self) -> Any | None:
        """Current validation context."""
        ...

    @property
    def config(self) -> CoreConfig | None:
        """The CoreConfig that applies to this validation."""
        ...

    @property
    def mode(self) -> Literal['python', 'json']:
        """The type of input data we are currently validating"""
        ...

    @property
    def data(self) -> dict[str, Any]:
        """The data being validated for this model."""
        ...

    @property
    def field_name(self) -> str | None:
        """
        The name of the current field being validated if this validator is
        attached to a model field.
        """
        ...


ExpectedSerializationTypes = Literal[
    'none',
    'int',
    'bool',
    'float',
    'str',
    'bytes',
    'bytearray',
    'list',
    'tuple',
    'set',
    'frozenset',
    'generator',
    'dict',
    'datetime',
    'date',
    'time',
    'timedelta',
    'url',
    'multi-host-url',
    'json',
    'uuid',
    'any',
]


class SimpleSerSchema(TypedDict, total=False):
    type: Required[ExpectedSerializationTypes]


def simple_ser_schema(type: ExpectedSerializationTypes) -> SimpleSerSchema:
    """
    Returns a schema for serialization with a custom type.

    Args:
        type: The type to use for serialization
    """
    return SimpleSerSchema(type=type)


# (input_value: Any, /) -> Any
GeneralPlainNoInfoSerializerFunction = Callable[[Any], Any]
# (input_value: Any, info: FieldSerializationInfo, /) -> Any
GeneralPlainInfoSerializerFunction = Callable[[Any, SerializationInfo], Any]
# (model: Any, input_value: Any, /) -> Any
FieldPlainNoInfoSerializerFunction = Callable[[Any, Any], Any]
# (model: Any, input_value: Any, info: FieldSerializationInfo, /) -> Any
FieldPlainInfoSerializerFunction = Callable[[Any, Any, FieldSerializationInfo], Any]
SerializerFunction = Union[
    GeneralPlainNoInfoSerializerFunction,
    GeneralPlainInfoSerializerFunction,
    FieldPlainNoInfoSerializerFunction,
    FieldPlainInfoSerializerFunction,
]

WhenUsed = Literal['always', 'unless-none', 'json', 'json-unless-none']
"""
Values have the following meanings:

* `'always'` means always use
* `'unless-none'` means use unless the value is `None`
* `'json'` means use when serializing to JSON
* `'json-unless-none'` means use when serializing to JSON and the value is not `None`
"""


class PlainSerializerFunctionSerSchema(TypedDict, total=False):
    type: Required[Literal['function-plain']]
    function: Required[SerializerFunction]
    is_field_serializer: bool  # default False
    info_arg: bool  # default False
    return_schema: CoreSchema  # if omitted, AnySchema is used
    when_used: WhenUsed  # default: 'always'


def plain_serializer_function_ser_schema(
    function: SerializerFunction,
    *,
    is_field_serializer: bool | None = None,
    info_arg: bool | None = None,
    return_schema: CoreSchema | None = None,
    when_used: WhenUsed = 'always',
) -> PlainSerializerFunctionSerSchema:
    """
    Returns a schema for serialization with a function, can be either a "general" or "field" function.

    Args:
        function: The function to use for serialization
        is_field_serializer: Whether the serializer is for a field, e.g. takes `model` as the first argument,
            and `info` includes `field_name`
        info_arg: Whether the function takes an `info` argument
        return_schema: Schema to use for serializing return value
        when_used: When the function should be called
    """
    if when_used == 'always':
        # just to avoid extra elements in schema, and to use the actual default defined in rust
        when_used = None  # type: ignore
    return _dict_not_none(
        type='function-plain',
        function=function,
        is_field_serializer=is_field_serializer,
        info_arg=info_arg,
        return_schema=return_schema,
        when_used=when_used,
    )


class SerializerFunctionWrapHandler(Protocol):  # pragma: no cover
    def __call__(self, input_value: Any, index_key: int | str | None = None, /) -> Any: ...


# (input_value: Any, serializer: SerializerFunctionWrapHandler, /) -> Any
GeneralWrapNoInfoSerializerFunction = Callable[[Any, SerializerFunctionWrapHandler], Any]
# (input_value: Any, serializer: SerializerFunctionWrapHandler, info: SerializationInfo, /) -> Any
GeneralWrapInfoSerializerFunction = Callable[[Any, SerializerFunctionWrapHandler, SerializationInfo], Any]
# (model: Any, input_value: Any, serializer: SerializerFunctionWrapHandler, /) -> Any
FieldWrapNoInfoSerializerFunction = Callable[[Any, Any, SerializerFunctionWrapHandler], Any]
# (model: Any, input_value: Any, serializer: SerializerFunctionWrapHandler, info: FieldSerializationInfo, /) -> Any
FieldWrapInfoSerializerFunction = Callable[[Any, Any, SerializerFunctionWrapHandler, FieldSerializationInfo], Any]
WrapSerializerFunction = Union[
    GeneralWrapNoInfoSerializerFunction,
    GeneralWrapInfoSerializerFunction,
    FieldWrapNoInfoSerializerFunction,
    FieldWrapInfoSerializerFunction,
]


class WrapSerializerFunctionSerSchema(TypedDict, total=False):
    type: Required[Literal['function-wrap']]
    function: Required[WrapSerializerFunction]
    is_field_serializer: bool  # default False
    info_arg: bool  # default False
    schema: CoreSchema  # if omitted, the schema on which this serializer is defined is used
    return_schema: CoreSchema  # if omitted, AnySchema is used
    when_used: WhenUsed  # default: 'always'


def wrap_serializer_function_ser_schema(
    function: WrapSerializerFunction,
    *,
    is_field_serializer: bool | None = None,
    info_arg: bool | None = None,
    schema: CoreSchema | None = None,
    return_schema: CoreSchema | None = None,
    when_used: WhenUsed = 'always',
) -> WrapSerializerFunctionSerSchema:
    """
    Returns a schema for serialization with a wrap function, can be either a "general" or "field" function.

    Args:
        function: The function to use for serialization
        is_field_serializer: Whether the serializer is for a field, e.g. takes `model` as the first argument,
            and `info` includes `field_name`
        info_arg: Whether the function takes an `info` argument
        schema: The schema to use for the inner serialization
        return_schema: Schema to use for serializing return value
        when_used: When the function should be called
    """
    if when_used == 'always':
        # just to avoid extra elements in schema, and to use the actual default defined in rust
        when_used = None  # type: ignore
    return _dict_not_none(
        type='function-wrap',
        function=function,
        is_field_serializer=is_field_serializer,
        info_arg=info_arg,
        schema=schema,
        return_schema=return_schema,
        when_used=when_used,
    )


class FormatSerSchema(TypedDict, total=False):
    type: Required[Literal['format']]
    formatting_string: Required[str]
    when_used: WhenUsed  # default: 'json-unless-none'


def format_ser_schema(formatting_string: str, *, when_used: WhenUsed = 'json-unless-none') -> FormatSerSchema:
    """
    Returns a schema for serialization using python's `format` method.

    Args:
        formatting_string: String defining the format to use
        when_used: Same meaning as for [general_function_plain_ser_schema], but with a different default
    """
    if when_used == 'json-unless-none':
        # just to avoid extra elements in schema, and to use the actual default defined in rust
        when_used = None  # type: ignore
    return _dict_not_none(type='format', formatting_string=formatting_string, when_used=when_used)


class ToStringSerSchema(TypedDict, total=False):
    type: Required[Literal['to-string']]
    when_used: WhenUsed  # default: 'json-unless-none'


def to_string_ser_schema(*, when_used: WhenUsed = 'json-unless-none') -> ToStringSerSchema:
    """
    Returns a schema for serialization using python's `str()` / `__str__` method.

    Args:
        when_used: Same meaning as for [general_function_plain_ser_schema], but with a different default
    """
    s = dict(type='to-string')
    if when_used != 'json-unless-none':
        # just to avoid extra elements in schema, and to use the actual default defined in rust
        s['when_used'] = when_used
    return s  # type: ignore


class ModelSerSchema(TypedDict, total=False):
    type: Required[Literal['model']]
    cls: Required[type[Any]]
    schema: Required[CoreSchema]


def model_ser_schema(cls: type[Any], schema: CoreSchema) -> ModelSerSchema:
    """
    Returns a schema for serialization using a model.

    Args:
        cls: The expected class type, used to generate warnings if the wrong type is passed
        schema: Internal schema to use to serialize the model dict
    """
    return ModelSerSchema(type='model', cls=cls, schema=schema)


SerSchema = Union[
    SimpleSerSchema,
    PlainSerializerFunctionSerSchema,
    WrapSerializerFunctionSerSchema,
    FormatSerSchema,
    ToStringSerSchema,
    ModelSerSchema,
]


class InvalidSchema(TypedDict, total=False):
    type: Required[Literal['invalid']]
    ref: str
    metadata: dict[str, Any]
    # note, we never plan to use this, but include it for type checking purposes to match
    # all other CoreSchema union members
    serialization: SerSchema


def invalid_schema(ref: str | None = None, metadata: dict[str, Any] | None = None) -> InvalidSchema:
    """
    Returns an invalid schema, used to indicate that a schema is invalid.

        Returns a schema that matches any value, e.g.:

    Args:
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
    """

    return _dict_not_none(type='invalid', ref=ref, metadata=metadata)


class ComputedField(TypedDict, total=False):
    type: Required[Literal['computed-field']]
    property_name: Required[str]
    return_schema: Required[CoreSchema]
    alias: str
    metadata: dict[str, Any]


def computed_field(
    property_name: str, return_schema: CoreSchema, *, alias: str | None = None, metadata: dict[str, Any] | None = None
) -> ComputedField:
    """
    ComputedFields are properties of a model or dataclass that are included in serialization.

    Args:
        property_name: The name of the property on the model or dataclass
        return_schema: The schema used for the type returned by the computed field
        alias: The name to use in the serialized output
        metadata: Any other information you want to include with the schema, not used by pydantic-core
    """
    return _dict_not_none(
        type='computed-field', property_name=property_name, return_schema=return_schema, alias=alias, metadata=metadata
    )


class AnySchema(TypedDict, total=False):
    type: Required[Literal['any']]
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def any_schema(
    *, ref: str | None = None, metadata: dict[str, Any] | None = None, serialization: SerSchema | None = None
) -> AnySchema:
    """
    Returns a schema that matches any value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.any_schema()
    v = SchemaValidator(schema)
    assert v.validate_python(1) == 1
    ```

    Args:
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(type='any', ref=ref, metadata=metadata, serialization=serialization)


class NoneSchema(TypedDict, total=False):
    type: Required[Literal['none']]
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def none_schema(
    *, ref: str | None = None, metadata: dict[str, Any] | None = None, serialization: SerSchema | None = None
) -> NoneSchema:
    """
    Returns a schema that matches a None value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.none_schema()
    v = SchemaValidator(schema)
    assert v.validate_python(None) is None
    ```

    Args:
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(type='none', ref=ref, metadata=metadata, serialization=serialization)


class BoolSchema(TypedDict, total=False):
    type: Required[Literal['bool']]
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def bool_schema(
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> BoolSchema:
    """
    Returns a schema that matches a bool value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.bool_schema()
    v = SchemaValidator(schema)
    assert v.validate_python('True') is True
    ```

    Args:
        strict: Whether the value should be a bool or a value that can be converted to a bool
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(type='bool', strict=strict, ref=ref, metadata=metadata, serialization=serialization)


class IntSchema(TypedDict, total=False):
    type: Required[Literal['int']]
    multiple_of: int
    le: int
    ge: int
    lt: int
    gt: int
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def int_schema(
    *,
    multiple_of: int | None = None,
    le: int | None = None,
    ge: int | None = None,
    lt: int | None = None,
    gt: int | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> IntSchema:
    """
    Returns a schema that matches a int value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.int_schema(multiple_of=2, le=6, ge=2)
    v = SchemaValidator(schema)
    assert v.validate_python('4') == 4
    ```

    Args:
        multiple_of: The value must be a multiple of this number
        le: The value must be less than or equal to this number
        ge: The value must be greater than or equal to this number
        lt: The value must be strictly less than this number
        gt: The value must be strictly greater than this number
        strict: Whether the value should be a int or a value that can be converted to a int
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='int',
        multiple_of=multiple_of,
        le=le,
        ge=ge,
        lt=lt,
        gt=gt,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class FloatSchema(TypedDict, total=False):
    type: Required[Literal['float']]
    allow_inf_nan: bool  # whether 'NaN', '+inf', '-inf' should be forbidden. default: True
    multiple_of: float
    le: float
    ge: float
    lt: float
    gt: float
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def float_schema(
    *,
    allow_inf_nan: bool | None = None,
    multiple_of: float | None = None,
    le: float | None = None,
    ge: float | None = None,
    lt: float | None = None,
    gt: float | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> FloatSchema:
    """
    Returns a schema that matches a float value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.float_schema(le=0.8, ge=0.2)
    v = SchemaValidator(schema)
    assert v.validate_python('0.5') == 0.5
    ```

    Args:
        allow_inf_nan: Whether to allow inf and nan values
        multiple_of: The value must be a multiple of this number
        le: The value must be less than or equal to this number
        ge: The value must be greater than or equal to this number
        lt: The value must be strictly less than this number
        gt: The value must be strictly greater than this number
        strict: Whether the value should be a float or a value that can be converted to a float
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='float',
        allow_inf_nan=allow_inf_nan,
        multiple_of=multiple_of,
        le=le,
        ge=ge,
        lt=lt,
        gt=gt,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class DecimalSchema(TypedDict, total=False):
    type: Required[Literal['decimal']]
    allow_inf_nan: bool  # whether 'NaN', '+inf', '-inf' should be forbidden. default: False
    multiple_of: Decimal
    le: Decimal
    ge: Decimal
    lt: Decimal
    gt: Decimal
    max_digits: int
    decimal_places: int
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def decimal_schema(
    *,
    allow_inf_nan: bool | None = None,
    multiple_of: Decimal | None = None,
    le: Decimal | None = None,
    ge: Decimal | None = None,
    lt: Decimal | None = None,
    gt: Decimal | None = None,
    max_digits: int | None = None,
    decimal_places: int | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> DecimalSchema:
    """
    Returns a schema that matches a decimal value, e.g.:

    ```py
    from decimal import Decimal
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.decimal_schema(le=0.8, ge=0.2)
    v = SchemaValidator(schema)
    assert v.validate_python('0.5') == Decimal('0.5')
    ```

    Args:
        allow_inf_nan: Whether to allow inf and nan values
        multiple_of: The value must be a multiple of this number
        le: The value must be less than or equal to this number
        ge: The value must be greater than or equal to this number
        lt: The value must be strictly less than this number
        gt: The value must be strictly greater than this number
        max_digits: The maximum number of decimal digits allowed
        decimal_places: The maximum number of decimal places allowed
        strict: Whether the value should be a float or a value that can be converted to a float
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='decimal',
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        max_digits=max_digits,
        decimal_places=decimal_places,
        multiple_of=multiple_of,
        allow_inf_nan=allow_inf_nan,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class ComplexSchema(TypedDict, total=False):
    type: Required[Literal['complex']]
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def complex_schema(
    *,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> ComplexSchema:
    """
    Returns a schema that matches a complex value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.complex_schema()
    v = SchemaValidator(schema)
    assert v.validate_python('1+2j') == complex(1, 2)
    assert v.validate_python(complex(1, 2)) == complex(1, 2)
    ```

    Args:
        strict: Whether the value should be a complex object instance or a value that can be converted to a complex object
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='complex',
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class StringSchema(TypedDict, total=False):
    type: Required[Literal['str']]
    pattern: Union[str, Pattern[str]]
    max_length: int
    min_length: int
    strip_whitespace: bool
    to_lower: bool
    to_upper: bool
    regex_engine: Literal['rust-regex', 'python-re']  # default: 'rust-regex'
    strict: bool
    coerce_numbers_to_str: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def str_schema(
    *,
    pattern: str | Pattern[str] | None = None,
    max_length: int | None = None,
    min_length: int | None = None,
    strip_whitespace: bool | None = None,
    to_lower: bool | None = None,
    to_upper: bool | None = None,
    regex_engine: Literal['rust-regex', 'python-re'] | None = None,
    strict: bool | None = None,
    coerce_numbers_to_str: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> StringSchema:
    """
    Returns a schema that matches a string value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.str_schema(max_length=10, min_length=2)
    v = SchemaValidator(schema)
    assert v.validate_python('hello') == 'hello'
    ```

    Args:
        pattern: A regex pattern that the value must match
        max_length: The value must be at most this length
        min_length: The value must be at least this length
        strip_whitespace: Whether to strip whitespace from the value
        to_lower: Whether to convert the value to lowercase
        to_upper: Whether to convert the value to uppercase
        regex_engine: The regex engine to use for pattern validation. Default is 'rust-regex'.
            - `rust-regex` uses the [`regex`](https://docs.rs/regex) Rust
              crate, which is non-backtracking and therefore more DDoS
              resistant, but does not support all regex features.
            - `python-re` use the [`re`](https://docs.python.org/3/library/re.html) module,
              which supports all regex features, but may be slower.
        strict: Whether the value should be a string or a value that can be converted to a string
        coerce_numbers_to_str: Whether to enable coercion of any `Number` type to `str` (not applicable in `strict` mode).
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='str',
        pattern=pattern,
        max_length=max_length,
        min_length=min_length,
        strip_whitespace=strip_whitespace,
        to_lower=to_lower,
        to_upper=to_upper,
        regex_engine=regex_engine,
        strict=strict,
        coerce_numbers_to_str=coerce_numbers_to_str,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class BytesSchema(TypedDict, total=False):
    type: Required[Literal['bytes']]
    max_length: int
    min_length: int
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def bytes_schema(
    *,
    max_length: int | None = None,
    min_length: int | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> BytesSchema:
    """
    Returns a schema that matches a bytes value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.bytes_schema(max_length=10, min_length=2)
    v = SchemaValidator(schema)
    assert v.validate_python(b'hello') == b'hello'
    ```

    Args:
        max_length: The value must be at most this length
        min_length: The value must be at least this length
        strict: Whether the value should be a bytes or a value that can be converted to a bytes
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='bytes',
        max_length=max_length,
        min_length=min_length,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class DateSchema(TypedDict, total=False):
    type: Required[Literal['date']]
    strict: bool
    le: date
    ge: date
    lt: date
    gt: date
    now_op: Literal['past', 'future']
    # defaults to current local utc offset from `time.localtime().tm_gmtoff`
    # value is restricted to -86_400 < offset < 86_400 by bounds in generate_self_schema.py
    now_utc_offset: int
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def date_schema(
    *,
    strict: bool | None = None,
    le: date | None = None,
    ge: date | None = None,
    lt: date | None = None,
    gt: date | None = None,
    now_op: Literal['past', 'future'] | None = None,
    now_utc_offset: int | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> DateSchema:
    """
    Returns a schema that matches a date value, e.g.:

    ```py
    from datetime import date
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.date_schema(le=date(2020, 1, 1), ge=date(2019, 1, 1))
    v = SchemaValidator(schema)
    assert v.validate_python(date(2019, 6, 1)) == date(2019, 6, 1)
    ```

    Args:
        strict: Whether the value should be a date or a value that can be converted to a date
        le: The value must be less than or equal to this date
        ge: The value must be greater than or equal to this date
        lt: The value must be strictly less than this date
        gt: The value must be strictly greater than this date
        now_op: The value must be in the past or future relative to the current date
        now_utc_offset: The value must be in the past or future relative to the current date with this utc offset
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='date',
        strict=strict,
        le=le,
        ge=ge,
        lt=lt,
        gt=gt,
        now_op=now_op,
        now_utc_offset=now_utc_offset,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class TimeSchema(TypedDict, total=False):
    type: Required[Literal['time']]
    strict: bool
    le: time
    ge: time
    lt: time
    gt: time
    tz_constraint: Union[Literal['aware', 'naive'], int]
    microseconds_precision: Literal['truncate', 'error']
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def time_schema(
    *,
    strict: bool | None = None,
    le: time | None = None,
    ge: time | None = None,
    lt: time | None = None,
    gt: time | None = None,
    tz_constraint: Literal['aware', 'naive'] | int | None = None,
    microseconds_precision: Literal['truncate', 'error'] = 'truncate',
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> TimeSchema:
    """
    Returns a schema that matches a time value, e.g.:

    ```py
    from datetime import time
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.time_schema(le=time(12, 0, 0), ge=time(6, 0, 0))
    v = SchemaValidator(schema)
    assert v.validate_python(time(9, 0, 0)) == time(9, 0, 0)
    ```

    Args:
        strict: Whether the value should be a time or a value that can be converted to a time
        le: The value must be less than or equal to this time
        ge: The value must be greater than or equal to this time
        lt: The value must be strictly less than this time
        gt: The value must be strictly greater than this time
        tz_constraint: The value must be timezone aware or naive, or an int to indicate required tz offset
        microseconds_precision: The behavior when seconds have more than 6 digits or microseconds is too large
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='time',
        strict=strict,
        le=le,
        ge=ge,
        lt=lt,
        gt=gt,
        tz_constraint=tz_constraint,
        microseconds_precision=microseconds_precision,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class DatetimeSchema(TypedDict, total=False):
    type: Required[Literal['datetime']]
    strict: bool
    le: datetime
    ge: datetime
    lt: datetime
    gt: datetime
    now_op: Literal['past', 'future']
    tz_constraint: Union[Literal['aware', 'naive'], int]
    # defaults to current local utc offset from `time.localtime().tm_gmtoff`
    # value is restricted to -86_400 < offset < 86_400 by bounds in generate_self_schema.py
    now_utc_offset: int
    microseconds_precision: Literal['truncate', 'error']  # default: 'truncate'
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def datetime_schema(
    *,
    strict: bool | None = None,
    le: datetime | None = None,
    ge: datetime | None = None,
    lt: datetime | None = None,
    gt: datetime | None = None,
    now_op: Literal['past', 'future'] | None = None,
    tz_constraint: Literal['aware', 'naive'] | int | None = None,
    now_utc_offset: int | None = None,
    microseconds_precision: Literal['truncate', 'error'] = 'truncate',
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> DatetimeSchema:
    """
    Returns a schema that matches a datetime value, e.g.:

    ```py
    from datetime import datetime
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.datetime_schema()
    v = SchemaValidator(schema)
    now = datetime.now()
    assert v.validate_python(str(now)) == now
    ```

    Args:
        strict: Whether the value should be a datetime or a value that can be converted to a datetime
        le: The value must be less than or equal to this datetime
        ge: The value must be greater than or equal to this datetime
        lt: The value must be strictly less than this datetime
        gt: The value must be strictly greater than this datetime
        now_op: The value must be in the past or future relative to the current datetime
        tz_constraint: The value must be timezone aware or naive, or an int to indicate required tz offset
            TODO: use of a tzinfo where offset changes based on the datetime is not yet supported
        now_utc_offset: The value must be in the past or future relative to the current datetime with this utc offset
        microseconds_precision: The behavior when seconds have more than 6 digits or microseconds is too large
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='datetime',
        strict=strict,
        le=le,
        ge=ge,
        lt=lt,
        gt=gt,
        now_op=now_op,
        tz_constraint=tz_constraint,
        now_utc_offset=now_utc_offset,
        microseconds_precision=microseconds_precision,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class TimedeltaSchema(TypedDict, total=False):
    type: Required[Literal['timedelta']]
    strict: bool
    le: timedelta
    ge: timedelta
    lt: timedelta
    gt: timedelta
    microseconds_precision: Literal['truncate', 'error']
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def timedelta_schema(
    *,
    strict: bool | None = None,
    le: timedelta | None = None,
    ge: timedelta | None = None,
    lt: timedelta | None = None,
    gt: timedelta | None = None,
    microseconds_precision: Literal['truncate', 'error'] = 'truncate',
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> TimedeltaSchema:
    """
    Returns a schema that matches a timedelta value, e.g.:

    ```py
    from datetime import timedelta
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.timedelta_schema(le=timedelta(days=1), ge=timedelta(days=0))
    v = SchemaValidator(schema)
    assert v.validate_python(timedelta(hours=12)) == timedelta(hours=12)
    ```

    Args:
        strict: Whether the value should be a timedelta or a value that can be converted to a timedelta
        le: The value must be less than or equal to this timedelta
        ge: The value must be greater than or equal to this timedelta
        lt: The value must be strictly less than this timedelta
        gt: The value must be strictly greater than this timedelta
        microseconds_precision: The behavior when seconds have more than 6 digits or microseconds is too large
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='timedelta',
        strict=strict,
        le=le,
        ge=ge,
        lt=lt,
        gt=gt,
        microseconds_precision=microseconds_precision,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class LiteralSchema(TypedDict, total=False):
    type: Required[Literal['literal']]
    expected: Required[list[Any]]
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def literal_schema(
    expected: list[Any],
    *,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> LiteralSchema:
    """
    Returns a schema that matches a literal value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.literal_schema(['hello', 'world'])
    v = SchemaValidator(schema)
    assert v.validate_python('hello') == 'hello'
    ```

    Args:
        expected: The value must be one of these values
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(type='literal', expected=expected, ref=ref, metadata=metadata, serialization=serialization)


class EnumSchema(TypedDict, total=False):
    type: Required[Literal['enum']]
    cls: Required[Any]
    members: Required[list[Any]]
    sub_type: Literal['str', 'int', 'float']
    missing: Callable[[Any], Any]
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def enum_schema(
    cls: Any,
    members: list[Any],
    *,
    sub_type: Literal['str', 'int', 'float'] | None = None,
    missing: Callable[[Any], Any] | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> EnumSchema:
    """
    Returns a schema that matches an enum value, e.g.:

    ```py
    from enum import Enum
    from pydantic_core import SchemaValidator, core_schema

    class Color(Enum):
        RED = 1
        GREEN = 2
        BLUE = 3

    schema = core_schema.enum_schema(Color, list(Color.__members__.values()))
    v = SchemaValidator(schema)
    assert v.validate_python(2) is Color.GREEN
    ```

    Args:
        cls: The enum class
        members: The members of the enum, generally `list(MyEnum.__members__.values())`
        sub_type: The type of the enum, either 'str' or 'int' or None for plain enums
        missing: A function to use when the value is not found in the enum, from `_missing_`
        strict: Whether to use strict mode, defaults to False
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='enum',
        cls=cls,
        members=members,
        sub_type=sub_type,
        missing=missing,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


# must match input/parse_json.rs::JsonType::try_from
JsonType = Literal['null', 'bool', 'int', 'float', 'str', 'list', 'dict']


class IsInstanceSchema(TypedDict, total=False):
    type: Required[Literal['is-instance']]
    cls: Required[Any]
    cls_repr: str
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def is_instance_schema(
    cls: Any,
    *,
    cls_repr: str | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> IsInstanceSchema:
    """
    Returns a schema that checks if a value is an instance of a class, equivalent to python's `isinstance` method, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    class A:
        pass

    schema = core_schema.is_instance_schema(cls=A)
    v = SchemaValidator(schema)
    v.validate_python(A())
    ```

    Args:
        cls: The value must be an instance of this class
        cls_repr: If provided this string is used in the validator name instead of `repr(cls)`
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='is-instance', cls=cls, cls_repr=cls_repr, ref=ref, metadata=metadata, serialization=serialization
    )


class IsSubclassSchema(TypedDict, total=False):
    type: Required[Literal['is-subclass']]
    cls: Required[type[Any]]
    cls_repr: str
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def is_subclass_schema(
    cls: type[Any],
    *,
    cls_repr: str | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> IsInstanceSchema:
    """
    Returns a schema that checks if a value is a subtype of a class, equivalent to python's `issubclass` method, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    class A:
        pass

    class B(A):
        pass

    schema = core_schema.is_subclass_schema(cls=A)
    v = SchemaValidator(schema)
    v.validate_python(B)
    ```

    Args:
        cls: The value must be a subclass of this class
        cls_repr: If provided this string is used in the validator name instead of `repr(cls)`
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='is-subclass', cls=cls, cls_repr=cls_repr, ref=ref, metadata=metadata, serialization=serialization
    )


class CallableSchema(TypedDict, total=False):
    type: Required[Literal['callable']]
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def callable_schema(
    *, ref: str | None = None, metadata: dict[str, Any] | None = None, serialization: SerSchema | None = None
) -> CallableSchema:
    """
    Returns a schema that checks if a value is callable, equivalent to python's `callable` method, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.callable_schema()
    v = SchemaValidator(schema)
    v.validate_python(min)
    ```

    Args:
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(type='callable', ref=ref, metadata=metadata, serialization=serialization)


class UuidSchema(TypedDict, total=False):
    type: Required[Literal['uuid']]
    version: Literal[1, 3, 4, 5, 7]
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def uuid_schema(
    *,
    version: Literal[1, 3, 4, 5, 6, 7, 8] | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> UuidSchema:
    return _dict_not_none(
        type='uuid', version=version, strict=strict, ref=ref, metadata=metadata, serialization=serialization
    )


class IncExSeqSerSchema(TypedDict, total=False):
    type: Required[Literal['include-exclude-sequence']]
    include: set[int]
    exclude: set[int]


def filter_seq_schema(*, include: set[int] | None = None, exclude: set[int] | None = None) -> IncExSeqSerSchema:
    return _dict_not_none(type='include-exclude-sequence', include=include, exclude=exclude)


IncExSeqOrElseSerSchema = Union[IncExSeqSerSchema, SerSchema]


class ListSchema(TypedDict, total=False):
    type: Required[Literal['list']]
    items_schema: CoreSchema
    min_length: int
    max_length: int
    fail_fast: bool
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: IncExSeqOrElseSerSchema


def list_schema(
    items_schema: CoreSchema | None = None,
    *,
    min_length: int | None = None,
    max_length: int | None = None,
    fail_fast: bool | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: IncExSeqOrElseSerSchema | None = None,
) -> ListSchema:
    """
    Returns a schema that matches a list value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.list_schema(core_schema.int_schema(), min_length=0, max_length=10)
    v = SchemaValidator(schema)
    assert v.validate_python(['4']) == [4]
    ```

    Args:
        items_schema: The value must be a list of items that match this schema
        min_length: The value must be a list with at least this many items
        max_length: The value must be a list with at most this many items
        fail_fast: Stop validation on the first error
        strict: The value must be a list with exactly this many items
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='list',
        items_schema=items_schema,
        min_length=min_length,
        max_length=max_length,
        fail_fast=fail_fast,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


# @deprecated('tuple_positional_schema is deprecated. Use pydantic_core.core_schema.tuple_schema instead.')
def tuple_positional_schema(
    items_schema: list[CoreSchema],
    *,
    extras_schema: CoreSchema | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: IncExSeqOrElseSerSchema | None = None,
) -> TupleSchema:
    """
    Returns a schema that matches a tuple of schemas, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.tuple_positional_schema(
        [core_schema.int_schema(), core_schema.str_schema()]
    )
    v = SchemaValidator(schema)
    assert v.validate_python((1, 'hello')) == (1, 'hello')
    ```

    Args:
        items_schema: The value must be a tuple with items that match these schemas
        extras_schema: The value must be a tuple with items that match this schema
            This was inspired by JSON schema's `prefixItems` and `items` fields.
            In python's `typing.Tuple`, you can't specify a type for "extra" items -- they must all be the same type
            if the length is variable. So this field won't be set from a `typing.Tuple` annotation on a pydantic model.
        strict: The value must be a tuple with exactly this many items
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    if extras_schema is not None:
        variadic_item_index = len(items_schema)
        items_schema = items_schema + [extras_schema]
    else:
        variadic_item_index = None
    return tuple_schema(
        items_schema=items_schema,
        variadic_item_index=variadic_item_index,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


# @deprecated('tuple_variable_schema is deprecated. Use pydantic_core.core_schema.tuple_schema instead.')
def tuple_variable_schema(
    items_schema: CoreSchema | None = None,
    *,
    min_length: int | None = None,
    max_length: int | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: IncExSeqOrElseSerSchema | None = None,
) -> TupleSchema:
    """
    Returns a schema that matches a tuple of a given schema, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.tuple_variable_schema(
        items_schema=core_schema.int_schema(), min_length=0, max_length=10
    )
    v = SchemaValidator(schema)
    assert v.validate_python(('1', 2, 3)) == (1, 2, 3)
    ```

    Args:
        items_schema: The value must be a tuple with items that match this schema
        min_length: The value must be a tuple with at least this many items
        max_length: The value must be a tuple with at most this many items
        strict: The value must be a tuple with exactly this many items
        ref: Optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return tuple_schema(
        items_schema=[items_schema or any_schema()],
        variadic_item_index=0,
        min_length=min_length,
        max_length=max_length,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class TupleSchema(TypedDict, total=False):
    type: Required[Literal['tuple']]
    items_schema: Required[list[CoreSchema]]
    variadic_item_index: int
    min_length: int
    max_length: int
    fail_fast: bool
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: IncExSeqOrElseSerSchema


def tuple_schema(
    items_schema: list[CoreSchema],
    *,
    variadic_item_index: int | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    fail_fast: bool | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: IncExSeqOrElseSerSchema | None = None,
) -> TupleSchema:
    """
    Returns a schema that matches a tuple of schemas, with an optional variadic item, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.tuple_schema(
        [core_schema.int_schema(), core_schema.str_schema(), core_schema.float_schema()],
        variadic_item_index=1,
    )
    v = SchemaValidator(schema)
    assert v.validate_python((1, 'hello', 'world', 1.5)) == (1, 'hello', 'world', 1.5)
    ```

    Args:
        items_schema: The value must be a tuple with items that match these schemas
        variadic_item_index: The index of the schema in `items_schema` to be treated as variadic (following PEP 646)
        min_length: The value must be a tuple with at least this many items
        max_length: The value must be a tuple with at most this many items
        fail_fast: Stop validation on the first error
        strict: The value must be a tuple with exactly this many items
        ref: Optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='tuple',
        items_schema=items_schema,
        variadic_item_index=variadic_item_index,
        min_length=min_length,
        max_length=max_length,
        fail_fast=fail_fast,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class SetSchema(TypedDict, total=False):
    type: Required[Literal['set']]
    items_schema: CoreSchema
    min_length: int
    max_length: int
    fail_fast: bool
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def set_schema(
    items_schema: CoreSchema | None = None,
    *,
    min_length: int | None = None,
    max_length: int | None = None,
    fail_fast: bool | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> SetSchema:
    """
    Returns a schema that matches a set of a given schema, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.set_schema(
        items_schema=core_schema.int_schema(), min_length=0, max_length=10
    )
    v = SchemaValidator(schema)
    assert v.validate_python({1, '2', 3}) == {1, 2, 3}
    ```

    Args:
        items_schema: The value must be a set with items that match this schema
        min_length: The value must be a set with at least this many items
        max_length: The value must be a set with at most this many items
        fail_fast: Stop validation on the first error
        strict: The value must be a set with exactly this many items
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='set',
        items_schema=items_schema,
        min_length=min_length,
        max_length=max_length,
        fail_fast=fail_fast,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class FrozenSetSchema(TypedDict, total=False):
    type: Required[Literal['frozenset']]
    items_schema: CoreSchema
    min_length: int
    max_length: int
    fail_fast: bool
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def frozenset_schema(
    items_schema: CoreSchema | None = None,
    *,
    min_length: int | None = None,
    max_length: int | None = None,
    fail_fast: bool | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> FrozenSetSchema:
    """
    Returns a schema that matches a frozenset of a given schema, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.frozenset_schema(
        items_schema=core_schema.int_schema(), min_length=0, max_length=10
    )
    v = SchemaValidator(schema)
    assert v.validate_python(frozenset(range(3))) == frozenset({0, 1, 2})
    ```

    Args:
        items_schema: The value must be a frozenset with items that match this schema
        min_length: The value must be a frozenset with at least this many items
        max_length: The value must be a frozenset with at most this many items
        fail_fast: Stop validation on the first error
        strict: The value must be a frozenset with exactly this many items
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='frozenset',
        items_schema=items_schema,
        min_length=min_length,
        max_length=max_length,
        fail_fast=fail_fast,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class GeneratorSchema(TypedDict, total=False):
    type: Required[Literal['generator']]
    items_schema: CoreSchema
    min_length: int
    max_length: int
    ref: str
    metadata: dict[str, Any]
    serialization: IncExSeqOrElseSerSchema


def generator_schema(
    items_schema: CoreSchema | None = None,
    *,
    min_length: int | None = None,
    max_length: int | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: IncExSeqOrElseSerSchema | None = None,
) -> GeneratorSchema:
    """
    Returns a schema that matches a generator value, e.g.:

    ```py
    from typing import Iterator
    from pydantic_core import SchemaValidator, core_schema

    def gen() -> Iterator[int]:
        yield 1

    schema = core_schema.generator_schema(items_schema=core_schema.int_schema())
    v = SchemaValidator(schema)
    v.validate_python(gen())
    ```

    Unlike other types, validated generators do not raise ValidationErrors eagerly,
    but instead will raise a ValidationError when a violating value is actually read from the generator.
    This is to ensure that "validated" generators retain the benefit of lazy evaluation.

    Args:
        items_schema: The value must be a generator with items that match this schema
        min_length: The value must be a generator that yields at least this many items
        max_length: The value must be a generator that yields at most this many items
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='generator',
        items_schema=items_schema,
        min_length=min_length,
        max_length=max_length,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


IncExDict = set[Union[int, str]]


class IncExDictSerSchema(TypedDict, total=False):
    type: Required[Literal['include-exclude-dict']]
    include: IncExDict
    exclude: IncExDict


def filter_dict_schema(*, include: IncExDict | None = None, exclude: IncExDict | None = None) -> IncExDictSerSchema:
    return _dict_not_none(type='include-exclude-dict', include=include, exclude=exclude)


IncExDictOrElseSerSchema = Union[IncExDictSerSchema, SerSchema]


class DictSchema(TypedDict, total=False):
    type: Required[Literal['dict']]
    keys_schema: CoreSchema  # default: AnySchema
    values_schema: CoreSchema  # default: AnySchema
    min_length: int
    max_length: int
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: IncExDictOrElseSerSchema


def dict_schema(
    keys_schema: CoreSchema | None = None,
    values_schema: CoreSchema | None = None,
    *,
    min_length: int | None = None,
    max_length: int | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> DictSchema:
    """
    Returns a schema that matches a dict value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.dict_schema(
        keys_schema=core_schema.str_schema(), values_schema=core_schema.int_schema()
    )
    v = SchemaValidator(schema)
    assert v.validate_python({'a': '1', 'b': 2}) == {'a': 1, 'b': 2}
    ```

    Args:
        keys_schema: The value must be a dict with keys that match this schema
        values_schema: The value must be a dict with values that match this schema
        min_length: The value must be a dict with at least this many items
        max_length: The value must be a dict with at most this many items
        strict: Whether the keys and values should be validated with strict mode
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='dict',
        keys_schema=keys_schema,
        values_schema=values_schema,
        min_length=min_length,
        max_length=max_length,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


# (input_value: Any, /) -> Any
NoInfoValidatorFunction = Callable[[Any], Any]


class NoInfoValidatorFunctionSchema(TypedDict):
    type: Literal['no-info']
    function: NoInfoValidatorFunction


# (input_value: Any, info: ValidationInfo, /) -> Any
WithInfoValidatorFunction = Callable[[Any, ValidationInfo], Any]


class WithInfoValidatorFunctionSchema(TypedDict, total=False):
    type: Required[Literal['with-info']]
    function: Required[WithInfoValidatorFunction]
    field_name: str


ValidationFunction = Union[NoInfoValidatorFunctionSchema, WithInfoValidatorFunctionSchema]


class _ValidatorFunctionSchema(TypedDict, total=False):
    function: Required[ValidationFunction]
    schema: Required[CoreSchema]
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


class BeforeValidatorFunctionSchema(_ValidatorFunctionSchema, total=False):
    type: Required[Literal['function-before']]
    json_schema_input_schema: CoreSchema


def no_info_before_validator_function(
    function: NoInfoValidatorFunction,
    schema: CoreSchema,
    *,
    ref: str | None = None,
    json_schema_input_schema: CoreSchema | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> BeforeValidatorFunctionSchema:
    """
    Returns a schema that calls a validator function before validating, no `info` argument is provided, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    def fn(v: bytes) -> str:
        return v.decode() + 'world'

    func_schema = core_schema.no_info_before_validator_function(
        function=fn, schema=core_schema.str_schema()
    )
    schema = core_schema.typed_dict_schema({'a': core_schema.typed_dict_field(func_schema)})

    v = SchemaValidator(schema)
    assert v.validate_python({'a': b'hello '}) == {'a': 'hello world'}
    ```

    Args:
        function: The validator function to call
        schema: The schema to validate the output of the validator function
        ref: optional unique identifier of the schema, used to reference the schema in other places
        json_schema_input_schema: The core schema to be used to generate the corresponding JSON Schema input type
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='function-before',
        function={'type': 'no-info', 'function': function},
        schema=schema,
        ref=ref,
        json_schema_input_schema=json_schema_input_schema,
        metadata=metadata,
        serialization=serialization,
    )


def with_info_before_validator_function(
    function: WithInfoValidatorFunction,
    schema: CoreSchema,
    *,
    field_name: str | None = None,
    ref: str | None = None,
    json_schema_input_schema: CoreSchema | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> BeforeValidatorFunctionSchema:
    """
    Returns a schema that calls a validator function before validation, the function is called with
    an `info` argument, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    def fn(v: bytes, info: core_schema.ValidationInfo) -> str:
        assert info.data is not None
        assert info.field_name is not None
        return v.decode() + 'world'

    func_schema = core_schema.with_info_before_validator_function(
        function=fn, schema=core_schema.str_schema(), field_name='a'
    )
    schema = core_schema.typed_dict_schema({'a': core_schema.typed_dict_field(func_schema)})

    v = SchemaValidator(schema)
    assert v.validate_python({'a': b'hello '}) == {'a': 'hello world'}
    ```

    Args:
        function: The validator function to call
        field_name: The name of the field
        schema: The schema to validate the output of the validator function
        ref: optional unique identifier of the schema, used to reference the schema in other places
        json_schema_input_schema: The core schema to be used to generate the corresponding JSON Schema input type
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='function-before',
        function=_dict_not_none(type='with-info', function=function, field_name=field_name),
        schema=schema,
        ref=ref,
        json_schema_input_schema=json_schema_input_schema,
        metadata=metadata,
        serialization=serialization,
    )


class AfterValidatorFunctionSchema(_ValidatorFunctionSchema, total=False):
    type: Required[Literal['function-after']]


def no_info_after_validator_function(
    function: NoInfoValidatorFunction,
    schema: CoreSchema,
    *,
    ref: str | None = None,
    json_schema_input_schema: CoreSchema | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> AfterValidatorFunctionSchema:
    """
    Returns a schema that calls a validator function after validating, no `info` argument is provided, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    def fn(v: str) -> str:
        return v + 'world'

    func_schema = core_schema.no_info_after_validator_function(fn, core_schema.str_schema())
    schema = core_schema.typed_dict_schema({'a': core_schema.typed_dict_field(func_schema)})

    v = SchemaValidator(schema)
    assert v.validate_python({'a': b'hello '}) == {'a': 'hello world'}
    ```

    Args:
        function: The validator function to call after the schema is validated
        schema: The schema to validate before the validator function
        ref: optional unique identifier of the schema, used to reference the schema in other places
        json_schema_input_schema: The core schema to be used to generate the corresponding JSON Schema input type
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='function-after',
        function={'type': 'no-info', 'function': function},
        schema=schema,
        ref=ref,
        json_schema_input_schema=json_schema_input_schema,
        metadata=metadata,
        serialization=serialization,
    )


def with_info_after_validator_function(
    function: WithInfoValidatorFunction,
    schema: CoreSchema,
    *,
    field_name: str | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> AfterValidatorFunctionSchema:
    """
    Returns a schema that calls a validator function after validation, the function is called with
    an `info` argument, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    def fn(v: str, info: core_schema.ValidationInfo) -> str:
        assert info.data is not None
        assert info.field_name is not None
        return v + 'world'

    func_schema = core_schema.with_info_after_validator_function(
        function=fn, schema=core_schema.str_schema(), field_name='a'
    )
    schema = core_schema.typed_dict_schema({'a': core_schema.typed_dict_field(func_schema)})

    v = SchemaValidator(schema)
    assert v.validate_python({'a': b'hello '}) == {'a': 'hello world'}
    ```

    Args:
        function: The validator function to call after the schema is validated
        schema: The schema to validate before the validator function
        field_name: The name of the field this validators is applied to, if any
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='function-after',
        function=_dict_not_none(type='with-info', function=function, field_name=field_name),
        schema=schema,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class ValidatorFunctionWrapHandler(Protocol):
    def __call__(self, input_value: Any, outer_location: str | int | None = None, /) -> Any:  # pragma: no cover
        ...


# (input_value: Any, validator: ValidatorFunctionWrapHandler, /) -> Any
NoInfoWrapValidatorFunction = Callable[[Any, ValidatorFunctionWrapHandler], Any]


class NoInfoWrapValidatorFunctionSchema(TypedDict):
    type: Literal['no-info']
    function: NoInfoWrapValidatorFunction


# (input_value: Any, validator: ValidatorFunctionWrapHandler, info: ValidationInfo, /) -> Any
WithInfoWrapValidatorFunction = Callable[[Any, ValidatorFunctionWrapHandler, ValidationInfo], Any]


class WithInfoWrapValidatorFunctionSchema(TypedDict, total=False):
    type: Required[Literal['with-info']]
    function: Required[WithInfoWrapValidatorFunction]
    field_name: str


WrapValidatorFunction = Union[NoInfoWrapValidatorFunctionSchema, WithInfoWrapValidatorFunctionSchema]


class WrapValidatorFunctionSchema(TypedDict, total=False):
    type: Required[Literal['function-wrap']]
    function: Required[WrapValidatorFunction]
    schema: Required[CoreSchema]
    ref: str
    json_schema_input_schema: CoreSchema
    metadata: dict[str, Any]
    serialization: SerSchema


def no_info_wrap_validator_function(
    function: NoInfoWrapValidatorFunction,
    schema: CoreSchema,
    *,
    ref: str | None = None,
    json_schema_input_schema: CoreSchema | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> WrapValidatorFunctionSchema:
    """
    Returns a schema which calls a function with a `validator` callable argument which can
    optionally be used to call inner validation with the function logic, this is much like the
    "onion" implementation of middleware in many popular web frameworks, no `info` argument is passed, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    def fn(
        v: str,
        validator: core_schema.ValidatorFunctionWrapHandler,
    ) -> str:
        return validator(input_value=v) + 'world'

    schema = core_schema.no_info_wrap_validator_function(
        function=fn, schema=core_schema.str_schema()
    )
    v = SchemaValidator(schema)
    assert v.validate_python('hello ') == 'hello world'
    ```

    Args:
        function: The validator function to call
        schema: The schema to validate the output of the validator function
        ref: optional unique identifier of the schema, used to reference the schema in other places
        json_schema_input_schema: The core schema to be used to generate the corresponding JSON Schema input type
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='function-wrap',
        function={'type': 'no-info', 'function': function},
        schema=schema,
        json_schema_input_schema=json_schema_input_schema,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


def with_info_wrap_validator_function(
    function: WithInfoWrapValidatorFunction,
    schema: CoreSchema,
    *,
    field_name: str | None = None,
    json_schema_input_schema: CoreSchema | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> WrapValidatorFunctionSchema:
    """
    Returns a schema which calls a function with a `validator` callable argument which can
    optionally be used to call inner validation with the function logic, this is much like the
    "onion" implementation of middleware in many popular web frameworks, an `info` argument is also passed, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    def fn(
        v: str,
        validator: core_schema.ValidatorFunctionWrapHandler,
        info: core_schema.ValidationInfo,
    ) -> str:
        return validator(input_value=v) + 'world'

    schema = core_schema.with_info_wrap_validator_function(
        function=fn, schema=core_schema.str_schema()
    )
    v = SchemaValidator(schema)
    assert v.validate_python('hello ') == 'hello world'
    ```

    Args:
        function: The validator function to call
        schema: The schema to validate the output of the validator function
        field_name: The name of the field this validators is applied to, if any
        json_schema_input_schema: The core schema to be used to generate the corresponding JSON Schema input type
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='function-wrap',
        function=_dict_not_none(type='with-info', function=function, field_name=field_name),
        schema=schema,
        json_schema_input_schema=json_schema_input_schema,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class PlainValidatorFunctionSchema(TypedDict, total=False):
    type: Required[Literal['function-plain']]
    function: Required[ValidationFunction]
    ref: str
    json_schema_input_schema: CoreSchema
    metadata: dict[str, Any]
    serialization: SerSchema


def no_info_plain_validator_function(
    function: NoInfoValidatorFunction,
    *,
    ref: str | None = None,
    json_schema_input_schema: CoreSchema | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> PlainValidatorFunctionSchema:
    """
    Returns a schema that uses the provided function for validation, no `info` argument is passed, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    def fn(v: str) -> str:
        assert 'hello' in v
        return v + 'world'

    schema = core_schema.no_info_plain_validator_function(function=fn)
    v = SchemaValidator(schema)
    assert v.validate_python('hello ') == 'hello world'
    ```

    Args:
        function: The validator function to call
        ref: optional unique identifier of the schema, used to reference the schema in other places
        json_schema_input_schema: The core schema to be used to generate the corresponding JSON Schema input type
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='function-plain',
        function={'type': 'no-info', 'function': function},
        ref=ref,
        json_schema_input_schema=json_schema_input_schema,
        metadata=metadata,
        serialization=serialization,
    )


def with_info_plain_validator_function(
    function: WithInfoValidatorFunction,
    *,
    field_name: str | None = None,
    ref: str | None = None,
    json_schema_input_schema: CoreSchema | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> PlainValidatorFunctionSchema:
    """
    Returns a schema that uses the provided function for validation, an `info` argument is passed, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    def fn(v: str, info: core_schema.ValidationInfo) -> str:
        assert 'hello' in v
        return v + 'world'

    schema = core_schema.with_info_plain_validator_function(function=fn)
    v = SchemaValidator(schema)
    assert v.validate_python('hello ') == 'hello world'
    ```

    Args:
        function: The validator function to call
        field_name: The name of the field this validators is applied to, if any
        ref: optional unique identifier of the schema, used to reference the schema in other places
        json_schema_input_schema: The core schema to be used to generate the corresponding JSON Schema input type
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='function-plain',
        function=_dict_not_none(type='with-info', function=function, field_name=field_name),
        ref=ref,
        json_schema_input_schema=json_schema_input_schema,
        metadata=metadata,
        serialization=serialization,
    )


class WithDefaultSchema(TypedDict, total=False):
    type: Required[Literal['default']]
    schema: Required[CoreSchema]
    default: Any
    default_factory: Union[Callable[[], Any], Callable[[dict[str, Any]], Any]]
    default_factory_takes_data: bool
    on_error: Literal['raise', 'omit', 'default']  # default: 'raise'
    validate_default: bool  # default: False
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def with_default_schema(
    schema: CoreSchema,
    *,
    default: Any = PydanticUndefined,
    default_factory: Union[Callable[[], Any], Callable[[dict[str, Any]], Any], None] = None,
    default_factory_takes_data: bool | None = None,
    on_error: Literal['raise', 'omit', 'default'] | None = None,
    validate_default: bool | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> WithDefaultSchema:
    """
    Returns a schema that adds a default value to the given schema, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.with_default_schema(core_schema.str_schema(), default='hello')
    wrapper_schema = core_schema.typed_dict_schema(
        {'a': core_schema.typed_dict_field(schema)}
    )
    v = SchemaValidator(wrapper_schema)
    assert v.validate_python({}) == v.validate_python({'a': 'hello'})
    ```

    Args:
        schema: The schema to add a default value to
        default: The default value to use
        default_factory: A callable that returns the default value to use
        default_factory_takes_data: Whether the default factory takes a validated data argument
        on_error: What to do if the schema validation fails. One of 'raise', 'omit', 'default'
        validate_default: Whether the default value should be validated
        strict: Whether the underlying schema should be validated with strict mode
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    s = _dict_not_none(
        type='default',
        schema=schema,
        default_factory=default_factory,
        default_factory_takes_data=default_factory_takes_data,
        on_error=on_error,
        validate_default=validate_default,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )
    if default is not PydanticUndefined:
        s['default'] = default
    return s


class NullableSchema(TypedDict, total=False):
    type: Required[Literal['nullable']]
    schema: Required[CoreSchema]
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def nullable_schema(
    schema: CoreSchema,
    *,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> NullableSchema:
    """
    Returns a schema that matches a nullable value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.nullable_schema(core_schema.str_schema())
    v = SchemaValidator(schema)
    assert v.validate_python(None) is None
    ```

    Args:
        schema: The schema to wrap
        strict: Whether the underlying schema should be validated with strict mode
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='nullable', schema=schema, strict=strict, ref=ref, metadata=metadata, serialization=serialization
    )


class UnionSchema(TypedDict, total=False):
    type: Required[Literal['union']]
    choices: Required[list[Union[CoreSchema, tuple[CoreSchema, str]]]]
    # default true, whether to automatically collapse unions with one element to the inner validator
    auto_collapse: bool
    custom_error_type: str
    custom_error_message: str
    custom_error_context: dict[str, Union[str, int, float]]
    mode: Literal['smart', 'left_to_right']  # default: 'smart'
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def union_schema(
    choices: list[CoreSchema | tuple[CoreSchema, str]],
    *,
    auto_collapse: bool | None = None,
    custom_error_type: str | None = None,
    custom_error_message: str | None = None,
    custom_error_context: dict[str, str | int] | None = None,
    mode: Literal['smart', 'left_to_right'] | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> UnionSchema:
    """
    Returns a schema that matches a union value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.union_schema([core_schema.str_schema(), core_schema.int_schema()])
    v = SchemaValidator(schema)
    assert v.validate_python('hello') == 'hello'
    assert v.validate_python(1) == 1
    ```

    Args:
        choices: The schemas to match. If a tuple, the second item is used as the label for the case.
        auto_collapse: whether to automatically collapse unions with one element to the inner validator, default true
        custom_error_type: The custom error type to use if the validation fails
        custom_error_message: The custom error message to use if the validation fails
        custom_error_context: The custom error context to use if the validation fails
        mode: How to select which choice to return
            * `smart` (default) will try to return the choice which is the closest match to the input value
            * `left_to_right` will return the first choice in `choices` which succeeds validation
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='union',
        choices=choices,
        auto_collapse=auto_collapse,
        custom_error_type=custom_error_type,
        custom_error_message=custom_error_message,
        custom_error_context=custom_error_context,
        mode=mode,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class TaggedUnionSchema(TypedDict, total=False):
    type: Required[Literal['tagged-union']]
    choices: Required[dict[Hashable, CoreSchema]]
    discriminator: Required[Union[str, list[Union[str, int]], list[list[Union[str, int]]], Callable[[Any], Hashable]]]
    custom_error_type: str
    custom_error_message: str
    custom_error_context: dict[str, Union[str, int, float]]
    strict: bool
    from_attributes: bool  # default: True
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def tagged_union_schema(
    choices: dict[Any, CoreSchema],
    discriminator: str | list[str | int] | list[list[str | int]] | Callable[[Any], Any],
    *,
    custom_error_type: str | None = None,
    custom_error_message: str | None = None,
    custom_error_context: dict[str, int | str | float] | None = None,
    strict: bool | None = None,
    from_attributes: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> TaggedUnionSchema:
    """
    Returns a schema that matches a tagged union value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    apple_schema = core_schema.typed_dict_schema(
        {
            'foo': core_schema.typed_dict_field(core_schema.str_schema()),
            'bar': core_schema.typed_dict_field(core_schema.int_schema()),
        }
    )
    banana_schema = core_schema.typed_dict_schema(
        {
            'foo': core_schema.typed_dict_field(core_schema.str_schema()),
            'spam': core_schema.typed_dict_field(
                core_schema.list_schema(items_schema=core_schema.int_schema())
            ),
        }
    )
    schema = core_schema.tagged_union_schema(
        choices={
            'apple': apple_schema,
            'banana': banana_schema,
        },
        discriminator='foo',
    )
    v = SchemaValidator(schema)
    assert v.validate_python({'foo': 'apple', 'bar': '123'}) == {'foo': 'apple', 'bar': 123}
    assert v.validate_python({'foo': 'banana', 'spam': [1, 2, 3]}) == {
        'foo': 'banana',
        'spam': [1, 2, 3],
    }
    ```

    Args:
        choices: The schemas to match
            When retrieving a schema from `choices` using the discriminator value, if the value is a str,
            it should be fed back into the `choices` map until a schema is obtained
            (This approach is to prevent multiple ownership of a single schema in Rust)
        discriminator: The discriminator to use to determine the schema to use
            * If `discriminator` is a str, it is the name of the attribute to use as the discriminator
            * If `discriminator` is a list of int/str, it should be used as a "path" to access the discriminator
            * If `discriminator` is a list of lists, each inner list is a path, and the first path that exists is used
            * If `discriminator` is a callable, it should return the discriminator when called on the value to validate;
              the callable can return `None` to indicate that there is no matching discriminator present on the input
        custom_error_type: The custom error type to use if the validation fails
        custom_error_message: The custom error message to use if the validation fails
        custom_error_context: The custom error context to use if the validation fails
        strict: Whether the underlying schemas should be validated with strict mode
        from_attributes: Whether to use the attributes of the object to retrieve the discriminator value
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='tagged-union',
        choices=choices,
        discriminator=discriminator,
        custom_error_type=custom_error_type,
        custom_error_message=custom_error_message,
        custom_error_context=custom_error_context,
        strict=strict,
        from_attributes=from_attributes,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class ChainSchema(TypedDict, total=False):
    type: Required[Literal['chain']]
    steps: Required[list[CoreSchema]]
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def chain_schema(
    steps: list[CoreSchema],
    *,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> ChainSchema:
    """
    Returns a schema that chains the provided validation schemas, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    def fn(v: str, info: core_schema.ValidationInfo) -> str:
        assert 'hello' in v
        return v + ' world'

    fn_schema = core_schema.with_info_plain_validator_function(function=fn)
    schema = core_schema.chain_schema(
        [fn_schema, fn_schema, fn_schema, core_schema.str_schema()]
    )
    v = SchemaValidator(schema)
    assert v.validate_python('hello') == 'hello world world world'
    ```

    Args:
        steps: The schemas to chain
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(type='chain', steps=steps, ref=ref, metadata=metadata, serialization=serialization)


class LaxOrStrictSchema(TypedDict, total=False):
    type: Required[Literal['lax-or-strict']]
    lax_schema: Required[CoreSchema]
    strict_schema: Required[CoreSchema]
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def lax_or_strict_schema(
    lax_schema: CoreSchema,
    strict_schema: CoreSchema,
    *,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> LaxOrStrictSchema:
    """
    Returns a schema that uses the lax or strict schema, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    def fn(v: str, info: core_schema.ValidationInfo) -> str:
        assert 'hello' in v
        return v + ' world'

    lax_schema = core_schema.int_schema(strict=False)
    strict_schema = core_schema.int_schema(strict=True)

    schema = core_schema.lax_or_strict_schema(
        lax_schema=lax_schema, strict_schema=strict_schema, strict=True
    )
    v = SchemaValidator(schema)
    assert v.validate_python(123) == 123

    schema = core_schema.lax_or_strict_schema(
        lax_schema=lax_schema, strict_schema=strict_schema, strict=False
    )
    v = SchemaValidator(schema)
    assert v.validate_python('123') == 123
    ```

    Args:
        lax_schema: The lax schema to use
        strict_schema: The strict schema to use
        strict: Whether the strict schema should be used
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='lax-or-strict',
        lax_schema=lax_schema,
        strict_schema=strict_schema,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class JsonOrPythonSchema(TypedDict, total=False):
    type: Required[Literal['json-or-python']]
    json_schema: Required[CoreSchema]
    python_schema: Required[CoreSchema]
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def json_or_python_schema(
    json_schema: CoreSchema,
    python_schema: CoreSchema,
    *,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> JsonOrPythonSchema:
    """
    Returns a schema that uses the Json or Python schema depending on the input:

    ```py
    from pydantic_core import SchemaValidator, ValidationError, core_schema

    v = SchemaValidator(
        core_schema.json_or_python_schema(
            json_schema=core_schema.int_schema(),
            python_schema=core_schema.int_schema(strict=True),
        )
    )

    assert v.validate_json('"123"') == 123

    try:
        v.validate_python('123')
    except ValidationError:
        pass
    else:
        raise AssertionError('Validation should have failed')
    ```

    Args:
        json_schema: The schema to use for Json inputs
        python_schema: The schema to use for Python inputs
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='json-or-python',
        json_schema=json_schema,
        python_schema=python_schema,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class TypedDictField(TypedDict, total=False):
    type: Required[Literal['typed-dict-field']]
    schema: Required[CoreSchema]
    required: bool
    validation_alias: Union[str, list[Union[str, int]], list[list[Union[str, int]]]]
    serialization_alias: str
    serialization_exclude: bool  # default: False
    metadata: dict[str, Any]


def typed_dict_field(
    schema: CoreSchema,
    *,
    required: bool | None = None,
    validation_alias: str | list[str | int] | list[list[str | int]] | None = None,
    serialization_alias: str | None = None,
    serialization_exclude: bool | None = None,
    metadata: dict[str, Any] | None = None,
) -> TypedDictField:
    """
    Returns a schema that matches a typed dict field, e.g.:

    ```py
    from pydantic_core import core_schema

    field = core_schema.typed_dict_field(schema=core_schema.int_schema(), required=True)
    ```

    Args:
        schema: The schema to use for the field
        required: Whether the field is required, otherwise uses the value from `total` on the typed dict
        validation_alias: The alias(es) to use to find the field in the validation data
        serialization_alias: The alias to use as a key when serializing
        serialization_exclude: Whether to exclude the field when serializing
        metadata: Any other information you want to include with the schema, not used by pydantic-core
    """
    return _dict_not_none(
        type='typed-dict-field',
        schema=schema,
        required=required,
        validation_alias=validation_alias,
        serialization_alias=serialization_alias,
        serialization_exclude=serialization_exclude,
        metadata=metadata,
    )


class TypedDictSchema(TypedDict, total=False):
    type: Required[Literal['typed-dict']]
    fields: Required[dict[str, TypedDictField]]
    cls: type[Any]
    cls_name: str
    computed_fields: list[ComputedField]
    strict: bool
    extras_schema: CoreSchema
    # all these values can be set via config, equivalent fields have `typed_dict_` prefix
    extra_behavior: ExtraBehavior
    total: bool  # default: True
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema
    config: CoreConfig


def typed_dict_schema(
    fields: dict[str, TypedDictField],
    *,
    cls: type[Any] | None = None,
    cls_name: str | None = None,
    computed_fields: list[ComputedField] | None = None,
    strict: bool | None = None,
    extras_schema: CoreSchema | None = None,
    extra_behavior: ExtraBehavior | None = None,
    total: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
    config: CoreConfig | None = None,
) -> TypedDictSchema:
    """
    Returns a schema that matches a typed dict, e.g.:

    ```py
    from typing_extensions import TypedDict

    from pydantic_core import SchemaValidator, core_schema

    class MyTypedDict(TypedDict):
        a: str

    wrapper_schema = core_schema.typed_dict_schema(
        {'a': core_schema.typed_dict_field(core_schema.str_schema())}, cls=MyTypedDict
    )
    v = SchemaValidator(wrapper_schema)
    assert v.validate_python({'a': 'hello'}) == {'a': 'hello'}
    ```

    Args:
        fields: The fields to use for the typed dict
        cls: The class to use for the typed dict
        cls_name: The name to use in error locations. Falls back to `cls.__name__`, or the validator name if no class
            is provided.
        computed_fields: Computed fields to use when serializing the model, only applies when directly inside a model
        strict: Whether the typed dict is strict
        extras_schema: The extra validator to use for the typed dict
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        extra_behavior: The extra behavior to use for the typed dict
        total: Whether the typed dict is total, otherwise uses `typed_dict_total` from config
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='typed-dict',
        fields=fields,
        cls=cls,
        cls_name=cls_name,
        computed_fields=computed_fields,
        strict=strict,
        extras_schema=extras_schema,
        extra_behavior=extra_behavior,
        total=total,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
        config=config,
    )


class ModelField(TypedDict, total=False):
    type: Required[Literal['model-field']]
    schema: Required[CoreSchema]
    validation_alias: Union[str, list[Union[str, int]], list[list[Union[str, int]]]]
    serialization_alias: str
    serialization_exclude: bool  # default: False
    frozen: bool
    metadata: dict[str, Any]


def model_field(
    schema: CoreSchema,
    *,
    validation_alias: str | list[str | int] | list[list[str | int]] | None = None,
    serialization_alias: str | None = None,
    serialization_exclude: bool | None = None,
    frozen: bool | None = None,
    metadata: dict[str, Any] | None = None,
) -> ModelField:
    """
    Returns a schema for a model field, e.g.:

    ```py
    from pydantic_core import core_schema

    field = core_schema.model_field(schema=core_schema.int_schema())
    ```

    Args:
        schema: The schema to use for the field
        validation_alias: The alias(es) to use to find the field in the validation data
        serialization_alias: The alias to use as a key when serializing
        serialization_exclude: Whether to exclude the field when serializing
        frozen: Whether the field is frozen
        metadata: Any other information you want to include with the schema, not used by pydantic-core
    """
    return _dict_not_none(
        type='model-field',
        schema=schema,
        validation_alias=validation_alias,
        serialization_alias=serialization_alias,
        serialization_exclude=serialization_exclude,
        frozen=frozen,
        metadata=metadata,
    )


class ModelFieldsSchema(TypedDict, total=False):
    type: Required[Literal['model-fields']]
    fields: Required[dict[str, ModelField]]
    model_name: str
    computed_fields: list[ComputedField]
    strict: bool
    extras_schema: CoreSchema
    extras_keys_schema: CoreSchema
    extra_behavior: ExtraBehavior
    from_attributes: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def model_fields_schema(
    fields: dict[str, ModelField],
    *,
    model_name: str | None = None,
    computed_fields: list[ComputedField] | None = None,
    strict: bool | None = None,
    extras_schema: CoreSchema | None = None,
    extras_keys_schema: CoreSchema | None = None,
    extra_behavior: ExtraBehavior | None = None,
    from_attributes: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> ModelFieldsSchema:
    """
    Returns a schema that matches the fields of a Pydantic model, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    wrapper_schema = core_schema.model_fields_schema(
        {'a': core_schema.model_field(core_schema.str_schema())}
    )
    v = SchemaValidator(wrapper_schema)
    print(v.validate_python({'a': 'hello'}))
    #> ({'a': 'hello'}, None, {'a'})
    ```

    Args:
        fields: The fields of the model
        model_name: The name of the model, used for error messages, defaults to "Model"
        computed_fields: Computed fields to use when serializing the model, only applies when directly inside a model
        strict: Whether the model is strict
        extras_schema: The schema to use when validating extra input data
        extras_keys_schema: The schema to use when validating the keys of extra input data
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        extra_behavior: The extra behavior to use for the model fields
        from_attributes: Whether the model fields should be populated from attributes
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='model-fields',
        fields=fields,
        model_name=model_name,
        computed_fields=computed_fields,
        strict=strict,
        extras_schema=extras_schema,
        extras_keys_schema=extras_keys_schema,
        extra_behavior=extra_behavior,
        from_attributes=from_attributes,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class ModelSchema(TypedDict, total=False):
    type: Required[Literal['model']]
    cls: Required[type[Any]]
    generic_origin: type[Any]
    schema: Required[CoreSchema]
    custom_init: bool
    root_model: bool
    post_init: str
    revalidate_instances: Literal['always', 'never', 'subclass-instances']  # default: 'never'
    strict: bool
    frozen: bool
    extra_behavior: ExtraBehavior
    config: CoreConfig
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def model_schema(
    cls: type[Any],
    schema: CoreSchema,
    *,
    generic_origin: type[Any] | None = None,
    custom_init: bool | None = None,
    root_model: bool | None = None,
    post_init: str | None = None,
    revalidate_instances: Literal['always', 'never', 'subclass-instances'] | None = None,
    strict: bool | None = None,
    frozen: bool | None = None,
    extra_behavior: ExtraBehavior | None = None,
    config: CoreConfig | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> ModelSchema:
    """
    A model schema generally contains a typed-dict schema.
    It will run the typed dict validator, then create a new class
    and set the dict and fields set returned from the typed dict validator
    to `__dict__` and `__pydantic_fields_set__` respectively.

    Example:

    ```py
    from pydantic_core import CoreConfig, SchemaValidator, core_schema

    class MyModel:
        __slots__ = (
            '__dict__',
            '__pydantic_fields_set__',
            '__pydantic_extra__',
            '__pydantic_private__',
        )

    schema = core_schema.model_schema(
        cls=MyModel,
        config=CoreConfig(str_max_length=5),
        schema=core_schema.model_fields_schema(
            fields={'a': core_schema.model_field(core_schema.str_schema())},
        ),
    )
    v = SchemaValidator(schema)
    assert v.isinstance_python({'a': 'hello'}) is True
    assert v.isinstance_python({'a': 'too long'}) is False
    ```

    Args:
        cls: The class to use for the model
        schema: The schema to use for the model
        generic_origin: The origin type used for this model, if it's a parametrized generic. Ex,
            if this model schema represents `SomeModel[int]`, generic_origin is `SomeModel`
        custom_init: Whether the model has a custom init method
        root_model: Whether the model is a `RootModel`
        post_init: The call after init to use for the model
        revalidate_instances: whether instances of models and dataclasses (including subclass instances)
            should re-validate defaults to config.revalidate_instances, else 'never'
        strict: Whether the model is strict
        frozen: Whether the model is frozen
        extra_behavior: The extra behavior to use for the model, used in serialization
        config: The config to use for the model
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='model',
        cls=cls,
        generic_origin=generic_origin,
        schema=schema,
        custom_init=custom_init,
        root_model=root_model,
        post_init=post_init,
        revalidate_instances=revalidate_instances,
        strict=strict,
        frozen=frozen,
        extra_behavior=extra_behavior,
        config=config,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class DataclassField(TypedDict, total=False):
    type: Required[Literal['dataclass-field']]
    name: Required[str]
    schema: Required[CoreSchema]
    kw_only: bool  # default: True
    init: bool  # default: True
    init_only: bool  # default: False
    frozen: bool  # default: False
    validation_alias: Union[str, list[Union[str, int]], list[list[Union[str, int]]]]
    serialization_alias: str
    serialization_exclude: bool  # default: False
    metadata: dict[str, Any]


def dataclass_field(
    name: str,
    schema: CoreSchema,
    *,
    kw_only: bool | None = None,
    init: bool | None = None,
    init_only: bool | None = None,
    validation_alias: str | list[str | int] | list[list[str | int]] | None = None,
    serialization_alias: str | None = None,
    serialization_exclude: bool | None = None,
    metadata: dict[str, Any] | None = None,
    frozen: bool | None = None,
) -> DataclassField:
    """
    Returns a schema for a dataclass field, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    field = core_schema.dataclass_field(
        name='a', schema=core_schema.str_schema(), kw_only=False
    )
    schema = core_schema.dataclass_args_schema('Foobar', [field])
    v = SchemaValidator(schema)
    assert v.validate_python({'a': 'hello'}) == ({'a': 'hello'}, None)
    ```

    Args:
        name: The name to use for the argument parameter
        schema: The schema to use for the argument parameter
        kw_only: Whether the field can be set with a positional argument as well as a keyword argument
        init: Whether the field should be validated during initialization
        init_only: Whether the field should be omitted  from `__dict__` and passed to `__post_init__`
        validation_alias: The alias(es) to use to find the field in the validation data
        serialization_alias: The alias to use as a key when serializing
        serialization_exclude: Whether to exclude the field when serializing
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        frozen: Whether the field is frozen
    """
    return _dict_not_none(
        type='dataclass-field',
        name=name,
        schema=schema,
        kw_only=kw_only,
        init=init,
        init_only=init_only,
        validation_alias=validation_alias,
        serialization_alias=serialization_alias,
        serialization_exclude=serialization_exclude,
        metadata=metadata,
        frozen=frozen,
    )


class DataclassArgsSchema(TypedDict, total=False):
    type: Required[Literal['dataclass-args']]
    dataclass_name: Required[str]
    fields: Required[list[DataclassField]]
    computed_fields: list[ComputedField]
    collect_init_only: bool  # default: False
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema
    extra_behavior: ExtraBehavior


def dataclass_args_schema(
    dataclass_name: str,
    fields: list[DataclassField],
    *,
    computed_fields: list[ComputedField] | None = None,
    collect_init_only: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
    extra_behavior: ExtraBehavior | None = None,
) -> DataclassArgsSchema:
    """
    Returns a schema for validating dataclass arguments, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    field_a = core_schema.dataclass_field(
        name='a', schema=core_schema.str_schema(), kw_only=False
    )
    field_b = core_schema.dataclass_field(
        name='b', schema=core_schema.bool_schema(), kw_only=False
    )
    schema = core_schema.dataclass_args_schema('Foobar', [field_a, field_b])
    v = SchemaValidator(schema)
    assert v.validate_python({'a': 'hello', 'b': True}) == ({'a': 'hello', 'b': True}, None)
    ```

    Args:
        dataclass_name: The name of the dataclass being validated
        fields: The fields to use for the dataclass
        computed_fields: Computed fields to use when serializing the dataclass
        collect_init_only: Whether to collect init only fields into a dict to pass to `__post_init__`
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
        extra_behavior: How to handle extra fields
    """
    return _dict_not_none(
        type='dataclass-args',
        dataclass_name=dataclass_name,
        fields=fields,
        computed_fields=computed_fields,
        collect_init_only=collect_init_only,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
        extra_behavior=extra_behavior,
    )


class DataclassSchema(TypedDict, total=False):
    type: Required[Literal['dataclass']]
    cls: Required[type[Any]]
    generic_origin: type[Any]
    schema: Required[CoreSchema]
    fields: Required[list[str]]
    cls_name: str
    post_init: bool  # default: False
    revalidate_instances: Literal['always', 'never', 'subclass-instances']  # default: 'never'
    strict: bool  # default: False
    frozen: bool  # default False
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema
    slots: bool
    config: CoreConfig


def dataclass_schema(
    cls: type[Any],
    schema: CoreSchema,
    fields: list[str],
    *,
    generic_origin: type[Any] | None = None,
    cls_name: str | None = None,
    post_init: bool | None = None,
    revalidate_instances: Literal['always', 'never', 'subclass-instances'] | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
    frozen: bool | None = None,
    slots: bool | None = None,
    config: CoreConfig | None = None,
) -> DataclassSchema:
    """
    Returns a schema for a dataclass. As with `ModelSchema`, this schema can only be used as a field within
    another schema, not as the root type.

    Args:
        cls: The dataclass type, used to perform subclass checks
        schema: The schema to use for the dataclass fields
        fields: Fields of the dataclass, this is used in serialization and in validation during re-validation
            and while validating assignment
        generic_origin: The origin type used for this dataclass, if it's a parametrized generic. Ex,
            if this model schema represents `SomeDataclass[int]`, generic_origin is `SomeDataclass`
        cls_name: The name to use in error locs, etc; this is useful for generics (default: `cls.__name__`)
        post_init: Whether to call `__post_init__` after validation
        revalidate_instances: whether instances of models and dataclasses (including subclass instances)
            should re-validate defaults to config.revalidate_instances, else 'never'
        strict: Whether to require an exact instance of `cls`
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
        frozen: Whether the dataclass is frozen
        slots: Whether `slots=True` on the dataclass, means each field is assigned independently, rather than
            simply setting `__dict__`, default false
    """
    return _dict_not_none(
        type='dataclass',
        cls=cls,
        generic_origin=generic_origin,
        fields=fields,
        cls_name=cls_name,
        schema=schema,
        post_init=post_init,
        revalidate_instances=revalidate_instances,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
        frozen=frozen,
        slots=slots,
        config=config,
    )


class ArgumentsParameter(TypedDict, total=False):
    name: Required[str]
    schema: Required[CoreSchema]
    mode: Literal['positional_only', 'positional_or_keyword', 'keyword_only']  # default positional_or_keyword
    alias: Union[str, list[Union[str, int]], list[list[Union[str, int]]]]


def arguments_parameter(
    name: str,
    schema: CoreSchema,
    *,
    mode: Literal['positional_only', 'positional_or_keyword', 'keyword_only'] | None = None,
    alias: str | list[str | int] | list[list[str | int]] | None = None,
) -> ArgumentsParameter:
    """
    Returns a schema that matches an argument parameter, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    param = core_schema.arguments_parameter(
        name='a', schema=core_schema.str_schema(), mode='positional_only'
    )
    schema = core_schema.arguments_schema([param])
    v = SchemaValidator(schema)
    assert v.validate_python(('hello',)) == (('hello',), {})
    ```

    Args:
        name: The name to use for the argument parameter
        schema: The schema to use for the argument parameter
        mode: The mode to use for the argument parameter
        alias: The alias to use for the argument parameter
    """
    return _dict_not_none(name=name, schema=schema, mode=mode, alias=alias)


VarKwargsMode: TypeAlias = Literal['uniform', 'unpacked-typed-dict']


class ArgumentsSchema(TypedDict, total=False):
    type: Required[Literal['arguments']]
    arguments_schema: Required[list[ArgumentsParameter]]
    validate_by_name: bool
    validate_by_alias: bool
    var_args_schema: CoreSchema
    var_kwargs_mode: VarKwargsMode
    var_kwargs_schema: CoreSchema
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def arguments_schema(
    arguments: list[ArgumentsParameter],
    *,
    validate_by_name: bool | None = None,
    validate_by_alias: bool | None = None,
    var_args_schema: CoreSchema | None = None,
    var_kwargs_mode: VarKwargsMode | None = None,
    var_kwargs_schema: CoreSchema | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> ArgumentsSchema:
    """
    Returns a schema that matches an arguments schema, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    param_a = core_schema.arguments_parameter(
        name='a', schema=core_schema.str_schema(), mode='positional_only'
    )
    param_b = core_schema.arguments_parameter(
        name='b', schema=core_schema.bool_schema(), mode='positional_only'
    )
    schema = core_schema.arguments_schema([param_a, param_b])
    v = SchemaValidator(schema)
    assert v.validate_python(('hello', True)) == (('hello', True), {})
    ```

    Args:
        arguments: The arguments to use for the arguments schema
        validate_by_name: Whether to populate by the parameter names, defaults to `False`.
        validate_by_alias: Whether to populate by the parameter aliases, defaults to `True`.
        var_args_schema: The variable args schema to use for the arguments schema
        var_kwargs_mode: The validation mode to use for variadic keyword arguments. If `'uniform'`, every value of the
            keyword arguments will be validated against the `var_kwargs_schema` schema. If `'unpacked-typed-dict'`,
            the `var_kwargs_schema` argument must be a [`typed_dict_schema`][pydantic_core.core_schema.typed_dict_schema]
        var_kwargs_schema: The variable kwargs schema to use for the arguments schema
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='arguments',
        arguments_schema=arguments,
        validate_by_name=validate_by_name,
        validate_by_alias=validate_by_alias,
        var_args_schema=var_args_schema,
        var_kwargs_mode=var_kwargs_mode,
        var_kwargs_schema=var_kwargs_schema,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class ArgumentsV3Parameter(TypedDict, total=False):
    name: Required[str]
    schema: Required[CoreSchema]
    mode: Literal[
        'positional_only',
        'positional_or_keyword',
        'keyword_only',
        'var_args',
        'var_kwargs_uniform',
        'var_kwargs_unpacked_typed_dict',
    ]  # default positional_or_keyword
    alias: Union[str, list[Union[str, int]], list[list[Union[str, int]]]]


def arguments_v3_parameter(
    name: str,
    schema: CoreSchema,
    *,
    mode: Literal[
        'positional_only',
        'positional_or_keyword',
        'keyword_only',
        'var_args',
        'var_kwargs_uniform',
        'var_kwargs_unpacked_typed_dict',
    ]
    | None = None,
    alias: str | list[str | int] | list[list[str | int]] | None = None,
) -> ArgumentsV3Parameter:
    """
    Returns a schema that matches an argument parameter, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    param = core_schema.arguments_v3_parameter(
        name='a', schema=core_schema.str_schema(), mode='positional_only'
    )
    schema = core_schema.arguments_v3_schema([param])
    v = SchemaValidator(schema)
    assert v.validate_python({'a': 'hello'}) == (('hello',), {})
    ```

    Args:
        name: The name to use for the argument parameter
        schema: The schema to use for the argument parameter
        mode: The mode to use for the argument parameter
        alias: The alias to use for the argument parameter
    """
    return _dict_not_none(name=name, schema=schema, mode=mode, alias=alias)


class ArgumentsV3Schema(TypedDict, total=False):
    type: Required[Literal['arguments-v3']]
    arguments_schema: Required[list[ArgumentsV3Parameter]]
    validate_by_name: bool
    validate_by_alias: bool
    extra_behavior: Literal['forbid', 'ignore']  # 'allow' doesn't make sense here.
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def arguments_v3_schema(
    arguments: list[ArgumentsV3Parameter],
    *,
    validate_by_name: bool | None = None,
    validate_by_alias: bool | None = None,
    extra_behavior: Literal['forbid', 'ignore'] | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> ArgumentsV3Schema:
    """
    Returns a schema that matches an arguments schema, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    param_a = core_schema.arguments_v3_parameter(
        name='a', schema=core_schema.str_schema(), mode='positional_only'
    )
    param_b = core_schema.arguments_v3_parameter(
        name='kwargs', schema=core_schema.bool_schema(), mode='var_kwargs_uniform'
    )
    schema = core_schema.arguments_v3_schema([param_a, param_b])
    v = SchemaValidator(schema)
    assert v.validate_python({'a': 'hi', 'kwargs': {'b': True}}) == (('hi',), {'b': True})
    ```

    This schema is currently not used by other Pydantic components. In V3, it will most likely
    become the default arguments schema for the `'call'` schema.

    Args:
        arguments: The arguments to use for the arguments schema.
        validate_by_name: Whether to populate by the parameter names, defaults to `False`.
        validate_by_alias: Whether to populate by the parameter aliases, defaults to `True`.
        extra_behavior: The extra behavior to use.
        ref: optional unique identifier of the schema, used to reference the schema in other places.
        metadata: Any other information you want to include with the schema, not used by pydantic-core.
        serialization: Custom serialization schema.
    """
    return _dict_not_none(
        type='arguments-v3',
        arguments_schema=arguments,
        validate_by_name=validate_by_name,
        validate_by_alias=validate_by_alias,
        extra_behavior=extra_behavior,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class CallSchema(TypedDict, total=False):
    type: Required[Literal['call']]
    arguments_schema: Required[CoreSchema]
    function: Required[Callable[..., Any]]
    function_name: str  # default function.__name__
    return_schema: CoreSchema
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def call_schema(
    arguments: CoreSchema,
    function: Callable[..., Any],
    *,
    function_name: str | None = None,
    return_schema: CoreSchema | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> CallSchema:
    """
    Returns a schema that matches an arguments schema, then calls a function, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    param_a = core_schema.arguments_parameter(
        name='a', schema=core_schema.str_schema(), mode='positional_only'
    )
    param_b = core_schema.arguments_parameter(
        name='b', schema=core_schema.bool_schema(), mode='positional_only'
    )
    args_schema = core_schema.arguments_schema([param_a, param_b])

    schema = core_schema.call_schema(
        arguments=args_schema,
        function=lambda a, b: a + str(not b),
        return_schema=core_schema.str_schema(),
    )
    v = SchemaValidator(schema)
    assert v.validate_python((('hello', True))) == 'helloFalse'
    ```

    Args:
        arguments: The arguments to use for the arguments schema
        function: The function to use for the call schema
        function_name: The function name to use for the call schema, if not provided `function.__name__` is used
        return_schema: The return schema to use for the call schema
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='call',
        arguments_schema=arguments,
        function=function,
        function_name=function_name,
        return_schema=return_schema,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class CustomErrorSchema(TypedDict, total=False):
    type: Required[Literal['custom-error']]
    schema: Required[CoreSchema]
    custom_error_type: Required[str]
    custom_error_message: str
    custom_error_context: dict[str, Union[str, int, float]]
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def custom_error_schema(
    schema: CoreSchema,
    custom_error_type: str,
    *,
    custom_error_message: str | None = None,
    custom_error_context: dict[str, Any] | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> CustomErrorSchema:
    """
    Returns a schema that matches a custom error value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.custom_error_schema(
        schema=core_schema.int_schema(),
        custom_error_type='MyError',
        custom_error_message='Error msg',
    )
    v = SchemaValidator(schema)
    v.validate_python(1)
    ```

    Args:
        schema: The schema to use for the custom error schema
        custom_error_type: The custom error type to use for the custom error schema
        custom_error_message: The custom error message to use for the custom error schema
        custom_error_context: The custom error context to use for the custom error schema
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='custom-error',
        schema=schema,
        custom_error_type=custom_error_type,
        custom_error_message=custom_error_message,
        custom_error_context=custom_error_context,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class JsonSchema(TypedDict, total=False):
    type: Required[Literal['json']]
    schema: CoreSchema
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def json_schema(
    schema: CoreSchema | None = None,
    *,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> JsonSchema:
    """
    Returns a schema that matches a JSON value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    dict_schema = core_schema.model_fields_schema(
        {
            'field_a': core_schema.model_field(core_schema.str_schema()),
            'field_b': core_schema.model_field(core_schema.bool_schema()),
        },
    )

    class MyModel:
        __slots__ = (
            '__dict__',
            '__pydantic_fields_set__',
            '__pydantic_extra__',
            '__pydantic_private__',
        )
        field_a: str
        field_b: bool

    json_schema = core_schema.json_schema(schema=dict_schema)
    schema = core_schema.model_schema(cls=MyModel, schema=json_schema)
    v = SchemaValidator(schema)
    m = v.validate_python('{"field_a": "hello", "field_b": true}')
    assert isinstance(m, MyModel)
    ```

    Args:
        schema: The schema to use for the JSON schema
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(type='json', schema=schema, ref=ref, metadata=metadata, serialization=serialization)


class UrlSchema(TypedDict, total=False):
    type: Required[Literal['url']]
    max_length: int
    allowed_schemes: list[str]
    host_required: bool  # default False
    default_host: str
    default_port: int
    default_path: str
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def url_schema(
    *,
    max_length: int | None = None,
    allowed_schemes: list[str] | None = None,
    host_required: bool | None = None,
    default_host: str | None = None,
    default_port: int | None = None,
    default_path: str | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> UrlSchema:
    """
    Returns a schema that matches a URL value, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.url_schema()
    v = SchemaValidator(schema)
    print(v.validate_python('https://example.com'))
    #> https://example.com/
    ```

    Args:
        max_length: The maximum length of the URL
        allowed_schemes: The allowed URL schemes
        host_required: Whether the URL must have a host
        default_host: The default host to use if the URL does not have a host
        default_port: The default port to use if the URL does not have a port
        default_path: The default path to use if the URL does not have a path
        strict: Whether to use strict URL parsing
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='url',
        max_length=max_length,
        allowed_schemes=allowed_schemes,
        host_required=host_required,
        default_host=default_host,
        default_port=default_port,
        default_path=default_path,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class MultiHostUrlSchema(TypedDict, total=False):
    type: Required[Literal['multi-host-url']]
    max_length: int
    allowed_schemes: list[str]
    host_required: bool  # default False
    default_host: str
    default_port: int
    default_path: str
    strict: bool
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def multi_host_url_schema(
    *,
    max_length: int | None = None,
    allowed_schemes: list[str] | None = None,
    host_required: bool | None = None,
    default_host: str | None = None,
    default_port: int | None = None,
    default_path: str | None = None,
    strict: bool | None = None,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> MultiHostUrlSchema:
    """
    Returns a schema that matches a URL value with possibly multiple hosts, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.multi_host_url_schema()
    v = SchemaValidator(schema)
    print(v.validate_python('redis://localhost,0.0.0.0,127.0.0.1'))
    #> redis://localhost,0.0.0.0,127.0.0.1
    ```

    Args:
        max_length: The maximum length of the URL
        allowed_schemes: The allowed URL schemes
        host_required: Whether the URL must have a host
        default_host: The default host to use if the URL does not have a host
        default_port: The default port to use if the URL does not have a port
        default_path: The default path to use if the URL does not have a path
        strict: Whether to use strict URL parsing
        ref: optional unique identifier of the schema, used to reference the schema in other places
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='multi-host-url',
        max_length=max_length,
        allowed_schemes=allowed_schemes,
        host_required=host_required,
        default_host=default_host,
        default_port=default_port,
        default_path=default_path,
        strict=strict,
        ref=ref,
        metadata=metadata,
        serialization=serialization,
    )


class DefinitionsSchema(TypedDict, total=False):
    type: Required[Literal['definitions']]
    schema: Required[CoreSchema]
    definitions: Required[list[CoreSchema]]
    metadata: dict[str, Any]
    serialization: SerSchema


def definitions_schema(schema: CoreSchema, definitions: list[CoreSchema]) -> DefinitionsSchema:
    """
    Build a schema that contains both an inner schema and a list of definitions which can be used
    within the inner schema.

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema = core_schema.definitions_schema(
        core_schema.list_schema(core_schema.definition_reference_schema('foobar')),
        [core_schema.int_schema(ref='foobar')],
    )
    v = SchemaValidator(schema)
    assert v.validate_python([1, 2, '3']) == [1, 2, 3]
    ```

    Args:
        schema: The inner schema
        definitions: List of definitions which can be referenced within inner schema
    """
    return DefinitionsSchema(type='definitions', schema=schema, definitions=definitions)


class DefinitionReferenceSchema(TypedDict, total=False):
    type: Required[Literal['definition-ref']]
    schema_ref: Required[str]
    ref: str
    metadata: dict[str, Any]
    serialization: SerSchema


def definition_reference_schema(
    schema_ref: str,
    ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    serialization: SerSchema | None = None,
) -> DefinitionReferenceSchema:
    """
    Returns a schema that points to a schema stored in "definitions", this is useful for nested recursive
    models and also when you want to define validators separately from the main schema, e.g.:

    ```py
    from pydantic_core import SchemaValidator, core_schema

    schema_definition = core_schema.definition_reference_schema('list-schema')
    schema = core_schema.definitions_schema(
        schema=schema_definition,
        definitions=[
            core_schema.list_schema(items_schema=schema_definition, ref='list-schema'),
        ],
    )
    v = SchemaValidator(schema)
    assert v.validate_python([()]) == [[]]
    ```

    Args:
        schema_ref: The schema ref to use for the definition reference schema
        metadata: Any other information you want to include with the schema, not used by pydantic-core
        serialization: Custom serialization schema
    """
    return _dict_not_none(
        type='definition-ref', schema_ref=schema_ref, ref=ref, metadata=metadata, serialization=serialization
    )


MYPY = False
# See https://github.com/python/mypy/issues/14034 for details, in summary mypy is extremely slow to process this
# union which kills performance not just for pydantic, but even for code using pydantic
if not MYPY:
    CoreSchema = Union[
        InvalidSchema,
        AnySchema,
        NoneSchema,
        BoolSchema,
        IntSchema,
        FloatSchema,
        DecimalSchema,
        StringSchema,
        BytesSchema,
        DateSchema,
        TimeSchema,
        DatetimeSchema,
        TimedeltaSchema,
        LiteralSchema,
        EnumSchema,
        IsInstanceSchema,
        IsSubclassSchema,
        CallableSchema,
        ListSchema,
        TupleSchema,
        SetSchema,
        FrozenSetSchema,
        GeneratorSchema,
        DictSchema,
        AfterValidatorFunctionSchema,
        BeforeValidatorFunctionSchema,
        WrapValidatorFunctionSchema,
        PlainValidatorFunctionSchema,
        WithDefaultSchema,
        NullableSchema,
        UnionSchema,
        TaggedUnionSchema,
        ChainSchema,
        LaxOrStrictSchema,
        JsonOrPythonSchema,
        TypedDictSchema,
        ModelFieldsSchema,
        ModelSchema,
        DataclassArgsSchema,
        DataclassSchema,
        ArgumentsSchema,
        ArgumentsV3Schema,
        CallSchema,
        CustomErrorSchema,
        JsonSchema,
        UrlSchema,
        MultiHostUrlSchema,
        DefinitionsSchema,
        DefinitionReferenceSchema,
        UuidSchema,
        ComplexSchema,
    ]
elif False:
    CoreSchema: TypeAlias = Mapping[str, Any]


# to update this, call `pytest -k test_core_schema_type_literal` and copy the output
CoreSchemaType = Literal[
    'invalid',
    'any',
    'none',
    'bool',
    'int',
    'float',
    'decimal',
    'str',
    'bytes',
    'date',
    'time',
    'datetime',
    'timedelta',
    'literal',
    'enum',
    'is-instance',
    'is-subclass',
    'callable',
    'list',
    'tuple',
    'set',
    'frozenset',
    'generator',
    'dict',
    'function-after',
    'function-before',
    'function-wrap',
    'function-plain',
    'default',
    'nullable',
    'union',
    'tagged-union',
    'chain',
    'lax-or-strict',
    'json-or-python',
    'typed-dict',
    'model-fields',
    'model',
    'dataclass-args',
    'dataclass',
    'arguments',
    'arguments-v3',
    'call',
    'custom-error',
    'json',
    'url',
    'multi-host-url',
    'definitions',
    'definition-ref',
    'uuid',
    'complex',
]

CoreSchemaFieldType = Literal['model-field', 'dataclass-field', 'typed-dict-field', 'computed-field']


# used in _pydantic_core.pyi::PydanticKnownError
# to update this, call `pytest -k test_all_errors` and copy the output
ErrorType = Literal[
    'no_such_attribute',
    'json_invalid',
    'json_type',
    'needs_python_object',
    'recursion_loop',
    'missing',
    'frozen_field',
    'frozen_instance',
    'extra_forbidden',
    'invalid_key',
    'get_attribute_error',
    'model_type',
    'model_attributes_type',
    'dataclass_type',
    'dataclass_exact_type',
    'none_required',
    'greater_than',
    'greater_than_equal',
    'less_than',
    'less_than_equal',
    'multiple_of',
    'finite_number',
    'too_short',
    'too_long',
    'iterable_type',
    'iteration_error',
    'string_type',
    'string_sub_type',
    'string_unicode',
    'string_too_short',
    'string_too_long',
    'string_pattern_mismatch',
    'enum',
    'dict_type',
    'mapping_type',
    'list_type',
    'tuple_type',
    'set_type',
    'set_item_not_hashable',
    'bool_type',
    'bool_parsing',
    'int_type',
    'int_parsing',
    'int_parsing_size',
    'int_from_float',
    'float_type',
    'float_parsing',
    'bytes_type',
    'bytes_too_short',
    'bytes_too_long',
    'bytes_invalid_encoding',
    'value_error',
    'assertion_error',
    'literal_error',
    'date_type',
    'date_parsing',
    'date_from_datetime_parsing',
    'date_from_datetime_inexact',
    'date_past',
    'date_future',
    'time_type',
    'time_parsing',
    'datetime_type',
    'datetime_parsing',
    'datetime_object_invalid',
    'datetime_from_date_parsing',
    'datetime_past',
    'datetime_future',
    'timezone_naive',
    'timezone_aware',
    'timezone_offset',
    'time_delta_type',
    'time_delta_parsing',
    'frozen_set_type',
    'is_instance_of',
    'is_subclass_of',
    'callable_type',
    'union_tag_invalid',
    'union_tag_not_found',
    'arguments_type',
    'missing_argument',
    'unexpected_keyword_argument',
    'missing_keyword_only_argument',
    'unexpected_positional_argument',
    'missing_positional_only_argument',
    'multiple_argument_values',
    'url_type',
    'url_parsing',
    'url_syntax_violation',
    'url_too_long',
    'url_scheme',
    'uuid_type',
    'uuid_parsing',
    'uuid_version',
    'decimal_type',
    'decimal_parsing',
    'decimal_max_digits',
    'decimal_max_places',
    'decimal_whole_digits',
    'complex_type',
    'complex_str_parsing',
]


def _dict_not_none(**kwargs: Any) -> Any:
    return {k: v for k, v in kwargs.items() if v is not None}


###############################################################################
# All this stuff is deprecated by #980 and will be removed eventually
# They're kept because some code external code will be using them


@deprecated('`field_before_validator_function` is deprecated, use `with_info_before_validator_function` instead.')
def field_before_validator_function(function: WithInfoValidatorFunction, field_name: str, schema: CoreSchema, **kwargs):
    warnings.warn(
        '`field_before_validator_function` is deprecated, use `with_info_before_validator_function` instead.',
        DeprecationWarning,
    )
    return with_info_before_validator_function(function, schema, field_name=field_name, **kwargs)


@deprecated('`general_before_validator_function` is deprecated, use `with_info_before_validator_function` instead.')
def general_before_validator_function(*args, **kwargs):
    warnings.warn(
        '`general_before_validator_function` is deprecated, use `with_info_before_validator_function` instead.',
        DeprecationWarning,
    )
    return with_info_before_validator_function(*args, **kwargs)


@deprecated('`field_after_validator_function` is deprecated, use `with_info_after_validator_function` instead.')
def field_after_validator_function(function: WithInfoValidatorFunction, field_name: str, schema: CoreSchema, **kwargs):
    warnings.warn(
        '`field_after_validator_function` is deprecated, use `with_info_after_validator_function` instead.',
        DeprecationWarning,
    )
    return with_info_after_validator_function(function, schema, field_name=field_name, **kwargs)


@deprecated('`general_after_validator_function` is deprecated, use `with_info_after_validator_function` instead.')
def general_after_validator_function(*args, **kwargs):
    warnings.warn(
        '`general_after_validator_function` is deprecated, use `with_info_after_validator_function` instead.',
        DeprecationWarning,
    )
    return with_info_after_validator_function(*args, **kwargs)


@deprecated('`field_wrap_validator_function` is deprecated, use `with_info_wrap_validator_function` instead.')
def field_wrap_validator_function(
    function: WithInfoWrapValidatorFunction, field_name: str, schema: CoreSchema, **kwargs
):
    warnings.warn(
        '`field_wrap_validator_function` is deprecated, use `with_info_wrap_validator_function` instead.',
        DeprecationWarning,
    )
    return with_info_wrap_validator_function(function, schema, field_name=field_name, **kwargs)


@deprecated('`general_wrap_validator_function` is deprecated, use `with_info_wrap_validator_function` instead.')
def general_wrap_validator_function(*args, **kwargs):
    warnings.warn(
        '`general_wrap_validator_function` is deprecated, use `with_info_wrap_validator_function` instead.',
        DeprecationWarning,
    )
    return with_info_wrap_validator_function(*args, **kwargs)


@deprecated('`field_plain_validator_function` is deprecated, use `with_info_plain_validator_function` instead.')
def field_plain_validator_function(function: WithInfoValidatorFunction, field_name: str, **kwargs):
    warnings.warn(
        '`field_plain_validator_function` is deprecated, use `with_info_plain_validator_function` instead.',
        DeprecationWarning,
    )
    return with_info_plain_validator_function(function, field_name=field_name, **kwargs)


@deprecated('`general_plain_validator_function` is deprecated, use `with_info_plain_validator_function` instead.')
def general_plain_validator_function(*args, **kwargs):
    warnings.warn(
        '`general_plain_validator_function` is deprecated, use `with_info_plain_validator_function` instead.',
        DeprecationWarning,
    )
    return with_info_plain_validator_function(*args, **kwargs)


_deprecated_import_lookup = {
    'FieldValidationInfo': ValidationInfo,
    'FieldValidatorFunction': WithInfoValidatorFunction,
    'GeneralValidatorFunction': WithInfoValidatorFunction,
    'FieldWrapValidatorFunction': WithInfoWrapValidatorFunction,
}

if TYPE_CHECKING:
    FieldValidationInfo = ValidationInfo


def __getattr__(attr_name: str) -> object:
    new_attr = _deprecated_import_lookup.get(attr_name)
    if new_attr is None:
        raise AttributeError(f"module 'pydantic_core' has no attribute '{attr_name}'")
    else:
        import warnings

        msg = f'`{attr_name}` is deprecated, use `{new_attr.__name__}` instead.'
        warnings.warn(msg, DeprecationWarning, stacklevel=1)
        return new_attr

# === NexusCore/openenv\Lib\site-packages\traitlets\traitlets.py ===
"""
A lightweight Traits like module.

This is designed to provide a lightweight, simple, pure Python version of
many of the capabilities of enthought.traits.  This includes:

* Validation
* Type specification with defaults
* Static and dynamic notification
* Basic predefined types
* An API that is similar to enthought.traits

We don't support:

* Delegation
* Automatic GUI generation
* A full set of trait types.  Most importantly, we don't provide container
  traits (list, dict, tuple) that can trigger notifications if their
  contents change.
* API compatibility with enthought.traits

There are also some important difference in our design:

* enthought.traits does not validate default values.  We do.

We choose to create this module because we need these capabilities, but
we need them to be pure Python so they work in all Python implementations,
including Jython and IronPython.

Inheritance diagram:

.. inheritance-diagram:: traitlets.traitlets
   :parts: 3
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
#
# Adapted from enthought.traits, Copyright (c) Enthought, Inc.,
# also under the terms of the Modified BSD License.

from __future__ import annotations

import contextlib
import enum
import inspect
import os
import re
import sys
import types
import typing as t
from ast import literal_eval

from .utils.bunch import Bunch
from .utils.descriptions import add_article, class_of, describe, repr_type
from .utils.getargspec import getargspec
from .utils.importstring import import_item
from .utils.sentinel import Sentinel
from .utils.warnings import deprecated_method, should_warn, warn

SequenceTypes = (list, tuple, set, frozenset)

# backward compatibility, use to differ between Python 2 and 3.
ClassTypes = (type,)

if t.TYPE_CHECKING:
    from typing_extensions import TypeVar
else:
    from typing import TypeVar

# exports:

__all__ = [
    "All",
    "Any",
    "BaseDescriptor",
    "Bool",
    "Bytes",
    "CBool",
    "CBytes",
    "CComplex",
    "CFloat",
    "CInt",
    "CLong",
    "CRegExp",
    "CUnicode",
    "Callable",
    "CaselessStrEnum",
    "ClassBasedTraitType",
    "Complex",
    "Container",
    "DefaultHandler",
    "Dict",
    "DottedObjectName",
    "Enum",
    "EventHandler",
    "Float",
    "ForwardDeclaredInstance",
    "ForwardDeclaredMixin",
    "ForwardDeclaredType",
    "FuzzyEnum",
    "HasDescriptors",
    "HasTraits",
    "Instance",
    "Int",
    "Integer",
    "List",
    "Long",
    "MetaHasDescriptors",
    "MetaHasTraits",
    "ObjectName",
    "ObserveHandler",
    "Set",
    "TCPAddress",
    "This",
    "TraitError",
    "TraitType",
    "Tuple",
    "Type",
    "Unicode",
    "Undefined",
    "Union",
    "UseEnum",
    "ValidateHandler",
    "default",
    "directional_link",
    "dlink",
    "link",
    "observe",
    "observe_compat",
    "parse_notifier_name",
    "validate",
]

# any TraitType subclass (that doesn't start with _) will be added automatically

# -----------------------------------------------------------------------------
# Basic classes
# -----------------------------------------------------------------------------


Undefined = Sentinel(
    "Undefined",
    "traitlets",
    """
Used in Traitlets to specify that no defaults are set in kwargs
""",
)

All = Sentinel(
    "All",
    "traitlets",
    """
Used in Traitlets to listen to all types of notification or to notifications
from all trait attributes.
""",
)

# Deprecated alias
NoDefaultSpecified = Undefined


class TraitError(Exception):
    pass


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------


def isidentifier(s: t.Any) -> bool:
    return t.cast(bool, s.isidentifier())


def _safe_literal_eval(s: str) -> t.Any:
    """Safely evaluate an expression

    Returns original string if eval fails.

    Use only where types are ambiguous.
    """
    try:
        return literal_eval(s)
    except (NameError, SyntaxError, ValueError):
        return s


def is_trait(t: t.Any) -> bool:
    """Returns whether the given value is an instance or subclass of TraitType."""
    return isinstance(t, TraitType) or (isinstance(t, type) and issubclass(t, TraitType))


def parse_notifier_name(names: Sentinel | str | t.Iterable[Sentinel | str]) -> t.Iterable[t.Any]:
    """Convert the name argument to a list of names.

    Examples
    --------
    >>> parse_notifier_name([])
    [traitlets.All]
    >>> parse_notifier_name("a")
    ['a']
    >>> parse_notifier_name(["a", "b"])
    ['a', 'b']
    >>> parse_notifier_name(All)
    [traitlets.All]
    """
    if names is All or isinstance(names, str):
        return [names]
    elif isinstance(names, Sentinel):
        raise TypeError("`names` must be either `All`, a str, or a list of strs.")
    else:
        if not names or All in names:
            return [All]
        for n in names:
            if not isinstance(n, str):
                raise TypeError(f"names must be strings, not {type(n).__name__}({n!r})")
        return names


class _SimpleTest:
    def __init__(self, value: t.Any) -> None:
        self.value = value

    def __call__(self, test: t.Any) -> bool:
        return bool(test == self.value)

    def __repr__(self) -> str:
        return "<SimpleTest(%r)" % self.value

    def __str__(self) -> str:
        return self.__repr__()


def getmembers(object: t.Any, predicate: t.Any = None) -> list[tuple[str, t.Any]]:
    """A safe version of inspect.getmembers that handles missing attributes.

    This is useful when there are descriptor based attributes that for
    some reason raise AttributeError even though they exist.  This happens
    in zope.interface with the __provides__ attribute.
    """
    results = []
    for key in dir(object):
        try:
            value = getattr(object, key)
        except AttributeError:
            pass
        else:
            if not predicate or predicate(value):
                results.append((key, value))
    results.sort()
    return results


def _validate_link(*tuples: t.Any) -> None:
    """Validate arguments for traitlet link functions"""
    for tup in tuples:
        if not len(tup) == 2:
            raise TypeError(
                "Each linked traitlet must be specified as (HasTraits, 'trait_name'), not %r" % t
            )
        obj, trait_name = tup
        if not isinstance(obj, HasTraits):
            raise TypeError("Each object must be HasTraits, not %r" % type(obj))
        if trait_name not in obj.traits():
            raise TypeError(f"{obj!r} has no trait {trait_name!r}")


class link:
    """Link traits from different objects together so they remain in sync.

    Parameters
    ----------
    source : (object / attribute name) pair
    target : (object / attribute name) pair
    transform: iterable with two callables (optional)
        Data transformation between source and target and target and source.

    Examples
    --------
    >>> class X(HasTraits):
    ...     value = Int()

    >>> src = X(value=1)
    >>> tgt = X(value=42)
    >>> c = link((src, "value"), (tgt, "value"))

    Setting source updates target objects:
    >>> src.value = 5
    >>> tgt.value
    5
    """

    updating = False

    def __init__(self, source: t.Any, target: t.Any, transform: t.Any = None) -> None:
        _validate_link(source, target)
        self.source, self.target = source, target
        self._transform, self._transform_inv = transform if transform else (lambda x: x,) * 2

        self.link()

    def link(self) -> None:
        try:
            setattr(
                self.target[0],
                self.target[1],
                self._transform(getattr(self.source[0], self.source[1])),
            )

        finally:
            self.source[0].observe(self._update_target, names=self.source[1])
            self.target[0].observe(self._update_source, names=self.target[1])

    @contextlib.contextmanager
    def _busy_updating(self) -> t.Any:
        self.updating = True
        try:
            yield
        finally:
            self.updating = False

    def _update_target(self, change: t.Any) -> None:
        if self.updating:
            return
        with self._busy_updating():
            setattr(self.target[0], self.target[1], self._transform(change.new))
            if getattr(self.source[0], self.source[1]) != change.new:
                raise TraitError(
                    f"Broken link {self}: the source value changed while updating " "the target."
                )

    def _update_source(self, change: t.Any) -> None:
        if self.updating:
            return
        with self._busy_updating():
            setattr(self.source[0], self.source[1], self._transform_inv(change.new))
            if getattr(self.target[0], self.target[1]) != change.new:
                raise TraitError(
                    f"Broken link {self}: the target value changed while updating " "the source."
                )

    def unlink(self) -> None:
        self.source[0].unobserve(self._update_target, names=self.source[1])
        self.target[0].unobserve(self._update_source, names=self.target[1])


class directional_link:
    """Link the trait of a source object with traits of target objects.

    Parameters
    ----------
    source : (object, attribute name) pair
    target : (object, attribute name) pair
    transform: callable (optional)
        Data transformation between source and target.

    Examples
    --------
    >>> class X(HasTraits):
    ...     value = Int()

    >>> src = X(value=1)
    >>> tgt = X(value=42)
    >>> c = directional_link((src, "value"), (tgt, "value"))

    Setting source updates target objects:
    >>> src.value = 5
    >>> tgt.value
    5

    Setting target does not update source object:
    >>> tgt.value = 6
    >>> src.value
    5

    """

    updating = False

    def __init__(self, source: t.Any, target: t.Any, transform: t.Any = None) -> None:
        self._transform = transform if transform else lambda x: x
        _validate_link(source, target)
        self.source, self.target = source, target
        self.link()

    def link(self) -> None:
        try:
            setattr(
                self.target[0],
                self.target[1],
                self._transform(getattr(self.source[0], self.source[1])),
            )
        finally:
            self.source[0].observe(self._update, names=self.source[1])

    @contextlib.contextmanager
    def _busy_updating(self) -> t.Any:
        self.updating = True
        try:
            yield
        finally:
            self.updating = False

    def _update(self, change: t.Any) -> None:
        if self.updating:
            return
        with self._busy_updating():
            setattr(self.target[0], self.target[1], self._transform(change.new))

    def unlink(self) -> None:
        self.source[0].unobserve(self._update, names=self.source[1])


dlink = directional_link


# -----------------------------------------------------------------------------
# Base Descriptor Class
# -----------------------------------------------------------------------------


class BaseDescriptor:
    """Base descriptor class

    Notes
    -----
    This implements Python's descriptor protocol.

    This class is the base class for all such descriptors.  The
    only magic we use is a custom metaclass for the main :class:`HasTraits`
    class that does the following:

    1. Sets the :attr:`name` attribute of every :class:`BaseDescriptor`
       instance in the class dict to the name of the attribute.
    2. Sets the :attr:`this_class` attribute of every :class:`BaseDescriptor`
       instance in the class dict to the *class* that declared the trait.
       This is used by the :class:`This` trait to allow subclasses to
       accept superclasses for :class:`This` values.
    """

    name: str | None = None
    this_class: type[HasTraits] | None = None

    def class_init(self, cls: type[HasTraits], name: str | None) -> None:
        """Part of the initialization which may depend on the underlying
        HasDescriptors class.

        It is typically overloaded for specific types.

        This method is called by :meth:`MetaHasDescriptors.__init__`
        passing the class (`cls`) and `name` under which the descriptor
        has been assigned.
        """
        self.this_class = cls
        self.name = name

    def subclass_init(self, cls: type[HasTraits]) -> None:
        # Instead of HasDescriptors.setup_instance calling
        # every instance_init, we opt in by default.
        # This gives descriptors a change to opt out for
        # performance reasons.
        # Because most traits do not need instance_init,
        # and it will otherwise be called for every HasTrait instance
        # being created, this otherwise gives a significant performance
        # pentalty. Most TypeTraits in traitlets opt out.
        cls._instance_inits.append(self.instance_init)

    def instance_init(self, obj: t.Any) -> None:
        """Part of the initialization which may depend on the underlying
        HasDescriptors instance.

        It is typically overloaded for specific types.

        This method is called by :meth:`HasTraits.__new__` and in the
        :meth:`BaseDescriptor.instance_init` method of descriptors holding
        other descriptors.
        """


G = TypeVar("G")
S = TypeVar("S")
T = TypeVar("T")


# Self from typing extension doesn't work well with mypy https://github.com/python/mypy/pull/14041
# see https://peps.python.org/pep-0673/#use-in-generic-classes
# Self = t.TypeVar("Self", bound="TraitType[Any, Any]")
if t.TYPE_CHECKING:
    from typing_extensions import Literal, Self

    K = TypeVar("K", default=str)
    V = TypeVar("V", default=t.Any)


# We use a type for the getter (G) and setter (G) because we allow
# for traits to cast (for instance CInt will use G=int, S=t.Any)
class TraitType(BaseDescriptor, t.Generic[G, S]):
    """A base class for all trait types."""

    metadata: dict[str, t.Any] = {}
    allow_none: bool = False
    read_only: bool = False
    info_text: str = "any value"
    default_value: t.Any = Undefined

    def __init__(
        self: TraitType[G, S],
        default_value: t.Any = Undefined,
        allow_none: bool = False,
        read_only: bool | None = None,
        help: str | None = None,
        config: t.Any = None,
        **kwargs: t.Any,
    ) -> None:
        """Declare a traitlet.

        If *allow_none* is True, None is a valid value in addition to any
        values that are normally valid. The default is up to the subclass.
        For most trait types, the default value for ``allow_none`` is False.

        If *read_only* is True, attempts to directly modify a trait attribute raises a TraitError.

        If *help* is a string, it documents the attribute's purpose.

        Extra metadata can be associated with the traitlet using the .tag() convenience method
        or by using the traitlet instance's .metadata dictionary.
        """
        if default_value is not Undefined:
            self.default_value = default_value
        if allow_none:
            self.allow_none = allow_none
        if read_only is not None:
            self.read_only = read_only
        self.help = help if help is not None else ""
        if self.help:
            # define __doc__ so that inspectors like autodoc find traits
            self.__doc__ = self.help

        if len(kwargs) > 0:
            stacklevel = 1
            f = inspect.currentframe()
            # count supers to determine stacklevel for warning
            assert f is not None
            while f.f_code.co_name == "__init__":
                stacklevel += 1
                f = f.f_back
                assert f is not None
            mod = f.f_globals.get("__name__") or ""
            pkg = mod.split(".", 1)[0]
            key = ("metadata-tag", pkg, *sorted(kwargs))
            if should_warn(key):
                warn(
                    f"metadata {kwargs} was set from the constructor. "
                    "With traitlets 4.1, metadata should be set using the .tag() method, "
                    "e.g., Int().tag(key1='value1', key2='value2')",
                    DeprecationWarning,
                    stacklevel=stacklevel,
                )
            if len(self.metadata) > 0:
                self.metadata = self.metadata.copy()
                self.metadata.update(kwargs)
            else:
                self.metadata = kwargs
        else:
            self.metadata = self.metadata.copy()
        if config is not None:
            self.metadata["config"] = config

        # We add help to the metadata during a deprecation period so that
        # code that looks for the help string there can find it.
        if help is not None:
            self.metadata["help"] = help

    def from_string(self, s: str) -> G | None:
        """Get a value from a config string

        such as an environment variable or CLI arguments.

        Traits can override this method to define their own
        parsing of config strings.

        .. seealso:: item_from_string

        .. versionadded:: 5.0
        """
        if self.allow_none and s == "None":
            return None
        return s  # type:ignore[return-value]

    def default(self, obj: t.Any = None) -> G | None:
        """The default generator for this trait

        Notes
        -----
        This method is registered to HasTraits classes during ``class_init``
        in the same way that dynamic defaults defined by ``@default`` are.
        """
        if self.default_value is not Undefined:
            return t.cast(G, self.default_value)
        elif hasattr(self, "make_dynamic_default"):
            return t.cast(G, self.make_dynamic_default())
        else:
            # Undefined will raise in TraitType.get
            return t.cast(G, self.default_value)

    def get_default_value(self) -> G | None:
        """DEPRECATED: Retrieve the static default value for this trait.
        Use self.default_value instead
        """
        warn(
            "get_default_value is deprecated in traitlets 4.0: use the .default_value attribute",
            DeprecationWarning,
            stacklevel=2,
        )
        return t.cast(G, self.default_value)

    def init_default_value(self, obj: t.Any) -> G | None:
        """DEPRECATED: Set the static default value for the trait type."""
        warn(
            "init_default_value is deprecated in traitlets 4.0, and may be removed in the future",
            DeprecationWarning,
            stacklevel=2,
        )
        value = self._validate(obj, self.default_value)
        obj._trait_values[self.name] = value
        return value

    def get(self, obj: HasTraits, cls: type[t.Any] | None = None) -> G | None:
        assert self.name is not None
        try:
            value = obj._trait_values[self.name]
        except KeyError:
            # Check for a dynamic initializer.
            default = obj.trait_defaults(self.name)
            if default is Undefined:
                warn(
                    "Explicit using of Undefined as the default value "
                    "is deprecated in traitlets 5.0, and may cause "
                    "exceptions in the future.",
                    DeprecationWarning,
                    stacklevel=2,
                )
            # Using a context manager has a large runtime overhead, so we
            # write out the obj.cross_validation_lock call here.
            _cross_validation_lock = obj._cross_validation_lock
            try:
                obj._cross_validation_lock = True
                value = self._validate(obj, default)
            finally:
                obj._cross_validation_lock = _cross_validation_lock
            obj._trait_values[self.name] = value
            obj._notify_observers(
                Bunch(
                    name=self.name,
                    value=value,
                    owner=obj,
                    type="default",
                )
            )
            return t.cast(G, value)
        except Exception as e:
            # This should never be reached.
            raise TraitError("Unexpected error in TraitType: default value not set properly") from e
        else:
            return t.cast(G, value)

    @t.overload
    def __get__(self, obj: None, cls: type[t.Any]) -> Self:
        ...

    @t.overload
    def __get__(self, obj: t.Any, cls: type[t.Any]) -> G:
        ...

    def __get__(self, obj: HasTraits | None, cls: type[t.Any]) -> Self | G:
        """Get the value of the trait by self.name for the instance.

        Default values are instantiated when :meth:`HasTraits.__new__`
        is called.  Thus by the time this method gets called either the
        default value or a user defined value (they called :meth:`__set__`)
        is in the :class:`HasTraits` instance.
        """
        if obj is None:
            return self
        else:
            return t.cast(G, self.get(obj, cls))  # the G should encode the Optional

    def set(self, obj: HasTraits, value: S) -> None:
        new_value = self._validate(obj, value)
        assert self.name is not None
        try:
            old_value = obj._trait_values[self.name]
        except KeyError:
            old_value = self.default_value

        obj._trait_values[self.name] = new_value
        try:
            silent = bool(old_value == new_value)
        except Exception:
            # if there is an error in comparing, default to notify
            silent = False
        if silent is not True:
            # we explicitly compare silent to True just in case the equality
            # comparison above returns something other than True/False
            obj._notify_trait(self.name, old_value, new_value)

    def __set__(self, obj: HasTraits, value: S) -> None:
        """Set the value of the trait by self.name for the instance.

        Values pass through a validation stage where errors are raised when
        impropper types, or types that cannot be coerced, are encountered.
        """
        if self.read_only:
            raise TraitError('The "%s" trait is read-only.' % self.name)
        self.set(obj, value)

    def _validate(self, obj: t.Any, value: t.Any) -> G | None:
        if value is None and self.allow_none:
            return value
        if hasattr(self, "validate"):
            value = self.validate(obj, value)
        if obj._cross_validation_lock is False:
            value = self._cross_validate(obj, value)
        return t.cast(G, value)

    def _cross_validate(self, obj: t.Any, value: t.Any) -> G | None:
        if self.name in obj._trait_validators:
            proposal = Bunch({"trait": self, "value": value, "owner": obj})
            value = obj._trait_validators[self.name](obj, proposal)
        elif hasattr(obj, "_%s_validate" % self.name):
            meth_name = "_%s_validate" % self.name
            cross_validate = getattr(obj, meth_name)
            deprecated_method(
                cross_validate,
                obj.__class__,
                meth_name,
                "use @validate decorator instead.",
            )
            value = cross_validate(value, self)
        return t.cast(G, value)

    def __or__(self, other: TraitType[t.Any, t.Any]) -> Union:
        if isinstance(other, Union):
            return Union([self, *other.trait_types])
        else:
            return Union([self, other])

    def info(self) -> str:
        return self.info_text

    def error(
        self,
        obj: HasTraits | None,
        value: t.Any,
        error: Exception | None = None,
        info: str | None = None,
    ) -> t.NoReturn:
        """Raise a TraitError

        Parameters
        ----------
        obj : HasTraits or None
            The instance which owns the trait. If not
            object is given, then an object agnostic
            error will be raised.
        value : any
            The value that caused the error.
        error : Exception (default: None)
            An error that was raised by a child trait.
            The arguments of this exception should be
            of the form ``(value, info, *traits)``.
            Where the ``value`` and ``info`` are the
            problem value, and string describing the
            expected value. The ``traits`` are a series
            of :class:`TraitType` instances that are
            "children" of this one (the first being
            the deepest).
        info : str (default: None)
            A description of the expected value. By
            default this is inferred from this trait's
            ``info`` method.
        """
        if error is not None:
            # handle nested error
            error.args += (self,)
            if self.name is not None:
                # this is the root trait that must format the final message
                chain = " of ".join(describe("a", t) for t in error.args[2:])
                if obj is not None:
                    error.args = (
                        "The '{}' trait of {} instance contains {} which "
                        "expected {}, not {}.".format(
                            self.name,
                            describe("an", obj),
                            chain,
                            error.args[1],
                            describe("the", error.args[0]),
                        ),
                    )
                else:
                    error.args = (
                        "The '{}' trait contains {} which " "expected {}, not {}.".format(
                            self.name,
                            chain,
                            error.args[1],
                            describe("the", error.args[0]),
                        ),
                    )
            raise error

        # this trait caused an error
        if self.name is None:
            # this is not the root trait
            raise TraitError(value, info or self.info(), self)

        # this is the root trait
        if obj is not None:
            e = "The '{}' trait of {} instance expected {}, not {}.".format(
                self.name,
                class_of(obj),
                info or self.info(),
                describe("the", value),
            )
        else:
            e = "The '{}' trait expected {}, not {}.".format(
                self.name,
                info or self.info(),
                describe("the", value),
            )
        raise TraitError(e)

    def get_metadata(self, key: str, default: t.Any = None) -> t.Any:
        """DEPRECATED: Get a metadata value.

        Use .metadata[key] or .metadata.get(key, default) instead.
        """
        if key == "help":
            msg = "use the instance .help string directly, like x.help"
        else:
            msg = "use the instance .metadata dictionary directly, like x.metadata[key] or x.metadata.get(key, default)"
        warn("Deprecated in traitlets 4.1, " + msg, DeprecationWarning, stacklevel=2)
        return self.metadata.get(key, default)

    def set_metadata(self, key: str, value: t.Any) -> None:
        """DEPRECATED: Set a metadata key/value.

        Use .metadata[key] = value instead.
        """
        if key == "help":
            msg = "use the instance .help string directly, like x.help = value"
        else:
            msg = "use the instance .metadata dictionary directly, like x.metadata[key] = value"
        warn("Deprecated in traitlets 4.1, " + msg, DeprecationWarning, stacklevel=2)
        self.metadata[key] = value

    def tag(self, **metadata: t.Any) -> Self:
        """Sets metadata and returns self.

        This allows convenient metadata tagging when initializing the trait, such as:

        Examples
        --------
        >>> Int(0).tag(config=True, sync=True)
        <traitlets.traitlets.Int object at ...>

        """
        maybe_constructor_keywords = set(metadata.keys()).intersection(
            {"help", "allow_none", "read_only", "default_value"}
        )
        if maybe_constructor_keywords:
            warn(
                "The following attributes are set in using `tag`, but seem to be constructor keywords arguments: %s "
                % maybe_constructor_keywords,
                UserWarning,
                stacklevel=2,
            )

        self.metadata.update(metadata)
        return self

    def default_value_repr(self) -> str:
        return repr(self.default_value)


# -----------------------------------------------------------------------------
# The HasTraits implementation
# -----------------------------------------------------------------------------


class _CallbackWrapper:
    """An object adapting a on_trait_change callback into an observe callback.

    The comparison operator __eq__ is implemented to enable removal of wrapped
    callbacks.
    """

    def __init__(self, cb: t.Any) -> None:
        self.cb = cb
        # Bound methods have an additional 'self' argument.
        offset = -1 if isinstance(self.cb, types.MethodType) else 0
        self.nargs = len(getargspec(cb)[0]) + offset
        if self.nargs > 4:
            raise TraitError("a trait changed callback must have 0-4 arguments.")

    def __eq__(self, other: object) -> bool:
        # The wrapper is equal to the wrapped element
        if isinstance(other, _CallbackWrapper):
            return bool(self.cb == other.cb)
        else:
            return bool(self.cb == other)

    def __call__(self, change: Bunch) -> None:
        # The wrapper is callable
        if self.nargs == 0:
            self.cb()
        elif self.nargs == 1:
            self.cb(change.name)
        elif self.nargs == 2:
            self.cb(change.name, change.new)
        elif self.nargs == 3:
            self.cb(change.name, change.old, change.new)
        elif self.nargs == 4:
            self.cb(change.name, change.old, change.new, change.owner)


def _callback_wrapper(cb: t.Any) -> _CallbackWrapper:
    if isinstance(cb, _CallbackWrapper):
        return cb
    else:
        return _CallbackWrapper(cb)


class MetaHasDescriptors(type):
    """A metaclass for HasDescriptors.

    This metaclass makes sure that any TraitType class attributes are
    instantiated and sets their name attribute.
    """

    def __new__(
        mcls: type[MetaHasDescriptors],
        name: str,
        bases: tuple[type, ...],
        classdict: dict[str, t.Any],
        **kwds: t.Any,
    ) -> MetaHasDescriptors:
        """Create the HasDescriptors class."""
        for k, v in classdict.items():
            # ----------------------------------------------------------------
            # Support of deprecated behavior allowing for TraitType types
            # to be used instead of TraitType instances.
            if inspect.isclass(v) and issubclass(v, TraitType):
                warn(
                    "Traits should be given as instances, not types (for example, `Int()`, not `Int`)."
                    " Passing types is deprecated in traitlets 4.1.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                classdict[k] = v()
            # ----------------------------------------------------------------

        return super().__new__(mcls, name, bases, classdict, **kwds)

    def __init__(
        cls, name: str, bases: tuple[type, ...], classdict: dict[str, t.Any], **kwds: t.Any
    ) -> None:
        """Finish initializing the HasDescriptors class."""
        super().__init__(name, bases, classdict, **kwds)
        cls.setup_class(classdict)

    def setup_class(cls: MetaHasDescriptors, classdict: dict[str, t.Any]) -> None:
        """Setup descriptor instance on the class

        This sets the :attr:`this_class` and :attr:`name` attributes of each
        BaseDescriptor in the class dict of the newly created ``cls`` before
        calling their :attr:`class_init` method.
        """
        cls._descriptors = []
        cls._instance_inits: list[t.Any] = []
        for k, v in classdict.items():
            if isinstance(v, BaseDescriptor):
                v.class_init(cls, k)  # type:ignore[arg-type]

        for _, v in getmembers(cls):
            if isinstance(v, BaseDescriptor):
                v.subclass_init(cls)  # type:ignore[arg-type]
                cls._descriptors.append(v)


class MetaHasTraits(MetaHasDescriptors):
    """A metaclass for HasTraits."""

    def setup_class(cls: MetaHasTraits, classdict: dict[str, t.Any]) -> None:
        # for only the current class
        cls._trait_default_generators: dict[str, t.Any] = {}
        # also looking at base classes
        cls._all_trait_default_generators = {}
        cls._traits = {}
        cls._static_immutable_initial_values = {}

        super().setup_class(classdict)

        mro = cls.mro()

        for name in dir(cls):
            # Some descriptors raise AttributeError like zope.interface's
            # __provides__ attributes even though they exist.  This causes
            # AttributeErrors even though they are listed in dir(cls).
            try:
                value = getattr(cls, name)
            except AttributeError:
                continue
            if isinstance(value, TraitType):
                cls._traits[name] = value
                trait = value
                default_method_name = "_%s_default" % name
                mro_trait = mro
                try:
                    mro_trait = mro[: mro.index(trait.this_class) + 1]  # type:ignore[arg-type]
                except ValueError:
                    # this_class not in mro
                    pass
                for c in mro_trait:
                    if default_method_name in c.__dict__:
                        cls._all_trait_default_generators[name] = c.__dict__[default_method_name]
                        break
                    if name in c.__dict__.get("_trait_default_generators", {}):
                        cls._all_trait_default_generators[name] = c._trait_default_generators[name]  # type: ignore[attr-defined]
                        break
                else:
                    # We don't have a dynamic default generator using @default etc.
                    # Now if the default value is not dynamic and immutable (string, number)
                    # and does not require any validation, we keep them in a dict
                    # of initial values to speed up instance creation.
                    # This is a very specific optimization, but a very common scenario in
                    # for instance ipywidgets.
                    none_ok = trait.default_value is None and trait.allow_none
                    if (
                        type(trait) in [CInt, Int]
                        and trait.min is None  # type: ignore[attr-defined]
                        and trait.max is None  # type: ignore[attr-defined]
                        and (isinstance(trait.default_value, int) or none_ok)
                    ):
                        cls._static_immutable_initial_values[name] = trait.default_value
                    elif (
                        type(trait) in [CFloat, Float]
                        and trait.min is None  # type: ignore[attr-defined]
                        and trait.max is None  # type: ignore[attr-defined]
                        and (isinstance(trait.default_value, float) or none_ok)
                    ):
                        cls._static_immutable_initial_values[name] = trait.default_value
                    elif type(trait) in [CBool, Bool] and (
                        isinstance(trait.default_value, bool) or none_ok
                    ):
                        cls._static_immutable_initial_values[name] = trait.default_value
                    elif type(trait) in [CUnicode, Unicode] and (
                        isinstance(trait.default_value, str) or none_ok
                    ):
                        cls._static_immutable_initial_values[name] = trait.default_value
                    elif type(trait) == Any and (
                        isinstance(trait.default_value, (str, int, float, bool)) or none_ok
                    ):
                        cls._static_immutable_initial_values[name] = trait.default_value
                    elif type(trait) == Union and trait.default_value is None:
                        cls._static_immutable_initial_values[name] = None
                    elif (
                        isinstance(trait, Instance)
                        and trait.default_args is None
                        and trait.default_kwargs is None
                        and trait.allow_none
                    ):
                        cls._static_immutable_initial_values[name] = None

                    # we always add it, because a class may change when we call add_trait
                    # and then the instance may not have all the _static_immutable_initial_values
                    cls._all_trait_default_generators[name] = trait.default


def observe(*names: Sentinel | str, type: str = "change") -> ObserveHandler:
    """A decorator which can be used to observe Traits on a class.

    The handler passed to the decorator will be called with one ``change``
    dict argument. The change dictionary at least holds a 'type' key and a
    'name' key, corresponding respectively to the type of notification and the
    name of the attribute that triggered the notification.

    Other keys may be passed depending on the value of 'type'. In the case
    where type is 'change', we also have the following keys:
    * ``owner`` : the HasTraits instance
    * ``old`` : the old value of the modified trait attribute
    * ``new`` : the new value of the modified trait attribute
    * ``name`` : the name of the modified trait attribute.

    Parameters
    ----------
    *names
        The str names of the Traits to observe on the object.
    type : str, kwarg-only
        The type of event to observe (e.g. 'change')
    """
    if not names:
        raise TypeError("Please specify at least one trait name to observe.")
    for name in names:
        if name is not All and not isinstance(name, str):
            raise TypeError("trait names to observe must be strings or All, not %r" % name)
    return ObserveHandler(names, type=type)


def observe_compat(func: FuncT) -> FuncT:
    """Backward-compatibility shim decorator for observers

    Use with:

    @observe('name')
    @observe_compat
    def _foo_changed(self, change):
        ...

    With this, `super()._foo_changed(self, name, old, new)` in subclasses will still work.
    Allows adoption of new observer API without breaking subclasses that override and super.
    """

    def compatible_observer(
        self: t.Any, change_or_name: str, old: t.Any = Undefined, new: t.Any = Undefined
    ) -> t.Any:
        if isinstance(change_or_name, dict):  # type:ignore[unreachable]
            change = Bunch(change_or_name)  # type:ignore[unreachable]
        else:
            clsname = self.__class__.__name__
            warn(
                f"A parent of {clsname}._{change_or_name}_changed has adopted the new (traitlets 4.1) @observe(change) API",
                DeprecationWarning,
                stacklevel=2,
            )
            change = Bunch(
                type="change",
                old=old,
                new=new,
                name=change_or_name,
                owner=self,
            )
        return func(self, change)

    return t.cast(FuncT, compatible_observer)


def validate(*names: Sentinel | str) -> ValidateHandler:
    """A decorator to register cross validator of HasTraits object's state
    when a Trait is set.

    The handler passed to the decorator must have one ``proposal`` dict argument.
    The proposal dictionary must hold the following keys:

    * ``owner`` : the HasTraits instance
    * ``value`` : the proposed value for the modified trait attribute
    * ``trait`` : the TraitType instance associated with the attribute

    Parameters
    ----------
    *names
        The str names of the Traits to validate.

    Notes
    -----
    Since the owner has access to the ``HasTraits`` instance via the 'owner' key,
    the registered cross validator could potentially make changes to attributes
    of the ``HasTraits`` instance. However, we recommend not to do so. The reason
    is that the cross-validation of attributes may run in arbitrary order when
    exiting the ``hold_trait_notifications`` context, and such changes may not
    commute.
    """
    if not names:
        raise TypeError("Please specify at least one trait name to validate.")
    for name in names:
        if name is not All and not isinstance(name, str):
            raise TypeError("trait names to validate must be strings or All, not %r" % name)
    return ValidateHandler(names)


def default(name: str) -> DefaultHandler:
    """A decorator which assigns a dynamic default for a Trait on a HasTraits object.

    Parameters
    ----------
    name
        The str name of the Trait on the object whose default should be generated.

    Notes
    -----
    Unlike observers and validators which are properties of the HasTraits
    instance, default value generators are class-level properties.

    Besides, default generators are only invoked if they are registered in
    subclasses of `this_type`.

    ::

        class A(HasTraits):
            bar = Int()

            @default('bar')
            def get_bar_default(self):
                return 11

        class B(A):
            bar = Float()  # This trait ignores the default generator defined in
                           # the base class A

        class C(B):

            @default('bar')
            def some_other_default(self):  # This default generator should not be
                return 3.0                 # ignored since it is defined in a
                                           # class derived from B.a.this_class.
    """
    if not isinstance(name, str):
        raise TypeError("Trait name must be a string or All, not %r" % name)
    return DefaultHandler(name)


FuncT = t.TypeVar("FuncT", bound=t.Callable[..., t.Any])


class EventHandler(BaseDescriptor):
    def _init_call(self, func: FuncT) -> EventHandler:
        self.func = func
        return self

    @t.overload
    def __call__(self, func: FuncT, *args: t.Any, **kwargs: t.Any) -> FuncT:
        ...

    @t.overload
    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        ...

    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        """Pass `*args` and `**kwargs` to the handler's function if it exists."""
        if hasattr(self, "func"):
            return self.func(*args, **kwargs)
        else:
            return self._init_call(*args, **kwargs)

    def __get__(self, inst: t.Any, cls: t.Any = None) -> types.MethodType | EventHandler:
        if inst is None:
            return self
        return types.MethodType(self.func, inst)


class ObserveHandler(EventHandler):
    def __init__(self, names: tuple[Sentinel | str, ...], type: str = "") -> None:
        self.trait_names = names
        self.type = type

    def instance_init(self, inst: HasTraits) -> None:
        inst.observe(self, self.trait_names, type=self.type)


class ValidateHandler(EventHandler):
    def __init__(self, names: tuple[Sentinel | str, ...]) -> None:
        self.trait_names = names

    def instance_init(self, inst: HasTraits) -> None:
        inst._register_validator(self, self.trait_names)


class DefaultHandler(EventHandler):
    def __init__(self, name: str) -> None:
        self.trait_name = name

    def class_init(self, cls: type[HasTraits], name: str | None) -> None:
        super().class_init(cls, name)
        cls._trait_default_generators[self.trait_name] = self


class HasDescriptors(metaclass=MetaHasDescriptors):
    """The base class for all classes that have descriptors."""

    def __new__(*args: t.Any, **kwargs: t.Any) -> t.Any:
        # Pass cls as args[0] to allow "cls" as keyword argument
        cls = args[0]
        args = args[1:]

        # This is needed because object.__new__ only accepts
        # the cls argument.
        new_meth = super(HasDescriptors, cls).__new__
        if new_meth is object.__new__:
            inst = new_meth(cls)
        else:
            inst = new_meth(cls, *args, **kwargs)
        inst.setup_instance(*args, **kwargs)
        return inst

    def setup_instance(*args: t.Any, **kwargs: t.Any) -> None:
        """
        This is called **before** self.__init__ is called.
        """
        # Pass self as args[0] to allow "self" as keyword argument
        self = args[0]
        args = args[1:]

        self._cross_validation_lock = False
        cls = self.__class__
        # Let descriptors performance initialization when a HasDescriptor
        # instance is created. This allows registration of observers and
        # default creations or other bookkeepings.
        # Note that descriptors can opt-out of this behavior by overriding
        # subclass_init.
        for init in cls._instance_inits:
            init(self)


class HasTraits(HasDescriptors, metaclass=MetaHasTraits):
    _trait_values: dict[str, t.Any]
    _static_immutable_initial_values: dict[str, t.Any]
    _trait_notifiers: dict[str | Sentinel, t.Any]
    _trait_validators: dict[str | Sentinel, t.Any]
    _cross_validation_lock: bool
    _traits: dict[str, t.Any]
    _all_trait_default_generators: dict[str, t.Any]

    def setup_instance(*args: t.Any, **kwargs: t.Any) -> None:
        # Pass self as args[0] to allow "self" as keyword argument
        self = args[0]
        args = args[1:]

        # although we'd prefer to set only the initial values not present
        # in kwargs, we will overwrite them in `__init__`, and simply making
        # a copy of a dict is faster than checking for each key.
        self._trait_values = self._static_immutable_initial_values.copy()
        self._trait_notifiers = {}
        self._trait_validators = {}
        self._cross_validation_lock = False
        super(HasTraits, self).setup_instance(*args, **kwargs)

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        # Allow trait values to be set using keyword arguments.
        # We need to use setattr for this to trigger validation and
        # notifications.
        super_args = args
        super_kwargs = {}

        if kwargs:
            # this is a simplified (and faster) version of
            # the hold_trait_notifications(self) context manager
            def ignore(change: Bunch) -> None:
                pass

            self.notify_change = ignore  # type:ignore[method-assign]
            self._cross_validation_lock = True
            changes = {}
            for key, value in kwargs.items():
                if self.has_trait(key):
                    setattr(self, key, value)
                    changes[key] = Bunch(
                        name=key,
                        old=None,
                        new=value,
                        owner=self,
                        type="change",
                    )
                else:
                    # passthrough args that don't set traits to super
                    super_kwargs[key] = value
            # notify and cross validate all trait changes that were set in kwargs
            changed = set(kwargs) & set(self._traits)
            for key in changed:
                value = self._traits[key]._cross_validate(self, getattr(self, key))
                self.set_trait(key, value)
                changes[key]["new"] = value
            self._cross_validation_lock = False
            # Restore method retrieval from class
            del self.notify_change
            for key in changed:
                self.notify_change(changes[key])

        try:
            super().__init__(*super_args, **super_kwargs)
        except TypeError as e:
            arg_s_list = [repr(arg) for arg in super_args]
            for k, v in super_kwargs.items():
                arg_s_list.append(f"{k}={v!r}")
            arg_s = ", ".join(arg_s_list)
            warn(
                "Passing unrecognized arguments to super({classname}).__init__({arg_s}).\n"
                "{error}\n"
                "This is deprecated in traitlets 4.2."
                "This error will be raised in a future release of traitlets.".format(
                    arg_s=arg_s,
                    classname=self.__class__.__name__,
                    error=e,
                ),
                DeprecationWarning,
                stacklevel=2,
            )

    def __getstate__(self) -> dict[str, t.Any]:
        d = self.__dict__.copy()
        # event handlers stored on an instance are
        # expected to be reinstantiated during a
        # recall of instance_init during __setstate__
        d["_trait_notifiers"] = {}
        d["_trait_validators"] = {}
        d["_trait_values"] = self._trait_values.copy()
        d["_cross_validation_lock"] = False  # FIXME: raise if cloning locked!

        return d

    def __setstate__(self, state: dict[str, t.Any]) -> None:
        self.__dict__ = state.copy()

        # event handlers are reassigned to self
        cls = self.__class__
        for key in dir(cls):
            # Some descriptors raise AttributeError like zope.interface's
            # __provides__ attributes even though they exist.  This causes
            # AttributeErrors even though they are listed in dir(cls).
            try:
                value = getattr(cls, key)
            except AttributeError:
                pass
            else:
                if isinstance(value, EventHandler):
                    value.instance_init(self)

    @property
    @contextlib.contextmanager
    def cross_validation_lock(self) -> t.Any:
        """
        A contextmanager for running a block with our cross validation lock set
        to True.

        At the end of the block, the lock's value is restored to its value
        prior to entering the block.
        """
        if self._cross_validation_lock:
            yield
            return
        else:
            try:
                self._cross_validation_lock = True
                yield
            finally:
                self._cross_validation_lock = False

    @contextlib.contextmanager
    def hold_trait_notifications(self) -> t.Any:
        """Context manager for bundling trait change notifications and cross
        validation.

        Use this when doing multiple trait assignments (init, config), to avoid
        race conditions in trait notifiers requesting other trait values.
        All trait notifications will fire after all values have been assigned.
        """
        if self._cross_validation_lock:
            yield
            return
        else:
            cache: dict[str, list[Bunch]] = {}

            def compress(past_changes: list[Bunch] | None, change: Bunch) -> list[Bunch]:
                """Merges the provided change with the last if possible."""
                if past_changes is None:
                    return [change]
                else:
                    if past_changes[-1]["type"] == "change" and change.type == "change":
                        past_changes[-1]["new"] = change.new
                    else:
                        # In case of changes other than 'change', append the notification.
                        past_changes.append(change)
                    return past_changes

            def hold(change: Bunch) -> None:
                name = change.name
                cache[name] = compress(cache.get(name), change)

            try:
                # Replace notify_change with `hold`, caching and compressing
                # notifications, disable cross validation and yield.
                self.notify_change = hold  # type:ignore[method-assign]
                self._cross_validation_lock = True
                yield
                # Cross validate final values when context is released.
                for name in list(cache.keys()):
                    trait = getattr(self.__class__, name)
                    value = trait._cross_validate(self, getattr(self, name))
                    self.set_trait(name, value)
            except TraitError as e:
                # Roll back in case of TraitError during final cross validation.
                self.notify_change = lambda x: None  # type:ignore[method-assign, assignment]  # noqa: ARG005
                for name, changes in cache.items():
                    for change in changes[::-1]:
                        # TODO: Separate in a rollback function per notification type.
                        if change.type == "change":
                            if change.old is not Undefined:
                                self.set_trait(name, change.old)
                            else:
                                self._trait_values.pop(name)
                cache = {}
                raise e
            finally:
                self._cross_validation_lock = False
                # Restore method retrieval from class
                del self.notify_change

                # trigger delayed notifications
                for changes in cache.values():
                    for change in changes:
                        self.notify_change(change)

    def _notify_trait(self, name: str, old_value: t.Any, new_value: t.Any) -> None:
        self.notify_change(
            Bunch(
                name=name,
                old=old_value,
                new=new_value,
                owner=self,
                type="change",
            )
        )

    def notify_change(self, change: Bunch) -> None:
        """Notify observers of a change event"""
        return self._notify_observers(change)

    def _notify_observers(self, event: Bunch) -> None:
        """Notify observers of any event"""
        if not isinstance(event, Bunch):
            # cast to bunch if given a dict
            event = Bunch(event)  # type:ignore[unreachable]
        name, type = event["name"], event["type"]

        callables = []
        if name in self._trait_notifiers:
            callables.extend(self._trait_notifiers.get(name, {}).get(type, []))
            callables.extend(self._trait_notifiers.get(name, {}).get(All, []))
        if All in self._trait_notifiers:
            callables.extend(self._trait_notifiers.get(All, {}).get(type, []))
            callables.extend(self._trait_notifiers.get(All, {}).get(All, []))

        # Now static ones
        magic_name = "_%s_changed" % name
        if event["type"] == "change" and hasattr(self, magic_name):
            class_value = getattr(self.__class__, magic_name)
            if not isinstance(class_value, ObserveHandler):
                deprecated_method(
                    class_value,
                    self.__class__,
                    magic_name,
                    "use @observe and @unobserve instead.",
                )
                cb = getattr(self, magic_name)
                # Only append the magic method if it was not manually registered
                if cb not in callables:
                    callables.append(_callback_wrapper(cb))

        # Call them all now
        # Traits catches and logs errors here.  I allow them to raise
        for c in callables:
            # Bound methods have an additional 'self' argument.

            if isinstance(c, _CallbackWrapper):
                c = c.__call__
            elif isinstance(c, EventHandler) and c.name is not None:
                c = getattr(self, c.name)

            c(event)

    def _add_notifiers(
        self, handler: t.Callable[..., t.Any], name: Sentinel | str, type: str | Sentinel
    ) -> None:
        if name not in self._trait_notifiers:
            nlist: list[t.Any] = []
            self._trait_notifiers[name] = {type: nlist}
        else:
            if type not in self._trait_notifiers[name]:
                nlist = []
                self._trait_notifiers[name][type] = nlist
            else:
                nlist = self._trait_notifiers[name][type]
        if handler not in nlist:
            nlist.append(handler)

    def _remove_notifiers(
        self, handler: t.Callable[..., t.Any] | None, name: Sentinel | str, type: str | Sentinel
    ) -> None:
        try:
            if handler is None:
                del self._trait_notifiers[name][type]
            else:
                self._trait_notifiers[name][type].remove(handler)
        except KeyError:
            pass

    def on_trait_change(
        self,
        handler: EventHandler | None = None,
        name: Sentinel | str | None = None,
        remove: bool = False,
    ) -> None:
        """DEPRECATED: Setup a handler to be called when a trait changes.

        This is used to setup dynamic notifications of trait changes.

        Static handlers can be created by creating methods on a HasTraits
        subclass with the naming convention '_[traitname]_changed'.  Thus,
        to create static handler for the trait 'a', create the method
        _a_changed(self, name, old, new) (fewer arguments can be used, see
        below).

        If `remove` is True and `handler` is not specified, all change
        handlers for the specified name are uninstalled.

        Parameters
        ----------
        handler : callable, None
            A callable that is called when a trait changes.  Its
            signature can be handler(), handler(name), handler(name, new),
            handler(name, old, new), or handler(name, old, new, self).
        name : list, str, None
            If None, the handler will apply to all traits.  If a list
            of str, handler will apply to all names in the list.  If a
            str, the handler will apply just to that name.
        remove : bool
            If False (the default), then install the handler.  If True
            then unintall it.
        """
        warn(
            "on_trait_change is deprecated in traitlets 4.1: use observe instead",
            DeprecationWarning,
            stacklevel=2,
        )
        if name is None:
            name = All
        if remove:
            self.unobserve(_callback_wrapper(handler), names=name)
        else:
            self.observe(_callback_wrapper(handler), names=name)

    def observe(
        self,
        handler: t.Callable[..., t.Any],
        names: Sentinel | str | t.Iterable[Sentinel | str] = All,
        type: Sentinel | str = "change",
    ) -> None:
        """Setup a handler to be called when a trait changes.

        This is used to setup dynamic notifications of trait changes.

        Parameters
        ----------
        handler : callable
            A callable that is called when a trait changes. Its
            signature should be ``handler(change)``, where ``change`` is a
            dictionary. The change dictionary at least holds a 'type' key.
            * ``type``: the type of notification.
            Other keys may be passed depending on the value of 'type'. In the
            case where type is 'change', we also have the following keys:
            * ``owner`` : the HasTraits instance
            * ``old`` : the old value of the modified trait attribute
            * ``new`` : the new value of the modified trait attribute
            * ``name`` : the name of the modified trait attribute.
        names : list, str, All
            If names is All, the handler will apply to all traits.  If a list
            of str, handler will apply to all names in the list.  If a
            str, the handler will apply just to that name.
        type : str, All (default: 'change')
            The type of notification to filter by. If equal to All, then all
            notifications are passed to the observe handler.
        """
        for name in parse_notifier_name(names):
            self._add_notifiers(handler, name, type)

    def unobserve(
        self,
        handler: t.Callable[..., t.Any],
        names: Sentinel | str | t.Iterable[Sentinel | str] = All,
        type: Sentinel | str = "change",
    ) -> None:
        """Remove a trait change handler.

        This is used to unregister handlers to trait change notifications.

        Parameters
        ----------
        handler : callable
            The callable called when a trait attribute changes.
        names : list, str, All (default: All)
            The names of the traits for which the specified handler should be
            uninstalled. If names is All, the specified handler is uninstalled
            from the list of notifiers corresponding to all changes.
        type : str or All (default: 'change')
            The type of notification to filter by. If All, the specified handler
            is uninstalled from the list of notifiers corresponding to all types.
        """
        for name in parse_notifier_name(names):
            self._remove_notifiers(handler, name, type)

    def unobserve_all(self, name: str | t.Any = All) -> None:
        """Remove trait change handlers of any type for the specified name.
        If name is not specified, removes all trait notifiers."""
        if name is All:
            self._trait_notifiers = {}
        else:
            try:
                del self._trait_notifiers[name]
            except KeyError:
                pass

    def _register_validator(
        self, handler: t.Callable[..., None], names: tuple[str | Sentinel, ...]
    ) -> None:
        """Setup a handler to be called when a trait should be cross validated.

        This is used to setup dynamic notifications for cross-validation.

        If a validator is already registered for any of the provided names, a
        TraitError is raised and no new validator is registered.

        Parameters
        ----------
        handler : callable
            A callable that is called when the given trait is cross-validated.
            Its signature is handler(proposal), where proposal is a Bunch (dictionary with attribute access)
            with the following attributes/keys:
                * ``owner`` : the HasTraits instance
                * ``value`` : the proposed value for the modified trait attribute
                * ``trait`` : the TraitType instance associated with the attribute
        names : List of strings
            The names of the traits that should be cross-validated
        """
        for name in names:
            magic_name = "_%s_validate" % name
            if hasattr(self, magic_name):
                class_value = getattr(self.__class__, magic_name)
                if not isinstance(class_value, ValidateHandler):
                    deprecated_method(
                        class_value,
                        self.__class__,
                        magic_name,
                        "use @validate decorator instead.",
                    )
        for name in names:
            self._trait_validators[name] = handler

    def add_traits(self, **traits: t.Any) -> None:
        """Dynamically add trait attributes to the HasTraits instance."""
        cls = self.__class__
        attrs = {"__module__": cls.__module__}
        if hasattr(cls, "__qualname__"):
            # __qualname__ introduced in Python 3.3 (see PEP 3155)
            attrs["__qualname__"] = cls.__qualname__
        attrs.update(traits)
        self.__class__ = type(cls.__name__, (cls,), attrs)
        for trait in traits.values():
            trait.instance_init(self)

    def set_trait(self, name: str, value: t.Any) -> None:
        """Forcibly sets trait attribute, including read-only attributes."""
        cls = self.__class__
        if not self.has_trait(name):
            raise TraitError(f"Class {cls.__name__} does not have a trait named {name}")
        getattr(cls, name).set(self, value)

    @classmethod
    def class_trait_names(cls: type[HasTraits], **metadata: t.Any) -> list[str]:
        """Get a list of all the names of this class' traits.

        This method is just like the :meth:`trait_names` method,
        but is unbound.
        """
        return list(cls.class_traits(**metadata))

    @classmethod
    def class_traits(cls: type[HasTraits], **metadata: t.Any) -> dict[str, TraitType[t.Any, t.Any]]:
        """Get a ``dict`` of all the traits of this class.  The dictionary
        is keyed on the name and the values are the TraitType objects.

        This method is just like the :meth:`traits` method, but is unbound.

        The TraitTypes returned don't know anything about the values
        that the various HasTrait's instances are holding.

        The metadata kwargs allow functions to be passed in which
        filter traits based on metadata values.  The functions should
        take a single value as an argument and return a boolean.  If
        any function returns False, then the trait is not included in
        the output.  If a metadata key doesn't exist, None will be passed
        to the function.
        """
        traits = cls._traits.copy()

        if len(metadata) == 0:
            return traits

        result = {}
        for name, trait in traits.items():
            for meta_name, meta_eval in metadata.items():
                if not callable(meta_eval):
                    meta_eval = _SimpleTest(meta_eval)
                if not meta_eval(trait.metadata.get(meta_name, None)):
                    break
            else:
                result[name] = trait

        return result

    @classmethod
    def class_own_traits(
        cls: type[HasTraits], **metadata: t.Any
    ) -> dict[str, TraitType[t.Any, t.Any]]:
        """Get a dict of all the traitlets defined on this class, not a parent.

        Works like `class_traits`, except for excluding traits from parents.
        """
        sup = super(cls, cls)
        return {
            n: t
            for (n, t) in cls.class_traits(**metadata).items()
            if getattr(sup, n, None) is not t
        }

    def has_trait(self, name: str) -> bool:
        """Returns True if the object has a trait with the specified name."""
        return name in self._traits

    def trait_has_value(self, name: str) -> bool:
        """Returns True if the specified trait has a value.

        This will return false even if ``getattr`` would return a
        dynamically generated default value. These default values
        will be recognized as existing only after they have been
        generated.

        Example

        .. code-block:: python

            class MyClass(HasTraits):
                i = Int()


            mc = MyClass()
            assert not mc.trait_has_value("i")
            mc.i  # generates a default value
            assert mc.trait_has_value("i")
        """
        return name in self._trait_values

    def trait_values(self, **metadata: t.Any) -> dict[str, t.Any]:
        """A ``dict`` of trait names and their values.

        The metadata kwargs allow functions to be passed in which
        filter traits based on metadata values.  The functions should
        take a single value as an argument and return a boolean.  If
        any function returns False, then the trait is not included in
        the output.  If a metadata key doesn't exist, None will be passed
        to the function.

        Returns
        -------
        A ``dict`` of trait names and their values.

        Notes
        -----
        Trait values are retrieved via ``getattr``, any exceptions raised
        by traits or the operations they may trigger will result in the
        absence of a trait value in the result ``dict``.
        """
        return {name: getattr(self, name) for name in self.trait_names(**metadata)}

    def _get_trait_default_generator(self, name: str) -> t.Any:
        """Return default generator for a given trait

        Walk the MRO to resolve the correct default generator according to inheritance.
        """
        method_name = "_%s_default" % name
        if method_name in self.__dict__:
            return getattr(self, method_name)
        if method_name in self.__class__.__dict__:
            return getattr(self.__class__, method_name)
        return self._all_trait_default_generators[name]

    def trait_defaults(self, *names: str, **metadata: t.Any) -> dict[str, t.Any] | Sentinel:
        """Return a trait's default value or a dictionary of them

        Notes
        -----
        Dynamically generated default values may
        depend on the current state of the object."""
        for n in names:
            if not self.has_trait(n):
                raise TraitError(f"'{n}' is not a trait of '{type(self).__name__}' instances")

        if len(names) == 1 and len(metadata) == 0:
            return t.cast(Sentinel, self._get_trait_default_generator(names[0])(self))

        trait_names = self.trait_names(**metadata)
        trait_names.extend(names)

        defaults = {}
        for n in trait_names:
            defaults[n] = self._get_trait_default_generator(n)(self)
        return defaults

    def trait_names(self, **metadata: t.Any) -> list[str]:
        """Get a list of all the names of this class' traits."""
        return list(self.traits(**metadata))

    def traits(self, **metadata: t.Any) -> dict[str, TraitType[t.Any, t.Any]]:
        """Get a ``dict`` of all the traits of this class.  The dictionary
        is keyed on the name and the values are the TraitType objects.

        The TraitTypes returned don't know anything about the values
        that the various HasTrait's instances are holding.

        The metadata kwargs allow functions to be passed in which
        filter traits based on metadata values.  The functions should
        take a single value as an argument and return a boolean.  If
        any function returns False, then the trait is not included in
        the output.  If a metadata key doesn't exist, None will be passed
        to the function.
        """
        traits = self._traits.copy()

        if len(metadata) == 0:
            return traits

        result = {}
        for name, trait in traits.items():
            for meta_name, meta_eval in metadata.items():
                if not callable(meta_eval):
                    meta_eval = _SimpleTest(meta_eval)
                if not meta_eval(trait.metadata.get(meta_name, None)):
                    break
            else:
                result[name] = trait

        return result

    def trait_metadata(self, traitname: str, key: str, default: t.Any = None) -> t.Any:
        """Get metadata values for trait by key."""
        try:
            trait = getattr(self.__class__, traitname)
        except AttributeError as e:
            raise TraitError(
                f"Class {self.__class__.__name__} does not have a trait named {traitname}"
            ) from e
        metadata_name = "_" + traitname + "_metadata"
        if hasattr(self, metadata_name) and key in getattr(self, metadata_name):
            return getattr(self, metadata_name).get(key, default)
        else:
            return trait.metadata.get(key, default)

    @classmethod
    def class_own_trait_events(cls: type[HasTraits], name: str) -> dict[str, EventHandler]:
        """Get a dict of all event handlers defined on this class, not a parent.

        Works like ``event_handlers``, except for excluding traits from parents.
        """
        sup = super(cls, cls)
        return {
            n: e
            for (n, e) in cls.events(name).items()  # type:ignore[attr-defined]
            if getattr(sup, n, None) is not e
        }

    @classmethod
    def trait_events(cls: type[HasTraits], name: str | None = None) -> dict[str, EventHandler]:
        """Get a ``dict`` of all the event handlers of this class.

        Parameters
        ----------
        name : str (default: None)
            The name of a trait of this class. If name is ``None`` then all
            the event handlers of this class will be returned instead.

        Returns
        -------
        The event handlers associated with a trait name, or all event handlers.
        """
        events = {}
        for k, v in getmembers(cls):
            if isinstance(v, EventHandler):
                if name is None:
                    events[k] = v
                elif name in v.trait_names:  # type:ignore[attr-defined]
                    events[k] = v
                elif hasattr(v, "tags"):
                    if cls.trait_names(**v.tags):
                        events[k] = v
        return events


# -----------------------------------------------------------------------------
# Actual TraitTypes implementations/subclasses
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# TraitTypes subclasses for handling classes and instances of classes
# -----------------------------------------------------------------------------


class ClassBasedTraitType(TraitType[G, S]):
    """
    A trait with error reporting and string -> type resolution for Type,
    Instance and This.
    """

    def _resolve_string(self, string: str) -> t.Any:
        """
        Resolve a string supplied for a type into an actual object.
        """
        return import_item(string)


class Type(ClassBasedTraitType[G, S]):
    """A trait whose value must be a subclass of a specified class."""

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: Type[type, type],
            default_value: Sentinel | None | str = ...,
            klass: None | str = ...,
            allow_none: Literal[False] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Type[type | None, type | None],
            default_value: Sentinel | None | str = ...,
            klass: None | str = ...,
            allow_none: Literal[True] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Type[S, S],
            default_value: S = ...,
            klass: S = ...,
            allow_none: Literal[False] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Type[S | None, S | None],
            default_value: S | None = ...,
            klass: S = ...,
            allow_none: Literal[True] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

    def __init__(
        self,
        default_value: t.Any = Undefined,
        klass: t.Any = None,
        allow_none: bool = False,
        read_only: bool | None = None,
        help: str | None = None,
        config: t.Any | None = None,
        **kwargs: t.Any,
    ) -> None:
        """Construct a Type trait

        A Type trait specifies that its values must be subclasses of
        a particular class.

        If only ``default_value`` is given, it is used for the ``klass`` as
        well. If neither are given, both default to ``object``.

        Parameters
        ----------
        default_value : class, str or None
            The default value must be a subclass of klass.  If an str,
            the str must be a fully specified class name, like 'foo.bar.Bah'.
            The string is resolved into real class, when the parent
            :class:`HasTraits` class is instantiated.
        klass : class, str [ default object ]
            Values of this trait must be a subclass of klass.  The klass
            may be specified in a string like: 'foo.bar.MyClass'.
            The string is resolved into real class, when the parent
            :class:`HasTraits` class is instantiated.
        allow_none : bool [ default False ]
            Indicates whether None is allowed as an assignable value.
        **kwargs
            extra kwargs passed to `ClassBasedTraitType`
        """
        if default_value is Undefined:
            new_default_value = object if (klass is None) else klass
        else:
            new_default_value = default_value

        if klass is None:
            if (default_value is None) or (default_value is Undefined):
                klass = object
            else:
                klass = default_value

        if not (inspect.isclass(klass) or isinstance(klass, str)):
            raise TraitError("A Type trait must specify a class.")

        self.klass = klass

        super().__init__(
            new_default_value,
            allow_none=allow_none,
            read_only=read_only,
            help=help,
            config=config,
            **kwargs,
        )

    def validate(self, obj: t.Any, value: t.Any) -> G:
        """Validates that the value is a valid object instance."""
        if isinstance(value, str):
            try:
                value = self._resolve_string(value)
            except ImportError as e:
                raise TraitError(
                    f"The '{self.name}' trait of {obj} instance must be a type, but "
                    f"{value!r} could not be imported"
                ) from e
        try:
            if issubclass(value, self.klass):  # type:ignore[arg-type]
                return t.cast(G, value)
        except Exception:
            pass

        self.error(obj, value)

    def info(self) -> str:
        """Returns a description of the trait."""
        if isinstance(self.klass, str):
            klass = self.klass
        else:
            klass = self.klass.__module__ + "." + self.klass.__name__
        result = "a subclass of '%s'" % klass
        if self.allow_none:
            return result + " or None"
        return result

    def instance_init(self, obj: t.Any) -> None:
        # we can't do this in subclass_init because that
        # might be called before all imports are done.
        self._resolve_classes()

    def _resolve_classes(self) -> None:
        if isinstance(self.klass, str):
            self.klass = self._resolve_string(self.klass)
        if isinstance(self.default_value, str):
            self.default_value = self._resolve_string(self.default_value)

    def default_value_repr(self) -> str:
        value = self.default_value
        assert value is not None
        if isinstance(value, str):
            return repr(value)
        else:
            return repr(f"{value.__module__}.{value.__name__}")


class Instance(ClassBasedTraitType[T, T]):
    """A trait whose value must be an instance of a specified class.

    The value can also be an instance of a subclass of the specified class.

    Subclasses can declare default classes by overriding the klass attribute
    """

    klass: str | type[T] | None = None

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: Instance[T],
            klass: type[T] = ...,
            args: tuple[t.Any, ...] | None = ...,
            kw: dict[str, t.Any] | None = ...,
            allow_none: Literal[False] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Instance[T | None],
            klass: type[T] = ...,
            args: tuple[t.Any, ...] | None = ...,
            kw: dict[str, t.Any] | None = ...,
            allow_none: Literal[True] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Instance[t.Any],
            klass: str | None = ...,
            args: tuple[t.Any, ...] | None = ...,
            kw: dict[str, t.Any] | None = ...,
            allow_none: Literal[False] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Instance[t.Any | None],
            klass: str | None = ...,
            args: tuple[t.Any, ...] | None = ...,
            kw: dict[str, t.Any] | None = ...,
            allow_none: Literal[True] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

    def __init__(
        self,
        klass: str | type[T] | None = None,
        args: tuple[t.Any, ...] | None = None,
        kw: dict[str, t.Any] | None = None,
        allow_none: bool = False,
        read_only: bool | None = None,
        help: str | None = None,
        **kwargs: t.Any,
    ) -> None:
        """Construct an Instance trait.

        This trait allows values that are instances of a particular
        class or its subclasses.  Our implementation is quite different
        from that of enthough.traits as we don't allow instances to be used
        for klass and we handle the ``args`` and ``kw`` arguments differently.

        Parameters
        ----------
        klass : class, str
            The class that forms the basis for the trait.  Class names
            can also be specified as strings, like 'foo.bar.Bar'.
        args : tuple
            Positional arguments for generating the default value.
        kw : dict
            Keyword arguments for generating the default value.
        allow_none : bool [ default False ]
            Indicates whether None is allowed as a value.
        **kwargs
            Extra kwargs passed to `ClassBasedTraitType`

        Notes
        -----
        If both ``args`` and ``kw`` are None, then the default value is None.
        If ``args`` is a tuple and ``kw`` is a dict, then the default is
        created as ``klass(*args, **kw)``.  If exactly one of ``args`` or ``kw`` is
        None, the None is replaced by ``()`` or ``{}``, respectively.
        """
        if klass is None:
            klass = self.klass

        if (klass is not None) and (inspect.isclass(klass) or isinstance(klass, str)):
            self.klass = klass
        else:
            raise TraitError("The klass attribute must be a class not: %r" % klass)

        if (kw is not None) and not isinstance(kw, dict):
            raise TraitError("The 'kw' argument must be a dict or None.")
        if (args is not None) and not isinstance(args, tuple):
            raise TraitError("The 'args' argument must be a tuple or None.")

        self.default_args = args
        self.default_kwargs = kw

        super().__init__(allow_none=allow_none, read_only=read_only, help=help, **kwargs)

    def validate(self, obj: t.Any, value: t.Any) -> T | None:
        assert self.klass is not None
        if self.allow_none and value is None:
            return value
        if isinstance(value, self.klass):  # type:ignore[arg-type]
            return t.cast(T, value)
        else:
            self.error(obj, value)

    def info(self) -> str:
        if isinstance(self.klass, str):
            result = add_article(self.klass)
        else:
            result = describe("a", self.klass)
        if self.allow_none:
            result += " or None"
        return result

    def instance_init(self, obj: t.Any) -> None:
        # we can't do this in subclass_init because that
        # might be called before all imports are done.
        self._resolve_classes()

    def _resolve_classes(self) -> None:
        if isinstance(self.klass, str):
            self.klass = self._resolve_string(self.klass)

    def make_dynamic_default(self) -> T | None:
        if (self.default_args is None) and (self.default_kwargs is None):
            return None
        assert self.klass is not None
        return self.klass(*(self.default_args or ()), **(self.default_kwargs or {}))  # type:ignore[operator]

    def default_value_repr(self) -> str:
        return repr(self.make_dynamic_default())

    def from_string(self, s: str) -> T | None:
        return t.cast(T, _safe_literal_eval(s))


class ForwardDeclaredMixin:
    """
    Mixin for forward-declared versions of Instance and Type.
    """

    def _resolve_string(self, string: str) -> t.Any:
        """
        Find the specified class name by looking for it in the module in which
        our this_class attribute was defined.
        """
        modname = self.this_class.__module__  # type:ignore[attr-defined]
        return import_item(".".join([modname, string]))


class ForwardDeclaredType(ForwardDeclaredMixin, Type[G, S]):
    """
    Forward-declared version of Type.
    """


class ForwardDeclaredInstance(ForwardDeclaredMixin, Instance[T]):
    """
    Forward-declared version of Instance.
    """


class This(ClassBasedTraitType[t.Optional[T], t.Optional[T]]):
    """A trait for instances of the class containing this trait.

    Because how how and when class bodies are executed, the ``This``
    trait can only have a default value of None.  This, and because we
    always validate default values, ``allow_none`` is *always* true.
    """

    info_text = "an instance of the same type as the receiver or None"

    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(None, **kwargs)

    def validate(self, obj: t.Any, value: t.Any) -> HasTraits | None:
        # What if value is a superclass of obj.__class__?  This is
        # complicated if it was the superclass that defined the This
        # trait.
        assert self.this_class is not None
        if isinstance(value, self.this_class) or (value is None):
            return value
        else:
            self.error(obj, value)


class Union(TraitType[t.Any, t.Any]):
    """A trait type representing a Union type."""

    def __init__(self, trait_types: t.Any, **kwargs: t.Any) -> None:
        """Construct a Union  trait.

        This trait allows values that are allowed by at least one of the
        specified trait types. A Union traitlet cannot have metadata on
        its own, besides the metadata of the listed types.

        Parameters
        ----------
        trait_types : sequence
            The list of trait types of length at least 1.
        **kwargs
            Extra kwargs passed to `TraitType`

        Notes
        -----
        Union([Float(), Bool(), Int()]) attempts to validate the provided values
        with the validation function of Float, then Bool, and finally Int.

        Parsing from string is ambiguous for container types which accept other
        collection-like literals (e.g. List accepting both `[]` and `()`
        precludes Union from ever parsing ``Union([List(), Tuple()])`` as a tuple;
        you can modify behaviour of too permissive container traits by overriding
        ``_literal_from_string_pairs`` in subclasses.
        Similarly, parsing unions of numeric types is only unambiguous if
        types are provided in order of increasing permissiveness, e.g.
        ``Union([Int(), Float()])`` (since floats accept integer-looking values).
        """
        self.trait_types = list(trait_types)
        self.info_text = " or ".join([tt.info() for tt in self.trait_types])
        super().__init__(**kwargs)

    def default(self, obj: t.Any = None) -> t.Any:
        default = super().default(obj)
        for trait in self.trait_types:
            if default is Undefined:
                default = trait.default(obj)
            else:
                break
        return default

    def class_init(self, cls: type[HasTraits], name: str | None) -> None:
        for trait_type in reversed(self.trait_types):
            trait_type.class_init(cls, None)
        super().class_init(cls, name)

    def subclass_init(self, cls: type[t.Any]) -> None:
        for trait_type in reversed(self.trait_types):
            trait_type.subclass_init(cls)
        # explicitly not calling super().subclass_init(cls)
        # to opt out of instance_init

    def validate(self, obj: t.Any, value: t.Any) -> t.Any:
        with obj.cross_validation_lock:
            for trait_type in self.trait_types:
                try:
                    v = trait_type._validate(obj, value)
                    # In the case of an element trait, the name is None
                    if self.name is not None:
                        setattr(obj, "_" + self.name + "_metadata", trait_type.metadata)
                    return v
                except TraitError:
                    continue
        self.error(obj, value)

    def __or__(self, other: t.Any) -> Union:
        if isinstance(other, Union):
            return Union(self.trait_types + other.trait_types)
        else:
            return Union([*self.trait_types, other])

    def from_string(self, s: str) -> t.Any:
        for trait_type in self.trait_types:
            try:
                v = trait_type.from_string(s)
                return trait_type.validate(None, v)
            except (TraitError, ValueError):
                continue
        return super().from_string(s)


# -----------------------------------------------------------------------------
# Basic TraitTypes implementations/subclasses
# -----------------------------------------------------------------------------


class Any(TraitType[t.Optional[t.Any], t.Optional[t.Any]]):
    """A trait which allows any value."""

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: Any,
            default_value: t.Any = ...,
            *,
            allow_none: Literal[False],
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Any,
            default_value: t.Any = ...,
            *,
            allow_none: Literal[True],
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Any,
            default_value: t.Any = ...,
            *,
            allow_none: Literal[True, False] = ...,
            help: str | None = ...,
            read_only: bool | None = False,
            config: t.Any = None,
            **kwargs: t.Any,
        ) -> None:
            ...

        def __init__(
            self: Any,
            default_value: t.Any = ...,
            *,
            allow_none: bool = False,
            help: str | None = "",
            read_only: bool | None = False,
            config: t.Any = None,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __get__(self, obj: None, cls: type[t.Any]) -> Any:
            ...

        @t.overload
        def __get__(self, obj: t.Any, cls: type[t.Any]) -> t.Any:
            ...

        def __get__(self, obj: t.Any | None, cls: type[t.Any]) -> t.Any | Any:
            ...

    default_value: t.Any | None = None
    allow_none = True
    info_text = "any value"

    def subclass_init(self, cls: type[t.Any]) -> None:
        pass  # fully opt out of instance_init


def _validate_bounds(
    trait: Int[t.Any, t.Any] | Float[t.Any, t.Any], obj: t.Any, value: t.Any
) -> t.Any:
    """
    Validate that a number to be applied to a trait is between bounds.

    If value is not between min_bound and max_bound, this raises a
    TraitError with an error message appropriate for this trait.
    """
    if trait.min is not None and value < trait.min:
        raise TraitError(
            f"The value of the '{trait.name}' trait of {class_of(obj)} instance should "
            f"not be less than {trait.min}, but a value of {value} was "
            "specified"
        )
    if trait.max is not None and value > trait.max:
        raise TraitError(
            f"The value of the '{trait.name}' trait of {class_of(obj)} instance should "
            f"not be greater than {trait.max}, but a value of {value} was "
            "specified"
        )
    return value


# I = t.TypeVar('I', t.Optional[int], int)


class Int(TraitType[G, S]):
    """An int trait."""

    default_value = 0
    info_text = "an int"

    @t.overload
    def __init__(
        self: Int[int, int],
        default_value: int | Sentinel = ...,
        allow_none: Literal[False] = ...,
        read_only: bool | None = ...,
        help: str | None = ...,
        config: t.Any | None = ...,
        **kwargs: t.Any,
    ) -> None:
        ...

    @t.overload
    def __init__(
        self: Int[int | None, int | None],
        default_value: int | Sentinel | None = ...,
        allow_none: Literal[True] = ...,
        read_only: bool | None = ...,
        help: str | None = ...,
        config: t.Any | None = ...,
        **kwargs: t.Any,
    ) -> None:
        ...

    def __init__(
        self,
        default_value: t.Any = Undefined,
        allow_none: bool = False,
        read_only: bool | None = None,
        help: str | None = None,
        config: t.Any | None = None,
        **kwargs: t.Any,
    ) -> None:
        self.min = kwargs.pop("min", None)
        self.max = kwargs.pop("max", None)
        super().__init__(
            default_value=default_value,
            allow_none=allow_none,
            read_only=read_only,
            help=help,
            config=config,
            **kwargs,
        )

    def validate(self, obj: t.Any, value: t.Any) -> G:
        if not isinstance(value, int):
            self.error(obj, value)
        return t.cast(G, _validate_bounds(self, obj, value))

    def from_string(self, s: str) -> G:
        if self.allow_none and s == "None":
            return t.cast(G, None)
        return t.cast(G, int(s))

    def subclass_init(self, cls: type[t.Any]) -> None:
        pass  # fully opt out of instance_init


class CInt(Int[G, S]):
    """A casting version of the int trait."""

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: CInt[int, t.Any],
            default_value: t.Any | Sentinel = ...,
            allow_none: Literal[False] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: CInt[int | None, t.Any],
            default_value: t.Any | Sentinel | None = ...,
            allow_none: Literal[True] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        def __init__(
            self: CInt[int | None, t.Any],
            default_value: t.Any | Sentinel | None = ...,
            allow_none: bool = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

    def validate(self, obj: t.Any, value: t.Any) -> G:
        try:
            value = int(value)
        except Exception:
            self.error(obj, value)
        return t.cast(G, _validate_bounds(self, obj, value))


Long, CLong = Int, CInt
Integer = Int


class Float(TraitType[G, S]):
    """A float trait."""

    default_value = 0.0
    info_text = "a float"

    @t.overload
    def __init__(
        self: Float[float, int | float],
        default_value: float | Sentinel = ...,
        allow_none: Literal[False] = ...,
        read_only: bool | None = ...,
        help: str | None = ...,
        config: t.Any | None = ...,
        **kwargs: t.Any,
    ) -> None:
        ...

    @t.overload
    def __init__(
        self: Float[int | None, int | float | None],
        default_value: float | Sentinel | None = ...,
        allow_none: Literal[True] = ...,
        read_only: bool | None = ...,
        help: str | None = ...,
        config: t.Any | None = ...,
        **kwargs: t.Any,
    ) -> None:
        ...

    def __init__(
        self: Float[int | None, int | float | None],
        default_value: float | Sentinel | None = Undefined,
        allow_none: bool = False,
        read_only: bool | None = False,
        help: str | None = None,
        config: t.Any | None = None,
        **kwargs: t.Any,
    ) -> None:
        self.min = kwargs.pop("min", -float("inf"))
        self.max = kwargs.pop("max", float("inf"))
        super().__init__(
            default_value=default_value,
            allow_none=allow_none,
            read_only=read_only,
            help=help,
            config=config,
            **kwargs,
        )

    def validate(self, obj: t.Any, value: t.Any) -> G:
        if isinstance(value, int):
            value = float(value)
        if not isinstance(value, float):
            self.error(obj, value)
        return t.cast(G, _validate_bounds(self, obj, value))

    def from_string(self, s: str) -> G:
        if self.allow_none and s == "None":
            return t.cast(G, None)
        return t.cast(G, float(s))

    def subclass_init(self, cls: type[t.Any]) -> None:
        pass  # fully opt out of instance_init


class CFloat(Float[G, S]):
    """A casting version of the float trait."""

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: CFloat[float, t.Any],
            default_value: t.Any = ...,
            allow_none: Literal[False] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: CFloat[float | None, t.Any],
            default_value: t.Any = ...,
            allow_none: Literal[True] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        def __init__(
            self: CFloat[float | None, t.Any],
            default_value: t.Any = ...,
            allow_none: bool = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any | None = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

    def validate(self, obj: t.Any, value: t.Any) -> G:
        try:
            value = float(value)
        except Exception:
            self.error(obj, value)
        return t.cast(G, _validate_bounds(self, obj, value))


class Complex(TraitType[complex, t.Union[complex, float, int]]):
    """A trait for complex numbers."""

    default_value = 0.0 + 0.0j
    info_text = "a complex number"

    def validate(self, obj: t.Any, value: t.Any) -> complex | None:
        if isinstance(value, complex):
            return value
        if isinstance(value, (float, int)):
            return complex(value)
        self.error(obj, value)

    def from_string(self, s: str) -> complex | None:
        if self.allow_none and s == "None":
            return None
        return complex(s)

    def subclass_init(self, cls: type[t.Any]) -> None:
        pass  # fully opt out of instance_init


class CComplex(Complex, TraitType[complex, t.Any]):
    """A casting version of the complex number trait."""

    def validate(self, obj: t.Any, value: t.Any) -> complex | None:
        try:
            return complex(value)
        except Exception:
            self.error(obj, value)


# We should always be explicit about whether we're using bytes or unicode, both
# for Python 3 conversion and for reliable unicode behaviour on Python 2. So
# we don't have a Str type.
class Bytes(TraitType[bytes, bytes]):
    """A trait for byte strings."""

    default_value = b""
    info_text = "a bytes object"

    def validate(self, obj: t.Any, value: t.Any) -> bytes | None:
        if isinstance(value, bytes):
            return value
        self.error(obj, value)

    def from_string(self, s: str) -> bytes | None:
        if self.allow_none and s == "None":
            return None
        if len(s) >= 3:
            # handle deprecated b"string"
            for quote in ('"', "'"):
                if s[:2] == f"b{quote}" and s[-1] == quote:
                    old_s = s
                    s = s[2:-1]
                    warn(
                        "Supporting extra quotes around Bytes is deprecated in traitlets 5.0. "
                        f"Use {s!r} instead of {old_s!r}.",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                    break
        return s.encode("utf8")

    def subclass_init(self, cls: type[t.Any]) -> None:
        pass  # fully opt out of instance_init


class CBytes(Bytes, TraitType[bytes, t.Any]):
    """A casting version of the byte string trait."""

    def validate(self, obj: t.Any, value: t.Any) -> bytes | None:
        try:
            return bytes(value)
        except Exception:
            self.error(obj, value)


class Unicode(TraitType[G, S]):
    """A trait for unicode strings."""

    default_value = ""
    info_text = "a unicode string"

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: Unicode[str, str | bytes],
            default_value: str | Sentinel = ...,
            allow_none: Literal[False] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Unicode[str | None, str | bytes | None],
            default_value: str | Sentinel | None = ...,
            allow_none: Literal[True] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        def __init__(
            self: Unicode[str | None, str | bytes | None],
            default_value: str | Sentinel | None = ...,
            allow_none: bool = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

    def validate(self, obj: t.Any, value: t.Any) -> G:
        if isinstance(value, str):
            return t.cast(G, value)
        if isinstance(value, bytes):
            try:
                return t.cast(G, value.decode("ascii", "strict"))
            except UnicodeDecodeError as e:
                msg = "Could not decode {!r} for unicode trait '{}' of {} instance."
                raise TraitError(msg.format(value, self.name, class_of(obj))) from e
        self.error(obj, value)

    def from_string(self, s: str) -> G:
        if self.allow_none and s == "None":
            return t.cast(G, None)
        s = os.path.expanduser(s)
        if len(s) >= 2:
            # handle deprecated "1"
            for c in ('"', "'"):
                if s[0] == s[-1] == c:
                    old_s = s
                    s = s[1:-1]
                    warn(
                        "Supporting extra quotes around strings is deprecated in traitlets 5.0. "
                        f"You can use {s!r} instead of {old_s!r} if you require traitlets >=5.",
                        DeprecationWarning,
                        stacklevel=2,
                    )
        return t.cast(G, s)

    def subclass_init(self, cls: type[t.Any]) -> None:
        pass  # fully opt out of instance_init


class CUnicode(Unicode[G, S], TraitType[str, t.Any]):
    """A casting version of the unicode trait."""

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: CUnicode[str, t.Any],
            default_value: str | Sentinel = ...,
            allow_none: Literal[False] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: CUnicode[str | None, t.Any],
            default_value: str | Sentinel | None = ...,
            allow_none: Literal[True] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        def __init__(
            self: CUnicode[str | None, t.Any],
            default_value: str | Sentinel | None = ...,
            allow_none: bool = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

    def validate(self, obj: t.Any, value: t.Any) -> G:
        try:
            return t.cast(G, str(value))
        except Exception:
            self.error(obj, value)


class ObjectName(TraitType[str, str]):
    """A string holding a valid object name in this version of Python.

    This does not check that the name exists in any scope."""

    info_text = "a valid object identifier in Python"

    coerce_str = staticmethod(lambda _, s: s)

    def validate(self, obj: t.Any, value: t.Any) -> str:
        value = self.coerce_str(obj, value)

        if isinstance(value, str) and isidentifier(value):
            return value
        self.error(obj, value)

    def from_string(self, s: str) -> str | None:
        if self.allow_none and s == "None":
            return None
        return s


class DottedObjectName(ObjectName):
    """A string holding a valid dotted object name in Python, such as A.b3._c"""

    def validate(self, obj: t.Any, value: t.Any) -> str:
        value = self.coerce_str(obj, value)

        if isinstance(value, str) and all(isidentifier(a) for a in value.split(".")):
            return value
        self.error(obj, value)


class Bool(TraitType[G, S]):
    """A boolean (True, False) trait."""

    default_value = False
    info_text = "a boolean"

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: Bool[bool, bool | int],
            default_value: bool | Sentinel = ...,
            allow_none: Literal[False] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Bool[bool | None, bool | int | None],
            default_value: bool | Sentinel | None = ...,
            allow_none: Literal[True] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        def __init__(
            self: Bool[bool | None, bool | int | None],
            default_value: bool | Sentinel | None = ...,
            allow_none: bool = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

    def validate(self, obj: t.Any, value: t.Any) -> G:
        if isinstance(value, bool):
            return t.cast(G, value)
        elif isinstance(value, int):
            if value == 1:
                return t.cast(G, True)
            elif value == 0:
                return t.cast(G, False)
        self.error(obj, value)

    def from_string(self, s: str) -> G:
        if self.allow_none and s == "None":
            return t.cast(G, None)
        s = s.lower()
        if s in {"true", "1"}:
            return t.cast(G, True)
        elif s in {"false", "0"}:
            return t.cast(G, False)
        else:
            raise ValueError("%r is not 1, 0, true, or false")

    def subclass_init(self, cls: type[t.Any]) -> None:
        pass  # fully opt out of instance_init

    def argcompleter(self, **kwargs: t.Any) -> list[str]:
        """Completion hints for argcomplete"""
        completions = ["true", "1", "false", "0"]
        if self.allow_none:
            completions.append("None")
        return completions


class CBool(Bool[G, S]):
    """A casting version of the boolean trait."""

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: CBool[bool, t.Any],
            default_value: bool | Sentinel = ...,
            allow_none: Literal[False] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: CBool[bool | None, t.Any],
            default_value: bool | Sentinel | None = ...,
            allow_none: Literal[True] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        def __init__(
            self: CBool[bool | None, t.Any],
            default_value: bool | Sentinel | None = ...,
            allow_none: bool = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

    def validate(self, obj: t.Any, value: t.Any) -> G:
        try:
            return t.cast(G, bool(value))
        except Exception:
            self.error(obj, value)


class Enum(TraitType[G, G]):
    """An enum whose value must be in a given sequence."""

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: Enum[G],
            values: t.Sequence[G],
            default_value: G | Sentinel = ...,
            allow_none: Literal[False] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Enum[G | None],
            values: t.Sequence[G] | None,
            default_value: G | Sentinel | None = ...,
            allow_none: Literal[True] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

    def __init__(
        self: Enum[G],
        values: t.Sequence[G] | None,
        default_value: G | Sentinel | None = Undefined,
        allow_none: bool = False,
        read_only: bool | None = None,
        help: str | None = None,
        config: t.Any = None,
        **kwargs: t.Any,
    ) -> None:
        self.values = values
        if allow_none is True and default_value is Undefined:
            default_value = None
        kwargs["allow_none"] = allow_none
        kwargs["read_only"] = read_only
        kwargs["help"] = help
        kwargs["config"] = config
        super().__init__(default_value, **kwargs)

    def validate(self, obj: t.Any, value: t.Any) -> G:
        if self.values and value in self.values:
            return t.cast(G, value)
        self.error(obj, value)

    def _choices_str(self, as_rst: bool = False) -> str:
        """Returns a description of the trait choices (not none)."""
        choices = self.values or []
        if as_rst:
            choice_str = "|".join("``%r``" % x for x in choices)
        else:
            choice_str = repr(list(choices))
        return choice_str

    def _info(self, as_rst: bool = False) -> str:
        """Returns a description of the trait."""
        none = " or %s" % ("`None`" if as_rst else "None") if self.allow_none else ""
        return f"any of {self._choices_str(as_rst)}{none}"

    def info(self) -> str:
        return self._info(as_rst=False)

    def info_rst(self) -> str:
        return self._info(as_rst=True)

    def from_string(self, s: str) -> G:
        try:
            return self.validate(None, s)
        except TraitError:
            return t.cast(G, _safe_literal_eval(s))

    def subclass_init(self, cls: type[t.Any]) -> None:
        pass  # fully opt out of instance_init

    def argcompleter(self, **kwargs: t.Any) -> list[str]:
        """Completion hints for argcomplete"""
        return [str(v) for v in self.values or []]


class CaselessStrEnum(Enum[G]):
    """An enum of strings where the case should be ignored."""

    def __init__(
        self: CaselessStrEnum[t.Any],
        values: t.Any,
        default_value: t.Any = Undefined,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(values, default_value=default_value, **kwargs)

    def validate(self, obj: t.Any, value: t.Any) -> G:
        if not isinstance(value, str):
            self.error(obj, value)

        for v in self.values or []:
            assert isinstance(v, str)
            if v.lower() == value.lower():
                return t.cast(G, v)
        self.error(obj, value)

    def _info(self, as_rst: bool = False) -> str:
        """Returns a description of the trait."""
        none = " or %s" % ("`None`" if as_rst else "None") if self.allow_none else ""
        return f"any of {self._choices_str(as_rst)} (case-insensitive){none}"

    def info(self) -> str:
        return self._info(as_rst=False)

    def info_rst(self) -> str:
        return self._info(as_rst=True)


class FuzzyEnum(Enum[G]):
    """An case-ignoring enum matching choices by unique prefixes/substrings."""

    case_sensitive = False
    #: If True, choices match anywhere in the string, otherwise match prefixes.
    substring_matching = False

    def __init__(
        self: FuzzyEnum[t.Any],
        values: t.Any,
        default_value: t.Any = Undefined,
        case_sensitive: bool = False,
        substring_matching: bool = False,
        **kwargs: t.Any,
    ) -> None:
        self.case_sensitive = case_sensitive
        self.substring_matching = substring_matching
        super().__init__(values, default_value=default_value, **kwargs)

    def validate(self, obj: t.Any, value: t.Any) -> G:
        if not isinstance(value, str):
            self.error(obj, value)

        conv_func = (lambda c: c) if self.case_sensitive else lambda c: c.lower()
        substring_matching = self.substring_matching
        match_func = (lambda v, c: v in c) if substring_matching else (lambda v, c: c.startswith(v))
        value = conv_func(value)  # type:ignore[no-untyped-call]
        choices = self.values or []
        matches = [match_func(value, conv_func(c)) for c in choices]  # type:ignore[no-untyped-call]
        if sum(matches) == 1:
            for v, m in zip(choices, matches):
                if m:
                    return v

        self.error(obj, value)

    def _info(self, as_rst: bool = False) -> str:
        """Returns a description of the trait."""
        none = " or %s" % ("`None`" if as_rst else "None") if self.allow_none else ""
        case = "sensitive" if self.case_sensitive else "insensitive"
        substr = "substring" if self.substring_matching else "prefix"
        return f"any case-{case} {substr} of {self._choices_str(as_rst)}{none}"

    def info(self) -> str:
        return self._info(as_rst=False)

    def info_rst(self) -> str:
        return self._info(as_rst=True)


class Container(Instance[T]):
    """An instance of a container (list, set, etc.)

    To be subclassed by overriding klass.
    """

    klass: type[T] | None = None
    _cast_types: t.Any = ()
    _valid_defaults = SequenceTypes
    _trait: t.Any = None
    _literal_from_string_pairs: t.Any = ("[]", "()")

    @t.overload
    def __init__(
        self: Container[T],
        *,
        allow_none: Literal[False],
        read_only: bool | None = ...,
        help: str | None = ...,
        config: t.Any | None = ...,
        **kwargs: t.Any,
    ) -> None:
        ...

    @t.overload
    def __init__(
        self: Container[T | None],
        *,
        allow_none: Literal[True],
        read_only: bool | None = ...,
        help: str | None = ...,
        config: t.Any | None = ...,
        **kwargs: t.Any,
    ) -> None:
        ...

    @t.overload
    def __init__(
        self: Container[T],
        *,
        trait: t.Any = ...,
        default_value: t.Any = ...,
        help: str = ...,
        read_only: bool = ...,
        config: t.Any = ...,
        **kwargs: t.Any,
    ) -> None:
        ...

    def __init__(
        self,
        trait: t.Any | None = None,
        default_value: t.Any = Undefined,
        help: str | None = None,
        read_only: bool | None = None,
        config: t.Any | None = None,
        **kwargs: t.Any,
    ) -> None:
        """Create a container trait type from a list, set, or tuple.

        The default value is created by doing ``List(default_value)``,
        which creates a copy of the ``default_value``.

        ``trait`` can be specified, which restricts the type of elements
        in the container to that TraitType.

        If only one arg is given and it is not a Trait, it is taken as
        ``default_value``:

        ``c = List([1, 2, 3])``

        Parameters
        ----------
        trait : TraitType [ optional ]
            the type for restricting the contents of the Container.  If unspecified,
            types are not checked.
        default_value : SequenceType [ optional ]
            The default value for the Trait.  Must be list/tuple/set, and
            will be cast to the container type.
        allow_none : bool [ default False ]
            Whether to allow the value to be None
        **kwargs : any
            further keys for extensions to the Trait (e.g. config)

        """

        # allow List([values]):
        if trait is not None and default_value is Undefined and not is_trait(trait):
            default_value = trait
            trait = None

        if default_value is None and not kwargs.get("allow_none", False):
            # improve backward-compatibility for possible subclasses
            # specifying default_value=None as default,
            # keeping 'unspecified' behavior (i.e. empty container)
            warn(
                f"Specifying {self.__class__.__name__}(default_value=None)"
                " for no default is deprecated in traitlets 5.0.5."
                " Use default_value=Undefined",
                DeprecationWarning,
                stacklevel=2,
            )
            default_value = Undefined

        if default_value is Undefined:
            args: t.Any = ()
        elif default_value is None:
            # default_value back on kwargs for super() to handle
            args = ()
            kwargs["default_value"] = None
        elif isinstance(default_value, self._valid_defaults):
            args = (default_value,)
        else:
            raise TypeError(f"default value of {self.__class__.__name__} was {default_value}")

        if is_trait(trait):
            if isinstance(trait, type):
                warn(
                    "Traits should be given as instances, not types (for example, `Int()`, not `Int`)."
                    " Passing types is deprecated in traitlets 4.1.",
                    DeprecationWarning,
                    stacklevel=3,
                )
            self._trait = trait() if isinstance(trait, type) else trait
        elif trait is not None:
            raise TypeError("`trait` must be a Trait or None, got %s" % repr_type(trait))

        super().__init__(
            klass=self.klass, args=args, help=help, read_only=read_only, config=config, **kwargs
        )

    def validate(self, obj: t.Any, value: t.Any) -> T | None:
        if isinstance(value, self._cast_types):
            assert self.klass is not None
            value = self.klass(value)  # type:ignore[call-arg]
        value = super().validate(obj, value)
        if value is None:
            return value

        value = self.validate_elements(obj, value)

        return t.cast(T, value)

    def validate_elements(self, obj: t.Any, value: t.Any) -> T | None:
        validated = []
        if self._trait is None or isinstance(self._trait, Any):
            return t.cast(T, value)
        for v in value:
            try:
                v = self._trait._validate(obj, v)
            except TraitError as error:
                self.error(obj, v, error)
            else:
                validated.append(v)
        assert self.klass is not None
        return self.klass(validated)  # type:ignore[call-arg]

    def class_init(self, cls: type[t.Any], name: str | None) -> None:
        if isinstance(self._trait, TraitType):
            self._trait.class_init(cls, None)
        super().class_init(cls, name)

    def subclass_init(self, cls: type[t.Any]) -> None:
        if isinstance(self._trait, TraitType):
            self._trait.subclass_init(cls)
        # explicitly not calling super().subclass_init(cls)
        # to opt out of instance_init

    def from_string(self, s: str) -> T | None:
        """Load value from a single string"""
        if not isinstance(s, str):
            raise TraitError(f"Expected string, got {s!r}")
        try:
            test = literal_eval(s)
        except Exception:
            test = None
        return self.validate(None, test)

    def from_string_list(self, s_list: list[str]) -> T | None:
        """Return the value from a list of config strings

        This is where we parse CLI configuration
        """
        assert self.klass is not None
        if len(s_list) == 1:
            # check for deprecated --Class.trait="['a', 'b', 'c']"
            r = s_list[0]
            if r == "None" and self.allow_none:
                return None
            if len(r) >= 2 and any(
                r.startswith(start) and r.endswith(end)
                for start, end in self._literal_from_string_pairs
            ):
                if self.this_class:
                    clsname = self.this_class.__name__ + "."
                else:
                    clsname = ""
                assert self.name is not None
                warn(
                    "--{0}={1} for containers is deprecated in traitlets 5.0. "
                    "You can pass `--{0} item` ... multiple times to add items to a list.".format(
                        clsname + self.name, r
                    ),
                    DeprecationWarning,
                    stacklevel=2,
                )
                return self.klass(literal_eval(r))  # type:ignore[call-arg]
        sig = inspect.signature(self.item_from_string)
        if "index" in sig.parameters:
            item_from_string = self.item_from_string
        else:
            # backward-compat: allow item_from_string to ignore index arg
            def item_from_string(s: str, index: int | None = None) -> T | str:
                return t.cast(T, self.item_from_string(s))

        return self.klass(  # type:ignore[call-arg]
            [item_from_string(s, index=idx) for idx, s in enumerate(s_list)]
        )

    def item_from_string(self, s: str, index: int | None = None) -> T | str:
        """Cast a single item from a string

        Evaluated when parsing CLI configuration from a string
        """
        if self._trait:
            return t.cast(T, self._trait.from_string(s))
        else:
            return s


class List(Container[t.List[T]]):
    """An instance of a Python list."""

    klass = list  # type:ignore[assignment]
    _cast_types: t.Any = (tuple,)

    def __init__(
        self,
        trait: t.List[T] | t.Tuple[T] | t.Set[T] | Sentinel | TraitType[T, t.Any] | None = None,
        default_value: t.List[T] | t.Tuple[T] | t.Set[T] | Sentinel | None = Undefined,
        minlen: int = 0,
        maxlen: int = sys.maxsize,
        **kwargs: t.Any,
    ) -> None:
        """Create a List trait type from a list, set, or tuple.

        The default value is created by doing ``list(default_value)``,
        which creates a copy of the ``default_value``.

        ``trait`` can be specified, which restricts the type of elements
        in the container to that TraitType.

        If only one arg is given and it is not a Trait, it is taken as
        ``default_value``:

        ``c = List([1, 2, 3])``

        Parameters
        ----------
        trait : TraitType [ optional ]
            the type for restricting the contents of the Container.
            If unspecified, types are not checked.
        default_value : SequenceType [ optional ]
            The default value for the Trait.  Must be list/tuple/set, and
            will be cast to the container type.
        minlen : Int [ default 0 ]
            The minimum length of the input list
        maxlen : Int [ default sys.maxsize ]
            The maximum length of the input list
        """
        self._maxlen = maxlen
        self._minlen = minlen
        super().__init__(trait=trait, default_value=default_value, **kwargs)

    def length_error(self, obj: t.Any, value: t.Any) -> None:
        e = (
            "The '%s' trait of %s instance must be of length %i <= L <= %i, but a value of %s was specified."
            % (self.name, class_of(obj), self._minlen, self._maxlen, value)
        )
        raise TraitError(e)

    def validate_elements(self, obj: t.Any, value: t.Any) -> t.Any:
        length = len(value)
        if length < self._minlen or length > self._maxlen:
            self.length_error(obj, value)

        return super().validate_elements(obj, value)

    def set(self, obj: t.Any, value: t.Any) -> None:
        if isinstance(value, str):
            return super().set(obj, [value])  # type:ignore[list-item]
        else:
            return super().set(obj, value)


class Set(Container[t.Set[t.Any]]):
    """An instance of a Python set."""

    klass = set
    _cast_types = (tuple, list)

    _literal_from_string_pairs = ("[]", "()", "{}")

    # Redefine __init__ just to make the docstring more accurate.
    def __init__(
        self,
        trait: t.Any = None,
        default_value: t.Any = Undefined,
        minlen: int = 0,
        maxlen: int = sys.maxsize,
        **kwargs: t.Any,
    ) -> None:
        """Create a Set trait type from a list, set, or tuple.

        The default value is created by doing ``set(default_value)``,
        which creates a copy of the ``default_value``.

        ``trait`` can be specified, which restricts the type of elements
        in the container to that TraitType.

        If only one arg is given and it is not a Trait, it is taken as
        ``default_value``:

        ``c = Set({1, 2, 3})``

        Parameters
        ----------
        trait : TraitType [ optional ]
            the type for restricting the contents of the Container.
            If unspecified, types are not checked.
        default_value : SequenceType [ optional ]
            The default value for the Trait.  Must be list/tuple/set, and
            will be cast to the container type.
        minlen : Int [ default 0 ]
            The minimum length of the input list
        maxlen : Int [ default sys.maxsize ]
            The maximum length of the input list
        """
        self._maxlen = maxlen
        self._minlen = minlen
        super().__init__(trait=trait, default_value=default_value, **kwargs)

    def length_error(self, obj: t.Any, value: t.Any) -> None:
        e = (
            "The '%s' trait of %s instance must be of length %i <= L <= %i, but a value of %s was specified."
            % (self.name, class_of(obj), self._minlen, self._maxlen, value)
        )
        raise TraitError(e)

    def validate_elements(self, obj: t.Any, value: t.Any) -> t.Any:
        length = len(value)
        if length < self._minlen or length > self._maxlen:
            self.length_error(obj, value)

        return super().validate_elements(obj, value)

    def set(self, obj: t.Any, value: t.Any) -> None:
        if isinstance(value, str):
            return super().set(obj, {value})
        else:
            return super().set(obj, value)

    def default_value_repr(self) -> str:
        # Ensure default value is sorted for a reproducible build
        list_repr = repr(sorted(self.make_dynamic_default() or []))
        if list_repr == "[]":
            return "set()"
        return "{" + list_repr[1:-1] + "}"


class Tuple(Container[t.Tuple[t.Any, ...]]):
    """An instance of a Python tuple."""

    klass = tuple
    _cast_types = (list,)

    def __init__(self, *traits: t.Any, **kwargs: t.Any) -> None:
        """Create a tuple from a list, set, or tuple.

        Create a fixed-type tuple with Traits:

        ``t = Tuple(Int(), Str(), CStr())``

        would be length 3, with Int,Str,CStr for each element.

        If only one arg is given and it is not a Trait, it is taken as
        default_value:

        ``t = Tuple((1, 2, 3))``

        Otherwise, ``default_value`` *must* be specified by keyword.

        Parameters
        ----------
        *traits : TraitTypes [ optional ]
            the types for restricting the contents of the Tuple.  If unspecified,
            types are not checked. If specified, then each positional argument
            corresponds to an element of the tuple.  Tuples defined with traits
            are of fixed length.
        default_value : SequenceType [ optional ]
            The default value for the Tuple.  Must be list/tuple/set, and
            will be cast to a tuple. If ``traits`` are specified,
            ``default_value`` must conform to the shape and type they specify.
        **kwargs
            Other kwargs passed to `Container`
        """
        default_value = kwargs.pop("default_value", Undefined)
        # allow Tuple((values,)):
        if len(traits) == 1 and default_value is Undefined and not is_trait(traits[0]):
            default_value = traits[0]
            traits = ()

        if default_value is None and not kwargs.get("allow_none", False):
            # improve backward-compatibility for possible subclasses
            # specifying default_value=None as default,
            # keeping 'unspecified' behavior (i.e. empty container)
            warn(
                f"Specifying {self.__class__.__name__}(default_value=None)"
                " for no default is deprecated in traitlets 5.0.5."
                " Use default_value=Undefined",
                DeprecationWarning,
                stacklevel=2,
            )
            default_value = Undefined

        if default_value is Undefined:
            args: t.Any = ()
        elif default_value is None:
            # default_value back on kwargs for super() to handle
            args = ()
            kwargs["default_value"] = None
        elif isinstance(default_value, self._valid_defaults):
            args = (default_value,)
        else:
            raise TypeError(f"default value of {self.__class__.__name__} was {default_value}")

        self._traits = []
        for trait in traits:
            if isinstance(trait, type):
                warn(
                    "Traits should be given as instances, not types (for example, `Int()`, not `Int`)"
                    " Passing types is deprecated in traitlets 4.1.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                trait = trait()
            self._traits.append(trait)

        if self._traits and (default_value is None or default_value is Undefined):
            # don't allow default to be an empty container if length is specified
            args = None
        super(Container, self).__init__(klass=self.klass, args=args, **kwargs)

    def item_from_string(self, s: str, index: int) -> t.Any:  # type:ignore[override]
        """Cast a single item from a string

        Evaluated when parsing CLI configuration from a string
        """
        if not self._traits or index >= len(self._traits):
            # return s instead of raising index error
            # length errors will be raised later on validation
            return s
        return self._traits[index].from_string(s)

    def validate_elements(self, obj: t.Any, value: t.Any) -> t.Any:
        if not self._traits:
            # nothing to validate
            return value
        if len(value) != len(self._traits):
            e = (
                "The '%s' trait of %s instance requires %i elements, but a value of %s was specified."
                % (self.name, class_of(obj), len(self._traits), repr_type(value))
            )
            raise TraitError(e)

        validated = []
        for trait, v in zip(self._traits, value):
            try:
                v = trait._validate(obj, v)
            except TraitError as error:
                self.error(obj, v, error)
            else:
                validated.append(v)
        return tuple(validated)

    def class_init(self, cls: type[t.Any], name: str | None) -> None:
        for trait in self._traits:
            if isinstance(trait, TraitType):
                trait.class_init(cls, None)
        super(Container, self).class_init(cls, name)

    def subclass_init(self, cls: type[t.Any]) -> None:
        for trait in self._traits:
            if isinstance(trait, TraitType):
                trait.subclass_init(cls)
        # explicitly not calling super().subclass_init(cls)
        # to opt out of instance_init


class Dict(Instance["dict[K, V]"]):
    """An instance of a Python dict.

    One or more traits can be passed to the constructor
    to validate the keys and/or values of the dict.
    If you need more detailed validation,
    you may use a custom validator method.

    .. versionchanged:: 5.0
        Added key_trait for validating dict keys.

    .. versionchanged:: 5.0
        Deprecated ambiguous ``trait``, ``traits`` args in favor of ``value_trait``, ``per_key_traits``.
    """

    _value_trait = None
    _key_trait = None

    def __init__(
        self,
        value_trait: TraitType[t.Any, t.Any] | dict[K, V] | Sentinel | None = None,
        per_key_traits: t.Any = None,
        key_trait: TraitType[t.Any, t.Any] | None = None,
        default_value: dict[K, V] | Sentinel | None = Undefined,
        **kwargs: t.Any,
    ) -> None:
        """Create a dict trait type from a Python dict.

        The default value is created by doing ``dict(default_value)``,
        which creates a copy of the ``default_value``.

        Parameters
        ----------
        value_trait : TraitType [ optional ]
            The specified trait type to check and use to restrict the values of
            the dict. If unspecified, values are not checked.
        per_key_traits : Dictionary of {keys:trait types} [ optional, keyword-only ]
            A Python dictionary containing the types that are valid for
            restricting the values of the dict on a per-key basis.
            Each value in this dict should be a Trait for validating
        key_trait : TraitType [ optional, keyword-only ]
            The type for restricting the keys of the dict. If
            unspecified, the types of the keys are not checked.
        default_value : SequenceType [ optional, keyword-only ]
            The default value for the Dict.  Must be dict, tuple, or None, and
            will be cast to a dict if not None. If any key or value traits are specified,
            the `default_value` must conform to the constraints.

        Examples
        --------
        a dict whose values must be text
        >>> d = Dict(Unicode())

        d2['n'] must be an integer
        d2['s'] must be text
        >>> d2 = Dict(per_key_traits={"n": Integer(), "s": Unicode()})

        d3's keys must be text
        d3's values must be integers
        >>> d3 = Dict(value_trait=Integer(), key_trait=Unicode())

        """

        # handle deprecated keywords
        trait = kwargs.pop("trait", None)
        if trait is not None:
            if value_trait is not None:
                raise TypeError(
                    "Found a value for both `value_trait` and its deprecated alias `trait`."
                )
            value_trait = trait
            warn(
                "Keyword `trait` is deprecated in traitlets 5.0, use `value_trait` instead",
                DeprecationWarning,
                stacklevel=2,
            )
        traits = kwargs.pop("traits", None)
        if traits is not None:
            if per_key_traits is not None:
                raise TypeError(
                    "Found a value for both `per_key_traits` and its deprecated alias `traits`."
                )
            per_key_traits = traits
            warn(
                "Keyword `traits` is deprecated in traitlets 5.0, use `per_key_traits` instead",
                DeprecationWarning,
                stacklevel=2,
            )

        # Handling positional arguments
        if default_value is Undefined and value_trait is not None:
            if not is_trait(value_trait):
                assert not isinstance(value_trait, TraitType)
                default_value = value_trait
                value_trait = None

        if key_trait is None and per_key_traits is not None:
            if is_trait(per_key_traits):
                key_trait = per_key_traits
                per_key_traits = None

        # Handling default value
        if default_value is Undefined:
            default_value = {}
        if default_value is None:
            args: t.Any = None
        elif isinstance(default_value, dict):
            args = (default_value,)
        elif isinstance(default_value, SequenceTypes):
            args = (default_value,)
        else:
            raise TypeError("default value of Dict was %s" % default_value)

        # Case where a type of TraitType is provided rather than an instance
        if is_trait(value_trait):
            if isinstance(value_trait, type):
                warn(  # type:ignore[unreachable]
                    "Traits should be given as instances, not types (for example, `Int()`, not `Int`)"
                    " Passing types is deprecated in traitlets 4.1.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                value_trait = value_trait()
            self._value_trait = value_trait
        elif value_trait is not None:
            raise TypeError(
                "`value_trait` must be a Trait or None, got %s" % repr_type(value_trait)
            )

        if is_trait(key_trait):
            if isinstance(key_trait, type):
                warn(  # type:ignore[unreachable]
                    "Traits should be given as instances, not types (for example, `Int()`, not `Int`)"
                    " Passing types is deprecated in traitlets 4.1.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                key_trait = key_trait()
            self._key_trait = key_trait
        elif key_trait is not None:
            raise TypeError("`key_trait` must be a Trait or None, got %s" % repr_type(key_trait))

        self._per_key_traits = per_key_traits

        super().__init__(klass=dict, args=args, **kwargs)

    def element_error(
        self, obj: t.Any, element: t.Any, validator: t.Any, side: str = "Values"
    ) -> None:
        e = (
            side
            + f" of the '{self.name}' trait of {class_of(obj)} instance must be {validator.info()}, but a value of {repr_type(element)} was specified."
        )
        raise TraitError(e)

    def validate(self, obj: t.Any, value: t.Any) -> dict[K, V] | None:
        value = super().validate(obj, value)
        if value is None:
            return value
        return self.validate_elements(obj, value)

    def validate_elements(self, obj: t.Any, value: dict[t.Any, t.Any]) -> dict[K, V] | None:
        per_key_override = self._per_key_traits or {}
        key_trait = self._key_trait
        value_trait = self._value_trait
        if not (key_trait or value_trait or per_key_override):
            return value

        validated = {}
        for key in value:
            v = value[key]
            if key_trait:
                try:
                    key = key_trait._validate(obj, key)
                except TraitError:
                    self.element_error(obj, key, key_trait, "Keys")
            active_value_trait = per_key_override.get(key, value_trait)
            if active_value_trait:
                try:
                    v = active_value_trait._validate(obj, v)
                except TraitError:
                    self.element_error(obj, v, active_value_trait, "Values")
            validated[key] = v

        return self.klass(validated)  # type:ignore[misc,operator]

    def class_init(self, cls: type[t.Any], name: str | None) -> None:
        if isinstance(self._value_trait, TraitType):
            self._value_trait.class_init(cls, None)
        if isinstance(self._key_trait, TraitType):
            self._key_trait.class_init(cls, None)
        if self._per_key_traits is not None:
            for trait in self._per_key_traits.values():
                trait.class_init(cls, None)
        super().class_init(cls, name)

    def subclass_init(self, cls: type[t.Any]) -> None:
        if isinstance(self._value_trait, TraitType):
            self._value_trait.subclass_init(cls)
        if isinstance(self._key_trait, TraitType):
            self._key_trait.subclass_init(cls)
        if self._per_key_traits is not None:
            for trait in self._per_key_traits.values():
                trait.subclass_init(cls)
        # explicitly not calling super().subclass_init(cls)
        # to opt out of instance_init

    def from_string(self, s: str) -> dict[K, V] | None:
        """Load value from a single string"""
        if not isinstance(s, str):
            raise TypeError(f"from_string expects a string, got {s!r} of type {type(s)}")
        try:
            return t.cast("dict[K, V]", self.from_string_list([s]))
        except Exception:
            test = _safe_literal_eval(s)
            if isinstance(test, dict):
                return test
            raise

    def from_string_list(self, s_list: list[str]) -> t.Any:
        """Return a dict from a list of config strings.

        This is where we parse CLI configuration.

        Each item should have the form ``"key=value"``.

        item parsing is done in :meth:`.item_from_string`.
        """
        if len(s_list) == 1 and s_list[0] == "None" and self.allow_none:
            return None
        if len(s_list) == 1 and s_list[0].startswith("{") and s_list[0].endswith("}"):
            warn(
                f"--{self.name}={s_list[0]} for dict-traits is deprecated in traitlets 5.0. "
                f"You can pass --{self.name} <key=value> ... multiple times to add items to a dict.",
                DeprecationWarning,
                stacklevel=2,
            )

            return literal_eval(s_list[0])

        combined = {}
        for d in [self.item_from_string(s) for s in s_list]:
            combined.update(d)
        return combined

    def item_from_string(self, s: str) -> dict[K, V]:
        """Cast a single-key dict from a string.

        Evaluated when parsing CLI configuration from a string.

        Dicts expect strings of the form key=value.

        Returns a one-key dictionary,
        which will be merged in :meth:`.from_string_list`.
        """

        if "=" not in s:
            raise TraitError(
                f"'{self.__class__.__name__}' options must have the form 'key=value', got {s!r}"
            )
        key, value = s.split("=", 1)

        # cast key with key trait, if defined
        if self._key_trait:
            key = self._key_trait.from_string(key)

        # cast value with value trait, if defined (per-key or global)
        value_trait = (self._per_key_traits or {}).get(key, self._value_trait)
        if value_trait:
            value = value_trait.from_string(value)
        return t.cast("dict[K, V]", {key: value})


class TCPAddress(TraitType[G, S]):
    """A trait for an (ip, port) tuple.

    This allows for both IPv4 IP addresses as well as hostnames.
    """

    default_value = ("127.0.0.1", 0)
    info_text = "an (ip, port) tuple"

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: TCPAddress[tuple[str, int], tuple[str, int]],
            default_value: bool | Sentinel = ...,
            allow_none: Literal[False] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: TCPAddress[tuple[str, int] | None, tuple[str, int] | None],
            default_value: bool | None | Sentinel = ...,
            allow_none: Literal[True] = ...,
            read_only: bool | None = ...,
            help: str | None = ...,
            config: t.Any = ...,
            **kwargs: t.Any,
        ) -> None:
            ...

        def __init__(
            self: TCPAddress[tuple[str, int] | None, tuple[str, int] | None]
            | TCPAddress[tuple[str, int], tuple[str, int]],
            default_value: bool | None | Sentinel = Undefined,
            allow_none: Literal[True, False] = False,
            read_only: bool | None = None,
            help: str | None = None,
            config: t.Any = None,
            **kwargs: t.Any,
        ) -> None:
            ...

    def validate(self, obj: t.Any, value: t.Any) -> G:
        if isinstance(value, tuple):
            if len(value) == 2:
                if isinstance(value[0], str) and isinstance(value[1], int):
                    port = value[1]
                    if port >= 0 and port <= 65535:
                        return t.cast(G, value)
        self.error(obj, value)

    def from_string(self, s: str) -> G:
        if self.allow_none and s == "None":
            return t.cast(G, None)
        if ":" not in s:
            raise ValueError("Require `ip:port`, got %r" % s)
        ip, port_str = s.split(":", 1)
        port = int(port_str)
        return t.cast(G, (ip, port))


class CRegExp(TraitType["re.Pattern[t.Any]", t.Union["re.Pattern[t.Any]", str]]):
    """A casting compiled regular expression trait.

    Accepts both strings and compiled regular expressions. The resulting
    attribute will be a compiled regular expression."""

    info_text = "a regular expression"

    def validate(self, obj: t.Any, value: t.Any) -> re.Pattern[t.Any] | None:
        try:
            return re.compile(value)
        except Exception:
            self.error(obj, value)


class UseEnum(TraitType[t.Any, t.Any]):
    """Use a Enum class as model for the data type description.
    Note that if no default-value is provided, the first enum-value is used
    as default-value.

    .. sourcecode:: python

        # -- SINCE: Python 3.4 (or install backport: pip install enum34)
        import enum
        from traitlets import HasTraits, UseEnum


        class Color(enum.Enum):
            red = 1  # -- IMPLICIT: default_value
            blue = 2
            green = 3


        class MyEntity(HasTraits):
            color = UseEnum(Color, default_value=Color.blue)


        entity = MyEntity(color=Color.red)
        entity.color = Color.green  # USE: Enum-value (preferred)
        entity.color = "green"  # USE: name (as string)
        entity.color = "Color.green"  # USE: scoped-name (as string)
        entity.color = 3  # USE: number (as int)
        assert entity.color is Color.green
    """

    default_value: enum.Enum | None = None
    info_text = "Trait type adapter to a Enum class"

    def __init__(
        self, enum_class: type[t.Any], default_value: t.Any = None, **kwargs: t.Any
    ) -> None:
        assert issubclass(enum_class, enum.Enum), "REQUIRE: enum.Enum, but was: %r" % enum_class
        allow_none = kwargs.get("allow_none", False)
        if default_value is None and not allow_none:
            default_value = next(iter(enum_class.__members__.values()))
        super().__init__(default_value=default_value, **kwargs)
        self.enum_class = enum_class
        self.name_prefix = enum_class.__name__ + "."

    def select_by_number(self, value: int, default: t.Any = Undefined) -> t.Any:
        """Selects enum-value by using its number-constant."""
        assert isinstance(value, int)
        enum_members = self.enum_class.__members__
        for enum_item in enum_members.values():
            if enum_item.value == value:
                return enum_item
        # -- NOT FOUND:
        return default

    def select_by_name(self, value: str, default: t.Any = Undefined) -> t.Any:
        """Selects enum-value by using its name or scoped-name."""
        assert isinstance(value, str)
        if value.startswith(self.name_prefix):
            # -- SUPPORT SCOPED-NAMES, like: "Color.red" => "red"
            value = value.replace(self.name_prefix, "", 1)
        return self.enum_class.__members__.get(value, default)

    def validate(self, obj: t.Any, value: t.Any) -> t.Any:
        if isinstance(value, self.enum_class):
            return value
        elif isinstance(value, int):
            # -- CONVERT: number => enum_value (item)
            value2 = self.select_by_number(value)
            if value2 is not Undefined:
                return value2
        elif isinstance(value, str):
            # -- CONVERT: name or scoped_name (as string) => enum_value (item)
            value2 = self.select_by_name(value)
            if value2 is not Undefined:
                return value2
        elif value is None:
            if self.allow_none:
                return None
            else:
                return self.default_value
        self.error(obj, value)

    def _choices_str(self, as_rst: bool = False) -> str:
        """Returns a description of the trait choices (not none)."""
        choices = self.enum_class.__members__.keys()
        if as_rst:
            return "|".join("``%r``" % x for x in choices)
        else:
            return repr(list(choices))  # Listify because py3.4- prints odict-class

    def _info(self, as_rst: bool = False) -> str:
        """Returns a description of the trait."""
        none = " or %s" % ("`None`" if as_rst else "None") if self.allow_none else ""
        return f"any of {self._choices_str(as_rst)}{none}"

    def info(self) -> str:
        return self._info(as_rst=False)

    def info_rst(self) -> str:
        return self._info(as_rst=True)


class Callable(TraitType[t.Callable[..., t.Any], t.Callable[..., t.Any]]):
    """A trait which is callable.

    Notes
    -----
    Classes are callable, as are instances
    with a __call__() method."""

    info_text = "a callable"

    def validate(self, obj: t.Any, value: t.Any) -> t.Any:
        if callable(value):
            return value
        else:
            self.error(obj, value)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\network.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Network
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import debugger
from . import emulation
from . import io
from . import page
from . import runtime
from . import security


class ResourceType(enum.Enum):
    '''
    Resource type as it was perceived by the rendering engine.
    '''
    DOCUMENT = "Document"
    STYLESHEET = "Stylesheet"
    IMAGE = "Image"
    MEDIA = "Media"
    FONT = "Font"
    SCRIPT = "Script"
    TEXT_TRACK = "TextTrack"
    XHR = "XHR"
    FETCH = "Fetch"
    PREFETCH = "Prefetch"
    EVENT_SOURCE = "EventSource"
    WEB_SOCKET = "WebSocket"
    MANIFEST = "Manifest"
    SIGNED_EXCHANGE = "SignedExchange"
    PING = "Ping"
    CSP_VIOLATION_REPORT = "CSPViolationReport"
    PREFLIGHT = "Preflight"
    OTHER = "Other"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class LoaderId(str):
    '''
    Unique loader identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> LoaderId:
        return cls(json)

    def __repr__(self):
        return 'LoaderId({})'.format(super().__repr__())


class RequestId(str):
    '''
    Unique network request identifier.
    Note that this does not identify individual HTTP requests that are part of
    a network request.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RequestId:
        return cls(json)

    def __repr__(self):
        return 'RequestId({})'.format(super().__repr__())


class InterceptionId(str):
    '''
    Unique intercepted request identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> InterceptionId:
        return cls(json)

    def __repr__(self):
        return 'InterceptionId({})'.format(super().__repr__())


class ErrorReason(enum.Enum):
    '''
    Network level fetch failure reason.
    '''
    FAILED = "Failed"
    ABORTED = "Aborted"
    TIMED_OUT = "TimedOut"
    ACCESS_DENIED = "AccessDenied"
    CONNECTION_CLOSED = "ConnectionClosed"
    CONNECTION_RESET = "ConnectionReset"
    CONNECTION_REFUSED = "ConnectionRefused"
    CONNECTION_ABORTED = "ConnectionAborted"
    CONNECTION_FAILED = "ConnectionFailed"
    NAME_NOT_RESOLVED = "NameNotResolved"
    INTERNET_DISCONNECTED = "InternetDisconnected"
    ADDRESS_UNREACHABLE = "AddressUnreachable"
    BLOCKED_BY_CLIENT = "BlockedByClient"
    BLOCKED_BY_RESPONSE = "BlockedByResponse"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class TimeSinceEpoch(float):
    '''
    UTC time in seconds, counted from January 1, 1970.
    '''
    def to_json(self) -> float:
        return self

    @classmethod
    def from_json(cls, json: float) -> TimeSinceEpoch:
        return cls(json)

    def __repr__(self):
        return 'TimeSinceEpoch({})'.format(super().__repr__())


class MonotonicTime(float):
    '''
    Monotonically increasing time in seconds since an arbitrary point in the past.
    '''
    def to_json(self) -> float:
        return self

    @classmethod
    def from_json(cls, json: float) -> MonotonicTime:
        return cls(json)

    def __repr__(self):
        return 'MonotonicTime({})'.format(super().__repr__())


class Headers(dict):
    '''
    Request / response headers as keys / values of JSON object.
    '''
    def to_json(self) -> dict:
        return self

    @classmethod
    def from_json(cls, json: dict) -> Headers:
        return cls(json)

    def __repr__(self):
        return 'Headers({})'.format(super().__repr__())


class ConnectionType(enum.Enum):
    '''
    The underlying connection technology that the browser is supposedly using.
    '''
    NONE = "none"
    CELLULAR2G = "cellular2g"
    CELLULAR3G = "cellular3g"
    CELLULAR4G = "cellular4g"
    BLUETOOTH = "bluetooth"
    ETHERNET = "ethernet"
    WIFI = "wifi"
    WIMAX = "wimax"
    OTHER = "other"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieSameSite(enum.Enum):
    '''
    Represents the cookie's 'SameSite' status:
    https://tools.ietf.org/html/draft-west-first-party-cookies
    '''
    STRICT = "Strict"
    LAX = "Lax"
    NONE = "None"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookiePriority(enum.Enum):
    '''
    Represents the cookie's 'Priority' status:
    https://tools.ietf.org/html/draft-west-cookie-priority-00
    '''
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieSourceScheme(enum.Enum):
    '''
    Represents the source scheme of the origin that originally set the cookie.
    A value of "Unset" allows protocol clients to emulate legacy cookie scope for the scheme.
    This is a temporary ability and it will be removed in the future.
    '''
    UNSET = "Unset"
    NON_SECURE = "NonSecure"
    SECURE = "Secure"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ResourceTiming:
    '''
    Timing information for the request.
    '''
    #: Timing's requestTime is a baseline in seconds, while the other numbers are ticks in
    #: milliseconds relatively to this requestTime.
    request_time: float

    #: Started resolving proxy.
    proxy_start: float

    #: Finished resolving proxy.
    proxy_end: float

    #: Started DNS address resolve.
    dns_start: float

    #: Finished DNS address resolve.
    dns_end: float

    #: Started connecting to the remote host.
    connect_start: float

    #: Connected to the remote host.
    connect_end: float

    #: Started SSL handshake.
    ssl_start: float

    #: Finished SSL handshake.
    ssl_end: float

    #: Started running ServiceWorker.
    worker_start: float

    #: Finished Starting ServiceWorker.
    worker_ready: float

    #: Started fetch event.
    worker_fetch_start: float

    #: Settled fetch event respondWith promise.
    worker_respond_with_settled: float

    #: Started sending request.
    send_start: float

    #: Finished sending request.
    send_end: float

    #: Time the server started pushing request.
    push_start: float

    #: Time the server finished pushing request.
    push_end: float

    #: Started receiving response headers.
    receive_headers_start: float

    #: Finished receiving response headers.
    receive_headers_end: float

    #: Started ServiceWorker static routing source evaluation.
    worker_router_evaluation_start: typing.Optional[float] = None

    #: Started cache lookup when the source was evaluated to ``cache``.
    worker_cache_lookup_start: typing.Optional[float] = None

    def to_json(self):
        json = dict()
        json['requestTime'] = self.request_time
        json['proxyStart'] = self.proxy_start
        json['proxyEnd'] = self.proxy_end
        json['dnsStart'] = self.dns_start
        json['dnsEnd'] = self.dns_end
        json['connectStart'] = self.connect_start
        json['connectEnd'] = self.connect_end
        json['sslStart'] = self.ssl_start
        json['sslEnd'] = self.ssl_end
        json['workerStart'] = self.worker_start
        json['workerReady'] = self.worker_ready
        json['workerFetchStart'] = self.worker_fetch_start
        json['workerRespondWithSettled'] = self.worker_respond_with_settled
        json['sendStart'] = self.send_start
        json['sendEnd'] = self.send_end
        json['pushStart'] = self.push_start
        json['pushEnd'] = self.push_end
        json['receiveHeadersStart'] = self.receive_headers_start
        json['receiveHeadersEnd'] = self.receive_headers_end
        if self.worker_router_evaluation_start is not None:
            json['workerRouterEvaluationStart'] = self.worker_router_evaluation_start
        if self.worker_cache_lookup_start is not None:
            json['workerCacheLookupStart'] = self.worker_cache_lookup_start
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            request_time=float(json['requestTime']),
            proxy_start=float(json['proxyStart']),
            proxy_end=float(json['proxyEnd']),
            dns_start=float(json['dnsStart']),
            dns_end=float(json['dnsEnd']),
            connect_start=float(json['connectStart']),
            connect_end=float(json['connectEnd']),
            ssl_start=float(json['sslStart']),
            ssl_end=float(json['sslEnd']),
            worker_start=float(json['workerStart']),
            worker_ready=float(json['workerReady']),
            worker_fetch_start=float(json['workerFetchStart']),
            worker_respond_with_settled=float(json['workerRespondWithSettled']),
            send_start=float(json['sendStart']),
            send_end=float(json['sendEnd']),
            push_start=float(json['pushStart']),
            push_end=float(json['pushEnd']),
            receive_headers_start=float(json['receiveHeadersStart']),
            receive_headers_end=float(json['receiveHeadersEnd']),
            worker_router_evaluation_start=float(json['workerRouterEvaluationStart']) if 'workerRouterEvaluationStart' in json else None,
            worker_cache_lookup_start=float(json['workerCacheLookupStart']) if 'workerCacheLookupStart' in json else None,
        )


class ResourcePriority(enum.Enum):
    '''
    Loading priority of a resource request.
    '''
    VERY_LOW = "VeryLow"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "VeryHigh"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PostDataEntry:
    '''
    Post data entry for HTTP request
    '''
    bytes_: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        if self.bytes_ is not None:
            json['bytes'] = self.bytes_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            bytes_=str(json['bytes']) if 'bytes' in json else None,
        )


@dataclass
class Request:
    '''
    HTTP request data.
    '''
    #: Request URL (without fragment).
    url: str

    #: HTTP request method.
    method: str

    #: HTTP request headers.
    headers: Headers

    #: Priority of the resource request at the time request is sent.
    initial_priority: ResourcePriority

    #: The referrer policy of the request, as defined in https://www.w3.org/TR/referrer-policy/
    referrer_policy: str

    #: Fragment of the requested URL starting with hash, if present.
    url_fragment: typing.Optional[str] = None

    #: HTTP POST request data.
    #: Use postDataEntries instead.
    post_data: typing.Optional[str] = None

    #: True when the request has POST data. Note that postData might still be omitted when this flag is true when the data is too long.
    has_post_data: typing.Optional[bool] = None

    #: Request body elements (post data broken into individual entries).
    post_data_entries: typing.Optional[typing.List[PostDataEntry]] = None

    #: The mixed content type of the request.
    mixed_content_type: typing.Optional[security.MixedContentType] = None

    #: Whether is loaded via link preload.
    is_link_preload: typing.Optional[bool] = None

    #: Set for requests when the TrustToken API is used. Contains the parameters
    #: passed by the developer (e.g. via "fetch") as understood by the backend.
    trust_token_params: typing.Optional[TrustTokenParams] = None

    #: True if this resource request is considered to be the 'same site' as the
    #: request corresponding to the main frame.
    is_same_site: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['method'] = self.method
        json['headers'] = self.headers.to_json()
        json['initialPriority'] = self.initial_priority.to_json()
        json['referrerPolicy'] = self.referrer_policy
        if self.url_fragment is not None:
            json['urlFragment'] = self.url_fragment
        if self.post_data is not None:
            json['postData'] = self.post_data
        if self.has_post_data is not None:
            json['hasPostData'] = self.has_post_data
        if self.post_data_entries is not None:
            json['postDataEntries'] = [i.to_json() for i in self.post_data_entries]
        if self.mixed_content_type is not None:
            json['mixedContentType'] = self.mixed_content_type.to_json()
        if self.is_link_preload is not None:
            json['isLinkPreload'] = self.is_link_preload
        if self.trust_token_params is not None:
            json['trustTokenParams'] = self.trust_token_params.to_json()
        if self.is_same_site is not None:
            json['isSameSite'] = self.is_same_site
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            method=str(json['method']),
            headers=Headers.from_json(json['headers']),
            initial_priority=ResourcePriority.from_json(json['initialPriority']),
            referrer_policy=str(json['referrerPolicy']),
            url_fragment=str(json['urlFragment']) if 'urlFragment' in json else None,
            post_data=str(json['postData']) if 'postData' in json else None,
            has_post_data=bool(json['hasPostData']) if 'hasPostData' in json else None,
            post_data_entries=[PostDataEntry.from_json(i) for i in json['postDataEntries']] if 'postDataEntries' in json else None,
            mixed_content_type=security.MixedContentType.from_json(json['mixedContentType']) if 'mixedContentType' in json else None,
            is_link_preload=bool(json['isLinkPreload']) if 'isLinkPreload' in json else None,
            trust_token_params=TrustTokenParams.from_json(json['trustTokenParams']) if 'trustTokenParams' in json else None,
            is_same_site=bool(json['isSameSite']) if 'isSameSite' in json else None,
        )


@dataclass
class SignedCertificateTimestamp:
    '''
    Details of a signed certificate timestamp (SCT).
    '''
    #: Validation status.
    status: str

    #: Origin.
    origin: str

    #: Log name / description.
    log_description: str

    #: Log ID.
    log_id: str

    #: Issuance date. Unlike TimeSinceEpoch, this contains the number of
    #: milliseconds since January 1, 1970, UTC, not the number of seconds.
    timestamp: float

    #: Hash algorithm.
    hash_algorithm: str

    #: Signature algorithm.
    signature_algorithm: str

    #: Signature data.
    signature_data: str

    def to_json(self):
        json = dict()
        json['status'] = self.status
        json['origin'] = self.origin
        json['logDescription'] = self.log_description
        json['logId'] = self.log_id
        json['timestamp'] = self.timestamp
        json['hashAlgorithm'] = self.hash_algorithm
        json['signatureAlgorithm'] = self.signature_algorithm
        json['signatureData'] = self.signature_data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            status=str(json['status']),
            origin=str(json['origin']),
            log_description=str(json['logDescription']),
            log_id=str(json['logId']),
            timestamp=float(json['timestamp']),
            hash_algorithm=str(json['hashAlgorithm']),
            signature_algorithm=str(json['signatureAlgorithm']),
            signature_data=str(json['signatureData']),
        )


@dataclass
class SecurityDetails:
    '''
    Security details about a request.
    '''
    #: Protocol name (e.g. "TLS 1.2" or "QUIC").
    protocol: str

    #: Key Exchange used by the connection, or the empty string if not applicable.
    key_exchange: str

    #: Cipher name.
    cipher: str

    #: Certificate ID value.
    certificate_id: security.CertificateId

    #: Certificate subject name.
    subject_name: str

    #: Subject Alternative Name (SAN) DNS names and IP addresses.
    san_list: typing.List[str]

    #: Name of the issuing CA.
    issuer: str

    #: Certificate valid from date.
    valid_from: TimeSinceEpoch

    #: Certificate valid to (expiration) date
    valid_to: TimeSinceEpoch

    #: List of signed certificate timestamps (SCTs).
    signed_certificate_timestamp_list: typing.List[SignedCertificateTimestamp]

    #: Whether the request complied with Certificate Transparency policy
    certificate_transparency_compliance: CertificateTransparencyCompliance

    #: Whether the connection used Encrypted ClientHello
    encrypted_client_hello: bool

    #: (EC)DH group used by the connection, if applicable.
    key_exchange_group: typing.Optional[str] = None

    #: TLS MAC. Note that AEAD ciphers do not have separate MACs.
    mac: typing.Optional[str] = None

    #: The signature algorithm used by the server in the TLS server signature,
    #: represented as a TLS SignatureScheme code point. Omitted if not
    #: applicable or not known.
    server_signature_algorithm: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        json['protocol'] = self.protocol
        json['keyExchange'] = self.key_exchange
        json['cipher'] = self.cipher
        json['certificateId'] = self.certificate_id.to_json()
        json['subjectName'] = self.subject_name
        json['sanList'] = [i for i in self.san_list]
        json['issuer'] = self.issuer
        json['validFrom'] = self.valid_from.to_json()
        json['validTo'] = self.valid_to.to_json()
        json['signedCertificateTimestampList'] = [i.to_json() for i in self.signed_certificate_timestamp_list]
        json['certificateTransparencyCompliance'] = self.certificate_transparency_compliance.to_json()
        json['encryptedClientHello'] = self.encrypted_client_hello
        if self.key_exchange_group is not None:
            json['keyExchangeGroup'] = self.key_exchange_group
        if self.mac is not None:
            json['mac'] = self.mac
        if self.server_signature_algorithm is not None:
            json['serverSignatureAlgorithm'] = self.server_signature_algorithm
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            protocol=str(json['protocol']),
            key_exchange=str(json['keyExchange']),
            cipher=str(json['cipher']),
            certificate_id=security.CertificateId.from_json(json['certificateId']),
            subject_name=str(json['subjectName']),
            san_list=[str(i) for i in json['sanList']],
            issuer=str(json['issuer']),
            valid_from=TimeSinceEpoch.from_json(json['validFrom']),
            valid_to=TimeSinceEpoch.from_json(json['validTo']),
            signed_certificate_timestamp_list=[SignedCertificateTimestamp.from_json(i) for i in json['signedCertificateTimestampList']],
            certificate_transparency_compliance=CertificateTransparencyCompliance.from_json(json['certificateTransparencyCompliance']),
            encrypted_client_hello=bool(json['encryptedClientHello']),
            key_exchange_group=str(json['keyExchangeGroup']) if 'keyExchangeGroup' in json else None,
            mac=str(json['mac']) if 'mac' in json else None,
            server_signature_algorithm=int(json['serverSignatureAlgorithm']) if 'serverSignatureAlgorithm' in json else None,
        )


class CertificateTransparencyCompliance(enum.Enum):
    '''
    Whether the request complied with Certificate Transparency policy.
    '''
    UNKNOWN = "unknown"
    NOT_COMPLIANT = "not-compliant"
    COMPLIANT = "compliant"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class BlockedReason(enum.Enum):
    '''
    The reason why request was blocked.
    '''
    OTHER = "other"
    CSP = "csp"
    MIXED_CONTENT = "mixed-content"
    ORIGIN = "origin"
    INSPECTOR = "inspector"
    SUBRESOURCE_FILTER = "subresource-filter"
    CONTENT_TYPE = "content-type"
    COEP_FRAME_RESOURCE_NEEDS_COEP_HEADER = "coep-frame-resource-needs-coep-header"
    COOP_SANDBOXED_IFRAME_CANNOT_NAVIGATE_TO_COOP_PAGE = "coop-sandboxed-iframe-cannot-navigate-to-coop-page"
    CORP_NOT_SAME_ORIGIN = "corp-not-same-origin"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_COEP = "corp-not-same-origin-after-defaulted-to-same-origin-by-coep"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_DIP = "corp-not-same-origin-after-defaulted-to-same-origin-by-dip"
    CORP_NOT_SAME_ORIGIN_AFTER_DEFAULTED_TO_SAME_ORIGIN_BY_COEP_AND_DIP = "corp-not-same-origin-after-defaulted-to-same-origin-by-coep-and-dip"
    CORP_NOT_SAME_SITE = "corp-not-same-site"
    SRI_MESSAGE_SIGNATURE_MISMATCH = "sri-message-signature-mismatch"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CorsError(enum.Enum):
    '''
    The reason why request was blocked.
    '''
    DISALLOWED_BY_MODE = "DisallowedByMode"
    INVALID_RESPONSE = "InvalidResponse"
    WILDCARD_ORIGIN_NOT_ALLOWED = "WildcardOriginNotAllowed"
    MISSING_ALLOW_ORIGIN_HEADER = "MissingAllowOriginHeader"
    MULTIPLE_ALLOW_ORIGIN_VALUES = "MultipleAllowOriginValues"
    INVALID_ALLOW_ORIGIN_VALUE = "InvalidAllowOriginValue"
    ALLOW_ORIGIN_MISMATCH = "AllowOriginMismatch"
    INVALID_ALLOW_CREDENTIALS = "InvalidAllowCredentials"
    CORS_DISABLED_SCHEME = "CorsDisabledScheme"
    PREFLIGHT_INVALID_STATUS = "PreflightInvalidStatus"
    PREFLIGHT_DISALLOWED_REDIRECT = "PreflightDisallowedRedirect"
    PREFLIGHT_WILDCARD_ORIGIN_NOT_ALLOWED = "PreflightWildcardOriginNotAllowed"
    PREFLIGHT_MISSING_ALLOW_ORIGIN_HEADER = "PreflightMissingAllowOriginHeader"
    PREFLIGHT_MULTIPLE_ALLOW_ORIGIN_VALUES = "PreflightMultipleAllowOriginValues"
    PREFLIGHT_INVALID_ALLOW_ORIGIN_VALUE = "PreflightInvalidAllowOriginValue"
    PREFLIGHT_ALLOW_ORIGIN_MISMATCH = "PreflightAllowOriginMismatch"
    PREFLIGHT_INVALID_ALLOW_CREDENTIALS = "PreflightInvalidAllowCredentials"
    PREFLIGHT_MISSING_ALLOW_EXTERNAL = "PreflightMissingAllowExternal"
    PREFLIGHT_INVALID_ALLOW_EXTERNAL = "PreflightInvalidAllowExternal"
    PREFLIGHT_MISSING_ALLOW_PRIVATE_NETWORK = "PreflightMissingAllowPrivateNetwork"
    PREFLIGHT_INVALID_ALLOW_PRIVATE_NETWORK = "PreflightInvalidAllowPrivateNetwork"
    INVALID_ALLOW_METHODS_PREFLIGHT_RESPONSE = "InvalidAllowMethodsPreflightResponse"
    INVALID_ALLOW_HEADERS_PREFLIGHT_RESPONSE = "InvalidAllowHeadersPreflightResponse"
    METHOD_DISALLOWED_BY_PREFLIGHT_RESPONSE = "MethodDisallowedByPreflightResponse"
    HEADER_DISALLOWED_BY_PREFLIGHT_RESPONSE = "HeaderDisallowedByPreflightResponse"
    REDIRECT_CONTAINS_CREDENTIALS = "RedirectContainsCredentials"
    INSECURE_PRIVATE_NETWORK = "InsecurePrivateNetwork"
    INVALID_PRIVATE_NETWORK_ACCESS = "InvalidPrivateNetworkAccess"
    UNEXPECTED_PRIVATE_NETWORK_ACCESS = "UnexpectedPrivateNetworkAccess"
    NO_CORS_REDIRECT_MODE_NOT_FOLLOW = "NoCorsRedirectModeNotFollow"
    PREFLIGHT_MISSING_PRIVATE_NETWORK_ACCESS_ID = "PreflightMissingPrivateNetworkAccessId"
    PREFLIGHT_MISSING_PRIVATE_NETWORK_ACCESS_NAME = "PreflightMissingPrivateNetworkAccessName"
    PRIVATE_NETWORK_ACCESS_PERMISSION_UNAVAILABLE = "PrivateNetworkAccessPermissionUnavailable"
    PRIVATE_NETWORK_ACCESS_PERMISSION_DENIED = "PrivateNetworkAccessPermissionDenied"
    LOCAL_NETWORK_ACCESS_PERMISSION_DENIED = "LocalNetworkAccessPermissionDenied"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class CorsErrorStatus:
    cors_error: CorsError

    failed_parameter: str

    def to_json(self):
        json = dict()
        json['corsError'] = self.cors_error.to_json()
        json['failedParameter'] = self.failed_parameter
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cors_error=CorsError.from_json(json['corsError']),
            failed_parameter=str(json['failedParameter']),
        )


class ServiceWorkerResponseSource(enum.Enum):
    '''
    Source of serviceworker response.
    '''
    CACHE_STORAGE = "cache-storage"
    HTTP_CACHE = "http-cache"
    FALLBACK_CODE = "fallback-code"
    NETWORK = "network"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class TrustTokenParams:
    '''
    Determines what type of Trust Token operation is executed and
    depending on the type, some additional parameters. The values
    are specified in third_party/blink/renderer/core/fetch/trust_token.idl.
    '''
    operation: TrustTokenOperationType

    #: Only set for "token-redemption" operation and determine whether
    #: to request a fresh SRR or use a still valid cached SRR.
    refresh_policy: str

    #: Origins of issuers from whom to request tokens or redemption
    #: records.
    issuers: typing.Optional[typing.List[str]] = None

    def to_json(self):
        json = dict()
        json['operation'] = self.operation.to_json()
        json['refreshPolicy'] = self.refresh_policy
        if self.issuers is not None:
            json['issuers'] = [i for i in self.issuers]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            operation=TrustTokenOperationType.from_json(json['operation']),
            refresh_policy=str(json['refreshPolicy']),
            issuers=[str(i) for i in json['issuers']] if 'issuers' in json else None,
        )


class TrustTokenOperationType(enum.Enum):
    ISSUANCE = "Issuance"
    REDEMPTION = "Redemption"
    SIGNING = "Signing"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AlternateProtocolUsage(enum.Enum):
    '''
    The reason why Chrome uses a specific transport protocol for HTTP semantics.
    '''
    ALTERNATIVE_JOB_WON_WITHOUT_RACE = "alternativeJobWonWithoutRace"
    ALTERNATIVE_JOB_WON_RACE = "alternativeJobWonRace"
    MAIN_JOB_WON_RACE = "mainJobWonRace"
    MAPPING_MISSING = "mappingMissing"
    BROKEN = "broken"
    DNS_ALPN_H3_JOB_WON_WITHOUT_RACE = "dnsAlpnH3JobWonWithoutRace"
    DNS_ALPN_H3_JOB_WON_RACE = "dnsAlpnH3JobWonRace"
    UNSPECIFIED_REASON = "unspecifiedReason"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ServiceWorkerRouterSource(enum.Enum):
    '''
    Source of service worker router.
    '''
    NETWORK = "network"
    CACHE = "cache"
    FETCH_EVENT = "fetch-event"
    RACE_NETWORK_AND_FETCH_HANDLER = "race-network-and-fetch-handler"
    RACE_NETWORK_AND_CACHE = "race-network-and-cache"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ServiceWorkerRouterInfo:
    #: ID of the rule matched. If there is a matched rule, this field will
    #: be set, otherwiser no value will be set.
    rule_id_matched: typing.Optional[int] = None

    #: The router source of the matched rule. If there is a matched rule, this
    #: field will be set, otherwise no value will be set.
    matched_source_type: typing.Optional[ServiceWorkerRouterSource] = None

    #: The actual router source used.
    actual_source_type: typing.Optional[ServiceWorkerRouterSource] = None

    def to_json(self):
        json = dict()
        if self.rule_id_matched is not None:
            json['ruleIdMatched'] = self.rule_id_matched
        if self.matched_source_type is not None:
            json['matchedSourceType'] = self.matched_source_type.to_json()
        if self.actual_source_type is not None:
            json['actualSourceType'] = self.actual_source_type.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            rule_id_matched=int(json['ruleIdMatched']) if 'ruleIdMatched' in json else None,
            matched_source_type=ServiceWorkerRouterSource.from_json(json['matchedSourceType']) if 'matchedSourceType' in json else None,
            actual_source_type=ServiceWorkerRouterSource.from_json(json['actualSourceType']) if 'actualSourceType' in json else None,
        )


@dataclass
class Response:
    '''
    HTTP response data.
    '''
    #: Response URL. This URL can be different from CachedResource.url in case of redirect.
    url: str

    #: HTTP response status code.
    status: int

    #: HTTP response status text.
    status_text: str

    #: HTTP response headers.
    headers: Headers

    #: Resource mimeType as determined by the browser.
    mime_type: str

    #: Resource charset as determined by the browser (if applicable).
    charset: str

    #: Specifies whether physical connection was actually reused for this request.
    connection_reused: bool

    #: Physical connection id that was actually used for this request.
    connection_id: float

    #: Total number of bytes received for this request so far.
    encoded_data_length: float

    #: Security state of the request resource.
    security_state: security.SecurityState

    #: HTTP response headers text. This has been replaced by the headers in Network.responseReceivedExtraInfo.
    headers_text: typing.Optional[str] = None

    #: Refined HTTP request headers that were actually transmitted over the network.
    request_headers: typing.Optional[Headers] = None

    #: HTTP request headers text. This has been replaced by the headers in Network.requestWillBeSentExtraInfo.
    request_headers_text: typing.Optional[str] = None

    #: Remote IP address.
    remote_ip_address: typing.Optional[str] = None

    #: Remote port.
    remote_port: typing.Optional[int] = None

    #: Specifies that the request was served from the disk cache.
    from_disk_cache: typing.Optional[bool] = None

    #: Specifies that the request was served from the ServiceWorker.
    from_service_worker: typing.Optional[bool] = None

    #: Specifies that the request was served from the prefetch cache.
    from_prefetch_cache: typing.Optional[bool] = None

    #: Specifies that the request was served from the prefetch cache.
    from_early_hints: typing.Optional[bool] = None

    #: Information about how ServiceWorker Static Router API was used. If this
    #: field is set with ``matchedSourceType`` field, a matching rule is found.
    #: If this field is set without ``matchedSource``, no matching rule is found.
    #: Otherwise, the API is not used.
    service_worker_router_info: typing.Optional[ServiceWorkerRouterInfo] = None

    #: Timing information for the given request.
    timing: typing.Optional[ResourceTiming] = None

    #: Response source of response from ServiceWorker.
    service_worker_response_source: typing.Optional[ServiceWorkerResponseSource] = None

    #: The time at which the returned response was generated.
    response_time: typing.Optional[TimeSinceEpoch] = None

    #: Cache Storage Cache Name.
    cache_storage_cache_name: typing.Optional[str] = None

    #: Protocol used to fetch this request.
    protocol: typing.Optional[str] = None

    #: The reason why Chrome uses a specific transport protocol for HTTP semantics.
    alternate_protocol_usage: typing.Optional[AlternateProtocolUsage] = None

    #: Security details for the request.
    security_details: typing.Optional[SecurityDetails] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['status'] = self.status
        json['statusText'] = self.status_text
        json['headers'] = self.headers.to_json()
        json['mimeType'] = self.mime_type
        json['charset'] = self.charset
        json['connectionReused'] = self.connection_reused
        json['connectionId'] = self.connection_id
        json['encodedDataLength'] = self.encoded_data_length
        json['securityState'] = self.security_state.to_json()
        if self.headers_text is not None:
            json['headersText'] = self.headers_text
        if self.request_headers is not None:
            json['requestHeaders'] = self.request_headers.to_json()
        if self.request_headers_text is not None:
            json['requestHeadersText'] = self.request_headers_text
        if self.remote_ip_address is not None:
            json['remoteIPAddress'] = self.remote_ip_address
        if self.remote_port is not None:
            json['remotePort'] = self.remote_port
        if self.from_disk_cache is not None:
            json['fromDiskCache'] = self.from_disk_cache
        if self.from_service_worker is not None:
            json['fromServiceWorker'] = self.from_service_worker
        if self.from_prefetch_cache is not None:
            json['fromPrefetchCache'] = self.from_prefetch_cache
        if self.from_early_hints is not None:
            json['fromEarlyHints'] = self.from_early_hints
        if self.service_worker_router_info is not None:
            json['serviceWorkerRouterInfo'] = self.service_worker_router_info.to_json()
        if self.timing is not None:
            json['timing'] = self.timing.to_json()
        if self.service_worker_response_source is not None:
            json['serviceWorkerResponseSource'] = self.service_worker_response_source.to_json()
        if self.response_time is not None:
            json['responseTime'] = self.response_time.to_json()
        if self.cache_storage_cache_name is not None:
            json['cacheStorageCacheName'] = self.cache_storage_cache_name
        if self.protocol is not None:
            json['protocol'] = self.protocol
        if self.alternate_protocol_usage is not None:
            json['alternateProtocolUsage'] = self.alternate_protocol_usage.to_json()
        if self.security_details is not None:
            json['securityDetails'] = self.security_details.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            status=int(json['status']),
            status_text=str(json['statusText']),
            headers=Headers.from_json(json['headers']),
            mime_type=str(json['mimeType']),
            charset=str(json['charset']),
            connection_reused=bool(json['connectionReused']),
            connection_id=float(json['connectionId']),
            encoded_data_length=float(json['encodedDataLength']),
            security_state=security.SecurityState.from_json(json['securityState']),
            headers_text=str(json['headersText']) if 'headersText' in json else None,
            request_headers=Headers.from_json(json['requestHeaders']) if 'requestHeaders' in json else None,
            request_headers_text=str(json['requestHeadersText']) if 'requestHeadersText' in json else None,
            remote_ip_address=str(json['remoteIPAddress']) if 'remoteIPAddress' in json else None,
            remote_port=int(json['remotePort']) if 'remotePort' in json else None,
            from_disk_cache=bool(json['fromDiskCache']) if 'fromDiskCache' in json else None,
            from_service_worker=bool(json['fromServiceWorker']) if 'fromServiceWorker' in json else None,
            from_prefetch_cache=bool(json['fromPrefetchCache']) if 'fromPrefetchCache' in json else None,
            from_early_hints=bool(json['fromEarlyHints']) if 'fromEarlyHints' in json else None,
            service_worker_router_info=ServiceWorkerRouterInfo.from_json(json['serviceWorkerRouterInfo']) if 'serviceWorkerRouterInfo' in json else None,
            timing=ResourceTiming.from_json(json['timing']) if 'timing' in json else None,
            service_worker_response_source=ServiceWorkerResponseSource.from_json(json['serviceWorkerResponseSource']) if 'serviceWorkerResponseSource' in json else None,
            response_time=TimeSinceEpoch.from_json(json['responseTime']) if 'responseTime' in json else None,
            cache_storage_cache_name=str(json['cacheStorageCacheName']) if 'cacheStorageCacheName' in json else None,
            protocol=str(json['protocol']) if 'protocol' in json else None,
            alternate_protocol_usage=AlternateProtocolUsage.from_json(json['alternateProtocolUsage']) if 'alternateProtocolUsage' in json else None,
            security_details=SecurityDetails.from_json(json['securityDetails']) if 'securityDetails' in json else None,
        )


@dataclass
class WebSocketRequest:
    '''
    WebSocket request data.
    '''
    #: HTTP request headers.
    headers: Headers

    def to_json(self):
        json = dict()
        json['headers'] = self.headers.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            headers=Headers.from_json(json['headers']),
        )


@dataclass
class WebSocketResponse:
    '''
    WebSocket response data.
    '''
    #: HTTP response status code.
    status: int

    #: HTTP response status text.
    status_text: str

    #: HTTP response headers.
    headers: Headers

    #: HTTP response headers text.
    headers_text: typing.Optional[str] = None

    #: HTTP request headers.
    request_headers: typing.Optional[Headers] = None

    #: HTTP request headers text.
    request_headers_text: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['status'] = self.status
        json['statusText'] = self.status_text
        json['headers'] = self.headers.to_json()
        if self.headers_text is not None:
            json['headersText'] = self.headers_text
        if self.request_headers is not None:
            json['requestHeaders'] = self.request_headers.to_json()
        if self.request_headers_text is not None:
            json['requestHeadersText'] = self.request_headers_text
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            status=int(json['status']),
            status_text=str(json['statusText']),
            headers=Headers.from_json(json['headers']),
            headers_text=str(json['headersText']) if 'headersText' in json else None,
            request_headers=Headers.from_json(json['requestHeaders']) if 'requestHeaders' in json else None,
            request_headers_text=str(json['requestHeadersText']) if 'requestHeadersText' in json else None,
        )


@dataclass
class WebSocketFrame:
    '''
    WebSocket message data. This represents an entire WebSocket message, not just a fragmented frame as the name suggests.
    '''
    #: WebSocket message opcode.
    opcode: float

    #: WebSocket message mask.
    mask: bool

    #: WebSocket message payload data.
    #: If the opcode is 1, this is a text message and payloadData is a UTF-8 string.
    #: If the opcode isn't 1, then payloadData is a base64 encoded string representing binary data.
    payload_data: str

    def to_json(self):
        json = dict()
        json['opcode'] = self.opcode
        json['mask'] = self.mask
        json['payloadData'] = self.payload_data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            opcode=float(json['opcode']),
            mask=bool(json['mask']),
            payload_data=str(json['payloadData']),
        )


@dataclass
class CachedResource:
    '''
    Information about the cached resource.
    '''
    #: Resource URL. This is the url of the original network request.
    url: str

    #: Type of this resource.
    type_: ResourceType

    #: Cached response body size.
    body_size: float

    #: Cached response data.
    response: typing.Optional[Response] = None

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['type'] = self.type_.to_json()
        json['bodySize'] = self.body_size
        if self.response is not None:
            json['response'] = self.response.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            type_=ResourceType.from_json(json['type']),
            body_size=float(json['bodySize']),
            response=Response.from_json(json['response']) if 'response' in json else None,
        )


@dataclass
class Initiator:
    '''
    Information about the request initiator.
    '''
    #: Type of this initiator.
    type_: str

    #: Initiator JavaScript stack trace, set for Script only.
    #: Requires the Debugger domain to be enabled.
    stack: typing.Optional[runtime.StackTrace] = None

    #: Initiator URL, set for Parser type or for Script type (when script is importing module) or for SignedExchange type.
    url: typing.Optional[str] = None

    #: Initiator line number, set for Parser type or for Script type (when script is importing
    #: module) (0-based).
    line_number: typing.Optional[float] = None

    #: Initiator column number, set for Parser type or for Script type (when script is importing
    #: module) (0-based).
    column_number: typing.Optional[float] = None

    #: Set if another request triggered this request (e.g. preflight).
    request_id: typing.Optional[RequestId] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.stack is not None:
            json['stack'] = self.stack.to_json()
        if self.url is not None:
            json['url'] = self.url
        if self.line_number is not None:
            json['lineNumber'] = self.line_number
        if self.column_number is not None:
            json['columnNumber'] = self.column_number
        if self.request_id is not None:
            json['requestId'] = self.request_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            stack=runtime.StackTrace.from_json(json['stack']) if 'stack' in json else None,
            url=str(json['url']) if 'url' in json else None,
            line_number=float(json['lineNumber']) if 'lineNumber' in json else None,
            column_number=float(json['columnNumber']) if 'columnNumber' in json else None,
            request_id=RequestId.from_json(json['requestId']) if 'requestId' in json else None,
        )


@dataclass
class CookiePartitionKey:
    '''
    cookiePartitionKey object
    The representation of the components of the key that are created by the cookiePartitionKey class contained in net/cookies/cookie_partition_key.h.
    '''
    #: The site of the top-level URL the browser was visiting at the start
    #: of the request to the endpoint that set the cookie.
    top_level_site: str

    #: Indicates if the cookie has any ancestors that are cross-site to the topLevelSite.
    has_cross_site_ancestor: bool

    def to_json(self):
        json = dict()
        json['topLevelSite'] = self.top_level_site
        json['hasCrossSiteAncestor'] = self.has_cross_site_ancestor
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            top_level_site=str(json['topLevelSite']),
            has_cross_site_ancestor=bool(json['hasCrossSiteAncestor']),
        )


@dataclass
class Cookie:
    '''
    Cookie object
    '''
    #: Cookie name.
    name: str

    #: Cookie value.
    value: str

    #: Cookie domain.
    domain: str

    #: Cookie path.
    path: str

    #: Cookie expiration date as the number of seconds since the UNIX epoch.
    expires: float

    #: Cookie size.
    size: int

    #: True if cookie is http-only.
    http_only: bool

    #: True if cookie is secure.
    secure: bool

    #: True in case of session cookie.
    session: bool

    #: Cookie Priority
    priority: CookiePriority

    #: True if cookie is SameParty.
    same_party: bool

    #: Cookie source scheme type.
    source_scheme: CookieSourceScheme

    #: Cookie source port. Valid values are {-1, [1, 65535]}, -1 indicates an unspecified port.
    #: An unspecified port value allows protocol clients to emulate legacy cookie scope for the port.
    #: This is a temporary ability and it will be removed in the future.
    source_port: int

    #: Cookie SameSite type.
    same_site: typing.Optional[CookieSameSite] = None

    #: Cookie partition key.
    partition_key: typing.Optional[CookiePartitionKey] = None

    #: True if cookie partition key is opaque.
    partition_key_opaque: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        json['domain'] = self.domain
        json['path'] = self.path
        json['expires'] = self.expires
        json['size'] = self.size
        json['httpOnly'] = self.http_only
        json['secure'] = self.secure
        json['session'] = self.session
        json['priority'] = self.priority.to_json()
        json['sameParty'] = self.same_party
        json['sourceScheme'] = self.source_scheme.to_json()
        json['sourcePort'] = self.source_port
        if self.same_site is not None:
            json['sameSite'] = self.same_site.to_json()
        if self.partition_key is not None:
            json['partitionKey'] = self.partition_key.to_json()
        if self.partition_key_opaque is not None:
            json['partitionKeyOpaque'] = self.partition_key_opaque
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
            domain=str(json['domain']),
            path=str(json['path']),
            expires=float(json['expires']),
            size=int(json['size']),
            http_only=bool(json['httpOnly']),
            secure=bool(json['secure']),
            session=bool(json['session']),
            priority=CookiePriority.from_json(json['priority']),
            same_party=bool(json['sameParty']),
            source_scheme=CookieSourceScheme.from_json(json['sourceScheme']),
            source_port=int(json['sourcePort']),
            same_site=CookieSameSite.from_json(json['sameSite']) if 'sameSite' in json else None,
            partition_key=CookiePartitionKey.from_json(json['partitionKey']) if 'partitionKey' in json else None,
            partition_key_opaque=bool(json['partitionKeyOpaque']) if 'partitionKeyOpaque' in json else None,
        )


class SetCookieBlockedReason(enum.Enum):
    '''
    Types of reasons why a cookie may not be stored from a response.
    '''
    SECURE_ONLY = "SecureOnly"
    SAME_SITE_STRICT = "SameSiteStrict"
    SAME_SITE_LAX = "SameSiteLax"
    SAME_SITE_UNSPECIFIED_TREATED_AS_LAX = "SameSiteUnspecifiedTreatedAsLax"
    SAME_SITE_NONE_INSECURE = "SameSiteNoneInsecure"
    USER_PREFERENCES = "UserPreferences"
    THIRD_PARTY_PHASEOUT = "ThirdPartyPhaseout"
    THIRD_PARTY_BLOCKED_IN_FIRST_PARTY_SET = "ThirdPartyBlockedInFirstPartySet"
    SYNTAX_ERROR = "SyntaxError"
    SCHEME_NOT_SUPPORTED = "SchemeNotSupported"
    OVERWRITE_SECURE = "OverwriteSecure"
    INVALID_DOMAIN = "InvalidDomain"
    INVALID_PREFIX = "InvalidPrefix"
    UNKNOWN_ERROR = "UnknownError"
    SCHEMEFUL_SAME_SITE_STRICT = "SchemefulSameSiteStrict"
    SCHEMEFUL_SAME_SITE_LAX = "SchemefulSameSiteLax"
    SCHEMEFUL_SAME_SITE_UNSPECIFIED_TREATED_AS_LAX = "SchemefulSameSiteUnspecifiedTreatedAsLax"
    SAME_PARTY_FROM_CROSS_PARTY_CONTEXT = "SamePartyFromCrossPartyContext"
    SAME_PARTY_CONFLICTS_WITH_OTHER_ATTRIBUTES = "SamePartyConflictsWithOtherAttributes"
    NAME_VALUE_PAIR_EXCEEDS_MAX_SIZE = "NameValuePairExceedsMaxSize"
    DISALLOWED_CHARACTER = "DisallowedCharacter"
    NO_COOKIE_CONTENT = "NoCookieContent"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieBlockedReason(enum.Enum):
    '''
    Types of reasons why a cookie may not be sent with a request.
    '''
    SECURE_ONLY = "SecureOnly"
    NOT_ON_PATH = "NotOnPath"
    DOMAIN_MISMATCH = "DomainMismatch"
    SAME_SITE_STRICT = "SameSiteStrict"
    SAME_SITE_LAX = "SameSiteLax"
    SAME_SITE_UNSPECIFIED_TREATED_AS_LAX = "SameSiteUnspecifiedTreatedAsLax"
    SAME_SITE_NONE_INSECURE = "SameSiteNoneInsecure"
    USER_PREFERENCES = "UserPreferences"
    THIRD_PARTY_PHASEOUT = "ThirdPartyPhaseout"
    THIRD_PARTY_BLOCKED_IN_FIRST_PARTY_SET = "ThirdPartyBlockedInFirstPartySet"
    UNKNOWN_ERROR = "UnknownError"
    SCHEMEFUL_SAME_SITE_STRICT = "SchemefulSameSiteStrict"
    SCHEMEFUL_SAME_SITE_LAX = "SchemefulSameSiteLax"
    SCHEMEFUL_SAME_SITE_UNSPECIFIED_TREATED_AS_LAX = "SchemefulSameSiteUnspecifiedTreatedAsLax"
    SAME_PARTY_FROM_CROSS_PARTY_CONTEXT = "SamePartyFromCrossPartyContext"
    NAME_VALUE_PAIR_EXCEEDS_MAX_SIZE = "NameValuePairExceedsMaxSize"
    PORT_MISMATCH = "PortMismatch"
    SCHEME_MISMATCH = "SchemeMismatch"
    ANONYMOUS_CONTEXT = "AnonymousContext"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CookieExemptionReason(enum.Enum):
    '''
    Types of reasons why a cookie should have been blocked by 3PCD but is exempted for the request.
    '''
    NONE = "None"
    USER_SETTING = "UserSetting"
    TPCD_METADATA = "TPCDMetadata"
    TPCD_DEPRECATION_TRIAL = "TPCDDeprecationTrial"
    TOP_LEVEL_TPCD_DEPRECATION_TRIAL = "TopLevelTPCDDeprecationTrial"
    TPCD_HEURISTICS = "TPCDHeuristics"
    ENTERPRISE_POLICY = "EnterprisePolicy"
    STORAGE_ACCESS = "StorageAccess"
    TOP_LEVEL_STORAGE_ACCESS = "TopLevelStorageAccess"
    SCHEME = "Scheme"
    SAME_SITE_NONE_COOKIES_IN_SANDBOX = "SameSiteNoneCookiesInSandbox"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class BlockedSetCookieWithReason:
    '''
    A cookie which was not stored from a response with the corresponding reason.
    '''
    #: The reason(s) this cookie was blocked.
    blocked_reasons: typing.List[SetCookieBlockedReason]

    #: The string representing this individual cookie as it would appear in the header.
    #: This is not the entire "cookie" or "set-cookie" header which could have multiple cookies.
    cookie_line: str

    #: The cookie object which represents the cookie which was not stored. It is optional because
    #: sometimes complete cookie information is not available, such as in the case of parsing
    #: errors.
    cookie: typing.Optional[Cookie] = None

    def to_json(self):
        json = dict()
        json['blockedReasons'] = [i.to_json() for i in self.blocked_reasons]
        json['cookieLine'] = self.cookie_line
        if self.cookie is not None:
            json['cookie'] = self.cookie.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            blocked_reasons=[SetCookieBlockedReason.from_json(i) for i in json['blockedReasons']],
            cookie_line=str(json['cookieLine']),
            cookie=Cookie.from_json(json['cookie']) if 'cookie' in json else None,
        )


@dataclass
class ExemptedSetCookieWithReason:
    '''
    A cookie should have been blocked by 3PCD but is exempted and stored from a response with the
    corresponding reason. A cookie could only have at most one exemption reason.
    '''
    #: The reason the cookie was exempted.
    exemption_reason: CookieExemptionReason

    #: The string representing this individual cookie as it would appear in the header.
    cookie_line: str

    #: The cookie object representing the cookie.
    cookie: Cookie

    def to_json(self):
        json = dict()
        json['exemptionReason'] = self.exemption_reason.to_json()
        json['cookieLine'] = self.cookie_line
        json['cookie'] = self.cookie.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            exemption_reason=CookieExemptionReason.from_json(json['exemptionReason']),
            cookie_line=str(json['cookieLine']),
            cookie=Cookie.from_json(json['cookie']),
        )


@dataclass
class AssociatedCookie:
    '''
    A cookie associated with the request which may or may not be sent with it.
    Includes the cookies itself and reasons for blocking or exemption.
    '''
    #: The cookie object representing the cookie which was not sent.
    cookie: Cookie

    #: The reason(s) the cookie was blocked. If empty means the cookie is included.
    blocked_reasons: typing.List[CookieBlockedReason]

    #: The reason the cookie should have been blocked by 3PCD but is exempted. A cookie could
    #: only have at most one exemption reason.
    exemption_reason: typing.Optional[CookieExemptionReason] = None

    def to_json(self):
        json = dict()
        json['cookie'] = self.cookie.to_json()
        json['blockedReasons'] = [i.to_json() for i in self.blocked_reasons]
        if self.exemption_reason is not None:
            json['exemptionReason'] = self.exemption_reason.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cookie=Cookie.from_json(json['cookie']),
            blocked_reasons=[CookieBlockedReason.from_json(i) for i in json['blockedReasons']],
            exemption_reason=CookieExemptionReason.from_json(json['exemptionReason']) if 'exemptionReason' in json else None,
        )


@dataclass
class CookieParam:
    '''
    Cookie parameter object
    '''
    #: Cookie name.
    name: str

    #: Cookie value.
    value: str

    #: The request-URI to associate with the setting of the cookie. This value can affect the
    #: default domain, path, source port, and source scheme values of the created cookie.
    url: typing.Optional[str] = None

    #: Cookie domain.
    domain: typing.Optional[str] = None

    #: Cookie path.
    path: typing.Optional[str] = None

    #: True if cookie is secure.
    secure: typing.Optional[bool] = None

    #: True if cookie is http-only.
    http_only: typing.Optional[bool] = None

    #: Cookie SameSite type.
    same_site: typing.Optional[CookieSameSite] = None

    #: Cookie expiration date, session cookie if not set
    expires: typing.Optional[TimeSinceEpoch] = None

    #: Cookie Priority.
    priority: typing.Optional[CookiePriority] = None

    #: True if cookie is SameParty.
    same_party: typing.Optional[bool] = None

    #: Cookie source scheme type.
    source_scheme: typing.Optional[CookieSourceScheme] = None

    #: Cookie source port. Valid values are {-1, [1, 65535]}, -1 indicates an unspecified port.
    #: An unspecified port value allows protocol clients to emulate legacy cookie scope for the port.
    #: This is a temporary ability and it will be removed in the future.
    source_port: typing.Optional[int] = None

    #: Cookie partition key. If not set, the cookie will be set as not partitioned.
    partition_key: typing.Optional[CookiePartitionKey] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        if self.url is not None:
            json['url'] = self.url
        if self.domain is not None:
            json['domain'] = self.domain
        if self.path is not None:
            json['path'] = self.path
        if self.secure is not None:
            json['secure'] = self.secure
        if self.http_only is not None:
            json['httpOnly'] = self.http_only
        if self.same_site is not None:
            json['sameSite'] = self.same_site.to_json()
        if self.expires is not None:
            json['expires'] = self.expires.to_json()
        if self.priority is not None:
            json['priority'] = self.priority.to_json()
        if self.same_party is not None:
            json['sameParty'] = self.same_party
        if self.source_scheme is not None:
            json['sourceScheme'] = self.source_scheme.to_json()
        if self.source_port is not None:
            json['sourcePort'] = self.source_port
        if self.partition_key is not None:
            json['partitionKey'] = self.partition_key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
            url=str(json['url']) if 'url' in json else None,
            domain=str(json['domain']) if 'domain' in json else None,
            path=str(json['path']) if 'path' in json else None,
            secure=bool(json['secure']) if 'secure' in json else None,
            http_only=bool(json['httpOnly']) if 'httpOnly' in json else None,
            same_site=CookieSameSite.from_json(json['sameSite']) if 'sameSite' in json else None,
            expires=TimeSinceEpoch.from_json(json['expires']) if 'expires' in json else None,
            priority=CookiePriority.from_json(json['priority']) if 'priority' in json else None,
            same_party=bool(json['sameParty']) if 'sameParty' in json else None,
            source_scheme=CookieSourceScheme.from_json(json['sourceScheme']) if 'sourceScheme' in json else None,
            source_port=int(json['sourcePort']) if 'sourcePort' in json else None,
            partition_key=CookiePartitionKey.from_json(json['partitionKey']) if 'partitionKey' in json else None,
        )


@dataclass
class AuthChallenge:
    '''
    Authorization challenge for HTTP status code 401 or 407.
    '''
    #: Origin of the challenger.
    origin: str

    #: The authentication scheme used, such as basic or digest
    scheme: str

    #: The realm of the challenge. May be empty.
    realm: str

    #: Source of the authentication challenge.
    source: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['origin'] = self.origin
        json['scheme'] = self.scheme
        json['realm'] = self.realm
        if self.source is not None:
            json['source'] = self.source
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            origin=str(json['origin']),
            scheme=str(json['scheme']),
            realm=str(json['realm']),
            source=str(json['source']) if 'source' in json else None,
        )


@dataclass
class AuthChallengeResponse:
    '''
    Response to an AuthChallenge.
    '''
    #: The decision on what to do in response to the authorization challenge.  Default means
    #: deferring to the default behavior of the net stack, which will likely either the Cancel
    #: authentication or display a popup dialog box.
    response: str

    #: The username to provide, possibly empty. Should only be set if response is
    #: ProvideCredentials.
    username: typing.Optional[str] = None

    #: The password to provide, possibly empty. Should only be set if response is
    #: ProvideCredentials.
    password: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['response'] = self.response
        if self.username is not None:
            json['username'] = self.username
        if self.password is not None:
            json['password'] = self.password
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            response=str(json['response']),
            username=str(json['username']) if 'username' in json else None,
            password=str(json['password']) if 'password' in json else None,
        )


class InterceptionStage(enum.Enum):
    '''
    Stages of the interception to begin intercepting. Request will intercept before the request is
    sent. Response will intercept after the response is received.
    '''
    REQUEST = "Request"
    HEADERS_RECEIVED = "HeadersReceived"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class RequestPattern:
    '''
    Request pattern for interception.
    '''
    #: Wildcards (``'*'`` -> zero or more, ``'?'`` -> exactly one) are allowed. Escape character is
    #: backslash. Omitting is equivalent to ``"*"``.
    url_pattern: typing.Optional[str] = None

    #: If set, only requests for matching resource types will be intercepted.
    resource_type: typing.Optional[ResourceType] = None

    #: Stage at which to begin intercepting requests. Default is Request.
    interception_stage: typing.Optional[InterceptionStage] = None

    def to_json(self):
        json = dict()
        if self.url_pattern is not None:
            json['urlPattern'] = self.url_pattern
        if self.resource_type is not None:
            json['resourceType'] = self.resource_type.to_json()
        if self.interception_stage is not None:
            json['interceptionStage'] = self.interception_stage.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url_pattern=str(json['urlPattern']) if 'urlPattern' in json else None,
            resource_type=ResourceType.from_json(json['resourceType']) if 'resourceType' in json else None,
            interception_stage=InterceptionStage.from_json(json['interceptionStage']) if 'interceptionStage' in json else None,
        )


@dataclass
class SignedExchangeSignature:
    '''
    Information about a signed exchange signature.
    https://wicg.github.io/webpackage/draft-yasskin-httpbis-origin-signed-exchanges-impl.html#rfc.section.3.1
    '''
    #: Signed exchange signature label.
    label: str

    #: The hex string of signed exchange signature.
    signature: str

    #: Signed exchange signature integrity.
    integrity: str

    #: Signed exchange signature validity Url.
    validity_url: str

    #: Signed exchange signature date.
    date: int

    #: Signed exchange signature expires.
    expires: int

    #: Signed exchange signature cert Url.
    cert_url: typing.Optional[str] = None

    #: The hex string of signed exchange signature cert sha256.
    cert_sha256: typing.Optional[str] = None

    #: The encoded certificates.
    certificates: typing.Optional[typing.List[str]] = None

    def to_json(self):
        json = dict()
        json['label'] = self.label
        json['signature'] = self.signature
        json['integrity'] = self.integrity
        json['validityUrl'] = self.validity_url
        json['date'] = self.date
        json['expires'] = self.expires
        if self.cert_url is not None:
            json['certUrl'] = self.cert_url
        if self.cert_sha256 is not None:
            json['certSha256'] = self.cert_sha256
        if self.certificates is not None:
            json['certificates'] = [i for i in self.certificates]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            label=str(json['label']),
            signature=str(json['signature']),
            integrity=str(json['integrity']),
            validity_url=str(json['validityUrl']),
            date=int(json['date']),
            expires=int(json['expires']),
            cert_url=str(json['certUrl']) if 'certUrl' in json else None,
            cert_sha256=str(json['certSha256']) if 'certSha256' in json else None,
            certificates=[str(i) for i in json['certificates']] if 'certificates' in json else None,
        )


@dataclass
class SignedExchangeHeader:
    '''
    Information about a signed exchange header.
    https://wicg.github.io/webpackage/draft-yasskin-httpbis-origin-signed-exchanges-impl.html#cbor-representation
    '''
    #: Signed exchange request URL.
    request_url: str

    #: Signed exchange response code.
    response_code: int

    #: Signed exchange response headers.
    response_headers: Headers

    #: Signed exchange response signature.
    signatures: typing.List[SignedExchangeSignature]

    #: Signed exchange header integrity hash in the form of ``sha256-<base64-hash-value>``.
    header_integrity: str

    def to_json(self):
        json = dict()
        json['requestUrl'] = self.request_url
        json['responseCode'] = self.response_code
        json['responseHeaders'] = self.response_headers.to_json()
        json['signatures'] = [i.to_json() for i in self.signatures]
        json['headerIntegrity'] = self.header_integrity
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            request_url=str(json['requestUrl']),
            response_code=int(json['responseCode']),
            response_headers=Headers.from_json(json['responseHeaders']),
            signatures=[SignedExchangeSignature.from_json(i) for i in json['signatures']],
            header_integrity=str(json['headerIntegrity']),
        )


class SignedExchangeErrorField(enum.Enum):
    '''
    Field type for a signed exchange related error.
    '''
    SIGNATURE_SIG = "signatureSig"
    SIGNATURE_INTEGRITY = "signatureIntegrity"
    SIGNATURE_CERT_URL = "signatureCertUrl"
    SIGNATURE_CERT_SHA256 = "signatureCertSha256"
    SIGNATURE_VALIDITY_URL = "signatureValidityUrl"
    SIGNATURE_TIMESTAMPS = "signatureTimestamps"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SignedExchangeError:
    '''
    Information about a signed exchange response.
    '''
    #: Error message.
    message: str

    #: The index of the signature which caused the error.
    signature_index: typing.Optional[int] = None

    #: The field which caused the error.
    error_field: typing.Optional[SignedExchangeErrorField] = None

    def to_json(self):
        json = dict()
        json['message'] = self.message
        if self.signature_index is not None:
            json['signatureIndex'] = self.signature_index
        if self.error_field is not None:
            json['errorField'] = self.error_field.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            message=str(json['message']),
            signature_index=int(json['signatureIndex']) if 'signatureIndex' in json else None,
            error_field=SignedExchangeErrorField.from_json(json['errorField']) if 'errorField' in json else None,
        )


@dataclass
class SignedExchangeInfo:
    '''
    Information about a signed exchange response.
    '''
    #: The outer response of signed HTTP exchange which was received from network.
    outer_response: Response

    #: Information about the signed exchange header.
    header: typing.Optional[SignedExchangeHeader] = None

    #: Security details for the signed exchange header.
    security_details: typing.Optional[SecurityDetails] = None

    #: Errors occurred while handling the signed exchange.
    errors: typing.Optional[typing.List[SignedExchangeError]] = None

    def to_json(self):
        json = dict()
        json['outerResponse'] = self.outer_response.to_json()
        if self.header is not None:
            json['header'] = self.header.to_json()
        if self.security_details is not None:
            json['securityDetails'] = self.security_details.to_json()
        if self.errors is not None:
            json['errors'] = [i.to_json() for i in self.errors]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            outer_response=Response.from_json(json['outerResponse']),
            header=SignedExchangeHeader.from_json(json['header']) if 'header' in json else None,
            security_details=SecurityDetails.from_json(json['securityDetails']) if 'securityDetails' in json else None,
            errors=[SignedExchangeError.from_json(i) for i in json['errors']] if 'errors' in json else None,
        )


class ContentEncoding(enum.Enum):
    '''
    List of content encodings supported by the backend.
    '''
    DEFLATE = "deflate"
    GZIP = "gzip"
    BR = "br"
    ZSTD = "zstd"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class DirectSocketDnsQueryType(enum.Enum):
    IPV4 = "ipv4"
    IPV6 = "ipv6"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class DirectTCPSocketOptions:
    #: TCP_NODELAY option
    no_delay: bool

    #: Expected to be unsigned integer.
    keep_alive_delay: typing.Optional[float] = None

    #: Expected to be unsigned integer.
    send_buffer_size: typing.Optional[float] = None

    #: Expected to be unsigned integer.
    receive_buffer_size: typing.Optional[float] = None

    dns_query_type: typing.Optional[DirectSocketDnsQueryType] = None

    def to_json(self):
        json = dict()
        json['noDelay'] = self.no_delay
        if self.keep_alive_delay is not None:
            json['keepAliveDelay'] = self.keep_alive_delay
        if self.send_buffer_size is not None:
            json['sendBufferSize'] = self.send_buffer_size
        if self.receive_buffer_size is not None:
            json['receiveBufferSize'] = self.receive_buffer_size
        if self.dns_query_type is not None:
            json['dnsQueryType'] = self.dns_query_type.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            no_delay=bool(json['noDelay']),
            keep_alive_delay=float(json['keepAliveDelay']) if 'keepAliveDelay' in json else None,
            send_buffer_size=float(json['sendBufferSize']) if 'sendBufferSize' in json else None,
            receive_buffer_size=float(json['receiveBufferSize']) if 'receiveBufferSize' in json else None,
            dns_query_type=DirectSocketDnsQueryType.from_json(json['dnsQueryType']) if 'dnsQueryType' in json else None,
        )


class PrivateNetworkRequestPolicy(enum.Enum):
    ALLOW = "Allow"
    BLOCK_FROM_INSECURE_TO_MORE_PRIVATE = "BlockFromInsecureToMorePrivate"
    WARN_FROM_INSECURE_TO_MORE_PRIVATE = "WarnFromInsecureToMorePrivate"
    PREFLIGHT_BLOCK = "PreflightBlock"
    PREFLIGHT_WARN = "PreflightWarn"
    PERMISSION_BLOCK = "PermissionBlock"
    PERMISSION_WARN = "PermissionWarn"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class IPAddressSpace(enum.Enum):
    LOCAL = "Local"
    PRIVATE = "Private"
    PUBLIC = "Public"
    UNKNOWN = "Unknown"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ConnectTiming:
    #: Timing's requestTime is a baseline in seconds, while the other numbers are ticks in
    #: milliseconds relatively to this requestTime. Matches ResourceTiming's requestTime for
    #: the same request (but not for redirected requests).
    request_time: float

    def to_json(self):
        json = dict()
        json['requestTime'] = self.request_time
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            request_time=float(json['requestTime']),
        )


@dataclass
class ClientSecurityState:
    initiator_is_secure_context: bool

    initiator_ip_address_space: IPAddressSpace

    private_network_request_policy: PrivateNetworkRequestPolicy

    def to_json(self):
        json = dict()
        json['initiatorIsSecureContext'] = self.initiator_is_secure_context
        json['initiatorIPAddressSpace'] = self.initiator_ip_address_space.to_json()
        json['privateNetworkRequestPolicy'] = self.private_network_request_policy.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            initiator_is_secure_context=bool(json['initiatorIsSecureContext']),
            initiator_ip_address_space=IPAddressSpace.from_json(json['initiatorIPAddressSpace']),
            private_network_request_policy=PrivateNetworkRequestPolicy.from_json(json['privateNetworkRequestPolicy']),
        )


class CrossOriginOpenerPolicyValue(enum.Enum):
    SAME_ORIGIN = "SameOrigin"
    SAME_ORIGIN_ALLOW_POPUPS = "SameOriginAllowPopups"
    RESTRICT_PROPERTIES = "RestrictProperties"
    UNSAFE_NONE = "UnsafeNone"
    SAME_ORIGIN_PLUS_COEP = "SameOriginPlusCoep"
    RESTRICT_PROPERTIES_PLUS_COEP = "RestrictPropertiesPlusCoep"
    NOOPENER_ALLOW_POPUPS = "NoopenerAllowPopups"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class CrossOriginOpenerPolicyStatus:
    value: CrossOriginOpenerPolicyValue

    report_only_value: CrossOriginOpenerPolicyValue

    reporting_endpoint: typing.Optional[str] = None

    report_only_reporting_endpoint: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['value'] = self.value.to_json()
        json['reportOnlyValue'] = self.report_only_value.to_json()
        if self.reporting_endpoint is not None:
            json['reportingEndpoint'] = self.reporting_endpoint
        if self.report_only_reporting_endpoint is not None:
            json['reportOnlyReportingEndpoint'] = self.report_only_reporting_endpoint
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=CrossOriginOpenerPolicyValue.from_json(json['value']),
            report_only_value=CrossOriginOpenerPolicyValue.from_json(json['reportOnlyValue']),
            reporting_endpoint=str(json['reportingEndpoint']) if 'reportingEndpoint' in json else None,
            report_only_reporting_endpoint=str(json['reportOnlyReportingEndpoint']) if 'reportOnlyReportingEndpoint' in json else None,
        )


class CrossOriginEmbedderPolicyValue(enum.Enum):
    NONE = "None"
    CREDENTIALLESS = "Credentialless"
    REQUIRE_CORP = "RequireCorp"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class CrossOriginEmbedderPolicyStatus:
    value: CrossOriginEmbedderPolicyValue

    report_only_value: CrossOriginEmbedderPolicyValue

    reporting_endpoint: typing.Optional[str] = None

    report_only_reporting_endpoint: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['value'] = self.value.to_json()
        json['reportOnlyValue'] = self.report_only_value.to_json()
        if self.reporting_endpoint is not None:
            json['reportingEndpoint'] = self.reporting_endpoint
        if self.report_only_reporting_endpoint is not None:
            json['reportOnlyReportingEndpoint'] = self.report_only_reporting_endpoint
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            value=CrossOriginEmbedderPolicyValue.from_json(json['value']),
            report_only_value=CrossOriginEmbedderPolicyValue.from_json(json['reportOnlyValue']),
            reporting_endpoint=str(json['reportingEndpoint']) if 'reportingEndpoint' in json else None,
            report_only_reporting_endpoint=str(json['reportOnlyReportingEndpoint']) if 'reportOnlyReportingEndpoint' in json else None,
        )


class ContentSecurityPolicySource(enum.Enum):
    HTTP = "HTTP"
    META = "Meta"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ContentSecurityPolicyStatus:
    effective_directives: str

    is_enforced: bool

    source: ContentSecurityPolicySource

    def to_json(self):
        json = dict()
        json['effectiveDirectives'] = self.effective_directives
        json['isEnforced'] = self.is_enforced
        json['source'] = self.source.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            effective_directives=str(json['effectiveDirectives']),
            is_enforced=bool(json['isEnforced']),
            source=ContentSecurityPolicySource.from_json(json['source']),
        )


@dataclass
class SecurityIsolationStatus:
    coop: typing.Optional[CrossOriginOpenerPolicyStatus] = None

    coep: typing.Optional[CrossOriginEmbedderPolicyStatus] = None

    csp: typing.Optional[typing.List[ContentSecurityPolicyStatus]] = None

    def to_json(self):
        json = dict()
        if self.coop is not None:
            json['coop'] = self.coop.to_json()
        if self.coep is not None:
            json['coep'] = self.coep.to_json()
        if self.csp is not None:
            json['csp'] = [i.to_json() for i in self.csp]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            coop=CrossOriginOpenerPolicyStatus.from_json(json['coop']) if 'coop' in json else None,
            coep=CrossOriginEmbedderPolicyStatus.from_json(json['coep']) if 'coep' in json else None,
            csp=[ContentSecurityPolicyStatus.from_json(i) for i in json['csp']] if 'csp' in json else None,
        )


class ReportStatus(enum.Enum):
    '''
    The status of a Reporting API report.
    '''
    QUEUED = "Queued"
    PENDING = "Pending"
    MARKED_FOR_REMOVAL = "MarkedForRemoval"
    SUCCESS = "Success"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class ReportId(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> ReportId:
        return cls(json)

    def __repr__(self):
        return 'ReportId({})'.format(super().__repr__())


@dataclass
class ReportingApiReport:
    '''
    An object representing a report generated by the Reporting API.
    '''
    id_: ReportId

    #: The URL of the document that triggered the report.
    initiator_url: str

    #: The name of the endpoint group that should be used to deliver the report.
    destination: str

    #: The type of the report (specifies the set of data that is contained in the report body).
    type_: str

    #: When the report was generated.
    timestamp: network.TimeSinceEpoch

    #: How many uploads deep the related request was.
    depth: int

    #: The number of delivery attempts made so far, not including an active attempt.
    completed_attempts: int

    body: dict

    status: ReportStatus

    def to_json(self):
        json = dict()
        json['id'] = self.id_.to_json()
        json['initiatorUrl'] = self.initiator_url
        json['destination'] = self.destination
        json['type'] = self.type_
        json['timestamp'] = self.timestamp.to_json()
        json['depth'] = self.depth
        json['completedAttempts'] = self.completed_attempts
        json['body'] = self.body
        json['status'] = self.status.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=ReportId.from_json(json['id']),
            initiator_url=str(json['initiatorUrl']),
            destination=str(json['destination']),
            type_=str(json['type']),
            timestamp=network.TimeSinceEpoch.from_json(json['timestamp']),
            depth=int(json['depth']),
            completed_attempts=int(json['completedAttempts']),
            body=dict(json['body']),
            status=ReportStatus.from_json(json['status']),
        )


@dataclass
class ReportingApiEndpoint:
    #: The URL of the endpoint to which reports may be delivered.
    url: str

    #: Name of the endpoint group.
    group_name: str

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['groupName'] = self.group_name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            group_name=str(json['groupName']),
        )


@dataclass
class LoadNetworkResourcePageResult:
    '''
    An object providing the result of a network resource load.
    '''
    success: bool

    #: Optional values used for error reporting.
    net_error: typing.Optional[float] = None

    net_error_name: typing.Optional[str] = None

    http_status_code: typing.Optional[float] = None

    #: If successful, one of the following two fields holds the result.
    stream: typing.Optional[io.StreamHandle] = None

    #: Response headers.
    headers: typing.Optional[network.Headers] = None

    def to_json(self):
        json = dict()
        json['success'] = self.success
        if self.net_error is not None:
            json['netError'] = self.net_error
        if self.net_error_name is not None:
            json['netErrorName'] = self.net_error_name
        if self.http_status_code is not None:
            json['httpStatusCode'] = self.http_status_code
        if self.stream is not None:
            json['stream'] = self.stream.to_json()
        if self.headers is not None:
            json['headers'] = self.headers.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            success=bool(json['success']),
            net_error=float(json['netError']) if 'netError' in json else None,
            net_error_name=str(json['netErrorName']) if 'netErrorName' in json else None,
            http_status_code=float(json['httpStatusCode']) if 'httpStatusCode' in json else None,
            stream=io.StreamHandle.from_json(json['stream']) if 'stream' in json else None,
            headers=network.Headers.from_json(json['headers']) if 'headers' in json else None,
        )


@dataclass
class LoadNetworkResourceOptions:
    '''
    An options object that may be extended later to better support CORS,
    CORB and streaming.
    '''
    disable_cache: bool

    include_credentials: bool

    def to_json(self):
        json = dict()
        json['disableCache'] = self.disable_cache
        json['includeCredentials'] = self.include_credentials
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            disable_cache=bool(json['disableCache']),
            include_credentials=bool(json['includeCredentials']),
        )


def set_accepted_encodings(
        encodings: typing.List[ContentEncoding]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets a list of content encodings that will be accepted. Empty list means no encoding is accepted.

    **EXPERIMENTAL**

    :param encodings: List of accepted content encodings.
    '''
    params: T_JSON_DICT = dict()
    params['encodings'] = [i.to_json() for i in encodings]
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setAcceptedEncodings',
        'params': params,
    }
    json = yield cmd_dict


def clear_accepted_encodings_override() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears accepted encodings set by setAcceptedEncodings

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.clearAcceptedEncodingsOverride',
    }
    json = yield cmd_dict


def can_clear_browser_cache() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Tells whether clearing browser cache is supported.

    :returns: True if browser cache can be cleared.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.canClearBrowserCache',
    }
    json = yield cmd_dict
    return bool(json['result'])


def can_clear_browser_cookies() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Tells whether clearing browser cookies is supported.

    :returns: True if browser cookies can be cleared.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.canClearBrowserCookies',
    }
    json = yield cmd_dict
    return bool(json['result'])


def can_emulate_network_conditions() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Tells whether emulation of network conditions is supported.

    :returns: True if emulation of network conditions is supported.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.canEmulateNetworkConditions',
    }
    json = yield cmd_dict
    return bool(json['result'])


def clear_browser_cache() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears browser cache.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.clearBrowserCache',
    }
    json = yield cmd_dict


def clear_browser_cookies() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears browser cookies.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.clearBrowserCookies',
    }
    json = yield cmd_dict


def continue_intercepted_request(
        interception_id: InterceptionId,
        error_reason: typing.Optional[ErrorReason] = None,
        raw_response: typing.Optional[str] = None,
        url: typing.Optional[str] = None,
        method: typing.Optional[str] = None,
        post_data: typing.Optional[str] = None,
        headers: typing.Optional[Headers] = None,
        auth_challenge_response: typing.Optional[AuthChallengeResponse] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Response to Network.requestIntercepted which either modifies the request to continue with any
    modifications, or blocks it, or completes it with the provided response bytes. If a network
    fetch occurs as a result which encounters a redirect an additional Network.requestIntercepted
    event will be sent with the same InterceptionId.
    Deprecated, use Fetch.continueRequest, Fetch.fulfillRequest and Fetch.failRequest instead.

    **EXPERIMENTAL**

    :param interception_id:
    :param error_reason: *(Optional)* If set this causes the request to fail with the given reason. Passing ```Aborted```` for requests marked with ````isNavigationRequest``` also cancels the navigation. Must not be set in response to an authChallenge.
    :param raw_response: *(Optional)* If set the requests completes using with the provided base64 encoded raw response, including HTTP status line and headers etc... Must not be set in response to an authChallenge.
    :param url: *(Optional)* If set the request url will be modified in a way that's not observable by page. Must not be set in response to an authChallenge.
    :param method: *(Optional)* If set this allows the request method to be overridden. Must not be set in response to an authChallenge.
    :param post_data: *(Optional)* If set this allows postData to be set. Must not be set in response to an authChallenge.
    :param headers: *(Optional)* If set this allows the request headers to be changed. Must not be set in response to an authChallenge.
    :param auth_challenge_response: *(Optional)* Response to a requestIntercepted with an authChallenge. Must not be set otherwise.
    '''
    params: T_JSON_DICT = dict()
    params['interceptionId'] = interception_id.to_json()
    if error_reason is not None:
        params['errorReason'] = error_reason.to_json()
    if raw_response is not None:
        params['rawResponse'] = raw_response
    if url is not None:
        params['url'] = url
    if method is not None:
        params['method'] = method
    if post_data is not None:
        params['postData'] = post_data
    if headers is not None:
        params['headers'] = headers.to_json()
    if auth_challenge_response is not None:
        params['authChallengeResponse'] = auth_challenge_response.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.continueInterceptedRequest',
        'params': params,
    }
    json = yield cmd_dict


def delete_cookies(
        name: str,
        url: typing.Optional[str] = None,
        domain: typing.Optional[str] = None,
        path: typing.Optional[str] = None,
        partition_key: typing.Optional[CookiePartitionKey] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes browser cookies with matching name and url or domain/path/partitionKey pair.

    :param name: Name of the cookies to remove.
    :param url: *(Optional)* If specified, deletes all the cookies with the given name where domain and path match provided URL.
    :param domain: *(Optional)* If specified, deletes only cookies with the exact domain.
    :param path: *(Optional)* If specified, deletes only cookies with the exact path.
    :param partition_key: **(EXPERIMENTAL)** *(Optional)* If specified, deletes only cookies with the the given name and partitionKey where all partition key attributes match the cookie partition key attribute.
    '''
    params: T_JSON_DICT = dict()
    params['name'] = name
    if url is not None:
        params['url'] = url
    if domain is not None:
        params['domain'] = domain
    if path is not None:
        params['path'] = path
    if partition_key is not None:
        params['partitionKey'] = partition_key.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.deleteCookies',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables network tracking, prevents network events from being sent to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.disable',
    }
    json = yield cmd_dict


def emulate_network_conditions(
        offline: bool,
        latency: float,
        download_throughput: float,
        upload_throughput: float,
        connection_type: typing.Optional[ConnectionType] = None,
        packet_loss: typing.Optional[float] = None,
        packet_queue_length: typing.Optional[int] = None,
        packet_reordering: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Activates emulation of network conditions.

    :param offline: True to emulate internet disconnection.
    :param latency: Minimum latency from request sent to response headers received (ms).
    :param download_throughput: Maximal aggregated download throughput (bytes/sec). -1 disables download throttling.
    :param upload_throughput: Maximal aggregated upload throughput (bytes/sec).  -1 disables upload throttling.
    :param connection_type: *(Optional)* Connection type if known.
    :param packet_loss: **(EXPERIMENTAL)** *(Optional)* WebRTC packet loss (percent, 0-100). 0 disables packet loss emulation, 100 drops all the packets.
    :param packet_queue_length: **(EXPERIMENTAL)** *(Optional)* WebRTC packet queue length (packet). 0 removes any queue length limitations.
    :param packet_reordering: **(EXPERIMENTAL)** *(Optional)* WebRTC packetReordering feature.
    '''
    params: T_JSON_DICT = dict()
    params['offline'] = offline
    params['latency'] = latency
    params['downloadThroughput'] = download_throughput
    params['uploadThroughput'] = upload_throughput
    if connection_type is not None:
        params['connectionType'] = connection_type.to_json()
    if packet_loss is not None:
        params['packetLoss'] = packet_loss
    if packet_queue_length is not None:
        params['packetQueueLength'] = packet_queue_length
    if packet_reordering is not None:
        params['packetReordering'] = packet_reordering
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.emulateNetworkConditions',
        'params': params,
    }
    json = yield cmd_dict


def enable(
        max_total_buffer_size: typing.Optional[int] = None,
        max_resource_buffer_size: typing.Optional[int] = None,
        max_post_data_size: typing.Optional[int] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables network tracking, network events will now be delivered to the client.

    :param max_total_buffer_size: **(EXPERIMENTAL)** *(Optional)* Buffer size in bytes to use when preserving network payloads (XHRs, etc).
    :param max_resource_buffer_size: **(EXPERIMENTAL)** *(Optional)* Per-resource buffer size in bytes to use when preserving network payloads (XHRs, etc).
    :param max_post_data_size: *(Optional)* Longest post body size (in bytes) that would be included in requestWillBeSent notification
    '''
    params: T_JSON_DICT = dict()
    if max_total_buffer_size is not None:
        params['maxTotalBufferSize'] = max_total_buffer_size
    if max_resource_buffer_size is not None:
        params['maxResourceBufferSize'] = max_resource_buffer_size
    if max_post_data_size is not None:
        params['maxPostDataSize'] = max_post_data_size
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.enable',
        'params': params,
    }
    json = yield cmd_dict


def get_all_cookies() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Cookie]]:
    '''
    Returns all browser cookies. Depending on the backend support, will return detailed cookie
    information in the ``cookies`` field.
    Deprecated. Use Storage.getCookies instead.

    :returns: Array of cookie objects.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getAllCookies',
    }
    json = yield cmd_dict
    return [Cookie.from_json(i) for i in json['cookies']]


def get_certificate(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Returns the DER-encoded certificate.

    **EXPERIMENTAL**

    :param origin: Origin to get certificate for.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getCertificate',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['tableNames']]


def get_cookies(
        urls: typing.Optional[typing.List[str]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Cookie]]:
    '''
    Returns all browser cookies for the current URL. Depending on the backend support, will return
    detailed cookie information in the ``cookies`` field.

    :param urls: *(Optional)* The list of URLs for which applicable cookies will be fetched. If not specified, it's assumed to be set to the list containing the URLs of the page and all of its subframes.
    :returns: Array of cookie objects.
    '''
    params: T_JSON_DICT = dict()
    if urls is not None:
        params['urls'] = [i for i in urls]
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getCookies',
        'params': params,
    }
    json = yield cmd_dict
    return [Cookie.from_json(i) for i in json['cookies']]


def get_response_body(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, bool]]:
    '''
    Returns content served for the given request.

    :param request_id: Identifier of the network request to get content for.
    :returns: A tuple with the following items:

        0. **body** - Response body.
        1. **base64Encoded** - True, if content was sent as base64.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getResponseBody',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['body']),
        bool(json['base64Encoded'])
    )


def get_request_post_data(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Returns post data sent with the request. Returns an error when no data was sent with the request.

    :param request_id: Identifier of the network request to get content for.
    :returns: Request body string, omitting files from multipart requests
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getRequestPostData',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['postData'])


def get_response_body_for_interception(
        interception_id: InterceptionId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, bool]]:
    '''
    Returns content served for the given currently intercepted request.

    **EXPERIMENTAL**

    :param interception_id: Identifier for the intercepted request to get body for.
    :returns: A tuple with the following items:

        0. **body** - Response body.
        1. **base64Encoded** - True, if content was sent as base64.
    '''
    params: T_JSON_DICT = dict()
    params['interceptionId'] = interception_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getResponseBodyForInterception',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['body']),
        bool(json['base64Encoded'])
    )


def take_response_body_for_interception_as_stream(
        interception_id: InterceptionId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,io.StreamHandle]:
    '''
    Returns a handle to the stream representing the response body. Note that after this command,
    the intercepted request can't be continued as is -- you either need to cancel it or to provide
    the response body. The stream only supports sequential read, IO.read will fail if the position
    is specified.

    **EXPERIMENTAL**

    :param interception_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['interceptionId'] = interception_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.takeResponseBodyForInterceptionAsStream',
        'params': params,
    }
    json = yield cmd_dict
    return io.StreamHandle.from_json(json['stream'])


def replay_xhr(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    This method sends a new XMLHttpRequest which is identical to the original one. The following
    parameters should be identical: method, url, async, request body, extra headers, withCredentials
    attribute, user, password.

    **EXPERIMENTAL**

    :param request_id: Identifier of XHR to replay.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.replayXHR',
        'params': params,
    }
    json = yield cmd_dict


def search_in_response_body(
        request_id: RequestId,
        query: str,
        case_sensitive: typing.Optional[bool] = None,
        is_regex: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[debugger.SearchMatch]]:
    '''
    Searches for given string in response content.

    **EXPERIMENTAL**

    :param request_id: Identifier of the network response to search.
    :param query: String to search for.
    :param case_sensitive: *(Optional)* If true, search is case sensitive.
    :param is_regex: *(Optional)* If true, treats string parameter as regex.
    :returns: List of search matches.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    params['query'] = query
    if case_sensitive is not None:
        params['caseSensitive'] = case_sensitive
    if is_regex is not None:
        params['isRegex'] = is_regex
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.searchInResponseBody',
        'params': params,
    }
    json = yield cmd_dict
    return [debugger.SearchMatch.from_json(i) for i in json['result']]


def set_blocked_ur_ls(
        urls: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Blocks URLs from loading.

    **EXPERIMENTAL**

    :param urls: URL patterns to block. Wildcards ('*') are allowed.
    '''
    params: T_JSON_DICT = dict()
    params['urls'] = [i for i in urls]
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setBlockedURLs',
        'params': params,
    }
    json = yield cmd_dict


def set_bypass_service_worker(
        bypass: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Toggles ignoring of service worker for each request.

    :param bypass: Bypass service worker and load from network.
    '''
    params: T_JSON_DICT = dict()
    params['bypass'] = bypass
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setBypassServiceWorker',
        'params': params,
    }
    json = yield cmd_dict


def set_cache_disabled(
        cache_disabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Toggles ignoring cache for each request. If ``true``, cache will not be used.

    :param cache_disabled: Cache disabled state.
    '''
    params: T_JSON_DICT = dict()
    params['cacheDisabled'] = cache_disabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setCacheDisabled',
        'params': params,
    }
    json = yield cmd_dict


def set_cookie(
        name: str,
        value: str,
        url: typing.Optional[str] = None,
        domain: typing.Optional[str] = None,
        path: typing.Optional[str] = None,
        secure: typing.Optional[bool] = None,
        http_only: typing.Optional[bool] = None,
        same_site: typing.Optional[CookieSameSite] = None,
        expires: typing.Optional[TimeSinceEpoch] = None,
        priority: typing.Optional[CookiePriority] = None,
        same_party: typing.Optional[bool] = None,
        source_scheme: typing.Optional[CookieSourceScheme] = None,
        source_port: typing.Optional[int] = None,
        partition_key: typing.Optional[CookiePartitionKey] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Sets a cookie with the given cookie data; may overwrite equivalent cookies if they exist.

    :param name: Cookie name.
    :param value: Cookie value.
    :param url: *(Optional)* The request-URI to associate with the setting of the cookie. This value can affect the default domain, path, source port, and source scheme values of the created cookie.
    :param domain: *(Optional)* Cookie domain.
    :param path: *(Optional)* Cookie path.
    :param secure: *(Optional)* True if cookie is secure.
    :param http_only: *(Optional)* True if cookie is http-only.
    :param same_site: *(Optional)* Cookie SameSite type.
    :param expires: *(Optional)* Cookie expiration date, session cookie if not set
    :param priority: **(EXPERIMENTAL)** *(Optional)* Cookie Priority type.
    :param same_party: **(EXPERIMENTAL)** *(Optional)* True if cookie is SameParty.
    :param source_scheme: **(EXPERIMENTAL)** *(Optional)* Cookie source scheme type.
    :param source_port: **(EXPERIMENTAL)** *(Optional)* Cookie source port. Valid values are {-1, [1, 65535]}, -1 indicates an unspecified port. An unspecified port value allows protocol clients to emulate legacy cookie scope for the port. This is a temporary ability and it will be removed in the future.
    :param partition_key: **(EXPERIMENTAL)** *(Optional)* Cookie partition key. If not set, the cookie will be set as not partitioned.
    :returns: Always set to true. If an error occurs, the response indicates protocol error.
    '''
    params: T_JSON_DICT = dict()
    params['name'] = name
    params['value'] = value
    if url is not None:
        params['url'] = url
    if domain is not None:
        params['domain'] = domain
    if path is not None:
        params['path'] = path
    if secure is not None:
        params['secure'] = secure
    if http_only is not None:
        params['httpOnly'] = http_only
    if same_site is not None:
        params['sameSite'] = same_site.to_json()
    if expires is not None:
        params['expires'] = expires.to_json()
    if priority is not None:
        params['priority'] = priority.to_json()
    if same_party is not None:
        params['sameParty'] = same_party
    if source_scheme is not None:
        params['sourceScheme'] = source_scheme.to_json()
    if source_port is not None:
        params['sourcePort'] = source_port
    if partition_key is not None:
        params['partitionKey'] = partition_key.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setCookie',
        'params': params,
    }
    json = yield cmd_dict
    return bool(json['success'])


def set_cookies(
        cookies: typing.List[CookieParam]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets given cookies.

    :param cookies: Cookies to be set.
    '''
    params: T_JSON_DICT = dict()
    params['cookies'] = [i.to_json() for i in cookies]
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setCookies',
        'params': params,
    }
    json = yield cmd_dict


def set_extra_http_headers(
        headers: Headers
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Specifies whether to always send extra HTTP headers with the requests from this page.

    :param headers: Map with extra HTTP headers.
    '''
    params: T_JSON_DICT = dict()
    params['headers'] = headers.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setExtraHTTPHeaders',
        'params': params,
    }
    json = yield cmd_dict


def set_attach_debug_stack(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Specifies whether to attach a page script stack id in requests

    **EXPERIMENTAL**

    :param enabled: Whether to attach a page script stack for debugging purpose.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setAttachDebugStack',
        'params': params,
    }
    json = yield cmd_dict


def set_request_interception(
        patterns: typing.List[RequestPattern]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets the requests to intercept that match the provided patterns and optionally resource types.
    Deprecated, please use Fetch.enable instead.

    **EXPERIMENTAL**

    :param patterns: Requests matching any of these patterns will be forwarded and wait for the corresponding continueInterceptedRequest call.
    '''
    params: T_JSON_DICT = dict()
    params['patterns'] = [i.to_json() for i in patterns]
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setRequestInterception',
        'params': params,
    }
    json = yield cmd_dict


def set_user_agent_override(
        user_agent: str,
        accept_language: typing.Optional[str] = None,
        platform: typing.Optional[str] = None,
        user_agent_metadata: typing.Optional[emulation.UserAgentMetadata] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Allows overriding user agent with the given string.

    :param user_agent: User agent to use.
    :param accept_language: *(Optional)* Browser language to emulate.
    :param platform: *(Optional)* The platform navigator.platform should return.
    :param user_agent_metadata: **(EXPERIMENTAL)** *(Optional)* To be sent in Sec-CH-UA-* headers and returned in navigator.userAgentData
    '''
    params: T_JSON_DICT = dict()
    params['userAgent'] = user_agent
    if accept_language is not None:
        params['acceptLanguage'] = accept_language
    if platform is not None:
        params['platform'] = platform
    if user_agent_metadata is not None:
        params['userAgentMetadata'] = user_agent_metadata.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setUserAgentOverride',
        'params': params,
    }
    json = yield cmd_dict


def stream_resource_content(
        request_id: RequestId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Enables streaming of the response for the given requestId.
    If enabled, the dataReceived event contains the data that was received during streaming.

    **EXPERIMENTAL**

    :param request_id: Identifier of the request to stream.
    :returns: Data that has been buffered until streaming is enabled.
    '''
    params: T_JSON_DICT = dict()
    params['requestId'] = request_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.streamResourceContent',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['bufferedData'])


def get_security_isolation_status(
        frame_id: typing.Optional[page.FrameId] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SecurityIsolationStatus]:
    '''
    Returns information about the COEP/COOP isolation status.

    **EXPERIMENTAL**

    :param frame_id: *(Optional)* If no frameId is provided, the status of the target is provided.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.getSecurityIsolationStatus',
        'params': params,
    }
    json = yield cmd_dict
    return SecurityIsolationStatus.from_json(json['status'])


def enable_reporting_api(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables tracking for the Reporting API, events generated by the Reporting API will now be delivered to the client.
    Enabling triggers 'reportingApiReportAdded' for all existing reports.

    **EXPERIMENTAL**

    :param enable: Whether to enable or disable events for the Reporting API
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.enableReportingApi',
        'params': params,
    }
    json = yield cmd_dict


def load_network_resource(
        frame_id: typing.Optional[page.FrameId] = None,
        url: str = None,
        options: LoadNetworkResourceOptions = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,LoadNetworkResourcePageResult]:
    '''
    Fetches the resource and returns the content.

    **EXPERIMENTAL**

    :param frame_id: *(Optional)* Frame id to get the resource for. Mandatory for frame targets, and should be omitted for worker targets.
    :param url: URL of the resource to get content for.
    :param options: Options for the request.
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    params['url'] = url
    params['options'] = options.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.loadNetworkResource',
        'params': params,
    }
    json = yield cmd_dict
    return LoadNetworkResourcePageResult.from_json(json['resource'])


def set_cookie_controls(
        enable_third_party_cookie_restriction: bool,
        disable_third_party_cookie_metadata: bool,
        disable_third_party_cookie_heuristics: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets Controls for third-party cookie access
    Page reload is required before the new cookie bahavior will be observed

    **EXPERIMENTAL**

    :param enable_third_party_cookie_restriction: Whether 3pc restriction is enabled.
    :param disable_third_party_cookie_metadata: Whether 3pc grace period exception should be enabled; false by default.
    :param disable_third_party_cookie_heuristics: Whether 3pc heuristics exceptions should be enabled; false by default.
    '''
    params: T_JSON_DICT = dict()
    params['enableThirdPartyCookieRestriction'] = enable_third_party_cookie_restriction
    params['disableThirdPartyCookieMetadata'] = disable_third_party_cookie_metadata
    params['disableThirdPartyCookieHeuristics'] = disable_third_party_cookie_heuristics
    cmd_dict: T_JSON_DICT = {
        'method': 'Network.setCookieControls',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Network.dataReceived')
@dataclass
class DataReceived:
    '''
    Fired when data chunk was received over the network.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: Data chunk length.
    data_length: int
    #: Actual bytes received (might be less than dataLength for compressed encodings).
    encoded_data_length: int
    #: Data that was received.
    data: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DataReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            data_length=int(json['dataLength']),
            encoded_data_length=int(json['encodedDataLength']),
            data=str(json['data']) if 'data' in json else None
        )


@event_class('Network.eventSourceMessageReceived')
@dataclass
class EventSourceMessageReceived:
    '''
    Fired when EventSource message is received.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: Message type.
    event_name: str
    #: Message identifier.
    event_id: str
    #: Message content.
    data: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> EventSourceMessageReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            event_name=str(json['eventName']),
            event_id=str(json['eventId']),
            data=str(json['data'])
        )


@event_class('Network.loadingFailed')
@dataclass
class LoadingFailed:
    '''
    Fired when HTTP request has failed to load.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: Resource type.
    type_: ResourceType
    #: Error message. List of network errors: https://cs.chromium.org/chromium/src/net/base/net_error_list.h
    error_text: str
    #: True if loading was canceled.
    canceled: typing.Optional[bool]
    #: The reason why loading was blocked, if any.
    blocked_reason: typing.Optional[BlockedReason]
    #: The reason why loading was blocked by CORS, if any.
    cors_error_status: typing.Optional[CorsErrorStatus]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LoadingFailed:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            type_=ResourceType.from_json(json['type']),
            error_text=str(json['errorText']),
            canceled=bool(json['canceled']) if 'canceled' in json else None,
            blocked_reason=BlockedReason.from_json(json['blockedReason']) if 'blockedReason' in json else None,
            cors_error_status=CorsErrorStatus.from_json(json['corsErrorStatus']) if 'corsErrorStatus' in json else None
        )


@event_class('Network.loadingFinished')
@dataclass
class LoadingFinished:
    '''
    Fired when HTTP request has finished loading.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: Total number of bytes received for this request.
    encoded_data_length: float

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> LoadingFinished:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            encoded_data_length=float(json['encodedDataLength'])
        )


@event_class('Network.requestIntercepted')
@dataclass
class RequestIntercepted:
    '''
    **EXPERIMENTAL**

    Details of an intercepted HTTP request, which must be either allowed, blocked, modified or
    mocked.
    Deprecated, use Fetch.requestPaused instead.
    '''
    #: Each request the page makes will have a unique id, however if any redirects are encountered
    #: while processing that fetch, they will be reported with the same id as the original fetch.
    #: Likewise if HTTP authentication is needed then the same fetch id will be used.
    interception_id: InterceptionId
    request: Request
    #: The id of the frame that initiated the request.
    frame_id: page.FrameId
    #: How the requested resource will be used.
    resource_type: ResourceType
    #: Whether this is a navigation request, which can abort the navigation completely.
    is_navigation_request: bool
    #: Set if the request is a navigation that will result in a download.
    #: Only present after response is received from the server (i.e. HeadersReceived stage).
    is_download: typing.Optional[bool]
    #: Redirect location, only sent if a redirect was intercepted.
    redirect_url: typing.Optional[str]
    #: Details of the Authorization Challenge encountered. If this is set then
    #: continueInterceptedRequest must contain an authChallengeResponse.
    auth_challenge: typing.Optional[AuthChallenge]
    #: Response error if intercepted at response stage or if redirect occurred while intercepting
    #: request.
    response_error_reason: typing.Optional[ErrorReason]
    #: Response code if intercepted at response stage or if redirect occurred while intercepting
    #: request or auth retry occurred.
    response_status_code: typing.Optional[int]
    #: Response headers if intercepted at the response stage or if redirect occurred while
    #: intercepting request or auth retry occurred.
    response_headers: typing.Optional[Headers]
    #: If the intercepted request had a corresponding requestWillBeSent event fired for it, then
    #: this requestId will be the same as the requestId present in the requestWillBeSent event.
    request_id: typing.Optional[RequestId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RequestIntercepted:
        return cls(
            interception_id=InterceptionId.from_json(json['interceptionId']),
            request=Request.from_json(json['request']),
            frame_id=page.FrameId.from_json(json['frameId']),
            resource_type=ResourceType.from_json(json['resourceType']),
            is_navigation_request=bool(json['isNavigationRequest']),
            is_download=bool(json['isDownload']) if 'isDownload' in json else None,
            redirect_url=str(json['redirectUrl']) if 'redirectUrl' in json else None,
            auth_challenge=AuthChallenge.from_json(json['authChallenge']) if 'authChallenge' in json else None,
            response_error_reason=ErrorReason.from_json(json['responseErrorReason']) if 'responseErrorReason' in json else None,
            response_status_code=int(json['responseStatusCode']) if 'responseStatusCode' in json else None,
            response_headers=Headers.from_json(json['responseHeaders']) if 'responseHeaders' in json else None,
            request_id=RequestId.from_json(json['requestId']) if 'requestId' in json else None
        )


@event_class('Network.requestServedFromCache')
@dataclass
class RequestServedFromCache:
    '''
    Fired if request ended up loading from cache.
    '''
    #: Request identifier.
    request_id: RequestId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RequestServedFromCache:
        return cls(
            request_id=RequestId.from_json(json['requestId'])
        )


@event_class('Network.requestWillBeSent')
@dataclass
class RequestWillBeSent:
    '''
    Fired when page is about to send HTTP request.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Loader identifier. Empty string if the request is fetched from worker.
    loader_id: LoaderId
    #: URL of the document this request is loaded for.
    document_url: str
    #: Request data.
    request: Request
    #: Timestamp.
    timestamp: MonotonicTime
    #: Timestamp.
    wall_time: TimeSinceEpoch
    #: Request initiator.
    initiator: Initiator
    #: In the case that redirectResponse is populated, this flag indicates whether
    #: requestWillBeSentExtraInfo and responseReceivedExtraInfo events will be or were emitted
    #: for the request which was just redirected.
    redirect_has_extra_info: bool
    #: Redirect response data.
    redirect_response: typing.Optional[Response]
    #: Type of this resource.
    type_: typing.Optional[ResourceType]
    #: Frame identifier.
    frame_id: typing.Optional[page.FrameId]
    #: Whether the request is initiated by a user gesture. Defaults to false.
    has_user_gesture: typing.Optional[bool]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RequestWillBeSent:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            loader_id=LoaderId.from_json(json['loaderId']),
            document_url=str(json['documentURL']),
            request=Request.from_json(json['request']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            wall_time=TimeSinceEpoch.from_json(json['wallTime']),
            initiator=Initiator.from_json(json['initiator']),
            redirect_has_extra_info=bool(json['redirectHasExtraInfo']),
            redirect_response=Response.from_json(json['redirectResponse']) if 'redirectResponse' in json else None,
            type_=ResourceType.from_json(json['type']) if 'type' in json else None,
            frame_id=page.FrameId.from_json(json['frameId']) if 'frameId' in json else None,
            has_user_gesture=bool(json['hasUserGesture']) if 'hasUserGesture' in json else None
        )


@event_class('Network.resourceChangedPriority')
@dataclass
class ResourceChangedPriority:
    '''
    **EXPERIMENTAL**

    Fired when resource loading priority is changed
    '''
    #: Request identifier.
    request_id: RequestId
    #: New priority
    new_priority: ResourcePriority
    #: Timestamp.
    timestamp: MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ResourceChangedPriority:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            new_priority=ResourcePriority.from_json(json['newPriority']),
            timestamp=MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Network.signedExchangeReceived')
@dataclass
class SignedExchangeReceived:
    '''
    **EXPERIMENTAL**

    Fired when a signed exchange was received over the network
    '''
    #: Request identifier.
    request_id: RequestId
    #: Information about the signed exchange response.
    info: SignedExchangeInfo

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SignedExchangeReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            info=SignedExchangeInfo.from_json(json['info'])
        )


@event_class('Network.responseReceived')
@dataclass
class ResponseReceived:
    '''
    Fired when HTTP response is available.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Loader identifier. Empty string if the request is fetched from worker.
    loader_id: LoaderId
    #: Timestamp.
    timestamp: MonotonicTime
    #: Resource type.
    type_: ResourceType
    #: Response data.
    response: Response
    #: Indicates whether requestWillBeSentExtraInfo and responseReceivedExtraInfo events will be
    #: or were emitted for this request.
    has_extra_info: bool
    #: Frame identifier.
    frame_id: typing.Optional[page.FrameId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ResponseReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            loader_id=LoaderId.from_json(json['loaderId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            type_=ResourceType.from_json(json['type']),
            response=Response.from_json(json['response']),
            has_extra_info=bool(json['hasExtraInfo']),
            frame_id=page.FrameId.from_json(json['frameId']) if 'frameId' in json else None
        )


@event_class('Network.webSocketClosed')
@dataclass
class WebSocketClosed:
    '''
    Fired when WebSocket is closed.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketClosed:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Network.webSocketCreated')
@dataclass
class WebSocketCreated:
    '''
    Fired upon WebSocket creation.
    '''
    #: Request identifier.
    request_id: RequestId
    #: WebSocket request URL.
    url: str
    #: Request initiator.
    initiator: typing.Optional[Initiator]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketCreated:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            url=str(json['url']),
            initiator=Initiator.from_json(json['initiator']) if 'initiator' in json else None
        )


@event_class('Network.webSocketFrameError')
@dataclass
class WebSocketFrameError:
    '''
    Fired when WebSocket message error occurs.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: WebSocket error message.
    error_message: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketFrameError:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            error_message=str(json['errorMessage'])
        )


@event_class('Network.webSocketFrameReceived')
@dataclass
class WebSocketFrameReceived:
    '''
    Fired when WebSocket message is received.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: WebSocket response data.
    response: WebSocketFrame

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketFrameReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            response=WebSocketFrame.from_json(json['response'])
        )


@event_class('Network.webSocketFrameSent')
@dataclass
class WebSocketFrameSent:
    '''
    Fired when WebSocket message is sent.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: WebSocket response data.
    response: WebSocketFrame

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketFrameSent:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            response=WebSocketFrame.from_json(json['response'])
        )


@event_class('Network.webSocketHandshakeResponseReceived')
@dataclass
class WebSocketHandshakeResponseReceived:
    '''
    Fired when WebSocket handshake response becomes available.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: WebSocket response data.
    response: WebSocketResponse

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketHandshakeResponseReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            response=WebSocketResponse.from_json(json['response'])
        )


@event_class('Network.webSocketWillSendHandshakeRequest')
@dataclass
class WebSocketWillSendHandshakeRequest:
    '''
    Fired when WebSocket is about to initiate handshake.
    '''
    #: Request identifier.
    request_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime
    #: UTC Timestamp.
    wall_time: TimeSinceEpoch
    #: WebSocket request data.
    request: WebSocketRequest

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebSocketWillSendHandshakeRequest:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            wall_time=TimeSinceEpoch.from_json(json['wallTime']),
            request=WebSocketRequest.from_json(json['request'])
        )


@event_class('Network.webTransportCreated')
@dataclass
class WebTransportCreated:
    '''
    Fired upon WebTransport creation.
    '''
    #: WebTransport identifier.
    transport_id: RequestId
    #: WebTransport request URL.
    url: str
    #: Timestamp.
    timestamp: MonotonicTime
    #: Request initiator.
    initiator: typing.Optional[Initiator]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebTransportCreated:
        return cls(
            transport_id=RequestId.from_json(json['transportId']),
            url=str(json['url']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            initiator=Initiator.from_json(json['initiator']) if 'initiator' in json else None
        )


@event_class('Network.webTransportConnectionEstablished')
@dataclass
class WebTransportConnectionEstablished:
    '''
    Fired when WebTransport handshake is finished.
    '''
    #: WebTransport identifier.
    transport_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebTransportConnectionEstablished:
        return cls(
            transport_id=RequestId.from_json(json['transportId']),
            timestamp=MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Network.webTransportClosed')
@dataclass
class WebTransportClosed:
    '''
    Fired when WebTransport is disposed.
    '''
    #: WebTransport identifier.
    transport_id: RequestId
    #: Timestamp.
    timestamp: MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> WebTransportClosed:
        return cls(
            transport_id=RequestId.from_json(json['transportId']),
            timestamp=MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Network.directTCPSocketCreated')
@dataclass
class DirectTCPSocketCreated:
    '''
    **EXPERIMENTAL**

    Fired upon direct_socket.TCPSocket creation.
    '''
    identifier: RequestId
    remote_addr: str
    #: Unsigned int 16.
    remote_port: int
    options: DirectTCPSocketOptions
    timestamp: MonotonicTime
    initiator: typing.Optional[Initiator]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DirectTCPSocketCreated:
        return cls(
            identifier=RequestId.from_json(json['identifier']),
            remote_addr=str(json['remoteAddr']),
            remote_port=int(json['remotePort']),
            options=DirectTCPSocketOptions.from_json(json['options']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            initiator=Initiator.from_json(json['initiator']) if 'initiator' in json else None
        )


@event_class('Network.directTCPSocketOpened')
@dataclass
class DirectTCPSocketOpened:
    '''
    **EXPERIMENTAL**

    Fired when direct_socket.TCPSocket connection is opened.
    '''
    identifier: RequestId
    remote_addr: str
    #: Expected to be unsigned integer.
    remote_port: int
    timestamp: MonotonicTime
    local_addr: typing.Optional[str]
    #: Expected to be unsigned integer.
    local_port: typing.Optional[int]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DirectTCPSocketOpened:
        return cls(
            identifier=RequestId.from_json(json['identifier']),
            remote_addr=str(json['remoteAddr']),
            remote_port=int(json['remotePort']),
            timestamp=MonotonicTime.from_json(json['timestamp']),
            local_addr=str(json['localAddr']) if 'localAddr' in json else None,
            local_port=int(json['localPort']) if 'localPort' in json else None
        )


@event_class('Network.directTCPSocketAborted')
@dataclass
class DirectTCPSocketAborted:
    '''
    **EXPERIMENTAL**

    Fired when direct_socket.TCPSocket is aborted.
    '''
    identifier: RequestId
    error_message: str
    timestamp: MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DirectTCPSocketAborted:
        return cls(
            identifier=RequestId.from_json(json['identifier']),
            error_message=str(json['errorMessage']),
            timestamp=MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Network.directTCPSocketClosed')
@dataclass
class DirectTCPSocketClosed:
    '''
    **EXPERIMENTAL**

    Fired when direct_socket.TCPSocket is closed.
    '''
    identifier: RequestId
    timestamp: MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DirectTCPSocketClosed:
        return cls(
            identifier=RequestId.from_json(json['identifier']),
            timestamp=MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Network.directTCPSocketChunkSent')
@dataclass
class DirectTCPSocketChunkSent:
    '''
    **EXPERIMENTAL**

    Fired when data is sent to tcp direct socket stream.
    '''
    identifier: RequestId
    data: str
    timestamp: MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DirectTCPSocketChunkSent:
        return cls(
            identifier=RequestId.from_json(json['identifier']),
            data=str(json['data']),
            timestamp=MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Network.directTCPSocketChunkReceived')
@dataclass
class DirectTCPSocketChunkReceived:
    '''
    **EXPERIMENTAL**

    Fired when data is received from tcp direct socket stream.
    '''
    identifier: RequestId
    data: str
    timestamp: MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DirectTCPSocketChunkReceived:
        return cls(
            identifier=RequestId.from_json(json['identifier']),
            data=str(json['data']),
            timestamp=MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Network.directTCPSocketChunkError')
@dataclass
class DirectTCPSocketChunkError:
    '''
    **EXPERIMENTAL**

    Fired when there is an error
    when writing to tcp direct socket stream.
    For example, if user writes illegal type like string
    instead of ArrayBuffer or ArrayBufferView.
    There's no reporting for reading, because
    we cannot know errors on the other side.
    '''
    identifier: RequestId
    error_message: str
    timestamp: MonotonicTime

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DirectTCPSocketChunkError:
        return cls(
            identifier=RequestId.from_json(json['identifier']),
            error_message=str(json['errorMessage']),
            timestamp=MonotonicTime.from_json(json['timestamp'])
        )


@event_class('Network.requestWillBeSentExtraInfo')
@dataclass
class RequestWillBeSentExtraInfo:
    '''
    **EXPERIMENTAL**

    Fired when additional information about a requestWillBeSent event is available from the
    network stack. Not every requestWillBeSent event will have an additional
    requestWillBeSentExtraInfo fired for it, and there is no guarantee whether requestWillBeSent
    or requestWillBeSentExtraInfo will be fired first for the same request.
    '''
    #: Request identifier. Used to match this information to an existing requestWillBeSent event.
    request_id: RequestId
    #: A list of cookies potentially associated to the requested URL. This includes both cookies sent with
    #: the request and the ones not sent; the latter are distinguished by having blockedReasons field set.
    associated_cookies: typing.List[AssociatedCookie]
    #: Raw request headers as they will be sent over the wire.
    headers: Headers
    #: Connection timing information for the request.
    connect_timing: ConnectTiming
    #: The client security state set for the request.
    client_security_state: typing.Optional[ClientSecurityState]
    #: Whether the site has partitioned cookies stored in a partition different than the current one.
    site_has_cookie_in_other_partition: typing.Optional[bool]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RequestWillBeSentExtraInfo:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            associated_cookies=[AssociatedCookie.from_json(i) for i in json['associatedCookies']],
            headers=Headers.from_json(json['headers']),
            connect_timing=ConnectTiming.from_json(json['connectTiming']),
            client_security_state=ClientSecurityState.from_json(json['clientSecurityState']) if 'clientSecurityState' in json else None,
            site_has_cookie_in_other_partition=bool(json['siteHasCookieInOtherPartition']) if 'siteHasCookieInOtherPartition' in json else None
        )


@event_class('Network.responseReceivedExtraInfo')
@dataclass
class ResponseReceivedExtraInfo:
    '''
    **EXPERIMENTAL**

    Fired when additional information about a responseReceived event is available from the network
    stack. Not every responseReceived event will have an additional responseReceivedExtraInfo for
    it, and responseReceivedExtraInfo may be fired before or after responseReceived.
    '''
    #: Request identifier. Used to match this information to another responseReceived event.
    request_id: RequestId
    #: A list of cookies which were not stored from the response along with the corresponding
    #: reasons for blocking. The cookies here may not be valid due to syntax errors, which
    #: are represented by the invalid cookie line string instead of a proper cookie.
    blocked_cookies: typing.List[BlockedSetCookieWithReason]
    #: Raw response headers as they were received over the wire.
    #: Duplicate headers in the response are represented as a single key with their values
    #: concatentated using ``\n`` as the separator.
    #: See also ``headersText`` that contains verbatim text for HTTP/1.*.
    headers: Headers
    #: The IP address space of the resource. The address space can only be determined once the transport
    #: established the connection, so we can't send it in ``requestWillBeSentExtraInfo``.
    resource_ip_address_space: IPAddressSpace
    #: The status code of the response. This is useful in cases the request failed and no responseReceived
    #: event is triggered, which is the case for, e.g., CORS errors. This is also the correct status code
    #: for cached requests, where the status in responseReceived is a 200 and this will be 304.
    status_code: int
    #: Raw response header text as it was received over the wire. The raw text may not always be
    #: available, such as in the case of HTTP/2 or QUIC.
    headers_text: typing.Optional[str]
    #: The cookie partition key that will be used to store partitioned cookies set in this response.
    #: Only sent when partitioned cookies are enabled.
    cookie_partition_key: typing.Optional[CookiePartitionKey]
    #: True if partitioned cookies are enabled, but the partition key is not serializable to string.
    cookie_partition_key_opaque: typing.Optional[bool]
    #: A list of cookies which should have been blocked by 3PCD but are exempted and stored from
    #: the response with the corresponding reason.
    exempted_cookies: typing.Optional[typing.List[ExemptedSetCookieWithReason]]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ResponseReceivedExtraInfo:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            blocked_cookies=[BlockedSetCookieWithReason.from_json(i) for i in json['blockedCookies']],
            headers=Headers.from_json(json['headers']),
            resource_ip_address_space=IPAddressSpace.from_json(json['resourceIPAddressSpace']),
            status_code=int(json['statusCode']),
            headers_text=str(json['headersText']) if 'headersText' in json else None,
            cookie_partition_key=CookiePartitionKey.from_json(json['cookiePartitionKey']) if 'cookiePartitionKey' in json else None,
            cookie_partition_key_opaque=bool(json['cookiePartitionKeyOpaque']) if 'cookiePartitionKeyOpaque' in json else None,
            exempted_cookies=[ExemptedSetCookieWithReason.from_json(i) for i in json['exemptedCookies']] if 'exemptedCookies' in json else None
        )


@event_class('Network.responseReceivedEarlyHints')
@dataclass
class ResponseReceivedEarlyHints:
    '''
    **EXPERIMENTAL**

    Fired when 103 Early Hints headers is received in addition to the common response.
    Not every responseReceived event will have an responseReceivedEarlyHints fired.
    Only one responseReceivedEarlyHints may be fired for eached responseReceived event.
    '''
    #: Request identifier. Used to match this information to another responseReceived event.
    request_id: RequestId
    #: Raw response headers as they were received over the wire.
    #: Duplicate headers in the response are represented as a single key with their values
    #: concatentated using ``\n`` as the separator.
    #: See also ``headersText`` that contains verbatim text for HTTP/1.*.
    headers: Headers

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ResponseReceivedEarlyHints:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            headers=Headers.from_json(json['headers'])
        )


@event_class('Network.trustTokenOperationDone')
@dataclass
class TrustTokenOperationDone:
    '''
    **EXPERIMENTAL**

    Fired exactly once for each Trust Token operation. Depending on
    the type of the operation and whether the operation succeeded or
    failed, the event is fired before the corresponding request was sent
    or after the response was received.
    '''
    #: Detailed success or error status of the operation.
    #: 'AlreadyExists' also signifies a successful operation, as the result
    #: of the operation already exists und thus, the operation was abort
    #: preemptively (e.g. a cache hit).
    status: str
    type_: TrustTokenOperationType
    request_id: RequestId
    #: Top level origin. The context in which the operation was attempted.
    top_level_origin: typing.Optional[str]
    #: Origin of the issuer in case of a "Issuance" or "Redemption" operation.
    issuer_origin: typing.Optional[str]
    #: The number of obtained Trust Tokens on a successful "Issuance" operation.
    issued_token_count: typing.Optional[int]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TrustTokenOperationDone:
        return cls(
            status=str(json['status']),
            type_=TrustTokenOperationType.from_json(json['type']),
            request_id=RequestId.from_json(json['requestId']),
            top_level_origin=str(json['topLevelOrigin']) if 'topLevelOrigin' in json else None,
            issuer_origin=str(json['issuerOrigin']) if 'issuerOrigin' in json else None,
            issued_token_count=int(json['issuedTokenCount']) if 'issuedTokenCount' in json else None
        )


@event_class('Network.policyUpdated')
@dataclass
class PolicyUpdated:
    '''
    **EXPERIMENTAL**

    Fired once security policy has been updated.
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PolicyUpdated:
        return cls(

        )


@event_class('Network.subresourceWebBundleMetadataReceived')
@dataclass
class SubresourceWebBundleMetadataReceived:
    '''
    **EXPERIMENTAL**

    Fired once when parsing the .wbn file has succeeded.
    The event contains the information about the web bundle contents.
    '''
    #: Request identifier. Used to match this information to another event.
    request_id: RequestId
    #: A list of URLs of resources in the subresource Web Bundle.
    urls: typing.List[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SubresourceWebBundleMetadataReceived:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            urls=[str(i) for i in json['urls']]
        )


@event_class('Network.subresourceWebBundleMetadataError')
@dataclass
class SubresourceWebBundleMetadataError:
    '''
    **EXPERIMENTAL**

    Fired once when parsing the .wbn file has failed.
    '''
    #: Request identifier. Used to match this information to another event.
    request_id: RequestId
    #: Error message
    error_message: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SubresourceWebBundleMetadataError:
        return cls(
            request_id=RequestId.from_json(json['requestId']),
            error_message=str(json['errorMessage'])
        )


@event_class('Network.subresourceWebBundleInnerResponseParsed')
@dataclass
class SubresourceWebBundleInnerResponseParsed:
    '''
    **EXPERIMENTAL**

    Fired when handling requests for resources within a .wbn file.
    Note: this will only be fired for resources that are requested by the webpage.
    '''
    #: Request identifier of the subresource request
    inner_request_id: RequestId
    #: URL of the subresource resource.
    inner_request_url: str
    #: Bundle request identifier. Used to match this information to another event.
    #: This made be absent in case when the instrumentation was enabled only
    #: after webbundle was parsed.
    bundle_request_id: typing.Optional[RequestId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SubresourceWebBundleInnerResponseParsed:
        return cls(
            inner_request_id=RequestId.from_json(json['innerRequestId']),
            inner_request_url=str(json['innerRequestURL']),
            bundle_request_id=RequestId.from_json(json['bundleRequestId']) if 'bundleRequestId' in json else None
        )


@event_class('Network.subresourceWebBundleInnerResponseError')
@dataclass
class SubresourceWebBundleInnerResponseError:
    '''
    **EXPERIMENTAL**

    Fired when request for resources within a .wbn file failed.
    '''
    #: Request identifier of the subresource request
    inner_request_id: RequestId
    #: URL of the subresource resource.
    inner_request_url: str
    #: Error message
    error_message: str
    #: Bundle request identifier. Used to match this information to another event.
    #: This made be absent in case when the instrumentation was enabled only
    #: after webbundle was parsed.
    bundle_request_id: typing.Optional[RequestId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SubresourceWebBundleInnerResponseError:
        return cls(
            inner_request_id=RequestId.from_json(json['innerRequestId']),
            inner_request_url=str(json['innerRequestURL']),
            error_message=str(json['errorMessage']),
            bundle_request_id=RequestId.from_json(json['bundleRequestId']) if 'bundleRequestId' in json else None
        )


@event_class('Network.reportingApiReportAdded')
@dataclass
class ReportingApiReportAdded:
    '''
    **EXPERIMENTAL**

    Is sent whenever a new report is added.
    And after 'enableReportingApi' for all existing reports.
    '''
    report: ReportingApiReport

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ReportingApiReportAdded:
        return cls(
            report=ReportingApiReport.from_json(json['report'])
        )


@event_class('Network.reportingApiReportUpdated')
@dataclass
class ReportingApiReportUpdated:
    '''
    **EXPERIMENTAL**


    '''
    report: ReportingApiReport

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ReportingApiReportUpdated:
        return cls(
            report=ReportingApiReport.from_json(json['report'])
        )


@event_class('Network.reportingApiEndpointsChangedForOrigin')
@dataclass
class ReportingApiEndpointsChangedForOrigin:
    '''
    **EXPERIMENTAL**


    '''
    #: Origin of the document(s) which configured the endpoints.
    origin: str
    endpoints: typing.List[ReportingApiEndpoint]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ReportingApiEndpointsChangedForOrigin:
        return cls(
            origin=str(json['origin']),
            endpoints=[ReportingApiEndpoint.from_json(i) for i in json['endpoints']]
        )