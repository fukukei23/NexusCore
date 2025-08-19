
# === NexusCore/tools\exports\export_20250803_114325\combined_134.py ===

# === NexusCore/openenv\Lib\site-packages\anthropic\_models.py ===
from __future__ import annotations

import os
import inspect
from typing import TYPE_CHECKING, Any, Type, Union, Generic, TypeVar, Callable, cast
from datetime import date, datetime
from typing_extensions import (
    Unpack,
    Literal,
    ClassVar,
    Protocol,
    Required,
    ParamSpec,
    TypedDict,
    TypeGuard,
    final,
    override,
    runtime_checkable,
)

import pydantic
import pydantic.generics
from pydantic.fields import FieldInfo

from ._types import (
    Body,
    IncEx,
    Query,
    ModelT,
    Headers,
    Timeout,
    NotGiven,
    AnyMapping,
    HttpxRequestFiles,
)
from ._utils import (
    PropertyInfo,
    is_list,
    is_given,
    lru_cache,
    is_mapping,
    parse_date,
    coerce_boolean,
    parse_datetime,
    strip_not_given,
    extract_type_arg,
    is_annotated_type,
    strip_annotated_type,
)
from ._compat import (
    PYDANTIC_V2,
    ConfigDict,
    GenericModel as BaseGenericModel,
    get_args,
    is_union,
    parse_obj,
    get_origin,
    is_literal_type,
    get_model_config,
    get_model_fields,
    field_get_default,
)
from ._constants import RAW_RESPONSE_HEADER

if TYPE_CHECKING:
    from pydantic_core.core_schema import ModelField, LiteralSchema, ModelFieldsSchema

__all__ = ["BaseModel", "GenericModel"]

_T = TypeVar("_T")
_BaseModelT = TypeVar("_BaseModelT", bound="BaseModel")

P = ParamSpec("P")


@runtime_checkable
class _ConfigProtocol(Protocol):
    allow_population_by_field_name: bool


class BaseModel(pydantic.BaseModel):
    if PYDANTIC_V2:
        model_config: ClassVar[ConfigDict] = ConfigDict(
            extra="allow", defer_build=coerce_boolean(os.environ.get("DEFER_PYDANTIC_BUILD", "true"))
        )
    else:

        @property
        @override
        def model_fields_set(self) -> set[str]:
            # a forwards-compat shim for pydantic v2
            return self.__fields_set__  # type: ignore

        class Config(pydantic.BaseConfig):  # pyright: ignore[reportDeprecated]
            extra: Any = pydantic.Extra.allow  # type: ignore

    def to_dict(
        self,
        *,
        mode: Literal["json", "python"] = "python",
        use_api_names: bool = True,
        exclude_unset: bool = True,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        warnings: bool = True,
    ) -> dict[str, object]:
        """Recursively generate a dictionary representation of the model, optionally specifying which fields to include or exclude.

        By default, fields that were not set by the API will not be included,
        and keys will match the API response, *not* the property names from the model.

        For example, if the API responds with `"fooBar": true` but we've defined a `foo_bar: bool` property,
        the output will use the `"fooBar"` key (unless `use_api_names=False` is passed).

        Args:
            mode:
                If mode is 'json', the dictionary will only contain JSON serializable types. e.g. `datetime` will be turned into a string, `"2024-3-22T18:11:19.117000Z"`.
                If mode is 'python', the dictionary may contain any Python objects. e.g. `datetime(2024, 3, 22)`

            use_api_names: Whether to use the key that the API responded with or the property name. Defaults to `True`.
            exclude_unset: Whether to exclude fields that have not been explicitly set.
            exclude_defaults: Whether to exclude fields that are set to their default value from the output.
            exclude_none: Whether to exclude fields that have a value of `None` from the output.
            warnings: Whether to log warnings when invalid fields are encountered. This is only supported in Pydantic v2.
        """
        return self.model_dump(
            mode=mode,
            by_alias=use_api_names,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            warnings=warnings,
        )

    def to_json(
        self,
        *,
        indent: int | None = 2,
        use_api_names: bool = True,
        exclude_unset: bool = True,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        warnings: bool = True,
    ) -> str:
        """Generates a JSON string representing this model as it would be received from or sent to the API (but with indentation).

        By default, fields that were not set by the API will not be included,
        and keys will match the API response, *not* the property names from the model.

        For example, if the API responds with `"fooBar": true` but we've defined a `foo_bar: bool` property,
        the output will use the `"fooBar"` key (unless `use_api_names=False` is passed).

        Args:
            indent: Indentation to use in the JSON output. If `None` is passed, the output will be compact. Defaults to `2`
            use_api_names: Whether to use the key that the API responded with or the property name. Defaults to `True`.
            exclude_unset: Whether to exclude fields that have not been explicitly set.
            exclude_defaults: Whether to exclude fields that have the default value.
            exclude_none: Whether to exclude fields that have a value of `None`.
            warnings: Whether to show any warnings that occurred during serialization. This is only supported in Pydantic v2.
        """
        return self.model_dump_json(
            indent=indent,
            by_alias=use_api_names,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            warnings=warnings,
        )

    @override
    def __str__(self) -> str:
        # mypy complains about an invalid self arg
        return f'{self.__repr_name__()}({self.__repr_str__(", ")})'  # type: ignore[misc]

    # Override the 'construct' method in a way that supports recursive parsing without validation.
    # Based on https://github.com/samuelcolvin/pydantic/issues/1168#issuecomment-817742836.
    @classmethod
    @override
    def construct(
        cls: Type[ModelT],
        _fields_set: set[str] | None = None,
        **values: object,
    ) -> ModelT:
        m = cls.__new__(cls)
        fields_values: dict[str, object] = {}

        config = get_model_config(cls)
        populate_by_name = (
            config.allow_population_by_field_name
            if isinstance(config, _ConfigProtocol)
            else config.get("populate_by_name")
        )

        if _fields_set is None:
            _fields_set = set()

        model_fields = get_model_fields(cls)
        for name, field in model_fields.items():
            key = field.alias
            if key is None or (key not in values and populate_by_name):
                key = name

            if key in values:
                fields_values[name] = _construct_field(value=values[key], field=field, key=key)
                _fields_set.add(name)
            else:
                fields_values[name] = field_get_default(field)

        _extra = {}
        for key, value in values.items():
            if key not in model_fields:
                if PYDANTIC_V2:
                    _extra[key] = value
                else:
                    _fields_set.add(key)
                    fields_values[key] = value

        object.__setattr__(m, "__dict__", fields_values)

        if PYDANTIC_V2:
            # these properties are copied from Pydantic's `model_construct()` method
            object.__setattr__(m, "__pydantic_private__", None)
            object.__setattr__(m, "__pydantic_extra__", _extra)
            object.__setattr__(m, "__pydantic_fields_set__", _fields_set)
        else:
            # init_private_attributes() does not exist in v2
            m._init_private_attributes()  # type: ignore

            # copied from Pydantic v1's `construct()` method
            object.__setattr__(m, "__fields_set__", _fields_set)

        return m

    if not TYPE_CHECKING:
        # type checkers incorrectly complain about this assignment
        # because the type signatures are technically different
        # although not in practice
        model_construct = construct

    if not PYDANTIC_V2:
        # we define aliases for some of the new pydantic v2 methods so
        # that we can just document these methods without having to specify
        # a specific pydantic version as some users may not know which
        # pydantic version they are currently using

        @override
        def model_dump(
            self,
            *,
            mode: Literal["json", "python"] | str = "python",
            include: IncEx = None,
            exclude: IncEx = None,
            by_alias: bool = False,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            round_trip: bool = False,
            warnings: bool | Literal["none", "warn", "error"] = True,
            context: dict[str, Any] | None = None,
            serialize_as_any: bool = False,
        ) -> dict[str, Any]:
            """Usage docs: https://docs.pydantic.dev/2.4/concepts/serialization/#modelmodel_dump

            Generate a dictionary representation of the model, optionally specifying which fields to include or exclude.

            Args:
                mode: The mode in which `to_python` should run.
                    If mode is 'json', the dictionary will only contain JSON serializable types.
                    If mode is 'python', the dictionary may contain any Python objects.
                include: A list of fields to include in the output.
                exclude: A list of fields to exclude from the output.
                by_alias: Whether to use the field's alias in the dictionary key if defined.
                exclude_unset: Whether to exclude fields that are unset or None from the output.
                exclude_defaults: Whether to exclude fields that are set to their default value from the output.
                exclude_none: Whether to exclude fields that have a value of `None` from the output.
                round_trip: Whether to enable serialization and deserialization round-trip support.
                warnings: Whether to log warnings when invalid fields are encountered.

            Returns:
                A dictionary representation of the model.
            """
            if mode != "python":
                raise ValueError("mode is only supported in Pydantic v2")
            if round_trip != False:
                raise ValueError("round_trip is only supported in Pydantic v2")
            if warnings != True:
                raise ValueError("warnings is only supported in Pydantic v2")
            if context is not None:
                raise ValueError("context is only supported in Pydantic v2")
            if serialize_as_any != False:
                raise ValueError("serialize_as_any is only supported in Pydantic v2")
            return super().dict(  # pyright: ignore[reportDeprecated]
                include=include,
                exclude=exclude,
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )

        @override
        def model_dump_json(
            self,
            *,
            indent: int | None = None,
            include: IncEx = None,
            exclude: IncEx = None,
            by_alias: bool = False,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            round_trip: bool = False,
            warnings: bool | Literal["none", "warn", "error"] = True,
            context: dict[str, Any] | None = None,
            serialize_as_any: bool = False,
        ) -> str:
            """Usage docs: https://docs.pydantic.dev/2.4/concepts/serialization/#modelmodel_dump_json

            Generates a JSON representation of the model using Pydantic's `to_json` method.

            Args:
                indent: Indentation to use in the JSON output. If None is passed, the output will be compact.
                include: Field(s) to include in the JSON output. Can take either a string or set of strings.
                exclude: Field(s) to exclude from the JSON output. Can take either a string or set of strings.
                by_alias: Whether to serialize using field aliases.
                exclude_unset: Whether to exclude fields that have not been explicitly set.
                exclude_defaults: Whether to exclude fields that have the default value.
                exclude_none: Whether to exclude fields that have a value of `None`.
                round_trip: Whether to use serialization/deserialization between JSON and class instance.
                warnings: Whether to show any warnings that occurred during serialization.

            Returns:
                A JSON string representation of the model.
            """
            if round_trip != False:
                raise ValueError("round_trip is only supported in Pydantic v2")
            if warnings != True:
                raise ValueError("warnings is only supported in Pydantic v2")
            if context is not None:
                raise ValueError("context is only supported in Pydantic v2")
            if serialize_as_any != False:
                raise ValueError("serialize_as_any is only supported in Pydantic v2")
            return super().json(  # type: ignore[reportDeprecated]
                indent=indent,
                include=include,
                exclude=exclude,
                by_alias=by_alias,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )


def _construct_field(value: object, field: FieldInfo, key: str) -> object:
    if value is None:
        return field_get_default(field)

    if PYDANTIC_V2:
        type_ = field.annotation
    else:
        type_ = cast(type, field.outer_type_)  # type: ignore

    if type_ is None:
        raise RuntimeError(f"Unexpected field type is None for {key}")

    return construct_type(value=value, type_=type_)


def is_basemodel(type_: type) -> bool:
    """Returns whether or not the given type is either a `BaseModel` or a union of `BaseModel`"""
    if is_union(type_):
        for variant in get_args(type_):
            if is_basemodel(variant):
                return True

        return False

    return is_basemodel_type(type_)


def is_basemodel_type(type_: type) -> TypeGuard[type[BaseModel] | type[GenericModel]]:
    origin = get_origin(type_) or type_
    if not inspect.isclass(origin):
        return False
    return issubclass(origin, BaseModel) or issubclass(origin, GenericModel)


def build(
    base_model_cls: Callable[P, _BaseModelT],
    *args: P.args,
    **kwargs: P.kwargs,
) -> _BaseModelT:
    """Construct a BaseModel class without validation.

    This is useful for cases where you need to instantiate a `BaseModel`
    from an API response as this provides type-safe params which isn't supported
    by helpers like `construct_type()`.

    ```py
    build(MyModel, my_field_a="foo", my_field_b=123)
    ```
    """
    if args:
        raise TypeError(
            "Received positional arguments which are not supported; Keyword arguments must be used instead",
        )

    return cast(_BaseModelT, construct_type(type_=base_model_cls, value=kwargs))


def construct_type_unchecked(*, value: object, type_: type[_T]) -> _T:
    """Loose coercion to the expected type with construction of nested values.

    Note: the returned value from this function is not guaranteed to match the
    given type.
    """
    return cast(_T, construct_type(value=value, type_=type_))


def construct_type(*, value: object, type_: object) -> object:
    """Loose coercion to the expected type with construction of nested values.

    If the given value does not match the expected type then it is returned as-is.
    """
    # we allow `object` as the input type because otherwise, passing things like
    # `Literal['value']` will be reported as a type error by type checkers
    type_ = cast("type[object]", type_)

    # unwrap `Annotated[T, ...]` -> `T`
    if is_annotated_type(type_):
        meta: tuple[Any, ...] = get_args(type_)[1:]
        type_ = extract_type_arg(type_, 0)
    else:
        meta = tuple()

    # we need to use the origin class for any types that are subscripted generics
    # e.g. Dict[str, object]
    origin = get_origin(type_) or type_
    args = get_args(type_)

    if is_union(origin):
        try:
            return validate_type(type_=cast("type[object]", type_), value=value)
        except Exception:
            pass

        # if the type is a discriminated union then we want to construct the right variant
        # in the union, even if the data doesn't match exactly, otherwise we'd break code
        # that relies on the constructed class types, e.g.
        #
        # class FooType:
        #   kind: Literal['foo']
        #   value: str
        #
        # class BarType:
        #   kind: Literal['bar']
        #   value: int
        #
        # without this block, if the data we get is something like `{'kind': 'bar', 'value': 'foo'}` then
        # we'd end up constructing `FooType` when it should be `BarType`.
        discriminator = _build_discriminated_union_meta(union=type_, meta_annotations=meta)
        if discriminator and is_mapping(value):
            variant_value = value.get(discriminator.field_alias_from or discriminator.field_name)
            if variant_value and isinstance(variant_value, str):
                variant_type = discriminator.mapping.get(variant_value)
                if variant_type:
                    return construct_type(type_=variant_type, value=value)

        # if the data is not valid, use the first variant that doesn't fail while deserializing
        for variant in args:
            try:
                return construct_type(value=value, type_=variant)
            except Exception:
                continue

        raise RuntimeError(f"Could not convert data into a valid instance of {type_}")

    if origin == dict:
        if not is_mapping(value):
            return value

        _, items_type = get_args(type_)  # Dict[_, items_type]
        return {key: construct_type(value=item, type_=items_type) for key, item in value.items()}

    if not is_literal_type(type_) and (issubclass(origin, BaseModel) or issubclass(origin, GenericModel)):
        if is_list(value):
            return [cast(Any, type_).construct(**entry) if is_mapping(entry) else entry for entry in value]

        if is_mapping(value):
            if issubclass(type_, BaseModel):
                return type_.construct(**value)  # type: ignore[arg-type]

            return cast(Any, type_).construct(**value)

    if origin == list:
        if not is_list(value):
            return value

        inner_type = args[0]  # List[inner_type]
        return [construct_type(value=entry, type_=inner_type) for entry in value]

    if origin == float:
        if isinstance(value, int):
            coerced = float(value)
            if coerced != value:
                return value
            return coerced

        return value

    if type_ == datetime:
        try:
            return parse_datetime(value)  # type: ignore
        except Exception:
            return value

    if type_ == date:
        try:
            return parse_date(value)  # type: ignore
        except Exception:
            return value

    return value


@runtime_checkable
class CachedDiscriminatorType(Protocol):
    __discriminator__: DiscriminatorDetails


class DiscriminatorDetails:
    field_name: str
    """The name of the discriminator field in the variant class, e.g.

    ```py
    class Foo(BaseModel):
        type: Literal['foo']
    ```

    Will result in field_name='type'
    """

    field_alias_from: str | None
    """The name of the discriminator field in the API response, e.g.

    ```py
    class Foo(BaseModel):
        type: Literal['foo'] = Field(alias='type_from_api')
    ```

    Will result in field_alias_from='type_from_api'
    """

    mapping: dict[str, type]
    """Mapping of discriminator value to variant type, e.g.

    {'foo': FooVariant, 'bar': BarVariant}
    """

    def __init__(
        self,
        *,
        mapping: dict[str, type],
        discriminator_field: str,
        discriminator_alias: str | None,
    ) -> None:
        self.mapping = mapping
        self.field_name = discriminator_field
        self.field_alias_from = discriminator_alias


def _build_discriminated_union_meta(*, union: type, meta_annotations: tuple[Any, ...]) -> DiscriminatorDetails | None:
    if isinstance(union, CachedDiscriminatorType):
        return union.__discriminator__

    discriminator_field_name: str | None = None

    for annotation in meta_annotations:
        if isinstance(annotation, PropertyInfo) and annotation.discriminator is not None:
            discriminator_field_name = annotation.discriminator
            break

    if not discriminator_field_name:
        return None

    mapping: dict[str, type] = {}
    discriminator_alias: str | None = None

    for variant in get_args(union):
        variant = strip_annotated_type(variant)
        if is_basemodel_type(variant):
            if PYDANTIC_V2:
                field = _extract_field_schema_pv2(variant, discriminator_field_name)
                if not field:
                    continue

                # Note: if one variant defines an alias then they all should
                discriminator_alias = field.get("serialization_alias")

                field_schema = field["schema"]

                if field_schema["type"] == "literal":
                    for entry in cast("LiteralSchema", field_schema)["expected"]:
                        if isinstance(entry, str):
                            mapping[entry] = variant
            else:
                field_info = cast("dict[str, FieldInfo]", variant.__fields__).get(discriminator_field_name)  # pyright: ignore[reportDeprecated, reportUnnecessaryCast]
                if not field_info:
                    continue

                # Note: if one variant defines an alias then they all should
                discriminator_alias = field_info.alias

                if field_info.annotation and is_literal_type(field_info.annotation):
                    for entry in get_args(field_info.annotation):
                        if isinstance(entry, str):
                            mapping[entry] = variant

    if not mapping:
        return None

    details = DiscriminatorDetails(
        mapping=mapping,
        discriminator_field=discriminator_field_name,
        discriminator_alias=discriminator_alias,
    )
    cast(CachedDiscriminatorType, union).__discriminator__ = details
    return details


def _extract_field_schema_pv2(model: type[BaseModel], field_name: str) -> ModelField | None:
    schema = model.__pydantic_core_schema__
    if schema["type"] != "model":
        return None

    fields_schema = schema["schema"]
    if fields_schema["type"] != "model-fields":
        return None

    fields_schema = cast("ModelFieldsSchema", fields_schema)

    field = fields_schema["fields"].get(field_name)
    if not field:
        return None

    return cast("ModelField", field)  # pyright: ignore[reportUnnecessaryCast]


def validate_type(*, type_: type[_T], value: object) -> _T:
    """Strict validation that the given value matches the expected type"""
    if inspect.isclass(type_) and issubclass(type_, pydantic.BaseModel):
        return cast(_T, parse_obj(type_, value))

    return cast(_T, _validate_non_model_type(type_=type_, value=value))


def set_pydantic_config(typ: Any, config: pydantic.ConfigDict) -> None:
    """Add a pydantic config for the given type.

    Note: this is a no-op on Pydantic v1.
    """
    setattr(typ, "__pydantic_config__", config)  # noqa: B010


# our use of subclasssing here causes weirdness for type checkers,
# so we just pretend that we don't subclass
if TYPE_CHECKING:
    GenericModel = BaseModel
else:

    class GenericModel(BaseGenericModel, BaseModel):
        pass


if PYDANTIC_V2:
    from pydantic import TypeAdapter as _TypeAdapter

    _CachedTypeAdapter = cast("TypeAdapter[object]", lru_cache(maxsize=None)(_TypeAdapter))

    if TYPE_CHECKING:
        from pydantic import TypeAdapter
    else:
        TypeAdapter = _CachedTypeAdapter

    def _validate_non_model_type(*, type_: type[_T], value: object) -> _T:
        return TypeAdapter(type_).validate_python(value)

elif not TYPE_CHECKING:  # TODO: condition is weird

    class RootModel(GenericModel, Generic[_T]):
        """Used as a placeholder to easily convert runtime types to a Pydantic format
        to provide validation.

        For example:
        ```py
        validated = RootModel[int](__root__="5").__root__
        # validated: 5
        ```
        """

        __root__: _T

    def _validate_non_model_type(*, type_: type[_T], value: object) -> _T:
        model = _create_pydantic_model(type_).validate(value)
        return cast(_T, model.__root__)

    def _create_pydantic_model(type_: _T) -> Type[RootModel[_T]]:
        return RootModel[type_]  # type: ignore


class FinalRequestOptionsInput(TypedDict, total=False):
    method: Required[str]
    url: Required[str]
    params: Query
    headers: Headers
    max_retries: int
    timeout: float | Timeout | None
    files: HttpxRequestFiles | None
    idempotency_key: str
    json_data: Body
    extra_json: AnyMapping


@final
class FinalRequestOptions(pydantic.BaseModel):
    method: str
    url: str
    params: Query = {}
    headers: Union[Headers, NotGiven] = NotGiven()
    max_retries: Union[int, NotGiven] = NotGiven()
    timeout: Union[float, Timeout, None, NotGiven] = NotGiven()
    files: Union[HttpxRequestFiles, None] = None
    idempotency_key: Union[str, None] = None
    post_parser: Union[Callable[[Any], Any], NotGiven] = NotGiven()

    # It should be noted that we cannot use `json` here as that would override
    # a BaseModel method in an incompatible fashion.
    json_data: Union[Body, None] = None
    extra_json: Union[AnyMapping, None] = None

    if PYDANTIC_V2:
        model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)
    else:

        class Config(pydantic.BaseConfig):  # pyright: ignore[reportDeprecated]
            arbitrary_types_allowed: bool = True

    def get_max_retries(self, max_retries: int) -> int:
        if isinstance(self.max_retries, NotGiven):
            return max_retries
        return self.max_retries

    def _strip_raw_response_header(self) -> None:
        if not is_given(self.headers):
            return

        if self.headers.get(RAW_RESPONSE_HEADER):
            self.headers = {**self.headers}
            self.headers.pop(RAW_RESPONSE_HEADER)

    # override the `construct` method so that we can run custom transformations.
    # this is necessary as we don't want to do any actual runtime type checking
    # (which means we can't use validators) but we do want to ensure that `NotGiven`
    # values are not present
    #
    # type ignore required because we're adding explicit types to `**values`
    @classmethod
    def construct(  # type: ignore
        cls,
        _fields_set: set[str] | None = None,
        **values: Unpack[FinalRequestOptionsInput],
    ) -> FinalRequestOptions:
        kwargs: dict[str, Any] = {
            # we unconditionally call `strip_not_given` on any value
            # as it will just ignore any non-mapping types
            key: strip_not_given(value)
            for key, value in values.items()
        }
        if PYDANTIC_V2:
            return super().model_construct(_fields_set, **kwargs)
        return cast(FinalRequestOptions, super().construct(_fields_set, **kwargs))  # pyright: ignore[reportDeprecated]

    if not TYPE_CHECKING:
        # type checkers incorrectly complain about this assignment
        model_construct = construct

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\retriever_service\transports\grpc.py ===
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
from typing import Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, grpc_helpers
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore
import grpc  # type: ignore

from google.ai.generativelanguage_v1beta.types import retriever, retriever_service

from .base import DEFAULT_CLIENT_INFO, RetrieverServiceTransport


class RetrieverServiceGrpcTransport(RetrieverServiceTransport):
    """gRPC backend transport for RetrieverService.

    An API for semantic search over a corpus of user uploaded
    content.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _stubs: Dict[str, Callable]

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]] = None,
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
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if a ``channel`` instance is provided.
            channel (Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]]):
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
          google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, grpc.Channel):
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

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> grpc.Channel:
        """Create and return a gRPC channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            grpc.Channel: A gRPC channel object.

        Raises:
            google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """

        return grpc_helpers.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    @property
    def grpc_channel(self) -> grpc.Channel:
        """Return the channel designed to connect to this service."""
        return self._grpc_channel

    @property
    def create_corpus(
        self,
    ) -> Callable[[retriever_service.CreateCorpusRequest], retriever.Corpus]:
        r"""Return a callable for the create corpus method over gRPC.

        Creates an empty ``Corpus``.

        Returns:
            Callable[[~.CreateCorpusRequest],
                    ~.Corpus]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_corpus" not in self._stubs:
            self._stubs["create_corpus"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/CreateCorpus",
                request_serializer=retriever_service.CreateCorpusRequest.serialize,
                response_deserializer=retriever.Corpus.deserialize,
            )
        return self._stubs["create_corpus"]

    @property
    def get_corpus(
        self,
    ) -> Callable[[retriever_service.GetCorpusRequest], retriever.Corpus]:
        r"""Return a callable for the get corpus method over gRPC.

        Gets information about a specific ``Corpus``.

        Returns:
            Callable[[~.GetCorpusRequest],
                    ~.Corpus]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_corpus" not in self._stubs:
            self._stubs["get_corpus"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/GetCorpus",
                request_serializer=retriever_service.GetCorpusRequest.serialize,
                response_deserializer=retriever.Corpus.deserialize,
            )
        return self._stubs["get_corpus"]

    @property
    def update_corpus(
        self,
    ) -> Callable[[retriever_service.UpdateCorpusRequest], retriever.Corpus]:
        r"""Return a callable for the update corpus method over gRPC.

        Updates a ``Corpus``.

        Returns:
            Callable[[~.UpdateCorpusRequest],
                    ~.Corpus]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_corpus" not in self._stubs:
            self._stubs["update_corpus"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/UpdateCorpus",
                request_serializer=retriever_service.UpdateCorpusRequest.serialize,
                response_deserializer=retriever.Corpus.deserialize,
            )
        return self._stubs["update_corpus"]

    @property
    def delete_corpus(
        self,
    ) -> Callable[[retriever_service.DeleteCorpusRequest], empty_pb2.Empty]:
        r"""Return a callable for the delete corpus method over gRPC.

        Deletes a ``Corpus``.

        Returns:
            Callable[[~.DeleteCorpusRequest],
                    ~.Empty]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_corpus" not in self._stubs:
            self._stubs["delete_corpus"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/DeleteCorpus",
                request_serializer=retriever_service.DeleteCorpusRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_corpus"]

    @property
    def list_corpora(
        self,
    ) -> Callable[
        [retriever_service.ListCorporaRequest], retriever_service.ListCorporaResponse
    ]:
        r"""Return a callable for the list corpora method over gRPC.

        Lists all ``Corpora`` owned by the user.

        Returns:
            Callable[[~.ListCorporaRequest],
                    ~.ListCorporaResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_corpora" not in self._stubs:
            self._stubs["list_corpora"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/ListCorpora",
                request_serializer=retriever_service.ListCorporaRequest.serialize,
                response_deserializer=retriever_service.ListCorporaResponse.deserialize,
            )
        return self._stubs["list_corpora"]

    @property
    def query_corpus(
        self,
    ) -> Callable[
        [retriever_service.QueryCorpusRequest], retriever_service.QueryCorpusResponse
    ]:
        r"""Return a callable for the query corpus method over gRPC.

        Performs semantic search over a ``Corpus``.

        Returns:
            Callable[[~.QueryCorpusRequest],
                    ~.QueryCorpusResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "query_corpus" not in self._stubs:
            self._stubs["query_corpus"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/QueryCorpus",
                request_serializer=retriever_service.QueryCorpusRequest.serialize,
                response_deserializer=retriever_service.QueryCorpusResponse.deserialize,
            )
        return self._stubs["query_corpus"]

    @property
    def create_document(
        self,
    ) -> Callable[[retriever_service.CreateDocumentRequest], retriever.Document]:
        r"""Return a callable for the create document method over gRPC.

        Creates an empty ``Document``.

        Returns:
            Callable[[~.CreateDocumentRequest],
                    ~.Document]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_document" not in self._stubs:
            self._stubs["create_document"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/CreateDocument",
                request_serializer=retriever_service.CreateDocumentRequest.serialize,
                response_deserializer=retriever.Document.deserialize,
            )
        return self._stubs["create_document"]

    @property
    def get_document(
        self,
    ) -> Callable[[retriever_service.GetDocumentRequest], retriever.Document]:
        r"""Return a callable for the get document method over gRPC.

        Gets information about a specific ``Document``.

        Returns:
            Callable[[~.GetDocumentRequest],
                    ~.Document]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_document" not in self._stubs:
            self._stubs["get_document"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/GetDocument",
                request_serializer=retriever_service.GetDocumentRequest.serialize,
                response_deserializer=retriever.Document.deserialize,
            )
        return self._stubs["get_document"]

    @property
    def update_document(
        self,
    ) -> Callable[[retriever_service.UpdateDocumentRequest], retriever.Document]:
        r"""Return a callable for the update document method over gRPC.

        Updates a ``Document``.

        Returns:
            Callable[[~.UpdateDocumentRequest],
                    ~.Document]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_document" not in self._stubs:
            self._stubs["update_document"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/UpdateDocument",
                request_serializer=retriever_service.UpdateDocumentRequest.serialize,
                response_deserializer=retriever.Document.deserialize,
            )
        return self._stubs["update_document"]

    @property
    def delete_document(
        self,
    ) -> Callable[[retriever_service.DeleteDocumentRequest], empty_pb2.Empty]:
        r"""Return a callable for the delete document method over gRPC.

        Deletes a ``Document``.

        Returns:
            Callable[[~.DeleteDocumentRequest],
                    ~.Empty]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_document" not in self._stubs:
            self._stubs["delete_document"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/DeleteDocument",
                request_serializer=retriever_service.DeleteDocumentRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_document"]

    @property
    def list_documents(
        self,
    ) -> Callable[
        [retriever_service.ListDocumentsRequest],
        retriever_service.ListDocumentsResponse,
    ]:
        r"""Return a callable for the list documents method over gRPC.

        Lists all ``Document``\ s in a ``Corpus``.

        Returns:
            Callable[[~.ListDocumentsRequest],
                    ~.ListDocumentsResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_documents" not in self._stubs:
            self._stubs["list_documents"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/ListDocuments",
                request_serializer=retriever_service.ListDocumentsRequest.serialize,
                response_deserializer=retriever_service.ListDocumentsResponse.deserialize,
            )
        return self._stubs["list_documents"]

    @property
    def query_document(
        self,
    ) -> Callable[
        [retriever_service.QueryDocumentRequest],
        retriever_service.QueryDocumentResponse,
    ]:
        r"""Return a callable for the query document method over gRPC.

        Performs semantic search over a ``Document``.

        Returns:
            Callable[[~.QueryDocumentRequest],
                    ~.QueryDocumentResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "query_document" not in self._stubs:
            self._stubs["query_document"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/QueryDocument",
                request_serializer=retriever_service.QueryDocumentRequest.serialize,
                response_deserializer=retriever_service.QueryDocumentResponse.deserialize,
            )
        return self._stubs["query_document"]

    @property
    def create_chunk(
        self,
    ) -> Callable[[retriever_service.CreateChunkRequest], retriever.Chunk]:
        r"""Return a callable for the create chunk method over gRPC.

        Creates a ``Chunk``.

        Returns:
            Callable[[~.CreateChunkRequest],
                    ~.Chunk]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_chunk" not in self._stubs:
            self._stubs["create_chunk"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/CreateChunk",
                request_serializer=retriever_service.CreateChunkRequest.serialize,
                response_deserializer=retriever.Chunk.deserialize,
            )
        return self._stubs["create_chunk"]

    @property
    def batch_create_chunks(
        self,
    ) -> Callable[
        [retriever_service.BatchCreateChunksRequest],
        retriever_service.BatchCreateChunksResponse,
    ]:
        r"""Return a callable for the batch create chunks method over gRPC.

        Batch create ``Chunk``\ s.

        Returns:
            Callable[[~.BatchCreateChunksRequest],
                    ~.BatchCreateChunksResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "batch_create_chunks" not in self._stubs:
            self._stubs["batch_create_chunks"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/BatchCreateChunks",
                request_serializer=retriever_service.BatchCreateChunksRequest.serialize,
                response_deserializer=retriever_service.BatchCreateChunksResponse.deserialize,
            )
        return self._stubs["batch_create_chunks"]

    @property
    def get_chunk(
        self,
    ) -> Callable[[retriever_service.GetChunkRequest], retriever.Chunk]:
        r"""Return a callable for the get chunk method over gRPC.

        Gets information about a specific ``Chunk``.

        Returns:
            Callable[[~.GetChunkRequest],
                    ~.Chunk]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_chunk" not in self._stubs:
            self._stubs["get_chunk"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/GetChunk",
                request_serializer=retriever_service.GetChunkRequest.serialize,
                response_deserializer=retriever.Chunk.deserialize,
            )
        return self._stubs["get_chunk"]

    @property
    def update_chunk(
        self,
    ) -> Callable[[retriever_service.UpdateChunkRequest], retriever.Chunk]:
        r"""Return a callable for the update chunk method over gRPC.

        Updates a ``Chunk``.

        Returns:
            Callable[[~.UpdateChunkRequest],
                    ~.Chunk]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_chunk" not in self._stubs:
            self._stubs["update_chunk"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/UpdateChunk",
                request_serializer=retriever_service.UpdateChunkRequest.serialize,
                response_deserializer=retriever.Chunk.deserialize,
            )
        return self._stubs["update_chunk"]

    @property
    def batch_update_chunks(
        self,
    ) -> Callable[
        [retriever_service.BatchUpdateChunksRequest],
        retriever_service.BatchUpdateChunksResponse,
    ]:
        r"""Return a callable for the batch update chunks method over gRPC.

        Batch update ``Chunk``\ s.

        Returns:
            Callable[[~.BatchUpdateChunksRequest],
                    ~.BatchUpdateChunksResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "batch_update_chunks" not in self._stubs:
            self._stubs["batch_update_chunks"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/BatchUpdateChunks",
                request_serializer=retriever_service.BatchUpdateChunksRequest.serialize,
                response_deserializer=retriever_service.BatchUpdateChunksResponse.deserialize,
            )
        return self._stubs["batch_update_chunks"]

    @property
    def delete_chunk(
        self,
    ) -> Callable[[retriever_service.DeleteChunkRequest], empty_pb2.Empty]:
        r"""Return a callable for the delete chunk method over gRPC.

        Deletes a ``Chunk``.

        Returns:
            Callable[[~.DeleteChunkRequest],
                    ~.Empty]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_chunk" not in self._stubs:
            self._stubs["delete_chunk"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/DeleteChunk",
                request_serializer=retriever_service.DeleteChunkRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_chunk"]

    @property
    def batch_delete_chunks(
        self,
    ) -> Callable[[retriever_service.BatchDeleteChunksRequest], empty_pb2.Empty]:
        r"""Return a callable for the batch delete chunks method over gRPC.

        Batch delete ``Chunk``\ s.

        Returns:
            Callable[[~.BatchDeleteChunksRequest],
                    ~.Empty]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "batch_delete_chunks" not in self._stubs:
            self._stubs["batch_delete_chunks"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/BatchDeleteChunks",
                request_serializer=retriever_service.BatchDeleteChunksRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["batch_delete_chunks"]

    @property
    def list_chunks(
        self,
    ) -> Callable[
        [retriever_service.ListChunksRequest], retriever_service.ListChunksResponse
    ]:
        r"""Return a callable for the list chunks method over gRPC.

        Lists all ``Chunk``\ s in a ``Document``.

        Returns:
            Callable[[~.ListChunksRequest],
                    ~.ListChunksResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_chunks" not in self._stubs:
            self._stubs["list_chunks"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/ListChunks",
                request_serializer=retriever_service.ListChunksRequest.serialize,
                response_deserializer=retriever_service.ListChunksResponse.deserialize,
            )
        return self._stubs["list_chunks"]

    def close(self):
        self.grpc_channel.close()

    @property
    def kind(self) -> str:
        return "grpc"


__all__ = ("RetrieverServiceGrpcTransport",)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\commands\install.py ===
import errno
import json
import operator
import os
import shutil
import site
from optparse import SUPPRESS_HELP, Values
from typing import List, Optional

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.rich import print_json

# Eagerly import self_outdated_check to avoid crashes. Otherwise,
# this module would be imported *after* pip was replaced, resulting
# in crashes if the new self_outdated_check module was incompatible
# with the rest of pip that's already imported, or allowing a
# wheel to execute arbitrary code on install by replacing
# self_outdated_check.
import pip._internal.self_outdated_check  # noqa: F401
from pip._internal.cache import WheelCache
from pip._internal.cli import cmdoptions
from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.cli.req_command import (
    RequirementCommand,
    with_cleanup,
)
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.exceptions import CommandError, InstallationError
from pip._internal.locations import get_scheme
from pip._internal.metadata import get_environment
from pip._internal.models.installation_report import InstallationReport
from pip._internal.operations.build.build_tracker import get_build_tracker
from pip._internal.operations.check import ConflictDetails, check_install_conflicts
from pip._internal.req import install_given_reqs
from pip._internal.req.req_install import (
    InstallRequirement,
    check_legacy_setup_py_options,
)
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.filesystem import test_writable_dir
from pip._internal.utils.logging import getLogger
from pip._internal.utils.misc import (
    check_externally_managed,
    ensure_dir,
    get_pip_version,
    protect_pip_from_modification_on_windows,
    warn_if_run_as_root,
    write_output,
)
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.virtualenv import (
    running_under_virtualenv,
    virtualenv_no_global,
)
from pip._internal.wheel_builder import build, should_build_for_install_command

logger = getLogger(__name__)


class InstallCommand(RequirementCommand):
    """
    Install packages from:

    - PyPI (and other indexes) using requirement specifiers.
    - VCS project urls.
    - Local project directories.
    - Local or remote source archives.

    pip also supports installing from "requirements files", which provide
    an easy way to specify a whole environment to be installed.
    """

    usage = """
      %prog [options] <requirement specifier> [package-index-options] ...
      %prog [options] -r <requirements file> [package-index-options] ...
      %prog [options] [-e] <vcs project url> ...
      %prog [options] [-e] <local project path> ...
      %prog [options] <archive url/path> ..."""

    def add_options(self) -> None:
        self.cmd_opts.add_option(cmdoptions.requirements())
        self.cmd_opts.add_option(cmdoptions.constraints())
        self.cmd_opts.add_option(cmdoptions.no_deps())
        self.cmd_opts.add_option(cmdoptions.pre())

        self.cmd_opts.add_option(cmdoptions.editable())
        self.cmd_opts.add_option(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help=(
                "Don't actually install anything, just print what would be. "
                "Can be used in combination with --ignore-installed "
                "to 'resolve' the requirements."
            ),
        )
        self.cmd_opts.add_option(
            "-t",
            "--target",
            dest="target_dir",
            metavar="dir",
            default=None,
            help=(
                "Install packages into <dir>. "
                "By default this will not replace existing files/folders in "
                "<dir>. Use --upgrade to replace existing packages in <dir> "
                "with new versions."
            ),
        )
        cmdoptions.add_target_python_options(self.cmd_opts)

        self.cmd_opts.add_option(
            "--user",
            dest="use_user_site",
            action="store_true",
            help=(
                "Install to the Python user install directory for your "
                "platform. Typically ~/.local/, or %APPDATA%\\Python on "
                "Windows. (See the Python documentation for site.USER_BASE "
                "for full details.)"
            ),
        )
        self.cmd_opts.add_option(
            "--no-user",
            dest="use_user_site",
            action="store_false",
            help=SUPPRESS_HELP,
        )
        self.cmd_opts.add_option(
            "--root",
            dest="root_path",
            metavar="dir",
            default=None,
            help="Install everything relative to this alternate root directory.",
        )
        self.cmd_opts.add_option(
            "--prefix",
            dest="prefix_path",
            metavar="dir",
            default=None,
            help=(
                "Installation prefix where lib, bin and other top-level "
                "folders are placed. Note that the resulting installation may "
                "contain scripts and other resources which reference the "
                "Python interpreter of pip, and not that of ``--prefix``. "
                "See also the ``--python`` option if the intention is to "
                "install packages into another (possibly pip-free) "
                "environment."
            ),
        )

        self.cmd_opts.add_option(cmdoptions.src())

        self.cmd_opts.add_option(
            "-U",
            "--upgrade",
            dest="upgrade",
            action="store_true",
            help=(
                "Upgrade all specified packages to the newest available "
                "version. The handling of dependencies depends on the "
                "upgrade-strategy used."
            ),
        )

        self.cmd_opts.add_option(
            "--upgrade-strategy",
            dest="upgrade_strategy",
            default="only-if-needed",
            choices=["only-if-needed", "eager"],
            help=(
                "Determines how dependency upgrading should be handled "
                "[default: %default]. "
                '"eager" - dependencies are upgraded regardless of '
                "whether the currently installed version satisfies the "
                "requirements of the upgraded package(s). "
                '"only-if-needed" -  are upgraded only when they do not '
                "satisfy the requirements of the upgraded package(s)."
            ),
        )

        self.cmd_opts.add_option(
            "--force-reinstall",
            dest="force_reinstall",
            action="store_true",
            help="Reinstall all packages even if they are already up-to-date.",
        )

        self.cmd_opts.add_option(
            "-I",
            "--ignore-installed",
            dest="ignore_installed",
            action="store_true",
            help=(
                "Ignore the installed packages, overwriting them. "
                "This can break your system if the existing package "
                "is of a different version or was installed "
                "with a different package manager!"
            ),
        )

        self.cmd_opts.add_option(cmdoptions.ignore_requires_python())
        self.cmd_opts.add_option(cmdoptions.no_build_isolation())
        self.cmd_opts.add_option(cmdoptions.use_pep517())
        self.cmd_opts.add_option(cmdoptions.no_use_pep517())
        self.cmd_opts.add_option(cmdoptions.check_build_deps())
        self.cmd_opts.add_option(cmdoptions.override_externally_managed())

        self.cmd_opts.add_option(cmdoptions.config_settings())
        self.cmd_opts.add_option(cmdoptions.global_options())

        self.cmd_opts.add_option(
            "--compile",
            action="store_true",
            dest="compile",
            default=True,
            help="Compile Python source files to bytecode",
        )

        self.cmd_opts.add_option(
            "--no-compile",
            action="store_false",
            dest="compile",
            help="Do not compile Python source files to bytecode",
        )

        self.cmd_opts.add_option(
            "--no-warn-script-location",
            action="store_false",
            dest="warn_script_location",
            default=True,
            help="Do not warn when installing scripts outside PATH",
        )
        self.cmd_opts.add_option(
            "--no-warn-conflicts",
            action="store_false",
            dest="warn_about_conflicts",
            default=True,
            help="Do not warn about broken dependencies",
        )
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())
        self.cmd_opts.add_option(cmdoptions.prefer_binary())
        self.cmd_opts.add_option(cmdoptions.require_hashes())
        self.cmd_opts.add_option(cmdoptions.progress_bar())
        self.cmd_opts.add_option(cmdoptions.root_user_action())

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, self.cmd_opts)

        self.cmd_opts.add_option(
            "--report",
            dest="json_report_file",
            metavar="file",
            default=None,
            help=(
                "Generate a JSON file describing what pip did to install "
                "the provided requirements. "
                "Can be used in combination with --dry-run and --ignore-installed "
                "to 'resolve' the requirements. "
                "When - is used as file name it writes to stdout. "
                "When writing to stdout, please combine with the --quiet option "
                "to avoid mixing pip logging output with JSON output."
            ),
        )

    @with_cleanup
    def run(self, options: Values, args: List[str]) -> int:
        if options.use_user_site and options.target_dir is not None:
            raise CommandError("Can not combine '--user' and '--target'")

        # Check whether the environment we're installing into is externally
        # managed, as specified in PEP 668. Specifying --root, --target, or
        # --prefix disables the check, since there's no reliable way to locate
        # the EXTERNALLY-MANAGED file for those cases. An exception is also
        # made specifically for "--dry-run --report" for convenience.
        installing_into_current_environment = (
            not (options.dry_run and options.json_report_file)
            and options.root_path is None
            and options.target_dir is None
            and options.prefix_path is None
        )
        if (
            installing_into_current_environment
            and not options.override_externally_managed
        ):
            check_externally_managed()

        upgrade_strategy = "to-satisfy-only"
        if options.upgrade:
            upgrade_strategy = options.upgrade_strategy

        cmdoptions.check_dist_restriction(options, check_target=True)

        logger.verbose("Using %s", get_pip_version())
        options.use_user_site = decide_user_install(
            options.use_user_site,
            prefix_path=options.prefix_path,
            target_dir=options.target_dir,
            root_path=options.root_path,
            isolated_mode=options.isolated_mode,
        )

        target_temp_dir: Optional[TempDirectory] = None
        target_temp_dir_path: Optional[str] = None
        if options.target_dir:
            options.ignore_installed = True
            options.target_dir = os.path.abspath(options.target_dir)
            if (
                # fmt: off
                os.path.exists(options.target_dir) and
                not os.path.isdir(options.target_dir)
                # fmt: on
            ):
                raise CommandError(
                    "Target path exists but is not a directory, will not continue."
                )

            # Create a target directory for using with the target option
            target_temp_dir = TempDirectory(kind="target")
            target_temp_dir_path = target_temp_dir.path
            self.enter_context(target_temp_dir)

        global_options = options.global_options or []

        session = self.get_default_session(options)

        target_python = make_target_python(options)
        finder = self._build_package_finder(
            options=options,
            session=session,
            target_python=target_python,
            ignore_requires_python=options.ignore_requires_python,
        )
        build_tracker = self.enter_context(get_build_tracker())

        directory = TempDirectory(
            delete=not options.no_clean,
            kind="install",
            globally_managed=True,
        )

        try:
            reqs = self.get_requirements(args, options, finder, session)
            check_legacy_setup_py_options(options, reqs)

            wheel_cache = WheelCache(options.cache_dir)

            # Only when installing is it permitted to use PEP 660.
            # In other circumstances (pip wheel, pip download) we generate
            # regular (i.e. non editable) metadata and wheels.
            for req in reqs:
                req.permit_editable_wheels = True

            preparer = self.make_requirement_preparer(
                temp_build_dir=directory,
                options=options,
                build_tracker=build_tracker,
                session=session,
                finder=finder,
                use_user_site=options.use_user_site,
                verbosity=self.verbosity,
            )
            resolver = self.make_resolver(
                preparer=preparer,
                finder=finder,
                options=options,
                wheel_cache=wheel_cache,
                use_user_site=options.use_user_site,
                ignore_installed=options.ignore_installed,
                ignore_requires_python=options.ignore_requires_python,
                force_reinstall=options.force_reinstall,
                upgrade_strategy=upgrade_strategy,
                use_pep517=options.use_pep517,
                py_version_info=options.python_version,
            )

            self.trace_basic_info(finder)

            requirement_set = resolver.resolve(
                reqs, check_supported_wheels=not options.target_dir
            )

            if options.json_report_file:
                report = InstallationReport(requirement_set.requirements_to_install)
                if options.json_report_file == "-":
                    print_json(data=report.to_dict())
                else:
                    with open(options.json_report_file, "w", encoding="utf-8") as f:
                        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

            if options.dry_run:
                would_install_items = sorted(
                    (r.metadata["name"], r.metadata["version"])
                    for r in requirement_set.requirements_to_install
                )
                if would_install_items:
                    write_output(
                        "Would install %s",
                        " ".join("-".join(item) for item in would_install_items),
                    )
                return SUCCESS

            try:
                pip_req = requirement_set.get_requirement("pip")
            except KeyError:
                modifying_pip = False
            else:
                # If we're not replacing an already installed pip,
                # we're not modifying it.
                modifying_pip = pip_req.satisfied_by is None
            protect_pip_from_modification_on_windows(modifying_pip=modifying_pip)

            reqs_to_build = [
                r
                for r in requirement_set.requirements.values()
                if should_build_for_install_command(r)
            ]

            _, build_failures = build(
                reqs_to_build,
                wheel_cache=wheel_cache,
                verify=True,
                build_options=[],
                global_options=global_options,
            )

            if build_failures:
                raise InstallationError(
                    "Failed to build installable wheels for some "
                    "pyproject.toml based projects ({})".format(
                        ", ".join(r.name for r in build_failures)  # type: ignore
                    )
                )

            to_install = resolver.get_installation_order(requirement_set)

            # Check for conflicts in the package set we're installing.
            conflicts: Optional[ConflictDetails] = None
            should_warn_about_conflicts = (
                not options.ignore_dependencies and options.warn_about_conflicts
            )
            if should_warn_about_conflicts:
                conflicts = self._determine_conflicts(to_install)

            # Don't warn about script install locations if
            # --target or --prefix has been specified
            warn_script_location = options.warn_script_location
            if options.target_dir or options.prefix_path:
                warn_script_location = False

            installed = install_given_reqs(
                to_install,
                global_options,
                root=options.root_path,
                home=target_temp_dir_path,
                prefix=options.prefix_path,
                warn_script_location=warn_script_location,
                use_user_site=options.use_user_site,
                pycompile=options.compile,
            )

            lib_locations = get_lib_location_guesses(
                user=options.use_user_site,
                home=target_temp_dir_path,
                root=options.root_path,
                prefix=options.prefix_path,
                isolated=options.isolated_mode,
            )
            env = get_environment(lib_locations)

            # Display a summary of installed packages, with extra care to
            # display a package name as it was requested by the user.
            installed.sort(key=operator.attrgetter("name"))
            summary = []
            installed_versions = {}
            for distribution in env.iter_all_distributions():
                installed_versions[distribution.canonical_name] = distribution.version
            for package in installed:
                display_name = package.name
                version = installed_versions.get(canonicalize_name(display_name), None)
                if version:
                    text = f"{display_name}-{version}"
                else:
                    text = display_name
                summary.append(text)

            if conflicts is not None:
                self._warn_about_conflicts(
                    conflicts,
                    resolver_variant=self.determine_resolver_variant(options),
                )

            installed_desc = " ".join(summary)
            if installed_desc:
                write_output(
                    "Successfully installed %s",
                    installed_desc,
                )
        except OSError as error:
            show_traceback = self.verbosity >= 1

            message = create_os_error_message(
                error,
                show_traceback,
                options.use_user_site,
            )
            logger.error(message, exc_info=show_traceback)

            return ERROR

        if options.target_dir:
            assert target_temp_dir
            self._handle_target_dir(
                options.target_dir, target_temp_dir, options.upgrade
            )
        if options.root_user_action == "warn":
            warn_if_run_as_root()
        return SUCCESS

    def _handle_target_dir(
        self, target_dir: str, target_temp_dir: TempDirectory, upgrade: bool
    ) -> None:
        ensure_dir(target_dir)

        # Checking both purelib and platlib directories for installed
        # packages to be moved to target directory
        lib_dir_list = []

        # Checking both purelib and platlib directories for installed
        # packages to be moved to target directory
        scheme = get_scheme("", home=target_temp_dir.path)
        purelib_dir = scheme.purelib
        platlib_dir = scheme.platlib
        data_dir = scheme.data

        if os.path.exists(purelib_dir):
            lib_dir_list.append(purelib_dir)
        if os.path.exists(platlib_dir) and platlib_dir != purelib_dir:
            lib_dir_list.append(platlib_dir)
        if os.path.exists(data_dir):
            lib_dir_list.append(data_dir)

        for lib_dir in lib_dir_list:
            for item in os.listdir(lib_dir):
                if lib_dir == data_dir:
                    ddir = os.path.join(data_dir, item)
                    if any(s.startswith(ddir) for s in lib_dir_list[:-1]):
                        continue
                target_item_dir = os.path.join(target_dir, item)
                if os.path.exists(target_item_dir):
                    if not upgrade:
                        logger.warning(
                            "Target directory %s already exists. Specify "
                            "--upgrade to force replacement.",
                            target_item_dir,
                        )
                        continue
                    if os.path.islink(target_item_dir):
                        logger.warning(
                            "Target directory %s already exists and is "
                            "a link. pip will not automatically replace "
                            "links, please remove if replacement is "
                            "desired.",
                            target_item_dir,
                        )
                        continue
                    if os.path.isdir(target_item_dir):
                        shutil.rmtree(target_item_dir)
                    else:
                        os.remove(target_item_dir)

                shutil.move(os.path.join(lib_dir, item), target_item_dir)

    def _determine_conflicts(
        self, to_install: List[InstallRequirement]
    ) -> Optional[ConflictDetails]:
        try:
            return check_install_conflicts(to_install)
        except Exception:
            logger.exception(
                "Error while checking for conflicts. Please file an issue on "
                "pip's issue tracker: https://github.com/pypa/pip/issues/new"
            )
            return None

    def _warn_about_conflicts(
        self, conflict_details: ConflictDetails, resolver_variant: str
    ) -> None:
        package_set, (missing, conflicting) = conflict_details
        if not missing and not conflicting:
            return

        parts: List[str] = []
        if resolver_variant == "legacy":
            parts.append(
                "pip's legacy dependency resolver does not consider dependency "
                "conflicts when selecting packages. This behaviour is the "
                "source of the following dependency conflicts."
            )
        else:
            assert resolver_variant == "resolvelib"
            parts.append(
                "pip's dependency resolver does not currently take into account "
                "all the packages that are installed. This behaviour is the "
                "source of the following dependency conflicts."
            )

        # NOTE: There is some duplication here, with commands/check.py
        for project_name in missing:
            version = package_set[project_name][0]
            for dependency in missing[project_name]:
                message = (
                    f"{project_name} {version} requires {dependency[1]}, "
                    "which is not installed."
                )
                parts.append(message)

        for project_name in conflicting:
            version = package_set[project_name][0]
            for dep_name, dep_version, req in conflicting[project_name]:
                message = (
                    "{name} {version} requires {requirement}, but {you} have "
                    "{dep_name} {dep_version} which is incompatible."
                ).format(
                    name=project_name,
                    version=version,
                    requirement=req,
                    dep_name=dep_name,
                    dep_version=dep_version,
                    you=("you" if resolver_variant == "resolvelib" else "you'll"),
                )
                parts.append(message)

        logger.critical("\n".join(parts))


def get_lib_location_guesses(
    user: bool = False,
    home: Optional[str] = None,
    root: Optional[str] = None,
    isolated: bool = False,
    prefix: Optional[str] = None,
) -> List[str]:
    scheme = get_scheme(
        "",
        user=user,
        home=home,
        root=root,
        isolated=isolated,
        prefix=prefix,
    )
    return [scheme.purelib, scheme.platlib]


def site_packages_writable(root: Optional[str], isolated: bool) -> bool:
    return all(
        test_writable_dir(d)
        for d in set(get_lib_location_guesses(root=root, isolated=isolated))
    )


def decide_user_install(
    use_user_site: Optional[bool],
    prefix_path: Optional[str] = None,
    target_dir: Optional[str] = None,
    root_path: Optional[str] = None,
    isolated_mode: bool = False,
) -> bool:
    """Determine whether to do a user install based on the input options.

    If use_user_site is False, no additional checks are done.
    If use_user_site is True, it is checked for compatibility with other
    options.
    If use_user_site is None, the default behaviour depends on the environment,
    which is provided by the other arguments.
    """
    # In some cases (config from tox), use_user_site can be set to an integer
    # rather than a bool, which 'use_user_site is False' wouldn't catch.
    if (use_user_site is not None) and (not use_user_site):
        logger.debug("Non-user install by explicit request")
        return False

    if use_user_site:
        if prefix_path:
            raise CommandError(
                "Can not combine '--user' and '--prefix' as they imply "
                "different installation locations"
            )
        if virtualenv_no_global():
            raise InstallationError(
                "Can not perform a '--user' install. User site-packages "
                "are not visible in this virtualenv."
            )
        logger.debug("User install by explicit request")
        return True

    # If we are here, user installs have not been explicitly requested/avoided
    assert use_user_site is None

    # user install incompatible with --prefix/--target
    if prefix_path or target_dir:
        logger.debug("Non-user install due to --prefix or --target option")
        return False

    # If user installs are not enabled, choose a non-user install
    if not site.ENABLE_USER_SITE:
        logger.debug("Non-user install because user site-packages disabled")
        return False

    # If we have permission for a non-user install, do that,
    # otherwise do a user install.
    if site_packages_writable(root=root_path, isolated=isolated_mode):
        logger.debug("Non-user install because site-packages writeable")
        return False

    logger.info(
        "Defaulting to user installation because normal site-packages "
        "is not writeable"
    )
    return True


def create_os_error_message(
    error: OSError, show_traceback: bool, using_user_site: bool
) -> str:
    """Format an error message for an OSError

    It may occur anytime during the execution of the install command.
    """
    parts = []

    # Mention the error if we are not going to show a traceback
    parts.append("Could not install packages due to an OSError")
    if not show_traceback:
        parts.append(": ")
        parts.append(str(error))
    else:
        parts.append(".")

    # Spilt the error indication from a helper message (if any)
    parts[-1] += "\n"

    # Suggest useful actions to the user:
    #  (1) using user site-packages or (2) verifying the permissions
    if error.errno == errno.EACCES:
        user_option_part = "Consider using the `--user` option"
        permissions_part = "Check the permissions"

        if not running_under_virtualenv() and not using_user_site:
            parts.extend(
                [
                    user_option_part,
                    " or ",
                    permissions_part.lower(),
                ]
            )
        else:
            parts.append(permissions_part)
        parts.append(".\n")

    # Suggest the user to enable Long Paths if path length is
    # more than 260
    if (
        WINDOWS
        and error.errno == errno.ENOENT
        and error.filename
        and len(error.filename) > 260
    ):
        parts.append(
            "HINT: This error might have occurred since "
            "this system does not have Windows Long Path "
            "support enabled. You can find information on "
            "how to enable this at "
            "https://pip.pypa.io/warnings/enable-long-paths\n"
        )

    return "".join(parts).strip() + "\n"

# === NexusCore/openenv\Lib\site-packages\nltk\text.py ===
# Natural Language Toolkit: Texts
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
This module brings together a variety of NLTK functionality for
text analysis, and provides simple, interactive interfaces.
Functionality includes: concordancing, collocation discovery,
regular expression search over tokenized strings, and
distributional similarity.
"""

import re
import sys
import unicodedata
from collections import Counter, defaultdict, namedtuple
from functools import reduce
from math import log

from nltk.collocations import BigramCollocationFinder
from nltk.lm import MLE
from nltk.lm.preprocessing import padded_everygram_pipeline
from nltk.metrics import BigramAssocMeasures, f_measure
from nltk.probability import ConditionalFreqDist as CFD
from nltk.probability import FreqDist
from nltk.tokenize import sent_tokenize
from nltk.util import LazyConcatenation, cut_string, tokenwrap

ConcordanceLine = namedtuple(
    "ConcordanceLine",
    ["left", "query", "right", "offset", "left_print", "right_print", "line"],
)


class ContextIndex:
    """
    A bidirectional index between words and their 'contexts' in a text.
    The context of a word is usually defined to be the words that occur
    in a fixed window around the word; but other definitions may also
    be used by providing a custom context function.
    """

    @staticmethod
    def _default_context(tokens, i):
        """One left token and one right token, normalized to lowercase"""
        left = tokens[i - 1].lower() if i != 0 else "*START*"
        right = tokens[i + 1].lower() if i != len(tokens) - 1 else "*END*"
        return (left, right)

    def __init__(self, tokens, context_func=None, filter=None, key=lambda x: x):
        self._key = key
        self._tokens = tokens
        if context_func:
            self._context_func = context_func
        else:
            self._context_func = self._default_context
        if filter:
            tokens = [t for t in tokens if filter(t)]
        self._word_to_contexts = CFD(
            (self._key(w), self._context_func(tokens, i)) for i, w in enumerate(tokens)
        )
        self._context_to_words = CFD(
            (self._context_func(tokens, i), self._key(w)) for i, w in enumerate(tokens)
        )

    def tokens(self):
        """
        :rtype: list(str)
        :return: The document that this context index was
            created from.
        """
        return self._tokens

    def word_similarity_dict(self, word):
        """
        Return a dictionary mapping from words to 'similarity scores,'
        indicating how often these two words occur in the same
        context.
        """
        word = self._key(word)
        word_contexts = set(self._word_to_contexts[word])

        scores = {}
        for w, w_contexts in self._word_to_contexts.items():
            scores[w] = f_measure(word_contexts, set(w_contexts))

        return scores

    def similar_words(self, word, n=20):
        scores = defaultdict(int)
        for c in self._word_to_contexts[self._key(word)]:
            for w in self._context_to_words[c]:
                if w != word:
                    scores[w] += (
                        self._context_to_words[c][word] * self._context_to_words[c][w]
                    )
        return sorted(scores, key=scores.get, reverse=True)[:n]

    def common_contexts(self, words, fail_on_unknown=False):
        """
        Find contexts where the specified words can all appear; and
        return a frequency distribution mapping each context to the
        number of times that context was used.

        :param words: The words used to seed the similarity search
        :type words: str
        :param fail_on_unknown: If true, then raise a value error if
            any of the given words do not occur at all in the index.
        """
        words = [self._key(w) for w in words]
        contexts = [set(self._word_to_contexts[w]) for w in words]
        empty = [words[i] for i in range(len(words)) if not contexts[i]]
        common = reduce(set.intersection, contexts)
        if empty and fail_on_unknown:
            raise ValueError("The following word(s) were not found:", " ".join(words))
        elif not common:
            # nothing in common -- just return an empty freqdist.
            return FreqDist()
        else:
            fd = FreqDist(
                c for w in words for c in self._word_to_contexts[w] if c in common
            )
            return fd


class ConcordanceIndex:
    """
    An index that can be used to look up the offset locations at which
    a given word occurs in a document.
    """

    def __init__(self, tokens, key=lambda x: x):
        """
        Construct a new concordance index.

        :param tokens: The document (list of tokens) that this
            concordance index was created from.  This list can be used
            to access the context of a given word occurrence.
        :param key: A function that maps each token to a normalized
            version that will be used as a key in the index.  E.g., if
            you use ``key=lambda s:s.lower()``, then the index will be
            case-insensitive.
        """
        self._tokens = tokens
        """The document (list of tokens) that this concordance index
           was created from."""

        self._key = key
        """Function mapping each token to an index key (or None)."""

        self._offsets = defaultdict(list)
        """Dictionary mapping words (or keys) to lists of offset indices."""
        # Initialize the index (self._offsets)
        for index, word in enumerate(tokens):
            word = self._key(word)
            self._offsets[word].append(index)

    def tokens(self):
        """
        :rtype: list(str)
        :return: The document that this concordance index was
            created from.
        """
        return self._tokens

    def offsets(self, word):
        """
        :rtype: list(int)
        :return: A list of the offset positions at which the given
            word occurs.  If a key function was specified for the
            index, then given word's key will be looked up.
        """
        word = self._key(word)
        return self._offsets[word]

    def __repr__(self):
        return "<ConcordanceIndex for %d tokens (%d types)>" % (
            len(self._tokens),
            len(self._offsets),
        )

    def find_concordance(self, word, width=80):
        """
        Find all concordance lines given the query word.

        Provided with a list of words, these will be found as a phrase.
        """
        if isinstance(word, list):
            phrase = word
        else:
            phrase = [word]

        phrase_str = " ".join(phrase)
        phrase_len = sum(1 for char in phrase_str if not unicodedata.combining(char))
        half_width = (width - phrase_len - 2) // 2
        context = width // 4  # approx number of words of context

        # Find the instances of the word to create the ConcordanceLine
        concordance_list = []
        offsets = self.offsets(phrase[0])
        for i, word in enumerate(phrase[1:]):
            word_offsets = {offset - i - 1 for offset in self.offsets(word)}
            offsets = sorted(word_offsets.intersection(offsets))
        if offsets:
            for i in offsets:
                query_word = " ".join(self._tokens[i : i + len(phrase)])
                # Find the context of query word.
                left_context = self._tokens[max(0, i - context) : i]
                right_context = self._tokens[i + len(phrase) : i + context]
                # Create the pretty lines with the query_word in the middle.
                left_print = cut_string(" ".join(left_context), -half_width).rjust(
                    half_width
                )
                right_print = cut_string(" ".join(right_context), half_width)
                # The WYSIWYG line of the concordance.
                line_print = " ".join([left_print, query_word, right_print])
                # Create the ConcordanceLine
                concordance_line = ConcordanceLine(
                    left_context,
                    query_word,
                    right_context,
                    i,
                    left_print,
                    right_print,
                    line_print,
                )
                concordance_list.append(concordance_line)
        return concordance_list

    def print_concordance(self, word, width=80, lines=25):
        """
        Print concordance lines given the query word.
        :param word: The target word or phrase (a list of strings)
        :type word: str or list
        :param lines: The number of lines to display (default=25)
        :type lines: int
        :param width: The width of each line, in characters (default=80)
        :type width: int
        :param save: The option to save the concordance.
        :type save: bool
        """
        concordance_list = self.find_concordance(word, width=width)

        if not concordance_list:
            print("no matches")
        else:
            lines = min(lines, len(concordance_list))
            print(f"Displaying {lines} of {len(concordance_list)} matches:")
            for i, concordance_line in enumerate(concordance_list[:lines]):
                print(concordance_line.line)


class TokenSearcher:
    """
    A class that makes it easier to use regular expressions to search
    over tokenized strings.  The tokenized string is converted to a
    string where tokens are marked with angle brackets -- e.g.,
    ``'<the><window><is><still><open>'``.  The regular expression
    passed to the ``findall()`` method is modified to treat angle
    brackets as non-capturing parentheses, in addition to matching the
    token boundaries; and to have ``'.'`` not match the angle brackets.
    """

    def __init__(self, tokens):
        self._raw = "".join("<" + w + ">" for w in tokens)

    def findall(self, regexp):
        """
        Find instances of the regular expression in the text.
        The text is a list of tokens, and a regexp pattern to match
        a single token must be surrounded by angle brackets.  E.g.

        >>> from nltk.text import TokenSearcher
        >>> from nltk.book import text1, text5, text9
        >>> text5.findall("<.*><.*><bro>")
        you rule bro; telling you bro; u twizted bro
        >>> text1.findall("<a>(<.*>)<man>")
        monied; nervous; dangerous; white; white; white; pious; queer; good;
        mature; white; Cape; great; wise; wise; butterless; white; fiendish;
        pale; furious; better; certain; complete; dismasted; younger; brave;
        brave; brave; brave
        >>> text9.findall("<th.*>{3,}")
        thread through those; the thought that; that the thing; the thing
        that; that that thing; through these than through; them that the;
        through the thick; them that they; thought that the

        :param regexp: A regular expression
        :type regexp: str
        """
        # preprocess the regular expression
        regexp = re.sub(r"\s", "", regexp)
        regexp = re.sub(r"<", "(?:<(?:", regexp)
        regexp = re.sub(r">", ")>)", regexp)
        regexp = re.sub(r"(?<!\\)\.", "[^>]", regexp)

        # perform the search
        hits = re.findall(regexp, self._raw)

        # Sanity check
        for h in hits:
            if not h.startswith("<") and h.endswith(">"):
                raise ValueError("Bad regexp for TokenSearcher.findall")

        # postprocess the output
        hits = [h[1:-1].split("><") for h in hits]
        return hits


class Text:
    """
    A wrapper around a sequence of simple (string) tokens, which is
    intended to support initial exploration of texts (via the
    interactive console).  Its methods perform a variety of analyses
    on the text's contexts (e.g., counting, concordancing, collocation
    discovery), and display the results.  If you wish to write a
    program which makes use of these analyses, then you should bypass
    the ``Text`` class, and use the appropriate analysis function or
    class directly instead.

    A ``Text`` is typically initialized from a given document or
    corpus.  E.g.:

    >>> import nltk.corpus
    >>> from nltk.text import Text
    >>> moby = Text(nltk.corpus.gutenberg.words('melville-moby_dick.txt'))

    """

    # This defeats lazy loading, but makes things faster.  This
    # *shouldn't* be necessary because the corpus view *should* be
    # doing intelligent caching, but without this it's running slow.
    # Look into whether the caching is working correctly.
    _COPY_TOKENS = True

    def __init__(self, tokens, name=None):
        """
        Create a Text object.

        :param tokens: The source text.
        :type tokens: sequence of str
        """
        if self._COPY_TOKENS:
            tokens = list(tokens)
        self.tokens = tokens

        if name:
            self.name = name
        elif "]" in tokens[:20]:
            end = tokens[:20].index("]")
            self.name = " ".join(str(tok) for tok in tokens[1:end])
        else:
            self.name = " ".join(str(tok) for tok in tokens[:8]) + "..."

    # ////////////////////////////////////////////////////////////
    # Support item & slice access
    # ////////////////////////////////////////////////////////////

    def __getitem__(self, i):
        return self.tokens[i]

    def __len__(self):
        return len(self.tokens)

    # ////////////////////////////////////////////////////////////
    # Interactive console methods
    # ////////////////////////////////////////////////////////////

    def concordance(self, word, width=79, lines=25):
        """
        Prints a concordance for ``word`` with the specified context window.
        Word matching is not case-sensitive.

        :param word: The target word or phrase (a list of strings)
        :type word: str or list
        :param width: The width of each line, in characters (default=80)
        :type width: int
        :param lines: The number of lines to display (default=25)
        :type lines: int

        :seealso: ``ConcordanceIndex``
        """
        if "_concordance_index" not in self.__dict__:
            self._concordance_index = ConcordanceIndex(
                self.tokens, key=lambda s: s.lower()
            )

        return self._concordance_index.print_concordance(word, width, lines)

    def concordance_list(self, word, width=79, lines=25):
        """
        Generate a concordance for ``word`` with the specified context window.
        Word matching is not case-sensitive.

        :param word: The target word or phrase (a list of strings)
        :type word: str or list
        :param width: The width of each line, in characters (default=80)
        :type width: int
        :param lines: The number of lines to display (default=25)
        :type lines: int

        :seealso: ``ConcordanceIndex``
        """
        if "_concordance_index" not in self.__dict__:
            self._concordance_index = ConcordanceIndex(
                self.tokens, key=lambda s: s.lower()
            )
        return self._concordance_index.find_concordance(word, width)[:lines]

    def collocation_list(self, num=20, window_size=2):
        """
        Return collocations derived from the text, ignoring stopwords.

            >>> from nltk.book import text4
            >>> text4.collocation_list()[:2]
            [('United', 'States'), ('fellow', 'citizens')]

        :param num: The maximum number of collocations to return.
        :type num: int
        :param window_size: The number of tokens spanned by a collocation (default=2)
        :type window_size: int
        :rtype: list(tuple(str, str))
        """
        if not (
            "_collocations" in self.__dict__
            and self._num == num
            and self._window_size == window_size
        ):
            self._num = num
            self._window_size = window_size

            # print("Building collocations list")
            from nltk.corpus import stopwords

            ignored_words = stopwords.words("english")
            finder = BigramCollocationFinder.from_words(self.tokens, window_size)
            finder.apply_freq_filter(2)
            finder.apply_word_filter(lambda w: len(w) < 3 or w.lower() in ignored_words)
            bigram_measures = BigramAssocMeasures()
            self._collocations = list(
                finder.nbest(bigram_measures.likelihood_ratio, num)
            )
        return self._collocations

    def collocations(self, num=20, window_size=2):
        """
        Print collocations derived from the text, ignoring stopwords.

            >>> from nltk.book import text4
            >>> text4.collocations() # doctest: +NORMALIZE_WHITESPACE
            United States; fellow citizens; years ago; four years; Federal
            Government; General Government; American people; Vice President; God
            bless; Chief Justice; one another; fellow Americans; Old World;
            Almighty God; Fellow citizens; Chief Magistrate; every citizen; Indian
            tribes; public debt; foreign nations


        :param num: The maximum number of collocations to print.
        :type num: int
        :param window_size: The number of tokens spanned by a collocation (default=2)
        :type window_size: int
        """

        collocation_strings = [
            w1 + " " + w2 for w1, w2 in self.collocation_list(num, window_size)
        ]
        print(tokenwrap(collocation_strings, separator="; "))

    def count(self, word):
        """
        Count the number of times this word appears in the text.
        """
        return self.tokens.count(word)

    def index(self, word):
        """
        Find the index of the first occurrence of the word in the text.
        """
        return self.tokens.index(word)

    def readability(self, method):
        # code from nltk_contrib.readability
        raise NotImplementedError

    def similar(self, word, num=20):
        """
        Distributional similarity: find other words which appear in the
        same contexts as the specified word; list most similar words first.

        :param word: The word used to seed the similarity search
        :type word: str
        :param num: The number of words to generate (default=20)
        :type num: int
        :seealso: ContextIndex.similar_words()
        """
        if "_word_context_index" not in self.__dict__:
            # print('Building word-context index...')
            self._word_context_index = ContextIndex(
                self.tokens, filter=lambda x: x.isalpha(), key=lambda s: s.lower()
            )

        # words = self._word_context_index.similar_words(word, num)

        word = word.lower()
        wci = self._word_context_index._word_to_contexts
        if word in wci.conditions():
            contexts = set(wci[word])
            fd = Counter(
                w
                for w in wci.conditions()
                for c in wci[w]
                if c in contexts and not w == word
            )
            words = [w for w, _ in fd.most_common(num)]
            print(tokenwrap(words))
        else:
            print("No matches")

    def common_contexts(self, words, num=20):
        """
        Find contexts where the specified words appear; list
        most frequent common contexts first.

        :param words: The words used to seed the similarity search
        :type words: str
        :param num: The number of words to generate (default=20)
        :type num: int
        :seealso: ContextIndex.common_contexts()
        """
        if "_word_context_index" not in self.__dict__:
            # print('Building word-context index...')
            self._word_context_index = ContextIndex(
                self.tokens, key=lambda s: s.lower()
            )

        try:
            fd = self._word_context_index.common_contexts(words, True)
            if not fd:
                print("No common contexts were found")
            else:
                ranked_contexts = [w for w, _ in fd.most_common(num)]
                print(tokenwrap(w1 + "_" + w2 for w1, w2 in ranked_contexts))

        except ValueError as e:
            print(e)

    def dispersion_plot(self, words):
        """
        Produce a plot showing the distribution of the words through the text.
        Requires pylab to be installed.

        :param words: The words to be plotted
        :type words: list(str)
        :seealso: nltk.draw.dispersion_plot()
        """
        from nltk.draw import dispersion_plot

        dispersion_plot(self, words)

    def _train_default_ngram_lm(self, tokenized_sents, n=3):
        train_data, padded_sents = padded_everygram_pipeline(n, tokenized_sents)
        model = MLE(order=n)
        model.fit(train_data, padded_sents)
        return model

    def generate(self, length=100, text_seed=None, random_seed=42):
        """
        Print random text, generated using a trigram language model.
        See also `help(nltk.lm)`.

        :param length: The length of text to generate (default=100)
        :type length: int

        :param text_seed: Generation can be conditioned on preceding context.
        :type text_seed: list(str)

        :param random_seed: A random seed or an instance of `random.Random`. If provided,
            makes the random sampling part of generation reproducible. (default=42)
        :type random_seed: int
        """
        # Create the model when using it the first time.
        self._tokenized_sents = [
            sent.split(" ") for sent in sent_tokenize(" ".join(self.tokens))
        ]
        if not hasattr(self, "_trigram_model"):
            print("Building ngram index...", file=sys.stderr)
            self._trigram_model = self._train_default_ngram_lm(
                self._tokenized_sents, n=3
            )

        generated_tokens = []

        assert length > 0, "The `length` must be more than 0."
        while len(generated_tokens) < length:
            for idx, token in enumerate(
                self._trigram_model.generate(
                    length, text_seed=text_seed, random_seed=random_seed
                )
            ):
                if token == "<s>":
                    continue
                if token == "</s>":
                    break
                generated_tokens.append(token)
            random_seed += 1

        prefix = " ".join(text_seed) + " " if text_seed else ""
        output_str = prefix + tokenwrap(generated_tokens[:length])
        print(output_str)
        return output_str

    def plot(self, *args):
        """
        See documentation for FreqDist.plot()
        :seealso: nltk.prob.FreqDist.plot()
        """
        return self.vocab().plot(*args)

    def vocab(self):
        """
        :seealso: nltk.prob.FreqDist
        """
        if "_vocab" not in self.__dict__:
            # print("Building vocabulary index...")
            self._vocab = FreqDist(self)
        return self._vocab

    def findall(self, regexp):
        """
        Find instances of the regular expression in the text.
        The text is a list of tokens, and a regexp pattern to match
        a single token must be surrounded by angle brackets.  E.g.

        >>> from nltk.book import text1, text5, text9
        >>> text5.findall("<.*><.*><bro>")
        you rule bro; telling you bro; u twizted bro
        >>> text1.findall("<a>(<.*>)<man>")
        monied; nervous; dangerous; white; white; white; pious; queer; good;
        mature; white; Cape; great; wise; wise; butterless; white; fiendish;
        pale; furious; better; certain; complete; dismasted; younger; brave;
        brave; brave; brave
        >>> text9.findall("<th.*>{3,}")
        thread through those; the thought that; that the thing; the thing
        that; that that thing; through these than through; them that the;
        through the thick; them that they; thought that the

        :param regexp: A regular expression
        :type regexp: str
        """

        if "_token_searcher" not in self.__dict__:
            self._token_searcher = TokenSearcher(self)

        hits = self._token_searcher.findall(regexp)
        hits = [" ".join(h) for h in hits]
        print(tokenwrap(hits, "; "))

    # ////////////////////////////////////////////////////////////
    # Helper Methods
    # ////////////////////////////////////////////////////////////

    _CONTEXT_RE = re.compile(r"\w+|[\.\!\?]")

    def _context(self, tokens, i):
        """
        One left & one right token, both case-normalized.  Skip over
        non-sentence-final punctuation.  Used by the ``ContextIndex``
        that is created for ``similar()`` and ``common_contexts()``.
        """
        # Left context
        j = i - 1
        while j >= 0 and not self._CONTEXT_RE.match(tokens[j]):
            j -= 1
        left = tokens[j] if j != 0 else "*START*"

        # Right context
        j = i + 1
        while j < len(tokens) and not self._CONTEXT_RE.match(tokens[j]):
            j += 1
        right = tokens[j] if j != len(tokens) else "*END*"

        return (left, right)

    # ////////////////////////////////////////////////////////////
    # String Display
    # ////////////////////////////////////////////////////////////

    def __str__(self):
        return "<Text: %s>" % self.name

    def __repr__(self):
        return "<Text: %s>" % self.name


# Prototype only; this approach will be slow to load
class TextCollection(Text):
    """A collection of texts, which can be loaded with list of texts, or
    with a corpus consisting of one or more texts, and which supports
    counting, concordancing, collocation discovery, etc.  Initialize a
    TextCollection as follows:

    >>> import nltk.corpus
    >>> from nltk.text import TextCollection
    >>> from nltk.book import text1, text2, text3
    >>> gutenberg = TextCollection(nltk.corpus.gutenberg)
    >>> mytexts = TextCollection([text1, text2, text3])

    Iterating over a TextCollection produces all the tokens of all the
    texts in order.
    """

    def __init__(self, source):
        if hasattr(source, "words"):  # bridge to the text corpus reader
            source = [source.words(f) for f in source.fileids()]

        self._texts = source
        Text.__init__(self, LazyConcatenation(source))
        self._idf_cache = {}

    def tf(self, term, text):
        """The frequency of the term in text."""
        return text.count(term) / len(text)

    def idf(self, term):
        """The number of texts in the corpus divided by the
        number of texts that the term appears in.
        If a term does not appear in the corpus, 0.0 is returned."""
        # idf values are cached for performance.
        idf = self._idf_cache.get(term)
        if idf is None:
            matches = len([True for text in self._texts if term in text])
            if len(self._texts) == 0:
                raise ValueError("IDF undefined for empty document collection")
            idf = log(len(self._texts) / matches) if matches else 0.0
            self._idf_cache[term] = idf
        return idf

    def tf_idf(self, term, text):
        return self.tf(term, text) * self.idf(term)


def demo():
    from nltk.corpus import brown

    text = Text(brown.words(categories="news"))
    print(text)
    print()
    print("Concordance:")
    text.concordance("news")
    print()
    print("Distributionally similar words:")
    text.similar("news")
    print()
    print("Collocations:")
    text.collocations()
    print()
    # print("Automatically generated text:")
    # text.generate()
    # print()
    print("Dispersion plot:")
    text.dispersion_plot(["news", "report", "said", "announced"])
    print()
    print("Vocabulary plot:")
    text.plot(50)
    print()
    print("Indexing:")
    print("text[3]:", text[3])
    print("text[3:5]:", text[3:5])
    print("text.vocab()['news']:", text.vocab()["news"])


if __name__ == "__main__":
    demo()

__all__ = [
    "ContextIndex",
    "ConcordanceIndex",
    "TokenSearcher",
    "Text",
    "TextCollection",
]

# === NexusCore/openenv\Lib\site-packages\rich\markdown.py ===
from __future__ import annotations

import sys
from typing import ClassVar, Iterable

from markdown_it import MarkdownIt
from markdown_it.token import Token

if sys.version_info >= (3, 8):
    from typing import get_args
else:
    from typing_extensions import get_args  # pragma: no cover

from rich.table import Table

from . import box
from ._loop import loop_first
from ._stack import Stack
from .console import Console, ConsoleOptions, JustifyMethod, RenderResult
from .containers import Renderables
from .jupyter import JupyterMixin
from .panel import Panel
from .rule import Rule
from .segment import Segment
from .style import Style, StyleStack
from .syntax import Syntax
from .text import Text, TextType


class MarkdownElement:
    new_line: ClassVar[bool] = True

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> MarkdownElement:
        """Factory to create markdown element,

        Args:
            markdown (Markdown): The parent Markdown object.
            token (Token): A node from markdown-it.

        Returns:
            MarkdownElement: A new markdown element
        """
        return cls()

    def on_enter(self, context: MarkdownContext) -> None:
        """Called when the node is entered.

        Args:
            context (MarkdownContext): The markdown context.
        """

    def on_text(self, context: MarkdownContext, text: TextType) -> None:
        """Called when text is parsed.

        Args:
            context (MarkdownContext): The markdown context.
        """

    def on_leave(self, context: MarkdownContext) -> None:
        """Called when the parser leaves the element.

        Args:
            context (MarkdownContext): [description]
        """

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        """Called when a child element is closed.

        This method allows a parent element to take over rendering of its children.

        Args:
            context (MarkdownContext): The markdown context.
            child (MarkdownElement): The child markdown element.

        Returns:
            bool: Return True to render the element, or False to not render the element.
        """
        return True

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        return ()


class UnknownElement(MarkdownElement):
    """An unknown element.

    Hopefully there will be no unknown elements, and we will have a MarkdownElement for
    everything in the document.

    """


class TextElement(MarkdownElement):
    """Base class for elements that render text."""

    style_name = "none"

    def on_enter(self, context: MarkdownContext) -> None:
        self.style = context.enter_style(self.style_name)
        self.text = Text(justify="left")

    def on_text(self, context: MarkdownContext, text: TextType) -> None:
        self.text.append(text, context.current_style if isinstance(text, str) else None)

    def on_leave(self, context: MarkdownContext) -> None:
        context.leave_style()


class Paragraph(TextElement):
    """A Paragraph."""

    style_name = "markdown.paragraph"
    justify: JustifyMethod

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> Paragraph:
        return cls(justify=markdown.justify or "left")

    def __init__(self, justify: JustifyMethod) -> None:
        self.justify = justify

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        self.text.justify = self.justify
        yield self.text


class Heading(TextElement):
    """A heading."""

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> Heading:
        return cls(token.tag)

    def on_enter(self, context: MarkdownContext) -> None:
        self.text = Text()
        context.enter_style(self.style_name)

    def __init__(self, tag: str) -> None:
        self.tag = tag
        self.style_name = f"markdown.{tag}"
        super().__init__()

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        text = self.text
        text.justify = "center"
        if self.tag == "h1":
            # Draw a border around h1s
            yield Panel(
                text,
                box=box.HEAVY,
                style="markdown.h1.border",
            )
        else:
            # Styled text for h2 and beyond
            if self.tag == "h2":
                yield Text("")
            yield text


class CodeBlock(TextElement):
    """A code block with syntax highlighting."""

    style_name = "markdown.code_block"

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> CodeBlock:
        node_info = token.info or ""
        lexer_name = node_info.partition(" ")[0]
        return cls(lexer_name or "text", markdown.code_theme)

    def __init__(self, lexer_name: str, theme: str) -> None:
        self.lexer_name = lexer_name
        self.theme = theme

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        code = str(self.text).rstrip()
        syntax = Syntax(
            code, self.lexer_name, theme=self.theme, word_wrap=True, padding=1
        )
        yield syntax


class BlockQuote(TextElement):
    """A block quote."""

    style_name = "markdown.block_quote"

    def __init__(self) -> None:
        self.elements: Renderables = Renderables()

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        self.elements.append(child)
        return False

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        render_options = options.update(width=options.max_width - 4)
        lines = console.render_lines(self.elements, render_options, style=self.style)
        style = self.style
        new_line = Segment("\n")
        padding = Segment("▌ ", style)
        for line in lines:
            yield padding
            yield from line
            yield new_line


class HorizontalRule(MarkdownElement):
    """A horizontal rule to divide sections."""

    new_line = False

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        style = console.get_style("markdown.hr", default="none")
        yield Rule(style=style)


class TableElement(MarkdownElement):
    """MarkdownElement corresponding to `table_open`."""

    def __init__(self) -> None:
        self.header: TableHeaderElement | None = None
        self.body: TableBodyElement | None = None

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        if isinstance(child, TableHeaderElement):
            self.header = child
        elif isinstance(child, TableBodyElement):
            self.body = child
        else:
            raise RuntimeError("Couldn't process markdown table.")
        return False

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        table = Table(box=box.SIMPLE_HEAVY)

        if self.header is not None and self.header.row is not None:
            for column in self.header.row.cells:
                table.add_column(column.content)

        if self.body is not None:
            for row in self.body.rows:
                row_content = [element.content for element in row.cells]
                table.add_row(*row_content)

        yield table


class TableHeaderElement(MarkdownElement):
    """MarkdownElement corresponding to `thead_open` and `thead_close`."""

    def __init__(self) -> None:
        self.row: TableRowElement | None = None

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        assert isinstance(child, TableRowElement)
        self.row = child
        return False


class TableBodyElement(MarkdownElement):
    """MarkdownElement corresponding to `tbody_open` and `tbody_close`."""

    def __init__(self) -> None:
        self.rows: list[TableRowElement] = []

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        assert isinstance(child, TableRowElement)
        self.rows.append(child)
        return False


class TableRowElement(MarkdownElement):
    """MarkdownElement corresponding to `tr_open` and `tr_close`."""

    def __init__(self) -> None:
        self.cells: list[TableDataElement] = []

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        assert isinstance(child, TableDataElement)
        self.cells.append(child)
        return False


class TableDataElement(MarkdownElement):
    """MarkdownElement corresponding to `td_open` and `td_close`
    and `th_open` and `th_close`."""

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> MarkdownElement:
        style = str(token.attrs.get("style")) or ""

        justify: JustifyMethod
        if "text-align:right" in style:
            justify = "right"
        elif "text-align:center" in style:
            justify = "center"
        elif "text-align:left" in style:
            justify = "left"
        else:
            justify = "default"

        assert justify in get_args(JustifyMethod)
        return cls(justify=justify)

    def __init__(self, justify: JustifyMethod) -> None:
        self.content: Text = Text("", justify=justify)
        self.justify = justify

    def on_text(self, context: MarkdownContext, text: TextType) -> None:
        text = Text(text) if isinstance(text, str) else text
        text.stylize(context.current_style)
        self.content.append_text(text)


class ListElement(MarkdownElement):
    """A list element."""

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> ListElement:
        return cls(token.type, int(token.attrs.get("start", 1)))

    def __init__(self, list_type: str, list_start: int | None) -> None:
        self.items: list[ListItem] = []
        self.list_type = list_type
        self.list_start = list_start

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        assert isinstance(child, ListItem)
        self.items.append(child)
        return False

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        if self.list_type == "bullet_list_open":
            for item in self.items:
                yield from item.render_bullet(console, options)
        else:
            number = 1 if self.list_start is None else self.list_start
            last_number = number + len(self.items)
            for index, item in enumerate(self.items):
                yield from item.render_number(
                    console, options, number + index, last_number
                )


class ListItem(TextElement):
    """An item in a list."""

    style_name = "markdown.item"

    def __init__(self) -> None:
        self.elements: Renderables = Renderables()

    def on_child_close(self, context: MarkdownContext, child: MarkdownElement) -> bool:
        self.elements.append(child)
        return False

    def render_bullet(self, console: Console, options: ConsoleOptions) -> RenderResult:
        render_options = options.update(width=options.max_width - 3)
        lines = console.render_lines(self.elements, render_options, style=self.style)
        bullet_style = console.get_style("markdown.item.bullet", default="none")

        bullet = Segment(" • ", bullet_style)
        padding = Segment(" " * 3, bullet_style)
        new_line = Segment("\n")
        for first, line in loop_first(lines):
            yield bullet if first else padding
            yield from line
            yield new_line

    def render_number(
        self, console: Console, options: ConsoleOptions, number: int, last_number: int
    ) -> RenderResult:
        number_width = len(str(last_number)) + 2
        render_options = options.update(width=options.max_width - number_width)
        lines = console.render_lines(self.elements, render_options, style=self.style)
        number_style = console.get_style("markdown.item.number", default="none")

        new_line = Segment("\n")
        padding = Segment(" " * number_width, number_style)
        numeral = Segment(f"{number}".rjust(number_width - 1) + " ", number_style)
        for first, line in loop_first(lines):
            yield numeral if first else padding
            yield from line
            yield new_line


class Link(TextElement):
    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> MarkdownElement:
        url = token.attrs.get("href", "#")
        return cls(token.content, str(url))

    def __init__(self, text: str, href: str):
        self.text = Text(text)
        self.href = href


class ImageItem(TextElement):
    """Renders a placeholder for an image."""

    new_line = False

    @classmethod
    def create(cls, markdown: Markdown, token: Token) -> MarkdownElement:
        """Factory to create markdown element,

        Args:
            markdown (Markdown): The parent Markdown object.
            token (Any): A token from markdown-it.

        Returns:
            MarkdownElement: A new markdown element
        """
        return cls(str(token.attrs.get("src", "")), markdown.hyperlinks)

    def __init__(self, destination: str, hyperlinks: bool) -> None:
        self.destination = destination
        self.hyperlinks = hyperlinks
        self.link: str | None = None
        super().__init__()

    def on_enter(self, context: MarkdownContext) -> None:
        self.link = context.current_style.link
        self.text = Text(justify="left")
        super().on_enter(context)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        link_style = Style(link=self.link or self.destination or None)
        title = self.text or Text(self.destination.strip("/").rsplit("/", 1)[-1])
        if self.hyperlinks:
            title.stylize(link_style)
        text = Text.assemble("🌆 ", title, " ", end="")
        yield text


class MarkdownContext:
    """Manages the console render state."""

    def __init__(
        self,
        console: Console,
        options: ConsoleOptions,
        style: Style,
        inline_code_lexer: str | None = None,
        inline_code_theme: str = "monokai",
    ) -> None:
        self.console = console
        self.options = options
        self.style_stack: StyleStack = StyleStack(style)
        self.stack: Stack[MarkdownElement] = Stack()

        self._syntax: Syntax | None = None
        if inline_code_lexer is not None:
            self._syntax = Syntax("", inline_code_lexer, theme=inline_code_theme)

    @property
    def current_style(self) -> Style:
        """Current style which is the product of all styles on the stack."""
        return self.style_stack.current

    def on_text(self, text: str, node_type: str) -> None:
        """Called when the parser visits text."""
        if node_type in {"fence", "code_inline"} and self._syntax is not None:
            highlight_text = self._syntax.highlight(text)
            highlight_text.rstrip()
            self.stack.top.on_text(
                self, Text.assemble(highlight_text, style=self.style_stack.current)
            )
        else:
            self.stack.top.on_text(self, text)

    def enter_style(self, style_name: str | Style) -> Style:
        """Enter a style context."""
        style = self.console.get_style(style_name, default="none")
        self.style_stack.push(style)
        return self.current_style

    def leave_style(self) -> Style:
        """Leave a style context."""
        style = self.style_stack.pop()
        return style


class Markdown(JupyterMixin):
    """A Markdown renderable.

    Args:
        markup (str): A string containing markdown.
        code_theme (str, optional): Pygments theme for code blocks. Defaults to "monokai". See https://pygments.org/styles/ for code themes.
        justify (JustifyMethod, optional): Justify value for paragraphs. Defaults to None.
        style (Union[str, Style], optional): Optional style to apply to markdown.
        hyperlinks (bool, optional): Enable hyperlinks. Defaults to ``True``.
        inline_code_lexer: (str, optional): Lexer to use if inline code highlighting is
            enabled. Defaults to None.
        inline_code_theme: (Optional[str], optional): Pygments theme for inline code
            highlighting, or None for no highlighting. Defaults to None.
    """

    elements: ClassVar[dict[str, type[MarkdownElement]]] = {
        "paragraph_open": Paragraph,
        "heading_open": Heading,
        "fence": CodeBlock,
        "code_block": CodeBlock,
        "blockquote_open": BlockQuote,
        "hr": HorizontalRule,
        "bullet_list_open": ListElement,
        "ordered_list_open": ListElement,
        "list_item_open": ListItem,
        "image": ImageItem,
        "table_open": TableElement,
        "tbody_open": TableBodyElement,
        "thead_open": TableHeaderElement,
        "tr_open": TableRowElement,
        "td_open": TableDataElement,
        "th_open": TableDataElement,
    }

    inlines = {"em", "strong", "code", "s"}

    def __init__(
        self,
        markup: str,
        code_theme: str = "monokai",
        justify: JustifyMethod | None = None,
        style: str | Style = "none",
        hyperlinks: bool = True,
        inline_code_lexer: str | None = None,
        inline_code_theme: str | None = None,
    ) -> None:
        parser = MarkdownIt().enable("strikethrough").enable("table")
        self.markup = markup
        self.parsed = parser.parse(markup)
        self.code_theme = code_theme
        self.justify: JustifyMethod | None = justify
        self.style = style
        self.hyperlinks = hyperlinks
        self.inline_code_lexer = inline_code_lexer
        self.inline_code_theme = inline_code_theme or code_theme

    def _flatten_tokens(self, tokens: Iterable[Token]) -> Iterable[Token]:
        """Flattens the token stream."""
        for token in tokens:
            is_fence = token.type == "fence"
            is_image = token.tag == "img"
            if token.children and not (is_image or is_fence):
                yield from self._flatten_tokens(token.children)
            else:
                yield token

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render markdown to the console."""
        style = console.get_style(self.style, default="none")
        options = options.update(height=None)
        context = MarkdownContext(
            console,
            options,
            style,
            inline_code_lexer=self.inline_code_lexer,
            inline_code_theme=self.inline_code_theme,
        )
        tokens = self.parsed
        inline_style_tags = self.inlines
        new_line = False
        _new_line_segment = Segment.line()

        for token in self._flatten_tokens(tokens):
            node_type = token.type
            tag = token.tag

            entering = token.nesting == 1
            exiting = token.nesting == -1
            self_closing = token.nesting == 0

            if node_type == "text":
                context.on_text(token.content, node_type)
            elif node_type == "hardbreak":
                context.on_text("\n", node_type)
            elif node_type == "softbreak":
                context.on_text(" ", node_type)
            elif node_type == "link_open":
                href = str(token.attrs.get("href", ""))
                if self.hyperlinks:
                    link_style = console.get_style("markdown.link_url", default="none")
                    link_style += Style(link=href)
                    context.enter_style(link_style)
                else:
                    context.stack.push(Link.create(self, token))
            elif node_type == "link_close":
                if self.hyperlinks:
                    context.leave_style()
                else:
                    element = context.stack.pop()
                    assert isinstance(element, Link)
                    link_style = console.get_style("markdown.link", default="none")
                    context.enter_style(link_style)
                    context.on_text(element.text.plain, node_type)
                    context.leave_style()
                    context.on_text(" (", node_type)
                    link_url_style = console.get_style(
                        "markdown.link_url", default="none"
                    )
                    context.enter_style(link_url_style)
                    context.on_text(element.href, node_type)
                    context.leave_style()
                    context.on_text(")", node_type)
            elif (
                tag in inline_style_tags
                and node_type != "fence"
                and node_type != "code_block"
            ):
                if entering:
                    # If it's an opening inline token e.g. strong, em, etc.
                    # Then we move into a style context i.e. push to stack.
                    context.enter_style(f"markdown.{tag}")
                elif exiting:
                    # If it's a closing inline style, then we pop the style
                    # off of the stack, to move out of the context of it...
                    context.leave_style()
                else:
                    # If it's a self-closing inline style e.g. `code_inline`
                    context.enter_style(f"markdown.{tag}")
                    if token.content:
                        context.on_text(token.content, node_type)
                    context.leave_style()
            else:
                # Map the markdown tag -> MarkdownElement renderable
                element_class = self.elements.get(token.type) or UnknownElement
                element = element_class.create(self, token)

                if entering or self_closing:
                    context.stack.push(element)
                    element.on_enter(context)

                if exiting:  # CLOSING tag
                    element = context.stack.pop()

                    should_render = not context.stack or (
                        context.stack
                        and context.stack.top.on_child_close(context, element)
                    )

                    if should_render:
                        if new_line:
                            yield _new_line_segment

                        yield from console.render(element, context.options)
                elif self_closing:  # SELF-CLOSING tags (e.g. text, code, image)
                    context.stack.pop()
                    text = token.content
                    if text is not None:
                        element.on_text(context, text)

                    should_render = (
                        not context.stack
                        or context.stack
                        and context.stack.top.on_child_close(context, element)
                    )
                    if should_render:
                        if new_line and node_type != "inline":
                            yield _new_line_segment
                        yield from console.render(element, context.options)

                if exiting or self_closing:
                    element.on_leave(context)
                    new_line = element.new_line


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Render Markdown to the console with Rich"
    )
    parser.add_argument(
        "path",
        metavar="PATH",
        help="path to markdown file, or - for stdin",
    )
    parser.add_argument(
        "-c",
        "--force-color",
        dest="force_color",
        action="store_true",
        default=None,
        help="force color for non-terminals",
    )
    parser.add_argument(
        "-t",
        "--code-theme",
        dest="code_theme",
        default="monokai",
        help="pygments code theme",
    )
    parser.add_argument(
        "-i",
        "--inline-code-lexer",
        dest="inline_code_lexer",
        default=None,
        help="inline_code_lexer",
    )
    parser.add_argument(
        "-y",
        "--hyperlinks",
        dest="hyperlinks",
        action="store_true",
        help="enable hyperlinks",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        dest="width",
        default=None,
        help="width of output (default will auto-detect)",
    )
    parser.add_argument(
        "-j",
        "--justify",
        dest="justify",
        action="store_true",
        help="enable full text justify",
    )
    parser.add_argument(
        "-p",
        "--page",
        dest="page",
        action="store_true",
        help="use pager to scroll output",
    )
    args = parser.parse_args()

    from rich.console import Console

    if args.path == "-":
        markdown_body = sys.stdin.read()
    else:
        with open(args.path, encoding="utf-8") as markdown_file:
            markdown_body = markdown_file.read()

    markdown = Markdown(
        markdown_body,
        justify="full" if args.justify else "left",
        code_theme=args.code_theme,
        hyperlinks=args.hyperlinks,
        inline_code_lexer=args.inline_code_lexer,
    )
    if args.page:
        import io
        import pydoc

        fileio = io.StringIO()
        console = Console(
            file=fileio, force_terminal=args.force_color, width=args.width
        )
        console.print(markdown)
        pydoc.pager(fileio.getvalue())

    else:
        console = Console(
            force_terminal=args.force_color, width=args.width, record=True
        )
        console.print(markdown)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\commands\install.py ===
import errno
import json
import operator
import os
import shutil
import site
from optparse import SUPPRESS_HELP, Values
from typing import List, Optional

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.rich import print_json

# Eagerly import self_outdated_check to avoid crashes. Otherwise,
# this module would be imported *after* pip was replaced, resulting
# in crashes if the new self_outdated_check module was incompatible
# with the rest of pip that's already imported, or allowing a
# wheel to execute arbitrary code on install by replacing
# self_outdated_check.
import pip._internal.self_outdated_check  # noqa: F401
from pip._internal.cache import WheelCache
from pip._internal.cli import cmdoptions
from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.cli.req_command import (
    RequirementCommand,
    with_cleanup,
)
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.exceptions import CommandError, InstallationError
from pip._internal.locations import get_scheme
from pip._internal.metadata import get_environment
from pip._internal.models.installation_report import InstallationReport
from pip._internal.operations.build.build_tracker import get_build_tracker
from pip._internal.operations.check import ConflictDetails, check_install_conflicts
from pip._internal.req import install_given_reqs
from pip._internal.req.req_install import (
    InstallRequirement,
    check_legacy_setup_py_options,
)
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.filesystem import test_writable_dir
from pip._internal.utils.logging import getLogger
from pip._internal.utils.misc import (
    check_externally_managed,
    ensure_dir,
    get_pip_version,
    protect_pip_from_modification_on_windows,
    warn_if_run_as_root,
    write_output,
)
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.virtualenv import (
    running_under_virtualenv,
    virtualenv_no_global,
)
from pip._internal.wheel_builder import build, should_build_for_install_command

logger = getLogger(__name__)


class InstallCommand(RequirementCommand):
    """
    Install packages from:

    - PyPI (and other indexes) using requirement specifiers.
    - VCS project urls.
    - Local project directories.
    - Local or remote source archives.

    pip also supports installing from "requirements files", which provide
    an easy way to specify a whole environment to be installed.
    """

    usage = """
      %prog [options] <requirement specifier> [package-index-options] ...
      %prog [options] -r <requirements file> [package-index-options] ...
      %prog [options] [-e] <vcs project url> ...
      %prog [options] [-e] <local project path> ...
      %prog [options] <archive url/path> ..."""

    def add_options(self) -> None:
        self.cmd_opts.add_option(cmdoptions.requirements())
        self.cmd_opts.add_option(cmdoptions.constraints())
        self.cmd_opts.add_option(cmdoptions.no_deps())
        self.cmd_opts.add_option(cmdoptions.pre())

        self.cmd_opts.add_option(cmdoptions.editable())
        self.cmd_opts.add_option(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help=(
                "Don't actually install anything, just print what would be. "
                "Can be used in combination with --ignore-installed "
                "to 'resolve' the requirements."
            ),
        )
        self.cmd_opts.add_option(
            "-t",
            "--target",
            dest="target_dir",
            metavar="dir",
            default=None,
            help=(
                "Install packages into <dir>. "
                "By default this will not replace existing files/folders in "
                "<dir>. Use --upgrade to replace existing packages in <dir> "
                "with new versions."
            ),
        )
        cmdoptions.add_target_python_options(self.cmd_opts)

        self.cmd_opts.add_option(
            "--user",
            dest="use_user_site",
            action="store_true",
            help=(
                "Install to the Python user install directory for your "
                "platform. Typically ~/.local/, or %APPDATA%\\Python on "
                "Windows. (See the Python documentation for site.USER_BASE "
                "for full details.)"
            ),
        )
        self.cmd_opts.add_option(
            "--no-user",
            dest="use_user_site",
            action="store_false",
            help=SUPPRESS_HELP,
        )
        self.cmd_opts.add_option(
            "--root",
            dest="root_path",
            metavar="dir",
            default=None,
            help="Install everything relative to this alternate root directory.",
        )
        self.cmd_opts.add_option(
            "--prefix",
            dest="prefix_path",
            metavar="dir",
            default=None,
            help=(
                "Installation prefix where lib, bin and other top-level "
                "folders are placed. Note that the resulting installation may "
                "contain scripts and other resources which reference the "
                "Python interpreter of pip, and not that of ``--prefix``. "
                "See also the ``--python`` option if the intention is to "
                "install packages into another (possibly pip-free) "
                "environment."
            ),
        )

        self.cmd_opts.add_option(cmdoptions.src())

        self.cmd_opts.add_option(
            "-U",
            "--upgrade",
            dest="upgrade",
            action="store_true",
            help=(
                "Upgrade all specified packages to the newest available "
                "version. The handling of dependencies depends on the "
                "upgrade-strategy used."
            ),
        )

        self.cmd_opts.add_option(
            "--upgrade-strategy",
            dest="upgrade_strategy",
            default="only-if-needed",
            choices=["only-if-needed", "eager"],
            help=(
                "Determines how dependency upgrading should be handled "
                "[default: %default]. "
                '"eager" - dependencies are upgraded regardless of '
                "whether the currently installed version satisfies the "
                "requirements of the upgraded package(s). "
                '"only-if-needed" -  are upgraded only when they do not '
                "satisfy the requirements of the upgraded package(s)."
            ),
        )

        self.cmd_opts.add_option(
            "--force-reinstall",
            dest="force_reinstall",
            action="store_true",
            help="Reinstall all packages even if they are already up-to-date.",
        )

        self.cmd_opts.add_option(
            "-I",
            "--ignore-installed",
            dest="ignore_installed",
            action="store_true",
            help=(
                "Ignore the installed packages, overwriting them. "
                "This can break your system if the existing package "
                "is of a different version or was installed "
                "with a different package manager!"
            ),
        )

        self.cmd_opts.add_option(cmdoptions.ignore_requires_python())
        self.cmd_opts.add_option(cmdoptions.no_build_isolation())
        self.cmd_opts.add_option(cmdoptions.use_pep517())
        self.cmd_opts.add_option(cmdoptions.no_use_pep517())
        self.cmd_opts.add_option(cmdoptions.check_build_deps())
        self.cmd_opts.add_option(cmdoptions.override_externally_managed())

        self.cmd_opts.add_option(cmdoptions.config_settings())
        self.cmd_opts.add_option(cmdoptions.global_options())

        self.cmd_opts.add_option(
            "--compile",
            action="store_true",
            dest="compile",
            default=True,
            help="Compile Python source files to bytecode",
        )

        self.cmd_opts.add_option(
            "--no-compile",
            action="store_false",
            dest="compile",
            help="Do not compile Python source files to bytecode",
        )

        self.cmd_opts.add_option(
            "--no-warn-script-location",
            action="store_false",
            dest="warn_script_location",
            default=True,
            help="Do not warn when installing scripts outside PATH",
        )
        self.cmd_opts.add_option(
            "--no-warn-conflicts",
            action="store_false",
            dest="warn_about_conflicts",
            default=True,
            help="Do not warn about broken dependencies",
        )
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())
        self.cmd_opts.add_option(cmdoptions.prefer_binary())
        self.cmd_opts.add_option(cmdoptions.require_hashes())
        self.cmd_opts.add_option(cmdoptions.progress_bar())
        self.cmd_opts.add_option(cmdoptions.root_user_action())

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, self.cmd_opts)

        self.cmd_opts.add_option(
            "--report",
            dest="json_report_file",
            metavar="file",
            default=None,
            help=(
                "Generate a JSON file describing what pip did to install "
                "the provided requirements. "
                "Can be used in combination with --dry-run and --ignore-installed "
                "to 'resolve' the requirements. "
                "When - is used as file name it writes to stdout. "
                "When writing to stdout, please combine with the --quiet option "
                "to avoid mixing pip logging output with JSON output."
            ),
        )

    @with_cleanup
    def run(self, options: Values, args: List[str]) -> int:
        if options.use_user_site and options.target_dir is not None:
            raise CommandError("Can not combine '--user' and '--target'")

        # Check whether the environment we're installing into is externally
        # managed, as specified in PEP 668. Specifying --root, --target, or
        # --prefix disables the check, since there's no reliable way to locate
        # the EXTERNALLY-MANAGED file for those cases. An exception is also
        # made specifically for "--dry-run --report" for convenience.
        installing_into_current_environment = (
            not (options.dry_run and options.json_report_file)
            and options.root_path is None
            and options.target_dir is None
            and options.prefix_path is None
        )
        if (
            installing_into_current_environment
            and not options.override_externally_managed
        ):
            check_externally_managed()

        upgrade_strategy = "to-satisfy-only"
        if options.upgrade:
            upgrade_strategy = options.upgrade_strategy

        cmdoptions.check_dist_restriction(options, check_target=True)

        logger.verbose("Using %s", get_pip_version())
        options.use_user_site = decide_user_install(
            options.use_user_site,
            prefix_path=options.prefix_path,
            target_dir=options.target_dir,
            root_path=options.root_path,
            isolated_mode=options.isolated_mode,
        )

        target_temp_dir: Optional[TempDirectory] = None
        target_temp_dir_path: Optional[str] = None
        if options.target_dir:
            options.ignore_installed = True
            options.target_dir = os.path.abspath(options.target_dir)
            if (
                # fmt: off
                os.path.exists(options.target_dir) and
                not os.path.isdir(options.target_dir)
                # fmt: on
            ):
                raise CommandError(
                    "Target path exists but is not a directory, will not continue."
                )

            # Create a target directory for using with the target option
            target_temp_dir = TempDirectory(kind="target")
            target_temp_dir_path = target_temp_dir.path
            self.enter_context(target_temp_dir)

        global_options = options.global_options or []

        session = self.get_default_session(options)

        target_python = make_target_python(options)
        finder = self._build_package_finder(
            options=options,
            session=session,
            target_python=target_python,
            ignore_requires_python=options.ignore_requires_python,
        )
        build_tracker = self.enter_context(get_build_tracker())

        directory = TempDirectory(
            delete=not options.no_clean,
            kind="install",
            globally_managed=True,
        )

        try:
            reqs = self.get_requirements(args, options, finder, session)
            check_legacy_setup_py_options(options, reqs)

            wheel_cache = WheelCache(options.cache_dir)

            # Only when installing is it permitted to use PEP 660.
            # In other circumstances (pip wheel, pip download) we generate
            # regular (i.e. non editable) metadata and wheels.
            for req in reqs:
                req.permit_editable_wheels = True

            preparer = self.make_requirement_preparer(
                temp_build_dir=directory,
                options=options,
                build_tracker=build_tracker,
                session=session,
                finder=finder,
                use_user_site=options.use_user_site,
                verbosity=self.verbosity,
            )
            resolver = self.make_resolver(
                preparer=preparer,
                finder=finder,
                options=options,
                wheel_cache=wheel_cache,
                use_user_site=options.use_user_site,
                ignore_installed=options.ignore_installed,
                ignore_requires_python=options.ignore_requires_python,
                force_reinstall=options.force_reinstall,
                upgrade_strategy=upgrade_strategy,
                use_pep517=options.use_pep517,
                py_version_info=options.python_version,
            )

            self.trace_basic_info(finder)

            requirement_set = resolver.resolve(
                reqs, check_supported_wheels=not options.target_dir
            )

            if options.json_report_file:
                report = InstallationReport(requirement_set.requirements_to_install)
                if options.json_report_file == "-":
                    print_json(data=report.to_dict())
                else:
                    with open(options.json_report_file, "w", encoding="utf-8") as f:
                        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

            if options.dry_run:
                would_install_items = sorted(
                    (r.metadata["name"], r.metadata["version"])
                    for r in requirement_set.requirements_to_install
                )
                if would_install_items:
                    write_output(
                        "Would install %s",
                        " ".join("-".join(item) for item in would_install_items),
                    )
                return SUCCESS

            try:
                pip_req = requirement_set.get_requirement("pip")
            except KeyError:
                modifying_pip = False
            else:
                # If we're not replacing an already installed pip,
                # we're not modifying it.
                modifying_pip = pip_req.satisfied_by is None
            protect_pip_from_modification_on_windows(modifying_pip=modifying_pip)

            reqs_to_build = [
                r
                for r in requirement_set.requirements.values()
                if should_build_for_install_command(r)
            ]

            _, build_failures = build(
                reqs_to_build,
                wheel_cache=wheel_cache,
                verify=True,
                build_options=[],
                global_options=global_options,
            )

            if build_failures:
                raise InstallationError(
                    "Failed to build installable wheels for some "
                    "pyproject.toml based projects ({})".format(
                        ", ".join(r.name for r in build_failures)  # type: ignore
                    )
                )

            to_install = resolver.get_installation_order(requirement_set)

            # Check for conflicts in the package set we're installing.
            conflicts: Optional[ConflictDetails] = None
            should_warn_about_conflicts = (
                not options.ignore_dependencies and options.warn_about_conflicts
            )
            if should_warn_about_conflicts:
                conflicts = self._determine_conflicts(to_install)

            # Don't warn about script install locations if
            # --target or --prefix has been specified
            warn_script_location = options.warn_script_location
            if options.target_dir or options.prefix_path:
                warn_script_location = False

            installed = install_given_reqs(
                to_install,
                global_options,
                root=options.root_path,
                home=target_temp_dir_path,
                prefix=options.prefix_path,
                warn_script_location=warn_script_location,
                use_user_site=options.use_user_site,
                pycompile=options.compile,
            )

            lib_locations = get_lib_location_guesses(
                user=options.use_user_site,
                home=target_temp_dir_path,
                root=options.root_path,
                prefix=options.prefix_path,
                isolated=options.isolated_mode,
            )
            env = get_environment(lib_locations)

            # Display a summary of installed packages, with extra care to
            # display a package name as it was requested by the user.
            installed.sort(key=operator.attrgetter("name"))
            summary = []
            installed_versions = {}
            for distribution in env.iter_all_distributions():
                installed_versions[distribution.canonical_name] = distribution.version
            for package in installed:
                display_name = package.name
                version = installed_versions.get(canonicalize_name(display_name), None)
                if version:
                    text = f"{display_name}-{version}"
                else:
                    text = display_name
                summary.append(text)

            if conflicts is not None:
                self._warn_about_conflicts(
                    conflicts,
                    resolver_variant=self.determine_resolver_variant(options),
                )

            installed_desc = " ".join(summary)
            if installed_desc:
                write_output(
                    "Successfully installed %s",
                    installed_desc,
                )
        except OSError as error:
            show_traceback = self.verbosity >= 1

            message = create_os_error_message(
                error,
                show_traceback,
                options.use_user_site,
            )
            logger.error(message, exc_info=show_traceback)

            return ERROR

        if options.target_dir:
            assert target_temp_dir
            self._handle_target_dir(
                options.target_dir, target_temp_dir, options.upgrade
            )
        if options.root_user_action == "warn":
            warn_if_run_as_root()
        return SUCCESS

    def _handle_target_dir(
        self, target_dir: str, target_temp_dir: TempDirectory, upgrade: bool
    ) -> None:
        ensure_dir(target_dir)

        # Checking both purelib and platlib directories for installed
        # packages to be moved to target directory
        lib_dir_list = []

        # Checking both purelib and platlib directories for installed
        # packages to be moved to target directory
        scheme = get_scheme("", home=target_temp_dir.path)
        purelib_dir = scheme.purelib
        platlib_dir = scheme.platlib
        data_dir = scheme.data

        if os.path.exists(purelib_dir):
            lib_dir_list.append(purelib_dir)
        if os.path.exists(platlib_dir) and platlib_dir != purelib_dir:
            lib_dir_list.append(platlib_dir)
        if os.path.exists(data_dir):
            lib_dir_list.append(data_dir)

        for lib_dir in lib_dir_list:
            for item in os.listdir(lib_dir):
                if lib_dir == data_dir:
                    ddir = os.path.join(data_dir, item)
                    if any(s.startswith(ddir) for s in lib_dir_list[:-1]):
                        continue
                target_item_dir = os.path.join(target_dir, item)
                if os.path.exists(target_item_dir):
                    if not upgrade:
                        logger.warning(
                            "Target directory %s already exists. Specify "
                            "--upgrade to force replacement.",
                            target_item_dir,
                        )
                        continue
                    if os.path.islink(target_item_dir):
                        logger.warning(
                            "Target directory %s already exists and is "
                            "a link. pip will not automatically replace "
                            "links, please remove if replacement is "
                            "desired.",
                            target_item_dir,
                        )
                        continue
                    if os.path.isdir(target_item_dir):
                        shutil.rmtree(target_item_dir)
                    else:
                        os.remove(target_item_dir)

                shutil.move(os.path.join(lib_dir, item), target_item_dir)

    def _determine_conflicts(
        self, to_install: List[InstallRequirement]
    ) -> Optional[ConflictDetails]:
        try:
            return check_install_conflicts(to_install)
        except Exception:
            logger.exception(
                "Error while checking for conflicts. Please file an issue on "
                "pip's issue tracker: https://github.com/pypa/pip/issues/new"
            )
            return None

    def _warn_about_conflicts(
        self, conflict_details: ConflictDetails, resolver_variant: str
    ) -> None:
        package_set, (missing, conflicting) = conflict_details
        if not missing and not conflicting:
            return

        parts: List[str] = []
        if resolver_variant == "legacy":
            parts.append(
                "pip's legacy dependency resolver does not consider dependency "
                "conflicts when selecting packages. This behaviour is the "
                "source of the following dependency conflicts."
            )
        else:
            assert resolver_variant == "resolvelib"
            parts.append(
                "pip's dependency resolver does not currently take into account "
                "all the packages that are installed. This behaviour is the "
                "source of the following dependency conflicts."
            )

        # NOTE: There is some duplication here, with commands/check.py
        for project_name in missing:
            version = package_set[project_name][0]
            for dependency in missing[project_name]:
                message = (
                    f"{project_name} {version} requires {dependency[1]}, "
                    "which is not installed."
                )
                parts.append(message)

        for project_name in conflicting:
            version = package_set[project_name][0]
            for dep_name, dep_version, req in conflicting[project_name]:
                message = (
                    "{name} {version} requires {requirement}, but {you} have "
                    "{dep_name} {dep_version} which is incompatible."
                ).format(
                    name=project_name,
                    version=version,
                    requirement=req,
                    dep_name=dep_name,
                    dep_version=dep_version,
                    you=("you" if resolver_variant == "resolvelib" else "you'll"),
                )
                parts.append(message)

        logger.critical("\n".join(parts))


def get_lib_location_guesses(
    user: bool = False,
    home: Optional[str] = None,
    root: Optional[str] = None,
    isolated: bool = False,
    prefix: Optional[str] = None,
) -> List[str]:
    scheme = get_scheme(
        "",
        user=user,
        home=home,
        root=root,
        isolated=isolated,
        prefix=prefix,
    )
    return [scheme.purelib, scheme.platlib]


def site_packages_writable(root: Optional[str], isolated: bool) -> bool:
    return all(
        test_writable_dir(d)
        for d in set(get_lib_location_guesses(root=root, isolated=isolated))
    )


def decide_user_install(
    use_user_site: Optional[bool],
    prefix_path: Optional[str] = None,
    target_dir: Optional[str] = None,
    root_path: Optional[str] = None,
    isolated_mode: bool = False,
) -> bool:
    """Determine whether to do a user install based on the input options.

    If use_user_site is False, no additional checks are done.
    If use_user_site is True, it is checked for compatibility with other
    options.
    If use_user_site is None, the default behaviour depends on the environment,
    which is provided by the other arguments.
    """
    # In some cases (config from tox), use_user_site can be set to an integer
    # rather than a bool, which 'use_user_site is False' wouldn't catch.
    if (use_user_site is not None) and (not use_user_site):
        logger.debug("Non-user install by explicit request")
        return False

    if use_user_site:
        if prefix_path:
            raise CommandError(
                "Can not combine '--user' and '--prefix' as they imply "
                "different installation locations"
            )
        if virtualenv_no_global():
            raise InstallationError(
                "Can not perform a '--user' install. User site-packages "
                "are not visible in this virtualenv."
            )
        logger.debug("User install by explicit request")
        return True

    # If we are here, user installs have not been explicitly requested/avoided
    assert use_user_site is None

    # user install incompatible with --prefix/--target
    if prefix_path or target_dir:
        logger.debug("Non-user install due to --prefix or --target option")
        return False

    # If user installs are not enabled, choose a non-user install
    if not site.ENABLE_USER_SITE:
        logger.debug("Non-user install because user site-packages disabled")
        return False

    # If we have permission for a non-user install, do that,
    # otherwise do a user install.
    if site_packages_writable(root=root_path, isolated=isolated_mode):
        logger.debug("Non-user install because site-packages writeable")
        return False

    logger.info(
        "Defaulting to user installation because normal site-packages "
        "is not writeable"
    )
    return True


def create_os_error_message(
    error: OSError, show_traceback: bool, using_user_site: bool
) -> str:
    """Format an error message for an OSError

    It may occur anytime during the execution of the install command.
    """
    parts = []

    # Mention the error if we are not going to show a traceback
    parts.append("Could not install packages due to an OSError")
    if not show_traceback:
        parts.append(": ")
        parts.append(str(error))
    else:
        parts.append(".")

    # Spilt the error indication from a helper message (if any)
    parts[-1] += "\n"

    # Suggest useful actions to the user:
    #  (1) using user site-packages or (2) verifying the permissions
    if error.errno == errno.EACCES:
        user_option_part = "Consider using the `--user` option"
        permissions_part = "Check the permissions"

        if not running_under_virtualenv() and not using_user_site:
            parts.extend(
                [
                    user_option_part,
                    " or ",
                    permissions_part.lower(),
                ]
            )
        else:
            parts.append(permissions_part)
        parts.append(".\n")

    # Suggest the user to enable Long Paths if path length is
    # more than 260
    if (
        WINDOWS
        and error.errno == errno.ENOENT
        and error.filename
        and len(error.filename) > 260
    ):
        parts.append(
            "HINT: This error might have occurred since "
            "this system does not have Windows Long Path "
            "support enabled. You can find information on "
            "how to enable this at "
            "https://pip.pypa.io/warnings/enable-long-paths\n"
        )

    return "".join(parts).strip() + "\n"

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\vertex_ai_non_gemini.py ===
import json
import os
import time
from typing import Any, Callable, Optional, cast

import httpx

import litellm
from litellm.litellm_core_utils.core_helpers import map_finish_reason
from litellm.llms.bedrock.common_utils import ModelResponseIterator
from litellm.llms.custom_httpx.http_handler import _DEFAULT_TTL_FOR_HTTPX_CLIENTS
from litellm.types.llms.vertex_ai import *
from litellm.utils import CustomStreamWrapper, ModelResponse, Usage


class VertexAIError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        self.request = httpx.Request(
            method="POST", url=" https://cloud.google.com/vertex-ai/"
        )
        self.response = httpx.Response(status_code=status_code, request=self.request)
        super().__init__(
            self.message
        )  # Call the base class constructor with the parameters it needs


class TextStreamer:
    """
    Fake streaming iterator for Vertex AI Model Garden calls
    """

    def __init__(self, text):
        self.text = text.split()  # let's assume words as a streaming unit
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index < len(self.text):
            result = self.text[self.index]
            self.index += 1
            return result
        else:
            raise StopIteration

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index < len(self.text):
            result = self.text[self.index]
            self.index += 1
            return result
        else:
            raise StopAsyncIteration  # once we run out of data to stream, we raise this error


def _get_client_cache_key(
    model: str, vertex_project: Optional[str], vertex_location: Optional[str]
):
    _cache_key = f"{model}-{vertex_project}-{vertex_location}"
    return _cache_key


def _get_client_from_cache(client_cache_key: str):
    return litellm.in_memory_llm_clients_cache.get_cache(client_cache_key)


def _set_client_in_cache(client_cache_key: str, vertex_llm_model: Any):
    litellm.in_memory_llm_clients_cache.set_cache(
        key=client_cache_key,
        value=vertex_llm_model,
        ttl=_DEFAULT_TTL_FOR_HTTPX_CLIENTS,
    )


def completion(  # noqa: PLR0915
    model: str,
    messages: list,
    model_response: ModelResponse,
    print_verbose: Callable,
    encoding,
    logging_obj,
    optional_params: dict,
    vertex_project=None,
    vertex_location=None,
    vertex_credentials=None,
    litellm_params=None,
    logger_fn=None,
    acompletion: bool = False,
):
    """
    NON-GEMINI/ANTHROPIC CALLS.

    This is the handler for OLDER PALM MODELS and VERTEX AI MODEL GARDEN

    For Vertex AI Anthropic: `vertex_anthropic.py`
    For Gemini: `vertex_httpx.py`
    """
    try:
        import vertexai
    except Exception:
        raise VertexAIError(
            status_code=400,
            message="vertexai import failed please run `pip install google-cloud-aiplatform`. This is required for the 'vertex_ai/' route on LiteLLM",
        )

    if not (
        hasattr(vertexai, "preview") or hasattr(vertexai.preview, "language_models")
    ):
        raise VertexAIError(
            status_code=400,
            message="""Upgrade vertex ai. Run `pip install "google-cloud-aiplatform>=1.38"`""",
        )
    try:
        import google.auth  # type: ignore
        from google.cloud import aiplatform  # type: ignore
        from google.cloud.aiplatform_v1beta1.types import (
            content as gapic_content_types,  # type: ignore
        )
        from google.protobuf import json_format  # type: ignore
        from google.protobuf.struct_pb2 import Value  # type: ignore
        from vertexai.language_models import CodeGenerationModel, TextGenerationModel
        from vertexai.preview.generative_models import GenerativeModel
        from vertexai.preview.language_models import ChatModel, CodeChatModel

        ## Load credentials with the correct quota project ref: https://github.com/googleapis/python-aiplatform/issues/2557#issuecomment-1709284744
        print_verbose(
            f"VERTEX AI: vertex_project={vertex_project}; vertex_location={vertex_location}"
        )

        _cache_key = _get_client_cache_key(
            model=model, vertex_project=vertex_project, vertex_location=vertex_location
        )
        _vertex_llm_model_object = _get_client_from_cache(client_cache_key=_cache_key)

        if _vertex_llm_model_object is None:
            from google.auth.credentials import Credentials

            if vertex_credentials is not None and isinstance(vertex_credentials, str):
                import google.oauth2.service_account

                json_obj = json.loads(vertex_credentials)

                creds = (
                    google.oauth2.service_account.Credentials.from_service_account_info(
                        json_obj,
                        scopes=["https://www.googleapis.com/auth/cloud-platform"],
                    )
                )
            else:
                creds, _ = google.auth.default(quota_project_id=vertex_project)
            print_verbose(
                f"VERTEX AI: creds={creds}; google application credentials: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}"
            )
            vertexai.init(
                project=vertex_project,
                location=vertex_location,
                credentials=cast(Credentials, creds),
            )

        ## Load Config
        config = litellm.VertexAIConfig.get_config()
        for k, v in config.items():
            if k not in optional_params:
                optional_params[k] = v

        ## Process safety settings into format expected by vertex AI
        safety_settings = None
        if "safety_settings" in optional_params:
            safety_settings = optional_params.pop("safety_settings")
            if not isinstance(safety_settings, list):
                raise ValueError("safety_settings must be a list")
            if len(safety_settings) > 0 and not isinstance(safety_settings[0], dict):
                raise ValueError("safety_settings must be a list of dicts")
            safety_settings = [
                gapic_content_types.SafetySetting(x) for x in safety_settings
            ]

        # vertexai does not use an API key, it looks for credentials.json in the environment

        prompt = " ".join(
            [
                message.get("content")
                for message in messages
                if isinstance(message.get("content", None), str)
            ]
        )

        mode = ""

        request_str = ""
        response_obj = None
        instances = None
        client_options = {
            "api_endpoint": f"{vertex_location}-aiplatform.googleapis.com"
        }
        fake_stream = False
        if (
            model in litellm.vertex_language_models
            or model in litellm.vertex_vision_models
        ):
            llm_model: Any = _vertex_llm_model_object or GenerativeModel(model)
            mode = "vision"
            request_str += f"llm_model = GenerativeModel({model})\n"
        elif model in litellm.vertex_chat_models:
            llm_model = _vertex_llm_model_object or ChatModel.from_pretrained(model)
            mode = "chat"
            request_str += f"llm_model = ChatModel.from_pretrained({model})\n"
        elif model in litellm.vertex_text_models:
            llm_model = _vertex_llm_model_object or TextGenerationModel.from_pretrained(
                model
            )
            mode = "text"
            request_str += f"llm_model = TextGenerationModel.from_pretrained({model})\n"
        elif model in litellm.vertex_code_text_models:
            llm_model = _vertex_llm_model_object or CodeGenerationModel.from_pretrained(
                model
            )
            mode = "text"
            request_str += f"llm_model = CodeGenerationModel.from_pretrained({model})\n"
            fake_stream = True
        elif model in litellm.vertex_code_chat_models:  # vertex_code_llm_models
            llm_model = _vertex_llm_model_object or CodeChatModel.from_pretrained(model)
            mode = "chat"
            request_str += f"llm_model = CodeChatModel.from_pretrained({model})\n"
        elif model == "private":
            mode = "private"
            model = optional_params.pop("model_id", None)
            # private endpoint requires a dict instead of JSON
            instances = [optional_params.copy()]
            instances[0]["prompt"] = prompt
            llm_model = aiplatform.PrivateEndpoint(
                endpoint_name=model,
                project=vertex_project,
                location=vertex_location,
            )
            request_str += f"llm_model = aiplatform.PrivateEndpoint(endpoint_name={model}, project={vertex_project}, location={vertex_location})\n"
        else:  # assume vertex model garden on public endpoint
            mode = "custom"

            instances = [optional_params.copy()]
            instances[0]["prompt"] = prompt
            instances = [
                json_format.ParseDict(instance_dict, Value())
                for instance_dict in instances
            ]
            # Will determine the API used based on async parameter
            llm_model = None

        # NOTE: async prediction and streaming under "private" mode isn't supported by aiplatform right now
        if acompletion is True:
            data = {
                "llm_model": llm_model,
                "mode": mode,
                "prompt": prompt,
                "logging_obj": logging_obj,
                "request_str": request_str,
                "model": model,
                "model_response": model_response,
                "encoding": encoding,
                "messages": messages,
                "print_verbose": print_verbose,
                "client_options": client_options,
                "instances": instances,
                "vertex_location": vertex_location,
                "vertex_project": vertex_project,
                "safety_settings": safety_settings,
                **optional_params,
            }
            if optional_params.get("stream", False) is True:
                # async streaming
                return async_streaming(**data)

            return async_completion(**data)

        completion_response = None

        stream = optional_params.pop(
            "stream", None
        )  # See note above on handling streaming for vertex ai
        if mode == "chat":
            chat = llm_model.start_chat()
            request_str += "chat = llm_model.start_chat()\n"

            if fake_stream is not True and stream is True:
                # NOTE: VertexAI does not accept stream=True as a param and raises an error,
                # we handle this by removing 'stream' from optional params and sending the request
                # after we get the response we add optional_params["stream"] = True, since main.py needs to know it's a streaming response to then transform it for the OpenAI format
                optional_params.pop(
                    "stream", None
                )  # vertex ai raises an error when passing stream in optional params

                request_str += (
                    f"chat.send_message_streaming({prompt}, **{optional_params})\n"
                )
                ## LOGGING
                logging_obj.pre_call(
                    input=prompt,
                    api_key=None,
                    additional_args={
                        "complete_input_dict": optional_params,
                        "request_str": request_str,
                    },
                )

                model_response = chat.send_message_streaming(prompt, **optional_params)

                return model_response

            request_str += f"chat.send_message({prompt}, **{optional_params}).text\n"
            ## LOGGING
            logging_obj.pre_call(
                input=prompt,
                api_key=None,
                additional_args={
                    "complete_input_dict": optional_params,
                    "request_str": request_str,
                },
            )
            completion_response = chat.send_message(prompt, **optional_params).text
        elif mode == "text":
            if fake_stream is not True and stream is True:
                request_str += (
                    f"llm_model.predict_streaming({prompt}, **{optional_params})\n"
                )
                ## LOGGING
                logging_obj.pre_call(
                    input=prompt,
                    api_key=None,
                    additional_args={
                        "complete_input_dict": optional_params,
                        "request_str": request_str,
                    },
                )
                model_response = llm_model.predict_streaming(prompt, **optional_params)

                return model_response

            request_str += f"llm_model.predict({prompt}, **{optional_params}).text\n"
            ## LOGGING
            logging_obj.pre_call(
                input=prompt,
                api_key=None,
                additional_args={
                    "complete_input_dict": optional_params,
                    "request_str": request_str,
                },
            )
            completion_response = llm_model.predict(prompt, **optional_params).text
        elif mode == "custom":
            """
            Vertex AI Model Garden
            """

            if vertex_project is None or vertex_location is None:
                raise ValueError(
                    "Vertex project and location are required for custom endpoint"
                )

            ## LOGGING
            logging_obj.pre_call(
                input=prompt,
                api_key=None,
                additional_args={
                    "complete_input_dict": optional_params,
                    "request_str": request_str,
                },
            )
            llm_model = aiplatform.gapic.PredictionServiceClient(
                client_options=client_options
            )
            request_str += f"llm_model = aiplatform.gapic.PredictionServiceClient(client_options={client_options})\n"
            endpoint_path = llm_model.endpoint_path(
                project=vertex_project, location=vertex_location, endpoint=model
            )
            request_str += (
                f"llm_model.predict(endpoint={endpoint_path}, instances={instances})\n"
            )
            response = llm_model.predict(
                endpoint=endpoint_path, instances=instances
            ).predictions

            completion_response = response[0]
            if (
                isinstance(completion_response, str)
                and "\nOutput:\n" in completion_response
            ):
                completion_response = completion_response.split("\nOutput:\n", 1)[1]
            if stream is True:
                response = TextStreamer(completion_response)
                return response
        elif mode == "private":
            """
            Vertex AI Model Garden deployed on private endpoint
            """
            if instances is None:
                raise ValueError("instances are required for private endpoint")
            if llm_model is None:
                raise ValueError("Unable to pick client for private endpoint")
            ## LOGGING
            logging_obj.pre_call(
                input=prompt,
                api_key=None,
                additional_args={
                    "complete_input_dict": optional_params,
                    "request_str": request_str,
                },
            )
            request_str += f"llm_model.predict(instances={instances})\n"
            response = llm_model.predict(instances=instances).predictions

            completion_response = response[0]
            if (
                isinstance(completion_response, str)
                and "\nOutput:\n" in completion_response
            ):
                completion_response = completion_response.split("\nOutput:\n", 1)[1]
            if stream is True:
                response = TextStreamer(completion_response)
                return response

        ## LOGGING
        logging_obj.post_call(
            input=prompt, api_key=None, original_response=completion_response
        )

        ## RESPONSE OBJECT
        if isinstance(completion_response, litellm.Message):
            model_response.choices[0].message = completion_response  # type: ignore
        elif len(str(completion_response)) > 0:
            model_response.choices[0].message.content = str(completion_response)  # type: ignore
        model_response.created = int(time.time())
        model_response.model = model
        ## CALCULATING USAGE
        if model in litellm.vertex_language_models and response_obj is not None:
            model_response.choices[0].finish_reason = map_finish_reason(
                response_obj.candidates[0].finish_reason.name
            )
            usage = Usage(
                prompt_tokens=response_obj.usage_metadata.prompt_token_count,
                completion_tokens=response_obj.usage_metadata.candidates_token_count,
                total_tokens=response_obj.usage_metadata.total_token_count,
            )
        else:
            # init prompt tokens
            # this block attempts to get usage from response_obj if it exists, if not it uses the litellm token counter
            prompt_tokens, completion_tokens, _ = 0, 0, 0
            if response_obj is not None:
                if hasattr(response_obj, "usage_metadata") and hasattr(
                    response_obj.usage_metadata, "prompt_token_count"
                ):
                    prompt_tokens = response_obj.usage_metadata.prompt_token_count
                    completion_tokens = (
                        response_obj.usage_metadata.candidates_token_count
                    )
            else:
                prompt_tokens = len(encoding.encode(prompt))
                completion_tokens = len(
                    encoding.encode(
                        model_response["choices"][0]["message"].get("content", "")
                    )
                )

            usage = Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
        setattr(model_response, "usage", usage)

        if fake_stream is True and stream is True:
            return ModelResponseIterator(model_response)
        return model_response
    except Exception as e:
        if isinstance(e, VertexAIError):
            raise e
        raise litellm.APIConnectionError(
            message=str(e), llm_provider="vertex_ai", model=model
        )


async def async_completion(  # noqa: PLR0915
    llm_model,
    mode: str,
    prompt: str,
    model: str,
    messages: list,
    model_response: ModelResponse,
    request_str: str,
    print_verbose: Callable,
    logging_obj,
    encoding,
    client_options=None,
    instances=None,
    vertex_project=None,
    vertex_location=None,
    safety_settings=None,
    **optional_params,
):
    """
    Add support for acompletion calls for gemini-pro
    """
    try:
        response_obj = None
        completion_response = None
        if mode == "chat":
            # chat-bison etc.
            chat = llm_model.start_chat()
            ## LOGGING
            logging_obj.pre_call(
                input=prompt,
                api_key=None,
                additional_args={
                    "complete_input_dict": optional_params,
                    "request_str": request_str,
                },
            )
            response_obj = await chat.send_message_async(prompt, **optional_params)
            completion_response = response_obj.text
        elif mode == "text":
            # gecko etc.
            request_str += f"llm_model.predict({prompt}, **{optional_params}).text\n"
            ## LOGGING
            logging_obj.pre_call(
                input=prompt,
                api_key=None,
                additional_args={
                    "complete_input_dict": optional_params,
                    "request_str": request_str,
                },
            )
            response_obj = await llm_model.predict_async(prompt, **optional_params)
            completion_response = response_obj.text
        elif mode == "custom":
            """
            Vertex AI Model Garden
            """
            from google.cloud import aiplatform  # type: ignore

            if vertex_project is None or vertex_location is None:
                raise ValueError(
                    "Vertex project and location are required for custom endpoint"
                )

            ## LOGGING
            logging_obj.pre_call(
                input=prompt,
                api_key=None,
                additional_args={
                    "complete_input_dict": optional_params,
                    "request_str": request_str,
                },
            )

            llm_model = aiplatform.gapic.PredictionServiceAsyncClient(
                client_options=client_options
            )
            request_str += f"llm_model = aiplatform.gapic.PredictionServiceAsyncClient(client_options={client_options})\n"
            endpoint_path = llm_model.endpoint_path(
                project=vertex_project, location=vertex_location, endpoint=model
            )
            request_str += (
                f"llm_model.predict(endpoint={endpoint_path}, instances={instances})\n"
            )
            response_obj = await llm_model.predict(
                endpoint=endpoint_path,
                instances=instances,
            )
            response = response_obj.predictions
            completion_response = response[0]
            if (
                isinstance(completion_response, str)
                and "\nOutput:\n" in completion_response
            ):
                completion_response = completion_response.split("\nOutput:\n", 1)[1]

        elif mode == "private":
            request_str += f"llm_model.predict_async(instances={instances})\n"
            response_obj = await llm_model.predict_async(
                instances=instances,
            )

            response = response_obj.predictions
            completion_response = response[0]
            if (
                isinstance(completion_response, str)
                and "\nOutput:\n" in completion_response
            ):
                completion_response = completion_response.split("\nOutput:\n", 1)[1]

        ## LOGGING
        logging_obj.post_call(
            input=prompt, api_key=None, original_response=completion_response
        )

        ## RESPONSE OBJECT
        if isinstance(completion_response, litellm.Message):
            model_response.choices[0].message = completion_response  # type: ignore
        elif len(str(completion_response)) > 0:
            model_response.choices[0].message.content = str(  # type: ignore
                completion_response
            )
        model_response.created = int(time.time())
        model_response.model = model
        ## CALCULATING USAGE
        if model in litellm.vertex_language_models and response_obj is not None:
            model_response.choices[0].finish_reason = map_finish_reason(
                response_obj.candidates[0].finish_reason.name
            )
            usage = Usage(
                prompt_tokens=response_obj.usage_metadata.prompt_token_count,
                completion_tokens=response_obj.usage_metadata.candidates_token_count,
                total_tokens=response_obj.usage_metadata.total_token_count,
            )
        else:
            # init prompt tokens
            # this block attempts to get usage from response_obj if it exists, if not it uses the litellm token counter
            prompt_tokens, completion_tokens, _ = 0, 0, 0
            if response_obj is not None and (
                hasattr(response_obj, "usage_metadata")
                and hasattr(response_obj.usage_metadata, "prompt_token_count")
            ):
                prompt_tokens = response_obj.usage_metadata.prompt_token_count
                completion_tokens = response_obj.usage_metadata.candidates_token_count
            else:
                prompt_tokens = len(encoding.encode(prompt))
                completion_tokens = len(
                    encoding.encode(
                        model_response["choices"][0]["message"].get("content", "")
                    )
                )

            # set usage
            usage = Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
        setattr(model_response, "usage", usage)
        return model_response
    except Exception as e:
        raise VertexAIError(status_code=500, message=str(e))


async def async_streaming(  # noqa: PLR0915
    llm_model,
    mode: str,
    prompt: str,
    model: str,
    model_response: ModelResponse,
    messages: list,
    print_verbose: Callable,
    logging_obj,
    request_str: str,
    encoding=None,
    client_options=None,
    instances=None,
    vertex_project=None,
    vertex_location=None,
    safety_settings=None,
    **optional_params,
):
    """
    Add support for async streaming calls for gemini-pro
    """
    response: Any = None
    if mode == "chat":
        chat = llm_model.start_chat()
        optional_params.pop(
            "stream", None
        )  # vertex ai raises an error when passing stream in optional params
        request_str += (
            f"chat.send_message_streaming_async({prompt}, **{optional_params})\n"
        )
        ## LOGGING
        logging_obj.pre_call(
            input=prompt,
            api_key=None,
            additional_args={
                "complete_input_dict": optional_params,
                "request_str": request_str,
            },
        )
        response = chat.send_message_streaming_async(prompt, **optional_params)

    elif mode == "text":
        optional_params.pop(
            "stream", None
        )  # See note above on handling streaming for vertex ai
        request_str += (
            f"llm_model.predict_streaming_async({prompt}, **{optional_params})\n"
        )
        ## LOGGING
        logging_obj.pre_call(
            input=prompt,
            api_key=None,
            additional_args={
                "complete_input_dict": optional_params,
                "request_str": request_str,
            },
        )
        response = llm_model.predict_streaming_async(prompt, **optional_params)
    elif mode == "custom":
        from google.cloud import aiplatform  # type: ignore

        if vertex_project is None or vertex_location is None:
            raise ValueError(
                "Vertex project and location are required for custom endpoint"
            )

        stream = optional_params.pop("stream", None)

        ## LOGGING
        logging_obj.pre_call(
            input=prompt,
            api_key=None,
            additional_args={
                "complete_input_dict": optional_params,
                "request_str": request_str,
            },
        )
        llm_model = aiplatform.gapic.PredictionServiceAsyncClient(
            client_options=client_options
        )
        request_str += f"llm_model = aiplatform.gapic.PredictionServiceAsyncClient(client_options={client_options})\n"
        endpoint_path = llm_model.endpoint_path(
            project=vertex_project, location=vertex_location, endpoint=model
        )
        request_str += (
            f"client.predict(endpoint={endpoint_path}, instances={instances})\n"
        )
        response_obj = await llm_model.predict(
            endpoint=endpoint_path,
            instances=instances,
        )

        response = response_obj.predictions
        completion_response = response[0]
        if (
            isinstance(completion_response, str)
            and "\nOutput:\n" in completion_response
        ):
            completion_response = completion_response.split("\nOutput:\n", 1)[1]
        if stream:
            response = TextStreamer(completion_response)

    elif mode == "private":
        if instances is None:
            raise ValueError("Instances are required for private endpoint")
        stream = optional_params.pop("stream", None)
        _ = instances[0].pop("stream", None)
        request_str += f"llm_model.predict_async(instances={instances})\n"
        response_obj = await llm_model.predict_async(
            instances=instances,
        )
        response = response_obj.predictions
        completion_response = response[0]
        if (
            isinstance(completion_response, str)
            and "\nOutput:\n" in completion_response
        ):
            completion_response = completion_response.split("\nOutput:\n", 1)[1]
        if stream:
            response = TextStreamer(completion_response)

    if response is None:
        raise ValueError("Unable to generate response")

    logging_obj.post_call(input=prompt, api_key=None, original_response=response)

    streamwrapper = CustomStreamWrapper(
        completion_stream=response,
        model=model,
        custom_llm_provider="vertex_ai",
        logging_obj=logging_obj,
    )

    return streamwrapper

# === NexusCore/openenv\Lib\site-packages\openai\resources\audio\transcriptions.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Union, Mapping, Optional, cast
from typing_extensions import Literal, overload, assert_never

import httpx

from ... import _legacy_response
from ...types import AudioResponseFormat
from ..._types import NOT_GIVEN, Body, Query, Headers, NotGiven, FileTypes
from ..._utils import extract_files, required_args, maybe_transform, deepcopy_minimal, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ..._streaming import Stream, AsyncStream
from ...types.audio import transcription_create_params
from ..._base_client import make_request_options
from ...types.audio_model import AudioModel
from ...types.audio.transcription import Transcription
from ...types.audio_response_format import AudioResponseFormat
from ...types.audio.transcription_include import TranscriptionInclude
from ...types.audio.transcription_verbose import TranscriptionVerbose
from ...types.audio.transcription_stream_event import TranscriptionStreamEvent
from ...types.audio.transcription_create_response import TranscriptionCreateResponse

__all__ = ["Transcriptions", "AsyncTranscriptions"]

log: logging.Logger = logging.getLogger("openai.audio.transcriptions")


class Transcriptions(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> TranscriptionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return TranscriptionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> TranscriptionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return TranscriptionsWithStreamingResponse(self)

    @overload
    def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        chunking_strategy: Optional[transcription_create_params.ChunkingStrategy] | NotGiven = NOT_GIVEN,
        include: List[TranscriptionInclude] | NotGiven = NOT_GIVEN,
        response_format: Union[Literal["json"], NotGiven] = NOT_GIVEN,
        language: str | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Transcription: ...

    @overload
    def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        chunking_strategy: Optional[transcription_create_params.ChunkingStrategy] | NotGiven = NOT_GIVEN,
        include: List[TranscriptionInclude] | NotGiven = NOT_GIVEN,
        response_format: Literal["verbose_json"],
        language: str | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> TranscriptionVerbose: ...

    @overload
    def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        chunking_strategy: Optional[transcription_create_params.ChunkingStrategy] | NotGiven = NOT_GIVEN,
        response_format: Literal["text", "srt", "vtt"],
        include: List[TranscriptionInclude] | NotGiven = NOT_GIVEN,
        language: str | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> str: ...

    @overload
    def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        stream: Literal[True],
        chunking_strategy: Optional[transcription_create_params.ChunkingStrategy] | NotGiven = NOT_GIVEN,
        include: List[TranscriptionInclude] | NotGiven = NOT_GIVEN,
        language: str | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        response_format: Union[AudioResponseFormat, NotGiven] = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Stream[TranscriptionStreamEvent]:
        """
        Transcribes audio into the input language.

        Args:
          file:
              The audio file object (not file name) to transcribe, in one of these formats:
              flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.

          model: ID of the model to use. The options are `gpt-4o-transcribe`,
              `gpt-4o-mini-transcribe`, and `whisper-1` (which is powered by our open source
              Whisper V2 model).

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section of the Speech-to-Text guide](https://platform.openai.com/docs/guides/speech-to-text?lang=curl#streaming-transcriptions)
              for more information.

              Note: Streaming is not supported for the `whisper-1` model and will be ignored.

          chunking_strategy: Controls how the audio is cut into chunks. When set to `"auto"`, the server
              first normalizes loudness and then uses voice activity detection (VAD) to choose
              boundaries. `server_vad` object can be provided to tweak VAD detection
              parameters manually. If unset, the audio is transcribed as a single block.

          include: Additional information to include in the transcription response. `logprobs` will
              return the log probabilities of the tokens in the response to understand the
              model's confidence in the transcription. `logprobs` only works with
              response_format set to `json` and only with the models `gpt-4o-transcribe` and
              `gpt-4o-mini-transcribe`.

          language: The language of the input audio. Supplying the input language in
              [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `en`)
              format will improve accuracy and latency.

          prompt: An optional text to guide the model's style or continue a previous audio
              segment. The
              [prompt](https://platform.openai.com/docs/guides/speech-to-text#prompting)
              should match the audio language.

          response_format: The format of the output, in one of these options: `json`, `text`, `srt`,
              `verbose_json`, or `vtt`. For `gpt-4o-transcribe` and `gpt-4o-mini-transcribe`,
              the only supported format is `json`.

          temperature: The sampling temperature, between 0 and 1. Higher values like 0.8 will make the
              output more random, while lower values like 0.2 will make it more focused and
              deterministic. If set to 0, the model will use
              [log probability](https://en.wikipedia.org/wiki/Log_probability) to
              automatically increase the temperature until certain thresholds are hit.

          timestamp_granularities: The timestamp granularities to populate for this transcription.
              `response_format` must be set `verbose_json` to use timestamp granularities.
              Either or both of these options are supported: `word`, or `segment`. Note: There
              is no additional latency for segment timestamps, but generating word timestamps
              incurs additional latency.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        stream: bool,
        chunking_strategy: Optional[transcription_create_params.ChunkingStrategy] | NotGiven = NOT_GIVEN,
        include: List[TranscriptionInclude] | NotGiven = NOT_GIVEN,
        language: str | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        response_format: Union[AudioResponseFormat, NotGiven] = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> TranscriptionCreateResponse | Stream[TranscriptionStreamEvent]:
        """
        Transcribes audio into the input language.

        Args:
          file:
              The audio file object (not file name) to transcribe, in one of these formats:
              flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.

          model: ID of the model to use. The options are `gpt-4o-transcribe`,
              `gpt-4o-mini-transcribe`, and `whisper-1` (which is powered by our open source
              Whisper V2 model).

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section of the Speech-to-Text guide](https://platform.openai.com/docs/guides/speech-to-text?lang=curl#streaming-transcriptions)
              for more information.

              Note: Streaming is not supported for the `whisper-1` model and will be ignored.

          chunking_strategy: Controls how the audio is cut into chunks. When set to `"auto"`, the server
              first normalizes loudness and then uses voice activity detection (VAD) to choose
              boundaries. `server_vad` object can be provided to tweak VAD detection
              parameters manually. If unset, the audio is transcribed as a single block.

          include: Additional information to include in the transcription response. `logprobs` will
              return the log probabilities of the tokens in the response to understand the
              model's confidence in the transcription. `logprobs` only works with
              response_format set to `json` and only with the models `gpt-4o-transcribe` and
              `gpt-4o-mini-transcribe`.

          language: The language of the input audio. Supplying the input language in
              [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `en`)
              format will improve accuracy and latency.

          prompt: An optional text to guide the model's style or continue a previous audio
              segment. The
              [prompt](https://platform.openai.com/docs/guides/speech-to-text#prompting)
              should match the audio language.

          response_format: The format of the output, in one of these options: `json`, `text`, `srt`,
              `verbose_json`, or `vtt`. For `gpt-4o-transcribe` and `gpt-4o-mini-transcribe`,
              the only supported format is `json`.

          temperature: The sampling temperature, between 0 and 1. Higher values like 0.8 will make the
              output more random, while lower values like 0.2 will make it more focused and
              deterministic. If set to 0, the model will use
              [log probability](https://en.wikipedia.org/wiki/Log_probability) to
              automatically increase the temperature until certain thresholds are hit.

          timestamp_granularities: The timestamp granularities to populate for this transcription.
              `response_format` must be set `verbose_json` to use timestamp granularities.
              Either or both of these options are supported: `word`, or `segment`. Note: There
              is no additional latency for segment timestamps, but generating word timestamps
              incurs additional latency.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @required_args(["file", "model"], ["file", "model", "stream"])
    def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        chunking_strategy: Optional[transcription_create_params.ChunkingStrategy] | NotGiven = NOT_GIVEN,
        include: List[TranscriptionInclude] | NotGiven = NOT_GIVEN,
        language: str | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        response_format: Union[AudioResponseFormat, NotGiven] = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> str | Transcription | TranscriptionVerbose | Stream[TranscriptionStreamEvent]:
        body = deepcopy_minimal(
            {
                "file": file,
                "model": model,
                "chunking_strategy": chunking_strategy,
                "include": include,
                "language": language,
                "prompt": prompt,
                "response_format": response_format,
                "stream": stream,
                "temperature": temperature,
                "timestamp_granularities": timestamp_granularities,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return self._post(  # type: ignore[return-value]
            "/audio/transcriptions",
            body=maybe_transform(
                body,
                transcription_create_params.TranscriptionCreateParamsStreaming
                if stream
                else transcription_create_params.TranscriptionCreateParamsNonStreaming,
            ),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=_get_response_format_type(response_format),
            stream=stream or False,
            stream_cls=Stream[TranscriptionStreamEvent],
        )


class AsyncTranscriptions(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncTranscriptionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncTranscriptionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncTranscriptionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncTranscriptionsWithStreamingResponse(self)

    @overload
    async def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        chunking_strategy: Optional[transcription_create_params.ChunkingStrategy] | NotGiven = NOT_GIVEN,
        include: List[TranscriptionInclude] | NotGiven = NOT_GIVEN,
        language: str | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        response_format: Union[Literal["json"], NotGiven] = NOT_GIVEN,
        stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> TranscriptionCreateResponse:
        """
        Transcribes audio into the input language.

        Args:
          file:
              The audio file object (not file name) to transcribe, in one of these formats:
              flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.

          model: ID of the model to use. The options are `gpt-4o-transcribe`,
              `gpt-4o-mini-transcribe`, and `whisper-1` (which is powered by our open source
              Whisper V2 model).

          chunking_strategy: Controls how the audio is cut into chunks. When set to `"auto"`, the server
              first normalizes loudness and then uses voice activity detection (VAD) to choose
              boundaries. `server_vad` object can be provided to tweak VAD detection
              parameters manually. If unset, the audio is transcribed as a single block.

          include: Additional information to include in the transcription response. `logprobs` will
              return the log probabilities of the tokens in the response to understand the
              model's confidence in the transcription. `logprobs` only works with
              response_format set to `json` and only with the models `gpt-4o-transcribe` and
              `gpt-4o-mini-transcribe`.

          language: The language of the input audio. Supplying the input language in
              [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `en`)
              format will improve accuracy and latency.

          prompt: An optional text to guide the model's style or continue a previous audio
              segment. The
              [prompt](https://platform.openai.com/docs/guides/speech-to-text#prompting)
              should match the audio language.

          response_format: The format of the output, in one of these options: `json`, `text`, `srt`,
              `verbose_json`, or `vtt`. For `gpt-4o-transcribe` and `gpt-4o-mini-transcribe`,
              the only supported format is `json`.

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section of the Speech-to-Text guide](https://platform.openai.com/docs/guides/speech-to-text?lang=curl#streaming-transcriptions)
              for more information.

              Note: Streaming is not supported for the `whisper-1` model and will be ignored.

          temperature: The sampling temperature, between 0 and 1. Higher values like 0.8 will make the
              output more random, while lower values like 0.2 will make it more focused and
              deterministic. If set to 0, the model will use
              [log probability](https://en.wikipedia.org/wiki/Log_probability) to
              automatically increase the temperature until certain thresholds are hit.

          timestamp_granularities: The timestamp granularities to populate for this transcription.
              `response_format` must be set `verbose_json` to use timestamp granularities.
              Either or both of these options are supported: `word`, or `segment`. Note: There
              is no additional latency for segment timestamps, but generating word timestamps
              incurs additional latency.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request
        """

    @overload
    async def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        chunking_strategy: Optional[transcription_create_params.ChunkingStrategy] | NotGiven = NOT_GIVEN,
        include: List[TranscriptionInclude] | NotGiven = NOT_GIVEN,
        response_format: Literal["verbose_json"],
        language: str | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> TranscriptionVerbose: ...

    @overload
    async def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        chunking_strategy: Optional[transcription_create_params.ChunkingStrategy] | NotGiven = NOT_GIVEN,
        include: List[TranscriptionInclude] | NotGiven = NOT_GIVEN,
        response_format: Literal["text", "srt", "vtt"],
        language: str | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> str: ...

    @overload
    async def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        stream: Literal[True],
        chunking_strategy: Optional[transcription_create_params.ChunkingStrategy] | NotGiven = NOT_GIVEN,
        include: List[TranscriptionInclude] | NotGiven = NOT_GIVEN,
        language: str | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        response_format: Union[AudioResponseFormat, NotGiven] = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[TranscriptionStreamEvent]:
        """
        Transcribes audio into the input language.

        Args:
          file:
              The audio file object (not file name) to transcribe, in one of these formats:
              flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.

          model: ID of the model to use. The options are `gpt-4o-transcribe`,
              `gpt-4o-mini-transcribe`, and `whisper-1` (which is powered by our open source
              Whisper V2 model).

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section of the Speech-to-Text guide](https://platform.openai.com/docs/guides/speech-to-text?lang=curl#streaming-transcriptions)
              for more information.

              Note: Streaming is not supported for the `whisper-1` model and will be ignored.

          chunking_strategy: Controls how the audio is cut into chunks. When set to `"auto"`, the server
              first normalizes loudness and then uses voice activity detection (VAD) to choose
              boundaries. `server_vad` object can be provided to tweak VAD detection
              parameters manually. If unset, the audio is transcribed as a single block.

          include: Additional information to include in the transcription response. `logprobs` will
              return the log probabilities of the tokens in the response to understand the
              model's confidence in the transcription. `logprobs` only works with
              response_format set to `json` and only with the models `gpt-4o-transcribe` and
              `gpt-4o-mini-transcribe`.

          language: The language of the input audio. Supplying the input language in
              [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `en`)
              format will improve accuracy and latency.

          prompt: An optional text to guide the model's style or continue a previous audio
              segment. The
              [prompt](https://platform.openai.com/docs/guides/speech-to-text#prompting)
              should match the audio language.

          response_format: The format of the output, in one of these options: `json`, `text`, `srt`,
              `verbose_json`, or `vtt`. For `gpt-4o-transcribe` and `gpt-4o-mini-transcribe`,
              the only supported format is `json`.

          temperature: The sampling temperature, between 0 and 1. Higher values like 0.8 will make the
              output more random, while lower values like 0.2 will make it more focused and
              deterministic. If set to 0, the model will use
              [log probability](https://en.wikipedia.org/wiki/Log_probability) to
              automatically increase the temperature until certain thresholds are hit.

          timestamp_granularities: The timestamp granularities to populate for this transcription.
              `response_format` must be set `verbose_json` to use timestamp granularities.
              Either or both of these options are supported: `word`, or `segment`. Note: There
              is no additional latency for segment timestamps, but generating word timestamps
              incurs additional latency.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    async def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        stream: bool,
        chunking_strategy: Optional[transcription_create_params.ChunkingStrategy] | NotGiven = NOT_GIVEN,
        include: List[TranscriptionInclude] | NotGiven = NOT_GIVEN,
        language: str | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        response_format: Union[AudioResponseFormat, NotGiven] = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> TranscriptionCreateResponse | AsyncStream[TranscriptionStreamEvent]:
        """
        Transcribes audio into the input language.

        Args:
          file:
              The audio file object (not file name) to transcribe, in one of these formats:
              flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.

          model: ID of the model to use. The options are `gpt-4o-transcribe`,
              `gpt-4o-mini-transcribe`, and `whisper-1` (which is powered by our open source
              Whisper V2 model).

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section of the Speech-to-Text guide](https://platform.openai.com/docs/guides/speech-to-text?lang=curl#streaming-transcriptions)
              for more information.

              Note: Streaming is not supported for the `whisper-1` model and will be ignored.

          chunking_strategy: Controls how the audio is cut into chunks. When set to `"auto"`, the server
              first normalizes loudness and then uses voice activity detection (VAD) to choose
              boundaries. `server_vad` object can be provided to tweak VAD detection
              parameters manually. If unset, the audio is transcribed as a single block.

          include: Additional information to include in the transcription response. `logprobs` will
              return the log probabilities of the tokens in the response to understand the
              model's confidence in the transcription. `logprobs` only works with
              response_format set to `json` and only with the models `gpt-4o-transcribe` and
              `gpt-4o-mini-transcribe`.

          language: The language of the input audio. Supplying the input language in
              [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `en`)
              format will improve accuracy and latency.

          prompt: An optional text to guide the model's style or continue a previous audio
              segment. The
              [prompt](https://platform.openai.com/docs/guides/speech-to-text#prompting)
              should match the audio language.

          response_format: The format of the output, in one of these options: `json`, `text`, `srt`,
              `verbose_json`, or `vtt`. For `gpt-4o-transcribe` and `gpt-4o-mini-transcribe`,
              the only supported format is `json`.

          temperature: The sampling temperature, between 0 and 1. Higher values like 0.8 will make the
              output more random, while lower values like 0.2 will make it more focused and
              deterministic. If set to 0, the model will use
              [log probability](https://en.wikipedia.org/wiki/Log_probability) to
              automatically increase the temperature until certain thresholds are hit.

          timestamp_granularities: The timestamp granularities to populate for this transcription.
              `response_format` must be set `verbose_json` to use timestamp granularities.
              Either or both of these options are supported: `word`, or `segment`. Note: There
              is no additional latency for segment timestamps, but generating word timestamps
              incurs additional latency.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @required_args(["file", "model"], ["file", "model", "stream"])
    async def create(
        self,
        *,
        file: FileTypes,
        model: Union[str, AudioModel],
        chunking_strategy: Optional[transcription_create_params.ChunkingStrategy] | NotGiven = NOT_GIVEN,
        include: List[TranscriptionInclude] | NotGiven = NOT_GIVEN,
        language: str | NotGiven = NOT_GIVEN,
        prompt: str | NotGiven = NOT_GIVEN,
        response_format: Union[AudioResponseFormat, NotGiven] = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        timestamp_granularities: List[Literal["word", "segment"]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Transcription | TranscriptionVerbose | str | AsyncStream[TranscriptionStreamEvent]:
        body = deepcopy_minimal(
            {
                "file": file,
                "model": model,
                "chunking_strategy": chunking_strategy,
                "include": include,
                "language": language,
                "prompt": prompt,
                "response_format": response_format,
                "stream": stream,
                "temperature": temperature,
                "timestamp_granularities": timestamp_granularities,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return await self._post(
            "/audio/transcriptions",
            body=await async_maybe_transform(
                body,
                transcription_create_params.TranscriptionCreateParamsStreaming
                if stream
                else transcription_create_params.TranscriptionCreateParamsNonStreaming,
            ),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=_get_response_format_type(response_format),
            stream=stream or False,
            stream_cls=AsyncStream[TranscriptionStreamEvent],
        )


class TranscriptionsWithRawResponse:
    def __init__(self, transcriptions: Transcriptions) -> None:
        self._transcriptions = transcriptions

        self.create = _legacy_response.to_raw_response_wrapper(
            transcriptions.create,
        )


class AsyncTranscriptionsWithRawResponse:
    def __init__(self, transcriptions: AsyncTranscriptions) -> None:
        self._transcriptions = transcriptions

        self.create = _legacy_response.async_to_raw_response_wrapper(
            transcriptions.create,
        )


class TranscriptionsWithStreamingResponse:
    def __init__(self, transcriptions: Transcriptions) -> None:
        self._transcriptions = transcriptions

        self.create = to_streamed_response_wrapper(
            transcriptions.create,
        )


class AsyncTranscriptionsWithStreamingResponse:
    def __init__(self, transcriptions: AsyncTranscriptions) -> None:
        self._transcriptions = transcriptions

        self.create = async_to_streamed_response_wrapper(
            transcriptions.create,
        )


def _get_response_format_type(
    response_format: Literal["json", "text", "srt", "verbose_json", "vtt"] | NotGiven,
) -> type[Transcription | TranscriptionVerbose | str]:
    if isinstance(response_format, NotGiven) or response_format is None:  # pyright: ignore[reportUnnecessaryComparison]
        return Transcription

    if response_format == "json":
        return Transcription
    elif response_format == "verbose_json":
        return TranscriptionVerbose
    elif response_format == "srt" or response_format == "text" or response_format == "vtt":
        return str
    elif TYPE_CHECKING:  # type: ignore[unreachable]
        assert_never(response_format)
    else:
        log.warn("Unexpected audio response format: %s", response_format)
        return Transcription

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\util.py ===
# Natural Language Toolkit: Corpus Reader Utilities
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import bisect
import os
import pickle
import re
import tempfile
from functools import reduce
from xml.etree import ElementTree

from nltk.data import (
    FileSystemPathPointer,
    PathPointer,
    SeekableUnicodeStreamReader,
    ZipFilePathPointer,
)
from nltk.internals import slice_bounds
from nltk.tokenize import wordpunct_tokenize
from nltk.util import AbstractLazySequence, LazyConcatenation, LazySubsequence

######################################################################
# { Corpus View
######################################################################


class StreamBackedCorpusView(AbstractLazySequence):
    """
    A 'view' of a corpus file, which acts like a sequence of tokens:
    it can be accessed by index, iterated over, etc.  However, the
    tokens are only constructed as-needed -- the entire corpus is
    never stored in memory at once.

    The constructor to ``StreamBackedCorpusView`` takes two arguments:
    a corpus fileid (specified as a string or as a ``PathPointer``);
    and a block reader.  A "block reader" is a function that reads
    zero or more tokens from a stream, and returns them as a list.  A
    very simple example of a block reader is:

        >>> def simple_block_reader(stream):
        ...     return stream.readline().split()

    This simple block reader reads a single line at a time, and
    returns a single token (consisting of a string) for each
    whitespace-separated substring on the line.

    When deciding how to define the block reader for a given
    corpus, careful consideration should be given to the size of
    blocks handled by the block reader.  Smaller block sizes will
    increase the memory requirements of the corpus view's internal
    data structures (by 2 integers per block).  On the other hand,
    larger block sizes may decrease performance for random access to
    the corpus.  (But note that larger block sizes will *not*
    decrease performance for iteration.)

    Internally, ``CorpusView`` maintains a partial mapping from token
    index to file position, with one entry per block.  When a token
    with a given index *i* is requested, the ``CorpusView`` constructs
    it as follows:

      1. First, it searches the toknum/filepos mapping for the token
         index closest to (but less than or equal to) *i*.

      2. Then, starting at the file position corresponding to that
         index, it reads one block at a time using the block reader
         until it reaches the requested token.

    The toknum/filepos mapping is created lazily: it is initially
    empty, but every time a new block is read, the block's
    initial token is added to the mapping.  (Thus, the toknum/filepos
    map has one entry per block.)

    In order to increase efficiency for random access patterns that
    have high degrees of locality, the corpus view may cache one or
    more blocks.

    :note: Each ``CorpusView`` object internally maintains an open file
        object for its underlying corpus file.  This file should be
        automatically closed when the ``CorpusView`` is garbage collected,
        but if you wish to close it manually, use the ``close()``
        method.  If you access a ``CorpusView``'s items after it has been
        closed, the file object will be automatically re-opened.

    :warning: If the contents of the file are modified during the
        lifetime of the ``CorpusView``, then the ``CorpusView``'s behavior
        is undefined.

    :warning: If a unicode encoding is specified when constructing a
        ``CorpusView``, then the block reader may only call
        ``stream.seek()`` with offsets that have been returned by
        ``stream.tell()``; in particular, calling ``stream.seek()`` with
        relative offsets, or with offsets based on string lengths, may
        lead to incorrect behavior.

    :ivar _block_reader: The function used to read
        a single block from the underlying file stream.
    :ivar _toknum: A list containing the token index of each block
        that has been processed.  In particular, ``_toknum[i]`` is the
        token index of the first token in block ``i``.  Together
        with ``_filepos``, this forms a partial mapping between token
        indices and file positions.
    :ivar _filepos: A list containing the file position of each block
        that has been processed.  In particular, ``_toknum[i]`` is the
        file position of the first character in block ``i``.  Together
        with ``_toknum``, this forms a partial mapping between token
        indices and file positions.
    :ivar _stream: The stream used to access the underlying corpus file.
    :ivar _len: The total number of tokens in the corpus, if known;
        or None, if the number of tokens is not yet known.
    :ivar _eofpos: The character position of the last character in the
        file.  This is calculated when the corpus view is initialized,
        and is used to decide when the end of file has been reached.
    :ivar _cache: A cache of the most recently read block.  It
       is encoded as a tuple (start_toknum, end_toknum, tokens), where
       start_toknum is the token index of the first token in the block;
       end_toknum is the token index of the first token not in the
       block; and tokens is a list of the tokens in the block.
    """

    def __init__(self, fileid, block_reader=None, startpos=0, encoding="utf8"):
        """
        Create a new corpus view, based on the file ``fileid``, and
        read with ``block_reader``.  See the class documentation
        for more information.

        :param fileid: The path to the file that is read by this
            corpus view.  ``fileid`` can either be a string or a
            ``PathPointer``.

        :param startpos: The file position at which the view will
            start reading.  This can be used to skip over preface
            sections.

        :param encoding: The unicode encoding that should be used to
            read the file's contents.  If no encoding is specified,
            then the file's contents will be read as a non-unicode
            string (i.e., a str).
        """
        if block_reader:
            self.read_block = block_reader
        # Initialize our toknum/filepos mapping.
        self._toknum = [0]
        self._filepos = [startpos]
        self._encoding = encoding
        # We don't know our length (number of tokens) yet.
        self._len = None

        self._fileid = fileid
        self._stream = None

        self._current_toknum = None
        """This variable is set to the index of the next token that
           will be read, immediately before ``self.read_block()`` is
           called.  This is provided for the benefit of the block
           reader, which under rare circumstances may need to know
           the current token number."""

        self._current_blocknum = None
        """This variable is set to the index of the next block that
           will be read, immediately before ``self.read_block()`` is
           called.  This is provided for the benefit of the block
           reader, which under rare circumstances may need to know
           the current block number."""

        # Find the length of the file.
        try:
            if isinstance(self._fileid, PathPointer):
                self._eofpos = self._fileid.file_size()
            else:
                self._eofpos = os.stat(self._fileid).st_size
        except Exception as exc:
            raise ValueError(f"Unable to open or access {fileid!r} -- {exc}") from exc

        # Maintain a cache of the most recently read block, to
        # increase efficiency of random access.
        self._cache = (-1, -1, None)

    fileid = property(
        lambda self: self._fileid,
        doc="""
        The fileid of the file that is accessed by this view.

        :type: str or PathPointer""",
    )

    def read_block(self, stream):
        """
        Read a block from the input stream.

        :return: a block of tokens from the input stream
        :rtype: list(any)
        :param stream: an input stream
        :type stream: stream
        """
        raise NotImplementedError("Abstract Method")

    def _open(self):
        """
        Open the file stream associated with this corpus view.  This
        will be called performed if any value is read from the view
        while its file stream is closed.
        """
        if isinstance(self._fileid, PathPointer):
            self._stream = self._fileid.open(self._encoding)
        elif self._encoding:
            self._stream = SeekableUnicodeStreamReader(
                open(self._fileid, "rb"), self._encoding
            )
        else:
            self._stream = open(self._fileid, "rb")

    def close(self):
        """
        Close the file stream associated with this corpus view.  This
        can be useful if you are worried about running out of file
        handles (although the stream should automatically be closed
        upon garbage collection of the corpus view).  If the corpus
        view is accessed after it is closed, it will be automatically
        re-opened.
        """
        if self._stream is not None:
            self._stream.close()
        self._stream = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __len__(self):
        if self._len is None:
            # iterate_from() sets self._len when it reaches the end
            # of the file:
            for tok in self.iterate_from(self._toknum[-1]):
                pass
        return self._len

    def __getitem__(self, i):
        if isinstance(i, slice):
            start, stop = slice_bounds(self, i)
            # Check if it's in the cache.
            offset = self._cache[0]
            if offset <= start and stop <= self._cache[1]:
                return self._cache[2][start - offset : stop - offset]
            # Construct & return the result.
            return LazySubsequence(self, start, stop)
        else:
            # Handle negative indices
            if i < 0:
                i += len(self)
            if i < 0:
                raise IndexError("index out of range")
            # Check if it's in the cache.
            offset = self._cache[0]
            if offset <= i < self._cache[1]:
                return self._cache[2][i - offset]
            # Use iterate_from to extract it.
            try:
                return next(self.iterate_from(i))
            except StopIteration as e:
                raise IndexError("index out of range") from e

    # If we wanted to be thread-safe, then this method would need to
    # do some locking.
    def iterate_from(self, start_tok):
        # Start by feeding from the cache, if possible.
        if self._cache[0] <= start_tok < self._cache[1]:
            for tok in self._cache[2][start_tok - self._cache[0] :]:
                yield tok
                start_tok += 1

        # Decide where in the file we should start.  If `start` is in
        # our mapping, then we can jump straight to the correct block;
        # otherwise, start at the last block we've processed.
        if start_tok < self._toknum[-1]:
            block_index = bisect.bisect_right(self._toknum, start_tok) - 1
            toknum = self._toknum[block_index]
            filepos = self._filepos[block_index]
        else:
            block_index = len(self._toknum) - 1
            toknum = self._toknum[-1]
            filepos = self._filepos[-1]

        # Open the stream, if it's not open already.
        if self._stream is None:
            self._open()

        # If the file is empty, the while loop will never run.
        # This *seems* to be all the state we need to set:
        if self._eofpos == 0:
            self._len = 0

        # Each iteration through this loop, we read a single block
        # from the stream.
        while filepos < self._eofpos:
            # Read the next block.
            self._stream.seek(filepos)
            self._current_toknum = toknum
            self._current_blocknum = block_index
            tokens = self.read_block(self._stream)
            assert isinstance(tokens, (tuple, list, AbstractLazySequence)), (
                "block reader %s() should return list or tuple."
                % self.read_block.__name__
            )
            num_toks = len(tokens)
            new_filepos = self._stream.tell()
            assert (
                new_filepos > filepos
            ), "block reader %s() should consume at least 1 byte (filepos=%d)" % (
                self.read_block.__name__,
                filepos,
            )

            # Update our cache.
            self._cache = (toknum, toknum + num_toks, list(tokens))

            # Update our mapping.
            assert toknum <= self._toknum[-1]
            if num_toks > 0:
                block_index += 1
                if toknum == self._toknum[-1]:
                    assert new_filepos > self._filepos[-1]  # monotonic!
                    self._filepos.append(new_filepos)
                    self._toknum.append(toknum + num_toks)
                else:
                    # Check for consistency:
                    assert (
                        new_filepos == self._filepos[block_index]
                    ), "inconsistent block reader (num chars read)"
                    assert (
                        toknum + num_toks == self._toknum[block_index]
                    ), "inconsistent block reader (num tokens returned)"

            # If we reached the end of the file, then update self._len
            if new_filepos == self._eofpos:
                self._len = toknum + num_toks
            # Generate the tokens in this block (but skip any tokens
            # before start_tok).  Note that between yields, our state
            # may be modified.
            for tok in tokens[max(0, start_tok - toknum) :]:
                yield tok
            # If we're at the end of the file, then we're done.
            assert new_filepos <= self._eofpos
            if new_filepos == self._eofpos:
                break
            # Update our indices
            toknum += num_toks
            filepos = new_filepos

        # If we reach this point, then we should know our length.
        assert self._len is not None
        # Enforce closing of stream once we reached end of file
        # We should have reached EOF once we're out of the while loop.
        self.close()

    # Use concat for these, so we can use a ConcatenatedCorpusView
    # when possible.
    def __add__(self, other):
        return concat([self, other])

    def __radd__(self, other):
        return concat([other, self])

    def __mul__(self, count):
        return concat([self] * count)

    def __rmul__(self, count):
        return concat([self] * count)


class ConcatenatedCorpusView(AbstractLazySequence):
    """
    A 'view' of a corpus file that joins together one or more
    ``StreamBackedCorpusViews<StreamBackedCorpusView>``.  At most
    one file handle is left open at any time.
    """

    def __init__(self, corpus_views):
        self._pieces = corpus_views
        """A list of the corpus subviews that make up this
        concatenation."""

        self._offsets = [0]
        """A list of offsets, indicating the index at which each
        subview begins.  In particular::
            offsets[i] = sum([len(p) for p in pieces[:i]])"""

        self._open_piece = None
        """The most recently accessed corpus subview (or None).
        Before a new subview is accessed, this subview will be closed."""

    def __len__(self):
        if len(self._offsets) <= len(self._pieces):
            # Iterate to the end of the corpus.
            for tok in self.iterate_from(self._offsets[-1]):
                pass

        return self._offsets[-1]

    def close(self):
        for piece in self._pieces:
            piece.close()

    def iterate_from(self, start_tok):
        piecenum = bisect.bisect_right(self._offsets, start_tok) - 1

        while piecenum < len(self._pieces):
            offset = self._offsets[piecenum]
            piece = self._pieces[piecenum]

            # If we've got another piece open, close it first.
            if self._open_piece is not piece:
                if self._open_piece is not None:
                    self._open_piece.close()
                self._open_piece = piece

            # Get everything we can from this piece.
            yield from piece.iterate_from(max(0, start_tok - offset))

            # Update the offset table.
            if piecenum + 1 == len(self._offsets):
                self._offsets.append(self._offsets[-1] + len(piece))

            # Move on to the next piece.
            piecenum += 1


def concat(docs):
    """
    Concatenate together the contents of multiple documents from a
    single corpus, using an appropriate concatenation function.  This
    utility function is used by corpus readers when the user requests
    more than one document at a time.
    """
    if len(docs) == 1:
        return docs[0]
    if len(docs) == 0:
        raise ValueError("concat() expects at least one object!")

    types = {d.__class__ for d in docs}

    # If they're all strings, use string concatenation.
    if all(isinstance(doc, str) for doc in docs):
        return "".join(docs)

    # If they're all corpus views, then use ConcatenatedCorpusView.
    for typ in types:
        if not issubclass(typ, (StreamBackedCorpusView, ConcatenatedCorpusView)):
            break
    else:
        return ConcatenatedCorpusView(docs)

    # If they're all lazy sequences, use a lazy concatenation
    for typ in types:
        if not issubclass(typ, AbstractLazySequence):
            break
    else:
        return LazyConcatenation(docs)

    # Otherwise, see what we can do:
    if len(types) == 1:
        typ = list(types)[0]

        if issubclass(typ, list):
            return reduce((lambda a, b: a + b), docs, [])

        if issubclass(typ, tuple):
            return reduce((lambda a, b: a + b), docs, ())

        if ElementTree.iselement(typ):
            xmltree = ElementTree.Element("documents")
            for doc in docs:
                xmltree.append(doc)
            return xmltree

    # No method found!
    raise ValueError("Don't know how to concatenate types: %r" % types)


######################################################################
# { Block Readers
######################################################################


def read_whitespace_block(stream):
    toks = []
    for i in range(20):  # Read 20 lines at a time.
        toks.extend(stream.readline().split())
    return toks


def read_wordpunct_block(stream):
    toks = []
    for i in range(20):  # Read 20 lines at a time.
        toks.extend(wordpunct_tokenize(stream.readline()))
    return toks


def read_line_block(stream):
    toks = []
    for i in range(20):
        line = stream.readline()
        if not line:
            return toks
        toks.append(line.rstrip("\n"))
    return toks


def read_blankline_block(stream):
    s = ""
    while True:
        line = stream.readline()
        # End of file:
        if not line:
            if s:
                return [s]
            else:
                return []
        # Blank line:
        elif line and not line.strip():
            if s:
                return [s]
        # Other line:
        else:
            s += line


def read_alignedsent_block(stream):
    s = ""
    while True:
        line = stream.readline()
        if line[0] == "=" or line[0] == "\n" or line[:2] == "\r\n":
            continue
        # End of file:
        if not line:
            if s:
                return [s]
            else:
                return []
        # Other line:
        else:
            s += line
            if re.match(r"^\d+-\d+", line) is not None:
                return [s]


def read_regexp_block(stream, start_re, end_re=None):
    """
    Read a sequence of tokens from a stream, where tokens begin with
    lines that match ``start_re``.  If ``end_re`` is specified, then
    tokens end with lines that match ``end_re``; otherwise, tokens end
    whenever the next line matching ``start_re`` or EOF is found.
    """
    # Scan until we find a line matching the start regexp.
    while True:
        line = stream.readline()
        if not line:
            return []  # end of file.
        if re.match(start_re, line):
            break

    # Scan until we find another line matching the regexp, or EOF.
    lines = [line]
    while True:
        oldpos = stream.tell()
        line = stream.readline()
        # End of file:
        if not line:
            return ["".join(lines)]
        # End of token:
        if end_re is not None and re.match(end_re, line):
            return ["".join(lines)]
        # Start of new token: backup to just before it starts, and
        # return the token we've already collected.
        if end_re is None and re.match(start_re, line):
            stream.seek(oldpos)
            return ["".join(lines)]
        # Anything else is part of the token.
        lines.append(line)


def read_sexpr_block(stream, block_size=16384, comment_char=None):
    """
    Read a sequence of s-expressions from the stream, and leave the
    stream's file position at the end the last complete s-expression
    read.  This function will always return at least one s-expression,
    unless there are no more s-expressions in the file.

    If the file ends in in the middle of an s-expression, then that
    incomplete s-expression is returned when the end of the file is
    reached.

    :param block_size: The default block size for reading.  If an
        s-expression is longer than one block, then more than one
        block will be read.
    :param comment_char: A character that marks comments.  Any lines
        that begin with this character will be stripped out.
        (If spaces or tabs precede the comment character, then the
        line will not be stripped.)
    """
    start = stream.tell()
    block = stream.read(block_size)
    encoding = getattr(stream, "encoding", None)
    assert encoding is not None or isinstance(block, str)
    if encoding not in (None, "utf-8"):
        import warnings

        warnings.warn(
            "Parsing may fail, depending on the properties "
            "of the %s encoding!" % encoding
        )
        # (e.g., the utf-16 encoding does not work because it insists
        # on adding BOMs to the beginning of encoded strings.)

    if comment_char:
        COMMENT = re.compile("(?m)^%s.*$" % re.escape(comment_char))
    while True:
        try:
            # If we're stripping comments, then make sure our block ends
            # on a line boundary; and then replace any comments with
            # space characters.  (We can't just strip them out -- that
            # would make our offset wrong.)
            if comment_char:
                block += stream.readline()
                block = re.sub(COMMENT, _sub_space, block)
            # Read the block.
            tokens, offset = _parse_sexpr_block(block)
            # Skip whitespace
            offset = re.compile(r"\s*").search(block, offset).end()

            # Move to the end position.
            if encoding is None:
                stream.seek(start + offset)
            else:
                stream.seek(start + len(block[:offset].encode(encoding)))

            # Return the list of tokens we processed
            return tokens
        except ValueError as e:
            if e.args[0] == "Block too small":
                next_block = stream.read(block_size)
                if next_block:
                    block += next_block
                    continue
                else:
                    # The file ended mid-sexpr -- return what we got.
                    return [block.strip()]
            else:
                raise


def _sub_space(m):
    """Helper function: given a regexp match, return a string of
    spaces that's the same length as the matched string."""
    return " " * (m.end() - m.start())


def _parse_sexpr_block(block):
    tokens = []
    start = end = 0

    while end < len(block):
        m = re.compile(r"\S").search(block, end)
        if not m:
            return tokens, end

        start = m.start()

        # Case 1: sexpr is not parenthesized.
        if m.group() != "(":
            m2 = re.compile(r"[\s(]").search(block, start)
            if m2:
                end = m2.start()
            else:
                if tokens:
                    return tokens, end
                raise ValueError("Block too small")

        # Case 2: parenthesized sexpr.
        else:
            nesting = 0
            for m in re.compile(r"[()]").finditer(block, start):
                if m.group() == "(":
                    nesting += 1
                else:
                    nesting -= 1
                if nesting == 0:
                    end = m.end()
                    break
            else:
                if tokens:
                    return tokens, end
                raise ValueError("Block too small")

        tokens.append(block[start:end])

    return tokens, end


######################################################################
# { Finding Corpus Items
######################################################################


def find_corpus_fileids(root, regexp):
    if not isinstance(root, PathPointer):
        raise TypeError("find_corpus_fileids: expected a PathPointer")
    regexp += "$"

    # Find fileids in a zipfile: scan the zipfile's namelist.  Filter
    # out entries that end in '/' -- they're directories.
    if isinstance(root, ZipFilePathPointer):
        fileids = [
            name[len(root.entry) :]
            for name in root.zipfile.namelist()
            if not name.endswith("/")
        ]
        items = [name for name in fileids if re.match(regexp, name)]
        return sorted(items)

    # Find fileids in a directory: use os.walk to search all (proper
    # or symlinked) subdirectories, and match paths against the regexp.
    elif isinstance(root, FileSystemPathPointer):
        items = []
        for dirname, subdirs, fileids in os.walk(root.path):
            prefix = "".join("%s/" % p for p in _path_from(root.path, dirname))
            items += [
                prefix + fileid
                for fileid in fileids
                if re.match(regexp, prefix + fileid)
            ]
            # Don't visit svn directories:
            if ".svn" in subdirs:
                subdirs.remove(".svn")
        return sorted(items)

    else:
        raise AssertionError("Don't know how to handle %r" % root)


def _path_from(parent, child):
    if os.path.split(parent)[1] == "":
        parent = os.path.split(parent)[0]
    path = []
    while parent != child:
        child, dirname = os.path.split(child)
        path.insert(0, dirname)
        assert os.path.split(child)[0] != child
    return path


######################################################################
# { Paragraph structure in Treebank files
######################################################################


def tagged_treebank_para_block_reader(stream):
    # Read the next paragraph.
    para = ""
    while True:
        line = stream.readline()
        # End of paragraph:
        if re.match(r"======+\s*$", line):
            if para.strip():
                return [para]
        # End of file:
        elif line == "":
            if para.strip():
                return [para]
            else:
                return []
        # Content line:
        else:
            para += line

# === NexusCore/openenv\Lib\site-packages\setuptools\config\setupcfg.py ===
"""
Load setuptools configuration from ``setup.cfg`` files.

**API will be made private in the future**

To read project metadata, consider using
``build.util.project_wheel_metadata`` (https://pypi.org/project/build/).
For simple scenarios, you can also try parsing the file directly
with the help of ``configparser``.
"""

from __future__ import annotations

import contextlib
import functools
import os
from collections import defaultdict
from collections.abc import Iterable, Iterator
from functools import partial, wraps
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Generic, TypeVar, cast

from packaging.markers import default_environment as marker_env
from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import InvalidVersion, Version

from .. import _static
from .._path import StrPath
from ..errors import FileError, OptionError
from ..warnings import SetuptoolsDeprecationWarning
from . import expand

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from setuptools.dist import Distribution

    from distutils.dist import DistributionMetadata

SingleCommandOptions: TypeAlias = dict[str, tuple[str, Any]]
"""Dict that associate the name of the options of a particular command to a
tuple. The first element of the tuple indicates the origin of the option value
(e.g. the name of the configuration file where it was read from),
while the second element of the tuple is the option value itself
"""
AllCommandOptions: TypeAlias = dict[str, SingleCommandOptions]
"""cmd name => its options"""
Target = TypeVar("Target", "Distribution", "DistributionMetadata")


def read_configuration(
    filepath: StrPath, find_others: bool = False, ignore_option_errors: bool = False
) -> dict:
    """Read given configuration file and returns options from it as a dict.

    :param str|unicode filepath: Path to configuration file
        to get options from.

    :param bool find_others: Whether to search for other configuration files
        which could be on in various places.

    :param bool ignore_option_errors: Whether to silently ignore
        options, values of which could not be resolved (e.g. due to exceptions
        in directives such as file:, attr:, etc.).
        If False exceptions are propagated as expected.

    :rtype: dict
    """
    from setuptools.dist import Distribution

    dist = Distribution()
    filenames = dist.find_config_files() if find_others else []
    handlers = _apply(dist, filepath, filenames, ignore_option_errors)
    return configuration_to_dict(handlers)


def apply_configuration(dist: Distribution, filepath: StrPath) -> Distribution:
    """Apply the configuration from a ``setup.cfg`` file into an existing
    distribution object.
    """
    _apply(dist, filepath)
    dist._finalize_requires()
    return dist


def _apply(
    dist: Distribution,
    filepath: StrPath,
    other_files: Iterable[StrPath] = (),
    ignore_option_errors: bool = False,
) -> tuple[ConfigMetadataHandler, ConfigOptionsHandler]:
    """Read configuration from ``filepath`` and applies to the ``dist`` object."""
    from setuptools.dist import _Distribution

    filepath = os.path.abspath(filepath)

    if not os.path.isfile(filepath):
        raise FileError(f'Configuration file {filepath} does not exist.')

    current_directory = os.getcwd()
    os.chdir(os.path.dirname(filepath))
    filenames = [*other_files, filepath]

    try:
        # TODO: Temporary cast until mypy 1.12 is released with upstream fixes from typeshed
        _Distribution.parse_config_files(dist, filenames=cast(list[str], filenames))
        handlers = parse_configuration(
            dist, dist.command_options, ignore_option_errors=ignore_option_errors
        )
        dist._finalize_license_files()
    finally:
        os.chdir(current_directory)

    return handlers


def _get_option(target_obj: Distribution | DistributionMetadata, key: str):
    """
    Given a target object and option key, get that option from
    the target object, either through a get_{key} method or
    from an attribute directly.
    """
    getter_name = f'get_{key}'
    by_attribute = functools.partial(getattr, target_obj, key)
    getter = getattr(target_obj, getter_name, by_attribute)
    return getter()


def configuration_to_dict(
    handlers: Iterable[
        ConfigHandler[Distribution] | ConfigHandler[DistributionMetadata]
    ],
) -> dict:
    """Returns configuration data gathered by given handlers as a dict.

    :param Iterable[ConfigHandler] handlers: Handlers list,
        usually from parse_configuration()

    :rtype: dict
    """
    config_dict: dict = defaultdict(dict)

    for handler in handlers:
        for option in handler.set_options:
            value = _get_option(handler.target_obj, option)
            config_dict[handler.section_prefix][option] = value

    return config_dict


def parse_configuration(
    distribution: Distribution,
    command_options: AllCommandOptions,
    ignore_option_errors: bool = False,
) -> tuple[ConfigMetadataHandler, ConfigOptionsHandler]:
    """Performs additional parsing of configuration options
    for a distribution.

    Returns a list of used option handlers.

    :param Distribution distribution:
    :param dict command_options:
    :param bool ignore_option_errors: Whether to silently ignore
        options, values of which could not be resolved (e.g. due to exceptions
        in directives such as file:, attr:, etc.).
        If False exceptions are propagated as expected.
    :rtype: list
    """
    with expand.EnsurePackagesDiscovered(distribution) as ensure_discovered:
        options = ConfigOptionsHandler(
            distribution,
            command_options,
            ignore_option_errors,
            ensure_discovered,
        )

        options.parse()
        if not distribution.package_dir:
            distribution.package_dir = options.package_dir  # Filled by `find_packages`

        meta = ConfigMetadataHandler(
            distribution.metadata,
            command_options,
            ignore_option_errors,
            ensure_discovered,
            distribution.package_dir,
            distribution.src_root,
        )
        meta.parse()
        distribution._referenced_files.update(
            options._referenced_files, meta._referenced_files
        )

    return meta, options


def _warn_accidental_env_marker_misconfig(label: str, orig_value: str, parsed: list):
    """Because users sometimes misinterpret this configuration:

    [options.extras_require]
    foo = bar;python_version<"4"

    It looks like one requirement with an environment marker
    but because there is no newline, it's parsed as two requirements
    with a semicolon as separator.

    Therefore, if:
        * input string does not contain a newline AND
        * parsed result contains two requirements AND
        * parsing of the two parts from the result ("<first>;<second>")
        leads in a valid Requirement with a valid marker
    a UserWarning is shown to inform the user about the possible problem.
    """
    if "\n" in orig_value or len(parsed) != 2:
        return

    markers = marker_env().keys()

    try:
        req = Requirement(parsed[1])
        if req.name in markers:
            _AmbiguousMarker.emit(field=label, req=parsed[1])
    except InvalidRequirement as ex:
        if any(parsed[1].startswith(marker) for marker in markers):
            msg = _AmbiguousMarker.message(field=label, req=parsed[1])
            raise InvalidRequirement(msg) from ex


class ConfigHandler(Generic[Target]):
    """Handles metadata supplied in configuration files."""

    section_prefix: str
    """Prefix for config sections handled by this handler.
    Must be provided by class heirs.

    """

    aliases: ClassVar[dict[str, str]] = {}
    """Options aliases.
    For compatibility with various packages. E.g.: d2to1 and pbr.
    Note: `-` in keys is replaced with `_` by config parser.

    """

    def __init__(
        self,
        target_obj: Target,
        options: AllCommandOptions,
        ignore_option_errors,
        ensure_discovered: expand.EnsurePackagesDiscovered,
    ) -> None:
        self.ignore_option_errors = ignore_option_errors
        self.target_obj: Target = target_obj
        self.sections = dict(self._section_options(options))
        self.set_options: list[str] = []
        self.ensure_discovered = ensure_discovered
        self._referenced_files = set[str]()
        """After parsing configurations, this property will enumerate
        all files referenced by the "file:" directive. Private API for setuptools only.
        """

    @classmethod
    def _section_options(
        cls, options: AllCommandOptions
    ) -> Iterator[tuple[str, SingleCommandOptions]]:
        for full_name, value in options.items():
            pre, _sep, name = full_name.partition(cls.section_prefix)
            if pre:
                continue
            yield name.lstrip('.'), value

    @property
    def parsers(self):
        """Metadata item name to parser function mapping."""
        raise NotImplementedError(
            f'{self.__class__.__name__} must provide .parsers property'
        )

    def __setitem__(self, option_name, value) -> None:
        target_obj = self.target_obj

        # Translate alias into real name.
        option_name = self.aliases.get(option_name, option_name)

        try:
            current_value = getattr(target_obj, option_name)
        except AttributeError as e:
            raise KeyError(option_name) from e

        if current_value:
            # Already inhabited. Skipping.
            return

        try:
            parsed = self.parsers.get(option_name, lambda x: x)(value)
        except (Exception,) * self.ignore_option_errors:
            return

        simple_setter = functools.partial(target_obj.__setattr__, option_name)
        setter = getattr(target_obj, f"set_{option_name}", simple_setter)
        setter(parsed)

        self.set_options.append(option_name)

    @classmethod
    def _parse_list(cls, value, separator=','):
        """Represents value as a list.

        Value is split either by separator (defaults to comma) or by lines.

        :param value:
        :param separator: List items separator character.
        :rtype: list
        """
        if isinstance(value, list):  # _get_parser_compound case
            return value

        if '\n' in value:
            value = value.splitlines()
        else:
            value = value.split(separator)

        return [chunk.strip() for chunk in value if chunk.strip()]

    @classmethod
    def _parse_dict(cls, value):
        """Represents value as a dict.

        :param value:
        :rtype: dict
        """
        separator = '='
        result = {}
        for line in cls._parse_list(value):
            key, sep, val = line.partition(separator)
            if sep != separator:
                raise OptionError(f"Unable to parse option value to dict: {value}")
            result[key.strip()] = val.strip()

        return result

    @classmethod
    def _parse_bool(cls, value):
        """Represents value as boolean.

        :param value:
        :rtype: bool
        """
        value = value.lower()
        return value in ('1', 'true', 'yes')

    @classmethod
    def _exclude_files_parser(cls, key):
        """Returns a parser function to make sure field inputs
        are not files.

        Parses a value after getting the key so error messages are
        more informative.

        :param key:
        :rtype: callable
        """

        def parser(value):
            exclude_directive = 'file:'
            if value.startswith(exclude_directive):
                raise ValueError(
                    f'Only strings are accepted for the {key} field, '
                    'files are not accepted'
                )
            return _static.Str(value)

        return parser

    def _parse_file(self, value, root_dir: StrPath | None):
        """Represents value as a string, allowing including text
        from nearest files using `file:` directive.

        Directive is sandboxed and won't reach anything outside
        directory with setup.py.

        Examples:
            file: README.rst, CHANGELOG.md, src/file.txt

        :param str value:
        :rtype: str
        """
        include_directive = 'file:'

        if not isinstance(value, str):
            return value

        if not value.startswith(include_directive):
            return _static.Str(value)

        spec = value[len(include_directive) :]
        filepaths = [path.strip() for path in spec.split(',')]
        self._referenced_files.update(filepaths)
        # XXX: Is marking as static contents coming from files too optimistic?
        return _static.Str(expand.read_files(filepaths, root_dir))

    def _parse_attr(self, value, package_dir, root_dir: StrPath):
        """Represents value as a module attribute.

        Examples:
            attr: package.attr
            attr: package.module.attr

        :param str value:
        :rtype: str
        """
        attr_directive = 'attr:'
        if not value.startswith(attr_directive):
            return _static.Str(value)

        attr_desc = value.replace(attr_directive, '')

        # Make sure package_dir is populated correctly, so `attr:` directives can work
        package_dir.update(self.ensure_discovered.package_dir)
        return expand.read_attr(attr_desc, package_dir, root_dir)

    @classmethod
    def _get_parser_compound(cls, *parse_methods):
        """Returns parser function to represents value as a list.

        Parses a value applying given methods one after another.

        :param parse_methods:
        :rtype: callable
        """

        def parse(value):
            parsed = value

            for method in parse_methods:
                parsed = method(parsed)

            return parsed

        return parse

    @classmethod
    def _parse_section_to_dict_with_key(cls, section_options, values_parser):
        """Parses section options into a dictionary.

        Applies a given parser to each option in a section.

        :param dict section_options:
        :param callable values_parser: function with 2 args corresponding to key, value
        :rtype: dict
        """
        value = {}
        for key, (_, val) in section_options.items():
            value[key] = values_parser(key, val)
        return value

    @classmethod
    def _parse_section_to_dict(cls, section_options, values_parser=None):
        """Parses section options into a dictionary.

        Optionally applies a given parser to each value.

        :param dict section_options:
        :param callable values_parser: function with 1 arg corresponding to option value
        :rtype: dict
        """
        parser = (lambda _, v: values_parser(v)) if values_parser else (lambda _, v: v)
        return cls._parse_section_to_dict_with_key(section_options, parser)

    def parse_section(self, section_options) -> None:
        """Parses configuration file section.

        :param dict section_options:
        """
        for name, (_, value) in section_options.items():
            with contextlib.suppress(KeyError):
                # Keep silent for a new option may appear anytime.
                self[name] = value

    def parse(self) -> None:
        """Parses configuration file items from one
        or more related sections.

        """
        for section_name, section_options in self.sections.items():
            method_postfix = ''
            if section_name:  # [section.option] variant
                method_postfix = f"_{section_name}"

            section_parser_method: Callable | None = getattr(
                self,
                # Dots in section names are translated into dunderscores.
                f'parse_section{method_postfix}'.replace('.', '__'),
                None,
            )

            if section_parser_method is None:
                raise OptionError(
                    "Unsupported distribution option section: "
                    f"[{self.section_prefix}.{section_name}]"
                )

            section_parser_method(section_options)

    def _deprecated_config_handler(self, func, msg, **kw):
        """this function will wrap around parameters that are deprecated

        :param msg: deprecation message
        :param func: function to be wrapped around
        """

        @wraps(func)
        def config_handler(*args, **kwargs):
            kw.setdefault("stacklevel", 2)
            _DeprecatedConfig.emit("Deprecated config in `setup.cfg`", msg, **kw)
            return func(*args, **kwargs)

        return config_handler


class ConfigMetadataHandler(ConfigHandler["DistributionMetadata"]):
    section_prefix = 'metadata'

    aliases = {
        'home_page': 'url',
        'summary': 'description',
        'classifier': 'classifiers',
        'platform': 'platforms',
    }

    strict_mode = False
    """We need to keep it loose, to be partially compatible with
    `pbr` and `d2to1` packages which also uses `metadata` section.

    """

    def __init__(
        self,
        target_obj: DistributionMetadata,
        options: AllCommandOptions,
        ignore_option_errors: bool,
        ensure_discovered: expand.EnsurePackagesDiscovered,
        package_dir: dict | None = None,
        root_dir: StrPath | None = os.curdir,
    ) -> None:
        super().__init__(target_obj, options, ignore_option_errors, ensure_discovered)
        self.package_dir = package_dir
        self.root_dir = root_dir

    @property
    def parsers(self):
        """Metadata item name to parser function mapping."""
        parse_list_static = self._get_parser_compound(self._parse_list, _static.List)
        parse_dict_static = self._get_parser_compound(self._parse_dict, _static.Dict)
        parse_file = partial(self._parse_file, root_dir=self.root_dir)
        exclude_files_parser = self._exclude_files_parser

        return {
            'author': _static.Str,
            'author_email': _static.Str,
            'maintainer': _static.Str,
            'maintainer_email': _static.Str,
            'platforms': parse_list_static,
            'keywords': parse_list_static,
            'provides': parse_list_static,
            'obsoletes': parse_list_static,
            'classifiers': self._get_parser_compound(parse_file, parse_list_static),
            'license': exclude_files_parser('license'),
            'license_files': parse_list_static,
            'description': parse_file,
            'long_description': parse_file,
            'long_description_content_type': _static.Str,
            'version': self._parse_version,  # Cannot be marked as dynamic
            'url': _static.Str,
            'project_urls': parse_dict_static,
        }

    def _parse_version(self, value):
        """Parses `version` option value.

        :param value:
        :rtype: str

        """
        version = self._parse_file(value, self.root_dir)

        if version != value:
            version = version.strip()
            # Be strict about versions loaded from file because it's easy to
            # accidentally include newlines and other unintended content
            try:
                Version(version)
            except InvalidVersion as e:
                raise OptionError(
                    f'Version loaded from {value} does not '
                    f'comply with PEP 440: {version}'
                ) from e

            return version

        return expand.version(self._parse_attr(value, self.package_dir, self.root_dir))


class ConfigOptionsHandler(ConfigHandler["Distribution"]):
    section_prefix = 'options'

    def __init__(
        self,
        target_obj: Distribution,
        options: AllCommandOptions,
        ignore_option_errors: bool,
        ensure_discovered: expand.EnsurePackagesDiscovered,
    ) -> None:
        super().__init__(target_obj, options, ignore_option_errors, ensure_discovered)
        self.root_dir = target_obj.src_root
        self.package_dir: dict[str, str] = {}  # To be filled by `find_packages`

    @classmethod
    def _parse_list_semicolon(cls, value):
        return cls._parse_list(value, separator=';')

    def _parse_file_in_root(self, value):
        return self._parse_file(value, root_dir=self.root_dir)

    def _parse_requirements_list(self, label: str, value: str):
        # Parse a requirements list, either by reading in a `file:`, or a list.
        parsed = self._parse_list_semicolon(self._parse_file_in_root(value))
        _warn_accidental_env_marker_misconfig(label, value, parsed)
        # Filter it to only include lines that are not comments. `parse_list`
        # will have stripped each line and filtered out empties.
        return _static.List(line for line in parsed if not line.startswith("#"))
        # ^-- Use `_static.List` to mark a non-`Dynamic` Core Metadata

    @property
    def parsers(self):
        """Metadata item name to parser function mapping."""
        parse_list = self._parse_list
        parse_bool = self._parse_bool
        parse_cmdclass = self._parse_cmdclass

        return {
            'zip_safe': parse_bool,
            'include_package_data': parse_bool,
            'package_dir': self._parse_dict,
            'scripts': parse_list,
            'eager_resources': parse_list,
            'dependency_links': parse_list,
            'namespace_packages': self._deprecated_config_handler(
                parse_list,
                "The namespace_packages parameter is deprecated, "
                "consider using implicit namespaces instead (PEP 420).",
                # TODO: define due date, see setuptools.dist:check_nsp.
            ),
            'install_requires': partial(  # Core Metadata
                self._parse_requirements_list, "install_requires"
            ),
            'setup_requires': self._parse_list_semicolon,
            'packages': self._parse_packages,
            'entry_points': self._parse_file_in_root,
            'py_modules': parse_list,
            'python_requires': _static.SpecifierSet,  # Core Metadata
            'cmdclass': parse_cmdclass,
        }

    def _parse_cmdclass(self, value):
        package_dir = self.ensure_discovered.package_dir
        return expand.cmdclass(self._parse_dict(value), package_dir, self.root_dir)

    def _parse_packages(self, value):
        """Parses `packages` option value.

        :param value:
        :rtype: list
        """
        find_directives = ['find:', 'find_namespace:']
        trimmed_value = value.strip()

        if trimmed_value not in find_directives:
            return self._parse_list(value)

        # Read function arguments from a dedicated section.
        find_kwargs = self.parse_section_packages__find(
            self.sections.get('packages.find', {})
        )

        find_kwargs.update(
            namespaces=(trimmed_value == find_directives[1]),
            root_dir=self.root_dir,
            fill_package_dir=self.package_dir,
        )

        return expand.find_packages(**find_kwargs)

    def parse_section_packages__find(self, section_options):
        """Parses `packages.find` configuration file section.

        To be used in conjunction with _parse_packages().

        :param dict section_options:
        """
        section_data = self._parse_section_to_dict(section_options, self._parse_list)

        valid_keys = ['where', 'include', 'exclude']
        find_kwargs = {k: v for k, v in section_data.items() if k in valid_keys and v}

        where = find_kwargs.get('where')
        if where is not None:
            find_kwargs['where'] = where[0]  # cast list to single val

        return find_kwargs

    def parse_section_entry_points(self, section_options) -> None:
        """Parses `entry_points` configuration file section.

        :param dict section_options:
        """
        parsed = self._parse_section_to_dict(section_options, self._parse_list)
        self['entry_points'] = parsed

    def _parse_package_data(self, section_options):
        package_data = self._parse_section_to_dict(section_options, self._parse_list)
        return expand.canonic_package_data(package_data)

    def parse_section_package_data(self, section_options) -> None:
        """Parses `package_data` configuration file section.

        :param dict section_options:
        """
        self['package_data'] = self._parse_package_data(section_options)

    def parse_section_exclude_package_data(self, section_options) -> None:
        """Parses `exclude_package_data` configuration file section.

        :param dict section_options:
        """
        self['exclude_package_data'] = self._parse_package_data(section_options)

    def parse_section_extras_require(self, section_options) -> None:  # Core Metadata
        """Parses `extras_require` configuration file section.

        :param dict section_options:
        """
        parsed = self._parse_section_to_dict_with_key(
            section_options,
            lambda k, v: self._parse_requirements_list(f"extras_require[{k}]", v),
        )

        self['extras_require'] = _static.Dict(parsed)
        # ^-- Use `_static.Dict` to mark a non-`Dynamic` Core Metadata

    def parse_section_data_files(self, section_options) -> None:
        """Parses `data_files` configuration file section.

        :param dict section_options:
        """
        parsed = self._parse_section_to_dict(section_options, self._parse_list)
        self['data_files'] = expand.canonic_data_files(parsed, self.root_dir)


class _AmbiguousMarker(SetuptoolsDeprecationWarning):
    _SUMMARY = "Ambiguous requirement marker."
    _DETAILS = """
    One of the parsed requirements in `{field}` looks like a valid environment marker:

        {req!r}

    Please make sure that the configuration file is correct.
    You can use dangling lines to avoid this problem.
    """
    _SEE_DOCS = "userguide/declarative_config.html#opt-2"
    # TODO: should we include due_date here? Initially introduced in 6 Aug 2022.
    # Does this make sense with latest version of packaging?

    @classmethod
    def message(cls, **kw):
        docs = f"https://setuptools.pypa.io/en/latest/{cls._SEE_DOCS}"
        return cls._format(cls._SUMMARY, cls._DETAILS, see_url=docs, format_args=kw)


class _DeprecatedConfig(SetuptoolsDeprecationWarning):
    _SEE_DOCS = "userguide/declarative_config.html"

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\test_tgrep.py ===
#!/usr/bin/env python
#
# Natural Language Toolkit: TGrep search
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Will Roberts <wildwilhelm@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Unit tests for nltk.tgrep.
"""


import unittest

from nltk import tgrep
from nltk.tree import ParentedTree


class TestSequenceFunctions(unittest.TestCase):
    """
    Class containing unit tests for nltk.tgrep.
    """

    def test_tokenize_simple(self):
        """
        Simple test of tokenization.
        """
        tokens = tgrep.tgrep_tokenize("A .. (B !< C . D) | ![<< (E , F) $ G]")
        self.assertEqual(
            tokens,
            [
                "A",
                "..",
                "(",
                "B",
                "!",
                "<",
                "C",
                ".",
                "D",
                ")",
                "|",
                "!",
                "[",
                "<<",
                "(",
                "E",
                ",",
                "F",
                ")",
                "$",
                "G",
                "]",
            ],
        )

    def test_tokenize_encoding(self):
        """
        Test that tokenization handles bytes and strs the same way.
        """
        self.assertEqual(
            tgrep.tgrep_tokenize(b"A .. (B !< C . D) | ![<< (E , F) $ G]"),
            tgrep.tgrep_tokenize("A .. (B !< C . D) | ![<< (E , F) $ G]"),
        )

    def test_tokenize_link_types(self):
        """
        Test tokenization of basic link types.
        """
        self.assertEqual(tgrep.tgrep_tokenize("A<B"), ["A", "<", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A>B"), ["A", ">", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A<3B"), ["A", "<3", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A>3B"), ["A", ">3", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A<,B"), ["A", "<,", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A>,B"), ["A", ">,", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A<-3B"), ["A", "<-3", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A>-3B"), ["A", ">-3", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A<-B"), ["A", "<-", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A>-B"), ["A", ">-", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A<'B"), ["A", "<'", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A>'B"), ["A", ">'", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A<:B"), ["A", "<:", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A>:B"), ["A", ">:", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A<<B"), ["A", "<<", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A>>B"), ["A", ">>", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A<<,B"), ["A", "<<,", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A>>,B"), ["A", ">>,", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A<<'B"), ["A", "<<'", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A>>'B"), ["A", ">>'", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A<<:B"), ["A", "<<:", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A>>:B"), ["A", ">>:", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A.B"), ["A", ".", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A,B"), ["A", ",", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A..B"), ["A", "..", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A,,B"), ["A", ",,", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A$B"), ["A", "$", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A$.B"), ["A", "$.", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A$,B"), ["A", "$,", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A$..B"), ["A", "$..", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A$,,B"), ["A", "$,,", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!<B"), ["A", "!", "<", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!>B"), ["A", "!", ">", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!<3B"), ["A", "!", "<3", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!>3B"), ["A", "!", ">3", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!<,B"), ["A", "!", "<,", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!>,B"), ["A", "!", ">,", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!<-3B"), ["A", "!", "<-3", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!>-3B"), ["A", "!", ">-3", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!<-B"), ["A", "!", "<-", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!>-B"), ["A", "!", ">-", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!<'B"), ["A", "!", "<'", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!>'B"), ["A", "!", ">'", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!<:B"), ["A", "!", "<:", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!>:B"), ["A", "!", ">:", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!<<B"), ["A", "!", "<<", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!>>B"), ["A", "!", ">>", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!<<,B"), ["A", "!", "<<,", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!>>,B"), ["A", "!", ">>,", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!<<'B"), ["A", "!", "<<'", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!>>'B"), ["A", "!", ">>'", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!<<:B"), ["A", "!", "<<:", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!>>:B"), ["A", "!", ">>:", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!.B"), ["A", "!", ".", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!,B"), ["A", "!", ",", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!..B"), ["A", "!", "..", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!,,B"), ["A", "!", ",,", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!$B"), ["A", "!", "$", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!$.B"), ["A", "!", "$.", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!$,B"), ["A", "!", "$,", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!$..B"), ["A", "!", "$..", "B"])
        self.assertEqual(tgrep.tgrep_tokenize("A!$,,B"), ["A", "!", "$,,", "B"])

    def test_tokenize_examples(self):
        """
        Test tokenization of the TGrep2 manual example patterns.
        """
        self.assertEqual(tgrep.tgrep_tokenize("NP < PP"), ["NP", "<", "PP"])
        self.assertEqual(tgrep.tgrep_tokenize("/^NP/"), ["/^NP/"])
        self.assertEqual(
            tgrep.tgrep_tokenize("NP << PP . VP"), ["NP", "<<", "PP", ".", "VP"]
        )
        self.assertEqual(
            tgrep.tgrep_tokenize("NP << PP | . VP"), ["NP", "<<", "PP", "|", ".", "VP"]
        )
        self.assertEqual(
            tgrep.tgrep_tokenize("NP !<< PP [> NP | >> VP]"),
            ["NP", "!", "<<", "PP", "[", ">", "NP", "|", ">>", "VP", "]"],
        )
        self.assertEqual(
            tgrep.tgrep_tokenize("NP << (PP . VP)"),
            ["NP", "<<", "(", "PP", ".", "VP", ")"],
        )
        self.assertEqual(
            tgrep.tgrep_tokenize("NP <' (PP <, (IN < on))"),
            ["NP", "<'", "(", "PP", "<,", "(", "IN", "<", "on", ")", ")"],
        )
        self.assertEqual(
            tgrep.tgrep_tokenize("S < (A < B) < C"),
            ["S", "<", "(", "A", "<", "B", ")", "<", "C"],
        )
        self.assertEqual(
            tgrep.tgrep_tokenize("S < ((A < B) < C)"),
            ["S", "<", "(", "(", "A", "<", "B", ")", "<", "C", ")"],
        )
        self.assertEqual(
            tgrep.tgrep_tokenize("S < (A < B < C)"),
            ["S", "<", "(", "A", "<", "B", "<", "C", ")"],
        )
        self.assertEqual(tgrep.tgrep_tokenize("A<B&.C"), ["A", "<", "B", "&", ".", "C"])

    def test_tokenize_quoting(self):
        """
        Test tokenization of quoting.
        """
        self.assertEqual(
            tgrep.tgrep_tokenize('"A<<:B"<<:"A $.. B"<"A>3B"<C'),
            ['"A<<:B"', "<<:", '"A $.. B"', "<", '"A>3B"', "<", "C"],
        )

    def test_tokenize_nodenames(self):
        """
        Test tokenization of node names.
        """
        self.assertEqual(tgrep.tgrep_tokenize("Robert"), ["Robert"])
        self.assertEqual(tgrep.tgrep_tokenize("/^[Bb]ob/"), ["/^[Bb]ob/"])
        self.assertEqual(tgrep.tgrep_tokenize("*"), ["*"])
        self.assertEqual(tgrep.tgrep_tokenize("__"), ["__"])
        # test tokenization of NLTK tree position syntax
        self.assertEqual(tgrep.tgrep_tokenize("N()"), ["N(", ")"])
        self.assertEqual(tgrep.tgrep_tokenize("N(0,)"), ["N(", "0", ",", ")"])
        self.assertEqual(tgrep.tgrep_tokenize("N(0,0)"), ["N(", "0", ",", "0", ")"])
        self.assertEqual(
            tgrep.tgrep_tokenize("N(0,0,)"), ["N(", "0", ",", "0", ",", ")"]
        )

    def test_tokenize_macros(self):
        """
        Test tokenization of macro definitions.
        """
        self.assertEqual(
            tgrep.tgrep_tokenize(
                "@ NP /^NP/;\n@ NN /^NN/;\n@NP [!< NP | < @NN] !$.. @NN"
            ),
            [
                "@",
                "NP",
                "/^NP/",
                ";",
                "@",
                "NN",
                "/^NN/",
                ";",
                "@NP",
                "[",
                "!",
                "<",
                "NP",
                "|",
                "<",
                "@NN",
                "]",
                "!",
                "$..",
                "@NN",
            ],
        )

    def test_node_simple(self):
        """
        Test a simple use of tgrep for finding nodes matching a given
        pattern.
        """
        tree = ParentedTree.fromstring(
            "(S (NP (DT the) (JJ big) (NN dog)) " "(VP bit) (NP (DT a) (NN cat)))"
        )
        self.assertEqual(list(tgrep.tgrep_positions("NN", [tree])), [[(0, 2), (2, 1)]])
        self.assertEqual(
            list(tgrep.tgrep_nodes("NN", [tree])), [[tree[0, 2], tree[2, 1]]]
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("NN|JJ", [tree])), [[(0, 1), (0, 2), (2, 1)]]
        )

    def test_node_printing(self):
        """Test that the tgrep print operator ' is properly ignored."""
        tree = ParentedTree.fromstring("(S (n x) (N x))")
        self.assertEqual(
            list(tgrep.tgrep_positions("N", [tree])),
            list(tgrep.tgrep_positions("'N", [tree])),
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("/[Nn]/", [tree])),
            list(tgrep.tgrep_positions("'/[Nn]/", [tree])),
        )

    def test_node_encoding(self):
        """
        Test that tgrep search strings handles bytes and strs the same
        way.
        """
        tree = ParentedTree.fromstring(
            "(S (NP (DT the) (JJ big) (NN dog)) " "(VP bit) (NP (DT a) (NN cat)))"
        )
        self.assertEqual(
            list(tgrep.tgrep_positions(b"NN", [tree])),
            list(tgrep.tgrep_positions(b"NN", [tree])),
        )
        self.assertEqual(
            list(tgrep.tgrep_nodes(b"NN", [tree])),
            list(tgrep.tgrep_nodes("NN", [tree])),
        )
        self.assertEqual(
            list(tgrep.tgrep_positions(b"NN|JJ", [tree])),
            list(tgrep.tgrep_positions("NN|JJ", [tree])),
        )

    def test_node_nocase(self):
        """
        Test selecting nodes using case insensitive node names.
        """
        tree = ParentedTree.fromstring("(S (n x) (N x))")
        self.assertEqual(list(tgrep.tgrep_positions('"N"', [tree])), [[(1,)]])
        self.assertEqual(list(tgrep.tgrep_positions('i@"N"', [tree])), [[(0,), (1,)]])

    def test_node_quoted(self):
        """
        Test selecting nodes using quoted node names.
        """
        tree = ParentedTree.fromstring('(N ("N" x) (N" x) ("\\" x))')
        self.assertEqual(list(tgrep.tgrep_positions('"N"', [tree])), [[()]])
        self.assertEqual(list(tgrep.tgrep_positions('"\\"N\\""', [tree])), [[(0,)]])
        self.assertEqual(list(tgrep.tgrep_positions('"N\\""', [tree])), [[(1,)]])
        self.assertEqual(list(tgrep.tgrep_positions('"\\"\\\\\\""', [tree])), [[(2,)]])

    def test_node_regex(self):
        """
        Test regex matching on nodes.
        """
        tree = ParentedTree.fromstring("(S (NP-SBJ x) (NP x) (NNP x) (VP x))")
        # This is a regular expression that matches any node whose
        # name starts with NP, including NP-SBJ:
        self.assertEqual(list(tgrep.tgrep_positions("/^NP/", [tree])), [[(0,), (1,)]])

    def test_node_regex_2(self):
        """
        Test regex matching on nodes.
        """
        tree = ParentedTree.fromstring("(S (SBJ x) (SBJ1 x) (NP-SBJ x))")
        self.assertEqual(list(tgrep.tgrep_positions("/^SBJ/", [tree])), [[(0,), (1,)]])
        # This is a regular expression that matches any node whose
        # name includes SBJ, including NP-SBJ:
        self.assertEqual(
            list(tgrep.tgrep_positions("/SBJ/", [tree])), [[(0,), (1,), (2,)]]
        )

    def test_node_tree_position(self):
        """
        Test matching on nodes based on NLTK tree position.
        """
        tree = ParentedTree.fromstring("(S (NP-SBJ x) (NP x) (NNP x) (VP x))")
        # test all tree positions that are not leaves
        leaf_positions = {tree.leaf_treeposition(x) for x in range(len(tree.leaves()))}
        tree_positions = [x for x in tree.treepositions() if x not in leaf_positions]
        for position in tree_positions:
            node_id = f"N{position}"
            tgrep_positions = list(tgrep.tgrep_positions(node_id, [tree]))
            self.assertEqual(len(tgrep_positions[0]), 1)
            self.assertEqual(tgrep_positions[0][0], position)

    def test_node_noleaves(self):
        """
        Test node name matching with the search_leaves flag set to False.
        """
        tree = ParentedTree.fromstring("(S (A (T x)) (B (N x)))")
        self.assertEqual(
            list(tgrep.tgrep_positions("x", [tree])), [[(0, 0, 0), (1, 0, 0)]]
        )
        self.assertEqual(list(tgrep.tgrep_positions("x", [tree], False)), [[]])

    def tests_rel_dominance(self):
        """
        Test matching nodes based on dominance relations.
        """
        tree = ParentedTree.fromstring("(S (A (T x)) (B (N x)))")
        self.assertEqual(list(tgrep.tgrep_positions("* < T", [tree])), [[(0,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* < T > S", [tree])), [[(0,)]])
        self.assertEqual(
            list(tgrep.tgrep_positions("* !< T", [tree])),
            [[(), (0, 0), (0, 0, 0), (1,), (1, 0), (1, 0, 0)]],
        )
        self.assertEqual(list(tgrep.tgrep_positions("* !< T > S", [tree])), [[(1,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* > A", [tree])), [[(0, 0)]])
        self.assertEqual(list(tgrep.tgrep_positions("* > B", [tree])), [[(1, 0)]])
        self.assertEqual(
            list(tgrep.tgrep_positions("* !> B", [tree])),
            [[(), (0,), (0, 0), (0, 0, 0), (1,), (1, 0, 0)]],
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* !> B >> S", [tree])), [[(0,), (0, 0), (1,)]]
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* >> S", [tree])),
            [[(0,), (0, 0), (1,), (1, 0)]],
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* >>, S", [tree])), [[(0,), (0, 0)]]
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* >>' S", [tree])), [[(1,), (1, 0)]]
        )
        # Known issue:
        # self.assertEqual(list(tgrep.tgrep_positions('* !>> S', [tree])),
        #                 [[()]])
        self.assertEqual(list(tgrep.tgrep_positions("* << T", [tree])), [[(), (0,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* <<' T", [tree])), [[(0,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* <<1 N", [tree])), [[(1,)]])
        self.assertEqual(
            list(tgrep.tgrep_positions("* !<< T", [tree])),
            [[(0, 0), (0, 0, 0), (1,), (1, 0), (1, 0, 0)]],
        )
        tree = ParentedTree.fromstring("(S (A (T x)) (B (T x) (N x )))")
        self.assertEqual(list(tgrep.tgrep_positions("* <: T", [tree])), [[(0,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* < T", [tree])), [[(0,), (1,)]])
        self.assertEqual(
            list(tgrep.tgrep_positions("* !<: T", [tree])),
            [[(), (0, 0), (0, 0, 0), (1,), (1, 0), (1, 0, 0), (1, 1), (1, 1, 0)]],
        )
        self.assertEqual(list(tgrep.tgrep_positions("* !<: T > S", [tree])), [[(1,)]])
        tree = ParentedTree.fromstring("(S (T (A x) (B x)) (T (C x)))")
        self.assertEqual(list(tgrep.tgrep_positions("* >: T", [tree])), [[(1, 0)]])
        self.assertEqual(
            list(tgrep.tgrep_positions("* !>: T", [tree])),
            [[(), (0,), (0, 0), (0, 0, 0), (0, 1), (0, 1, 0), (1,), (1, 0, 0)]],
        )
        tree = ParentedTree.fromstring(
            "(S (A (B (C (D (E (T x))))))" " (A (B (C (D (E (T x))) (N x)))))"
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* <<: T", [tree])),
            [
                [
                    (0,),
                    (0, 0),
                    (0, 0, 0),
                    (0, 0, 0, 0),
                    (0, 0, 0, 0, 0),
                    (1, 0, 0, 0),
                    (1, 0, 0, 0, 0),
                ]
            ],
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* >>: A", [tree])),
            [
                [
                    (0, 0),
                    (0, 0, 0),
                    (0, 0, 0, 0),
                    (0, 0, 0, 0, 0),
                    (0, 0, 0, 0, 0, 0),
                    (1, 0),
                    (1, 0, 0),
                ]
            ],
        )

    def test_bad_operator(self):
        """
        Test error handling of undefined tgrep operators.
        """
        tree = ParentedTree.fromstring("(S (A (T x)) (B (N x)))")
        self.assertRaises(
            tgrep.TgrepException, list, tgrep.tgrep_positions("* >>> S", [tree])
        )

    def test_comments(self):
        """
        Test that comments are correctly filtered out of tgrep search
        strings.
        """
        tree = ParentedTree.fromstring("(S (NN x) (NP x) (NN x))")
        search1 = """
        @ NP /^NP/;
        @ NN /^NN/;
        @NN
        """
        self.assertEqual(list(tgrep.tgrep_positions(search1, [tree])), [[(0,), (2,)]])
        search2 = """
        # macros
        @ NP /^NP/;
        @ NN /^NN/;

        # search string
        @NN
        """
        self.assertEqual(list(tgrep.tgrep_positions(search2, [tree])), [[(0,), (2,)]])

    def test_rel_sister_nodes(self):
        """
        Test matching sister nodes in a tree.
        """
        tree = ParentedTree.fromstring("(S (A x) (B x) (C x))")
        self.assertEqual(list(tgrep.tgrep_positions("* $. B", [tree])), [[(0,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* $.. B", [tree])), [[(0,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* $, B", [tree])), [[(2,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* $,, B", [tree])), [[(2,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* $ B", [tree])), [[(0,), (2,)]])

    def tests_rel_indexed_children(self):
        """
        Test matching nodes based on their index in their parent node.
        """
        tree = ParentedTree.fromstring("(S (A x) (B x) (C x))")
        self.assertEqual(list(tgrep.tgrep_positions("* >, S", [tree])), [[(0,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* >1 S", [tree])), [[(0,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* >2 S", [tree])), [[(1,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* >3 S", [tree])), [[(2,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* >' S", [tree])), [[(2,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* >-1 S", [tree])), [[(2,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* >-2 S", [tree])), [[(1,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* >-3 S", [tree])), [[(0,)]])
        tree = ParentedTree.fromstring(
            "(S (D (A x) (B x) (C x)) (E (B x) (C x) (A x)) " "(F (C x) (A x) (B x)))"
        )
        self.assertEqual(list(tgrep.tgrep_positions("* <, A", [tree])), [[(0,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* <1 A", [tree])), [[(0,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* <2 A", [tree])), [[(2,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* <3 A", [tree])), [[(1,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* <' A", [tree])), [[(1,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* <-1 A", [tree])), [[(1,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* <-2 A", [tree])), [[(2,)]])
        self.assertEqual(list(tgrep.tgrep_positions("* <-3 A", [tree])), [[(0,)]])

    def test_rel_precedence(self):
        """
        Test matching nodes based on precedence relations.
        """
        tree = ParentedTree.fromstring(
            "(S (NP (NP (PP x)) (NP (AP x)))"
            " (VP (AP (X (PP x)) (Y (AP x))))"
            " (NP (RC (NP (AP x)))))"
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* . X", [tree])), [[(0,), (0, 1), (0, 1, 0)]]
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* . Y", [tree])), [[(1, 0, 0), (1, 0, 0, 0)]]
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* .. X", [tree])),
            [[(0,), (0, 0), (0, 0, 0), (0, 1), (0, 1, 0)]],
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* .. Y", [tree])),
            [[(0,), (0, 0), (0, 0, 0), (0, 1), (0, 1, 0), (1, 0, 0), (1, 0, 0, 0)]],
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* , X", [tree])), [[(1, 0, 1), (1, 0, 1, 0)]]
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* , Y", [tree])),
            [[(2,), (2, 0), (2, 0, 0), (2, 0, 0, 0)]],
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* ,, X", [tree])),
            [[(1, 0, 1), (1, 0, 1, 0), (2,), (2, 0), (2, 0, 0), (2, 0, 0, 0)]],
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("* ,, Y", [tree])),
            [[(2,), (2, 0), (2, 0, 0), (2, 0, 0, 0)]],
        )

    def test_examples(self):
        """
        Test the Basic Examples from the TGrep2 manual.
        """
        tree = ParentedTree.fromstring("(S (NP (AP x)) (NP (PP x)))")
        # This matches any NP node that immediately dominates a PP:
        self.assertEqual(list(tgrep.tgrep_positions("NP < PP", [tree])), [[(1,)]])

        tree = ParentedTree.fromstring("(S (NP x) (VP x) (NP (PP x)) (VP x))")
        # This matches an NP that dominates a PP and is immediately
        # followed by a VP:
        self.assertEqual(list(tgrep.tgrep_positions("NP << PP . VP", [tree])), [[(2,)]])

        tree = ParentedTree.fromstring(
            "(S (NP (AP x)) (NP (PP x)) " "(NP (DET x) (NN x)) (VP x))"
        )
        # This matches an NP that dominates a PP or is immediately
        # followed by a VP:
        self.assertEqual(
            list(tgrep.tgrep_positions("NP << PP | . VP", [tree])), [[(1,), (2,)]]
        )

        tree = ParentedTree.fromstring(
            "(S (NP (NP (PP x)) (NP (AP x)))"
            " (VP (AP (NP (PP x)) (NP (AP x))))"
            " (NP (RC (NP (AP x)))))"
        )
        # This matches an NP that does not dominate a PP. Also, the NP
        # must either have a parent that is an NP or be dominated by a
        # VP:
        self.assertEqual(
            list(tgrep.tgrep_positions("NP !<< PP [> NP | >> VP]", [tree])),
            [[(0, 1), (1, 0, 1)]],
        )

        tree = ParentedTree.fromstring(
            "(S (NP (AP (PP x) (VP x))) " "(NP (AP (PP x) (NP x))) (NP x))"
        )
        # This matches an NP that dominates a PP which itself is
        # immediately followed by a VP. Note the use of parentheses to
        # group ". VP" with the PP rather than with the NP:
        self.assertEqual(
            list(tgrep.tgrep_positions("NP << (PP . VP)", [tree])), [[(0,)]]
        )

        tree = ParentedTree.fromstring(
            "(S (NP (DET a) (NN cat) (PP (IN on) (NP x)))"
            " (NP (DET a) (NN cat) (PP (IN on) (NP x)) (PP x))"
            " (NP x))"
        )
        # This matches an NP whose last child is a PP that begins with
        # the preposition "on":
        self.assertEqual(
            list(tgrep.tgrep_positions("NP <' (PP <, (IN < on))", [tree])), [[(0,)]]
        )

        tree = ParentedTree.fromstring(
            "(S (S (C x) (A (B x))) (S (C x) (A x)) " "(S (D x) (A (B x))))"
        )
        # The following pattern matches an S which has a child A and
        # another child that is a C and that the A has a child B:
        self.assertEqual(
            list(tgrep.tgrep_positions("S < (A < B) < C", [tree])), [[(0,)]]
        )

        tree = ParentedTree.fromstring(
            "(S (S (A (B x) (C x))) (S (S (C x) (A (B x)))))"
        )
        # However, this pattern means that S has child A and that A
        # has children B and C:
        self.assertEqual(
            list(tgrep.tgrep_positions("S < ((A < B) < C)", [tree])), [[(0,)]]
        )

        # It is equivalent to this:
        self.assertEqual(
            list(tgrep.tgrep_positions("S < (A < B < C)", [tree])), [[(0,)]]
        )

    def test_use_macros(self):
        """
        Test defining and using tgrep2 macros.
        """
        tree = ParentedTree.fromstring(
            "(VP (VB sold) (NP (DET the) "
            "(NN heiress)) (NP (NN deed) (PREP to) "
            "(NP (DET the) (NN school) (NN house))))"
        )
        self.assertEqual(
            list(
                tgrep.tgrep_positions(
                    "@ NP /^NP/;\n@ NN /^NN/;\n@NP !< @NP !$.. @NN", [tree]
                )
            ),
            [[(1,), (2, 2)]],
        )
        # use undefined macro @CNP
        self.assertRaises(
            tgrep.TgrepException,
            list,
            tgrep.tgrep_positions(
                "@ NP /^NP/;\n@ NN /^NN/;\n@CNP !< @NP !$.. @NN", [tree]
            ),
        )

    def test_tokenize_node_labels(self):
        """Test tokenization of labeled nodes."""
        self.assertEqual(
            tgrep.tgrep_tokenize("S < @SBJ < (@VP < (@VB $.. @OBJ))"),
            [
                "S",
                "<",
                "@SBJ",
                "<",
                "(",
                "@VP",
                "<",
                "(",
                "@VB",
                "$..",
                "@OBJ",
                ")",
                ")",
            ],
        )
        self.assertEqual(
            tgrep.tgrep_tokenize("S < @SBJ=s < (@VP=v < (@VB $.. @OBJ))"),
            [
                "S",
                "<",
                "@SBJ",
                "=",
                "s",
                "<",
                "(",
                "@VP",
                "=",
                "v",
                "<",
                "(",
                "@VB",
                "$..",
                "@OBJ",
                ")",
                ")",
            ],
        )

    def test_tokenize_segmented_patterns(self):
        """Test tokenization of segmented patterns."""
        self.assertEqual(
            tgrep.tgrep_tokenize("S < @SBJ=s < (@VP=v < (@VB $.. @OBJ)) : =s .. =v"),
            [
                "S",
                "<",
                "@SBJ",
                "=",
                "s",
                "<",
                "(",
                "@VP",
                "=",
                "v",
                "<",
                "(",
                "@VB",
                "$..",
                "@OBJ",
                ")",
                ")",
                ":",
                "=s",
                "..",
                "=v",
            ],
        )

    def test_labeled_nodes(self):
        """
        Test labeled nodes.

        Test case from Emily M. Bender.
        """
        search = """
            # macros
            @ SBJ /SBJ/;
            @ VP /VP/;
            @ VB /VB/;
            @ VPoB /V[PB]/;
            @ OBJ /OBJ/;

            # 1 svo
            S < @SBJ=s < (@VP=v < (@VB $.. @OBJ)) : =s .. =v"""
        sent1 = ParentedTree.fromstring(
            "(S (NP-SBJ I) (VP (VB eat) (NP-OBJ (NNS apples))))"
        )
        sent2 = ParentedTree.fromstring(
            "(S (VP (VB eat) (NP-OBJ (NNS apples))) (NP-SBJ I))"
        )
        search_firsthalf = search.split("\n\n")[0] + "S < @SBJ < (@VP < (@VB $.. @OBJ))"
        search_rewrite = "S < (/.*SBJ/ $.. (/VP/ < (/VB/ $.. /.*OBJ/)))"

        self.assertTrue(list(tgrep.tgrep_positions(search_firsthalf, [sent1]))[0])
        self.assertTrue(list(tgrep.tgrep_positions(search, [sent1]))[0])
        self.assertTrue(list(tgrep.tgrep_positions(search_rewrite, [sent1]))[0])
        self.assertEqual(
            list(tgrep.tgrep_positions(search, [sent1])),
            list(tgrep.tgrep_positions(search_rewrite, [sent1])),
        )
        self.assertTrue(list(tgrep.tgrep_positions(search_firsthalf, [sent2]))[0])
        self.assertFalse(list(tgrep.tgrep_positions(search, [sent2]))[0])
        self.assertFalse(list(tgrep.tgrep_positions(search_rewrite, [sent2]))[0])
        self.assertEqual(
            list(tgrep.tgrep_positions(search, [sent2])),
            list(tgrep.tgrep_positions(search_rewrite, [sent2])),
        )

    def test_multiple_conjs(self):
        """
        Test that multiple (3 or more) conjunctions of node relations are
        handled properly.
        """
        sent = ParentedTree.fromstring("((A (B b) (C c)) (A (B b) (C c) (D d)))")
        # search = '(A < B < C < D)'
        # search_tworels = '(A < B < C)'
        self.assertEqual(
            list(tgrep.tgrep_positions("(A < B < C < D)", [sent])), [[(1,)]]
        )
        self.assertEqual(
            list(tgrep.tgrep_positions("(A < B < C)", [sent])), [[(0,), (1,)]]
        )

    def test_trailing_semicolon(self):
        """
        Test that semicolons at the end of a tgrep2 search string won't
        cause a parse failure.
        """
        tree = ParentedTree.fromstring(
            "(S (NP (DT the) (JJ big) (NN dog)) " "(VP bit) (NP (DT a) (NN cat)))"
        )
        self.assertEqual(list(tgrep.tgrep_positions("NN", [tree])), [[(0, 2), (2, 1)]])
        self.assertEqual(list(tgrep.tgrep_positions("NN;", [tree])), [[(0, 2), (2, 1)]])
        self.assertEqual(
            list(tgrep.tgrep_positions("NN;;", [tree])), [[(0, 2), (2, 1)]]
        )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\guardrails\guardrail_endpoints.py ===
"""
CRUD ENDPOINTS FOR GUARDRAILS
"""

from typing import Any, Dict, List, Optional, Type, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from litellm._logging import verbose_proxy_logger
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.guardrails.guardrail_registry import GuardrailRegistry
from litellm.types.guardrails import (
    PII_ENTITY_CATEGORIES_MAP,
    BedrockGuardrailConfigModel,
    Guardrail,
    GuardrailEventHooks,
    GuardrailInfoResponse,
    GuardrailParamUITypes,
    GuardrailUIAddGuardrailSettings,
    LakeraV2GuardrailConfigModel,
    ListGuardrailsResponse,
    LitellmParams,
    PatchGuardrailRequest,
    PiiAction,
    PiiEntityType,
    PresidioPresidioConfigModelUserInterface,
    SupportedGuardrailIntegrations,
)

#### GUARDRAILS ENDPOINTS ####

router = APIRouter()
GUARDRAIL_REGISTRY = GuardrailRegistry()


def _get_guardrails_list_response(
    guardrails_config: List[Dict],
) -> ListGuardrailsResponse:
    """
    Helper function to get the guardrails list response
    """
    guardrail_configs: List[GuardrailInfoResponse] = []
    for guardrail in guardrails_config:
        guardrail_configs.append(
            GuardrailInfoResponse(
                guardrail_name=guardrail.get("guardrail_name"),
                litellm_params=guardrail.get("litellm_params"),
                guardrail_info=guardrail.get("guardrail_info"),
            )
        )
    return ListGuardrailsResponse(guardrails=guardrail_configs)


@router.get(
    "/guardrails/list",
    tags=["Guardrails"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=ListGuardrailsResponse,
)
async def list_guardrails():
    """
    List the guardrails that are available on the proxy server

    👉 [Guardrail docs](https://docs.litellm.ai/docs/proxy/guardrails/quick_start)

    Example Request:
    ```bash
    curl -X GET "http://localhost:4000/guardrails/list" -H "Authorization: Bearer <your_api_key>"
    ```

    Example Response:
    ```json
    {
        "guardrails": [
            {
            "guardrail_name": "bedrock-pre-guard",
            "guardrail_info": {
                "params": [
                {
                    "name": "toxicity_score",
                    "type": "float",
                    "description": "Score between 0-1 indicating content toxicity level"
                },
                {
                    "name": "pii_detection",
                    "type": "boolean"
                }
                ]
            }
            }
        ]
    }
    ```
    """
    from litellm.proxy.proxy_server import proxy_config

    config = proxy_config.config

    _guardrails_config = cast(Optional[list[dict]], config.get("guardrails"))

    if _guardrails_config is None:
        return _get_guardrails_list_response([])

    return _get_guardrails_list_response(_guardrails_config)


@router.get(
    "/v2/guardrails/list",
    tags=["Guardrails"],
    dependencies=[Depends(user_api_key_auth)],
    response_model=ListGuardrailsResponse,
)
async def list_guardrails_v2():
    """
    List the guardrails that are available in the database using GuardrailRegistry

    👉 [Guardrail docs](https://docs.litellm.ai/docs/proxy/guardrails/quick_start)

    Example Request:
    ```bash
    curl -X GET "http://localhost:4000/v2/guardrails/list" -H "Authorization: Bearer <your_api_key>"
    ```

    Example Response:
    ```json
    {
        "guardrails": [
            {
                "guardrail_id": "123e4567-e89b-12d3-a456-426614174000",
                "guardrail_name": "my-bedrock-guard",
                "litellm_params": {
                    "guardrail": "bedrock",
                    "mode": "pre_call",
                    "guardrailIdentifier": "ff6ujrregl1q",
                    "guardrailVersion": "DRAFT",
                    "default_on": true
                },
                "guardrail_info": {
                    "description": "Bedrock content moderation guardrail"
                }
            }
        ]
    }
    ```
    """
    from litellm.proxy.guardrails.guardrail_registry import IN_MEMORY_GUARDRAIL_HANDLER
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail="Prisma client not initialized")

    try:
        guardrails = await GUARDRAIL_REGISTRY.get_all_guardrails_from_db(
            prisma_client=prisma_client
        )

        guardrail_configs: List[GuardrailInfoResponse] = []
        seen_guardrail_ids = set()
        for guardrail in guardrails:
            guardrail_configs.append(
                GuardrailInfoResponse(
                    guardrail_id=guardrail.get("guardrail_id"),
                    guardrail_name=guardrail.get("guardrail_name"),
                    litellm_params=guardrail.get("litellm_params"),
                    guardrail_info=guardrail.get("guardrail_info"),
                    created_at=guardrail.get("created_at"),
                    updated_at=guardrail.get("updated_at"),
                    guardrail_definition_location="db",
                )
            )
            seen_guardrail_ids.add(guardrail.get("guardrail_id"))

        # get guardrails initialized on litellm config.yaml
        in_memory_guardrails = IN_MEMORY_GUARDRAIL_HANDLER.list_in_memory_guardrails()
        for guardrail in in_memory_guardrails:
            # only add guardrails that are not in DB guardrail list already
            if guardrail.get("guardrail_id") not in seen_guardrail_ids:
                guardrail_configs.append(
                    GuardrailInfoResponse(
                        guardrail_id=guardrail.get("guardrail_id"),
                        guardrail_name=guardrail.get("guardrail_name"),
                        litellm_params=dict(guardrail.get("litellm_params") or {}),
                        guardrail_info=dict(guardrail.get("guardrail_info") or {}),
                        guardrail_definition_location="config",
                    )
                )
                seen_guardrail_ids.add(guardrail.get("guardrail_id"))

        return ListGuardrailsResponse(guardrails=guardrail_configs)
    except Exception as e:
        verbose_proxy_logger.exception(f"Error getting guardrails from db: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CreateGuardrailRequest(BaseModel):
    guardrail: Guardrail


@router.post(
    "/guardrails",
    tags=["Guardrails"],
    dependencies=[Depends(user_api_key_auth)],
)
async def create_guardrail(request: CreateGuardrailRequest):
    """
    Create a new guardrail

    👉 [Guardrail docs](https://docs.litellm.ai/docs/proxy/guardrails/quick_start)

    Example Request:
    ```bash
    curl -X POST "http://localhost:4000/guardrails" \\
        -H "Authorization: Bearer <your_api_key>" \\
        -H "Content-Type: application/json" \\
        -d '{
            "guardrail": {
                "guardrail_name": "my-bedrock-guard",
                "litellm_params": {
                    "guardrail": "bedrock",
                    "mode": "pre_call",
                    "guardrailIdentifier": "ff6ujrregl1q",
                    "guardrailVersion": "DRAFT",
                    "default_on": true
                },
                "guardrail_info": {
                    "description": "Bedrock content moderation guardrail"
                }
            }
        }'
    ```

    Example Response:
    ```json
    {
        "guardrail_id": "123e4567-e89b-12d3-a456-426614174000",
        "guardrail_name": "my-bedrock-guard",
        "litellm_params": {
            "guardrail": "bedrock",
            "mode": "pre_call",
            "guardrailIdentifier": "ff6ujrregl1q",
            "guardrailVersion": "DRAFT",
            "default_on": true
        },
        "guardrail_info": {
            "description": "Bedrock content moderation guardrail"
        },
        "created_at": "2023-11-09T12:34:56.789Z",
        "updated_at": "2023-11-09T12:34:56.789Z"
    }
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail="Prisma client not initialized")

    try:
        result = await GUARDRAIL_REGISTRY.add_guardrail_to_db(
            guardrail=request.guardrail, prisma_client=prisma_client
        )
        return result
    except Exception as e:
        verbose_proxy_logger.exception(f"Error adding guardrail to db: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/guardrails/{guardrail_id}",
    tags=["Guardrails"],
    dependencies=[Depends(user_api_key_auth)],
)
async def get_guardrail(guardrail_id: str):
    """
    Get a guardrail by ID

    👉 [Guardrail docs](https://docs.litellm.ai/docs/proxy/guardrails/quick_start)

    Example Request:
    ```bash
    curl -X GET "http://localhost:4000/guardrails/123e4567-e89b-12d3-a456-426614174000" \\
        -H "Authorization: Bearer <your_api_key>"
    ```

    Example Response:
    ```json
    {
        "guardrail_id": "123e4567-e89b-12d3-a456-426614174000",
        "guardrail_name": "my-bedrock-guard",
        "litellm_params": {
            "guardrail": "bedrock",
            "mode": "pre_call",
            "guardrailIdentifier": "ff6ujrregl1q",
            "guardrailVersion": "DRAFT",
            "default_on": true
        },
        "guardrail_info": {
            "description": "Bedrock content moderation guardrail"
        },
        "created_at": "2023-11-09T12:34:56.789Z",
        "updated_at": "2023-11-09T12:34:56.789Z"
    }
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail="Prisma client not initialized")

    try:
        result = await GUARDRAIL_REGISTRY.get_guardrail_by_id_from_db(
            guardrail_id=guardrail_id, prisma_client=prisma_client
        )

        if result is None:
            raise HTTPException(
                status_code=404, detail=f"Guardrail with ID {guardrail_id} not found"
            )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UpdateGuardrailRequest(BaseModel):
    guardrail: Guardrail


@router.put(
    "/guardrails/{guardrail_id}",
    tags=["Guardrails"],
    dependencies=[Depends(user_api_key_auth)],
)
async def update_guardrail(guardrail_id: str, request: UpdateGuardrailRequest):
    """
    Update an existing guardrail

    👉 [Guardrail docs](https://docs.litellm.ai/docs/proxy/guardrails/quick_start)

    Example Request:
    ```bash
    curl -X PUT "http://localhost:4000/guardrails/123e4567-e89b-12d3-a456-426614174000" \\
        -H "Authorization: Bearer <your_api_key>" \\
        -H "Content-Type: application/json" \\
        -d '{
            "guardrail": {
                "guardrail_name": "updated-bedrock-guard",
                "litellm_params": {
                    "guardrail": "bedrock",
                    "mode": "pre_call",
                    "guardrailIdentifier": "ff6ujrregl1q",
                    "guardrailVersion": "1.0",
                    "default_on": true
                },
                "guardrail_info": {
                    "description": "Updated Bedrock content moderation guardrail"
                }
            }
        }'
    ```

    Example Response:
    ```json
    {
        "guardrail_id": "123e4567-e89b-12d3-a456-426614174000",
        "guardrail_name": "updated-bedrock-guard",
        "litellm_params": {
            "guardrail": "bedrock",
            "mode": "pre_call",
            "guardrailIdentifier": "ff6ujrregl1q",
            "guardrailVersion": "1.0",
            "default_on": true
        },
        "guardrail_info": {
            "description": "Updated Bedrock content moderation guardrail"
        },
        "created_at": "2023-11-09T12:34:56.789Z",
        "updated_at": "2023-11-09T13:45:12.345Z"
    }
    ```
    """
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail="Prisma client not initialized")

    try:
        # Check if guardrail exists
        existing_guardrail = await GUARDRAIL_REGISTRY.get_guardrail_by_id_from_db(
            guardrail_id=guardrail_id, prisma_client=prisma_client
        )

        if existing_guardrail is None:
            raise HTTPException(
                status_code=404, detail=f"Guardrail with ID {guardrail_id} not found"
            )

        result = await GUARDRAIL_REGISTRY.update_guardrail_in_db(
            guardrail_id=guardrail_id,
            guardrail=request.guardrail,
            prisma_client=prisma_client,
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/guardrails/{guardrail_id}",
    tags=["Guardrails"],
    dependencies=[Depends(user_api_key_auth)],
)
async def delete_guardrail(guardrail_id: str):
    """
    Delete a guardrail

    👉 [Guardrail docs](https://docs.litellm.ai/docs/proxy/guardrails/quick_start)

    Example Request:
    ```bash
    curl -X DELETE "http://localhost:4000/guardrails/123e4567-e89b-12d3-a456-426614174000" \\
        -H "Authorization: Bearer <your_api_key>"
    ```

    Example Response:
    ```json
    {
        "message": "Guardrail 123e4567-e89b-12d3-a456-426614174000 deleted successfully"
    }
    ```
    """
    from litellm.proxy.guardrails.guardrail_registry import IN_MEMORY_GUARDRAIL_HANDLER
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail="Prisma client not initialized")

    try:
        # Check if guardrail exists
        existing_guardrail = await GUARDRAIL_REGISTRY.get_guardrail_by_id_from_db(
            guardrail_id=guardrail_id, prisma_client=prisma_client
        )

        if existing_guardrail is None:
            raise HTTPException(
                status_code=404, detail=f"Guardrail with ID {guardrail_id} not found"
            )

        result = await GUARDRAIL_REGISTRY.delete_guardrail_from_db(
            guardrail_id=guardrail_id, prisma_client=prisma_client
        )

        # delete in memory guardrail
        IN_MEMORY_GUARDRAIL_HANDLER.delete_in_memory_guardrail(
            guardrail_id=guardrail_id,
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/guardrails/{guardrail_id}",
    tags=["Guardrails"],
    dependencies=[Depends(user_api_key_auth)],
)
async def patch_guardrail(guardrail_id: str, request: PatchGuardrailRequest):
    """
    Partially update an existing guardrail

    👉 [Guardrail docs](https://docs.litellm.ai/docs/proxy/guardrails/quick_start)

    This endpoint allows updating specific fields of a guardrail without sending the entire object.
    Only the following fields can be updated:
    - guardrail_name: The name of the guardrail
    - default_on: Whether the guardrail is enabled by default
    - guardrail_info: Additional information about the guardrail

    Example Request:
    ```bash
    curl -X PATCH "http://localhost:4000/guardrails/123e4567-e89b-12d3-a456-426614174000" \\
        -H "Authorization: Bearer <your_api_key>" \\
        -H "Content-Type: application/json" \\
        -d '{
            "guardrail_name": "updated-name",
            "default_on": true,
            "guardrail_info": {
                "description": "Updated description"
            }
        }'
    ```

    Example Response:
    ```json
    {
        "guardrail_id": "123e4567-e89b-12d3-a456-426614174000",
        "guardrail_name": "updated-name",
        "litellm_params": {
            "guardrail": "bedrock",
            "mode": "pre_call",
            "guardrailIdentifier": "ff6ujrregl1q",
            "guardrailVersion": "DRAFT",
            "default_on": true
        },
        "guardrail_info": {
            "description": "Updated description"
        },
        "created_at": "2023-11-09T12:34:56.789Z",
        "updated_at": "2023-11-09T14:22:33.456Z"
    }
    ```
    """
    from litellm.proxy.guardrails.guardrail_registry import IN_MEMORY_GUARDRAIL_HANDLER
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail="Prisma client not initialized")

    try:
        # Check if guardrail exists and get current data
        existing_guardrail = await GUARDRAIL_REGISTRY.get_guardrail_by_id_from_db(
            guardrail_id=guardrail_id, prisma_client=prisma_client
        )

        if existing_guardrail is None:
            raise HTTPException(
                status_code=404, detail=f"Guardrail with ID {guardrail_id} not found"
            )

        # Create updated guardrail object
        guardrail_name = (
            request.guardrail_name
            if request.guardrail_name is not None
            else existing_guardrail.get("guardrail_name")
        )

        # Update litellm_params if default_on is provided or pii_entities_config is provided
        litellm_params = LitellmParams(
            **dict(existing_guardrail.get("litellm_params", {}))
        )
        if (
            request.litellm_params is not None
            and request.litellm_params.default_on is not None
        ):
            litellm_params.default_on = request.litellm_params.default_on

        if (
            request.litellm_params is not None
            and request.litellm_params.pii_entities_config is not None
        ):
            litellm_params.pii_entities_config = (
                request.litellm_params.pii_entities_config
            )

        # Update guardrail_info if provided
        guardrail_info = (
            request.guardrail_info
            if request.guardrail_info is not None
            else existing_guardrail.get("guardrail_info", {})
        )

        # Create the guardrail object
        guardrail = Guardrail(
            guardrail_name=guardrail_name or "",
            litellm_params=litellm_params,
            guardrail_info=guardrail_info,
        )
        result = await GUARDRAIL_REGISTRY.update_guardrail_in_db(
            guardrail_id=guardrail_id,
            guardrail=guardrail,
            prisma_client=prisma_client,
        )

        # update in memory guardrail
        IN_MEMORY_GUARDRAIL_HANDLER.update_in_memory_guardrail(
            guardrail_id=guardrail_id,
            guardrail=guardrail,
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        verbose_proxy_logger.exception(f"Error updating guardrail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/guardrails/{guardrail_id}/info",
    tags=["Guardrails"],
    dependencies=[Depends(user_api_key_auth)],
)
async def get_guardrail_info(guardrail_id: str):
    """
    Get detailed information about a specific guardrail by ID

    👉 [Guardrail docs](https://docs.litellm.ai/docs/proxy/guardrails/quick_start)

    Example Request:
    ```bash
    curl -X GET "http://localhost:4000/guardrails/123e4567-e89b-12d3-a456-426614174000/info" \\
        -H "Authorization: Bearer <your_api_key>"
    ```

    Example Response:
    ```json
    {
        "guardrail_id": "123e4567-e89b-12d3-a456-426614174000",
        "guardrail_name": "my-bedrock-guard",
        "litellm_params": {
            "guardrail": "bedrock",
            "mode": "pre_call",
            "guardrailIdentifier": "ff6ujrregl1q",
            "guardrailVersion": "DRAFT",
            "default_on": true
        },
        "guardrail_info": {
            "description": "Bedrock content moderation guardrail"
        },
        "created_at": "2023-11-09T12:34:56.789Z",
        "updated_at": "2023-11-09T12:34:56.789Z"
    }
    ```
    """
    from litellm.proxy.guardrails.guardrail_registry import IN_MEMORY_GUARDRAIL_HANDLER
    from litellm.proxy.proxy_server import prisma_client

    if prisma_client is None:
        raise HTTPException(status_code=500, detail="Prisma client not initialized")

    try:
        result = await GUARDRAIL_REGISTRY.get_guardrail_by_id_from_db(
            guardrail_id=guardrail_id, prisma_client=prisma_client
        )
        if result is None:
            result = IN_MEMORY_GUARDRAIL_HANDLER.get_guardrail_by_id(
                guardrail_id=guardrail_id
            )

        if result is None:
            raise HTTPException(
                status_code=404, detail=f"Guardrail with ID {guardrail_id} not found"
            )

        return GuardrailInfoResponse(
            guardrail_id=result.get("guardrail_id"),
            guardrail_name=result.get("guardrail_name"),
            litellm_params=dict(result.get("litellm_params") or {}),
            guardrail_info=dict(result.get("guardrail_info") or {}),
            created_at=result.get("created_at"),
            updated_at=result.get("updated_at"),
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/guardrails/ui/add_guardrail_settings",
    tags=["Guardrails"],
    dependencies=[Depends(user_api_key_auth)],
)
async def get_guardrail_ui_settings():
    """
    Get the UI settings for the guardrails

    Returns:
    - Supported entities for guardrails
    - Supported modes for guardrails
    - PII entity categories for UI organization
    """
    # Convert the PII_ENTITY_CATEGORIES_MAP to the format expected by the UI
    category_maps = []
    for category, entities in PII_ENTITY_CATEGORIES_MAP.items():
        category_maps.append({"category": category, "entities": entities})

    return GuardrailUIAddGuardrailSettings(
        supported_entities=list(PiiEntityType),
        supported_actions=list(PiiAction),
        supported_modes=list(GuardrailEventHooks),
        pii_entity_categories=category_maps,
    )


def _get_fields_from_model(model_class: Type[BaseModel]) -> List[Dict[str, Any]]:
    """
    Get the fields from a Pydantic model
    """
    fields = []
    for field_name, field in model_class.model_fields.items():
        # Get field metadata
        description = field.description or field_name

        # Check if this field is in the required_fields class variable
        required = field.is_required()

        field_type: Optional[GuardrailParamUITypes] = None
        field_json_schema_extra = getattr(field, "json_schema_extra", {})
        if field_json_schema_extra and "ui_type" in field_json_schema_extra:
            field_type = field_json_schema_extra["ui_type"]

        fields.append(
            {
                "param": field_name,
                "description": description,
                "required": required,
                "type": field_type.value if field_type else None,
            }
        )
    return fields


@router.get(
    "/guardrails/ui/provider_specific_params",
    tags=["Guardrails"],
    dependencies=[Depends(user_api_key_auth)],
)
async def get_provider_specific_params():
    """
    Get provider-specific parameters for different guardrail types.

    Returns a dictionary mapping guardrail providers to their specific parameters,
    including parameter names, descriptions, and whether they are required.

    Example Response:
    ```json
    {
        "bedrock": [
            {
                "param": "guardrailIdentifier",
                "description": "The ID of your guardrail on Bedrock",
                "required": true
            },
            {
                "param": "guardrailVersion",
                "description": "The version of your Bedrock guardrail (e.g., DRAFT or version number)",
                "required": true
            }
        ],
        "presidio": [
            {
                "param": "presidio_analyzer_api_base",
                "description": "Base URL for the Presidio analyzer API",
                "required": true
            },
            {
                "param": "presidio_anonymizer_api_base",
                "description": "Base URL for the Presidio anonymizer API",
                "required": true
            },
            {
                "param": "output_parse_pii",
                "description": "Whether to parse PII in model outputs",
                "required": false,
                "type": "bool"
            }
        ]
    }
    ```
    """
    # Get fields from the models
    bedrock_fields = _get_fields_from_model(BedrockGuardrailConfigModel)
    presidio_fields = _get_fields_from_model(PresidioPresidioConfigModelUserInterface)
    lakera_v2_fields = _get_fields_from_model(LakeraV2GuardrailConfigModel)

    # Return the provider-specific parameters
    provider_params = {
        SupportedGuardrailIntegrations.BEDROCK.value: bedrock_fields,
        SupportedGuardrailIntegrations.PRESIDIO.value: presidio_fields,
        SupportedGuardrailIntegrations.LAKERA_V2.value: lakera_v2_fields,
    }

    return provider_params

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\hooks\parallel_request_limiter_v3.py ===
"""
This is a rate limiter implementation based on a similar one by Envoy proxy. 

This is currently in development and not yet ready for production.
"""
import os
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    TypedDict,
    Union,
    cast,
)

from fastapi import HTTPException

from litellm import DualCache
from litellm._logging import verbose_proxy_logger
from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy._types import UserAPIKeyAuth

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    from litellm.proxy.utils import InternalUsageCache as _InternalUsageCache
    from litellm.types.caching import RedisPipelineIncrementOperation

    Span = Union[_Span, Any]
    InternalUsageCache = _InternalUsageCache
else:
    Span = Any
    InternalUsageCache = Any

BATCH_RATE_LIMITER_SCRIPT = """
local results = {}
local now = tonumber(ARGV[1])
local window_size = tonumber(ARGV[2])

-- Process each window/counter pair
for i = 1, #KEYS, 2 do
    local window_key = KEYS[i]
    local counter_key = KEYS[i + 1]
    local increment_value = 1

    -- Check if window exists and is valid
    local window_start = redis.call('GET', window_key)
    if not window_start or (now - tonumber(window_start)) >= window_size then
        -- Reset window and counter
        redis.call('SET', window_key, tostring(now))
        redis.call('SET', counter_key, increment_value)
        redis.call('EXPIRE', window_key, window_size)
        redis.call('EXPIRE', counter_key, window_size)
        table.insert(results, tostring(now)) -- window_start
        table.insert(results, increment_value) -- counter
    else
        local counter = redis.call('INCR', counter_key)
        table.insert(results, window_start) -- window_start
        table.insert(results, counter) -- counter
    end
end

return results
"""


class RateLimitDescriptorRateLimitObject(TypedDict, total=False):
    requests_per_unit: Optional[int]
    tokens_per_unit: Optional[int]
    max_parallel_requests: Optional[int]
    window_size: Optional[int]


class RateLimitDescriptor(TypedDict):
    key: str
    value: str
    rate_limit: Optional[RateLimitDescriptorRateLimitObject]


class RateLimitStatus(TypedDict):
    code: str
    current_limit: int
    limit_remaining: int
    rate_limit_type: Literal["requests", "tokens", "max_parallel_requests"]
    descriptor_key: str


class RateLimitResponse(TypedDict):
    overall_code: str
    statuses: List[RateLimitStatus]


class RateLimitResponseWithDescriptors(TypedDict):
    descriptors: List[RateLimitDescriptor]
    response: RateLimitResponse


class _PROXY_MaxParallelRequestsHandler_v3(CustomLogger):
    def __init__(self, internal_usage_cache: InternalUsageCache):
        self.internal_usage_cache = internal_usage_cache
        if self.internal_usage_cache.dual_cache.redis_cache is not None:
            self.batch_rate_limiter_script = (
                self.internal_usage_cache.dual_cache.redis_cache.async_register_script(
                    BATCH_RATE_LIMITER_SCRIPT
                )
            )
        else:
            self.batch_rate_limiter_script = None

        self.window_size = int(os.getenv("LITELLM_RATE_LIMIT_WINDOW_SIZE", 60))

    async def in_memory_cache_sliding_window(
        self,
        keys: List[str],
        now_int: int,
        window_size: int,
    ) -> List[Any]:
        """
        Implement sliding window rate limiting logic using in-memory cache operations.
        This follows the same logic as the Redis Lua script but uses async cache operations.
        """
        results: List[Any] = []

        # Process each window/counter pair
        for i in range(0, len(keys), 2):
            window_key = keys[i]
            counter_key = keys[i + 1]
            increment_value = 1

            # Get the window start time
            window_start = await self.internal_usage_cache.async_get_cache(
                key=window_key,
                litellm_parent_otel_span=None,
                local_only=True,
            )

            # Check if window exists and is valid
            if window_start is None or (now_int - int(window_start)) >= window_size:
                # Reset window and counter
                await self.internal_usage_cache.async_set_cache(
                    key=window_key,
                    value=str(now_int),
                    ttl=window_size,
                    litellm_parent_otel_span=None,
                    local_only=True,
                )
                await self.internal_usage_cache.async_set_cache(
                    key=counter_key,
                    value=increment_value,
                    ttl=window_size,
                    litellm_parent_otel_span=None,
                    local_only=True,
                )
                results.append(str(now_int))  # window_start
                results.append(increment_value)  # counter
            else:
                # Increment the counter
                current_counter = await self.internal_usage_cache.async_get_cache(
                    key=counter_key,
                    litellm_parent_otel_span=None,
                    local_only=True,
                )
                new_counter_value = (
                    int(current_counter) if current_counter is not None else 0
                ) + increment_value
                await self.internal_usage_cache.async_set_cache(
                    key=counter_key,
                    value=new_counter_value,
                    ttl=window_size,
                    litellm_parent_otel_span=None,
                    local_only=True,
                )
                results.append(window_start)  # window_start
                results.append(new_counter_value)  # counter

        return results

    def create_rate_limit_keys(
        self,
        key: str,
        value: str,
        rate_limit_type: Literal["requests", "tokens", "max_parallel_requests"],
    ) -> str:
        """
        Create the rate limit keys for the given key and value.
        """
        counter_key = f"{{{key}:{value}}}:{rate_limit_type}"

        return counter_key

    def is_cache_list_over_limit(
        self,
        keys_to_fetch: List[str],
        cache_values: List[Any],
        key_metadata: Dict[str, Any],
    ) -> RateLimitResponse:
        """
        Check if the cache values are over the limit.
        """
        statuses: List[RateLimitStatus] = []
        overall_code = "OK"

        for i in range(0, len(cache_values), 2):
            item_code = "OK"
            window_key = keys_to_fetch[i]
            counter_key = keys_to_fetch[i + 1]
            counter_value = cache_values[i + 1]
            requests_limit = key_metadata[window_key]["requests_limit"]
            max_parallel_requests_limit = key_metadata[window_key][
                "max_parallel_requests_limit"
            ]
            tokens_limit = key_metadata[window_key]["tokens_limit"]

            # Determine which limit to use for current_limit and limit_remaining
            current_limit: Optional[int] = None
            rate_limit_type: Optional[
                Literal["requests", "tokens", "max_parallel_requests"]
            ] = None
            if counter_key.endswith(":requests"):
                current_limit = requests_limit
                rate_limit_type = "requests"
            elif counter_key.endswith(":max_parallel_requests"):
                current_limit = max_parallel_requests_limit
                rate_limit_type = "max_parallel_requests"
            elif counter_key.endswith(":tokens"):
                current_limit = tokens_limit
                rate_limit_type = "tokens"

            if current_limit is None or rate_limit_type is None:
                continue

            if counter_value is not None and int(counter_value) + 1 > current_limit:
                overall_code = "OVER_LIMIT"
                item_code = "OVER_LIMIT"

            # Only compute limit_remaining if current_limit is not None
            limit_remaining = (
                current_limit - int(counter_value)
                if counter_value is not None
                else current_limit
            )

            statuses.append(
                {
                    "code": item_code,
                    "current_limit": current_limit,
                    "limit_remaining": limit_remaining,
                    "rate_limit_type": rate_limit_type,
                    "descriptor_key": key_metadata[window_key]["descriptor_key"],
                }
            )

        return RateLimitResponse(overall_code=overall_code, statuses=statuses)

    async def should_rate_limit(
        self,
        descriptors: List[RateLimitDescriptor],
        parent_otel_span: Optional[Span] = None,
        read_only: bool = False,
    ) -> RateLimitResponse:
        """
        Check if any of the rate limit descriptors should be rate limited.
        Returns a RateLimitResponse with the overall code and status for each descriptor.
        Uses batch operations for Redis to improve performance.
        """

        now = datetime.now().timestamp()
        now_int = int(now)  # Convert to integer for Redis Lua script

        # Collect all keys and their metadata upfront
        keys_to_fetch: List[str] = []
        key_metadata = {}  # Store metadata for each key
        for descriptor in descriptors:
            descriptor_key = descriptor["key"]
            descriptor_value = descriptor["value"]
            rate_limit = descriptor.get("rate_limit", {}) or {}
            requests_limit = rate_limit.get("requests_per_unit")
            tokens_limit = rate_limit.get("tokens_per_unit")
            max_parallel_requests_limit = rate_limit.get("max_parallel_requests")
            window_size = rate_limit.get("window_size") or self.window_size

            window_key = f"{{{descriptor_key}:{descriptor_value}}}:window"

            rate_limit_set = False
            if requests_limit is not None:
                rpm_key = self.create_rate_limit_keys(
                    descriptor_key, descriptor_value, "requests"
                )
                keys_to_fetch.extend([window_key, rpm_key])
                rate_limit_set = True
            if tokens_limit is not None:
                tpm_key = self.create_rate_limit_keys(
                    descriptor_key, descriptor_value, "tokens"
                )
                keys_to_fetch.extend([window_key, tpm_key])
                rate_limit_set = True
            if max_parallel_requests_limit is not None:
                max_parallel_requests_key = self.create_rate_limit_keys(
                    descriptor_key, descriptor_value, "max_parallel_requests"
                )
                keys_to_fetch.extend([window_key, max_parallel_requests_key])
                rate_limit_set = True

            if not rate_limit_set:
                continue

            key_metadata[window_key] = {
                "requests_limit": int(requests_limit)
                if requests_limit is not None
                else None,
                "tokens_limit": int(tokens_limit) if tokens_limit is not None else None,
                "max_parallel_requests_limit": int(max_parallel_requests_limit)
                if max_parallel_requests_limit is not None
                else None,
                "window_size": int(window_size),
                "descriptor_key": descriptor_key,
            }

        ## CHECK IN-MEMORY CACHE
        cache_values = await self.internal_usage_cache.async_batch_get_cache(
            keys=keys_to_fetch,
            parent_otel_span=parent_otel_span,
            local_only=True,
        )

        if cache_values is not None:
            rate_limit_response = self.is_cache_list_over_limit(
                keys_to_fetch, cache_values, key_metadata
            )
            if rate_limit_response["overall_code"] == "OVER_LIMIT":
                return rate_limit_response

        ## IF under limit, check Redis
        if self.batch_rate_limiter_script is not None:
            cache_values = await self.batch_rate_limiter_script(
                keys=keys_to_fetch,
                args=[now_int, self.window_size],  # Use integer timestamp
            )

            # update in-memory cache with new values
            for i in range(0, len(cache_values), 2):
                window_key = keys_to_fetch[i]
                counter_key = keys_to_fetch[i + 1]
                window_value = cache_values[i]
                counter_value = cache_values[i + 1]
                await self.internal_usage_cache.async_set_cache(
                    key=counter_key,
                    value=counter_value,
                    ttl=self.window_size,
                    litellm_parent_otel_span=parent_otel_span,
                    local_only=True,
                )
                await self.internal_usage_cache.async_set_cache(
                    key=window_key,
                    value=window_value,
                    ttl=self.window_size,
                    litellm_parent_otel_span=parent_otel_span,
                    local_only=True,
                )
        else:
            cache_values = await self.in_memory_cache_sliding_window(
                keys=keys_to_fetch,
                now_int=now_int,
                window_size=self.window_size,
            )

        rate_limit_response = self.is_cache_list_over_limit(
            keys_to_fetch, cache_values, key_metadata
        )
        return rate_limit_response

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: str,
    ):
        """
        Pre-call hook to check rate limits before making the API call.
        """
        from litellm.proxy.auth.auth_utils import (
            get_key_model_rpm_limit,
            get_key_model_tpm_limit,
        )

        verbose_proxy_logger.debug("Inside Rate Limit Pre-Call Hook")

        # Create rate limit descriptors
        descriptors = []

        # API Key rate limits
        if user_api_key_dict.api_key:
            descriptors.append(
                RateLimitDescriptor(
                    key="api_key",
                    value=user_api_key_dict.api_key,
                    rate_limit={
                        "requests_per_unit": user_api_key_dict.rpm_limit,
                        "tokens_per_unit": user_api_key_dict.tpm_limit,
                        "max_parallel_requests": user_api_key_dict.max_parallel_requests,
                        "window_size": self.window_size,  # 1 minute window
                    },
                )
            )

        # User rate limits
        if user_api_key_dict.user_id:
            descriptors.append(
                RateLimitDescriptor(
                    key="user",
                    value=user_api_key_dict.user_id,
                    rate_limit={
                        "requests_per_unit": user_api_key_dict.user_rpm_limit,
                        "tokens_per_unit": user_api_key_dict.user_tpm_limit,
                        "window_size": self.window_size,
                    },
                )
            )

        # Team rate limits
        if user_api_key_dict.team_id:
            descriptors.append(
                RateLimitDescriptor(
                    key="team",
                    value=user_api_key_dict.team_id,
                    rate_limit={
                        "requests_per_unit": user_api_key_dict.team_rpm_limit,
                        "tokens_per_unit": user_api_key_dict.team_tpm_limit,
                        "window_size": self.window_size,
                    },
                )
            )

        # End user rate limits
        if user_api_key_dict.end_user_id:
            descriptors.append(
                RateLimitDescriptor(
                    key="end_user",
                    value=user_api_key_dict.end_user_id,
                    rate_limit={
                        "requests_per_unit": user_api_key_dict.end_user_rpm_limit,
                        "tokens_per_unit": user_api_key_dict.end_user_tpm_limit,
                        "window_size": self.window_size,
                    },
                )
            )

        # Model rate limits
        requested_model = data.get("model", None)
        if requested_model and (
            get_key_model_tpm_limit(user_api_key_dict) is not None
            or get_key_model_rpm_limit(user_api_key_dict) is not None
        ):
            _tpm_limit_for_key_model = get_key_model_tpm_limit(user_api_key_dict) or {}
            _rpm_limit_for_key_model = get_key_model_rpm_limit(user_api_key_dict) or {}
            should_check_rate_limit = False
            if requested_model in _tpm_limit_for_key_model:
                should_check_rate_limit = True
            elif requested_model in _rpm_limit_for_key_model:
                should_check_rate_limit = True

            if should_check_rate_limit:
                model_specific_tpm_limit: Optional[int] = None
                model_specific_rpm_limit: Optional[int] = None
                if requested_model in _tpm_limit_for_key_model:
                    model_specific_tpm_limit = _tpm_limit_for_key_model[requested_model]
                if requested_model in _rpm_limit_for_key_model:
                    model_specific_rpm_limit = _rpm_limit_for_key_model[requested_model]
                descriptors.append(
                    RateLimitDescriptor(
                        key="model_per_key",
                        value=f"{user_api_key_dict.api_key}:{requested_model}",
                        rate_limit={
                            "requests_per_unit": model_specific_rpm_limit,
                            "tokens_per_unit": model_specific_tpm_limit,
                            "window_size": self.window_size,
                        },
                    )
                )

        # Check rate limits
        response = await self.should_rate_limit(
            descriptors=descriptors,
            parent_otel_span=user_api_key_dict.parent_otel_span,
        )

        if response["overall_code"] == "OVER_LIMIT":
            # Find which descriptor hit the limit
            for i, status in enumerate(response["statuses"]):
                if status["code"] == "OVER_LIMIT":
                    descriptor = descriptors[i]
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded for {descriptor['key']}: {descriptor['value']}. Remaining: {status['limit_remaining']}",
                        headers={
                            "retry-after": str(self.window_size)
                        },  # Retry after 1 minute
                    )

        else:
            # add descriptors to request headers
            data["litellm_proxy_rate_limit_response"] = response

    def _create_pipeline_operations(
        self,
        key: str,
        value: str,
        rate_limit_type: Literal["requests", "tokens", "max_parallel_requests"],
        total_tokens: int,
    ) -> List["RedisPipelineIncrementOperation"]:
        """
        Create pipeline operations for TPM increments
        """
        from litellm.types.caching import RedisPipelineIncrementOperation

        pipeline_operations: List[RedisPipelineIncrementOperation] = []
        counter_key = self.create_rate_limit_keys(
            key=key,
            value=value,
            rate_limit_type="tokens",
        )
        pipeline_operations.append(
            RedisPipelineIncrementOperation(
                key=counter_key,
                increment_value=total_tokens,
                ttl=self.window_size,
            )
        )

        return pipeline_operations

    def get_rate_limit_type(self) -> Literal["output", "input", "total"]:
        from litellm.proxy.proxy_server import general_settings

        specified_rate_limit_type = general_settings.get(
            "token_rate_limit_type", "output"
        )
        if not specified_rate_limit_type or specified_rate_limit_type not in [
            "output",
            "input",
            "total",
        ]:
            return "total"  # default to total
        return specified_rate_limit_type

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        """
        Update TPM usage on successful API calls by incrementing counters using pipeline
        """
        from litellm.litellm_core_utils.core_helpers import (
            _get_parent_otel_span_from_kwargs,
        )
        from litellm.proxy.common_utils.callback_utils import (
            get_model_group_from_litellm_kwargs,
        )
        from litellm.types.caching import RedisPipelineIncrementOperation
        from litellm.types.utils import ModelResponse, Usage

        rate_limit_type = self.get_rate_limit_type()

        litellm_parent_otel_span: Union[Span, None] = _get_parent_otel_span_from_kwargs(
            kwargs
        )
        try:
            verbose_proxy_logger.debug(
                "INSIDE parallel request limiter ASYNC SUCCESS LOGGING"
            )

            # Get metadata from kwargs
            user_api_key = kwargs["litellm_params"]["metadata"].get("user_api_key")
            user_api_key_user_id = kwargs["litellm_params"]["metadata"].get(
                "user_api_key_user_id"
            )
            user_api_key_team_id = kwargs["litellm_params"]["metadata"].get(
                "user_api_key_team_id"
            )
            user_api_key_end_user_id = kwargs.get("user") or kwargs["litellm_params"][
                "metadata"
            ].get("user_api_key_end_user_id")
            model_group = get_model_group_from_litellm_kwargs(kwargs)

            # Get total tokens from response
            total_tokens = 0
            if isinstance(response_obj, ModelResponse):
                _usage = getattr(response_obj, "usage", None)
                if _usage and isinstance(_usage, Usage):
                    if rate_limit_type == "output":
                        total_tokens = _usage.completion_tokens
                    elif rate_limit_type == "input":
                        total_tokens = _usage.prompt_tokens
                    elif rate_limit_type == "total":
                        total_tokens = _usage.total_tokens

            # Create pipeline operations for TPM increments
            pipeline_operations: List[RedisPipelineIncrementOperation] = []

            # API Key TPM
            if user_api_key:
                # MAX PARALLEL REQUESTS - only support for API Key, just decrement the counter
                counter_key = self.create_rate_limit_keys(
                    key="api_key",
                    value=user_api_key,
                    rate_limit_type="max_parallel_requests",
                )
                pipeline_operations.append(
                    RedisPipelineIncrementOperation(
                        key=counter_key,
                        increment_value=-1,
                        ttl=self.window_size,
                    )
                )
                pipeline_operations.extend(
                    self._create_pipeline_operations(
                        key="api_key",
                        value=user_api_key,
                        rate_limit_type="tokens",
                        total_tokens=total_tokens,
                    )
                )

            # User TPM
            if user_api_key_user_id:
                # TPM
                pipeline_operations.extend(
                    self._create_pipeline_operations(
                        key="user",
                        value=user_api_key_user_id,
                        rate_limit_type="tokens",
                        total_tokens=total_tokens,
                    )
                )

            # Team TPM
            if user_api_key_team_id:
                pipeline_operations.extend(
                    self._create_pipeline_operations(
                        key="team",
                        value=user_api_key_team_id,
                        rate_limit_type="tokens",
                        total_tokens=total_tokens,
                    )
                )

            # End User TPM
            if user_api_key_end_user_id:
                pipeline_operations.extend(
                    self._create_pipeline_operations(
                        key="end_user",
                        value=user_api_key_end_user_id,
                        rate_limit_type="tokens",
                        total_tokens=total_tokens,
                    )
                )

            # Model-specific TPM
            if model_group and user_api_key:
                pipeline_operations.extend(
                    self._create_pipeline_operations(
                        key="model_per_key",
                        value=f"{user_api_key}:{model_group}",
                        rate_limit_type="tokens",
                        total_tokens=total_tokens,
                    )
                )

            # Execute all increments in a single pipeline
            if pipeline_operations:
                await self.internal_usage_cache.dual_cache.async_increment_cache_pipeline(
                    increment_list=pipeline_operations,
                    litellm_parent_otel_span=litellm_parent_otel_span,
                )

        except Exception as e:
            verbose_proxy_logger.exception(
                f"Error in rate limit success event: {str(e)}"
            )

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        """
        Decrement max parallel requests counter for the API Key
        """
        from litellm.litellm_core_utils.core_helpers import (
            _get_parent_otel_span_from_kwargs,
        )
        from litellm.types.caching import RedisPipelineIncrementOperation

        try:
            litellm_parent_otel_span: Union[
                Span, None
            ] = _get_parent_otel_span_from_kwargs(kwargs)
            user_api_key = kwargs["litellm_params"]["metadata"].get("user_api_key")
            pipeline_operations: List[RedisPipelineIncrementOperation] = []

            if user_api_key:
                # MAX PARALLEL REQUESTS - only support for API Key, just decrement the counter
                counter_key = self.create_rate_limit_keys(
                    key="api_key",
                    value=user_api_key,
                    rate_limit_type="max_parallel_requests",
                )
                pipeline_operations.append(
                    RedisPipelineIncrementOperation(
                        key=counter_key,
                        increment_value=-1,
                        ttl=self.window_size,
                    )
                )

            # Execute all increments in a single pipeline
            if pipeline_operations:
                await self.internal_usage_cache.dual_cache.async_increment_cache_pipeline(
                    increment_list=pipeline_operations,
                    litellm_parent_otel_span=litellm_parent_otel_span,
                )
        except Exception as e:
            verbose_proxy_logger.exception(
                f"Error in rate limit failure event: {str(e)}"
            )

    async def async_post_call_success_hook(
        self, data: dict, user_api_key_dict: UserAPIKeyAuth, response
    ):
        """
        Post-call hook to update rate limit headers in the response.
        """
        try:
            from pydantic import BaseModel

            litellm_proxy_rate_limit_response = cast(
                Optional[RateLimitResponse],
                data.get("litellm_proxy_rate_limit_response", None),
            )

            if litellm_proxy_rate_limit_response is not None:
                # Update response headers
                if hasattr(response, "_hidden_params"):
                    _hidden_params = getattr(response, "_hidden_params")
                else:
                    _hidden_params = None

                if _hidden_params is not None and (
                    isinstance(_hidden_params, BaseModel)
                    or isinstance(_hidden_params, dict)
                ):
                    if isinstance(_hidden_params, BaseModel):
                        _hidden_params = _hidden_params.model_dump()

                    _additional_headers = (
                        _hidden_params.get("additional_headers", {}) or {}
                    )

                    # Add rate limit headers
                    for status in litellm_proxy_rate_limit_response["statuses"]:
                        prefix = f"x-ratelimit-{status['descriptor_key']}"
                        _additional_headers[
                            f"{prefix}-remaining-{status['rate_limit_type']}"
                        ] = status["limit_remaining"]
                        _additional_headers[
                            f"{prefix}-limit-{status['rate_limit_type']}"
                        ] = status["current_limit"]

                    setattr(
                        response,
                        "_hidden_params",
                        {**_hidden_params, "additional_headers": _additional_headers},
                    )

        except Exception as e:
            verbose_proxy_logger.exception(
                f"Error in rate limit post-call hook: {str(e)}"
            )